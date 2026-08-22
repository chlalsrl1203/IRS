"""
PHASE 4 — 희석 드래그 조사(2026-08-21)의 불변조건.

⚠️ 이 테스트가 지키는 것은 **지표가 아니라 실패의 기록**이다.
초판이 주식분할·IPO·ADS 비율변경을 희석으로 오독해 완전히 틀린 값을 냈고,
그것을 자본배분 경로에 배선까지 했다가 되돌렸다. 그 오염 검출이 사라지면
같은 실수가 재발한다.

고정하는 것:
  ① 구조적 주식수 점프를 희석으로 계산하지 않는다
  ② 임계값은 도메인 제약이며 결과를 보고 정한 것이 아니다
  ③ 측정 불가를 '희석 없음'으로 오독하지 않는다
  ④ 이 지표는 자본배분 경로에 배선돼 있지 않다(REJECT 상태)
"""
import importlib.util
import json
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
DRAG = ROOT / "reports" / "dilution_drag_2026-08-21.json"
BUYLIST = ROOT / "reports" / "buylist_2026-08-03.json"


def _load(name):
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


MOD = _load("dilution_drag_2026_08_21")


def _rows():
    return {r["ticker"]: r for r in json.loads(DRAG.read_text(encoding="utf-8"))["results"]}


# ── ① 구조적 점프를 희석으로 계산하지 않는다 ─────────────────────────────
def test_stock_splits_and_ipos_are_not_counted_as_dilution():
    """
    2026-08-21 실측으로 확인된 오염(초판이 전부 '희석'으로 계산했다):
      TTD  FY2021 x10.2  (10:1 주식분할)
      TCOM FY2021 x8.4   (ADS 비율 변경)
      DUOL FY2021 x1.8 / MNDY FY2022 x1.5 (IPO 직후)
      PDD  FY2025 x1002  (ADS/보통주 단위 혼재)
    이들은 반드시 STRUCTURAL_SHARE_JUMP로 걸러져야 한다.
    """
    rows = _rows()
    for t in ("TTD", "TCOM", "DUOL", "MNDY", "PDD", "BRO"):
        assert rows[t]["status"] == "STRUCTURAL_SHARE_JUMP", t
        assert rows[t].get("dilution_drag") is None, t


def test_contaminated_tickers_carry_the_evidence():
    """어떤 연도가 왜 걸렸는지 남지 않으면 나중에 재검토할 수 없다."""
    for r in _rows().values():
        if r["status"] == "STRUCTURAL_SHARE_JUMP":
            assert r.get("jumps"), r["ticker"]
            assert all("fy" in j and "ratio" in j for j in r["jumps"]), r["ticker"]


def test_threshold_is_a_domain_constraint_not_a_tuned_value():
    """
    1.5배는 결과를 보고 고른 값이 아니라 도메인 제약이다 - 정상적인 연간 희석이
    50%를 넘는 것은 사실상 불가능하다. 이 값이 조용히 완화되면 오염이 다시 샌다.
    """
    assert MOD.STRUCTURAL_JUMP_RATIO == 1.5


def test_clean_tickers_have_plausible_share_changes():
    """오염 필터를 통과한 종목의 주식수 변화는 도메인상 타당한 범위여야 한다."""
    for r in _rows().values():
        if r["status"] != "OK":
            continue
        assert -0.5 < r["share_count_change_pct"] < 3.0, r["ticker"]


# ── ③ 측정 불가를 '희석 없음'으로 오독하지 않는다 ────────────────────────
def test_unmeasurable_is_recorded_not_defaulted_to_zero():
    rows = _rows()
    bad = [r for r in rows.values() if r["status"] != "OK"]
    assert bad, "측정 불가 종목이 0이면 필터가 죽은 것"
    for r in bad:
        assert r.get("detail"), r["ticker"]
        assert "dilution_drag" not in r or r["dilution_drag"] is None


def test_buy_universe_coverage_is_reported_honestly():
    """
    매수 유니버스 12종목 중 6종목(비중 41.33%)이 측정 불가다.
    이 사실이 사라지면 12.16%라는 신호가 전체를 대표하는 것처럼 오독된다.
    """
    rows = _rows()
    buy = {r["ticker"]: r["weight_final"]
           for r in json.loads(BUYLIST.read_text(encoding="utf-8"))}
    unmeasured = [t for t in buy if rows[t]["status"] != "OK"]
    assert len(unmeasured) >= 5
    assert sum(buy[t] for t in unmeasured) > 0.35


# ── ④ 배선하지 않았다 (REJECT 상태) ──────────────────────────────────────
def test_dilution_is_not_wired_into_the_capital_path():
    """
    §13 게이트 6번(validation strategy)이 없고 매수 유니버스 커버리지가 50%뿐이라
    진단축으로도 배선하지 않았다. 배선하려면 커버리지 문제부터 해소해야 한다.
    """
    for r in json.loads(BUYLIST.read_text(encoding="utf-8")):
        assert "dilution_drag" not in r, (
            f"{r['ticker']}: 희석 드래그가 매수리스트에 배선됐다 - "
            "결정 #64가 REJECT(커버리지 부족)로 등록돼 있다")


def test_report_declares_it_does_not_affect_judgment():
    d = json.loads(DRAG.read_text(encoding="utf-8"))
    assert d["affects_official_judgment"] is False
    assert "not_wired_into_growth" in d
