"""
ETF 엔진 테스트 (v3.33, 2026-08-06)

골든 케이스는 합성 숫자가 아니라 2026-08-06에 실제로 조사한 값을 쓴다
(회사 엔진 테스트가 CDNS 실데이터를 고정한 것과 같은 방식) - 특히 IWM은
이 엔진의 설계 근거가 된 실제 사건이므로 반드시 회귀 테스트로 고정한다.
"""

import json
import math

import pytest

from engine.etf_engine import (
    PE_DIVERGENCE_WARNING_THRESHOLD,
    breadth_score,
    concentration_score,
    earnings_yield,
    etf_risk_score,
    evaluate_valuation_by_source,
    expense_drag,
    fed_model_spread,
    growth_anchor_cross_check,
    growth_sensitivity,
    holdings_overlap,
    implied_growth_from_pe,
    net_expected_growth,
    pe_source_divergence,
    realized_eps_growth,
    required_growth_thresholds,
    to_nominal_growth,
)
from engine.etf_pipeline import (
    ETFInputs,
    compare_etfs,
    format_overlap_table,
    portfolio_overlap_report,
    run_etf_analysis,
    save_etf_ledger,
)


# ----------------------------------------------------------------------
# 실측 골든 데이터 (2026-08-06 조사)
# ----------------------------------------------------------------------

def voo_inputs(**overrides):
    base = dict(
        ticker="VOO",
        name="Vanguard S&P 500 ETF",
        tracks="S&P 500",
        pe_by_source={"stockanalysis(trailing)": 27.53, "FactSet(forward)": 19.6},
        expense_ratio=0.0003,
        n_holdings=505,
        top10_weight=0.37,
        risk_free_rate=0.0461,
        expected_earnings_growth=0.08,
        expected_earnings_growth_basis=(
            "S&P500 장기 명목 EPS 성장률 근사(과거 수십년 실적 7~8%대) [추정치]"
        ),
        dividend_yield=0.0104,
        return_1y=0.2341,
    )
    base.update(overrides)
    return ETFInputs(**base)


# ----------------------------------------------------------------------
# 순수 함수
# ----------------------------------------------------------------------

def test_earnings_yield_is_pe_inverse():
    assert earnings_yield(20.0) == pytest.approx(0.05)
    assert earnings_yield(19.6) == pytest.approx(1 / 19.6)


def test_earnings_yield_rejects_nonpositive_pe():
    with pytest.raises(ValueError, match="Model Not Applicable"):
        earnings_yield(0)
    with pytest.raises(ValueError, match="Model Not Applicable"):
        earnings_yield(-12.0)


def test_implied_growth_matches_gordon_identity():
    """g = (r - y)/(1 + y) 를 직접 검산한다."""
    pe, r = 20.0, 0.09
    y = 1 / pe
    assert implied_growth_from_pe(pe, r) == pytest.approx((r - y) / (1 + y))


def test_implied_growth_rises_as_pe_rises():
    """비쌀수록(P/E가 클수록) 정당화에 더 높은 성장이 필요하다."""
    r = 0.09
    assert implied_growth_from_pe(30, r) > implied_growth_from_pe(20, r)


def test_expense_drag_compounds():
    # 0.03% 10년 -> 약 0.30%
    assert expense_drag(0.0003, 10) == pytest.approx(1 - 0.9997 ** 10)
    # 고비용 ETF의 10년 누적은 Gap 추정치와 맞먹는 크기가 된다
    assert expense_drag(0.0075, 10) > 0.07


def test_expense_drag_rejects_bad_units():
    with pytest.raises(ValueError):
        expense_drag(1.5, 10)
    with pytest.raises(ValueError):
        expense_drag(0.0003, 0)


def test_score_buckets_are_monotonic():
    """위험이 커질수록 점수가 단조증가해야 한다(구간표 정합성)."""
    assert concentration_score(0.10) < concentration_score(0.45) < concentration_score(0.90)
    # 보유종목은 적을수록 위험 -> 역방향
    assert breadth_score(2000) < breadth_score(300) < breadth_score(30)


def test_etf_risk_score_uses_drs_scale():
    """ERS는 DRS와 같은 0~100 스케일이어야 erp_from_drs를 재사용할 수 있다."""
    ers = etf_risk_score(0.37, 505, 0.0)
    assert 0 <= ers["score"] <= 100
    assert ers["excluded"] == ["earnings_quality"]

    full = etf_risk_score(0.37, 505, 0.0, pct_unprofitable=0.02)
    assert full["excluded"] == []
    assert len(full["components"]) == 4
    # v3.34: 보수율은 위험점수가 아니므로 ERS 구성에 없어야 한다
    assert "cost" not in full["components"]


