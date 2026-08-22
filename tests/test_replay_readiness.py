"""
PHASE 5 — Historical Replay readiness 판정(2026-08-21)의 불변조건.

⚠️ 이 테스트가 지키는 것은 **판정이 아니라 판정 규칙**이다.
readiness는 데이터가 채워지면 바뀌어야 하는 값이고, 바뀌면 안 되는 것은
"어떻게 판정하는가"다.

고정하는 것:
  ① Historical Replay를 구현하지 않았다(§14)
  ② 축을 평균내지 않는다 - 가장 약한 축이 전체를 결정한다
  ③ 차단된 축은 반드시 차단 사유를 남긴다(공백을 '무해'로 읽지 않는다)
  ④ 재작성 임계값은 도메인 제약이며 결과를 보고 정한 값이 아니다
  ⑤ ledger 판본 측정이 "분석이 틀렸다"로 오독되지 않게 단서를 단다
  ⑥ 공식 판정에 아무것도 배선하지 않았다
"""
import importlib.util
import json
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
REPORT = ROOT / "reports" / "replay_readiness_2026-08-21.json"


def _load(name):
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


MOD = _load("replay_readiness_2026_08_21")
DATA = json.loads(REPORT.read_text(encoding="utf-8"))


# ── ① Replay를 구현하지 않았다 ───────────────────────────────────────────
def test_replay_was_not_implemented():
    """
    §14는 Historical Replay 구현을 명시적으로 금지한다 - 2026년 데이터로 2023년
    결과를 재구성하는 것 자체가 look-ahead이기 때문이다. readiness만 판정한다.
    """
    assert DATA["implemented_replay"] is False
    assert "구현하지 않았다" in DATA["note"]


def test_no_pit_valid_is_granted_retroactively():
    """
    과거 34종목에 근거 없이 PIT_VALID를 부여하지 않는다(§14).
    A2가 READY로 바뀌려면 실제로 그 필드가 채워져야 한다.
    """
    a2 = DATA["axes"]["A2_as_of_inputs"]
    assert a2["verdict"] != "READY"
    assert "0/34" in a2["measure"]


# ── ② 평균내지 않는다 ────────────────────────────────────────────────────
def test_overall_verdict_is_the_weakest_axis_not_an_average():
    """
    평균은 치명적 공백을 '통과 가능한 숫자'로 바꾼다(§61 단일 합성점수 금지와 동일 이유).
    전체 판정은 반드시 가장 약한 축과 같아야 한다.
    """
    order = {"NOT_READY": 0, "PARTIAL": 1, "READY": 2}
    weakest = min(DATA["axes"].values(), key=lambda a: order[a["verdict"]])["verdict"]
    assert DATA["overall_verdict"] == weakest


def test_all_ten_axes_are_reported():
    """축을 조용히 빼면 판정이 실제보다 관대해진다."""
    assert len(DATA["axes"]) == 10
    for k in ("A1_historical_filings", "A2_as_of_inputs", "A3_input_preservation",
              "A4_market_data", "A5_thesis_date", "A6_prediction_state",
              "A7_valuation_inputs", "A8_source_availability",
              "A9_restatement_information",
              "A10_information_set_reproducibility"):
        assert k in DATA["axes"], k


# ── ③ 차단된 축은 사유를 남긴다 ──────────────────────────────────────────
def test_blocked_axes_state_why():
    for name, a in DATA["axes"].items():
        if a["verdict"] == "NOT_READY":
            assert a["blocking"], f"{name}: 차단인데 사유가 없다"


def test_verdicts_use_the_declared_vocabulary():
    for name, a in DATA["axes"].items():
        assert a["verdict"] in ("READY", "PARTIAL", "NOT_READY"), name


# ── ④ 임계값은 도메인 제약이다 ───────────────────────────────────────────
def test_restatement_tolerance_is_not_tuned():
    """
    0.1%는 회계 반올림·단위 표기 차이를 재작성으로 세지 않기 위한 값이다.
    조용히 완화되면 재작성 빈도가 실제보다 커 보인다.
    """
    assert MOD.RESTATEMENT_TOL == 0.001


# ── ⑤ ledger 판본 측정의 오독 방지 ───────────────────────────────────────
def test_vintage_finding_carries_the_do_not_misread_note():
    """
    "최신 판본과 일치한다"는 사실은 **더 이른 T0로 되돌릴 때만** 문제다.
    이 단서가 사라지면 "기존 34종목 분석이 look-ahead였다"로 오독된다.
    """
    a9 = DATA["axes"]["A9_restatement_information"]
    assert "틀렸다는 뜻이 아니다" in a9["note"]
    v = a9["vintage"]
    assert v["ledger_values_on_restated_periods"] > 0
    # 최초/최신 판본 구분이 실제로 작동하는지 - 둘 다 0이면 측정이 죽은 것이다
    assert (v["matches_latest_vintage_only"]
            + v["matches_first_vintage_only"]) > 0


# ── ⑥ 공식 판정에 배선하지 않았다 ────────────────────────────────────────
def test_nothing_is_wired_into_official_judgment():
    assert DATA["affects_official_judgment"] is False
