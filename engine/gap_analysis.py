"""
Gap Analysis (v3.48 신규, 2026-08-15) - Expectation Gap을 **숫자 하나로 끝내지 않는다.**

## 왜 필요한가

이 프로젝트는 Gap을 잘 계산하지만, Gap 하나만 보고는 다음 다섯 질문 중 첫
번째밖에 답하지 못했다:

  1. 지금 괴리가 얼마나 큰가?            -> `expectation_gap` (있었음)
  2. 괴리가 확대되고 있는가 축소인가?     -> thesis_monitor에 흩어져 있었음
  3. 왜 이 괴리가 발생했는가?             -> **없었음**
  4. 그 판단을 뒷받침하는 근거는 얼마나 강한가? -> growth_scorecard에 흩어져 있었음
  5. 모델 불확실성은 어느 정도인가?        -> gap_distribution/sensitivity에 흩어져 있었음

**이 모듈은 새 계산을 거의 하지 않는다.** 2·4·5는 이미 만들어 둔 모듈
(`thesis_monitor` v3.42 / `growth_scorecard` v3.43 / `gap_distribution` v3.44)을
호출할 뿐이고, 3만 새로 만든다. 흩어진 것을 한 구조로 모으는 게 목적이다.

## ⚠️ 3(gap_drivers)에서 지킨 원칙 - 근거 없는 정량 attribution을 만들지 않는다

Gap = RealisticGrowth - ImpliedGrowth 이므로 **두 시점 간 변화는 정확한
항등식**이다:

    ΔGap = ΔRealisticGrowth - ΔImpliedGrowth        (오차 없음)

여기까지는 발명이 아니라 대수다. 문제는 ΔImpliedGrowth를 다시 쪼갤 때다 -
Implied Growth는 (시가총액, FCF0, r, n, g_terminal)의 **비선형** 함수라
"시총이 X만큼 기여했다"는 분해가 유일하게 정해지지 않는다.

그래서 이 모듈은 **one-at-a-time(OAT) + 잔차 명시** 방식만 쓴다: 한 번에 하나씩만
바꿔 재계산하고, 개별 기여도의 합과 실제 변화의 차이를 `interaction_residual`로
**숨기지 않고 그대로 보고한다.** 잔차가 크면 그 분해를 믿지 말라는 뜻이다.
방법 이름도 결과에 `method` 필드로 박아둔다.

가중치를 지어내 100%로 맞추는 식의 attribution은 하지 않는다(계약서 5.2절
"금융 가정 발명 금지", CLAUDE.md의 P/B 임계값·LYNCH_TYPE_CAPS와 동일 판단).

## ⚠️ Expectation Gap의 인식론적 지위 - 검증된 alpha가 아니다

`GAP_SIGNAL_STATUS`가 이를 기계 판독 가능하게 못박는다. Gap이 크다는 것은
**연구 가설**이지 초과수익의 증거가 아니다. 이 프로젝트에는 Gap과 미래
위험조정수익률의 관계를 검증한 데이터가 아직 없다(그 검증 자체가
`engine/experiment_registry.py`의 EXP-001로 등록돼 있다).

실제로 v3.42가 TTD에서 실측한 반례가 있다 - **주가가 26.3% 빠지자 Gap이
+17.01%p에서 +20.96%p로 오히려 벌어졌는데, 같은 기간 반증조건 3개가 동시
발동했다.** 즉 사업이 무너져서 주가가 빠진 경우에도 Gap은 "더 사라"고 말한다.
Gap 단독 사용이 가치함정을 만든다는 수학적 원리이며, 이 모듈이 gap_level만
따로 쓰지 말라고 경고하는 이유다.
"""

from engine.expectation_gap_engine import (
    JUDGMENT_BAND,
    implied_growth_single_stage,
    implied_growth_two_stage,
    judgment_from_gap,
)

