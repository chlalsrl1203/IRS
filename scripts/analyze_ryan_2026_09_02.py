"""
Ryan Specialty Holdings, Inc.(RYAN) 정식 분석 - 2026-09-02.

경위: 연구 우선순위 큐(스크리너 tier A, Gap 추정 +18.83%p, 시총 근사
~$8.56B). LNTH/EQT/CDE를 FRAMEWORK_MISMATCH로 제외한 뒤 큐 순서상 다음
순위.

## 원자료 - SEC XBRL companyfacts(1차자료, `SecCompanyFactsProvider`,
2026-09-02 조회, CIK 0001849253, 2019~2025 7개년 확보 - 2021-07 IPO라
공개기업 이력 자체가 짧음, 10y CAGR 산출 불가(연도수 부족)).

## ⭐ 핵심 발견 - Up-C 이중클래스 구조에서 시가총액을 Class A만으로 잡으면
FCF 배수가 절반으로 왜곡된다

RYAN은 2021-07 IPO 시 전형적인 Up-C 구조(상장지주회사가 운영LLC의 지분
일부만 보유, 나머지는 사전IPO 소유주가 LLC Unit + 의결권만 있는 무경제권
Class B주로 보유)로 상장했다. **재무제표(매출·영업이익·OCF·capex)는
운영LLC 전체(100% 연결)를 담는데, Class A 주식만으로 시가총액을 잡으면
분자(전체 FCF)와 분모(부분 지분가치)가 어긋난다** - `check_scale_
plausibility()`가 원리적으로 잡으려는 유형의 함정과 같은 계열이지만 이번엔
비율 스케일이 아니라 지분구조 스케일 문제라 그 가드로는 안 걸린다.

WebSearch로 2026-07-27 10-Q 표지 확인: Class A 122,077,702주 + Class B
133,737,083주(LLC Unit과 1:1 페어링, Class A로 교환 가능 - 경제적 지분은
Class A와 동일) = 총 경제적 지분 255,814,785주. **총주식수 기준 시총
(~$10.83B)을 채택** - Class A만으로 계산하면(~$5.43B, 실제로 investing.com
등 일부 소스가 이렇게 보고) FCF수익률이 실제의 약 2배로 부풀어 내재성장률이
음수 근처까지 떨어지는 허위 초저평가 신호를 만들 뻔했다.

## 발견 2 - 2021년 capex $343.2M은 조직재편/M&A 관련 일회성 항목(원자료
그대로 사용, 계산에는 영향 없음)

WebSearch(2026-09-02): RYAN이 2021 IPO와 동시에 All Risk 인수를 진행,
순이익률이 이 인수 관련 비용으로 감소했다고 공시. SEC 태그
`PaymentsToAcquireProductiveAssets`가 2021년 $343.2M(다른 해는
$0.1M~$7.7M 수준)을 담고 있어 M&A 관련 지급으로 보이나
`PaymentsToAcquireBusinessesNetOfCashAcquired` 태그는 비어있어 확정은
못했다. **계산에는 영향 없음** - `capex_years`(=최근 5개년)를 쓰는 경로는
`capex_classification`(opt-in) 미사용 시 전혀 호출되지 않고, fcf0는 2025년
capex($3.0M, 정상범위)만 쓴다. 원자료 그대로 두고 이 서술만 기록한다.

## 발견 3 - 회사 자체 오가닉 성장 가이던스(5~7%)가 trailing CAGR(3y
20.5%/5y 24.1%)보다 훨씬 낮다 - GEN/BRO/TCOM 계열과 유사하나 오버라이드는
쓰지 않음

Q2 2026(2026-07 발표) 총매출 +7.2%YoY·**오가닉 성장 +6.7%**(총성장과
근접 - 최근 분기는 M&A 기여가 작다는 뜻)로 FY2026 오가닉 가이던스를
5~7%(상단 근접 예상)로 상향했다. trailing CAGR이 훨씬 높은 건 2019~2022
초고성장기(다수 소형 인수+시장 확장)의 잔재다. **ROP가 확립한 기준
(다년 실현실적만 override 자격)에 못 미친다** - Q2 실측 1개 분기+FY
가이던스 1건뿐이라 `realistic_growth_override`는 쓰지 않고 이 괴리를
falsification_conditions/model_choice_reason에 병기만 한다.

## 경쟁구도(2026-09-02 WebSearch) - 특수보험 도매유통(E&S wholesale) 업종

AmWINS(업계 최대, 비상장, 압도적 글로벌 플레이스먼트 역량) > CRC Group
(Truist Insurance 소유) > Risk Placement Services(BRO 소유). RYAN은
MGA(총괄대리점) 비중이 높은 독자 언더라이팅 시설 확보 전략으로 차별화 -
업계 전반이 인수합병으로 통합 중(EBITDA 배수 15배 이상 거래 다수).

## 실행: python3 scripts/analyze_ryan_2026_09_02.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.filing_dates import pit_inputs_for
from engine.pipeline import AnalysisInputs, run_analysis, save_ledger
from engine.provenance import provenance_from_sec_facts

TICKER = "RYAN"
UA = "IRS Research chlalsrl1203@gmail.com"
TODAY = "2026-09-02"

# ── SEC XBRL companyfacts 실측(2026-09-02 조회) ──────────────────────────
REVENUE = {
    2019: 765111000.0, 2020: 1018274000.0, 2021: 1432771000.0,
    2022: 1711861000.0, 2023: 2026596000.0, 2024: 2455671000.0,
    2025: 2994582000.0,
}
OPERATING_INCOME = {
    2019: 101038000.0, 2020: 158538000.0, 2021: 186624000.0,
    2022: 289508000.0, 2023: 359081000.0, 2024: 427812000.0,
    2025: 493640000.0,
}
OPERATING_CASHFLOW = {
    2019: 149507000.0, 2020: 135393000.0, 2021: 273493000.0,
    2022: 335514000.0, 2023: 477203000.0, 2024: 514868000.0,
    2025: 643667000.0,
}
CAPEX = {
    2019: 100000.0, 2020: 5236000.0, 2021: 343158000.0,
    2022: 7714000.0, 2023: 0.0, 2024: 0.0, 2025: 3014000.0,
}
NET_INCOME = {
    2019: 64166000.0, 2020: 68104000.0, 2021: 65873000.0,
    2022: 61052000.0, 2023: 61037000.0, 2024: 94665000.0,
    2025: 63399000.0,
}
SBC = {
    2019: 8153000.0, 2020: 10800000.0, 2021: 67534000.0,
    2022: 77480000.0, 2023: 69743000.0, 2024: 78995000.0,
    2025: 69451000.0,
}

# ── 대차대조표(FY2025말, 2025-12-31, SEC XBRL 실측) ──────────────────────
CASH_2025 = 158322000.0            # CashAndCashEquivalentsAtCarryingValue
TOTAL_DEBT_2025 = 3346276000.0     # LongTermDebt(총액, 유동+비유동)
NET_DEBT = TOTAL_DEBT_2025 - CASH_2025

DA_2025 = 13089000.0 + 274400000.0  # Depreciation + AmortizationOfIntangibleAssets(피인수 무형자산 상각)
EBITDA = OPERATING_INCOME[2025] + DA_2025

# ── 시가총액(2026-09-02) - Up-C 이중클래스 총주식수 채택 ──────────────────
# Class A 122,077,702주 + Class B 133,737,083주(LLC Unit 1:1 페어링,
# Class A 교환가능 - 경제적 지분 동일) = 총 255,814,785주(2026-07-27
# 10-Q 표지, WebSearch 재인용). 재무제표가 운영LLC 전체(100% 연결)를
# 담으므로 시총도 전체 경제적 지분 기준으로 맞춰야 FCF수익률이 왜곡되지
# 않는다(Class A만 쓰면 ~$5.43B로 절반 수준 - 허위 초저평가 신호 유발).
PRICE = 42.32  # Alpha Vantage GLOBAL_QUOTE, 2026-09-01 종가(latestDay)
SHARES_OUT = 122077702.0 + 133737083.0
MARKET_CAP = PRICE * SHARES_OUT  # 약 $10.83B

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
        company_name="Ryan Specialty Holdings, Inc.",
        revenue_by_year=REVENUE,
        operating_income_by_year=OPERATING_INCOME,
        operating_cashflow_by_year=OPERATING_CASHFLOW,
        capex_by_year=CAPEX,
        market_cap=MARKET_CAP,
        net_debt=NET_DEBT,
        ebitda=EBITDA,
        risk_free_rate=RF,
        competitor_threat_weights=[0.20, 0.12],
        market_share_trend_pp_per_year=0.3,
        active_antitrust_or_regulatory_case=False,
        demand_sensitivity_pct=0.18,
        subjective_input_basis=(
            "competitor_threat_weights=[0.20(AmWINS), 0.12(CRC Group)] - AmWINS가 "
            "업계 최대(비상장, 압도적 글로벌 플레이스먼트 역량·독점적 데이터분석 "
            "플랫폼)로 최대 위협, CRC Group(Truist Insurance 소유)이 2선 - RYAN은 "
            "MGA(총괄대리점) 비중이 높은 독자 언더라이팅 시설로 차별화돼 완전 "
            "직접경쟁보다는 낮게 반영. market_share_trend_pp_per_year=+0.3 - "
            "업계 전반 M&A 통합 국면(EBITDA 15배+ 거래 다수)에서 RYAN도 지속적 "
            "볼트온 인수로 점유율 확대 중이나 오가닉 성장이 최근 둔화(아래 참고)돼 "
            "완만한 값만 반영(2026-09-02 WebSearch, 정량 점유율 데이터 미확보). "
            "demand_sensitivity_pct=0.18 - CLAUDE.md 업종앵커표 '기업용 필수 "
            "SW·전문서비스(계약기반, 전환비용 높음)' 버킷(BRO·PGR 등, 앵커 0.20) "
            "보다 약간 낮게 - E&S 특수보험 배치는 갱신형 계약구조라 전환비용이 "
            "특히 높음(BRO가 같은 버킷에서 0.20 사용, RYAN은 특수보험 도매유통 "
            "특유의 더 높은 재계약 지속성을 반영해 소폭 하향)."
        ),
        model_used="two_stage",
        model_choice_reason=(
            "trailing 매출 CAGR(3y 20.49%/5y 24.08%)이 default_terminal_growth"
            "(2.0~4.5%)보다 크게 높아 다년 수렴 경로가 필요하다고 판단. 다만 "
            "회사 자체 FY2026 오가닉성장 가이던스(5~7%, Q2 실측 오가닉 +6.7%)가 "
            "trailing CAGR보다 훨씬 낮다 - GEN/BRO/TCOM과 유사한 괴리이지만 "
            "ROP가 확립한 override 기준(다년 실현실적 필요)에는 못 미쳐(1개 "
            "분기+1개년 가이던스뿐) `realistic_growth_override`는 쓰지 않고 "
            "이 괴리를 falsification_conditions에 명시적으로 남긴다."
        ),
        falsification_conditions=(
            "다음 분기(Q3 2026) 오가닉 성장률이 FY2026 가이던스 하단(5%)을 밑돌거나, "
            "손해보험 요율(특히 재산보험 property pricing)이 계속 하락하며 캐주얼티/"
            "바인딩 세그먼트 경쟁이 심화돼 EBITDA 마진 가이던스(2025년 36.1% 대비 "
            "-50~100bp)를 추가로 하회하면 이 판정을 재검토할 것."
        ),
        price_at_analysis=PRICE,
        currency="USD",
        net_income_by_year=NET_INCOME,
        sbc_by_year=SBC,
        data_sources=[
            "SEC XBRL companyfacts (CIK 0001849253, 조회 2026-09-02)",
            "Alpha Vantage GLOBAL_QUOTE (2026-09-01 종가 $42.32)",
            "WebSearch: RYAN 2026-07-27 10-Q 표지(Class A/B 주식수), "
            "Q2 2026 실적발표(2026-07-30 전후), 경쟁구도",
        ],
        **pit,
        provenance=provenance,
    )


if __name__ == "__main__":
    inputs = build_inputs()
    result = run_analysis(inputs)
    path = save_ledger(result)
    print(f"saved: {path}")
