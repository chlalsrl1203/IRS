"""
engine/market_relative.py 테스트 (v3.45).

핵심: 이 모듈은 벤치마크 차감(정직한 뺄셈)일 뿐 요인분해가 아니다 - 그
경계를 흐리지 않는 것이 설계의 핵심이므로, 계산이 순수 대수 항등식을
지키는지와 공식 ledger를 오염시키지 않는지를 고정한다.
"""

import glob
import json

import pytest

from engine.market_relative import market_baseline, relative_to_market


def _load(ticker, dirpath="ledger"):
    paths = sorted(glob.glob(f"{dirpath}/{ticker}_*.json"))
    assert paths, f"{dirpath}/{ticker}_*.json 없음"
    with open(paths[-1], encoding="utf-8") as f:
        return json.load(f)


def _voo():
    return _load("VOO", dirpath="ledger_etf")


def test_baseline_picks_the_most_conservative_voo_source():
    """
    etf_pipeline.format_comparison_table()의 규칙과 동일해야 한다: 가장
    비싼 P/E(=가장 높은 implied_growth)를 보수적 기준으로 쓴다. VOO는 실측
    2개 출처(stockanalysis 27.53x, FactSet forward 19.6x)가 있고 트레일링
    쪽 P/E가 더 높다 - 즉 implied_growth도 더 높은 쪽이 선택돼야 한다.
    """
    voo = _voo()
    baseline = market_baseline(voo)
    by_source = voo["valuation"]["by_source"]
    assert baseline["implied_growth"] == max(s["implied_growth"] for s in by_source.values())
    assert baseline["gap"] == min(s["gap"] for s in by_source.values())  # RG 고정이므로 IG 최대 = Gap 최소


def test_relative_gap_is_pure_subtraction():
    """relative_gap = Gap_company - Gap_market. 이 항등식이 계산의 전부다."""
    voo, baseline = _voo(), market_baseline(_voo())
    for ticker in ("TTD", "BSX", "ROP"):
        led = _load(ticker)
        r = relative_to_market(led, baseline)
        assert r["relative_gap"] == pytest.approx(led["expectation_gap"] - baseline["gap"], abs=1e-12)
        assert r["growth_premium"] == pytest.approx(
            led["implied_growth"]["value"] - baseline["implied_growth"], abs=1e-12)


def test_relative_gap_matches_absolute_gap_when_market_gap_is_zero():
    """
    시장 Gap이 0이면(가상 시나리오) 상대Gap은 그냥 절대Gap과 같아야 한다 -
    회귀적으로 계산식 자체를 검증하는 가장 단순한 케이스.
    """
    zero_baseline = {"implied_growth": 0.05, "gap": 0.0, "source": "test", "expected_growth": 0.05}
    led = _load("TTD")
    r = relative_to_market(led, zero_baseline)
    assert r["relative_gap"] == pytest.approx(led["expectation_gap"], abs=1e-12)


def test_does_not_mutate_either_ledger():
    voo, led = _voo(), _load("BSX")
    voo_before = json.dumps(voo, sort_keys=True)
    led_before = json.dumps(led, sort_keys=True)
    relative_to_market(led, market_baseline(voo))
    assert json.dumps(voo, sort_keys=True) == voo_before
    assert json.dumps(led, sort_keys=True) == led_before


def test_official_judgment_is_carried_through_unchanged():
    """
    이 모듈은 판정을 다시 내리지 않는다 - 원본 judgment를 그대로 병기만
    한다(공식판정 재계산 금지 원칙, is_insurer/sbc_cross_check와 동일).
    """
    led = _load("KEYS")
    r = relative_to_market(led, market_baseline(_voo()))
    assert r["judgment"] == led["judgment"]
