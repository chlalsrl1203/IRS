"""
HealthEquity, Inc.(HQY) 정식 분석 - 2026-09-08.

경위: 연구 우선순위 큐 1순위(스크리너 추정 Gap +7.23%p, tier A, 시총 근사
$7.00B). 직전 순위였던 QSR(Restaurant Brands)은 COVID 저점 기저효과(2020)
+ Carrols 인수 M&A 단계상승(2024, override로 3y CAGR 시작연도를 못 피함) 이중
왜곡으로 CHDN과 동일 사유로 `data/excluded_tickers.json`에 FRAMEWORK_MISMATCH
등록했다.

## M&A 왜곡 사전점검 - 통과

HQY는 2019-08 WageWorks 인수(대형 HSA/복리후생 관리업체)로 매출이 FY2019
$287.2M -> FY2020 $532.0M(+85.2%)로 급증했다. **그러나 이 단계상승은 3y/5y
CAGR 창 어디에도 걸리지 않는다** - 14개년 시계열(2013~2026)에서 5y 기준연도는
`years[-6]`=2021(WageWorks 완전편입 이후), 3y 기준연도는 `years[-4]`=2023으로
둘 다 인수 이후다. 10y 기준연도(`years[-11]`=2016)만 이 단계상승을 포함하나
가중치 0.2뿐이라(CROX 선례와 동일한 희석 메커니즘) 별도 조치 없이 진행했다.
2021년 이후 YoY는 +3.1%/+13.9%/+16.0%/+20.0%/+9.5%로 단계상승 없는 매끄러운
가속-감속 패턴이다.

## ⭐ 핵심 발견 - 영업이익 변동성의 원인이 금리 사이클이다(구조적, 일시적 아님)

영업이익이 FY2021 $34.0M -> FY2022 **-$24.2M(적자)** -> FY2023 $9.1M ->
FY2024 $117.7M -> FY2025 $162.3M -> FY2026 $322.5M로 극심하게 요동친다.
WebSearch로 원인을 확인했다 - HQY 매출의 상당 부분이 HSA 현금잔고에 대한
**수탁/이자수익**(custodial/interest revenue)인데, 이게 2021~2022년 제로금리
시대에 붕괴했다가 2023~2026년 고금리 국면에서 급팽창했다. 회사 스스로 10-K에
"금리 하락이 사업에 부정적 영향을 줄 수 있다"고 명시하며, 부분적으로 Treasury
채권 선도헤지와 "Enhanced Rates"(보험연금 배치, 은행예치보다 안정적) 비중
확대로 위험을 완화 중이다. **엔진의 margin_volatility가 최근 5개년
(2022~2026)을 그대로 보므로 이 금리 사이클이 DRS의 변동성 점수에 자동
반영된다** - BSX의 COVID 저마진(2020)이 cyclicality를 밀어올린 것과 같은
메커니즘이며, 별도 조치 없이 진행했다.

## 경쟁구도(2026-09-08 WebSearch)

HQY가 미국 HSA 수탁자산 1위(2021년 Optum 추월, $37.9B/+14%YoY, 계좌
~1,070만개), 상위 4개사(HQY/Optum/Fidelity/HSA Bank)가 전체 시장($159B,
Devenir 2025중반)의 약 2/3을 점유. 신규 HSA 판매도 +24%YoY로 시장성장률을
상회해 점유율이 최소 하락 중은 아님을 시사(정밀 추세 데이터는 미확보).
경쟁강도는 Optum(UnitedHealth 계열 대형 통합경쟁자)·Fidelity(대형 브랜드·
유통망을 앞세운 진출)·기타(WEX·HSA Bank·지역은행계)로 구성.

## ⚠️ 데이터 브리치(2024-03) - 반독점/경쟁 리스크와 별개로 취급

2024-03 벤더(Conduent) SharePoint 계정 침해로 430만명 개인정보(주민번호·
건강정보 포함) 유출이 확인됐다. 집단소송이 진행 중이나 주 피고는 벤더
Conduent이고, 규제제재·매출 이탈 등 실질적 재무영향은 확인되지 않았다(미해결
불확실성으로 정직하게 남김). `active_antitrust_or_regulatory_case`는
반독점/경쟁규제 소송 전용 필드라 데이터브리치 소송을 여기 넣지 않고
False로 두었다 - 대신 falsification_conditions에 별도 반영했다.

## 성장률 - 회사 가이던스가 trailing보다 낮다(override 기준 미달)

FY2027 가이던스 매출 $1.410~1.420B(중간값 대비 +7.4~8.1%YoY, Q2 FY27 실적
+8%YoY로 이미 부합)가 trailing 3y/5y CAGR(약 15%/12%)보다 뚜렷이 낮다 -
TCOM/GEN/BRO/RYAN류 패턴이나, 이번엔 회사가 그 배경(WageWorks 기저효과 소진 +
정상화)을 명시적으로 설명하고 있어 신뢰할 만한 정상화 신호다. 다만 **1개년
가이던스뿐**이라 ROP가 확립한 override 기준(다년 실현 오가닉)에 못 미쳐
`realistic_growth_override`는 쓰지 않고 model_choice_reason·
falsification_conditions에 병기했다.

원자료: SEC XBRL companyfacts(CIK 0001428336), 2026-09-08 조회. 회계연도는
매년 1월 31일 종료(FY2026 = 2025-02-01~2026-01-31). FY2026 10-K는
2026-03-17 제출.

실행: python3 scripts/analyze_hqy_2026_09_08.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.filing_dates import pit_inputs_for
from engine.pipeline import AnalysisInputs, run_analysis, save_ledger
from engine.provenance import provenance_from_sec_facts

TICKER = "HQY"
UA = "IRS Research chlalsrl1203@gmail.com"
TODAY = "2026-09-08"
M = 1_000_000

# ── SEC XBRL companyfacts 실측(2026-09-08 조회, FY2013~2026 14개년) ──────
REVENUE = {
    2013: 46.088 * M, 2014: 62.015 * M, 2015: 87.855 * M, 2016: 126.786 * M,
    2017: 178.370 * M, 2018: 229.525 * M, 2019: 287.243 * M, 2020: 531.993 * M,
    2021: 733.570 * M, 2022: 756.556 * M, 2023: 861.748 * M, 2024: 999.587 * M,
    2025: 1199.774 * M, 2026: 1313.429 * M,
}
OPERATING_INCOME = {
    2013: 7.092 * M, 2014: 11.524 * M, 2015: 16.873 * M, 2016: 26.143 * M,
    2017: 41.212 * M, 2018: 54.418 * M, 2019: 77.670 * M, 2020: 77.006 * M,
    2021: 34.014 * M,
    2022: -24.238 * M,   # 제로금리기 수탁/이자수익 붕괴
    2023: 9.057 * M,
    2024: 117.699 * M, 2025: 162.334 * M, 2026: 322.456 * M,
}
OPERATING_CASHFLOW = {
    2013: 11.770 * M, 2014: 18.015 * M, 2015: 15.046 * M, 2016: 26.541 * M,
    2017: 45.591 * M, 2018: 81.702 * M, 2019: 113.422 * M, 2020: 105.010 * M,
    2021: 181.619 * M, 2022: 140.995 * M, 2023: 150.650 * M, 2024: 242.826 * M,
    2025: 339.856 * M, 2026: 457.094 * M,
}
CAPEX = {
    2013: 0.831 * M, 2014: 1.595 * M, 2015: 1.712 * M, 2016: 2.376 * M,
    2017: 3.645 * M, 2018: 5.458 * M, 2019: 3.869 * M, 2020: 7.286 * M,
    2021: 13.093 * M, 2022: 8.908 * M, 2023: 3.371 * M, 2024: 1.694 * M,
    2025: 2.084 * M, 2026: 1.969 * M,
}
SBC = {
    2013: None, 2026: 73.063 * M,  # 최근연도만 확보(SBC 차감 교차검증용)
}

# 재무상태표(FY2026, 2026-01-31 기준, SEC XBRL)
CASH = 318.927 * M
TOTAL_DEBT = 957.379 * M       # LongTermDebt(전액 비유동)
NET_DEBT = TOTAL_DEBT - CASH   # $638.452M

DA_2026 = 154.657 * M          # DepreciationDepletionAndAmortization
EBITDA = OPERATING_INCOME[2026] + DA_2026

# 시가총액: 2026-09-04 종가 x 최신 발행주식수(2026-07-31, 10-Q 표지)
PRICE = 96.07
SHARES_OUT = 82_909_000
MARKET_CAP = PRICE * SHARES_OUT

RF = 0.0477  # 미국 10Y, 2026-09-03 종가(Alpha Vantage TREASURY_YIELD, CAH와 동일 조회값)


def build_inputs() -> AnalysisInputs:
    years = list(REVENUE)
    pit = pit_inputs_for(TICKER, TODAY, years, user_agent=UA)
    try:
        from engine.data.providers.sec import fetch_company_facts, ticker_to_cik

        facts = fetch_company_facts(ticker_to_cik(TICKER, UA), UA)
        provenance = provenance_from_sec_facts(facts, TICKER, TODAY, years)
    except Exception:  # noqa: BLE001 - provenance는 부가 기록, 실패해도 분석은 계속
        provenance = None

    return AnalysisInputs(
        ticker=TICKER,
        company_name="HealthEquity, Inc.",
        revenue_by_year=REVENUE,
        operating_income_by_year=OPERATING_INCOME,
        operating_cashflow_by_year=OPERATING_CASHFLOW,
        capex_by_year=CAPEX,
        market_cap=MARKET_CAP,
        net_debt=NET_DEBT,
        ebitda=EBITDA,
        risk_free_rate=RF,

        competitor_threat_weights=[0.30, 0.30, 0.20],
        market_share_trend_pp_per_year=0.0,
        active_antitrust_or_regulatory_case=False,
        demand_sensitivity_pct=0.15,
        subjective_input_basis=(
            "competitor_threat_weights=[0.30, 0.30, 0.20][전부 추정치] - HQY는 "
            "미국 HSA 수탁자산 1위(2021년 Optum 추월, $37.9B/+14%YoY, 계좌 "
            "~1,070만개)이나 상위 4개사(HQY/Optum/Fidelity/HSA Bank)가 시장의 "
            "약 2/3을 점유하는 과점구조. Optum(UnitedHealth 계열, 대형 통합 "
            "경쟁자) 0.30, Fidelity(대형 브랜드·유통망 기반 진출) 0.30, "
            "WEX·HSA Bank 등 기타(0.20). CAH/MCK/COR(3사 완전과점, [0.35,0.30,"
            "0.25])보다 다소 낮춘 이유는 HQY가 실제 시장선도자이고 신규HSA "
            "판매(+24%YoY)가 시장성장률을 상회해 점유율이 확대 국면이기 "
            "때문이다. market_share_trend=0.0[추정치] - 정밀 pp 추세 데이터는 "
            "미확보이나 최근 자산성장률·신규판매 증가율이 시장평균을 상회해 "
            "하락으로 볼 근거가 없어 중립(하락 벌점 없음, 상승 가점도 없음) "
            "채택. active_antitrust_or_regulatory_case=False - 2024-03 데이터"
            "브리치(벤더 Conduent 경유, 430만명 개인정보 유출) 집단소송이 "
            "진행 중이나 반독점·경쟁규제 소송이 아니라 별도 리스크로 "
            "falsification_conditions에 반영했다. demand_sensitivity_pct=0.15"
            "[추정치, 앵커 이탈] - CLAUDE.md 앵커표의 '헬스케어·필수소비재 "
            "반복매출'(0.12)과 '기업용 필수 SW·전문서비스(계약기반, 전환비용 "
            "높음)'(0.20) 사이 값을 택했다 - HSA 관리는 건강 관련 필수성과 "
            "B2B 다년계약(고용주가 수탁자를 선택하면 직원 계좌 이전 복잡성 "
            "때문에 전환비용이 높음)을 동시에 갖는 하이브리드 성격이라 어느 "
            "한쪽 앵커에도 완전히 들어맞지 않는다."
        ),

        model_used="two_stage",
        model_choice_reason=(
            "trailing 3y/5y 매출 CAGR(약 15%/12%)이 회사 자체 FY2027 가이던스"
            "(매출 +7.4~8.1%YoY, Q2 FY27 실적 +8%YoY로 이미 부합)보다 뚜렷이 "
            "높다 - 회사 스스로 이 감속을 WageWorks 인수 기저효과 소진과 "
            "정상화로 설명한다(1개년 가이던스뿐이라 ROP 기준(다년 실현)에 "
            "못 미쳐 realistic_growth_override는 쓰지 않았다). trailing "
            "고성장이 무기한 지속된다고 가정하는 single_stage보다 터미널 "
            "성장률로 수렴하는 경로를 명시하는 two_stage가 이 정상화 신호와 "
            "정합적이다. 첫 정식분석이라 대조할 과거 기록 없음."
        ),

        falsification_conditions=(
            "(1) FY2027 실제 매출성장률이 회사 가이던스(+7.4~8.1%) 대비 5% "
            "미만으로 크게 미달하면 재검토 - 이 분석의 Realistic Growth가 "
            "trailing CAGR에 기반해 가이던스보다 여전히 높을 수 있다. "
            "(2) 2024년 초 발생한 데이터브리치 집단소송(주피고 벤더 Conduent)에서 "
            "HealthEquity 자신에게 중대한 배상책임·규제제재가 확정되거나, "
            "회사가 고객 이탈을 공시하면 즉시 재검토 - 현재는 재무영향이 "
            "확인되지 않은 미해결 불확실성이다. (3) 연준이 2026~2027년 "
            "금리를 큰 폭 인하하고 회사의 수탁/이자수익이 실제로 뚜렷이 "
            "감소하면 영업이익 경로 재검토 - FY2022~2026 이익 확장의 상당 "
            "부분이 물량 증가가 아니라 금리 상승에 기인했을 수 있다(회사 "
            "자신이 이 리스크를 10-K에 명시). (4) Optum·Fidelity가 HSA "
            "수탁자산 점유율을 HQY로부터 유의미하게 뺏어온다는 공시·데이터가 "
            "나오면 competitor_threat_weights 상향 재검토."
        ),

        price_at_analysis=PRICE,
        currency="USD",

        sbc_by_year={2026: 73.063 * M},

        data_sources=[
            "SEC XBRL companyfacts(CIK 0001428336), 2026-09-08 조회 - 매출·"
            "영업이익·영업현금흐름·capex·SBC·D&A·현금·장기부채·발행주식수 "
            "전부 1차자료",
            "SEC 10-Q(2026-08-27 제출) dei 발행주식수 82,909,000주(2026-07-31 "
            "기준)",
            "Alpha Vantage GLOBAL_QUOTE 종가 $96.07(2026-09-04), "
            "TREASURY_YIELD 10Y 4.77%(2026-09-03)",
            "WebSearch: HSA 시장점유율(Devenir 2025중반 자료)·2024-03 데이터"
            "브리치 경과·금리민감도 관련 회사 10-K 공시·FY2027 가이던스"
            "(2026-08-31 Q2 FY2027 실적발표), 2026-09-08 조회",
        ],

        **pit,
        provenance=provenance,
    )


if __name__ == "__main__":
    result = run_analysis(build_inputs())
    d, g = result["derived"], result["growth"]
    models = result["implied_growth"]["models"]
    print("=" * 96)
    print(f"HQY 정식 분석 ({result['meta']['analyzed_at'][:10]}, 엔진 {result['meta']['engine_version']})")
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
