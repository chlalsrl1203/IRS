"""
QSI 3단계 증거 묶음 — 판독자가 읽을 원문 발췌를 종목·질문별로 모은다 (v3.98)

판독자(사람·모델)는 이 묶음 **안의 원문만** 근거로 답한다(`docs/qsi_reading_rubric.md`). 발췌는 SEC 원문을
정규화한 텍스트의 연속 구간이고 출처 URL을 함께 남겨, 답의 인용문을 코드가 원문과 글자 단위로 대조할 수 있다.

- 아직 답하지 못한(unknown·미질문) 질문에 대해서만 발췌를 만든다.
- 발췌 선택은 정규식 창(window)일 뿐 판단이 아니다. 놓친 원문이 있을 수 있으므로 판독자는 확신이 없으면
  unknown으로 남긴다.

실행: python -m scripts.qsi_evidence_pack [TICKER ...] → reports/qsi_reading/packs/<T>.json
"""

import datetime
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from engine import guidance_ledger as GL  # noqa: E402
from engine import qualitative_input as Q  # noqa: E402
from engine import sec_events as E  # noqa: E402
from engine.filing_dates import ticker_to_cik  # noqa: E402
from scripts.qsi_sec_events import fetch_json, fetch_text  # noqa: E402

PACK_DIR = os.path.join(ROOT, "reports", "qsi_reading", "packs")
MAX_PER_TOPIC = 4
WIN_BEFORE, WIN_AFTER = 250, 900

