"""
Sea Limited(SE) 정식 분석 - 2026-07-30.

경위: "매수 평가가 무조건 나올 기업 스크리닝 후 분석까지 실행" 요청에 대한
응답. engine/screener.py(v3.19 판별식, Realistic Growth>=8% AND Implied
Growth<=5.5%)로 새 후보군(Coupang/Sea Limited/JD.com)을 훑은 결과 Coupang은
FCF가 최근 2년 연속 감소(FY2023 $1.756B -> FY2024 $1.007B -> FY2025 $0.522B)
해 탈락, Sea Limited만 A등급 통과(Gap 추정 +17.39%p, DRS추정 34.6). 통과했다고
"무조건 매수"가 확정된 것은 아니다 - 스크리너는 관측가능한 시장지표로부터의
근사치일 뿐이며(engine/screener.py 상단 docstring, BKNG/PDD 실사례가 이미
증명), 정식판정은 반드시 run_analysis()로 확정한다.

Shopee(이커머스, SEA 6개국 GMV 1위 ~53%)/Garena(게임, Free Fire)/Monee(구
SeaMoney, 핀테크-대출) 3개 사업부 지주회사. 케이맨제도 법인이라 SEC에는
10-K가 아닌 20-F(외국민간발행인)로 공시한다.

원자료: 전부 SEC EDGAR as-filed 20-F에서 직접 추출(2026-07-30 조회).
  FY2025 20-F(CIK 1703399, accession 0001140361-26-015366) R2/R4/R6
  FY2022 20-F(accession 0001140361-23-017021) R2/R4/R6 (FY2020~2022)
시가총액: stockanalysis.com 2026-07-30 조회 $66.37B(전일종가 $107.41,
52주 고점 $199.30 대비 -46.1%, YoY -30.0%).

⚠️ FY2020 FCF($220M)이 매출($4.4B) 대비 극히 작아(초기 스케일업 단계) 이를
기준연도로 쓰면 FCF CAGR이 노이즈에 극도로 민감해진다(분모가 작아 사소한
변동도 CAGR을 크게 흔든다) - BKNG류의 '위기 저점' 왜곡과는 다른 유형이지만
결과적으로 유사하게 과장 위험이 있다는 점을 data_limitations에 명시할 것.
override는 걸지 않았다(2021~2022 FCF가 적자라 더 나은 대안 기준연도가
없음 - CAGR가드상 음수 기준연도 자체가 불가능).

⚠️ 경쟁강도: TikTok Shop이 동남아 이커머스 GMV 점유율을 33%->44%로 1년만에
급등시켰고(Shopee는 53%로 여전히 1위지만 베트남 등 개별시장에서는 64%->52%로
하락), Q1 2026 실적에서 마진압박(조정EPS 컨센서스 미달, Shopee 개발인력
8% 감원)이 이미 현실화됐다 - PDD와 같은 유형의 '스크리너가 못 보는 경쟁강도'
리스크라 판단해 subjective_input에 반영(2026-07 WebSearch로 확인).

실행: python3 scripts/analyze_se_2026_07_30.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.pipeline import AnalysisInputs, run_analysis, save_ledger

K = 1_000  # 원자료가 '천 달러' 단위

# ── SEC EDGAR as-filed 실측 (단위: USD, 원 단위) ────────────────────────
REVENUE = {
    2020: 4375664 * K, 2021: 9955190 * K, 2022: 12449705 * K,
    2023: 13063560 * K, 2024: 16819866 * K, 2025: 22938469 * K,
}
OPERATING_INCOME = {
    2020: -1303325 * K, 2021: -1583060 * K, 2022: -1487508 * K,
    2023: 224778 * K, 2024: 662152 * K, 2025: 1985306 * K,
}
OPERATING_CASHFLOW = {
    2020: 555868 * K, 2021: 208649 * K, 2022: -1055692 * K,
    2023: 2079688 * K, 2024: 3277420 * K, 2025: 5024523 * K,
}
CAPEX = {
    2020: 336274 * K, 2021: 772177 * K, 2022: 924178 * K,
    2023: 241605 * K, 2024: 318153 * K, 2025: 513809 * K,
}

# 재무상태표 (FY2025 20-F R2, 2025-12-31 기준)
CASH = 4158920 * K
SHORT_TERM_INVESTMENTS = 6413261 * K
BORROWINGS_CURRENT = 283181 * K
CONVERTIBLE_NOTES_CURRENT = 1050071 * K
BORROWINGS_LT = 510396 * K
CONVERTIBLE_NOTES_LT = 0 * K
TOTAL_DEBT = BORROWINGS_CURRENT + CONVERTIBLE_NOTES_CURRENT + BORROWINGS_LT + CONVERTIBLE_NOTES_LT
NET_DEBT = TOTAL_DEBT - CASH - SHORT_TERM_INVESTMENTS   # 순현금(대규모)

DA_2025 = 372171 * K
EBITDA = OPERATING_INCOME[2025] + DA_2025

MARKET_CAP = 66.37e9
RF = 0.0447


def build_inputs() -> AnalysisInputs:
    return AnalysisInputs(
        ticker="SE",
        company_name="Sea Limited",
        revenue_by_year=REVENUE,
        operating_income_by_year=OPERATING_INCOME,
        operating_cashflow_by_year=OPERATING_CASHFLOW,
        capex_by_year=CAPEX,
        market_cap=MARKET_CAP,
        net_debt=NET_DEBT,
        ebitda=EBITDA,
        risk_free_rate=RF,

        competitor_threat_weights=[0.35, 0.15, 0.10],
        market_share_trend_pp_per_year=-2.0,
        active_antitrust_or_regulatory_case=False,
        demand_sensitivity_pct=0.30,
        subjective_input_basis=(
            "TikTok Shop 0.35(2026-07 WebSearch 확인: 동남아 이커머스 GMV "
            "점유율 33%->44%로 1년만에 급등, 베트남에서는 Shopee 점유율을 "
            "64%->52%로 직접 잠식 - PDD의 3파전과 유사한 유형의 실측 경쟁강도), "
            "Lazada(Alibaba계열) 0.15(점유율 6%->3%로 반토막나 위협도는 낮아지는 "
            "중이나 자본력 있는 경쟁자라 완전배제는 안함), Tencent/miHoYo 등 "
            "게임업계 대형퍼블리셔 0.10(Garena/Free Fire 대비 상대적으로 낮은 "
            "가중치 - Free Fire는 2026 Q1 '2021년 이후 최고분기'로 자체 사이클 "
            "견조). market_share_trend=-2.0pp: TikTok Shop의 실측 점유율 "
            "급등세(연 +11pp)를 반영해 음수로 설정 - Shopee가 전체 1위(53%)를"
            "유지 중이라 -2.0pp로 완화했으나 방향은 명확히 열세전환. "
            "active_antitrust_or_regulatory_case=False: 2026-07 WebSearch로 "
            "확인한 결과 현재 진행 중인 반독점・규제조사는 발견되지 않음(다만 "
            "SEA 각국의 이커머스・핀테크 규제 변화 리스크는 상존). "
            "demand_sensitivity=0.30: 동남아・남미(Monee 신규진출) 신흥국 "
            "소비자 지출에 노출돼 PDD(중국 내수, 규제리스크로 별도반영)와는 "
            "다른 유형의 경기민감도 - 신흥국 통화・금리 변동에 좀 더 열려있어 "
            "GWRE/PTC(0.22~0.25)보다는 높게, PDD 수준([추정치])으로 설정."
        ),

        model_used="two_stage",
        model_choice_reason=(
            "Sea는 FY2020(매출 $4.4B)에서 FY2025(매출 $22.9B)까지 5년간 "
            "매출이 5.2배로 커진 전형적 고성장 스토리이자, FY2023부터 "
            "영업이익・FCF가 흑자전환 후 매년 확대되는 궤적이다 - 명시적 "
            "성장기간을 모델링하는 two_stage가 이 궤적에 부합한다고 1차 "
            "판단. 회사 자체 FY2026 가이던스(매출 +25% 성장, EBITDA는 "
            "전년 수준 유지 - 마진압박 시사)와도 대조해 재검토할 것(아래 "
            "실행결과 참고, 모델괴리가 크면 GWRE/KLAC/VRT/KEYS와 동일 "
            "절차로 최종 확정)."
        ),

        data_sources=[
            "SEC EDGAR 20-F FY2025(0001140361-26-015366) R2/R4/R6, as-filed, 2026-07-30 조회",
            "SEC EDGAR 20-F FY2022(0001140361-23-017021) R2/R4/R6 (FY2020~2022)",
            "stockanalysis.com 시가총액 $66.37B, 주가 $107.41(전일종가), 2026-07-30 조회",
            "WebSearch: Shopee/TikTok Shop/Lazada 동남아 이커머스 점유율(2026), "
            "Sea Q1 2026 실적・가이던스・주가하락 배경 확인",
        ],
    )


def main():
    result = run_analysis(build_inputs())
    d, g = result["derived"], result["growth"]
    models = result["implied_growth"]["models"]

    print("=" * 100)
    print(f"SE(Sea Limited) 정식 분석 결과 ({result['meta']['analyzed_at'][:10]}, 엔진 {result['meta']['engine_version']})")
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
