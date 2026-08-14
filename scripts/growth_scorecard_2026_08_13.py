"""
Growth Scorecard 1차 실행 - 2026-08-13 (v3.43).

`engine/thesis_monitor.py`(v3.42)가 반증조건이라는 **이진** 예측을 감시한다면,
이 스크립트는 엔진의 핵심 **연속값** 주장인 Realistic Growth를 회사가 실제로
내놓는 숫자와 대조한다. 주가 검증은 몇 년이 걸리지만 성장률 검증은 분기마다
가능하다는 게 핵심 - 지금 확보 가능한 가장 빠른 외부 검증이다.

## ⚠️ 읽는 법 - 비대칭이 있다(이 표를 오독하지 않으려면 반드시 볼 것)

Realistic Growth는 `min(FCF CAGR, 매출가중CAGR) x (1 - 구조적할인)`이라
**설계상 원시 성장률보다 낮게 나온다.** 따라서:

  - 관측치 > 엔진추정  -> **정상**이다. 구조적 할인이 의도대로 작동한 것일 뿐
    엔진이 틀렸다는 뜻이 아니다(단, 격차가 극단적이면 KEYS처럼 trailing CAGR이
    변곡점을 못 본 경우일 수 있다).
  - 관측치 < 엔진추정  -> **경고**다. 이미 보수적으로 깎은 추정치조차 회사가
    못 내고 있다는 뜻이라 해석의 여지가 훨씬 좁다.

그래서 아래 표는 `divergence_pp`의 **부호**를 반드시 함께 봐야 한다.

## 관측치 종류를 섞지 않는다

`realized_multiyear`(다년 실현) > `realized_quarterly`(분석 이후 1개 분기) >
`guidance_annual`(1개년 예측)의 순으로 증거력이 다르다. 특히 가이던스는
**예측이지 실적이 아니라서** 점수가 아니라 괴리 플래그로만 쓴다 - CLAUDE.md가
KEYS 크로스체크에서 "검증 안 된 1개년 가이던스만으로 realistic_growth_override를
쓰는 것은 ROP가 확립한 기준(다년 실적)에 못 미친다"고 이미 못박은 지점이다.

## 이번 실행의 핵심 발견

**TTD가 두 번째 독립 경로로 확인됐다.** v3.42 thesis_monitor는 반증조건
(이진 사건)으로 TTD를 잡았는데, 이 스크립트는 완전히 다른 축(성장률 입력)에서
같은 결론에 도달한다 - TTD의 **저평가 판정 최소선이 4.69%인데 회사가 직접
제시한 Q3 가이던스는 -12.1% 역성장**이다. 서로 다른 두 검증축이 같은 종목을
가리킨다는 건 우연일 가능성이 낮다.

실행: python3 scripts/growth_scorecard_2026_08_13.py
"""

import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.growth_scorecard import (
    breakeven_growth,
    growth_cap_is_binding,
    score_observation,
)

REPORT_PATH = "reports/growth_scorecard_2026-08-13.json"

# ── 관측치 - 전부 1차 확인된 수치다(추측 없음) ───────────────────────────
# growth 값은 "회사가 내고 있는 성장률"이며, 엔진의 Realistic Growth와 개념이
# 완전히 같지는 않다(위 docstring의 비대칭 설명 참고). 범위로 제시된 가이던스는
# 중간값을 쓰되 원 범위를 label에 남긴다.
OBSERVATIONS = [
    # ── 분석 이후 실제로 발표된 실적(진짜 out-of-sample) ──
    {"ticker": "TTD", "kind": "realized_quarterly", "growth": 0.030,
     "label": "Q2 2026 매출 +3.0%YoY($715M)",
     "source": "TTD 2026-08-06 실적발표(8-K), WebSearch 2026-08-13 확인"},
    {"ticker": "SE", "kind": "realized_quarterly", "growth": 0.481,
     "label": "Q2 2026 매출 +48.1%YoY($7.8B)",
     "source": "SE 2026-08-11 실적발표, WebSearch 2026-08-13 확인"},
    {"ticker": "DUOL", "kind": "realized_quarterly", "growth": 0.183,
     "label": "Q2 2026 매출 +18.3%YoY($298.5M)",
     "source": "DUOL 2026-08-05 실적발표, WebSearch 2026-08-13 확인"},
    {"ticker": "MNDY", "kind": "realized_quarterly", "growth": 0.220,
     "label": "Q2 2026 매출 +22%YoY($364.6M)",
     "source": "MNDY 2026-08-10 실적발표, WebSearch 2026-08-13 확인"},
    {"ticker": "PGR", "kind": "realized_quarterly", "growth": 0.060,
     "label": "Q2 2026 순보험료수입 +6%YoY($21,573M)",
     "source": "PGR 2026-08-04 실적발표(8-K), WebSearch 2026-08-13 확인"},

    # ── 회사 자체 가이던스(예측 - 점수 아님, 괴리 플래그) ──
    {"ticker": "TTD", "kind": "guidance_annual", "growth": -0.121,
     "label": "Q3 2026 가이던스 -12.1%YoY($650M 중간값)",
     "source": "TTD 2026-08-06 실적발표 회사 제시, WebSearch 2026-08-13 확인"},
    {"ticker": "DUOL", "kind": "guidance_annual", "growth": 0.163,
     "label": "FY2026 매출 가이던스 +16.3%(~$1.21B)",
     "source": "DUOL 2026-08-05 실적발표 회사 제시, WebSearch 2026-08-13 확인"},
    {"ticker": "TCOM", "kind": "guidance_annual", "growth": 0.055,
     "label": "Q2/Q3 2026 가이던스 +3~8%YoY(중간값 5.5%)",
     "source": "CLAUDE.md 2026-08-04 A등급 정성심층조사에서 확인된 회사 가이던스"},
    {"ticker": "GEN", "kind": "guidance_annual", "growth": 0.075,
     "label": "익년도 가이던스 +6.5~8.5%(중간값 7.5%)",
     "source": "CLAUDE.md 2026-07-28 GEN 세그먼트 조사에서 확인된 회사 가이던스"},
    {"ticker": "KEYS", "kind": "guidance_annual", "growth": 0.28,
     "label": "FY2026 가이던스 20%대 후반(28% 근사)",
     "source": "CLAUDE.md 2026-08-04 KEYS 크로스체크에서 확인된 회사 가이던스"},

    # ── 다년 실현실적(증거력 최상 - 유일하게 공식판정 승격 근거가 된다) ──
    {"ticker": "ROP", "kind": "realized_multiyear", "growth": 0.055,
     "label": "오가닉 성장률 5~6%(3년 연속 감속, Q1/Q2'26 실측 5%)",
     "source": "CLAUDE.md v3.28 - 이미 공식판정에 반영됨(통제사례)"},
]


