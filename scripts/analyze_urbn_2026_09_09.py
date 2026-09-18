"""
Urban Outfitters, Inc.(URBN) 정식 분석 - 2026-09-09.

경위: research_queue.json 1순위 후보였던 BLDR·QSR·TEAM을 조사한 결과 BLDR은
4분류 3번(진짜나빠짐, 주택경기 하강 - CLAUDE.md 별도 기록, ledger 미생성)으로
확인됐고, TTEK는 RPS 인수(2023) 단계상승이 override 불가능한 3년 CAGR
고정창(years[-4]=2022)에 걸려 FRAMEWORK_MISMATCH로 등록했다(data/
excluded_tickers.json). URBN(스크리너 Gap 추정 +6.99%p, tier A, 시총 근사
~$4.83B)이 다음 순위이자 구조 확인 결과 가장 깨끗했다.

## CAGR 창 확인 - BKNG형 COVID 저점 기저효과, override로 해소

SEC XBRL 매출 실측(FY2009~2026, 회계연도 종료 1월 31일): FY2021(코로나
셧다운 전체 반영) 매출 -13.4%YoY, FY2022 +31.9%(회복). 5년 CAGR 기본
기준연도(`years[-6]`)가 정확히 FY2021(저점)에 걸려 회복반등을 성장으로
착각할 위험이 있다(v3.21 BKNG 원칙과 동일 구조). **기준연도를 FY2020
(코로나 직전 마지막 정상연도)으로 override**했다 - v3.21이 확립한 "저점이
아니라 고점(직전 정상연도)을 고를 것" 원칙을 문자 그대로 적용(BKNG도
"가장 높은 해"를 찾은 게 아니라 "붕괴 직전 해"를 택했다). 3년 CAGR
(`years[-4]`, override 불가, FY2023→2026)은 이 저점 구간을 건드리지
않아 애초에 깨끗하다(8.68%) - override 여부와 무관하게 3y/5y/10y 세
창이 서로 근접해(8.68%/7.55%/6.02%) M&A 왜곡 없는 정상 다년 성장임을
뒷받침한다.

FCF(=OCF-capex)는 FY2020(코로나 직전) $56.46M·FY2026 $315.02M 둘 다
양수라 v3.19 가드에 걸리지 않는다. capex/매출 비중 최근5년평균(4.21%)이
직전5년평균(3.88%)보다 +0.33%p 높을 뿐이라(3%p 미만) capex 재분류
(`capex_classification`)는 적용하지 않았다.

## 순부채 - 사실상 무차입(추정치, 정밀 확인 필요)

FY2026(2026-01-31) 기준 회사 자체 공시가 "무차입(zero long-term debt),
신용한도 $350M 미사용, 현금+시장성증권 유동성 $1.1B+"이라 명시한다.
집계사이트가 보고하는 "총부채 ~$1.226B"는 회계기준(ASC 842) 리스부채를
포함한 값으로 추정된다(CAH·MCK 선례와 동일하게 DebtAndCapitalLeaseObligations
계열 태그를 그대로 채택하는 이 프로젝트의 관례를 따름). 정밀한 현금+
증권 합계를 확보하지 못해 "유동성 $1.1B+" 문구로 근사해
NET_DEBT≈$126M(거의 무차입)으로 산정했다 - leverage_score에 미치는
영향은 제한적이다(R-001/PHASE3 감사가 실측한 대로 DRS→ERP 경로의
민감도 자체가 작다).

## 경쟁구도(2026-09-09 WebSearch)

FY2026(2026-01-31 종료) 매출 사상최대 $6.17B(+11.1%YoY), 세 브랜드
전부 양(+) 동일점포성장(Urban Outfitters +7.3%/Anthropologie +5.9%/
Free People +4.8%, FY26 Q4 기준) - 단일 브랜드 편중이 아니라 포트폴리오
전반의 건강한 성장. Nuuly 구독사업 +50.2%YoY(구독자수 +45.3%)로 특히
가속. 유럽 등 신규 매장 확장(연 54개 신규출점 계획) 중.

실행: python3 scripts/analyze_urbn_2026_09_09.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.filing_dates import pit_inputs_for
from engine.pipeline import AnalysisInputs, run_analysis, save_ledger
from engine.provenance import provenance_from_sec_facts

TICKER = "URBN"
UA = "IRS Research chlalsrl1203@gmail.com"
TODAY = "2026-09-09"
M = 1_000_000

# ── SEC XBRL companyfacts 실측(2026-09-09 조회, FY2009~2026 18개년) ─────
REVENUE = {
    2009: 1834.6 * M, 2010: 1937.8 * M, 2011: 2274.1 * M, 2012: 2473.8 * M,
    2013: 2794.9 * M, 2014: 3086.6 * M, 2015: 3323.1 * M, 2016: 3445.1 * M,
    2017: 3545.8 * M, 2018: 3616.0 * M, 2019: 3950.6 * M, 2020: 3983.8 * M,
    2021: 3449.7 * M, 2022: 4548.8 * M, 2023: 4795.2 * M, 2024: 5153.2 * M,
    2025: 5550.7 * M, 2026: 6165.4 * M,
}
OPERATING_INCOME = {
    2009: 299.44 * M, 2010: 338.98 * M, 2011: 414.2 * M, 2012: 284.73 * M,
    2013: 374.29 * M, 2014: 426.83 * M, 2015: 365.38 * M, 2016: 353.58 * M,
    2017: 338.53 * M, 2018: 259.89 * M, 2019: 381.31 * M, 2020: 231.93 * M,
    2021: 3.97 * M,      # 코로나 셧다운
    2022: 408.57 * M, 2023: 226.62 * M, 2024: 369.8 * M,
    2025: 473.76 * M, 2026: 605.63 * M,
}
OPERATING_CASHFLOW = {
    2009: 251.57 * M, 2010: 325.39 * M, 2011: 385.11 * M, 2012: 282.7 * M,
    2013: 395.68 * M, 2014: 423.15 * M, 2015: 322.32 * M, 2016: 413.42 * M,
    2017: 415.25 * M, 2018: 303.06 * M, 2019: 446.62 * M, 2020: 273.89 * M,
    2021: 285.81 * M, 2022: 359.32 * M, 2023: 142.73 * M, 2024: 509.41 * M,
    2025: 502.83 * M, 2026: 575.19 * M,
}
CAPEX = {
    2009: 112.55 * M, 2010: 109.26 * M, 2011: 143.64 * M, 2012: 190.01 * M,
    2013: 168.88 * M, 2014: 186.1 * M, 2015: 229.8 * M, 2016: 134.95 * M,
    2017: 143.71 * M, 2018: 83.81 * M, 2019: 114.92 * M, 2020: 217.43 * M,
    2021: 159.24 * M, 2022: 262.43 * M, 2023: 199.51 * M, 2024: 199.62 * M,
    2025: 182.58 * M, 2026: 260.17 * M,
}

# 재무상태표(FY2026, 2026-01-31 기준) - 회사 자체 공시(무차입, 신용한도
# 미사용) + 집계사이트 리스부채 포함 총부채. 정밀 현금+증권 합계 미확보라
# "유동성 $1.1B+" 근사치로 산정(위 docstring 참고).
TOTAL_DEBT = 1226 * M           # DebtAndCapitalLeaseObligations 계열(리스부채 포함 추정)
CASH_AND_SECURITIES_APPROX = 1100 * M
NET_DEBT = TOTAL_DEBT - CASH_AND_SECURITIES_APPROX   # ≈ $126M(거의 무차입)

DA_2026 = 128.529 * M            # DepreciationDepletionAndAmortization(FY2026)
EBITDA = OPERATING_INCOME[2026] + DA_2026

# 시가총액: 2026-09-08 종가(Alpha Vantage GLOBAL_QUOTE) x FY2026 10-K 표지
# 발행주식수(2026-04-30 10-Q 기준, dei:EntityCommonStockSharesOutstanding) -
# broad_screen이 쓴 EntityPublicFloat 근사($4.83B)보다 최신이라 이쪽을
# 채택한다(v3.72 한계, OKTA/MEDP/ROKU/CAH와 동일 패턴).
PRICE = 79.43
SHARES_OUT = 89_691_297
MARKET_CAP = PRICE * SHARES_OUT

RF = 0.0477  # 미국 10Y, 2026-09-03 종가(Alpha Vantage TREASURY_YIELD)

SBC = {2026: 30.41 * M}  # us-gaap:ShareBasedCompensation, FY2026(최신연도)만


def build_inputs() -> AnalysisInputs:
    pit = pit_inputs_for(TICKER, TODAY, list(REVENUE), user_agent=UA)
    try:
        from engine.data.providers.sec import fetch_company_facts, ticker_to_cik

        facts = fetch_company_facts(ticker_to_cik(TICKER, UA), UA)
        provenance = provenance_from_sec_facts(facts, TICKER, TODAY, list(REVENUE))
    except Exception:  # noqa: BLE001 - provenance는 부가 기록, 실패해도 분석은 계속
        provenance = None

    return AnalysisInputs(
        ticker=TICKER,
        company_name="Urban Outfitters, Inc.",
        revenue_by_year=REVENUE,
        operating_income_by_year=OPERATING_INCOME,
        operating_cashflow_by_year=OPERATING_CASHFLOW,
        capex_by_year=CAPEX,
        market_cap=MARKET_CAP,
        net_debt=NET_DEBT,
        ebitda=EBITDA,
        risk_free_rate=RF,

        cagr_base_year_override=2020,
        cagr_base_year_override_reason=(
            "기본 5년 기준연도(years[-6]=FY2021)가 코로나 셧다운 저점(매출 "
            "-13.4%YoY, 영업이익 $3.97M로 사실상 0)에 정확히 걸려 회복반등을 "
            "성장으로 착각할 위험이 있다(v3.21 BKNG 원칙). 저점이 아니라 "
            "직전 마지막 정상연도(FY2020, 코로나 셧다운 이전)를 기준으로 "
            "택했다 - '고점을 찾는' 것이 아니라 '붕괴 직전 해'를 택하는 "
            "BKNG 선례의 문자 그대로의 적용."
        ),

        competitor_threat_weights=[0.25, 0.20, 0.15],
        market_share_trend_pp_per_year=0.5,
        active_antitrust_or_regulatory_case=False,
        demand_sensitivity_pct=0.30,
        subjective_input_basis=(
            "경쟁강도: Zara/H&M(패스트패션, 0.25)·American Eagle(중가 캐주얼, "
            "0.20)·Abercrombie&Fitch(0.15)[셋 다 추정치] - URBN은 4개 브랜드"
            "(Urban Outfitters/Anthropologie/Free People/FP Movement)로 "
            "가격대·타겟연령을 분산해 단일 경쟁자 노출도가 낮다. "
            "market_share_trend=+0.5%p: FY2026 3개 브랜드 전부 양의 동일점포"
            "성장(+4.8~7.3%)에 Nuuly 구독 +50.2%YoY까지 겹쳐 점유율 확대 "
            "추세가 뚜렷[2026-09-09 WebSearch로 확인]. active_antitrust=False: "
            "규제·반독점 이슈 없음. demand_sensitivity=0.30: CLAUDE.md 앵커표 "
            "'소비자 구독/플랫폼(재량소비, 대체재 존재)' 버킷(앵커 0.30, 관측범위 "
            "0.20~0.38) - 의류소매는 재량소비 성격이 뚜렷하나 URBN은 다브랜드 "
            "포트폴리오+구독사업 성장으로 앵커값 그대로 채택(이탈 없음)."
        ),

        model_used="two_stage",
        model_choice_reason=(
            "3y/5y(override)/10y 매출 CAGR이 8.68%/7.55%/6.02%로 서로 근접해 "
            "M&A·일회성 왜곡이 없는 정상 다년 성장궤적이다(창이 심하게 갈리면 "
            "왜곡 신호인데 여기선 그렇지 않음). FY2026 성장(+11.1%)이 3y/5y "
            "평균보다 다소 높아 - 신규출점(연 54개)·Nuuly 구독 고성장(+50.2%)"
            "이라는 명확한 성장촉매가 있으나 무기한 지속을 가정하는 "
            "single_stage보다 정상화 경로를 명시하는 two_stage가 보수적이다. "
            "첫 정식분석이라 대조할 과거 기록 없음."
        ),

        falsification_conditions=(
            "(1) FY2027 실적(2027년 3~4월경 예상)에서 세 브랜드(Urban "
            "Outfitters·Anthropologie·Free People) 동일점포성장이 전부 "
            "저성장·감속하면(FY2026 평균 5~7%대 대비) 이 분석이 채택한 "
            "market_share_trend=+0.5%p·demand_sensitivity=0.30 가정을 "
            "재검토한다. (2) Nuuly 구독자수 증가율이 FY2026(+45.3%YoY) "
            "대비 절반 이하로 둔화하면 구독사업 고성장을 성장촉매로 삼은 "
            "근거가 약화된다. (3) 신규출점 계획(연 54개)이 취소·축소되면 "
            "확장전략 지속성을 재검토. (4) 순부채 추정치(NET_DEBT≈$126M, "
            "무차입에 가까움)가 실제 정밀 확인 결과와 크게 다르면(예: 리스부채 "
            "제외 시 순현금 확대) leverage_score 영향을 재확인할 것 - 이 "
            "분석 최대 데이터 근사치다."
        ),

        price_at_analysis=PRICE,
        currency="USD",
        sbc_by_year=SBC,

        data_sources=[
            "SEC XBRL companyfacts, 2026-09-09 조회 - 매출·영업이익·영업현금"
            "흐름·capex 전부 1차자료(FY2009~2026, 18개년)",
            "Alpha Vantage GLOBAL_QUOTE 종가 $79.43(2026-09-08), "
            "TREASURY_YIELD 10Y 4.77%(2026-09-03)",
            "SEC FY2026 10-Q(2026-04-30 기준) dei:EntityCommonStockSharesOutstanding "
            "89,691,297주",
            "WebSearch: FY2026 10-K/Q4 실적발표(브랜드별 동일점포성장·구독·"
            "신규출점 계획), 무차입·유동성 $1.1B+ 공시, 2026-09-09 조회",
        ],

        **pit,
        provenance=provenance,
    )


if __name__ == "__main__":
    result = run_analysis(build_inputs())
    d, g = result["derived"], result["growth"]
    models = result["implied_growth"]["models"]
    print("=" * 96)
    print(f"URBN 정식 분석 ({result['meta']['analyzed_at'][:10]}, 엔진 {result['meta']['engine_version']})")
    print("=" * 96)
    rev10 = "N/A" if d["revenue_cagr_10y"] is None else f"{d['revenue_cagr_10y']*100:.2f}%"
    print(f"  매출 CAGR   3y {d['revenue_cagr_3y']*100:.2f}% / "
          f"{d['cagr_5y_span']}y {d['revenue_cagr_5y']*100:.2f}% / 10y {rev10}")
    print(f"  FCF CAGR    {d['fcf_cagr_5y']*100:.2f}%   FCF0 ${d['fcf0']/1e9:.3f}B "
          f"(FCF수익률 {d['fcf0']/MARKET_CAP*100:.2f}%)")
    print(f"  순부채/EBITDA {d['net_debt_to_ebitda']:.3f}배   시총 ${MARKET_CAP/1e9:.2f}B")
    print(f"  DRS         {result['drs']['score']:.2f}  {result['drs']['components']}")
    print(f"  Lynch       {result['lynch']['used']}   구조적할인 {g['structural_discount_pct']*100:.2f}%")
    print(f"  Realistic   {g['realistic_growth']*100:.2f}%")
    ss = "N/A" if models["single_stage"] is None else f"{models['single_stage']*100:.2f}%"
    ts = "N/A" if models["two_stage"] is None else f"{models['two_stage']*100:.2f}%"
    print(f"  Implied     single {ss} / two {ts} -> "
          f"{result['implied_growth']['value']*100:.2f}% ({result['implied_growth']['model_used']})")
    print(f"  Gap         {result['expectation_gap']*100:+.2f}%p   "
          f"RAR {result['rar']:+.4f}   Confidence {result['confidence']['final']}/100")
    print(f"  ** {result['judgment']} / {result['judgment_grade']}등급 **")
    print(f"  강건성 flip {result['sensitivity_check'].get('judgment_flipped')}   "
          f"PIT {(result['meta'].get('point_in_time') or {}).get('status')}")
    if result.get("sbc_cross_check"):
        s = result["sbc_cross_check"]
        print(f"  SBC/FCF {s.get('sbc_to_fcf_pct', 0)*100:.1f}% -> "
              f"Gap {(s.get('gap_sbc_adjusted') or 0)*100:+.2f}%p")
    for x in result["data_limitations"]:
        print(f"    - {x}")
    print(f"\n저장: {save_ledger(result)}")
