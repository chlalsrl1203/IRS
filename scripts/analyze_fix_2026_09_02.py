"""
Comfort Systems USA, Inc.(FIX) 정식 분석 - 2026-09-02.

경위: 연구 우선순위 큐(스크리너 tier B, Gap 추정 +18.51%p, 시총 근사
~$18.64B). LNTH/EQT/CDE를 FRAMEWORK_MISMATCH로 제외한 뒤 큐 순서상
다음 순위.

## 원자료 - SEC XBRL companyfacts(1차자료, `SecCompanyFactsProvider`,
2026-09-02 조회, CIK 0001035983, 2009~2025 17개년 확보 - 10y CAGR 산출
가능).

## ⭐ 핵심 발견 - 스크리너 시총 근사치가 AI 데이터센터 붐발 +1,240%(3년)
랠리를 거의 놓쳤다

FIX는 상업용/산업용 건설의 기계·전기·배관(MEP) 시공업체로, 2022년 이후
데이터센터·첨단기술 고객向 수요가 폭발적으로 늘며 매출성장률이 가속됐다
(YoY: 2022 +34.7%, 2023 +25.8%, 2024 +35.0%, 2025 +29.5% - 2021년 이전
한자릿수~10%대와 뚜렷이 구분됨, 단일연도 단계상승이 아니라 다년 가속
패턴이라 M&A 단계상승과는 다른 유형). 2026-05 Motley Fool 기사가 이 종목을
"3년간 시장을 조용히 압도한 HVAC 종목"으로, WebSearch(2026-09-02)로 확인한
2026-08 자료는 **주가가 최근 3년간 +1,240%, 2026년 YTD만 +116%** 급등했다고
보도한다. 스크리너의 시총 근사(~$18.64B)는 실시간 시총(~$54.67B)의 1/3
수준에 불과하다.

Q1 2026 실적(매출 $2.87B, +56%YoY, 컨센서스 대비 +20%, EPS $10.51로 전년
$4.75의 2배 이상)·백로그 $12.5B(2026년 예상 연매출 ~$12B와 맞먹는 수준) 등
전부 실질적 실적 개선이라 M&A/일회성 아티팩트가 아니다 - CFO가 2026년
동일점포(same-store) 매출성장을 "20%대 중후반"으로 직접 가이던스했다(회사
자체 가이던스가 오히려 trailing CAGR과 근접 - KEYS/KLAC와 반대로 여기선
가이던스가 성장둔화 신호가 아님).

## ⚠️ 발견 2 - 밸류에이션이 이미 상당히 낙관을 반영했다는 외부 경고

Seeking Alpha(2026-09)가 "밸류에이션과 기술적 지표가 이미 팽팽하다(stretched)"
고 평가하고, 별도 기사는 "2026년 EPS 기준 43배로 업종 중앙값의 2배 이상"이며
"데이터센터 지출이 2020년대 이후 이동하면 미래성장이 둔화될 수 있어 현재
밸류에이션이 이미 낙관적 장기가정을 반영했을 가능성"을 지적한다. AMD/AMAT/
ACN이 이미 문서화한 "펀더멘털은 훌륭한데 이미 비쌈"(4분류 2번) 패턴과 정확히
같은 계열 - 정식분석으로 확인이 필요했다.

## 경쟁구도(2026-09-02 WebSearch) - MEP(기계·전기·배관) 시공 업종

EMCOR Group(더 크고 다각화된 MEP/시설관리 업체) > MYR Group/Quanta Services
(전력 인프라 인접 세그먼트). 데이터센터 붐은 업종 전반의 공유된 순풍이라
FIX만의 고유 해자라기보다 업종 전체가 수혜 중 - FIX가 기록적 백로그로
peer 대비 다소 우위를 보이나 압도적 차별화는 아니다.

## 실행: python3 scripts/analyze_fix_2026_09_02.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.filing_dates import pit_inputs_for
from engine.pipeline import AnalysisInputs, run_analysis, save_ledger
from engine.provenance import provenance_from_sec_facts

TICKER = "FIX"
UA = "IRS Research chlalsrl1203@gmail.com"
TODAY = "2026-09-02"

# ── SEC XBRL companyfacts 실측(2026-09-02 조회) ──────────────────────────
REVENUE = {
    2009: 1128907000.0, 2010: 1108282000.0, 2011: 1240020000.0,
    2012: 1331185000.0, 2013: 1357272000.0, 2014: 1410795000.0,
    2015: 1580519000.0, 2016: 1634340000.0, 2017: 1787922000.0,
    2018: 2182879000.0, 2019: 2615277000.0, 2020: 2856659000.0,
    2021: 3073636000.0, 2022: 4140364000.0, 2023: 5206760000.0,
    2024: 7027476000.0, 2025: 9101641000.0,
}
OPERATING_INCOME = {
    2009: 56633000.0, 2010: 20042000.0, 2011: -49368000.0,
    2012: 22303000.0, 2013: 46258000.0, 2014: 42222000.0,
    2015: 90044000.0, 2016: 101569000.0, 2017: 99260000.0,
    2018: 150238000.0, 2019: 163639000.0, 2020: 190651000.0,
    2021: 188438000.0, 2022: 253849000.0, 2023: 418388000.0,
    2024: 749369000.0, 2025: 1314589000.0,
}
OPERATING_CASHFLOW = {
    2009: 54251000.0, 2010: 32149000.0, 2011: 29680000.0,
    2012: 30510000.0, 2013: 38423000.0, 2014: 42552000.0,
    2015: 97867000.0, 2016: 91188000.0, 2017: 114090000.0,
    2018: 147190000.0, 2019: 142028000.0, 2020: 286510000.0,
    2021: 180151000.0, 2022: 301531000.0, 2023: 639568000.0,
    2024: 849057000.0, 2025: 1186356000.0,
}
CAPEX = {
    2009: 9457000.0, 2010: 7089000.0, 2011: 8666000.0,
    2012: 11782000.0, 2013: 17403000.0, 2014: 19183000.0,
    2015: 20808000.0, 2016: 23217000.0, 2017: 35467000.0,
    2018: 27268000.0, 2019: 31750000.0, 2020: 24131000.0,
    2021: 22330000.0, 2022: 48359000.0, 2023: 94838000.0,
    2024: 111071000.0, 2025: 154903000.0,
}
NET_INCOME = {
    2009: 34182000.0, 2010: 14740000.0, 2011: -36492000.0,
    2012: 11849000.0, 2013: 27269000.0, 2014: 23063000.0,
    2015: 49364000.0, 2016: 64896000.0, 2017: 55272000.0,
    2018: 112903000.0, 2019: 114324000.0, 2020: 150139000.0,
    2021: 143348000.0, 2022: 245947000.0, 2023: 323398000.0,
    2024: 522433000.0, 2025: 1022558000.0,
}
SBC = {
    2009: 3454000.0, 2010: 3687000.0, 2011: 3604000.0,
    2012: 2797000.0, 2013: 3974000.0, 2014: 4806000.0,
    2015: 5609000.0, 2016: 5041000.0, 2017: 6377000.0,
    2018: 7161000.0, 2019: 5878000.0, 2020: 6934000.0,
    2021: 10593000.0, 2022: 10532000.0, 2023: 12939000.0,
    2024: 16646000.0, 2025: 21809000.0,
}

# ── 대차대조표(FY2025말, 2025-12-31, SEC XBRL 실측) ──────────────────────
CASH_2025 = 981898000.0            # CashAndCashEquivalentsAtCarryingValue
TOTAL_DEBT_2025 = 145226000.0      # LongTermDebt(총액, 유동+비유동)
NET_DEBT = TOTAL_DEBT_2025 - CASH_2025  # -836,672,000(순현금)

DA_2025 = 62379000.0 + 79580000.0  # Depreciation + AmortizationOfIntangibleAssets
EBITDA = OPERATING_INCOME[2025] + DA_2025

# ── 시가총액(2026-09-02, Alpha Vantage 종가 + 10-K 표지 발행주식수) ──────
PRICE = 1554.37  # Alpha Vantage GLOBAL_QUOTE, 2026-09-01 종가(latestDay)
SHARES_OUT = 35174967.0  # FY2025 10-K 표지 dei:EntityCommonStockSharesOutstanding(2026-02-13)
MARKET_CAP = PRICE * SHARES_OUT  # 약 $54.67B

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
        company_name="Comfort Systems USA, Inc.",
        revenue_by_year=REVENUE,
        operating_income_by_year=OPERATING_INCOME,
        operating_cashflow_by_year=OPERATING_CASHFLOW,
        capex_by_year=CAPEX,
        market_cap=MARKET_CAP,
        net_debt=NET_DEBT,
        ebitda=EBITDA,
        risk_free_rate=RF,
        usd_fx_rate=1.0,
        competitor_threat_weights=[0.25, 0.10],
        market_share_trend_pp_per_year=0.5,
        active_antitrust_or_regulatory_case=False,
        demand_sensitivity_pct=0.45,
        subjective_input_basis=(
            "competitor_threat_weights=[0.25(EMCOR Group), 0.10(MYR Group/Quanta "
            "Services)] - EMCOR이 더 크고 다각화된 MEP/시설관리 업체로 최대 "
            "위협, MYR/Quanta는 전력인프라 인접세그먼트라 낮게 반영. "
            "market_share_trend_pp_per_year=+0.5 - 데이터센터 붐은 업종 전반의 "
            "공유된 순풍(FIX 고유 해자 아님)이나 백로그 $12.5B(2026년 예상 연매출과 "
            "맞먹음)로 peer 대비 다소 우위를 보여 완만한 양(+)값만 반영. "
            "demand_sensitivity_pct=0.45 - CLAUDE.md 업종앵커표 '자본재/"
            "데이터센터 인프라(설비투자 사이클)' 버킷(VRT, 앵커 0.45)과 동일 "
            "테마·동일 앵커 적용 - 하이퍼스케일러 capex 사이클에 직접 노출돼 "
            "경기민감도가 높음(2026-09-02 WebSearch, '데이터센터 지출이 2020년대 "
            "이후 이동하면 성장 둔화 가능'이라는 외부 경고와 일치)."
        ),
        model_used="two_stage",
        model_choice_reason=(
            "trailing 매출 CAGR(3y 30.03%/5y 26.08%/10y 19.13%)이 "
            "default_terminal_growth(2.0~4.5%)보다 극도로 높고, 외부 애널리스트도 "
            "'데이터센터 지출 사이클 이동 시 성장 둔화 가능'을 명시적으로 경고해 "
            "다년 수렴 경로(two_stage)가 필요하다고 판단. Lynch fast_grower "
            "상한(25%) 또는 v3.67 규모조건부 상한(시총 $54.67B, base_rates 최상위 "
            "구간)이 바인딩될 가능성이 높아 원시 CAGR을 그대로 신뢰하지 않는다."
        ),
        falsification_conditions=(
            "다음 분기(Q3 2026) 동일점포 매출성장률이 가이던스 하단(20%대 중반)을 "
            "밑돌거나, 백로그 증가세가 정체·역전되거나, 하이퍼스케일러(Microsoft/"
            "Google/Amazon/Meta 등) 데이터센터 capex 가이던스가 하향되면 이 "
            "판정을 재검토할 것 - 밸류에이션이 이미 다년 낙관을 선반영했다는 "
            "외부 지적(43x 2026 EPS, 업종중앙값 2배 이상)이 실현될 신호다."
        ),
        price_at_analysis=PRICE,
        currency="USD",
        net_income_by_year=NET_INCOME,
        sbc_by_year=SBC,
        data_sources=[
            "SEC XBRL companyfacts (CIK 0001035983, 조회 2026-09-02)",
            "Alpha Vantage GLOBAL_QUOTE (2026-09-01 종가 $1,554.37)",
            "WebSearch: FIX Q1 2026 실적발표·데이터센터 수요 서사·밸류에이션 경고"
            "(Motley Fool/Seeking Alpha/TIKR/Yahoo Finance, 2026-09-02 재인용)",
        ],
        **pit,
        provenance=provenance,
    )


if __name__ == "__main__":
    inputs = build_inputs()
    result = run_analysis(inputs)
    path = save_ledger(result)
    print(f"saved: {path}")
