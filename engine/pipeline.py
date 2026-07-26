"""
Analysis Pipeline (v3.19 신규)

왜 만들었나 (2026-07-25 감사 결과):
지금까지 모든 종목 분석은 세션마다 파이썬 코드를 손으로 다시 배선해서 돌렸다.
그 결과 반복된 사고가 셋 있다.

1. **단위 사고**: rar()에 소수를 넣어 100배 틀린 값이 4종목에 기록됨(v3.19에서
   가드 추가). 체인을 손으로 이을 때마다 재발 위험이 있다.
2. **계산 유실**: 큐22(Cadence)는 "엔진계산은 했다"는 기록만 남고 입력값·중간값이
   전부 사라져 전면 재수행해야 했다. CDNS/MNST/PH의 과거 RAR과 대조검증도
   불가능했다.
3. **모델선택 실수**: PH를 single_stage로 계산해 Gap이 -1.48%p(적정가)로 나왔으나
   실제 확립된 컨벤션은 two_stage(-8.59%p, 과대평가)였다. 기존 기록과 우연히
   비교해봐서 잡았을 뿐, 코드가 잡아준 게 아니다.

이 모듈은 셋 다 구조적으로 막는다:
- 체인을 한 곳에서만 배선한다(단위 실수 원천 차단)
- 입력값·중간값·최종값을 전부 ledger JSON으로 저장한다(재현·대조검증 가능)
- 두 모델을 항상 같이 계산해 괴리가 크면 경고하고, 선택 사유를 필수로 받는다
"""

import json
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone

from engine.expectation_gap_engine import (
    DRSInputs,
    LYNCH_TYPE_CAPS,
    bull_bear_base_growth_rates,
    capped_n,
    check_deceleration_double_count,
    check_stalwart_two_stage_bias,
    classify_lynch_type,
    competition_intensity_score,
    confidence_score,
    cyclicality_score,
    default_terminal_growth,
    erp_from_drs,
    expectation_gap_sensitivity_check,
    expected_return,
    implied_growth_single_stage,
    implied_growth_two_stage,
    leverage_score,
    margin_volatility_score,
    rar_from_decimal_return,
    realistic_growth_estimate,
    revenue_volatility_score,
    scenario_probabilities_from_drs,
    scenario_return_from_growth,
    structural_discount_rate,
)

MODEL_DIVERGENCE_WARNING_THRESHOLD = 0.03  # 3%p 이상 벌어지면 경고


def compare_implied_growth_models(
    market_cap: float,
    fcf0: float,
    r: float,
    n: int,
    g_terminal: float,
) -> dict:
    """
    v3.19 신규: single_stage와 two_stage를 **항상 둘 다** 계산해 비교한다.

    왜 강제 비교인가: 어느 모델이 옳은지 판정하는 확립된 규칙이 이 프로젝트에
    문서화된 적이 없다(GOOGL은 two_stage 오사용이 v3.11 감사에서 발견돼
    single_stage로 정정하며 판정 자체가 뒤집혔고, PH는 반대로 two_stage가
    관행이었다). 규칙이 없는 상태에서 코드가 임의로 하나를 고르면 그게 곧
    근거 없는 자동화다. 그래서 고르지 않고, **둘의 괴리를 드러내서 분석자가
    의식적으로 선택하고 사유를 남기도록** 만든다.

    반환값: {single_stage, two_stage, divergence, divergence_warning}
    두 모델 중 하나가 계산 불가면(Model N/A) 해당 값은 None, error에 사유.
    """
    result = {"single_stage": None, "two_stage": None, "errors": {}}

    try:
        result["single_stage"] = implied_growth_single_stage(market_cap, fcf0, r)
    except ValueError as e:
        result["errors"]["single_stage"] = str(e)

    try:
        g2, _, _ = implied_growth_two_stage(market_cap, fcf0, r, n, g_terminal)
        result["two_stage"] = g2
    except (ValueError, RuntimeError) as e:
        result["errors"]["two_stage"] = str(e)

    if result["single_stage"] is not None and result["two_stage"] is not None:
        divergence = abs(result["single_stage"] - result["two_stage"])
        result["divergence"] = divergence
        if divergence >= MODEL_DIVERGENCE_WARNING_THRESHOLD:
            result["divergence_warning"] = (
                f"[모델 괴리 경고] single_stage({result['single_stage']*100:.2f}%)와 "
                f"two_stage({result['two_stage']*100:.2f}%)가 {divergence*100:.2f}%p 벌어져 있다. "
                f"어느 쪽을 쓰느냐에 따라 Expectation Gap 판정이 바뀔 수 있으므로, "
                f"model_choice_reason에 선택 근거를 반드시 남길 것(v3.19). "
                f"과거 같은 종목 기록이 있으면 그 내재성장률과 대조해볼 것 - "
                f"PH가 이 방법으로 모델선택 실수를 잡은 사례다(2026-07-25)."
            )
        else:
            result["divergence_warning"] = None
    else:
        result["divergence"] = None
        result["divergence_warning"] = None

    return result


