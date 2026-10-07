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
    text = html.unescape(re.sub(r"<[^>]+>", " ", raw))
    # 폭 없는 공백·BOM은 \s가 아니라서 숫자 사이에 끼면 파싱이 조용히 깨진다(실측: SKYW 5.07 표).
    text = re.sub(r"[\u200b\u200c\u200d\ufeff]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


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
    r"(?:are|is|were)\s+(?:currently\s+)?not\s+(?:currently\s+)?(?:a\s+)?(?:party|subject)\s+to,?\s+"
    # 'party to, nor are we aware of, any legal proceeding …' (실측: SE 20-F)
    r"(?:nor\s+[^,.]{0,60},\s+)?(?:any|material)[^.]{0,120}(?:legal|litigation|proceeding)[^.]*\.", re.I)
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


# =====================================================================================
# v3.95 — 적신호 공시·거버넌스 확장 (QSI의 비어 있던 회계품질·거버넌스 칸을 1차 출처로)
# =====================================================================================
# 전부 **사실 집계**다. 좋고 나쁨은 판정하지 않는다. 규칙이 답하지 못하면 `None`이며,
# 그 이유를 `reason`에 남긴다(조용히 청정 신호로 오독되지 않게).

NT_FORMS = ("NT 10-K", "NT 10-Q", "NT 10-K/A", "NT 10-Q/A")
FLAG_WINDOW_DAYS = RESTATEMENT_WINDOW_DAYS     # 3년 — 목록 조회 창과 동일(덮음 확인 재사용)

INSIDER_GROUP_BANDS = ("lt_1pct", "1_to_5pct", "5_to_20pct", "gte_20pct")   # 사전 고정·비검증


def collect_listing_flags(listing: dict, as_of: str) -> dict:
    """제출 목록만으로 센다(본문을 읽지 않는다): NT 10-K/10-Q(지연 제출 통지)·
    8-K Item 4.01(감사인 변경)·8-K Item 2.06(중대 손상 인식).

    ⚠️ 건수는 **그 일이 있었다는 사실**이다. 4.01은 감사인 임기 만료·정기 교체도 포함하고
    2.06은 회사가 스스로 '중요'하다고 결론낸 손상만 공시된다 — 원인·심각도는 판단하지 않는다.
    """
    if is_foreign_private_issuer(listing["all_forms"]):
        return {"status": UNAVAILABLE, "reason": "20-F/6-K 발행사 — NT 10-K·8-K 의무가 없다"}
    since = (datetime.date.fromisoformat(as_of) - datetime.timedelta(days=FLAG_WINDOW_DAYS)).isoformat()
    if not listing["covers_window"]:
        return {"status": UNAVAILABLE, "reason": "제출 목록이 3년 창을 덮지 못해 부재 판단 불가"}
    nt = [r for r in listing["rows"] if r["form"] in NT_FORMS and r["filingDate"] >= since]
    aud = rows_with_item(listing, "4.01", since)
    imp = rows_with_item(listing, "2.06", since)
    pick = lambda rs: [{"date": r["filingDate"], "accession": r["accessionNumber"], "form": r["form"]} for r in rs]
    return {"status": "OK", "window_since": since,
            "n_nt": len(nt), "nt": pick(nt),
            "n_auditor_change": len(aud), "auditor_change": pick(aud),
            "n_material_impairment": len(imp), "material_impairment": pick(imp)}


# --- 보수 승인(say-on-pay) 투표: 8-K Item 5.07 -----------------------------------------

_SOP_ANCHOR = re.compile(
    r"(?:advisory|non-binding)\s*(?:\([^)]{0,30}\)\s*)?(?:vote|basis)?[^.]{0,200}?"
    r"(?:executive\s+compensation|named\s+executive|compensation\s+of\s+(?:our|the\s+company))", re.I)
