"""
engine/dilution.py 불변조건 (v3.84).

PHASE 4(2026-08-21)는 주식분할·IPO·ADS비율변경을 희석으로 오독해 틀린 값을
자본배분 경로에 배선까지 했다가 되돌렸다. `tests/test_dilution_drag.py`가 그
**당시 기록**을 고정한다면, 이 파일은 그 실패를 고친 **현재 구현**을 고정한다.

고정하는 것:
  ① 소급재표시 계수는 회사 공시에서 읽지, 추측하지 않는다
  ② 정규화는 스스로를 검증한 뒤에만 채택된다(단위 오타를 분할로 오인 금지)
  ③ CAGR 창을 파생할 때는 저장된 값을 재현해야만 쓴다
  ④ 측정 불가를 '희석 없음'으로 오독하지 않는다
  ⑤ 부호 항등식 — 주식수가 늘면 드래그는 반드시 음수다
  ⑥ 공식 판정 경로에 배선돼 있지 않다
"""
import ast
import json
import pathlib

import pytest

from engine.dilution import (
    FACTOR_CONSISTENCY_TOL,
    RESTATEMENT_TOL,
    SHARE_TAGS,
    STATUS_BASE_NONPOSITIVE,
    STATUS_END_NONPOSITIVE,
    STATUS_FY_COLLISION,
    STATUS_JUMP,
    STATUS_MISSING_YEAR,
    STATUS_NO_WINDOW,
    STATUS_OK,
    STRUCTURAL_JUMP_RATIO,
    VALIDATION_STATUS,
    annual_share_facts,
    consistent_share_series,
    detect_fy_label_collision,
    dilution_drag,
    normalize_to_latest_basis,
    resolve_cagr_window,
    structural_jumps,
)

ROOT = pathlib.Path(__file__).resolve().parent.parent
REPORT = ROOT / "reports" / "dilution_drag.json"


# ── 합성 데이터 헬퍼 ──────────────────────────────────────────────────────
def facts(tag, entries, taxonomy="us-gaap", unit="shares"):
    """entries: [(start, end, filed, val)]"""
    return {"facts": {taxonomy: {tag: {"units": {unit: [
        {"start": s, "end": e, "filed": f, "val": v, "form": "10-K"}
        for s, e, f, v in entries]}}}}}


def year_entries(pairs, filed):
    return [(f"{y}-01-01", f"{y}-12-31", filed, v) for y, v in pairs]


def ledger(fcf_by_year, base=None, span=None, fcf_cagr_5y=None, revenue=None):
    d = {"derived": {"fcf_by_year": {str(k): v for k, v in fcf_by_year.items()}}}
    if base is not None:
        d["derived"]["cagr_5y_base_year"] = base
    if span is not None:
        d["derived"]["cagr_5y_span"] = span
    if fcf_cagr_5y is not None:
        d["derived"]["fcf_cagr_5y"] = fcf_cagr_5y
    if revenue is not None:
        d["inputs"] = {"revenue_by_year": {str(k): v for k, v in revenue.items()}}
    return d


def merge_facts(*docs):
    out = {"facts": {"us-gaap": {}}}
    for d in docs:
        for tax, tags in d["facts"].items():
            out["facts"].setdefault(tax, {}).update(tags)
    return out


def fifty_three_week_entries(years, filed_offset_days=40):
    """결산일이 연초로 밀리는 52/53주 회계연도 — `end_year`가 두 해를 한 라벨로 묶는다.

    FY2020: 2020-01-02 ~ 2020-12-31   (라벨 2020)
    FY2021: 2021-01-01 ~ 2022-01-01   (라벨 2022 <- 밀림)
    FY2022: 2022-01-02 ~ 2022-12-31   (라벨 2022 <- 충돌)
    """
    out = []
    for fy, val in years.items():
        start = f"{fy}-01-01" if fy % 2 else f"{fy}-01-02"
        end = f"{fy + 1}-01-01" if fy % 2 else f"{fy}-12-31"
        out.append((start, end, f"{fy + 1}-02-10", val))
    return out


