"""
자동 심층분석 (Deep Screen) — v3.65 신규, 2026-08-23.

## 왜 만들었나

`engine/screener.py`는 후보를 넓게 걸러내는 1차 필터다. 5개 관측값만 받고
DRS 5개 구성요소 중 3개(매출변동성·마진변동성·경쟁강도)를 corpus 중앙값으로
가정하며, 구조적할인율도 실측 대신 단일 상수(`STRUCTURAL_DISCOUNT_MEDIAN`)를
쓴다 - 스크리닝 단계에서는 그 이상의 데이터가 없기 때문이다.

그런데 하루 통과 후보는 보통 0~2종목뿐이다(스크리닝 문서 기록). 그 소수에
대해서는 **SEC에서 더 넓은 창(최대 11개년)을 가져오면 이미 검증된 engine/
공식 계산 경로를 그대로 돌릴 수 있다** - 매출변동성·마진변동성은 상수 대신
실제 3y/5y/10y 매출 CAGR과 실제 영업이익률 시계열에서 계산되고, 구조적
할인율도 `structural_discount_rate()`(2026-08-16 외부검증에서 trend_delta
메커니즘이 ECONOMICALLY_SUPPORTED로 승격된 바로 그 함수)를 그대로 부른다.

## 이것이 공식 분석(run_analysis 결과)이 아닌 이유 - 정직하게 못박는다

`AnalysisInputs`가 요구하는 것 중 **의도적으로 재현하지 않는 것**이 있다:

1. **`model_choice_reason`** - single_stage vs two_stage 선택. 2026-08-16
   모델선택 연구가 "이론 기준이 실제 선택을 설명하지 못한다"(구간 완전중첩)는
   것을 실증했고 규칙화를 REJECT했다. 그러니 여기서 규칙을 만드는 것도 같은
   이유로 하지 않는다 - **항상 single_stage(Gordon)만 계산**하고 그렇게
   명시한다.
2. **`competition_intensity`** - 경쟁강도는 재무제표에 없다. `screener.py`가
   이미 쓰는 `ASSUMED_COMPETITION_INTENSITY`(corpus 중앙값 12.0)를 그대로
   재사용한다. BSX 스크리너 거짓탈락 사건(실제값이 상수보다 낮아 판정이
   뒤집혔던 사례)이 이미 경고해뒀듯, 이 자리는 **정성조사 없이는 항상
   부정확할 수 있다.**
3. **`demand_sensitivity_pct`** - 마찬가지로 재무제표 밖의 정성적 판단이라
   `screener.py`의 `ASSUMED_DEMAND_SENSITIVITY`(0.15)를 그대로 쓴다.
4. **`net_debt_to_ebitda`** - 순부채·EBITDA를 만들 SEC 태그가 아직
   `engine/data/providers/sec.py`의 `METRIC_TAGS`에 등록돼 있지 않다(이번에
   추가하지 않았다 - 실제로 필요해진 사례가 하나뿐이라 근거가 약하다,
   Simplicity First). `screener.py`가 이미 쓰는 corpus 중앙값(0.406)을
   그대로 쓴다.

즉 이 모듈은 **"재무제표만으로 객관적으로 계산 가능한 부분은 공식 엔진
함수 그대로, 재무제표 밖의 판단이 필요한 부분(경쟁강도·수요민감도·순부채·
모델선택)은 corpus 중앙값으로 고정"**한 결과물이다 - `screener.py`가 이미
확립한 "추정 불가한 항목만 가정한다"는 설계를 그대로 이어받아 범위만
넓혔을 뿐, 새 방법론은 0줄이다(전부 기존 검증된 함수 재사용).

## 새로 계산하는 로직 (Simplicity First 검토 대상은 이것뿐)

CAGR 윈도우 산출(`_window_cagr`)과 결과 조립(`deep_screen`) 자체는 새
코드지만, 안에서 부르는 함수는 전부 기존 것이다:
`revenue_volatility_score`·`margin_volatility_score`·`leverage_score`·
`cyclicality_score`·`DRSInputs`·`erp_from_drs`·`classify_lynch_type`·
`structural_discount_rate`·`realistic_growth_estimate`·`judgment_from_gap`
(`engine/expectation_gap_engine.py`) + `implied_growth_from_fcf_yield`
(`engine/screener.py`).

## 단위 함정 주의 (CLAUDE.md 단위 규약과 동일)

`market_cap`은 `implied_growth_from_fcf_yield`에는 **원화(달러) 단위
그대로**, `structural_discount_rate`/`classify_lynch_type`에는 **10억
단위**로 나눠 넣어야 한다 - 이 프로젝트가 반복 경계해온 함정이라 테스트로
직접 고정한다.
"""

