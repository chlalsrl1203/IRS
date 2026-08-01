"""
Arch Capital Group(ACGL) 재분석 - 2026-08-01 (v3.22 is_insurer 경로).

경위: "지금까지 조사한 모든 종목 매수 순위" 요청에 대응해 트래커 전체를
훑던 중, ACGL이 **원 데이터(raw) 기준 RAR 3.003으로 프로젝트 전체 1위**
(PDD +2.4757보다도 높음)로 나온다는 사실을 확인했다. 그런데 이 값은
v3.13(2026-07-18) 당시 산출된 것으로, **PGR(analyze_pgr_2026_07_28.py)
스크립트 자체가 명시한 선례**다: "ACGL(v3.13 당시 손배선 분석, ledger 없음)의
핵심노트에 이미 이 문제가 명문화돼 있다 - Gap+31.44%p/RAR3.003은 FCF-DCF를
자본집약적 보험업에 적용한 데서 오는 과장일 가능성 높음."

즉 ACGL의 RAR 3.003은 **이미 이 프로젝트가 스스로 신뢰하지 않는다고 기록해둔
값**인데, 정작 그 문제를 해결한 v3.22 `is_insurer` 경로(PGR에서 실증됨)로
ACGL 본인은 아직 재분석된 적이 없다. ledger도 없어 재현조차 불가능하다.
"매수 순위"에 원 RAR 3.003을 그대로 넣으면 이 프로젝트가 스스로 경고한
왜곡을 다시 반복하는 것이므로, 순위를 매기기 전에 먼저 고친다.

**보험업 FCF-DCF 문제**(PGR 스크립트와 동일 - 자세한 설명은 그쪽 참고):
보험사 OCF는 플로트(선수보험료-후지급보험금) 증가를 포함해 회계이익보다
구조적으로 부풀려진다. is_insurer=True 경로는 ROE x 유보율(지속가능성장률)과
P/B를 자동 병기해 FCF-DCF 결과를 교차검증한다.

**ACGL 실측 결과(v3.22 자동계산)**:
  5y 평균 ROE(2021~2025) ≈ 계산결과 참고(아래 실행)
  배당성향(2023~2025 합산) - Arch는 정기배당이 사실상 없다(2023년 보통주
  배당 $0, 2025년 $7M) - 2024년 $1,866M는 특별배당으로 추정. 유보율이
  매우 높게 나올 것이다.
  P/B = 시가총액 $34.14B / 자기자본 $24.21B ≈ 1.41배 (직접계산, 아래
  cross_check와 대조)
  -> **v3.13 핵심노트가 언급한 P/B 1.46배(정상범위)와 거의 일치** - 이번
  재분석이 과거 손계산을 재확인하는 셈이다.

⚠️ **2026 반영 사항 - 재보험 소프트사이클**: WebSearch로 확인(2026-07-29
Q2 실적발표) - 재보험 시장이 2026년 초 갱신에서 가격 10~20% 하락하는
'매수자 우위' 국면으로 전환, Fitch가 업종 전망을 'deteriorating'으로
하향. 재보험 부문 순보험료가 경쟁 심화·고객 리스크 자체보유 확대로
전년比 -10%. CEO "시장점유율을 좇지 않겠다"(가격규율 유지 방침).
이는 v3.13 분석 시점(2026-07-18)에는 부분적으로만 반영됐을 시황 변화라
market_share_trend를 소폭 음수로 조정한다.

원자료: 전부 SEC EDGAR as-filed 10-K에서 직접 추출(2026-08-01 조회, 11개년
2015~2025, PGR과 동일한 재무제표 구조).
  FY2025 10-K(0000947484-26-000017) R3/R5/R8
  FY2022 10-K(0000947484-23-000015) R3/R5/R8 (FY2020~2022)
  FY2024 10-K(0000947484-25-000017) R3 (FY2023 자기자본)
  FY2019 10-K(0000947484-20-000012) R4/R7 (FY2017~2019)
  FY2017 10-K(0000947484-18-000012) R4/R7 (FY2015~2016)
  ⚠️FY2017 OCF값이 두 filing에서 소폭 다르다(FY2017 10-K 1,112,617천달러
  vs FY2019 10-K 1,094,878천달러) - 후자(더 최근 filing, 잠재적 재분류 반영)를
  채택했다. capex는 두 filing에서 정확히 일치(22,841천달러)해 문제 없음.
시가총액: stockanalysis.com 2026-07-31 조회 $34.14B(주가 $100.53, YoY +5.8%
- **이 프로젝트의 다른 후보들과 달리 ACGL은 하락주가 아니라 상승주**다.
큐 기반 체계적 분석에서 발굴됐지 스크리닝/공포과잉 서사와 무관하다).

실행: python3 scripts/analyze_acgl_2026_08_01.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.pipeline import AnalysisInputs, run_analysis, save_ledger

M = 1_000_000

# ── SEC EDGAR as-filed 실측 (단위: USD, 원 단위) ────────────────────────
# operating_income_by_year = 세전이익(income before income taxes[and operating
# affiliates]) - 보험업 특성상 별도 '영업이익' 라인이 없어 PGR과 동일하게 대용.
REVENUE = {
    2015: 3936.590 * M, 2016: 4463.556 * M, 2017: 5627.375 * M,
    2018: 5450.568 * M, 2019: 6928.200 * M, 2020: 8508.509 * M,
    2021: 9249.980 * M, 2022: 9614.808 * M, 2023: 13634 * M,
    2024: 17440 * M, 2025: 19929 * M,
}
OPERATING_INCOME = {
    2015: 567.194 * M, 2016: 855.552 * M, 2017: 757.277 * M,
    2018: 841.772 * M, 2019: 1849.110 * M, 2020: 1560.783 * M,
    2021: 2103.351 * M, 2022: 1488.493 * M, 2023: 3385 * M,
    2024: 4474 * M, 2025: 4979 * M,
}
OPERATING_CASHFLOW = {
    2015: 997.906 * M, 2016: 1396.644 * M, 2017: 1094.878 * M,
    2018: 1559.322 * M, 2019: 2048.459 * M, 2020: 2886.505 * M,
    2021: 3427.555 * M, 2022: 3815.227 * M, 2023: 5749 * M,
    2024: 6673 * M, 2025: 6172 * M,
}
CAPEX = {
    2015: 15.736 * M, 2016: 15.303 * M, 2017: 22.841 * M,
    2018: 29.809 * M, 2019: 37.837 * M, 2020: 39.872 * M,
    2021: 41.394 * M, 2022: 51.672 * M, 2023: 52 * M,
    2024: 51 * M, 2025: 44 * M,
}

# 순이익・자기자본・배당 (v3.22: is_insurer=True 경로로 pipeline이 자동 교차검증)
NET_INCOME_5Y = {2021: 2239.462 * M, 2022: 1482.423 * M, 2023: 4442 * M,
                 2024: 4312 * M, 2025: 4399 * M}
EQUITY_5Y = {2021: 13545.896 * M, 2022: 12910.073 * M, 2023: 18353 * M,
             2024: 20820 * M, 2025: 24206 * M}
# 보통주+우선주 배당 합산. Arch는 정기 보통주배당이 사실상 없음(2023 $0,
# 2025 $7M) - 2024년 $1,866M는 특별배당으로 추정(정기 배당정책 변경 근거
# 없음, WebSearch로 별도 공시 확인 못함 - data_limitations에 명시).
DIVIDENDS_3Y = {2023: (0 + 40) * M, 2024: (1866 + 40) * M, 2025: (7 + 40) * M}

# 재무상태표 (FY2025 10-K R3, 2025-12-31 기준)
CASH = 993.0 * M           # 보험업은 투자포트폴리오($46.5B)가 준비금과 짝이라 순부채 상쇄에서 제외(PGR과 동일 처리)
SENIOR_NOTES = 2729.0 * M
NET_DEBT = SENIOR_NOTES - CASH

DA_2025 = 193.0 * M          # 무형자산상각(고정자산 감가상각 별도 라인 없음 - PGR과 다른 점, 근사치)
EBITDA = OPERATING_INCOME[2025] + DA_2025

MARKET_CAP = 34.14e9
RF = 0.0447


def build_inputs() -> AnalysisInputs:
    return AnalysisInputs(
        ticker="ACGL",
        company_name="Arch Capital Group Ltd.",
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

        competitor_threat_weights=[0.25, 0.20, 0.15],
        market_share_trend_pp_per_year=-1.5,
        active_antitrust_or_regulatory_case=False,
        demand_sensitivity_pct=0.20,
        subjective_input_basis=(
            "Berkshire Hathaway Re/Munich Re/Swiss Re 등 초대형 재보험사 "
            "0.25(막대한 자본력으로 가격경쟁 주도 가능), RenaissanceRe/Everest "
            "Re 등 전문 재보험사 0.20(유사 니치 전략 경쟁), Chubb 등 종합 "
            "손해보험사 0.15(원수보험 부문 경쟁). 전부 [추정치]. "
            "market_share_trend=-1.5pp: 2026-07-29 Q2 실적발표(WebSearch "
            "확인)에서 재보험 부문 순보험료가 경쟁심화・고객 리스크자체보유"
            "확대로 전년比 -10%, 2026년초 갱신 가격이 10~20% 하락하는 "
            "'매수자 우위' 국면 전환, Fitch가 업종전망 'deteriorating'으로 "
            "하향. 다만 CEO가 '시장점유율을 좇지 않겠다'며 가격규율을 "
            "유지한다고 명시(재무건전성 우려가 아니라 선택적 위축) - PGR"
            "(+1.0pp, 업계 1위 등극)과 정반대 국면이라 이 프로젝트 보험업 "
            "2건 중 가장 음수로 설정[추정치]. "
            "active_antitrust_or_regulatory_case=False: 2026-08 WebSearch로 "
            "확인한 결과 반독점/규제기관의 시장구조적 조사는 발견되지 않음. "
            "demand_sensitivity=0.20: 특수보험・재보험은 원수보험(자동차 "
            "의무가입)보다는 경기민감도가 있으나(대재해 손해율 변동이 더 "
            "큰 변수) 여전히 낮은 편 - PGR(0.15)보다 소폭 높게 설정[추정치]."
        ),

        model_used="two_stage",
        model_choice_reason=(
            "ACGL 세전이익도 PGR과 유사하게 언더라이팅・대재해 사이클로 "
            "진동한다(2022년 14.88억달러 저점 -> 2025년 49.79억달러 고점, "
            "3.3배). 마진이 현재 수준으로 무한 지속된다고 가정하는 "
            "single_stage보다 일정기간 후 정상화를 명시하는 two_stage가 "
            "보수적 - PGR과 동일 논리. ⚠️ **다만 이 모델선택 논의 자체가 "
            "보험업에는 부차적**이다 - 아래 insurer_cross_check가 보여주듯 "
            "FCF-DCF 프레임 자체가 보험업 밸류에이션에 구조적으로 부적합할 "
            "수 있어, Gap/RAR 결과는 방향성 참고자료로만 쓸 것(PGR과 동일 "
            "원칙). 재분석 대상이라 과거 기록(v3.13, RAR 3.003)이 있으나 "
            "그 기록 자체가 이번 재분석의 문제제기 대상이라 cross_check "
            "대조는 하지 않는다."
        ),

        data_sources=[
            "SEC EDGAR 10-K FY2025(0000947484-26-000017) R3/R5/R8, as-filed, 2026-08-01 조회",
            "SEC EDGAR 10-K FY2022(0000947484-23-000015) R3/R5/R8 (FY2020~2022)",
            "SEC EDGAR 10-K FY2024(0000947484-25-000017) R3 (FY2023 자기자본)",
            "SEC EDGAR 10-K FY2019(0000947484-20-000012) R4/R7 (FY2017~2019)",
            "SEC EDGAR 10-K FY2017(0000947484-18-000012) R4/R7 (FY2015~2016, FY2017 capex 대조검증)",
            "stockanalysis.com 시가총액 $34.14B(주가 $100.53, YoY+5.8%), 2026-07-31 조회",
            "WebSearch: ACGL 2026 Q2 실적(2026-07-29), 재보험 소프트사이클・가격하락・"
            "Fitch 업종전망 하향, 반독점/규제조사 여부 확인(2026-08)",
            "Notion 트래커 ACGL v3.13 원 기록(2026-07-18) - 이번 재분석의 문제제기 대상",
            "analyze_pgr_2026_07_28.py - is_insurer 경로 및 방법론 선례",
        ],
    )


def main():
    result = run_analysis(build_inputs())
    d, g = result["derived"], result["growth"]
    models = result["implied_growth"]["models"]
    cross = result["insurer_cross_check"]

    print("=" * 100)
    print(f"ACGL 재분석 결과 ({result['meta']['analyzed_at'][:10]}, 엔진 {result['meta']['engine_version']})")
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
    print(f"  RAR              : {result['rar']:+.4f}   (⚠️참고: v3.13 원기록 +3.003 - 이번 재분석 대상)")
    print(f"  강건성점검 flip  : {result['sensitivity_check'].get('judgment_flipped')}")
    print(f"  Confidence       : {result['confidence']['final']}/100")
    print(f"  ** 판정(엔진, 참고용) : {result['judgment']} **")
    print()
    print("  ── 보험업 교차검증(v3.22 is_insurer 자동배선, PGR과 동일 방법론) ──")
    print(f"  5y 평균 ROE          : {cross['avg_roe']*100:.2f}%  (사용연도 {cross['roe_years_used']})")
    print(f"  배당성향(3y 합산)    : {cross['payout_ratio']*100:.2f}%  (유보율 {cross['retention_ratio']*100:.2f}%)")
    print(f"  지속가능성장률        : {cross['sustainable_growth']*100:.2f}%")
    print(f"  P/B                  : {cross['price_to_book']:.2f}배  "
          f"(v3.13 핵심노트 언급값 1.46배와 대조)")
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