# ── ① 계수를 공시에서 읽는다 ─────────────────────────────────────────────
def test_split_factor_is_read_from_the_companys_own_restatement():
    """
    분할은 GAAP상 소급 재표시된다 — 같은 회계연도가 분할 전/후 두 기준으로
    공시되고 그 비율이 곧 계수다. TTD FY2019가 실제로 그랬다:
    47,806,000(분할 전) vs 478,061,000(분할 후 비교표) -> 정확히 x10.
    """
    f = facts(SHARE_TAGS[0],
              year_entries([(2019, 47_806_000), (2020, 48_988_000)], "2021-02-19")
              + year_entries([(2019, 478_061_000), (2020, 489_881_000),
                              (2021, 498_540_000)], "2024-02-15"))
    per_year = annual_share_facts(f, SHARE_TAGS[0])
    _series, meta = normalize_to_latest_basis(per_year, 2019, 2021)
    assert meta["factor"] == pytest.approx(10.0, rel=1e-4)
    assert meta["oldest_restated_year"] == 2019


def test_unrestated_older_years_are_lifted_onto_the_latest_basis():
    """분할 후 10-K는 비교표 2~3년치만 담는다 — 그보다 오래된 해는 직접 올려야 한다."""
    f = facts(SHARE_TAGS[0],
              year_entries([(2018, 100), (2019, 102), (2020, 104)], "2021-02-01")
              + year_entries([(2019, 204), (2020, 208), (2021, 212)], "2024-02-01"))
    per_year = annual_share_facts(f, SHARE_TAGS[0])
    series, meta = consistent_share_series(per_year, 2018, 2021)
    assert meta["adopted"] is True
    assert series[2018] == pytest.approx(200.0)   # 재표시본이 없어 x2로 올림
    assert series[2021] == pytest.approx(212.0)   # 이미 최신 기준
    assert structural_jumps(series, 2018, 2021) == []


def test_detection_is_confined_to_the_calculation_window():
    """
    구간 밖의 오래된 분할·단위오류까지 끌어들이면 계수가 서로 달라져 정규화가
    통째로 무산된다(RLI·MNST가 실제로 그랬다 — 2010년대 초 단위오류가 2022년
    2:1 분할 탐지를 가렸다).
    """
    f = facts(SHARE_TAGS[0],
              year_entries([(2011, 50), (2022, 100), (2023, 101)], "2012-02-01")
              + year_entries([(2011, 50_000), (2022, 200), (2023, 202),
                              (2024, 203)], "2025-02-01"))
    per_year = annual_share_facts(f, SHARE_TAGS[0])
    # 창을 2022~2024로 두면 2011년 단위오류(x1000)는 탐지 대상이 아니다
    _s, meta = normalize_to_latest_basis(per_year, 2022, 2024)
    assert meta["factor"] == pytest.approx(2.0, rel=1e-6)
    # 창을 2011까지 넓히면 계수가 흩어져 정규화를 포기한다
    _s2, meta2 = normalize_to_latest_basis(per_year, 2011, 2024)
    assert meta2["factor"] is None


# ── ② 정규화는 스스로를 검증한 뒤에만 채택된다 ───────────────────────────
def test_single_year_unit_typo_is_not_mistaken_for_a_split():
    """
    ⚠️ 실제로 잡은 결함 — BRO FY2021은 277,414로 잘못 공시됐다가 277,400,000으로
    정정됐다. 한 해만 재표시되면 계수 일관성 검사가 자동으로 통과해버려(표본 1개)
    x1000이 '분할'로 채택되고, 그 결과 이전 연도가 1000배로 부풀어 **측정 가능하던
    종목이 측정 불가가 된다**. 조정 후 점프가 줄지 않으면 기각해야 한다.
    """
    f = facts(SHARE_TAGS[0],
              year_entries([(2020, 275_800_000), (2021, 277_414),
                            (2022, 279_000_000)], "2022-02-01")
              + year_entries([(2021, 277_400_000)], "2025-02-01"))
    per_year = annual_share_facts(f, SHARE_TAGS[0])
    _s, raw_meta = normalize_to_latest_basis(per_year, 2020, 2022)
    assert raw_meta["factor"] is not None       # 계수 자체는 탐지된다

    series, meta = consistent_share_series(per_year, 2020, 2022)
    assert meta["adopted"] is False             # 그러나 채택되지 않는다
    assert "점프가 줄지 않아" in meta["note"]
    assert series[2020] == pytest.approx(275_800_000)
    assert structural_jumps(series, 2020, 2022) == []


