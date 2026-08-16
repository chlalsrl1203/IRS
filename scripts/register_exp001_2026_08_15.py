"""
EXP-001 등록 - 이 시스템의 근본 가설을 연구 등록부에 올린다(2026-08-15).

가설: "Valuation-Implied Requirement와 Evidence-Supported Forward Expectation
사이의 괴리(Expectation Gap)가 미래 위험조정수익률과 관계가 있는가?"

⚠️ **결과를 미리 가정하지 않는다.** 관계가 없다는 결과가 나와도 그대로
기록한다 - 이 프로젝트는 가설이 실측으로 기각된 사례를 그대로 남겨둔 전례가
있다(v3.44 gap_distribution의 확률분포 가설 기각, META capex 가설 기각).

⚠️ **지금은 실행할 수 없다.** 분석 이력이 3주뿐이라 12개월 보유수익률을 잴
구간이 없고, 진입가(price_at_analysis)가 34종목 중 9건뿐이다. 그 사실을
차단 사유로 명시해 등록한다 - 실행 가능해질 때까지 등록부에 남아 있는 것이
"언젠가 검증하겠다"고 말만 하는 것보다 낫다.

이 등록 자체가 중요한 이유: **매수리스트는 이미 Gap 기반 등급(S/A)으로
만들어지고 있다.** 즉 미검증 가설이 이미 자본배분을 움직이는 중이며, 이
등록부는 그 상태를 정직하게 드러내는 장치다.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.experiment_registry import (  # noqa: E402
    BLOCKED_REASON_EXP001,
    core_hypothesis_experiment,
    register_experiment,
)

REGISTERED_DATE = "2026-08-15"


def main():
    exp = core_hypothesis_experiment(REGISTERED_DATE)
    path = register_experiment(exp, status="BLOCKED",
                               blocked_reason=BLOCKED_REASON_EXP001)

    print("=" * 78)
    print(f"EXP-001 등록 완료: {path}")
    print("=" * 78)
    print(f"가설      : {exp.hypothesis}")
    print()
    print(f"유니버스  : {exp.universe}")
    print(f"진입규칙  : {exp.entry_rule}")
    print(f"청산규칙  : {exp.exit_rule}")
    print(f"벤치마크  : {exp.benchmark}")
    print()
    print("상태      : BLOCKED")
    print(f"차단사유  : {BLOCKED_REASON_EXP001}")


if __name__ == "__main__":
    main()
