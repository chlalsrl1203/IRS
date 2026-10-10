"""
QSI 개정본 — 2단계: 경쟁 대리지표 + 불성실 공시 부재 규칙 (v3.97)

채우는 질문(전부 사전 고정 규칙, `engine/competition_signals.py`·`engine/sec_events.py`):
  cmp.pricing_power      매출총이익률 3년 추세·수준(대리지표 — 원가 하락으로도 오른다)
  cmp.share_trend        회사가 직접 지명한 상장 경쟁사 묶음 대비 3년 매출 CAGR 격차(data/peer_baskets.json)
  cmp.lifecycle_shakeout_or_decline  회사+경쟁사 묶음 매출 CAGR
  cmp.new_threat         전년 대비 위험요인에 새로 추가된 경쟁 관련 문장(회사 자신의 새 인정)
  acc.unfaithful_disclosure  3년 재작성 없음 + 연차보고서에 확정적 제재·합의 진술 없음 → False
                             (진술이 있으면 사람이 읽도록 보류)

⚠️ unknown인 답만 채운다(merge 재사용). 판정·비중·ledger는 건드리지 않는다.
실행: python -m scripts.qsi_phase2 [--dry-run] [TICKER ...]
"""

import datetime
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from engine import competition_signals as C  # noqa: E402
from engine import guidance_ledger as GL  # noqa: E402
from engine import qualitative_input as Q  # noqa: E402
from engine import sec_events as E  # noqa: E402
from engine.filing_dates import fetch_company_facts, ticker_to_cik  # noqa: E402
from scripts.qsi_sec_events import (REVENUE_TAGS, _cit, _claim, _ev, fetch_json,  # noqa: E402
                                    fetch_text, merge)

REPORT_DIR = os.path.join(ROOT, "reports", "qsi_phase2")
PEERS = os.path.join(ROOT, "data", "peer_baskets.json")
GP_TAGS = ["GrossProfit"]
COST_TAGS = ["CostOfRevenue", "CostOfGoodsAndServicesSold", "CostOfSales",
             "CostOfRevenueExcludingDepreciationAndAmortization",
             "CostOfGoodsAndServicesSoldExcludingDepreciationDepletionAndAmortization"]
NEW_THREAT_QUOTES = 2


def _unit(facts):
    """매출이 USD로 없으면 보고 통화(실측: PDD는 CNY만 보고한다)."""
    for unit in ("USD", "CNY", "EUR"):
        if GL.annual_revenue_actuals(facts, REVENUE_TAGS, unit):
            return unit
    return "USD"


def _vals(series):
    return {y: v[0] for y, v in series.items()}


