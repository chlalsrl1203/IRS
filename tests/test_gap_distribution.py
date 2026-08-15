"""
engine/gap_distribution.py 테스트 (v3.44).

핵심 불변식: perturbation 없이(mode 그대로) DRS를 재구성하면 ledger에 저장된
DRS/r/Gap과 **정확히** 일치해야 한다 - 이게 어긋나면 Monte Carlo가 애초에
엔진과 다른 걸 계산하고 있다는 뜻이라 나머지 전부가 무의미해진다.
"""

import glob
import json

import pytest

from engine.expectation_gap_engine import (
    _CYCLICALITY_BUCKETS,
    _bucket_score,
    erp_from_drs,
)
from engine.gap_distribution import (
    ObservedRange,
    _implied_growth_at_r,
    _triangular,
    fragility_label,
    monte_carlo_gap,
    observed_ranges,
)


def _load(ticker):
    paths = sorted(glob.glob(f"ledger/{ticker}_*.json"))
    assert paths, f"ledger/{ticker}_*.json 없음"
    with open(paths[-1], encoding="utf-8") as f:
        return json.load(f)


def _all_ledgers():
    out = []
    for p in sorted(glob.glob("ledger/*.json")):
        with open(p, encoding="utf-8") as f:
            out.append(json.load(f))
    return out


# ── 자기일치: mode 그대로 재구성하면 ledger 원본과 정확히 일치해야 한다 ──

@pytest.mark.parametrize("ticker", ["TTD", "ROP", "BSX", "KEYS", "PDD"])
def test_reconstructed_drs_matches_ledger_exactly_at_mode(ticker):
    """
    DRS 재구성 공식(고정 3항목 합 + cyclicality + competition_intensity)이
    DRSInputs.score()의 기본가중치(전부 1.0) 결과와 대수적으로 같아야 한다.
    perturb 없이(분석자의 실제 판단값 그대로) 넣으면 오차가 0이어야 한다.
    """
    led = _load(ticker)
    comps = led["drs"]["components"]
    fixed_sum = comps["revenue_volatility"] + comps["margin_volatility"] + comps["leverage"]
    worst_yoy = led["derived"]["worst_yoy_revenue_growth"]
    ds = led["inputs"]["demand_sensitivity_pct"]

    cyc_base = _bucket_score(worst_yoy, _CYCLICALITY_BUCKETS, ascending=False)
    cyc = min(cyc_base + min(max(ds, 0.0), 1.0) * 4.0, 20.0)
    drs_reconstructed = fixed_sum + cyc + comps["competition_intensity"]

    assert drs_reconstructed == pytest.approx(led["drs"]["score"], abs=1e-9)

    r_reconstructed = led["discount_rate"]["rf"] + erp_from_drs(drs_reconstructed)
    assert r_reconstructed == pytest.approx(led["discount_rate"]["r"], abs=1e-12)

    ig_reconstructed = _implied_growth_at_r(led, r_reconstructed)
    gap_reconstructed = led["growth"]["realistic_growth"] - ig_reconstructed
    assert gap_reconstructed == pytest.approx(led["expectation_gap"], abs=1e-9)


def test_implied_growth_at_r_respects_stored_model_choice():
    """
    two_stage로 분석된 종목에 _implied_growth_at_r을 쓰면 two_stage 경로를
    타야 한다 - single_stage로 잘못 계산하면 이분탐색 vs 폐형식 차이로
    값이 달라진다(모델 괴리가 존재하는 종목에서 특히 티가 난다).
    """
    led = _load("TTD")
    assert led["implied_growth"]["model_used"] == "two_stage"
    r = led["discount_rate"]["r"]
    got = _implied_growth_at_r(led, r)
    assert got == pytest.approx(led["implied_growth"]["models"]["two_stage"], abs=1e-9)
    # single_stage 값과는 달라야 한다(괴리가 실제로 존재하므로)
    assert got != pytest.approx(led["implied_growth"]["models"]["single_stage"], abs=1e-6)


