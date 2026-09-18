"""
포트폴리오 점검(v3.82)의 불변조건.

이 모듈의 가치는 '무엇을 계산하는가'가 아니라 **'무엇을 계산하지 않는가'**에
있다. 그래서 테스트의 절반이 경계를 고정하는 데 쓰인다 - `engine/thesis.py`가
`test_no_function_maps_gap_to_action`으로 같은 일을 한 선례가 있다.
"""
import ast
import json
import os
import pathlib

import pytest

from engine import portfolio as P

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = (ROOT / "engine" / "portfolio.py").read_text(encoding="utf-8")
SCRIPT = (ROOT / "scripts" / "portfolio_review.py").read_text(encoding="utf-8")
TODAY = "2026-09-05"


# ── 경계 ① 액션을 고르지 않는다 ──────────────────────────────────────────

def test_no_function_produces_a_buy_or_sell_action():
    """
    Gap/등급을 넣으면 액션이 나오는 함수가 생기면 실패한다.

    ⚠️ 이 경계가 무너지면 검증되지 않은 신호(gap_analysis.GAP_SIGNAL_STATUS
    = RESEARCH_HYPOTHESIS)가 곧바로 자본배분이 된다 - engine/thesis.py가
    v3.48에서 확립한 것과 같은 이유다.
    """
    banned = ("decide", "recommend", "action_for", "should_buy", "should_sell",
              "signal_to_action", "suggest")
    for node in ast.walk(ast.parse(SRC)):
        if isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
            low = node.name.lower()
            assert not any(b in low for b in banned), (
                f"{node.name}: 액션을 산출하는 함수로 보인다 - 이 모듈의 경계 위반"
            )


def test_no_review_output_contains_an_action_field():
    r = P.review_portfolio(TODAY)
    for p in r["positions"]:
        assert "action" not in p and "recommendation" not in p, p["ticker"]
    for c in r["unheld_sa_candidates"]:
        assert "action" not in c and "recommendation" not in c, c["ticker"]


# ── 경계 ② 목표비중을 계산하지 않는다 ────────────────────────────────────

def test_no_target_weight_is_produced():
    """
    2026-08-21 PHASE 2 감사: 근거 없는 버킷 상수가 자본의 16.75~18.82%를
    좌우하는 반면 가장 노력 들인 축은 2.33%만 움직였다. 새 배분 공식을
    만들면 그 문제를 복제한다.
    """
    r = P.review_portfolio(TODAY)
    for p in r["positions"]:
        # 'weight'는 **현재 보유 비중**(관측값)이고 목표치가 아니다
        assert "target_weight" not in p and "weight_final" not in p
        assert "suggested_weight" not in p
    banned = ("target_weight", "weight_final", "suggested_weight", "sizing")
    for node in ast.walk(ast.parse(SRC)):
        if isinstance(node, ast.FunctionDef):
            assert not any(b in node.name.lower() for b in banned), node.name


# ── 경계 ③ 어떤 파일에도 쓰지 않는다 ─────────────────────────────────────

def test_engine_module_has_no_write_path():
    """
    보유 상태는 사람이 유지한다(v3.64 '확인은 사람의 행위'). 코드가 고치기
    시작하면 기록의 신뢰성이 무너진다.
    """
    for node in ast.walk(ast.parse(SRC)):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id == "open":
                mode = None
                for kw in node.keywords:
                    if kw.arg == "mode" and isinstance(kw.value, ast.Constant):
                        mode = kw.value.value
                if len(node.args) >= 2 and isinstance(node.args[1], ast.Constant):
                    mode = node.args[1].value
                assert mode in (None, "r", "rt"), f"쓰기 모드 open 발견: {mode}"
        if isinstance(node, ast.Attribute) and node.attr in ("write_text", "unlink"):
            pytest.fail(f"쓰기/삭제 경로 발견: {node.attr}")


def test_review_does_not_touch_ledger_or_holdings(tmp_path):
    """AST만으로는 간접 호출을 못 잡는다 - 실제 실행 후 파일 상태를 확인한다."""
    before = {p: (os.path.getmtime(p), os.path.getsize(p))
              for p in sorted(pathlib.Path("ledger").glob("*.json"))}
    hp = pathlib.Path(P.HOLDINGS_PATH)
    h_before = (os.path.getmtime(hp), hp.read_bytes())

    P.review_portfolio(TODAY)

    after = {p: (os.path.getmtime(p), os.path.getsize(p))
             for p in sorted(pathlib.Path("ledger").glob("*.json"))}
    assert after == before, "ledger가 변경됐다"
    assert (os.path.getmtime(hp), hp.read_bytes()) == h_before, "holdings가 변경됐다"


# ── 사전등록 규칙 ────────────────────────────────────────────────────────

def test_rules_are_declared_unvalidated():
    """
    플래그가 붙은 종목이 실제로 더 나쁜 결과를 냈는지 확인할 수단이 없다
    (실현수익률 관측 0건). 그 사실이 코드에서 사라지면 독자가 플래그를
    검증된 위험신호로 오독한다.
    """
    assert P.RULE_STATUS == "PRE_REGISTERED_NOT_VALIDATED"
    r = P.review_portfolio(TODAY)
    assert r["rule_status"] == P.RULE_STATUS


