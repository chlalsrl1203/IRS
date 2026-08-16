"""
Research Experiment Registry 테스트.

핵심: 실패한 실험을 지우거나 덮어쓸 수 없어야 한다. 그게 뚫리면 등록부는
'성공한 실험만 모아둔 목록'이 되어 연구 기록이 아니라 광고가 된다.
"""

import json

import pytest

from engine.experiment_registry import (
    BLOCKED_REASON_EXP001,
    BLOCKED_REASON_SEQUENCE,
    FINDING_STATUSES,
    check_dependencies_satisfied,
    EXPERIMENT_STATUSES,
    Experiment,
    core_hypothesis_experiment,
    load_experiments,
    record_result,
    register_experiment,
    research_sequence,
)


def make_experiment(**overrides):
    base = dict(
        experiment_id="EXP-TEST",
        hypothesis="Gap이 큰 종목이 작은 종목보다 12개월 위험조정수익률이 높은가",
        universe="ledger/의 미국 개별주식",
        entry_rule="분석일 종가 진입, Gap 5분위 최상/최하 비교",
        exit_rule="12개월 보유 후 청산",
        test_period="2026-07~2027-07",
        oos_period="2027-08~2028-08",
        benchmark="VOO 동일기간 총수익률",
        analysis_as_of="2026-08-15",
        data_version="ledger/ 34종목 (2026-08-15)",
        methodology_version="v3.50",
        transaction_cost_assumption="왕복 20bp",
        registered_date="2026-08-15",
    )
    base.update(overrides)
    return Experiment(**base)


# ──────────────────────────────────────────────────────────────────
# 핵심: 실패를 지울 수 없다
# ──────────────────────────────────────────────────────────────────

def test_results_are_append_only(tmp_path):
    """
    ⚠️ 실패한 결과 위에 성공한 결과를 덮어쓰면 등록부가 무의미해진다.
    두 번째 결과를 기록해도 첫 번째(실패)가 그대로 남아야 한다.
    """
    path = register_experiment(make_experiment(), experiment_dir=str(tmp_path))

    record_result(path, {"run": 1, "finding": "관계 없음", "spearman": -0.02})
    record_result(path, {"run": 2, "finding": "표본 확대 후에도 관계 없음",
                         "spearman": 0.01}, status="COMPLETED")

    rec = json.loads(open(path, encoding="utf-8").read())
    assert len(rec["results"]) == 2
    assert rec["results"][0]["finding"] == "관계 없음"    # 실패 기록이 살아있다
    assert rec["status"] == "COMPLETED"


def test_experiment_cannot_be_overwritten(tmp_path):
    register_experiment(make_experiment(), experiment_dir=str(tmp_path))
    with pytest.raises(FileExistsError, match="규칙을 바꾸려면"):
        register_experiment(make_experiment(), experiment_dir=str(tmp_path))


def test_no_delete_function_exists():
    """
    삭제 함수를 제공하지 않는 것이 설계다. 실패한 실험을 지우는 경로가
    코드에 있으면 언젠가 쓰이게 된다.
    """
    import engine.experiment_registry as reg

    assert not any(n.startswith(("delete", "remove", "drop"))
                   for n in dir(reg)), "실험 삭제 경로가 생겼다"


def test_core_rules_cannot_change_after_registration(tmp_path):
    """
    ⚠️ 결과를 본 뒤 진입/청산 규칙을 조정하는 것이 백테스트를 무의미하게 만드는
    주범이다. 실제 공격을 재현한다 - 12개월 보유로는 성과가 나쁘자 24개월로
    바꿔놓고 결과를 기록하려는 시도.

    (이 테스트의 초판은 before/after 비교만 해서 **절대 실패할 수 없는** 검사를
    통과시켰다. 코어 해시 대조로 바꾼 뒤에야 실제로 잡힌다.)
    """
    path = register_experiment(make_experiment(), experiment_dir=str(tmp_path))

    rec = json.loads(open(path, encoding="utf-8").read())
    rec["core"]["exit_rule"] = "24개월 보유(결과 보고 바꿈)"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rec, f, ensure_ascii=False)

    with pytest.raises(ValueError, match="코어가 등록 이후 변경"):
        record_result(path, {"run": 1, "finding": "규칙 바꾸니 성과 좋아짐"})


def test_result_refused_when_integrity_cannot_be_verified(tmp_path):
    """
    core_hash가 없으면 규칙 불변을 확인할 방법이 없다 - 그때는 '아마 괜찮겠지'로
    넘기지 않고 기록을 거부한다(검증 못 하는 것을 검증된 것처럼 두지 않는다).
    """
    path = register_experiment(make_experiment(), experiment_dir=str(tmp_path))
    rec = json.loads(open(path, encoding="utf-8").read())
    del rec["core_hash"]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rec, f, ensure_ascii=False)

    with pytest.raises(ValueError, match="core_hash가 없는"):
        record_result(path, {"run": 1, "finding": "무언가"})


