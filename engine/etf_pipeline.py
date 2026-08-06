"""
ETF Analysis Pipeline (v3.33 신규, 2026-08-06)

`engine/pipeline.py`가 개별 기업에 대해 하는 일을 ETF에 대해 한다:
체인을 한 곳에서만 배선하고, 입력·중간값·결과를 전부 ledger JSON으로 남겨
재현과 대조검증이 가능하게 만든다.

**왜 회사 pipeline에 끼워넣지 않고 별도 파일인가**: `AnalysisInputs`는
revenue/operating_income/OCF/capex 시계열을 필수로 요구하는데 ETF에는 그런
게 존재하지 않는다. 억지로 하나의 dataclass에 합치면 절반이 항상 None인
필드가 되고, `run_analysis()` 본문이 "ETF면 이 분기, 회사면 저 분기"로
갈라진다 - CLAUDE.md의 Simplicity First가 경고하는 "강제 분기보다 opt-in"
원칙에 정면으로 어긋난다. 대신 **공유 가능한 원시함수는 전부 재사용**한다
(etf_engine 상단 주석 참고).

ledger 저장 위치가 회사와 다르다(`ledger_etf/`). 같은 디렉터리에 쓰면
`tests/test_ledger_integrity.py`가 회사 ledger 스키마(judgment/
sensitivity_check 키 존재)를 기대하고 파싱하다 깨진다 - 스키마가 다른
두 종류의 기록을 한 폴더에 섞지 않는다.
"""

import json
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone

from engine.etf_engine import (
    ENGINE_VERSION,
    PE_DIVERGENCE_WARNING_THRESHOLD,
    erp_from_drs,
    etf_risk_score,
    evaluate_valuation_by_source,
    expense_drag,
    fed_model_spread,
    pe_source_divergence,
)

DEFAULT_HOLDING_YEARS = 10


@dataclass
class ETFInputs:
    """
    ETF 1건 분석에 필요한 모든 입력. 여기 담긴 값만으로 결과가 100% 재현되어야 한다.

    단위 규약(v3.19 100배 사고의 교훈): 수익률·성장률·보수율·비중은 전부 **소수**.
    P/E만 배수 그대로.
    """

    ticker: str
    name: str
    tracks: str                      # 추종 지수/섹터 (예: "S&P 500")

    # ⭐ P/E는 단일 스칼라가 아니라 {출처명: P/E} - IWM 사건 때문이다.
    # 최소 2개 출처(트레일링/forward)를 권장하며, 1개면 경고가 붙는다.
    pe_by_source: dict

    expense_ratio: float             # 소수 (0.0003 = 0.03%)
    n_holdings: int
    top10_weight: float              # 소수 (0.59 = 59%)

    risk_free_rate: float            # 소수, 장기국채금리

    # 회사 분석의 Realistic Growth에 대응하는 자리. 지수의 장기 지속가능
    # 이익성장률로, **근거 없이 넣으면 실행을 거부한다**(회사 엔진이
    # subjective_input_basis를 필수화한 것과 동일 취지).
    expected_earnings_growth: float
    expected_earnings_growth_basis: str

    dividend_yield: float = None
    pct_unprofitable_constituents: float = None   # 소수, 모르면 None
    return_1y: float = None
    return_ytd: float = None
    holding_years: int = DEFAULT_HOLDING_YEARS
    currency: str = "USD"
    price_at_analysis: float = None
    data_sources: list = field(default_factory=list)

    # 반증조건 - 회사 엔진의 falsification_conditions와 동일 취지(opt-in,
    # 과거 분석에 소급 작성 금지).
    falsification_conditions: str = None

    def __post_init__(self):
        if not self.pe_by_source:
            raise ValueError(
                "pe_by_source 필수(v3.33): ETF의 P/E는 출처마다 집계방식이 달라 "
                "값이 크게 갈릴 수 있다(IWM 실측 20.07x vs 26x). 단일 스칼라가 "
                "아니라 {출처명: P/E} 형태로 넣을 것."
            )
        if not (self.expected_earnings_growth_basis
                and self.expected_earnings_growth_basis.strip()):
            raise ValueError(
                "expected_earnings_growth_basis 필수(v3.33): 지수의 장기 이익성장률은 "
                "추정치이며 Gap을 통째로 좌우한다. 근거(과거 지수 EPS CAGR/애널리스트 "
                "바텀업 추정/명목GDP 프록시 등)를 남기지 않으면 종목간 비교가 "
                "불가능해진다 - 회사 엔진의 subjective_input_basis와 동일 취지."
            )
        if self.n_holdings <= 0:
            raise ValueError("n_holdings는 1 이상이어야 함")
        if not (0.0 <= self.top10_weight <= 1.0):
            raise ValueError("top10_weight는 0~1 소수여야 함")
        if not (0.0 <= self.expense_ratio < 1.0):
            raise ValueError("expense_ratio는 0~1 소수여야 함")
        # 보수율을 퍼센트로 잘못 넣는 실수(0.03%를 0.03으로 오인) 방지.
        # 실제 ETF 보수율이 3%에 이르는 경우는 사실상 없고, 하필 0.03을 그대로
        # 넣는 것이 이 실수의 대표 사례라 경계값을 포함해(>=) 막는다.
        if self.expense_ratio >= 0.03:
            raise ValueError(
                f"expense_ratio={self.expense_ratio}가 3% 이상이다. 퍼센트 숫자를 "
                f"소수 자리에 넣은 것으로 보인다(0.03% -> 0.0003). 정말 3% 이상 "
                f"보수율이면 이 가드를 명시적으로 완화할 것."
            )


