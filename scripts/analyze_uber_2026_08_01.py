"""
Uber Technologies(UBER) 재분석 - 2026-08-01.

경위: "전체 종목 매수 순위" 마스터 랭킹을 만들다가, UBER가 이 트래커
전체에서 **가장 오래된 기록**(v3.9, 2026-07-08)이라는 사실을 확인했다.
당시엔 강건성점검(expectation_gap_sensitivity_check) 자체가 아직
엔진에 없었고(Notion 기록의 강건성점검 필드가 null), is_insurer/
capex_classification/cagr_base_year_override/v3.19 rar() 가드 등
이후 도입된 안전장치를 전혀 거치지 않았다. DRS 64.5(이 프로젝트
buy-tier 상위권)로 구조적 위험이 높다고 스스로 판정한 종목인데
검증 수준은 가장 낮았다 - 재분석 최우선순위로 선정.

세계 최대 차량공유/배달 플랫폼. 주가 YoY -21.4%, 52주 고점 대비 -35%.

**핵심 리스크 - Waymo 자율주행 확장**: WebSearch로 확인(2026-08) -
Waymo 주간 유료승차가 45만건으로 1년새 약 2배 증가, 샌프란시스코
특정 구역에서는 총거래액 기준 Lyft를 이미 추월해 점유율 25%+ 도달.
Uber는 자체 자율주행차 개발 대신 서드파티 AV 플랫폼(Waymo 포함)을
자사 앱에 통합하는 '유통 플랫폼' 전략으로 대응 중 - 위협이지만
동시에 잠재적 파트너십 구조이기도 하다는 점을 반영.

⚠️ **CAGR 기준연도 override 필요**: 기본 기준연도 FY2020(팬데믹 직격탄)
의 OCF가 -$2,745M로 적자라 FCF가 음수(-$3,361M) -> CAGR 시작값 음수
가드(v3.19)에 걸려 실행 거부. FY2022(FCF 첫 플러스전환 +$390M)를
기준연도로 override(3년 구간) - BKNG/MNDY와 동일 절차.

원자료: 전부 SEC EDGAR 10-K as-filed에서 직접 추출(2026-08-01 조회).
  FY2025 10-K(CIK 1543151, accession 0001543151-26-000015) R3/R5/R8
  FY2022 10-K(accession 0001543151-23-000010) R5/R8 (FY2020~2022)
시가총액: stockanalysis.com 2026-07-31 조회 $143.22B(주가 $70.36, YoY -21.4%).

실행: python3 scripts/analyze_uber_2026_08_01.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.pipeline import AnalysisInputs, run_analysis, save_ledger

M = 1_000_000

# ── SEC EDGAR as-filed 실측 (단위: USD, 원 단위) ────────────────────────
REVENUE = {
    2020: 11139 * M, 2021: 17455 * M, 2022: 31877 * M,
    2023: 37281 * M, 2024: 43978 * M, 2025: 52017 * M,
}
OPERATING_INCOME = {
    2020: -4863 * M, 2021: -3834 * M, 2022: -1832 * M,
    2023: 1110 * M, 2024: 2799 * M, 2025: 5565 * M,
}
OPERATING_CASHFLOW = {
    2020: -2745 * M, 2021: -445 * M, 2022: 642 * M,
    2023: 3585 * M, 2024: 7137 * M, 2025: 10099 * M,
}
CAPEX = {
    2020: 616 * M, 2021: 298 * M, 2022: 252 * M,
    2023: 223 * M, 2024: 242 * M, 2025: 336 * M,
}

# 재무상태표 (FY2025 10-K R3, 2025-12-31 기준)
CASH = 7105 * M
SHORT_TERM_INVESTMENTS = 528 * M
LONG_TERM_DEBT = 10521 * M          # 유동성 만기부채 별도라인 없음(사채 만기구조상)
NET_DEBT = LONG_TERM_DEBT - CASH - SHORT_TERM_INVESTMENTS

DA_2025 = 747 * M                    # 현금흐름표 조정항목 기준(손익계산서 719M과 소폭 차이 - ROU상각 등 포함범위 차이)
EBITDA = OPERATING_INCOME[2025] + DA_2025

MARKET_CAP = 143.22e9
RF = 0.0447


def build_inputs() -> AnalysisInputs:
    return AnalysisInputs(
        ticker="UBER",
        company_name="Uber Technologies, Inc.",
        revenue_by_year=REVENUE,
        operating_income_by_year=OPERATING_INCOME,
        operating_cashflow_by_year=OPERATING_CASHFLOW,
        capex_by_year=CAPEX,
        market_cap=MARKET_CAP,
        net_debt=NET_DEBT,
        ebitda=EBITDA,
        risk_free_rate=RF,

        # v3.23(2026-08-01 방법론 감사 Critical-1): SBC 병기 교차검증.
        # SEC 10-K R8 현금흐름표 "Stock-based compensation" FY2025 실측.
        sbc_by_year={2025: 1826 * M},

        cagr_base_year_override=2022,
        cagr_base_year_override_reason=(
            "기본 기준연도 FY2020(팬데믹 직격탄)의 OCF가 -$2,745M 적자라 "
            "FCF가 음수(-$3,361M) -> CAGR 시작값 음수 가드(v3.19)에 걸려 "
            "실행 거부. FY2022(FCF 첫 플러스전환 +$390M)를 기준연도로 "
            "삼아 3년 구간 CAGR을 산출한다."
        ),

        competitor_threat_weights=[0.30, 0.20, 0.15],
        market_share_trend_pp_per_year=-2.0,
        active_antitrust_or_regulatory_case=False,
        demand_sensitivity_pct=0.30,
        subjective_input_basis=(
            "Waymo(Alphabet) 0.30 - 2026-08 WebSearch 확인: 주간 유료승차 "
            "45만건으로 1년새 약 2배 증가, 샌프란시스코 특정구역 총거래액 "
            "기준 Lyft 추월해 점유율 25%+ 도달. 자체 운전자 비용구조가 "
            "없는 대형테크의 실측 확장이라 이 프로젝트 최대 가중치권. "
            "다만 Uber가 서드파티 AV를 자사 플랫폼에 통합하는 전략을 "
            "취하고 있어 순수 경쟁자가 아니라 잠재적 유통파트너이기도 "
            "함(위협도를 TTD의 Amazon DSP 0.40보다는 낮게 설정한 이유). "
            "Lyft 0.20(핵심 직접경쟁자, 미국 승차공유 2위). DoorDash 등 "
            "배달 전문업체 0.15(Uber Eats와 직접경쟁하나 승차공유는 "
            "겹치지 않아 부분적 위협). 전부 [추정치]. "
            "market_share_trend=-2.0pp: Waymo의 실측 점유율 급증(SF "
            "25%+, 0에서 시작)을 반영해 이 프로젝트 최대 음수권으로 설정"
            "[추정치] - 다만 이는 특정 도시(SF) 국지적 데이터라 전국 "
            "단위로 일반화하기엔 근거가 제한적임을 인지. "
            "active_antitrust_or_regulatory_case=False: 2026-08 "
            "WebSearch로 주요 반독점 조사는 확인 안 됨(다만 각국 "
            "긱워커 분류 소송·규제는 상시 존재 - 별도 사업모델 리스크로 "
            "data_limitations에 준하는 정성 리스크로만 인지). "
            "demand_sensitivity=0.30: 승차공유·배달은 재량소비 성격이 "
            "뚜렷해 경기침체시 이용빈도 영향을 받는다 - SE(재량소비 "
            "이커머스)와 유사한 수준으로 이 프로젝트 상위권[추정치]."
        ),

        model_used="two_stage",
        model_choice_reason=(
            "Uber는 FY2020~2022 영업손실에서 FY2023부터 흑자전환 후 "
            "매년 확대되는 궤적(2023년 $1.1B -> 2025년 $5.6B, 5배)의 "
            "명시적 고성장기다. 이 정상화 국면을 모델링하는 데 "
            "single_stage(현재 마진이 무한 지속된다고 가정)보다 "
            "two_stage가 이론적으로 더 부합한다고 판단 - 실행 후 "
            "모델괴리를 보고 재검토할 것(다른 종목들과 동일 절차). "
            "v3.9 원기록과는 엔진 버전 차이가 너무 커 직접 대조하지 "
            "않고 처음부터 다시 판단했다."
        ),

        data_sources=[
            "SEC EDGAR 10-K FY2025(0001543151-26-000015) R3/R5/R8, as-filed, 2026-08-01 조회",
            "SEC EDGAR 10-K FY2022(0001543151-23-000010) R5/R8 (FY2020~2022)",
            "stockanalysis.com 시가총액 $143.22B(주가 $70.36, YoY-21.4%), 2026-07-31 조회",
            "WebSearch: Waymo 로보택시 확장 현황(2026-08), Uber의 서드파티 AV 플랫폼 "
            "통합전략 확인",
        ],
    )


def main():
    result = run_analysis(build_inputs())
    d, g = result["derived"], result["growth"]
    models = result["implied_growth"]["models"]

    print("=" * 100)
    print(f"UBER 재분석 결과 ({result['meta']['analyzed_at'][:10]}, 엔진 {result['meta']['engine_version']})")
    print("=" * 100)
    print(f"  CAGR 기준연도    : {d['cagr_5y_base_year']}년 ({d['cagr_5y_span']}년 구간, override 사용)")
    rev_10y_str = "N/A" if d['revenue_cagr_10y'] is None else f"{d['revenue_cagr_10y']*100:.2f}%"
    print(f"  매출 CAGR        : 3y {d['revenue_cagr_3y']*100:.2f}% / "
          f"{d['cagr_5y_span']}y {d['revenue_cagr_5y']*100:.2f}% / 10y {rev_10y_str}")
    print(f"  FCF CAGR         : {d['fcf_cagr_5y']*100:.2f}%   (FCF0 {d['fcf0']/1e9:.3f}B)")
    print(f"  최악 YoY 매출    : {d['worst_yoy_revenue_growth']*100:.2f}% ({d['worst_yoy_year']}년)")
    print(f"  순부채/EBITDA    : {d['net_debt_to_ebitda']:.3f}배")
    print()
    print(f"  DRS              : {result['drs']['score']:.2f}   (v3.9 원기록: 64.50)")
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
    print(f"  Expectation Gap  : {result['expectation_gap']*100:+.2f}%p   (v3.9 원기록: +11.01%p)")
    print(f"  RAR              : {result['rar']:+.4f}   (v3.9 원기록: +0.558)")
    print(f"  강건성점검 flip  : {result['sensitivity_check'].get('judgment_flipped')}")
    print(f"  Confidence       : {result['confidence']['final']}/100")
    print(f"  ** 판정          : {result['judgment']} **")
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
