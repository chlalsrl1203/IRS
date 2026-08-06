"""
ETF Valuation Engine (v3.33 신규, 2026-08-06)

왜 별도 모듈인가:
`engine/pipeline.py`의 `run_analysis()`는 10-K 재무제표(revenue/operating income/
OCF/capex)를 가진 **개별 기업** 전용이다. ETF는 그런 재무제표를 내지 않는다 -
NAV·보수율·기초자산 집계지표만 공시하므로 FCF-DCF 경로 자체가 성립하지 않는다.
2026-08-06 사용자가 "VOO 같은 미국 상장 ETF 자체가 싼가"를 물었을 때 이 구조적
한계가 드러났고, 첫 대응은 WebSearch 스냅샷을 JSON 리포트로 남기는 것이었다
(`reports/etf_valuation_comparison_2026-08-06.json`) - 재현 가능성이 회사 단위
분석(SEC EDGAR + ledger)보다 현저히 낮다는 한계를 스스로 명시했었다. 이 모듈은
그 한계를 코드로 해소한다.

**회사 엔진을 억지로 재사용하지 않되, 공유 가능한 원시함수는 반드시 재사용한다.**
v3.32 감사에서 "판정 규칙이 4곳에 복사돼 이미 라벨이 어긋나 있었다"는 사고를
겪었으므로, 아래 셋은 새로 구현하지 않고 `expectation_gap_engine`/`screener`에서
그대로 가져온다:
  - `implied_growth_from_fcf_yield()` - Gordon 역산 항등식. 분자가 FCF든 이익이든
    "영구 현금흐름 수익률 -> 내재성장률" 변환은 수학적으로 동일하다.
  - `erp_from_drs()` - 0~100 위험점수 -> ERP 매핑. ETF 위험점수(ERS)도 같은
    0~100 스케일로 설계해 이 매핑을 그대로 쓴다.
  - `judgment_from_gap()` - ±5%p 3단계 판정. **이 프로젝트의 유일한 판정 규칙
    구현체다**(v3.32에서 단일화). ETF라고 다른 사본을 만들지 않는다.

⚠️ **가장 중요한 설계 근거 - IWM(러셀2000) 사건(2026-08-06 실측)**:
같은 ETF의 P/E가 출처에 따라 20.07x(stockanalysis.com, 트레일링)와 26x(Goldman
Sachs, forward)로 갈렸고, **그 차이가 "3대 지수 중 가장 싸다"와 "가장 비싸다"라는
정반대 결론을 만들었다.** 원인은 Russell2000 구성종목 중 무이익/저이익 기업
비중이 커서 P/E 집계 방식(트레일링 단순평균 vs forward 애널리스트추정 가중)에
따라 값이 통째로 달라지는 지수 고유의 계산 왜곡이다.

그래서 이 엔진은 **P/E를 단일 스칼라로 받지 않는다** - `{출처명: P/E}` 딕셔너리로
받아 출처별로 내재성장률·Gap·판정을 각각 계산하고, 판정이 갈리는지
(`judgment_flipped_across_sources`)를 최상위 결과로 내놓는다. 이는 이 프로젝트가
이미 확립한 "병기, 자동판정 안 함" 원칙(is_insurer/sbc_cross_check)의 ETF판이다 -
어느 출처가 맞는지 코드가 임의로 고르지 않고, 갈린다는 사실 자체를 드러낸다.

단위 규약(v3.19 100배 사고의 교훈 - 어기면 조용히 틀린다):
  - 수익률·성장률·보수율은 전부 **소수**(0.0003 = 0.03%)
  - P/E는 배수 그대로(19.6)
  - `top10_weight`/`pct_unprofitable_constituents`도 **소수**(0.59 = 59%)
"""

from engine.expectation_gap_engine import (
    ENGINE_VERSION,
    _bucket_score,
    erp_from_drs,
    judgment_from_gap,
)
from engine.screener import implied_growth_from_fcf_yield

# ======================================================================
# ERS(ETF Risk Score) 구간 임계값
# ======================================================================
# ⚠️ 이 임계값들은 **검증된 값이 아니다.** LYNCH_TYPE_CAPS·demand_sensitivity
# 앵커표와 동일하게 "관측 기반 시작점"으로 취급할 것 - 2026-08-06 시점 8개 ETF
# (VOO/QQQ/IWM/DIA/XLK/XLE/XLF/XLU) 관측치를 자연스럽게 구분하는 지점에서 잡았고,
# 표본이 8건뿐이라 경계값 자체의 통계적 근거는 없다. 표본이 쌓이면 재조정할 것.
# DRS의 0~20 스케일을 그대로 따라 5개 항목 평균 x5 = 0~100이 되게 설계했다
# (erp_from_drs를 재사용하기 위한 필수 조건).

