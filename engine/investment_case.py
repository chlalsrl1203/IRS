"""
Investment Case (v3.50 신규, 2026-08-15) - 계약서 §3의 **얇은 계층**.

## 이 모듈은 계산하지 않는다

§3이 요구한 14개 필드는 **전부 이미 어딘가에서 계산되고 있다**:

    fundamental_view              <- ledger.derived (CAGR·마진)
    valuation_implied_requirement <- ledger.implied_growth
    expectation_gap               <- ledger.expectation_gap
    gap_change                    <- gap_analysis.gap_change   (v3.48)
    gap_drivers                   <- gap_analysis.gap_drivers  (v3.48)
    evidence_strength             <- gap_analysis.evidence_strength
    model_uncertainty             <- gap_analysis.model_uncertainty
    market_assumption             <- thesis.market_assumption  (v3.48)
    irs_view                      <- thesis.irs_view
    thesis / catalysts / risks / invalidation_conditions <- thesis (v3.48)
    decision                      <- thesis.build_decision

문제는 **흩어져 있어서 한 종목의 투자 판단 전체를 한눈에 볼 수 없다**는
것이었다. 이 모듈은 그 조각들을 하나로 묶기만 한다 - 새 valuation 로직도,
새 score도 추가하지 않는다(§18 "새로운 score 남발" 금지).

## ⚠️ Signal과 Decision의 경계를 여기서도 지킨다

Investment Case는 signal 파트(gap_*)와 decision 파트(thesis/decision)를
**같은 객체에 담되 섞지 않는다.** `build_case()`는 결정을 만들어내지 않고,
이미 기록된 결정을 참조만 한다. 결정이 없으면 `decision=None`인 채로
"아직 signal만 있다"는 상태가 그대로 드러난다.

`case_completeness()`가 14개 필드 중 무엇이 비었는지 보고한다 - 빈 것을
추측으로 채우지 않고 **비었다는 사실을 드러내는 것**이 이 프로젝트의 방식이다.
"""

from engine.gap_analysis import (
    GAP_SIGNAL_STATUS,
    evidence_strength,
    gap_change,
    gap_drivers,
    gap_level,
    gap_range_over_assumptions,
    model_uncertainty,
)

# §3이 열거한 14개 필드. 다만 **셋으로 나눠서** 센다 - 그러지 않으면 갓 분석한
# 종목이 전부 "미완성"으로 찍혀 플래그가 무의미해진다.
#
#   SIGNAL_AT_ANALYSIS : 분석 시점 T에 곧바로 계산되는 것
#   SIGNAL_OVER_TIME   : **비교 대상이 생겨야** 정의되는 것. 분석 직후에는
#                        값이 없는 게 정상이다(변한 게 없으니 변화도 없다) -
#                        이걸 '누락'으로 세면 안 된다.
#   DECISION_FIELDS    : 분석자가 기록해야 채워지는 것
SIGNAL_AT_ANALYSIS = (
    "fundamental_view",
    "valuation_implied_requirement",
    "expectation_gap",
    "evidence_strength",
    "model_uncertainty",
)
SIGNAL_OVER_TIME = ("gap_change", "gap_drivers")
DECISION_FIELDS = (
    "market_assumption",
    "irs_view",
    "thesis",
    "catalysts",
    "risks",
    "invalidation_conditions",
    "decision",
)
CASE_FIELDS = SIGNAL_AT_ANALYSIS + SIGNAL_OVER_TIME + DECISION_FIELDS


