"""
Filing Dates (v3.49 신규, 2026-08-15) - SEC 원자료에서 **실제 제출일**을 얻는다.

## 왜 필요한가 - v3.47이 만든 수단에 데이터를 공급한다

v3.47에서 Point-in-Time 필드(`analysis_as_of` / `filing_dates_by_year`)와
검증 규칙(`filing_date <= analysis_as_of`)을 배선했지만, **실제로 채운 종목이
0건**이었다. 채울 수단이 없었기 때문이다.

v3.47은 "과거 filing_date는 알 수 없으니 추정해 넣지 말라"고 못박았는데,
그 문장에서 금지된 것은 **추정**이지 **조회**가 아니다. SEC XBRL
companyfacts API의 각 항목에는 `filed` 필드로 그 수치가 처음 공시된 날짜가
그대로 들어 있다 - 이건 1차 자료의 사실이지 추측이 아니다.

이 프로젝트는 ONON에서 이미 이 경로를 확립했다(2차 출처끼리 어긋났을 때
companyfacts로 확정). 같은 API에서 재무수치와 제출일을 함께 가져오므로
출처가 갈릴 여지도 없다.

## 무엇을 '그 회계연도의 제출일'로 보는가

같은 회계연도 수치는 여러 연차보고서에 반복 등장한다(FY2023 매출은 FY2023
10-K에도, FY2025 10-K에도 비교표로 실린다). PIT에서 의미 있는 것은 **그
수치가 처음 공개된 날**이므로 **최초 제출일(min)** 을 택한다.

세금계산서 같은 부분기간이 섞이지 않도록 **연간 구간(약 330~400일)**만 본다.
분기(10-Q)는 애초에 제외한다.

## ⚠️ 이 모듈이 보장하지 않는 것 - 재작성(restatement)

`filing_date <= analysis_as_of`를 통과해도, **ledger에 들어간 숫자가 그 시점의
숫자였다는 보장은 아니다.** 재무데이터는 분석 시점에 Alpha Vantage 등에서
가져왔고, 그 값이 이후 재작성됐다면 지금 조회한 값과 다를 수 있다.

즉 이 모듈은 "그 시점에 **공시돼 있었는가**"만 답한다. "분석이 그 시점 값을
**썼는가**"는 별개 질문이고, 그건 원자료 스냅샷을 저장해야 답할 수 있다
(`docs/change_plan.md` C-09 Provenance - 여전히 DEFERRED).

그래서 이 모듈로 과거 ledger를 `PIT_VALID`로 소급 표시하지 않는다. 대신
**미래정보를 쓴 흔적이 있는지**(filing_date > analysis_as_of)를 감사하는
용도로 쓴다 - 그건 이 데이터만으로 확정적으로 잡히는 진짜 결함이다.
"""

import json
import os
import urllib.error
import urllib.request

from engine.data.governance.source_registry import rate_limiter_for

SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SEC_FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"

# SEC가 요구하는 식별 가능한 User-Agent(없으면 403). 환경변수로 덮어쓸 수 있다.
DEFAULT_USER_AGENT = os.environ.get(
    "SEC_USER_AGENT", "IRS Research chlalsrl1203@gmail.com"
)

# 연차보고서 서식. 국내 발행사는 10-K, 외국 발행사는 20-F(SAP·BABA·ONON 등).
ANNUAL_FORMS = ("10-K", "10-K/A", "20-F", "20-F/A", "40-F")

# 연간 구간으로 인정할 일수 범위. 52/53주 회계연도와 전환기를 포용하되
# 반기·분기가 섞이지 않을 만큼은 좁게 잡는다.
_MIN_ANNUAL_DAYS = 330
_MAX_ANNUAL_DAYS = 400


