"""
engine/deep_screen.py 불변조건 (v3.65, 2026-08-23).

핵심 주장은 "재무제표만으로 객관적으로 계산 가능한 부분은 공식 엔진과
정확히 일치한다"이다 - 그 주장을 실제 ledger 데이터로 검증한다.
"""
import json
import pathlib

import pytest

from engine.deep_screen import DeepScreenResult, _window_cagr, deep_screen
from engine.screener import (
    ASSUMED_COMPETITION_INTENSITY,
    ASSUMED_DEMAND_SENSITIVITY,
    DEFAULT_NDTE,
)

ROOT = pathlib.Path(__file__).resolve().parent.parent


def _bsx_series():
    d = json.loads((ROOT / "ledger" / "BSX_2026-08-13.json").read_text(encoding="utf-8"))
    inp = d["inputs"]

    def to_int(dd):
        return {int(k): v for k, v in dd.items()}

    series = {k: to_int(inp[k]) for k in
              ("revenue_by_year", "operating_cashflow_by_year",
               "capex_by_year", "operating_income_by_year")}
    return d, series


# ── _window_cagr 원자 함수 ────────────────────────────────────────────
def test_window_cagr_basic():
    assert _window_cagr({2020: 100, 2025: 200}, 2025, 5) == pytest.approx(
        (200 / 100) ** (1 / 5) - 1)


def test_window_cagr_none_when_base_year_missing():
    assert _window_cagr({2022: 100, 2025: 200}, 2025, 5) is None


def test_window_cagr_none_on_nonpositive_values():
    """v3.19 가드와 동일 원리 - 음수/0 시작값에서 복소수를 조용히 반환하면 안 된다."""
    assert _window_cagr({2020: -10, 2025: 200}, 2025, 5) is None
    assert _window_cagr({2020: 100, 2025: -10}, 2025, 5) is None
    assert _window_cagr({2020: 0, 2025: 200}, 2025, 5) is None


# ── 핵심: BSX 실제 ledger 대비 골든 교차검증 ─────────────────────────
def test_growth_side_matches_official_ledger_exactly():
    """
    revenue/FCF CAGR·구조적할인율·lynch_type·realistic_growth는 재무제표만으로
    계산 가능하므로 공식 ledger와 **1e-12 정밀도로 완전히 일치**해야 한다.
    """
    d, series = _bsx_series()
    r = deep_screen("BSX", series, market_cap=d["inputs"]["market_cap"])

    dv = d["derived"]
    assert r.revenue_cagr_3y == pytest.approx(dv["revenue_cagr_3y"], abs=1e-12)
    assert r.revenue_cagr_5y == pytest.approx(dv["revenue_cagr_5y"], abs=1e-12)
    assert r.revenue_cagr_10y == pytest.approx(dv["revenue_cagr_10y"], abs=1e-12)
    assert r.fcf_cagr_5y == pytest.approx(dv["fcf_cagr_5y"], abs=1e-12)
    assert r.worst_yoy_revenue == pytest.approx(dv["worst_yoy_revenue_growth"], abs=1e-12)

    assert r.lynch_type == d["lynch"]["used"]
    assert r.structural_discount_pct == pytest.approx(
        d["growth"]["structural_discount_pct"], abs=1e-12)
    assert r.realistic_growth == pytest.approx(d["growth"]["realistic_growth"], abs=1e-12)


def test_objectively_measurable_drs_components_match_exactly():
    """
    revenue_volatility·margin_volatility는 재무제표에서만 나오므로 정확히
    일치해야 한다. margin_volatility는 pipeline.py의 margin_years 규약
    (최근 5개년만)을 그대로 따라야 한다 - 전 구간을 쓰면 2020 코로나 저마진이
    stdev를 부풀려 4.0->8.0으로 등급 자체가 달라진다(실제로 겪은 회귀).
    """
    d, series = _bsx_series()
    r = deep_screen("BSX", series, market_cap=d["inputs"]["market_cap"])
    official = d["drs"]["components"]
    assert r.drs_components["revenue_volatility"] == official["revenue_volatility"]
    assert r.drs_components["margin_volatility"] == official["margin_volatility"]


