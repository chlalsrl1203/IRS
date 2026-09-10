"""
LFUS(Littelfuse) 정식분석 - 연구 우선순위 큐 신규 후보.

핵심 확인사항들:

1. **52/53주 회계연도 라벨 재구성 필요** - SEC 자동추출이 `[회계연도 라벨
   충돌]` 경고를 내고 2015·2021년을 통째로 누락시킨다(CDNS/GEN 선례와
   동일 함정). 원자료(period_start/period_end) 각 기간의 **중간일자가
   속한 달력연도**로 라벨을 재구성해 17개년(FY2009~2025) 전체를 확보했다
   - WebSearch로 두 지점(FY2021 "+44%총/+33%오가닉", FY2024 "$2,190.8M,
     -7.3%") 재확인해 라벨링이 정확함을 교차검증했다.

2. **QCOM(2026-08-14)과 동일한 반도체 사이클 패턴 - override 불필요로
   확정** - 3y CAGR 기준연도(years[-4]=2022)가 반도체 공급망 부족발
   수요폭증의 사이클 정점이라(2022 매출 $2,514M, 사상 최고) 3y CAGR이
   음수(-1.72%)로 나오고, 5y 기준연도(2020)는 반대로 코로나 저점이라
   5y CAGR이 높게(10.54%) 나온다 - 두 왜곡이 서로 반대방향이라 완전히
   상쇄되진 않지만, QCOM이 이미 같은 구조("3y CAGR 0.06%[2022 정점기준]
   vs 5y 13.48%[2020 저점기준])을 cyclical 분류로 정상 처리"한 선례가
   있어 별도 override 없이 진행한다. 10y CAGR(10.64%, 2015년 기준 -
   양끝 다 사이클 극단이 아님)이 가장 신뢰할 만한 장기 성장 신호다.

3. **FY2025 영업이익 급감(-76.4%, $158.8M→$37.5M)은 비현금 영업권
   손상차손($301.2M, 반도체 사업부 대상)이 원인** - CROX(HEYDUDE)·
   BYD(카지노) 선례와 동일하게 GAAP 그대로 사용(임의 정규화 안 함).
   OCF는 오히려 개선(FY2024 $367.6M→FY2025 $433.8M, +18%)돼 FCF-DCF
   계산 자체(fcf0)에는 영향이 제한적 - margin_volatility/DRS 경로에서만
   반영된다.
"""
from engine.filing_dates import pit_inputs_for
from engine.pipeline import AnalysisInputs, run_analysis, save_ledger
from engine.provenance import provenance_from_sec_facts

TICKER = "LFUS"
COMPANY = "Littelfuse, Inc."
TODAY = "2026-09-09"
UA = "IRS Research chlalsrl1203@gmail.com"
M = 1_000_000

# 52/53주 회계연도 - 원자료(start,end)의 중간일자가 속한 달력연도로 재구성.
REVENUE = {
    2009: 430147000.0, 2010: 608021000.0, 2011: 664955000.0, 2012: 667913000.0,
    2013: 757853000.0, 2014: 851995000.0, 2015: 867864000.0, 2016: 1056159000.0,
    2017: 1221534000.0, 2018: 1718468000.0, 2019: 1503873000.0, 2020: 1445695000.0,
    2021: 2079928000.0, 2022: 2513897000.0, 2023: 2362657000.0, 2024: 2190768000.0,
    2025: 2386294000.0,
}
OPERATING_INCOME = {
    2009: 13695000.0, 2010: 107574000.0, 2011: 113904000.0, 2012: 106870000.0,
    2013: 129881000.0, 2014: 133830000.0, 2015: 104157000.0, 2016: 130644000.0,
    2017: 218511000.0, 2018: 225049000.0, 2019: 192791000.0, 2020: 162372000.0,
    2021: 385642000.0, 2022: 500826000.0, 2023: 360862000.0, 2024: 158780000.0,
    2025: 37528000.0,  # 2025: 비현금 영업권손상 $301.2M 반영(반도체 사업부) - GAAP 그대로
}
OPERATING_CASHFLOW = {
    2009: 29611000.0, 2010: 104069000.0, 2011: 120750000.0, 2012: 116170000.0,
    2013: 117367000.0, 2014: 153141000.0, 2015: 165826000.0, 2016: 180133000.0,
    2017: 269170000.0, 2018: 331828000.0, 2019: 245328000.0, 2020: 258031000.0,
    2021: 373344000.0, 2022: 419718000.0, 2023: 457387000.0, 2024: 367621000.0,
    2025: 433764000.0,
}
CAPEX = {
    2009: 15536000.0, 2010: 22433000.0, 2011: 17555000.0, 2012: 22529000.0,
    2013: 34953000.0, 2014: 32281000.0, 2015: 44019000.0, 2016: 46228000.0,
    2017: 65925000.0, 2018: 74753000.0, 2019: 61895000.0, 2020: 56191000.0,
    2021: 90562000.0, 2022: 104341000.0, 2023: 86188000.0, 2024: 75877000.0,
    2025: 67637000.0,
}
SBC = {
    2009: None, 2010: 5200000.0, 2011: 5800000.0, 2012: 7300000.0, 2013: 8900000.0,
    2014: 9400000.0, 2015: 10700000.0, 2016: 12800000.0, 2017: 17300000.0,
    2018: 28200000.0, 2019: 19900000.0, 2020: 19100000.0, 2021: 21400000.0,
    2022: 24600000.0, 2023: 25700000.0, 2024: 27400000.0, 2025: 28600000.0,
}
SBC = {y: v for y, v in SBC.items() if v is not None}

