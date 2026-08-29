"""
pit_backtest.py (2026-08-29) — 실제 과거 시점(T0) 데이터만으로 스크리닝을
재현하고, 그 판정이 실제 이후 성과와 관계있는지 정직하게 대조한다.

## 이게 왜 "Historical Replay 금지"에 안 걸리는가

2026-08-16 감사가 발동한 §66 STOP CONDITION은 **기존 ledger를 과거 시점으로
재라벨링**하는 것을 막았다 - ledger 값은 최신 판본(재작성 반영)이라 그걸
"그때 알았던 값"으로 위장하면 미래정보 오염이다(PHASE 5 실측: 재작성 기간
148건 중 101건이 최신판과만 일치).

이 스크립트는 다르다 - **ledger를 재사용하지 않는다.** SEC에서 `filed <= T0`
인 값만 새로 받는다(`engine/data/providers/sec.py`의 `as_of` 파라미터,
이번에 신설). 이건 "그때 실제로 공시돼 있던 원자료로 지금 막 계산"하는
것이지 "이미 계산해둔 결과를 과거인 척"하는 게 아니다 - PIT 인프라
(`filing_dates.py`/`check_lookahead`)가 애초에 이걸 위해 만들어졌었다.

## 표본 선택 - 결과를 보기 전에 정한다

`broad_screen.py`가 이미 쓴 것과 **같은 300종목**(SEC 유니버스 이름
사전필터 후 앞부분, 오늘 스크리닝 통과 여부와 무관하게 고정된 순서)을
그대로 재사용한다 - "T0에 뭐가 통과했는지 보고 표본을 고르는" 사후선택
편향을 원천 차단한다.

## 새 밸류에이션 로직 0줄

`broad_screen.build_candidate`·`engine.screener.screen_all`을 그대로
재사용한다. 이 스크립트가 새로 하는 일은 **입력을 T0로 truncate하는 것**뿐.

## 이 스크립트가 내는 것과 안 내는 것

낸다: T0 시점 판정(통과/미통과) 목록.
안 낸다: 실현수익률 대조 - 그건 실시간 시세가 필요해 별도 수동 단계(MCP)로
분리했다(이 스크립트는 시크릿·MCP 없이도 동작해야 한다).
"""
import datetime
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))
sys.path.insert(0, _HERE)

from engine.data.providers.sec import (  # noqa: E402
    SecCompanyFactsProvider, public_float_from_facts,
)
from engine.filing_dates import DEFAULT_USER_AGENT, fetch_company_facts  # noqa: E402
from engine.screener import screen_all  # noqa: E402

from broad_screen import (  # noqa: E402
    PUBLIC_FLOAT_STALE_YEARS, build_candidate, full_ticker_universe,
    prefilter_universe,
)

REPORTS_DIR = os.path.join(os.path.dirname(_HERE), "reports", "pit_backtest")

# companyfacts 디스크 캐시. **여러 T0를 검증하려면 필수다** - companyfacts
# 자체는 T0와 무관하게 동일하고(T0는 `filed<=as_of`로 truncate만 한다), 캐시가
# 없으면 T0 6개 × 티커 N개 = 6N회를 SEC에 요청하게 된다. 캐시가 있으면 N회다.
# 이게 없으면 "T0 하나만 보고 결론내는" 함정에 비용 때문에 구조적으로 빠진다
# (실제로 이 프로젝트가 T0=2021 하나만 보고 정반대 결론을 낼 뻔했다).
FACTS_CACHE_DIR = os.path.join(os.path.dirname(_HERE), ".cache", "companyfacts")


def log(msg):
    print(msg, flush=True)


def cached_company_facts(cik, user_agent=None):
    """companyfacts를 디스크 캐시 경유로 받는다. 실패하면 (None, 사유)."""
    os.makedirs(FACTS_CACHE_DIR, exist_ok=True)
    path = os.path.join(FACTS_CACHE_DIR, f"{cik}.json")
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f), None
        except json.JSONDecodeError:
            os.remove(path)  # 깨진 캐시는 버리고 다시 받는다
    try:
        facts = fetch_company_facts(cik, user_agent)
    except Exception as e:  # noqa: BLE001 - 사유를 살려 보낸다(v3.68 원칙)
        return None, f"companyfacts 조회 실패(CIK {cik}): {e!r}"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(facts, f)
    return facts, None


