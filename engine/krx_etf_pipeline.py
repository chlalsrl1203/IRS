"""
KRX 래퍼 ETF 분석 파이프라인 (v3.38 신설, 2026-08-07)

`engine/etf_pipeline.py`가 미국 상장 ETF에 대해 하는 일을, 그 미국 ETF를
추종하는 **국내 상장 ETF**에 대해 한다. 다만 밸류에이션 자체를 다시 계산하지
않는다 - `engine/krx_etf_engine.py` 모듈독스트링에 적은 대로, 같은 지수를
추종하는 국내 ETF의 P/E·성장률·위험점수는 이미 계산된 미국 원본 결과를 그대로
재사용하고 `run_etf_analysis()`를 다시 호출하는 방식으로 파이프라인을 100%
재사용한다.

ledger 저장 위치는 `ledger_krx/`로 회사(`ledger/`)·미국 ETF(`ledger_etf/`)와
전부 분리한다 - 세 스키마가 서로 다르고, `tests/test_ledger_integrity.py`가
디렉터리별 스키마를 가정하고 전수 파싱하기 때문이다.
"""

import json
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone

from engine.etf_engine import ENGINE_VERSION, holdings_overlap
from engine.etf_pipeline import ETFInputs, OVERLAP_WARNING_THRESHOLD, run_etf_analysis
from engine.krx_etf_engine import expense_ratio_delta, hedge_cost_warning


@dataclass
class KRXWrapperInputs:
    """
    국내 상장 래퍼 ETF 1건의 입력. 밸류에이션 입력(P/E·성장률 등)은 여기 담지
    않는다 - `run_krx_wrapper_analysis()`가 `us_result`에서 그대로 가져온다.
    """

    krx_ticker: str
    krx_name: str

    # ⭐ 재사용의 전제조건 - 정말 같은 지수를 추종하는지 근거를 남긴다.
    # "TIGER 미국배당다우존스"가 다우존스30이 아니라 전혀 다른 배당지수를
    # 추종하는 걸 조사 중 실제로 확인했다 - 이름만 보고 재사용하면 안 된다.
    tracks_same_index_as: str
    us_reference_ticker: str          # 재사용할 미국 원본 ETF 티커(예: "VOO")

    expense_ratio: float              # 국내 상장분 자체의 총보수(소수)
    hedged: bool
    listed_date: str                  # "YYYY-MM-DD" (미확인이면 "미확인")

    # 순자산총액(원 단위 그대로 - 억원 아님). None 허용(v3.38 후반 완화) - 밸류에이션과
    # 무관한 정보성 필드라 검색으로 못 찾았을 때 억지로 숫자를 만들어 넣기보다
    # None으로 정직하게 남긴다(listed_date="미확인"과 같은 취급). None인 항목은
    # 비교표에서 "미확인"으로 표시되고 비용 정렬에서 후순위로 밀린다.
    aum_krw: float = None

    data_sources: list = field(default_factory=list)

    # 레버리지/인버스/커버드콜/액티브 등은 이 재사용 전제가 깨진다 - "plain"만 허용.
    product_type: str = "plain"

    estimated_hedge_carry: float = None   # opt-in, hedge_cost_warning 참고
    currency: str = "KRW"
    price_at_analysis: float = None
    falsification_conditions: str = None

    def __post_init__(self):
        if not (self.tracks_same_index_as and self.tracks_same_index_as.strip()):
            raise ValueError(
                "tracks_same_index_as 필수(v3.38): 국내 상장 ETF가 미국 원본과 "
                "정말 같은 지수를 추종하는지 근거를 남겨야 한다. 상품명이 비슷해도 "
                "실제로는 다른 지수인 경우가 있다(TIGER 미국배당다우존스가 "
                "다우존스30이 아니라 Dow Jones U.S. Dividend 100을 추종하는 것이 "
                "실제 사례) - 기초지수 원문을 확인하고 근거를 적을 것."
            )
        if not (self.us_reference_ticker and self.us_reference_ticker.strip()):
            raise ValueError("us_reference_ticker 필수 - 재사용할 미국 원본 ETF 티커")
        if self.product_type != "plain":
            raise ValueError(
                f'product_type="{self.product_type}"는 지원하지 않는다(v3.38). '
                f'레버리지/인버스/커버드콜/액티브 상품은 기초지수를 그대로 복제하지 '
                f'않아 "미국 원본 결과 재사용" 전제 자체가 깨진다 - 이 파이프라인의 '
                f'대상이 아니다.'
            )
        if self.expense_ratio < 0 or self.expense_ratio >= 0.03:
            raise ValueError(
                f"expense_ratio={self.expense_ratio}가 범위를 벗어났다(0~3% 미만 "
                f"소수여야 함) - 퍼센트 숫자를 그대로 넣은 것으로 보인다."
            )
        if self.aum_krw is not None and self.aum_krw < 0:
            raise ValueError("aum_krw는 원 단위 양수여야 함(억원 단위로 넣지 말 것)")


