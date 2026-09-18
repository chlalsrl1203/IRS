"""
engine/track_record.py 고정 테스트 (2026-09-18).

가장 중요한 두 가지를 고정한다:
  ① 정렬순서 가정 금지 - 2026-09-18 1차 측정에서 실제로 밟은 버그
     (`raw[-1]`을 최신으로 가정 -> 1년 전 종가 채택 -> BSX +92% 같은 허구)
  ② 수익률은 배당조정 시계열 안에서만 계산 - 진입 원종가와 청산 조정종가를
     섞으면 배당만큼 조용히 틀린다
"""
import json
import os

import pytest

from engine.track_record import (
    GRADE_ORDER, LEDGER_PRICE_TOLERANCE, MEASUREMENT_STATUS,
    bucket_stats, build_report, collect_cohort, entry_bar_as_known_at,
    fetch_daily_series, format_report, measure, parse_series,
    price_on_or_before,
)


# ── 진입가 시점 규칙: "그 시각에 실제로 알 수 있었던 종가" ────────────
#
# 2026-09-18 무결성 점검이 실제로 잡아낸 버그의 회귀 테스트다. ledger 57건 중
# 34건이 "기록가 != 그날 종가"로 걸렸는데, 원인은 데이터 오류가 아니라
# **분석이 미국 장 개장 전(한국 오전)에 돌아서 직전 거래일 종가를 썼기
# 때문**이었다. 날짜만 보고 그날 종가를 진입가로 쓰면 하루가 통째로 어긋난다.
_SERIES = {
    "2026-09-01": {"close": 286.08, "adj": 286.08},
    "2026-09-02": {"close": 279.79, "adj": 279.79},
    "2026-09-03": {"close": 285.75, "adj": 285.75},
    "2026-09-04": {"close": 266.51, "adj": 266.51},
}


def test_pre_market_analysis_uses_previous_trading_day_close():
    """ADBE 실측: 09-04 09:24 UTC(= 동부 05:24, 개장 전) -> 09-03 종가."""
    date, bar = entry_bar_as_known_at(_SERIES, "2026-09-04T09:24:35+00:00")
    assert date == "2026-09-03"
    assert bar["close"] == 285.75      # ledger의 price_at_analysis와 일치


def test_after_close_analysis_uses_same_day_close():
    """VRT 실측: 09-04 23:02 UTC(= 동부 19:02, 마감 후) -> 09-04 종가."""
    date, bar = entry_bar_as_known_at(_SERIES, "2026-09-04T23:02:06+00:00")
    assert date == "2026-09-04"
    assert bar["close"] == 266.51


def test_weekend_analysis_walks_back_to_friday():
    """TEAM 실측 유형: 월요일 오전(개장 전) -> 직전 금요일 종가."""
    series = {"2026-09-10": {"close": 179.57, "adj": 179.57},
              "2026-09-11": {"close": 179.70, "adj": 179.70},
              "2026-09-14": {"close": 192.77, "adj": 192.77}}
    date, bar = entry_bar_as_known_at(series, "2026-09-14T10:00:18+00:00")
    assert date == "2026-09-11" and bar["close"] == 179.70


def test_dst_boundary_is_handled_by_tzdata_not_a_fixed_utc_offset():
    """
    겨울(EST)엔 마감이 21:00 UTC라 20:30 UTC는 아직 **개장 중**이고,
    여름(EDT)엔 마감이 20:00 UTC라 같은 20:30 UTC가 **마감 후**다.
    UTC 상수 하나로 고정하면 계절에 따라 하루씩 어긋난다.
    """
    winter = {"2026-01-14": {"close": 10.0, "adj": 10.0},
              "2026-01-15": {"close": 11.0, "adj": 11.0}}
    d_win, _ = entry_bar_as_known_at(winter, "2026-01-15T20:30:00+00:00")
    assert d_win == "2026-01-14", "EST에서 20:30 UTC는 아직 장중"

    summer = {"2026-07-14": {"close": 10.0, "adj": 10.0},
              "2026-07-15": {"close": 11.0, "adj": 11.0}}
    d_sum, _ = entry_bar_as_known_at(summer, "2026-07-15T20:30:00+00:00")
    assert d_sum == "2026-07-15", "EDT에서 20:30 UTC는 마감 후"


def test_measure_uses_timestamp_aware_entry_when_available():
    entry = {"ticker": "ADBE", "analyzed_at": "2026-09-04T09:24:35+00:00",
             "analysis_date": "2026-09-04", "price_at_analysis": 285.75}
    row = measure(entry, dict(_SERIES,
                              **{"2026-09-17": {"close": 300.0, "adj": 300.0}}))
    assert row["entry_date_used"] == "2026-09-03"
    assert row["price_mismatch"] is False      # 시점 규칙이 맞으면 일치한다


