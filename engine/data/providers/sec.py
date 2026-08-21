"""
SEC Provider (P0-03, 2026-08-19) — SEC XBRL companyfacts를 IRS 도메인 타입으로.

# SOURCE:
https://github.com/dgunning/edgartools  (MIT)

# CAPABILITY:
SEC EDGAR / XBRL 표준화 재무제표 / typed filing abstraction / rate limiting

# IRS_TARGET:
engine/data/providers/sec.py

# METHOD:
**REIMPLEMENT** (계획서의 ADAPT에서 변경 — 근거는 아래)

# WHY — 왜 ADAPT가 아니라 REIMPLEMENT인가

계획서는 P0-03을 ADAPT(edgartools를 의존성으로 두고 어댑터로 감싸기)로 잡았다.
실제 코드·의존성을 확인한 뒤(§1.4) 바꿨다. 확인한 사실:

1. **edgartools 런타임 의존성 21개** (pyproject.toml 직접 확인, MIT):
   httpx · pandas · tabulate · pyarrow · beautifulsoup4 · lxml · rich · humanize ·
   stamina · orjson · textdistance · rank_bm25 · rapidfuzz · unidecode · pydantic ·
   tqdm · nest-asyncio · jinja2 · pyrate-limiter · httpxthrottlecache · truststore
2. **IRS의 현재 런타임 의존성은 0개다.** `engine/` 전체가 표준 라이브러리만
   쓴다(dataclasses·datetime·glob·hashlib·json·os·random·re·statistics·urllib).
   `requirements.txt`도 `pyproject.toml`도 없다.
3. **CI(`.github/workflows/tests.yml`)는 `pip install pytest` 한 줄뿐이다.**

즉 ADAPT는 의존성 0개 프로젝트에 21개 트리를 들이고, 의존성 관리 파일을
신설하고, CI를 바꾸는 일이다 — 통합 원칙 §1.14("외부 repository가 IRS
architecture를 무리하게 바꾸도록 하지 않는다")와 §1.15("더 적합한 기존 IRS
기능이 있다면 외부 repository를 사용하지 않는다")에 정면으로 걸린다.
게다가 IRS가 지금 필요한 것은 edgartools 기능 표면의 극히 일부다 — 연간
재무수치와 제출일이며, 그건 `engine/filing_dates.py`가 **이미 stdlib으로**
가져오고 있다(ONON 사건에서 실전 검증됨).

**REJECT가 아니라 REIMPLEMENT다.** edgartools에서 실제로 가져온 설계는 둘:
  - **XBRL 태그 표준화**: 회사마다, 그리고 **같은 회사도 연도마다** 다른 태그를
    쓰므로(us-gaap vs ifrs-full, ASC 606 전후) 지표별 **우선순위 목록**으로
    정규화한다. 태그 하나를 고정하면 외국 발행사나 기준 변경 이전 연도가
    조용히 사라진다 — BSX FY2015에서 실제로 그랬다.
  - **어댑터 경계**: 외부 응답 객체를 도메인에 노출하지 않고 typed 도메인
    객체만 돌려준다(§1.8).
레이트리밋은 P0-01에서 이미 별도로 반영했다.

# TEST:
tests/test_sec_provider.py  (네트워크 없이 합성 companyfacts로 검증)

---

## ⚠️ `available_at`의 정확한 의미 — 실측으로 확인된 미묘함

이 값은 **"그 회계연도 실적이 처음 공시된 날"이 아니라 "그 수치가 이 태그로
처음 등장한 날"** 이다. BSX 실측에서 FY2016·2017·2018이 전부 `2019-02-19`로
나왔는데, 세 해 모두 `Revenues` 태그로는 FY2018 10-K에서 처음 등장하기 때문이다
(ASC 606 전환 전에는 회사가 다른 태그를 썼다).

PIT 관점에서 이는 **보수적인 방향**이다 — 실제보다 늦은 날짜를 쓰므로 미래정보
사용을 놓치지 않는다. 다만 분석일이 원 공시일과 태그 최초등장일 **사이**에 있으면
실제로는 알 수 있었던 데이터가 위반으로 잡힐 수 있다(거짓 양성). 그 경우
`[태그 혼재]` 경고와 함께 원 공시일을 직접 확인할 것.

## ⚠️ 이 provider가 보장하지 않는 것

- **재작성(restatement)을 구분하지 못한다.** companyfacts는 현재 시점의 값을
  주며, 같은 회계연도가 여러 번 나오면 **최초 공시일(min filed)** 을 택하지만
  그 값 자체는 최신본일 수 있다. "그 시점에 공시돼 있었는가"는 답하고
  "그때 숫자가 이거였는가"는 답하지 못한다(`engine/filing_dates.py`와 동일 한계).
- **값을 검증하지 않는다.** 태그가 맞는지, 회사가 그 태그를 관행대로 썼는지는
  보증하지 않는다. 대조는 P0-07의 몫이다.
"""

