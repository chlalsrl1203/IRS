"""
engine/portfolio_pipeline.py 테스트 (2026-09-06).

이 모듈은 `portfolio_screen_2026_09_05.py`(Stage 0-1) +
`build_conviction_portfolio_2026_09_05.py`(Stage 2-3) +
`publish_buylist_2026_09_06.py`(발행)을 하나로 합친 것이다. 핵심 불변조건은
**골든 재현** - 통합 전 세 스크립트가 만든 `conviction_portfolio_2026-09-05.json`
(18종목)을 오차 없이 재현해야 한다. 재현이 안 되면 통합 자체가 계산을 바꾼
것이므로 실패해야 맞다.

경계 테스트는 `engine/portfolio.py`(v3.82, 실제 보유종목 검토용 - 이 모듈과는
목적이 다르다: 그쪽은 사이징을 아예 하지 않고, 이 모듈은 S/A 후보의 비중을
정하는 게 본업이다)의 선례를 따르되, "사이징 금지"가 아니라 "**근거 없는
버킷 목표비중 금지**"(PHASE 2 감사)로 경계를 다시 잡는다.
"""
import ast
import json
import os
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = (ROOT / "engine" / "portfolio_pipeline.py").read_text(encoding="utf-8")

from engine import portfolio_pipeline as PP  # noqa: E402
from engine.monitor_state import load_acknowledgements  # noqa: E402
from engine.portfolio import load_ledgers  # noqa: E402

CONVICTION_PATH = ROOT / "reports" / "conviction_portfolio_2026-09-05.json"


# ── 경계 ① 목표비중을 발명하지 않는다 ────────────────────────────────────
def test_no_bucket_target_weight_dict():
    """
    PHASE 2 감사(2026-08-21) - 근거 없는 버킷 목표비중(40/30/20/10 등)이
    자본의 16.75~18.82%를 좌우했다. 이 모듈은 그 상수를 다시 만들지 않는다 -
    quality_score 순위 + 종목당 상한만 쓴다.
    """
    banned = ("bucket_target", "target_weight", "cluster_target")
    for node in ast.walk(ast.parse(SRC)):
        if isinstance(node, ast.FunctionDef):
            assert not any(b in node.name.lower() for b in banned), node.name
    assert "bucket_target" not in SRC.lower()


# ── 경계 ② 파일에 쓰지 않는다(ledger/holdings/qualitative_overrides 전부 읽기 전용) ──
def test_module_never_writes_files():
    """
    ledger·holdings.json·qualitative_overrides.json 어디에도 쓰지 않는다 -
    발행은 scripts/build_portfolio.py가 명시적으로 한다(engine/은 순수 계산).
    """
    for node in ast.walk(ast.parse(SRC)):
        if isinstance(node, ast.Call):
            func = node.func
            fname = getattr(func, "attr", None) or getattr(func, "id", None)
            assert fname not in ("write_text", "dump"), (
                f"{fname}: engine/portfolio_pipeline.py는 파일을 쓰면 안 된다"
            )


# ── 경계 ③ 액션을 자동으로 고르지 않는다 ─────────────────────────────────
def test_no_function_produces_a_buy_or_sell_action():
    banned = ("decide", "recommend", "should_buy", "should_sell",
              "signal_to_action", "auto_approve")
    for node in ast.walk(ast.parse(SRC)):
        if isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
            low = node.name.lower()
            assert not any(b in low for b in banned), node.name


# ── ④ EXCLUDED 사실은 파생한다 - 하드코딩된 티커 사전이 없다 ────────────────
def test_falsification_confirmed_is_derived_not_hardcoded():
    """
    구 스크립트의 FALSIFICATION_CONFIRMED = {"TTD": "..."}는 사실의 두 번째
    사본이었다 - monitor/acknowledgements.json에 이미 TRIGGERED로 기록돼
    있다. **코드**(모듈 docstring이 역사적 배경을 설명하며 "TTD"를 예시로
    언급하는 것과는 별개로) 안에 티커를 키로 하는 dict 리터럴이 있으면 안
    된다.
    """
    tree = ast.parse(SRC)
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            for k in node.keys:
                if isinstance(k, ast.Constant) and k.value == "TTD":
                    raise AssertionError(
                        "TTD가 dict 리터럴 키로 하드코딩돼 있다 - "
                        "monitor/acknowledgements.json에서 파생해야 한다"
                    )


