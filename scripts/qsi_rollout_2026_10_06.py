"""
QSI v1 확장 실행 — 확신 포트폴리오(reports/buylist_2026-09-06.json) 16종목, as_of 2026-10-06

파일럿(ACGL·DLO·PTC)은 형식 시험이었다. 이 스크립트는 같은 형식을 실제 매수 후보에 적용한다.

⚠️ 원칙 (파일럿보다 엄격하게)
  1. **모든 인용문은 코드가 원문과 대조한다.** `quote`는 실행 시 SEC에서 내려받은 문서 본문에
     글자 그대로(공백 정규화 후) 들어 있을 때만 통과한다. 사람이 옮겨 적다 틀리는 경로를 막는다.
  2. **SBC·희석주식수·준비금 발전은 사람이 숫자를 옮기지 않는다.** SEC companyfacts에서
     직접 계산한다. SBC/FCF 분모(fcf0)는 ledger 값이고, companyfacts SBC가 ledger의 SBC/FCF에서
     역산한 값과 0.5% 안에서 일치하는 연도만 인용한다(연도 어긋남 방지).
  3. 이번 세션에서 읽지 못한 질문은 `unknown` + 사유로 남긴다. **낮은 커버리지가 정상 출력이다.**
  4. ledger·thesis·holdings·공식 판정·매수리스트는 건드리지 않는다(병기).

실행: python -m scripts.qsi_rollout_2026_10_06 [--dry-run] [TICKER ...]
"""

import html
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from engine import dilution as D  # noqa: E402
from engine import qualitative_input as Q  # noqa: E402
from engine.filing_dates import _http_json, _http_text, fetch_company_facts  # noqa: E402

AS_OF = "2026-10-06"
SBC_TOL = 0.005                      # companyfacts SBC가 ledger 역산값과 맞아야 하는 허용오차
SBC_TAGS = ("ShareBasedCompensation", "AdjustmentsForSharebasedPayments")


# --- SEC 조회 -----------------------------------------------------------------
_TICKERS = None
_DOC = {}
_FACTS = {}


def cik_of(ticker):
    global _TICKERS
    if _TICKERS is None:
        raw = json.loads(_http_text("https://www.sec.gov/files/company_tickers.json"))
        _TICKERS = {v["ticker"]: str(v["cik_str"]).zfill(10) for v in raw.values()}
    return _TICKERS[ticker]


def facts_of(ticker):
    if ticker not in _FACTS:
        _FACTS[ticker] = fetch_company_facts(cik_of(ticker))
    return _FACTS[ticker]


def doc_of(ticker, form):
    """가장 최근 `form` 문서의 (설명, URL, 정규화된 본문)."""
    key = (ticker, form)
    if key in _DOC:
        return _DOC[key]
    cik = cik_of(ticker)
    sub = _http_json(f"https://data.sec.gov/submissions/CIK{cik}.json")["filings"]["recent"]
    for i, f in enumerate(sub["form"]):
        if f == form:
            acc = sub["accessionNumber"][i]
            url = (f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/"
                   f"{acc.replace('-', '')}/{sub['primaryDocument'][i]}")
            raw = re.sub(r"(?is)<(script|style).*?</\1>", " ", _http_text(url))
            body = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", raw)))
            label = f"{ticker} {form} (filed {sub['filingDate'][i]}, acc {acc})"
            _DOC[key] = (label, url, body)
            return _DOC[key]
    raise LookupError(f"{ticker}: {form} 문서를 찾지 못했다")


def _norm(s):
    return re.sub(r"\s+", " ", s).strip()


# --- 페이로드 부품 --------------------------------------------------------------
def cite(ticker, form, location, quote):
    """원문에 quote가 **그대로 있을 때만** 인용을 만든다. 없으면 즉시 예외."""
    label, url, body = doc_of(ticker, form)
    q = _norm(quote)
    if q not in body:
        raise ValueError(f"{ticker} {form}: 인용문이 원문에 없다 — {q[:80]!r}")
    return {"source_key": "sec_edgar", "document": label, "location": location,
            "observed_date": AS_OF, "url": url, "quote": q}


def ev(summary, citation, direction="supports", metric=None, value=None, note=""):
    return {"summary": summary, "direction": direction, "verification": "VERIFIED_PRIMARY",
            "confidence": "HIGH", "citation": citation, "metric": metric, "value": value,
            "note": note}


