"""
2026-08-16 예측 봉인(`scripts/freeze_predictions_2026_08_16.py`)의 결과물
무결성 테스트.

핵심: (1) 예측 범위가 ledger에 이미 저장된 값 그대로인지(새 밴드 발명 없음),
(2) thesis_id가 정직한지(있지도 않은 thesis를 지어내지 않았는지),
(3) 전부 OPEN 상태로 시작하는지(결과를 미리 채우지 않았는지).
"""

import glob
import json

import pytest

PREDICTIONS = [json.load(open(p, encoding="utf-8"))
               for p in sorted(glob.glob("predictions/*.json"))]


def test_predictions_exist_for_real():
    """
    ⚠️ 2026-08-16 Historical Replay 감사 이전에는 이 디렉터리 자체가 없었다
    (실사용 0건). 이 테스트는 그 상태가 되돌아가지 않았는지 고정한다.
    """
    assert len(PREDICTIONS) >= 30, (
        f"predictions/ 파일이 {len(PREDICTIONS)}건뿐이다 - 34종목 동결이 "
        f"되돌려졌거나 손상됐다"
    )


def test_every_prediction_starts_open_with_no_prefilled_outcome():
    for p in PREDICTIONS:
        assert p["status"] == "OPEN"
        assert p["actual_value"] is None
        assert p["forecast_error"] is None


def test_thesis_id_is_honest_placeholder_not_fabricated():
    """
    34종목 중 실제 Investment Thesis가 기록된 종목은 0건이다(thesis/ 디렉터리
    자체가 없다). 있지도 않은 thesis를 지어내 연결하면 안 된다.
    """
    for p in PREDICTIONS:
        assert p["core"]["thesis_id"] == "NO_THESIS_SIGNAL_ONLY"


def test_expected_range_matches_ledger_cagr_components_exactly():
    """
    ⚠️ 이 테스트가 이 개선의 핵심 불변조건을 지킨다 - expected_low/high가
    새로 발명한 밴드가 아니라 ledger의 growth.breakdown.revenue_cagr_inputs
    최소/최대와 **정확히 일치**해야 한다.
    """
    ledger_by_ticker = {}
    for path in sorted(glob.glob("ledger/*.json")):
        led = json.load(open(path, encoding="utf-8"))
        ledger_by_ticker[led["meta"]["ticker"]] = led

    checked = 0
    for p in PREDICTIONS:
        ticker = p["core"]["ticker"]
        led = ledger_by_ticker.get(ticker)
        if led is None:
            continue
        ci = led["growth"]["breakdown"]["revenue_cagr_inputs"]
        vals = [v for v in ci.values() if v is not None]
        if len(vals) < 2:
            continue
        assert p["core"]["expected_low"] == pytest.approx(min(vals), abs=1e-6), ticker
        assert p["core"]["expected_high"] == pytest.approx(max(vals), abs=1e-6), ticker
        checked += 1

    assert checked >= 30, f"검증된 종목이 {checked}건뿐이다"


def test_prediction_date_is_freeze_date_not_backdated():
    """
    ⚠️ 예측이 실제로 동결된 시점은 스크립트 실행일(2026-08-16)이지 원분석일이
    아니다. backdate하면 "그때 이미 예측을 걸어뒀다"는 거짓 인상을 준다.
    """
    for p in PREDICTIONS:
        assert p["core"]["prediction_date"] == "2026-08-16"
        # 원분석일은 source/horizon에 별도로 남아 있어야 한다(정보 손실 없음)
        assert "원분석" in p["core"]["horizon"] or "원분석" in p["source"]


def test_core_hash_integrity_holds_for_all_frozen_predictions():
    """저장소에 실제로 쓰인 34건 전부 봉인 해시가 유효해야 한다."""
    from engine.prediction_ledger import core_hash

    for p in PREDICTIONS:
        assert core_hash(p["core"]) == p["core_hash"], p["core"]["ticker"]
