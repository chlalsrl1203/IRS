"""
Cincinnati Financial Corp(CINF) 정식 분석 - 2026-09-03.

경위: 연구 우선순위 큐(스크리너 tier S, Gap 추정 +12.04%p, 시총 근사
~$22.85B). FRAMEWORK_MISMATCH 16종목 + HLNE/FIVE/TW/RLI 정식분석 완료,
OVV 제외 뒤 큐 순서상 다음 후보. 손해보험사 - `is_insurer=True` 경로
(v3.22, ACGL/PGR/BRO/SIGI/RLI 선례)를 그대로 따른다.

## 원자료 - SEC XBRL companyfacts(1차자료, `SecCompanyFactsProvider`,
2026-09-03 조회, CIK 0000020286, 2008~2025 18개년 확보). PGR/ACGL/SIGI/
RLI 선례와 동일하게 `operating_income_by_year`에는 **세전이익(income
before income taxes)**을 대용한다. Q4단독 오염 없음(raw entries 전수
확인).

## ⚠️ SBC - XBRL 개별태그 2021년 이후 중단, 세후금액을 세전으로 역환산

`ShareBasedCompensation`류 태그가 2021년($33M)까지만 보고되고 이후
중단(RLI와 동일 패턴) - WebSearch로 10-K 원문 인용("세후 SBC비용
2025/2024/2023년 각각 $37M/$37M/$32M, 관련 세금혜택 $9M/$9M/$8M")을
확보해 **세전 환산값**(37+9=46, 37+9=46, 32+8=40)으로 FY2025=$46M을
채택했다 - RLI처럼 완전히 생략하지 않고 세후+세금혜택 역산이라는 다른
경로로 확보했다.

## ⭐ 핵심 발견 - 언더라이팅 규율이 동종 보험사 대비 뚜렷이 열위

**2026 Q2 합산비율 100.8%(전년比 +5.9%p 악화, 재해손해 증가)로
언더라이팅 손실 구간** - SIGI(98%대)·RLI(85.6%)보다도 나쁘고
Travelers(84%대)와는 격차가 크다. 신규계약보험료가 전체 -11%,
개인보험 -40% 급감(경쟁심화+선별적 언더라이팅). **투자포트폴리오의
약 40%가 보통주**(동종 보험사 대비 이례적으로 높은 주식비중)로
자본시장 변동성에 특히 취약 - 2022년 세전손실(-$693M)이 그 결과
(주식시장 급락 반영). 외부 분석은 "8~9% ROE 전망 대비 1.6배 P/B는
동종업계(1.2~1.3배) 대비 고평가"로 평가(2026-09-03 WebSearch,
Seeking Alpha/GuruFocus) - 스크리너 Gap 추정과 정반대 방향의 외부
평가가 존재해 `is_insurer` 교차검증 결과를 최우선으로 확인할 것.

## 경쟁구도(2026-09-03 WebSearch)

Travelers가 압도적 규율(84%대 합산비율)의 최대 위협, Chubb은 대형
다각화 경쟁자. CINF 자체 신규계약 감소가 경쟁압력을 실측으로 보여줌.

## 실행: python3 scripts/analyze_cinf_2026_09_03.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.filing_dates import pit_inputs_for
from engine.pipeline import AnalysisInputs, run_analysis, save_ledger
from engine.provenance import provenance_from_sec_facts

TICKER = "CINF"
UA = "IRS Research chlalsrl1203@gmail.com"
TODAY = "2026-09-03"

REVENUE = {
    2008: 3824000000.0, 2009: 3903000000.0, 2010: 3772000000.0, 2011: 3803000000.0,
    2012: 4111000000.0, 2013: 4531000000.0, 2014: 4945000000.0, 2015: 5142000000.0,
    2016: 5449000000.0, 2017: 5732000000.0, 2018: 5407000000.0, 2019: 7924000000.0,
    2020: 7536000000.0, 2021: 9630000000.0, 2022: 6557000000.0, 2023: 10013000000.0,
    2024: 11337000000.0, 2025: 12631000000.0,
}
# 세전이익(income before income taxes) - 보험업 영업이익 대용.
OPERATING_INCOME = {
    2019: 2472000000.0, 2020: 1499000000.0, 2021: 3670000000.0,
    2022: -693000000.0, 2023: 2276000000.0, 2024: 2858000000.0,
    2025: 2980000000.0,
}
OPERATING_CASHFLOW = {
    2008: 484000000.0, 2009: 525000000.0, 2010: 531000000.0, 2011: 247000000.0,
    2012: 638000000.0, 2013: 796000000.0, 2014: 873000000.0, 2015: 1064000000.0,
    2016: 1103000000.0, 2017: 1052000000.0, 2018: 1181000000.0, 2019: 1208000000.0,
    2020: 1491000000.0, 2021: 1981000000.0, 2022: 2052000000.0, 2023: 2052000000.0,
    2024: 2649000000.0, 2025: 3112000000.0,
}
CAPEX = {
    2008: 36000000.0, 2009: 42000000.0, 2010: 17000000.0, 2011: 7000000.0,
    2012: 6000000.0, 2013: 7000000.0, 2014: 9000000.0, 2015: 10000000.0,
    2016: 13000000.0, 2017: 16000000.0, 2018: 20000000.0, 2019: 24000000.0,
    2020: 20000000.0, 2021: 15000000.0, 2022: 15000000.0, 2023: 18000000.0,
    2024: 22000000.0, 2025: 20000000.0,
}
NET_INCOME = {
    2021: 2946000000.0, 2022: -486000000.0, 2023: 1843000000.0,
    2024: 2292000000.0, 2025: 2393000000.0,
}
SHAREHOLDERS_EQUITY = {
    2021: 13105000000.0, 2022: 10531000000.0, 2023: 12098000000.0,
    2024: 13935000000.0, 2025: 15911000000.0,
}
DIVIDENDS_PAID = {
    2021: 395000000.0, 2022: 423000000.0, 2023: 454000000.0,
    2024: 490000000.0, 2025: 525000000.0,
}
# 세후 SBC비용+관련 세금혜택 역산(10-K 원문 인용, WebSearch) - RLI와
# 달리 완전 생략하지 않고 다른 경로로 확보(위 docstring 참고).
SBC = {
    2023: 40000000.0, 2024: 46000000.0, 2025: 46000000.0,
}

# 재무상태표(FY2025, 2025-12-31 기준) - PGR/ACGL/SIGI/RLI와 동일 원칙(투자포트폴리오 제외)
CASH_2025 = 1431000000.0  # CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents
DEBT_2025 = 790000000.0   # LongTermDebt
NET_DEBT = DEBT_2025 - CASH_2025
DA_2025 = 36000000.0      # Depreciation(고정자산만, PGR/SIGI/RLI와 동일)
EBITDA = OPERATING_INCOME[2025] + DA_2025

PRICE = 171.69   # Alpha Vantage GLOBAL_QUOTE, 2026-09-02 종가(latestDay)
SHARES_OUT = 154686742.0  # 10-Q 표지(2026-04-22 기준)
MARKET_CAP = PRICE * SHARES_OUT  # 약 $26.56B

RF = 0.0475


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
        company_name="Cincinnati Financial Corporation",
        revenue_by_year=REVENUE,
        operating_income_by_year=OPERATING_INCOME,
        operating_cashflow_by_year=OPERATING_CASHFLOW,
        capex_by_year=CAPEX,
        market_cap=MARKET_CAP,
        net_debt=NET_DEBT,
        ebitda=EBITDA,
        risk_free_rate=RF,
        competitor_threat_weights=[0.30, 0.15],
        market_share_trend_pp_per_year=-1.5,
        active_antitrust_or_regulatory_case=False,
        demand_sensitivity_pct=0.18,
        subjective_input_basis=(
            "competitor_threat_weights=[0.30(Travelers - 합산비율 84%대의 "
            "'best-in-class' 규율, CINF 자체 100.8%와 극명한 격차라 최대 "
            "경쟁위협으로 비중있게 반영), 0.15(Chubb - 대형 다각화 손해"
            "보험사)]. market_share_trend_pp_per_year=-1.5 - 신규계약"
            "보험료가 전체 -11%·개인보험 -40% 급감(2026 Q2 실적발표로 "
            "확인된 실측, SIGI의 -1.0pp보다 더 부정적으로 설정 - CINF는 "
            "합산비율까지 100.8%로 손실전환해 SIGI보다 상황이 나쁘다고 "
            "판단[추정치]). demand_sensitivity_pct=0.18 - 상업용·개인용 "
            "혼합 손해보험 구조로 SIGI(0.18)·RLI(0.18)와 유사한 사업믹스."
        ),
        model_used="two_stage",
        model_choice_reason=(
            "PGR·ACGL·SIGI·RLI 선례와 동일하게 two_stage를 채택한다 - "
            "18개년(2008~2025) 매출이 시장가치 반영 변동(특히 2022년 "
            "주식시장 급락)으로 진동하지만 순보험료 기반 장기추세는 "
            "꾸준히 성장해왔다는 점에서 다년 수렴 모델이 적절."
        ),
        falsification_conditions=(
            "(1) 2026 하반기 실적에서 합산비율이 105%를 넘거나(현재 "
            "100.8%) 신규계약 감소가 추가로 확대되면 재검토. (2) "
            "is_insurer 교차검증(지속가능성장률 vs Realistic Growth) 괴리가 "
            "5%p를 넘거나 P/B가 외부평가(1.6배, '동종업계 대비 고평가')와 "
            "판정이 상충하면 최우선 재검토."
        ),
        price_at_analysis=PRICE,
        currency="USD",
        is_insurer=True,
        net_income_by_year=NET_INCOME,
        shareholders_equity_by_year=SHAREHOLDERS_EQUITY,
        dividends_paid_by_year=DIVIDENDS_PAID,
        sbc_by_year=SBC,
        data_sources=[
            "SEC XBRL companyfacts (CIK 0000020286, 조회 2026-09-03)",
            "Alpha Vantage GLOBAL_QUOTE (2026-09-02 종가 $171.69)",
            "WebSearch: CINF 10-Q 표지 주식수(2026-04-22 기준), SBC "
            "세전환산(10-K 원문 인용), 합산비율·경쟁구도·P/B 외부평가"
            "(2026 Q2 실적발표/Seeking Alpha/GuruFocus, 2026-09-03 재인용)",
        ],
        **pit,
        provenance=provenance,
    )


if __name__ == "__main__":
    inputs = build_inputs()
    result = run_analysis(inputs)
    path = save_ledger(result)
    print(f"saved: {path}")
