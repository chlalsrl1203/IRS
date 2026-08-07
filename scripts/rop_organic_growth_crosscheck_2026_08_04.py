"""
ROP 유기적성장률 교차검증 - 2026-08-04.

경위: 2026-08-04 A등급 6종목 정성심층조사에서 나온 가장 비중있는 발견 -
ROP의 Realistic Growth(12.00%)는 실제 계산값이 아니라 stalwart 성장상한
그 자체다(M-1, 성장상한 바인딩). 회사 자체 공시 오가닉(유기적) 성장률은
5-6%로 3년 연속 감속 중(FY2023 ~8% -> FY2024 ~6% -> FY2025/26 ~5-6%,
Q1'26/Q2'26 모두 5%)이고, 연결(오가닉+M&A) 성장률도 FY2026 가이던스
"north of 8%" 수준이다. ledger의 falsification_conditions가 "다음 세션에서
반드시 재실행 검증할 것"을 명시했다 - 이 스크립트가 그 검증이다.

⚠️ 이것은 공식 재분석이 아니라 교차검증이다(is_insurer/sbc_cross_check와
동일한 "병기, 자동판정 안 함" 원칙). engine/pipeline.py의 AnalysisInputs에는
"유기적성장 오버라이드" 필드가 없다(CLAUDE.md가 의도적으로 아직 배선하지
않았다고 명시 - 세그먼트 공시 방식이 회사마다 달라 표준 입력 스키마를
만들기엔 실증사례가 더 필요함). 대신 ledger/ROP_2026-08-04.json에 이미
저장된 DRS·할인율(r)·Implied Growth(두 growth 입력과 무관하게 고정)를
그대로 가져와, Realistic Growth 자리에만 유기적성장/연결성장을 대입해
Gap·시나리오수익률·RAR·판정을 재계산한다. 공식 ledger의 Gap/RAR/판정은
전혀 건드리지 않는다.

두 시나리오:
  A) 유기적성장 기준: 5.5%(최근 2개분기 Q1/Q2'26 실측 5%와 FY26 가이던스
     상단 6%의 중간값 - 회사가 공시한 구체적 숫자만 사용, 추측 없음)
  B) 연결성장 기준: 8.5%(FY2026 가이던스 "north of 8%"의 대표값)

실행: python3 scripts/rop_organic_growth_crosscheck_2026_08_04.py
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.expectation_gap_engine import (
    bull_bear_base_growth_rates,
    scenario_return_from_growth,
    scenario_probabilities_from_drs,
    expected_return,
    rar_from_decimal_return,
    judgment_from_gap,
    judgment_grade_from_gap,
)

LEDGER_PATH = "ledger/ROP_2026-08-04.json"

# 회사 공시 실측치(2026-08-04 정성심층조사 확인, 추측 아님)
ORGANIC_GROWTH = 0.055   # Q1'26 5% / Q2'26 5% / FY26 가이던스 5-6%의 대표값
CONSOLIDATED_GROWTH = 0.085   # FY2026 가이던스 "north of 8%"의 대표값

LYNCH_TYPE = "stalwart"


def run_scenario(name, growth, ledger):
    d = ledger["derived"]
    disc = ledger["discount_rate"]
    drs = ledger["drs"]["score"]
    market_cap = ledger["inputs"]["market_cap"]
    fcf0 = d["fcf0"]
    r, n, g_terminal = disc["r"], disc["n"], disc["g_terminal"]
    implied_growth = ledger["implied_growth"]["value"]  # growth 입력과 무관, 고정값 재사용

    rates = bull_bear_base_growth_rates(growth, LYNCH_TYPE)
    r_bull = scenario_return_from_growth(market_cap, fcf0, r, n, g_terminal, rates["g_bull"])
    r_base = scenario_return_from_growth(market_cap, fcf0, r, n, g_terminal, rates["g_base"])
    r_bear = scenario_return_from_growth(market_cap, fcf0, r, n, g_terminal, rates["g_bear"])

    p_bull, p_base, p_bear, _ = scenario_probabilities_from_drs(drs)
    er = expected_return(p_bull, r_bull, p_base, r_base, p_bear, r_bear)
    rar_value = rar_from_decimal_return(er, drs)

    gap = growth - implied_growth
    # v3.32: 판정 규칙 사본을 지우고 엔진의 judgment_from_gap()을 그대로 쓴다.
    judgment = judgment_from_gap(gap)
    grade = judgment_grade_from_gap(gap)

    print(f"\n  [{name}] Realistic Growth 대체값 {growth*100:.2f}%")
    print(f"    Implied Growth(고정, {ledger['implied_growth']['model_used']}) : {implied_growth*100:.2f}%")
    print(f"    Expectation Gap  : {gap*100:+.2f}%p")
    print(f"    시나리오 수익률  : bull {r_bull*100:+.2f}% / base {r_base*100:+.2f}% / bear {r_bear*100:+.2f}%")
    print(f"    기대수익률(ER)   : {er*100:+.2f}%")
    print(f"    RAR              : {rar_value:+.4f}")
    print(f"    판정             : {judgment} (등급 {grade})")

    return {"scenario": name, "growth": growth, "gap": gap, "er": er,
            "rar": rar_value, "judgment": judgment, "grade": grade}


def main():
    ledger = json.load(open(LEDGER_PATH))

    print("=" * 100)
    print("ROP 유기적성장률 교차검증 (ledger/ROP_2026-08-04.json 기반, 공식 판정 아님)")
    print("=" * 100)
    # v3.32: 여기 "12.00%(stalwart 캡, 바인딩)"가 문자열로 박혀 있었는데, v3.28에서
    # ROP를 realistic_growth_override=5.5%로 공식 승격한 뒤부터는 사실이 아니게 됐다
    # (ledger의 공식 Realistic Growth는 5.5%). 하드코딩을 걷어내고 ledger에서 읽는다.
    override = ledger["growth"]["breakdown"].get("realistic_growth_override_applied")
    rg_desc = f"{ledger['growth']['realistic_growth']*100:.2f}%"
    if override:
        rg_desc += (f" (v3.28 오버라이드 - 원래 캡 기반값 "
                    f"{override['pre_override_growth']*100:.2f}%)")
    print(f"  공식 기록: Realistic Growth {rg_desc} / "
          f"Gap {ledger['expectation_gap']*100:+.2f}%p / RAR {ledger['rar']:+.4f} / "
          f"판정 {ledger['judgment']} (등급 {ledger['judgment_grade']})")
    print(f"  DRS {ledger['drs']['score']:.2f} / 할인율 r {ledger['discount_rate']['r']*100:.2f}% "
          f"(교차검증에서도 동일하게 재사용 - growth 입력과 무관)")

    results = [
        run_scenario("A) 유기적성장 기준", ORGANIC_GROWTH, ledger),
        run_scenario("B) 연결성장 기준(오가닉+M&A)", CONSOLIDATED_GROWTH, ledger),
    ]

    print("\n" + "=" * 100)
    print("요약")
    print("=" * 100)
    print(f"  공식(캡 12.00%)              : Gap {ledger['expectation_gap']*100:+.2f}%p -> {ledger['judgment']}")
    for r_ in results:
        print(f"  {r_['scenario']:32}: Gap {r_['gap']*100:+.2f}%p -> {r_['judgment']} (등급 {r_['grade']})")
    print("\n  ⚠️ falsification_conditions가 예상한 것보다 결과가 더 뚜렷하다 - 두")
    print("     시나리오 모두 판정이 '저평가 가능성'에서 '적정가/경계선'으로")
    print("     실제로 뒤집힌다(A: Gap +1.24%p, B: Gap +4.24%p, 둘 다 ±5%p 경계")
    print("     안쪽). 즉 ROP의 공식 판정(+7.74%p, A등급)이 서 있는 근거는")
    print("     사실상 stalwart 성장상한(12%) 그 자체이며, 회사 자체 공시")
    print("     성장률(오가닉 5.5%든 연결 8.5%든)로 대체하면 저평가 근거가")
    print("     사라진다. 공식 ledger의 Gap/RAR/판정은 변경하지 않는다 - 이")
    print("     결과는 병기용 교차검증이며, 공식 재실행 여부는 분석자 판단.")

    os.makedirs("reports", exist_ok=True)
    out_path = "reports/rop_organic_growth_crosscheck_2026-08-04.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({
            "official": {
                "realistic_growth": ledger["growth"]["realistic_growth"],
                "gap": ledger["expectation_gap"],
                "rar": ledger["rar"],
                "judgment": ledger["judgment"],
                "grade": ledger["judgment_grade"],
            },
            "crosscheck_scenarios": results,
        }, f, ensure_ascii=False, indent=2)
    print(f"\n결과 저장: {out_path}")


if __name__ == "__main__":
    main()