def test_normalization_is_adopted_only_when_it_reduces_jumps():
    f = facts(SHARE_TAGS[0],
              year_entries([(2020, 100), (2021, 101), (2022, 102)], "2023-02-01")
              + year_entries([(2022, 510), (2023, 515)], "2026-02-01"))
    per_year = annual_share_facts(f, SHARE_TAGS[0])
    before = structural_jumps({y: r[-1][2] for y, r in per_year.items()}, 2020, 2023)
    series, meta = consistent_share_series(per_year, 2020, 2023)
    assert before and meta["adopted"] is True
    assert structural_jumps(series, 2020, 2023) == []
    assert meta["jumps_before_after"][1] < meta["jumps_before_after"][0]


def test_threshold_is_a_domain_constraint_not_a_tuned_value():
    """1.5배는 PHASE 4가 정한 도메인 제약이다 — 결과를 보고 조정하면 오염이 샌다."""
    assert STRUCTURAL_JUMP_RATIO == 1.5
    assert RESTATEMENT_TOL == 0.02
    assert FACTOR_CONSISTENCY_TOL == 0.05


# ── ③ 창 파생은 저장값을 재현해야만 채택된다 ─────────────────────────────
def test_derived_window_must_reproduce_the_stored_cagr():
    fcf = {y: 100 * 1.1 ** (y - 2015) for y in range(2015, 2026)}
    stored = (fcf[2025] / fcf[2020]) ** (1 / 5) - 1
    base, span, how, _ = resolve_cagr_window(ledger(fcf, fcf_cagr_5y=stored))
    assert (base, span, how) == (2020, 5, "derived_and_verified")


def test_derived_window_is_refused_when_it_does_not_reproduce():
    """
    재현하지 못하면 창을 특정할 수 없다는 뜻이다 — 추측해서 쓰지 않고 거부한다
    (v3.19 이후 이 프로젝트가 일관되게 지킨 '빈칸을 추측으로 채우지 않는다').
    """
    fcf = {y: 100 * 1.1 ** (y - 2015) for y in range(2015, 2026)}
    base, span, how, _ = resolve_cagr_window(ledger(fcf, fcf_cagr_5y=0.99))
    assert base is None and span is None
    assert "재현하지 못한다" in how


def test_stored_window_wins_over_derivation():
    fcf = {y: 100.0 for y in range(2015, 2026)}
    base, span, how, _ = resolve_cagr_window(ledger(fcf, base=2019, span=6))
    assert (base, span, how) == (2019, 6, "ledger")


# ── ④ 측정 불가를 '희석 없음'으로 오독하지 않는다 ────────────────────────
@pytest.mark.parametrize("build, expected", [
    (lambda: (ledger({2024: 1.0}), facts(SHARE_TAGS[0], [])), STATUS_NO_WINDOW),
    (lambda: (ledger({y: 100.0 for y in range(2015, 2026)}, base=2020, span=5),
              facts(SHARE_TAGS[0], year_entries([(2020, 10)], "2021-01-01"))),
     STATUS_MISSING_YEAR),
    (lambda: (ledger({**{y: 100.0 for y in range(2015, 2026)}, 2020: -5.0},
                     base=2020, span=5),
              facts(SHARE_TAGS[0],
                    year_entries([(2020, 10), (2025, 11)], "2026-01-01"))),
     STATUS_BASE_NONPOSITIVE),
    (lambda: (ledger({**{y: 100.0 for y in range(2015, 2026)}, 2025: -5.0},
                     base=2020, span=5),
              facts(SHARE_TAGS[0],
                    year_entries([(2020, 10), (2025, 11)], "2026-01-01"))),
     STATUS_END_NONPOSITIVE),
])
def test_every_failure_mode_returns_a_reason_never_a_number(build, expected):
    led, f = build()
    r = dilution_drag("X", led, f)
    assert r["status"] == expected
    assert r.get("detail")
    assert "dilution_drag" not in r