_SOP_TABLE = re.compile(
    r"(?:votes\s+)?for\s+(?:votes\s+)?against\s+(?:votes\s+)?abst(?:ain|ent)\w*\s+"
    r"(?:broker\s+non[\s-]*votes?\s+)?([\d,]+)\s+([\d,]+)"
    r"|votes\s+for(?:\s+approval)?\s+([\d,]+)\s+votes\s+against\s+([\d,]+)", re.I)
SOP_WINDOW = 300     # 안건 문장 끝에서 표·서술까지의 최대 거리(사전 고정)
_SOP_PROSE = re.compile(
    r"([\d,]{4,})\s+(?:affirmative\s+votes|votes\s+for|shares\s+voted\s+for)[^.]{0,60}?"
    r"([\d,]{3,})\s+(?:negative\s+votes|votes\s+against|shares\s+voted\s+against)", re.I)


def say_on_pay_from_507(section: str) -> dict:
    """8-K Item 5.07 절에서 보수 승인 투표 찬성·반대. 찬성률 = 찬성/(찬성+반대)(기권 제외, 통용 관행).

    - '투표 빈도'(frequency) 안건은 보수 승인이 아니므로 제외한다.
    - 표 형식과 서술 형식 둘 다 읽고, 어느 쪽도 못 읽으면 `None`(추측하지 않는다).
    """
    for m in _SOP_ANCHOR.finditer(section):
        if "frequency" in section[m.start():m.end() + 120].lower():
            continue
        # 표는 그 안건 **바로 뒤**에 있어야 한다 — 멀리 있는 표는 다른 안건의 것일 수 있다(오연결 방지).
        tail = section[m.end():m.end() + SOP_WINDOW]
        t = _SOP_TABLE.search(tail)
        p = _SOP_PROSE.search(tail)
        hit = None
        if t and (not p or t.start() <= p.start()):
            hit = (t, t.group(1) or t.group(3), t.group(2) or t.group(4))
        elif p:
            hit = (p, p.group(1), p.group(2))
        if not hit:
            continue
        try:
            f, a = int(hit[1].replace(",", "")), int(hit[2].replace(",", ""))
        except ValueError:
            continue
        if f + a <= 0:
            continue
        excerpt = section[m.start():m.end() + hit[0].end()]
        return {"answer": f / (f + a), "for": f, "against": a, "excerpt": excerpt,
                "rule": "찬성/(찬성+반대), 기권·브로커 무투표 제외(사전 고정)"}
    return {"answer": None, "reason": "보수 승인(say-on-pay) 안건의 찬반 표를 읽지 못했다"}


def collect_say_on_pay(listing: dict, fetch_text, cik: str, as_of: str) -> dict:
    """최근 24개월 8-K Item 5.07 중 **가장 최근에 보수 승인 결과를 읽을 수 있는** 제출."""
    if is_foreign_private_issuer(listing["all_forms"]):
        return {"status": UNAVAILABLE, "reason": "20-F/6-K 발행사 — 8-K Item 5.07 의무가 없다"}
    since = (datetime.date.fromisoformat(as_of) - datetime.timedelta(days=CXO_WINDOW_DAYS)).isoformat()
    if not listing["covers_window"]:
        return {"status": UNAVAILABLE, "reason": "제출 목록이 24개월 창을 덮지 못해 부재 판단 불가"}
    rows = sorted(rows_with_item(listing, "5.07", since), key=lambda r: r["filingDate"], reverse=True)
    if not rows:
        return {"status": "OK", "n_item_507": 0, "result": None,
                "reason": "24개월 내 8-K Item 5.07(주총 결과) 제출이 없다"}
    for r in rows:
        url = filing_url(cik, r)
        try:
            body = normalize_text(fetch_text(url))
        except Exception as e:
            return {"status": UNAVAILABLE, "reason": f"8-K 본문 읽기 실패({r['accessionNumber']}): {e}"}
        res = say_on_pay_from_507(item_section(body, "5.07") or body)
        if res["answer"] is not None and quote_in_text(res["excerpt"], body):
            return {"status": "OK", "n_item_507": len(rows), "result": res,
                    "filing_date": r["filingDate"], "accession": r["accessionNumber"], "url": url}
    return {"status": "OK", "n_item_507": len(rows), "result": None,
            "reason": "5.07 제출은 있으나 보수 승인 안건의 찬반을 읽지 못했다"}


