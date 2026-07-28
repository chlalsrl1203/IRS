"""
Trip.com Group(TCOM) 정식 분석 - 2026-07-28.

경위: 2026-07-26 스크리닝 통과 후보를 정식분석한다. 비큐(ad-hoc) 분석
(BKNG/PDD와 동일 범주). 애초에 "BKNG보다 더 심한 버전의 조회창 문제"로
플래그했던 종목이다 - 실제로 대조해보니 그 우려가 부분적으로만 맞았다(아래 참고).

⚠️ **BKNG과 같은 문제, 그러나 한 겹 더**: TCOM은 중국 본토 여행수요 기업이라
중국의 제로코로나 정책이 2022년 12월까지 유지됐다. 그 결과:
  (1) 기본 5년 룩백(FY2020)은 BKNG과 동일한 문제 - FY2020 FCF가
      -RMB 43.55억(OCF -38.23억 - capex 5.32억)로 음수라 CAGR 자체가 불가능.
      -> BKNG과 동일하게 cagr_base_year_override=2019(코로나 이전 고점)로 해결.
  (2) **BKNG에는 없던 문제**: 3년 CAGR(고정 windows[-4], override 영향 안 받음)의
      기준연도가 FY2022인데, 중국은 그 시점까지도 제로코로나로 억눌려 있었다
      (FY2022 매출 200.39억이 FY2019 356.66억의 56%에 불과 - 아직 회복 전).
      그 결과 매출 3y CAGR이 46.04%로 산출되는데 이는 '성장'이 아니라 '억눌림
      해제'다. pipeline.py의 cagr_base_year_override는 5y/FCF 창만 바꾸고
      3y 창(revenue_cagr_3y)은 건드리지 않으므로 이 왜곡은 override로 막을 수
      없다.
  => **그런데도 엔진 코드 변경이 필요 없었다**: realistic_growth_estimate()의
     FCF보수원칙(min(FCF CAGR, 매출가중평균) 채택)이 이미 이 문제를 흡수한다.
     매출가중평균(3y 46.04% x0.5 + 6y 9.78% x0.3 + 10y 19.07% x0.2 = 29.77%)이
     여전히 왜곡돼 있어도, override 적용한 FCF 6y CAGR(13.04%)이 그보다 훨씬
     낮아 FCF CAGR이 채택되며 왜곡이 최종 Realistic Growth로 새지 않는다.
     대신 왜곡된 3y 매출 변동성은 DRS의 revenue_volatility로 흘러들어가는데,
     이건 버그가 아니라 **의도된 동작**이다 - 코로나 붕괴+회복의 진폭 자체가
     실재하는 리스크이므로 DRS가 이를 반영해 구조적할인을 높이는 것이 맞다.
     이 사례를 통해 v3.21 기능의 설계(FCF보수원칙이 1차 방어선, 기준연도
     override는 2차 방어선)가 BKNG보다 더 나쁜 조건에서도 작동함을 확인했다.

⚠️ **2026-07-25 SAMR 반독점 과징금(분석일 3일 전, 매우 최근)**: 중국
국가시장감독관리총국이 2020년부터 이어진 호텔예약 플랫폼 반독점 행위(배타조항,
트래픽 통제로 가격결정권 제한 - 반독점법 22조4·5항 위반 확정)에 대해
52.79억위안(약 7.65억달러) 제재를 확정했다(불법이득 몰수 16.58억+과징금
35.21억+호텔보증금 환급 1.22억). 조사가 2026-01-14 개시돼 6개월만에 결론난
사건으로, BKNG의 스페인 과징금(항소심까지 집행정지)과 달리 **이미 확정**된
제재다. 시가총액은 2026-07-27 종가(과징금 발표 이후 반영) 기준을 사용해
밸류에이션에는 이미 시장 반응이 녹아있으나, FY2026 FCF에는 약 51.8억위안
(FY2025 FCF 135.82억의 약 38%)의 일회성 현금유출이 예상되며 이는 과거
재무제표(FY2014~2025)에는 반영되지 않은 향후 리스크임을 data_limitations에
명시한다.

원자료: 전부 SEC EDGAR as-filed 20-F에서 직접 추출(2026-07-28 조회).
  FY2025 20-F(0001193125-26-183379) R2/R3/R7 - FY2023~2025 + 재무상태표
  FY2022 20-F(0001193125-23-080422) R2/R7 - FY2020~2022
  FY2019 20-F(0001193125-20-102627) R2/R7 - FY2017~2019
  FY2016 20-F(0001104659-17-023278) R2/R7 - FY2014~2016(당시 사명 Ctrip.com International)
시가총액: stockanalysis.com 2026-07-27 종가 기준 $28.19B(주가 $44.77 x 629.71M주,
  SAMR 과징금 발표 이후 반영된 가격).
환율: USD/CNY 6.7716(기존 프로젝트에서 검증된 값, PDD/TCOM 스크리닝과 동일).

실행: python3 scripts/analyze_tcom_2026_07_28.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.pipeline import AnalysisInputs, run_analysis, save_ledger

M = 1_000_000

# ── SEC EDGAR as-filed 실측 (단위: RMB, 원 단위) ────────────────────────
REVENUE = {
    2014: 7346.918369 * M, 2015: 10897.568061 * M, 2016: 19228.439814 * M,
    2017: 26796 * M, 2018: 30965 * M, 2019: 35666 * M,
    2020: 18316 * M,                      # 코로나: 전년比 -48.65%
    2021: 20023 * M, 2022: 20039 * M,     # 中 제로코로나 지속 - 아직 회복 전
    2023: 44510 * M, 2024: 53294 * M, 2025: 62409 * M,
}
OPERATING_INCOME = {
    2014: -150.797144 * M, 2015: 381.042945 * M, 2016: -1568.478486 * M,
    2017: 2943 * M, 2018: 2605 * M, 2019: 5040 * M,
    2020: -1423 * M, 2021: -1411 * M, 2022: 88 * M,
    2023: 11324 * M, 2024: 14177 * M, 2025: 15773 * M,
}
OPERATING_CASHFLOW = {
    2014: 1958.603856 * M, 2015: 3048.809916 * M, 2016: 5272.730491 * M,
    2017: 7069 * M, 2018: 7115 * M, 2019: 7333 * M,
    2020: -3823 * M,                      # 코로나: 영업활동현금흐름 자체가 마이너스
    2021: 2475 * M, 2022: 2641 * M,
    2023: 22004 * M, 2024: 19625 * M, 2025: 14379 * M,  # FY25 YoY -26.7%
}
CAPEX = {
    2014: 4788.676371 * M,   # 당시 대규모 시설투자(이례적으로 높음, 10y CAGR
                              # 기준연도가 아니라 계산에 영향 없음 - 아래 참고)
    2015: 638.13343 * M, 2016: 682.83131 * M,
    2017: 471 * M, 2018: 673 * M, 2019: 823 * M,
    2020: 532 * M, 2021: 570 * M, 2022: 497 * M,
    2023: 606 * M, 2024: 591 * M, 2025: 797 * M,
}

# 재무상태표 (FY2025 20-F R3, 2025-12-31 기준)
CASH = 39848 * M
SHORT_TERM_INVESTMENTS = 32007 * M
# 제한현금(6,603M)은 자유롭게 부채상환에 쓸 수 없어 보수적으로 제외(BKNG/PDD와 동일 원칙).
SHORT_TERM_DEBT = 19335 * M   # 유동성 단기차입금 + 장기차입금 유동분
LONG_TERM_DEBT = 11430 * M
NET_DEBT = (SHORT_TERM_DEBT + LONG_TERM_DEBT) - (CASH + SHORT_TERM_INVESTMENTS)

DA_2025 = (647 + 198) * M   # 감가상각 647M + 무형자산/토지사용권 상각 198M
                             # (사용권자산 상각 250M은 리스 관련이라 제외 - BKNG 관행과 동일)
EBITDA = OPERATING_INCOME[2025] + DA_2025

USD_CNY = 6.7716
MARKET_CAP = 28.19e9 * USD_CNY   # RMB 환산 (재무제표 통화와 일치시킴)
RF = 0.0447


def build_inputs() -> AnalysisInputs:
    return AnalysisInputs(
        ticker="TCOM",
        company_name="Trip.com Group Limited",
        revenue_by_year=REVENUE,
        operating_income_by_year=OPERATING_INCOME,
        operating_cashflow_by_year=OPERATING_CASHFLOW,
        capex_by_year=CAPEX,
        market_cap=MARKET_CAP,
        net_debt=NET_DEBT,
        ebitda=EBITDA,
        risk_free_rate=RF,

        competitor_threat_weights=[0.35, 0.25, 0.20],
        market_share_trend_pp_per_year=0.0,
        active_antitrust_or_regulatory_case=True,
        demand_sensitivity_pct=0.55,
        subjective_input_basis=(
            "Meituan 0.35(로컬라이프서비스 슈퍼앱 트래픽으로 호텔쿠폰 교차판매 - "
            "가장 구조적인 위협), Tongcheng-Elong 0.25(Tencent/WeChat 미니프로그램 "
            "유통망으로 저가・하위도시 공략), Fliggy 0.20(Alipay 13억 사용자 "
            "생태계와 결제 연동). 셋 다 [추정치]. 다만 2026-07 WebSearch 기준 "
            "TCOM이 여행객 선호도 68.7%(2025)로 '독보적 1위'라는 시장조사가 "
            "확인되어 위협도를 PDD(3파전, 순위 밀림)보다는 낮게 잡았다. "
            "market_share_trend=0.0: 1위 지위가 유지되고 있다는 근거는 있으나 "
            "정량적 추세치를 뒷받침할 시계열 데이터가 없어 중립 처리[추정치]. "
            "active_antitrust_or_regulatory_case=True: 근거가 이 프로젝트에서 "
            "가장 명확하고 최신이다 - 中 SAMR이 2026-01-14 조사 개시, "
            "**2026-07-25(분석일 3일 전) 52.79억위안(약 7.65억달러) 제재 확정**"
            "(불법이득몰수 16.58억+과징금 35.21억+보증금환급 1.22억). 2020년부터 "
            "이어진 배타조항・트래픽통제로 호텔사업자의 가격결정권을 제한한 혐의가 "
            "인정돼 반독점법 22조 4·5항 위반으로 **이미 확정**됐다(BKNG 스페인건은 "
            "항소심까지 집행정지 중인 것과 대조적 - TCOM 건이 법적으로 더 확정적). "
            "demand_sensitivity=0.55: 중국 내수・해외여행 재량소비 - FY2020 매출이 "
            "-48.65% 폭락한 실측 이력이 있어(BKNG -54.9%와 유사한 규모) 여행업종"
            "전형의 높은 값 채택. BKNG(0.60)보다 근소하게 낮게 잡은 이유는 TCOM이 "
            "중국 국내여행 비중이 상대적으로 높아 완전한 해외재량소비 성격의 "
            "BKNG보다는 소폭 완충 여지가 있다고 판단했기 때문[추정치]."
        ),

        model_used="two_stage",
        model_choice_reason=(
            "FY2023(회복 초입, 매출 +122% - 2022 억눌림 기저효과) 이후 "
            "FY2024 +19.7%, FY2025 +17.1%로 안정화되는 두자릿수 성장 궤적을 "
            "보인다. 1위 사업자 지위(선호도 68.7%)를 유지하며 명시적 성장기간 "
            "이후 터미널로 수렴하는 구조가 이론적으로 더 부합한다고 판단해 "
            "two_stage 채택(BKNG/PDD와 동일 논리). 이 종목은 첫 정식분석이라 "
            "대조할 과거 기록이 없다 - 실제 괴리는 divergence_warning 필드로 "
            "확인하고 3%p 미만이면 모델선택이 판정을 바꾸지 않는다는 뜻이므로 "
            "이 사유가 그대로 유효하다."
        ),

        cagr_base_year_override=2019,
        cagr_base_year_override_reason=(
            "기본 기준연도 FY2020은 코로나 직격탄을 맞은 해라 BKNG과 동일한 "
            "이유로 사용 불가하다. (1) FCF가 -RMB 43.55억(OCF -38.23억 - capex "
            "5.32억)로 음수여서 CAGR이 수학적으로 정의되지 않는다. (2) 매출도 "
            "전년比 -48.65% 폭락한 저점이다. 대안으로 **FY2019(코로나 이전 "
            "고점, 직전연도까지 꾸준히 증가하다 코로나로 꺾인 지점)**를 골랐다 - "
            "저점이 아닌 고점 기준이므로 성장률을 부풀리지 않는다. 단, 이 "
            "override는 5y/FCF 창에만 적용되고 고정된 3y 창(기준연도 FY2022)은 "
            "여전히 中 제로코로나 지속기(2022년 12월까지)라 왜곡돼 있다 - 이 "
            "잔여 왜곡은 realistic_growth_estimate의 FCF보수원칙(min 채택)이 "
            "구조적으로 흡수함을 실행 결과로 확인했다(위 모듈 docstring 참고)."
        ),

        data_sources=[
            "SEC EDGAR 20-F FY2025(0001193125-26-183379) R2/R3/R7, as-filed, 2026-07-28 조회",
            "SEC EDGAR 20-F FY2022(0001193125-23-080422) R2/R7 (FY2020~2022)",
            "SEC EDGAR 20-F FY2019(0001193125-20-102627) R2/R7 (FY2017~2019)",
            "SEC EDGAR 20-F FY2016(0001104659-17-023278) R2/R7 (FY2014~2016, 당시 사명 Ctrip.com International)",
            "stockanalysis.com 시가총액 $28.19B (2026-07-27 종가, SAMR 과징금 발표 이후)",
            "USD/CNY 6.7716 (기존 프로젝트 검증치, PDD와 동일)",
            "WebSearch: 中 SAMR 反독점 과징금 52.79억위안(PYMNTS/Caixin/SCMP/MLex, "
            "2026-07-25 확정), 中 온라인여행 시장 경쟁구도(Mordor Intelligence, 2025 선호도 68.7%)",
        ],
    )


def main():
    result = run_analysis(build_inputs())
    d, g = result["derived"], result["growth"]
    models = result["implied_growth"]["models"]

    print("=" * 100)
    print(f"TCOM 정식 분석 결과 ({result['meta']['analyzed_at'][:10]}, 엔진 {result['meta']['engine_version']})")
    print("=" * 100)
    print(f"  CAGR 기준연도    : {d['cagr_5y_base_year']}년 ({d['cagr_5y_span']}년 구간, 5y/FCF만 override)")
    rev_10y_str = "N/A" if d['revenue_cagr_10y'] is None else f"{d['revenue_cagr_10y']*100:.2f}%"
    print(f"  매출 CAGR        : 3y {d['revenue_cagr_3y']*100:.2f}%(고정창, 中 제로코로나 잔여왜곡) / "
          f"{d['cagr_5y_span']}y {d['revenue_cagr_5y']*100:.2f}% / 10y {rev_10y_str}")
    print(f"  FCF CAGR         : {d['fcf_cagr_5y']*100:.2f}%   (FCF0 {d['fcf0']/1e9:.3f}B RMB)")
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
