"""
SEC 이벤트 수집기(v3.94) 테스트.

고정하는 불변조건:
  ① Form 4: 공개시장 P/S만, 10b5-1(체크박스·각주) 제외, 재량 순거래액 floor 미만은 기회적 아님
  ② 발행사가 다른 Form 4(회사가 타사 지분을 거래한 제출)는 내부자 매매에서 제외 — UBER 실측 오염
  ③ 제출 목록이 조회 창을 덮는지 먼저 증명하고, 덮지 못하면 부재 주장을 하지 않는다
  ④ 20-F/6-K 발행사는 UNAVAILABLE(Form 4·8-K 의무 없음) — 오탐 방지
  ⑤ 소송은 회사가 직접 '없음'이라 쓴 경우만 none, 그 밖에는 판단하지 않는다
  ⑥ 자사주 재원: 최근 연도가 낡으면 모른다(PGR 2009년 값 실측 오염)
  ⑦ 판정·점수 함수와 네트워크 import가 없다(§31, fetcher는 주입)
  ⑧ 개정본: 기존 파일·해시 불변, 사슬이 끊기면 거부, coverage는 최신본만 센다
  ⑨ merge: answered는 덮지 않고, 업종 변형에 없는 축은 버린다
"""
import ast
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from engine import qualitative_input as Q  # noqa: E402
from engine import sec_events as E  # noqa: E402

MODULE = os.path.join(ROOT, "engine", "sec_events.py")


def form4(issuer="1234", owner="Doe Jane", codes=(("S", "2026-03-01", 1000, 1500.0),),
          flag=False, footnote=""):
    tx = "".join(
        f"<nonDerivativeTransaction><transactionDate><value>{d}</value></transactionDate>"
        f"<transactionCoding><transactionCode>{c}</transactionCode></transactionCoding>"
        f"<transactionAmounts><transactionShares><value>{sh}</value></transactionShares>"
        f"<transactionPricePerShare><value>{px}</value></transactionPricePerShare>"
        f"<transactionAcquiredDisposedCode><value>{'A' if c == 'P' else 'D'}</value>"
        f"</transactionAcquiredDisposedCode></transactionAmounts></nonDerivativeTransaction>"
        for c, d, sh, px in codes)
    return (f"<ownershipDocument>{'<aff10b5One>1</aff10b5One>' if flag else ''}"
            f"<issuer><issuerCik>000{issuer}</issuerCik></issuer>"
            f"<reportingOwner><reportingOwnerId><rptOwnerName>{owner}</rptOwnerName></reportingOwnerId>"
            f"<reportingOwnerRelationship><isOfficer>1</isOfficer><officerTitle>CFO</officerTitle>"
            f"</reportingOwnerRelationship></reportingOwner>"
            f"<nonDerivativeTable>{tx}</nonDerivativeTable>"
            f"<footnotes><footnote id='F1'>{footnote}</footnote></footnotes></ownershipDocument>")


# ① Form 4 규칙 ---------------------------------------------------------------
def test_parse_form4_reads_transactions_and_flags():
    t = E.parse_form4(form4(flag=True))[0]
    assert (t["code"], t["shares"], t["price"], t["value_usd"]) == ("S", 1000.0, 1500.0, 1_500_000.0)
    assert t["is_10b5_1"] and t["issuer_cik"] == "1234" and t["is_officer"]


def test_footnote_10b5_1_mention_marks_routine():
    t = E.parse_form4(form4(footnote="sold pursuant to a Rule 10b5-1 trading plan"))[0]
    assert t["is_10b5_1"]


def _sm(txs):
    return E.summarize_insider(txs, "2025-10-06", "2026-10-06")


def test_non_open_market_codes_are_excluded():
    txs = E.parse_form4(form4(codes=(("A", "2026-03-01", 10**6, 10.0), ("M", "2026-03-01", 10**6, 10.0),
                                     ("F", "2026-03-01", 10**6, 10.0), ("G", "2026-03-01", 10**6, 10.0))))
    assert _sm(txs)["answer"] == "none"


def test_all_10b5_1_is_routine_only():
    txs = E.parse_form4(form4(flag=True, codes=(("S", "2026-03-01", 10**6, 100.0),)))
    assert _sm(txs)["answer"] == "routine_only"


def test_discretionary_below_floor_is_not_opportunistic():
    txs = E.parse_form4(form4(codes=(("S", "2026-03-01", 100, 100.0),)))     # $10k
    assert _sm(txs)["answer"] == "routine_only"


