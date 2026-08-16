"""
연구 순서 H-001~H-004 등록 (2026-08-15, 계약서 §11·§12).

## 왜 네 개를 지금 한꺼번에 등록하는가

§12는 순서를 고정했다: H-001(Gap 수준) → H-002(Gap 변화) → H-003(Gap+품질)
→ H-004(Gap+기대수정). **결과를 본 뒤 "이번엔 이 변수가 좋아 보이니 순서를
바꾸자"가 가능하면 그건 검증이 아니라 튜닝이다**(§13).

그래서 넷을 지금 - 데이터가 하나도 없는 시점에 - 등록해 순서를 못박는다.
`depends_on`이 그 순서를 실험 코어(변경 불가)에 담는다.

## EXP-001은 지우지 않는다

EXP-001(v3.48 등록)은 H-001과 **같은 가설**이지만 §10이 요구한 스키마
(비용 가정·데이터/방법론 버전·생존편향 통제)를 갖추지 못했다. 삭제하거나
덮어쓰지 않고 `SUPERSEDED`로 표시해 남긴다 - "실패한 실험도 삭제하지 마라"
(§10)는 구버전 실험에도 똑같이 적용된다.

## 전부 BLOCKED로 등록한다

분석 이력이 3주뿐이라 12개월 보유수익률 구간이 없고, 진입가를 아는 종목이
34건 중 9건뿐이다. 실행 불가 사실과 재개 조건을 함께 남긴다 - 등록만 해두고
왜 못 도는지 안 적으면 이 실험들은 조용히 잊힌다.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.expectation_gap_engine import ENGINE_VERSION  # noqa: E402
from engine.experiment_registry import (  # noqa: E402
    BLOCKED_REASON_SEQUENCE,
    check_dependencies_satisfied,
    load_experiments,
    record_result,
    register_experiment,
    research_sequence,
)

REGISTERED_DATE = "2026-08-15"
DATA_VERSION = "ledger/ 34종목 (2026-08-15 스냅샷, PIT_UNKNOWN)"


def main():
    print("=" * 78)
    print(f"연구 순서 등록 (§12) - methodology_version={ENGINE_VERSION}")
    print("=" * 78)

    for exp in research_sequence(REGISTERED_DATE, ENGINE_VERSION, DATA_VERSION):
        path = os.path.join("experiments", f"{exp.experiment_id}.json")
        if os.path.exists(path):
            print(f"  {exp.experiment_id}: 이미 등록됨 - 건너뜀(덮어쓰지 않는다)")
            continue
        register_experiment(exp, status="BLOCKED",
                            blocked_reason=BLOCKED_REASON_SEQUENCE)
        dep = f" (선행: {', '.join(exp.depends_on)})" if exp.depends_on else ""
        print(f"  {exp.experiment_id} 등록{dep}")

    # EXP-001을 SUPERSEDED로 표시 - 삭제하지 않는다
    exp001 = os.path.join("experiments", "EXP-001.json")
    if os.path.exists(exp001):
        import json
        with open(exp001, encoding="utf-8") as f:
            rec = json.load(f)
        if rec["status"] != "SUPERSEDED":
            record_result(
                exp001,
                {
                    "event": "superseded_by_H-001",
                    "date": REGISTERED_DATE,
                    "reason": (
                        "가설은 동일하나 §10 스키마(transaction_cost_assumption· "
                        "data_version·methodology_version·생존편향 통제)를 갖추지 "
                        "못했다. 기록은 삭제하지 않고 그대로 보존한다."
                    ),
                },
                status="SUPERSEDED",
            )
            print("  EXP-001 -> SUPERSEDED (삭제하지 않고 사유와 함께 보존)")

    print()
    print("등록된 실험 및 의존관계 충족 여부:")
    for rec in load_experiments():
        eid = rec["core"]["experiment_id"]
        dep = check_dependencies_satisfied(eid)
        deps = ", ".join(dep.get("depends_on") or []) or "-"
        mark = "충족" if dep["satisfied"] else "미충족"
        print(f"  {eid:8s} {rec['status']:12s} 선행={deps:16s} {mark}")

    print()
    print("⚠️ 전부 BLOCKED다. 실행 전제:")
    print(f"   {BLOCKED_REASON_SEQUENCE}")


if __name__ == "__main__":
    main()
