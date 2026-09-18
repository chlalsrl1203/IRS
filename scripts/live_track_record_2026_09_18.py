"""
2026-09-18 - 실전 트랙레코드 1차 측정.

## 왜 이게 지금까지 없었나

이 프로젝트는 v3.73~v3.78에서 **합성 PIT 백테스트**(과거 시점으로
되돌아가 그때 데이터만으로 판정을 재구성한 뒤 이후 실현수익률과 대조)를
만들었다. 그런데 2026-09-01(CROX) 이후 정식분석한 종목들은 전부
`price_at_analysis`(v3.24)를 채워왔고, 지금 시점에 그 값과 현재가를
대조하면 **합성이 아니라 진짜** T0->결과 관측을 얻을 수 있다 - 이 값을
한 번도 실제로 대조해본 적이 없었다.

## ⚠️ 이건 사전등록된 실험(H-00X)이 아니다

H-001~H-006이 `experiments/`에 등록하는 이유는 "결과를 보기 전에 판정
기준을 고정"하기 위해서다. 이 스크립트는 그 반대다 - 지금 가진 것으로
**방향성만** 본다(2.5~46일짜리 초단기 창, n=57, 단일 시장국면). 여기서
나온 관찰이 향후 정식 실험(H-001, 12개월 보유수익률)의 결론을 대신하지
않는다. `experiments/H-001.json`은 여전히 BLOCKED다.

## 무엇을 새로 만들지 않았는가

새 밸류에이션 로직 0줄. ledger에 이미 저장된 `price_at_analysis`/
`judgment`/`judgment_grade`를 그대로 읽고, 현재가만 stockanalysis.com
(`scripts/pit_price_validation.py`가 이미 검증해 쓰는 출처, robots.txt
확인됨)에서 가져와 나눈다. 이 결과는 **`ledger/`에 쓰지 않는다**
(v3.42 원칙 - 재계산은 병기일 뿐 공식 판정이 아니다).
"""
import glob
import json
import os
import statistics
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone

sys.path.insert(0, ".")

_HERE = os.path.dirname(os.path.abspath(__file__))
REPORTS_DIR = os.path.join(os.path.dirname(_HERE), "reports")

API = "https://stockanalysis.com/api/symbol/s/{sym}/history?range=1M&period=Daily"
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/120 Safari/537.36")
REQUEST_INTERVAL_SEC = 0.7
SYMBOL_OVERRIDES = {}  # 이번 57종목 중 특수기호 티커 없음(확인됨)


def log(msg):
    print(msg, flush=True)


def collect_cohort():
    """price_at_analysis가 채워진 전 ledger를 모은다."""
    rows = []
    for p in sorted(glob.glob("ledger/*.json")):
        d = json.load(open(p, encoding="utf-8"))
        m = d.get("meta", {})
        price = m.get("price_at_analysis")
        analyzed_at = m.get("analyzed_at")
        if price is None or not analyzed_at:
            continue
        rows.append({
            "ticker": m["ticker"],
            "ledger_file": os.path.basename(p),
            "analyzed_at": analyzed_at,
            "price_at_analysis": price,
            "currency": m.get("currency", "USD"),
            "judgment": d.get("judgment"),
            "judgment_grade": d.get("judgment_grade"),
            "expectation_gap": d.get("expectation_gap"),
        })
    return rows


def fetch_latest_close(ticker):
    """최신 종가. 실패하면 (None, 사유) - v3.68 원칙대로 사유를 살린다."""
    sym = SYMBOL_OVERRIDES.get(ticker, ticker)
    url = API.format(sym=urllib.parse.quote(sym.lower()))
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except Exception as e:  # noqa: BLE001
        return None, None, f"조회 실패: {e!r}"

    raw = payload.get("data")
    if isinstance(raw, dict):
        raw = raw.get("data")
    if not raw:
        return None, None, "가격 시계열 없음(상장폐지·인수합병·심볼 변경 가능)"

    # ⚠️ range=1M이 실제로는 1년치(252거래일)를 돌려주고, 정렬순서도 최신순
    # (내림차순)이다 - raw[-1]을 "최신"으로 가정했다가 1년 전 값을 잘못
    # 채택한 사고를 여기서 잡았다. pit_price_validation.py가 max()로 방어한
    # 것과 같은 이유로, 순서를 신뢰하지 않고 날짜 최댓값으로 직접 고른다.
    latest = max(raw, key=lambda r: r.get("t", ""))
    price = latest.get("c")
    date = latest.get("t")
    if price is None or date is None:
        return None, None, "최신 종가 파싱 실패"
    return float(price), date, None


