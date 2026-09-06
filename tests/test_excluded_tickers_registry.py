"""
`data/excluded_tickers.json` + `scripts/update_research_queue.py` 배선 테스트
(2026-09-06).

이 레지스트리가 존재하는 이유는 LNTH가 실제로 큐에 재등장해 사람이 또
조사해야 했던 사고(CLAUDE.md 'LNTH 제외' 항목)다 - 여기서는 그 사고가
막히는지, 그리고 잘못 넣기 쉬운 카테고리(실적이 실제로 나빠져서 제외된
종목)가 안 섞여 있는지를 고정한다.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

REGISTRY_PATH = os.path.join(ROOT, "data", "excluded_tickers.json")

ALLOWED_CATEGORIES = {"FRAMEWORK_MISMATCH", "PENDING_ACQUISITION"}

# CLAUDE.md가 "4분류 3번"(실적이 실제로 나빠짐)으로 확정한 종목 - 시점부
# 판단이라 여기 있으면 안 된다. 턴어라운드하면 재조사할 가치가 있다.
GENUINELY_WORSENED_NOT_STRUCTURAL = {
    "KR", "AGCO", "NKE", "UAA", "HON", "UWM", "AI", "ALGN", "LMB", "PTON",
}


def _load():
    with open(REGISTRY_PATH, encoding="utf-8") as f:
        return json.load(f)


def test_registry_file_exists_and_parses():
    data = _load()
    assert "entries" in data and isinstance(data["entries"], dict)
    assert len(data["entries"]) > 0


def test_every_entry_has_required_fields():
    data = _load()
    for ticker, e in data["entries"].items():
        assert ticker == ticker.upper(), f"{ticker}: 티커는 대문자여야 한다"
        assert e["reason_category"] in ALLOWED_CATEGORIES, (
            f"{ticker}: 알 수 없는 reason_category {e['reason_category']!r} - "
            f"허용값은 {ALLOWED_CATEGORIES}뿐이다(합성 카테고리 남발 금지)"
        )
        assert e.get("reason"), f"{ticker}: 근거 없이 등록된 제외는 검증 불가"
        assert e.get("excluded_at"), f"{ticker}: 제외 시점이 없다"


def test_does_not_contain_genuinely_worsened_tickers():
    """
    '실적이 실제로 나빠져서' 뺀 종목은 시점부 판단이라 영구 배제 레지스트리에
    넣으면 안 된다 - 나중에 실적이 개선되면 재조사할 가치가 있고, 큐가 그런
    턴어라운드 후보를 다시 골라내는 건 스크리닝의 목적 중 하나다.
    """
    data = _load()
    leaked = set(data["entries"]) & GENUINELY_WORSENED_NOT_STRUCTURAL
    assert not leaked, f"영구배제 레지스트리에 시점부 판단 종목이 섞였다: {leaked}"


def test_excluded_tickers_loader_reads_registry():
    from scripts import update_research_queue as U

    excl = U.excluded_tickers()
    assert "LNTH" in excl
    assert excl["LNTH"]["reason_category"] == "PENDING_ACQUISITION"


def test_excluded_tickers_loader_survives_missing_file(monkeypatch):
    """레지스트리가 없어도 실행이 막히면 안 된다(opt-in) - 빈 dict로 진행."""
    from scripts import update_research_queue as U

    monkeypatch.setattr(U, "EXCLUDED_PATH", "/nonexistent/path.json")
    assert U.excluded_tickers() == {}


def test_lnth_end_to_end_never_resurfaces_via_run():
    """
    LNTH 재등장 사고의 실제 재현 - run()이 만드는 최종 큐에서 LNTH가
    QUEUED로 다시 나타나면 안 된다.
    """
    from engine.research_queue import annotate, merge_run, next_to_research
    from scripts.update_research_queue import excluded_tickers

    passed = [{"ticker": "LNTH", "tier": "S", "expectation_gap_est": 0.20,
               "market_cap": 5e9, "out_of_validated_scope": []}]
    q = merge_run({}, passed, "2026-09-06")
    entries = annotate(q, set(), set(), "2026-09-06", excluded_tickers())
    assert entries["LNTH"]["state"] == "EXCLUDED"
    nxt = next_to_research(list(entries.values()), n=10)
    assert "LNTH" not in [e["ticker"] for e in nxt]