def test_subjective_drs_components_differ_and_are_labeled():
    """
    leverage(실측 net_debt/ebitda 없음)·competition_intensity·cyclicality의
    demand_sensitivity 성분은 재무제표 밖 정보라 공식값과 다를 수 있다 -
    다르다는 사실 자체가 정상이며, assumed_inputs에 반드시 라벨돼야 한다.
    """
    d, series = _bsx_series()
    r = deep_screen("BSX", series, market_cap=d["inputs"]["market_cap"])
    assert r.drs_components["competition_intensity"] == ASSUMED_COMPETITION_INTENSITY
    assert r.drs_components["competition_intensity"] != d["drs"]["components"]["competition_intensity"]
    assert "net_debt_to_ebitda" in r.assumed_inputs
    assert "competition_intensity" in r.assumed_inputs
    assert "demand_sensitivity_pct" in r.assumed_inputs
    assert "model_used" in r.assumed_inputs


def test_never_claims_two_stage():
    """
    모델선택 규칙화는 2026-08-16 연구에서 REJECT됐다(구간 완전중첩, 규칙
    불가) - deep_screen이 여기서 몰래 규칙을 발명하면 그 결론을 어기는 것.
    항상 single_stage(Gordon)만 계산해야 하고, 그 사실을 명시해야 한다.
    """
    d, series = _bsx_series()
    r = deep_screen("BSX", series, market_cap=d["inputs"]["market_cap"])
    assert "single_stage" in r.assumed_inputs["model_used"]
    ig_official_single = d["implied_growth"]["models"]["single_stage"]
    # r(할인율)이 DRS 차이로 조금 다르므로 완전 일치는 아니지만 근접해야 한다
    assert r.implied_growth == pytest.approx(ig_official_single, abs=0.01)


# ── 단위 함정 (CLAUDE.md 단위규약과 동일 - 가장 중요한 회귀 방지) ───────
def test_market_cap_unit_trap_structural_discount_uses_billions():
    """
    structural_discount_rate/classify_lynch_type은 10억 단위를 받는다.
    market_cap을 원 단위 그대로 넣으면(단위 실수) market_cap_b가 10^9배
    커져 초대형주 가산(+3%p, market_cap_b>=1000 조건)이 무조건 걸리는 등
    결과가 조용히 틀려진다.

    BSX($74B, 가산 기준 $200B/$1000B 미달)로는 이 함정을 재현할 수 없다 -
    가산 임계값을 실제로 넘나드는 시가총액이어야 unit 실수가 값에 드러난다.
    """
    d, series = _bsx_series()
    mega_cap = 500_000_000_000  # $500B = 500(10억단위) - 200 이상 1000 미만 가산 구간
    r_correct = deep_screen("BSX", series, market_cap=mega_cap)
    # 단위 실수를 흉내: 10억단위로 나눈 값을 원단위인 것처럼 넣으면
    # market_cap_b가 500/1e9로 쪼그라들어 가산이 전혀 안 걸린다
    r_wrong_scale = deep_screen("BSX", series, market_cap=mega_cap / 1e9)
    assert r_correct.structural_discount_pct != pytest.approx(
        r_wrong_scale.structural_discount_pct, abs=1e-6)
    assert r_correct.structural_discount_pct > r_wrong_scale.structural_discount_pct


def test_market_cap_unit_trap_implied_growth_uses_raw_units():
    """implied_growth_from_fcf_yield/fcf_yield는 원 단위 그대로 써야 한다."""
    d, series = _bsx_series()
    mc = d["inputs"]["market_cap"]
    r = deep_screen("BSX", series, market_cap=mc)
    assert r.fcf_yield == pytest.approx(r.fcf0 / mc, abs=1e-12)


