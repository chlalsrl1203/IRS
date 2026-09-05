"""
Micron Technology(MU) 참조 점검 - 2026-09-04. **보유 6순위(5.7%) 종목.**

## ⚠️ 이 스크립트는 ledger를 만들지 않는다

`run_analysis()`를 **메모리에서만** 실행해 DRS·할인율 등 위험 파라미터를 얻고,
Expectation Gap은 여러 FCF0 기준으로 재계산해 **범위로만** 제시한다. 공식
판정으로 승격하지 않는 이유는 아래 ①이다 - `engine/thesis_monitor.py`(v3.42)가
확립한 "재계산 결과를 ledger/에 절대 저장하지 않는다" 원칙과 같은 처리다.

## ① MU를 FRAMEWORK_MISMATCH로 유지한다 - 다만 **제외 사유를 정정한다**

2026-08-14 스크리닝 배치의 제외 사유는 이랬다:
  > "5y CAGR 시작점(FY2020)의 FCF가 $83M로 거의 0에 수렴 ... FCF CAGR이
  >  82.23%라는 터무니없는 숫자가 나온다 ... 5y CAGR 하나로 이 정도
  >  변동성을 대표할 수 없다"

**이 사유는 부정확하다.** `realistic_growth_estimate()`는
`min(FCF CAGR, 매출 가중평균 CAGR)`을 쓰므로 82.23%짜리 아티팩트는
**자동으로 버려진다**(MU 실측: 매출 가중평균 8.63% < FCF CAGR 82.23% ->
8.63% 채택). PATH·CHWY·MNDY·UBER에서 이미 확인된 '보호가 작동하는' 경우와
같다. 즉 그 아티팩트만으로는 제외 근거가 되지 않는다.

**진짜 제외 사유는 훨씬 단순하고 결정적이다 - 연차 데이터가 이미 낡았다.**
SEC 1차자료 실측(2026-09-04 조회):

  | 기간 | 매출 | 영업이익 | 순이익 |
  |---|---|---|---|
  | **FY2025 연간**(2025-08-28 종료) | $37,378M | $9,770M | $8,539M |
  | FY2026 Q1(2025-11-27) | $13,643M | $6,136M | $5,240M |
  | FY2026 Q2(2026-02-26) | $23,860M | $16,135M | $13,785M |
  | **FY2026 Q3**(2026-05-28) | **$41,456M** | **$33,318M** | **$28,243M** |
  | **FY2026 9개월 누적** | **$78,959M** | **$55,589M** | **$47,268M** |

**단일 분기(Q3) 매출이 직전 회계연도 전체를 넘어섰고, 9개월 누적은 그
2.1배다.** 이 엔진은 연차(10-K) 시계열만 쓰므로 최신 데이터가 FY2025인데,
그 시점 이후 사업 규모가 3배 넘게 변했다. FY2025 기반 FCF-DCF는 계산은
되지만 **답하는 질문 자체가 이미 무의미**하다.

이것은 KEYS/KLAC(반도체 장비, trailing CAGR이 AI 수요 인플렉션 과소추정)와
같은 계열이되 **정도가 비교가 안 될 만큼 극단적**이다 - KEYS는 가이던스가
CAGR보다 높은 정도였지만, MU는 **이미 보고된 실적**이 연차 기준의 3배다.
CLAUDE.md '알려진 한계 3건째'의 네 번째 관측 사례이자 최악의 사례로 기록한다.

## ② 그래서 무엇을 볼 수 있는가 - FCF0 기준을 셋으로 나눠 범위를 낸다

Expectation Gap은 FCF0에 직접 좌우된다. 세 기준을 병기한다:

  - `FY2025_연간`      : $1,668M  (OCF $17,525M - capex $15,857M) - 엔진 표준
  - `FY2026_9개월누적` : $26,100M (OCF $45,702M - capex $19,602M)
  - `FY2026Q3_연율화`  : $70,248M (Q3 단독 FCF $17,562M x 4)

⚠️ 셋 다 결함이 있다 - FY2025는 낡았고, 9개월 누적은 연간이 아니며, Q3
연율화는 사상 최고 분기를 영구화하는 가정이다. **어느 하나를 정답으로
고르지 않는다**(is_insurer의 P/B, sbc_cross_check와 동일 원칙).

## ③ 회사 자신이 공시한 전방 지표(2026-09-04 WebSearch)

  - FY2026 Q4 가이던스 **매출 $50B**, 비GAAP 총마진 **86%**
  - FY2026 capex 약 **$27B**(FY2027은 더 늘 것이라고 예고, 증가분의 절반
    이상이 건설)
  - **16건의 take-or-pay 전략고객계약으로 최소 계약매출 약 $100B, 선수금
    $22B 확보** - 이 정도 규모의 계약잔액은 이 트래커에서 본 적이 없다
  - HBM4 주력 고객 대량출하 중, HBM4E는 2027년 양산 목표

## ④ 참고 - 순이익 기준으로 보면 그림이 정반대다

시가총액 $1,147.9B(주가 $1,016.59 x 1,129.4M주) 기준:
  - FY2025 순이익 $8,539M -> **P/E 134배**(비싸 보인다)
  - FY2026 9개월 순이익 $47,268M -> **연율화 P/E 약 18배**
  - Q3 단독 연율화($112,972M) -> **P/E 약 10배**

**FY2025 기준과 최신 실적 기준이 정반대 결론을 준다.** 이 종목에서 낡은
데이터를 쓰는 비용이 얼마나 큰지 보여주는 실측이다.

## ⑤ 언제 정식분석이 가능해지는가

**FY2026 10-K(2026-10경 제출 예상)** 이후. 그때는 FY2026 연간 실적이
연차 시계열에 들어와 이 사이클 국면이 반영된다. 다만 그때도 반도체 메모리
특유의 boom/bust(FY2023 매출 -49.5%, 영업손실 $-5,745M) 때문에 단일 연도를
영구화하는 DCF의 한계는 남는다 - **정식분석을 하더라도 Confidence를 액면
그대로 신뢰하지 말 것.**

실행: python3 scripts/mu_reference_check_2026_09_04.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.expectation_gap_engine import (
    implied_growth_single_stage,
    implied_growth_two_stage,
    judgment_from_gap,
    judgment_grade_from_gap,
)
from engine.pipeline import AnalysisInputs, run_analysis

OUT = "reports/mu_reference_check_2026-09-04.json"

# ── SEC XBRL companyfacts 실측(CIK 0000723125, 2026-09-04 조회) ─────────
# MU는 52/53주 회계연도(8월 말~9월 초 종료). FY2015 매출만 us-gaap:
# SalesRevenueNet($16,192M), FY2016~2018은 Revenues, FY2019~ 는
# RevenueFromContractWithCustomerExcludingAssessedTax에서 나온다.
REVENUE = {
    2015: 16192000000.0, 2016: 12399000000.0, 2017: 20322000000.0,
    2018: 30391000000.0, 2019: 23406000000.0, 2020: 21435000000.0,
    2021: 27705000000.0, 2022: 30758000000.0, 2023: 15540000000.0,
    2024: 25111000000.0, 2025: 37378000000.0,
}
OPERATING_INCOME = {
    2015: 2998000000.0, 2016: 168000000.0, 2017: 5868000000.0,
    2018: 14994000000.0, 2019: 7376000000.0, 2020: 3003000000.0,
    2021: 6283000000.0, 2022: 9702000000.0, 2023: -5745000000.0,
    2024: 1304000000.0, 2025: 9770000000.0,
}
OPERATING_CASHFLOW = {
    2015: 5208000000.0, 2016: 3168000000.0, 2017: 8153000000.0,
    2018: 17400000000.0, 2019: 13189000000.0, 2020: 8306000000.0,
    2021: 12468000000.0, 2022: 15181000000.0, 2023: 1559000000.0,
    2024: 8507000000.0, 2025: 17525000000.0,
}
CAPEX = {
    2015: 4021000000.0, 2016: 5817000000.0, 2017: 4734000000.0,
    2018: 8879000000.0, 2019: 9780000000.0, 2020: 8223000000.0,
    2021: 10030000000.0, 2022: 12067000000.0, 2023: 7676000000.0,
    2024: 8386000000.0, 2025: 15857000000.0,
}
NET_INCOME = {
    2015: 2899000000.0, 2016: -276000000.0, 2017: 5089000000.0,
    2018: 14135000000.0, 2019: 6313000000.0, 2020: 2687000000.0,
    2021: 5861000000.0, 2022: 8687000000.0, 2023: -5833000000.0,
    2024: 778000000.0, 2025: 8539000000.0,
}
SBC = {
    2015: 168000000.0, 2016: 191000000.0, 2017: 215000000.0,
    2018: 198000000.0, 2019: 243000000.0, 2020: 328000000.0,
    2021: 378000000.0, 2022: 514000000.0, 2023: 596000000.0,
    2024: 833000000.0, 2025: 972000000.0,
}

# ── FY2026 중간 실적(10-Q 실측) ──────────────────────────────────────────
Q_REVENUE = {"FY26Q1": 13643e6, "FY26Q2": 23860e6, "FY26Q3": 41456e6}
Q_NET_INCOME = {"FY26Q1": 5240e6, "FY26Q2": 13785e6, "FY26Q3": 28243e6}
YTD9M_OCF = 45702e6
YTD9M_CAPEX = 19602e6
Q3_OCF = 45702e6 - 20314e6          # 9개월 - 6개월
Q3_CAPEX = 19602e6 - 11776e6

# ── 대차대조표(2026-05-28 10-Q) ─────────────────────────────────────────
DEBT = 5722000000.0            # DebtAndCapitalLeaseObligations
CASH = 24995000000.0
AFS = 1027000000.0 + 4106000000.0   # 유동 + 비유동 매도가능채무증권
NET_DEBT = DEBT - CASH - AFS   # -$24,406,000,000(순현금)

DA_2025 = 8352000000.0
EBITDA = OPERATING_INCOME[2025] + DA_2025

PRICE = 1016.59                # Alpha Vantage GLOBAL_QUOTE, latestDay 2026-09-04
SHARES_OUT = 1129400000.0      # 2026-06-17 10-Q 표지
MARKET_CAP = PRICE * SHARES_OUT

RF = 0.0475

FCF_BASES = {
    "FY2025_연간(엔진 표준)": OPERATING_CASHFLOW[2025] - CAPEX[2025],
    "FY2026_9개월누적": YTD9M_OCF - YTD9M_CAPEX,
    "FY2026Q3_연율화": (Q3_OCF - Q3_CAPEX) * 4,
}


def build_inputs() -> AnalysisInputs:
    return AnalysisInputs(
        ticker="MU",
        company_name="Micron Technology, Inc.",
        revenue_by_year=REVENUE,
        operating_income_by_year=OPERATING_INCOME,
        operating_cashflow_by_year=OPERATING_CASHFLOW,
        capex_by_year=CAPEX,
        market_cap=MARKET_CAP,
        net_debt=NET_DEBT,
        ebitda=EBITDA,
        risk_free_rate=RF,
        usd_fx_rate=1.0,
        competitor_threat_weights=[0.40, 0.35, 0.15],
        market_share_trend_pp_per_year=1.0,
        active_antitrust_or_regulatory_case=False,
        demand_sensitivity_pct=0.55,
        subjective_input_basis=(
            "competitor_threat_weights=[0.40(SK하이닉스 - HBM 선두 경쟁), "
            "0.35(삼성전자 - 메모리 최대 생산자), 0.15(중국 CXMT/YMTC 등 "
            "후발 증설)] - DRAM/HBM은 3사 과점이며 HBM4 세대에서 경쟁이 "
            "격화되는 국면. market_share_trend_pp_per_year=+1.0 - HBM4 "
            "주력고객 대량출하와 $100B take-or-pay 계약 확보로 점유율이 "
            "후퇴하고 있다는 증거가 없으나, 세대 전환마다 순위가 바뀌는 "
            "업종이라 크게 반영하지 않는다. demand_sensitivity_pct=0.55 - "
            "CLAUDE.md 업종앵커표에 메모리반도체 버킷이 없어 '여행·레저"
            "(재량소비 최상단, 0.55)'와 같은 수준을 적용했다. 근거는 실측 "
            "변동성이다 - FY2023 매출 **-49.5%YoY**, 영업손실 $-5,745M으로 "
            "이 트래커의 어떤 종목보다 경기민감도가 크다."
        ),
        model_used="two_stage",
        model_choice_reason=(
            "⚠️ 이 분석은 **참조용이며 ledger로 저장되지 않는다**(위 docstring ①). "
            "그럼에도 모델을 명시하는 이유는 `run_analysis()`가 근거 없이는 "
            "실행을 거부하기 때문이다(v3.19). two_stage를 쓰는 근거: 매출 "
            "CAGR이 default_terminal_growth를 웃돌고, FY2026 실적이 AI 메모리 "
            "슈퍼사이클로 급등 중이나 메모리 업종은 정의상 사이클을 되돌리므로 "
            "고성장->terminal 수렴 경로가 구조에 맞다. 다만 어떤 모델을 쓰든 "
            "**FY2025 기준 FCF0가 이미 낡았다는 문제는 해결되지 않는다.**"
        ),
        falsification_conditions=(
            "이 항목은 참조 계산이라 공식 반증조건으로 등록하지 않는다. "
            "정식분석 재개 조건은 FY2026 10-K 제출(2026-10경 예상)이다."
        ),
        price_at_analysis=PRICE,
        currency="USD",
        net_income_by_year=NET_INCOME,
        sbc_by_year=SBC,
        data_sources=[
            "SEC XBRL companyfacts (CIK 0000723125 Micron, 조회 2026-09-04)",
            "SEC 10-Q (FY2026 Q1~Q3 분기실적·2026-05-28 대차대조표·"
            "표지 발행주식수 1,129,400,000주)",
            "Alpha Vantage GLOBAL_QUOTE (latestDay 2026-09-04, $1,016.59)",
            "WebSearch: MU FY2026 Q3 실적($41.46B, 비GAAP 총마진 84.9%)·"
            "Q4 가이던스($50B)·FY2026 capex $27B·take-or-pay $100B"
            "(investors.micron.com/CNBC/Futurum, 2026-09-04 재인용)",
        ],
    )


def main() -> int:
    # ⚠️ run_analysis()는 메모리에서만 돈다 - save_ledger()를 부르지 않는다.
    result = run_analysis(build_inputs())
    d = result["discount_rate"]
    r, n, g_term = d["r"], d["n"], d["g_terminal"]
    rg = result["growth"]["realistic_growth"]

    rows = []
    for label, fcf0 in FCF_BASES.items():
        ig_two, _, _ = implied_growth_two_stage(MARKET_CAP, fcf0, r, n, g_term)
        ig_one = implied_growth_single_stage(MARKET_CAP, fcf0, r)
        gap = rg - ig_two
        rows.append({
            "fcf0_basis": label,
            "fcf0": fcf0,
            "fcf_yield": fcf0 / MARKET_CAP,
            "implied_growth_two_stage": ig_two,
            "implied_growth_single_stage": ig_one,
            "gap": gap,
            "judgment": judgment_from_gap(gap),
            "grade": judgment_grade_from_gap(gap),
        })

    ni_ttm_ann = sum(Q_NET_INCOME.values()) / 3 * 4
    pe = {
        "FY2025_연간": MARKET_CAP / NET_INCOME[2025],
        "FY2026_9개월_연율화": MARKET_CAP / ni_ttm_ann,
        "FY2026Q3_연율화": MARKET_CAP / (Q_NET_INCOME["FY26Q3"] * 4),
    }

    print("=== MU 참조 점검 2026-09-04 (ledger 미생성) ===")
    print(f"시가총액       : ${MARKET_CAP/1e9:,.1f}B  (주가 ${PRICE}, "
          f"주식수 {SHARES_OUT:,.0f})")
    print(f"순부채         : ${NET_DEBT/1e9:,.1f}B(순현금)")
    print(f"DRS            : {result['drs']['score']:.2f}   r={r*100:.2f}%  "
          f"n={n}  g_term={g_term*100:.2f}%")
    print(f"Lynch 유형     : {result['lynch']['used']}")
    print(f"Realistic Growth: {rg*100:.2f}%  "
          f"(매출CAGR 3y/5y/10y = "
          f"{result['growth']['breakdown']['revenue_cagr_inputs']})")
    print()
    print(f"{'FCF0 기준':>24}{'FCF0($B)':>11}{'FCF수익률':>10}{'IG':>9}"
          f"{'Gap':>10}  판정(등급)")
    for x in rows:
        print(f"{x['fcf0_basis']:>24}{x['fcf0']/1e9:>10,.1f}"
              f"{x['fcf_yield']*100:>9.2f}%{x['implied_growth_two_stage']*100:>8.2f}%"
              f"{x['gap']*100:>+9.2f}%p  {x['judgment']}({x['grade']})")
    print()
    print("참고 - 순이익 기준 P/E:")
    for k, v in pe.items():
        print(f"  {k:>22}: {v:>6.1f}배")
    print()
    print("⚠️ 어느 기준도 정답이 아니다. FY2025는 이미 3배 낡았고, 9개월 누적은")
    print("   연간이 아니며, Q3 연율화는 사상 최고 분기를 영구화하는 가정이다.")
    print("   -> 공식 판정 없음(FRAMEWORK_MISMATCH 유지). FY2026 10-K 이후 재개.")

    payload = {
        "ticker": "MU",
        "as_of": "2026-09-04",
        "status": "FRAMEWORK_MISMATCH",
        "ledger_written": False,
        "exclusion_reason_corrected": (
            "2026-08-14 배치의 제외 사유('FCF 5y CAGR 82.23% 아티팩트')는 "
            "부정확하다 - realistic_growth_estimate()의 min() 로직이 그 값을 "
            "자동으로 버린다(실측: 매출 가중평균 8.63% 채택). 진짜 사유는 "
            "**연차 데이터 노후화**다: FY2026 Q3 단독 매출($41,456M)이 "
            "FY2025 연간($37,378M)을 넘어섰고 9개월 누적은 그 2.1배다."
        ),
        "market_cap": MARKET_CAP,
        "price_at_check": PRICE,
        "discount_rate": {"r": r, "n": n, "g_terminal": g_term,
                          "drs": result["drs"]["score"]},
        "realistic_growth": rg,
        "fcf0_scenarios": rows,
        "pe_reference": pe,
        "interim_actuals": {
            "quarterly_revenue": Q_REVENUE,
            "quarterly_net_income": Q_NET_INCOME,
            "ytd9m_ocf": YTD9M_OCF,
            "ytd9m_capex": YTD9M_CAPEX,
        },
        "reopen_condition": "FY2026 10-K 제출(2026-10경 예상) 이후 정식분석",
        "known_limitation": (
            "이 참조 계산의 DRS·할인율·Realistic Growth는 전부 FY2015~2025 "
            "연차 시계열에서 나온 값이라 위 노후화 문제를 똑같이 안고 있다. "
            "FCF0만 바꿔 끼운 것이므로 세 행의 Gap 차이는 'FCF0 기준을 "
            "바꾸면 얼마나 달라지는가'만 보여줄 뿐 어느 것도 공정가치 "
            "추정이 아니다."
        ),
    }
    os.makedirs("reports", exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"\nsaved: {OUT}  (ledger는 만들지 않았다)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