def claim(cid, statement, materiality, *evs):
    return {"claim_id": cid, "statement": statement, "materiality": materiality,
            "evidence": list(evs)}


def ans(qid, answer, *claim_ids, note=""):
    return {"qid": qid, "status": "answered", "answer": answer,
            "claim_ids": list(claim_ids), "note": note}


def unk(qid, note):
    return {"qid": qid, "status": "unknown", "note": note}


def finding(lens, effect, summary, *claim_ids):
    return {"lens": lens, "effect": effect, "summary": summary, "claim_ids": list(claim_ids)}


# --- 자동 산출(숫자를 사람이 옮기지 않는다) ----------------------------------------
def _ledger(ticker):
    import glob
    paths = sorted(glob.glob(os.path.join(ROOT, "ledger", f"{ticker}_*.json")))
    with open(paths[-1], encoding="utf-8") as f:
        return json.load(f)


def sbc_claim(ticker, form):
    """(claim|None, answer|unknown). SBC/FCF는 ledger 비율에서 역산한 SBC와 일치하는 연도만 인용."""
    led = _ledger(ticker)
    pct = (led.get("sbc_cross_check") or {}).get("sbc_to_fcf_pct")
    fcf0 = (led.get("derived") or {}).get("fcf0")
    if not pct or not fcf0:
        return None, unk("dil.sbc_to_fcf_pct", "ledger에 SBC/FCF가 없어 대조 기준이 없다")
    target = pct * fcf0
    facts = facts_of(ticker)
    best = None
    for tag in SBC_TAGS:
        for fy, rows in D.annual_facts(facts, tag).items():
            val = rows[-1][2]
            if target and abs(val - target) / target <= SBC_TOL:
                best = (tag, fy, val)
    if best is None:
        return None, unk("dil.sbc_to_fcf_pct",
                         "companyfacts SBC가 ledger SBC/FCF 역산값과 일치하는 연도가 없다 — "
                         "연도 정합을 증명하지 못해 인용하지 않는다")
    tag, fy, val = best
    label, url, _ = doc_of(ticker, form)
    c = claim(f"{ticker}.SBC", f"SBC가 FCF의 {pct:.1%}다", "HIGH", ev(
        f"FY{fy} SBC {val:,.0f} / fcf0 {fcf0:,.0f}",
        {"source_key": "sec_edgar", "document": label,
         "location": f"{tag} FY{fy} = {val:,.0f} (companyfacts)",
         "observed_date": AS_OF, "url": url, "quote": ""},
        metric="SBC/FCF", value=round(val / fcf0, 4),
        note="분모 fcf0는 IRS ledger 값. 분자는 companyfacts에서 직접 읽었고 ledger의 "
             "sbc_to_fcf_pct 역산값과 0.5% 안에서 일치하는 연도다"))
    return c, ans("dil.sbc_to_fcf_pct", round(val / fcf0, 4), f"{ticker}.SBC")


def shares_claim(ticker, form):
    facts = facts_of(ticker)
    for tag in D.SHARE_TAGS:
        per_year = D.annual_share_facts(facts, tag)
        if not per_year:
            continue
        end = max(per_year)
        base = end - 3
        if base not in per_year:
            continue
        coll = [y for y in D.detect_fy_label_collision(per_year) if base <= y <= end]
        if coll:
            return None, unk("dil.net_share_change_3y_pct",
                             f"회계연도 라벨 충돌 FY{coll} — 어느 해 값인지 특정할 수 없다(v3.61)")
        series, meta = D.consistent_share_series(per_year, base, end)
        jumps = D.structural_jumps(series, base, end)
        if jumps:
            return None, unk("dil.net_share_change_3y_pct",
                             f"정규화 후에도 구조적 점프 {jumps} — 분할·IPO·ADS 변경이 섞여 "
                             "희석을 재지 못한다(v3.84)")
        chg = series[end] / series[base] - 1
        label, url, _ = doc_of(ticker, form)
        c = claim(f"{ticker}.SHARES",
                  f"최근 3년 희석주식수 변화 {chg:+.2%}", "HIGH", ev(
                      f"가중평균 희석주식수 FY{base} {series[base]:,.0f} -> FY{end} {series[end]:,.0f}",
                      {"source_key": "sec_edgar", "document": label,
                       "location": f"{tag} FY{base}·FY{end} (companyfacts)",
                       "observed_date": AS_OF, "url": url, "quote": ""},
                      direction="supports" if chg <= 0 else "contradicts",
                      metric="net_share_change_3y", value=round(chg, 4),
                      note=f"분할 정규화: {'적용(' + meta.get('basis', '') + ')' if meta.get('adopted') else '불필요'}. "
                           "희석 가중평균은 주가에 따라 변하는 희석 증권 효과를 포함한다"))
        return c, ans("dil.net_share_change_3y_pct", round(chg, 4), f"{ticker}.SHARES")
    return None, unk("dil.net_share_change_3y_pct",
                     "companyfacts에 연차 희석주식수가 없다(다중클래스는 차원 데이터라 무차원 사실에 안 담긴다)")


