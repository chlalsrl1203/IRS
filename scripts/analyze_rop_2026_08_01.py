"""
Roper Technologies(ROP) 재분석 - 2026-08-01.

경위: "전체 종목 매수 순위" 마스터 랭킹을 만들다가 ROP가 CLAUDE.md에
명시된 실제 사고 사례("VRSN, ROP 종목에서 서로 다른 세션이 같은 종목을
중복 분석하는 사고")의 당사자임을 확인했다. 트래커에 같은 날(2026-07-18,
v3.13) 서로 다른 판정을 내린 기록이 3건 남아있다:
  (1) DRS44.56 / RAR+0.408 / 판정 저평가가능성
  (2)(3) DRS49.8 / RAR+0.335 / 판정 적정가/경계선 (동일 기록 2부)
ledger가 전혀 없어 어느 쪽이 맞는지 판단할 근거가 없었다 - SEC EDGAR
원자료로 처음부터 다시 분석해 이 상충을 해소한다.

산업용 소프트웨어·계측기기 니치리더 인수합병(M&A) 지주회사. 애널리스트
컨센서스 Buy, 목표가 상승여력 +24.69%(2026-07 WebSearch 확인) - 이
프로젝트의 다른 최근 후보들과 달리 '급락주 공포과잉' 서사가 아니라
초기 큐 기반 체계적 커버리지 대상이었다.

**M&A 중심 성장모델 - 유기적/비유기적 분리 미실시**: ROP는 니치리더
기업 인수가 핵심 성장전략이다(FY2025 한 해만 인수에 $3,290M 지출).
CLAUDE.md의 GEN 사례(M&A가 CAGR 구간 양끝에 걸리면 통계적으로 상쇄돼
숫자가 안 튀어 보일 수 있음) 경고가 원칙적으로 적용되나, 세그먼트별
유기적성장 분리는 시간 제약상 이번 재분석에서는 수행하지 못했다 -
data_limitations에 명시. 매출 자체는 과거 매각한 산업/RF기술 부문을
제외한 계속영업 기준으로 이미 재작성돼 있어(FY2022 10-K 재무제표
기준) 최소한 '매각으로 인한 구간단절'은 없다.

⚠️ **FY2022 OCF 일회성 왜곡 확인**: FY2022 계속영업 현금흐름이 $606.6M
으로 전후년도(2021년 $1,655.8M, 2023년 $2,035.1M) 대비 급감했는데,
원인은 영업활동이 아니라 자산매각차익에 대한 일회성 세금납부
($953.8M, 2021년 대규모 사업부 매각 관련)다. 다만 이 값은 3y FCF
CAGR의 기준연도(2022)에 해당하는데, realistic_growth_estimate()가
FCF CAGR과 매출가중평균 중 min()을 취하므로 3y FCF CAGR이 왜곡돼
과대추정되더라도 5y FCF CAGR(기준연도 2020, 왜곡 없음)이나 매출
성장률이 대신 채택될 가능성이 높다 - 실행결과에서 확인.

원자료: 전부 SEC EDGAR 10-K as-filed에서 직접 추출(2026-08-01 조회).
  FY2025 10-K(CIK 882835, accession 0000882835-26-000009) R3/R5/R9
  FY2022 10-K(accession 0000882835-23-000016) R5/R10 (FY2020~2022,
  계속영업 기준으로 재작성된 수치)
시가총액: stockanalysis.com 2026-07-31 조회 $38.77B(주가 $391.97).

실행: python3 scripts/analyze_rop_2026_08_01.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.pipeline import AnalysisInputs, run_analysis, save_ledger

M = 1_000_000

# ── SEC EDGAR as-filed 실측 (단위: USD, 원 단위, 계속영업 기준) ─────────
REVENUE = {
    2020: 4022.4 * M, 2021: 4833.8 * M, 2022: 5371.8 * M,
    2023: 6177.8 * M, 2024: 7039.2 * M, 2025: 7902.5 * M,
}
OPERATING_INCOME = {
    2020: 1082.9 * M, 2021: 1241.2 * M, 2022: 1524.5 * M,
    2023: 1745.2 * M, 2024: 1996.8 * M, 2025: 2235.4 * M,
}
OPERATING_CASHFLOW = {
    2020: 1123.2 * M, 2021: 1655.8 * M, 2022: 606.6 * M,  # 2022 일회성 세금납부로 급감(본문 참고)
    2023: 2035.1 * M, 2024: 2393.2 * M, 2025: 2540.3 * M,
}
# capex = 유형자산투자 + 자본화 소프트웨어개발비
CAPEX = {
    2020: (24.7 + 17.7) * M, 2021: (28.5 + 29.7) * M, 2022: (40.1 + 30.2) * M,
    2023: (68.0 + 40.0) * M, 2024: (66.0 + 45.0) * M, 2025: (47.4 + 57.3) * M,
}

# 재무상태표 (FY2025 10-K R3, 2025-12-31 기준)
CASH = 297.4 * M
CURRENT_DEBT = 705.2 * M
LONG_TERM_DEBT = 8595.8 * M
NET_DEBT = CURRENT_DEBT + LONG_TERM_DEBT - CASH

DA_2025 = 39.8 * M + 858.4 * M       # PP&E감가상각 + 무형자산상각(대규모 M&A 영업권 상각 포함)
EBITDA = OPERATING_INCOME[2025] + DA_2025

MARKET_CAP = 38.77e9
RF = 0.0447


def build_inputs() -> AnalysisInputs:
    return AnalysisInputs(
        ticker="ROP",
        company_name="Roper Technologies, Inc.",
        revenue_by_year=REVENUE,
        operating_income_by_year=OPERATING_INCOME,
        operating_cashflow_by_year=OPERATING_CASHFLOW,
        capex_by_year=CAPEX,
        market_cap=MARKET_CAP,
        net_debt=NET_DEBT,
        ebitda=EBITDA,
        risk_free_rate=RF,

        # v3.23(2026-08-01 방법론 감사 Critical-1): SBC 병기 교차검증.
        # SEC 10-K R9 현금흐름표 "Non-cash stock compensation" FY2025 실측.
        sbc_by_year={2025: 166.3 * M},

        competitor_threat_weights=[0.15, 0.15, 0.10],
        market_share_trend_pp_per_year=0.0,
        active_antitrust_or_regulatory_case=False,
        demand_sensitivity_pct=0.18,
        subjective_input_basis=(
            "Danaher/Illinois Tool Works 0.15(유사한 다각화 산업재 인수합병 "
            "전략 추구, 인수대상 니치기업을 두고 경쟁 가능), Constellation "
            "Software 0.15(소프트웨어 지주회사 모델이 유사하나 사업영역 "
            "겹침은 제한적), Ametek 0.10(계측기기 부문 일부 겹침). Roper는 "
            "매출의 대부분을 수백개 니치시장 1~2위 자회사에서 얻어 개별 "
            "시장 내 경쟁강도는 낮은 편[추정치]. market_share_trend=0.0pp: "
            "니치시장이 매우 파편화돼 있어 점유율 추세라는 개념 자체가 "
            "단일 지표로 의미가 약함 - 중립값 부여[추정치]. "
            "demand_sensitivity=0.18: 산업/의료/기술 SW 포트폴리오가 "
            "다각화돼 있어 특정 경기사이클에 대한 민감도가 낮은 "
            "편(PGR·GWRE와 유사 수준)[추정치]."
        ),

        model_used="two_stage",
        model_choice_reason=(
            "ROP는 M&A 중심으로 매출이 꾸준히 확대되는 궤적(2020년 $4.0B "
            "-> 2025년 $7.9B, 2배)이나 SE/TTD/DUOL류의 극단적 고성장은 "
            "아니다. FY2025 한 해 인수지출($3.29B)이 시총의 8.5%에 "
            "달할 만큼 M&A가 상시적 성장동력이라 명시적 고성장기 이후 "
            "정상화를 가정하는 two_stage보다 정상마진을 유지하는 "
            "single_stage가 이 비즈니스모델에 더 맞을 수도 있으나, 이 "
            "세션의 다른 종목들과의 비교가능성을 위해 우선 two_stage로 "
            "실행하고 모델괴리를 확인해 재검토한다 - VRSN/GWRE(single_"
            "stage 채택 선례)와 유사한 상황일 가능성. ⚠️2022년 OCF가 "
            "일회성 세금납부로 급감했으나 3y FCF CAGR 기준연도라 왜곡 "
            "가능성 있음(본문 참고) - 결과의 fcf_conservatism_applied "
            "여부로 실제 영향 확인할 것."
        ),

        data_sources=[
            "SEC EDGAR 10-K FY2025(0000882835-26-000009) R3/R5/R9, as-filed, 2026-08-01 조회",
            "SEC EDGAR 10-K FY2022(0000882835-23-000016) R5/R10 (FY2020~2022, 계속영업 기준 재작성치)",
            "stockanalysis.com 시가총액 $38.77B(주가 $391.97), 2026-07-31 조회",
            "WebSearch: ROP 애널리스트 컨센서스(Buy, 목표가 +24.69%), 경쟁사 구도 확인(2026-07)",
            "Notion 트래커 ROP 상충기록 3건(v3.13, 2026-07-18) - 이번 재분석의 해소 대상",
        ],
    )


def main():
    result = run_analysis(build_inputs())
    d, g = result["derived"], result["growth"]
    models = result["implied_growth"]["models"]

    print("=" * 100)
    print(f"ROP 재분석 결과 ({result['meta']['analyzed_at'][:10]}, 엔진 {result['meta']['engine_version']})")
    print("=" * 100)
    print(f"  CAGR 기준연도    : {d['cagr_5y_base_year']}년 ({d['cagr_5y_span']}년 구간, override 미사용)")
    rev_10y_str = "N/A" if d['revenue_cagr_10y'] is None else f"{d['revenue_cagr_10y']*100:.2f}%"
    print(f"  매출 CAGR        : 3y {d['revenue_cagr_3y']*100:.2f}% / "
          f"{d['cagr_5y_span']}y {d['revenue_cagr_5y']*100:.2f}% / 10y {rev_10y_str}")
    print(f"  FCF CAGR         : {d['fcf_cagr_5y']*100:.2f}%   (FCF0 {d['fcf0']/1e9:.3f}B)")
    print(f"  최악 YoY 매출    : {d['worst_yoy_revenue_growth']*100:.2f}% ({d['worst_yoy_year']}년)")
    print(f"  순부채/EBITDA    : {d['net_debt_to_ebitda']:.3f}배")
    print()
    print(f"  DRS              : {result['drs']['score']:.2f}   (v3.13 원기록: 44.56 / 49.80(중복))")
    for k, v in result["drs"]["components"].items():
        print(f"      {k:24} {v:5.2f}")
    print(f"  Lynch 유형       : {result['lynch']['used']}")
    print(f"  구조적 할인      : {g['structural_discount_pct']*100:.2f}%")
    if g["breakdown"].get("fcf_conservatism_applied"):
        print(f"  FCF 보수화 적용  : {g['breakdown']['fcf_conservatism_applied']}")
    print(f"  Realistic Growth : {g['realistic_growth']*100:.2f}%")
    ss_str = "N/A" if models['single_stage'] is None else f"{models['single_stage']*100:.2f}%"
    ts_str = "N/A" if models['two_stage'] is None else f"{models['two_stage']*100:.2f}%"
    print(f"  Implied Growth   : single_stage {ss_str} / two_stage {ts_str} "
          f"-> 채택 {result['implied_growth']['value']*100:.2f}% ({result['implied_growth']['model_used']})")
    if models.get("divergence") is not None:
        print(f"  모델 괴리        : {models['divergence']*100:.2f}%p")
    print(f"  Expectation Gap  : {result['expectation_gap']*100:+.2f}%p   (v3.13 원기록: +6.04%p / +5.73%p)")
    print(f"  RAR              : {result['rar']:+.4f}   (v3.13 원기록: +0.408 / +0.335)")
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