TOPICS = {
    # qid: [(문서 종류, 정규식, 앞, 뒤)]
    "gov.key_person_no_succession": [
        ("annual", r"\bdepend\w*\s+(?:heavily\s+|substantially\s+|significantly\s+)?(?:on|upon)\s+[^.]{0,120}"
                   r"(?:key\s+personnel|senior\s+management|executive\s+officers|founders?|Chief\s+Executive|CEO|"
                   r"co-?founder|management\s+team)", 250, 600),
        ("proxy", r"succession", 300, 500), ("annual", r"succession\s+plan", 300, 500)],
    "gov.ceo_succession_policy": [("proxy", r"succession", 300, 500), ("annual", r"succession", 300, 500)],
    "gov.chair_separated": [
        ("proxy", r"(?:Chair(?:man|person)?\s+of\s+the\s+Board|Board\s+Chair|Executive\s+Chair|"
                  r"Lead\s+Independent\s+Director|roles\s+of\s+(?:the\s+)?Chair)", 250, 500),
        ("annual", r"(?:Chair(?:man|person)?\s+of\s+(?:the|our)\s+Board|Executive\s+Chair)", 250, 400)],
    "gov.material_litigation": [
        ("annual", r"(?:Item\s+3\.?\s*Legal\s+Proceedings|Legal\s+(?:and\s+\w+\s+)?Proceedings|Litigation\s+and\s+"
                   r"(?:Regulatory|Other)|Loss\s+Contingenc|Contingencies)", 100, 1500)],
    "acc.material_one_time_items": [
        ("release", r"(?:restructuring|impairment|litigation|settlement|gain\s+on|loss\s+on|acquisition[- ]related|"
                    r"transaction[- ]related|divest|non-?recurring|one-?time)", 300, 700)],
    "acc.voluntary_bad_news": [
        ("release_all", r"(?:lower(?:ed|ing)?|reduc(?:e|ed|ing)|withdr(?:aw|ew|awn)|cut|below)\s+[^.]{0,80}"
                        r"(?:guidance|outlook|expectations?)", 300, 400),
        ("release_all", r"(?:guidance|outlook)[^.]{0,60}(?:lower(?:ed)?|reduc(?:ed|ing)|withdr(?:aw|ew|awn))",
         300, 400)],
    "gov.insider_group_ownership": [("proxy", r"as\s+a\s+group", 900, 400), ("annual", r"as\s+a\s+group", 900, 400)],
    "cap.ma_discipline": [
        ("annual", r"acqui\w+[^.]{0,160}\$\s?[\d.,]+\s*(?:billion|million)", 200, 500),
        ("annual", r"impairment[^.]{0,80}goodwill|goodwill[^.]{0,80}impairment", 200, 500),
        ("annual", r"terminat\w+[^.]{0,80}(?:merger|acquisition)\s+agreement|termination\s+fee", 200, 500)],
    "cmp.share_trend": [
        ("annual", r"(?:market\s+share|share\s+of\s+the\s+market|largest|leading|market\s+leader|#\s?1|number\s+one)",
         200, 400),
        ("release", r"(?:market\s+share|gain(?:ed|ing)?\s+share|share\s+gains?)", 250, 350)],
    "cmp.lifecycle_shakeout_or_decline": [
        ("annual", r"(?:market|industry)\s+(?:is\s+)?(?:grow\w*|expand\w*|declin\w*|shrink\w*|consolidat\w*|"
                   r"matur\w*|fragment\w*)", 200, 400)],
    "acc.guidance_miss_3y": [("release_all", r"(?:outlook|guidance)", 100, 600)],
    "cap.dividend_predictable": [("annual", r"dividend", 250, 400)],
    "cap.debt_funded_buyback": [
        ("annual", r"(?:no\s+(?:outstanding\s+)?(?:borrowings|debt|indebtedness)|outstanding\s+borrowings|"
                   r"revolving\s+credit|term\s+loan)", 250, 400),
        ("annual", r"repurchas\w+[^.]{0,120}(?:\$\s?[\d.,]+|shares)", 200, 500)],
    "uw.combined_ratio_pct": [("annual", r"combined\s+ratio", 300, 500)],
    "cat.cat_exposure": [("annual", r"catastroph\w+\s+(?:loss|losses|events?)", 250, 500),
                         ("annual", r"reinsurance\s+(?:program|protection|coverage|treaty)", 250, 500)],
    "cap.buyback_effect": [("annual", r"(?:weighted[- ]average[^.]{0,60}diluted|repurchas\w+[^.]{0,120}shares)",
                            250, 500)],
    "dil.net_share_change_3y_pct": [("annual", r"weighted[- ]average[^.]{0,60}diluted", 300, 600)],
    "gov.cxo_turnover_24m": [("annual", r"(?:appointed|resigned|stepped\s+down|succeeded|joined\s+us)[^.]{0,120}"
                                        r"(?:Chief\s+Executive|Chief\s+Financial|CEO|CFO)", 250, 400)],
    "acc.material_impairment_3y": [("annual", r"impairment", 250, 500)],
    "gov.dual_class": [("annual", r"Class\s+[AB]\s+(?:common|ordinary)", 200, 500)],
    "acc.unfaithful_disclosure": [("annual", r"(?:non|deferred)[- ]prosecution|Wells\s+notice|consent\s+order|"
                                             r"settled[^.]{0,60}(?:SEC|Commission)", 300, 600)],
    "acc.restated_down_3y": [("annual", r"restat\w+", 250, 500)],
    "acc.icfr_conclusion": [("annual", r"internal\s+control\s+over\s+financial\s+reporting\s+(?:was|is)", 300, 300)],
    "cmp.pricing_power": [("annual", r"(?:pricing|price\s+increases?|take\s+rate)", 200, 400)],
    "cmp.new_threat": [("annual", r"compet\w+", 200, 400)],
    "gov.insider_pattern": [("annual", r"(?:purchased|sold)\s+[^.]{0,60}(?:ordinary\s+shares|ADSs)", 200, 300)],
    "dil.sbc_to_fcf_pct": [("annual", r"share[- ]based\s+compensation", 200, 300)],
}
TOPICS["acc.promise_kept_record"] = TOPICS["acc.guidance_miss_3y"]


