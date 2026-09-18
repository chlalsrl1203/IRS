"""
ServiceNow, Inc.(NOW) 최초 정식 분석 - 2026-09-04. **보유 5순위(6.7%) 종목.**

## ⭐ 이 분석의 첫 번째 결론: 2026-08-14 FRAMEWORK_MISMATCH 제외가 틀렸다

2026-08-14 스크리닝 배치에서 NOW를 이렇게 제외했다:
  > "대차대조표에서 goodwill이 Q1'26 $4.54B -> Q2'26 $9.84B로 한 분기만에
  >  2배 이상 급증... RBA와 동일한 'M&A가 성장구간에 걸치는' 패턴이 단일
  >  인수가 아니라 연쇄 인수라 더 심하게 오염됐을 가능성이 높다...
  >  방금 확인한 '가속하는' 분기 매출 성장이 순수 유기적성장이 아니라
  >  상당부분 인수효과일 수 있다"

**이 추론에는 연도 확인이 빠져 있었다.** 이번에 SEC 연차 원자료를 직접
열어보니:

  - 인수 종결 시점: Moveworks 2025-12, Veza 2026H1, **Armis 2026-04-20**
    (회사 공식 발표로 재확인). goodwill 급증(Q1'26 $4.54B -> Q2'26 $9.84B)은
    **전부 FY2026 사건**이다.
  - 그런데 이 엔진이 쓰는 것은 **연차(10-K) 시계열**이고 최신 연도는
    FY2025다. FY2015~2025 매출 YoY: 38.4% -> 36.0% -> 32.6% -> 30.6% ->
    30.5% -> 22.9% -> 23.8% -> 22.4% -> 20.9% - **단계상승이 단 한 번도
    없는 매끄러운 단조 감속**이다. 교과서적인 유기적 SaaS 성장곡선이며
    GEN/BRO/ROP/RBA/AVGO가 보인 M&A 단계상승과 전혀 다르다.

즉 제외 근거였던 M&A 오염은 **CAGR 창 바깥(FY2026)에서 일어난 일**이었다.
분기 대차대조표를 보고 연차 손익 시계열의 오염을 추정한 것이 오류였다 -
"그럴듯한 원인을 먼저 떠올리고 검증 없이 기록하지 말 것"(WM/WCN FCF CAGR
교훈)의 재발이다. **연도 확인 없이 제외를 확정한 것 자체가 실수**였고,
이번에 정정한다.

  ⚠️ M&A는 **앞으로의** 문제로 남는다 - FY2026 실적부터는 Armis($7.75B,
  현금)·Veza·Moveworks가 연결에 들어와 다음 정식분석 때는 세그먼트/오가닉
  분리 대조가 반드시 필요하다. `falsification_conditions`에 명시했다.

## 원자료 - SEC XBRL companyfacts(CIK 0001373715, 2026-09-04 조회)

FY2015~2025 **11개년** 확보 -> 10년 CAGR을 실제로 산출할 수 있다(대체 없음).
⚠️ FY2015 매출만 `us-gaap:Revenues`($1,005.5M)에서, FY2016~2025는
`RevenueFromContractWithCustomerExcludingAssessedTax`에서 나온다(ASC 606
전환에 따른 태그 이동). **FY2016은 두 태그가 겹치는데 $1,390.5M vs
$1,391.0M으로 사실상 동일**($0.5M, 0.04% 차이)해 같은 측정치임을 확인했다 -
CROX/MEDP에서 겪은 '태그 전환이 실제 정의 변경이었던' 사례와 달리 여기서는
연속성이 실측으로 확인된다.

## ⭐ 발견 2 - 'AI가 좌석형 SaaS를 죽인다'는 서사를 회사가 실적으로 반박 중

2026-09-04 WebSearch로 확인한 Q2 2026(2026-07 발표):
  - 구독매출 $3,877M **+24.5%YoY**(상수통화 +23%, 가이던스 상단을 1.5%p 초과)
  - **cRPO +21.5%(상수통화)로 가이던스를 2%p 이상 초과** - 2026-08-14
    스크리닝 노트가 인용했던 "organic cRPO growth decelerating to high
    teens"보다 실제 실적이 높았다.
  - FY2026 구독매출 가이던스 상향: **$15.76~15.78B(+21% 상수통화)**
  - ServiceNow AI 연간계약금액(ACV) **$10억 돌파**, 에이전틱 배포가 9개월간
    9배 증가
  - **신규 계약의 50% 이상이 좌석(seat) 기반이 아닌 가격모델** - 'AI가
    좌석 수를 줄인다'는 위협에 대해 회사가 가격모델 자체를 옮기고 있다는
    실측 증거다.

**회사 가이던스(+21% 상수통화)가 이번 엔진 Realistic Growth와 거의 같은
수준**이라 KEYS/KLAC 같은 '성장 과소추정' 우려도, TCOM/GEN 같은 '가이던스가
CAGR보다 훨씬 낮음' 우려도 해당하지 않는다 - 두 값이 정합적인 드문 사례다.

## ⚠️ 순부채 처리 - 유가증권을 포함했다

FY2026 2분기말: 차입금 $5,435M(Armis 인수 자금조달로 $1,491M -> $5,435M 급증),
현금 $2,503M, **매도가능채무증권 $4,213M**. 현금만 쓰면 순부채 +$2,932M이지만
유가증권은 다툼의 여지 없이 회사 자신의 유동자산이므로 포함해 **-$1,281M
(순현금)**으로 잡는다. DLO의 '가맹점 예치금'과 성격이 정반대다(그쪽은 남의
돈, 이쪽은 내 돈).
  ⚠️ 이 선택이 결과에 미치는 영향은 작다 - 이 엔진의 `implied_growth_*()`는
  기업가치가 아니라 시가총액에 직접 역산하므로 `net_debt`는 DRS의 leverage
  항목으로만 들어간다.

## 경쟁구도

Microsoft(Power Platform + Copilot, 번들 위협) > Salesforce(인접 워크플로) >
AI네이티브 자동화 스타트업. ServiceNow는 ITSM/엔터프라이즈 워크플로에서
여전히 선두이며, 위 '비좌석 가격모델 50%+'가 AI 위협에 대한 실질적 대응으로
확인된다.

## 실행: python3 scripts/analyze_now_2026_09_04.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.filing_dates import pit_inputs_for
from engine.pipeline import AnalysisInputs, run_analysis, save_ledger
from engine.provenance import provenance_from_sec_facts

TICKER = "NOW"
UA = "IRS Research chlalsrl1203@gmail.com"
TODAY = "2026-09-05"   # ⚠️ 실행이 UTC 날짜 경계를 넘겨 ledger 파일명(analyzed_at 기준)과
              # 맞췄다 - v3.35에서 ETF ledger가 두 날짜로 갈릴 뻔한 사고와 같은 지점.

# ── SEC XBRL companyfacts 실측(2026-09-04 조회) ──────────────────────────
# FY2015만 us-gaap:Revenues, FY2016~ RevenueFromContractWithCustomer...
# (FY2016 두 태그 겹침 구간에서 $1,390.5M vs $1,391.0M로 연속성 확인)
REVENUE = {
    2015: 1005500000.0, 2016: 1391000000.0, 2017: 1918500000.0,
    2018: 2608800000.0, 2019: 3460000000.0, 2020: 4519000000.0,
    2021: 5896000000.0, 2022: 7245000000.0, 2023: 8971000000.0,
    2024: 10984000000.0, 2025: 13278000000.0,
}
OPERATING_INCOME = {
    2015: -166400000.0, 2016: -382200000.0, 2017: -64400000.0,
    2018: -42400000.0, 2019: 42000000.0, 2020: 199000000.0,
    2021: 257000000.0, 2022: 355000000.0, 2023: 762000000.0,
    2024: 1364000000.0, 2025: 1824000000.0,
}
OPERATING_CASHFLOW = {
    2015: 317800000.0, 2016: 159100000.0, 2017: 642900000.0,
    2018: 811100000.0, 2019: 1236000000.0, 2020: 1786000000.0,
    2021: 2191000000.0, 2022: 2723000000.0, 2023: 3398000000.0,
    2024: 4267000000.0, 2025: 5444000000.0,
}
CAPEX = {
    2015: 87500000.0, 2016: 105600000.0, 2017: 150500000.0,
    2018: 224500000.0, 2019: 265000000.0, 2020: 419000000.0,
    2021: 392000000.0, 2022: 550000000.0, 2023: 694000000.0,
    2024: 852000000.0, 2025: 868000000.0,
}
NET_INCOME = {
    2015: -198400000.0, 2016: -414200000.0, 2017: -116800000.0,
    2018: -26700000.0, 2019: 626700000.0, 2020: 119000000.0,
    2021: 230000000.0, 2022: 325000000.0, 2023: 1731000000.0,
    2024: 1425000000.0, 2025: 1748000000.0,
}
SBC = {
    2015: 257700000.0, 2016: 317700000.0, 2017: 394000000.0,
    2018: 544000000.0, 2019: 662000000.0, 2020: 870000000.0,
    2021: 1131000000.0, 2022: 1401000000.0, 2023: 1604000000.0,
    2024: 1746000000.0, 2025: 1955000000.0,
}

# ── 대차대조표(2026-06-30 10-Q) ──────────────────────────────────────────
DEBT = 5435000000.0        # LongTermDebt(Armis 인수 자금조달로 급증)
CASH = 2503000000.0        # CashAndCashEquivalentsAtCarryingValue
AFS_SECURITIES = 4213000000.0  # AvailableForSaleDebtSecuritiesAmortizedCostBasis
NET_DEBT = DEBT - CASH - AFS_SECURITIES        # -$1,281,000,000(순현금)

DA_2025 = 738000000.0      # DepreciationDepletionAndAmortization(FY2025)
EBITDA = OPERATING_INCOME[2025] + DA_2025      # $2,562,000,000

# ── 시가총액(2026-09-04) ─────────────────────────────────────────────────
PRICE = 141.26             # Alpha Vantage GLOBAL_QUOTE, latestDay 2026-09-04
SHARES_OUT = 1034000000.0  # 2026-06-30 10-Q 표지 dei:EntityCommonStockSharesOutstanding
MARKET_CAP = PRICE * SHARES_OUT                # 약 $146.06B

RF = 0.0475


def build_inputs() -> AnalysisInputs:
    pit = pit_inputs_for(TICKER, TODAY, list(REVENUE), user_agent=UA)

    try:
        from engine.data.providers.sec import fetch_company_facts, ticker_to_cik

        facts = fetch_company_facts(ticker_to_cik(TICKER, UA), UA)
        provenance = provenance_from_sec_facts(facts, TICKER, TODAY, list(REVENUE))
    except Exception:  # noqa: BLE001
        provenance = None

    return AnalysisInputs(
        ticker=TICKER,
        company_name="ServiceNow, Inc.",
        revenue_by_year=REVENUE,
        operating_income_by_year=OPERATING_INCOME,
        operating_cashflow_by_year=OPERATING_CASHFLOW,
        capex_by_year=CAPEX,
        market_cap=MARKET_CAP,
        net_debt=NET_DEBT,
        ebitda=EBITDA,
        risk_free_rate=RF,
        usd_fx_rate=1.0,
        competitor_threat_weights=[0.35, 0.25, 0.20],
        market_share_trend_pp_per_year=0.5,
        active_antitrust_or_regulatory_case=False,
        demand_sensitivity_pct=0.20,
        subjective_input_basis=(
            "competitor_threat_weights=[0.35(Microsoft - Power Platform + "
            "Copilot 번들, 엔터프라이즈 전반 침투력이 가장 큰 위협), "
            "0.25(Salesforce - 인접 워크플로/CRM에서 중첩), 0.20(AI네이티브 "
            "자동화 스타트업 - 서사상 위협이나 아직 점유율 실측 증거 없음)]. "
            "market_share_trend_pp_per_year=+0.5 - 2026-09-04 WebSearch로 "
            "확인한 Q2 2026 cRPO +21.5%(상수통화)가 가이던스를 2%p 이상 "
            "초과했고 ServiceNow AI ACV가 $10억을 넘겨 점유율이 후퇴하고 "
            "있다는 증거가 없다. 다만 '워크플로 SW 시장에서 점유율이 얼마나 "
            "늘고 있는가'를 직접 측정한 자료를 확보하지 못해 완만한 양(+)값만 "
            "반영한다(모르는 것을 크게 반영하지 않는다). "
            "demand_sensitivity_pct=0.20 - CLAUDE.md 업종앵커표 '기업용 필수 "
            "SW·전문서비스(계약기반, 전환비용 높음)' 버킷 앵커값 그대로 "
            "(CDNS·WDAY·GWRE·PTC 등과 같은 버킷). RPO $29.0B / cRPO $13.2B의 "
            "계약잔액이 이 낮은 민감도를 뒷받침한다."
        ),
        model_used="two_stage",
        model_choice_reason=(
            "매출 CAGR(3y 22.4% / 5y 24.1% / 10y 29.4%)이 default_terminal_"
            "growth(2.0~4.5%)를 크게 웃도는 고성장 국면이라 Gordon 정상상태 "
            "가정이 성립하지 않는다. 동시에 **11개년 YoY가 38.4%에서 20.9%로 "
            "단조 감속하는 교과서적 수렴 경로**를 이미 그리고 있고 회사 자신의 "
            "FY2026 가이던스(+21% 상수통화)도 그 연장선에 있어, 고성장->terminal "
            "수렴을 명시적으로 모형화하는 two_stage가 이 구조에 정확히 맞는다. "
            "이 종목은 감속 자체가 관측 가능하므로 모델 선택의 자의성이 "
            "VRT(모델괴리 10.88%p) 같은 종목보다 작다."
        ),
        falsification_conditions=(
            "(1) **FY2026 10-K(2027-01경)에서 유기적/비유기적 성장을 반드시 "
            "분리 대조할 것** - Armis($7.75B, 이미 종결)·Veza·Moveworks가 "
            "FY2026부터 연결에 들어와 GEN/BRO/ROP와 같은 M&A CAGR 왜곡이 "
            "**다음 분석부터는 실제로 발생한다**. 회사 공시 구독매출 유기적 "
            "성장률이 연결 성장률보다 3%p 이상 낮으면 이 판정을 재검토. "
            "(2) cRPO 상수통화 성장률이 두 분기 연속 20% 아래로 떨어지면 - "
            "cRPO는 매출보다 먼저 움직이는 선행지표다. "
            "(3) 비좌석(non-seat) 가격모델 신규계약 비중이 50%에서 후퇴하면 - "
            "'AI가 좌석 수를 줄인다'는 위협에 대한 회사의 대응이 실패하고 "
            "있다는 신호. (4) ServiceNow AI ACV 성장이 정체되면. "
            "(5) 차입금이 Armis 인수 자금조달($1,491M -> $5,435M) 이후 추가로 "
            "크게 늘면 - 연쇄 M&A 자금조달이 재무 유연성을 잠식한다."
        ),
        price_at_analysis=PRICE,
        currency="USD",
        net_income_by_year=NET_INCOME,
        sbc_by_year=SBC,
        data_sources=[
            "SEC XBRL companyfacts (CIK 0001373715 ServiceNow, 조회 2026-09-04)",
            "SEC 10-Q (2026-06-30 대차대조표: 차입금/현금/매도가능증권, "
            "표지 발행주식수 1,034,000,000주)",
            "Alpha Vantage GLOBAL_QUOTE (latestDay 2026-09-04, $141.26)",
            "WebSearch: NOW Q2 2026 실적(구독매출 +24.5%, cRPO +21.5% cc)·"
            "FY2026 가이던스·ServiceNow AI ACV $1B·비좌석 가격모델 50%+·"
            "Armis 인수 종결일(investor.servicenow.com/TradingView/CNBC/"
            "TechTimes, 2026-09-04 재인용)",
        ],
        **pit,
        provenance=provenance,
    )


def main() -> int:
    result = run_analysis(build_inputs())
    path = save_ledger(result)

    g, d, ig = result["growth"], result["discount_rate"], result["implied_growth"]
    print(f"=== {TICKER} {TODAY} ===")
    print(f"시가총액       : ${MARKET_CAP/1e9:,.2f}B  (주가 ${PRICE}, "
          f"주식수 {SHARES_OUT:,.0f})")
    print(f"순부채         : ${NET_DEBT/1e6:,.1f}M  (차입금 ${DEBT/1e6:,.0f}M - "
          f"현금 ${CASH/1e6:,.0f}M - 유가증권 ${AFS_SECURITIES/1e6:,.0f}M)")
    print(f"DRS            : {result['drs']['score']:.2f}   r={d['r']*100:.2f}%  "
          f"g_term={d['g_terminal']*100:.2f}%")
    print(f"Lynch 유형     : {result['lynch']['used']}  "
          f"cap={g['breakdown']['cap_applied']}")
    print(f"Realistic Growth: {g['realistic_growth']*100:.2f}%  "
          f"(할인전 {g['breakdown']['base_growth_after_fcf_check']*100:.2f}%)")
    print(f"  매출 CAGR    : {g['breakdown']['revenue_cagr_inputs']}")
    print(f"Implied Growth : {ig['value']*100:.2f}%  ({ig['model_used']}) "
          f"[single {ig['models']['single_stage']*100:.2f}% / "
          f"two {ig['models']['two_stage']*100:.2f}%, "
          f"괴리 {ig['models']['divergence']*100:.2f}%p]")
    print(f"Expectation Gap: {result['expectation_gap']*100:+.2f}%p  "
          f"-> {result['judgment']} ({result['judgment_grade']})")
    print(f"RAR            : {result['rar']:+.4f}")
    print(f"Confidence     : {result['confidence']['final']}/100")
    sc = result.get("sensitivity_check") or {}
    print(f"강건성점검     : flip={sc.get('judgment_flipped')}")
    sbc = result.get("sbc_cross_check") or {}
    if sbc.get("sbc_to_fcf_pct") is not None:
        print(f"SBC 교차검증   : SBC/FCF {sbc['sbc_to_fcf_pct']*100:.1f}%  "
              f"Gap {sbc['gap_sbc_adjusted']*100:+.2f}%p  "
              f"flip={sbc['judgment_flipped']}")
    pit = (result.get("meta") or {}).get("point_in_time") or {}
    print(f"PIT            : {pit.get('status')} "
          f"(위반 {len(pit.get('violations') or [])}건)")
    print("\n[data_limitations]")
    for lim in result.get("data_limitations") or []:
        print(f"  - {lim}")
    print(f"\nsaved: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
