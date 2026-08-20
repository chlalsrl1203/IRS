"""
P0-16 Refresh Boundary 테스트.

# SOURCE:
https://github.com/byteseek/Mira (Apache-2.0) — stale_after / must_refresh_if

# METHOD:
ADAPT — 개념만 가져왔다. `engine/thesis.py`가 이미 존재하므로 새 모듈을 만들지
않고 기존 타입에 opt-in 필드를 얹었다(§1.11).

고정하는 불변조건:
  ① `UNBOUNDED`는 `FRESH`가 아니다 (경계 미설정을 안전 신호로 읽지 않는다)
  ② 조건 발동은 기한보다 우선한다 ("아직 기한 전이니 괜찮다"를 막는다)
  ③ 파싱되지 않는 경계는 거부한다
  ④ 기존 논거(경계 없음)는 그대로 동작한다 (opt-in, 비파괴)
  ⑤ 발동 표시는 분석자가 명시적으로 한다 (자동판정 금지)
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.thesis import (  # noqa: E402
    REFRESH_STATES, InvestmentThesis, mark_refresh_required, refresh_status,
    save_thesis,
)


def thesis(**kw):
    base = dict(
        ticker="TTD", thesis_date="2026-08-03",
        why_buy="시장이 거버넌스 리스크를 과도하게 반영했다",
        market_assumption="시장은 광고 점유율 상실을 확정으로 본다",
        irs_view="CEO 자사주 직접매수는 진성 강세신호다",
        key_drivers=["CTV 광고 전환"], expected_outcomes=["Q3 매출 성장 재가속"],
        catalysts=["Q3 실적"], risks=["Amazon DSP 점유율 확대"],
        invalidation_conditions=[{"condition": "Q2 매출이 가이던스 하회",
                                  "check_by": "2026-08-06"}],
        holding_horizon="3년",
    )
    base.update(kw)
    return InvestmentThesis(**base)


# ── ① UNBOUNDED ≠ FRESH ──────────────────────────────────────────────────
def test_unbounded_is_a_distinct_state_from_fresh():
    """경계를 안 정한 것을 '아직 신선하다'로 읽으면 안 된다."""
    r = refresh_status(thesis(), today="2030-01-01")
    assert r["status"] == "UNBOUNDED"
    assert r["status"] != "FRESH"
    assert "안전 신호로 읽지 말 것" in r["reason"]


def test_state_vocabulary_keeps_unbounded_separate():
    assert set(REFRESH_STATES) == {"FRESH", "STALE", "MUST_REFRESH", "UNBOUNDED"}


def test_within_boundary_is_fresh():
    r = refresh_status(thesis(stale_after="2026-11-30"), today="2026-08-19")
    assert r["status"] == "FRESH" and r["stale_after"] == "2026-11-30"


def test_past_boundary_is_stale():
    r = refresh_status(thesis(stale_after="2026-08-06"), today="2026-08-19")
    assert r["status"] == "STALE"
    assert "재확인 없이 이 논거를 인용하지 말 것" in r["reason"]


# ── ② 조건 발동이 기한보다 우선한다 ──────────────────────────────────────
def test_triggered_condition_outranks_a_still_valid_date():
    """
    '아직 기한 전이니 괜찮다'가 정확히 이 저장소가 반증조건에서 겪은 실패
    방식이다(트리거 날짜 5건이 지났는데 12일간 아무도 안 봄).
    """
    t = thesis(stale_after="2027-12-31",
               must_refresh_if=[{"condition": "경영진 3인 이상 동시 교체",
                                 "triggered": True,
                                 "triggered_note": "CFO·CMO·커머셜총괄 동시 교체"}])
    r = refresh_status(t, today="2026-08-19")
    assert r["status"] == "MUST_REFRESH"
    assert "기한이 남아 있어도" in r["reason"]
    assert len(r["triggered_conditions"]) == 1


def test_untriggered_conditions_do_not_force_refresh():
    t = thesis(stale_after="2027-12-31",
               must_refresh_if=[{"condition": "경영진 교체"}])
    assert refresh_status(t, today="2026-08-19")["status"] == "FRESH"


# ── ③ 파싱되지 않는 경계는 거부 ──────────────────────────────────────────
def test_unparseable_boundary_is_rejected():
    with pytest.raises(ValueError, match="파싱되지 않는 경계는 경계가 아니다"):
        thesis(stale_after="2026년 말쯤")


def test_boundary_before_thesis_date_is_rejected():
    with pytest.raises(ValueError, match="만들자마자 낡은 논거는 논거가 아니다"):
        thesis(stale_after="2026-08-01")        # thesis_date 2026-08-03보다 앞


def test_malformed_refresh_condition_is_rejected():
    with pytest.raises(ValueError, match="must_refresh_if"):
        thesis(must_refresh_if=["문자열은 안 된다"])


# ── ④ opt-in / 비파괴 ────────────────────────────────────────────────────
def test_existing_theses_without_boundaries_still_work():
    """기존 경로를 깨지 않는다 — 필드는 opt-in이다."""
    t = thesis()
    assert t.stale_after is None and t.must_refresh_if is None
    assert t.thesis_id == "TTD-2026-08-03"


def test_boundary_survives_serialization(tmp_path):
    t = thesis(stale_after="2026-11-30",
               must_refresh_if=[{"condition": "Q3 매출 역성장"}])
    path = save_thesis(t, thesis_dir=str(tmp_path))
    import json
    rec = json.load(open(path, encoding="utf-8"))
    assert rec["thesis"]["stale_after"] == "2026-11-30"
    assert rec["thesis"]["must_refresh_if"][0]["triggered"] is False
    # 저장된 기록으로도 판정이 된다
    assert refresh_status(rec, today="2026-12-01")["status"] == "STALE"


# ── ⑤ 발동은 명시적으로 ──────────────────────────────────────────────────
def test_marking_refresh_required_is_explicit_and_persisted(tmp_path):
    """정규식은 트리거 날짜와 서술적 날짜를 구분하지 못한다(v3.42)."""
    t = thesis(stale_after="2027-12-31",
               must_refresh_if=[{"condition": "경영진 3인 이상 동시 교체"}])
    path = save_thesis(t, thesis_dir=str(tmp_path))
    assert refresh_status(t, today="2026-08-19")["status"] == "FRESH"

    rec = mark_refresh_required(path, 0, "CFO·CMO·커머셜총괄 동시 교체 확인")
    assert rec["thesis"]["must_refresh_if"][0]["triggered"] is True
    assert refresh_status(rec, today="2026-08-19")["status"] == "MUST_REFRESH"


def test_marking_a_nonexistent_condition_raises(tmp_path):
    path = save_thesis(thesis(), thesis_dir=str(tmp_path))
    with pytest.raises(IndexError):
        mark_refresh_required(path, 0, "없는 조건")


def test_refresh_note_cannot_be_blank(tmp_path):
    t = thesis(must_refresh_if=[{"condition": "x"}])
    path = save_thesis(t, thesis_dir=str(tmp_path))
    with pytest.raises(ValueError):
        mark_refresh_required(path, 0, "   ")
