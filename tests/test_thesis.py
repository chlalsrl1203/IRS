"""
Investment Thesis / Decision / 모니터링 테스트.

가장 중요한 테스트는 `test_no_function_maps_gap_to_action`이다 - 이 모듈의
존재 이유가 "Gap에서 매수를 자동 도출하지 않는다"이므로, 그 경계가 실수로
뚫리면 여기서 잡혀야 한다.
"""

import json

import pytest

from engine.thesis import (
    DECISION_ACTIONS,
    DECISION_GATES,
    THESIS_STATUSES,
    InvestmentThesis,
    build_decision,
    build_evidence,
    evaluate_thesis_status,
    latest_thesis,
    load_thesis,
    mark_invalidation_triggered,
    record_decision,
    record_evidence,
    save_thesis,
)


def make_thesis(**overrides):
    base = dict(
        ticker="CDNS",
        thesis_date="2026-08-15",
        why_buy="EDA 과점 구조에서 백로그가 사상최대이나 시장은 Synopsys/Ansys 합병 위협을 과대반영했다.",
        market_assumption="시장은 Implied Growth 8.71%를 요구 - 합병 이후 점유율 잠식을 가정한 수준.",
        irs_view="재무 실적 기반 현실적 성장률은 12.00%로, 시장 요구치보다 높다.",
        key_drivers=["백로그 전환율", "AI 칩 설계 수요", "Synopsys 합병 후 점유율"],
        expected_outcomes=["FY2026 매출 성장률 10% 이상 유지"],
        catalysts=["FY2026 Q3 실적"],
        risks=["Synopsys-Ansys 통합 시너지가 실제 점유율 잠식으로 이어질 위험"],
        invalidation_conditions=[
            {"condition": "FY2026 Q3에서 매출 성장률이 5% 아래로 떨어지면 재검토",
             "check_by": "2026-11-30"},
        ],
        holding_horizon="3~5년",
        linked_ledger="CDNS_2026-07-25.json",
    )
    base.update(overrides)
    return InvestmentThesis(**base)


def full_gates():
    return {
        "signal_summary": "Gap +3.29%p, 적정가/경계선. 신호는 약하다.",
        "business_quality": "EDA 3사 과점, 전환비용 높음. 백로그 사상최대.",
        "financial_quality": "FCF 마진 30%대, SBC/OCF 26~27%로 다소 높음.",
        "risk_assessment": "DRS 36.6(트래커 하위권). 수출규제 노출 있으나 완화 추세.",
        "valuation_assessment": "Implied Growth 8.71% vs 현실적 성장률 12.00%.",
        "portfolio_context": "growth_platform 버킷 이미 41% - 추가 편입 시 집중도 주의.",
    }


# ──────────────────────────────────────────────────────────────────
# §5 Signal / Decision 분리 - 이 파일에서 가장 중요한 테스트
# ──────────────────────────────────────────────────────────────────

def test_no_function_maps_gap_to_action():
    """
    ⚠️ 이 모듈의 존재 이유. Gap(숫자) 하나를 받아 액션을 돌려주는 함수가
    있으면 미검증 신호가 곧바로 자본배분 결정이 된다(§5 명시적 금지).

    engine/thesis.py의 어떤 공개 함수도 그런 시그니처를 갖지 않아야 한다.
    """
    import inspect

    import engine.thesis as t

    for name, fn in inspect.getmembers(t, inspect.isfunction):
        if name.startswith("_") or fn.__module__ != "engine.thesis":
            continue
        params = list(inspect.signature(fn).parameters)
        # gap/expectation_gap을 받는 함수 자체가 없어야 한다
        assert not any(p in ("gap", "expectation_gap", "grade") for p in params), (
            f"{name}()이 Gap을 직접 인자로 받는다 - Gap->액션 자동 매핑 위험"
        )


def test_decision_requires_every_gate():
    """관문 근거가 하나라도 비면 결정을 기록할 수 없다(근거 필수화 패턴)."""
    for missing in DECISION_GATES:
        gates = full_gates()
        gates[missing] = "   "
        with pytest.raises(ValueError, match="관문 근거"):
            build_decision("CDNS-2026-08-15", "2026-08-15", "BUY", gates, "근거")


