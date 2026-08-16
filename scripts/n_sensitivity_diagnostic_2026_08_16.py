"""
성장지속기간(n) 민감도 진단 - 엔진 허용범위 전체 (2026-08-16).

## 문제

`engine/gap_analysis.ASSUMPTION_GRID`의 `n_delta = (-2, 0, 2)`는 n ∈ {10,12,14}만
본다. 그런데 엔진 자신은 `capped_n(n_min=8, n_max=15)`로 **8~15를 허용**한다.
즉 강건성 격자가 엔진 허용범위보다 좁고, 그 결과 `gap_range_over_assumptions()`는
34종목 전부에 대해 `growth_duration_n: 0 flips`를 보고한다 - 허용범위 안에서
실제로 3건이 뒤집히는데도.

## ⚠️ ASSUMPTION_GRID를 수정하지 않는 이유

`experiments/H-005.json`이 `robust` 정의를 **2026-08-15 ASSUMPTION_GRID로 코드
고정해 사전등록**했다. 격자를 지금 바꾸면 사전등록 정의가 깨지고, 그건 결과를
본 뒤 규칙을 바꾸는 것과 구분되지 않는다. 그래서 엔진 상수는 그대로 두고
`gap_range_over_assumptions(ledger, grid=...)`의 기존 오버라이드 인자로만
넓은 범위를 본다 - **엔진 코드 변경 0줄, H-005 사전등록 불변.**

이 스크립트의 산출물은 공식 판정이 아니라 진단 신호다(병기, 자동판정 안 함).
"""
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.expectation_gap_engine import capped_n  # noqa: E402
from engine.gap_analysis import ASSUMPTION_GRID, gap_range_over_assumptions  # noqa: E402

DEFAULT_N = 12
# capped_n이 허용하는 8~15를 전부 덮는 delta. 엔진 자신의 한계를 그대로 따른다 -
# 임의로 정한 폭이 아니라는 점이 중요하다(새 파라미터를 발명하지 않았다).
FULL_RANGE_N_DELTA = tuple(n - DEFAULT_N for n in range(8, 16))


def _assert_range_matches_engine():
    """진단 격자가 엔진 허용범위와 정확히 일치하는지 - 임의 확장이 아님을 보장."""
    covered = sorted(DEFAULT_N + d for d in FULL_RANGE_N_DELTA)
    allowed = sorted({capped_n(n) for n in range(0, 40)})
    assert covered == allowed, f"격자 {covered} != capped_n 허용 {allowed}"


def analyze(ledger):
    frozen = gap_range_over_assumptions(ledger)
    wide = gap_range_over_assumptions(ledger, grid={"n_delta": FULL_RANGE_N_DELTA})
    if frozen.get("status") != "COMPUTED" or wide.get("status") != "COMPUTED":
        return None
    return {
        "ticker": ledger["meta"]["ticker"],
        "model_used": ledger["implied_growth"]["model_used"],
        "official_judgment": ledger["judgment"],
        "frozen_judgment_set": frozen["judgment_set"],
        "frozen_robust": frozen["robust"],
        "frozen_n_flip_detected": bool(frozen["flip_drivers"]["growth_duration_n"]),
        "wide_judgment_set": wide["judgment_set"],
        "wide_robust": wide["robust"],
        "wide_n_flip_detected": bool(wide["flip_drivers"]["growth_duration_n"]),
        "gap_span_pp_frozen": frozen["gap_span_pp"] * 100,
        "gap_span_pp_wide": wide["gap_span_pp"] * 100,
        # 핵심: 고정격자가 놓치는가
        "missed_by_frozen_grid": (not frozen["robust"]) is False and (not wide["robust"]) is True,
    }


def main():
    _assert_range_matches_engine()
    results = [r for r in (analyze(json.load(open(p, encoding="utf-8")))
                           for p in sorted(glob.glob("ledger/*.json"))) if r]

    missed = [r for r in results if r["missed_by_frozen_grid"]]
    n_flip_new = [r for r in results
                  if r["wide_n_flip_detected"] and not r["frozen_n_flip_detected"]]

    print(f"대상 {len(results)}종목 "
          f"(고정격자 n∈{{10,12,14}} vs 엔진 허용 n∈{{8..15}})")
    print(f"  고정격자 robust=False        : {sum(1 for r in results if not r['frozen_robust'])}")
    print(f"  허용범위 robust=False        : {sum(1 for r in results if not r['wide_robust'])}")
    print(f"  >>> 고정격자가 놓치는 종목    : {len(missed)}  {[r['ticker'] for r in missed]}")
    print(f"  >>> n축 flip 신규 탐지        : {len(n_flip_new)}  {[r['ticker'] for r in n_flip_new]}")
    print()
    if n_flip_new:
        print("=== n축이 판정을 뒤집는데 고정격자가 못 보던 종목 ===")
        for r in n_flip_new:
            print(f"  {r['ticker']:6s} 공식 '{r['official_judgment']}'  "
                  f"고정격자={r['frozen_judgment_set']} -> 허용범위={r['wide_judgment_set']}  "
                  f"(Gap 변동폭 {r['gap_span_pp_frozen']:.2f}%p -> {r['gap_span_pp_wide']:.2f}%p)")

    report = {
        "generated_at": "2026-08-16",
        "frozen_grid_n_values": sorted(DEFAULT_N + d for d in ASSUMPTION_GRID["n_delta"]),
        "engine_allowed_n_values": sorted(DEFAULT_N + d for d in FULL_RANGE_N_DELTA),
        "note": (
            "ASSUMPTION_GRID는 H-005가 사전등록으로 고정했으므로 수정하지 않았다. "
            "이 리포트는 진단 신호이며 공식 판정·Gap·비중을 바꾸지 않는다."
        ),
        "n_missed_by_frozen_grid": [r["ticker"] for r in missed],
        "n_flip_newly_detected": [r["ticker"] for r in n_flip_new],
        "results": results,
    }
    os.makedirs("reports", exist_ok=True)
    out = "reports/n_sensitivity_2026-08-16.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n저장: {out}")


if __name__ == "__main__":
    main()