def test_empty_result_rejected(tmp_path):
    path = register_experiment(make_experiment(), experiment_dir=str(tmp_path))
    with pytest.raises(ValueError, match="비어 있지 않은"):
        record_result(path, {})


# ──────────────────────────────────────────────────────────────────
# 스키마 - 규칙은 결과를 보기 전에 확정돼야 한다
# ──────────────────────────────────────────────────────────────────

def test_every_core_rule_required_at_registration():
    for f in ("hypothesis", "universe", "entry_rule", "exit_rule",
              "test_period", "oos_period", "benchmark"):
        with pytest.raises(ValueError, match=f):
            make_experiment(**{f: "  "})


def test_blocked_status_requires_reason(tmp_path):
    """왜 지금 못 하는지 안 적으면 이 실험은 조용히 잊힌다."""
    with pytest.raises(ValueError, match="blocked_reason"):
        register_experiment(make_experiment(), status="BLOCKED",
                            experiment_dir=str(tmp_path))


def test_unknown_status_rejected(tmp_path):
    with pytest.raises(ValueError, match="알 수 없는 상태"):
        register_experiment(make_experiment(), status="MAYBE",
                            experiment_dir=str(tmp_path))


# ──────────────────────────────────────────────────────────────────
# EXP-001 - 근본 가설
# ──────────────────────────────────────────────────────────────────

def test_exp001_does_not_presuppose_its_own_result():
    """
    ⚠️ §8: "이 가설의 결과를 미리 가정하지 마라." 가설 문구가 방향을 단정하면
    (예: "Gap이 크면 수익이 높다") 이미 결론을 내린 것이다.
    """
    exp = core_hypothesis_experiment("2026-08-15")
    h = exp.hypothesis
    assert "관계가 있는가" in h, "가설이 의문형이 아니다"
    assert "가정하지 않는다" in h


def test_exp001_pins_rules_before_data_exists():
    """
    규칙을 미리 못박지 않으면 나중에 결과를 보고 유리한 정의를 고르게 된다.
    진입·청산·벤치마크가 전부 구체적이어야 한다.
    """
    exp = core_hypothesis_experiment("2026-08-15")
    assert "5분위" in exp.entry_rule
    assert "12개월" in exp.exit_rule
    assert "VOO" in exp.benchmark


def test_exp001_registers_as_blocked_with_measured_reason(tmp_path):
    """
    지금 실행할 수 없다는 사실과 그 이유(실측 수치)를 남긴다 - 재개 조건이
    없으면 실험은 잊힌다.
    """
    exp = core_hypothesis_experiment("2026-08-15")
    path = register_experiment(exp, status="BLOCKED",
                               blocked_reason=BLOCKED_REASON_EXP001,
                               experiment_dir=str(tmp_path))
    rec = json.loads(open(path, encoding="utf-8").read())

    assert rec["status"] == "BLOCKED"
    assert "9건" in rec["blocked_reason"], "차단 사유에 실측 표본수가 없다"
    assert "재개 조건" in rec["blocked_reason"]
    assert rec["results"] == []


def test_load_experiments_returns_registered(tmp_path):
    register_experiment(make_experiment(), experiment_dir=str(tmp_path))
    register_experiment(make_experiment(experiment_id="EXP-TEST2"),
                        experiment_dir=str(tmp_path))
    assert len(load_experiments(str(tmp_path))) == 2


# ──────────────────────────────────────────────────────────────────
# §10 재현 좌표 / §12 연구 순서 / §14 결과 판정 (v3.50)
# ──────────────────────────────────────────────────────────────────

def test_reproduction_coordinates_required(tmp_path):
    """
    §10: 어느 데이터·어느 코드로 낸 결과인지 특정할 수 없으면 결과 자체가
    재현 불가능하다. 비용 가정이 없으면 총수익이 체계적으로 과대평가된다(§13).
    """
    for f in ("analysis_as_of", "data_version", "methodology_version",
              "transaction_cost_assumption"):
        with pytest.raises(ValueError, match=f):
            make_experiment(**{f: "  "})


def test_finding_status_vocabulary_and_validation(tmp_path):
    """§14의 결과 판정은 실행 상태(status)와 다른 축이다."""
    assert FINDING_STATUSES == ("REJECTED", "INCONCLUSIVE", "PROMISING", "VALIDATED")

    path = register_experiment(make_experiment(), experiment_dir=str(tmp_path))
    with pytest.raises(ValueError, match="알 수 없는 결과 판정"):
        record_result(path, {"run": 1}, finding="ALPHA")


def test_completed_experiment_can_still_be_rejected(tmp_path):
    """
    ⚠️ COMPLETED(실행 끝남)와 VALIDATED(가설 입증)는 전혀 다르다. 끝났지만
    기각된 실험이 정상적으로 기록돼야 한다.
    """
    path = register_experiment(make_experiment(), experiment_dir=str(tmp_path))
    rec = record_result(path, {"spearman": -0.02, "n": 34},
                        status="COMPLETED", finding="REJECTED")
    assert rec["status"] == "COMPLETED" and rec["finding"] == "REJECTED"