def fetch_pit_series(ticker, cik, as_of, user_agent=None, retrieved_at=None):
    """
    broad_screen.fetch_stage1_series와 동일 구조이나 **as_of로 truncate**한다 -
    `filed <= as_of`인 값만 쓴다(그 시점에 실제로 알 수 있었던 원자료).

    ⚠️ `retrieved_at`(이 코드를 실제로 실행한 오늘 날짜)과 `as_of`(재현하려는
    과거 시점 T0)를 혼동하지 않는다 - 초판에서 실제로 `retrieved_at=as_of`로
    잘못 넘겼다가(engine/data/providers/sec.py 자신의 docstring이 명시적으로
    경고한 바로 그 실수) 실행 전에 발견해 고쳤다. `retrieved_at`은 "이 코드를
    언제 돌렸는가"라는 감사기록이라 항상 실제 오늘이어야 한다.

    반환: (series_dict_or_None, [limitation, ...])
    """
    ua = user_agent or DEFAULT_USER_AGENT
    retrieved_at = retrieved_at or datetime.date.today().isoformat()
    facts_json, err = cached_company_facts(cik, ua)
    if facts_json is None:
        return None, [err]

    provider = SecCompanyFactsProvider(
        user_agent=ua,
        fetch_facts=lambda c, u=None: facts_json,
        resolve_cik=lambda t, u=None: cik,
    )
    result = provider.fetch_annual_financials(
        ticker, metrics=("revenue", "operating_cashflow", "capex"),
        fiscal_years=None, retrieved_at=retrieved_at, as_of=as_of,
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
            f"매출·OCF·capex 공통 확보 연도가 {len(common_years)}개뿐(T0={as_of} "
            f"기준) - 5년 CAGR에 최소 6개년 필요")
        return None, limitations

    pf = public_float_from_facts(facts_json, as_of=as_of)
    if not pf:
        limitations.append("public_float 미확보(T0 기준)")
        return None, limitations
    latest_pf_year = max(pf)
    if int(as_of[:4]) - latest_pf_year > PUBLIC_FLOAT_STALE_YEARS:
        limitations.append(
            f"public_float 낡음(T0={as_of} 기준 최신값이 FY{latest_pf_year})")
        return None, limitations

    return {
        "revenue_by_year": {y: rev[y] for y in common_years},
        "operating_cashflow_by_year": {y: ocf[y] for y in common_years},
        "capex_by_year": {y: capex[y] for y in common_years},
        "public_float_by_year": pf,
    }, limitations


def run(as_of, limit=None, user_agent=None):
    user_agent = user_agent or DEFAULT_USER_AGENT
    log(f"[PIT] T0={as_of} 기준 재구성 시작")

    universe = full_ticker_universe(user_agent)
    kept, dropped = prefilter_universe(universe)
    if limit:
        kept = kept[:limit]
    log(f"[PIT] 유니버스 {len(universe)} -> 사전필터 후 {len(kept)}종목 시도")

    skipped, candidates = {}, []
    for i, row in enumerate(kept):
        ticker, cik, name = row["ticker"], row["cik"], row["title"]
        try:
            series, lim = fetch_pit_series(ticker, cik, as_of, user_agent)
            if series is None:
                skipped[ticker] = lim
                continue
            candidates.append(build_candidate(ticker, name, series))
        except Exception as e:  # noqa: BLE001
            skipped[ticker] = [repr(e)]
        if (i + 1) % 100 == 0:
            log(f"[PIT] 진행 {i + 1}/{len(kept)} "
                f"(후보 {len(candidates)}, 제외 {len(skipped)})")

    results = screen_all(candidates)
    passed = [r for r in results if r.passed]
    log(f"[PIT] T0={as_of} 채점 {len(results)}종목 -> 통과(저평가 판정) {len(passed)}종목")

    not_passed = [r for r in results if not r.passed]
    return {
        "as_of": as_of,
        "generated_at": datetime.date.today().isoformat(),
        "universe_total": len(universe),
        "attempted": len(kept),
        "scored": len(results),
        "passed_tickers": sorted(
            [r.candidate.ticker for r in passed]),
        "not_passed_tickers": sorted(
            [r.candidate.ticker for r in not_passed]),
        "passed_detail": [
            {"ticker": r.candidate.ticker, "tier": r.tier,
             "expectation_gap_est": r.expectation_gap_est}
            for r in sorted(passed, key=lambda x: -x.expectation_gap_est)
        ],
    }


def main():
    import argparse
    ap = argparse.ArgumentParser(description="PIT 백테스트 - T0 재구성")
    ap.add_argument("--as-of", required=True, help="재구성할 과거 시점(YYYY-MM-DD)")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    result = run(as_of=args.as_of, limit=args.limit)
    out_path = args.out or os.path.join(
        REPORTS_DIR, f"pit_backtest_{args.as_of}.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    log(f"[PIT] 저장: {out_path}")
    print(json.dumps({k: v for k, v in result.items()
                      if k not in ("passed_detail", "not_passed_tickers")},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