def run_krx_wrapper_analysis(inputs: KRXWrapperInputs, us_result: dict) -> dict:
    """
    `us_result`: 미국 원본 ETF를 `run_etf_analysis()`로 분석한 결과 dict
    (예: VOO 분석 결과). P/E·성장률·위험점수 계산에 필요한 입력을 전부 여기서
    그대로 복사해온다 - 국내 상장분을 위해 다시 타이핑하지 않는다(전사 오류 방지).

    바뀌는 것은 딱 하나 - `expense_ratio`(국내 상장분 자체의 총보수). 나머지는
    ticker/name/화폐 표시 같은 메타정보만 국내 상장분 것으로 바꾼다.
    """
    us_inputs = us_result["inputs"]

    # ledger JSON을 왕복하면 dict 키가 전부 문자열로 바뀐다(JSON 객체 키는
    # 문자열만 허용) - realized_eps_by_year는 연도(int)를 키로 기대하므로
    # 여기서 되돌린다. 이 변환을 빠뜨리면 realized_eps_growth()가 "2014"-"2015"를
    # 계산하려다 TypeError를 낸다(정수 뺄셈 기대).
    realized_eps_by_year = us_inputs.get("realized_eps_by_year")
    if realized_eps_by_year:
        realized_eps_by_year = {int(y): v for y, v in realized_eps_by_year.items()}

    wrapped = ETFInputs(
        ticker=inputs.krx_ticker,
        name=inputs.krx_name,
        tracks=us_result["meta"]["tracks"],
        pe_by_source=us_inputs["pe_by_source"],
        expense_ratio=inputs.expense_ratio,
        n_holdings=us_inputs["n_holdings"],
        top10_weight=us_inputs["top10_weight"],
        risk_free_rate=us_inputs["risk_free_rate"],
        expected_earnings_growth=us_inputs["expected_earnings_growth"],
        expected_earnings_growth_basis=(
            us_inputs["expected_earnings_growth_basis"]
            + f" [v3.38: {us_result['meta']['ticker']} 분석"
            f"({us_result['meta']['analyzed_at'][:10]})에서 그대로 재사용 - "
            f"같은 주식 바스켓이라 P/E·성장률은 화폐 표시와 무관]"
        ),
        dividend_yield=us_inputs.get("dividend_yield"),
        pct_unprofitable_constituents=us_inputs.get("pct_unprofitable_constituents"),
        realized_eps_by_year=realized_eps_by_year,
        realized_eps_basis=us_inputs.get("realized_eps_basis"),
        inflation_for_conversion=us_inputs.get("inflation_for_conversion"),
        top10_holdings=None,  # 겹침 측정은 미국 원본 티커 기준으로 이미 하므로 중복 방지
        holding_years=us_inputs.get("holding_years", 10),
        growth_uncertainty=us_inputs.get("growth_uncertainty", 0.02),
        currency=inputs.currency,
        price_at_analysis=inputs.price_at_analysis,
        data_sources=inputs.data_sources,
        falsification_conditions=inputs.falsification_conditions,
    )
    result = run_etf_analysis(wrapped)

    result["meta"]["engine_version"] = ENGINE_VERSION
    result["meta"]["analysis_type"] = "krx_wrapper"
    result["meta"]["wrapper_of"] = {
        "us_reference_ticker": inputs.us_reference_ticker,
        "us_analyzed_at": us_result["meta"]["analyzed_at"],
        "tracks_same_index_as": inputs.tracks_same_index_as,
    }
    result["wrapper"] = {
        "expense_ratio": inputs.expense_ratio,
        "expense_ratio_delta_vs_us": expense_ratio_delta(
            inputs.expense_ratio, us_inputs["expense_ratio"]
        ),
        "hedged": inputs.hedged,
        # v3.40 버그수정: 이 값이 hedge_cost_warning() 문구를 만드는 데만 쓰이고
        # 결과 dict에는 저장되지 않아, 다운스트림 스크립트(rank_krx_etfs_
        # 2026_08_08.py)가 "캐리비용이 실제로 병기됐는지"를 경고 문자열
        # 파싱 없이는 알 수 없었다 - 구조화된 필드로 명시.
        "estimated_hedge_carry": inputs.estimated_hedge_carry,
        "aum_krw": inputs.aum_krw,
        "listed_date": inputs.listed_date,
    }

    hedge_warn = hedge_cost_warning(inputs.hedged, inputs.estimated_hedge_carry)
    if hedge_warn:
        result["data_limitations"].append(hedge_warn)
    result["data_limitations"].append(
        f"[래퍼 재사용] 이 결과의 P/E·성장률·위험점수는 {inputs.us_reference_ticker} "
        f"분석({us_result['meta']['analyzed_at'][:10]} 기준)을 그대로 재사용했다 - "
        f"국내 상장 ETF 자체의 기초자산을 재평가한 것이 아니다. 원본 분석이 오래되면 "
        f"이 결과도 함께 낡아진다."
    )
    return result


