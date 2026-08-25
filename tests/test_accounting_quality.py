"""
engine/accounting_quality.py(v3.70) 고정 테스트.

고정하는 것 세 가지:
  ① 합성점수를 만들지 않는다(§31 안티기능 등록부)
  ② `run_analysis()`에 배선돼 있지 않다(미검증 변수가 판정을 바꾸면 안 됨)
  ③ SBC를 되돌리는 것이 이 지표의 존재 이유다 - 안 되돌리면 SBC 강도 재측정
"""
import ast
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.accounting_quality import (  # noqa: E402
    OBSERVED_RANGE,
    VALIDATION_STATUS,
    accounting_quality_profile,
    accrual_ratio_series,
)


# ── ① 합성점수 금지 (§31) ───────────────────────────────────────────────
def test_no_composite_score_is_produced():
    """
    Piotroski F-Score류 0~9 합산은 §31에 '만들지 않는 것'으로 등록돼 있다.
    반환 dict에 점수·판정류 키가 생기면 그 등록을 조용히 뒤집는 것이다.
    """
    p = accounting_quality_profile(
        {2021: 100, 2022: 120, 2023: 140},
        {2021: 150, 2022: 170, 2023: 190},
        {2021: 1000, 2022: 1100, 2023: 1200},
    )
    banned = {"score", "f_score", "composite", "rating", "grade", "judgment",
              "total_score", "points"}
    assert not (banned & set(p)), f"합성점수/판정 키가 생겼다: {banned & set(p)}"
    assert "composite_score" in VALIDATION_STATUS
    assert "DELIBERATELY_ABSENT" in VALIDATION_STATUS["composite_score"]


def test_module_does_not_define_a_scoring_function():
    src = (ROOT / "engine" / "accounting_quality.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    names = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
    for n in names:
        assert "score" not in n.lower(), f"점수 함수가 생겼다: {n}"


# ── ② 판정 경로에 배선되지 않았다 ───────────────────────────────────────
def test_not_wired_into_run_analysis():
    """
    이 지표는 IRS 표본에서 성과와의 관계가 검증된 바 없다. 배선하면 미검증
    변수가 34종목 판정을 즉시 바꾼다 - growth_quality.py와 동일한 판단.
    """
    pipeline = (ROOT / "engine" / "pipeline.py").read_text(encoding="utf-8")
    assert "accounting_quality" not in pipeline, \
        "accounting_quality가 pipeline에 배선됐다 - 승격은 별도 실증 이후여야 한다"


def test_validation_status_admits_no_performance_evidence():
    assert "검증된 바 없다" in VALIDATION_STATUS["accrual_ratio"]
    assert "PROXY_ONLY" in VALIDATION_STATUS["accrual_ratio"]


# ── ③ SBC 되돌림이 핵심 - 이 모듈의 존재 이유 ───────────────────────────
def test_sbc_addback_changes_the_result():
    ni = {2021: 100, 2022: 110, 2023: 120}
    ocf = {2021: 300, 2022: 320, 2023: 340}
    ta = {2021: 1000, 2022: 1000, 2023: 1000}
    sbc = {2021: 150, 2022: 160, 2023: 170}

    naive = accrual_ratio_series(ni, ocf, ta)
    adj = accrual_ratio_series(ni, ocf, ta, sbc)
    assert adj[2023] > naive[2023], "SBC를 되돌리면 발생액이 덜 음수여야 한다"
    assert adj[2023] == pytest.approx((120 - 340 + 170) / 1000)


def test_missing_sbc_is_flagged_not_silently_accepted():
    """
    SBC 없이 계산한 값을 조용히 내보내면 SBC 강도를 회계품질로 오독하게 된다 -
    RQ-001이 FCF/영업이익에서 잡은 함정과 같은 것이다.
    """
    p = accounting_quality_profile({2021: 100, 2022: 110},
                                   {2021: 200, 2022: 210},
                                   {2021: 1000, 2022: 1000})
    assert p["sbc_adjusted"] is False
    assert any("SBC 미반영" in n for n in p["notes"])

    p2 = accounting_quality_profile({2021: 100, 2022: 110},
                                    {2021: 200, 2022: 210},
                                    {2021: 1000, 2022: 1000},
                                    {2021: 50, 2022: 55})
    assert p2["sbc_adjusted"] is True
    assert not any("SBC 미반영" in n for n in p2["notes"])


# ── ④ 계산 규약 ─────────────────────────────────────────────────────────
def test_first_year_is_skipped_because_average_assets_needs_prior_year():
    s = accrual_ratio_series({2021: 10, 2022: 20}, {2021: 5, 2022: 8},
                             {2021: 100, 2022: 200})
    assert 2021 not in s, "첫 해는 평균총자산을 만들 수 없으므로 나오면 안 된다"
    assert s[2022] == pytest.approx((20 - 8) / 150)


def test_sign_convention_positive_means_earnings_exceed_cash():
    """양수 = 회계이익 > 현금이익(Sloan 기준 주의 방향)."""
    watch = accrual_ratio_series({2021: 10, 2022: 100}, {2021: 10, 2022: 20},
                                 {2021: 1000, 2022: 1000})
    conservative = accrual_ratio_series({2021: 10, 2022: 20},
                                        {2021: 10, 2022: 100},
                                        {2021: 1000, 2022: 1000})
    assert watch[2022] > 0
    assert conservative[2022] < 0


def test_nonpositive_assets_are_skipped_not_crashed():
    s = accrual_ratio_series({2021: 10, 2022: 20}, {2021: 5, 2022: 8},
                             {2021: -100, 2022: 50})
    assert s == {}, "평균총자산이 0 이하인 해는 조용히 빠져야 한다(예외 아님)"


def test_empty_series_raises_rather_than_returning_garbage():
    with pytest.raises(ValueError):
        accrual_ratio_series({}, {2022: 1}, {2022: 1})


def test_out_of_observed_range_is_flagged_as_unseen_not_as_threshold():
    p = accounting_quality_profile({2021: 10, 2022: 500}, {2021: 10, 2022: 10},
                                   {2021: 1000, 2022: 1000})
    note = " ".join(p["notes"])
    assert "관측범위 밖" in note
    assert "임계값이 아니라" in note, "관측범위를 임계값처럼 쓰면 안 된다"


# ── ⑤ 34종목 실측 재현 (RQ-003) ─────────────────────────────────────────
def test_observed_constants_match_the_measured_corpus():
    """
    상수가 지어낸 값이 아니라 2026-08-24 34종목 실측에서 나왔음을 고정한다.
    나중에 누가 임의로 바꾸면 이 테스트가 잡는다.
    """
    assert OBSERVED_RANGE[0] == pytest.approx(-0.0829, abs=1e-4)
    assert OBSERVED_RANGE[1] == pytest.approx(0.0169, abs=1e-4)
    assert OBSERVED_RANGE[0] < OBSERVED_RANGE[1]