# 대차대조표 - SEC 10-Q(2026-06-27) + WebSearch 재확인(2026-09-09):
# 총부채 $629.66M, 현금 $628.22M -> 순부채 거의 0(net_debt ≈ +$1.4M).
TOTAL_DEBT = 629.660 * M
CASH = 628.224 * M
NET_DEBT = TOTAL_DEBT - CASH
DA_2025 = 74.871 * M + 59.793 * M  # Depreciation + AmortizationOfIntangibleAssets(FY2025)
EBITDA = OPERATING_INCOME[2025] + DA_2025  # 손상차손이 이미 반영된 GAAP 영업이익 기준(정규화 안 함)

PRICE = 422.95  # Alpha Vantage GLOBAL_QUOTE 종가(2026-09-08)
SHARES_OUT = 25_398_747  # SEC 10-Q(2026-06-27) 표지, 2026-07-24 기준
MARKET_CAP = PRICE * SHARES_OUT
RF = 0.0478  # Alpha Vantage TREASURY_YIELD 10Y(2026-09-04)


def build_inputs() -> AnalysisInputs:
    try:
        pit = pit_inputs_for(TICKER, TODAY, list(REVENUE), user_agent=UA)
    except Exception:  # noqa: BLE001 - PIT는 부가 기록, 실패해도 분석은 계속
        pit = {}
    try:
        from engine.data.providers.sec import fetch_company_facts, ticker_to_cik

        facts = fetch_company_facts(ticker_to_cik(TICKER, UA), UA)
        provenance = provenance_from_sec_facts(facts, TICKER, TODAY, list(REVENUE))
    except Exception:  # noqa: BLE001 - provenance는 부가 기록, 실패해도 분석은 계속
        provenance = None

    return AnalysisInputs(
        ticker=TICKER,
        company_name=COMPANY,
        revenue_by_year=REVENUE,
        operating_income_by_year=OPERATING_INCOME,
        operating_cashflow_by_year=OPERATING_CASHFLOW,
        capex_by_year=CAPEX,
        market_cap=MARKET_CAP,
        net_debt=NET_DEBT,
        ebitda=EBITDA,
        risk_free_rate=RF,
        competitor_threat_weights=[0.20, 0.15, 0.10],
        market_share_trend_pp_per_year=0.0,
        active_antitrust_or_regulatory_case=False,
        demand_sensitivity_pct=0.45,
        subjective_input_basis=(
            "competitor_threat_weights: 전력관리·회로보호 반도체·수동소자 부품업 - "
            "Eaton·Sensata·TE Connectivity·Bel Fuse 등과 경쟁하나 특정 1개사가 "
            "구조적 우위를 갖는 시장이 아니라(파편화된 산업재 부품 공급망) 낮은 "
            "가중치로 채택. market_share_trend=0.0 - 이번 FY2025 손상차손은 "
            "'경쟁열위로 인한 점유율 상실'이 아니라 반도체 사업부 자체의 최종수요 "
            "약세(원 서사 확인: '지속되는 연약한 시장환경')라는 업황 문제로 판단, "
            "0으로 중립화. demand_sensitivity=0.45 - CLAUDE.md 앵커표 "
            "'자본재/데이터센터 인프라(설비투자 사이클)' VRT(0.45)에 준하는 "
            "산업재·전장·데이터센터 전력관리 부품업 - 실제로 3y/5y CAGR이 "
            "반도체 공급망 사이클(2020 저점->2022 정점->2024 재저점)을 그대로 "
            "따라가는 것으로 확인돼 경기민감도가 매우 높다."
        ),
        model_used="single_stage",
        model_choice_reason=(
            "structural_discount_rate(cyclical 분류, 16.18% - revenue_volatility·"
            "margin_volatility·cyclicality 전부 상위권)를 거친 뒤의 Realistic "
            "Growth(3.71%)가 g_terminal(3.78%)과 사실상 동일하다(오히려 근소하게"
            "낮음) - 원시 3y/5y/10y CAGR 창이 반도체 사이클(2020 저점->2022 "
            "정점->2024 재저점)로 크게 갈려도(-1.72%/10.54%/10.64%), 구조적할인이 "
            "이미 그 변동성을 흡수해 회사를 '터미널 성장에 근접한 성숙 사이클주'로 "
            "만들었다는 뜻이다. 이 조건(RG≈g_terminal)은 무기한 고정성장을 "
            "가정하는 Gordon 모형(single_stage)이 정확히 성립하는 경우라 "
            "2단계 정상화 경로(two_stage)를 쓸 근거가 없다 - 2단계 모형은 RG가 "
            "터미널보다 뚜렷이 높을 때(예: REGN 7.57% vs g_terminal 3.5%대) "
            "쓰는 것이지, 이미 터미널 수준인 종목에 적용하면 인위적으로 "
            "고성장 경로를 만들어 시가총액을 부당하게 정당화하게 된다. 첫 "
            "정식분석이라 대조할 과거 기록 없음."
        ),
        cagr_base_year_override=None,
        cagr_base_year_override_reason=None,
        capex_classification=None,
        capex_classification_basis=None,
        falsification_conditions=(
            "(1) FY2026 실적(2027년 2월경 예상)에서 반도체 사업부 매출이 추가로 "
            "감소하고 두 번째 손상차손이 인식되면 '업황 문제'라는 이번 판단을 "
            "재검토하고 competition_intensity를 상향한다. "
            "(2) 반도체 사업부 외 전장(Automotive)·산업(Industrial) 세그먼트 "
            "매출성장이 -5%YoY 이하로 둔화하면 회사 전체가 단순 사이클 조정이 "
            "아니라 구조적 침체 국면일 가능성을 재확인한다. "
            "(3) 순부채 추정치(약 $140만, 최근 분기 대차대조표 스냅샷)가 다음 "
            "분기 대비 크게 늘어나면(예: 대규모 M&A로 차입 확대) leverage_score "
            "영향을 재확인할 것."
        ),
        price_at_analysis=PRICE,
        currency="USD",
        sbc_by_year=SBC,
        data_sources=[
            "SEC XBRL companyfacts, 2026-09-09 조회 - 매출·영업이익·영업현금흐름·"
            "capex·SBC 전부 1차자료(FY2009~2025, 17개년). 52/53주 회계연도 라벨을 "
            "원자료(start,end) 중간일자 기준으로 재구성(CDNS/GEN 선례와 동일 절차).",
            "SEC XBRL Depreciation + AmortizationOfIntangibleAssets, FY2025 합산 "
            "$134.664M(2026-02-19 제출)",
            "Alpha Vantage GLOBAL_QUOTE 종가 $422.95(2026-09-08), "
            "TREASURY_YIELD 10Y 4.78%(2026-09-04)",
            "SEC 10-Q(2026-06-27 기준, 2026-08 제출) 표지 "
            "dei:EntityCommonStockSharesOutstanding 25,398,747주(2026-07-24 기준)",
            "WebSearch: SEC 10-Q(2026-06-27 기준) 대차대조표 - 총부채 $629.66M, "
            "현금 $628.224M, 2026-09-09 조회",
            "WebSearch: FY2025 실적발표(영업이익 -76.4%YoY, 비현금 영업권손상 "
            "$301.2M 반도체 사업부 대상), FY2021/FY2024 실적발표(라벨 재구성 "
            "교차검증용), 2026-09-09 조회",
        ],
        **pit,
        provenance=provenance,
    )


