"""
Okta, Inc.(OKTA) 정식 분석 - 2026-09-02.

경위: `scripts/broad_screen.py` 주간 대규모 스크리닝(2026-08-30)에서 통과한
검증범위 안 후보(연구 우선순위 큐, tier B, Gap 추정 +20.65%p, 스크리너
기준 시총 ~$16.4B - 2025-07-31 시점 `EntityPublicFloat` 근사치). LNTH/EQT를
FRAMEWORK_MISMATCH로 제외한 뒤 큐에서 처음으로 정량모델 적용 가능이 확인된
종목이라 정식분석으로 승격한다.

## 원자료 - SEC XBRL companyfacts(1차자료, `SecCompanyFactsProvider`,
2026-09-02 조회, CIK 0001660134, 2017~2026 10개년 확보 - 10y CAGR은
연도수 부족(<11)으로 산출 불가, 5y로 자동 대체됨(v3.25 버그수정 경로,
`data_limitations`에 명시적으로 기록됨).

## ⭐ 핵심 발견 1 - 스크리너 추정치가 완전히 낡았다: 2026-08-27 실적발표 후
+29% 단일일 급등을 놓쳤다

스크리너 시총 근사(~$16.4B, `EntityPublicFloat` 2025-07-31 시점)는 8개월
이상 낡은 값이다. Okta는 2026-08-27(FY2027 Q2, 3개월 종료 2026-07-31) 실적을
발표하며 매출 $805M(컨센서스 상회)·순신규청구서(bookings) 사상 최대(비4분기
기준)·신제품이 전체 예약의 약 30%(신제품 포함 거래는 ACV +40%)를 기록,
FY2027 매출가이던스를 $3.216B~$3.226B(상향)로 제시했다 - 주가가 2026-08-26
종가 $134.42에서 2026-08-27 $172.91로 **하루 만에 +28.6%** 급등했다
(Morgan Stanley/Wells Fargo/BMO/Stifel/Jefferies/Cantor/Truist/KeyBanc가
목표가를 일제히 $180까지 상향). 분석 시점(2026-09-02) 주가 $166.43은 이
급등을 이미 반영한 수준이다.

**정식분석은 이 급등 이후 실시간 시총을 그대로 쓴다** - PTC 사례("분석시점
주가가 실적발표 후 +21% 랠리구간에 걸려있어 Gap이 stale일 가능성")와 동일한
경계가 필요하다는 뜻이지, 급등 자체를 무시하거나 보정할 근거는 없다(주가가
현재 가격이라는 사실 자체를 조정할 수 없다 - `price_at_analysis`는 실측치를
그대로 기록하는 필드다).

## ⭐ 핵심 발견 2 - trailing CAGR(16~28%)이 회사 자체 가이던스(~10%)보다
크게 높다 - KEYS/KLAC/TCOM/GEN과 같은 계열이지만 방향이 반대

FY2026(2026-01-31 종료) 매출 $2,919M -> FY2027 가이던스 중간값 $3,221M =
**+10.35%YoY**. 반면 trailing revenue CAGR은 3y(2023->2026) 16.26%,
5y(2021->2026) 28.43%로 가이던스보다 훨씬 높다. **KEYS/KLAC 계열(trailing
CAGR이 AI 수요 인플렉션을 과소추정해 가이던스가 더 높았던 경우)과 정확히
반대 방향** - 여기서는 trailing CAGR이 최근 성장률 자체(고성장기 기저효과+
최근 감속)를 과대추정하고, 가이던스가 이미 감속을 반영한 더 낮은 수치다.
Realistic Growth가 min(FCF CAGR, 매출가중CAGR)·구조적할인·Lynch캡을 거쳐
가이던스보다 여전히 높게 나오면 이 괴리를 반드시 `data_limitations`/
falsification_conditions에 남긴다(자동 보정하지 않음 - v3.43
growth_scorecard가 확립한 "가이던스를 정답지로 쓰지 않는다" 원칙 - 1개년
가이던스는 다년 실현실적이 아니라 override 자격이 없다).

## ⭐ 핵심 발견 3 - SBC/FCF가 매우 높다(트래커 상위권)

FY2026 SBC $544M vs FCF0 $875M(OCF $884M - capex $9M) = **SBC/FCF 62.2%**.
TTD(62%)·WDAY(59%)급으로, `sbc_by_year`를 채워 SBC 차감 대안 시나리오를
병기한다(v3.23, 판정 자동 변경 없음).

## 부채구조 - 전환사채 대부분 상환/전환 완료(긍정적 신호)

`ConvertibleDebtNoncurrent`가 FY2025 $349M -> FY2026 $0으로, `ConvertibleDebtCurrent`도
FY2025 $509M -> FY2026 $350M로 감소 - 만기 도래분이 상환·전환되며 부채구조가
가벼워지는 중. FY2026말 총부채 $350M(전액 유동성 전환사채) vs 현금
$864M(제한현금 포함) - **순현금 -$514M**(net_debt 음수, 순현금 포지션).

## 경쟁구도(2026-09-02 WebSearch)

Microsoft Entra ID가 최대 위협 - M365/Azure 번들링으로 80만+ 조직·10억+
월간활성사용자 규모(Okta는 19,450개 고객, 2024-10 기준). Gartner MQ에서
Microsoft가 실행력(ability to execute)에서 Okta를 앞서기 시작했고("모멘텀이
Microsoft 쪽으로 이동 중"), Okta는 9년 연속 Leader 유지하되 "혁신성"에서는
여전히 선두. Ping Identity(Thales 소유)가 2선 경쟁자. CyberArk(PAM)·SailPoint
(IGA)는 인접 세그먼트로 직접 경쟁 강도는 상대적으로 낮음.

## 실행: python3 scripts/analyze_okta_2026_09_02.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.filing_dates import pit_inputs_for
from engine.pipeline import AnalysisInputs, run_analysis, save_ledger
from engine.provenance import provenance_from_sec_facts

TICKER = "OKTA"
UA = "IRS Research chlalsrl1203@gmail.com"
TODAY = "2026-09-02"

# ── SEC XBRL companyfacts 실측(2026-09-02 조회) ──────────────────────────
REVENUE = {
    2017: 160806000.0, 2018: 256547000.0, 2019: 399254000.0,
    2020: 586067000.0, 2021: 835424000.0, 2022: 1300201000.0,
    2023: 1858000000.0, 2024: 2263000000.0, 2025: 2610000000.0,
    2026: 2919000000.0,
}
OPERATING_INCOME = {
    2016: -75988000.0, 2017: -83123000.0, 2018: -116362000.0,
    2019: -119622000.0, 2020: -185832000.0, 2021: -204159000.0,
    2022: -767103000.0, 2023: -812000000.0, 2024: -516000000.0,
    2025: -74000000.0, 2026: 149000000.0,
}
OPERATING_CASHFLOW = {
    2016: -41536000.0, 2017: -42101000.0, 2018: -25240000.0,
    2019: 15172000.0, 2020: 55603000.0, 2021: 127962000.0,
    2022: 104119000.0, 2023: 86000000.0, 2024: 512000000.0,
    2025: 750000000.0, 2026: 884000000.0,
}
CAPEX = {
    2016: 4093000.0, 2017: 6253000.0, 2018: 6550000.0,
    2019: 19811000.0, 2020: 15442000.0, 2021: 13083000.0,
    2022: 12310000.0, 2023: 12000000.0, 2024: 8000000.0,
    2025: 8000000.0, 2026: 9000000.0,
}
NET_INCOME = {
    2016: -76302000.0, 2017: -83509000.0, 2018: -114359000.0,
    2019: -125497000.0, 2020: -208913000.0, 2021: -266332000.0,
    2022: -848411000.0, 2023: -815000000.0, 2024: -355000000.0,
    2025: 28000000.0, 2026: 235000000.0,
}
SBC = {
    2016: 9832000.0, 2017: 17127000.0, 2018: 49860000.0,
    2019: 76320000.0, 2020: 126624000.0, 2021: 196181000.0,
    2022: 565480000.0, 2023: 677000000.0, 2024: 684000000.0,
    2025: 565000000.0, 2026: 544000000.0,
}

# ── 대차대조표(FY2026말, 2026-01-31 종료, SEC XBRL 실측) ─────────────────
CASH_2026 = 864000000.0  # CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents
DEBT_CURRENT_2026 = 350000000.0   # ConvertibleDebtCurrent
DEBT_NONCURRENT_2026 = 0.0        # ConvertibleDebtNoncurrent
NET_DEBT = DEBT_CURRENT_2026 + DEBT_NONCURRENT_2026 - CASH_2026  # -514,000,000(순현금)

DA_2026 = 13000000.0 + 83000000.0  # Depreciation + AmortizationOfIntangibleAssets
EBITDA = OPERATING_INCOME[2026] + DA_2026  # 245,000,000

# ── 시가총액(2026-09-02, Alpha Vantage 종가 + 최근 분기 희석주식수) ──────
PRICE = 166.43  # Alpha Vantage GLOBAL_QUOTE, 2026-09-01 종가(latestDay)
SHARES_OUT = 178808000.0  # 10-Q(FY2027 Q2, 3개월 2026-07-31 종료) 희석가중평균
MARKET_CAP = PRICE * SHARES_OUT  # 약 $29.76B

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
        company_name="Okta, Inc.",
        revenue_by_year=REVENUE,
        operating_income_by_year=OPERATING_INCOME,
        operating_cashflow_by_year=OPERATING_CASHFLOW,
        capex_by_year=CAPEX,
        market_cap=MARKET_CAP,
        net_debt=NET_DEBT,
        ebitda=EBITDA,
        risk_free_rate=RF,
        competitor_threat_weights=[0.40, 0.15],
        market_share_trend_pp_per_year=-1.0,
        active_antitrust_or_regulatory_case=False,
        demand_sensitivity_pct=0.20,
        subjective_input_basis=(
            "competitor_threat_weights=[0.40(Microsoft Entra ID), 0.15(Ping Identity)] - "
            "Entra ID가 M365/Azure 번들링으로 80만+ 조직·10억+ MAU 규모(Okta 19,450개 "
            "고객 대비 압도적 스케일), Gartner MQ에서 Microsoft가 실행력 축에서 "
            "Okta를 추월(모멘텀이 Microsoft 쪽으로 이동 중이라는 애널리스트 서술). "
            "Ping(Thales 소유)은 2선 경쟁자, CyberArk/SailPoint는 인접세그먼트(PAM/IGA)"
            "라 직접 위협도는 낮게 반영. market_share_trend_pp_per_year=-1.0 - 위 "
            "'모멘텀 이동' 서술을 반영한 완만한 열세 추세(2026-09-02 WebSearch 종합, "
            "정량 점유율 데이터는 출처마다 상이해 서술적 근거만 확보). "
            "demand_sensitivity_pct=0.20 - CLAUDE.md 업종앵커표 '기업용 필수 SW·전문"
            "서비스(계약기반, 전환비용 높음)' 버킷(CDNS·DSGX·PGR·ROP·BRO 등, 앵커 0.20) "
            "적용 - ID/접근관리는 보안 인프라로 이탈비용이 크고 침해리스크가 예산을 "
            "보호하는 경향(2026-08-27 실적에서 신제품 예약 확대·ACV 상승이 확인돼 "
            "수요 저항력이 실측으로 뒷받침됨)."
        ),
        model_used="two_stage",
        model_choice_reason=(
            "trailing 매출 CAGR(3y 16.26%/5y 28.43%)이 default_terminal_growth"
            "(2.0~4.5%)보다 여전히 크게 높아 다년 수렴 경로가 필요하다고 판단. "
            "다만 FY2027 자체 가이던스(중간값 +10.35%YoY)가 trailing CAGR보다 "
            "훨씬 낮아 - 2026-08-27 실적발표 이후 성장 감속이 회사 스스로 확인한 "
            "사실이라 - Realistic Growth가 가이던스를 크게 상회하면 그 괴리를 "
            "명시적으로 기록한다(v3.43 growth_scorecard 원칙 - 1개년 가이던스는 "
            "override 자격 없음, 병기만)."
        ),
        falsification_conditions=(
            "FY2027(2027-01-31 종료) 실적이 가이던스(매출 $3.216B~$3.226B, EPS "
            "$3.90~$3.94) 하단에도 미달하거나, 다음 분기 순신규청구서(bookings) 성장률이 "
            "재차 둔화되거나, Microsoft Entra ID로의 고객 이탈(migration) 사례가 "
            "구체적으로 보고되면 이 판정을 재검토할 것. 2026-08-27 실적 서프라이즈 "
            "이후 애널리스트 목표가 상향(최대 $180)이 후속 분기에서 정당화되지 "
            "않으면(예: 다음 실적에서 신제품 ACV 상승세 재확인 실패) 이번 급등이 "
            "과잉반응이었을 가능성."
        ),
        price_at_analysis=PRICE,
        currency="USD",
        net_income_by_year=NET_INCOME,
        sbc_by_year=SBC,
        data_sources=[
            "SEC XBRL companyfacts (CIK 0001660134, 조회 2026-09-02)",
            "Alpha Vantage GLOBAL_QUOTE (2026-09-01 종가 $166.43)",
            "WebSearch: Okta FY2027 Q2 실적발표(2026-08-27), 경쟁구도(Gartner MQ 서술)",
        ],
        **pit,
        provenance=provenance,
    )


if __name__ == "__main__":
    inputs = build_inputs()
    result = run_analysis(inputs)
    path = save_ledger(result)
    print(f"saved: {path}")
