"""
engine/monitor_state.py + scripts/daily_monitor_ci.py 불변조건 (v3.64, 2026-08-23).

이 감시는 무인으로 매일 돌기 때문에 회귀가 나도 아무도 즉시 못 알아챈다 -
정확히 그래서 "조용히 안전해 보이는" 실패 경로를 테스트로 고정한다.
"""
import importlib.util
import json
import os
import pathlib
from datetime import date

import pytest

from engine.monitor_state import (
    CLOSED_VERDICTS, DEFAULT_RECHECK_DAYS, OPEN_VERDICTS, VERDICTS,
    build_acknowledgement, is_open, item_key, latest_verdict, triage,
)

ROOT = pathlib.Path(__file__).resolve().parent.parent


def _load_runner():
    path = ROOT / "scripts" / "daily_monitor_ci.py"
    spec = importlib.util.spec_from_file_location("daily_monitor_ci", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


RUNNER = _load_runner()
TODAY = date(2026, 8, 23)


def _scan(ticker, status, past=(), pending=(), text="조건"):
    return {
        "ticker": ticker, "analyzed_at": "2026-08-01", "status": status,
        "past_due": [{"date": d, "raw": str(d), "context": text} for d in past],
        "pending": [{"date": d, "raw": str(d), "context": text} for d in pending],
        "conditions_text": text,
    }


def _acks(entries):
    out = {}
    for e in entries:
        out.setdefault(e["item_key"], []).append(e)
    return {"_missing": False, "entries": out}


# ── 핵심: 자동 판정 금지 ──────────────────────────────────────────────
def test_module_never_decides_whether_a_condition_fired():
    """
    v3.42가 확립한 원칙 - 정규식은 트리거 날짜와 서술적 날짜를 구분하지
    못한다(TCOM 소송 집단기간이 실제 오탐이었다). 이 모듈에 '발동 판정'
    함수가 생기면 그 원칙이 깨진 것이다.
    """
    import engine.monitor_state as ms
    banned = ("decide", "judge", "evaluate_trigger", "auto_resolve",
              "determine_triggered")
    public = [n for n in dir(ms) if not n.startswith("_")]
    for name in public:
        assert not any(b in name.lower() for b in banned), (
            f"{name}: 이 모듈은 '확인했는가'만 추적하고 '발동했는가'는 "
            f"판정하지 않는다")


def test_verdicts_are_recorded_not_computed():
    """verdict는 사람이 넣는 값이다 - 근거(note) 없으면 거부한다."""
    with pytest.raises(ValueError, match="note는 필수"):
        build_acknowledgement("AAA", "2026-01-01", "NOT_TRIGGERED",
                              "2026-01-02", note="   ")
    with pytest.raises(ValueError, match="알 수 없는 verdict"):
        build_acknowledgement("AAA", "2026-01-01", "PROBABLY_FINE",
                              "2026-01-02", note="x")


# ── 핵심: 확인 못한 것을 확인된 것으로 닫지 않는다 ──────────────────
def test_inconclusive_resurfaces_and_is_not_treated_as_closed():
    """
    2026-08-13 MNDY 실사례 - 조건이 지정한 코호트별 NDR을 회사가 공개하지
    않아 판정 불가였다. 이걸 '확인 완료'로 닫으면 영영 안 돌아온다.
    (is_insurer/sbc_cross_check의 '데이터 없음 != 안전' 원칙의 시간축 버전)
    """
    assert "INCONCLUSIVE" in OPEN_VERDICTS
    assert "INCONCLUSIVE" not in CLOSED_VERDICTS
    acked_on = date(2026, 8, 13)
    e = build_acknowledgement("MNDY", "2026-08-10", "INCONCLUSIVE",
                              acked_on.isoformat(), note="코호트별 NDR 미공개")
    due = date.fromordinal(acked_on.toordinal() + DEFAULT_RECHECK_DAYS)
    # 재확인 기한 전날까지는 조용하다가
    assert is_open(e, date.fromordinal(due.toordinal() - 1)) is False
    # 기한 당일부터 다시 떠오른다
    assert is_open(e, due) is True


def test_explicit_recheck_after_overrides_default():
    e = build_acknowledgement("AAA", "2026-01-01", "INCONCLUSIVE",
                              "2026-01-02", note="n", recheck_after="2026-03-01")
    assert is_open(e, date(2026, 2, 28)) is False
    assert is_open(e, date(2026, 3, 1)) is True


def test_unknown_verdict_stays_open_rather_than_silently_closing():
    """어휘가 늘었는데 is_open을 안 고치면 조용히 닫히는 것보다 시끄러운 게 낫다."""
    assert is_open({"verdict": "SOMETHING_NEW"}, TODAY) is True


# ── 핵심: 알림 피로 방지가 실제로 작동하는가 ────────────────────────
def test_acknowledged_item_does_not_realert():
    """
    이 감시를 만든 이유 그 자체 - 08-13에 6건을 실제로 검증했는데 상태를
    기록할 곳이 없어 매일 같은 6건이 다시 뜨면 사람이 전체를 무시하게 된다.
    """
    scans = [_scan("SE", "past_due", past=[date(2026, 8, 11)])]
    acks = _acks([build_acknowledgement(
        "SE", "2026-08-11", "NOT_TRIGGERED", "2026-08-13", note="Shopee EBITDA +12.2%")])
    t = triage(scans, acks, TODAY)
    assert t["needs_review"] == []
    assert len(t["acknowledged"]) == 1


def test_unacknowledged_item_alerts():
    scans = [_scan("PDD", "past_due", past=[date(2026, 8, 28)])]
    t = triage(scans, {"_missing": False, "entries": {}}, date(2026, 8, 28))
    assert len(t["needs_review"]) == 1
    assert t["needs_review"][0]["ticker"] == "PDD"
    assert "미확인" in t["needs_review"][0]["reason"]


def test_triggered_items_stay_visible_but_are_not_new_alerts():
    """TTD - 이미 조치(비중 4.80%->2.70%)했으므로 재알림은 아니되 사라지면 안 된다."""
    scans = [_scan("TTD", "past_due", past=[date(2026, 8, 6)])]
    acks = _acks([build_acknowledgement(
        "TTD", "2026-08-06", "TRIGGERED", "2026-08-13", note="4개 중 3개 발동")])
    t = triage(scans, acks, TODAY)
    assert t["needs_review"] == []
    assert len(t["triggered"]) == 1


# ── 핵심: 데이터 없음을 안전으로 오독하지 않는다 ─────────────────────
def test_missing_state_file_is_flagged_not_silently_assumed_clean():
    t = triage([_scan("X", "past_due", past=[date(2026, 8, 1)])],
               {"_missing": True, "entries": {}}, TODAY)
    assert t["state_file_missing"] is True
    assert len(t["needs_review"]) == 1  # 기록이 없으면 전부 미확인이다


def test_no_conditions_is_reported_as_absence_of_basis_not_safety():
    """반증조건 미기재 20종목을 '안전'으로 읽으면 안 된다(v3.24 소급작성 금지 원칙)."""
    result = {
        "n_ledgers": 1,
        "falsification": triage([_scan("Z", "no_conditions")],
                                {"_missing": False, "entries": {}}, TODAY),
        "predictions": {"due": [], "pending": 0, "resolved": 0, "dir_missing": False},
    }
    section = RUNNER.format_monitor_section(result)
    assert "감시근거 없음" in section
    assert "안전" in section  # "'안전'이 아니라" 문구로 명시돼야 한다


# ── 실제 저장소 상태 회귀 ────────────────────────────────────────────
def test_seeded_state_matches_recorded_2026_08_13_verdicts():
    """
    monitor/acknowledgements.json은 08-13 리포트에서 전사한 것이다.
    누군가 verdict를 나중에 고쳐 쓰면(사후합리화) 이 테스트가 잡는다.
    """
    ack_path = ROOT / "monitor" / "acknowledgements.json"
    if not ack_path.exists():
        pytest.skip("확인 기록 파일 없음")
    data = json.loads(ack_path.read_text(encoding="utf-8"))
    by_key = {a["item_key"]: a for a in data["acknowledgements"]}
    expected = {
        "DUOL:2026-08-05": "NOT_TRIGGERED",
        "MNDY:2026-08-10": "INCONCLUSIVE",
        "PGR:2026-08-04": "NOT_TRIGGERED",
        "SE:2026-08-11": "NOT_TRIGGERED",
        "TCOM:2024-04-30": "NOT_A_TRIGGER_DATE",
        "TCOM:2026-01-13": "NOT_A_TRIGGER_DATE",
        "TTD:2026-08-06": "TRIGGERED",
    }
    for key, verdict in expected.items():
        assert key in by_key, f"{key} 확인 기록이 사라졌다"
        assert by_key[key]["verdict"] == verdict, (
            f"{key}: 기록된 판정이 {verdict}에서 "
            f"{by_key[key]['verdict']}로 바뀌었다 - 사후 수정 금지")
        assert by_key[key]["note"].strip(), f"{key}: 근거가 비었다"


def test_real_repo_today_has_no_unreviewed_backlog():
    """
    현재 저장소 기준 미확인 잔여가 0이어야 한다 - 08-13 검증분이 전부
    기록됐다는 뜻. 새 반증조건 기한이 도래하면 이 테스트가 실패하는 게
    아니라(그건 정상) needs_review에 잡혀 알림이 나간다.
    """
    result = RUNNER.run_monitor(TODAY, ledger_dir=str(ROOT / "ledger"),
                                ack_path=str(ROOT / "monitor" / "acknowledgements.json"),
                                predictions_dir=str(ROOT / "predictions"))
    assert result["n_ledgers"] == 36  # 2026-09-01/02: CROX·SIGI 정식분석 추가(34->36)
    assert result["falsification"]["needs_review"] == []
    assert result["action_required"] is False


def test_ledger_dedup_uses_latest_per_ticker():
    """v3.32 중복 ledger 사고 - 티커당 1건만 세야 한다."""
    ledgers = RUNNER._iter_ledgers(str(ROOT / "ledger"))
    tickers = [d["meta"]["ticker"] for d in ledgers]
    assert len(tickers) == len(set(tickers))


def test_runner_writes_nothing_into_ledger_or_state():
    """
    CI는 ledger와 확인기록을 **읽기만** 한다. 자동 커밋 사고를 원천 차단하는
    설계이므로 쓰기 경로가 생기면 즉시 잡아야 한다.
    """
    import ast
    src = (ROOT / "scripts" / "daily_monitor_ci.py").read_text(encoding="utf-8")
    tree = ast.parse(src)

    # 파괴적 **파일시스템** 호출이 없어야 한다. 모듈을 특정한다 - 초판은
    # 메서드명만 봐서 `ctx.replace("\n"," ")`(문자열 정리)를 os.replace로
    # 오검출했다. 이 프로젝트가 반복 확인한 "측정 도구를 먼저 의심하라"의 사례.
    banned = {"remove", "unlink", "rmtree", "rename", "replace", "rmdir"}
    fs_modules = {"os", "shutil", "pathlib", "Path"}
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)):
            continue
        if node.func.attr not in banned:
            continue
        owner = node.func.value
        owner_name = getattr(owner, "id", None) or getattr(owner, "attr", None)
        assert owner_name not in fs_modules, (
            f"파괴적 파일시스템 호출 {owner_name}.{node.func.attr}() "
            f"발견 (line {node.lineno})")

    # open(...)은 결과 JSON 저장 1곳(/tmp)만 허용한다. ledger/확인기록 경로에
    # 쓰기가 생기면 잡는다.
    write_opens = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "open":
            mode = ""
            if len(node.args) > 1 and isinstance(node.args[1], ast.Constant):
                mode = node.args[1].value
            for kw in node.keywords:
                if kw.arg == "mode" and isinstance(kw.value, ast.Constant):
                    mode = kw.value.value
            if "w" in mode or "a" in mode:
                write_opens.append(node.lineno)
    assert len(write_opens) == 1, (
        f"쓰기용 open()이 {len(write_opens)}곳 - /tmp 결과저장 1곳만 허용 "
        f"(lines {write_opens})")
    assert "out_path" in src.split("\n")[write_opens[0] - 1], (
        "허용된 유일한 쓰기는 /tmp 결과 저장이어야 한다")


def test_item_key_is_stable_against_condition_text_edits():
    """원문 오탈자를 고쳐도 확인 기록이 유실되면 안 된다."""
    assert item_key("AAA", "2026-01-01") == item_key("AAA", date(2026, 1, 1))


def test_latest_verdict_returns_most_recent_entry():
    e1 = build_acknowledgement("A", "2026-01-01", "INCONCLUSIVE", "2026-01-02", note="1")
    e2 = build_acknowledgement("A", "2026-01-01", "NOT_TRIGGERED", "2026-02-02", note="2")
    acks = _acks([e1, e2])
    assert latest_verdict(acks, "A:2026-01-01")["verdict"] == "NOT_TRIGGERED"


def test_all_verdicts_documented():
    assert set(VERDICTS) == CLOSED_VERDICTS | OPEN_VERDICTS
    for v, desc in VERDICTS.items():
        assert desc.strip(), f"{v}: 설명이 비었다"