# 계약서 40절 검증단계 어휘를 그대로 쓴다(expectation_gap_engine.VALIDATION_STATUS와 동일 체계).
# Gap이 실제 초과수익을 만든다는 근거는 이 저장소에 **없다** - 검증 전까지 가설이다.
GAP_SIGNAL_STATUS = "RESEARCH_HYPOTHESIS (미검증 - Gap과 실현 위험조정수익률의 관계는 EXP-001에서 검증 중)"

# 증거력 서열 - growth_scorecard.OBSERVATION_KINDS와 같은 어휘를 쓰되 순위를 매긴다.
# ROP(다년 실현 오가닉)만 공식판정 승격까지 갔고, KEYS(1개년 가이던스)는
# 승격을 보류했다 - 그 선례가 이 서열의 근거다.
EVIDENCE_RANK = {
    "realized_multiyear": 3,    # 다년 실현 - 유일하게 override 자격
    "realized_quarterly": 2,    # 분석 이후 1개 분기 - 진짜 out-of-sample이나 노이즈 큼
    "guidance_annual": 1,       # 회사 1개년 예측 - 실적이 아님
}


def gap_level(ledger: dict) -> dict:
    """
    질문 1: 지금 괴리가 얼마나 큰가.

    저장된 판정을 재계산하지 않고 그대로 읽는다(공식 기록이 진실). 다만
    "저평가로 판정되려면 성장률이 최소 얼마여야 하는가"라는 객관적 기준선을
    함께 준다 - growth_scorecard.breakeven_growth()를 그대로 재사용한다.
    """
    from engine.growth_scorecard import breakeven_growth, growth_cap_is_binding

    be = breakeven_growth(ledger)
    return {
        "ticker": ledger["meta"]["ticker"],
        "analyzed_at": ledger["meta"]["analyzed_at"][:10],
        "gap": ledger["expectation_gap"],
        "judgment": ledger["judgment"],
        "grade": ledger.get("judgment_grade"),
        "signal_status": GAP_SIGNAL_STATUS,
        # 시장이 이미 요구하고 있는 성장률(분석자 주관이 개입할 수 없는 축)
        "valuation_implied_requirement": be["implied_growth"],
        "evidence_supported_expectation": be["engine_realistic_growth"],
        "undervalued_floor": be["undervalued_floor"],
        "headroom_vs_undervalued_floor": be["headroom_vs_undervalued_floor"],
        # 상한이 바인딩되면 Gap이 사실상 '캡 - Implied Growth'만 남는다
        "growth_cap_binding": growth_cap_is_binding(ledger),
    }