# --- 임원·이사 합산 지분: DEF 14A ---------------------------------------------------------

_GROUP = re.compile(
    r"as\s+a\s+group(?:\s*\(\s*(?:\d+|[a-z]+)\s+(?:persons?|individuals?|people|members)\s*\))?", re.I)
_GTOK = re.compile(r"\s*(?:(?P<fn>\(\w{1,2}\))|(?P<star>\*)|(?P<pct>\d+(?:\.\d+)?)\s*%|(?P<num>\d[\d,]*(?:\.\d+)?))")


def group_band(pct: float) -> str:
    if pct < 1:
        return "lt_1pct"
    if pct < 5:
        return "1_to_5pct"
    if pct < 20:
        return "5_to_20pct"
    return "gte_20pct"


def insider_group_from_proxy(body: str) -> dict:
    """위임장 지분표의 'All directors and executive officers as a group' 행.

    **모호하면 답하지 않는다** — 다중 클래스(주식 종류별 퍼센트가 여러 개)·형식 이탈은 `None`.
    `*`(1% 미만 표기)는 `lt_1pct`. 퍼센트가 없는 행도 `None`.
    """
    found = []
    for m in _GROUP.finditer(body):
        pos, toks = m.end(), []
        while len(toks) < 8:
            t = _GTOK.match(body, pos)
            if not t:
                break
            kind = t.lastgroup
            if kind != "fn":
                toks.append((kind, t.group(kind)))
            pos = t.end()
        if not toks or toks[0][0] != "num":
            continue
        rest = toks[1:]
        if len(rest) == 1 and rest[0][0] == "star":
            pct, label = None, "lt_1pct"
        elif len(rest) == 1 and rest[0][0] == "pct":
            pct = float(rest[0][1]); label = group_band(pct)
        elif len(rest) == 1 and rest[0][0] == "num" and "." in rest[0][1] and float(rest[0][1]) <= 100:
            pct = float(rest[0][1]); label = group_band(pct)
        else:
            found.append(("ambiguous", None, None))
            continue
        start = max(0, m.start() - 90)
        found.append((label, pct, body[start:pos].strip()))
    ok = {f[0] for f in found if f[0] != "ambiguous"}
    if len(ok) == 1:
        label = ok.pop()
        hit = next(f for f in found if f[0] == label)
        return {"answer": label, "pct": hit[1], "excerpt": hit[2],
                "rule": "임원·이사 합산 지분 퍼센트를 구간으로(사전 고정). '*'는 1% 미만"}
    if len(ok) > 1:
        return {"answer": None, "reason": "합산 지분 행이 서로 다른 구간을 가리킨다"}
    return {"answer": None, "reason": ("합산 지분 행이 다중 클래스·비표준 형식이라 단일 퍼센트를 읽을 수 없다"
                                     if found else "'as a group' 지분 행을 찾지 못했다")}


