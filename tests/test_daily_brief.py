"""
`scripts/daily_brief.py` 고정 테스트 (2026-08-28).

이 브리핑이 실제로 쓰이려면 지켜져야 하는 것만 고정한다:
  ① 네트워크 없이 항상 생성된다(외부 API가 죽어도 나와야 한다)
  ② 매수리스트를 **금액**까지 낸다(비중만으로는 주문을 못 낸다)
  ③ 계좌 구분이 사라지지 않는다(ISA로는 미국 개별주를 못 산다)
  ④ 없는 배분 규칙을 지어내지 않는다(KRX ETF에 비중을 붙이지 않는다)
  ⑤ 성과 미검증 사실이 매수표와 같은 화면에 남는다
"""
import json
import os
import pathlib
import sys
from datetime import date

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts import daily_brief as B  # noqa: E402


@pytest.fixture
def text():
    os.chdir(ROOT)
    t, _ = B.build(date(2026, 8, 28), 10_000_000, 8)
    return t


# ── ① 네트워크 의존 0 ───────────────────────────────────────────────────
def test_no_network_calls_in_generation(monkeypatch):
    """
    브리핑 생성 경로가 소켓을 열면 실패한다. 외부 API 장애 때 조용히 빈
    결과가 나오던 이력(v3.68)을 브리핑까지 전파시키지 않기 위한 고정이다.
    """
    import socket

    def boom(*a, **k):  # noqa: ANN001
        raise AssertionError("브리핑 생성이 네트워크를 탔다")

    monkeypatch.setattr(socket.socket, "connect", boom)
    monkeypatch.setattr(socket, "create_connection", boom)
    os.chdir(ROOT)
    t, _ = B.build(date(2026, 8, 28), 10_000_000, 8)
    assert "오늘의 실행 브리핑" in t


def test_generation_does_not_import_requests_at_module_level():
    """`requests`는 게시(--post)에서만 쓴다 — 생성 경로에 있으면 안 된다."""
    src = (ROOT / "scripts" / "daily_brief.py").read_text(encoding="utf-8")
    head = src.split("def post(")[0]
    assert "import requests" not in head


# ── ② 금액까지 낸다 ─────────────────────────────────────────────────────
def _top_weight_amount(capital):
    """`_latest('buylist_')`가 실제로 가리키는 파일에서 최상위 비중을 읽어
    기대 금액을 계산한다. 특정 buylist 스냅샷의 최상위 비중(예: 구
    buylist_2026-08-03.json의 GEN 18.00%)을 하드코딩하면, 그 뒤에 새
    buylist_<날짜>.json이 나올 때마다(2026-09-06 발행 등) 테스트가 매번
    깨진다 - 이 테스트가 고정해야 할 불변조건은 '금액으로 환산됐는가'이지
    '어느 스냅샷이 최신인가'가 아니다."""
    path = B._latest("buylist_")
    data = B.load_json(path)
    rows = data if isinstance(data, list) else data.get("positions") or []
    top_w = max(r["weight_final"] for r in rows)
    return B.won(capital * top_w)


def test_buylist_renders_actual_amounts(text):
    assert _top_weight_amount(10_000_000) in text, "비중을 금액으로 환산하지 못했다"
    assert "10,000,000원" in text
    assert "**합계** | **100.00%**" in text


def test_amounts_scale_with_capital():
    os.chdir(ROOT)
    a, _ = B.build(date(2026, 8, 28), 10_000_000, 8)
    b, _ = B.build(date(2026, 8, 28), 20_000_000, 8)
    assert _top_weight_amount(10_000_000) in a
    assert _top_weight_amount(20_000_000) in b


def test_share_count_is_not_invented(text):
    """실시간 시세를 보지 않으므로 주수를 계산하면 안 된다."""
    assert "주수는 여기서 계산하지 않는다" in text


# ── ③ 계좌 구분 ─────────────────────────────────────────────────────────
def test_account_separation_is_explicit(text):
    assert "해외주식 계좌" in text and "ISA 계좌" in text
    assert "ISA 계좌로는 이 종목들을 매수할 수 없다" in text


