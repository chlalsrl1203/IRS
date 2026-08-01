"""
Workday(WDAY) 정식 분석 - 2026-07-31.

경위: "계속실행" 요청. Barchart "AI Disruption Overblown! 4 Software Stocks
to Buy on the Dip" 기사의 나머지 2종목(CRM/MNDY 기존 완료)을 확인 -
Workday(WDAY)와 ServiceNow(NOW). 둘 다 실제로 큰 폭 하락(WDAY YoY -50.22%,
NOW YoY -46.46%) 확인 후 screener.py 통과 여부 테스트: **WDAY만 통과**
(A등급, 추정 Gap +11.92%p). NOW는 시가총액이 커서($115B) FCF수익률이
3.98%에 그쳐 스크리너 임계치(내재성장 5.5% 이하 -> FCF수익률 4.63% 이상
필요)를 못 넘어 탈락 - "많이 떨어졌다"와 "여전히 비싸다"는 별개라는 걸
보여주는 사례. WDAY만 정식분석 진행.

세계 최대 클라우드 HR/재무관리(HCM/ERP) SaaS 중 하나. 주가는 YoY -50.22%,
52주 고점($249.85, 2025-09-29) 대비 저점($110.36, 2026-04-09)까지 -55.8%.

**공포과잉 여부 판단**: 회사 펀더멘털 자체는 견고 - FY2026(2026-01-31
마감) 매출 $9,552M(+13.09%), 영업이익 $721M으로 5년 연속 흑자전환 후 최대
실적, FCF $2,777M(사상 최대). Oracle/SAP 등 대형 경쟁사 대비 고객
전환비율도 우위(ADP 대비 순전입 2:1, Taleo 대비 8.9배 등). 다만 (1) 매출
성장률 자체가 5년 전 20%대에서 13%대로 자연 감속 중이고, (2) AI-네이티브
신생 재무/HR 자동화 스타트업이라는 정성적 위협이 부상 중이며, (3)
**Mobley v. Workday** - AI 채용스크리닝 도구의 인종·연령·장애 차별 소송이
2026-06-22 법원이 핵심 청구를 기각하지 않고 본안심리로 진행 허용, 집단소송
opt-in 진행 중(2026-03-07 마감) - 아직 배상액이 확정되지 않은 진행중인
소송 리스크가 있다. 이 소송은 반독점/규제 사건이 아니라 고용차별
소송이므로 `active_antitrust_or_regulatory_case`에는 반영하지 않되(필드
의도와 다름), data_limitations에 별도로 명시해 정성적 리스크로 남긴다.

원자료: 전부 SEC EDGAR 10-K as-filed에서 직접 추출(2026-07-31 조회, curl
직접 fetch).
  FY2026 10-K(CIK 1327811, accession 0001327811-26-000014) R3/R5/R10
  FY2024 10-K(accession 0001327811-24-000044) R5/R10 (FY2023/2022 검증)
  FY2022 10-K(accession 0001327811-22-000030) R5/R10 (FY2021 데이터)
시가총액: stockanalysis.com 2026-07-31 조회 $39.60B(전일종가 $160.34 반영).

실행: python3 scripts/analyze_wday_2026_07_31.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.pipeline import AnalysisInputs, run_analysis, save_ledger

M = 1_000_000  # 원자료가 '백만 달러' 단위 (일부는 천달러->백만달러 환산 후 기록)

# ── SEC EDGAR as-filed 실측 (단위: USD, 원 단위, 회계연도는 1/31 마감) ──
REVENUE = {
    2021: 4317.996 * M, 2022: 5138.798 * M, 2023: 6216 * M,
    2024: 7259 * M, 2025: 8446 * M, 2026: 9552 * M,
}
OPERATING_INCOME = {
    2021: -248.599 * M, 2022: -116.450 * M, 2023: -222 * M,
    2024: 183 * M, 2025: 415 * M, 2026: 721 * M,
}
OPERATING_CASHFLOW = {
    2021: 1268.441 * M, 2022: 1650.704 * M, 2023: 1657 * M,
    2024: 2149 * M, 2025: 2461 * M, 2026: 2939 * M,
}
# capex = 일반 유형자산투자 + 자가소유 부동산프로젝트(있는 연도만, R10 investing activities)
CAPEX = {
    2021: 253.380 * M + 6.116 * M,
    2022: 264.267 * M + 171.501 * M,
    2023: 360 * M + 4 * M,
    2024: 228 * M + 4 * M,
    2025: 269 * M,
    2026: 162 * M,
}

# 재무상태표 (FY2026 10-K R3, 2026-01-31 기준)
CASH = 1501 * M
SHORT_TERM_INVESTMENTS = 3942 * M
TOTAL_DEBT = 2987 * M  # Debt, noncurrent
NET_DEBT = TOTAL_DEBT - CASH - SHORT_TERM_INVESTMENTS

DA_2026 = 347 * M
EBITDA = OPERATING_INCOME[2026] + DA_2026

MARKET_CAP = 39.60e9
RF = 0.0447


def build_inputs() -> AnalysisInputs:
    return AnalysisInputs(
        ticker="WDAY",
        company_name="Workday, Inc.",
        revenue_by_year=REVENUE,
        operating_income_by_year=OPERATING_INCOME,
        operating_cashflow_by_year=OPERATING_CASHFLOW,
        capex_by_year=CAPEX,
        market_cap=MARKET_CAP,
        net_debt=NET_DEBT,
        ebitda=EBITDA,
        risk_free_rate=RF,

        # v3.23(2026-08-01 방법론 감사 Critical-1): SBC 병기 교차검증.
        # SEC 10-K R5 손익계산서 각주 "Total share-based compensation expense"
        # FY2026(2026-01-31 마감, 이 스크립트의 최근연도 키) 실측.
        sbc_by_year={2026: 1626 * M},

        competitor_threat_weights=[0.20, 0.15, 0.15],
        market_share_trend_pp_per_year=-0.5,
        active_antitrust_or_regulatory_case=False,
        demand_sensitivity_pct=0.20,
        subjective_input_basis=(
            "Oracle Fusion Cloud/SAP SuccessFactors 등 대형 ERP/HCM 통합업체 "
            "0.20(WebSearch 확인: 실제 고객전환 데이터는 Workday가 ADP 대비 "
            "2:1, Taleo 대비 8.9배 우위로 나타나 위협도를 TTD의 Amazon DSP "
            "0.40만큼 크게 잡지 않음). ADP/UKG/Ceridian Dayforce 등 HR전문 "
            "경쟁사 0.15. AI-네이티브 신생 재무자동화 스타트업(자율결산·"
            "에이전틱 재무보고 등 신규 카테고리 창출 중) 0.15 - 아직 실측 "
            "점유율 데이터는 없으나 신흥 위협으로 분류. 전부 [추정치]. "
            "market_share_trend=-0.5pp: 실측 고객전환 데이터 자체는 "
            "Workday에 유리하나(순전입 우위), 매출성장률이 5년 전 20%대에서 "
            "13%대로 자연감속 중이고 AI-네이티브 카테고리 재편 초기 국면 "
            "이라는 정성적 불확실성을 반영해 소폭 음수만 부여 - MNDY(-1.0pp)"
            "보다는 낙관적[추정치]. demand_sensitivity=0.20: 엔터프라이즈 "
            "HR/재무 SaaS는 다년계약·높은 전환비용으로 경기민감도가 낮은 "
            "편(GWRE/PTC 0.22~0.25와 유사하거나 약간 낮음)[추정치]. "
            "⚠️Mobley v. Workday(AI채용스크리닝 차별 집단소송, 2026-06-22 "
            "법원이 본안심리 진행 허용)는 반독점/규제 사건이 아니라 고용"
            "차별 소송이라 active_antitrust_or_regulatory_case에는 반영하지 "
            "않음 - 대신 data_limitations에 미확정 배상액 리스크로 명시."
        ),

        model_used="two_stage",
        model_choice_reason=(
            "매출 5년 CAGR 16.76%(2022년 5,139M -> 2026년 9,552M)로 SE/RMD/"
            "DUOL/TTD/MNDY만큼 극단적인 고성장은 아니나 여전히 뚜렷한 감속"
            "구간(4년 전 20%대 성장 -> 최근 13%대)에 있다는 점, FCF가 최근 "
            "5년간 흑자전환 후 3배 이상 성장했다는 점에서 two_stage가 "
            "명시적 고성장기 이후 정상화를 모델링하는 데 이 세션의 다른 "
            "종목들과 일관되게 더 부합한다고 판단 - 실행 후 모델괴리를 보고 "
            "재검토할 것. 첫 분석이라 대조할 과거 기록 없음."
        ),

        data_sources=[
            "SEC EDGAR 10-K FY2026(0001327811-26-000014) R3/R5/R10, as-filed, 2026-07-31 조회",
            "SEC EDGAR 10-K FY2024(0001327811-24-000044) R5/R10 (FY2023/2022 대조검증)",
            "SEC EDGAR 10-K FY2022(0001327811-22-000030) R5/R10 (FY2021 데이터)",
            "stockanalysis.com 시가총액 $39.60B(주가 $160.34), 2026-07-31 조회",
            "WebSearch: Barchart 'AI Disruption Overblown! 4 Software Stocks to Buy "
            "on the Dip' 기사, Workday 경쟁구도(ADP/Taleo 전환데이터), Mobley v. "
            "Workday 소송 진행상황(2026-06-22 법원 판결) 확인",
        ],
    )


def main():
    result = run_analysis(build_inputs())
    d, g = result["derived"], result["growth"]
    models = result["implied_growth"]["models"]

    print("=" * 100)
    print(f"WDAY(Workday) 정식 분석 결과 ({result['meta']['analyzed_at'][:10]}, 엔진 {result['meta']['engine_version']})")
    print("=" * 100)
    print(f"  CAGR 기준연도    : {d['cagr_5y_base_year']}년 ({d['cagr_5y_span']}년 구간, override 미사용)")
    rev_10y_str = "N/A" if d['revenue_cagr_10y'] is None else f"{d['revenue_cagr_10y']*100:.2f}%"
    print(f"  매출 CAGR        : 3y {d['revenue_cagr_3y']*100:.2f}% / "
          f"{d['cagr_5y_span']}y {d['revenue_cagr_5y']*100:.2f}% / 10y {rev_10y_str}")
    print(f"  FCF CAGR         : {d['fcf_cagr_5y']*100:.2f}%   (FCF0 {d['fcf0']/1e6:.3f}M)")
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