def compare_krx_wrappers(results: list) -> dict:
    """
    **같은 지수를 추종하는** 국내 상장 ETF끼리만 비교한다(`us_reference_ticker`
    기준으로 그룹핑). 밸류에이션(Gap)은 그룹 내에서 전부 동일하다 - 같은 미국
    원본을 재사용했기 때문이다. 따라서 그룹 내 순위는 **밸류에이션이 아니라
    비용·유동성**으로만 매긴다: 총보수가 낮을수록, 순자산이 클수록 우선한다.

    ⚠️ 이 정렬을 "어느 게 더 저평가됐나"로 읽으면 안 된다 - 그룹 내에서는
    전부 같은 Gap을 갖는다. 이 함수가 답하는 질문은 "같은 지수를 사려면 어느
    상품이 더 저렴하고 안전한가"이다.
    """
    groups = {}
    for res in results:
        key = res["meta"]["wrapper_of"]["us_reference_ticker"]
        groups.setdefault(key, []).append(res)

    for key in groups:
        # aum_krw가 None(미확인)인 항목은 순자산 비교에서 최하위로 밀린다 -
        # "0원"으로 취급하지 않는다(그러면 최하위가 아니라 최상위로 잘못 밀릴 수
        # 있는 부호 함정이 있다. -None은 TypeError라 아예 이렇게 방지한다).
        groups[key].sort(key=lambda r: (
            r["wrapper"]["expense_ratio"],
            r["wrapper"]["aum_krw"] is None,
            -(r["wrapper"]["aum_krw"] or 0),
        ))

    return groups


