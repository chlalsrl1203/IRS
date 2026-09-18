"""
Erie Indemnity Company(ERIE) 정식 분석 - 2026-09-11.

경위: 연구 우선순위 큐(2026-08-30 대규모 스크리닝, tier S, 검증범위 안 ·
1회 연속통과) 순서상 BLDR(4분류3번, 시점부 배제라 영구등록 안 함) ·
STRL(FRAMEWORK_MISMATCH, 2026년 CEC/Stone Ridge 인수로 90%YoY 매출급증
- FY2026 연차 XBRL 반영 전) 다음 후보.

## ⚠️ 사업모델이 PGR/ACGL/SIGI/CINF/RLI와 다르다 - is_insurer=False 채택

Erie Indemnity는 손해보험 언더라이터가 아니라 **Erie Insurance Exchange**
(상호보험조합)를 대신해 판매·언더라이팅·보험금처리 등 관리서비스를 제공하고
그 대가로 **직접·인수 보험료의 최대 25%(계약상 상한, 이사회가 매년 재확인 -
2026-01-01부터도 25% 유지, WebSearch로 확인)를 관리수수료로 받는 fee-based
서비스업체**다. 언더라이팅 리스크(준비금·손해율·재보험)는 전부 Exchange가
부담하고 Indemnity의 대차대조표에는 없다 - PGR/ACGL/SIGI/CINF/RLI가 쓰는
`is_insurer=True`(플로트 성장으로 OCF가 부풀려지는 문제를 보정)의 전제
자체가 성립하지 않는다. 대신 RYAN/BRO(보험중개·유통사, 마찬가지로 리스크를
직접 부담하지 않음)의 선례를 따라 `is_insurer=False`로 일반 FCF-DCF
경로를 그대로 쓴다.

## 원자료 - SEC XBRL companyfacts(1차자료, `SecCompanyFactsProvider`,
2026-09-11 조회, CIK 0000922621).

## ⚠️ 회계정의 단절(2014→2015, -75.4%) - 창 밖에 두어 회피

2008~2014년 매출은 Erie Insurance Exchange의 보험료를 연결 매출로 잡던
구시대 표시방식이고, 2015년부터 관리수수료·서비스수수료만 인식하는 방식으로
바뀌어 매출이 $6.12B→$1.51B로 75.4% 급락한다(CROX/CHDN급이 아니라 그보다
훨씬 큰 순수 정의 단절 - M&A가 아니라 회계표시 방법 변경). **2016년부터만
입력값을 채택**해(3y/5y 창이 각각 2022/2020 기준이라 이 단절과 무관하고,
10y 창은 데이터가 10개년뿐이라 5y로 자동 대체돼 이 문제를 원천 회피한다)
`cagr_base_year_override` 없이 진행했다. 2018년 +40.8% 단계상승도 확인했으나
(ASC 606 도입 추정, 원인 미확정) 3y/5y 창 어느 경계도 안 건드려 영향 없다.

## capex 2015년 결측 - 창을 2016년부터로 통일

`PaymentsToAcquireProductiveAssets`(METRIC_TAGS 1순위)가 2018년부터만
존재하고, 다른 어떤 capex 태그도 2015~2017년 데이터가 없다(회사가 그
이전엔 별도 태그로 보고하지 않은 것으로 추정). revenue/OCF/net_income/
equity/dividends는 전부 2016년부터 확보 가능해 **전 계열을 2016년으로
통일**했다(10개년 - 10y CAGR은 자동으로 5y 대체, 엔진이 `data_limitations`
에 그 사실을 명시한다).

## ⭐ 핵심 리스크 - 트레일링 CAGR이 2026년 실제 감속을 못 본다
(KEYS/KLAC의 정반대 원인, 같은 구조)

2026-09-11 WebSearch로 확인: Q1 2026 직접보험료(DWP) +3.6%YoY·정책건수
-1.7%YoY(공격적 보험료 인상이 유지율을 88%까지 끌어내림), 2026 상반기
대리점수수료가 전년동기 대비 $72.7M 증가(대리점 인센티브 확대 + 보험료
증가가 원인)로 마진 압박. 3y/5y CAGR(2022→2025 기준 매출 12.72%/FCF
23.94%, 2020→2025 기준 매출 9.92%/FCF 14.74%)은 전부 **2025년까지의
연차 실적**이라 이 2026년 실제 감속(대리점 유지율 하락+수수료비용 급증)을
반영하지 못한다 - KEYS/KLAC이 'trailing CAGR이 AI 수요 인플렉션을 과소
추정'했던 것과 원인은 반대(여기는 과대추정 위험)지만 구조는 동일하다
(최근 1~2개 분기 변곡점이 5년 CAGR에 few-quarter 영향만 줘 희석됨).
1개년 미만 데이터(Q1 2026 한 개 분기)라 KEYS 기준(다년 실현 필요)에 못
미쳐 `realistic_growth_override`는 쓰지 않고 falsification_conditions에
최우선 재검토 사유로 명시했다.

## 재무상태표 - 부채 사실상 없음, 순현금

Total debt $63.16M(2026-06-30, WebSearch) vs 현금 $569M(같은 시점) - 순현금
$505.84M. D&A는 `DepreciationDepletionAndAmortization` 태그(FY2025
$69.45M) - RLI/PGR/SIGI와 달리 별도 `Depreciation`(고정자산만) 태그가
없어 이 넓은 정의를 그대로 썼다(감가상각+상각 합산, 무형자산 상각이 크지
않은 서비스업이라 왜곡 우려는 낮다고 판단).

## 경쟁구도(2026-09-11 WebSearch)

Erie는 중부대서양·중서부 12개주+DC 한정 지역 독립대리점 전용 판매모델로
전통적으로 높은 고객충성도·낮은 손해율을 유지해왔으나, 2024~2026년 공격적
보험료 인상(손해율 급등에 대응)이 State Farm·Progressive·GEICO 등 저가
직접판매 경쟁자로의 이탈을 실제로 촉발했다(유지율 88%까지 하락, 정책건수
YoY 역성장 - 실측 확인). `market_share_trend_pp_per_year`를 음수(-0.5)로
채택 - 정책건수 역성장이 실제 관측치이나 단일분기라 극단값(-2.0 이상)은
피했다.

## 실행: python3 scripts/analyze_erie_2026_09_11.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.filing_dates import pit_inputs_for
from engine.pipeline import AnalysisInputs, run_analysis, save_ledger
from engine.provenance import provenance_from_sec_facts

TICKER = "ERIE"
UA = "IRS Research chlalsrl1203@gmail.com"
TODAY = "2026-09-11"

REVENUE = {
    2016: 1596631000.0, 2017: 1691774000.0, 2018: 2382212000.0,
    2019: 2477298000.0, 2020: 2536489000.0, 2021: 2633977000.0,
    2022: 2840124000.0, 2023: 3268940000.0, 2024: 3795115000.0,
    2025: 4067258000.0,
}
OPERATING_INCOME = {
    2016: 292364000.0, 2017: 288372000.0, 2018: 344343000.0,
    2019: 357339000.0, 2020: 338157000.0, 2021: 318097000.0,
    2022: 376214000.0, 2023: 520256000.0, 2024: 676455000.0,
    2025: 717184000.0,
}
OPERATING_CASHFLOW = {
    2016: 254336000.0, 2017: 197126000.0, 2018: 263585000.0,
    2019: 364527000.0, 2020: 342595000.0, 2021: 402794000.0,
    2022: 366152000.0, 2023: 381205000.0, 2024: 611249000.0,
    2025: 686657000.0,
}
CAPEX = {
    2016: 25208000.0, 2017: 28927000.0, 2018: 56297000.0,
    2019: 102039000.0, 2020: 55528000.0, 2021: 148800000.0,
    2022: 67204000.0, 2023: 92647000.0, 2024: 124845000.0,
    2025: 115692000.0,
}
NET_INCOME = {
    2016: 210366000.0, 2017: 196999000.0, 2018: 288224000.0,
    2019: 316821000.0, 2020: 293304000.0, 2021: 297860000.0,
    2022: 298569000.0, 2023: 446061000.0, 2024: 600314000.0,
    2025: 559335000.0,
}
SHAREHOLDERS_EQUITY = {
    2016: 816910000.0, 2017: 857344000.0, 2018: 973672000.0,
    2019: 1133253000.0, 2020: 1188048000.0, 2021: 1342478000.0,
    2022: 1448408000.0, 2023: 1662835000.0, 2024: 1987258000.0,
    2025: 2283374000.0,
}
DIVIDENDS_PAID = {
    2016: 135985000.0, 2017: 145765000.0, 2018: 156474000.0,
    2019: 167651000.0, 2020: 272902000.0, 2021: 192801000.0,
    2022: 206772000.0, 2023: 221675000.0, 2024: 237508000.0,
    2025: 254275000.0,
}

DA_2025 = 69450000.0  # DepreciationDepletionAndAmortization (넓은 정의)
EBITDA = OPERATING_INCOME[2025] + DA_2025

DEBT = 63160000.0     # WebSearch, 2026-06-30 기준(10-Q)
CASH = 569000000.0    # WebSearch, 2026-06-30 기준(10-Q)
NET_DEBT = DEBT - CASH  # 순현금 -$505.84M

PRICE = 240.40  # Alpha Vantage GLOBAL_QUOTE, 2026-09-10 종가
# Class A 46,189,068주 + Class B 2,542주(전환비율 1:2,400 - 경제적 지분
# 동일가치로 환산) - WebSearch(2026-04-17 10-Q 표지) 및 총주식수 보도치
# (52.29M)와 정합
SHARES_OUT = 46189068.0 + 2542.0 * 2400.0
MARKET_CAP = PRICE * SHARES_OUT

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
        company_name="Erie Indemnity Company",
        revenue_by_year=REVENUE,
        operating_income_by_year=OPERATING_INCOME,
        operating_cashflow_by_year=OPERATING_CASHFLOW,
        capex_by_year=CAPEX,
        market_cap=MARKET_CAP,
        net_debt=NET_DEBT,
        ebitda=EBITDA,
        risk_free_rate=RF,
        competitor_threat_weights=[0.30, 0.20],
        market_share_trend_pp_per_year=-0.5,
        active_antitrust_or_regulatory_case=False,
        demand_sensitivity_pct=0.20,
        subjective_input_basis=(
            "competitor_threat_weights=[0.30(State Farm - 지역 중첩시장 "
            "최대 경쟁자, 대규모 자본력·브랜드), 0.20(Progressive/GEICO - "
            "가격민감 이탈고객을 흡수하는 저가 직접판매 채널, 2026년 Erie "
            "유지율 하락(88%)의 주된 도피처로 추정)]. "
            "market_share_trend_pp_per_year=-0.5 - Q1 2026 정책건수 "
            "-1.7%YoY 실측(WebSearch) 확인, 단일분기라 극단값은 피했다. "
            "demand_sensitivity_pct=0.20 - CINF/SIGI/RLI(0.18) 대비 소폭 "
            "상향, 공격적 보험료 인상에 실제 고객이탈(유지율 88%까지 하락)이 "
            "확인된 유일한 사례라 순수 추정치가 아닌 실측 근거가 있다."
        ),
        model_used="two_stage",
        model_choice_reason=(
            "PGR/ACGL/SIGI/CINF/RLI 선례와 동일하게 two_stage 채택 - "
            "2016~2025년 매출이 M&A 단계상승 없이 꾸준히 성장($1.60B->"
            "$4.07B)했고, fee-based 관리서비스업 특성상 완만한 다년 수렴 "
            "성장 궤적이 이론적으로 부합한다. 다만 아래 반증조건(1)이 "
            "이미 트레일링 CAGR의 신뢰도에 의문을 제기하고 있음을 명시."
        ),
        falsification_conditions=(
            "(1) [최우선] 2026 하반기~2027년 실적에서 직접보험료 성장률이 "
            "3~5%대 저성장으로 고착되거나 정책건수 역성장이 2개 분기 이상 "
            "이어지면 - 트레일링 CAGR(매출가중평균 약 11%)이 2026년 실제 "
            "감속을 과대추정했을 가능성이 높아 재검토 필요(KEYS/KLAC과 "
            "원인은 반대이나 구조는 동일한 'trailing CAGR이 최근 변곡점을 "
            "못 본다' 패턴). (2) 대리점 유지율이 85% 밑으로 추가 하락하거나 "
            "대리점수수료 증가율이 2개 분기 이상 보험료 증가율을 앞서면 "
            "마진압박 구조화로 재검토. (3) 관리수수료율(현재 25% 상한 유지)이 "
            "이사회 결의로 인하되면 즉시 재검토(수수료율은 매출의 직접 "
            "승수라 어떤 성장추정도 무효화한다)."
        ),
        price_at_analysis=PRICE,
        currency="USD",
        is_insurer=False,
        data_sources=[
            "SEC XBRL companyfacts (CIK 0000922621, 조회 2026-09-11)",
            "Alpha Vantage GLOBAL_QUOTE (2026-09-10 종가 $240.40)",
            "WebSearch: 10-Q 표지 주식수(2026-04-17 기준, Class A/B), "
            "부채·현금(2026-06-30 10-Q), 관리수수료율 25% 유지(2026-01-01 "
            "이사회 결의), Q1/Q2 2026 실적 - DWP +3.6%/정책건수 -1.7%/"
            "유지율 88%/대리점수수료 +$72.7M(2026 상반기 YoY)",
        ],
        **pit,
        provenance=provenance,
    )


if __name__ == "__main__":
    inputs = build_inputs()
    result = run_analysis(inputs)
    path = save_ledger(result)
    print(f"saved: {path}")