def collect_insider_group(listing: dict, fetch_text, cik: str, as_of: str) -> dict:
    if is_foreign_private_issuer(listing["all_forms"]):
        return {"status": UNAVAILABLE, "reason": "20-F/6-K 발행사 — 미국 위임장(DEF 14A) 의무가 없다"}
    rows = sorted([r for r in listing["rows"] if r["form"] == "DEF 14A"],
                  key=lambda r: r["filingDate"], reverse=True)
    if not rows:
        return {"status": "OK", "result": None, "reason": "조회 창 안에 DEF 14A가 없다"}
    r = rows[0]
    url = filing_url(cik, r)
    try:
        body = normalize_text(fetch_text(url))
    except Exception as e:
        return {"status": UNAVAILABLE, "reason": f"DEF 14A 본문 읽기 실패({r['accessionNumber']}): {e}"}
    res = insider_group_from_proxy(body)
    if res.get("answer") and not quote_in_text(res["excerpt"], body):
        res = {"answer": None, "reason": "추출한 행이 원문과 글자 일치하지 않아 폐기"}
    return {"status": "OK", "result": res, "filing_date": r["filingDate"],
            "accession": r["accessionNumber"], "url": url}


# --- 내부통제(ICFR) 결론: 10-K Item 9A ----------------------------------------------------

_ICFR = re.compile(
    r"concluded\s+that[^.]{0,200}?internal\s+control\s+over\s+financial\s+reporting"
    r"[^.]{0,80}?\b(?:was|is|were)\s+(not\s+)?effective"
    # 'management concluded that the Company maintained effective internal control …' (실측: DLO 20-F)
    r"|concluded\s+that\s+(?:the\s+Company|we|our\s+company)\s+(did\s+not\s+maintain|maintained)\s+"
    r"effective\s+internal\s+control\s+over\s+financial\s+reporting", re.I)


def _longest_section(body: str, start_pat: str, end_pat: str, cap: int = 60000) -> str:
    best = ""
    for m in re.finditer(start_pat, body, re.I):
        nxt = re.search(end_pat, body[m.end():], re.I)
        e = m.end() + nxt.start() if nxt else min(len(body), m.end() + cap)
        if e - m.start() > len(best):
            best = body[m.start():e]
    return best


def _icfr_outcome(h) -> str:
    if h.group(1) or (h.group(2) or "").lower().startswith("did not"):
        return "ineffective"
    return "effective"


def icfr_from_10k(body: str) -> dict:
    """Item 9A에서 **경영진이 직접 내린 결론** 문장만. 위험요인의 가정문('if we identify…')은 읽지 않는다."""
    sec = _longest_section(body, r"Item\s+9A\s*[.:\-—–]?\s*Controls\s+and\s+Procedures",
                           r"Item\s+9B")
    if not sec:
        return {"answer": None, "reason": "Item 9A 절을 찾지 못했다"}
    hits = list(_ICFR.finditer(sec))
    if not hits:
        return {"answer": None, "reason": "Item 9A에 경영진의 ICFR 결론 문장이 없다(Exhibit 참조일 수 있다)"}
    outs = {_icfr_outcome(h) for h in hits}
    if len(outs) > 1:
        return {"answer": None, "reason": "Item 9A에 effective/not effective 결론이 함께 있다 — 사람이 읽어야 한다"}
    return {"answer": outs.pop(), "excerpt": hits[0].group(0).strip(), "section_len": len(sec),
            "rule": "경영진 결론 문장('concluded that … internal control … was/is (not) effective')만"}


# --- 배당 예측가능성: companyfacts ----------------------------------------------------------

DIVIDEND_TAGS = ("CommonStockDividendsPerShareDeclared", "CommonStockDividendsPerShareCashPaid")
DIVIDEND_YEARS = 5