def test_negative_end_fcf_never_produces_a_complex_number():
    """
    ⚠️ 파이썬은 음수의 실수제곱을 복소수로 **조용히** 돌려준다(v3.19가 잡은 함정).
    기준연도만 막고 종료연도를 안 막으면 복소수가 결과에 섞인다.
    """
    led = ledger({**{y: 100.0 for y in range(2015, 2026)}, 2025: -50.0},
                 base=2020, span=5)
    f = facts(SHARE_TAGS[0], year_entries([(2020, 10), (2025, 11)], "2026-01-01"))
    r = dilution_drag("X", led, f)
    assert r["status"] == STATUS_END_NONPOSITIVE
    assert not any(isinstance(v, complex) for v in r.values())


def test_fy_label_collision_is_reported_not_silently_resolved():
    """
    52/53주 결산이 같은 라벨로 묶이면 어느 해 값인지 특정할 수 없다(v3.61 CDNS·GEN).
    ⚠️ 자동 재라벨링은 하지 않는다 — 규약이 회사마다 반대다.
    """
    f = facts(SHARE_TAGS[0], [
        ("2021-01-04", "2022-01-02", "2022-02-01", 100),
        ("2022-01-03", "2022-12-31", "2023-02-01", 101),
    ])
    per_year = annual_share_facts(f, SHARE_TAGS[0])
    assert detect_fy_label_collision(per_year) == [2022]

    led = ledger({y: 100.0 for y in range(2015, 2026)}, base=2020, span=5)
    r = dilution_drag("X", led, f)
    assert r["status"] == STATUS_FY_COLLISION
    assert "dilution_drag" not in r


def test_relabeling_is_adopted_only_when_it_reproduces_the_ledger():
    """
    ⚠️ v3.61이 금지한 것은 **일반적인 자동 재라벨링**이다(규약이 회사마다 반대라
    어느 쪽이 옳은지 코드가 알 수 없다). 여기서 하는 것은 다른 질문이다 —
    "이 라벨링이 **이 ledger의 연도 키**를 재현하는가"이고, 그 답은 같은
    companyfacts의 매출로 증명된다. 증명되지 않으면 종전대로 측정을 거부한다.
    """
    rev = {y: 1_000_000.0 * (y - 2014) for y in range(2015, 2026)}
    fcf = {y: 100.0 for y in range(2015, 2026)}

    f_ok = merge_facts(
        facts(SHARE_TAGS[0], fifty_three_week_entries(
            {y: 100 + y - 2015 for y in range(2015, 2026)})),
        facts("Revenues", fifty_three_week_entries(rev)))
    r = dilution_drag("X", ledger(fcf, base=2020, span=5, revenue=rev), f_ok)
    assert r["status"] == STATUS_OK
    assert r["year_labeling"] == "midpoint"
    assert r["year_labeling_check"]["midpoint"][1] == 0      # 불일치 0
    assert r["shares_base"] == 105 and r["shares_end"] == 110

    # 같은 주식수인데 ledger 매출이 재라벨링과 맞지 않으면 -> 채택하지 않는다.
    f_bad = merge_facts(
        facts(SHARE_TAGS[0], fifty_three_week_entries(
            {y: 100 + y - 2015 for y in range(2015, 2026)})),
        facts("Revenues", fifty_three_week_entries(
            {y: v * 3 for y, v in rev.items()})))
    r2 = dilution_drag("X", ledger(fcf, base=2020, span=5, revenue=rev), f_bad)
    assert r2["status"] == STATUS_FY_COLLISION
    assert r2["labeling_check"]["midpoint"][1] > 0   # 불일치가 실제로 잡혔다