# ── 삼각분포 유틸 ────────────────────────────────────────────────────────

def test_triangular_clamps_mode_outside_range():
    """
    분석자의 실제 판단값이 corpus 관측범위 밖에 있으면(신규 종목이 극단값을
    쓴 경우) random.triangular가 정의되지 않는다 - clamp해서 방어한다.
    """
    import random
    rng = random.Random(1)
    for _ in range(200):
        v = _triangular(rng, 0.0, 10.0, mode=99.0)   # mode가 범위 밖
        assert 0.0 <= v <= 10.0


def test_observed_ranges_reflect_actual_corpus_not_hardcoded():
    """
    상수를 박아두지 않고 ledger corpus에서 직접 뽑는다는 설계를 고정한다 -
    corpus가 자라면 범위도 같이 갱신돼야 한다(screener.py의 competition_
    intensity 중앙값 재검증과 동일 원칙).
    """
    ledgers = _all_ledgers()
    ranges = observed_ranges(ledgers)
    assert ranges["demand_sensitivity_pct"].n == len(ledgers)
    assert ranges["competition_intensity"].lo < ranges["competition_intensity"].hi


# ── Monte Carlo 본체 ─────────────────────────────────────────────────────

def test_monte_carlo_is_deterministic_given_fixed_seed():
    """리포트가 재실행할 때마다 달라지면 재현성이 깨진다."""
    led, ranges = _load("BSX"), observed_ranges(_all_ledgers())
    a = monte_carlo_gap(led, ranges, n_draws=500, seed=42)
    b = monte_carlo_gap(led, ranges, n_draws=500, seed=42)
    assert a["gap_mean"] == b["gap_mean"]
    assert a["p_undervalued"] == b["p_undervalued"]


def test_monte_carlo_probabilities_sum_to_one():
    led, ranges = _load("BSX"), observed_ranges(_all_ledgers())
    r = monte_carlo_gap(led, ranges, n_draws=500)
    total = r["p_undervalued"] + r["p_overvalued"] + r["p_neutral"]
    assert total == pytest.approx(1.0, abs=1e-9)


def test_monte_carlo_never_mutates_ledger():
    """읽기 전용이어야 한다 - 공식 기록을 오염시키면 안 된다."""
    led, ranges = _load("BSX"), observed_ranges(_all_ledgers())
    before = json.dumps(led, sort_keys=True)
    monte_carlo_gap(led, ranges, n_draws=200)
    assert json.dumps(led, sort_keys=True) == before


def test_full_range_perturbation_barely_moves_r_for_bsx():
    """
    ⚠️ 이 프로젝트의 실제 발견을 고정하는 테스트다(가설이 아니라 실측):
    demand_sensitivity_pct·competition_intensity를 corpus 전체 관측범위로
    끝까지 흔들어도 erp_from_drs()의 좁은 매핑(ERP 5~8%) 때문에 r은 최대
    ~0.6%p밖에 안 움직인다. 이게 "34종목 전부 견고"의 실제 원인이며,
    growth_scorecard가 발견한 성장률 축 취약성(TTD 등)과 대비되는 축이다.
    """
    led, ranges = _load("BSX"), observed_ranges(_all_ledgers())
    r = monte_carlo_gap(led, ranges, n_draws=3000)
    assert r["gap_stdev"] < 0.01, "표준편차가 1%p를 넘으면 이 구조적 발견이 더 이상 성립하지 않는다"


def test_fragility_label_flags_low_confidence_and_confirms_high():
    mc_confident = {"official_judgment": "저평가 가능성",
                    "p_undervalued": 0.99, "p_overvalued": 0.0, "p_neutral": 0.01}
    mc_fragile = {"official_judgment": "저평가 가능성",
                 "p_undervalued": 0.51, "p_overvalued": 0.10, "p_neutral": 0.39}
    assert fragility_label(mc_confident) == "견고"
    assert fragility_label(mc_fragile) != "견고"
