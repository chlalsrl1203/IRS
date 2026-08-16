"""
Investment Case 테스트 (계약서 §3).

핵심: (1) 새 계산을 하지 않고 조합만 하는지, (2) signal/decision 경계를
지키는지, (3) 빈 필드를 추측으로 채우지 않는지, (4) 시간이 지나야 정의되는
필드를 '누락'으로 오판하지 않는지.
"""

import glob
import json
import tempfile

import pytest

from engine.investment_case import (
    CASE_FIELDS,
    DECISION_FIELDS,
    SIGNAL_AT_ANALYSIS,
    SIGNAL_OVER_TIME,
    build_case,
    case_completeness,
    format_case_summary,
    fundamental_view,
)
from engine.thesis import (
    DECISION_ACTIONS,
    InvestmentThesis,
    build_decision,
    load_thesis,
    record_decision,
    save_thesis,
)

LEDGER = json.load(open(sorted(glob.glob("ledger/BSX_*.json"))[-1], encoding="utf-8"))


def full_gates():
    return {g: f"{g} 근거" for g in (
        "signal_summary", "business_quality", "financial_quality",
        "risk_assessment", "valuation_assessment", "portfolio_context")}


def make_thesis_record(tmp_dir, action="WATCH"):
    t = InvestmentThesis(
        ticker="BSX", thesis_date="2026-08-15",
        why_buy="근거 기반 기대가 가격이 요구하는 성장률을 상회한다",
        market_assumption="시장은 리콜·소송으로 EP 성장 지속성을 할인하고 있다",
        irs_view="PFA 하위세그먼트 점유 우위가 경쟁강도 입력을 낮춘다",
        key_drivers=["EP 부문 성장"], expected_outcomes=["두 자릿수 성장 유지"],
        catalysts=["FY2026 Q3 실적"], risks=["J&J 반격"],
        invalidation_conditions=[{"condition": "EP 성장 한 자릿수 둔화",
                                  "check_by": "2026-11-30"}],
        holding_horizon="3~5년", linked_ledger="BSX_2026-08-13.json",
    )
    path = save_thesis(t, thesis_dir=tmp_dir)
    record_decision(path, build_decision(t.thesis_id, "2026-08-15", action,
                                         full_gates(), "판단 근거"))
    return load_thesis("BSX", "2026-08-15", thesis_dir=tmp_dir)


# ──────────────────────────────────────────────────────────────────
# §3의 14개 필드
# ──────────────────────────────────────────────────────────────────

def test_case_covers_all_fourteen_spec_fields():
    assert len(CASE_FIELDS) == 14
    assert set(CASE_FIELDS) == set(SIGNAL_AT_ANALYSIS) | set(SIGNAL_OVER_TIME) | set(DECISION_FIELDS)


def test_case_reuses_existing_values_without_recomputing():
    """
    ⚠️ §3은 '얇은 계층'을 요구한다 - 새 valuation 로직을 만들면 안 된다.
    Gap·판정·Implied Growth가 ledger 값과 **정확히 같아야** 한다.
    """
    case = build_case(LEDGER)
    assert case["expectation_gap"] == LEDGER["expectation_gap"]
    assert case["judgment"] == LEDGER["judgment"]
    assert case["valuation_implied_requirement"] == LEDGER["implied_growth"]["value"]
    assert case["fundamental_view"]["evidence_supported_expectation"] == \
        LEDGER["growth"]["realistic_growth"]


def test_fundamental_view_is_price_independent():
    """
    Fundamental Reality는 재무제표에서만 나온다 - 시가총액이 바뀌어도 불변이며,
    그래야 "사업이 좋아졌나 주가만 빠졌나"를 가를 기준선이 된다.
    """
    fv = fundamental_view(LEDGER)
    for key in ("revenue_cagr_5y", "fcf_cagr_5y", "fcf0",
                "evidence_supported_expectation"):
        assert fv[key] is not None
    assert "시가총액" in fv["note"] or "주가" in fv["note"]


# ──────────────────────────────────────────────────────────────────
# Signal / Decision 경계
# ──────────────────────────────────────────────────────────────────

def test_case_without_thesis_has_no_decision():
    """
    thesis가 없으면 decision은 None이고, 그게 **정확한 상태**다(아직 판단하지
    않은 종목). 신호가 있다고 결정을 지어내지 않는다.
    """
    case = build_case(LEDGER)
    assert case["decision"] is None
    assert case["completeness"]["stage"] == "SIGNAL_ONLY"
    assert case["completeness"]["signal_complete"] is True
    assert case["completeness"]["decision_complete"] is False


def test_build_case_never_creates_a_decision():
    """
    ⚠️ §3: Expectation Gap이 BUY를 직접 결정해서는 안 된다. build_case는
    이미 기록된 결정을 **참조만** 하며, Gap이 아무리 커도 결정을 만들지 않는다.
    """
    huge = json.loads(json.dumps(LEDGER))
    huge["expectation_gap"] = 0.50          # 극단적 저평가 신호
    huge["judgment"] = "저평가 가능성"
    case = build_case(huge)
    assert case["decision"] is None
    assert "직접 결정하지 않는다" in case["separation_note"]