# ── ④ 없는 규칙을 지어내지 않는다 ───────────────────────────────────────
def test_krx_section_has_no_invented_weights(text):
    isa = text.split("ISA 계좌 — 국내 상장 ETF 후보")[1]
    assert "비중 배분 규칙이 없다" in isa
    # ISA 표에 '금액' 열이 생기면 배분 규칙을 지어낸 것이다
    header = [ln for ln in isa.splitlines() if ln.startswith("| 순위")][0]
    assert "금액" not in header and "비중" not in header


def test_low_breakeven_is_not_stated_as_buy_signal(text):
    assert "시장요구성장이 낮다 = 사라**가 아니다" in text


# ── ⑤ 미검증 사실이 같은 화면에 남는다 ──────────────────────────────────
def test_performance_evidence_limits_are_disclosed(text):
    """
    ⚠️ 원래 이 테스트는 "실현 수익률을 한 번도 관측한 적이 없다"는 **문구**를
    검사했다. 2026-08-29에 3개 T0 백테스트가 나오면서 그 문구가 사실이
    아니게 됐고, 브리핑이 매일 낡은 주장을 반복하는 상태였다 - 테스트가
    오히려 그 낡은 주장을 고정하고 있었다.

    검사 대상을 **문구**에서 **의도**로 옮긴다: 성과 근거의 한계가 매수표와
    같은 화면에 반드시 남아야 한다. 검증이 없으면 "없다"고, 있으면 "이것으로
    시장을 이긴다고 말할 수 없다"고 남는다.
    """
    assert "성적표" in text
    assert ("'시장을 이긴다'는 근거가 아니다" in text
            or "실현 수익률 검증 없음" in text)


def test_scorecard_absent_says_so_rather_than_implying_verified(monkeypatch, tmp_path):
    """성적표 파일이 없으면 없는 검증을 있다고 하지 않는다."""
    monkeypatch.setattr(B, "REPORTS", str(tmp_path))
    out = "\n".join(B.section_scorecard())
    assert "실현 수익률 검증 없음" in out


def test_scorecard_reports_replication_counts(monkeypatch, tmp_path):
    d = tmp_path / "pit_backtest"
    d.mkdir(parents=True)
    (d / "pit_multi_t0_summary.json").write_text(json.dumps([
        {"t0": "2021-06-30", "metrics": {
            "min_pct": {"flagged": 1, "not_flagged": -5, "flagged_better": True},
            "median_pct": {"flagged": 1, "not_flagged": 5, "flagged_better": False}}},
        {"t0": "2023-06-30", "metrics": {
            "min_pct": {"flagged": 1, "not_flagged": -5, "flagged_better": True},
            "median_pct": {"flagged": 1, "not_flagged": 5, "flagged_better": False}}},
    ]), encoding="utf-8")
    monkeypatch.setattr(B, "REPORTS", str(tmp_path))
    out = "\n".join(B.section_scorecard())
    assert "최저 종목**: 2/2" in out          # 3/3 재현 축
    assert "중앙값**: 0/2" in out             # 재현 실패 축도 숨기지 않는다
    assert "뭘 피하라" in out


def test_deep_screen_candidates_are_flagged_as_not_official(monkeypatch, tmp_path):
    """심층 스크리닝 후보가 나올 때 '정식 분석 아님'이 반드시 붙어야 한다."""
    os.chdir(ROOT)
    d = tmp_path / "reports" / "deep_screen"
    d.mkdir(parents=True)
    (d / "ZZZ_2026-08-28.json").write_text(json.dumps(
        {"ticker": "ZZZ", "expectation_gap": 0.09, "judgment": "저평가 가능성"}),
        encoding="utf-8")
    monkeypatch.setattr(B, "REPORTS", str(tmp_path / "reports"))
    out = B.section_new_candidates(date(2026, 8, 28))
    body = "\n".join(out)
    assert "ZZZ" in body
    assert "정식 분석이 아니다" in body


# ── Confidence를 확률처럼 노출하지 않는다(P0-1, 2026-08-29) ───────────────
def test_confidence_column_is_not_labeled_as_probability(text):
    """
    confidence_score()는 스스로 '확률이 아니다·실현결과로 보정된 적이 없다'고
    말하는데, 표 열 이름이 '신뢰도'였던 것은 그 경고를 화면에서 위반하고
    있었다 — 이름을 바꾸고 옆에 근거를 남긴다.
    """
    overseas = text.split("해외주식 계좌 — 매수 실행표")[1]
    assert "| 신뢰도 |" not in overseas
    assert "모델점수" in overseas
    assert "확률이 아니다" in overseas
    assert "검증(calibration)된" in overseas


