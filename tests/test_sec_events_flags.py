"""
SEC 이벤트 수집기 확장(v3.95) 테스트 — 적신호 공시·보수 승인·내부자 지분·ICFR·배당.

고정하는 불변조건 (전부 **실문서에서 실제로 마주친 형식**을 입력으로 삼았다):
  ① NT·4.01·2.06은 제출 목록에서 센다. 20-F 발행사·창 미충족은 UNAVAILABLE(0건으로 오독 금지)
  ② say-on-pay: 표 3형식·서술 1형식을 읽고, '빈도(frequency)' 안건과 멀리 있는 표는 연결하지 않는다
  ③ 내부자 지분: '*'=1% 미만, 다중 클래스·비표준 행은 답하지 않는다
  ④ ICFR: 경영진의 결론 문장만 — 위험요인의 가정문은 읽지 않는다
  ⑤ 배당: True만 단언한다(감소는 특별배당과 구분 불가라 판단 보류)
  ⑥ 보이지 않는 문자(U+200B)가 숫자 사이에 끼어도 읽는다(SKYW 실측)
  ⑦ 새 함수에 판정·점수 이름이 없다
"""
import ast
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from engine import qualitative_input as Q  # noqa: E402
from engine import sec_events as E  # noqa: E402

MODULE = os.path.join(ROOT, "engine", "sec_events.py")


def listing(rows, covers=True, forms=("10-K", "8-K", "DEF 14A")):
    return {"cik": "0000000001", "rows": rows, "covers_window": covers,
            "oldest_seen": "2020-01-01", "all_forms": list(forms)}


def row(form, date, items="", acc="0001-26-000001"):
    return {"accessionNumber": acc, "filingDate": date, "form": form, "items": items,
            "primaryDocument": "x.htm"}


# ① 목록 기반 적신호 -------------------------------------------------------------
def test_listing_flags_count_nt_auditor_and_impairment():
    rows = [row("NT 10-K", "2025-03-03"), row("NT 10-Q", "2025-08-01"),
            row("8-K", "2024-10-30", "4.01,9.01"), row("8-K", "2024-11-18", "4.01"),
            row("8-K", "2025-06-01", "2.06"), row("8-K", "2025-07-01", "5.02"),
            row("NT 10-K", "2020-01-01")]          # 창 밖
    fl = E.collect_listing_flags(listing(rows), "2026-10-07")
    assert (fl["n_nt"], fl["n_auditor_change"], fl["n_material_impairment"]) == (2, 2, 1)


def test_listing_flags_zero_is_a_statement_only_when_window_is_covered():
    assert E.collect_listing_flags(listing([], covers=False), "2026-10-07")["status"] == E.UNAVAILABLE
    ok = E.collect_listing_flags(listing([]), "2026-10-07")
    assert ok["status"] == "OK" and ok["n_nt"] == 0


def test_listing_flags_foreign_private_issuer_is_unavailable():
    fl = E.collect_listing_flags(listing([], forms=("20-F", "6-K")), "2026-10-07")
    assert fl["status"] == E.UNAVAILABLE and "20-F" in fl["reason"]


# ② 보수 승인 ----------------------------------------------------------------------
TABLE_ADBE = ("4. Approve, on an advisory basis, the compensation of our named executive officers. "
              "Votes For Votes Against Abstentions Broker Non-Votes 148,837,167 144,993,886 687,689 41,927,404")
PROSE_PGR = ("Proposal Two - Cast an advisory vote approving the Company’s executive compensation program. "
             "This proposal received 464,140,742 affirmative votes and 18,782,535 negative votes. There were")
TABLE_GEN = ("Proposal 3: Advisory vote to approve the Company’s executive compensation: Votes For Votes Against "
             "Abstentions Broker Non- Votes 209,903,985 307,097,626 430,536 28,340,494 The proposal was not approved.")
TABLE_DUOL = ("Proposal 3 — Approval, on an advisory (non-binding) basis, of the compensation of the Company's named "
              "executive officers. Votes FOR Votes AGAINST Votes ABSTAINED Broker Non-Votes 147,871,738 1,113,706 48,468")
TABLE_SKYW = ("2. The Company’s shareholders approved, on an advisory basis, the compensation of the Company’s named "
              "executive officers, based upon the following votes: Votes for approval 34,740,787 Votes against 622,058")


def test_say_on_pay_reads_all_four_real_formats():
    got = {k: E.say_on_pay_from_507(v) for k, v in
           dict(adbe=TABLE_ADBE, pgr=PROSE_PGR, gen=TABLE_GEN, duol=TABLE_DUOL, skyw=TABLE_SKYW).items()}
    assert got["adbe"]["for"] == 148_837_167 and got["adbe"]["against"] == 144_993_886
    assert abs(got["adbe"]["answer"] - 0.50654) < 1e-4
    assert (got["pgr"]["for"], got["pgr"]["against"]) == (464_140_742, 18_782_535)
    assert got["gen"]["answer"] < 0.5                         # GEN은 실제로 부결됐다
    assert got["duol"]["for"] == 147_871_738 and got["skyw"]["against"] == 622_058


