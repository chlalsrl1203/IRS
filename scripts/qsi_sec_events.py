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
  (v3.96 가이던스 원장)
  acc.guidance_miss_3y / acc.promise_kept_record
                          8-K 2.02 EX-99.x의 연간 총매출 가이던스 vs 10-K 실제 매출(engine/guidance_ledger.py)

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
from engine import guidance_ledger as GL  # noqa: E402
from engine.data.providers.sec import METRIC_TAGS  # noqa: E402
from engine import qualitative_input as Q  # noqa: E402
from engine import sec_events as E  # noqa: E402
from engine.filing_dates import (_http_json, _http_text, fetch_company_facts,  # noqa: E402
                                 ticker_to_cik)

REPORT_DIR = os.path.join(ROOT, "reports", "sec_events")
TARGET_QIDS = ("gov.insider_pattern", "gov.cxo_turnover_24m", "acc.restated_down_3y",
               "gov.material_litigation", "cap.debt_funded_buyback",
               "acc.late_filing_nt_3y", "acc.auditor_change_3y", "acc.material_impairment_3y",
               "gov.say_on_pay_support_pct", "gov.insider_group_ownership",
               "acc.icfr_conclusion", "cap.dividend_predictable",
               "acc.guidance_miss_3y", "acc.promise_kept_record")
REVENUE_TAGS = [t.split(":")[-1] for t in METRIC_TAGS["revenue"]]
GUIDANCE_LOOKBACK_DAYS = 1700     # 3개 회계연도의 '최초' 가이던스까지 거슬러 가려면 3년 창으로는 모자란다


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
    # --- 가이던스 원장(8-K 2.02 EX-99.x vs companyfacts 매출) ---------------------------------
    g = collect_guidance(ticker, cik, as_of, facts)
    report["guidance_ledger"] = g
    if g["judge"] is None or g["judge"]["guidance_miss_3y"] is None:
        why = g.get("reason") or g["judge"]["reason"]
        unknown("acc.guidance_miss_3y", why)
        unknown("acc.promise_kept_record", why)
    else:
        jd = g["judge"]
        cid = f"{ticker}.GUIDANCE"
        evs = []
        for row in g["evaluated_rows"]:
            ini = row["initial"]
            evs.append(_ev(
                f"FY{row['fy']} 최초 가이던스 {ini['low']:,.0f}~{ini['high']:,.0f} ({ini['kind']}, {ini['filed']}) "
                f"vs 실제 {row['actual']['value']:,.0f} → {row['status']}",
                _cit(f"{ticker} {g['source_form']} EX-99 (filed {ini['filed']})", "연간 매출 가이던스 문장",
                     ini["url"], as_of, ini["excerpt"]),
                metric="actual_vs_initial_low", value=round(row["vs_initial_low_pct"], 4),
                note=f"실제값: companyfacts {row['actual']['tag']} (결산 {row['actual']['end']}, "
                     f"공시 {row['actual']['filed']})"))
        claims.append(_claim(cid,
            f"최근 {jd['n_evaluated']}개 회계연도 {jd['years']} 최초 연간 매출 가이던스 대비 미달 {jd['n_miss']}회",
            "HIGH", *evs))
        answers.append({"qid": "acc.guidance_miss_3y", "status": "answered",
                        "answer": jd["guidance_miss_3y"], "claim_ids": [cid],
                        "note": "GAAP 총매출 연간 가이던스만 본다(EPS·세그먼트·ARR 제외). 사전 고정 규칙"})
        if jd["promise_kept_record"] is None:
            unknown("acc.promise_kept_record", jd["reason"])
        else:
            answers.append({"qid": "acc.promise_kept_record", "status": "answered",
                            "answer": jd["promise_kept_record"], "claim_ids": [cid],
                            "note": "매출 가이던스 이행만 본다 — 자본배분 약속 등 다른 약속은 포함하지 않는다. "
                                    "가이던스를 낮게 잡는 관행(sandbagging)이면 쉽게 True가 된다"})
        findings.append({"lens": "accounting_quality", "effect": "neutral", "claim_ids": [cid],
                         "summary": "최초 연간 매출 가이던스와 실제 매출을 대조(사전 고정 규칙, 판단 없음)"})
    # --- v3.96 외국 발행사(20-F) 경로 ------------------------------------------------------------
    if E.is_foreign_private_issuer(listing["all_forms"]):
        collect_fpi(ticker, cik, as_of, listing, claims, answers, findings, report)
    else:
        collect_domestic_extra(ticker, cik, as_of, listing, facts, k, claims, answers, findings, report)
    return claims, answers, findings, report


