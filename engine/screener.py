"""
매수관점 후보 스크리너 (v3.19 신규, 2026-07-26)

왜 만들었나:
트래커 74건을 전수 분석하니 저평가/매수 판정군(13건)과 과대평가/회피군(18건)이
두 축으로 거의 완벽하게 갈렸다. 이 판별식을 사람의 감이 아니라 코드로 고정한다.

  실측 판별력 (트래커 전수, 2026-07-26):
    Realistic Growth >= 8%   : 저평가군 13/13 (100%)  vs 과대평가군  2/18 (11%)
    Implied Growth   <= 5.5% : 저평가군 11/13 ( 85%)  vs 과대평가군  0/18 ( 0%)
    둘 다 충족               : 저평가군 11/13 ( 85%)  vs 과대평가군  0/18 ( 0%)

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
    review_flags = []
    rg_from_revenue = c.revenue_cagr_5y * (1 - STRUCTURAL_DISCOUNT_MEDIAN)
    fcf_binds = 0 < c.fcf_cagr_5y < c.revenue_cagr_5y
    if fcf_binds and rg < MIN_REALISTIC_GROWTH <= rg_from_revenue:
        msg = (
            f"[capex 재검토 대상] 매출 CAGR {c.revenue_cagr_5y*100:.2f}%만 보면 "
            f"현실적성장률 {rg_from_revenue*100:.2f}%로 통과하는데, FCF CAGR "
            f"{c.fcf_cagr_5y*100:.2f}%가 제약이 되어 탈락했다"
        )
        if c.capex_to_revenue_current is not None and c.capex_to_revenue_avg is not None:
            delta = c.capex_to_revenue_current - c.capex_to_revenue_avg
            msg += (f". capex/매출이 평균 대비 {delta*100:+.1f}%p"
                    f"{' 급증' if delta > 0.03 else ''}")
            if delta > 0.03:
                msg += (" - v3.7 임계값(3%p) 초과이므로 growth_investment로 "
                        "분류되면 FCF CAGR이 상향조정되어 판정이 바뀔 수 있다")
        else:
            msg += ". capex 시계열을 확보해 급증 여부를 확인할 것"
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
