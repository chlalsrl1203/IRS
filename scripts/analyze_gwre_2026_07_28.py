"""
Guidewire Software, Inc.(GWRE) 정식 분석 - 2026-07-28.

경위: 공식 83개 큐의 45번째 종목. 2026-07-26 06:10에 한 세션이 잠금을 걸고
SEC 10-K FY2017~2025 데이터 수집까지 마쳤으나 엔진 미실행 상태에서 민기님
지시로 중단・잠금해제됐다(큐 페이지 45번 항목 기록). 재개 지침에 따라
데이터 수집부터 처음부터 다시 했다(이전 세션의 미검증 중간 산출물을
재사용하지 않음).

⚠️ **큐 페이지가 미리 경고한 CAGR 가드 이슈 - 실제로는 발동하지 않음**:
FY2022 영업손실 -$199.4M・OCF -$37.9M(둘 다 확인됨)로 FCF가 -$59.7M까지
깊은 적자다. 우려는 이 해가 기본 5년 CAGR 기준연도(`years[-6]`)에 걸려
BKNG/TCOM처럼 CAGR 가드가 발동할 수 있다는 것이었다. 그러나 **9개년
(FY2017~2025) 전체를 확보하고 나니 기본 기준연도가 FY2020으로 계산됐다**
(2025-5=2020, 배열 길이와 무관하게 항상 "최근연도-5년"이므로) - FY2020은
OCF $113.1M・capex $25.7M로 FCF $87.4M(흑자)라 가드에 걸리지 않는다.
FY2022는 3년 CAGR의 고정 기준연도(`years[-4]`)에도 걸리지 않는다
(2025-3=2022 세대로 계산되면 걸렸겠지만, revenue_cagr_3y는 매출만 쓰고
FCF는 안 쓰므로애초에 FCF 적자 여부와 무관하다). 결론: **override 불필요**
- 데이터를 충분히 확보하면 저절로 우회되는 케이스였다(짧은 조회창을 썼다면
FY2022가 기준연도가 됐을 수 있어 BKNG류 교훈과 일맥상통).

GWRE는 SaaS 전환(라이선스→클라우드 구독) 과정에서 FY2020~2024 내내
영업적자를 기록하다 FY2025에 흑자전환(+$41.1M)한 전형적 SaaS 전환기
기업이다. margin_years 기본값(최근 5개년=FY2021~2025)이 이 적자 구간
대부분을 그대로 포함해 margin_volatility가 실제 리스크(마진압박이 실재
했다)를 정직하게 반영한다 - 별도 조치 불필요.

원자료: 전부 SEC EDGAR as-filed 10-K에서 직접 추출(2026-07-28 조회, FY2017
~2025, 9개년, 회계연도는 매년 7월 31일 종료).
  FY2025 10-K(0001528396-25-000221) R3/R5/R8
  FY2022 10-K(0001528396-22-000106) R5/R8 (FY2020~2022, 손실구간 포함)
  FY2019 10-K(0001528396-19-000032) R4/R7 (FY2017~2019)
시가총액: stockanalysis.com 2026-07-28 종가 기준 $13.27B(전일 대비 +6.78% -
2026-07-28 WebSearch로 확인, 국채금리 하락에 따른 장기듀레이션 SaaS 업종
전반 랠리이지 GWRE 개별 뉴스 아님. 직전 실적발표는 2026-06-04, 어닝비트+
가이던스 상향).

실행: python3 scripts/analyze_gwre_2026_07_28.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.pipeline import AnalysisInputs, run_analysis, save_ledger

K = 1_000  # 원자료가 '천 달러' 단위

# ── SEC EDGAR as-filed 실측 (단위: USD, 원 단위) ────────────────────────
REVENUE = {
    2017: 509533 * K, 2018: 652849 * K, 2019: 719514 * K,
    2020: 742307 * K, 2021: 743267 * K, 2022: 812614 * K,
    2023: 905341 * K, 2024: 980497 * K, 2025: 1202459 * K,
}
OPERATING_INCOME = {
    2017: 21861 * K, 2018: -15624 * K, 2019: 1471 * K,
    2020: -23886 * K, 2021: -105584 * K, 2022: -199447 * K,   # SaaS 전환기 적자
    2023: -149490 * K, 2024: -52573 * K, 2025: 41068 * K,     # FY25 흑자전환
}
OPERATING_CASHFLOW = {
    2017: 138759 * K, 2018: 140459 * K, 2019: 116126 * K,
    2020: 113066 * K, 2021: 111587 * K,
    2022: -37940 * K,    # FY22 유일한 OCF 적자 - 그러나 기본 기준연도(FY2020) 아님
    2023: 38395 * K, 2024: 195748 * K, 2025: 300867 * K,
}
CAPEX = {
    2017: 6670 * K, 2018: 12011 * K,
    2019: 48857 * K,     # 본사 부동산 관련 일시적 급증(유형자산 $44.9M)
    2020: 25660 * K, 2021: 28854 * K, 2022: 21776 * K,
    2023: 17427 * K, 2024: 18527 * K, 2025: 20455 * K,
}

# 재무상태표 (FY2025 10-K R3, 2025-07-31 기준)
CASH = 697902 * K
SHORT_TERM_INVESTMENTS = 451541 * K
CONVERTIBLE_NOTES_LT = 674568 * K   # 유동분 $0 - 전액 비유동으로 재분류됨(FY25 중)
NET_DEBT = CONVERTIBLE_NOTES_LT - (CASH + SHORT_TERM_INVESTMENTS)

DA_2025 = 23758 * K   # 감가상각+무형자산상각(부채발행비상각・계약획득원가상각은 제외)
EBITDA = OPERATING_INCOME[2025] + DA_2025

MARKET_CAP = 13.27e9   # 2026-07-28 종가($159.40 x 83.26M주), 업종전반 랠리 반영
RF = 0.0447


def build_inputs() -> AnalysisInputs:
    return AnalysisInputs(
        ticker="GWRE",
        company_name="Guidewire Software, Inc.",
        revenue_by_year=REVENUE,
        operating_income_by_year=OPERATING_INCOME,
        operating_cashflow_by_year=OPERATING_CASHFLOW,
        capex_by_year=CAPEX,
        market_cap=MARKET_CAP,
        net_debt=NET_DEBT,
        ebitda=EBITDA,
        risk_free_rate=RF,

        competitor_threat_weights=[0.40, 0.25, 0.20],
        market_share_trend_pp_per_year=0.5,
        active_antitrust_or_regulatory_case=False,
        demand_sensitivity_pct=0.22,
        subjective_input_basis=(
            "Duck Creek Technologies 0.40(가장 직접적인 경쟁자 - 2023년 "
            "Vista Equity가 $2.6B에 인수해 비상장 PE 소유 상태로 저가・중견 "
            "보험사 시장을 공격적으로 공략 중), Sapiens International "
            "0.25(P&C・생명보험 전반의 다각화 포트폴리오, EMEA 강세 + 북미 "
            "진출 확대), SAP/Salesforce 등 범용 엔터프라이즈SW 0.20(보험 "
            "전용은 아니나 일부 기능 대체 위협). 셋 다 [추정치]. "
            "market_share_trend=+0.5pp: 2026-07 WebSearch 확인 - Tier 1 "
            "대형 보험사 시장에서 GWRE 압도적 우위 유지(고객리뷰 4.6점 vs "
            "Duck Creek 3.2점), 다만 Duck Creek이 중견시장에서 진전 중이라 "
            "완전한 독주는 아님 - 완만한 긍정 추세로 설정[추정치]. "
            "active_antitrust_or_regulatory_case=False: 2026-07 WebSearch로 "
            "확인 결과 반독점・경쟁당국 조사는 발견되지 않았다. 2020년 "
            "클라우드 전환 관련 진술에 대한 증권집단소송과 2024년 원고측 "
            "로펌의 '조사 발표'(통상적 소송인 모집 공고)가 있으나 반독점・"
            "시장구조 규제와는 무관해 False 유지. "
            "demand_sensitivity=0.22: 보험사 대상 기간계 시스템(코어시스템) "
            "판매는 다년 계약・필수업무 소프트웨어라 재량소비 성격은 약하나, "
            "신규 도입・업그레이드 의사결정은 보험사 IT예산 사이클에 따라 "
            "지연될 수 있어 완전한 방어주는 아니다 - MCK(0.08)보다는 "
            "높고 BKNG(0.60)보다는 훨씬 낮은 중간값[추정치]."
        ),

        model_used="single_stage",
        model_choice_reason=(
            "초안에서는 'FY2025 흑자전환+가속 성장' 서사를 근거로 two_stage를 "
            "고려했으나, 실제 계산 결과 single_stage(8.35%)와 two_stage"
            "(17.38%)의 괴리가 9.03%p로 이 프로젝트에서 손꼽히게 크고(경고임계값 "
            "3%p의 3배), **판정 자체가 갈린다**(two_stage: Gap -6.11%p "
            "과대평가 vs single_stage: Gap +2.92%p 적정가/경계선) - PH가 "
            "정확히 이 유형의 실수(모델선택이 판정을 뒤집음)로 재검증됐던 "
            "사례다. 엔진의 Lynch 자동분류가 'stalwart'로 나온 점이 결정적 "
            "근거다(revenue_cagr_5y 10.13%는 fast_grower 기준 15% 미달 - "
            "SaaS 전환기 매출은 견조했으나 폭발적 고성장은 아니었음). 이 "
            "프로젝트의 확립된 관행(CDNS: '성숙 stalwart이고 two_stage와의 "
            "괴리가 커 Gordon Growth 채택')을 그대로 따라 stalwart + 대형 "
            "모델괴리 조합에서는 더 보수적인 single_stage를 채택한다. "
            "GWRE가 여전히 SaaS 전환 초기 국면이라는 반론은 있을 수 있으나, "
            "엔진 자체 분류 결과를 무시하고 서사만으로 더 낙관적인 모델을 "
            "고르는 것은 이 프로젝트가 반복적으로 경계해온 '근거 없는 "
            "자동화/서술형 근사'와 다를 바 없다고 판단했다."
        ),

        data_sources=[
            "SEC EDGAR 10-K FY2025(0001528396-25-000221) R3/R5/R8, as-filed, 2026-07-28 조회",
            "SEC EDGAR 10-K FY2022(0001528396-22-000106) R5/R8 (FY2020~2022)",
            "SEC EDGAR 10-K FY2019(0001528396-19-000032) R4/R7 (FY2017~2019)",
            "stockanalysis.com 시가총액 $13.27B (2026-07-28 종가)",
            "WebSearch: GWRE 주가 급등 원인(업종전반 금리랠리, 2026-06-04 실적 "
            "어닝비트/가이던스상향), 경쟁구도(Duck Creek/Sapiens), 반독점/규제조사 여부 확인",
        ],
    )


def main():
    result = run_analysis(build_inputs())
    d, g = result["derived"], result["growth"]
    models = result["implied_growth"]["models"]

    print("=" * 100)
    print(f"GWRE 정식 분석 결과 ({result['meta']['analyzed_at'][:10]}, 엔진 {result['meta']['engine_version']})")
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
