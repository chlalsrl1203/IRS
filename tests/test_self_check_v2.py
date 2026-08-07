import pytest

from engine.self_check_v2 import run_self_check_v2


FULL_MEMO = """
5. Expectation Gap
Implied Growth: 15.92%
Realistic Growth: 18.00%
Expectation Gap: 2.08%p

6. DRS
DRS: 55

7. RAR
RAR: 0.05

10. Bear Case
매출 둔화 리스크가 존재한다.

결론: 매수 (저평가 가능성)
"""

FULL_CTX = {
    "implied_growth": 0.1592,
    "realistic_growth": 0.18,
    "expectation_gap": 0.0208,
    "drs": 55,
    "rar": 0.05,
}


def test_run_self_check_v2_passes_when_memo_matches_ctx():
    run_self_check_v2(FULL_MEMO, FULL_CTX)


def test_run_self_check_v2_fails_on_implied_growth_mismatch():
    bad_memo = FULL_MEMO.replace("Implied Growth: 15.92%", "Implied Growth: 10.00%")
    with pytest.raises(ValueError) as exc_info:
        run_self_check_v2(bad_memo, FULL_CTX)
    assert "Implied Growth" in str(exc_info.value)


def test_run_self_check_v2_fails_when_bear_case_missing():
    bad_memo = FULL_MEMO.replace("10. Bear Case\n매출 둔화 리스크가 존재한다.\n", "")
    with pytest.raises(ValueError) as exc_info:
        run_self_check_v2(bad_memo, FULL_CTX)
    assert "Bear Case" in str(exc_info.value)


def test_run_self_check_v2_fails_when_conclusion_missing():
    bad_memo = FULL_MEMO.replace("결론: 매수 (저평가 가능성)", "")
    with pytest.raises(ValueError) as exc_info:
        run_self_check_v2(bad_memo, FULL_CTX)
    assert "결론" in str(exc_info.value)


def test_run_self_check_v2_fails_on_empty_memo_text():
    with pytest.raises(ValueError) as exc_info:
        run_self_check_v2("", FULL_CTX)
    assert "memo_text가 비어있음" in str(exc_info.value)


def test_run_self_check_v2_skips_check_when_ctx_value_is_none():
    memo_without_implied_growth = FULL_MEMO.replace("Implied Growth: 15.92%\n", "")
    ctx = dict(FULL_CTX)
    ctx["implied_growth"] = None  # 예: Model Not Applicable 케이스
    run_self_check_v2(memo_without_implied_growth, ctx)
