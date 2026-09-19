"""
engine/portfolio_track_record.py — 매수리스트(공식 포트폴리오)의 실제
가중 수익률을 추적한다 (2026-09-19).

## 왜 engine/track_record.py(v3.89)로는 부족한가

`track_record.py`는 **종목별** T0->현재 수익률을 잰다 - 각 ledger의
`price_at_analysis`를 그 종목만의 T0로 쓴다(종목마다 T0가 제각각이다:
ACGL은 2026-09-05, PGR은 2026-08-23...). 그 개별 수익률을 매수리스트
비중으로 가중평균해도 "이 포트폴리오를 실제로 샀다면 얼마인가"에는
답하지 못한다 - 진짜 살 수 있는 포트폴리오는 **하나의 공통 매수일**에서
시작해야 한다. 이 모듈이 재는 것은 그거다: 매수리스트가 발행된 날
(`generated_at`)을 유일한 진입일로 삼아, 그날 그 비중대로 샀다면 지금
얼마인지를 계산한다.

## 재사용 원칙 - 새 가격 조회/파싱 로직 0줄

`engine.track_record`의 `fetch_daily_series`/`price_on_or_before`를 그대로
쓴다(AST 테스트로 재구현 금지를 고정 - Simplicity First, "중복 구현이
두 계산을 미묘하게 어긋나게 만든다"는 이 프로젝트의 반복 교훈). 이 모듈이
추가하는 건 "여러 종목을 공통 진입일 기준으로 비중가중 합산"뿐이다.

## 병기, 자동판정 안 함(v3.42 원칙)

이 결과는 Gap·판정등급·Confidence·사이징 어디에도 되먹임되지 않는다
(AST 테스트로 고정 - `decide`/`judge`/`rebalance`류 공개 함수가 생기면
실패한다). `ledger/`·`portfolio/holdings.json`·`watchlist.json`·
`reports/buylist_*.json` 어디에도 쓰지 않는다 - 전부 읽기만 한다.

## MEASUREMENT_STATUS

`engine.track_record`와 동일한 라벨(`OBSERVATIONAL_NOT_INFERENTIAL`)을
그대로 재사용한다 - 새 라벨을 발명하면 두 모듈이 같은 성질을 다른
말로 부르게 되어, 어느 쪽이 더 신뢰할 만한지 오독될 수 있다. 관측기간이
포트폴리오 발행 이후일수뿐이라 벤치마크 대비 우위를 통계적으로
주장하지 않는다.

## 커버리지가 정직해야 하는 이유

18개 종목 중 일부가 가격 조회에 실패하면(상장폐지·심볼변경·API 장애)
그 비중만큼은 "수익률 0%"로 조용히 취급하지 않는다 - 그러면 손실 종목이
빠졌을 때 포트폴리오가 실제보다 좋아 보인다. 대신 `covered_weight`(실제
가중합산에 들어간 비중)를 그대로 드러내고, 그 커버리지 안에서만
정규화한 수익률을 낸다.
"""
import datetime
import glob
import json
import os
import re

from engine.track_record import fetch_daily_series, price_on_or_before

MEASUREMENT_STATUS = (
    "OBSERVATIONAL_NOT_INFERENTIAL - 실제 관측이지만 사전등록된 실험이 아니다. "
    "관측기간이 포트폴리오 발행 이후일수뿐이라 벤치마크 대비 우위를 통계적으로 "
    "주장하지 않으며, 판정·사이징·Confidence 어디에도 되먹임되지 않는다."
)

BUYLIST_GLOB = os.path.join("reports", "buylist_*.json")
_DATED_BUYLIST_RE = re.compile(r"buylist_\d{4}-\d{2}-\d{2}\.json$")
OUT_DIR = os.path.join("reports", "portfolio_track_record")
BENCHMARK_TICKER = "SPY"


def _is_dated_buylist(path):
    """
    publish_buylist 계열 스키마(`buylist_<날짜>.json`)만 채택한다.

    daily_brief.py가 2026-08-28에 접두어매칭(`buylist_`)만 쓰다가
    `buylist_boundary_review_2026-08-16.json`(경계검토 리포트, 전혀 다른
    스키마)을 공식 매수리스트로 잘못 골라 매수표가 전 종목 0%로 나온
    사고가 있었다 - 정규식으로 스키마를 좁혀 같은 함정을 피한다.
    """
    return bool(_DATED_BUYLIST_RE.search(os.path.basename(path)))


def load_latest_buylist(pattern=BUYLIST_GLOB):
    """가장 최근 날짜의 공식 매수리스트를 읽는다. 없으면 None."""
    candidates = sorted(p for p in glob.glob(pattern) if _is_dated_buylist(p))
    if not candidates:
        return None
    path = candidates[-1]
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    data = dict(data)
    data["_source_path"] = path
    return data


