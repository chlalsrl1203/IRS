"""
P0-05/06/07 Canonical · Normalization · Reconciliation 테스트.

# SOURCE:
https://github.com/chenditc/investment_data (Apache-2.0)

# METHOD:
REIMPLEMENT — 가져온 것은 "출처별 원본을 남기고 대조본을 별도 계층으로 둔다"는
원칙뿐이라, 테스트도 그 원칙이 실제로 지켜지는지를 고정한다.

고정하는 불변조건:
  ① 선택되지 않은 후보를 버리지 않는다 (버리면 '왜 이 값인가'를 잃는다)
  ② 물질적 불일치를 자동 해결하지 않는다 (정의 차이일 수 있다)
  ③ 통화가 다르면 오류다 (환율 변환을 몰래 하지 않는다)
  ④ 부호 규약을 뒤집기가 아니라 절댓값으로 맞춘다
  ⑤ 미해결 충돌을 안은 채 분석 입력을 만들 수 없다
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.data.canonical import (  # noqa: E402
    OUTFLOW_POSITIVE_METRICS, CanonicalSeries, NormalizationError,
    build_canonical_series, detect_scale_mismatch, normalize_sign,
)
from engine.data.providers.base import FinancialFact  # noqa: E402
from engine.data.reconcile import (  # noqa: E402
    TOLERANCE_TIERS, VALIDATION_STATUS, classify_difference,
    reconcile_candidates, reconciliation_report,
)


def fact(metric="operating_income", fy=2025, value=1000.0, source_key="sec_edgar",
         currency="USD", available_at="2026-02-18"):
    return FinancialFact(
        entity="BSX", metric=metric, fiscal_year=fy, value=value,
        unit="currency_amount", currency=currency,
        period_start=f"{fy}-01-01", period_end=f"{fy}-12-31",
        available_at=available_at, source=f"{source_key} src",
        source_key=source_key, retrieved_at="2026-08-19",
    )


# ── ① 후보를 버리지 않는다 ───────────────────────────────────────────────
def test_rejected_candidates_are_preserved_not_discarded():
    """원본을 덮어쓰면 '왜 이 값이 선택됐는가'를 영원히 잃는다."""
    s = build_canonical_series("BSX", {
        "sec_edgar": [fact(value=3_613_000_000)],
        "alpha_vantage": [fact(value=3_971_000_000, source_key="alpha_vantage")],
    }, reconcile_fn=reconcile_candidates)
    cv = s.values[("operating_income", 2025)]
    assert {c["source_key"] for c in cv.candidates} == {"sec_edgar", "alpha_vantage"}
    assert {c["value"] for c in cv.candidates} == {3_613_000_000.0, 3_971_000_000.0}
    assert cv.conflict["rejected"]          # 탈락 후보가 결과에 남아 있다


def test_agreeing_sources_record_that_they_agreed():
    s = build_canonical_series("BSX", {
        "sec_edgar": [fact(metric="operating_cashflow", value=4_534_000_000)],
        "alpha_vantage": [fact(metric="operating_cashflow", value=4_534_000_000,
                               source_key="alpha_vantage")],
    }, reconcile_fn=reconcile_candidates)
    cv = s.values[("operating_cashflow", 2025)]
    assert cv.value == 4_534_000_000.0
    assert "동일한 값" in cv.chosen_reason
    assert not cv.has_unresolved_conflict


# ── ② 물질적 불일치를 자동 해결하지 않는다 ───────────────────────────────
def test_material_conflict_is_not_auto_resolved():
    """
    BSX 실사례: 벤더 3,971M vs SEC 3,613M(9.0% 차이). 자동으로 SEC를 택하면
    34종목 입력이 조용히 바뀌고 그 변화의 출처를 추적할 수 없다.
    """
    d = reconcile_candidates([
        {"source_key": "alpha_vantage", "value": 3_971_000_000.0, "source": "AV",
         "available_at": "2026-02-18"},
        {"source_key": "sec_edgar", "value": 3_613_000_000.0, "source": "SEC",
         "available_at": "2026-02-18"},
    ])
    assert d["severity"] == "MATERIAL"
    assert d["requires_review"] is True
    assert d["value"] is None                       # 채택하지 않는다
    assert d["chosen_source_key"] is None
    assert d["suggested_source_key"] == "sec_edgar"  # 제안은 한다
    assert "정의가 다르다" in d["reason"]


def test_small_difference_is_auto_resolved_by_authority():
    """반올림 수준 차이는 판단할 것이 없다 — 막으면 잡음만 늘어난다."""
    d = reconcile_candidates([
        {"source_key": "alpha_vantage", "value": 1_000_000.0, "source": "AV",
         "available_at": "2026-02-18"},
        {"source_key": "sec_edgar", "value": 1_000_500.0, "source": "SEC",
         "available_at": "2026-02-18"},
    ])
    assert d["severity"] in ("ROUNDING", "MINOR")
    assert d["requires_review"] is False
    assert d["value"] == 1_000_500.0                # 1차 공시가 이긴다
    assert d["chosen_source_key"] == "sec_edgar"


def test_sign_conflict_is_always_material_regardless_of_magnitude():
    """
    BSX FY2015 실사례: 벤더 +790M(이익) vs SEC −327M(손실). 상대오차가 얼마든
    부호가 갈리면 같은 것을 재고 있지 않다는 뜻이다.
    """
    c = classify_difference([790_000_000.0, -327_000_000.0])
    assert c["sign_conflict"] is True
    assert c["tier"] == "MATERIAL" and c["auto_resolvable"] is False
    d = reconcile_candidates([
        {"source_key": "alpha_vantage", "value": 790_000_000.0, "source": "AV",
         "available_at": "2016-02-23"},
        {"source_key": "sec_edgar", "value": -327_000_000.0, "source": "SEC",
         "available_at": "2016-02-23"},
    ])
    assert "부호가 갈린다" in d["reason"]


def test_no_reconcile_policy_means_unresolved_not_silent_pick():
    """정책이 없으면 조용히 하나를 고르지 않는다."""
    s = build_canonical_series("BSX", {
        "sec_edgar": [fact(value=100.0)],
        "alpha_vantage": [fact(value=200.0, source_key="alpha_vantage")],
    })
    cv = s.values[("operating_income", 2025)]
    assert cv.value is None and cv.has_unresolved_conflict
    assert any("[미해결 충돌]" in x for x in s.limitations)


# ── ③ 통화 ───────────────────────────────────────────────────────────────
def test_mixed_currency_is_an_error_not_a_silent_conversion():
    """M-6: PDD가 CNY인데 ledger에 아무 표시가 없었다."""
    with pytest.raises(NormalizationError, match="통화가 다르다"):
        build_canonical_series("PDD", {
            "sec_edgar": [fact(currency="USD")],
            "alpha_vantage": [fact(currency="CNY", source_key="alpha_vantage")],
        }, reconcile_fn=reconcile_candidates)


# ── ④ 부호 규약 ──────────────────────────────────────────────────────────
def test_outflow_metrics_are_made_positive_by_absolute_value_not_negation():
    """
    뒤집기(-value)를 쓰면 이미 올바른 부호로 온 값까지 망가진다. 벤더는 음수로,
    SEC는 양수로 주므로 같은 코드가 둘 다 다뤄야 한다.
    """
    assert normalize_sign("capex", -876.0) == 876.0
    assert normalize_sign("capex", 876.0) == 876.0        # 뒤집기였다면 -876
    assert normalize_sign("dividends_paid", -50.0) == 50.0
    assert "capex" in OUTFLOW_POSITIVE_METRICS


def test_non_outflow_metrics_keep_their_sign():
    """영업이익 적자(-327M)를 양수로 만들면 손실이 이익으로 둔갑한다."""
    assert normalize_sign("operating_income", -327.0) == -327.0
    assert normalize_sign("net_income", -100.0) == -100.0


def test_sign_normalization_makes_opposite_conventions_agree():
    s = build_canonical_series("BSX", {
        "sec_edgar": [fact(metric="capex", value=876_000_000)],
        "alpha_vantage": [fact(metric="capex", value=-876_000_000,
                               source_key="alpha_vantage")],
    }, reconcile_fn=reconcile_candidates)
    cv = s.values[("capex", 2025)]
    assert cv.value == 876_000_000.0
    assert not cv.has_unresolved_conflict     # 부호 규약만 달랐을 뿐 같은 값이다


# ── 스케일 ───────────────────────────────────────────────────────────────
def test_scale_mismatch_is_reported_not_auto_corrected():
    """RAR 100배 사고의 교훈 — 그럴듯한 원인을 검증 없이 확정하지 않는다."""
    r = detect_scale_mismatch(4_534_000_000.0, 4_534_000.0)
    assert r["suspected"] is True and r["factor"] == 1_000
    assert "자동으로 고치지 않는다" in r["reason"]
    assert detect_scale_mismatch(100.0, 109.0)["suspected"] is False


# ── ⑤ 미해결 충돌을 안고 분석에 들어갈 수 없다 ───────────────────────────
def test_unresolved_conflict_blocks_analysis_inputs_by_default():
    s = build_canonical_series("BSX", {
        "sec_edgar": [fact(value=3_613_000_000)],
        "alpha_vantage": [fact(value=3_971_000_000, source_key="alpha_vantage")],
    }, reconcile_fn=reconcile_candidates)
    with pytest.raises(NormalizationError, match="미해결 출처 충돌"):
        s.to_inputs_kwargs()
    # 감수하려면 명시적으로 선언해야 한다
    assert s.to_inputs_kwargs(strict=False) == {}   # 값이 None이라 시계열이 비어 있다


def test_clean_series_produces_analysis_inputs_shape():
    s = build_canonical_series("BSX", {
        "sec_edgar": [fact(metric="revenue", fy=y, value=1000.0 + y)
                      for y in (2024, 2025)],
    }, reconcile_fn=reconcile_candidates)
    kw = s.to_inputs_kwargs(metrics=["revenue"])
    assert kw == {"revenue_by_year": {2024: 3024.0, 2025: 3025.0}}
    assert s.available_at("revenue") == {2024: "2026-02-18", 2025: "2026-02-18"}


# ── 리포트 / 인식론적 지위 ───────────────────────────────────────────────
def test_report_leads_with_what_is_unresolved():
    s = build_canonical_series("BSX", {
        "sec_edgar": [fact(value=3_613_000_000),
                      fact(metric="revenue", value=20_074_000_000)],
        "alpha_vantage": [fact(value=3_971_000_000, source_key="alpha_vantage"),
                          fact(metric="revenue", value=20_074_000_000,
                               source_key="alpha_vantage")],
    }, reconcile_fn=reconcile_candidates)
    rep = reconciliation_report(s)
    assert rep["n_values"] == 2 and rep["n_unresolved"] == 1
    assert rep["unresolved"][0]["metric"] == "operating_income"
    assert rep["by_severity"]["MATERIAL"] == 1
    assert "어느 출처를 썼는지 모르는 결과" in rep["note"]


def test_thresholds_declare_they_are_not_validated():
    """근거 없는 숫자를 근거 있는 것처럼 쓰지 않는다."""
    assert "IMPLEMENTED_NOT_VALIDATED" in VALIDATION_STATUS["tolerance_tiers"]
    assert TOLERANCE_TIERS[-1][1] == "MATERIAL"
    assert TOLERANCE_TIERS[-1][2] is False          # 물질적 차이는 자동해결 불가


def test_external_objects_cannot_enter_the_canonical_layer():
    with pytest.raises(TypeError, match="FinancialFact만 받는다"):
        build_canonical_series("BSX", {"sec_edgar": [{"metric": "revenue"}]})
