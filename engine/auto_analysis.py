"""
자동 정식분석 (Auto Analysis) — v4.03, 2026-10-10.

## 무엇을 위한 것인가

`run_analysis()`는 `model_choice_reason`·`subjective_input_basis`가 없으면 실행을
거부한다(v3.19). 지금까지는 사람(또는 AI 세션)이 그 칸을 채웠다. 구독·API 비용 없이
GitHub Actions만으로 같은 파이프라인을 돌리려면 그 칸을 **코드 규칙으로** 채워야 한다.
이 모듈이 그 규칙이다. **새 밸류에이션 로직은 0줄** — 입력을 규칙으로 조립해 기존
`run_analysis()`를 그대로 부른다.

## 공식 분석과 섞이지 않는다 (가장 중요한 경계)

결과는 `ledger/`가 아니라 `ledger_auto/`에만 저장된다(스크립트 쪽 책임). 매수리스트·
포트폴리오·thesis는 `ledger_auto/`를 읽지 않는다(테스트로 고정). 이유: 이 입력은
경쟁강도·수요민감도를 **corpus 중앙값으로 대체**하고 모델 선택을 휴리스틱으로 한 것이라
BSX·MEDP·NXT에서 이미 세 번 확인된 대체값 오차(거짓 탈락/등급 오차)를 그대로 가진다.
결과 JSON 최상단에 `auto_analysis` 블록으로 "자동 생성·정성조사 없음"을 남긴다.

## 사전 고정 규칙 (검증된 값이 아니며 결과를 보고 조정하지 않는다)

| 판단 | 규칙 | 근거 |
|---|---|---|
| 영업이익 미보고 | 거부(FRAMEWORK_MISMATCH) | 금융·보험·REIT은 FCF-DCF 가정이 안 맞음(COF/AMP/VICI) |
| FCF0 <= 0 | 거부 | Gordon 적용 불가 |
| 3년 창 안 연 매출 +30% 초과 | 거부 | M&A 단계상승과 진짜 고성장을 코드가 구분할 수 없고, 3년 창은 override도 불가(GEN/ROP/CHDN/QSR) |
| 5년 기준연도 매출 -8% 이하 급락 | 직전 정상연도로 `cagr_base_year_override` | COVID 저점 기저효과(BKNG/URBN/EME) — 그 해 FCF가 양수일 때만 |
| 모델 선택 | 단일단계 예비 실행 후 RG − g_terminal >= 5%p면 two_stage, 아니면 single_stage | LFUS·ULTA·NYT·EME·OSIS 사례에서 쓴 기준. 2026-08-16 연구는 이 선택이 "규칙으로 분리되지 않는다"고 했으므로 **비검증 휴리스틱**이며 두 모델 결과가 `run_analysis()`에 항상 함께 기록된다 |
| 경쟁강도 | `competitor_threat_weights=[0.2]`·점유율 추세 0·반독점 False | 중앙값 대체 — 정성조사 없음 |
| 수요민감도 | 0.15 | ledger 중앙값 |
| 순부채·EBITDA | SEC 태그로 계산, 못 구하면 corpus 중앙값 배수로 대체 | 대체 시 명시 |
"""

from engine.expectation_gap_engine import default_terminal_growth
from engine.pipeline import AnalysisInputs, run_analysis
from engine.screener import DEFAULT_NDTE, DEFAULT_RISK_FREE_RATE

AUTO_VERSION = "auto-v1"
STEP_UP_REFUSE = 0.30      # 3년 창 안 연 매출 성장 거부선
BASE_DROP = -0.08          # 5년 기준연도 급락 판정선
TWO_STAGE_MARGIN = 0.05    # RG - g_terminal 이 이 이상이면 two_stage
MIN_YEARS = 6

_DEBT_TAGS = ("LongTermDebt", "LongTermDebtNoncurrent", "DebtLongtermAndShorttermCombinedAmount",
              "LongTermDebtAndCapitalLeaseObligations")
_CASH_TAGS = ("CashAndCashEquivalentsAtCarryingValue",
              "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents")
_DA_TAGS = ("DepreciationDepletionAndAmortization", "DepreciationAndAmortization",
            "DepreciationAmortizationAndAccretionNet")
_ANNUAL = ("10-K", "10-K/A", "20-F", "20-F/A", "40-F")


class AutoAnalysisRefused(Exception):
    """이 종목은 자동 분석 대상이 아니다. category는 excluded_tickers 어휘와 맞춘다."""

    def __init__(self, category, reason):
        super().__init__(f"{category}: {reason}")
        self.category = category
        self.reason = reason


