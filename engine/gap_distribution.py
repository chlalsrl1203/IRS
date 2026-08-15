"""
Gap Distribution (v3.44 신규, 2026-08-13) - Gap을 점추정이 아니라 분포로 본다.

**왜 만들었나 - 오늘 BSX 사건이 보여준 문제의 일반해다.** BSX의 screener
false-rejection(이 세션 앞부분)은 "큰 분산을 가진 값(경쟁강도, 실측범위
3.6~20.0)을 점 하나(12.0 중앙값)로 대체했더니 판정이 뒤집혔다"는 사건이었다.
그런데 **정식 엔진도 구조가 똑같다** - `run_analysis()`가 Gap 하나(예: BSX
+5.87%p)를 뽑아 ±5%p 밴드에 대고 판정하는데, 정작 그 Gap이 만드는 데 쓰인
`demand_sensitivity_pct`·`competition_intensity`가 얼마나 흔들리는 값인지는
아무도 모른다. **BSX는 스크리너에서 우연히 드러났을 뿐, 모든 정식분석이 같은
구조적 취약점을 안고 있다.**

## 무엇을 흔드는가 - 이 프로젝트가 이미 축적한 값만 쓴다

Gap = Realistic Growth(주로 재무 시계열에서 나오는 객관값) - Implied
Growth(시총·FCF0·r·n에서 나오는 값). r은 DRS -> ERP 경로로 나오고, DRS 5개
구성요소 중 3개(revenue_volatility/margin_volatility/leverage)는 재무
데이터에서 **직접 계산**되므로 흔들 대상이 아니다. 흔들 가치가 있는 건
분석자의 근거 있는 **판단**이 들어가는 두 개뿐이다:

  - `demand_sensitivity_pct`(cyclicality_score에 반영) - 34종목 관측범위
    0.05~0.60(CLAUDE.md demand_sensitivity 앵커표와 일치하는 원자료).
  - `competition_intensity`(competition_intensity_score의 결과값) - 34종목
    관측범위 3.6~20.0.

**지어낸 사전분포가 아니라 자기가 실제로 축적한 값을 쓴다** - 이 프로젝트
원칙과 정확히 일치한다(demand_sensitivity 앵커표·P/B 임계값 미고정과 같은
"관측 기반 시작점" 철학).

## 분포 형태 - triangular(전체관측범위, 분석자의 실제 판단값)

균등분포로 전체 범위를 뽑으면 모든 종목이 같은 분포를 공유하게 돼 "이
종목 고유의 판단이 얼마나 흔들리는지"를 측정한다는 목적이 사라진다.
분석자가 이미 근거를 남기고 내린 값(`subjective_input_basis`)을 무시하는
것도 아니다 - 봉우리(mode)는 그 실제 판단값에 두고, 양끝(min/max)만 프로젝트가
실측한 전체 범위로 잡는 **삼각분포**를 쓴다. "이 판단이 맞을 가능성이 가장
높지만, 다른 34종목에 실제로 쓰인 값들만큼은 벌어질 수 있다"는 뜻이다.

## ⚠️ 이 모듈도 "병기, 자동판정 안 함" 원칙을 따른다

`P(저평가 가능성)` 같은 확률은 공식 판정을 대체하지 않는다. 오히려 반대 -
**P가 낮은데 공식 판정이 저평가면, 그 판정은 동전던지기에 가깝다는 뜻**이라
분석자가 `demand_sensitivity_pct`/경쟁강도 근거를 더 파야 한다는 신호로 쓴다.
결과는 `reports/`로만 나가고 `ledger/`는 건드리지 않는다(thesis_monitor·
growth_scorecard와 동일 설계).
"""

import random
import statistics
from dataclasses import dataclass

from engine.expectation_gap_engine import (
    erp_from_drs,
    implied_growth_single_stage,
    implied_growth_two_stage,
    judgment_from_gap,
)

DEFAULT_N_DRAWS = 3000
DEFAULT_SEED = 20260813   # 실행마다 같은 리포트가 나오도록 고정(재현성)


@dataclass
class ObservedRange:
    lo: float
    hi: float
    n: int


def observed_ranges(ledgers: list) -> dict:
    """
    ledger corpus에서 demand_sensitivity_pct·competition_intensity의 실측
    최소/최대를 뽑는다. 하드코딩된 상수를 두지 않는 이유는 corpus가 자랄수록
    (지금 34종목) 범위 자체가 갱신돼야 하기 때문이다 - screener.py의
    competition_intensity 중앙값을 34종목으로 재검증했던 것과 같은 이유.
    """
    ds = [d["inputs"]["demand_sensitivity_pct"] for d in ledgers]
    ci = [d["drs"]["components"]["competition_intensity"] for d in ledgers]
    return {
        "demand_sensitivity_pct": ObservedRange(min(ds), max(ds), len(ds)),
        "competition_intensity": ObservedRange(min(ci), max(ci), len(ci)),
    }