# ── 파일 선택 사고 재발 방지 ────────────────────────────────────────────
def test_latest_prefix_does_not_match_longer_names(tmp_path):
    """
    `buylist_`가 `buylist_boundary_review_...`까지 잡아 공식 매수리스트 대신
    경계검토 리포트를 골랐던 실제 사고의 회귀 테스트.
    """
    (tmp_path / "buylist_2026-08-03.json").write_text("[]", encoding="utf-8")
    (tmp_path / "buylist_boundary_review_2026-08-16.json").write_text("[]",
                                                                      encoding="utf-8")
    got = B._latest("buylist_", str(tmp_path))
    assert os.path.basename(got) == "buylist_2026-08-03.json"


def test_missing_inputs_degrade_gracefully(monkeypatch, tmp_path):
    """산출물이 하나도 없어도 예외 없이 브리핑이 나와야 한다."""
    os.chdir(ROOT)
    monkeypatch.setattr(B, "REPORTS", str(tmp_path))
    out = "\n".join(B.section_overseas(1_000_000) + B.section_isa(5))
    assert "찾지 못했다" in out


# ── 감시 로직을 다시 구현하지 않았다 ────────────────────────────────────
def test_monitor_logic_is_reused_not_reimplemented():
    src = (ROOT / "scripts" / "daily_brief.py").read_text(encoding="utf-8")
    assert "from scripts.daily_monitor_ci import run_monitor" in src
    assert "scan_falsification_conditions" not in src, \
        "감시 로직을 브리핑에서 다시 구현했다 — 두 계산이 어긋난다"


# ── 주간 대규모 스크리닝 배선(2026-08-29) ────────────────────────────────
def test_broad_screen_section_appears_in_brief(text):
    """
    v3.72에서 대규모 스크리닝을 배선했으나 daily_brief가 그 결과를 한 번도
    읽지 않았다 - "데이터는 있는데 결정 경로에 배선 안 됨" 패턴의 재발.
    """
    assert "주간 대규모 스크리닝" in text


def test_broad_screen_missing_file_is_stated_not_silent(monkeypatch, tmp_path):
    monkeypatch.setattr(B, "REPORTS", str(tmp_path))
    out = "\n".join(B.section_broad_screen())
    assert "아직 결과 파일이 없다" in out


def test_broad_screen_renders_passed_tickers(monkeypatch, tmp_path):
    d = tmp_path / "broad_screen"
    d.mkdir(parents=True)
    (d / "broad_screen_2026-08-29.json").write_text(json.dumps({
        "universe_total": 10391, "scored": 4000,
        "passed_tickers": [
            {"ticker": "AAA", "tier": "S", "expectation_gap_est": 0.20,
             "market_cap": 1e10},
            {"ticker": "BBB", "tier": "A", "expectation_gap_est": 0.09,
             "market_cap": 5e9},
        ]}), encoding="utf-8")
    monkeypatch.setattr(B, "REPORTS", str(tmp_path))
    out = "\n".join(B.section_broad_screen())
    assert "AAA" in out and "BBB" in out
    assert out.index("AAA") < out.index("BBB")      # Gap 내림차순
    assert "정식 분석이 아니다" in out


def test_broad_screen_states_downside_framing(monkeypatch, tmp_path):
    """백테스트가 실측한 '하방 방어가 재현성 높다'는 사실이 표시돼야 한다."""
    d = tmp_path / "broad_screen"
    d.mkdir(parents=True)
    (d / "broad_screen_2026-08-29.json").write_text(json.dumps({
        "universe_total": 1, "scored": 1,
        "passed_tickers": [{"ticker": "AAA", "tier": "S",
                            "expectation_gap_est": 0.2, "market_cap": 1e9}]}),
        encoding="utf-8")
    monkeypatch.setattr(B, "REPORTS", str(tmp_path))
    out = "\n".join(B.section_broad_screen())
    assert "하방 방어" in out and "제외 근거" in out