def dividend_predictable(dps: dict, min_fy: int, n: int = DIVIDEND_YEARS) -> dict:
    """최근 `n`개 연속 회계연도 주당배당이 모두 양수이고 **한 번도 줄지 않았으면** True.

    ⚠️ **True만 단언한다.** 감소가 있어도 False로 답하지 않는다 — 특별배당 뒤 정상화가
    '삭감'으로 읽힐 수 있어(실측 PGR: 연 변동 배당), 감소 연도를 사실로만 돌려주고 판단은 비운다.
    """
    years = sorted(dps)[-n:]
    if len(years) < n or years[-1] < min_fy or years[-1] - years[0] != n - 1:
        return {"answer": None, "reason": f"연속 {n}개 회계연도의 주당배당 값이 없다(최근 연도 FY{min_fy} 이후 필요)"}
    vals = [dps[y] for y in years]
    if any(v <= 0 for v in vals):
        return {"answer": None, "reason": "주당배당이 0 이하인 연도가 있다"}
    declines = [(years[i], vals[i - 1], vals[i]) for i in range(1, n) if vals[i] < vals[i - 1] - 1e-9]
    if declines:
        return {"answer": None, "declines": declines,
                "reason": "주당배당이 감소한 연도가 있다 — 특별배당 후 정상화인지 삭감인지는 판단하지 않는다"}
    return {"answer": True, "years": years, "values": vals,
            "rule": f"최근 {n}개 연속 회계연도 주당배당이 모두 양수이고 감소 없음(사전 고정)"}


# --- v3.96: 외국 발행사(20-F) 경로 -------------------------------------------------------------
# 20-F 발행사는 8-K·Form 4·DEF 14A 의무가 없어서 v3.94/v3.95 수집기가 전부 UNAVAILABLE로 남겼다.
# 같은 사실이 20-F 본문의 대응 항목에 있다:
#   10-K Item 9A ↔ 20-F Item 15 / 8-K 4.01 ↔ 20-F Item 16F / 10-K Item 3 ↔ 20-F Item 8.A.7
#   DEF 14A 지분표 ↔ 20-F Item 6.E·7.A / NT 10-K ↔ NT 20-F / 10-K/A ↔ 20-F/A
# 보수 승인 투표는 외국 사적 발행사에 적용되지 않는다(미국 위임장 규칙 면제) — 해당 없음.

FPI_NT_FORMS = ("NT 20-F", "NT 20-F/A")
SAY_ON_PAY_FPI_NOTE = ("외국 사적 발행사(20-F)는 미국 위임장 규칙(Rule 14a-21 보수 승인 투표) 적용 대상이 아니다 — "
                       "투표 자체가 존재하지 않는다")


def icfr_from_20f(body: str) -> dict:
    """20-F Item 15의 경영진 결론. Item 15 머리가 없는 교차참조형(실측: MNDY)은 문서 전체에서 찾되
    결론이 서로 다르면 답하지 않는다."""
    sec = _longest_section(body, r"Item\s+15\s*[.:\-—–]?\s*Controls\s+and\s+Procedures", r"Item\s+16")
    scope = "Item 15"
    hits = list(_ICFR.finditer(sec)) if sec else []
    if not hits:
        hits, scope = list(_ICFR.finditer(body)), "문서 전체(Item 15 머리 없음)"
    if not hits:
        return {"answer": None, "reason": "20-F에서 경영진의 ICFR 결론 문장을 찾지 못했다"}
    outs = {_icfr_outcome(h) for h in hits}
    if len(outs) > 1:
        return {"answer": None, "reason": "effective/not effective 결론이 함께 있다 — 사람이 읽어야 한다"}
    return {"answer": outs.pop(), "excerpt": hits[0].group(0).strip(), "scope": scope,
            "rule": "경영진 결론 문장만(외부 감사인 의견과 별개)"}


# 'I tem 16F'(실측: DLO 2025 20-F의 분리된 글자), 'Item' 없는 교차참조표 '16F Change … N/A'(실측: MNDY)
_16F_HEAD = r"(?:I\s?tem\s+)?16F\s*[.:\-—–]?\s*Change\s+in\s+Registrant.s\s+Certifying\s+Accountant"
_DISMISS = re.compile(r"[^.]{0,240}\b(dismissed|resigned|declined\s+to\s+stand)\b[^.]{0,200}\.", re.I)
_DATE = re.compile(r"(January|February|March|April|May|June|July|August|September|October|November|December)"
                   r"\s+\d{1,2},\s+(20\d\d)")


