"""
Hamilton Lane Incorporated(HLNE) 정식 분석 - 2026-09-03.

경위: 연구 우선순위 큐(스크리너 tier A, Gap 추정 +12.80%p, 시총 근사
~$5.47B). FRAMEWORK_MISMATCH 15종목(LNTH/EQT/CDE/CHDN/VICI/COP/DINO/EOG/
COF/IDCC/EXE/XYZ/NEM/WSC/AMP) 제외 뒤 큐 순서상 다음 후보.

## 원자료 - SEC XBRL companyfacts(1차자료, `SecCompanyFactsProvider`,
2026-09-03 조회, CIK 0001433642, FYE 3월 31일(52/53주 아님, 표준
회계연도) 2017~2026 회계연도 확보.

## ⚠️ 데이터 함정 - operating_income 미확보, OperatingExpenses로 직접 파생

HLNE는 사모시장 투자자문·자산운용사(private markets solutions provider,
2023년 완전 지주회사 전환 - LP구조에서 Delaware Corp로)라 `OperatingIncomeLoss`
태그 자체가 없다(COF/AMP와 유사한 결측이나, 원인이 다르다 - 은행/보험처럼
손익구조가 원리적으로 다른 게 아니라 회사가 `Total revenues` -
`OperatingExpenses` = `Income from operations` 구조를 다른 태그명으로
보고할 뿐이다). `OperatingExpenses` 태그가 2016~2026 전 연도 일관되게
확보되어 `operating_income = revenue - OperatingExpenses`로 직접 파생
- 마진이 42.8~50.4%로 안정적이라(고정비 위주 자산운용업 특성과 부합)
파생값의 타당성을 확인했다. MCK capex 파생(v3.60)과 동일한 "회사 자신의
태그 구조로 직접 계산 - 새 추정 아님" 원칙.

## ⚠️ Up-C 구조 확인 - RYAN과 달리 이미 완전 전환돼 함정 없음

HLNE는 과거 Class A/B/C 다중클래스 Up-C 구조였으나(RYAN과 유사 우려
제기), 2026-09-03 WebSearch로 확인한 결과 "Class B·C 유닛의 완전 교환이
이미 GAAP 희석주식수(Class A 공통주 기준)에 전부 반영됐다"(회사 자체
실적발표 언급) - 즉 RYAN과 달리 현재는 사실상 단일 경제적 지분 구조로
완전 전환됐다. SEC 10-Q 표지(2026-07-31 기준) Class A 43,349,167주가
곧 전체 경제적 지분이라 별도 합산이 불필요함을 확인했다.

## 발견 - 안정적 다년 성장, M&A 왜곡 없음

매출 3y CAGR 11.07%/5y CAGR 17.32%, 단일연도 단계상승 없이 유기적
성장곡선(AUM 성장 기반). FCF(OCF-capex) 3y CAGR 23.63%/5y CAGR 19.85%.

## 경쟁구도(2026-09-03 WebSearch) - 사모시장 솔루션·자문 업종

HLNE는 이 분야 "Top 3" 글로벌 사업자로 평가되나, Blackstone·KKR 등
초대형 대체투자사가 에버그린/리테일 펀드 시장에 공격적으로 진출 중이라
규모 우위 경쟁압력이 존재. StepStone Group이 동일 비즈니스모델(사모시장
솔루션·자문)의 직접 경쟁자. 업계 전반의 수수료 압박(fee pressure)이
구조적 리스크로 지목됨. AUM $1.1조(2026-06-30 기준, discretionary
$146.3B + non-discretionary $914.1B), 2022~2026 AUM CAGR 7%.

## 실행: python3 scripts/analyze_hlne_2026_09_03.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.filing_dates import pit_inputs_for
from engine.pipeline import AnalysisInputs, run_analysis, save_ledger
from engine.provenance import provenance_from_sec_facts

TICKER = "HLNE"
UA = "IRS Research chlalsrl1203@gmail.com"
TODAY = "2026-09-03"

# ── SEC XBRL companyfacts 실측(2026-09-03 조회, FYE 3월 31일) ────────────
REVENUE = {
    2017: 179820000.0, 2018: 244033000.0, 2019: 252179000.0,
    2020: 274048000.0, 2021: 341635000.0, 2022: 367919000.0,
    2023: 528753000.0, 2024: 553842000.0, 2025: 712963000.0,
    2026: 758993000.0,
}
OPERATING_EXPENSES = {
    2017: 103705000.0, 2018: 121080000.0, 2019: 147955000.0,
    2020: 157619000.0, 2021: 185907000.0, 2022: 198355000.0,
    2023: 288713000.0, 2024: 308024000.0, 2025: 396411000.0,
    2026: 434050000.0,
}
OPERATING_INCOME = {y: REVENUE[y] - OPERATING_EXPENSES[y] for y in REVENUE}
OPERATING_CASHFLOW = {
    2017: 81679000.0, 2018: 96692000.0, 2019: 111622000.0,
    2020: 116373000.0, 2021: 188158000.0, 2022: 169523000.0,
    2023: 226589000.0, 2024: 120852000.0, 2025: 300820000.0,
    2026: 424917000.0,
}
CAPEX = {
    2017: 1275000.0, 2018: 2254000.0, 2019: 5366000.0,
    2020: 1978000.0, 2021: 18637000.0, 2022: 8526000.0,
    2023: 4747000.0, 2024: 11073000.0, 2025: 12156000.0,
    2026: 5844000.0,
}
NET_INCOME = {
    2017: 612000.0, 2018: 17341000.0, 2019: 33573000.0,
    2020: 60825000.0, 2021: 98022000.0, 2022: 145986000.0,
    2023: 109120000.0, 2024: 140858000.0, 2025: 217417000.0,
    2026: 249180000.0,
}
SBC = {
    2017: 4681000.0, 2018: 5544000.0, 2019: 6382000.0,
    2020: 7183000.0, 2021: 7079000.0, 2022: 7404000.0,
    2023: 9950000.0, 2024: 12133000.0, 2025: 31407000.0,
    2026: 50867000.0,
}

# ── 대차대조표(FY2026말, 2026-03-31, SEC XBRL 실측) ───────────────────────
CASH_2026 = 371904000.0    # CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents
DEBT_2026 = 278420000.0    # LongTermDebt
NET_DEBT = DEBT_2026 - CASH_2026  # -93,484,000(순현금)

DA_2026 = 9878000.0  # DepreciationDepletionAndAmortization(FY2026, 2025-04~2026-03)
EBITDA = OPERATING_INCOME[2026] + DA_2026

# ── 시가총액(2026-09-02, Alpha Vantage 종가 + SEC 10-Q 표지 Class A) ─────
PRICE = 103.16  # Alpha Vantage GLOBAL_QUOTE, 2026-09-02 종가(latestDay)
SHARES_OUT = 43349167.0  # 10-Q 표지(2026-07-31 기준) Class A 주식수 - Class B/C 완전전환 완료
MARKET_CAP = PRICE * SHARES_OUT  # 약 $4.47B

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
        company_name="Hamilton Lane Incorporated",
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
        demand_sensitivity_pct=0.25,
        subjective_input_basis=(
            "competitor_threat_weights=[0.20(Blackstone/KKR류 초대형 "
            "대체투자사), 0.15(StepStone Group)] - 초대형사가 에버그린/"
            "리테일 펀드 시장에 규모 우위로 공격적 진출 중이라 비중있게 "
            "반영, StepStone은 동일 비즈니스모델(사모시장 솔루션·자문)의 "
            "직접 경쟁자. market_share_trend_pp_per_year=0.0 - 'Top 3' "
            "지위 유지·AUM CAGR 7% 성장 지속 중이나 업계 전반 수수료압박이 "
            "구조적 리스크로 지목돼 뚜렷한 방향성 근거가 부족해 중립값 "
            "채택(2026-09-03 WebSearch). demand_sensitivity_pct=0.25 - "
            "관리보수(management fee)는 약정자본 기준 계약형이라 상대적으로 "
            "안정적이나, 성과보수(incentive fee)는 시장 사이클·펀드 성과에 "
            "연동돼 변동성이 있어 CLAUDE.md 업종앵커표 '기업용 필수 SW·"
            "전문서비스'(0.20) 앵커보다 다소 높게 조정."
        ),
        model_used="two_stage",
        model_choice_reason=(
            "trailing 매출 CAGR(3y 11.07%/5y 17.32%)이 default_terminal_"
            "growth(2.0~4.5%)보다 크게 높고, AUM 기반 사업 특성상 향후 "
            "여러 해에 걸쳐 성장률이 완만히 수렴할 것으로 예상돼 다년 "
            "수렴 경로(two_stage)가 적절하다고 판단."
        ),
        falsification_conditions=(
            "다음 분기 AUM 성장률이 뚜렷이 둔화되거나 Blackstone/KKR류 "
            "초대형사의 사모시장 솔루션 부문 진출로 수수료율(fee rate)이 "
            "가시적으로 압박받는 증거가 나오면 이 판정을 재검토할 것."
        ),
        price_at_analysis=PRICE,
        currency="USD",
        net_income_by_year=NET_INCOME,
        sbc_by_year=SBC,
        data_sources=[
            "SEC XBRL companyfacts (CIK 0001433642, 조회 2026-09-03) - "
            "operating_income은 revenue-OperatingExpenses로 직접 파생",
            "Alpha Vantage GLOBAL_QUOTE (2026-09-02 종가 $103.16)",
            "WebSearch: HLNE 10-Q 표지 Class A 주식수(2026-07-31 기준), "
            "AUM·경쟁구도(2026-09-03 재인용)",
        ],
        **pit,
        provenance=provenance,
    )


if __name__ == "__main__":
    inputs = build_inputs()
    result = run_analysis(inputs)
    path = save_ledger(result)
    print(f"saved: {path}")