# 상위10종목 비중: 높을수록 '지수'가 아니라 소수 종목 베팅에 가까워진다
_CONCENTRATION_BUCKETS = [(0.20, 2.0), (0.30, 6.0), (0.40, 10.0),
                          (0.50, 14.0), (0.60, 18.0), (float("inf"), 20.0)]
# 보유종목 수: 적을수록 위험(ascending=False로 '이하면 그 점수')
_BREADTH_BUCKETS = [(50, 20.0), (100, 18.0), (200, 14.0),
                    (500, 10.0), (1000, 6.0), (float("inf"), 2.0)]
# 보수율: 확정적으로 발생하는 손실이라 위험이라기보다 '확실한 마이너스 알파'
_COST_BUCKETS = [(0.0005, 2.0), (0.0010, 6.0), (0.0025, 10.0),
                 (0.0050, 14.0), (0.0075, 18.0), (float("inf"), 20.0)]
# P/E 출처간 상대괴리: IWM 사건을 점수화한 항목(이 엔진의 핵심 기여)
_PE_DIVERGENCE_BUCKETS = [(0.05, 2.0), (0.10, 6.0), (0.20, 10.0),
                          (0.35, 14.0), (0.50, 18.0), (float("inf"), 20.0)]
# 무이익 구성종목 비중: P/E 집계 왜곡의 근본 원인
_UNPROFITABLE_BUCKETS = [(0.05, 2.0), (0.10, 6.0), (0.20, 10.0),
                         (0.30, 14.0), (0.40, 18.0), (float("inf"), 20.0)]

# 출처간 P/E 괴리가 이 수준을 넘으면 "단일 결론 금지" 경고를 띄운다.
# IWM 실측(20.07 vs 26.0 = 29.5% 괴리)에서 판정이 실제로 뒤집혔으므로 그보다
# 낮은 20%를 임계값으로 잡았다.
PE_DIVERGENCE_WARNING_THRESHOLD = 0.20


def earnings_yield(pe_ratio: float) -> float:
    """
    P/E -> 이익수익률(소수). Gordon 역산의 입력이 된다.

    P/E<=0은 지수 전체가 적자라는 뜻인데, 이 경우 이익수익률이 음수가 되어
    Gordon 역산이 무의미해진다(회사 엔진의 FCF0<=0 가드와 같은 상황).
    """
    if pe_ratio <= 0:
        raise ValueError(
            f"P/E({pe_ratio})가 0 이하다. 지수 전체가 적자라는 뜻이므로 "
            f"이익 기반 밸류에이션이 성립하지 않는다 - [Model Not Applicable]로 "
            f"처리하고 P/B 등 자산 기반 지표로 대체할 것."
        )
    return 1.0 / pe_ratio


def implied_growth_from_pe(pe_ratio: float, r: float) -> float:
    """
    P/E에 내재된 영구 이익성장률을 역산한다.

    `screener.implied_growth_from_fcf_yield()`를 그대로 재사용한다 - 분자가
    FCF든 이익이든 "영구 현금흐름 수익률 y에서 g = (r-y)/(1+y)"는 동일한
    Gordon 항등식이다. 별도 구현하면 v3.32에서 겪은 '같은 규칙의 사본이
    미묘하게 어긋나는' 사고를 반복하게 된다.

    ⚠️ 방법론 한계(반드시 함께 읽을 것): 이 계산은 **이익 전액이 주주에게
    귀속된다**고 가정한다. 실제 지수 구성기업은 이익의 상당부분을 재투자하므로
    (S&P500 배당성향 ~30% + 자사주매입), 여기서 나온 내재성장률은 "이 가격이
    정당화되려면 필요한 이익성장률"의 **하한 근사**로 읽어야 한다. 배당성향을
    반영한 정교한 버전은 재투자수익률(ROE) 가정이 추가로 필요해 주관적 입력이
    하나 더 늘어나므로, 실증사례가 쌓이기 전에는 넣지 않는다(Simplicity First).
    """
    return implied_growth_from_fcf_yield(earnings_yield(pe_ratio), r)