# ── ① 정렬순서를 신뢰하지 않는다(실측 버그 회귀 테스트) ──────────────
def test_parse_series_ignores_row_order_descending():
    """
    API가 최신순(내림차순)으로 주는 실제 형태. raw[-1]을 최신으로 가정하면
    1년 전 값을 잡는다 - 그 가정이 되살아나면 이 테스트가 잡는다.
    """
    payload = {"data": [
        {"t": "2026-09-17", "c": 96.7, "a": 96.7},
        {"t": "2026-09-16", "c": 97.0, "a": 97.0},
        {"t": "2025-09-17", "c": 87.35, "a": 87.35},   # 배열 마지막 = 1년 전
    ]}
    series = parse_series(payload)
    assert max(series) == "2026-09-17"
    assert series["2026-09-17"]["close"] == 96.7


def test_parse_series_ignores_row_order_ascending():
    """오름차순으로 와도 동일하게 동작해야 한다(순서 가정 자체가 없어야)."""
    payload = {"data": [
        {"t": "2025-09-17", "c": 87.35, "a": 87.35},
        {"t": "2026-09-17", "c": 96.7, "a": 96.7},
    ]}
    series = parse_series(payload)
    assert max(series) == "2026-09-17"


def test_parse_series_handles_nested_data_shape():
    payload = {"data": {"data": [{"t": "2026-01-02", "c": 10.0, "a": 10.0}]}}
    assert parse_series(payload)["2026-01-02"]["close"] == 10.0


def test_parse_series_empty_is_empty_not_crash():
    assert parse_series({}) == {}
    assert parse_series({"data": []}) == {}


# ── ② 배당조정 시계열 안에서만 수익률을 계산한다 ─────────────────────
def test_return_uses_adjusted_series_not_raw_close():
    """
    배당이 있으면 조정종가와 원종가가 갈린다. 조정 기준 수익률이어야 하고,
    원종가로 계산한 값과 달라야 한다(같으면 조정을 안 쓴 것).
    """
    series = {
        "2026-09-04": {"close": 100.0, "adj": 98.0},   # 이후 배당만큼 조정됨
        "2026-09-17": {"close": 110.0, "adj": 110.0},
    }
    entry = {"ticker": "AAA", "analysis_date": "2026-09-04",
             "price_at_analysis": 100.0}
    row = measure(entry, series)
    # 조정 기준: 110/98 - 1 = +12.24%, 원종가 기준이면 +10.00%
    assert row["return_pct"] == pytest.approx(12.2449, abs=1e-3)
    assert row["return_pct"] != pytest.approx(10.0, abs=1e-6)


def test_ledger_price_mismatch_is_surfaced_not_silently_used():
    """ledger 기록가가 그날 실제 원종가와 다르면 숨기지 않고 드러낸다."""
    series = {"2026-09-04": {"close": 100.0, "adj": 100.0},
              "2026-09-17": {"close": 105.0, "adj": 105.0}}
    entry = {"ticker": "AAA", "analysis_date": "2026-09-04",
             "price_at_analysis": 120.0}       # 20% 어긋남
    row = measure(entry, series)
    assert row["price_mismatch"] is True
    assert row["ledger_price_delta_pct"] == pytest.approx(16.667, abs=1e-2)


def test_matching_ledger_price_is_not_flagged():
    series = {"2026-09-04": {"close": 98.10, "adj": 98.10},
              "2026-09-17": {"close": 96.70, "adj": 96.70}}
    entry = {"ticker": "ACGL", "analysis_date": "2026-09-04",
             "price_at_analysis": 98.10}
    row = measure(entry, series)
    assert row["price_mismatch"] is False
    assert row["return_pct"] == pytest.approx(-1.4271, abs=1e-3)
    assert row["days_held"] == 13


# ── 진입일 처리: 휴장일이면 직전 거래일 ──────────────────────────────
def test_entry_falls_back_to_previous_trading_day():
    series = {"2026-09-04": {"close": 50.0, "adj": 50.0},   # 금요일
              "2026-09-08": {"close": 55.0, "adj": 55.0}}
    # 2026-09-06은 주말 - 직전 거래일(09-04)을 써야 한다
    date, bar = price_on_or_before(series, "2026-09-06")
    assert date == "2026-09-04" and bar["close"] == 50.0


def test_entry_before_series_start_is_an_honest_error():
    series = {"2026-09-04": {"close": 50.0, "adj": 50.0}}
    entry = {"ticker": "AAA", "analysis_date": "2020-01-01",
             "price_at_analysis": 10.0}
    row = measure(entry, series)
    assert "error" in row and "이전 가격이 시계열에 없음" in row["error"]
    assert "return_pct" not in row


