"""
Provenance (v3.50 신규, 2026-08-15) - 개별 수치의 출처를 값 단위로 추적한다.

## 왜 필요한가 - `data_sources`로는 답할 수 없는 질문들

지금까지 출처 기록은 `AnalysisInputs.data_sources`라는 **자유 문자열 리스트**
하나뿐이었다(예: `["Alpha Vantage (2026-07-25)", "WebSearch: EDA market share"]`).
이걸로는 다음에 답할 수 없다:

  - FY2023 매출이 **어느 공시**에서 왔고 **언제 공개**됐는가?
  - 그 값의 **통화**가 무엇인가? (PDD가 CNY인데 ledger에 표시가 없던 M-6 문제)
  - **언제 조회**한 값인가? (재작성 전인가 후인가)
  - 회계기간이 정확히 **어디부터 어디까지**인가? (52/53주 회계연도)

`docs/change_plan.md`의 C-09가 이걸 DEFERRED로 두고 있었고, 사유는
"원자료가 분석 스크립트 안 dict 리터럴로만 존재해 수집 계층을 신설해야 한다"
였다. **v3.49에서 그 전제가 바뀌었다** - SEC companyfacts에서 제출일을 조회하는
경로가 생겼고, 같은 응답에 값·기간·단위가 전부 들어 있다. 즉 수집 계층을
새로 만들지 않고도 provenance를 **자동 생성**할 수 있다.

## 이 모듈이 하는 것 / 하지 않는 것

**한다**: 값 하나에 §6이 요구한 7개 축을 붙인다 -
source / publication_date / period / value / unit / currency / retrieval_date.
SEC companyfacts에서 자동 생성하는 경로(`provenance_from_sec_facts`)를 제공한다.

**하지 않는다**:
- 기존 34종목에 소급 생성하지 않는다. 그 분석들이 실제로 어느 값을 봤는지
  지금 알 수 없고, 지금 조회한 값을 그때 값인 양 붙이면 **허위 출처**가 된다.
  `PROVENANCE_UNKNOWN`으로 정직하게 남긴다(계약서 5.1절, §6 마지막 문단).
- 계산에 관여하지 않는다. 순수 기록 경로이며 Gap/RAR/판정에 영향이 없다
  (`price_at_analysis`·PIT 필드와 동일).
- 값이 **맞는지**는 검증하지 않는다. 출처가 무엇인지만 기록한다 - 두 출처가
  어긋날 때 어느 쪽이 옳은지는 분석자가 판단한다(TYL SBC 3배 오류의 교훈:
  2차 출처를 검증 없이 인용하지 말 것 - provenance가 있으면 최소한 **어디서
  왔는지는** 알 수 있다).
"""

from dataclasses import asdict, dataclass, field

# 출처 미상 상태 - PIT_UNKNOWN과 같은 어휘 체계(계약서 21절)
PROVENANCE_UNKNOWN = "PROVENANCE_UNKNOWN"

# 출처 종류. 신뢰도 서열이 아니라 **분류**다 - 1차 자료라고 항상 옳은 것은
# 아니지만(재작성이 있다), 최소한 무엇을 봤는지는 구분돼야 한다.
SOURCE_KINDS = (
    "sec_xbrl",        # SEC XBRL companyfacts - 발행사 제출 구조화 데이터
    "sec_filing",      # SEC 공시 원문(10-K/20-F 본문)
    "vendor_api",      # Alpha Vantage/FMP 등 2차 벤더
    "company_ir",      # 회사 IR 자료·보도자료
    "web_research",    # 웹 검색 기반(가장 약함 - TYL SBC 3배 오류가 여기서 났다)
    "analyst_input",   # 분석자 주관 입력(경쟁강도 등)
)


@dataclass
class ValueProvenance:
    """
    값 하나의 출처. §6이 요구한 7개 축을 전부 담는다.

    `unit`과 `currency`를 분리한 이유: 같은 "USD"라도 절대금액(USD)과 비율
    (ratio)은 단위가 다르고, 비율에는 통화 개념이 없다. 이 프로젝트는 단위
    사고를 두 번 겪었다(RAR 100배, 실질/명목 EPS) - 단위를 뭉뚱그리지 않는다.
    """

    field_path: str          # 무엇의 출처인가 (예: "revenue_by_year[2025]")
    value: float
    unit: str                # "currency_amount" / "ratio" / "shares" / "count"
    currency: str            # 통화. 비통화 단위면 None
    period: str              # 회계기간 (예: "FY2025" 또는 "2025-01-01~2025-12-31")
    source: str              # 출처 식별자 (예: "SEC XBRL us-gaap:Revenues")
    source_kind: str         # SOURCE_KINDS 중 하나
    publication_date: str    # 그 값이 **공개**된 날 (SEC filed 등)
    retrieval_date: str      # 우리가 **조회**한 날
    note: str = ""

    def __post_init__(self):
        if self.source_kind not in SOURCE_KINDS:
            raise ValueError(
                f"알 수 없는 출처 종류: {self.source_kind} (허용: {SOURCE_KINDS})"
            )
        for f in ("field_path", "unit", "period", "source", "retrieval_date"):
            if not str(getattr(self, f) or "").strip():
                raise ValueError(
                    f"{f}이(가) 비어 있다. 출처 기록은 빈칸을 추측으로 채우지 "
                    f"않는다 - 모르면 그 값에 provenance를 붙이지 말 것"
                    f"(PROVENANCE_UNKNOWN으로 남는다)."
                )
        # publication_date는 없을 수 있다(분석자 주관 입력 등). 그 경우 None으로
        # 두되, 자동으로 오늘 날짜를 넣지 않는다 - 공개일을 조회일로 위장하면
        # PIT 검증이 통째로 무의미해진다.
        if self.publication_date is not None and not str(self.publication_date).strip():
            self.publication_date = None