def test_fed_model_is_reported_but_flagged_as_contested():
    fed = fed_model_spread(19.6, 0.0461)
    assert fed["spread"] == pytest.approx(1 / 19.6 - 0.0461)
    assert "논쟁적" in fed["caveat"]


# ----------------------------------------------------------------------
# ⭐ IWM 사건 - 이 엔진의 설계 근거
# ----------------------------------------------------------------------

def test_iwm_pe_divergence_is_detected():
    """
    2026-08-06 실측: stockanalysis.com 20.07x(트레일링) vs Goldman Sachs
    26x(forward). 상대괴리 29.5%로 임계값(20%)을 넘어 경고가 떠야 한다.
    """
    d = pe_source_divergence({"stockanalysis(trailing)": 20.07, "GoldmanSachs(forward)": 26.0})
    assert d["min"] == 20.07
    assert d["max"] == 26.0
    assert d["spread_relative"] == pytest.approx((26.0 - 20.07) / 20.07)
    assert d["spread_relative"] > PE_DIVERGENCE_WARNING_THRESHOLD
    assert d["warning"] is not None
    assert "IWM" in d["warning"]


def test_iwm_judgment_actually_flips_across_sources():
    """
    핵심 회귀 테스트: IWM은 출처에 따라 판정이 실제로 뒤집힌다.
    이 성질이 사라지면 엔진이 IWM 사건을 더 이상 잡지 못한다는 뜻이다.
    """
    r = 0.09
    v = evaluate_valuation_by_source(
        {"trailing": 20.07, "forward": 26.0},
        expected_earnings_growth=0.09,
        r=r,
    )
    assert v["judgment_flipped_across_sources"] is True
    assert v["consensus_judgment"] is None
    assert len(v["judgments_seen"]) > 1
    # 싼 쪽 출처가 더 큰(유리한) Gap을 낸다
    assert v["by_source"]["trailing"]["gap"] > v["by_source"]["forward"]["gap"]


def test_single_source_gets_explicit_warning():
    """출처가 1개면 괴리를 검증할 방법 자체가 없으므로 경고를 붙인다."""
    d = pe_source_divergence({"only": 20.0})
    assert d["spread_relative"] == 0.0
    assert d["warning"] is not None
    assert "단일 출처" in d["warning"]


def test_agreeing_sources_produce_no_warning_and_consensus():
    d = pe_source_divergence({"a": 19.5, "b": 19.6})
    assert d["warning"] is None
    v = evaluate_valuation_by_source({"a": 19.5, "b": 19.6}, 0.08, 0.09)
    assert v["judgment_flipped_across_sources"] is False
    assert v["consensus_judgment"] is not None


def test_pe_divergence_rejects_bad_input():
    with pytest.raises(ValueError):
        pe_source_divergence({})
    with pytest.raises(ValueError):
        pe_source_divergence({"bad": -3.0})


# ----------------------------------------------------------------------
# 판정 규칙 재사용 (v3.32 단일화가 ETF에도 적용되는지)
# ----------------------------------------------------------------------

def test_etf_judgment_uses_the_same_shared_rule_as_companies():
    """
    ETF 판정이 회사 엔진과 **같은 함수**를 쓰는지 확인한다. v3.32에서 판정
    규칙 사본 4개가 이미 어긋나 있던 사고를 겪었으므로, 새 분석 유형이
    또 다른 사본을 만들지 않았는지 테스트로 고정한다.
    """
    from engine.expectation_gap_engine import judgment_from_gap

    v = evaluate_valuation_by_source({"s": 20.0}, 0.09, 0.09)
    entry = v["by_source"]["s"]
    assert entry["judgment"] == judgment_from_gap(entry["gap"])


# ----------------------------------------------------------------------
# 파이프라인 가드
# ----------------------------------------------------------------------

def test_growth_basis_is_mandatory():
    with pytest.raises(ValueError, match="expected_earnings_growth_basis"):
        voo_inputs(expected_earnings_growth_basis="   ")


def test_pe_by_source_is_mandatory():
    with pytest.raises(ValueError, match="pe_by_source"):
        voo_inputs(pe_by_source={})