def gap_change(ledger: dict, market_cap_now: float = None,
               current_result: dict = None) -> dict:
    """
    질문 2: 괴리가 확대되고 있는가 축소되고 있는가.

    두 가지 입력을 받는다(둘 중 하나는 있어야 한다):

    - `market_cap_now`: 펀더멘털을 고정하고 주가만 갱신. thesis_monitor(v3.42)의
      `recompute_gap_at_market_cap()`을 **그대로 재사용**한다(새 계산 0줄).
      이 경로에서 Realistic Growth는 반드시 불변이어야 하며, 아니면 버그이므로
      `realistic_growth_unchanged=False`로 드러낸다.
    - `current_result`: 새 재무데이터로 다시 돌린 `run_analysis()` 결과.
      이 경우 ΔGap을 정확한 항등식으로 분해한다.

    ⚠️ 이 프로젝트는 **티커당 ledger 1건** 규칙(v3.32)을 강제하므로 과거 ledger
    끼리 비교하는 경로는 원칙적으로 존재하지 않는다. 그래서 '변화'는 항상
    저장된 공식 기록 대비 현재값으로 정의한다.
    """
    if market_cap_now is None and current_result is None:
        raise ValueError(
            "market_cap_now 또는 current_result 중 하나는 필요하다 - "
            "무엇과 비교할지 없으면 변화를 정의할 수 없다."
        )

    out = {
        "ticker": ledger["meta"]["ticker"],
        "gap_then": ledger["expectation_gap"],
        "judgment_then": ledger["judgment"],
    }

    if market_cap_now is not None:
        from engine.thesis_monitor import recompute_gap_at_market_cap

        decay = recompute_gap_at_market_cap(ledger, market_cap_now)
        out.update({
            "basis": "price_only",
            "gap_now": decay["gap_now"],
            "gap_change_pp": decay["gap_decay_pp"],
            "judgment_now": decay["judgment_now"],
            "judgment_flipped": decay["judgment_flipped"],
            "market_cap_change_pct": decay["market_cap_change_pct"],
            # 주가만 바꿨으므로 성장추정은 불변이어야 한다(아니면 버그)
            "realistic_growth_unchanged": (
                abs(decay["realistic_growth_now"] - decay["realistic_growth_then"]) < 1e-12
            ),
            # ⚠️ v3.42 TTD 실측: 사업이 나빠져 주가가 빠져도 Gap은 벌어진다.
            "direction_note": (
                "주가 하락은 Gap을 반드시 확대시킨다(Implied Growth만 내려가고 "
                "Realistic Growth는 재무제표에서만 나오므로 불변) - Gap 확대를 "
                "곧바로 '더 싸졌다'로 읽지 말고 반증조건과 함께 볼 것."
            ),
        })
        return out

    # current_result 경로 - 정확한 항등식 분해
    rg_then = ledger["growth"]["realistic_growth"]
    ig_then = ledger["implied_growth"]["value"]
    rg_now = current_result["growth"]["realistic_growth"]
    ig_now = current_result["implied_growth"]["value"]
    gap_now = current_result["expectation_gap"]

    out.update({
        "basis": "full_reanalysis",
        "gap_now": gap_now,
        "gap_change_pp": gap_now - ledger["expectation_gap"],
        "judgment_now": current_result["judgment"],
        "judgment_flipped": current_result["judgment"] != ledger["judgment"],
        "identity": {
            "method": "exact_algebraic (Gap = RealisticGrowth - ImpliedGrowth)",
            "delta_realistic_growth": rg_now - rg_then,
            "delta_implied_growth": ig_now - ig_then,
            # 항등식이 성립하는지 스스로 확인한다 - 안 맞으면 어느 쪽이 잘못된 것
            "identity_residual": (
                (gap_now - ledger["expectation_gap"])
                - ((rg_now - rg_then) - (ig_now - ig_then))
            ),
        },
    })
    return out


