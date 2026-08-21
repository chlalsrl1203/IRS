"""
Repo 03·04·17 Research Validation 테스트.

# SOURCE:
https://github.com/stefan-jansen/machine-learning-for-trading ·
https://github.com/CPZ-Lab/cpz-quant (Apache-2.0) · https://github.com/microsoft/qlib

고정하는 불변조건:
  ① 없는 데이터로 통계를 만들지 않는다 (PBO·DSR은 계산 시도조차 안 함)
  ② 리포트 1건 = 검정 1회가 아니다 (시나리오 수를 밝히면 그 수를 센다)
  ③ 파싱 실패와 실제 0건을 구분한다
  ④ 생존율이 ledger 전체에 적용되는 것으로 오독되지 않는다
  ⑤ FWER 포화를 계산 오류로 오독하지 않는다
  ⑥ 보정을 자동 적용하지 않는다 (적용할 p값이 없다)
"""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.quant.validation import (  # noqa: E402
    SCREEN_BUCKETS, VALIDATION_STATUS, _parse_screen_buckets,
    count_tests_on_sample, familywise_error, multiple_testing_report,
    sharpe_based_metrics_available, survivorship_report,
)


# ── ① 없는 데이터로 통계를 만들지 않는다 ────────────────────────────────
def test_pbo_dsr_refuses_to_compute_without_return_series():
    """
    §31 등록부의 포트폴리오 최적화 REJECT와 같은 판단 — 없는 데이터로 돌리면
    "정밀해 보이는 허구"가 된다.
    """
    r = sharpe_based_metrics_available()
    assert r["available"] is False
    assert r["has_return_series"] is False
    assert "종목별 수익률 시계열" in r["blocking_inputs"]
    assert "NOT_APPLICABLE" in VALIDATION_STATUS["pbo_dsr"]
    # 계산 결과를 흉내낸 필드가 없어야 한다
    for fabricated in ("pbo", "dsr", "sharpe", "psr"):
        assert fabricated not in r


def test_pbo_report_states_the_real_entry_price_coverage():
    """진입가조차 9/34뿐이라는 사실을 숨기지 않는다."""
    r = sharpe_based_metrics_available()
    assert r["n_tickers"] > 0
    assert r["n_with_entry_price"] < r["n_tickers"]


# ── ② 리포트 1건 ≠ 검정 1회 ─────────────────────────────────────────────
def test_self_reported_scenario_counts_are_used(tmp_path):
    """R-001 하나가 9,675개 시나리오를 검사했다 — 1로 세면 안 된다."""
    d = tmp_path / "reports"
    d.mkdir()
    (d / "big.json").write_text(
        json.dumps({"total_valid_scenarios_examined": 9675}), encoding="utf-8")
    (d / "small.json").write_text(json.dumps({"result": "x"}), encoding="utf-8")
    c = count_tests_on_sample(str(d / "*.json"), str(tmp_path / "none" / "*.json"))
    assert c["n_reports"] == 2
    assert c["counted_tests"] == 9675 + 1
    assert c["unknown_scenario_counts"] == ["small.json"]


def test_unknown_scenario_count_is_recorded_not_silently_assumed():
    """모르는 것을 1로 확정하지 않는다 — 1로 세되 그 사실을 남긴다."""
    c = count_tests_on_sample()
    assert c["counted_tests"] >= c["n_reports"]
    assert isinstance(c["unknown_scenario_counts"], list)
    # 실측: 대부분의 리포트는 시나리오 수를 스스로 밝히지 않는다
    assert len(c["unknown_scenario_counts"]) > 0


def test_broken_json_does_not_break_counting(tmp_path):
    d = tmp_path / "reports"
    d.mkdir()
    (d / "ok.json").write_text(json.dumps({"a": 1}), encoding="utf-8")
    (d / "broken.json").write_text("{not json", encoding="utf-8")
    c = count_tests_on_sample(str(d / "*.json"), str(tmp_path / "none" / "*.json"))
    assert c["n_reports"] == 1          # 깨진 파일이 전체 집계를 막지 않는다


# ── ③ 파싱 실패 ≠ 0건 ───────────────────────────────────────────────────
def test_unbalanced_bracket_yields_none_not_zero(tmp_path):
    """파싱 실패를 0건으로 만들면 '탈락 없음'으로 오독된다."""
    p = tmp_path / "screen_broken.py"
    p.write_text('PREFILTERED_OUT = {\n    "AAA": "설명이 끝나지 않음',
                 encoding="utf-8")
    out = _parse_screen_buckets(str(p))
    assert out["PREFILTERED_OUT"] is None


def test_candidates_appended_after_empty_literal_are_found(tmp_path):
    """
    ⚠️ 실제 결함의 회귀 테스트. 스크리닝 스크립트는 `CANDIDATES = []`로 시작한 뒤
    `CANDIDATES.append(Candidate(ticker="META", ...))`로 채운다. 리터럴 블록만
    파싱한 초판은 **항상 0건**을 냈다.
    """
    p = tmp_path / "screen_x.py"
    p.write_text(
        'CANDIDATES = []\n\n'
        '# 주석\n'
        'CANDIDATES.append(Candidate(\n'
        '    ticker="META", name="Meta Platforms",\n'
        '))\n'
        'CANDIDATES.append(Candidate(\n'
        '    ticker="BSX", name="Boston Scientific",\n'
        '))\n',
        encoding="utf-8")
    out = _parse_screen_buckets(str(p))
    assert out["CANDIDATES"] == ["BSX", "META"]


