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
    growth_anchor_cross_check,
    growth_sensitivity,
    holdings_overlap,
    net_expected_growth,
    pe_source_divergence,
    realized_eps_growth,
    to_nominal_growth,
)

DEFAULT_HOLDING_YEARS = 10
# 성장률 가정 불확실성 기본값(±%p). v3.34에서 도입 - 근거는
# etf_engine.growth_sensitivity() 주석 참고.
DEFAULT_GROWTH_UNCERTAINTY = 0.02


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

    # v3.35: 지수 EPS 실적 시계열(opt-in). 넣으면 실적 CAGR을 계산해 분석자
    # 가정과 대조한다(방향 A - v3.34가 "근본 해결은 이것뿐"이라 기록한 항목).
    # {회계연도: 지수 EPS}. 회사 엔진의 capex_classification처럼 값이 없으면
    # 기존 동작 그대로다.
    realized_eps_by_year: dict = None
    # ⚠️ 단위 필수(v3.35): 공개 지수 EPS 시계열은 실질(real, 인플레 조정)인
    # 경우가 흔한데(multpl.com S&P500 EPS가 그렇다) 분석자의 기대성장률은
    # 명목이다. 그대로 비교하면 인플레이션율만큼 조용히 어긋난다 - RAR 100배
    # 사고와 같은 단위 함정이라 코드로 막는다.
    realized_eps_basis: str = None        # "nominal" | "real"
    inflation_for_conversion: float = None  # realized_eps_basis="real"일 때 필수

    # v3.36: 상위 보유종목 {티커: 비중(소수)}. 넣으면 ETF간 겹침을 측정할 수
    # 있다(portfolio_overlap_report). 개별 ETF 판정에는 영향을 주지 않는다 -
    # 겹침은 본질적으로 '여러 개를 같이 살 때'의 문제이기 때문이다.
    top10_holdings: dict = None
    return_1y: float = None
    return_ytd: float = None
    holding_years: int = DEFAULT_HOLDING_YEARS
    growth_uncertainty: float = DEFAULT_GROWTH_UNCERTAINTY
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
        if self.realized_eps_by_year:
            if self.realized_eps_basis not in ("nominal", "real"):
                raise ValueError(
                    'realized_eps_by_year를 넣으면 realized_eps_basis를 '
                    '"nominal" 또는 "real"로 명시해야 한다(v3.35). 공개 지수 EPS '
                    '시계열은 실질(인플레 조정) 값인 경우가 흔한데(multpl.com의 '
                    'S&P500 EPS가 "constant dollars" 기준) 기대성장률은 명목이라, '
                    '단위를 밝히지 않으면 인플레이션율만큼 조용히 어긋난다.'
                )
            if self.realized_eps_basis == "real" and self.inflation_for_conversion is None:
                raise ValueError(
                    'realized_eps_basis="real"이면 inflation_for_conversion(소수)이 '
                    '필수다 - 실질 CAGR을 명목으로 환산해야 명목 기대성장률과 '
                    '비교할 수 있다.'
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

    # v3.34: 보수율을 성장률에서 직접 차감한다(ERS에서는 제거해 이중반영 방지).
    net_growth = net_expected_growth(
        inputs.expected_earnings_growth, inputs.expense_ratio
    )
    valuation = evaluate_valuation_by_source(inputs.pe_by_source, net_growth, r)

    # v3.34: 성장률 가정이 결과를 사실상 단독 결정한다는 자체 진단(2026-08-06)에
    # 대한 대응. 가장 비싼 P/E(보수적)를 기준으로 ±uncertainty 밴드를 계산해
    # 판정이 그 안에서 유지되는지 본다.
    # v3.35(방향 A): 지수 EPS 실적이 있으면 분석자 가정을 관측값과 대조한다.
    # 자동으로 덮어쓰지 않고 병기·경고만 한다(insurer_cross_check와 동일 원칙).
    anchor = None
    if inputs.realized_eps_by_year:
        realized = realized_eps_growth(inputs.realized_eps_by_year)
        realized["basis"] = inputs.realized_eps_basis
        if inputs.realized_eps_basis == "real":
            # 실질 -> 명목 환산(위 단위 가드 참고). 원 실질값도 함께 남긴다.
            realized["cagr_real"] = realized["cagr"]
            realized["inflation_used"] = inputs.inflation_for_conversion
            realized["cagr"] = to_nominal_growth(
                realized["cagr"], inputs.inflation_for_conversion
            )
            data_limitations.append(
                f"[EPS 단위 환산] 지수 EPS가 실질(real) 기준이라 실질 CAGR "
                f"{realized['cagr_real']*100:.2f}%를 인플레이션 "
                f"{inputs.inflation_for_conversion*100:.2f}% 가정으로 명목 "
                f"{realized['cagr']*100:.2f}%로 환산해 비교했다. 인플레이션 가정이 "
                f"틀리면 앵커 자체가 그만큼 어긋난다."
            )
        anchor = growth_anchor_cross_check(
            inputs.expected_earnings_growth, realized
        )
        if anchor["warning"]:
            data_limitations.append(anchor["warning"])
    else:
        data_limitations.append(
            "[성장률 앵커 없음] 지수 EPS 실적 시계열(realized_eps_by_year)이 없어 "
            "기대성장률이 순수 분석자 추정이다. Gap은 이 추정에 1:1로 좌우되므로 "
            "(v3.34 진단) 이 ETF의 Gap을 실적 앵커가 있는 ETF와 나란히 놓고 "
            "순위를 매기지 말 것 - 비교하려면 required_growth.breakeven을 쓸 것."
        )

    sensitivity = growth_sensitivity(
        divergence["max"], r, net_growth, inputs.growth_uncertainty
    )
    if not sensitivity["robust"]:
        data_limitations.append(
            f"[성장률 가정 취약] 기대성장률을 ±{inputs.growth_uncertainty*100:.1f}%p만 "
            f"달리 잡아도 판정이 '{sensitivity['judgment_low']}' <-> "
            f"'{sensitivity['judgment_high']}'로 바뀐다. 이 ETF의 판정은 엔진 계산이 "
            f"아니라 **분석자의 성장률 가정**이 결정하고 있다는 뜻이므로, Gap 수치를 "
            f"근거로 순위를 매기지 말고 아래 required_growth(시장이 요구하는 성장률)를 "
            f"기준으로 판단할 것."
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
            "expense_ratio_deducted": inputs.expense_ratio,
            "net_expected_growth": net_growth,
            "basis": inputs.expected_earnings_growth_basis,
            # v3.35: 이 성장률이 관측 기반인지 순수 추정인지 명시한다.
            # 두 유형을 섞어 순위를 매기면 사과와 오렌지를 비교하는 셈이라,
            # 라벨을 결과에 남겨 그 사실이 드러나게 한다.
            "basis_type": "observed_anchored" if anchor else "analyst_estimate",
            "anchor_cross_check": anchor,
            "sensitivity": sensitivity,
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

    ⚠️ **신뢰할 수 없는 순위를 앞에 두지 않는다.** 두 종류의 취약성을 모두
    뒤로 보낸다:
      1) 판정이 P/E 출처간에 갈리는 경우(IWM) - Gap이 어느 출처를 믿느냐에 달림
      2) 판정이 성장률 가정 ±band 안에서 갈리는 경우(v3.34 신규) - Gap이 엔진
         계산이 아니라 분석자 타이핑에 달림

    ⚠️⚠️ **이 정렬 자체를 투자 순위로 쓰지 말 것**(v3.34 자체 진단): 7개 ETF의
    성장률 가정을 전부 8%로 통일해봤더니 순위가 거의 정반대로 뒤집혔다
    (XLK 2위->7위, XLE 7위->2위). 즉 Gap 기반 순위는 분석자의 성장률 가정을
    되비추는 거울에 가깝다. 객관적으로 비교 가능한 것은 각 ETF의
    `required_growth.breakeven`(시장이 요구하는 성장률)뿐이며, 그것을 각
    지수의 실제 성장 가능성과 대조하는 일은 사람이 해야 한다.
    """
    def sort_key(res):
        v = res["valuation"]
        fragile = (v["judgment_flipped_across_sources"]
                   or not res["growth"]["sensitivity"]["robust"])
        return (fragile, -v["gap_min"])

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
    """
    상대비교 결과를 사람이 읽는 표로.

    v3.34에서 열 구성을 바꿨다: **객관적 값(시장이 요구하는 성장률)을 앞에,
    주관에 오염된 값(Gap)을 뒤에** 둔다. v3.33 표는 Gap을 가운데 두어 마치
    엔진이 계산한 결론처럼 보이게 했는데, 실제로는 분석자의 성장률 가정이
    그 Gap을 거의 그대로 결정하고 있었다.
    """
    lines = []
    head = (f"{'티커':6} {'추종':20} {'ERS':>5} {'P/E범위':>13} "
            f"{'시장요구성장':>13} {'저평가되려면':>13} "
            f"{'가정성장(순)':>13} {'Gap':>16} 신뢰도")
    lines.append(head)
    lines.append("-" * 132)
    for res in results:
        v, d, g = res["valuation"], res["pe_divergence"], res["growth"]
        # 보수적 기준 = 가장 비싼 P/E(=가장 높은 내재성장률 요구)
        worst = max(v["by_source"].values(), key=lambda s: s["implied_growth"])
        req = worst["required_growth"]

        flags = []
        if v["judgment_flipped_across_sources"]:
            flags.append("출처갈림")
        if not g["sensitivity"]["robust"]:
            flags.append("성장가정취약")
        trust = "⚠️" + "+".join(flags) if flags else "일관"

        pe_range = "{:.1f}~{:.1f}x".format(d["min"], d["max"])
        breakeven = "{:.2f}%".format(req["breakeven"] * 100)
        need = "{:.2f}%+".format(req["for_undervalued"] * 100)
        assumed = "{:.2f}%".format(g["net_expected_growth"] * 100)
        gap_range = "{:+.2f}~{:+.2f}%p".format(
            v["gap_min"] * 100, v["gap_max"] * 100)

        lines.append(
            f"{res['meta']['ticker']:6} {res['meta']['tracks'][:20]:20} "
            f"{res['ers']['score']:5.1f} {pe_range:>13} {breakeven:>13} "
            f"{need:>13} {assumed:>13} {gap_range:>16} {trust}"
        )
    return "\n".join(lines)


# 겹침이 이 수준을 넘으면 "함께 보유 시 분산 효과 없음" 경고를 띄운다.
# 2026-08-07 실측 top10 기준 VOO∩QQQ 34.5%p / QQQ∩XLK 32.0%p / VOO∩XLK 23.2%p로,
# 광범위지수와 섹터ETF를 같이 담는 흔한 조합이 전부 20%p를 넘었다. top10만
# 본 하한값이 이 정도라는 뜻이므로 임계값을 그보다 낮게 잡을 이유가 없어
# 20%p로 둔다 - ERS 임계값과 마찬가지로 **검증된 값이 아닌 관측 기반 시작점**이다.
OVERLAP_WARNING_THRESHOLD = 0.20


def portfolio_overlap_report(results: list) -> dict:
    """
    여러 ETF를 **함께 보유할 때** 생기는 중복노출을 보고한다.

    개별 `run_etf_analysis()`는 ETF를 하나씩만 보므로 이 위험을 구조적으로 볼 수
    없다 - "VOO+QQQ+XLK로 분산했다"고 믿는 투자자가 실제로는 같은 메가캡을 세 번
    사고 있는 상황을 잡아내지 못한다. 이 함수가 그 빈자리를 채운다.

    `top10_holdings`가 없는 ETF는 조용히 건너뛰지 않고 `skipped`에 남긴다
    (데이터 없음을 '겹침 없음'으로 오독하면 안 되기 때문).
    """
    have = [r for r in results if r["inputs"].get("top10_holdings")]
    skipped = [r["meta"]["ticker"] for r in results
               if not r["inputs"].get("top10_holdings")]

    pairs = []
    for i in range(len(have)):
        for j in range(i + 1, len(have)):
            a, b = have[i], have[j]
            ov = holdings_overlap(a["inputs"]["top10_holdings"],
                                  b["inputs"]["top10_holdings"])
            ov["pair"] = (a["meta"]["ticker"], b["meta"]["ticker"])
            ov["warning"] = None
            if ov["shared_weight"] >= OVERLAP_WARNING_THRESHOLD:
                ov["warning"] = (
                    f"[중복노출 경고] {ov['pair'][0]}와 {ov['pair'][1]}는 상위 "
                    f"보유종목만으로도 {ov['shared_weight']*100:.1f}%p가 겹친다"
                    f"(공통 {ov['n_common']}종목: {', '.join(ov['common_tickers'])}). "
                    f"둘을 함께 보유하면 분산이 아니라 **같은 종목을 두 번 사는 것**에 "
                    f"가깝다. top10만 본 하한값이므로 실제 겹침은 이보다 크다."
                )
            pairs.append(ov)

    pairs.sort(key=lambda x: -x["shared_weight"])
    return {
        "pairs": pairs,
        "skipped_no_holdings": skipped,
        "threshold": OVERLAP_WARNING_THRESHOLD,
        "note": (
            "shared_weight는 공통 종목별 min(비중) 합 = 두 ETF가 공유하는 최소 "
            "공통 노출. top10 기준이라 실제 겹침의 하한이다."
        ),
    }


def format_overlap_table(report: dict) -> str:
    lines = ["ETF 쌍          공통종목수   겹침(하한)   경고"]
    lines.append("-" * 66)
    for ov in report["pairs"]:
        flag = "⚠️ 분산효과 없음" if ov["warning"] else ""
        pair = f"{ov['pair'][0]}+{ov['pair'][1]}"
        lines.append(
            f"{pair:14} {ov['n_common']:>8}   {ov['shared_weight']*100:9.1f}%p   {flag}")
    if report["skipped_no_holdings"]:
        lines.append("")
        lines.append("보유종목 데이터 없어 측정 제외: "
                     + ", ".join(report["skipped_no_holdings"])
                     + "  (겹침 없음이 아니라 '모름'이다)")
    return "\n".join(lines)
