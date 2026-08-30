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
    #
    # ⚠️ **최하위 폴백 추가(대규모 스크리닝, 2026-08-29 LLY 실측)**: LLY는 위
    # 세 태그 어디에도 **10-K 연간치**가 없다(`PaymentsToAcquireProductiveAssets`가
    # 10-Q 분기누계로만 채워지고 연간 항목이 아예 없다). 실제 연간 capex는
    # `PaymentsToAcquireOtherPropertyPlantAndEquipment`(FY2025 $7,841M, 10-K)에
    # 있었다 - 34종목 큐를 넘어 1만종목 규모로 가니 처음 마주친 태그 변형이다.
    # **최하위(4번째) 우선순위로만 추가한다** - 우선순위 메커니즘상(연도별로
    # 아직 안 채워진 경우에만 다음 태그를 쓴다) 이 추가는 기존 34종목의 이미
    # 확정된 값을 절대 바꿀 수 없고 **미확보였던 연도만 채울 수 있다**(순수
    # additive). 34종목 골든재현으로 이를 실측 확인했다(불일치 0건).
    "capex": (
        "PaymentsToAcquireProductiveAssets",
        "PaymentsToAcquirePropertyPlantAndEquipment",
        "PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities",  # ifrs
        "PaymentsToAcquireOtherPropertyPlantAndEquipment",
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
# "public_float"은 METRIC_TAGS(FinancialFact 경로)에는 없지만 같은 파싱
# 헬퍼(`_annual_entries`)를 재사용하므로 여기에도 등록한다.
INSTANT_METRICS = frozenset({"shareholders_equity", "public_float"})

# ⚠️ `public_float`은 위 METRIC_TAGS(→FinancialFact→AnalysisInputs 1:1 경로,
# base.py의 METRICS로 강제됨)에 넣지 않는다 - `run_analysis()`가 소비하는
# 지표가 아니라 **대규모 스크리닝(2026-08-29) 전용 시가총액 근사치**이기
# 때문이다. 별도 얇은 함수(`public_float_by_year`)로 분리한다.
_PUBLIC_FLOAT_TAG = "EntityPublicFloat"


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

    ⚠️ **회계연도는 종료일의 연도(`int(end[:4])`)로 정한다 — 52/53주 회계연도를
    쓰는 회사에서 이 규약이 회사 자신의 라벨과 어긋난다.** CDNS 실측(2026-08-21):

        2019-12-29~2021-01-02  (회사 기준 FY2020)  -> 여기서는 fy=2021
        2021-01-03~2022-01-01  (회사 기준 FY2021)  -> 여기서는 fy=2022

    그 결과 CDNS는 provider 출력이 ledger 대비 **한 해씩 밀린다**(FY2021 자리에
    FY2020 값, 불일치 7~16%). 두 기간이 같은 라벨로 충돌하면 min(filed) 규칙상
    **이른 회계연도가 이기고 늦은 쪽이 조용히 사라진다.**

    **자동 재라벨링은 하지 않는다** — 회계연도 라벨 규약이 회사마다 다르고
    (CDNS는 1월 초 종료를 전년으로, GEN은 3월 말 종료를 당해로 센다) 관측이
    2종목뿐이라 일반 규칙을 만들 근거가 없다(§21 LEVEL 1, PHASE 3의 소프트웨어
    태그와 같은 판단). 대신 충돌 사실을 호출부에 알린다.

    반환: (picked, collisions) — collisions는 {fy: [(start, end), ...]}.
    """
    picked, seen = {}, {}
    for start, end, filed, val in rows:
        fy = int(end[:4])
        if years is not None and fy not in years:
            continue
        seen.setdefault(fy, set()).add((start, end))
        if fy not in picked or filed < picked[fy][2]:
            picked[fy] = (start, end, filed, val)
    collisions = {fy: sorted(p) for fy, p in seen.items() if len(p) > 1}
    return picked, collisions


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
                                retrieved_at=None, as_of=None) -> "ProviderResult":  # noqa: F821
        """
        as_of(2026-08-29, PIT 백테스트 신설): 지정하면 `filed <= as_of`인
        항목만 쓴다 - "그 시점에 실제로 알 수 있었던 값"으로 되돌린다.

        ⚠️ `retrieved_at`(오늘 이 코드를 실행한 시각)과 `as_of`(재현하려는 과거
        시점)는 다른 개념이다. `retrieved_at`은 항상 오늘이어야 하고(추측
        금지 원칙 그대로), `as_of`만 과거로 설정한다 - 결과의 `meta.retrieved_at`
        은 실행 시각을 정직하게 남기고, "그 시점 재구성"이라는 사실은
        `governance`에 별도로 기록한다(아래).

        None(기본값)이면 기존 동작과 완전히 동일 - 모든 기존 호출부
        (`run_analysis`/`deep_screen`/`broad_screen`)는 영향 없다.
        """
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
            picked, chosen, fy_collisions = {}, {}, {}
            units_available = set()
            for taxonomy_name, taxonomy in taxonomies.items():
                for tag in METRIC_TAGS[metric]:
                    if tag not in taxonomy:
                        continue
                    for unit_name, entries in (taxonomy[tag].get("units") or {}).items():
                        rows = _annual_entries(entries, metric)
                        if as_of:
                            rows = [r for r in rows if r[2] <= as_of]  # r=(start,end,filed,val)
                        cand, coll = _pick_by_fiscal_year(rows, years)
                        if cand:
                            units_available.add(unit_name)
                        for fy, periods in coll.items():
                            fy_collisions.setdefault(fy, set()).update(periods)
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

            # ⚠️ 통화/단위 혼재 (2026-08-26, RQ-005 측정 중 발견)
            #
            # 中 발행사는 같은 태그를 **CNY와 USD 두 단위로 동시 보고**한다
            # (PDD·TCOM 실측). 위 루프는 `if fy not in picked`라 JSON에 먼저
            # 나온 단위가 이기는데, 그 순서에는 아무 의미가 없다.
            #
            # 두 경우를 구분한다:
            #  (a) 채택된 시계열이 **한 단위로 일관** → 정보성 안내. 값 자체는
            #      일관되므로 비율(FCF수익률·Gap)은 옳지만, 어느 통화인지 모른 채
            #      절대값을 쓰면 틀린다 - v3.67 규모 조건부 상한이 정확히 그
            #      경로다(TCOM ledger가 CNY 값에 currency="USD" 라벨을 달고 있어
            #      규모구간이 25000+ vs 4500-7000으로 갈렸다. RG 12.39%가 두 상한
            #      17.87%/23.00% 어느 쪽에도 안 걸려 실제 피해는 없었다).
            #  (b) 채택된 시계열이 **여러 단위에 걸침** → 한 시계열 안에서 연도별로
            #      통화가 섞였다는 뜻이라 CAGR이 7배 단위로 망가진다. 조용히
            #      넘기지 않는다.
            units_used = {u for _, _, u in chosen.values()}
            if len(units_used) > 1:
                by_unit = {}
                for fy, (_, _, u) in chosen.items():
                    by_unit.setdefault(u, []).append(fy)
                limitations.append(
                    f"[단위 혼재 - 심각] {metric}: 채택된 시계열이 여러 단위에 "
                    f"걸쳐 있다 { {u: sorted(v) for u, v in by_unit.items()} }. "
                    f"연도별로 통화·단위가 달라 CAGR·증감률이 무의미하다 — "
                    f"단위를 하나로 지정해 다시 받을 것."
                )
            elif len(units_available) > 1:
                limitations.append(
                    f"[복수 단위 보고] {metric}: 이 회사는 "
                    f"{sorted(units_available)} 단위로 같은 값을 함께 보고한다. "
                    f"채택된 단위는 {sorted(units_used)[0] if units_used else '?'}"
                    f"이며 시계열은 일관된다. 비율 지표는 영향이 없으나 "
                    f"**절대값을 쓰는 경로(규모 구간 판정 등)는 이 통화를 "
                    f"명시적으로 확인할 것.**"
                )

            if fy_collisions:
                sample = sorted(fy_collisions)[:3]
                limitations.append(
                    f"[회계연도 라벨 충돌] {metric}: {sorted(fy_collisions)}년에 서로 "
                    f"다른 보고기간이 같은 회계연도로 잡힌다(예: FY{sample[0]} "
                    + " | ".join(f"{a}~{b}" for a, b in sorted(fy_collisions[sample[0]]))
                    + "). 52/53주 회계연도를 쓰는 회사에서 이 라벨이 회사 자신의 "
                    "회계연도와 어긋날 수 있고, 그 경우 값이 **한 해씩 밀린다** "
                    "(CDNS 실측: ledger 대비 7~16% 불일치). 연도 정렬을 직접 확인할 것."
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
                                _annual_entries(entries, metric), years)[0].items():
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
                                _annual_entries(entries, metric), years)[0].items():
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
        result.governance = dict(result.governance, used_tags=used_tags, as_of=as_of)
        return result


# ── 재작성 이력 (RQ-005, 2026-08-26) ────────────────────────────────────
# 축0 L2(회계 품질)의 세 번째 진단값. 발생액·AR추세와 달리 **외부 문헌이 필요
# 없는 직접 관측 사실**이다 - 같은 회계기간을 여러 공시가 서로 다른 값으로
# 보고했는가.
#
# 여기에 두는 이유: 이 함수는 여러 공시본을 가로질러 봐야 하는데, 그 원자료
# (companyfacts의 filed별 항목)를 파싱하는 계층이 여기다. `accounting_quality`는
# 연도->값 dict만 받는 순수 모듈로 유지한다.

# 5% 초과 변경만 '재작성'으로 센다(반올림·재분류 잡음 제외).
RESTATEMENT_MATERIAL = 0.05

# ⚠️ 10배 초과 변경은 재작성이 아니다. 감사받은 연간 수치가 10배 고쳐지는 일은
# 사실상 없고, 그 규모는 **두 숫자가 서로 다른 실체를 가리킨다**는 뜻이다 -
# 단위 차이이거나 같은 CIK 아래 보고주체가 바뀐 경우다(VRT가 2020년 SPAC 합병
# 전 껍데기 법인 재무제표를 같은 CIK로 제출한 것이 실례: FY2018 영업현금흐름이
# -710,388에서 -221,900,000으로 311배). 분자·분모 양쪽에서 빼고 따로 센다.
#
# 이 규칙은 VRT 사례를 본 **뒤에** 정했다 - 이 프로젝트 관행대로 숨기지 않는다.
# 근거는 결과가 아니라 도메인 사실(감사된 연간 수치의 정정 폭 한계)이며,
# PHASE 4가 주식분할 오염을 '인접연도 1.5배'로 막은 것과 같은 형태의 제약이다.
ENTITY_CHANGE_THRESHOLD = 10.0

RESTATEMENT_METRICS = ("revenue", "operating_cashflow", "net_income")


def restatement_profile(facts, metrics=RESTATEMENT_METRICS):
    """
    companyfacts에서 **재작성 이력**을 센다.

    같은 (태그, 단위, 기간)을 두 번 이상 보고한 항목만 대상이며, 최초 공시본과
    최신 공시본의 차이가 `RESTATEMENT_MATERIAL`를 넘으면 재작성으로 센다.

    ⚠️ **단위별로 따로 센다.** 초판(RQ-005 측정 스크립트)은 `units.values()`를
    합쳐 비교했다가 PDD·TCOM이 재작성률 0.83~0.87로 나왔는데, 편차가 정확히
    629.9%로 반복돼 확인해보니 CNY와 USD를 나란히 비교한 것이었다(7.299 =
    위안/달러). 이 프로젝트가 반복해 밟은 단위 함정과 같은 계열이다.

    ⚠️ **재작성률 0은 '깨끗하다'가 아니다.** 공시가 한 번뿐인 기간은 분모에
    들어가지 않는다 - 상장이 짧거나 XBRL 이력이 얕으면 잴 기회 자체가 없다.
    그래서 `multi_filed_periods`를 함께 낸다("데이터 없음을 안전으로 오독하지
    않는다"는 이 프로젝트의 반복 원칙).

    ⚠️ **연속 순위지표로 쓰지 말 것.** 34종목 실측에서 22종목이 정확히 0이라
    중앙값이 0이다 - 사실상 '재작성 이력이 있는가'라는 이진 사실이다.

    판정·점수를 내지 않는다(§31 합성점수 금지).
    """
    taxonomies = facts.get("facts", {}) or {}
    total = restated = 0
    worst = 0.0
    detail, entity = [], []

    for metric in metrics:
        for tag in METRIC_TAGS[metric]:
            hit = False
            for taxonomy in taxonomies.values():
                node = taxonomy.get(tag)
                if not node:
                    continue
                hit = True
                for unit, entries in (node.get("units") or {}).items():
                    periods = {}
                    for start, end, filed, val in _annual_entries(entries, metric):
                        periods.setdefault((start, end), []).append((filed, val))
                    for period, rows in periods.items():
                        if len(rows) < 2:
                            continue
                        rows.sort()
                        first, last = rows[0][1], rows[-1][1]
                        if first == 0:
                            continue
                        dev = abs(last - first) / abs(first)
                        rec = {"metric": metric, "unit": unit,
                               "period": list(period), "first_reported": first,
                               "latest_reported": last, "deviation": dev,
                               "first_filed": rows[0][0], "latest_filed": rows[-1][0]}
                        if dev > ENTITY_CHANGE_THRESHOLD:
                            entity.append(rec)      # 분모에서도 뺀다
                            continue
                        total += 1
                        if dev > RESTATEMENT_MATERIAL:
                            restated += 1
                            worst = max(worst, dev)
                            detail.append(rec)
            if hit:
                break   # 지표당 첫 유효 태그만(_pick_by_fiscal_year와 같은 규약)

    notes = []
    if total == 0:
        notes.append(
            "[측정 불가] 두 번 이상 보고된 회계기간이 없다 - 재작성이 없었다는 "
            "뜻이 아니라 **잴 기회가 없었다**는 뜻이다.")
    if entity:
        notes.append(
            f"[실체·단위 변경 제외] 변경폭이 {ENTITY_CHANGE_THRESHOLD:.0f}배를 넘는 "
            f"{len(entity)}건은 재작성이 아니라 보고주체 또는 단위가 바뀐 것으로 "
            f"보고 분모·분자에서 제외했다.")

    return {
        "multi_filed_periods": total,
        "restated_periods": restated,
        "restatement_rate": (restated / total) if total else None,
        "has_material_restatement": restated > 0,
        "worst_deviation": worst if restated else None,
        "restatements": sorted(detail, key=lambda d: -d["deviation"]),
        "entity_or_unit_changes": sorted(entity, key=lambda d: -d["deviation"]),
        "notes": notes,
    }


# ── 시가총액 근사치 (대규모 스크리닝 전용, 2026-08-29) ─────────────────────
#
# 34종목 손입력 큐를 넘어서려면 수천 개 티커의 대략적인 시가총액이 필요한데,
# Alpha Vantage는 무료 한도가 25회/일이라 애초에 스케일이 안 맞고, Yahoo
# Finance·Stooq 같은 무료 시세원은 API 호스트 robots.txt가 **전체 봇을
# 차단**한다(2026-08-29 원문 직접 확인: query1.finance.yahoo.com·stooq.com
# 둘 다 `User-agent: *` / `Disallow: /`) - Finviz 때 이미 확립한 원칙
# ("robots.txt로 자동화 허용범위를 직접 확인할 것")을 그대로 적용하면 이
# 경로는 쓸 수 없다.
#
# 대신 SEC가 10-K 표지에 회사 스스로 보고하는 `EntityPublicFloat`(비계열
# 주주 보유주식의 시가총액)을 근사치로 쓴다 - 이건 위 METRIC_TAGS 경로
# (FinancialFact → AnalysisInputs 1:1)와 별개다. `run_analysis()`가 쓰는
# 지표가 아니라 **스크리닝 1차 필터 전용**이라 `base.METRICS` 검증을 거치지
# 않는 얇은 함수로 분리했다.
def public_float_from_facts(facts_json: dict, as_of: str = None) -> dict:
    """
    순수 파싱 함수 - 이미 받아둔 companyfacts JSON에서 public_float만 뽑는다.

    ⚠️ 대규모 스크리닝(2026-08-29) 실측에서 `public_float_by_year`가 매
    티커마다 companyfacts를 **두 번**(financials용 1회 + 이 함수 안에서 1회)
    받고 있어 SEC 요청량이 그대로 배로 늘고 있었다(300종목 파일럿이 180초
    타임아웃을 넘김). 원인은 네트워크 호출과 파싱이 한 함수에 묶여 있던 것 -
    이미 받아온 JSON을 재사용할 방법이 없었다. 파싱만 분리해 호출부가 같은
    companyfacts를 여러 목적(재무지표 + 시총 근사)에 **한 번의 요청으로**
    재사용할 수 있게 한다.

    as_of(PIT 백테스트 신설): `fetch_annual_financials`의 동명 인자와 동일한
    의미 - `filed <= as_of`인 값만 쓴다. None(기본값)이면 기존 동작과 동일.

    세 가지 한계는 `public_float_by_year`와 동일(그 함수의 docstring 참고).
    """
    taxonomies = facts_json.get("facts") or {}
    node = taxonomies.get("dei", {}).get(_PUBLIC_FLOAT_TAG)
    if not node:
        return {}
    out = {}
    for entries in (node.get("units") or {}).values():
        rows = _annual_entries(entries, "public_float")
        if as_of:
            rows = [r for r in rows if r[2] <= as_of]
        picked, _ = _pick_by_fiscal_year(rows, None)
        for fy, (_, _, _, val) in picked.items():
            out[fy] = float(val)
    return out


def public_float_by_year(entity: str, retrieved_at: str, user_agent: str = None,
                         resolve_cik=None, fetch_facts=None) -> dict:
    """
    티커 -> {회계연도: EntityPublicFloat(USD)}. 못 찾으면 빈 dict(추측하지 않음).

    ⚠️ 세 가지 한계 - 호출부가 반드시 인지할 것:
      (1) 계열주주(임원·대주주) 보유분 제외 - 실제 시총보다 작을 수 있다.
      (2) 회계연도 중 한 시점(대개 2분기 말) 스냅샷 - 최대 ~18개월 낡을 수 있다.
      (3) 10-K에만 실린다 - 20-F 외국 발행사는 대개 미보고.
    최종 후보로 좁혀진 뒤에는 반드시 정밀한 실시간 시총으로 재확인할 것.

    ⚠️ 이미 companyfacts를 받아둔 상태라면 이 함수(자체 네트워크 호출 포함)
    대신 `public_float_from_facts(facts_json)`을 직접 쓸 것 - 안 그러면
    같은 회사를 두 번 조회하게 된다(위 `public_float_from_facts` docstring
    참고, 실제로 이 중복이 대규모 스크리닝을 2배 느리게 만들었다).
    """
    if not retrieved_at:
        raise ValueError("retrieved_at을 반드시 넘길 것(추측 금지).")
    resolve_cik = resolve_cik or ticker_to_cik
    fetch_facts = fetch_facts or fetch_company_facts
    cik = resolve_cik(entity, user_agent)
    if not cik:
        return {}
    return public_float_from_facts(fetch_facts(cik, user_agent))