from engine.data.providers.base import FinancialFact, FinancialProvider
from engine.filing_dates import (
    ANNUAL_FORMS, _days_between, fetch_company_facts, ticker_to_cik,
)

# 지표별 XBRL 태그 우선순위. 앞의 태그를 먼저 쓰되 **비어 있는 연도만** 뒤의
# 태그로 보충한다(BSX FY2015 실측으로 확정 — ASC 606 전후로 태그가 갈린다).
# 섞였다는 사실은 값마다 `FinancialFact.source`에 남고 limitations로도 경고한다.
# ifrs-full은 외국 발행사(20-F)용이다: SAP·BABA·ONON 등이 여기 걸린다.
METRIC_TAGS = {
    "revenue": (
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "Revenues",
        "RevenueFromContractWithCustomerIncludingAssessedTax",
        "SalesRevenueNet",
        "Revenue",                                     # ifrs-full
    ),
    "operating_income": (
        "OperatingIncomeLoss",
        "ProfitLossFromOperatingActivities",           # ifrs-full
    ),
    "operating_cashflow": (
        "NetCashProvidedByUsedInOperatingActivities",
        "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations",
        "CashFlowsFromUsedInOperatingActivities",      # ifrs-full
    ),
    # ⚠️ XBRL의 Payments* 태그는 **유출을 양수로** 보고한다. IRS의 capex 규약도
    # 양수다(FCF = OCF − capex, BSX FY2025: 4,534 − 876 = 3,658로 확인). 부호를
    # 뒤집지 않는다 — 이 프로젝트는 capex 부호 사고를 이미 한 번 겪었다.
    #
    # ⚠️ **우선순위 주의(PHASE 3, 2026-08-21에 실측으로 뒤집음)**:
    # `PaymentsToAcquireProductiveAssets`(넓은 정의 = 유형자산 + 기타 생산자산)를
    # `PaymentsToAcquirePropertyPlantAndEquipment`(좁은 정의)보다 **먼저** 쓴다.
    # 초판은 좁은 정의가 1순위여서, 두 태그를 모두 보고하는 회사에서 소프트웨어
    # 자본화 등이 통째로 빠졌다 — MCK FY2026 실측 436M vs 실제 745M(−41%).
    #
    # 근거: 넓은 태그를 보고하는 4종목의 **39개년 전수에서 넓은 정의가 ledger
    # (1차 자료 기반 손입력)와 100% 일치**한다(ACGL 11/11 · MCK 7/7 · WCN 9/9 ·
    # WM 12/12). MCK는 `narrow + PaymentsToAcquireSoftware == broad`로 교차확인까지
    # 된다. 넓은 태그가 없는 종목은 그대로 좁은 정의로 폴백하므로 동작이 안 바뀐다.
    "capex": (
        "PaymentsToAcquireProductiveAssets",
        "PaymentsToAcquirePropertyPlantAndEquipment",
        "PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities",  # ifrs
    ),
    "net_income": (
        "NetIncomeLoss",
        "ProfitLoss",                                  # ifrs-full
    ),
    "shareholders_equity": (
        "StockholdersEquity",
        "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
        "Equity",                                      # ifrs-full
    ),
    "dividends_paid": (
        "PaymentsOfDividendsCommonStock",
        "PaymentsOfDividends",
        "DividendsPaidClassifiedAsFinancingActivities",  # ifrs-full
    ),
    "sbc": (
        "ShareBasedCompensation",
        "AllocatedShareBasedCompensationExpense",
    ),
}

# 시점(instant) 지표 — 구간이 아니라 특정 날짜의 잔액이다. companyfacts 항목에
# `start`가 없다. 기간 지표와 같은 규칙(330~400일)으로 거르면 전부 탈락한다.
INSTANT_METRICS = frozenset({"shareholders_equity"})


def _annual_entries(entries, metric):
    """연간(또는 시점) 항목만 남긴다. 분기·반기는 제외."""
    out = []
    for e in entries:
        if e.get("form") not in ANNUAL_FORMS:
            continue
        end, filed, val = e.get("end"), e.get("filed"), e.get("val")
        if not (end and filed) or val is None:
            continue
        if metric in INSTANT_METRICS:
            out.append((end, end, filed, val))
            continue
        start = e.get("start")
        if not start:
            continue
        try:
            if not 330 <= _days_between(start, end) <= 400:
                continue
        except ValueError:
            continue
        out.append((start, end, filed, val))
    return out