def test_discretionary_net_sell_and_buy_above_floor():
    sell = E.parse_form4(form4(codes=(("S", "2026-03-01", 10_000, 500.0),)))
    buy = E.parse_form4(form4(codes=(("P", "2026-03-01", 10_000, 500.0),)))
    assert _sm(sell)["answer"] == "opp_net_sell"
    assert _sm(buy)["answer"] == "opp_net_buy"
    both = sell + buy
    assert _sm(both)["discretionary_net_usd"] == 0 and _sm(both)["answer"] == "routine_only"


def test_transactions_outside_window_are_ignored():
    old = E.parse_form4(form4(codes=(("S", "2024-01-01", 10_000, 500.0),)))
    assert _sm(old)["answer"] == "none"


def test_unparseable_xml_raises_not_silently_empty():
    with pytest.raises(E.SecEventsError):
        E.parse_form4("<not xml")


# ② 발행사 필터 ----------------------------------------------------------------
LISTING = {"cik": "0000001234", "covers_window": True, "oldest_seen": "2020-01-01",
           "all_forms": ["4", "8-K", "10-K"],
           "rows": [{"form": "4", "filingDate": "2026-03-02", "accessionNumber": "0000001234-26-000001",
                     "items": "", "primaryDocument": "xslF345X06/form4.xml"},
                    {"form": "4", "filingDate": "2026-03-03", "accessionNumber": "0000001234-26-000002",
                     "items": "", "primaryDocument": "xslF345X06/form4.xml"}]}


def test_other_issuer_form4_is_excluded_from_insider_pattern():
    docs = {
        "000000123426000001": form4(issuer="1234", codes=(("P", "2026-03-01", 10_000, 500.0),)),
        # 회사 자신이 타사 지분을 판 제출 — 발행사 CIK가 다르다
        "000000123426000002": form4(issuer="9999", owner="Corp Inc", codes=(("S", "2026-03-01", 10**7, 100.0),)),
    }

    def fetch(url):
        return next(v for k, v in docs.items() if k in url)

    out = E.collect_insider(LISTING, fetch, "2026-10-06")
    assert out["status"] == "OK"
    assert out["summary"]["answer"] == "opp_net_buy"
    assert out["excluded_other_issuer_transactions"] == 1


def test_form4_read_failure_never_yields_partial_answer():
    def fetch(url):
        raise OSError("boom")
    out = E.collect_insider(LISTING, fetch, "2026-10-06")
    assert out["status"] == E.UNAVAILABLE and "읽기 실패" in out["reason"]


def test_too_many_form4_is_not_silently_truncated():
    big = {**LISTING, "rows": [LISTING["rows"][0]] * (E.FORM4_MAX + 1)}
    out = E.collect_insider(big, lambda u: form4(), "2026-10-06")
    assert out["status"] == E.UNAVAILABLE


# ③ 창 덮음 ---------------------------------------------------------------------
def _top(rows_dates, files=()):
    n = len(rows_dates)
    return {"filings": {"recent": {
        "accessionNumber": [f"a{i}" for i in range(n)], "filingDate": rows_dates,
        "form": ["8-K"] * n, "items": [""] * n, "primaryDocument": ["d.htm"] * n},
        "files": [{"name": f} for f in files]}}


def test_list_filings_reads_older_pages_until_window_is_covered():
    pages = {"https://data.sec.gov/submissions/CIK0000001234.json": _top(["2026-01-01"], ["old.json"]),
             "https://data.sec.gov/submissions/old.json": {
                 "accessionNumber": ["b0"], "filingDate": ["2022-01-01"], "form": ["8-K"],
                 "items": [""], "primaryDocument": ["d.htm"]}}
    out = E.list_filings("1234", "2023-01-01", lambda u: pages[u])
    assert out["covers_window"] and out["oldest_seen"] == "2022-01-01"


def test_list_filings_short_history_is_covered_only_after_all_pages_are_read():
    """상장 이력이 창보다 짧은 회사: 페이지를 모두 읽어 전체 이력을 확보했을 때만 덮은 것이다."""
    pages = {"https://data.sec.gov/submissions/CIK0000001234.json": _top(["2026-01-01"], ["old.json"]),
             "https://data.sec.gov/submissions/old.json": {
                 "accessionNumber": ["b0"], "filingDate": ["2025-06-01"], "form": ["8-K"],
                 "items": [""], "primaryDocument": ["d.htm"]}}
    out = E.list_filings("1234", "2023-01-01", lambda u: pages[u])
    assert out["oldest_seen"] == "2025-06-01" and out["covers_window"] is True


