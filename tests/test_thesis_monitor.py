"""
engine/thesis_monitor.py 테스트 (v3.42).

이 모듈은 "판정을 낸 뒤 그 판정이 아직 살아있는지" 감시한다 - 결과가 공식
판정을 오염시키면 안 되고(설계원칙 1), 기한이 지난 조건을 자동으로 반증됨이라
단정해도 안 된다(설계원칙 2). 그 두 가지를 코드로 고정한다.
"""

import glob
import json
import os
from datetime import date

import pytest

from engine.thesis_monitor import (
    extract_trigger_dates,
    inputs_from_ledger,
    recompute_gap_at_market_cap,
    scan_falsification_conditions,
)


def _load(ticker):
    paths = sorted(glob.glob(f"ledger/{ticker}_*.json"))
    assert paths, f"ledger/{ticker}_*.json 없음"
    with open(paths[-1], encoding="utf-8") as f:
        return json.load(f)


# ── 날짜 추출 ────────────────────────────────────────────────────────────

def test_extract_handles_every_format_actually_used_in_ledgers():
    """
    실제 반증조건에 쓰인 표기만 지원한다(없는 형식을 미리 넣지 않는 게 원칙).
    여기 있는 형식들은 전부 ledger 원문에서 관측된 것이다.
    """
    text = ("2026-08-05 Q2 실적, 2027-08~2027-10경 발표, Q3 2026 확정치, "
            "2026년 8월 31일 예정, 전환시한(2026-12-02)")
    got = {d["raw"]: d["date"] for d in extract_trigger_dates(text)}

    assert got["2026-08-05"] == date(2026, 8, 5)
    assert got["2027-08"] == date(2027, 8, 1)      # 일 없는 표기는 1일로
    assert got["Q3 2026"] == date(2026, 9, 30)     # 분기는 분기말로
    assert got["2026년 8월 31일"] == date(2026, 8, 31)
    assert got["2026-12-02"] == date(2026, 12, 2)


def test_extract_returns_context_so_analyst_can_triage():
    """
    설계원칙 (2): 정규식은 트리거 날짜와 서술적 날짜를 구분하지 못한다.
    자동 필터링 대신 문맥을 함께 돌려줘 사람이 분류하게 한다 - TCOM의
    소송 집단기간(2024-04-30~2026-01-13)이 실제 오탐 사례다.
    """
    text = "De Wilde 증권소송(E.D.N.Y., 집단기간 2024-04-30~2026-01-13)이 화해되면 재검토"
    got = extract_trigger_dates(text)
    assert len(got) == 2
    for d in got:
        assert "집단기간" in d["context"], "문맥이 없으면 트리거인지 분류할 수 없다"


def test_extract_does_not_crash_on_impossible_calendar_dates():
    assert extract_trigger_dates("2026-02-30에 발표") == []


def test_extract_sorts_by_date():
    got = extract_trigger_dates("2026-12-02 그리고 2026-08-05")
    assert [d["raw"] for d in got] == ["2026-08-05", "2026-12-02"]


# ── 기한도래 분류 ─────────────────────────────────────────────────────────

def _fake_ledger(fc):
    return {"meta": {"ticker": "TEST", "analyzed_at": "2026-08-01T00:00:00"},
            "inputs": {"falsification_conditions": fc}}


def test_status_past_due_when_any_date_has_passed():
    s = scan_falsification_conditions(_fake_ledger("2026-08-05 실적 확인"), date(2026, 8, 13))
    assert s["status"] == "past_due"
    assert len(s["past_due"]) == 1 and not s["pending"]


def test_status_pending_when_all_dates_are_future():
    s = scan_falsification_conditions(_fake_ledger("2026-12-02 시한"), date(2026, 8, 13))
    assert s["status"] == "pending"
    assert not s["past_due"] and len(s["pending"]) == 1


def test_status_undated_is_not_a_defect():
    """
    사건 기반 조건(ACGL의 '3개 분기 연속 악화되면')은 날짜가 없는 게 정상이다.
    이걸 결함으로 처리하면 멀쩡한 반증조건이 노이즈로 묻힌다.
    """
    s = scan_falsification_conditions(
        _fake_ledger("컴바인드레이쇼가 3개 분기 연속 악화되면 재검토"), date(2026, 8, 13))
    assert s["status"] == "undated"