def load(ticker):
    p = sorted(glob.glob(f"ledger/{ticker}_*.json"))[-1]
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def main():
    ledgers = {o["ticker"]: load(o["ticker"]) for o in OBSERVATIONS}
    scored = [score_observation(ledgers[o["ticker"]], o) for o in OBSERVATIONS]

    print("=" * 118)
    print("Growth Scorecard - 엔진 Realistic Growth vs 회사 실제 숫자 (2026-08-13)")
    print("=" * 118)

    # ── 기준선 표: 저평가 판정에 필요한 최소 성장률 ──
    print("\n[기준선] 저평가 판정 최소선 = Implied Growth + 판정밴드(5%p)")
    print("  ⭐ 분석자 주관이 개입할 수 없는 객관적 기준 - 회사가 내는 숫자와 곧바로 비교 가능\n")
    head = f"  {'종목':6} {'엔진RG':>8} {'저평가최소선':>12} {'여유':>9}  {'캡바인딩':8} 현재판정"
    print(head)
    print("  " + "-" * (len(head) - 2))
    for t in sorted(ledgers):
        led, bk = ledgers[t], breakeven_growth(ledgers[t])
        print(f"  {t:6} {bk['engine_realistic_growth']*100:7.2f}% "
              f"{bk['undervalued_floor']*100:11.2f}% "
              f"{bk['headroom_vs_undervalued_floor']*100:+8.2f}%p  "
              f"{'예' if growth_cap_is_binding(led) else '아니오':8} {led['judgment']}")

    # ── 관측치 대조 ──
    for kind, title in (
        ("realized_quarterly", "분석 이후 발표된 실적 (진짜 out-of-sample, 단 1개 분기라 노이즈 큼)"),
        ("guidance_annual", "회사 가이던스 (예측이지 실적 아님 - 괴리 플래그로만 사용)"),
        ("realized_multiyear", "다년 실현실적 (증거력 최상 - 공식판정 승격 근거가 됨)"),
    ):
        rows = [s for s in scored if s["kind"] == kind]
        if not rows:
            continue
        print(f"\n[{kind}] {title}")
        h = (f"  {'종목':6} {'엔진RG':>8} {'관측':>9} {'괴리':>9} "
             f"{'Gap(엔진)':>10} {'Gap(관측)':>10}  판정변화")
        print(h)
        print("  " + "-" * (len(h) - 2))
        for s in sorted(rows, key=lambda x: x["divergence_pp"]):
            flip = (f"⚠️ {s['engine_judgment']} → {s['judgment_at_observed']}"
                    if s["judgment_flipped"] else "불변")
            warn = "!" if s["divergence_exceeds_threshold"] else " "
            print(f"  {s['ticker']:6} {s['engine_realistic_growth']*100:7.2f}% "
                  f"{s['observed_growth']*100:8.2f}% "
                  f"{s['divergence_pp']*100:+8.2f}%p{warn}"
                  f"{s['engine_gap']*100:+9.2f}%p {s['gap_at_observed']*100:+9.2f}%p  {flip}")
            print(f"         └ {s['label']}")

    # ── 요약 ──
    flipped = [s for s in scored if s["judgment_flipped"]]
    # 종목당 관측치가 여러 건일 수 있어 티커는 중복 제거해서 센다
    neg_tickers = sorted({s["ticker"] for s in scored
                          if s["divergence_pp"] < 0 and s["divergence_exceeds_threshold"]})
    flip_tickers = sorted({s["ticker"] for s in flipped})
    print("\n" + "=" * 118)
    print(f"판정이 뒤집히는 관측치: {len(flipped)}/{len(scored)}건 "
          f"({len(flip_tickers)}종목) - "
          f"{', '.join(s['ticker'] + '(' + s['kind'] + ')' for s in flipped)}")
    print(f"⚠️ 부정방향 큰 괴리(관측 < 엔진, 해석 여지 좁음) {len(neg_tickers)}종목: "
          f"{', '.join(neg_tickers) if neg_tickers else '없음'}")
    print("\n관측 > 엔진은 구조적 할인이 의도대로 작동한 정상 상태다 - 엔진 오류가 아니다.")
    print("공식 ledger는 이 스크립트로 변경되지 않는다(병기, 자동판정 안 함).")

    os.makedirs("reports", exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump({
            "generated_at": "2026-08-13",
            "baselines": {t: breakeven_growth(ledgers[t]) for t in sorted(ledgers)},
            "observations": scored,
        }, f, ensure_ascii=False, indent=2)
    print(f"\n리포트 저장: {REPORT_PATH}")
    return scored


if __name__ == "__main__":
    main()
