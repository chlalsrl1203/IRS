"""
P0-13 Hard Gates 테스트.

# SOURCE:
https://github.com/DimaMerc/TieOutBench (MIT)

고정하는 불변조건:
  ① 하드 게이트는 감점이 아니라 **자동 실패**다 (총점으로 상쇄되지 않는다)
  ② 검사하지 않은 게이트(vacuous)를 통과로 세지 않는다
  ③ "판단 불가"는 실패가 아니라 credit이다
  ④ `PIT_UNKNOWN`은 실패가 아니고 `PIT_INVALID`는 실패다
  ⑤ GATE.MATCH는 self_check_v2에 위임한다 (중복 구현 금지)
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.evaluation.gates import (  # noqa: E402
    GATES, UNCERTAINTY_MARKERS, VALIDATION_STATUS,
    calibrated_uncertainty_credit, gate_direction, gate_fabrication,
    gate_lookahead, gate_recon, gate_scale, run_hard_gates,
)

MEMO_OK = (
    "결론: 저평가 가능성.\n"
    "Implied Growth 8.00%\nRealistic Growth 13.86%\nExpectation Gap 5.87%p\n"
    "DRS: 43.8\nRAR: 0.4926\n10. Bear Case: 경쟁 심화 시 마진 훼손.\n"
)
CTX_OK = {
    "implied_growth": 0.08, "realistic_growth": 0.1386,
    "expectation_gap": 0.0587, "drs": 43.8, "rar": 0.4926,
    "labeled_values": {"Implied Growth": 0.08, "Realistic Growth": 0.1386,
                       "Expectation Gap": 0.0587},
}


# ── ① 자동 실패 ──────────────────────────────────────────────────────────
def test_all_gates_pass_on_a_consistent_memo():
    r = run_hard_gates(MEMO_OK, CTX_OK)
    assert r["passed"] is True and r["n_failed"] == 0


def test_one_failed_gate_fails_everything_regardless_of_the_rest():
    """총점으로 상쇄하지 않는다 — 이것이 하드 게이트의 존재 이유다."""
    memo = MEMO_OK.replace("Expectation Gap 5.87%p", "Expectation Gap 25.87%p")
    r = run_hard_gates(memo, CTX_OK)
    assert r["passed"] is False
    assert "GATE.FABRICATION" in r["failed_gates"]
    # 다른 게이트가 여러 개 통과해도 전체는 실패다
    assert r["n_gates"] - r["n_failed"] >= 3


def test_fabricated_number_is_auto_fail_not_a_deduction():
    """TYL SBC 3배 오류의 형태 — 계산 결과와 대응하지 않는 수치."""
    memo = "SBC/FCF 62.0% 로 트래커 최고 수준이다."
    r = gate_fabrication(memo, {"labeled_values": {"SBC/FCF": 0.244}})
    assert r.passed is False
    assert "자동 실패" in r.reason
    assert r.detail["mismatches"][0]["stated"] == pytest.approx(0.62)


def test_missing_labeled_value_in_memo_is_also_a_fabrication_failure():
    r = gate_fabrication("아무 수치도 없다", {"labeled_values": {"Gap": 0.05}})
    assert r.passed is False and r.detail["mismatches"][0]["issue"] == "메모에 없음"


# ── 스케일 / 부호 ────────────────────────────────────────────────────────
def test_scale_error_is_separated_from_plain_mismatch():
    """RAR 100배 오류(v3.19) — 원인과 조치가 단순 불일치와 다르다."""
    r = gate_scale("Expectation Gap 587.00%p", {"labeled_values": {"Expectation Gap": 0.0587}})
    assert r.passed is False and r.detail["hits"][0]["factor"] == 100


def test_thousand_fold_scale_error_is_caught():
    r = gate_scale("Realistic Growth 13860.00%",
                   {"labeled_values": {"Realistic Growth": 0.1386}})
    assert r.passed is False and r.detail["hits"][0]["factor"] == 1_000


def test_sign_flip_fails_regardless_of_magnitude():
    r = gate_direction("Expectation Gap -5.87%p",
                       {"labeled_values": {"Expectation Gap": 0.0587}})
    assert r.passed is False
    assert "크기와 무관하게" in r.reason


def test_matching_sign_and_value_passes_direction():
    assert gate_direction(MEMO_OK, CTX_OK).passed is True


# ── ② vacuous를 통과로 세지 않는다 ──────────────────────────────────────
def test_gates_without_data_are_marked_vacuous_not_silently_passed():
    r = run_hard_gates("", {})
    assert r["passed"] is True                 # 실패는 아니지만
    assert r["n_vacuous"] >= 3                 # 아무것도 보증하지 않는다
    assert "GATE.RECON" in r["vacuous_gates"]
    assert "검사 자체를 하지 않았다" in r["note"]


def test_recon_without_data_does_not_fail_but_declares_nothing():
    r = gate_recon("메모", {})
    assert r.passed is True and r.detail["vacuous"] is True
    assert "아무것도 보증하지 않는다" in r.reason


def test_unresolved_reconciliation_conflicts_fail():
    """P0-07이 8종목 336개 값 중 67건의 물질적 불일치를 찾았다."""
    r = gate_recon("메모", {"reconciliation": {
        "n_values": 44, "n_unresolved": 11,
        "unresolved": [{"metric": "operating_income", "fiscal_year": 2025}]}})
    assert r.passed is False
    assert "어느 출처를 썼는지 모르는 결론" in r.reason


# ── ④ PIT ────────────────────────────────────────────────────────────────
def test_pit_unknown_is_not_a_failure():
    """34종목이 전부 이 상태다 — 모른다고 말하는 것을 실패로 처리하지 않는다."""
    r = gate_lookahead("메모", {"point_in_time": {"status": "PIT_UNKNOWN"}})
    assert r.passed is True and r.detail["pit_unknown"] is True


def test_pit_violation_is_a_failure():
    r = gate_lookahead("메모", {"point_in_time": {
        "status": "PIT_INVALID",
        "violations": [{"fiscal_year": 2025, "filed": "2026-02-17",
                        "analysis_as_of": "2026-01-01"}]}})
    assert r.passed is False
    assert "계산 전제 자체가 무너진다" in r.reason


def test_pit_valid_passes_and_is_not_marked_unknown():
    r = gate_lookahead("메모", {"point_in_time": {"status": "PIT_VALID",
                                                 "violations": []}})
    assert r.passed is True and r.detail["pit_unknown"] is False


# ── ③ calibrated uncertainty ─────────────────────────────────────────────
def test_saying_not_determinable_is_credited_not_penalized():
    c = calibrated_uncertainty_credit(
        "이 항목은 자료 부족으로 판단 불가다.", {})
    assert c["n_markers"] >= 1
    assert c["acknowledged"] is True
    assert "실패가 아니다" in c["note"]


def test_unacknowledged_system_unknowns_are_flagged_but_not_scored():
    """감점이 아니라 **누락 표시**다."""
    c = calibrated_uncertainty_credit("모든 것이 확실하다.", {
        "point_in_time": {"status": "PIT_UNKNOWN"},
        "governance": {"decision": "UNVERIFIED", "provider": "Alpha Vantage"},
    })
    assert c["acknowledged"] is False
    assert "PIT 미검증" in c["system_known_unknowns"]
    assert any("Alpha Vantage" in x for x in c["system_known_unknowns"])
    assert "score" not in c and "penalty" not in c


def test_uncertainty_markers_include_this_projects_own_vocabulary():
    for token in ("미확인", "원인불명", "PIT_UNKNOWN", "PROVENANCE_UNKNOWN"):
        assert token in UNCERTAINTY_MARKERS


# ── ⑤ 중복 구현 금지 ─────────────────────────────────────────────────────
def test_gate_match_delegates_to_self_check_v2():
    """같은 검사를 다시 구현하면 두 구현이 미묘하게 어긋난다(§1.11)."""
    import engine.self_check_v2 as sc
    called = []
    orig = sc.run_self_check_v2
    sc.run_self_check_v2 = lambda memo, ctx: called.append((memo, ctx))
    try:
        r = GATES["GATE.MATCH"](MEMO_OK, CTX_OK)
    finally:
        sc.run_self_check_v2 = orig
    assert called and r.passed is True


def test_gate_match_reports_self_check_failure():
    memo = MEMO_OK.replace("DRS: 43.8", "DRS: 99.9")
    r = GATES["GATE.MATCH"](memo, CTX_OK)
    assert r.passed is False and "self_check_v2" in r.detail["detail"]


# ── 인식론적 지위 ────────────────────────────────────────────────────────
def test_gates_declare_they_are_not_linked_to_investment_outcomes():
    assert "증거는 0건" in VALIDATION_STATUS["hard_gates"]
    assert "IMPLEMENTED_NOT_VALIDATED" in VALIDATION_STATUS["calibrated_uncertainty"]


def test_unimplemented_upstream_gates_are_absent_on_purpose():
    """
    원본의 GATE.BRIDGE·GATE.FREELUNCH·GATE.BASIS는 IRS에 실증 사고가 없어
    넣지 않았다. 실증 없이 게이트를 늘리면 통과 의례만 늘어난다.
    """
    for absent in ("GATE.BRIDGE", "GATE.FREELUNCH", "GATE.BASIS"):
        assert absent not in GATES
