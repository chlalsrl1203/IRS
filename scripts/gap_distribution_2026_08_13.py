"""
Gap Distribution 1차 실행 - 2026-08-13 (v3.44).

경위: BSX의 screener false-rejection(이 세션 앞부분)이 보여준 문제 - "큰
분산을 가진 값을 점 하나로 대체하면 판정이 흔들릴 수 있다" - 의 일반해로
`engine/gap_distribution.py`를 만들었다. 정식 엔진에도 같은 구조가 있다:
DRS 5개 구성요소 중 분석자 판단이 들어가는 2개(demand_sensitivity_pct,
competition_intensity)를 이 프로젝트가 34종목에서 **실제로 쓴 값의 범위**로
삼각분포 삼아 흔들고, Gap·판정이 얼마나 흔들리는지 본다.

## ⚠️ 실측 결과가 애초 가설과 달랐다 - 그대로 기록한다

사용자에게 처음 제안할 때 "P(저평가)=73%" 같은 예시를 들었으나, 실제로 돌려보니
**34종목 전부 100%/0% - 하나도 안 흔들린다.** 원인을 추적해보니 가짜 발견이
아니라 이 엔진 설계의 실제 성질이었다:

  `erp_from_drs(drs) = 0.05 + (drs/100)*0.03` (DRS 0~100 -> ERP 5~8%만)

demand_sensitivity_pct는 cyclicality_score에 최대 +4점만 기여하고(공식
자체가 `min(demand_sensitivity,1)*4.0`으로 상한이 고정돼 있다),
competition_intensity를 corpus 관측범위(3.6~20.0) 끝에서 끝까지 흔들어도
DRS는 최대 ~16.4점만 움직인다. 이 둘을 합쳐도 DRS 스윙은 ~20점 남짓 -> ERP는
0.2*0.03=0.6%p 남짓만 움직인다. **가장 근접했던 BSX(공식 Gap +5.87%p,
경계 +5.00%p까지 0.87%p)조차 표준편차 0.20%p로 한 번도 경계를 못 넘었다**
(p10~p90 폭이 0.52%p뿐).

## 결론 - 취약성은 성장률 축에 있지, DRS 축에는 없다

이건 `engine/growth_scorecard.py`(v3.43)의 발견과 정확히 대비된다.
growth_scorecard는 TTD/TCOM/KEYS 3종목의 판정이 **성장률 가정** 하나만으로
실제로 뒤집혔음을 보였다. gap_distribution은 같은 종목들의 판정이 **경쟁강도·
수요민감도 가정**으로는(이 프로젝트가 실제 축적한 범위 안에서는) 전혀 안
뒤집힘을 보인다. 두 모듈을 나란히 놓으면 "이 프로젝트에서 판정을 재검토할
가치가 있는 곳은 성장률 입력이지, DRS 리스크스코어링 입력이 아니다"라는
꽤 구체적인 결론이 나온다 - 원래 가설(확률분포로 흔들리는 판정을 찾겠다)은
기각됐지만, 그 기각 자체가 "왜 이 프로젝트의 위험도 축은 안 흔들리는가"라는
더 구체적인 답을 줬다.

실행: python3 scripts/gap_distribution_2026_08_13.py
"""

import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.gap_distribution import fragility_label, monte_carlo_gap, observed_ranges

REPORT_PATH = "reports/gap_distribution_2026-08-13.json"


def load_ledgers():
    out = []
    for p in sorted(glob.glob("ledger/*.json")):
        with open(p, encoding="utf-8") as f:
            out.append(json.load(f))
    return out


def main():
    ledgers = load_ledgers()
    ranges = observed_ranges(ledgers)

    print("=" * 100)
    print(f"Gap Distribution - DRS 주관입력 Monte Carlo (2026-08-13, ledger {len(ledgers)}건)")
    print("=" * 100)
    print(f"\n관측범위(34종목 실측, 지어낸 사전분포 아님):")
    ds, ci = ranges["demand_sensitivity_pct"], ranges["competition_intensity"]
    print(f"  demand_sensitivity_pct : {ds.lo:.2f} ~ {ds.hi:.2f}  (n={ds.n})")
    print(f"  competition_intensity  : {ci.lo:.1f} ~ {ci.hi:.1f}  (n={ci.n})")

    rows = [monte_carlo_gap(d, ranges) for d in ledgers]
    rows.sort(key=lambda r: r["gap_stdev"], reverse=True)

    print(f"\n{'종목':6} {'공식판정':14} {'Gap(공식)':>10} {'평균':>9} {'표준편차':>8} "
          f"{'P(저평가)':>9} {'P(적정)':>8} {'P(과대)':>8}  견고성")
    print("-" * 106)
    n_fragile = 0
    for r in rows:
        label = fragility_label(r)
        if label != "견고":
            n_fragile += 1
        print(f"{r['ticker']:6} {r['official_judgment']:14} {r['official_gap']*100:+9.2f}%p "
              f"{r['gap_mean']*100:+8.2f}%p {r['gap_stdev']*100:7.3f}%p "
              f"{r['p_undervalued']*100:8.1f}% {r['p_neutral']*100:7.1f}% {r['p_overvalued']*100:7.1f}%  {label}")

    max_stdev = max(r["gap_stdev"] for r in rows)
    closest = min(rows, key=lambda r: abs(abs(r["official_gap"]) - 0.05))
    print(f"\n최대 표준편차: {max_stdev*100:.3f}%p ({max(rows, key=lambda r: r['gap_stdev'])['ticker']})")
    print(f"경계(±5%p)에 가장 근접: {closest['ticker']} "
          f"(공식 Gap {closest['official_gap']*100:+.2f}%p, 경계까지 "
          f"{abs(abs(closest['official_gap'])-0.05)*100:.2f}%p)")
    print(f"취약 판정: {n_fragile}/{len(rows)}건")
    print()
    print("결론: DRS 주관입력(경쟁강도·수요민감도)만으로는 34종목 중 단 한 건도")
    print("      판정이 흔들리지 않는다 - erp_from_drs()의 좁은 매핑(ERP 5~8%) 때문에")
    print("      구조적으로 스윙 폭이 작다(최대 ~0.6%p). growth_scorecard(v3.43)가 보인")
    print("      성장률 축 취약성(TTD/TCOM/KEYS)과 정확히 대비되는 결과다 - 취약성은")
    print("      DRS 리스크스코어링이 아니라 성장률 입력에 있다.")

    os.makedirs("reports", exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump({
            "generated_at": "2026-08-13",
            "observed_ranges": {
                "demand_sensitivity_pct": {"lo": ds.lo, "hi": ds.hi, "n": ds.n},
                "competition_intensity": {"lo": ci.lo, "hi": ci.hi, "n": ci.n},
            },
            "rows": rows,
            "n_fragile": n_fragile,
        }, f, ensure_ascii=False, indent=2)
    print(f"\n리포트 저장: {REPORT_PATH}")
    return rows


if __name__ == "__main__":
    main()
