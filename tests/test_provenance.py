"""
Provenance 테스트 - 네트워크 없이 순수 함수만.

핵심: (1) 빈칸을 추측으로 채우지 않는지, (2) 못 찾은 것을 '없음'이 아니라
'누락'으로 드러내는지, (3) 기존 34종목이 PROVENANCE_UNKNOWN으로 남는지.
"""

import pytest

from engine.provenance import (
    PROVENANCE_UNKNOWN,
    SOURCE_KINDS,
    ValueProvenance,
    build_provenance_record,
    provenance_coverage,
    provenance_from_sec_facts,
)


def make_prov(**overrides):
    base = dict(
        field_path="revenue_by_year[2025]",
        value=20074000000,
        unit="currency_amount",
        currency="USD",
        period="2025-01-01~2025-12-31",
        source="SEC XBRL us-gaap:Revenues",
        source_kind="sec_xbrl",
        publication_date="2026-02-17",
        retrieval_date="2026-08-15",
    )
    base.update(overrides)
    return ValueProvenance(**base)


def sec_facts(entries, taxonomy="us-gaap", tag="Revenues", unit="USD"):
    return {"facts": {taxonomy: {tag: {"units": {unit: entries}}}}}


def annual(start, end, filed, val, form="10-K"):
    return {"start": start, "end": end, "filed": filed, "val": val, "form": form}


# ──────────────────────────────────────────────────────────────────
# §6이 요구한 7개 축
# ──────────────────────────────────────────────────────────────────

def test_records_all_seven_provenance_axes():
    p = make_prov()
    for axis in ("source", "publication_date", "period", "value",
                 "unit", "currency", "retrieval_date"):
        assert getattr(p, axis) is not None, f"{axis}가 없다"


def test_unit_and_currency_are_separate():
    """
    단위와 통화를 뭉뚱그리지 않는다 - 비율에는 통화 개념이 없고, 이 프로젝트는
    단위 사고를 두 번 겪었다(RAR 100배, 실질/명목 EPS).
    """
    ratio = make_prov(field_path="demand_sensitivity_pct", value=0.15,
                      unit="ratio", currency=None, source_kind="analyst_input",
                      publication_date=None)
    assert ratio.unit == "ratio" and ratio.currency is None


def test_empty_required_axis_rejected():
    for f in ("field_path", "unit", "period", "source", "retrieval_date"):
        with pytest.raises(ValueError, match=f):
            make_prov(**{f: "  "})


def test_unknown_source_kind_rejected():
    with pytest.raises(ValueError, match="알 수 없는 출처 종류"):
        make_prov(source_kind="rumor")
    assert "web_research" in SOURCE_KINDS   # 가장 약한 출처도 분류는 된다


def test_publication_date_is_never_auto_filled_with_today():
    """
    ⚠️ 공개일을 조회일로 위장하면 PIT 검증이 통째로 무의미해진다.
    없으면 None으로 남아야 하고, 자동으로 오늘 날짜가 들어가면 안 된다.
    """
    p = make_prov(publication_date=None, source_kind="analyst_input")
    assert p.publication_date is None
    assert p.retrieval_date == "2026-08-15"


# ──────────────────────────────────────────────────────────────────
# 누락을 숨기지 않는다
# ──────────────────────────────────────────────────────────────────

def test_missing_fields_are_reported_not_omitted():
    """
    빠진 것을 적지 않으면 커버리지가 실제보다 높아 보인다(ETF 엔진이 ERS 항목
    제외 시 사실을 남기는 것과 동일 원칙).
    """
    rec = build_provenance_record([make_prov()], "2026-08-15",
                                  missing_fields=["revenue_by_year[2015]"])
    assert rec["n_covered"] == 1
    assert rec["n_missing"] == 1
    assert rec["missing_fields"] == ["revenue_by_year[2015]"]


def test_empty_record_is_unknown_not_recorded():
    rec = build_provenance_record([], "2026-08-15", missing_fields=["a", "b"])
    assert rec["status"] == PROVENANCE_UNKNOWN
    assert rec["n_missing"] == 2


# ──────────────────────────────────────────────────────────────────
# SEC 자동 생성
# ──────────────────────────────────────────────────────────────────

def test_generates_from_sec_with_period_and_publication_date():
    rec = provenance_from_sec_facts(
        sec_facts([annual("2025-01-01", "2025-12-31", "2026-02-17", 20074000000)]),
        "BSX", "2026-08-15", [2025],
    )
    e = rec["entries"][0]
    assert e["value"] == 20074000000
    assert e["period"] == "2025-01-01~2025-12-31"
    assert e["publication_date"] == "2026-02-17"
    assert e["source_kind"] == "sec_xbrl"
    assert e["currency"] == "USD"


def test_earliest_publication_wins_for_repeated_year():
    """같은 회계연도가 비교표로 반복 등장하면 최초 공시본을 쓴다(PIT 일관성)."""
    rec = provenance_from_sec_facts(
        sec_facts([
            annual("2024-01-01", "2024-12-31", "2026-02-17", 999),   # 비교표
            annual("2024-01-01", "2024-12-31", "2025-02-18", 100),   # 원본
        ]),
        "X", "2026-08-15", [2024],
    )
    assert rec["entries"][0]["publication_date"] == "2025-02-18"
    assert rec["entries"][0]["value"] == 100


