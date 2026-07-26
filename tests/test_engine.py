import pytest

from engine.expectation_gap_engine import (
    DRSInputs,
    check_stalwart_two_stage_bias,
    confidence_score,
    erp_from_drs,
    expectation_gap_sensitivity_check,
    expected_return,
    implied_growth_single_stage,
    implied_growth_two_stage,
    rar,
    rar_from_decimal_return,
    realistic_growth_estimate,
)


def test_implied_growth_single_stage_basic():
    g = implied_growth_single_stage(market_cap=100_000, fcf0=5_000, r=0.09)
    market_cap_check = 5_000 * (1 + g) / (0.09 - g)
    assert market_cap_check == pytest.approx(100_000, rel=1e-6)


def test_implied_growth_single_stage_rejects_zero_fcf():
    with pytest.raises(ValueError):
        implied_growth_single_stage(market_cap=100_000, fcf0=0, r=0.09)


def test_implied_growth_two_stage_converges():
    g, log, err = implied_growth_two_stage(
        market_cap=500_000, fcf0=8_000, r=0.075, n=12, g_terminal=0.035
    )
    assert -0.20 <= g <= 0.60
    assert err < 1e-3
    assert len(log) > 0


def test_implied_growth_two_stage_rejects_nonpositive_fcf0():
    with pytest.raises(ValueError):
        implied_growth_two_stage(
            market_cap=500_000, fcf0=-1_000, r=0.075, n=12, g_terminal=0.035
        )


def test_erp_from_drs_endpoints():
    assert erp_from_drs(0) == pytest.approx(0.05)
    assert erp_from_drs(100) == pytest.approx(0.08)


def test_erp_from_drs_rejects_out_of_range():
    with pytest.raises(ValueError):
        erp_from_drs(150)


def test_drs_inputs_score_all_present():
    drs = DRSInputs(
        revenue_volatility=10,
        margin_volatility=10,
        leverage=10,
        cyclicality=10,
        competition_intensity=10,
    )
    assert drs.score() == pytest.approx(50.0)


def test_drs_inputs_score_requires_reason_for_excluded():
    drs = DRSInputs(
        revenue_volatility=10,
        margin_volatility=10,
        leverage=10,
        cyclicality=None,
        competition_intensity=10,
    )
    with pytest.raises(ValueError):
        drs.score()

    drs.excluded_reasons["cyclicality"] = "해당 업종에 적용 불가"
    assert drs.score() > 0


def test_realistic_growth_estimate_basic():
    growth, breakdown = realistic_growth_estimate(
        revenue_cagr_3y=0.10,
        revenue_cagr_5y=0.12,
        revenue_cagr_10y=0.15,
        lynch_type="stalwart",
    )
    assert breakdown["final_realistic_growth"] == growth
    g_min, g_max = 0.00, 0.12
    assert g_min <= growth <= g_max


def test_realistic_growth_estimate_requires_at_least_one_cagr():
    with pytest.raises(ValueError):
        realistic_growth_estimate()


def test_check_stalwart_two_stage_bias_flags_negative_rar():
    flag_required, note = check_stalwart_two_stage_bias(
        lynch_type="stalwart", rar_value=-0.02, model_used="two_stage"
    )
    assert flag_required is True
    assert note is not None
    assert "구조적 편향" in note


def test_check_stalwart_two_stage_bias_skips_non_stalwart_or_positive_rar():
    flag_required, note = check_stalwart_two_stage_bias(
        lynch_type="fast_grower", rar_value=-0.02, model_used="two_stage"
    )
    assert flag_required is False
    assert note is None

    flag_required, note = check_stalwart_two_stage_bias(
        lynch_type="stalwart", rar_value=0.03, model_used="two_stage"
    )
    assert flag_required is False
    assert note is None


def test_confidence_score_all_positive_factors():
    result = confidence_score(
        sensitivity_check_result={"judgment_flipped": False},
        gap=0.02,
        rar=0.05,
        data_completeness_pct=1.0,
        lynch_type_cap_applied=False,
        stalwart_two_stage_bias_flagged=False,
    )
    assert result["base"] == 50
    assert result["final"] == 95


def test_confidence_score_all_negative_factors():
    result = confidence_score(
        sensitivity_check_result={"judgment_flipped": True},
        gap=0.02,
        rar=-0.05,
        data_completeness_pct=0.0,
        lynch_type_cap_applied=True,
        stalwart_two_stage_bias_flagged=True,
    )
    assert result["final"] == 40
    assert result["adjustments"]["robustness_check_passed"] == 0
    assert result["adjustments"]["section_5_7_aligned"] == 0
    assert result["adjustments"]["data_completeness"] == 0


def test_confidence_score_rejects_out_of_range_data_completeness():
    with pytest.raises(ValueError):
        confidence_score(
            sensitivity_check_result={"judgment_flipped": False},
            gap=0.02,
            rar=0.05,
            data_completeness_pct=-0.1,
        )
    with pytest.raises(ValueError):
        confidence_score(
            sensitivity_check_result={"judgment_flipped": False},
            gap=0.02,
            rar=0.05,
            data_completeness_pct=1.1,
        )


def test_confidence_score_stays_within_bounds_on_extreme_negative_input():
    result = confidence_score(
        sensitivity_check_result={"judgment_flipped": True},
        gap=0.02,
        rar=-0.05,
        data_completeness_pct=0.0,
        lynch_type_cap_applied=True,
        stalwart_two_stage_bias_flagged=True,
        base=0,
    )
    assert 0 <= result["final"] <= 100


