"""
The Trade Desk(TTD) 정식 분석 - 2026-07-31.

경위: "스크리닝 계속" 요청에 응답 - Seeking Alpha "30 for 30"(2026-07-15,
S&P500 중 2026년 -30%+ 하락 30종목) 리스트에서 이미 분석된 종목(ORCL/NKE/
CHTR/PODD/LULU/TYL/ZTS/CSGP/APP)을 제외한 잔여 21종목을 훑음. CRM/ADBE는
2026-07-22 기존 저평가 기록이 아직 유효함을 확인(가격·실적 변동 없음),
INTU/TTD/BSX 3종목이 새로 engine/screener.py 통과(전부 A~B등급) -
**TTD가 이 세션 스크리너 추정 Gap 최대치(+21.33%p)**로 최우선 정식분석
대상.

세계 최대 독립계(walled-garden 미소속) 프로그래매틱 광고 DSP. 주가는
YoY -79.6%(이 세션 발굴 종목 중 최대 낙폭), 52주 고점 대비 그 이상.

**⚠️ 이번에도 순수 '공포과잉'이 아니다(DUOL과 동일 유형)**: WebSearch로
확인한 결과 (1) 2026 Q1 실적발표 시 Q2 가이던스가 전년比 +8% 성장에
불과해(과거 5년 연 25~45% 성장과 대비) 발표 당일 주가 -15% 추가하락,
(2) Amazon DSP가 광고주들이 '주력 플랫폼'으로 꼽는 비중을 늘리며 실제
점유율을 잠식 중, (3) CFO 복수 교체·CRO 이탈 등 임원진 이슈, (4) 대형
광고대행사 그룹의 고객감사(client audit)까지 겹쳐 - DUOL(회사 스스로
가이던스 인하)보다 한 단계 더 나아가 **경영진 이슈까지 겹친 복합
리스크**다.

**그래도 정식분석까지 가는 이유**: 자사주 매입 규모가 이례적이다 -
FY2025 한 해에만 $1.38B(현재 시총 $8.48B의 16.3%에 해당)를 자사주
매입에 투입했다 - 경영진이 현재가를 저평가로 보고 있다는 실질적
신호. 정식 계산으로 시장의 Implied Growth가 회사의 낮아진 가이던스
(+8%)조차에도 못 미치는지 확인할 가치가 있다.

원자료: 전부 SEC EDGAR as-filed 10-K에서 직접 추출(2026-07-31 조회).
  FY2025 10-K(CIK 1671933, accession 0001671933-26-000014) R3/R5/R7
  FY2022 10-K(accession 0001671933-23-000007) R5/R7 (FY2020~2022)
시가총액: stockanalysis.com 2026-07-31 조회 $8.48B(전일종가 반영,
YoY -79.6%).

실행: python3 scripts/analyze_ttd_2026_07_31.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.pipeline import AnalysisInputs, run_analysis, save_ledger

K = 1_000  # 원자료가 '천 달러' 단위

# ── SEC EDGAR as-filed 실측 (단위: USD, 원 단위) ────────────────────────
REVENUE = {
    2020: 836033 * K, 2021: 1196467 * K, 2022: 1577795 * K,
    2023: 1946120 * K, 2024: 2444831 * K, 2025: 2896284 * K,
}
OPERATING_INCOME = {
    2020: 144208 * K, 2021: 124817 * K, 2022: 113654 * K,
    2023: 200480 * K, 2024: 427167 * K, 2025: 589321 * K,
}
OPERATING_CASHFLOW = {
    2020: 405069 * K, 2021: 378513 * K, 2022: 548734 * K,
    2023: 598322 * K, 2024: 739456 * K, 2025: 992721 * K,
}
CAPEX = {
    2020: 74061 * K, 2021: 54804 * K, 2022: 84160 * K,
    2023: 46790 * K, 2024: 98238 * K, 2025: 197011 * K,
}

# 재무상태표 (FY2025 10-K R3, 2025-12-31 기준) - 무차입 경영(재무부채 없음)
CASH = 658175 * K
SHORT_TERM_INVESTMENTS = 644882 * K
TOTAL_DEBT = 0
NET_DEBT = TOTAL_DEBT - CASH - SHORT_TERM_INVESTMENTS

DA_2025 = 115784 * K
EBITDA = OPERATING_INCOME[2025] + DA_2025

MARKET_CAP = 8.48e9
RF = 0.0447


def build_inputs() -> AnalysisInputs:
    return AnalysisInputs(
        ticker="TTD",
        company_name="The Trade Desk, Inc.",
        revenue_by_year=REVENUE,
        operating_income_by_year=OPERATING_INCOME,
        operating_cashflow_by_year=OPERATING_CASHFLOW,
        capex_by_year=CAPEX,
        market_cap=MARKET_CAP,
        net_debt=NET_DEBT,
        ebitda=EBITDA,
        risk_free_rate=RF,

        # v3.23(2026-08-01 방법론 감사 Critical-1): SBC 병기 교차검증.
        # SEC 10-K R7 현금흐름표 "Stock-based compensation expense" FY2025 실측.
        sbc_by_year={2025: 490627 * K},

        competitor_threat_weights=[0.40, 0.20, 0.15],
        market_share_trend_pp_per_year=-2.5,
        active_antitrust_or_regulatory_case=False,
        demand_sensitivity_pct=0.35,
        subjective_input_basis=(
            "Amazon DSP 0.40(2026-07 WebSearch로 확인: 광고주들이 '주력 "
            "플랫폼'으로 Amazon DSP를 꼽는 비중이 실측으로 늘고 있음 - "
            "리테일미디어 데이터 우위를 앞세운 실질적 점유율 잠식, 이 "
            "종목 하락의 핵심 서사). Google DV360/Meta 등 walled garden "
            "0.20(광고예산 자체를 흡수하는 간접경쟁). 대행사 자체거래데스크 "
            "(in-house trading desk) 0.15. 전부 [추정치]지만 Amazon 위협은 "
            "업계 다수 보도로 뒷받침됨. market_share_trend=-2.5pp: 위 "
            "Amazon 점유율 잠식 실측 보도를 반영해 이 세션 최대 음수값으로 "
            "설정 - DUOL(-1.0pp)보다 근거가 구체적이라 더 큰 음수 "
            "부여[추정치]. active_antitrust_or_regulatory_case=False: "
            "반독점 조사는 확인 안 됐으나 대형 광고대행사그룹의 고객감사"
            "(client audit)가 진행 중이라는 점은 별도 리스크로 존재 - "
            "규제소송은 아니라 False 유지하되 데이터한계에 명시. "
            "demand_sensitivity=0.35: 디지털광고 예산은 경기민감도가 "
            "뚜렷한 편(경기둔화시 광고비 우선삭감) - GWRE/PTC(0.22~0.25)"
            "보다 높고 KLAC(0.38)에 근접[추정치]."
        ),

        model_used="two_stage",
        model_choice_reason=(
            "⚠️핵심 판단: TTD는 FY2020~2025 5년간 매출이 3.5배(연 20%대"
            "중후반) 성장한 고성장기였으나, 2026 Q1 실적발표에서 제시한 "
            "Q2 가이던스가 전년比 +8%에 불과해(DUOL과 동일하게 회사 "
            "스스로의 근시일 감속 인정) 발표당일 주가 -15% 추가하락했다. "
            "여기에 Amazon DSP 점유율 잠식, CFO 복수교체, CRO 이탈, "
            "대형대행사 고객감사까지 겹쳐 DUOL보다 리스크가 다층적이다. "
            "명시적 고성장구간 이후 정상화를 모델링하는 two_stage가 이 "
            "감속국면에 이론적으로 부합한다고 판단 - 실행 후 모델괴리를 "
            "보고 재검토할 것(GWRE/KLAC/VRT/KEYS/SE/RMD/DUOL과 동일 절차). "
            "첫 분석이라 대조할 과거 기록 없음."
        ),

        # v3.24+(2026-08-03, S등급 나머지 4종목 심층조사): 원분석에는 없던
        # 가장 심각한 신규 발견 - **연방 증권사기 집단소송이 기각동의 기각**
        # (2026-03-17)으로 본안 진행 중이며, CEO Jeff Green·전 CFO·전
        # 최고전략책임자를 Kokai 롤아웃 관련 허위진술 및 **내부자거래 혐의로
        # 직접 지목**하고 있다(소송기간 2023-11-15~2025-08-08). CFO가 14개월
        # 새 4명 교체, CRO는 7개월만에 이탈 후 후임 미충원. Publicis와의
        # 수수료 투명성 분쟁은 2026-06-12 해소됐으나 Omnicom 건은 불명확.
        # Amazon DSP 점유율이 15개월새 10%→20%로 배증, TTD는 "시장평균
        # 속도로만 성장"(점유율 방어 실패)이 확인됨. 다만 CEO가 2026-03-04
        # 저점 부근에서 $148M 개인자금으로 직접매수한 사실은 진성 강세신호.
        falsification_conditions=(
            "(1) 증권소송에서 불리한 판결이나 거액 화해금 합의가 나오면 "
            "이 판정은 재검토 대상. (2) 12개월 내 5번째 CFO/CRO급 교체가 "
            "발생하면 재검토. (3) 미국 매출성장률이 FY2027까지 낮은 한자릿수 "
            "밑으로 재차 둔화되거나 회복 실패하면(Amazon DSP 잠식이 구조적 "
            "임을 뜻함) 재검토. (4) 2026-08-06 Q2 실적에서 가이던스 "
            "$750M을 다시 하회하면 즉시 재검토."
        ),

        data_sources=[
            "SEC EDGAR 10-K FY2025(0001671933-26-000014) R3/R5/R7, as-filed, 2026-07-31 조회",
            "SEC EDGAR 10-K FY2022(0001671933-23-000007) R5/R7 (FY2020~2022)",
            "stockanalysis.com 시가총액 $8.48B, 2026-07-31 조회",
            "WebSearch: Seeking Alpha '30 for 30'(2026-07-15) 리스트, TTD 2026 Q1 실적/"
            "Q2가이던스(+8%YoY, 발표당일 -15%), Amazon DSP 경쟁구도, 임원진 이탈 확인",
        ],
    )


def main():
    result = run_analysis(build_inputs())
    d, g = result["derived"], result["growth"]
    models = result["implied_growth"]["models"]

    print("=" * 100)
    print(f"TTD(The Trade Desk) 정식 분석 결과 ({result['meta']['analyzed_at'][:10]}, 엔진 {result['meta']['engine_version']})")
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