def fetch_inception_prices(tickers, inception_date, opener=None):
    """
    공통 진입일 기준 진입가를 종목별로 확보한다(순수 I/O 래퍼).

    실패는 조용히 넘어가지 않는다 - `errors`에 사유를 남기고, 그 종목은
    이후 가중합산에서 빠진다는 사실이 리포트에 그대로 드러난다.
    """
    prices, errors, series_cache = {}, {}, {}
    for ticker in tickers:
        series, err = fetch_daily_series(ticker, opener=opener)
        if err:
            errors[ticker] = err
            continue
        entry_date, bar = price_on_or_before(series, inception_date)
        if bar is None:
            errors[ticker] = f"진입일({inception_date}) 이전 가격 없음"
            continue
        prices[ticker] = {"entry_date": entry_date, "entry_adj": bar["adj"]}
        series_cache[ticker] = series
    return prices, errors, series_cache


def snapshot(buylist, as_of=None, opener=None, benchmark_ticker=BENCHMARK_TICKER):
    """
    현재 시점 가중 포트폴리오 수익률 스냅샷(순수 함수 - 네트워크는
    opener로만 들어온다).

    반환값은 저장·표시용 dict일 뿐 - Gap/판정/사이징 어디에도 이 값을
    되먹이지 않는다(호출부가 그렇게 쓰지 않는 한 이 함수 자체는 아무것도
    바꾸지 않는다 - 인자로 받은 `buylist`도 변경하지 않는다).
    """
    inception_date = buylist["generated_at"]
    positions = buylist["positions"]
    tickers = [p["ticker"] for p in positions]

    inception, errors, series_cache = fetch_inception_prices(
        tickers, inception_date, opener=opener)

    rows = []
    covered_weight = 0.0
    weighted_return_sum = 0.0
    weights_by_ticker = {}
    for p in positions:
        t = p["ticker"]
        if t not in inception:
            rows.append({"ticker": t, "weight": p["weight_final"],
                         "grade": p.get("grade"),
                         "error": errors.get(t, "진입가 미확보")})
            continue
        series = series_cache[t]
        latest_date = max(series)
        latest_bar = series[latest_date]
        entry_adj = inception[t]["entry_adj"]
        ret = (latest_bar["adj"] / entry_adj - 1.0) * 100.0
        w = p["weight_final"]
        rows.append({
            "ticker": t, "weight": w, "grade": p.get("grade"),
            "cluster": p.get("cluster"),
            "entry_date": inception[t]["entry_date"], "entry_adj": entry_adj,
            "latest_date": latest_date, "latest_adj": latest_bar["adj"],
            "return_pct": ret, "contribution_pct": ret * w,
        })
        covered_weight += w
        weighted_return_sum += ret * w
        weights_by_ticker[t] = w

    portfolio_return_pct = (weighted_return_sum / covered_weight
                             if covered_weight > 0 else None)

    bench_row, bseries, bench_entry_adj = None, None, None
    if benchmark_ticker:
        bseries, berr = fetch_daily_series(benchmark_ticker, opener=opener)
        if bseries:
            bdate, bbar = price_on_or_before(bseries, inception_date)
            if bbar:
                bench_entry_adj = bbar["adj"]
                blatest = max(bseries)
                bret = (bseries[blatest]["adj"] / bench_entry_adj - 1.0) * 100.0
                bench_row = {"ticker": benchmark_ticker, "entry_date": bdate,
                             "entry_adj": bench_entry_adj, "latest_date": blatest,
                             "latest_adj": bseries[blatest]["adj"],
                             "return_pct": bret}
        if bench_row is None:
            errors[benchmark_ticker] = berr or "벤치마크 가격 미확보"

    alpha_vs_benchmark_pct = None
    if portfolio_return_pct is not None and bench_row is not None:
        alpha_vs_benchmark_pct = portfolio_return_pct - bench_row["return_pct"]

    latest_dates = [r["latest_date"] for r in rows if "error" not in r]
    as_of_actual = max(latest_dates) if latest_dates else None
    days_held = None
    if as_of_actual is not None:
        days_held = (datetime.date.fromisoformat(as_of_actual)
                     - datetime.date.fromisoformat(inception_date)).days

    rows_sorted = sorted(
        (r for r in rows if "error" not in r),
        key=lambda r: r["contribution_pct"], reverse=True,
    ) + [r for r in rows if "error" in r]

    trajectory = _daily_trajectory(
        series_cache, inception, weights_by_ticker, covered_weight,
        bseries, bench_entry_adj,
    )

    return {
        "as_of": as_of or datetime.date.today().isoformat(),
        "as_of_actual_latest_bar": as_of_actual,
        "measurement_status": MEASUREMENT_STATUS,
        "return_definition": (
            "배당조정 종가 기준, 매수리스트 발행일(inception_date) 공통진입 "
            "가중바스켓 수익률. 개별 종목의 track_record.py T0 수익률(종목마다 "
            "T0가 다름)과는 다른 값이다."
        ),
        "portfolio_version": {
            "source_path": buylist.get("_source_path"),
            "generated_at": buylist.get("generated_at"),
            "n_positions": len(positions),
        },
        "inception_date": inception_date,
        "days_held": days_held,
        "n_positions": len(positions),
        "n_covered": sum(1 for r in rows if "error" not in r),
        "covered_weight": covered_weight,
        "uncovered_weight": max(0.0, 1.0 - covered_weight),
        "portfolio_return_pct": portfolio_return_pct,
        "benchmark": bench_row,
        "alpha_vs_benchmark_pct": alpha_vs_benchmark_pct,
        "rows": rows_sorted,
        "errors": errors,
        "trajectory": trajectory,
    }