def build_provenance_record(entries: list, retrieval_date: str,
                            missing_fields: list = None) -> dict:
    """
    ValueProvenance 목록 -> ledger에 넣을 기록.

    `missing_fields`: 출처를 확보하지 못한 필드 목록. **비워두지 말 것** -
    빠진 것을 적지 않으면 커버리지가 실제보다 높아 보인다(ETF 엔진이 ERS
    항목 제외 시 사실을 남기는 것과 동일 원칙).
    """
    missing = list(missing_fields or [])
    covered = [asdict(e) if isinstance(e, ValueProvenance) else dict(e)
               for e in entries]
    return {
        "status": PROVENANCE_UNKNOWN if not covered else "PROVENANCE_RECORDED",
        "retrieval_date": retrieval_date,
        "n_covered": len(covered),
        "n_missing": len(missing),
        "missing_fields": missing,
        "entries": covered,
        "note": (
            "출처 기록은 값이 **맞는지**를 보증하지 않는다 - 어디서 왔는지만 "
            "말한다. 두 출처가 어긋나면 분석자가 1차 자료로 확정할 것."
        ),
    }


def provenance_from_sec_facts(facts: dict, ticker: str, retrieval_date: str,
                              fiscal_years, tag_preference=None) -> dict:
    """
    SEC companyfacts에서 **매출 시계열의 provenance를 자동 생성**한다.

    v3.49의 `filing_dates`와 같은 응답을 쓰므로 출처가 갈릴 여지가 없다.
    자동 생성이 중요한 이유: 손으로 적게 만들면 결국 아무도 안 적는다(이
    프로젝트가 문서 규칙에서 네 번 겪은 실패).

    ⚠️ 태그를 못 찾으면 **빈 결과**를 돌려준다. 다른 태그 값으로 대충 채우면
    "이 값은 Revenues에서 왔다"는 허위 기록이 남는다.
    """
    from engine.filing_dates import ANNUAL_FORMS, _days_between

    tags = tag_preference or (
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "Revenues",
        "RevenueFromContractWithCustomerIncludingAssessedTax",
        "Revenue",                      # ifrs-full
        "SalesRevenueNet",
    )
    years = {int(y) for y in fiscal_years}

    # 태그 우선순위대로 처음 매칭되는 것 하나만 쓴다 - 여러 태그를 섞으면
    # "이 시계열이 어느 태그에서 왔는가"가 흐려진다.
    for taxonomy_name, taxonomy in (facts.get("facts") or {}).items():
        for tag in tags:
            if tag not in taxonomy:
                continue
            for unit_name, entries in (taxonomy[tag].get("units") or {}).items():
                found = {}
                for e in entries:
                    if e.get("form") not in ANNUAL_FORMS:
                        continue
                    start, end, filed = e.get("start"), e.get("end"), e.get("filed")
                    if not (start and end and filed):
                        continue
                    try:
                        if not 330 <= _days_between(start, end) <= 400:
                            continue
                    except ValueError:
                        continue
                    fy = int(end[:4])
                    if fy not in years:
                        continue
                    # 같은 연도가 여러 번 나오면 최초 공시본을 쓴다
                    if fy not in found or filed < found[fy]["publication_date"]:
                        found[fy] = {
                            "value": e["val"], "period": f"{start}~{end}",
                            "publication_date": filed,
                        }
                if not found:
                    continue

                out = [
                    ValueProvenance(
                        field_path=f"revenue_by_year[{fy}]",
                        value=found[fy]["value"],
                        unit="currency_amount",
                        currency=unit_name,          # SEC는 단위명을 통화코드로 준다
                        period=found[fy]["period"],
                        source=f"SEC XBRL {taxonomy_name}:{tag}",
                        source_kind="sec_xbrl",
                        publication_date=found[fy]["publication_date"],
                        retrieval_date=retrieval_date,
                    )
                    for fy in sorted(found)
                ]
                missing = [f"revenue_by_year[{y}]" for y in sorted(years - set(found))]
                return build_provenance_record(out, retrieval_date, missing)

    # 아무 태그도 못 찾음 - 억지로 채우지 않는다
    return build_provenance_record(
        [], retrieval_date,
        missing_fields=[f"revenue_by_year[{y}]" for y in sorted(years)],
    )


def provenance_coverage(ledger: dict) -> dict:
    """
    ledger 1건의 출처 커버리지를 요약한다.

    기존 34종목은 `data_sources` 자유문자열만 있어 전부 `PROVENANCE_UNKNOWN`이
    나온다 - 그게 정확한 현재 상태이며, 소급 생성하지 않는다(§6).
    """
    prov = (ledger.get("meta") or {}).get("provenance")
    legacy = (ledger.get("inputs") or {}).get("data_sources") or []

    if not prov:
        return {
            "ticker": ledger["meta"]["ticker"],
            "status": PROVENANCE_UNKNOWN,
            "n_covered": 0,
            "legacy_data_sources": legacy,
            "note": (
                "값 단위 출처 기록이 없다(v3.50 이전 분석). data_sources 자유문자열만 "
                "있어 '어느 공시의 어느 값인지'는 알 수 없다. **소급 생성하지 않는다** - "
                "지금 조회한 값을 그때 값인 양 붙이면 허위 출처가 된다."
            ),
        }

    return {
        "ticker": ledger["meta"]["ticker"],
        "status": prov.get("status"),
        "n_covered": prov.get("n_covered", 0),
        "n_missing": prov.get("n_missing", 0),
        "missing_fields": prov.get("missing_fields", []),
        "retrieval_date": prov.get("retrieval_date"),
        "legacy_data_sources": legacy,
    }
