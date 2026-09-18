"""
Vertiv Holdings Co(VRT) 정식 재분석 - 2026-09-04. **보유 2순위(19.2%) 종목.**

경위: 사용자 보유 포트폴리오 정밀 재검토. 기존 ledger는 2026-08-02판
(Gap +1.72%p "적정가/경계선", DRS 41.2, Confidence 94)인데 그 사이
`ENGINE_VERSION`이 v3.71 -> v3.80으로 올랐고 시가총액도 크게 움직였다.

## ⚠️ 데이터 함정 1 - SPAC 잔존 오염을 실제 원자료로 확인했다(v3.71 추정 -> 확정)

v3.71은 VRT의 재작성률 0.105를 보고 "SPAC 잔존 오염 가능성이 높다"고
**추정만** 하고 남겨뒀다(최대편차 491.4%). 이번에 companyfacts를 직접
열어 확정했다 - CIK 0001674101은 원래 **GS Acquisition Holdings Corp**
(SPAC)이고 2020-02-07 Vertiv와 합병하며 개명했다. 그래서 같은 CIK 안에
**전혀 다른 두 법인의 재무제표가 섞여 있다**:

  - `operating_cashflow` FY2016 = **-25,000** / FY2018 = **-710,388**
    (껍데기 법인 규모 - 수만~수십만 달러)
  - 같은 해 `revenue` FY2018 = **$4,285,600,000**(실제 Vertiv 예비법인)
  - `revenue` FY2017 = **0**

즉 어느 창을 쓰든 FY2020(합병 완료) 이전은 두 법인이 섞일 위험이 있다.
**FY2020~2025 6개년만 사용**하며, 이는 기존 ledger(2026-08-02)와 동일한
창이라 이번 변화가 순수하게 '데이터 갱신' 때문임을 분리해 볼 수 있다
(PTC 재분석에서 쓴 것과 같은 통제 설계).

  ⚠️ FY2019 예비법인 수치(revenue $4,431.2M / opinc $206.1M / OCF $57.5M /
  capex $47.6M)는 후속 10-K에 재작성돼 있어 값 자체는 일관돼 보였으나,
  **의도적으로 넣지 않았다** - 이 CIK에서 법인 혼입이 실측으로 확인된
  이상 합병 이전 연도를 끌어오는 것은 PTC에서 FY2015~2016 구독전환기를
  잘못 넣을 뻔한 것과 같은 유형의 위험이다. 6개년뿐이라 10년 CAGR이
  5년으로 자동 대체되며(엔진이 `data_limitations`에 기록) 그만큼 DRS가
  관대해질 수 있다는 점은 알려진 한계로 남긴다.

## ⚠️ 데이터 함정 2 - FY2022 FCF가 음수다(계산은 막히지 않는다)

OCF FY2022 = **-$152.8M**(공급망 비용 급등·운전자본 악화) -> FCF -$252.8M.
5년 CAGR 기준연도는 FY2020(FCF +$164.5M)이라 v3.19 음수 가드에 걸리지
않지만, **시계열 한가운데 음수가 있다는 사실 자체**가 이 회사의 현금흐름
변동성이 크다는 신호다(MU의 '근사-0 기준연도'와도, PODD의 '적자->흑자
최초전환'과도 다른 제3의 형태 - 흑자->적자->흑자 비단조, ONON과 같은 유형).

## ⭐ 핵심 발견 1 - 기존 ledger 대비 시가총액이 +26% 커졌다

  - 기존(2026-08-02): market_cap $85.67B, net_debt $1,085.1M
  - 이번(2026-09-04): **market_cap ~$108.0B**(주가 $280.53 x 발행주식수
    384,988,173주, 2026-07-27 10-Q 표지), **net_debt $129.2M**

순부채가 $1,085.1M -> **$129.2M**으로 급감한 것은 부채 상환이 아니라
**현금 급증**이다(현금 FY2025말 $1,728.4M -> 2026-06-30 $2,810.6M, 차입금은
$2,913.0M -> $2,939.8M로 거의 불변). AI 데이터센터 수요로 영업현금흐름이
폭증한 결과. net_debt/EBITDA가 약 **0.06x**로 사실상 무차입 상태다.

⚠️ **정정** - 초판 docstring에 "순부채 감소가 기업가치를 낮춰 Gap을 넓힌다"고
적었는데 **틀렸다**. 이 엔진의 `implied_growth_*()`는 기업가치(EV)가 아니라
**시가총액에 직접** 역산하며(engine/pipeline.py:848 `compare_implied_growth_
models(inputs.market_cap, ...)`), `net_debt`는 오직 DRS의 `leverage` 항목으로만
들어간다. 실제로 순부채가 $1,085.1M -> $129.2M으로 8배 넘게 줄었는데도
`leverage_score`가 둘 다 6.0이라 **DRS가 41.20으로 정확히 불변**이었다.
따라서 이번 Gap 변화는 **100% 시가총액 증가 때문**이다(성장률·DRS 전부 불변).

## ⭐ 핵심 발견 2 - 회사 자체 가이던스(+30~32% 오가닉)가 trailing CAGR을
크게 상회한다 - KEYS/KLAC와 같은 계열의 '성장 과소추정' 후보

2026-09-04 WebSearch로 확인한 Q2 2026 실적·가이던스:
  - Q2 순매출 $3,274M, **오가닉 +18%**(인수 +5%, 환율 +1%)
  - **수주잔고 $15B**(전년比 2배 이상), book-to-bill **2.9x**
  - FY2026 가이던스 상향: 순매출 $13.8~14.2B, **오가닉 성장 +30~32%**,
    조정영업마진 23.3~24.3%, 조정 EPS $6.65~6.75

엔진의 Realistic Growth는 매출 3y/5y CAGR 가중평균에서 나오는데, 회사
가이던스는 그보다 훨씬 높다. CLAUDE.md '알려진 한계 3건째'(반도체/AI장비
섹터의 trailing CAGR 성장과소추정, KEYS·KLAC 2건 관측)와 **같은 구조**이며
VRT가 3번째 관측 사례가 된다. ⚠️ 다만 KEYS 크로스체크가 확립한 기준대로
**검증 안 된 1개년 가이던스를 `realistic_growth_override`로 승격하지
않는다**(ROP는 다년 실현 오가닉 실적이 있었기에 승격됐다). 대신
`falsification_conditions`에 검증 시점을 못박고 별도 시나리오 병기로만
다룬다.

## ⭐ 핵심 발견 3 - v3.67 규모조건부 성장상한이 '거의' 걸린다(바인딩 안 함)

매출 $10.23B(2015년 달러 환산 $7,577.7M) -> base_rates 구간 **7000-12000**.
이 구간에서 실질 20% 이상을 10년간 유지한 기업은 **1.1%**뿐이라 명목
상한이 **23.00%**로 계산된다. 이번 Realistic Growth는 그보다 낮아
바인딩되지 않지만, **회사 가이던스(+30~32%)는 이 역사적 상한을 크게
웃돈다** - 즉 가이던스를 다년 성장률로 그대로 믿는 것은 이 규모에서
역사적으로 1% 미만의 기업만 해낸 일을 가정하는 셈이다.

## ⚠️ 기존 ledger의 알려진 취약성 2건(그대로 유효)

  1) **모델괴리 8.68%p**(single_stage 8.31% vs two_stage 16.99%) - 경고
     임계값 3%p의 약 3배. v3.51이 "모델선택 단독으로 Gap이 12~20%p
     움직이는 9종목"에 VRT를 포함시킨 근거.
  2) **성장프리미엄 +9.92%p로 34종목 중 1위**(v3.45 market_relative) -
     시장이 이 종목에 시장평균보다 훨씬 낙관적인 성장을 이미 가격에
     반영해뒀다는 뜻.

## 경쟁구도(2026-09-04 WebSearch)

데이터센터 전력 시장은 Schneider Electric·ABB·Eaton·Vertiv·Delta가
합계 41~43%를 나눠 갖는 과점이고, **정밀냉각(precision cooling)에서
Vertiv 점유율 23%**. Eaton은 2025-07 Resilient Power Systems를 인수해
UPS 경쟁력을 보강했다. 다만 차세대 AI 학습시설이 전력·냉각·제어의
긴밀한 통합을 요구하는 방향이라 **부품 단품 공급자보다 통합 인프라
공급자에 유리**하다는 것이 업계 평가 - VRT의 상대적 위치는 유지~소폭
개선으로 본다.

## 실행: python3 scripts/analyze_vrt_2026_09_04.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.filing_dates import pit_inputs_for
from engine.pipeline import AnalysisInputs, run_analysis, save_ledger
from engine.provenance import provenance_from_sec_facts

TICKER = "VRT"
UA = "IRS Research chlalsrl1203@gmail.com"
TODAY = "2026-09-04"

# ── SEC XBRL companyfacts 실측(2026-09-04 조회, CIK 0001674101) ──────────
# ⚠️ FY2020부터. 그 이전은 GS Acquisition Holdings(SPAC) 재무제표와 섞인다.
REVENUE = {
    2020: 4370600000.0, 2021: 4998100000.0, 2022: 5691500000.0,
    2023: 6863200000.0, 2024: 8011800000.0, 2025: 10229900000.0,
}
OPERATING_INCOME = {
    2020: 213500000.0, 2021: 259900000.0, 2022: 223400000.0,
    2023: 872200000.0, 2024: 1367400000.0, 2025: 1829700000.0,
}
OPERATING_CASHFLOW = {
    2020: 208900000.0, 2021: 210900000.0, 2022: -152800000.0,
    2023: 900500000.0, 2024: 1319300000.0, 2025: 2113800000.0,
}
CAPEX = {
    2020: 44400000.0, 2021: 73400000.0, 2022: 100000000.0,
    2023: 127900000.0, 2024: 167000000.0, 2025: 220000000.0,
}
NET_INCOME = {
    2020: -327300000.0, 2021: 119600000.0, 2022: 76600000.0,
    2023: 460200000.0, 2024: 495800000.0, 2025: 1332800000.0,
}
SBC = {
    2020: 13000000.0, 2021: 23200000.0, 2022: 24700000.0,
    2023: 25000000.0, 2024: 34600000.0, 2025: 45900000.0,
}

# ── 대차대조표(2026-06-30 10-Q, SEC XBRL 실측) ───────────────────────────
# 기존 ledger(2026-08-02)는 net_debt $1,085.1M을 썼는데, 그 사이 현금이
# $1,728.4M(FY2025말) -> $2,810.6M으로 급증해 순부채가 사실상 사라졌다.
DEBT_LATEST = 2939800000.0   # LongTermDebt(비유동 2,939.8 + 유동 0)
CASH_LATEST = 2810600000.0   # CashAndCashEquivalentsAtCarryingValue
NET_DEBT = DEBT_LATEST - CASH_LATEST          # $129,200,000

DA_2025 = 308600000.0        # DepreciationDepletionAndAmortization(FY2025)
EBITDA = OPERATING_INCOME[2025] + DA_2025     # $2,138,300,000

# ── 시가총액(2026-09-04) ─────────────────────────────────────────────────
PRICE = 280.53               # Alpha Vantage GLOBAL_QUOTE, latestDay 2026-09-04
SHARES_OUT = 384988173.0     # 2026-07-27 10-Q 표지 dei:EntityCommonStockSharesOutstanding
MARKET_CAP = PRICE * SHARES_OUT               # 약 $108.0B

RF = 0.0475


def build_inputs() -> AnalysisInputs:
    pit = pit_inputs_for(TICKER, TODAY, list(REVENUE), user_agent=UA)

    try:
        from engine.data.providers.sec import fetch_company_facts, ticker_to_cik

        cik = ticker_to_cik(TICKER, UA)
        facts = fetch_company_facts(cik, UA)
        provenance = provenance_from_sec_facts(facts, TICKER, TODAY, list(REVENUE))
    except Exception:  # noqa: BLE001 - provenance는 부가 기록
        provenance = None

    return AnalysisInputs(
        ticker=TICKER,
        company_name="Vertiv Holdings Co",
        revenue_by_year=REVENUE,
        operating_income_by_year=OPERATING_INCOME,
        operating_cashflow_by_year=OPERATING_CASHFLOW,
        capex_by_year=CAPEX,
        market_cap=MARKET_CAP,
        net_debt=NET_DEBT,
        ebitda=EBITDA,
        risk_free_rate=RF,
        usd_fx_rate=1.0,
        competitor_threat_weights=[0.45, 0.30, 0.20],
        market_share_trend_pp_per_year=0.0,
        active_antitrust_or_regulatory_case=False,
        demand_sensitivity_pct=0.45,
        subjective_input_basis=(
            "기존 ledger(2026-08-02)의 주관적 입력을 **의도적으로 그대로** "
            "유지했다 - 이번 재분석의 목적이 '데이터 갱신이 판정을 어떻게 "
            "바꾸는가'를 분리해 보는 것이라, 주관 입력을 동시에 손대면 "
            "원인 분해가 불가능해진다(PTC 재분석과 같은 통제 설계). "
            "competitor_threat_weights=[0.45(Schneider Electric), "
            "0.30(Eaton), 0.20(ABB/Delta 등)] - 2026-09-04 WebSearch 재확인: "
            "데이터센터 전력 시장을 Schneider·ABB·Eaton·Vertiv·Delta가 "
            "합계 41~43%로 나눠 갖는 과점이고 Schneider가 최대 경쟁자, "
            "Eaton은 2025-07 Resilient Power Systems 인수로 UPS 경쟁력 보강. "
            "market_share_trend_pp_per_year=0.0 - 정밀냉각 점유율 23%로 "
            "선두권이나 대형 경쟁사들도 같은 AI 순풍을 받고 있어 상대 "
            "점유율의 뚜렷한 추세 증거를 확인하지 못했다(모른다를 0으로 "
            "두는 것이지 '변화 없음'을 확인한 것이 아니다). "
            "demand_sensitivity_pct=0.45 - CLAUDE.md 업종앵커표 '자본재/"
            "데이터센터 인프라(설비투자 사이클)' 버킷 앵커값 그대로. "
            "하이퍼스케일러 capex 사이클에 직접 노출되며, FY2022 영업현금흐름 "
            "-$152.8M이 그 변동성의 실측 증거다."
        ),
        model_used="two_stage",
        model_choice_reason=(
            "⚠️ 이 종목은 **모델선택 취약 종목**이다 - 기존 ledger 실측 "
            "모델괴리 8.68%p(single_stage 8.31% vs two_stage 16.99%)로 경고 "
            "임계값 3%p의 약 3배이고, v3.51 gap_range 분석이 '모델선택 단독으로 "
            "Gap이 12~20%p 움직이는 9종목'에 VRT를 포함시켰다. 그럼에도 "
            "two_stage를 유지하는 근거는 (1) trailing 매출 CAGR(3y 21.6%/5y 18.5%)이 "
            "default_terminal_growth(2.0~4.5%)를 압도적으로 웃돌아 Gordon 정상상태 "
            "가정이 성립하지 않고, (2) 회사 자신이 FY2026 오가닉 +30~32%를 "
            "가이던스하며 수주잔고가 전년比 2배($15B, book-to-bill 2.9x)로 "
            "현재가 명백한 고성장 국면임을 보여주며, (3) 동시에 v3.67 규모조건부 "
            "상한이 이 매출규모에서 역사적 지속가능 상한을 명목 23.00%로 "
            "제시해(base rate 1.1%) 언젠가 수렴이 불가피함을 시사하기 때문이다. "
            "고성장->수렴 경로를 명시적으로 모형화하는 two_stage가 이 구조에 "
            "맞다. **단, 판정은 이 선택에 민감하므로 Gap 절대값을 액면 그대로 "
            "신뢰하지 말 것**(v3.51 robust=False 종목)."
        ),
        falsification_conditions=(
            "(1) 2026-11월경 Q3 2026 실적에서 수주잔고($15B)가 전분기 대비 "
            "감소하거나 book-to-bill이 1.0x 아래로 떨어지면 - AI 데이터센터 "
            "수주 사이클의 정점 통과 신호이므로 이 판정을 재검토할 것. "
            "(2) FY2026 오가닉 성장이 가이던스 하단(+30%)을 밑돌면 - 회사 "
            "자체 가이던스가 trailing CAGR을 크게 웃도는 상태(KEYS/KLAC와 "
            "같은 계열)이므로, 그 괴리가 실현되지 않으면 성장 전제 자체가 "
            "무너진다. (3) 하이퍼스케일러(Microsoft/Google/Amazon/Meta) "
            "데이터센터 capex 가이던스가 하향되면 - demand_sensitivity 0.45의 "
            "근거가 되는 외생 수요원이다. (4) 조정영업마진이 가이던스 하단"
            "(23.3%)을 밑돌면 - Schneider/Eaton과의 경쟁이 가격으로 번지고 "
            "있다는 신호."
        ),
        price_at_analysis=PRICE,
        currency="USD",
        net_income_by_year=NET_INCOME,
        sbc_by_year=SBC,
        data_sources=[
            "SEC XBRL companyfacts (CIK 0001674101, 조회 2026-09-04)",
            "SEC 10-Q 표지 (2026-07-27, 발행주식수 384,988,173주)",
            "SEC 10-Q 대차대조표 (2026-06-30, 차입금 $2,939.8M / 현금 $2,810.6M)",
            "Alpha Vantage GLOBAL_QUOTE (latestDay 2026-09-04, $280.53)",
            "WebSearch: VRT Q2 2026 실적·FY2026 가이던스·데이터센터 전력 시장 "
            "점유율(investors.vertiv.com/PRNewswire/MarketsandMarkets, "
            "2026-09-04 재인용)",
        ],
        **pit,
        provenance=provenance,
    )


def main() -> int:
    result = run_analysis(build_inputs())
    path = save_ledger(result)

    g = result["growth"]
    d = result["discount_rate"]
    print(f"=== {TICKER} {TODAY} ===")
    print(f"시가총액       : ${MARKET_CAP/1e9:,.2f}B  (주가 ${PRICE}, "
          f"주식수 {SHARES_OUT:,.0f})")
    print(f"순부채         : ${NET_DEBT/1e6:,.1f}M   "
          f"(net_debt/EBITDA {NET_DEBT/EBITDA:.3f}x)")
    print(f"DRS            : {result['drs']['score']:.2f}   r={d['r']*100:.2f}%  "
          f"g_term={d['g_terminal']*100:.2f}%")
    print(f"Lynch 유형     : {result['lynch']['used']}  "
          f"cap={g['breakdown']['cap_applied']}")
    print(f"Realistic Growth: {g['realistic_growth']*100:.2f}%  "
          f"(구조적할인 {g['structural_discount_pct']*100:.2f}%, "
          f"할인전 {g['breakdown']['base_growth_after_fcf_check']*100:.2f}%)")
    ig = result['implied_growth']
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
