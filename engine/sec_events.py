"""
SEC 이벤트 수집기 (v3.94) — 정성평가 표준입력(QSI v1)의 `unknown`을 1차 출처로 채운다.

# 왜 만들었나
QSI 확장(2026-10-06)에서 답한 질문이 9~45%에 머문 이유는 판단이 어려워서가 아니라
**수집 경로가 없어서**였다. 내부자 매매·재작성·임원 교체·소송은 판단 이전에 SEC가 공시한
사실이고, 규칙대로 뽑을 수 있다. 이 모듈은 그 사실만 뽑는다.

# 하지 않는 것 (전부 테스트로 고정)
  - **좋고 나쁨을 판정하지 않는다.** 답은 사전 고정 규칙이 낳는 열거값이거나, 규칙이
    답하지 못하면 `None`이다. 종합점수·등급·"반증 확정" 류 함수 없음(§31).
  - **사람이 숫자를 옮기지 않는다.** Form 4 XML·8-K 본문에서 직접 읽고, 인용문은 원문에
    글자 그대로 있을 때만 만든다(`quote_in_text`).
  - **데이터 없음을 '문제 없음'으로 오독하지 않는다.** 제출 목록이 조회 창을 덮는지 먼저
    증명하고, 덮지 못하면 부재 주장 자체를 하지 않는다(`covers_window`).
  - 20-F/6-K 발행사는 Form 4·8-K 의무가 없다 — 그 사실을 `UNAVAILABLE`로 돌려준다(오탐 방지).
  - 판정·비중·`run_analysis()`에 배선하지 않는다.

# ⚠️ 사전 고정 규칙 (검증된 값이 아니다 — 결과를 보고 조정하지 않는다)
  - 공개시장 거래 = 거래코드 P(매수)·S(매도)만. 부여(A)·옵션행사(M)·세금원천징수(F)·증여(G)는 제외.
  - 정기 거래 = Form 4의 10b5-1 체크박스(`aff10b5One`) 또는 각주의 '10b5-1' 언급.
  - 재량 순거래액 절댓값이 `OPP_FLOOR_USD` 미만이면 '기회적'으로 보지 않는다.
  - CEO/CFO 교체 = 8-K Item 5.02 본문에서 직책과 이직 동사가 같은 문장에 있는 경우.

# 알려진 한계
  - Form 4 파싱은 비파생 거래(`nonDerivativeTransaction`)만 본다. 파생증권 거래는 제외.
  - 'little r' 재작성(이전 연도 수치만 조용히 수정)은 8-K 4.02가 없어 탐지하지 못한다.
  - 소송은 Item 3 본문이 '해당 없음'이라고 *회사가 직접 쓴* 경우만 답한다(중요성 한정이 있으면 `immaterial`).
    'Note 참조' 식 서술은 심각도를 판단하지 않고 `None`을 돌려준다.

# TEST:
tests/test_sec_events.py
"""

import datetime
import html
import re
import xml.etree.ElementTree as ET

VALIDATION_STATUS = (
    "IMPLEMENTED_NOT_VALIDATED — 규칙은 사전 고정이며 실현 결과와 대조된 적이 없다. "
    "수집된 사실의 정확성(원문 일치)과 규칙이 가리키는 방향의 정당성은 별개다."
)

OPEN_MARKET_CODES = ("P", "S")
OPP_FLOOR_USD = 1_000_000          # 재량 순거래액이 이보다 작으면 기회적으로 보지 않는다(비검증)
INSIDER_WINDOW_DAYS = 365
CXO_WINDOW_DAYS = 730
RESTATEMENT_WINDOW_DAYS = 1095
FORM4_MAX = 400                    # 한 종목 조회 상한 — 넘으면 조용히 자르지 않고 UNAVAILABLE

SEC_ARCHIVE = "https://www.sec.gov/Archives/edgar/data/{cik}/{acc}/{doc}"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
SUBMISSIONS_PAGE_URL = "https://data.sec.gov/submissions/{name}"

