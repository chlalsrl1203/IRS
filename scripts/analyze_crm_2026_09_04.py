"""
Salesforce, Inc.(CRM) 정식 분석 - 2026-09-04.

경위: 연구 우선순위 큐 tier A, 스크리너 Gap 추정 +10.10%p, 시총 근사
$191.8B(public_float 근사치, 노후화 - OKTA/ROKU급 패턴). FRAMEWORK_MISMATCH
20종목 + BYD 정식분석 완료 뒤 큐 순서상 다음 후보.

## 원자료 - SEC XBRL companyfacts(1차자료, `SecCompanyFactsProvider`,
2026-09-04 조회, CIK 0001108524, FY2015~FY2026 12개년 확보 - 회계연도는
1월 결산이라 FY2026=2025-02~2026-01).

## ⚠️ 실시간 시총이 스크리너 근사치를 14% 상회 - OKTA/MEDP/NBIX/NXT/ROKU/
FIVE급 float 스냅샷 노후화 패턴

WebSearch(2026-09-04) 확인: 실시간 시총 약 $217.6B(주가 $264.43 x
발행주식 823M) - 스크리너 근사($191.8B)의 1.13배. 주가는 2025년 -25%~
2026년 저점(6월, $146.32) 대비 -33%까지 하락했다가 2026-08-26 Q2 FY27
실적 호조(beat-and-raise)로 급반등해 현재 52주 신고가($269.11) 근접
수준 - 애널리스트 컨센서스 목표주가($266~270)도 현재가와 거의 일치해
"이미 시장이 재평가를 상당부분 반영했다"는 신호. PTC 선례(랠리 구간에
Gap이 stale일 위험)와 유사하나, 정식분석 시점 실시간 시총을 그대로
채택하는 것으로 그 함정을 회피했다.

## ⚠️ $250억 부채조달 자사주매입 - 레버리지 급증 + FCF성장 가이던스
반토막

2026-03 이사회가 $500억 자사주매입 승인, 즉시 $250억 규모 가속자사주매입
(ASR)을 **$250억 선순위채(쿠폰 4.5~6.7%) 발행으로 조달**해 집행 -
FY2027 Q1(2026-04 결산)에 발행주식 -12% 감소(923M->819M). SEC XBRL
실측으로 확인: LongTermDebt가 $144.39억(2026-01-31)->$392.88억
(2026-07-31)로 급증. 이 자사주매입의 부채조달 비용 때문에 **회사 스스로
FCF성장 가이던스를 절반 수준으로 하향**(2026-09-04 WebSearch, Motley
Fool "Salesforce Borrowed $25 Billion to Buy Its Own Stock and Cut Its
Cash Flow Growth Guidance in Half"). net_debt/EBITDA가 이 매입 이전
(~0.75x, 매우 낮음)에서 이후 **약 3.25x**로 급등 - leverage_score에
반영했다. 시가총액·순부채 모두 이 매입 **이후** 최신값을 사용했다(내부
일관성 - 어느 한쪽만 과거값을 쓰면 레버리지가 과소평가된다).

## ⚠️ 5y CAGR 창(2021→2026)에 Slack 인수(2021-07 종결, ~$277억) 단계상승
일부 포함 - GEN/BRO/ROP/CROX 계열이나 override 미적용

매출 YoY: FY2021 $212.52억 -> FY2022 $264.92억(+24.65%, Slack 완전편입
첫해) - 5y CAGR(2021 기준, 13.44%->14.34%로 재계산주의: 아래 수치 참고)이
3y(2023기준, 9.82%)·10y(2016기준, 20.07%)보다 다소 높게 나오는 원인.
**BYD(같은 세션)와 달리 오버라이드하지 않았다** - BYD의 2020년은 COVID라는
일시적 외생 충격(BKNG형 저점)이었지만, Salesforce의 M&A(MuleSoft·Tableau·
Slack·Informatica)는 회사의 상시적 핵심 성장전략 자체라 "저점을 피하고
고점을 택한다"는 원칙이 깔끔하게 적용되지 않는다(어느 인수를 "제외"할
근거가 없음 - 지속적 볼트온 M&A는 CROX 선례처럼 그대로 두고
realistic_growth_estimate의 3y 0.5 가중치가 자연히 희석하도록 뒀다).
왜곡폭도 BYD(8.6%p)보다 완만하다(4.5%p).

## ⚠️ FY2027(2026-02~2027-01, 아직 미완결) M&A는 이 데이터셋에 없음

Informatica 인수($80억, 2025-11-18 종결)는 FY2027 Q1~Q2에 매출의 약 4%
(2026-09-04 WebSearch: Q2 FY27 매출 $113.5억 중 $4.56억)를 기여 중이나,
이는 FY2027 연간 실적(아직 미확정)에 해당해 이번 분석의 3y/5y/10y CAGR
창(전부 FY2026 종료 기준)에는 거의 반영되지 않는다(FY2026에 약 2.5개월분,
~$3.5억 미만 추정 - 전체 매출의 1% 미만, 무시 가능한 영향).

## 데이터 함정 - FY2021 capex 태그 오류 정정(v3.60 우선순위 로직의 역설)

`PaymentsToAcquireProductiveAssets`(v3.60 1순위 태그)가 FY2021에 단
$1.5억을 보고했는데, 같은 기간 `PaymentsToAcquirePropertyPlantAndEquipment`
(2순위)는 $7.1억 - 앞뒤 연도(FY2020 $6.43억, FY2022 $7.17억) 추세와
정합적인 건 $7.1억 쪽이다. MCK 선례("넓은 정의가 옳음")와 정반대로 여기선
**좁은 정의가 더 신뢰할 만하다** - 자동선택을 신뢰하지 않고 $7.1억으로
직접 정정했다(LNTH IPR&D 오분류와 동일 계열의 태그 함정). ⚠️ 이 정정은
최종 Realistic Growth에 **영향이 없다** - FCF CAGR이 어느 값을 쓰든
매출가중평균보다 높아(FCF 조건이 바인딩 안 됨) 결과가 동일하다(RYAN
capex 사례와 같은 "정직하게 정정하되 계산결과는 불변" 유형).

## 성장동력 - Agentforce/AI는 아직 소규모, 핵심 성장은 여전히 코어 CRM

Agentforce ARR $15억+(+240%YoY, 단 Q2 FY27부터 Slackbot·Headless 360을
포함하도록 지표 정의가 바뀌어 동일기준 비교가 아님)이나 전체매출의 ~3%
불과 - "핵심 좌석기반 성장 둔화를 AI가 상쇄할 수 있는가"라는 애널리스트
회의론이 실재(Benioff CEO가 직접 반박할 정도로 컨센서스에 영향력 있는
서사). AI에이전트발 SaaS 대체 우려("SaaSpocalypse", 2026년초 소프트웨어
섹터 시총 약 $2조 증발)는 서사 단계이며 **구체적 시장점유율 손실 데이터는
확인되지 않았다**(2026-09-04 WebSearch).

## 실행: python3 scripts/analyze_crm_2026_09_04.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.filing_dates import pit_inputs_for
from engine.pipeline import AnalysisInputs, run_analysis, save_ledger
from engine.provenance import provenance_from_sec_facts

TICKER = "CRM"
UA = "IRS Research chlalsrl1203@gmail.com"
TODAY = "2026-09-04"

# ── SEC XBRL companyfacts 실측(2026-09-04 조회, CIK 0001108524) ──────────
# 회계연도 라벨은 SEC fy 필드 기준(FY2026 = 2025-02~2026-01 결산)
REVENUE = {
    2015: 5373586000.0, 2016: 6667216000.0, 2017: 8437000000.0, 2018: 10540000000.0,
    2019: 13282000000.0, 2020: 17098000000.0, 2021: 21252000000.0, 2022: 26492000000.0,
    2023: 31352000000.0, 2024: 34857000000.0, 2025: 37895000000.0, 2026: 41525000000.0,
}
OPERATING_INCOME = {
    2015: -145633000.0, 2016: 114923000.0, 2017: 64228000.0, 2018: 235768000.0,
    2019: 535000000.0, 2020: 297000000.0, 2021: 455000000.0, 2022: 548000000.0,
    2023: 1030000000.0, 2024: 5011000000.0, 2025: 7205000000.0, 2026: 8331000000.0,
}
OPERATING_CASHFLOW = {
    2015: 1173714000.0, 2016: 1612585000.0, 2017: 2162198000.0, 2018: 2737965000.0,
    2019: 3398000000.0, 2020: 4331000000.0, 2021: 4801000000.0, 2022: 6000000000.0,
    2023: 7111000000.0, 2024: 10234000000.0, 2025: 13092000000.0, 2026: 14996000000.0,
}
CAPEX = {  # FY2021: PaymentsToAcquireProductiveAssets($1.5억) 태그오류 정정 -> PP&E 태그($7.1억) 채택(docstring 참고)
    2015: 290454000.0, 2016: 284476000.0, 2017: 463958000.0, 2018: 534027000.0,
    2019: 595000000.0, 2020: 643000000.0, 2021: 710000000.0, 2022: 717000000.0,
    2023: 798000000.0, 2024: 736000000.0, 2025: 658000000.0, 2026: 594000000.0,
}
NET_INCOME = {  # 참고 기록만 - is_insurer 아니므로 계산에 미사용
    2015: -262688000.0, 2016: -47426000.0, 2017: 179632000.0, 2018: 127478000.0,
    2019: 1110000000.0, 2020: 126000000.0, 2021: 4072000000.0, 2022: 1444000000.0,
    2023: 208000000.0, 2024: 4136000000.0, 2025: 6197000000.0, 2026: 7457000000.0,
}
SBC = {
    2015: 564765000.0, 2016: 593628000.0, 2017: 820367000.0, 2018: 997013000.0,
    2019: 1283000000.0, 2020: 1785000000.0, 2021: 2190000000.0, 2022: 2779000000.0,
    2023: 3279000000.0, 2024: 2787000000.0, 2025: 3183000000.0, 2026: 3509000000.0,
}

# ── 대차대조표(2026-07-31, FY2027 Q2, $250억 부채조달 자사주매입 반영된
#    최신값 - SEC XBRL 실측) ───────────────────────────────────────────
DEBT_LATEST = 39288000000.0  # LongTermDebtNoncurrent(2026-07-31) - Current=0
CASH_LATEST = 8310000000.0   # CashAndCashEquivalentsAtCarryingValue(2026-07-31)
NET_DEBT = DEBT_LATEST - CASH_LATEST  # $30,978,000,000

DA_2026 = 1200000000.0  # DepreciationDepletionAndAmortization(FY2026)
EBITDA = OPERATING_INCOME[2026] + DA_2026  # $9,531,000,000

# ── 시가총액(2026-09-03 Alpha Vantage 종가 + 최신 EntityCommonStockShares) ─
PRICE = 264.43  # Alpha Vantage GLOBAL_QUOTE, 2026-09-03 종가(latestDay)
SHARES_OUT = 823000000.0  # EntityCommonStockSharesOutstanding, 2026-08-20 기준(10-Q)
MARKET_CAP = PRICE * SHARES_OUT  # 약 $217.6B

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
        company_name="Salesforce, Inc.",
        revenue_by_year=REVENUE,
        operating_income_by_year=OPERATING_INCOME,
        operating_cashflow_by_year=OPERATING_CASHFLOW,
        capex_by_year=CAPEX,
        market_cap=MARKET_CAP,
        net_debt=NET_DEBT,
        ebitda=EBITDA,
        risk_free_rate=RF,
        competitor_threat_weights=[0.12, 0.10, 0.08],
        market_share_trend_pp_per_year=-0.3,
        active_antitrust_or_regulatory_case=False,
        demand_sensitivity_pct=0.22,
        subjective_input_basis=(
            "competitor_threat_weights=[0.12(Microsoft Dynamics/Copilot - "
            "거대 플랫폼과 결합된 네이티브 AI 위협), 0.10(HubSpot - SMB/"
            "중견시장 빠른 성장), 0.08(AI네이티브 신흥경쟁 - 'SaaSpocalypse' "
            "서사 단계이며 구체적 시장점유율 손실 데이터는 미확인, 2026-09-04 "
            "WebSearch)]. market_share_trend_pp_per_year=-0.3 - 하드데이터로 "
            "확인된 점유율 손실은 없으나(WebSearch로 확인 실패), Agentforce "
            "ARR이 전체매출의 ~3%에 불과해 핵심 좌석기반 성장둔화를 아직 "
            "상쇄하지 못한다는 점을 반영해 소폭 음수. demand_sensitivity_"
            "pct=0.22 - CLAUDE.md 앵커표 '기업용 필수 SW·전문서비스'(0.20, "
            "CDNS·DSGX·PGR·ROP·BRO·BSY·GWRE·PTC)에 근접하되, 2026년초 "
            "AI에이전트발 소프트웨어섹터 전반 셀오프('SaaSpocalypse', 약 "
            "$2조 시총증발)로 나타난 실제 시장 재평가 리스크를 반영해 소폭 "
            "상향."
        ),
        model_used="two_stage",
        model_choice_reason=(
            "trailing 매출 CAGR(3y 9.82%/5y 14.34%/10y 20.07%)이 "
            "default_terminal_growth(2.0~4.5%)를 크게 상회하고 아직 성숙기에 "
            "도달하지 않은 초대형 SaaS 기업이라 다년 수렴 경로(two_stage)가 "
            "적절하다고 판단. 다만 $250억 부채조달 자사주매입으로 회사가 "
            "직접 FCF성장 가이던스를 절반으로 낮춘 점(2026-09-04 WebSearch) "
            "은 이 수렴경로가 과거 추세보다 완만해질 수 있음을 시사한다."
        ),
        falsification_conditions=(
            "Q3/Q4 FY2027 실적에서 오가닉 매출성장률(Informatica 등 M&A "
            "제외)이 현재 수준(약 6.4%YoY, 2026-09-04 WebSearch 확인)보다 "
            "더 둔화되거나, Agentforce ARR 성장이 정체되거나, FCF성장률이 "
            "회사 자체 하향 가이던스(약 4~5%)조차 못 미치면 이 판정을 "
            "재검토할 것."
        ),
        price_at_analysis=PRICE,
        currency="USD",
        net_income_by_year=NET_INCOME,
        sbc_by_year=SBC,
        data_sources=[
            "SEC XBRL companyfacts (CIK 0001108524, 조회 2026-09-04)",
            "Alpha Vantage GLOBAL_QUOTE (2026-09-03 종가 $264.43)",
            "WebSearch: $250억 부채조달 자사주매입·FCF가이던스 하향, "
            "Informatica 인수(FY2027 Q2 매출기여 4%), Agentforce ARR·"
            "오가닉성장률(6.4%), 경쟁구도(Microsoft/HubSpot/AI네이티브), "
            "애널리스트 컨센서스(2026-09-04 재인용)",
        ],
        **pit,
        provenance=provenance,
    )


if __name__ == "__main__":
    inputs = build_inputs()
    result = run_analysis(inputs)
    path = save_ledger(result)
    print(f"saved: {path}")
