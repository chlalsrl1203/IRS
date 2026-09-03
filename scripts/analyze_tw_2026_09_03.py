"""
Tradeweb Markets Inc.(TW) 정식 분석 - 2026-09-03.

경위: 연구 우선순위 큐(스크리너 tier A, Gap 추정 +12.69%p, 시총 근사
~$16.9B). FRAMEWORK_MISMATCH 15종목 + HLNE/FIVE 정식분석 완료 뒤 큐
순서상 다음 후보.

## 원자료 - SEC XBRL companyfacts(1차자료, `SecCompanyFactsProvider`,
2026-09-03 조회, CIK 0001758730, 2017/2019~2025 확보 - 2018년(IPO
2019-04) 자료 없음, 3y/5y CAGR 산출에는 영향 없음(2022/2020 기준연도
모두 확보).

## ⭐ 핵심 발견 - 다중클래스 구조, RYAN과 정반대의 함정(경제적 지분이
아닌 클래스를 걸러내야 함)

TW는 Class A/B/C/D 4중 주식클래스 구조 - RYAN(Up-C, 모든 클래스가
경제적으로 동등)과 비슷해 보이나 실제로는 정반대다. 2026-09-03
WebSearch로 회사 S-1/증권신고서 원문을 확인한 결과 **"Class C·D 보통주
보유자는 Class A가 갖는 배당·청산분배 등 경제적 권리를 전혀 갖지
않는다"**(회사 공시 원문) - Class C/D는 순수 의결권(각 1표/10표) 전용
주식으로 LSEG(런던증권거래소그룹)의 지배력 확보 수단일 뿐, 경제적 지분은
0이다. **경제적 지분은 Class A(114,140,240주)+Class B(96,933,192주, LLC
지분과 1:1 교환권+배당권)뿐** - Class C(18,000,000)+D(5,056,868)를
포함시키면 실제로는 **없는** 경제적 가치를 더해 시총을 과대계상하는
것이므로 명시적으로 제외했다(2026-09-03 WebSearch, SEC S-1 원문 인용
재확인 - RYAN이 "모든 클래스 합산 필요"였다면 TW는 "일부 클래스만 합산
필요"인 정반대 사례).

## 대차대조표 - 무차입 순현금

`LongTermDebt` 계열 태그 전부 없음(무차입). FY2025말(2025-12-31) 현금
$2,084.7M.

## 경쟁구도(2026-09-03 WebSearch) - 전자 채권거래 플랫폼 업종

**2026-07 ICE(Intercontinental Exchange)가 MarketAxess를 $60억에
인수** - Tradeweb·Bloomberg와 경쟁하던 MarketAxess가 ICE의 자본력을
등에 업은 강력한 통합경쟁자로 재편되는 구조적 변화. 다만 2026-06 TW가
美 신용채권(credit) 전자거래 시장점유율에서 **사상 최초로 MarketAxess를
추월** - 20년간 이 부문 압도적 1위였던 MarketAxess를 상대로 한 실질적
점유율 확대가 실측 확인됨. Rates(금리)/IRS 부문은 이미 선두, Credit
부문은 개선 중.

## 실행: python3 scripts/analyze_tw_2026_09_03.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.filing_dates import pit_inputs_for
from engine.pipeline import AnalysisInputs, run_analysis, save_ledger
from engine.provenance import provenance_from_sec_facts

TICKER = "TW"
UA = "IRS Research chlalsrl1203@gmail.com"
TODAY = "2026-09-03"

# ── SEC XBRL companyfacts 실측(2026-09-03 조회, 2018년 자료 없음) ────────
REVENUE = {
    2017: 562968000.0, 2019: 775566000.0, 2020: 892659000.0,
    2021: 1076447000.0, 2022: 1188781000.0, 2023: 1338219000.0,
    2024: 1725949000.0, 2025: 2052429000.0,
}
OPERATING_INCOME = {
    2017: 89092000.0, 2019: 189819000.0, 2020: 263355000.0,
    2021: 358828000.0, 2022: 412573000.0, 2023: 505269000.0,
    2024: 678028000.0, 2025: 835338000.0,
}
OPERATING_CASHFLOW = {
    2017: 224580000.0, 2019: 311003000.0, 2020: 443234000.0,
    2021: 578021000.0, 2022: 632822000.0, 2023: 746089000.0,
    2024: 897741000.0, 2025: 1167646000.0,
}
CAPEX = {
    2017: 13461000.0, 2019: 15781000.0, 2020: 11490000.0,
    2021: 16878000.0, 2022: 23214000.0, 2023: 18529000.0,
    2024: 40960000.0, 2025: 40552000.0,
}
NET_INCOME = {
    2017: 83648000.0, 2019: 83769000.0, 2020: 166296000.0,
    2021: 226828000.0, 2022: 309338000.0, 2023: 364866000.0,
    2024: 501507000.0, 2025: 812792000.0,
}
SBC = {
    2017: 26100000.0, 2019: 49824000.0, 2020: 39286000.0,
    2021: 51943000.0, 2022: 66644000.0, 2023: 65128000.0,
    2024: 89649000.0, 2025: 103537000.0,
}

# ── 대차대조표(FY2025말, 2025-12-31, SEC XBRL 실측) ───────────────────────
CASH_2025 = 2084739000.0  # CashAndCashEquivalentsAtCarryingValue
DEBT_2025 = 0.0              # LongTermDebt 계열 태그 없음(무차입)
NET_DEBT = DEBT_2025 - CASH_2025  # -2,084,739,000(순현금)

DA_2025 = 250189000.0  # DepreciationAndAmortization(FY2025)
EBITDA = OPERATING_INCOME[2025] + DA_2025

# ── 시가총액(2026-09-02, Alpha Vantage 종가 + 경제적 지분 클래스만 합산) ──
PRICE = 103.47  # Alpha Vantage GLOBAL_QUOTE, 2026-09-02 종가(latestDay)
SHARES_A = 114140240.0   # 2026-06-30 10-Q 표지, 경제적 지분 있음
SHARES_B = 96933192.0    # 2026-06-30 10-Q 표지, LLC지분 1:1교환+배당권 - 경제적 지분 있음
# Class C(18,000,000)+D(5,056,868)는 회사 공시상 배당·청산분배 등
# 경제적 권리가 전혀 없는 순수 의결권 전용 주식이라 제외(위 docstring 참고)
SHARES_OUT = SHARES_A + SHARES_B  # 211,073,432
MARKET_CAP = PRICE * SHARES_OUT  # 약 $21.84B

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
        company_name="Tradeweb Markets Inc.",
        revenue_by_year=REVENUE,
        operating_income_by_year=OPERATING_INCOME,
        operating_cashflow_by_year=OPERATING_CASHFLOW,
        capex_by_year=CAPEX,
        market_cap=MARKET_CAP,
        net_debt=NET_DEBT,
        ebitda=EBITDA,
        risk_free_rate=RF,
        competitor_threat_weights=[0.20, 0.15],
        market_share_trend_pp_per_year=0.2,
        active_antitrust_or_regulatory_case=False,
        demand_sensitivity_pct=0.15,
        subjective_input_basis=(
            "competitor_threat_weights=[0.20(ICE-MarketAxess 통합체 - "
            "2026-07 ICE가 MarketAxess를 $60억에 인수해 자본력을 등에 업은 "
            "강력한 신규 위협으로 재편), 0.15(Bloomberg - 터미널 기반 "
            "압도적 진입장벽을 가진 기존 강자)]. market_share_trend_pp_"
            "per_year=+0.2 - 2026-06 美 신용채권 전자거래 시장점유율에서 "
            "TW가 20년간 1위였던 MarketAxess를 사상 최초로 추월한 실측을 "
            "긍정적으로 반영하되 ICE 인수 리스크를 감안해 완만한 값 채택 "
            "(2026-09-03 WebSearch). demand_sensitivity_pct=0.15 - 전자 "
            "채권거래 플랫폼은 거래대금 연동 매출구조라 시장변동성 확대 "
            "시 오히려 거래량이 늘어나는 반경기순환적 요소가 있어 CLAUDE.md "
            "업종앵커표 '필수/의무 지출'(0.08)보다는 높고 '기업용 필수 "
            "SW·전문서비스'(0.20)보다는 낮게 채택."
        ),
        model_used="two_stage",
        model_choice_reason=(
            "trailing 매출 CAGR(3y 19.94%/5y 18.15%)이 default_terminal_"
            "growth(2.0~4.5%)보다 크게 높고, 다중 자산군(금리·크레딧·ETF·"
            "파생상품)으로의 지속적 확장 국면이라 다년 수렴 경로"
            "(two_stage)가 적절하다고 판단."
        ),
        falsification_conditions=(
            "ICE-MarketAxess 통합법인이 향후 분기 신용채권 전자거래 "
            "시장점유율을 재역전하는 구체 증거가 나오거나, TW의 거래대금"
            "(ADV) 성장률이 뚜렷이 둔화되면 이 판정을 재검토할 것."
        ),
        price_at_analysis=PRICE,
        currency="USD",
        net_income_by_year=NET_INCOME,
        sbc_by_year=SBC,
        data_sources=[
            "SEC XBRL companyfacts (CIK 0001758730, 조회 2026-09-03)",
            "Alpha Vantage GLOBAL_QUOTE (2026-09-02 종가 $103.47)",
            "WebSearch: TW 10-Q 표지 클래스별 주식수(2026-06-30 기준), "
            "S-1 경제적 권리 구조, ICE-MarketAxess 인수·경쟁구도(2026-09-03 "
            "재인용)",
        ],
        **pit,
        provenance=provenance,
    )


if __name__ == "__main__":
    inputs = build_inputs()
    result = run_analysis(inputs)
    path = save_ledger(result)
    print(f"saved: {path}")
