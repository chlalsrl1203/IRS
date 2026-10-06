"""
정성평가 표준입력(QSI v1) 테스트.

고정하는 불변조건:
  ① 질문 은행이 5축과 업종 변형의 모든 축을 덮는다
  ② unknown은 사유 없이 못 쓰고, 모른다면서 답·근거를 달 수 없다
  ③ answered는 근거 주장이 있어야 하고, 사실 주장(requires_primary)은 1차 확인이 있어야 한다
  ④ 분석 시점 이후에 본 증거는 거부한다
  ⑤ 봉인: 한 글자라도 바뀌면 검증 실패, 같은 종목·날짜 덮어쓰기 거부
  ⑥ 점수·판정·자동 변경 함수와 네트워크/LLM 의존이 없다 (§31)
  ⑦ 판정 경로에 배선되지 않는다
  ⑧ scorecard 파생은 불리언만, 모르는 항목은 키를 만들지 않는다
"""
import ast
import copy
import glob
import json
import os
import re
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from engine import qualitative_input as Q  # noqa: E402
from engine.research_lenses import SECTOR_LENS_OVERRIDES, STANDARD_LENSES  # noqa: E402

MODULE = os.path.join(ROOT, "engine", "qualitative_input.py")


def cit(url="https://www.sec.gov/x", observed="2026-10-06"):
    return {"source_key": "sec_edgar", "document": "TEST 10-K (2026-02-01)",
            "location": "Item 7", "observed_date": observed, "url": url}


def ev(verification="VERIFIED_PRIMARY", direction="supports", **ck):
    return {"summary": "근거", "direction": direction, "verification": verification,
            "confidence": "HIGH", "citation": {**cit(), **ck}}


def payload(**over):
    p = {
        "entity": "TEST", "as_of": "2026-10-06", "lens_set": "standard",
        "price_at_analysis": 10.0, "currency": "USD",
        "claims": [{"claim_id": "C1", "statement": "의장·CEO 분리", "materiality": "MEDIUM",
                    "evidence": [ev()]}],
        "answers": [
            {"qid": "gov.chair_separated", "status": "answered", "answer": True,
             "claim_ids": ["C1"]},
            {"qid": "gov.dual_class", "status": "unknown", "note": "프록시 미확보"},
        ],
        "findings": [{"lens": "governance", "effect": "neutral", "summary": "특이사항 없음"}],
        "disqualifiers": [], "inversion": ["핵심 고객 이탈이 회사를 죽인다"],
        "confidence_recommendation": None,
    }
    p.update(over)
    return p


# ① ----------------------------------------------------------------------
def test_bank_covers_every_lens_of_every_lens_set():
    for ls, lenses in [("standard", STANDARD_LENSES)] + list(SECTOR_LENS_OVERRIDES.items()):
        have = {q.lens for q in Q.bank_for(ls)}
        assert set(lenses) <= have, f"{ls}: 질문 없는 축 {set(lenses) - have}"


def test_unknown_lens_set_rejected():
    with pytest.raises(Q.QualitativeInputError):
        Q.bank_for("semiconductor")


# ② ----------------------------------------------------------------------
def test_unknown_requires_reason():
    p = payload()
    p["answers"][1] = {"qid": "gov.dual_class", "status": "unknown"}
    with pytest.raises(Q.QualitativeInputError, match="note"):
        Q.build_record(p)


def test_unknown_cannot_carry_answer_or_claims():
    p = payload()
    p["answers"][1] = {"qid": "gov.dual_class", "status": "unknown", "note": "x",
                       "answer": True}
    with pytest.raises(Q.QualitativeInputError):
        Q.build_record(p)
    p["answers"][1] = {"qid": "gov.dual_class", "status": "unknown", "note": "x",
                       "claim_ids": ["C1"]}
    with pytest.raises(Q.QualitativeInputError):
        Q.build_record(p)


# ③ ----------------------------------------------------------------------
def test_answered_needs_claims_and_existing_claims():
    p = payload()
    p["answers"][0]["claim_ids"] = []
    with pytest.raises(Q.QualitativeInputError, match="claim_ids"):
        Q.build_record(p)
    p["answers"][0]["claim_ids"] = ["NOPE"]
    with pytest.raises(Q.QualitativeInputError, match="존재하지 않는"):
        Q.build_record(p)


def test_answer_value_type_enforced():
    p = payload()
    p["answers"][0]["answer"] = "yes"          # bool 질문에 문자열
    with pytest.raises(Q.QualitativeInputError, match="형식"):
        Q.build_record(p)


