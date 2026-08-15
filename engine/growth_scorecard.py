"""
Growth Scorecard (v3.43 신규, 2026-08-13) - 엔진의 성장률 추정을 현실과 대조한다.

**왜 만들었나 - 주가 검증은 몇 년이 걸리지만 성장률 검증은 분기마다 가능하다.**
`engine/thesis_monitor.py`(v3.42)가 반증조건이라는 이진 예측을 감시한다면,
이 모듈은 엔진의 **핵심 연속값 주장인 Realistic Growth**를 회사가 실제로
내놓는 숫자와 대조한다. 이 프로젝트는 이미 이 대조를 **손으로 5번** 했고
전부 정성조사 중 우연히 나온 부산물이었다:

  ROP  엔진 12.00%(stalwart 캡)  vs 회사 오가닉 공시 5~6%      -> 판정 뒤집힘
  KEYS 엔진  1.47%(trailing CAGR) vs FY26 가이던스 20%대 후반  -> 판정 뒤집힘
  TCOM 엔진 12.39%               vs 회사 가이던스 +3~8%
  GEN  엔진 14%대                vs 회사 가이던스 6.5~8.5%
  MNDY 엔진이 FCF CAGR 230%를 노이즈로 기각  -> 회사가 지속불가를 스스로 인정

ROP는 `realistic_growth_override` 신설(v3.28)로, KEYS는 크로스체크 스크립트로
각각 일회성 대응했다. 실증사례가 5건이나 쌓였으므로 이제 공유 로직으로
승격한다(capex_intensity가 NVO 1건으로 배선된 선례보다 근거가 두텁다).

## ⚠️ 이 모듈이 **하지 않는** 것 - 가이던스를 정답지로 쓰지 않는다

Realistic Growth는 n≈12년에 걸쳐 쓰이는 **장기 지속가능 성장률**이고, 회사
가이던스는 **1개년 예측**이다. 둘을 직접 비교해 "엔진이 틀렸다"고 채점하면
CLAUDE.md가 KEYS 크로스체크에서 이미 경고한 실수를 그대로 반복한다:

  "검증 안 된 1개년 가이던스만으로 realistic_growth_override를 쓰는 것은
   ROP 사례가 확립한 기준(다년 실적 필요)에 못 미친다"

그래서 관측치를 **종류별로 라벨링해 저장하고 절대 섞어 평균내지 않는다**
(`ObservationKind`). 가이던스는 점수가 아니라 **괴리 플래그**다.

## 대신 하는 것 - 판정이 성장률 입력에 얼마나 취약한지 정량화

Implied Growth는 시가총액·FCF0·r·n에서만 나오므로 **성장률 입력과 완전히
독립**이다(ROP 크로스체크가 이미 활용한 성질). 따라서:

  - `breakeven_growth()`: "저평가로 판정되려면 성장률이 최소 몇 %여야 하는가"
    = Implied Growth + 판정밴드. **분석자 주관이 개입할 수 없는 객관적 기준선**
    이라 회사가 실제로 내는 숫자와 곧바로 비교할 수 있다. ETF 엔진의
    `required_growth_thresholds()`(v3.34)가 확립한 발상을 회사 엔진에 그대로
    옮긴 것 - 두 엔진이 같은 사고방식을 공유하게 된다.
  - `gap_at_alternative_growth()`: 관측치를 Realistic Growth 자리에 대입해
    Gap·ER·RAR·판정을 재계산. ROP/KEYS 크로스체크 스크립트가 각자 복사해
    갖고 있던 계산을 하나로 합친 것이다(v3.32가 판정규칙 4중복에서 겪은
    사고를 성장률 크로스체크에서 되풀이하지 않는다).

결과는 전부 `reports/`로만 나간다 - 공식 ledger는 건드리지 않는다
(thesis_monitor와 동일한 "병기, 자동판정 안 함" 원칙).
"""

from engine.expectation_gap_engine import (
    JUDGMENT_BAND,
    bull_bear_base_growth_rates,
    expected_return,
    judgment_from_gap,
    judgment_grade_from_gap,
    rar_from_decimal_return,
    scenario_probabilities_from_drs,
    scenario_return_from_growth,
)

# 관측치 종류 - **절대 섞어서 평균내지 말 것.** 각각 증거력이 다르다.
#   realized_multiyear : 여러 분기/연도에 걸쳐 회사가 실제로 실현한 성장률.
#                        증거력이 가장 높다(ROP 오가닉 5~6%가 이 유형이라
#                        v3.28에서 공식판정 승격까지 갔다).
#   realized_quarterly : 분석 이후 발표된 단일 분기 실적. 진짜 out-of-sample
#                        이지만 1개 분기라 노이즈가 크다.
#   guidance_annual    : 회사의 1개년 가이던스. **예측이지 실적이 아니다** -
#                        괴리 플래그로만 쓰고 점수로 쓰지 않는다.
OBSERVATION_KINDS = ("realized_multiyear", "realized_quarterly", "guidance_annual")

# 관측치가 엔진 추정과 이만큼 벌어지면 경고(임계값 근거: ROP 6.5%p·KEYS 26%p·
# TCOM 6.9%p·GEN 6.5%p가 전부 실제로 문제가 됐던 사례이고, 그 최솟값이
# 6.5%p였다. 판정밴드(±5%p)보다 크게 잡아 밴드 내 미세차이로 경고가 남발되지
# 않게 했다 - 관측 5건 기반 시작점이며 검증된 값이 아니다).
DIVERGENCE_WARNING_THRESHOLD = 0.065