UNAVAILABLE = "UNAVAILABLE"


class SecEventsError(ValueError):
    """수집 계약 위반."""


# --- 제출 목록 -------------------------------------------------------------------

def _rows(block: dict) -> list:
    n = len(block.get("form", []))
    keys = ("accessionNumber", "filingDate", "form", "items", "primaryDocument")
    return [{k: (block.get(k) or [""] * n)[i] for k in keys} for i in range(n)]


def list_filings(cik: str, since: str, fetch_json) -> dict:
    """
    `since`(ISO) 이후 제출 목록과, 그 창을 **완전히 덮었는지** 여부.

    submissions의 `recent`는 최근 약 1000건뿐이라 제출이 많은 회사는 3년 창이 잘린다.
    덮지 못하면 부재(없다) 주장이 거짓이 되므로 `files` 페이지를 더 읽고, 그래도 못 덮으면
    `covers_window=False`로 돌려준다.
    """
    cik10 = str(cik).zfill(10)
    top = fetch_json(SUBMISSIONS_URL.format(cik=cik10))
    rows = _rows(top["filings"]["recent"])
    pages = list(top["filings"].get("files") or [])
    oldest = min((r["filingDate"] for r in rows), default=None)
    while oldest is not None and oldest > since and pages:
        page = pages.pop(0)
        more = _rows(fetch_json(SUBMISSIONS_PAGE_URL.format(name=page["name"])))
        rows.extend(more)
        oldest = min((r["filingDate"] for r in rows), default=oldest)
    exhausted = not pages
    # 덮음 = 창 시작 이전 제출까지 읽었거나, 페이지를 모두 읽어 **전체 이력**을 확보한 경우
    # (상장 이력이 창보다 짧은 회사). 비어 있는 목록은 덮은 것이 아니다.
    covers = oldest is not None and (oldest <= since or exhausted)
    return {"cik": cik10, "rows": [r for r in rows if r["filingDate"] >= since],
            "covers_window": bool(covers), "oldest_seen": oldest,
            "all_forms": sorted({r["form"] for r in rows})}


def is_foreign_private_issuer(all_forms) -> bool:
    """20-F/40-F를 내고 10-K는 없으면 외국 발행사다 — Section 16·8-K 의무 밖.

    ⚠️ Form 4/8-K가 보인다고 국내 발행사로 취급하면 안 된다(실측: DLO·MNDY·PDD·SE는 20-F
    발행사인데 자발적·제3자 Form 4가 5~200건 섞여 있다). 그 일부로 '정기 거래만'이라 답하면
    내부자 매매 전체를 본 것처럼 오독된다.
    """
    s = set(all_forms)
    return bool(s & {"20-F", "40-F"}) and "10-K" not in s


def filing_url(cik: str, row: dict, raw_xml: bool = False) -> str:
    doc = row["primaryDocument"]
    if raw_xml:
        doc = doc.rsplit("/", 1)[-1]          # xslF345X06/form4.xml -> form4.xml (원본 XML)
    return SEC_ARCHIVE.format(cik=int(cik), acc=row["accessionNumber"].replace("-", ""), doc=doc)


# --- 본문 정규화 / 인용 ------------------------------------------------------------

def normalize_text(raw: str) -> str:
    raw = re.sub(r"(?is)<(script|style).*?</\1>", " ", raw)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", raw))).strip()


def quote_in_text(quote: str, body: str) -> bool:
    return re.sub(r"\s+", " ", quote).strip() in body


# --- Form 4 ------------------------------------------------------------------------

def _t(node, path):
    el = node.find(path)
    return el.text.strip() if el is not None and el.text else None