def test_splice_is_a_last_resort_that_leaves_clean_series_untouched():
    """
    스플라이스는 값을 비율로 재계산하므로 이미 매끄러운 종목을 건드리면 기존
    측정값이 흔들린다(실측 4~5번째 자리). 점프가 남은 경우에만 탄다.
    """
    clean = annual_share_facts(
        facts(SHARE_TAGS[0],
              year_entries([(y, 100 + y - 2020) for y in range(2020, 2026)],
                           "2026-02-01")), SHARE_TAGS[0])
    series, meta = consistent_share_series(clean, 2020, 2025)
    assert meta["basis"] == "latest_filed"
    assert series[2020] == 100 and series[2025] == 105

    # 공시본 하나가 통째로 1/1000 스케일 -> 스플라이스가 기준을 되돌린다(PDD 형태).
    f = facts(SHARE_TAGS[0],
              year_entries([(2020, 1_000), (2021, 1_010), (2022, 1_020)], "2023-02-01")
              + year_entries([(2022, 1.020), (2023, 1.030)], "2024-02-01")
              + year_entries([(2023, 1_030), (2024, 1_040), (2025, 1_050)], "2026-02-01"))
    per_year = annual_share_facts(f, SHARE_TAGS[0])
    series2, meta2 = consistent_share_series(per_year, 2020, 2025)
    assert meta2["basis"] == "spliced_filings"
    assert meta2["filing_ratios"]["2024-02-01"] == pytest.approx(1000.0)
    assert structural_jumps(series2, 2020, 2025) == []
    assert series2[2020] == 1_000  # 공시된 값 그대로 — 재계산 근사치가 아니다


def test_same_year_amendments_are_not_a_collision():
    """같은 기간의 정정공시는 충돌이 아니다 — 충돌로 세면 멀쩡한 종목이 탈락한다."""
    f = facts(SHARE_TAGS[0], [
        ("2022-01-01", "2022-12-31", "2023-02-01", 100),
        ("2022-01-01", "2022-12-31", "2023-05-01", 101),
    ])
    assert detect_fy_label_collision(annual_share_facts(f, SHARE_TAGS[0])) == []


# ── ⑤ 부호 항등식 ────────────────────────────────────────────────────────
def test_drag_sign_follows_share_count_direction_exactly():
    """
    drag = (F_e/F_b)^(1/n) * [(S_b/S_e)^(1/n) − 1] 이므로 F가 양수인 한
    부호는 오직 주식수 방향이 결정한다. 이 항등식이 깨지면 계산이 틀린 것이다.
    """
    fcf = {y: 100.0 * 1.2 ** (y - 2020) for y in range(2020, 2026)}
    for s_end, expect_negative in [(130, True), (100, None), (80, False)]:
        f = facts(SHARE_TAGS[0],
                  year_entries([(2020, 100), (2025, s_end)], "2026-01-01"))
        r = dilution_drag("X", ledger(fcf, base=2020, span=5), f)
        assert r["status"] == STATUS_OK
        if expect_negative is None:
            assert r["dilution_drag"] == pytest.approx(0.0, abs=1e-12)
        elif expect_negative:
            assert r["dilution_drag"] < 0 and r["share_count_change_pct"] > 0
        else:
            assert r["dilution_drag"] > 0 and r["share_count_change_pct"] < 0


def test_real_report_satisfies_the_sign_identity():
    doc = json.loads(REPORT.read_text(encoding="utf-8"))
    ok = [r for r in doc["results"] if r["status"] == STATUS_OK]
    assert len(ok) >= 55, "측정 종목이 급감했다면 정규화가 퇴행한 것"
    for r in ok:
        if r["share_count_change_pct"] > 1e-12:
            assert r["dilution_drag"] < 0, r["ticker"]
        elif r["share_count_change_pct"] < -1e-12:
            assert r["dilution_drag"] > 0, r["ticker"]


# ── PHASE 4 회귀 방지 — 오염 종목은 여전히 측정 불가여야 한다 ────────────
def test_ipo_era_tickers_remain_unmeasurable():
    """
    DUOL·MNDY·PATH는 IPO가 RG 창 **안에** 들어 있어 상장 전/후 가중평균 주식수의
    기준이 다르다(상장 전은 전환 전 우선주를 제외한다). 이들이 'OK'로 바뀌면
    PHASE 4의 오염이 되살아난 것이다.

    ⚠️ PDD는 여기서 빠졌다 — v3.84가 'ADS/보통주 단위 혼재'로 적은 진단이
    2026-09-12 원자료 확인에서 **틀린 것으로 드러났다**. 실제 원인은 20-F 한
    건(2025-04-28)이 FY2022~24를 통째로 1/1000 스케일로 보고하고 다음 공시가
    되돌린 것이라, 공시본 스플라이스로 정당하게 회복된다.
    """
    rows = {r["ticker"]: r
            for r in json.loads(REPORT.read_text(encoding="utf-8"))["results"]}
    for t in ("DUOL", "MNDY", "PATH"):
        assert rows[t]["status"] != STATUS_OK, t
        assert rows[t].get("detail")