if __name__ == "__main__":
    result = run_analysis(build_inputs())

    g = result["growth"]
    ig = result["implied_growth"]
    drs = result["drs"]
    print(f"매출 CAGR   3y {g['breakdown']['revenue_cagr_inputs']['3y']:.2%} / "
          f"5y {g['breakdown']['revenue_cagr_inputs']['5y']:.2%} / "
          f"10y {g['breakdown']['revenue_cagr_inputs']['10y']:.2%}")
    print(f"FCF0 ${result['derived']['fcf0']/1e9:.3f}B "
          f"(FCF수익률 {result['derived']['fcf0']/MARKET_CAP:.2%})")
    print(f"순부채/EBITDA {NET_DEBT/EBITDA:.3f}배   시총 ${MARKET_CAP/1e9:.2f}B")
    print(f"DRS         {drs['score']:.2f}  {drs['components']}")
    print(f"Lynch       {g['breakdown']['lynch_type']}   "
          f"구조적할인 {g['structural_discount_pct']:.2%}")
    print(f"Realistic   {g['realistic_growth']:.2%}")
    print(f"Implied     single {ig['models']['single_stage']:.4f} / "
          f"two {ig['models']['two_stage']:.4f} -> {ig['value']:.4f} ({ig['model_used']})")
    print(f"Gap         {result['expectation_gap']:+.2%}p   "
          f"RAR {result['rar']:+.4f}   Confidence {result['confidence']['final']}/100")
    print(f"** {result['judgment']} / {result['judgment_grade']}등급 **")
    print(f"강건성 flip {result['sensitivity_check']['judgment_with_drs'] != result['sensitivity_check']['judgment_without_drs']}   "
          f"PIT {result['meta'].get('point_in_time', {}).get('status', 'N/A')}")
    if result.get("sbc_cross_check"):
        cc = result["sbc_cross_check"]
        print(f"SBC/FCF {cc['sbc_to_fcf_pct']:.1%} -> Gap {cc['gap_sbc_adjusted']:+.2%}p"
              f" (판정: {cc['judgment_sbc_adjusted']}, flip={cc.get('judgment_flipped')})")
    if result.get("data_limitations"):
        print("data_limitations:")
        for d in result["data_limitations"]:
            print(" -", d)

    save_ledger(result)
