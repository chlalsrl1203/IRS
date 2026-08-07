"""
Brown & Brown(BRO) 스크립트 정식 등록 - 2026-08-04(원분석일 2026-07-25).

경위: 2026-08-04 A등급 6종목 정성심층조사(GEN/UBER/WDAY/ROP/TCOM/BRO) 진행 중
BRO만 scripts/ 아래 재현용 스크립트가 없다는 사실을 확인했다(BSY가 2026-07-26
당시 세션 내 직접 배선으로 실행되고 재현용 파일이 누락됐던 것과 동일한
패턴 - v3.25에서 scripts/analyze_bsy_2026_08_02.py로 사후 등록한 선례를
그대로 따른다). ledger/BRO_2026-07-25.json의 원본 입력값을 그대로 옮겨
등록하고, 여기에 이번 정성심층조사에서 나온 falsification_conditions만
추가한다(계산에 영향을 주는 입력값은 일절 변경하지 않음).

원분석 노트(ledger meta 기준): Fiscal.ai standardized financials(2026-07-25
조회) + WebSearch 시가총액($22.93B, 2026-07-23 기준). model_used=single_stage는
과거 v3.15 큐28 기록과의 대조검증 목적으로 선택됐음이 ledger에 명시돼 있다.
lynch_type_override=stalwart는 자동분류(fast_grower)를 하향 오버라이드한
것으로, M&A 롤업 성장과 Q1'26 오가닉 성장률 0%라는 반전신호가 근거다.

**2026-08-04 정성심층조사 핵심 발견**: 회사 공시 오가닉 성장률이 7분기
연속 감속(+13.8%→-2.8%→-0.7%)해 두 차례 마이너스를 기록했다 - lynch_type_
override 사유에 이미 명시된 "Q1'26 오가닉 0%" 반전신호가 이후 실제로 더
악화됐음을 확인한 것이다. ROP와 동일한 유형의 발견(캡/오버라이드 근거가
된 초기신호가 후속 데이터로 재확인·강화됨).

실행: python3 scripts/analyze_bro_2026_07_25.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.pipeline import AnalysisInputs, run_analysis, save_ledger

# ── ledger/BRO_2026-07-25.json의 inputs를 그대로 전사(원 단위 그대로) ──────
REVENUE = {
    2014: 1567460000, 2015: 1656951000, 2016: 1762787000, 2017: 1857270000,
    2018: 2009857000, 2019: 2384737000, 2020: 2606100000, 2021: 3047500000,
    2022: 3563000000, 2023: 4199000000, 2024: 4705000000, 2025: 5763000000,
}
OPERATING_INCOME = {
    2014: 417184000, 2015: 440633000, 2016: 467032000, 2017: 471004000,
    2018: 499447000, 2019: 570768000, 2020: 668900000, 2021: 854700000,
    2022: 963000000, 2023: 1156000000, 2024: 1367000000, 2025: 1502000000,
}
OPERATING_CASHFLOW = {
    2014: 385019000, 2015: 381832000, 2016: 411042000, 2017: 441975000,
    2018: 567529000, 2019: 678180000, 2020: 713000000, 2021: 808800000,
    2022: 881000000, 2023: 1010000000, 2024: 1174000000, 2025: 1450000000,
}
CAPEX = {
    2014: 24923000, 2015: 18375000, 2016: 17765000, 2017: 24192000,
    2018: 41520000, 2019: 73108000, 2020: 70700000, 2021: 45000000,
    2022: 52000000, 2023: 69000000, 2024: 82000000, 2025: 68000000,
}

MARKET_CAP = 22933210922
NET_DEBT = 6534000000
EBITDA = 1869000000
RF = 0.0447


def build_inputs() -> AnalysisInputs:
    return AnalysisInputs(
        ticker="BRO",
        company_name="Brown & Brown, Inc.",
        revenue_by_year=REVENUE,
        operating_income_by_year=OPERATING_INCOME,
        operating_cashflow_by_year=OPERATING_CASHFLOW,
        capex_by_year=CAPEX,
        market_cap=MARKET_CAP,
        net_debt=NET_DEBT,
        ebitda=EBITDA,
        risk_free_rate=RF,

        competitor_threat_weights=[0.5, 0.45, 0.4],
        market_share_trend_pp_per_year=0.0,
        active_antitrust_or_regulatory_case=False,
        demand_sensitivity_pct=0.2,
        subjective_input_basis=(
            "보험중개. Marsh McLennan 0.50, Aon 0.45, AJG 0.40. 점유율추세 "
            "0.0(M&A 롤업 성장이나 유기적 점유율 변화 근거 없음), 수요민감도 "
            "0.20(보험중개 수수료는 방어적이나 보험료 사이클 노출). 전부 [추정치]."
        ),

        model_used="single_stage",
        model_choice_reason=(
            "과거 큐28 기록(v3.15)이 single_stage 4.25%를 사용했음이 트래커에 "
            "명시되어 동일 모델 채택(대조검증 목적)."
        ),

        margin_years=[2021, 2022, 2023, 2024, 2025],
        data_completeness_pct=0.9,
        lynch_type_override="stalwart",
        lynch_type_override_reason=(
            "자동분류는 fast_grower(5y 매출CAGR 17.2%)이나, 과거 v3.15 기록과 "
            "동일하게 stalwart로 하향 오버라이드. 근거: 매출성장 대부분이 "
            "M&A(Accession 등) 연결효과이고 Q1'26 오가닉 성장률 0%라는 명확한 "
            "반전신호가 있음."
        ),

        # 2026-08-04 정성심층조사(A등급 6종목 배치) 반증조건 - 결과 미확정
        # 미래시점 이벤트 기준. 근거: lynch_type_override 사유에 이미 있던 "Q1'26 "
        # 오가닉 0%" 신호가 이후 실제로 더 악화(Q4'25 -2.8%, Q2'26 -0.7%, 7분기
        # 연속 감속)됐음을 확인 - stalwart 오버라이드 판단이 사후적으로 뒷받침됨.
        falsification_conditions=(
            "1) 오가닉 성장률(ex-contingents)이 H2 2026 가이던스(Retail "
            "1.5-2.5%/Specialty Distribution 2-4%) 대비 추가로 악화되면 "
            "stalwart 분류를 넘어 성장서사 자체를 재검토. 2) 순부채/EBITDA"
            "(~2.77x, Accession 인수 후)가 추가 상승하거나 신용등급 조정이 "
            "발생하면 레버리지 리스크 반영. 3) Gallagher/Aon/Marsh 등 경쟁사의 "
            "대형 M&A가 BRO의 타겟 인수 풀 가격을 추가로 밀어올리는 정황이 "
            "확인되면 M&A 자본배분 규율 재검토."
        ),

        data_sources=[
            "Fiscal.ai standardized financials (2026-07-25)",
            "WebSearch: BRO 시가총액 $22.93B (2026-07-23 기준)",
            "2026-08-04 정성심층조사(A등급): M&A자본배분(Accession $9.8B, ~12-16x)·오가닉"
            "성장률(7분기 연속 감속, 2회 마이너스 확인)·보험료사이클 노출·컨틴전트커미션·"
            "거버넌스·희석(SBC 낮으나 M&A주식대가 다일루션 ~19% 별도 존재) - 판정불변, "
            "Confidence 재검토 권고(89→미검증 유지)",
        ],
    )


def main():
    result = run_analysis(build_inputs())
    d, g = result["derived"], result["growth"]
    models = result["implied_growth"]["models"]

    print("=" * 100)
    print(f"BRO 분석 결과 재현 ({result['meta']['analyzed_at'][:10]}, 엔진 {result['meta']['engine_version']})")
    print("=" * 100)
    print(f"  CAGR 기준연도    : {d['cagr_5y_base_year']}년 ({d['cagr_5y_span']}년 구간, override 미사용)")
    rev_10y_str = "N/A" if d['revenue_cagr_10y'] is None else f"{d['revenue_cagr_10y']*100:.2f}%"
    print(f"  매출 CAGR        : 3y {d['revenue_cagr_3y']*100:.2f}% / "
          f"{d['cagr_5y_span']}y {d['revenue_cagr_5y']*100:.2f}% / 10y {rev_10y_str}")
    print(f"  FCF CAGR         : {d['fcf_cagr_5y']*100:.2f}%   (FCF0 {d['fcf0']/1e9:.3f}B)")
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
