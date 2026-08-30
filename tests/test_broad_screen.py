"""
broad_screen.py 테스트 - 순수 로직만 네트워크 없이 고정한다.

fetch_stage1_series는 `fetch_company_facts`를 주입 가능하게 만들지 않았으므로
(운영 스크립트라 daily_screen.py의 `_cached_facts` 같은 얇은 함수 주입 지점이
없다) 여기서는 `public_float_from_facts`/`prefilter_universe`/`build_candidate`/
`_classify_stage1` 같은 순수 함수만 고정한다. companyfacts 단위 네트워크
동작(태그 우선순위·재무지표 파싱)은 tests/test_sec_provider.py가 이미 고정한다.
"""
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from scripts import broad_screen as B  # noqa: E402


# ── 이름 사전필터 ────────────────────────────────────────────────────────
def test_prefilter_drops_obvious_fund_names():
    universe = [
        {"ticker": "AAPL", "cik": "1", "title": "Apple Inc."},
        {"ticker": "SPY", "cik": "2", "title": "SPDR S&P 500 ETF Trust"},
        {"ticker": "XYZFND", "cik": "3", "title": "Some Mutual Fund"},
        {"ticker": "ABCW", "cik": "4", "title": "ABC Acquisition Corp"},
    ]
    kept, dropped = B.prefilter_universe(universe)
    assert dropped == 3
    assert [r["ticker"] for r in kept] == ["AAPL"]


def test_prefilter_does_not_drop_operating_companies_with_incidental_words():
    """'Fund'가 포함된 진짜 운용사 이름 등은 걸러선 안 된다 - 지금은 오탐이 있다는
    것 자체를 문서화만 한다(사전필터는 정확도 무관, 다운스트림이 실제 거름망)."""
    universe = [{"ticker": "TROW", "cik": "1", "title": "T. Rowe Price Group Inc"}]
    kept, dropped = B.prefilter_universe(universe)
    assert dropped == 0
    assert kept == universe


# ── build_candidate ─────────────────────────────────────────────────────
def _series(rev, ocf, capex, pf):
    return {
        "revenue_by_year": rev, "operating_cashflow_by_year": ocf,
        "capex_by_year": capex, "public_float_by_year": pf,
    }


def test_build_candidate_uses_latest_public_float_as_market_cap():
    series = _series(
        rev={y: 100 + y for y in range(2020, 2026)},
        ocf={y: 30 + y for y in range(2020, 2026)},
        capex={y: 5 for y in range(2020, 2026)},
        pf={2023: 900, 2025: 1000, 2024: 950},
    )
    c = B.build_candidate("X", "X Corp", series)
    assert c.market_cap == 1000
    assert "FY2025" in c.note


def test_build_candidate_rejects_nonpositive_base_year_cagr():
    """PODD/ONON 유형 - 기준연도 값이 0 이하면 CAGR 자체가 정의되지 않는다."""
    series = _series(
        rev={y: 100 for y in range(2020, 2026)},
        ocf={2020: -10, 2021: 5, 2022: 10, 2023: 15, 2024: 20, 2025: 25},
        capex={y: 5 for y in range(2020, 2026)},
        pf={2025: 1000},
    )
    with pytest.raises(ValueError, match="프레임워크 부적합"):
        B.build_candidate("X", "X Corp", series)


def test_build_candidate_rejects_nonpositive_fcf0():
    """
    FCF0<=0이면 fcf_cagr_5y 자체가 계산 안 되므로(_window_cagr이 end<=0일 때
    None) 프레임워크 부적합 경로로 먼저 걸린다 - "Model N/A"가 아니라
    "프레임워크 부적합"이 뜨는 게 맞다(build_candidate가 도달 불가능한 분기를
    갖지 않는다는 것 자체를 이 테스트가 확인한다).
    """
    series = _series(
        rev={y: 100 + y for y in range(2020, 2026)},
        ocf={y: 10 for y in range(2020, 2026)},
        capex={y: 50 for y in range(2020, 2026)},   # FCF = 10-50 < 0
        pf={2025: 1000},
    )
    with pytest.raises(ValueError, match="프레임워크 부적합"):
        B.build_candidate("X", "X Corp", series)