def test_say_on_pay_ignores_frequency_vote():
    s = ("Advisory vote on the frequency of future advisory votes on executive compensation: "
         "One Year Two Years Three Years 1,200 3 4")
    assert E.say_on_pay_from_507(s)["answer"] is None


def test_say_on_pay_does_not_bind_a_distant_table_to_the_proposal_list():
    # UBER 실측: 안건 목록의 문장 뒤 멀리 있는 표는 다른 안건의 것이다 — 오연결 금지
    s = ("2. To approve, on a non-binding advisory basis, the 2025 compensation of the Company’s named executive "
         "officers . 3. To ratify the appointment of the independent registered public accounting firm for 2026 and "
         "to transact such other business as may properly come before the Meeting and any adjournment thereof. "
         "1. Election of Directors Nominee For Against Abstain Broker Non-Vote Votes 1,376,324,629 121,066,128")
    assert E.say_on_pay_from_507(s)["answer"] is None


def test_say_on_pay_support_excludes_abstentions():
    r = E.say_on_pay_from_507(TABLE_ADBE)
    assert abs(r["answer"] - 148_837_167 / (148_837_167 + 144_993_886)) < 1e-12


def test_zero_width_space_between_numbers_does_not_break_parsing():
    raw = "<p>Votes for approval ​ 34,740,787</p><p>Votes against ​ 622,058</p>"
    text = E.normalize_text("<p>on an advisory basis, the compensation of named executive officers: </p>" + raw)
    assert E.say_on_pay_from_507(text)["for"] == 34_740_787


def test_collect_say_on_pay_picks_latest_readable_and_quotes_verbatim():
    rows = [row("8-K", "2026-05-01", "5.07", "A"), row("8-K", "2026-09-01", "5.07", "B")]
    bodies = {"B": "<html>Item 5.07 Submission of Matters. Proposal: directors elected. Item 9.01</html>",
              "A": f"<html>Item 5.07 Submission of Matters. {TABLE_ADBE} Item 9.01</html>"}

    def fetch(url):
        # accession의 대시를 지우면 URL에 '0000000000A' / '0000000000B'가 남는다
        return bodies["A" if "0000000000A" in url else "B"]

    rows[0]["accessionNumber"], rows[1]["accessionNumber"] = "0000000000-A", "0000000000-B"
    out = E.collect_say_on_pay(listing(rows), fetch, "1", "2026-10-07")
    assert out["status"] == "OK" and out["accession"] == "0000000000-A"      # 최신(B)은 못 읽어 A로
    assert E.quote_in_text(out["result"]["excerpt"], E.normalize_text(bodies["A"]))


def test_collect_say_on_pay_no_507_is_not_an_answer():
    out = E.collect_say_on_pay(listing([row("8-K", "2026-01-01", "2.02")]), lambda u: "", "1", "2026-10-07")
    assert out["status"] == "OK" and out["result"] is None


# ③ 내부자 지분 ---------------------------------------------------------------------
def test_insider_group_star_means_less_than_one_percent():
    r = E.insider_group_from_proxy(
        "All directors and current executive officers as a group (18 persons) 803,767 (22) * ________ "
        "* Less than 1%. (1) The address")
    assert r["answer"] == "lt_1pct" and r["pct"] is None


def test_insider_group_numeric_percent_maps_to_band():
    for pct, band in (("0.4", "lt_1pct"), ("3.2", "1_to_5pct"), ("12.5", "5_to_20pct"), ("31", "gte_20pct")):
        r = E.insider_group_from_proxy(f"All directors and executive officers as a group (9 persons) 1,234,567 {pct}%")
        assert r["answer"] == band


def test_insider_group_multi_class_row_is_not_answered():
    # HLNE 실측: 주식 종류별 퍼센트가 여러 개 — 하나로 단정하면 거짓 정밀도
    r = E.insider_group_from_proxy(
        "All current executive officers and directors as a group (13 persons) 3,289,081 8% 9,951,470 84 % 64 % 25 %")
    assert r["answer"] is None and "다중" in r["reason"]


def test_insider_group_missing_row_is_not_answered():
    assert E.insider_group_from_proxy("no ownership table here")["answer"] is None


# ④ ICFR -----------------------------------------------------------------------------
def k10(sentence):
    return ("Item 9A. Controls and Procedures Evaluation of disclosure controls. " + sentence +
            " Item 9B. Other Information")


def test_icfr_reads_management_conclusion_both_ways():
    eff = E.icfr_from_10k(k10("Our management has concluded that, as of November 28, 2025, our internal control "
                              "over financial reporting is effective based on these criteria."))
    bad = E.icfr_from_10k(k10("management concluded that our internal control over financial reporting was not "
                              "effective as of December 31, 2025."))
    assert eff["answer"] == "effective" and bad["answer"] == "ineffective"