def _http_json(url: str, user_agent: str = None) -> dict:
    # P0-01(2026-08-19): SEC 공식 상한은 10 req/s인데(sec.gov/os/webmaster-faq)
    # 이 함수에는 **레이트리밋이 아예 없었다.** 34종목 PIT 감사처럼 반복 조회하는
    # 경로에서 차단당하면 분석 자체가 중단되므로, 등록부가 아는 상한(SEC 8/s)을
    # 강제한다. 등록부에 없는 호스트는 보수적 기본값(2/s)이 걸린다.
    # SOURCE: https://github.com/simonlin1212/global-stock-data (per-domain limiter)
    rate_limiter_for(url).wait()
    req = urllib.request.Request(
        url, headers={"User-Agent": user_agent or DEFAULT_USER_AGENT}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def ticker_to_cik(ticker: str, user_agent: str = None) -> str:
    """
    티커 -> 10자리 CIK. 찾지 못하면 None을 돌려준다(추측하지 않는다).
    """
    data = _http_json(SEC_TICKERS_URL, user_agent)
    want = ticker.strip().upper()
    for row in data.values():
        if row["ticker"].upper() == want:
            return str(row["cik_str"]).zfill(10)
    return None


def fetch_company_facts(cik: str, user_agent: str = None) -> dict:
    """CIK -> companyfacts JSON 원본."""
    try:
        return _http_json(SEC_FACTS_URL.format(cik=str(cik).zfill(10)), user_agent)
    except urllib.error.HTTPError as e:
        raise RuntimeError(
            f"SEC companyfacts 조회 실패(CIK {cik}): HTTP {e.code}. "
            f"CIK가 맞는지, User-Agent가 설정됐는지 확인할 것."
        ) from e


def _days_between(start: str, end: str) -> int:
    from datetime import date

    a = date.fromisoformat(start)
    b = date.fromisoformat(end)
    return (b - a).days


def annual_filing_dates(facts: dict) -> dict:
    """
    companyfacts -> {회계연도(int): 최초 제출일(ISO str)}.

    **순수 함수다**(네트워크 없음) - 저장된 JSON으로 테스트할 수 있다.

    회계연도는 연간 구간의 **종료일 연도**로 정한다. 예를 들어 2026-01-31에
    끝나는 회계연도는 FY2026으로 잡히는데, 이는 이 프로젝트의 ledger가
    `revenue_by_year` 키를 매기는 방식(회계연도 종료 기준)과 같다.

    ⚠️ 태그를 하나로 고정하지 않고 **모든 태그를 훑는다.** 제출일은 태그가
    아니라 '그 공시'의 속성이고, 회사·업종마다 쓰는 매출 태그가 달라
    (us-gaap vs ifrs-full, Revenues vs RevenueFromContract...) 하나를 고르면
    조용히 빈 결과가 나온다.
    """
    earliest = {}
    for taxonomy in (facts.get("facts") or {}).values():
        for tag_data in taxonomy.values():
            for entries in (tag_data.get("units") or {}).values():
                for e in entries:
                    if e.get("form") not in ANNUAL_FORMS:
                        continue
                    start, end, filed = e.get("start"), e.get("end"), e.get("filed")
                    if not (start and end and filed):
                        continue
                    try:
                        span = _days_between(start, end)
                    except ValueError:
                        continue
                    if not _MIN_ANNUAL_DAYS <= span <= _MAX_ANNUAL_DAYS:
                        continue
                    fy = int(end[:4])
                    # 처음 공개된 날이 PIT에서 의미 있는 날짜다
                    if fy not in earliest or filed < earliest[fy]:
                        earliest[fy] = filed
    return dict(sorted(earliest.items()))


def filing_dates_for_ticker(ticker: str, user_agent: str = None) -> dict:
    """
    티커 하나에 대해 {회계연도: 최초 제출일}을 조회한다.

    CIK를 찾지 못하면 `{}`를 돌려준다 - 없는 것을 있는 것처럼 만들지 않는다.
    """
    cik = ticker_to_cik(ticker, user_agent)
    if cik is None:
        return {}
    return annual_filing_dates(fetch_company_facts(cik, user_agent))


def pit_inputs_for(ticker: str, analysis_as_of: str, fiscal_years,
                   user_agent: str = None) -> dict:
    """
    새 분석에서 **한 줄로** PIT 필드를 채우기 위한 헬퍼.

        from engine.filing_dates import pit_inputs_for
        inputs = AnalysisInputs(..., **pit_inputs_for("BSX", "2026-08-15",
                                                      revenue_by_year))

    반환: `{"analysis_as_of": ..., "filing_dates_by_year": {...}}` 또는
    최근 회계연도 제출일을 못 찾았으면 `{"analysis_as_of": ...}`만.

    ⚠️ **못 찾은 것을 채워 넣지 않는다.** `AnalysisInputs`는
    `filing_dates_by_year`에 최근 회계연도가 반드시 있어야 한다고 요구하는데
    (그 해가 fcf0를 결정하므로), 그걸 못 구했으면 필드 자체를 빼서
    `PIT_UNKNOWN`으로 정직하게 떨어지게 한다. 억지로 채우면 "검증한 척"이 된다.

    이 프로젝트는 문서로만 둔 규칙이 무력화된 사례를 이미 네 번 겪었다
    (run_self_check·confidence_score·claim/lock·cross_check_prior_record).
    "새 분석에서 PIT를 채우자"를 다섯 번째로 만들지 않으려면 한 줄이어야 한다.
    """
    years = sorted(int(y) for y in fiscal_years)
    filing_dates = filing_dates_for_ticker(ticker, user_agent)

    latest_fy = max(years) if years else None
    if latest_fy is None or latest_fy not in filing_dates:
        return {"analysis_as_of": analysis_as_of}

    return {
        "analysis_as_of": analysis_as_of,
        # 분석에 실제로 쓴 연도만 넘긴다(불필요한 연도까지 넣으면 검증 대상이
        # 흐려진다). 못 찾은 연도는 빠지며, 그 사실은 PIT 평가에서 드러난다.
        "filing_dates_by_year": {y: filing_dates[y] for y in years
                                 if y in filing_dates},
    }


def check_lookahead(filing_dates: dict, analysis_as_of: str,
                    fiscal_years_used) -> dict:
    """
    분석에 쓴 회계연도들이 분석일 **이전에** 공시됐는지 확인한다.

    반환값:
      violations   - filing_date > analysis_as_of 인 항목(= 미래정보 사용 흔적)
      unknown_years - 제출일을 못 찾은 연도(추측하지 않고 그대로 남긴다)

    ⚠️ violations가 비었다고 `PIT_VALID`는 아니다(모듈 docstring의 재작성 한계).
    이 함수는 **확정적으로 잡히는 위반만** 보고한다.
    """
    violations, unknown = [], []
    for fy in sorted(fiscal_years_used):
        filed = filing_dates.get(int(fy))
        if filed is None:
            unknown.append(int(fy))
            continue
        if filed > analysis_as_of:
            violations.append({
                "fiscal_year": int(fy),
                "filed": filed,
                "analysis_as_of": analysis_as_of,
                "days_after_analysis": _days_between(analysis_as_of, filed),
            })
    return {
        "violations": violations,
        "unknown_years": unknown,
        "checked_years": sorted(int(y) for y in fiscal_years_used),
    }