ACQ_TAGS = ("PaymentsToAcquireBusinessesNetOfCashAcquired", "PaymentsToAcquireBusinessesGross",
            "PaymentsToAcquireBusinessesAndInterestInAffiliates")
OCF_TAGS = ("NetCashProvidedByUsedInOperatingActivities",
            "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations")


def collect_domestic_extra(ticker, cik, as_of, listing, facts, k_rows, claims, answers, findings, report):
    """v3.96 국내 발행사 기계 규칙: 표지 단일 클래스 / 무배당 진술 / 차입 잔액 대체 규칙 / M&A 강도."""
    def unknown(qid, note):
        answers.append({"qid": qid, "status": "unknown", "note": note})

    extra = {}
    report["domestic_extra"] = extra
    cf_url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
    body = url = doc = None
    if k_rows:
        row = sorted(k_rows, key=lambda r: r["filingDate"])[-1]
        url = E.filing_url(cik, row)
        body = E.normalize_text(fetch_text(url))
        doc = f"{ticker} 10-K (filed {row['filingDate']}, acc {row['accessionNumber']})"
    # 이중 주식 구조 — 10-K 표지
    if body:
        sc = E.single_class_from_cover(body)
        extra["cover"] = sc
        if sc.get("answer") is False and E.quote_in_text(sc["excerpt"], body):
            cid = f"{ticker}.COVER"
            claims.append(_claim(cid, "10-K 표지: 보통주 단일 클래스만 발행", "HIGH",
                _ev("10-K 표지 발행주식수 문장", _cit(doc, "Cover page (shares outstanding)", url, as_of,
                                                   sc["excerpt"]), note=sc["rule"])))
            answers.append({"qid": "gov.dual_class", "status": "answered", "answer": False,
                            "claim_ids": [cid], "note": "표지 기준 — 우선주의 의결권은 별도로 보지 않았다"})
        else:
            unknown("gov.dual_class", sc.get("reason", "표지 확인 실패"))
    # 무배당 진술 → 배당 예측가능성 해당 없음(주당배당 값이 없을 때만)
    _, dps = _debt_series(facts, E.DIVIDEND_TAGS)
    recent_div = {y: v for y, v in dps.items() if y >= int(as_of[:4]) - 5 and v and v > 0}
    if body and not recent_div:
        nd = E.no_dividend_statement(body)
        extra["no_dividend"] = nd
        if nd:
            answers.append({"qid": "cap.dividend_predictable", "status": "not_applicable",
                            "note": f"회사가 무배당을 직접 진술하고 최근 5년 주당배당 값이 없다: \"{nd}\" ({doc}, {url})"})
    # 자사주 매입 재원 — 흐름 태그가 없을 때 차입 잔액으로
    _, buy = _debt_series(facts, E.BUYBACK_TAGS)
    debt_tag, debt = None, {}
    for tg in E.DEBT_BALANCE_TAGS:
        v = E.instant_values(facts, tg)
        if v and max(v) >= int(as_of[:4]) - 2:
            debt_tag, debt = tg, v
            break
    db = E.debt_funded_buyback_balance(buy, debt, min_fy=int(as_of[:4]) - 2) if debt else {
        "answer": None, "reason": "차입 잔액 태그를 찾지 못했다(무차입이거나 미보고 — 구분할 수 없다)"}
    extra["debt_funded_buyback_balance"] = db | {"tag": debt_tag}
    if db["answer"] is not None:
        cid = f"{ticker}.DEBTBUYBACK_BAL"
        claims.append(_claim(cid,
            f"FY{db['fy']} 차입 잔액 변동 {db['debt_change']:,.0f} vs 자사주 매입 {db['buyback']:,.0f} → "
            f"부채 조달 {'맞다' if db['answer'] else '아니다'}", "HIGH",
            _ev("대차대조표 차입 잔액(전년·당년)과 현금흐름표 매입 지출", _cit(f"{ticker} companyfacts",
                f"{debt_tag} FY{db['fy'] - 1}~FY{db['fy']} / 자사주 매입 FY{db['fy']}", cf_url, as_of),
                metric="debt_change", value=db["debt_change"], note=db["rule"])))
        answers.append({"qid": "cap.debt_funded_buyback", "status": "answered", "answer": db["answer"],
                        "claim_ids": [cid], "note": "차입 잔액 순변동 근사(흐름 태그 부재 시 대체 규칙)"})
    # M&A 강도 — 최근 인수 완료 공시(8-K 2.01)가 결산 후에 있으면 보류
    _, acq = _debt_series(facts, ACQ_TAGS)
    _, ocf = _debt_series(facts, OCF_TAGS)
    latest_fy = max(ocf) if ocf else None
    if latest_fy is None:
        unknown("cap.ma_discipline", "영업현금흐름 값이 없다")
        return
    ma = E.ma_intensity(acq, ocf, latest_fy)
    fy_end = max((v[1] for v in GL.annual_revenue_actuals(facts, REVENUE_TAGS).values()), default=None)
    recent_201 = [r["filingDate"] for r in E.rows_with_item(listing, "2.01", fy_end or as_of)] if fy_end else []
    # 해지된 대형 거래(해지 수수료)는 현금 인수 지출에 잡히지 않는다(실측: ADBE-Figma 2023). 3년 창의
    # 8-K Item 1.02(중요 계약 해지)가 있으면 규율을 단정하지 않는다 — 신용계약 해지도 섞여 보수적이다.
    since3 = (datetime.date.fromisoformat(as_of) - datetime.timedelta(days=E.RESTATEMENT_WINDOW_DAYS)).isoformat()
    item_102 = [r["filingDate"] for r in E.rows_with_item(listing, "1.02", since3)]
    extra["ma"] = ma | {"recent_8k_201": recent_201, "item_102_3y": item_102}
    if ma["answer"] == "no_material_ma" and not recent_201 and not item_102:
        cid = f"{ticker}.MA"
        claims.append(_claim(cid, f"FY{ma['years'][0]}~FY{ma['years'][-1]} 인수 현금지출 {ma['acquisitions']:,.0f} = "
                                  f"영업현금흐름의 {ma['ratio']:.1%}", "MEDIUM",
            _ev("현금흐름표 인수 지출·영업현금흐름(companyfacts)", _cit(f"{ticker} companyfacts",
                f"사업 인수 지출 / 영업현금흐름 FY{ma['years'][0]}~FY{ma['years'][-1]}", cf_url, as_of),
                metric="acquisitions_to_ocf_5y", value=round(ma["ratio"], 4), note=ma["rule"])))
        answers.append({"qid": "cap.ma_discipline", "status": "answered", "answer": "no_material_ma",
                        "claim_ids": [cid],
                        "note": "현금 인수만 본다 — 주식 대가 인수·해지된 시도(해지 수수료)는 포함하지 않는다"})
    else:
        why = ma.get("reason") or ""
        if recent_201:
            why = f"결산 후 인수 완료 공시(8-K 2.01) {recent_201} — 최근 인수가 아직 연차 수치에 없다. " + why
        if item_102 and ma["answer"] == "no_material_ma":
            why = (f"현금 인수 지출은 영업현금흐름의 {ma['ratio']:.1%}로 작지만, 3년 내 중요 계약 해지 공시"
                   f"(8-K 1.02) {item_102}가 있다 — 해지된 거래의 가격 규율은 사람이 판단한다. " + why)
        unknown("cap.ma_discipline", why or "M&A 강도를 판정하지 못했다")


