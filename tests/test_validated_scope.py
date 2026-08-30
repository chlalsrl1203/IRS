"""
validated_scope.py 테스트 (2026-08-30).

고정하는 것:
  ① 코퍼스 관측범위 안이면 빈 리스트(= 표시할 것 없음)
  ② 범위를 벗어나면 **사유가 남는다**(조용히 통과시키지 않는다)
  ③ **거르는 함수가 없다** - 이 모듈은 판정하지 않는다(병기, 자동판정 안 함)
  ④ 상수가 34종목 ledger 실측값과 일치한다(임의로 바뀌면 실패)
  ⑤ 값이 없으면 "범위 밖"으로 단정하지 않는다(데이터 없음 ≠ 위험)
"""
import inspect
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from engine import validated_scope as V  # noqa: E402


# ── ① 범위 안 ────────────────────────────────────────────────────────────
def test_inside_corpus_range_reports_nothing():
    assert V.out_of_scope_reasons(gap=0.089, market_cap=247e9) == []


def test_boundary_values_are_inside():
    """경계값 자체는 관측된 값이므로 범위 안이다."""
    assert V.out_of_scope_reasons(gap=V.CORPUS_GAP_MAX) == []
    assert V.out_of_scope_reasons(market_cap=V.CORPUS_MARKET_CAP_MIN) == []


# ── ② 범위 밖은 사유가 남는다 ────────────────────────────────────────────
def test_extreme_gap_is_flagged():
    r = V.out_of_scope_reasons(gap=0.9309)          # VATE 실측
    assert len(r) == 1 and "Gap" in r[0] and "3.8배" in r[0]


def test_microcap_is_flagged():
    r = V.out_of_scope_reasons(market_cap=30e6)     # VATE 실측 $30M
    assert len(r) == 1 and "시총" in r[0]
    assert "estimate_drs" in r[0], "왜 문제인지(중앙값 대체) 근거가 있어야 한다"


def test_both_axes_flag_independently():
    assert len(V.out_of_scope_reasons(gap=0.9309, market_cap=30e6)) == 2


def test_gap_below_corpus_min_is_flagged():
    assert V.out_of_scope_reasons(gap=-0.30)


# ── ③ 거르지 않는다 ──────────────────────────────────────────────────────
def test_module_exposes_no_filter_or_verdict_function():
    """
    이 모듈이 컷오프로 변질되는 것을 구조적으로 막는다. 범위 밖을 자동으로
    탈락시키면 이 프로젝트가 반복 금지해온 "근거 없는 임계값 신설"이 된다
    (LYNCH_TYPE_CAPS·P/B 임계값·screener competition_intensity 선례).
    """
    banned = ("filter", "reject", "exclude", "drop", "verdict", "judge", "decide")
    for name, obj in vars(V).items():
        if name.startswith("_") or not inspect.isfunction(obj):
            continue
        assert not any(b in name.lower() for b in banned), \
            f"{name}: validated_scope는 표시만 한다 - 거르는 함수를 두지 않는다"


def test_returns_reasons_not_boolean():
    """bool을 돌려주면 호출부가 곧바로 필터로 쓰게 된다 - 사유 문자열을 준다."""
    r = V.out_of_scope_reasons(gap=0.9309)
    assert isinstance(r, list) and all(isinstance(x, str) for x in r)


# ── ④ 상수는 코퍼스 실측값 ───────────────────────────────────────────────
def test_constants_match_measured_corpus_range():
    assert V.CORPUS_GAP_MAX == 0.2438           # ACGL
    assert V.CORPUS_GAP_MIN == -0.1436          # KEYS
    assert V.CORPUS_MARKET_CAP_MIN == 3.74e9    # MNDY
    assert V.CORPUS_MARKET_CAP_MAX == 817.9e9   # PDD


def test_validation_status_states_range_is_not_a_correctness_claim():
    s = V.VALIDATION_STATUS["corpus_range"]
    assert "OBSERVED_RANGE_ONLY" in s
    assert "생존편향" in s, "범위 밖을 실측하지 못한 이유가 명시돼야 한다"


# ── ⑤ 데이터 없음 ≠ 범위 밖 ──────────────────────────────────────────────
def test_missing_values_are_not_treated_as_out_of_scope():
    assert V.out_of_scope_reasons() == []
    assert V.out_of_scope_reasons(gap=None, market_cap=None) == []


def test_nonpositive_market_cap_is_not_flagged_as_microcap():
    """시총 0/음수는 별도 가드(build_candidate)가 이미 막는다 - 여기서 중복 판정하지 않는다."""
    assert V.out_of_scope_reasons(market_cap=0) == []
