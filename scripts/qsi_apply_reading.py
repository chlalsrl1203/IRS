"""
QSI 3단계 — 독립 판독 두 벌(A·B)을 검증·병합해 개정본으로 봉인한다 (v3.98)

규칙(사전 고정, `docs/qsi_reading_rubric.md`):
  1. 판독자의 `quote`가 증거 묶음 발췌문의 **연속 부분 문자열**이 아니면 그 답은 버린다(그 판독자는 unknown 취급).
  2. A·B가 **같은 status·같은 answer**일 때만 채택한다. 다르면 unknown("판독 불일치"). 한쪽만 답했어도 unknown.
  3. 채택한 답의 근거는 A의 인용을 쓰고 B의 인용을 보조 증거로 단다(서로 다른 발췌여도 둘 다 검증됨).
  4. 이미 answered인 답은 덮지 않는다(merge 재사용). 판정·비중·ledger는 건드리지 않는다.
  5. 일치도(질문별 A=B 비율, 답변 시 일치율)를 `reports/qsi_reading/agreement.json`에 남긴다.

실행: python -m scripts.qsi_apply_reading [--dry-run] [TICKER ...]
"""

import datetime
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from engine import qualitative_input as Q  # noqa: E402
from scripts.qsi_sec_events import _cit, _claim, _ev, merge  # noqa: E402

BASE = os.path.join(ROOT, "reports", "qsi_reading")
STATUSES = ("answered", "unknown", "not_applicable")


def _load(path):
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def verify_answer(ans, pack, bank):
    """판독자 답 하나를 검증. (정규화된 답 | None, 사유)"""
    qid = ans.get("qid")
    q = bank.get(qid)
    if q is None:
        return None, "질문 은행에 없음"
    st = ans.get("status")
    if st not in STATUSES:
        return None, f"status {st!r}"
    if st == "unknown":
        return {"qid": qid, "status": "unknown", "answer": None, "reason": ans.get("reason") or ""}, "unknown"
    ex = {e["id"]: e for e in pack["excerpts"]}
    e = ex.get(ans.get("excerpt_id"))
    quote = ans.get("quote")
    if e is None or not isinstance(quote, str) or not quote:
        return None, "근거 발췌/인용 없음"
    if not (40 <= len(quote) <= 400) or quote not in e["text"]:
        return None, "인용이 원문 발췌의 연속 구간이 아님"
    if st == "answered":
        try:
            Q._check_value(q, ans.get("answer"))
        except Q.QualitativeInputError as err:
            return None, f"답 형식: {err}"
    return {"qid": qid, "status": st, "answer": ans.get("answer") if st == "answered" else None,
            "excerpt_id": e["id"], "quote": quote, "url": e["url"], "doc": e["doc"],
            "reason": ans.get("reason") or ""}, "ok"


def combine(a, b):
    """두 판독 결과 → (채택 답 | None, 사유). 같은 status·answer일 때만."""
    if a is None or b is None:
        return None, "한쪽 판독이 무효/누락"
    if a["status"] == "unknown" or b["status"] == "unknown":
        return None, "한쪽 이상 unknown"
    if a["status"] != b["status"] or a["answer"] != b["answer"]:
        return None, "판독 불일치"
    return a, "일치"


