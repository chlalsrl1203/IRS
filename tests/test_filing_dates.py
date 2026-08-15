"""
Filing Dates 테스트 - 네트워크 없이 순수 함수만 검증한다.

`annual_filing_dates()`를 순수 함수로 분리한 이유가 이것이다 - 테스트가
SEC 응답에 의존하면 오프라인/장애 시 CI가 깨진다.

픽스처는 실제 companyfacts 구조를 그대로 축소한 것이다(DDOG 실데이터로
구조 확인 후 작성).
"""

import pytest

from engine.filing_dates import (
    ANNUAL_FORMS,
    annual_filing_dates,
    check_lookahead,
)


def facts(entries, taxonomy="us-gaap", tag="Revenues", unit="USD"):
    return {"facts": {taxonomy: {tag: {"units": {unit: entries}}}}}


def annual(start, end, filed, form="10-K", val=100):
    return {"start": start, "end": end, "filed": filed, "form": form, "val": val}


# ──────────────────────────────────────────────────────────────────
# 최초 제출일 선택
# ──────────────────────────────────────────────────────────────────

def test_picks_earliest_filing_for_a_fiscal_year():
    """
    같은 회계연도 수치는 여러 연차보고서에 반복 등장한다(비교표). PIT에서
    의미 있는 것은 **처음 공개된 날**이므로 최소값을 택해야 한다.
    """
    fd = annual_filing_dates(facts([
        annual("2024-01-01", "2024-12-31", "2026-02-20"),   # FY2026 10-K의 비교표
        annual("2024-01-01", "2024-12-31", "2025-02-18"),   # FY2024 10-K 원본
    ]))
    assert fd == {2024: "2025-02-18"}


def test_fiscal_year_keyed_by_period_end_year():
    """
    ledger의 revenue_by_year가 회계연도 종료 기준으로 키를 매기므로 동일하게
    맞춘다(2026-01-31 종료 -> FY2026).
    """
    fd = annual_filing_dates(facts([
        annual("2025-02-01", "2026-01-31", "2026-03-06"),
    ]))
    assert fd == {2026: "2026-03-06"}


def test_quarterly_filings_are_excluded():
    """10-Q가 섞이면 연차 제출일이 실제보다 이르게 잡혀 PIT 검사가 무력해진다."""
    fd = annual_filing_dates(facts([
        annual("2024-01-01", "2024-03-31", "2024-05-01", form="10-Q"),
        annual("2024-01-01", "2024-12-31", "2025-02-18"),
    ]))
    assert fd == {2024: "2025-02-18"}


def test_partial_year_durations_are_excluded():
    """반기·전환기 같은 비연간 구간은 제외한다(330~400일만 인정)."""
    fd = annual_filing_dates(facts([
        annual("2024-01-01", "2024-06-30", "2024-08-01"),   # 반기 - 제외
        annual("2024-01-01", "2024-12-31", "2025-02-18"),   # 연간 - 채택
    ]))
    assert fd == {2024: "2025-02-18"}


def test_52_53_week_fiscal_years_are_accepted():
    """소매업 등의 52/53주 회계연도가 배제되면 안 된다."""
    fd = annual_filing_dates(facts([
        annual("2024-02-04", "2025-02-01", "2025-03-20"),   # 363일
    ]))
    assert fd == {2025: "2025-03-20"}


def test_foreign_issuer_20f_and_ifrs_taxonomy_recognized():
    """
    SAP·BABA·ONON 같은 외국 발행사는 20-F에 ifrs-full 태그를 쓴다. 태그를
    하나로 고정했다면 조용히 빈 결과가 나왔을 지점이다.
    """
    fd = annual_filing_dates(facts(
        [annual("2025-01-01", "2025-12-31", "2026-04-29", form="20-F")],
        taxonomy="ifrs-full", tag="Revenue", unit="CNY",
    ))
    assert fd == {2025: "2026-04-29"}
    assert "20-F" in ANNUAL_FORMS


def test_entries_missing_dates_are_skipped_not_guessed():
    fd = annual_filing_dates(facts([
        {"end": "2024-12-31", "filed": "2025-02-18", "form": "10-K", "val": 1},
        annual("2023-01-01", "2023-12-31", "2024-02-20"),
    ]))
    assert fd == {2023: "2024-02-20"}


def test_multiple_tags_are_merged():
    """제출일은 태그가 아니라 공시의 속성이므로 모든 태그를 훑어야 한다."""
    f = {"facts": {"us-gaap": {
        "Revenues": {"units": {"USD": [annual("2024-01-01", "2024-12-31", "2025-03-01")]}},
        "NetIncomeLoss": {"units": {"USD": [annual("2024-01-01", "2024-12-31", "2025-02-18")]}},
    }}}
    assert annual_filing_dates(f) == {2024: "2025-02-18"}


def test_empty_facts_returns_empty_not_error():
    assert annual_filing_dates({}) == {}
    assert annual_filing_dates({"facts": {}}) == {}


# ──────────────────────────────────────────────────────────────────
# 미래정보 검사
# ──────────────────────────────────────────────────────────────────

def test_lookahead_violation_detected():
    """분석일 이후에 공시된 회계연도를 썼다면 확정적 결함이다."""
    out = check_lookahead({2025: "2026-02-18"}, "2026-01-01", [2025])
    assert out["violations"][0]["fiscal_year"] == 2025
    assert out["violations"][0]["days_after_analysis"] == 48


def test_no_violation_when_filed_before_analysis():
    out = check_lookahead({2025: "2026-02-18"}, "2026-07-25", [2025])
    assert out["violations"] == []


def test_same_day_filing_is_not_a_violation():
    """규칙은 filing_date <= analysis_as_of다 - 당일 공시는 사용 가능하다."""
    out = check_lookahead({2025: "2026-02-18"}, "2026-02-18", [2025])
    assert out["violations"] == []


def test_unknown_years_are_reported_not_assumed_safe():
    """
    ⚠️ 제출일을 못 찾은 연도를 조용히 통과시키면 검증이 실제보다 관대해진다.
    unknown_years로 드러내되 위반으로 단정하지도 않는다.
    """
    out = check_lookahead({2025: "2026-02-18"}, "2026-07-25", [2014, 2015, 2025])
    assert out["unknown_years"] == [2014, 2015]
    assert out["violations"] == []
    assert out["checked_years"] == [2014, 2015, 2025]


def test_string_years_accepted():
    """ledger의 JSON 키는 문자열이므로 그대로 넘어와도 동작해야 한다."""
    out = check_lookahead({2025: "2026-02-18"}, "2026-07-25", ["2025"])
    assert out["violations"] == [] and out["unknown_years"] == []