from dataclasses import dataclass, field

from engine.expectation_gap_engine import (
    DRSInputs,
    classify_lynch_type,
    cyclicality_score,
    erp_from_drs,
    judgment_from_gap,
    leverage_score,
    margin_volatility_score,
    operating_margin_from_series,
    realistic_growth_estimate,
    revenue_volatility_score,
    structural_discount_rate,
)
from engine.screener import (
    ASSUMED_COMPETITION_INTENSITY,
    ASSUMED_DEMAND_SENSITIVITY,
    DEFAULT_NDTE,
    DEFAULT_RISK_FREE_RATE,
    implied_growth_from_fcf_yield,
)


def _window_cagr(series: dict, final_year: int, span: int):
    """
    series[final_year - span] -> series[final_year] CAGR. 시작연도가 없거나
    시작·끝값이 0 이하면(v3.19 가드와 동일 이유 - 복소수 함정) None.
    """
    base_year = final_year - span
    if base_year not in series or final_year not in series:
        return None
    start, end = series[base_year], series[final_year]
    if start <= 0 or end <= 0:
        return None
    return (end / start) ** (1 / span) - 1


@dataclass
class DeepScreenResult:
    ticker: str
    final_year: int
    n_years_available: int
    revenue_cagr_3y: float
    revenue_cagr_5y: float
    revenue_cagr_10y: float          # None이면 5y로 대체됐음(아래 참고)
    revenue_cagr_10y_is_fallback: bool
    fcf_cagr_5y: float
    fcf0: float
    worst_yoy_revenue: float
    op_margins: list
    drs_components: dict
    drs: float
    r: float
    lynch_type: str
    lynch_note: str
    structural_discount_pct: float
    realistic_growth: float
    growth_breakdown: dict
    fcf_yield: float
    implied_growth: float            # single_stage(Gordon)만 - 위 docstring 참고
    gap: float
    judgment: str
    assumed_inputs: dict = field(default_factory=dict)
    data_limitations: list = field(default_factory=list)


