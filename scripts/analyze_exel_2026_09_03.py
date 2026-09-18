"""
Exelixis, Inc.(EXEL) 정식 분석 - 2026-09-03.

경위: 연구 우선순위 큐(스크리너 tier A, Gap 추정 +15.24%p, 시총 근사
~$9.40B). FRAMEWORK_MISMATCH 9종목 제외 뒤 큐 순서상 다음 후보.

## ⚠️ 원자료 함정 - 52/53주 회계연도 라벨 충돌을 수동으로 해소했다

`SecCompanyFactsProvider`의 자동 추출 결과가 2019·2024년 매출을 통째로
누락시키고(2018->2020으로 건너뜀, 2023->2025로 건너뜀) 2020/2021년 값을
서로 바꿔치기했다(v3.61이 CDNS/GEN에서 발견한 "회계연도 라벨이 한 해
밀림" 패턴의 세 번째 실사례, 이번엔 결측까지 겹친 더 심한 경우). 원인:
Exelixis가 52/53주 회계연도를 쓰는데, 자동 추출이 `end` 날짜의 달력연도로
회계연도를 추정해 회사 자신의 `fy` 필드(SEC가 10-K 제출 시 회사가 직접
붙이는 회계연도 라벨)와 어긋났다.

**SEC XBRL의 `fy` 필드를 직접 사용해 12개월 단위(355~375일) 항목만
수동으로 재구성**했다(2026-09-03, `us-gaap:Revenues`/
`RevenueFromContractWithCustomerExcludingAssessedTax`/`OperatingIncomeLoss`/
`NetCashProvidedByUsedInOperatingActivities`/`PaymentsToAcquireProperty
PlantAndEquipment`/`NetIncomeLoss`/`AllocatedShareBasedCompensationExpense`,
매 회계연도의 최신 제출분만 채택). 이렇게 재구성한 FY2021 매출은
$1,434,970,000으로, 자동추출이 잘못 부여했던 $987,538,000(실은 FY2020 값)
과 크게 다르다 - 재구성 없이 그대로 썼다면 성장률이 심각하게 왜곡됐을
것이다.

## 발견 - 콜라보레이션 매출의 분기별 변동성으로 YoY가 들쭉날쭉(M&A 아님)

YoY: 2019 +13.3%, 2020 +2.0%, 2021 +45.3%(Ipsen/Takeda 로열티·마일스톤
변동 추정), 2022~2025 12~19%대로 안정화. 3y(2022->2025)/5y(2020->2025)
CAGR 창은 이 변동을 부분적으로만 포함해 심각하게 왜곡되지는 않는다고
판단했다.

## 경쟁구도(2026-09-03 WebSearch) - 신장세포암(RCC) 표적/면역항암제 업종

Cabometyx(카보잔티닙) 프랜차이즈가 핵심 매출원, Merck의 Keytruda 기반
병용요법이 최대 경쟁위협(다만 Exelixis 자체 평가로는 병용요법의 독성·
40%대 조기중단율로 "practice-changing은 아님"). 파이프라인 후보
zanzalintinib이 "$5B 기회"로 평가되며 대장암 적응증 2026-12 PDUFA 심사
예정 - 아직 승인 전이라 상당한 규제 리스크가 남아있음. 회사 자체
2026 매출가이던스 중간값 ~$2.4B(전년 대비 완만한 성장)로 trailing
CAGR(13~19%대)보다 낮아 성장둔화를 시사.

## 실행: python3 scripts/analyze_exel_2026_09_03.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.filing_dates import pit_inputs_for
from engine.pipeline import AnalysisInputs, run_analysis, save_ledger
from engine.provenance import provenance_from_sec_facts

TICKER = "EXEL"
UA = "IRS Research chlalsrl1203@gmail.com"
TODAY = "2026-09-03"

# ── 수동 재구성(SEC XBRL `fy` 필드 기준, 2026-09-03) ─────────────────────
REVENUE = {
    2016: 191454000.0, 2017: 452477000.0, 2018: 853826000.0,
    2019: 967775000.0, 2020: 987538000.0, 2021: 1434970000.0,
    2022: 1611062000.0, 2023: 1830208000.0, 2024: 2168701000.0,
    2025: 2320126000.0,
}
OPERATING_INCOME = {
    2016: -28124000.0, 2017: 165910000.0, 2018: 438855000.0,
    2019: 369470000.0, 2020: 110060000.0, 2021: 286666000.0,
    2022: 201484000.0, 2023: 170885000.0, 2024: 604617000.0,
    2025: 872191000.0,
}
OPERATING_CASHFLOW = {
    2016: 206296000.0, 2017: 165611000.0, 2018: 415720000.0,
    2019: 526956000.0, 2020: 208982000.0, 2021: 400804000.0,
    2022: 362614000.0, 2023: 333324000.0, 2024: 699971000.0,
    2025: 884267000.0,
}
CAPEX = {
    2016: 1703000.0, 2017: 21143000.0, 2018: 33297000.0,
    2019: 12834000.0, 2020: 30345000.0, 2021: 64225000.0,
    2022: 27706000.0, 2023: 40469000.0, 2024: 28435000.0,
    2025: 8429000.0,
}
NET_INCOME = {
    2016: -70222000.0, 2017: 154227000.0, 2018: 690070000.0,
    2019: 321012000.0, 2020: 111781000.0, 2021: 231063000.0,
    2022: 182282000.0, 2023: 207765000.0, 2024: 521267000.0,
    2025: 782570000.0,
}
SBC = {
    2016: 22912000.0, 2017: 23938000.0, 2018: 40626000.0,
    2019: 56602000.0, 2020: 105070000.0, 2021: 119820000.0,
    2022: 107574000.0, 2023: 106345000.0, 2024: 93836000.0,
    2025: 112983000.0,
}

# ── 대차대조표(FY2025말, 2026-01-02, SEC XBRL 실측) ──────────────────────
CASH_2025 = 482488000.0    # CashAndCashEquivalentsAtCarryingValue
DEBT_2025 = 0.0              # LongTermDebtNoncurrent/Current 둘 다 FY2016 이후 미보고(무차입)
NET_DEBT = DEBT_2025 - CASH_2025  # -482,488,000(순현금)

DA_2025 = 29055000.0  # DepreciationDepletionAndAmortization(통합 태그)
EBITDA = OPERATING_INCOME[2025] + DA_2025

# ── 시가총액(2026-09-02, Alpha Vantage 종가 + 10-K 표지 발행주식수) ──────
PRICE = 58.53  # Alpha Vantage GLOBAL_QUOTE, 2026-09-02 종가(latestDay)
SHARES_OUT = 259708689.0  # FY2025 10-K 표지 dei:EntityCommonStockSharesOutstanding(2026-02-02)
MARKET_CAP = PRICE * SHARES_OUT  # 약 $15.20B

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
        company_name="Exelixis, Inc.",
        revenue_by_year=REVENUE,
        operating_income_by_year=OPERATING_INCOME,
        operating_cashflow_by_year=OPERATING_CASHFLOW,
        capex_by_year=CAPEX,
        market_cap=MARKET_CAP,
        net_debt=NET_DEBT,
        ebitda=EBITDA,
        risk_free_rate=RF,
        competitor_threat_weights=[0.25, 0.12],
        market_share_trend_pp_per_year=0.0,
        active_antitrust_or_regulatory_case=False,
        demand_sensitivity_pct=0.12,
        subjective_input_basis=(
            "competitor_threat_weights=[0.25(Merck Keytruda 기반 병용요법), "
            "0.12(기타 TKI/IO 병용경쟁)] - Merck가 신장세포암 시장 최대 "
            "위협이나 Exelixis 자체 평가로는 병용요법의 독성·40%대 조기중단율로 "
            "'practice-changing은 아님'이라 최대치 대비 낮게 반영. "
            "market_share_trend_pp_per_year=0.0 - RCC 치료시장이 '매우 경쟁적이고 "
            "빠르게 변화 중'이라는 서술과 Exelixis의 방어논리가 상쇄돼 평평하게 "
            "반영(2026-09-03 WebSearch). demand_sensitivity_pct=0.12 - "
            "CLAUDE.md 업종앵커표 '헬스케어·필수소비재 반복매출' 버킷(IDXX·ZTS·"
            "MNST·RMD·NBIX, 앵커 0.12) 적용 - 항암치료제는 경기와 무관한 필수 "
            "치료."
        ),
        model_used="two_stage",
        model_choice_reason=(
            "trailing 매출 CAGR(3y 12.93%/5y 18.63%)이 default_terminal_growth"
            "(2.0~4.5%)보다 여전히 높고, 회사 자체 2026 가이던스(중간값 ~$2.4B, "
            "trailing 대비 완만한 성장)가 성장둔화를 시사해 다년 수렴 경로"
            "(two_stage)가 적절하다고 판단."
        ),
        falsification_conditions=(
            "다음 분기 Cabometyx 매출성장률이 가이던스를 크게 밑돌거나, "
            "zanzalintinib의 대장암 적응증 승인(2026-12 PDUFA 예정)이 거부되거나, "
            "Merck 등 경쟁 병용요법이 실제로 임상 우위를 입증해 처방 전환이 "
            "발생하면 이 판정을 재검토할 것."
        ),
        price_at_analysis=PRICE,
        currency="USD",
        net_income_by_year=NET_INCOME,
        sbc_by_year=SBC,
        data_sources=[
            "SEC XBRL companyfacts (CIK 0000939767, 조회 2026-09-03, "
            "52/53주 회계연도 라벨 충돌 수동 재구성)",
            "Alpha Vantage GLOBAL_QUOTE (2026-09-02 종가 $58.53)",
            "WebSearch: EXEL 2026 가이던스·zanzalintinib 파이프라인·RCC "
            "경쟁구도(2026-09-03 재인용)",
        ],
        **pit,
        provenance=provenance,
    )


if __name__ == "__main__":
    inputs = build_inputs()
    result = run_analysis(inputs)
    path = save_ledger(result)
    print(f"saved: {path}")
