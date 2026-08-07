"""
Self-Check v2 (v3.15 신규)

기존 run_self_check(answers)의 결함(불리언 자기신고만 받고 메모 텍스트를
전혀 검증하지 않음, 18개 호출 인스턴스 전체에서 확인)을 보완하기 위해
메모 원문(memo_text)과 계산 컨텍스트(ctx)를 받아 실제 대조 검증을
수행한다.

ctx는 아래 키를 포함해야 한다(해당 없는 항목은 None):
    - implied_growth: float (예: 0.1592 = 15.92%)
    - realistic_growth: float
    - expectation_gap: float (realistic - implied)
    - drs: float
    - rar: float
    - tolerance: float, 기본 0.001 (0.1%p 이내 일치로 간주)
"""

import re


def _extract_pct_after_label(memo_text: str, label: str):
    """memo_text에서 'label ... 12.34%' 패턴을 찾아 소수(0.1234)로 반환. 못 찾으면 None."""
    pattern = re.escape(label) + r".{0,40}?(-?\d+\.?\d*)\s*%"
    m = re.search(pattern, memo_text)
    if not m:
        return None
    return float(m.group(1)) / 100


def _check_implied_growth(memo_text: str, ctx: dict, tol: float) -> tuple:
    if ctx.get("implied_growth") is None:
        return True, None  # Model Not Applicable 케이스 등, 검증 대상 아님
    found = _extract_pct_after_label(memo_text, "Implied Growth")
    if found is None:
        return False, "메모에서 'Implied Growth' 수치를 찾을 수 없음"
    if abs(found - ctx["implied_growth"]) > tol:
        return False, f"메모 기재값({found*100:.2f}%)이 계산값({ctx['implied_growth']*100:.2f}%)과 불일치"
    return True, None


def _check_realistic_growth(memo_text: str, ctx: dict, tol: float) -> tuple:
    if ctx.get("realistic_growth") is None:
        return True, None
    found = _extract_pct_after_label(memo_text, "Realistic Growth")
    if found is None:
        return False, "메모에서 'Realistic Growth' 수치를 찾을 수 없음"
    if abs(found - ctx["realistic_growth"]) > tol:
        return False, f"메모 기재값({found*100:.2f}%)이 계산값({ctx['realistic_growth']*100:.2f}%)과 불일치"
    return True, None


def _check_expectation_gap(memo_text: str, ctx: dict, tol: float) -> tuple:
    if ctx.get("expectation_gap") is None:
        return True, None
    found = _extract_pct_after_label(memo_text, "Expectation Gap")
    if found is None:
        return False, "메모에서 'Expectation Gap' 수치를 찾을 수 없음"
    if abs(found - ctx["expectation_gap"]) > tol:
        return False, f"메모 기재값({found*100:.2f}%p)이 계산값({ctx['expectation_gap']*100:.2f}%p)과 불일치"
    return True, None


def _check_drs(memo_text: str, ctx: dict, tol_abs: float = 0.5) -> tuple:
    if ctx.get("drs") is None:
        return True, None
    m = re.search(r"DRS\s*[:=]?\s*(\d+\.?\d*)", memo_text)
    if not m:
        return False, "메모에서 'DRS' 수치를 찾을 수 없음"
    found = float(m.group(1))
    if abs(found - ctx["drs"]) > tol_abs:
        return False, f"메모 기재 DRS({found})가 계산값({ctx['drs']})과 불일치"
    return True, None


def _check_rar(memo_text: str, ctx: dict, tol_abs: float = 0.01) -> tuple:
    if ctx.get("rar") is None:
        return True, None
    m = re.search(r"RAR\s*[:=]?\s*(-?\d+\.?\d*)", memo_text)
    if not m:
        return False, "메모에서 'RAR' 수치를 찾을 수 없음"
    found = float(m.group(1))
    if abs(found - ctx["rar"]) > tol_abs:
        return False, f"메모 기재 RAR({found})가 계산값({ctx['rar']})과 불일치"
    return True, None


def _check_bear_case_present(memo_text: str, ctx: dict, tol=None) -> tuple:
    if "Bear Case" not in memo_text and "10. Bear" not in memo_text:
        return False, "메모에 Bear Case 섹션이 없음"
    return True, None


def _check_final_conclusion_present(memo_text: str, ctx: dict, tol=None) -> tuple:
    keywords = ["매수", "보류", "회피", "저평가", "과대평가", "적정가"]
    if "결론" not in memo_text:
        return False, "메모에 '결론' 표기가 없음"
    if not any(k in memo_text for k in keywords):
        return False, "메모 결론에 판정 키워드(매수/보류/회피/저평가/과대평가/적정가)가 없음"
    return True, None


_CHECKS = [
    ("Implied Growth 재현", _check_implied_growth),
    ("Realistic Growth 재현", _check_realistic_growth),
    ("Expectation Gap 재현", _check_expectation_gap),
    ("DRS 일치", _check_drs),
    ("RAR 일치", _check_rar),
    ("Bear Case 섹션 존재", _check_bear_case_present),
    ("최종 결론 존재 및 판정 명시", _check_final_conclusion_present),
]


def run_self_check_v2(memo_text: str, ctx: dict) -> None:
    """
    메모 원문과 계산 컨텍스트를 대조해 7개 항목을 실제로 검증한다.
    하나라도 실패하면 ValueError로 상세 사유를 담아 발행을 막는다.
    통과하면 통과 로그를 출력한다.
    """
    if not memo_text or not memo_text.strip():
        raise ValueError("memo_text가 비어있음 — 실제 메모 본문을 넣어야 함(불리언 자기신고 금지, v3.15)")

    tol = ctx.get("tolerance", 0.001)
    failed = []
    for name, check_fn in _CHECKS:
        ok, reason = check_fn(memo_text, ctx, tol)
        if not ok:
            failed.append(f"{name}: {reason}")

    if failed:
        raise ValueError("self_check_v2 미통과 항목:\n" + "\n".join(failed))

    print(f"Self-check v2 전체 통과 ({len(_CHECKS)}개 항목). 메모 발행 가능.")