def test_expense_ratio_percent_mistake_is_caught():
    """0.03%를 0.03(=3%)으로 잘못 넣는 단위 실수를 막는다(v3.19 100배 사고 계열)."""
    with pytest.raises(ValueError, match="퍼센트 숫자를 소수 자리"):
        voo_inputs(expense_ratio=0.03)


def test_bad_weights_rejected():
    with pytest.raises(ValueError):
        voo_inputs(top10_weight=1.5)
    with pytest.raises(ValueError):
        voo_inputs(n_holdings=0)


# ----------------------------------------------------------------------
# 전체 실행
# ----------------------------------------------------------------------

def test_run_etf_analysis_produces_full_record():
    result = run_etf_analysis(voo_inputs())
    assert result["meta"]["ticker"] == "VOO"
    assert result["meta"]["analysis_type"] == "etf"
    assert result["discount_rate"]["r"] > result["discount_rate"]["rf"]
    assert set(result["valuation"]["by_source"]) == {
        "stockanalysis(trailing)", "FactSet(forward)"
    }
    assert result["cost"]["cumulative_drag"] > 0
    # 입력이 전부 보존돼 재현 가능해야 한다
    assert result["inputs"]["expected_earnings_growth"] == 0.08


def test_engine_version_is_shared_not_duplicated():
    from engine.expectation_gap_engine import ENGINE_VERSION

    result = run_etf_analysis(voo_inputs())
    assert result["meta"]["engine_version"] == ENGINE_VERSION


def test_high_expense_ratio_raises_limitation():
    result = run_etf_analysis(voo_inputs(expense_ratio=0.0075))
    assert any("보수율 부담" in x for x in result["data_limitations"])


def test_missing_unprofitable_pct_is_disclosed_not_silent():
    result = run_etf_analysis(voo_inputs())
    assert "earnings_quality" in result["ers"]["excluded"]
    assert any("ERS 항목 제외" in x for x in result["data_limitations"])


def iwm_inputs(**overrides):
    """IWM 실측 골든 케이스(2026-08-06)."""
    base = dict(
        ticker="IWM",
        name="iShares Russell 2000 ETF",
        tracks="Russell 2000",
        pe_by_source={"stockanalysis(trailing)": 20.07, "GoldmanSachs(forward)": 26.0},
        expected_earnings_growth=0.11,
        expected_earnings_growth_basis=(
            "소형주 이익성장 전망치 17~18%(2026-08 컨센서스)를 '증명되지 않은 "
            "전망'으로 보고 보수적으로 할인한 값 [추정치]"
        ),
    )
    base.update(overrides)
    return voo_inputs(**base)


def test_flipped_judgment_surfaces_in_data_limitations():
    result = run_etf_analysis(iwm_inputs())
    assert result["valuation"]["judgment_flipped_across_sources"] is True
    assert any("판정 불일치" in x for x in result["data_limitations"])


def test_high_divergence_without_flip_still_warns():
    """
    ⚠️ 2026-08-06 테스트에서 발견한 성질의 회귀 고정:
    P/E 괴리는 Gap에 일정한 폭을 만들지만, 그 폭이 ±5%p 경계를 가로지르는지는
    r·성장률이 어디 놓이느냐에 달렸다. 같은 IWM 데이터가 성장률 9%에서는
    판정이 일치하고 11%에서는 갈린다. **일치했다고 안전한 게 아니므로**
    괴리가 큰데 판정만 우연히 같은 경우도 반드시 경고해야 한다.
    """
    result = run_etf_analysis(iwm_inputs(expected_earnings_growth=0.09))
    assert result["valuation"]["judgment_flipped_across_sources"] is False
    assert any("판정 우연 일치 주의" in x for x in result["data_limitations"])
    # 원인이 되는 P/E 괴리 경고는 별도로 항상 남아 있어야 한다
    assert any("P/E 출처 괴리" in x for x in result["data_limitations"])


def test_compare_etfs_pushes_flipped_ones_back():
    """
    판정이 갈린 ETF는 Gap이 좋아 보여도 순위를 신뢰할 수 없으므로 뒤로 간다.
    IWM이 정확히 이 경우(한 출처로는 최상위, 다른 출처로는 최하위).
    """
    clean = run_etf_analysis(voo_inputs())
    flipped = run_etf_analysis(iwm_inputs())
    assert flipped["valuation"]["judgment_flipped_across_sources"] is True
    ordered = compare_etfs([flipped, clean])
    assert ordered[0]["meta"]["ticker"] == "VOO"
    assert ordered[-1]["meta"]["ticker"] == "IWM"


