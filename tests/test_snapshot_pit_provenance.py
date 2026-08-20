"""
P0-08 / P0-09 / P0-10 — Provenance 연결 · Snapshot · PIT 연결 테스트.

# SOURCE:
https://github.com/chenditc/investment_data (versioned dataset / manifest)

고정하는 불변조건:
  ① provider가 값 단위 출처를 **자동 생성**한다 (손으로 적게 하면 아무도 안 적는다)
  ② PIT 날짜가 **실제로 쓴 값과 같은 사실**에서 나온다
  ③ 스냅샷이 같은 날 다른 내용을 조용히 덮어쓰지 않는다
  ④ 스냅샷 1개로 "재작성 없음"이라 말하지 않는다
  ⑤ 소급 스냅샷을 만들지 않는다
"""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.data.canonical import (  # noqa: E402
    build_canonical_series, canonical_pit_inputs, canonical_provenance_record,
)
from engine.data.providers.base import FinancialFact, ProviderResult  # noqa: E402
from engine.data.reconcile import reconcile_candidates  # noqa: E402
from engine.data.snapshot import (  # noqa: E402
    content_hash, detect_restatements, load_snapshots, save_snapshot,
    write_manifest,
)
from engine.provenance import PROVENANCE_UNKNOWN, ValueProvenance  # noqa: E402


def fact(metric="revenue", fy=2025, value=20_074_000_000.0,
         source_key="sec_edgar", available_at="2026-02-18"):
    return FinancialFact(
        entity="BSX", metric=metric, fiscal_year=fy, value=value,
        unit="currency_amount", currency="USD",
        period_start=f"{fy}-01-01", period_end=f"{fy}-12-31",
        available_at=available_at, source="SEC XBRL us-gaap:Revenues",
        source_key=source_key, retrieved_at="2026-08-19",
    )


def result(facts, retrieved_at="2026-08-19"):
    return ProviderResult(
        source_key="sec_edgar", entity="BSX", facts=facts,
        governance={"decision": "ALLOWED"}, retrieved_at=retrieved_at,
    )


# ── ① Provenance 자동 생성 ───────────────────────────────────────────────
def test_fact_converts_to_value_provenance_without_manual_entry():
    p = fact().to_provenance()
    assert isinstance(p, ValueProvenance)
    assert p.field_path == "revenue_by_year[2025]"
    assert p.period == "2025-01-01~2025-12-31"
    assert p.publication_date == "2026-02-18"      # 공시일 — 조회일과 다르다
    assert p.retrieval_date == "2026-08-19"
    assert p.source_kind == "sec_xbrl"             # 등록부에서 끌어온다


def test_provenance_source_kind_comes_from_the_registry_not_a_literal():
    """
    provider 거버넌스와 값 단위 출처가 어긋나면 두 계층을 대조할 수 없다.
    문자열을 손으로 적지 않고 등록부에서 끌어오는지 확인한다.
    """
    from engine.data.governance.source_registry import get_source
    for key in ("sec_edgar", "alpha_vantage"):
        f = fact(source_key=key)
        assert f.to_provenance().source_kind == get_source(key).source_kind


def test_result_generates_a_provenance_record_including_what_is_missing():
    r = result([fact(), fact(fy=2024, value=1.0)])
    r.limitations.append("[미확보] sbc: 태그를 찾지 못했다")
    rec = r.to_provenance_record()
    assert rec["status"] == "PROVENANCE_RECORDED"
    assert rec["n_covered"] == 2
    assert any("[미확보]" in m for m in rec["missing_fields"])


def test_empty_result_reports_provenance_unknown_not_a_fake_record():
    assert result([]).to_provenance_record()["status"] == PROVENANCE_UNKNOWN


def test_canonical_layer_records_chosen_source_and_flags_unresolved():
    s = build_canonical_series("BSX", {
        "sec_edgar": [fact(metric="operating_income", value=3_613_000_000)],
        "alpha_vantage": [fact(metric="operating_income", value=3_971_000_000,
                               source_key="alpha_vantage")],
    }, reconcile_fn=reconcile_candidates)
    rec = canonical_provenance_record(s, "2026-08-19")
    # 미해결이라 채택된 값이 없다 -> 커버가 아니라 missing으로 잡혀야 한다
    assert rec["n_covered"] == 0
    assert rec["missing_fields"] == ["operating_income_by_year[2025]"]


# ── ② PIT가 실제로 쓴 값과 같은 사실에서 나온다 ──────────────────────────
def test_pit_inputs_come_from_the_same_facts_as_the_values():
    r = result([fact(fy=2024, available_at="2025-02-18"),
                fact(fy=2025, available_at="2026-02-18")])
    pit = r.to_pit_inputs("2026-08-19")
    assert pit["analysis_as_of"] == "2026-08-19"
    assert pit["filing_dates_by_year"] == {2024: "2025-02-18", 2025: "2026-02-18"}
    # 값과 날짜가 같은 사실에서 나왔다
    assert r.available_at_by_year("revenue") == pit["filing_dates_by_year"]