def gap_drivers(ledger: dict, market_cap_now: float = None,
                fcf0_now: float = None, r_now: float = None) -> dict:
    """
    질문 3: 왜 이 괴리가 (변)했는가 - Implied Growth 쪽 원인을 쪼갠다.

    ⚠️ **이 분해는 유일하지 않다.** Implied Growth는 입력들의 비선형 함수라
    "시총 기여분"이 수학적으로 유일하게 정해지지 않는다. 여기서는 한 번에 하나씩만
    바꿔 재계산하는 OAT 방식을 쓰고, **개별 기여도의 합과 실제 변화의 차이를
    `interaction_residual`로 그대로 보고한다.** 잔차가 크면 이 분해를 신뢰하지 말 것.

    100%로 딱 떨어지게 만드는 가중치를 지어내지 않는다(계약서 5.2절).

    바꾸지 않은 인자는 ledger 값을 그대로 쓴다. 아무것도 주지 않으면
    변화가 없는 것이므로 기여도가 전부 0이다.
    """
    d = ledger["derived"]
    disc = ledger["discount_rate"]
    model = ledger["implied_growth"]["model_used"]

    base = {
        "market_cap": ledger["inputs"]["market_cap"],
        "fcf0": d["fcf0"],
        "r": disc["r"],
    }
    now = {
        "market_cap": market_cap_now if market_cap_now is not None else base["market_cap"],
        "fcf0": fcf0_now if fcf0_now is not None else base["fcf0"],
        "r": r_now if r_now is not None else base["r"],
    }

    n, g_terminal = disc["n"], disc["g_terminal"]

    def _ig(market_cap, fcf0, r):
        if model == "single_stage":
            return implied_growth_single_stage(market_cap, fcf0, r)
        # ⚠️ two_stage는 (성장률, 수렴로그, 반복횟수) 튜플을 돌려준다 - 첫 값만
        # 쓴다. 초판은 튜플을 그대로 빼서 TypeError를 냈는데, 골든케이스(CDNS)가
        # single_stage라 테스트를 통과했다. two_stage 종목(BSX)으로 회귀 테스트를
        # 따로 건다.
        g, _, _ = implied_growth_two_stage(market_cap, fcf0, r, n, g_terminal)
        return g

    ig_base = _ig(**base)
    ig_now = _ig(**now)
    total_delta = ig_now - ig_base

    contributions = {}
    for factor in ("market_cap", "fcf0", "r"):
        if now[factor] == base[factor]:
            contributions[factor] = 0.0
            continue
        oat = dict(base)
        oat[factor] = now[factor]
        contributions[factor] = _ig(**oat) - ig_base

    residual = total_delta - sum(contributions.values())

    return {
        "ticker": ledger["meta"]["ticker"],
        "method": "one_at_a_time_with_residual (분해는 유일하지 않음 - 잔차를 반드시 함께 볼 것)",
        "model_used": model,
        "implied_growth_then": ig_base,
        "implied_growth_now": ig_now,
        "delta_implied_growth": total_delta,
        "contributions": contributions,
        "interaction_residual": residual,
        # 잔차가 전체 변화의 10%를 넘으면 개별 기여도를 단독으로 인용하지 말 것
        "residual_is_material": (
            abs(residual) > 0.1 * abs(total_delta) if abs(total_delta) > 1e-12 else False
        ),
        "inputs_changed": {
            k: {"then": base[k], "now": now[k]}
            for k in base if now[k] != base[k]
        },
    }


def evidence_strength(ledger: dict, observations: list = None) -> dict:
    """
    질문 4: 이 판단을 뒷받침하는 근거가 얼마나 강한가.

    관측치 채점은 growth_scorecard.score_observation()을 **그대로 재사용**한다.
    이 모듈이 더하는 것은 **증거력 서열**뿐이다(EVIDENCE_RANK).

    ⚠️ 관측치 종류를 절대 섞어 평균내지 않는다 - Realistic Growth는 다년 개념이고
    가이던스는 1개년 예측이라 같은 축에 놓으면 KEYS 크로스체크가 이미 경고한
    실수를 반복한다. 대신 **가장 강한 증거가 무엇인지**만 뽑아준다.

    observations 없이 부르면 "증거 없음"이 정직하게 드러난다 - 이 프로젝트
    34종목 중 대부분이 실제로 이 상태다(추측으로 채우지 않는다).
    """
    from engine.growth_scorecard import DIVERGENCE_WARNING_THRESHOLD, score_observation

    observations = observations or []
    scored = [score_observation(ledger, o) for o in observations]

    strongest = None
    if scored:
        strongest = max(scored, key=lambda s: EVIDENCE_RANK[s["kind"]])

    return {
        "ticker": ledger["meta"]["ticker"],
        "n_observations": len(scored),
        # Confidence는 확률이 아니다(v3.46 VALIDATION_STATUS) - 참고값으로만 병기
        "engine_confidence": ledger["confidence"]["final"],
        "engine_confidence_note": "UNCALIBRATED - 확률로 해석 금지(v3.46)",
        "strongest_evidence_kind": strongest["kind"] if strongest else None,
        "strongest_evidence_rank": EVIDENCE_RANK[strongest["kind"]] if strongest else 0,
        "has_override_grade_evidence": any(s["usable_as_override"] for s in scored),
        "any_observation_flips_judgment": any(s["judgment_flipped"] for s in scored),
        "divergence_threshold": DIVERGENCE_WARNING_THRESHOLD,
        "observations": scored,
        "data_limitations": ledger.get("data_limitations", []),
    }


