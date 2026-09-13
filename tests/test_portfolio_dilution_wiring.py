"""
희석 드래그 배선(v3.86)의 불변조건 — "병기하되 자본은 건드리지 않는다".

이 지표는 실현수익률과의 관계 증거가 **0건**이고(§13 게이트 6번 부재),
측정된 부분집합이 희석을 과소평가하는 방향으로 치우쳐 있다(고SBC DUOL·MNDY가
구조적으로 측정 불가, v3.85). 그래서 배선은 F6 플래그까지이며 배제·비중에는
닿지 않는다.

⚠️ 여기서 고정하는 것은 "소스에 dilution이라는 문자열이 없다"가 아니라
**"희석 데이터를 넣든 빼든 결과가 같다"**이다 — grep은 우회되지만 이건 안 된다.
"""
from __future__ import annotations

import json
import os
import pathlib

from engine.monitor_state import load_acknowledgements
from engine.portfolio import load_ledgers
from engine.portfolio_pipeline import (
    apply_g6,
    confirmed_falsifications,
    evidence_row,
    load_dilution_drag,
    load_qualitative_overrides,
    load_sbc_verdicts,
    screen_universe,
    size_portfolio,
    to_buylist_rows,
)

ROOT = pathlib.Path(__file__).resolve().parent.parent


def _inputs():
    q = load_qualitative_overrides()
    return {
        "ledgers": load_ledgers(),
        "sbc": load_sbc_verdicts(),
        "fc": confirmed_falsifications(load_acknowledgements()),
        "ov": q["overrides"],
        "g6": q["g6_substitutes"],
    }


def _run(inp, dilution):
    survivors, ex1 = screen_universe(
        inp["ledgers"], inp["sbc"], inp["fc"], inp["ov"], dilution)
    kept, ex6 = apply_g6(survivors, inp["g6"])
    sized = size_portfolio(kept, inp["ov"])
    return survivors, ex1, ex6, sized


def test_dilution_data_changes_no_weight_and_no_exclusion():
    """이 배선의 유일한 핵심 불변조건 — 실행해서 확인한다."""
    inp = _inputs()
    dil = load_dilution_drag()["rows"]
    assert dil, "희석 드래그 리포트가 비어 있으면 이 테스트가 아무것도 검증하지 않는다"

    s_off, e1_off, e6_off, w_off = _run(inp, None)
    s_on, e1_on, e6_on, w_on = _run(inp, dil)

    assert [r["ticker"] for r in s_off] == [r["ticker"] for r in s_on]
    assert sorted(r["ticker"] for r in e1_off) == sorted(r["ticker"] for r in e1_on)
    assert sorted(r["ticker"] for r in e6_off) == sorted(r["ticker"] for r in e6_on)
    assert ([(r["ticker"], r["weight"]) for r in w_off]
            == [(r["ticker"], r["weight"]) for r in w_on])
    assert ([(r["ticker"], r["quality_score"]) for r in w_off]
            == [(r["ticker"], r["quality_score"]) for r in w_on])


def test_dilution_never_appears_in_excluded_by():
    """F6은 플래그다 — 배제 사유 목록에 들어가면 미검증 지표가 유니버스를 바꾼다."""
    inp = _inputs()
    dil = load_dilution_drag()["rows"]
    survivors, ex1, _e6, _w = _run(inp, dil)
    for r in survivors + ex1:
        for reason in r["excluded_by"]:
            assert "희석" not in reason and "F6" not in reason, (r["ticker"], reason)


def test_unmeasured_is_flagged_as_unknown_not_as_harmless():
    """'데이터 없음 ≠ 안전' — 측정 불가 종목이 조용히 통과하면 안 된다."""
    inp = _inputs()
    dil = load_dilution_drag()["rows"]
    survivors, _e1, _e6, _w = _run(inp, dil)

    seen = False
    for r in survivors:
        if r["dilution_status"] in (None, "OK"):
            continue
        seen = True
        f6 = [f for f in r["flags"] if f.startswith("F6")]
        assert f6, r["ticker"]
        assert "미확인" in f6[0], f6
    assert seen, "측정 불가 생존종목이 하나도 없다 - 이 테스트가 무의미해졌다"


def test_material_drag_is_flagged_with_its_number():
    inp = _inputs()
    dil = load_dilution_drag()["rows"]
    survivors, _e1, _e6, _w = _run(inp, dil)

    flagged = {r["ticker"] for r in survivors
               for f in r["flags"] if f.startswith("F6 희석 드래그 -")}
    material = {r["ticker"] for r in survivors
                if r["dilution_status"] == "OK"
                and r["dilution_drag"] is not None
                and r["dilution_drag"] <= -0.05}
    assert flagged == material
    assert material, "드래그가 임계값을 넘는 생존종목이 하나도 없다"


def test_missing_report_degrades_to_unknown_not_to_clean():
    """리포트가 없을 때 조용히 '희석 없음'이 되면 안 된다."""
    empty = load_dilution_drag(reports_dir=str(ROOT / "does-not-exist"))
    assert empty["rows"] == {}
    assert empty["coverage"] is None

    inp = _inputs()
    survivors, _e1, _e6, _w = _run(inp, empty["rows"])
    for r in survivors:
        assert any("F6" in f and "미확인" in f for f in r["flags"]), r["ticker"]


def test_buylist_rows_carry_no_dilution_field():
    """매수리스트 행은 daily_brief가 읽는 발행 스키마다 - 진단축을 섞지 않는다."""
    inp = _inputs()
    _s, _e1, _e6, sized = _run(inp, load_dilution_drag()["rows"])
    for row in to_buylist_rows(sized):
        assert not any("dilution" in k or "drag" in k for k in row), row


def test_evidence_row_without_dilution_is_still_valid():
    """옛 3인자 호출이 깨지지 않는다(기본값 None -> 전부 미측정)."""
    inp = _inputs()
    led = next(iter(inp["ledgers"].values()))
    r = evidence_row(led, inp["sbc"], inp["ov"])
    assert r["dilution_status"] is None
    assert r["dilution_drag"] is None


def test_published_diagnostics_declare_the_coverage_bias():
    """산출물이 편향을 숨기면 부분 표본이 전체 신호로 읽힌다."""
    paths = sorted(pathlib.Path(ROOT / "reports").glob("portfolio_pipeline_*.json"))
    if not paths:
        return  # 아직 발행 전 - 발행되면 아래 조건이 걸린다
    doc = json.loads(paths[-1].read_text(encoding="utf-8"))
    dil = doc["dilution_annotation"]
    assert dil["affects_weights"] is False
    assert dil["affects_exclusion"] is False
    assert dil["coverage"]["measured"] < dil["coverage"]["total"]
    assert dil["coverage_bias"]["direction"] == "optimistic"
    assert dil["residual_gap"]
    assert doc["boundary_review"]


def test_wiring_script_passes_dilution_through():
    """진입점이 로더를 실제로 부르는지 - 부르지 않으면 배선이 죽은 코드가 된다."""
    src = (ROOT / "scripts" / "build_portfolio.py").read_text(encoding="utf-8")
    assert "load_dilution_drag()" in src
    assert 'dilution["rows"]' in src


def test_env_keeps_reports_dir_default():
    """기본 경로가 저장소 reports/를 가리킨다(테스트가 우연히 통과하지 않도록)."""
    from engine.portfolio_pipeline import REPORTS
    assert os.path.basename(REPORTS) == "reports"