def parse_form4(xml_text: str) -> list:
    """Form 4 XML -> 비파생 거래 목록. 거래가 없으면 빈 리스트."""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        raise SecEventsError(f"Form 4 XML 파싱 실패: {e}")
    flag_10b5 = (_t(root, "aff10b5One") or "").lower() in ("1", "true")
    issuer_cik = (_t(root, "issuer/issuerCik") or "").lstrip("0")
    owners = []
    for ro in root.findall("reportingOwner"):
        rel = ro.find("reportingOwnerRelationship")
        owners.append({
            "name": _t(ro, "reportingOwnerId/rptOwnerName") or "미확인",
            "is_officer": (_t(rel, "isOfficer") or "0") in ("1", "true") if rel is not None else False,
            "is_director": (_t(rel, "isDirector") or "0") in ("1", "true") if rel is not None else False,
            "title": _t(rel, "officerTitle") if rel is not None else None,
        })
    foot = " ".join((f.text or "") for f in root.findall("footnotes/footnote"))
    footnote_10b5 = bool(re.search(r"10b5-?1", foot, re.I))
    out = []
    for tx in root.findall("nonDerivativeTable/nonDerivativeTransaction"):
        code = _t(tx, "transactionCoding/transactionCode")
        shares = _t(tx, "transactionAmounts/transactionShares/value")
        price = _t(tx, "transactionAmounts/transactionPricePerShare/value")
        try:
            sh = float(shares) if shares else 0.0
            px = float(price) if price else 0.0
        except ValueError:
            continue
        out.append({
            "date": _t(tx, "transactionDate/value"), "code": code, "shares": sh, "price": px,
            "value_usd": sh * px,
            "acq_disp": _t(tx, "transactionAmounts/transactionAcquiredDisposedCode/value"),
            "is_10b5_1": flag_10b5 or footnote_10b5,
            "issuer_cik": issuer_cik,
            "owner": owners[0]["name"] if owners else "미확인",
            "is_officer": any(o["is_officer"] for o in owners),
            "is_director": any(o["is_director"] for o in owners),
            "title": next((o["title"] for o in owners if o["title"]), None),
        })
    return out


def summarize_insider(txs: list, since: str, until: str, floor: float = OPP_FLOOR_USD) -> dict:
    """
    사전 고정 규칙으로 `gov.insider_pattern` 열거값을 낸다.
    입력은 `parse_form4` 결과의 합. **판단하지 않고 규칙을 적용한다.**
    """
    om = [t for t in txs if t["code"] in OPEN_MARKET_CODES and t["date"]
          and since <= t["date"] <= until and t["value_usd"] > 0]

    def signed(t):
        return t["value_usd"] if t["code"] == "P" else -t["value_usd"]

    disc = [t for t in om if not t["is_10b5_1"]]
    routine = [t for t in om if t["is_10b5_1"]]
    net_disc = sum(signed(t) for t in disc)
    if not om:
        answer = "none"
    elif not disc:
        answer = "routine_only"
    elif abs(net_disc) < floor:
        answer = "routine_only"
    else:
        answer = "opp_net_buy" if net_disc > 0 else "opp_net_sell"
    by_owner = {}
    for t in disc:
        by_owner[t["owner"]] = by_owner.get(t["owner"], 0.0) + signed(t)
    return {
        "answer": answer, "n_open_market": len(om), "n_discretionary": len(disc),
        "n_routine_10b5_1": len(routine),
        "discretionary_net_usd": round(net_disc, 2),
        "discretionary_buy_usd": round(sum(t["value_usd"] for t in disc if t["code"] == "P"), 2),
        "discretionary_sell_usd": round(sum(t["value_usd"] for t in disc if t["code"] == "S"), 2),
        "routine_sell_usd": round(sum(t["value_usd"] for t in routine if t["code"] == "S"), 2),
        "discretionary_net_by_owner": {k: round(v, 2) for k, v in sorted(by_owner.items(), key=lambda kv: kv[1])},
        "floor_usd": floor,
        "rule": ("공개시장 P/S만, 10b5-1 표시(체크박스·각주) 제외, 재량 순거래액 절댓값이 "
                 f"${floor:,.0f} 미만이면 기회적으로 보지 않는다(사전 고정·비검증)"),
    }


