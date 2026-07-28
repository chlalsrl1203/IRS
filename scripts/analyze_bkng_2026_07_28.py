"""
BKNG(Booking Holdings) 정식 분석 - 2026-07-28.

경위: 2026-07-26 스크리닝(scripts/screen_2026_07_26.py)에서 A등급 통과(Gap 추정
+18.99%p)한 후보를 정식 분석한다. 공식 83개 큐에는 없는 비큐(ad-hoc) 분석이다
(GOOGL/UBER/ADBE 등과 동일 범주).

⚠️ 이 종목에서 엔진 한계가 드러나 v3.21 기능(cagr_base_year_override)을 추가했다:
BKNG은 코로나가 정확히 5년 룩백 자리(FY2020)에 걸린다.
  - FY2020 FCF = OCF $85M - capex $286M = **-$201M(음수)** -> 5년 CAGR 정의 불가
  - FY2020 매출 $6,796M은 전년比 -54.9% 폭락한 저점 -> 이걸 기준으로 5년 CAGR을
    내면 31.7%가 나오는데, 이는 '성장'이 아니라 '회복 반등'이다
스크리닝에서 쓴 4년 CAGR(2021 기준, FCF 37.86%)도 같은 이유로 과대였다.
=> 기준연도를 **FY2019(코로나 이전 고점)**로 명시 변경했다. 저점이 아닌 고점을
   기준으로 삼는 것이므로 성장률을 부풀리지 않는 보수적 선택이다.

원자료: 전부 SEC EDGAR as-filed 10-K에서 직접 추출(2026-07-28 조회).
  FY2025 10-K (0001075531-26-000009): R5 손익, R9 현금흐름, R3 재무상태표
  FY2022 10-K (0001075531-23-000016): R5 손익, R9 현금흐름
  FY2019 10-K (0001075531-20-000011): R4 손익, R8 현금흐름
  FY2016 10-K (0001075531-17-000009): R4 손익, R9 현금흐름 (당시 사명 Priceline Group)
시가총액: stockanalysis.com 2026-07-27 종가 기준 $144.74B(주가 $186.79 x 774.88M주).

실행: python3 scripts/analyze_bkng_2026_07_28.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.pipeline import AnalysisInputs, cross_check_prior_record, run_analysis, save_ledger

M = 1_000_000

# ── SEC EDGAR as-filed 실측 (단위: 달러) ────────────────────────────────
REVENUE = {
    2014: 8441.971 * M, 2015: 9223.987 * M, 2016: 10743.006 * M,
    2017: 12681 * M, 2018: 14527 * M, 2019: 15066 * M,
    2020: 6796 * M,                      # 코로나: 전년比 -54.9%
    2021: 10958 * M, 2022: 17090 * M, 2023: 21365 * M,
    2024: 23739 * M, 2025: 26917 * M,
}
OPERATING_INCOME = {
    2014: 3073.312 * M, 2015: 3258.907 * M,
    2016: 2906.313 * M,                  # 굿윌손상 $940.7M 반영된 해
    2017: 4538 * M, 2018: 5341 * M, 2019: 5345 * M,
    2020: -631 * M,                      # 코로나: 영업손실
    2021: 2496 * M, 2022: 5102 * M, 2023: 5835 * M,
    2024: 7555 * M, 2025: 8825 * M,
}
OPERATING_CASHFLOW = {
    2014: 2914.397 * M, 2015: 3102.231 * M, 2016: 3924.697 * M,
    2017: 4662 * M, 2018: 5338 * M, 2019: 4865 * M,
    2020: 85 * M,                        # 코로나: 거의 소멸
    2021: 2820 * M, 2022: 6554 * M, 2023: 7344 * M,
    2024: 8323 * M, 2025: 9409 * M,
}
CAPEX = {
    2014: 131.504 * M, 2015: 173.915 * M, 2016: 219.889 * M,
    2017: 288 * M, 2018: 442 * M, 2019: 368 * M,
    2020: 286 * M, 2021: 304 * M, 2022: 368 * M, 2023: 345 * M,
    2024: 429 * M, 2025: 322 * M,
}

# 재무상태표 (FY2025 10-K R3, 2025-12-31 기준)
CASH = 17203 * M
SHORT_TERM_DEBT = 1880 * M
LONG_TERM_DEBT = 16856 * M
# 장기투자자산 $582M은 현금성으로 보지 않고 제외(보수적). CDNS 등 기존 관행은
# '현금+단기투자'였는데 BKNG 재무상태표에 단기투자 별도 항목이 없다.
NET_DEBT = (SHORT_TERM_DEBT + LONG_TERM_DEBT) - CASH

DA_2025 = 623 * M                        # FY2025 10-K R9 감가상각비+무형자산상각
EBITDA = OPERATING_INCOME[2025] + DA_2025

MARKET_CAP = 144.74e9
RF = 0.0447                              # 미국 10Y, 2026-07 기준(기존 분석과 동일)


def build_inputs() -> AnalysisInputs:
    return AnalysisInputs(
        ticker="BKNG",
        company_name="Booking Holdings Inc.",
        revenue_by_year=REVENUE,
        operating_income_by_year=OPERATING_INCOME,
        operating_cashflow_by_year=OPERATING_CASHFLOW,
        capex_by_year=CAPEX,
        market_cap=MARKET_CAP,
        net_debt=NET_DEBT,
        ebitda=EBITDA,
        risk_free_rate=RF,

        competitor_threat_weights=[0.50, 0.40, 0.35],
        market_share_trend_pp_per_year=0.0,
        active_antitrust_or_regulatory_case=True,
        demand_sensitivity_pct=0.60,
        subjective_input_basis=(
            "Expedia 0.50(직접 경쟁 OTA, 매출 약 $15B로 BKNG과 함께 미국·유럽 "
            "온라인 여행예약의 약 60%를 과점), Airbnb 0.40(대체숙박 시장을 새로 "
            "만들어 BKNG·Expedia가 뒤따라 진입중, 매출 $11.94B), Google Travel "
            "0.35(호텔광고·직접예약 푸시로 OTA 자체를 중간에서 걷어낼 수 있는 "
            "구조적 위협). 셋 다 2026-07 WebSearch 기반 [추정치]. "
            "market_share_trend=0.0: BKNG이 객실판매를 꾸준히 늘리고 있으나 "
            "대체숙박에서는 Airbnb에 밀리는 양면이 있어 순 유기적 점유율 변화를 "
            "뒷받침할 정량근거가 없어 중립 처리 [추정치]. "
            "active_antitrust_or_regulatory_case=True: 근거 명확하다. 스페인 CNMC가 "
            "2024년 €413.2M 과징금(CNMC 사상 최대, 스페인 점유율 70~90% 지배력 "
            "남용 - 다만 2025-02 스페인 국가법원이 항소심 판단까지 집행정지), "
            "2024-05-13 EU DMA 게이트키퍼 지정(2024-11-13부터 의무 적용), "
            "2025-09 EU가 DSA로 가짜매물·금융사기 대응 관련 공식 조사 착수, "
            "프랑스 경쟁당국도 2026-01까지 관행시정 최종명령. "
            "demand_sensitivity=0.60: 이 프로젝트에서 가장 높게 잡은 값이다. "
            "여행수요는 대표적 재량지출이고, 실제로 FY2020 매출이 -54.9% 폭락한 "
            "실측 이력이 있다(PH 산업재 0.35, TYL 정부SW 0.05과 대비)."
        ),

        model_used="two_stage",
        model_choice_reason=(
            "single_stage(4.7%대)와 two_stage(5.7%대)의 괴리가 약 1.0%p로 v3.19 "
            "경고임계값(3%p)에 한참 못 미쳐 **모델 선택이 판정을 바꾸지 않는다**"
            "(CDNS 10.97%p, PH 7.1%p 사례와 대조적). 그 전제 위에서, BKNG이 아직 "
            "두 자릿수 매출성장 중인 플랫폼이라 명시적 성장기간을 모델링하는 "
            "two_stage가 이론적으로 더 적합하다고 보아 채택. 이 종목은 첫 분석이라 "
            "대조할 과거 기록이 없다."
        ),

        cagr_base_year_override=2019,
        cagr_base_year_override_reason=(
            "기본 기준연도인 FY2020은 코로나 직격탄을 맞은 해라 두 가지가 동시에 "
            "망가진다. (1) FCF가 -$201M(OCF $85M - capex $286M)로 음수여서 CAGR이 "
            "수학적으로 정의되지 않는다. (2) 매출도 전년比 -54.9% 폭락한 저점이라 "
            "이를 기준으로 하면 5년 CAGR이 31.7%로 나오는데 이는 성장이 아니라 "
            "회복 반등이다(2026-07-26 스크리닝이 쓴 4년 CAGR 37.86%도 같은 오류). "
            "대안으로 **FY2019(코로나 이전 고점)**를 골랐다. 저점이 아니라 고점을 "
            "기준으로 삼으므로 성장률을 부풀리지 않으며, 코로나 붕괴와 회복을 "
            "모두 포함한 6년 구간이 되어 through-cycle 성장률에 가깝다."
        ),

        data_sources=[
            "SEC EDGAR 10-K FY2025(0001075531-26-000009) R5/R9/R3, as-filed, 2026-07-28 조회",
            "SEC EDGAR 10-K FY2022(0001075531-23-000016) R5/R9",
            "SEC EDGAR 10-K FY2019(0001075531-20-000011) R4/R8",
            "SEC EDGAR 10-K FY2016(0001075531-17-000009) R4/R9 (당시 Priceline Group)",
            "stockanalysis.com 시가총액 $144.74B (2026-07-27 종가)",
            "WebSearch: OTA 경쟁구도 2026, 스페인 CNMC 과징금/EU DMA/DSA 규제현황",
        ],
    )


def main():
    result = run_analysis(build_inputs())
    d, g = result["derived"], result["growth"]

    print("=" * 100)
    print(f"BKNG 정식 분석 결과 ({result['meta']['analyzed_at'][:10]}, 엔진 {result['meta']['engine_version']})")
    print("=" * 100)
    print(f"  CAGR 기준연도    : {d['cagr_5y_base_year']}년 ({d['cagr_5y_span']}년 구간)")
    print(f"  매출 CAGR        : 3y {d['revenue_cagr_3y']*100:.2f}% / "
          f"{d['cagr_5y_span']}y {d['revenue_cagr_5y']*100:.2f}% / 10y {d['revenue_cagr_10y']*100:.2f}%")
    print(f"  FCF CAGR         : {d['fcf_cagr_5y']*100:.2f}%   (FCF0 ${d['fcf0']/1e9:.3f}B)")
    print(f"  최악 YoY 매출    : {d['worst_yoy_revenue_growth']*100:.2f}% ({d['worst_yoy_year']}년)")
    print(f"  순부채/EBITDA    : {d['net_debt_to_ebitda']:.3f}배")
    print()
    print(f"  DRS              : {result['drs']['score']:.2f}")
    for k, v in result["drs"]["components"].items():
        print(f"      {k:24} {v:5.2f}")
    print(f"  Lynch 유형       : {result['lynch']['used']}")
    print(f"  구조적 할인      : {g['structural_discount_pct']*100:.2f}%")
    print(f"  Realistic Growth : {g['realistic_growth']*100:.2f}%")
    print(f"  Implied Growth   : {result['implied_growth']['value']*100:.2f}% "
          f"({result['implied_growth']['model_used']})")
    print(f"  Expectation Gap  : {result['expectation_gap']*100:+.2f}%p")
    print(f"  RAR              : {result['rar']:+.4f}")
    print(f"  강건성점검 flip  : {result['sensitivity_check'].get('judgment_flipped')}")
    print(f"  Confidence       : {result['confidence']['final']}/100")
    print(f"  ** 판정          : {result['judgment']} **")
    print()
    if result["data_limitations"]:
        print("  데이터 한계·경고:")
        for x in result["data_limitations"]:
            print(f"    - {x}")

    path = save_ledger(result)
    print(f"\n  ledger 저장: {path}")

    # 스크리닝 추정치와 대조 - 추정이 실제와 얼마나 벌어졌는지 기록한다
    print("\n" + "=" * 100)
    print("스크리닝 추정치 vs 정식 분석 (스크리너 정확도 사후검증)")
    print("=" * 100)
    print(f"  {'항목':20} {'스크리닝 추정':>14} {'정식 분석':>12} {'차이':>10}")
    for label, est, act in [
        ("내재성장률", 0.0366, result["implied_growth"]["value"]),
        ("현실적성장률", 0.2265, g["realistic_growth"]),
        ("Expectation Gap", 0.1899, result["expectation_gap"]),
        ("DRS", 34.6, result["drs"]["score"]),
    ]:
        if label == "DRS":
            print(f"  {label:20} {est:13.1f} {act:12.1f} {act-est:+10.1f}")
        else:
            print(f"  {label:20} {est*100:12.2f}% {act*100:11.2f}% {(act-est)*100:+9.2f}%p")
    return result


if __name__ == "__main__":
    main()
