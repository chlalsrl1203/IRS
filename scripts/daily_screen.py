"""
daily_screen.py (2026-08-22) — 자동 아침 스크리닝의 "기계적인 부분"만 담당한다.

왜 필요한가:
  1차(넓게 거르기)는 Finviz 화이트리스트 프리셋(ta_newlow·it_latestbuys 등,
  engine/data/governance/source_registry.py의 finviz 항목 참고)에서 나온
  티커 목록을 받는다. 이 스크립트는 그 목록에 대해 **SEC 원자료로 실제
  재무수치를 계산**해 engine/screener.py의 검증된 기준(Realistic Growth
  ≥8% / Implied Growth ≤5.5%)으로 1차 필터링한다.

  이 단계는 LLM 판단이 필요 없는 순수 계산이라 스크립트로 뺐다 - 클로드
  세션이 종목마다 재무제표를 읽고 CAGR을 암산하게 하면 그게 토큰 낭비의
  본체다. 정성적 판단("공포과잉 vs 진짜나빠짐")은 이 스크립트가 하지
  않는다 - screener.py 문서가 이미 명시한 대로 그건 사람/세션이 할 일이다.

사용법 (2단계):
  1) SEC에서 재무수치만 가져오기(시가총액 제외, 무제한·무료):
       python3 scripts/daily_screen.py fetch AAPL MSFT ... > candidates_raw.json

  2) 시가총액(Alpha Vantage 등에서 별도로 가져온 값)을 채워서 최종 판정:
       python3 scripts/daily_screen.py score candidates_raw.json market_caps.json

  market_caps.json 형식: {"AAPL": 3500000000000, "MSFT": ...}
  (raw USD, SEC 재무수치와 같은 단위여야 함 - 천/백만 단위 아님)

net_debt_to_ebitda 기본값 0.406은 ledger 34종목 실측 중앙값이다(2026-08-22
계산, screener.py의 ASSUMED_* 상수들과 동일한 "관측 중앙값을 기본값으로"
원칙 - 임의로 지어낸 값이 아니다). 시가총액 조회에 쓴 API로 실제 부채/EBITDA를
같이 확보했다면 그 값을 market_caps.json에 "TICKER__ndte": 0.55 형태로 넣으면
기본값 대신 쓴다.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.data.providers.sec import SecCompanyFactsProvider
from engine.screener import Candidate, format_table, screen_all

CACHE_DIR = os.environ.get(
    "SEC_CACHE_DIR",
    "/tmp/claude-0/-home-user-IRS/1fb7a46a-ee0b-5b39-806f-ff7ee862da26/scratchpad/secfacts",
)
# ledger/ 34종목 실측 중앙값(2026-08-22) - screener.py ASSUMED_* 상수와 동일 원칙
DEFAULT_NDTE = 0.406


def _cached_facts(ticker):
    os.makedirs(CACHE_DIR, exist_ok=True)
    path = os.path.join(CACHE_DIR, f"{ticker}.json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    from engine.filing_dates import fetch_company_facts, ticker_to_cik

    ua = "IRS daily screener demo@example.com"
    cik = ticker_to_cik(ticker, ua)
    if not cik:
        return None
    facts = fetch_company_facts(cik, ua)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(facts, f)
    return facts


def _cagr(start, end, years):
    if start <= 0 or end <= 0:
        return None
    return (end / start) ** (1 / years) - 1


def _worst_yoy(series_by_year):
    ys = sorted(series_by_year)
    if len(ys) < 2:
        return None
    return min(series_by_year[ys[i]] / series_by_year[ys[i - 1]] - 1
                for i in range(1, len(ys)) if series_by_year[ys[i - 1]] != 0)


def fetch_sec_fields(ticker, retrieved_at):
    """SEC에서 매출·OCF·capex 6개년(5y CAGR용)을 가져와 screener 입력 필드를 만든다."""
    facts = _cached_facts(ticker)
    if facts is None:
        return None, ["companyfacts 조회 실패(CIK 매핑 안 됨 또는 네트워크 오류)"]

    import datetime
    this_year = int(retrieved_at[:4])
    years = list(range(this_year - 6, this_year))

    provider = SecCompanyFactsProvider(
        purpose="internal_research",
        fetch_facts=lambda cik, ua=None: facts,
        resolve_cik=lambda t, ua=None: "unused",
    )
    result = provider.fetch_annual_financials(
        ticker, metrics=("revenue", "operating_cashflow", "capex"),
        fiscal_years=years, retrieved_at=retrieved_at,
    )
    by_metric = {}
    for f in result.facts:
        by_metric.setdefault(f.metric, {})[f.fiscal_year] = f.value

    rev = by_metric.get("revenue", {})
    ocf = by_metric.get("operating_cashflow", {})
    capex = by_metric.get("capex", {})
    limitations = list(result.limitations)

    common_years = sorted(set(rev) & set(ocf) & set(capex))
    if len(common_years) < 2:
        limitations.append(
            f"매출·OCF·capex 공통 확보 연도가 {len(common_years)}개뿐 - CAGR 계산 불가")
        return None, limitations

    y0, y1 = common_years[0], common_years[-1]
    span = y1 - y0
    if span < 1:
        limitations.append("CAGR 계산에 필요한 최소 구간(1년) 미확보")
        return None, limitations

    fcf_series = {y: ocf[y] - capex[y] for y in common_years}
    if fcf_series[y0] <= 0 or fcf_series[y1] <= 0:
        # v3.19 가드와 동일 원리: 시작·끝 어느 쪽이든 음수면 CAGR이 정의되지 않는다.
        limitations.append(
            f"FCF 기준연도({y0}) 또는 최종연도({y1})가 0 이하 - CAGR 계산 불가"
            f"(FY{y0}={fcf_series[y0]:,.0f}, FY{y1}={fcf_series[y1]:,.0f})")
        return None, limitations

    fields = {
        "revenue_cagr_5y": _cagr(rev[y0], rev[y1], span),
        "fcf_cagr_5y": _cagr(fcf_series[y0], fcf_series[y1], span),
        "fcf0": fcf_series[y1],
        "worst_yoy_revenue": _worst_yoy({y: rev[y] for y in common_years}),
        "base_year": y0, "final_year": y1, "span_years": span,
    }
    if fields["revenue_cagr_5y"] is None or fields["fcf_cagr_5y"] is None:
        limitations.append("CAGR 시작값이 0 이하 - 계산 불가")
        return None, limitations
    return fields, limitations


def cmd_fetch(tickers):
    import datetime
    today = datetime.date.today().isoformat()
    out = {"retrieved_at": today, "candidates": {}, "skipped": {}}
    for t in tickers:
        t = t.upper()
        fields, limitations = fetch_sec_fields(t, today)
        if fields is None:
            out["skipped"][t] = limitations
        else:
            fields["limitations"] = limitations
            out["candidates"][t] = fields
    print(json.dumps(out, ensure_ascii=False, indent=2))


def cmd_score(raw_path, market_caps_path):
    with open(raw_path, encoding="utf-8") as f:
        raw = json.load(f)
    with open(market_caps_path, encoding="utf-8") as f:
        caps = json.load(f)

    candidates = []
    missing_cap = []
    for ticker, fields in raw["candidates"].items():
        mc = caps.get(ticker)
        if mc is None or mc <= 0:
            missing_cap.append(ticker)
            continue
        ndte = caps.get(f"{ticker}__ndte", DEFAULT_NDTE)
        candidates.append(Candidate(
            ticker=ticker, name=ticker, market_cap=mc, fcf0=fields["fcf0"],
            revenue_cagr_5y=fields["revenue_cagr_5y"],
            fcf_cagr_5y=fields["fcf_cagr_5y"],
            net_debt_to_ebitda=ndte,
            worst_yoy_revenue=fields["worst_yoy_revenue"] or 0.0,
            note=f"FY{fields['base_year']}->FY{fields['final_year']} "
                 f"({fields['span_years']}y), ndte={'실측' if f'{ticker}__ndte' in caps else '중앙값기본값'}",
        ))

    results = screen_all(candidates)
    passed = [r for r in results if r.passed]

    print(format_table(results))
    print(f"\n총 {len(candidates)}종목 채점, {len(passed)}종목 통과")
    if missing_cap:
        print(f"시가총액 미확보로 채점 제외: {missing_cap}")
    if raw.get("skipped"):
        print(f"SEC 재무데이터 확보 실패로 애초에 제외: {list(raw['skipped'])}")

    out = {
        "scored_at": raw["retrieved_at"],
        "passed": [
            {"ticker": r.candidate.ticker, "tier": r.tier,
             "fcf_yield": r.fcf_yield, "implied_growth_est": r.implied_growth_est,
             "realistic_growth_est": r.realistic_growth_est,
             "expectation_gap_est": r.expectation_gap_est,
             "drs_est": r.drs_est, "note": r.candidate.note,
             "review_flags": r.review_flags}
            for r in passed
        ],
        "missing_market_cap": missing_cap,
        "sec_fetch_failed": raw.get("skipped", {}),
    }
    out_path = raw_path.replace(".json", "_scored.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"\n-> {out_path}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    if sys.argv[1] == "fetch":
        cmd_fetch(sys.argv[2:])
    elif sys.argv[1] == "score":
        cmd_score(sys.argv[2], sys.argv[3])
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
