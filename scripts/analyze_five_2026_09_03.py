"""
Five Below, Inc.(FIVE) 정식 분석 - 2026-09-03.

경위: 연구 우선순위 큐(스크리너 tier B, Gap 추정 +12.76%p, 시총 근사
~$7.26B). FRAMEWORK_MISMATCH 15종목 제외 + HLNE 정식분석 완료 뒤 큐
순서상 다음 후보.

## 원자료 - SEC XBRL companyfacts(1차자료, `SecCompanyFactsProvider`,
2026-09-03 조회, CIK 0001177609, FYE 1월말/2월초(52/53주) 2011~2026
16개년 확보 - 10y CAGR 산출 가능).

## 데이터 정합성 확인 - 52/53주 회계연도지만 라벨충돌 없음

EXEL/CDNS/GEN이 겪은 회계연도 라벨충돌(연말이 캘린더연도 경계 부근에서
갈리는 경우)과 달리, FIVE는 회계연도 종료일이 매년 1월 말~2월 초로
일관돼(never crosses 연중 경계 애매지점) `end` 날짜의 캘린더연도가
회계연도와 항상 일치한다 - 원자료를 직접 대조해 확인(각 기간 raw
entries의 end일 캘린더연도가 provider가 부여한 키와 전부 일치).
`revenue`/`operating_cashflow`에 태그 전환 경고([태그 혼재])가 있으나
경계연도(FY2018 매출, FY2020/2021 OCF)에서 완전히 일치하는 재중복
값이라 실질 왜곡 없음을 직접 대조로 확인.

## ⭐ 핵심 발견 - 스크리너 시총 근사치가 최근 랠리를 크게 놓쳤다

실시간 시총(~$13.44B, Alpha Vantage 종가 + 10-Q 표지 주식수)이 스크리너
근사(~$7.26B)의 1.85배 - OKTA/MEDP/NBIX/NXT/ROKU급 float 스냅샷 노후화
사례. 신임 CEO Winnie Park 체제(Gen Z/Alpha 타겟 전략, "Five Beyond"
가격구조 확장)에서 실적이 크게 개선(2025 홀리데이 코호트 comps +14.5%,
2026 Q2 매출 +22.9%YoY, 가이던스 상향)됐고 주가가 이를 반영해 상승.

## 대차대조표 - 무차입 순현금

`LongTermDebt` 태그 자체가 최근 연도에 없다(2020년 이후 원자료 미보고) -
자체 매장망 확장을 임차(operating lease) 기반으로 운영해 유이자부채가
사실상 없는 구조. FY2026말(2026-01-31) 현금 $723.7M, 순부채 -$723.7M
(순현금).

## 경쟁구도(2026-09-03 WebSearch) - 할인 버라이어티 소매업

Dollar Tree/Family Dollar가 가격 측면 직접경쟁자(다만 소비재·생필품
비중이 Five Below보다 훨씬 높아 구성이 다름), Dollar General은 대규모
일상용품 중심 가치소매업체로 트래픽 경쟁. Ollie's Bargain Outlet은
비즈니스모델이 유사한 참고군(고령층·재고정리 중심으로 고객층은 다름).
Five Below는 "재미·트렌드" 중심 차별화 포지셔닝으로 최근 강한 회복세.

## 실행: python3 scripts/analyze_five_2026_09_03.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.filing_dates import pit_inputs_for
from engine.pipeline import AnalysisInputs, run_analysis, save_ledger
from engine.provenance import provenance_from_sec_facts

TICKER = "FIVE"
UA = "IRS Research chlalsrl1203@gmail.com"
TODAY = "2026-09-03"

# ── SEC XBRL companyfacts 실측(2026-09-03 조회, FYE 1월말/2월초) ─────────
REVENUE = {
    2011: 197189000.0, 2012: 297113000.0, 2013: 418825000.0,
    2014: 535402000.0, 2015: 680218000.0, 2016: 831954000.0,
    2017: 1000410000.0, 2018: 1278208000.0, 2019: 1559563000.0,
    2020: 1846730000.0, 2021: 1962137000.0, 2022: 2848354000.0,
    2023: 3076308000.0, 2024: 3559369000.0, 2025: 3876527000.0,
    2026: 4764147000.0,
}
OPERATING_INCOME = {
    2011: 11804000.0, 2012: 26221000.0, 2013: 37654000.0,
    2014: 53737000.0, 2015: 77016000.0, 2016: 92941000.0,
    2017: 113962000.0, 2018: 157391000.0, 2019: 187184000.0,
    2020: 217284000.0, 2021: 154803000.0, 2022: 379880000.0,
    2023: 345043000.0, 2024: 385571000.0, 2025: 323817000.0,
    2026: 457399000.0,
}
OPERATING_CASHFLOW = {
    2011: 15045000.0, 2012: 46695000.0, 2013: 30363000.0,
    2014: 31187000.0, 2015: 61430000.0, 2016: 87913000.0,
    2017: 106622000.0, 2018: 167381000.0, 2019: 184133000.0,
    2020: 187029000.0, 2021: 365966000.0, 2022: 327912000.0,
    2023: 314926000.0, 2024: 499619000.0, 2025: 430648000.0,
    2026: 586428000.0,
}
CAPEX = {
    2011: 14883000.0, 2012: 18558000.0, 2013: 22890000.0,
    2014: 25931000.0, 2015: 32322000.0, 2016: 53059000.0,
    2017: 44794000.0, 2018: 67795000.0, 2019: 113720000.0,
    2020: 212297000.0, 2021: 200189000.0, 2022: 288167000.0,
    2023: 251954000.0, 2024: 335050000.0, 2025: 323994000.0,
    2026: 174741000.0,
}
NET_INCOME = {
    2011: 7023000.0, 2012: 16078000.0, 2013: 20025000.0,
    2014: 32142000.0, 2015: 48024000.0, 2016: 57680000.0,
    2017: 71840000.0, 2018: 102451000.0, 2019: 149645000.0,
    2020: 175056000.0, 2021: 123361000.0, 2022: 278810000.0,
    2023: 261528000.0, 2024: 301106000.0, 2025: 253611000.0,
    2026: 358641000.0,
}
SBC = {
    2011: 2104000.0, 2012: 1197000.0, 2013: 12324000.0,
    2014: 10092000.0, 2015: 5931000.0, 2016: 11172000.0,
    2017: 11953000.0, 2018: 16373000.0, 2019: 12018000.0,
    2020: 12383000.0, 2021: 9551000.0, 2022: 25787000.0,
    2023: 23583000.0, 2024: 17859000.0, 2025: 15589000.0,
    2026: 34680000.0,
}

# ── 대차대조표(FY2026말, 2026-01-31, SEC XBRL 실측) ───────────────────────
CASH_2026 = 723699000.0  # CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents
DEBT_2026 = 0.0            # LongTermDebt 태그 없음(무차입, 임차기반 확장)
NET_DEBT = DEBT_2026 - CASH_2026  # -723,699,000(순현금)

DA_2026 = 192123000.0  # DepreciationDepletionAndAmortization(FY2026)
EBITDA = OPERATING_INCOME[2026] + DA_2026

# ── 시가총액(2026-09-02, Alpha Vantage 종가 + 10-Q 표지 주식수) ──────────
PRICE = 243.08  # Alpha Vantage GLOBAL_QUOTE, 2026-09-02 종가(latestDay)
SHARES_OUT = 55295351.0  # 10-Q 표지(2026-06-03 기준)
MARKET_CAP = PRICE * SHARES_OUT  # 약 $13.44B

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
        company_name="Five Below, Inc.",
        revenue_by_year=REVENUE,
        operating_income_by_year=OPERATING_INCOME,
        operating_cashflow_by_year=OPERATING_CASHFLOW,
        capex_by_year=CAPEX,
        market_cap=MARKET_CAP,
        net_debt=NET_DEBT,
        ebitda=EBITDA,
        risk_free_rate=RF,
        competitor_threat_weights=[0.15, 0.10],
        market_share_trend_pp_per_year=0.3,
        active_antitrust_or_regulatory_case=False,
        demand_sensitivity_pct=0.20,
        subjective_input_basis=(
            "competitor_threat_weights=[0.15(Dollar General - 대규모 "
            "일상용품 중심 가치소매업체, 트래픽 경쟁), 0.10(Dollar Tree/"
            "Family Dollar - 가격측면 직접경쟁이나 소비재·생필품 비중이 "
            "훨씬 높아 구성이 달라 낮게 반영)]. market_share_trend_pp_"
            "per_year=+0.3 - 신임 CEO 체제에서 comps·매출 성장이 뚜렷이 "
            "가속(2025 홀리데이 comps +14.5%, 2026 Q2 매출 +22.9%YoY, "
            "가이던스 상향)돼 긍정적 방향 반영(2026-09-03 WebSearch). "
            "demand_sensitivity_pct=0.20 - 할인 버라이어티 소매업은 "
            "소비침체 시 트레이드다운 수혜(반경기순환적 요소)와 '재미/"
            "충동구매' 재량소비 요소가 혼재돼 CLAUDE.md 업종앵커표 "
            "'헬스케어·필수소비재 반복매출'(0.12)보다는 높고 '소비자 "
            "구독/플랫폼'(0.30)보다는 낮은 중간값 채택."
        ),
        model_used="two_stage",
        model_choice_reason=(
            "trailing 매출 CAGR(3y 15.70%/5y 19.42%)이 default_terminal_"
            "growth(2.0~4.5%)보다 크게 높고, 매장망 지속 확장 중인 성장기 "
            "소매업이라 다년 수렴 경로(two_stage)가 적절하다고 판단."
        ),
        falsification_conditions=(
            "다음 분기 comps 성장률이 뚜렷이 둔화되거나 Dollar General/"
            "Dollar Tree의 가격경쟁 심화로 트래픽이 유의하게 감소하는 "
            "증거가 나오면 이 판정을 재검토할 것."
        ),
        price_at_analysis=PRICE,
        currency="USD",
        net_income_by_year=NET_INCOME,
        sbc_by_year=SBC,
        data_sources=[
            "SEC XBRL companyfacts (CIK 0001177609, 조회 2026-09-03)",
            "Alpha Vantage GLOBAL_QUOTE (2026-09-02 종가 $243.08)",
            "WebSearch: FIVE 10-Q 표지 주식수(2026-06-03 기준), 경쟁구도·"
            "실적동향(Retail Dive/Placer.ai, 2026-09-03 재인용)",
        ],
        **pit,
        provenance=provenance,
    )


if __name__ == "__main__":
    inputs = build_inputs()
    result = run_analysis(inputs)
    path = save_ledger(result)
    print(f"saved: {path}")
