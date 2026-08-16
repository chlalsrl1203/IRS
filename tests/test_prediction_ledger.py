"""
Prediction Ledger 테스트.

가장 중요한 것은 `test_cannot_edit_prediction_after_seeing_outcome` 계열이다 -
이 모듈의 유일한 핵심 불변조건이며, 뚫리면 예측 기록 전체가 무의미해진다
(결과를 보고 범위를 넓히면 적중률이 100%가 된다).
"""

import json

import pytest

from engine.prediction_ledger import (
    Prediction,
    core_hash,
    forecast_error,
    load_predictions,
    prediction_summary,
    record_prediction,
    resolve_prediction,
)


def make_prediction(**overrides):
    base = dict(
        thesis_id="CDNS-2026-08-15",
        ticker="CDNS",
        prediction_date="2026-08-15",
        horizon="FY2026 Q3 실적(2026-11 발표 예정)",
        metric="매출 YoY 성장률",
        expected_low=0.09,
        expected_high=0.14,
        assumption="백로그 전환율이 최근 4개 분기 평균 수준을 유지한다",
        source="ledger/CDNS_2026-07-25.json의 realistic_growth 12.00%",
    )
    base.update(overrides)
    return Prediction(**base)


# ──────────────────────────────────────────────────────────────────
# 핵심 불변조건 - 결과를 알고 난 뒤 수정 불가
# ──────────────────────────────────────────────────────────────────

def test_cannot_edit_prediction_after_seeing_outcome(tmp_path):
    """
    ⚠️ 이 모듈의 존재 이유. 실제 공격을 재현한다 - 실적이 예측 범위를 벗어난
    걸 확인한 뒤, 파일을 열어 범위를 넓히고 HIT로 만들려는 시도.
    """
    path = record_prediction(make_prediction(), prediction_dir=str(tmp_path))

    # 결과가 3%로 나와 예측 범위(9~14%)를 크게 벗어났음을 알게 됐다.
    # 예측 범위를 사후에 넓혀 적중으로 만들려고 시도한다.
    rec = json.loads(open(path, encoding="utf-8").read())
    rec["core"]["expected_low"] = 0.01
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rec, f, ensure_ascii=False)

    with pytest.raises(ValueError, match="변조"):
        resolve_prediction(path, actual_value=0.03, actual_date="2026-11-20")


def test_tampering_with_any_core_field_is_detected(tmp_path):
    """범위뿐 아니라 지표·기한·가정을 바꿔도 잡혀야 한다."""
    for field, new_value in [
        ("metric", "영업이익 YoY 성장률"),
        ("horizon", "FY2027 Q1"),
        ("assumption", "다른 전제"),
        ("expected_high", 0.99),
    ]:
        d = tmp_path / field
        path = record_prediction(make_prediction(), prediction_dir=str(d))
        rec = json.loads(open(path, encoding="utf-8").read())
        rec["core"][field] = new_value
        with open(path, "w", encoding="utf-8") as f:
            json.dump(rec, f, ensure_ascii=False)

        with pytest.raises(ValueError, match="변조"):
            resolve_prediction(path, actual_value=0.10, actual_date="2026-11-20")


def test_cannot_resolve_twice(tmp_path):
    """결과를 두 번 쓰면 사후 조정과 구분할 수 없다."""
    path = record_prediction(make_prediction(), prediction_dir=str(tmp_path))
    resolve_prediction(path, actual_value=0.03, actual_date="2026-11-20")

    with pytest.raises(ValueError, match="이미 해소"):
        resolve_prediction(path, actual_value=0.11, actual_date="2026-11-21")


def test_recording_same_prediction_twice_is_rejected(tmp_path):
    path = record_prediction(make_prediction(), prediction_dir=str(tmp_path))
    with pytest.raises(FileExistsError):
        record_prediction(make_prediction(), prediction_dir=str(tmp_path))


def test_core_hash_survives_json_roundtrip(tmp_path):
    """
    봉인이 성립하려면 저장/로드를 왕복해도 해시가 같아야 한다. expected_range를
    튜플이 아닌 스칼라 2개로 나눈 이유가 정확히 이것이다(list/tuple이 흔들리면
    정상적인 해소까지 '변조'로 오판된다).
    """
    p = make_prediction()
    path = record_prediction(p, prediction_dir=str(tmp_path))
    rec = json.loads(open(path, encoding="utf-8").read())
    assert core_hash(rec["core"]) == p.core_hash()

    # 정상 해소가 막히지 않아야 한다
    out = resolve_prediction(path, actual_value=0.11, actual_date="2026-11-20")
    assert out["status"] == "HIT"