def test_no_trading_day_after_entry_is_an_honest_error():
    series = {"2026-09-17": {"close": 50.0, "adj": 50.0}}
    entry = {"ticker": "AAA", "analysis_date": "2026-09-17",
             "price_at_analysis": 50.0}
    row = measure(entry, series)
    assert "error" in row and "이후 거래일 없음" in row["error"]


# ── 코호트 수집: 통화 섞임 방지 ──────────────────────────────────────
def _write_ledger(d, ticker, date, price, currency="USD", grade="A",
                  judgment="저평가 가능성"):
    path = os.path.join(d, f"{ticker}_{date}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({
            "meta": {"ticker": ticker, "price_at_analysis": price,
                     "analyzed_at": f"{date}T00:00:00+00:00",
                     "currency": currency},
            "judgment": judgment, "judgment_grade": grade,
            "expectation_gap": 0.1,
        }, f)


def test_cohort_excludes_non_usd_with_reason(tmp_path):
    """통화가 섞이면 조용히 틀린다 - 빼되 사유를 남긴다."""
    _write_ledger(str(tmp_path), "USA", "2026-09-01", 10.0, currency="USD")
    _write_ledger(str(tmp_path), "CNY", "2026-09-01", 10.0, currency="CNY")
    cohort, skipped = collect_cohort(str(tmp_path))
    assert [c["ticker"] for c in cohort] == ["USA"]
    assert len(skipped) == 1 and "CNY" in skipped[0]["reason"]


def test_cohort_excludes_missing_price_with_reason(tmp_path):
    path = os.path.join(str(tmp_path), "NOPRICE_2026-09-01.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"meta": {"ticker": "NOPRICE",
                            "analyzed_at": "2026-09-01T00:00:00+00:00"},
                   "judgment": "적정가/경계선"}, f)
    cohort, skipped = collect_cohort(str(tmp_path))
    assert cohort == []
    assert "price_at_analysis" in skipped[0]["reason"]


def test_real_ledger_dir_collects_without_error():
    """실제 ledger/를 읽어도 예외 없이 동작해야 한다."""
    cohort, skipped = collect_cohort("ledger")
    assert isinstance(cohort, list)
    assert all("analysis_date" in c and "judgment_grade" in c for c in cohort)


# ── 네트워크 실패를 사유와 함께 돌려준다 ─────────────────────────────
def test_fetch_failure_returns_reason_not_exception():
    def boom(req, timeout=None):
        raise OSError("network down")
    series, err = fetch_daily_series("AAA", opener=boom)
    assert series is None and "network down" in err


def test_fetch_empty_series_returns_reason():
    class _Resp:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self): return json.dumps({"data": []}).encode()
    series, err = fetch_daily_series("AAA", opener=lambda req, timeout=None: _Resp())
    assert series is None and "가격 시계열 없음" in err


# ── 집계·리포트 ──────────────────────────────────────────────────────
def test_bucket_stats_basic():
    rows = [{"judgment_grade": "S", "return_pct": 10.0},
            {"judgment_grade": "S", "return_pct": -2.0},
            {"judgment_grade": "C", "return_pct": -5.0}]
    out = bucket_stats(rows, "judgment_grade")
    assert out["S"]["n"] == 2 and out["S"]["median_return_pct"] == 4.0
    assert out["S"]["pct_positive"] == 50.0
    assert out["C"]["n"] == 1


def test_report_counts_errors_and_skips_without_hiding_them():
    measured = [
        {"ticker": "OK1", "judgment_grade": "A", "judgment": "저평가 가능성",
         "return_pct": 5.0, "days_held": 10, "price_at_analysis": 1.0,
         "entry_close": 1.0, "ledger_price_delta_pct": 0.0,
         "price_mismatch": False},
        {"ticker": "BAD", "error": "분석일 이후 거래일 없음"},
    ]
    rep = build_report(measured, failures=[{"ticker": "NET", "error": "조회 실패"}],
                       skipped=[{"ticker": "CNY", "reason": "통화"}],
                       as_of="2026-09-18", price_source="test")
    assert rep["n_measured"] == 1
    assert rep["n_error"] == 2          # measure 실패 1 + fetch 실패 1
    assert rep["n_skipped_from_ledgers"] == 1
    assert rep["overall"]["median_return_pct"] == 5.0


def test_report_flags_price_mismatches_prominently():
    measured = [{"ticker": "X", "judgment_grade": "C", "judgment": "적정가/경계선",
                 "return_pct": 1.0, "days_held": 5, "price_at_analysis": 100.0,
                 "entry_date_used": "2026-09-04", "entry_close": 120.0,
                 "ledger_price_delta_pct": 16.7, "price_mismatch": True,
                 "ledger_price_traced_to": None}]
    rep = build_report(measured, [], [], "2026-09-18", "test")
    assert rep["n_price_mismatch"] == 1
    out = format_report(rep)
    assert "불일치" in out and "X" in out


