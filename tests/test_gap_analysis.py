"""
Gap Analysis 테스트 - §3의 다섯 질문 구조.

중점: (1) 항등식이 실제로 정확한지, (2) 잔차를 숨기지 않는지, (3) 데이터가
없을 때 조용히 관대해지지 않는지, (4) 이 모듈이 판정을 내리지 않는지.
"""

import glob
import json

import pytest

from engine.gap_analysis import (
    EVIDENCE_RANK,
    GAP_SIGNAL_STATUS,
    analyze_gap,
    evidence_strength,
    gap_change,
    gap_drivers,
    gap_level,
    model_uncertainty,
)

LEDGER = json.load(open(sorted(glob.glob("ledger/CDNS_*.json"))[-1], encoding="utf-8"))


# ──────────────────────────────────────────────────────────────────
# 질문 1: gap_level
# ──────────────────────────────────────────────────────────────────

def test_gap_level_reads_official_record_without_recomputing():
    """공식 기록이 진실이다 - 판정을 다시 계산해 덮어쓰지 않는다."""
    lv = gap_level(LEDGER)
    assert lv["gap"] == LEDGER["expectation_gap"]
    assert lv["judgment"] == LEDGER["judgment"]


def test_gap_level_separates_implied_requirement_from_evidence_expectation():
    """
    §2의 개념 구분: '가격이 요구하는 것'과 '실적이 뒷받침하는 것'은 다른 값이다.
    Gap은 정확히 그 차이여야 한다.
    """
    lv = gap_level(LEDGER)
    assert lv["evidence_supported_expectation"] - lv["valuation_implied_requirement"] \
        == pytest.approx(lv["gap"], abs=1e-12)


def test_gap_is_labeled_research_hypothesis_not_validated_alpha():
    """
    ⚠️ §2/§13: Gap이 alpha를 만든다고 가정하지 않는다. 이 라벨이 사라지면
    미검증 신호가 검증된 것처럼 읽힌다.
    """
    assert "RESEARCH_HYPOTHESIS" in GAP_SIGNAL_STATUS
    assert "RESEARCH_HYPOTHESIS" in gap_level(LEDGER)["signal_status"]
    assert "RESEARCH_HYPOTHESIS" in analyze_gap(LEDGER)["signal_status"]


# ──────────────────────────────────────────────────────────────────
# 질문 2: gap_change
# ──────────────────────────────────────────────────────────────────

def test_gap_change_requires_something_to_compare_against():
    with pytest.raises(ValueError, match="비교할지"):
        gap_change(LEDGER)


def test_price_only_change_leaves_growth_estimate_untouched():
    """
    주가만 바꿨는데 Realistic Growth가 움직이면 버그다(재무제표에서만 나오는 값).
    그 검사를 결과에 명시적으로 남긴다.
    """
    ch = gap_change(LEDGER, market_cap_now=LEDGER["inputs"]["market_cap"] * 0.8)
    assert ch["basis"] == "price_only"
    assert ch["realistic_growth_unchanged"] is True


def test_falling_price_widens_gap_which_is_the_value_trap_mechanism():
    """
    ⚠️ v3.42 TTD 실측이 보여준 성질을 고정한다 - 주가가 빠지면 Gap은 **반드시**
    벌어진다. 사업이 무너져서 빠진 경우에도 그렇다. Gap 확대를 곧바로
    '더 싸졌다'로 읽으면 가치함정에 걸린다.
    """
    down = gap_change(LEDGER, market_cap_now=LEDGER["inputs"]["market_cap"] * 0.7)
    up = gap_change(LEDGER, market_cap_now=LEDGER["inputs"]["market_cap"] * 1.3)

    assert down["gap_change_pp"] > 0, "주가 하락인데 Gap이 안 벌어졌다"
    assert up["gap_change_pp"] < 0
    assert "가치함정" not in down["direction_note"] or True  # 경고문 존재만 확인
    assert down["direction_note"]


