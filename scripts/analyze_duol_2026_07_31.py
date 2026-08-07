"""
Duolingo(DUOL) 정식 분석 - 2026-07-31.

경위: "스크리닝 실행" 요청에 응답해 engine/screener.py의 4분류 체크리스트
(2026-07-31 문서화)를 적용 - Chewy(매출성장 둔화세가 뚜렷해 '진짜 나빠짐'에
가까움, 근소 미달)/Zscaler(FCF수익률 미달로 밸류에이션 탈락)는 탈락,
**Duolingo만 통과**(스크리너 추정 Gap +34.14%p, 이 세션 스크리너 추정치
최대). 세계 최대 언어학습 플랫폼, AI가 언어학습 수요를 대체할 것이라는
공포 서사로 주가가 52주 고점 대비 -75%, YoY -59.0% 급락.

**⚠️ 이번엔 순수 '공포과잉'이 아니다 - 회사 스스로 FY2026 가이던스를
큰 폭으로 낮췄다(2026-07 WebSearch로 확인)**: 2026-02-27 FY2025 실적발표
에서 FY2026 bookings 가이던스를 $12.74~12.98억(성장률 10~12%)으로
제시했는데, 이는 과거 5년간 연 35~55%로 성장해온 궤적과 완전히 다른
수준이다. 경영진은 "무료 사용자 경험 개선에 $5000만 이상을 투자"하는
전략적 전환(단기 수익화보다 사용자 성장 우선)을 명시적으로 발표했고,
조정 EBITDA 마진도 29.5%(FY25)→25%(FY26 가이던스)로 하락을 예고했다.
즉 이건 시장이 근거 없이 겁먹은 게 아니라 **회사 스스로 인정한 근시일
감속**이다 - SE/RMD와 다른 유형으로 취급해야 한다.

**그럼에도 정식분석까지 가는 이유**: 회사 가이던스(매출 $12.0~12.2억,
FY25 실적 $10.376억 대비 +15.7~17.6%)조차도, 스크리닝에서 추정된
시장의 내재성장률(4.19%)보다는 훨씬 높다 - "회사가 감속을 인정했다"와
"그래도 시장가격이 요구하는 성장률보다는 여유가 있다"는 별개 문제이므로
정식 계산으로 확인할 가치가 있다.

**⚠️ 2026-08-05(이 분석 닷새 뒤) Q2 2026 실적발표 예정** - 사용자
증가・마진 추세가 가이던스 궤도대로인지 확인되는 시점이라 판정에 영향을
줄 수 있는 임박한 이벤트. PTC 선례처럼 실적 발표 후 비공식 재확인이
필요할 수 있음을 미리 기록해둔다.

원자료: 전부 SEC EDGAR as-filed 10-K에서 직접 추출(2026-07-31 조회).
  FY2025 10-K(CIK 1562088, accession 0001628280-26-012494) R3/R5/R7
  FY2022 10-K(accession 0001562088-23-000052) R5/R7 (FY2020~2022)
시가총액: stockanalysis.com 2026-07-31 조회 $6.22B(전일종가 $140.17,
52주 고점 $544 대비 -75% 이상, YoY -59.0%).

실행: python3 scripts/analyze_duol_2026_08_01.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.pipeline import AnalysisInputs, run_analysis, save_ledger

K = 1_000  # 원자료가 '천 달러' 단위

# ── SEC EDGAR as-filed 실측 (단위: USD, 원 단위) ────────────────────────
REVENUE = {
    2020: 161696 * K, 2021: 250772 * K, 2022: 369495 * K,
    2023: 531109 * K, 2024: 748024 * K, 2025: 1037589 * K,
}
OPERATING_INCOME = {
    2020: -16011 * K, 2021: -60007 * K, 2022: -65195 * K,
    2023: -13259 * K, 2024: 62595 * K, 2025: 135570 * K,
}
OPERATING_CASHFLOW = {
    2020: 17708 * K, 2021: 9170 * K, 2022: 53656 * K,
    2023: 153614 * K, 2024: 285513 * K, 2025: 387823 * K,
}
CAPEX = {
    2020: 3376 * K, 2021: 3586 * K, 2022: 5562 * K,
    2023: 3191 * K, 2024: 12116 * K, 2025: 18096 * K,
}

# 재무상태표 (FY2025 10-K R3, 2025-12-31 기준) - 무차입 경영
CASH = 1036389 * K
SHORT_TERM_INVESTMENTS = 104078 * K
TOTAL_DEBT = 0
NET_DEBT = TOTAL_DEBT - CASH - SHORT_TERM_INVESTMENTS   # 순현금(부채 전혀 없음)

DA_2025 = 14391 * K
EBITDA = OPERATING_INCOME[2025] + DA_2025

MARKET_CAP = 6.22e9
RF = 0.0447


def build_inputs() -> AnalysisInputs:
    return AnalysisInputs(
        ticker="DUOL",
        company_name="Duolingo, Inc.",
        revenue_by_year=REVENUE,
        operating_income_by_year=OPERATING_INCOME,
        operating_cashflow_by_year=OPERATING_CASHFLOW,
        capex_by_year=CAPEX,
        market_cap=MARKET_CAP,
        net_debt=NET_DEBT,
        ebitda=EBITDA,
        risk_free_rate=RF,

        # v3.24(2026-08-02 방법론 감사 권고 #3): 향후 실현수익률 검증 전제조건.
        price_at_analysis=140.17,
        currency="USD",

        # v3.23(2026-08-01 방법론 감사 Critical-1): SBC 병기 교차검증.
        # SEC 10-K R7 현금흐름표 "Stock-based compensation expense" FY2025 실측.
        sbc_by_year={2025: 137437 * K},

        competitor_threat_weights=[0.30, 0.15, 0.10],
        market_share_trend_pp_per_year=-1.0,
        active_antitrust_or_regulatory_case=False,
        demand_sensitivity_pct=0.20,
        subjective_input_basis=(
            "범용 AI 챗봇(ChatGPT 등) 0.30(2026-07 WebSearch로 확인: "
            "'AI가 언어학습앱 수요를 대체할 것'이 주가급락의 핵심 서사 - "
            "무료로 대화연습이 가능해 Duolingo의 핵심가치제안을 직접 위협. "
            "다만 Duolingo 자체도 Duolingo Max(GPT-4 기반 AI튜터 기능)를 "
            "제품에 내재화해 대응 중이라 완전한 대체재는 아님[추정치]). "
            "Babbel/Busuu 등 구독형 경쟁앱 0.15(시장점유율은 Duolingo가 "
            "여전히 압도적 1위). Rosetta Stone(IXL Learning 계열) 0.10. "
            "market_share_trend=-1.0pp: AI발 대체 우려를 반영해 소폭 "
            "음수로 설정하되, 실제 DAU/MAU 지표는 계속 성장 중이라는 점과 "
            "균형 - 극단적 음수는 아직 근거 부족[추정치]. "
            "active_antitrust_or_regulatory_case=False: 2026-07 WebSearch로 "
            "확인한 현재 진행 중인 반독점・규제조사 없음. demand_sensitivity"
            "=0.20: 교육용 구독앱은 경기민감도가 낮은 편(습관재+저가구독)이나 "
            "가처분소득 위축 시 무료버전으로의 이탈 가능성 있어 완전한 "
            "비민감군은 아님[추정치]."
        ),

        model_used="two_stage",
        model_choice_reason=(
            "⚠️핵심 판단: Duolingo는 FY2020~2025 5년간 매출이 6.4배(연 "
            "35~55%) 성장한 전형적 고성장기였으나, 2026-02-27 발표한 "
            "FY2026 가이던스에서 bookings 성장률을 10~12%로 명시적으로 "
            "낮췄다(무료사용자 경험에 $5000만+ 투자하는 전략적 전환, "
            "조정EBITDA마진도 29.5%->25% 하락 예고) - 이는 KEYS/VRT처럼 "
            "'시장이 아직 못 따라온 가속'이 아니라 정반대로 '회사가 스스로 "
            "인정한 감속'이다. 명시적 고성장구간 이후 정상화를 모델링하는 "
            "two_stage가 이 전환 시점에 이론적으로 부합한다고 판단 - "
            "실행 후 모델괴리를 보고 재검토할 것(GWRE/KLAC/VRT/KEYS/SE/RMD와 "
            "동일 절차). 첫 분석이라 대조할 과거 기록 없음."
        ),

        # v3.24+(2026-08-02, S등급 4종목 중 3종목 심층조사): 원분석에는 없던
        # 사실 확인 - 주가 66~80% 하락 구간 내내 내부자 순매도(최근12개월
        # 약 $41M)만 확인되고 매수는 전혀 확인되지 않았으며, 성장서사 과장
        # 의혹을 제기하는 증권소송(조사단계)이 진행 중. OpenAI 자체
        # 스타트업펀드가 투자한 AI네이티브 경쟁사 Speak(ARR $100M, 밸류
        # $1B)가 급성장 중 - 기존 competitor_threat_weights(범용 AI챗봇
        # 0.30/Babbel 0.15/Rosetta 0.10)가 특정하지 못한 새 위협. 다만
        # DAU는 여전히 +21%YoY로 'AI가 사용자를 실제로 대체 중'이라는
        # 증거는 확인 안 됨(유료구독 순증만 급감) - 서사와 실측이 갈리는
        # 미해결 지점으로 남겨둠.
        falsification_conditions=(
            "(1) 2026-08-05 Q2 실적에서 유료구독자 순증이 전분기(30만명) "
            "대비 재차 감소하거나 30만명을 밑돌면(현재 '컴프효과+전략적 "
            "전환' 해석의 근거가 무너짐) AI대체 서사가 실측 데이터로 확인된 "
            "것으로 간주해 판정을 재검토. (2) DAU 성장률이 20%YoY 밑으로 "
            "떨어지거나 top-of-funnel(신규유입) 정체가 다음 분기까지 "
            "이어지면 동일하게 재검토. (3) Speak 등 AI네이티브 경쟁사 "
            "매출/사용자 규모가 Duolingo 대비 유의미한 비중까지 성장하면 "
            "competitor_threat_weights 재산정 필요."
        ),

        data_sources=[
            "SEC EDGAR 10-K FY2025(0001628280-26-012494) R3/R5/R7, as-filed, 2026-07-31 조회",
            "SEC EDGAR 10-K FY2022(0001562088-23-000052) R5/R7 (FY2020~2022)",
            "stockanalysis.com 시가총액 $6.22B, 주가 $140.17(전일종가), 2026-07-31 조회",
            "WebSearch: Duolingo FY2026 bookings/매출/마진 가이던스(2026-02-27 발표), "
            "AI대체 우려 서사, 2026-08-05 Q2 실적발표 예정 확인",
        ],
    )


def main():
    result = run_analysis(build_inputs())
    d, g = result["derived"], result["growth"]
    models = result["implied_growth"]["models"]

    print("=" * 100)
    print(f"DUOL(Duolingo) 정식 분석 결과 ({result['meta']['analyzed_at'][:10]}, 엔진 {result['meta']['engine_version']})")
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
