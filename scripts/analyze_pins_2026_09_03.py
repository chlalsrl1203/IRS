"""
Pinterest, Inc.(PINS) 정식 분석 - 2026-09-03.

경위: 연구 우선순위 큐(스크리너 tier A, Gap 추정 +14.46%p, 시총 근사
~$18.70B). FRAMEWORK_MISMATCH 11종목(LNTH/EQT/CDE/CHDN/VICI/COP/DINO/
EOG/COF/IDCC/EXE) 제외 뒤 큐 순서상 다음 후보.

## 원자료 - SEC XBRL companyfacts(1차자료, `SecCompanyFactsProvider`,
2026-09-03 조회, CIK 0001506293, 2017~2025 9개년 확보 - 10y CAGR 산출
불가). 2019년 영업손실 -$1.39B/순손실 -$1.36B는 IPO 관련 대규모 SBC 비용
일회성 인식(RSU 베스팅 가속) 추정 - FCF(OCF-capex)에는 영향 없음(2019
OCF는 소폭 플러스 $0.66M).

## 발견 - COVID붐 이후 깨끗한 감속->재가속 패턴(M&A 왜곡 없음)

YoY: 2018~2021 48~60%대 고성장(COVID 온라인쇼핑 붐) -> 2022~2023 약
9%대로 급감속 -> 2024~2025 19.3%/15.8%로 재가속. 광고매출이 경쟁사
(Snap/X/LinkedIn) 대비 빠르게 성장 중이라는 외부평가와 일치.

## ⚠️ 발견 - SBC/FCF가 70%대로 트래커 최상위권(PATH급)

FY2025 SBC $880.5M vs FCF0 $1,251.9M(OCF $1,284.3M - capex $32.4M) -
SBC/FCF ≈ 70.3%. SBC 교차검증 결과를 최우선으로 확인할 것.

## 경쟁구도(2026-09-03 WebSearch) - 소셜미디어 광고 업종

Meta가 소셜광고 지출의 약 39%로 압도적 1위, Pinterest는 나머지 14%
파이에 속하나(Snapchat/X/기타 포함) 시각적 발견/쇼핑 특화 포지셔닝으로
차별화 - 2025년 광고매출 $4.6B(+31%YoY)로 Snapchat/X/LinkedIn보다 빠른
성장률을 2년 연속 기록. 리테일/홈/라이프스타일 카테고리에서 고의도
트래픽 창출력이 핵심 경쟁우위로 평가된다.

## 실행: python3 scripts/analyze_pins_2026_09_03.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.filing_dates import pit_inputs_for
from engine.pipeline import AnalysisInputs, run_analysis, save_ledger
from engine.provenance import provenance_from_sec_facts

TICKER = "PINS"
UA = "IRS Research chlalsrl1203@gmail.com"
TODAY = "2026-09-03"

# ── SEC XBRL companyfacts 실측(2026-09-03 조회) ──────────────────────────
REVENUE = {
    2017: 472852000.0, 2018: 755932000.0, 2019: 1142761000.0,
    2020: 1692658000.0, 2021: 2578027000.0, 2022: 2802574000.0,
    2023: 3055071000.0, 2024: 3646166000.0, 2025: 4221767000.0,
}
OPERATING_INCOME = {
    2017: -137934000.0, 2018: -74721000.0, 2019: -1388866000.0,
    2020: -142504000.0, 2021: 326187000.0, 2022: -101677000.0,
    2023: -125678000.0, 2024: 179817000.0, 2025: 319883000.0,
}
OPERATING_CASHFLOW = {
    2017: -102913000.0, 2018: -60369000.0, 2019: 657000.0,
    2020: 28826000.0, 2021: 752907000.0, 2022: 469202000.0,
    2023: 612961000.0, 2024: 964594000.0, 2025: 1284264000.0,
}
CAPEX = {
    2017: 41192000.0, 2018: 22194000.0, 2019: 33783000.0,
    2020: 17401000.0, 2021: 9031000.0, 2022: 28984000.0,
    2023: 8063000.0, 2024: 24606000.0, 2025: 32375000.0,
}
NET_INCOME = {
    2017: -130044000.0, 2018: -62974000.0, 2019: -1361371000.0,
    2020: -128323000.0, 2021: 316438000.0, 2022: -96047000.0,
    2023: -35610000.0, 2024: 1862106000.0, 2025: 416855000.0,
}
SBC = {
    2017: 28804000.0, 2018: 14859000.0, 2019: 1377781000.0,
    2020: 321020000.0, 2021: 415382000.0, 2022: 497123000.0,
    2023: 647860000.0, 2024: 765795000.0, 2025: 880463000.0,
}

# ── 대차대조표(FY2025말, 2025-12-31, SEC XBRL 실측) ──────────────────────
CASH_2025 = 969342000.0   # CashAndCashEquivalentsAtCarryingValue
DEBT_2025 = 0.0             # LongTermDebtNoncurrent/Current 태그 자체가 없음(무차입)
NET_DEBT = DEBT_2025 - CASH_2025  # -969,342,000(순현금)

DA_2025 = 25151000.0  # DepreciationDepletionAndAmortization(통합 태그)
EBITDA = OPERATING_INCOME[2025] + DA_2025

# ── 시가총액(2026-09-02, Alpha Vantage 종가 + 최근 분기 희석주식수) ──────
PRICE = 21.22  # Alpha Vantage GLOBAL_QUOTE, 2026-09-02 종가(latestDay)
SHARES_OUT = 562913000.0  # FY2026 Q2(2026-06-30 종료) 10-Q 희석가중평균
MARKET_CAP = PRICE * SHARES_OUT  # 약 $11.95B

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
        company_name="Pinterest, Inc.",
        revenue_by_year=REVENUE,
        operating_income_by_year=OPERATING_INCOME,
        operating_cashflow_by_year=OPERATING_CASHFLOW,
        capex_by_year=CAPEX,
        market_cap=MARKET_CAP,
        net_debt=NET_DEBT,
        ebitda=EBITDA,
        risk_free_rate=RF,
        competitor_threat_weights=[0.30, 0.10],
        market_share_trend_pp_per_year=0.5,
        active_antitrust_or_regulatory_case=False,
        demand_sensitivity_pct=0.35,
        subjective_input_basis=(
            "competitor_threat_weights=[0.30(Meta), 0.10(Snap)] - Meta가 "
            "소셜광고 지출의 약 39%로 압도적 최대 위협, Snap은 규모가 "
            "유사한 직접경쟁자로 낮게 반영. market_share_trend_pp_per_year="
            "+0.5 - Pinterest 광고매출이 Snapchat/X/LinkedIn보다 빠른 "
            "성장률(+31%YoY)을 2년 연속 기록해 파이 내 상대점유율이 "
            "확대되는 추세로 판단(2026-09-03 WebSearch). demand_sensitivity_"
            "pct=0.35 - CLAUDE.md 업종앵커표 '광고·전자상거래·경기민감 "
            "산업재' 버킷(PDD·TTD·PH, 앵커 0.35) 적용 - 디지털광고는 "
            "경기 침체 시 예산삭감 1순위."
        ),
        model_used="two_stage",
        model_choice_reason=(
            "trailing 매출 CAGR(3y 14.63%/5y 20.06%)이 default_terminal_growth"
            "(2.0~4.5%)보다 여전히 높고, YoY 성장률이 2022~2023년 감속(약 9%대) "
            "이후 2024~2025년 재가속(+19.3%/+15.8%)하는 비단조 패턴이라 다년 "
            "수렴 경로(two_stage)가 적절하다고 판단."
        ),
        falsification_conditions=(
            "다음 분기 광고매출 성장률이 Snap/X 등 경쟁사 대비 다시 둔화되거나, "
            "Meta·TikTok의 쇼핑/발견 기능 강화로 Pinterest 고유의 고의도 트래픽 "
            "차별화가 약화되는 구체 증거가 나오면 이 판정을 재검토할 것. SBC "
            "차감 시 판정이 뒤집히는지(SBC/FCF 70.3%로 트래커 최상위권) 반드시 "
            "함께 확인할 것."
        ),
        price_at_analysis=PRICE,
        currency="USD",
        net_income_by_year=NET_INCOME,
        sbc_by_year=SBC,
        data_sources=[
            "SEC XBRL companyfacts (CIK 0001506293, 조회 2026-09-03)",
            "Alpha Vantage GLOBAL_QUOTE (2026-09-02 종가 $21.22)",
            "WebSearch: PINS 광고매출 성장률·경쟁구도(Meta/Snap/TikTok, "
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