# ── 연구 우선순위 큐 배선(2026-08-30) — 스크리닝↔매수리스트 연결 ────────────
def test_research_queue_section_appears_in_brief(text):
    """
    스크리닝 통과 목록과 매수리스트 사이에 아무 연결이 없던 것을 잇는 칸이다.
    브리핑에 안 나오면 큐가 결정 경로에 도달하지 않는다.
    """
    assert "다음에 분석할 종목" in text


def test_research_queue_missing_file_is_stated(monkeypatch, tmp_path):
    monkeypatch.setattr(B, "REPORTS", str(tmp_path))
    out = "\n".join(B.section_research_queue())
    assert "아직 큐 파일이 없다" in out


def test_research_queue_is_not_presented_as_a_buy_instruction(monkeypatch, tmp_path):
    """
    큐는 연구 **순서**이지 매수 지시가 아니다 - 정식분석·정성조사를 거쳐야
    매수리스트에 들어간다(run_analysis가 주관적 입력 없이는 실행을 거부한다).
    """
    (tmp_path / "research_queue.json").write_text(json.dumps({
        "latest_run": "2026-08-30",
        "counts": {"total": 2, "QUEUED": 2},
        "persistence": {"n_runs": 1, "discriminating": False},
        "next_to_research": [
            {"ticker": "CROX", "tier": "S", "latest_gap": 0.2397,
             "market_cap": 4.8e9, "priority_reason": "검증범위 안 · 미분석"},
        ],
    }), encoding="utf-8")
    monkeypatch.setattr(B, "REPORTS", str(tmp_path))
    out = "\n".join(B.section_research_queue())
    assert "CROX" in out
    assert "매수 지시가 아니라 연구 순서" in out
    # 비중·금액 열이 생기면 사이징을 지어낸 것이다
    header = [ln for ln in out.splitlines() if ln.startswith("| # |")][0]
    assert "비중" not in header and "금액" not in header


def test_research_queue_warns_when_persistence_not_discriminating(monkeypatch, tmp_path):
    (tmp_path / "research_queue.json").write_text(json.dumps({
        "latest_run": "2026-08-30", "counts": {"total": 1, "QUEUED": 1},
        "persistence": {"n_runs": 1, "discriminating": False},
        "next_to_research": [{"ticker": "X", "tier": "S", "latest_gap": 0.1,
                              "market_cap": 1e9, "priority_reason": "x"}],
    }), encoding="utf-8")
    monkeypatch.setattr(B, "REPORTS", str(tmp_path))
    out = "\n".join(B.section_research_queue())
    assert "아직 아무것도 구분하지 못한다" in out


# ── 실제 보유 vs 시스템 목표 ────────────────────────────────────────────
def test_reconciliation_section_appears_in_brief(text):
    assert "실제 보유 vs 시스템 목표" in text


def test_reconciliation_lists_every_held_ticker(text):
    """
    «판정 불가라 표에서 뺀다»가 가장 나쁜 처리다 - 판정 불가가 «문제 없음»으로
    보이게 된다(is_insurer·sbc_cross_check·holdings_overlap이 매번 경계해온
    «데이터 없음을 안전으로 오독» 원칙). 보유 종목은 하나도 빠짐없이 표에
    올라와야 한다.
    """
    os.chdir(ROOT)
    holdings = B.load_json(B.HOLDINGS_PATH)
    if not holdings:
        pytest.skip("holdings.json 없음")
    section = "\n".join(B.section_reconciliation())
    for p in holdings["positions"]:
        assert f"**{p['ticker']}**" in section, p["ticker"]


def test_reconciliation_has_no_buy_or_sell_column():
    """
    차이를 «조치»로 번역하는 순간, 실현수익률 관측이 0건인 신호가 곧바로
    자본배분이 된다 - engine/portfolio.py(v3.82)·engine/thesis.py(v3.48)가
    구조로 못박은 것과 같은 경계다.
    """
    os.chdir(ROOT)
    section = "\n".join(B.section_reconciliation())
    header = next(l for l in section.splitlines() if l.startswith("| 종목 |"))
    for banned in ("매도", "매수", "조치", "액션", "추천"):
        assert banned not in header, header
    assert "청산하라»가 아니다" in section


