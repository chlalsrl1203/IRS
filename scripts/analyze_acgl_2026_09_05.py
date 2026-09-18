"""
Arch Capital Group Ltd.(ACGL) 정식 재분석 - 2026-09-05. **보유 8순위(2.3%).**

경위: 사용자 보유 포트폴리오 정밀 재검토의 마지막 종목. 기존 ledger는
**2026-08-03판이고 엔진 스탬프가 v3.27**로, 이번 8종목 중 가장 낡았다.
그 사이 `ENGINE_VERSION`이 v3.27 -> v3.81로 올랐고 그중 **계산 결과를
실제로 바꾸는 변경**이 여럿 있었다:
  - v3.32: 판정 규칙 단일화 + 오버라이드가 캡 플래그를 지우지 않던 버그
  - v3.60: capex 태그 우선순위 역전(넓은 정의 1순위)
  - **v3.67: 규모조건부 성장상한**(매출 규모에 따라 Lynch 캡 위에 추가 상한)
  - v3.81: SBC 교차검증 미수렴 가드

즉 이 재실행은 '시가총액 갱신'뿐 아니라 **54개 버전만큼의 엔진 변경을
한꺼번에 통과시키는 것**이라, 다른 7종목보다 결과 이동 폭이 클 수 있다.

## 통제 설계 - 재무제표·주관적 입력은 전부 그대로

ACGL은 FY2025(2025-12-31)가 최신 연차이고 2026-08-03 분석 때와 동일하다.
**바뀌는 것은 셋뿐**이며 나머지(매출/영업이익/OCF/capex/순이익/자기자본/
배당, 경쟁강도·수요민감도·점유율추세·모델선택)는 손대지 않는다:

  1. **시가총액** $34.14B -> **$33.47B**(주가 $100.53 -> $98.10,
     발행주식수 341,229,126주 - 2026-07-30 10-Q 표지)
  2. **무위험수익률** 0.0447 -> 0.0475(이번 포트폴리오 재검토 8종목 공통)
  3. **엔진 버전** v3.27 -> v3.81

## 보험업 경로(`is_insurer=True`)는 그대로 유지한다

v3.22가 배선한 경로로, ROE x 유보율(지속가능성장률)과 P/B를 Realistic
Growth와 교차검증해 병기한다. ACGL은 이 경로를 만든 계기가 된 두 종목 중
하나다(다른 하나는 PGR) - v3.13 핵심노트가 "Gap+31.44%p/RAR3.003은
FCF-DCF를 자본집약적 보험업에 적용한 데서 오는 과장일 가능성 높음"이라고
경고해둔 바로 그 종목이다.

  ⚠️ **2026-08-03 정성 심층조사 결론을 그대로 승계한다**: 준비금 적정성·
  자본배분(BVPS +22.6%)·거버넌스는 양호하고 신용등급도 상향됐으나,
  재보험 ex-cat 컴바인드레이쇼가 2분기 연속 소폭 악화(+130~160bp YoY)
  중이고 **2025년 LA산불급 대재해리스크는 DCF의 평활화된 FCF로 전혀
  반영되지 않는다**. Confidence를 액면 94가 아니라 **80대 초중반**으로
  보라는 권고가 붙어 있다.

## 실행: python3 scripts/analyze_acgl_2026_09_05.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.filing_dates import pit_inputs_for
from engine.pipeline import AnalysisInputs, run_analysis, save_ledger
from engine.provenance import provenance_from_sec_facts

TICKER = "ACGL"
UA = "IRS Research chlalsrl1203@gmail.com"
TODAY = "2026-09-05"

# ── ledger/ACGL_2026-08-03.json의 입력값을 그대로 승계(SEC 원자료 기반) ──
REVENUE = {
    2015: 3936590000.0, 2016: 4463556000.0, 2017: 5627375000.0,
    2018: 5450568000.0, 2019: 6928200000.0, 2020: 8508509000.0,
    2021: 9249980000.0, 2022: 9614808000.0, 2023: 13634000000.0,
    2024: 17440000000.0, 2025: 19929000000.0,
}
OPERATING_INCOME = {
    2015: 567194000.0, 2016: 855552000.0, 2017: 757277000.0,
    2018: 841772000.0, 2019: 1849110000.0, 2020: 1560783000.0,
    2021: 2103351000.0, 2022: 1488493000.0, 2023: 3385000000.0,
    2024: 4474000000.0, 2025: 4979000000.0,
}
OPERATING_CASHFLOW = {
    2015: 997906000.0, 2016: 1396644000.0, 2017: 1094878000.0,
    2018: 1559322000.0, 2019: 2048458999.0, 2020: 2886505000.0,
    2021: 3427555000.0, 2022: 3815227000.0, 2023: 5749000000.0,
    2024: 6673000000.0, 2025: 6172000000.0,
}
CAPEX = {
    2015: 15736000.0, 2016: 15303000.0, 2017: 22841000.0,
    2018: 29809000.0, 2019: 37837000.0, 2020: 39872000.0,
    2021: 41394000.0, 2022: 51672000.0, 2023: 52000000.0,
    2024: 51000000.0, 2025: 44000000.0,
}
NET_INCOME = {
    2021: 2239462000.0, 2022: 1482423000.0, 2023: 4442000000.0,
    2024: 4312000000.0, 2025: 4399000000.0,
}
SHAREHOLDERS_EQUITY = {
    2021: 13545896000.0, 2022: 12910073000.0, 2023: 18353000000.0,
    2024: 20820000000.0, 2025: 24206000000.0,
}
DIVIDENDS_PAID = {2023: 40000000.0, 2024: 1906000000.0, 2025: 47000000.0}
SBC = {2025: 148000000.0}

NET_DEBT = 1736000000.0
EBITDA = 5172000000.0

# ── 시가총액(2026-09-05 기준, 종가는 latestDay 2026-09-04) ───────────────
PRICE = 98.10               # Alpha Vantage GLOBAL_QUOTE, latestDay 2026-09-04
SHARES_OUT = 341229126.0    # 2026-07-30 10-Q 표지 dei:EntityCommonStockSharesOutstanding
MARKET_CAP = PRICE * SHARES_OUT   # 약 $33.47B

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
        company_name="Arch Capital Group Ltd.",
        revenue_by_year=REVENUE,
        operating_income_by_year=OPERATING_INCOME,
        operating_cashflow_by_year=OPERATING_CASHFLOW,
        capex_by_year=CAPEX,
        market_cap=MARKET_CAP,
        net_debt=NET_DEBT,
        ebitda=EBITDA,
        risk_free_rate=RF,
        usd_fx_rate=1.0,
        competitor_threat_weights=[0.25, 0.20, 0.15],
        market_share_trend_pp_per_year=-1.5,
        active_antitrust_or_regulatory_case=False,
        demand_sensitivity_pct=0.20,
        subjective_input_basis=(
            "기존 ledger(2026-08-03, v3.27)의 주관적 입력을 **의도적으로 그대로** "
            "유지했다 - 이번 재분석의 목적이 '시가총액 갱신 + 엔진 54개 버전 "
            "변경이 판정을 어떻게 바꾸는가'를 분리해 보는 것이라, 주관 입력을 "
            "동시에 손대면 원인 분해가 불가능해진다(PTC·VRT·SE와 같은 통제 설계). "
            "competitor_threat_weights=[0.25(대형 재보험사), 0.20(특수보험 "
            "경쟁사), 0.15(모기지보험 경쟁)] - 3개 세그먼트(재보험·특수보험·"
            "모기지보험) 각각의 주요 경쟁자를 반영. "
            "market_share_trend_pp_per_year=-1.5 - 2026-08-03 정성조사에서 "
            "재보험 ex-cat 컴바인드레이쇼가 2분기 연속 소폭 악화"
            "(+130~160bp YoY)한 것이 확인돼 음수로 반영. "
            "demand_sensitivity_pct=0.20 - 보험 수요는 경기민감도가 낮다"
            "(CLAUDE.md 업종앵커표 '기업용 필수 계약기반' 버킷과 같은 수준, "
            "PGR·BRO와 정합적)."
        ),
        model_used="two_stage",
        model_choice_reason=(
            "기존 ledger(2026-08-03)와 동일하게 two_stage를 유지한다 - 매출 "
            "CAGR이 default_terminal_growth를 크게 웃도는 성장 국면이고, "
            "보험 사이클상 현 수준의 인수이익률이 영구히 지속된다고 보기 "
            "어려워 수렴 경로를 명시적으로 모형화하는 편이 맞다. 통제 설계상 "
            "모델을 바꾸지 않는다(바꾸면 시총·엔진버전 효과와 섞인다)."
        ),
        falsification_conditions=(
            "(1) 재보험 부문 ex-cat 컴바인드레이쇼가 세 분기 연속 전년比 "
            "악화되면 - 직전 정성 심층조사가 지목한 유일한 실질 악화 신호가 "
            "추세로 확정되는 것이므로 재검토. (2) 단일 대재해(허리케인·산불 "
            "등)로 분기 세전손실이 발생하면 - 이 엔진의 평활화된 FCF는 "
            "대재해 리스크를 전혀 반영하지 못한다는 알려진 한계가 실현되는 "
            "경우다. (3) `insurer_cross_check`의 지속가능성장률(ROE x 유보율)과 "
            "Realistic Growth 괴리가 5%p를 넘으면 - FCF-DCF가 보험 플로트 "
            "성장을 유기적 성장으로 착각하고 있다는 신호(v3.13 ACGL 핵심노트가 "
            "경고한 바로 그 지점). (4) P/B가 2.0배를 넘으면 - 직전 조사 "
            "시점 1.46배는 '정상범위'로 평가됐으나, 시장이 구조적 우위를 이미 "
            "재평가한 상태라면 저평가 근거가 약해진다(PGR 4.14배 사례)."
        ),
        price_at_analysis=PRICE,
        currency="USD",
        is_insurer=True,
        net_income_by_year=NET_INCOME,
        shareholders_equity_by_year=SHAREHOLDERS_EQUITY,
        dividends_paid_by_year=DIVIDENDS_PAID,
        sbc_by_year=SBC,
        data_sources=[
            "ledger/ACGL_2026-08-03.json (재무 시계열·주관적 입력 승계)",
            "SEC 10-Q (2026-07-30 표지 발행주식수 341,229,126주)",
            "SEC XBRL companyfacts (CIK 0000947484, provenance/PIT 조회 2026-09-05)",
            "Alpha Vantage GLOBAL_QUOTE (latestDay 2026-09-04, $98.10)",
            "2026-08-03 S등급 정성 심층조사(준비금 적정성·BVPS +22.6%·재보험 "
            "ex-cat 컴바인드레이쇼 악화·대재해 리스크 미반영) - CLAUDE.md 기록",
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
          f"주식수 {SHARES_OUT:,.0f})   [기존 $34.14B]")
    print(f"DRS            : {result['drs']['score']:.2f}   r={d['r']*100:.2f}%  "
          f"g_term={d['g_terminal']*100:.2f}%   [기존 48.00]")
    print(f"Lynch 유형     : {result['lynch']['used']}  "
          f"cap={g['breakdown']['cap_applied']}")
    print(f"Realistic Growth: {g['realistic_growth']*100:.2f}%   [기존 15.74%]")
    print(f"Implied Growth : {ig['value']*100:.2f}%  ({ig['model_used']}) "
          f"[single {ig['models']['single_stage']*100:.2f}% / "
          f"two {ig['models']['two_stage']*100:.2f}%, "
          f"괴리 {ig['models']['divergence']*100:.2f}%p]   [기존 -8.65%]")
    print(f"Expectation Gap: {result['expectation_gap']*100:+.2f}%p  "
          f"-> {result['judgment']} ({result['judgment_grade']})   "
          f"[기존 +24.38%p S]")
    print(f"RAR            : {result['rar']:+.4f}")
    print(f"Confidence     : {result['confidence']['final']}/100")
    sc = result.get("sensitivity_check") or {}
    print(f"강건성점검     : flip={sc.get('judgment_flipped')}")
    icc = result.get("insurer_cross_check") or {}
    if icc:
        print(f"보험 교차검증  : 지속가능성장률 "
              f"{(icc.get('sustainable_growth') or 0)*100:.2f}%  "
              f"P/B {icc.get('price_to_book')}  "
              f"괴리경고={bool(icc.get('warning'))}")
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