def test_status_no_conditions_when_field_empty():
    """
    반증조건이 빈 것도 결함이 아니다 - 과거 분석에 소급 작성하는 건 사후
    합리화라 금지돼 있어(v3.24) 구 ledger는 비어있는 게 정상이다.
    """
    s = scan_falsification_conditions(_fake_ledger(None), date(2026, 8, 13))
    assert s["status"] == "no_conditions"


# ── 시가총액 부식 재계산 ──────────────────────────────────────────────────

def test_ledger_inputs_survive_json_roundtrip_with_int_year_keys():
    """
    JSON은 객체 키를 문자열로만 저장하므로 연도 키가 "2020"이 된다 - 그대로
    엔진에 넣으면 연도 뺄셈에서 TypeError가 난다(v3.38에서 KRX 래퍼가 실제로
    겪은 함정). 복원이 정수 키로 되는지 고정한다.
    """
    inputs = inputs_from_ledger(_load("BSX"))
    assert all(isinstance(k, int) for k in inputs.revenue_by_year)
    assert all(isinstance(k, int) for k in inputs.capex_by_year)


def test_realistic_growth_is_invariant_to_market_cap():
    """
    Realistic Growth는 재무 시계열에서만 나온다 - 시총이 여기 영향을 주면
    '시장가가 성장추정을 오염시키는' 심각한 버그다.
    """
    led = _load("BSX")
    r = recompute_gap_at_market_cap(led, led["inputs"]["market_cap"] * 1.5)
    assert r["realistic_growth_now"] == pytest.approx(r["realistic_growth_then"], abs=1e-12)


def test_gap_widens_when_price_falls_and_narrows_when_price_rises():
    """
    TTD 실사례의 일반형: 주가가 빠지면 Gap은 벌어진다(더 싸 보인다).
    **이게 가치함정의 원리다** - 사업이 나빠져 주가가 빠져도 Gap은 좋아지므로
    Gap 단독으로는 절대 판단하면 안 되고 반증조건과 함께 봐야 한다.
    """
    led = _load("BSX")
    mc = led["inputs"]["market_cap"]
    cheaper = recompute_gap_at_market_cap(led, mc * 0.7)
    pricier = recompute_gap_at_market_cap(led, mc * 1.3)

    assert cheaper["gap_now"] > led["expectation_gap"] > pricier["gap_now"]
    assert cheaper["gap_decay_pp"] > 0 > pricier["gap_decay_pp"]


def test_recompute_never_writes_to_ledger_dir():
    """
    설계원칙 (1): 재계산은 오늘 날짜로 스탬프된 완전한 결과를 만들어내는데
    이걸 저장하면 같은 티커의 ledger가 2개가 되어 test_ledger_integrity의
    '종목당 1건' 규칙이 즉시 깨진다(v3.32 WM/WCN/IDXX 중복 사고와 동일 유형).
    """
    before = set(os.listdir("ledger"))
    recompute_gap_at_market_cap(_load("BSX"), 1e11)
    assert set(os.listdir("ledger")) == before


def test_recompute_rejects_nonpositive_market_cap():
    with pytest.raises(ValueError):
        recompute_gap_at_market_cap(_load("BSX"), 0)


# ----------------------------------------------------------------------
# Drift 3분할 (v3.50, 계약서 §9)
# ----------------------------------------------------------------------

import glob as _glob  # noqa: E402
import json as _json  # noqa: E402

from dataclasses import replace as _replace  # noqa: E402

from engine.pipeline import run_analysis as _run  # noqa: E402
from engine.thesis_monitor import (  # noqa: E402
    DRIFT_KINDS,
    decompose_drift,
    inputs_from_ledger,
)

_BSX = _json.load(open(sorted(_glob.glob("ledger/BSX_*.json"))[-1], encoding="utf-8"))


def _bsx_inputs():
    return inputs_from_ledger(_BSX)


def test_drift_identity_holds_exactly():
    """
    ΔGap = ΔRealisticGrowth - ΔImpliedGrowth 는 대수 항등식이다. 잔차가 0이
    아니면 세 갈래 중 하나가 잘못 계산된 것이다.
    """
    base = _bsx_inputs()
    now = _run(_replace(base, market_cap=base.market_cap * 0.7))
    d = decompose_drift(_BSX, now)
    assert d["identity"]["residual"] == pytest.approx(0.0, abs=1e-12)


