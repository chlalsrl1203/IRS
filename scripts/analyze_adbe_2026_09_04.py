"""
Adobe Inc.(ADBE) 정식 분석 - 2026-09-04.

경위: 연구 우선순위 큐 tier A, 스크리너 Gap 추정 +7.83%p. FRAMEWORK_MISMATCH
20종목 + BYD·CRM·DECK·QCOM·EAT 정식분석 + (HBAN/CNM/CVX/AXP/GLPI/IBP/APTV/
MLI 배제) 뒤 큐 순서상 다음 후보. Creative Cloud·Firefly(생성형AI) 보유.

## 원자료 - SEC XBRL companyfacts(CIK 0000796343, 2026-09-04 조회,
FY2015~FY2025 11개년 확보, 11월말 결산). M&A 왜곡·사이클성 없는 깨끗한
다년성장(3y 10.52%/5y 13.06%/10y 17.36%, 매끄러운 감속) - 오버라이드
불필요. capex/매출 비중이 오히려 최근 감소(FY2022 2.5%->FY2025 0.75%,
v3.20 재분류 불필요).

## ⚠️ 실시간 시총이 스크리너 근사치보다 22% 낮음 - AI디스럽션 서사 +
공격적 자사주매입 복합(DECK와 동일 방향)

2026-09-04 WebSearch 확인: "SaaSpocalypse" 서사로 Canva·Figma·OpenAI
Sora가 Adobe의 전문 크리에이터 기반을 잠식할 것이라는 우려로 주가가 큰
폭 하락(트레일링PER 약 12배까지 압축 - 역사적으로 프리미엄 SaaS였던
것과 대비). **그러나 실측은 AI 사업이 실제로 확장 중임을 보여준다** -
AI중심 ARR이 전년比 3배 이상($5억+), Firefly ARR +50%QoQ, 크리에이티브
프리미엄 MAU 9천만명+. 최근 FY2026 가이던스도 오히려 상향(WebSearch
확인) - "서사가 실측보다 비관적"이라는 이 프로젝트가 반복 확인해온 패턴
(BSX·NBIX 등)과 유사. 실시간 시총($1,136억)이 스크리너 근사($1,449억)
보다 22% 낮은 건 주가하락 + 발행주식감소(공격적 자사주매입, 9개월새
-5.0%) 복합효과 - DECK와 동일한 이번 세션 두 번째 역방향 사례.

## 대차대조표 - 부채증가했으나 여전히 순현금에 근접

FY2025말(2025-11-28) LongTermDebt $62.10억(FY2024대비 +$20.8억, 자사주
매입 재원 추정) - 현금+단기투자 $65.95억이 이를 상회해 순부채는 여전히
음수(-$3.85억, 사실상 순현금). EBITDA(OPINC+D&A) $95.24억.

## 실행: python3 scripts/analyze_adbe_2026_09_04.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.filing_dates import pit_inputs_for
from engine.pipeline import AnalysisInputs, run_analysis, save_ledger
from engine.provenance import provenance_from_sec_facts

TICKER = "ADBE"
UA = "IRS Research chlalsrl1203@gmail.com"
TODAY = "2026-09-04"

# ── SEC XBRL companyfacts 실측(2026-09-04 조회, CIK 0000796343) ──────────
# 회계연도는 11월말 결산(FY2025 = 2024-12~2025-11)
REVENUE = {
    2015: 4795511000.0, 2016: 5854430000.0, 2017: 7301505000.0, 2018: 9030008000.0,
    2019: 11171297000.0, 2020: 12868000000.0, 2021: 15785000000.0, 2022: 17606000000.0,
    2023: 19409000000.0, 2024: 21505000000.0, 2025: 23769000000.0,
}
OPERATING_INCOME = {
    2015: 903095000.0, 2016: 1493602000.0, 2017: 2168095000.0, 2018: 2840369000.0,
    2019: 3268121000.0, 2020: 4237000000.0, 2021: 5802000000.0, 2022: 6098000000.0,
    2023: 6650000000.0, 2024: 6741000000.0, 2025: 8706000000.0,
}
OPERATING_CASHFLOW = {
    2015: 1469502000.0, 2016: 2199728000.0, 2017: 2912853000.0, 2018: 4029304000.0,
    2019: 4421813000.0, 2020: 5727000000.0, 2021: 7230000000.0, 2022: 7838000000.0,
    2023: 7302000000.0, 2024: 8056000000.0, 2025: 10031000000.0,
}
CAPEX = {
    2015: 184936000.0, 2016: 203805000.0, 2017: 178122000.0, 2018: 266579000.0,
    2019: 394479000.0, 2020: 419000000.0, 2021: 348000000.0, 2022: 442000000.0,
    2023: 360000000.0, 2024: 183000000.0, 2025: 179000000.0,
}
NET_INCOME = {  # 참고 기록만 - is_insurer 아니므로 계산에 미사용
    2015: 629551000.0, 2016: 1168782000.0, 2017: 1693954000.0, 2018: 2590774000.0,
    2019: 2951458000.0, 2020: 5260000000.0, 2021: 4822000000.0, 2022: 4756000000.0,
    2023: 5428000000.0, 2024: 5560000000.0, 2025: 7130000000.0,
}
SBC = {
    2015: 335859000.0, 2016: 349912000.0, 2017: 451451000.0, 2018: 609562000.0,
    2019: 787705000.0, 2020: 909000000.0, 2021: 1069000000.0, 2022: 1440000000.0,
    2023: 1718000000.0, 2024: 1833000000.0, 2025: 1942000000.0,
}

# ── 대차대조표(FY2025말, 2025-11-28) ──────────────────────────────────────
DEBT_2025 = 6210000000.0  # LongTermDebt(Current=0)
CASH_AND_STI_2025 = 5431000000.0 + 1164000000.0  # Cash + ShortTermInvestments
NET_DEBT = DEBT_2025 - CASH_AND_STI_2025  # -$385,000,000(순현금)

DA_2025 = 818000000.0  # DepreciationDepletionAndAmortization(FY2025)
EBITDA = OPERATING_INCOME[2025] + DA_2025  # $9,524,000,000

# ── 시가총액(2026-09-03 Alpha Vantage 종가 + 최신 EntityCommonStockShares) ─
PRICE = 285.75  # Alpha Vantage GLOBAL_QUOTE, 2026-09-03 종가(latestDay)
SHARES_OUT = 397500000.0  # EntityCommonStockSharesOutstanding, 2026-06-11 기준(10-Q)
MARKET_CAP = PRICE * SHARES_OUT  # 약 $113.6B

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
        company_name="Adobe Inc.",
        revenue_by_year=REVENUE,
        operating_income_by_year=OPERATING_INCOME,
        operating_cashflow_by_year=OPERATING_CASHFLOW,
        capex_by_year=CAPEX,
        market_cap=MARKET_CAP,
        net_debt=NET_DEBT,
        ebitda=EBITDA,
        risk_free_rate=RF,
        competitor_threat_weights=[0.15, 0.12, 0.10],
        market_share_trend_pp_per_year=-0.3,
        active_antitrust_or_regulatory_case=False,
        demand_sensitivity_pct=0.25,
        subjective_input_basis=(
            "competitor_threat_weights=[0.15(Canva - 비전문가 친화적 "
            "생성형AI 디자인툴, 속도·템플릿에서 우위), 0.12(Figma - "
            "전문 UI/협업 디자인에서 강세), 0.10(OpenAI Sora 등 AI네이티브 "
            "신흥 크리에이티브툴 - 서사 단계)]. market_share_trend_pp_"
            "per_year=-0.3 - 'SaaSpocalypse' 서사로 실제 시장 재평가가 "
            "있었으나(주가 큰 폭 하락), AI중심 ARR이 오히려 전년比 3배로 "
            "확장 중이라(Firefly ARR +50%QoQ) 서사만큼 심각한 잠식은 아직 "
            "확인되지 않아 소폭 음수로 제한. demand_sensitivity_pct=0.25 - "
            "CLAUDE.md 앵커표 '기업용 필수 SW'(0.20)보다 약간 높게 채택 "
            "(Creative Cloud 구독의 일부는 프리랜서/개인 사용자로 기업용"
            "보다 재량소비 성격이 있음)."
        ),
        model_used="two_stage",
        model_choice_reason=(
            "trailing 매출 CAGR(3y 10.52%/5y 13.06%/10y 17.36%)이 매끄럽게 "
            "감속하는 패턴이라 default_terminal_growth로의 다년 수렴 "
            "경로(two_stage)가 적절. M&A 단계상승·사이클왜곡 없어 "
            "오버라이드 불필요."
        ),
        falsification_conditions=(
            "FY2027 실적에서 AI중심 ARR 성장이 정체되거나(현재 전년比 3배+ "
            "확장세), Creative Cloud 구독자 순증이 Canva/Figma 경쟁 심화로 "
            "마이너스 전환되면 이 판정을 재검토할 것."
        ),
        price_at_analysis=PRICE,
        currency="USD",
        net_income_by_year=NET_INCOME,
        sbc_by_year=SBC,
        data_sources=[
            "SEC XBRL companyfacts (CIK 0000796343, 조회 2026-09-04)",
            "Alpha Vantage GLOBAL_QUOTE (2026-09-03 종가 $285.75)",
            "WebSearch: AI중심 ARR·Firefly 트랙션, 경쟁구도(Canva/Figma), "
            "FY2026 가이던스 상향(2026-09-04 재인용)",
        ],
        **pit,
        provenance=provenance,
    )


if __name__ == "__main__":
    inputs = build_inputs()
    result = run_analysis(inputs)
    path = save_ledger(result)
    print(f"saved: {path}")
