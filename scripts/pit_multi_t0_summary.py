"""
pit_multi_t0_summary.py (2026-08-29) — 여러 T0의 성적표를 나란히 놓는다.

## 왜 이게 단일 T0 성적표보다 중요한가

T0 하나만 보면 그 시점의 시장 국면을 스크리너의 실력으로 착각한다. 실제로
2026-08-29 실측에서 T0=2021-06-30만 봤을 때는 flagged가 동일가중 +283% vs
+105%로 압도적이었는데, T0=2023-06-30을 추가하니 **중앙값 기준으로 flagged가
오히려 뒤진다**(+53.9% vs +64.8%). 한 시점만 보고 결론냈다면 정반대로 틀렸다.

## 무엇을 비교하는가

각 T0마다 flagged(저평가 판정)와 not_flagged를 **같은 보유기간**으로 비교한다.
T0가 다르면 보유기간도 다르므로(2018 T0는 8년, 2023 T0는 3년) **T0끼리 수익률
절대값을 비교하지 않는다** - 각 T0 안에서의 상대비교만 의미가 있다.

## 판정 어휘

`flagged_better`는 그 지표에서 flagged가 앞섰다는 사실 서술일 뿐이며,
통계적 유의성 주장이 아니다(표본이 T0당 17~27종목이고 단일 시장국면이다).
"""
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

from pit_scorecard import build  # noqa: E402

# 비교할 지표: (JSON 키, 표시 이름, 높을수록 좋은가)
METRICS = [
    ("equal_weight_portfolio_pct", "동일가중", True),
    ("median_pct", "중앙값", True),
    ("p25_pct", "하위25%(최악 구간)", True),
    ("min_pct", "최저 종목", True),
    ("beat_benchmark_rate", "벤치마크 초과비율", True),
]


def compare(paths):
    rows = []
    for p in sorted(paths):
        summary, _ = build(p)
        fl, nf = summary["flagged"], summary["not_flagged"]
        bench = (summary.get("benchmark") or {}).get("return_pct")
        t0 = os.path.basename(p).replace("pit_returns_", "").replace(".json", "")
        rec = {"t0": t0, "n_flagged": fl.get("n"), "n_not_flagged": nf.get("n"),
               "benchmark_pct": bench, "metrics": {}}
        for key, label, _hib in METRICS:
            a, b = fl.get(key), nf.get(key)
            if a is None or b is None:
                continue
            rec["metrics"][key] = {"flagged": a, "not_flagged": b,
                                   "flagged_better": a > b}
        # 집중도 강건 지표(상위5 제외)도 함께
        a = (fl.get("concentration") or {}).get("mean_excl_top5_pct")
        b = (nf.get("concentration") or {}).get("mean_excl_top5_pct")
        if a is not None and b is not None:
            rec["metrics"]["mean_excl_top5_pct"] = {
                "flagged": a, "not_flagged": b, "flagged_better": a > b}
        rows.append(rec)
    return rows


def render(rows):
    labels = dict((k, l) for k, l, _ in METRICS)
    labels["mean_excl_top5_pct"] = "상위5 제외 평균"
    order = [k for k, _, _ in METRICS] + ["mean_excl_top5_pct"]

    out = ["# PIT 백테스트 — 여러 T0 교차 요약", "",
           "⚠️ T0마다 보유기간이 다르므로 **T0끼리 절대 수익률을 비교하지 말 것.**",
           "각 T0 안에서 flagged vs not_flagged 상대비교만 의미가 있다.", ""]
    head = "| 지표 | " + " | ".join(
        f"T0={r['t0']}<br>(f{r['n_flagged']}/n{r['n_not_flagged']})" for r in rows) + " |"
    out += [head, "|---|" + "---|" * len(rows)]
    out.append("| 벤치마크 SPY | " + " | ".join(
        f"{r['benchmark_pct']:+.1f}%" if r["benchmark_pct"] is not None else "-"
        for r in rows) + " |")
    for key in order:
        cells = []
        for r in rows:
            m = r["metrics"].get(key)
            if not m:
                cells.append("-")
                continue
            fmt = (lambda v: f"{v * 100:.0f}%") if key.endswith("_rate") \
                else (lambda v: f"{v:+.1f}%")
            mark = "✅" if m["flagged_better"] else "❌"
            cells.append(f"{mark} {fmt(m['flagged'])} vs {fmt(m['not_flagged'])}")
        out.append(f"| {labels.get(key, key)} | " + " | ".join(cells) + " |")

    out += ["", "✅ = 그 지표에서 flagged가 앞섬(사실 서술일 뿐, 통계적 유의성 주장 아님)", ""]

    # 지표별 재현 횟수
    out.append("**재현 횟수(3개 T0 중 flagged가 앞선 횟수)**", )
    out.append("")
    for key in order:
        wins = sum(1 for r in rows if (r["metrics"].get(key) or {}).get("flagged_better"))
        have = sum(1 for r in rows if key in r["metrics"])
        out.append(f"- {labels.get(key, key)}: **{wins}/{have}**")
    return "\n".join(out)


def main():
    import argparse
    ap = argparse.ArgumentParser(description="여러 T0 교차 요약")
    ap.add_argument("returns", nargs="+", help="pit_returns_*.json 경로들")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    rows = compare(args.returns)
    text = render(rows)
    print(text)
    if args.out:
        os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