def test_case_with_thesis_and_decision_is_complete():
    with tempfile.TemporaryDirectory() as d:
        case = build_case(LEDGER, thesis_record=make_thesis_record(d),
                          market_cap_now=LEDGER["inputs"]["market_cap"] * 0.9)
    assert case["completeness"]["stage"] == "DECIDED"
    assert case["completeness"]["missing_fields"] == []
    assert case["decision"]["action"] == "WATCH"


def test_decision_history_is_preserved_not_just_latest():
    """결정은 append-only이므로 이력 전체가 남아야 사후 추적이 가능하다."""
    with tempfile.TemporaryDirectory() as d:
        rec = make_thesis_record(d, action="WATCH")
        case = build_case(LEDGER, thesis_record=rec)
    assert case["decision_history"][-1] == case["decision"]
    assert len(case["decision_history"]) == 1


# ──────────────────────────────────────────────────────────────────
# 시간 의존 필드를 '누락'으로 오판하지 않는다
# ──────────────────────────────────────────────────────────────────

def test_time_dependent_fields_do_not_mark_fresh_analysis_incomplete():
    """
    ⚠️ gap_change/gap_drivers는 **비교 대상이 생겨야** 정의된다. 분석 직후엔
    값이 없는 게 정상인데 이를 누락으로 세면 모든 신규 분석이 INCOMPLETE로
    찍혀 플래그 자체가 무의미해진다(초판이 실제로 그랬다).
    """
    c = build_case(LEDGER)["completeness"]
    assert c["stage"] == "SIGNAL_ONLY"          # INCOMPLETE가 아니다
    assert c["time_dependent_pending"] == list(SIGNAL_OVER_TIME)
    assert c["signal_complete"] is True


def test_time_dependent_fields_fill_in_when_current_data_supplied():
    case = build_case(LEDGER, market_cap_now=LEDGER["inputs"]["market_cap"] * 0.8)
    assert case["gap_change"] is not None
    assert case["gap_drivers"] is not None
    assert case["completeness"]["time_dependent_pending"] == []


def test_missing_fields_are_listed_not_filled():
    """빈 것을 추측으로 채우지 않고 목록으로 드러낸다."""
    c = build_case(LEDGER)["completeness"]
    assert "decision" in c["missing_fields"]
    assert "thesis" in c["missing_fields"]


# ──────────────────────────────────────────────────────────────────
# PASS 어휘 (§3) - 기존 어휘 호환 유지
# ──────────────────────────────────────────────────────────────────

def test_pass_action_is_available_and_distinct_from_watch():
    """
    PASS(투자 대상 아님으로 결론)와 WATCH(아직 아니지만 계속 봄)는 다르다.
    구분이 없으면 "안 산다"가 전부 WATCH로 뭉뚱그려져 감시 목록이 무한히
    늘어나고 무엇을 왜 버렸는지가 사라진다.
    """
    assert "PASS" in DECISION_ACTIONS and "WATCH" in DECISION_ACTIONS
    p = build_decision("X-1", "2026-08-15", "PASS", full_gates(), "투자 대상 아님")
    w = build_decision("X-1", "2026-08-15", "WATCH", full_gates(), "조건 대기")
    assert p["action"] != w["action"]


def test_existing_vocabulary_preserved_for_compatibility():
    """
    ⚠️ §3: "기존 judgment vocabulary가 존재한다면 compatibility를 유지한다."
    v3.48에 있던 6개는 하나도 사라지면 안 된다(기존 기록이 무효화된다).
    """
    for legacy in ("BUY", "ADD", "HOLD", "WATCH", "REDUCE", "SELL"):
        assert legacy in DECISION_ACTIONS


@pytest.mark.parametrize("action", DECISION_ACTIONS)
def test_every_action_still_requires_all_gates(action):
    """PASS도 예외가 아니다 - '안 산다'는 결정에도 근거가 필요하다."""
    gates = full_gates()
    gates["risk_assessment"] = "  "
    with pytest.raises(ValueError, match="관문 근거"):
        build_decision("X-1", "2026-08-15", action, gates, "근거")


# ──────────────────────────────────────────────────────────────────
# 요약 출력
# ──────────────────────────────────────────────────────────────────

def test_summary_renders_without_decision():
    out = format_case_summary(build_case(LEDGER))
    assert "SIGNAL_ONLY" in out
    assert "신호까지만" in out


def test_all_existing_ledgers_are_signal_only():
    """
    저장소의 현재 상태를 사실대로 고정한다 - 34종목 전부 계산만 있고 투자
    판단 기록이 없다. 누군가 thesis를 기록하면 여기서 깨지고, 그때 이 사실
    서술을 갱신하게 된다.
    """
    for path in sorted(glob.glob("ledger/*.json")):
        led = json.load(open(path, encoding="utf-8"))
        stage = build_case(led)["completeness"]["stage"]
        assert stage == "SIGNAL_ONLY", f"{path}: {stage}"
