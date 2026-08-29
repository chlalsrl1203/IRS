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


# ── PHASE 3 (2026-08-21): capex 정의 우선순위 ────────────────────────────
def _facts(*tag_series):
    """{tag: {fy: val}} -> 합성 companyfacts."""
    facts = {}
    for tag, series in tag_series:
        units = [{"form": "10-K", "start": f"{fy}-01-01", "end": f"{fy}-12-31",
                  "filed": f"{fy + 1}-02-15", "val": v} for fy, v in series.items()]
        facts[tag] = {"units": {"USD": units}}
    return {"facts": {"us-gaap": facts}}


def _fetch(facts, years, metrics=("capex",)):
    from engine.data.providers.sec import SecCompanyFactsProvider
    p = SecCompanyFactsProvider(
        purpose="internal_research",
        fetch_facts=lambda cik, ua=None: facts,
        resolve_cik=lambda t, ua=None: "0000000000")
    return p.fetch_annual_financials("TEST", metrics=metrics,
                                     fiscal_years=years, retrieved_at="2026-08-21")


def test_broad_capex_definition_wins_over_narrow():
    """
    MCK 실측(2026-08-21): 좁은 정의가 1순위였을 때 FY2026 capex가 436M로 나왔으나
    회사가 보고한 총 자본지출은 745M이었다(−41%). 넓은 태그를 보고하는 4종목
    39개년 전수에서 넓은 정의가 ledger와 100% 일치한다.
    """
    r = _fetch(_facts(
        ("PaymentsToAcquirePropertyPlantAndEquipment", {2024: 431.0}),
        ("PaymentsToAcquireProductiveAssets", {2024: 687.0}),
    ), [2024])
    assert [f.value for f in r.facts if f.metric == "capex"] == [687.0]


def test_narrow_capex_is_still_used_when_broad_is_absent():
    """넓은 태그가 없는 종목(31/34)은 동작이 바뀌지 않아야 한다."""
    r = _fetch(_facts(
        ("PaymentsToAcquirePropertyPlantAndEquipment", {2024: 876.0}),
    ), [2024])
    assert [f.value for f in r.facts if f.metric == "capex"] == [876.0]
    assert not any("정의 공존" in m for m in r.limitations)


def test_coexisting_capex_definitions_are_reported_not_silently_resolved():
    """넓은 쪽을 채택하되 두 정의가 공존하고 값이 다르다는 사실을 남긴다."""
    r = _fetch(_facts(
        ("PaymentsToAcquirePropertyPlantAndEquipment", {2024: 431.0}),
        ("PaymentsToAcquireProductiveAssets", {2024: 687.0}),
    ), [2024])
    assert any("정의 공존" in m for m in r.limitations)


def test_separately_tagged_software_capex_is_flagged_not_auto_summed():
    """
    소프트웨어 자본화를 별도 태그로 보고하는 회사(MCK)에서, 넓은 태그가 없는
    연도는 좁은 정의가 채택된다. **자동 합산하지 않는다** - 회사에 따라 유형자산
    취득에 이미 포함됐을 수 있어 이중계상 위험이 있고 관측이 1종목뿐이다.
    누락 가능성은 경고로 드러낸다.
    """
    r = _fetch(_facts(
        ("PaymentsToAcquirePropertyPlantAndEquipment", {2026: 436.0}),
        ("PaymentsToAcquireSoftware", {2026: 309.0}),
    ), [2026])
    vals = [f.value for f in r.facts if f.metric == "capex"]
    assert vals == [436.0], "소프트웨어를 자동 합산하면 안 된다"
    assert any("소프트웨어 별도 보고" in m for m in r.limitations)