def latest_annual_value(facts_json, tags, year=None):
    """companyfacts에서 연차보고서 기준 가장 최근(또는 지정 연도) 값. (값, 종료일, 태그) 또는 None."""
    gaap = (facts_json or {}).get("facts", {}).get("us-gaap", {})
    best = None
    for tag in tags:
        for e in gaap.get(tag, {}).get("units", {}).get("USD", []):
            if e.get("form") not in _ANNUAL or e.get("val") is None or not e.get("end"):
                continue
            if year is not None and int(e["end"][:4]) != year:
                continue
            if best is None or e["end"] > best[1]:
                best = (e["val"], e["end"], tag)
        if best:
            return best
    return None


def balance_from_facts(facts_json, final_year, op_income_last):
    """순부채·EBITDA를 SEC 태그로 계산. 못 구하면 (None, None, 사유)."""
    debt = latest_annual_value(facts_json, _DEBT_TAGS, final_year)
    cash = latest_annual_value(facts_json, _CASH_TAGS, final_year)
    da = latest_annual_value(facts_json, _DA_TAGS, final_year)
    if debt is None or cash is None or da is None:
        miss = [n for n, v in (("부채", debt), ("현금", cash), ("감가상각", da)) if v is None]
        return None, None, f"SEC 태그 미확보({', '.join(miss)})"
    return debt[0] - cash[0], op_income_last + da[0], None


def _yoy(rev, y):
    prev = rev.get(y - 1)
    return None if not prev or prev <= 0 else rev[y] / prev - 1


def check_gates(series):
    """거부 사유를 찾는다. 통과하면 (years, fcf, base_override, notes)."""
    rev, ocf, capex = (series["revenue_by_year"], series["operating_cashflow_by_year"],
                       series["capex_by_year"])
    op = series.get("operating_income_by_year", {})
    years = sorted(set(rev) & set(ocf) & set(capex))
    if len(years) < MIN_YEARS:
        raise AutoAnalysisRefused("INSUFFICIENT_DATA", f"공통 연도 {len(years)}개 (최소 {MIN_YEARS})")
    if sum(1 for y in years[-5:] if y in op) < 4:
        raise AutoAnalysisRefused(
            "FRAMEWORK_MISMATCH", "최근 5개년 중 영업이익 보고가 4년 미만 — 금융·보험·REIT 유형으로 추정")
    fcf = {y: ocf[y] - capex[y] for y in years}
    final = years[-1]
    if fcf[final] <= 0:
        raise AutoAnalysisRefused("FCF_NONPOSITIVE", f"FCF0={fcf[final]:,.0f} — Gordon 적용 불가")
    for y in years[-3:]:
        g = _yoy(rev, y)
        if g is not None and g > STEP_UP_REFUSE:
            raise AutoAnalysisRefused(
                "FRAMEWORK_MISMATCH",
                f"{y}년 매출 YoY {g:+.1%} > {STEP_UP_REFUSE:.0%} — 3년 창 안 단계상승 "
                f"(M&A와 진짜 고성장을 코드가 구분 못 하고 3년 창은 override 불가)")
    notes, override = [], None
    if len(years) >= 7:
        base = years[-6]
        g = _yoy(rev, base)
        if g is not None and g <= BASE_DROP:
            cand = years[-7]
            if fcf.get(cand, 0) > 0 and rev[cand] > 0:
                override = (cand, f"5년 기준연도 {base}의 매출이 전년 대비 {g:+.1%}로 급락한 "
                                  f"저점이라 직전 연도 {cand}를 기준으로 삼음(v3.21 BKNG 원칙, 자동 규칙)")
            else:
                raise AutoAnalysisRefused(
                    "FRAMEWORK_MISMATCH", f"5년 기준연도 {base}가 저점이나 대체 기준연도 {cand}의 FCF가 음수/없음")
    if fcf[years[-6]] <= 0 and override is None:
        raise AutoAnalysisRefused("FCF_NONPOSITIVE", f"5년 기준연도 {years[-6]} FCF 음수 — CAGR 정의 불가(v3.19)")
    return years, fcf, override, notes


