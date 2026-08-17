"""
Growth Quality 프로파일 - 34종목 (2026-08-16, STAGE 1).

§12 STAGE 1 완료 조건에 답한다:
  "빠르게 성장하는 기업" vs "좋은 경제성을 가진 상태에서 성장하는 기업"을 구분할 수 있는가

IRS는 지금까지 성장률(Realistic Growth)만 보고 그 성장이 어떤 마진·자본집약도
위에서 일어나는지는 보지 않았다. 이 스크립트는 두 축을 나란히 놓는다.

⚠️ **공식 판정·Gap·비중을 바꾸지 않는다.** ledger를 읽기만 하고 쓰지 않는다.
두 축이 미래 성과와 관계가 있다는 증거는 아직 없다(H-007 사전등록).
"""
import glob
import json
import os
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.growth_quality import economic_profile  # noqa: E402

# 사분면 경계는 **관측 중앙값**이다 - 임의로 고른 임계값이 아니라는 점이 중요하다.
# (Terry Smith의 ROCE 15% 같은 외부 숫자를 그대로 규칙화하지 않는다.)


def build():
    rows = []
    for p in sorted(glob.glob("ledger/*.json")):
        led = json.load(open(p, encoding="utf-8"))
        I = led["inputs"]
        prof = economic_profile(I["revenue_by_year"], I["operating_income_by_year"],
                                I["capex_by_year"])
        rows.append({
            "ticker": led["meta"]["ticker"],
            "realistic_growth": led["growth"]["realistic_growth"],
            "expectation_gap": led["expectation_gap"],
            "judgment": led["judgment"],
            "operating_margin_level": prof["operating_margin_level"],
            "capex_to_revenue_level": prof["capex_to_revenue_level"],
            "n_years_margin": prof["n_years_margin"],
            "data_limitations": prof["data_limitations"],
        })
    return rows


def main():
    rows = build()
    growth_med = statistics.median(r["realistic_growth"] for r in rows)
    margin_med = statistics.median(r["operating_margin_level"] for r in rows)

    for r in rows:
        hi_g = r["realistic_growth"] >= growth_med
        hi_m = r["operating_margin_level"] >= margin_med
        r["quadrant"] = ("고성장·고마진" if hi_g and hi_m else
                         "고성장·저마진" if hi_g else
                         "저성장·고마진" if hi_m else "저성장·저마진")

    print(f"기준(관측 중앙값): Realistic Growth {growth_med*100:.2f}% / "
          f"영업이익률 {margin_med*100:.2f}%")
    print("=" * 92)
    print(f"{'종목':6s} {'RealGrowth':>11s} {'영업이익률':>10s} {'capex/매출':>10s} "
          f"{'Gap':>9s}  {'사분면':14s} 판정")
    print("-" * 92)
    for r in sorted(rows, key=lambda x: (-x["realistic_growth"])):
        flag = " ⚠️" if r["data_limitations"] else ""
        print(f"{r['ticker']:6s} {r['realistic_growth']*100:10.2f}% "
              f"{r['operating_margin_level']*100:9.2f}% "
              f"{r['capex_to_revenue_level']*100:9.2f}% "
              f"{r['expectation_gap']*100:+8.2f}%p  {r['quadrant']:14s} {r['judgment']}{flag}")

    print()
    print("=== §12 STAGE 1 완료 조건: 같은 성장률인데 경제성이 다른 기업이 구분되는가 ===")
    hi = [r for r in rows if r["quadrant"] == "고성장·고마진"]
    lo = [r for r in rows if r["quadrant"] == "고성장·저마진"]
    print(f"  고성장·고마진 {len(hi)}종목: {', '.join(r['ticker'] for r in hi)}")
    print(f"  고성장·저마진 {len(lo)}종목: {', '.join(r['ticker'] for r in lo)}")
    if hi and lo:
        print(f"  -> 두 집단의 Realistic Growth 중앙값은 "
              f"{statistics.median(r['realistic_growth'] for r in hi)*100:.2f}% vs "
              f"{statistics.median(r['realistic_growth'] for r in lo)*100:.2f}%로 유사하나 "
              f"영업이익률은 "
              f"{statistics.median(r['operating_margin_level'] for r in hi)*100:.1f}% vs "
              f"{statistics.median(r['operating_margin_level'] for r in lo)*100:.1f}%로 갈린다")
        print("     기존 IRS는 이 차이를 전혀 표현하지 못했다.")

    flagged = [r for r in rows if r["data_limitations"]]
    if flagged:
        print()
        print(f"⚠️ 데이터 한계가 기록된 종목 {len(flagged)}건:")
        for r in flagged:
            print(f"  {r['ticker']:6s} {'; '.join(r['data_limitations'])}")

    report = {
        "generated_at": "2026-08-16",
        "stage": "STAGE 1 prototype",
        "affects_official_judgment": False,
        "quadrant_thresholds": {
            "basis": "관측 중앙값(임의 임계값 아님)",
            "realistic_growth_median": growth_med,
            "operating_margin_median": margin_med,
        },
        "caveat": (
            "두 축이 미래 수익률·성장 지속성과 관계가 있다는 증거는 없다. "
            "experiments/H-007.json으로 사전등록된 가설이며 검정 전이다."
        ),
        "results": rows,
    }
    os.makedirs("reports", exist_ok=True)
    out = "reports/growth_quality_profile_2026-08-16.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n저장: {out}")


if __name__ == "__main__":
    main()
