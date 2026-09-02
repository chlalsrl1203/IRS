"""
Selective Insurance Group(SIGI) 정식 분석 - 2026-09-01.

경위: 연구 우선순위 큐 3순위(스크린 Gap 추정 +21.36%p, S등급, 앞선 LNTH/EQT는
각각 진행중 인수합병·M&A+원자재 사이클로 FRAMEWORK_MISMATCH 처리). P&C
(손해)보험사 - `is_insurer=True` 경로(v3.22, ACGL/PGR/BRO 선례)를 그대로 따른다.

## 원자료 - SEC XBRL companyfacts(CIK 0000230557, 2026-09-01 조회, 2008~2025
18개년 확보). PGR·ACGL 선례와 동일하게 `operating_income_by_year`에는
**세전이익(income before income taxes)**을 대용한다(보험업은 별도 '영업이익'
라인이 없음).

## ⭐ 데이터 함정 - 2016~2020년 세전이익에 "Q4 단독 수치"가 섞여 있었다

SEC provider 자동 fetch가 `operating_income`을 통째로 [미확보] 처리했다 -
안전한 실패였다. 원인: `IncomeLossFromContinuingOperationsBeforeIncomeTaxes...`
태그에 같은 회계연도(예: 2016-12-31)로 **두 개의 다른 가액**이 동시에
존재했다 - 하나는 `start=2016-01-01`(정상 12개월), 다른 하나는
`start=2016-10-01`(4분기 단독 3개월, 예: 2016년 219,955,000 vs 50,326,000).
회사가 10-K에 연차 손익과 4분기 손익을 같은 XBRL 태그로 함께 보고했고, 자동
피커는 이를 구분할 근거가 없어 정직하게 실패를 반환했다(조용히 틀린 값을
고르지 않았다는 점에서 설계대로 작동함). `start`가 1월 1일인 값만 걸러
2016~2020 5개년을 수동 확정했다. 다른 시계열(매출·순이익 등)은 동일 검증
결과 이 문제가 없었다(피커가 이미 올바른 값을 골랐음을 확인).

## 재무상태표 항목 - PGR/ACGL 관행 그대로

보험업은 투자포트폴리오가 준비금과 짝이라 순부채 상쇄에서 제외한다(PGR $125M/
ACGL $993M 선례와 동일 원칙) - SIGI는 `CashCashEquivalentsRestrictedCash...`
태그(투자포트폴리오 제외한 협의의 현금)를 썼다. D&A도 PGR과 동일하게
고정자산 감가상각만(`Depreciation` 태그, 채권 프리미엄상각 등 투자관련
항목 제외).

## 경쟁구도(2026-09-01 WebSearch, 각사 2026 Q1/Q2 실적발표 기준)

Travelers(TRV)는 압도적 1위 - 합산비율(combined ratio) 84.1~84.7%로
"best-in-class" 언더라이팅 규율(SIGI/CINF은 90%대 후반). Cincinnati
Financial(CINF)은 SIGI와 유사한 처지(2026 Q1 합산비율 98.6%, 전년 91.9%
대비 6.7%p 악화 - 업계 전반의 언더라이팅 사이클 둔화). **SIGI 자체도
순보험료(NPW)가 경쟁압력+의도적 언더라이팅 조정으로 전년比 -5% 역성장** -
자체 시장점유율 축소가 실측으로 확인됨(2026 Q2 실적발표).

## 실행: python3 scripts/analyze_sigi_2026_09_01.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.filing_dates import pit_inputs_for
from engine.pipeline import AnalysisInputs, run_analysis, save_ledger
from engine.provenance import provenance_from_sec_facts

TICKER = "SIGI"
UA = "IRS Research chlalsrl1203@gmail.com"
TODAY = "2026-09-01"

# ⚠️ SEC XBRL에 2011~2017년 capex(PP&E 취득) 태그 자체가 없다(당시 SIGI가
# 별도 라인으로 태깅하지 않은 것으로 보임 - 다른 어떤 후보 태그로도 확인 안 됨).
# fcf(=OCF-capex) 계산이 연도별로 짝을 이뤄야 하므로, capex가 있는 2018~2025
# 8개년만 균일하게 쓴다(BSY 선례와 동일 판단 - "10년치 미달, 있는 구간만 사용").
REVENUE = {
    2018: 2586080000.0, 2019: 2846491000.0, 2020: 2922274000.0, 2021: 3379164000.0,
    2022: 3558062000.0, 2023: 4232106000.0, 2024: 4861664000.0, 2025: 5336928000.0,
}
# 세전이익(income before income taxes) - 보험업 영업이익 대용(PGR/ACGL 선례).
# 2018~2020은 Q4단독 수치를 걸러낸 정상 12개월 값(위 docstring 참고).
OPERATING_INCOME = {
    2018: 211721000.0, 2019: 336390000.0, 2020: 302988000.0,
    2021: 505310000.0, 2022: 280186000.0, 2023: 458412000.0, 2024: 258034000.0,
    2025: 589597000.0,
}
OPERATING_CASHFLOW = {
    2018: 454944000.0, 2019: 477495000.0,
    2020: 554045000.0, 2021: 771422000.0, 2022: 802409000.0, 2023: 758908000.0,
    2024: 1099888000.0, 2025: 1233021000.0,
}
CAPEX = {
    2018: 16110000.0,
    2019: 30986000.0, 2020: 22064000.0, 2021: 22163000.0, 2022: 26019000.0,
    2023: 22631000.0, 2024: 30810000.0, 2025: 38742000.0,
}
NET_INCOME = {
    2018: 178939000.0, 2019: 271623000.0,
    2020: 246355000.0, 2021: 403837000.0, 2022: 224886000.0, 2023: 365238000.0,
    2024: 207012000.0, 2025: 466411000.0,
}
SHAREHOLDERS_EQUITY = {
    2018: 1791802000.0, 2019: 2194936000.0,
    2020: 2738889000.0, 2021: 2982885000.0, 2022: 2527564000.0, 2023: 2954381000.0,
    2024: 3120076000.0, 2025: 3608975000.0,
}
DIVIDENDS_PAID = {
    2018: 42097000.0, 2019: 47675000.0,
    2020: 54486000.0, 2021: 60136000.0, 2022: 66920000.0, 2023: 73827000.0,
    2024: 84936000.0, 2025: 92884000.0,
}
SBC = {
    2018: 14507000.0, 2019: 19077000.0,
    2020: 16227000.0, 2021: 15893000.0, 2022: 18428000.0, 2023: 18346000.0,
    2024: 22763000.0, 2025: 23104000.0,
}

# 재무상태표(FY2025, 2025-12-31 기준) - PGR/ACGL과 동일 원칙(투자포트폴리오 제외)
CASH_2025 = 17958000.0    # CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents
TOTAL_DEBT_2025 = 901873000.0  # LongTermDebtAndCapitalLeaseObligationsIncludingCurrentMaturities
NET_DEBT = TOTAL_DEBT_2025 - CASH_2025
DA_2025 = 26300000.0      # Depreciation(고정자산만, 투자관련 상각 제외 - PGR과 동일)
EBITDA = OPERATING_INCOME[2025] + DA_2025

PRICE = 91.21
SHARES_OUT = 59569119
MARKET_CAP = PRICE * SHARES_OUT

RF = 0.0475  # 미국 10Y, 2026-08-31 종가(CROX 분석과 동일 시점 재사용)


def build_inputs() -> AnalysisInputs:
    pit = pit_inputs_for(TICKER, TODAY, list(REVENUE), user_agent=UA)
    provenance = None
    try:
        from engine.data.providers.sec import fetch_company_facts, ticker_to_cik

        cik = ticker_to_cik(TICKER, UA)
        facts = fetch_company_facts(cik, UA)
        provenance = provenance_from_sec_facts(facts, TICKER, TODAY, list(REVENUE))
    except Exception:  # noqa: BLE001
        provenance = None

    return AnalysisInputs(
        ticker=TICKER,
        company_name="Selective Insurance Group, Inc.",
        revenue_by_year=REVENUE,
        operating_income_by_year=OPERATING_INCOME,
        operating_cashflow_by_year=OPERATING_CASHFLOW,
        capex_by_year=CAPEX,
        market_cap=MARKET_CAP,
        net_debt=NET_DEBT,
        ebitda=EBITDA,
        risk_free_rate=RF,

        competitor_threat_weights=[0.35, 0.20],
        market_share_trend_pp_per_year=-1.0,
        active_antitrust_or_regulatory_case=False,
        demand_sensitivity_pct=0.18,
        subjective_input_basis=(
            "경쟁강도 - Travelers 0.35(2026 Q1/Q2 합산비율 84.1~84.7%로 "
            "'best-in-class' 언더라이팅 규율, SIGI/CINF 대비 10%p 이상 "
            "우위 - PGR이 자사 최대경쟁자에 부여한 0.35와 동일 수준[추정치])"
            ". Cincinnati Financial 0.20(SIGI와 유사한 처지 - 2026 Q1 합산"
            "비율 98.6%(전년 91.9% 대비 6.7%p 악화)로 업계 공통의 언더라이팅"
            "사이클 둔화를 함께 겪는 근접 동종 경쟁자[추정치]). market_share_"
            "trend=-1.0pp: SIGI 자체 순보험료(NPW)가 경쟁압력+의도적 "
            "언더라이팅 조정으로 2026 Q2 전년比 -5% 역성장(회사 자체 실적발표"
            "로 확인된 실측 신호, ACGL의 -1.5pp보다는 완만하게 설정 - SIGI는 "
            "스스로 2026 가이던스에서 합산비율 개선을 전망 중이라 완전한 "
            "구조적 후퇴로 보진 않음[추정치]). active_antitrust_or_"
            "regulatory_case=False: 2026-09 WebSearch로 확인한 진행 중인 "
            "반독점·경쟁당국 조사 없음. demand_sensitivity=0.18: 상업용"
            "일반배상책임・자동차보험 등 상당부분이 법적・계약적 의무가입"
            "이라 재량소비재보다 훨씬 둔감 - PGR(개인용 자동차, 0.15)과 "
            "ACGL(전문보험・재보험, 0.20) 중간값으로 설정했다(SIGI는 상업용"
            "비중이 커 완전히 의무가입 성격인 개인용 자동차보다는 다소 "
            "높게, 그러나 초과보험(E&S) 비중이 있는 ACGL보다는 낮게)"
            "[추정치, 신규 관측치]."
        ),

        model_used="two_stage",
        model_choice_reason=(
            "PGR·ACGL 선례와 동일하게 two_stage를 채택한다 - 18개년(2008~"
            "2025) 매출이 M&A 단계상승이나 극단적 사이클 없이 꾸준히 "
            "성장해왔고($1.59B->$5.34B), 최근 5개년(2020->2025) 성장률이 "
            "직전 구간보다 오히려 가속(보험료 인상 사이클 반영)돼 있어 "
            "'현재 고성장 -> 장기 수렴'을 모델링하는 two_stage가 이 "
            "궤적에 이론적으로 부합한다고 판단. 언더라이팅 이익(세전이익) "
            "자체는 사이클로 진동하지만 매출(순보험료)은 안정적 성장 "
            "궤적을 보인다는 점에서 CROX(3y CAGR이 이미 한자릿수로 정체돼 "
            "single_stage 채택)와는 반대 상황."
        ),

        falsification_conditions=(
            "(1) 2026 Q3/Q4 실적에서 순보험료(NPW) 역성장이 추가로 확대되거나"
            "(현재 -5%YoY) 회사가 2026 가이던스(합산비율 96.5~97.5%)를 "
            "재차 하향하면 재검토. (2) Travelers·Cincinnati Financial 대비"
            " 합산비율 격차가 더 벌어지면(현재 SIGI Q2 98% vs Travelers "
            "84%대) competition_intensity 상향 재검토. (3) is_insurer "
            "교차검증(지속가능성장률 vs Realistic Growth) 괴리가 5%p를 "
            "넘으면 재검토."
        ),

        price_at_analysis=PRICE,
        currency="USD",

        is_insurer=True,
        net_income_by_year=NET_INCOME,
        shareholders_equity_by_year=SHAREHOLDERS_EQUITY,
        dividends_paid_by_year=DIVIDENDS_PAID,
        sbc_by_year=SBC,

        data_sources=[
            "SEC XBRL companyfacts(CIK 0000230557), 2026-09-01 조회",
            "Alpha Vantage GLOBAL_QUOTE, 2026-09-01 조회",
            "WebSearch: SIGI/Travelers/Cincinnati Financial 2026 Q1/Q2 "
            "실적발표(합산비율·NPW), 2026-09-01 조회",
        ],

        **pit,
        provenance=provenance,
    )


if __name__ == "__main__":
    inputs = build_inputs()
    result = run_analysis(inputs)
    path = save_ledger(result)
    print(f"저장: {path}")
    print(f"판정: {result['judgment']} (등급 {result['judgment_grade']})")
    print(f"Gap: {result['expectation_gap']*100:+.2f}%p")
    print(f"RAR: {result['rar']:+.4f}")
    print(f"DRS: {result['drs']['score']:.2f}")
    print(f"Realistic Growth: {result['growth']['realistic_growth']*100:.2f}%")
    print(f"Implied Growth: {result['implied_growth']*100:.2f}% ({result['inputs']['model_used']})")
    print(f"Confidence: {result['confidence']['final']}")
    if result.get("insurer_cross_check"):
        print("insurer_cross_check:", result["insurer_cross_check"])
    if result.get("data_limitations"):
        print("한계:")
        for lim in result["data_limitations"]:
            print(f"  - {lim}")