def collect_insider(listing: dict, fetch_text, as_of: str) -> dict:
    """
    Form 4를 읽어 요약한다. 반환 `status`:
      OK / UNAVAILABLE(외국 발행사·창 미충족·상한 초과) — 이유는 `reason`.
    """
    if is_foreign_private_issuer(listing["all_forms"]):
        return {"status": UNAVAILABLE, "reason": "20-F/6-K 발행사 — Section 16 Form 4 의무가 없다"}
    since = (datetime.date.fromisoformat(as_of) - datetime.timedelta(days=INSIDER_WINDOW_DAYS)).isoformat()
    if not listing["covers_window"]:
        return {"status": UNAVAILABLE, "reason": "제출 목록이 12개월 창을 덮지 못해 부재 판단 불가"}
    rows = [r for r in listing["rows"] if r["form"] == "4" and r["filingDate"] >= since]
    if len(rows) > FORM4_MAX:
        return {"status": UNAVAILABLE,
                "reason": f"Form 4가 {len(rows)}건으로 상한 {FORM4_MAX}를 넘는다 — 일부만 읽고 결론내지 않는다"}
    txs, accs, failed, foreign_issuer = [], [], [], 0
    want_cik = str(int(listing["cik"]))
    for r in rows:
        try:
            parsed = parse_form4(fetch_text(filing_url(listing["cik"], r, raw_xml=True)))
        except Exception as e:  # 개별 파일 실패는 숨기지 않고 센다
            failed.append({"accession": r["accessionNumber"], "error": f"{type(e).__name__}: {e}"})
            continue
        # 제출 목록에는 회사가 **다른 발행사 지분을 거래했다고 낸** Form 4도 섞인다(실측: UBER가
        # 타사 지분 $11억 매도). 발행사가 이 회사인 거래만 내부자 매매다.
        mine = [t for t in parsed if t["issuer_cik"] == want_cik]
        foreign_issuer += len(parsed) - len(mine)
        accs.append(r["accessionNumber"])
        txs.extend(mine)
    if failed:
        return {"status": UNAVAILABLE, "reason": f"Form 4 {len(failed)}건 읽기 실패 — 부분 결과로 답하지 않는다",
                "failed": failed[:5]}
    summ = summarize_insider(txs, since, as_of)
    return {"status": "OK", "window": [since, as_of], "n_form4_filings": len(rows),
            "summary": summ, "accessions": accs,
            "excluded_other_issuer_transactions": foreign_issuer}


# --- 8-K 항목 ----------------------------------------------------------------------

def rows_with_item(listing: dict, item: str, since: str, forms=("8-K", "8-K/A")) -> list:
    out = []
    for r in listing["rows"]:
        if r["form"] in forms and r["filingDate"] >= since and \
                item in [x.strip() for x in (r["items"] or "").split(",")]:
            out.append(r)
    return out


def item_section(body: str, item: str) -> str:
    """정규화된 8-K 본문에서 `Item X.XX` 절. 목차·표지의 언급이 아니라 **본문**을 고른다."""
    marks = [m.start() for m in re.finditer(rf"Item\s+{re.escape(item)}\b", body, re.I)]
    best = ""
    for s in marks:
        nxt = re.search(r"Item\s+\d\.\d\d\b", body[s + 8:], re.I)
        e = s + 8 + nxt.start() if nxt else len(body)
        if e - s > len(best):
            best = body[s:e]
    return best


_TITLE = re.compile(r"(Chief Executive Officer|Chief Financial Officer|\bCEO\b|\bCFO\b)", re.I)
_LEAVE = re.compile(r"(resign|step(?:s|ping)? down|retire|terminat|depart|will leave|leave the Company"
                    r"|separation|no longer serve)", re.I)
_JOIN = re.compile(r"(appoint|named|elected|succeed|interim|will serve as)", re.I)