def collect_fpi(ticker, cik, as_of, listing, claims, answers, findings, report):
    """20-F 대응 항목으로 국내 발행사 질문을 채운다. 같은 qid의 앞선 unknown은 merge에서 뒤의 답이 이긴다."""
    def unknown(qid, note):
        answers.append({"qid": qid, "status": "unknown", "note": note})

    fpi = {}
    report["fpi"] = fpi
    # 보수 승인 투표 — 제도 자체가 적용되지 않는다(규칙 기반 해당 없음).
    answers.append({"qid": "gov.say_on_pay_support_pct", "status": "not_applicable",
                    "note": E.SAY_ON_PAY_FPI_NOTE})
    # NT 20-F · 20-F/A (목록 기반)
    fl = E.fpi_listing_flags(listing, as_of)
    fpi["listing_flags"] = fl
    browse = (f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={int(cik)}"
              "&type={t}&dateb=&owner=include&count=100")
    if fl["status"] == "OK":
        cid = f"{ticker}.FPI_NT"
        claims.append(_claim(cid, f"최근 3년({fl['window'][0]}~{fl['window'][1]}) NT 20-F {fl['n_nt']}건", "HIGH",
            _ev(f"제출 목록 3년 창에서 NT 20-F {fl['n_nt']}건", _cit(f"{ticker} EDGAR 제출 목록",
                "form = NT 20-F", browse.format(t="NT+20-F"), as_of),
                metric="nt_filings_3y", value=fl["n_nt"],
                note="외국 발행사의 지연 제출 통지는 NT 20-F다(NT 10-K/10-Q 대응)")))
        answers.append({"qid": "acc.late_filing_nt_3y", "status": "answered", "answer": fl["n_nt"],
                        "claim_ids": [cid], "note": "NT 20-F 건수(외국 발행사)"})
        if fl["n_20f_amendments"] == 0:
            cid2 = f"{ticker}.FPI_RESTATE"
            claims.append(_claim(cid2, "최근 3년 20-F/A(정정 제출) 0건", "MEDIUM",
                _ev("제출 목록 3년 창에서 20-F/A 0건", _cit(f"{ticker} EDGAR 제출 목록", "form = 20-F/A",
                    browse.format(t="20-F%2FA"), as_of), metric="amendments_3y", value=0,
                    note="외국 발행사에는 8-K 4.02(비의존 공시)가 없어 국내 규칙보다 약한 근거다 — "
                         "본 보고서 안의 재표시('little r')는 탐지하지 못한다")))
            answers.append({"qid": "acc.restated_down_3y", "status": "answered", "answer": False,
                            "claim_ids": [cid2], "note": "20-F/A 부재만 근거(4.02 대응 공시 없음)"})
        else:
            unknown("acc.restated_down_3y", f"20-F/A {fl['n_20f_amendments']}건 — 정정 사유는 사람이 읽어야 한다")
    # 20-F 본문(최근 2건 — 16F는 각 보고서가 직전 2개 회계연도를 덮는다)
    tf = sorted([r for r in listing["rows"] if r["form"] == "20-F"], key=lambda r: r["filingDate"],
                reverse=True)[:2]
    if not tf:
        for q in ("acc.icfr_conclusion", "acc.auditor_change_3y", "gov.material_litigation"):
            unknown(q, "최근 3년 창에 20-F가 없다")
        return
    docs = []
    for r in tf:
        url = E.filing_url(cik, r)
        docs.append((r, url, E.normalize_text(fetch_text(url))))
    r0, u0, b0 = docs[0]
    doc0 = f"{ticker} 20-F (filed {r0['filingDate']}, acc {r0['accessionNumber']})"
    # ICFR
    ic = E.icfr_from_20f(b0)
    fpi["icfr"] = ic
    if ic.get("answer") and E.quote_in_text(ic["excerpt"], b0):
        cid = f"{ticker}.FPI_ICFR"
        claims.append(_claim(cid, f"20-F 경영진 결론: ICFR {ic['answer']}", "HIGH",
            _ev("20-F Item 15 경영진 결론 문장", _cit(doc0, ic["scope"], u0, as_of, ic["excerpt"]),
                note=ic["rule"])))
        answers.append({"qid": "acc.icfr_conclusion", "status": "answered", "answer": ic["answer"],
                        "claim_ids": [cid], "note": "경영진의 자기 평가다 — 독립 확인이 아니다"})
    else:
        unknown("acc.icfr_conclusion", ic.get("reason", "20-F ICFR 결론 확인 실패"))
    # 감사인 변경(16F)
    evs, total, seen, ok = [], 0, set(), True
    for r, u, b in docs:
        a = E.auditor_change_from_16f(b)
        fpi.setdefault("item16f", []).append({"filed": r["filingDate"], **a})
        if a.get("answer") is None or not E.quote_in_text(a["excerpt"], b):
            ok = False
            break
        new = [e for e in a["events"] if e not in seen]
        seen.update(a["events"])
        total += len(new)
        evs.append(_ev(f"20-F Item 16F (filed {r['filingDate']}): 사건 {a['answer']}건",
                       _cit(f"{ticker} 20-F (filed {r['filingDate']}, acc {r['accessionNumber']})",
                            "Item 16F. Change in Registrant’s Certifying Accountant", u, as_of, a["excerpt"]),
                       metric="auditor_change_events", value=a["answer"]))
    if ok and evs:
        cid = f"{ticker}.FPI_16F"
        claims.append(_claim(cid, f"최근 20-F {len(evs)}건의 Item 16F 감사인 변경 사건 {total}건", "HIGH", *evs))
        answers.append({"qid": "acc.auditor_change_3y", "status": "answered", "answer": total,
                        "claim_ids": [cid], "note": "20-F Item 16F(8-K 4.01 대응). 각 보고서는 직전 2개 회계연도를 덮는다 — "
                                                     "동일 사건은 한 번만 센다. 정기 교체·계열 법인 간 이관도 포함된다"})
    else:
        unknown("acc.auditor_change_3y", "20-F Item 16F를 읽지 못했다")
    # 소송(Item 8.A.7)
    lt = E.litigation_from_20f(b0)
    fpi["litigation"] = lt
    if lt.get("answer") and E.quote_in_text(lt["excerpt"], b0):
        cid = f"{ticker}.FPI_LIT"
        claims.append(_claim(cid, f"20-F Legal Proceedings 회사 진술 → {lt['answer']}", "HIGH",
            _ev("20-F 회사 자기 진술", _cit(doc0, "Item 8.A.7 Legal Proceedings", u0, as_of, lt["excerpt"]),
                note=lt["reason"])))
        answers.append({"qid": "gov.material_litigation", "status": "answered", "answer": lt["answer"],
                        "claim_ids": [cid], "note": "회사 자기 진술만 — 심각도를 판단하지 않는다"})
    else:
        unknown("gov.material_litigation", lt["reason"])
    # 임원·이사 합산 지분(Item 6.E/7.A)
    ig = E.insider_group_from_proxy(b0)
    fpi["insider_group"] = ig
    if ig.get("answer") and E.quote_in_text(ig["excerpt"], b0):
        cid = f"{ticker}.FPI_GROUP"
        claims.append(_claim(cid, f"20-F 임원·이사 합산 지분 {ig.get('pct')}% → {ig['answer']}", "MEDIUM",
            _ev("20-F 주요 주주표의 'as a group' 행", _cit(doc0, "Item 6.E / 7.A", u0, as_of, ig["excerpt"]),
                metric="insider_group_pct", value=ig.get("pct"), note=ig.get("rule", ""))))
        answers.append({"qid": "gov.insider_group_ownership", "status": "answered", "answer": ig["answer"],
                        "claim_ids": [cid], "note": "20-F 기준"})
    else:
        unknown("gov.insider_group_ownership", ig.get("reason", "20-F 지분표 확인 실패"))
    # 무배당 진술 → 배당 예측가능성 해당 없음
    nd = E.no_dividend_statement(b0)
    fpi["no_dividend"] = nd
    if nd:
        answers.append({"qid": "cap.dividend_predictable", "status": "not_applicable",
                        "note": f"회사가 무배당을 직접 진술: \"{nd}\" ({doc0}, {u0})"})


