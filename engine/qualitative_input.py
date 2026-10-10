"""
정성평가 표준입력 (QSI v1, v3.93)

# 왜 만들었나
정성 심층조사(S/A 13종목 + B/C/D 20종목)는 지금까지 채팅 요약과 자유서술
(`portfolio/qualitative_overrides.json`)로만 남았다. 같은 축을 두고도 종목마다 다른
질문을 던졌고, 확인 못한 항목은 문장 속에 묻혔다. 이 모듈은 **고정된 질문 은행**과
**답의 형식 검증**을 제공한다 — 조사 자체는 사람(또는 세션 안의 Claude)이 하고, 코드는
형식과 근거 계약만 강제한다. 새 밸류에이션 로직은 0줄이다.

# 재사용한 것 (복제 금지)
  - `engine/evidence.py`        Citation/Evidence/Claim — 근거 계약(2차 출처의 1차 위장 불가)
  - `engine/research_lenses.py` 5축·업종 변형·LensFinding·Disqualifier·QualitativeReview
  - `engine/prediction_ledger.py::core_hash` — 봉인 해시(로직을 다시 짜지 않는다)

# 설계상 하지 않는 것 (전부 테스트로 고정)
  - 종합점수/등급/판정/자동 비중 변경 없음 — 축별 값과 공백만 낸다(§31 안티기능)
  - `run_analysis()`·`portfolio_pipeline`에 배선하지 않는다 — 정성값이 투자 성과와
    관계있다는 증거가 0건이다
  - 네트워크·LLM 호출 없음(stdlib + engine만) — 조사는 코드 밖에서 한다
  - **`unknown`을 1급 값으로 둔다.** "확인 못함"과 "문제 없음"을 구분하지 못하면
    미조사가 안전 신호로 오독된다(P0-01 UNVERIFIED와 같은 계열)

# ⚠️ 검증 상태
IMPLEMENTED_NOT_VALIDATED — 이 입력이 더 나은 판단이나 성과로 이어진다는 증거는 없다.
봉인은 사후에 정성 평가를 고쳐 쓰는 것을 막을 뿐, 그 평가가 옳다는 보증이 아니다.

# TEST:
tests/test_qualitative_input.py
"""

import datetime
import json
import math
import os
import re
from dataclasses import dataclass

from engine.evidence import (Citation, Claim, Evidence,
                             EvidenceError)
from engine.prediction_ledger import core_hash
from engine.research_lenses import (LensError, LensFinding, Disqualifier,
                                    SECTOR_LENS_OVERRIDES, STANDARD_LENSES,
                                    new_review)

SCHEMA = "QSI_v1"
QUALITATIVE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "qualitative")
FNAME_RE = re.compile(
    r"^(?P<ticker>[A-Z.]+)_(?P<date>\d{4}-\d{2}-\d{2})(?:_r(?P<rev>\d+))?\.json$")

ANSWER_STATUSES = ("answered", "unknown", "not_applicable")
ANSWER_TYPES = ("bool", "enum", "number", "text")

# 봉인되는 코어 키. 이 키들의 내용이 바뀌면 해시가 달라진다.
CORE_KEYS = ("schema", "entity", "as_of", "lens_set", "price_at_analysis", "currency",
             "claims", "answers", "findings", "disqualifiers", "inversion",
             "confidence_recommendation")

VALIDATION_STATUS = {
    "qualitative_input": (
        "IMPLEMENTED_NOT_VALIDATED — 질문 은행과 형식 계약은 테스트로 고정돼 있으나, "
        "이 입력이 더 나은 판단이나 투자 성과로 이어진다는 증거는 0건이다. "
        "봉인은 사후 수정을 막을 뿐 평가가 옳다는 보증이 아니다."
    ),
    "question_bank": (
        "ECONOMICALLY_SUPPORTED — 축은 이 저장소가 33종목에 실제로 적용한 5축이다. "
        "개별 질문은 그 조사에서 반복적으로 물었던 것을 고정한 시작점이며 검증된 "
        "체크리스트가 아니다."
    ),
}


class QualitativeInputError(ValueError):
    """정성 입력 계약 위반."""