def test_confirmed_falsifications_finds_ttd_from_real_acknowledgements():
    acks = load_acknowledgements()
    out = PP.confirmed_falsifications(acks)
    assert "TTD" in out
    assert all(e["verdict"] == "TRIGGERED" for e in out["TTD"])


def test_confirmed_falsifications_excludes_not_triggered():
    acks = load_acknowledgements()
    out = PP.confirmed_falsifications(acks)
    # NOT_TRIGGERED/INCONCLUSIVE 종목은 절대 포함되면 안 된다
    for e in acks["entries"].values():
        for entry in e:
            if entry["verdict"] != "TRIGGERED":
                assert entry["ticker"] not in out or all(
                    x["verdict"] == "TRIGGERED" for x in out[entry["ticker"]]
                )


# ── ⑤ 정성 레지스트리 - 없으면 크래시하지 않고 미검증 폴백 ──────────────────
def test_qualitative_overrides_missing_file_returns_empty():
    got = PP.load_qualitative_overrides(path=str(ROOT / "nonexistent.json"))
    assert got == {"overrides": {}, "g6_substitutes": {}}


def test_unresearched_ticker_falls_back_to_engine_confidence():
    """레지스트리에 없는 종목이 크래시하면 안 된다 - 엔진 원시 Confidence로
    폴백하고 '미검증'을 명시한다."""
    survivor = {
        "ticker": "ZZZZ", "company": "Test Co", "grade": "A", "gap": 0.10,
        "confidence_engine": 94, "cap_applied": None, "analyzed_at": "2026-09-06",
        "gap_min": 0.05,
    }
    # 단일 종목이면 비중이 100%가 돼 12% 상한과 무관하게 무조건 캡오버가
    # 되므로(재분배할 다른 종목이 없어 apply_cap이 예외를 던진다), 이
    # 테스트는 Confidence 폴백 로직만 보고 싶으니 상한을 사실상 없앤다.
    sized = PP.size_portfolio([survivor], overrides={}, per_stock_cap=1.0)
    assert len(sized) == 1
    assert sized[0]["confidence_adj"] == 94
    assert sized[0]["confidence_status"] == "미검증"


# ── ⑥ G6은 등급이 실제로 이탈할 때만 배제한다 ────────────────────────────
def test_g6_does_not_exclude_when_grade_survives_substitution():
    """
    회사 가이던스로 대체해도 여전히 S/A면 배제하면 안 된다(DLO형 - 상향
    가이던스). G6은 "회사 성장률이 낮다"가 아니라 "등급이 이탈하는가"만
    본다.
    """
    survivor = {
        "ticker": "GOOD", "company": "Good Co", "grade": "A", "gap": 0.10,
        "realistic_growth": 0.12, "confidence_engine": 94, "cap_applied": "12.0%",
        "analyzed_at": "2026-09-06",
    }
    # 엔진 IG = RG - Gap = 0.02. 회사성장률을 오히려 더 높게 주면(0.20) Gap이
    # 더 벌어져 등급이 개선되거나 최소한 이탈하지 않아야 한다.
    subs = {"GOOD": {"company_growth": 0.20, "basis": "test", "detail": "test"}}
    kept, excluded = PP.apply_g6([survivor], subs)
    assert not excluded
    assert kept[0]["ticker"] == "GOOD"


def test_g6_excludes_when_grade_actually_leaves_universe():
    survivor = {
        "ticker": "BAD", "company": "Bad Co", "grade": "A", "gap": 0.10,
        "realistic_growth": 0.12, "confidence_engine": 94, "cap_applied": None,
        "analyzed_at": "2026-09-06",
    }
    # IG = 0.02. 회사성장률을 아주 낮게(-0.20) 주면 Gap이 크게 음수가 돼
    # 등급이 S/A를 벗어나야 한다.
    subs = {"BAD": {"company_growth": -0.20, "basis": "test", "detail": "test"}}
    kept, excluded = PP.apply_g6([survivor], subs)
    assert not kept
    assert excluded[0]["ticker"] == "BAD"