def run_etf_analysis(inputs: ETFInputs) -> dict:
    """
    ETF 1건의 전체 파이프라인을 실행하고 모든 중간값을 담은 dict를 반환한다.

    회사 `run_analysis()`와 같은 원칙:
      - 단위 처리를 여기서 전부 책임진다(호출부가 헷갈릴 여지 없음)
      - 판정을 자동으로 하나로 좁히지 않는다 - P/E 출처별로 병기하고
        갈리면 갈린다고 보고한다
    """
    data_limitations = []

    divergence = pe_source_divergence(inputs.pe_by_source)
    if divergence["warning"]:
        data_limitations.append(divergence["warning"])

    ers = etf_risk_score(
        top10_weight=inputs.top10_weight,
        n_holdings=inputs.n_holdings,
        expense_ratio=inputs.expense_ratio,
        pe_spread_relative=divergence["spread_relative"],
        pct_unprofitable=inputs.pct_unprofitable_constituents,
    )
    if ers["excluded"]:
        data_limitations.append(
            f"[ERS 항목 제외] {', '.join(ers['excluded'])} 항목을 구하지 못해 "
            f"나머지 {len(ers['components'])}개로만 위험점수를 산출했다. 특히 "
            f"earnings_quality(무이익 구성종목 비중)는 P/E 출처 괴리의 근본 "
            f"원인이라, 이 값이 없으면 괴리가 큰 ETF의 위험이 과소평가될 수 있다."
        )

    erp = erp_from_drs(ers["score"])
    r = inputs.risk_free_rate + erp

    valuation = evaluate_valuation_by_source(
        inputs.pe_by_source, inputs.expected_earnings_growth, r
    )

    if valuation["judgment_flipped_across_sources"]:
        data_limitations.append(
            f"[판정 불일치] P/E 출처에 따라 판정이 갈린다"
            f"({' / '.join(valuation['judgments_seen'])}). Gap 범위 "
            f"{valuation['gap_min']*100:+.2f}%p ~ {valuation['gap_max']*100:+.2f}%p. "
            f"**단일 결론을 내리지 말 것** - 어느 출처의 집계방식이 이 지수에 "
            f"적합한지 먼저 판단해야 한다(무이익 기업이 많은 소형주 지수는 "
            f"트레일링 단순평균이 특히 왜곡되기 쉽다). IWM이 실제 사례다."
        )
    elif divergence["spread_relative"] >= PE_DIVERGENCE_WARNING_THRESHOLD:
        # ⚠️ 2026-08-06 테스트에서 발견한 중요한 성질: P/E 괴리는 Gap에 **일정한
        # 폭**을 만들지만(IWM의 경우 약 1.16%p), 그 폭이 ±5%p 판정 경계를
        # 가로지르는지는 r과 성장률이 어디 놓이느냐에 달려 있다. 실제로 같은
        # IWM 데이터가 r=0.09에서는 판정이 갈리고 r=0.1081에서는 안 갈렸다.
        # 따라서 **judgment_flipped=False를 '문제 없음'으로 읽으면 안 된다** -
        # 데이터 신뢰도 문제는 그대로 남아 있고, 입력이 조금만 달라져도
        # 판정이 갈릴 수 있다는 뜻이다. 이 경우를 조용히 넘기지 않는다.
        data_limitations.append(
            f"[판정 우연 일치 주의] P/E 출처 괴리가 "
            f"{divergence['spread_relative']*100:.1f}%로 큰데도 이번 입력에서는 "
            f"판정이 '{valuation['consensus_judgment']}'로 일치했다. 이는 Gap "
            f"범위({valuation['gap_min']*100:+.2f}%p ~ "
            f"{valuation['gap_max']*100:+.2f}%p)가 마침 같은 판정 구간 안에 들어온 "
            f"결과일 뿐, 데이터 신뢰도가 확보됐다는 뜻이 아니다 - 할인율이나 "
            f"성장률 가정이 조금만 달라져도 판정이 갈릴 수 있다."
        )

    drag = expense_drag(inputs.expense_ratio, inputs.holding_years)
    # 보수율은 '확실한 마이너스 알파'라 Gap과 같은 축에서 비교할 수 있게
    # 연율 기준으로도 병기한다(누적 drag를 보유기간으로 나눈 근사가 아니라
    # 보수율 그 자체가 연율이므로 그대로 쓴다).
    if inputs.expense_ratio >= 0.0025:
        data_limitations.append(
            f"[보수율 부담] 연 보수율 {inputs.expense_ratio*100:.2f}%는 "
            f"{inputs.holding_years}년 보유 시 누적 {drag*100:.2f}%의 확정 비용이다. "
            f"Gap 추정치는 불확실하지만 이 비용은 계약으로 확정돼 있다 - "
            f"저비용 대안(광범위지수 ETF는 0.03%대)과 반드시 비교할 것."
        )

    fed = fed_model_spread(divergence["min"], inputs.risk_free_rate)

    return {
        "meta": {
            "ticker": inputs.ticker,
            "name": inputs.name,
            "tracks": inputs.tracks,
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
            "engine_version": ENGINE_VERSION,
            "analysis_type": "etf",
            "data_sources": inputs.data_sources,
            "falsification_conditions": inputs.falsification_conditions,
            "price_at_analysis": inputs.price_at_analysis,
            "currency": inputs.currency,
        },
        "data_limitations": data_limitations,
        "inputs": asdict(inputs),
        "pe_divergence": divergence,
        "ers": ers,
        "discount_rate": {"rf": inputs.risk_free_rate, "erp": erp, "r": r},
        "growth": {
            "expected_earnings_growth": inputs.expected_earnings_growth,
            "basis": inputs.expected_earnings_growth_basis,
        },
        "valuation": valuation,
        "cost": {
            "expense_ratio": inputs.expense_ratio,
            "holding_years": inputs.holding_years,
            "cumulative_drag": drag,
        },
        "fed_model": fed,
        "performance": {
            "return_1y": inputs.return_1y,
            "return_ytd": inputs.return_ytd,
            "dividend_yield": inputs.dividend_yield,
        },
    }