@dataclass(frozen=True)
class Question:
    qid: str
    lens: str
    question: str
    answer_type: str
    allowed: tuple = ()
    requires_primary: bool = False     # 판정 경계를 움직일 수 있는 사실 주장
    maps_to: str = None                # scorecard_core 입력 필드(있다면)

    def __post_init__(self):
        if self.answer_type not in ANSWER_TYPES:
            raise QualitativeInputError(f"{self.qid}: 알 수 없는 answer_type")
        if (self.answer_type == "enum") != bool(self.allowed):
            raise QualitativeInputError(f"{self.qid}: enum 질문만 allowed를 가진다")


def _q(*a, **k):
    return Question(*a, **k)


# 질문 은행. **새 업종·새 질문은 실제 사례가 생겼을 때 추가한다**(상상으로 늘리지 않는다).
QUESTION_BANK = (
    # --- governance -------------------------------------------------------
    _q("gov.dual_class", "governance", "차등의결권 등 이중 주식 구조가 있는가?",
       "bool", requires_primary=True),
    _q("gov.chair_separated", "governance", "이사회 의장과 CEO가 분리돼 있는가?",
       "bool", requires_primary=True, maps_to="chair_separated"),
    _q("gov.ceo_succession_policy", "governance", "CEO 승계 정책이 공시돼 있는가?",
       "bool", maps_to="ceo_succession_policy"),
    _q("gov.key_person_no_succession", "governance",
       "핵심 인물 의존이 크면서 승계 계획이 없는가?", "bool",
       maps_to="key_person_no_succession"),
    _q("gov.insider_pattern", "governance",
       "최근 12개월 내부자 매매가 기회적(비정기·10b5-1 아님) 순매도/순매수인가?",
       "enum", ("opp_net_sell", "opp_net_buy", "routine_only", "none"),
       requires_primary=True, maps_to="opp_insider"),
    _q("gov.cxo_turnover_24m", "governance",
       "최근 24개월 CEO/CFO 이직을 공시한 8-K(Item 5.02)는 몇 건인가?", "number",
       requires_primary=True),
    _q("gov.material_litigation", "governance",
       "회사 존속·성장 서사에 직결되는 진행 중 소송이 있는가?",
       "enum", ("none", "immaterial", "material"), requires_primary=True),
    _q("gov.say_on_pay_support_pct", "governance",
       "최근 보수 승인(say-on-pay) 주총 투표의 찬성률(찬성/(찬성+반대), 소수)", "number",
       requires_primary=True),
    _q("gov.insider_group_ownership", "governance",
       "임원·이사 전체의 합산 지분(위임장 기준)이 어느 구간인가?",
       "enum", ("lt_1pct", "1_to_5pct", "5_to_20pct", "gte_20pct"), requires_primary=True),
    # v4.00 — 위임장 PvP 표·Item 408 ecd inline XBRL (engine/ecd.py, 규칙은 수집 전 고정)
    _q("gov.pay_measure_category", "governance",
       "위임장 보수-성과(PvP) 표에서 회사가 고른 가장 중요한 보상 연계 재무지표는 어느 범주인가?",
       "enum", ("return_on_capital", "shareholder_return", "cash_flow", "earnings",
                "revenue_growth", "other"), requires_primary=True),
    _q("gov.pvp_tsr_vs_peer", "governance",
       "PvP 표 최근 연도 회사 누적 TSR / 회사가 고른 비교군 TSR − 1 (소수)", "number",
       requires_primary=True),
    _q("gov.trading_plan_adoptions_12m", "governance",
       "최근 12개월 정기보고서(Item 408)가 공시한 임원·이사 매매계획 채택 건수", "number",
       requires_primary=True),
    # --- capital_allocation -----------------------------------------------
    _q("cap.buyback_effect", "capital_allocation",
       "자사주 매입이 실제로 주식수를 줄이는가, SBC 희석만 상쇄하는가?",
       "enum", ("reduces_share_count", "offsets_dilution_only", "share_count_rising"),
       requires_primary=True),
    _q("cap.ma_discipline", "capital_allocation", "M&A 가격 규율은 어떠한가?",
       "enum", ("disciplined", "mixed", "undisciplined", "no_material_ma")),
    _q("cap.dividend_predictable", "capital_allocation", "배당 정책이 예측 가능한가?",
       "bool", maps_to="div_predictable"),
    _q("cap.debt_funded_buyback", "capital_allocation",
       "자사주 매입을 신규 부채로 조달했는가?", "bool", requires_primary=True),
    # --- accounting_quality -----------------------------------------------
    _q("acc.restated_down_3y", "accounting_quality",
       "최근 3년 내 실적을 하향 재작성한 적이 있는가?", "bool",
       requires_primary=True, maps_to="honesty:restated_down_3y"),
    _q("acc.unfaithful_disclosure", "accounting_quality",
       "불성실 공시로 제재·정정이 있었는가?", "bool", maps_to="honesty:unfaithful_disclosure"),
    _q("acc.guidance_miss_3y", "accounting_quality",
       "최근 3년 내 자체 가이던스를 반복해서 하회했는가?", "bool",
       maps_to="honesty:guidance_miss_3y"),
    _q("acc.promise_kept_record", "accounting_quality",
       "경영진이 공개 약속(목표·자본배분)을 지킨 이력이 있는가?", "bool",
       maps_to="honesty:promise_kept_record"),
    _q("acc.voluntary_bad_news", "accounting_quality",
       "나쁜 소식을 먼저 자발적으로 공시한 이력이 있는가?", "bool",
       maps_to="honesty:voluntary_bad_news"),
    _q("acc.material_one_time_items", "accounting_quality",
       "FCF·영업이익에 판정을 흔들 만한 일회성 항목이 있는가?", "bool",
       requires_primary=True),
    _q("acc.icfr_conclusion", "accounting_quality",
       "최근 10-K에서 경영진은 재무보고 내부통제(ICFR)를 effective로 결론냈는가?",
       "enum", ("effective", "ineffective"), requires_primary=True),
    _q("acc.late_filing_nt_3y", "accounting_quality",
       "최근 3년 정기보고서 지연 제출 통지(NT 10-K/10-Q)는 몇 건인가?", "number",
       requires_primary=True),
    _q("acc.auditor_change_3y", "accounting_quality",
       "최근 3년 감사인 변경을 공시한 8-K(Item 4.01)는 몇 건인가?", "number",
       requires_primary=True),
    _q("acc.material_impairment_3y", "accounting_quality",
       "최근 3년 회사가 '중대한 손상 인식'을 공시한 8-K(Item 2.06)는 몇 건인가?", "number",
       requires_primary=True),
    # --- dilution ---------------------------------------------------------
    _q("dil.sbc_to_fcf_pct", "dilution", "SBC/FCF 비율(소수, 0.6=60%)", "number",
       requires_primary=True),
    _q("dil.net_share_change_3y_pct", "dilution",
       "최근 3년 순 희석주식수 변화율(소수, 분할 보정)", "number", requires_primary=True),
    # --- competitive_landscape --------------------------------------------
    _q("cmp.new_threat", "competitive_landscape",
       "엔진의 경쟁자 가중치가 놓친 신규 위협은 무엇인가?", "text"),
    _q("cmp.share_trend", "competitive_landscape", "최근 점유율 추세는?",
       "enum", ("gaining", "stable", "losing")),
    _q("cmp.pricing_power", "competitive_landscape", "가격결정력의 증거가 있는가?",
       "enum", ("evidenced", "unevidenced", "eroding")),
    _q("cmp.lifecycle_shakeout_or_decline", "competitive_landscape",
       "산업이 도태·쇠퇴 국면인가?", "bool", maps_to="lifecycle_shakeout_or_decline"),
    # --- insurance 변형 ---------------------------------------------------
    _q("res.reserve_development", "reserve_adequacy",
       "최근 연도 준비금 발전이 유리/중립/불리 중 어느 쪽인가?",
       "enum", ("favorable", "neutral", "adverse"), requires_primary=True),
    _q("cat.cat_exposure", "catastrophe_risk",
       "대재해 노출과 재보험 방어는 어떠한가?", "text"),
    _q("uw.combined_ratio_pct", "underwriting_discipline",
       "최근 연도 합산비율(소수, 0.87=87%)", "number", requires_primary=True),
    # --- conglomerate 변형 ------------------------------------------------
    _q("seg.capital_allocation", "segment_capital_allocation",
       "세그먼트별 자본이 수익성 높은 곳으로 배분되는가?", "text"),
    _q("aff.affiliate_dependence", "affiliate_relationships",
       "계열사·대주주 의존도는?", "enum", ("none", "moderate", "material")),
)

