"""
SBC 하방 검증(2026-08-21)의 불변조건.

결정 #40("SBC 미확보 25종목 확보")의 재개조건이 P0-03 SEC provider로 충족돼
실행한 실험의 산출물과 그 배선을 고정한다.

고정하는 것:
  ① 재구성 계산이 기존 9종목 ledger와 정확히 일치한다(자기일치 없이는 나머지 무의미)
  ② SBC 차감은 Gap을 반드시 낮춘다(단조성) - 따라서 거짓편입 필터이지 진입 경로가 아니다
  ③ 미확보를 '무해'로 오독하지 않는다
  ④ 이 배선이 매수리스트 비중을 바꾸지 않는다
  ⑤ 자본이 걸린 SBC 의존 종목이 조용히 사라지지 않는다
  ⑥ 성장경로 비대칭이 알려진 한계로 명시돼 있다
"""
import importlib.util
import json
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
HARVEST = ROOT / "reports" / "sbc_harvest_2026-08-21.json"
BUYLIST = ROOT / "reports" / "buylist_2026-08-03.json"
BOUNDARY = ROOT / "reports" / "buylist_boundary_review_2026-08-16.json"


def _load(name):
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


HARVEST_MOD = _load("sbc_harvest_2026_08_21")
BUYLIST_MOD = _load("build_buylist_2026_08_03")


def _rows():
    return json.loads(HARVEST.read_text(encoding="utf-8"))["results"]


# ── ① 자기일치 — 이게 깨지면 신규 25건도 전부 신뢰할 수 없다 ──────────────
def test_reconstruction_matches_existing_ledger_cross_checks_exactly():
    """
    ledger에 이미 `sbc_cross_check`가 있는 종목에 같은 재구성 계산을 적용하면
    저장값과 **정확히** 일치해야 한다. 이 스크립트는 `run_analysis()`를 다시
    돌리지 않고 ledger 저장값으로 계산을 재현하므로, 그 재현이 원본과 어긋나면
    새로 얻은 25종목 결과의 근거가 통째로 사라진다.
    """
    ledgers = HARVEST_MOD._load_ledgers()
    checked = 0
    for _t, (_fn, d) in ledgers.items():
        cc = d.get("sbc_cross_check")
        if not cc:
            continue
        mine = HARVEST_MOD.sbc_cross_check_from_ledger(d, cc["sbc0"])
        for k in ("sbc_to_fcf_pct", "fcf0_sbc_adjusted",
                  "implied_growth_sbc_adjusted", "gap_sbc_adjusted"):
            if cc.get(k) is None and mine.get(k) is None:
                continue
            assert mine[k] == pytest.approx(cc[k], abs=1e-12), (_t, k)
        assert mine["judgment_sbc_adjusted"] == cc["judgment_sbc_adjusted"], _t
        assert mine["judgment_flipped"] == cc["judgment_flipped"], _t
        checked += 1
    assert checked >= 9, f"기존 확보 종목이 {checked}건뿐 - 자기일치 검증 표본 부족"


# ── ② 단조성 — 구조적으로 거짓편입 필터다 ────────────────────────────────
def test_sbc_adjustment_can_only_lower_the_gap():
    """
    SBC>0이면 fcf0가 줄고, 같은 시가총액을 정당화하려면 더 높은 성장이 필요하므로
    Implied Growth가 오른다 -> Gap = RG − IG는 반드시 감소한다.

    이 성질이 중요한 이유: 이 교차검증은 유니버스 **이탈만** 만들 수 있고 진입은
    만들 수 없다. 모델선택 검토(양방향)와 구조가 달라서, 배선에 '진입' 절을 두면
    영원히 비어 있는 절이 되어 읽는 사람을 오도한다.
    """
    rows = [r for r in _rows() if r["status"] == "OK"
            and r.get("gap_sbc_adjusted") is not None]
    assert rows
    for r in rows:
        assert r["sbc0"] > 0, r["ticker"]
        assert r["gap_sbc_adjusted"] <= r["gap_base"] + 1e-15, r["ticker"]


# 이 리포트는 **2026-08-21 당시 ledger 전수(34종목)의 스냅샷**이다(rows에
# status="OK"인 것도 이미 sbc_cross_check가 있던 것도 섞여 있음 - "미확보만"이
# 아니었다). 그래서 이후 추가된 ledger는 이 스냅샷에 없는 게 정상이다 -
# BSX 거짓탈락·TCOM 통화라벨과 동일한 "알려진 예외" 패턴으로 등록한다.
KNOWN_POST_SNAPSHOT_LEDGERS = {"CROX", "SIGI", "OKTA", "MEDP", "RYAN", "FIX", "NBIX", "NXT", "PATH", "PCTY", "EXEL", "PINS", "ROKU", "HLNE", "FIVE", "TW", "RLI", "DOCU", "CINF", "TENB", "SKYW", "RMBS", "BYD", "CRM", "DECK", "QCOM", "EAT"}  # 2026-09-01/04, 스냅샷(2026-08-21) 이후 신규


def test_harvest_covers_every_ledger_ticker():
    """리포트가 실제로 담은 종목이 그 시점 ledger 전수와 정확히 일치했는지."""
    tickers = {r["ticker"] for r in _rows()}
    ledger_tickers = set(HARVEST_MOD._load_ledgers()) - KNOWN_POST_SNAPSHOT_LEDGERS
    assert tickers == ledger_tickers


# ── ③ 미확보를 '무해'로 오독하지 않는다 ──────────────────────────────────
def test_missing_harvest_file_reports_unknown_not_no_dependence():
    assert BUYLIST_MOD.load_sbc_dependence("reports/__does_not_exist__.json") is None