BUYBACK_TAGS = ("PaymentsForRepurchaseOfCommonStock", "PaymentsToAcquireOrRedeemEntitysShares")
# 사전 고정 규칙 — 결과를 보고 조정하지 않는다. 3년 희석주식수 변화가 이 선을 넘으면
# '줄인다/늘었다'로 보고, 안쪽이면 매입이 희석 상쇄에 그친 것으로 본다.
BUYBACK_BAND = 0.01


def buyback_claim(ticker, form, shares_answer):
    """cap.buyback_effect — 자사주 매입액(SEC)과 이미 확인한 3년 주식수 변화를 결합한다.

    매입 지출이 없으면 질문 자체가 성립하지 않아 unknown. 규칙은 BUYBACK_BAND로 고정돼 있다.
    """
    if shares_answer.get("status") != "answered":
        return None, unk("cap.buyback_effect", "3년 주식수 변화를 확인하지 못해 판단하지 않는다")
    chg = shares_answer["answer"]
    facts = facts_of(ticker)
    spend = None
    for tag in BUYBACK_TAGS:
        per_year = {fy: rows[-1][2] for fy, rows in D.annual_facts(facts, tag).items()}
        if per_year:
            fy = max(per_year)
            spend = (tag, fy, per_year[fy])
            break
    if not spend or spend[2] <= 0:
        return None, unk("cap.buyback_effect", "최근 연차 자사주 매입 지출을 companyfacts에서 확인하지 못했다")
    tag, fy, amt = spend
    kind = ("share_count_rising" if chg >= BUYBACK_BAND else
            "reduces_share_count" if chg <= -BUYBACK_BAND else "offsets_dilution_only")
    label, url, _ = doc_of(ticker, form)
    c = claim(f"{ticker}.BUYBACK", f"자사주 매입 지출이 있으나 3년 주식수 변화는 {chg:+.2%}다 → {kind}", "HIGH",
              ev(f"FY{fy} 자사주 매입 {amt:,.0f}; 3년 희석주식수 {chg:+.2%}",
                 {"source_key": "sec_edgar", "document": label,
                  "location": f"{tag} FY{fy} = {amt:,.0f} (companyfacts)",
                  "observed_date": AS_OF, "url": url, "quote": ""},
                 direction="supports" if kind == "reduces_share_count" else "contradicts",
                 metric="buyback_spend", value=amt,
                 note=f"분류 규칙: 변화 ≥ +{BUYBACK_BAND:.0%} 증가, ≤ -{BUYBACK_BAND:.0%} 감소, 그 안쪽은 "
                      "상쇄에 그침. 임계값은 사전 고정이며 검증된 값이 아니다. 매입 자금의 출처(부채 여부)는 "
                      "확인하지 않았다"))
    return c, ans("cap.buyback_effect", kind, f"{ticker}.BUYBACK")


def reserve_claim(ticker, form):
    tag = ("SupplementalInformationForPropertyCasualtyInsuranceUnderwriters"
           "PriorYearClaimsAndClaimsAdjustmentExpense")
    per_year = {fy: rows[-1][2] for fy, rows in D.annual_facts(facts_of(ticker), tag).items()}
    years = sorted(per_year)[-3:]
    if len(years) < 3:
        return None, unk("res.reserve_development", "최근 3개 연도 전기 손해액 조정이 companyfacts에 없다")
    vals = [per_year[y] for y in years]
    kind = "favorable" if all(v < 0 for v in vals) else "adverse" if all(v > 0 for v in vals) else "neutral"
    label, url, _ = doc_of(ticker, form)
    c = claim(f"{ticker}.RESERVE", f"최근 3개 연도 준비금 발전: {kind}(부호가 연도마다 갈리면 neutral)", "HIGH", ev(
        "전기 손해액 조정 " + ", ".join(f"FY{y} {v/1e6:,.0f}M" for y, v in zip(years, vals)) +
        " (음수 = 비용 감소 = 유리한 발전)",
        {"source_key": "sec_edgar", "document": label,
         "location": f"us-gaap:{tag} FY{years[0]}~FY{years[-1]} (companyfacts)",
         "observed_date": AS_OF, "url": url, "quote": ""},
        metric="prior_year_claims_expense_usd", value=vals[-1],
        note="부호 해석(음수=유리)은 보험회계 관행이며 10-K MD&A 문장으로는 대조하지 않았다"))
    return c, ans("res.reserve_development", kind, f"{ticker}.RESERVE")