def test_format_report_always_states_epistemic_status():
    """이 숫자가 무엇이 아닌지를 리포트가 항상 스스로 말해야 한다."""
    measured = [{"ticker": "X", "judgment_grade": "A", "judgment": "저평가 가능성",
                 "return_pct": 1.0, "days_held": 5, "price_at_analysis": 1.0,
                 "entry_close": 1.0, "ledger_price_delta_pct": 0.0,
                 "price_mismatch": False}]
    out = format_report(build_report(measured, [], [], "2026-09-18", "test"))
    assert "OBSERVATIONAL_NOT_INFERENTIAL" in out


def test_empty_measurement_is_reported_not_crashed():
    rep = build_report([], [], [], "2026-09-18", "test")
    assert rep["n_measured"] == 0
    assert "측정된 종목 없음" in format_report(rep)


# ── 이 모듈은 판정하지 않는다 ────────────────────────────────────────
def test_module_never_produces_a_verdict_or_weight():
    """
    측정 모듈이 '그래서 사라/팔아라'를 내놓기 시작하면 검증되지 않은 신호가
    곧바로 자본배분이 된다(engine/thesis.py §5와 같은 경계).
    """
    import engine.track_record as tr
    banned = ("decide", "verdict", "recommend", "should_buy", "weight",
              "size_position", "allocate")
    public = [n for n in dir(tr) if not n.startswith("_")]
    for name in public:
        assert not any(b in name.lower() for b in banned), (
            f"{name}: 이 모듈은 측정만 한다 - 판정·사이징은 범위 밖")


def test_grade_order_matches_engine_vocabulary():
    from engine.expectation_gap_engine import JUDGMENT_GRADE_LABELS
    assert set(GRADE_ORDER) == set(JUDGMENT_GRADE_LABELS)


def test_tolerance_is_a_named_constant_not_a_magic_number():
    assert 0 < LEDGER_PRICE_TOLERANCE < 0.05
    assert "OBSERVATIONAL" in MEASUREMENT_STATUS


def test_date_only_entry_falls_back_to_that_days_close():
    """
    시각 없이 날짜만 있으면 '그날 종가'로 읽는다 - 모르는 것을 개장 전이라고
    가정하면 그것도 추측이다(실제 ledger는 전부 타임스탬프를 갖고 있다).
    """
    date, bar = entry_bar_as_known_at(_SERIES, "2026-09-03")
    assert date == "2026-09-03" and bar["close"] == 285.75


def test_stale_ledger_price_is_traced_to_its_actual_trading_day():
    """
    실측 6건(DUOL·NBIX·SKYW·TCOM·UBER·WDAY)이 전부 "1~2거래일 묵은 시세를
    썼다"로 설명됐다 - 얼마나 어긋났나보다 **어느 날 종가였나**가 실제로
    고칠 수 있는 정보다.
    """
    from engine.track_record import trace_ledger_price
    series = {"2026-07-29": {"close": 140.17, "adj": 140.17},
              "2026-07-30": {"close": 133.60, "adj": 133.60},
              "2026-07-31": {"close": 134.81, "adj": 134.81},
              "2026-08-03": {"close": 136.00, "adj": 136.00}}
    traced = trace_ledger_price(series, 140.17, entry_date="2026-07-31")
    assert traced["date"] == "2026-07-29"
    assert traced["trading_days_before_entry"] == 2


def test_untraceable_price_returns_none_not_a_guess():
    """근방 어디에도 없으면 추측하지 않고 None - 원인 미상으로 남긴다."""
    from engine.track_record import trace_ledger_price
    series = {"2026-07-29": {"close": 100.0, "adj": 100.0},
              "2026-07-30": {"close": 101.0, "adj": 101.0}}
    assert trace_ledger_price(series, 44.77, entry_date="2026-07-30") is None


def test_measure_attaches_trace_only_when_mismatched():
    series = {"2026-09-03": {"close": 285.75, "adj": 285.75},
              "2026-09-04": {"close": 266.51, "adj": 266.51},
              "2026-09-17": {"close": 300.0, "adj": 300.0}}
    ok = measure({"ticker": "ADBE", "analyzed_at": "2026-09-04T09:24:35+00:00",
                  "analysis_date": "2026-09-04", "price_at_analysis": 285.75},
                 series)
    assert "ledger_price_traced_to" not in ok      # 일치하면 붙이지 않는다

    stale = measure({"ticker": "X", "analyzed_at": "2026-09-17T23:00:00+00:00",
                     "analysis_date": "2026-09-17", "price_at_analysis": 285.75},
                    dict(series, **{"2026-09-18": {"close": 310.0, "adj": 310.0}}))
    assert stale["price_mismatch"] is True
    assert stale["ledger_price_traced_to"]["date"] == "2026-09-03"
