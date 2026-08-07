"""
monday.com(MNDY) 정식 분석 - 2026-07-31.

경위: "계속실행" 요청에 응답. Barchart "AI Disruption Overblown! 4 Software
Stocks to Buy on the Dip"(2026-07) 기사가 CRM(기존 저평가 기록 보유,
2026-07-22 확인 완료)과 함께 언급한 종목. 소프트웨어 섹터 전반의 "AI가
SaaS를 대체한다"는 공포로 시총 약 $1조가 증발한 매도세의 일부.

이스라엘 소재 협업/워크매니지먼트 SaaS. 주가는 YoY -74.45%, YTD -49.91%,
52주 고점 대비 약 -75%(2026-07 Motley Fool/barchart 확인).

**이번엔 SE/RMD 유형에 가깝다(순수 공포과잉) - DUOL/TTD와 다르다**: WebSearch로
확인한 결과, Q1 2026 실적은 매출 $351.3M(+24% YoY)으로 컨센서스 상회, $500K+
ARR 고객 +74% YoY, **FY2026 매출 가이던스 19~20% YoY 성장을 재확인(하향
아님)**했다. 2026-07-22 발표한 630명(전체 20%) 감원은 비용절감이 아니라
"좌석 기반 과금(seat-based) 모델에서 AI 에이전트 플랫폼으로" 사업모델을
선제 전환하겠다는 구조조정이며, 발표 당일 주가는 오히려 소폭 상승했다 -
시장이 이를 "회사가 흔들린다"는 신호가 아니라 "경쟁상 필요한 선제조치"로
받아들였다는 뜻. 즉 DUOL(가이던스 자체 인하)·TTD(가이던스 인하+임원이탈)와
달리, MNDY는 **회사 실적·가이던스 자체는 견고한데 섹터 전체가 AI발
디스커플링 공포로 동반 하락**한 경우 - SE(GLP-1 공포)·RMD(동일 공포)와
같은 계열의 "공포과잉"에 더 가깝다.

다만 5년 매출 CAGR(41.4%, 2022년 68%→2025년 26.8%로 자연 감속 중)과 회사
자체 FY2026 가이던스(19~20%)의 격차는 여전히 크다 - "감속이 실제로 존재한다"는
사실 자체는 부정할 수 없으므로 realistic_growth_estimate()의 구조적 할인이
이를 얼마나 반영하는지 결과에서 확인할 것.

⚠️ **CAGR 기준연도 override 필요(v3.21 경로)**: 기본 5년 CAGR 기준연도인
FY2020(IPO 초기, 팬데믹 첫해)의 OCF가 -$37.175M로 음수라 FCF가 음수(-$42.656M)
-> CAGR 시작값 음수 가드에 걸려 실행이 거부된다. FY2021(IPO 직후 첫 흑자전환
직전 해, FCF +$2.597M로 첫 플러스)을 기준연도로 override(4년 구간).

원자료: 전부 SEC EDGAR 20-F(외국민간발행인 연차보고서, 10-K 대응) as-filed에서
직접 추출(2026-07-31 조회, curl 직접 fetch로 WebFetch 503 우회).
  FY2025 20-F(CIK 1845338, accession 0001178913-26-000870) R2/R4/R8
  FY2022 20-F(accession 0001178913-23-000966) R4/R8 (FY2020~2022)
시가총액: stockanalysis.com 2026-07-31 조회 $3.74B(전일종가 $87.15 반영).

실행: python3 scripts/analyze_mndy_2026_07_31.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.pipeline import AnalysisInputs, run_analysis, save_ledger

K = 1_000  # 원자료가 '천 달러' 단위

# ── SEC EDGAR as-filed 실측 (단위: USD, 원 단위) ────────────────────────
REVENUE = {
    2020: 161123 * K, 2021: 308150 * K, 2022: 519029 * K,
    2023: 729695 * K, 2024: 971995 * K, 2025: 1231997 * K,
}
OPERATING_INCOME = {
    2020: -150537 * K, 2021: -126125 * K, 2022: -152015 * K,
    2023: -38585 * K, 2024: -21034 * K, 2025: -1748 * K,
}
OPERATING_CASHFLOW = {
    2020: -37175 * K, 2021: 16355 * K, 2022: 27138 * K,
    2023: 215404 * K, 2024: 311065 * K, 2025: 333644 * K,
}
# capex = 유형자산 취득 + 자본화 소프트웨어개발비(둘 다 R8 investing activities)
CAPEX = {
    2020: (4362 + 1119) * K, 2021: (11578 + 2180) * K, 2022: (16003 + 2998) * K,
    2023: (7901 + 2558) * K, 2024: (13211 + 2024) * K, 2025: (20362 + 3380) * K,
}

# 재무상태표 (FY2025 20-F R2, 2025-12-31 기준) - 무차입 경영(재무부채 없음, 확인됨)
CASH = 1503149 * K
SHORT_TERM_INVESTMENTS = 162308 * K
TOTAL_DEBT = 0
NET_DEBT = TOTAL_DEBT - CASH - SHORT_TERM_INVESTMENTS

DA_2025 = 13805 * K
EBITDA = OPERATING_INCOME[2025] + DA_2025

MARKET_CAP = 3.74e9
RF = 0.0447


def build_inputs() -> AnalysisInputs:
    return AnalysisInputs(
        ticker="MNDY",
        company_name="monday.com Ltd.",
        revenue_by_year=REVENUE,
        operating_income_by_year=OPERATING_INCOME,
        operating_cashflow_by_year=OPERATING_CASHFLOW,
        capex_by_year=CAPEX,
        market_cap=MARKET_CAP,
        net_debt=NET_DEBT,
        ebitda=EBITDA,
        risk_free_rate=RF,

        # v3.24(2026-08-02 방법론 감사 권고 #3): 향후 실현수익률 검증 전제조건.
        price_at_analysis=87.15,
        currency="USD",

        # v3.23(2026-08-01 방법론 감사 Critical-1): SBC 병기 교차검증.
        # SEC 20-F R8 현금흐름표 "Share-based compensation" FY2025 실측.
        sbc_by_year={2025: 177011 * K},

        cagr_base_year_override=2021,
        cagr_base_year_override_reason=(
            "기본 기준연도 FY2020(IPO 초기·팬데믹 첫해)의 OCF가 -$37.175M로 "
            "적자라 FCF가 음수(-$42.656M) -> CAGR 시작값 음수 가드(v3.19)에 "
            "걸려 실행 자체가 거부된다. FY2021(상장 직후, FCF 첫 플러스전환 "
            "+$2.597M)을 기준연도로 삼아 4년 구간 CAGR을 산출한다."
        ),

        competitor_threat_weights=[0.25, 0.20, 0.15],
        market_share_trend_pp_per_year=-1.0,
        active_antitrust_or_regulatory_case=False,
        demand_sensitivity_pct=0.25,
        subjective_input_basis=(
            "ClickUp/Asana/Smartsheet 등 협업툴 시장은 다수 경쟁사가 난립한 "
            "파편화 시장 - 단일 지배적 경쟁자가 없어 TTD(Amazon DSP 0.40)만큼 "
            "집중된 위협은 아니라고 판단해 최대 가중치를 0.25로 설정[추정치]. "
            "AI 네이티브 신생 워크관리 툴(범주 자체를 재정의할 잠재 위협) "
            "0.20, 기존 대형 경쟁사(Asana/Smartsheet, 이미 AI 기능을 무료 "
            "번들로 제공 중이라 가격경쟁 유발 가능) 0.15. 전부 [추정치]. "
            "market_share_trend=-1.0pp: 회사가 자발적으로 좌석기반 과금을"
            "폐기하고 AI 에이전트 모델로 전환 중이라는 사실 자체가 기존 "
            "모델의 점유율 압박을 인정하는 신호로 보되, Q1 순증가고객·ARR "
            "지표는 견고해(DUOL -1.0pp와 동일 수준) 과도한 음수는 부여하지 "
            "않음[추정치]. demand_sensitivity=0.25: 협업 SaaS는 기업 IT예산 "
            "삭감시 영향받으나 필수업무툴 성격이 강해 광고(TTD 0.35)나 "
            "소비자재량재(SE) 대비 낮은 편[추정치]."
        ),

        model_used="two_stage",
        model_choice_reason=(
            "⚠️핵심 판단: MNDY는 5년 매출 CAGR이 41.4%(2022년 +68%→2025년 "
            "+26.8%로 자연 감속 중)에 달하는 고성장기였고, DUOL/TTD와 달리 "
            "Q1 2026 실적은 컨센서스 상회·FY2026 가이던스(19~20%)도 하향이 "
            "아니라 재확인이었다. 2026-07-22 발표한 20% 감원은 실적 부진이 "
            "아니라 좌석과금->AI에이전트 사업모델 선제전환이며 발표 당일 "
            "주가가 오히려 소폭 상승했다 - 시장이 부정적 신호로 보지 않았다는 "
            "뜻. 그럼에도 명시적 고성장구간(3배 이상 매출성장) 이후 감속 "
            "국면이라는 구조 자체는 DUOL/TTD와 동일해 two_stage가 이론적으로 "
            "더 부합한다고 판단 - 실행 후 모델괴리를 보고 재검토할 것"
            "(GWRE/KLAC/VRT/KEYS/SE/RMD/DUOL/TTD와 동일 절차). 첫 분석이라 "
            "대조할 과거 기록 없음."
        ),

        # v3.24+(2026-08-02, S등급 4종목 중 3종목 심층조사): 원분석에는 없던
        # 사실 확인 - 2026-02-09 실적발표에서 FY2027 매출목표($1.8B)가 철회되고
        # 주가가 하루 -21% 급락한 사건이 있었다(본문 FY2026 가이던스 19~20%는
        # 이미 그 하향 이후 값). 이를 근거로 성장서사가 오도됐다는 증권소송이
        # 진행 중(S.D.N.Y., 소송기간 2025-09-17~2026-02-06). 자사주매입($870M
        # 승인 중 ~$688M 집행)으로 최근 3분기 희석주식수가 -8%로 반전됐으나
        # 그 재원이 현금성자산 축소(그리고 GAAP 순이익의 상당부분을 차지하는
        # 이자수익)에서 나와 지속가능성은 불확실. 회사 자체 FY2026 조정FCF
        # 가이던스도 전년대비 감소($322.7M/26%마진 -> $275~290M/19~20%마진)로
        # 제시돼 있어 엔진이 노이즈로 간주해 채택하지 않은 FCF CAGR 230%가
        # 실제로도 지속불가능한 수치였음이 회사 스스로에 의해 확인됐다.
        falsification_conditions=(
            "(1) 2026-08-10 Q2 실적에서 $50K+/$100K+ ARR 코호트 NDR이 110% "
            "미만으로 하락하거나 SMB/셀프서브 채널 매출비중이 추가로 축소되는 "
            "신호가 나오면(현재 상단 코호트 강세로 하단 약세가 상쇄되는 구도가 "
            "무너짐) 이 판정은 틀린 것으로 간주. (2) 진행 중인 증권소송이 "
            "화해·기각이 아니라 실제 손해배상 판결이나 대규모 화해금으로 "
            "귀결되면 거버넌스 리스크를 재평가할 것."
        ),

        data_sources=[
            "SEC EDGAR 20-F FY2025(0001178913-26-000870) R2/R4/R8, as-filed, 2026-07-31 조회",
            "SEC EDGAR 20-F FY2022(0001178913-23-000966) R4/R8 (FY2020~2022)",
            "stockanalysis.com 시가총액 $3.74B(주가 $87.15), 2026-07-31 조회",
            "WebSearch: Barchart 'AI Disruption Overblown! 4 Software Stocks to Buy "
            "on the Dip' 기사, MNDY Q1 2026 실적(매출 $351.3M +24%YoY, 가이던스 "
            "19~20% 재확인), 2026-07-22 630명 감원(AI 에이전트 전환) 보도 확인",
        ],
    )


def main():
    result = run_analysis(build_inputs())
    d, g = result["derived"], result["growth"]
    models = result["implied_growth"]["models"]

    print("=" * 100)
    print(f"MNDY(monday.com) 정식 분석 결과 ({result['meta']['analyzed_at'][:10]}, 엔진 {result['meta']['engine_version']})")
    print("=" * 100)
    print(f"  CAGR 기준연도    : {d['cagr_5y_base_year']}년 ({d['cagr_5y_span']}년 구간, override 사용)")
    rev_10y_str = "N/A" if d['revenue_cagr_10y'] is None else f"{d['revenue_cagr_10y']*100:.2f}%"
    print(f"  매출 CAGR        : 3y {d['revenue_cagr_3y']*100:.2f}% / "
          f"{d['cagr_5y_span']}y {d['revenue_cagr_5y']*100:.2f}% / 10y {rev_10y_str}")
    print(f"  FCF CAGR         : {d['fcf_cagr_5y']*100:.2f}%   (FCF0 {d['fcf0']/1e6:.3f}M)")
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