def auditor_change_from_16f(body: str) -> dict:
    """20-F Item 16F. 'Not applicable/None'이면 0, 해임·사임 문장이 있으면 그 사건들(날짜로 중복 제거).

    목차 줄('Item 16F. Change … 138 Item 16G')은 본문이 아니다 — 가장 긴 절을 쓴다.
    """
    sec = _longest_section(body, _16F_HEAD, r"(?:I\s?tem\s+)?16G\b")
    if not sec:
        return {"answer": None, "reason": "Item 16F 절을 찾지 못했다"}
    rest = re.sub(_16F_HEAD, "", sec, count=1, flags=re.I).strip(" .:\u2014\u2013-")
    if re.match(r"(Not\s+applicable|None|N/A)\b", rest, re.I):
        return {"answer": 0, "events": [], "excerpt": sec[:160].strip()}
    events = {}
    for m in _DISMISS.finditer(rest):
        d = _DATE.search(m.group(0))
        events.setdefault(d.group(0) if d else m.group(0)[:60], m.group(0).strip())
    if not events:
        return {"answer": None, "reason": "Item 16F에 내용이 있으나 해임·사임 문장을 읽지 못했다",
                "excerpt": rest[:400]}
    return {"answer": len(events), "events": sorted(events), "excerpt": next(iter(events.values()))}


def litigation_from_20f(body: str) -> dict:
    """20-F Item 8.A.7 'Legal Proceedings' — 10-K Item 3과 같은 규칙(회사 자기 진술만).

    위험요인에도 'legal proceedings'가 수없이 나오므로, 그 표현 **바로 뒤 400자 안에서** 회사가
    소송 부재를 진술한 경우만 본다.
    """
    for m in re.finditer(r"Legal\s+(?:and\s+\w+\s+)?Proceedings", body, re.I):
        win = body[m.end(): m.end() + 400]
        n = _NONE_STMT.search(win)
        if n and not _NOTE_REF.search(win[:n.end()]):
            qualified = bool(_MATERIAL_QUAL.search(n.group(0)))
            return {"answer": "immaterial" if qualified else "none", "excerpt": n.group(0).strip(),
                    "materiality_qualified": qualified,
                    "reason": ("회사가 '중요한 소송이 없다'고 한정해 진술" if qualified
                               else "회사가 해당 소송이 없다고 직접 진술")}
    return {"answer": None, "reason": "Legal Proceedings 절에서 회사의 소송 부재 진술을 찾지 못했다 "
                                      "(소송을 기술하거나 주석 참조일 수 있다 — 심각도는 사람이 판단한다)"}


_NO_DIVIDEND = re.compile(
    r"[^.]{0,160}\b(?:(?:have|has)\s+never\s+(?:declared\s+or\s+)?paid\s+(?:any\s+)?(?:cash\s+)?dividends"
    r"|(?:do|does)\s+not\s+(?:currently\s+)?(?:anticipate|expect|intend|plan)\s+(?:to\s+)?pay(?:ing)?\s+"
    r"(?:any\s+)?(?:cash\s+)?dividends)[^.]{0,160}\.", re.I)


def no_dividend_statement(body: str):
    """회사가 무배당을 **직접** 진술한 문장(첫 번째). 없으면 None — 부재를 무배당으로 읽지 않는다."""
    m = _NO_DIVIDEND.search(body)
    return m.group(0).strip() if m else None


def fpi_listing_flags(listing: dict, as_of: str) -> dict:
    """외국 발행사의 목록 기반 적신호: NT 20-F 건수, 20-F/A(정정) 건수."""
    if not listing["covers_window"]:
        return {"status": UNAVAILABLE, "reason": "제출 목록이 3년 창을 덮지 못했다"}
    since = (datetime.date.fromisoformat(as_of) - datetime.timedelta(days=FLAG_WINDOW_DAYS)).isoformat()
    rows = [r for r in listing["rows"] if since <= r["filingDate"] <= as_of]
    nt = [r for r in rows if r["form"] in FPI_NT_FORMS]
    amend = [r for r in rows if r["form"] == "20-F/A"]
    return {"status": "OK", "window": [since, as_of], "n_nt": len(nt), "nt": [r["filingDate"] for r in nt],
            "n_20f_amendments": len(amend), "20f_amendments": [r["filingDate"] for r in amend]}


