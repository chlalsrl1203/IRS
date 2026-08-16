"""
Investment Thesis (v3.48 신규, 2026-08-15) - 분석을 실제 투자판단으로 연결한다.

## 이 프로젝트에 없던 것

지금까지 IRS는 "이 종목이 싼가"(`judgment`: 저평가/적정가/과대평가)까지만
답했다. 그런데 **싸다는 것과 사야 한다는 것은 다른 명제다.** 그 사이에는
사업품질·재무품질·리스크·포트폴리오 맥락이라는 관문이 있는데, 지금까지는
그 관문이 코드 어디에도 없었고 사실상 등급(S/A)이 곧 매수리스트였다
(`scripts/build_buylist_2026_08_03.py`의 `grade in ("S","A")`).

## ⚠️ 이 모듈의 가장 중요한 설계 - Gap에서 매수를 자동 도출하지 않는다

`decide()` 같은 함수는 **의도적으로 없다.** Expectation Gap을 넣으면 BUY가
나오는 함수를 만드는 순간, 검증되지 않은 신호(`gap_analysis.GAP_SIGNAL_STATUS`
= RESEARCH_HYPOTHESIS)가 자동으로 자본배분 결정이 된다.

대신 이 모듈은 **분석자가 각 관문을 실제로 통과했는지 검사만** 한다:

    Signal -> 사업품질 -> 재무품질 -> 리스크 -> 밸류에이션 -> 포트폴리오 맥락 -> 결정

`record_decision()`은 여섯 관문의 근거가 하나라도 비어 있으면 **거부한다.**
이 프로젝트가 이미 `model_choice_reason`·`subjective_input_basis`에서 쓴
"근거 없으면 실행 거부" 패턴과 동일하다 - 점수 공식을 지어내는 대신,
분석자가 생각했다는 사실을 기록으로 남기게 강제한다.

액션(BUY/ADD/HOLD/WATCH/REDUCE/SELL)은 **분석자가 고른다.** 코드가 고르지
않는다. 이건 기능 부족이 아니라 이 단계에서 의도한 경계다(계약서 5.2·13절 -
검증되지 않은 방법론을 발명하지 않는다).

## 기록 구조 - 코어는 불변, 로그는 append-only

`thesis/<TICKER>_<날짜>.json` 한 파일에 세 부분이 들어간다:

  - **thesis(코어)**: 최초 기록 후 **변경 불가**. 생각이 바뀌면 새 날짜로 새
    thesis를 쓴다(과거 판단을 조용히 고쳐 쓰면 사후합리화가 된다 -
    `falsification_conditions`를 소급 작성하지 않는 원칙과 같다).
  - **decisions**: 시점별 액션 로그. **덧붙이기만** 가능.
  - **evidence**: 이후 들어온 실적·공시. **덧붙이기만** 가능.

기존 항목을 고치려는 호출은 예외를 던진다.
"""

import glob
import json
import os
from dataclasses import asdict, dataclass, field

# §3의 액션 어휘. 분석자가 고르는 값이며 코드가 계산하지 않는다.
#
# v3.50에서 `PASS`를 추가했다(계약서 §3의 vocabulary). WATCH와 다르다:
#   PASS  - 검토했고 **투자 대상이 아니라고 결론**냈다(감시도 하지 않는다)
#   WATCH - 아직 아니지만 조건이 바뀌면 살 수 있어 **계속 본다**
# 이 구분이 없으면 "안 산다"가 전부 WATCH로 뭉뚱그려져 감시 목록이 무한히
# 늘어나고, 정작 무엇을 왜 버렸는지가 기록에서 사라진다.
#
# ⚠️ 기존 어휘는 하나도 바꾸지 않았다(§3 "기존 judgment vocabulary가 존재한다면
# compatibility를 유지한다") - 추가만 했으므로 v3.48 기록은 전부 그대로 유효하다.
DECISION_ACTIONS = ("PASS", "WATCH", "BUY", "ADD", "HOLD", "REDUCE", "SELL")

# §7 모니터링 상태
THESIS_STATUSES = ("STRENGTHENING", "STABLE", "WEAKENING", "INVALIDATED")

# 증거의 방향 - 분석자가 근거와 함께 기록한다(감성분석 같은 자동판정 없음)
EVIDENCE_DIRECTIONS = ("supports", "contradicts", "neutral")

