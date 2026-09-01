"""
Crocs, Inc.(CROX) 정식 분석 - 2026-09-01.

경위: `scripts/broad_screen.py` 주간 대규모 스크리닝(2026-08-30)에서 259개
통과 법인 중 검증범위 안 최우선 순위(연구 우선순위 큐 1위, Gap 추정
+23.97%p)로 올라온 종목. 스크리너 추정치는 6개년 근사·corpus 중앙값
대체값을 쓰므로 `run_analysis()`로 정식 확정한다.

## 원자료 - SEC XBRL companyfacts(1차자료, engine/data/providers/sec.py
`SecCompanyFactsProvider`, 2026-09-01 조회, CIK 0001334036, 2009~2025
17개년 확보 - 10y CAGR 산출 가능). `[태그 혼재]` 경고 3건(revenue·
operating_cashflow·shareholders_equity, ASC 606/보고서식 변경 구간) -
프로바이더가 값 단위로 출처를 기록하므로 CAGR 경계연도(2015/2020)는
전부 문제없는 태그로 확인됨.

## ⭐ 핵심 발견 - 스크리너 Gap +23.97%p는 M&A 단계상승 아티팩트다
(GEN/BRO/ROP/SNPS/NRG/RBA/NOW/AVGO와 동일 패턴)

HEYDUDE 인수(2022-02-17 종결)가 5y CAGR 구간(2020->2025) 한가운데 걸린다.
매출 5y CAGR **23.86%**(스크리너가 그대로 인용한 값과 정확히 일치)는 두
개의 서로 다른 사건이 겹친 결과다: (1) 2020->2021 +67.0%(코로나 이후
Crocs 브랜드 DTC 회복 - 유기적), (2) 2021->2022 +53.6%(HEYDUDE 10.5개월
연결 - M&A). 인수 종결 **이후**로만 깨끗한 3y CAGR(2022->2025)은 매출
**4.36%**·FCF **9.73%**로 5y 수치의 1/5~1/2에 불과하다 - 10y CAGR(13.99%)도
같은 이유로 부풀려져 있다.

`realistic_growth_estimate()`의 3y/5y/10y 가중평균(0.5/0.3/0.2)이 3y에
과반 가중치를 줘 이 왜곡을 상당 부분 자동 흡수하므로 별도
`cagr_base_year_override`는 쓰지 않는다(적용하면 3y 단독으로 강제되는데,
그 근거인 세그먼트 완전분리 데이터를 확보하지 못했다 - 아래 참고). 다만
정식 Realistic Growth가 스크리너의 24%대와 크게 다를 것으로 예상하고
기록해둔다.

## ⭐ 발견 2 - FY2025 영업이익 붕괴는 비현금 손상차손(HEYDUDE)이다

WebSearch(2026-09-01, Yahoo Finance/PRNewswire 2025 Q4 실적발표 재인용)로
확인: FY2025 영업이익 $149.5M(FY2024 $1,021.9M 대비 -85.4%, 영업이익률
24.9%->3.7%)은 HEYDUDE 상표권 손상 $430M + HEYDUDE 브랜드 영업권 손상
$307M(합계 $738.1M, 전부 비현금)이 원인 - 회사 자체가 손상차손 primary
driver라고 명시했다. **영업현금흐름은 오히려 견조**(FY2025 $710.4M, FY2024
$992.5M 대비 -28.4%로 완만한 감소, 손상차손 자체는 현금유출이 아니므로).

**engine에 별도 "손상차손 조정" 입력 필드가 없어 원자료(GAAP) 그대로
쓴다** - margin_volatility_score는 이 손상으로 인한 실제 P&L 변동성을
그대로 반영하고(비현금이라 해서 시장이 이 리스크를 무시하지는 않는다),
net_debt/EBITDA도 GAAP EBITDA(영업이익+D&A, 손상차손 add-back 없음)를
그대로 쓴다 - is_insurer/sbc_cross_check와 동일한 "임의 정규화 안 함"
원칙. 레버리지가 이 해에 한해 과대평가될 수 있다는 점만 아래 명시적으로
기록한다(v3.46 P0-①의 EBITDA<=0 가드는 해당 없음 - 여전히 양수).

## 경쟁구도(2026-09-01 WebSearch, CROX/DECK/SKX 각사 최신 실적발표 기준)

Q2 2026(2026-08-07 발표): Crocs 연결매출 $1.18B(+2.6%YoY) - Crocs 브랜드
분기 최초 $1B+ 돌파(+4.3%), **HEYDUDE 브랜드 -5.7%**(도매 -17.2% vs
D2C +7.2% - 도매 채널에서 실제 점유율 침식, D2C는 안정화 신호). 같은
분기 Skechers 매출 $2.44B(+13.1%YoY) - CROX보다 5배 규모로 훨씬 빠르게
성장 중인 직접경쟁자. Deckers(HOKA/UGG) 매출 $1.02B(+5.7%YoY) - 프리미엄
러닝/컴포트화로 일부 겹침. **CROX는 규모가 작은 두 경쟁자보다 느리게
성장하는 열세 국면**이라 판단.

## 실행: python3 scripts/analyze_crox_2026_09_01.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.filing_dates import pit_inputs_for
from engine.pipeline import AnalysisInputs, run_analysis, save_ledger
from engine.provenance import provenance_from_sec_facts

TICKER = "CROX"
UA = "IRS Research chlalsrl1203@gmail.com"
TODAY = "2026-09-01"

# ── SEC XBRL companyfacts 실측(2026-09-01 조회) ──────────────────────────
REVENUE = {
    2015: 1090630000.0, 2016: 1036273000.0, 2017: 1023513000.0,
    2018: 1088205000.0, 2019: 1230593000.0, 2020: 1385951000.0,
    2021: 2313416000.0, 2022: 3554985000.0, 2023: 3962347000.0,
    2024: 4102108000.0, 2025: 4040647000.0,
}
OPERATING_INCOME = {
    2015: -72324000.0, 2016: -6154000.0, 2017: 17336000.0, 2018: 62944000.0,
    2019: 128649000.0, 2020: 214124000.0, 2021: 683064000.0,
    2022: 850756000.0, 2023: 1036783000.0, 2024: 1021911000.0,
    2025: 149515000.0,
}
OPERATING_CASHFLOW = {
    2015: 9698000.0, 2016: 39754000.0, 2017: 98264000.0, 2018: 114162000.0,
    2019: 89958000.0, 2020: 266902000.0, 2021: 567165000.0,
    2022: 603142000.0, 2023: 930444000.0, 2024: 992486000.0,
    2025: 710431000.0,
}
CAPEX = {
    2015: 12826000.0, 2016: 13233000.0, 2017: 13117000.0, 2018: 11979000.0,
    2019: 36576000.0, 2020: 42033000.0, 2021: 55916000.0, 2022: 104190000.0,
    2023: 115625000.0, 2024: 69347000.0, 2025: 51231000.0,
}
NET_INCOME = {
    2015: -83196000.0, 2016: -16494000.0, 2017: 10238000.0,
    2018: 50437000.0, 2019: 119497000.0, 2020: 312861000.0,
    2021: 725694000.0, 2022: 540159000.0, 2023: 792566000.0,
    2024: 950071000.0, 2025: -81198000.0,
}
SBC = {
    2015: 11236000.0, 2016: 10736000.0, 2017: 9773000.0, 2018: 13105000.0,
    2019: 14412000.0, 2020: 16361000.0, 2021: 38122000.0, 2022: 31303000.0,
    2023: 29072000.0, 2024: 33053000.0, 2025: 36701000.0,
}

# 재무상태표(FY2025, 2025-12-31 기준, SEC XBRL)
CASH_2025 = 130354000.0
LT_DEBT_NONCURRENT_2025 = 1230885000.0
LT_DEBT_CURRENT_2025 = 0.0  # FY2024부터 유동성 장기부채 항목 자체가 미보고(0으로 확인)
TOTAL_DEBT_2025 = LT_DEBT_NONCURRENT_2025 + LT_DEBT_CURRENT_2025
NET_DEBT = TOTAL_DEBT_2025 - CASH_2025

DA_2025 = 79282000.0  # DepreciationDepletionAndAmortization, FY2025 현금흐름표
EBITDA = OPERATING_INCOME[2025] + DA_2025  # 손상차손 add-back 없음(원자료 그대로)

# 시가총액(2026-08-31 종가 $120.38 x 발행주식 47,945,075주, 2026-07-23
# 10-Q 표지 dei:EntityCommonStockSharesOutstanding, Alpha Vantage GLOBAL_QUOTE
# 2026-09-01 조회) - broad_screen이 쓴 EntityPublicFloat($4.8B, 2025-06-30
# 스냅샷 - v3.72 문서화된 한계)보다 최신이라 이쪽을 채택한다.
PRICE = 120.38
SHARES_OUT = 47945075
MARKET_CAP = PRICE * SHARES_OUT

RF = 0.0475  # 미국 10Y, 2026-08-31 종가(WebSearch: tradingeconomics/CNBC 재인용)


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
        company_name="Crocs, Inc.",
        revenue_by_year=REVENUE,
        operating_income_by_year=OPERATING_INCOME,
        operating_cashflow_by_year=OPERATING_CASHFLOW,
        capex_by_year=CAPEX,
        market_cap=MARKET_CAP,
        net_debt=NET_DEBT,
        ebitda=EBITDA,
        risk_free_rate=RF,

        competitor_threat_weights=[0.30, 0.12],
        market_share_trend_pp_per_year=-0.8,
        active_antitrust_or_regulatory_case=False,
        demand_sensitivity_pct=0.35,
        subjective_input_basis=(
            "경쟁강도 - Skechers 0.30(2026 Q2 매출 $2.44B/+13.1%YoY로 CROX"
            "(+2.6%)보다 5배 규모에 5배 빠른 성장 - 캐주얼·컴포트화 직접경쟁, "
            "IRS 트래커 내 가장 공격적인 경쟁자 축에 해당[추정치]). Deckers"
            "(HOKA/UGG) 0.12(2026 Q2 +5.7%YoY, $1.02B - 프리미엄 러닝/컴포트"
            "화로 일부 겹치나 포지셔닝이 CROX 캐주얼과는 다소 달라 Skechers"
            "보다 낮게 설정[추정치]). market_share_trend=-0.8pp: 정확한 "
            "시장점유율 통계는 확보하지 못했고, CROX 연결성장(+2.6%)이 "
            "Skechers(+13.1%)에 뚜렷이 뒤처지는 상대성장 격차와 HEYDUDE "
            "도매채널 -17.2%YoY(D2C는 +7.2%로 안정화 신호와 대비)를 근거로 "
            "완만한 음수를 부여했다[추정치, 정밀 시장점유율 데이터 미확보]. "
            "active_antitrust_or_regulatory_case=False: 2026-09 WebSearch로 "
            "확인한 진행 중인 반독점·경쟁당국 조사 없음. demand_sensitivity"
            "=0.35: 캐주얼/컴포트 신발은 재량소비재이고 HEYDUDE 도매 -17.2%"
            "이 유행/재고사이클 민감성을 실측으로 보여준다 - CLAUDE.md "
            "demand_sensitivity 앵커표에 신발/의류 카테고리가 아직 없어 "
            "가장 가까운 '소비자 구독/플랫폼(재량소비, 대체재 존재)' 앵커"
            "(0.30)보다 소폭 높게 설정했다[추정치, 신규 업종 - 향후 신발/"
            "의류 종목이 더 쌓이면 앵커표에 반영할 것]."
        ),

        model_used="single_stage",
        model_choice_reason=(
            "HEYDUDE 인수(2022-02 종결) 이후로만 깨끗한 3y CAGR(2022->2025)"
            "이 매출 4.36%/FCF 9.73%로 이미 완만한 한자릿수대이고, 직전 1y"
            "(2024->2025)는 매출이 오히려 -1.50%로 역성장했다 - 명시적 "
            "고성장 국면 이후 수렴을 모델링하는 two_stage보다, 이미 정상상태"
            "에 근접했다고 보는 single_stage(Gordon)가 현재 성장궤적에 "
            "이론적으로 더 부합한다고 판단(BRO가 확립한 '이미 성숙한 성장률"
            "에는 Gordon' 판단과 동일 논리, 2026-08-16 모델선택 연구가 "
            "확인한 대로 이론기준이 완벽히 선택을 가르지는 못하나 이 경우는 "
            "방향이 뚜렷함). 첫 정식분석이라 대조할 과거 기록 없음."
        ),

        falsification_conditions=(
            "(1) 2026 Q3/Q4 실적(2026-11월경 예상)에서 HEYDUDE 도매채널 "
            "역성장이 추가로 확대되거나 회사가 HEYDUDE 회복 가이던스를 "
            "재차 하향하면 재검토. (2) Crocs 브랜드 자체 성장률이 3~4%대 "
            "아래로 추가 둔화되면(현재 3y CAGR 4.36%가 이미 이 분석의 "
            "핵심 가정) 재검토. (3) Skechers·Deckers 대비 상대성장 격차가 "
            "더 벌어지면(현재 CROX +2.6% vs Skechers +13.1%) competition_"
            "intensity 상향 재검토 필요."
        ),

        price_at_analysis=PRICE,
        currency="USD",

        net_income_by_year=NET_INCOME,
        sbc_by_year=SBC,

        data_sources=[
            "SEC XBRL companyfacts(CIK 0001334036), 2026-09-01 조회",
            "Alpha Vantage GLOBAL_QUOTE, 2026-09-01 조회(2026-08-31 종가)",
            "WebSearch: Yahoo Finance/PRNewswire 2025 Q4 실적발표 재인용"
            "(HEYDUDE 손상차손 상세), 2026 Q2 실적발표(CROX/DECK/SKX 각사),"
            " tradingeconomics/CNBC(10Y 국채금리) - 전부 2026-09-01 조회",
        ],

        **pit,
        provenance=provenance,
    )


if __name__ == "__main__":
    inputs = build_inputs()
    result = run_analysis(inputs)
    path = save_ledger(result)
    print(f"저장: {path}")
    print(f"판정: {result['judgment']} (등급 {result['judgment_grade']})")
    print(f"Gap: {result['expectation_gap']['gap']*100:+.2f}%p")
    print(f"RAR: {result['rar']:+.4f}")
    print(f"DRS: {result['drs']['score']:.2f}")
    print(f"Realistic Growth: {result['growth']['realistic_growth']*100:.2f}%")
    print(f"Implied Growth: {result['expectation_gap']['implied_growth']*100:.2f}%")
    print(f"Confidence: {result['confidence']['score']}")
    print(f"모델: {result['model_used']}")
    if result.get("data_limitations"):
        print("한계:")
        for lim in result["data_limitations"]:
            print(f"  - {lim}")