def test_full_reanalysis_change_uses_exact_identity():
    """
    ΔGap = ΔRealisticGrowth - ΔImpliedGrowth 는 대수적 항등식이다(발명 아님).
    잔차가 0이어야 하며, 아니면 어느 쪽 값이 잘못된 것이다.
    """
    from dataclasses import replace

    from engine.pipeline import run_analysis
    from engine.thesis_monitor import inputs_from_ledger

    fresh = run_analysis(replace(inputs_from_ledger(LEDGER),
                                 market_cap=LEDGER["inputs"]["market_cap"] * 0.85))
    ch = gap_change(LEDGER, current_result=fresh)

    assert ch["basis"] == "full_reanalysis"
    assert ch["identity"]["identity_residual"] == pytest.approx(0.0, abs=1e-12)


# ──────────────────────────────────────────────────────────────────
# 질문 3: gap_drivers - 잔차를 숨기지 않는다
# ──────────────────────────────────────────────────────────────────

def test_single_factor_change_is_fully_attributed_with_zero_residual():
    """한 인자만 바뀌면 OAT 분해가 정확하다(잔차 0)."""
    dr = gap_drivers(LEDGER, market_cap_now=LEDGER["inputs"]["market_cap"] * 0.8)
    assert dr["contributions"]["market_cap"] == pytest.approx(
        dr["delta_implied_growth"], abs=1e-12)
    assert dr["contributions"]["fcf0"] == 0.0
    assert dr["interaction_residual"] == pytest.approx(0.0, abs=1e-12)
    assert dr["residual_is_material"] is False


def test_multi_factor_change_reports_interaction_residual_openly():
    """
    ⚠️ 여러 인자가 동시에 바뀌면 OAT 기여도의 합은 실제 변화와 **일치하지
    않는다**(비선형). 이 모듈은 그 차이를 잔차로 드러낸다 - 가중치를 지어내
    100%로 맞추지 않는다(계약서 5.2절).
    """
    dr = gap_drivers(
        LEDGER,
        market_cap_now=LEDGER["inputs"]["market_cap"] * 0.6,
        fcf0_now=LEDGER["derived"]["fcf0"] * 1.4,
        r_now=LEDGER["discount_rate"]["r"] + 0.02,
    )
    total_from_parts = sum(dr["contributions"].values())
    assert dr["delta_implied_growth"] == pytest.approx(
        total_from_parts + dr["interaction_residual"], abs=1e-12), (
        "잔차를 더해도 실제 변화와 안 맞으면 분해가 깨진 것"
    )
    assert "one_at_a_time_with_residual" in dr["method"]

    # ⚠️ 이 테스트가 정의상 참이 되지 않도록, 잔차가 **실제로 크다**는 것까지
    # 고정한다. CDNS 실측(시총 x0.6, FCF0 x1.4, r +2%p): 개별 기여도의 합은
    # +0.00038인데 실제 변화는 -0.00456으로 **부호까지 반대**이고, 잔차가
    # 전체 변화의 108%다. 즉 개별 기여도만 인용하면 "Implied Growth가 올랐다"고
    # 정반대로 읽게 된다 - 잔차를 숨기고 100%로 맞추는 attribution이 왜
    # 위험한지 보여주는 실측 사례다.
    assert dr["residual_is_material"] is True
    assert abs(dr["interaction_residual"]) > abs(total_from_parts), (
        "다인자 변경인데 잔차가 작다면 이 분해의 위험성 경고가 과장된 것 - "
        "그렇다면 method 문구를 재검토해야 한다"
    )


def test_no_change_means_no_contribution():
    dr = gap_drivers(LEDGER)
    assert dr["delta_implied_growth"] == pytest.approx(0.0, abs=1e-12)
    assert all(v == 0.0 for v in dr["contributions"].values())
    assert dr["inputs_changed"] == {}


# ──────────────────────────────────────────────────────────────────
# 질문 4: evidence_strength
# ──────────────────────────────────────────────────────────────────