def test_empty_listing_is_never_covered():
    top = {"filings": {"recent": {"accessionNumber": [], "filingDate": [], "form": [], "items": [],
                                   "primaryDocument": []}, "files": []}}
    out = E.list_filings("1234", "2023-01-01", lambda u: top)
    assert out["covers_window"] is False


def test_uncovered_window_blocks_absence_claims():
    short = {**LISTING, "covers_window": False, "oldest_seen": "2026-01-01"}
    assert E.collect_restatement(short, "2026-10-06")["status"] == E.UNAVAILABLE
    assert E.collect_cxo(short, lambda u: "", "1234", "2026-10-06")["status"] == E.UNAVAILABLE
    assert E.collect_insider(short, lambda u: "", "2026-10-06")["status"] == E.UNAVAILABLE


# ④ 외국 발행사 ------------------------------------------------------------------
def test_foreign_private_issuer_is_unavailable_not_clean():
    fpi = {**LISTING, "all_forms": ["20-F", "6-K"]}
    assert E.is_foreign_private_issuer(fpi["all_forms"])
    assert not E.is_foreign_private_issuer(["10-K", "8-K", "4", "6-K"])
    # 20-F 발행사가 자발적·제3자 Form 4/8-K를 일부 내도 외국 발행사다(DLO·MNDY·PDD·SE 실측)
    assert E.is_foreign_private_issuer(["20-F", "6-K", "4", "3", "144"])
    # 20-F에서 10-K로 전환한 회사는 국내 발행사다
    assert not E.is_foreign_private_issuer(["20-F", "10-K", "8-K"])
    for out in (E.collect_insider(fpi, lambda u: "", "2026-10-06"),
                E.collect_cxo(fpi, lambda u: "", "1234", "2026-10-06"),
                E.collect_restatement(fpi, "2026-10-06")):
        assert out["status"] == E.UNAVAILABLE and "20-F" in out["reason"]


# 8-K 항목 / 임원 교체 ---------------------------------------------------------------
def test_restatement_collector_reports_facts_without_judging():
    rows = [{"form": "8-K", "filingDate": "2025-05-01", "accessionNumber": "x", "items": "2.02, 4.02",
             "primaryDocument": "d.htm"},
            {"form": "10-K/A", "filingDate": "2025-06-01", "accessionNumber": "y", "items": "",
             "primaryDocument": "d.htm"}]
    out = E.collect_restatement({**LISTING, "rows": rows}, "2026-10-06")
    assert out["n_item_402"] == 1 and out["n_10k_amendments"] == 1
    assert "answer" not in out                    # 방향(하향 여부)은 판단하지 않는다


def test_item_section_picks_body_not_table_of_contents():
    body = ("Item 5.02 Departure ... Item 9.01 Exhibits (cover list) "
            "Item 5.02 Departure of Officers. Mr. X, Chief Financial Officer, resigned effective today "
            "and the Board appointed an interim successor. Item 9.01 Financial Statements.")
    sec = E.item_section(body, "5.02")
    assert "resigned effective today" in sec and "Item 9.01" not in sec


def test_cxo_sentences_require_title_and_verb_in_same_sentence():
    sec = ("The Company announced that Jane Roe, Chief Financial Officer, will step down on May 1, 2026. "
           "The Board also reviewed the annual budget for the coming year in detail today. "
           "John Doe was appointed as Chief Executive Officer of the Company effective June 1, 2026.")
    out = E.cxo_sentences(sec)
    assert [s["departure"] for s in out] == [True, False]
    assert out[1]["appointment"]


def test_collect_cxo_counts_only_verified_departure_sentences():
    html = ("<html>Item 5.02 Departure. The Company announced that Jane Roe, Chief Financial Officer, "
            "will step down from her role on May 1, 2026. Item 9.01 Exhibits.</html>")
    listing = {**LISTING, "rows": [{"form": "8-K", "filingDate": "2026-02-01", "accessionNumber": "0000001234-26-000009",
                                    "items": "5.02,9.01", "primaryDocument": "e.htm"}]}
    out = E.collect_cxo(listing, lambda u: html, "1234", "2026-10-06")
    assert out["n_cxo_departure_filings"] == 1 and out["n_item_502_filings"] == 1
    ev = out["events"][0]
    assert E.quote_in_text(ev["quote"], E.normalize_text(html))      # 인용은 원문에 그대로 있다


