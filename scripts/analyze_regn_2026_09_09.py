"""
REGN(Regeneron Pharmaceuticals) 정식분석 - 연구 우선순위 큐 신규 후보.

핵심 확인사항 - 2021 COVID 항체(REGEN-COV) 일회성 매출 급증이 고정 CAGR
창에 실제로 걸리는지 사전점검(CROX/CHDN/QSR 선례와 동일 절차):
  - 3y 시작연도(years[-4]) = 2022, 5y 시작연도(years[-6]) = 2020,
    10y 시작연도(years[-11]) = 2015. 2021(피크연도) 자체가 어느 창의
    시작/종료연도에도 해당하지 않는다 - CAGR은 시작·종료값에만 의존하므로
    중간에 낀 일회성 스파이크는 직접 왜곡을 만들지 않는다(GEN/BRO/ROP형
    M&A 단계상승과 다른 성격 - 그건 창 경계 자체가 단계상승 지점).
  - 매출 CAGR 3y/5y/10y = 5.62%/11.04%/13.33% - 서로 완만히 벌어지나
    극단적 발산은 아님(override 불필요).
  - FCF CAGR 3y/5y/10y = -2.66%/15.29%/20.11% - 3y가 음수인 이유는 2022년
    (COVID 항체 매출 정산으로 운전자본이 부풀려진 시점)이 시작값이라
    상대적으로 높은 기저를 만들었기 때문. `realistic_growth_estimate()`의
    min(FCF가중, 매출가중) 로직이 FCF가중(7.28%) < 매출가중(8.79%)이라
    FCF가중을 그대로 채택 - 별도 개입 불필요, 설계대로 작동.
  - capex/매출 5년평균(5.26%) vs 2025(6.26%): delta +1.00%p < 3%p 임계값 -
    v3.20 capex 재검토 트리거 미발동.
"""
from engine.filing_dates import pit_inputs_for
from engine.pipeline import AnalysisInputs, run_analysis, save_ledger
from engine.provenance import provenance_from_sec_facts

TICKER = "REGN"
COMPANY = "Regeneron Pharmaceuticals, Inc."
TODAY = "2026-09-09"
UA = "IRS Research chlalsrl1203@gmail.com"
M = 1_000_000

REVENUE = {
    2015: 4103728000.0, 2016: 4860400000.0, 2017: 5872200000.0, 2018: 6710800000.0,
    2019: 7863400000.0, 2020: 8497100000.0, 2021: 16071700000.0, 2022: 12172900000.0,
    2023: 13117200000.0, 2024: 14202000000.0, 2025: 14342900000.0,
}
OPERATING_INCOME = {
    2015: 1251916000.0, 2016: 1330741000.0, 2017: 2079591000.0, 2018: 2534400000.0,
    2019: 2209800000.0, 2020: 3576600000.0, 2021: 8946800000.0, 2022: 4738900000.0,
    2023: 4047100000.0, 2024: 3990700000.0, 2025: 3577900000.0,
}
OPERATING_CASHFLOW = {
    2015: 1330780000.0, 2016: 1473396000.0, 2017: 1307112000.0, 2018: 2195100000.0,
    2019: 2430000000.0, 2020: 2618100000.0, 2021: 7081300000.0, 2022: 5014900000.0,
    2023: 4594000000.0, 2024: 4420500000.0, 2025: 4978900000.0,
}
CAPEX = {
    2015: 677933000.0, 2016: 511941000.0, 2017: 272626000.0, 2018: 383100000.0,
    2019: 429600000.0, 2020: 614600000.0, 2021: 551900000.0, 2022: 590100000.0,
    2023: 718600000.0, 2024: 755900000.0, 2025: 898400000.0,
}
SBC = {
    2015: 459049000.0, 2016: 559878000.0, 2017: 507277000.0, 2018: 427400000.0,
    2019: 464300000.0, 2020: 432000000.0, 2021: 601700000.0, 2022: 725000000.0,
    2023: 885000000.0, 2024: 982800000.0, 2025: 993700000.0,
}

# 대차대조표 - SEC 10-Q(2026-06-30) 표지·본문(WebSearch 확인) + D&A는 SEC XBRL
# DepreciationDepletionAndAmortization FY2025 직접조회
LONG_TERM_DEBT = 1986.2 * M
CASH_AND_SECURITIES = 18539.6 * M  # 현금 + 유동/비유동 시장성증권 합계(2026-03-31 기준)
NET_DEBT = LONG_TERM_DEBT - CASH_AND_SECURITIES  # 순현금(대규모)
DA_2025 = 543.7 * M
EBITDA = OPERATING_INCOME[2025] + DA_2025

