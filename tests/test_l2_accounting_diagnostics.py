"""
축0 L2 두 번째·세 번째 진단값 고정 테스트 (RQ-005, 2026-08-26).

고정하는 것:
  ① AR 추세는 **상대**로 비교한다(절대 %p는 수준에 비례해 커져 비교 불가)
  ② 재작성 탐지는 **단위를 절대 합치지 않는다**(CNY/USD 동시보고 오탐)
  ③ 실체·단위 변경은 분자·분모 양쪽에서 뺀다
  ④ 여전히 합성점수가 없고 `run_analysis()`에 배선돼 있지 않다
  ⑤ ledger `meta.currency` 라벨 - 알려진 이탈 1건(TCOM) 외에 새로 생기면 실패
"""
import ast
import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.accounting_quality import (  # noqa: E402
    AR_LEVEL_THIN,
    AR_TREND_OBSERVED_RANGE,
    VALIDATION_STATUS,
    ar_to_revenue_trend,
)
from engine.data.providers.sec import (  # noqa: E402
    ENTITY_CHANGE_THRESHOLD,
    RESTATEMENT_MATERIAL,
    restatement_profile,
)


# ── ① AR 추세: 상대로 비교한다 ─────────────────────────────────────────
def test_relative_trend_is_comparable_across_different_levels():
    """
    핵심 성질 - 수준이 10배 다른 두 회사가 **같은 비율로** 악화되면 상대추세는
    같아야 하고, 절대 %p 기울기는 10배 차이 나야 한다. TTD(수준 1.3~1.9)가
    절대 기울기로는 코퍼스 최대 이상치인데 상대추세로는 평범해지는 이유다.
    """
    rev = {y: 1000.0 for y in range(2021, 2026)}
    small = {y: 100.0 * (1.10 ** (y - 2021)) for y in range(2021, 2026)}
    big = {y: 1000.0 * (1.10 ** (y - 2021)) for y in range(2021, 2026)}

    a = ar_to_revenue_trend(small, rev)
    b = ar_to_revenue_trend(big, rev)

    assert a["trend_relative"] == pytest.approx(b["trend_relative"], rel=1e-9)
    assert b["trend_slope_pp"] == pytest.approx(10 * a["trend_slope_pp"], rel=1e-9)
    assert b["mean_level"] == pytest.approx(10 * a["mean_level"], rel=1e-9)


def test_sign_convention_positive_means_receivables_outrun_revenue():
    rev = {y: 1000.0 for y in range(2021, 2026)}
    growing = {y: 100.0 + 10 * (y - 2021) for y in range(2021, 2026)}
    shrinking = {y: 100.0 - 10 * (y - 2021) for y in range(2021, 2026)}
    assert ar_to_revenue_trend(growing, rev)["trend_relative"] > 0
    assert ar_to_revenue_trend(shrinking, rev)["trend_relative"] < 0


def test_thin_receivables_are_flagged_because_relative_trend_amplifies():
    """
    분모(AR/매출 수준)가 작으면 사소한 절대변화가 큰 비율변화로 찍힌다.
    실측 사례: VRSN 수준 0.0042(매출의 0.4%), SE 0.0236에서 -18.12%/yr.
    """
    rev = {y: 1_000_000.0 for y in range(2021, 2026)}
    thin = {y: 2000.0 + 100 * (y - 2021) for y in range(2021, 2026)}
    p = ar_to_revenue_trend(thin, rev)
    assert p["mean_level"] < AR_LEVEL_THIN
    assert any("얇은 채권" in n for n in p["notes"])


def test_out_of_observed_range_is_flagged_as_unseen_not_as_threshold():
    rev = {y: 1000.0 for y in range(2021, 2026)}
    wild = {y: 100.0 * (2.0 ** (y - 2021)) for y in range(2021, 2026)}
    p = ar_to_revenue_trend(wild, rev)
    assert p["trend_relative"] > AR_TREND_OBSERVED_RANGE[1]
    note = " ".join(p["notes"])
    assert "관측범위 밖" in note and "임계값이 아니라" in note


def test_too_few_years_returns_uncomputable_rather_than_guessing():
    p = ar_to_revenue_trend({2024: 10.0, 2025: 12.0}, {2024: 100.0, 2025: 100.0})
    assert p["trend_relative"] is None
    assert any("계산 불가" in n for n in p["notes"])


