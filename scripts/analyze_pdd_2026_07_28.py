"""
PDD Holdings 정식 분석 - 2026-07-28.

경위: 2026-07-26 스크리닝(scripts/screen_2026_07_26.py)에서 S등급 통과(Gap 추정
+40.96%p, 후보 중 최고치)한 종목을 정식 분석한다. 공식 83개 큐에는 없는
비큐(ad-hoc) 분석이다(BKNG/GOOGL/UBER 등과 동일 범주).

BKNG에서 드러난 "짧은 조회창이 경기 저점을 놓친다" 문제의 재확인 대상으로
선정했으나, PDD는 2018년 IPO(20-F 최초 제출)라 애초에 10년 데이터가 존재하지
않는다 - 확보 가능한 최장 구간(FY2018~2025, 8개년)을 전부 사용했다. BKNG과
달리 코로나(FY2020)가 PDD에는 저점이 아니라 오히려 성장 가속 구간이었으므로
(중국 온라인 e-commerce 수요 증가) cagr_base_year_override는 불필요 -
기본 5년 룩백(FY2020 기준)의 FCF가 양수(+281.5억 위안)라 엔진이 그대로 통과한다.

원자료: 전부 SEC EDGAR as-filed 20-F에서 직접 추출(2026-07-28 조회, 재무제표는
전부 RMB 표시 원본, 단위 위안).
  FY2025 20-F (0001104659-26-050727): R2 재무상태표, R4 손익, R7 현금흐름
  FY2022 20-F (0001104659-23-049927): R4 손익, R7 현금흐름 (FY2020~2022 비교)
  FY2020 20-F (0001104659-21-058237): R4 손익, R7 현금흐름 (FY2018~2020 비교)
시가총액: stockanalysis.com 2026-07-27 종가 기준 $120.78B.
환율: USD/CNY 6.7716 (2026-07-24 Fed H.10 교차검증치, 기존 스크리닝에서 이미
  검증됨 - 2026-07-27 시점 스팟(6.765~6.773)과도 0.1% 이내로 일치).

실행: python3 scripts/analyze_pdd_2026_07_28.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.pipeline import AnalysisInputs, run_analysis, save_ledger

K = 1_000  # 원자료가 '천 위안' 단위라 원 단위로 환산

# ── SEC EDGAR as-filed 실측 (단위: RMB, 원 단위) ────────────────────────
REVENUE = {
    2018: 13_119_990 * K, 2019: 30_141_886 * K, 2020: 59_491_865 * K,
    2021: 93_949_939 * K, 2022: 130_557_589 * K, 2023: 247_639_205 * K,
    2024: 393_836_097 * K, 2025: 431_845_713 * K,
}
OPERATING_INCOME = {
    2018: -10_799_741 * K, 2019: -8_538_211 * K, 2020: -9_380_325 * K,
    2021: 6_896_762 * K, 2022: 30_401_921 * K, 2023: 58_698_762 * K,
    2024: 108_422_862 * K, 2025: 93_102_131 * K,
}
OPERATING_CASHFLOW = {
    2018: 7_767_927 * K, 2019: 14_820_976 * K, 2020: 28_196_627 * K,
    2021: 28_783_011 * K, 2022: 48_507_860 * K, 2023: 94_162_531 * K,
    2024: 121_929_292 * K, 2025: 106_938_690 * K,
}
CAPEX = {
    2018: 27_331 * K, 2019: 27_436 * K, 2020: 43_046 * K,
    2021: 3_287_232 * K, 2022: 635_716 * K, 2023: 583_879 * K,
    2024: 967_137 * K, 2025: 1_145_077 * K,
}

# 재무상태표 (FY2025 20-F R2, 2025-12-31 기준)
CASH = 108_900_587 * K
SHORT_TERM_INVESTMENTS = 313_407_682 * K
# 별도 이자부 차입금 라인이 없음 - 전환사채(2024년 잔액 53.096억 위안)는
# FY2025 재무활동현금흐름에서 -5,228,716천 위안 상환되어 사실상 완전 상환됨.
# 총부채 2,166.6억 위안은 매입채무·판매자정산대금(에스크로)·이연수익 등
# 비이자부 운전자본성 부채가 대부분 - 이자부 차입금 = 0으로 처리.
TOTAL_DEBT = 0
NET_DEBT = TOTAL_DEBT - (CASH + SHORT_TERM_INVESTMENTS)  # 순현금(대규모)

DA_2025 = 601_483 * K                     # FY2025 20-F R7 감가상각비+무형자산상각
EBITDA = OPERATING_INCOME[2025] + DA_2025

USD_CNY = 6.7716
MARKET_CAP = 120.78e9 * USD_CNY           # RMB 환산 (재무제표 통화와 일치시킴)
RF = 0.0447


def build_inputs() -> AnalysisInputs:
    return AnalysisInputs(
        ticker="PDD",
        company_name="PDD Holdings Inc. (Pinduoduo/Temu)",
        revenue_by_year=REVENUE,
        operating_income_by_year=OPERATING_INCOME,
        operating_cashflow_by_year=OPERATING_CASHFLOW,
        capex_by_year=CAPEX,
        market_cap=MARKET_CAP,
        net_debt=NET_DEBT,
        ebitda=EBITDA,
        risk_free_rate=RF,

        # v3.24(2026-08-01 방법론 감사 M-6): 재무제표가 RMB 표시라 market_cap도
        # RMB 환산해 넣었다(위 MARKET_CAP 주석 참고) - currency 필드가 없던
        # 시점에는 이 사실이 ledger에 남지 않아 향후 종목 간 절대값을 비교하면
        # 조용히 틀릴 위험이 있었다. 비율 기반 계산이라 내부 정합성 자체는
        # 문제없었지만(감사에서 확인), 이제 명시적으로 기록한다.
        currency="CNY",

        competitor_threat_weights=[0.45, 0.40, 0.30],
        market_share_trend_pp_per_year=-1.0,
        active_antitrust_or_regulatory_case=True,
        demand_sensitivity_pct=0.35,
        subjective_input_basis=(
            "Alibaba(Taobao/Tmall) 0.45(중국 최대 플랫폼, PDD에 저가 카테고리에서 "
            "정면 반격 중), Douyin(ByteDance) e-commerce 0.40(라이브커머스 기반 "
            "두자릿수 성장으로 Alibaba 5%대 성장을 크게 앞지르며 저가경쟁까지 "
            "가세 - 2026-07 WebSearch), JD.com 0.30(3위로 밀렸으나 물류·정품 "
            "신뢰도 기반 안정적 방어). 셋 다 [추정치]. "
            "market_share_trend=-1.0pp: PDD가 2023년 JD를 제치고 2024년 한때 "
            "Alibaba 시가총액을 넘어섰던 상승세가 2025년 들어 급격히 꺾였다 - "
            "매출성장률이 FY2024 59.06%->FY2025 9.65%로 급감했고, Douyin의 "
            "두자릿수 성장이 PDD의 핵심 무기였던 '전체 최저가'를 잠식하는 중이라 "
            "순 점유율 모멘텀을 음(-)으로 판단[추정치]. "
            "active_antitrust_or_regulatory_case=True: 근거 명확하다. (1) 미국이 "
            "2025-05-02 중국발 소액면세(de minimis, $800 미만) 통관특례를 폐지해 "
            "Temu 미국 앱 일일 방문자가 58% 급감(2025-02 CNBC 보도, 관세정책발 "
            "직접 충격), (2) EU 집행위가 2024-10-31 Temu에 대해 DSA(디지털서비스법) "
            "정식 조사를 개시했고 2025-07-28 예비판정(불법상품 유통 리스크관리 "
            "의무 위반)을 거쳐 2026-06 실제 과징금 2억 유로가 부과됐다(EU 공식 "
            "발표 확인). (3) 중국 내에서도 SAMR 등 규제당국의 '반내권(反内卷, "
            "출혈경쟁 방지)' 압박이 저가 플랫폼 전반에 가해지는 중. "
            "demand_sensitivity=0.35: PDD의 핵심 가치제안이 '초저가'라 중국 내수 "
            "경기둔화 국면에서는 오히려 소비 downgrade 수혜(역방향 완충) 여지가 "
            "있으나, 실제로는 '중국 소비 변동성'이 FY2025 둔화 요인 중 하나로 "
            "언급됐고 Temu 해외매출은 관세정책 충격에 극단적으로 노출된 이력이 "
            "있어(-58% 방문자) 완전한 방어주로 보기 어렵다 - BKNG(0.60) 대비 "
            "낮지만 TYL(0.05) 같은 방어주보다는 확연히 높은 중간값[추정치]."
        ),

        model_used="two_stage",
        model_choice_reason=(
            "PDD는 FY2024 59.06% -> FY2025 9.65%로 매출성장률이 6분의 1로 "
            "급감한 뒤 최근 분기(Q3 2025 +9%, Q4 2025 +12%)에 한 자릿수 후반~ "
            "두자릿수 초반으로 재안정화되는 명확한 감속국면에 있다(2026-07 "
            "WebSearch, PYMNTS/eMarketer 실적 보도). 이런 '고성장에서 성숙성장로 "
            "이행 중'인 궤적은 일정 성장기간 이후 터미널 성장률로 수렴하는 "
            "구조를 명시적으로 모델링하는 two_stage가 이론적으로 더 부합한다 "
            "(BKNG과 동일 논리). 이 종목은 첫 정식분석이라 대조할 과거 기록이 "
            "없다 - single_stage/two_stage 실제 괴리는 결과의 divergence_warning "
            "필드로 확인하고, 3%p 미만이면 모델선택이 판정을 바꾸지 않는다는 "
            "뜻이므로 이 사유가 그대로 유효하다."
        ),

        data_sources=[
            "SEC EDGAR 20-F FY2025(0001104659-26-050727) R2/R4/R7, as-filed, 2026-07-28 조회",
            "SEC EDGAR 20-F FY2022(0001104659-23-049927) R4/R7 (FY2020~2022 비교치)",
            "SEC EDGAR 20-F FY2020(0001104659-21-058237) R4/R7 (FY2018~2020 비교치)",
            "stockanalysis.com 시가총액 $120.78B (2026-07-27 종가)",
            "USD/CNY 6.7716 (2026-07-24 Fed H.10, 기존 스크리닝에서 검증된 값, "
            "2026-07-27 스팟 6.765~6.773과 0.1% 이내 일치 재확인)",
            "WebSearch: Temu 미국 de minimis 폐지 영향(PYMNTS/CNBC/eMarketer), "
            "EU DSA Temu 조사·과징금(Lewis Silkin/EU 공식 발표), "
            "중국 e-commerce 경쟁구도 2026(Douyin/Alibaba/JD)",
        ],
    )


def main():
    result = run_analysis(build_inputs())
    d, g = result["derived"], result["growth"]
    models = result["implied_growth"]["models"]

    print("=" * 100)
    print(f"PDD 정식 분석 결과 ({result['meta']['analyzed_at'][:10]}, 엔진 {result['meta']['engine_version']})")
    print("=" * 100)
    print(f"  CAGR 기준연도    : {d['cagr_5y_base_year']}년 ({d['cagr_5y_span']}년 구간, override 미사용)")
    rev_10y_str = "N/A" if d['revenue_cagr_10y'] is None else f"{d['revenue_cagr_10y']*100:.2f}%"
    print(f"  매출 CAGR        : 3y {d['revenue_cagr_3y']*100:.2f}% / "
          f"{d['cagr_5y_span']}y {d['revenue_cagr_5y']*100:.2f}% / 10y {rev_10y_str}")
    print(f"  FCF CAGR         : {d['fcf_cagr_5y']*100:.2f}%   (FCF0 {d['fcf0']/1e9:.3f}B RMB)")
    print(f"  최악 YoY 매출    : {d['worst_yoy_revenue_growth']*100:.2f}% ({d['worst_yoy_year']}년)")
    print(f"  순부채/EBITDA    : {d['net_debt_to_ebitda']:.3f}배 (순현금 포지션)")
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

    print("\n" + "=" * 100)
    print("스크리닝 추정치 vs 정식 분석 (스크리너 정확도 사후검증)")
    print("=" * 100)
    # 2026-07-26 스크리닝 스크립트 실측치(scripts/screen_2026_07_26.py PDD 행,
    # engine.screener.screen()으로 2026-07-28 재계산해 확인)
    print(f"  {'항목':20} {'스크리닝 추정':>14} {'정식 분석':>12} {'차이':>10}")
    for label, est, act in [
        ("내재성장률", -0.02551, result["implied_growth"]["value"]),
        ("현실적성장률", 0.38409, g["realistic_growth"]),
        ("Expectation Gap", 0.40960, result["expectation_gap"]),
        ("DRS", 30.6, result["drs"]["score"]),
    ]:
        if label == "DRS":
            print(f"  {label:20} {est:13.1f} {act:12.1f} {act-est:+10.1f}")
        else:
            print(f"  {label:20} {est*100:12.2f}% {act*100:11.2f}% {(act-est)*100:+9.2f}%p")
    return result


if __name__ == "__main__":
    main()