PRICE = 810.31  # Alpha Vantage GLOBAL_QUOTE 종가(2026-09-08)
SHARES_OUT = 101_137_842  # SEC 10-Q(2026-06-30) 표지, 2026-07-23 기준
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
        competitor_threat_weights=[0.30, 0.20, 0.15],
        market_share_trend_pp_per_year=-0.3,
        active_antitrust_or_regulatory_case=False,
        demand_sensitivity_pct=0.12,
        subjective_input_basis=(
            "competitor_threat_weights: Eylea(legacy) 매출이 최근분기 -45%YoY로 "
            "실측 침식 중(바이오시밀러 다수 화해·승인으로 유럽·APAC·美 후반부 "
            "출시경로 확보) - ZTS Elanco형 실측 침식과 유사한 1순위 위협. "
            "다만 Eylea HD(연장투여간격 라벨 강화)가 legacy 대체 진행 중이고 "
            "Dupixent가 +32~38%YoY로 회사 성장을 이미 견인하는 분산효과가 "
            "뚜렷해 - CLAUDE.md 헬스케어 앵커표(IDXX·ZTS·MNST·RMD, 0.10~0.15)에서 "
            "중간값 채택. market_share_trend는 legacy Eylea 프랜차이즈 단독 "
            "기준 소폭 음수(-0.3%p/yr)로 잡되 Dupixent 성장이 전사 실적에서 "
            "이를 상쇄하는 점을 falsification_conditions에 별도 명시. "
            "active_antitrust_or_regulatory_case=False - 바이오시밀러 특허소송은 "
            "지식재산권 분쟁이지 반독점·규제경쟁 사건이 아니다(HQY 데이터브리치 "
            "소송을 이 필드에서 제외한 것과 동일한 범위 판단)."
        ),
        model_used="two_stage",
        model_choice_reason=(
            "매출 CAGR 3y/5y/10y(5.62%/11.04%/13.33%)가 완만히 감속하는 다년 "
            "궤적이고, min(FCF가중 7.28%, 매출가중 8.79%) 로직으로 채택된 "
            "base_growth(7.28%)가 default_terminal_growth(3.5%대)보다 뚜렷이 "
            "높다 - Eylea 바이오시밀러 침식이 legacy 프랜차이즈를 정상화 "
            "경로로 이끄는 중이라(위 subjective_input_basis) 무기한 고정성장을 "
            "가정하는 single_stage보다 성장이 터미널로 수렴하는 경로를 명시하는 "
            "two_stage가 이 회사의 실제 궤적에 더 부합한다. 첫 정식분석이라 "
            "대조할 과거 기록 없음."
        ),
        cagr_base_year_override=None,
        cagr_base_year_override_reason=None,
        capex_classification=None,
        capex_classification_basis=None,
        falsification_conditions=(
            "(1) FY2026 4분기 실적(2027년 2월경 예상)에서 legacy Eylea 매출 "
            "감소율이 -45%YoY보다 더 가팔라지고 Eylea HD 성장이 이를 상쇄하지 "
            "못하면 이 분석이 채택한 market_share_trend=-0.3%p·demand_sensitivity "
            "=0.12 가정을 재검토한다. "
            "(2) Dupixent 성장률이 +32%YoY(최근 분기) 대비 절반 이하로 둔화하면 "
            "회사 전체 성장서사(Eylea 침식을 Dupixent가 상쇄)의 핵심축이 약화된다. "
            "(3) 아플리버셉트(Eylea) 바이오시밀러의 미국 시장 실제 출시가 확정되면 "
            "(현재는 유럽·APAC 우선, 美 후반부 예상) 침식 속도 가정을 즉시 재확인. "
            "(4) 순현금 추정치(NET_DEBT 약 -$165.5억, 최근 분기 대차대조표 "
            "스냅샷)가 다음 분기 대비 크게 달라지면(예: 대규모 M&A로 순현금 소진) "
            "leverage_score 영향을 재확인할 것."
        ),
        price_at_analysis=PRICE,
        currency="USD",
        sbc_by_year=SBC,
        data_sources=[
            "SEC XBRL companyfacts, 2026-09-09 조회 - 매출·영업이익·영업현금흐름·"
            "capex·SBC 전부 1차자료(FY2015~2025, 11개년)",
            "SEC XBRL DepreciationDepletionAndAmortization, FY2025 $543.7M(2026-02-04 제출)",
            "Alpha Vantage GLOBAL_QUOTE 종가 $810.31(2026-09-08), "
            "TREASURY_YIELD 10Y 4.78%(2026-09-04)",
            "SEC 10-Q(2026-06-30 기준, 2026-07-30 제출) 표지 "
            "dei:EntityCommonStockSharesOutstanding 101,137,842주(2026-07-23 기준)",
            "WebSearch: SEC 10-Q(2026-03-31 기준) 대차대조표 - 장기부채 $1,986.2M, "
            "현금+시장성증권 합계 $18,539.6M, 2026-09-09 조회",
            "WebSearch: Eylea/Dupixent 2026 실적발표·컨퍼런스 자료(legacy Eylea "
            "-45%YoY, Dupixent +32~38%YoY, 바이오시밀러 경쟁구도), 2026-09-09 조회",
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
