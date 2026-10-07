"""
QSI 개정본 — SEC 이벤트 수집으로 `unknown`을 채운다 (v3.94)

종목마다 최신 봉인 레코드를 읽어, **아직 unknown인 질문만** 1차 출처로 채워 개정본(r2…)으로
쌓는다. 기존 파일은 한 글자도 바꾸지 않는다(봉인 해시 불변).

채우는 질문(전부 `engine/sec_events.py`의 사전 고정 규칙):
  gov.insider_pattern     Form 4 (공개시장 P/S, 10b5-1 제외, 재량 순거래액 ≥ $1M)
  gov.cxo_turnover_24m    8-K Item 5.02에서 CEO/CFO 이직 문장이 있는 건수
  acc.restated_down_3y    8-K Item 4.02·10-K/A 부재(존재하면 판단 보류)
  gov.material_litigation 10-K Item 3 — 회사 자기 진술만(없음=none, 중요성 한정=immaterial)
  cap.debt_funded_buyback 같은 연도 순차입 ≥ 매입액의 50%
  (v3.95 확장)
  acc.late_filing_nt_3y / acc.auditor_change_3y / acc.material_impairment_3y
                          제출 목록의 NT 10-K·10-Q / 8-K 4.01 / 8-K 2.06 건수(본문을 읽지 않는다)
  gov.say_on_pay_support_pct 8-K Item 5.07 — 보수 승인 투표 찬성/(찬성+반대)
  gov.insider_group_ownership DEF 14A — 임원·이사 합산 지분 구간(모호하면 unknown)
  acc.icfr_conclusion     10-K Item 9A — 경영진의 ICFR 결론 문장만
  cap.dividend_predictable companyfacts — 5개 연속 연도 주당배당 양수·무감소일 때만 True

⚠️ 이미 answered인 답은 건드리지 않는다. 확인하지 못하면 unknown을 유지하고 **사유를 구체화**한다.
⚠️ 판정·비중·ledger·thesis·holdings는 건드리지 않는다(병기).

실행: python -m scripts.qsi_sec_events [--dry-run] [TICKER ...]
"""

import datetime
import json
import os
import sys
import time
import urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from engine import dilution as D  # noqa: E402
from engine import qualitative_input as Q  # noqa: E402
from engine import sec_events as E  # noqa: E402
from engine.filing_dates import (_http_json, _http_text, fetch_company_facts,  # noqa: E402
                                 ticker_to_cik)

REPORT_DIR = os.path.join(ROOT, "reports", "sec_events")
TARGET_QIDS = ("gov.insider_pattern", "gov.cxo_turnover_24m", "acc.restated_down_3y",
               "gov.material_litigation", "cap.debt_funded_buyback",
               "acc.late_filing_nt_3y", "acc.auditor_change_3y", "acc.material_impairment_3y",
               "gov.say_on_pay_support_pct", "gov.insider_group_ownership",
               "acc.icfr_conclusion", "cap.dividend_predictable")


def _retry(fn, url):
    for attempt in range(4):
        try:
            return fn(url)
        except urllib.error.HTTPError as e:
            if e.code not in (429, 500, 502, 503, 504) or attempt == 3:
                raise
            time.sleep(2 ** attempt)
        except (urllib.error.URLError, TimeoutError):
            if attempt == 3:
                raise
            time.sleep(2 ** attempt)


def fetch_json(url):
    return _retry(_http_json, url)


_TEXT_CACHE = {}


def fetch_text(url):
    if url not in _TEXT_CACHE:
        _TEXT_CACHE[url] = _retry(_http_text, url)
    return _TEXT_CACHE[url]


def _cit(doc, location, url, as_of, quote=""):
    return {"source_key": "sec_edgar", "document": doc, "location": location,
            "observed_date": as_of, "url": url, "quote": quote}


def _ev(summary, citation, direction="neutral", metric=None, value=None, note=""):
    return {"summary": summary, "direction": direction, "verification": "VERIFIED_PRIMARY",
            "confidence": "HIGH", "citation": citation, "metric": metric, "value": value,
            "note": note}