def test_build_candidate_rejects_nonpositive_market_cap():
    """public_float 원자료가 0/음수인 이론적 경우 - CAGR 가드를 안 거치므로
    별도 검사가 필요하다."""
    series = _series(
        rev={y: 100 + y for y in range(2020, 2026)},
        ocf={y: 30 + y for y in range(2020, 2026)},
        capex={y: 5 for y in range(2020, 2026)},
        pf={2025: 0},
    )
    with pytest.raises(ValueError, match="Model N/A"):
        B.build_candidate("X", "X Corp", series)


# ── public_float_from_facts 재사용(중복요청 제거 회귀) ─────────────────────
def test_fetch_stage1_series_does_not_double_fetch_companyfacts(monkeypatch):
    """
    2026-08-29 실측 버그의 회귀 테스트 - companyfacts를 재무지표용과
    public_float용으로 각각 요청해 티커당 SEC 호출이 2배였다. 이제
    `fetch_company_facts`가 **정확히 1회**만 불려야 한다.
    """
    calls = {"n": 0}
    facts = {
        "facts": {
            "us-gaap": {
                "Revenues": {"units": {"USD": [
                    {"start": f"{y}-01-01", "end": f"{y}-12-31",
                     "filed": f"{y + 1}-02-01", "val": 100 + y, "form": "10-K"}
                    for y in range(2019, 2026)
                ]}},
                "NetCashProvidedByUsedInOperatingActivities": {"units": {"USD": [
                    {"start": f"{y}-01-01", "end": f"{y}-12-31",
                     "filed": f"{y + 1}-02-01", "val": 30 + y, "form": "10-K"}
                    for y in range(2019, 2026)
                ]}},
                "PaymentsToAcquireProductiveAssets": {"units": {"USD": [
                    {"start": f"{y}-01-01", "end": f"{y}-12-31",
                     "filed": f"{y + 1}-02-01", "val": 5, "form": "10-K"}
                    for y in range(2019, 2026)
                ]}},
            },
            "dei": {"EntityPublicFloat": {"units": {"USD": [
                {"end": "2025-06-30", "filed": "2026-02-01", "val": 1000, "form": "10-K"},
            ]}}},
        }
    }

    def counting_fetch(cik, ua=None):
        calls["n"] += 1
        return facts

    monkeypatch.setattr(B, "fetch_company_facts", counting_fetch)
    series, lim = B.fetch_stage1_series("X", "0000000001", "2026-08-29")
    assert calls["n"] == 1, f"companyfacts를 {calls['n']}번 요청했다(1번이어야 함)"
    assert series is not None
    assert series["public_float_by_year"] == {2025: 1000.0}


def test_fetch_stage1_series_rejects_stale_public_float(monkeypatch):
    """
    ASML 실측 회귀 - public_float 최신값이 오래됐으면(보고의무 축소·중단 추정)
    시총 근사치로 쓰면 안 된다.
    """
    facts = {
        "facts": {
            "us-gaap": {
                "Revenues": {"units": {"USD": [
                    {"start": f"{y}-01-01", "end": f"{y}-12-31",
                     "filed": f"{y + 1}-02-01", "val": 100 + y, "form": "10-K"}
                    for y in range(2019, 2026)
                ]}},
                "NetCashProvidedByUsedInOperatingActivities": {"units": {"USD": [
                    {"start": f"{y}-01-01", "end": f"{y}-12-31",
                     "filed": f"{y + 1}-02-01", "val": 30 + y, "form": "10-K"}
                    for y in range(2019, 2026)
                ]}},
                "PaymentsToAcquireProductiveAssets": {"units": {"USD": [
                    {"start": f"{y}-01-01", "end": f"{y}-12-31",
                     "filed": f"{y + 1}-02-01", "val": 5, "form": "10-K"}
                    for y in range(2019, 2026)
                ]}},
            },
            "dei": {"EntityPublicFloat": {"units": {"USD": [
                {"end": "2009-03-01", "filed": "2009-10-01", "val": 999, "form": "10-K"},
            ]}}},
        }
    }
    monkeypatch.setattr(B, "fetch_company_facts", lambda cik, ua=None: facts)
    series, lim = B.fetch_stage1_series("ASML", "1", "2026-08-29")
    assert series is None
    assert any("public_float 낡음" in x for x in lim)