# ── PHASE 5 (2026-08-21): 회계연도 라벨 충돌 ─────────────────────────────
def test_fiscal_year_label_collision_is_reported():
    """
    52/53주 회계연도를 쓰는 회사는 회계연도가 1월 초에 끝나 `int(end[:4])`가
    다음 해를 가리킨다. CDNS 실측(2026-08-21): 2019-12-29~2021-01-02(회사 기준
    FY2020)이 fy=2021로 잡혀 provider 출력이 ledger 대비 **한 해씩 밀린다**
    (불일치 7~16%). 두 기간이 같은 라벨로 충돌하면 min(filed) 규칙상 이른
    회계연도가 이기고 늦은 쪽이 조용히 사라진다.
    """
    facts = {"facts": {"us-gaap": {"Revenues": {"units": {"USD": [
        # 회사 기준 FY2015 - 1월 초에 끝나 int(end[:4])가 2016을 가리킨다
        {"form": "10-K", "start": "2015-01-04", "end": "2016-01-02",
         "filed": "2016-02-20", "val": 100.0},
        # 회사 기준 FY2016 - 같은 2016 라벨로 충돌한다
        {"form": "10-K", "start": "2016-01-03", "end": "2016-12-31",
         "filed": "2017-02-20", "val": 200.0},
    ]}}}}}
    r = _fetch(facts, [2015, 2016], metrics=("revenue",))
    assert any("회계연도 라벨 충돌" in m for m in r.limitations)
    # 충돌 시 min(filed)가 이긴다 - 늦은 회계연도가 조용히 사라진다
    vals = {f.fiscal_year: f.value for f in r.facts if f.metric == "revenue"}
    assert vals == {2016: 100.0}, vals


def test_no_collision_warning_for_normal_calendar_years():
    r = _fetch(_facts(("Revenues", {2023: 10.0, 2024: 20.0})),
               [2023, 2024], metrics=("revenue",))
    assert not any("회계연도 라벨 충돌" in m for m in r.limitations)


def test_relabeling_is_not_done_automatically():
    """
    자동 재라벨링은 하지 않는다 - 회계연도 규약이 회사마다 다르고(CDNS는 1월 초
    종료를 전년으로, GEN은 3월 말 종료를 당해로) 관측이 2종목뿐이다(§21 LEVEL 1).
    경고만 내고 값은 종료일 연도 그대로 둔다.
    """
    facts = {"facts": {"us-gaap": {"Revenues": {"units": {"USD": [
        {"form": "10-K", "start": "2015-01-04", "end": "2016-01-02",
         "filed": "2016-02-20", "val": 100.0},
    ]}}}}}
    r = _fetch(facts, [2015, 2016], metrics=("revenue",))
    vals = {f.fiscal_year: f.value for f in r.facts if f.metric == "revenue"}
    assert 2016 in vals and 2015 not in vals, "종료일 연도 규약이 조용히 바뀌었다"


# ── 통화/단위 혼재 (RQ-005, 2026-08-26) ─────────────────────────────────
#
# 中 발행사(PDD·TCOM 실측)는 같은 태그를 CNY와 USD로 **동시 보고**한다.
# provider의 선택 루프는 `if fy not in picked`라 JSON에 먼저 나온 단위가 이기는데
# 그 순서에는 아무 의미가 없다. 두 위험이 다르므로 경고도 분리한다.
def test_dual_currency_reporting_is_disclosed_even_when_series_is_consistent():
    """
    (a) 한 단위로 일관되게 채택된 경우 - 비율 지표(Gap)는 옳지만 **절대값을
    쓰는 경로**는 통화를 알아야 한다. v3.67 규모 조건부 상한이 정확히 그
    경로이고, TCOM ledger가 CNY 값에 currency="USD" 라벨을 달고 있었다.
    """
    f = facts(**{
        "us-gaap__Revenues__CNY": [
            unit(431_845_713_000, "2025-01-01", "2025-12-31", "2026-02-18")],
        "us-gaap__Revenues__USD": [
            unit(59_978_571_250, "2025-01-01", "2025-12-31", "2026-02-18")],
    })
    r = provider(f).fetch_annual_financials(
        "PDD", metrics=["revenue"], fiscal_years=[2025], retrieved_at="2026-08-26")
    lim = " ".join(r.limitations)
    assert "복수 단위 보고" in lim
    assert "CNY" in lim and "USD" in lim
    assert "단위 혼재 - 심각" not in lim, "일관된 시계열을 심각으로 올리면 안 된다"