@dataclass
class AnalysisInputs:
    """
    한 종목 분석에 필요한 모든 입력. 여기 담긴 값만으로 결과가 100% 재현되어야 한다.

    재무 시계열은 {회계연도: 값} 딕셔너리로 받는다(연도 정렬은 내부에서 처리).
    market_cap/net_debt/ebitda/fcf 등 금액은 **원 단위 그대로**(예: 92_952_756_000).
    """

    ticker: str
    company_name: str

    revenue_by_year: dict
    operating_income_by_year: dict
    operating_cashflow_by_year: dict
    capex_by_year: dict

    market_cap: float
    net_debt: float
    ebitda: float
    risk_free_rate: float

    # 주관적 입력 - 반드시 근거를 함께 남길 것(v3.19: 사유 필수화)
    competitor_threat_weights: list
    market_share_trend_pp_per_year: float
    active_antitrust_or_regulatory_case: bool
    demand_sensitivity_pct: float
    subjective_input_basis: str

    # 모델 선택 - v3.19부터 명시 필수
    model_used: str  # "single_stage" | "two_stage"
    model_choice_reason: str

    margin_years: list = None
    n_requested: int = 12
    data_completeness_pct: float = 0.9
    lynch_type_override: str = None
    lynch_type_override_reason: str = None
    data_sources: list = field(default_factory=list)

    def __post_init__(self):
        if self.model_used not in ("single_stage", "two_stage"):
            raise ValueError('model_used는 "single_stage" 또는 "two_stage"여야 함')
        if not self.model_choice_reason or not self.model_choice_reason.strip():
            raise ValueError(
                "model_choice_reason 필수(v3.19): 어느 모델을 왜 골랐는지 남기지 않으면 "
                "다음 세션이 PH처럼 반대 모델로 계산해 판정이 뒤집힐 수 있다."
            )
        if not self.subjective_input_basis or not self.subjective_input_basis.strip():
            raise ValueError(
                "subjective_input_basis 필수(v3.19): competitor_threat_weights/"
                "market_share_trend/demand_sensitivity는 [추정치]이므로 근거를 "
                "남기지 않으면 종목간 DRS 비교가 불가능해진다."
            )
        if self.lynch_type_override is not None and not self.lynch_type_override_reason:
            raise ValueError("lynch_type을 수동 오버라이드하려면 사유 필수")

        # ⚠️ v3.19에서 실제로 겪은 사고(2026-07-25 BRO 재검증): 데이터 소스마다
        # capex 부호 규약이 다르다. Alpha Vantage는 양수(지출액), Fiscal.ai는
        # 음수(현금유출)로 준다. 파이프라인은 fcf = ocf - capex 이므로 음수를 그대로
        # 넣으면 capex를 빼는 대신 **더해서** FCF가 과대계상된다(BRO FY25 기준
        # 1,382M -> 1,518M, +9.8%). RAR 100배 사고와 같은 유형의 조용한 단위 사고라
        # 코드로 막는다.
        negative_capex = {y: v for y, v in self.capex_by_year.items() if v < 0}
        if negative_capex:
            raise ValueError(
                f"capex에 음수 값이 있다: {negative_capex}. capex는 **지출액(양수)**으로 "
                f"넣어야 한다(fcf = ocf - capex). 데이터 소스가 현금유출을 음수로 주면"
                f"(Fiscal.ai 등) abs()로 부호를 정규화할 것. 그대로 넣으면 FCF가 "
                f"capex의 2배만큼 과대계상된다(v3.19 가드)."
            )
        if self.margin_years is None:
            self.margin_years = sorted(self.revenue_by_year)[-5:]


