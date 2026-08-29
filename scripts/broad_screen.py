"""
broad_screen.py (2026-08-29) — 34종목 손입력 큐를 넘어선 대규모 스크리닝.

## 왜 만들었나

이 프로젝트가 지금까지 다룬 종목은 전부 Trefis 52주 신저가 연재 등에서
사람이 손으로 골라온 34개뿐이었다(생존편향 있는 좁은 표본, CLAUDE.md에
이미 여러 번 기록됨). 미국 상장기업은 SEC 등록 기준 약 1만개다. 이 스크립트는
그 전체를 모집단으로 삼아 `engine.screener.screen()`을 그대로 돌린다.

**새 밸류에이션 로직은 0줄이다.** `engine.screener`/`engine.data.providers.sec`를
그대로 재사용한다 - Simplicity First, 중복 계산이 두 계산을 미묘하게
어긋나게 만든다는 이 프로젝트의 반복 교훈.

## 2단계 설계 - 시가총액 데이터 접근성을 실측해서 정한 구조

Alpha Vantage(무료 25회/일)로는 1만종목을 도저히 커버 못한다. 대안을 실측했다:

- **Yahoo Finance(query1.finance.yahoo.com)**: 가격 API는 인증 없이 작동하지만
  `robots.txt`가 `User-agent: *` / `Disallow: /`로 **전체 봇을 차단**한다
  (2026-08-29 원문 확인). Finviz 때 이미 세운 원칙("robots.txt로 자동화
  허용범위를 직접 확인할 것")을 그대로 지키면 이 경로는 못 쓴다.
- **Stooq**: 마찬가지로 `Disallow: /`(Bing/Google만 예외) + 실제로 JS 우회방지
  챌린지(SHA-256 proof-of-work)까지 걸려 있다 - 자동화 대상 아님.
- **SEC `EntityPublicFloat`**: 10-K 표지에 회사가 직접 보고하는 "비계열주주
  보유주식 시가총액". 1차자료·완전준수·무료·무제한(SEC 8req/s 안에서).
  한계는 `engine/data/providers/sec.py::public_float_by_year` docstring에
  명시(계열주주분 제외·최대 ~18개월 낡음·20-F는 대개 미보고).

그래서:
  **Stage 1**(이 스크립트, 전체 유니버스) - SEC만으로 revenue/OCF/capex +
  public_float을 받아 `screen()`을 전 종목에 돌린다. 8req/s로 1만종목이
  약 20~25분에 끝난다.
  **Stage 2**(daily_screen_ci.py의 기존 경로) - Stage 1 통과자만 정밀
  실시간 시총(Alpha Vantage)으로 재확인한다. 이 스크립트는 Stage 2를
  실행하지 않는다 - 통과자 목록만 낸다.

## Stage 1 결과를 읽을 때 반드시 기억할 것

`public_float`은 근사치다. 컷오프 경계에 있는 종목은 이 근사 오차로
놓치거나 잘못 통과시킬 수 있다 - "1만종목 중 0종목까지 정확히 걸러냈다"가
아니라 "1만종목을 수십~수백종목으로 좁히는 1차 거름망"으로 읽을 것.
"""
import datetime
import json
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))
sys.path.insert(0, _HERE)

from engine.data.providers.sec import (  # noqa: E402
    SecCompanyFactsProvider, public_float_from_facts,
)
from engine.deep_screen import _window_cagr  # noqa: E402
from engine.filing_dates import (  # noqa: E402
    DEFAULT_USER_AGENT, fetch_company_facts, full_ticker_universe,
)
from engine.screener import (  # noqa: E402
    Candidate, DEFAULT_NDTE, DEFAULT_RISK_FREE_RATE, screen_all,
)
from daily_screen_ci import SKIP_CATEGORIES, classify_skips  # noqa: E402

REPORTS_DIR = os.path.join(os.path.dirname(_HERE), "reports", "broad_screen")

# 순수 이름 기반 사전필터 - 정확하지 않다(펀드/신탁/ETF를 완벽히 못 거른다).
# 진짜 거름망은 다운스트림(재무제표 태그 자체가 없으면 자연히 탈락)이다.
# 이건 오직 **시간 절약용**이라 판정 정확도에 영향이 없다 - 걸러진 종목도
# 어차피 SEC 재무제표가 없어서 탈락했을 것들이다.
_JUNK_TITLE_RE = re.compile(
    r"\b(TRUST|FUND|ETF|ETN|DEPOSITARY|WARRANT|ACQUISITION CORP|SPAC|"
    r"L\.?P\.?|LTD PARTNERSHIP|NOTES?|UNIT INVESTMENT)\b", re.IGNORECASE)