def test_series_spanning_two_units_is_flagged_as_severe():
    """
    (b) 한 시계열 안에서 연도별로 통화가 갈리면 CAGR이 7배 단위로 망가진다 -
    조용히 넘기지 않는다. CNY가 2024년만, USD가 2025년만 있는 경우.
    """
    f = facts(**{
        "us-gaap__Revenues__CNY": [
            unit(393_836_097_000, "2024-01-01", "2024-12-31", "2025-02-18")],
        "us-gaap__Revenues__USD": [
            unit(59_978_571_250, "2025-01-01", "2025-12-31", "2026-02-18")],
    })
    r = provider(f).fetch_annual_financials(
        "PDD", metrics=["revenue"], fiscal_years=[2024, 2025],
        retrieved_at="2026-08-26")
    lim = " ".join(r.limitations)
    assert "단위 혼재 - 심각" in lim
    assert "2024" in lim and "2025" in lim


def test_single_currency_company_gets_no_unit_warning():
    r = provider(facts(**{"us-gaap__Revenues__USD": ANNUAL_2025})).fetch_annual_financials(
        "BSX", metrics=["revenue"], fiscal_years=[2025], retrieved_at="2026-08-26")
    lim = " ".join(r.limitations)
    assert "복수 단위 보고" not in lim and "단위 혼재" not in lim


# ── public_float_by_year — 대규모 스크리닝 전용 시총 근사치(2026-08-29) ────
from engine.data.providers.sec import public_float_by_year  # noqa: E402


def _pf_facts(entries):
    return {"facts": {"dei": {"EntityPublicFloat": {"units": {"USD": entries}}}}}


def test_public_float_reads_dei_instant_tag():
    """시점 지표라 `start` 없이 `end`만으로도 연도가 잡혀야 한다."""
    f = _pf_facts([
        {"val": 2_830_067_000_000, "end": "2022-03-25", "filed": "2022-10-28",
         "form": "10-K"},
    ])
    out = public_float_by_year(
        "AAPL", retrieved_at="2026-08-29",
        fetch_facts=lambda c, ua=None: f, resolve_cik=lambda t, ua=None: "0000320193")
    assert out == {2022: 2_830_067_000_000.0}


def test_public_float_missing_tag_returns_empty_not_zero():
    """20-F 외국 발행사 등 태그 자체가 없으면 0이 아니라 빈 dict(추측 금지)."""
    out = public_float_by_year(
        "TCOM", retrieved_at="2026-08-29",
        fetch_facts=lambda c, ua=None: {"facts": {"us-gaap": {}}},
        resolve_cik=lambda t, ua=None: "0001529192")
    assert out == {}


def test_public_float_unresolved_ticker_returns_empty():
    out = public_float_by_year(
        "NOPE", retrieved_at="2026-08-29", resolve_cik=lambda t, ua=None: None)
    assert out == {}


def test_public_float_requires_retrieved_at():
    with pytest.raises(ValueError):
        public_float_by_year("AAPL", retrieved_at=None)


def test_public_float_earliest_filing_wins_for_same_fiscal_year():
    """다른 SEC 지표들과 동일한 규약 - 같은 회계연도가 여러 번 나오면 최초본."""
    f = _pf_facts([
        {"val": 999, "end": "2024-03-01", "filed": "2025-02-01", "form": "10-K"},
        {"val": 111, "end": "2024-03-01", "filed": "2024-10-01", "form": "10-K"},
    ])
    out = public_float_by_year(
        "X", retrieved_at="2026-08-29",
        fetch_facts=lambda c, ua=None: f, resolve_cik=lambda t, ua=None: "1")
    assert out == {2024: 111.0}


def test_public_float_not_in_financial_fact_metrics():
    """`run_analysis()` 경로(FinancialFact/METRICS)를 오염시키지 않는다."""
    assert "public_float" not in METRICS
    assert "public_float" not in METRIC_TAGS