def test_recovered_tickers_carry_their_evidence():
    """
    회복된 종목은 '왜 회복됐는지'가 남아야 한다 — 근거가 없으면 나중에 검증할
    수 없다. 경로마다 남겨야 할 근거가 다르다:
      - 소급재표시 정규화 -> 계수와 재표시 연도
      - 공시본 스플라이스 -> 어느 공시본이 어떤 비율로 어긋났는지
    """
    rows = {r["ticker"]: r
            for r in json.loads(REPORT.read_text(encoding="utf-8"))["results"]}
    adopted = [r for r in rows.values()
               if r["status"] == STATUS_OK
               and (r.get("normalization") or {}).get("adopted")]
    assert adopted, "정규화로 회복된 종목이 하나도 없다면 경로가 죽은 것"
    for r in adopted:
        norm = r["normalization"]
        if norm.get("basis") == "spliced_filings":
            assert norm["filing_ratios"], r["ticker"]
        else:
            assert norm["factor"] > 1.0, r["ticker"]
            assert norm["restated_years"], r["ticker"]


def test_pdd_recovered_because_one_filing_was_off_by_a_thousand():
    """
    PDD 2025-04-28 20-F는 FY2022~24를 1/1000 스케일로 보고했고 **다음 공시가
    되돌렸다**. 되돌려진다는 것이 분할(영구 소급재표시)과 구분되는 지점이다.
    """
    r = {x["ticker"]: x
         for x in json.loads(REPORT.read_text(encoding="utf-8"))["results"]}["PDD"]
    assert r["status"] == STATUS_OK
    assert r["normalization"]["basis"] == "spliced_filings"
    assert r["normalization"]["filing_ratios"]["2025-04-28"] == pytest.approx(1000.0)
    # 회복된 값은 회사가 실제로 공시한 숫자여야 한다 — 비율로 재계산한 근사치가
    # 기록에 남으면 어느 공시본에도 없는 숫자를 인용하게 된다.
    assert r["shares_base"] == 4_768_343_300


def test_residual_gap_is_declared_unrecoverable_not_merely_missing():
    """
    남은 공백을 '아직 안 가져왔다'로 두면 닫을 수 없는 것을 계속 닫으려 하게 된다.
    2026-09-12 원자료 진단 결과 셋 다 이 출처로는 원리적으로 못 채운다.
    """
    doc = json.loads(REPORT.read_text(encoding="utf-8"))
    residual = doc["residual_gap"]
    assert residual, "측정 불가 종목이 있는 한 사유가 비어 있으면 안 된다"
    for status, info in residual.items():
        assert info["tickers"]
        assert info["recoverable_from_companyfacts"] is False, status
        assert info["cause"]


def test_tcom_per_share_decline_was_an_ads_ratio_artifact():
    """
    PHASE 4는 TCOM을 '총 FCF는 성장했는데 주당 FCF는 감소(−21.18%)'로 보고했다.
    그 −34.22%p는 2021년 ADS 비율변경(x8)을 희석으로 오독한 결과였다.
    정규화 후에는 주당 FCF가 **양수**여야 한다.
    """
    rows = {r["ticker"]: r
            for r in json.loads(REPORT.read_text(encoding="utf-8"))["results"]}
    tcom = rows["TCOM"]
    assert tcom["status"] == STATUS_OK
    assert tcom["fcf_cagr_per_share"] > 0
    assert tcom["dilution_drag"] > -0.05


