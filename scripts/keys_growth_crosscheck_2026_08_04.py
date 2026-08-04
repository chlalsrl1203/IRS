"""
KEYS 성장률 교차검증 - 2026-08-04.

경위: 2026-08-04 B/D등급 6종목 가벼운 정성검증(1차 배치) 중 KEYS에서 이
트래커 전체에서 가장 의외의 결과가 나왔다 - "트래커 최고 과대평가"
(-14.36%p) 판정의 근거인 Realistic Growth 1.47%(trailing CAGR 기반)를
회사 자체 FY2026 가이던스가 정면으로 반박한다. AI 데이터센터 광통신/
인터커넥트 테스트 수요 급증(Q2 주문 +56%YoY, AI 관련 매출 H1만으로
FY2025 전체 초과)에 힘입어 FY2026 매출성장 가이던스가 20%대 후반(Q3
가이던스 중간값 기준 +29%YoY)까지 상향됐다 - 시장의 내재성장률(15.84%)
보다도 높다.

⚠️ ROP 사례와는 성격이 다르다 - 신중하게 접근한다:
  - ROP: 회사가 **여러 분기 동안 실제로 실현한** 오가닉 성장률(다년간
    추세)을 근거로 썼다 - 검증된 과거 실적.
  - KEYS: 회사의 **향후 1개년 가이던스**(아직 실현 안 됨)를 근거로 쓰려는
    것이다 - AI 데이터센터 투자 슈퍼사이클이라는 특수 국면에 의존하는
    예측치이며, 사이클이 꺾이면 빠르게 되돌아갈 수 있다. Realistic Growth는
    본래 "지속가능한 다년성장률" 개념이라, 1개년 가이던스를 그대로 쓰면
    개념이 다른 값을 억지로 끼워맞추는 것이다.

**그래서 이 스크립트는 ROP처럼 공식판정 승격을 겨냥하지 않는다** - 순수
교차검증이며, 두 시나리오를 병기해 "판정이 얼마나 민감한가"만 보여준다:
  A) cyclical Lynch 상한(20%) 시나리오: trailing CAGR을 아예 무시하고
     이 프로젝트가 cyclical 유형에 허용하는 최댓값을 쓰면 어떻게 되는가
     - "성장분석 자체가 최대한 관대해도"라는 보수적 상한 테스트.
  B) 가이던스 시나리오(28%, FY26 가이던스 중간값 대표): 회사가 실제로
     제시한 향후 1개년 숫자를 그대로 쓰면 어떻게 되는가 - 공격적이고
     검증 안 된 시나리오임을 명시.

engine에 "1개년 가이던스 오버라이드"용 별도 필드는 만들지 않는다
(Simplicity First - 이 종목 1건만으로 새 필드를 만들 근거가 아직 부족,
ROP의 realistic_growth_override는 다년실적이라는 다른 성격의 근거였다).
ledger에 이미 저장된 DRS·할인율(r)·Implied Growth(growth 입력과 무관하게
고정)를 재사용해 Gap·RAR·판정만 재계산한다.

실행: python3 scripts/keys_growth_crosscheck_2026_08_04.py
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.expectation_gap_engine import (
    LYNCH_TYPE_CAPS,
    bull_bear_base_growth_rates,
    scenario_return_from_growth,
    scenario_probabilities_from_drs,
    expected_return,
    rar_from_decimal_return,
    judgment_grade_from_gap,
)

LEDGER_PATH = "ledger/KEYS_2026-08-02.json"

CYCLICAL_CAP_GROWTH = LYNCH_TYPE_CAPS["cyclical"][1]  # 0.20
GUIDANCE_GROWTH = 0.28   # FY2026 가이던스 중간값 대표(고~20%대, Q3가이던스 +29%YoY 근사)

LYNCH_TYPE = "cyclical"


def run_scenario(name, growth, ledger, caveat):
    d = ledger["derived"]
    disc = ledger["discount_rate"]
    drs = ledger["drs"]["score"]
    market_cap = ledger["inputs"]["market_cap"]
    fcf0 = d["fcf0"]
    r, n, g_terminal = disc["r"], disc["n"], disc["g_terminal"]
    implied_growth = ledger["implied_growth"]["value"]

    rates = bull_bear_base_growth_rates(growth, LYNCH_TYPE)
    r_bull = scenario_return_from_growth(market_cap, fcf0, r, n, g_terminal, rates["g_bull"])
    r_base = scenario_return_from_growth(market_cap, fcf0, r, n, g_terminal, rates["g_base"])
    r_bear = scenario_return_from_growth(market_cap, fcf0, r, n, g_terminal, rates["g_bear"])

    p_bull, p_base, p_bear, _ = scenario_probabilities_from_drs(drs)
    er = expected_return(p_bull, r_bull, p_base, r_base, p_bear, r_bear)
    rar_value = rar_from_decimal_return(er, drs)

    gap = growth - implied_growth
    if gap >= 0.05:
        judgment = "저평가 가능성"
    elif gap <= -0.05:
        judgment = "과대평가 가능성"
    else:
        judgment = "적정가/경계선"
    grade = judgment_grade_from_gap(gap)

    print(f"\n  [{name}] Realistic Growth 대체값 {growth*100:.2f}%  ({caveat})")
    print(f"    Implied Growth(고정, {ledger['implied_growth']['model_used']}) : {implied_growth*100:.2f}%")
    print(f"    Expectation Gap  : {gap*100:+.2f}%p")
    print(f"    RAR              : {rar_value:+.4f}")
    print(f"    판정             : {judgment} (등급 {grade})")

    return {"scenario": name, "growth": growth, "gap": gap, "er": er,
            "rar": rar_value, "judgment": judgment, "grade": grade, "caveat": caveat}


def main():
    ledger = json.load(open(LEDGER_PATH))

    print("=" * 100)
    print("KEYS 성장률 교차검증 (ledger/KEYS_2026-08-02.json 기반, 공식 판정 아님)")
    print("=" * 100)
    print(f"  공식 기록: Realistic Growth 1.47%(trailing CAGR) / "
          f"Gap {ledger['expectation_gap']*100:+.2f}%p / RAR {ledger['rar']:+.4f} / "
          f"판정 {ledger['judgment']} (트래커 최고 과대평가)")
    print(f"  DRS {ledger['drs']['score']:.2f} / 할인율 r {ledger['discount_rate']['r']*100:.2f}% "
          f"(교차검증에서도 동일하게 재사용 - growth 입력과 무관)")

    results = [
        run_scenario(
            "A) cyclical 상한 시나리오", CYCLICAL_CAP_GROWTH, ledger,
            "trailing CAGR 무시, 이 프로젝트가 cyclical에 허용하는 최댓값(보수적 상한 테스트)"
        ),
        run_scenario(
            "B) FY26 가이던스 시나리오", GUIDANCE_GROWTH, ledger,
            "⚠️1개년 가이던스, AI 데이터센터 수퍼사이클 의존 - 검증 안 된 공격적 가정"
        ),
    ]

    print("\n" + "=" * 100)
    print("요약")
    print("=" * 100)
    print(f"  공식(trailing CAGR)          : Gap {ledger['expectation_gap']*100:+.2f}%p -> {ledger['judgment']}")
    for r_ in results:
        print(f"  {r_['scenario']:26}: Gap {r_['gap']*100:+.2f}%p -> {r_['judgment']} (등급 {r_['grade']})")
    print("\n  ⚠️ 가장 보수적인 시나리오(A, trailing CAGR을 완전히 무시하고 cyclical")
    print("     상한 20%만 적용)조차도 판정을 '과대평가 가능성'에서 '적정가/경계선'으로")
    print("     끌어올린다 - 즉 trailing CAGR 기반 Realistic Growth(1.47%)가 이 종목의")
    print("     실제 성장궤적을 심각하게 과소추정하고 있을 가능성이 높다. 시나리오 B")
    print("     (회사 가이던스 28%)까지 가면 '저평가 가능성'(A등급)으로 완전히 뒤집힌다.")
    print("     다만 시나리오 B는 검증되지 않은 1개년 가이던스에 의존하므로(ROP의 다년")
    print("     오가닉 실적과는 성격이 다름) 이 결과를 곧바로 realistic_growth_override로")
    print("     공식 승격하는 것은 권하지 않는다 - 최소 1개 분기(FY26 Q4, 실적발표 예정)의")
    print("     실제 매출로 가이던스 이행 여부를 확인한 뒤 재검토할 것을 권고한다.")
    print("     공식 ledger의 Gap/RAR/판정은 변경하지 않는다.")

    os.makedirs("reports", exist_ok=True)
    out_path = "reports/keys_growth_crosscheck_2026-08-04.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({
            "official": {
                "realistic_growth": ledger["growth"]["realistic_growth"],
                "gap": ledger["expectation_gap"],
                "rar": ledger["rar"],
                "judgment": ledger["judgment"],
            },
            "crosscheck_scenarios": results,
            "recommendation": (
                "재실행 보류 - FY26 Q4 실적(가이던스 이행 여부) 확인 후 재검토 권고. "
                "1개년 가이던스만으로 realistic_growth_override 승격은 시기상조."
            ),
        }, f, ensure_ascii=False, indent=2)
    print(f"\n결과 저장: {out_path}")


if __name__ == "__main__":
    main()