def deep_screen(ticker: str, series: dict, market_cap: float,
                net_debt_to_ebitda: float = None,
                rf: float = DEFAULT_RISK_FREE_RATE) -> DeepScreenResult:
    """
    다년 원자료(daily_screen.fetch_deep_series 등에서 수집) -> 심층 추정.

    series: {"revenue_by_year": {y: v}, "operating_cashflow_by_year": {...},
             "capex_by_year": {...}, "operating_income_by_year": {...}}
    net_debt_to_ebitda: None이면 screener.py의 corpus 중앙값으로 대체(명시적으로 기록됨).
    """
    data_limitations = []
    assumed_inputs = {}

    rev = series["revenue_by_year"]
    ocf = series["operating_cashflow_by_year"]
    capex = series["capex_by_year"]
    op_income = series.get("operating_income_by_year", {})

    common_years = sorted(set(rev) & set(ocf) & set(capex))
    if len(common_years) < 2:
        raise ValueError(
            f"{ticker}: 매출·OCF·capex 공통 연도가 {len(common_years)}개뿐 - "
            f"심층분석에 최소 2개년 필요")
    final_year = common_years[-1]
    fcf_by_year = {y: ocf[y] - capex[y] for y in common_years}

    # ── 성장률(전부 실측, 가정 없음) ──────────────────────────────────
    rev_cagr_3y = _window_cagr(rev, final_year, 3)
    rev_cagr_5y = _window_cagr(rev, final_year, 5)
    rev_cagr_10y = _window_cagr(rev, final_year, 10)
    revenue_cagr_10y_is_fallback = False
    if rev_cagr_10y is None and rev_cagr_5y is not None:
        # v3.25가 확립한 정확한 대체 규약(3y가 아니라 5y로 대체) 그대로.
        revenue_cagr_10y_is_fallback = True
        data_limitations.append(
            f"10년 CAGR 산출 불가({len(common_years)}개 연도만 확보) - "
            f"5년 CAGR({rev_cagr_5y*100:.2f}%)로 대체(v3.25 규약과 동일). "
            f"revenue_volatility·구조적할인율 편차가 실제보다 축소됐을 수 있음")
    rev_cagr_10y_input = rev_cagr_10y if rev_cagr_10y is not None else rev_cagr_5y

    if rev_cagr_5y is None:
        raise ValueError(
            f"{ticker}: 5년 매출 CAGR을 계산할 수 없음(기준연도 매출 <= 0 또는 "
            f"5년 전 데이터 없음) - 심층분석 프레임 부적합(PODD/ONON 유형)")

    fcf_cagr_5y = _window_cagr(fcf_by_year, final_year, 5)
    fcf0 = fcf_by_year[final_year]
    if fcf_cagr_5y is None:
        data_limitations.append(
            f"5년 FCF CAGR 계산 불가(기준연도 또는 최종연도 FCF <= 0) - "
            f"realistic_growth_estimate가 매출 가중평균만으로 계산됨")

    worst_yoy = min(
        rev[common_years[i]] / rev[common_years[i - 1]] - 1
        for i in range(1, len(common_years))
        if rev[common_years[i - 1]] != 0
    )

    # pipeline.py의 margin_years 기본 규약과 동일: 최근 5개년만 쓴다
    # (`inputs.margin_years = sorted(revenue_by_year)[-5:]`). 확보 가능한
    # 전 구간을 쓰면 2020년 코로나 저마진 같은 오래된 이상치가 표준편차를
    # 부풀려 margin_volatility가 실제보다 나쁘게 나온다 - BSX 교차검증에서
    # 실측(전구간 stdev 3.5%p vs 최근5y stdev 1.8%p, 등급 8.0 vs 4.0)으로
    # 확인했다.
    op_margin_years = sorted(y for y in common_years if y in op_income)[-5:]
    op_margins = None
    if len(op_margin_years) >= 2:
        op_margins = operating_margin_from_series(
            [op_income[y] for y in op_margin_years],
            [rev[y] for y in op_margin_years],
        )
    else:
        data_limitations.append(
            f"영업이익 확보 연도가 {len(op_margin_years)}개뿐 - margin_volatility "
            f"계산 불가, ASSUMED_MARGIN_VOLATILITY 대신 이 컴포넌트를 제외")

    # ── DRS: 실측 가능한 항목은 실측, 재무제표 밖은 corpus 중앙값(명시) ──
    if net_debt_to_ebitda is None:
        net_debt_to_ebitda = DEFAULT_NDTE
        assumed_inputs["net_debt_to_ebitda"] = (
            f"{DEFAULT_NDTE} (corpus 중앙값 - SEC 태그 미등록으로 실측 불가)")

    cyclicality = cyclicality_score(worst_yoy, ASSUMED_DEMAND_SENSITIVITY)
    assumed_inputs["demand_sensitivity_pct"] = (
        f"{ASSUMED_DEMAND_SENSITIVITY} (corpus 중앙값 - 정성판단 불가)")
    assumed_inputs["competition_intensity"] = (
        f"{ASSUMED_COMPETITION_INTENSITY} (corpus 중앙값 - 정성판단 불가, "
        f"BSX 거짓탈락 사례처럼 이 값이 실제와 크게 다를 수 있음)")

    drs_components = {
        "revenue_volatility": revenue_volatility_score(
            rev_cagr_3y if rev_cagr_3y is not None else rev_cagr_5y,
            rev_cagr_5y, rev_cagr_10y_input),
        "leverage": leverage_score(net_debt_to_ebitda),
        "cyclicality": cyclicality,
        "competition_intensity": ASSUMED_COMPETITION_INTENSITY,
    }
    excluded_reasons = {}
    if op_margins is not None:
        drs_components["margin_volatility"] = margin_volatility_score(op_margins)
    else:
        drs_components["margin_volatility"] = None
        excluded_reasons["margin_volatility"] = "영업이익 데이터 부족(위 data_limitations 참고)"
    if rev_cagr_3y is None:
        data_limitations.append(
            "3년 매출 CAGR 미확보 - revenue_volatility 계산에 5년 값으로 대체")

    drs = DRSInputs(**drs_components, excluded_reasons=excluded_reasons).score()
    r = rf + erp_from_drs(drs)

    # ── 성장분류·구조적할인·Realistic Growth (전부 공식 엔진 함수) ──────
    market_cap_b = market_cap / 1e9
    lynch_type, lynch_note = classify_lynch_type(
        rev_cagr_5y, drs_components["cyclicality"], market_cap_b)
    structural_discount_pct = structural_discount_rate(
        rev_cagr_3y if rev_cagr_3y is not None else rev_cagr_5y,
        rev_cagr_10y_input, market_cap_b)
    realistic_growth, growth_breakdown = realistic_growth_estimate(
        revenue_cagr_3y=rev_cagr_3y, revenue_cagr_5y=rev_cagr_5y,
        revenue_cagr_10y=rev_cagr_10y_input, fcf_cagr_5y=fcf_cagr_5y,
        structural_discount_pct=structural_discount_pct, lynch_type=lynch_type,
    )
    if growth_breakdown.get("cap_applied"):
        data_limitations.append(
            f"[성장상한 바인딩] {growth_breakdown['cap_applied']} - 성장분석 결과가 "
            f"결과에 기여하지 못하고 있음(v3.24 M-1과 동일 경고)")

    # ── 밸류에이션: single_stage(Gordon)만 - 위 docstring 참고 ──────────
    fcf_yield = fcf0 / market_cap if market_cap > 0 else None
    if fcf0 <= 0:
        raise ValueError(
            f"{ticker}: FCF0가 {fcf0:,.0f}로 0 이하 - Gordon 모형 적용 불가(Model N/A)")
    implied_growth = implied_growth_from_fcf_yield(fcf_yield, r)
    gap = realistic_growth - implied_growth
    judgment = judgment_from_gap(gap)

    assumed_inputs["model_used"] = (
        "single_stage(Gordon) 고정 - 모델선택 규칙화는 2026-08-16 연구에서 "
        "REJECT됐음(구간 완전중첩, 규칙 불가)")

    return DeepScreenResult(
        ticker=ticker, final_year=final_year, n_years_available=len(common_years),
        revenue_cagr_3y=rev_cagr_3y, revenue_cagr_5y=rev_cagr_5y,
        revenue_cagr_10y=rev_cagr_10y,
        revenue_cagr_10y_is_fallback=revenue_cagr_10y_is_fallback,
        fcf_cagr_5y=fcf_cagr_5y, fcf0=fcf0, worst_yoy_revenue=worst_yoy,
        op_margins=op_margins, drs_components=drs_components, drs=drs, r=r,
        lynch_type=lynch_type, lynch_note=lynch_note,
        structural_discount_pct=structural_discount_pct,
        realistic_growth=realistic_growth, growth_breakdown=growth_breakdown,
        fcf_yield=fcf_yield, implied_growth=implied_growth, gap=gap,
        judgment=judgment, assumed_inputs=assumed_inputs,
        data_limitations=data_limitations,
    )
