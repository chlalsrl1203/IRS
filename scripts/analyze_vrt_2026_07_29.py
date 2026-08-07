"""
Vertiv Holdings Co(VRT) 정식 분석 - 2026-07-29.

경위: 사용자 요청에 의한 비큐(ad-hoc) 분석(공식 83개 큐에는 없음, BKNG/PDD/
TCOM 등과 동일 범주). 데이터센터 전력(UPS・배전)・열관리(공랭・수랭) 인프라의
선두업체 - AI 데이터센터 투자 붐의 대표적 '피켈・삽' 수혜주.

⚠️ **분석 당일(2026-07-29) Q2 2026 실적발표 직후 주가 -17.3% 폭락** - 실적
자체는 컨센서스 상회했으나(조정EPS $1.52 vs 예상 $1.42~1.43, +6.4%), 매출이
컨센서스 미달($3.27B vs 예상 $3.38~3.39B, -3.4%, 그래도 YoY는 +24.1%
성장)했고, 이 매출 미달이 전년 가이던스 상향(FY26 EPS $6.65~6.75, 매출
$13.8~14.2B로 상향)을 압도해 주가가 급락했다(2026-07-30 WebSearch로 확인).
경영진은 미달 원인을 수요둔화가 아니라 "일시적 공급망 정체 + 대형
다단계프로젝트의 타이밍"으로 설명(AI/범용컴퓨팅 수요는 "계속 강화"된다고
언급). 시가총액은 이 폭락 반영 종가($223.04, 전일比 -17.3%) 기준 사용 -
직전 52주 고점($376.15, 2026-05-14)대비로는 이미 -40.7% 조정된 상태.

⚠️ **FY2022 영업활동현금흐름 적자 - BKNG류 함정, 6개년 확보로 회피**:
FY2022 OCF가 -$152.8M(운전자본 -$449.2M 악화, 당시 공급망위기・원자재 인플레
영향)로 FCF -$252.8M까지 깊은 적자였다. 다행히 회사가 2020년 SPAC합병
(GS Acquisition Holdings Corp) 직후부터 현재까지 확보 가능한 최장 구간
(FY2020~2025, 6개년, pipeline.py 최소요건 정확히 충족)을 쓰니 기본 5년
기준연도가 FY2020(2025-5=2020)으로 계산돼 FY2022를 비켜간다 - GWRE와
동일한 패턴(짧은 조회창이었다면 걸렸을 함정을 데이터 확보로 회피).

⚠️ **10년 데이터 원천적으로 불가능**: VRT는 2020-02 SPAC합병으로 상장된
지 6년밖에 안 돼 2019년 이전은 다른 법인격(GS Acquisition Holdings Corp,
무자산 SPAC)이라 비교가능한 재무제표 자체가 없다 - 데이터를 더 구해서
해결할 수 있는 문제가 아니라 상장 이력의 구조적 한계임을 명시.

원자료: 전부 SEC EDGAR as-filed 10-K에서 직접 추출(2026-07-29 조회, FY2020
~2025, 6개년).
  FY2025 10-K(0001674101-26-000008) R3/R5/R7
  FY2022 10-K(0001628280-23-005248) R3/R7 (FY2020~2022, OCF적자 구간 포함)
시가총액: 2026-07-29 종가($223.04, Q2 실적발표 당일 -17.3% 급락 반영) 기준 $85.67B.

실행: python3 scripts/analyze_vrt_2026_07_29.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.pipeline import AnalysisInputs, run_analysis, save_ledger

M = 1_000_000

# ── SEC EDGAR as-filed 실측 (단위: USD, 원 단위) ────────────────────────
REVENUE = {
    2020: 4370.6 * M, 2021: 4998.1 * M, 2022: 5691.5 * M,
    2023: 6863.2 * M, 2024: 8011.8 * M, 2025: 10229.9 * M,
}
OPERATING_INCOME = {
    2020: 213.5 * M, 2021: 259.9 * M, 2022: 223.4 * M,
    2023: 872.2 * M, 2024: 1367.4 * M, 2025: 1829.7 * M,
}
OPERATING_CASHFLOW = {
    2020: 208.9 * M, 2021: 210.9 * M,
    2022: -152.8 * M,   # 공급망위기 운전자본 악화(-$449.2M) - 기본기준연도 아님(FY2020)
    2023: 900.5 * M, 2024: 1319.3 * M, 2025: 2113.8 * M,
}
CAPEX = {
    2020: 44.4 * M, 2021: 73.4 * M, 2022: 100.0 * M,
    2023: 127.9 * M, 2024: 167.0 * M, 2025: 220.0 * M,
}

# 재무상태표 (FY2025 10-K R5, 2025-12-31 기준)
CASH = 1728.4 * M
SHORT_TERM_INVESTMENTS = 99.5 * M
SHORT_TERM_DEBT = 20.9 * M
LONG_TERM_DEBT = 2892.1 * M
NET_DEBT = (SHORT_TERM_DEBT + LONG_TERM_DEBT) - (CASH + SHORT_TERM_INVESTMENTS)

DA_2025 = 97.1 * M + 211.5 * M   # 감가상각 + 무형자산상각
EBITDA = OPERATING_INCOME[2025] + DA_2025

MARKET_CAP = 85.67e9   # 2026-07-29 종가($223.04) - Q2 실적발표 당일 -17.3% 급락 반영
RF = 0.0447


def build_inputs() -> AnalysisInputs:
    return AnalysisInputs(
        ticker="VRT",
        company_name="Vertiv Holdings Co",
        revenue_by_year=REVENUE,
        operating_income_by_year=OPERATING_INCOME,
        operating_cashflow_by_year=OPERATING_CASHFLOW,
        capex_by_year=CAPEX,
        market_cap=MARKET_CAP,
        net_debt=NET_DEBT,
        ebitda=EBITDA,
        risk_free_rate=RF,

        competitor_threat_weights=[0.45, 0.30, 0.20],
        market_share_trend_pp_per_year=0.0,
        active_antitrust_or_regulatory_case=False,
        demand_sensitivity_pct=0.45,
        subjective_input_basis=(
            "Schneider Electric 0.45(Dell'Oro Group 기준 VRT와 '사실상 "
            "동률'인 글로벌 시장점유율 1위 경쟁자), Eaton 0.30(전력관리 "
            "전반의 대형 경쟁자), ABB 0.20(전동화・산업 전반에서 일부 중첩). "
            "북미 데이터센터 전력시장 상위5개사(ABB/Schneider/VRT/Eaton/"
            "Mitsubishi Electric)가 약 62% 과점(2026-07 WebSearch, Mordor "
            "Intelligence). VRT는 정밀냉각(precision cooling) 부문에서 "
            "글로벌 점유율 23%로 별도 강세[셋 다 추정치]. market_share_"
            "trend=0.0: Schneider와 '사실상 동률'이라는 근거는 있으나 방향성 "
            "추세 데이터가 없어 중립[추정치]. active_antitrust_or_regulatory_"
            "case=False: 2026-07 WebSearch로 확인 결과 반독점・경쟁당국 "
            "조사는 발견되지 않았다 - 2022년 공급망・인플레이션 공시 관련 "
            "증권집단소송(2022-05 제기, 2023-06 파생소송 추가)이 진행 중이나 "
            "이는 주주소송이지 반독점・시장구조 규제가 아니라 False 유지. "
            "demand_sensitivity=0.45: AI데이터센터 설비투자는 대규모・"
            "다단계 프로젝트 단위로 발주돼 분기별 매출 변동성이 크다 - "
            "실제로 이번 분기(2026-07-29 발표) 매출이 컨센서스에 3.4% "
            "미달해 EPS 서프라이즈에도 주가가 -17.3% 급락했고, FY2022엔 "
            "공급망위기로 OCF 자체가 적자 전환한 실측 이력도 있다. KLAC"
            "(0.38)보다 높은 이 프로젝트 상위권으로 설정 - 다만 회사는 "
            "수요둔화가 아니라 프로젝트 타이밍・공급망 문제로 설명하고 "
            "있어 BKNG류 순수 소비재 재량지출 리스크와는 성격이 다름"
            "[추정치]."
        ),

        model_used="two_stage",
        model_choice_reason=(
            "VRT는 FY2023~2025 3개년 연속 매출 +16~28%, FCF는 거의 매년 "
            "40~65%씩 성장하는 명확한 고성장 국면에 있고, AI데이터센터 "
            "투자사이클이라는 구조적 성장동력이 있어 명시적 성장기간을 "
            "모델링하는 two_stage가 이론적으로 부합한다고 판단했다. "
            "실제 계산 결과 single_stage(8.31%)와 two_stage(16.99%)의 "
            "괴리가 8.68%p로 커서(GWRE 9.03%p·KLAC 12.85%p에 준하는 수준) "
            "GWRE/KLAC와 동일한 절차로 재검토했다 - 다만 이번엔 결론이 "
            "반대다. GWRE/KLAC는 two_stage가 회사 가이던스보다 과도하게 "
            "낙관적이라 single_stage로 전환했지만, VRT는 **정반대**다: "
            "회사의 FY2026 가이던스(매출 $13.8~14.2B, 중간값 $14.0B)는 "
            "FY2025($10.23B) 대비 +36.9% 성장을 시사하는데, 이는 "
            "single_stage가 요구하는 8.31%는 물론이고 Realistic Growth"
            "(18.40%)보다도 훨씬 높다. 즉 single_stage를 쓰면 회사 자체 "
            "가이던스보다 훨씬 비관적인 성장가정으로 밸류에이션하는 "
            "셈이 되어 오히려 부적절하다 - two_stage(16.99%)가 그나마 "
            "가이던스에 더 가깝다. 첫 정식분석이라 대조할 과거 기록은 "
            "없으나, GWRE/KLAC와 같은 원칙(모델선택이 판정을 뒤집을 만큼 "
            "크면 서사가 아니라 실제 가이던스와 더 정합적인 쪽을 선택)을 "
            "일관되게 적용해 two_stage를 유지했다."
        ),

        data_sources=[
            "SEC EDGAR 10-K FY2025(0001674101-26-000008) R3/R5/R7, as-filed, 2026-07-29 조회",
            "SEC EDGAR 10-K FY2022(0001628280-23-005248) R3/R7 (FY2020~2022, OCF적자 구간)",
            "WebSearch: VRT 시가총액/종가 2026-07-29(Google Finance/macrotrends), "
            "Q2 2026 실적발표 및 주가급락 상세(TipRanks/StockStory/Yahoo Finance), "
            "경쟁구도(Dell'Oro/Mordor Intelligence/MarketsandMarkets), "
            "증권집단소송 현황(2022 공급망 공시 관련)",
        ],
    )


def main():
    result = run_analysis(build_inputs())
    d, g = result["derived"], result["growth"]
    models = result["implied_growth"]["models"]

    print("=" * 100)
    print(f"VRT 정식 분석 결과 ({result['meta']['analyzed_at'][:10]}, 엔진 {result['meta']['engine_version']})")
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