def days_between(analyzed_at_iso, latest_date_str):
    dt0 = datetime.fromisoformat(analyzed_at_iso.replace("Z", "+00:00"))
    dt1 = datetime.strptime(latest_date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return (dt1 - dt0).days


def build_rows():
    cohort = collect_cohort()
    log(f"코호트: {len(cohort)}종목 (price_at_analysis 확보된 전체 ledger)")

    results = []
    failed = []
    for i, row in enumerate(cohort, 1):
        t = row["ticker"]
        price_now, date_now, err = fetch_latest_close(t)
        if err:
            failed.append({**row, "error": err})
            log(f"[{i}/{len(cohort)}] {t}: 실패 - {err}")
            time.sleep(REQUEST_INTERVAL_SEC)
            continue
        days = days_between(row["analyzed_at"], date_now)
        ret_pct = (price_now / row["price_at_analysis"] - 1.0) * 100.0
        results.append({
            **row,
            "price_now": price_now,
            "price_now_date": date_now,
            "days_since_analysis": days,
            "return_pct": ret_pct,
        })
        log(f"[{i}/{len(cohort)}] {t}: {row['price_at_analysis']:.2f} -> "
            f"{price_now:.2f} ({ret_pct:+.2f}%, {days}일)")
        time.sleep(REQUEST_INTERVAL_SEC)

    return results, failed


def bucket_stats(results, key):
    buckets = {}
    for r in results:
        k = r.get(key)
        buckets.setdefault(k, []).append(r["return_pct"])
    out = {}
    for k, vals in buckets.items():
        out[k] = {
            "n": len(vals),
            "median_return_pct": round(statistics.median(vals), 2),
            "mean_return_pct": round(statistics.mean(vals), 2),
            "min_return_pct": round(min(vals), 2),
            "max_return_pct": round(max(vals), 2),
            "pct_positive": round(sum(1 for v in vals if v > 0) / len(vals) * 100, 1),
        }
    return out


def main():
    results, failed = build_rows()

    grade_order = ["S", "A", "B", "C", "D", "F"]
    by_grade = bucket_stats(results, "judgment_grade")
    by_judgment = bucket_stats(results, "judgment")

    all_returns = [r["return_pct"] for r in results]
    all_days = [r["days_since_analysis"] for r in results]

    report = {
        "as_of": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "purpose": (
            "실전(합성 아님) T0->현재 관측 1차 측정. 사전등록된 실험이 "
            "아니며 방향성 참고용이다. experiments/H-001.json(정식 12개월 "
            "보유수익률 실험)을 대체하지 않는다 - 그건 여전히 BLOCKED다."
        ),
        "price_source": "stockanalysis.com (일봉 종가, robots.txt 확인됨)",
        "n_total_cohort": len(results) + len(failed),
        "n_measured": len(results),
        "n_failed": len(failed),
        "horizon_days": {
            "min": min(all_days) if all_days else None,
            "max": max(all_days) if all_days else None,
            "median": round(statistics.median(all_days), 1) if all_days else None,
        },
        "overall": {
            "median_return_pct": round(statistics.median(all_returns), 2) if all_returns else None,
            "mean_return_pct": round(statistics.mean(all_returns), 2) if all_returns else None,
            "pct_positive": round(sum(1 for v in all_returns if v > 0) / len(all_returns) * 100, 1) if all_returns else None,
        },
        "by_judgment_grade": {k: by_grade.get(k) for k in grade_order if k in by_grade},
        "by_judgment": by_judgment,
        "caveats": [
            "표본기간 4~46일(중앙값은 결과에 표시) - 어떤 결론도 통계적으로 "
            "확립되지 않는다(H-006이 최소 15건을 요구하는 것과 같은 이유로 "
            "이 결과는 공식 판정 기준으로 쓰지 않는다).",
            "단일 시장국면(2026-08~09) 관측이라 시장 전체 상승/하락과 "
            "구분되지 않는다 - 벤치마크(예: SPY) 대조가 없다.",
            "생존편향 없음(전부 현재 상장 중인 종목만 코호트에 포함 - "
            "T0 이후 상장폐지된 종목이 있었다면 이 방식으로는 놓친다, "
            "다만 4~46일 초단기 창에서 상장폐지 가능성은 낮다).",
            "거래비용·세금 미반영(v3.74/v3.78 성적표와 동일 한계).",
            "이 코호트는 '스크리닝 통과 종목'이 아니라 '정식분석까지 마친 "
            "종목'이라 이미 한 번 걸러진 표본이다 - PIT 백테스트(비필터링 "
            "유니버스)와 성격이 다르다.",
        ],
        "results": results,
        "failed": failed,
    }

    out_path = os.path.join(REPORTS_DIR, f"live_track_record_{report['as_of']}.json")
    os.makedirs(REPORTS_DIR, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    log("")
    log(f"=== 등급별 ({report['n_measured']}종목, 실패 {report['n_failed']}건) ===")
    for g in grade_order:
        s = by_grade.get(g)
        if s:
            log(f"  {g}: n={s['n']:2d}  중앙값 {s['median_return_pct']:+6.2f}%  "
                f"평균 {s['mean_return_pct']:+6.2f}%  양(+) 비율 {s['pct_positive']:5.1f}%")
    log("")
    log(f"저장: {out_path}")
    return report


if __name__ == "__main__":
    main()
