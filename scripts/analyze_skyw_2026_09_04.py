"""
SkyWest, Inc.(SKYW) 정식 분석 - 2026-09-04.

경위: 연구 우선순위 큐(스크리너 tier A, Gap 추정 +10.98%p, 시총 근사
~$4.16B). FRAMEWORK_MISMATCH 18종목(LNTH/EQT/CDE/CHDN/VICI/COP/DINO/
EOG/COF/IDCC/EXE/XYZ/NEM/WSC/AMP/OVV/CF/HL) 제외, HLNE/FIVE/TW/RLI/
CINF/TENB 정식분석 완료 뒤 큐 순서상 다음 후보.

## 원자료 - SEC XBRL companyfacts(1차자료, `SecCompanyFactsProvider`,
2026-09-03/04 조회, CIK 0000793733, 2009~2025 17개년 확보 - 10y CAGR
산출 가능).

## ⚠️ capex 정의 공존 - 넓은 정의(항공기 취득 포함) 채택

`[capex 정의 공존]` 경고 발생 - 넓은 정의(생산자산 취득,
PaymentsToAcquireProductiveAssets류)와 좁은 정의(유형자산 취득)가 함께
보고되며 FY2025 기준 548,984,000 vs 32,023,000로 17배 차이. **넓은
정의를 그대로 채택했다** - MCK capex 파생(v3.60) 때와 반대로 이번엔
넓은 정의가 명백히 옳다: 지상장비만 잡는 좁은 정의는 항공사의 핵심
자본자산인 **항공기 취득**을 빠뜨린다. 좁은 정의를 쓰면 FCF가 사실상
전액 OCF와 같아져(자본집약 항공사 특성이 사라짐) 명백히 왜곡된다.

## 대차대조표 - 상당한 부채(전형적 항공사 구조)

`LongTermDebtNoncurrent`+`LongTermDebtCurrent` = FY2025말 $2,392.1M,
현금 $122.7M(투자자 대상 자사주매입에 사용) - 순부채 $2,269.4M,
net_debt/EBITDA ≈ 2.31x(항공사 기준 준수한 수준).

## 경쟁구도(2026-09-03 WebSearch) - 지역항공(Capacity Purchase
Agreement) 업종

**⭐ CPA(용량구매계약) 구조가 수요변동성을 원리적으로 차단** - 본선
항공사(Delta/United/American/Alaska)가 요금·수요·연료위험을 부담하고
지역항공사는 고정 용량기반 수수료만 받는다(WebSearch 원문: "regional
carrier is insulated from demand and pricing volatility"). SkyWest·
Republic Airways가 독립계 지역항공 운항의 약 84%를 양분(사실상
복점) - Republic이 CPA수주·조종사·항공기경제성에서 직접경쟁하는
가장 가까운 동종업체. 조종사 부족(2026년 북미 전체 약 24,000명
부족 전망)은 업계 전반 비용/공급 리스크이지 SkyWest 고유의 경쟁열위는
아님. United Express 확장이 SkyWest Leasing 이익을 +23.8%(Q1
2026) 견인 중.

## 실행: python3 scripts/analyze_skyw_2026_09_04.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.filing_dates import pit_inputs_for
from engine.pipeline import AnalysisInputs, run_analysis, save_ledger
from engine.provenance import provenance_from_sec_facts

TICKER = "SKYW"
UA = "IRS Research chlalsrl1203@gmail.com"
TODAY = "2026-09-04"

# ── SEC XBRL companyfacts 실측(2026-09-03/04 조회) ───────────────────────
REVENUE = {
    2011: 3654923000.0,
    2012: 3534372000.0, 2013: 3297725000.0, 2014: 3237447000.0,
    2015: 3095563000.0, 2016: 3063702000.0, 2017: 3122592000.0,
    2018: 3221679000.0, 2019: 2971963000.0, 2020: 2127106000.0,
    2021: 2713491000.0, 2022: 3004925000.0, 2023: 2935432000.0,
    2024: 3527920000.0, 2025: 4058202000.0,
}
OPERATING_INCOME = {
    2011: 41105000.0,
    2012: 165987000.0, 2013: 153111000.0, 2014: 24848000.0,
    2015: 234515000.0, 2016: -172684000.0, 2017: 388199000.0,
    2018: 474280000.0, 2019: 512258000.0, 2020: 108802000.0,
    2021: 275867000.0, 2022: 181162000.0, 2023: 104069000.0,
    2024: 494657000.0, 2025: 617846000.0,
}
OPERATING_CASHFLOW = {
    2011: 162126000.0,
    2012: 288824000.0, 2013: 289890000.0, 2014: 285539000.0,
    2015: 417325000.0, 2016: 506665000.0, 2017: 684124000.0,
    2018: 802534000.0, 2019: 721030000.0, 2020: 633563000.0,
    2021: 831820000.0, 2022: 480376000.0, 2023: 736334000.0,
    2024: 692462000.0, 2025: 940364000.0,
}
# 넓은 정의(항공기 취득 포함) - 위 docstring 참고
CAPEX = {
    2011: 199756000.0, 2012: 94840000.0, 2013: 142044000.0,
    2014: 696923000.0, 2015: 715089000.0, 2016: 1159001000.0,
    2017: 689398000.0, 2018: 1156276000.0, 2019: 846470000.0,
    2020: 460483000.0, 2021: 567037000.0, 2022: 662317000.0,
    2023: 263909000.0, 2024: 439220000.0, 2025: 548984000.0,
}
NET_INCOME = {
    2015: 117817000.0, 2016: -161586000.0, 2017: 428907000.0,
    2018: 280372000.0, 2019: 340099000.0, 2020: -8515000.0,
    2021: 111910000.0, 2022: 72953000.0, 2023: 34342000.0,
    2024: 322962000.0, 2025: 428334000.0,
}
SBC = {
    2011: 5365000.0,
    2012: 4693000.0, 2013: 4363000.0, 2014: 5318000.0,
    2015: 5368000.0, 2016: 7568000.0, 2017: 10580000.0,
    2018: 13105000.0, 2019: 10274000.0, 2020: 6802000.0,
    2021: 8685000.0, 2022: 9159000.0, 2023: 17125000.0,
    2024: 19864000.0, 2025: 18729000.0,
}

# ── 대차대조표(FY2025말, 2025-12-31, SEC XBRL 실측) ───────────────────────
CASH_2025 = 122673000.0        # CashAndCashEquivalentsAtCarryingValue
DEBT_2025 = 1845272000.0 + 546812000.0  # LongTermDebtNoncurrent + LongTermDebtCurrent
NET_DEBT = DEBT_2025 - CASH_2025  # 2,269,411,000

DA_2025 = 364497000.0  # DepreciationDepletionAndAmortization(FY2025)
EBITDA = OPERATING_INCOME[2025] + DA_2025

# ── 시가총액(2026-08말, Alpha Vantage 종가 + 최근 자사주매입 반영 주식수) ─
PRICE = 94.96   # Alpha Vantage GLOBAL_QUOTE, 2026-08-31 종가 근사
SHARES_OUT = 38830000.0  # 2026-08월말 근사(Feb 2026 10-K 40,406,672주에서
                            # 2026 H1 자사주매입으로 감소, WebSearch 확인)
MARKET_CAP = PRICE * SHARES_OUT  # 약 $3.69B

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
        company_name="SkyWest, Inc.",
        revenue_by_year=REVENUE,
        operating_income_by_year=OPERATING_INCOME,
        operating_cashflow_by_year=OPERATING_CASHFLOW,
        capex_by_year=CAPEX,
        market_cap=MARKET_CAP,
        net_debt=NET_DEBT,
        ebitda=EBITDA,
        risk_free_rate=RF,
        competitor_threat_weights=[0.20, 0.10],
        market_share_trend_pp_per_year=0.3,
        active_antitrust_or_regulatory_case=False,
        demand_sensitivity_pct=0.10,
        subjective_input_basis=(
            "competitor_threat_weights=[0.20(Republic Airways - 독립계 "
            "지역항공 운항에서 SkyWest와 함께 약 84% 양분, CPA수주·조종사·"
            "항공기경제성에서 가장 직접적으로 경쟁), 0.10(본선항공사 "
            "산하 캡티브 지역자회사(Envoy/PSA/Piedmont/Endeavor) - 별도 "
            "상장 경쟁사는 아니나 CPA 슬롯을 구조적으로 잠식할 수 있어 "
            "낮게 반영)]. market_share_trend_pp_per_year=+0.3 - United "
            "Express 확장으로 SkyWest Leasing 이익이 +23.8%(Q1 2026) "
            "성장 중(2026-09-03 WebSearch). demand_sensitivity_pct=0.10 "
            "- CPA(용량구매계약) 구조상 본선항공사가 요금·수요·연료위험을 "
            "부담하고 지역항공사는 고정 용량기반 수수료만 받아 수요 "
            "변동성으로부터 원리적으로 절연됨(회사 자체 CPA 계약구조 "
            "설명, WebSearch 재확인) - CLAUDE.md 업종앵커표 어느 버킷보다 "
            "낮게 채택."
        ),
        model_used="two_stage",
        model_choice_reason=(
            "trailing 매출 CAGR(3y 11.42%/5y 13.85%/10y 이용가능)이 "
            "default_terminal_growth(2.0~4.5%)보다 높고, CPA 신규체결·"
            "기존기재 대체(E175 등)로 지속적 매출 성장이 예상되는 국면"
            "이라 다년 수렴 경로(two_stage)가 적절하다고 판단."
        ),
        falsification_conditions=(
            "다음 분기 SkyWest Leasing 이익 성장률이 뚜렷이 둔화되거나 "
            "조종사 부족 심화로 신규 CPA 항공기 배치가 지연되는 구체 "
            "증거가 나오면 이 판정을 재검토할 것."
        ),
        price_at_analysis=PRICE,
        currency="USD",
        net_income_by_year=NET_INCOME,
        sbc_by_year=SBC,
        data_sources=[
            "SEC XBRL companyfacts (CIK 0000793733, 조회 2026-09-03/04)",
            "Alpha Vantage GLOBAL_QUOTE (2026-08-31 종가 근사 $94.96)",
            "WebSearch: SKYW 자사주매입 반영 주식수(2026-08월말 근사), "
            "CPA구조·경쟁구도(2026-09-03 재인용)",
        ],
        **pit,
        provenance=provenance,
    )


if __name__ == "__main__":
    inputs = build_inputs()
    result = run_analysis(inputs)
    path = save_ledger(result)
    print(f"saved: {path}")
