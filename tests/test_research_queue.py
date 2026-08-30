"""
research_queue.py 테스트 (2026-08-30).

고정하는 것:
  ① **필드 없음을 "범위 안"으로 읽지 않는다**(첫 실행에서 실제로 난 결함)
  ② 우선순위는 합성 점수가 아니라 사전식 정렬이다
  ③ 상태는 ledger·매수리스트에서 파생한다(손으로 관리하는 상태 파일 없음)
  ④ 이번에 안 나온 종목을 큐에서 지우지 않는다(지속성 신호가 사라진다)
  ⑤ 실행 1회뿐이면 지속성 축이 작동하지 않는다고 정직하게 말한다
  ⑥ 이 모듈은 매수리스트를 만들지 않는다(판정·사이징 함수가 없다)
"""
import inspect
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from engine import research_queue as Q  # noqa: E402


def _row(t, gap, cap, scope=None, tier="S"):
    r = {"ticker": t, "expectation_gap_est": gap, "market_cap": cap, "tier": tier}
    if scope is not None:
        r["out_of_validated_scope"] = scope
    return r


# ── ① 필드 없음 ≠ 범위 안 (실제 결함의 회귀 테스트) ───────────────────────
def test_missing_scope_field_is_recomputed_not_assumed_in_scope():
    """
    v3.76 이전에 만들어진 스크리닝 결과에는 `out_of_validated_scope` 키가 없다.
    `row.get(...) or []`로 받으면 범위 밖 종목이 전부 "범위 안"이 되고, 실제로
    첫 실행에서 VATE(Gap +93%p, 시총 $0.03B)가 최우선 분석 후보로 올라왔다.
    """
    q = Q.merge_run({}, [_row("VATE", 0.9309, 30e6)], "2026-08-30")
    e = q["VATE"]
    assert e["out_of_validated_scope"], "범위 밖인데 빈 리스트로 들어왔다"
    assert e.get("scope_recomputed") is True


def test_explicit_empty_scope_is_respected_not_recomputed():
    """이미 계산된 빈 리스트는 그대로 믿는다 - 재계산은 **키가 없을 때만**."""
    q = Q.merge_run({}, [_row("CROX", 0.2397, 4.8e9, scope=[])], "2026-08-30")
    assert q["CROX"]["out_of_validated_scope"] == []
    assert "scope_recomputed" not in q["CROX"]


def test_out_of_scope_candidate_is_excluded_from_next_to_research():
    q = Q.merge_run({}, [_row("VATE", 0.9309, 30e6),
                         _row("CROX", 0.2397, 4.8e9)], "2026-08-30")
    entries = Q.annotate(q, set(), set(), "2026-08-30")
    nxt = Q.next_to_research(list(entries.values()))
    assert [e["ticker"] for e in nxt] == ["CROX"]


# ── ② 사전식 정렬 (합성 점수 없음) ────────────────────────────────────────
def test_in_scope_beats_higher_gap_out_of_scope():
    """Gap이 훨씬 커도 범위 밖이면 뒤로 간다 - 점수를 합치면 이게 뒤집힌다."""
    q = Q.merge_run({}, [_row("BIGGAP", 0.90, 30e6),
                         _row("INSCOPE", 0.10, 10e9)], "2026-08-30")
    ordered = Q.priority_order(list(Q.annotate(q, set(), set(),
                                               "2026-08-30").values()))
    assert ordered[0]["ticker"] == "INSCOPE"


def test_unanalyzed_beats_analyzed_at_same_scope():
    q = Q.merge_run({}, [_row("DONE", 0.20, 10e9, scope=[]),
                         _row("NEW", 0.10, 10e9, scope=[])], "2026-08-30")
    ordered = Q.priority_order(
        list(Q.annotate(q, {"DONE"}, set(), "2026-08-30").values()))
    assert ordered[0]["ticker"] == "NEW"


