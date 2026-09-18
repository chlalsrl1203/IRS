"""
Nextpower Inc.(NXT, 舊 Nextracker Inc.) 정식 분석 - 2026-09-02.

경위: 연구 우선순위 큐(스크리너 tier B, Gap 추정 +16.43%p, 시총 근사
~$10.80B). FRAMEWORK_MISMATCH 8종목을 제외한 뒤 NBIX에 이은 두 번째
정량모델 적용 가능 종목.

## 원자료 - SEC XBRL companyfacts(1차자료, `SecCompanyFactsProvider`,
2026-09-02 조회, CIK 0001852131, 2021~2026 6개년 확보 - 2023-02 IPO라
공개기업 이력이 짧다(Flex Ltd에서 분사, 2026년 중 사명을 Nextracker
Inc.에서 Nextpower Inc.로 변경 - SEC 등록명 확인). 10y CAGR 산출 불가
(연도수 부족). 회계연도는 3월 말 종료(FY2026=2025-04~2026-03).

## 발견 - YoY 성장률이 매년 두 자릿수로 완만하게 감속하는 진짜 다년
가속/감속 패턴(M&A 왜곡 아님)

YoY: 2022 +21.9%, 2023 +30.5%, 2024 +31.4%, 2025 +18.4%, 2026 +20.3% -
단일연도 단계상승 없이 유틸리티스케일 태양광 트래커 시장 성장에 따른
유기적 확장으로 판단(WebSearch로 확인한 시장전망 CAGR 17.3%와 유사한
궤적).

## ⭐ 핵심 발견 - 관세·정책 리스크로 주가가 고점 대비 약 48% 하락한
상태에서 시총을 실측했다

WebSearch(2026-09-02) 확인: NXT 주가는 IPO 이후 $30->약 $160까지 상승했다가
최근 관세·재생에너지 정책 불확실성(ITC 세액공제 변경 가능성)으로 큰 폭
조정을 받아 2026-09-02 종가 $82.55 - 고점 대비 약 48% 하락한 상태다.
관세가 Q2 실적에서 300bp 마진 역풍으로 실제 작용했고, 회사는 국내
철강 조달 다각화·자체 철강프레임 사업 진출로 대응 중이다. 정책리스크가
현실화된 실제 비용(마진압박)으로 확인됐다는 점에서 순수 "공포과잉"과는
결이 다르다 - 실시간 시총(~$12.81B)을 그대로 채택했다(스크리너 근사
$10.80B보다 1.19배 큼, OKTA/MEDP/NBIX급의 극단적 괴리는 아님).

## 경쟁구도(2026-09-02 WebSearch) - 유틸리티스케일 태양광 트래커 업종

NEXTracker(NXT)가 시장선도(NXT·Array Technologies·Arctech Solar 3사가
2025년 출하량의 55~60% 점유), Array Technologies가 북미 최대 직접경쟁자,
Arctech Solar(중국계)가 글로벌 3위권. NXT·Array 둘 다 관세대응으로 국내
철강 공급망(제철소 투자 등)에 나서고 있어 업계 전반이 유사한 방식으로
정책리스크에 대응 중.

## 실행: python3 scripts/analyze_nxt_2026_09_02.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.filing_dates import pit_inputs_for
from engine.pipeline import AnalysisInputs, run_analysis, save_ledger
from engine.provenance import provenance_from_sec_facts

TICKER = "NXT"
UA = "IRS Research chlalsrl1203@gmail.com"
TODAY = "2026-09-02"

# ── SEC XBRL companyfacts 실측(2026-09-02 조회, FYE 3월) ─────────────────
REVENUE = {
    2021: 1195617000.0, 2022: 1457592000.0, 2023: 1902137000.0,
    2024: 2499841000.0, 2025: 2959197000.0, 2026: 3559390000.0,
}
OPERATING_INCOME = {
    2021: 158531000.0, 2022: 65907000.0, 2023: 168485000.0,
    2024: 587118000.0, 2025: 639112000.0, 2026: 697266000.0,
}
OPERATING_CASHFLOW = {
    2021: 94273000.0, 2022: -147113000.0, 2023: 107669000.0,
    2024: 428973000.0, 2025: 655794000.0, 2026: 562911000.0,
}
CAPEX = {
    2021: 2463000.0, 2022: 5917000.0, 2023: 3183000.0,
    2024: 6160000.0, 2025: 33921000.0, 2026: 49277000.0,
}
NET_INCOME = {
    2021: 0.0, 2022: 0.0, 2023: 1143000.0,
    2024: 306241000.0, 2025: 509168000.0, 2026: 585883000.0,
}
SBC = {
    2021: 4306000.0, 2022: 3048000.0, 2023: 31994000.0,
    2024: 56783000.0, 2025: 118880000.0, 2026: 120298000.0,
}

# ── 대차대조표(FY2026말, 2026-03-31, SEC XBRL 실측) ──────────────────────
CASH_2026 = 1094976000.0   # CashAndCashEquivalentsAtCarryingValue
DEBT_2026 = 0.0             # LongTermDebtNoncurrent/Current 둘 다 FY2025 이후 0
NET_DEBT = DEBT_2026 - CASH_2026  # -1,094,976,000(순현금)

DA_2026 = 30602000.0  # DepreciationDepletionAndAmortization(통합 태그)
EBITDA = OPERATING_INCOME[2026] + DA_2026

# ── 시가총액(2026-09-02, Alpha Vantage 종가 + 최근 분기 희석주식수) ──────
PRICE = 82.55  # Alpha Vantage GLOBAL_QUOTE, 2026-09-02 종가(latestDay)
SHARES_OUT = 155141856.0  # FY2027 Q1(2026-07-03 종료) 10-Q 희석가중평균
MARKET_CAP = PRICE * SHARES_OUT  # 약 $12.81B

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
        company_name="Nextpower Inc.",
        revenue_by_year=REVENUE,
        operating_income_by_year=OPERATING_INCOME,
        operating_cashflow_by_year=OPERATING_CASHFLOW,
        capex_by_year=CAPEX,
        market_cap=MARKET_CAP,
        net_debt=NET_DEBT,
        ebitda=EBITDA,
        risk_free_rate=RF,
        competitor_threat_weights=[0.18, 0.12],
        market_share_trend_pp_per_year=0.2,
        active_antitrust_or_regulatory_case=False,
        demand_sensitivity_pct=0.40,
        subjective_input_basis=(
            "competitor_threat_weights=[0.18(Array Technologies), 0.12(Arctech "
            "Solar)] - Array가 북미 최대 직접경쟁자(내구성·비용효율 강점), "
            "Arctech은 중국계 글로벌 3위권 - NXT·Array·Arctech 3사가 2025년 "
            "출하량의 55~60%를 점유하는 중간 집중도 시장. market_share_trend_"
            "pp_per_year=+0.2 - NXT가 시장선도 지위를 유지하며 관세대응(국내 "
            "철강조달 다각화)에도 선제적이라 완만한 양(+)값 반영(2026-09-02 "
            "WebSearch, 정량 점유율 추세는 미확보). demand_sensitivity_pct=0.40 "
            "- CLAUDE.md 업종앵커표 '자본재/데이터센터 인프라(설비투자 사이클)' "
            "버킷(VRT, 앵커 0.45)에 근접하되 소폭 낮게 - 유틸리티스케일 태양광은 "
            "데이터센터보다 최종수요처가 다변화돼 있으나 정책(ITC 세액공제)·관세 "
            "리스크에 직접 노출돼 여전히 경기·정책민감도가 높음."
        ),
        model_used="two_stage",
        model_choice_reason=(
            "trailing 매출 CAGR이 default_terminal_growth(2.0~4.5%)보다 여전히 "
            "높고, YoY 성장률이 2024년 +31.4% 정점 이후 완만히 감속 중(2025 "
            "+18.4%, 2026 +20.3%)이라 다년 수렴 경로(two_stage)가 적절하다고 "
            "판단."
        ),
        falsification_conditions=(
            "美 ITC(투자세액공제) 정책이 유틸리티스케일 태양광에 불리하게 "
            "변경되거나, 관세 마진 역풍이 300bp를 크게 상회해 지속되거나, "
            "Array Technologies 대비 수주점유율이 뚜렷이 하락하면 이 판정을 "
            "재검토할 것."
        ),
        price_at_analysis=PRICE,
        currency="USD",
        net_income_by_year=NET_INCOME,
        sbc_by_year=SBC,
        data_sources=[
            "SEC XBRL companyfacts (CIK 0001852131, 조회 2026-09-02)",
            "Alpha Vantage GLOBAL_QUOTE (2026-09-02 종가 $82.55)",
            "WebSearch: NXT 관세 리스크·Q2 FY2026 실적발표, 태양광 트래커 "
            "시장 경쟁구도(2026-09-02 재인용)",
        ],
        **pit,
        provenance=provenance,
    )


if __name__ == "__main__":
    inputs = build_inputs()
    result = run_analysis(inputs)
    path = save_ledger(result)
    print(f"saved: {path}")