# §5의 관문. 이 여섯 개가 전부 채워져야 결정을 기록할 수 있다.
DECISION_GATES = (
    "signal_summary",         # Gap 등 신호 요약 - 출발점이지 결론이 아니다
    "business_quality",       # 사업품질
    "financial_quality",      # 재무품질(회계품질·현금흐름의 질)
    "risk_assessment",        # 리스크
    "valuation_assessment",   # 밸류에이션
    "portfolio_context",      # 포트폴리오 맥락(집중도·상관·기존 보유)
)

# ⚠️ 상태 판정 규칙의 인식론적 지위(v3.46 VALIDATION_STATUS 체계와 동일 어휘).
# 이건 보정된 모델이 아니라 **투명한 집계 규칙**이다. 증거의 방향은 분석자가
# 근거와 함께 기록하고, 이 함수는 그것을 셀 뿐이다.
STATUS_RULE_VALIDATION = (
    "IMPLEMENTED_NOT_VALIDATED - 단순 집계 규칙이며 실현결과로 보정된 적 없다. "
    "상태를 확률이나 수익률 예측으로 해석하지 말 것."
)


def _require_text(value, label: str) -> str:
    if value is None or not str(value).strip():
        raise ValueError(
            f"{label}이(가) 비어 있다. 이 프로젝트는 근거 없는 입력을 거부한다 - "
            f"모르면 '확인 못함'이라고 정직하게 적을 것(추측 금지)."
        )
    return str(value).strip()


def _require_list(value, label: str) -> list:
    if not value:
        raise ValueError(f"{label}이(가) 비어 있다. 최소 1개 항목이 필요하다.")
    return list(value)


@dataclass
class InvestmentThesis:
    """
    §4의 구조화된 투자논거. 핵심 질문 5개에 답하도록 필드가 배치돼 있다.

      why_buy               -> 왜 지금 사는가
      market_assumption     -> 시장은 무엇을 기대하는가
      irs_view              -> 나는 왜 시장과 다르게 보는가
      expected_outcomes     -> 무엇이 일어나야 thesis가 맞는가
      invalidation_conditions -> 무엇이 일어나면 thesis가 틀린 것인가

    `linked_ledger`로 어느 분석에 근거했는지 추적한다(계약서 13절 - 모든 중요
    값은 출처와 계산 경로를 추적할 수 있어야 한다).
    """

    ticker: str
    thesis_date: str                # ISO 날짜
    why_buy: str
    market_assumption: str
    irs_view: str
    key_drivers: list
    expected_outcomes: list
    catalysts: list
    risks: list
    invalidation_conditions: list   # [{"condition": str, "check_by": str|None}]
    holding_horizon: str
    linked_ledger: str = None       # ledger 파일명 (예: "CDNS_2026-07-25.json")
    author_note: str = ""

    def __post_init__(self):
        self.ticker = _require_text(self.ticker, "ticker").upper()
        _require_text(self.thesis_date, "thesis_date")
        for f in ("why_buy", "market_assumption", "irs_view", "holding_horizon"):
            setattr(self, f, _require_text(getattr(self, f), f))
        for f in ("key_drivers", "expected_outcomes", "catalysts", "risks"):
            setattr(self, f, _require_list(getattr(self, f), f))

        # 반증조건은 이 프로젝트가 가장 중요하게 여기는 필드다(사후합리화를 막는
        # 유일한 실질적 장치). 형식까지 검사한다.
        conds = _require_list(self.invalidation_conditions, "invalidation_conditions")
        normalized = []
        for i, c in enumerate(conds):
            if not isinstance(c, dict) or not str(c.get("condition", "")).strip():
                raise ValueError(
                    f"invalidation_conditions[{i}]는 "
                    f"{{'condition': str, 'check_by': str|None}} 형식이어야 한다."
                )
            normalized.append({
                "condition": str(c["condition"]).strip(),
                "check_by": c.get("check_by"),
                # 발동 여부는 분석자가 나중에 명시적으로 표시한다(자동판정 안 함)
                "triggered": bool(c.get("triggered", False)),
                "triggered_note": c.get("triggered_note"),
            })
        self.invalidation_conditions = normalized

    @property
    def thesis_id(self) -> str:
        """결정적 ID - prediction/experiment가 이 값으로 thesis를 참조한다."""
        return f"{self.ticker}-{self.thesis_date}"


