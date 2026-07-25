import json

import pytest

from engine.pipeline import (
    AnalysisInputs,
    compare_implied_growth_models,
    run_analysis,
    save_ledger,
)


# ----------------------------------------------------------------------
# CDNS 2025 실데이터 (Alpha Vantage, 2026-07-25 조회)
# 골든 회귀 테스트용 - 합성 숫자가 아니라 실제로 트래커에 기록된 계산을 고정한다.
# ----------------------------------------------------------------------

CDNS_REVENUE = {
    2014: 1580932000, 2015: 1702091000, 2016: 1816083000, 2017: 1943032000,
    2018: 2138022000, 2019: 2336319000, 2020: 2682891000, 2021: 2988244000,
    2022: 3561718000, 2023: 4089986000, 2024: 4641264000, 2025: 5296759000,
}
CDNS_OPINC = {
    2014: 206644000, 2015: 285430000, 2016: 244901000, 2017: 323955000,
    2018: 396209000, 2019: 491796000, 2020: 645552000, 2021: 779089000,
    2022: 1073686000, 2023: 1251225000, 2024: 1350763000, 2025: 1649781000,
}
CDNS_OCF = {
    2014: 316722000, 2015: 378200000, 2016: 444879000, 2017: 470740000,
    2018: 604751000, 2019: 729600000, 2020: 904922000, 2021: 1100958000,
    2022: 1241894000, 2023: 1349176000, 2024: 1260551000, 2025: 1728781000,
}
CDNS_CAPEX = {
    2014: 39810000, 2015: 44808000, 2016: 53712000, 2017: 57901000,
    2018: 61503000, 2019: 74605000, 2020: 94813000, 2021: 66881000,
    2022: 124215000, 2023: 102503000, 2024: 142542000, 2025: 141871000,
}


def cdns_inputs(**overrides):
    base = dict(
        ticker="CDNS",
        company_name="Cadence Design Systems, Inc.",
        revenue_by_year=CDNS_REVENUE,
        operating_income_by_year=CDNS_OPINC,
        operating_cashflow_by_year=CDNS_OCF,
        capex_by_year=CDNS_CAPEX,
        market_cap=92952756000,
        net_debt=2480150000 - (3001317000 + 154213000),
        ebitda=1649781000 + 233844000,
        risk_free_rate=0.0447,
        competitor_threat_weights=[0.75, 0.35, 0.15],
        market_share_trend_pp_per_year=-1.0,
        active_antitrust_or_regulatory_case=False,
        demand_sensitivity_pct=0.15,
        subjective_input_basis=(
            "Synopsys 0.75(2025-07 Ansys $35B 인수완료로 EDA 35~40% 점유), "
            "Siemens EDA 0.35, Keysight 0.15. 점유율 추세 -1.0pp/년은 시장조사 "
            "기사 기반 [추정치]."
        ),
        model_used="single_stage",
        model_choice_reason=(
            "성숙 stalwart이고 two_stage와의 괴리가 커 Gordon Growth 채택. "
            "2026-07-25 최초 분석 시 사용한 모델."
        ),
        data_sources=["Alpha Vantage (2026-07-25)", "WebSearch: EDA market share"],
    )
    base.update(overrides)
    return AnalysisInputs(**base)


# ----------------------------------------------------------------------
# 골든 회귀 테스트 - 실데이터 계산 결과 고정
# ----------------------------------------------------------------------

def test_cdns_golden_regression():
    """
    CDNS 실데이터로 돌린 결과가 2026-07-25 트래커 기록과 일치하는지 고정한다.
    엔진 리팩터링이 실제 판정을 바꾸면 여기서 잡힌다.
    """
    result = run_analysis(cdns_inputs())

    assert result["drs"]["score"] == pytest.approx(36.6, abs=0.05)
    assert result["lynch"]["used"] == "stalwart"
    assert result["growth"]["realistic_growth"] == pytest.approx(0.12, abs=1e-4)
    assert result["implied_growth"]["value"] == pytest.approx(0.0871, abs=5e-4)
    assert result["expectation_gap"] == pytest.approx(0.0329, abs=5e-4)
    assert result["judgment"] == "적정가/경계선"
    assert result["confidence"]["final"] == 69


def test_cdns_rar_uses_percent_convention():
    """
    v3.19 회귀 방지: 파이프라인이 RAR을 퍼센트 규약으로 산출하는지 확인한다.
    소수 규약이면 -0.006 근처가 나오는데, 그건 100배 틀린 값이다.
    """
    result = run_analysis(cdns_inputs())
    assert result["rar"] == pytest.approx(-0.5994, abs=1e-3)
    assert abs(result["rar"]) > 0.1  # 소수 규약이었다면 절대 통과 못 함


def test_cdns_stalwart_bias_flagged():
    result = run_analysis(cdns_inputs())
    assert result["stalwart_bias"]["flagged"] is True
    assert "구조적 편향" in result["stalwart_bias"]["note"]


# ----------------------------------------------------------------------
# 모델 비교 / 선택 강제
# ----------------------------------------------------------------------

def test_compare_models_returns_both_and_flags_divergence():
    models = compare_implied_growth_models(
        market_cap=92952756000, fcf0=1586910000, r=0.10568, n=12, g_terminal=0.0347
    )
    assert models["single_stage"] is not None
    assert models["two_stage"] is not None
    # CDNS는 두 모델이 11%p 가까이 벌어지는 대표 사례
    assert models["divergence"] > 0.03
    assert "모델 괴리 경고" in models["divergence_warning"]


