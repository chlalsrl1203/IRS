"""QSI 3단계 병합 스크립트(scripts/qsi_apply_reading.py) 회귀 테스트.

2026-10-09: 두 판독자가 `not_applicable`로 일치하면 claim을 붙여 넘기다가
`qualitative_input._validate_answer`가 "not_applicable인데 claim_ids가 있다"로 거부해
병합 전체가 예외로 멈췄다. 관례(qsi_sec_events 무배당 처리)대로 근거 인용은 note에 남긴다.
"""

import json
import os
import shutil

import pytest

from engine import qualitative_input as Q
from scripts import qsi_apply_reading as R

TICKER = "DECK"
QID = "cap.dividend_predictable"


def _record_for(pack):
    """묶음이 만들어진 시점의 기록(병합 이후에도 테스트가 저장소 상태에 끌려가지 않게)."""
    for f in sorted(os.listdir(Q.QUALITATIVE_DIR)):
        if f.startswith(f"{TICKER}_") and f.endswith(".json"):
            rec = json.load(open(os.path.join(Q.QUALITATIVE_DIR, f), encoding="utf-8"))
            if rec.get("sealed_core_hash") == pack["based_on_record"]:
                return rec
    pytest.fail("묶음의 based_on_record에 해당하는 기록 파일이 없다")


def _setup(tmp_path, monkeypatch, status_a, status_b, answer_a=None, answer_b=None):
    pack = json.load(open(os.path.join(R.BASE, "packs", f"{TICKER}.json"), encoding="utf-8"))
    rec0 = _record_for(pack)
    monkeypatch.setattr(R.Q, "latest_record", lambda t, *a, **k: rec0)
    ex = next(e for e in pack["excerpts"] if len(e["text"]) >= 60)
    quote = ex["text"][:60]
    for d in ("packs", "passA", "passB"):
        os.makedirs(tmp_path / d)
    shutil.copy(os.path.join(R.BASE, "packs", f"{TICKER}.json"), tmp_path / "packs")

    def ans(st, val):
        if st == "unknown":
            return {"qid": QID, "status": "unknown", "answer": None, "excerpt_id": None,
                    "quote": None, "reason": "모름"}
        return {"qid": QID, "status": st, "answer": val, "excerpt_id": ex["id"],
                "quote": quote, "reason": "테스트"}

    for x, st, val in (("A", status_a, answer_a), ("B", status_b, answer_b)):
        rec = {"ticker": TICKER, "reader": x, "based_on_record": pack["based_on_record"],
               "answers": [ans(st, val)]}
        (tmp_path / f"pass{x}" / f"{TICKER}.json").write_text(json.dumps(rec), encoding="utf-8")
    return quote


def test_agreed_not_applicable_merges_with_quote_in_note(tmp_path, monkeypatch):
    quote = _setup(tmp_path, monkeypatch, "not_applicable", "not_applicable")
    monkeypatch.setattr(R, "BASE", str(tmp_path))
    prior, core, changed, stats = R.build(TICKER, "2026-10-09")
    rec = Q.build_record(core)          # 예전엔 여기서 QualitativeInputError
    a = next(x for x in rec["answers"] if x["qid"] == QID)
    assert a["status"] == "not_applicable"
    assert a["claim_ids"] == [] and a["answer"] is None
    assert quote in a["note"]
    assert QID in changed
    assert not any(c["claim_id"] == f"READ-{TICKER}-{QID}" for c in core["claims"])


def test_disagreement_stays_unknown(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch, "answered", "answered", True, False)
    monkeypatch.setattr(R, "BASE", str(tmp_path))
    _, core, _, stats = R.build(TICKER, "2026-10-09")
    a = next(x for x in Q.build_record(core)["answers"] if x["qid"] == QID)
    assert a["status"] == "unknown"
    assert next(s for s in stats if s["qid"] == QID)["outcome"] == "판독 불일치"