def build(ticker, as_of):
    pack = _load(os.path.join(BASE, "packs", f"{ticker}.json"))
    ra = _load(os.path.join(BASE, "passA", f"{ticker}.json"))
    rb = _load(os.path.join(BASE, "passB", f"{ticker}.json"))
    if not (pack and ra and rb):
        return None
    prior = Q.latest_record(ticker)
    if prior["sealed_core_hash"] != pack["based_on_record"]:
        raise RuntimeError(f"{ticker}: 증거 묶음이 만들어진 뒤 QSI 기록이 바뀌었다 — 묶음을 다시 만들 것")
    bank = {q.qid: q for q in Q.bank_for(prior["lens_set"])}
    A = {x["qid"]: x for x in ra["answers"]}
    B = {x["qid"]: x for x in rb["answers"]}
    claims, answers, stats = [], [], []
    for qid in pack["targets"]:
        va, ra_why = verify_answer(A[qid], pack, bank) if qid in A else (None, "누락")
        vb, rb_why = verify_answer(B[qid], pack, bank) if qid in B else (None, "누락")
        chosen, why = combine(va, vb)
        stats.append({"qid": qid, "a": (va or {}).get("status", f"무효:{ra_why}"),
                      "b": (vb or {}).get("status", f"무효:{rb_why}"), "outcome": why})
        if chosen is None:
            note = f"3단계 판독 미채택: {why}"
            if why == "한쪽 이상 unknown" and va and vb:
                note += f" (A={va['status']}, B={vb['status']})"
            answers.append({"qid": qid, "status": "unknown", "answer": None, "claim_ids": [], "note": note})
            continue
        cid = f"READ-{ticker}-{qid}"
        evs = []
        for v in (va, vb):
            cit = _cit(v["doc"], v["excerpt_id"], v["url"], as_of, v["quote"])
            evs.append(_ev(v["reason"] or f"{qid} 판독", cit, "neutral", note="독립 판독자 인용 · 원문 대조 통과"))
        # 같은 인용이면 중복 증거를 하나로
        if evs[0]["citation"]["quote"] == evs[1]["citation"]["quote"]:
            evs = evs[:1]
        claims.append(_claim(cid, f"{qid} = {chosen['answer']!r} (독립 판독 2인 일치)", "MEDIUM", *evs))
        answers.append({"qid": qid, "status": chosen["status"], "answer": chosen["answer"],
                        "claim_ids": [cid], "note": "3단계 독립 판독 2인 일치 · 인용은 원문 발췌와 글자 일치 확인"})
    core, changed = merge(prior, claims, answers, [], as_of)
    return prior, core, changed, stats


def main(argv):
    dry = "--dry-run" in argv
    as_of = datetime.date.today().isoformat()
    tickers = [a for a in argv if not a.startswith("--")] or sorted(
        f[:-5] for f in os.listdir(os.path.join(BASE, "passA")) if f.endswith(".json"))
    agg = {}
    for t in tickers:
        try:
            out = build(t, as_of)
        except Exception as e:
            print(f"{t:5} 실패: {type(e).__name__}: {e}")
            continue
        if out is None:
            print(f"{t:5} A/B 판독 파일이 모두 있어야 한다 — 건너뜀")
            continue
        prior, core, changed, stats = out
        for s in stats:
            d = agg.setdefault(s["qid"], {"n": 0, "agree": 0, "both_answered": 0, "adopted": 0})
            d["n"] += 1
            if s["outcome"] == "일치":
                d["adopted"] += 1
            if s["a"] in ("answered", "not_applicable") and s["b"] in ("answered", "not_applicable"):
                d["both_answered"] += 1
                if s["outcome"] == "일치":
                    d["agree"] += 1
        rec = Q.build_record(core)
        c = rec["coverage"]
        print(f"{t:5} 답 {prior['coverage']['n_answered']:>2} -> {c['n_answered']:>2} / {c['n_questions']}  "
              f"채택 {sum(1 for s in stats if s['outcome'] == '일치')}/{len(stats)}")
        if not dry and rec["sealed_core_hash"] != prior["sealed_core_hash"]:
            print("      ->", os.path.relpath(Q.save_record(rec, supersedes=prior["sealed_core_hash"]), ROOT))
    both = sum(d["both_answered"] for d in agg.values())
    agree = sum(d["agree"] for d in agg.values())
    summary = {"as_of": as_of, "by_question": agg,
               "agreement_when_both_answered": round(agree / both, 3) if both else None,
               "n_both_answered": both}
    if not dry:
        with open(os.path.join(BASE, "agreement.json"), "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2, sort_keys=True)
            f.write("\n")
    print("두 판독자가 모두 답한 항목의 일치율:", summary["agreement_when_both_answered"], f"(n={both})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