def test_reconciliation_missing_holdings_degrades_gracefully(monkeypatch, tmp_path):
    os.chdir(ROOT)
    monkeypatch.setattr(B, "HOLDINGS_PATH", str(tmp_path / "nope.json"))
    out = "\n".join(B.section_reconciliation())
    assert "찾지 못해" in out


def test_reconciliation_never_writes_to_holdings_or_ledger():
    """보유 상태는 사람이 유지한다(v3.64 «확인은 사람의 행위»)."""
    os.chdir(ROOT)
    hp = ROOT / B.HOLDINGS_PATH
    before = (os.path.getmtime(hp), hp.read_bytes())
    led_before = {p: os.path.getmtime(p)
                  for p in sorted((ROOT / "ledger").glob("*.json"))}
    B.section_reconciliation()
    assert (os.path.getmtime(hp), hp.read_bytes()) == before
    assert {p: os.path.getmtime(p)
            for p in sorted((ROOT / "ledger").glob("*.json"))} == led_before


def test_reconciliation_reuses_pipeline_exclusion_reasons():
    """
    «왜 목표에 없는가»를 다시 계산하지 않는다 - 파이프라인 진단 리포트가 이미
    갖고 있는 사유를 그대로 읽는다(중복 구현이 두 계산을 어긋나게 만든다).
    """
    os.chdir(ROOT)
    diag_path = B._latest("portfolio_pipeline_")
    if not diag_path:
        pytest.skip("파이프라인 진단 리포트 없음")
    diag = B.load_json(diag_path)
    section = "\n".join(B.section_reconciliation())
    holdings = B.load_json(B.HOLDINGS_PATH)
    held = {p["ticker"] for p in holdings["positions"]}
    excluded_and_held = [r["ticker"] for r in diag.get("stage1_excluded", [])
                         if r["ticker"] in held]
    for t in excluded_and_held:
        line = next(l for l in section.splitlines() if l.startswith(f"| **{t}**"))
        assert "G1" in line or "G2" in line or "G3" in line, line


# ── ⑥ thesis 반증조건 check_by 기한 (2026-09-18 배선) ────────────────────
def _thesis_dir_with(tmp_path, check_by, ticker="ZZZ"):
    """check_by 하나만 가진 최소 thesis 레코드를 tmp에 만든다."""
    d = tmp_path / "thesis"
    d.mkdir()
    (d / f"{ticker}_2026-01-01.json").write_text(json.dumps({
        "thesis": {
            "ticker": ticker,
            "thesis_id": f"{ticker}_2026-01-01",
            "invalidation_conditions": [
                {"condition": "합성 테스트 조건", "check_by": check_by,
                 "triggered": False},
                {"condition": "날짜 없는 상시감시", "check_by": None,
                 "triggered": False},
            ],
        },
        "decisions": [], "evidence": [],
    }, ensure_ascii=False), encoding="utf-8")
    return str(d)


def test_due_thesis_checkpoint_reaches_the_brief_and_counts(tmp_path, monkeypatch):
    """
    기한이 도래한 thesis 조건이 브리핑 본문에 뜨고 `n_need`에도 들어가야 한다.
    `n_need`는 `action_required`로 이어져 이슈 제목 긴급도를 올린다 - 본문에만
    뜨고 카운트에서 빠지면 조용한 제목에 묻힌다.
    """
    os.chdir(ROOT)
    from scripts import daily_monitor_ci as M

    today = date(2026, 6, 1)
    tdir = _thesis_dir_with(tmp_path, "2026-05-01")  # 31일 경과
    monkeypatch.setattr(B, "run_monitor",
                        lambda t: M.run_monitor(t, thesis_dir=tdir))
    lines, n_need = B.section_today(today)
    text = "\n".join(lines)

    assert "ZZZ" in text and "2026-05-01" in text
    assert "합성 테스트 조건" in text
    assert n_need >= 1


def test_brief_never_claims_a_thesis_condition_fired(tmp_path, monkeypatch):
    """
    «기한이 됐다»와 «조건이 맞았다»는 다르다 - v3.42가 확립한 원칙
    (정규식은 트리거 날짜와 서술적 날짜를 구분 못 한다)의 thesis판.
    브리핑은 판정 어휘를 쓰지 않고, 판단 경로를 사람에게 되돌린다.
    """
    os.chdir(ROOT)
    from scripts import daily_monitor_ci as M

    tdir = _thesis_dir_with(tmp_path, "2026-05-01")
    monkeypatch.setattr(B, "run_monitor",
                        lambda t: M.run_monitor(t, thesis_dir=tdir))
    text = "\n".join(B.section_today(date(2026, 6, 1))[0])

    assert "기한이 됐다는 뜻이지 조건이 맞았다는 뜻이 아니다" in text
    assert "mark_invalidation_triggered" in text
    for word in ("반증 확정", "발동 확정", "논거 무효"):
        assert word not in text