def test_decision_action_is_analyst_supplied_not_computed():
    """
    같은 신호·같은 관문 근거로 서로 다른 액션을 기록할 수 있어야 한다 -
    액션이 계산된 값이 아니라 분석자 판단임을 구조로 증명한다.
    """
    gates = full_gates()
    buy = build_decision("CDNS-2026-08-15", "2026-08-15", "BUY", gates, "근거")
    watch = build_decision("CDNS-2026-08-15", "2026-08-15", "WATCH", gates, "근거")

    assert buy["action"] == "BUY" and watch["action"] == "WATCH"
    assert buy["gates"] == watch["gates"]
    assert "analyst_recorded" in buy["action_source"]


def test_unknown_action_rejected():
    with pytest.raises(ValueError, match="알 수 없는 액션"):
        build_decision("CDNS-2026-08-15", "2026-08-15", "STRONG_BUY",
                       full_gates(), "근거")


# ──────────────────────────────────────────────────────────────────
# §4 Thesis 스키마
# ──────────────────────────────────────────────────────────────────

def test_thesis_requires_all_core_questions_answered():
    for f in ("why_buy", "market_assumption", "irs_view", "holding_horizon"):
        with pytest.raises(ValueError, match=f):
            make_thesis(**{f: "  "})


def test_thesis_requires_structured_invalidation_conditions():
    """반증조건은 이 프로젝트가 사후합리화를 막는 유일한 실질적 장치다."""
    with pytest.raises(ValueError, match="invalidation_conditions"):
        make_thesis(invalidation_conditions=[])
    with pytest.raises(ValueError, match="invalidation_conditions"):
        make_thesis(invalidation_conditions=["문자열은 안 됨"])


def test_thesis_id_is_deterministic():
    """prediction이 이 ID로 thesis를 참조하므로 안정적이어야 한다."""
    assert make_thesis().thesis_id == "CDNS-2026-08-15"
    assert make_thesis(ticker="cdns").thesis_id == "CDNS-2026-08-15"


# ──────────────────────────────────────────────────────────────────
# 기록 무결성 - 코어 불변 / 로그 append-only
# ──────────────────────────────────────────────────────────────────

def test_thesis_core_cannot_be_overwritten(tmp_path):
    save_thesis(make_thesis(), thesis_dir=str(tmp_path))
    with pytest.raises(FileExistsError, match="변경 불가"):
        save_thesis(make_thesis(), thesis_dir=str(tmp_path))


def test_decisions_and_evidence_are_append_only(tmp_path):
    path = save_thesis(make_thesis(), thesis_dir=str(tmp_path))

    record_decision(path, build_decision("CDNS-2026-08-15", "2026-08-15",
                                         "WATCH", full_gates(), "관찰 시작"))
    record_decision(path, build_decision("CDNS-2026-08-15", "2026-09-01",
                                         "BUY", full_gates(), "Q3 확인 후 진입"))
    record_evidence(path, build_evidence("2026-09-01", "Q3 매출 +11%",
                                         "supports", "회사 실적발표"))

    rec = json.loads(open(path, encoding="utf-8").read())
    assert [d["action"] for d in rec["decisions"]] == ["WATCH", "BUY"]
    assert len(rec["evidence"]) == 1
    # 첫 결정이 그대로 남아 있어야 한다(덮어쓰기 없음)
    assert rec["decisions"][0]["rationale"] == "관찰 시작"


def test_invalidation_trigger_is_explicit_never_automatic(tmp_path):
    """
    v3.42가 확립한 원칙: 코드가 텍스트를 읽고 반증조건 발동을 자동 판정하면
    서술적 날짜를 트리거로 오인한다. 분석자가 명시적으로 표시해야만 발동한다.
    """
    path = save_thesis(make_thesis(), thesis_dir=str(tmp_path))
    rec = json.loads(open(path, encoding="utf-8").read())
    assert rec["thesis"]["invalidation_conditions"][0]["triggered"] is False

    mark_invalidation_triggered(path, 0, "Q3 매출 성장률 3.1%로 확인")
    rec = json.loads(open(path, encoding="utf-8").read())
    assert rec["thesis"]["invalidation_conditions"][0]["triggered"] is True

    # 두 번 발동시키거나 되돌리는 경로는 없다
    with pytest.raises(ValueError, match="이미 발동"):
        mark_invalidation_triggered(path, 0, "재표시")


