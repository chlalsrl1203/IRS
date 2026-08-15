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