# ⑤ 소송 -------------------------------------------------------------------------
def test_litigation_materiality_qualified_statement_is_immaterial_not_none():
    """ACGL 실측: '중요한 악영향이 예상되는 소송이 없다'는 소송이 없다는 뜻이 아니다."""
    body = ("Item 3. Legal Proceedings We were not a party to any litigation or arbitration which is "
            "expected by management to have a material adverse effect on our results. "
            "Item 4. Mine Safety Disclosures Not applicable.")
    out = E.litigation_from_item3(body)
    assert out["answer"] == "immaterial" and out["materiality_qualified"]


def test_litigation_unqualified_denial_is_none():
    body = ("Item 3. Legal Proceedings We are not currently a party to any legal proceedings. "
            "Item 4. Mine Safety Disclosures Not applicable.")
    out = E.litigation_from_item3(body)
    assert out["answer"] == "none" and not out["materiality_qualified"]


def test_litigation_note_reference_is_not_judged():
    body = ("Item 3. Legal Proceedings See Note 12, Commitments and Contingencies, for a description of "
            "legal proceedings. Item 4. Mine Safety Disclosures Not applicable.")
    out = E.litigation_from_item3(body)
    assert out["answer"] is None and out["excerpt"]


def test_litigation_missing_section_is_unknown():
    assert E.litigation_from_item3("no such heading")["answer"] is None


# ⑥ 자사주 재원 ------------------------------------------------------------------------
def test_debt_funded_buyback_rule_and_staleness_guard():
    assert E.debt_funded_buyback({2025: 400.0}, {2025: 100.0}, {2025: 800.0})["answer"] is False   # 순 300 < 400
    assert E.debt_funded_buyback({2025: 600.0}, {2025: 100.0}, {2025: 800.0})["answer"] is True    # 순 500 >= 400
    assert E.debt_funded_buyback({2025: 100.0}, {2025: 500.0}, {2025: 800.0})["answer"] is False   # 순상환
    stale = E.debt_funded_buyback({2009: 900.0}, {}, {2009: 800.0}, min_fy=2024)
    assert stale["answer"] is None and "낡았다" in stale["reason"]
    assert E.debt_funded_buyback({2025: 1.0}, {}, {2024: 1.0})["answer"] is None