def _daily_trajectory(series_cache, inception, weights_by_ticker, covered_weight,
                       bseries, bench_entry_adj):
    """
    진입일부터 오늘까지 **매일**의 가중 포트폴리오 지수(진입일=100)를
    계산한다 - `snapshot()`이 이미 받아온 `series_cache`/`bseries`를 그대로
    쓴다(추가 네트워크 요청 0건). 첫 스냅샷부터 두 점(진입/오늘)이 아니라
    실제 궤적을 보여주기 위함이다.

    `price_on_or_before`(재사용)를 날짜마다 다시 부르는 것도 의도적이다 -
    거래일마다 값이 있는 종목만 있는 게 아니라(상장폐지·조회 지연 등),
    "그 날짜에 실제로 있었던 마지막 값"이라는 동일한 규칙을 매일 적용해야
    covered_weight 정규화가 항상 일관된다.
    """
    if not series_cache or covered_weight <= 0:
        return []
    start = min(inception[t]["entry_date"] for t in weights_by_ticker)
    all_dates = sorted({d for s in series_cache.values() for d in s if d >= start})

    trajectory = []
    for d in all_dates:
        idx_sum = 0.0
        for t, w in weights_by_ticker.items():
            _, bar = price_on_or_before(series_cache[t], d)
            if bar is None:
                continue
            idx_sum += w * (bar["adj"] / inception[t]["entry_adj"] * 100.0)
        point = {"date": d, "portfolio_index": idx_sum / covered_weight}
        if bseries and bench_entry_adj:
            _, bbar = price_on_or_before(bseries, d)
            if bbar:
                point["benchmark_index"] = bbar["adj"] / bench_entry_adj * 100.0
        trajectory.append(point)
    return trajectory


def load_history(out_dir=OUT_DIR):
    """
    누적된 스냅샷 파일(`portfolio_track_record_<날짜>.json`)을 시간순으로
    읽는다 - 차트용. 디렉터리가 없거나 비어 있으면 빈 리스트(추측하지 않는다).
    """
    if not os.path.isdir(out_dir):
        return []
    paths = sorted(glob.glob(os.path.join(out_dir, "portfolio_track_record_*.json")))
    history = []
    for p in paths:
        with open(p, encoding="utf-8") as f:
            history.append(json.load(f))
    return history


def format_snapshot(snap):
    """사람이 읽는 요약."""
    L = [f"## 포트폴리오 트랙레코드 ({snap['as_of']})", ""]
    v = snap["portfolio_version"]
    L.append(f"매수리스트 {v['source_path']} (발행일 {v['generated_at']}, "
             f"{v['n_positions']}종목) - 진입일 {snap['inception_date']}")
    if snap["portfolio_return_pct"] is None:
        L.append("")
        L.append("가중수익률 계산 불가 - 확보된 가격이 없음.")
        return "\n".join(L)

    L.append(f"경과 {snap['days_held']}일(최신 바 {snap['as_of_actual_latest_bar']}) · "
             f"커버리지 {snap['n_covered']}/{snap['n_positions']}종목 "
             f"(가중치 {snap['covered_weight']*100:.1f}%)")
    L.append(f"포트폴리오 가중수익률: {snap['portfolio_return_pct']:+.2f}%")
    if snap["benchmark"]:
        b = snap["benchmark"]
        L.append(f"벤치마크({b['ticker']}): {b['return_pct']:+.2f}%")
    if snap["alpha_vs_benchmark_pct"] is not None:
        L.append(f"벤치마크 대비: {snap['alpha_vs_benchmark_pct']:+.2f}%p")
    if snap["uncovered_weight"] > 0:
        L.append(f"⚠️ 미확보 비중 {snap['uncovered_weight']*100:.1f}% - "
                 f"수익률 계산에서 빠짐(0%로 취급 안 함)")
    L.append("")
    L.append("| 종목 | 등급 | 비중 | 수익률 | 기여도 |")
    L.append("|---|---|---:|---:|---:|")
    for r in snap["rows"]:
        if "error" in r:
            L.append(f"| {r['ticker']} | {r.get('grade','?')} | "
                     f"{r['weight']*100:.2f}% | 미확보({r['error']}) | - |")
        else:
            L.append(f"| {r['ticker']} | {r.get('grade','?')} | "
                     f"{r['weight']*100:.2f}% | {r['return_pct']:+.2f}% | "
                     f"{r['contribution_pct']:+.2f}%p |")
    L.append("")
    L.append("⚠️ " + MEASUREMENT_STATUS)
    return "\n".join(L)