def test_finding_changes_are_kept_as_history_not_overwritten(tmp_path):
    """
    판정이 바뀌었다면 그 사실 자체가 기록돼야 한다 - 덮어쓰면 "처음부터
    그렇게 봤다"가 된다.
    """
    path = register_experiment(make_experiment(), experiment_dir=str(tmp_path))
    record_result(path, {"run": 1}, finding="INCONCLUSIVE")
    rec = record_result(path, {"run": 2}, finding="REJECTED")

    assert [h["finding"] for h in rec["finding_history"]] == \
        ["INCONCLUSIVE", "REJECTED"]
    assert rec["finding"] == "REJECTED"


def test_research_sequence_pins_order_via_depends_on():
    """
    ⚠️ §12·§13: 결과를 본 뒤 순서를 바꿀 수 있으면 검증이 아니라 튜닝이다.
    의존관계가 **코어**(변경 불가)에 들어 있어야 한다.
    """
    seq = research_sequence("2026-08-15", "v3.50", "snapshot")
    by_id = {e.experiment_id: e for e in seq}

    assert [e.experiment_id for e in seq] == ["H-001", "H-002", "H-003", "H-004"]
    assert by_id["H-001"].depends_on == []
    assert by_id["H-002"].depends_on == ["H-001"]
    assert by_id["H-003"].depends_on == ["H-001"]
    assert by_id["H-004"].depends_on == ["H-001", "H-002"]
    assert "depends_on" in by_id["H-002"].core()   # 코어에 포함 = 변경 불가


def test_research_sequence_hypotheses_never_presuppose_direction():
    """네 가설 모두 의문형이며 방향을 단정하지 않는다(§11)."""
    for exp in research_sequence("2026-08-15", "v3.50", "snapshot"):
        assert "가정하지 않는다" in exp.hypothesis, exp.experiment_id
        assert "?" in exp.hypothesis, exp.experiment_id


def test_research_sequence_controls_survivorship_and_costs():
    """§13이 요구한 생존편향 통제와 비용 반영이 규칙에 명시돼야 한다."""
    for exp in research_sequence("2026-08-15", "v3.50", "snapshot"):
        assert "생존 편향" in exp.universe
        assert "bp" in exp.transaction_cost_assumption


def test_dependency_check_reports_unmet_but_does_not_block(tmp_path):
    """
    §12 순서는 드러내되 실행을 막지는 않는다(병기 원칙). 선행이 COMPLETED가
    아니면 미충족으로 보고한다.
    """
    for exp in research_sequence("2026-08-15", "v3.50", "snapshot")[:2]:
        register_experiment(exp, status="BLOCKED",
                            blocked_reason=BLOCKED_REASON_SEQUENCE,
                            experiment_dir=str(tmp_path))

    assert check_dependencies_satisfied("H-001", str(tmp_path))["satisfied"] is True
    dep = check_dependencies_satisfied("H-002", str(tmp_path))
    assert dep["satisfied"] is False
    assert "BLOCKED" in dep["unmet"][0]["reason"]
    assert "막지 않는다" in dep["note"]


def test_dependency_requires_finding_not_just_completion(tmp_path):
    """
    선행 실험이 '끝났다'만으로는 부족하다 - 결과 판정이 있어야 다음 단계의
    기준선이 생긴다.
    """
    seq = research_sequence("2026-08-15", "v3.50", "snapshot")[:2]
    p1 = register_experiment(seq[0], status="BLOCKED",
                             blocked_reason=BLOCKED_REASON_SEQUENCE,
                             experiment_dir=str(tmp_path))
    register_experiment(seq[1], status="BLOCKED",
                        blocked_reason=BLOCKED_REASON_SEQUENCE,
                        experiment_dir=str(tmp_path))

    record_result(p1, {"run": 1}, status="COMPLETED")      # finding 없음
    dep = check_dependencies_satisfied("H-002", str(tmp_path))
    assert dep["satisfied"] is False
    assert "finding" in dep["unmet"][0]["reason"]

    record_result(p1, {"run": 2}, status="COMPLETED", finding="REJECTED")
    assert check_dependencies_satisfied("H-002", str(tmp_path))["satisfied"] is True


def test_superseded_status_available_so_old_experiments_are_not_deleted():
    """구버전 실험도 삭제하지 않고 SUPERSEDED로 남긴다(§10)."""
    assert "SUPERSEDED" in EXPERIMENT_STATUSES


def test_registered_sequence_in_repo_is_intact():
    """
    저장소에 실제로 등록된 실험들이 순서·상태를 유지하는지 확인한다.
    누군가 H-002를 H-001보다 먼저 돌리면 여기서 드러난다.
    """
    import os

    if not os.path.isdir("experiments"):
        return
    ids = {r["core"]["experiment_id"] for r in load_experiments()}
    if "H-001" not in ids:
        return
    for eid in ("H-002", "H-003", "H-004"):
        dep = check_dependencies_satisfied(eid)
        assert dep["satisfied"] is False, (
            f"{eid}의 선행 실험이 완료된 적 없는데 충족으로 나온다"
        )
