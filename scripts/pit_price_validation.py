"""
pit_price_validation.py (2026-08-29) — PIT 백테스트의 **성적표**를 만든다.

`scripts/pit_backtest.py`가 T0 시점 원자료만으로 재현한 판정(flagged =
"저평가 가능성", not flagged = 나머지)을, T0 이후 **실제 주가 수익률**과
대조한다. 이 저장소가 만들어진 이래 "계산이 현실과 맞았는가"에 답하는
첫 산출물이다.

## 표본을 고르지 않는다

T0에 채점된 **128종목 전부**를 쓴다(flagged 21 + not flagged 107). 부분
표본을 뽑으면 "어느 종목을 골랐나"가 결과를 좌우할 수 있어, 아예 고르는
행위를 없앴다. 128은 `broad_screen.py`가 쓰는 것과 같은 유니버스 앞부분
300종목에서 T0 기준 재무데이터가 확보된 전부이며, 그 순서는 SEC 티커
목록 순서라 성과와 무관하다.

## 가격 출처 - 왜 stockanalysis.com인가

가격 데이터를 자동으로 받을 수 있는 경로를 실측으로 좁힌 결과다:
- Yahoo Finance(`query1.finance.yahoo.com`) · Stooq: robots.txt가
  `User-agent: *` / `Disallow: /`로 **전체 봇 차단**(2026-08-29 원문 확인).
  이 프로젝트가 Finviz에서 세운 원칙("robots.txt를 직접 확인하고 지킨다")상
  자동화 경로로 쓸 수 없다.
- Alpha Vantage: 무료 25회/일이라 128종목에 애초에 부족하다.
- FMP: `chart` 엔드포인트의 날짜 범위 파라미터가 유료 플랜 전용.
- **stockanalysis.com**: robots.txt가 `/e/`·`/p/`만 금지하고 나머지를
  허용한다(2026-08-29 원문 확인). 이 저장소 `source_registry`에 이미
  등록된 출처이기도 하다(ETF 엔진이 v3.33부터 사용 중).

⚠️ **교차확인을 하고 쓴다**: AAPL 2021-06 배당조정 종가가 이 출처에서
133.387, FMP `historical-price-eod-dividend-adjusted`에서 133.39로 일치했다.
TYL SBC 3배 오류(2차 출처를 검증 없이 인용)의 재발을 막기 위한 절차다.

## 수익률 정의

`a`(배당·분할 조정 종가) 기준 단순 보유수익률:
    return = a(최신월) / a(T0월) - 1
배당 재투자가 반영된 총수익이며, 거래비용·세금은 반영하지 않는다.

⚠️ **생존편향 주의**: T0 이후 상장폐지·인수합병된 종목은 이 출처에서
시계열이 끊기거나 사라진다. 그런 종목은 `unavailable`로 남기고 **수익률
0%나 평균값으로 채우지 않는다**(데이터 없음을 유리한 값으로 오독하지
않는다는 이 프로젝트의 반복 원칙). 확보 실패 건수를 반드시 함께 읽을 것.
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request

_HERE = os.path.dirname(os.path.abspath(__file__))
REPORTS_DIR = os.path.join(os.path.dirname(_HERE), "reports", "pit_backtest")

API = "https://stockanalysis.com/api/symbol/s/{sym}/history?range=10Y&period=Monthly"
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/120 Safari/537.36")

# 폴라이트 딜레이. robots.txt에 Crawl-delay 지시자는 없지만, 무료 공개
# 서비스를 128회 연속 호출하므로 자발적으로 간격을 둔다(SEC 8req/s를
# 스스로 낮춰 잡은 것과 같은 태도).
REQUEST_INTERVAL_SEC = 0.7

# stockanalysis.com의 심볼 표기가 SEC 티커와 다른 경우.
SYMBOL_OVERRIDES = {"BRK-B": "BRK.B", "BF-B": "BF.B"}


def log(msg):
    print(msg, flush=True)


# 가격 시계열 디스크 캐시. **여러 T0를 검증하려면 필수다** - 같은 티커의
# 10년 월봉을 T0마다 다시 받으면 무료 공개 서비스를 몇 배로 두드리게 되고,
# 재현 테스트 자체가 비싸져서 "T0 하나만 보고 결론내는" 함정에 빠진다.
# 월봉이라 하루 단위로 안 변하므로 세션 내 캐시는 안전하다.
CACHE_DIR = os.path.join(os.path.dirname(_HERE), ".cache", "prices")


def fetch_monthly_adjusted(ticker, use_cache=True):
    """티커 -> {'YYYY-MM': 조정종가}. 실패하면 (None, 사유)."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    cache_path = os.path.join(CACHE_DIR, f"{ticker}.json")
    if use_cache and os.path.exists(cache_path):
        with open(cache_path, encoding="utf-8") as f:
            cached = json.load(f)
        if cached.get("series"):
            return cached["series"], None
        return None, cached.get("error") or "캐시된 실패"

    sym = SYMBOL_OVERRIDES.get(ticker, ticker)
    url = API.format(sym=urllib.parse.quote(sym.lower()))
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except Exception as e:  # noqa: BLE001 - 사유를 살려 보낸다(v3.68 원칙)
        return None, f"조회 실패: {e!r}"

    raw = payload.get("data")
    if isinstance(raw, dict):
        raw = raw.get("data")
    if not raw:
        err = "가격 시계열 없음(상장폐지·인수합병·심볼 변경 가능)"
        _write_cache(cache_path, None, err)
        return None, err

    out = {}
    for row in raw:
        t, adj = row.get("t"), row.get("a")
        if t and adj:
            out[t[:7]] = float(adj)
    if not out:
        err = "조정종가 파싱 실패"
        _write_cache(cache_path, None, err)
        return None, err
    _write_cache(cache_path, out, None)
    return out, None