def build_decision(thesis_id: str, decision_date: str, action: str,
                   gates: dict, rationale: str, position_pct: float = None) -> dict:
    """
    §5의 결정 기록을 만든다. **액션은 인자로 받는다 - 계산하지 않는다.**

    gates: DECISION_GATES 6개를 키로 갖는 dict. 하나라도 비면 거부한다.
    이 검사가 이 함수의 존재 이유다 - "Gap이 크니까 산다"는 한 줄짜리 결정을
    구조적으로 불가능하게 만든다.

    position_pct: 편입 비중(선택). 사이징 공식은 여기서 만들지 않는다 -
    기존 `scripts/build_buylist_2026_08_03.py`가 이미 규칙기반 배분을 하고 있고,
    그 규칙을 이 모듈이 중복 구현하면 두 계산이 어긋난다(Simplicity First).
    """
    if action not in DECISION_ACTIONS:
        raise ValueError(f"알 수 없는 액션: {action} (허용: {DECISION_ACTIONS})")

    missing = [g for g in DECISION_GATES
               if not str((gates or {}).get(g, "")).strip()]
    if missing:
        raise ValueError(
            f"결정을 기록하려면 관문 근거가 전부 필요하다. 누락: {missing}. "
            f"이 프로젝트는 Expectation Gap에서 매수를 자동 도출하지 않는다 - "
            f"신호(signal)와 결정(decision)은 분리돼 있으며, 각 관문을 "
            f"분석자가 실제로 검토했다는 기록이 있어야 결정이 성립한다."
        )

    return {
        "thesis_id": thesis_id,
        "decision_date": decision_date,
        "action": action,
        "action_source": "analyst_recorded (엔진이 계산한 값이 아님)",
        "gates": {g: str(gates[g]).strip() for g in DECISION_GATES},
        "rationale": _require_text(rationale, "rationale"),
        "position_pct": position_pct,
    }


def build_evidence(observed_date: str, summary: str, direction: str,
                   source: str, metric: str = None, value=None) -> dict:
    """
    §7의 새 증거 1건. 방향(supports/contradicts/neutral)은 **분석자가** 판단해
    근거(source)와 함께 기록한다 - 텍스트에서 자동 추론하지 않는다.
    """
    if direction not in EVIDENCE_DIRECTIONS:
        raise ValueError(f"알 수 없는 방향: {direction} (허용: {EVIDENCE_DIRECTIONS})")
    return {
        "observed_date": observed_date,
        "summary": _require_text(summary, "summary"),
        "direction": direction,
        "source": _require_text(source, "source"),
        "metric": metric,
        "value": value,
    }


def evaluate_thesis_status(record: dict) -> dict:
    """
    §7 상태 판정: STRENGTHENING / STABLE / WEAKENING / INVALIDATED.

    규칙(투명한 집계 - 숨은 가중치 없음):
      1. 반증조건이 하나라도 `triggered=True`면 -> INVALIDATED. 다른 증거가
         아무리 좋아도 뒤집지 않는다. 사전등록된 반증조건이 발동했는데
         "그래도 좋아 보인다"고 넘어가는 것이 정확히 사후합리화다.
      2. 아니면 supports/contradicts 개수를 비교해 STRENGTHENING/WEAKENING/STABLE.

    ⚠️ `STATUS_RULE_VALIDATION` - 이 규칙은 보정된 적이 없다. 증거 개수는
    증거의 무게가 아니다(v3.42 TTD처럼 반증조건 1건이 나머지 전부를 압도할
    수 있다). 그래서 개수와 함께 항목 원문을 그대로 돌려준다 - 최종 해석은
    사람이 한다.
    """
    invalidation = record.get("thesis", {}).get("invalidation_conditions", [])
    triggered = [c for c in invalidation if c.get("triggered")]

    evidence = record.get("evidence", [])
    supports = [e for e in evidence if e["direction"] == "supports"]
    contradicts = [e for e in evidence if e["direction"] == "contradicts"]

    if triggered:
        status = "INVALIDATED"
    elif len(contradicts) > len(supports):
        status = "WEAKENING"
    elif len(supports) > len(contradicts):
        status = "STRENGTHENING"
    else:
        status = "STABLE"

    return {
        "thesis_id": record["thesis"]["thesis_id"],
        "ticker": record["thesis"]["ticker"],
        "status": status,
        "validation_status": STATUS_RULE_VALIDATION,
        "triggered_invalidations": triggered,
        "n_supports": len(supports),
        "n_contradicts": len(contradicts),
        "n_neutral": len(evidence) - len(supports) - len(contradicts),
        "evidence": evidence,
        "note": (
            "증거 '개수'는 증거의 '무게'가 아니다 - 반증조건 1건이 나머지 전부를 "
            "압도할 수 있다(v3.42 TTD 실측). 최종 해석은 사람이 할 것."
        ),
    }


