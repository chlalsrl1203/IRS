"""
Deckers Brands(DECK) 정식 분석 - 2026-09-04.

경위: 연구 우선순위 큐 tier A, 스크리너 Gap 추정 +9.83%p. FRAMEWORK_MISMATCH
20종목 + BYD·CRM 정식분석 완료 뒤 큐 순서상 다음 후보. HOKA·UGG 브랜드 보유
신발/의류업체. (이후 분석부터 종목당 전담 리서치 에이전트 생략, 직접
WebSearch로 대체 - 2026-09-04 효율화 결정)

## 원자료 - SEC XBRL companyfacts(CIK 0000910521, 2026-09-04 조회).
매출은 2017년부터만 확보(2015/2016 결측, 태그 미발견) - 10y CAGR 산출
불가해 5y로 자동 대체됨(엔진 표준 경고).

## 무차입 순현금 - 대형 자사주매입도 부채조달 없이 진행

`LongTermDebt` 계열 태그 전무(무차입). 현금 $19.07억(FY2026말, 2026-03-31).
FY2026 중 $10.75억 자사주매입 집행(WebSearch) - CRM(부채조달)과 정반대로
순수 현금여력으로 조달, 레버리지 리스크 없음.

## 성장 - M&A 왜곡 없는 깨끗한 다년 성장(3y 14.69%/5y 16.54%), FY2026
성장 둔화는 일시적 도매 타이밍 이슈로 설명됨(WebSearch)

capex/매출 비중 1.3~2.5%로 안정적(급증 없음, v3.20 재분류 불필요). YoY
성장률이 FY2025 +16.28%->FY2026 +9.76%로 둔화됐으나, 회사 발표(Q4 FY2026
실적발표, 2026-05-21)에 따르면 6월분기 HOKA 한자릿수 성장 둔화는 "일회성
도매 타이밍 이슈이지 수요변화가 아님"(WebSearch 확인). 관세 부담(FY2026
$1.5억, 매출총이익률 -80bp)이 실측 확인됨 - FY2027 가이던스($58.6~59.1억,
+7~8%)에도 관세환급 가정 없이 보수적으로 반영. 2030년까지 중기 프레임워크
(HOKA 두자릿수초반·UGG 한자릿수중반·연결 한자릿수후반 매출CAGR, EPS
두자릿수초반 성장) 공개(2026-05-21 실적발표).

## ⚠️ 실시간 시총이 스크리너 근사치보다 오히려 낮음 - 이번 세션 첫 역방향
사례

주가 $84.50(2026-09-03) x 발행주식 1.364억(2026-07-09 10-Q) = 약
$115.3억 - 스크리너 근사($147.6억)보다 **22% 낮다**(OKTA/CRM/ROKU 등
지금까지의 float 스냅샷 노후화는 전부 실시간 시총이 더 컸던 것과 반대
방향). 발행주식이 9개월새 -6.6% 감소(자사주매입)한 게 주된 원인으로
추정된다 - 스크리너의 public_float 스냅샷이 매입 이전 더 많은 주식수
기준이었을 가능성. 실시간 값을 그대로 채택했다(다른 종목과 동일 원칙).

## 경쟁구도(2026-09-04 WebSearch) - HOKA·UGG 신발업

Nike가 전반적 점유율을 잃는 가운데 HOKA·On Holding·New Balance·adidas가
점유율을 나눠 가져가는 파편화 국면(2026년 기준 On+HOKA가 美프리미엄
러닝화시장의 약 19% 합산 점유). **On Holding이 HOKA보다 훨씬 빠르게
성장**(최근 분기 On +43%YoY vs HOKA +10%YoY, 직접적 경쟁 열위 신호).
러닝화 카테고리 자체는 +8.9%YoY로 견조(라이프스타일 -0.9%와 대비).

## 실행: python3 scripts/analyze_deck_2026_09_04.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.filing_dates import pit_inputs_for
from engine.pipeline import AnalysisInputs, run_analysis, save_ledger
from engine.provenance import provenance_from_sec_facts

TICKER = "DECK"
UA = "IRS Research chlalsrl1203@gmail.com"
TODAY = "2026-09-04"

# ── SEC XBRL companyfacts 실측(2026-09-04 조회, CIK 0000910521) ──────────
# 회계연도는 3월 결산(FY2026 = 2025-04~2026-03)
REVENUE = {
    2017: 1790147000.0, 2018: 1903339000.0, 2019: 2020437000.0, 2020: 2132689000.0,
    2021: 2545641000.0, 2022: 3150339000.0, 2023: 3627286000.0, 2024: 4287763000.0,
    2025: 4985612000.0, 2026: 5472296000.0,
}
OPERATING_INCOME = {
    2017: -1919000.0, 2018: 222584000.0, 2019: 327320000.0, 2020: 338135000.0,
    2021: 504205000.0, 2022: 564707000.0, 2023: 652751000.0, 2024: 927514000.0,
    2025: 1179092000.0, 2026: 1262903000.0,
}
OPERATING_CASHFLOW = {
    2017: 199330000.0, 2018: 327351000.0, 2019: 359505000.0, 2020: 286334000.0,
    2021: 596217000.0, 2022: 172353000.0, 2023: 537422000.0, 2024: 1033184000.0,
    2025: 1044523000.0, 2026: 1181955000.0,
}
CAPEX = {
    2017: 44499000.0, 2018: 34813000.0, 2019: 29086000.0, 2020: 32455000.0,
    2021: 32218000.0, 2022: 51017000.0, 2023: 81025000.0, 2024: 89365000.0,
    2025: 86171000.0, 2026: 84623000.0,
}
NET_INCOME = {  # 참고 기록만 - is_insurer 아니므로 계산에 미사용
    2017: 5710000.0, 2018: 114394000.0, 2019: 264308000.0, 2020: 276142000.0,
    2021: 382575000.0, 2022: 451949000.0, 2023: 516822000.0, 2024: 759563000.0,
    2025: 966091000.0, 2026: 1024071000.0,
}
SBC = {
    2017: 6175000.0, 2018: 14302000.0, 2019: 14585000.0, 2020: 14477000.0,
    2021: 22701000.0, 2022: 26816000.0, 2023: 26897000.0, 2024: 37288000.0,
    2025: 37943000.0, 2026: 44835000.0,
}

# ── 대차대조표(FY2026말, 2026-03-31, 무차입) ──────────────────────────────
CASH_2026 = 1907249000.0  # CashAndCashEquivalentsAtCarryingValue
NET_DEBT = 0.0 - CASH_2026  # -$1,907,249,000(순현금)

DA_2026 = 75773000.0  # DepreciationAmortizationAndAccretionNet(FY2026)
EBITDA = OPERATING_INCOME[2026] + DA_2026  # $1,338,676,000

# ── 시가총액(2026-09-03 Alpha Vantage 종가 + 최신 EntityCommonStockShares) ─
PRICE = 84.50  # Alpha Vantage GLOBAL_QUOTE, 2026-09-03 종가(latestDay)
SHARES_OUT = 136414227.0  # EntityCommonStockSharesOutstanding, 2026-07-09 기준(10-Q)
MARKET_CAP = PRICE * SHARES_OUT  # 약 $11.53B

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
        company_name="Deckers Outdoor Corporation",
        revenue_by_year=REVENUE,
        operating_income_by_year=OPERATING_INCOME,
        operating_cashflow_by_year=OPERATING_CASHFLOW,
        capex_by_year=CAPEX,
        market_cap=MARKET_CAP,
        net_debt=NET_DEBT,
        ebitda=EBITDA,
        risk_free_rate=RF,
        competitor_threat_weights=[0.15, 0.10],
        market_share_trend_pp_per_year=-0.3,
        active_antitrust_or_regulatory_case=False,
        demand_sensitivity_pct=0.30,
        subjective_input_basis=(
            "competitor_threat_weights=[0.15(On Holding - 러닝화 프리미엄 "
            "시장 직접경쟁자, 최근분기 매출성장 +43%YoY로 HOKA(+10%YoY)를 "
            "크게 앞섬), 0.10(Nike - 시장 최대사업자, 전반적 점유율은 잃고 "
            "있으나 규모 자체가 여전히 압도적)]. market_share_trend_pp_"
            "per_year=-0.3 - On Holding의 상대적 고성장이 실측 확인돼 "
            "HOKA의 점유율 확대 속도가 둔화되고 있음을 반영. demand_"
            "sensitivity_pct=0.30 - 신발/의류는 재량소비 성격이 있으나 "
            "HOKA·UGG 둘 다 브랜드 충성도가 높은 카테고리라 CLAUDE.md "
            "앵커표 '소비자 구독/플랫폼'(0.30)에 근접 채택."
        ),
        model_used="two_stage",
        model_choice_reason=(
            "trailing 매출 CAGR(3y 14.69%/5y 16.54%)이 default_terminal_"
            "growth(2.0~4.5%)를 크게 상회하고, 회사 스스로 2030년까지의 "
            "다년 성장프레임워크(한자릿수후반 연결매출CAGR)를 제시해 다년 "
            "수렴 경로(two_stage)가 명확히 적절하다고 판단."
        ),
        falsification_conditions=(
            "FY2027 Q1~Q2 실적에서 HOKA 성장률이 On Holding 대비 격차를 "
            "계속 벌리며 둔화되거나(6월분기 +10%YoY보다 더 낮아지면), "
            "관세환급 미반영 가이던스에도 불구하고 매출총이익률이 추가로 "
            "악화되면 이 판정을 재검토할 것."
        ),
        price_at_analysis=PRICE,
        currency="USD",
        net_income_by_year=NET_INCOME,
        sbc_by_year=SBC,
        data_sources=[
            "SEC XBRL companyfacts (CIK 0000910521, 조회 2026-09-04)",
            "Alpha Vantage GLOBAL_QUOTE (2026-09-03 종가 $84.50)",
            "WebSearch: FY2026 실적·FY2027 가이던스·2030 프레임워크, "
            "관세 부담($1.5억), HOKA vs On Holding 경쟁구도(2026-09-04 재인용)",
        ],
        **pit,
        provenance=provenance,
    )


if __name__ == "__main__":
    inputs = build_inputs()
    result = run_analysis(inputs)
    path = save_ledger(result)
    print(f"saved: {path}")
