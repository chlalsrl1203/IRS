"""
Keysight Technologies(KEYS) 정식 분석 - 2026-07-30.

경위: 공식 83개 큐의 49번째 종목(Notion 큐 페이지가 "다음 작업은 여기서부터"로
가리키고 있던 항목). "뭐 사야돼" 질문에 대한 응답으로 큐를 계속 진행.

회계연도는 매년 10월 31일 종료. FY2020~2025 6개년 전부 흑자 - CAGR 가드나
기준연도 함정 이슈 없음(디폴트 5y lookback이 정확히 FY2020에 떨어짐).

**M&A 참고(GEN 선례 점검)**: FY2025 4분기(2025-10-15)에 Spirent Communications
인수를 현금 $1,415M(순, 인수 현금 차감후)에 완료했고, 반독점 조건 충족을 위해
Spirent의 일부 사업부(고속이더넷·네트워크보안·채널에뮬레이션)를 Viavi에 $399M에
동시 매각했다. 인수 종결일이 FY2025 회계연도 마감(10/31) 2주 전이라 FY2025
매출($5,375M)에 대한 영향은 미미(SEC 10-Q에 따르면 Spirent의 실질적 매출
기여는 FY2026 1~2분기에 각각 $88M/$55M 순증 - FY2025에는 사실상 없음).
**따라서 GEN과 달리 FY2020~2025 과거 CAGR 자체는 M&A로 왜곡되지 않은
유기적 수치다.** 다만 현재 시가총액은 Spirent의 향후 매출 기여(연산
~$700~800M 추정)를 이미 반영하고 있을 가능성이 높다 - 이는 후행 CAGR과
전방 시장 기대 사이의 비대칭이므로 data_limitations에 명시.

원자료: 전부 SEC EDGAR as-filed 10-K에서 직접 추출(2026-07-30 조회).
  FY2025 10-K(CIK 1601046, accession 0001601046-25-000127) R3/R6/R8/R20
  FY2022 10-K(accession 0001601046-22-000161) R3/R6/R8 (FY2020~2022)
시가총액: stockanalysis.com 2026-07-30 조회 $50.71B(전일종가 $305.17,
당일 -2.77%, 52주 레인지 $152.85~$374.96 - 변동성 매우 큼).

실행: python3 scripts/analyze_keys_2026_07_30.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.pipeline import AnalysisInputs, run_analysis, save_ledger

M = 1_000_000  # 원자료가 '백만 달러' 단위

# ── SEC EDGAR as-filed 실측 (단위: USD, 원 단위) ────────────────────────
REVENUE = {
    2020: 4221 * M, 2021: 4941 * M, 2022: 5420 * M,
    2023: 5464 * M, 2024: 4979 * M, 2025: 5375 * M,
}
OPERATING_INCOME = {
    2020: 765 * M, 2021: 1080 * M, 2022: 1334 * M,
    2023: 1358 * M, 2024: 833 * M, 2025: 876 * M,
}
OPERATING_CASHFLOW = {
    2020: 1016 * M, 2021: 1322 * M, 2022: 1144 * M,
    2023: 1408 * M, 2024: 1052 * M, 2025: 1409 * M,
}
CAPEX = {
    2020: 117 * M, 2021: 174 * M, 2022: 185 * M,
    2023: 197 * M, 2024: 154 * M, 2025: 128 * M,
}

# 재무상태표 (FY2025 10-K R6/R20, 2025-10-31 기준)
CASH = 1873 * M
LONG_TERM_DEBT = 2534 * M   # 전부 선순위채권, 유동성 부채 없음(R20 확인)
NET_DEBT = LONG_TERM_DEBT - CASH

DA_2025 = (131 + 145) * M   # 감가상각 131 + 무형자산상각 145 (R8)
EBITDA = OPERATING_INCOME[2025] + DA_2025

MARKET_CAP = 50.71e9
RF = 0.0447


def build_inputs() -> AnalysisInputs:
    return AnalysisInputs(
        ticker="KEYS",
        company_name="Keysight Technologies, Inc.",
        revenue_by_year=REVENUE,
        operating_income_by_year=OPERATING_INCOME,
        operating_cashflow_by_year=OPERATING_CASHFLOW,
        capex_by_year=CAPEX,
        market_cap=MARKET_CAP,
        net_debt=NET_DEBT,
        ebitda=EBITDA,
        risk_free_rate=RF,

        competitor_threat_weights=[0.35, 0.20, 0.15],
        market_share_trend_pp_per_year=0.8,
        active_antitrust_or_regulatory_case=False,
        demand_sensitivity_pct=0.32,
        subjective_input_basis=(
            "Rohde & Schwarz 0.35(비상장 독일기업, RF/무선통신 계측 최대 "
            "경쟁자 - 통설상 Keysight와 함께 T&M 시장 선두그룹), Anritsu "
            "0.20(통신망 테스트 강세), Viavi Solutions 0.15(2025-10 Spirent "
            "일부 사업부-고속이더넷/네트워크보안/채널에뮬레이션-를 Keysight "
            "로부터 인수해 네트워크 가시성 영역에서 직접 경쟁자로 강화됨). "
            "Tektronix(Fortive)·National Instruments(Emerson 편입)·Teradyne"
            "(반도체 ATE, 인접영역)는 부문이 겹치나 핵심 RF/무선 계측과는 "
            "거리가 있어 가중치에서 제외 - [추정치]. market_share_trend="
            "+0.8pp: 2025-10-15 Spirent 인수 완료(현금 $1,415M 순액)로 "
            "소프트웨어정의 테스트・5G/6G 네트워크 테스트 영역 포트폴리오가 "
            "강화됐고, FY2026 1~2분기 10-Q에 이미 매출 순증($88M/$55M)이 "
            "확인됨 - 완만한 긍정 추세로 설정[추정치]. "
            "active_antitrust_or_regulatory_case=False: Spirent 인수 관련 "
            "반독점 조건(사업부 매각)은 2025-10-15 인수 종결과 동시에 이미 "
            "이행 완료됐고 2026-07 WebSearch로 확인한 결과 현재 진행 중인 "
            "별도의 반독점・경쟁당국 조사는 발견되지 않음. "
            "demand_sensitivity=0.32: T&M 장비 수요는 반도체・통신・"
            "항공우주국방・자동차 등 광범위한 설비투자 사이클에 걸쳐있어 "
            "KLAC(0.38, 반도체 웨이퍼검사 단일 의존)보다는 분산되나, "
            "FY2024 매출이 반도체 계측장비 수요둔화로 -8.86% YoY 감소한 "
            "실측 사례가 있어 GWRE/PTC(0.22~0.25)보다는 경기민감도가 "
            "뚜렷하다고 판단[추정치]."
        ),

        model_used="two_stage",
        model_choice_reason=(
            "1차 실행 결과 모델괴리 7.67%p(single_stage 8.17% / two_stage "
            "15.84%)로 GWRE/KLAC 사례와 같은 재검토 기준을 넘어, Lynch "
            "자동분류(cyclical, 대체분류 없음)와 2026-07 WebSearch로 확보한 "
            "최신 가이던스를 대조했다. KEYS는 2026-05-19 발표 FY2026 Q2 "
            "실적에서 매출 +31% YoY(AI 관련 매출이 FY2025 연간 실적을 "
            "상반기만에 초과), 수주 +56% YoY를 기록했고 FY2026 전사 매출 "
            "성장률 가이던스를 'high-20s%'로 상향했다 - 이는 Spirent 인수 "
            "기여분을 포함한 수치이나 AI 인프라 테스트 수요가 핵심 동인으로 "
            "지목됐다. 애널리스트들은 이 예외적 속도가 결국 정상화된다고 "
            "보고 장기 정상화 성장률을 15.4%로 역산했는데, 이는 two_stage의 "
            "15.84%와 거의 일치하고(0.44%p 차이) single_stage의 8.17%보다 "
            "훨씬 가깝다 - VRT 사례와 같은 결론(AI발 고성장 국면에서는 "
            "two_stage가 시장의 실제 기대치에 더 부합). 다만 이 회사 스스로도 "
            "'AI가 기준선을 끌어올린 지금도 기존 5~7% 장기 프레임워크가 "
            "유효한지'에 대해 '향후 업데이트 예정'이라고만 답해 아직 공식 "
            "장기목표를 재확정하지 않았다는 점은 불확실성으로 남는다."
        ),

        data_sources=[
            "SEC EDGAR 10-K FY2025(0001601046-25-000127) R3/R6/R8/R20, as-filed, 2026-07-30 조회",
            "SEC EDGAR 10-K FY2022(0001601046-22-000161) R3/R6/R8 (FY2020~2022)",
            "stockanalysis.com 시가총액 $50.71B, 주가 $305.17(전일종가), 2026-07-30 조회",
            "WebSearch: Keysight-Spirent 인수/매각 구조, FY2026 10-Q 매출기여, 경쟁구도 확인",
            "WebSearch: Keysight FY2026 Q2 실적발표(2026-05-19) - 매출 +31% YoY, "
            "수주 +56% YoY, FY26 가이던스 high-20s%, 애널리스트 장기정상화성장률 15.4% 역산",
        ],
    )


def main():
    result = run_analysis(build_inputs())
    d, g = result["derived"], result["growth"]
    models = result["implied_growth"]["models"]

    print("=" * 100)
    print(f"KEYS 정식 분석 결과 ({result['meta']['analyzed_at'][:10]}, 엔진 {result['meta']['engine_version']})")
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