_BY_QID = {q.qid: q for q in QUESTION_BANK}
if len(_BY_QID) != len(QUESTION_BANK):
    raise QualitativeInputError("qid 중복")


def lenses_for(lens_set: str) -> tuple:
    if lens_set == "standard":
        return STANDARD_LENSES
    if lens_set not in SECTOR_LENS_OVERRIDES:
        raise QualitativeInputError(f"알 수 없는 lens_set: {lens_set}")
    return SECTOR_LENS_OVERRIDES[lens_set]


def bank_for(lens_set: str) -> list:
    """해당 업종 변형의 질문 목록(체크리스트)."""
    ls = set(lenses_for(lens_set))
    return [q for q in QUESTION_BANK if q.lens in ls]


# --- 답 검증 ----------------------------------------------------------------

def _check_value(q: Question, value):
    if q.answer_type == "bool":
        ok = isinstance(value, bool)
    elif q.answer_type == "enum":
        ok = value in q.allowed
    elif q.answer_type == "number":
        ok = (isinstance(value, (int, float)) and not isinstance(value, bool)
              and math.isfinite(value))
    else:
        ok = isinstance(value, str) and bool(value.strip())
    if not ok:
        raise QualitativeInputError(
            f"{q.qid}: 답 {value!r}이(가) {q.answer_type}"
            f"{' ' + str(q.allowed) if q.allowed else ''} 형식이 아니다")


