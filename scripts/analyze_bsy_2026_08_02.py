"""
Bentley Systems(BSY) 재검증 - 2026-08-02.

경위: 2026-08-01 방법론 감사 M-3(structural_discount_rate 10년 대체값 버그)
수정 이후 영향받는 18개 종목을 순차 재검증하는 작업의 일부. BSY는 원래
2026-07-26에 분석됐으나 그 시점에는 종목별 analyze_*.py 스크립트가 아니라
세션 내 직접 배선으로 실행되어 재현용 스크립트가 저장소에 없었다(ledger
JSON에는 입력값이 전부 남아있어 재구성 가능). 이번 기회에 ledger의 원본
입력값을 그대로 옮겨 정식 스크립트로 만든다 - 향후 재검증 시 다시 이런
간극이 생기지 않도록.

원자료·주관적 입력 전부 ledger/BSY_2026-07-26.json의 inputs를 그대로
옮김(연도 키만 JSON 문자열 -> int로 복원, 계산 로직/주관적 판단 변경 없음).
구조적 할인율만 M-3 수정으로 10.00% -> 11.21%로 바뀔 것으로 예상(10년
데이터 없어 fallback 경로, 이전엔 rev_cagr_3y 대체 버그로 신호가 0이었음).

실행: python3 scripts/analyze_bsy_2026_08_02.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.pipeline import AnalysisInputs, run_analysis, save_ledger

# ── SEC EDGAR as-filed 실측 (단위: USD, 원 단위) - ledger/BSY_2026-07-26.json 원본 ──
REVENUE = {
    2018: 691710000, 2019: 736654000, 2020: 801544000, 2021: 965046000,
    2022: 1099082000, 2023: 1228413000, 2024: 1353095000, 2025: 1501779000,
}
OPERATING_INCOME = {
    2018: 121391000, 2019: 141865000, 2020: 150150000, 2021: 94589000,
    2022: 208612000, 2023: 230542000, 2024: 302150000, 2025: 362621000,
}
OPERATING_CASHFLOW = {
    2018: 161465000, 2019: 170773000, 2020: 258340000, 2021: 288024000,
    2022: 274324000, 2023: 416696000, 2024: 435292000, 2025: 538464000,
}
CAPEX = {
    2018: 19493000, 2019: 16639000, 2020: 16447000, 2021: 17539000,
    2022: 18546000, 2023: 25002000, 2024: 14046000, 2025: 18255000,
}

MARKET_CAP = 9047468213.66
NET_DEBT = 1125634000
EBITDA = 428501000
RF = 0.0447


def build_inputs() -> AnalysisInputs:
    return AnalysisInputs(
        ticker="BSY",
        company_name="Bentley Systems, Incorporated",
        revenue_by_year=REVENUE,
        operating_income_by_year=OPERATING_INCOME,
        operating_cashflow_by_year=OPERATING_CASHFLOW,
        capex_by_year=CAPEX,
        market_cap=MARKET_CAP,
        net_debt=NET_DEBT,
        ebitda=EBITDA,
        risk_free_rate=RF,

        competitor_threat_weights=[0.45, 0.30, 0.25],
        market_share_trend_pp_per_year=0.0,
        active_antitrust_or_regulatory_case=False,
        demand_sensitivity_pct=0.20,
        subjective_input_basis=(
            "Autodesk 0.45(AEC/BIM 시장 압도적 1위, Bentley와 가장 넓게 중복), "
            "Trimble 0.30(건설·인프라 현장 소프트웨어·하드웨어 통합), Hexagon AB "
            "0.25(지리공간·인프라 자산관리 SW) [추정치, 2026-07 WebSearch 기반]. "
            "market_share_trend=0.0은 Autodesk 대비 상대적 열세가 지속되나 "
            "정량적 점유율 변화 근거가 없어 중립 처리 [추정치]. demand_sensitivity"
            "=0.20은 인프라 엔지니어링 SW가 건설·인프라 설비투자 사이클과 "
            "어느정도 연동되지만(TYL 정부SW보다 높음) 구독매출 비중 확대와 "
            "인프라 프로젝트의 장기성 덕에 순수 산업재보다는 낮게 설정 [추정치]. "
            "2021년 영업이익 급감($150M→$95M)은 매출증가($802M→$965M)에도 "
            "불구하고 발생 - 2020-09 직상장(direct listing) 이후 SBC 등 "
            "상장비용 반영 추정이나 원인 확정은 못함 [검증필요], "
            "margin_volatility에 그대로 반영됨. 반독점/규제소송 없음(2026-07 "
            "확인). 순부채/EBITDA 2.63배로 이 세션 분석 종목 중 유일하게 "
            "유의미한 레버리지 보유(대부분 순현금이었음) - 2024년 대규모 "
            "자사주매입+M&A 재원조달 목적 채권발행 추정."
        ),

        model_used="single_stage",
        model_choice_reason=(
            "stalwart 자동분류(5y 매출CAGR 13.38%로 fast_grower 임계값 15% "
            "미만). single_stage(4.94%)와 two_stage(6.29%)의 괴리가 1.35%p로 "
            "v3.19 경고임계값(3%p) 한참 미만이라 모델선택에 강건함. "
            "stalwart+two_stage 조합은 v3.13에서 확인된 구조적 RAR 음수편향이 "
            "있어(min_spread 가드), 괴리가 작아 사실상 등가인 상황에서는 그 "
            "편향을 피할 수 있는 single_stage(Gordon Growth, 성숙기업 표준)를 "
            "선택함. 이 종목은 첫 분석이라 대조할 과거 기록이 없음."
        ),

        data_sources=[
            "SEC EDGAR 10-K FY2025/2022/2020 (as-filed R.htm, 2026-07-26 조회)",
            "WebSearch: BSY 시가총액/주가 2026-07-25, 인프라엔지니어링SW 경쟁사 현황 2026",
        ],
    )


def main():
    result = run_analysis(build_inputs())
    d, g = result["derived"], result["growth"]
    models = result["implied_growth"]["models"]

    print("=" * 100)
    print(f"BSY 재검증 결과 ({result['meta']['analyzed_at'][:10]}, 엔진 {result['meta']['engine_version']})")
    print("=" * 100)
    print(f"  매출 CAGR        : 3y {d['revenue_cagr_3y']*100:.2f}% / 5y {d['revenue_cagr_5y']*100:.2f}%")
    print(f"  FCF CAGR         : {d['fcf_cagr_5y']*100:.2f}%   (FCF0 {d['fcf0']/1e6:.1f}M)")
    print(f"  DRS              : {result['drs']['score']:.2f}   (2026-07-26 원기록: 46.80)")
    print(f"  구조적 할인      : {g['structural_discount_pct']*100:.2f}%   (원기록: 10.00% - M-3 버그영향 종목)")
    print(f"  Realistic Growth : {g['realistic_growth']*100:.2f}%")
    print(f"  Implied Growth   : {result['implied_growth']['value']*100:.2f}% ({result['implied_growth']['model_used']})")
    print(f"  Expectation Gap  : {result['expectation_gap']*100:+.2f}%p   (원기록: +5.84%p)")
    print(f"  RAR              : {result['rar']:+.4f}")
    print(f"  Confidence       : {result['confidence']['final']}/100")
    print(f"  ** 판정          : {result['judgment']} **   (원기록: 저평가 가능성)")
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