def _claim(cid, statement, materiality, *evs):
    return {"claim_id": cid, "statement": statement, "materiality": materiality,
            "evidence": list(evs)}


def _debt_series(facts, tags):
    """태그 중 **가장 최근 연도까지** 값이 있는 시리즈. 첫 태그를 고르면 2009년에서 멈춘 옛 태그를 집는다."""
    best_tag, best = None, {}
    for tag in tags:
        per = {fy: rows[-1][2] for fy, rows in D.annual_facts(facts, tag).items()}
        if per and (not best or max(per) > max(best)):
            best_tag, best = tag, per
    return best_tag, best


def collect(ticker, as_of):
    """종목 하나의 수집 결과: (claims, answers, findings, report)."""
    cik = ticker_to_cik(ticker)
    since = (datetime.date.fromisoformat(as_of)
             - datetime.timedelta(days=E.RESTATEMENT_WINDOW_DAYS)).isoformat()
    listing = E.list_filings(cik, since, fetch_json)
    index_url = E.SUBMISSIONS_URL.format(cik=listing["cik"])
    browse = (f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={int(cik)}"
              "&type={t}&dateb=&owner=include&count=100")
    claims, answers, findings, report = [], [], [], {"ticker": ticker, "as_of": as_of, "cik": cik}

    def unknown(qid, note):
        answers.append({"qid": qid, "status": "unknown", "note": note})

    # --- Form 4 ---------------------------------------------------------------
    ins = E.collect_insider(listing, fetch_text, as_of)
    report["insider"] = ins
    if ins["status"] == "OK":
        sm = ins["summary"]
        cid = f"{ticker}.INSIDER"
        claims.append(_claim(cid,
            f"최근 12개월 공개시장 거래 {sm['n_open_market']}건: 재량 순 ${sm['discretionary_net_usd']:,.0f}, "
            f"10b5-1 정기 {sm['n_routine_10b5_1']}건 → {sm['answer']}", "HIGH",
            _ev(f"Form 4 {ins['n_form4_filings']}건 집계 (재량 매수 ${sm['discretionary_buy_usd']:,.0f} / "
                f"재량 매도 ${sm['discretionary_sell_usd']:,.0f} / 10b5-1 매도 ${sm['routine_sell_usd']:,.0f})",
                _cit(f"{ticker} Form 4 x{ins['n_form4_filings']} ({ins['window'][0]}~{ins['window'][1]})",
                     "nonDerivativeTransaction, 거래코드 P/S, aff10b5One·각주 10b5-1",
                     browse.format(t="4"), as_of),
                metric="discretionary_net_usd", value=sm["discretionary_net_usd"],
                note=sm["rule"] + ". 파생증권 거래와 옵션행사(M)·세금원천(F)은 제외. "
                     "접수번호 목록은 reports/sec_events에 있다")))
        answers.append({"qid": "gov.insider_pattern", "status": "answered", "answer": sm["answer"],
                        "claim_ids": [cid], "note": ""})
        findings.append({"lens": "governance", "effect": "neutral", "claim_ids": [cid],
                         "summary": "내부자 공개시장 거래를 Form 4로 집계(규칙 적용, 좋고 나쁨은 판단하지 않음)"})
    else:
        unknown("gov.insider_pattern", ins["reason"])

    # --- 8-K 5.02 -------------------------------------------------------------
    cxo = E.collect_cxo(listing, fetch_text, cik, as_of)
    report["cxo"] = cxo
    if cxo["status"] == "OK":
        cid = f"{ticker}.CXO"
        n = cxo["n_cxo_departure_filings"]
        evs = [_ev(f"{e['filing_date']} 8-K Item 5.02", _cit(f"{ticker} 8-K ({e['filing_date']}, acc {e['accession']})",
                  "Item 5.02", e["url"], as_of, e["quote"]), direction="neutral") for e in cxo["events"]]
        if not evs:
            evs = [_ev(f"24개월 8-K Item 5.02 {cxo['n_item_502_filings']}건 중 CEO/CFO 이직 문장 없음",
                       _cit(f"{ticker} submissions index", "filings.recent items 필드", index_url, as_of),
                       note="제출 목록이 24개월 창을 덮는지 확인했다. 본문에서 직책+이직 동사가 같은 문장에 있는 경우만 센다")]
        claims.append(_claim(cid, f"최근 24개월 CEO/CFO 이직 공시 8-K는 {n}건(5.02 전체 {cxo['n_item_502_filings']}건)",
                             "HIGH", *evs))
        answers.append({"qid": "gov.cxo_turnover_24m", "status": "answered", "answer": n,
                        "claim_ids": [cid], "note": ""})
        findings.append({"lens": "governance", "effect": "neutral", "claim_ids": [cid],
                         "summary": "CEO/CFO 이직 공시 건수(8-K 5.02 문장 규칙, 사유·후임 적절성은 판단하지 않음)"})
    else:
        unknown("gov.cxo_turnover_24m", cxo["reason"])

    # --- 재작성 -----------------------------------------------------------------
    rs = E.collect_restatement(listing, as_of)
    report["restatement"] = rs
    if rs["status"] == "OK":
        cid = f"{ticker}.RESTATE"
        if rs["n_item_402"] == 0 and rs["n_10k_amendments"] == 0:
            claims.append(_claim(cid, "최근 3년 8-K Item 4.02(비신뢰 통지)와 10-K/A가 없다", "HIGH",
                _ev("제출 목록에 4.02·10-K/A 없음",
                    _cit(f"{ticker} submissions index", "filings.recent items·form 필드", index_url, as_of),
                    note="'little r' 재작성(이전 연도 수치만 조용히 수정)은 8-K 4.02가 없어 탐지하지 못한다")))
            answers.append({"qid": "acc.restated_down_3y", "status": "answered", "answer": False,
                            "claim_ids": [cid], "note": ""})
            findings.append({"lens": "accounting_quality", "effect": "neutral", "claim_ids": [cid],
                             "summary": "3년 내 재작성 공시(8-K 4.02·10-K/A) 없음 — little r은 미탐지"})
        else:
            claims.append(_claim(cid,
                f"3년 내 8-K 4.02 {rs['n_item_402']}건 {rs['item_402']}, 10-K/A {rs['n_10k_amendments']}건 "
                f"{rs['10k_amendments']} — 방향(하향 여부)은 본문을 읽어야 한다", "HIGH",
                _ev("재작성 관련 공시 존재", _cit(f"{ticker} submissions index", "filings.recent items·form 필드",
                                                  index_url, as_of), direction="contradicts")))
            findings.append({"lens": "accounting_quality", "effect": "neutral", "claim_ids": [cid],
                             "summary": "재작성 관련 공시가 존재 — 본문 확인 필요(자동 판단하지 않음)"})
            unknown("acc.restated_down_3y",
                    f"재작성 관련 공시가 있다({cid}) — 하향 여부·원인은 본문을 사람이 읽어야 한다")
    else:
        unknown("acc.restated_down_3y", rs["reason"])

    # --- 소송(10-K Item 3) ---------------------------------------------------------
    k = [r for r in listing["rows"] if r["form"] == "10-K"]
    if not k:
        unknown("gov.material_litigation", "10-K가 없다(외국 발행사이거나 최근 제출 목록에 없음)")
    else:
        row = sorted(k, key=lambda r: r["filingDate"])[-1]
        url = E.filing_url(cik, row)
        body = E.normalize_text(fetch_text(url))
        lit = E.litigation_from_item3(body)
        report["litigation"] = {k_: v for k_, v in lit.items() if k_ != "excerpt"} | {
            "form_url": url, "filed": row["filingDate"]}
        if lit.get("excerpt") and E.quote_in_text(lit["excerpt"], body):
            cid = f"{ticker}.LITIGATION"
            doc = f"{ticker} 10-K (filed {row['filingDate']}, acc {row['accessionNumber']})"
            claims.append(_claim(cid, "10-K Item 3 서술을 그대로 인용한다", "MEDIUM",
                _ev("Item 3 Legal Proceedings 발췌", _cit(doc, "Item 3. Legal Proceedings", url, as_of,
                                                         lit["excerpt"]))))
            if lit["answer"] in ("none", "immaterial"):
                answers.append({"qid": "gov.material_litigation", "status": "answered",
                                "answer": lit["answer"], "claim_ids": [cid],
                                "note": "회사의 자기 진술이다 — 독립 확인이 아니다. " + lit["reason"]})
            else:
                unknown("gov.material_litigation", f"{lit['reason']} (발췌: {cid})")
            findings.append({"lens": "governance", "effect": "neutral", "claim_ids": [cid],
                             "summary": "10-K Item 3 서술 인용(심각도는 판단하지 않음)"})
        else:
            unknown("gov.material_litigation", lit.get("reason", "Item 3 확인 실패"))

    # --- 적신호 공시(목록 기반): NT·감사인 변경·중대 손상 ---------------------------------------
    fl = E.collect_listing_flags(listing, as_of)
    report["listing_flags"] = fl
    if fl["status"] == "OK":
        for qid, key, label, cid_sfx in (
                ("acc.late_filing_nt_3y", "nt", "정기보고서 지연 제출 통지(NT 10-K/10-Q)", "NT"),
                ("acc.auditor_change_3y", "auditor_change", "감사인 변경 8-K(Item 4.01)", "AUDITOR"),
                ("acc.material_impairment_3y", "material_impairment", "중대 손상 인식 8-K(Item 2.06)", "IMPAIR")):
            n = fl["n_" + {"nt": "nt", "auditor_change": "auditor_change",
                           "material_impairment": "material_impairment"}[key]]
            cid = f"{ticker}.{cid_sfx}"
            claims.append(_claim(cid, f"최근 3년 {label} {n}건 {[x['date'] for x in fl[key]]}", "HIGH",
                _ev(f"제출 목록에서 {label} {n}건 (창 {fl['window_since']}~{as_of}, 목록이 창을 덮음 확인)",
                    _cit(f"{ticker} submissions index", "filings.recent form·items 필드", index_url, as_of),
                    metric=qid, value=n,
                    note="건수는 그 공시가 있었다는 사실이다. 원인·심각도는 판단하지 않는다"
                         + (" (4.01은 정기 감사인 교체·임기 만료도 포함)" if key == "auditor_change" else "")
                         + (" (2.06은 회사가 스스로 '중요'하다고 결론낸 손상만 공시된다)"
                            if key == "material_impairment" else ""))))
            answers.append({"qid": qid, "status": "answered", "answer": n,
                            "claim_ids": [cid], "note": ""})
        findings.append({"lens": "accounting_quality", "effect": "neutral",
                         "claim_ids": [f"{ticker}.NT", f"{ticker}.AUDITOR", f"{ticker}.IMPAIR"],
                         "summary": "적신호 공시(NT·감사인 변경·중대 손상) 건수를 제출 목록에서 집계(원인 판단 없음)"})
    else:
        for qid in ("acc.late_filing_nt_3y", "acc.auditor_change_3y", "acc.material_impairment_3y"):
            unknown(qid, fl["reason"])

    # --- 보수 승인 투표(8-K 5.07) -------------------------------------------------------------
    sop = E.collect_say_on_pay(listing, fetch_text, cik, as_of)
    report["say_on_pay"] = {k_: v for k_, v in sop.items() if k_ != "result"} | {
        "result": ({k_: v for k_, v in sop["result"].items() if k_ != "excerpt"} if sop.get("result") else None)}
    if sop["status"] == "OK" and sop.get("result"):
        res = sop["result"]
        cid = f"{ticker}.SAYONPAY"
        claims.append(_claim(cid,
            f"{sop['filing_date']} 주총 보수 승인 투표 찬성 {res['for']:,} / 반대 {res['against']:,} → "
            f"찬성률 {res['answer']:.1%}", "HIGH",
            _ev("8-K Item 5.07 보수 승인 안건 찬반",
                _cit(f"{ticker} 8-K ({sop['filing_date']}, acc {sop['accession']})", "Item 5.07",
                     sop["url"], as_of, res["excerpt"]),
                metric="say_on_pay_support", value=round(res["answer"], 4), note=res["rule"])))
        answers.append({"qid": "gov.say_on_pay_support_pct", "status": "answered",
                        "answer": round(res["answer"], 4), "claim_ids": [cid], "note": ""})
        findings.append({"lens": "governance", "effect": "neutral", "claim_ids": [cid],
                         "summary": "주총 보수 승인(say-on-pay) 찬성률을 8-K 5.07에서 집계(좋고 나쁨은 판단하지 않음)"})
    else:
        unknown("gov.say_on_pay_support_pct",
                sop.get("reason") or "보수 승인 결과를 읽지 못했다")

    # --- 임원·이사 합산 지분(DEF 14A) ------------------------------------------------------------
    ig = E.collect_insider_group(listing, fetch_text, cik, as_of)
    report["insider_group"] = {k_: v for k_, v in ig.items() if k_ != "result"} | {
        "result": ({k_: v for k_, v in ig["result"].items() if k_ != "excerpt"} if ig.get("result") else None)}
    igr = ig.get("result") if ig["status"] == "OK" else None
    if igr and igr.get("answer"):
        cid = f"{ticker}.INSIDERGROUP"
        claims.append(_claim(cid,
            f"위임장({ig['filing_date']}) 기준 임원·이사 합산 지분 구간 {igr['answer']}"
            + (f" ({igr['pct']}%)" if igr.get("pct") is not None else " ('*' = 1% 미만 표기)"), "MEDIUM",
            _ev("DEF 14A 지분표의 'as a group' 행",
                _cit(f"{ticker} DEF 14A (filed {ig['filing_date']}, acc {ig['accession']})",
                     "Security Ownership 표 — 'as a group' 행", ig["url"], as_of, igr["excerpt"]),
                metric="insider_group_pct", value=igr.get("pct"), note=igr["rule"])))
        answers.append({"qid": "gov.insider_group_ownership", "status": "answered",
                        "answer": igr["answer"], "claim_ids": [cid], "note": ""})
        findings.append({"lens": "governance", "effect": "neutral", "claim_ids": [cid],
                         "summary": "임원·이사 합산 지분을 위임장 지분표에서 구간으로 집계(판단 없음)"})
    else:
        unknown("gov.insider_group_ownership",
                (ig.get("reason") if ig["status"] != "OK" else (igr or {}).get("reason") or ig.get("reason"))
                or "합산 지분을 읽지 못했다")

    # --- ICFR 결론(10-K Item 9A) ---------------------------------------------------------------
    if not k:
        unknown("acc.icfr_conclusion", "10-K가 없다(외국 발행사이거나 최근 제출 목록에 없음)")
    else:
        row = sorted(k, key=lambda r: r["filingDate"])[-1]
        url = E.filing_url(cik, row)
        body = E.normalize_text(fetch_text(url))
        ic = E.icfr_from_10k(body)
        report["icfr"] = {k_: v for k_, v in ic.items() if k_ != "excerpt"} | {
            "form_url": url, "filed": row["filingDate"]}
        if ic.get("answer") and E.quote_in_text(ic["excerpt"], body):
            cid = f"{ticker}.ICFR"
            doc = f"{ticker} 10-K (filed {row['filingDate']}, acc {row['accessionNumber']})"
            claims.append(_claim(cid, f"10-K Item 9A 경영진 결론: ICFR {ic['answer']}", "HIGH",
                _ev("Item 9A 경영진 결론 문장", _cit(doc, "Item 9A. Controls and Procedures", url, as_of,
                                                    ic["excerpt"]),
                    note=ic["rule"] + ". 경영진의 자기 평가이며 외부 감사인 의견과 별개다")))
            answers.append({"qid": "acc.icfr_conclusion", "status": "answered", "answer": ic["answer"],
                            "claim_ids": [cid], "note": "경영진의 자기 평가다 — 독립 확인이 아니다"})
            findings.append({"lens": "accounting_quality", "effect": "neutral", "claim_ids": [cid],
                             "summary": "10-K Item 9A 경영진의 ICFR 결론 문장을 인용(판단 없음)"})
        else:
            unknown("acc.icfr_conclusion", ic.get("reason", "Item 9A 확인 실패"))

    # --- 배당 예측가능성(companyfacts) ---------------------------------------------------------
    facts = fetch_company_facts(cik)
    dtag, dps = _debt_series(facts, E.DIVIDEND_TAGS)
    dv = E.dividend_predictable(dps, min_fy=int(as_of[:4]) - 2) if dps else {
        "answer": None, "reason": "주당배당 태그 값이 없다(무배당이거나 미보고 — 구분할 수 없다)"}
    report["dividend"] = dv | {"tag": dtag}
    if dv["answer"] is True:
        cid = f"{ticker}.DIVIDEND"
        claims.append(_claim(cid, f"최근 {len(dv['years'])}개 연속 회계연도 주당배당 {dv['values']} — 감소 없음",
            "MEDIUM", _ev("현금흐름·자본 관련 주당배당(companyfacts)",
                _cit(f"{ticker} companyfacts", f"{dtag} FY{dv['years'][0]}~FY{dv['years'][-1]}",
                     f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json", as_of),
                metric="dividends_per_share", value=dv["values"][-1], note=dv["rule"])))
        answers.append({"qid": "cap.dividend_predictable", "status": "answered", "answer": True,
                        "claim_ids": [cid], "note": ""})
        findings.append({"lens": "capital_allocation", "effect": "neutral", "claim_ids": [cid],
                         "summary": "배당이 5개 연속 연도 감소 없이 지급됨(companyfacts, 사전 고정 규칙)"})
    else:
        extra = f" 감소 연도: {dv['declines']}" if dv.get("declines") else ""
        unknown("cap.dividend_predictable", dv["reason"] + extra)

    # --- 자사주 매입 재원 ------------------------------------------------------------
    _, issue = _debt_series(facts, E.DEBT_ISSUE_TAGS)
    _, repay = _debt_series(facts, E.DEBT_REPAY_TAGS)
    _, buy = _debt_series(facts, E.BUYBACK_TAGS)
    dfb = E.debt_funded_buyback(issue, repay, buy, min_fy=int(as_of[:4]) - 2)
    report["debt_funded_buyback"] = dfb
    if dfb["answer"] is None:
        unknown("cap.debt_funded_buyback", dfb["reason"])
    else:
        cid = f"{ticker}.DEBTBUYBACK"
        claims.append(_claim(cid,
            f"FY{dfb['fy']} 순차입 {dfb['net_debt_issuance']:,.0f} vs 자사주 매입 {dfb['buyback']:,.0f} → "
            f"부채 조달 {'맞다' if dfb['answer'] else '아니다'}", "HIGH",
            _ev("현금흐름표 차입 발행·상환·매입 지출(companyfacts)",
                _cit(f"{ticker} companyfacts", f"차입 발행/상환/자사주 매입 FY{dfb['fy']}",
                     f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json", as_of),
                metric="net_debt_issuance", value=dfb["net_debt_issuance"],
                note=dfb["rule"] + ("" if dfb["repay_known"] else ". ⚠️ 상환 값을 찾지 못해 상환 0으로 가정했다"))))
        answers.append({"qid": "cap.debt_funded_buyback", "status": "answered", "answer": dfb["answer"],
                        "claim_ids": [cid], "note": ""})
        findings.append({"lens": "capital_allocation", "effect": "neutral", "claim_ids": [cid],
                         "summary": "자사주 매입 재원을 같은 연도 순차입과 비교(사전 고정 규칙)"})
    return claims, answers, findings, report


def merge(prior, claims, answers, findings, as_of):
    """prior 코어를 복사해 **unknown이던 답만** 바꾼다. answered는 절대 덮지 않는다."""
    # 업종 변형이 갖지 않는 축(보험사에는 자본배분·회계품질 축이 없다)의 질문·finding은 버린다.
    # 축을 즉석에서 늘리면 종목 간 비교가 깨진다(research_lenses 계약).
    in_bank = {q.qid for q in Q.bank_for(prior["lens_set"])}
    lenses = set(Q.lenses_for(prior["lens_set"]))
    answers = [a for a in answers if a["qid"] in in_bank]
    findings = [f for f in findings if f["lens"] in lenses]
    keep = {cid for a in answers if a["status"] == "answered" for cid in a["claim_ids"]}
    keep |= {cid for f in findings for cid in f["claim_ids"]}
    claims = [c for c in claims if c["claim_id"] in keep]
    core = {k: prior[k] for k in Q.CORE_KEYS}
    core = json.loads(json.dumps(core))
    core["as_of"] = as_of
    have = {c["claim_id"] for c in core["claims"]}
    new_by_qid = {a["qid"]: a for a in answers}
    changed = []
    out = []
    seen = set()
    for a in core["answers"]:
        seen.add(a["qid"])
        n = new_by_qid.get(a["qid"])
        if a["status"] == "unknown" and n is not None:
            if n["status"] == "answered" or n["note"] != a.get("note"):
                changed.append(a["qid"])
            out.append(n)
        else:
            out.append(a)
    for q in Q.bank_for(core["lens_set"]):          # 은행에 새로 생긴 질문
        if q.qid not in seen and q.qid in new_by_qid:
            out.append(new_by_qid[q.qid])
            changed.append(q.qid)
    core["answers"] = out
    used = {cid for a in out if a["status"] == "answered" for cid in a["claim_ids"]}
    for c in claims:
        if c["claim_id"] not in have:
            core["claims"].append(c)
    # 축마다 finding은 하나만 허용된다 — 같은 축이면 근거 주장과 요약을 합친다.
    by_lens = {f["lens"]: f for f in core["findings"]}
    for f in findings:
        cur = by_lens.get(f["lens"])
        if cur is None:
            core["findings"].append(dict(f))
            by_lens[f["lens"]] = core["findings"][-1]
        else:
            cur["claim_ids"] = list(dict.fromkeys(cur["claim_ids"] + f["claim_ids"]))
            if f["summary"] not in cur["summary"]:
                cur["summary"] = f"{cur['summary']} / {f['summary']}"
    return core, changed


def main(argv):
    dry = "--dry-run" in argv
    as_of = datetime.date.today().isoformat()
    tickers = [a for a in argv if not a.startswith("--")]
    if not tickers:
        tickers = sorted({f.split("_")[0] for f in os.listdir(Q.QUALITATIVE_DIR) if f.endswith(".json")})
    os.makedirs(REPORT_DIR, exist_ok=True)
    for t in tickers:
        prior = Q.latest_record(t)
        if prior is None:
            print(f"{t:5} 기존 QSI 기록이 없다 — 건너뜀")
            continue
        try:
            claims, answers, findings, report = collect(t, as_of)
            core, changed = merge(prior, claims, answers, findings, as_of)
            rec = Q.build_record(core)
        except Exception as e:
            print(f"{t:5} 실패: {type(e).__name__}: {e}")
            continue
        c = rec["coverage"]
        newly = [a for a in changed if next(x for x in rec["answers"] if x["qid"] == a)["status"] == "answered"]
        print(f"{t:5} 답 {prior['coverage']['n_answered']:>2}/{prior['coverage']['n_questions']:<2} -> "
              f"{c['n_answered']:>2}/{c['n_questions']:<2}  새로 답한 것: {newly or '-'}")
        with open(os.path.join(REPORT_DIR, f"{t}_{as_of}.json"), "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2, sort_keys=True, default=str)
            f.write("\n")
        if not dry and rec["sealed_core_hash"] != prior["sealed_core_hash"]:
            print("      ->", os.path.relpath(
                Q.save_record(rec, supersedes=prior["sealed_core_hash"]), ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
