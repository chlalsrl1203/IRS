"""
DocuSign, Inc.(DOCU) 정식 분석 - 2026-09-03.

경위: 연구 우선순위 큐(스크리너 tier A, Gap 추정 +12.12%p, 시총 근사
~$15.1B). FRAMEWORK_MISMATCH 16종목 + HLNE/FIVE/TW/RLI 정식분석 완료 뒤
큐 순서상 다음 후보.

## 원자료 - SEC XBRL companyfacts(1차자료, `SecCompanyFactsProvider`,
2026-09-03 조회, CIK 0001261333, FYE 1월 31일, 2017~2026 10개년 확보 -
10y CAGR 산출 가능).

## 발견 - 흑자전환 이후 안정적 다년 성장, M&A 왜곡 없음

FY2024(영업이익 최초 흑자 $31.6M)까지 만성적 영업적자를 겪은 뒤
FY2025 $199.9M/FY2026 $298.6M로 빠르게 개선. FCF(OCF-capex) 3y CAGR
35.10%/5y CAGR 37.63%, 매출 3y CAGR 8.57%/5y CAGR 17.26% - 단일연도
단계상승 없는 유기적 성장.

## 대차대조표 - 전환사채 완전상환, 무차입 순현금

2018년 발행 전환사채($722.9M, FY2023말 잔액)가 **FY2024(2024-01-31)에
$0으로 전액 상환/전환 완료** - 현재 무차입 구조. FY2026말(2026-01-31)
현금 $602.4M.

## ⚠️ SBC/FCF 매우 높음(58.8%) - WDAY/OKTA급

FY2026 SBC $622.3M vs FCF0 $1,058.6M(OCF $1,165.0M - capex $106.4M) -
SBC/FCF ≈ 58.8%. SBC 교차검증 결과를 최우선으로 확인할 것(WDAY가 이
경로로 판정이 실제 뒤집힌 선례).

## 경쟁구도(2026-09-03 WebSearch) - 전자서명·계약관리(CLM) SaaS 업종

DocuSign이 e서명 시장 56.84% 점유(2위 SignRequest 10.60%, Adobe Sign
10.15%)로 여전히 압도적 1위 - 글로벌 e서명 시장은 2025년 $70억에서
2030년 $350억+로 성장 전망. 다만 업계 전반에서 "AI 에이전트가 계약서
작성·검토·서명 워크플로 전체를 자동화한다"는 구조적 위협 서사가
제기되는 중(2026년 시장 자체가 "그 어느 때보다 경쟁적"으로 평가) -
아직 구체적 점유율 잠식 증거는 확인되지 않았으나(WDAY의 AI네이티브
경쟁 서사와 유사한 계열) 서사 자체는 실재하는 리스크로 남김.

## 실행: python3 scripts/analyze_docu_2026_09_03.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.filing_dates import pit_inputs_for
from engine.pipeline import AnalysisInputs, run_analysis, save_ledger
from engine.provenance import provenance_from_sec_facts

TICKER = "DOCU"
UA = "IRS Research chlalsrl1203@gmail.com"
TODAY = "2026-09-03"

# ── SEC XBRL companyfacts 실측(2026-09-03 조회, FYE 1월 31일) ────────────
REVENUE = {
    2017: 381459000.0, 2018: 518504000.0, 2019: 700969000.0,
    2020: 973971000.0, 2021: 1453047000.0, 2022: 2107213000.0,
    2023: 2515915000.0, 2024: 2761882000.0, 2025: 2976739000.0,
    2026: 3219500000.0,
}
OPERATING_INCOME = {
    2017: -115817000.0, 2018: -51653000.0, 2019: -426323000.0,
    2020: -193509000.0, 2021: -173855000.0, 2022: -61884000.0,
    2023: -88031000.0, 2024: 31634000.0, 2025: 199928000.0,
    2026: 298579000.0,
}
OPERATING_CASHFLOW = {
    2017: -4790000.0, 2018: 54979000.0, 2019: 76086000.0,
    2020: 115696000.0, 2021: 296954000.0, 2022: 506467000.0,
    2023: 506759000.0, 2024: 979526000.0, 2025: 1017272000.0,
    2026: 1165007000.0,
}
CAPEX = {
    2017: 43330000.0, 2018: 18929000.0, 2019: 30413000.0,
    2020: 72046000.0, 2021: 82395000.0, 2022: 61396000.0,
    2023: 77654000.0, 2024: 92391000.0, 2025: 96988000.0,
    2026: 106445000.0,
}
NET_INCOME = {
    2017: -115412000.0, 2018: -52276000.0, 2019: -426458000.0,
    2020: -208359000.0, 2021: -243267000.0, 2022: -69976000.0,
    2023: -97454000.0, 2024: 73980000.0, 2025: 1067885000.0,
    2026: 309085000.0,
}
SBC = {
    2017: 35443000.0, 2018: 29747000.0, 2019: 410978000.0,
    2020: 206404000.0, 2021: 286877000.0, 2022: 408542000.0,
    2023: 538726000.0, 2024: 616847000.0, 2025: 610335000.0,
    2026: 622321000.0,
}

# ── 대차대조표(FY2026말, 2026-01-31, SEC XBRL 실측) ───────────────────────
CASH_2026 = 602442000.0  # CashAndCashEquivalentsAtCarryingValue
DEBT_2026 = 0.0             # ConvertibleDebtCurrent/Noncurrent 둘 다 FY2024 이후 0(전액상환)
NET_DEBT = DEBT_2026 - CASH_2026  # -602,442,000(순현금)

DA_2026 = 116081000.0  # DepreciationDepletionAndAmortization(FY2026)
EBITDA = OPERATING_INCOME[2026] + DA_2026

# ── 시가총액(2026-09-02, Alpha Vantage 종가 + FY2026 10-K 표지 주식수) ───
PRICE = 65.39  # Alpha Vantage GLOBAL_QUOTE, 2026-09-02 종가(latestDay)
SHARES_OUT = 194427928.0  # FY2026 10-K 표지(2026-02-28 기준)
MARKET_CAP = PRICE * SHARES_OUT  # 약 $12.71B

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
        company_name="DocuSign, Inc.",
        revenue_by_year=REVENUE,
        operating_income_by_year=OPERATING_INCOME,
        operating_cashflow_by_year=OPERATING_CASHFLOW,
        capex_by_year=CAPEX,
        market_cap=MARKET_CAP,
        net_debt=NET_DEBT,
        ebitda=EBITDA,
        risk_free_rate=RF,
        competitor_threat_weights=[0.15, 0.10],
        market_share_trend_pp_per_year=-0.2,
        active_antitrust_or_regulatory_case=False,
        demand_sensitivity_pct=0.20,
        subjective_input_basis=(
            "competitor_threat_weights=[0.15(Adobe Sign - Acrobat 번들로 "
            "확보한 자원력 있는 경쟁자), 0.10(PandaDoc 등 신흥 경쟁자 + "
            "AI 에이전트 기반 계약워크플로 자동화 서사)]. market_share_"
            "trend_pp_per_year=-0.2 - DocuSign이 여전히 56.84%로 압도적 "
            "1위 유지 중이나(2026-09-03 WebSearch), 'AI 에이전트가 계약 "
            "작성·검토·서명을 통째로 자동화한다'는 구조적 위협 서사가 "
            "업계 전반에 제기 중이라 WDAY 선례와 동일하게 완만한 음수값 "
            "채택(구체적 점유율 잠식 증거는 아직 없음). demand_"
            "sensitivity_pct=0.20 - 전자서명·계약관리는 기업 워크플로에 "
            "깊이 내재화돼 전환비용이 높은 필수 SW라 CLAUDE.md 업종앵커표 "
            "'기업용 필수 SW·전문서비스'(0.20) 그대로 적용."
        ),
        model_used="two_stage",
        model_choice_reason=(
            "trailing 매출 CAGR(3y 8.57%/5y 17.26%)이 default_terminal_"
            "growth(2.0~4.5%)보다 높고, FY2024 흑자전환 이후 마진 개선이 "
            "지속되는 국면이라 다년 수렴 경로(two_stage)가 적절하다고 "
            "판단."
        ),
        falsification_conditions=(
            "다음 분기 신규계약 순증(net new ARR)이 뚜렷이 둔화되거나, "
            "AI 네이티브 계약워크플로 경쟁자의 실제 트랙션(ARR·고객사 "
            "이탈률)이 구체적으로 확인되면 이 판정을 재검토할 것. SBC "
            "차감 시 판정이 뒤집히는지(SBC/FCF 58.8%로 WDAY급) 반드시 "
            "함께 확인할 것."
        ),
        price_at_analysis=PRICE,
        currency="USD",
        net_income_by_year=NET_INCOME,
        sbc_by_year=SBC,
        data_sources=[
            "SEC XBRL companyfacts (CIK 0001261333, 조회 2026-09-03)",
            "Alpha Vantage GLOBAL_QUOTE (2026-09-02 종가 $65.39)",
            "WebSearch: DOCU FY2026 10-K 표지 주식수(2026-02-28 기준), "
            "e서명 시장 경쟁구도(2026-09-03 재인용)",
        ],
        **pit,
        provenance=provenance,
    )


if __name__ == "__main__":
    inputs = build_inputs()
    result = run_analysis(inputs)
    path = save_ledger(result)
    print(f"saved: {path}")