def _validate_answer(ans: dict, review, lens_set: str) -> dict:
    qid = ans.get("qid")
    q = _BY_QID.get(qid)
    if q is None:
        raise QualitativeInputError(f"질문 은행에 없는 qid: {qid}")
    if q.lens not in lenses_for(lens_set):
        raise QualitativeInputError(
            f"{qid}: lens '{q.lens}'는 lens_set='{lens_set}'의 축이 아니다")
    status = ans.get("status")
    if status not in ANSWER_STATUSES:
        raise QualitativeInputError(f"{qid}: 알 수 없는 status: {status}")
    note = str(ans.get("note") or "").strip()
    claim_ids = list(ans.get("claim_ids") or [])

    if status in ("unknown", "not_applicable"):
        if not note:
            raise QualitativeInputError(
                f"{qid}: status='{status}'인데 note(사유)가 비어 있다 — "
                f"왜 모르는지/왜 해당 없는지를 적지 않으면 빈칸과 구분되지 않는다")
        if ans.get("answer") is not None or claim_ids:
            raise QualitativeInputError(
                f"{qid}: status='{status}'인데 answer/claim_ids가 있다 — "
                f"모른다면서 답이나 근거를 달 수 없다")
        return {"qid": qid, "status": status, "answer": None,
                "claim_ids": [], "note": note}

    # answered
    _check_value(q, ans.get("answer"))
    if not claim_ids:
        raise QualitativeInputError(
            f"{qid}: 답했다면 근거 주장(claim_ids)이 있어야 한다 — "
            f"근거 없는 정성 판단이 이 프로젝트가 경계해온 것이다")
    known = {c.claim_id: c for c in review.matrix.claims}
    missing = [c for c in claim_ids if c not in known]
    if missing:
        raise QualitativeInputError(f"{qid}: 존재하지 않는 주장을 가리킨다 {missing}")
    evs = [e for cid in claim_ids for e in known[cid].evidence]
    if not evs:
        raise QualitativeInputError(
            f"{qid}: 가리키는 주장에 증거가 하나도 없다 — 증거 없는 주장은 gap이다")
    if q.requires_primary and not any(e.verification == "VERIFIED_PRIMARY" for e in evs):
        raise QualitativeInputError(
            f"{qid}: 판정 경계를 움직일 수 있는 사실 주장이라 1차 확인"
            f"(VERIFIED_PRIMARY)이 필요하다. 1차 출처를 확보하지 못했다면 "
            f"status='unknown'으로 남길 것 — TYL SBC 3배 오류가 2차 출처 무검증 "
            f"인용이었다.")
    return {"qid": qid, "status": "answered", "answer": ans["answer"],
            "claim_ids": claim_ids, "note": note}