def test_price_only_change_leaves_fundamental_drift_at_zero():
    """주가만 변하면 펀더멘털 drift는 정확히 0이어야 한다(재무제표 불변)."""
    base = _bsx_inputs()
    now = _run(_replace(base, market_cap=base.market_cap * 0.7))
    d = decompose_drift(_BSX, now)

    assert d["fundamental_drift"]["change_pp"] == pytest.approx(0.0, abs=1e-12)
    assert d["expectation_drift"]["change_pp"] != 0.0
    assert d["dominant_drift"] == "expectation"


def test_two_stage_ticker_does_not_crash_on_tuple_return():
    """
    ⚠️ 회귀 테스트: `implied_growth_two_stage()`는 (성장률, 로그, 반복) 튜플을
    돌려주는데 초판이 튜플째로 뺄셈해 TypeError를 냈다. 골든케이스(CDNS)가
    single_stage라 테스트를 통과했고, two_stage 종목에서만 터졌다.
    """
    assert _BSX["implied_growth"]["model_used"] == "two_stage", "테스트 전제 변경됨"
    base = _bsx_inputs()
    now = _run(_replace(base, market_cap=base.market_cap * 0.8))
    d = decompose_drift(_BSX, now)
    assert isinstance(d["price_drift"]["implied_growth_contribution"], float)


def test_value_trap_pattern_is_flagged():
    """
    ⚠️ 가장 위험한 조합: 근거 기반 기대가 **낮아졌는데** Gap은 벌어짐.
    v3.42 TTD가 정확히 이 패턴이었다(주가 -26.3%, Gap +3.95%p, 동시에
    반증조건 3개 발동). Gap만 보면 "더 싸졌다"로 읽힌다.
    """
    base = _bsx_inputs()
    latest = max(base.revenue_by_year)
    # ⚠️ 배율 선택에 근거가 있다. **주가가 펀더멘털보다 더 빠져야** 가치함정
    # 패턴이 된다 - 초판은 펀더멘털을 너무 심하게(-45%) 훼손시켜 Gap이 오히려
    # 좁아졌고(-7.59%p) 전제 자체가 깨졌다. 아래 배율은 펀더 -1.45%p / Gap
    # +3.95%p를 만드는데, 이는 v3.42가 TTD에서 실측한 Gap 확대폭(+3.95%p)과
    # 정확히 같은 크기다.
    rev = dict(base.revenue_by_year); rev[latest] = rev[latest] * 0.95
    ocf = dict(base.operating_cashflow_by_year); ocf[latest] = ocf[latest] * 0.95
    opi = dict(base.operating_income_by_year); opi[latest] = opi[latest] * 0.95

    now = _run(_replace(base, market_cap=base.market_cap * 0.6,
                        revenue_by_year=rev, operating_cashflow_by_year=ocf,
                        operating_income_by_year=opi))
    d = decompose_drift(_BSX, now)

    assert d["fundamental_drift"]["change_pp"] < 0, "테스트 전제(펀더멘털 악화) 미성립"
    assert d["gap_change_pp"] > 0, "테스트 전제(Gap 확대) 미성립"
    assert "가치함정 주의" in d["interpretation"]


def test_expectation_drift_contains_price_drift_and_must_not_be_summed():
    """
    ⚠️ Expectation Drift는 Price Drift를 **포함한다**(Implied Growth가 시총과
    FCF0 양쪽에 의존). 둘을 더하면 이중계상이다 - 그래서 이 함수는 합계를
    만들지 않는다.
    """
    base = _bsx_inputs()
    now = _run(_replace(base, market_cap=base.market_cap * 0.7))
    d = decompose_drift(_BSX, now)

    assert "더하지 말 것" in d["expectation_drift"]["note"]
    assert "total_drift" not in d and "drift_sum" not in d


def test_drift_does_not_assign_thesis_status():
    """
    §9: "완전 자동 판정을 서두르지 마라." drift는 크기와 방향만 내놓고,
    STRENGTHENING/INVALIDATED 같은 상태는 분석자가 기록한 증거로 정해진다.
    """
    base = _bsx_inputs()
    now = _run(_replace(base, market_cap=base.market_cap * 0.7))
    d = decompose_drift(_BSX, now)

    blob = _json.dumps(d, ensure_ascii=False, default=str)
    for status in ("STRENGTHENING", "WEAKENING", "INVALIDATED", "STABLE"):
        assert status not in blob, f"drift가 thesis 상태({status})를 판정하고 있다"


def test_drift_kinds_vocabulary():
    assert DRIFT_KINDS == ("price", "fundamental", "expectation")