def test_save_etf_ledger_roundtrip(tmp_path):
    result = run_etf_analysis(voo_inputs())
    path = save_etf_ledger(result, ledger_dir=str(tmp_path))
    assert path.endswith(".json")
    reloaded = json.load(open(path, encoding="utf-8"))
    assert reloaded["meta"]["ticker"] == "VOO"
    assert reloaded["valuation"]["by_source"]


def test_ledger_dir_is_separate_from_company_ledgers():
    """
    ETF ledger가 회사 ledger 디렉터리를 오염시키지 않아야 한다
    (test_ledger_integrity가 회사 스키마를 가정하고 전수 파싱하므로).
    """
    import inspect

    from engine.etf_pipeline import save_etf_ledger as f

    default = inspect.signature(f).parameters["ledger_dir"].default
    assert default != "ledger"
    assert default == "ledger_etf"


# ----------------------------------------------------------------------
# v3.34 — 주관적 성장률 지배 문제 대응
# ----------------------------------------------------------------------

def test_required_growth_is_independent_of_analyst_assumption():
    """
    ⭐ v3.34의 존재 이유: breakeven(시장이 요구하는 성장률)은 P/E와 r에서만
    나오므로 분석자가 성장률을 어떻게 잡든 **변하지 않는다**. 그래서 Gap과
    달리 ETF간 객관적 비교가 가능하다.
    """
    a = required_growth_thresholds(20.0, 0.09)
    b = required_growth_thresholds(20.0, 0.09)
    assert a == b
    assert a["breakeven"] == pytest.approx(implied_growth_from_pe(20.0, 0.09))
    # 저평가 판정을 받으려면 breakeven보다 정확히 밴드(5%p)만큼 높아야 한다
    assert a["for_undervalued"] == pytest.approx(a["breakeven"] + 0.05)
    assert a["for_overvalued"] == pytest.approx(a["breakeven"] - 0.05)


def test_gap_is_one_to_one_sensitive_to_growth_assumption():
    """
    2026-08-06 진단으로 확인한 성질을 회귀로 고정한다: implied_growth는
    expected_earnings_growth와 독립이므로 Gap 민감도는 정확히 1:1이다.
    이 성질이 있는 한 성장률 가정은 판정을 그대로 좌우한다.
    """
    r, pe = 0.09, 20.0
    ig = implied_growth_from_pe(pe, r)
    g1 = evaluate_valuation_by_source({"s": pe}, 0.08, r)["by_source"]["s"]
    g2 = evaluate_valuation_by_source({"s": pe}, 0.10, r)["by_source"]["s"]
    assert g1["implied_growth"] == pytest.approx(ig)
    assert g2["implied_growth"] == pytest.approx(ig)
    assert (g2["gap"] - g1["gap"]) == pytest.approx(0.02)


def test_growth_sensitivity_flags_fragile_judgment():
    """성장률 ±2%p 안에서 판정이 갈리면 robust=False여야 한다."""
    r, pe = 0.09, 20.0
    ig = implied_growth_from_pe(pe, r)
    # 정확히 저평가 경계(+5%p)에 걸치도록 성장률을 잡으면 밴드가 경계를 가로지른다
    fragile = growth_sensitivity(pe, r, ig + 0.05, uncertainty=0.02)
    assert fragile["robust"] is False
    # 경계에서 충분히 먼 값이면 robust
    solid = growth_sensitivity(pe, r, ig + 0.20, uncertainty=0.02)
    assert solid["robust"] is True


def test_expense_ratio_is_deducted_from_growth_not_scored_as_risk():
    """
    v3.34 설계 정정: 보수율은 (a) ERS에서 빠지고 (b) 성장률에서 차감된다.
    같은 ETF에서 보수율만 올리면 ERS는 그대로이고 Gap만 줄어야 한다.
    """
    cheap = run_etf_analysis(voo_inputs(expense_ratio=0.0003))
    pricey = run_etf_analysis(voo_inputs(expense_ratio=0.0095))

    # 위험점수는 보수율과 무관해야 한다(이중 반영 방지)
    assert cheap["ers"]["score"] == pricey["ers"]["score"]
    # 순 기대성장률은 보수율만큼 정확히 낮아야 한다
    assert net_expected_growth(0.08, 0.0095) == pytest.approx(0.08 - 0.0095)
    assert pricey["growth"]["net_expected_growth"] < cheap["growth"]["net_expected_growth"]
    # 따라서 Gap도 비싼 쪽이 나쁘다
    assert pricey["valuation"]["gap_min"] < cheap["valuation"]["gap_min"]


