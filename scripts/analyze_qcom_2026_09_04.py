"""
Qualcomm Incorporated(QCOM) 정식 분석 - 2026-09-04.

경위: 연구 우선순위 큐 tier A, 스크리너 Gap 추정 +9.02%p. FRAMEWORK_MISMATCH
20종목 + BYD·CRM·(HBAN/CNM 배제)·DECK 정식분석 완료 뒤 큐 순서상 다음 후보.

## 원자료 - SEC XBRL companyfacts(CIK 0000804328, 2026-09-04 조회,
FY2015~FY2025 11개년 확보 - FY2026(2026-09말 결산)은 아직 미제출).

## ⚠️ MU(이미 배제)와 비교 - 반도체 사이클성이지만 계산 아티팩트가 아니라
실제 변동이라 정량모델 적용 가능하다고 판단

매출: FY2021 $335.66억(+42.6%, 5G램프)→FY2022 $442.00억(+31.7%, 사이클
정점)→FY2023 $358.20억(-19.0%, 반도체 다운사이클)→FY2025 $442.84억(회복).
3y CAGR(2022기준)이 정확히 0.06%(2022가 사이클 정점이라 3년 뒤에도 매출이
거의 같음)인 반면 5y CAGR(2020기준)은 13.48%(2020이 상대적 저점) - 창마다
크게 갈린다. **그러나 MU와 달리 계산 아티팩트가 아니다** - MU는 FCF
시작값이 거의 0(FY2020 $83M)에 수렴해 CAGR 82%라는 무의미한 수치가
나왔지만, QCOM은 FCF 시작값이 전부 건전한 양수($44~68억)이고 매출·FCF
CAGR 전부 정의 가능한 실측치다. 사이클성 자체는 lynch_type의 cyclical
분류와 구조적할인율이 다루도록 설계된 영역이라(BSX의 COVID 매출감소가
cyclical로 정상 처리된 선례) 정량모델에서 배제하지 않고 그대로 진행했다.
가중평균(0.5*3y+0.3*5y+0.2*10y≈5.23%)도 3y의 과반 가중치가 사이클 정점
기준값을 자연히 눌러 극단값이 되지 않는다.

## ⚠️ Apple 모뎀 사업 구조적 손실 - 2026-09-04 WebSearch로 실측 확인된
가장 중요한 리스크

Apple이 2027년까지 자체 모뎀으로 QCOM 부품을 완전 대체 목표 - 연 $57~78억
규모 Apple 모뎀매출이 소멸 예정(2026 Q3 실적발표에서 CEO가 "다음 분기
Apple 매출 -50%" 명시적 언급, WebSearch 확인). **다만 이를 상쇄할 다각화가
이미 실측 트랙션을 보이고 있다**: 자동차부문 QCT매출 $16억(+61%YoY,
사상최대 분기), 연환산 자동차매출 런레이트 $60억→$70억으로 상향. 데이터
센터AI $50억(FY2027)·$150억(FY2029) 목표, 비핸드셋 QCT매출이 FY2027
+60%YoY 성장해 Apple 손실분 전액 상쇄를 회사가 공개 목표로 제시(2026-07-29
실적발표). falsification_conditions에 이 전환 타임라인을 명시.

## 대차대조표 - 저레버리지(net_debt/EBITDA≈0.67x)

FY2025말(2025-09-28) LongTermDebt $148.11억, 현금 $55.20억, 순부채
$92.91억. EBITDA(OPINC+D&A) $139.57억.

## 실행: python3 scripts/analyze_qcom_2026_09_04.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.filing_dates import pit_inputs_for
from engine.pipeline import AnalysisInputs, run_analysis, save_ledger
from engine.provenance import provenance_from_sec_facts

TICKER = "QCOM"
UA = "IRS Research chlalsrl1203@gmail.com"
TODAY = "2026-09-04"

# ── SEC XBRL companyfacts 실측(2026-09-04 조회, CIK 0000804328) ──────────
# 회계연도는 9월말 결산(FY2025 = 2024-09~2025-09), FY2026 아직 미제출
REVENUE = {
    2015: 25281000000.0, 2016: 23554000000.0, 2017: 22291000000.0, 2018: 22732000000.0,
    2019: 24273000000.0, 2020: 23531000000.0, 2021: 33566000000.0, 2022: 44200000000.0,
    2023: 35820000000.0, 2024: 38962000000.0, 2025: 44284000000.0,
}
OPERATING_INCOME = {
    2015: 5776000000.0, 2016: 6495000000.0, 2017: 2614000000.0, 2018: 742000000.0,
    2019: 7667000000.0, 2020: 6255000000.0, 2021: 9789000000.0, 2022: 15860000000.0,
    2023: 7788000000.0, 2024: 10071000000.0, 2025: 12355000000.0,
}
OPERATING_CASHFLOW = {
    2015: 5506000000.0, 2016: 7400000000.0, 2017: 4693000000.0, 2018: 3895000000.0,
    2019: 7286000000.0, 2020: 5814000000.0, 2021: 10536000000.0, 2022: 9096000000.0,
    2023: 11299000000.0, 2024: 12202000000.0, 2025: 14012000000.0,
}
CAPEX = {
    2015: 994000000.0, 2016: 539000000.0, 2017: 690000000.0, 2018: 784000000.0,
    2019: 887000000.0, 2020: 1407000000.0, 2021: 1888000000.0, 2022: 2262000000.0,
    2023: 1450000000.0, 2024: 1041000000.0, 2025: 1192000000.0,
}
NET_INCOME = {  # 참고 기록만 - is_insurer 아니므로 계산에 미사용
    2015: 5271000000.0, 2016: 5705000000.0, 2017: 2466000000.0, 2018: -4864000000.0,
    2019: 4386000000.0, 2020: 5198000000.0, 2021: 9043000000.0, 2022: 12936000000.0,
    2023: 7232000000.0, 2024: 10142000000.0, 2025: 5541000000.0,
}
SBC = {
    2015: 1026000000.0, 2016: 943000000.0, 2017: 914000000.0, 2018: 883000000.0,
    2019: 1037000000.0, 2020: 1212000000.0, 2021: 1663000000.0, 2022: 2031000000.0,
    2023: 2484000000.0, 2024: 2648000000.0, 2025: 2783000000.0,
}

# ── 대차대조표(FY2025말, 2025-09-28) ──────────────────────────────────────
DEBT_2025 = 14811000000.0  # LongTermDebtNoncurrent(Current=0)
CASH_2025 = 5520000000.0   # CashAndCashEquivalentsAtCarryingValue
NET_DEBT = DEBT_2025 - CASH_2025  # $9,291,000,000

DA_2025 = 1602000000.0  # DepreciationDepletionAndAmortization(FY2025)
EBITDA = OPERATING_INCOME[2025] + DA_2025  # $13,957,000,000

# ── 시가총액(2026-09-03 Alpha Vantage 종가 + 최신 EntityCommonStockShares) ─
PRICE = 168.57  # Alpha Vantage GLOBAL_QUOTE, 2026-09-03 종가(latestDay)
SHARES_OUT = 1050000000.0  # EntityCommonStockSharesOutstanding, 2026-07-27 기준(10-Q)
MARKET_CAP = PRICE * SHARES_OUT  # 약 $177.0B

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
        company_name="Qualcomm Incorporated",
        revenue_by_year=REVENUE,
        operating_income_by_year=OPERATING_INCOME,
        operating_cashflow_by_year=OPERATING_CASHFLOW,
        capex_by_year=CAPEX,
        market_cap=MARKET_CAP,
        net_debt=NET_DEBT,
        ebitda=EBITDA,
        risk_free_rate=RF,
        competitor_threat_weights=[0.15, 0.10, 0.08],
        market_share_trend_pp_per_year=-0.5,
        active_antitrust_or_regulatory_case=False,
        demand_sensitivity_pct=0.35,
        subjective_input_basis=(
            "competitor_threat_weights=[0.15(Apple 자체 모뎀 - 2027년까지 "
            "완전대체 목표, 연 $57~78억 규모 매출이 구조적으로 소멸 예정, "
            "2026-09-04 WebSearch 확인), 0.10(MediaTek - 중저가 스마트폰 "
            "칩셋 경쟁자), 0.08(자동차/데이터센터AI 신흥경쟁 - Nvidia·"
            "Mobileye 등)]. market_share_trend_pp_per_year=-0.5 - Apple "
            "모뎀손실이 실측 확정적 리스크(다음 분기 Apple매출 -50% 회사 "
            "직접 명시)라 음수로 반영. demand_sensitivity_pct=0.35 - "
            "스마트폰 핵심부품은 소비자 교체주기에 연동돼 경기민감도가 "
            "있으나(CLAUDE.md 앵커표 '스마트폰부품' 계열), 자동차·산업용 "
            "다각화가 진행 중이라 순수 소비자 재량소비보다는 낮게 채택."
        ),
        model_used="two_stage",
        model_choice_reason=(
            "trailing 매출 CAGR이 3y(0.06%, 2022 사이클정점 기준)~5y(13.48%, "
            "2020 저점기준)로 창에 따라 크게 갈리는 반도체 사이클 특성상, "
            "단일수렴(single_stage)보다 다년에 걸친 사업믹스 전환(Apple "
            "모뎀손실→자동차/데이터센터AI 대체)을 반영하는 two_stage가 "
            "적절하다고 판단. 3y 가중치(0.5)가 사이클정점 기준값을 자연히 "
            "눌러 가중평균(~5.23%)이 극단값으로 흐르지 않는다."
        ),
        falsification_conditions=(
            "FY2027(2026-10~2027-09) 실적에서 비핸드셋 QCT매출 성장률이 "
            "회사 목표(+60%YoY)에 크게 미달하거나, Apple 모뎀매출 감소폭이 "
            "가이던스(-50%)보다 더 가파르게 진행되는데도 자동차·데이터센터"
            "매출이 이를 상쇄하지 못하면 이 판정을 재검토할 것."
        ),
        price_at_analysis=PRICE,
        currency="USD",
        net_income_by_year=NET_INCOME,
        sbc_by_year=SBC,
        data_sources=[
            "SEC XBRL companyfacts (CIK 0000804328, 조회 2026-09-04)",
            "Alpha Vantage GLOBAL_QUOTE (2026-09-03 종가 $168.57)",
            "WebSearch: Apple 모뎀사업 손실 타임라인, 자동차/데이터센터AI "
            "다각화 목표·트랙션(2026-09-04 재인용)",
        ],
        **pit,
        provenance=provenance,
    )


if __name__ == "__main__":
    inputs = build_inputs()
    result = run_analysis(inputs)
    path = save_ledger(result)
    print(f"saved: {path}")
