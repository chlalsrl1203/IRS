"""
auto_analysis_ci.py (v4.03) — 연구 우선순위 큐 상위 종목을 규칙 기반으로 자동 정식분석한다.

Claude·API 비용 없이 GitHub Actions만으로 돈다. 판단 입력은 engine/auto_analysis.py의
사전 고정 규칙이 채우고, 결과는 **`ledger_auto/`에만** 저장한다(`ledger/` 불가침).

  - 대상: reports/research_queue.json 의 QUEUED·검증범위 안 종목을 우선순위 순으로 N개
  - 시가총액: ALPHA_VANTAGE_API_KEY가 있으면 실시간, 없으면 큐의 public_float 근사(낡음 — 리포트에 표시)
  - 재실행 정책: ledger_auto에 30일 이내 결과가 있으면 건너뜀, 거부된 종목은 90일간 재시도 안 함
  - 요약: reports/auto_analysis/<날짜>.json (+ --post 시 날짜별 이슈 댓글)
"""
import datetime
import glob
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.validated_scope import CORPUS_MARKET_CAP_MAX, CORPUS_MARKET_CAP_MIN
from engine.auto_analysis import AutoAnalysisRefused, auto_analyze
from engine.pipeline import save_ledger

QUEUE_PATH = "reports/research_queue.json"
AUTO_LEDGER_DIR = "ledger_auto"
REPORT_DIR = "reports/auto_analysis"
REFUSED_PATH = os.path.join(REPORT_DIR, "refused.json")
FRESH_DAYS, REFUSED_DAYS = 30, 90
DEFAULT_LIMIT = 10
SUSPECT_FCF_YIELD = 0.25   # engine의 스케일 이상 탐지 밴드 상한(ledger 실측 최대 17.95%)


def log(m):
    print(m, flush=True)


def _days_since(date_str, today):
    return (datetime.date.fromisoformat(today) - datetime.date.fromisoformat(date_str)).days


def watchlist_candidates(path="watchlist.json", official_dir="ledger", excluded=None):
    """사용자가 직접 지정한 종목 중 공식 ledger가 없는 것. 스크리닝 큐와 무관한 공급원."""
    if not os.path.exists(path):
        return []
    tickers = [t.strip().upper() for t in json.load(open(path, encoding="utf-8")).get("tickers", [])]
    out = []
    for t in dict.fromkeys(tickers):
        if glob.glob(os.path.join(official_dir, f"{t}_*.json")) or t in (excluded or {}):
            continue
        out.append({"ticker": t, "state": "QUEUED", "in_validated_scope": True,
                    "market_cap": None, "latest_gap": None, "source": "watchlist"})
    return out


def pick_candidates(queue, today, limit, ledger_dir=AUTO_LEDGER_DIR, refused=None, extra=None):
    from engine.research_queue import priority_order

    refused = refused or {}
    fresh = set()
    for p in glob.glob(os.path.join(ledger_dir, "*.json")):
        name = os.path.basename(p)[:-5]
        t, _, d = name.rpartition("_")
        try:
            if _days_since(d, today) <= FRESH_DAYS:
                fresh.add(t)
        except ValueError:
            pass
    out = []
    for e in list(extra or []) + priority_order(list(queue["entries"].values())):
        t = e["ticker"]
        if e.get("state") != "QUEUED":
            continue
        # 검증범위 안이거나, 시총만 범위 안인 Gap 이상치(스크린 Gap이 코퍼스 최대를 넘음)는 허용한다.
        # 시총이 범위 밖인 초소형·초대형은 자동 분석 대상에서 제외(근사 시총 오차가 판정을 좌우).
        mc = e.get("market_cap")
        gap_only = (not e.get("in_validated_scope") and mc
                    and CORPUS_MARKET_CAP_MIN <= mc <= CORPUS_MARKET_CAP_MAX)
        if not (e.get("in_validated_scope") or gap_only):
            continue
        if t in fresh:
            continue
        r = refused.get(t)
        if r and _days_since(r["date"], today) <= REFUSED_DAYS:
            continue
        out.append(e)
        if len(out) >= limit:
            break
    return out


def fetch_series(ticker, today):
    from engine.data.providers.sec import SecCompanyFactsProvider
    from scripts import daily_screen as ds

    facts, reason = ds._cached_facts(ticker)
    if facts is None:
        return None, None, [reason]
    years = list(range(int(today[:4]) - 11, int(today[:4])))
    prov = SecCompanyFactsProvider(
        purpose="internal_research", fetch_facts=lambda cik, ua=None: facts,
        resolve_cik=lambda t, ua=None: "unused")
    res = prov.fetch_annual_financials(
        ticker, metrics=("revenue", "operating_cashflow", "capex", "operating_income", "sbc"),
        fiscal_years=years, retrieved_at=today)
    by = {}
    for f in res.facts:
        by.setdefault(f.metric, {})[f.fiscal_year] = f.value
    series = {
        "revenue_by_year": by.get("revenue", {}),
        "operating_cashflow_by_year": by.get("operating_cashflow", {}),
        "capex_by_year": by.get("capex", {}),
        "operating_income_by_year": by.get("operating_income", {}),
    }
    if by.get("sbc"):
        series["sbc_by_year"] = by["sbc"]
    return series, facts, list(res.limitations)


