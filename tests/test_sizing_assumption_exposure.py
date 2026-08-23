"""
PHASE 2 — 사이징 구간 미검증 가정 자본 노출(2026-08-21)의 불변조건.

고정하는 것:
  ① 절제가 실제로 적용된다(조용히 무력화되면 '무해'로 오독된다)
  ② 감사 실행이 공식 산출물을 오염시키지 않는다
  ③ 버킷 구조가 최대 노출이라는 사실이 사라지지 않는다
"""
import importlib.util
import json
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
EXPOSURE = ROOT / "reports" / "sizing_assumption_exposure_2026-08-21.json"
BUYLIST = ROOT / "reports" / "buylist_2026-08-03.json"


def _load(name):
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _doc():
    return json.loads(EXPOSURE.read_text(encoding="utf-8"))


def _by_id():
    return {r["id"]: r for r in _doc()["results"]}


# ── ① 절제가 실제로 적용된다 ─────────────────────────────────────────────
def test_every_ablation_actually_moved_capital():
    """
    turnover 0은 "이 가정이 무해하다"가 아니라 대개 **절제가 적용되지 않았다**는
    뜻이다. 실제로 초판이 그랬다 - `effective_bucket_targets`의 `min_achievement`가
    함수 정의 시점 기본 인자라 모듈 상수를 바꿔도 반영되지 않아 turnover 0.00%가
    나왔고, 그건 v3.30이 기록한 "GEN 12%->18%"와 정면으로 모순됐다.
    (R-001에서 fcf0 축 키 오타로 한 축이 조용히 죽어 있던 것과 같은 유형.)
    """
    for r in _doc()["results"]:
        assert r["turnover"] > 0, (
            f"{r['id']}의 turnover가 0이다 - 절제가 실제로 적용됐는지 확인할 것")


def test_bucket_floor_ablation_matches_the_recorded_v330_effect():
    """
    v3.30 기록: 달성률 바닥 때문에 GEN 상한이 12%->18%로 완화됐다.
    따라서 바닥을 제거하면 GEN은 정확히 −6.00%p 움직여야 한다.
    이 대조가 절제 무력화를 잡아낸 실제 수단이었다.
    """
    r = _by_id()["bucket_floor_removed"]
    assert r["shifts"]["GEN"] == pytest.approx(-0.06, abs=1e-9)
    assert r["max_shift_ticker"] == "GEN"


# ── ② 공식 산출물 오염 금지 ──────────────────────────────────────────────
def test_audit_restores_official_outputs(tmp_path):
    """
    이 감사는 `build_buylist.main()`을 상수를 바꿔가며 여러 번 부른다.
    그 실행이 실제 매수리스트를 덮어쓴 채 끝나면 감사가 자본배분을 오염시킨다.
    """
    before = BUYLIST.read_bytes()
    mod = _load("sizing_assumption_exposure_2026_08_21")
    import contextlib
    import io
    with contextlib.redirect_stdout(io.StringIO()):
        mod.main()
    assert BUYLIST.read_bytes() == before, "감사 실행이 공식 매수리스트를 변경했다"
    for p in mod.OUTPUTS:
        assert not (ROOT / (p + mod.BACKUP_SUFFIX)).exists(), "백업 파일이 남았다"


def test_audit_declares_it_is_not_a_proposal():
    d = _doc()
    assert d["affects_official_judgment"] is False
    assert "not_a_proposal" in d


# ── ③ 최대 노출이 조용히 사라지지 않는다 ─────────────────────────────────
def test_bucket_structure_is_the_largest_unvalidated_exposure():
    """
    2026-08-21 실측: 버킷 구조(매핑+목표비중)가 turnover 18.82%로 최대다.
    (v3.67 규모 조건부 캡으로 비중이 바뀐 뒤 17.92%로 이동했으나 순위는 불변 -
     원 관측치를 지우지 않고 남긴다. 이 테스트는 절대값이 아니라 순위를 고정한다.)
    정성 심층조사 결과(CONFIDENCE_ADJ, 2.33%)보다 8배 크다 - 이 프로젝트가
    가장 많은 노력을 들인 축이 자본에는 가장 적게 영향을 준다는 뜻이다.
    """
    b = _by_id()
    bucket = max(b["bucket_diversification_removed"]["turnover"],
                 b["bucket_targets_equalized"]["turnover"])
    assert bucket > b["conf_qualitative_removed"]["turnover"] * 3
    assert bucket > b["flag_penalties_removed"]["turnover"] * 3
    assert b["bucket_diversification_removed"]["turnover"] == max(
        r["turnover"] for r in _doc()["results"])


def test_gen_weight_is_mostly_a_bucket_rule_artifact():
    """
    GEN은 포트폴리오 최대 보유(18.00%)이면서 Confidence 70(최하위권)·캡바인딩
    종목이다. 버킷 구조를 중립화하면 5.14%까지 내려간다 - 18% 중 12.86%p가
    quality 기여가 아니라 버킷 규칙의 산물이라는 뜻이다.
    """
    base = _doc()["base_weights"]["GEN"]
    shift = _by_id()["bucket_diversification_removed"]["shifts"]["GEN"]
    assert base == pytest.approx(0.18, abs=1e-9)
    assert base + shift < 0.06


def test_sizing_ablations_never_change_the_universe():
    """
    사이징 가정은 비중만 바꾸고 편입 종목 집합은 바꾸지 않아야 한다 - 유니버스는
    등급(S/A)에서 결정되므로. 바뀐다면 사이징과 선정이 뒤섞인 것이다.
    """
    for r in _doc()["results"]:
        assert r["universe_changed"] is False, r["id"]
