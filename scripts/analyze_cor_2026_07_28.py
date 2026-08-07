"""
Cencora, Inc.(COR, 구 AmerisourceBergen) 정식 분석 - 2026-07-28.

경위: 2026-07-26 스크리닝 통과 후보(MCK와 동일 산업 - 의약품유통 3파전
과점). 비큐(ad-hoc) 분석. 스크리닝 노트에 "⚠️출처 내부 불일치: 통계페이지
P/FCF 38.70인데 시총/FY2025 FCF는 18.8배 - FCF 정의 차이로 보이나 확정
못함. 통과폭이 얇아 이 불일치가 판정을 뒤집을 수 있음"이라는 경고가 있어
SEC EDGAR 원자료로 재검증 후 진행했다. 재검증 결과 FCF 원자료 자체(FY2023
~2025)는 스크리닝 추정치와 소수점까지 정확히 일치해 - 불일치의 원인은
FCF가 아니라 다른 곳(아마도 시가총액 조회 시점 차이나 P/FCF 산출 방식)임을
확인했다.

⚠️ **FY2020 오피오이드 소송충당금 - MCK와 동일 유형, 규모는 더 큼**: FY2020
영업손실 -$5,135M(원 충당금은 세전 $6.6B, 세후 $5.5B)은 AmerisourceBergen이
2020년 4분기에 인식한 오피오이드 소송충당금이다 - 2022년 확정된 18년간
$6.4B 전국합의로 이어졌다(McKesson/Cardinal Health와 함께 3사 $21B 합의의
일부). MCK 분석에서 확인한 것과 동일하게 **비현금성**이라 FY2020
영업활동현금흐름은 정상($2,207M)이었다 - 기본 5년 기준연도가 하필 FY2020
이지만 FCF 기준 CAGR 계산은 막히지 않는다. margin_years 기본값(최근
5개년=FY2021~2025)이 FY2020을 자동 제외해 별도 조치 불필요(FY2019의 $570M
자산손상차손도 같은 이유로 자동 제외됨).

이 소송은 MCK보다도 더 진행형이다 - 2024년 이사회가 임원 배임 관련 파생
소송으로 $111M 추가 합의를 했고, 법무부(DOJ)가 별도로 통제물질법(CSA)
위반 관련 전국 소송을 제기한 상태다. active_antitrust_or_regulatory_case=
True로 반영.

원자료: 전부 SEC EDGAR as-filed 10-K에서 직접 추출(2026-07-28 조회, FY2017
~2025, 9개년, 회계연도는 매년 9월 30일 종료).
  FY2025 10-K(0001140859-25-000131) R3/R5/R9
  FY2022 10-K(0001140859-22-000098) R5/R9 (FY2020~2022)
  FY2019 10-K(0001140859-19-000040) R4/R8 (FY2017~2019, 당시 사명 AmerisourceBergen)
시가총액: stockanalysis.com 2026-07-27 종가 기준 $60.54B.

실행: python3 scripts/analyze_cor_2026_07_28.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.pipeline import AnalysisInputs, run_analysis, save_ledger

M = 1_000_000
K = 1_000  # 원자료가 '천 달러' 단위

# ── SEC EDGAR as-filed 실측 (단위: USD, 원 단위) ────────────────────────
REVENUE = {
    2017: 153143826 * K, 2018: 167939635 * K, 2019: 179589121 * K,
    2020: 189893926 * K, 2021: 213988843 * K, 2022: 238587006 * K,
    2023: 262173411 * K, 2024: 293958599 * K, 2025: 321332819 * K,
}
OPERATING_INCOME = {
    2017: 1060342 * K, 2018: 1443685 * K,
    2019: 1111923 * K,     # 자산손상차손 $570M 포함
    2020: -5135354 * K,    # 오피오이드 소송충당금(세전 $6.6B) 반영
    2021: 2354197 * K, 2022: 2366378 * K, 2023: 2340731 * K,
    2024: 2175249 * K, 2025: 2628601 * K,
}
OPERATING_CASHFLOW = {
    2017: 1504138 * K, 2018: 1411388 * K, 2019: 2344023 * K,
    2020: 2207040 * K, 2021: 2666586 * K, 2022: 2703088 * K,
    2023: 3911334 * K, 2024: 3484685 * K, 2025: 3875120 * K,
}
CAPEX = {
    2017: 466397 * K, 2018: 336411 * K, 2019: 310222 * K,
    2020: 369677 * K, 2021: 438217 * K, 2022: 496318 * K,
    2023: 458359 * K, 2024: 487173 * K, 2025: 667981 * K,
}

# 재무상태표 (FY2025 10-K R3, 2025-09-30 기준)
CASH = 4356138 * K
SHORT_TERM_DEBT = 117785 * K
LONG_TERM_DEBT = 7542988 * K
NET_DEBT = (SHORT_TERM_DEBT + LONG_TERM_DEBT) - CASH

DA_2025 = 501310 * K + 567106 * K   # 감가상각 + 무형자산상각
EBITDA = OPERATING_INCOME[2025] + DA_2025

MARKET_CAP = 60.54e9
RF = 0.0447


def build_inputs() -> AnalysisInputs:
    return AnalysisInputs(
        ticker="COR",
        company_name="Cencora, Inc.",
        revenue_by_year=REVENUE,
        operating_income_by_year=OPERATING_INCOME,
        operating_cashflow_by_year=OPERATING_CASHFLOW,
        capex_by_year=CAPEX,
        market_cap=MARKET_CAP,
        net_debt=NET_DEBT,
        ebitda=EBITDA,
        risk_free_rate=RF,

        competitor_threat_weights=[0.35, 0.30, 0.25],
        market_share_trend_pp_per_year=0.0,
        active_antitrust_or_regulatory_case=True,
        demand_sensitivity_pct=0.08,
        subjective_input_basis=(
            "McKesson 0.35(3파전 중 최대 경쟁자이자 이번 배치에서 동시분석한 "
            "동일업종 종목), Cardinal Health 0.30, PBM/보험사 수직계열화 "
            "위협 0.25(CVS/Optum의 자체 유통망 내재화 압력) - MCK 분석과 "
            "동일 논리로 동일 가중치 적용(같은 산업구조이므로 일관성 유지)"
            "[셋 다 추정치]. market_share_trend=0.0: 3사 과점구조가 수십년째 "
            "안정적이라는 근거는 있으나 정량 추세 데이터가 없어 중립[추정치]. "
            "active_antitrust_or_regulatory_case=True: MCK보다도 진행형 "
            "성격이 강하다 - (1)FY2020 세전 $6.6B 오피오이드 소송충당금 "
            "-> 2022년 18년간 $6.4B 전국합의로 확정(3사 $21B 합의의 일부), "
            "(2)2024년 이사회 임원 배임 관련 파생소송 $111M 추가 합의, "
            "(3)미 법무부(DOJ)가 별도로 통제물질법(CSA) 위반 관련 전국 "
            "소송을 제기한 상태. demand_sensitivity=0.08: MCK과 동일 논리 "
            "(처방의약품 유통은 경기와 무관하게 필수 소비) - 이 프로젝트 "
            "최저권."
        ),

        model_used="two_stage",
        model_choice_reason=(
            "COR도 MCK와 같은 이유로 two_stage를 채택한다 - 성숙・안정 "
            "산업의 과점 사업자이나 최근 3년 매출성장이 가속(FY24 +12.1%, "
            "FY25 +9.3%)되는 국면이라 GLP-1 등 고가 특수의약품 유통 확대 "
            "효과로 추정되며, 이 가속이 무기한 지속된다고 가정하는 "
            "single_stage보다 정상화 경로를 명시하는 two_stage가 보수적이다. "
            "첫 정식분석이라 대조할 과거 기록이 없다 - 실제 괴리는 "
            "divergence_warning으로 확인."
        ),

        data_sources=[
            "SEC EDGAR 10-K FY2025(0001140859-25-000131) R3/R5/R9, as-filed, 2026-07-28 조회",
            "SEC EDGAR 10-K FY2022(0001140859-22-000098) R5/R9 (FY2020~2022)",
            "SEC EDGAR 10-K FY2019(0001140859-19-000040) R4/R8 (FY2017~2019, 당시 AmerisourceBergen)",
            "stockanalysis.com 시가총액 $60.54B (2026-07-27 종가)",
            "WebSearch: 오피오이드 소송충당금 확정 경위($6.6B->$6.4B/18년), "
            "2024 이사회 파생소송 $111M, DOJ CSA 소송 확인",
        ],
    )


def main():
    result = run_analysis(build_inputs())
    d, g = result["derived"], result["growth"]
    models = result["implied_growth"]["models"]

    print("=" * 100)
    print(f"COR 정식 분석 결과 ({result['meta']['analyzed_at'][:10]}, 엔진 {result['meta']['engine_version']})")
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
