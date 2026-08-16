"""
매수리스트 경계검토 배선의 불변조건 (2026-08-16).

2026-08-16 모델선택 D3 연구의 ADOPT 결정("등급·유니버스 수준 모델의존성 병기")을
`build_buylist`에 배선했다. **이 배선의 유일한 절대 조건은 비중을 바꾸지 않는
것이다** - 병기·자동판정 안 함 원칙이며, 어기면 검증된 사이징 산출물이 조용히
흔들린다(이전 감사가 build_buylist 재작성을 DEFER한 바로 그 이유).

⚠️ 이 프로젝트가 겪은 패턴: 결정을 문서에만 적어두면 지켜지지 않는다
(run_self_check·confidence_score·claim/lock·cross_check_prior_record 4회).
그래서 ADOPT 결정을 리포트가 아니라 실제 결정경로에 배선하고, 그 안전성을
테스트로 고정한다.
"""
import importlib.util
import json
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
BUYLIST = ROOT / "reports" / "buylist_2026-08-03.json"
BOUNDARY = ROOT / "reports" / "buylist_boundary_review_2026-08-16.json"


def _load_script():
    path = ROOT / "scripts" / "build_buylist_2026_08_03.py"
    spec = importlib.util.spec_from_file_location("build_buylist_2026_08_03", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


MOD = _load_script()


def test_weights_still_sum_to_one_and_respect_bucket_caps():
    rows = json.loads(BUYLIST.read_text(encoding="utf-8"))
    assert sum(r["weight_final"] for r in rows) == pytest.approx(1.0, abs=1e-9)
    for r in rows:
        assert r["weight_final"] <= r["bucket_cap_applied"] + 1e-9, r["ticker"]


def test_boundary_review_never_changed_any_weight():
    """
    경계검토는 weight_final이 확정된 **뒤에** 키만 덧붙인다. 그 결과 경계검토가
    지목한 종목(BRO)의 비중이 다른 종목과 같은 규칙으로만 결정돼 있어야 한다.
    """
    rows = {r["ticker"]: r for r in json.loads(BUYLIST.read_text(encoding="utf-8"))}
    boundary = json.loads(BOUNDARY.read_text(encoding="utf-8"))
    for h in boundary["held_but_model_dependent"]:
        row = rows[h["ticker"]]
        # 경계검토에 걸렸다고 비중이 깎이거나 0이 되지 않았는지
        assert row["weight_final"] > 0, h["ticker"]
        assert row["weight_final"] == pytest.approx(h["weight_final"], abs=1e-12)


def test_missing_data_is_reported_as_unknown_not_as_no_dependence():
    """데이터 없음을 '의존 없음'으로 오독하지 않는다(프로젝트 반복 원칙)."""
    assert MOD.load_model_dependence("reports/__does_not_exist__.json") is None


def test_held_position_bro_is_flagged_as_model_dependent():
    """
    BRO는 보유 중(6.75%)인데 A등급이 모델선택에 달려 있고 그 사유가 과거기록
    답습이다. 이 경고가 조용히 사라지면 안 된다.
    """
    boundary = json.loads(BOUNDARY.read_text(encoding="utf-8"))
    held = {h["ticker"]: h for h in boundary["held_but_model_dependent"]}
    assert "BRO" in held, "BRO의 모델의존 경고가 사라졌다면 근거를 재확인할 것"
    assert held["BRO"]["reason_is_prior_record"] is True
    assert held["BRO"]["grade"] == "A" and held["BRO"]["grade_alternative"] == "B"


def test_false_rejection_candidates_are_surfaced():
    """
    유니버스 밖인데 대안모델이면 진입하는 종목(거짓탈락 후보)이 드러나야 한다 -
    BSX 스크리너 사건이 확립한 '배제된 종목은 아무도 다시 안 본다' 문제.
    """
    boundary = json.loads(BOUNDARY.read_text(encoding="utf-8"))
    tickers = {e["ticker"] for e in boundary["excluded_but_would_enter"]}
    assert tickers, "거짓탈락 후보가 최소 1건 있어야 한다(2026-08-16 실측 DSGX·VRT)"
    for e in boundary["excluded_but_would_enter"]:
        assert e["grade"] not in ("S", "A")
        assert e["grade_alternative"] in ("S", "A")


def test_ranking_staleness_is_distinguished_from_judgment_rejection():
    """
    순위 파일 노후화로 고려조차 안 된 종목은 '판정에 의한 탈락'과 구분돼야 한다.
    2026-08-16 실측: BSX(분석 08-13)가 순위 파일(08-02)에 없다.
    """
    boundary = json.loads(BOUNDARY.read_text(encoding="utf-8"))
    ranked = {r["ticker"] for r in json.loads(
        (ROOT / "reports" / "portfolio_ranking_2026-08-02.json").read_text(encoding="utf-8"))}
    for m in boundary["missing_from_ranking"]:
        assert m["ticker"] not in ranked
        assert (ROOT / "ledger").glob(f"{m['ticker']}_*.json") is not None