def test_fragile_growth_surfaces_in_data_limitations_and_demotes_ranking():
    """성장률 취약 ETF는 경고가 붙고 compare_etfs에서 뒤로 밀려야 한다."""
    solid = run_etf_analysis(voo_inputs())
    # 저평가 경계에 딱 걸치는 성장률을 만들어 취약 케이스를 구성
    r_probe = run_etf_analysis(voo_inputs())["discount_rate"]["r"]
    ig = implied_growth_from_pe(27.53, r_probe)
    fragile = run_etf_analysis(voo_inputs(
        ticker="FRAG",
        expected_earnings_growth=ig + 0.05 + 0.0003,  # 보수율 차감 후 경계에 걸림
        expected_earnings_growth_basis="취약성 검증용 인위적 값 [테스트]",
    ))
    assert fragile["growth"]["sensitivity"]["robust"] is False
    assert any("성장률 가정 취약" in x for x in fragile["data_limitations"])

    ordered = compare_etfs([fragile, solid])
    assert ordered[-1]["meta"]["ticker"] == "FRAG"


def test_required_growth_recorded_per_source_in_ledger():
    """ledger에 객관적 기준선이 출처별로 남아야 재현·대조가 가능하다."""
    result = run_etf_analysis(voo_inputs())
    for src, entry in result["valuation"]["by_source"].items():
        assert "required_growth" in entry
        assert entry["required_growth"]["breakeven"] == pytest.approx(
            entry["implied_growth"])


# ----------------------------------------------------------------------
# v3.35 — 판정 밴드 단일화 + 성장률 실적 앵커(방향 A)
# ----------------------------------------------------------------------

def test_judgment_band_is_single_source():
    """
    ⭐ v3.35 회귀 고정: "저평가가 되려면 필요한 성장률"은 정의상 판정 경계와
    같아야 한다. v3.34에서 required_growth_thresholds가 band=0.05를 독립
    하드코딩해 judgment_from_gap의 경계와 중복돼 있었다(v3.32에서 규칙은
    단일화했지만 경계값 숫자는 놓쳤던 것).

    한쪽만 바뀌면 엔진이 "저평가라 부르려면 X% 필요"라고 안내해놓고 정작
    그 X%에서 저평가 판정을 안 내리는 자기모순이 생긴다.
    """
    from engine.expectation_gap_engine import JUDGMENT_BAND, judgment_from_gap

    r, pe = 0.09, 20.0
    req = required_growth_thresholds(pe, r)
    assert req["band_used"] == JUDGMENT_BAND

    # 안내된 성장률을 그대로 믿으면 실제로 저평가 판정이 나와야 한다
    ig = req["breakeven"]
    assert judgment_from_gap(req["for_undervalued"] - ig) == "저평가 가능성"
    assert judgment_from_gap(req["for_overvalued"] - ig) == "과대평가 가능성"
    # breakeven 자체는 중립이어야 한다
    assert judgment_from_gap(req["breakeven"] - ig) == "적정가/경계선"


def test_realized_eps_growth_computes_cagr_from_index_earnings():
    """지수 EPS 실적에서 CAGR을 계산한다(방향 A의 계산부)."""
    eps = {2020: 100.0, 2021: 110.0, 2022: 121.0, 2023: 133.1, 2024: 146.41,
           2025: 161.051}
    out = realized_eps_growth(eps)
    assert out["base_year"] == 2020
    assert out["end_year"] == 2025
    assert out["span_years"] == 5
    assert out["cagr"] == pytest.approx(0.10)  # 정확히 연 10% 복리 시계열


