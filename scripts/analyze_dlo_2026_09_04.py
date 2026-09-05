"""
DLocal Limited(DLO) 최초 정식 분석 - 2026-09-04. **보유 4순위(11.1%) 종목.**

경위: 사용자 보유 포트폴리오 정밀 재검토. 이 프로젝트가 **한 번도 분석한 적
없는 종목**이다(ledger 없음, 스크리너 통과 이력 없음). 보유비중 11.1%가 아무런
정량 근거 없이 유지되고 있었다는 뜻이라 우선순위를 높여 다뤘다.

## 원자료 - IFRS 20-F(우루과이 소재 외국 발행사, CIK 0001846832)

`ifrs-full` 택소노미를 쓰는 첫 정식분석 종목이다(기존 60여 종목은 전부
`us-gaap`). 태그 대응:
  - `Revenue` -> revenue
  - `ProfitLossFromOperatingActivities` -> operating_income
  - `CashFlowsFromUsedInOperatingActivities` -> operating_cashflow
  - `PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities` -> capex
  - `ExpenseFromSharebasedPaymentTransactionsWithEmployees` -> SBC
FY2019~2025 7개년 확보(2021-06 IPO 이전 연도까지 20-F에 재작성돼 있다).
10년 CAGR은 산출 불가 -> 엔진이 5년으로 자동 대체(그 사실을 기록).

## ⚠️⚠️ 최대 한계 - 결제대행업의 영업현금흐름은 '가맹점 예치금'으로 심하게
왜곡된다. 이 종목의 FCF-DCF 결과는 다른 종목과 같은 신뢰도로 읽으면 안 된다.

FCF(=OCF-capex) 실측: 2021 $106.5M -> 2022 $153.5M -> 2023 $292.5M ->
**2024 -$34.5M(음수)** -> 2025 $413.2M. 한 해 만에 -$34.5M에서 +$413.2M으로
뒤집히는 것은 사업이 그렇게 변한 게 아니라 **가맹점에 지급할 대금의 결제
타이밍**이 운전자본을 통해 OCF를 관통하기 때문이다. 실제로 FY2025말
대차대조표에서 현금 $719.9M보다 **매입채무 등이 $854.4M으로 더 크다** -
보유 현금의 상당부분이 회사 돈이 아니라 가맹점에 줄 돈이다.

이 프로젝트가 보험업(v3.22 플로트)에서 만난 것과 **같은 계열의 구조적 왜곡**
이며, 보험업처럼 전용 경로(`is_insurer`)를 만들 만큼 실증사례가 쌓이지
않았다. 그래서 두 가지로 대응한다:

  (1) **순부채를 보수적으로 잡는다** - 표준 처리(차입금 - 현금 = **-$633.2M**
      순현금)를 쓰지 않고 **차입금만($86.7M)**을 순부채로 쓴다. 매입채무
      $854.4M > 현금 $719.9M이라 주주에게 귀속되는 여유현금이 있다고 볼
      근거가 없기 때문이다.
      ⚠️ **효과는 생각보다 작다** - 이 엔진의 `implied_growth_*()`는 기업가치가
      아니라 **시가총액에 직접** 역산하므로(engine/pipeline.py:848),
      `net_debt`는 오직 DRS의 `leverage` 항목으로만 들어간다. 실측 차이는
      `leverage_score` 6.0(보수적, 0.35x) vs 2.0(표준, -2.57x) -> DRS 56.2 vs
      52.2로 4점뿐이다. 즉 이 보수적 처리는 '기업가치를 $720M 늘리는 것'이
      아니라 '할인율을 약간 올리는 것'에 그친다.
      **반대로 말하면 이 엔진은 순부채가 큰 회사를 밸류에이션 자체에서
      전혀 벌하지 않는다** - 알려진 구조적 한계로 기록해둔다.
  (2) **FCF0 정규화 시나리오를 병기한다** - 공식 판정은 엔진 표준대로
      최근연도 FCF($413.2M)를 쓰지만, 3년 평균($223.7M)을 쓰면 결과가
      어떻게 달라지는지 함께 낸다.

⚠️ 어느 쪽이 '맞는' 처리인지 자동으로 결정하지 않는다 - is_insurer의 P/B,
sbc_cross_check와 동일한 "병기, 자동판정 안 함" 원칙.

## ⭐ 핵심 발견 - TPV는 +92%인데 총이익은 +29%: 테이크레이트 압축이 실측된다

2026-09-04 WebSearch로 확인한 Q2 2026 실적:
  - **TPV $17.7B, +92%YoY**(2022년 1분기 이후 최고 증가율, 7분기 연속 50%+)
  - **총이익 $127M, +29%YoY**(사상 최대이지만 TPV 증가율의 **3분의 1**)
  - 신규 물량 증분 테이크레이트가 Q1 ~57bp -> Q2 **~33bp**로 급락. 회사는
    "대형 승차공유 가맹점 한 곳이 급성장하며 낮은 가격구간으로 이동한 효과"
    라고 설명하며, 그 가맹점과 환율효과를 빼면 순 테이크레이트는 전분기와
    거의 같다고 밝혔다.
  - 순매출유지율(NRR) 153%, TPV 유지율 188% - 기존 가맹점 침투가 성장의
    대부분($14.4B 증가분 중 $10.2B가 기존 가맹점의 기존 시장 물량 증가,
    신규 가맹점 기여는 $0.5B뿐인 land-and-expand 모델).
  - **가이던스 상향**: TPV 성장 +60~70%, 총이익 성장 **+25~30%**, 영업이익
    성장 +27.5~32.5%.

**회사 자신의 이익성장 가이던스(+25~32.5%)가 엔진이 계산한 매출 CAGR
(3y 37.7% / 5y 60.1%)보다 낮다.** 즉 이 종목의 성장 리스크는 '물량이
줄어드는 것'이 아니라 **'물량당 수익이 줄어드는 것'**이다 - 성장률 입력을
과거 매출 CAGR에서 뽑는 이 엔진이 구조적으로 낙관 편향될 수 있는 지점이라
`falsification_conditions`에 명시한다.

## 경쟁구도

Adyen(글로벌 대형사, 신흥국 확장 중) > Ebanx(중남미 직접 경쟁) >
Stripe/Nuvei/Payoneer(인접 위협). 테이크레이트 압축이 이미 실측되고 있으므로
경쟁강도를 낮게 잡을 근거가 없다.

## 실행: python3 scripts/analyze_dlo_2026_09_04.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.filing_dates import pit_inputs_for
from engine.pipeline import AnalysisInputs, run_analysis, save_ledger
from engine.provenance import provenance_from_sec_facts

TICKER = "DLO"
UA = "IRS Research chlalsrl1203@gmail.com"
TODAY = "2026-09-04"

# ── SEC XBRL companyfacts / ifrs-full 실측(2026-09-04 조회) ──────────────
REVENUE = {
    2019: 55289000.0, 2020: 104143000.0, 2021: 244120000.0,
    2022: 418925000.0, 2023: 650351000.0, 2024: 745974000.0,
    2025: 1093587000.0,
}
OPERATING_INCOME = {  # ifrs-full:ProfitLossFromOperatingActivities
    2019: 17564000.0, 2020: 30945000.0, 2021: 83838000.0,
    2022: 127910000.0, 2023: 179657000.0, 2024: 140500000.0,
    2025: 219915000.0,
}
OPERATING_CASHFLOW = {  # ⚠️ 2024 음수 - 가맹점 정산 타이밍(위 docstring 참고)
    2019: 30723000.0, 2020: 88486000.0, 2021: 108486000.0,
    2022: 154451000.0, 2023: 293453000.0, 2024: -32784000.0,
    2025: 415457000.0,
}
CAPEX = {
    2019: 152000.0, 2020: 876000.0, 2021: 1949000.0,
    2022: 987000.0, 2023: 965000.0, 2024: 1705000.0,
    2025: 2282000.0,
}
NET_INCOME = {
    2019: 15602000.0, 2020: 28187000.0, 2021: 77853000.0,
    2022: 108697000.0, 2023: 149086000.0, 2024: 120469000.0,
    2025: 196902000.0,
}
SBC = {
    2019: 716000.0, 2020: 7295000.0, 2021: 7590000.0,
    2022: 8684000.0, 2023: 11922000.0, 2024: 23780000.0,
    2025: 24136000.0,
}

# ── 대차대조표(FY2025말, 2025-12-31) ─────────────────────────────────────
BORROWINGS = 86713000.0            # ifrs-full:Borrowings
CASH = 719897000.0                 # ifrs-full:CashAndCashEquivalents
PAYABLES = 854436000.0             # ifrs-full:TradeAndOtherCurrentPayables
# ⚠️ 보수적 처리: 매입채무(대부분 가맹점 지급대기 대금)가 현금을 초과하므로
# 주주 귀속 여유현금을 0으로 보고 차입금만 순부채로 잡는다. 표준 처리
# (BORROWINGS - CASH = -$633.2M)와의 차이는 크로스체크로 병기한다.
NET_DEBT = BORROWINGS

DA_2025 = 26260000.0               # ifrs-full:DepreciationAndAmortisationExpense
EBITDA = OPERATING_INCOME[2025] + DA_2025     # $246,175,000

# ── 시가총액(2026-09-04) ─────────────────────────────────────────────────
PRICE = 15.52                      # Alpha Vantage GLOBAL_QUOTE, latestDay 2026-09-04
SHARES_OUT = 294931956.0           # FY2025 20-F 표지 dei:EntityCommonStockSharesOutstanding
MARKET_CAP = PRICE * SHARES_OUT    # 약 $4.58B

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
        company_name="DLocal Limited",
        revenue_by_year=REVENUE,
        operating_income_by_year=OPERATING_INCOME,
        operating_cashflow_by_year=OPERATING_CASHFLOW,
        capex_by_year=CAPEX,
        market_cap=MARKET_CAP,
        net_debt=NET_DEBT,
        ebitda=EBITDA,
        risk_free_rate=RF,
        usd_fx_rate=1.0,
        competitor_threat_weights=[0.40, 0.30, 0.20],
        market_share_trend_pp_per_year=1.0,
        active_antitrust_or_regulatory_case=False,
        demand_sensitivity_pct=0.35,
        subjective_input_basis=(
            "competitor_threat_weights=[0.40(Adyen - 글로벌 대형 결제사, 신흥국 "
            "확장 중), 0.30(Ebanx - 중남미 직접 경쟁), 0.20(Stripe/Nuvei/"
            "Payoneer 등 인접 위협)] - 2026-09-04 WebSearch로 **테이크레이트 "
            "압축이 이미 실측**됨을 확인했다(신규 물량 증분 테이크레이트 Q1 "
            "~57bp -> Q2 ~33bp). 경쟁강도를 낮게 잡을 근거가 없다. "
            "market_share_trend_pp_per_year=+1.0 - TPV가 +92%YoY로 시장 성장률을 "
            "크게 웃돌고 NRR 153%·TPV유지율 188%라 **물량 점유율은 분명히 "
            "확대 중**이나, 같은 기간 총이익 증가율은 +29%에 그쳐 **단위당 "
            "수익성은 오히려 후퇴**했다. 물량 점유율 확대를 온전히 반영하면 "
            "가격결정력 상실을 무시하게 되므로 절반 수준(+1.0)만 반영한다. "
            "demand_sensitivity_pct=0.35 - CLAUDE.md 업종앵커표 '광고·"
            "전자상거래·경기민감 산업재' 버킷(0.35) 채택. 신흥국(중남미·"
            "아프리카·아시아) 소비자 결제 물량이라 현지 경기·환율 변동에 "
            "직접 노출되며, 회사 스스로 Q2 가이던스에서 '예상치 못한 환율 "
            "역풍'을 영업이익 성장 제약요인으로 명시했다."
        ),
        model_used="two_stage",
        model_choice_reason=(
            "매출 3y CAGR 37.7% / 5y 60.1%가 default_terminal_growth(2.0~4.5%)를 "
            "압도적으로 웃도는 명백한 고성장 국면이라 Gordon 정상상태 가정"
            "(single_stage)이 성립하지 않는다. 동시에 회사 자신의 이익성장 "
            "가이던스(+25~32.5%)가 과거 매출 CAGR보다 낮고 테이크레이트 압축이 "
            "실측되고 있어 **수렴이 이미 진행 중**이다 - 고성장에서 terminal로 "
            "수렴하는 경로를 명시적으로 모형화하는 two_stage가 이 구조에 맞다. "
            "⚠️ 다만 이 종목은 FCF 자체가 가맹점 정산 타이밍에 크게 흔들려"
            "(2024 -$34.5M -> 2025 +$413.2M) 어느 모델을 쓰든 Implied Growth의 "
            "정밀도가 다른 종목보다 낮다."
        ),
        falsification_conditions=(
            "(1) 2026-11경 Q3 2026 실적에서 **총이익 성장률이 가이던스 하단"
            "(+25%)을 밑돌면** 재검토 - 이 종목의 핵심 리스크는 물량이 아니라 "
            "테이크레이트다. (2) 순 테이크레이트가 두 분기 연속 하락하면 - "
            "회사는 '대형 승차공유 가맹점 한 곳의 가격구간 이동'이라는 "
            "일회성 설명을 내놨는데, 두 분기 더 이어지면 구조적 경쟁압력으로 "
            "봐야 한다. (3) NRR이 140% 아래로 떨어지면 - 5분기 연속 140%+가 "
            "land-and-expand 모델의 근거였다. (4) FY2026 영업현금흐름이 다시 "
            "음수로 돌아서면 - 위 '가맹점 예치금' 한계가 일시적 타이밍이 "
            "아니라 반복적 패턴임을 뜻하므로 FCF-DCF 적용 자체를 재검토해야 "
            "한다. (5) 중남미 주요국(브라질·멕시코·아르헨티나)에서 결제 "
            "라이선스·외환 규제가 강화되면."
        ),
        price_at_analysis=PRICE,
        currency="USD",
        net_income_by_year=NET_INCOME,
        sbc_by_year=SBC,
        data_sources=[
            "SEC XBRL companyfacts (CIK 0001846832 DLocal Limited, ifrs-full, "
            "조회 2026-09-04)",
            "Alpha Vantage GLOBAL_QUOTE (latestDay 2026-09-04, $15.52)",
            "WebSearch: DLO Q2 2026 실적·TPV/총이익 괴리·테이크레이트 압축·"
            "FY2026 가이던스(Investing.com/StockTitan/Yahoo Finance 실적발표 "
            "요약, 2026-09-04 재인용)",
        ],
        **pit,
        provenance=provenance,
    )


def main() -> int:
    result = run_analysis(build_inputs())
    path = save_ledger(result)

    g, d, ig = result["growth"], result["discount_rate"], result["implied_growth"]
    fcf0 = OPERATING_CASHFLOW[2025] - CAPEX[2025]
    print(f"=== {TICKER} {TODAY} ===")
    print(f"시가총액       : ${MARKET_CAP/1e9:,.2f}B  (주가 ${PRICE}, "
          f"주식수 {SHARES_OUT:,.0f})")
    print(f"순부채(보수적) : ${NET_DEBT/1e6:,.1f}M  "
          f"(표준처리라면 ${(BORROWINGS-CASH)/1e6:,.1f}M)")
    print(f"FCF0           : ${fcf0/1e6:,.1f}M  "
          f"(3년평균 ${sum(OPERATING_CASHFLOW[y]-CAPEX[y] for y in (2023,2024,2025))/3/1e6:,.1f}M)")
    print(f"DRS            : {result['drs']['score']:.2f}   r={d['r']*100:.2f}%  "
          f"g_term={d['g_terminal']*100:.2f}%")
    print(f"Lynch 유형     : {result['lynch']['used']}  "
          f"cap={g['breakdown']['cap_applied']}")
    print(f"Realistic Growth: {g['realistic_growth']*100:.2f}%  "
          f"(할인전 {g['breakdown']['base_growth_after_fcf_check']*100:.2f}%)")
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