# ⚠️ 첫 실측(2026-08-29, ASML)에서 실제로 잡힌 함정: `EntityPublicFloat`이
# **FY2009 값 단 하나만** 있는 종목이 있었다 - 외국발행사가 SEC 보고의무를
# 축소·중단하면 XBRL 태깅이 그 시점에서 멈춘다. `max(pf)`가 그 낡은 값을
# 조용히 "최신"으로 골라 시총 $10.4B(실제로는 수백B$)로 계산했고, 그 오류가
# ASML을 S등급 통과로 잘못 만들었다 - 파일럿 15종목 중 실제로 발생.
# **"최대 ~18개월"이라던 docstring의 근거는 정상 필자를 가정한 것**이었고,
# 비정상 필자는 걸러야 한다. 연 1회 보고(10-K)+보고지연을 감안해 2년을
# 컷오프로 둔다 - 임의값이 아니라 "정상적인 연간 공시 주기의 2배"라는
# 도메인 근거다(RESTATEMENT_MATERIAL·ENTITY_CHANGE_THRESHOLD와 같은 형태의
# 판단). 이 컷오프를 넘기면 낡은 게 아니라 **못 쓴다** - 근사치가 아니라
# 명백히 틀린 값이 되므로.
PUBLIC_FLOAT_STALE_YEARS = 2

# Stage 1 전용 스킵 사유 - daily_screen_ci.SKIP_CATEGORIES를 확장한다
# (그 목록을 직접 수정하지 않는다 - Stage 2 파이프라인의 분류에 영향을 주면
# 안 되므로 이 파일 안에서만 확장한다).
STAGE1_SKIP_CATEGORIES = SKIP_CATEGORIES + (
    ("시가총액 근사치(public_float) 미확보(20-F 외국발행사 등)",
     ("public_float 미확보",), False),
    ("시가총액 근사치(public_float) 낡음(SEC 보고의무 축소·중단 추정)",
     ("public_float 낡음",), False),
    # NVDA 파일럿 실측(2026-08-29): 5y CAGR 기준연도가 0 이하라 계산 자체가
    # 안 되는 경우(PODD/ONON/MU와 동일 유형, 이 프로젝트가 반복 관측한 프레임
    # 워크 부적합) - "0 이하"(daily_screen_ci의 다른 문구)와 안 겹치게 별도 라벨.
    ("5년 CAGR 계산 불가(PODD/ONON/MU형 프레임워크 부적합)",
     ("프레임워크 부적합",), False),
)


def log(msg):
    print(msg, flush=True)


def _classify_stage1(skipped):
    """daily_screen_ci.classify_skips와 같은 로직, Stage1 전용 카테고리로."""
    buckets = {}
    for ticker, limitations in skipped.items():
        text = " ".join(str(x) for x in (limitations or []) if x)
        label, is_infra = "기타·미분류", False
        for lbl, needles, infra in STAGE1_SKIP_CATEGORIES:
            if any(n in text for n in needles):
                label, is_infra = lbl, infra
                break
        buckets.setdefault((label, is_infra), []).append(ticker)
    return [(lbl, sorted(ts), infra) for (lbl, infra), ts in buckets.items()]


def prefilter_universe(universe):
    """이름 기반 사전필터(시간 절약용, 정확도 무관)."""
    kept, dropped = [], 0
    for row in universe:
        if _JUNK_TITLE_RE.search(row.get("title", "")):
            dropped += 1
            continue
        kept.append(row)
    return kept, dropped


