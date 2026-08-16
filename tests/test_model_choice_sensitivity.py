"""
모델선택 민감도 분석의 불변조건 (2026-08-16).

이 테스트가 고정하는 것은 "어느 모델이 옳은가"가 아니라 - 그건 이 저장소가
판정할 근거가 없다 - **취약성을 어느 수준에서 봐야 하는가**이다.

⚠️ 이 조사 도중 실제로 밟은 오류를 회귀로 박아둔다: 처음에 판정(3단계)
수준만 보고 "현재 매수리스트 중 모델취약 종목 0건"이라 결론냈으나 틀렸다.
등급(S~F) 수준에서 보면 BRO가 A->B로 떨어지고 B는 매수 유니버스에서
제외된다 - 즉 **판정이 안 바뀌어도 자본배분은 바뀔 수 있다.**
"""
import importlib.util
import json
import os
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent


def _load_module():
    path = ROOT / "scripts" / "model_choice_sensitivity_2026_08_16.py"
    spec = importlib.util.spec_from_file_location("mcs_2026_08_16", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


MOD = _load_module()


def _results():
    out = {}
    for p in sorted((ROOT / "ledger").glob("*.json")):
        led = json.loads(p.read_text(encoding="utf-8"))
        out[led["meta"]["ticker"]] = MOD.analyze(led)
    return out


def test_grade_dependence_can_exist_without_judgment_dependence():
    """핵심 교훈: 판정(3단계) 불변인데 등급이 바뀌는 종목이 실재한다."""
    res = _results()
    only_grade = [t for t, r in res.items()
                  if r["grade_depends_on_model"] and not r["judgment_depends_on_model"]]
    assert only_grade, (
        "판정 수준만 검사하면 놓치는 종목이 있어야 한다 - 이 성질이 사라졌다면 "
        "판정/등급 경계 구조가 바뀐 것이므로 보고서를 재검토할 것"
    )


def test_buy_universe_dependence_is_reported_and_directional():
    """유니버스 편입 여부가 모델선택에 달린 종목은 방향까지 명시돼야 한다."""
    res = _results()
    dep = [r for r in res.values() if r["buy_universe_depends_on_model"]]
    assert dep, "유니버스 의존 종목이 최소 1건 있어야 한다(2026-08-16 실측 4건)"
    for r in dep:
        assert r["universe_direction"] is not None
        assert (r["grade_official"] in MOD.BUY_UNIVERSE_GRADES) != (
            r["grade_alternative"] in MOD.BUY_UNIVERSE_GRADES
        )


def test_held_position_bro_universe_membership_depends_on_model():
    """
    BRO는 실제 보유종목(2026-08-03 리스트 6.75%)인데 A등급이 모델선택에 달려 있다.
    이 사실이 조용히 사라지면(예: 입력 갱신으로) 보고서의 핵심 근거가 무효가 되므로
    변화를 감지해야 한다.
    """
    res = _results()
    assert "BRO" in res, "BRO ledger가 존재해야 한다"
    bro = res["BRO"]
    assert bro["buy_universe_depends_on_model"], (
        "BRO의 유니버스 편입이 더 이상 모델선택에 의존하지 않는다면 "
        "reports/research/model_choice_2026-08-16.md의 핵심 사례를 갱신할 것"
    )
    assert bro["reason_is_prior_record"], "BRO 선택사유는 과거기록 답습으로 분류돼야 한다"


def test_prior_record_regex_does_not_match_absence_phrasing():
    """
    '대조할 과거 기록이 없다'(정반대 의미)를 '과거기록 답습'으로 오분류하면
    안 된다 - 다수 종목의 사유에 이 표현이 들어 있다.
    """
    assert not MOD.PRIOR_RECORD_RE.search("첫 정식분석이라 대조할 과거 기록이 없다")
    assert not MOD.PRIOR_RECORD_RE.search("첫 분석이라 대조할 과거 기록 없음")
    assert MOD.PRIOR_RECORD_RE.search("과거 큐28 기록(v3.15)이 single_stage를 사용")
    assert MOD.PRIOR_RECORD_RE.search("기존 v3.13 기록의 내재성장률과 일치")


def test_analysis_never_mutates_official_values():
    """병기 원칙: 공식 Gap/판정을 재계산하거나 덮어쓰지 않는다."""
    for p in sorted((ROOT / "ledger").glob("*.json")):
        before = p.read_text(encoding="utf-8")
        led = json.loads(before)
        r = MOD.analyze(led)
        assert r["gap_official"] == pytest.approx(led["expectation_gap"], abs=1e-12)
        assert r["judgment_official"] == led["judgment"]
        assert p.read_text(encoding="utf-8") == before, "ledger 파일이 변경되면 안 된다"


def test_alternative_model_is_the_opposite_of_chosen():
    res = _results()
    for t, r in res.items():
        assert {r["model_chosen"], r["model_alternative"]} == {"single_stage", "two_stage"}, t