# --- 종목별 지배구조 사실(인용은 실행 시 원문 대조) ---------------------------------
P, K, F = "DEF 14A", "10-K", "20-F"

# (ticker, lens_set, 연차보고서 form, 위임장 form|None, gov 항목들)
# gov 항목: (qid, answer, claim_id, statement, form, location, quote, materiality, note)
GOV = {
    "PGR": ("insurance", K, P, [
        ("gov.chair_separated", True, "독립 의장이 이사회를 이끈다", P,
         "Proxy Summary — governance highlights", "Independent, experienced Chairperson", "MEDIUM", ""),
        ("gov.dual_class", False, "단일 클래스 의결권", P,
         "Proxy Summary — shareholder rights", "Single class voting", "HIGH", ""),
        ("gov.ceo_succession_policy", True, "후보 지명 위원회가 임원·이사 승계를 조율한다", P,
         "Board committees — Nominating and Governance",
         "Coordinates efforts relating to succession planning of executives and directors",
         "MEDIUM", "CEO를 명시하지 않고 '임원'으로 쓴다 — 약한 증거"),
    ]),
    "SIGI": ("insurance", K, P, [
        ("gov.chair_separated", False, "CEO가 이사회 의장을 겸한다(선임 독립이사가 균형)", P,
         "Board Leadership Structure",
         "for Mr. Marchioni to serve as both CEO and Board Chairperson", "MEDIUM", ""),
        ("gov.ceo_succession_policy", True, "보상 위원회가 임원 승계 계획을 검토한다", P,
         "Compensation Committee responsibilities",
         "review matters related to succession planning and professional development for executive officers",
         "MEDIUM", "CEO를 명시하지 않고 '임원'으로 쓴다 — 약한 증거"),
    ]),
    "CINF": ("insurance", K, P, [
        ("gov.chair_separated", True, "이사회가 의장·CEO를 분리하기로 결정했다(2024)", P,
         "Corporate Governance — Board Leadership",
         "the offices of chairman of the board and CEO would be split following the 2024 annual shareholders' meeting",
         "MEDIUM", "2024년 결정 문장이다. 현재 직책은 같은 문서의 이사 표(Executive Chairman)로 보강"),
        ("gov.ceo_succession_policy", True, "분리 결정을 승계 계획 과정의 일부로 설명한다", P,
         "Corporate Governance — Board Leadership",
         "is part of the succession planning process", "MEDIUM", ""),
    ]),
    "DUOL": ("standard", K, P, [
        ("gov.dual_class", True, "Class B 주식이 20표를 갖는다", P,
         "Proxy — voting rights note", "each share of Class B common stock is entitled to 20 votes",
         "HIGH", "경제적 권리는 동일(투표·전환권만 상이)"),
        ("gov.ceo_succession_policy", True, "위원회가 핵심 임원 승계 계획을 감독한다", P,
         "Corporate Governance — committee responsibilities",
         "overseeing succession planning for key executives", "MEDIUM", ""),
    ]),
    "NBIX": ("standard", K, P, [
        ("gov.chair_separated", True, "의장과 CEO가 분리돼 있다", P,
         "Proxy Summary — governance highlights", "Separate Chairman and CEO", "MEDIUM", ""),
        ("gov.ceo_succession_policy", True, "이사회가 CEO·경영진 승계 계획을 핵심 책임으로 둔다", P,
         "Role of the Board in Succession Planning",
         "A key responsibility of the Board is succession planning for the CEO and other members "
         "of the executive management team", "MEDIUM", ""),
    ]),
    "HLNE": ("standard", K, P, [
        ("gov.dual_class", True, "Class B 주식이 10표를 갖는다", P,
         "Proxy — voting rights",
         "each share of Class B common stock is entitled to ten votes per share",
         "HIGH", "일몰(Sunset) 조항이 있으나 아직 발동하지 않았다고 문서가 명시한다"),
    ]),
    "DECK": ("standard", K, P, [
        ("gov.chair_separated", True, "독립이사가 이사회 의장이다", P,
         "Board Leadership", "independent director, serves as Chair of the Board", "MEDIUM",
         "의장이 독립이사라고 서술 — CEO와 분리를 함의"),
    ]),
    "UBER": ("standard", K, P, [
        ("gov.chair_separated", True, "독립 의장이 이사회를 이끈다", P,
         "Letter to shareholders — signature", "Independent Chairperson of the Board of Directors",
         "MEDIUM", ""),
        ("gov.ceo_succession_policy", True, "이사회가 경영진 승계 계획을 감독한다", P,
         "Proxy Summary — governance highlights",
         "Board oversight of management succession planning", "MEDIUM", "'경영진'으로 서술 — 약한 증거"),
    ]),
    "ADBE": ("standard", K, P, [
        ("gov.chair_separated", False, "의장과 CEO가 같은 사람이다", P,
         "Directors table", "Chair of the Board and CEO, Adobe", "MEDIUM",
         "독립 선임이사를 두는 규정은 별도로 존재(미대조)"),
        ("gov.ceo_succession_policy", True, "이사회가 CEO 승계 계획을 검토한다", P,
         "Board responsibilities",
         "management development and succession planning for senior management, including the CEO position",
         "MEDIUM", ""),
    ]),
    "SKYW": ("standard", K, P, [
        ("gov.chair_separated", True, "의장(Welch)은 퇴직한 타사 CEO다 — 자사 임원이 아니다", P,
         "Director nominees — James L. Welch", "Principal Occupation: Retired CEO of YRC Worldwide Inc.",
         "MEDIUM", "자사 CEO가 별도 인물임을 직접 확인한 문장은 아니다"),
        ("gov.ceo_succession_policy", True, "위원회가 CEO 평가와 장기 승계 계획을 검토한다", P,
         "CEO Evaluation and Management Succession",
         "as well as the Company’s long-term succession plans", "MEDIUM", ""),
    ]),
    "NXT": ("standard", K, P, [
        ("gov.ceo_succession_policy", True, "이사회가 CEO 승계(임시·비상 승계 포함)를 계획한다", P,
         "Board responsibilities",
         "working with the Chief Executive Officer to plan for the succession of the Chief Executive Officer",
         "MEDIUM", ""),
    ]),
    "TW": ("standard", K, P, [
        ("gov.dual_class", True, "Class B·D 주식이 10표를 갖는다", P,
         "Proxy — voting rights",
         "Each share of Class B common stock and Class D common stock entitles its holder to 10 votes",
         "HIGH", "Class C·D는 경제적 권리가 없는 의결권 전용 주식이다(2026-09-03 별도 확인)"),
    ]),
    "GEN": ("standard", K, P, [
        ("gov.chair_separated", False, "FY26부터 CEO와 의장 역할을 합쳤다", P,
         "Board leadership",
         "the Board decided it was in the best interest of the Company to combine the CEO and Chair roles in FY26",
         "MEDIUM", "선임 독립이사(LID)를 지정해 균형 장치를 둔다고 서술"),
    ]),
    # 20-F 발행사 — 위임장이 없다. 의결권 구조는 20-F 본문에서 확인한다.
    "SE": ("standard", F, None, [
        ("gov.dual_class", True, "Class B 주식이 15표를 갖고 창업자가 전량 보유한다", F,
         "Item 7 Major Shareholders",
         "holders of Class B ordinary shares are entitled to 15 votes per share", "HIGH",
         "창업자 Forrest Li가 총 의결권의 약 57.6%를 갖는다고 같은 문서가 서술"),
        ("gov.chair_separated", False, "창업자가 의장과 CEO를 겸한다", F,
         "Item 3 Risk Factors — controlled structure",
         "our founder, Chairman and Chief Executive Officer", "MEDIUM", ""),
    ]),
    "PDD": ("standard", F, None, [
        ("gov.dual_class", True, "Class B 주식이 10표를 갖는다", F,
         "Item 10 Description of Share Capital",
         "each Class B ordinary share shall entitle the holder thereof to ten (10) votes", "HIGH", ""),
    ]),
    "MNDY": ("standard", F, None, [
        ("gov.dual_class", False, "보통주 1종이며 1주 1표다", F,
         "Note 13 Shareholders’ equity",
         "The holders of ordinary shares are entitled to one vote per share", "HIGH",
         "재무제표 주석 문장으로 단일 클래스를 확인했다. 정관 원문은 대조하지 않았다"),
    ]),
}