# ── 그레이스풀 디그레이드 ────────────────────────────────────────────
def test_missing_10y_window_falls_back_to_5y_like_v325():
    """v3.25가 확립한 정확한 대체 규약(3y가 아니라 5y로 대체)과 동일해야 한다."""
    series = {
        "revenue_by_year": {y: 1000 * (1.1 ** i) for i, y in enumerate(range(2020, 2026))},
        "operating_cashflow_by_year": {y: 300 * (1.1 ** i) for i, y in enumerate(range(2020, 2026))},
        "capex_by_year": {y: 50 * (1.05 ** i) for i, y in enumerate(range(2020, 2026))},
        "operating_income_by_year": {y: 200 * (1.1 ** i) for i, y in enumerate(range(2020, 2026))},
    }
    r = deep_screen("TEST", series, market_cap=50_000_000_000)
    assert r.revenue_cagr_10y is None
    assert r.revenue_cagr_10y_is_fallback is True
    assert any("10년 CAGR 산출 불가" in m for m in r.data_limitations)
    # structural_discount_rate가 실제로 5y 값을 받았는지(3y로 오염 안 됐는지)
    from engine.expectation_gap_engine import structural_discount_rate
    expected = structural_discount_rate(
        r.revenue_cagr_3y, r.revenue_cagr_5y, 50_000_000_000 / 1e9)
    assert r.structural_discount_pct == pytest.approx(expected, abs=1e-12)


def test_missing_operating_income_excludes_margin_volatility_not_crash():
    series = {
        "revenue_by_year": {y: 1000 * (1.1 ** i) for i, y in enumerate(range(2020, 2026))},
        "operating_cashflow_by_year": {y: 300 * (1.1 ** i) for i, y in enumerate(range(2020, 2026))},
        "capex_by_year": {y: 50 * (1.05 ** i) for i, y in enumerate(range(2020, 2026))},
        "operating_income_by_year": {},
    }
    r = deep_screen("TEST", series, market_cap=50_000_000_000)
    assert r.drs_components["margin_volatility"] is None
    assert any("margin_volatility 계산 불가" in m for m in r.data_limitations)
    assert r.drs > 0  # DRSInputs가 excluded_reasons로 정상 처리했는지


def test_fcf0_nonpositive_raises_model_not_applicable():
    series = {
        "revenue_by_year": {y: 1000 * (1.1 ** i) for i, y in enumerate(range(2020, 2026))},
        "operating_cashflow_by_year": {y: 10 for y in range(2020, 2026)},
        "capex_by_year": {y: 50 for y in range(2020, 2026)},
        "operating_income_by_year": {y: 100 for y in range(2020, 2026)},
    }
    with pytest.raises(ValueError, match="Model N/A"):
        deep_screen("TEST", series, market_cap=50_000_000_000)


def test_growth_cap_binding_is_flagged():
    """v3.24 M-1과 동일한 경고 - 성장상한이 바인딩되면 성장분석이 결과에 기여 못 한다."""
    series = {
        "revenue_by_year": {y: 1000 * (1.6 ** i) for i, y in enumerate(range(2020, 2026))},
        "operating_cashflow_by_year": {y: 300 * (1.6 ** i) for i, y in enumerate(range(2020, 2026))},
        "capex_by_year": {y: 20 * (1.1 ** i) for i, y in enumerate(range(2020, 2026))},
        "operating_income_by_year": {y: 250 * (1.6 ** i) for i, y in enumerate(range(2020, 2026))},
    }
    r = deep_screen("TEST", series, market_cap=50_000_000_000)
    assert any("성장상한 바인딩" in m for m in r.data_limitations)