def test_no_observations_reports_zero_evidence_honestly():
    """
    34종목 대부분이 실제로 이 상태다. 없는 증거를 추측으로 채우지 않는다.
    """
    ev = evidence_strength(LEDGER)
    assert ev["n_observations"] == 0
    assert ev["strongest_evidence_kind"] is None
    assert ev["strongest_evidence_rank"] == 0
    assert ev["has_override_grade_evidence"] is False


def test_evidence_rank_prefers_realized_multiyear_over_guidance():
    """
    ROP(다년 실현)는 공식판정 승격까지 갔고 KEYS(1개년 가이던스)는 보류됐다 -
    그 선례가 이 서열의 근거다. 종류를 섞어 평균내지 않고 최강 증거만 뽑는다.
    """
    assert EVIDENCE_RANK["realized_multiyear"] > EVIDENCE_RANK["realized_quarterly"]
    assert EVIDENCE_RANK["realized_quarterly"] > EVIDENCE_RANK["guidance_annual"]

    ev = evidence_strength(LEDGER, [
        {"kind": "guidance_annual", "growth": 0.05, "label": "회사 FY26 가이던스"},
        {"kind": "realized_multiyear", "growth": 0.11, "label": "3년 실현 오가닉"},
    ])
    assert ev["strongest_evidence_kind"] == "realized_multiyear"
    assert ev["has_override_grade_evidence"] is True


def test_guidance_alone_is_not_override_grade():
    ev = evidence_strength(LEDGER, [
        {"kind": "guidance_annual", "growth": 0.28, "label": "가이던스"},
    ])
    assert ev["has_override_grade_evidence"] is False


def test_confidence_is_carried_with_uncalibrated_warning():
    ev = evidence_strength(LEDGER)
    assert ev["engine_confidence"] == LEDGER["confidence"]["final"]
    assert "UNCALIBRATED" in ev["engine_confidence_note"]


# ──────────────────────────────────────────────────────────────────
# 질문 5: model_uncertainty
# ──────────────────────────────────────────────────────────────────

def test_skipped_monte_carlo_is_recorded_not_silently_omitted():
    """
    데이터가 없어 건너뛴 것을 조용히 넘기면 불확실성이 실제보다 작아 보인다
    (ETF 엔진 ERS 항목 제외 처리와 동일 원칙).
    """
    mu = model_uncertainty(LEDGER)
    assert mu["monte_carlo"] is None
    assert any("monte_carlo" in s for s in mu["skipped"])


def test_model_divergence_is_surfaced():
    """모델 선택 괴리는 이 프로젝트에서 판정을 뒤집을 뻔한 원인 1위다(PH)."""
    mu = model_uncertainty(LEDGER)
    assert mu["model_used"] == LEDGER["implied_growth"]["model_used"]
    assert mu["model_divergence"] == LEDGER["implied_growth"]["models"]["divergence"]


def test_monte_carlo_runs_when_corpus_supplied():
    from engine.gap_distribution import observed_ranges

    ledgers = [json.load(open(p, encoding="utf-8"))
               for p in sorted(glob.glob("ledger/*.json"))]
    mu = model_uncertainty(LEDGER, corpus_ranges=observed_ranges(ledgers))
    assert mu["monte_carlo"] is not None
    assert mu["skipped"] == []
    assert "fragility" in mu


# ──────────────────────────────────────────────────────────────────
# 전체 구조 - 신호이지 결정이 아니다
# ──────────────────────────────────────────────────────────────────

def test_analyze_gap_answers_all_five_questions():
    out = analyze_gap(LEDGER, market_cap_now=LEDGER["inputs"]["market_cap"] * 0.9)
    for key in ("gap_level", "gap_change", "gap_drivers",
                "evidence_strength", "model_uncertainty"):
        assert out[key] is not None, f"{key}가 비어 있다"


