"""자동 분석 규칙 vs 공식 ledger 일치도 측정(오프라인). ledger 입력 시계열에 auto 규칙을 적용해
공식 판정과 비교한다. 공식 입력(오버라이드·정성조사)이 이미 반영된 시계열을 쓰므로 '규칙이 사람 판단을
얼마나 재현하는가'의 낙관적 상한이다. 결과: reports/auto_analysis/concordance_2026-10-10.json"""
import glob, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from engine.auto_analysis import AutoAnalysisRefused, auto_analyze

rows = []
for p in sorted(glob.glob("ledger/*.json")):
    d = json.load(open(p, encoding="utf-8")); i = d["inputs"]; t = d["meta"]["ticker"]
    if i.get("is_insurer"):
        rows.append({"ticker": t, "status": "SKIP_INSURER"}); continue
    ser = {k: {int(y): v for y, v in i[k].items()} for k in
           ("revenue_by_year", "operating_income_by_year", "operating_cashflow_by_year", "capex_by_year")}
    try:
        r = auto_analyze(t, t, ser, i["market_cap"], "2026-10-10")
    except AutoAnalysisRefused as e:
        rows.append({"ticker": t, "status": "REFUSED", "category": e.category}); continue
    except Exception as e:  # noqa: BLE001
        rows.append({"ticker": t, "status": "ERROR", "reason": str(e)[:80]}); continue
    rows.append({"ticker": t, "status": "OK", "official_gap": d["expectation_gap"], "auto_gap": r["expectation_gap"],
                 "official_judgment": d["judgment"], "auto_judgment": r["judgment"],
                 "official_grade": d.get("judgment_grade"), "auto_grade": r.get("judgment_grade")})
ok = [r for r in rows if r["status"] == "OK"]
same_j = sum(r["official_judgment"] == r["auto_judgment"] for r in ok)
same_g = sum(r["official_grade"] == r["auto_grade"] for r in ok)
errs = sorted(abs(r["auto_gap"] - r["official_gap"]) for r in ok)
summary = {"n_ledgers": len(rows), "n_ok": len(ok),
           "n_refused": sum(r["status"] == "REFUSED" for r in rows),
           "n_skipped_insurer": sum(r["status"] == "SKIP_INSURER" for r in rows),
           "n_error": sum(r["status"] == "ERROR" for r in rows),
           "judgment_match": same_j, "grade_match": same_g,
           "abs_gap_error_median": errs[len(errs) // 2] if errs else None,
           "abs_gap_error_p90": errs[int(len(errs) * 0.9)] if errs else None, "rows": rows}
os.makedirs("reports/auto_analysis", exist_ok=True)
json.dump(summary, open("reports/auto_analysis/concordance_2026-10-10.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print({k: v for k, v in summary.items() if k != "rows"})