def model_uncertainty(ledger: dict, corpus_ranges: dict = None) -> dict:
    """
    질문 5: 모델 불확실성은 어느 정도인가.

    세 가지를 모은다(전부 기존 산출물 재사용, 새 계산 없음):

    1. **모델 선택 괴리** - single_stage vs two_stage. 이 프로젝트에서 판정을
       실제로 뒤집을 뻔했던 원인 1위다(PH 사례).
    2. **DRS 민감도** - `sensitivity_check`(강건성 점검)가 이미 저장돼 있다.
    3. **주관적 입력 분포** - `gap_distribution.monte_carlo_gap()`. corpus_ranges를
       주면 실행한다(34종목 실측 범위 기반). 없으면 건너뛰되 **건너뛴 사실을
       남긴다**(조용히 관대해지지 않게 - ETF 엔진의 ERS 항목 제외 처리와 동일 원칙).
    """
    models = ledger["implied_growth"]["models"]
    sens = ledger.get("sensitivity_check", {})

    out = {
        "ticker": ledger["meta"]["ticker"],
        "model_used": ledger["implied_growth"]["model_used"],
        "model_choice_reason": ledger["implied_growth"].get("model_choice_reason"),
        "model_divergence": models.get("divergence"),
        "model_divergence_warning": models.get("divergence_warning"),
        "drs_sensitivity_flips_judgment": sens.get("judgment_flipped"),
        "gap_with_drs": sens.get("gap_with_drs"),
        "gap_without_drs": sens.get("gap_without_drs"),
        "monte_carlo": None,
        "skipped": [],
    }

    if corpus_ranges is None:
        out["skipped"].append(
            "monte_carlo - corpus_ranges 미제공(gap_distribution.observed_ranges()로 "
            "생성해 넘기면 주관적 입력 분포에 따른 판정 취약성을 측정한다)"
        )
        return out

    from engine.gap_distribution import fragility_label, monte_carlo_gap

    mc = monte_carlo_gap(ledger, corpus_ranges)
    out["monte_carlo"] = mc
    out["fragility"] = fragility_label(mc)
    return out


def analyze_gap(ledger: dict, market_cap_now: float = None,
                current_result: dict = None, observations: list = None,
                corpus_ranges: dict = None) -> dict:
    """
    다섯 질문을 한 구조로 묶는다. 각 하위 함수는 독립적으로도 쓸 수 있다.

    ⚠️ 이 함수는 **투자판단을 내리지 않는다.** Gap이 크다는 것은 연구 가설이지
    매수 신호가 아니다(`GAP_SIGNAL_STATUS`). 판단으로 넘어가려면
    `engine/thesis.py`의 게이트(사업품질·재무품질·리스크·밸류에이션·포트폴리오
    맥락)를 통과해야 한다.
    """
    result = {
        "ticker": ledger["meta"]["ticker"],
        "signal_status": GAP_SIGNAL_STATUS,
        "gap_level": gap_level(ledger),
        "gap_change": None,
        "gap_drivers": None,
        "evidence_strength": evidence_strength(ledger, observations),
        "model_uncertainty": model_uncertainty(ledger, corpus_ranges),
        "decision_note": (
            "이 구조는 신호(signal)일 뿐 결정(decision)이 아니다. "
            "BUY/HOLD/WATCH/SELL은 engine/thesis.py의 게이트를 거쳐 "
            "분석자가 기록한다 - Gap에서 자동으로 도출하지 않는다."
        ),
    }

    if market_cap_now is not None or current_result is not None:
        result["gap_change"] = gap_change(ledger, market_cap_now, current_result)
        result["gap_drivers"] = gap_drivers(ledger, market_cap_now=market_cap_now)

    return result