def test_explicit_net_debt_to_ebitda_overrides_default_without_flag():
    d, series = _bsx_series()
    real_ndte = 1.94
    r = deep_screen("BSX", series, market_cap=d["inputs"]["market_cap"],
                    net_debt_to_ebitda=real_ndte)
    assert "net_debt_to_ebitda" not in r.assumed_inputs
    assert r.drs_components["leverage"] != DEFAULT_NDTE  # 그냥 값이 다르다는 스모크체크


def test_raises_on_insufficient_years():
    with pytest.raises(ValueError, match="심층분석에 최소"):
        deep_screen("TEST", {
            "revenue_by_year": {2025: 100},
            "operating_cashflow_by_year": {2025: 30},
            "capex_by_year": {2025: 5},
            "operating_income_by_year": {2025: 20},
        }, market_cap=1_000_000_000)


# ── base rate 병기 (v3.66) ────────────────────────────────────────────
def test_base_rate_is_attached_but_never_changes_judgment():
    """
    base rate는 **병기 전용**이다. Mauboussin 자신이 하드컷이 아니라
    'reality check'로 쓰라고 했고, IRS는 v3.19에서 하드 필터가 이중 반영을
    만든다는 걸 이미 실증했다(BRO·BSY 오탈락).
    """
    d, series = _bsx_series()
    mc = d["inputs"]["market_cap"]
    r = deep_screen("BSX", series, market_cap=mc)
    assert r.base_rate is not None
    assert "base_rate_pct" in r.base_rate
    # 판정은 Gap에서만 나온다 - base rate가 붙어도 그대로여야 한다
    from engine.expectation_gap_engine import judgment_from_gap
    assert r.judgment == judgment_from_gap(r.gap)


def test_extremely_rare_growth_raises_a_limitation_not_a_rejection():
    """대형사에 고성장을 부여하면 경고는 나오되 예외가 나면 안 된다."""
    years = list(range(2015, 2026))
    # 매출 $40B 규모에서 연 30% 성장 - 역사적으로 거의 없는 조합
    series = {
        "revenue_by_year": {y: 40e9 * (1.30 ** (i - 10)) for i, y in enumerate(years)},
        "operating_cashflow_by_year": {y: 12e9 * (1.30 ** (i - 10)) for i, y in enumerate(years)},
        "capex_by_year": {y: 1e9 * (1.1 ** (i - 10)) for i, y in enumerate(years)},
        "operating_income_by_year": {y: 9e9 * (1.30 ** (i - 10)) for i, y in enumerate(years)},
    }
    r = deep_screen("BIGFAST", series, market_cap=500e9)
    assert r.base_rate["size_class"] in ("25000+", "50000+")
    assert r.base_rate["tier"] in ("NO_PRECEDENT", "EXTREMELY_RARE", "RARE")
    assert any("base rate" in m for m in r.data_limitations)
    assert r.judgment in ("저평가 가능성", "적정가/경계선", "과대평가 가능성")


def test_base_rate_failure_does_not_break_deep_screen():
    """병기가 실패해도 심층분석 본체는 살아남아야 한다."""
    import engine.deep_screen as ds_mod
    d, series = _bsx_series()
    orig = ds_mod.assess_growth_plausibility
    try:
        ds_mod.assess_growth_plausibility = lambda **kw: (_ for _ in ()).throw(
            ValueError("의도적 파손"))
        r = deep_screen("BSX", series, market_cap=d["inputs"]["market_cap"])
        assert r.base_rate is None
        assert any("base rate 대조 실패" in m for m in r.data_limitations)
        assert r.gap == pytest.approx(r.realistic_growth - r.implied_growth)
    finally:
        ds_mod.assess_growth_plausibility = orig


def test_result_is_dataclass_with_documented_fields():
    d, series = _bsx_series()
    r = deep_screen("BSX", series, market_cap=d["inputs"]["market_cap"])
    assert isinstance(r, DeepScreenResult)
    assert r.judgment in ("저평가 가능성", "적정가/경계선", "과대평가 가능성")
