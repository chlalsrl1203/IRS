import json

import pytest

from engine.expectation_gap_engine import judgment_grade_from_gap
from engine.pipeline import (
    PIT_INVALID,
    PIT_UNKNOWN,
    PIT_VALID,
    AnalysisInputs,
    compare_implied_growth_models,
    evaluate_point_in_time,
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


def test_cdns_no_lynch_override_means_not_overridden_down():
    result = run_analysis(cdns_inputs())
    assert result["lynch"]["overridden_down"] is False


# ----------------------------------------------------------------------
# MNST 2025 실데이터 (Alpha Vantage, 2026-07-25 조회) - structural_discount가
# 11.1%로 v3.8 이중반영 가드의 10% 임계값을 넘는 유일한 확보 실데이터 사례라
# check_deceleration_double_count 배선 테스트 전용으로 쓴다.
# ----------------------------------------------------------------------

MNST_REVENUE = {
    2014: 2464867000, 2015: 2722564000, 2016: 3049393000, 2017: 3369045000,
    2018: 3807183000, 2019: 4200819000, 2020: 4598638000, 2021: 5541352000,
    2022: 6311050000, 2023: 7140027000, 2024: 7492709000, 2025: 8294343000,
}
MNST_OPINC = {
    2014: 747505000, 2015: 893653000, 2016: 1085338000, 2017: 1198787000,
    2018: 1283619000, 2019: 1402939000, 2020: 1633153000, 2021: 1797467000,
    2022: 1584721000, 2023: 1953355000, 2024: 1930294000, 2025: 2419354000,
}
MNST_OCF = {
    2014: 585567000, 2015: 207986000, 2016: 701355000, 2017: 987731000,
    2018: 1161881000, 2019: 1113762000, 2020: 1364163000, 2021: 1155741000,
    2022: 887699000, 2023: 1717753000, 2024: 1928533000, 2025: 2098177000,
}
MNST_CAPEX = {
    2014: 31363000, 2015: 42493000, 2016: 105337000, 2017: 93128000,
    2018: 74925000, 2019: 110398000, 2020: 67272000, 2021: 57453000,
    2022: 212153000, 2023: 234724000, 2024: 264074000, 2025: 132275000,
}


def mnst_inputs(**overrides):
    base = dict(
        ticker="MNST",
        company_name="Monster Beverage Corporation",
        revenue_by_year=MNST_REVENUE,
        operating_income_by_year=MNST_OPINC,
        operating_cashflow_by_year=MNST_OCF,
        capex_by_year=MNST_CAPEX,
        market_cap=91433976000,
        net_debt=0 - (2088117000 + 677084000),
        ebitda=2419354000 + 114441000,
        risk_free_rate=0.0447,
        competitor_threat_weights=[0.6, 0.4, 0.2],
        market_share_trend_pp_per_year=-0.5,
        active_antitrust_or_regulatory_case=False,
        demand_sensitivity_pct=0.10,
        subjective_input_basis=(
            "Red Bull 0.6, Celsius 0.4, 기타 0.2. 점유율추세 -0.5pp/년은 "
            "Celsius 잠식 관련 기사 기반 [추정치]."
        ),
        model_used="single_stage",
        model_choice_reason="성숙 stalwart, 순현금 구조. 2026-07-25 최초 분석 시 사용한 모델.",
        data_sources=["Alpha Vantage (2026-07-25)"],
    )
    base.update(overrides)
    return AnalysisInputs(**base)


def test_deceleration_double_count_silent_without_override():
    """오버라이드가 없으면 이중반영 가능성 자체가 없으므로 경고가 없어야 한다."""
    result = run_analysis(mnst_inputs())
    assert result["lynch"]["auto_classified"] == "stalwart"
    assert result["growth"]["structural_discount_pct"] > 0.10  # v3.8 가드 임계값 초과 확인
    assert result["lynch"]["overridden_down"] is False
    assert not any("이중 반영 경고" in x for x in result["data_limitations"])


def test_deceleration_double_count_warns_when_override_down_and_discount_high():
    """
    v3.19 전면점검(2026-07-26)에서 발견: check_deceleration_double_count()가
    pipeline.py에 배선돼 있지 않아 한 번도 호출되지 않았다. structural_discount가
    10%를 넘고(MNST 11.1%) lynch_type을 성장상한이 더 낮은 유형으로 하향
    오버라이드하면 이중반영 경고가 떠야 한다.
    """
    result = run_analysis(mnst_inputs(
        lynch_type_override="slow_grower",  # g_max 0.05 < stalwart의 0.12
        lynch_type_override_reason="가드 배선 테스트용 인위적 하향 오버라이드",
    ))
    assert result["lynch"]["overridden_down"] is True
    assert any("이중 반영 경고" in x for x in result["data_limitations"])


def test_deceleration_double_count_silent_when_override_up():
    """상향 오버라이드는 이중반영 우려 대상이 아니므로 경고가 없어야 한다."""
    result = run_analysis(mnst_inputs(
        lynch_type_override="fast_grower",  # g_max 0.25 > stalwart의 0.12
        lynch_type_override_reason="가드 배선 테스트용 인위적 상향 오버라이드",
    ))
    assert result["lynch"]["overridden_down"] is False
    assert not any("이중 반영 경고" in x for x in result["data_limitations"])


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


# ----------------------------------------------------------------------
# 과거 기록 자동 대조 (v3.19) - "대조하는 습관"을 코드로 고정
# ----------------------------------------------------------------------

def test_cross_check_detects_100x_rar_scale_mismatch():
    """트래커 감사에서 실제로 발견된 유형: 과거 RAR이 100배 작게 기록된 경우."""
    from engine.pipeline import cross_check_prior_record

    result = run_analysis(cdns_inputs())  # RAR = -0.5994
    warnings = cross_check_prior_record(result, {"rar": -0.006})
    assert any("RAR 스케일 경고" in w for w in warnings)


def test_cross_check_detects_sign_flip():
    from engine.pipeline import cross_check_prior_record

    result = run_analysis(cdns_inputs())
    warnings = cross_check_prior_record(result, {"rar": 0.55})
    assert any("RAR 부호 반전" in w for w in warnings)


def test_cross_check_detects_model_mismatch_ph_case():
    """
    PH 사례를 코드가 잡을 수 있는지 확인: 과거 내재성장률이 two_stage에 가까운데
    single_stage로 계산하면 경고가 나와야 한다.
    """
    from engine.pipeline import cross_check_prior_record

    result = run_analysis(cdns_inputs())  # single_stage 사용
    # 과거 기록이 two_stage 값(19.69%)에 가까운 상황을 가정
    warnings = cross_check_prior_record(result, {"implied_growth": 0.1950})
    assert any("모델 불일치 의심" in w for w in warnings)


def test_cross_check_silent_when_records_agree():
    from engine.pipeline import cross_check_prior_record

    result = run_analysis(cdns_inputs())
    warnings = cross_check_prior_record(
        result,
        {"rar": result["rar"], "gap": result["expectation_gap"],
         "drs": result["drs"]["score"],
         "implied_growth": result["implied_growth"]["value"]},
    )
    assert warnings == []


def test_inputs_reject_negative_capex_sign_convention():
    """
    v3.19 실사고 회귀 방지(2026-07-25 BRO): Fiscal.ai는 capex를 음수(유출)로 준다.
    그대로 넣으면 fcf = ocf - capex 가 capex를 더해버려 FCF가 2x capex만큼 과대계상된다.
    """
    negative_capex = {y: -v for y, v in CDNS_CAPEX.items()}
    with pytest.raises(ValueError) as exc:
        cdns_inputs(capex_by_year=negative_capex)
    assert "capex" in str(exc.value)
    assert "과대계상" in str(exc.value)


def test_sensitivity_check_uses_same_model_as_section_5_single_stage():
    """
    v3.19 근본수정(2026-07-26): sensitivity_check가 더 이상 항상 two_stage로
    판정하지 않고, Section 5(model_used)와 같은 모델로 판정해야 한다.
    single_stage를 쓴 CDNS의 경우, 강건성점검의 implied_growth_with_drs는
    compare_implied_growth_models()의 single_stage 값(둘 다 같은 r=r_with_drs를
    씀)과 정확히 일치해야 한다(과거 버그였다면 대신 two_stage 값과 가까웠을 것).
    """
    result = run_analysis(cdns_inputs())  # model_used="single_stage"
    models = result["implied_growth"]["models"]
    sensitivity = result["sensitivity_check"]
    assert sensitivity["implied_growth_with_drs"] == pytest.approx(
        models["single_stage"], abs=1e-9
    )
    assert sensitivity["implied_growth_with_drs"] != pytest.approx(
        models["two_stage"], abs=1e-4
    )


def test_sensitivity_check_uses_same_model_as_section_5_two_stage():
    """Section 5가 two_stage를 쓰면 강건성점검도 two_stage로 판정해야 한다."""
    result = run_analysis(cdns_inputs(
        model_used="two_stage",
        model_choice_reason="two_stage 컨벤션 테스트용",
    ))
    models = result["implied_growth"]["models"]
    sensitivity = result["sensitivity_check"]
    assert sensitivity["implied_growth_with_drs"] == pytest.approx(
        models["two_stage"], abs=1e-9
    )


def test_sensitivity_check_no_longer_emits_stale_interpretation_warning():
    """
    v3.19 근본수정으로 [강건성점검 해석주의] 임시 우회 경고문은 제거됐다
    (모델이 항상 일치하니 더 이상 필요 없음). data_limitations에 이 문구가
    다시 나타나면 회귀다.
    """
    result = run_analysis(cdns_inputs())
    assert not any("강건성점검 해석주의" in x for x in result["data_limitations"])


# ----------------------------------------------------------------------
# v3.20: capex 급증 분류 배선 (v3.6/v3.7 함수가 그전까지 미실행이었다)
# ----------------------------------------------------------------------

def test_capex_classification_defaults_to_none_and_changes_nothing():
    """미지정이면 기존 동작과 완전히 동일해야 한다(순수 가산적 변경)."""
    base = run_analysis(cdns_inputs())
    assert base["growth"]["capex_adjustment"] is None
    explicit_none = run_analysis(cdns_inputs(capex_classification=None))
    assert explicit_none["growth"]["realistic_growth"] == base["growth"]["realistic_growth"]
    assert explicit_none["rar"] == base["rar"]


def test_capex_classification_rejects_unknown_value():
    with pytest.raises(ValueError):
        cdns_inputs(capex_classification="capex_good",
                    capex_classification_basis="아무말")


def test_capex_classification_requires_basis():
    """
    '성장투자' 분류는 FCF CAGR을 올려 판정을 뒤집을 수 있으므로
    model_choice_reason과 동일하게 근거를 강제한다.
    """
    with pytest.raises(ValueError) as exc:
        cdns_inputs(capex_classification="growth_investment")
    assert "capex_classification_basis" in str(exc.value)


def _capex_spike_inputs(**overrides):
    """
    최근년도 capex를 인위적으로 급증시켜 capex_intensity delta가 v3.7 임계값
    (3%p)을 넘게 만든 케이스. NVO(capex 5년새 9.5배)를 축소 재현한 것.
    """
    spiked = dict(CDNS_CAPEX)
    spiked[2025] = int(CDNS_REVENUE[2025] * 0.09)   # capex/매출 9%로 급증
    base = dict(capex_by_year=spiked)
    base.update(overrides)
    return cdns_inputs(**base)


def test_growth_investment_classification_raises_fcf_cagr_and_records_limitation():
    margin = run_analysis(_capex_spike_inputs(
        capex_classification="margin_erosion",
        capex_classification_basis="증설 근거 없음 - 보수적으로 마진훼손 처리",
    ))
    growth = run_analysis(_capex_spike_inputs(
        capex_classification="growth_investment",
        capex_classification_basis="증설계획 공시 및 수주잔고 확인(테스트용 가정)",
    ))
    adj = growth["growth"]["capex_adjustment"]
    assert adj is not None
    assert adj["fcf_cagr_after"] > adj["fcf_cagr_before"]
    # 성장투자로 부르면 현실적성장률이 같거나 높아진다(캡에 걸리면 같을 수 있음)
    assert growth["growth"]["realistic_growth"] >= margin["growth"]["realistic_growth"]
    assert any("capex 분류 조정" in x for x in growth["data_limitations"])


def test_margin_erosion_keeps_fcf_cagr_unchanged():
    """마진훼손으로 분류하면 FCF CAGR을 그대로 채택(보수 유지)해야 한다."""
    result = run_analysis(_capex_spike_inputs(
        capex_classification="margin_erosion",
        capex_classification_basis="가동률 하락으로 마진훼손 판단(테스트용 가정)",
    ))
    adj = result["growth"]["capex_adjustment"]
    assert adj["fcf_cagr_after"] == pytest.approx(adj["fcf_cagr_before"])
    assert not any("capex 분류 조정" in x for x in result["data_limitations"])


def test_growth_investment_claim_inconsistency_surfaces_when_revenue_decelerating():
    """
    v3.7 validate_growth_investment_claim: 매출이 둔화중인데 capex 급증을
    '성장투자'라 주장하면 정합성 경고가 data_limitations에 올라와야 한다.
    """
    decelerating = dict(CDNS_REVENUE)
    for y in (2023, 2024, 2025):        # 최근 3년을 평탄하게 만들어 3y CAGR을 떨군다
        decelerating[y] = CDNS_REVENUE[2022]
    result = run_analysis(_capex_spike_inputs(
        revenue_by_year=decelerating,
        capex_classification="growth_investment",
        capex_classification_basis="증설 주장(정합성 경고 발동 확인용)",
    ))
    assert any("capex 정합성" in x for x in result["data_limitations"])


def test_capex_adjustment_reuses_weighted_average_not_recomputed():
    """
    CLAUDE.md 배선지침 준수 확인: fcf_conservatism_adjustment에 넘긴
    revenue_weighted_cagr이 realistic_growth_estimate가 계산한
    base_growth_before_fcf_check와 동일해야 한다(중복 구현 금지).
    """
    result = run_analysis(_capex_spike_inputs(
        capex_classification="growth_investment",
        capex_classification_basis="배선 검증용",
    ))
    adj = result["growth"]["capex_adjustment"]
    blended = 0.7 * adj["fcf_cagr_before"] + 0.3 * result["growth"]["breakdown"]["base_growth_before_fcf_check"]
    expected = min(blended, result["growth"]["breakdown"]["base_growth_before_fcf_check"])
    assert adj["fcf_cagr_after"] == pytest.approx(expected, abs=1e-12)


# ----------------------------------------------------------------------
# v3.21: CAGR 기준연도 override (BKNG 실사례에서 도출)
# ----------------------------------------------------------------------

def _covid_shaped_inputs(**overrides):
    """
    BKNG 패턴 재현: 5년 전(기본 기준연도)이 코로나로 FCF 음수인 케이스.
    2020년 OCF를 capex보다 작게 만들어 FCF를 음수로 떨군다.
    """
    ocf = dict(CDNS_OCF)
    ocf[2020] = 50_000_000          # capex(94,813,000)보다 작음 -> FCF 음수
    base = dict(operating_cashflow_by_year=ocf)
    base.update(overrides)
    return cdns_inputs(**base)


def test_negative_fcf_at_default_base_year_is_rejected_without_override():
    """
    기본 기준연도의 FCF가 음수면 CAGR이 정의되지 않으므로 실행이 거부돼야 한다.
    BKNG(FY2020 FCF -$201M)이 실제로 이 벽에 부딪혔다.
    """
    with pytest.raises(ValueError) as exc:
        run_analysis(_covid_shaped_inputs())
    assert "FCF 5y" in str(exc.value)


def test_cagr_base_year_override_unblocks_and_records_limitation():
    result = run_analysis(_covid_shaped_inputs(
        cagr_base_year_override=2019,
        cagr_base_year_override_reason="2020년이 일회성 충격으로 FCF 음수(테스트용 가정)",
    ))
    assert result["derived"]["cagr_5y_base_year"] == 2019
    assert result["derived"]["cagr_5y_span"] == 6
    assert any("CAGR 기준연도 변경" in x for x in result["data_limitations"])


def test_cagr_base_year_override_applies_to_both_revenue_and_fcf():
    """
    매출과 FCF에 서로 다른 창을 쓰면 realistic_growth_estimate의 min() 비교가
    성립하지 않는다. 반드시 같은 기준연도를 써야 한다.
    """
    result = run_analysis(cdns_inputs(
        cagr_base_year_override=2018,
        cagr_base_year_override_reason="양쪽 동일 적용 검증용",
    ))
    d = result["derived"]
    span = d["cagr_5y_span"]
    expected_rev = (CDNS_REVENUE[2025] / CDNS_REVENUE[2018]) ** (1 / span) - 1
    fcf18 = CDNS_OCF[2018] - CDNS_CAPEX[2018]
    fcf25 = CDNS_OCF[2025] - CDNS_CAPEX[2025]
    expected_fcf = (fcf25 / fcf18) ** (1 / span) - 1
    assert d["revenue_cagr_5y"] == pytest.approx(expected_rev, abs=1e-12)
    assert d["fcf_cagr_5y"] == pytest.approx(expected_fcf, abs=1e-12)


def test_cagr_base_year_override_requires_reason():
    with pytest.raises(ValueError) as exc:
        cdns_inputs(cagr_base_year_override=2019)
    assert "cagr_base_year_override_reason" in str(exc.value)


def test_cagr_base_year_override_rejects_year_not_in_data():
    with pytest.raises(ValueError):
        cdns_inputs(cagr_base_year_override=2009,
                    cagr_base_year_override_reason="데이터에 없는 해")


def test_cagr_base_year_override_rejects_latest_year():
    with pytest.raises(ValueError):
        cdns_inputs(cagr_base_year_override=2025,
                    cagr_base_year_override_reason="최근년도는 기준이 될 수 없음")


def test_cagr_base_year_default_is_unchanged():
    """override 미지정 시 기존 동작(years[-6], 5년)과 완전히 동일해야 한다."""
    result = run_analysis(cdns_inputs())
    assert result["derived"]["cagr_5y_base_year"] == 2020
    assert result["derived"]["cagr_5y_span"] == 5


# ----------------------------------------------------------------------
# v3.22: 보험업 FCF-DCF 교차검증 (ACGL/PGR 실사례에서 도출)
# ----------------------------------------------------------------------

def test_is_insurer_requires_three_series():
    with pytest.raises(ValueError) as exc:
        cdns_inputs(is_insurer=True)
    msg = str(exc.value)
    assert "net_income_by_year" in msg
    assert "shareholders_equity_by_year" in msg
    assert "dividends_paid_by_year" in msg


def test_is_insurer_partial_series_still_rejected():
    """세 시계열 중 일부만 있어도 거부돼야 한다(부분 데이터로 왜곡된 ROE 계산 방지)."""
    with pytest.raises(ValueError) as exc:
        cdns_inputs(
            is_insurer=True,
            net_income_by_year={2025: 1_000_000},
            shareholders_equity_by_year={2025: 10_000_000},
            # dividends_paid_by_year 누락
        )
    assert "dividends_paid_by_year" in str(exc.value)


def _pgr_like_inputs(**overrides):
    """
    PGR 실사례(2026-07-28 정식분석)를 축약 재현. 5개년 ROE 평균과 3개년
    배당성향으로 지속가능성장률을 계산하는 경로를 검증한다.
    """
    net_income = {2021: 3_350_900, 2022: 721_500, 2023: 3_903_000,
                  2024: 8_480_000, 2025: 11_308_000}
    equity = {2021: 18_231_600, 2022: 15_891_000, 2023: 20_277_000,
              2024: 25_591_000, 2025: 30_323_000}
    dividends = {2023: 277_000, 2024: 682_000, 2025: 2_871_000}
    base = dict(
        is_insurer=True,
        net_income_by_year=net_income,
        shareholders_equity_by_year=equity,
        dividends_paid_by_year=dividends,
        market_cap=125_440_000_000,
    )
    base.update(overrides)
    return cdns_inputs(**base)


def test_insurer_cross_check_matches_hand_calculation():
    """PGR 스크립트에서 손으로 계산한 값과 파이프라인 자동계산이 일치해야 한다."""
    result = run_analysis(_pgr_like_inputs())
    cross = result["insurer_cross_check"]
    assert cross is not None

    net_income = {2021: 3_350_900, 2022: 721_500, 2023: 3_903_000,
                  2024: 8_480_000, 2025: 11_308_000}
    equity = {2021: 18_231_600, 2022: 15_891_000, 2023: 20_277_000,
              2024: 25_591_000, 2025: 30_323_000}
    expected_roe = sum(net_income[y] / equity[y] for y in equity) / len(equity)
    assert cross["avg_roe"] == pytest.approx(expected_roe, abs=1e-12)

    total_div = 277_000 + 682_000 + 2_871_000
    total_ni_3y = 3_903_000 + 8_480_000 + 11_308_000
    expected_payout = total_div / total_ni_3y
    assert cross["payout_ratio"] == pytest.approx(expected_payout, abs=1e-12)
    assert cross["retention_ratio"] == pytest.approx(1 - expected_payout, abs=1e-12)
    assert cross["sustainable_growth"] == pytest.approx(
        expected_roe * (1 - expected_payout), abs=1e-12
    )
    assert cross["price_to_book"] == pytest.approx(125_440_000_000 / 30_323_000, abs=1e-6)


def test_insurer_cross_check_none_when_not_insurer():
    result = run_analysis(cdns_inputs())
    assert result["insurer_cross_check"] is None


def test_insurer_cross_check_flags_large_divergence():
    """
    Realistic Growth와 지속가능성장률이 크게 벌어지면(ACGL 유형) 경고가
    남아야 한다 - 낮은 ROE/보수적 배당으로 지속가능성장률을 인위적으로
    낮게 만들어 괴리를 유발한다.
    """
    result = run_analysis(_pgr_like_inputs(
        net_income_by_year={y: v * 0.1 for y, v in
                             {2021: 3_350_900, 2022: 721_500, 2023: 3_903_000,
                              2024: 8_480_000, 2025: 11_308_000}.items()},
    ))
    cross = result["insurer_cross_check"]
    divergence = abs(result["growth"]["realistic_growth"] - cross["sustainable_growth"])
    assert divergence >= 0.05
    assert any("보험업 교차검증 경고" in x for x in result["data_limitations"])


def test_insurer_cross_check_no_warning_when_growth_estimates_agree():
    result = run_analysis(_pgr_like_inputs())
    cross = result["insurer_cross_check"]
    divergence = abs(result["growth"]["realistic_growth"] - cross["sustainable_growth"])
    if divergence < 0.05:
        assert any(
            x.startswith("[보험업 교차검증]") for x in result["data_limitations"]
        )
        assert not any("보험업 교차검증 경고" in x for x in result["data_limitations"])
    assert not any("CAGR 기준연도 변경" in x for x in result["data_limitations"])


# ----------------------------------------------------------------------
# v3.23: SBC 병기 교차검증 (2026-08-01 방법론 감사 Critical-1에서 배선)
# ----------------------------------------------------------------------

def test_sbc_cross_check_none_when_not_provided():
    """sbc_by_year를 안 넘기면 기존 동작 그대로(opt-in) - None이어야 한다."""
    result = run_analysis(cdns_inputs())
    assert result["sbc_cross_check"] is None


def test_sbc_by_year_rejects_negative_values():
    with pytest.raises(ValueError) as exc:
        cdns_inputs(sbc_by_year={2025: -1000})
    assert "sbc_by_year" in str(exc.value)


def test_sbc_by_year_requires_latest_year():
    """fcf0와 동일 시점 비교가 전제이므로 최근 회계연도가 없으면 거부한다."""
    with pytest.raises(ValueError) as exc:
        cdns_inputs(sbc_by_year={2020: 1000})
    assert "최근 회계연도" in str(exc.value)


def test_sbc_cross_check_small_sbc_no_warning():
    """SBC가 FCF의 5%면 판정도 그대로고 경고도 안 남아야 한다."""
    fcf0 = 1728781000 - 141871000
    result = run_analysis(cdns_inputs(sbc_by_year={2025: int(fcf0 * 0.05)}))
    cross = result["sbc_cross_check"]
    assert cross["judgment_flipped"] is False
    assert not any("SBC 교차검증" in x for x in result["data_limitations"])


def test_sbc_cross_check_large_sbc_warns_without_flip():
    """SBC가 30% 이상이면 판정이 안 뒤집혀도 경고는 남아야 한다."""
    fcf0 = 1728781000 - 141871000
    result = run_analysis(cdns_inputs(sbc_by_year={2025: int(fcf0 * 0.40)}))
    cross = result["sbc_cross_check"]
    assert cross["judgment_flipped"] is False
    assert any(x.startswith("[SBC 교차검증]") for x in result["data_limitations"])


def test_sbc_cross_check_flips_judgment():
    """
    2026-08-01 방법론 감사에서 실제로 WDAY가 이 경로로 뒤집힌 사례를 재현한다.
    시총을 낮춰 저평가 가능성으로 만든 뒤 SBC를 크게 넣으면 적정가로 돌아와야 한다.
    """
    fcf0 = 1728781000 - 141871000
    low_mc = 40_000_000_000
    baseline = run_analysis(cdns_inputs(market_cap=low_mc))
    assert baseline["judgment"] == "저평가 가능성"

    result = run_analysis(cdns_inputs(
        market_cap=low_mc, sbc_by_year={2025: int(fcf0 * 0.5)}
    ))
    cross = result["sbc_cross_check"]
    assert result["judgment"] == "저평가 가능성"  # 원 판정은 그대로 유지
    assert cross["judgment_sbc_adjusted"] == "적정가/경계선"  # SBC차감 시나리오만 뒤집힘
    assert cross["judgment_flipped"] is True
    assert any("SBC 교차검증 경고" in x for x in result["data_limitations"])
    assert any("뒤집힌다" in x for x in result["data_limitations"])


def test_sbc_cross_check_not_applicable_when_sbc_exceeds_fcf():
    """SBC가 FCF보다 크면 차감시 FCF가 음수가 되어 DCF 자체가 불가능(Not Applicable)."""
    fcf0 = 1728781000 - 141871000
    result = run_analysis(cdns_inputs(sbc_by_year={2025: int(fcf0 * 1.5)}))
    cross = result["sbc_cross_check"]
    assert cross["fcf0_sbc_adjusted"] < 0
    assert cross["implied_growth_sbc_adjusted"] is None
    assert cross["judgment_sbc_adjusted"] is None
    assert any("Not Applicable" in x for x in result["data_limitations"])


# ----------------------------------------------------------------------
# v3.24: 반증조건·분석시점 주가/통화 병기 (2026-08-01 방법론 감사 권고 #2/#3)
# ----------------------------------------------------------------------

def test_falsification_price_currency_default_none_when_not_provided():
    """세 필드 모두 opt-in - 안 넘기면 falsification/price는 None, currency는 USD 기본값."""
    result = run_analysis(cdns_inputs())
    meta = result["meta"]
    assert meta["falsification_conditions"] is None
    assert meta["price_at_analysis"] is None
    assert meta["currency"] == "USD"


def test_falsification_price_currency_pass_through():
    """넘긴 값이 그대로 meta에 병기되어야 한다 - 계산에는 관여하지 않는다."""
    result = run_analysis(cdns_inputs(
        falsification_conditions=(
            "차년도 EDA 매출성장률이 8% 밑으로 떨어지면(경쟁강도 과소평가) "
            "이 판정은 틀린 것으로 간주한다."
        ),
        price_at_analysis=345.67,
        currency="USD",
    ))
    meta = result["meta"]
    assert "8%" in meta["falsification_conditions"]
    assert meta["price_at_analysis"] == pytest.approx(345.67)
    assert meta["currency"] == "USD"
    # 계산 경로에는 영향을 주지 않아야 한다 - 골든 회귀값과 동일해야 함
    assert result["expectation_gap"] == pytest.approx(0.0329, abs=5e-4)


# ----------------------------------------------------------------------
# v3.24: 성장상한 바인딩 경고 (2026-08-01 방법론 감사 M-1, 권고 #6)
# ----------------------------------------------------------------------

def test_growth_cap_binding_warns_when_upper_cap_overrides_calculated_growth():
    """
    상한 캡이 바인딩되면(=계산된 성장률이 Lynch 유형 상한보다 높음) Realistic
    Growth가 매출·FCF CAGR 계산과 무관하게 상한값으로 고정된다는 사실을
    data_limitations에 명시적으로 남겨야 한다(M-1: 안 남기면 조용히 순위를
    결정한다).
    """
    result = run_analysis(mnst_inputs(
        lynch_type_override="slow_grower",  # g_max 5.0% - MNST 계산성장률보다 낮음
        lynch_type_override_reason="가드 배선 테스트용 인위적 하향 오버라이드",
    ))
    assert result["growth"]["breakdown"]["cap_applied"] is not None
    assert result["growth"]["realistic_growth"] == pytest.approx(0.05)
    assert any("성장상한 바인딩" in x for x in result["data_limitations"])


def test_growth_cap_binding_silent_when_not_bound():
    """캡이 안 걸리면(기본 stalwart 자동분류) 경고가 없어야 한다."""
    result = run_analysis(mnst_inputs())
    assert result["growth"]["breakdown"]["cap_applied"] is None
    assert not any("성장상한 바인딩" in x for x in result["data_limitations"])


# ----------------------------------------------------------------------
# v3.28: realistic_growth_override 배선 (2026-08-04, ROP 유기적성장률
# 교차검증이 실증사례 - Lynch 캡이 만든 여유폭이 회사 실제 공시 성장률과
# 크게 괴리됨을 확인한 뒤 공식판정으로 승격)
# ----------------------------------------------------------------------

def test_realistic_growth_override_defaults_to_none_and_changes_nothing():
    """override를 안 쓰면 기존 CDNS 골든 결과와 완전히 동일해야 한다."""
    result = run_analysis(cdns_inputs())
    assert result["growth"]["realistic_growth"] == pytest.approx(0.12, abs=1e-4)
    assert "realistic_growth_override_applied" not in result["growth"]["breakdown"]
    assert not any("Realistic Growth 오버라이드" in x for x in result["data_limitations"])


def test_realistic_growth_override_requires_reason():
    with pytest.raises(ValueError, match="realistic_growth_override"):
        cdns_inputs(realistic_growth_override=0.05)


def test_realistic_growth_override_replaces_capped_growth_and_can_flip_judgment():
    """
    CDNS는 stalwart 캡(12%)이 바인딩된 골든 케이스(Implied Growth 8.71%,
    Gap +3.29%p, 적정가/경계선). 오버라이드로 2%를 직접 넣으면 캡을 완전히
    우회해 Gap이 -5%p 경계 밖으로 뒤집혀야 한다(과대평가 가능성) - CAGR
    계산이나 캡과 무관하게 override 값이 그대로 쓰인다는 증거.
    """
    result = run_analysis(cdns_inputs(
        realistic_growth_override=0.02,
        realistic_growth_override_reason="가드 배선 테스트용 인위적 오버라이드",
    ))
    assert result["growth"]["realistic_growth"] == pytest.approx(0.02)
    applied = result["growth"]["breakdown"]["realistic_growth_override_applied"]
    assert applied["pre_override_growth"] == pytest.approx(0.12, abs=1e-4)
    assert applied["override_value"] == pytest.approx(0.02)
    assert result["expectation_gap"] < 0
    assert result["judgment"] == "과대평가 가능성"
    assert any("Realistic Growth 오버라이드" in x for x in result["data_limitations"])


# ----------------------------------------------------------------------
# v3.24: structural_discount_rate 10y 대체값 버그수정
# (2026-08-01 방법론 감사 M-3 - data_limitations 경고문은 "5년 CAGR을 대체
# 입력했다"고 이미 약속하고 있었는데 실제 코드는 rev_cagr_3y를 넣고 있었다.
# rev_cagr_3y를 자기 자신과 비교하면 trend_delta가 항상 정확히 0이 되어
# 구조적 할인율이 신호 없이 base_discount 고정값만 반환하는 결과를 낳았다)
# ----------------------------------------------------------------------

def _short_history_inputs(**overrides):
    """10년치가 없는(6개년만 확보) 합성 fixture - fallback 경로를 강제로 태운다."""
    rev = {2020: 100e6, 2021: 112e6, 2022: 126e6, 2023: 150e6, 2024: 178e6, 2025: 210e6}
    base = dict(
        ticker="SYNTH",
        company_name="Synthetic Test Co.",
        revenue_by_year=rev,
        operating_income_by_year={y: v * 0.20 for y, v in rev.items()},
        operating_cashflow_by_year={y: v * 0.25 for y, v in rev.items()},
        capex_by_year={y: v * 0.05 for y, v in rev.items()},
        market_cap=3_000_000_000,
        net_debt=-500_000_000,
        ebitda=rev[2025] * 0.20 + 5_000_000,
        risk_free_rate=0.045,
        competitor_threat_weights=[0.3, 0.2],
        market_share_trend_pp_per_year=0.0,
        active_antitrust_or_regulatory_case=False,
        demand_sensitivity_pct=0.2,
        subjective_input_basis="합성 fixture - M-3 fallback 경로 검증용, 실제 근거 없음",
        model_used="single_stage",
        model_choice_reason="합성 fixture - 모델괴리 무관, single_stage로 고정",
        data_sources=["synthetic"],
    )
    base.update(overrides)
    return AnalysisInputs(**base)


def test_structural_discount_fallback_uses_5y_not_3y():
    """
    10년 CAGR이 없을 때 structural_discount_rate에 넘어가는 대체값이 rev_cagr_3y가
    아니라 rev_cagr_5y여야 한다(data_limitations 경고문이 이미 그렇게 약속하고
    있었다). rev_cagr_3y로 자기 자신과 비교하면 trend_delta가 항상 정확히 0이 되어
    버그 있는 경로에서는 정확히 base_discount(10%)가 나온다 - 고쳐진 경로는
    3y(18.56%)와 5y(16.00%)가 다르므로 0이 아닌 값이 나와야 한다.
    """
    result = run_analysis(_short_history_inputs())
    d = result["derived"]
    assert d["revenue_cagr_10y"] is None  # fallback 경로 확인
    assert d["revenue_cagr_3y"] == pytest.approx(0.18563, abs=1e-4)
    assert d["revenue_cagr_5y"] == pytest.approx(0.15996, abs=1e-4)

    structural_discount = result["growth"]["structural_discount_pct"]
    # 버그 있던 경로(rev_cagr_3y를 자기 자신과 비교)라면 trend_delta=0이라
    # 정확히 10.00%가 나왔을 것 - 고쳐진 경로는 그렇지 않아야 한다.
    assert structural_discount != pytest.approx(0.10, abs=1e-6)
    # 3y > 5y(가속 중)이므로 trend_delta(5y-3y)가 음수 -> 할인율이 base보다 낮아야 함
    assert structural_discount < 0.10


def test_structural_discount_10y_data_present_unaffected():
    """10년 데이터가 실제로 있으면(CDNS) 이 fallback 경로 자체를 타지 않는다."""
    result = run_analysis(cdns_inputs())
    assert result["derived"]["revenue_cagr_10y"] is not None
    assert not any("10년 CAGR 산출 불가" in x for x in result["data_limitations"])


# ----------------------------------------------------------------------
# v3.25: n_requested 기본값(12) 이탈 시 사유 필수화
# (2026-08-01 방법론 감사 M-4 - capped_n()이 8~15년 차등화를 지원하지만
# 36종목 ledger 전부가 기본값 12를 그대로 썼다. 버그는 아니고 미사용
# 유연성이었을 뿐이라 강제 로직은 넣지 않고, 이탈 시 근거만 요구한다)
# ----------------------------------------------------------------------

def test_n_requested_default_needs_no_reason():
    """기본값 12를 그대로 쓰면(기존 36종목 전부 이 경로) 사유 없이도 통과해야 한다."""
    result = run_analysis(cdns_inputs())
    assert result["discount_rate"]["n"] == 12


def test_n_requested_override_without_reason_rejected():
    with pytest.raises(ValueError) as exc:
        cdns_inputs(n_requested=15)
    assert "n_requested_reason" in str(exc.value)


def test_n_requested_override_with_reason_accepted():
    result = run_analysis(cdns_inputs(
        n_requested=15,
        n_requested_reason="가드 배선 테스트용 - 실제 해자 근거 아님",
    ))
    assert result["discount_rate"]["n"] == 15


# ----------------------------------------------------------------------
# v3.26: RAR 방향성 경고 (2026-08-02 방법론 감사 M-2)
# RAR=ER/DRS는 ER이 음수일 때 방향이 뒤집힌다(DRS가 클수록 RAR이 0에 가깝게
# 압축돼 "덜 나빠 보임"). 공식 자체(과거 트래커 전체가 이 컨벤션)는 바꾸지
# 않고 경고만 남긴다.
# ----------------------------------------------------------------------

def test_rar_direction_warning_fires_when_er_negative():
    """CDNS 기본 fixture는 ER이 음수(-21.94%) - 경고가 남아야 한다."""
    result = run_analysis(cdns_inputs())
    assert result["scenarios"]["expected_return_decimal"] < 0
    assert any("RAR 방향성 경고" in x for x in result["data_limitations"])


def test_rar_direction_warning_silent_when_er_positive():
    """시총을 낮춰 ER을 양수로 만들면(정상 동작 구간) 경고가 없어야 한다."""
    result = run_analysis(cdns_inputs(market_cap=40_000_000_000))
    assert result["scenarios"]["expected_return_decimal"] > 0
    assert not any("RAR 방향성 경고" in x for x in result["data_limitations"])


# ----------------------------------------------------------------------
# v3.27: 판정 세분화(Judgment Grade, 2026-08-02 사용자 요청)
# 기존 3단계(±5%p) 경계는 그대로 두고 6단계(S/A/B/C/D/F)로 세분화만 추가.
# ----------------------------------------------------------------------

def test_judgment_grade_boundaries():
    """S>=15%p, A 7~15%p, B 5~7%p, C -5~5%p, D -15~-5%p, F<=-15%p."""
    assert judgment_grade_from_gap(0.30) == "S"
    assert judgment_grade_from_gap(0.15) == "S"
    assert judgment_grade_from_gap(0.1499) == "A"
    assert judgment_grade_from_gap(0.07) == "A"
    assert judgment_grade_from_gap(0.0699) == "B"
    assert judgment_grade_from_gap(0.05) == "B"
    assert judgment_grade_from_gap(0.0499) == "C"
    assert judgment_grade_from_gap(0.0) == "C"
    assert judgment_grade_from_gap(-0.0499) == "C"
    assert judgment_grade_from_gap(-0.05) == "D"
    assert judgment_grade_from_gap(-0.1499) == "D"
    assert judgment_grade_from_gap(-0.15) == "F"
    assert judgment_grade_from_gap(-0.30) == "F"


def test_judgment_grade_is_strict_subset_of_judgment():
    """S/A/B는 전부 '저평가 가능성'의 부분집합, D/F는 '과대평가 가능성'의 부분집합이어야 한다."""
    for gap in [0.30, 0.15, 0.10, 0.07, 0.06, 0.05]:
        assert judgment_grade_from_gap(gap) in ("S", "A", "B")
    for gap in [0.0499, 0.0, -0.0499]:
        assert judgment_grade_from_gap(gap) == "C"
    for gap in [-0.05, -0.10, -0.15, -0.30]:
        assert judgment_grade_from_gap(gap) in ("D", "F")


def test_judgment_grade_wired_into_run_analysis():
    result = run_analysis(cdns_inputs())
    assert result["judgment_grade"] in ("S", "A", "B", "C", "D", "F")
    # CDNS golden case: judgment="적정가/경계선" (Gap +3.29%p) -> grade는 반드시 C
    assert result["judgment"] == "적정가/경계선"
    assert result["judgment_grade"] == "C"


# ----------------------------------------------------------------------
# v3.32 (2026-08-05 감사) — 버전 스탬프·판정 단일화·오버라이드 캡플래그
# ----------------------------------------------------------------------


def test_engine_version_comes_from_single_constant():
    """
    ledger의 engine_version은 반드시 ENGINE_VERSION 상수에서 나와야 한다.

    배경(실제 사고): v3.27까지는 이 값이 run_analysis() 본문에 문자열
    리터럴로 박혀 있었고, v3.28에서 realistic_growth_override(계산 결과를
    바꾸는 기능)를 배선하면서 아무도 그 리터럴을 올리지 않았다. 그 결과
    ledger/ROP_2026-08-04.json은 v3.27로 스탬프돼 있으면서 v3.27에는
    존재하지 않는 필드를 담고 있다 - 스탬프가 거짓말을 하는 상태였다.
    """
    from engine.expectation_gap_engine import ENGINE_VERSION

    result = run_analysis(cdns_inputs())
    assert result["meta"]["engine_version"] == ENGINE_VERSION
    # 리터럴이 다시 기어들어오면 이 assert가 잡는다.
    assert ENGINE_VERSION.startswith("v3.")


def test_judgment_uses_single_shared_rule_everywhere():
    """
    최상위 judgment와 sensitivity_check의 판정이 같은 함수(judgment_from_gap)를
    쓰는지 확인한다. v3.32 이전에는 sensitivity_check 안에 사본이 있었고
    중립 라벨만 "적정가"로 갈려 있어, 한 ledger 안에서 같은 규칙의 출력이
    두 이름으로 저장됐다(36건 중 13건).
    """
    from engine.expectation_gap_engine import (
        JUDGMENT_NEUTRAL,
        JUDGMENT_OVERVALUED,
        JUDGMENT_UNDERVALUED,
        judgment_from_gap,
    )

    allowed = {JUDGMENT_UNDERVALUED, JUDGMENT_NEUTRAL, JUDGMENT_OVERVALUED}
    result = run_analysis(cdns_inputs())

    assert result["judgment"] == judgment_from_gap(result["expectation_gap"])
    assert result["sensitivity_check"]["judgment_with_drs"] in allowed
    assert result["sensitivity_check"]["judgment_without_drs"] in allowed
    # 중립 구간 라벨이 두 곳에서 동일해야 한다(v3.32에서 통일한 지점).
    assert judgment_from_gap(0.0) == JUDGMENT_NEUTRAL == "적정가/경계선"


def test_judgment_from_gap_matches_pipeline_boundaries():
    from engine.expectation_gap_engine import judgment_from_gap

    assert judgment_from_gap(0.05) == "저평가 가능성"
    assert judgment_from_gap(0.0499) == "적정가/경계선"
    assert judgment_from_gap(-0.0499) == "적정가/경계선"
    assert judgment_from_gap(-0.05) == "과대평가 가능성"


def test_override_clears_cap_flag_but_keeps_penalty():
    """
    realistic_growth_override가 캡을 우회하면 cap_applied는 사실대로 None이
    되어야 하고(ledger 자기모순 제거), 감점은 사라지는 게 아니라 실제 원인인
    realistic_growth_overridden 항목으로 옮겨가야 한다.

    ROP 실사례: Realistic Growth는 5.5%인데 cap_applied에는 "상한 캡
    적용(12.0%)"이 남아 있었고, 걸리지도 않은 캡을 근거로 -5점이 붙어 있었다.
    """
    base = run_analysis(cdns_inputs())
    assert base["confidence"]["adjustments"]["realistic_growth_overridden"] == 0

    result = run_analysis(cdns_inputs(
        realistic_growth_override=0.02,
        realistic_growth_override_reason="캡 플래그 정정 검증용 인위적 오버라이드",
    ))
    breakdown = result["growth"]["breakdown"]

    # 캡은 실제로 적용되지 않았으므로 None
    assert breakdown["cap_applied"] is None
    # 원래 캡 문구는 진단정보로 보존된다
    applied = breakdown["realistic_growth_override_applied"]
    assert applied["pre_override_cap_note"] is not None
    assert "상한" in applied["pre_override_cap_note"]

    adj = result["confidence"]["adjustments"]
    assert adj["lynch_type_cap_applied"] == 0      # 걸리지 않은 캡으로 감점하지 않는다
    assert adj["realistic_growth_overridden"] == -5  # 대신 실제 원인으로 감점


def test_override_confidence_total_unchanged_versus_stale_cap_flag():
    """
    v3.32 정정이 기존 종목의 Confidence 총점을 바꾸지 않는지 확인한다
    (감점 근거만 옮기고 크기는 동일하게 설계했다 - ROP 89 유지).
    """
    result = run_analysis(cdns_inputs(
        realistic_growth_override=0.02,
        realistic_growth_override_reason="총점 불변 검증용",
    ))
    adj = result["confidence"]["adjustments"]
    # 캡 감점(-5)이 오버라이드 감점(-5)으로 이동했을 뿐 합계 기여는 동일
    assert adj["lynch_type_cap_applied"] + adj["realistic_growth_overridden"] == -5


def test_two_stage_bisection_log_records_market_cap_not_growth():
    """
    이분탐색 로그의 implied_cap이 g_guess와 같은 값이던 복붙 버그(v3.32 수정)
    회귀 방지. 로그 전용 필드지만, 수렴이 이상할 때 원인을 찾는 유일한 단서다.
    """
    from engine.expectation_gap_engine import implied_growth_two_stage

    target_cap = 500_000
    g, log, _ = implied_growth_two_stage(target_cap, 8_000, 0.093, 12, 0.035)

    assert log, "이분탐색 로그가 비어 있다"
    for entry in log:
        assert entry["implied_cap"] != entry["g_guess"], (
            "implied_cap에 성장률 추정치가 그대로 들어가 있다(v3.32 이전 버그)"
        )
    # 수렴한 마지막 항목의 implied_cap은 목표 시총에 수렴해 있어야 한다
    assert log[-1]["implied_cap"] == pytest.approx(target_cap, rel=1e-4)


# ======================================================================
# v3.46 Phase 0 감사(2026-08-15) - P0 결함 회귀 테스트
# docs/system_audit.md FM-1~FM-4 / docs/change_plan.md C-01~C-04, C-06
# ======================================================================


def test_ebitda_zero_rejected_with_explanatory_message():
    """
    C-01: EBITDA=0이면 net_debt/EBITDA가 정의되지 않는다. 가드 이전에는 원인
    설명 없는 ZeroDivisionError가 났다(계약서 107절 Error Contract 위배).
    """
    with pytest.raises(ValueError, match="EBITDA가 0 이하"):
        cdns_inputs(ebitda=0.0)


def test_ebitda_negative_rejected_instead_of_inverting_leverage_risk():
    """
    C-01의 핵심 회귀 테스트. 가드 이전에는 EBITDA 적자 기업이 '순현금'으로
    오인되어 leverage_score가 **최저 위험(2.0)** 을 받았다 - 부실할수록 DRS가
    낮게(안전하게) 나오는 방향의 오류였다.

    실측(감사 FM-1): 순부채 +$30억 동일 조건에서
        EBITDA -$5억 -> leverage 2.0 / DRS 22.4 (경고 없음)
        EBITDA +$5억 -> leverage 20.0 / DRS 40.4
    """
    with pytest.raises(ValueError, match="정반대"):
        cdns_inputs(ebitda=-500_000_000.0)


def test_net_cash_company_still_passes_with_lowest_leverage_score():
    """
    C-01 수정이 **정상 경로를 깨지 않는지** 확인한다. 순현금(net_debt<0)이면서
    EBITDA>0인 기업은 34종목 중 13종목이 해당하며(MNDY -138.13 등) 그 종목들의
    leverage 2.0은 옳다. 가드는 분모(EBITDA)만 검사하므로 이 경로는 그대로여야 한다.
    """
    result = run_analysis(cdns_inputs(net_debt=-5_000_000_000.0))
    assert result["derived"]["net_debt_to_ebitda"] < 0
    assert result["drs"]["components"]["leverage"] == 2.0


def test_run_analysis_is_deterministic_except_timestamp():
    """
    C-04: 동일 입력 2회 실행 시 meta.analyzed_at을 제외한 전 필드가 동일해야
    한다(계약서 58·111절). 감사 시점에 실제로는 결정적이었으나 이를 고정하는
    테스트가 없어, 향후 비결정적 요소가 들어와도 잡히지 않았다.
    """
    first = run_analysis(cdns_inputs())
    second = run_analysis(cdns_inputs())

    assert first["meta"]["analyzed_at"] != second["meta"]["analyzed_at"] or True

    def strip(obj):
        trimmed = dict(obj)
        meta = dict(trimmed["meta"])
        meta.pop("analyzed_at")
        trimmed["meta"] = meta
        return json.dumps(trimmed, sort_keys=True, default=str)

    assert strip(first) == strip(second), "동일 입력인데 결과가 달라졌다(결정성 위반)"


def test_save_ledger_rejects_overwriting_different_content(tmp_path):
    """
    C-02: 같은 티커·같은 날짜에 **내용이 다른** 결과를 저장하면 이전 분석이
    흔적 없이 사라졌다(감사 FM-2 재현: Gap +0.10 -> -0.30 저장 시 파일 1개만
    남고 1차 결과 소실). 이제 예외로 막고 원본을 보존한다.
    """
    result = run_analysis(cdns_inputs())
    path = save_ledger(result, ledger_dir=str(tmp_path))

    mutated = json.loads(json.dumps(result, default=str))
    mutated["expectation_gap"] = -0.30

    with pytest.raises(FileExistsError, match="내용이 다른 ledger"):
        save_ledger(mutated, ledger_dir=str(tmp_path))

    with open(path, encoding="utf-8") as f:
        assert json.load(f)["expectation_gap"] == pytest.approx(
            result["expectation_gap"]
        ), "예외를 던졌는데도 원본이 훼손됐다"


def test_save_ledger_allows_identical_rerun(tmp_path):
    """
    C-02 설계 판단의 회귀 테스트: '같은 입력으로 재실행해 값이 같은지 확인'은
    이 프로젝트의 표준 검증 관행이다(v3.19/v3.32에서 33종목 전건 재실행).
    내용이 같으면(analyzed_at 제외) 예외 없이 통과해야 한다.
    """
    save_ledger(run_analysis(cdns_inputs()), ledger_dir=str(tmp_path))
    save_ledger(run_analysis(cdns_inputs()), ledger_dir=str(tmp_path))

    assert len(list(tmp_path.iterdir())) == 1


def test_save_ledger_overwrite_flag_allows_intentional_update(tmp_path):
    """C-02: 의도한 갱신(정성조사 결과 반영 등)은 명시적으로 허용된다."""
    result = run_analysis(cdns_inputs())
    save_ledger(result, ledger_dir=str(tmp_path))

    updated = json.loads(json.dumps(result, default=str))
    updated["expectation_gap"] = -0.30
    path = save_ledger(updated, ledger_dir=str(tmp_path), overwrite=True)

    with open(path, encoding="utf-8") as f:
        assert json.load(f)["expectation_gap"] == pytest.approx(-0.30)


def test_default_data_completeness_is_flagged_as_unmeasured():
    """
    C-06: data_completeness_pct 기본값 0.9는 Confidence에 14점을 자동 부여하는데
    ledger 34종목 전부가 이 기본값이었다 - 그 축의 판별력이 0이라는 사실이
    드러나야 한다. **점수 자체는 바꾸지 않는다**(가시화만).
    """
    result = run_analysis(cdns_inputs())
    assert any("데이터 완전성 미실측" in s for s in result["data_limitations"])
    assert result["confidence"]["adjustments"]["data_completeness"] == 14


def test_explicit_data_completeness_is_not_flagged():
    """C-06: 분석자가 실제로 값을 넣으면 경고하지 않는다."""
    result = run_analysis(cdns_inputs(data_completeness_pct=0.75))
    assert not any("데이터 완전성 미실측" in s for s in result["data_limitations"])


def test_validation_status_marks_confidence_as_uncalibrated():
    """
    C-05: 모델의 인식론적 지위가 코드에 남아 있어야 한다(계약서 40·50절).
    Confidence를 확률로 오독하는 것을 막는 유일한 기계 판독 장치다.
    """
    from engine.expectation_gap_engine import VALIDATION_STATUS

    assert "UNCALIBRATED" in VALIDATION_STATUS["confidence_score"]
    assert "HEURISTIC_MAPPING" in VALIDATION_STATUS["erp_from_drs"]


def test_default_terminal_growth_ceiling_never_binds_on_existing_ledgers():
    """
    2026-08-23 외부검증(reports/research/screening_criteria_external_2026-08-23.md):
    default_terminal_growth의 ceiling(4.5%)이 Damodaran이 통상 인용하는
    성숙기업 영구성장률 범위(2.0~3.5%)보다 100bp 높다는 게 발견됐다. 코드는
    바꾸지 않기로 했는데(v3.52 초대형주가산과 동일 원칙), 그 결정의 전제가
    "34/34 ledger에서 ceiling이 한 번도 안 걸렸다"는 사실이다. 이 사실이
    조용히 깨지면(향후 분석에서 실제로 4.5%에 도달) 결정을 재검토해야 한다.
    """
    import glob
    import json

    ceiling = 0.045
    stale_bound = 0.04  # 결정기록 #14의 재개조건("4.0%를 넘으면")과 정확히 일치
    hits = []
    for path in sorted(glob.glob("ledger/*.json")):
        d = json.load(open(path, encoding="utf-8"))
        g = d.get("discount_rate", {}).get("g_terminal")
        if g is not None and g >= stale_bound:
            hits.append((d["meta"]["ticker"], g))
    assert not hits, (
        f"g_terminal이 재개조건(4.0%) 이상인 종목이 나왔다 - "
        f"reports/research/screening_criteria_external_2026-08-23.md #6 재검토할 것: {hits}"
    )
    assert stale_bound < ceiling


def test_validation_status_documents_terminal_growth_ceiling_gap():
    """default_terminal_growth의 VALIDATION_STATUS 라벨이 실제로 등재됐는지 고정."""
    from engine.expectation_gap_engine import VALIDATION_STATUS

    label = VALIDATION_STATUS["default_terminal_growth"]
    assert "IMPLEMENTED_NOT_VALIDATED" in label
    assert "Damodaran" in label
    assert "34/34" in label


def test_implied_growth_architecture_support_does_not_overclaim_thresholds():
    """
    2026-08-23: implied_growth 비교 아키텍처는 ECONOMICALLY_SUPPORTED로
    승격됐지만(Gebhardt/Lee/Swaminathan 2001 JAR 등 3갈래 수렴), 그 지지가
    IRS의 특정 임계값(±5%p 판정밴드 등)을 정당화한다고 주장하면 v3.52가
    structural_discount_rate에서 이미 지킨 경계를 깨는 것이다.
    """
    from engine.expectation_gap_engine import VALIDATION_STATUS

    label = VALIDATION_STATUS["implied_growth"]
    assert "ECONOMICALLY_SUPPORTED" in label
    assert "정당화하지 않는다" in label


def test_scale_check_silent_on_all_existing_ledgers():
    """
    v3.46 Phase 2: 스케일 탐지 밴드는 **알려진 정상 종목에서 절대 발동하면 안
    된다**. 34종목 실측 FCF수익률 범위는 1.50%(KLAC)~17.95%(ACGL)이며 밴드는
    0.5~25%로 여유를 뒀다. 이 테스트가 깨지면 밴드가 너무 좁아진 것이다.
    """
    import glob

    from engine.expectation_gap_engine import check_scale_plausibility

    fired = []
    for path in sorted(glob.glob("ledger/*.json")):
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        ok, _ = check_scale_plausibility(
            data["derived"]["fcf0"], data["inputs"]["market_cap"]
        )
        if not ok:
            fired.append(data["meta"]["ticker"])

    assert not fired, f"정상 종목에서 스케일 경고가 오발동했다: {fired}"


@pytest.mark.parametrize("multiplier,label", [(1 / 100, "100배 과소"), (100.0, "100배 과대")])
def test_scale_check_catches_order_of_magnitude_errors(multiplier, label):
    """
    v3.46 Phase 2 핵심 회귀 테스트. 가드 이전에는 single_stage 경로에서 자릿수
    오류가 **경고 없이 실행되어 판정까지 흘러갔다**(BRO 실데이터 검증):
        100배 과소 -> Gap +7.43%p가 +96.22%p로 (매수리스트 1위감)
        100배 과대 -> 판정이 '저평가'에서 '적정가'로 뒤집힘
    100배 오류는 기저 FCF수익률과 무관하게 전부 탐지된다(실측 확인).
    """
    result = run_analysis(
        cdns_inputs(market_cap=92952756000 * multiplier, model_used="single_stage")
    )
    assert any("스케일/통화 이상 의심" in s for s in result["data_limitations"]), (
        f"{label} 오류가 탐지되지 않았다"
    )


def test_scale_check_currency_error_detected_only_above_yield_floor():
    """
    ⚠️ 이 가드의 **알려진 한계를 고정하는 테스트**(임계값을 조정해 통과시키지
    않고 사실을 그대로 박아둔다).

    통화 오류(x7.1) 탐지 여부는 그 종목의 기저 FCF수익률에 의존한다:
        CDNS(기저 1.71%) x7.1 -> 12.14%  탐지 실패 - PDD 정상값 12.94%와 겹침
        BRO (기저 6.03%) x7.1 -> 42.81%  탐지 성공
    어떤 임계값으로도 분리되지 않으므로, 이 가드는 자릿수 오류의 안전망일 뿐
    통화 오류 전반을 막지 못한다. 비USD 종목은 수작업 대조가 여전히 필요하다.
    """
    from engine.expectation_gap_engine import check_scale_plausibility

    # 기저가 낮은 종목: 통화 오류가 밴드 안에 들어와 탐지되지 않는다(한계)
    low_yield_ok, _ = check_scale_plausibility(0.0171 * 7.1 * 1e9, 1e9)
    assert low_yield_ok, "기저 1.71% 종목의 통화오류가 탐지된다면 밴드가 좁아진 것"

    # 기저가 중간 이상인 종목: 탐지된다
    mid_yield_ok, warning = check_scale_plausibility(0.0603 * 7.1 * 1e9, 1e9)
    assert not mid_yield_ok and "스케일/통화 이상 의심" in warning


def test_scale_check_never_blocks_or_autocorrects():
    """
    계약서 30절: '100배 차이나니 100으로 나눈다'는 자동보정은 금지다. 경고만
    남기고 계산값은 입력 그대로여야 한다(어느 쪽이 틀렸는지 코드는 모른다).
    """
    bad_cap = 92952756000 / 100
    result = run_analysis(cdns_inputs(market_cap=bad_cap, model_used="single_stage"))

    assert result["inputs"]["market_cap"] == bad_cap, "입력값이 자동으로 수정됐다"
    assert result["judgment"], "경고 때문에 실행이 막혔다(경고는 차단이 아니다)"


# ----------------------------------------------------------------------
# Phase 3 (v3.47) — Point-in-Time 토대
# 계약서 5.5절(미래정보 사용 금지) / 21~22절(PIT 상태 어휘와 규칙)
# ----------------------------------------------------------------------

def test_existing_analyses_are_pit_unknown_not_pit_valid():
    """
    ⚠️ 가장 중요한 PIT 테스트: 기존 34종목은 filing_date를 기록한 적이 없다.
    그 상태를 'PIT_VALID'로 취급하면 **검증하지 않은 것을 검증했다고 주장**하는
    셈이라 계약서 5.1절 위반이다. 반드시 PIT_UNKNOWN으로 떨어지고, 그 사실이
    data_limitations에 드러나야 한다.
    """
    result = run_analysis(cdns_inputs())

    assert result["meta"]["point_in_time"]["status"] == PIT_UNKNOWN
    assert any("PIT" in s or "시점" in s for s in result["data_limitations"])


def test_pit_valid_when_all_filings_precede_analysis_date():
    """filing_date <= analysis_as_of를 전부 만족하면 PIT_VALID(계약서 22절)."""
    result = run_analysis(
        cdns_inputs(
            analysis_as_of="2026-07-25",
            filing_dates_by_year={2024: "2025-02-24", 2025: "2026-02-23"},
        )
    )

    pit = result["meta"]["point_in_time"]
    assert pit["status"] == PIT_VALID
    assert pit["violations"] == []
    assert pit["analysis_as_of"] == "2026-07-25"


def test_future_filing_date_is_rejected_not_merely_warned():
    """
    계약서 5.5절: 분석 시점 이후에 공시된 실적을 쓴 결과는 무의미하다 -
    경고로 흘려보내지 않고 실행 자체를 거부한다(다른 병기 경고들과 달리
    이건 '해석의 여지'가 아니라 계산 전제의 붕괴이기 때문).
    """
    with pytest.raises(ValueError, match="미래정보"):
        run_analysis(
            cdns_inputs(
                analysis_as_of="2026-01-01",
                filing_dates_by_year={2025: "2026-02-23"},  # 분석 이후 공시
            )
        )


def test_pit_evaluation_names_the_offending_year_and_lag():
    """위반이 있으면 '어느 해가, 며칠 늦게'까지 특정돼야 추적이 가능하다."""
    inputs = cdns_inputs(
        analysis_as_of="2026-01-01",
        filing_dates_by_year={2025: "2026-02-23"},
    )
    pit = evaluate_point_in_time(inputs)

    assert pit["status"] == PIT_INVALID
    assert len(pit["violations"]) == 1
    v = pit["violations"][0]
    assert str(v["fiscal_year"]) == "2025"
    assert v["days_after_analysis"] == 53


def test_malformed_pit_date_is_rejected_at_construction():
    """
    형식 오류를 조용히 PIT_UNKNOWN으로 떨구면 '기록했다고 생각했는데 사실은
    안 된' 상태가 된다 - 즉시 거부한다.
    """
    with pytest.raises(ValueError, match="ISO 날짜"):
        cdns_inputs(analysis_as_of="2026/07/25")

    with pytest.raises(ValueError, match="ISO 날짜"):
        cdns_inputs(
            analysis_as_of="2026-07-25",
            filing_dates_by_year={2025: "23-Feb-2026"},
        )


def test_filing_dates_require_latest_fiscal_year_and_analysis_date():
    """
    최근 회계연도가 fcf0를 결정하므로 PIT 검증의 핵심이다 - 그 해가 빠진
    filing_dates_by_year는 '검증한 척'이 되므로 거부한다.
    """
    with pytest.raises(ValueError, match="최근 회계연도"):
        cdns_inputs(
            analysis_as_of="2026-07-25",
            filing_dates_by_year={2024: "2025-02-24"},  # 2025 누락
        )

    with pytest.raises(ValueError, match="analysis_as_of"):
        cdns_inputs(filing_dates_by_year={2025: "2026-02-23"})

    with pytest.raises(ValueError, match="빈 dict"):
        cdns_inputs(analysis_as_of="2026-07-25", filing_dates_by_year={})


def test_pit_fields_do_not_change_any_computed_value():
    """
    PIT는 **순수 기록·검증 경로**다(falsification_conditions/price_at_analysis와
    동일). Gap/RAR/DRS/판정 어디에도 영향을 주면 안 된다.
    """
    plain = run_analysis(cdns_inputs())
    with_pit = run_analysis(
        cdns_inputs(
            analysis_as_of="2026-07-25",
            filing_dates_by_year={2025: "2026-02-23"},
        )
    )

    for key in ("expectation_gap", "rar", "judgment", "judgment_grade"):
        assert plain[key] == with_pit[key], f"{key}가 PIT 필드 때문에 달라졌다"
    assert plain["drs"]["score"] == with_pit["drs"]["score"]
    assert plain["confidence"]["final"] == with_pit["confidence"]["final"]


# ----------------------------------------------------------------------
# Phase 3 (v3.47) — 과거 기록 자동 대조
# 감사 T-2: cross_check_prior_record()가 55개 스크립트 중 1개에서만 호출됨
# ----------------------------------------------------------------------

def _write_prior_ledger(tmp_path, result, date_str, **overrides):
    """직전 ledger를 흉내 낸 파일을 만든다(같은 티커, 더 이른 날짜)."""
    prior = json.loads(json.dumps(result, default=str))
    prior["meta"]["analyzed_at"] = f"{date_str}T00:00:00+00:00"
    prior.update(overrides)
    path = tmp_path / f"{result['meta']['ticker']}_{date_str}.json"
    path.write_text(json.dumps(prior, ensure_ascii=False), encoding="utf-8")
    return path


def test_save_ledger_auto_cross_checks_prior_record(tmp_path):
    """
    T-2의 핵심: 모든 분석 스크립트가 save_ledger()를 부르므로, 여기에 배선하면
    **대조 누락이 구조적으로 불가능**해진다. RAR 100배 사고(v3.19)를 재현한
    과거 기록을 넣고 경고가 실제로 잡히는지 확인한다.
    """
    result = run_analysis(cdns_inputs())
    _write_prior_ledger(tmp_path, result, "2026-07-01", rar=result["rar"] / 100)

    path = save_ledger(result, ledger_dir=str(tmp_path))
    saved = json.loads(open(path, encoding="utf-8").read())

    assert saved["prior_cross_check"]["prior_ledger"] == "CDNS_2026-07-01.json"
    assert any("RAR 스케일 경고" in w for w in saved["prior_cross_check"]["warnings"])


def test_cross_check_records_no_prior_when_first_analysis(tmp_path):
    """직전 기록이 없으면 '대조했고 비교 대상이 없었다'가 기록돼야 한다 -
    경고 0건과 '아예 대조 안 함'은 다른 상태다."""
    path = save_ledger(run_analysis(cdns_inputs()), ledger_dir=str(tmp_path))
    saved = json.loads(open(path, encoding="utf-8").read())

    assert saved["prior_cross_check"]["checked"] is True
    assert saved["prior_cross_check"]["prior_ledger"] is None
    assert saved["prior_cross_check"]["warnings"] == []


def test_cross_check_never_blocks_saving(tmp_path):
    """
    대조는 **조언이지 차단이 아니다**. 과거 파일이 깨져 있어도 저장은 반드시
    성공해야 한다 - 대조 실패로 새 분석이 유실되는 게 더 나쁜 결과다.
    """
    (tmp_path / "CDNS_2026-07-01.json").write_text("{ 깨진 JSON", encoding="utf-8")

    path = save_ledger(run_analysis(cdns_inputs()), ledger_dir=str(tmp_path))
    assert json.loads(open(path, encoding="utf-8").read())["judgment"]


def test_cross_check_can_be_disabled_for_repo_independent_tests(tmp_path):
    """
    골든테스트가 저장소의 다른 ledger 유무에 따라 흔들리면 안 된다 -
    CLAUDE.md v3.32가 이 배선을 미룬 이유가 정확히 그 부작용이었으므로
    끄는 경로를 명시적으로 둔다.
    """
    result = run_analysis(cdns_inputs())
    _write_prior_ledger(tmp_path, result, "2026-07-01", rar=result["rar"] / 100)

    path = save_ledger(result, ledger_dir=str(tmp_path), cross_check=False)
    saved = json.loads(open(path, encoding="utf-8").read())

    assert saved["prior_cross_check"]["checked"] is False
    assert saved["prior_cross_check"]["warnings"] == []


def test_cross_check_does_not_alter_official_numbers(tmp_path):
    """
    병기 원칙(A-6): 대조 경고가 떠도 판정·Gap·RAR은 그대로여야 한다.
    is_insurer/sbc_cross_check와 동일하게 '병기, 자동판정 안 함'.
    """
    result = run_analysis(cdns_inputs())
    _write_prior_ledger(tmp_path, result, "2026-07-01", rar=result["rar"] / 100)

    path = save_ledger(result, ledger_dir=str(tmp_path))
    saved = json.loads(open(path, encoding="utf-8").read())

    assert saved["prior_cross_check"]["warnings"], "테스트 전제(경고 발생)가 깨졌다"
    for key in ("expectation_gap", "rar", "judgment"):
        assert saved[key] == result[key]


# ── v3.67: 규모 조건부 성장상한 (2026-08-23 사용자 승인) ────────────────
def test_size_cap_does_not_replace_lynch_cap_but_takes_the_stricter():
    """
    린치 캡을 **대체하지 않고 함께 적용**한다(둘 중 엄격한 쪽). 대체하면
    린치 캡이 더 낮은 종목의 동작이 조용히 느슨해진다.
    """
    import glob
    import json

    from engine.pipeline import run_analysis
    from engine.thesis_monitor import inputs_from_ledger

    # BRO: stalwart 12% 캡이 규모캡(3000-4500 -> 명목 23.0%)보다 엄격
    d = json.load(open(glob.glob("ledger/BRO_*.json")[-1], encoding="utf-8"))
    r = run_analysis(inputs_from_ledger(d))
    assert r["growth"]["realistic_growth"] == pytest.approx(0.12, abs=1e-9)
    assert "size_conditioned_cap_applied" not in r["growth"]["breakdown"]


def test_size_cap_skipped_without_fx_rate_rather_than_guessing():
    """
    외화 표시인데 환율이 없으면 **적용하지 않고 그 사실을 남긴다.** 임의
    환율을 지어내면 규모 구간이 잘못 배정돼 상한이 조용히 틀어진다
    (이 프로젝트의 추측 금지 원칙).
    """
    import dataclasses
    import glob
    import json

    from engine.pipeline import run_analysis
    from engine.thesis_monitor import inputs_from_ledger

    d = json.load(open(glob.glob("ledger/PDD_*.json")[-1], encoding="utf-8"))
    inp = inputs_from_ledger(d)
    assert inp.currency == "CNY"
    no_fx = dataclasses.replace(inp, usd_fx_rate=None)
    r = run_analysis(no_fx)
    assert "size_conditioned_cap_applied" not in r["growth"]["breakdown"]
    assert any("규모 조건부 상한 미적용" in m for m in r["data_limitations"])


def test_size_cap_applies_with_fx_rate_and_is_recorded():
    """PDD - 이 연구의 핵심 사례. 환율이 있으면 적용되고 근거가 기록돼야 한다."""
    import glob
    import json

    from engine.pipeline import run_analysis
    from engine.thesis_monitor import inputs_from_ledger

    d = json.load(open(glob.glob("ledger/PDD_*.json")[-1], encoding="utf-8"))
    inp = inputs_from_ledger(d)
    assert inp.usd_fx_rate == pytest.approx(7.2)
    r = run_analysis(inp)
    sc = r["growth"]["breakdown"]["size_conditioned_cap_applied"]
    assert sc["size_class"] == "25000+"
    assert r["growth"]["realistic_growth"] == pytest.approx(0.1787, abs=1e-4)
    assert r["growth"]["breakdown"]["realistic_growth_before_size_cap"] == pytest.approx(0.25)
    assert any("규모 조건부 상한 적용" in m for m in r["data_limitations"])


def test_realistic_growth_override_bypasses_size_cap():
    """
    오버라이드는 분석자가 근거를 갖고 직접 넣은 값이므로 규모 캡도 우회한다
    (v3.28이 CAGR·린치캡을 우회하게 만든 것과 같은 이유). ROP가 실사례다.
    """
    import glob
    import json

    from engine.pipeline import run_analysis
    from engine.thesis_monitor import inputs_from_ledger

    d = json.load(open(glob.glob("ledger/ROP_*.json")[-1], encoding="utf-8"))
    inp = inputs_from_ledger(d)
    assert inp.realistic_growth_override is not None
    r = run_analysis(inp)
    assert r["growth"]["realistic_growth"] == pytest.approx(inp.realistic_growth_override)
    assert "size_conditioned_cap_applied" not in r["growth"]["breakdown"]


# v3.67 승인(2026-08-23) 당시 34종목 코퍼스에서 규모캡이 걸린 3종목 -
# 이 셋은 반드시 계속 걸려야 한다(회귀 감시). v3.67 **이후** 신규 분석된
# 티커가 이 상시활성 메커니즘(opt-in 아님 - fast_grower + 대형 시총이면
# 항상 평가된다)에 새로 걸리는 것은 승인범위 이탈이 아니라 정상 동작이다 -
# FIX(2026-09-02, 시총 $54.67B·fast_grower)가 첫 사례. 새로 걸리는 티커가
# 생기면 여기 추가하고 그 근거를 CLAUDE.md에 남길 것(BSX 거짓탈락 등과
# 동일한 "알려진 확장" 등록 패턴).
APPROVED_SIZE_CAPPED_TICKERS = {"PDD", "PGR", "SE"}
KNOWN_ADDITIONAL_SIZE_CAPPED_TICKERS = {"FIX"}  # 2026-09-02, v3.67 이후 신규분석


def test_approved_three_tickers_reproduce_and_others_unchanged():
    """
    2026-08-23 승인 범위(PDD·PGR·SE)가 계속 유효한지, 그리고 그 외에 규모캡이
    걸리는 티커는 전부 `KNOWN_ADDITIONAL_SIZE_CAPPED_TICKERS`에 명시적으로
    등록된 것뿐인지 고정한다. 등록되지 않은 새 티커가 걸리면(=이 메커니즘이
    의도치 않게 더 넓게 발동하면) 이 테스트가 실패해 알려준다.
    """
    import glob
    import json

    from engine.pipeline import run_analysis
    from engine.thesis_monitor import inputs_from_ledger

    applied = set()
    for p in sorted(glob.glob("ledger/*.json")):
        d = json.load(open(p, encoding="utf-8"))
        r = run_analysis(inputs_from_ledger(d))
        if "size_conditioned_cap_applied" in r["growth"]["breakdown"]:
            applied.add(d["meta"]["ticker"])
    allowed = APPROVED_SIZE_CAPPED_TICKERS | KNOWN_ADDITIONAL_SIZE_CAPPED_TICKERS
    assert APPROVED_SIZE_CAPPED_TICKERS <= applied, (
        f"원 승인 3종목 중 일부가 더 이상 안 걸림: {APPROVED_SIZE_CAPPED_TICKERS - applied}"
    )
    assert applied <= allowed, f"등록되지 않은 신규 발동: {applied - allowed}"