def save_krx_ledger(result: dict, ledger_dir: str = "ledger_krx") -> str:
    os.makedirs(ledger_dir, exist_ok=True)
    date = result["meta"]["analyzed_at"][:10]
    path = os.path.join(ledger_dir, f"{result['meta']['ticker']}_{date}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2, default=str)
    return path


def format_krx_comparison_table(groups: dict) -> str:
    lines = []
    for us_ticker, group in groups.items():
        tracks = group[0]["meta"]["tracks"]
        gap_min = group[0]["valuation"]["gap_min"]
        gap_max = group[0]["valuation"]["gap_max"]
        judgment = group[0]["valuation"]["consensus_judgment"]
        lines.append(f"[{us_ticker} 추종 - {tracks}] 밸류에이션(전부 동일): "
                      f"Gap {gap_min*100:+.2f}~{gap_max*100:+.2f}%p, {judgment}")
        lines.append(f"{'티커':8} {'종목명':28} {'총보수':>8} {'보수차':>8} "
                      f"{'환헤지':>6} {'순자산(억원)':>12}")
        for r in group:
            w = r["wrapper"]
            aum_str = f"{w['aum_krw']/1e8:12,.0f}" if w["aum_krw"] is not None else f"{'미확인':>12}"
            lines.append(
                f"{r['meta']['ticker']:8} {r['meta']['name'][:28]:28} "
                f"{w['expense_ratio']*100:7.2f}% {w['expense_ratio_delta_vs_us']*100:+7.2f}%p "
                f"{'H' if w['hedged'] else '-':>6} {aum_str}"
            )
        lines.append("")
    return "\n".join(lines)


def krx_holdings_overlap_report(krx_results: list, us_results_by_ticker: dict) -> dict:
    """
    ⭐ v3.39 후속 - **실제로 살 국내 상장 ETF끼리** 여러 개를 함께 담을 때
    생기는 중복노출을 측정한다.

    v3.36의 `portfolio_overlap_report()`는 미국 원본끼리의 겹침만 봤다 - 그런데
    한국 투자자는 미국 원본을 못 사고 국내 래퍼를 산다. 그렇다고 국내 래퍼마다
    별도로 top10_holdings를 새로 조사할 필요는 없다 - **이 엔진의 핵심 전제**
    (국내 래퍼는 미국 원본과 같은 주식 바스켓을 담는다)가 여기서도 그대로
    성립하므로, 국내 래퍼 A·B의 겹침은 각각의 `us_reference_ticker` 원본의
    top10_holdings로 근사할 수 있다. 새 데이터 수집 없이 `holdings_overlap()`
    (v3.36/v3.37에서 이미 만들고 검증한 함수)을 그대로 재사용한다 - Simplicity
    First 원칙(중복 계산 금지)을 여기서도 지킨다.

    `us_results_by_ticker`: {US 티커: run_etf_analysis() 결과 dict}. 이 dict에
    `top10_holdings`가 없는 원본을 참조하는 국내 래퍼는 `skipped_no_holdings`로
    빠진다(데이터 없음을 '겹침 없음'으로 오독하지 않는다 - v3.36 원칙).

    ⚠️ **같은 미국 원본을 추종하는 국내 래퍼끼리는 정의상 거의 완전히 겹친다**
    (TIGER/KODEX/ACE 미국S&P500이 전부 VOO를 재사용하므로) - 이건 버그가 아니라
    사실이다. `informative`가 True인 이상 그대로 보고하되, "같은 지수를
    파는 다른 브랜드일 뿐"이라는 걸 명확히 표시한다(같은 그룹 내 비교는 이미
    `compare_krx_wrappers()`가 비용 기준으로 하고 있으므로 여기서는 정보 제공만).
    """
    have = []
    skipped = []
    for r in krx_results:
        us_ticker = r["meta"]["wrapper_of"]["us_reference_ticker"]
        us_result = us_results_by_ticker.get(us_ticker)
        holdings = us_result["inputs"].get("top10_holdings") if us_result else None
        if holdings:
            have.append((r, us_ticker, holdings))
        else:
            skipped.append(r["meta"]["ticker"])

    measured = []
    uninformative = []
    same_index = []
    for i in range(len(have)):
        for j in range(i + 1, len(have)):
            r_a, us_a, hold_a = have[i]
            r_b, us_b, hold_b = have[j]
            ov = holdings_overlap(hold_a, hold_b)
            ov["pair"] = (r_a["meta"]["ticker"], r_b["meta"]["ticker"])
            ov["pair_names"] = (r_a["meta"]["name"], r_b["meta"]["name"])
            ov["us_pair"] = (us_a, us_b)
            ov["warning"] = None

            if us_a == us_b:
                ov["warning"] = (
                    f"[동일지수 경고] {r_a['meta']['ticker']}({r_a['meta']['name']})와 "
                    f"{r_b['meta']['ticker']}({r_b['meta']['name']})는 둘 다 {us_a}를 "
                    f"재사용해 사실상 동일한 주식 바스켓이다 - 같이 담아도 분산 효과가 "
                    f"전혀 없다. 총보수·유동성만 비교해 하나만 고를 것"
                    f"(`compare_krx_wrappers()` 참고)."
                )
                same_index.append(ov)
                continue

            if not ov["informative"]:
                uninformative.append(ov)
                continue

            if ov["shared_weight"] >= OVERLAP_WARNING_THRESHOLD:
                ov["warning"] = (
                    f"[중복노출 경고] {r_a['meta']['ticker']}({r_a['meta']['name']})와 "
                    f"{r_b['meta']['ticker']}({r_b['meta']['name']})는 서로 다른 지수를 "
                    f"추종하지만 상위 보유종목만으로도 {ov['shared_weight']*100:.1f}%p가 "
                    f"겹친다(공통 {ov['n_common']}종목: {', '.join(ov['common_tickers'])}). "
                    f"top10만 본 하한값이므로 실제 겹침은 이보다 크다."
                )
            measured.append(ov)

    measured.sort(key=lambda x: -x["shared_weight"])
    return {
        "same_index_pairs": same_index,
        "pairs": measured,
        "uninformative_pairs": uninformative,
        "skipped_no_holdings": skipped,
        "threshold": OVERLAP_WARNING_THRESHOLD,
        "note": (
            "국내 래퍼의 겹침은 각자의 미국 원본 top10_holdings로 근사한 값이다 "
            "(재사용 설계 원칙상 국내 래퍼=미국 원본과 동일 바스켓). top10 기준이라 "
            "실제 겹침의 하한이다."
        ),
    }


def format_krx_overlap_table(report: dict) -> str:
    lines = []
    if report["same_index_pairs"]:
        lines.append("같은 미국 원본을 재사용하는 쌍(정의상 거의 완전히 겹침):")
        for ov in report["same_index_pairs"]:
            pair = f"{ov['pair'][0]}+{ov['pair'][1]}"
            lines.append(f"  {pair:16} {ov['shared_weight']*100:6.1f}%p  ({ov['us_pair'][0]} 공용)")
        lines.append("")

    lines.append("서로 다른 지수 추종 - 실측 겹침:")
    lines.append(f"{'KRX 쌍':16} {'미국원본 쌍':14} {'공통종목수':>8} {'겹침(하한)':>10} 경고")
    lines.append("-" * 90)
    for ov in report["pairs"]:
        pair = f"{ov['pair'][0]}+{ov['pair'][1]}"
        us_pair = f"{ov['us_pair'][0]}+{ov['us_pair'][1]}"
        flag = "⚠️ 중복노출" if ov["warning"] else ""
        lines.append(
            f"{pair:16} {us_pair:14} {ov['n_common']:>8} {ov['shared_weight']*100:9.1f}%p {flag}"
        )

    if report["uninformative_pairs"]:
        lines.append("")
        lines.append(f"측정 불가(top10 표본이 우연히 안 겹침 - '겹침 0'이 아니라 '모름'): "
                     f"{len(report['uninformative_pairs'])}쌍")

    if report["skipped_no_holdings"]:
        lines.append("")
        lines.append("보유종목 데이터 없어 측정 제외: " + ", ".join(report["skipped_no_holdings"]))

    return "\n".join(lines)