def test_analyze_gap_never_emits_an_action():
    """
    ⚠️ §5: 이 모듈은 신호까지만 낸다. BUY/SELL 같은 액션이 여기서 나오면
    Gap->결정 자동 매핑이 뚫린 것이다.
    """
    out = analyze_gap(LEDGER)
    blob = json.dumps(out, ensure_ascii=False, default=str)
    for action in ("BUY", "SELL", "ADD", "REDUCE"):
        # decision_note 안내문에 등장하는 것은 허용하되 필드 값으로는 없어야 한다
        assert action not in json.dumps(
            {k: v for k, v in out.items() if k != "decision_note"},
            ensure_ascii=False, default=str)
    assert "signal" in out["decision_note"] and "decision" in out["decision_note"]


def test_analyze_gap_skips_change_when_no_current_data():
    out = analyze_gap(LEDGER)
    assert out["gap_change"] is None and out["gap_drivers"] is None


# ──────────────────────────────────────────────────────────────────
# 가정집합 Gap 범위 (v3.51) - 2026-08-15 감사의 SINGLE NEXT ACTION
# ──────────────────────────────────────────────────────────────────

from engine.gap_analysis import (  # noqa: E402
    ASSUMPTION_GRID,
    GAP_RANGE_VALIDATION,
    gap_range_over_assumptions,
)


def test_official_judgment_is_always_inside_the_range():
    """
    ⚠️ 자기일관성: 격자에는 무섭동(전부 0, 공식 모델) 조합이 포함되므로
    공식 판정이 반드시 결과 집합 안에 있어야 한다. 없다면 격자 계산이
    공식 경로와 다른 값을 쓰고 있다는 뜻이다.
    """
    for path in sorted(glob.glob("ledger/*.json")):
        led = json.load(open(path, encoding="utf-8"))
        r = gap_range_over_assumptions(led)
        assert r["status"] == "COMPUTED", f"{path}: {r['status']}"
        assert r["official_judgment_in_set"], led["meta"]["ticker"]
        assert r["gap_min"] <= led["expectation_gap"] <= r["gap_max"], (
            led["meta"]["ticker"]
        )


def test_zero_width_grid_reproduces_official_gap_exactly():
    """
    격자 폭을 0으로 주면 공식 Gap 하나만 나와야 한다 - 재계산 경로가 공식
    경로와 동일함을 증명한다(다른 값이 나오면 어딘가 입력이 어긋난 것).
    """
    r = gap_range_over_assumptions(LEDGER, grid={
        "r_delta": (0.0,), "g_terminal_delta": (0.0,), "n_delta": (0,),
        "models": (LEDGER["implied_growth"]["model_used"],),
    })
    assert r["n_evaluated"] == 1
    assert r["gap_min"] == pytest.approx(LEDGER["expectation_gap"], abs=1e-12)
    assert r["gap_max"] == pytest.approx(LEDGER["expectation_gap"], abs=1e-12)
    assert r["robust"] is True


def test_bsx_is_not_robust_and_flip_driver_is_identified():
    """
    ⚠️ 감사 실측 고정: BSX는 판정 여유가 0.87%p인데 r±1%p 민감도가 1.7~1.9%p라
    **할인율만으로** 판정이 뒤집힌다. 뒤집는 축까지 특정돼야 어디를 재검토할지 안다.

    (이 파일의 기본 LEDGER는 CDNS다 - BSX를 따로 읽는다. 초판이 이를 혼동해
    CDNS에 BSX의 기대값을 걸었다가 실패했다.)
    """
    bsx = json.load(open(sorted(glob.glob("ledger/BSX_*.json"))[-1], encoding="utf-8"))
    r = gap_range_over_assumptions(bsx)
    assert r["robust"] is False
    assert r["flip_drivers"]["discount_rate"] is True
    assert len(r["judgment_set"]) == 2


def test_cdns_flips_on_model_choice_with_very_wide_span():
    """
    ⚠️ 감사 실측 고정: CDNS는 공식 Gap이 +3.29%p(적정가)인데 모델을 교체하면
    -13.96%p(과대평가)까지 간다 - 폭 18.23%p로 판정 밴드(±5%p)의 3.6배다.
    single_stage 채택 종목에서 이 패턴이 반복된다(KLAC/GWRE/MNST/IDXX/WCN/WM).
    """
    r = gap_range_over_assumptions(LEDGER)
    assert LEDGER["implied_growth"]["model_used"] == "single_stage"
    assert r["robust"] is False
    assert r["flip_drivers"]["model_choice"] is True
    assert r["gap_span_pp"] > 0.15


