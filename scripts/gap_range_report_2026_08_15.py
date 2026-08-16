"""
가정집합 Gap 범위 전수 리포트 (2026-08-15).

34종목 각각에 대해 정당화 가능한 가정집합에서 Gap이 어느 범위에 놓이는지,
그리고 판정이 뒤집히는지를 계산해 `reports/`에 남긴다.

⚠️ **공식 판정은 건드리지 않는다**(병기 원칙). ledger는 읽기만 한다.
"""

import glob
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.gap_analysis import (  # noqa: E402
    ASSUMPTION_GRID,
    GAP_RANGE_VALIDATION,
    gap_range_over_assumptions,
)

OUT = f"reports/gap_range_{datetime.now(timezone.utc):%Y-%m-%d}.json"


def main():
    rows = []
    for p in sorted(glob.glob("ledger/*.json")):
        led = json.load(open(p, encoding="utf-8"))
        r = gap_range_over_assumptions(led)
        r["official_model"] = led["implied_growth"]["model_used"]
        r["sensitivity_check_flipped"] = (
            led.get("sensitivity_check") or {}).get("judgment_flipped")
        rows.append(r)

    frag = [r for r in rows if not r["robust"]]
    old = {r["ticker"] for r in rows if r["sensitivity_check_flipped"]}
    new = {r["ticker"] for r in frag}

    print("=" * 96)
    print(f"가정집합 Gap 범위 - {len(rows)}종목")
    print("=" * 96)
    print(f"{'종목':6s} {'공식Gap':>8s} {'범위':>19s} {'폭':>8s} {'강건':>5s}  뒤집는 축")
    for r in sorted(rows, key=lambda x: -x["gap_span_pp"]):
        ax = ",".join(k for k, v in r["flip_drivers"].items() if v) or "-"
        print(f"{r['ticker']:6s} {r['official_gap']*100:+7.2f}%p "
              f"{r['gap_min']*100:+8.2f}~{r['gap_max']*100:+7.2f}%p "
              f"{r['gap_span_pp']*100:7.2f}%p {'O' if r['robust'] else 'X':>5s}  {ax}")

    print()
    print(f"robust=False : {len(frag)}/{len(rows)}")
    print(f"기존 sensitivity_check flip : {len(old)}종목 {sorted(old)}")
    print(f"새로 잡은 종목               : {len(new - old)}")
    print(f"기존만 잡고 여기서 놓친 종목  : {len(old - new)}")
    print()
    print("⚠️ robust=True는 '확실하다'가 아니라 '이 격자 안에서는 안 뒤집힌다'다.")
    print("   Realistic Growth는 고정돼 있고, 감사가 측정한 최대 오차원이 그 축이다.")

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "grid": {k: list(v) for k, v in ASSUMPTION_GRID.items()},
        "validation_status": GAP_RANGE_VALIDATION,
        "n_tickers": len(rows),
        "n_not_robust": len(frag),
        "not_robust_tickers": sorted(new),
        "sensitivity_check_flipped_tickers": sorted(old),
        "newly_caught": sorted(new - old),
        "missed_vs_sensitivity_check": sorted(old - new),
        "flip_driver_counts": {
            k: sum(1 for r in frag if r["flip_drivers"][k])
            for k in ("model_choice", "discount_rate", "terminal_growth",
                      "growth_duration_n")
        },
        "results": rows,
    }
    os.makedirs("reports", exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n리포트: {OUT}")


if __name__ == "__main__":
    main()