def cxo_sentences(section: str) -> list:
    """직책과 이직(또는 선임) 동사가 한 문장에 함께 있는 문장. 문장은 원문 그대로."""
    out = []
    for s in re.split(r"(?<=[.!?])\s+", section):
        if _TITLE.search(s) and (_LEAVE.search(s) or _JOIN.search(s)) and 20 <= len(s) <= 700:
            out.append({"sentence": s.strip(), "departure": bool(_LEAVE.search(s)),
                        "appointment": bool(_JOIN.search(s))})
    return out


def collect_cxo(listing: dict, fetch_text, cik: str, as_of: str) -> dict:
    if is_foreign_private_issuer(listing["all_forms"]):
        return {"status": UNAVAILABLE, "reason": "20-F/6-K 발행사 — 8-K Item 5.02 의무가 없다"}
    since = (datetime.date.fromisoformat(as_of) - datetime.timedelta(days=CXO_WINDOW_DAYS)).isoformat()
    if not listing["covers_window"]:
        return {"status": UNAVAILABLE, "reason": "제출 목록이 24개월 창을 덮지 못해 부재 판단 불가"}
    events, n_502 = [], 0
    for r in rows_with_item(listing, "5.02", since):
        n_502 += 1
        url = filing_url(cik, r)
        try:
            body = normalize_text(fetch_text(url))
        except Exception as e:
            return {"status": UNAVAILABLE, "reason": f"8-K 본문 읽기 실패({r['accessionNumber']}): {e}"}
        sents = [s for s in cxo_sentences(item_section(body, "5.02")) if s["departure"]]
        if sents:
            s = sents[0]["sentence"]
            if not quote_in_text(s, body):
                continue
            events.append({"filing_date": r["filingDate"], "accession": r["accessionNumber"],
                           "url": url, "quote": s})
    return {"status": "OK", "window_since": since, "n_item_502_filings": n_502,
            "n_cxo_departure_filings": len(events), "events": events}


def collect_restatement(listing: dict, as_of: str) -> dict:
    """8-K Item 4.02(비신뢰 통지)와 10-K/A 존재 여부. 존재하면 판단하지 않고 사실만."""
    if is_foreign_private_issuer(listing["all_forms"]):
        return {"status": UNAVAILABLE, "reason": "20-F/6-K 발행사 — 8-K Item 4.02 의무가 없다"}
    since = (datetime.date.fromisoformat(as_of) - datetime.timedelta(days=RESTATEMENT_WINDOW_DAYS)).isoformat()
    if not listing["covers_window"]:
        return {"status": UNAVAILABLE, "reason": "제출 목록이 3년 창을 덮지 못해 부재 판단 불가"}
    nonrel = rows_with_item(listing, "4.02", since)
    amend = [r for r in listing["rows"] if r["form"] == "10-K/A" and r["filingDate"] >= since]
    return {"status": "OK", "window_since": since,
            "n_item_402": len(nonrel), "item_402": [r["filingDate"] for r in nonrel],
            "n_10k_amendments": len(amend), "10k_amendments": [r["filingDate"] for r in amend]}


# --- 소송(10-K Item 3) ---------------------------------------------------------------

_NONE_STMT = re.compile(
    r"(?:are|is|were)\s+not\s+(?:currently\s+)?(?:a\s+)?(?:party|subject)\s+to\s+"
    r"(?:any|material)[^.]{0,120}(?:legal|litigation|proceeding)[^.]*\.", re.I)
_MATERIAL_QUAL = re.compile(r"(material|adverse|significant|expected)", re.I)
_NOTE_REF = re.compile(r"\b(Note\s+\d+|Commitments and Contingencies|Contingencies)\b", re.I)