def test_model_divergence_threshold_reuses_the_engine_constant():
    """
    새 숫자를 발명하지 않았다 - 엔진이 이미 경고에 쓰는 3%p(v3.19)를 그대로
    쓴다. 값이 갈라지면 같은 종목이 엔진에서는 경고인데 여기서는 아니게 된다.
    """
    assert P.MODEL_DIVERGENCE_THRESHOLD == 0.03
    ledgers = P.load_ledgers()
    for t, d in ledgers.items():
        div = (d.get("implied_growth") or {}).get("models", {}).get("divergence")
        if div is None:
            continue
        engine_warned = any("모델 괴리 경고" in x for x in (d.get("data_limitations") or []))
        assert engine_warned == (div >= P.MODEL_DIVERGENCE_THRESHOLD), t


def test_every_rule_code_has_a_written_rule():
    r = P.review_portfolio(TODAY)
    for p in r["positions"]:
        for f in p["flags"]:
            assert f["code"] in P.REVIEW_RULES
            assert f["rule"] == P.REVIEW_RULES[f["code"]]
            assert f["detail"], f"{p['ticker']}/{f['code']}: 근거가 비어 있다"


# ── 판정 불가 종목을 조용히 버리지 않는다 ────────────────────────────────

def test_positions_without_judgment_are_surfaced_not_dropped():
    """
    'ledger가 없으니 표에서 뺀다'가 가장 나쁜 처리다 - 판정 불가가
    '문제 없음'으로 보이게 된다(is_insurer·sbc_cross_check·holdings_overlap이
    매번 경계해온 '데이터 없음을 안전으로 오독' 원칙).
    """
    r = P.review_portfolio(TODAY)
    holdings = P.load_holdings()
    assert len(r["positions"]) == len(holdings["positions"])
    no_judgment = [p for p in r["positions"] if not p["has_judgment"]]
    for p in no_judgment:
        assert any(f["code"] == "NO_JUDGMENT" for f in p["flags"]), p["ticker"]
    cov = r["coverage"]
    assert cov["weight_with_judgment"] + cov["weight_without_judgment"] == pytest.approx(1.0)


def test_weight_reconciliation_discrepancy_is_surfaced_not_hidden():
    """
    보유 합계(증권앱 표시)와 개별 평가금액 합이 반올림 때문에 정확히
    일치하지 않는다. **조용히 정규화해서 1.0으로 맞추지 않는다** - 차이를
    드러내고, 그 차이가 무시할 수준인지 읽는 사람이 판단하게 한다
    (P0-07이 출처 불일치를 자동 해소하지 않은 것과 같은 원칙).
    """
    r = P.review_portfolio(TODAY)
    rec = r["reconciliation"]
    assert rec["difference"] == rec["reported_total"] - rec["sum_of_positions"]
    # 실측 차이는 0.0001% 미만 - 표시 반올림 수준임을 고정한다
    assert abs(rec["relative_difference"]) < 1e-5
    assert sum(p["weight"] for p in r["positions"]) == pytest.approx(
        1.0 - rec["relative_difference"], abs=1e-12)


# ── 우선순위는 합성 점수가 아니다 ────────────────────────────────────────

def test_review_queue_is_lexicographic_not_a_composite_score():
    """
    §31 안티기능 등록부: 단일 합성점수를 만들지 않는다. 큐는 (플래그 수,
    비중) 사전식 정렬이라 각 축이 관측 가능한 사실 그대로 남는다.
    """
    r = P.review_portfolio(TODAY)
    keys = [(-q["n_flags"], -q["weight"]) for q in r["review_queue"]]
    assert keys == sorted(keys)
    for q in r["review_queue"]:
        assert "score" not in q and "rank_score" not in q


# ── 미보유 후보 ──────────────────────────────────────────────────────────

def test_unheld_candidates_exclude_holdings_and_are_sa_only():
    r = P.review_portfolio(TODAY)
    held = {p["ticker"] for p in r["positions"]}
    for c in r["unheld_sa_candidates"]:
        assert c["ticker"] not in held
        assert c["grade"] in ("S", "A")


def test_candidate_list_is_not_labelled_as_a_buy_list():
    """
    이 목록은 `build_buylist`가 요구하는 버킷·정성조사를 통과하지 않았다.
    '매수 권고 아님'이라는 문구가 산출물에서 사라지면 오독된다.
    """
    assert "매수 권고 아님" in SCRIPT
    r = P.review_portfolio(TODAY)
    assert any("액션" in x for x in r["not_provided"])
    assert any("목표비중" in x for x in r["not_provided"])


# ── 리포트 재현성 ────────────────────────────────────────────────────────

def test_report_is_deterministic_for_a_fixed_date():
    a = json.dumps(P.review_portfolio(TODAY), sort_keys=True, ensure_ascii=False)
    b = json.dumps(P.review_portfolio(TODAY), sort_keys=True, ensure_ascii=False)
    assert a == b