# 같은 이사 표의 보강 증거(CINF)
EXTRA = {"CINF": [("gov.chair_separated", "CINF.CHAIR2",
                   "현 의장은 Executive Chairman 직함의 이사다", P,
                   "Director table", "Executive Chairman of the Board, Cincinnati Financial Corporation")]}


def build(ticker):
    lens_set, annual, proxy, gov = GOV[ticker]
    claims, answers = [], []
    for i, (qid, value, stmt, form, loc, quote, mat, note) in enumerate(gov, 1):
        cid = f"{ticker}.{qid.split('.')[1].upper()}"
        claims.append(claim(cid, stmt, mat, ev(stmt, cite(ticker, form, loc, quote), note=note)))
        answers.append(ans(qid, value, cid))
    for qid, cid, stmt, form, loc, quote in EXTRA.get(ticker, []):
        claims.append(claim(cid, stmt, "MEDIUM", ev(stmt, cite(ticker, form, loc, quote))))
        for a in answers:
            if a["qid"] == qid:
                a["claim_ids"].append(cid)

    answered = {a["qid"] for a in answers}
    shares_ans = None
    for fn in (sbc_claim, shares_claim):
        c, a = fn(ticker, annual)
        if c:
            claims.append(c)
        answers.append(a)
        answered.add(a["qid"])
        if fn is shares_claim:
            shares_ans = a
    if lens_set == "standard":
        c, a = buyback_claim(ticker, annual, shares_ans)
        if c:
            claims.append(c)
        answers.append(a)
        answered.add(a["qid"])
    if lens_set == "insurance":
        c, a = reserve_claim(ticker, annual)
        if c:
            claims.append(c)
        answers.append(a)
        answered.add(a["qid"])

    # 은행에 있으나 답하지 못한 질문은 전부 unknown으로 명시한다(조용히 빠지지 않게).
    for q in Q.bank_for(lens_set):
        if q.qid not in answered:
            answers.append(unk(q.qid, "이번 회차에서 1차 출처를 조회하지 않았다"))

    findings = []
    got = {c["claim_id"] for c in claims}
    sbc_ids = [x for x in (f"{ticker}.SBC", f"{ticker}.SHARES") if x in got]
    if f"{ticker}.BUYBACK" in got:
        findings.append(finding("capital_allocation", "neutral",
                                "자사주 매입 지출과 3년 주식수 변화를 결합(자금 출처·M&A 규율은 미확인)",
                                f"{ticker}.BUYBACK"))
    if sbc_ids:
        findings.append(finding("dilution", "neutral",
                                "SBC/FCF와 3년 희석주식수를 SEC 원자료로 확인(방향 판단은 수치 참조)", *sbc_ids))
    gov_ids = [c["claim_id"] for c in claims if c["claim_id"].split(".")[1] in
               ("CHAIR_SEPARATED", "DUAL_CLASS", "CEO_SUCCESSION_POLICY", "CHAIR2")]
    if gov_ids:
        findings.append(finding("governance", "neutral",
                                "의결권 구조·의장 분리·승계 감독만 확인. 내부자·소송은 미확인",
                                *gov_ids))
    if f"{ticker}.RESERVE" in got:
        findings.append(finding("reserve_adequacy", "neutral",
                                "3개 연도 전기 손해액 조정 부호를 확인", f"{ticker}.RESERVE"))

    return {"entity": ticker, "as_of": AS_OF, "lens_set": lens_set,
            "price_at_analysis": None, "currency": "USD",
            "claims": claims, "answers": answers, "findings": findings,
            "disqualifiers": [],
            "inversion": ["이번 회차는 지배구조·희석 사실 확인에 한정했다 — 사업 붕괴 시나리오는 미조사"],
            "confidence_recommendation": None}


def main(argv):
    dry = "--dry-run" in argv
    tickers = [a for a in argv if not a.startswith("--")] or list(GOV)
    for t in tickers:
        rec = Q.build_record(build(t))
        c = rec["coverage"]
        print(f"{t:5} 답 {c['n_answered']:>2}/{c['n_questions']:<2} 해시 {rec['sealed_core_hash'][:10]}")
        if not dry:
            print("      ->", os.path.relpath(Q.save_record(rec), ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
