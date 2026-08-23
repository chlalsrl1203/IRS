"""
매수관점 후보 스크리너 (v3.19 신규, 2026-07-26)

왜 만들었나:
트래커 74건을 전수 분석하니 저평가/매수 판정군(13건)과 과대평가/회피군(18건)이
두 축으로 거의 완벽하게 갈렸다. 이 판별식을 사람의 감이 아니라 코드로 고정한다.

  ⚠️ **이 판별력은 "엔진 자기 라벨" 대비다, 시장 대비가 아니다** (2026-08-01
  방법론 감사 High-1에서 지적): 아래 저평가군/과대평가군은 실제 주가 움직임이
  아니라 engine/pipeline.py의 run_analysis()가 내린 판정을 정답지로 삼은 것이다.
  즉 이 수치는 "스크리너가 엔진을 잘 근사한다"는 뜻이며, **"엔진이 시장을 이긴다"는
  근거가 아니다.** 이 프로젝트는 실현수익률로 검증된 적이 단 한 번도 없다
  (`grep -rli 'backtest|실현수익|realized_return|out_of_sample' engine/ tests/
  scripts/` → 결과 없음). 아래 판별력 수치를 읽을 때 이 구분을 반드시 유지할 것.

  실측 판별력 (트래커 전수, 2026-07-26, **엔진 자체 판정 기준**):
    Realistic Growth >= 8%   : 저평가군 13/13 (100%)  vs 과대평가군  2/18 (11%)
    Implied Growth   <= 5.5% : 저평가군 11/13 ( 85%)  vs 과대평가군  0/18 ( 0%)
    둘 다 충족               : 저평가군 11/13 ( 85%)  vs 과대평가군  0/18 ( 0%)

  ⚠️ **재검증 (2026-07-31, ledger/ 27종목 전수 - DECK/ACGL/ROP 등 ledger가
  없는 v3.18 이전 분석은 이 재검증에서 제외돼 표본이 다름)**:
    screen() 실제 호출        : 저평가군 11/11(100%)  vs 과대평가군  0/2 ( 0%)
  임계값·estimate_drs() 둘 다 안 건드렸다 - 그대로 재검증만 했고 여전히
  깨끗하게 통과한다. **주의**: 처음엔 "저평가군의 엔진 정식 Implied
  Growth 값(DRS 전체 5요소 반영)을 5.5% 임계값과 직접 비교"하는 방식으로
  재검증했다가 DUOL/BKNG/PTC 3건이 근소하게(0.5%p 이내) 못 미치는
  것처럼 보여 "근접탈락" 보정 로직을 추가했었다 - 그런데 이는 잘못된
  비교였다. **screen()은 정식 DRS가 아니라 estimate_drs()의 자체 근사치
  (2요소 실측+3요소 중앙값 가정)로 별도의 r을 계산**하므로, 정식
  Implied Growth와 스크리너 추정 Implied Growth는 애초에 다른 수치다.
  실제로 screen()을 그대로 호출해보니 11/11 전부 통과했다 - 가짜
  결함을 근거로 코드를 고칠 뻔한 사례라 기록해둔다(v3.12 가짜버전
  사건과 같은 계열의 교훈: 검증 없이 그럴듯한 원인을 확정하지 말 것).

문제는 Implied Growth/Realistic Growth 둘 다 엔진을 돌려야 나오는 값이라
스크리닝 단계에서는 쓸 수 없다는 것이다. 그래서 **관측 가능한 시장지표로
역산**해서 1차 필터로 쓴다.

1) Implied Growth -> FCF수익률 (정확한 항등식, ledger 12건에서 오차 0 검증)
   단일단계 Gordon:  MarketCap = FCF0(1+g)/(r-g)
   y = FCF0/MarketCap 로 두면  g = (r - y)/(1 + y)  <=>  y = (r - g)/(1 + g)
   즉 Implied Growth 상한을 정하면 FCF수익률 하한이 정확히 결정된다.

2) Realistic Growth -> min(FCF CAGR, 매출 CAGR) (근사, 구조적할인 역산)
   RG = min(FCF CAGR 5y, 매출가중평균) x (1 - 구조적할인) 이고
   구조적할인 실측 중앙값이 10.1%(범위 7.95~13.34%)이므로
   RG >= 8% 를 만족하려면 min(...) >= 약 8.9% 가 필요하다.
   **여기서 min()이 핵심이다** - 과대평가군 AJG/AZO/ELV가 RG 0.00~0.75%로
   추락한 원인이 정확히 이것이다(매출은 늘었는데 FCF가 못 따라와 FCF CAGR이
   채택되며 급락). 매출성장만 보는 일반 스크리너가 놓치는 지점.

주의: 이 스크리너는 **후보를 좁히는 1차 필터일 뿐** 판정이 아니다.
통과 종목은 반드시 engine/pipeline.py의 run_analysis()로 정식 분석할 것.

⚠️ **알려진 한계: 조회창이 짧으면 경기 저점을 통째로 놓친다** (BKNG 실사례,
2026-07-28에 정식분석과 대조하며 확인):
스크리닝은 보통 확보하기 쉬운 5개년만 쓰는데, 그 창 밖에 폭락기가 있으면
아래 둘이 동시에 왜곡된다.
  - worst_yoy_revenue가 실제보다 훨씬 좋게 잡혀 DRS가 과소추정된다
  - CAGR 기준연도가 회복 직후가 되어 '반등'을 '성장'으로 착각한다
BKNG(2021~2025 창) 실측 오차:
  최악 YoY   +11.11% (추정) vs -54.89% (실제, 2020 코로나)
  DRS          34.6  (추정) vs   56.0  (실제)  -> 21점 과소
  FCF CAGR   37.86%  (추정) vs  12.44%  (실제) -> 3배 과대
  Gap        +18.99%p(추정) vs  +5.98%p(실제) -> 13%p 과대
판정 **방향**은 맞았으나(둘 다 저평가) 크기는 크게 빗나갔다. 따라서
Gap 추정치로 후보 간 순위를 매길 때는 조회창 길이를 함께 볼 것. 특히
여행·항공·소재 등 경기민감 업종은 10년 이상 창으로 재확인이 필요하다.

⚠️ **알려진 한계 2건째: competition_intensity가 상수 placeholder** (PDD 실사례,
2026-07-28에 정식분석과 대조하며 확인):
BKNG과는 원인이 다른 별개의 한계다. `estimate_drs()`는 leverage/cyclicality만
실측하고 나머지 3개 DRS 구성요소(revenue_volatility/margin_volatility/
competition_intensity)는 ledger 중앙값 상수를 쓴다(스크리닝 단계에는 경쟁사
위협도·시장점유율추세 같은 정성적 입력이 없어 구조적으로 불가피). 규제·경쟁이
실제로 치열한 종목은 이 placeholder가 실제 competition_intensity를 크게
과소평가한다.
PDD 실측 오차(4년 조회창 2021~2025의 매출·FCF 원자료 자체는 SEC 실측치와
소수점까지 일치 - 조회창 길이가 원인이 아님을 확인):
  competition_intensity  12.0(상수) vs  20.0(만점, 실제)
  DRS                     30.6(추정) vs  45.4(실제)   -> 14.8점 과소
  현실적성장률            38.41%(추정) vs 25.00%(실제) -> 13.41%p 과대
  Gap                    +40.96%p(추정) vs +29.16%p(실제) -> 11.80%p 과대
판정 **방향**은 이번에도 맞았으나(둘 다 저평가) 크기는 신뢰할 수 없었다.
플랫폼·중국기업·반독점 노출 종목처럼 규제·경쟁 이슈가 뚜렷한 업종은
Gap 추정치를 정성적으로 할인해서 볼 것.

⚠️ **같은 한계의 반대방향 사례 - false rejection까지 발생함(BSX 실사례,
2026-08-13에 정식분석과 대조하며 확인)**: PDD는 실제 competition_intensity가
상수(12.0)보다 **높아서** Gap이 과대(방향은 맞음)였는데, BSX는 실제값이
상수보다 **낮아서**(경쟁자 2곳 모두 위협도가 낮게 평가됨 - RMD와 동일한
5.4) DRS가 50.6(추정)까지 과대평가돼 **판정 자체가 뒤집혔다**(screen()
탈락 vs 정식분석 "저평가 가능성" 통과, Gap +5.87%p). ledger 34종목 전수
재확인 결과 ASSUMED_COMPETITION_INTENSITY=12.0 상수 자체는 여전히 정확한
중앙값이다(median 12.0, mean 11.91) - 상수를 바꿔야 할 문제가 아니라,
median 대체 방식 자체가 median에서 크게 벗어난 개별종목(RMD/BSX처럼 실제
5.4대, VRSN/ROP처럼 실제 3.6~4.8대)에서는 구조적으로 오분류할 수 있다는
뜻이다. 이 스크리너의 "worst error"(docstring 문서화된 실제 저평가 종목을
거짓 탈락시키는 경우)가 실측으로 확인된 첫 사례라 `tests/test_screener.py`
의 골든테스트에 BSX를 문서화된 예외로 남겨뒀다 - screen()을 고쳐서 통과
시키지 않는다(고치면 다른 종목의 판정이 조용히 바뀔 위험).

⚠️ **후보 선정 전 1차 분류 - 재무데이터를 긁기 전에 먼저 걸러낼 것**
(2026-07-31, SE/RMD 통과 + 약 40종목 탈락을 훑으며 실측한 패턴):

병목은 screen() 자체가 아니라 "여기 넣을 후보를 어떻게 고르느냐"였다.
"최근 하락했다"는 후보 다수가 재무데이터까지 긁고 나서야 탈락 사유가
드러났는데, 아래 4가지로 미리 분류하면 그 전에 걸러진다:

1. **공포 과잉**(진짜 후보) - 성장은 안 꺾였는데 서사 하나(경쟁위협・
   규제우려・일시적 실적 미스)가 주가를 두들긴 경우. SE(TikTok Shop
   경쟁우려), RMD(GLP-1 수요파괴 우려) 둘 다 이 유형이었고, 최근 실적이
   서사와 반대로 움직이는지(RMD FY26 Q3 매출+11%) 확인하면 구분된다.
2. **이미 비쌈** - 실제로 하락했어도 FCF수익률이 여전히 낮은 경우.
   Chipotle(-18.8%인데 FCF수익률 2.96%), Insulet(-44.2%인데도 3.29%) -
   성장에 대한 시장 기대가 하락폭보다 더 높았던 경우라 "많이 떨어졌다"만
   보고 후보로 넣으면 헛수고다.
3. **진짜 나빠짐** - 하락이 정당한 경우. 매출・FCF가 실제로 꺾이는 중인
   종목(Lennox/Nike/Target/UPS/Charter Communications). 서사와 대조할
   필요도 없이 재무제표 자체가 답을 준다.
4. **버블 되돌림** - 1개월 하락률만 보면 낚인다. Micron(7월 -26.5%지만
   연초대비 +197%), SanDisk(연초대비 +471% 찍고 조정) - AI/메모리 랠리가
   과열된 뒤 일부 반납 중인 것이지 저평가가 아니다. **반드시 1년/YTD
   수익률까지 같이 확인할 것** - 최근 1개월 낙폭만 보고 후보에 넣으면
   "많이 올랐다가 조금 빠진 것"을 "쌓다"로 착각한다.

**프레임워크 자체가 안 맞는 자산군은 후보에서 아예 제외할 것**:
- 대마초(연방 불법 + 280E 세제로 GAAP 손익이 정상기업과 비교 불가)
- REIT(감가상각・배당구조가 표준 FCF-DCF와 다른 밸류에이션 체계 필요)
- 최근 M&A・사업분할이 CAGR 구간에 걸친 종목(Disney의 코로나 저점,
  Crown Castle의 파이버사업 매각, PTC/GEN 선례와 동일 유형) - 세그먼트
  조정 없이는 스크리닝 자체가 왜곡되므로 후순위로 미룬다.

이 4분류는 재무데이터를 긁기 전, WebSearch로 하락 배경을 확인하는
시점에 1줄로 판단 가능하다 - 여기서 "1번(공포과잉)"으로 분류된 것만
Candidate로 만들어 screen()에 넣을 것.

⚠️ **외부검증 완료(2026-08-23, 사용자 요청 - 저명 학술지·오픈소스 스크리닝
프로젝트 대조)**: 상세는 `reports/research/screening_criteria_external_
2026-08-23.md`. 요지만 남긴다 -

- **MIN_REALISTIC_GROWTH(8%)/MAX_IMPLIED_GROWTH(5.5%)/tier 경계에 대응하는
  절대 컷오프는 학술문헌에도, 조사한 오픈소스 스크리너(hjones20/fundamental-
  analysis, FinanceToolkit 등)에도 없다.** 다들 지표 계산 함수만 제공하고
  임계값은 사용자 파라미터로 남긴다 - "34~74종목 corpus에서 도출"이라는 지금의
  근거 수준이 그대로 최선이며, 바꿀 이유가 없다(REJECT, 근거 없는 숫자를 근거
  없는 다른 숫자로 바꾸지 않는다는 원칙).
- **오히려 절대 성장 하한선이라는 설계 자체에 학계 반례가 있다** - Greenblatt
  Magic Formula는 성장 입력을 아예 안 쓰고, Chan/Karceski/Lakonishok(2003 JF,
  structural_discount_rate 근거로 이미 인용된 문헌)은 "장기 이익성장에 우연
  이상의 지속성이 없다"고 본다. 8%를 없애야 한다는 뜻은 아니다(이 스크리너는
  예측력이 아니라 34~74종목 corpus와의 상관을 근거로 쓰는 1차 필터라 그
  반박이 직접 적용되지 않는다) - 다만 "이 하한선에 외부 학술 근거가 없다"는
  사실은 이제 기록됐다.
- **`implied_growth_from_fcf_yield`가 쓰는 reverse-DCF 비교 구조(시장가에서
  성장률을 역산해 독립 추정치와 대조) 자체는 강하게 지지된다** - Gebhardt/Lee/
  Swaminathan(2001, JAR, 피어리뷰 2000+인용)의 "내재자본비용" 역산 방법론과
  수학적으로 동형이고, Rappaport&Mauboussin의 "Expectations Investing"·
  Damodaran의 강의체계와 독립적으로 수렴한다. **단, 이건 아키텍처를 지지할 뿐
  5.5%라는 특정 숫자를 정당화하지 않는다** - 이 구분을 흐리면 거짓 권위 주장이
  된다.

아래 `VALIDATION_STATUS`가 이 결론을 기계 판독 가능한 라벨로 남긴다
(`engine/expectation_gap_engine.py`의 동명 딕셔너리와 동일 패턴).
"""