def _cagr(start: float, end: float, years: int, label: str = "") -> float:
    """
    CAGR 계산. start<=0이면 계산이 성립하지 않으므로 예외를 던진다.

    ⚠️ v3.19 자체감사에서 발견: 가드가 없으면 start가 음수일 때 파이썬이
    **복소수를 조용히 반환**한다((100/-50)**(1/5) -> -0.07+0.68j). 그 복소수가
    DRS/성장률 계산을 타고 흘러 들어가면 어디서 틀렸는지 추적조차 어렵다.
    FCF 적자 연도가 기준연도가 되는 경우(INTC/BYND 등)에 실제로 발생 가능하다.
    """
    if start <= 0:
        raise ValueError(
            f"CAGR 계산 불가{f'({label})' if label else ''}: 시작값이 {start:,.0f}로 0 이하다. "
            f"FCF 적자 등으로 기준연도가 음수면 CAGR은 정의되지 않는다(v3.19 가드). "
            f"해당 지표를 제외하거나 [Model Not Applicable] 처리할 것."
        )
    if end <= 0:
        raise ValueError(
            f"CAGR 계산 불가{f'({label})' if label else ''}: 종료값이 {end:,.0f}로 0 이하다. "
            f"흑자->적자 전환은 CAGR로 표현할 수 없다(v3.19 가드)."
        )
    return (end / start) ** (1 / years) - 1