def collect_guidance(ticker, cik, as_of, facts):
    """8-K 2.02 EX-99.x → 원장 → 판정. 네트워크 실패는 호출부로 올린다(조용히 '없음'이 되지 않게)."""
    since = (datetime.date.fromisoformat(as_of) - datetime.timedelta(days=GUIDANCE_LOOKBACK_DAYS)).isoformat()
    listing = E.list_filings(cik, since, fetch_json)
    fpi = E.is_foreign_private_issuer(listing["all_forms"])
    if not listing["covers_window"]:
        return {"judge": None, "reason": "제출 목록이 가이던스 조회 창을 덮지 못했다"}
    actuals = GL.annual_revenue_actuals(facts, REVENUE_TAGS)
    if GL.label_ambiguous(actuals):
        return {"judge": None, "reason": "결산일이 1월 초인 해가 있어 회계연도 라벨이 모호하다(v3.61) — 짝짓기 거부"}
    releases = []
    # 외국 발행사는 실적 보도자료를 6-K로 낸다(8-K 2.02 의무 없음). 6-K는 실적 외 공시도 섞여 있지만
    # 가이던스 문장이 없는 문서는 추출 결과가 비므로 그대로 흘려보낸다.
    rows = ([r for r in listing["rows"] if r["form"] == "6-K" and r["filingDate"] >= since] if fpi
            else E.rows_with_item(listing, "2.02", since))
    for row in rows:
        acc = row["accessionNumber"]
        idx = fetch_text(f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc.replace('-', '')}/"
                         f"{acc}-index.htm")
        found = {}
        for url in GL.exhibit99_urls(idx):
            body = E.normalize_text(fetch_text(url))
            for gd in GL.extract_annual_revenue_guidance(body):
                if gd["fy"] not in found and E.quote_in_text(gd["excerpt"], body):
                    found[gd["fy"]] = dict(gd, url=url)
        releases.append({"filed": row["filingDate"], "accession": acc, "url": None,
                         "guidance": list(found.values())})
    ledger = GL.build_ledger(releases, actuals)
    jd = GL.judge(ledger, as_of)
    evaluated = [r for r in ledger if r["fy"] in jd["years"]]
    out = {"judge": jd, "ledger": ledger, "evaluated_rows": evaluated,
           "source_form": "6-K" if fpi else "8-K Item 2.02",
           "n_releases": len(releases), "n_with_guidance": sum(bool(r["guidance"]) for r in releases)}
    if not any(r["guidance"] for r in releases):
        src = "6-K" if fpi else "8-K 2.02 보도자료"
        out["reason"] = (f"{src} {len(releases)}건에서 연간 총매출 범위·'약 $X' 가이던스를 찾지 못했다 "
                         "(회사가 제시하지 않았거나 형식을 읽지 못함 — 둘을 구분하지 않는다)")
    return out


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
