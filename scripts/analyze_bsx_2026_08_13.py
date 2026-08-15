"""
Boston Scientific(BSX) 정식 분석 - 2026-08-13.

경위: `scripts/screen_2026_08_13.py` 스크리닝에서 BSX가 이번 배치 3종목
중 임계값에 가장 근접하게 탈락했다(내재성장률 추정 5.77% vs 임계값 5.5%,
필요 FCF수익률 5.20%에 실제 4.93%로 근소 미달). 스크리너는 DRS 5개 구성요소
중 3개(매출변동성・마진변동성・경쟁강도)를 ledger 실측 중앙값으로 가정하는
근사치라, 실제 경쟁강도・수요민감도를 반영하면 결과가 달라질 수 있다 -
사용자 요청으로 정식분석(run_analysis)을 돌려 확인한다.

원자료: Alpha Vantage MCP(INCOME_STATEMENT/CASH_FLOW/BALANCE_SHEET,
2026-08-13 조회, SEC 공시 기반) - 스크리닝 때보다 구간을 넓혀 2015~2025
11개년(10y CAGR 산출 가능)을 확보했다. 시가총액·주가는 WebSearch로 재확인
($74.19B, 주가 $51.19, 2026-08-13). 위험할인율은 미국10Y 4.69%(2026-08-12
종가, WebSearch 확인)를 썼다 - 스크리닝 때 쓴 4.47%(screener.py 기본값,
2026-07 기준)보다 소폭 높아진 최신값으로 갱신.

**하락 배경 정리**(스크리닝 때 조사 내용 재확인, 2026-08-13):
2025-09 고점($109.50) 대비 ~53% 하락. 2026 매출가이던스 소폭 하향($22.2B->
$21.7B, -2.3%), CRE/CRE Pro 위장관기기 Class II 리콜(FDA, 멸균파우치 손상
가능성), WATCHMAN(좌심방이색전증 폐쇄술) 성장둔화 우려, 전기생리학(EP)
성장 관련 증권 집단소송(공시 부실 의혹)까지 겹쳐 하락폭이 가이던스 컷
자체보다 훨씬 크다.

**경쟁구도 실측(2026-08-13 WebSearch)**: EP(전기생리학) 시장 전체는 J&J
(Biosense Webster)가 54%로 압도적 1위, BSX는 9%뿐이다 - 다만 최근
고성장 중인 PFA(pulsed field ablation) 하위세그먼트에서는 BSX의 Farapulse가
Medtronic 대비 74%를 점유하며 사실상 주도하고 있다. J&J MedTech 임원이
"이 시장 싸움은 매우 개인적"이라고 언급할 만큼 경쟁이 격화되는 중 - EP
소송(증권집단소송)이 겨냥하는 바로 그 성장서사(Farapulse/PFA 고성장)를
둘러싼 경쟁압력이 실재한다.

실행: python3 scripts/analyze_bsx_2026_08_13.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.pipeline import AnalysisInputs, run_analysis, save_ledger

# ── Alpha Vantage 실측 (단위: USD, 원 단위 그대로, 2026-08-13 조회) ──
REVENUE = {
    2015: 7477000000, 2016: 8386000000, 2017: 9048000000, 2018: 9823000000,
    2019: 10735000000, 2020: 9913000000, 2021: 11888000000, 2022: 12682000000,
    2023: 14240000000, 2024: 16747000000, 2025: 20074000000,
}
OPERATING_INCOME = {
    2015: 790000000, 2016: 1236000000, 2017: 1525000000, 2018: 1737000000,
    2019: 1712000000, 2020: 601000000, 2021: 1922000000, 2022: 1824000000,
    2023: 2181000000, 2024: 2635000000, 2025: 3971000000,
}
OPERATING_CASHFLOW = {
    2015: 600000000, 2016: 972000000, 2017: 1426000000, 2018: 310000000,
    2019: 1836000000, 2020: 1508000000, 2021: 1870000000, 2022: 1526000000,
    2023: 2503000000, 2024: 3435000000, 2025: 4534000000,
}
CAPEX = {
    2015: 247000000, 2016: 376000000, 2017: 319000000, 2018: 316000000,
    2019: 461000000, 2020: 376000000, 2021: 554000000, 2022: 612000000,
    2023: 800000000, 2024: 790000000, 2025: 876000000,
}

# 재무상태표 (FY2025, 2025-12-31 기준, Alpha Vantage BALANCE_SHEET)
CASH = 2045000000
TOTAL_DEBT = 12418000000   # shortLongTermDebtTotal
NET_DEBT = TOTAL_DEBT - CASH

DA_2025 = 1368000000  # depreciationAndAmortization (FY2025 손익계산서)
EBITDA = OPERATING_INCOME[2025] + DA_2025

MARKET_CAP = 74.19e9
RF = 0.0469   # 미국 10Y, 2026-08-12 종가(4.69%), WebSearch 확인


def build_inputs() -> AnalysisInputs:
    return AnalysisInputs(
        ticker="BSX",
        company_name="Boston Scientific Corporation",
        revenue_by_year=REVENUE,
        operating_income_by_year=OPERATING_INCOME,
        operating_cashflow_by_year=OPERATING_CASHFLOW,
        capex_by_year=CAPEX,
        market_cap=MARKET_CAP,
        net_debt=NET_DEBT,
        ebitda=EBITDA,
        risk_free_rate=RF,

        competitor_threat_weights=[0.30, 0.15],
        market_share_trend_pp_per_year=0.5,
        active_antitrust_or_regulatory_case=False,
        demand_sensitivity_pct=0.10,
        subjective_input_basis=(
            "경쟁강도 - J&J/Biosense Webster 0.30(EP 전체시장 점유율 54%로 "
            "압도적 1위, 2026-08 WebSearch에서 J&J MedTech 임원이 'EP 시장 "
            "싸움은 매우 개인적'이라 언급할 만큼 명시적으로 공격적 태세 - EP "
            "소송이 겨냥하는 성장서사 자체를 위협하는 가장 실질적인 경쟁자라 "
            "RMD의 Philips 0.25보다 소폭 높게 설정[추정치]). Medtronic 0.15"
            "(BSX Farapulse가 PFA 하위세그먼트에서 Medtronic 대비 74% "
            "점유하며 현재는 앞서 있으나, Medtronic도 2026년 자체 PFA 제품을 "
            "출시해 3파전에 참여 중이라 0을 주지 않음 - 다만 현재 열세라 J&J "
            "보다는 낮게 설정[추정치]). market_share_trend=+0.5pp: Farapulse가 "
            "PFA 신규세그먼트에서 아직 주도권을 유지 중이나(RMD의 Philips "
            "부재 상황과 달리) J&J・Medtronic 둘 다 적극 반격 중이라 과도하게 "
            "낙관하지 않고 RMD와 동일한 완만한 값 사용[추정치]. "
            "active_antitrust_or_regulatory_case=False: 2026-08 WebSearch로 "
            "확인한 진행 중인 반독점・경쟁당국 조사는 없음 - 다만 EP 관련 "
            "증권집단소송(공시 부실 의혹, 반독점과는 성격이 다른 별도 "
            "리스크)과 CRE/CRE Pro Class II 리콜(FDA, 멸균파우치 손상 "
            "가능성)이 진행 중이라는 점은 이 불리언이 포착 못 하는 별도 "
            "리스크로 falsification_conditions에 남긴다. demand_sensitivity"
            "=0.10: 심장질환(구조적심장질환・EP・관상동맥) 시술은 대부분 "
            "생명과 직결된 응급・필수 의료라 경기순환에 상대적으로 가장 "
            "둔감한 축에 속한다고 판단 - RMD(수면무호흡증 CPAP, 0.15)보다도 "
            "낮게 설정했다[추정치]. 다만 이 낮은 수치는 GLP-1이나 대체 "
            "치료법에 의한 구조적 수요치환 리스크는 포착하지 못한다는 점을 "
            "RMD와 동일하게 명시해둔다 - 다만 BSX의 경우 그런 구조적 대체 "
            "서사는 이번 조사에서 확인되지 않았다(WATCHMAN 성장둔화는 경쟁・"
            "가이던스 요인으로 설명되며 대체치료법 서사는 없음)."
        ),

        model_used="two_stage",
        model_choice_reason=(
            "BSX는 2015~2025 전 구간 흑자를 유지했고(2020년 코로나로 마진이 "
            "크게 눌렸으나 적자전환은 아님), 최근 3개년 영업이익 성장이 매출 "
            "성장보다 뚜렷하게 빠르다(FY23->FY24 매출 +17.6%/영업이익 "
            "+20.8%, FY24->FY25 매출 +19.9%/영업이익 +50.7%) - RMD와 동일하게 "
            "명시적 성장기간 이후 정상화를 모델링하는 two_stage가 이 마진확장"
            "궤적에 이론적으로 부합한다고 판단. 첫 정식분석이라 대조할 과거 "
            "기록 없음."
        ),

        cagr_base_year_override=None,  # 2020년 YoY -7.66%는 BKNG급(-54%대) 폭락이 아니라 완만한 조정 - override 불필요(스크리닝 단계에서 2019년과 비교 검증 완료)

        falsification_conditions=(
            "(1) 2026 Q3/Q4 실적에서 WATCHMAN 성장률이 추가로 둔화되거나 "
            "회사가 재차 가이던스를 하향하면 재검토. (2) CRE/CRE Pro 리콜이 "
            "확대되거나(현재 Class II, 81,000+ 유닛) 추가 제품군으로 번지면 "
            "재검토. (3) EP 증권집단소송이 화해・기각 없이 본안 진행되며 "
            "거액 배상이 확정되면 재검토. (4) Medtronic・J&J의 PFA 신제품이 "
            "실제 시장점유율에서 Farapulse를 유의미하게 잠식(예: BSX PFA "
            "점유율이 74%에서 60% 미만으로 하락)하면 경쟁강도 가정을 재검토."
        ),
        price_at_analysis=51.19,
        currency="USD",

        data_sources=[
            "Alpha Vantage MCP INCOME_STATEMENT/CASH_FLOW/BALANCE_SHEET(BSX, 2026-08-13 조회, SEC 공시 기반)",
            "WebSearch: 시가총액 $74.19B/주가 $51.19(2026-08-13), 미국10Y 4.69%(2026-08-12)",
            "WebSearch: BSX 하락배경(가이던스 하향・리콜・WATCHMAN 성장둔화・EP 소송, 2026-08-13)",
            "WebSearch: EP시장 경쟁구도(J&J 54%/BSX 9% 전체시장, BSX Farapulse PFA세그먼트 74% vs Medtronic, 2026-08-13)",
        ],
    )


def main():
    result = run_analysis(build_inputs())
    d, g = result["derived"], result["growth"]
    models = result["implied_growth"]["models"]

    print("=" * 100)
    print(f"BSX(Boston Scientific) 정식 분석 결과 ({result['meta']['analyzed_at'][:10]}, 엔진 {result['meta']['engine_version']})")
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
