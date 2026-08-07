"""
KLA Corporation(KLAC) 정식 분석 - 2026-07-29.

경위: 공식 83개 큐의 48번째 종목. KLA는 반도체 공정제어(웨이퍼 검사/계측)
분야의 사실상 독점적 리더(웨이퍼검사·계측 시장점유율 약 50%, "선단공정 팹의
품질관리에 사실상 필수"로 평가됨, 2026-07 WebSearch) - 경쟁강도는 낮지만
대신 지정학적/수출통제 리스크가 매우 크다.

⚠️ **분석일 직전 실적발표(2026-07-28) - 가이던스 실망으로 급락**: FY2026
4분기(2026-06-30 마감) 실적 자체는 컨센서스 상회(EPS $1.05 vs 예상 $1.00,
매출 $3.66B vs 예상 $3.6B)했으나, FY2027 1분기 가이던스가 시장기대에
못미쳐(EPS $1.06~1.26 vs 컨센서스 $1.13, 중간값이 컨센서스를 근소하게 상회
하는 수준에 그침) 정규장에서 -6.18%(종가 $190.80, 전일比 $203.36) 급락했다
(2026-07-29 WebSearch로 확인). 시가총액은 이 하락이 반영된 2026-07-28 종가
기준을 사용 - 밸류에이션에는 이미 시장의 실망 반응이 녹아있다. **참고**:
SEC 10-K는 FY2025(2025-06-30 마감)까지만 제출돼 있어(FY2026 10-K는 아직
미제출, 통상 8월 초 제출) 재무 시계열은 감사완료된 FY2017~2025 9개년을
사용했다 - FY2026 잠정실적(매출 $13.58B)은 미반영.

⚠️ **미・중 반도체 장비 수출통제 - 활성 규제리스크**: 2026-07 WebSearch
확인 - 미 상무부가 KLA를 포함한 반도체장비 3대 기업(Applied Materials/
Lam Research/KLA)에 中 화훙반도체(Hua Hong) 등 선단공정 中 팹向 첨단
증착・식각・계측 장비 수출을 사실상 불허(라이선스 추정거부)하는 조치를
내렸다 - 진행형 규제조치다. 中이 KLA 매출의 약 30%(직전회계연도 기준
약 $2.66B)를 차지해 재무적 영향이 실질적이다. active_antitrust_or_
regulatory_case=True로 반영(경쟁당국 반독점이 아니라 수출통제/무역정책
성격임을 명시).

KLA 자체 재무데이터는 영업이익 별도 표시 라인이 없어(세전이익 직전에
이자비용・기타손익을 그대로 반영) 매출-매출원가-R&D-SG&A-손상차손으로
직접 계산했다(이자비용/기타손익 등 비영업 항목 제외).

원자료: 전부 SEC EDGAR as-filed 10-K에서 직접 추출(2026-07-29 조회, FY2017
~2025, 9개년, 회계연도는 매년 6월 30일 종료).
  FY2025 10-K(0000319201-25-000024) R3/R5/R9
  FY2022 10-K(0000319201-22-000023) R5/R9 (FY2020~2022)
  FY2019 10-K(0000319201-19-000031) R4/R8 (FY2017~2019)
시가총액: stockanalysis.com 2026-07-28 종가($190.80) 기준 $249.24B.

실행: python3 scripts/analyze_klac_2026_07_29.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.pipeline import AnalysisInputs, run_analysis, save_ledger

K = 1_000  # 원자료가 '천 달러' 단위

# ── SEC EDGAR as-filed 실측 (단위: USD, 원 단위) ────────────────────────
REVENUE = {
    2017: 3480014 * K, 2018: 4036701 * K, 2019: 4568904 * K,
    2020: 5806424 * K, 2021: 6918734 * K, 2022: 9211883 * K,
    2023: 10496056 * K, 2024: 9812247 * K,   # WFE 다운사이클로 YoY -6.5%
    2025: 12156162 * K,
}
# = 매출 - 매출원가 - R&D - SG&A - 손상차손(이자비용/기타손익 등 비영업항목 제외).
# KLA 재무제표는 별도 '영업이익' 라인이 없어 직접 계산.
OPERATING_INCOME = {
    2017: 1278900 * K, 2018: 1539825 * K, 2019: 1389373 * K,
    2020: 1502201 * K, 2021: 2488480 * K, 2022: 3654181 * K,
    2023: 3994696 * K, 2024: 3346210 * K, 2025: 4775127 * K,
}
OPERATING_CASHFLOW = {
    2017: 1079665 * K, 2018: 1229120 * K, 2019: 1152632 * K,
    2020: 1778850 * K, 2021: 2185026 * K, 2022: 3312702 * K,
    2023: 3669805 * K, 2024: 3308575 * K, 2025: 4081903 * K,
}
CAPEX = {
    2017: 38594 * K, 2018: 66947 * K, 2019: 130498 * K,
    2020: 152675 * K, 2021: 231628 * K, 2022: 307320 * K,
    2023: 341591 * K, 2024: 277384 * K, 2025: 335259 * K,
}

# 재무상태표 (FY2025 10-K R3, 2025-06-30 기준)
CASH = 2078908 * K
MARKETABLE_SECURITIES = 2415715 * K
LONG_TERM_DEBT = 5884257 * K
NET_DEBT = LONG_TERM_DEBT - (CASH + MARKETABLE_SECURITIES)

DA_2025 = 394088 * K
EBITDA = OPERATING_INCOME[2025] + DA_2025

MARKET_CAP = 249.24e9   # 2026-07-28 종가($190.80) - 7/28 실적발표 가이던스실망 -6.18% 반영됨
RF = 0.0447


def build_inputs() -> AnalysisInputs:
    return AnalysisInputs(
        ticker="KLAC",
        company_name="KLA Corporation",
        revenue_by_year=REVENUE,
        operating_income_by_year=OPERATING_INCOME,
        operating_cashflow_by_year=OPERATING_CASHFLOW,
        capex_by_year=CAPEX,
        market_cap=MARKET_CAP,
        net_debt=NET_DEBT,
        ebitda=EBITDA,
        risk_free_rate=RF,

        competitor_threat_weights=[0.25, 0.20, 0.15],
        market_share_trend_pp_per_year=-0.5,
        active_antitrust_or_regulatory_case=True,
        demand_sensitivity_pct=0.38,
        subjective_input_basis=(
            "Applied Materials 0.25(가장 큰 종합WFE업체이나 KLA만큼 공정제어에 "
            "특화되지는 않음), Onto Innovation 0.20(순수 공정제어 전문업체로 "
            "빠르게 성장 중인 위협), Nova Ltd 등 기타 계측전문사 0.15. 셋 다 "
            "낮은 편으로 설정한 이유는 KLA가 웨이퍼검사・계측 시장점유율 "
            "약 50%로 '선단공정 팹 품질관리에 사실상 필수'로 평가되는 압도적 "
            "지위 때문(2026-07 WebSearch)[추정치]. market_share_trend="
            "-0.5pp: 글로벌 기술적 리더십 자체는 침식 증거가 없으나, 아래 "
            "수출통제로 中 매출(전체의 약 30%)이 구조적으로 위축될 리스크가 "
            "있어 완만한 음(-) 추세로 보수적 반영[추정치]. "
            "active_antitrust_or_regulatory_case=True: 근거 명확 - 美 상무부가 "
            "2026-07 KLA/Applied Materials/Lam Research 반도체장비 3대사에 "
            "中 화훙반도체(Hua Hong) 등 선단공정 中 팹向 첨단장비 수출을 "
            "사실상 불허하는 조치를 내렸다(라이선스 추정거부). 中이 KLA "
            "매출의 약 30%(약 $2.66B)를 차지해 재무영향이 실질적 - 경쟁당국 "
            "반독점이 아니라 수출통제/무역정책 성격임을 명시. "
            "demand_sensitivity=0.38: 반도체장비는 WFE(웨이퍼팹장비) "
            "지출사이클에 연동되는 대표적 경기민감 산업 - 실제로 FY2024 "
            "매출이 전년比 -6.5% 역성장한 실측 이력이 있다. GWRE(0.22)・"
            "PTC(0.25)보다 높은 값을 채택[추정치]."
        ),

        model_used="single_stage",
        model_choice_reason=(
            "초안에서는 'WFE 다운사이클→회복' 서사로 two_stage를 검토했으나, "
            "실제 계산 결과 single_stage(9.47%)와 two_stage(22.31%)의 괴리가 "
            "**12.85%p로 이 프로젝트 역대 최대**(CDNS 10.97%p·GWRE 9.03%p를 "
            "능가)이고 판정 자체가 갈렸다(two_stage: Gap -11.61%p 과대평가 "
            "vs single_stage: Gap +1.23%p 적정가/경계선). 결정적으로, "
            "two_stage가 요구하는 22.31% 성장은 KLA 자체의 2026-07-28 "
            "FY2027 1분기 가이던스(컨센서스를 근소하게 상회하는 수준에 그침, "
            "'underwhelming'으로 시장이 평가해 당일 -6.18% 급락)와 정면으로 "
            "배치된다 - 회사 스스로도 22%대 성장을 시사하지 않는데 "
            "two_stage로 밸류에이션하면 이를 무시하는 셈이다. 반면 "
            "single_stage가 요구하는 9.47%는 Realistic Growth(10.70%)와 "
            "근접해 훨씬 현실적이다. Lynch 자동분류는 'cyclical'이라 GWRE"
            "(stalwart)와 완전히 동일한 전례는 아니지만, 이 프로젝트가 "
            "반복적으로 확인해온 원칙(모델선택이 판정을 뒤집을 만큼 크면 "
            "서사가 아니라 실제 가이던스・펀더멘털과 더 정합적인 쪽을 "
            "선택)을 그대로 적용해 single_stage로 전환했다."
        ),

        data_sources=[
            "SEC EDGAR 10-K FY2025(0000319201-25-000024) R3/R5/R9, as-filed, 2026-07-29 조회",
            "SEC EDGAR 10-K FY2022(0000319201-22-000023) R5/R9 (FY2020~2022)",
            "SEC EDGAR 10-K FY2019(0000319201-19-000031) R4/R8 (FY2017~2019)",
            "stockanalysis.com 시가총액 $249.24B (2026-07-28 종가, 실적발표 반영)",
            "WebSearch: KLA FY2026 4분기 실적/가이던스 실망 주가급락(2026-07-28), "
            "美 상무부 中 화훙반도체向 수출통제 조치, KLA 시장점유율/경쟁구도",
        ],
    )


def main():
    result = run_analysis(build_inputs())
    d, g = result["derived"], result["growth"]
    models = result["implied_growth"]["models"]

    print("=" * 100)
    print(f"KLAC 정식 분석 결과 ({result['meta']['analyzed_at'][:10]}, 엔진 {result['meta']['engine_version']})")
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
