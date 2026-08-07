"""
2026-08-06 매수관점 후보 스크리닝 (screener.py 4분류 체크리스트 적용).

기준·방법론은 engine/screener.py docstring 참고. 이 스크립트를 남기는 이유는
scripts/screen_2026_07_26.py와 동일 - 스크리닝 결과만 남기고 입력값이 사라지면
큐22(Cadence) 사고가 반복된다.

원자료 출처: Alpha Vantage(COMPANY_OVERVIEW/INCOME_STATEMENT/CASH_FLOW,
2026-08-06 조회) + WebSearch(하락 배경 확인, 2026-08-05/06). MLM의
net_debt_to_ebitda는 대차대조표 API 접근 불가로 EV(=EVToRevenue x Revenue)와
MarketCap의 차이를 순부채 근사치로 역산했다(TTM EBITDA로 나눔) - 근사치임을
명시.

이번 배치는 08-05 시점 최근 급락/52주 저점 뉴스를 WebSearch로 먼저 확인한 뒤
재무데이터를 긁는 순서로 진행했다(07-31 배치와 동일 절차). 결과: **10종목 전수
탈락** - 07-31 배치(0/26 통과)에 이어 두 번째로 완전탈락한 배치다. 이유는
종목마다 다르지만 공통적으로 "가이던스 하향/마진 압박이 실제 펀더멘털
경고"(공포과잉이 아니라 진짜 나빠짐)인 경우가 많았다 - 최근 몇 주간의
급락 뉴스가 실적시즌(Q2 2026 어닝콜) 직후에 몰려 있어, 서사가 아니라
회사 스스로 낸 가이던스 하향이 하락 원인인 종목이 대부분이었다.

**2차 라운드(동일 08-06 세션, 사용자 "계속 스크리닝" 요청) - LKQ/EME 추가
검토**: LKQ는 독일 ERP 시스템 장애(일회성 운영이슈로 프레이밍됨)로 -14%
급락했으나, 재무데이터를 보니 그 이슈와 무관하게 5년 매출 CAGR 3.66%·FCF
CAGR마저 마이너스(2020년 대비 오히려 감소)인 원래부터 저성장 롤업 기업이었다
- "일회성 이슈"라는 서사에 낚일 뻔한 사례(4분류 프레임워크가 정확히 이런
케이스를 걸러내라고 만들어짐). EME는 반대로 펀더멘털 자체는 최상급
(데이터센터 인프라 수혜, 매출 5y CAGR 14.07%·최근 분기 +19.8%YoY, FCF
CAGR 9.42%)이었으나 FCF수익률 3.29%로 밸류에이션이 이미 높아 통과 문턱
(4.86%)에 못 미쳤다 - SPGI와 같은 "이미 좋은 회사라 저평가까지는 안 됨"
유형. 반도체 섹터 전체 조정(Intel -20%+ 등)은 AI 자본지출 지속가능성에 대한
섹터 전체 재평가라 개별종목 미스프라이싱과 무관하다고 판단해 후보 리스트에
넣지 않았고, 보험/금융 섹터도 이번 검색에서 뚜렷한 미스프라이싱 신호가
나오지 않아 후보를 추가하지 않았다.

**3차 라운드(동일 08-06 세션) - "SaaSpocalypse" 테마에서 ADBE 발굴, 첫
통과 종목**: 2026년초부터 "AI 에이전트가 SaaS를 대체한다"는 서사로
소프트웨어 섹터 전체가 $2T 증발한 사건(Microsoft -16%/Shopify -26%/
Adobe -27~46%/Salesforce -30%)을 확인 - 개별기업 문제가 아니라 섹터
전체 재평가라는 점에서 반도체(MU 등)와 같은 계열이지만, **여기서는
펀더멘털이 실제로 안 꺾인 개별종목이 섞여 있는지 재무데이터로 직접
확인**했다(반도체는 위에서 이미 섹터 전체 배제로 판단, 이번엔 배제하지
않고 검증):

- **ADBE(Adobe) - 이 프로젝트 두 배치(07-31/08-06) 통틀어 첫 통과
  종목(A등급, Gap 추정 +11.15%p).** "생성형AI가 Photoshop 구독수요를
  잠식한다"는 서사로 52주 고점 대비 -46%(PER 14.4x까지 하락, SaaS
  대형주 치고 이례적으로 저렴)했으나, 실측 재무데이터는 정반대다 -
  5y 매출 CAGR 13.06%, **FCF CAGR이 매출보다 더 빠른 13.17%**(마진
  확장 중), FCF수익률 9.86%(문턱 4.86%의 2배). 관측구간(2014~2025)
  최악 YoY 매출성장률이 +10.24%로 **12년간 단 한 번도 역성장이 없었다**
  (코로나 해도 +15.19%). 회사 발표 AI-first ARR도 전년比 3배 성장 -
  AI가 위협이 아니라 오히려 신규 성장동력으로 편입되고 있다는 근거.
  전형적 4분류 1번(공포과잉) - 서사(AI 파괴 우려)가 아직 숫자에 나타나지
  않은 상태에서 시장이 선반영했다.
- **SHOP(Shopify) - 성장은 ADBE보다도 강하나(YoY +34.3%, 4개분기
  연속 30%+, AI 트래픽 8배 증가) 밸류에이션이 이미 너무 높아 탈락.**
  FCF수익률 단 1.25%(EV/EBITDA 68.6x, P/S 12.94x) - "30% 하락"이
  이미 훨씬 더 비쌌던 출발점에서의 하락이라 여전히 극단적 프리미엄
  밸류에이션. Agentic commerce의 실질적 수혜주(ChatGPT/Copilot/Google
  안에서 상거래를 구동하는 유일한 플랫폼)라는 서사는 오히려 사실에
  가까워 보이나, 그 사실이 이미 주가에 과반영돼 있다 - EME와 동일한
  "이미비쌈"(4분류 2번) 유형. Salesforce(CRM)는 Alpha Vantage 일일
  호출한도(25회/일) 소진으로 이번 라운드에서 재무데이터 미확보 -
  다음 세션에서 이어서 확인할 것.

**⚠️ ADBE는 이 배치에서 유일한 통과 종목이므로 engine/pipeline.py의
run_analysis()로 정식분석 우선순위 1순위.** 스크리너 추정치(estimate_drs
등 근사)일 뿐 정식 판정이 아니다 - 특히 AI 파괴 리스크 같은 정성적
경쟁강도(competition_intensity)는 스크리너가 상수로 가정하므로(PDD
선례와 동일 한계), 정식분석 시 실제 근거를 갖고 입력할 것.

**4차 라운드(동일 08-06 세션, 사용자 요청 "ETF에서" -> "스스로 많은
섹터 분석 비교") - ETF 구성종목 기반 발굴, IGV/XLV는 WebSearch로 정성
스크리닝만, SOXX 3종목은 SEC EDGAR 원자료로 정식 확인**:

- **IGV(소프트웨어) 구성종목 확인**: 상위 25종목 중 CDNS/ROP/WDAY/PTC는
  이미 정식분석 완료, ZM/INTU는 이미 탈락 확정(저성장/진짜나빠짐).
  CRM(Salesforce)이 유력 후보로 식별돼 아래에서 SEC EDGAR로 정식 확인.
- **XLV(헬스케어) 확인**: 상위 25종목 대부분 이미 분석완료(UNH/CVS/
  SYK/MCK/COR/CI/BSX/REGN)이거나 이번 검색에서 뚜렷한 "공포과잉" 신호를
  못 찾음(대형제약 LLY/JNJ/MRK/PFE 등은 최근 급락 뉴스 자체가 없었음) -
  이번 라운드에서는 신규 후보를 추가하지 않는다.

**5차 라운드(동일 08-06 세션, 사용자 재촉 "etf조사하라고") - Alpha
Vantage 일일한도 소진 지속으로 SEC EDGAR XBRL companyconcept API 직접
조회로 전환(TYL/GWRE SBC 크로스체크와 동일 방식)**:

- **CRM(Salesforce) - ADBE와 동일 패턴, 두 번째 통과 종목(A등급,
  Gap 추정 +10.84%p).** SEC EDGAR 실측: FY2025(2025-01-31) 매출
  \$41.525B, 5y 매출 CAGR 14.34%, **FCF 5y CAGR 28.12%**(매출보다
  훨씬 빠름 - 이연수익 증가+마진확장), FCF수익률 8.29%(문턱의 2배
  이상). 관측구간(FY2017~2025) 최악 YoY도 +8.72%로 단 한 번도 역성장
  없음. Agentforce ARR +205%YoY(\$1.2B, 회사발표)가 KeyBanc의 "채택
  둔화" 다운그레이드 근거와 정면으로 배치 - ADBE와 마찬가지로 서사가
  아직 숫자에 반영되지 않은 상태.
- **SOXX(반도체) 재검토 결과 - 가설이 실측으로 기각됨, 정직하게 기록.**
  KLAC/KEYS 패턴(trailing CAGR이 AI 수요 인플렉션을 과소추정)이 같은
  공정제어/테스트장비 하위섹터인 AMAT/LRCX/TER에도 재현될 것이라는
  가설을 세웠으나, **SEC EDGAR 실측 결과 셋 다 탈락 - 그것도 KLAC/KEYS와
  정반대 이유였다**:
  - AMAT: 매출 5y CAGR 10.52%·FCF CAGR 11.00%로 성장 자체는 견조하나,
    시가총액이 이미 \$443B까지 랠리해 FCF수익률 1.29%(문턱 5.09%의
    1/4)로 밸류에이션 탈락. Gap 거의 0(-0.00%p) - "저평가"가 아니라
    "정확히 적정가"에 가깝다.
  - LRCX: 매출 5y CAGR 12.91%·FCF CAGR 9.85%로 역시 견조하나 시총
    \$350.7B로 FCF수익률 1.54% - 동일하게 밸류에이션 탈락(Gap -0.33%p).
  - TER: AMAT/LRCX와 반대로 **성장 자체가 진짜 꺾였다** - 매출 5y CAGR
    0.44%(2020년 팬데믹 특수 고점 기저효과), FCF 5y CAGR -8.02%(마진
    악화 동반). 밸류에이션도 여전히 비쌈(FCF수익률 0.79%) - 이중탈락
    (Gap -17.31%p, 트래커 최저권).
  **결론: KLAC/KEYS 패턴은 "회사가 최근 급락"이 전제조건인데, AMAT/
  LRCX는 애초에 급락한 적이 없다(오히려 AI 랠리로 최고가권) - 섹터
  뉴스만 보고 개별 주가 흐름을 확인하지 않은 채 가설을 세운 것이
  원인이다. 반도체 섹터 전체를 배제한 1차 라운드 판단이 결과적으로
  맞았다.** 다음에 이 패턴을 다시 적용할 땐 "최근 실제로 급락했는가"부터
  먼저 확인할 것(BKNG/PDD 스크리너 한계 항목이 강조하는 것과 같은
  교훈 - 원인을 확인 없이 그럴듯하게 확정하지 말 것).

실행: python3 scripts/screen_2026_08_06.py
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

# ── SPGI (S&P Global) ──
# 2026 가이던스 하향(EPS 9.7%p 컷) + Energy부문 이란제재 여파로 52주 고점
# 543->저점 359권까지 하락. ⚠️ 2022-02 IHS Markit 인수($44B, 반반 현금+주식)가
# 5년 CAGR 창(2020년 기준)에 정확히 걸려 있다 - GEN/BRO 선례와 동일한
# M&A CAGR 왜곡 우려. 3y(2022년 이후, 합병완료 후) CAGR도 별도 계산해 대조.
_rev = {2014: 5051, 2015: 5313, 2016: 5661, 2017: 6063, 2018: 6258, 2019: 6699,
        2020: 7442, 2021: 8297, 2022: 11181, 2023: 12497, 2024: 14208, 2025: 15336}
_ocf = {2020: 3567, 2021: 3598, 2022: 2603, 2023: 3710, 2024: 5689, 2025: 5651}
_capex = {2020: 76, 2021: 35, 2022: 89, 2023: 143, 2024: 124, 2025: 195}
_fcf = {y: _ocf[y] - _capex[y] for y in _ocf}
CANDIDATES.append(Candidate(
    ticker="SPGI", name="S&P Global", exchange="NYSE",
    market_cap=121613.844, fcf0=_fcf[2025],
    revenue_cagr_5y=cagr(_rev[2020], _rev[2025], 5), fcf_cagr_5y=cagr(_fcf[2020], _fcf[2025], 5),
    net_debt_to_ebitda=0.6, worst_yoy_revenue=worst_yoy(_rev),
    note=(
        f"내재성장률 5.88% > 5.5% 문턱 근소초과로 탈락(FCF수익률 4.49%, 필요 4.86%) "
        f"- 이 배치에서 가장 아까운 탈락. IHS Markit 인수 여파로 5y FCF CAGR이 "
        f"과대추정됐을 가능성도 있음(3y 매출 CAGR {cagr(_rev[2022], _rev[2025], 3)*100:.2f}% "
        f"vs 5y {cagr(_rev[2020], _rev[2025], 5)*100:.2f}% - 3y가 더 낮아 5y가 부풀려진 "
        f"신호는 아니었으나 합병 자체가 FCF0 규모를 구조변경했다는 점은 유의). "
        f"영업마진 44.8%(TTM)의 초고마진 데이터·애널리틱스 비즈니스라 질적으로는 "
        f"매력적 - 향후 주가 추가하락 시 재확인 가치 있음."
    ),
))

# ── MOH (Molina Healthcare) ──
# Medicaid MCR 92.2%(전년 90.4%)까지 악화, 경영진 스스로 "2026이 마진 트로프"라고
# 표현. 2025 OCF가 -$535M으로 적자전환 - FCF-DCF 모델 자체가 적용 불가.
_ocf_moh = {2019: 427, 2020: 1890, 2021: 2119, 2022: 773, 2023: 1662, 2024: 644, 2025: -535}
_capex_moh = {2019: 57, 2020: 74, 2021: 77, 2022: 91, 2023: 84, 2024: 100, 2025: 101}
_fcf_moh = {y: _ocf_moh[y] - _capex_moh[y] for y in _ocf_moh}
CANDIDATES.append(Candidate(
    ticker="MOH", name="Molina Healthcare", exchange="NYSE",
    market_cap=9988.992, fcf0=_fcf_moh[2025],
    revenue_cagr_5y=0.0, fcf_cagr_5y=0.0,  # FCF0<=0이라 screen()이 즉시 Model N/A 처리
    net_debt_to_ebitda=1.0, worst_yoy_revenue=-0.057,
    note=(
        "FCF0 -$636M(OCF -$535M, 2025) - Model N/A. QuarterlyRevenueGrowthYOY "
        "-5.7%로 매출 자체가 역성장 중이고, 경영진이 스스로 '트로프 연도'라 표현한 "
        "메디케이드 요율-의료비 미스매치가 원인 - 서사가 아니라 회사 확인 "
        "펀더멘털 문제(4분류 3번, 진짜나빠짐). Managed care 특유 회계구조(보험료 "
        "선수취-의료비 후지급)로 OCF 변동성이 커 SOFI와 유사하게 표준 FCF-DCF "
        "적용에 신중해야 함(별도 방법론 미확립)."
    ),
))

# ── MLM (Martin Marietta Materials) ──
# $13.5B Lhoist North America 인수(미종결, 현금+주식) 발표로 희석·레버리지
# (3.7x 예상) 우려 - 52주 고점 709->556권(-21%). 다만 이 우려는 아직 재무제표에
# 반영 안 됨(딜 미종결) - 현재 수치는 순수 스탠드얼론 실적.
_rev_mlm = {2014: 2957.951, 2015: 3539.57, 2016: 3818.749, 2017: 3965.6, 2018: 4244.3,
            2019: 4739.1, 2020: 4729.9, 2021: 5414, 2022: 6161, 2023: 6777, 2024: 6536, 2025: 6544}
_ocf_mlm = {2020: 1050.1, 2021: 1137.7, 2022: 991.2, 2023: 1528, 2024: 1459, 2025: 1785}
_capex_mlm = {2020: 359.7, 2021: 423.1, 2022: 481.8, 2023: 650, 2024: 855, 2025: 807}
_fcf_mlm = {y: _ocf_mlm[y] - _capex_mlm[y] for y in _ocf_mlm}
CANDIDATES.append(Candidate(
    ticker="MLM", name="Martin Marietta Materials", exchange="NYSE",
    market_cap=33385.796, fcf0=_fcf_mlm[2025],
    revenue_cagr_5y=cagr(_rev_mlm[2020], _rev_mlm[2025], 5), fcf_cagr_5y=cagr(_fcf_mlm[2020], _fcf_mlm[2025], 5),
    net_debt_to_ebitda=2.07,  # 근사치: (EV-MarketCap)/EBITDA_TTM, 대차대조표 API 미접근
    worst_yoy_revenue=worst_yoy(_rev_mlm),
    note=(
        "밸류에이션·성장 이중탈락. FCF수익률 2.93%(자본집약적 골재사업 특성상 "
        "capex가 매출의 12%대) - 내재성장률 7.83%로 문턱(5.5%) 크게 초과. "
        "현실적성장률도 6.03%<8.0% 미달(최근 2년 매출 정체 6777->6536->6544, "
        "포트폴리오 조정 여파 추정). EV/EBITDA 18x·PER 36x로 이미 밸류에이션 "
        "높음 - '많이 떨어졌다'가 아니라 '원래도 비쌌다'(4분류 2번, 이미비쌈). "
        "Lhoist 인수가 종결되면 레버리지 3.7x·주식수 증가로 오히려 상황이 "
        "악화될 가능성 - 딜 종결 후 재확인 시 우선순위 낮음."
    ),
))

# ── LKQ (LKQ Corporation, 자동차 대체부품 유통) ──
# 독일 ERP 시스템 장애($140M 매출타격+$50M EBITDA손실)로 2026 가이던스 하향,
# -14% 급락. "일회성 운영이슈"로 프레이밍됐으나 재무데이터를 보면 이슈와
# 무관하게 원래부터 저성장(5y 매출CAGR 3.66%)이고 FCF CAGR은 오히려 마이너스
# (2020년 $1,271M -> 2025년 $847M, -33%) - 자동차 애프터마켓 부품 롤업업체
# 특유의 성숙기 정체가 ERP 이슈로 가려져 있었을 뿐이다.
_rev_lkq = {2014: 6740.064, 2015: 7192.633, 2016: 8584.031, 2017: 9736.909, 2018: 11876.674,
            2019: 12506.109, 2020: 11628.83, 2021: 13089, 2022: 12794, 2023: 13866, 2024: 14355, 2025: 13916}
_ocf_lkq = {2020: 1443.87, 2021: 1367.047, 2022: 1250, 2023: 1356, 2024: 1121, 2025: 1063}
_capex_lkq = {2020: 172.695, 2021: 293.466, 2022: 222, 2023: 358, 2024: 311, 2025: 216}
_fcf_lkq = {y: _ocf_lkq[y] - _capex_lkq[y] for y in _ocf_lkq}
CANDIDATES.append(Candidate(
    ticker="LKQ", name="LKQ Corporation", exchange="NASDAQ",
    market_cap=6196.021, fcf0=_fcf_lkq[2025],
    revenue_cagr_5y=cagr(_rev_lkq[2020], _rev_lkq[2025], 5), fcf_cagr_5y=cagr(_fcf_lkq[2020], _fcf_lkq[2025], 5),
    net_debt_to_ebitda=1.8,  # EVToRevenue 근사 기반 추정
    worst_yoy_revenue=worst_yoy(_rev_lkq),
    note=(
        "저성장 이중탈락(밸류에이션은 확인 불필요할 만큼 성장이 먼저 미달). "
        "5y 매출 CAGR 3.66%<8.0%, FCF CAGR은 마이너스(2020년 대비 -33%) - "
        "독일 ERP 이슈(2026 특수사건)를 걷어내도 원래 저성장 롤업기업이었다. "
        "'일회성 이슈'라는 서사에 낚이지 않도록 4분류 프레임워크가 정확히 "
        "의도한 판별."
    ),
))

# ── EME (EMCOR Group, 전기·기계 설비공사) ──
# 데이터센터/전력인프라 건설 수요 직접 수혜주. 펀더멘털은 최상급이나 이미
# 상당히 비싸게 거래되고 있어(-5~-10% 조정에도) 밸류에이션 문턱을 못 넘었다.
_rev_eme = {2014: 6424.965, 2015: 6718.726, 2016: 7551.524, 2017: 7686.999, 2018: 8130.631,
            2019: 9174.611, 2020: 8797.061, 2021: 9903.58, 2022: 11076.12, 2023: 12582.873,
            2024: 14566.116, 2025: 16990}
_ocf_eme = {2020: 806.366, 2021: 318.817, 2022: 497.933, 2023: 899.655, 2024: 1407.894, 2025: 1302.063}
_capex_eme = {2020: 47.969, 2021: 36.192, 2022: 49.289, 2023: 78.404, 2024: 74.95, 2025: 112.75}
_fcf_eme = {y: _ocf_eme[y] - _capex_eme[y] for y in _ocf_eme}
CANDIDATES.append(Candidate(
    ticker="EME", name="EMCOR Group", exchange="NYSE",
    market_cap=36164.825, fcf0=_fcf_eme[2025],
    revenue_cagr_5y=cagr(_rev_eme[2020], _rev_eme[2025], 5), fcf_cagr_5y=cagr(_fcf_eme[2020], _fcf_eme[2025], 5),
    net_debt_to_ebitda=-0.68,  # EVToRevenue 근사 기반, 순현금 추정
    worst_yoy_revenue=worst_yoy(_rev_eme),
    note=(
        "밸류에이션 단독 탈락(성장은 통과: 현실적성장률 추정 8.46%>=8.0%). "
        "FCF수익률 3.29%로 문턱(필요 4.86%)에 못 미침 - 분기매출 +19.8%YoY· "
        "이익 +34.8%YoY의 최상급 펀더멘털이지만 이미 그만큼 비싸게 거래 중 "
        "(P/E 25.5x). SPGI와 동일 유형('좋은 회사인 걸 시장도 이미 안다') - "
        "추가 조정 시 재확인 가치 있음(SPGI보다 성장은 확실히 우위)."
    ),
))

# ── ADBE (Adobe) - 이 배치 유일한 통과 종목 ──
# "생성형AI가 Photoshop을 대체한다"는 서사로 52주 고점 대비 -46%했으나
# 실측 재무데이터는 정반대(매출·FCF 모두 두 자릿수 성장, FCF가 매출보다
# 더 빠르게 성장 - 마진 확장 중). 12년 관측구간 최악 YoY도 +10.24%로
# 단 한 번도 역성장 없음(코로나 해도 +15.19%).
_rev_adbe = {2014: 4147.065, 2015: 4795.511, 2016: 5854.43, 2017: 7301.505, 2018: 9030.008,
             2019: 11171.297, 2020: 12868, 2021: 15785, 2022: 17606, 2023: 19409, 2024: 21505, 2025: 23769}
_ocf_adbe = {2020: 5727, 2021: 7230, 2022: 7838, 2023: 7302, 2024: 8056, 2025: 10031}
_capex_adbe = {2020: 419, 2021: 330, 2022: 442, 2023: 360, 2024: 232, 2025: 179}
_fcf_adbe = {y: _ocf_adbe[y] - _capex_adbe[y] for y in _ocf_adbe}
CANDIDATES.append(Candidate(
    ticker="ADBE", name="Adobe", exchange="NASDAQ",
    market_cap=99907.65, fcf0=_fcf_adbe[2025],
    revenue_cagr_5y=cagr(_rev_adbe[2020], _rev_adbe[2025], 5), fcf_cagr_5y=cagr(_fcf_adbe[2020], _fcf_adbe[2025], 5),
    net_debt_to_ebitda=0.11,  # EVToRevenue 근사 기반, 순부채 거의 없음
    worst_yoy_revenue=worst_yoy(_rev_adbe),
    note=(
        "이 배치 유일한 통과 종목(A등급, Gap 추정 +11.15%p). AI 파괴 서사로 "
        "-46% 급락했으나 매출 5y CAGR 13.06%, FCF CAGR 13.17%(매출보다 빠름 - "
        "마진확장), FCF수익률 9.86%(문턱의 2배). AI-first ARR 전년比 3배(회사"
        "발표) - AI가 위협이 아니라 신규 성장동력으로 편입 중일 가능성. 정식분석 "
        "우선순위 1순위 - competition_intensity(AI 경쟁 위협의 실체) 등 정성적 "
        "입력은 스크리너가 못 보므로 반드시 별도 근거 확보할 것."
    ),
))

# ── SHOP (Shopify) - 성장은 ADBE보다 강하나 밸류에이션 탈락 ──
# YoY +34.3%(4개분기 연속 30%+대), agentic commerce 실질 수혜주 서사도
# 사실에 가까우나 이미 극단적 프리미엄 밸류에이션(EV/EBITDA 68.6x)이라
# FCF수익률이 1.25%에 불과 - "30% 하락"이 훨씬 더 비쌌던 출발점에서의
# 하락일 뿐. Alpha Vantage 일일한도로 revenue_cagr_5y는 CompanyOverview의
# QuarterlyRevenueGrowthYOY(34.3%)로 근사(정식 5y CAGR 미확보 - 어느 쪽이든
# FCF수익률이 결정적 탈락사유라 결론에 영향 없음).
CANDIDATES.append(Candidate(
    ticker="SHOP", name="Shopify", exchange="NASDAQ",
    market_cap=160000.819, fcf0=2007,  # 2025 OCF 2033 - capex 26
    revenue_cagr_5y=0.343, fcf_cagr_5y=0.343,  # 근사(위 설명 참고) - 밸류에이션이 결정적 탈락사유
    net_debt_to_ebitda=0.0,
    worst_yoy_revenue=0.10,  # 보수적 추정(정식 데이터 미확보)
    note=(
        "밸류에이션 탈락 - 성장(YoY+34.3%, ADBE보다 강함)은 문제가 아니다. "
        "FCF수익률 1.25%(EV/EBITDA 68.6x, P/S 12.94x)로 문턱에 크게 못 미침. "
        "Agentic commerce 수혜주 서사는 사실에 가까우나 이미 주가에 과반영 - "
        "EME와 동일한 '이미비쌈' 유형. 밸류에이션이 큰 폭으로 추가 하락하면 "
        "재확인 가치 있음(ADBE보다 낙폭이 더 커야 통과권에 진입할 것)."
    ),
))

# ── CRM (Salesforce) - ADBE와 동일 패턴, 두 번째 통과 종목 ──
# 원자료: SEC EDGAR XBRL companyconcept API(CIK0001108524, 2026-08-06 조회,
# Alpha Vantage 일일한도 소진으로 전환). "SaaSpocalypse" 서사로 YTD -33%했으나
# FCF가 매출보다 훨씬 빠르게 성장(5y CAGR 28.12% vs 매출 14.34%) - ADBE보다도
# 마진확장 속도가 빠르다. FY 표기는 Salesforce 회계연도(1/31 마감) 기준.
_rev_crm = {2017: 10540, 2018: 13282, 2019: 17098, 2020: 21252, 2021: 26492,
            2022: 31352, 2023: 34857, 2024: 37895, 2025: 41525}
_ocf_crm = {2020: 4331, 2025: 13092}
_capex_crm = {2020: 710, 2025: 594}
_fcf_crm = {y: _ocf_crm[y] - _capex_crm[y] for y in _ocf_crm}
CANDIDATES.append(Candidate(
    ticker="CRM", name="Salesforce", exchange="NYSE",
    market_cap=150710, fcf0=_fcf_crm[2025],
    revenue_cagr_5y=cagr(_rev_crm[2020], _rev_crm[2025], 5), fcf_cagr_5y=cagr(_fcf_crm[2020], _fcf_crm[2025], 5),
    net_debt_to_ebitda=0.62,  # 총부채 $17.7B - 현금성자산 근사, EBITDA 근사치 기준
    worst_yoy_revenue=worst_yoy(_rev_crm),
    note=(
        "이 배치 두 번째 통과 종목(A등급, Gap 추정 +10.84%p) - ADBE와 완전히 "
        "동일한 패턴. SaaSpocalypse 서사로 YTD -33%(52주 고점267->저점146)했으나 "
        "FY2025(2025-01-31) 매출 $41.525B, 5y 매출 CAGR 14.34%, FCF 5y CAGR "
        "28.12%(매출보다 훨씬 빠름 - 이연수익 증가+마진확장). FY2017~2025 관측 "
        "구간 최악 YoY도 +8.72%로 단 한 번도 역성장 없음. Agentforce ARR "
        "+205%YoY($1.2B, 회사발표)가 KeyBanc의 '채택 둔화' 다운그레이드 근거와 "
        "정면 배치 - 서사가 아직 숫자에 반영 안 된 상태. ADBE와 함께 정식분석 "
        "우선순위 상위."
    ),
))

# ── AMAT/LRCX/TER (반도체 공정제어·테스트장비) - KLAC/KEYS 패턴 가설, 실측으로 기각 ──
# 원자료: SEC EDGAR XBRL(CIK0000006951/CIK0000707549/CIK0000097210, 2026-08-06).
# 가설(같은 하위섹터라 KLAC/KEYS의 trailing CAGR 과소추정이 재현될 것)이
# 실측으로 기각됐다 - AMAT/LRCX는 애초에 급락한 적이 없어(AI 랠리로 오히려
# 최고가권) 밸류에이션이 이미 성장을 반영, TER는 반대로 성장 자체가 진짜
# 꺾였다(팬데믹 특수 기저효과+마진악화). 셋 다 서로 다른 이유로 탈락.
_rev_amat = {2018: 16705, 2019: 14608, 2020: 17202, 2021: 23063, 2022: 25785,
             2023: 26517, 2024: 27176, 2025: 28368}
_fcf_amat = {2020: 3804 - 422, 2025: 7958 - 2260}
CANDIDATES.append(Candidate(
    ticker="AMAT", name="Applied Materials", exchange="NASDAQ",
    market_cap=443000, fcf0=_fcf_amat[2025],
    revenue_cagr_5y=cagr(_rev_amat[2020], _rev_amat[2025], 5), fcf_cagr_5y=cagr(_fcf_amat[2020], _fcf_amat[2025], 5),
    net_debt_to_ebitda=0.3,
    worst_yoy_revenue=worst_yoy(_rev_amat),
    note=(
        "밸류에이션 탈락(Gap 거의 0, -0.00%p) - KLAC/KEYS 가설과 달리 성장은 "
        "이미 충분히 반영돼 있다. 매출 5y CAGR 10.52%·FCF CAGR 11.00%로 견조하나 "
        "AI 랠리로 시총이 이미 $443B까지 상승해 FCF수익률 1.29%(문턱 5.09%의 "
        "1/4). KLAC/KEYS 패턴의 전제조건('회사가 최근 급락')이 애초에 성립하지 "
        "않는 종목이었다 - 섹터 뉴스만 보고 개별주가를 확인 안 한 게 원인."
    ),
))

_rev_lrcx = {2017: 8013.62, 2018: 11076.998, 2019: 9653.559, 2020: 10044.736, 2021: 14626.15,
             2022: 17227.039, 2023: 17428.516, 2024: 14905.386, 2025: 18435.591}
_fcf_lrcx = {2020: 3588.163 - 203.239, 2025: 6173.264 - 759.186}
CANDIDATES.append(Candidate(
    ticker="LRCX", name="Lam Research", exchange="NASDAQ",
    market_cap=350710, fcf0=_fcf_lrcx[2025],
    revenue_cagr_5y=cagr(_rev_lrcx[2020], _rev_lrcx[2025], 5), fcf_cagr_5y=cagr(_fcf_lrcx[2020], _fcf_lrcx[2025], 5),
    net_debt_to_ebitda=0.2,
    worst_yoy_revenue=worst_yoy(_rev_lrcx),
    note=(
        "AMAT와 동일 유형 - 밸류에이션 탈락(Gap -0.33%p). 매출 5y CAGR "
        "12.91%·FCF CAGR 9.85%로 견조하나 시총 $350.7B(AI 랠리 반영)로 "
        "FCF수익률 1.54%에 불과. KLAC/KEYS와 달리 이 종목은 최근 급락한 적이 "
        "없다."
    ),
))

_rev_ter = {2014: 1647.824, 2015: 1639.578, 2016: 1753.25, 2017: 2136.606, 2018: 2100.802,
            2019: 2294.965, 2020: 3121.469, 2021: 3702.881, 2022: 3155.045, 2023: 2676.298,
            2024: 2819.88, 2025: 3190.024}
_fcf_ter = {2020: 868.935 - 184.977, 2025: 674.415 - 224.009}
CANDIDATES.append(Candidate(
    ticker="TER", name="Teradyne", exchange="NASDAQ",
    market_cap=57210, fcf0=_fcf_ter[2025],
    revenue_cagr_5y=cagr(_rev_ter[2020], _rev_ter[2025], 5), fcf_cagr_5y=cagr(_fcf_ter[2020], _fcf_ter[2025], 5),
    net_debt_to_ebitda=0.1,
    worst_yoy_revenue=worst_yoy(_rev_ter),
    note=(
        "AMAT/LRCX와 정반대 이유로 이중탈락(Gap -17.31%p, 이 배치 최저권) - "
        "성장 자체가 진짜 꺾였다. 매출 5y CAGR 0.44%(2020년 팬데믹 특수 고점이 "
        "기준연도라 사실상 정체), FCF 5y CAGR -8.02%(마진 악화 동반). "
        "밸류에이션도 여전히 비쌈(FCF수익률 0.79%) - KLAC/KEYS의 '숨겨진 가속'이 "
        "아니라 진짜나빠짐(4분류 3번)에 가깝다."
    ),
))

# ── 아래는 WebSearch 확인 단계에서 '진짜 나빠짐'으로 판정, 재무데이터 없이 제외 ──
PREFILTERED_OUT = {
    "APTV(Aptiv)": (
        "FY2026 매출 가이던스 $300M 하향 + EBITDA마진 90bp 하락(15.7%->14.8%). "
        "Rivian-VW 파트너십이 전기차 전장 아키텍처 자체제작으로 Aptiv의 해자를 "
        "직접 위협한다는 애널리스트 우려(Barclays/UBS/HSBC 목표가 일제히 하향). "
        "EV 수요둔화+경쟁위협 동시 - 4분류 3번(진짜나빠짐)."
    ),
    "DVA(DaVita)": (
        "Q2 2026 실적은 컨센서스 상회했으나 상업보험 가입자 비중 하락(정부보조 "
        "플랜으로 이전) 추세가 2026년 내내 이어질 것으로 경영진이 직접 가이던스 - "
        "치료당 매출 성장률 둔화가 서사가 아니라 회사 확인 트렌드. 2019년 이후 "
        "환자수 자체도 감소 - 진짜나빠짐."
    ),
    "TDC(Teradata)": (
        "Q3 2026 매출 가이던스 -4~-6%YoY, 5년 추세 자체가 -3%/년 지속 축소 - "
        "'클라우드 전환기 일시적 부진'이 아니라 5년 연속 구조적 축소. 진짜나빠짐."
    ),
    "CRTO(Criteo)": (
        "Q1 2026 매출 -6%YoY, 리테일미디어 -31%. 2026 연간 가이던스 자체가 "
        "'low single digit 감소' - 경영진이 스스로 역성장을 예고. 진짜나빠짐."
    ),
    "RRX(Regal Rexnord)": (
        "Q2 2026 FCF가 전년동기 +$85.5M -> -$2.5M로 적자전환, 매출성장도 "
        "4.2%로 저조. 레거시 산업재 수요둔화가 데이터센터向 성장을 상쇄 - "
        "저성장+FCF 악화 이중신호."
    ),
}


def main():
    results = screen_all(CANDIDATES)

    print("=" * 108)
    print("2026-08-06 스크리닝 결과")
    print("=" * 108)
    print(format_table(results))
    print()

    n_passed = sum(1 for r in results if r.passed)
    print(f"통과: {n_passed}/{len(results)}종목")
    print()

    print("=" * 108)
    print("⚠️ 재무데이터 확보 종목 상세(통과/탈락 포함, 11종목)")
    print("=" * 108)
    for r in results:
        c = r.candidate
        mark = "[통과]" if r.passed else "[탈락]"
        print(f"  {mark} {c.ticker:6} {c.name}")
        print(f"    -> {c.note}")
        if r.failures:
            for f in r.failures:
                print(f"       [탈락사유] {f}")
        print()

    print("=" * 108)
    print("⚠️ WebSearch 확인 단계에서 '진짜 나빠짐'으로 사전 제외(재무데이터 미확보)")
    print("=" * 108)
    for ticker, reason in PREFILTERED_OUT.items():
        print(f"  {ticker}")
        print(f"    -> {reason}")

    print("\n" + "=" * 108)
    print("이 결과는 후보를 좁힌 1차 필터일 뿐 판정이 아니다.")
    print("통과 종목은 반드시 engine/pipeline.py의 run_analysis()로 정식 분석할 것.")
    passed_tickers = ", ".join(r.candidate.ticker for r in results if r.passed)
    print(f"이번 배치는 총 {len(results)}종목 중 {n_passed}종목 통과({passed_tickers}) - ")
    print("07-31/08-06 1·2차 라운드 전수탈락 이후 3·5차 라운드에서 SaaS 섹터")
    print("2종목(ADBE/CRM) 통과, 반도체 섹터(AMAT/LRCX/TER) 가설은 실측으로 기각.")
    print("=" * 108)


if __name__ == "__main__":
    main()
