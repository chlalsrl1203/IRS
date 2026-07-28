"""
Progressive Corporation(PGR) 정식 분석 - 2026-07-28.

경위: 2026-07-26 스크리닝 통과 후보. 비큐(ad-hoc) 분석(BKNG/PDD/TCOM과
동일 범주). 정식분석 전부터 "보험업 OCF는 float(플로트) 증가가 섞여 있어
일반기업의 FCF와 다르다"는 방법론 우려로 별도 플래그해뒀던 종목이다.

⚠️ **보험업 FCF-DCF 적용의 근본적 한계 - ACGL 선례 대조**:
같은 손해보험업종인 ACGL(Arch Capital, v3.13 당시 손배선 분석, ledger 없음)의
핵심노트에 이미 이 문제가 명문화돼 있다: "Gap+31.44%p/RAR3.003은 FCF-DCF를
자본집약적 보험업에 적용한 데서 오는 과장일 가능성 높음 - 지속가능성장률
(ROE x 유보율≈10.1%) 및 P/B(1.46x, 정상범위) 교차검증은 훨씬 절제된 저평가를
시사. 방향은 저평가가 맞으나 크기는 할인해석 필요."
왜 문제가 되는가: 보험사의 OCF = 보험료 수취(선불) - 보험금 지급(후불)이라
플로트(float)가 성장하는 동안은 OCF가 회계이익보다 구조적으로 크게 잡힌다.
이 '초과분'은 주주에게 배당 가능한 진짜 잉여현금이 아니라 준비금(reserve)
부채와 쌍을 이루는 부채성 자금이다 - 성장기 보험사에서 FCF-DCF가 내재가치를
체계적으로 과대평가하는 구조적 이유다. pipeline.py는 이를 보정하는 별도
기능이 없다(v3.19~v3.21 어디에도 보험업 FCF 조정 로직 없음 - 미해결 항목으로
CLAUDE.md에 별도 기록 예정).

**대응**: 표준 파이프라인은 그대로 돌려 트래커 비교가능성을 유지하되, ACGL과
동일한 교차검증(지속가능성장률=ROE x 유보율, P/B)을 병행 계산해 병기한다.
PGR은 특히 언더라이팅 사이클 변동성이 극심해(순이익 2022년 7.22억달러 저점 →
2025년 113.08억달러 고점, 15.7배) 단일 연도 ROE는 왜곡이 크므로 **5개년
평균**(2021~2025)을 사용한다.

**2026-07-28 업데이트(v3.22)**: 이 교차검증은 원래 이 스크립트에 별도 함수로
손계산했으나, 실증사례가 2건(ACGL/PGR) 쌓여 `pipeline.py`에
`AnalysisInputs.is_insurer` 플래그로 배선됐다(`net_income_by_year`/
`shareholders_equity_by_year`/`dividends_paid_by_year` 필수). 아래 수치는
이제 파이프라인이 자동 계산한다 - 재계산해도 손계산과 동일함을 확인함:

  ROE(5y 평균, 기말자기자본 기준) ≈ 22.52%
  배당성향(2023~2025 합산 배당/순이익) ≈ 16.17% -> 유보율 ≈ 83.83%
  지속가능성장률 = ROE x 유보율 ≈ 18.88%
  P/B = 시가총액 $125.44B / 자기자본 $30.32B ≈ **4.14배**

ACGL(P/B 1.46x, '정상범위')과 결정적으로 다른 지점: PGR의 P/B 4.14배는 이미
상당히 높다. 2026-05 S&P Global 확인 - PGR이 1942년 이후 처음으로 State
Farm을 제치고 미국 1위 개인용 자동차보험사가 됐다(직전 12개월 기준). 이
구조적 우위(텔레매틱스 기반 정밀요율산정)를 시장이 이미 상당폭 반영한
결과로 해석되며, ACGL과 달리 "정상범위 P/B가 저평가를 뒷받침"하는 논리를
PGR에는 그대로 적용하기 어렵다. 즉 **판정 방향 자체도 ACGL보다 신뢰도를
낮춰서 볼 것**.

원자료: 전부 SEC EDGAR as-filed 10-K에서 직접 추출(2026-07-28 조회, 11개년
2015~2025). 보험업은 별도 '영업이익' 라인이 없어 세전이익(income before
income taxes)을 operating_income 대용으로 사용(margin_volatility 산출용,
근사치임을 명시).
  FY2025 10-K(0000080661-26-000086) R3/R4/R7
  FY2022 10-K(0000080661-23-000006) R3/R4/R7
  FY2019 10-K(0000080661-20-000006) R2/R7
  FY2017 10-K(0000080661-18-000011) R2/R7
  FY2024 10-K(0000080661-25-000007) R4 (2023년 자기자본)
시가총액: stockanalysis.com 2026-07-27 종가 기준 $125.44B.

실행: python3 scripts/analyze_pgr_2026_07_28.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.pipeline import AnalysisInputs, run_analysis, save_ledger

M = 1_000_000

# ── SEC EDGAR as-filed 실측 (단위: USD, 원 단위) ────────────────────────
# operating_income_by_year는 보험업 특성상 세전이익(income before income taxes)을 대용.
REVENUE = {
    2015: 20853.8 * M, 2016: 23441.4 * M, 2017: 26839.0 * M,
    2018: 31979.0 * M, 2019: 39022.3 * M, 2020: 42658.1 * M,
    2021: 47702.0 * M, 2022: 49610.7 * M, 2023: 62109 * M,
    2024: 75372 * M, 2025: 87671 * M,
}
OPERATING_INCOME = {  # = income before income taxes (보험업 근사)
    2015: 1911.6 * M, 2016: 1470.7 * M, 2017: 2138.9 * M,
    2018: 3163.6 * M, 2019: 5160.3 * M, 2020: 7173.2 * M,
    2021: 4210.0 * M, 2022: 922.1 * M, 2023: 4904 * M,
    2024: 10713 * M, 2025: 14223 * M,
}
OPERATING_CASHFLOW = {
    2015: 2292.9 * M, 2016: 2732.7 * M, 2017: 3756.8 * M,
    2018: 6284.8 * M, 2019: 6261.6 * M, 2020: 6905.6 * M,
    2021: 7761.7 * M, 2022: 6848.8 * M, 2023: 10643 * M,
    2024: 15119 * M, 2025: 17548 * M,
}
CAPEX = {
    2015: 130.7 * M, 2016: 215.0 * M, 2017: 155.7 * M,
    2018: 266.0 * M, 2019: 363.5 * M, 2020: 223.5 * M,
    2021: 243.5 * M, 2022: 292.0 * M, 2023: 252 * M,
    2024: 285 * M, 2025: 348 * M,
}

# 순이익・자기자본・배당 (v3.22: is_insurer=True 경로로 pipeline이 자동 교차검증)
NET_INCOME_5Y = {2021: 3350.9 * M, 2022: 721.5 * M, 2023: 3903 * M, 2024: 8480 * M, 2025: 11308 * M}
EQUITY_5Y = {2021: 18231.6 * M, 2022: 15891.0 * M, 2023: 20277.0 * M, 2024: 25591.0 * M, 2025: 30323.0 * M}
DIVIDENDS_3Y = {2023: (234 + 43) * M, 2024: (674 + 8) * M, 2025: (2871 + 0) * M}  # 보통주+우선주

# 재무상태표 (FY2025 10-K R4, 2025-12-31 기준)
CASH = 125.0 * M          # 보험업은 투자포트폴리오(9.74B)가 준비금과 짝이라 순부채 상쇄에서 제외
LONG_TERM_DEBT = 6897.0 * M
NET_DEBT = LONG_TERM_DEBT - CASH

DA_2025 = 313.0 * M        # 감가상각(고정자산) - 채권 프리미엄상각 등 투자관련 항목은 제외
EBITDA = OPERATING_INCOME[2025] + DA_2025   # 세전이익 기준 근사 EBITDA(보험업 관행 아님, 명시)

MARKET_CAP = 125.44e9
RF = 0.0447


def build_inputs() -> AnalysisInputs:
    return AnalysisInputs(
        ticker="PGR",
        company_name="The Progressive Corporation",
        revenue_by_year=REVENUE,
        operating_income_by_year=OPERATING_INCOME,
        operating_cashflow_by_year=OPERATING_CASHFLOW,
        capex_by_year=CAPEX,
        market_cap=MARKET_CAP,
        net_debt=NET_DEBT,
        ebitda=EBITDA,
        risk_free_rate=RF,

        is_insurer=True,
        net_income_by_year=NET_INCOME_5Y,
        shareholders_equity_by_year=EQUITY_5Y,
        dividends_paid_by_year=DIVIDENDS_3Y,

        competitor_threat_weights=[0.35, 0.30, 0.20],
        market_share_trend_pp_per_year=1.0,
        active_antitrust_or_regulatory_case=False,
        demand_sensitivity_pct=0.15,
        subjective_input_basis=(
            "State Farm 0.35(상호회사, 오랫동안 업계 1위였던 최대 스케일 - "
            "2026-05 S&P Global 확인상 PGR에 직전 12개월 기준 1위를 처음 "
            "내줬으나 여전히 최대 경쟁자), GEICO/Berkshire 0.30(공격적 광고・"
            "가격경쟁력), Allstate 0.20(텔레매틱스 등 데이터기반 요율산정에서 "
            "PGR과 유사 전략 추구). 셋 다 [추정치]. "
            "market_share_trend=+1.0pp: 2026-05 S&P Global 보도로 확인된 "
            "명확한 근거 - PGR이 1942년 이후 최초로 State Farm을 제치고 "
            "직전 12개월 기준 미국 1위 개인용 자동차보험사가 됐다(2025년말 "
            "기준 시장점유율 약 17%, DPW 기준 672억달러). "
            "active_antitrust_or_regulatory_case=False: 2026-07 WebSearch로 "
            "확인한 결과 반독점/경쟁당국의 공식 조사・제재는 발견되지 않았다"
            "(BKNG/PDD/TCOM과 대조적). 총손해액 산정・PIP・UM/UIM 관련 소비자 "
            "집단소송이 다수 진행 중이나(2026-04 일리노이 연방법원 집단소송 "
            "인증 기각 등) 이는 대형 손보사의 통상적 소송 리스크이지 반독점・"
            "규제기관의 시장구조적 조사가 아니라 False로 유지. "
            "demand_sensitivity=0.15: 자동차보험은 대부분 주(state)에서 법적 "
            "의무가입이라 재량소비 성격이 약하다 - 실제로 FY2020(코로나) "
            "매출이 오히려 증가했다(BKNG/TCOM과 정반대). 경기침체기 신차판매 "
            "둔화・보장등급 하향 정도의 완만한 민감도만 반영해 이 프로젝트 "
            "최저권으로 설정[추정치]."
        ),

        model_used="two_stage",
        model_choice_reason=(
            "PGR의 세전이익은 언더라이팅 사이클로 극심하게 진동한다(2022년 "
            "9.22억달러 저점 -> 2025년 142.23억달러 고점, 15.4배) - 현재는 "
            "사이클 고점 부근으로 판단되며 이 마진이 무한히 지속된다고 "
            "가정하는 single_stage보다, 일정 기간 후 정상화(terminal)를 "
            "명시적으로 모델링하는 two_stage가 보수적이다. 첫 정식분석이라 "
            "대조할 과거 기록이 없다 - 실제 괴리는 divergence_warning으로 "
            "확인. ⚠️ **다만 이 모델선택 논의 자체가 보험업에는 부차적**이다 - "
            "아래 insurer_cross_check()가 보여주듯 FCF-DCF 프레임 자체가 "
            "보험업 밸류에이션에 구조적으로 부적합할 수 있어(ACGL 선례), "
            "Gap/RAR 결과는 방향성 참고자료로만 쓸 것."
        ),

        data_sources=[
            "SEC EDGAR 10-K FY2025(0000080661-26-000086) R3/R4/R7, as-filed, 2026-07-28 조회",
            "SEC EDGAR 10-K FY2022(0000080661-23-000006) R3/R4/R7 (FY2020~2022)",
            "SEC EDGAR 10-K FY2019(0000080661-20-000006) R2/R7 (FY2018~2019)",
            "SEC EDGAR 10-K FY2017(0000080661-18-000011) R2/R7 (FY2015~2017)",
            "SEC EDGAR 10-K FY2024(0000080661-25-000007) R4 (FY2023 자기자본)",
            "stockanalysis.com 시가총액 $125.44B (2026-07-27 종가)",
            "WebSearch: PGR 1위 등극(S&P Global 2026-05), 반독점/규제조사 여부 확인(2026-07)",
            "Notion 트래커 ACGL 핵심노트(2026-07-18, v3.13) - 보험업 FCF-DCF 방법론 우려 선례",
        ],
    )


def main():
    result = run_analysis(build_inputs())
    d, g = result["derived"], result["growth"]
    models = result["implied_growth"]["models"]
    cross = result["insurer_cross_check"]

    print("=" * 100)
    print(f"PGR 정식 분석 결과 ({result['meta']['analyzed_at'][:10]}, 엔진 {result['meta']['engine_version']})")
    print("=" * 100)
    print(f"  CAGR 기준연도    : {d['cagr_5y_base_year']}년 ({d['cagr_5y_span']}년 구간, override 미사용)")
    rev_10y_str = "N/A" if d['revenue_cagr_10y'] is None else f"{d['revenue_cagr_10y']*100:.2f}%"
    print(f"  매출 CAGR        : 3y {d['revenue_cagr_3y']*100:.2f}% / "
          f"{d['cagr_5y_span']}y {d['revenue_cagr_5y']*100:.2f}% / 10y {rev_10y_str}")
    print(f"  FCF CAGR         : {d['fcf_cagr_5y']*100:.2f}%   (FCF0 {d['fcf0']/1e9:.3f}B)")
    print(f"  최악 YoY 매출    : {d['worst_yoy_revenue_growth']*100:.2f}% ({d['worst_yoy_year']}년)")
    print(f"  순부채/EBITDA(근사): {d['net_debt_to_ebitda']:.3f}배")
    print()
    print(f"  DRS              : {result['drs']['score']:.2f}")
    for k, v in result["drs"]["components"].items():
        print(f"      {k:24} {v:5.2f}")
    print(f"  Lynch 유형       : {result['lynch']['used']}")
    print(f"  구조적 할인      : {g['structural_discount_pct']*100:.2f}%")
    print(f"  Realistic Growth : {g['realistic_growth']*100:.2f}%")
    ss_str = "N/A" if models['single_stage'] is None else f"{models['single_stage']*100:.2f}%"
    ts_str = "N/A" if models['two_stage'] is None else f"{models['two_stage']*100:.2f}%"
    print(f"  Implied Growth   : single_stage {ss_str} / two_stage {ts_str} "
          f"-> 채택 {result['implied_growth']['value']*100:.2f}% ({result['implied_growth']['model_used']})")
    if models.get("divergence") is not None:
        print(f"  모델 괴리        : {models['divergence']*100:.2f}%p")
    print(f"  Expectation Gap  : {result['expectation_gap']*100:+.2f}%p")
    print(f"  RAR              : {result['rar']:+.4f}")
    print(f"  강건성점검 flip  : {result['sensitivity_check'].get('judgment_flipped')}")
    print(f"  Confidence       : {result['confidence']['final']}/100")
    print(f"  ** 판정(엔진, 참고용) : {result['judgment']} **")
    print()
    print("  ── 보험업 교차검증(v3.22 is_insurer 자동배선, ACGL 선례와 동일 방법론) ──")
    print(f"  5y 평균 ROE          : {cross['avg_roe']*100:.2f}%  (사용연도 {cross['roe_years_used']})")
    print(f"  배당성향(3y 합산)    : {cross['payout_ratio']*100:.2f}%  (유보율 {cross['retention_ratio']*100:.2f}%)")
    print(f"  지속가능성장률        : {cross['sustainable_growth']*100:.2f}%")
    print(f"  P/B                  : {cross['price_to_book']:.2f}배  (ACGL 1.46배 '정상범위'와 대조)")
    print()
    if result["data_limitations"]:
        print("  데이터 한계·경고:")
        for x in result["data_limitations"]:
            print(f"    - {x}")

    path = save_ledger(result)
    print(f"\n  ledger 저장: {path}")
    return result, cross


if __name__ == "__main__":
    main()
