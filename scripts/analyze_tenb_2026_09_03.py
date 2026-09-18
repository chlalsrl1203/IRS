"""
Tenable Holdings, Inc.(TENB) 정식 분석 - 2026-09-03.

경위: 연구 우선순위 큐(스크리너 tier A, Gap 추정 +11.97%p, 시총 근사
~$4.1B). FRAMEWORK_MISMATCH 16종목 + HLNE/FIVE/TW/RLI/CINF 정식분석
완료, OVV 제외 뒤 큐 순서상 다음 후보.

## 원자료 - SEC XBRL companyfacts(1차자료, `SecCompanyFactsProvider`,
2026-09-03 조회, CIK 0001660280, 2016~2025 10개년 확보 - 10y CAGR
산출 가능).

## 발견 - 여전한 GAAP 영업적자, 그러나 OCF/FCF는 견조하고 개선 추세

FY2025 영업손실 -$9.2M(마진 -0.9%, FY2022 -$67.8M에서 크게 개선)이지만
OCF는 $266.75M(2025)로 꾸준히 성장 중이라 FCF(OCF-capex) 3y CAGR
27.88%/5y CAGR 42.09% - 전형적인 성장기 SaaS 패턴(영업손익은 SBC 등
비현금비용 반영해 적자, 현금창출력은 견조).

## ⚠️ SBC/FCF 극히 높음(75.3%) - 트래커 최상위권

FY2025 SBC $191.8M vs FCF0 $254.6M(OCF $266.75M - capex $12.1M) -
SBC/FCF ≈ 75.3%(PATH·ROKU급). SBC 교차검증 결과를 최우선으로 확인할 것.

## 대차대조표 - 전환사채(2021년 발행, 2026년 만기) + 단기투자 포함 순부채

`SecuredLongTermDebt`(전환사채 순장부가, 발행총액 $373.75M에서 상각) 
FY2025말 $354.2M. 현금+단기투자(`ShortTermInvestments`) 합산 $402.2M -
넷 소폭 순현금(-$48.0M).

## 경쟁구도(2026-09-03 WebSearch) - 노출관리(Exposure Management)·
취약점관리 업종

**Tenable이 IDC 세계 취약점·노출관리 시장점유율 조사에서 7년 연속
1위**(2024년 기준) - 자체 통합플랫폼 'Tenable One'이 신규영업의 41%를
차지(전년比 +8%p). 직접경쟁자는 Qualys·Rapid7(영업 현장에서 Tenable이
Rapid7의 '1순위 경쟁상대'로 확인됨 - Tenable 우위), 인접 위협은
CrowdStrike(엔드포인트 보안에서 노출관리로 확장 중)와 Palo Alto
Networks/Wiz(클라우드 보안 대형사의 잠식).

## 실행: python3 scripts/analyze_tenb_2026_09_03.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.filing_dates import pit_inputs_for
from engine.pipeline import AnalysisInputs, run_analysis, save_ledger
from engine.provenance import provenance_from_sec_facts

TICKER = "TENB"
UA = "IRS Research chlalsrl1203@gmail.com"
TODAY = "2026-09-03"

# ── SEC XBRL companyfacts 실측(2026-09-03 조회) ──────────────────────────
REVENUE = {
    2016: 124371000.0, 2017: 187727000.0, 2018: 267360000.0,
    2019: 354586000.0, 2020: 440221000.0, 2021: 541130000.0,
    2022: 683191000.0, 2023: 798710000.0, 2024: 900021000.0,
    2025: 999405000.0,
}
OPERATING_INCOME = {
    2016: -35833000.0, 2017: -40760000.0, 2018: -72581000.0,
    2019: -90799000.0, 2020: -36433000.0, 2021: -41768000.0,
    2022: -67815000.0, 2023: -52160000.0, 2024: -6856000.0,
    2025: -9168000.0,
}
OPERATING_CASHFLOW = {
    2016: -2785000.0, 2017: -6266000.0, 2018: -2559000.0,
    2019: -10744000.0, 2020: 64232000.0, 2021: 96765000.0,
    2022: 131151000.0, 2023: 149855000.0, 2024: 217476000.0,
    2025: 266750000.0,
}
CAPEX = {
    2016: 5776000.0, 2017: 2755000.0, 2018: 5733000.0,
    2019: 20674000.0, 2020: 20277000.0, 2021: 6561000.0,
    2022: 9359000.0, 2023: 1704000.0, 2024: 4247000.0,
    2025: 12102000.0,
}
NET_INCOME = {
    2016: -37208000.0, 2017: -41022000.0, 2018: -73521000.0,
    2019: -99013000.0, 2020: -42731000.0, 2021: -46677000.0,
    2022: -92222000.0, 2023: -78284000.0, 2024: -36301000.0,
    2025: -36118000.0,
}
SBC = {
    2016: 2532000.0, 2017: 7760000.0, 2018: 22875000.0,
    2019: 41610000.0, 2020: 59573000.0, 2021: 79405000.0,
    2022: 120633000.0, 2023: 145327000.0, 2024: 163515000.0,
    2025: 191813000.0,
}

# ── 대차대조표(FY2025말, 2025-12-31, SEC XBRL 실측) ───────────────────────
CASH_2025 = 187762000.0        # CashAndCashEquivalentsAtCarryingValue
SHORT_TERM_INV_2025 = 214419000.0  # ShortTermInvestments
DEBT_2025 = 354209000.0        # SecuredLongTermDebt(전환사채, 순장부가)
NET_DEBT = DEBT_2025 - (CASH_2025 + SHORT_TERM_INV_2025)  # -47,972,000(소폭 순현금)

DA_2025 = 41955000.0  # DepreciationDepletionAndAmortization(FY2025)
EBITDA = OPERATING_INCOME[2025] + DA_2025

# ── 시가총액(2026-09-02, Alpha Vantage 종가 + 10-Q 표지 주식수) ──────────
PRICE = 34.24  # Alpha Vantage GLOBAL_QUOTE, 2026-09-02 종가(latestDay)
SHARES_OUT = 110271973.0  # 10-Q 표지(2026-04-30 기준) - 2026 H1 중 추가
                            # 자사주매입(11.4M주, $230M) 진행돼 이보다
                            # 낮을 수 있음(보수적으로 이 값 사용)
MARKET_CAP = PRICE * SHARES_OUT  # 약 $3.78B

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
        company_name="Tenable Holdings, Inc.",
        revenue_by_year=REVENUE,
        operating_income_by_year=OPERATING_INCOME,
        operating_cashflow_by_year=OPERATING_CASHFLOW,
        capex_by_year=CAPEX,
        market_cap=MARKET_CAP,
        net_debt=NET_DEBT,
        ebitda=EBITDA,
        risk_free_rate=RF,
        competitor_threat_weights=[0.15, 0.15],
        market_share_trend_pp_per_year=0.5,
        active_antitrust_or_regulatory_case=False,
        demand_sensitivity_pct=0.18,
        subjective_input_basis=(
            "competitor_threat_weights=[0.15(CrowdStrike - 엔드포인트 "
            "보안에서 노출관리로 확장 중인 자본력 있는 경쟁자), "
            "0.15(Palo Alto Networks/Wiz - 클라우드 보안 대형사의 인접 "
            "시장 잠식)]. market_share_trend_pp_per_year=+0.5 - IDC "
            "취약점·노출관리 시장점유율 7년 연속 1위, 통합플랫폼 "
            "'Tenable One'이 신규영업의 41%(+8%p YoY)를 차지하며 점유율 "
            "확대 중임이 실측 확인(2026-09-03 WebSearch). demand_"
            "sensitivity_pct=0.18 - 취약점관리·보안규제준수는 재량소비재"
            "보다 훨씬 필수적 지출이라 CLAUDE.md 업종앵커표 '기업용 필수 "
            "SW·전문서비스'(0.20)보다 다소 낮게(더 필수적으로) 채택."
        ),
        model_used="two_stage",
        model_choice_reason=(
            "trailing 매출 CAGR(3y 13.52%/5y 17.82%/10y 이용가능)이 "
            "default_terminal_growth(2.0~4.5%)보다 크게 높고, 여전히 "
            "GAAP 영업적자에서 벗어나는 마진 개선 국면이라 다년 수렴 "
            "경로(two_stage)가 적절하다고 판단."
        ),
        falsification_conditions=(
            "다음 분기 순보유고객수 순증(net new customers)이 뚜렷이 "
            "둔화되거나 CrowdStrike/Wiz의 노출관리 신규제품이 구체적 "
            "고객이탈로 이어지는 증거가 나오면 이 판정을 재검토할 것. SBC "
            "차감 시 판정이 뒤집히는지(SBC/FCF 75.3%로 트래커 최상위권) "
            "반드시 함께 확인할 것."
        ),
        price_at_analysis=PRICE,
        currency="USD",
        net_income_by_year=NET_INCOME,
        sbc_by_year=SBC,
        data_sources=[
            "SEC XBRL companyfacts (CIK 0001660280, 조회 2026-09-03)",
            "Alpha Vantage GLOBAL_QUOTE (2026-09-02 종가 $34.24)",
            "WebSearch: TENB 10-Q 표지 주식수(2026-04-30 기준), IDC "
            "취약점·노출관리 시장점유율·경쟁구도(2026-09-03 재인용)",
        ],
        **pit,
        provenance=provenance,
    )


if __name__ == "__main__":
    inputs = build_inputs()
    result = run_analysis(inputs)
    path = save_ledger(result)
    print(f"saved: {path}")
