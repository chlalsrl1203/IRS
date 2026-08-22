"""
scripts/daily_screen.py (2026-08-22)의 순수 로직 불변조건.

매일 밤 무인 상태(사용자 폰 접근 불가 시간대)로 도는 스크립트라 회귀가 나면
아무도 즉시 못 알아챈다 - 그래서 핵심 계산 함수만은 테스트로 고정한다.
네트워크는 타지 않는다(합성 SEC facts 주입).
"""
import importlib.util
import os
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent


def _load():
    path = ROOT / "scripts" / "daily_screen.py"
    spec = importlib.util.spec_from_file_location("daily_screen", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


MOD = _load()


def test_cagr_basic():
    assert MOD._cagr(100, 200, 5) == pytest.approx((200 / 100) ** 0.2 - 1)


def test_cagr_returns_none_on_nonpositive_start_or_end():
    """v3.19 가드와 동일 원리 - 음수/0 시작값에서 복소수를 조용히 반환하면 안 된다."""
    assert MOD._cagr(-10, 100, 5) is None
    assert MOD._cagr(100, -10, 5) is None
    assert MOD._cagr(0, 100, 5) is None


def test_worst_yoy_picks_the_minimum():
    assert MOD._worst_yoy({2020: 100, 2021: 90, 2022: 120}) == pytest.approx(-0.1)


def test_worst_yoy_needs_at_least_two_points():
    assert MOD._worst_yoy({2020: 100}) is None


def _facts_with(tag_series):
    """{tag: {fy: val}} -> 합성 companyfacts (test_sec_provider.py와 동일 패턴)."""
    facts = {}
    for tag, series in tag_series.items():
        units = [{"form": "10-K", "start": f"{fy}-01-01", "end": f"{fy}-12-31",
                  "filed": f"{fy + 1}-02-15", "val": v} for fy, v in series.items()]
        facts[tag] = {"units": {"USD": units}}
    return {"facts": {"us-gaap": facts}}


def test_fetch_sec_fields_computes_cagr_and_fcf0(monkeypatch, tmp_path):
    facts = _facts_with({
        "Revenues": {2020: 1000, 2021: 1100, 2022: 1300, 2023: 1500,
                     2024: 1700, 2025: 2000},
        "NetCashProvidedByUsedInOperatingActivities": {
            2020: 300, 2021: 330, 2022: 380, 2023: 430, 2024: 480, 2025: 550},
        "PaymentsToAcquirePropertyPlantAndEquipment": {
            2020: 50, 2021: 55, 2022: 60, 2023: 65, 2024: 70, 2025: 75},
    })
    monkeypatch.setattr(MOD, "_cached_facts", lambda t: facts)
    fields, limitations = MOD.fetch_sec_fields("TEST", "2026-08-22")
    assert fields is not None
    assert fields["fcf0"] == 550 - 75  # OCF - capex, 최종연도
    assert fields["revenue_cagr_5y"] == pytest.approx(MOD._cagr(1000, 2000, 5))
    assert fields["base_year"] == 2020
    assert fields["final_year"] == 2025


def test_fetch_sec_fields_rejects_negative_base_or_final_fcf(monkeypatch):
    """FCF 시작/끝 연도가 적자면 CAGR을 계산하지 않고 정직하게 skip한다(Model N/A 경로)."""
    facts = _facts_with({
        "Revenues": {2023: 1000, 2024: 1200, 2025: 1400},
        "NetCashProvidedByUsedInOperatingActivities": {2023: 100, 2024: 120, 2025: 140},
        "PaymentsToAcquirePropertyPlantAndEquipment": {2023: 200, 2024: 50, 2025: 60},
    })
    monkeypatch.setattr(MOD, "_cached_facts", lambda t: facts)
    fields, limitations = MOD.fetch_sec_fields("TEST", "2026-08-22")
    assert fields is None
    assert any("0 이하" in m for m in limitations)


def test_default_ndte_matches_ledger_median():
    """
    ledger 34종목 실측 중앙값(2026-08-22 계산)과 다르면 조용히 임의값으로
    바뀐 것 - screener.py의 ASSUMED_* 상수 원칙과 동일하게 근거를 고정한다.
    """
    assert MOD.DEFAULT_NDTE == pytest.approx(0.406, abs=0.001)


def test_score_writes_output_with_passed_and_review_fields(tmp_path):
    raw = {
        "retrieved_at": "2026-08-22",
        "candidates": {
            "TEST": {
                "revenue_cagr_5y": 0.15, "fcf_cagr_5y": 0.20, "fcf0": 3_000_000_000,
                "worst_yoy_revenue": 0.05, "base_year": 2020, "final_year": 2025,
                "span_years": 5, "limitations": [],
            }
        },
        "skipped": {},
    }
    import json
    raw_path = tmp_path / "raw.json"
    caps_path = tmp_path / "caps.json"
    raw_path.write_text(json.dumps(raw), encoding="utf-8")
    caps_path.write_text(json.dumps({"TEST": 30_000_000_000}), encoding="utf-8")

    MOD.cmd_score(str(raw_path), str(caps_path))

    out_path = tmp_path / "raw_scored.json"
    assert out_path.exists()
    out = json.loads(out_path.read_text(encoding="utf-8"))
    assert "passed" in out and "missing_market_cap" in out


def test_score_reports_missing_market_cap_honestly(tmp_path):
    """
    시가총액을 못 구한 종목을 조용히 빼버리면 안 된다 - '측정 불가'가
    '통과 실패'로 오독될 위험이 있다(이 프로젝트의 반복 원칙).
    """
    import json
    raw = {"retrieved_at": "2026-08-22",
           "candidates": {"NOCAP": {"revenue_cagr_5y": 0.1, "fcf_cagr_5y": 0.1,
                                     "fcf0": 100, "worst_yoy_revenue": 0.0,
                                     "base_year": 2020, "final_year": 2025,
                                     "span_years": 5, "limitations": []}},
           "skipped": {}}
    raw_path = tmp_path / "raw2.json"
    caps_path = tmp_path / "caps2.json"
    raw_path.write_text(json.dumps(raw), encoding="utf-8")
    caps_path.write_text(json.dumps({}), encoding="utf-8")

    MOD.cmd_score(str(raw_path), str(caps_path))
    out = json.loads((tmp_path / "raw2_scored.json").read_text(encoding="utf-8"))
    assert out["missing_market_cap"] == ["NOCAP"]