def _iso(d, label):
    try:
        return datetime.date.fromisoformat(str(d))
    except ValueError:
        raise QualitativeInputError(f"{label}이(가) ISO 날짜가 아니다: {d!r}")


# --- 레코드 빌드/봉인/검증 ---------------------------------------------------

def build_record(payload: dict) -> dict:
    """페이로드를 검증하고 봉인된 레코드를 만든다. 계약 위반이면 예외."""
    for k in ("entity", "as_of", "lens_set"):
        if not str(payload.get(k) or "").strip():
            raise QualitativeInputError(f"{k}가 비어 있다")
    as_of = _iso(payload["as_of"], "as_of")
    lens_set = payload["lens_set"]
    lenses_for(lens_set)

    try:
        review = new_review(payload["entity"], payload["as_of"], lens_set=lens_set)
        for c in payload.get("claims") or []:
            cl = Claim(claim_id=c["claim_id"], statement=c["statement"],
                       materiality=c.get("materiality", "MEDIUM"))
            for e in c.get("evidence") or []:
                cit = Citation(**e["citation"])
                if _iso(cit.observed_date, f"{cl.claim_id} observed_date") > as_of:
                    raise QualitativeInputError(
                        f"{cl.claim_id}: observed_date({cit.observed_date})가 "
                        f"as_of({payload['as_of']})보다 늦다 — 분석 시점에 볼 수 "
                        f"없던 정보다")
                cl.add(Evidence(
                    summary=e["summary"], direction=e["direction"], citation=cit,
                    verification=e["verification"], confidence=e["confidence"],
                    metric=e.get("metric"), value=e.get("value"),
                    note=e.get("note", "")))
            review.matrix.add(cl)
        for f in payload.get("findings") or []:
            review.add_finding(LensFinding(
                lens=f["lens"], effect=f["effect"], summary=f["summary"],
                claim_ids=list(f.get("claim_ids") or [])))
        for d in payload.get("disqualifiers") or []:
            review.add_disqualifier(Disqualifier(
                code=d["code"], statement=d["statement"],
                claim_ids=list(d.get("claim_ids") or [])))
    except (KeyError, TypeError) as e:
        raise QualitativeInputError(f"페이로드 구조 오류: {type(e).__name__}: {e}")
    except (EvidenceError, LensError):
        raise

    review.inversion = [str(x).strip() for x in (payload.get("inversion") or [])
                        if str(x).strip()]
    rec = payload.get("confidence_recommendation")
    if rec is not None and not (isinstance(rec, int) and not isinstance(rec, bool)
                                and 0 <= rec <= 100):
        raise QualitativeInputError("confidence_recommendation은 0~100 정수 또는 null")
    review.confidence_recommendation = rec

    answers, seen = [], set()
    for a in payload.get("answers") or []:
        v = _validate_answer(a, review, lens_set)
        if v["qid"] in seen:
            raise QualitativeInputError(f"중복 답: {v['qid']}")
        seen.add(v["qid"])
        answers.append(v)

    price = payload.get("price_at_analysis")
    if price is not None and not (isinstance(price, (int, float)) and price > 0
                                  and not isinstance(price, bool)):
        raise QualitativeInputError("price_at_analysis는 양수 또는 null")

    matrix = review.matrix.as_dict()
    core = {
        "schema": SCHEMA, "entity": payload["entity"], "as_of": payload["as_of"],
        "lens_set": lens_set, "price_at_analysis": price,
        "currency": payload.get("currency", "USD"),
        "claims": matrix["claims"], "answers": answers,
        "findings": review.as_dict()["findings"],
        "disqualifiers": review.as_dict()["disqualifiers"],
        "inversion": review.inversion,
        "confidence_recommendation": rec,
    }
    return {**core,
            "sealed_core_hash": core_hash(core),
            "coverage": coverage(core, review),
            "validation_status": VALIDATION_STATUS,
            "affects_official_judgment": False}