from dataclasses import dataclass, field

from engine.expectation_gap_engine import (
    cyclicality_score,
    erp_from_drs,
    leverage_score,
)

# 트래커 실측에서 도출한 임계값 (근거는 위 docstring)
DEFAULT_RISK_FREE_RATE = 0.0447          # 미국 10Y, 2026-07 기준
STRUCTURAL_DISCOUNT_MEDIAN = 0.101       # ledger 12건 실측 중앙값
MIN_REALISTIC_GROWTH = 0.08              # 저평가군 13/13이 이 위
MAX_IMPLIED_GROWTH = 0.055               # 과대평가군 18/18이 이 위(=하나도 통과 못함)

# ⚠️ v3.19 역검증(2026-07-26)에서 잡은 설계오류:
# 최초 구현은 순부채/EBITDA<=2.5, 최악YoY>=-5%를 **하드 필터**로 걸었는데,
# 이는 check_deceleration_double_count가 경고하는 것과 같은 유형의 **이중 반영**이었다.
# 레버리지와 경기민감도는 이미 DRS -> ERP -> r -> 내재성장률 경로로 반영되고 있어
# 별도 컷을 또 걸면 같은 증거로 두 번 페널티를 준다. 실제로 이 때문에 BRO(3.50배)와
# BSY(2.63배)가 탈락했는데 **둘 다 실전에서 저평가 판정이 난 종목**이었다
# (저평가군 13건의 DRS 실측범위가 21.4~67.75로 넓다는 사실 자체가 반증이다).
# 고친 방식: 하드 필터를 없애고, 관측가능한 값으로 DRS를 추정해 r에 반영한다.
# 추정 불가한 2개 항목(마진변동성/경쟁강도)만 실측 중앙값을 가정한다.
ASSUMED_MARGIN_VOLATILITY = 8.0          # ledger 실측 중앙값
ASSUMED_COMPETITION_INTENSITY = 12.0     # ledger 실측 중앙값
ASSUMED_REVENUE_VOLATILITY = 4.0         # ledger 실측 중앙값(안정성장주 기준)
ASSUMED_DEMAND_SENSITIVITY = 0.15        # ledger 실측 중앙값
# ledger 34종목 실측 중앙값(2026-08-22 계산) - scripts/daily_screen.py와
# engine/deep_screen.py가 공유한다. 원래 daily_screen.py에만 있었는데
# engine/deep_screen.py(v3.65)가 필요해지며 여기로 옮겼다 - engine/이
# scripts/를 참조하는 역방향 의존을 만들지 않기 위함(scripts/는 engine/을
# 참조하는 게 정상 방향이다).
DEFAULT_NDTE = 0.406
CAPEX_SPIKE_THRESHOLD = 0.03             # v3.7 growth_investment_capex_delta_threshold와 동일

