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
    cost_score,
    earnings_yield,
    etf_risk_score,
    evaluate_valuation_by_source,
    expense_drag,
    fed_model_spread,
    implied_growth_from_pe,
    pe_source_divergence,
)
from engine.etf_pipeline import (
    ETFInputs,
    compare_etfs,
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
    assert cost_score(0.0003) < cost_score(0.003) < cost_score(0.009)
    # 보유종목은 적을수록 위험 -> 역방향
    assert breadth_score(2000) < breadth_score(300) < breadth_score(30)


def test_etf_risk_score_uses_drs_scale():
    """ERS는 DRS와 같은 0~100 스케일이어야 erp_from_drs를 재사용할 수 있다."""
    ers = etf_risk_score(0.37, 505, 0.0003, 0.0)
    assert 0 <= ers["score"] <= 100
    assert ers["excluded"] == ["earnings_quality"]

    full = etf_risk_score(0.37, 505, 0.0003, 0.0, pct_unprofitable=0.02)
    assert full["excluded"] == []
    assert len(full["components"]) == 5


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
