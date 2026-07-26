import glob
import json

import pytest

from engine.screener import (
    Candidate,
    estimate_drs,
    implied_growth_from_fcf_yield,
    required_fcf_yield,
    screen,
)


def _ledger_candidates():
    """저장된 ledger에서 '스크리닝 단계에 관측 가능한 값'만 뽑아 후보로 만든다."""
    out = []
    for path in sorted(glob.glob("ledger/*.json")):
        d = json.load(open(path, encoding="utf-8"))
        tick = d["meta"]["ticker"]
        date = d["meta"]["analyzed_at"][:10]
        # WCN/WM/IDXX는 2026-07-26판이 공식 기록(그 전 판은 건너뜀)
        if date != "2026-07-26" and tick in ("WCN", "WM", "IDXX"):
            continue
        inp, dv = d["inputs"], d["derived"]
        out.append((
            Candidate(
                ticker=tick, name=inp["company_name"], market_cap=inp["market_cap"],
                fcf0=dv["fcf0"], revenue_cagr_5y=dv["revenue_cagr_5y"],
                fcf_cagr_5y=dv["fcf_cagr_5y"],
                net_debt_to_ebitda=dv["net_debt_to_ebitda"],
                worst_yoy_revenue=dv["worst_yoy_revenue_growth"],
            ),
            d,
        ))
    return out


def test_implied_growth_formula_matches_engine_exactly():
    """
    y = FCF0/시총 -> g = (r-y)/(1+y) 항등식이 엔진의 single_stage 값과 정확히
    일치해야 한다. ledger 전건에서 오차 0이 확인된 관계다.
    """
    for c, d in _ledger_candidates():
        ig_engine = d["implied_growth"]["models"].get("single_stage")
        if ig_engine is None:
            continue
        r = d["discount_rate"]["r"]
        ig_formula = implied_growth_from_fcf_yield(c.fcf0 / c.market_cap, r)
        assert ig_formula == pytest.approx(ig_engine, abs=1e-12), c.ticker


def test_required_fcf_yield_is_inverse_of_implied_growth():
    r = 0.105
    for g in (-0.02, 0.0, 0.0411, 0.055, 0.08):
        y = required_fcf_yield(g, r)
        assert implied_growth_from_fcf_yield(y, r) == pytest.approx(g, abs=1e-12)


def test_screener_reproduces_known_buy_verdicts():
    """
    ledger 보유 12종목 중 실제 저평가 판정이 난 BRO/BSY는 반드시 통과해야 한다.
    (거짓 탈락은 후보를 영영 놓치므로 스크리너에서 가장 나쁜 오류다)
    """
    for c, d in _ledger_candidates():
        if d["judgment"] == "저평가 가능성":
            r = screen(c)
            assert r.passed, f"{c.ticker}(실제 저평가)가 탈락함: {r.failures}"


def test_screener_rejects_known_overvalued():
    """실제 과대평가 판정이 난 PH는 탈락해야 한다."""
    for c, d in _ledger_candidates():
        if d["judgment"] == "과대평가 가능성":
            r = screen(c)
            assert not r.passed, f"{c.ticker}(실제 과대평가)가 통과함"


def test_leverage_is_not_a_hard_filter_anymore():
    """
    v3.19 역검증에서 잡은 이중반영 회귀 방지: 순부채/EBITDA가 2.5배를 넘어도
    다른 조건이 좋으면 통과해야 한다. BRO(3.50배)/BSY(2.63배)가 실제로
    저평가 판정을 받은 사례가 근거다.
    """
    levered = Candidate(
        ticker="TEST", name="고레버리지 우량성장주", market_cap=10_000_000_000,
        fcf0=650_000_000,          # FCF수익률 6.5%
        revenue_cagr_5y=0.15, fcf_cagr_5y=0.15,
        net_debt_to_ebitda=3.5,    # 구 하드필터(2.5배)에 걸리던 값
        worst_yoy_revenue=0.02,
    )
    result = screen(levered)
    assert result.passed
    assert not any("순부채" in f for f in result.failures)


def test_negative_fcf_is_model_not_applicable():
    c = Candidate(
        ticker="LOSS", name="FCF 적자기업", market_cap=1_000_000_000,
        fcf0=-50_000_000, revenue_cagr_5y=0.30, fcf_cagr_5y=0.30,
        net_debt_to_ebitda=1.0, worst_yoy_revenue=0.10,
    )
    r = screen(c)
    assert not r.passed
    assert any("Model N/A" in f for f in r.failures)


def test_fcf_cagr_binds_when_lower_than_revenue():
    """
    AJG/AZO/ELV가 RG 0%대로 추락한 메커니즘: 매출은 좋은데 FCF가 안 따라오면
    FCF CAGR이 제약이 되어 탈락해야 한다.
    """
    c = Candidate(
        ticker="TRAP", name="매출만 성장하고 FCF는 정체", market_cap=10_000_000_000,
        fcf0=700_000_000,
        revenue_cagr_5y=0.18,   # 매출은 훌륭
        fcf_cagr_5y=0.01,       # FCF는 정체 -> 이쪽이 제약
        net_debt_to_ebitda=1.0, worst_yoy_revenue=0.05,
    )
    r = screen(c)
    assert not r.passed
    assert any("FCF CAGR" in f for f in r.failures)


def test_estimate_drs_moves_with_leverage_and_cyclicality():
    low = estimate_drs(net_debt_to_ebitda=-1.0, worst_yoy_revenue=0.05)
    high = estimate_drs(net_debt_to_ebitda=4.5, worst_yoy_revenue=-0.20)
    assert low < high
    assert 0 <= low <= 100 and 0 <= high <= 100


def test_tier_s_requires_nonpositive_implied_growth():
    """
    S등급은 시장이 역성장을 가격에 반영한 상태(ACGL/ADBE/TIGR/EVO 패턴).
    내재성장률 <= 0 이어야 한다.
    """
    deep = Candidate(
        ticker="DEEP", name="딥밸류 성장주", market_cap=10_000_000_000,
        fcf0=1_200_000_000,     # FCF수익률 12% -> 내재성장률 음수
        revenue_cagr_5y=0.15, fcf_cagr_5y=0.15,
        net_debt_to_ebitda=0.5, worst_yoy_revenue=0.03,
    )
    r = screen(deep)
    assert r.passed
    assert r.tier == "S"
    assert r.implied_growth_est <= 0
