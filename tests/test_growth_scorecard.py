"""
engine/growth_scorecard.py 테스트 (v3.43).

이 모듈은 손으로 만든 크로스체크 2건(ROP v3.28 / KEYS 2026-08-04)을 공유
로직으로 승격한 것이다. **일반화가 그 두 선례를 정확히 재현하지 못하면
승격 자체가 틀린 것**이므로 그 재현을 골든테스트로 고정한다.
"""

import glob
import json

import pytest

from engine.growth_scorecard import (
    DIVERGENCE_WARNING_THRESHOLD,
    breakeven_growth,
    gap_at_alternative_growth,
    growth_cap_is_binding,
    score_observation,
)


def _load(ticker):
    paths = sorted(glob.glob(f"ledger/{ticker}_*.json"))
    assert paths, f"ledger/{ticker}_*.json 없음"
    with open(paths[-1], encoding="utf-8") as f:
        return json.load(f)


# ── 손으로 만든 선례 재현(승격의 정당성 근거) ──────────────────────────────

def test_reproduces_rop_crosscheck_exactly():
    """
    ROP는 v3.28에서 오가닉 5.5%가 공식 판정에 승격됐다 - 따라서 5.5%를
    대입하면 ledger 자신의 Gap/RAR이 **정확히** 나와야 한다(자기일치).
    이게 어긋나면 일반화한 계산이 원본과 다르다는 뜻이다.
    """
    led = _load("ROP")
    got = gap_at_alternative_growth(led, 0.055)
    assert got["gap"] == pytest.approx(led["expectation_gap"], abs=1e-12)
    assert got["rar"] == pytest.approx(led["rar"], abs=1e-9)
    assert got["judgment"] == led["judgment"]


def test_reproduces_rop_consolidated_scenario():
    """CLAUDE.md 기록: 연결성장 8.5% 시나리오 -> Gap +4.24%p."""
    got = gap_at_alternative_growth(_load("ROP"), 0.085)
    assert got["gap"] * 100 == pytest.approx(4.24, abs=0.01)


def test_reproduces_keys_crosscheck_both_scenarios():
    """
    CLAUDE.md 기록: cyclical 상한 20% -> Gap +4.16%p(적정가),
    FY26 가이던스 28% -> Gap +12.16%p(저평가).
    ROP와 Lynch 유형이 달라(cyclical vs stalwart) 유형을 ledger에서 읽어오는
    일반화가 실제로 동작하는지도 여기서 함께 검증된다.
    """
    led = _load("KEYS")
    cap = gap_at_alternative_growth(led, 0.20)
    guide = gap_at_alternative_growth(led, 0.28)

    assert cap["gap"] * 100 == pytest.approx(4.16, abs=0.02)
    assert cap["judgment"] == "적정가/경계선"
    assert guide["gap"] * 100 == pytest.approx(12.16, abs=0.02)
    assert guide["judgment"] == "저평가 가능성"
    assert cap["lynch_type_used"] == "cyclical"


def test_lynch_type_is_read_from_ledger_not_hardcoded():
    """
    원본 크로스체크 스크립트 2개는 Lynch 유형을 각자 하드코딩했다 - 티커마다
    다르므로 일반화하려면 ledger에서 읽어야 한다(하드코딩을 옮겨왔다면
    ROP=stalwart / KEYS=cyclical 중 하나는 틀렸을 것이다).
    """
    assert gap_at_alternative_growth(_load("ROP"), 0.055)["lynch_type_used"] == "stalwart"
    assert gap_at_alternative_growth(_load("KEYS"), 0.20)["lynch_type_used"] == "cyclical"


# ── 기준선(저평가 최소선) ────────────────────────────────────────────────

def test_breakeven_floor_actually_produces_the_judgment_it_promises():
    """
    "저평가로 판정되려면 최소 이만큼"이라고 안내해놓고 정작 그 값에서 저평가가
    안 나오면 안내가 거짓말이 된다(v3.35가 ETF 엔진에서 정확히 이 자기모순을
    잡아 JUDGMENT_BAND를 단일화한 지점). 회사 엔진에서도 같은 성질을 고정한다.
    """
    for t in ("ROP", "KEYS"):
        led = _load(t)
        floor = breakeven_growth(led)["undervalued_floor"]
        assert gap_at_alternative_growth(led, floor + 1e-9)["judgment"] == "저평가 가능성"
        assert gap_at_alternative_growth(led, floor - 1e-3)["judgment"] != "저평가 가능성"


def test_breakeven_uses_implied_growth_which_is_independent_of_growth_input():
    """
    기준선이 객관적이라는 주장의 근거 - Implied Growth는 성장률 입력과
    무관하다. 대입값을 바꿔도 반환되는 implied_growth는 불변이어야 한다.
    """
    led = _load("ROP")
    a = gap_at_alternative_growth(led, 0.02)
    b = gap_at_alternative_growth(led, 0.30)
    assert a["implied_growth"] == b["implied_growth"] == led["implied_growth"]["value"]


# ── 관측치 채점 ──────────────────────────────────────────────────────────

def _obs(kind, growth):
    return {"kind": kind, "growth": growth, "label": "t", "source": "t"}


def test_only_multiyear_realized_is_usable_as_official_override():
    """
    ROP가 확립한 기준: 1개년 가이던스만으로 realistic_growth_override를 쓰면
    안 된다(KEYS 크로스체크가 명시적으로 승격을 보류한 이유). 관측치 종류가
    이 자격을 결정한다.
    """
    led = _load("ROP")
    assert score_observation(led, _obs("realized_multiyear", 0.055))["usable_as_override"]
    assert not score_observation(led, _obs("guidance_annual", 0.055))["usable_as_override"]
    assert not score_observation(led, _obs("realized_quarterly", 0.055))["usable_as_override"]


def test_unknown_observation_kind_is_rejected():
    """종류를 모르면 증거력을 판단할 수 없다 - 조용히 통과시키지 않는다."""
    with pytest.raises(ValueError):
        score_observation(_load("ROP"), _obs("아무거나", 0.05))


def test_divergence_sign_and_threshold_flag():
    led = _load("KEYS")   # 엔진 RG 1.47%
    low = score_observation(led, _obs("guidance_annual", 0.28))
    assert low["divergence_pp"] > 0
    assert low["divergence_exceeds_threshold"]

    tiny = score_observation(led, _obs("guidance_annual", 0.0147 + 0.001))
    assert not tiny["divergence_exceeds_threshold"]
    assert DIVERGENCE_WARNING_THRESHOLD > 0.05, "판정밴드보다 커야 밴드 내 미세차 남발을 막는다"


def test_score_does_not_mutate_ledger():
    """채점은 읽기 전용이어야 한다 - 공식 기록을 오염시키면 안 된다."""
    led = _load("ROP")
    before = json.dumps(led, sort_keys=True)
    score_observation(led, _obs("realized_multiyear", 0.09))
    assert json.dumps(led, sort_keys=True) == before


# ── 성장상한 바인딩 감지 ──────────────────────────────────────────────────

def test_growth_cap_binding_detected_where_engine_recorded_it():
    """
    캡이 바인딩되면 성장분석이 결과에 기여하지 못한다(M-1) - 관측치와 괴리가
    구조적으로 커지는 원인이라 채점표에서 함께 봐야 한다. ROP는 실제로
    바인딩된 종목이고 KEYS는 아니다(RG 1.47%로 하한 근처).
    """
    assert growth_cap_is_binding(_load("ROP")) is True
    assert growth_cap_is_binding(_load("KEYS")) is False