def test_non_ok_rows_are_excluded_from_the_dependence_map(tmp_path):
    """
    확보 실패 행이 의존도 맵에 섞이면 `grade_sbc_adjusted=None`이 'S/A 아님'으로
    읽혀 **미확보 종목이 이탈로 잘못 표시**된다. status=OK만 통과해야 한다.
    """
    p = tmp_path / "h.json"
    p.write_text(json.dumps({"results": [
        {"ticker": "AAA", "status": "OK", "grade_sbc_adjusted": "A"},
        {"ticker": "BBB", "status": "YEAR_UNRESOLVED"},
    ]}), encoding="utf-8")
    dep = BUYLIST_MOD.load_sbc_dependence(str(p))
    assert set(dep) == {"AAA"}


# ── ④ 비중 불변 — 이 배선의 유일한 절대 조건 ─────────────────────────────
def test_sbc_boundary_review_changed_no_weight():
    rows = json.loads(BUYLIST.read_text(encoding="utf-8"))
    assert sum(r["weight_final"] for r in rows) == pytest.approx(1.0, abs=1e-9)
    boundary = json.loads(BOUNDARY.read_text(encoding="utf-8"))
    by_ticker = {r["ticker"]: r for r in rows}
    for h in boundary["sbc"]["held_but_sbc_dependent"]:
        row = by_ticker[h["ticker"]]
        assert row["weight_final"] > 0, h["ticker"]
        assert row["weight_final"] == pytest.approx(h["weight_final"], abs=1e-12)


# ── ⑤ 자본이 걸린 경고가 사라지지 않는다 ─────────────────────────────────
def test_capital_at_risk_from_sbc_assumption_is_surfaced():
    """
    2026-08-21 실측: TCOM(10.25%)·WDAY(4.51%)·TTD(2.70%)의 유니버스 편입이
    'SBC를 비용으로 보지 않는다'는 가정에 달려 있다. WDAY·TTD는 데이터가
    2026-08-01부터 ledger에 있었는데도 **매수리스트가 그 필드를 읽지 않아**
    자본배분 경로에 한 번도 드러난 적이 없었다.
    """
    boundary = json.loads(BOUNDARY.read_text(encoding="utf-8"))
    assert boundary["sbc"]["status"] == "확인"
    held = {h["ticker"] for h in boundary["sbc"]["held_but_sbc_dependent"]}
    assert "TCOM" in held, "TCOM의 SBC 의존 경고가 사라졌다면 근거를 재확인할 것"
    for h in boundary["sbc"]["held_but_sbc_dependent"]:
        assert h["grade"] in ("S", "A")
        assert h["grade_sbc_adjusted"] not in ("S", "A")


def test_every_buylist_row_carries_an_explicit_sbc_verdict():
    """True/False/None 셋 다 의미가 다르다 - 키 자체가 없으면 판별 불가."""
    for r in json.loads(BUYLIST.read_text(encoding="utf-8")):
        assert "sbc_dependent_universe" in r, r["ticker"]


# ── ⑥ 성장경로 비대칭을 한계로 명시한다 ──────────────────────────────────
def test_growth_path_asymmetry_is_declared_as_a_known_limitation():
    """
    현행 교차검증은 SBC를 fcf0에만 적용하고 FCF CAGR에는 적용하지 않는다.
    2026-08-21 실측으로 그 크기(GEN −1.07%p ~ PTC +13.41%p)를 처음 쟀고,
    확장은 DEFER했다(기준연도 FCF에서 SBC를 빼면 근사-0 기준연도 문제가 생긴다).
    이 한계 문구가 사라지면 독자가 SBC 차감 Gap을 정밀한 값으로 오독한다.
    """
    doc = json.loads(HARVEST.read_text(encoding="utf-8"))
    assert "known_limitation_growth_path" in doc
    assert doc["affects_official_judgment"] is False


# ── 부수 수정: 기준선 검증이 스스로를 오염시키던 문제 ─────────────────────
def test_verifying_the_baseline_does_not_rewrite_it():
    """
    2026-08-21 실측 결함: `freeze_baseline` 스크립트에 검증 경로가 CLI로 없어서,
    fingerprint를 확인하려면 재동결 함수를 부를 수밖에 없었고 그때마다
    `engine_version_at_freeze`가 **오늘 버전으로 조용히 재스탬프**됐다
    (실제로 v3.58 -> v3.59로 바뀌는 것을 확인). 이름이 '동결 시점'인 필드가
    거짓이 되는, v3.32가 잡은 버전 스탬프 문제와 같은 유형이다.
    """
    mod = _load("freeze_baseline_2026_08_16")
    path = ROOT / mod.BASELINE_PATH
    before = path.read_bytes()
    rc = mod.main([])                      # 인자 없음 = 검증
    assert rc == 0
    assert path.read_bytes() == before, "검증이 기준선 파일을 변경했다"


def test_refreeze_preserves_the_original_freeze_version():
    """재동결해도 '동결 시점' 버전은 보존돼야 한다(오늘 버전으로 덮어쓰지 않는다)."""
    mod = _load("freeze_baseline_2026_08_16")
    path = ROOT / mod.BASELINE_PATH
    original = json.loads(path.read_text(encoding="utf-8"))
    frozen_version = original["engine_version_at_freeze"]
    from engine.expectation_gap_engine import ENGINE_VERSION
    payload = mod.freeze()
    try:
        assert payload["engine_version_at_freeze"] == frozen_version
        if frozen_version != ENGINE_VERSION:
            assert payload["engine_version_at_freeze"] != ENGINE_VERSION
    finally:
        path.write_text(json.dumps(original, ensure_ascii=False, indent=2),
                        encoding="utf-8")