# ⑦ 경계 -------------------------------------------------------------------------------
def test_module_has_no_judgment_or_network_surface():
    with open(MODULE, encoding="utf-8") as f:
        tree = ast.parse(f.read())
    banned = ("score", "grade", "verdict", "decide", "recommend", "should_", "rank", "weight")
    fns = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and not n.name.startswith("_")]
    assert not [n for n in fns if any(b in n.lower() for b in banned)], fns
    imports = {a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    imports |= {n.module.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module}
    assert not imports & {"urllib", "requests", "http", "socket", "anthropic", "openai"}, imports


def test_not_wired_into_judgment_path():
    for name in ("pipeline.py", "expectation_gap_engine.py", "portfolio_pipeline.py", "screener.py"):
        with open(os.path.join(ROOT, "engine", name), encoding="utf-8") as f:
            assert "sec_events" not in f.read(), name


# ⑧ 개정본 ------------------------------------------------------------------------------
def _payload(**over):
    p = {"entity": "TEST", "as_of": "2026-10-06", "lens_set": "standard", "price_at_analysis": None,
         "currency": "USD", "claims": [], "findings": [], "disqualifiers": [],
         "inversion": [], "confidence_recommendation": None,
         "answers": [{"qid": "gov.dual_class", "status": "unknown", "note": "미확인"}]}
    p.update(over)
    return p


def _two_records():
    first = Q.build_record(_payload())
    second = Q.build_record(_payload(answers=[
        {"qid": "gov.dual_class", "status": "unknown", "note": "프록시 미확보(사유 구체화)"}]))
    return first, second


def test_revision_chain_keeps_original_untouched(tmp_path):
    first, second = _two_records()
    p1 = Q.save_record(first, str(tmp_path))
    before = open(p1, "rb").read()
    with pytest.raises(FileExistsError):                 # supersedes 없이는 여전히 거부
        Q.save_record(second, str(tmp_path))
    p2 = Q.save_record(second, str(tmp_path), supersedes=first["sealed_core_hash"])
    assert os.path.basename(p2) == "TEST_2026-10-06_r2.json"
    assert open(p1, "rb").read() == before               # 기존 파일 한 글자도 불변
    saved = json.load(open(p2, encoding="utf-8"))
    assert saved["revision"] == 2 and saved["supersedes"] == first["sealed_core_hash"]
    assert Q.verify_record(saved)["ok"]                  # 개정 필드는 비봉인이라 해시가 유지된다
    assert Q.latest_record("TEST", str(tmp_path))["revision"] == 2


def test_revision_with_broken_chain_or_no_change_is_refused(tmp_path):
    first, second = _two_records()
    Q.save_record(first, str(tmp_path))
    with pytest.raises(Q.QualitativeInputError):
        Q.save_record(second, str(tmp_path), supersedes="deadbeef")
    with pytest.raises(Q.QualitativeInputError):
        Q.save_record(first, str(tmp_path), supersedes=first["sealed_core_hash"])
    with pytest.raises(Q.QualitativeInputError):
        Q.save_record(Q.build_record(_payload(entity="OTHER")), str(tmp_path), supersedes="x")


def test_filename_regex_accepts_revisions():
    m = Q.FNAME_RE.match("PGR_2026-10-06_r3.json")
    assert (m["ticker"], m["date"], m["rev"]) == ("PGR", "2026-10-06", "3")
    assert Q.FNAME_RE.match("PGR_2026-10-06.json")["rev"] is None


def test_coverage_counts_latest_revision_only(tmp_path):
    import importlib
    intake = importlib.import_module("scripts.qualitative_intake")
    first, second = _two_records()
    Q.save_record(first, str(tmp_path))
    Q.save_record(second, str(tmp_path), supersedes=first["sealed_core_hash"])
    rep = intake.build_coverage(str(tmp_path))
    assert rep["n_sealed_records"] == 1 and rep["n_record_files"] == 2
    assert rep["sealed"][0]["sealed_core_hash"] == second["sealed_core_hash"]


def test_new_cxo_question_is_primary_required_number():
    q = Q._BY_QID["gov.cxo_turnover_24m"]
    assert q.answer_type == "number" and q.requires_primary and q.lens == "governance"


# ⑨ merge ------------------------------------------------------------------------------
def test_merge_never_overwrites_answered_and_drops_foreign_lenses():
    import importlib
    S = importlib.import_module("scripts.qsi_sec_events")
    claim = {"claim_id": "T.X", "statement": "s", "materiality": "HIGH", "evidence": [{
        "summary": "e", "direction": "neutral", "verification": "VERIFIED_PRIMARY", "confidence": "HIGH",
        "citation": {"source_key": "sec_edgar", "document": "d", "location": "l",
                     "observed_date": "2026-10-06", "url": "u", "quote": ""}}]}
    prior = Q.build_record(_payload(
        lens_set="insurance",
        claims=[{**claim, "claim_id": "T.OLD"}],
        answers=[{"qid": "gov.dual_class", "status": "answered", "answer": False, "claim_ids": ["T.OLD"],
                  "note": ""},
                 {"qid": "gov.insider_pattern", "status": "unknown", "note": "미조회"}]))
    new_answers = [
        {"qid": "gov.dual_class", "status": "answered", "answer": True, "claim_ids": ["T.X"], "note": ""},
        {"qid": "gov.insider_pattern", "status": "answered", "answer": "none", "claim_ids": ["T.X"], "note": ""},
        {"qid": "cap.debt_funded_buyback", "status": "answered", "answer": True, "claim_ids": ["T.X"],
         "note": ""}]                                  # 보험 업종 변형에는 자본배분 축이 없다
    findings = [{"lens": "governance", "effect": "neutral", "claim_ids": ["T.X"], "summary": "g"},
                {"lens": "capital_allocation", "effect": "neutral", "claim_ids": ["T.X"], "summary": "c"}]
    core, changed = S.merge(prior, [claim], new_answers, findings, "2026-10-06")
    by = {a["qid"]: a for a in core["answers"]}
    assert by["gov.dual_class"]["answer"] is False                  # answered는 덮지 않는다
    assert by["gov.insider_pattern"]["answer"] == "none"
    assert "cap.debt_funded_buyback" not in by
    assert {f["lens"] for f in core["findings"]} == {"governance"}
    rec = Q.build_record(core)                                      # 계약을 통과한다
    assert rec["sealed_core_hash"] != prior["sealed_core_hash"]
    assert changed == ["gov.insider_pattern"]