def collect(ticker, as_of, prior):
    cik = ticker_to_cik(ticker)
    cf_url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
    facts = fetch_company_facts(cik)
    unit = _unit(facts)
    claims, answers, findings, report = [], [], [], {"ticker": ticker, "as_of": as_of, "unit": unit}

    def unknown(qid, note):
        answers.append({"qid": qid, "status": "unknown", "note": note})

    rev_full = GL.annual_revenue_actuals(facts, REVENUE_TAGS, unit)
    rev = _vals(rev_full)

    # --- 가격결정력 대리 -----------------------------------------------------------------
    gm = C.gross_margins(rev, _vals(GL.annual_revenue_actuals(facts, GP_TAGS, unit)),
                         _vals(GL.annual_revenue_actuals(facts, COST_TAGS, unit)))
    pp = C.pricing_power_from_margins(rev, gm)
    report["pricing_power"] = pp
    if pp["answer"]:
        cid = f"{ticker}.GM"
        claims.append(_claim(cid, f"매출총이익률 FY{pp['fy_start']} {pp['gm_start']}% → FY{pp['fy_end']} {pp['gm_end']}% "
                                  f"({pp['gm_change_pp']:+.2f}%p) → {pp['answer']}", "MEDIUM",
            _ev("매출·매출총이익(또는 매출원가) 연차값(companyfacts)", _cit(f"{ticker} companyfacts",
                f"매출총이익률 FY{pp['fy_start']}~FY{pp['fy_end']} ({unit})", cf_url, as_of),
                metric="gross_margin_change_pp", value=pp["gm_change_pp"], note=pp["rule"])))
        answers.append({"qid": "cmp.pricing_power", "status": "answered", "answer": pp["answer"],
                        "claim_ids": [cid], "note": "총이익률 대리지표 — 원가 하락·제품 믹스·보조금(예: 생산세액공제)으로도 "
                                                     "움직인다. 가격 인상의 직접 증거가 아니다"})
    else:
        unknown("cmp.pricing_power", pp["reason"])

    # --- 지명 경쟁사 대비 상대 성장 ----------------------------------------------------------
    baskets = json.load(open(PEERS, encoding="utf-8"))["baskets"]
    if ticker in baskets:
        b = baskets[ticker]
        peers = {p: C.align_to(rev_full, GL.annual_revenue_actuals(
            fetch_company_facts(ticker_to_cik(p)), REVENUE_TAGS)) for p in b["peers"]}
        rg = C.relative_growth(rev, peers)
        report["relative_growth"] = rg | {"basket": b}
        if rg["answer"]:
            cid = f"{ticker}.PEERS"
            claims.append(_claim(cid,
                f"FY{rg['fy_start']}~FY{rg['fy_end']} 매출 CAGR {rg['company_cagr_pct']}% vs 지명 경쟁사 "
                f"{rg['peers_used']} 합계 {rg['peer_cagr_pct']}% → {rg['answer']}", "MEDIUM",
                _ev("회사가 연차보고서에서 직접 지명한 경쟁사", _cit(f"{ticker} 최신 연차보고서", "Competition",
                    "data/peer_baskets.json", as_of), note=f"근거 원문: {b['quote']} / 제외: {b['excluded']}"),
                _ev("회사·경쟁사 연차 매출(companyfacts, 결산일 기준 정렬)", _cit("companyfacts", "매출 FY 정렬",
                    cf_url, as_of), metric="growth_gap_pp", value=rg["gap_pp"], note=rg["rule"])))
            answers.append({"qid": "cmp.share_trend", "status": "answered", "answer": rg["answer"],
                            "claim_ids": [cid], "note": "시장점유율이 아니라 지명 경쟁사 묶음 대비 성장 격차"})
            if rg["lifecycle_decline"] is not None:
                answers.append({"qid": "cmp.lifecycle_shakeout_or_decline", "status": "answered",
                                "answer": rg["lifecycle_decline"], "claim_ids": [cid],
                                "note": f"회사+지명 경쟁사 매출 합계 CAGR {rg['basket_cagr_pct']}% — 생존 기업만 집계"})
            else:
                unknown("cmp.lifecycle_shakeout_or_decline",
                        f"묶음 CAGR {rg['basket_cagr_pct']}%가 판정 구간(0~3%) 사이")
        else:
            unknown("cmp.share_trend", rg["reason"])
    else:
        unknown("cmp.share_trend", "연차보고서가 SEC 공시 상장 경쟁사를 개별 지명하지 않았거나 지명된 회사가 "
                                   "거대 복합기업이라 비교군을 만들 수 없다(data/peer_baskets.json)")

    # --- 위험요인 신규 경쟁 문장 / 불성실 공시 ---------------------------------------------------
    since = (datetime.date.fromisoformat(as_of) - datetime.timedelta(days=800)).isoformat()
    listing = E.list_filings(cik, since, fetch_json)
    rows = sorted([r for r in listing["rows"] if r["form"] in ("10-K", "20-F")],
                  key=lambda r: r["filingDate"], reverse=True)[:2]
    if len(rows) < 2:
        unknown("cmp.new_threat", "최근 연차보고서 2건을 찾지 못했다")
    else:
        docs = [(r, E.filing_url(cik, r)) for r in rows]
        bodies = [E.normalize_text(fetch_text(u)) for _, u in docs]
        secs = [C.risk_factor_section(b, r["form"]) for (r, _), b in zip(docs, bodies)]
        nc = C.new_competition_sentences(secs[0], secs[1])
        report["new_competition"] = nc | {"docs": [r["filingDate"] for r in rows]}
        if nc.get("answer") is None:
            unknown("cmp.new_threat", nc["reason"])
        else:
            r0, u0 = docs[0]
            doc0 = f"{ticker} {r0['form']} (filed {r0['filingDate']})"
            quotes = [s for s in nc["sentences"] if E.quote_in_text(s, bodies[0])][:NEW_THREAT_QUOTES]
            cid = f"{ticker}.NEWTHREAT"
            evs = [_ev("전년 대비 새로 추가된 위험요인 문장", _cit(doc0, "Risk Factors", u0, as_of, q),
                       note=nc["rule"]) for q in quotes]
            if not evs:
                evs = [_ev(f"전년 대비 새 위험요인 문장 {nc['n_new_sentences']}개 중 경쟁 관련 0개",
                           _cit(doc0, "Risk Factors", u0, as_of), metric="new_competition_sentences", value=0,
                           note=nc["rule"] + f". 비교 대상: {rows[1]['form']} (filed {rows[1]['filingDate']})")]
            text = (f"전년 대비 새로 추가된 경쟁 관련 위험 문장 {nc['n_new_competition']}개: " +
                    " / ".join(f"「{q}」" for q in quotes)) if quotes else \
                "전년 대비 새로 추가된 경쟁 관련 위험 문장 없음"
            claims.append(_claim(cid, text[:900], "MEDIUM", *evs))
            answers.append({"qid": "cmp.new_threat", "status": "answered", "answer": text,
                            "claim_ids": [cid],
                            "note": "회사가 스스로 새로 인정한 위협만 모은다(문장 비교, 사람이 요약하지 않음). "
                                    "엔진 경쟁자 가중치와 직접 대조하지는 않았다"})
            findings.append({"lens": "competitive_landscape", "effect": "neutral", "claim_ids": [cid],
                             "summary": "위험요인 연도별 비교로 새 경쟁 위협 문장을 모음(판단 없음)"})
        # 불성실 공시 — 3년 재작성 없음(기존 답) + 확정적 제재 진술 없음
        restated = next((a for a in prior["answers"] if a["qid"] == "acc.restated_down_3y"), None)
        enf = E.enforcement_statements(bodies[0])
        report["enforcement"] = enf
        if enf:
            unknown("acc.unfaithful_disclosure", f"연차보고서에 제재·합의 진술 {len(enf)}건 — 사람이 읽어야 한다: {enf[0][:200]}")
        elif not restated or restated["status"] != "answered" or restated["answer"] is not False:
            unknown("acc.unfaithful_disclosure", "3년 재작성 여부가 확인되지 않아 '제재·정정 없음'을 단정하지 않는다")
        else:
            r0, u0 = docs[0]
            cid = f"{ticker}.NOENF"
            claims.append(_claim(cid, "최근 연차보고서에 SEC 제재·합의(Wells notice, 동의 명령, 기소유예 등) 진술 없음, "
                                      "3년 재작성 없음", "MEDIUM",
                _ev("연차보고서 전문 검색 — 확정적 제재·합의 진술 0건",
                    _cit(f"{ticker} {r0['form']} (filed {r0['filingDate']})", "전문", u0, as_of),
                    metric="enforcement_statements", value=0,
                    note="중요한 제재는 법적 절차(Item 103/8.A.7) 공시 대상이다. 위험요인의 가정문은 세지 않는다")))
            answers.append({"qid": "acc.unfaithful_disclosure", "status": "answered", "answer": False,
                            "claim_ids": [cid] + restated["claim_ids"],
                            "note": "공시된 제재·정정의 부재 — 비공개 조사까지 배제하지는 않는다"})
    return claims, answers, findings, report


def main(argv):
    dry = "--dry-run" in argv
    as_of = datetime.date.today().isoformat()
    tickers = [a for a in argv if not a.startswith("--")] or sorted(
        {f.split("_")[0] for f in os.listdir(Q.QUALITATIVE_DIR) if f.endswith(".json")})
    os.makedirs(REPORT_DIR, exist_ok=True)
    for t in tickers:
        prior = Q.latest_record(t)
        if prior is None or "competitive_landscape" not in Q.lenses_for(prior["lens_set"]):
            print(f"{t:5} 경쟁 축이 없는 질문 묶음 — 건너뜀")
            continue
        try:
            claims, answers, findings, report = collect(t, as_of, prior)
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
            print("      ->", os.path.relpath(Q.save_record(rec, supersedes=prior["sealed_core_hash"]), ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