def test_realized_eps_growth_respects_lookback_and_reuses_cagr_guard():
    eps = {2015: 20.0, 2020: 100.0, 2021: 110.0, 2022: 121.0,
           2023: 133.1, 2024: 146.41, 2025: 161.051}
    # lookback=5면 2020~2025 구간만 봐서 정확히 10%
    assert realized_eps_growth(eps, lookback=5)["cagr"] == pytest.approx(0.10)
    # 전체 구간(2015 기준)은 저점 기저효과로 더 높게 나온다 - 기준연도 선택이
    # 성장률을 통째로 바꾼다는 회사 엔진의 교훈(cagr_base_year_override)과 동일
    assert realized_eps_growth(eps)["cagr"] > 0.10

    # 시작값이 음수면 회사 엔진의 _cagr 가드가 복소수 반환을 막아야 한다
    with pytest.raises(ValueError, match="CAGR 계산 불가"):
        realized_eps_growth({2020: -10.0, 2025: 100.0})
    with pytest.raises(ValueError):
        realized_eps_growth({2025: 100.0})  # 1개 연도로는 계산 불가
    with pytest.raises(ValueError):
        realized_eps_growth({2024: 100.0, 2025: 110.0}, lookback=5)  # 데이터 부족


def test_growth_anchor_warns_when_assumption_departs_from_realized():
    """
    분석자 가정이 실적 CAGR에서 크게 벗어나면 경고한다 - 자동으로 덮어쓰지는
    않는다(insurer_cross_check와 같은 '병기, 자동판정 안 함' 원칙).
    """
    realized = realized_eps_growth({2020: 100.0, 2025: 161.051})  # 10%
    near = growth_anchor_cross_check(0.11, realized)
    assert near["within_tolerance"] is True
    assert near["warning"] is None

    far = growth_anchor_cross_check(0.18, realized)
    assert far["within_tolerance"] is False
    assert "성장률 앵커 괴리" in far["warning"]
    assert far["deviation"] == pytest.approx(0.08)
    # 가정값을 덮어쓰지 않았음을 확인(병기만 한다)
    assert far["assumed"] == 0.18


def test_missing_anchor_is_disclosed_not_silent():
    """실적 앵커가 없으면 그 사실이 data_limitations에 남아야 한다."""
    result = run_etf_analysis(voo_inputs())
    assert result["growth"]["basis_type"] == "analyst_estimate"
    assert result["growth"]["anchor_cross_check"] is None
    assert any("성장률 앵커 없음" in x for x in result["data_limitations"])


def test_anchored_etf_is_labelled_and_cross_checked():
    """실적 시계열을 넣으면 basis_type이 바뀌고 대조 결과가 기록된다."""
    result = run_etf_analysis(voo_inputs(
        realized_eps_by_year={2020: 100.0, 2021: 110.0, 2022: 121.0,
                              2023: 133.1, 2024: 146.41, 2025: 161.051},
        realized_eps_basis="nominal",
    ))
    assert result["growth"]["basis_type"] == "observed_anchored"
    cc = result["growth"]["anchor_cross_check"]
    assert cc["realized"]["cagr"] == pytest.approx(0.10)
    # 가정 8% vs 실적 10% -> 2%p 차이로 허용폭(3%p) 안
    assert cc["within_tolerance"] is True
    assert not any("성장률 앵커 없음" in x for x in result["data_limitations"])


def test_real_vs_nominal_eps_unit_trap_is_guarded():
    """
    ⚠️ v3.35 단위 가드(RAR 100배 사고와 같은 계열): 공개 지수 EPS 시계열은
    실질(인플레 조정)인 경우가 흔한데(multpl.com S&P500 EPS가 "constant
    dollars" 기준) 기대성장률은 명목이다. 그대로 비교하면 인플레이션율만큼
    (연 2~3%p) 조용히 어긋나 ±5%p 판정 밴드를 넘길 수 있다.
    """
    eps = {2015: 122.17, 2020: 120.68, 2025: 247.98}

    # 단위를 안 밝히면 거부
    with pytest.raises(ValueError, match="realized_eps_basis"):
        voo_inputs(realized_eps_by_year=eps)
    # real이라고 했으면 인플레이션 가정을 반드시 받아야 한다
    with pytest.raises(ValueError, match="inflation_for_conversion"):
        voo_inputs(realized_eps_by_year=eps, realized_eps_basis="real")

    # 정확식: (1+real)(1+infl)-1
    assert to_nominal_growth(0.05, 0.025) == pytest.approx(1.05 * 1.025 - 1)
    # 근사식(단순 덧셈)과 다르다는 점을 고정 - 크기가 작아 보여도 누적되면 갈린다
    assert to_nominal_growth(0.05, 0.025) > 0.075