def test_persistence_beats_gap():
    """오래 살아남은 종목이 한 주 반짝 통과한 높은 Gap보다 앞선다."""
    q = Q.merge_run({}, [_row("OLD", 0.10, 10e9, scope=[])], "2026-08-16")
    q = Q.merge_run(q, [_row("OLD", 0.10, 10e9, scope=[]),
                        _row("FRESH", 0.20, 10e9, scope=[])], "2026-08-30")
    ordered = Q.priority_order(
        list(Q.annotate(q, set(), set(), "2026-08-30").values()))
    assert ordered[0]["ticker"] == "OLD"
    assert q["OLD"]["times_seen"] == 2


def test_priority_reason_is_attached():
    """순위만 주고 근거를 안 주면 사람이 검증할 수 없다."""
    q = Q.merge_run({}, [_row("X", 0.10, 10e9, scope=[])], "2026-08-30")
    ordered = Q.priority_order(list(Q.annotate(q, set(), set(),
                                               "2026-08-30").values()))
    assert "검증범위 안" in ordered[0]["priority_reason"]
    assert "미분석" in ordered[0]["priority_reason"]


# ── ③ 상태는 파생한다 ────────────────────────────────────────────────────
def test_state_is_derived_from_ledger_and_buylist():
    assert Q.derive_state("A", {"A"}, {"A"}) == "IN_BUYLIST"
    assert Q.derive_state("A", {"A"}, set()) == "ANALYZED"
    assert Q.derive_state("A", set(), set()) == "QUEUED"


def test_buylist_membership_wins_over_ledger():
    """매수리스트 종목은 ledger에도 있다 - 더 구체적인 상태를 택해야 한다."""
    assert Q.derive_state("ACGL", {"ACGL"}, {"ACGL"}) == "IN_BUYLIST"


# ── ④ 안 나온 종목을 지우지 않는다 ───────────────────────────────────────
def test_absent_ticker_is_kept_so_persistence_survives():
    """
    지웠다가 다음 주에 다시 나오면 times_seen이 1로 초기화돼 지속성 신호가
    통째로 사라진다. "안 보인다"와 "본 적 없다"는 다르다.
    """
    q = Q.merge_run({}, [_row("GONE", 0.1, 10e9, scope=[])], "2026-08-16")
    q = Q.merge_run(q, [_row("OTHER", 0.1, 10e9, scope=[])], "2026-08-30")
    assert "GONE" in q and q["GONE"]["last_seen"] == "2026-08-16"
    e = Q.annotate(q, set(), set(), "2026-08-30")["GONE"]
    assert e["days_since_seen"] == 14


def test_same_run_twice_does_not_double_count():
    q = Q.merge_run({}, [_row("X", 0.1, 10e9, scope=[])], "2026-08-30")
    q = Q.merge_run(q, [_row("X", 0.1, 10e9, scope=[])], "2026-08-30")
    assert q["X"]["times_seen"] == 1


# ── ⑤ 지속성 축이 언제 작동하는지 정직하게 말한다 ─────────────────────────
def test_single_run_reports_persistence_not_discriminating():
    q = Q.merge_run({}, [_row("X", 0.1, 10e9, scope=[])], "2026-08-30")
    p = Q.persistence_available(q)
    assert p["n_runs"] == 1 and p["discriminating"] is False


def test_two_runs_enable_persistence():
    q = Q.merge_run({}, [_row("X", 0.1, 10e9, scope=[])], "2026-08-16")
    q = Q.merge_run(q, [_row("X", 0.1, 10e9, scope=[])], "2026-08-30")
    assert Q.persistence_available(q)["discriminating"] is True


# ── ⑥ 이 모듈은 매수리스트를 만들지 않는다 ───────────────────────────────
def test_module_does_not_produce_weights_or_verdicts():
    """
    스크리닝 후보가 매수리스트에 들어가려면 정식분석(run_analysis)과 정성조사가
    필요하다 - 큐가 비중이나 판정을 내놓기 시작하면 그 빈칸을 지어내는 것이 된다.
    """
    banned = ("weight", "size", "sizing", "buy", "allocat", "verdict", "judge")
    for name, obj in vars(Q).items():
        if name.startswith("_") or not inspect.isfunction(obj):
            continue
        assert not any(b in name.lower() for b in banned), \
            f"{name}: research_queue는 분석 순서만 정한다 - 사이징·판정 금지"