# ======================================================================
# 외부검증 상태 (2026-08-23) - engine/expectation_gap_engine.py의 동명
# 딕셔너리와 같은 패턴. 근거 수준은 위 모듈 docstring "외부검증 완료" 절 참고,
# 전문은 reports/research/screening_criteria_external_2026-08-23.md.
# ======================================================================
VALIDATION_STATUS = {
    "min_realistic_growth": (
        "IMPLEMENTED_NOT_VALIDATED - 절대 하한(8%)에 대응하는 외부 학술 근거 "
        "없음. Greenblatt Magic Formula(성장 입력 없음)·Chan/Karceski/Lakonishok "
        "2003 JF(장기 성장은 우연 이상 지속 안 함)가 오히려 반대방향 - 단 이 "
        "스크리너는 예측력이 아니라 corpus 상관을 근거로 쓰므로 직접 반박은 아님"
    ),
    "max_implied_growth": (
        "IMPLEMENTED_NOT_VALIDATED - 절대 상한(5.5%)에 대응하는 외부 학술 근거 "
        "없음. 비교 대상인 implied_growth 자체의 아키텍처는 ECONOMICALLY_SUPPORTED "
        "(expectation_gap_engine.VALIDATION_STATUS['implied_growth'] 참고) - 그러나 "
        "그 지지는 5.5%라는 숫자를 정당화하지 않는다"
    ),
    "tier_thresholds": (
        "IMPLEMENTED_NOT_VALIDATED - ig<=0.0/ig<=0.0411 경계는 저평가군 내재성장률 "
        "중앙값에서 도출. GARP 실무관행의 PEG<1.0 '매력적' 구간과 경계값이 느슨하게 "
        "유사하나(IG/RG=0.6875) 지표 정의 자체가 달라(PEG는 P/E·EPS성장, IRS는 "
        "FCF수익률·DCF역산성장) 검증으로 쓰지 않는다 - 기록만"
    ),
    "open_source_survey": (
        "조사한 오픈소스 스크리닝 프로젝트(hjones20/fundamental-analysis, "
        "FinanceToolkit, StockScreener 등) 전부 절대 컷오프를 하드코딩하지 "
        "않음 - 임계값은 항상 사용자 파라미터. 이 스크리너의 '34~74종목 corpus "
        "근거'가 조사 범위 내에서는 오히려 더 투명한 편"
    ),
}


