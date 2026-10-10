"""
QSI v4.00 — 위임장 PvP 표·Item 408 매매계획(ecd inline XBRL)으로 거버넌스 질문 3개를 채운다

    python -m scripts.qsi_ecd [--dry-run] [TICKER ...]

규칙은 `engine/ecd.py` docstring에 수집 전 고정. 이미 answered인 답은 덮지 않고(merge 재사용),
기존 봉인 파일은 건드리지 않고 개정본을 쌓는다. 판정·비중·ledger 무관.
"""

import datetime
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from engine import ecd  # noqa: E402
from engine import qualitative_input as Q  # noqa: E402
from engine import sec_events as E  # noqa: E402
from engine.filing_dates import ticker_to_cik  # noqa: E402
from scripts.qsi_sec_events import _cit, _claim, _ev, fetch_json, fetch_text, merge  # noqa: E402

REPORT_DIR = os.path.join(ROOT, "reports", "qsi_ecd")
PROXY_WINDOW_DAYS = 456          # 연 1회 위임장 + 3개월 여유(15개월)
PERIODIC_WINDOW_DAYS = 365
QIDS = ("gov.pay_measure_category", "gov.pvp_tsr_vs_peer", "gov.trading_plan_adoptions_12m")
FPI_NOTE = ("외국 발행사(20-F) — 위임장 PvP 표(Reg S-K 402(v))와 Item 408 매매계획 공시 의무가 없다"
            "(제도 부재, 규칙 기반 해당 없음)")


def _quote(text, body):
    """보이는 글자가 원문에 그대로 있으면 인용으로 쓴다. 아니면 빈 인용(지어내지 않는다)."""
    t = (text or "").strip()
    return t if t and E.quote_in_text(t, body) else ""


