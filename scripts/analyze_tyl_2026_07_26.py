"""
Tyler Technologies(TYL) 스크립트 정식 등록 - 2026-08-05(원분석일 2026-07-26).

경위: 2026-08-04/05 B/C/D등급 20종목 가벼운 정성검증 중 TYL에서 처음으로
SBC/FCF ≈ 62%(가이던스 기반 추정)라는 신규 발견이 나왔는데, scripts/
아래 재현용 스크립트가 없다는 사실을 확인했다(BRO/BSY와 동일한 패턴 -
과거 세션 내 직접 배선으로 실행되고 재현용 파일이 누락됐던 사례). SBC를
SEC 원자료로 정식 크로스체크하려면 재현 가능한 스크립트가 먼저 필요해
ledger/TYL_2026-07-26.json의 원본 입력값을 그대로 옮겨 등록하고, 여기에
SEC EDGAR 실측 SBC만 추가한다(계산에 영향을 주는 다른 입력값은 일절
변경하지 않음).

원분석 노트(ledger meta 기준): SEC EDGAR 10-K FY2025/2022/2019/2016
(as-filed R.htm, 2026-07-26 조회) + WebSearch 시가총액/경쟁구도. Lynch
자동분류 fast_grower(5y 매출CAGR 15.87%), model_used=two_stage(모델괴리
2.47%p로 경고임계값 미만이나 SaaS 성장기업 특성상 명시적 성장기 모델링이
이론적으로 더 부합한다고 판단).

**SBC 병기 교차검증(2026-08-05)**: SEC EDGAR XBRL companyconcept API
(CIK 860731, us-gaap:ShareBasedCompensation, FY2025=calendar 2025) 실측
$151,276K - 2026-08-04 정성심층조사에서 가이던스 기반으로 추정했던
"SBC/FCF ≈ 62%"를 SEC 원자료로 정식 검증한다.

실행: python3 scripts/analyze_tyl_2026_07_26.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.pipeline import AnalysisInputs, run_analysis, save_ledger

# ── ledger/TYL_2026-07-26.json의 inputs를 그대로 전사(원 단위 그대로) ──────
REVENUE = {
    2014: 493101000, 2015: 591022000, 2016: 756043000, 2017: 840899000,
    2018: 935282000, 2019: 1086427000, 2020: 1116663000, 2021: 1592287000,
    2022: 1850204000, 2023: 1951751000, 2024: 2137803000, 2025: 2332340000,
}
OPERATING_INCOME = {
    2014: 94822000, 2015: 108043000, 2016: 131305000, 2017: 162758000,
    2018: 152492000, 2019: 156367000, 2020: 172926000, 2021: 180735000,
    2022: 214249000, 2023: 218537000, 2024: 299526000, 2025: 357676000,
}
OPERATING_CASHFLOW = {
    2014: 142839000, 2015: 134327000, 2016: 191859000, 2017: 195755000,
    2018: 250203000, 2019: 254720000, 2020: 355089000, 2021: 371753000,
    2022: 381455000, 2023: 380440000, 2024: 624633000, 2025: 653543000,
}
CAPEX = {
    2014: 9343000, 2015: 12501000, 2016: 37726000, 2017: 43057000,
    2018: 27424000, 2019: 42040000, 2020: 28466000, 2021: 55612000,
    2022: 50151000, 2023: 53009000, 2024: 49936000, 2025: 32793000,
}

MARKET_CAP = 12773093780.999998
NET_DEBT = -497537000
EBITDA = 496034000
RF = 0.0447


def build_inputs() -> AnalysisInputs:
    return AnalysisInputs(
        ticker="TYL",
        company_name="Tyler Technologies, Inc.",
        revenue_by_year=REVENUE,
        operating_income_by_year=OPERATING_INCOME,
        operating_cashflow_by_year=OPERATING_CASHFLOW,
        capex_by_year=CAPEX,
        market_cap=MARKET_CAP,
        net_debt=NET_DEBT,
        ebitda=EBITDA,
        risk_free_rate=RF,

        # v3.23(2026-08-05 추가배선): SBC 병기 교차검증. SEC EDGAR XBRL
        # companyconcept API(us-gaap:ShareBasedCompensation) FY2025(calendar
        # 2025) 실측 - 2026-08-04 정성심층조사에서 가이던스 기반으로 추정했던
        # "SBC/FCF ≈ 62%"(TTD·WDAY급)를 SEC 원자료로 정식 검증한다.
        sbc_by_year={2025: 151276000},

        competitor_threat_weights=[0.35, 0.3, 0.25],
        market_share_trend_pp_per_year=0.0,
        active_antitrust_or_regulatory_case=False,
        demand_sensitivity_pct=0.05,
        subjective_input_basis=(
            "OpenGov 0.35(SaaS-first로 가장 빠르게 성장하는 도전자, "
            "budgeting/permitting/reporting 통합 플랫폼으로 Tyler와 직접 "
            "경쟁 확대중), Accela 0.30(permitting/licensing/inspection에서 "
            "Tyler EnerGov와 직접 경쟁, 2026 RFP 숏리스트에 상시 등장), "
            "CentralSquare 0.25(공공안전/ERP 영역 중복). 셋 다 개별로는 "
            "Tyler 규모에 크게 못 미치는 파편화된 시장의 도전자들 "
            "[추정치, 2026-07 WebSearch 기반]. market_share_trend=0.0은 "
            "Tyler가 NIC 인수(2021, 전자결제) 이후 꾸준한 유기적 성장과 "
            "SaaS 전환을 병행중이나 순수 유기적 점유율 변화를 뒷받침할 "
            "정량근거가 없어 중립 처리 [추정치]. demand_sensitivity=0.05로 "
            "낮게 설정 - 매출 대부분이 주/지방정부와의 다년 SaaS/구독 "
            "계약(법원, 재산세, 공공안전, ERP)으로 경기침체에도 정부 핵심 "
            "소프트웨어 예산은 잘 삭감되지 않는 특성 반영(2020 COVID "
            "최악 YoY도 +2.78%로 역성장 없었음, 12년 조회창 확인). "
            "반독점/규제소송: 2021년 Lexur사와의 반독점 분쟁은 이미 "
            "종결(정성리스크로만 언급), 현재 진행중인 반독점/규제 소송 "
            "없음 확인(2026-07 WebSearch) - active_case=False."
        ),

        model_used="two_stage",
        model_choice_reason=(
            "fast_grower 자동분류(5y 매출CAGR 15.87%, 시총 $12.77B<$1000B) "
            "예상, single_stage(5.83%)와 two_stage(8.30%)의 괴리가 2.47%p로 "
            "v3.19 경고임계값(3%p) 미만이라 모델선택에 비교적 강건하지만, "
            "여전히 두 자릿수 성장률이 진행중인 SaaS 성장기업 특성상 명시적 "
            "성장기간을 모델링하는 two_stage가 이론적으로 더 적합하다고 "
            "판단(Gordon Growth는 이미 안정된 성숙기업에 더 적합). 이 종목은 "
            "첫 분석이라 대조할 과거 기록이 없음."
        ),

        margin_years=[2021, 2022, 2023, 2024, 2025],
        data_completeness_pct=0.9,

        data_sources=[
            "SEC EDGAR 10-K FY2025/2022/2019/2016 (as-filed R.htm, 2026-07-26 조회)",
            "WebSearch: TYL market cap/price 2026-07-24, gov-tech competitor landscape 2026",
            "SEC EDGAR XBRL companyconcept API (CIK 860731, us-gaap:ShareBasedCompensation, "
            "FY2025) - SBC $151,276K 실측, 2026-08-05 조회",
        ],
    )


def main():
    result = run_analysis(build_inputs())
    d, g = result["derived"], result["growth"]
    models = result["implied_growth"]["models"]

    print("=" * 100)
    print(f"TYL 분석 결과 재현 ({result['meta']['analyzed_at'][:10]}, 엔진 {result['meta']['engine_version']})")
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
    sbc = result.get("sbc_cross_check")
    if sbc:
        print()
        print(f"  SBC 교차검증     : SBC/FCF {sbc['sbc_to_fcf_pct']*100:.1f}% -> "
              f"SBC차감 Gap {sbc['gap_sbc_adjusted']*100:+.2f}%p "
              f"(판정 {'뒤집힘' if sbc['judgment_flipped'] else '유지'}: {sbc['judgment_sbc_adjusted']})")
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
