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
import csv
import json
import os
import re
import statistics
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(_HERE)
sys.path.insert(0, ROOT)

PIT_DIR = os.path.join(ROOT, "reports", "pit_backtest")
RES_DIR = os.path.join(ROOT, "reports", "research")

LISTING_DIR = os.path.join(ROOT, "data", "listing_status")

# ⚠️ 초판은 T0 이전 폐지 종목 2건을 **손으로 적어뒀다**(WESTMORELAND·MICROSEMI).
# T0가 6개로 늘면 손으로 채울 수 없어 이름 매칭으로 자동화한다 - 다만 매칭
# 대상이 flagged 수십 건뿐이라(전체 유니버스가 아니라) 오탐 위험이 작다.
# 전체 유니버스에 이름 매칭을 쓰지 않는 이유는 단일 CIK 확정률이 65.9%밖에
# 안 되기 때문이다(v3.77 실측) - 여기서는 CIK가 아니라 "폐지일"만 붙이면
# 되므로 그 한계가 적용되지 않는다.
_STRIP = re.compile(
    r"\b(INC|CORP|CORPORATION|CO|COMPANY|LTD|LLC|LP|PLC|DE|GROUP|THE|"
    r"HOLDINGS?|CLASS [A-Z])\b")


def _norm(s):
    s = re.sub(r"[^A-Z0-9 ]", " ", s.upper())
    return re.sub(r"\s+", " ", _STRIP.sub(" ", s)).strip()


def delisting_dates():
    """{정규화 회사명: 폐지일}. 파일이 없으면 빈 dict(조용히 다르게 굴지 않게 경고)."""
    p = os.path.join(LISTING_DIR, "delisted_all_2026-08-30.csv")
    if not os.path.exists(p):
        return {}, f"폐지 목록 파일 없음({p}) - T0 이전 폐지 종목을 걸러내지 못했다"
    out = {}
    with open(p, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r.get("assetType") != "Stock":
                continue
            n = _norm(r.get("name", ""))
            d = r.get("delistingDate") or ""
            if n and (n not in out or d < out[n]):   # 가장 이른 폐지일 채택
                out[n] = d
    return out, None


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

    # T0 시점에 이미 폐지된 종목은 그때 살 수 없었으므로 유니버스가 아니다
    dd, warn = delisting_dates()
    pre, unmatched = {}, 0
    for x in sv["passed_detail"]:
        d = dd.get(_norm(x["name"]))
        if d is None:
            unmatched += 1
        elif d < t0:
            pre[x["name"]] = d
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

    # ⚠️ **대칭 보정** — 위 시나리오는 놓친 flagged만 더해 flagged 쪽에만
    # 불이익을 준다. 사라진 집단에는 not_flagged도 같이 있었으므로(2018 기준
    # 채점 114 중 flagged 18, not_flagged 96) 한쪽만 더하면 비교가 기울어진다.
    # 두 그룹에 같은 가정을 넣어야 "flagged가 not_flagged보다 나았는가"라는
    # 원래 질문이 유지된다.
    nf_visible = [r["return_pct"] for r in rt["not_flagged"]]
    n_inv_nf = sv["scored"] - sv["passed"]
    symmetric = {}
    for tag, fill in (("worst_minus100", -100.0), ("neutral_benchmark", bench)):
        f_xs = visible + [fill] * n_inv
        nf_xs = nf_visible + [fill] * n_inv_nf
        symmetric[tag] = {
            "flagged": summarize(f_xs, bench),
            "not_flagged": summarize(nf_xs, bench),
            "flagged_median_advantage_pp": (statistics.median(f_xs)
                                            - statistics.median(nf_xs)),
        }
    symmetric["as_reported"] = {
        "flagged": summarize(visible, bench),
        "not_flagged": summarize(nf_visible, bench),
        "flagged_median_advantage_pp": (statistics.median(visible)
                                        - statistics.median(nf_visible)),
    }

    scale = sv["invisible_to_backtest"] / sv["sampled"]
    return {
        "as_of_t0": t0,
        "benchmark_pct": bench,
        "n_visible_flagged": len(visible),
        "n_invisible_flagged_measured": n_inv,
        "excluded_delisted_before_t0": pre,
        "delisting_name_unmatched": unmatched,
        "scenarios": scenarios,
        "symmetric": symmetric,
        "n_invisible_not_flagged": n_inv_nf,
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
            "산출 구간은 **하한**이다 - 사라진 집단 중 600개만 표본조사했다.",
            "`scenarios`는 놓친 flagged만 더하므로 flagged에 불리하게 기울어져 "
            "있다 - 두 그룹에 같은 가정을 넣은 `symmetric`을 함께 볼 것.",
            "폐지 사유(파산 vs 피인수)를 구분할 데이터가 없어 어느 시나리오가 "
            "실제에 가까운지 알 수 없다. 명단에 파산(AKORN·LANNETT)과 프리미엄 "
            "피인수(ALLEGHANY·CELGENE)가 둘 다 있다.",
            f"놓친 판정 중 {unmatched}건은 폐지목록에서 이름 매칭이 안 돼 "
            "T0 이전 폐지 여부를 확인하지 못했다 - 그대로 포함시켰다(빼면 "
            "근거 없이 표본을 줄이는 것이 된다).",
        ] + ([warn] if warn else []),
    }