def test_years_not_found_are_listed_as_missing():
    """XBRL 태깅 이전 연도는 실제로 안 잡힌다(BSX FY2015이 그 사례)."""
    rec = provenance_from_sec_facts(
        sec_facts([annual("2025-01-01", "2025-12-31", "2026-02-17", 1)]),
        "X", "2026-08-15", [2015, 2025],
    )
    assert rec["missing_fields"] == ["revenue_by_year[2015]"]
    assert rec["n_covered"] == 1


def test_no_matching_tag_returns_empty_not_fabricated():
    """
    ⚠️ 태그를 못 찾았을 때 다른 태그 값으로 대충 채우면 '이 값은 Revenues에서
    왔다'는 허위 기록이 남는다. 빈 결과 + 전건 누락이 정답이다.
    """
    rec = provenance_from_sec_facts(
        sec_facts([annual("2025-01-01", "2025-12-31", "2026-02-17", 1)],
                  tag="SomeUnrelatedTag"),
        "X", "2026-08-15", [2025],
    )
    assert rec["status"] == PROVENANCE_UNKNOWN
    assert rec["entries"] == []
    assert rec["missing_fields"] == ["revenue_by_year[2025]"]


def test_ifrs_foreign_issuer_currency_is_captured():
    """PDD가 CNY인데 ledger에 표시가 없던 M-6 문제를 구조적으로 막는다."""
    rec = provenance_from_sec_facts(
        sec_facts([annual("2025-01-01", "2025-12-31", "2026-04-29", 500)],
                  taxonomy="ifrs-full", tag="Revenue", unit="CNY"),
        "PDD", "2026-08-15", [2025],
    )
    assert rec["entries"][0]["currency"] == "CNY"


def test_quarterly_entries_excluded():
    rec = provenance_from_sec_facts(
        sec_facts([
            annual("2025-01-01", "2025-03-31", "2025-05-01", 5, form="10-Q"),
            annual("2025-01-01", "2025-12-31", "2026-02-17", 20, form="10-K"),
        ]),
        "X", "2026-08-15", [2025],
    )
    assert len(rec["entries"]) == 1 and rec["entries"][0]["value"] == 20


# ──────────────────────────────────────────────────────────────────
# 기존 34종목은 UNKNOWN으로 남는다 (§6)
# ──────────────────────────────────────────────────────────────────

def test_legacy_ledger_reports_unknown_and_keeps_free_text_sources():
    """
    ⚠️ 소급 생성하지 않는다 - 지금 조회한 값을 그때 값인 양 붙이면 허위 출처다.
    자유문자열 data_sources는 참고로 남기되 '출처 기록 있음'으로 세지 않는다.
    """
    legacy = {
        "meta": {"ticker": "CDNS"},
        "inputs": {"data_sources": ["Alpha Vantage (2026-07-25)"]},
    }
    cov = provenance_coverage(legacy)
    assert cov["status"] == PROVENANCE_UNKNOWN
    assert cov["n_covered"] == 0
    assert cov["legacy_data_sources"] == ["Alpha Vantage (2026-07-25)"]


def test_recorded_ledger_reports_coverage():
    rec = build_provenance_record([make_prov()], "2026-08-15", ["x"])
    led = {"meta": {"ticker": "BSX", "provenance": rec}, "inputs": {}}
    cov = provenance_coverage(led)
    assert cov["status"] == "PROVENANCE_RECORDED"
    assert cov["n_covered"] == 1 and cov["n_missing"] == 1


# v3.50 34종목은 P0-08(2026-08-19) 이전 분석이라 원자료 스냅샷이 없다 -
# 소급 생성하면 §6 위반(허위 출처)이므로 전부 PROVENANCE_UNKNOWN으로 남아야
# 한다. 이후 **처음부터** provenance를 채워 분석한 신규 ledger는 소급이
# 아니라 정당한 신규 분석이라 이 규칙 대상이 아니다 - BSX 거짓탈락
# (`KNOWN_SCREENER_FALSE_REJECTIONS`)·TCOM 통화라벨(`KNOWN_CURRENCY_LABEL_
# DIVERGENCE`)과 동일한 "알려진 예외" 패턴으로 등록한다.
KNOWN_PROVENANCE_RECORDED_LEDGERS = {"CROX", "SIGI", "OKTA", "MEDP", "RYAN", "FIX", "NBIX", "NXT", "PATH", "PCTY", "EXEL", "PINS", "ROKU", "HLNE", "FIVE"}  # 2026-09-01/03, 분석 시점에 확보


def test_all_existing_ledgers_are_provenance_unknown():
    """
    저장소의 현재 상태를 사실 그대로 고정한다 - 누군가 소급 생성하면 여기서
    깨지고, 그때 §6 위반인지 정당한 신규 분석인지 검토하게 된다.
    """
    import glob
    import json

    for path in sorted(glob.glob("ledger/*.json")):
        led = json.load(open(path, encoding="utf-8"))
        ticker = led["meta"]["ticker"]
        if ticker in KNOWN_PROVENANCE_RECORDED_LEDGERS:
            assert provenance_coverage(led)["status"] != PROVENANCE_UNKNOWN, (
                f"{ticker}는 알려진 예외 목록에 있는데 실제로는 여전히 "
                f"UNKNOWN이다 - 목록에서 빼야 한다"
            )
            continue
        assert provenance_coverage(led)["status"] == PROVENANCE_UNKNOWN, (
            f"{path}에 provenance가 소급 생성됐다 - §6은 이를 금지한다. "
            f"정당한 신규 분석이면 KNOWN_PROVENANCE_RECORDED_LEDGERS에 추가할 것"
        )