# ────────────────────────────────────────────────────────────────────────
# 저장 - 코어 불변 / 로그 append-only
# ────────────────────────────────────────────────────────────────────────

THESIS_DIR = "thesis"


def _thesis_path(thesis: InvestmentThesis, thesis_dir: str) -> str:
    return os.path.join(thesis_dir, f"{thesis.ticker}_{thesis.thesis_date}.json")


def save_thesis(thesis: InvestmentThesis, thesis_dir: str = THESIS_DIR) -> str:
    """
    새 thesis를 기록한다. 같은 티커·같은 날짜 파일이 이미 있으면 **거부**한다
    (`save_ledger` v3.46 가드와 같은 이유 - 조용한 소실이 가장 나쁜 실패다).

    생각이 바뀌었다면 새 날짜로 새 thesis를 쓸 것. 과거 판단을 덮어쓰면
    "그때 나는 이렇게 생각했다"는 기록 자체가 사라져 사후 학습이 불가능해진다.
    """
    os.makedirs(thesis_dir, exist_ok=True)
    path = _thesis_path(thesis, thesis_dir)
    if os.path.exists(path):
        raise FileExistsError(
            f"{path}에 이미 thesis가 있다. thesis 코어는 변경 불가다 - "
            f"판단이 바뀌었다면 새 날짜로 새 thesis를 작성할 것. "
            f"과거 판단을 덮어쓰면 예측-실제 비교의 근거가 사라진다."
        )

    core = asdict(thesis)
    core["thesis_id"] = thesis.thesis_id
    record = {"thesis": core, "decisions": [], "evidence": []}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2, default=str)
    return path


def load_thesis(ticker: str, thesis_date: str, thesis_dir: str = THESIS_DIR) -> dict:
    path = os.path.join(thesis_dir, f"{ticker.upper()}_{thesis_date}.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def latest_thesis(ticker: str, thesis_dir: str = THESIS_DIR):
    """티커의 가장 최근 thesis(파일명 정렬 = 날짜 정렬)."""
    paths = sorted(glob.glob(os.path.join(thesis_dir, f"{ticker.upper()}_*.json")))
    if not paths:
        return None, None
    with open(paths[-1], encoding="utf-8") as f:
        return paths[-1], json.load(f)


def _append_only(path: str, key: str, entry: dict) -> dict:
    """
    로그에 항목을 덧붙인다. **기존 항목이 하나라도 바뀌면 거부**한다 -
    append-only를 문서가 아니라 코드로 강제한다.
    """
    with open(path, encoding="utf-8") as f:
        record = json.load(f)

    before = json.dumps(record.get(key, []), ensure_ascii=False, sort_keys=True)
    record.setdefault(key, []).append(entry)
    after_prefix = json.dumps(record[key][:-1], ensure_ascii=False, sort_keys=True)
    if before != after_prefix:
        raise ValueError(
            f"{key} 로그의 기존 항목이 변경됐다 - append-only 위반. "
            f"과거 기록은 고치지 않는다."
        )

    with open(path, "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2, default=str)
    return record


def record_decision(path: str, decision: dict) -> dict:
    """결정을 로그에 덧붙인다(기존 결정은 절대 수정되지 않는다)."""
    return _append_only(path, "decisions", decision)


def record_evidence(path: str, evidence: dict) -> dict:
    """새 증거를 로그에 덧붙인다."""
    return _append_only(path, "evidence", evidence)


def mark_invalidation_triggered(path: str, index: int, note: str) -> dict:
    """
    반증조건 발동을 표시한다. **분석자가 명시적으로 호출해야만** 발동되며,
    코드가 텍스트를 읽고 자동 판정하지 않는다(v3.42가 확립한 원칙 -
    정규식은 트리거 날짜와 서술적 날짜를 구분하지 못한다).

    한 번 발동한 조건을 되돌리는 경로는 두지 않았다 - 발동이 잘못된
    판단이었다면 새 thesis를 쓸 일이지, 기록을 지울 일이 아니다.
    """
    with open(path, encoding="utf-8") as f:
        record = json.load(f)

    conds = record["thesis"]["invalidation_conditions"]
    if not 0 <= index < len(conds):
        raise IndexError(f"invalidation_conditions[{index}]가 없다(총 {len(conds)}건).")
    if conds[index].get("triggered"):
        raise ValueError(f"invalidation_conditions[{index}]는 이미 발동 표시돼 있다.")

    conds[index]["triggered"] = True
    conds[index]["triggered_note"] = _require_text(note, "note")

    with open(path, "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2, default=str)
    return record