# --- v3.96: 표지·자본배분 기계 규칙 ------------------------------------------------------------

_COVER_ANCHOR = re.compile(r"Indicate\s+by\s+check\s+mark\s+whether\s+the\s+registrant\s+is\s+a\s+shell\s+company", re.I)
_OUTSTANDING_SENT = re.compile(r"[^.]{0,250}\boutstanding\b[^.]{0,250}", re.I)
_SHARE_WORD = re.compile(r"(common\s+stock|common\s+shares|ordinary\s+shares)", re.I)
_CLASS = re.compile(r"\bClass\s+([B-Z])\b")
_NO_CLASS = re.compile(r"no\s+shares\s+of\s+[^.]{0,60}?Class\s+([B-Z])\b", re.I)
COVER_SPAN = 3000


_COVER_END = re.compile(r"DOCUMENTS\s+INCORPORATED\s+BY\s+REFERENCE", re.I)


def single_class_from_cover(body: str) -> dict:
    """10-K 표지의 '발행주식수' 기재 — 양식이 **모든 보통주 클래스**의 발행주식수를 적게 한다.

    표지 구간(쉘 회사 체크 ~ 'DOCUMENTS INCORPORATED BY REFERENCE')에서 클래스 B 이상이 언급되지
    않으면 단일 클래스(False). 'no shares of … Class B … outstanding'처럼 0주로 명시된 클래스는 제외한다
    (실측: NXT). 다른 클래스가 있으면 의결권 차이는 이 구간으로 알 수 없어 답하지 않는다.

    ⚠️ 문장 단위로 자르지 않는다 — '$0.00001' 같은 액면가의 소수점이 문장을 끊어 클래스 표를 놓친다
    (실측: TW는 Class A~D 4중 구조인데 첫 '문장'만 보면 단일 클래스로 오판한다).
    """
    m = _COVER_ANCHOR.search(body)
    if not m:
        return {"answer": None, "reason": "10-K 표지의 쉘 회사 체크 문장을 찾지 못했다"}
    seg = body[m.end(): m.end() + COVER_SPAN]
    e = _COVER_END.search(seg)
    if e:
        seg = seg[:e.start()]
    o = None
    for mm in re.finditer(r"\boutstanding\b", seg, re.I):
        ctx = seg[max(0, mm.start() - 250): mm.end() + 120]
        near = seg[max(0, mm.start() - 100): mm.end() + 100].lower()
        if _SHARE_WORD.search(ctx) and "affiliate" not in near:
            o = mm
            break
    if o is None:
        return {"answer": None, "reason": "표지에서 발행주식수 기재를 찾지 못했다"}
    excerpt = seg[max(0, o.start() - 250): o.end() + 120].strip()
    classes = set(_CLASS.findall(seg)) - set(_NO_CLASS.findall(seg))
    if classes:
        return {"answer": None, "excerpt": excerpt,
                "reason": f"표지에 Class {sorted(classes)} 주식이 있다 — 의결권 차이는 정관·위임장을 읽어야 한다"}
    return {"answer": False, "excerpt": excerpt,
            "rule": "10-K 표지 구간에 보통주 클래스 B 이상이 없다(양식상 모든 클래스를 적어야 한다)"}


