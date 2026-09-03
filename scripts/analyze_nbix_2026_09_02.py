"""
Neurocrine Biosciences, Inc.(NBIX) 정식 분석 - 2026-09-02.

경위: 연구 우선순위 큐(스크리너 tier A, Gap 추정 +17.16%p, 시총 근사
~$9.52B). LNTH/EQT/CDE/CHDN/VICI/COP/DINO/EOG를 FRAMEWORK_MISMATCH로
제외한 뒤 큐 순서상 다음 후보(제외 사유가 없는 첫 종목).

## 원자료 - SEC XBRL companyfacts(1차자료, `SecCompanyFactsProvider`,
2026-09-02 조회, CIK 0000914475, 상용화 이전 연도(2009~2017)는 임상단계
바이오텍 특유의 적자·매출 미미 구간이나, 5y/3y CAGR 창(2020~2025)은
전부 흑자·FCF플러스 구간이라 v3.19 가드에 걸리지 않는다.

## 발견 - 스크리너 근사치가 시가총액을 약 40% 과소평가했다

시가총액 근사(~$9.52B)는 스크리너 `EntityPublicFloat` 스냅샷 기반인데,
Alpha Vantage 대체 실측(WebSearch, 2026-09-02 종가 $154.03) x 10-K 표지
발행주식수(100,363,463주, 2026-02-04)로 계산한 실시간 시총(~$15.46B)이
1.6배 크다 - OKTA/MEDP와 같은 계열의 float 스냅샷 노후화.

## 경쟁구도(2026-09-02 WebSearch) - Ingrezza(VMAT2 억제제, 지연성운동장애·
헌팅턴무도병) 대 Teva Austedo

Ingrezza가 지연성운동장애(TD) 시장에서 **53~55% 점유율**을 유지 중 -
Teva가 Austedo 가격을 38% 인하하며 경쟁을 강화했음에도 Neurocrine의
실사용데이터(real-world evidence)가 Ingrezza의 치료지속률이 Austedo XR
대비 높음을 보여줘 점유율 방어에 성공했다(BMO Capital은 이 "상대적으로
낮은 할인폭"을 Neurocrine에 긍정적으로 해석). 신제품 Crenessity(선천성
부신과다형성증 CAH 치료제)가 2026년 상반기 매출 $337M(+400%YoY)로 급성장,
회사는 2026년 Ingrezza 가이던스를 $2.825~2.875B(중간값 기준 +13%YoY)로
상향했다. 파이프라인 리스크: valbenazine의 신경발달장애 적응증 Phase III
실패(기존 Ingrezza 매출과는 무관, 향후 파이프라인 확장성에는 부정적).

## 실행: python3 scripts/analyze_nbix_2026_09_02.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.filing_dates import pit_inputs_for
from engine.pipeline import AnalysisInputs, run_analysis, save_ledger
from engine.provenance import provenance_from_sec_facts

TICKER = "NBIX"
UA = "IRS Research chlalsrl1203@gmail.com"
TODAY = "2026-09-02"

# ── SEC XBRL companyfacts 실측(2026-09-02 조회) ──────────────────────────
REVENUE = {
    2016: 15000000.0, 2017: 161626000.0, 2018: 451240000.0,
    2019: 788087000.0, 2020: 1045900000.0, 2021: 1133500000.0,
    2022: 1488700000.0, 2023: 1887100000.0, 2024: 2355300000.0,
    2025: 2860500000.0,
}
OPERATING_INCOME = {
    2016: -147372000.0, 2017: -131361000.0, 2018: 36895000.0,
    2019: 72283000.0, 2020: 163000000.0, 2021: 102500000.0,
    2022: 249000000.0, 2023: 250900000.0, 2024: 570500000.0,
    2025: 619100000.0,
}
OPERATING_CASHFLOW = {
    2016: -106181000.0, 2017: -94331000.0, 2018: 101364000.0,
    2019: 152054000.0, 2020: 228500000.0, 2021: 256500000.0,
    2022: 339400000.0, 2023: 389900000.0, 2024: 595400000.0,
    2025: 782700000.0,
}
CAPEX = {
    2016: 4108000.0, 2017: 6940000.0, 2018: 24812000.0,
    2019: 14748000.0, 2020: 10900000.0, 2021: 23400000.0,
    2022: 16500000.0, 2023: 28300000.0, 2024: 38200000.0,
    2025: 34000000.0,
}
NET_INCOME = {
    2016: -141090000.0, 2017: -142542000.0, 2018: 21111000.0,
    2019: 37012000.0, 2020: 407300000.0, 2021: 89600000.0,
    2022: 154500000.0, 2023: 249700000.0, 2024: 341300000.0,
    2025: 478600000.0,
}
SBC = {
    2016: 28464000.0, 2017: 42522000.0, 2018: 58068000.0,
    2019: 75262000.0, 2020: 100000000.0, 2021: 134200000.0,
    2022: 173100000.0, 2023: 194300000.0, 2024: 195500000.0,
    2025: 217900000.0,
}

# ── 대차대조표(FY2025말, 2025-12-31, SEC XBRL 실측) ──────────────────────
CASH_2025 = 713000000.0   # CashAndCashEquivalentsAtCarryingValue
DEBT_2025 = 0.0            # ConvertibleDebtNoncurrent - FY2022 이후 0(전액 상환/전환)
NET_DEBT = DEBT_2025 - CASH_2025  # -713,000,000(순현금)

DA_2025 = 26000000.0 + 4100000.0  # Depreciation + AmortizationOfIntangibleAssets
EBITDA = OPERATING_INCOME[2025] + DA_2025

# ── 시가총액(2026-09-02) - Alpha Vantage 한도초과로 WebSearch 대체확보 ────
PRICE = 154.03  # WebSearch(investing.com 재인용, 2026-09-02)
SHARES_OUT = 100363463.0  # FY2025 10-K 표지 dei:EntityCommonStockSharesOutstanding(2026-02-04)
MARKET_CAP = PRICE * SHARES_OUT  # 약 $15.46B

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
        company_name="Neurocrine Biosciences, Inc.",
        revenue_by_year=REVENUE,
        operating_income_by_year=OPERATING_INCOME,
        operating_cashflow_by_year=OPERATING_CASHFLOW,
        capex_by_year=CAPEX,
        market_cap=MARKET_CAP,
        net_debt=NET_DEBT,
        ebitda=EBITDA,
        risk_free_rate=RF,
        competitor_threat_weights=[0.20, 0.08],
        market_share_trend_pp_per_year=0.0,
        active_antitrust_or_regulatory_case=False,
        demand_sensitivity_pct=0.12,
        subjective_input_basis=(
            "competitor_threat_weights=[0.20(Teva Austedo), 0.08(기타 VMAT2/전문의약품)] "
            "- Teva가 Austedo 가격을 38% 인하하며 경쟁을 강화했으나 Ingrezza가 "
            "지연성운동장애 시장 53~55% 점유율을 실사용데이터(치료지속률 우위)로 "
            "방어 중이라 가격경쟁 대비 낮게 반영. market_share_trend_pp_per_year="
            "0.0 - Teva 가격인하 공세와 Neurocrine의 실사용데이터 방어가 상쇄돼 "
            "순추세는 평평(2026-09-02 WebSearch, BMO Capital 등 '상대적으로 낮은 "
            "할인폭이 긍정적'이라는 평가 근거). demand_sensitivity_pct=0.12 - "
            "CLAUDE.md 업종앵커표 '헬스케어·필수소비재 반복매출' 버킷(IDXX·ZTS·"
            "MNST·RMD, 앵커 0.12) 적용 - 지연성운동장애·CAH 모두 만성질환 필수 "
            "치료제라 경기민감도가 낮음."
        ),
        model_used="two_stage",
        model_choice_reason=(
            "trailing 매출 CAGR(3y 14.87%/5y 22.29%)이 default_terminal_growth"
            "(2.0~4.5%)보다 여전히 높고, Ingrezza 성숙화(2026 가이던스 중간값 "
            "+13%YoY로 trailing 대비 둔화)와 Crenessity 신규 급성장(+400%YoY)이 "
            "상쇄되는 과도기라 다년 수렴 경로(two_stage)가 적절하다고 판단."
        ),
        falsification_conditions=(
            "다음 분기 Ingrezza 매출이 가이던스 하단($2.825B)을 밑돌거나 "
            "Teva Austedo 대비 시장점유율이 뚜렷이 하락하면(현재 53~55% "
            "유지), 또는 Crenessity 성장률이 급격히 둔화되면 이 판정을 "
            "재검토할 것. valbenazine 신경발달장애 Phase III 실패는 기존 "
            "매출과 무관하나 파이프라인 확장성 리스크로 감안할 것."
        ),
        price_at_analysis=PRICE,
        currency="USD",
        net_income_by_year=NET_INCOME,
        sbc_by_year=SBC,
        data_sources=[
            "SEC XBRL companyfacts (CIK 0000914475, 조회 2026-09-02)",
            "WebSearch: NBIX 주가(investing.com 재인용, 2026-09-02), "
            "Ingrezza/Crenessity 2026 실적·경쟁구도(Fierce Pharma/Seeking Alpha 등)",
        ],
        **pit,
        provenance=provenance,
    )


if __name__ == "__main__":
    inputs = build_inputs()
    result = run_analysis(inputs)
    path = save_ledger(result)
    print(f"saved: {path}")