def pe_source_divergence(pe_by_source: dict) -> dict:
    """
    ⭐ 이 엔진의 핵심 함수 - IWM 사건을 코드로 만든 것.

    같은 ETF의 P/E가 출처마다 다른 것은 데이터 오류가 아니라 **지수 고유의
    구조적 현상**이다(트레일링 단순평균 vs forward 애널리스트추정 가중, 무이익
    기업 처리방식 차이). 그리고 그 차이가 결론을 뒤집을 만큼 클 수 있다는 것이
    2026-08-06 IWM에서 실증됐다(20.07x '가장 쌈' vs 26x '가장 비쌈').

    반환값: {min, max, spread_abs, spread_relative, sources, warning}
    spread_relative는 최소값 대비 상대괴리(=IWM의 경우 0.295).
    """
    if not pe_by_source:
        raise ValueError("pe_by_source가 비어 있다 - 최소 1개 출처가 필요하다")
    values = list(pe_by_source.values())
    if any(v <= 0 for v in values):
        raise ValueError(f"P/E에 0 이하 값이 있다: {pe_by_source}")

    lo, hi = min(values), max(values)
    spread_relative = (hi - lo) / lo

    warning = None
    if len(values) == 1:
        warning = (
            "[단일 출처 경고] P/E 출처가 1개뿐이라 집계방식 차이로 인한 왜곡을 "
            "검증할 수 없다. IWM 사례에서 같은 ETF의 P/E가 출처에 따라 20.07x와 "
            "26x로 갈려 '가장 쌈'과 '가장 비쌈'이라는 정반대 결론이 나온 적이 "
            "있으므로(2026-08-06 실측), 최소 2개 출처(가능하면 트레일링 1개 + "
            "forward 1개)를 확보할 것."
        )
    elif spread_relative >= PE_DIVERGENCE_WARNING_THRESHOLD:
        warning = (
            f"[P/E 출처 괴리 경고] 출처간 P/E가 {lo:.2f}x ~ {hi:.2f}x로 "
            f"{spread_relative*100:.1f}% 벌어져 있다(임계값 "
            f"{PE_DIVERGENCE_WARNING_THRESHOLD*100:.0f}%). 이 정도 괴리는 판정을 "
            f"뒤집을 수 있다 - IWM이 정확히 이 사례였다. **어느 한 출처의 숫자로 "
            f"단일 결론을 내리지 말 것.** 원인은 대개 지수에 무이익 기업이 많아 "
            f"집계방식(트레일링 단순평균 vs forward 가중)에 따라 값이 달라지는 "
            f"것이므로, pct_unprofitable_constituents를 함께 확인할 것."
        )

    return {
        "sources": dict(pe_by_source),
        "min": lo,
        "max": hi,
        "spread_abs": hi - lo,
        "spread_relative": spread_relative,
        "warning": warning,
    }


def expense_drag(expense_ratio: float, years: int = 10) -> float:
    """
    보수율의 누적 비용(소수). 1 - (1-er)^years.

    ETF에서 이 값은 **유일하게 확실한 마이너스 수익**이다 - 성장률·밸류에이션은
    전부 추정이지만 보수율만은 계약으로 확정돼 있다. VOO(0.03%)와 액티브
    ETF(0.75%)의 10년 누적 차이는 7%p를 넘어 웬만한 Gap 추정치보다 크다.
    """
    if not (0.0 <= expense_ratio < 1.0):
        raise ValueError(f"expense_ratio는 0~1 소수여야 함(받은 값: {expense_ratio})")
    if years <= 0:
        raise ValueError("years는 1 이상이어야 함")
    return 1.0 - (1.0 - expense_ratio) ** years


def concentration_score(top10_weight: float) -> float:
    """상위10종목 비중(소수) -> 0~20. 높을수록 '지수'가 아니라 소수 베팅."""
    if not (0.0 <= top10_weight <= 1.0):
        raise ValueError(f"top10_weight는 0~1 소수여야 함(받은 값: {top10_weight})")
    return _bucket_score(top10_weight, _CONCENTRATION_BUCKETS, ascending=True)


def breadth_score(n_holdings: int) -> float:
    """보유종목 수 -> 0~20. 적을수록 위험."""
    if n_holdings <= 0:
        raise ValueError("n_holdings는 1 이상이어야 함")
    return _bucket_score(n_holdings, _BREADTH_BUCKETS, ascending=False)


def cost_score(expense_ratio: float) -> float:
    """보수율(소수) -> 0~20."""
    if not (0.0 <= expense_ratio < 1.0):
        raise ValueError(f"expense_ratio는 0~1 소수여야 함(받은 값: {expense_ratio})")
    return _bucket_score(expense_ratio, _COST_BUCKETS, ascending=True)


def data_quality_score(pe_spread_relative: float) -> float:
    """P/E 출처간 상대괴리 -> 0~20. IWM 사건의 점수화."""
    if pe_spread_relative < 0:
        raise ValueError("pe_spread_relative는 음수일 수 없음")
    return _bucket_score(pe_spread_relative, _PE_DIVERGENCE_BUCKETS, ascending=True)


def earnings_quality_score(pct_unprofitable: float) -> float:
    """무이익 구성종목 비중(소수) -> 0~20. P/E 집계 왜곡의 근본 원인."""
    if not (0.0 <= pct_unprofitable <= 1.0):
        raise ValueError(
            f"pct_unprofitable은 0~1 소수여야 함(받은 값: {pct_unprofitable})"
        )
    return _bucket_score(pct_unprofitable, _UNPROFITABLE_BUCKETS, ascending=True)


