"""
QSI v4.01 — 비정기 가이던스 하향으로 `acc.voluntary_bad_news`를 채운다

    python -m scripts.qsi_bad_news [--dry-run] [TICKER ...]

규칙은 `engine/bad_news.py` docstring에 수집 전 고정(True만 단언). 이미 answered인 답은 덮지 않고
개정본만 쌓는다. 판정·비중·ledger 무관.
"""

import datetime
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from engine import bad_news as BN  # noqa: E402
from engine import guidance_ledger as GL  # noqa: E402
from engine import qualitative_input as Q  # noqa: E402
from engine import sec_events as E  # noqa: E402
from engine.filing_dates import ticker_to_cik  # noqa: E402
from scripts.qsi_sec_events import _cit, _claim, _ev, fetch_json, fetch_text, merge  # noqa: E402

REPORT_DIR = os.path.join(ROOT, "reports", "qsi_bad_news")
LOOKBACK_DAYS = 3 * 365
ITEMS = ("2.02", "7.01", "8.01")
QID = "acc.voluntary_bad_news"


def collect(ticker, as_of):
    cik = ticker_to_cik(ticker)
    since = (datetime.date.fromisoformat(as_of) - datetime.timedelta(days=LOOKBACK_DAYS)).isoformat()
    listing = E.list_filings(cik, since, fetch_json)
    report = {"ticker": ticker, "as_of": as_of, "cik": cik, "since": since}
    if E.is_foreign_private_issuer(listing["all_forms"]):
        report["fpi"] = True
        return [], [{"qid": QID, "status": "unknown",
                     "note": "외국 발행사(6-K) — 정기/비정기 발표를 구분할 Item 번호가 없어 이 규칙을 적용하지 않는다"}], report
    if not listing["covers_window"]:
        return [], [{"qid": QID, "status": "unknown", "note": "제출 목록이 3년 창을 덮지 못했다"}], report

    periodic = [r["filingDate"] for r in listing["rows"] if r["form"] in ("10-Q", "10-K")]
    r202 = E.rows_with_item(listing, "2.02", since)
    sched = BN.scheduled_releases([r["filingDate"] for r in r202], periodic)
    sched_acc = {r["accessionNumber"] for r in r202 if r["filingDate"] in sched}
    rows = {}
    for it in ITEMS:
        for r in E.rows_with_item(listing, it, since):
            rows[r["accessionNumber"]] = r
    releases = []
    for acc, r in sorted(rows.items(), key=lambda kv: kv[1]["filingDate"]):
        idx = fetch_text(f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc.replace('-', '')}/{acc}-index.htm")
        found = {}
        for url in GL.exhibit99_urls(idx):
            body = E.normalize_text(fetch_text(url))
            for g in GL.extract_annual_revenue_guidance(body):
                if g["fy"] not in found and E.quote_in_text(g["excerpt"], body):
                    found[g["fy"]] = dict(g, url=url)
        is_202 = "2.02" in [x.strip() for x in (r["items"] or "").split(",")]
        releases.append({"filed": r["filingDate"], "accession": acc, "items": r["items"],
                         "scheduled": bool(is_202 and acc in sched_acc), "guidance": list(found.values())})
    cuts = BN.guidance_cuts(releases)
    res = BN.voluntary_bad_news(cuts, len(releases), sum(bool(x["guidance"]) for x in releases))
    report.update({"n_periodic": len(periodic), "n_scheduled": len(sched_acc), "n_releases": len(releases),
                   "releases": releases, "cuts": cuts, "result": {k: v for k, v in res.items() if k != "evidence"}})
    if res["status"] != "answered":
        return [], [{"qid": QID, "status": "unknown", "note": "비정기 가이던스 하향 규칙: " + res["reason"]}], report
    c = res["evidence"][0]
    cid = f"{ticker}.VOLUNTARY_BAD_NEWS"
    evs = [_ev(f"FY{x['fy']} 매출 가이던스 {x['prev']['low']:,.0f}~{x['prev']['high']:,.0f} → "
               f"{x['new']['low']:,.0f}~{x['new']['high']:,.0f} ({x['change_pct']:+.1%}), 비정기 8-K(Item {x['items']})",
               _cit(f"{ticker} 8-K ({x['filed']}, acc {x['accession']})", "EX-99", x["url"], as_of, x["excerpt"]),
               direction="supports", note=res["rule"]) for x in res["evidence"][:3]]
    claims = [_claim(cid, f"정기 실적 발표 전 가이던스 하향을 먼저 공시({c['filed']} 외 {len(res['evidence']) - 1}건)",
                     "MEDIUM", *evs)]
    return claims, [{"qid": QID, "status": "answered", "answer": True, "claim_ids": [cid], "note": ""}], report


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
        if QID not in {q.qid for q in Q.bank_for(prior["lens_set"])}:
            print(f"{t:5} 이 업종 변형({prior['lens_set']})에는 회계품질 축이 없다 — 건너뜀")
            continue
        try:
            claims, answers, report = collect(t, as_of)
            core, changed = merge(prior, claims, answers, [], as_of)
            rec = Q.build_record(core)
        except Exception as e:
            print(f"{t:5} 실패: {type(e).__name__}: {e}")
            continue
        a = next(x for x in rec["answers"] if x["qid"] == QID)
        print(f"{t:5} {a['status']:8} {a.get('answer')!s:5} cuts={len(report.get('cuts', []))} "
              f"rel={report.get('n_releases', '-')} {a.get('note', '')[:90]}")
        with open(os.path.join(REPORT_DIR, f"{t}_{as_of}.json"), "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2, sort_keys=True, default=str)
            f.write("\n")
        if not dry and rec["sealed_core_hash"] != prior["sealed_core_hash"]:
            print("      ->", os.path.relpath(Q.save_record(rec, supersedes=prior["sealed_core_hash"]), ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
