"""
RLI Corp(RLI) 정식 분석 - 2026-09-03.

경위: 연구 우선순위 큐(스크리너 tier S, Gap 추정 +12.66%p, 시총 근사
~$5.49B). FRAMEWORK_MISMATCH 15종목 + HLNE/FIVE/TW 정식분석 완료 뒤 큐
순서상 다음 후보. 특수(E&S)손해보험사 - `is_insurer=True` 경로(v3.22,
ACGL/PGR/BRO/SIGI 선례)를 그대로 따른다.

## 원자료 - SEC XBRL companyfacts(1차자료, `SecCompanyFactsProvider`,
2026-09-03 조회, CIK 0000084246, 2008~2025 18개년 확보). PGR/ACGL/SIGI
선례와 동일하게 `operating_income_by_year`에는 **세전이익(income before
income taxes)**을 대용한다(보험업은 별도 '영업이익' 라인이 없음).

## 데이터 확인 - SIGI형 Q4단독 오염 없음

`IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNon
ControllingInterest` 태그의 raw entries를 전수 확인한 결과 SIGI가 겪은
"Q4 단독 수치 혼입"이 RLI에는 없었다(모든 연도가 `start=1월1일` 정상
12개월 구간으로 일관) - SEC provider가 이 태그를 시도 목록에 안 넣어서만
[미확보]로 표시된 것이라 수동 보완했다.

## ⚠️ SBC 자료 - 2020년 이후 XBRL 미공시로 제외

`AllocatedShareBasedCompensationExpense` 태그가 2019년(FY2019, $4.5M)
이후 더 이상 보고되지 않는다(회사가 2020년부터 이 항목을 XBRL 개별
태그가 아닌 다른 방식으로 공시하는 것으로 추정 - WebSearch로도 최근
연도 정확한 수치를 확보하지 못했다). 추측으로 채우지 않고
`sbc_by_year`를 아예 생략했다(SBC 교차검증 없이 진행 - PGR/ACGL과
달리 이번엔 확보 실패를 정직하게 인정).

## 재무상태표 항목 - PGR/ACGL/SIGI 관행 그대로

보험업은 투자포트폴리오가 준비금과 짝이라 순부채 상쇄에서 제외한다.
`CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents` 태그
(투자포트폴리오 제외한 협의의 현금) 사용. 부채는 XBRL `LongTermDebt`
태그가 2023년 이후 갱신을 멈춰(회사가 태그를 바꾼 것으로 추정) 2차
WebSearch로 "PNC Bank·FHLB Chicago 차입금 합계 $100백만"을 재확인
(1차 WebSearch가 다른 보험사(추정 CIK 890926)의 수치를 잘못 인용해
$10.7억으로 나왔다가, RLI 고유 CIK 0000084246 원자료 및 2차 독립
WebSearch로 재검증해 $100백만이 옳음을 확정 - TYL SBC 3배 오류와
동일 계열의 "2차 출처 무검증 인용 위험", 채택 전에 잡아냄). D&A도
PGR/SIGI와 동일하게 고정자산 감가상각만(`Depreciation` 태그).

## 경쟁구도(2026-09-03 WebSearch) - 특수(E&S)손해보험 업종

RLI는 2025년 언더라이팅이익 $264.2M·합산비율 83.6%(**30년 연속
언더라이팅 흑자**), 2026 Q2 합산비율 85.6%로 여전히 업계 최상위권
규율(SIGI 98%대와 대비). 다만 **Arch Capital Group(ACGL)·Kinsale
Capital Group·W.R. Berkley 등 대형 자본력을 갖춘 경쟁자들이 E&S
특수시장으로 잠식 확대 중**이고, E&S 보험료율이 하락(허리케인 -19%/
지진 -16%)하며 재진입한 admitted carrier와의 경쟁도 심화. E&S 부동산
segment 보험료는 -6%(경쟁압력)인 반면 Casualty(+11%, 개인우산배상책임·
운송보험 주도)는 성장 중 - 세그먼트별로 방향이 갈린다.

## 실행: python3 scripts/analyze_rli_2026_09_03.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.filing_dates import pit_inputs_for
from engine.pipeline import AnalysisInputs, run_analysis, save_ledger
from engine.provenance import provenance_from_sec_facts

TICKER = "RLI"
UA = "IRS Research chlalsrl1203@gmail.com"
TODAY = "2026-09-03"

REVENUE = {
    2008: 561012000.0, 2009: 546552000.0, 2010: 583424000.0, 2011: 619169000.0,
    2012: 660774000.0, 2013: 705601000.0, 2014: 775165000.0, 2015: 794634000.0,
    2016: 816328000.0, 2017: 797224000.0, 2018: 818123000.0, 2019: 1003591000.0,
    2020: 983626000.0, 2021: 1179245000.0, 2022: 1697992000.0, 2023: 1511994000.0,
    2024: 1770384000.0, 2025: 1882448000.0,
}
# 세전이익(income before income taxes) - 보험업 영업이익 대용(PGR/ACGL/SIGI 선례).
OPERATING_INCOME = {
    2009: 132437000.0, 2010: 178490000.0, 2011: 189729000.0, 2012: 142732000.0,
    2013: 175666000.0, 2014: 189487000.0, 2015: 196682000.0, 2016: 157082000.0,
    2017: 84589000.0, 2018: 67581000.0, 2019: 232734000.0, 2020: 189841000.0,
    2021: 344321000.0, 2022: 720678000.0, 2023: 377265000.0, 2024: 427551000.0,
    2025: 505981000.0,
}
OPERATING_CASHFLOW = {
    2008: 161334000.0, 2009: 127759000.0, 2010: 100235000.0, 2011: 117991000.0,
    2012: 36240000.0, 2013: 134966000.0, 2014: 123085000.0, 2015: 152586000.0,
    2016: 174463000.0, 2017: 197525000.0, 2018: 217102000.0, 2019: 276917000.0,
    2020: 263259000.0, 2021: 384905000.0, 2022: 250448000.0, 2023: 464257000.0,
    2024: 560219000.0, 2025: 614221000.0,
}
CAPEX = {
    2008: 6002000.0, 2009: 11565000.0, 2010: 2841000.0, 2011: 5382000.0,
    2012: 18521000.0, 2013: 25407000.0, 2014: 7121000.0, 2015: 10035000.0,
    2016: 16155000.0, 2017: 9238000.0, 2018: 6087000.0, 2019: 6955000.0,
    2020: 5768000.0, 2021: 8310000.0, 2022: 5889000.0, 2023: 5913000.0,
    2024: 4710000.0, 2025: 5523000.0,
}
NET_INCOME = {
    2016: 114920000.0, 2017: 105028000.0, 2018: 64179000.0, 2019: 191642000.0,
    2020: 157091000.0, 2021: 279354000.0, 2022: 583411000.0, 2023: 304611000.0,
    2024: 345779000.0, 2025: 403337000.0,
}
SHAREHOLDERS_EQUITY = {
    2016: 823572000.0, 2017: 853598000.0, 2018: 806842000.0, 2019: 995388000.0,
    2020: 1135978000.0, 2021: 1229361000.0, 2022: 1177341000.0, 2023: 1413514000.0,
    2024: 1521967000.0, 2025: 1778196000.0,
}
DIVIDENDS_PAID = {
    2016: 122488000.0, 2017: 113813000.0, 2018: 83100000.0, 2019: 85591000.0,
    2020: 87906000.0, 2021: 135330000.0, 2022: 364848000.0, 2023: 140093000.0,
    2024: 235656000.0, 2025: 241562000.0,
}

# 재무상태표(FY2025, 2025-12-31 기준) - PGR/ACGL/SIGI와 동일 원칙(투자포트폴리오 제외)
CASH_2025 = 51565000.0   # CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents
DEBT_2025 = 100000000.0  # PNC Bank+FHLB Chicago 차입금 합계(WebSearch 2차 재확인)
NET_DEBT = DEBT_2025 - CASH_2025
DA_2025 = 8129000.0      # Depreciation(고정자산만, PGR/SIGI와 동일)
EBITDA = OPERATING_INCOME[2025] + DA_2025

PRICE = 63.35   # Alpha Vantage GLOBAL_QUOTE, 2026-09-02 종가(latestDay)
SHARES_OUT = 91772634.0  # 10-Q 표지(2026-06-30 기준)
MARKET_CAP = PRICE * SHARES_OUT  # 약 $5.81B

RF = 0.0475


def build_inputs() -> AnalysisInputs:
    pit = pit_inputs_for(TICKER, TODAY, list(REVENUE), user_agent=UA)
    provenance = None
    try:
        from engine.data.providers.sec import fetch_company_facts, ticker_to_cik

        cik = ticker_to_cik(TICKER, UA)
        facts = fetch_company_facts(cik, UA)
        provenance = provenance_from_sec_facts(facts, TICKER, TODAY, list(REVENUE))
    except Exception:  # noqa: BLE001
        provenance = None

    return AnalysisInputs(
        ticker=TICKER,
        company_name="RLI Corp",
        revenue_by_year=REVENUE,
        operating_income_by_year=OPERATING_INCOME,
        operating_cashflow_by_year=OPERATING_CASHFLOW,
        capex_by_year=CAPEX,
        market_cap=MARKET_CAP,
        net_debt=NET_DEBT,
        ebitda=EBITDA,
        risk_free_rate=RF,
        competitor_threat_weights=[0.20, 0.15],
        market_share_trend_pp_per_year=0.0,
        active_antitrust_or_regulatory_case=False,
        demand_sensitivity_pct=0.18,
        subjective_input_basis=(
            "competitor_threat_weights=[0.20(Arch Capital Group - 대형 "
            "자본력을 갖춘 E&S 특수시장 잠식 경쟁자, RLI 자체가 2026-09 "
            "실적발표에서 명시적으로 지목), 0.15(Kinsale Capital Group - "
            "빠르게 성장 중인 순수 E&S 전문사)]. market_share_trend_pp_"
            "per_year=0.0 - 세그먼트별로 방향이 엇갈린다(전체 보험료 "
            "+3%·Casualty +11% 성장 vs E&S부동산 -6% 경쟁압력)는 게 "
            "2026-09-03 WebSearch(2026 Q2 실적발표)로 확인돼 중립값 채택. "
            "demand_sensitivity_pct=0.18 - 상업용 특수보험(E&S)·개인우산"
            "배상책임 혼합구조로 SIGI(상업용 비중 큼, 0.18)와 유사한 "
            "사업믹스라 동일값 채택."
        ),
        model_used="two_stage",
        model_choice_reason=(
            "PGR·ACGL·SIGI 선례와 동일하게 two_stage를 채택한다 - "
            "18개년(2008~2025) 매출이 M&A 단계상승이나 극단적 사이클 "
            "없이 꾸준히 성장해왔고($561M->$1,882M), 30년 연속 언더라이팅 "
            "흑자를 유지하며 향후에도 완만한 다년 수렴 성장 궤적이 "
            "이론적으로 부합한다고 판단."
        ),
        falsification_conditions=(
            "(1) 2026 하반기 실적에서 합산비율이 90%를 넘어서거나(현재 "
            "85.6%) E&S부동산 보험료 역성장이 -10% 이상으로 확대되면 "
            "재검토. (2) Arch Capital·Kinsale·W.R. Berkley 등의 E&S 시장 "
            "잠식이 전사 순보험료 역성장으로 이어지면 competition_intensity "
            "상향 재검토. (3) is_insurer 교차검증(지속가능성장률 vs "
            "Realistic Growth) 괴리가 5%p를 넘으면 재검토."
        ),
        price_at_analysis=PRICE,
        currency="USD",
        is_insurer=True,
        net_income_by_year=NET_INCOME,
        shareholders_equity_by_year=SHAREHOLDERS_EQUITY,
        dividends_paid_by_year=DIVIDENDS_PAID,
        data_sources=[
            "SEC XBRL companyfacts (CIK 0000084246, 조회 2026-09-03)",
            "Alpha Vantage GLOBAL_QUOTE (2026-09-02 종가 $63.35)",
            "WebSearch: RLI 10-Q 표지 주식수(2026-06-30 기준), 부채 재확인"
            "(PNC/FHLB $100M), 경쟁구도·합산비율(2026 Q2 실적발표, "
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