def etf_risk_score(
    top10_weight: float,
    n_holdings: int,
    expense_ratio: float,
    pe_spread_relative: float,
    pct_unprofitable: float = None,
) -> dict:
    """
    ERS(ETF Risk Score) 0~100. 회사 엔진의 DRS와 같은 스케일·같은 산식
    (5개 항목 0~20 평균 x5)이라 `erp_from_drs()`를 그대로 쓸 수 있다.

    pct_unprofitable이 None이면 그 항목을 제외하고 나머지 4개로 평균낸다
    (DRSInputs가 항목 제외를 허용하는 것과 같은 취지). 다만 제외 사실을
    components에 남겨 조용히 관대해지는 일이 없게 한다.
    """
    components = {
        "concentration": concentration_score(top10_weight),
        "breadth": breadth_score(n_holdings),
        "cost": cost_score(expense_ratio),
        "data_quality": data_quality_score(pe_spread_relative),
    }
    excluded = []
    if pct_unprofitable is not None:
        components["earnings_quality"] = earnings_quality_score(pct_unprofitable)
    else:
        excluded.append("earnings_quality")

    score = (sum(components.values()) / len(components)) * 5
    return {"components": components, "excluded": excluded, "score": score}


def fed_model_spread(pe_ratio: float, treasury_yield: float) -> dict:
    """
    이익수익률 - 장기국채금리(=흔히 말하는 Fed 모델 스프레드).

    ⚠️ 이 지표는 학술적으로 논쟁적이다(명목금리와 실질 이익성장을 직접
    비교한다는 비판이 표준적이다). 그래서 이 엔진은 이 값을 **판정에 쓰지
    않고 병기만 한다** - is_insurer의 P/B를 임계값 없이 숫자만 제공하는 것과
    동일한 처리다. 분석자가 직접 해석할 것.
    """
    ey = earnings_yield(pe_ratio)
    return {
        "earnings_yield": ey,
        "treasury_yield": treasury_yield,
        "spread": ey - treasury_yield,
        "caveat": (
            "Fed 모델 스프레드는 명목 국채금리와 이익수익률을 직접 비교하는 "
            "논쟁적 지표다(인플레이션 처리 문제). 판정 근거로 쓰지 말고 참고용 "
            "병기로만 볼 것 - 이 엔진도 판정 계산에 사용하지 않는다."
        ),
    }


def evaluate_valuation_by_source(
    pe_by_source: dict,
    expected_earnings_growth: float,
    r: float,
) -> dict:
    """
    출처별로 내재성장률·Gap·판정을 각각 계산해 **판정이 갈리는지** 본다.

    이 함수가 이 엔진의 결론부다. 회사 엔진에서 `sbc_cross_check`가 SBC 차감
    시나리오를 병기하고 `judgment_flipped`를 보고하는 것과 정확히 같은 구조 -
    다만 여기서는 "어느 데이터 출처를 믿느냐"가 시나리오 축이다.

    expected_earnings_growth: 이 지수의 장기 지속가능 이익성장률(소수).
      회사 분석의 Realistic Growth에 대응하는 자리로, 근거 없이 넣으면 안 된다
      (호출부인 etf_pipeline이 basis 문자열을 필수로 요구한다).
    """
    per_source = {}
    for source, pe in pe_by_source.items():
        ig = implied_growth_from_pe(pe, r)
        gap = expected_earnings_growth - ig
        per_source[source] = {
            "pe_ratio": pe,
            "earnings_yield": earnings_yield(pe),
            "implied_growth": ig,
            "gap": gap,
            "judgment": judgment_from_gap(gap),
        }

    judgments = {v["judgment"] for v in per_source.values()}
    gaps = [v["gap"] for v in per_source.values()]
    return {
        "by_source": per_source,
        "gap_min": min(gaps),
        "gap_max": max(gaps),
        "judgments_seen": sorted(judgments),
        "judgment_flipped_across_sources": len(judgments) > 1,
        "consensus_judgment": judgments.pop() if len(judgments) == 1 else None,
    }


__all__ = [
    "ENGINE_VERSION",
    "PE_DIVERGENCE_WARNING_THRESHOLD",
    "breadth_score",
    "concentration_score",
    "cost_score",
    "data_quality_score",
    "earnings_quality_score",
    "earnings_yield",
    "etf_risk_score",
    "evaluate_valuation_by_source",
    "expense_drag",
    "fed_model_spread",
    "implied_growth_from_pe",
    "pe_source_divergence",
    "erp_from_drs",
]
