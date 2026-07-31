"""
ResMed(RMD) 정식 분석 - 2026-07-31.

경위: "계속해서 발굴" 요청 - engine/screener.py로 미분석 후보군 2차 배치
(Rollins/Dexcom/ResMed/Stryker/STERIS, 전부 최근 1년 급락한 헬스케어/
의료기기주)를 훑음. ROL/DXCM/STE/SYK는 매출·FCF 성장은 견조했으나 FCF
수익률이 여전히 낮아(3.2~4.3%) 밸류에이션 기준(내재성장률≤5.5%)에서 전부
탈락 - "많이 떨어졌다"가 "싸다"를 보장하지 않는다는 걸 보여주는 사례.
**ResMed만 B등급 통과**(스크리너 추정 Gap +6.75%p) - 유일하게 FCF수익률
(5.53%)이 밸류에이션 기준을 통과.

회계연도는 매년 6월 30일 종료. 수면무호흡증 CPAP기기 세계 1위. 주가는
52주 저점 부근, YoY -26.1% - GLP-1 비만치료제(Ozempic/Zepbound 등)가
수면무호흡증 환자 자체를 줄여 CPAP 수요를 잠식할 것이라는 시장 우려가
핵심 하락 원인.

**GLP-1 서사 검증(2026-07 WebSearch)**: 실제 210만명 환자 실측 데이터에서는
GLP-1과 PAP치료를 병행하는 환자의 치료 개시율이 오히려 11%p 더 높게
나타났다 - "수요 파괴"가 아니라 "수요 창출"(GLP-1로 병원 방문이 늘어
수면무호흡증 진단・치료 자체가 늘어남) 가능성을 시사. 시장의 우려와 실측
데이터가 상충한다는 점을 그대로 기록해둔다(어느 쪽이 맞는지 이 분석에서
확정하지 않음 - subjective_input에 양쪽 다 명시).

**Philips Respironics 재진입 리스크 - 아직 미실현**: 2021년 대규모 리콜로
Philips가 美 CPAP 시장에서 사실상 퇴출됐고 ResMed가 반사이익으로 점유율을
크게 늘렸다. 2026-01 기준 Philips는 여전히 美 시장에서 기기를 판매하지
못하고 있다(FDA 시정조치 진행 중) - Morgan Stanley는 현재 주가가 "2026년
Philips 가격할인 재진입"이라는 베어케이스를 이미 선반영한 상태라고 평가.
즉 아직 벌어지지 않은 리스크가 이미 가격에 반영돼 있다는 뜻.

원자료: 전부 SEC EDGAR as-filed 10-K에서 직접 추출(2026-07-31 조회).
  FY2025 10-K(CIK 943819, accession 0000943819-25-000035) R3/R5/R9
  FY2022 10-K(accession 0000943819-22-000010) R5/R8 (FY2020~2022)
시가총액: stockanalysis.com 2026-07-31 조회 $30.08B(전일종가 $214.29,
52주 레인지 $180.27~$293.81).

⚠️ 순현금 계산은 stockanalysis.com 수치(FY25 net cash $357.64M)와 SEC
원자료 직접계산($541.16M) 사이에 괴리가 있었다 - SEC 10-K 원자료를
공식값으로 채택했다(집계사이트보다 1차자료 우선 원칙).

실행: python3 scripts/analyze_rmd_2026_07_31.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.pipeline import AnalysisInputs, run_analysis, save_ledger

K = 1_000  # 원자료가 '천 달러' 단위

# ── SEC EDGAR as-filed 실측 (단위: USD, 원 단위, 회계연도 6/30 종료) ────
REVENUE = {
    2020: 2957013 * K, 2021: 3196825 * K, 2022: 3578127 * K,
    2023: 4222993 * K, 2024: 4685297 * K, 2025: 5146327 * K,
}
OPERATING_INCOME = {
    2020: 809659 * K, 2021: 903678 * K, 2022: 1000286 * K,
    2023: 1131871 * K, 2024: 1319893 * K, 2025: 1685363 * K,
}
OPERATING_CASHFLOW = {
    2020: 802255 * K, 2021: 736718 * K, 2022: 351147 * K,
    2023: 693299 * K, 2024: 1401260 * K, 2025: 1751588 * K,
}
CAPEX = {
    2020: 95330 * K, 2021: 102712 * K, 2022: 134835 * K,
    2023: 119672 * K, 2024: 99460 * K, 2025: 89865 * K,
}

# 재무상태표 (FY2025 10-K R3, 2025-06-30 기준)
CASH = 1209450 * K
SHORT_TERM_DEBT = 9900 * K
LONG_TERM_DEBT = 658392 * K
NET_DEBT = (SHORT_TERM_DEBT + LONG_TERM_DEBT) - CASH   # 순현금(음수)

DA_2025 = 198473 * K   # 감가상각+무형자산상각(사용권자산 상각은 별도 제외 - PTC 관행과 동일)
EBITDA = OPERATING_INCOME[2025] + DA_2025

MARKET_CAP = 30.08e9
RF = 0.0447


def build_inputs() -> AnalysisInputs:
    return AnalysisInputs(
        ticker="RMD",
        company_name="ResMed Inc.",
        revenue_by_year=REVENUE,
        operating_income_by_year=OPERATING_INCOME,
        operating_cashflow_by_year=OPERATING_CASHFLOW,
        capex_by_year=CAPEX,
        market_cap=MARKET_CAP,
        net_debt=NET_DEBT,
        ebitda=EBITDA,
        risk_free_rate=RF,

        competitor_threat_weights=[0.25, 0.20],
        market_share_trend_pp_per_year=0.5,
        active_antitrust_or_regulatory_case=False,
        demand_sensitivity_pct=0.15,
        subjective_input_basis=(
            "Philips Respironics 0.25(2021년 대규모 리콜로 美 시장에서 "
            "사실상 퇴출된 역사적 2위 - 2026-01 기준 여전히 美 시장 기기판매 "
            "재개 못함/FDA 시정조치 진행중이나, 재진입 시 가격할인 경쟁이 "
            "촉발될 잠재 리스크는 남아있어 0을 주지 않음), Fisher & Paykel "
            "Healthcare 0.20(뉴질랜드 상장, 마스크・가습기 부문에서 실제 "
            "경쟁 중인 활성 경쟁자). 둘 다 2026-07 WebSearch로 확인 - "
            "[추정치]. market_share_trend=+0.5pp: Philips 부재가 지속되며 "
            "ResMed의 시장 리더십이 현재는 안정적으로 유지되는 중이나, "
            "Philips 재진입이 임박했다는 근거는 아직 없어 과도하게 낙관하지 "
            "않고 완만한 값으로 설정[추정치]. active_antitrust_or_"
            "regulatory_case=False: 2026-07 WebSearch로 현재 진행 중인 "
            "반독점・규제조사는 확인 안됨(Philips 리콜은 ResMed가 아닌 "
            "경쟁사 건). demand_sensitivity=0.15: 수면무호흡증 치료기기는 "
            "만성질환 관리・소모품(마스크 교체 등) 매출 비중이 높아 경기 "
            "사이클과 상대적으로 무관 - GWRE/PTC(0.22~0.25)보다 낮게 설정. "
            "**단, 이 낮은 수치는 GLP-1발 구조적 수요치환 리스크를 포착하지 "
            "못한다** - 이는 경기순환이 아니라 치료 패러다임 전환 리스크라 "
            "cyclicality 축으로 반영이 안 되는 별도 항목이다. 2026-07 "
            "WebSearch로 확인한 실측 데이터(환자 210만명 기준 GLP-1+PAP "
            "병행환자의 치료개시율이 오히려 +11%p 높음 - '수요파괴'보다 "
            "'수요창출' 가능성)와 시장의 우려가 상충한다는 점을 그대로 "
            "기록해둔다 - 이 분석에서 어느 쪽이 맞는지 판정하지 않는다."
        ),

        model_used="two_stage",
        model_choice_reason=(
            "ResMed는 FY2020~2025 전 구간 흑자를 유지했고 최근 3개년 "
            "영업이익 성장이 매출성장보다 빠른(FY24->FY25 매출 +9.84%, "
            "영업이익 +27.7%) 마진확장 국면에 있다 - 명시적 성장기간 "
            "이후 정상화를 모델링하는 two_stage가 이 궤적에 이론적으로 "
            "부합한다고 판단. 첫 분석이라 대조할 과거 기록 없음 - 모델괴리가 "
            "크면 GWRE/KLAC/VRT/KEYS/SE와 동일 절차로 재검토할 것(아래 "
            "실행결과 참고)."
        ),

        data_sources=[
            "SEC EDGAR 10-K FY2025(0000943819-25-000035) R3/R5/R9, as-filed, 2026-07-31 조회",
            "SEC EDGAR 10-K FY2022(0000943819-22-000010) R5/R8 (FY2020~2022)",
            "stockanalysis.com 시가총액 $30.08B, 주가 $214.29(전일종가), 2026-07-31 조회",
            "WebSearch: ResMed GLP-1 실측 데이터(210만명), Philips Respironics 美 재진입 여부,"
            " FY2026 가이던스 확인",
        ],
    )


def main():
    result = run_analysis(build_inputs())
    d, g = result["derived"], result["growth"]
    models = result["implied_growth"]["models"]

    print("=" * 100)
    print(f"RMD(ResMed) 정식 분석 결과 ({result['meta']['analyzed_at'][:10]}, 엔진 {result['meta']['engine_version']})")
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
