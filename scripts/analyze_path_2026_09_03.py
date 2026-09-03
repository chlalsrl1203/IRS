"""
UiPath, Inc.(PATH) 정식 분석 - 2026-09-03.

경위: 연구 우선순위 큐(스크리너 tier A, Gap 추정 +16.40%p, 시총 근사
~$4.80B). FRAMEWORK_MISMATCH 8종목 제외 뒤 큐 순서상 다음 후보.

## 원자료 - SEC XBRL companyfacts(1차자료, `SecCompanyFactsProvider`,
2026-09-03 조회, CIK 0001734722, 2020~2026 7개년 확보, FYE 1월말 -
FY2026=2025-02~2026-01). 10y CAGR 산출 불가(연도수 부족).

## ⭐ 핵심 발견 1 - 주가가 사상최고가 대비 87% 폭락, 2026년만 -35%.
생성형/에이전틱 AI의 RPA 대체 우려가 근본 원인

2023-11 ChatGPT 출시 이후 UiPath는 "생성형 AI가 RPA를 대체할 것"이라는
구조적 위협 서사에 시달렸고, 사상최고가 대비 -87%, 2026년 한 해만 -35%
하락했다(WebSearch, 2026-09-03). Gartner MQ 2025 기준 Microsoft Power
Automate가 종합점수 4.5로 UiPath(4.1)를 앞서기 시작했으나, UiPath는
6년 연속 RPA 부문 1위를 유지 중 - "가벼운 사무자동화"는 Microsoft가,
"SAP/Oracle/레거시 메인프레임을 포함하는 중대형 엔터프라이즈 프로세스"는
UiPath가 우위를 유지한다는 평가다. 2026-05 "UiPath for Coding Agents"
출시로 경쟁 AI 코딩에이전트 위의 오케스트레이션 레이어로 포지셔닝을
전환 중.

## ⭐ 핵심 발견 2 - 매출성장률이 극심하게 둔화됐다(80%대->한자릿수)

YoY: 2021 +80.8%, 2022 +46.8%, 2023 +18.6%, 2024 +23.6%, 2025 +9.3%,
2026 +12.7% - 초고성장기 이후 뚜렷한 성숙화 국면. FY2026에 처음으로
GAAP 영업이익 흑자전환($56.8M, 직전연도까지 전부 적자)했다는 점은
긍정적 반전 신호.

## ⚠️ 발견 3 - SBC/FCF가 82.5%로 트래커 최상위권(TTD·WDAY급)

FY2026 SBC $290.7M vs FCF0 $352.2M(OCF $371.2M - capex $19.0M) - SBC를
비용으로 차감하면 FCF0가 5분의 1 이하로 줄어든다. AI 대체우려·성장둔화와
겹쳐 판정 취약성이 특히 높을 것으로 예상되는 조합이라 SBC 교차검증
결과를 최우선으로 확인할 것.

## 부수 발견 - FCF 5y CAGR이 근사-0 기준연도 아티팩트다(계산에는 무영향)

FCF(2021)=$27.2M(거의 0에 수렴), FCF(2026)=$352.2M -> FCF 5y CAGR
66.86%라는 비현실적 수치가 나오나, `realistic_growth_estimate()`의
min(매출가중CAGR, FCF CAGR) 로직이 이를 자동으로 버린다(매출가중CAGR이
훨씬 낮아 그쪽이 채택됨) - MU/MNDY/UBER와 동일한 "보호가 우연적"
아티팩트 유형이므로 기록만 해둔다.

## 실행: python3 scripts/analyze_path_2026_09_03.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.filing_dates import pit_inputs_for
from engine.pipeline import AnalysisInputs, run_analysis, save_ledger
from engine.provenance import provenance_from_sec_facts

TICKER = "PATH"
UA = "IRS Research chlalsrl1203@gmail.com"
TODAY = "2026-09-03"

# ── SEC XBRL companyfacts 실측(2026-09-03 조회, FYE 1월말) ───────────────
REVENUE = {
    2020: 336156000.0, 2021: 607643000.0, 2022: 892252000.0,
    2023: 1058581000.0, 2024: 1308072000.0, 2025: 1429664000.0,
    2026: 1610572000.0,
}
OPERATING_INCOME = {
    2020: -517283000.0, 2021: -110323000.0, 2022: -500946000.0,
    2023: -348283000.0, 2024: -164720000.0, 2025: -162569000.0,
    2026: 56760000.0,
}
OPERATING_CASHFLOW = {
    2020: -359436000.0, 2021: 29177000.0, 2022: -54963000.0,
    2023: -9981000.0, 2024: 299082000.0, 2025: 320565000.0,
    2026: 371208000.0,
}
CAPEX = {
    2020: 15748000.0, 2021: 1953000.0, 2022: 8879000.0,
    2023: 23815000.0, 2024: 7342000.0, 2025: 14923000.0,
    2026: 19048000.0,
}
NET_INCOME = {
    2020: -519933000.0, 2021: -92393000.0, 2022: -525586000.0,
    2023: -328352000.0, 2024: -89883000.0, 2025: -73694000.0,
    2026: 282330000.0,
}
SBC = {
    2020: 137862000.0, 2021: 86167000.0, 2022: 515583000.0,
    2023: 369840000.0, 2024: 371955000.0, 2025: 358151000.0,
    2026: 290676000.0,
}

# ── 대차대조표(FY2026말, 2026-01-31, SEC XBRL 실측) ──────────────────────
CASH_2026 = 871157000.0   # CashAndCashEquivalentsAtCarryingValue
DEBT_2026 = 0.0             # LongTermDebtNoncurrent/Current 태그 자체가 없음(무차입)
NET_DEBT = DEBT_2026 - CASH_2026  # -871,157,000(순현금)

DA_2026 = 5800000.0 + 8200000.0  # Depreciation + AmortizationOfIntangibleAssets
EBITDA = OPERATING_INCOME[2026] + DA_2026

# ── 시가총액(2026-09-02, Alpha Vantage 종가 + 최근 분기 희석주식수) ──────
PRICE = 17.99  # Alpha Vantage GLOBAL_QUOTE, 2026-09-02 종가(latestDay)
SHARES_OUT = 527818000.0  # FY2027 Q1(2026-04-30 종료) 10-Q 희석가중평균
MARKET_CAP = PRICE * SHARES_OUT  # 약 $9.50B

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
        company_name="UiPath, Inc.",
        revenue_by_year=REVENUE,
        operating_income_by_year=OPERATING_INCOME,
        operating_cashflow_by_year=OPERATING_CASHFLOW,
        capex_by_year=CAPEX,
        market_cap=MARKET_CAP,
        net_debt=NET_DEBT,
        ebitda=EBITDA,
        risk_free_rate=RF,
        competitor_threat_weights=[0.35, 0.15],
        market_share_trend_pp_per_year=-1.0,
        active_antitrust_or_regulatory_case=False,
        demand_sensitivity_pct=0.22,
        subjective_input_basis=(
            "competitor_threat_weights=[0.35(Microsoft Power Automate), "
            "0.15(Automation Anywhere)] - Gartner MQ 2025 종합점수에서 "
            "Microsoft(4.5)가 UiPath(4.1)를 앞서기 시작했고 M365/Azure "
            "번들링 우위까지 있어 최대 위협으로 높게 반영. Automation Anywhere는 "
            "Gartner 2위이나 UiPath 대비 규모가 작아 낮게 반영. 이 두 경쟁자 "
            "가중치와 별개로 생성형/에이전틱 AI 자체가 RPA 카테고리를 구조적으로 "
            "대체할 수 있다는 서사가 실제 주가에 -87%(사상최고가 대비)로 반영돼 "
            "있음을 감안(2026-09-03 WebSearch). market_share_trend_pp_per_year="
            "-1.0 - Microsoft의 종합점수 역전 + AI대체 서사의 실제 주가반영을 "
            "반영한 음(-)값. demand_sensitivity_pct=0.22 - CLAUDE.md 업종앵커표 "
            "'기업용 필수 SW·전문서비스(계약기반, 전환비용 높음)' 버킷(앵커 0.20) "
            "에 근접하되 소폭 높임 - SAP/Oracle/레거시 통합 자동화는 전환비용이 "
            "높아 매크로 경기민감도 자체는 낮으나, AI대체 서사로 인한 예산 "
            "재배분 리스크를 소폭 반영."
        ),
        model_used="two_stage",
        model_choice_reason=(
            "trailing 매출 CAGR(3y 15.01%/5y 21.53%)이 default_terminal_growth"
            "(2.0~4.5%)보다 여전히 높으나, YoY 성장률이 80%대(2021)에서 한자릿수"
            "~10%대(2025 +9.3%, 2026 +12.7%)로 급격히 둔화된 성숙화 국면이라 "
            "다년 수렴 경로(two_stage)가 적절하다고 판단."
        ),
        falsification_conditions=(
            "다음 분기 매출성장률이 한자릿수 초반으로 추가 둔화되거나, Microsoft "
            "Power Automate·에이전틱 AI 플랫폼으로의 고객 이탈(migration) 구체 "
            "사례가 보고되거나, GAAP 영업흑자가 재차 적자로 전환되면 이 판정을 "
            "재검토할 것. SBC 차감 시 판정이 뒤집히는지(SBC/FCF 82.5%로 트래커 "
            "최상위권) 반드시 함께 확인할 것."
        ),
        price_at_analysis=PRICE,
        currency="USD",
        net_income_by_year=NET_INCOME,
        sbc_by_year=SBC,
        data_sources=[
            "SEC XBRL companyfacts (CIK 0001734722, 조회 2026-09-03)",
            "Alpha Vantage GLOBAL_QUOTE (2026-09-02 종가 $17.99)",
            "WebSearch: PATH 경쟁구도(Gartner MQ 2025)·주가하락 서사·"
            "에이전틱 AI 전략전환(2026-09-03 재인용)",
        ],
        **pit,
        provenance=provenance,
    )


if __name__ == "__main__":
    inputs = build_inputs()
    result = run_analysis(inputs)
    path = save_ledger(result)
    print(f"saved: {path}")
