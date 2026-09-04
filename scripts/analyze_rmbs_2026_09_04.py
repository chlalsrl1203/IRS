"""
Rambus Inc.(RMBS) 정식 분석 - 2026-09-04.

경위: 연구 우선순위 큐(스크리너 tier B, Gap 추정 +10.48%p, 시총 근사
~$5.2B). FRAMEWORK_MISMATCH 20종목 + HLNE/FIVE/TW/RLI/CINF/TENB/SKYW
정식분석 완료 뒤 큐 순서상 다음 후보.

## 원자료 - SEC XBRL companyfacts(1차자료, `SecCompanyFactsProvider`,
2026-09-04 조회, CIK 0000917273, 2008~2025 18개년 확보).

## ⚠️ IDCC와 대조 - 과거엔 라이선싱 매출 변동성이 있었으나 최근엔 해소됨

2008~2018년 매출은 소송합의금·일시불 라이선스 비중이 커 들쭉날쭉했다
(2017년 $393.1M→2018년 $231.2M, -41%) - 이 프로젝트가 이미 IDCC를
FRAMEWORK_MISMATCH로 분류한 것과 같은 유형의 위험이었다. **그러나
최근(2019~2025) 회사가 반복적 로열티 기반 매출구조(DDR5 메모리인터페이스
IP·칩)로 전환하며 이 변동성이 사실상 해소됐다** - YoY 성장률이
2020~2025년 +8.4%/+35.3%/+38.6%/+1.4%/+20.7%/+27.1%로 여전히 높은
성장률이지만 IDCC처럼 단일분기 캐치업 항목이 40%를 차지하는 종류의
급락·급등은 없다. 3y/5y CAGR 창(2022→2025, 2020→2025)이 이 변동성
높았던 구간을 건드리지 않아 정량모델 적용이 타당하다고 판단했다.

## 대차대조표 - 무차입 순현금

`LongTermDebt`·`ConvertibleDebt` 계열 태그 전부 없음(무차입).
FY2025말(2025-12-31) 현금 $182.8M.

## 경쟁구도(2026-09-04 WebSearch) - AI메모리 슈퍼사이클, DDR5 메모리
인터페이스 IP·칩 업종

Rambus의 메모리 인터페이스 IP가 NVDA·AMD의 모든 AI가속기에 탑재되며
DDR5 RCD(레지스터드 클록 드라이버) 시장점유율 약 40~45%로 확대 중,
"과거 1년간의 점유율 확대가 지속될 전망이며 잠식 조짐 없음"(2026-09-04
WebSearch). Q3 2026 분기매출 20% 성장 목표. 메모리 인터페이스 칩
경쟁자는 Monolithic Power Systems·Montage Technology·Renesas·Texas
Instruments, Silicon IP 시장에서는 Cadence·Synopsys(Rambus는 특화
메모리·보안IP로 차별화, 경쟁사는 더 넓지만 덜 특화된 포트폴리오).

## 실행: python3 scripts/analyze_rmbs_2026_09_04.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.filing_dates import pit_inputs_for
from engine.pipeline import AnalysisInputs, run_analysis, save_ledger
from engine.provenance import provenance_from_sec_facts

TICKER = "RMBS"
UA = "IRS Research chlalsrl1203@gmail.com"
TODAY = "2026-09-04"

# ── SEC XBRL companyfacts 실측(2026-09-04 조회) - 최근 10개년만 사용 ──────
# (2008~2018 라이선싱 매출 변동성 구간은 위 docstring 근거로 3y/5y CAGR
# 창이 닿지 않으나, 10y CAGR 산출 시 2015년을 기준연도로 쓰게 되므로
# 안전하게 2016년부터로 제한 - 10y 미달이면 자동으로 5y 대체됨)
REVENUE = {
    2016: 336597000.0, 2017: 393096000.0, 2018: 231201000.0,
    2019: 224027000.0, 2020: 242747000.0, 2021: 328304000.0,
    2022: 454793000.0, 2023: 461117000.0, 2024: 556624000.0,
    2025: 707630000.0,
}
OPERATING_INCOME = {
    2016: 33642000.0, 2017: 54407000.0, 2018: -86967000.0,
    2019: -104539000.0, 2020: -46807000.0, 2021: 24281000.0,
    2022: 76942000.0, 2023: 153639000.0, 2024: 183009000.0,
    2025: 260218000.0,
}
OPERATING_CASHFLOW = {
    2016: 92538000.0, 2017: 117437000.0, 2018: 87117000.0,
    2019: 128535000.0, 2020: 185459000.0, 2021: 209217000.0,
    2022: 230393000.0, 2023: 195786000.0, 2024: 230599000.0,
    2025: 360019000.0,
}
CAPEX = {
    2016: 8556000.0, 2017: 9385000.0, 2018: 10762000.0,
    2019: 6472000.0, 2020: 29728000.0, 2021: 13792000.0,
    2022: 17478000.0, 2023: 23240000.0, 2024: 30697000.0,
    2025: 26842000.0,
}
NET_INCOME = {
    2016: 6820000.0, 2017: -22862000.0, 2018: -157957000.0,
    2019: -90419000.0, 2020: -43609000.0, 2021: 18334000.0,
    2022: -14310000.0, 2023: 333904000.0, 2024: 179821000.0,
    2025: 230455000.0,
}
SBC = {
    2016: 21013000.0, 2017: 27403000.0, 2018: 21736000.0,
    2019: 26476000.0, 2020: 25778000.0, 2021: 27486000.0,
    2022: 35552000.0, 2023: 45011000.0, 2024: 44880000.0,
    2025: 54267000.0,
}

# ── 대차대조표(FY2025말, 2025-12-31, SEC XBRL 실측) ───────────────────────
CASH_2025 = 182822000.0  # CashAndCashEquivalentsAtCarryingValue
DEBT_2025 = 0.0             # LongTermDebt/ConvertibleDebt 계열 태그 없음(무차입)
NET_DEBT = DEBT_2025 - CASH_2025  # -182,822,000(순현금)

DA_2025 = 11916000.0  # DepreciationDepletionAndAmortization(FY2025)
EBITDA = OPERATING_INCOME[2025] + DA_2025

# ── 시가총액(2026-09-03, Alpha Vantage 종가 + 10-Q 표지 주식수) ──────────
PRICE = 84.34  # Alpha Vantage GLOBAL_QUOTE, 2026-09-03 종가(latestDay)
SHARES_OUT = 108462000.0  # 10-Q 표지(2026-06-30 기준)
MARKET_CAP = PRICE * SHARES_OUT  # 약 $9.15B

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
        company_name="Rambus Inc.",
        revenue_by_year=REVENUE,
        operating_income_by_year=OPERATING_INCOME,
        operating_cashflow_by_year=OPERATING_CASHFLOW,
        capex_by_year=CAPEX,
        market_cap=MARKET_CAP,
        net_debt=NET_DEBT,
        ebitda=EBITDA,
        risk_free_rate=RF,
        competitor_threat_weights=[0.15, 0.10],
        market_share_trend_pp_per_year=0.5,
        active_antitrust_or_regulatory_case=False,
        demand_sensitivity_pct=0.40,
        subjective_input_basis=(
            "competitor_threat_weights=[0.15(Renesas - 메모리 인터페이스 "
            "칩 직접경쟁자, 대형 반도체기업), 0.10(Monolithic Power "
            "Systems/Montage Technology - 신흥 경쟁자)]. market_share_"
            "trend_pp_per_year=+0.5 - DDR5 RCD 시장점유율 약 40~45%로 "
            "확대 중이며 '잠식 조짐 없음'으로 평가됨(2026-09-04 "
            "WebSearch). demand_sensitivity_pct=0.40 - 메모리 반도체는 "
            "역사적으로 DRAM 가격사이클에 따라 극심한 boom/bust를 겪는 "
            "업종(이 프로젝트가 MU 스크리닝에서 이미 확인한 특성)이라 "
            "CLAUDE.md 업종앵커표 '자본재/데이터센터 인프라'(VRT, "
            "0.45)에 근접하게 채택 - AI메모리 슈퍼사이클이라는 현재의 "
            "긍정적 국면과 별개로 구조적 사이클리스크는 유지."
        ),
        model_used="two_stage",
        model_choice_reason=(
            "trailing 매출 CAGR(3y 15.85%/5y 23.85%)이 default_terminal_"
            "growth(2.0~4.5%)보다 크게 높고, AI메모리 수요 확대에 따른 "
            "가속 국면(YoY 2024 +20.7%->2025 +27.1%)이라 다년 수렴 "
            "경로(two_stage)가 적절하다고 판단."
        ),
        falsification_conditions=(
            "다음 분기 DDR5 RCD 시장점유율이 뚜렷이 하락하거나 AI 데이터"
            "센터 메모리 수요가 둔화되는 구체 증거(Q3 2026 가이던스 "
            "+20% 미달 등)가 나오면 이 판정을 재검토할 것."
        ),
        price_at_analysis=PRICE,
        currency="USD",
        net_income_by_year=NET_INCOME,
        sbc_by_year=SBC,
        data_sources=[
            "SEC XBRL companyfacts (CIK 0000917273, 조회 2026-09-04)",
            "Alpha Vantage GLOBAL_QUOTE (2026-09-03 종가 $84.34)",
            "WebSearch: RMBS 10-Q 표지 주식수(2026-06-30 기준), DDR5 "
            "시장점유율·경쟁구도(2026-09-04 재인용)",
        ],
        **pit,
        provenance=provenance,
    )


if __name__ == "__main__":
    inputs = build_inputs()
    result = run_analysis(inputs)
    path = save_ledger(result)
    print(f"saved: {path}")