# ──────────────────────────────────────────────────────────────────
# §7 모니터링 상태
# ──────────────────────────────────────────────────────────────────

def test_status_starts_stable_with_no_evidence(tmp_path):
    path = save_thesis(make_thesis(), thesis_dir=str(tmp_path))
    rec = load_thesis("CDNS", "2026-08-15", thesis_dir=str(tmp_path))
    assert evaluate_thesis_status(rec)["status"] == "STABLE"


@pytest.mark.parametrize("directions,expected", [
    (["supports", "supports"], "STRENGTHENING"),
    (["contradicts"], "WEAKENING"),
    (["supports", "contradicts"], "STABLE"),
    (["neutral"], "STABLE"),
])
def test_status_tally_rule(tmp_path, directions, expected):
    path = save_thesis(make_thesis(), thesis_dir=str(tmp_path))
    for i, d in enumerate(directions):
        record_evidence(path, build_evidence(f"2026-09-0{i+1}", f"증거{i}", d, "출처"))
    rec = load_thesis("CDNS", "2026-08-15", thesis_dir=str(tmp_path))
    assert evaluate_thesis_status(rec)["status"] == expected


def test_triggered_invalidation_overrides_all_supporting_evidence(tmp_path):
    """
    ⚠️ 사전등록된 반증조건이 발동했는데 "그래도 좋아 보인다"고 넘어가는 것이
    정확히 사후합리화다. 지지 증거가 아무리 많아도 INVALIDATED가 이긴다.
    """
    path = save_thesis(make_thesis(), thesis_dir=str(tmp_path))
    for i in range(5):
        record_evidence(path, build_evidence(f"2026-09-0{i+1}", f"좋은 소식{i}",
                                             "supports", "출처"))
    mark_invalidation_triggered(path, 0, "조건 발동 확인")

    rec = load_thesis("CDNS", "2026-08-15", thesis_dir=str(tmp_path))
    status = evaluate_thesis_status(rec)
    assert status["status"] == "INVALIDATED"
    assert status["n_supports"] == 5      # 지지 증거는 그대로 세지만 판정은 뒤집지 못한다
    assert len(status["triggered_invalidations"]) == 1


def test_status_carries_uncalibrated_label():
    """집계 규칙을 확률처럼 읽지 않도록 인식론적 지위를 명시한다(v3.46 패턴)."""
    rec = {"thesis": {"thesis_id": "X-1", "ticker": "X", "invalidation_conditions": []},
           "evidence": []}
    out = evaluate_thesis_status(rec)
    assert "IMPLEMENTED_NOT_VALIDATED" in out["validation_status"]
    assert out["status"] in THESIS_STATUSES


def test_evidence_direction_is_recorded_not_inferred():
    """감성분석 같은 자동 추론 없이 분석자가 방향과 출처를 함께 기록한다."""
    with pytest.raises(ValueError, match="알 수 없는 방향"):
        build_evidence("2026-09-01", "실적 좋음", "positive", "출처")
    with pytest.raises(ValueError, match="source"):
        build_evidence("2026-09-01", "실적 좋음", "supports", "")


def test_latest_thesis_picks_most_recent(tmp_path):
    save_thesis(make_thesis(thesis_date="2026-08-15"), thesis_dir=str(tmp_path))
    save_thesis(make_thesis(thesis_date="2026-09-20"), thesis_dir=str(tmp_path))
    _, rec = latest_thesis("CDNS", thesis_dir=str(tmp_path))
    assert rec["thesis"]["thesis_date"] == "2026-09-20"


def test_all_actions_are_recordable():
    """§1이 요구한 6개 액션이 전부 기록 가능해야 한다."""
    for action in DECISION_ACTIONS:
        d = build_decision("X-1", "2026-08-15", action, full_gates(), "근거")
        assert d["action"] == action
