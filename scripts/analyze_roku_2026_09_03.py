"""
Roku, Inc.(ROKU) 정식 분석 - 2026-09-03.

경위: 연구 우선순위 큐(스크리너 tier B, Gap 추정 +14.15%p, 시총 근사
~$9.70B). FRAMEWORK_MISMATCH 12종목(LNTH/EQT/CDE/CHDN/VICI/COP/DINO/
EOG/COF/IDCC/EXE/XYZ) 제외 뒤 큐 순서상 다음 후보.

## 원자료 - SEC XBRL companyfacts(1차자료, `SecCompanyFactsProvider`,
2026-09-03 조회, CIK 0001428439, 2015~2025 11개년 확보 - 10y CAGR 산출
가능).

## 발견 - COVID붐 이후 깨끗한 다년 감속 패턴(M&A 왜곡 없음)

YoY: 2018~2021 44.8%~57.5%(COVID 스트리밍 붐) -> 2022~2025 11.5%~18.0%로
안정화. 단일연도 단계상승 없이 유기적 성장곡선.

## ⭐ 핵심 발견 - 스크리너 시총 근사치가 실시간 시총의 40%에 불과했다

실시간 시총(~$23.95B, Alpha Vantage 종가 + 최근 분기 희석주식수)이
스크리너 근사(~$9.70B)의 2.47배 - OKTA/MEDP/NBIX/NXT급의 극단적 float
스냅샷 노후화 사례.

## ⚠️ 발견 - SBC/FCF가 74%로 트래커 최상위권(PATH/PINS급)

FY2025 SBC $354.2M vs FCF0 $478.4M(OCF $483.7M - capex $5.3M) - SBC/FCF
≈ 74.0%. SBC 교차검증 결과를 최우선으로 확인할 것.

## 경쟁구도(2026-09-03 WebSearch) - 커넥티드TV(CTV) 플랫폼 업종

Roku가 북미(28~36% 점유, 지표별 상이)·중남미(42%) 선두, Samsung Tizen이
2위(23%, EMEA에서는 1위 28%) - Amazon Fire TV가 북미에서 QoQ +18%로
가장 빠르게 성장 중인 위협. 5대 플랫폼(Roku/Samsung/LG/Amazon/Vizio)
모두 무료 광고기반 스트리밍(FAST) 서비스를 운영하는 구조적 경쟁시장.

## 실행: python3 scripts/analyze_roku_2026_09_03.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.filing_dates import pit_inputs_for
from engine.pipeline import AnalysisInputs, run_analysis, save_ledger
from engine.provenance import provenance_from_sec_facts

TICKER = "ROKU"
UA = "IRS Research chlalsrl1203@gmail.com"
TODAY = "2026-09-03"

# ── SEC XBRL companyfacts 실측(2026-09-03 조회) ──────────────────────────
REVENUE = {
    2015: 319857000.0, 2016: 398649000.0, 2017: 512763000.0,
    2018: 742506000.0, 2019: 1128921000.0, 2020: 1778388000.0,
    2021: 2764584000.0, 2022: 3126534000.0, 2023: 3484619000.0,
    2024: 4112898000.0, 2025: 4737251000.0,
}
OPERATING_INCOME = {
    2015: -37552000.0, 2016: -43361000.0, 2017: -19616000.0,
    2018: -13296000.0, 2019: -65059000.0, 2020: -20253000.0,
    2021: 235100000.0, 2022: -530888000.0, 2023: -792377000.0,
    2024: -218167000.0, 2025: -5624000.0,
}
OPERATING_CASHFLOW = {
    2015: -32604000.0, 2016: -32463000.0, 2017: 37292000.0,
    2018: 13922000.0, 2019: 13707000.0, 2020: 148192000.0,
    2021: 228081000.0, 2022: 11795000.0, 2023: 255856000.0,
    2024: 218045000.0, 2025: 483718000.0,
}
CAPEX = {
    2015: 5019000.0, 2016: 8596000.0, 2017: 9229000.0,
    2018: 18327000.0, 2019: 77180000.0, 2020: 82382000.0,
    2021: 40041000.0, 2022: 161696000.0, 2023: 82619000.0,
    2024: 5061000.0, 2025: 5280000.0,
}
NET_INCOME = {
    2015: -40611000.0, 2016: -42758000.0, 2017: -63509000.0,
    2018: -8857000.0, 2019: -59937000.0, 2020: -17507000.0,
    2021: 242385000.0, 2022: -498005000.0, 2023: -709561000.0,
    2024: -129386000.0, 2025: 88361000.0,
}
SBC = {
    2015: 5284000.0, 2016: 8206000.0, 2017: 10953000.0,
    2018: 37674000.0, 2019: 85175000.0, 2020: 134076000.0,
    2021: 187532000.0, 2022: 359931000.0, 2023: 370130000.0,
    2024: 384662000.0, 2025: 354169000.0,
}

# ── 대차대조표(FY2025말, 2025-12-31, SEC XBRL 실측) ──────────────────────
CASH_2025 = 1587068000.0   # CashAndCashEquivalentsAtCarryingValue
DEBT_2025 = 0.0              # LongTermDebtNoncurrent/Current 둘 다 FY2023 이후 0(무차입)
NET_DEBT = DEBT_2025 - CASH_2025  # -1,587,068,000(순현금)

DA_2025 = 45600000.0  # DepreciationDepletionAndAmortization(통합 태그)
EBITDA = OPERATING_INCOME[2025] + DA_2025

# ── 시가총액(2026-09-02, Alpha Vantage 종가 + 최근 분기 희석주식수) ──────
PRICE = 157.70  # Alpha Vantage GLOBAL_QUOTE, 2026-09-02 종가(latestDay)
SHARES_OUT = 151895000.0  # FY2026 Q2(2026-06-30 종료) 10-Q 희석가중평균
MARKET_CAP = PRICE * SHARES_OUT  # 약 $23.95B

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
        company_name="Roku, Inc.",
        revenue_by_year=REVENUE,
        operating_income_by_year=OPERATING_INCOME,
        operating_cashflow_by_year=OPERATING_CASHFLOW,
        capex_by_year=CAPEX,
        market_cap=MARKET_CAP,
        net_debt=NET_DEBT,
        ebitda=EBITDA,
        risk_free_rate=RF,
        competitor_threat_weights=[0.20, 0.15],
        market_share_trend_pp_per_year=-0.3,
        active_antitrust_or_regulatory_case=False,
        demand_sensitivity_pct=0.35,
        subjective_input_basis=(
            "competitor_threat_weights=[0.20(Samsung Tizen), 0.15(Amazon Fire "
            "TV)] - Samsung이 강력한 설치기반(EMEA 1위 28%)의 2위 경쟁자, "
            "Amazon Fire TV는 북미에서 QoQ +18%로 가장 빠르게 성장 중인 위협이라 "
            "비중있게 반영. market_share_trend_pp_per_year=-0.3 - Roku가 "
            "북미/중남미 선두를 유지하나 Amazon의 빠른 성장세를 감안해 완만한 "
            "음(-)값(2026-09-03 WebSearch, Parks Associates/Pixalate 조사). "
            "demand_sensitivity_pct=0.35 - CLAUDE.md 업종앵커표 '광고·전자상거래·"
            "경기민감 산업재' 버킷(PDD·TTD·PH, 앵커 0.35) 적용 - CTV 광고매출은 "
            "경기침체 시 예산삭감 대상."
        ),
        model_used="two_stage",
        model_choice_reason=(
            "trailing 매출 CAGR(3y 14.86%/5y 21.65%/10y 30.94%)이 "
            "default_terminal_growth(2.0~4.5%)보다 여전히 높고, YoY 성장률이 "
            "COVID붐(2018~2021 44.8~57.5%) 이후 안정화(2022~2025 11.5~18.0%)된 "
            "성숙화 국면이라 다년 수렴 경로(two_stage)가 적절하다고 판단."
        ),
        falsification_conditions=(
            "다음 분기 스트리밍 시간 점유율(SOV)이 Amazon Fire TV 대비 뚜렷이 "
            "하락하거나, 광고매출 성장률이 가이던스를 크게 밑돌면 이 판정을 "
            "재검토할 것. SBC 차감 시 판정이 뒤집히는지(SBC/FCF 74.0%로 트래커 "
            "최상위권) 반드시 함께 확인할 것."
        ),
        price_at_analysis=PRICE,
        currency="USD",
        net_income_by_year=NET_INCOME,
        sbc_by_year=SBC,
        data_sources=[
            "SEC XBRL companyfacts (CIK 0001428439, 조회 2026-09-03)",
            "Alpha Vantage GLOBAL_QUOTE (2026-09-02 종가 $157.70)",
            "WebSearch: ROKU CTV 플랫폼 경쟁구도(Parks Associates/Pixalate, "
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
