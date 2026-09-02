"""
Medpace Holdings, Inc.(MEDP) 정식 분석 - 2026-09-02.

경위: 연구 우선순위 큐(스크리너 tier A, Gap 추정 +19.21%p, 시총 근사
~$7.00B - `EntityPublicFloat` 2025-06-30 스냅샷). OKTA와 동일하게 스크리너
근사치가 낡아 실시간 시총과 크게 다르다 - 이번엔 그 격차가 실적 랠리가
아니라 **오래된 float 스냅샷 자체의 시차**(14개월 이상) 때문이다.

## 원자료 - SEC XBRL companyfacts(1차자료, `SecCompanyFactsProvider`,
2026-09-02 조회, CIK 0001668397, 2015~2025 11개년 확보 - 10y CAGR
산출 가능하나 아래 정의불연속 때문에 해석에 주의 필요).

## ⭐ 발견 1 - 2018년 매출 태그 정의가 바뀌었다(ASC 606 전환, M&A 아님)

2017->2018 매출이 +61.5% 급증(taxonomy가 `SalesRevenueNet`에서
`RevenueFromContractWithCustomerExcludingAssessedTax`로 바뀜, provider가
`[태그 혼재]` 경고로 자동 표시). WebSearch(투자자관계 2018 Q1/Q4 실적발표
재인용)로 확인: Medpace는 ASC 606을 2018-01-01자로 전면 도입했고, 회사
스스로 2018년 가이던스를 "2017년 순용역매출(net service revenue) $386.5M
대비 19.3~22.4% 성장"으로 제시했다 - 실제 보고매출 $704.6M은 총액표시
(gross, 상환가능비용 포함) 기준 전환의 결과이지 조직적 성장이 아니다.
CROX/BSX가 겪은 것과 같은 계열의 "정의불연속을 실제성장으로 오독" 함정.

**3y(2022->2025)/5y(2020->2025) CAGR 창은 이 경계(2017->2018)를 건드리지
않아 오염되지 않는다.** 10y(2015->2025) CAGR만 영향을 받고, 가중치가
0.2뿐이라 `realistic_growth_estimate()`의 min()·가중평균 결과에 미치는
영향은 제한적이라고 판단해 `cagr_base_year_override`는 쓰지 않았다(BKNG과
달리 실제 사용되는 3y/5y 창 자체는 깨끗함).

## 발견 2 - 부채 없음, 공격적 자사주매입

`LongTermDebtNoncurrent`/`LongTermDebtCurrent` 둘 다 FY2019 이후 $0 -
2018년 이후 부채 전액 상환. 반면 발행주식수는 2024-02(30.76M) ->
2026-02(28.38M)로 매년 감소(자사주매입) - 자기자본이 2021년 $952.9M에서
2022년 $386.4M으로 급락한 것도 대규모 buyback 회계처리 결과(적자 전환이
아님 - 순이익은 매년 흑자·증가).

## 경쟁구도(2026-09-02 WebSearch) - CRO(임상시험수탁기관) 업종

IQVIA(업계 최대, 대형제약 중심으로 세그먼트 일부 차별화) > ICON plc
(PRA Health 합병 후 대형화) > Parexel/Labcorp-Fortrea/Syneos Health(PE
소유, 중견). Medpace는 중소형 바이오텍/제약 특화 풀서비스 아웃소싱에
집중 - Q2 2026 실적(매출 +17.2%YoY·EBITDA +17.6%·순이익 +34%·신규수주
+28.2%·book-to-bill 1.13x·백로그 $3.0B+)이 업계 평균 대비 견조한 성장을
보여 시장점유율이 오히려 확대 중인 것으로 판단(2026-07-23 실적서프라이즈
+15.13% 단일일 상승, Deutsche Bank/Mizuho 등 목표가 상향).

## 실행: python3 scripts/analyze_medp_2026_09_02.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.filing_dates import pit_inputs_for
from engine.pipeline import AnalysisInputs, run_analysis, save_ledger
from engine.provenance import provenance_from_sec_facts

TICKER = "MEDP"
UA = "IRS Research chlalsrl1203@gmail.com"
TODAY = "2026-09-02"

# ── SEC XBRL companyfacts 실측(2026-09-02 조회) ──────────────────────────
REVENUE = {
    2015: 359059000.0, 2016: 421582000.0, 2017: 436152000.0,
    2018: 704589000.0, 2019: 860969000.0, 2020: 925925000.0,
    2021: 1142377000.0, 2022: 1459996000.0, 2023: 1885842000.0,
    2024: 2109054000.0, 2025: 2530234000.0,
}
OPERATING_INCOME = {
    2015: 20562000.0, 2016: 52490000.0, 2017: 64858000.0,
    2018: 101048000.0, 2019: 127263000.0, 2020: 167042000.0,
    2021: 198615000.0, 2022: 278697000.0, 2023: 336825000.0,
    2024: 446870000.0, 2025: 534935000.0,
}
OPERATING_CASHFLOW = {
    2015: 85870000.0, 2016: 91732000.0, 2017: 97385000.0,
    2018: 156584000.0, 2019: 201867000.0, 2020: 258676000.0,
    2021: 263327000.0, 2022: 388050000.0, 2023: 433374000.0,
    2024: 608815000.0, 2025: 713223000.0,
}
CAPEX = {
    2015: 6465000.0, 2016: 13537000.0, 2017: 11724000.0,
    2018: 16024000.0, 2019: 17912000.0, 2020: 31340000.0,
    2021: 28271000.0, 2022: 36879000.0, 2023: 36648000.0,
    2024: 36548000.0, 2025: 31356000.0,
}
NET_INCOME = {
    2015: -8673000.0, 2016: 13425000.0, 2017: 39122000.0,
    2018: 73185000.0, 2019: 100443000.0, 2020: 145384000.0,
    2021: 181848000.0, 2022: 245368000.0, 2023: 282810000.0,
    2024: 404386000.0, 2025: 451123000.0,
}
SBC = {
    2015: 22324000.0, 2016: 9815000.0, 2017: 4463000.0,
    2018: 6499000.0, 2019: 20741000.0, 2020: 13784000.0,
    2021: 14469000.0, 2022: 21412000.0, 2023: 20516000.0,
    2024: 25514000.0, 2025: 34786000.0,
}

# ── 대차대조표(FY2025말, 2025-12-31, SEC XBRL 실측) ──────────────────────
CASH_2025 = 497049000.0  # CashAndCashEquivalentsAtCarryingValue
DEBT_2025 = 0.0           # LongTermDebtNoncurrent/Current 둘 다 FY2019 이후 0
NET_DEBT = DEBT_2025 - CASH_2025  # -497,049,000(순현금)

DA_2025 = 27178000.0 + 946000.0  # Depreciation + AmortizationOfIntangibleAssets
EBITDA = OPERATING_INCOME[2025] + DA_2025

# ── 시가총액(2026-09-02, Alpha Vantage 종가 + 10-K 표지 발행주식수) ──────
PRICE = 583.21  # Alpha Vantage GLOBAL_QUOTE, 2026-09-01 종가(latestDay)
SHARES_OUT = 28381283.0  # FY2025 10-K 표지 dei:EntityCommonStockSharesOutstanding(2026-02-06)
MARKET_CAP = PRICE * SHARES_OUT  # 약 $16.55B

RF = 0.0475


def build_inputs() -> AnalysisInputs:
    pit = pit_inputs_for(TICKER, TODAY, list(REVENUE), user_agent=UA)

    provenance = None
    try:
        from engine.data.providers.sec import fetch_company_facts, ticker_to_cik

        cik = ticker_to_cik(TICKER, UA)
        facts = fetch_company_facts(cik, UA)
        provenance = provenance_from_sec_facts(facts, TICKER, TODAY, list(REVENUE))
    except Exception:  # noqa: BLE001 - provenance는 부가 기록, 실패해도 분석은 계속
        provenance = None

    return AnalysisInputs(
        ticker=TICKER,
        company_name="Medpace Holdings, Inc.",
        revenue_by_year=REVENUE,
        operating_income_by_year=OPERATING_INCOME,
        operating_cashflow_by_year=OPERATING_CASHFLOW,
        capex_by_year=CAPEX,
        market_cap=MARKET_CAP,
        net_debt=NET_DEBT,
        ebitda=EBITDA,
        risk_free_rate=RF,
        competitor_threat_weights=[0.20, 0.15],
        market_share_trend_pp_per_year=0.4,
        active_antitrust_or_regulatory_case=False,
        demand_sensitivity_pct=0.20,
        subjective_input_basis=(
            "competitor_threat_weights=[0.20(IQVIA), 0.15(ICON plc)] - IQVIA가 "
            "업계 최대(대형제약 중심, Medpace의 중소형 바이오텍 특화 세그먼트와는 "
            "부분적으로만 겹침)라 완전 직접경쟁 대비 낮춰 반영, ICON plc는 PRA "
            "Health 합병 후 대형화된 2선 경쟁자. market_share_trend_pp_per_year="
            "+0.4 - Q2 2026 실적(매출 +17.2%YoY·신규수주 +28.2%·book-to-bill "
            "1.13x·백로그 $3.0B+)이 업계 평균 대비 견조해 점유율 확대 추세로 "
            "판단(2026-09-02 WebSearch, 정량 시장점유율 데이터는 미확보라 실적 "
            "모멘텀으로 근사). demand_sensitivity_pct=0.20 - CLAUDE.md "
            "업종앵커표 '기업용 필수 SW·전문서비스(계약기반, 전환비용 높음)' "
            "버킷(CDNS·DSGX·PGR·ROP·BRO 등) 적용 - 진행 중인 임상시험의 CRO "
            "전환비용이 극히 높고(시험 중단·재계약 리스크), 다년 계약구조라 "
            "경기민감도가 낮음."
        ),
        model_used="two_stage",
        model_choice_reason=(
            "trailing 매출 CAGR(3y ~20%대, 5y ~22%대)이 default_terminal_growth"
            "(2.0~4.5%)보다 여전히 크게 높고, Q2 2026 실측 성장률(+17.2%YoY)도 "
            "터미널 성장률에서 멀어 다년 수렴 경로(two_stage)가 적절하다고 판단. "
            "2018년 매출 태그 정의 전환(ASC 606, [태그 혼재] 경고)이 10y CAGR "
            "창에만 영향을 주고 실제 채택되는 3y/5y 창은 오염되지 않아 "
            "cagr_base_year_override는 쓰지 않았다."
        ),
        falsification_conditions=(
            "다음 분기(Q3 2026) 신규수주(book-to-bill)가 1.0x 아래로 하락하거나 "
            "백로그 성장이 둔화되면, 또는 바이오텍 자금조달 환경 악화로 소형 "
            "바이오텍 고객의 임상시험 취소·연기가 늘어나 매출 가이던스가 하향되면 "
            "이 판정을 재검토할 것."
        ),
        price_at_analysis=PRICE,
        currency="USD",
        net_income_by_year=NET_INCOME,
        sbc_by_year=SBC,
        data_sources=[
            "SEC XBRL companyfacts (CIK 0001668397, 조회 2026-09-02)",
            "Alpha Vantage GLOBAL_QUOTE (2026-09-01 종가 $583.21)",
            "WebSearch: Medpace Q2 2026 실적발표(2026-07-23), CRO 업종 경쟁구도",
        ],
        **pit,
        provenance=provenance,
    )


if __name__ == "__main__":
    inputs = build_inputs()
    result = run_analysis(inputs)
    path = save_ledger(result)
    print(f"saved: {path}")
