"""
P0-07 실측: ledger에 손입력된 벤더 수치를 SEC 1차자료와 전수 대조한다 (2026-08-19).

⚠️ **ledger를 수정하지 않는다.** 이 스크립트는 "두 출처가 얼마나, 어느 지표에서
어긋나는가"만 측정한다. 어느 값을 쓸지는 `reconcile.py`가 자동 결정하지 않으며
(물질적 불일치는 `requires_review=True`), 채택 여부는 분석자·사용자가 정한다.

# SOURCE:
https://github.com/chenditc/investment_data — 교차검증을 상시 절차로 두는 원칙

왜 필요한가: P0-03이 BSX 1종목에서 `operating_income` 11/11 불일치를 발견했다.
1종목으로는 (a) 그 지표만의 문제인지 (b) 다른 종목에도 퍼져 있는지 알 수 없고,
`TOLERANCE_TIERS` 임계값도 1종목 관측에 기대고 있다. 표본을 늘려 확인한다.
"""
import glob
import json
import os
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.data.canonical import build_canonical_series  # noqa: E402
from engine.data.providers.base import FinancialFact  # noqa: E402
from engine.data.providers.sec import SecCompanyFactsProvider  # noqa: E402
from engine.data.reconcile import reconcile_candidates, reconciliation_report  # noqa: E402

RETRIEVED_AT = "2026-08-19"
LEDGER_FIELDS = {
    "revenue": "revenue_by_year",
    "operating_income": "operating_income_by_year",
    "operating_cashflow": "operating_cashflow_by_year",
    "capex": "capex_by_year",
}


def ledger_facts(ledger):
    """
    ledger의 손입력 값을 `FinancialFact`로 옮긴다.

    ⚠️ `available_at`을 **알 수 없다** — 기존 34종목에는 PIT 필드가 없다(v3.49
    감사에서 확인). 추측해 채우지 않고, 대조에 필요한 최소값으로 회계기간
    종료일을 쓰되 그 사실을 결과에 명시한다. 이 값은 대조 계산에 쓰이지 않는다
    (`min(available_at)`으로 표시만 된다).
    """
    out, entity = [], ledger["meta"]["ticker"]
    for metric, field in LEDGER_FIELDS.items():
        for y, v in (ledger["inputs"].get(field) or {}).items():
            fy = int(y)
            out.append(FinancialFact(
                entity=entity, metric=metric, fiscal_year=fy, value=float(v),
                unit="currency_amount", currency="USD",
                period_start=f"{fy}-01-01", period_end=f"{fy}-12-31",
                available_at=f"{fy}-12-31",     # ⚠️ 미상 - 아래 note 참조
                source="ledger 손입력(대부분 Alpha Vantage)",
                source_key="alpha_vantage", retrieved_at=RETRIEVED_AT,
            ))
    return out


