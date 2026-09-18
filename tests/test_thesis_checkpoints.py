"""
engine/thesis_checkpoints.py 고정 테스트 (2026-09-18).

핵심 불변조건: 이 모듈은 "확인할 때가 됐는가"만 계산하고 "조건이 실제로
발동했는가"는 절대 판정하지 않는다(v3.42 원칙의 thesis 계층 확장).
"""
import json
import os

import pytest

from engine.thesis_checkpoints import (
    due_conditions, enrich_with_sec_freshness, format_checkpoint_report,
)


def _write_thesis(thesis_dir, ticker, thesis_date, conditions,
                   linked_ledger=None):
    path = os.path.join(thesis_dir, f"{ticker}_{thesis_date}.json")
    record = {
        "thesis": {
            "ticker": ticker,
            "thesis_id": f"{ticker}-{thesis_date}",
            "thesis_date": thesis_date,
            "linked_ledger": linked_ledger,
            "invalidation_conditions": conditions,
        },
        "decisions": [],
        "evidence": [],
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(record, f)
    return path


def _cond(text, check_by=None, triggered=False):
    return {"condition": text, "check_by": check_by, "triggered": triggered,
            "triggered_note": None}


# ── 핵심: 자동 판정 금지 ──────────────────────────────────────────────
def test_module_never_decides_whether_a_condition_fired():
    import engine.thesis_checkpoints as tc
    banned = ("decide", "judge", "evaluate_trigger", "auto_resolve",
              "determine_triggered", "is_triggered")
    public = [n for n in dir(tc) if not n.startswith("_")]
    for name in public:
        assert not any(b in name.lower() for b in banned), (
            f"{name}: 이 모듈은 '기한이 됐는가'만 계산하고 '발동했는가'는 "
            f"판정하지 않는다")


# ── due_conditions: 순수 날짜 산술 ───────────────────────────────────
def test_due_condition_is_past_check_by(tmp_path):
    _write_thesis(str(tmp_path), "AAA", "2026-01-01", [
        _cond("조건1", check_by="2026-09-01"),
    ])
    out = due_conditions("2026-09-18", thesis_dir=str(tmp_path))
    assert len(out["due"]) == 1
    assert out["due"][0]["ticker"] == "AAA"
    assert out["due"][0]["days_until_check_by"] == -17


def test_approaching_condition_within_warn_window(tmp_path):
    _write_thesis(str(tmp_path), "BBB", "2026-01-01", [
        _cond("조건1", check_by="2026-09-30"),  # 12일 뒤
    ])
    out = due_conditions("2026-09-18", thesis_dir=str(tmp_path),
                         warn_window_days=30)
    assert len(out["approaching"]) == 1
    assert out["due"] == []
    assert out["approaching"][0]["days_until_check_by"] == 12


def test_far_future_condition_is_neither_due_nor_approaching(tmp_path):
    _write_thesis(str(tmp_path), "CCC", "2026-01-01", [
        _cond("조건1", check_by="2027-06-01"),
    ])
    out = due_conditions("2026-09-18", thesis_dir=str(tmp_path),
                         warn_window_days=30)
    assert out["due"] == []
    assert out["approaching"] == []


def test_no_date_condition_goes_to_its_own_bucket(tmp_path):
    _write_thesis(str(tmp_path), "DDD", "2026-01-01", [
        _cond("날짜없는 조건", check_by=None),
    ])
    out = due_conditions("2026-09-18", thesis_dir=str(tmp_path))
    assert len(out["no_date"]) == 1
    assert out["due"] == [] and out["approaching"] == []


def test_triggered_conditions_are_excluded_entirely(tmp_path):
    """이미 발동 표시된 조건은 확인할 것이 아니다 - 세 버킷 어디에도 없어야."""
    _write_thesis(str(tmp_path), "EEE", "2026-01-01", [
        _cond("이미 발동", check_by="2026-01-01", triggered=True),
    ])
    out = due_conditions("2026-09-18", thesis_dir=str(tmp_path))
    assert out["due"] == [] and out["approaching"] == [] and out["no_date"] == []


def test_multiple_theses_and_conditions_all_scanned(tmp_path):
    _write_thesis(str(tmp_path), "F1", "2026-01-01", [
        _cond("f1-a", check_by="2026-09-01"),
        _cond("f1-b", check_by="2027-01-01"),
    ])
    _write_thesis(str(tmp_path), "F2", "2026-02-01", [
        _cond("f2-a", check_by="2026-09-15"),
    ])
    out = due_conditions("2026-09-18", thesis_dir=str(tmp_path))
    tickers_due = {e["ticker"] for e in out["due"]}
    assert tickers_due == {"F1", "F2"}


def test_date_object_input_accepted():
    import datetime
    # 문자열이 아니라 date 객체를 넣어도 동작해야 한다.
    out = due_conditions(datetime.date(2026, 9, 18), thesis_dir="does-not-exist")
    assert out == {"due": [], "approaching": [], "no_date": []}


# ── enrich_with_sec_freshness: 네트워크 없이 가짜 provider로 검증 ────
class _FakeFact:
    def __init__(self, metric, fiscal_year, value):
        self.metric, self.fiscal_year, self.value = metric, fiscal_year, value


class _FakeResult:
    def __init__(self, facts):
        self.facts = facts


class _FakeProvider:
    def __init__(self, facts_by_ticker):
        self.facts_by_ticker = facts_by_ticker
        self.calls = []

    def fetch_annual_financials(self, entity, metrics=None, retrieved_at=None):
        self.calls.append((entity, metrics, retrieved_at))
        if entity == "BROKEN":
            raise RuntimeError("network down")
        facts = self.facts_by_ticker.get(entity, [])
        return _FakeResult(facts)


def _write_ledger(ledger_dir, ticker, date, revenue_by_year):
    os.makedirs(ledger_dir, exist_ok=True)
    path = os.path.join(ledger_dir, f"{ticker}_{date}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"inputs": {"revenue_by_year": revenue_by_year}}, f)
    return f"{ticker}_{date}.json"


def test_enrich_detects_new_annual_data(tmp_path):
    ledger_dir = str(tmp_path / "ledger")
    linked = _write_ledger(ledger_dir, "GGG", "2026-01-01",
                           {"2023": 100, "2024": 110, "2025": 120})
    entries = [{"ticker": "GGG", "linked_ledger": linked,
                "check_by": "2026-09-01"}]
    provider = _FakeProvider({
        "GGG": [_FakeFact("revenue", 2025, 120), _FakeFact("revenue", 2026, 140)],
    })
    out = enrich_with_sec_freshness(entries, provider, retrieved_at="2026-09-18",
                                    ledger_dir=ledger_dir)
    assert out[0]["sec_freshness"]["status"] == "OK"
    assert out[0]["sec_freshness"]["new_annual_available"] is True
    assert out[0]["sec_freshness"]["ledger_latest_fy"] == 2025
    assert out[0]["sec_freshness"]["sec_latest_fy"] == 2026


def test_enrich_reports_no_new_data_honestly(tmp_path):
    ledger_dir = str(tmp_path / "ledger")
    linked = _write_ledger(ledger_dir, "HHH", "2026-01-01", {"2025": 50})
    entries = [{"ticker": "HHH", "linked_ledger": linked, "check_by": None}]
    provider = _FakeProvider({"HHH": [_FakeFact("revenue", 2025, 50)]})
    out = enrich_with_sec_freshness(entries, provider, retrieved_at="2026-09-18",
                                    ledger_dir=ledger_dir)
    assert out[0]["sec_freshness"]["new_annual_available"] is False


def test_enrich_surfaces_provider_failure_without_crashing(tmp_path):
    ledger_dir = str(tmp_path / "ledger")
    linked = _write_ledger(ledger_dir, "BROKEN", "2026-01-01", {"2025": 1})
    entries = [{"ticker": "BROKEN", "linked_ledger": linked, "check_by": None}]
    provider = _FakeProvider({})
    out = enrich_with_sec_freshness(entries, provider, retrieved_at="2026-09-18",
                                    ledger_dir=ledger_dir)
    assert out[0]["sec_freshness"]["status"] == "SEC_FETCH_FAILED"
    assert "network down" in out[0]["sec_freshness"]["error"]


def test_enrich_handles_missing_ledger_honestly(tmp_path):
    entries = [{"ticker": "GHOST", "linked_ledger": None, "check_by": None}]
    provider = _FakeProvider({})
    out = enrich_with_sec_freshness(entries, provider, retrieved_at="2026-09-18",
                                    ledger_dir=str(tmp_path / "empty"))
    assert out[0]["sec_freshness"]["status"] == "LEDGER_NOT_FOUND"


# ── format_checkpoint_report: 사람이 읽는 요약 ───────────────────────
def test_report_is_quiet_when_nothing_due():
    out = format_checkpoint_report(due=[], approaching=[])
    assert "0건" in out
    assert "확인이 필요한" in out


def test_report_surfaces_due_and_approaching_separately():
    due = [{"ticker": "AAA", "check_by": "2026-09-01", "condition": "x",
           "days_until_check_by": -17,
           "sec_freshness": {"status": "OK", "new_annual_available": True,
                             "sec_latest_fy": 2026, "ledger_latest_fy": 2025}}]
    approaching = [{"ticker": "BBB", "check_by": "2026-09-30",
                    "days_until_check_by": 12}]
    out = format_checkpoint_report(due=due, approaching=approaching)
    assert "지금 확인할 것" in out and "AAA" in out
    assert "FY2026 신규 확보됨" in out
    assert "곧 도래" in out and "BBB" in out


def test_real_thesis_directory_scans_without_error():
    """실제 thesis/ 디렉터리를 스캔해도 예외 없이 동작해야 한다."""
    out = due_conditions("2026-09-18")
    assert isinstance(out, dict)
    assert set(out) == {"due", "approaching", "no_date"}