def estimate_drs(net_debt_to_ebitda: float, worst_yoy_revenue: float) -> float:
    """
    스크리닝 단계에서 구할 수 있는 값만으로 DRS를 추정한다.

    5개 항목 중 2개(레버리지·경기민감도)는 엔진 함수로 **실제 계산**하고,
    나머지 3개(매출변동성·마진변동성·경쟁강도)는 ledger 실측 중앙값을 가정한다.
    가중치는 전부 1.0(DRSInputs 기본값)이므로 단순평균 x 5.
    """
    components = [
        ASSUMED_REVENUE_VOLATILITY,
        ASSUMED_MARGIN_VOLATILITY,
        leverage_score(net_debt_to_ebitda),
        cyclicality_score(worst_yoy_revenue, ASSUMED_DEMAND_SENSITIVITY),
        ASSUMED_COMPETITION_INTENSITY,
    ]
    return (sum(components) / len(components)) * 5


def implied_growth_from_fcf_yield(fcf_yield: float, r: float) -> float:
    """FCF수익률 -> 내재성장률. 단일단계 Gordon의 정확한 항등식."""
    return (r - fcf_yield) / (1 + fcf_yield)


def required_fcf_yield(max_implied_growth: float, r: float) -> float:
    """목표 내재성장률 상한을 만족하는 FCF수익률 하한. 위 식의 역함수."""
    return (r - max_implied_growth) / (1 + max_implied_growth)