def test_compare_models_no_warning_when_models_agree():
    # ZTS는 두 모델이 거의 같은 값을 내는 사례
    models = compare_implied_growth_models(
        market_cap=31945181000, fcf0=2283000000, r=0.10922, n=12, g_terminal=0.0347
    )
    assert models["divergence"] < 0.03
    assert models["divergence_warning"] is None


def test_model_choice_changes_judgment_for_ph_like_case():
    """
    PH 사례 재현: 같은 데이터라도 모델 선택에 따라 Gap이 크게 달라진다.
    이 테스트는 '모델 선택이 판정을 바꾼다'는 사실 자체를 고정한다.
    """
    models = compare_implied_growth_models(
        market_cap=124255617000, fcf0=3341000000, r=0.10892, n=12, g_terminal=0.0347
    )
    realistic_growth = 0.06508
    gap_single = realistic_growth - models["single_stage"]
    gap_two = realistic_growth - models["two_stage"]
    assert gap_single > -0.05   # single_stage면 적정가로 보임
    assert gap_two <= -0.05     # two_stage면 과대평가로 뒤집힘


# ----------------------------------------------------------------------
# 입력 검증 (v3.19: 사유 없는 주관적 입력/모델선택 거부)
# ----------------------------------------------------------------------

def test_inputs_reject_missing_model_choice_reason():
    with pytest.raises(ValueError) as exc:
        cdns_inputs(model_choice_reason="")
    assert "model_choice_reason" in str(exc.value)


def test_inputs_reject_missing_subjective_basis():
    with pytest.raises(ValueError) as exc:
        cdns_inputs(subjective_input_basis="   ")
    assert "subjective_input_basis" in str(exc.value)


def test_inputs_reject_invalid_model_name():
    with pytest.raises(ValueError):
        cdns_inputs(model_used="three_stage")


def test_inputs_reject_lynch_override_without_reason():
    with pytest.raises(ValueError):
        cdns_inputs(lynch_type_override="cyclical")


# ----------------------------------------------------------------------
# Ledger 영속화
# ----------------------------------------------------------------------

def test_save_ledger_roundtrip_preserves_inputs(tmp_path):
    result = run_analysis(cdns_inputs())
    path = save_ledger(result, ledger_dir=str(tmp_path))

    with open(path, encoding="utf-8") as f:
        reloaded = json.load(f)

    # 재현에 필요한 입력이 전부 남아있어야 한다(큐22 유실 사고 재발 방지)
    assert reloaded["meta"]["ticker"] == "CDNS"
    assert reloaded["inputs"]["market_cap"] == 92952756000
    assert reloaded["inputs"]["model_used"] == "single_stage"
    assert reloaded["inputs"]["subjective_input_basis"]
    assert reloaded["rar"] == pytest.approx(result["rar"])
    assert reloaded["drs"]["score"] == pytest.approx(result["drs"]["score"])


# ----------------------------------------------------------------------
# v3.19 자체감사에서 발견한 조용한 실패 2건 회귀 방지
# ----------------------------------------------------------------------

def test_cagr_rejects_negative_start_instead_of_returning_complex():
    """
    가드가 없으면 파이썬이 복소수를 조용히 반환해 계산 전체를 오염시킨다.
    FCF 적자 기준연도(INTC/BYND 유형)에서 실제로 발생 가능.
    """
    from engine.pipeline import _cagr

    with pytest.raises(ValueError) as exc:
        _cagr(-50, 100, 5, "FCF 5y")
    assert "0 이하" in str(exc.value)

    with pytest.raises(ValueError):
        _cagr(100, -50, 5)


def test_short_history_records_data_limitation_instead_of_silent_fallback():
    """
    10년치가 없으면 5y를 10y 자리에 대체하는데, 그 사실이 결과에 기록되어야 한다.
    기록이 없으면 DRS가 실제보다 관대하게 나온 걸 아무도 모른다.
    """
    years = list(range(2020, 2027))  # 7개 연도 (10y 산출 불가)
    rev = {y: 100 * (1.1 ** (y - 2020)) for y in years}
    result = run_analysis(
        cdns_inputs(
            revenue_by_year=rev,
            operating_income_by_year={y: v * 0.3 for y, v in rev.items()},
            operating_cashflow_by_year={y: v * 0.35 for y, v in rev.items()},
            capex_by_year={y: v * 0.05 for y, v in rev.items()},
            market_cap=1e9,
            net_debt=-1e8,
            ebitda=5e7,
            margin_years=years[-5:],
        )
    )
    assert result["derived"]["revenue_cagr_10y"] is None
    assert any("10년 CAGR 산출 불가" in x for x in result["data_limitations"])


def test_model_divergence_warning_surfaces_in_data_limitations():
    """모델 괴리 경고가 메모 작성자 눈에 띄도록 한계 목록에 올라와야 한다."""
    result = run_analysis(cdns_inputs())
    assert any("모델 괴리 경고" in x for x in result["data_limitations"])


def test_full_history_has_no_spurious_limitations():
    """12년치 정상 데이터에서는 데이터 한계 항목에 10년 CAGR 경고가 없어야 한다."""
    result = run_analysis(cdns_inputs())
    assert not any("10년 CAGR 산출 불가" in x for x in result["data_limitations"])
