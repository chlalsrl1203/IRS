"""
McKesson Corporation(MCK) 정식 분석 - 2026-07-28.

경위: 2026-07-26 스크리닝 통과 후보. 비큐(ad-hoc) 분석(BKNG/PDD/TCOM/PGR/GEN과
동일 범주). 사용자가 GEN 이후 "NAVER는 데이터 확보 실패로 보류, MCK부터 계속"
으로 방향을 정해 진행했다.

⚠️ **FY2021 오피오이드 소송충당금 - 영업손실이지만 CAGR 계산엔 영향 없음**:
FY2021(2020-04~2021-03) 영업손익이 **-$5,040M(적자)**로 나타나는데, 이는
"claims and litigation charges, net" $7,936M 때문이다 - McKesson·Cardinal
Health·Cencora(당시 AmerisourceBergen) 3사가 미국 전역 주정부·지자체와 합의한
$21B 규모 오피오이드 전국합의(2021~2022 확정)의 회계상 충당금 인식분이다.
**중요**: 이 항목은 비현금성 충당금이라 FY2021 영업활동현금흐름은 오히려
정상적이었다($4,542M, 전후 연도와 비슷한 수준) - 그래서 기본 5년 기준연도가
FY2021이어도 FCF 기준 CAGR 계산 자체는 막히지 않는다(BKNG/TCOM과 다른 유형).
다만 margin_volatility(영업이익률 변동성) 산출에 쓰이는 margin_years는 기본값
(최근 5개년=FY2022~2026)이라 FY2021의 극단치가 자동으로 제외된다 - 별도 조치
불필요.

오피오이드 소송은 여전히 진행형이다(2025-06 볼티모어시 배상 판결 - 감액후
$52M+구제금 $100M). active_antitrust_or_regulatory_case=True로 반영하되
경쟁당국 반독점이 아니라 대규모 규제/소송 리스크임을 명시한다.

원자료: 전부 SEC EDGAR as-filed 10-K에서 직접 추출(2026-07-28 조회, FY2019
~2026, 8개년, 회계연도는 매년 3월 31일 종료).
  FY2026 10-K(0000927653-26-000069) R3/R5/R9
  FY2023 10-K(0000927653-23-000038) R3/R9 (FY2021~2023)
  FY2021 10-K(0000927653-21-000039) R2/R8 (FY2019~2021)
시가총액: stockanalysis.com 2026-07-27 종가 기준 $99.53B.

실행: python3 scripts/analyze_mck_2026_07_28.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.pipeline import AnalysisInputs, run_analysis, save_ledger

M = 1_000_000

# ── SEC EDGAR as-filed 실측 (단위: USD, 원 단위) ────────────────────────
REVENUE = {
    2019: 214319 * M, 2020: 231051 * M, 2021: 238228 * M,
    2022: 263966 * M, 2023: 276711 * M, 2024: 308951 * M,
    2025: 359051 * M, 2026: 403430 * M,
}
OPERATING_INCOME = {
    2019: 886 * M, 2020: 2489 * M,
    2021: -5040 * M,   # 오피오이드 소송충당금 $7,936M 반영(비현금성)
    2022: 2038 * M, 2023: 4381 * M, 2024: 3909 * M,
    2025: 4422 * M, 2026: 6212 * M,
}
OPERATING_CASHFLOW = {
    2019: 4036 * M, 2020: 4374 * M, 2021: 4542 * M,
    2022: 4434 * M, 2023: 5159 * M, 2024: 4314 * M,
    2025: 6085 * M, 2026: 6155 * M,
}
CAPEX = {
    2019: 557 * M, 2020: 506 * M, 2021: 641 * M,
    2022: 535 * M, 2023: 558 * M, 2024: 687 * M,
    2025: 859 * M, 2026: 745 * M,
}

# 재무상태표 (FY2026 10-K R5, 2026-03-31 기준)
CASH = 3975 * M
# 운용리스부채(2,088M)는 BKNG/PDD/TCOM과 동일 관행으로 순부채에서 제외(이자부
# 차입금만 사용) - 스크리너 추정치(8.79B)는 리스부채 포함치라 다소 다름.
SHORT_TERM_DEBT = 1267 * M   # 장기차입금 유동분
LONG_TERM_DEBT = 5259 * M
NET_DEBT = (SHORT_TERM_DEBT + LONG_TERM_DEBT) - CASH

DA_2026 = 256 * M + 473 * M   # 감가상각 256M + 무형자산상각 473M
EBITDA = OPERATING_INCOME[2026] + DA_2026

MARKET_CAP = 99.53e9
RF = 0.0447


def build_inputs() -> AnalysisInputs:
    return AnalysisInputs(
        ticker="MCK",
        company_name="McKesson Corporation",
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
            "Cardinal Health 0.35(3파전 중 최대 경쟁자, 유사 스케일), "
            "Cencora(구 AmerisourceBergen) 0.30(같은 스크리닝 배치의 다른 "
            "후보이기도 함 - 3사가 미국 의약품유통시장 대부분을 과점), "
            "PBM/보험사 수직계열화 위협 0.25(CVS Health/UnitedHealth Optum "
            "등이 자체 유통망을 내재화하려는 구조적 압력 - 전통 3파전 "
            "도매상을 우회할 잠재 리스크)[셋 다 추정치]. market_share_trend="
            "0.0: 3사 과점구조가 수십년째 25~33%대에서 안정적이라는 근거는 "
            "있으나 정량 추세 데이터가 없어 중립[추정치]. "
            "active_antitrust_or_regulatory_case=True: 경쟁당국 반독점은 "
            "아니지만 규모와 성격상 동급으로 취급 - MCK/Cardinal/Cencora 3사가 "
            "2021~2022 미 전역 오피오이드 전국합의로 총 $21B를 부담했고 "
            "(FY2021 McKesson 단독 $7.94B 충당금), 2025-06 볼티모어시 배심 "
            "판결(감액후 $52M+구제금 $100M)에서 보듯 개별 소송이 여전히 "
            "진행형이다. demand_sensitivity=0.08: 처방의약품 유통은 경기와 "
            "무관하게 필수적으로 소비되는 재화라 이 프로젝트에서 가장 낮은 "
            "축에 속함(PGR 0.15보다도 낮음 - 자동차보험은 그래도 보장등급 "
            "선택 여지가 있으나 처방약 유통량은 그런 여지가 거의 없음)"
            "[추정치]."
        ),

        model_used="two_stage",
        model_choice_reason=(
            "MCK은 처방약 유통이라는 성숙・안정 산업의 3파전 과점 사업자로, "
            "최근 3년 매출성장이 오히려 가속(FY24 +11.0%, FY25 +16.2%, "
            "FY26 +12.4% - GLP-1 등 고가 특수의약품 유통 확대가 주된 배경으로 "
            "추정)되는 특이 국면에 있다. 이 가속이 무기한 지속되긴 어렵다고 "
            "보아 명시적 성장기간 이후 정상화를 모델링하는 two_stage를 "
            "채택했다. 첫 정식분석이라 대조할 과거 기록이 없다 - 실제 괴리는 "
            "divergence_warning으로 확인."
        ),

        data_sources=[
            "SEC EDGAR 10-K FY2026(0000927653-26-000069) R3/R5/R9, as-filed, 2026-07-28 조회",
            "SEC EDGAR 10-K FY2023(0000927653-23-000038) R3/R9 (FY2021~2023)",
            "SEC EDGAR 10-K FY2021(0000927653-21-000039) R2/R8 (FY2019~2021)",
            "stockanalysis.com 시가총액 $99.53B (2026-07-27 종가 기준)",
            "WebSearch: 오피오이드 전국합의 $21B 및 볼티모어 판결(2025-06) 확인",
        ],
    )


def main():
    result = run_analysis(build_inputs())
    d, g = result["derived"], result["growth"]
    models = result["implied_growth"]["models"]

    print("=" * 100)
    print(f"MCK 정식 분석 결과 ({result['meta']['analyzed_at'][:10]}, 엔진 {result['meta']['engine_version']})")
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
