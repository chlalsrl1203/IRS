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
def test_buylist_renders_actual_amounts(text):
    assert "1,800,000원" in text, "비중을 금액으로 환산하지 못했다"
    assert "10,000,000원" in text
    assert "**합계** | **100.00%**" in text


def test_amounts_scale_with_capital():
    os.chdir(ROOT)
    a, _ = B.build(date(2026, 8, 28), 10_000_000, 8)
    b, _ = B.build(date(2026, 8, 28), 20_000_000, 8)
    assert "1,800,000원" in a and "3,600,000원" in b


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
