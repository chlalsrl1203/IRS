"""
Gen Digital(GEN) 정식 분석 - 2026-07-28.

경위: 2026-07-26 스크리닝 통과 후보(BRO와 동일 유형 - M&A주도 성장 우려로
사전 플래그). 비큐(ad-hoc) 분석. 사용자 확인(2026-07-28)을 거쳐 "무거운
주의사항과 함께 분석 진행"으로 방향을 확정하고 진행했다.

⚠️ **GEN은 BRO보다 훨씬 심한 사례 - 6년 안에 이질적 사건 3개가 겹친다**:
  (1) Broadcom 매각(2019-11, FY2020 중): Symantec의 Enterprise 보안사업을
      $10.7B에 매각하고 소비자 전용(NortonLifeLock)으로 축소. FY2020 OCF가
      **-$861M(음수)**로 나온 게 이 거래의 잔재로 추정됨(재무제표상 계속영업
      기준으로는 매출 자체는 FY2019~2021이 $2,456M→$2,551M로 완만해
      비교가능해 보이나 영업이익은 $158M→$896M로 5.7배 - 매각 후 비용구조
      재편 효과이지 유기적 마진개선이 아님). 다행히 기본 5년 기준연도가
      FY2021이라 이 음수 OCF 연도는 CAGR 계산에서 자동으로 비켜간다.
  (2) Avast 합병(2022-09 종결, FY2023 중 7개월 반영): FY2023 매출 $3,338M에
      Avast 매출이 부분기간 포함. 3년 CAGR의 기준연도(FY2023)가 바로 이
      해다.
  (3) MoneyLion 인수(FY2026 중 종결, 소비자 대출/핀테크 사업): FY2026 매출이
      $5,000M로 전년比 +27% 급증했으나, **세그먼트 공시로 직접 확인한 결과**
      (2026-05-07 Gen 실적발표, PRNewswire):
        Cyber Safety Platform(핵심 보안사업): $3,176M -> $3,339M, **+5.1%만
        성장**
        Trust-Based Solutions(MoneyLion 포함): $759M -> $1,661M, **+118.8%**
      즉 연결 매출성장 27%의 절대다수가 신규 인수한 핀테크/대출 사업의
      기계적 연결 효과이고, 핵심 사이버보안 사업의 유기적 성장은 5.1%에
      불과하다. **이는 BRO/(1)(2)와 성격이 다르다** - 단순 볼트온 M&A가
      아니라 완전히 다른 산업(소비자 대출)으로의 사업다각화라, 하나의
      FCF-DCF 틀로 밸류에이션하는 것 자체가 개념적으로 무리다(보험업
      PGR/ACGL 사례와 유사한 "프레임 자체가 안 맞을 수 있다" 문제).

**대응**: 3y/5y CAGR 수치 자체는 역설적으로 극단값으로 튀지 않는다(3y 14.4%,
5y 14.4%대 - TCOM처럼 눈에 띄는 이상치가 아니다). 이는 기준연도(FY2023)와
종료연도(FY2026) **양쪽 모두**에 인수 관련 단계상승이 끼어있어 통계적으로
서로 상쇄돼 보이기 때문이다 - 즉 "숫자가 정상으로 보인다"는 사실 자체가
안심할 근거가 아니라 오히려 위험신호다. 표준 파이프라인 CAGR만으로는 이
왜곡을 탐지할 수 없어 세그먼트 공시 교차검증이 필수였다. 추가로 회사 자체
가이던스(FY27 매출 $5,325~5,425M = **+6.5~8.5%**)가 과거 CAGR(14~17%)보다
훨씬 낮아, 회사 스스로도 FY26의 성장률이 지속가능하지 않다고 보고 있음을
시사한다 - PGR의 P/B처럼 이번에도 외부 교차검증치를 함께 제시한다.

원자료: 전부 SEC EDGAR as-filed 10-K에서 직접 추출(2026-07-28 조회, FY2021
~2026, 6개년 - Broadcom 매각 이후 계속영업 기준으로 비교가능한 구간만 사용).
  FY2026 10-K(0000849399-26-000017) R3/R5/R9 (FY2024~2026 + 재무상태표)
  FY2023 10-K(0000849399-23-000014) R5/R9 (FY2021~2023)
  FY2021 10-K(0000849399-21-000010) R4/R8 (FY2019~2021, 참고용 - Broadcom
    매각 직후 맥락 확인 목적, 분석 입력creening에는 FY2021만 사용)
세그먼트 공시: Gen Digital 2026-05-07 FY26 실적발표(PRNewswire) - Cyber
  Safety Platform vs Trust-Based Solutions 매출 분리, FY27 가이던스.
시가총액: stockanalysis.com 2026-07-27 종가 기준 $16.11B.

실행: python3 scripts/analyze_gen_2026_07_28.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.pipeline import AnalysisInputs, run_analysis, save_ledger

M = 1_000_000

# ── SEC EDGAR as-filed 실측 (단위: USD, 원 단위) ────────────────────────
# FY2021을 시작점으로 삼음(Broadcom 매각 이후 계속영업 기준 첫 온전한 해).
REVENUE = {
    2021: 2551 * M, 2022: 2796 * M, 2023: 3338 * M,   # FY23은 Avast 7개월 포함
    2024: 3800 * M, 2025: 3935 * M,
    2026: 5000 * M,   # MoneyLion 연결 - Cyber Safety만은 +5.1%(세그먼트 공시)
}
OPERATING_INCOME = {
    2021: 896 * M, 2022: 1005 * M, 2023: 1227 * M,
    2024: 1110 * M, 2025: 1610 * M, 2026: 2120 * M,
}
OPERATING_CASHFLOW = {
    2021: 706 * M, 2022: 974 * M, 2023: 757 * M,
    2024: 2064 * M, 2025: 1221 * M, 2026: 1545 * M,
}
CAPEX = {
    2021: 6 * M, 2022: 6 * M, 2023: 6 * M,
    2024: 20 * M, 2025: 15 * M, 2026: 22 * M,
}

# 세그먼트 공시 (pipeline 입력이 아니라 교차검증 텍스트용, 2026-05-07 실적발표)
CYBER_SAFETY_REVENUE = {2025: 3176 * M, 2026: 3339 * M}   # +5.1%(유기적에 가까움)
TRUST_BASED_REVENUE = {2025: 759 * M, 2026: 1661 * M}     # +118.8%(MoneyLion 연결효과)
FY27_GUIDANCE_GROWTH_RANGE = (0.065, 0.085)                # 회사 자체 가이던스

# 재무상태표 (FY2026 10-K R3, 2026-04-03 기준)
CASH = 411 * M
TOTAL_DEBT = 181 * M + 8015 * M   # 유동성 장기차입금 + 장기차입금
NET_DEBT = TOTAL_DEBT - CASH

DA_2026 = 493 * M          # 상각+감가상각 합계(인수 무형자산 상각 포함 - 보수적으로 그대로 사용)
EBITDA = OPERATING_INCOME[2026] + DA_2026

MARKET_CAP = 16.11e9
RF = 0.0447


def build_inputs() -> AnalysisInputs:
    return AnalysisInputs(
        ticker="GEN",
        company_name="Gen Digital Inc.",
        revenue_by_year=REVENUE,
        operating_income_by_year=OPERATING_INCOME,
        operating_cashflow_by_year=OPERATING_CASHFLOW,
        capex_by_year=CAPEX,
        market_cap=MARKET_CAP,
        net_debt=NET_DEBT,
        ebitda=EBITDA,
        risk_free_rate=RF,

        competitor_threat_weights=[0.35, 0.30],
        market_share_trend_pp_per_year=0.0,
        active_antitrust_or_regulatory_case=False,
        demand_sensitivity_pct=0.30,
        subjective_input_basis=(
            "McAfee 0.35(소비자용 백신・신원보호 번들에서 가장 직접적인 "
            "경쟁자, 유사한 구독모델), Windows Defender 등 OS내장 무료보안 "
            "0.30(유료 소비자백신 시장 자체를 구조적으로 잠식하는 위협 - "
            "Cyber Safety 세그먼트가 최근 1년 +5.1%에 그친 배경 중 하나로 "
            "추정[추정치]). 셋째 경쟁축(Trust-Based Solutions/MoneyLion의 "
            "핀테크・대출 경쟁자 - SoFi, Chime 등)은 완전히 다른 산업이라 "
            "이 3-가중치 프레임에 억지로 넣지 않고 별도 정성 리스크로만 "
            "취급했다. market_share_trend=0.0: Cyber Safety 세그먼트가 "
            "성숙・완만 성장 국면이라는 근거는 있으나 정량 점유율 추세 "
            "데이터가 없어 중립[추정치]. active_antitrust_or_regulatory_"
            "case=False: 2026-07 WebSearch로 확인 - 반독점/경쟁당국 조사는 "
            "발견되지 않았다(BKNG/PDD/TCOM과 대조적). 2025~2026년 로보콜 "
            "관련 TCPA 집단소송 합의금($9.95M, 2026-04 청구마감)이 있으나 "
            "이는 통신마케팅 규정 위반이지 반독점・경쟁 이슈가 아니다. "
            "demand_sensitivity=0.30: Cyber Safety 구독은 필수재에 가까운 "
            "성격(신원도용 우려로 해지율 낮음)이나, MoneyLion의 개인대출/"
            "선지급 사업은 경기・신용사이클에 훨씬 민감해 블렌드로 중간값 "
            "채택[추정치]."
        ),

        model_used="two_stage",
        model_choice_reason=(
            "회사 자체 FY27 가이던스가 매출성장 6.5~8.5%로 과거 3y/5y CAGR"
            "(14%대)보다 크게 낮다 - 이는 FY26의 27% 연결성장이 MoneyLion "
            "인수의 기계적 반영이며 지속 불가능함을 회사 스스로 사실상 "
            "인정하는 신호다. 명시적 감속 경로를 모델링하는 two_stage가 "
            "이 상황에 이론적으로 더 부합한다고 판단했다. 첫 정식분석이라 "
            "대조할 과거 기록이 없다. ⚠️ **다만 모델선택 자체가 이 종목의 "
            "핵심 쟁점이 아니다** - Realistic Growth 입력값인 3y/5y CAGR "
            "자체가 세그먼트 공시(Cyber Safety +5.1% vs Trust-Based "
            "+118.8%)와 대조하면 이질적 사업의 연결효과를 담고 있어, "
            "어느 모델을 쓰든 Gap/RAR은 참고용으로만 볼 것."
        ),

        data_sources=[
            "SEC EDGAR 10-K FY2026(0000849399-26-000017) R3/R5/R9, as-filed, 2026-07-28 조회",
            "SEC EDGAR 10-K FY2023(0000849399-23-000014) R5/R9 (FY2021~2023)",
            "SEC EDGAR 10-K FY2021(0000849399-21-000010) R4/R8 (FY2019~2021, 참고용)",
            "Gen Digital FY26 실적발표(2026-05-07, PRNewswire) - 세그먼트별 매출, FY27 가이던스",
            "stockanalysis.com 시가총액 $16.11B (2026-07-27 종가)",
            "WebSearch: GEN 반독점/규제조사 여부 확인(2026-07), TCPA 집단소송($9.95M) 확인",
        ],
    )


def main():
    result = run_analysis(build_inputs())
    d, g = result["derived"], result["growth"]
    models = result["implied_growth"]["models"]

    cyber_safety_growth = CYBER_SAFETY_REVENUE[2026] / CYBER_SAFETY_REVENUE[2025] - 1
    trust_based_growth = TRUST_BASED_REVENUE[2026] / TRUST_BASED_REVENUE[2025] - 1

    print("=" * 100)
    print(f"GEN 정식 분석 결과 ({result['meta']['analyzed_at'][:10]}, 엔진 {result['meta']['engine_version']})")
    print("=" * 100)
    print(f"  CAGR 기준연도    : {d['cagr_5y_base_year']}년 ({d['cagr_5y_span']}년 구간, override 미사용)")
    rev_10y_str = "N/A" if d['revenue_cagr_10y'] is None else f"{d['revenue_cagr_10y']*100:.2f}%"
    print(f"  매출 CAGR(연결)  : 3y {d['revenue_cagr_3y']*100:.2f}% / "
          f"{d['cagr_5y_span']}y {d['revenue_cagr_5y']*100:.2f}% / 10y {rev_10y_str}")
    print(f"  FCF CAGR(연결)   : {d['fcf_cagr_5y']*100:.2f}%   (FCF0 {d['fcf0']/1e9:.3f}B)")
    print(f"  최악 YoY 매출    : {d['worst_yoy_revenue_growth']*100:.2f}% ({d['worst_yoy_year']}년)")
    print(f"  순부채/EBITDA    : {d['net_debt_to_ebitda']:.3f}배 (레버리지 높은 편)")
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
    print("  ── 세그먼트 교차검증(핵심 사업 vs 인수사업 분리, 2026-05-07 실적발표) ──")
    print(f"  Cyber Safety(핵심보안) YoY   : {cyber_safety_growth*100:+.2f}%  <- 유기적 성장에 가까움")
    print(f"  Trust-Based(MoneyLion 등) YoY: {trust_based_growth*100:+.2f}%  <- 인수 연결효과")
    print(f"  회사 FY27 가이던스(연결)     : +{FY27_GUIDANCE_GROWTH_RANGE[0]*100:.1f}~{FY27_GUIDANCE_GROWTH_RANGE[1]*100:.1f}%  "
          f"<- 과거 CAGR({d['revenue_cagr_5y']*100:.1f}%)보다 훨씬 낮음")
    print()
    if result["data_limitations"]:
        print("  데이터 한계·경고:")
        for x in result["data_limitations"]:
            print(f"    - {x}")

    path = save_ledger(result)
    print(f"\n  ledger 저장: {path}")
    return result


if __name__ == "__main__":
    main()