def coverage(core: dict, review=None) -> dict:
    """축별 답한/모르는/해당없음 집계. **모른다는 사실을 숨기지 않는 것**이 목적이다."""
    bank = bank_for(core["lens_set"])
    by_qid = {a["qid"]: a for a in core["answers"]}
    per_lens = {}
    for lens in lenses_for(core["lens_set"]):
        qs = [q for q in bank if q.lens == lens]
        cnt = {"answered": 0, "unknown": 0, "not_applicable": 0, "unasked": 0}
        for q in qs:
            a = by_qid.get(q.qid)
            cnt[a["status"] if a else "unasked"] += 1
        per_lens[lens] = {"n_questions": len(qs), **cnt}
    n = sum(v["n_questions"] for v in per_lens.values())
    answered = sum(v["answered"] for v in per_lens.values())
    # 판정을 흔들 수 있는 사실 질문 중 1차 확인으로 답한 비율의 분모/분자
    prim = [q for q in bank if q.requires_primary]
    prim_answered = sum(1 for q in prim
                        if by_qid.get(q.qid, {}).get("status") == "answered")
    out = {
        "per_lens": per_lens, "n_questions": n, "n_answered": answered,
        "answered_fraction": round(answered / n, 4) if n else None,
        "n_primary_required": len(prim), "n_primary_answered": prim_answered,
        "note": "answered_fraction이 낮다는 것은 '문제 없음'이 아니라 '확인 못함'이다.",
    }
    if review is not None:
        r = review.report()
        out["unexamined_lenses"] = r["unexamined_lenses"]
        out["inversion_complete"] = r["inversion_complete"]
        m = review.matrix.report()
        out["gaps"] = [g["claim_id"] for g in m["gaps"]]
        out["material_without_primary"] = [
            x["claim_id"] for x in m["material_without_primary"]]
    return out


def verify_record(record: dict) -> dict:
    """봉인 해시와 계약을 다시 검증한다. 한 글자라도 바뀌었으면 예외."""
    core = {k: record[k] for k in CORE_KEYS}
    if core_hash(core) != record.get("sealed_core_hash"):
        raise QualitativeInputError(
            "봉인 해시 불일치 — 기록된 정성 평가가 사후에 수정됐다. "
            "생각이 바뀌었다면 수정하지 말고 새 날짜로 새 기록을 만들 것.")
    rebuilt = build_record(core)
    if rebuilt["sealed_core_hash"] != record["sealed_core_hash"]:
        raise QualitativeInputError("재구성한 레코드의 해시가 다르다(계약 변경 의심)")
    return {"ok": True, "entity": record["entity"], "as_of": record["as_of"]}


def _revision_paths(entity: str, directory: str) -> list:
    """한 종목의 모든 기록 경로를 (as_of, revision) 순으로."""
    found = []
    for name in os.listdir(directory) if os.path.isdir(directory) else []:
        m = FNAME_RE.match(name)
        if m and m["ticker"] == entity:
            found.append((m["date"], int(m["rev"] or 1), os.path.join(directory, name)))
    return [p for _, _, p in sorted(found)]


def latest_record(entity: str, directory: str = None):
    """종목의 최신 봉인 레코드(없으면 None). 개정본이 있으면 가장 높은 revision."""
    directory = directory or QUALITATIVE_DIR
    paths = _revision_paths(entity, directory)
    if not paths:
        return None
    with open(paths[-1], encoding="utf-8") as f:
        return json.load(f)


