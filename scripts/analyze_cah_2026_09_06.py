"""
Cardinal Health, Inc.(CAH) 정식 분석 - 2026-09-06.

경위: 2026-09-06 연구 우선순위 큐 상위(스크리너 추정 Gap +7.07%p, tier A,
시총 근사 ~$48.19B). 같은 배치 15개 후보를 SEC 매출 시계열로 구조 선별한
결과 CAH가 가장 깨끗했다 - 19개년(2008~2026) 전 구간에서 25%를 넘는 단계상승이
**한 번도 없고**, 매출·영업이익·영업현금흐름·capex 네 계열이 전부 확보된다.

⭐ **이 종목의 특수성 - 동일 산업 peer 2종목이 이미 ledger에 있다.** 미국
의약품유통은 McKesson(MCK) · Cencora(COR) · Cardinal Health 3사 과점이고
앞의 둘은 2026-07-28/08-02에 정식분석돼 있다. 주관적 입력(경쟁강도 가중치·
수요민감도·모델선택)을 **두 peer와 정확히 동일하게 맞췄다** - 같은 산업구조에
다른 가정을 쓰면 세 종목의 Gap 차이가 사업 차이인지 내 입력 차이인지 구분되지
않는다(COR 분석이 MCK와 동일 가중치를 쓴 것과 같은 논리를 3번째로 확장).

## ⚠️ 데이터상 주의 3건

**(1) FY2026 영업현금흐름이 전년의 2.16배($2,397M -> $5,174M)다.**
유통업 특유의 운전자본(매입채무 결제 타이밍) 변동이며, 과거에도 진폭이 컸다
($3,122M(22) -> $2,839M(23) -> $3,762M(24) -> $2,397M(25) -> $5,174M(26)).
이 프로젝트의 관례대로 **FCF0는 최근연도 단일값을 그대로 쓴다**(관례를 벗어나
평균을 쓰면 새 규칙을 발명하는 것이라 하지 않았다) - 다만 그 결과 FCF수익률
7.87%가 3년 평균 기준(약 5.6%)보다 유의미하게 높다는 사실을 반증조건에
명시한다. 이 한 해가 일시적 스윙이면 Gap이 과대평가된 것이다.

**(2) 영업이익이 2018/2020/2022년에 붕괴한다**(각 $126M / -$4,098M / -$596M).
FY2020은 오피오이드 소송충당금(MCK·COR와 같은 3사 $21B 전국합의의 일부),
2018/2022는 Medical 부문 영업권·무형자산 손상차손이다. **GAAP 원자료를 그대로
쓴다**(CROX HEYDUDE 손상차손·BSX와 동일 원칙 - 임의 정규화 금지). 엔진의
margin_volatility는 최근 5개년(FY2022~2026)만 보므로 2018/2020은 자동 제외되고
2022의 -$596M만 반영된다.

**(3) 자기자본이 FY2022부터 음수다**(FY2026 -$2,883M). 공격적 자사주매입의
결과이며(AutoZone·Domino's형), 영업현금흐름이 강하게 플러스라 존속위험이
아니다 - v3.75 B게이트가 "자기자본<0 AND 영업현금흐름<0"을 함께 요구하도록
설계된 이유가 정확히 이 패턴이다. 이 엔진은 net_debt를 기업가치가 아니라
DRS의 leverage 항목으로만 쓰므로(v3.82에서 확인) 음수 자기자본 자체는
밸류에이션 경로에 들어가지 않는다.

## FY2026 매출 +14.2%의 성격 - M&A 왜곡이 아니다

FY2025가 -1.9% 역성장한 뒤의 반등이라 기저효과가 섞여 있다(대형 고객
이탈로 알려진 구간). FY2026 Q4 단독 매출성장은 +6%로 연간 +14%보다 훨씬
낮아, 연간 수치가 상반기에 몰려 있었음을 보여준다. 인수(GI Alliance·
Solaris Health·Integrated Oncology Network)는 전부 소형 "Other" 부문이고
회사 자체 FY2027 가이던스도 인수 기여를 **Other 부문 이익성장의 2%p**로만
제시한다 - 연결매출 $254B 대비 미미해 GEN/BRO/ROP형 CAGR 왜곡에 해당하지
않는다. 3y/5y/10y 매출 CAGR이 7.4%/9.4%/7.7%로 서로 근접한 것이 그 증거다
(M&A 단계상승이 있으면 이 셋이 크게 갈린다).

## ⚠️ SBC 태그 불일치(판정에는 영향 없음)

`ShareBasedCompensation`(현금흐름표 가산액)과 `AllocatedShareBasedCompensation
Expense`가 FY2025~2026에서 갈린다(244/367 vs 121/122). FCF 조정 목적에는
**OCF에 실제로 가산된 금액**인 전자가 정의상 맞으므로 전자를 채택했다.
어느 쪽을 써도 SBC/FCF가 8.1% vs 2.7%로 둘 다 낮아 판정에 영향이 없음을
확인했다(TYL 사고와 달리 이번엔 불일치가 판정을 흔들지 않는다는 것까지
확인한 뒤 넘어간다).

원자료: SEC XBRL companyfacts(CIK 0000721371), 2026-09-06 조회. 회계연도는
매년 6월 30일 종료. FY2026 10-K는 2026-08-11 제출.

실행: python3 scripts/analyze_cah_2026_09_06.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.filing_dates import pit_inputs_for
from engine.pipeline import AnalysisInputs, run_analysis, save_ledger
from engine.provenance import provenance_from_sec_facts

TICKER = "CAH"
UA = "IRS Research chlalsrl1203@gmail.com"
TODAY = "2026-09-06"
M = 1_000_000

# ── SEC XBRL companyfacts 실측(2026-09-06 조회, FY2016~2026 11개년) ──────
REVENUE = {
    2016: 121546 * M, 2017: 129976 * M, 2018: 136809 * M, 2019: 145534 * M,
    2020: 152922 * M, 2021: 162467 * M, 2022: 181364 * M, 2023: 205012 * M,
    2024: 226827 * M, 2025: 222578 * M, 2026: 254248 * M,
}
OPERATING_INCOME = {
    2016: 2459 * M, 2017: 2120 * M,
    2018: 126 * M,      # Medical 부문 손상차손
    2019: 2060 * M,
    2020: -4098 * M,    # 오피오이드 소송충당금
    2021: 472 * M,
    2022: -596 * M,     # Medical 부문 영업권 손상차손
    2023: 727 * M, 2024: 1243 * M, 2025: 2275 * M, 2026: 2613 * M,
}
OPERATING_CASHFLOW = {
    2016: 2971 * M, 2017: 1184 * M, 2018: 2768 * M, 2019: 2722 * M,
    2020: 1960 * M, 2021: 2429 * M, 2022: 3122 * M, 2023: 2839 * M,
    2024: 3762 * M, 2025: 2397 * M, 2026: 5174 * M,
}
CAPEX = {
    2016: 465 * M, 2017: 387 * M, 2018: 384 * M, 2019: 328 * M,
    2020: 375 * M, 2021: 400 * M, 2022: 387 * M, 2023: 481 * M,
    2024: 511 * M, 2025: 547 * M, 2026: 649 * M,
}
NET_INCOME = {
    2016: 386 * M, 2017: 381 * M, 2018: 255 * M, 2019: 296 * M,
    2020: 350 * M, 2021: 611 * M, 2022: -933 * M, 2023: 261 * M,
    2024: 261 * M, 2025: 1561 * M, 2026: 1714 * M,
}
# 현금흐름표 가산액 기준(us-gaap:ShareBasedCompensation) - docstring 참고
SBC = {
    2016: 111 * M, 2017: 96 * M, 2018: 85 * M, 2019: 82 * M,
    2020: 90 * M, 2021: 89 * M, 2022: 81 * M, 2023: 96 * M,
    2024: 121 * M, 2025: 244 * M, 2026: 367 * M,
}

# 재무상태표(FY2026, 2026-06-30 기준, SEC XBRL)
CASH = 4856 * M
TOTAL_DEBT = 8886 * M          # DebtAndCapitalLeaseObligations(장기 7,004 + 유동 1,882)
NET_DEBT = TOTAL_DEBT - CASH   # $4,030M

DA_2026 = 956 * M              # DepreciationDepletionAndAmortization
EBITDA = OPERATING_INCOME[2026] + DA_2026

# 시가총액: 2026-09-04 종가 x FY2026 10-K 표지 발행주식수
# (dei:EntityCommonStockSharesOutstanding, 2026-07-31 기준) - broad_screen이
# 쓴 EntityPublicFloat 근사($48.19B)보다 최신이라 이쪽을 채택한다(v3.72 한계).
PRICE = 247.18
SHARES_OUT = 232_575_728
MARKET_CAP = PRICE * SHARES_OUT

RF = 0.0477  # 미국 10Y, 2026-09-03 종가(Alpha Vantage TREASURY_YIELD)


def build_inputs() -> AnalysisInputs:
    pit = pit_inputs_for(TICKER, TODAY, list(REVENUE), user_agent=UA)
    try:
        from engine.data.providers.sec import fetch_company_facts, ticker_to_cik

        facts = fetch_company_facts(ticker_to_cik(TICKER, UA), UA)
        provenance = provenance_from_sec_facts(facts, TICKER, TODAY, list(REVENUE))
    except Exception:  # noqa: BLE001 - provenance는 부가 기록, 실패해도 분석은 계속
        provenance = None

    return AnalysisInputs(
        ticker=TICKER,
        company_name="Cardinal Health, Inc.",
        revenue_by_year=REVENUE,
        operating_income_by_year=OPERATING_INCOME,
        operating_cashflow_by_year=OPERATING_CASHFLOW,
        capex_by_year=CAPEX,
        market_cap=MARKET_CAP,
        net_debt=NET_DEBT,
        ebitda=EBITDA,
        risk_free_rate=RF,

        competitor_threat_weights=[0.35, 0.30, 0.25],
        market_share_trend_pp_per_year=0.0,
        active_antitrust_or_regulatory_case=True,
        demand_sensitivity_pct=0.08,
        subjective_input_basis=(
            "**MCK(2026-07-28)·COR(2026-08-02) 분석과 정확히 동일한 가중치를 "
            "의도적으로 재사용한다** - 미국 의약품유통 3사 과점의 세 번째 "
            "사업자이므로 같은 산업구조에 다른 가정을 쓰면 세 종목의 Gap 차이가 "
            "사업 차이인지 분석자 입력 차이인지 구분되지 않는다(COR가 MCK 가중치를 "
            "그대로 쓴 것과 같은 논리의 3번째 확장). McKesson 0.35(3파전 중 최대 "
            "경쟁자), Cencora 0.30, PBM/보험사 수직계열화 위협 0.25(CVS Health/"
            "UnitedHealth Optum의 자체 유통망 내재화 압력)[셋 다 추정치]. "
            "market_share_trend=0.0: 3사 과점구조가 수십년째 안정적이나 정량 추세 "
            "데이터가 없어 중립[추정치]. active_antitrust_or_regulatory_case=True: "
            "Cardinal Health는 MCK·Cencora와 함께 3사 $21B 오피오이드 전국합의의 "
            "당사자이며(18년 분할상환, COR 분석에서 확인한 것과 동일 건), FY2020 "
            "영업손실 -$4,098M이 그 충당금 인식분이다. demand_sensitivity=0.08: "
            "처방의약품 유통은 경기와 무관한 필수·의무 지출 - CLAUDE.md 앵커표의 "
            "'필수/의무 지출(의약품유통)' 버킷 값이자 MCK·COR가 실제로 쓴 값과 "
            "동일(앵커 이탈 없음)."
        ),

        model_used="two_stage",
        model_choice_reason=(
            "MCK·COR와 동일하게 two_stage를 채택한다 - 성숙·안정 산업의 과점 "
            "사업자이나 FY2026 매출이 +14.2%로 크게 가속한 국면이라(GLP-1 등 "
            "고가 특수의약품 유통 확대 + FY2025 대형고객 이탈의 기저효과) 이 "
            "가속이 무기한 지속된다고 가정하는 single_stage보다 정상화 경로를 "
            "명시하는 two_stage가 보수적이다. 회사 자체 FY2027 가이던스도 "
            "비GAAP EPS +13~15%로 FY2026의 +37%보다 뚜렷이 낮아 감속을 스스로 "
            "제시한다. 2026-08-16 모델선택 연구가 확인한 대로 이론기준이 실제 "
            "선택을 완벽히 가르지는 못하나, 이 경우 동일산업 peer 2종목이 같은 "
            "선택을 했다는 것이 추가 근거다(BRO형 '과거기록 답습'과는 다르다 - "
            "그쪽은 같은 종목의 복원 불가능한 과거 판단을 따른 것이고, 이쪽은 "
            "같은 산업 다른 종목의 명시적 경제논리를 따른 것이다). 첫 정식분석"
            "이라 대조할 과거 기록 없음."
        ),

        falsification_conditions=(
            "(1) FY2027 Q1 실적(11월경 예상)과 그 이후 분기에서 영업현금흐름이 "
            "연환산 $3.5B 아래로 되돌아가면, 이 분석의 FCF0($4,525M)가 FY2026 "
            "단일연도 운전자본 스윙의 산물이었다는 뜻이므로 재검토한다 - 3년 평균 "
            "FCF 기준 수익률은 약 5.6%로 이번 7.87%보다 크게 낮다(이 종목 최대 "
            "취약점). (2) 회사가 제시한 FY2027 비GAAP EPS 성장 +13~15% 대비 실제가 "
            "한자릿수 초반으로 미달하면 재검토. (3) Pharmaceutical and Specialty "
            "Solutions 부문 이익성장이 회사 가이던스(+8~11%) 하단을 밑돌면 3사 "
            "과점의 가격결정력이 약화된 신호로 보고 competition_intensity 상향 "
            "재검토. (4) CVS Health·UnitedHealth Optum 등 대형 PBM/보험사가 "
            "Cardinal이 담당하던 유통물량을 자체 내재화한다고 공시하면 즉시 재검토 "
            "- 이 분석이 0.25 가중치로만 반영한 구조적 위협이 실현되는 경우다."
        ),

        price_at_analysis=PRICE,
        currency="USD",

        net_income_by_year=NET_INCOME,
        sbc_by_year=SBC,

        data_sources=[
            "SEC XBRL companyfacts(CIK 0000721371), 2026-09-06 조회 - 매출·영업이익·"
            "영업현금흐름·capex·순이익·SBC·D&A·현금·총차입금 전부 1차자료",
            "SEC FY2026 10-K 표지 dei:EntityCommonStockSharesOutstanding "
            "232,575,728주(2026-07-31 기준, 2026-08-11 제출)",
            "Alpha Vantage GLOBAL_QUOTE 종가 $247.18(2026-09-04), "
            "TREASURY_YIELD 10Y 4.77%(2026-09-03)",
            "WebSearch: FY2026 Q4/연간 실적발표 및 FY2027 가이던스(비GAAP EPS "
            "+13~15%, Pharma 부문 이익 +8~11%, Other 부문 이익 +15~18% 중 인수 "
            "기여 2%p), 2026-09-06 조회",
        ],

        **pit,
        provenance=provenance,
    )


if __name__ == "__main__":
    result = run_analysis(build_inputs())
    d, g = result["derived"], result["growth"]
    models = result["implied_growth"]["models"]
    print("=" * 96)
    print(f"CAH 정식 분석 ({result['meta']['analyzed_at'][:10]}, 엔진 {result['meta']['engine_version']})")
    print("=" * 96)
    rev10 = "N/A" if d["revenue_cagr_10y"] is None else f"{d['revenue_cagr_10y']*100:.2f}%"
    print(f"  매출 CAGR   3y {d['revenue_cagr_3y']*100:.2f}% / "
          f"{d['cagr_5y_span']}y {d['revenue_cagr_5y']*100:.2f}% / 10y {rev10}")
    print(f"  FCF CAGR    {d['fcf_cagr_5y']*100:.2f}%   FCF0 ${d['fcf0']/1e9:.3f}B "
          f"(FCF수익률 {d['fcf0']/MARKET_CAP*100:.2f}%)")
    print(f"  순부채/EBITDA {d['net_debt_to_ebitda']:.3f}배   시총 ${MARKET_CAP/1e9:.2f}B")
    print(f"  DRS         {result['drs']['score']:.2f}  {result['drs']['components']}")
    print(f"  Lynch       {result['lynch']['used']}   구조적할인 {g['structural_discount_pct']*100:.2f}%")
    print(f"  Realistic   {g['realistic_growth']*100:.2f}%")
    ss = "N/A" if models["single_stage"] is None else f"{models['single_stage']*100:.2f}%"
    ts = "N/A" if models["two_stage"] is None else f"{models['two_stage']*100:.2f}%"
    print(f"  Implied     single {ss} / two {ts} -> "
          f"{result['implied_growth']['value']*100:.2f}% ({result['implied_growth']['model_used']})")
    print(f"  Gap         {result['expectation_gap']*100:+.2f}%p   "
          f"RAR {result['rar']:+.4f}   Confidence {result['confidence']['final']}/100")
    print(f"  ** {result['judgment']} / {result['judgment_grade']}등급 **")
    print(f"  강건성 flip {result['sensitivity_check'].get('judgment_flipped')}   "
          f"PIT {(result['meta'].get('point_in_time') or {}).get('status')}")
    if result.get("sbc_cross_check"):
        s = result["sbc_cross_check"]
        print(f"  SBC/FCF {s.get('sbc_to_fcf_pct', 0)*100:.1f}% -> "
              f"Gap {(s.get('gap_sbc_adjusted') or 0)*100:+.2f}%p")
    for x in result["data_limitations"]:
        print(f"    - {x}")
    print(f"\n저장: {save_ledger(result)}")