def test_requires_primary_rejects_secondary_only_evidence():
    """TYL SBC 3배 오류 형태: 판정을 움직이는 사실을 2차 출처로만 답하면 거부."""
    p = payload()
    p["claims"][0]["evidence"] = [{
        "summary": "블로그 요약", "direction": "supports",
        "verification": "VERIFIED_SECONDARY", "confidence": "MEDIUM",
        "citation": {"source_key": "web_research", "document": "블로그",
                     "location": "본문", "observed_date": "2026-10-06"}}]
    with pytest.raises(Q.QualitativeInputError, match="VERIFIED_PRIMARY"):
        Q.build_record(p)


def test_secondary_evidence_ok_for_non_primary_question():
    p = payload()
    p["claims"][0]["evidence"] = [{
        "summary": "분석가 평가", "direction": "supports",
        "verification": "VERIFIED_SECONDARY", "confidence": "MEDIUM",
        "citation": {"source_key": "web_research", "document": "리포트",
                     "location": "본문", "observed_date": "2026-10-06"}}]
    p["answers"] = [{"qid": "cmp.share_trend", "status": "answered", "answer": "stable",
                     "claim_ids": ["C1"]}]
    p["findings"] = [{"lens": "competitive_landscape", "effect": "neutral", "summary": "x"}]
    assert Q.build_record(p)["answers"][0]["answer"] == "stable"


def test_secondary_cannot_masquerade_as_primary():
    """증거 계약(evidence.py)이 그대로 작동한다 — 재구현이 아니라 재사용의 증거."""
    p = payload()
    p["claims"][0]["evidence"][0]["citation"]["source_key"] = "web_research"
    with pytest.raises(Exception, match="VERIFIED_PRIMARY"):
        Q.build_record(p)


# ④ ----------------------------------------------------------------------
def test_evidence_observed_after_as_of_rejected():
    p = payload()
    p["claims"][0]["evidence"][0]["citation"]["observed_date"] = "2026-10-07"
    with pytest.raises(Q.QualitativeInputError, match="as_of"):
        Q.build_record(p)


def test_bad_dates_rejected():
    with pytest.raises(Q.QualitativeInputError, match="ISO"):
        Q.build_record(payload(as_of="2026/10/06"))


# ⑤ ----------------------------------------------------------------------
def test_seal_detects_any_change(tmp_path):
    rec = Q.build_record(payload())
    assert Q.verify_record(rec)["ok"]
    for mutate in (
        lambda r: r["answers"][0].__setitem__("answer", False),
        lambda r: r["inversion"].append("사후에 끼워 넣음"),
        lambda r: r.__setitem__("price_at_analysis", 11.0),
        lambda r: r["findings"][0].__setitem__("effect", "strengthens"),
    ):
        bad = copy.deepcopy(rec)
        mutate(bad)
        with pytest.raises(Q.QualitativeInputError):
            Q.verify_record(bad)


def test_save_refuses_same_day_overwrite_but_allows_new_date(tmp_path):
    rec = Q.build_record(payload())
    path = Q.save_record(rec, str(tmp_path))
    assert os.path.basename(path) == "TEST_2026-10-06.json"
    with pytest.raises(FileExistsError):
        Q.save_record(rec, str(tmp_path))
    later = Q.build_record(payload(as_of="2026-12-01"))
    Q.save_record(later, str(tmp_path))
    assert len(os.listdir(tmp_path)) == 2     # 과거 기록이 남는다


def test_roundtrip_through_json_keeps_seal(tmp_path):
    rec = Q.build_record(payload())
    path = Q.save_record(rec, str(tmp_path))
    with open(path, encoding="utf-8") as f:
        again = json.load(f)
    assert Q.verify_record(again)["ok"]


# 커버리지: 모른다는 사실을 숨기지 않는다 -----------------------------------
def test_coverage_exposes_unknown_and_unasked():
    rec = Q.build_record(payload())
    c = rec["coverage"]
    assert c["per_lens"]["governance"]["answered"] == 1
    assert c["per_lens"]["governance"]["unknown"] == 1
    n_gov = sum(1 for q in Q.bank_for("standard") if q.lens == "governance")
    assert c["per_lens"]["governance"]["unasked"] == n_gov - 2     # 은행 크기에 고정하지 않는다
    assert c["answered_fraction"] < 0.1
    assert "capital_allocation" in c["unexamined_lenses"]
    assert "문제 없음" in c["note"]


def test_inversion_missing_is_reported_incomplete():
    rec = Q.build_record(payload(inversion=[]))
    assert rec["coverage"]["inversion_complete"] is False


# ⑥ ----------------------------------------------------------------------
def _tree():
    with open(MODULE, encoding="utf-8") as f:
        return ast.parse(f.read())


def test_no_score_verdict_or_auto_change_functions():
    banned = re.compile(r"(^|_)(score|total|overall|composite|verdict|decide|recommend|"
                        r"rating|rank|grade|buy|sell)(_|$)")
    names = [n.name for n in ast.walk(_tree())
             if isinstance(n, (ast.FunctionDef, ast.ClassDef))]
    bad = [n for n in names if banned.search(n.lower())]
    assert not bad, f"종합점수·판정 계열 이름은 금지(§31): {bad}"


