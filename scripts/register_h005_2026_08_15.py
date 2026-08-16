"""
H-005 사전등록 (2026-08-15) - 가정집합 강건성이 성과와 관계가 있는가.

⚠️ **결과가 존재하기 전에 등록한다.** 이 가설이 다루는 12개월 보유수익률은
아직 하나도 관측되지 않았다(분석일 2026-07-25~08-13). 따라서 지금 정의를
못박아두면 나중에 결과를 보고 `robust` 정의를 조정할 여지가 원천적으로 없다
(§13·§21이 금지하는 튜닝).

정의는 `gap_analysis.gap_range_over_assumptions()`의 `robust` 필드로 고정하며,
격자(`ASSUMPTION_GRID`)도 이미 코드에 상수로 박혀 있다.

⚠️ 결과를 미리 가정하지 않는다 - robust 종목이 더 나을 수도, 다를 바 없을
수도, 오히려 나쁠 수도 있다(강건한 종목이 이미 시장에 잘 알려져 초과수익이
없을 가능성도 충분하다).
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.expectation_gap_engine import ENGINE_VERSION  # noqa: E402
from engine.experiment_registry import (  # noqa: E402
    BLOCKED_REASON_SEQUENCE,
    Experiment,
    check_dependencies_satisfied,
    register_experiment,
)

REGISTERED_DATE = "2026-08-15"


def main():
    exp = Experiment(
        experiment_id="H-005",
        hypothesis=(
            "가정집합 강건성(`gap_range_over_assumptions().robust`)이 미래 "
            "benchmark-relative 위험조정수익률과 관계가 있는가? 즉 **robust=True "
            "부분집합이 전체집합과 다른 성과를 내는가?** "
            "**방향과 존재 여부 모두 미지이며 가정하지 않는다** - 강건한 종목이 "
            "이미 시장에 충분히 알려져 초과수익이 오히려 낮을 가능성도 열어둔다."
        ),
        universe=(
            "H-001과 동일. ledger/에 공식 분석이 존재하는 미국 상장 개별주식. "
            "**생존 편향 통제**: 분석 시점에 존재한 종목 전부를 포함하며 이후 "
            "상장폐지·피인수된 종목도 빼지 않는다(§13)."
        ),
        entry_rule=(
            "H-001의 Gap 5분위 진입 규칙을 그대로 쓰되, 각 분위를 "
            "robust=True / robust=False로 다시 나눠 비교한다. robust 정의는 "
            "2026-08-15에 코드로 고정된 `ASSUMPTION_GRID`(모델 2종 x r±1%p x "
            "g_terminal±1%p x n±2년) 기준이며 **결과를 보고 바꾸지 않는다.** "
            "2026-08-15 시점 실측: 34종목 중 robust=False 21종목."
        ),
        exit_rule=(
            "진입 후 12개월 보유 후 청산(H-001과 동일). 두 부분집합을 같은 "
            "규칙으로 다뤄야 비교가 성립한다."
        ),
        parameters={
            "signal": "gap_range_over_assumptions().robust",
            "grid_frozen_at": "2026-08-15 ASSUMPTION_GRID",
            "measured_robust_false_at_registration": 21,
            "measured_universe_at_registration": 34,
            "min_sample_per_group": 5,
        },
        test_period="미정 - H-001과 동시에 사전 고정",
        oos_period="미정 - test_period 확정과 동시에 분리 고정",
        benchmark="VOO(S&P500) 동일기간 총수익률 대비 초과수익(H-001과 동일)",
        analysis_as_of=REGISTERED_DATE,
        data_version="ledger/ 34종목 (2026-08-15 스냅샷, PIT_UNKNOWN)",
        methodology_version=ENGINE_VERSION,
        transaction_cost_assumption=(
            "왕복 20bp(H-001과 동일). 두 부분집합에 동일 적용하므로 비교 자체는 "
            "비용 가정에 둔감하나, 절대 성과 주장에는 반드시 반영한다."
        ),
        depends_on=["H-001"],
        registered_date=REGISTERED_DATE,
        note=(
            "2026-08-15 투자가치 감사의 SINGLE NEXT ACTION에서 파생. 감사가 "
            "확인한 것은 '판정이 가정 하나로 뒤집힌다'는 **내부** 사실이며, "
            "그것이 **투자 성과와 관계가 있는지는 전혀 검증되지 않았다** - "
            "이 실험이 바로 그 미검증 부분이다. robust 라벨을 성과 예측으로 "
            "읽지 말 것."
        ),
    )

    path = os.path.join("experiments", "H-005.json")
    if os.path.exists(path):
        print(f"H-005 이미 등록됨 - 건너뜀(덮어쓰지 않는다): {path}")
    else:
        register_experiment(exp, status="BLOCKED",
                            blocked_reason=BLOCKED_REASON_SEQUENCE)
        print(f"H-005 등록 완료: {path}")

    dep = check_dependencies_satisfied("H-005")
    print(f"  선행 {dep['depends_on']} 충족={dep['satisfied']}")
    if dep["unmet"]:
        print(f"  미충족 사유: {dep['unmet'][0]['reason']}")


if __name__ == "__main__":
    main()
