"""
Chewy, Inc.(CHWY) 정식 분석 - 2026-09-04.

경위: 연구 우선순위 큐 tier A, 스크리너 Gap 추정 +7.44%p. FRAMEWORK_MISMATCH
20종목 + BYD·CRM·DECK·QCOM·EAT·ADBE·MMS 정식분석 + (HBAN/CNM/CVX/AXP/GLPI/
IBP/APTV/MLI/MKL/FCFS/ADI/DHI 배제) 뒤 큐 순서상 다음 후보. 반려동물용품
전문 이커머스.

## 원자료 - SEC XBRL companyfacts(CIK 0001766502, 2026-09-04 조회,
FY2018~FY2026 9개년 확보 - FY2016/2017은 상장 전이라 태그 없음).

## ⚠️ FCF 5년창 기준연도(2021)가 거의 0에 수렴 - PATH(같은 세션)와 동일한
근사-0 기준연도 아티팩트, 결과에는 무영향

FCF(2021) = OCF $1.328억 - capex $1.307억 = **$201만**(거의 0). 이를
기준으로 5y FCF CAGR을 계산하면 FCF(2026) $5.624억까지의 CAGR이 약
208%라는 비현실적 수치가 나온다(PODD·ONON·MU와 같은 계열이나 원인은
각각 다름 - Chewy는 '적자에서 흑자전환 직전 해가 우연히 거의 0'인
경우). `realistic_growth_estimate()`의 min(매출가중CAGR, FCF CAGR) 로직이
이를 자동으로 버렸다(매출가중CAGR 9.83% 채택, FCF CAGR 미사용) - 보호가
우연적이라는 점까지 PATH 사례와 동일. 계산에는 영향 없음, 원자료 그대로
사용.

## 성장 - 흑자전환 이후 견조한 성장(3y 7.65%/5y 9.83%), 구독형 매출비중
확대가 실측 확인됨

2023년 최초 영업흑자($5,575만) 이후 2024년 일시적 재적자(-$2,363만) 거쳐
2025~2026년 안정적 흑자확대($1.126억→$2.543억). 2026-09-04 WebSearch
확인: Autoship(구독형 반복매출) 비중이 2018년 66.2%→현재 84.4%로 확대,
FCF $5.624억(+24%YoY) - 재무데이터와 정확히 일치(교차검증됨).

## ⚠️ 실시간 시총이 스크리너 근사치보다 24% 높음 - 이번 세션 세 번째
'값싼 원인'이 M&A/스트레스가 아닌 표준 사례

주가 -40%YTD로 2019년 상장가 밑으로 하락했으나(Amazon·Walmart 저가경쟁,
재량소비 압박, agentic AI가 광고사업을 위협할 수 있다는 우려), 실시간
시총(~$99.1억)은 스크리너 근사($80.0억)보다 오히려 24% 높다 - 근사치의
정확한 스냅샷 시점을 특정하기 어려워 원인은 불명확하나, 다른 종목들의
float 스냅샷 노후화 패턴과 방향이 다르다는 점만 기록해둔다.

## 경쟁구도(2026-09-04 WebSearch) - 반려동물 온라인 시장

美 반려동물 시장 규모 $1,520억(연 6% 성장, 2028년 $1,920억 전망). 온라인
반려동물 판매 점유율: Amazon 1위(~50%), **Chewy 2위(41%)**, Walmart
3위(33%) - 저가경쟁 압박이 실재하나 시장 자체가 성장 중이고 Chewy의
2위 지위는 견고. 수의사 클리닉·전문건강서비스로 사업다각화 진행 중.

## 실행: python3 scripts/analyze_chwy_2026_09_04.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.filing_dates import pit_inputs_for
from engine.pipeline import AnalysisInputs, run_analysis, save_ledger
from engine.provenance import provenance_from_sec_facts

TICKER = "CHWY"
UA = "IRS Research chlalsrl1203@gmail.com"
TODAY = "2026-09-04"

# ── SEC XBRL companyfacts 실측(2026-09-04 조회, CIK 0001766502) ──────────
# 회계연도는 1월말/2월초 결산(FY2026 = 2025-02~2026-02)
REVENUE = {
    2018: 2104287000.0, 2019: 3532837000.0, 2020: 4846743000.0, 2021: 7146264000.0,
    2022: 8890773000.0, 2023: 10098939000.0, 2024: 11147720000.0, 2025: 11861335000.0,
    2026: 12601500000.0,
}
OPERATING_INCOME = {
    2018: -337851000.0, 2019: -267766000.0, 2020: -252726000.0, 2021: -90464000.0,
    2022: -72178000.0, 2023: 55753000.0, 2024: -23625000.0, 2025: 112587000.0,
    2026: 254300000.0,
}
OPERATING_CASHFLOW = {
    2018: -79747000.0, 2019: -13415000.0, 2020: 46581000.0, 2021: 132755000.0,
    2022: 191739000.0, 2023: 349572000.0, 2024: 486211000.0, 2025: 596325000.0,
    2026: 691600000.0,
}
CAPEX = {
    2018: 40282000.0, 2019: 44160000.0, 2020: 48636000.0, 2021: 130743000.0,
    2022: 183186000.0, 2023: 230310000.0, 2024: 143282000.0, 2025: 143831000.0,
    2026: 129200000.0,
}
NET_INCOME = {  # 참고 기록만 - is_insurer 아니므로 계산에 미사용
    2018: -338057000.0, 2019: -267890000.0, 2020: -252370000.0, 2021: -92486000.0,
    2022: -73817000.0, 2023: 49232000.0, 2024: 39580000.0, 2025: 392738000.0,
    2026: 222800000.0,
}
SBC = {
    2018: 11209000.0, 2019: 14351000.0, 2020: 134926000.0, 2021: 121265000.0,
    2022: 77772000.0, 2023: 158122000.0, 2024: 239107000.0, 2025: 306435000.0,
    2026: 297900000.0,
}

# ── 대차대조표(FY2026말, 2026-02-01, 무차입) ──────────────────────────────
CASH_2026 = 860100000.0  # CashAndCashEquivalentsAtCarryingValue
NET_DEBT = 0.0 - CASH_2026  # -$860,100,000(순현금, LongTermDebt 태그 없음)

DA_2026 = 129300000.0  # DepreciationDepletionAndAmortization(FY2026)
EBITDA = OPERATING_INCOME[2026] + DA_2026  # $383,600,000

# ── 시가총액(2026-09-03 Alpha Vantage 종가 + 최신 가중평균 기본주식수) ──────
PRICE = 23.96  # Alpha Vantage GLOBAL_QUOTE, 2026-09-03 종가(latestDay)
SHARES_OUT = 413800000.0  # WeightedAverageNumberOfSharesOutstandingBasic, Q1 FY2027(2026-05-03 종료분기)
MARKET_CAP = PRICE * SHARES_OUT  # 약 $9.91B

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
        company_name="Chewy, Inc.",
        revenue_by_year=REVENUE,
        operating_income_by_year=OPERATING_INCOME,
        operating_cashflow_by_year=OPERATING_CASHFLOW,
        capex_by_year=CAPEX,
        market_cap=MARKET_CAP,
        net_debt=NET_DEBT,
        ebitda=EBITDA,
        risk_free_rate=RF,
        competitor_threat_weights=[0.20, 0.12],
        market_share_trend_pp_per_year=-0.3,
        active_antitrust_or_regulatory_case=False,
        demand_sensitivity_pct=0.20,
        subjective_input_basis=(
            "competitor_threat_weights=[0.20(Amazon - 온라인 반려동물 "
            "시장 1위, 약 50% 점유, 저가경쟁 공세), 0.12(Walmart - 3위, "
            "33% 점유, 마찬가지로 저가경쟁)]. market_share_trend_pp_per_"
            "year=-0.3 - Amazon·Walmart의 저가경쟁 압박이 실측 확인돼 "
            "소폭 음수. demand_sensitivity_pct=0.20 - 반려동물용품(사료 등 "
            "필수소비재 비중 높음)은 CLAUDE.md 앵커표 '헬스케어·필수소비재 "
            "반복매출'(0.12)보다는 높으나 순수 재량소비('소비자 구독/"
            "플랫폼' 0.30)보다는 낮게 채택 - Autoship 구독비중 84.4%가 "
            "반복성을 뒷받침."
        ),
        model_used="two_stage",
        model_choice_reason=(
            "trailing 매출 CAGR(3y 7.65%/5y 9.83%)이 default_terminal_"
            "growth(2.0~4.5%)를 상회하고, 2023년 최초 흑자전환 이후 이익률"
            "확대가 지속되는 국면이라 다년 수렴 경로(two_stage)가 적절. "
            "FCF 5y창 기준연도(2021)가 근사-0이라 FCF CAGR이 비현실적으로 "
            "나오나(약 208%) min() 로직이 자동 배제해 최종 성장률에 영향"
            "없음(매출가중CAGR 9.83% 채택)."
        ),
        falsification_conditions=(
            "Amazon·Walmart의 저가경쟁으로 Autoship 구독자 순증이 둔화되거나"
            "(현재 84.4% 구독비중), 수의사클리닉 다각화 투자가 이익률 확대"
            "추세를 훼손하면 이 판정을 재검토할 것."
        ),
        price_at_analysis=PRICE,
        currency="USD",
        net_income_by_year=NET_INCOME,
        sbc_by_year=SBC,
        data_sources=[
            "SEC XBRL companyfacts (CIK 0001766502, 조회 2026-09-04)",
            "Alpha Vantage GLOBAL_QUOTE (2026-09-03 종가 $23.96)",
            "WebSearch: 반려동물 시장규모·경쟁구도(Amazon/Walmart 점유율), "
            "Autoship 비중 추이, FCF 성장(2026-09-04 재인용)",
        ],
        **pit,
        provenance=provenance,
    )


if __name__ == "__main__":
    inputs = build_inputs()
    result = run_analysis(inputs)
    path = save_ledger(result)
    print(f"saved: {path}")