def test_confidence_score_rejects_non_sensitivity_check_dict():
    with pytest.raises(TypeError):
        confidence_score(
            sensitivity_check_result={"some_other_key": True},
            gap=0.02,
            rar=0.05,
            data_completeness_pct=0.5,
        )


def test_confidence_score_robustness_and_alignment_both_pass():
    result = confidence_score(
        sensitivity_check_result={"judgment_flipped": False},
        gap=0.03,
        rar=0.04,
        data_completeness_pct=0.5,
    )
    assert result["adjustments"]["robustness_check_passed"] == 15
    assert result["adjustments"]["section_5_7_aligned"] == 15
    assert result["section_5_7_aligned"] is True


def test_confidence_score_judgment_flipped_true_zeroes_robustness():
    result = confidence_score(
        sensitivity_check_result={"judgment_flipped": True},
        gap=0.03,
        rar=0.04,
        data_completeness_pct=0.5,
    )
    assert result["adjustments"]["robustness_check_passed"] == 0


def test_confidence_score_judgment_flipped_none_is_conservative():
    result = confidence_score(
        sensitivity_check_result={"judgment_flipped": None, "error": "Model Not Applicable"},
        gap=0.03,
        rar=0.04,
        data_completeness_pct=0.5,
    )
    assert result["adjustments"]["robustness_check_passed"] == 0


def test_confidence_score_sign_mismatch_zeroes_alignment():
    result = confidence_score(
        sensitivity_check_result={"judgment_flipped": False},
        gap=0.03,
        rar=-0.01,
        data_completeness_pct=0.5,
    )
    assert result["adjustments"]["section_5_7_aligned"] == 0
    assert result["section_5_7_aligned"] is False


def test_rar_accepts_percent_number():
    # 기대수익률 -22.39%, DRS 40.4 -> 퍼센트 컨벤션 기준 약 -0.554
    assert rar(-22.387, 40.4) == pytest.approx(-0.5541, abs=1e-4)


def test_rar_rejects_decimal_passed_as_percent():
    # v3.19 가드: 소수(-0.2239)를 퍼센트 자리에 넣으면 100배 오차가 나므로 거부
    with pytest.raises(ValueError) as exc_info:
        rar(-0.22387, 40.4)
    assert "rar_from_decimal_return" in str(exc_info.value)


def test_rar_allows_genuinely_small_return_when_explicit():
    # 진짜로 ±1% 미만인 기대수익률은 명시적 플래그로 통과
    assert rar(0.5, 40.0, allow_sub_one_pct=True) == pytest.approx(0.0125)


def test_rar_from_decimal_return_matches_percent_path():
    er_decimal = -0.22387
    assert rar_from_decimal_return(er_decimal, 40.4) == pytest.approx(rar(-22.387, 40.4), abs=1e-9)


def test_sensitivity_check_default_model_used_is_two_stage_backward_compat():
    result_default = expectation_gap_sensitivity_check(
        market_cap=500_000, fcf0=8_000, r_with_drs=0.075, base_erp=0.05, rf=0.045,
        realistic_growth=0.12, n=12, g_terminal=0.035,
    )
    result_explicit = expectation_gap_sensitivity_check(
        market_cap=500_000, fcf0=8_000, r_with_drs=0.075, base_erp=0.05, rf=0.045,
        realistic_growth=0.12, n=12, g_terminal=0.035, model_used="two_stage",
    )
    assert result_default["implied_growth_with_drs"] == pytest.approx(
        result_explicit["implied_growth_with_drs"]
    )


def test_sensitivity_check_model_used_single_stage_matches_single_stage_function():
    # v3.19 근본수정(2026-07-26): model_used="single_stage"이면 내부적으로
    # implied_growth_single_stage()를 써야 한다(과거엔 항상 two_stage였음).
    result = expectation_gap_sensitivity_check(
        market_cap=500_000, fcf0=8_000, r_with_drs=0.075, base_erp=0.05, rf=0.045,
        realistic_growth=0.12, n=12, g_terminal=0.035, model_used="single_stage",
    )
    expected_g_with = implied_growth_single_stage(500_000, 8_000, 0.075)
    expected_g_without = implied_growth_single_stage(500_000, 8_000, 0.045 + 0.05)
    assert result["implied_growth_with_drs"] == pytest.approx(expected_g_with)
    assert result["implied_growth_without_drs"] == pytest.approx(expected_g_without)


def test_sensitivity_check_rejects_invalid_model_used():
    with pytest.raises(ValueError):
        expectation_gap_sensitivity_check(
            market_cap=500_000, fcf0=8_000, r_with_drs=0.075, base_erp=0.05, rf=0.045,
            realistic_growth=0.12, n=12, g_terminal=0.035, model_used="triple_stage",
        )


def test_expected_return_to_rar_chain_is_unit_safe():
    # expected_return()은 소수를 반환하므로 rar()에 직접 넣으면 가드에 걸려야 하고,
    # rar_from_decimal_return()으로는 정상 동작해야 한다.
    er = expected_return(0.33, -0.15, 0.50, -0.24, 0.17, -0.32)
    assert abs(er) < 1.0  # 소수임을 확인
    with pytest.raises(ValueError):
        rar(er, 40.0)
    assert rar_from_decimal_return(er, 40.0) == pytest.approx(er * 100 / 40.0)