def instant_values(facts: dict, tag: str) -> dict:
    """{결산 연도: 값} — 10-K/20-F의 시점(instant) 값, 같은 해는 최신 공시본."""
    out = {}
    for _tax, tagmap in (facts.get("facts") or {}).items():
        node = tagmap.get(tag)
        if not node:
            continue
        for _u, entries in (node.get("units") or {}).items():
            for e in entries:
                if e.get("form") in ("10-K", "10-K/A", "20-F", "20-F/A") and not e.get("start") and e.get("end") \
                        and e.get("val") is not None:
                    out.setdefault(int(e["end"][:4]), []).append((e["filed"], float(e["val"])))
    return {y: sorted(v)[-1][1] for y, v in out.items()}


DEBT_BALANCE_TAGS = ("LongTermDebt", "LongTermDebtNoncurrent", "DebtInstrumentCarryingAmount",
                     "LongTermDebtAndCapitalLeaseObligations", "ConvertibleNotesPayable", "SeniorNotes",
                     "DebtLongtermAndShorttermCombinedAmount")


def debt_funded_buyback_balance(buyback: dict, debt: dict, min_fy: int) -> dict:
    """현금흐름 차입 태그가 없을 때의 대체 규칙 — 같은 해 **차입 잔액 증가**와 매입액을 비교한다.

    차입 잔액 증가 ≥ 매입액의 50% → 부채 조달(True). 잔액이 줄거나 거의 그대로면 False.
    ⚠️ 잔액 변동은 신규 차입 − 상환의 순액이라 재원 추정이 흐름 규칙보다 거칠다(근사).
    """
    yrs = sorted(y for y, v in buyback.items() if v and v > 0 and y >= min_fy and y in debt and (y - 1) in debt)
    if not yrs:
        return {"answer": None, "reason": "매입이 있는 최근 연도의 차입 잔액(전년·당년)을 찾지 못했다"}
    fy = yrs[-1]
    delta = debt[fy] - debt[fy - 1]
    return {"answer": delta >= DEBT_FUNDED_RATIO * buyback[fy], "fy": fy, "buyback": buyback[fy],
            "debt_change": delta, "debt_begin": debt[fy - 1], "debt_end": debt[fy],
            "rule": f"차입 잔액 증가 ≥ 매입액의 {DEBT_FUNDED_RATIO:.0%}이면 부채 조달(잔액 순변동 근사, 사전 고정)"}


MA_WINDOW_YEARS = 5
MA_IMMATERIAL_RATIO = 0.10     # 5년 인수 지출 합 / 5년 영업현금흐름 합(양수만) — 사전 고정·비검증


def ma_intensity(acq: dict, ocf: dict, latest_fy: int) -> dict:
    """최근 5개 회계연도 인수 지출 강도. 10% 미만이면 'no_material_ma', 아니면 규율은 사람이 판단한다.

    ⚠️ 체결되지 않은 시도(해지 수수료)·주식 대가 인수(현금 지출 없음)는 포함하지 않는다.
    """
    yrs = list(range(latest_fy - MA_WINDOW_YEARS + 1, latest_fy + 1))
    have = [y for y in yrs if y in acq]
    if len(have) < MA_WINDOW_YEARS - 1:
        return {"answer": None, "reason": f"인수 지출 값이 5개 연도 중 {len(have)}개뿐이다"}
    a = sum(acq.get(y, 0.0) for y in yrs)
    o = sum(v for y, v in ocf.items() if y in yrs and v > 0)
    if o <= 0:
        return {"answer": None, "reason": "같은 기간 영업현금흐름이 양수가 아니다"}
    ratio = a / o
    out = {"years": yrs, "acquisitions": a, "ocf": o, "ratio": ratio,
           "rule": f"5년 인수 현금지출 ≤ 영업현금흐름의 {MA_IMMATERIAL_RATIO:.0%} → no_material_ma(사전 고정)"}
    if ratio <= MA_IMMATERIAL_RATIO:
        return out | {"answer": "no_material_ma"}
    return out | {"answer": None,
                  "reason": f"5년 인수 지출이 영업현금흐름의 {ratio:.0%} — 가격 규율은 사람이 판단해야 한다"}