def _pick_by_fiscal_year(rows, years):
    """
    회계연도별로 하나씩 고른다. 같은 연도가 여러 번 나오면 **최초 공시본**
    (min filed)을 택한다 — PIT에서 의미 있는 것은 처음 알려진 날이기 때문이며,
    `engine/filing_dates.py`의 규칙과 같다.
    """
    picked = {}
    for start, end, filed, val in rows:
        fy = int(end[:4])
        if years is not None and fy not in years:
            continue
        if fy not in picked or filed < picked[fy][2]:
            picked[fy] = (start, end, filed, val)
    return picked


class SecCompanyFactsProvider(FinancialProvider):
    """
    SEC XBRL companyfacts -> `FinancialFact`.

    네트워크 호출은 `engine/filing_dates.py`의 함수에 위임한다(P0-01에서 배선한
    레이트리밋이 거기 걸려 있으므로 우회 경로를 새로 만들지 않는다).
    """

    source_key = "sec_edgar"

    def __init__(self, purpose=None, today=None, user_agent=None,
                 fetch_facts=None, resolve_cik=None):
        super().__init__(purpose=purpose, today=today)
        self.user_agent = user_agent
        # 테스트에서 네트워크 없이 주입할 수 있게 열어둔다. 기본은 실제 SEC 경로.
        self._fetch_facts = fetch_facts or fetch_company_facts
        self._resolve_cik = resolve_cik or ticker_to_cik

    def fetch_annual_financials(self, entity, metrics=None, fiscal_years=None,
                                retrieved_at=None) -> "ProviderResult":  # noqa: F821
        if not retrieved_at:
            raise ValueError(
                "retrieved_at을 반드시 넘길 것 — 조회일을 자동으로 오늘로 채우면 "
                "나중에 이 결과가 언제 것인지 알 수 없다(추측 금지)."
            )
        want = tuple(metrics or METRIC_TAGS)
        unknown = [m for m in want if m not in METRIC_TAGS]
        if unknown:
            raise ValueError(f"SEC 태그 매핑이 없는 지표: {unknown}")
        years = {int(y) for y in fiscal_years} if fiscal_years else None

        cik = self._resolve_cik(entity, self.user_agent)
        if not cik:
            # 추측하지 않는다 — 티커를 못 찾으면 빈 결과 + 사유를 남긴다.
            return self._result(
                entity, [], retrieved_at,
                limitations=[f"[티커 미해결] SEC 티커 목록에서 '{entity}'를 찾지 "
                             f"못했다. CIK를 직접 넘기거나 티커를 확인할 것."],
            )
        facts_json = self._fetch_facts(cik, self.user_agent)
        taxonomies = facts_json.get("facts") or {}

        out, limitations, used_tags = [], [], {}
        for metric in want:
            # ⚠️ 우선순위가 높은 태그부터 훑되, **아직 안 채워진 연도만** 낮은
            # 순위 태그로 보충한다. 처음에는 "첫 태그에서 멈춤"으로 구현했는데,
            # BSX 실측에서 FY2015 매출이 통째로 사라졌다 — ASC 606(2018) 전후로
            # 회사가 쓰는 태그가 갈리기 때문이다(`Revenues` -> `RevenueFrom
            # ContractWithCustomer...`). 긴 시계열은 한 태그로 덮이지 않는다.
            #
            # 출처가 흐려지지 않는 이유: 태그는 **값마다** `FinancialFact.source`에
            # 기록되므로, 섞였다는 사실 자체가 값 단위로 드러난다.
            picked, chosen = {}, {}
            for taxonomy_name, taxonomy in taxonomies.items():
                for tag in METRIC_TAGS[metric]:
                    if tag not in taxonomy:
                        continue
                    for unit_name, entries in (taxonomy[tag].get("units") or {}).items():
                        cand = _pick_by_fiscal_year(_annual_entries(entries, metric), years)
                        for fy, row in cand.items():
                            if fy not in picked:
                                picked[fy] = row
                                chosen[fy] = (taxonomy_name, tag, unit_name)

            if not picked:
                # ⚠️ 0으로 채우지 않는다. 0은 "값이 0"으로 읽혀 CAGR을 조용히 망친다.
                limitations.append(
                    f"[미확보] {metric}: 시도한 태그 {METRIC_TAGS[metric]} 중 "
                    f"연간 데이터를 찾지 못했다. 회사가 다른 태그를 쓰거나 "
                    f"XBRL 태깅 이전 연도일 수 있다."
                )
                continue

            used_tags[metric] = sorted(
                {f"{t}:{g} ({u})" for t, g, u in chosen.values()}
            )

            # capex는 넓은 정의와 좁은 정의가 **같은 해에 공존**할 수 있고 값이
            # 다르다(MCK: 745M vs 436M). 넓은 쪽을 채택하되 그 사실을 조용히
            # 넘기지 않는다 — 좁은 정의를 원하는 분석에는 이 차이가 중요하다.
            if metric == "capex" and picked:
                narrow = {}
                for taxonomy in taxonomies.values():
                    tag = "PaymentsToAcquirePropertyPlantAndEquipment"
                    if tag not in taxonomy:
                        continue
                    for entries in (taxonomy[tag].get("units") or {}).values():
                        for fy, row in _pick_by_fiscal_year(
                                _annual_entries(entries, metric), years).items():
                            narrow.setdefault(fy, row[3])
                gaps = {fy: (picked[fy][3], narrow[fy]) for fy in sorted(narrow)
                        if fy in picked and picked[fy][3]
                        and abs(picked[fy][3] - narrow[fy]) / abs(picked[fy][3]) > 0.005}
                if gaps:
                    fy0 = max(gaps)
                    wide, nar = gaps[fy0]
                    limitations.append(
                        f"[capex 정의 공존] 넓은 정의(생산자산 취득)와 좁은 정의"
                        f"(유형자산 취득)가 {sorted(gaps)}년에 함께 보고되며 값이 "
                        f"다르다. 넓은 정의를 채택했다(예: FY{fy0} {wide:,.0f} vs "
                        f"{nar:,.0f}). 좁은 정의가 필요한 분석이면 직접 지정할 것."
                    )

                # ⚠️ 소프트웨어 자본화를 별도 태그로 보고하는 회사가 있다(MCK).
                # **자동으로 더하지 않는다** — 회사에 따라 유형자산 취득에 이미
                # 포함돼 있을 수 있어 이중계상 위험이 있고, 관측 사례가 1종목뿐이라
                # 일반 규칙을 만들 근거가 없다(§21 LEVEL 1). 대신 누락 가능성을
                # 조용히 넘기지 않는다: MCK FY2026이 정확히 이 경우로,
                # 넓은 태그가 아직 없어 좁은 정의(436M)가 채택되지만 회사가 보고한
                # 총 자본지출은 745M(= 436 + 소프트웨어 309)이다.
                soft = {}
                for taxonomy in taxonomies.values():
                    if "PaymentsToAcquireSoftware" not in taxonomy:
                        continue
                    for entries in (taxonomy["PaymentsToAcquireSoftware"]
                                    .get("units") or {}).values():
                        for fy, row in _pick_by_fiscal_year(
                                _annual_entries(entries, metric), years).items():
                            soft.setdefault(fy, row[3])
                unmerged = sorted(fy for fy, v in soft.items()
                                  if fy in picked and picked[fy][3] == narrow.get(fy))
                if unmerged:
                    limitations.append(
                        f"[capex 소프트웨어 별도 보고] {unmerged}년의 채택값은 "
                        f"유형자산 취득만이며, 이 회사는 소프트웨어 취득을 별도 "
                        f"태그로 보고한다(예: FY{unmerged[-1]} "
                        f"{soft[unmerged[-1]]:,.0f}). **자동으로 더하지 않았다** - "
                        f"총 자본지출이 필요하면 합산 여부를 직접 확인할 것."
                    )
            for fy, (start, end, filed, val) in sorted(picked.items()):
                taxonomy_name, tag, unit_name = chosen[fy]
                out.append(FinancialFact(
                    entity=entity, metric=metric, fiscal_year=fy,
                    value=float(val),
                    unit="currency_amount" if unit_name not in ("shares", "pure")
                         else ("shares" if unit_name == "shares" else "ratio"),
                    currency=unit_name if unit_name not in ("shares", "pure") else None,
                    period_start=start, period_end=end, available_at=filed,
                    source=f"SEC XBRL {taxonomy_name}:{tag}",
                    source_key=self.source_key, retrieved_at=retrieved_at,
                ))

            if years:
                missing = sorted(years - set(picked))
                if missing:
                    limitations.append(
                        f"[연도 누락] {metric}: 요청한 회계연도 중 {missing}를 "
                        f"찾지 못했다(시도한 태그 {METRIC_TAGS[metric]})."
                    )
            if len(used_tags[metric]) > 1:
                # 섞였다는 사실을 숨기지 않는다 — 회계기준 변경 구간일 수도, 회사가
                # 태그를 바꾼 것일 수도 있어 정의가 연도마다 다를 수 있다.
                limitations.append(
                    f"[태그 혼재] {metric}: 연도에 따라 서로 다른 XBRL 태그에서 왔다"
                    f"({used_tags[metric]}). 정의가 구간마다 다를 수 있으니 "
                    f"CAGR을 그대로 믿기 전에 경계 연도를 확인할 것."
                )

        result = self._result(
            entity, out, retrieved_at, limitations=limitations,
            raw_ref=f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json",
        )
        result.governance = dict(result.governance, used_tags=used_tags)
        return result
