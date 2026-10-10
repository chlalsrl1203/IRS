"""
QSI v4.02 — SEC 의견서한 건수 + 개선된 위임장 지분표 파서로 남은 칸을 채운다

    python -m scripts.qsi_disclosure_extras [--dry-run] [TICKER ...]

- `acc.sec_comment_letters_3y`: `engine/comment_letters.py` 규칙(사전 고정).
- `gov.insider_group_ownership`: v4.02에서 고친 `sec_events.insider_group_from_proxy`로 **unknown인 칸만**
  다시 읽는다(answered는 merge가 덮지 않는다). 답을 얻은 경우에만 제출 — 못 얻으면 기존 사유를 그대로 둔다.
판정·비중·ledger 무관. 기존 봉인 파일은 건드리지 않고 개정본만 쌓는다.
"""

import datetime
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from engine import comment_letters as CL  # noqa: E402
from engine import qualitative_input as Q  # noqa: E402
from engine import sec_events as E  # noqa: E402
from engine.filing_dates import ticker_to_cik  # noqa: E402
from scripts.qsi_sec_events import _cit, _claim, _ev, fetch_json, fetch_text, merge  # noqa: E402

REPORT_DIR = os.path.join(ROOT, "reports", "qsi_disclosure_extras")
LOOKBACK_DAYS = 3 * 365


def collect(ticker, as_of, prior):
    bank = {q.qid for q in Q.bank_for(prior["lens_set"])}
    cik = ticker_to_cik(ticker)
    since = (datetime.date.fromisoformat(as_of) - datetime.timedelta(days=LOOKBACK_DAYS)).isoformat()
    listing = E.list_filings(cik, since, fetch_json)
    claims, answers, report = [], [], {"ticker": ticker, "as_of": as_of, "cik": cik, "since": since}

    if "acc.sec_comment_letters_3y" in bank:
        cl = CL.count_letters(listing, since, as_of)
        topics = {}
        for r in cl.get("corresp_rows", []):
            if r["primaryDocument"].lower().endswith((".htm", ".html", ".txt")):
                try:
                    topics[r["filingDate"]] = CL.corresp_topics(E.normalize_text(fetch_text(E.filing_url(cik, r))))
                except Exception as e:
                    topics[r["filingDate"]] = [f"읽기 실패: {type(e).__name__}"]
        report["comment_letters"] = {k: v for k, v in cl.items() if k != "corresp_rows"} | {"corresp_topics": topics}
        if cl["status"] == "OK":
            cid = f"{ticker}.SEC_COMMENT_LETTERS"
            browse = (f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={int(cik)}"
                      "&type=UPLOAD&dateb=&owner=include&count=40")
            claims.append(_claim(cid, f"{since}~{as_of} SEC 의견서한(UPLOAD) {cl['answer']}건, 회사 답변(CORRESP) "
                                      f"{cl['n_corresp']}건", "MEDIUM",
                _ev("EDGAR 제출 목록의 UPLOAD 건수", _cit(f"{ticker} EDGAR 제출 목록", "form=UPLOAD", browse, as_of, ""),
                    metric="sec_comment_letters_3y", value=cl["answer"],
                    note="등록신고서 검토·종결 서한 포함, 공개는 검토 종료 후 20일 이상 지연. 품질 판정 아님")))
            answers.append({"qid": "acc.sec_comment_letters_3y", "status": "answered",
                            "answer": cl["answer"], "claim_ids": [cid], "note": ""})
        else:
            answers.append({"qid": "acc.sec_comment_letters_3y", "status": "unknown", "note": cl["reason"]})

    cur = next((a for a in prior["answers"] if a["qid"] == "gov.insider_group_ownership"), None)
    if cur is not None and cur["status"] == "unknown":
        ig = E.collect_insider_group(listing, fetch_text, cik, as_of)
        igr = ig.get("result") if ig["status"] == "OK" else None
        report["insider_group"] = {k: v for k, v in ig.items() if k != "result"} | {"result": igr}
        if igr and igr.get("answer"):
            cid = f"{ticker}.INSIDERGROUP"
            claims.append(_claim(cid,
                f"위임장({ig['filing_date']}) 기준 임원·이사 합산 지분 구간 {igr['answer']}"
                + (f" ({igr['pct']}%)" if igr.get("pct") is not None else " ('*' = 1% 미만 표기)"), "MEDIUM",
                _ev("DEF 14A 지분표의 임원·이사 합산 행(v4.02 파서)",
                    _cit(f"{ticker} DEF 14A (filed {ig['filing_date']}, acc {ig['accession']})",
                         "Security Ownership 표 — 합산 행", ig["url"], as_of, igr["excerpt"]),
                    metric="insider_group_pct", value=igr.get("pct"), note=igr["rule"])))
            answers.append({"qid": "gov.insider_group_ownership", "status": "answered",
                            "answer": igr["answer"], "claim_ids": [cid], "note": ""})
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
            continue
        try:
            claims, answers, report = collect(t, as_of, prior)
            core, changed = merge(prior, claims, answers, [], as_of)
            rec = Q.build_record(core)
        except Exception as e:
            print(f"{t:5} 실패: {type(e).__name__}: {e}")
            continue
        got = {a["qid"]: a for a in rec["answers"]}
        cl = got.get("acc.sec_comment_letters_3y")
        ig = got.get("gov.insider_group_ownership")
        print(f"{t:5} letters={cl['answer'] if cl and cl['status'] == 'answered' else (cl or {}).get('status')}  "
              f"insider_group={ig['answer'] if ig and ig['status'] == 'answered' else (ig or {}).get('status')}  "
              f"topics={report.get('comment_letters', {}).get('corresp_topics')}")
        with open(os.path.join(REPORT_DIR, f"{t}_{as_of}.json"), "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2, sort_keys=True, default=str)
            f.write("\n")
        if not dry and rec["sealed_core_hash"] != prior["sealed_core_hash"]:
            print("      ->", os.path.relpath(Q.save_record(rec, supersedes=prior["sealed_core_hash"]), ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