def assumed_r(drs: float, rf: float = DEFAULT_RISK_FREE_RATE) -> float:
    """DRS -> r. 엔진의 erp_from_drs()를 그대로 쓴다(규칙 중복 구현 금지)."""
    return rf + erp_from_drs(drs)


def required_min_cagr(min_realistic_growth: float = MIN_REALISTIC_GROWTH,
                      structural_discount: float = STRUCTURAL_DISCOUNT_MEDIAN) -> float:
    """목표 Realistic Growth를 만족하는 min(FCF CAGR, 매출 CAGR) 하한."""
    return min_realistic_growth / (1 - structural_discount)


@dataclass
class Candidate:
    """스크리닝 입력. 전부 공시/시세에서 직접 구할 수 있는 값만 받는다."""
    ticker: str
    name: str
    market_cap: float          # 시가총액(원 단위)
    fcf0: float                # 최근 회계연도 FCF = OCF - capex
    revenue_cagr_5y: float     # 소수
    fcf_cagr_5y: float         # 소수
    net_debt_to_ebitda: float
    worst_yoy_revenue: float   # 관측구간 최악 YoY 매출성장(소수, 역성장이면 음수)
    exchange: str = ""
    note: str = ""
    # v3.20: capex 억눌림 판별용(선택). 넣으면 재검토 플래그가 정밀해진다.
    capex_to_revenue_current: float = None
    capex_to_revenue_avg: float = None