def fundamental_view(ledger: dict) -> dict:
    """
    §1의 첫 단계 "Fundamental Reality" - 재무제표에서만 나오는 값들.

    ledger의 `derived`를 재조합할 뿐 새로 계산하지 않는다. 이 값들이 중요한
    이유: **주가가 어떻게 움직이든 이 숫자들은 바뀌지 않는다.** Gap이 벌어질 때
    사업이 실제로 좋아진 것인지 주가만 빠진 것인지 가르는 기준선이다.
    """
    d = ledger["derived"]
    return {
        "revenue_cagr_3y": d.get("revenue_cagr_3y"),
        "revenue_cagr_5y": d.get("revenue_cagr_5y"),
        "revenue_cagr_10y": d.get("revenue_cagr_10y"),
        "fcf_cagr_5y": d.get("fcf_cagr_5y"),
        "fcf0": d.get("fcf0"),
        "operating_margins": d.get("op_margins"),
        "evidence_supported_expectation": ledger["growth"]["realistic_growth"],
        "lynch_type": ledger["lynch"]["used"],
        # ⚠️ `cap_applied`는 growth **최상위가 아니라 breakdown 안**에 있다.
        # v3.50 초판이 `ledger["growth"].get("cap_applied")`로 읽어 6종목
        # (BRO/CDNS/DUOL/GEN/MNDY/PDD)이 캡에 걸려 있는데도 전부 None을
        # 반환했다 - 조용히 틀리는 유형이라 감사에서야 잡혔다.
        "growth_cap_applied": (ledger["growth"].get("breakdown") or {}).get("cap_applied"),
        "note": (
            "재무제표에서만 나오는 값이다 - 시가총액·주가와 무관하며, "
            "Expectation Gap이 움직여도 여기가 안 움직였다면 사업 현실은 그대로다."
        ),
    }


def build_case(ledger: dict, thesis_record: dict = None,
               market_cap_now: float = None, current_result: dict = None,
               observations: list = None, corpus_ranges: dict = None) -> dict:
    """
    §3의 14개 필드를 하나로 묶는다.

    `thesis_record`: `thesis.load_thesis()`가 돌려주는 기록(thesis/decisions/
    evidence). 없으면 signal 파트만 채워지고 decision 파트는 None으로 남는다 -
    **그게 정확한 상태다**(아직 투자 판단을 내리지 않은 종목).

    ⚠️ 결정을 만들어내지 않는다. 이미 기록된 마지막 결정을 참조만 한다.
    """
    lv = gap_level(ledger)

    case = {
        "ticker": ledger["meta"]["ticker"],
        "ledger": f"{ledger['meta']['ticker']}_{ledger['meta']['analyzed_at'][:10]}.json",
        "signal_status": GAP_SIGNAL_STATUS,

        # ── Signal 파트 (계산에서 나옴) ──────────────────────────
        "fundamental_view": fundamental_view(ledger),
        "valuation_implied_requirement": lv["valuation_implied_requirement"],
        "expectation_gap": lv["gap"],
        "judgment": lv["judgment"],
        "judgment_grade": lv["grade"],
        "gap_change": None,
        "gap_drivers": None,
        "evidence_strength": evidence_strength(ledger, observations),
        "model_uncertainty": model_uncertainty(ledger, corpus_ranges),
        # v3.51: 정당화 가능한 가정집합 위의 Gap 범위. **공식 판정은 바꾸지
        # 않는다**(병기 원칙) - 다만 그 판정이 가정 하나로 뒤집히는지 드러낸다.
        # 34종목 실측: 21종목이 robust=False였고, 기존 sensitivity_check는
        # 그중 2종목만 잡고 있었다.
        "gap_range": gap_range_over_assumptions(ledger),

        # ── Decision 파트 (분석자가 기록) ────────────────────────
        "market_assumption": None,
        "irs_view": None,
        "thesis": None,
        "catalysts": None,
        "risks": None,
        "invalidation_conditions": None,
        "decision": None,

        "separation_note": (
            "signal 파트는 계산에서, decision 파트는 분석자 기록에서 온다. "
            "Expectation Gap이 BUY를 직접 결정하지 않는다(§3) - decision이 "
            "None이면 아직 투자 판단을 내리지 않은 것이며, 그 상태가 정확하다."
        ),
    }

    if market_cap_now is not None or current_result is not None:
        case["gap_change"] = gap_change(ledger, market_cap_now, current_result)
        case["gap_drivers"] = gap_drivers(ledger, market_cap_now=market_cap_now)

    if thesis_record:
        t = thesis_record["thesis"]
        decisions = thesis_record.get("decisions") or []
        case.update({
            "market_assumption": t["market_assumption"],
            "irs_view": t["irs_view"],
            "thesis": {
                "thesis_id": t["thesis_id"],
                "thesis_date": t["thesis_date"],
                "why_buy": t["why_buy"],
                "key_drivers": t["key_drivers"],
                "expected_outcomes": t["expected_outcomes"],
                "holding_horizon": t["holding_horizon"],
            },
            "catalysts": t["catalysts"],
            "risks": t["risks"],
            "invalidation_conditions": t["invalidation_conditions"],
            # 마지막 결정만 노출하되 전체 이력도 남긴다(결정은 append-only)
            "decision": decisions[-1] if decisions else None,
            "decision_history": decisions,
        })

    case["completeness"] = case_completeness(case)
    return case


