"""
Paylocity Holding Corp(PCTY) 정식 분석 - 2026-09-03.

경위: 연구 우선순위 큐(스크리너 tier A, Gap 추정 +16.28%p, 시총 근사
~$6.60B). FRAMEWORK_MISMATCH 9종목(LNTH/EQT/CDE/CHDN/VICI/COP/DINO/EOG/
COF) 제외 뒤 큐 순서상 다음 후보.

## 원자료 - SEC XBRL companyfacts(1차자료, `SecCompanyFactsProvider`,
2026-09-03 조회, CIK 0001591698, 2012~2026 15개년 확보 - 10y CAGR 산출
가능, FYE 6월말).

## 발견 - 성숙화 국면의 깨끗한 다년 감속 패턴(M&A 왜곡 없음)

YoY: 2013~2016 40%대 고성장 -> 2017~2020 20%대 -> 2021 +15.7%(COVID
헤드카운트 영향 추정) -> 2022 +34.2%(반등) -> 2023~2026 29.5%->16.7%->
14.8%->12.2% 완만한 감속. 단일연도 단계상승 없이 유기적 성장곡선 -
2024년 Airbase 인수($325M, 재무·지출관리 스위트 추가)는 매출 $1.65B
대비 소규모 볼트온이라 CAGR 왜곡이 미미하다고 판단했다.

## 경쟁구도(2026-09-03 WebSearch) - HCM/급여관리 SaaS 업종

ADP(업계 압도적 1위, Paylocity가 "ADP의 최대 도전자"로 평가됨) > Rippling
(비상장, ~78% 초고성장의 신흥 플랫폼 경쟁자, private valuation ~17x
매출) > Paycom(3위권). 회사 자체 가이던스는 성장 둔화를 시사(Q2 2026
+11%YoY -> 다음 분기 가이던스 +8.3%YoY).

## 실행: python3 scripts/analyze_pcty_2026_09_03.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.filing_dates import pit_inputs_for
from engine.pipeline import AnalysisInputs, run_analysis, save_ledger
from engine.provenance import provenance_from_sec_facts

TICKER = "PCTY"
UA = "IRS Research chlalsrl1203@gmail.com"
TODAY = "2026-09-03"

# ── SEC XBRL companyfacts 실측(2026-09-03 조회, FYE 6월말) ───────────────
REVENUE = {
    2016: 230701000.0, 2017: 300010000.0, 2018: 368434000.0,
    2019: 447752000.0, 2020: 546212000.0, 2021: 631725000.0,
    2022: 847694000.0, 2023: 1098036000.0, 2024: 1281680000.0,
    2025: 1471801000.0, 2026: 1651362000.0,
}
OPERATING_INCOME = {
    2016: -3550000.0, 2017: 7296000.0, 2018: 15949000.0,
    2019: 56224000.0, 2020: 66171000.0, 2021: 58043000.0,
    2022: 84594000.0, 2023: 155026000.0, 2024: 260093000.0,
    2025: 304024000.0, 2026: 385993000.0,
}
OPERATING_CASHFLOW = {
    2016: 32993000.0, 2017: 61980000.0, 2018: 97866000.0,
    2019: 115032000.0, 2020: 112655000.0, 2021: 124850000.0,
    2022: 155053000.0, 2023: 282723000.0, 2024: 384670000.0,
    2025: 418226000.0, 2026: 533252000.0,
}
CAPEX = {
    2016: 16083000.0, 2017: 21338000.0, 2018: 21676000.0,
    2019: 11280000.0, 2020: 16578000.0, 2021: 9461000.0,
    2022: 18069000.0, 2023: 21910000.0, 2024: 18028000.0,
    2025: 13073000.0, 2026: 36152000.0,
}
NET_INCOME = {
    2016: -3851000.0, 2017: 6718000.0, 2018: 38598000.0,
    2019: 53823000.0, 2020: 64455000.0, 2021: 70819000.0,
    2022: 90777000.0, 2023: 140822000.0, 2024: 206766000.0,
    2025: 227127000.0, 2026: 269741000.0,
}
SBC = {
    2016: 17563000.0, 2017: 26734000.0, 2018: 30354000.0,
    2019: 38765000.0, 2020: 47493000.0, 2021: 63052000.0,
    2022: 96202000.0, 2023: 147300000.0, 2024: 146032000.0,
    2025: 142820000.0, 2026: 138657000.0,
}

# ── 대차대조표(FY2026말, 2026-06-30, SEC XBRL 실측) ──────────────────────
CASH_2026 = 271917000.0   # CashAndCashEquivalentsAtCarryingValue
DEBT_2026 = 0.0             # LongTermDebtNoncurrent/Current 둘 다 FY2014 이후 미보고(무차입)
NET_DEBT = DEBT_2026 - CASH_2026  # -271,917,000(순현금)

DA_2026 = 19970000.0 + 21331000.0  # Depreciation + AmortizationOfIntangibleAssets
EBITDA = OPERATING_INCOME[2026] + DA_2026

# ── 시가총액(2026-09-02, Alpha Vantage 종가 + 10-K 표지 발행주식수) ──────
PRICE = 154.60  # Alpha Vantage GLOBAL_QUOTE, 2026-09-02 종가(latestDay)
SHARES_OUT = 53056963.0  # FY2026 10-K 표지 dei:EntityCommonStockSharesOutstanding(2026-07-29)
MARKET_CAP = PRICE * SHARES_OUT  # 약 $8.20B

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
        company_name="Paylocity Holding Corp",
        revenue_by_year=REVENUE,
        operating_income_by_year=OPERATING_INCOME,
        operating_cashflow_by_year=OPERATING_CASHFLOW,
        capex_by_year=CAPEX,
        market_cap=MARKET_CAP,
        net_debt=NET_DEBT,
        ebitda=EBITDA,
        risk_free_rate=RF,
        competitor_threat_weights=[0.30, 0.15],
        market_share_trend_pp_per_year=0.3,
        active_antitrust_or_regulatory_case=False,
        demand_sensitivity_pct=0.20,
        subjective_input_basis=(
            "competitor_threat_weights=[0.30(ADP), 0.15(Rippling)] - ADP가 "
            "업계 압도적 1위 규모의 위협이나 Paylocity가 'ADP의 최대 도전자'로 "
            "평가되며 꾸준히 점유율을 확보 중이라 최대값 대비 다소 낮게 반영. "
            "Rippling은 비상장 초고성장(~78%YoY) 신흥 플랫폼으로 아직 규모는 "
            "작으나 성장속도가 위협적이라 별도 반영. market_share_trend_pp_"
            "per_year=+0.3 - Paylocity가 ADP 대비 꾸준히 도전자 지위를 강화해온 "
            "궤적을 반영하되 Rippling발 경쟁강도 증가를 감안해 완만하게만 "
            "반영(2026-09-03 WebSearch). demand_sensitivity_pct=0.20 - "
            "CLAUDE.md 업종앵커표 '기업용 필수 SW·전문서비스(계약기반, 전환비용 "
            "높음)' 버킷 적용 - 급여처리는 경기와 무관하게 필수적이나 신규고객 "
            "획득 속도는 경기에 다소 영향받음."
        ),
        model_used="two_stage",
        model_choice_reason=(
            "trailing 매출 CAGR(3y 14.57%/5y 21.19%/10y 21.75%)이 "
            "default_terminal_growth(2.0~4.5%)보다 여전히 높고, 회사 자체 "
            "가이던스도 성장둔화를 시사(Q2 2026 +11%YoY -> 다음분기 가이던스 "
            "+8.3%YoY)해 다년 수렴 경로(two_stage)가 적절하다고 판단."
        ),
        falsification_conditions=(
            "다음 분기 매출성장률이 가이던스(+8.3%YoY)를 크게 밑돌거나, "
            "Rippling 등 신흥 경쟁자로의 고객 이탈이 구체적으로 보고되거나, "
            "ADP 대비 순증고객수 증가율이 둔화되면 이 판정을 재검토할 것."
        ),
        price_at_analysis=PRICE,
        currency="USD",
        net_income_by_year=NET_INCOME,
        sbc_by_year=SBC,
        data_sources=[
            "SEC XBRL companyfacts (CIK 0001591698, 조회 2026-09-03)",
            "Alpha Vantage GLOBAL_QUOTE (2026-09-02 종가 $154.60)",
            "WebSearch: PCTY Q2 2026 실적발표·HCM 경쟁구도(ADP/Rippling/Paycom, "
            "2026-09-03 재인용)",
        ],
        **pit,
        provenance=provenance,
    )


if __name__ == "__main__":
    inputs = build_inputs()
    result = run_analysis(inputs)
    path = save_ledger(result)
    print(f"saved: {path}")