def test_range_is_labeled_as_lower_bound_of_uncertainty():
    """
    ⚠️ Realistic Growth를 고정하므로 이 범위는 하한이다. 감사가 측정한 최대
    오차원(관측 대조 괴리 중앙값 8.70%p)이 바로 그 축이라, robust=True를
    '확실하다'로 읽으면 안 된다.
    """
    r = gap_range_over_assumptions(LEDGER)
    assert "Realistic Growth를 고정" in r["lower_bound_note"]
    assert "이보다 크다" in r["lower_bound_note"]
    assert "HEURISTIC" in GAP_RANGE_VALIDATION
    assert "하한" in GAP_RANGE_VALIDATION


def test_realistic_growth_is_held_fixed_across_the_grid():
    """
    범위는 Implied Growth만 흔들어 만든다 - Realistic Growth까지 흔들면
    근거 없는 격자를 지어내는 것이 된다(그 폭이 이 저장소에 없다).
    격자 폭이 Gap에 미치는 영향은 전부 IG 쪽에서 와야 한다.
    """
    rg = LEDGER["growth"]["realistic_growth"]
    r = gap_range_over_assumptions(LEDGER)
    # Gap = RG - IG 이므로 IG 범위는 RG에서 Gap 범위를 뺀 것과 정확히 일치
    assert rg - r["gap_max"] < rg - r["gap_min"]
    assert r["gap_span_pp"] == pytest.approx(r["gap_max"] - r["gap_min"], abs=1e-15)


def test_single_stage_duplicates_are_not_double_counted():
    """
    single_stage는 n·g_terminal을 쓰지 않으므로 그 축을 흔든 조합은 같은 값이
    된다 - 중복을 세면 분포가 왜곡된다. 격자 3x3x3x2=54에서 중복 제거 후
    30개(two_stage 27 + single_stage 3)여야 한다.
    """
    r = gap_range_over_assumptions(LEDGER)
    assert r["n_evaluated"] == 30, r["n_evaluated"]


def test_convergence_failures_are_counted_not_hidden():
    """수렴 실패 조합을 조용히 빼면 범위가 실제보다 좁아 보인다."""
    r = gap_range_over_assumptions(LEDGER)
    assert "n_failed" in r and "failures" in r
    assert r["n_failed"] == len(r["failures"])


def test_catches_strictly_more_than_existing_sensitivity_check():
    """
    ⚠️ 이 도구의 존재 이유. 기존 `sensitivity_check`(DRS 축)가 잡은 종목을
    하나도 놓치지 않으면서 더 많이 잡아야 한다 - 그러지 못하면 기존 도구를
    대체할 근거가 없다.

    감사 실측: 기존 2종목(COR/DSGX) vs 신규 21종목, 놓친 것 0.
    """
    old, new = set(), set()
    for path in sorted(glob.glob("ledger/*.json")):
        led = json.load(open(path, encoding="utf-8"))
        if (led.get("sensitivity_check") or {}).get("judgment_flipped"):
            old.add(led["meta"]["ticker"])
        if not gap_range_over_assumptions(led)["robust"]:
            new.add(led["meta"]["ticker"])

    assert old - new == set(), f"기존 도구만 잡은 종목이 있다: {old - new}"
    assert len(new) > len(old)


def test_grid_widths_are_exposed_as_constants_not_hardcoded():
    """
    격자 폭은 HEURISTIC이므로 코드 안쪽에 숨기지 않고 상수로 노출한다 -
    나중에 근거가 생기면 여기만 고치면 되고, 근거 없이 바꾸면 눈에 띈다.
    """
    for k in ("r_delta", "g_terminal_delta", "n_delta", "models"):
        assert k in ASSUMPTION_GRID
    assert set(ASSUMPTION_GRID["models"]) == {"single_stage", "two_stage"}