def _windows(body, pat, before, after, cap=MAX_PER_TOPIC):
    out, last_end = [], -1
    for m in re.finditer(pat, body, re.I):
        s, e = max(0, m.start() - before), min(len(body), m.end() + after)
        if s < last_end:              # 겹치는 창은 합치지 않고 건너뛴다(중복 읽기 방지)
            continue
        out.append(body[s:e])
        last_end = e
        if len(out) >= cap:
            break
    return out


def _docs(ticker, as_of):
    cik = ticker_to_cik(ticker)
    since = (datetime.date.fromisoformat(as_of) - datetime.timedelta(days=1100)).isoformat()
    listing = E.list_filings(cik, since, fetch_json)
    fpi = E.is_foreign_private_issuer(listing["all_forms"])
    rows = sorted(listing["rows"], key=lambda r: r["filingDate"], reverse=True)
    docs = {}
    ann = [r for r in rows if r["form"] in ("10-K", "20-F")]
    if ann:
        docs["annual"] = [(ann[0], E.filing_url(cik, ann[0]))]
    px = [r for r in rows if r["form"] == "DEF 14A"]
    if px:
        docs["proxy"] = [(px[0], E.filing_url(cik, px[0]))]
    rel_rows = [r for r in rows if r["form"] == "6-K"] if fpi else E.rows_with_item(listing, "2.02", since)
    rel_rows = sorted(rel_rows, key=lambda r: r["filingDate"], reverse=True)
    rels = []
    for r in rel_rows[: (24 if fpi else 12)]:
        acc = r["accessionNumber"]
        idx = fetch_text(f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc.replace('-', '')}/{acc}-index.htm")
        for u in GL.exhibit99_urls(idx)[:2]:
            rels.append((r, u))
    docs["release_all"] = rels
    docs["release"] = rels[:4]
    return cik, fpi, docs


def build_pack(ticker, as_of):
    rec = Q.latest_record(ticker)
    have = {a["qid"]: a for a in rec["answers"]}
    targets = [q.qid for q in Q.bank_for(rec["lens_set"])
               if q.qid not in have or have[q.qid]["status"] == "unknown"]
    cik, fpi, docs = _docs(ticker, as_of)
    bodies = {}
    excerpts, n = [], 0
    for qid in targets:
        for kind, pat, before, after in TOPICS.get(qid, []):
            for row, url in docs.get(kind, []):
                if url not in bodies:
                    bodies[url] = E.normalize_text(fetch_text(url))
                for w in _windows(bodies[url], pat, before, after):
                    if any(w == x["text"] for x in excerpts):
                        continue
                    n += 1
                    excerpts.append({"id": f"{ticker}-{n}", "for": qid, "doc": f"{row['form']} filed {row['filingDate']}",
                                     "url": url, "text": w})
    unknown_notes = {qid: (have[qid]["note"] if qid in have else "미질문") for qid in targets}
    return {"ticker": ticker, "as_of": as_of, "lens_set": rec["lens_set"], "foreign_private_issuer": fpi,
            "based_on_record": rec["sealed_core_hash"], "targets": targets, "prior_unknown_notes": unknown_notes,
            "excerpts": excerpts}


def main(argv):
    as_of = datetime.date.today().isoformat()
    tickers = [a for a in argv if not a.startswith("--")] or sorted(
        {f.split("_")[0] for f in os.listdir(Q.QUALITATIVE_DIR) if f.endswith(".json")})
    os.makedirs(PACK_DIR, exist_ok=True)
    for t in tickers:
        try:
            pack = build_pack(t, as_of)
        except Exception as e:
            print(f"{t:5} 실패: {type(e).__name__}: {e}")
            continue
        with open(os.path.join(PACK_DIR, f"{t}.json"), "w", encoding="utf-8") as f:
            json.dump(pack, f, ensure_ascii=False, indent=1)
            f.write("\n")
        size = sum(len(x["text"]) for x in pack["excerpts"])
        print(f"{t:5} 질문 {len(pack['targets']):2} 발췌 {len(pack['excerpts']):3} ({size:,}자)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
