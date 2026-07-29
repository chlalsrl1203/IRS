"""
PTC Inc.(PTC) 정식 분석 - 2026-07-29.

경위: 공식 83개 큐의 47번째 종목(46번 Ansys는 2025-07-17 Synopsys에 $35B로
인수완료돼 더 이상 독립 상장사가 아니라 건너뜀 - 단독 밸류에이션 대상인
현재 시가총액 자체가 존재하지 않아 FTV/Atlas Copco/Halma/Experian과 동일
유형의 건너뜀).

PTC는 GWRE와 달리 관측구간(FY2017~2025) 내내 흑자를 유지한 꾸준한 성장
스토리다 - CAGR 가드나 기준연도 함정 이슈가 없다. CAD/PLM(제품수명주기관리)
소프트웨어의 '빅3'(PTC/Siemens/Dassault Systèmes) 중 하나로, ABI Research
경쟁력 평가에서 대형 제조업체 대상 PLM 부문 1위로 평가됐다.

원자료: 전부 SEC EDGAR as-filed 10-K에서 직접 추출(2026-07-29 조회, FY2017
~2025, 9개년, 회계연도는 매년 9월 30일 종료).
  FY2025 10-K(0001193125-25-291326) R2/R4/R7
  FY2022 10-K(0000950170-22-025211) R4/R7 (FY2020~2022)
  FY2019 10-K(0000857005-19-000040) R4/R7 (FY2017~2019)
시가총액: stockanalysis.com 2026-07-28 종가 기준 $14.73B.

실행: python3 scripts/analyze_ptc_2026_07_29.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.pipeline import AnalysisInputs, run_analysis, save_ledger

K = 1_000  # 원자료가 '천 달러' 단위

# ── SEC EDGAR as-filed 실측 (단위: USD, 원 단위) ────────────────────────
REVENUE = {
    2017: 1164039 * K, 2018: 1241824 * K, 2019: 1255631 * K,
    2020: 1458415 * K, 2021: 1807159 * K, 2022: 1933347 * K,
    2023: 2097053 * K, 2024: 2298472 * K, 2025: 2739226 * K,
}
OPERATING_INCOME = {
    2017: 41766 * K, 2018: 72613 * K, 2019: 63042 * K,
    2020: 210863 * K, 2021: 380748 * K, 2022: 447362 * K,
    2023: 458474 * K, 2024: 588062 * K, 2025: 982385 * K,
}
OPERATING_CASHFLOW = {
    2017: 135203 * K, 2018: 247752 * K, 2019: 285145 * K,
    2020: 233808 * K, 2021: 368809 * K, 2022: 435326 * K,
    2023: 610861 * K, 2024: 749984 * K, 2025: 867696 * K,
}
CAPEX = {
    2017: 25444 * K, 2018: 36041 * K, 2019: 64411 * K,
    2020: 20196 * K, 2021: 24713 * K, 2022: 19496 * K,
    2023: 23814 * K, 2024: 14378 * K, 2025: 11008 * K,
}

# 재무상태표 (FY2025 10-K R2, 2025-09-30 기준)
CASH = 184415 * K
SHORT_TERM_DEBT = 25000 * K
LONG_TERM_DEBT = 1172434 * K
NET_DEBT = (SHORT_TERM_DEBT + LONG_TERM_DEBT) - CASH   # 운용리스부채는 제외(BKNG 이후 관행)

DA_2025 = 102504 * K   # 감가상각+무형자산상각(사용권자산 상각 $32.9M은 제외)
EBITDA = OPERATING_INCOME[2025] + DA_2025

MARKET_CAP = 14.73e9
RF = 0.0447


def build_inputs() -> AnalysisInputs:
    return AnalysisInputs(
        ticker="PTC",
        company_name="PTC Inc.",
        revenue_by_year=REVENUE,
        operating_income_by_year=OPERATING_INCOME,
        operating_cashflow_by_year=OPERATING_CASHFLOW,
        capex_by_year=CAPEX,
        market_cap=MARKET_CAP,
        net_debt=NET_DEBT,
        ebitda=EBITDA,
        risk_free_rate=RF,

        competitor_threat_weights=[0.40, 0.35, 0.20],
        market_share_trend_pp_per_year=0.5,
        active_antitrust_or_regulatory_case=False,
        demand_sensitivity_pct=0.25,
        subjective_input_basis=(
            "Siemens Digital Industries Software 0.40(NX/Teamcenter, 가장 "
            "포괄적인 CAx 플랫폼 - 온프레미스・하이브리드・SaaS 전배포모델 "
            "지원), Dassault Systèmes 0.35(SolidWorks/CATIA/ENOVIA, 중견~대형 "
            "제조업 전반 강세), Autodesk 0.20(Fusion 360 등 일부 세그먼트 "
            "중첩). 셋 다 [추정치]. PTC/Siemens/Dassault를 CAD・PLM '빅3'로 "
            "보는 것이 업계 통설(2026-07 WebSearch). market_share_trend="
            "+0.5pp: 2026-07 ABI Research 평가에서 PTC가 대형 제조업체 대상 "
            "PLM 부문 경쟁력 1위로 평가돼 완만한 긍정 추세로 설정 - 다만 "
            "정량 점유율 시계열은 확보 못해 [추정치]. "
            "active_antitrust_or_regulatory_case=False: 2026-07 WebSearch로 "
            "확인 결과 반독점・경쟁당국의 현재 진행 중인 조사는 발견되지 "
            "않았다(2016년 中 관련 FCPA 조사・화해금 $28.2M은 종결된 "
            "과거건이라 반영하지 않음). demand_sensitivity=0.25: "
            "CAD・PLM 소프트웨어는 제조업 설비투자 사이클에 어느정도 연동되나"
            "(신규 시트 확장・도입 결정이 경기에 영향받음), 구독 매출 비중이 "
            "높아 완전한 경기민감 업종은 아니다 - GWRE(0.22)와 유사한 "
            "중간값[추정치]."
        ),

        model_used="two_stage",
        model_choice_reason=(
            "PTC는 관측구간(FY2017~2025) 내내 흑자를 유지하며 최근 3개년 "
            "영업이익이 매출성장보다 훨씬 빠르게 증가하는(FY24->FY25 매출 "
            "+19.2%, 영업이익 +67.1%) 마진확장 국면에 있다 - 명시적 성장기간 "
            "이후 정상화를 모델링하는 two_stage가 이 궤적에 이론적으로 더 "
            "부합한다고 판단했다. 첫 정식분석이라 대조할 과거 기록이 없다 - "
            "실제 괴리는 divergence_warning으로 확인하고, GWRE 사례처럼 "
            "3%p를 크게 넘으면 Lynch 자동분류 결과를 근거로 재검토할 것."
        ),

        data_sources=[
            "SEC EDGAR 10-K FY2025(0001193125-25-291326) R2/R4/R7, as-filed, 2026-07-29 조회",
            "SEC EDGAR 10-K FY2022(0000950170-22-025211) R4/R7 (FY2020~2022)",
            "SEC EDGAR 10-K FY2019(0000857005-19-000040) R4/R7 (FY2017~2019)",
            "stockanalysis.com 시가총액 $14.73B (2026-07-28 종가)",
            "WebSearch: PTC 경쟁구도(ABI Research MCAD/PLM 랭킹), 반독점/규제조사 여부 확인",
        ],
    )


def main():
    result = run_analysis(build_inputs())
    d, g = result["derived"], result["growth"]
    models = result["implied_growth"]["models"]

    print("=" * 100)
    print(f"PTC 정식 분석 결과 ({result['meta']['analyzed_at'][:10]}, 엔진 {result['meta']['engine_version']})")
    print("=" * 100)
    print(f"  CAGR 기준연도    : {d['cagr_5y_base_year']}년 ({d['cagr_5y_span']}년 구간, override 미사용)")
    rev_10y_str = "N/A" if d['revenue_cagr_10y'] is None else f"{d['revenue_cagr_10y']*100:.2f}%"
    print(f"  매출 CAGR        : 3y {d['revenue_cagr_3y']*100:.2f}% / "
          f"{d['cagr_5y_span']}y {d['revenue_cagr_5y']*100:.2f}% / 10y {rev_10y_str}")
    print(f"  FCF CAGR         : {d['fcf_cagr_5y']*100:.2f}%   (FCF0 {d['fcf0']/1e9:.3f}B)")
    print(f"  최악 YoY 매출    : {d['worst_yoy_revenue_growth']*100:.2f}% ({d['worst_yoy_year']}년)")
    print(f"  순부채/EBITDA    : {d['net_debt_to_ebitda']:.3f}배")
    print()
    print(f"  DRS              : {result['drs']['score']:.2f}")
    for k, v in result["drs"]["components"].items():
        print(f"      {k:24} {v:5.2f}")
    print(f"  Lynch 유형       : {result['lynch']['used']} ({result['lynch']['auto_note']})")
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
