"""
bound_backtest_performance_2026_08_30.py — 측정 불가를 **구간**으로 바꾼다.

## 왜 구간인가

PIT 백테스트가 보고하는 flagged 수익률은 **생존으로 선택된 표본**에서 나왔다
(`scripts/measure_survivorship_bias_2026_08_30.py` 실측: T0=2018-06-30 유니버스
7,784 CIK 중 4,118개(52.9%)가 오늘자 SEC 티커목록에 없어 애초에 채점되지
못했다). 그리고 그 사라진 집단도 **거의 같은 비율로 저평가 판정을 받았다**
(15.8% vs 보이는 집단 14.9%).

폐지 종목의 주가는 유료 데이터라 확보할 수 없다. 그러나 **"모르니까 못
말한다"로 끝낼 필요는 없다** - 놓친 판정의 개수를 알고 있으므로, 그 종목들의
수익률에 극단 가정을 넣어 보고값이 얼마나 움직이는지 **구간으로 묶을 수 있다.**

## 시나리오 — 방향을 가정하지 않는다

사라진 명단에는 파산(AKORN·LANNETT)과 프리미엄 피인수(ALLEGHANY·CELGENE·
MICROSEMI 등)가 **둘 다** 들어 있어 편향 방향을 단정할 수 없다. 그래서 한쪽을
"정답"으로 두지 않고 세 시나리오를 나란히 낸다:

  최악 : 놓친 판정 전부 -100% (전량 파산)
  중립 : 놓친 판정 전부 벤치마크 수익률
  최선 : 놓친 판정 전부 보이는 flagged의 중앙값

## ⚠️ T0 이전 폐지 종목은 제외한다

파일럿에서 WESTMORELAND COAL(폐지 2018-04-24)·MICROSEMI(2018-05-29)가
T0=2018-06-30 유니버스에 들어와 있었다 - 직전 12개월에 10-K를 냈지만 T0
시점엔 이미 살 수 없는 종목이다. 유니버스 정의의 결함이었고
`universe_at(delisted_before=...)`로 고쳤다. 이 스크립트도 같은 기준으로 뺀다.

## ⚠️ 산출되는 구간은 **하한**이다

표본은 사라진 4,118개 중 600개뿐이다. 전수로 확대하면 놓친 판정 수가 약 7배
늘어나므로 실제 구간은 여기서 계산된 것보다 **더 넓다.**
"""
import argparse
import json
import os
import statistics
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(_HERE)
sys.path.insert(0, ROOT)

PIT_DIR = os.path.join(ROOT, "reports", "pit_backtest")
RES_DIR = os.path.join(ROOT, "reports", "research")

# T0 이전에 이미 폐지돼 유니버스에 잘못 들어온 종목(파일럿 실측).
# LISTING_STATUS의 delistingDate < T0으로 확인했다.
DELISTED_BEFORE_T0 = {
    "2018-06-30": {"WESTMORELAND COAL Co": "2018-04-24",
                   "MICROSEMI CORP": "2018-05-29"},
}


def summarize(xs, bench):
    return {
        "n": len(xs),
        "median_pct": statistics.median(xs),
        "mean_pct": statistics.fmean(xs),
        "beat_benchmark_rate": sum(1 for x in xs if x > bench) / len(xs),
    }


def build(t0):
    rt = json.load(open(os.path.join(PIT_DIR, f"pit_returns_{t0}.json")))
    sv = json.load(open(os.path.join(RES_DIR, f"survivorship_bias_{t0}.json")))
    bench = rt["benchmark"]["return_pct"]
    visible = [r["return_pct"] for r in rt["flagged"]]

    pre = DELISTED_BEFORE_T0.get(t0, {})
    invisible = [x for x in sv["passed_detail"] if x["name"] not in pre]
    n_inv = len(invisible)
    vis_median = statistics.median(visible)

    scenarios = {
        "as_reported_visible_only": summarize(visible, bench),
        "worst_all_missing_minus100": summarize(
            visible + [-100.0] * n_inv, bench),
        "neutral_all_missing_benchmark": summarize(
            visible + [bench] * n_inv, bench),
        "best_all_missing_visible_median": summarize(
            visible + [vis_median] * n_inv, bench),
    }
    meds = [s["median_pct"] for s in scenarios.values()]

    scale = sv["invisible_to_backtest"] / sv["sampled"]
    return {
        "as_of_t0": t0,
        "benchmark_pct": bench,
        "n_visible_flagged": len(visible),
        "n_invisible_flagged_measured": n_inv,
        "excluded_delisted_before_t0": pre,
        "scenarios": scenarios,
        "median_range_pct": [min(meds), max(meds)],
        "extrapolation": {
            "invisible_group_size": sv["invisible_to_backtest"],
            "sampled": sv["sampled"],
            "implied_total_missed_flags": round(n_inv * scale),
            "ratio_to_visible": n_inv * scale / len(visible),
            "note": ("표본 확대 시 놓친 판정이 이만큼일 수 있다는 **단순 비례 "
                     "추정**이다 - 사라진 집단 안에서 판정률이 균일하다는 "
                     "가정에 의존하므로 정밀한 값이 아니다."),
        },
        "caveats": [
            "산출 구간은 **하한**이다 - 사라진 4,118개 중 600개만 표본조사했다.",
            "폐지 사유(파산 vs 피인수)를 구분할 데이터가 없어 어느 시나리오가 "
            "실제에 가까운지 알 수 없다. 명단에 파산(AKORN·LANNETT)과 프리미엄 "
            "피인수(ALLEGHANY·CELGENE)가 둘 다 있다.",
            "T0=2018 하나만 계산했다 - 나머지 5개 T0는 미측정.",
        ],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--as-of", default="2018-06-30")
    args = ap.parse_args()
    out = build(args.as_of)

    p = os.path.join(RES_DIR, f"backtest_bounds_{args.as_of}.json")
    os.makedirs(RES_DIR, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f"T0={out['as_of_t0']}  벤치마크 {out['benchmark_pct']:+.1f}%")
    print(f"보이는 flagged {out['n_visible_flagged']} / "
          f"놓친 flagged {out['n_invisible_flagged_measured']}(실측)\n")
    print(f"{'시나리오':34} {'중앙값':>10} {'평균':>10} {'벤치초과':>8}")
    print("-" * 66)
    labels = {
        "as_reported_visible_only": "현재 보고값(보이는 것만)",
        "worst_all_missing_minus100": "최악: 놓친 것 전부 -100%",
        "neutral_all_missing_benchmark": "중립: 놓친 것 = 벤치마크",
        "best_all_missing_visible_median": "최선: 놓친 것 = 보이는 중앙값",
    }
    for k, s in out["scenarios"].items():
        print(f"{labels[k]:32} {s['median_pct']:+9.1f}% {s['mean_pct']:+9.1f}% "
              f"{s['beat_benchmark_rate']*100:7.0f}%")
    lo, hi = out["median_range_pct"]
    print(f"\n>>> 중앙값 구간: {lo:+.1f}% ~ {hi:+.1f}%")
    e = out["extrapolation"]
    print(f">>> ⚠️ 하한이다 - 전수 확대 시 놓친 판정 약 {e['implied_total_missed_flags']}건"
          f"(보이는 것의 {e['ratio_to_visible']:.1f}배)")
    print(f">>> 저장: {p}")


if __name__ == "__main__":
    main()
