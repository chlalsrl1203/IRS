"""
scripts/watchlist_ci.py(v3.69) 고정 테스트.

핵심 불변조건은 하나다 - **이 경로는 `ledger/`에 절대 쓰지 않는다.**
`recompute_gap_at_market_cap`은 오늘 날짜로 스탬프된 완전한 결과를 만들기 때문에,
그걸 저장하면 같은 티커 ledger가 2개가 되어 "종목당 1건" 규칙이 즉시 깨진다
(v3.32 WM/WCN/IDXX 중복이 CLAUDE.md 통계까지 오염시킨 사고와 같은 유형).
"""
import ast
import datetime
import glob
import json
import os
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts import watchlist_ci as W  # noqa: E402


# ── ① ledger 오염 금지 (최우선 불변조건) ────────────────────────────────
def test_no_write_path_into_ledger_dir():
    """
    소스를 AST로 훑어 ledger 디렉터리에 쓰는 경로가 없음을 고정한다.
    문서로만 둔 규칙이 무력화된 사례를 이 프로젝트는 이미 여러 번 겪었다.
    """
    src = (ROOT / "scripts" / "watchlist_ci.py").read_text(encoding="utf-8")
    tree = ast.parse(src)

    # save_ledger를 부르지 않는다
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            fn = node.func
            name = getattr(fn, "attr", None) or getattr(fn, "id", None)
            assert name != "save_ledger", "watchlist 경로가 save_ledger를 호출한다"

    # open(..., "w") 대상이 LEDGER_DIR을 향하지 않는다
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "open":
            mode = node.args[1].value if len(node.args) > 1 and isinstance(
                node.args[1], ast.Constant) else None
            if mode and "w" in str(mode):
                target = ast.dump(node.args[0])
                assert "LEDGER_DIR" not in target, "쓰기 대상이 ledger 디렉터리다"


def test_run_watchlist_never_touches_ledger_dir(tmp_path, monkeypatch):
    """실제 실행에서도 ledger/ 파일 목록이 그대로인지 확인한다."""
    before = sorted(glob.glob(str(ROOT / "ledger" / "*.json")))
    before_mtimes = {p: os.path.getmtime(p) for p in before}

    monkeypatch.setattr(W.ci, "fetch_market_cap_av", lambda t, k: 50_000_000_000)
    monkeypatch.setattr(W.ci, "AV_CALL_INTERVAL_SEC", 0)

    W.run_watchlist(["ACGL"], "2026-08-24", "fake-key", budget=1,
                    out_dir=str(tmp_path))

    after = sorted(glob.glob(str(ROOT / "ledger" / "*.json")))
    assert after == before, "ledger 파일 목록이 변했다"
    assert {p: os.path.getmtime(p) for p in after} == before_mtimes, \
        "ledger 파일이 수정됐다"


# ── ② 회전이 결정적이고 모든 종목을 덮는다 ──────────────────────────────
def test_rotation_is_deterministic_for_the_same_day():
    tickers = [f"T{i:02d}" for i in range(34)]
    day = datetime.date(2026, 8, 24)
    assert W.rotate(tickers, day, 18) == W.rotate(tickers, day, 18)


def test_rotation_covers_every_ticker_within_a_full_cycle():
    """
    상태 파일 없이도 어떤 종목이 영영 안 뽑히는 일이 없어야 한다 -
    그게 상태 기반 회전 대신 날짜 기반을 택한 이유다.
    """
    tickers = [f"T{i:02d}" for i in range(34)]
    seen = set()
    for d in range(1, 15):  # 2주면 한 바퀴 이상 돈다
        seen |= set(W.rotate(tickers, datetime.date(2026, 1, 1)
                             + datetime.timedelta(days=d - 1), 18))
    assert seen == set(tickers), f"14일 안에 안 뽑힌 종목: {set(tickers) - seen}"


def test_rotation_returns_all_when_budget_exceeds_list():
    tickers = ["A", "B", "C"]
    assert W.rotate(tickers, datetime.date(2026, 8, 24), 10) == tickers


def test_rotation_handles_empty_and_zero_budget():
    assert W.rotate([], datetime.date(2026, 8, 24), 5) == []
    assert W.rotate(["A"], datetime.date(2026, 8, 24), 0) == []