def breakeven_growth(ledger: dict) -> dict:
    """
    이 종목이 각 판정을 받으려면 Realistic Growth가 얼마여야 하는지.

    Implied Growth는 성장률 입력과 무관하게 고정이므로 판정 경계는 순전히
    Implied Growth ± 판정밴드다 - **분석자 주관이 전혀 개입하지 않는 기준선**.
    """
    ig = ledger["implied_growth"]["value"]
    return {
        "implied_growth": ig,
        # 이 값 이상이어야 "저평가 가능성"
        "undervalued_floor": ig + JUDGMENT_BAND,
        # 이 값 이하면 "과대평가 가능성"
        "overvalued_ceiling": ig - JUDGMENT_BAND,
        "engine_realistic_growth": ledger["growth"]["realistic_growth"],
        # 엔진 추정이 저평가 문턱을 얼마나 여유있게 넘었는가(음수면 못 넘음)
        "headroom_vs_undervalued_floor": (
            ledger["growth"]["realistic_growth"] - (ig + JUDGMENT_BAND)
        ),
    }


def gap_at_alternative_growth(ledger: dict, alt_growth: float,
                              lynch_type: str = None) -> dict:
    """
    Realistic Growth 자리에만 다른 값을 대입해 Gap·ER·RAR·판정을 재계산한다.

    ledger에 저장된 DRS·할인율(r)·n·g_terminal·Implied Growth를 그대로 재사용한다
    - Implied Growth는 성장률 입력과 독립이라 고정해도 정당하다(ROP 크로스체크가
    확립한 성질).

    lynch_type: 시나리오 상하한 캡에 쓴다. None이면 ledger가 실제로 채택한
    유형을 그대로 쓴다(ROP/KEYS 스크립트는 이걸 하드코딩했는데, 티커마다 달라
    일반화하려면 ledger에서 읽어야 한다).
    """
    d = ledger["derived"]
    disc = ledger["discount_rate"]
    drs = ledger["drs"]["score"]
    market_cap = ledger["inputs"]["market_cap"]
    fcf0 = d["fcf0"]
    r, n, g_terminal = disc["r"], disc["n"], disc["g_terminal"]
    implied_growth = ledger["implied_growth"]["value"]
    lt = lynch_type or ledger["lynch"]["used"]

    rates = bull_bear_base_growth_rates(alt_growth, lt)
    r_bull = scenario_return_from_growth(market_cap, fcf0, r, n, g_terminal, rates["g_bull"])
    r_base = scenario_return_from_growth(market_cap, fcf0, r, n, g_terminal, rates["g_base"])
    r_bear = scenario_return_from_growth(market_cap, fcf0, r, n, g_terminal, rates["g_bear"])

    p_bull, p_base, p_bear, _ = scenario_probabilities_from_drs(drs)
    er = expected_return(p_bull, r_bull, p_base, r_base, p_bear, r_bear)
    gap = alt_growth - implied_growth

    return {
        "alt_growth": alt_growth,
        "lynch_type_used": lt,
        "implied_growth": implied_growth,
        "gap": gap,
        "expected_return": er,
        "rar": rar_from_decimal_return(er, drs),
        "judgment": judgment_from_gap(gap),
        "grade": judgment_grade_from_gap(gap),
    }


def score_observation(ledger: dict, observation: dict) -> dict:
    """
    관측치 1건을 엔진 추정과 대조한다.

    observation: {"kind": OBSERVATION_KINDS 중 하나, "growth": float,
                  "label": str, "source": str}

    ⚠️ 반환값의 `judgment_flipped`는 "관측치를 그대로 Realistic Growth로 썼다면
    판정이 달라졌을 것"이라는 뜻이지, **관측치가 옳다는 뜻이 아니다.** 특히
    kind="guidance_annual"은 1개년 예측이라 다년 개념인 Realistic Growth를
    대체할 자격이 없다(모듈 docstring 참고) - 그래서 `usable_as_override`로
    구분해 표시한다.
    """
    kind = observation["kind"]
    if kind not in OBSERVATION_KINDS:
        raise ValueError(f"알 수 없는 관측치 종류: {kind} (허용: {OBSERVATION_KINDS})")

    engine_rg = ledger["growth"]["realistic_growth"]
    obs_g = observation["growth"]
    alt = gap_at_alternative_growth(ledger, obs_g)
    divergence = obs_g - engine_rg

    return {
        "ticker": ledger["meta"]["ticker"],
        "analyzed_at": ledger["meta"]["analyzed_at"][:10],
        "kind": kind,
        "label": observation.get("label", ""),
        "source": observation.get("source", ""),
        "engine_realistic_growth": engine_rg,
        "observed_growth": obs_g,
        "divergence_pp": divergence,
        "divergence_exceeds_threshold": abs(divergence) >= DIVERGENCE_WARNING_THRESHOLD,
        "engine_gap": ledger["expectation_gap"],
        "gap_at_observed": alt["gap"],
        "engine_judgment": ledger["judgment"],
        "judgment_at_observed": alt["judgment"],
        "judgment_flipped": alt["judgment"] != ledger["judgment"],
        "rar_at_observed": alt["rar"],
        # ROP가 확립한 기준: 다년 실현실적만 공식판정 승격 근거가 된다.
        "usable_as_override": kind == "realized_multiyear",
    }


def growth_cap_is_binding(ledger: dict) -> bool:
    """
    Realistic Growth가 Lynch 유형 상한 그 자체인가(M-1 성장상한 바인딩).

    바인딩된 종목은 성장분석이 결과에 전혀 기여하지 못하고 Gap이 사실상
    `상한 - Implied Growth`만 남는다 - 관측치와의 괴리가 특히 크게 벌어지는
    구조적 이유이며, ROP·GEN·BRO가 전부 이 경우였다.
    """
    for note in ledger.get("data_limitations", []):
        if "성장상한 바인딩" in note:
            return True
    return False