def compare_etfs(results: list) -> list:
    """
    여러 ETF 결과를 상대비교용으로 정렬한다.

    ⚠️ **판정이 출처간에 갈린 ETF는 순위를 신뢰할 수 없으므로 뒤로 보낸다** -
    Gap이 아무리 좋아 보여도 그 Gap 자체가 어느 출처를 믿느냐에 달려 있기
    때문이다(IWM이 정확히 이 경우: 한 출처로는 최상위, 다른 출처로는 최하위).
    정렬 키는 (판정불일치 여부, -보수적 Gap) - 보수적 Gap은 출처별 Gap 중
    최솟값으로, 가장 비싼 P/E를 믿었을 때의 Gap이다.
    """
    def sort_key(res):
        v = res["valuation"]
        return (v["judgment_flipped_across_sources"], -v["gap_min"])

    return sorted(results, key=sort_key)


def save_etf_ledger(result: dict, ledger_dir: str = "ledger_etf") -> str:
    """
    ETF 분석 결과 전체를 JSON으로 저장한다.

    회사 ledger(`ledger/`)와 **디렉터리를 분리한다** - 스키마가 다르고,
    `tests/test_ledger_integrity.py`가 회사 ledger 구조를 가정하고 전수
    파싱하기 때문이다.
    """
    os.makedirs(ledger_dir, exist_ok=True)
    date = result["meta"]["analyzed_at"][:10]
    path = os.path.join(ledger_dir, f"{result['meta']['ticker']}_{date}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2, default=str)
    return path


def format_comparison_table(results: list) -> str:
    """상대비교 결과를 사람이 읽는 표로."""
    lines = []
    head = (f"{'티커':6} {'추종':22} {'ERS':>6} {'P/E범위':>14} "
            f"{'내재성장':>16} {'Gap범위':>18} {'보수율':>7} 판정")
    lines.append(head)
    lines.append("-" * 118)
    for res in results:
        v, d = res["valuation"], res["pe_divergence"]
        igs = [s["implied_growth"] for s in v["by_source"].values()]
        judgment = (v["consensus_judgment"]
                    if not v["judgment_flipped_across_sources"]
                    else "⚠️출처간 불일치: " + " / ".join(v["judgments_seen"]))
        pe_range = f"{d['min']:.2f}~{d['max']:.2f}x"
        ig_range = f"{min(igs)*100:.2f}~{max(igs)*100:.2f}%"
        gap_range = f"{v['gap_min']*100:+.2f}~{v['gap_max']*100:+.2f}%p"
        lines.append(
            f"{res['meta']['ticker']:6} {res['meta']['tracks'][:22]:22} "
            f"{res['ers']['score']:6.1f} {pe_range:>14} {ig_range:>16} "
            f"{gap_range:>18} {res['cost']['expense_ratio']*100:6.2f}% {judgment}"
        )
    return "\n".join(lines)
