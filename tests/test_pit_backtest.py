"""
pit_backtest.py 테스트 - 네트워크 없이 순수 로직 + PIT truncate만 고정한다.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import pytest  # noqa: E402

from scripts import pit_backtest as PB  # noqa: E402


@pytest.fixture(autouse=True)
def isolated_facts_cache(tmp_path, monkeypatch):
    """
    ⚠️ companyfacts 디스크 캐시가 테스트 간 상태를 누출시킨다 - 실제로
    앞 테스트가 CIK "1"로 저장한 픽스처를 뒷 테스트가 읽어 **자기 픽스처가
    무시되는** 사고가 났다(2026-08-29, 캐시 도입 직후 이 테스트가 잡아냄).
    캐시 자체는 프로덕션에서 옳은 동작이므로(다중 T0 검증의 전제) 테스트
    쪽을 격리한다.
    """
    monkeypatch.setattr(PB, "FACTS_CACHE_DIR", str(tmp_path / "facts"))


def _facts(rev_entries, ocf_entries, capex_entries, pf_entries):
    return {"facts": {
        "us-gaap": {
            "Revenues": {"units": {"USD": rev_entries}},
            "NetCashProvidedByUsedInOperatingActivities": {"units": {"USD": ocf_entries}},
            "PaymentsToAcquireProductiveAssets": {"units": {"USD": capex_entries}},
        },
        "dei": {"EntityPublicFloat": {"units": {"USD": pf_entries}}},
    }}


def _annual(y, val, filed):
    return {"start": f"{y}-01-01", "end": f"{y}-12-31", "filed": filed,
            "val": val, "form": "10-K"}


def test_fetch_pit_series_excludes_data_filed_after_t0(monkeypatch):
    """T0 이후 공시된 회계연도는 아예 안 보여야 한다 - 미래정보 혼입 방지."""
    facts = _facts(
        rev_entries=[_annual(y, 100 + y, f"{y + 1}-02-01") for y in range(2014, 2022)],
        ocf_entries=[_annual(y, 30 + y, f"{y + 1}-02-01") for y in range(2014, 2022)],
        capex_entries=[_annual(y, 5, f"{y + 1}-02-01") for y in range(2014, 2022)],
        pf_entries=[
            {"end": "2020-06-30", "filed": "2020-10-01", "val": 900, "form": "10-K"},
            {"end": "2021-06-30", "filed": "2021-10-01", "val": 1000, "form": "10-K"},
        ],
    )
    monkeypatch.setattr(PB, "fetch_company_facts", lambda cik, ua=None: facts)
    series, lim = PB.fetch_pit_series("X", "1", as_of="2021-06-30")
    assert series is not None
    # 2021년 회계연도는 2022-02-01에 공시되므로 T0=2021-06-30 이후 - 제외돼야 함
    assert 2021 not in series["revenue_by_year"]
    assert 2020 in series["revenue_by_year"]
    # public_float도 2021-10-01 공시분은 T0 이후라 제외 - 2020 값만 남는다
    assert series["public_float_by_year"] == {2020: 900.0}


def test_fetch_pit_series_uses_real_retrieved_at_not_as_of(monkeypatch):
    """
    실제로 밟았던 버그의 회귀 테스트 - retrieved_at에 as_of(과거)를 그대로
    넘긴 채 실행할 뻔했다. retrieved_at은 항상 코드 실행 시각(오늘)이어야
    한다.
    """
    seen = {}

    class SpyProvider:
        def __init__(self, **kw):
            pass

        def fetch_annual_financials(self, entity, metrics=None, fiscal_years=None,
                                    retrieved_at=None, as_of=None):
            seen["retrieved_at"] = retrieved_at
            seen["as_of"] = as_of
            from engine.data.providers.base import ProviderResult
            return ProviderResult(source_key="sec_edgar", entity=entity, facts=[],
                                  governance={"as_of": as_of}, retrieved_at=retrieved_at)

    monkeypatch.setattr(PB, "SecCompanyFactsProvider", SpyProvider)
    monkeypatch.setattr(PB, "fetch_company_facts", lambda cik, ua=None: {"facts": {}})
    PB.fetch_pit_series("X", "1", as_of="2021-06-30", retrieved_at="2026-08-29")
    assert seen["as_of"] == "2021-06-30"
    assert seen["retrieved_at"] == "2026-08-29"
    assert seen["retrieved_at"] != seen["as_of"]


def test_fetch_pit_series_rejects_stale_public_float_relative_to_t0(monkeypatch):
    facts = _facts(
        rev_entries=[_annual(y, 100 + y, f"{y + 1}-02-01") for y in range(2010, 2021)],
        ocf_entries=[_annual(y, 30 + y, f"{y + 1}-02-01") for y in range(2010, 2021)],
        capex_entries=[_annual(y, 5, f"{y + 1}-02-01") for y in range(2010, 2021)],
        pf_entries=[
            {"end": "2010-03-01", "filed": "2010-10-01", "val": 900, "form": "10-K"},
        ],
    )
    monkeypatch.setattr(PB, "fetch_company_facts", lambda cik, ua=None: facts)
    series, lim = PB.fetch_pit_series("X", "1", as_of="2021-06-30")
    assert series is None
    assert any("public_float 낡음" in x for x in lim)


# ── companyfacts 캐시 (다중 T0 검증의 전제) ──────────────────────────────
def test_companyfacts_fetched_once_across_multiple_t0(monkeypatch):
    """
    같은 티커를 여러 T0로 재현할 때 SEC를 T0 횟수만큼 다시 두드리면 안 된다 -
    companyfacts는 T0와 무관하게 동일하고 T0는 truncate만 하기 때문이다.
    캐시가 없으면 다중 T0 검증이 비싸져 "T0 하나만 보고 결론내는" 함정에
    구조적으로 빠진다(이 프로젝트가 실제로 그럴 뻔했다).
    """
    calls = {"n": 0}
    facts = _facts(
        rev_entries=[_annual(y, 100 + y, f"{y + 1}-02-01") for y in range(2010, 2026)],
        ocf_entries=[_annual(y, 30 + y, f"{y + 1}-02-01") for y in range(2010, 2026)],
        capex_entries=[_annual(y, 5, f"{y + 1}-02-01") for y in range(2010, 2026)],
        pf_entries=[{"end": f"{y}-06-30", "filed": f"{y}-10-01", "val": 900,
                     "form": "10-K"} for y in range(2015, 2026)],
    )

    def counting(cik, ua=None):
        calls["n"] += 1
        return facts

    monkeypatch.setattr(PB, "fetch_company_facts", counting)
    for t0 in ("2018-06-30", "2021-06-30", "2023-06-30"):
        series, _ = PB.fetch_pit_series("X", "0000000042", as_of=t0)
        assert series is not None
    assert calls["n"] == 1, f"companyfacts를 {calls['n']}번 받았다(1번이어야 함)"


def test_corrupt_cache_is_discarded_not_propagated(tmp_path, monkeypatch):
    """깨진 캐시 파일이 영구 실패를 만들면 안 된다 - 버리고 다시 받는다."""
    monkeypatch.setattr(PB, "FACTS_CACHE_DIR", str(tmp_path / "facts"))
    os.makedirs(PB.FACTS_CACHE_DIR, exist_ok=True)
    bad = os.path.join(PB.FACTS_CACHE_DIR, "0000000099.json")
    with open(bad, "w", encoding="utf-8") as f:
        f.write("{not json")
    monkeypatch.setattr(PB, "fetch_company_facts",
                        lambda cik, ua=None: {"facts": {"us-gaap": {}}})
    facts, err = PB.cached_company_facts("0000000099")
    assert err is None and facts == {"facts": {"us-gaap": {}}}