def run_analysis(inputs: AnalysisInputs) -> dict:
    """
    전체 파이프라인을 한 번에 실행하고 모든 중간값을 담은 dict를 반환한다.

    단위 처리는 전부 여기서 책임진다(호출부가 소수/퍼센트를 헷갈릴 여지 없음):
    - 성장률·수익률은 전부 소수로 흐른다
    - rar만 퍼센트 규약이므로 rar_from_decimal_return()으로 안전하게 변환
    - structural_discount_rate/classify_lynch_type에는 10억 단위 시총을 넘긴다
    """
    years = sorted(inputs.revenue_by_year)
    rev = inputs.revenue_by_year
    fcf = {
        y: inputs.operating_cashflow_by_year[y] - inputs.capex_by_year[y] for y in years
    }

    if len(years) < 6:
        raise ValueError(
            f"재무 시계열이 {len(years)}개 연도뿐이라 5년 CAGR도 계산할 수 없다. "
            f"최소 6개 연도가 필요하다."
        )

    data_limitations = []

    rev_cagr_3y = _cagr(rev[years[-4]], rev[years[-1]], 3, "revenue 3y")
    rev_cagr_5y = _cagr(rev[years[-6]], rev[years[-1]], 5, "revenue 5y")
    if len(years) >= 11:
        rev_cagr_10y = _cagr(rev[years[-11]], rev[years[-1]], 10, "revenue 10y")
    else:
        # ⚠️ v3.19 자체감사에서 발견: 예전 구현은 10년치가 없으면 아무 기록 없이
        # 5y 값을 10y 자리에 끼워 넣었다. 그러면 revenue_volatility_score가 보는
        # 표준편차가 인위적으로 줄어 DRS가 실제보다 낮게 나오고, 아무도 그 사실을
        # 알 수 없다. 대체는 유지하되 반드시 명시적으로 기록한다.
        rev_cagr_10y = None
        data_limitations.append(
            f"10년 CAGR 산출 불가({len(years)}개 연도만 확보). revenue_volatility_score와 "
            f"structural_discount_rate에 5년 CAGR({rev_cagr_5y*100:.2f}%)을 대체 입력했다. "
            f"3/5/10y 편차가 인위적으로 축소되므로 DRS의 revenue_volatility 항목과 "
            f"구조적 할인율이 모두 실제보다 낮게(=관대하게) 나왔을 수 있다."
        )

    fcf_cagr_5y = _cagr(fcf[years[-6]], fcf[years[-1]], 5, "FCF 5y")
    fcf0 = fcf[years[-1]]

    yoy = [(years[i], rev[years[i]] / rev[years[i - 1]] - 1) for i in range(1, len(years))]
    worst_yoy = min(g for _, g in yoy)
    worst_year = [y for y, g in yoy if g == worst_yoy][0]

    op_margins = [
        inputs.operating_income_by_year[y] / rev[y] for y in inputs.margin_years
    ]
    net_debt_to_ebitda = inputs.net_debt / inputs.ebitda

    drs_components = {
        "revenue_volatility": revenue_volatility_score(
            rev_cagr_3y, rev_cagr_5y, rev_cagr_10y if rev_cagr_10y is not None else rev_cagr_5y
        ),
        "margin_volatility": margin_volatility_score(op_margins),
        "leverage": leverage_score(net_debt_to_ebitda),
        "cyclicality": cyclicality_score(worst_yoy, inputs.demand_sensitivity_pct),
        "competition_intensity": competition_intensity_score(
            inputs.competitor_threat_weights,
            inputs.market_share_trend_pp_per_year,
            inputs.active_antitrust_or_regulatory_case,
        ),
    }
    drs = DRSInputs(**drs_components).score()

    market_cap_b = inputs.market_cap / 1e9
    auto_lynch_type, lynch_note = classify_lynch_type(
        rev_cagr_5y, drs_components["cyclicality"], market_cap_b
    )
    lynch_type = inputs.lynch_type_override or auto_lynch_type

    structural_discount = structural_discount_rate(
        rev_cagr_3y,
        rev_cagr_10y if rev_cagr_10y is not None else rev_cagr_3y,
        market_cap_b,
    )

    # ⚠️ v3.19 전면점검에서 발견(2026-07-26): check_deceleration_double_count()는
    # v3.8부터 엔진에 있었지만 pipeline.py가 만들어진 이래 한 번도 import되지
    # 않아 실행 경로에서 호출된 적이 없었다("손배선 대신 pipeline.py를 쓰라"는
    # 원칙이 있어도 pipeline.py 자체가 엔진 안전장치를 빠뜨리면 무력화된다).
    # "하향 오버라이드"는 lynch_type_override의 성장상한(g_max)이 자동분류보다
    # 낮은 경우로 기계적으로 정의한다(주관적 판단 불필요, LYNCH_TYPE_CAPS만 비교).
    lynch_type_overridden_down = (
        inputs.lynch_type_override is not None
        and LYNCH_TYPE_CAPS[lynch_type][1] < LYNCH_TYPE_CAPS[auto_lynch_type][1]
    )
    _, double_count_warning = check_deceleration_double_count(
        structural_discount, lynch_type_overridden_down
    )
    if double_count_warning:
        data_limitations.append(double_count_warning)

    realistic_growth, growth_breakdown = realistic_growth_estimate(
        revenue_cagr_3y=rev_cagr_3y,
        revenue_cagr_5y=rev_cagr_5y,
        revenue_cagr_10y=rev_cagr_10y,
        fcf_cagr_5y=fcf_cagr_5y,
        structural_discount_pct=structural_discount,
        lynch_type=lynch_type,
    )

    erp = erp_from_drs(drs)
    r = inputs.risk_free_rate + erp
    n = capped_n(inputs.n_requested)
    g_terminal = default_terminal_growth(inputs.risk_free_rate)

    models = compare_implied_growth_models(inputs.market_cap, fcf0, r, n, g_terminal)
    if models.get("divergence_warning"):
        data_limitations.append(models["divergence_warning"])
    implied_growth = models[inputs.model_used]
    if implied_growth is None:
        raise ValueError(
            f"선택한 모델({inputs.model_used})로 Implied Growth 계산 불가: "
            f"{models['errors'].get(inputs.model_used)} -> [Model Not Applicable] 처리할 것"
        )
    gap = realistic_growth - implied_growth

    growth_rates = bull_bear_base_growth_rates(realistic_growth, lynch_type)
    scenario_returns = {
        key: scenario_return_from_growth(
            inputs.market_cap, fcf0, r, n, g_terminal, growth_rates[g_key]
        )
        for key, g_key in [("bull", "g_bull"), ("base", "g_base"), ("bear", "g_bear")]
    }
    p_bull, p_base, p_bear, prob_rationale = scenario_probabilities_from_drs(drs)
    er_decimal = expected_return(
        p_bull, scenario_returns["bull"],
        p_base, scenario_returns["base"],
        p_bear, scenario_returns["bear"],
    )
    # ⚠️ 여기가 v3.19 사고 지점. 반드시 decimal 전용 함수를 쓴다.
    rar_value = rar_from_decimal_return(er_decimal, drs)

    # ⚠️ 여기에 inputs.model_used를 넘기면 안 된다(v3.19 골든테스트가 잡아낸 버그).
    # RAR은 scenario_return_from_growth() -> _two_stage_market_cap() 경로라
    # **Section 5에서 single_stage를 썼더라도 항상 two_stage로 산출**된다.
    # v3.13 구조적 편향은 그 two_stage 경로의 min_spread 가드에서 나오는 것이므로,
    # Section 5 모델이 아니라 시나리오 모델(=항상 two_stage)로 판정해야 한다.
    SCENARIO_MODEL = "two_stage"
    bias_flag, bias_note = check_stalwart_two_stage_bias(
        lynch_type, rar_value, SCENARIO_MODEL
    )
    # ⚠️ v3.19 근본수정(2026-07-26): 2026-07-25에는 이 함수가 항상 two_stage로만
    # 판정해 Section 5가 single_stage를 쓴 경우 서로 다른 모델을 비교하는
    # 오류가 있었다(WCN/WM/IDXX에서 발견, 당시엔 [강건성점검 해석주의] 경고문으로
    # 임시 우회). 이제 engine.expectation_gap_engine.expectation_gap_sensitivity_check가
    # model_used를 받으므로, Section 5가 실제로 쓴 모델을 그대로 넘겨 같은 모델끼리
    # 비교되도록 근본 수정했다. 이전 경고문 우회책은 더 이상 필요 없어 제거함.
    sensitivity = expectation_gap_sensitivity_check(
        inputs.market_cap, fcf0, r, 0.05, inputs.risk_free_rate,
        realistic_growth, n, g_terminal,
        model_used=inputs.model_used,
    )
    confidence = confidence_score(
        sensitivity_check_result=sensitivity,
        gap=gap,
        rar=rar_value,
        data_completeness_pct=inputs.data_completeness_pct,
        lynch_type_cap_applied=(growth_breakdown["cap_applied"] is not None),
        stalwart_two_stage_bias_flagged=bias_flag,
    )

    if gap >= 0.05:
        judgment = "저평가 가능성"
    elif gap <= -0.05:
        judgment = "과대평가 가능성"
    else:
        judgment = "적정가/경계선"

    return {
        "meta": {
            "ticker": inputs.ticker,
            "company_name": inputs.company_name,
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
            "engine_version": "v3.19",
            "data_sources": inputs.data_sources,
        },
        "data_limitations": data_limitations,
        "inputs": asdict(inputs),
        "derived": {
            "revenue_cagr_3y": rev_cagr_3y,
            "revenue_cagr_5y": rev_cagr_5y,
            "revenue_cagr_10y": rev_cagr_10y,
            "fcf_cagr_5y": fcf_cagr_5y,
            "fcf0": fcf0,
            "fcf_by_year": fcf,
            "worst_yoy_revenue_growth": worst_yoy,
            "worst_yoy_year": worst_year,
            "operating_margins": op_margins,
            "net_debt_to_ebitda": net_debt_to_ebitda,
        },
        "drs": {"components": drs_components, "score": drs},
        "lynch": {
            "auto_classified": auto_lynch_type,
            "auto_note": lynch_note,
            "used": lynch_type,
            "override_reason": inputs.lynch_type_override_reason,
            "overridden_down": lynch_type_overridden_down,
        },
        "discount_rate": {"rf": inputs.risk_free_rate, "erp": erp, "r": r,
                          "n": n, "g_terminal": g_terminal},
        "growth": {
            "structural_discount_pct": structural_discount,
            "realistic_growth": realistic_growth,
            "breakdown": growth_breakdown,
        },
        "implied_growth": {
            "models": models,
            "model_used": inputs.model_used,
            "model_choice_reason": inputs.model_choice_reason,
            "value": implied_growth,
        },
        "expectation_gap": gap,
        "scenarios": {
            "growth_rates": growth_rates,
            "returns": scenario_returns,
            "probabilities": {"bull": p_bull, "base": p_base, "bear": p_bear},
            "probability_rationale": prob_rationale,
            "expected_return_decimal": er_decimal,
        },
        "rar": rar_value,
        "stalwart_bias": {"flagged": bias_flag, "note": bias_note},
        "sensitivity_check": sensitivity,
        "confidence": confidence,
        "judgment": judgment,
    }