def run(today, limit, av_key=None, queue_path=QUEUE_PATH):
    os.makedirs(REPORT_DIR, exist_ok=True)
    queue = json.load(open(queue_path, encoding="utf-8"))
    refused = json.load(open(REFUSED_PATH, encoding="utf-8")) if os.path.exists(REFUSED_PATH) else {}
    excl = json.load(open("data/excluded_tickers.json", encoding="utf-8")).get("entries", {}) \
        if os.path.exists("data/excluded_tickers.json") else {}
    picked = pick_candidates(queue, today, limit, refused=refused,
                             extra=watchlist_candidates(excluded=excl))
    log(f"[자동분석] 대상 {len(picked)}종목: {', '.join(e['ticker'] for e in picked)}")
    rows = []
    for e in picked:
        t = e["ticker"]
        mc, mc_src = e.get("market_cap"), "public_float 근사(낡을 수 있음)"
        if av_key:
            try:
                from scripts import daily_screen_ci as ci
                live = ci.fetch_market_cap_av(t, av_key)
                time.sleep(ci.AV_CALL_INTERVAL_SEC)
                if live:
                    mc, mc_src = live, "Alpha Vantage 실시간"
            except Exception as ex:  # noqa: BLE001
                log(f"[자동분석] {t} 시총 조회 실패, 근사치 사용: {type(ex).__name__}")
        if not mc:
            rows.append({"ticker": t, "status": "NO_MARKET_CAP",
                         "reason": "시가총액 없음 — ALPHA_VANTAGE_API_KEY가 필요(관심종목 경로)"})
            continue
        try:
            series, facts, lim = fetch_series(t, today)
            if series is None:
                rows.append({"ticker": t, "status": "NO_DATA", "reason": (lim or ["?"])[0]})
                continue
            result = auto_analyze(t, t, series, mc, today, facts_json=facts)
            result["auto_analysis"]["market_cap_source"] = mc_src
            fcf_yield = result["derived"]["fcf0"] / mc if mc else None
            # 시총이 SEC public_float 근사인데 FCF수익률이 비현실적으로 높으면 시총이 틀린 것이다
            # (지배주주 지분이 큰 회사는 float이 실제 시총의 일부 — SCCO $9B vs 실제 ~$141B).
            suspect = bool(fcf_yield and fcf_yield > SUSPECT_FCF_YIELD and "근사" in mc_src)
            result["auto_analysis"]["market_cap_suspect"] = suspect
            path = save_ledger(result, ledger_dir=AUTO_LEDGER_DIR, overwrite=True, cross_check=False)
            rows.append({"ticker": t, "status": "MARKET_CAP_SUSPECT" if suspect else "OK", "path": path,
                         "gap": result["expectation_gap"], "grade": result.get("judgment_grade"),
                         "judgment": result["judgment"], "market_cap_source": mc_src,
                         "screen_gap": e.get("latest_gap")})
        except AutoAnalysisRefused as ex:
            refused[t] = {"date": today, "category": ex.category, "reason": ex.reason}
            rows.append({"ticker": t, "status": "REFUSED", "category": ex.category, "reason": ex.reason})
        except Exception as ex:  # noqa: BLE001 - 한 종목 실패가 전체를 막지 않는다
            rows.append({"ticker": t, "status": "ERROR", "reason": f"{type(ex).__name__}: {str(ex)[:150]}"})
    json.dump(refused, open(REFUSED_PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    summary = {"date": today, "official": False, "rows": rows}
    json.dump(summary, open(os.path.join(REPORT_DIR, f"{today}.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    return summary


def format_body(s):
    ok = [r for r in s["rows"] if r["status"] == "OK"]
    sus = [r for r in s["rows"] if r["status"] == "MARKET_CAP_SUSPECT"]
    lines = [f"## {s['date']} 자동 정식분석 (규칙 기반, 비공식)",
             "경쟁강도·수요민감도는 중앙값 대체이며 정성조사가 없다. **공식 판정·매수리스트와 무관**하다.", "",
             f"분석 {len(ok)} / 거부 {sum(r['status']=='REFUSED' for r in s['rows'])} / "
             f"기타 실패 {sum(r['status'] in ('ERROR','NO_DATA') for r in s['rows'])}", ""]
    if ok:
        lines += ["| 종목 | 등급 | Gap | 스크린 추정 | 시총 출처 |", "|---|---|---|---|---|"]
        for r in sorted(ok, key=lambda r: -r["gap"]):
            sg = f"{r['screen_gap']*100:+.1f}%p" if r.get("screen_gap") is not None else "-"
            lines.append(f"| {r['ticker']} | {r['grade']} | {r['gap']*100:+.2f}%p | {sg} | {r['market_cap_source']} |")
    if sus:
        lines += ["", "**시가총액 의심(FCF수익률 > 25%, 근사 시총이 틀렸을 가능성 — 등급을 믿지 말 것)**: "
                  + ", ".join(f"{r['ticker']}({r['grade']} {r['gap']*100:+.1f}%p)" for r in sus)]
    for r in s["rows"]:
        if r["status"] not in ("OK", "MARKET_CAP_SUSPECT"):
            lines.append(f"- {r['ticker']}: {r['status']} — {r.get('category','')} {r.get('reason','')}")
    return "\n".join(lines)


def main():
    today = os.environ.get("IRS_TODAY") or datetime.date.today().isoformat()
    limit = int(os.environ.get("IRS_AUTO_LIMIT") or DEFAULT_LIMIT)
    s = run(today, limit, os.environ.get("ALPHA_VANTAGE_API_KEY"))
    log(format_body(s))
    if "--post" in sys.argv:
        import issue_reporting as IR
        IR.report("daily", today, format_body(s), urgency_key="routine", log=log)


if __name__ == "__main__":
    main()
