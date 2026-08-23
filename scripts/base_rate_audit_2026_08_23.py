"""
34종목 성장률 base rate 감사 (2026-08-23, v3.66).

IRS가 각 종목에 부여한 Realistic Growth가 **그 회사의 매출 규모 구간에서
역사적으로 얼마나 흔했는지**를 Credit Suisse HOLT 실측 분포로 대조한다.

⚠️ 공식 판정을 바꾸지 않는다. ledger도 건드리지 않는다 - 병기 전용이다.
"""

import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.base_rates import (  # noqa: E402
    assess_growth_plausibility, base_rate_at_least, median_growth,
)

LEDGER_DIR = "ledger"
OUT = "reports/base_rate_audit_2026-08-23.json"

# 외화 표시 종목 -> USD 환산율. ledger의 currency 필드를 따른다.
FX_TO_USD = {"USD": 1.0, "CNY": 7.2}


def latest_ledgers(ledger_dir=LEDGER_DIR):
    latest = {}
    for name in sorted(os.listdir(ledger_dir)):
        if not name.endswith(".json"):
            continue
        with open(os.path.join(ledger_dir, name), encoding="utf-8") as f:
            d = json.load(f)
        t = d["meta"]["ticker"]
        if t not in latest or d["meta"]["analyzed_at"] > latest[t]["meta"]["analyzed_at"]:
            latest[t] = d
    return [latest[k] for k in sorted(latest)]


def main():
    rows = []
    for d in latest_ledgers():
        inp = d["inputs"]
        ticker = d["meta"]["ticker"]
        cur = inp.get("currency", "USD")
        if cur not in FX_TO_USD:
            print(f"  [skip] {ticker}: 환산율 없는 통화 {cur}")
            continue
        rev = {int(k): v for k, v in inp["revenue_by_year"].items()}
        sales_usd = rev[max(rev)] / FX_TO_USD[cur]
        rg = d["growth"]["realistic_growth"]

        a = assess_growth_plausibility(sales_usd, rg, horizon_years=10)
        cap_note = d["growth"]["breakdown"].get("cap_applied")
        rows.append({
            "ticker": ticker,
            "currency": cur,
            "sales_usd": sales_usd,
            "realistic_growth_nominal_pct": round(rg * 100, 2),
            "cap_bound": bool(cap_note),
            "cap_note": cap_note,
            "lynch_type": d["lynch"]["used"],
            "judgment": d["judgment"],
            "gap_pct": round(d["expectation_gap"] * 100, 2),
            **a,
        })

    rows.sort(key=lambda r: r["base_rate_pct"])

    print(f"{'종목':6} {'규모구간':>13} {'RG명목':>7} {'RG실질':>7} "
          f"{'10년 base rate':>14} {'등급':>15} {'또래중앙값':>10} 캡")
    print("-" * 96)
    for r in rows:
        cap = " ★" if r["cap_bound"] else ""
        print(f"{r['ticker']:6} {r['size_class']:>13} "
              f"{r['realistic_growth_nominal_pct']:6.2f}% {r['growth_real_pct']:6.2f}% "
              f"{r['base_rate_pct']:13.1f}% {r['tier']:>15} "
              f"{r['peer_median_real_pct']:9.1f}%{cap}")

    tiers = Counter(r["tier"] for r in rows)
    print(f"\n등급 분포: {dict(tiers)}")

    below1 = [r["ticker"] for r in rows if r["base_rate_pct"] < 1.0]
    below5 = [r["ticker"] for r in rows if r["base_rate_pct"] < 5.0]
    print(f"base rate 1% 미만: {below1}")
    print(f"base rate 5% 미만: {below5}")

    # 캡 바인딩 종목은 성장분석이 결과에 기여하지 못하므로 별도로 본다
    print("\n[캡 바인딩 종목 - 성장분석이 Gap에 기여하지 않는 종목]")
    for r in rows:
        if r["cap_bound"]:
            print(f"  {r['ticker']:6} {r['lynch_type']:12} "
                  f"RG {r['realistic_growth_nominal_pct']:.2f}% "
                  f"-> base rate {r['base_rate_pct']:.1f}% ({r['tier']})")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({
            "generated_at": "2026-08-23",
            "note": (
                "IRS가 부여한 Realistic Growth를 Credit Suisse HOLT 실측 "
                "base rate와 대조. 병기 전용 - 공식 판정·ledger 불변."
            ),
            "source": "Mauboussin & Callahan, The Base Rate Book (2016-09-26)",
            "n": len(rows),
            "tier_counts": dict(tiers),
            "below_1pct": below1,
            "below_5pct": below5,
            "rows": rows,
        }, f, ensure_ascii=False, indent=2)
    print(f"\n-> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