def cross_check_prior_record(result: dict, prior: dict) -> list:
    """
    v3.19 신규: 새로 계산한 결과를 **과거 기록과 자동 대조**한다.

    왜 코드로 넣는가: "기존 기록이 있으면 대조하라"는 규칙을 문서로만 두면
    지켜지지 않는다는 걸 이 프로젝트가 세 번 겪었다(self_check, confidence_score,
    claim/lock 모두 문서에만 있다가 무력화됐다). PH 모델선택 실수도 사람이
    우연히 대조해서 잡았을 뿐이다.

    prior: 트래커에 남아있는 과거 값 {"rar":..., "drs":..., "gap":...,
           "implied_growth":..., "engine_version":..., "analyzed_at":...}
           (모르는 항목은 생략 가능)

    반환값: 경고 문자열 리스트(문제 없으면 빈 리스트)
    """
    warnings = []

    prior_rar, new_rar = prior.get("rar"), result["rar"]
    if prior_rar is not None and new_rar and abs(new_rar) > 1e-9:
        ratio = abs(prior_rar / new_rar)
        if ratio > 20 or ratio < 0.05:
            warnings.append(
                f"[RAR 스케일 경고] 과거 기록 {prior_rar:.4f} vs 재계산 {new_rar:.4f} "
                f"(배율 {ratio:.0f}x). 100배 근처면 rar() 단위 사고(v3.19)일 가능성이 크다. "
                f"어느 쪽이 퍼센트 규약인지 확인할 것 - RARxDRS가 함의하는 기대수익률이 "
                f"|1%| 미만이면 그쪽이 잘못된 값이다."
            )
        if (prior_rar >= 0) != (new_rar >= 0):
            warnings.append(
                f"[RAR 부호 반전] 과거 {prior_rar:+.4f} -> 재계산 {new_rar:+.4f}. "
                f"부호가 바뀌면 5·7번 정합성 판정과 confidence가 함께 달라진다. "
                f"입력값 차이인지 로직 변경인지 특정할 것."
            )

    prior_gap, new_gap = prior.get("gap"), result["expectation_gap"]
    if prior_gap is not None:
        if abs(prior_gap - new_gap) > 0.03:
            warnings.append(
                f"[Gap 괴리] 과거 {prior_gap*100:+.2f}%p vs 재계산 {new_gap*100:+.2f}%p "
                f"({abs(prior_gap-new_gap)*100:.2f}%p 차이). 모델선택(single/two stage)이 "
                f"다른 경우가 대표적 원인이다 - PH가 정확히 이 사례였다."
            )

    prior_ig = prior.get("implied_growth")
    if prior_ig is not None:
        models = result["implied_growth"]["models"]
        best = min(
            ((k, v) for k, v in (("single_stage", models["single_stage"]),
                                 ("two_stage", models["two_stage"])) if v is not None),
            key=lambda kv: abs(kv[1] - prior_ig), default=None,
        )
        if best and best[0] != result["implied_growth"]["model_used"]:
            warnings.append(
                f"[모델 불일치 의심] 과거 내재성장률 {prior_ig*100:.2f}%는 "
                f"{best[0]}({best[1]*100:.2f}%)에 더 가까운데, 이번 분석은 "
                f"{result['implied_growth']['model_used']}를 썼다. 과거 관행과 다른 모델을 "
                f"쓰는 것이라면 model_choice_reason에 그 사실과 이유를 명시할 것."
            )

    prior_drs = prior.get("drs")
    if prior_drs is not None and abs(prior_drs - result["drs"]["score"]) > 10:
        warnings.append(
            f"[DRS 괴리] 과거 {prior_drs:.2f} vs 재계산 {result['drs']['score']:.2f}. "
            f"주관적 입력(경쟁강도/수요민감도)이 세션마다 달라진 결과일 수 있다 - "
            f"양쪽 subjective_input_basis를 대조할 것."
        )

    return warnings


def save_ledger(result: dict, ledger_dir: str = "ledger") -> str:
    """
    분석 결과 전체(입력값 포함)를 JSON으로 저장한다.

    왜 필요한가: 큐22(Cadence)가 "계산은 했다"는 기록만 남고 입력값이 사라져
    전면 재수행해야 했고, CDNS/MNST/PH의 과거 RAR과 대조검증도 불가능했다.
    ledger 파일이 있으면 다음 세션이 같은 입력으로 재현하거나 차이를 특정할 수 있다.
    """
    os.makedirs(ledger_dir, exist_ok=True)
    date = result["meta"]["analyzed_at"][:10]
    path = os.path.join(ledger_dir, f"{result['meta']['ticker']}_{date}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2, default=str)
    return path
