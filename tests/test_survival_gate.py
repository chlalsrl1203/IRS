"""
survival_gate.py 테스트 (2026-08-30).

고정하는 것:
  ① 자기자본<0 AND OCF<0 -> 거른다
  ② 자기자본<0 이지만 OCF>=0(자사주매입형) -> 거르지 않는다(BRO/BSY 재발 방지)
  ③ OCF<0 이지만 자기자본>=0 -> 거르지 않는다
  ④ 둘 다 양수 -> 거르지 않는다
  ⑤ 데이터 부재 -> 거르지 않는다(판단 불가를 위험으로 오독하지 않는다)
  ⑥ 자기자본·OCF 최신연도가 서로 달라도 각자의 최신연도를 쓴다
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from engine.survival_gate import extreme_survival_risk  # noqa: E402


def test_negative_equity_and_negative_ocf_is_rejected():
    at_risk, reason = extreme_survival_risk(
        {2023: -500.0, 2024: -800.0}, {2023: -100.0, 2024: -150.0})
    assert at_risk is True
    assert "극단적 존속위험" in reason


def test_negative_equity_with_positive_ocf_is_not_rejected():
    """AutoZone/Domino's형 - 자사주매입으로 자본잠식이어도 현금흐름이 건전하면 통과."""
    at_risk, reason = extreme_survival_risk(
        {2023: -2000.0, 2024: -2500.0}, {2023: 800.0, 2024: 900.0})
    assert at_risk is False
    assert reason is None


def test_positive_equity_with_negative_ocf_is_not_rejected():
    at_risk, reason = extreme_survival_risk(
        {2023: 500.0, 2024: 600.0}, {2023: -50.0, 2024: -80.0})
    assert at_risk is False


def test_both_positive_is_not_rejected():
    at_risk, reason = extreme_survival_risk(
        {2023: 500.0, 2024: 600.0}, {2023: 50.0, 2024: 80.0})
    assert at_risk is False


def test_missing_equity_data_does_not_reject():
    at_risk, reason = extreme_survival_risk({}, {2023: -50.0, 2024: -80.0})
    assert at_risk is False
    assert "미확보" in reason


def test_missing_ocf_data_does_not_reject():
    at_risk, reason = extreme_survival_risk({2023: -500.0}, {})
    assert at_risk is False


def test_both_missing_does_not_reject():
    at_risk, reason = extreme_survival_risk({}, {})
    assert at_risk is False


def test_uses_latest_year_independently_per_series():
    """자기자본은 FY2022가 최신(마이너스), OCF는 FY2024가 최신(마이너스) - 둘 다 최신연도 기준으로 거른다."""
    at_risk, _ = extreme_survival_risk(
        {2020: 100.0, 2021: 50.0, 2022: -10.0},
        {2020: 5.0, 2021: -1.0, 2022: 10.0, 2023: 20.0, 2024: -5.0})
    assert at_risk is True


def test_does_not_duplicate_drs_leverage_axis():
    """
    이 게이트가 순부채/EBITDA·매출변동성 같은 DRS 연속반영 축을 인자로
    받지 않는지 확인한다 - v3.19 BRO/BSY 이중반영 사고의 재발을 구조적으로
    막는다(시그니처 자체가 그 축을 받을 수 없다).
    """
    import inspect
    params = set(inspect.signature(extreme_survival_risk).parameters)
    assert params == {"shareholders_equity_by_year", "operating_cashflow_by_year"}