def test_real_eps_is_converted_to_nominal_before_comparison():
    """real 기준 EPS는 명목으로 환산된 뒤에야 명목 가정과 비교돼야 한다."""
    eps = {2020: 100.0, 2025: 127.628}  # 실질 CAGR 정확히 5%
    result = run_etf_analysis(voo_inputs(
        realized_eps_by_year=eps,
        realized_eps_basis="real",
        inflation_for_conversion=0.025,
    ))
    realized = result["growth"]["anchor_cross_check"]["realized"]
    assert realized["basis"] == "real"
    assert realized["cagr_real"] == pytest.approx(0.05, abs=1e-4)
    assert realized["cagr"] == pytest.approx(1.05 * 1.025 - 1, abs=1e-4)
    assert any("EPS 단위 환산" in x for x in result["data_limitations"])


# ----------------------------------------------------------------------
# v3.36 — ETF간 중복노출(함께 보유할 때의 위험)
# ----------------------------------------------------------------------

# 2026-08-07 stockanalysis.com 실측 top10
VOO_TOP10 = {"NVDA": 0.0750, "AAPL": 0.0658, "MSFT": 0.0429, "AMZN": 0.0361,
             "GOOGL": 0.0324, "AVGO": 0.0277, "GOOG": 0.0258, "MU": 0.0201,
             "META": 0.0191, "TSLA": 0.0183}
QQQ_TOP10 = {"AAPL": 0.0815, "NVDA": 0.0786, "MSFT": 0.0558, "MU": 0.0453,
             "AMZN": 0.0422, "AMD": 0.0364, "GOOGL": 0.0323, "AVGO": 0.0306,
             "GOOG": 0.0303, "META": 0.0266}
XLK_TOP10 = {"NVDA": 0.1391, "AAPL": 0.1298, "MSFT": 0.0988, "AVGO": 0.0527,
             "AMD": 0.0423, "MU": 0.0366, "CSCO": 0.0320, "INTC": 0.0298,
             "AMAT": 0.0281, "LRCX": 0.0256}


def test_overlap_uses_min_weight_and_is_symmetric():
    """공통 종목별 min(비중) 합 = 두 펀드가 공유하는 최소 공통 노출."""
    a = {"X": 0.10, "Y": 0.05, "Z": 0.03}
    b = {"X": 0.04, "Y": 0.09, "W": 0.20}
    ov = holdings_overlap(a, b)
    assert ov["common_tickers"] == ["X", "Y"]
    assert ov["shared_weight"] == pytest.approx(0.04 + 0.05)
    # 대칭이어야 한다
    assert holdings_overlap(b, a)["shared_weight"] == pytest.approx(ov["shared_weight"])
    # top10 기준이라 하한임을 명시해야 한다
    assert ov["is_lower_bound"] is True


def test_overlap_rejects_percent_numbers():
    """비중을 퍼센트(7.5)로 넣는 단위 실수를 막는다."""
    with pytest.raises(ValueError, match="0~1 소수"):
        holdings_overlap({"X": 7.5}, {"X": 0.05})


def test_real_megacap_triple_counting_is_detected():
    """
    ⭐ v3.36의 존재 이유(2026-08-07 실측): VOO+QQQ+XLK를 함께 사면 "시장+성장+
    기술"로 분산했다고 느끼지만 실제로는 같은 메가캡을 세 번 사는 것에 가깝다.
    top10만 봐도 세 쌍 전부 20%p를 넘는다.
    """
    voo_qqq = holdings_overlap(VOO_TOP10, QQQ_TOP10)
    qqq_xlk = holdings_overlap(QQQ_TOP10, XLK_TOP10)
    voo_xlk = holdings_overlap(VOO_TOP10, XLK_TOP10)

    assert voo_qqq["shared_weight"] == pytest.approx(0.3448, abs=1e-3)
    assert qqq_xlk["shared_weight"] == pytest.approx(0.3195, abs=1e-3)
    assert voo_xlk["shared_weight"] == pytest.approx(0.2315, abs=1e-3)
    # 셋 다 경고 임계값을 넘는다
    for ov in (voo_qqq, qqq_xlk, voo_xlk):
        assert ov["shared_weight"] >= 0.20
    # NVDA/AAPL/MSFT는 세 ETF 모두에 들어 있다(삼중 계상의 핵심)
    for t in ("NVDA", "AAPL", "MSFT"):
        assert t in voo_qqq["common_tickers"]
        assert t in qqq_xlk["common_tickers"]
        assert t in voo_xlk["common_tickers"]


