"""
Boyd Gaming Corporation(BYD) 정식 분석 - 2026-09-04.

경위: 연구 우선순위 큐 tier A, 스크리너 Gap 추정 +10.30%p, 시총 근사 $4.3B.
FRAMEWORK_MISMATCH 20종목 배제 뒤 큐 순서상 다음 검증범위 안 후보.

## 원자료 - SEC XBRL companyfacts(1차자료, `SecCompanyFactsProvider`,
2026-09-04 조회, CIK 0000906553, 2015~2025 11개년 확보).

## ⚠️ 이중 왜곡 발견 - COVID 저점 기저효과(BKNG형) + capex 성장투자 재분류
필요(NVO형)가 동시에 걸린 사례

### (1) 5년 CAGR 기준연도(2020)가 COVID 저점 - BKNG 패턴 재현
매출: 2019년 $3,326M(전년比 +26.6%, Pinnacle Entertainment 인수 완전편입
첫해로 추정) -> 2020년 $2,178M(-34.5%, COVID 셧다운) -> 2021년 $3,370M
(+54.7%, 회복). 기본 5y 기준연도(2020, 저점)를 그대로 쓰면 5y CAGR이
13.44%로 나와 3y(4.80%)·10y(6.41%)와 크게 어긋난다(v3.21 BKNG 원칙 -
"기준연도는 저점이 아니라 고점을 고를 것"). **2019년(코로나 이전, Pinnacle
인수 이후 안정화된 첫해)을 기준연도로 오버라이드**했다 - 6y CAGR 3.51%로
3y/10y와 훨씬 정합적이다. 2018->2019 매출 +26.6% 자체가 2018-10월 완결된
Pinnacle 인수의 첫 완전연도 반영으로 추정되나(WebSearch 미확정), 이 M&A
단계상승은 6y 창(2019->2025)의 **바깥**(2018년 이전)에 있어 오버라이드가
새로운 M&A 왜곡을 끌어들이지 않는다.

### (2) capex 급증 - Norfolk VA 리조트 등 실제 성장투자로 확인(NVO형 재분류)
capex/매출 비중이 최근 5년(2021~2025) 평균 9.61%에서 2025년 14.37%로
+4.76%p 급증(v3.20 임계값 3%p 초과). 2026-09-04 WebSearch로 확인한 구체
근거: **Norfolk, VA 리조트**(총 $7.5억 프로젝트, 2025년 중 ~$1.5억 집행,
2025-11 임시카지노 개장·2027년 하반기 정식개장 예정) + **Cadence
Crossing**(Jokers Wild 대체 신규 카지노, 1만sqft·슬롯머신 450대) +
호텔 리노베이션(3개 시설, ~$1억). 2026년 가이던스도 총capex $6.5~7.0억
(유지보수 $2.5억 + Cadence Crossing/Par-A-Dice $0.75억 + Virginia
$2.5~3.0억 + 객실 리노베이션 $0.75억)로 **일시적 급증이 아니라 지속될
예정**임을 회사 스스로 명시 - `capex_classification="growth_investment"`로
분류했다(정합성가드: 매출감속 6.41%y10-4.80%y3=1.61%p < 3%p 허용범위,
경고 미발동).

## ⚠️ 영업이익 감소(2024->2025, -19.3%)의 원인 - 대부분 비현금 손상차손
FY2025 영업이익 $748.4M(전년 $927.8M 대비 -19.3%)는 대부분 **비현금
손상차손 $1.284억**(Las Vegas Locals 세그먼트 ~$0.501억 + Midwest&South
세그먼트 ~$0.783억, 2026-09-04 WebSearch로 10-K 확인)에 기인한다. 나머지는
실질 마진압박(EBITDA마진 31.07%(FY2024)->약 27.4%(Q3'25 시점), 인플레이션
인건비·마케팅비 + 라스베이거스 로컬 시장 신규경쟁 - Red Rock Resorts의
신규 Durango Casino & Resort가 명시적으로 지목됨). **CROX(HEYDUDE 손상
차손) 선례와 동일하게 GAAP 그대로 사용**(임의 정규화 안 함 원칙) - 영업이익
시계열은 조정 없이 그대로 썼다.

## 순부채 - 유차입, net_debt/EBITDA ≈1.61x(준수한 수준)
LongTermDebtNoncurrent+Current(FY2025) $20.456억, 현금 $3.534억,
net_debt $16.922억. EBITDA(FY2025, OPINC+D&A) $10.511억.

## 순이익 급증(2024대비 +219%)은 FanDuel 지분매각 일회성 이익 - FCF·영업이익
계산에는 영향 없음
2025-07-10 Flutter Entertainment에 FanDuel Group 5% 지분을 $17.55억
현금에 매각 완료(2025 Q3 종결) - 세전이익 $17.48억 인식(2026-09-04
WebSearch 확인). 이 일회성 항목은 영업이익·OCF 계산 경로에 들어가지 않아
(투자활동 현금흐름/기타손익 항목) FCF-DCF 계산에는 영향이 없다 - `net_income_
by_year`는 is_insurer가 아니므로 계산에 사용되지 않고 참고 기록으로만
남긴다.

## 경쟁구도(2026-09-04 WebSearch) - 라스베이거스 로컬·중서부/남부 지역 카지노

Penn Entertainment(온라인 공격적 확장)·Caesars(다운타운 라스베이거스·지역
자산 중복, 일부 애널리스트는 Boyd가 Caesars 지역자산 인수 후보라 추측)·
Red Rock Resorts(라스베이거스 로컬 시장 직접경쟁자, 신규 Durango
Casino&Resort가 명시적 경쟁압력으로 지목됨)와 경쟁. "소비자들이 여전히
스트립보다 지역카지노를 선호"(스트립 회귀로 인한 로컬 잠식 반대증거).
온라인 카지노(iGaming)의 오프라인 잠식 여부는 구체 수치 미확인.

## FanDuel/온라인 부문 - 매각 이후 축소되는 성장동력(과거엔 확대 서사였음)

매각 이후(2025-07-01 이후) 변동수익쉐어에서 **고정수수료 시장접근계약
(2038년까지, Iowa/Indiana/Kansas/Louisiana/Pennsylvania)**로 전환,
연 ~$0.65억 비용절감. 그러나 온라인 세그먼트 영업이익/EBITDAR 가이던스가
2025년 $0.50~0.55억 -> 2026년 ~$0.30억으로 **축소** - 향후 성장서사는
온라인이 아니라 육상 카지노 확장(Norfolk·Cadence Crossing)에 있음을
falsification_conditions에 명시.

## 실행: python3 scripts/analyze_byd_2026_09_04.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.filing_dates import pit_inputs_for
from engine.pipeline import AnalysisInputs, run_analysis, save_ledger
from engine.provenance import provenance_from_sec_facts

TICKER = "BYD"
UA = "IRS Research chlalsrl1203@gmail.com"
TODAY = "2026-09-04"

# ── SEC XBRL companyfacts 실측(2026-09-04 조회, CIK 0000906553) ──────────
REVENUE = {
    2015: 2199432000.0, 2016: 2199259000.0, 2017: 2400819000.0, 2018: 2626730000.0,
    2019: 3326119000.0, 2020: 2178490000.0, 2021: 3369810000.0, 2022: 3555377000.0,
    2023: 3738492000.0, 2024: 3930194000.0, 2025: 4091989000.0,
}
OPERATING_INCOME = {
    2015: 344623000.0, 2016: 260627000.0, 2017: 343495000.0, 2018: 355284000.0,
    2019: 472568000.0, 2020: 14263000.0, 2021: 900104000.0, 2022: 981224000.0,
    2023: 901831000.0, 2024: 927777000.0, 2025: 748406000.0,
}
OPERATING_CASHFLOW = {
    2015: 339846000.0, 2016: 302881000.0, 2017: 414864000.0, 2018: 434527000.0,
    2019: 548992000.0, 2020: 289032000.0, 2021: 1010411000.0, 2022: 976111000.0,
    2023: 914516000.0, 2024: 957075000.0, 2025: 976679000.0,
}
CAPEX = {
    2015: 131170000.0, 2016: 160358000.0, 2017: 190464000.0, 2018: 161544000.0,
    2019: 207637000.0, 2020: 175030000.0, 2021: 199452000.0, 2022: 269155000.0,
    2023: 373950000.0, 2024: 400400000.0, 2025: 588215000.0,
}
NET_INCOME = {  # 참고 기록만 - is_insurer 아니므로 계산에 미사용(FanDuel 매각익 포함)
    2015: 47234000.0, 2016: 418003000.0, 2017: 189193000.0, 2018: 115048000.0,
    2019: 157636000.0, 2020: -134700000.0, 2021: 463846000.0, 2022: 639377000.0,
    2023: 620023000.0, 2024: 577952000.0, 2025: 1843273000.0,
}
SBC = {
    2015: 19264000.0, 2016: 15518000.0, 2017: 17413000.0, 2018: 25379000.0,
    2019: 25202000.0, 2020: 9202000.0, 2021: 37773000.0, 2022: 34066000.0,
    2023: 32379000.0, 2024: 29666000.0, 2025: 32146000.0,
}

# ── 대차대조표(FY2025말, 2025-12-31, SEC XBRL 실측) ───────────────────────
DEBT_2025 = 2045569000.0 + 0.0  # LongTermDebtNoncurrent + LongTermDebtCurrent
CASH_2025 = 353413000.0  # CashAndCashEquivalentsAtCarryingValue
NET_DEBT = DEBT_2025 - CASH_2025  # $1,692,156,000

DA_2025 = 302710000.0  # DepreciationDepletionAndAmortization(FY2025)
EBITDA = OPERATING_INCOME[2025] + DA_2025  # $1,051,116,000

# ── 시가총액(2026-09-03 Alpha Vantage 종가 + 최신 EntityCommonStockShares) ─
PRICE = 77.79  # Alpha Vantage GLOBAL_QUOTE, 2026-09-03 종가(latestDay)
SHARES_OUT = 72655414.0  # EntityCommonStockSharesOutstanding, 2026-07-27 기준(10-Q)
MARKET_CAP = PRICE * SHARES_OUT  # 약 $5.65B

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
        company_name="Boyd Gaming Corporation",
        revenue_by_year=REVENUE,
        operating_income_by_year=OPERATING_INCOME,
        operating_cashflow_by_year=OPERATING_CASHFLOW,
        capex_by_year=CAPEX,
        market_cap=MARKET_CAP,
        net_debt=NET_DEBT,
        ebitda=EBITDA,
        risk_free_rate=RF,
        competitor_threat_weights=[0.18, 0.12, 0.10],
        market_share_trend_pp_per_year=-0.5,
        active_antitrust_or_regulatory_case=False,
        demand_sensitivity_pct=0.35,
        subjective_input_basis=(
            "competitor_threat_weights=[0.18(Red Rock Resorts - 라스베이거스 "
            "로컬 시장 직접경쟁자, 신규 Durango Casino&Resort가 실측 경쟁압력으로 "
            "확인됨), 0.12(Caesars Entertainment - 다운타운 라스베이거스·지역 "
            "자산 중복), 0.10(Penn Entertainment - 온라인 공격적 확장)]. "
            "market_share_trend_pp_per_year=-0.5 - Red Rock 신규 카지노발 로컬 "
            "시장 경쟁 심화 + 온라인부문 축소(FanDuel 매각 후 EBITDAR 가이던스 "
            "$0.50~0.55억->$0.30억)를 반영해 음수. demand_sensitivity_pct=0.35 "
            "- 카지노업은 재량소비 지출 성격이 강하나(CLAUDE.md 앵커표 "
            "'여행·레저' 0.55~0.60보다는 낮음 - 지역 카지노는 원거리여행보다 "
            "경기민감도가 낮은 편) 2025년 실측 마진압박(인플레이션 인건비·"
            "마케팅비)이 확인돼 '소비자 구독/플랫폼' 앵커(0.30)보다는 높게 채택."
        ),
        model_used="two_stage",
        model_choice_reason=(
            "trailing 매출 CAGR(3y 4.80%/오버라이드6y 3.51%/10y 6.41%)이 "
            "default_terminal_growth 범위(2.0~4.5%) 안팎이라 성숙기업에 "
            "가까우나, Norfolk VA 리조트(2027년 정식개장 예정)·Cadence "
            "Crossing 등 진행 중인 성장투자가 2026~2027년에 걸쳐 완공되는 "
            "다년 수렴 경로라 two_stage가 적절하다고 판단."
        ),
        cagr_base_year_override=2019,
        cagr_base_year_override_reason=(
            "기본 5년 기준연도(2020)는 COVID 셧다운으로 매출이 -34.5%YoY "
            "급감한 저점 - 그대로 쓰면 5y CAGR이 13.44%로 3y(4.80%)·"
            "10y(6.41%)와 크게 어긋나 '회복 반등'을 '성장'으로 착각하게 "
            "된다(v3.21 BKNG 원칙 - 저점이 아니라 고점을 기준으로). "
            "2019년(코로나 이전, 2018-10월 종결된 Pinnacle Entertainment "
            "인수의 첫 완전편입연도로 추정되나 이 M&A 단계상승 자체는 "
            "2019년 이전에 위치해 6y 창(2019->2025) 밖에 있음)을 기준연도로 "
            "오버라이드 - 6y CAGR 3.51%로 3y/10y와 훨씬 정합적이다."
        ),
        capex_classification="growth_investment",
        capex_classification_basis=(
            "capex/매출 비중이 최근5년평균 9.61%->2025년 14.37%(+4.76%p)로 "
            "급증. 2026-09-04 WebSearch로 확인한 구체 프로젝트: Norfolk, VA "
            "리조트($7.5억 총사업비, 2025년 ~$1.5억 집행, 2025-11 임시카지노 "
            "개장·2027년 하반기 정식개장 예정) + Cadence Crossing(신규 카지노, "
            "Jokers Wild 대체) + 호텔 리노베이션 3개 시설(~$1억). 2026년 "
            "가이던스도 총capex $6.5~7.0억으로 지속 예정 - 일시적 급증이 "
            "아니라 명명된 다년 성장프로젝트. 정합성가드 통과(매출감속 1.61%p "
            "< 3%p 허용범위)."
        ),
        falsification_conditions=(
            "Norfolk VA 리조트가 2027년 하반기 정식개장 이후에도 지역 매출이 "
            "가이던스에 미달하거나, 2026년 온라인부문 EBITDAR가 가이던스"
            "($0.30억)를 크게 하회하거나, Red Rock 신규 카지노발 라스베이거스 "
            "로컬 시장점유율 잠식이 다음 2개 분기 연속 확인되면 이 판정을 "
            "재검토할 것."
        ),
        price_at_analysis=PRICE,
        currency="USD",
        net_income_by_year=NET_INCOME,
        sbc_by_year=SBC,
        data_sources=[
            "SEC XBRL companyfacts (CIK 0000906553, 조회 2026-09-04)",
            "Alpha Vantage GLOBAL_QUOTE (2026-09-03 종가 $77.79)",
            "WebSearch: FanDuel 지분매각($17.55억, 2025-07-10 발표/Q3 종결), "
            "Norfolk VA 리조트·Cadence Crossing 성장투자, 영업이익 손상차손 "
            "$1.284억 구성, 경쟁구도(Red Rock/Caesars/Penn), 온라인부문 "
            "EBITDAR 가이던스(2026-09-04 재인용)",
        ],
        **pit,
        provenance=provenance,
    )


if __name__ == "__main__":
    inputs = build_inputs()
    result = run_analysis(inputs)
    path = save_ledger(result)
    print(f"saved: {path}")
