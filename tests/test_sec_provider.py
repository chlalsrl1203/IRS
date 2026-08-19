"""
P0-03 SEC Provider 테스트 — **네트워크를 타지 않는다**(합성 companyfacts 주입).

# SOURCE:
https://github.com/dgunning/edgartools

# METHOD:
REIMPLEMENT — 가져온 설계는 XBRL 태그 표준화(지표별 우선순위)와 어댑터 경계뿐.
테스트도 그 두 가지가 실제로 작동하는지를 고정한다.

고정하는 불변조건:
  ① 태그 우선순위가 실제로 작동한다 (us-gaap 우선, 없으면 ifrs-full)
  ② 값을 못 찾으면 0으로 채우지 않고 limitations에 남긴다
  ③ 분기·반기가 연간으로 섞이지 않는다
  ④ 같은 연도가 여러 번 나오면 최초 공시본(min filed)을 택한다
  ⑤ 시점(instant) 지표가 기간 규칙에 걸려 통째로 사라지지 않는다
  ⑥ capex 부호를 뒤집지 않는다 (FCF = OCF − capex)
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.data.providers.base import FinancialFact  # noqa: E402
from engine.data.providers.sec import (  # noqa: E402
    INSTANT_METRICS, METRIC_TAGS, SecCompanyFactsProvider,
)
from engine.data.providers.base import METRICS  # noqa: E402


def unit(val, start, end, filed, form="10-K"):
    d = {"val": val, "end": end, "filed": filed, "form": form}
    if start:
        d["start"] = start
    return d


def facts(**tags):
    """{taxonomy: {tag: {units: {USD: [...]}}}} 형태의 합성 companyfacts."""
    out = {}
    for key, entries in tags.items():
        taxonomy, tag, unit_name = key.split("__")
        out.setdefault(taxonomy, {}).setdefault(tag, {"units": {}})
        out[taxonomy][tag]["units"][unit_name] = entries
    return {"facts": out}


def provider(facts_json, cik="0000885725"):
    return SecCompanyFactsProvider(
        fetch_facts=lambda c, ua=None: facts_json,
        resolve_cik=lambda t, ua=None: cik,
    )


ANNUAL_2025 = [unit(20_074_000_000, "2025-01-01", "2025-12-31", "2026-02-18")]


# ── ① 태그 우선순위 ──────────────────────────────────────────────────────
def test_preferred_tag_wins_when_multiple_are_present():
    f = facts(
        **{"us-gaap__Revenues__USD": [unit(1, "2025-01-01", "2025-12-31", "2026-02-18")],
           "us-gaap__RevenueFromContractWithCustomerExcludingAssessedTax__USD":
               [unit(999, "2025-01-01", "2025-12-31", "2026-02-18")]}
    )
    r = provider(f).fetch_annual_financials("BSX", metrics=["revenue"],
                                            retrieved_at="2026-08-19")
    assert r.to_series("revenue") == {2025: 999.0}       # 우선순위 1번이 이긴다
    assert "RevenueFromContract" in r.facts[0].source


def test_foreign_filer_ifrs_tag_is_found_when_us_gaap_absent():
    """
    태그를 하나로 고정하면 외국 발행사(20-F/ifrs-full)에서 조용히 빈 결과가
    나온다 — SAP·BABA·ONON이 여기 걸린다.
    """
    f = facts(**{"ifrs-full__Revenue__CHF":
                 [unit(3_014_000_000, "2025-01-01", "2025-12-31", "2026-03-10", "20-F")]})
    r = provider(f).fetch_annual_financials("ONON", metrics=["revenue"],
                                            retrieved_at="2026-08-19")
    assert r.to_series("revenue") == {2025: 3_014_000_000.0}
    assert r.facts[0].currency == "CHF"                   # 통화를 USD로 가정하지 않는다


# ── ② 못 찾으면 0으로 채우지 않는다 ──────────────────────────────────────
def test_missing_metric_is_reported_not_zero_filled():
    """0으로 채우면 '값이 0'으로 읽혀 CAGR이 조용히 틀린다."""
    r = provider(facts(**{"us-gaap__Revenues__USD": ANNUAL_2025})).fetch_annual_financials(
        "BSX", metrics=["revenue", "sbc"], retrieved_at="2026-08-19")
    assert r.to_series("sbc") == {}                        # 빈 딕셔너리 — 0이 아니다
    assert any("[미확보] sbc" in x for x in r.limitations)


def test_requested_year_gap_is_reported():
    r = provider(facts(**{"us-gaap__Revenues__USD": ANNUAL_2025})).fetch_annual_financials(
        "BSX", metrics=["revenue"], fiscal_years=[2024, 2025],
        retrieved_at="2026-08-19")
    assert r.to_series("revenue") == {2025: 20_074_000_000.0}
    assert any("[연도 누락]" in x and "2024" in x for x in r.limitations)


def test_unresolved_ticker_returns_empty_with_reason_not_a_guess():
    p = SecCompanyFactsProvider(fetch_facts=lambda c, ua=None: facts(),
                                resolve_cik=lambda t, ua=None: None)
    r = p.fetch_annual_financials("NOTATICKER", retrieved_at="2026-08-19")
    assert r.facts == []
    assert any("[티커 미해결]" in x for x in r.limitations)


# ── ③ 기간 필터 ──────────────────────────────────────────────────────────
def test_quarterly_entries_are_not_treated_as_annual():
    f = facts(**{"us-gaap__Revenues__USD": [
        unit(5_000, "2025-01-01", "2025-03-31", "2025-04-30", "10-Q"),   # 분기
        unit(9_000, "2025-01-01", "2025-06-30", "2026-02-18"),           # 반기 길이
        unit(20_000, "2025-01-01", "2025-12-31", "2026-02-18"),          # 연간
    ]})
    r = provider(f).fetch_annual_financials("BSX", metrics=["revenue"],
                                            retrieved_at="2026-08-19")
    assert r.to_series("revenue") == {2025: 20_000.0}


def test_52_53_week_fiscal_year_is_accepted():
    """330~400일 창은 52/53주 회계연도를 포용해야 한다(AAPL·CSCO류)."""
    f = facts(**{"us-gaap__Revenues__USD":
                 [unit(1_000, "2024-09-29", "2025-09-27", "2025-11-01")]})
    r = provider(f).fetch_annual_financials("X", metrics=["revenue"],
                                            retrieved_at="2026-08-19")
    assert r.to_series("revenue") == {2025: 1_000.0}


# ── ④ 최초 공시본 ────────────────────────────────────────────────────────
def test_earliest_filing_wins_for_the_same_fiscal_year():
    """
    같은 회계연도 수치는 후속 연차보고서에 비교표로 다시 실린다. PIT에서
    의미 있는 것은 **처음 알려진 날**이다(filing_dates와 같은 규칙).
    """
    f = facts(**{"us-gaap__Revenues__USD": [
        unit(20_074, "2025-01-01", "2025-12-31", "2027-02-17"),   # 이듬해 10-K 비교표
        unit(20_074, "2025-01-01", "2025-12-31", "2026-02-18"),   # 최초 공시
    ]})
    r = provider(f).fetch_annual_financials("BSX", metrics=["revenue"],
                                            retrieved_at="2026-08-19")
    assert r.available_at_by_year("revenue") == {2025: "2026-02-18"}


# ── ⑤ 시점(instant) 지표 ─────────────────────────────────────────────────
def test_instant_metric_survives_the_duration_filter():
    """
    자기자본은 구간이 아니라 잔액이라 `start`가 없다. 기간 규칙(330~400일)을
    그대로 적용하면 **통째로 사라진다** — 보험사 경로(is_insurer)가 조용히 죽는다.
    """
    assert "shareholders_equity" in INSTANT_METRICS
    f = facts(**{"us-gaap__StockholdersEquity__USD":
                 [unit(18_000, None, "2025-12-31", "2026-02-18")]})
    r = provider(f).fetch_annual_financials("PGR", metrics=["shareholders_equity"],
                                            retrieved_at="2026-08-19")
    assert r.to_series("shareholders_equity") == {2025: 18_000.0}
    assert r.facts[0].period_start == r.facts[0].period_end == "2025-12-31"


# ── ⑥ 부호 규약 ──────────────────────────────────────────────────────────
def test_capex_sign_is_not_flipped_and_fcf_matches_ledger_convention():
    """
    XBRL의 Payments* 태그는 유출을 **양수**로 보고하고 IRS 규약도 양수다.
    BSX FY2025 실측: OCF 4,534 − capex 876 = FCF 3,658(ledger와 일치).
    이 프로젝트는 capex 부호 사고를 이미 한 번 겪었다.
    """
    f = facts(**{
        "us-gaap__NetCashProvidedByUsedInOperatingActivities__USD":
            [unit(4_534_000_000, "2025-01-01", "2025-12-31", "2026-02-18")],
        "us-gaap__PaymentsToAcquirePropertyPlantAndEquipment__USD":
            [unit(876_000_000, "2025-01-01", "2025-12-31", "2026-02-18")],
    })
    r = provider(f).fetch_annual_financials(
        "BSX", metrics=["operating_cashflow", "capex"], retrieved_at="2026-08-19")
    ocf = r.to_series("operating_cashflow")[2025]
    capex = r.to_series("capex")[2025]
    assert capex > 0
    assert ocf - capex == 3_658_000_000.0


# ── 경계·계약 ────────────────────────────────────────────────────────────
def test_every_domain_metric_has_a_tag_mapping():
    """지표를 늘려놓고 태그를 안 붙이면 그 지표는 영원히 빈 결과가 된다."""
    assert set(METRIC_TAGS) == set(METRICS)


def test_retrieved_at_must_be_supplied_explicitly():
    with pytest.raises(ValueError, match="추측 금지"):
        provider(facts()).fetch_annual_financials("BSX")


def test_unknown_metric_is_rejected():
    with pytest.raises(ValueError, match="태그 매핑이 없는"):
        provider(facts()).fetch_annual_financials("BSX", metrics=["ebitda"],
                                                  retrieved_at="2026-08-19")


def test_result_is_typed_domain_objects_and_records_which_tag_was_used():
    r = provider(facts(**{"us-gaap__Revenues__USD": ANNUAL_2025})).fetch_annual_financials(
        "BSX", metrics=["revenue"], retrieved_at="2026-08-19")
    assert all(isinstance(f, FinancialFact) for f in r.facts)
    assert r.governance["used_tags"]["revenue"] == ["us-gaap:Revenues (USD)"]
    assert r.raw_ref.startswith("https://data.sec.gov/api/xbrl/companyfacts/")
    assert r.governance["decision"] == "ALLOWED"      # SEC는 1차 확인 완료


def test_long_series_spanning_a_tag_change_is_not_silently_truncated():
    """
    ⚠️ 실제 결함의 회귀 테스트. BSX 실측에서 FY2015 매출이 통째로 사라졌다 —
    ASC 606(2018) 전후로 회사가 쓰는 태그가 갈리는데 "첫 태그에서 멈춤"이
    그 구간을 버렸기 때문이다. 긴 시계열은 한 태그로 덮이지 않는다.
    """
    f = facts(**{
        "us-gaap__RevenueFromContractWithCustomerExcludingAssessedTax__USD":
            [unit(20_000, "2025-01-01", "2025-12-31", "2026-02-18")],
        "us-gaap__Revenues__USD":
            [unit(7_477, "2015-01-01", "2015-12-31", "2016-02-23")],
    })
    r = provider(f).fetch_annual_financials("BSX", metrics=["revenue"],
                                            retrieved_at="2026-08-19")
    assert r.to_series("revenue") == {2015: 7_477.0, 2025: 20_000.0}
    # 섞였다는 사실을 숨기지 않는다 — 정의가 구간마다 다를 수 있다
    assert any("[태그 혼재]" in x for x in r.limitations)
    src = {f.fiscal_year: f.source for f in r.facts}
    assert "Revenues" in src[2015] and "RevenueFromContract" in src[2025]
