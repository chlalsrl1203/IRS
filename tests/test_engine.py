import pytest

from engine.expectation_gap_engine import (
    DRSInputs,
    check_stalwart_two_stage_bias,
    confidence_score,
    erp_from_drs,
    implied_growth_single_stage,
    implied_growth_two_stage,
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
        robustness_check_passed=True,
        section_5_7_aligned=True,
        data_completeness_pct=1.0,
        lynch_type_cap_applied=False,
        stalwart_two_stage_bias_flagged=False,
    )
    assert result["base"] == 50
    assert result["final"] == 95


def test_confidence_score_all_negative_factors():
    result = confidence_score(
        robustness_check_passed=False,
        section_5_7_aligned=False,
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
            robustness_check_passed=True,
            section_5_7_aligned=True,
            data_completeness_pct=-0.1,
        )
    with pytest.raises(ValueError):
        confidence_score(
            robustness_check_passed=True,
            section_5_7_aligned=True,
            data_completeness_pct=1.1,
        )


def test_confidence_score_stays_within_bounds_on_extreme_negative_input():
    result = confidence_score(
        robustness_check_passed=False,
        section_5_7_aligned=False,
        data_completeness_pct=0.0,
        lynch_type_cap_applied=True,
        stalwart_two_stage_bias_flagged=True,
        base=0,
    )
    assert 0 <= result["final"] <= 100