# ── ③ 시총 변경만으로 Realistic Growth가 움직이면 버그 ──────────────────
def test_market_cap_change_must_not_move_realistic_growth():
    """
    Realistic Growth는 재무 시계열에서만 나온다. 시총을 바꿨는데 이 값이
    움직이면 계산 경로 버그이므로 조용히 넘기지 않고 integrity_error로 드러낸다.
    """
    ledger_path = sorted(glob.glob(str(ROOT / "ledger" / "ACGL_*.json")))[-1]
    ledger = json.loads(pathlib.Path(ledger_path).read_text(encoding="utf-8"))

    row = W.track_existing("ACGL", ledger, ledger["inputs"]["market_cap"] * 1.4)
    assert "integrity_error" not in row, row.get("integrity_error")
    assert row["realistic_growth_then"] == pytest.approx(
        row["realistic_growth_now"], abs=1e-12)
    assert row["mode"] == "gap_decay"


def test_price_drop_widens_gap_the_value_trap_property():
    """
    주가가 빠지면 Gap은 반드시 벌어진다(Implied Growth만 내려가므로).
    v3.42가 TTD에서 실측한 가치함정의 수학적 원리 - 여기서도 성립해야 한다.
    """
    ledger_path = sorted(glob.glob(str(ROOT / "ledger" / "ACGL_*.json")))[-1]
    ledger = json.loads(pathlib.Path(ledger_path).read_text(encoding="utf-8"))

    down = W.track_existing("ACGL", ledger, ledger["inputs"]["market_cap"] * 0.7)
    up = W.track_existing("ACGL", ledger, ledger["inputs"]["market_cap"] * 1.3)
    assert down["gap_decay_pp"] > 0, "주가 하락인데 Gap이 안 벌어졌다"
    assert up["gap_decay_pp"] < 0, "주가 상승인데 Gap이 안 좁혀졌다"


# ── ④ watchlist.json 로딩 ───────────────────────────────────────────────
def test_watchlist_file_exists_and_seeds_from_ledger():
    tickers = W.load_watchlist(str(ROOT / "watchlist.json"))
    ledger_tickers = {json.loads(pathlib.Path(p).read_text(encoding="utf-8"))
                      ["meta"]["ticker"]
                      for p in glob.glob(str(ROOT / "ledger" / "*.json"))}
    assert set(tickers) == ledger_tickers, "초기 관심종목이 ledger 전수와 다르다"


def test_load_watchlist_dedupes_and_preserves_order(tmp_path):
    p = tmp_path / "wl.json"
    p.write_text(json.dumps({"tickers": ["b", "A", "B", "a", "", "  "]}),
                 encoding="utf-8")
    assert W.load_watchlist(str(p)) == ["B", "A"]


# ── ⑤ 리포트가 실패를 숨기지 않는다 ─────────────────────────────────────
def test_report_surfaces_integrity_errors_and_flips():
    rows = [
        {"ticker": "AAA", "mode": "gap_decay", "gap_now": 0.05,
         "judgment_now": "저평가 가능성", "judgment_then": "적정가/경계선",
         "judgment_flipped": True, "market_cap_change_pct": -0.3},
        {"ticker": "BBB", "mode": "gap_decay", "gap_now": 0.01,
         "judgment_now": "적정가/경계선", "integrity_error": "RG가 움직였다"},
        {"ticker": "CCC", "mode": "skipped", "error": "시가총액 미확보"},
    ]
    out = W.format_watchlist_section(rows, total_tickers=34)
    assert "계산 무결성 오류" in out
    assert "AAA" in out and "판정이 바뀐" in out
    assert "CCC" in out          # 제외된 종목도 드러난다
    assert "공식 판정이 아니다" in out


def test_report_is_quiet_when_nothing_notable():
    rows = [{"ticker": "AAA", "mode": "gap_decay", "gap_now": 0.01,
             "judgment_now": "적정가/경계선", "judgment_flipped": False,
             "market_cap_change_pct": 0.001}]
    out = W.format_watchlist_section(rows, total_tickers=34)
    assert "판정 변화·주목할 Gap 이동 없음" in out
    assert "🛑" not in out


# ── ⑥ 스크리너와 분리돼 있다 ────────────────────────────────────────────
def test_watchlist_does_not_reimplement_engine_functions():
    """
    새 밸류에이션 로직 0줄 - 기존 검증된 함수만 부른다.
    직접 Gap을 계산하는 산술이 들어오면 두 계산이 어긋나는 버그의 시작이다.
    """
    src = (ROOT / "scripts" / "watchlist_ci.py").read_text(encoding="utf-8")
    assert "recompute_gap_at_market_cap" in src
    assert "deep_screen" in src
    # Gap을 직접 빼서 만드는 코드가 없어야 한다(변화량 비교는 예외 - prior 대비)
    assert "realistic_growth -" not in src
    assert "- implied_growth" not in src