def fetch_stage1_series(ticker, cik, retrieved_at, user_agent=None):
    """
    SEC에서 revenue/OCF/capex(5y CAGR용 6개년) + public_float을 받는다.

    ⚠️ companyfacts를 **티커당 딱 1회만** 요청한다 - 초판은 재무지표용
    (`SecCompanyFactsProvider`)과 public_float용(`public_float_by_year`)이
    각자 별도로 SEC를 호출해 요청량이 배로 늘었다(300종목 파일럿이 3분
    타임아웃을 넘김, 실측으로 발견). 한 번 받은 JSON을 두 파싱 경로에
    주입하는 것으로 고쳤다(`engine/data/providers/sec.py::
    public_float_from_facts` 참고).

    반환: (series_dict_or_None, [limitation, ...])
    series_dict: {"revenue_by_year", "operating_cashflow_by_year",
                  "capex_by_year", "public_float_by_year"}
    """
    ua = user_agent or DEFAULT_USER_AGENT
    try:
        facts_json = fetch_company_facts(cik, ua)
    except Exception as e:  # noqa: BLE001 - 사유를 살려 보낸다(v3.68 원칙)
        return None, [f"companyfacts 조회 실패(CIK {cik}): {e!r}"]

    provider = SecCompanyFactsProvider(
        user_agent=ua,
        fetch_facts=lambda c, u=None: facts_json,
        resolve_cik=lambda t, u=None: cik,
    )
    result = provider.fetch_annual_financials(
        ticker, metrics=("revenue", "operating_cashflow", "capex"),
        fiscal_years=None, retrieved_at=retrieved_at,
    )

    by_metric = {}
    for f in result.facts:
        by_metric.setdefault(f.metric, {})[f.fiscal_year] = f.value
    limitations = list(result.limitations)

    rev = by_metric.get("revenue", {})
    ocf = by_metric.get("operating_cashflow", {})
    capex = by_metric.get("capex", {})
    common_years = sorted(set(rev) & set(ocf) & set(capex))
    if len(common_years) < 6:
        limitations.append(
            f"매출·OCF·capex 공통 확보 연도가 {len(common_years)}개뿐 - "
            f"5년 CAGR에 최소 6개년 필요")
        return None, limitations

    pf = public_float_from_facts(facts_json)
    if not pf:
        limitations.append("public_float 미확보")
        return None, limitations

    latest_pf_year = max(pf)
    retrieved_year = int(retrieved_at[:4])
    if retrieved_year - latest_pf_year > PUBLIC_FLOAT_STALE_YEARS:
        limitations.append(
            f"public_float 낡음(최신값이 FY{latest_pf_year}로 {retrieved_year - latest_pf_year}년 "
            f"전 - SEC 보고의무 축소·중단 추정, 이 값으로 시총을 근사하면 안 됨)")
        return None, limitations

    series = {
        "revenue_by_year": {y: rev[y] for y in common_years},
        "operating_cashflow_by_year": {y: ocf[y] for y in common_years},
        "capex_by_year": {y: capex[y] for y in common_years},
        "public_float_by_year": pf,
    }
    return series, limitations


def build_candidate(ticker, name, series, rf=DEFAULT_RISK_FREE_RATE):
    """
    series -> screener.Candidate. market_cap은 public_float 중 가장 최근 연도값.

    ⚠️ net_debt_to_ebitda는 SEC 태그 미등록으로 실측 불가 - engine/deep_screen.py와
    동일하게 corpus 중앙값(DEFAULT_NDTE)으로 명시 대체한다(새 판단 아님, 기존
    확립된 관행 재사용).
    """
    rev = series["revenue_by_year"]
    ocf = series["operating_cashflow_by_year"]
    capex = series["capex_by_year"]
    pf = series["public_float_by_year"]

    common_years = sorted(set(rev) & set(ocf) & set(capex))
    final_year = common_years[-1]
    fcf_by_year = {y: ocf[y] - capex[y] for y in common_years}
    fcf0 = fcf_by_year[final_year]

    revenue_cagr_5y = _window_cagr(rev, final_year, 5)
    fcf_cagr_5y = _window_cagr(fcf_by_year, final_year, 5)
    if revenue_cagr_5y is None or fcf_cagr_5y is None:
        raise ValueError(
            f"{ticker}: 5년 CAGR 계산 불가(기준연도 값 <=0 - PODD/ONON 유형 "
            f"프레임워크 부적합)")

    worst_yoy = min(
        rev[common_years[i]] / rev[common_years[i - 1]] - 1
        for i in range(1, len(common_years))
        if rev[common_years[i - 1]] != 0
    )

    # ⚠️ fcf0<=0은 여기서 별도로 검사하지 않는다 - `_window_cagr`이 이미
    # end(=final_year 값=fcf0)<=0이면 None을 돌려주므로, 위 fcf_cagr_5y is
    # None 가드를 통과했다는 것 자체가 fcf0>0을 보장한다(도달 불가능한 분기를
    # 만들지 않는다 - 테스트로 이 사실을 확인했다). market_cap만 별도 검사한다
    # - public_float은 CAGR 가드를 거치지 않아 이론상 0/음수 원자료가 가능하다.
    market_cap_year = max(pf)
    market_cap = pf[market_cap_year]
    if market_cap <= 0:
        raise ValueError(f"{ticker}: 시총 근사치(public_float)가 0 이하 - Model N/A")

    return Candidate(
        ticker=ticker, name=name, market_cap=market_cap, fcf0=fcf0,
        revenue_cagr_5y=revenue_cagr_5y, fcf_cagr_5y=fcf_cagr_5y,
        net_debt_to_ebitda=DEFAULT_NDTE, worst_yoy_revenue=worst_yoy,
        note=f"public_float FY{market_cap_year} 기준(근사치, 최대 ~18개월 낡을 수 있음)",
    )


