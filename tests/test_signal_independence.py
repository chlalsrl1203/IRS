"""
PHASE 1 — 신호 독립성 검증(2026-08-21)의 불변조건.

RQ-002가 하루 전 "TCOM은 서로 독립인 두 축에서 이탈한다"고 결론냈고,
§6 Evidence Dependency Rule을 그 결론에 적용해 **틀렸음을 확인**했다.
이 테스트는 그 정정이 조용히 되돌아가지 않게 고정한다.

고정하는 것:
  ① CANCELLED와 SURVIVES를 구분한다(둘 다 '부분 적용에서 이탈'이지만 의미가 정반대)
  ② TCOM의 SBC 신호가 인공물이라는 사실이 자본배분 경로에 드러난다
  ③ 계산 불가를 '무해'로 오독하지 않는다
  ④ 이 배선이 비중을 바꾸지 않는다
  ⑤ RG가 변하지 않는 종목에서는 부분 적용 == 일관 적용이다(구조적 규칙)
"""
import importlib.util
import json
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
SIGNAL = ROOT / "reports" / "signal_independence_2026-08-21.json"
BUYLIST = ROOT / "reports" / "buylist_2026-08-03.json"
BOUNDARY = ROOT / "reports" / "buylist_boundary_review_2026-08-16.json"


def _load(name):
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


BUYLIST_MOD = _load("build_buylist_2026_08_03")


def _rows():
    return {r["ticker"]: r for r in
            json.loads(SIGNAL.read_text(encoding="utf-8"))["results"]}


# ── ① CANCELLED와 SURVIVES는 정반대 의미다 ───────────────────────────────
def test_cancelled_and_survives_are_distinguished_not_merged():
    """
    둘 다 "부분 적용(fcf0에만)에서 유니버스를 이탈한다"는 점은 같다. 다른 것은
    **일관 적용(성장경로에도) 후에도 이탈하는가**이며, 이 구분이 사라지면
    인공물을 근거로 자본을 움직이게 된다.
    """
    rows = _rows()
    for t in ("TCOM", "WDAY", "TTD"):
        r = rows[t]
        assert r["base"]["grade"] in ("S", "A"), t
        assert r["sbc_level_only"]["grade"] not in ("S", "A"), t
    assert rows["TCOM"]["verdict"] == "CANCELLED"
    assert rows["WDAY"]["verdict"] == "SURVIVES"
    assert rows["TTD"]["verdict"] == "SURVIVES"


def test_tcom_sbc_exit_disappears_under_consistent_application():
    """
    2026-08-21 실측: TCOM 부분 +5.28%p(B) -> 일관 +7.50%p(A).
    RQ-002가 어제 "SBC 축 이탈"로 보고한 것이 적용 비대칭의 산물이었다.
    """
    r = _rows()["TCOM"]
    assert r["sbc_consistent"] is not None
    assert r["sbc_consistent"]["grade"] in ("S", "A")
    assert r["sbc_consistent"]["gap"] > r["sbc_level_only"]["gap"]
    # RG가 실제로 움직여서 상쇄된 것이지 우연이 아니다
    assert r["rg_driver"] == "fcf_cagr"
    assert not r["cap_applied"]
    assert r["sbc_consistent"]["realistic_growth"] > r["base"]["realistic_growth"]


def test_tcom_growth_axis_signal_still_stands():
    """
    SBC 축이 인공물이라고 해서 TCOM이 안전한 것은 아니다 — RG를 기업 자신의
    CAGR 최소값으로 낮추면 여전히 유니버스를 이탈한다(R-001의 RG축).
    이 사실이 함께 사라지면 정정이 과잉교정이 된다.
    """
    r = _rows()["TCOM"]
    assert r["rg_low"]["grade"] not in ("S", "A")


def test_ttd_signal_gets_stronger_not_weaker():
    """TTD는 일관 적용에서 오히려 악화된다(+5.51%p B -> −5.24%p D)."""
    r = _rows()["TTD"]
    assert r["sbc_consistent"]["gap"] < r["sbc_level_only"]["gap"]
    assert r["sbc_consistent"]["grade"] == "D"


# ── ③ 계산 불가를 '무해'로 오독하지 않는다 ───────────────────────────────
def test_uncomputable_consistency_is_unknown_not_safe():
    rows = _rows()
    blocked = [r for r in rows.values() if r["sbc_consistent"] is None]
    assert blocked, "계산 불가 종목이 하나도 없다면 제외 규칙이 죽은 것"
    for r in blocked:
        assert r.get("sbc_consistent_blocked"), r["ticker"]
        # 부분 적용에서 이탈했는데 일관 적용을 못 쟀으면 UNKNOWN이어야 한다
        if (r["base"]["grade"] in ("S", "A")
                and r["sbc_level_only"]["grade"] not in ("S", "A")):
            assert r["verdict"] == "UNKNOWN", r["ticker"]


def test_missing_signal_file_reports_unknown_not_no_artifact():
    assert BUYLIST_MOD.load_sbc_signal_verdict("reports/__missing__.json") is None


# ── ④ 비중 불변 ──────────────────────────────────────────────────────────
def test_wiring_changed_no_weight():
    rows = json.loads(BUYLIST.read_text(encoding="utf-8"))
    assert sum(r["weight_final"] for r in rows) == pytest.approx(1.0, abs=1e-9)
    for r in rows:
        assert "sbc_signal_verdict" in r, r["ticker"]


def test_boundary_review_carries_the_verdict_for_every_flagged_holding():
    b = json.loads(BOUNDARY.read_text(encoding="utf-8"))
    assert b["sbc"]["signal_independence_checked"] is True
    held = b["sbc"]["held_but_sbc_dependent"]
    assert held
    for h in held:
        assert h["signal_verdict"] in ("SURVIVES", "CANCELLED", "UNKNOWN"), h["ticker"]
    tcom = [h for h in held if h["ticker"] == "TCOM"]
    assert tcom and tcom[0]["signal_verdict"] == "CANCELLED", (
        "TCOM의 SBC 신호가 인공물이라는 경고가 자본배분 경로에서 사라졌다")


# ── ⑤ 구조적 규칙 — RG가 안 움직이면 부분 == 일관 ────────────────────────
def test_partial_equals_consistent_when_growth_path_cannot_move():
    """
    RG가 `revenue_weighted`로 결정되거나 Lynch 캡이 바인딩된 종목은 FCF CAGR이
    아무리 변해도 RG가 고정된다. 그런 종목에서는 부분 적용과 일관 적용의 Gap이
    **정확히 같아야** 한다 — 다르다면 계산 경로에 의도하지 않은 차이가 있다.
    """
    checked = 0
    for r in _rows().values():
        if r["sbc_consistent"] is None:
            continue
        if r["rg_driver"] == "revenue_weighted" or r["cap_applied"]:
            assert r["sbc_consistent"]["gap"] == pytest.approx(
                r["sbc_level_only"]["gap"], abs=1e-12), r["ticker"]
            checked += 1
    assert checked >= 5, f"이 구간 종목이 {checked}건뿐 - 규칙 검증 표본 부족"