def _write_cache(path, series, error):
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"series": series, "error": error}, f)


def holding_return(series, t0_month):
    """T0 월 -> 최신 월 보유수익률. T0 이전 상장이면 (None, 사유)."""
    if t0_month not in series:
        return None, None, None, f"T0({t0_month}) 시점 가격 없음(상장이 T0보다 늦음)"
    latest_month = max(series)
    if latest_month <= t0_month:
        return None, None, None, "T0 이후 가격이 없다(시계열 중단)"
    p0, p1 = series[t0_month], series[latest_month]
    if p0 <= 0:
        return None, None, None, f"T0 가격이 {p0}"
    return (p1 / p0 - 1) * 100, p0, p1, None


def run(backtest_path, benchmark="SPY"):
    with open(backtest_path, encoding="utf-8") as f:
        bt = json.load(f)
    t0 = bt["as_of"]
    t0_month = t0[:7]

    groups = {
        "flagged": list(bt["passed_tickers"]),
        "not_flagged": list(bt["not_passed_tickers"]),
    }
    results, unavailable = {"flagged": [], "not_flagged": []}, []
    total = sum(len(v) for v in groups.values())
    done = 0

    for group, tickers in groups.items():
        for ticker in tickers:
            done += 1
            cached = os.path.exists(os.path.join(CACHE_DIR, f"{ticker}.json"))
            series, err = fetch_monthly_adjusted(ticker)
            if not cached:
                time.sleep(REQUEST_INTERVAL_SEC)
            if series is None:
                unavailable.append({"ticker": ticker, "group": group, "reason": err})
                continue
            ret, p0, p1, err = holding_return(series, t0_month)
            if ret is None:
                unavailable.append({"ticker": ticker, "group": group, "reason": err})
                continue
            results[group].append({
                "ticker": ticker, "t0_adj_close": p0,
                "latest_month": max(series), "latest_adj_close": p1,
                "return_pct": ret,
            })
            if done % 25 == 0:
                log(f"[price] 진행 {done}/{total}")

    bench = None
    series, err = fetch_monthly_adjusted(benchmark)
    if series:
        ret, p0, p1, err2 = holding_return(series, t0_month)
        if ret is not None:
            bench = {"ticker": benchmark, "t0_adj_close": p0,
                     "latest_adj_close": p1, "return_pct": ret}

    return {
        "as_of_t0": t0,
        "validated_at": __import__("datetime").date.today().isoformat(),
        "price_source": "stockanalysis.com (배당·분할 조정 월봉 종가)",
        "return_definition": "a(최신월)/a(T0월)-1, 배당 재투자 포함, 거래비용·세금 미반영",
        "benchmark": bench,
        "n_flagged": len(results["flagged"]),
        "n_not_flagged": len(results["not_flagged"]),
        "n_unavailable": len(unavailable),
        "flagged": sorted(results["flagged"], key=lambda r: -r["return_pct"]),
        "not_flagged": sorted(results["not_flagged"], key=lambda r: -r["return_pct"]),
        "unavailable": unavailable,
    }


def main():
    import argparse
    ap = argparse.ArgumentParser(description="PIT 백테스트 성적표(실현 수익률 대조)")
    ap.add_argument("--backtest", required=True, help="pit_backtest_*.json 경로")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    result = run(args.backtest)
    out = args.out or os.path.join(
        REPORTS_DIR, f"pit_returns_{result['as_of_t0']}.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    log(f"[price] 저장: {out}")
    log(f"[price] flagged {result['n_flagged']} / not_flagged "
        f"{result['n_not_flagged']} / 확보실패 {result['n_unavailable']}")


if __name__ == "__main__":
    main()