def run(limit=None, retrieved_at=None, user_agent=None):
    """
    전체 파이프라인. limit을 주면 유니버스 앞부분 N개만 처리한다(테스트/부분실행용,
    운영 자동화에서는 None으로 전체를 돈다).
    """
    retrieved_at = retrieved_at or datetime.date.today().isoformat()
    user_agent = user_agent or DEFAULT_USER_AGENT

    log("[Stage1] SEC 전체 티커 유니버스 조회 중...")
    universe = full_ticker_universe(user_agent)
    log(f"[Stage1] 원본 유니버스: {len(universe)}종목")

    kept, dropped = prefilter_universe(universe)
    log(f"[Stage1] 이름 사전필터: {dropped}종목 제외(펀드/신탁/ETF류 이름패턴) "
        f"-> {len(kept)}종목 시도")

    if limit:
        kept = kept[:limit]
        log(f"[Stage1] limit={limit} 적용 -> {len(kept)}종목만 처리")

    skipped, candidates = {}, []
    for i, row in enumerate(kept):
        ticker, cik, name = row["ticker"], row["cik"], row["title"]
        try:
            series, lim = fetch_stage1_series(ticker, cik, retrieved_at, user_agent)
            if series is None:
                skipped[ticker] = lim
                continue
            candidates.append(build_candidate(ticker, name, series))
        except Exception as e:  # noqa: BLE001 - 종목 하나의 실패가 전체를 막지 않는다
            skipped[ticker] = [repr(e)]
        if (i + 1) % 500 == 0:
            log(f"[Stage1] 진행 {i + 1}/{len(kept)} "
                f"(후보 {len(candidates)}, 제외 {len(skipped)})")

    log(f"[Stage1] SEC 재무계산 완료: 성공 {len(candidates)} / 제외 {len(skipped)}")
    results = screen_all(candidates)
    passed = [r for r in results if r.passed]
    log(f"[Stage1] 채점 {len(results)}종목 -> 통과 {len(passed)}종목")

    return {
        "retrieved_at": retrieved_at,
        "universe_total": len(universe),
        "prefiltered_out": dropped,
        "attempted": len(kept),
        "sec_ok": len(candidates),
        "sec_skipped": len(skipped),
        "scored": len(results),
        "passed": len(passed),
        "skip_breakdown": [
            {"label": lbl, "count": len(ts), "infra_failure": infra,
             "sample": ts[:10]}
            for lbl, ts, infra in sorted(_classify_stage1(skipped),
                                         key=lambda g: (not g[2], -len(g[1])))
        ],
        "passed_tickers": [
            {"ticker": r.candidate.ticker, "tier": r.tier,
             "expectation_gap_est": r.expectation_gap_est,
             "market_cap": r.candidate.market_cap, "note": r.candidate.note}
            for r in passed
        ],
    }


def main():
    import argparse
    ap = argparse.ArgumentParser(description="대규모 스크리닝(Stage 1, SEC 전용)")
    ap.add_argument("--limit", type=int, default=None,
                    help="유니버스 앞 N개만 처리(부분실행/테스트용)")
    ap.add_argument("--out", default=None, help="결과 JSON 저장 경로")
    args = ap.parse_args()

    result = run(limit=args.limit)
    out_path = args.out or os.path.join(
        REPORTS_DIR, f"broad_screen_{result['retrieved_at']}.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    log(f"[Stage1] 저장: {out_path}")
    log(json.dumps({k: v for k, v in result.items() if k != "skip_breakdown"},
                   ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