def test_pit_field_is_omitted_when_dates_are_unavailable():
    """억지로 채우면 '검증한 척'이 된다 — PIT_UNKNOWN으로 떨어져야 한다."""
    assert result([]).to_pit_inputs("2026-08-19") == {"analysis_as_of": "2026-08-19"}


def test_canonical_pit_uses_the_earliest_publication_date():
    """늦은 쪽을 쓰면 PIT 검증이 실제보다 관대해진다."""
    s = build_canonical_series("BSX", {
        "sec_edgar": [fact(available_at="2026-02-18")],
        "alpha_vantage": [fact(source_key="alpha_vantage",
                               available_at="2026-03-30")],
    }, reconcile_fn=reconcile_candidates)
    assert canonical_pit_inputs(s, "2026-08-19")["filing_dates_by_year"] == {
        2025: "2026-02-18"}


# ── ③ 스냅샷 덮어쓰기 ────────────────────────────────────────────────────
def test_identical_rerun_is_allowed(tmp_path):
    """'같은 입력으로 재실행해 값이 같은지 확인'이 이 저장소의 표준 검증 관행이다."""
    d = str(tmp_path)
    p1 = save_snapshot(result([fact()]), base_dir=d)
    p2 = save_snapshot(result([fact()]), base_dir=d)
    assert p1 == p2 and len(load_snapshots("BSX", base_dir=d)) == 1


def test_same_day_different_content_is_refused(tmp_path):
    """v3.46이 save_ledger에서 잡은 사고(1차 결과가 흔적 없이 사라짐)를 막는다."""
    d = str(tmp_path)
    save_snapshot(result([fact(value=100.0)]), base_dir=d)
    with pytest.raises(FileExistsError, match="흔적 없이 사라진다"):
        save_snapshot(result([fact(value=200.0)]), base_dir=d)
    # 의도한 갱신은 명시해야 한다
    save_snapshot(result([fact(value=200.0)]), base_dir=d, overwrite=True)


def test_content_hash_ignores_key_order_but_not_values():
    assert content_hash({"a": 1, "b": 2}) == content_hash({"b": 2, "a": 1})
    assert content_hash({"a": 1}) != content_hash({"a": 2})


# ── ④ 재작성 탐지 ────────────────────────────────────────────────────────
def test_single_snapshot_says_unknown_not_no_restatement(tmp_path):
    """데이터 부재를 안전 신호로 오독하지 않는다(v3.37 겹침 측정의 교훈)."""
    d = str(tmp_path)
    save_snapshot(result([fact()]), base_dir=d)
    r = detect_restatements("BSX", base_dir=d)
    assert r["comparable"] is False
    assert r["restatements"] == []
    assert "알 수 없음" in r["note"]


def test_restatement_between_snapshots_is_detected(tmp_path):
    d = str(tmp_path)
    save_snapshot(result([fact(value=20_074_000_000.0)],
                         retrieved_at="2026-08-19"), base_dir=d)
    save_snapshot(result([fact(value=20_500_000_000.0)],
                         retrieved_at="2027-03-01"), base_dir=d)
    r = detect_restatements("BSX", base_dir=d)
    assert r["comparable"] is True and len(r["restatements"]) == 1
    c = r["restatements"][0]
    assert c["from_value"] == 20_074_000_000.0 and c["to_value"] == 20_500_000_000.0
    assert c["from_retrieved_at"] == "2026-08-19"
    assert c["rel_change"] == pytest.approx(0.021221, rel=1e-3)


def test_unchanged_values_across_snapshots_produce_no_false_restatement(tmp_path):
    d = str(tmp_path)
    save_snapshot(result([fact()], retrieved_at="2026-08-19"), base_dir=d)
    save_snapshot(result([fact()], retrieved_at="2027-03-01"), base_dir=d)
    r = detect_restatements("BSX", base_dir=d)
    assert r["comparable"] is True and r["restatements"] == []


# ── ⑤ 소급 스냅샷 금지 ───────────────────────────────────────────────────
def test_manifest_states_that_backfill_is_not_done(tmp_path):
    d = str(tmp_path)
    save_snapshot(result([fact()]), base_dir=d)
    m = json.load(open(write_manifest(base_dir=d, today="2026-08-19"),
                       encoding="utf-8"))
    assert m["n_snapshots"] == 1 and m["entities"] == ["BSX"]
    assert m["snapshots"][0]["content_hash"]
    assert "소급 생성하지 않는다" in m["note"]


def test_repository_has_no_backfilled_snapshots_for_the_34_tickers():
    """
    기존 34종목에 오늘 조회한 값을 그때 값인 양 저장하면 허위 증거가 된다
    (provenance v3.50이 같은 이유로 거부한 일). 실제로 안 만들었는지 고정한다.
    """
    import glob
    existing = glob.glob(os.path.join("snapshots", "*", "*.json"))
    ledger_tickers = {
        os.path.basename(p).split("_")[0] for p in glob.glob("ledger/*.json")}
    backfilled = [p for p in existing
                  if os.path.basename(p).split("_")[0] in ledger_tickers
                  and "2026-08-19" not in p]
    assert backfilled == [], f"소급 스냅샷으로 보이는 파일: {backfilled}"
