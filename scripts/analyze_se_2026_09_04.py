"""
Sea Limited(SE) 정식 재분석 - 2026-09-04. **보유 3순위(13.4%) 종목.**

경위: 사용자 보유 포트폴리오 정밀 재검토. 기존 ledger는 2026-08-23판
(v3.67, Gap +13.50%p "저평가 가능성" A등급, DRS 52.4, Confidence 94).
12일밖에 안 됐지만 **SBC가 통째로 빠져 있었고**(sbc_by_year=None) 그 사이
주가가 $107.41 -> $112.09로 올랐다.

## 원자료 - 재무제표는 하나도 바뀌지 않았다(20-F 연차 공시 주기)

SE는 외국 발행사(20-F)라 분기 재무제표를 SEC에 제출하지 않는다. 최신
연차는 FY2025(2025-12-31)이고 2026-08-23 분석 때와 **동일**하다. 따라서
이번 재분석에서 바뀌는 것은 딱 셋뿐이다:

  1. **시가총액** $66.37B -> **$71.54B**(+7.8%)
  2. **SBC 배선**(신규) - FY2025 $625.0M
  3. **무위험수익률** 0.0447 -> 0.0475

⚠️ (3)은 주관적 입력이 아니라 **날짜가 붙은 시장 관측치**다. 이번 포트폴리오
재검토의 8종목 전부를 같은 무위험수익률로 맞춰야 종목간 비교가 성립하므로
갱신했다(PTC/VRT와 동일하게 0.0475). 나머지 주관적 입력(경쟁강도·수요
민감도·점유율추세·모델선택)은 **전부 그대로** 유지해 변화 원인을 분리한다.

## ⭐ 발견 1 - 발행주식수 기준을 명시적으로 바꿨다(더 보수적인 쪽)

기존 ledger의 시가총액($66.37B / 주가 $107.41)이 함의하는 주식수는
약 617.8M주인데, SEC 20-F 실측은 **basic 595.0M / diluted 638.2M**이다
(FY2025 가중평균). 어느 것을 썼는지 기존 ledger에 기록이 없어 재현이
불가능했다 - 이번에는 **희석주식수 638,227,141주를 명시**한다. 희석
기준이 주식수가 크므로 시가총액이 커지고 Gap은 좁아진다(보수적 방향).

  ⚠️ SE는 Class A/B 이중구조에 ADS까지 얹혀 있어(RYAN·TW에서 겪은 다중
  클래스 함정과 같은 계열) 20-F 표지 발행주식수가 XBRL에 태깅돼 있지
  않다. 희석 가중평균은 근사이며, 정확한 시점 발행주식수는 미확보로
  남긴다(추측해서 채우지 않는다).

## ⭐ 발견 2 - SBC를 처음 배선했다: FCF의 13.9%로 판정을 흔들지 않는다

FY2025 SBC $625.0M / FCF0 $4,510.7M = **13.9%**. 2026-08-03 정성조사가
"SBC/희석은 양호(FCF의 14%)"라고 웹서치로 확인했던 값과 SEC 1차자료가
정확히 일치한다(TYL에서 2차출처 추정이 3배 틀렸던 사례가 있어 매번
1차자료로 확인한다). WDAY/OKTA/PATH/PINS/ROKU/TENB처럼 판정을 뒤집는
수준이 아니다.

  ⚠️ 단, 정성조사가 지적한 **희석주식수 자체의 증가(+5.5%/년)**는 SBC
  비율과 별개 채널이며 이 엔진이 다루지 않는다(BRO의 M&A 주식대가
  다일루션과 같은 유형). 위 발견 1에서 희석 기준으로 옮긴 것이 그 일부를
  보수적으로 반영한다.

## ⚠️ 기존 판정의 알려진 취약성(그대로 유효)

  - **v3.67 규모조건부 성장상한이 실제로 바인딩된다**: 원시 Realistic
    Growth 23.56% -> 상한 **17.875%**(매출 $22.9B, base_rates $12-25B 구간).
    즉 이 종목의 성장률은 CAGR 계산이 아니라 **상한값 그 자체**이며,
    Gap은 사실상 `상한 - Implied Growth`만 남는다(M-1 성장상한 바인딩).
  - **2026-08-03 정성조사 결론**: Shopee EBITDA가 사상최대 GMV에도 전년比
    감소(TikTok Shop 방어비용), 그룹 이익성장이 사실상 Garena 단독부담,
    TikTok Shop 점유율 잠식 진행(베트남 52%->41%). Confidence를 액면
    94가 아니라 **70대 후반~80대 초반**으로 보라는 권고가 붙어 있다.

## 실행: python3 scripts/analyze_se_2026_09_04.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.pipeline import AnalysisInputs, run_analysis, save_ledger
from engine.provenance import provenance_from_sec_facts

TICKER = "SE"
TODAY = "2026-09-05"   # ⚠️ 실행이 UTC 날짜 경계를 넘겨 ledger 파일명(analyzed_at 기준)과
              # 맞췄다 - v3.35에서 ETF ledger가 두 날짜로 갈릴 뻔한 사고와 같은 지점.

# ── SEC XBRL companyfacts 실측(CIK 0001703399, 조회 2026-09-04) ──────────
# ⚠️ FY2025가 최신 연차(20-F). 2026-08-23 분석과 동일한 값 - 재확인 완료.
# ⚠️ 초판에서 이 값들을 **반올림된 출력에서 옮겨 적었다가**(4,375.7M -> 
# 4375700000) 기존 ledger·frozen prediction과 5년 CAGR이 1.9e-6 어긋나
# 회귀 테스트가 잡아냈다. SEC 원자료 정수값으로 정정했다 - 이 프로젝트가
# 반복 경계해온 "2차/가공된 수치를 검증 없이 옮겨 적기"(TYL SBC 3배 오류)의
# 축소판이다.
REVENUE = {  # us-gaap:Revenues(총매출)
    2020: 4375664000.0, 2021: 9955190000.0, 2022: 12449705000.0,
    2023: 13063560000.0, 2024: 16819866000.0, 2025: 22938469000.0,
}
OPERATING_INCOME = {
    2020: -1303325000.0, 2021: -1583060000.0, 2022: -1487508000.0,
    2023: 224778000.0, 2024: 662152000.0, 2025: 1985306000.0,
}
OPERATING_CASHFLOW = {
    2020: 555868000.0, 2021: 208649000.0, 2022: -1055692000.0,
    2023: 2079688000.0, 2024: 3277420000.0, 2025: 5024523000.0,
}
CAPEX = {
    2020: 336274000.0, 2021: 772177000.0, 2022: 924178000.0,
    2023: 241605000.0, 2024: 318153000.0, 2025: 513809000.0,
}
NET_INCOME = {  # 신규 배선(기존 ledger에 없었음)
    2020: -1618056000.0, 2021: -2046759000.0, 2022: -1651421000.0,
    2023: 150726000.0, 2024: 444321000.0, 2025: 1578149000.0,
}
SBC = {  # ⭐ 신규 배선 - us-gaap:ShareBasedCompensation
    2020: 290246000.0, 2021: 470324000.0, 2022: 705896000.0,
    2023: 685030000.0, 2024: 715839000.0, 2025: 624995000.0,
}

# ── 대차대조표(FY2025말) - 기존 ledger와 동일(같은 20-F에서 나옴) ────────
NET_DEBT = -8728533000.0   # 순현금 $8.73B
EBITDA = 2357477000.0

# ── 시가총액(2026-09-04) ─────────────────────────────────────────────────
PRICE = 112.09             # Alpha Vantage GLOBAL_QUOTE, latestDay 2026-09-04
SHARES_DILUTED = 638227141.0  # FY2025 20-F 희석 가중평균(basic 595,023,879)
MARKET_CAP = PRICE * SHARES_DILUTED           # 약 $71.54B

RF = 0.0475


CIK = "0001703399"   # Sea Limited - SEC 티커맵에 'SE'가 없어 CIK를 직접 지정
UA = "IRS Research chlalsrl1203@gmail.com"


def build_inputs() -> AnalysisInputs:
    from engine.data.providers.sec import fetch_company_facts
    from engine.filing_dates import annual_filing_dates

    facts = fetch_company_facts(CIK, UA)
    # ⚠️ `pit_inputs_for`는 티커->CIK 매핑에 의존하는데 SEC 티커맵에 'SE'가
    # 없어 CIK를 직접 넘겨야 한다. 로직은 그 헬퍼와 동일하게 유지한다 -
    # 최근 회계연도를 못 찾으면 필드 자체를 빼서 PIT_UNKNOWN으로 정직하게
    # 떨어뜨린다(억지로 채우면 '검증한 척'이 된다).
    all_dates = annual_filing_dates(facts)
    years = sorted(REVENUE)
    pit = {"analysis_as_of": TODAY}
    if years and max(years) in all_dates:
        pit["filing_dates_by_year"] = {y: all_dates[y] for y in years
                                       if y in all_dates}
    try:
        provenance = provenance_from_sec_facts(facts, TICKER, TODAY, list(REVENUE))
    except Exception:  # noqa: BLE001
        provenance = None

    return AnalysisInputs(
        ticker=TICKER,
        company_name="Sea Limited",
        revenue_by_year=REVENUE,
        operating_income_by_year=OPERATING_INCOME,
        operating_cashflow_by_year=OPERATING_CASHFLOW,
        capex_by_year=CAPEX,
        market_cap=MARKET_CAP,
        net_debt=NET_DEBT,
        ebitda=EBITDA,
        risk_free_rate=RF,
        usd_fx_rate=1.0,
        competitor_threat_weights=[0.35, 0.15, 0.10],
        market_share_trend_pp_per_year=-2.0,
        active_antitrust_or_regulatory_case=False,
        demand_sensitivity_pct=0.30,
        subjective_input_basis=(
            "기존 ledger(2026-08-23)의 주관적 입력을 **의도적으로 그대로** "
            "유지했다 - 이번 재분석의 목적이 '시가총액 갱신 + SBC 배선이 "
            "판정을 어떻게 바꾸는가'를 분리해 보는 것이라, 주관 입력을 "
            "동시에 손대면 원인 분해가 불가능해진다(PTC·VRT와 같은 통제 설계). "
            "competitor_threat_weights=[0.35(TikTok Shop), 0.15(Lazada/Tokopedia 등 "
            "역내 이커머스), 0.10(Garena 게임 부문 경쟁)] - 2026-08-03 정성 "
            "심층조사가 TikTok Shop의 동남아 점유율 잠식을 최대 위협으로 "
            "확인했다. market_share_trend_pp_per_year=-2.0 - 같은 조사에서 "
            "베트남 Shopee 점유율이 52%->41%로 실제 하락한 것이 관측됐다"
            "(음수 = 점유율 하락 반영). demand_sensitivity_pct=0.30 - "
            "CLAUDE.md 업종앵커표 '소비자 구독/플랫폼(재량소비, 대체재 존재)' "
            "버킷 앵커값 그대로."
        ),
        model_used="two_stage",
        model_choice_reason=(
            "기존 ledger(2026-08-23)와 동일하게 two_stage를 유지한다 - "
            "매출 3y/5y CAGR이 default_terminal_growth를 크게 웃도는 고성장 "
            "국면이고, v3.67 규모조건부 상한(매출 $22.9B, base_rates $12-25B "
            "구간에서 명목 17.875%)이 **실제로 바인딩**돼 언젠가 수렴이 "
            "불가피함을 엔진 스스로 명시하고 있어 고성장->수렴 경로 모형이 "
            "구조에 맞다. 통제 설계상 모델을 바꾸지 않는다(바꾸면 시총 갱신 "
            "효과와 모델 효과가 섞인다)."
        ),
        falsification_conditions=(
            "(1) FY2026 실적(2027-04경 20-F)에서 Shopee 조정 EBITDA가 전년比 "
            "다시 감소하면 - 직전 정성 심층조사가 지목한 'TikTok Shop 방어 "
            "비용으로 이익성장이 Garena 단독부담'이라는 우려가 재확인되는 "
            "것이므로 재검토. (2) 동남아 주요국(인도네시아·베트남·태국) "
            "Shopee 점유율이 추가로 5%p 이상 하락하면 - "
            "market_share_trend_pp_per_year=-2.0 가정보다 빠른 잠식이다. "
            "(3) 희석주식수가 FY2026에도 +5% 이상 늘면 - 이 엔진이 다루지 "
            "않는 별도 다일루션 채널이 계속 주주가치를 잠식하고 있다는 뜻. "
            "(4) 인도네시아 등에서 과거와 같은 이커머스 규제 제동이 재발하면."
        ),
        price_at_analysis=PRICE,
        currency="USD",
        net_income_by_year=NET_INCOME,
        sbc_by_year=SBC,
        data_sources=[
            "SEC XBRL companyfacts (CIK 0001703399 Sea Limited, 조회 2026-09-04)",
            "Alpha Vantage GLOBAL_QUOTE (latestDay 2026-09-04, $112.09)",
            "ledger/SE_2026-08-23.json (net_debt·EBITDA·주관적 입력 승계)",
            "2026-08-03 S등급 정성 심층조사(Shopee EBITDA·TikTok Shop 잠식·"
            "SBC 교차검증) - CLAUDE.md 기록",
        ],
        **pit,
        provenance=provenance,
    )


def main() -> int:
    result = run_analysis(build_inputs())
    path = save_ledger(result)

    g, d, ig = result["growth"], result["discount_rate"], result["implied_growth"]
    print(f"=== {TICKER} {TODAY} ===")
    print(f"시가총액       : ${MARKET_CAP/1e9:,.2f}B  (주가 ${PRICE}, "
          f"희석주식수 {SHARES_DILUTED:,.0f})")
    print(f"DRS            : {result['drs']['score']:.2f}   r={d['r']*100:.2f}%  "
          f"g_term={d['g_terminal']*100:.2f}%")
    print(f"Lynch 유형     : {result['lynch']['used']}  "
          f"cap={g['breakdown']['cap_applied']}")
    print(f"Realistic Growth: {g['realistic_growth']*100:.2f}%  "
          f"(할인전 {g['breakdown']['base_growth_after_fcf_check']*100:.2f}%)")
    print(f"Implied Growth : {ig['value']*100:.2f}%  ({ig['model_used']}) "
          f"[single {ig['models']['single_stage']*100:.2f}% / "
          f"two {ig['models']['two_stage']*100:.2f}%, "
          f"괴리 {ig['models']['divergence']*100:.2f}%p]")
    print(f"Expectation Gap: {result['expectation_gap']*100:+.2f}%p  "
          f"-> {result['judgment']} ({result['judgment_grade']})")
    print(f"RAR            : {result['rar']:+.4f}")
    print(f"Confidence     : {result['confidence']['final']}/100")
    sc = result.get("sensitivity_check") or {}
    print(f"강건성점검     : flip={sc.get('judgment_flipped')}")
    sbc = result.get("sbc_cross_check") or {}
    if sbc.get("sbc_to_fcf_pct") is not None:
        print(f"SBC 교차검증   : SBC/FCF {sbc['sbc_to_fcf_pct']*100:.1f}%  "
              f"Gap {sbc['gap_sbc_adjusted']*100:+.2f}%p  "
              f"flip={sbc['judgment_flipped']}")
    print("\n[data_limitations]")
    for lim in result.get("data_limitations") or []:
        print(f"  - {lim}")
    print(f"\nsaved: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
