"""
Growth Quality 모듈 테스트 (2026-08-16).

§10이 요구하는 Unit / Domain / Determinism을 덮고, 이 모듈의 **핵심 안전조건**을
고정한다: 이 모듈은 어떤 공식 판정도 바꾸지 않으며, proxy를 ROIIC라고 부르지 않는다.
"""
import json
import pathlib

import pytest

from engine.growth_quality import (
    MIN_YEARS,
    VALIDATION_STATUS,
    capex_to_revenue_series,
    economic_profile,
    operating_margin_series,
)

ROOT = pathlib.Path(__file__).resolve().parent.parent

REV = {"2021": 100.0, "2022": 120.0, "2023": 150.0}
OI = {"2021": 10.0, "2022": 18.0, "2023": 30.0}
CAP = {"2021": 5.0, "2022": 6.0, "2023": 9.0}


# ── Unit ────────────────────────────────────────────────────────────────
def test_margin_series_basic():
    r = operating_margin_series(OI, REV)
    assert r["by_year"] == {"2021": 0.10, "2022": 0.15, "2023": 0.20}
    assert r["skipped_years_nonpositive_revenue"] == []


def test_capex_ratio_basic():
    r = capex_to_revenue_series(CAP, REV)
    assert r["by_year"]["2023"] == pytest.approx(0.06)


def test_profile_reports_levels_not_a_composite_score():
    p = economic_profile(REV, OI, CAP)
    assert p["operating_margin_level"] == pytest.approx(0.20)
    assert p["capex_to_revenue_level"] == pytest.approx(0.06)
    # 종합점수를 만들지 않는다 - 이름에 score/composite가 들어간 키가 없어야 한다
    assert not [k for k in p if "score" in k.lower() or "composite" in k.lower()]


# ── Domain (경제적으로 말이 안 되는 입력 차단) ─────────────────────────────
def test_negative_capex_is_rejected_not_silently_flipped():
    """capex 부호 규약이 어긋나면 자본집약도가 정반대가 된다 - 조용히 통과 금지."""
    with pytest.raises(ValueError, match="양수 지출"):
        capex_to_revenue_series({"2023": -9.0}, {"2023": 150.0})


def test_nonpositive_revenue_year_is_excluded_and_recorded():
    """매출≤0인 해는 마진이 정의되지 않는다 - 제외하되 사실을 남긴다."""
    r = operating_margin_series({"2022": 5.0, "2023": 30.0}, {"2022": 0.0, "2023": 150.0})
    assert "2022" not in r["by_year"]
    assert r["skipped_years_nonpositive_revenue"] == ["2022"]


def test_unprofitable_company_is_flagged_not_hidden():
    p = economic_profile({"2023": 100.0, "2022": 90.0, "2021": 80.0},
                         {"2023": -5.0, "2022": -8.0, "2021": -9.0},
                         {"2023": 3.0, "2022": 3.0, "2021": 3.0})
    assert p["operating_margin_level"] < 0
    assert any("UNPROFITABLE" in s for s in p["data_limitations"])


def test_insufficient_years_is_recorded_as_data_missing():
    p = economic_profile({"2023": 100.0}, {"2023": 20.0}, {"2023": 5.0})
    assert p["n_years_margin"] < MIN_YEARS
    assert any("DATA MISSING" in s for s in p["data_limitations"])


def test_malformed_year_keys_raise():
    with pytest.raises(ValueError, match="정수로 해석"):
        operating_margin_series({"FY23": 1.0}, {"FY23": 10.0})


# ── Determinism ─────────────────────────────────────────────────────────
def test_deterministic_same_input_same_output():
    assert economic_profile(REV, OI, CAP) == economic_profile(REV, OI, CAP)


# ── 인식론적 지위 / 안전조건 ────────────────────────────────────────────
def test_proxy_is_never_called_roiic():
    """§3-3: proxy를 ROIIC라고 부르지 않는다."""
    p = economic_profile(REV, OI, CAP)
    for k in p:
        assert "roiic" not in k.lower(), k
        assert "roic" not in k.lower(), k
    assert VALIDATION_STATUS["roic_roiic"].startswith("BLOCKED")
    assert "PROXY_ONLY" in VALIDATION_STATUS["capex_to_revenue_level"]


def test_module_declares_it_does_not_affect_judgment():
    assert economic_profile(REV, OI, CAP)["affects_official_judgment"] is False


def test_growth_quality_is_not_wired_into_run_analysis():
    """
    STAGE 1은 prototype이다. 이 모듈이 pipeline에 배선되면 34종목 ledger가 바뀌므로,
    배선하려면 골든재현 영향을 별도로 판단해야 한다 - 그 전까지는 미배선이어야 한다.
    """
    src = (ROOT / "engine" / "pipeline.py").read_text(encoding="utf-8")
    assert "growth_quality" not in src, (
        "growth_quality가 pipeline에 배선됐다면 34종목 ledger 영향과 "
        "H-007 사전등록 상태를 먼저 검토할 것"
    )


# ── 실데이터 회귀 ────────────────────────────────────────────────────────
def test_runs_on_every_stored_ledger_without_error():
    """34종목 실입력 전부에서 예외 없이 동작하는지 - 도메인 가드가 과하지 않은지 확인."""
    n = 0
    for p in sorted((ROOT / "ledger").glob("*.json")):
        led = json.loads(p.read_text(encoding="utf-8"))
        I = led["inputs"]
        prof = economic_profile(I["revenue_by_year"], I["operating_income_by_year"],
                                I["capex_by_year"])
        assert prof["n_years_margin"] >= 1, led["meta"]["ticker"]
        n += 1
    assert n >= 30, f"ledger를 {n}건만 읽었다"