def test_zero_revenue_years_are_skipped_not_crashed():
    p = ar_to_revenue_trend({y: 10.0 for y in range(2021, 2026)},
                            {2021: 0.0, 2022: 100.0, 2023: 100.0,
                             2024: 100.0, 2025: 100.0})
    assert 2021 not in p["ar_to_revenue_by_year"]
    assert p["trend_relative"] is not None


def test_ar_trend_produces_no_score_or_judgment():
    p = ar_to_revenue_trend({y: 10.0 for y in range(2021, 2026)},
                            {y: 100.0 for y in range(2021, 2026)})
    banned = {"score", "grade", "judgment", "rating", "composite", "f_score"}
    assert not (banned & set(p))


# ── ② 재작성: 단위를 합치지 않는다 ─────────────────────────────────────
def _facts(rows_by_unit, tag="Revenues", metric_ns="us-gaap"):
    """합성 companyfacts - 네트워크 없이 규약만 검증한다."""
    return {"facts": {metric_ns: {tag: {"units": rows_by_unit}}}}


def _row(start, end, filed, val):
    return {"form": "10-K", "start": start, "end": end, "filed": filed, "val": val}


def test_currencies_are_never_compared_against_each_other():
    """
    ⚠️ 이 테스트가 막는 사고: 中 발행사(PDD·TCOM)는 같은 태그를 CNY와 USD로
    **동시 보고**한다. 초판이 단위를 합쳐 비교해 재작성률 0.83~0.87이 나왔고,
    편차가 정확히 629.9%(=위안/달러 7.299)로 반복돼 발각됐다.
    """
    facts = _facts({
        "CNY": [_row("2024-01-01", "2024-12-31", "2025-02-01", 393_836_097_000),
                _row("2024-01-01", "2024-12-31", "2026-02-01", 393_836_097_000)],
        "USD": [_row("2024-01-01", "2024-12-31", "2025-02-01", 53_955_324_000),
                _row("2024-01-01", "2024-12-31", "2026-02-01", 53_955_324_000)],
    })
    p = restatement_profile(facts, metrics=("revenue",))
    assert p["restated_periods"] == 0, "통화가 다른 값을 재작성으로 오탐했다"
    assert p["multi_filed_periods"] == 2      # 단위별로 하나씩
    assert p["has_material_restatement"] is False


def test_material_restatement_within_one_unit_is_detected():
    facts = _facts({"USD": [
        _row("2024-01-01", "2024-12-31", "2025-02-01", 1_000_000.0),
        _row("2024-01-01", "2024-12-31", "2026-02-01", 1_200_000.0),   # +20%
    ]})
    p = restatement_profile(facts, metrics=("revenue",))
    assert p["restated_periods"] == 1
    assert p["has_material_restatement"] is True
    assert p["restatements"][0]["deviation"] == pytest.approx(0.20)
    assert p["restatements"][0]["unit"] == "USD"


def test_immaterial_change_is_not_counted_as_restatement():
    facts = _facts({"USD": [
        _row("2024-01-01", "2024-12-31", "2025-02-01", 1_000_000.0),
        _row("2024-01-01", "2024-12-31", "2026-02-01", 1_000_000.0 * (1 + RESTATEMENT_MATERIAL / 2)),
    ]})
    p = restatement_profile(facts, metrics=("revenue",))
    assert p["restated_periods"] == 0
    assert p["multi_filed_periods"] == 1, "분모에는 들어가야 한다"


# ── ③ 실체·단위 변경은 양쪽에서 뺀다 ───────────────────────────────────
def test_entity_change_is_excluded_from_both_numerator_and_denominator():
    """
    VRT는 2020년 SPAC 합병 전 껍데기 법인 재무제표를 같은 CIK로 제출했다 -
    FY2018 영업현금흐름이 -710,388 -> -221,900,000(311배). 이걸 재작성으로
    세면 그 회사의 회계 신뢰도를 완전히 잘못 읽는다. 분모에도 넣지 않는
    이유는, 넣으면 '재작성률이 낮다'는 반대 방향 왜곡이 생기기 때문이다.
    """
    facts = _facts({"USD": [
        _row("2018-01-01", "2018-12-31", "2019-02-01", 1_000.0),
        _row("2018-01-01", "2018-12-31", "2021-02-01",
             1_000.0 * (ENTITY_CHANGE_THRESHOLD + 10)),
    ]})
    p = restatement_profile(facts, metrics=("revenue",))
    assert p["restated_periods"] == 0
    assert p["multi_filed_periods"] == 0
    assert len(p["entity_or_unit_changes"]) == 1
    assert any("실체·단위 변경 제외" in n for n in p["notes"])


