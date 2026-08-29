"""broad_screen_post.py 테스트 - 포맷팅만, 네트워크 없이."""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from scripts import broad_screen_post as P  # noqa: E402


SAMPLE = {
    "retrieved_at": "2026-08-29",
    "universe_total": 10391,
    "attempted": 8897,
    "sec_ok": 4000,
    "scored": 4000,
    "passed": 2,
    "passed_tickers": [
        {"ticker": "PGR", "tier": "S", "expectation_gap_est": 0.1408,
         "market_cap": 155_900_000_000.0, "note": "public_float FY2025 기준"},
        {"ticker": "COR", "tier": "A", "expectation_gap_est": 0.0787,
         "market_cap": 37_887_695_618.0, "note": "public_float FY2025 기준"},
    ],
    "skip_breakdown": [
        {"label": "연도 데이터 부족", "count": 62, "infra_failure": False,
         "sample": ["JPM", "LLY"]},
    ],
}


def test_format_body_sorts_passed_by_gap_descending():
    body = P.format_body(SAMPLE)
    assert body.index("PGR") < body.index("COR")


def test_format_body_includes_estimate_caveat():
    body = P.format_body(SAMPLE)
    assert "1차 추정치일 뿐 정식 판정이 아니다" in body


def test_format_body_no_passed_tickers_says_so_explicitly():
    empty = dict(SAMPLE, passed=0, passed_tickers=[])
    body = P.format_body(empty)
    assert "통과 후보 없음" in body


def test_latest_report_picks_newest_date(tmp_path, monkeypatch):
    monkeypatch.setattr(P, "REPORTS_DIR", str(tmp_path))
    (tmp_path / "broad_screen_2026-08-22.json").write_text(
        json.dumps({"retrieved_at": "2026-08-22"}), encoding="utf-8")
    (tmp_path / "broad_screen_2026-08-29.json").write_text(
        json.dumps({"retrieved_at": "2026-08-29"}), encoding="utf-8")
    d = P.latest_report()
    assert d["retrieved_at"] == "2026-08-29"


def test_latest_report_returns_none_when_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(P, "REPORTS_DIR", str(tmp_path))
    assert P.latest_report() is None