def collect(ticker, as_of):
    cik = ticker_to_cik(ticker)
    since = (datetime.date.fromisoformat(as_of) - datetime.timedelta(days=PROXY_WINDOW_DAYS)).isoformat()
    listing = E.list_filings(cik, since, fetch_json)
    claims, answers, report = [], [], {"ticker": ticker, "as_of": as_of, "cik": cik}

    def unknown(qid, note):
        answers.append({"qid": qid, "status": "unknown", "note": note})

    if E.is_foreign_private_issuer(listing["all_forms"]):
        for qid in QIDS:
            answers.append({"qid": qid, "status": "not_applicable", "note": FPI_NOTE})
        report["fpi"] = True
        return claims, answers, report

    # --- PvP (DEF 14A) -------------------------------------------------------------
    proxies = sorted((r for r in listing["rows"] if r["form"] == "DEF 14A"),
                     key=lambda r: r["filingDate"], reverse=True)
    if not proxies:
        for qid in QIDS[:2]:
            unknown(qid, "조회 창(15개월) 안에 DEF 14A가 없다")
    else:
        r = proxies[0]
        url = E.filing_url(cik, r)
        try:
            html = fetch_text(url)
            pvp = ecd.pvp_from_proxy(html)
        except Exception as e:  # 한 문서 실패가 나머지를 막지 않게
            pvp = {"status": "FETCH_FAILED", "reason": f"{type(e).__name__}: {e}"}
            html = ""
        report["pvp"] = {"accession": r["accessionNumber"], "filed": r["filingDate"], "url": url,
                         **{k: v for k, v in pvp.items()}}
        doc = f"{ticker} DEF 14A ({r['filingDate']}, acc {r['accessionNumber']})"
        body = E.normalize_text(html) if html else ""
        if pvp.get("status") == "OK" and pvp.get("measure_category"):
            cid = f"{ticker}.PVP_MEASURE"
            claims.append(_claim(cid, f"회사 선정 지표 '{pvp['measure_name']}' → {pvp['measure_category']}", "MEDIUM",
                _ev("PvP 표 ecd:CoSelectedMeasureName",
                    _cit(doc, "ecd:CoSelectedMeasureName", url, as_of, _quote(pvp["measure_name"], body)),
                    note="engine/ecd.py MEASURE_RULES 순서대로 키워드 분류(사전 고정)")))
            answers.append({"qid": "gov.pay_measure_category", "status": "answered",
                            "answer": pvp["measure_category"], "claim_ids": [cid], "note": ""})
        else:
            unknown("gov.pay_measure_category", pvp.get("reason") or "회사 선정 지표(ecd:CoSelectedMeasureName)가 없다")
        if pvp.get("status") == "OK" and pvp.get("tsr_vs_peer") is not None:
            cid = f"{ticker}.PVP_TSR"
            claims.append(_claim(cid,
                f"{pvp['period_end']} 누적 TSR {pvp['tsr']:.2f} vs 비교군 {pvp['peer_tsr']:.2f} "
                f"→ {pvp['tsr_vs_peer']:+.1%}", "MEDIUM",
                _ev("PvP 표 ecd:TotalShareholderRtnAmt / PeerGroupTotalShareholderRtnAmt",
                    _cit(doc, f"ecd TSR ({pvp['period_end']})", url, as_of, ""),
                    metric="pvp_tsr_vs_peer", value=round(pvp["tsr_vs_peer"], 4),
                    note="같은 시점 $100 투자의 누적 가치 비율. 비교군은 회사가 고른 것")))
            answers.append({"qid": "gov.pvp_tsr_vs_peer", "status": "answered",
                            "answer": round(pvp["tsr_vs_peer"], 4), "claim_ids": [cid], "note": ""})
        else:
            unknown("gov.pvp_tsr_vs_peer", pvp.get("reason") or "TSR·비교군 TSR 쌍이 없다")

    # --- Item 408 매매계획 (10-Q·10-K, 12개월) ---------------------------------------
    p_since = (datetime.date.fromisoformat(as_of) - datetime.timedelta(days=PERIODIC_WINDOW_DAYS)).isoformat()
    periodic = sorted((r for r in listing["rows"]
                       if r["form"] in ("10-Q", "10-K") and p_since < r["filingDate"] <= as_of),
                      key=lambda r: r["filingDate"])
    per, rep = [], []
    for r in periodic:
        try:
            tp = ecd.trading_plans_from_periodic(fetch_text(E.filing_url(cik, r)))
        except Exception as e:
            tp = {"has_block": False, "adoptions": 0, "terminations": 0, "individuals": [],
                  "error": f"{type(e).__name__}: {e}"}
        per.append((r["filingDate"], tp))
        rep.append({"form": r["form"], "filed": r["filingDate"], "accession": r["accessionNumber"], **tp})
    agg = ecd.trading_plan_adoptions(per)
    report["trading_plans"] = {"reports": rep, **agg}
    if agg["status"] == "OK":
        cid = f"{ticker}.TRADING_PLANS"
        last = periodic[-1]
        claims.append(_claim(cid,
            f"최근 12개월 정기보고서 {agg['n_reports']}건의 Item 408: 매매계획 채택 {agg['answer']}건, "
            f"해지 {agg['terminations']}건", "MEDIUM",
            _ev("ecd:TrdArrAdoptionDate 사실 수 집계",
                _cit(f"{ticker} {last['form']} 외 {agg['n_reports'] - 1}건", "Item 408 (ecd)",
                     E.filing_url(cik, last), as_of, ""),
                metric="trading_plan_adoptions_12m", value=agg["answer"],
                note="채택은 10b5-1·비10b5-1 합계. 매도 신호인지 판단하지 않는다")))
        answers.append({"qid": "gov.trading_plan_adoptions_12m", "status": "answered",
                        "answer": agg["answer"], "claim_ids": [cid], "note": ""})
    else:
        unknown("gov.trading_plan_adoptions_12m", agg["reason"])
    return claims, answers, report


def main(argv):
    dry = "--dry-run" in argv
    as_of = datetime.date.today().isoformat()
    tickers = [a for a in argv if not a.startswith("--")] or sorted(
        {f.split("_")[0] for f in os.listdir(Q.QUALITATIVE_DIR) if f.endswith(".json")})
    os.makedirs(REPORT_DIR, exist_ok=True)
    for t in tickers:
        prior = Q.latest_record(t)
        if prior is None:
            print(f"{t:5} 기존 QSI 기록 없음 — 건너뜀")
            continue
        try:
            claims, answers, report = collect(t, as_of)
            core, changed = merge(prior, claims, answers, [], as_of)
            rec = Q.build_record(core)
        except Exception as e:
            print(f"{t:5} 실패: {type(e).__name__}: {e}")
            continue
        got = {a["qid"]: a for a in rec["answers"] if a["qid"] in QIDS}
        print(f"{t:5} " + "  ".join(f"{q.split('.')[1]}={got[q]['answer'] if got[q]['status'] == 'answered' else got[q]['status']}"
                                    for q in QIDS if q in got))
        with open(os.path.join(REPORT_DIR, f"{t}_{as_of}.json"), "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2, sort_keys=True, default=str)
            f.write("\n")
        if not dry and rec["sealed_core_hash"] != prior["sealed_core_hash"]:
            print("      ->", os.path.relpath(Q.save_record(rec, supersedes=prior["sealed_core_hash"]), ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
