"""
after_cost.py 테스트 — 세후 계산의 성질을 고정한다.

고정하는 것:
  ① 양도세는 **이익에만** 붙는다(손실이면 세금 0)
  ② 세후 수익률 < 총수익률 (이익 구간에서 항상)
  ③ 기본공제가 금액 기준이므로 **원금이 클수록 공제 효과가 희석된다**
  ④ 손익통산을 켜면 세금이 줄어든다(끄는 쪽이 손실 많은 그룹에 불리)
  ⑤ 총수익 격차 > 세후 격차 (양도세의 비대칭성)
"""
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from engine.after_cost import (  # noqa: E402
    ANNUAL_EXEMPTION_KRW, CAPITAL_GAINS_TAX_RATE, VALIDATION_STATUS,
    after_cost_return, portfolio_after_cost,
)


# ── ① 손실이면 양도세 없음 ───────────────────────────────────────────────
def test_loss_incurs_no_capital_gains_tax():
    net = after_cost_return(-50.0, principal_krw=10_000_000)
    # 세금은 0이고 거래비용만 깎인다 -> -50%보다 약간 더 나쁘다
    assert -51.0 < net < -50.0


def test_zero_return_still_loses_transaction_costs():
    net = after_cost_return(0.0, principal_krw=10_000_000)
    assert net < 0, "왕복 거래비용이 있으면 0% 총수익도 세후는 마이너스여야 한다"


# ── ② 이익 구간에서 세후 < 총수익 ────────────────────────────────────────
@pytest.mark.parametrize("gross", [10.0, 100.0, 500.0, 1870.0])
def test_after_cost_is_always_below_gross_when_profitable(gross):
    net = after_cost_return(gross, principal_krw=10_000_000)
    assert net < gross


# ── ③ 기본공제는 금액 기준 - 원금이 클수록 희석 ──────────────────────────
def test_exemption_dilutes_as_principal_grows():
    small = after_cost_return(100.0, principal_krw=5_000_000)
    large = after_cost_return(100.0, principal_krw=500_000_000)
    assert small > large, (
        "기본공제가 정액이므로 원금이 작을수록 세후 수익률이 높아야 한다")


def test_exemption_can_be_disabled():
    with_ex = after_cost_return(100.0, principal_krw=10_000_000,
                                apply_exemption=True)
    without = after_cost_return(100.0, principal_krw=10_000_000,
                                apply_exemption=False)
    assert with_ex > without


def test_small_gain_fully_covered_by_exemption_pays_no_tax():
    """공제(250만원) 이내 차익이면 양도세가 0이어야 한다."""
    # 원금 1000만원에 총수익 10% -> 차익 약 100만원 < 250만원 공제
    net = after_cost_return(10.0, principal_krw=10_000_000)
    no_tax = after_cost_return(10.0, principal_krw=10_000_000, tax_rate=0.0)
    assert net == pytest.approx(no_tax, abs=1e-9)


# ── ④ 손익통산 ───────────────────────────────────────────────────────────
def test_loss_offset_reduces_tax():
    rets = [200.0, -80.0, 50.0, -30.0]
    with_offset = portfolio_after_cost(rets, offset_losses=True)
    without = portfolio_after_cost(rets, offset_losses=False)
    assert with_offset > without, "손익통산을 켜면 세금이 줄어 실수령이 늘어야 한다"


def test_portfolio_empty_returns_none():
    assert portfolio_after_cost([]) is None


def test_portfolio_equal_weight_matches_single_when_one_holding():
    single = after_cost_return(100.0, principal_krw=10_000_000)
    port = portfolio_after_cost([100.0], total_principal_krw=10_000_000)
    assert port == pytest.approx(single, abs=1e-9)


# ── ⑤ 양도세 비대칭 - 총수익 격차보다 세후 격차가 작다 ───────────────────
def test_tax_compresses_the_gap_between_groups():
    """
    핵심 성질: flagged가 총수익이 높으면 세금도 더 내므로 **세후 격차는
    반드시 총수익 격차보다 작다.** 성적표를 총수익으로만 읽으면 우위를
    과대평가한다.
    """
    flagged = [283.0] * 5
    not_flagged = [104.0] * 5
    gross_gap = 283.0 - 104.0
    net_gap = (portfolio_after_cost(flagged)
               - portfolio_after_cost(not_flagged))
    assert 0 < net_gap < gross_gap


# ── 상수의 지위를 명시한다 ───────────────────────────────────────────────
def test_validation_status_separates_legal_constant_from_assumption():
    """세율은 법정값이고 스프레드·수수료는 가정이다 - 섞어 쓰면 안 된다."""
    assert "LEGAL_CONSTANT" in VALIDATION_STATUS["tax_rate"]
    assert "UNVALIDATED_DEFAULT" in VALIDATION_STATUS["fx_spread"]
    assert "UNVALIDATED_DEFAULT" in VALIDATION_STATUS["commission"]


def test_statutory_values_are_what_we_documented():
    assert CAPITAL_GAINS_TAX_RATE == 0.22
    assert ANNUAL_EXEMPTION_KRW == 2_500_000


def test_principal_must_be_positive():
    with pytest.raises(ValueError):
        after_cost_return(10.0, principal_krw=0)