def test_no_network_or_llm_dependency():
    mods = set()
    for n in ast.walk(_tree()):
        if isinstance(n, ast.Import):
            mods |= {a.name.split(".")[0] for a in n.names}
        elif isinstance(n, ast.ImportFrom) and n.module:
            mods.add(n.module.split(".")[0])
    forbidden = {"requests", "urllib", "http", "socket", "anthropic", "openai",
                 "numpy", "pandas", "scipy"}
    assert not (mods & forbidden), mods & forbidden


# ⑦ ----------------------------------------------------------------------
def test_not_wired_into_judgment_paths():
    for rel in ("engine/pipeline.py", "engine/expectation_gap_engine.py",
                "engine/portfolio_pipeline.py", "engine/screener.py"):
        with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
            assert "qualitative_input" not in f.read(), f"{rel}에 배선됨"


# ⑧ ----------------------------------------------------------------------
def _full_honesty_payload(honesty_true=("restated_down_3y",)):
    items = ["restated_down_3y", "unfaithful_disclosure", "guidance_miss_3y",
             "promise_kept_record", "voluntary_bad_news"]
    p = payload()
    p["claims"] = [{"claim_id": "H1", "statement": "h", "materiality": "LOW",
                    "evidence": [ev()]}]
    p["answers"] = [{"qid": f"acc.{i}", "status": "answered",
                     "answer": i in honesty_true, "claim_ids": ["H1"]} for i in items]
    p["findings"] = [{"lens": "accounting_quality", "effect": "neutral", "summary": "x"}]
    return p


def test_scorecard_fields_only_for_answered_and_honesty_needs_url():
    rec = Q.build_record(_full_honesty_payload())
    out = Q.scorecard_input_fields(rec)
    f = out["fields"]
    assert f["honesty_checklist"] == {"restated_down_3y": "https://www.sec.gov/x"}
    assert f["honesty_reviewed"] is True
    assert out["wired"] is False
    assert "roiic_5y" in out["not_derivable"]


def test_scorecard_unknown_items_produce_no_key():
    rec = Q.build_record(payload())
    f = Q.scorecard_input_fields(rec)["fields"]
    assert "ceo_succession_policy" not in f          # 질문하지 않음
    assert f["chair_separated"] is True              # 답함
    assert f["honesty_reviewed"] is False            # 5항목 미답


def test_honesty_true_without_url_is_skipped_not_counted():
    p = _full_honesty_payload()
    p["claims"][0]["evidence"][0]["citation"]["url"] = ""
    out = Q.scorecard_input_fields(Q.build_record(p))
    assert out["fields"]["honesty_checklist"] == {}
    assert any(s["reason"] == "no_evidence_url" for s in out["skipped"])


def test_insider_pattern_maps_both_directions():
    p = payload()
    p["claims"] = [{"claim_id": "I1", "statement": "i", "materiality": "MEDIUM",
                    "evidence": [ev()]}]
    p["answers"] = [{"qid": "gov.insider_pattern", "status": "answered",
                     "answer": "opp_net_sell", "claim_ids": ["I1"]}]
    f = Q.scorecard_input_fields(Q.build_record(p))["fields"]
    assert f["opp_insider_net_sell"] is True and f["opp_insider_net_buy"] is False


# 저장소 무결성: qualitative/ ---------------------------------------------
def test_repo_qualitative_records_are_sealed_and_named_correctly():
    for path in sorted(glob.glob(os.path.join(Q.QUALITATIVE_DIR, "*.json"))):
        name = os.path.basename(path)
        m = Q.FNAME_RE.match(name)
        assert m, f"파일명 규칙 위반: {name}"
        with open(path, encoding="utf-8") as f:
            rec = json.load(f)
        assert (rec["entity"], rec["as_of"]) == (m["ticker"], m["date"]), name
        Q.verify_record(rec)
        assert rec["affects_official_judgment"] is False


def test_sparse_qsi_list_matches_threshold():
    """QSI 봉인이 있다는 사실이 '정성조사가 표준화됐다'로 읽히지 않게 한다."""
    import importlib
    intake = importlib.import_module("scripts.qualitative_intake")
    rep = intake.build_coverage()
    by_entity = {r["entity"]: r for r in rep["sealed"]}
    assert rep["sparse_qsi_threshold"] == intake.SPARSE_QSI
    for t in rep["legacy_with_sparse_qsi"]:
        assert by_entity[t]["answered_fraction"] < intake.SPARSE_QSI
    for t, r in by_entity.items():
        if r["answered_fraction"] >= intake.SPARSE_QSI:
            assert t not in rep["legacy_with_sparse_qsi"]