def test_portfolio_overlap_report_warns_and_lists_missing_data():
    voo = run_etf_analysis(voo_inputs(top10_holdings=VOO_TOP10))
    qqq = run_etf_analysis(voo_inputs(ticker="QQQ", top10_holdings=QQQ_TOP10))
    no_data = run_etf_analysis(voo_inputs(ticker="XLF"))

    rep = portfolio_overlap_report([voo, qqq, no_data])
    assert len(rep["pairs"]) == 1                 # 데이터 있는 2개만 쌍이 된다
    assert rep["pairs"][0]["warning"] is not None
    assert "중복노출 경고" in rep["pairs"][0]["warning"]
    # 데이터 없는 ETF를 '겹침 없음'으로 처리하지 않고 명시적으로 남긴다
    assert rep["skipped_no_holdings"] == ["XLF"]


def test_holdings_overlap_zero_common_tickers_is_flagged_uninformative():
    """
    ⭐ v3.37 정정의 근거 사실 - top10 표본끼리 공통 종목이 0개면 shared_weight도
    기계적으로 0이 되지만, 그게 "안 겹친다"는 뜻은 아니다. XLF(전부 S&P500
    소속 금융주)와 VOO 실측 top10이 정확히 이 경우였다 - 우연히 top10끼리만
    안 겹쳤을 뿐, XLF 보유종목은 전부 VOO 안에 있다.
    """
    xlf_top10 = {"JPM": 0.12, "BRK.B": 0.10, "V": 0.09, "MA": 0.08, "BAC": 0.07}
    voo_top10_without_financials = {"NVDA": 0.0750, "AAPL": 0.0658, "MSFT": 0.0429,
                                     "AMZN": 0.0361, "GOOGL": 0.0324}
    ov = holdings_overlap(xlf_top10, voo_top10_without_financials)
    assert ov["n_common"] == 0
    assert ov["shared_weight"] == 0.0
    # 이게 이번 정정의 핵심 - 0.0은 계산 결과일 뿐 "겹침 없음"으로 읽으면 안 된다
    assert ov["informative"] is False
    assert "모름" in ov["interpretation"]


def test_holdings_overlap_nonzero_common_is_informative():
    ov = holdings_overlap(VOO_TOP10, QQQ_TOP10)
    assert ov["n_common"] > 0
    assert ov["informative"] is True
    assert "하한" in ov["interpretation"]


def test_portfolio_overlap_report_separates_uninformative_pairs():
    """
    ⭐ v3.37 - portfolio_overlap_report()가 uninformative 쌍을 pairs(실측
    겹침) 목록에서 제외하고 uninformative_pairs로 따로 보고해야 한다.
    XLF+VOO처럼 top10끼리 우연히 안 겹친 쌍이 "0.0%p 겹침"으로
    format_overlap_table()에 나오면 "섹터ETF와 광범위지수를 같이 담아도
    안전하다"는 정반대 결론을 유도하기 때문이다.
    """
    xlf_top10 = {"JPM": 0.12, "BRK.B": 0.10, "V": 0.09, "MA": 0.08, "BAC": 0.07}
    voo = run_etf_analysis(voo_inputs(top10_holdings=VOO_TOP10))
    xlf = run_etf_analysis(voo_inputs(ticker="XLF", top10_holdings=xlf_top10))

    rep = portfolio_overlap_report([voo, xlf])
    assert rep["pairs"] == []                       # 실측 겹침 목록에는 없어야 함
    assert len(rep["uninformative_pairs"]) == 1
    assert rep["uninformative_pairs"][0]["pair"] == ("VOO", "XLF")
    assert rep["uninformative_pairs"][0]["informative"] is False

    table = format_overlap_table(rep)
    # "0.0%p"로 렌더링되면 안 되고, 명시적으로 "측정 불가"라고 나와야 한다
    assert "VOO+XLF" not in table.split("측정 불가")[0]  # pairs 섹션에는 없음
    assert "측정 불가" in table
    assert "0.0%p" not in table


def test_overlap_does_not_affect_individual_judgment():
    """겹침은 '함께 살 때'의 문제이므로 개별 ETF 판정은 건드리지 않는다."""
    without = run_etf_analysis(voo_inputs())
    with_h = run_etf_analysis(voo_inputs(top10_holdings=VOO_TOP10))
    assert without["valuation"]["gap_min"] == pytest.approx(with_h["valuation"]["gap_min"])
    assert without["ers"]["score"] == with_h["ers"]["score"]