def test_zero_due_does_not_read_as_nothing_to_watch(tmp_path, monkeypatch):
    """
    현재 thesis 조건 21건 중 17건이 `check_by=None`(사건기반 상시감시)이다.
    «기한 도래 0건»만 보이면 «볼 게 없다»로 읽힌다 - 이 프로젝트가 반복
    경계해온 «데이터 없음을 안전으로 오독»의 같은 형태다.
    """
    os.chdir(ROOT)
    from scripts import daily_monitor_ci as M

    tdir = _thesis_dir_with(tmp_path, "2027-12-31")  # 도래·임박 둘 다 아님
    monkeypatch.setattr(B, "run_monitor",
                        lambda t: M.run_monitor(t, thesis_dir=tdir))
    lines, n_need = B.section_today(date(2026, 6, 1))
    text = "\n".join(lines)

    assert n_need == 0
    assert "날짜없는 상시감시 1건" in text
    assert "기한 0건이 '볼 게 없다'는 뜻은 아니다" in text


def test_brief_does_not_use_the_network_bound_sec_enrichment():
    """
    ⚠️ 브리핑의 핵심 불변조건은 «네트워크 의존 0»이다. thesis 체크포인트는
    `due_conditions()`(순수 날짜 산술)만 써야 하고, SEC를 조회하는
    `enrich_with_sec_freshness()`를 끌어들이면 그 하나 때문에 브리핑 전체가
    외부 API 장애에 묶인다.

    ⚠️ 단순 문자열 검색으로 막지 않는다 - 그러면 «왜 안 쓰는가»를 설명하는
    주석까지 위반으로 잡혀, 판단 근거를 코드에서 지우는 쪽으로 압력이 생긴다.
    실제로 **호출·import 하는지**를 AST로 확인한다.
    """
    import ast
    import inspect

    from scripts import daily_monitor_ci as M

    banned = "enrich_with_sec_freshness"
    for mod in (B, M):
        tree = ast.parse(inspect.getsource(mod))
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id == banned:
                raise AssertionError(f"{mod.__name__}가 {banned}를 참조한다")
            if isinstance(node, ast.Attribute) and node.attr == banned:
                raise AssertionError(f"{mod.__name__}가 {banned}를 참조한다")
            if isinstance(node, ast.ImportFrom):
                names = {a.name for a in node.names}
                assert banned not in names, f"{mod.__name__}가 {banned}를 import한다"


def test_brief_does_not_claim_a_thesis_condition_total(tmp_path, monkeypatch):
    """
    `due_conditions()`는 도래·임박·날짜없음 세 갈래만 돌려주고 **경고창 밖의
    미래 기한은 어느 갈래에도 없다.** 세 갈래를 더해 «총 N건»이라 쓰면 실제보다
    적은 수가 총계로 찍힌다(실측: 저장소 thesis 조건 23건, 세 갈래 합 19건).
    여기서는 조건 2건 중 1건만 세 갈래에 들어가는 상황을 만들어 고정한다.
    """
    os.chdir(ROOT)
    from scripts import daily_monitor_ci as M

    tdir = _thesis_dir_with(tmp_path, "2027-12-31")  # 창 밖 미래 + 날짜없음 1건
    monkeypatch.setattr(B, "run_monitor",
                        lambda t: M.run_monitor(t, thesis_dir=tdir))
    text = "\n".join(B.section_today(date(2026, 6, 1))[0])

    cp = M.run_monitor(date(2026, 6, 1), thesis_dir=tdir)["thesis_checkpoints"]
    assert len(cp["no_date"]) == 1 and not cp["due"] and not cp["approaching"]
    assert "thesis 조건 1건" not in text  # 세 갈래 합을 총계로 쓰지 않는다
    assert "날짜없는 상시감시 1건" in text