# ── ⑦ 상한흡수 - v3.67 수정판 그대로 ─────────────────────────────────────
def test_apply_cap_respects_per_stock_cap():
    # 12% 상한 아래 A 하나만 20% 초과 - 나머지 9종목이 여유가 있어 흡수 가능.
    rows = [{"ticker": "A", "weight": 0.20, "quality_score": 20.0}]
    rows += [{"ticker": f"X{i}", "weight": 0.08, "quality_score": 8.0}
             for i in range(10)]
    PP.apply_cap(rows, cap=0.12)
    assert all(r["weight"] <= 0.12 + 1e-9 for r in rows)
    assert abs(sum(r["weight"] for r in rows) - 1.0) < 1e-9


def test_apply_cap_raises_when_no_room_to_absorb():
    rows = [
        {"ticker": "A", "weight": 0.60, "quality_score": 60.0},
        {"ticker": "B", "weight": 0.40, "quality_score": 40.0},
    ]
    try:
        PP.apply_cap(rows, cap=0.12)
        raised = False
    except RuntimeError:
        raised = True
    assert raised, "재분배할 여유가 없으면 조용히 위반을 통과시키면 안 된다"


# ── ⑧ 골든 재현 - 통합 전후 계산이 정확히 같아야 한다 ────────────────────
def test_golden_reproduction_matches_conviction_portfolio():
    """
    portfolio_screen + build_conviction_portfolio 두 스크립트가 만든
    conviction_portfolio_2026-09-05.json(18종목)을, 통합된 engine/
    portfolio_pipeline.py가 오차 없이 재현하는지 확인한다. 이게 실패하면
    통합이 계산을 바꾼 것이다.
    """
    if not CONVICTION_PATH.exists():
        return  # 재현 대상 파일이 없으면(다른 환경) 스킵

    ledgers = load_ledgers()
    sbc_verdicts = PP.load_sbc_verdicts()
    acks = load_acknowledgements()
    falsification_confirmed = PP.confirmed_falsifications(acks)
    qual = PP.load_qualitative_overrides()

    survivors, _ = PP.screen_universe(
        ledgers, sbc_verdicts, falsification_confirmed, qual["overrides"])
    kept, excluded_g6 = PP.apply_g6(survivors, qual["g6_substitutes"])
    sized = PP.size_portfolio(kept, qual["overrides"])

    expected = {p["ticker"]: p["weight"]
                for p in json.loads(CONVICTION_PATH.read_text(encoding="utf-8"))["positions"]}
    got = {r["ticker"]: r["weight"] for r in sized}

    assert set(got) == set(expected), (set(got) ^ set(expected))
    for t in expected:
        assert abs(got[t] - expected[t]) < 1e-9, (
            f"{t}: 재현값 {got[t]} vs 원본 {expected[t]}"
        )

    # G6 배제 종목도 동일해야 한다(RYAN·CROX)
    assert {r["ticker"] for r in excluded_g6} == {"RYAN", "CROX"}


def test_to_buylist_rows_has_daily_brief_schema():
    """`scripts/daily_brief.py::section_overseas()`가 요구하는 필드명 그대로."""
    sized = [{
        "ticker": "X", "company": "X Co", "weight": 0.10, "grade": "A",
        "confidence_adj": 80, "confidence_status": "검증(2026-09-06)",
        "cap_bound": None, "cluster": "test", "gap_pct": 10.0,
        "analyzed_at": "2026-09-06",
    }]
    rows = PP.to_buylist_rows(sized)
    r = rows[0]
    for key in ("weight_final", "grade", "conf_adj", "conf_status", "cap_bound"):
        assert key in r, key
    assert abs(sum(r["weight_final"] for r in rows) - 0.10) < 1e-12