def build_inputs(ticker, company_name, series, market_cap, today, model_used,
                 model_reason, facts_json=None, base_override=None):
    years = sorted(set(series["revenue_by_year"]) & set(series["operating_cashflow_by_year"])
                   & set(series["capex_by_year"]))
    rev = {y: series["revenue_by_year"][y] for y in years}
    op = {y: series["operating_income_by_year"][y] for y in years
          if y in series.get("operating_income_by_year", {})}
    final = years[-1]
    assumptions = ["경쟁강도=중앙값 대체(competitor_threat_weights=[0.2], 점유율 추세 0)",
                   "수요민감도=0.15(ledger 중앙값)", "반독점/규제 사건=False 가정"]
    net_debt = ebitda = None
    if facts_json is not None and final in op:
        net_debt, ebitda, why = balance_from_facts(facts_json, final, op[final])
        if why:
            assumptions.append(why)
    if net_debt is None or ebitda is None or ebitda <= 0:
        base = op.get(final, 0)
        if base <= 0:
            raise AutoAnalysisRefused("FRAMEWORK_MISMATCH", "영업이익 <= 0 — EBITDA 대체 불가(v3.46 가드)")
        ebitda = base
        net_debt = DEFAULT_NDTE * base
        assumptions.append(f"순부채/EBITDA={DEFAULT_NDTE}(corpus 중앙값) 대체, EBITDA=영업이익 근사")
    kw = {}
    if base_override:
        kw["cagr_base_year_override"], kw["cagr_base_year_override_reason"] = base_override
    sbc = series.get("sbc_by_year")
    if sbc and final in sbc and all(v >= 0 for v in sbc.values()):
        kw["sbc_by_year"] = sbc
    return AnalysisInputs(
        ticker=ticker, company_name=company_name or ticker,
        revenue_by_year=rev, operating_income_by_year=op,
        operating_cashflow_by_year={y: series["operating_cashflow_by_year"][y] for y in years},
        capex_by_year={y: series["capex_by_year"][y] for y in years},
        market_cap=market_cap, net_debt=net_debt, ebitda=ebitda,
        risk_free_rate=DEFAULT_RISK_FREE_RATE,
        competitor_threat_weights=[0.2], market_share_trend_pp_per_year=0.0,
        active_antitrust_or_regulatory_case=False, demand_sensitivity_pct=0.15,
        subjective_input_basis=(
            "AUTO(자동 생성, 정성조사 없음): " + "; ".join(assumptions)
            + ". BSX·MEDP·NXT에서 이 대체값이 실제와 달라 등급이 어긋난 선례가 있으므로 "
              "사람의 정성 검토 전에는 참고용으로만 쓸 것."),
        model_used=model_used, model_choice_reason=model_reason,
        falsification_conditions=(
            "다음 연차보고서의 매출 성장률이 Realistic Growth의 절반 미만이면 이 자동 분석을 폐기하고 "
            "재분석할 것. 자동 분석은 경쟁·규제 변화를 보지 못한다."),
        data_sources=[f"SEC XBRL companyfacts (자동 수집, {today})"],
        **kw,
    ), assumptions


def auto_analyze(ticker, company_name, series, market_cap, today, facts_json=None):
    """게이트 -> 단일단계 예비 실행 -> 모델 규칙 -> 최종 실행. 거부 시 AutoAnalysisRefused."""
    _, _, override, _ = check_gates(series)
    pre_reason = "AUTO 예비 실행: 모델 선택 규칙 적용을 위해 single_stage로 먼저 계산"
    pre_inputs, _ = build_inputs(ticker, company_name, series, market_cap, today,
                                 "single_stage", pre_reason, facts_json, override)
    try:
        pre = run_analysis(pre_inputs)
    except ValueError as e:
        raise AutoAnalysisRefused("ENGINE_REFUSED", str(e)[:200]) from e
    rg = pre["growth"]["realistic_growth"]
    g_term = default_terminal_growth(DEFAULT_RISK_FREE_RATE)
    spread = rg - g_term
    if spread >= TWO_STAGE_MARGIN:
        model = "two_stage"
        reason = (f"AUTO 규칙: Realistic Growth {rg:.2%} − g_terminal {g_term:.2%} = {spread:+.2%}p >= "
                  f"{TWO_STAGE_MARGIN:.0%}p 이므로 다단계(고성장 후 수렴). 비검증 휴리스틱이며 "
                  f"두 모델 결과가 모두 기록된다.")
    else:
        model = "single_stage"
        reason = (f"AUTO 규칙: Realistic Growth {rg:.2%} − g_terminal {g_term:.2%} = {spread:+.2%}p < "
                  f"{TWO_STAGE_MARGIN:.0%}p 이므로 Gordon(성장이 터미널에 근접). 비검증 휴리스틱이며 "
                  f"두 모델 결과가 모두 기록된다.")
    inputs, assumptions = build_inputs(ticker, company_name, series, market_cap, today,
                                       model, reason, facts_json, override)
    result = run_analysis(inputs)
    result["auto_analysis"] = {
        "version": AUTO_VERSION, "official": False, "qualitative_research": False,
        "model_rule": {"rg": rg, "g_terminal": g_term, "margin": TWO_STAGE_MARGIN, "chosen": model},
        "assumptions": assumptions,
        "base_year_override": override[0] if override else None,
        "warning": "자동 생성 결과. 경쟁강도·수요민감도는 중앙값 대체이며 사람의 검토 전에는 "
                   "공식 판정·매수리스트·thesis에 쓰지 않는다.",
    }
    return result