# ──────────────────────────────────────────────────────────────────
# 채점 규칙
# ──────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("actual,expected_status,expected_err", [
    (0.11, "HIT", 0.0),        # 범위 안
    (0.09, "HIT", 0.0),        # 하단 경계 포함
    (0.14, "HIT", 0.0),        # 상단 경계 포함
    (0.20, "MISS", 0.06),      # 위로 벗어남 -> 양수
    (0.03, "MISS", -0.06),     # 아래로 벗어남 -> 음수
])
def test_scoring_uses_preregistered_range(tmp_path, actual, expected_status, expected_err):
    path = record_prediction(make_prediction(),
                             prediction_dir=str(tmp_path / str(actual)))
    out = resolve_prediction(path, actual_value=actual, actual_date="2026-11-20")
    assert out["status"] == expected_status
    assert out["forecast_error"] == pytest.approx(expected_err, abs=1e-12)


def test_forecast_error_keeps_sign_for_bias_detection():
    """
    부호를 남기는 이유: "나는 체계적으로 낙관적인가"에 답하려면 절댓값만으로는
    알 수 없다. 위로 벗어나면 +, 아래로 벗어나면 -.
    """
    assert forecast_error(0.20, 0.09, 0.14) > 0
    assert forecast_error(0.03, 0.09, 0.14) < 0
    assert forecast_error(0.11, 0.09, 0.14) == 0.0


def test_unresolvable_is_honest_exit_not_a_guess(tmp_path):
    """
    데이터를 못 구했을 때 추측으로 채우지 않는다(계약서 155절 빈칸 채우기 금지).
    UNRESOLVABLE은 적중/실패 집계에서 빠진다.
    """
    path = record_prediction(make_prediction(), prediction_dir=str(tmp_path))
    out = resolve_prediction(path, actual_value=None, actual_date="2026-11-20",
                             note="회사가 해당 지표를 공시하지 않음", unresolvable=True)
    assert out["status"] == "UNRESOLVABLE"
    assert out["actual_value"] is None
    assert out["forecast_error"] is None

    s = prediction_summary(prediction_dir=str(tmp_path))
    assert s["n_unresolvable"] == 1 and s["n_resolved"] == 0
    assert s["hit_rate"] is None      # 표본 0이면 비율을 만들지 않는다


# ──────────────────────────────────────────────────────────────────
# 스키마 검증
# ──────────────────────────────────────────────────────────────────

def test_prediction_requires_every_core_field():
    for f in ("thesis_id", "horizon", "metric", "assumption"):
        with pytest.raises(ValueError, match=f):
            make_prediction(**{f: "  "})


def test_inverted_range_rejected():
    with pytest.raises(ValueError, match="뒤집혀"):
        make_prediction(expected_low=0.14, expected_high=0.09)


def test_prediction_id_is_content_derived():
    """같은 내용 = 같은 ID(중복을 파일명 단계에서 잡는다), 다르면 다른 ID."""
    assert make_prediction().prediction_id == make_prediction().prediction_id
    assert make_prediction().prediction_id != make_prediction(
        expected_high=0.15).prediction_id


# ──────────────────────────────────────────────────────────────────
# 집계
# ──────────────────────────────────────────────────────────────────

def test_summary_reports_sample_size_and_refuses_to_call_it_probability(tmp_path):
    for i, actual in enumerate([0.11, 0.20, 0.10]):
        p = make_prediction(metric=f"지표{i}")
        path = record_prediction(p, prediction_dir=str(tmp_path))
        resolve_prediction(path, actual_value=actual, actual_date="2026-11-20")

    s = prediction_summary(prediction_dir=str(tmp_path))
    assert s["n_resolved"] == 3 and s["n_hit"] == 2
    assert s["hit_rate"] == pytest.approx(2 / 3)
    assert "UNCALIBRATED" in s["calibration_status"]
    # 편향: 하나만 위로 벗어났으므로 평균 부호 오차는 양수
    assert s["mean_signed_error"] > 0


def test_load_predictions_filters_by_thesis_and_ticker(tmp_path):
    record_prediction(make_prediction(), prediction_dir=str(tmp_path))
    record_prediction(make_prediction(ticker="ROP", thesis_id="ROP-2026-08-15"),
                      prediction_dir=str(tmp_path))

    assert len(load_predictions(str(tmp_path))) == 2
    assert len(load_predictions(str(tmp_path), ticker="CDNS")) == 1
    assert len(load_predictions(str(tmp_path), thesis_id="ROP-2026-08-15")) == 1