# ── ⑥ 공식 판정 경로에 배선돼 있지 않다 ──────────────────────────────────
def test_valuation_engine_does_not_import_dilution():
    """
    §13 게이트 6번(validation strategy)이 없다 — 성과와의 관계 증거가 0건이다.
    Gap·RG·판정을 만드는 두 파일은 이 지표를 **이름으로도** 참조하지 않는다.

    ⚠️ v3.86 이전에는 `portfolio_pipeline.py`도 이 목록에 있었다. 거기서 뺀
    이유는 규칙이 느슨해져서가 아니라, 그 파일에서 지켜야 할 불변조건이
    "문자열이 없다"가 아니라 **"비중과 배제가 바뀌지 않는다"**이기 때문이다 —
    `test_portfolio_dilution_wiring.py`가 그 강한 쪽을 실행으로 검증한다.
    """
    for name in ("pipeline.py", "expectation_gap_engine.py"):
        src = (ROOT / "engine" / name).read_text(encoding="utf-8")
        assert "dilution" not in src, f"engine/{name}이 희석 드래그를 참조한다"


def test_material_threshold_has_a_single_source():
    """리포트와 포트폴리오 경계검토가 같은 선을 쓴다(v3.35 ① 재발 방지)."""
    from engine.dilution import DRAG_MATERIAL_PCT

    src = (ROOT / "scripts" / "dilution_drag.py").read_text(encoding="utf-8")
    assert "DRAG_MATERIAL_PCT" in src
    assert "-0.05" not in src, "임계값 리터럴이 스크립트에 복사돼 있다"
    assert DRAG_MATERIAL_PCT == -0.05


def test_module_exposes_no_verdict_or_weight_function():
    """
    Gap을 액션으로 바꾸는 함수가 생기는 순간 미검증 신호가 곧바로 자본배분이
    된다(engine/thesis.py·portfolio.py가 같은 경계를 강제한다).
    """
    tree = ast.parse((ROOT / "engine" / "dilution.py").read_text(encoding="utf-8"))
    banned = ("verdict", "judge", "decide", "weight", "grade", "score", "penal")
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            assert not any(b in node.name.lower() for b in banned), node.name


def test_validation_status_declares_it_is_unvalidated():
    assert VALIDATION_STATUS["dilution_drag"] == "IMPLEMENTED_NOT_VALIDATED"
    doc = json.loads(REPORT.read_text(encoding="utf-8"))
    assert doc["affects_official_judgment"] is False
    assert "not_wired_into_growth" in doc


def test_report_states_buy_universe_coverage_honestly():
    """
    커버리지를 숨기면 부분 표본의 신호가 전체를 대표하는 것처럼 오독된다
    (PHASE 4가 41.33% 미측정 상태로 배선했다가 되돌린 이유).
    """
    doc = json.loads(REPORT.read_text(encoding="utf-8"))
    cov = doc["coverage"]
    assert cov["held_measured"] <= cov["held_total"]
    assert cov["held_unmeasured_weight"] >= 0.0
    assert doc["buylist_source"], "어느 매수리스트 기준인지 없으면 재현 불가"


def test_coverage_bias_direction_is_declared():
    """
    ⚠️ 미측정 집단은 무작위가 아니다 — IPO 직후·고SBC 종목이 구조적으로 몰린다
    (주식수 급증 자체가 측정을 막기 때문이다). 2026-09-11 실측: 매수 유니버스
    최고 SBC 2종목 DUOL(37%)·MNDY(57%)가 둘 다 측정 불가인데, 측정된 종목의
    주식수 변화 중앙값은 +1.3%뿐이다. 이 편향을 적지 않으면 부분집합의 '희석
    온건함'이 전체를 대표하는 것처럼 읽힌다.
    """
    doc = json.loads(REPORT.read_text(encoding="utf-8"))
    bias = doc["coverage_bias"]
    assert bias["direction"] in ("optimistic", "unknown")
    assert bias["note"]
    if bias["unmeasured_high_sbc"]:
        assert bias["direction"] == "optimistic"


def test_buylist_source_is_the_latest_not_a_frozen_date():
    """
    ⚠️ PHASE 4 스크립트는 `buylist_2026-08-03.json`에 고정돼 있어 그 뒤 늘어난
    종목을 구조적으로 보지 못했다(12종목만 집계). 같은 실수를 막는다.
    """
    import re
    doc = json.loads(REPORT.read_text(encoding="utf-8"))
    pat = re.compile(r"^buylist_(\d{4}-\d{2}-\d{2})\.json$")
    latest = sorted(f for f in (ROOT / "reports").iterdir()
                    if pat.match(f.name))[-1].name
    assert doc["buylist_source"] == latest