def test_dict_keys_with_company_names_are_parsed(tmp_path):
    """딕셔너리 키가 `"KR(Kroger)"` 형태다 — 괄호를 못 벗기면 통째로 놓친다."""
    p = tmp_path / "screen_y.py"
    p.write_text(
        'PREFILTERED_OUT = {\n'
        '    "KR(Kroger)": "매출 박스권",\n'
        '    "AGCO": "2년 연속 역성장",\n'
        '}\n', encoding="utf-8")
    out = _parse_screen_buckets(str(p))
    assert out["PREFILTERED_OUT"] == ["AGCO", "KR"]


def test_prose_capitals_are_not_mistaken_for_tickers(tmp_path):
    """설명 문자열 안의 대문자를 티커로 세면 탈락 수가 부풀려진다."""
    p = tmp_path / "screen_z.py"
    p.write_text(
        'PREFILTERED_OUT = {\n'
        '    "KR(Kroger)": "WebSearch 결과 FY2023 대비 EBITDA 악화",\n'
        '}\n', encoding="utf-8")
    assert _parse_screen_buckets(str(p))["PREFILTERED_OUT"] == ["KR"]


# ── ④ 생존율 오독 방지 ──────────────────────────────────────────────────
def test_survivorship_separates_screening_sourced_from_the_rest():
    """
    ledger 종목이 전부 스크리닝을 거친 게 아니다 — 상당수는 스크리닝 스크립트가
    생기기 전 경로로 들어왔다. 이 구분 없이 생존율을 읽으면 ledger 전체에
    적용되는 것으로 오독된다.
    """
    s = survivorship_report()
    assert s["n_ledger_from_screening"] + s["n_ledger_not_from_screening"] == \
        s["n_ledger_tickers"]
    assert s["n_ledger_not_from_screening"] > 0     # 실측: 26종목
    assert "부분집합에만" in s["note"]


def test_survivorship_finds_real_rejected_tickers():
    """스크리닝 탈락 기록이 실제로 파싱되는지 — 0이면 편향을 못 잰다."""
    s = survivorship_report()
    assert s["n_considered_in_screening"] > s["n_ledger_from_screening"]
    assert s["n_rejected"] > 0
    assert s["parse_failures"] == []
    # 실측으로 확인된 탈락 종목이 실제로 잡히는지
    assert "KR" in s["rejected_tickers"] and "AGCO" in s["rejected_tickers"]


def test_survivorship_declares_it_is_a_lower_bound():
    """기록되지 않은 탈락은 셀 수 없다."""
    s = survivorship_report()
    assert 0.0 <= s["survival_rate_lower_bound"] <= 1.0
    assert "하한" in s["note"]
    assert "하한" in VALIDATION_STATUS["survivorship"]


def test_every_declared_bucket_is_actually_parsed():
    s = survivorship_report()
    assert set(s["by_bucket"]) == set(SCREEN_BUCKETS)


# ── ⑤ FWER 포화 ─────────────────────────────────────────────────────────
def test_fwer_saturation_is_flagged_not_mistaken_for_a_bug():
    """1.0이 나왔다고 계산이 틀린 게 아니라 지표가 정보를 잃은 것이다."""
    r = familywise_error(9702, alpha=0.05)
    assert r["fwer_upper_bound"] == pytest.approx(1.0)
    assert r["fwer_saturated"] is True
    assert "포화" in r["note"]
    assert r["expected_false_positives"] == pytest.approx(485.1)


def test_small_n_is_not_saturated():
    r = familywise_error(3, alpha=0.05)
    assert r["fwer_saturated"] is False
    assert r["fwer_upper_bound"] == pytest.approx(1 - 0.95 ** 3)
    assert r["bonferroni_alpha"] == pytest.approx(0.05 / 3)


def test_independence_assumption_is_declared_as_an_upper_bound():
    """같은 표본·같은 엔진이라 실제 FWER은 이보다 낮다."""
    r = familywise_error(100)
    assert r["independence_assumed"] is True
    assert "상한" in r["note"]


@pytest.mark.parametrize("bad", [0, -1])
def test_invalid_test_count_is_rejected(bad):
    with pytest.raises(ValueError):
        familywise_error(bad)


@pytest.mark.parametrize("bad", [0.0, 1.0, -0.1, 1.5])
def test_invalid_alpha_is_rejected(bad):
    with pytest.raises(ValueError):
        familywise_error(10, alpha=bad)


# ── ⑥ 보정을 자동 적용하지 않는다 ───────────────────────────────────────
def test_report_does_not_apply_correction_because_there_are_no_p_values():
    """
    IRS의 분석 대부분은 가설검정이 아니라 감사·서술이라 nominal p값이 없다.
    없는 p값에 보정을 적용하는 척하면 그게 바로 허구다.
    """
    r = multiple_testing_report()
    assert r["correction_applied"] is False
    assert "적용할 p값이 없기 때문이다" in r["note"]
    assert "nominal p값이 없" in VALIDATION_STATUS["multiple_testing"]


def test_report_surfaces_the_real_repository_scale():
    """이 저장소가 같은 표본을 몇 번 봤는지가 이 리포트의 핵심이다."""
    r = multiple_testing_report()
    c = r["counts"]
    assert c["n_reports"] > 20          # 실측 28건
    assert c["n_experiments"] >= 8      # 실측 9건
    assert c["counted_tests"] > 9000    # R-001의 9,675 시나리오가 포함된다


def test_module_adds_no_third_party_dependency():
    """IRS 런타임 의존성 0개 원칙을 깨지 않는다."""
    import engine.quant.validation as v
    src = open(v.__file__, encoding="utf-8").read()
    for banned in ("import numpy", "import pandas", "import scipy", "from scipy"):
        assert banned not in src
