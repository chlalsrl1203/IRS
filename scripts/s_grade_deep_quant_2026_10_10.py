"""S등급 10종목 정량 심화(2026-10-10): 가정 범위 Gap(v3.51) + SBC 차감 + base rate. ledger 무수정, reports/만 쓴다."""
import glob, json
from dataclasses import replace
from engine.gap_analysis import gap_range_over_assumptions
from engine.base_rates import assess_growth_plausibility
from engine.thesis_monitor import inputs_from_ledger
from engine.pipeline import run_analysis

PRICE = {"ACGL":95.57,"CINF":163.39,"DLO":15.23,"DUOL":149.92,"MNDY":88.96,"PDD":81.35,"PGR":217.43,"PINS":21.40,"SIGI":84.22,"TTD":12.08}
out = {}
for t in PRICE:
    led = json.load(open(sorted(glob.glob(f"ledger/{t}_*.json"))[-1]))
    now = json.load(open(f"reports/watchlist/{t}_2026-10-10.json"))
    gr = gap_range_over_assumptions(led)
    inp = led["inputs"]; rev = inp["revenue_by_year"]; y = str(max(map(int, rev)))
    sales = float(rev[y]); fx = inp.get("usd_fx_rate") or (1.0 if led["meta"].get("currency","USD") == "USD" else None)
    pl = assess_growth_plausibility(sales / fx, led["growth"]["realistic_growth"]) if fx else None
    sbc = led.get("sbc_cross_check") or {}
    # 현재 시총에서 SBC 차감 Gap(같은 model_used) - run_analysis 재실행으로 계산
    fresh = run_analysis(replace(inputs_from_ledger(led), market_cap=now["market_cap_now"]))
    sc = fresh.get("sbc_cross_check") or {}
    out[t] = dict(
        gap_now=now["gap_now"], grade_now=now["grade_now"],
        range_min=gr["gap_min"], range_max=gr["gap_max"], robust=gr["robust"],
        judgments=sorted(gr["judgment_set"]), flip_drivers=[k for k, v in gr["flip_drivers"].items() if v],
        sbc_pct=sc.get("sbc_to_fcf_pct"), gap_sbc_now=sc.get("gap_sbc_adjusted"), judg_sbc_now=sc.get("judgment_sbc_adjusted"),
        rg=led["growth"]["realistic_growth"], base_rate_pct=pl and pl["base_rate_pct"], tier=pl and pl["tier"],
        size_class=pl and pl["size_class"], peer_median_real=pl and pl["peer_median_real_pct"])
    o = out[t]
    f = lambda v: "  -  " if v is None else f"{v*100:+6.2f}"
    print(f"{t:5} Gap {f(o['gap_now'])} 범위[{f(o['range_min'])},{f(o['range_max'])}] robust={o['robust']!s:5} flip={o['flip_drivers']} | SBC {o['sbc_pct'] if o['sbc_pct'] is None else round(o['sbc_pct']*100,1)}% Gap_sbc {f(o['gap_sbc_now'])} {o['judg_sbc_now']} | RG {o['rg']*100:.2f}% base {o['base_rate_pct']} {o['tier']} ({o['size_class']})")
json.dump(out, open("reports/s_grade_deep_quant_2026-10-10.json", "w"), ensure_ascii=False, indent=1)