def save_record(record: dict, directory: str = None, supersedes: str = None) -> str:
    """
    봉인 저장. **종목당 1건이 아니라 누적한다** — 정성 평가를 나중에 덮어쓰는 것을 막는 것이
    목적이므로 과거 기록은 남겨야 한다. 같은 종목·같은 날짜 파일이 있으면 거부한다.

    **개정본(`supersedes`)**: 같은 날짜에 새 사실을 확보했다면 기존 파일을 고치지 않고
    `<T>_<날짜>_r2.json`을 새로 쌓는다. `supersedes`는 직전 최신 기록의 봉인 해시여야 하며
    (사슬이 끊기면 거부), 개정본은 `revision`/`supersedes`를 **비봉인 필드**로 담는다 —
    기존 해시·기존 파일은 한 글자도 바뀌지 않는다.
    """
    directory = directory or QUALITATIVE_DIR
    verify_record(record)
    os.makedirs(directory, exist_ok=True)
    base = os.path.join(directory, f"{record['entity']}_{record['as_of']}")
    path = base + ".json"
    if os.path.exists(path):
        if supersedes is None:
            raise FileExistsError(
                f"{path}가 이미 있다. 봉인된 정성 평가는 수정할 수 없다 — "
                f"새 사실이 있으면 supersedes로 개정본을 쌓거나 as_of를 새 날짜로 하여 "
                f"새 기록을 만들 것.")
    elif supersedes is not None and not _revision_paths(record["entity"], directory):
        raise QualitativeInputError("supersedes를 줬는데 이 종목의 기존 기록이 없다")
    if supersedes is not None:
        prior = latest_record(record["entity"], directory)
        if prior is None or prior["sealed_core_hash"] != supersedes:
            raise QualitativeInputError(
                "supersedes가 이 종목의 최신 기록 해시와 다르다 — 개정 사슬이 끊겼다")
        if prior["sealed_core_hash"] == record["sealed_core_hash"]:
            raise QualitativeInputError("개정본이 직전 기록과 내용이 같다 — 개정할 것이 없다")
        revs = [int(FNAME_RE.match(os.path.basename(p))["rev"] or 1)
                for p in _revision_paths(record["entity"], directory)
                if FNAME_RE.match(os.path.basename(p))["date"] == record["as_of"]]
        rev = (max(revs) + 1) if revs else 1
        if rev > 1:
            path = f"{base}_r{rev}.json"
        record = {**record, "revision": rev, "supersedes": supersedes}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")
    return path


# --- scorecard_core 입력 필드 파생 (배선 아님) ---------------------------------

def scorecard_input_fields(record: dict) -> dict:
    """
    답에서 `scorecard_core` 입력 dict의 **일부 필드**를 만든다. 계산도 호출도 하지 않는다.

    파생 가능한 것은 불리언/열거형 항목뿐이다. `roiic_5y`·`dollar_test_ratio`·업종
    백분위 같은 입력은 업종 내 상대값이라 한 회사의 질문 답으로 만들 수 없다 — 억지로
    채우지 않고 `not_derivable`로 남긴다. 모르는 항목은 키 자체를 넣지 않는다
    (None/False로 채우면 '확인한 결과 아님'이 '확인한 결과 아님'으로 보인다).

    `honesty_checklist`는 scorecard_core 규칙대로 **증거 URL이 있는 True 항목만**
    넣는다. 다섯 항목을 모두 답했을 때만 `honesty_reviewed=True`.
    """
    by_qid = {a["qid"]: a for a in record["answers"]}
    claims = {c["claim_id"]: c for c in record["claims"]}

    def first_url(a):
        for cid in a["claim_ids"]:
            for e in claims[cid]["evidence"]:
                if e["citation"].get("url"):
                    return e["citation"]["url"]
        return None

    fields, honesty, skipped = {}, {}, []
    for q in bank_for(record["lens_set"]):
        a = by_qid.get(q.qid)
        if not q.maps_to:
            continue
        if not a or a["status"] != "answered":
            skipped.append({"qid": q.qid, "reason": a["status"] if a else "unasked"})
            continue
        if q.maps_to.startswith("honesty:"):
            if a["answer"] is True:
                url = first_url(a)
                if url:
                    honesty[q.maps_to.split(":", 1)[1]] = url
                else:
                    skipped.append({"qid": q.qid, "reason": "no_evidence_url"})
        elif q.maps_to == "opp_insider":
            fields["opp_insider_net_sell"] = a["answer"] == "opp_net_sell"
            fields["opp_insider_net_buy"] = a["answer"] == "opp_net_buy"
        else:
            fields[q.maps_to] = a["answer"]

    h_ids = [q.qid for q in bank_for(record["lens_set"]) if (q.maps_to or "").startswith("honesty:")]
    if h_ids:
        fields["honesty_checklist"] = honesty
        fields["honesty_reviewed"] = all(
            by_qid.get(i, {}).get("status") == "answered" for i in h_ids)
    return {"fields": fields, "skipped": skipped,
            "not_derivable": ["roiic_5y", "wacc", "dollar_test_ratio", "spread_series",
                              "gm_cv_10y", "share_trend_5y", "kcg_compliance",
                              "net_payout_yield", "업종 상대 백분위 입력 전부"],
            "wired": False}
