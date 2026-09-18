"""
Maximus, Inc.(MMS) 정식 분석 - 2026-09-04.

경위: 연구 우선순위 큐 tier A, 스크리너 Gap 추정 +7.57%p. FRAMEWORK_MISMATCH
20종목 + BYD·CRM·DECK·QCOM·EAT·ADBE 정식분석 + (HBAN/CNM/CVX/AXP/GLPI/IBP/
APTV/MLI/MKL/FCFS/ADI 배제) 뒤 큐 순서상 다음 후보. 정부위탁 행정서비스
(Medicaid/Medicare 가입관리·실업급여 행정) 운영사.

## 원자료 - SEC XBRL companyfacts(CIK 0001032220, 2026-09-04 조회,
FY2018~FY2025 8개년만 사용 - FY2016/2017 capex 태그 미확보로 제외,
10y CAGR은 8개년<11로 자동 5y 대체됨).

## 성장 - COVID발 실업급여 수요급증(2020~2021) 이후 정상화, 창간 왜곡
크지 않음(오버라이드 불필요)

YoY 성장률이 2020년 +19.9%/2021년 +22.9%(COVID로 인한 실업급여 행정
수요 급증)에서 2025년 +2.4%까지 감속. 그러나 3y(5.46%)/5y(9.43%)/10y대체
(9.43%, 8개년<11로 5y와 동일값 채택)가 서로 크게 어긋나지 않아(BYD·CNM급
왜곡 아님) 오버라이드 불필요.

## ⚠️ 주가 -33%YTD - VA(재향군인부) 실적인센티브 일시중단이 직접 원인
(2026-09-04 WebSearch 확인)

FY2026 실적발표에서 재향군인부(VA) Medical Disability Exam 프로그램
실적인센티브가 일시 중단돼 이익·FCF 가이던스가 하향됐다 - 구체적이고
확인된 단기 악재. **동시에 장기 순풍도 실측 확인됨**: $504억 규모 영업
파이프라인, AI 활용 신규입찰 비중 75~80%(5개 계약에서 영업마진 +3.5%p
개선 실증), FY2027부터 시행되는 신규 연방법(Medicaid 근로요건·SNAP
지급정합성 강화)이 주정부의 컴플라이언스·행정서비스 수요를 구조적으로
확대시킬 전망. 실시간 시총($30.59억)이 스크리너 근사($38.0억)보다 20%
낮음(주가하락+자사주매입 복합, DECK와 동일 방향).

## 대차대조표 - 중간 레버리지(net_debt/EBITDA≈1.95x)

FY2025말(2025-09-30) LongTermDebt 총 $13.34억, 현금 $2.22억, 순부채
$11.12억. EBITDA(OPINC+D&A) $5.70억.

## 실행: python3 scripts/analyze_mms_2026_09_04.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.filing_dates import pit_inputs_for
from engine.pipeline import AnalysisInputs, run_analysis, save_ledger
from engine.provenance import provenance_from_sec_facts

TICKER = "MMS"
UA = "IRS Research chlalsrl1203@gmail.com"
TODAY = "2026-09-04"

# ── SEC XBRL companyfacts 실측(2026-09-04 조회, CIK 0001032220) ──────────
# 회계연도는 9월말 결산(FY2025 = 2024-10~2025-09). FY2016/2017은 capex
# 태그 미확보로 제외(2018년부터 사용).
REVENUE = {
    2018: 2392236000.0, 2019: 2886815000.0, 2020: 3461537000.0, 2021: 4254485000.0,
    2022: 4631018000.0, 2023: 4904728000.0, 2024: 5306197000.0, 2025: 5431276000.0,
}
OPERATING_INCOME = {
    2018: 295483000.0, 2019: 317107000.0, 2020: 288278000.0, 2021: 408530000.0,
    2022: 325898000.0, 2023: 294794000.0, 2024: 488499000.0, 2025: 528289000.0,
}
OPERATING_CASHFLOW = {
    2018: 323525000.0, 2019: 356727000.0, 2020: 244592000.0, 2021: 517322000.0,
    2022: 289839000.0, 2023: 314340000.0, 2024: 515258000.0, 2025: 429372000.0,
}
CAPEX = {
    2018: 26520000.0, 2019: 66846000.0, 2020: 40707000.0, 2021: 36565000.0,
    2022: 56145000.0, 2023: 90695000.0, 2024: 114190000.0, 2025: 63213000.0,
}
NET_INCOME = {  # 참고 기록만 - is_insurer 아니므로 계산에 미사용
    2018: 220751000.0, 2019: 240824000.0, 2020: 214509000.0, 2021: 291200000.0,
    2022: 203828000.0, 2023: 161792000.0, 2024: 306914000.0, 2025: 319034000.0,
}
SBC = {
    2018: 20238000.0, 2019: 20774000.0, 2020: 23708000.0, 2021: 28554000.0,
    2022: 30476000.0, 2023: 29522000.0, 2024: 35349000.0, 2025: 41182000.0,
}

# ── 대차대조표(FY2025말, 2025-09-30) ──────────────────────────────────────
DEBT_2025 = 1281593000.0 + 52680000.0  # LongTermDebtNoncurrent + LongTermDebtCurrent
CASH_2025 = 222351000.0  # CashAndCashEquivalentsAtCarryingValue
NET_DEBT = DEBT_2025 - CASH_2025  # $1,111,922,000

DA_2025 = 41669000.0  # DepreciationAndAmortization(FY2025)
EBITDA = OPERATING_INCOME[2025] + DA_2025  # $569,958,000

# ── 시가총액(2026-09-03 Alpha Vantage 종가 + 최신 EntityCommonStockShares) ─
PRICE = 58.43  # Alpha Vantage GLOBAL_QUOTE, 2026-09-03 종가(latestDay)
SHARES_OUT = 52357763.0  # EntityCommonStockSharesOutstanding, 2026-08-03 기준(10-Q)
MARKET_CAP = PRICE * SHARES_OUT  # 약 $3.06B

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
        company_name="Maximus, Inc.",
        revenue_by_year=REVENUE,
        operating_income_by_year=OPERATING_INCOME,
        operating_cashflow_by_year=OPERATING_CASHFLOW,
        capex_by_year=CAPEX,
        market_cap=MARKET_CAP,
        net_debt=NET_DEBT,
        ebitda=EBITDA,
        risk_free_rate=RF,
        competitor_threat_weights=[0.12, 0.10],
        market_share_trend_pp_per_year=0.0,
        active_antitrust_or_regulatory_case=False,
        demand_sensitivity_pct=0.12,
        subjective_input_basis=(
            "competitor_threat_weights=[0.12(Conduent/Deloitte 등 대형 "
            "정부위탁 BPO 경쟁자), 0.10(Accenture Federal Services)]. "
            "market_share_trend_pp_per_year=0.0 - 구체적 점유율 손실/확대 "
            "데이터 미확인이라 중립. demand_sensitivity_pct=0.12 - "
            "정부계약 기반 필수행정서비스라 CLAUDE.md 앵커표 '필수/의무 "
            "지출(정부SW·인터넷 인프라)' 0.08에 근접하되, 계약 갱신·예산"
            "삭감 리스크(VA 프로그램 일시중단 실측 확인)를 반영해 소폭 "
            "상향."
        ),
        model_used="two_stage",
        model_choice_reason=(
            "trailing 매출 CAGR(3y 5.46%/5y 9.43%)이 default_terminal_"
            "growth(2.0~4.5%)를 상회하고, FY2027부터 시행되는 신규 연방법"
            "(Medicaid 근로요건·SNAP 강화)이 향후 수요확대 촉매로 확인돼 "
            "다년 수렴 경로(two_stage)가 적절. 창간 편차가 크지 않아"
            "(3y/5y/10y대체 전부 5~10%대) 오버라이드 불필요."
        ),
        falsification_conditions=(
            "VA Medical Disability Exam 프로그램 실적인센티브가 다음 2개 "
            "분기 내 재개되지 않거나, FY2027 신규 연방법(Medicaid 근로요건 "
            "등) 시행이 지연되어 예상된 수요확대가 실현되지 않으면 이 "
            "판정을 재검토할 것."
        ),
        price_at_analysis=PRICE,
        currency="USD",
        net_income_by_year=NET_INCOME,
        sbc_by_year=SBC,
        data_sources=[
            "SEC XBRL companyfacts (CIK 0001032220, 조회 2026-09-04)",
            "Alpha Vantage GLOBAL_QUOTE (2026-09-03 종가 $58.43)",
            "WebSearch: VA 프로그램 일시중단, FY2026 가이던스, 영업파이프라인·"
            "AI활용 신규입찰 비중·FY2027 신규연방법(2026-09-04 재인용)",
        ],
        **pit,
        provenance=provenance,
    )


if __name__ == "__main__":
    inputs = build_inputs()
    result = run_analysis(inputs)
    path = save_ledger(result)
    print(f"saved: {path}")
