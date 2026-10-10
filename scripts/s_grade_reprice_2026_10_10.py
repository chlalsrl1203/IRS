"""S등급 10종목 가격 재계산(2026-10-10). ledger 미수정, reports/만 쓴다(v3.42)."""
import json, glob
from engine.thesis_monitor import recompute_gap_at_market_cap
PRICE = {"ACGL":95.57,"CINF":163.39,"DLO":15.23,"DUOL":149.92,"MNDY":88.96,
         "PDD":81.35,"PGR":217.43,"PINS":21.40,"SIGI":84.22,"TTD":12.08}
out = {}
for t, p in PRICE.items():
    prev = json.load(open(f"reports/watchlist/{t}_2026-09-10.json"))
    p0 = prev.get("price_used") or {"PDD":78.61,"PGR":215.50,"TTD":13.88}[t]
    mc0 = prev.get("market_cap_used_direct") or prev["market_cap_now"]
    mc = mc0 * p / p0
    led = json.load(open(sorted(glob.glob(f"ledger/{t}_*.json"))[-1]))
    r = recompute_gap_at_market_cap(led, mc)
    r.update(price_now=p, date="2026-10-10", price_ref="Alpha Vantage GLOBAL_QUOTE 2026-10-09 종가; 주식수는 2026-09-10 리포트 비율 역산")
    out[t] = r
    json.dump(r, open(f"reports/watchlist/{t}_2026-10-10.json","w"), ensure_ascii=False, indent=1)
    print(f"{t:5} mc_chg_vs_ledger {r['market_cap_change_pct']*100:+6.1f}%  Gap {r['gap_then']*100:+6.2f}->{r['gap_now']*100:+6.2f}  {r['grade_then']}->{r['grade_now']}  RGdrift {r['realistic_growth_now']-r['realistic_growth_then']:.1e}")