# ── 1차 스크리닝 "B" 게이트(존속위험) 배선 회귀(2026-08-30) ────────────────
def _facts_with_equity_and_ocf(equity_by_year, ocf_by_year):
    """PODD 이슈를 피하려고 revenue/capex는 항상 정상 데이터로 채운다."""
    years = range(2019, 2026)
    return {
        "facts": {
            "us-gaap": {
                "Revenues": {"units": {"USD": [
                    {"start": f"{y}-01-01", "end": f"{y}-12-31",
                     "filed": f"{y + 1}-02-01", "val": 100 + y, "form": "10-K"}
                    for y in years
                ]}},
                "NetCashProvidedByUsedInOperatingActivities": {"units": {"USD": [
                    {"start": f"{y}-01-01", "end": f"{y}-12-31",
                     "filed": f"{y + 1}-02-01", "val": ocf_by_year.get(y, 30 + y),
                     "form": "10-K"}
                    for y in years
                ]}},
                "PaymentsToAcquireProductiveAssets": {"units": {"USD": [
                    {"start": f"{y}-01-01", "end": f"{y}-12-31",
                     "filed": f"{y + 1}-02-01", "val": 5, "form": "10-K"}
                    for y in years
                ]}},
                "StockholdersEquity": {"units": {"USD": [
                    {"end": f"{y}-12-31", "filed": f"{y + 1}-02-01",
                     "val": equity_by_year.get(y, 200 + y), "form": "10-K"}
                    for y in years
                ]}},
            },
            "dei": {"EntityPublicFloat": {"units": {"USD": [
                {"end": "2025-06-30", "filed": "2026-02-01", "val": 1000, "form": "10-K"},
            ]}}},
        }
    }


def test_fetch_stage1_series_excludes_extreme_survival_risk(monkeypatch):
    """자기자본·OCF가 최신연도(2025)에 동시 마이너스면 게이트가 걸려야 한다."""
    facts = _facts_with_equity_and_ocf(
        equity_by_year={2025: -500}, ocf_by_year={2025: -100})
    monkeypatch.setattr(B, "fetch_company_facts", lambda cik, ua=None: facts)
    series, lim = B.fetch_stage1_series("X", "1", "2026-08-30")
    assert series is None
    assert any("극단적 존속위험" in x for x in lim)


def test_fetch_stage1_series_keeps_negative_equity_with_positive_ocf(monkeypatch):
    """자사주매입형 마이너스 자기자본(BRO/BSY류) - OCF가 건전하면 통과해야 한다."""
    facts = _facts_with_equity_and_ocf(
        equity_by_year={2025: -500}, ocf_by_year={2025: 800})
    monkeypatch.setattr(B, "fetch_company_facts", lambda cik, ua=None: facts)
    series, lim = B.fetch_stage1_series("X", "1", "2026-08-30")
    assert series is not None
    assert series["shareholders_equity_by_year"][2025] == -500


# ── skip 분류 ────────────────────────────────────────────────────────────
def test_classify_stage1_covers_new_categories():
    skipped = {
        "A": ["public_float 미확보"],
        "B": ["public_float 낡음(최신값이 FY2009로 17년 전)"],
        "C": ["5년 CAGR 계산 불가(기준연도 값 <=0 - PODD/ONON 유형 프레임워크 부적합)"],
    }
    groups = {lbl: ts for lbl, ts, infra in B._classify_stage1(skipped)}
    assert "A" in groups["시가총액 근사치(public_float) 미확보(20-F 외국발행사 등)"]
    assert "B" in groups["시가총액 근사치(public_float) 낡음(SEC 보고의무 축소·중단 추정)"]
    assert "C" in groups["5년 CAGR 계산 불가(PODD/ONON/MU형 프레임워크 부적합)"]
    assert "기타·미분류" not in groups
