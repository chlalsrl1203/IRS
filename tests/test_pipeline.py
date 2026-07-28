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