def _implied_growth_at_r(ledger: dict, r: float) -> float:
    """model_used와 동일한 모델로, r만 바꿔서 Implied Growth를 다시 푼다."""
    d = ledger["derived"]
    disc = ledger["discount_rate"]
    market_cap = ledger["inputs"]["market_cap"]
    fcf0 = d["fcf0"]
    model = ledger["implied_growth"]["model_used"]

    if model == "single_stage":
        return implied_growth_single_stage(market_cap, fcf0, r)
    g, _log, _err = implied_growth_two_stage(
        market_cap, fcf0, r, disc["n"], disc["g_terminal"]
    )
    return g


def _triangular(rng: random.Random, lo: float, hi: float, mode: float) -> float:
    """
    mode가 [lo, hi] 밖이면(분석자 판단이 관측 corpus 범위를 벗어난 경우)
    random.triangular가 자동으로 mode를 clamp하지 않으므로 여기서 명시적으로
    가둔다 - 그렇지 않으면 삼각분포 자체가 정의되지 않는다.
    """
    mode = min(max(mode, lo), hi)
    return rng.triangular(lo, hi, mode)


def monte_carlo_gap(ledger: dict, corpus_ranges: dict,
                    n_draws: int = DEFAULT_N_DRAWS,
                    seed: int = DEFAULT_SEED) -> dict:
    """
    demand_sensitivity_pct·competition_intensity만 삼각분포로 흔들고 나머지
    (revenue_volatility/margin_volatility/leverage/worst_yoy/Realistic Growth)는
    전부 ledger에 저장된 값으로 고정한 채 Gap 분포를 얻는다.

    반환값의 `gap_samples`는 리포트에는 요약통계만 남기고 원본은 버린다
    (n_draws=3000 x 34종목을 전부 JSON에 담으면 리포트가 불필요하게 커진다 -
    요약이면 재현성엔 지장 없다, seed가 고정돼 있어 언제든 다시 뽑을 수 있다).
    """
    rng = random.Random(seed ^ hash(ledger["meta"]["ticker"]) & 0xFFFFFFFF)

    comps = ledger["drs"]["components"]
    fixed_sum = (comps["revenue_volatility"] + comps["margin_volatility"]
                 + comps["leverage"])
    worst_yoy = ledger["derived"]["worst_yoy_revenue_growth"]
    realistic_growth = ledger["growth"]["realistic_growth"]
    rf = ledger["discount_rate"]["rf"]

    ds_range = corpus_ranges["demand_sensitivity_pct"]
    ci_range = corpus_ranges["competition_intensity"]
    ds_mode = ledger["inputs"]["demand_sensitivity_pct"]
    ci_mode = comps["competition_intensity"]

    from engine.expectation_gap_engine import _CYCLICALITY_BUCKETS, _bucket_score
    cyclicality_base = _bucket_score(worst_yoy, _CYCLICALITY_BUCKETS, ascending=False)

    gaps, judgments = [], []
    for _ in range(n_draws):
        ds_draw = _triangular(rng, ds_range.lo, ds_range.hi, ds_mode)
        ci_draw = _triangular(rng, ci_range.lo, ci_range.hi, ci_mode)

        cyclicality_draw = min(cyclicality_base + min(max(ds_draw, 0.0), 1.0) * 4.0, 20.0)
        # DRSInputs.score() = (가중합/가중치합)*5. 기본 가중치가 전부 1.0이면
        # 이는 대수적으로 "5개 구성요소의 합"과 정확히 같다(평균 x 5 = 합).
        drs_draw = fixed_sum + cyclicality_draw + ci_draw

        r_draw = rf + erp_from_drs(drs_draw)
        ig_draw = _implied_growth_at_r(ledger, r_draw)
        gap_draw = realistic_growth - ig_draw

        gaps.append(gap_draw)
        judgments.append(judgment_from_gap(gap_draw))

    n = len(gaps)
    p_under = sum(1 for j in judgments if j == "저평가 가능성") / n
    p_over = sum(1 for j in judgments if j == "과대평가 가능성") / n
    p_neutral = 1.0 - p_under - p_over

    return {
        "ticker": ledger["meta"]["ticker"],
        "n_draws": n,
        "official_gap": ledger["expectation_gap"],
        "official_judgment": ledger["judgment"],
        "gap_mean": statistics.mean(gaps),
        "gap_stdev": statistics.pstdev(gaps),
        "gap_p10": sorted(gaps)[int(n * 0.10)],
        "gap_p90": sorted(gaps)[int(n * 0.90)],
        "p_undervalued": p_under,
        "p_overvalued": p_over,
        "p_neutral": p_neutral,
        "ds_range_used": (ds_range.lo, ds_range.hi, ds_mode),
        "ci_range_used": (ci_range.lo, ci_range.hi, ci_mode),
    }


def fragility_label(mc: dict) -> str:
    """
    공식 판정과 다수결 확률이 어긋나거나, 확률이 50%에 가까우면 '취약'.
    임계값(0.60)은 관측 34종목 기반 시작점이다(검증된 값 아님 - demand_
    sensitivity 앵커표와 동일한 성격의 시작점).
    """
    official = mc["official_judgment"]
    p = {"저평가 가능성": mc["p_undervalued"],
         "과대평가 가능성": mc["p_overvalued"],
         "적정가/경계선": mc["p_neutral"]}.get(official, 0.0)
    if p < 0.60:
        return "취약(동전던지기에 가까움)"
    return "견고"
