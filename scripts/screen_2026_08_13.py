"""
2026-08-13 매수관점 후보 스크리닝 (screener.py 4분류 체크리스트 적용).

기준·방법론은 engine/screener.py docstring 참고. 이 스크립트를 남기는 이유는
scripts/screen_2026_07_26.py와 동일 - 스크리닝 결과만 남기고 입력값이 사라지면
큐22(Cadence) 사고가 반복된다.

원자료 출처: Alpha Vantage MCP(INCOME_STATEMENT/CASH_FLOW/BALANCE_SHEET,
2026-08-13 조회, 원자료는 SEC 공시 기반) + WebSearch(하락 배경 확인,
2026-08-13). 시가총액은 FMP MCP(quote/market-cap)가 세션 도중 플랜 제한으로
간헐적으로 막혀 일부는 WebSearch로 보완했다(BSX). FMP의 무료 플랜 quote
엔드포인트가 특정 티커(MCO)에서만 막히는 비일관적 동작을 확인 - 재현 안 되는
간헐적 문제라 원인 특정은 보류.

**이번 배치 절차**: WebSearch로 최근 급락/52주 저점 종목을 먼저 수집한 뒤(Trefis
"S&P 500 52-Week Lows" 연재, 2026-07-24~08-10 다수), 4분류 체크리스트로
재무데이터를 긁기 전에 먼저 걸러냈다(screener.py docstring 참고). 총 9개 후보를
조사해 3개만 정량 스크리닝까지 진행했고(META/MCO/BSX), 나머지는 서사 확인
단계 또는 프레임워크 부적합으로 재무데이터를 긁지 않고 제외했다(사유는
PREFILTERED_OUT/FRAMEWORK_MISMATCH 참고).

**결과 요약**: **3종목 전수 탈락(0/3)** - 07-31/08-06 배치에 이어 세 번째로
완전탈락한 배치다. 셋 다 사유가 다르다는 점이 오히려 이번 배치의 소득이다:
- **BSX**: 가장 근접(내재성장률 추정 5.77% vs 임계값 5.5%, 필요 FCF수익률
  5.20%에 4.93%로 근소 미달) - 성장(현실적성장률 추정 13.63%)은 압도적으로
  통과, 서사도 과장(공포과잉)으로 판단했지만 **밸류에이션 자체가 아직 그
  정도로 싸지지는 않았다**. 후보 재확인 가치가 가장 높은 종목.
- **META**: 현실적성장률 추정 12.86%로 성장은 넉넉히 통과(v3.20 capex
  재검토 플래그도 발동 안 함 - AI capex 급증이 성장 판정에는 문제가 안 됨).
  탈락 원인은 순수 밸류에이션(FCF수익률 3.13% vs 필요 4.97%) - "실적은
  훌륭한데 이미 비쌈"(4분류 2번)에 더 가깝고, capex 서사는 부차적이었다.
- **MCO**: 성장(현실적성장률 추정 4.26%)과 밸류에이션(내재성장률 추정
  7.63%) 둘 다 미달 - "공포과잉"처럼 보였던 서사가 실제로는 실측 FCF 성장
  둔화(2022년 금리급등발 채권발행 급감)로 뒷받침되는 "혼재" 사례였다.

**2차 라운드(동일 08-13 세션, 사용자 "계속 스크리닝" 요청)**: 07-31 배치가
"특별처리 필요, 보류"로 남겨뒀던 APP(AppLovin)를 재검토했고, 신규로 ALGN
(Align Technology)을 조사했다.

- **APP(AppLovin) - 여전히 보류, 이번엔 원인을 구체적으로 확인했다.** 2024년
  모바일게임 Apps 사업부 매각(Tripledot에 매각, 2024년 중 종결)으로 분기별
  매출에 뚜렷한 구조단절이 있다(FY2024 분기 매출이 $1,058M→$711M로 급락 후
  재상승) - PTC의 Kepware/ThingWorx 매각과 동일 유형. **Alpha Vantage
  totalRevenue 시계열 자체가 재작성(discontinued operations 재분류) 영향을
  받은 것으로 보여**(2022년 $2.82B→2023년 $1.84B로 오히려 감소 - 사업축소가
  아니라 회계 재작성 때문으로 추정) 5y CAGR을 그대로 계산하면 의미가 왜곡된
  숫자가 나온다(2020→2025 FCF CAGR 78.18%는 진짜 유기적성장이 아니라 상당부분
  믹스효과). 대신 **완전히 클린한 TTM 비교**(2025Q3~2026Q2 합산 vs
  2024Q3~2025Q2 합산, 둘 다 매각 이후 구간이라 구조단절이 없음)로 매출성장
  47.6%를 확인했고, 이는 회사가 밝힌 Q2 실적 발표의 "53% YoY"와 근접해
  신뢰성을 교차검증했다. 펀더멘털 자체는 매우 강함(FY2025 EBITDA마진
  79.4%=$4,354.7M/$5,480.7M, FY2025 FCF $3,942.8M) - 다만 회사 자체 최초
  가이던스 미스(Q2 2026, Wells Fargo/Piper Sandler 하향) + 이전 공매도
  의혹(CapitalWatch, 자금세탁방지 통제 관련 - 회사는 부인)까지 겹쳐 하락폭이
  컸다. **5y CAGR 프레임에 억지로 밀어넣지 않고 이번에도 정량모델에서
  제외한다** - Bullfincher 등 2차 출처의 세그먼트별 매출과 Alpha Vantage
  연결매출이 서로 정합적이지 않아(2023년 수치가 우연히 일치하는 등 오히려
  혼란) SEC 10-K 원문을 직접 대조하지 않고는 믿을 만한 세그먼트 조정 CAGR을
  만들 수 없다고 판단했다 - 정직하게 미해결로 남긴다.
- **ALGN(Align Technology) - 4분류 3번(진짜나빠짐)으로 신규 제외.** Q1 2026
  매출이 전년동기 대비 약 2%(≈$980M→$1.0B) 성장에 그쳤다는 WebSearch 결과를
  Alpha Vantage 연간 매출로 대조: 2021년 $3.95B → 2022년 $3.73B(역성장) →
  2023년 $3.86B → 2024년 $4.00B → 2025년 $4.03B - **4년째 사실상 정체**
  (2021년이 코로나 이후 치과 시술 이연수요 폭발로 인한 일시적 고점이었을
  가능성이 높다). 표면적 5y CAGR(2020→2025, 10.29%)은 2020년이 코로나로
  억눌린 저점이라 BKNG와 동일한 방식으로 부풀려진 숫자다 - 최근 4년 추세와
  회사 자체 최신 분기 실적이 이미 성장정체를 직접 보여주고 있어, 서사(경쟁
  심화·시장포화)와 실측이 일치하는 '진짜나빠짐' 사례로 판단해 재무데이터를
  더 긁지 않고 제외했다.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.screener import Candidate, screen_all, format_table


def cagr(s, e, y):
    return (e / s) ** (1 / y) - 1


def worst_yoy(series):
    ys = sorted(series)
    return min(series[ys[i]] / series[ys[i - 1]] - 1 for i in range(1, len(ys)))


CANDIDATES = []

# ── META (Meta Platforms) - AI capex 급증으로 FCF가 눌린 대형주, capex 재검토 대상 ──
# 원자료: Alpha Vantage INCOME_STATEMENT/CASH_FLOW/BALANCE_SHEET(2026-08-13),
# 시가총액 FMP company/market-cap(2026-08-12 종가 기준, $1,474,612,601,045).
# 하락배경: 2026 AI 인프라 capex 가이던스를 $125~145B로 상향, Q2 FCF가 전분기比
# 91% 급감($784M)하며 -10% 시간외 급락(WebSearch, 2026-08-13 조회). 다만 FY2025
# **연간** FCF는 여전히 견조($461.09억, capex 급증에도 OCF가 더 빠르게 늘어서다) -
# 시장이 반응한 건 최근 1~2개 분기 흐름이지 FY2025 연간 실적이 아니다.
_rev_meta = {2020: 85965, 2021: 117929, 2022: 116609, 2023: 134902, 2024: 164501, 2025: 200966}
_fcf_meta = {2020: 38747 - 15115, 2021: 57683 - 18567, 2022: 50475 - 31431,
             2023: 71113 - 27266, 2024: 91328 - 37256, 2025: 115800 - 69691}
_capex_meta = {2020: 15115, 2021: 18567, 2022: 31431, 2023: 27266, 2024: 37256, 2025: 69691}
CANDIDATES.append(Candidate(
    ticker="META", name="Meta Platforms", exchange="NASDAQ",
    market_cap=1474613, fcf0=_fcf_meta[2025],
    revenue_cagr_5y=cagr(_rev_meta[2020], _rev_meta[2025], 5),
    fcf_cagr_5y=cagr(_fcf_meta[2020], _fcf_meta[2025], 5),
    net_debt_to_ebitda=0.02,  # 총부채 $839.0억 - 현금·단기투자 $815.9억(FY2025), EBITDA 대비 사실상 무차입
    worst_yoy_revenue=worst_yoy(_rev_meta),
    capex_to_revenue_current=_capex_meta[2025] / _rev_meta[2025],
    capex_to_revenue_avg=sum(_capex_meta[y] / _rev_meta[y] for y in range(2020, 2025)) / 5,
    note=(
        "FY2025 실측: 매출 5y CAGR 18.51%, FCF CAGR 14.30%(매출보다 낮음 - "
        "AI인프라 capex가 FY2020~2024 평균 20.63%/매출 -> FY2025 34.68%/매출로 "
        "+14.05%p 급증). **그런데도 현실적성장률 추정 12.86%(14.30%*(1-10.1%))로 "
        "임계값(8%)은 이미 넉넉히 통과한다** - v3.20 capex 재검토 로직이 발동하는 "
        "조건(rg가 8% 미만인데 매출기준 rg는 8% 이상)에 해당하지 않아 실제로도 "
        "screen()에서 review_flag가 뜨지 않았다(성장 자체는 문제가 아니라는 뜻).  "
        "탈락 원인은 순수 밸류에이션이다 - FCF수익률 3.13%($461.09억/$1.4746조)가 "
        "필요치(4.97%)에 못 미친다. $1.47조라는 시가총액 자체가 이미 매우 큰 "
        "숫자(초대형주 프리미엄)라 이번 batch의 capex 급증 서사와는 별개로, "
        "'실적은 훌륭한데 이미 비쌈'(screener.py 4분류 2번)에 더 가까운 결과 - "
        "AI capex 급증이 FCF0를 낮춰 탈락에 일부 기여했으나(급증 전 capex/매출 "
        "수준이었다면 FCF0가 더 컸을 것) 주된 원인은 아니었다."
    ),
))

# ── MCO (Moody's) - 레이팅업계 매크로 우려, 그러나 실측 FCF 성장이 이미 둔화 ──
# 원자료: Alpha Vantage(2026-08-13), 시가총액 WebSearch($82.53B, 2026-08-13).
# 하락배경: 부채발행 동결 우려(지정학·금리변동성), 임원 지분매도, 2026 영업마진
# 가이던스 소폭 하향(자사주매입 가이던스는 오히려 상향) - "공포과잉"처럼
# 보였으나 재무데이터를 긁어보니 실제로 FCF 성장이 눌려있었다(2022년 -12.06%
# YoY 매출역성장이 5y창에 걸림 - 2022년 급격한 금리인상으로 채권발행이
# 급감한 실제 사건, 서사가 아니라 실측).
_rev_mco = {2020: 5371, 2021: 6218, 2022: 5468, 2023: 5916, 2024: 7088, 2025: 7718}
_fcf_mco = {2020: 2146 - 103, 2021: 2005 - 139, 2022: 1474 - 283,
            2023: 2151 - 271, 2024: 2838 - 317, 2025: 2901 - 326}
CANDIDATES.append(Candidate(
    ticker="MCO", name="Moody's Corporation", exchange="NYSE",
    market_cap=82530, fcf0=_fcf_mco[2025],
    revenue_cagr_5y=cagr(_rev_mco[2020], _rev_mco[2025], 5),
    fcf_cagr_5y=cagr(_fcf_mco[2020], _fcf_mco[2025], 5),
    net_debt_to_ebitda=1.2,  # 총부채 $73.51억 - 현금 $23.84억(FY2025), EBITDA 추정 ~$41억
    worst_yoy_revenue=worst_yoy(_rev_mco),
    note=(
        "FY2025 실측: 매출 5y CAGR 7.52%, **FCF CAGR 4.74%로 제약** - 현실적성장률 "
        "추정 4.26%(4.74%*(1-10.1%))로 임계값(8%)에 크게 미달한다. 2022년 "
        "금리급등으로 채권발행(Moody's 핵심 수익원)이 급감한 여파가 5y창에 걸려 "
        "worst_yoy -12.06%로 실측됨 - '레이팅업계 매크로 우려'라는 서사가 실제로 "
        "성장 둔화로 나타난 사례다. 다른 이번 배치 후보(BSX)와 달리 이건 "
        "'공포과잉'이 아니라 '혼재'에 가깝다 - screen() 실행 결과 밸류에이션도 "
        "함께 미달(내재성장률 추정 7.63% > 5.5%, 필요 FCF수익률 5.20%에 실제 "
        "3.12%)로 확인돼 이중탈락이다."
    ),
))

# ── BSX (Boston Scientific) - 가이던스 하향+리콜+소송 겹침, 실측은 견조 ──
# 원자료: Alpha Vantage(2026-08-13), 시가총액 WebSearch($74.19B, 2026-08-13).
# 하락배경: 2026년 고점($109.50, 2025-09) 대비 ~53% 하락. 2026 매출가이던스
# 소폭 하향($22.2B->$21.7B, -2.3%)에 CRE/CRE Pro 위장관기기 Class II 리콜,
# WATCHMAN(좌심방이색전증 폐쇄술) 성장둔화 우려, 전기생리학 성장 관련 증권
# 집단소송까지 겹쳐 하락폭이 가이던스 컷 자체보다 훨씬 크다 - 노이즈가 겹겹이
# 쌓인 전형적 공포과잉 패턴(RMD의 GLP-1 공포 사례와 유사 구조).
_rev_bsx = {2019: 10735, 2020: 9913, 2021: 11888, 2022: 12682, 2023: 14240, 2024: 16747, 2025: 20074}
_fcf_bsx = {2020: 1508 - 376, 2021: 1870 - 554, 2022: 1526 - 612,
            2023: 2503 - 800, 2024: 3435 - 790, 2025: 4534 - 876}
CANDIDATES.append(Candidate(
    ticker="BSX", name="Boston Scientific", exchange="NYSE",
    market_cap=74190, fcf0=_fcf_bsx[2025],
    revenue_cagr_5y=cagr(_rev_bsx[2020], _rev_bsx[2025], 5),
    fcf_cagr_5y=cagr(_fcf_bsx[2020], _fcf_bsx[2025], 5),
    net_debt_to_ebitda=1.9,  # 총부채 $124.18억 - 현금 $20.45억(FY2025), EBITDA 추정 ~$55억(순이익+D&A 기준 근사)
    worst_yoy_revenue=worst_yoy(_rev_bsx),  # 2019 포함 - 2020 코로나 트로프(-7.66%) 반영
    note=(
        "FY2025 실측: 매출 5y CAGR 15.16%, FCF CAGR 26.44%(매출보다 빠름 - "
        "마진 확장 중, capex 재검토 대상 아님). FCF수익률 4.93%($36.58억/"
        "$741.9억). 2020년(코로나로 선택적 시술 연기, YoY -7.66%)이 5y창 "
        "기준연도에 걸려있으나 BKNG급 폭락(-54%대)이 아니라 완만한 조정이라 "
        "기준연도를 옮기지 않았다(2019년 매출 $107.35억도 함께 확인해 저점이 "
        "2020년임을 검증). 최근 하락은 가이던스 소폭 컷(-2.3%)에 리콜·소송· "
        "WATCHMAN 성장둔화 우려가 동시에 겹쳐 서사가 과장된 전형적 사례로 판단."
    ),
))

# ── 아래는 WebSearch 확인 단계에서 재무데이터 없이 제외 ──
PREFILTERED_OUT = {
    "ORCL(Oracle)": (
        "FY2026 인프라 capex $557억(전년대비 2.6배)로 FCF가 -$237억까지 적자전환 "
        "(WebSearch, 2026-08-13). fcf0<=0이라 screener.py 가드상 애초에 모델 적용 "
        "불가(Model N/A) - 데이터를 긁어도 screen()이 즉시 탈락 처리한다."
    ),
    "ROL(Rollins)": (
        "Q2 2026 실적 컨센서스 미스(EPS -5.9%, 매출 -1.7%), 주거용 방제 수요 "
        "둔화·마진 압박·CFO 사임·M&A 배수 상승이 동시에 확인됨(WebSearch,  "
        "2026-08-13). BofA가 Buy->Underperform으로 목표가 $55->$35 강등 - "
        "다중 부정신호가 서사가 아니라 회사 실적 자체에서 나와 4분류 3번(진짜 "
        "나빠짐)으로 판단, 재무데이터 확보 전 제외."
    ),
    "SNPS(Synopsys)": (
        "Ansys 인수($350억, 2026년 중 종결)가 5y CAGR 구간(2020~2025) 종료연도에 "
        "걸려 있고, Ansys 제외 유기적성장은 China 수출규제(IP사업 매출 ~10%)로 "
        "둔화 중임을 확인(WebSearch, 2026-08-13). GEN/BRO/ROP 선례와 동일한 "
        "'M&A가 CAGR 구간에 걸친 종목' - screener.py docstring이 명시한 대로 "
        "세그먼트 조정 없이는 스크리닝 자체가 왜곡되므로 후순위로 미룬다."
    ),
    "NRG(NRG Energy)": (
        "LS Power 발전자산 인수($64억 현금+주식, 2026-01-30 종결)가 5y CAGR "
        "구간에 걸려 있고, 인수 관련 이자비용·감가상각 증가로 EPS가 컨센서스를 "
        "18.1% 하회(WebSearch, 2026-08-13). SNPS와 동일한 M&A-CAGR 왜곡 사례에 "
        "더해 발전설비업은 이 프로젝트의 표준 FCF-DCF 틀과 자본구조가 크게 "
        "다른 자본집약 규제산업이라(보험업 P/B 병기 사례처럼 별도 검증체계가 "
        "필요할 수 있음) 이번 배치에서는 제외."
    ),
    "POOL(Pool Corporation)": (
        "5y 매출 CAGR이 2.2%로 이미 낮고, 순매출도 최근 9개월 YoY 소폭 역성장 "
        "(WebSearch, 2026-08-13) - 소비자 재량지출 위축+신규 수영장 건설 감소가 "
        "서사가 아니라 회사 실적 트렌드로 확인됨. MIN_REALISTIC_GROWTH(8%) 미달이 "
        "거의 확실해 재무데이터 확보 전 4분류 3번으로 판단, 제외."
    ),
    "APTV(Aptiv)/LII(Lennox)/CHTR(Charter)": (
        "scripts/screen_2026_08_06.py에서 이미 4분류 3번(진짜나빠짐)으로 제외된 "
        "종목들이 이번 배치의 52주 저점 리스트에도 반복 등장 - 새로운 반증이 "
        "없어 기존 판단 유지."
    ),
    "ALGN(Align Technology)": (
        "2차 라운드(08-13 동일세션) 신규 조사. Alpha Vantage 연간매출 실측: "
        "2021년 $3.95B -> 2022년 $3.73B(역성장) -> 2023년 $3.86B -> 2024년 "
        "$4.00B -> 2025년 $4.03B - 4년째 사실상 정체. 회사 자체 Q1 2026 "
        "실적도 YoY ~2%(WebSearch, 2026-08-13) - 경쟁심화(저가 투명교정 "
        "대체재)·시장포화 서사가 최근 4년 추세와 최신 분기 실적 둘 다로 "
        "뒷받침되는 4분류 3번(진짜나빠짐). 표면 5y CAGR(2020->2025)은 10.29%로 "
        "통과권처럼 보이지만 2020년이 코로나로 눌린 저점이라(BKNG와 동일 "
        "패턴) 부풀려진 숫자 - 재무데이터를 더 긁지 않고 제외."
    ),
}

# ── 프레임워크 자체가 5y CAGR과 안 맞는 경우 - 재무데이터는 확보했으나 정량모델 제외 ──
FRAMEWORK_MISMATCH = {
    "PODD(Insulet)": (
        "Alpha Vantage CASH_FLOW 실측(2026-08-13): FCF가 2019~2022년 4개년 "
        "연속 적자(-$190.8M~-$38.3M)였다가 **2023년에야 처음 흑자전환**"
        "($70.1M -> 2024 $305.4M -> 2025 $377.7M). screener.py의 5y CAGR "
        "프레임 자체가 시작값이 음수면 성립하지 않는다(v3.19 가드와 동일 "
        "원리) - 2023년을 기준연도로 쓰면 2년치(70.1->377.7, CAGR 132%)뿐이라 "
        "5y 프레임 다른 후보와 비교 불가능한 숫자가 나온다. **정성적으로는 "
        "매우 긍정적**(매출 5y CAGR 24.52%, GLP-1發 수요파괴 우려가 RMD와 "
        "동일하게 실측과 반대로 확인 안 됨, FCF가 4년 연속 적자에서 뚜렷한 "
        "흑자전환 궤도로 진입) - 다만 5y CAGR 정량모델에 억지로 밀어넣지 "
        "않고 정직하게 제외한다(cagr_base_year_override가 요구하는 '고점 "
        "기준연도'가 이 경우엔 존재하지 않음 - 폭락 후 회복이 아니라 아예 "
        "적자에서 흑자로 최초 전환하는 사례라 성격이 다르다). 다음 회계연도 "
        "(FY2026) FCF까지 확인되면 3y CAGR로 재시도 가능."
    ),
    "APP(AppLovin)": (
        "2차 라운드(08-13 동일세션) 재검토 - 07-31 배치가 '특별처리 필요, "
        "보류'로 남겼던 것을 이번에 원인까지 구체적으로 확인했다. 2024년 "
        "모바일게임 Apps 사업부 매각(Tripledot, 2024년 중 종결)으로 분기매출에 "
        "구조단절이 있다(2024 Q1 $1,058M -> Q2 $711M 급락 후 재상승) - PTC "
        "Kepware/ThingWorx 매각과 동일 유형. Alpha Vantage 연결매출 시계열도 "
        "재작성 영향으로 보이는 이상치가 있어(2022년 $2.82B -> 2023년 $1.84B "
        "역성장, discontinued operations 재분류 추정) 5y CAGR을 그대로 쓰면 "
        "왜곡된다(2020->2025 FCF CAGR 78.18%는 유기적성장이 아니라 상당부분 "
        "믹스효과). 대신 **매각 이후로만 완전히 클린한 TTM 비교**(2025Q3~"
        "2026Q2 합산 vs 2024Q3~2025Q2 합산)로 매출성장 47.6%를 확인 - 회사가 "
        "발표한 Q2 실적 '53% YoY'와 근접해 신뢰성 교차검증됨. 펀더멘털은 매우 "
        "강함(FY2025 EBITDA마진 79.4%, FCF $3,942.8M) - 하락은 회사 최초 "
        "가이던스 미스(Q2 2026)+공매도 의혹(CapitalWatch, 회사는 부인)이 "
        "겹친 결과. 2차 출처(Bullfincher 세그먼트 매출)와 Alpha Vantage "
        "연결매출이 서로 정합적이지 않아 SEC 10-K 원문 대조 없이는 믿을 만한 "
        "세그먼트조정 5y CAGR을 만들 수 없다고 판단 - 정량모델에서 계속 "
        "제외, 정직하게 미해결로 남긴다."
    ),
}


def main():
    results = screen_all(CANDIDATES)

    print("=" * 108)
    print("2026-08-13 스크리닝 결과")
    print("=" * 108)
    print(format_table(results))
    print()

    n_passed = sum(1 for r in results if r.passed)
    print(f"통과: {n_passed}/{len(results)}")
    print()

    for r in results:
        c = r.candidate
        status = "PASS" if r.passed else "FAIL"
        print(f"[{c.ticker}] {status}")
        if not r.passed:
            for f in r.failures:
                print(f"    - {f}")
        for f in r.review_flags:
            print(f"    ⚠️ {f}")
        print(f"    note: {c.note}")
        print()

    print("=" * 108)
    print(f"1차 분류에서 제외된 후보 ({len(PREFILTERED_OUT)}건):")
    for k, v in PREFILTERED_OUT.items():
        print(f"  - {k}: {v}")
    print()
    print(f"프레임워크 부적합으로 정량모델 제외 ({len(FRAMEWORK_MISMATCH)}건):")
    for k, v in FRAMEWORK_MISMATCH.items():
        print(f"  - {k}: {v}")


if __name__ == "__main__":
    main()