def litigation_from_item3(body: str) -> dict:
    """
    10-K 본문에서 Item 3. 회사가 **직접** '해당 소송 없음'이라 쓴 경우만 `none`.
    그 밖에는 심각도를 판단하지 않고 발췌만 돌려준다(answer=None).
    """
    marks = [m.start() for m in re.finditer(r"Item\s+3\s*[.:\-\u2014\u2013]?\s*Legal\s+Proceedings", body, re.I)]
    best = ""
    for s in marks:
        nxt = re.search(r"Item\s+4\s*[.:\-\u2014\u2013]?\s*Mine\s+Safety", body[s + 10:], re.I)
        e = s + 10 + nxt.start() if nxt else min(len(body), s + 3000)
        if e - s > len(best):
            best = body[s:e]
    if not best:
        return {"answer": None, "reason": "Item 3 절을 찾지 못했다", "excerpt": None}
    m = _NONE_STMT.search(best)
    if m and not _NOTE_REF.search(best[:m.end() + 400]):
        # '중요한 악영향이 예상되는 소송이 없다'처럼 **중요성으로 한정**된 진술은 소송이 아예 없다는
        # 뜻이 아니다(실측: ACGL). 한정이 있으면 immaterial — 거짓 청정 신호를 만들지 않는다.
        qualified = bool(_MATERIAL_QUAL.search(m.group(0)))
        return {"answer": "immaterial" if qualified else "none", "excerpt": m.group(0).strip(),
                "section_len": len(best), "materiality_qualified": qualified,
                "reason": ("회사가 '중요한(material) 소송이 없다'고 한정해 진술 — 소송 존재 여부는 말하지 않는다"
                           if qualified else "회사가 Item 3에서 해당 소송이 없다고 직접 진술")}
    ex = best[:700].strip()
    return {"answer": None, "excerpt": ex, "section_len": len(best),
            "reason": "회사 서술이 Note 참조이거나 소송을 기술한다 — 심각도는 사람이 판단한다"}


# --- 자사주 매입 재원 ----------------------------------------------------------------

DEBT_ISSUE_TAGS = ("ProceedsFromIssuanceOfLongTermDebt", "ProceedsFromIssuanceOfDebt",
                   "ProceedsFromIssuanceOfSeniorLongTermDebt", "ProceedsFromNotesPayable")
DEBT_REPAY_TAGS = ("RepaymentsOfLongTermDebt", "RepaymentsOfDebt", "RepaymentsOfSeniorDebt",
                   "RepaymentsOfNotesPayable")
BUYBACK_TAGS = ("PaymentsForRepurchaseOfCommonStock", "PaymentsToAcquireOrRedeemEntitysShares")
DEBT_FUNDED_RATIO = 0.5     # 순차입이 매입액의 이 비율 이상이면 부채 조달로 본다(사전 고정·비검증)


def debt_funded_buyback(issue: dict, repay: dict, buyback: dict, min_fy: int = None) -> dict:
    """
    같은 회계연도의 순차입(발행−상환)과 자사주 매입액을 비교.
    입력은 {fy: 금액}. 순차입이 매입액의 `DEBT_FUNDED_RATIO` 이상이면 True.
    발행 또는 매입 값이 없거나 `min_fy`보다 낡으면 `None`(모른다).
    """
    years = sorted(set(buyback) & set(issue))
    if not years:
        return {"answer": None, "reason": "같은 회계연도의 차입 발행·매입 값이 없다"}
    fy = years[-1]
    if min_fy is not None and fy < min_fy:
        return {"answer": None, "reason": f"가장 최근 공통 회계연도가 FY{fy}로 낡았다(FY{min_fy} 이후 필요)"}
    net = issue[fy] - repay.get(fy, 0.0)
    spend = buyback[fy]
    if spend <= 0:
        return {"answer": None, "reason": "해당 연도 매입 지출이 없다"}
    return {"answer": bool(net > 0 and net >= DEBT_FUNDED_RATIO * spend), "fy": fy,
            "net_debt_issuance": net, "buyback": spend, "repay_known": fy in repay,
            "rule": f"순차입(발행−상환) ≥ 매입액의 {DEBT_FUNDED_RATIO:.0%}면 부채 조달(사전 고정·비검증)"}