def case_completeness(case: dict) -> dict:
    """
    §3의 14개 필드 중 무엇이 비었는지 보고한다.

    ⚠️ 빈 필드를 추측으로 채우지 않는다 - **비었다는 사실을 드러내는 것**이
    목적이다. signal만 있고 decision이 없는 상태는 결함이 아니라 정상적인
    중간 단계다(아직 판단하지 않았다는 뜻).
    """
    missing = [f for f in CASE_FIELDS if case.get(f) in (None, [], {})]

    return {
        "n_fields": len(CASE_FIELDS),
        "n_present": len(CASE_FIELDS) - len(missing),
        "missing_fields": missing,
        "signal_complete": all(f not in missing for f in SIGNAL_AT_ANALYSIS),
        "decision_complete": all(f not in missing for f in DECISION_FIELDS),
        # ⚠️ 시간이 지나야 정의되는 필드는 별도로 센다 - 분석 직후 값이 없는
        # 것은 결함이 아니다(비교 대상이 아직 없다).
        "time_dependent_pending": [f for f in SIGNAL_OVER_TIME if f in missing],
        "stage": _case_stage(missing),
    }


def _case_stage(missing) -> str:
    """
    §1 loop 상에서 이 종목이 어디까지 왔는가. **판정이 아니라 진행 표시**다.

    `SIGNAL_OVER_TIME`(gap_change/gap_drivers)은 단계 판정에 쓰지 않는다 -
    분석 직후에는 정의되지 않는 값이라, 이걸 요구하면 갓 분석한 종목이 전부
    INCOMPLETE로 찍혀 플래그 자체가 무의미해진다.
    """
    if "decision" not in missing:
        return "DECIDED"
    if all(f not in missing for f in DECISION_FIELDS if f != "decision"):
        return "THESIS_RECORDED"    # 논거는 썼으나 아직 액션을 안 정함
    if all(f not in missing for f in SIGNAL_AT_ANALYSIS):
        return "SIGNAL_ONLY"        # 계산만 돌린 상태 - 34종목 대부분이 여기
    return "INCOMPLETE"


def format_case_summary(case: dict) -> str:
    """한 종목의 Investment Case를 사람이 읽는 요약으로."""
    c = case["completeness"]
    fv = case["fundamental_view"]
    lines = [
        f"{case['ticker']} — {c['stage']} ({c['n_present']}/{c['n_fields']} 필드)",
        f"  경제적 현실  : 매출 5y CAGR {(fv['revenue_cagr_5y'] or 0)*100:.2f}%, "
        f"근거기반 기대 {fv['evidence_supported_expectation']*100:.2f}%",
        f"  가격이 요구  : {case['valuation_implied_requirement']*100:.2f}%",
        f"  Gap          : {case['expectation_gap']*100:+.2f}%p ({case['judgment']})",
    ]
    ev = case["evidence_strength"]
    lines.append(f"  외부 증거    : {ev['n_observations']}건 "
                 f"(최강 {ev['strongest_evidence_kind']})")
    if case["decision"]:
        lines.append(f"  결정         : {case['decision']['action']} "
                     f"({case['decision']['decision_date']})")
    else:
        lines.append("  결정         : 없음 - 신호까지만 확보된 상태")
    if c["missing_fields"]:
        lines.append(f"  누락         : {', '.join(c['missing_fields'])}")
    return "\n".join(lines)
