"""
P0-02 Provider Interface 테스트.

# SOURCE:
https://github.com/dgunning/edgartools · https://github.com/eddmpython/dartlab

# METHOD:
REIMPLEMENT — 경계 설계만 가져왔으므로 테스트도 **IRS가 지키기로 한 경계**를 고정한다.

고정하는 불변조건:
  ① period ≠ available_at (§14의 핵심 요구 — 섞이면 PIT가 무의미해진다)
  ② 미확인 출처가 조용히 통과하지 않는다 (경고가 결과를 따라다닌다)
  ③ 확인된 금지만 차단한다 (미확인에서 막으면 돌아가던 분석이 전부 멈춘다)
  ④ provider가 값을 임의로 고르지 않는다 (대조는 P0-07의 몫)
  ⑤ 외부 객체가 도메인으로 새지 않는다
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.data.governance.source_registry import UNVERIFIED  # noqa: E402
from engine.data.providers.base import (  # noqa: E402
    METRIC_TO_INPUT_FIELD, METRICS, FinancialFact, FinancialProvider,
    ProviderGovernanceError, ProviderResult,
)
from engine.pipeline import AnalysisInputs  # noqa: E402


def fact(**kw):
    base = dict(
        entity="BSX", metric="revenue", fiscal_year=2025, value=20_074_000_000.0,
        unit="currency_amount", currency="USD",
        period_start="2025-01-01", period_end="2025-12-31",
        available_at="2026-02-18", source="SEC XBRL us-gaap:Revenues",
        source_key="sec_edgar", retrieved_at="2026-08-19",
    )
    base.update(kw)
    return FinancialFact(**base)


class _StubProvider(FinancialProvider):
    source_key = "sec_edgar"

    def fetch_annual_financials(self, entity, metrics=None, fiscal_years=None):
        return self._result(entity, [fact(entity=entity)], "2026-08-19")


class _VendorProvider(_StubProvider):
    source_key = "alpha_vantage"

    def fetch_annual_financials(self, entity, metrics=None, fiscal_years=None):
        return self._result(
            entity,
            [fact(entity=entity, source_key="alpha_vantage",
                  source="Alpha Vantage INCOME_STATEMENT")],
            "2026-08-19",
        )


# ── ① period ≠ available_at ──────────────────────────────────────────────
def test_available_at_before_period_end_is_rejected():
    """기간이 끝나기 전에 그 기간 실적이 공시될 수는 없다."""
    with pytest.raises(ValueError, match="공시일"):
        fact(available_at="2025-06-30")          # 기간종료 2025-12-31보다 앞섬


def test_period_and_available_at_are_distinct_fields():
    f = fact()
    assert f.period_end == "2025-12-31"
    assert f.available_at == "2026-02-18"
    assert f.available_at != f.period_end


def test_available_at_cannot_be_silently_blank():
    """빈칸을 오늘 날짜로 자동 보정하면 PIT 검증이 거짓이 된다."""
    with pytest.raises(ValueError, match="추측으로 채우지 않는다"):
        fact(available_at="  ")


# ── ② 미확인이 조용히 통과하지 않는다 ────────────────────────────────────
def test_unverified_source_attaches_warning_to_every_result():
    r = _VendorProvider().fetch_annual_financials("BSX")
    assert r.governance["decision"] == UNVERIFIED
    assert any("출처 거버넌스 미확인" in x for x in r.limitations)
    assert any("2차 출처" in x for x in r.limitations)


def test_verified_primary_source_has_no_governance_warning():
    r = _StubProvider().fetch_annual_financials("BSX")
    assert r.governance["decision"] == "ALLOWED"
    assert not any("거버넌스 미확인" in x for x in r.limitations)
    assert not any("2차 출처" in x for x in r.limitations)


def test_governance_travels_with_the_result_into_serialized_form():
    """ledger·리포트까지 따라가지 않으면 경고가 사라진다."""
    d = _VendorProvider().fetch_annual_financials("BSX").as_dict()
    assert d["governance"]["decision"] == UNVERIFIED
    assert d["limitations"]


# ── ③ 확인된 금지만 차단한다 ─────────────────────────────────────────────
def test_unverified_does_not_block_construction():
    """
    현재 등록된 6건 중 4건이 미확인이다. 여기서 막으면 돌아가던 스크리닝이
    전부 멈춘다 — 막지 않되 반드시 보이게 한다.
    """
    p = _VendorProvider()
    assert p.governance["decision"] == UNVERIFIED


def test_verified_prohibited_purpose_blocks_construction():
    class _Redistributor(_StubProvider):
        source_key = "web_research"
        default_purpose = "raw_redistribution"   # 등록부에서 확인된 금지

    with pytest.raises(ProviderGovernanceError, match="PROHIBITED"):
        _Redistributor()


def test_provider_without_source_key_is_rejected():
    class _Nameless(FinancialProvider):
        def fetch_annual_financials(self, entity, metrics=None, fiscal_years=None):
            return None

    with pytest.raises(ValueError, match="source_key"):
        _Nameless()


# ── ④ provider가 값을 임의로 고르지 않는다 ───────────────────────────────
def test_conflicting_values_for_same_year_raise_instead_of_overwriting():
    r = ProviderResult(
        source_key="sec_edgar", entity="BSX",
        facts=[fact(value=100.0), fact(value=200.0)],
        governance={"decision": "ALLOWED"}, retrieved_at="2026-08-19",
    )
    with pytest.raises(ValueError, match="대조·선택은 reconcile"):
        r.to_series("revenue")


def test_identical_duplicates_are_not_treated_as_conflict():
    r = ProviderResult(
        source_key="sec_edgar", entity="BSX", facts=[fact(), fact()],
        governance={"decision": "ALLOWED"}, retrieved_at="2026-08-19",
    )
    assert r.to_series("revenue") == {2025: 20_074_000_000.0}


# ── ⑤ 도메인 연결 ────────────────────────────────────────────────────────
def test_metric_names_map_onto_real_analysis_inputs_fields():
    """이름이 어긋나면 조용히 빈 딕셔너리가 들어가 CAGR이 틀린다."""
    fields = set(AnalysisInputs.__dataclass_fields__)
    for metric, field_name in METRIC_TO_INPUT_FIELD.items():
        assert field_name in fields, (metric, field_name)
    assert set(METRICS) == set(METRIC_TO_INPUT_FIELD)


def test_series_and_filing_dates_feed_analysis_inputs_shape():
    r = _StubProvider().fetch_annual_financials("BSX")
    assert r.to_series("revenue") == {2025: 20_074_000_000.0}
    assert r.available_at_by_year("revenue") == {2025: "2026-02-18"}


def test_unknown_metric_is_rejected_at_both_ends():
    with pytest.raises(ValueError, match="알 수 없는 지표"):
        fact(metric="ebitda")
    r = _StubProvider().fetch_annual_financials("BSX")
    with pytest.raises(ValueError, match="알 수 없는 지표"):
        r.to_series("ebitda")


def test_unregistered_source_key_is_rejected_on_the_fact_itself():
    with pytest.raises(KeyError, match="등록되지 않은 출처"):
        fact(source_key="bloomberg_terminal")


def test_result_never_carries_external_library_objects():
    """
    §1.8: 외부 라이브러리 객체를 IRS 전체에 노출하지 않는다. 원본은 `raw_ref`
    문자열 참조로만 남고, facts는 전부 IRS 자체 타입이어야 한다.
    """
    r = _StubProvider().fetch_annual_financials("BSX")
    assert all(isinstance(f, FinancialFact) for f in r.facts)
    assert isinstance(r.raw_ref, str)
    import json
    json.dumps(r.as_dict())          # 직렬화 불가 객체가 섞여 있으면 실패한다


def test_coverage_reports_limitations_rather_than_hiding_them():
    c = _VendorProvider().fetch_annual_financials("BSX").coverage()
    assert c["metrics"] == ["revenue"] and c["fiscal_years"] == [2025]
    assert c["governance_decision"] == UNVERIFIED
    assert c["limitations"]
