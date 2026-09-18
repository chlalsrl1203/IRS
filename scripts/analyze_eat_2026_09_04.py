"""
Brinker International, Inc.(EAT) 정식 분석 - 2026-09-04.

경위: 연구 우선순위 큐 tier A, 스크리너 Gap 추정 +8.39%p. FRAMEWORK_MISMATCH
20종목 + BYD·CRM·DECK·QCOM 정식분석 + (HBAN/CNM/CVX/AXP/GLPI 배제) 뒤
큐 순서상 다음 후보. Chili's Grill & Bar·Maggiano's Little Italy 운영사.

## 원자료 - SEC XBRL companyfacts(CIK 0000703351, 2026-09-04 조회,
FY2016~FY2026 11개년 확보, 6월말 결산).

## 성장동력 - Chili's 브랜드의 실제 확인된 턴어라운드(M&A 아님)

2026-09-04 WebSearch로 확인: Chili's가 FY2025 동일매장매출 +약26%
(21분기 연속 성장 중, 메뉴개편·운영단순화·가치소구 마케팅이 원인) -
2010년대 정체됐던 브랜드가 실질적으로 회복. FY2026 들어 4~5%대로 감속
(비교기저 상승) 중이나 여전히 플러스 성장 유지. **M&A 없이 순수 오가닉**
(GEN/BRO/ROP류 왜곡과 무관) - rev 3y(12.0%)·5y(11.71%)가 서로 정합적,
10y(5.95%)만 낮은데 이는 2016~2020년 실제 정체기(브랜드 부진기)를
정확히 반영하는 것이라 왜곡이 아니다(오버라이드 불필요). 회사 자체 대차
대조표도 10년 넘게 자기자본잠식(공격적 자사주매입) 상태였다가 FY2024부터
플러스 전환 - 턴어라운드가 재무구조에도 실질적으로 반영됐다.

## 대차대조표 - 저레버리지(net_debt/EBITDA≈0.40x)

FY2026말(2026-06-24) DebtAndCapitalLeaseObligations $4.48억, 현금
$1.10억, 순부채 $3.38억. EBITDA(OPINC+D&A) $8.365억.

## 실시간 시총이 스크리너 근사보다 1.47배 높음

주가 $228.88(2026-09-03) x 발행주식 4177만주(2026-08-11 10-K) = 약
$95.6억 - 스크리너 근사($65.2억)의 1.47배(턴어라운드 재평가로 인한 대폭
주가상승 + float 스냅샷 노후화 복합).

## 실행: python3 scripts/analyze_eat_2026_09_04.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.filing_dates import pit_inputs_for
from engine.pipeline import AnalysisInputs, run_analysis, save_ledger
from engine.provenance import provenance_from_sec_facts

TICKER = "EAT"
UA = "IRS Research chlalsrl1203@gmail.com"
TODAY = "2026-09-04"

# ── SEC XBRL companyfacts 실측(2026-09-04 조회, CIK 0000703351) ──────────
# 회계연도는 6월말 결산(FY2026 = 2025-07~2026-06)
REVENUE = {
    2016: 3257489000.0, 2017: 3150837000.0, 2018: 3135417000.0, 2019: 3217900000.0,
    2020: 3078500000.0, 2021: 3337800000.0, 2022: 3804100000.0, 2023: 4133200000.0,
    2024: 4415100000.0, 2025: 5384200000.0, 2026: 5807400000.0,
}
OPERATING_INCOME = {
    2016: 317476000.0, 2017: 256178000.0, 2018: 226106000.0, 2019: 230700000.0,
    2020: 62600000.0, 2021: 199300000.0, 2022: 159500000.0, 2023: 144400000.0,
    2024: 229600000.0, 2025: 512000000.0, 2026: 619900000.0,
}
OPERATING_CASHFLOW = {
    2016: 394700000.0, 2017: 312886000.0, 2018: 284451000.0, 2019: 212700000.0,
    2020: 245000000.0, 2021: 369700000.0, 2022: 252200000.0, 2023: 256300000.0,
    2024: 421900000.0, 2025: 679000000.0, 2026: 789400000.0,
}
CAPEX = {
    2016: 112788000.0, 2017: 102573000.0, 2018: 101281000.0, 2019: 167600000.0,
    2020: 104500000.0, 2021: 94000000.0, 2022: 150300000.0, 2023: 184900000.0,
    2024: 198900000.0, 2025: 265300000.0, 2026: 231900000.0,
}
NET_INCOME = {  # 참고 기록만 - is_insurer 아니므로 계산에 미사용
    2016: 200745000.0, 2017: 150823000.0, 2018: 125882000.0, 2019: 154900000.0,
    2020: 24400000.0, 2021: 131600000.0, 2022: 117600000.0, 2023: 102600000.0,
    2024: 155300000.0, 2025: 383100000.0, 2026: 487000000.0,
}
SBC = {
    2016: 15159000.0, 2017: 14568000.0, 2018: 14245000.0, 2019: 16400000.0,
    2020: 14800000.0, 2021: 16400000.0, 2022: 18600000.0, 2023: 14400000.0,
    2024: 25900000.0, 2025: 31400000.0, 2026: 32200000.0,
}

# ── 대차대조표(FY2026말, 2026-06-24) ──────────────────────────────────────
DEBT_2026 = 448000000.0  # DebtAndCapitalLeaseObligations(총액, LT+Current)
CASH_2026 = 110000000.0  # CashAndCashEquivalentsAtCarryingValue
NET_DEBT = DEBT_2026 - CASH_2026  # $338,000,000

DA_2026 = 216600000.0  # Depreciation(FY2026)
EBITDA = OPERATING_INCOME[2026] + DA_2026  # $836,500,000

# ── 시가총액(2026-09-03 Alpha Vantage 종가 + 최신 EntityCommonStockShares) ─
PRICE = 228.88  # Alpha Vantage GLOBAL_QUOTE, 2026-09-03 종가(latestDay)
SHARES_OUT = 41765010.0  # EntityCommonStockSharesOutstanding, 2026-08-11 기준(10-K)
MARKET_CAP = PRICE * SHARES_OUT  # 약 $9.56B

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
        company_name="Brinker International, Inc.",
        revenue_by_year=REVENUE,
        operating_income_by_year=OPERATING_INCOME,
        operating_cashflow_by_year=OPERATING_CASHFLOW,
        capex_by_year=CAPEX,
        market_cap=MARKET_CAP,
        net_debt=NET_DEBT,
        ebitda=EBITDA,
        risk_free_rate=RF,
        competitor_threat_weights=[0.12, 0.10],
        market_share_trend_pp_per_year=0.3,
        active_antitrust_or_regulatory_case=False,
        demand_sensitivity_pct=0.30,
        subjective_input_basis=(
            "competitor_threat_weights=[0.12(Applebee's/Dine Brands - "
            "캐주얼다이닝 직접경쟁자), 0.10(Texas Roadhouse - 가치소구형 "
            "캐주얼다이닝 경쟁자)]. market_share_trend_pp_per_year=0.3 - "
            "Chili's가 21분기 연속 동일매장매출 성장 중이며 업계평균을 "
            "상회하는 것으로 확인돼(2026-09-04 WebSearch) 양수 채택. "
            "demand_sensitivity_pct=0.30 - 캐주얼다이닝은 재량소비 성격이나 "
            "Chili's의 가치소구 포지셔닝(저가 프로모션)이 경기둔화기에도 "
            "방어력을 보여온 것으로 판단해 CLAUDE.md 앵커표 '소비자 구독/"
            "플랫폼'(0.30)에 근접 채택."
        ),
        model_used="two_stage",
        model_choice_reason=(
            "trailing 매출 CAGR(3y 12.0%/5y 11.71%)이 default_terminal_"
            "growth(2.0~4.5%)를 상회하나, 회사 스스로 밝힌 성장 감속 패턴"
            "(FY2025 동일매장매출 +26%->FY2026 4~5%대, 비교기저 상승에 따른 "
            "자연스러운 정상화)이 다년 수렴 경로에 부합해 two_stage를 "
            "채택. 10y CAGR(5.95%)은 2016~2020년 실제 브랜드 정체기를 "
            "반영하는 것이라 오버라이드하지 않았다."
        ),
        falsification_conditions=(
            "FY2027 실적에서 Chili's 동일매장매출 성장률이 마이너스로 "
            "전환되거나(현재 20분기 이상 연속 플러스 기록 종료), 가치소구 "
            "마케팅 효과가 소진돼 트래픽 증가 없이 가격인상에만 의존하는 "
            "패턴이 지속되면 이 판정을 재검토할 것."
        ),
        price_at_analysis=PRICE,
        currency="USD",
        net_income_by_year=NET_INCOME,
        sbc_by_year=SBC,
        data_sources=[
            "SEC XBRL companyfacts (CIK 0000703351, 조회 2026-09-04)",
            "Alpha Vantage GLOBAL_QUOTE (2026-09-03 종가 $228.88)",
            "WebSearch: Chili's 동일매장매출 턴어라운드 추이(2026-09-04 재인용)",
        ],
        **pit,
        provenance=provenance,
    )


if __name__ == "__main__":
    inputs = build_inputs()
    result = run_analysis(inputs)
    path = save_ledger(result)
    print(f"saved: {path}")