def main(tickers=None, limit=None):
    paths = sorted(glob.glob("ledger/*.json"))
    rows, failures = [], []
    for path in paths:
        L = json.load(open(path, encoding="utf-8"))
        t = L["meta"]["ticker"]
        if tickers and t not in tickers:
            continue
        years = sorted(int(y) for y in L["inputs"]["revenue_by_year"])
        try:
            sec = SecCompanyFactsProvider().fetch_annual_financials(
                t, metrics=list(LEDGER_FIELDS), fiscal_years=years,
                retrieved_at=RETRIEVED_AT)
        except Exception as e:                       # 네트워크·티커 문제
            failures.append({"ticker": t, "error": f"{type(e).__name__}: {e}"})
            continue

        # ⚠️ SEC 사실의 currency를 ledger와 맞춘다. 통화가 실제로 다르면
        # build_canonical_series가 오류를 내며, 그건 잡아야 할 진짜 문제다.
        series = build_canonical_series(t, {
            "alpha_vantage": ledger_facts(L),
            "sec_edgar": sec.facts,
        }, reconcile_fn=reconcile_candidates)
        rep = reconciliation_report(series)

        per_metric = {}
        for (metric, fy), v in series.values.items():
            sev = (v.conflict or {}).get("severity", "EXACT")
            d = per_metric.setdefault(metric, {"n": 0, "sev": {}, "rel": []})
            d["n"] += 1
            d["sev"][sev] = d["sev"].get(sev, 0) + 1
            rel = (v.conflict or {}).get("max_rel_diff")
            if rel is not None and rel != float("inf") and len(v.candidates) > 1:
                d["rel"].append(rel)
        rows.append({"ticker": t, "report": rep, "per_metric": per_metric,
                     "sec_limitations": sec.limitations})
        if limit and len(rows) >= limit:
            break

    # ── 요약 ──
    agg = {}
    for r in rows:
        for metric, d in r["per_metric"].items():
            a = agg.setdefault(metric, {"n": 0, "sev": {}, "rel": []})
            a["n"] += d["n"]
            for k, c in d["sev"].items():
                a["sev"][k] = a["sev"].get(k, 0) + c
            a["rel"] += d["rel"]

    print(f"대조 종목 {len(rows)}건 / 실패 {len(failures)}건\n")
    print(f"{'지표':20s}{'값수':>6s}{'EXACT':>8s}{'ROUND':>7s}{'MINOR':>7s}"
          f"{'MATERIAL':>10s}{'중앙편차':>10s}{'최대편차':>10s}")
    for metric in LEDGER_FIELDS:
        a = agg.get(metric)
        if not a:
            continue
        s = a["sev"]
        med = statistics.median(a["rel"]) * 100 if a["rel"] else 0.0
        mx = max(a["rel"]) * 100 if a["rel"] else 0.0
        print(f"{metric:20s}{a['n']:>6d}{s.get('EXACT',0):>8d}"
              f"{s.get('ROUNDING',0):>7d}{s.get('MINOR',0):>7d}"
              f"{s.get('MATERIAL',0):>10d}{med:>9.2f}%{mx:>9.1f}%")

    worst = sorted(rows, key=lambda r: -r["report"]["n_unresolved"])[:8]
    print(f"\n미해결(MATERIAL) 상위 종목:")
    for r in worst:
        rep = r["report"]
        by = {m: d["sev"].get("MATERIAL", 0) for m, d in r["per_metric"].items()
              if d["sev"].get("MATERIAL")}
        print(f"  {r['ticker']:6s} 미해결 {rep['n_unresolved']:3d}/{rep['n_values']:3d}  {by}")
    if failures:
        print(f"\n실패: {[(f['ticker'], f['error'][:60]) for f in failures]}")

    out = {
        "generated_at": RETRIEVED_AT, "step": "P0-07",
        "source_repo": "https://github.com/chenditc/investment_data",
        "affects_official_judgment": False,
        "n_tickers": len(rows), "aggregate": {
            m: {"n": a["n"], "severity": a["sev"],
                "median_rel_diff": statistics.median(a["rel"]) if a["rel"] else None,
                "max_rel_diff": max(a["rel"]) if a["rel"] else None}
            for m, a in agg.items()},
        "by_ticker": rows, "failures": failures,
        "note": (
            "ledger를 수정하지 않는다. 물질적 불일치는 자동 해결되지 않으며"
            "(requires_review=True), 채택은 원자료를 확인한 분석자가 정한다. "
            "⚠️ ledger 측 available_at은 미상이라 회계기간 종료일로 표시만 했다 - "
            "기존 34종목에는 PIT 필드가 없다(v3.49 감사)."
        ),
    }
    os.makedirs("reports", exist_ok=True)
    p = f"reports/ledger_vs_sec_reconciliation_{RETRIEVED_AT}.json"
    with open(p, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"\n저장: {p}")


if __name__ == "__main__":
    args = sys.argv[1:]
    main(tickers=set(args) if args else None)