def test_single_filed_periods_report_unmeasurable_not_clean():
    """'재작성 없음'과 '잴 기회가 없었음'을 구분한다."""
    facts = _facts({"USD": [_row("2024-01-01", "2024-12-31", "2025-02-01", 100.0)]})
    p = restatement_profile(facts, metrics=("revenue",))
    assert p["multi_filed_periods"] == 0
    assert p["restatement_rate"] is None, "0이 아니라 None이어야 한다"
    assert any("측정 불가" in n for n in p["notes"])


def test_restatement_profile_produces_no_score():
    facts = _facts({"USD": [_row("2024-01-01", "2024-12-31", "2025-02-01", 100.0)]})
    p = restatement_profile(facts, metrics=("revenue",))
    banned = {"score", "grade", "judgment", "rating", "composite", "f_score"}
    assert not (banned & set(p))


# ── ④ 여전히 판정 경로에 배선되지 않았다 ───────────────────────────────
def test_l2_diagnostics_are_not_wired_into_run_analysis():
    pipeline = (ROOT / "engine" / "pipeline.py").read_text(encoding="utf-8")
    for name in ("accounting_quality", "ar_to_revenue_trend", "restatement_profile"):
        assert name not in pipeline, f"{name}이 pipeline에 배선됐다"


def test_new_diagnostics_declare_no_performance_evidence():
    for key in ("ar_to_revenue_trend", "restatement_history"):
        assert "검증된 바 없다" in VALIDATION_STATUS[key]


def test_sec_module_defines_no_scoring_function():
    src = (ROOT / "engine" / "data" / "providers" / "sec.py").read_text(encoding="utf-8")
    for n in [f.name for f in ast.walk(ast.parse(src))
              if isinstance(f, ast.FunctionDef)]:
        assert "score" not in n.lower(), f"점수 함수가 생겼다: {n}"


# ── ⑤ ledger 통화 라벨 - 알려진 이탈 외에 새로 생기면 실패 ─────────────
#
# 2026-08-26 전수 감사(reports/ledger_currency_audit_2026-08-26.json): 34종목 중
# TCOM 하나만 선언(USD)과 실제(CNY)가 다르다. 원인은 오타가 아니라 **필드 의미
# 중복**이다 - v3.24는 `currency`를 재무제표 통화로 도입했고(PDD가 그 관행을
# 따른다) TCOM 작성자는 `price_at_analysis`의 거래통화(ADS는 실제로 USD)로 썼다.
# v3.67 규모 조건부 상한은 이를 재무제표 통화로 읽는다.
#
# BSX 거짓탈락(KNOWN_SCREENER_FALSE_REJECTIONS) 선례와 같은 처리다 - 알려진
# 이탈을 명시적으로 등록하고, **새 이탈이 생기거나 이 이탈이 해소되면** 테스트가
# 알려준다.
KNOWN_CURRENCY_LABEL_DIVERGENCE = {"TCOM"}
_AUDIT = ROOT / "reports" / "ledger_currency_audit_2026-08-26.json"


def test_no_new_currency_label_divergence_appears():
    audit = json.loads(_AUDIT.read_text(encoding="utf-8"))
    found = {m["ticker"] for m in audit["mislabeled"]}
    new = found - KNOWN_CURRENCY_LABEL_DIVERGENCE
    assert not new, f"새 통화 라벨 이탈: {new} - 감사 리포트를 확인할 것"
    assert not audit["undetermined"], "판별불가 종목이 생겼다"


def test_known_divergence_is_still_reproducible():
    """
    TCOM이 고쳐지면 이 테스트가 실패해 위 예외 등록을 지우라고 알려준다
    (BSX 거짓탈락 회귀 테스트와 같은 목적).
    """
    import glob
    led = json.loads(pathlib.Path(
        sorted(glob.glob(str(ROOT / "ledger" / "TCOM_*.json")))[-1]
    ).read_text(encoding="utf-8"))
    assert led["meta"].get("currency") == "USD", (
        "TCOM의 통화 라벨이 바뀌었다 - KNOWN_CURRENCY_LABEL_DIVERGENCE에서 "
        "TCOM을 빼고 이 테스트를 갱신할 것")
    audit = json.loads(_AUDIT.read_text(encoding="utf-8"))
    row = next(r for r in audit["rows"] if r["ticker"] == "TCOM")
    assert row["detected"] == "CNY" and row["matched_years"] >= 9
