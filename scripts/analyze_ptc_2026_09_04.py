"""
PTC Inc.(PTC) 재분석 - 2026-09-04. **보유 포트폴리오 최대비중(38.4%) 종목.**

경위: 사용자 실제 보유 포트폴리오 심층분석의 1순위. 기존 ledger는
2026-08-02·엔진 v3.25로 **33일 전·8버전 뒤**였고, 그 사이 (a)시가총액이
$147.3억->$162.9억(+10.5%)로 올랐고 (b)Kepware/ThingWorx 매각이 완료됐으며
(c)엔진에 v3.60(capex 태그)·v3.67(규모 조건부 성장상한) 등 계산을 실제로
바꾸는 변경이 있었다.

## ⚠️ 주관적 입력을 의도적으로 고정했다 - 변화의 원인을 분리하기 위해

`competitor_threat_weights=[0.4,0.35,0.2]` / `market_share_trend=+0.5` /
`demand_sensitivity_pct=0.25` / `model_used=two_stage`를 **2026-08-02판과
동일하게 유지**했다. 이렇게 해야 Gap 변화가 "내가 주관값을 다시 찍어서"가
아니라 **데이터·엔진 변화에서 왔다**는 것이 확인된다(ROP 크로스체크가
확립한 통제 방식). 바꾼 것은 다음 4가지뿐이고 전부 근거가 있다:

1. **시가총액**: $147.3억 -> **$162.9억**(주가 $150.08 x 발행주식 1.085억,
   2026-09-03 종가 / 2026-07-29 10-Q 표지). 발행주식이 1년새 1.198억->
   1.085억으로 **-9.4%** 감소($16억 자사주매입 프로그램) - 주가상승과
   주식수감소가 동시에 일어나 시총은 순증했다.
2. **순부채**: 2026-06-30 기준 $13.98억 - 현금 $3.51억 = **$10.47억**
   (매각대금 유입에도 자사주매입으로 차입이 늘어 순부채는 소폭 증가).
3. **데이터 창**: FY2017~2025(9개년)를 **그대로 유지**했다. ⚠️ 처음엔
   FY2015~2025(11개년)로 넓혀 진짜 10년 CAGR을 쓰려 했으나 **실행 후
   되돌렸다** - 그 창을 쓰면 DRS가 44.4->56.4(+12점)로 뛰고 Lynch 유형이
   stalwart->cyclical로 바뀌는데, 원인을 추적하니 **FY2016 매출감소
   (-9.1%)·영업적자가 경기순환이 아니라 영구라이선스->구독 전환의 회계적
   착시**였다. SEC 공시 원문: "Revenue was down year over year due to a
   higher mix of subscription revenue in 2016 compared to 2015 as the
   company transitioned from selling perpetual licenses to a
   subscription-based licensing model."(2026-09-04 WebSearch 확인).
   FY2019 매출($12.56억)이 FY2015($12.55억)과 거의 같은 전형적인 구독전환
   U자 곡선이며, PTC는 2018-01-01자로 영구라이선스 판매를 완전히 중단했다.
   이를 경기순환성으로 세면 일회성·기지(旣知)의 회계전환을 **영구적
   할인율 상승**으로 바꾸는 것이라 과대계상이다(CROX·MEDP의 ASC 606
   태그전환 사례와 동일 계열). FY2015~2025 변형은 별도 크로스체크로 병기.
4. **SBC 시계열 추가**: 기존 ledger는 `sbc_cross_check`가 **None**이었다
   (v3.23 배선 이전 분석). FY2025 SBC $2.162억 = FCF의 **25.2%**로 결코
   무시할 수 없는 수준이라 반드시 병기가 필요하다.
   (risk_free_rate도 0.0447->0.0475로 현재 코퍼스 표준에 맞췄다.)

## ⚠️ Kepware/ThingWorx 매각(2026-03-13 완료) - FY2025 재무제표에는 아직
포함돼 있다

TPG에 매각, 종결 시 **$5.23억 수령**, 매각이익 $4.63억(비영업), 세후
순유입 약 $3.75억, FY2026 현금흐름에 매각관련 유출 약 $1.5억(비용 $0.4억
+ 현금세금 $1.1억) 반영 예정(2026-09-04 WebSearch, 회사 IR).

**규모**: Q2'26 ARR이 as-reported +3%YoY인데 매각분 제외 기준으로는
+7.5~9.5%(CC) - 즉 **매각된 사업은 ARR의 약 5~6%**. APTV(사업부 절반을
분할)와 달리 회사 정체성을 바꾸는 규모가 아니라 정량모델 적용은 유효하다.
다만 **이 분석의 FY2025 기저에는 이제 보유하지 않는 사업 약 5~6%가 아직
들어 있다** - 그만큼 성장·이익 기저가 과대다. 아래 크로스체크에서 이를
보정한 시나리오를 병기한다.

## ⚠️ 가장 중요한 한계 - GAAP 매출 CAGR이 회사 자신의 ARR 성장률보다 높다

trailing 매출 CAGR: 3y **12.32%** / 5y **13.44%** / 10y **8.11%**.
회사 자체 지표(ARR, 매각분 제외 CC): FY2026 가이던스 **7.5~9.5%**,
Q3'26 실적 **9.1%**(가이던스 상단 상회).

PTC는 ASC 606상 온프레미스 라이선스 매출을 **선인식**하기 때문에 GAAP
매출이 계약 타이밍에 따라 출렁이며, 회사 스스로 매출이 아니라 ARR·FCF로
가이던스를 준다. 즉 **trailing 매출 CAGR이 구독 기반 지속성장률을
과대표시할 가능성**이 있다 - ROP(회사 공시 오가닉 5~6% vs 엔진 12% 캡)와
같은 계열의 위험이다.

**그럼에도 `realistic_growth_override`를 쓰지 않았다.** ROP 승격 때
확립한 기준은 "여러 분기에 걸쳐 실제로 실현된 다년 오가닉 실적"인데,
PTC의 ARR은 (a)매출과 정의가 다른 지표이고(영구라이선스·전문서비스 제외)
(b)9.1%는 최근 분기 실적이라 다년 실현치가 아니다. KEYS 선례("검증 안 된
1개년 가이던스로 override하지 않는다")를 따라 **공식 판정은 건드리지 않고
아래 크로스체크로 병기**한다.

## 실행: python3 scripts/analyze_ptc_2026_09_04.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.filing_dates import pit_inputs_for
from engine.pipeline import AnalysisInputs, run_analysis, save_ledger
from engine.provenance import provenance_from_sec_facts

TICKER = "PTC"
UA = "IRS Research chlalsrl1203@gmail.com"
TODAY = "2026-09-04"

# ── SEC XBRL companyfacts 실측(2026-09-04 조회, CIK 0000857005) ──────────
# 회계연도는 9월말 결산(FY2025 = 2024-10~2025-09). FY2026은 아직 미제출.
REVENUE = {
    2017: 1164039000.0, 2018: 1241824000.0,
    2019: 1255631000.0, 2020: 1458415000.0, 2021: 1807159000.0, 2022: 1933347000.0,
    2023: 2097053000.0, 2024: 2298472000.0, 2025: 2739226000.0,
}
OPERATING_INCOME = {
    2017: 40898000.0, 2018: 73237000.0,
    2019: 63042000.0, 2020: 210863000.0, 2021: 380748000.0, 2022: 447362000.0,
    2023: 458474000.0, 2024: 588062000.0, 2025: 982385000.0,
}
OPERATING_CASHFLOW = {
    2017: 134590000.0, 2018: 247811000.0,
    2019: 285145000.0, 2020: 233808000.0, 2021: 368809000.0, 2022: 435326000.0,
    2023: 610861000.0, 2024: 749984000.0, 2025: 867696000.0,
}
CAPEX = {
    2017: 25444000.0, 2018: 36041000.0,
    2019: 64411000.0, 2020: 20196000.0, 2021: 24713000.0, 2022: 19496000.0,
    2023: 23814000.0, 2024: 14378000.0, 2025: 11008000.0,
}
NET_INCOME = {  # 참고 기록만 - is_insurer 아니므로 계산에 미사용
    2017: 6239000.0, 2018: 51987000.0,
    2019: -27460000.0, 2020: 130695000.0, 2021: 476923000.0, 2022: 313081000.0,
    2023: 245540000.0, 2024: 376333000.0, 2025: 733997000.0,
}
SBC = {  # ⭐ 기존 ledger에 없던 항목(v3.23 배선 이전 분석이라 sbc_cross_check=None이었음)
    2017: 76708000.0, 2018: 82939000.0,
    2019: 86400000.0, 2020: 115149000.0, 2021: 177289000.0, 2022: 174863000.0,
    2023: 206459000.0, 2024: 223461000.0, 2025: 216205000.0,
}

# ── 대차대조표(2026-06-30, FY2026 Q3 10-Q - 매각·자사주매입 반영 최신값) ──
DEBT_LATEST = 1398241000.0   # LongTermDebt
CASH_LATEST = 351454000.0    # CashAndCashEquivalentsAtCarryingValue
NET_DEBT = DEBT_LATEST - CASH_LATEST  # $1,046,787,000

DA_2025 = 102504000.0  # DepreciationDepletionAndAmortization(FY2025)
EBITDA = OPERATING_INCOME[2025] + DA_2025  # $1,084,889,000

# ── 시가총액(2026-09-03 Alpha Vantage 종가 + 2026-07-29 10-Q 표지 주식수) ──
PRICE = 150.08
SHARES_OUT = 108506261.0   # 1년 전 119,792,704주 대비 -9.4%(자사주매입)
MARKET_CAP = PRICE * SHARES_OUT  # 약 $16.285B (기존 ledger $14.73B 대비 +10.5%)

RF = 0.0475


def build_inputs() -> AnalysisInputs:
    pit = pit_inputs_for(TICKER, TODAY, list(REVENUE), user_agent=UA)

    provenance = None
    try:
        from engine.data.providers.sec import fetch_company_facts, ticker_to_cik

        cik = ticker_to_cik(TICKER, UA)
        facts = fetch_company_facts(cik, UA)
        provenance = provenance_from_sec_facts(facts, TICKER, TODAY, list(REVENUE))
    except Exception:  # noqa: BLE001 - provenance는 부가 기록, 실패해도 분석은 계속
        provenance = None

    return AnalysisInputs(
        ticker=TICKER,
        company_name="PTC Inc.",
        revenue_by_year=REVENUE,
        operating_income_by_year=OPERATING_INCOME,
        operating_cashflow_by_year=OPERATING_CASHFLOW,
        capex_by_year=CAPEX,
        market_cap=MARKET_CAP,
        net_debt=NET_DEBT,
        ebitda=EBITDA,
        risk_free_rate=RF,
        # ⚠️ 아래 3개 주관값은 2026-08-02판과 **의도적으로 동일**하게 유지했다
        competitor_threat_weights=[0.4, 0.35, 0.2],
        market_share_trend_pp_per_year=0.5,
        active_antitrust_or_regulatory_case=False,
        demand_sensitivity_pct=0.25,
        subjective_input_basis=(
            "⚠️ 2026-08-02판(v3.25)과 **동일한 주관값을 의도적으로 유지**했다 - "
            "Gap 변화가 주관값 재추측이 아니라 데이터·엔진 변화에서 온 것임을 "
            "분리하기 위함(ROP 크로스체크가 확립한 통제 방식). 원 근거: "
            "Siemens Digital Industries Software 0.40(NX/Teamcenter, 가장 "
            "포괄적인 CAx 플랫폼), Dassault Systemes 0.35(SolidWorks/CATIA/"
            "ENOVIA, 중견~대형 제조업 전반 강세), Autodesk 0.20(Fusion 360 등 "
            "일부 세그먼트 중첩) - 셋 다 [추정치], PTC/Siemens/Dassault를 "
            "CAD·PLM '빅3'로 보는 업계 통설 기반. market_share_trend=+0.5pp: "
            "2026-07 ABI Research가 PTC를 대형 제조업체 대상 PLM 부문 경쟁력 "
            "1위로 평가. demand_sensitivity_pct=0.25 - 기업용 필수 SW(앵커 "
            "0.20)이되 제조업 설비투자 사이클 노출을 반영해 소폭 상향. "
            "2026-09-04 재확인 사항: Q3'26 ARR +9.1%YoY로 가이던스 상단을 "
            "상회해 경쟁력 훼손 증거는 나타나지 않았다."
        ),
        model_used="two_stage",
        model_choice_reason=(
            "2026-08-02판과 **동일하게 two_stage 유지**(주관값 고정 원칙). "
            "원 근거: 관측구간 내내 흑자이며 최근 3개년 영업이익이 매출성장을 "
            "크게 앞서는 마진확장 국면(FY24->FY25 매출 +19.2%, 영업이익 "
            "+67.1%)이라 명시적 성장기간 후 정상화를 모델링하는 two_stage가 "
            "궤적에 부합. ⚠️ 단 GAAP 매출 CAGR(3y 12.32%)이 회사 자신의 ARR "
            "성장률(FY26 가이던스 7.5~9.5% CC, Q3'26 실적 9.1%)보다 높다 - "
            "ASC 606 온프레미스 라이선스 선인식 때문이며, 이 괴리는 "
            "falsification_conditions와 별도 크로스체크로 병기한다."
        ),
        falsification_conditions=(
            "① FY2026 Q4 실적(2026-11월경 예상)에서 매각분 제외 ARR 성장률이 "
            "회사 가이던스 하단(7.5% CC)을 밑돌면 재검토. ② FY2026 FCF가 "
            "가이던스(약 $10억, 매각관련 유출 $1.5억 반영 후)를 크게 하회하면 "
            "재검토. ③ Kepware/ThingWorx 매각으로 ARR 기저가 5~6% 축소된 "
            "상태에서 FY2027 가이던스가 한자릿수 초반으로 제시되면, GAAP "
            "매출 CAGR(12%대)이 아니라 그 수치를 성장 기준으로 재검토할 것."
        ),
        price_at_analysis=PRICE,
        currency="USD",
        net_income_by_year=NET_INCOME,
        sbc_by_year=SBC,
        data_sources=[
            "SEC XBRL companyfacts (CIK 0000857005, 조회 2026-09-04)",
            "Alpha Vantage GLOBAL_QUOTE (2026-09-03 종가 $150.08)",
            "SEC 10-Q 표지 발행주식수 (2026-07-29 기준 108,506,261주)",
            "WebSearch: Kepware/ThingWorx 매각 조건($5.23억 수령·$4.63억 "
            "매각이익·ARR 5~6% 규모), FY2026 가이던스(ARR 7.5~9.5% CC, "
            "FCF 약 $10억), Q3'26 ARR +9.1%(2026-09-04 재인용)",
        ],
        **pit,
        provenance=provenance,
    )


if __name__ == "__main__":
    inputs = build_inputs()
    result = run_analysis(inputs)
    path = save_ledger(result)
    print(f"saved: {path}")