def test_icfr_ignores_hypothetical_risk_factor_language():
    # UBER 위험요인: 'if we identify one or more material weaknesses … we will be unable to assert … effective'
    body = ("Item 1A risk: if we identify one or more material weaknesses in our internal control over financial "
            "reporting, we will be unable to assert that our internal control over financial reporting is effective. "
            + k10("Management has concluded that our internal control over financial reporting was effective."))
    assert E.icfr_from_10k(body)["answer"] == "effective"
    assert E.icfr_from_10k("Item 1A if we identify a material weakness we will be unable to assert it is effective."
                           )["answer"] is None


def test_icfr_conflicting_conclusions_are_not_answered():
    s = k10("management concluded that our internal control over financial reporting was effective. "
            "Previously management concluded that our internal control over financial reporting was not effective.")
    assert E.icfr_from_10k(s)["answer"] is None


def test_icfr_without_conclusion_in_body_is_not_answered():
    r = E.icfr_from_10k(k10("The information is incorporated by reference to Exhibit 13."))
    assert r["answer"] is None and "Exhibit" in r["reason"]


# ⑤ 배당 --------------------------------------------------------------------------------
def test_dividend_true_only_for_five_consecutive_non_decreasing_years():
    r = E.dividend_predictable({2022: .5, 2023: .5, 2024: .5, 2025: .5, 2026: .5}, min_fy=2024)
    assert r["answer"] is True
    r = E.dividend_predictable({2022: .4, 2023: .45, 2024: .5, 2025: .55, 2026: .6}, min_fy=2024)
    assert r["answer"] is True


def test_dividend_decline_is_not_asserted_false():
    # PGR 실측: 연 변동 배당 — 특별배당 후 정상화를 '삭감'으로 단정하지 않는다
    r = E.dividend_predictable({2021: 1.9, 2022: 0.4, 2023: 1.15, 2024: 4.9, 2025: 13.9}, min_fy=2024)
    assert r["answer"] is None and r["declines"] == [(2022, 1.9, 0.4)]


def test_dividend_gaps_zero_and_stale_are_not_answered():
    assert E.dividend_predictable({2022: .5, 2023: .5, 2025: .5, 2026: .5, 2027: .5}, 2024)["answer"] is None
    assert E.dividend_predictable({2022: 0, 2023: .5, 2024: .5, 2025: .5, 2026: .5}, 2024)["answer"] is None
    assert E.dividend_predictable({2019: .5, 2020: .5, 2021: .5, 2022: .5, 2023: .5}, 2024)["answer"] is None


# ⑦ 새 질문은 은행에 있고 사실 질문이다 --------------------------------------------------------
def test_new_questions_are_in_bank_and_require_primary():
    for qid in ("gov.say_on_pay_support_pct", "gov.insider_group_ownership", "acc.icfr_conclusion",
                "acc.late_filing_nt_3y", "acc.auditor_change_3y", "acc.material_impairment_3y"):
        q = Q._BY_QID[qid]
        assert q.requires_primary, qid
    assert Q._BY_QID["acc.icfr_conclusion"].allowed == ("effective", "ineffective")


def test_new_functions_have_no_verdict_names():
    banned = ("decide", "verdict", "judge", "score", "rate", "grade", "recommend", "should", "flag_bad")
    tree = ast.parse(open(MODULE, encoding="utf-8").read())
    names = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
    for n in names:
        assert not any(b in n.lower() for b in banned), n


# v4.02 지분표 파서 개선 — 실측 행 형식 그대로 ------------------------------------------
def test_insider_group_row_without_as_a_group_acgl_ptc():
    r = E.insider_group_from_proxy(
        "Christine Todd (21) 251,580 * All directors and executive officers (17 persons) (22) 11,618,680 3.3% "
        "* Denotes beneficial ownership of less than 1%")
    assert r["answer"] == "1_to_5pct" and r["pct"] == 3.3
    r = E.insider_group_from_proxy(
        "Aaron von Staats 28,789 * All directors and executive officers ( 15 persons) 345,136 * * Less than 1%.")
    assert r["answer"] == "lt_1pct"


def test_insider_group_ignores_preferred_share_tables():
    body = ("All directors and executive officers (17 persons) (22) 11,618,680 3.3% * Denotes ... "
            "Number of Series G Preferred Shares Beneficially Owned Percentage of Class Owned Brian S. Posner 5,000 * "
            "All directors and executive officers (17 persons) 5,000 * * Denotes")
    r = E.insider_group_from_proxy(body)
    assert r["answer"] == "1_to_5pct"


def test_insider_group_trailing_next_row_tokens_deck_sigi():
    r = E.insider_group_from_proxy(
        "All Directors and Executive Officers as a Group (16 persons) 549,704 0.4 % 5% Stockholders BlackRock")
    assert r["answer"] == "lt_1pct" and r["pct"] == 0.4
    r = E.insider_group_from_proxy(
        "All directors and executive officers, as a group (17 persons) 490,429 1% * Less than 1% of the common")
    assert r["answer"] == "1_to_5pct"


def test_insider_group_narrative_sentence_is_not_a_row():
    r = E.insider_group_from_proxy(
        "and (3) all of the directors and executive officers of Arch Capital as a group. Except as otherwise")
    assert r["answer"] is None
