"""
STAGE 3 강건성 감사 회귀 테스트.

핵심 불변조건은 셋이다:
  ① 감사가 **공식 판정을 바꾸지 않는다** — Base Case를 읽기만 한다(§33·§35).
  ② 사전등록 가정공간(R-001)과 구현이 **일치한다** — fcf0 축이 조용히 비활성화됐던
     실제 결함이 재발하지 않게 고정한다.
  ③ single_stage 시나리오에서 n·g_terminal을 흔들지 않는다(§11 경제적 제약) —
     흔들면 결과가 동일한 가짜 시나리오가 stability를 부풀린다(§25).
"""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.global_robustness_research_2026_08_16 import (  # noqa: E402
    N_VALUES, audit, load_base, scenarios,
)
from engine.expectation_gap_engine import capped_n  # noqa: E402

ROWS = load_base()
BY = {r["ticker"]: r for r in ROWS}


def test_grid_covers_engine_allowed_n_range_exactly():
    """§2 불일치의 원인이었던 '격자 ⊂ 엔진 허용범위'가 R-001에서는 해소돼 있다."""
    allowed = {capped_n(v) for v in range(1, 30)}
    assert set(N_VALUES) == allowed, (
        f"R-001 n 격자 {set(N_VALUES)} != 엔진 허용범위 {allowed} — "
        "격자가 좁으면 거짓 강건성이 생긴다(§24)"
    )


def test_fcf0_axis_is_actually_active_for_sbc_tickers():
    """
    실제로 발생한 결함의 회귀 테스트: ledger 키를 잘못 읽어(`fcf0_after_sbc`)
    fcf0 축이 34종목 전부에서 비활성화됐었다. 사전등록 축이 조용히 죽으면
    가정공간이 등록보다 좁아진다.
    """
    with_sbc = [r for r in ROWS if r["fcf0_sbc"]]
    assert len(with_sbc) >= 9, (
        f"SBC 차감 fcf0를 가진 종목이 {len(with_sbc)}개뿐 — ledger 키 이름을 확인할 것"
    )
    row = BY["WDAY"]
    labels = {s["labels"]["fcf0"] for s in scenarios(row)}
    assert labels == {"base", "sbc_adjusted"}, "fcf0 축이 시나리오에 반영되지 않았다"


def test_single_stage_does_not_perturb_unused_axes():
    """§11: Gordon 모형이 쓰지 않는 축을 흔들면 가짜 시나리오가 생긴다."""
    row = BY["WDAY"]
    ss = [s for s in scenarios(row) if s["model"] == "single_stage"]
    assert ss
    assert {s["labels"]["g_terminal_delta"] for s in ss} == {0.0}
    assert {s["labels"]["n"] for s in ss} == {row["n"]}
    ts = [s for s in scenarios(row) if s["model"] == "two_stage"]
    assert len({s["labels"]["n"] for s in ts}) == len(N_VALUES)


def test_audit_never_mutates_base_case():
    """§33: 감사 계층은 Base Case를 고치지 않는다."""
    row = BY["BSX"]
    before = dict(row)
    a = audit(row)
    assert row == before
    assert a["base"]["gap"] == before["gap"]
    assert a["base"]["judgment"] == before["judgment"]


def test_stability_is_a_ratio_not_a_probability_claim():
    """
    §15: stability는 0~1 비율이며 확률이 아니다. 코드가 확률로 오독되지 않도록
    리포트에 명시 플래그가 있는지 고정한다.
    """
    a = audit(BY["KLAC"])
    for k, v in a["stability"].items():
        assert 0.0 <= v <= 1.0, k
    p = "reports/global_robustness_2026-08-16.json"
    if os.path.exists(p):
        rep = json.load(open(p, encoding="utf-8"))
        assert rep["stability_is_not_probability"] is True
        assert rep["affects_official_judgment"] is False


def test_base_case_is_always_inside_realistic_growth_range():
    """
    §24: 캡 바인딩 종목은 base가 자체 CAGR 범위 밖일 수 있다. 그때 범위를
    조작하지 않고 base를 포함시키는지 확인한다(하방이 없다는 사실 자체는
    한계로 보고할 뿐 숨기지 않는다).
    """
    for r in ROWS:
        assert r["rg_low"] <= r["rg"] <= r["rg_high"], r["ticker"]
    capped = [r for r in ROWS if r["cap_bound"]]
    assert capped, "캡 바인딩 종목이 하나도 없으면 이 테스트가 무의미하다"
    one_sided = [r["ticker"] for r in capped if r["rg_low"] >= r["rg"]]
    assert one_sided, (
        "캡 바인딩인데 하방이 열려 있다면 §24 서술(7종목 상방 편향)을 갱신해야 한다"
    )


@pytest.mark.parametrize("ticker", ["ACGL", "PDD", "PGR", "SE"])
def test_fully_stable_tickers_have_no_flip_driver(ticker):
    """전 가정공간에서 판정이 유지되는 종목은 flip driver가 비어 있어야 한다."""
    a = audit(BY[ticker])
    assert a["stability"]["judgment"] == 1.0
    assert a["flip_drivers"] == []
    assert a["primary_uncertainty_type"] is None