@dataclass
class ScreenResult:
    candidate: Candidate
    fcf_yield: float
    implied_growth_est: float
    binding_cagr: float           # min(FCF CAGR, 매출 CAGR)
    realistic_growth_est: float
    expectation_gap_est: float
    passed: bool
    tier: str                     # "S" / "A" / "B" / "-"
    drs_est: float = float("nan")
    failures: list = field(default_factory=list)
    review_flags: list = field(default_factory=list)


def screen(c: Candidate, drs_override: float = None,
           rf: float = DEFAULT_RISK_FREE_RATE) -> ScreenResult:
    """
    후보 1건을 판정한다. 반환값의 implied/realistic growth는 **추정치**이며
    정식 값은 run_analysis()로만 확정된다.

    drs_override: 이미 DRS를 아는 경우(재검증 등)에만 지정. 평소엔 None으로 두고
    estimate_drs()가 관측값에서 추정하게 할 것.
    """
    failures = []

    if c.market_cap <= 0:
        raise ValueError(f"{c.ticker}: market_cap은 0보다 커야 함")

    drs = drs_override if drs_override is not None else estimate_drs(
        c.net_debt_to_ebitda, c.worst_yoy_revenue
    )
    r = assumed_r(drs, rf)

    if c.fcf0 <= 0:
        # FCF 적자면 Gordon/two-stage 둘 다 성립하지 않는다(엔진 v3.4/v3.5 가드와 동일)
        failures.append(f"FCF0가 {c.fcf0:,.0f}로 0 이하 - 모델 적용 불가(Model N/A)")
        return ScreenResult(c, float("nan"), float("nan"), float("nan"),
                            float("nan"), float("nan"), False, "-", drs, failures)

    fcf_yield = c.fcf0 / c.market_cap
    ig = implied_growth_from_fcf_yield(fcf_yield, r)
    binding = min(c.fcf_cagr_5y, c.revenue_cagr_5y)
    rg = binding * (1 - STRUCTURAL_DISCOUNT_MEDIAN)
    gap = rg - ig

    review_flags = []

    if ig > MAX_IMPLIED_GROWTH:
        failures.append(
            f"내재성장률 추정 {ig*100:.2f}% > {MAX_IMPLIED_GROWTH*100:.1f}% "
            f"(FCF수익률 {fcf_yield*100:.2f}%가 낮음, 필요 "
            f"{required_fcf_yield(MAX_IMPLIED_GROWTH, r)*100:.2f}%)"
        )
    if rg < MIN_REALISTIC_GROWTH:
        failures.append(
            f"현실적성장률 추정 {rg*100:.2f}% < {MIN_REALISTIC_GROWTH*100:.1f}% "
            f"(제약: {'FCF' if c.fcf_cagr_5y < c.revenue_cagr_5y else '매출'} "
            f"CAGR {binding*100:.2f}%, 필요 {required_min_cagr()*100:.2f}%)"
        )

    # ── v3.20: capex에 눌린 후보를 '단순 탈락'과 분리한다 ──────────────────
    # NVO 사례: 매출 CAGR 21.7%로 최상위권인데 FCF CAGR은 4.92%뿐이었다. capex가
    # 5년새 9.5배 폭증(GLP-1 증설)해 FCF를 눌렀기 때문이다. 이런 종목을 그냥
    # '성장 미달'로 버리면, capex가 실제로 '성장투자'인 경우(pipeline v3.20의
    # capex_classification="growth_investment")에 판정이 뒤집힐 후보를 놓친다.
    # 그래서 탈락시키되 재검토 대상으로 표시한다.
    # ⚠️ FCF CAGR이 음수면 이 플래그를 붙이지 않는다. capex에 '눌린' 것과 FCF가
    # 절대금액으로 줄어드는 것은 다른 문제이고, 후자는 capex를 성장투자로
    # 재분류해도 구제되지 않는다(UNH가 -5.18%로 잡혀 이 가드를 추가했다).
    rg_from_revenue = c.revenue_cagr_5y * (1 - STRUCTURAL_DISCOUNT_MEDIAN)
    fcf_binds = 0 < c.fcf_cagr_5y < c.revenue_cagr_5y
    if fcf_binds and rg < MIN_REALISTIC_GROWTH <= rg_from_revenue:
        msg = (
            f"[capex 재검토 대상] 매출 CAGR {c.revenue_cagr_5y*100:.2f}%만 보면 "
            f"현실적성장률 {rg_from_revenue*100:.2f}%로 통과하는데, FCF CAGR "
            f"{c.fcf_cagr_5y*100:.2f}%가 제약이 되어 탈락했다"
        )
        capex_known = (c.capex_to_revenue_current is not None
                       and c.capex_to_revenue_avg is not None)
        delta = (c.capex_to_revenue_current - c.capex_to_revenue_avg) if capex_known else None

        if capex_known and delta <= CAPEX_SPIKE_THRESHOLD:
            # capex를 확인해봤더니 급증이 아니었던 경우. 여기서 결론을 내려버린다 -
            # "확인할 것"으로 열어두면 이미 해소된 항목이 계속 재검토 대상에 남는다.
            # CI(0.64%->0.44%)와 PYPL(2.83%->2.53%)이 실제로 이 경우였다:
            # FCF 정체의 원인이 capex가 아니라 마진/운전자본이라는 뜻이다.
            msg += (f". 그러나 capex/매출이 평균 대비 {delta*100:+.1f}%p로 "
                    f"급증하지 않았다(v3.7 임계값 {CAPEX_SPIKE_THRESHOLD*100:.0f}%p 미만) "
                    f"→ capex에 눌린 게 아니라 마진/운전자본 문제이므로 "
                    f"margin_erosion으로 분류해야 하며, 재분류로 구제되지 않는다. 해소됨.")
            review_flags.append(msg)
        else:
            if capex_known:
                msg += (f". capex/매출이 평균 대비 {delta*100:+.1f}%p 급증 "
                        f"- v3.7 임계값({CAPEX_SPIKE_THRESHOLD*100:.0f}%p) 초과")
            else:
                msg += ". capex 시계열을 확보해 급증 여부를 확인할 것"

            # ⚠️ 재분류가 실제로 판정을 바꿀 수 있는지는 밸류에이션 통과 여부에 달렸다.
            # growth_investment 분류는 FCF **CAGR**만 상향조정할 뿐 FCF0(=내재성장률의
            # 입력)은 건드리지 않기 때문이다. 밸류에이션까지 탈락한 종목은 재분류해도
            # 여전히 탈락한다 - 이걸 구분하지 않으면 '판정이 바뀔 수 있다'가 거짓
            # 기대를 준다(GOOGL이 FCF수익률 1.87%로 이 경우에 해당).
            if ig <= MAX_IMPLIED_GROWTH:
                msg += (" → 밸류에이션은 이미 통과했으므로 growth_investment 재분류만으로 "
                        "통과 가능. 우선 확인 대상.")
            else:
                msg += (f" → 단, 내재성장률 {ig*100:.2f}%로 밸류에이션도 미달이라 "
                        f"재분류만으로는 통과 못 한다(재분류는 FCF CAGR만 올리고 FCF0는 "
                        f"그대로라 내재성장률이 안 변한다). 가격이 더 내려와야 함.")
            review_flags.append(msg)

    passed = not failures
    if not passed:
        tier = "-"
    elif ig <= 0.0:
        # ACGL/ADBE/TIGR/EVO 패턴 - 시장이 역성장을 가격에 반영한 상태
        tier = "S"
    elif ig <= 0.0411:  # 저평가군 내재성장률 중앙값
        tier = "A"
    else:
        tier = "B"

    return ScreenResult(c, fcf_yield, ig, binding, rg, gap, passed, tier, drs,
                        failures, review_flags)


def screen_all(candidates: list) -> list:
    """여러 후보를 판정하고 통과분을 Gap 추정치 내림차순으로 정렬해 반환."""
    results = [screen(c) for c in candidates]
    results.sort(key=lambda x: (not x.passed, -(x.expectation_gap_est
                                                if x.expectation_gap_est == x.expectation_gap_est
                                                else -99)))
    return results


def format_table(results: list) -> str:
    """결과를 사람이 읽는 표로."""
    lines = []
    head = (f"{'종목':10} {'등급':>4} {'FCF수익률':>10} {'내재성장(추정)':>14} "
            f"{'제약CAGR':>10} {'현실성장(추정)':>14} {'Gap(추정)':>11}")
    lines.append(head)
    lines.append("-" * len(head))
    for r in results:
        if not r.passed:
            continue
        c = r.candidate
        lines.append(
            f"{c.ticker:10} {r.tier:>4} {r.fcf_yield*100:9.2f}% "
            f"{r.implied_growth_est*100:13.2f}% {r.binding_cagr*100:9.2f}% "
            f"{r.realistic_growth_est*100:13.2f}% {r.expectation_gap_est*100:+10.2f}%p"
        )
    return "\n".join(lines)