def summarize_all():
    """
    확보된 모든 T0의 구간을 한 표로. **T0끼리 절대 수익률을 비교하지 말 것** -
    보유기간이 다르다(pit_multi_t0_summary와 동일한 경고).

    비교해도 되는 것은 **T0 안에서의 상대 변화**와 "놓친 판정 / 보이는 판정"
    비율처럼 무차원인 값뿐이다.
    """
    t0s = sorted(f[len("survivorship_bias_"):-len(".json")]
                 for f in os.listdir(RES_DIR)
                 if f.startswith("survivorship_bias_"))
    rows = []
    for t0 in t0s:
        if not os.path.exists(os.path.join(PIT_DIR, f"pit_returns_{t0}.json")):
            continue
        rows.append(build(t0))

    print("# 생존편향 구간 — T0 교차 요약\n")
    print("⚠️ T0마다 보유기간이 다르므로 **T0끼리 절대 수익률을 비교하지 말 것.**\n")
    print(f"| T0 | 보이는 flagged | 놓친(실측) | 놓친/보이는(전수추정) | "
          f"현재 중앙값 | 최악 | 중립 |")
    print("|---|---:|---:|---:|---:|---:|---:|")
    for r in rows:
        s = r["scenarios"]
        print(f"| {r['as_of_t0']} | {r['n_visible_flagged']} | "
              f"{r['n_invisible_flagged_measured']} | "
              f"{r['extrapolation']['ratio_to_visible']:.1f}배 | "
              f"{s['as_reported_visible_only']['median_pct']:+.1f}% | "
              f"{s['worst_all_missing_minus100']['median_pct']:+.1f}% | "
              f"{s['neutral_all_missing_benchmark']['median_pct']:+.1f}% |")

    print("\n**벤치마크 초과비율 변화**\n")
    print("| T0 | 현재 | 최악 | 중립 |")
    print("|---|---:|---:|---:|")
    for r in rows:
        s = r["scenarios"]
        print(f"| {r['as_of_t0']} | "
              f"{s['as_reported_visible_only']['beat_benchmark_rate']*100:.0f}% | "
              f"{s['worst_all_missing_minus100']['beat_benchmark_rate']*100:.0f}% | "
              f"{s['neutral_all_missing_benchmark']['beat_benchmark_rate']*100:.0f}% |")

    print("\n**대칭 보정 — flagged 중앙값 우위(%p), 두 그룹에 같은 가정 적용**\n")
    print("| T0 | 현재 | 최악(양쪽 -100%) | 중립(양쪽 벤치마크) |")
    print("|---|---:|---:|---:|")
    for r in rows:
        sy = r["symmetric"]
        print(f"| {r['as_of_t0']} | "
              f"{sy['as_reported']['flagged_median_advantage_pp']:+.1f}%p | "
              f"{sy['worst_minus100']['flagged_median_advantage_pp']:+.1f}%p | "
              f"{sy['neutral_benchmark']['flagged_median_advantage_pp']:+.1f}%p |")
    adv = [r["symmetric"]["worst_minus100"]["flagged_median_advantage_pp"]
           for r in rows]
    print(f"\n>>> 최악 시나리오에서도 flagged 우위가 유지된 T0: "
          f"{sum(1 for a in adv if a > 0)}/{len(adv)}")

    ratios = [r["extrapolation"]["ratio_to_visible"] for r in rows]
    print(f"\n>>> 놓친/보이는 비율 범위: {min(ratios):.1f}배 ~ {max(ratios):.1f}배 "
          f"(중앙값 {statistics.median(ratios):.1f}배)")
    print(">>> ⚠️ 전부 **하한**이다 - 사라진 집단 중 600개만 표본조사했다.")

    p = os.path.join(RES_DIR, "backtest_bounds_all_t0.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
    print(f">>> 저장: {p}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--as-of", default="2018-06-30")
    ap.add_argument("--all", action="store_true",
                    help="확보된 모든 T0를 계산해 교차 요약표를 낸다")
    args = ap.parse_args()
    if args.all:
        summarize_all()
        return
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
