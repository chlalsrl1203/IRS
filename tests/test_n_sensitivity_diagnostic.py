"""
성장지속기간(n) 민감도 진단의 불변조건 (2026-08-16).

이 진단이 지키는 두 가지:
1. **격자를 임의로 넓히지 않는다** - 진단 범위는 엔진 자신의 `capped_n(8~15)`과
   정확히 일치해야 한다. 임의 폭을 고르면 그 폭 자체가 새 미검증 파라미터가 된다.
2. **`ASSUMPTION_GRID`를 수정하지 않는다** - H-005가 `robust` 정의를 그 상수로
   사전등록했다. 결과를 본 뒤 사전등록 정의를 바꾸면 사후합리화와 구분되지 않는다.
"""
import importlib.util
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
REPORT = ROOT / "reports" / "n_sensitivity_2026-08-16.json"


def _load():
    path = ROOT / "scripts" / "n_sensitivity_diagnostic_2026_08_16.py"
    spec = importlib.util.spec_from_file_location("n_sens_2026_08_16", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


MOD = _load()


def test_diagnostic_range_exactly_matches_engine_permitted_range():
    """임의 확장이 아님을 보장 - 새 파라미터를 발명하지 않았다."""
    MOD._assert_range_matches_engine()  # 불일치면 AssertionError


def test_frozen_assumption_grid_is_not_modified():
    """H-005 사전등록 보존: 엔진 상수가 그대로여야 한다."""
    from engine.gap_analysis import ASSUMPTION_GRID
    assert tuple(ASSUMPTION_GRID["n_delta"]) == (-2, 0, 2), (
        "ASSUMPTION_GRID의 n_delta가 바뀌었다면 H-005의 robust 정의가 깨진 것이다 - "
        "새 실험 ID로 재등록했는지 확인할 것"
    )


def test_diagnostic_does_not_write_to_ledger():
    """진단은 병기 경로다 - ledger를 건드리면 안 된다."""
    before = {p.name: p.read_text(encoding="utf-8") for p in (ROOT / "ledger").glob("*.json")}
    for name, text in list(before.items())[:3]:
        MOD.analyze(json.loads(text))
    after = {p.name: p.read_text(encoding="utf-8") for p in (ROOT / "ledger").glob("*.json")}
    assert before == after


def test_frozen_grid_misattributes_n_axis_for_known_tickers():
    """
    핵심 발견의 회귀 고정: BSX·DSGX·PTC는 고정격자에서 이미 robust=False였으나
    **n축은 안전하다고 잘못 귀속**돼 있었다(flip_drivers.growth_duration_n=False).
    허용범위 전체로 보면 n축이 실제 원인 중 하나다.
    """
    data = json.loads(REPORT.read_text(encoding="utf-8"))
    by = {r["ticker"]: r for r in data["results"]}
    for t in ("BSX", "DSGX", "PTC"):
        r = by[t]
        assert r["frozen_robust"] is False, f"{t}: 고정격자에서도 이미 취약했어야 한다"
        assert r["frozen_n_flip_detected"] is False, f"{t}: 고정격자는 n축을 못 봤어야 한다"
        assert r["wide_n_flip_detected"] is True, f"{t}: 허용범위에서는 n축이 드러나야 한다"


def test_rop_is_the_only_newly_fragile_ticker():
    """
    ROP만 robust=True -> False로 진짜 신규 취약해진다. 그리고 n 단독이 아니라
    조합에서 뒤집힌다(n축 단독 탐지는 False).
    """
    data = json.loads(REPORT.read_text(encoding="utf-8"))
    newly = [r["ticker"] for r in data["results"]
             if r["frozen_robust"] and not r["wide_robust"]]
    assert newly == ["ROP"], f"신규 취약 종목이 바뀌었다: {newly}"
    rop = next(r for r in data["results"] if r["ticker"] == "ROP")
    assert rop["wide_n_flip_detected"] is False, "ROP는 n 단독이 아니라 조합에서 뒤집힌다"


def test_single_stage_tickers_are_unaffected_by_n_range():
    """single_stage는 n을 쓰지 않으므로 범위를 넓혀도 변화가 없어야 한다."""
    data = json.loads(REPORT.read_text(encoding="utf-8"))
    for r in data["results"]:
        if r["model_used"] == "single_stage":
            assert r["frozen_judgment_set"] == r["wide_judgment_set"], r["ticker"]
            assert r["frozen_robust"] == r["wide_robust"], r["ticker"]
