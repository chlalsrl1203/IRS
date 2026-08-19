"""
P0-11 SEC Document Index · P0-12 Evidence Engine 테스트.

# SOURCE:
https://github.com/dgunning/edgartools ·
https://github.com/noahnan-max/private-equity-investment-dd-skill ·
https://github.com/DimaMerc/TieOutBench

고정하는 불변조건:
  ① 2차 출처를 1차 확인으로 표시할 수 없다 (TYL SBC 3배 오류의 형태)
  ② 인용에 문서·위치가 없으면 증거가 성립하지 않는다
  ③ 반대 증거는 찬성 증거 수와 무관하게 우선한다 (사후합리화 방지)
  ④ 공백(gap)과 모순을 점수 뒤에 숨기지 않는다
  ⑤ 삼각검증은 **서로 다른 출처** 2개 이상을 요구한다
  ⑥ 문서 이력이 불완전하면 "없다"로 단정하지 않는다
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.data.providers.sec_documents import (  # noqa: E402
    FilingDocument, SecDocumentIndex, documents_as_dicts,
)
from engine.evidence import (  # noqa: E402
    CONFIDENCE_LEVELS, VALIDATION_STATUS, VERIFICATION_STATES, Citation, Claim,
    Evidence, EvidenceError, EvidenceMatrix,
)


SUBMISSIONS = {
    "filings": {
        "recent": {
            "accessionNumber": ["0000885725-26-000053", "0000885725-26-000012"],
            "filingDate": ["2026-08-03", "2026-02-17"],
            "reportDate": ["2026-06-30", "2025-12-31"],
            "form": ["10-Q", "10-K"],
            "primaryDocument": ["bsx-20260630.htm", "bsx-20251231.htm"],
            "primaryDocDescription": ["10-Q", "10-K"],
            "isXBRL": [1, 1],
        },
        "files": [{"name": "old.json", "filingFrom": "2010-06-22",
                   "filingTo": "2020-08-25", "filingCount": 2001}],
    }
}


def index(payload=SUBMISSIONS, cik="0000885725"):
    return SecDocumentIndex(fetch_json=lambda url: payload,
                            resolve_cik=lambda t, ua=None: cik)


def cite(source_key="sec_edgar", location="Item 8 F-12"):
    return Citation(source_key=source_key, document="BSX 10-K (2026-02-17)",
                    location=location, observed_date="2026-08-19")


# ── P0-11 문서 신원 ──────────────────────────────────────────────────────
def test_filing_index_builds_resolvable_urls():
    idx = index().fetch_filing_index("BSX")
    tenk = [d for d in idx["documents"] if d.form == "10-K"][0]
    assert tenk.url == (
        "https://www.sec.gov/Archives/edgar/data/885725/"
        "000088572526000012/bsx-20251231.htm")
    assert tenk.citation("Item 7 MD&A") == "BSX 10-K (2026-02-17), Item 7 MD&A"


def test_filing_date_and_report_date_are_distinct():
    """`available_at` vs `period_end`와 같은 구분 — 섞으면 PIT가 무의미해진다."""
    d = [x for x in index().fetch_filing_index("BSX")["documents"]
         if x.form == "10-K"][0]
    assert d.filing_date == "2026-02-17" and d.report_date == "2025-12-31"


def test_fiscal_year_lookup_matches_on_report_date_not_filing_date():
    """filing_date로 매칭하면 이듬해 초에 제출된 연차보고서를 놓친다."""
    d = index().find_filing_for_fiscal_year("BSX", 2025)
    assert d is not None and d.form == "10-K" and d.report_date == "2025-12-31"
    assert index().find_filing_for_fiscal_year("BSX", 2019) is None   # 추측하지 않는다


def test_incomplete_history_is_declared_not_silently_treated_as_absent():
    """SEC가 오래된 공시를 별도 파일로 분리한다 — '여기 없다'가 '공시가 없다'는 아니다."""
    idx = index().fetch_filing_index("BSX")
    assert idx["truncated"] is True
    assert any("[이력 불완전]" in x for x in idx["limitations"])


def test_document_index_refuses_to_pretend_it_has_financials():
    with pytest.raises(NotImplementedError, match="문서 신원만"):
        index().fetch_annual_financials("BSX")


def test_unresolved_ticker_returns_reason_not_a_guess():
    idx = SecDocumentIndex(fetch_json=lambda url: SUBMISSIONS,
                           resolve_cik=lambda t, ua=None: None
                           ).fetch_filing_index("NOPE")
    assert idx["documents"] == []
    assert any("[티커 미해결]" in x for x in idx["limitations"])


def test_documents_serialize_without_external_objects():
    import json
    json.dumps(documents_as_dicts(index().fetch_filing_index("BSX")["documents"]))


# ── P0-12 ① 2차를 1차로 표시할 수 없다 ──────────────────────────────────
def test_secondary_source_cannot_be_marked_verified_primary():
    """TYL SBC 3배 오류가 정확히 이 형태였다 — 2차 출처를 1차 확인으로 취급."""
    with pytest.raises(EvidenceError, match="2차 출처를 1차 확인으로"):
        Evidence(summary="SBC/FCF 62%", direction="supports",
                 citation=cite(source_key="web_research", location="블로그 요약"),
                 verification="VERIFIED_PRIMARY", confidence="HIGH")


def test_primary_filing_can_be_marked_verified_primary():
    e = Evidence(summary="SBC/FCF 24.4%", direction="supports", citation=cite(),
                 verification="VERIFIED_PRIMARY", confidence="HIGH")
    assert e.citation.authority == "PRIMARY_FILING"


def test_secondary_source_may_still_be_recorded_as_secondary():
    """2차 출처를 금지하는 게 아니라 **1차로 위장하는 것**을 금지한다."""
    e = Evidence(summary="경쟁사 점유율 확대", direction="contradicts",
                 citation=cite(source_key="web_research", location="미확인"),
                 verification="VERIFIED_SECONDARY", confidence="LOW")
    assert e.verification == "VERIFIED_SECONDARY"


# ── ② 인용 계약 ──────────────────────────────────────────────────────────
def test_citation_requires_document_and_location():
    with pytest.raises(EvidenceError, match="location"):
        Citation(source_key="sec_edgar", document="BSX 10-K", location="",
                 observed_date="2026-08-19")
    # 모르면 "미확인"이라고 적을 수 있다 — 빈칸만 막는다
    assert cite(location="미확인").location == "미확인"


def test_free_string_source_is_rejected():
    with pytest.raises(EvidenceError, match="자유 문자열 출처"):
        Evidence(summary="x", direction="supports", citation="10-K 어딘가",
                 verification="UNVERIFIED", confidence="LOW")


def test_unregistered_source_key_is_rejected():
    with pytest.raises(KeyError, match="등록되지 않은 출처"):
        cite(source_key="bloomberg_terminal")


def test_citation_from_filing_document_avoids_hand_typing():
    doc = [d for d in index().fetch_filing_index("BSX")["documents"]
           if d.form == "10-K"][0]
    c = Citation.from_filing(doc, location="Item 8", observed_date="2026-08-19")
    assert c.document == "BSX 10-K (2026-02-17)" and c.url == doc.url
    assert c.source_key == "sec_edgar"


# ── ③ 반대 증거 우선 ─────────────────────────────────────────────────────
def test_contradicting_evidence_outranks_any_number_of_supports():
    """'그래도 좋아 보인다'고 넘어가는 것이 정확히 사후합리화다."""
    c = Claim(claim_id="C1", statement="해자가 유지된다")
    for i in range(5):
        c.add(Evidence(summary=f"지지 {i}", direction="supports", citation=cite(),
                       verification="VERIFIED_PRIMARY", confidence="HIGH"))
    c.add(Evidence(summary="점유율 하락", direction="contradicts",
                   citation=cite(source_key="stockanalysis", location="미확인"),
                   verification="VERIFIED_SECONDARY", confidence="LOW"))
    s = c.status()
    assert s["status"] == "CONTRADICTED"
    assert "찬성 증거 수와 무관하게" in s["reason"]


def test_claim_without_evidence_is_a_gap_not_neutral():
    s = Claim(claim_id="C2", statement="경영진이 유능하다").status()
    assert s["status"] == "UNSUPPORTED" and s["gap"] is True


# ── ④ 공백·모순을 숨기지 않는다 ──────────────────────────────────────────
def test_report_surfaces_gaps_ordered_by_materiality():
    m = EvidenceMatrix(entity="BSX", topic="해자", as_of="2026-08-19")
    m.add(Claim(claim_id="LOW1", statement="사소한 것", materiality="LOW"))
    m.add(Claim(claim_id="HIGH1", statement="핵심 가정", materiality="HIGH"))
    m.add(Claim(claim_id="MED1", statement="중간", materiality="MEDIUM"))
    rep = m.report()
    assert rep["n_gaps"] == 3
    assert [g["claim_id"] for g in rep["gaps"]] == ["HIGH1", "MED1", "LOW1"]


def test_report_produces_no_single_score():
    """단일 합성점수는 §31 안티기능 등록부 항목이다 — 공백이 점수 뒤에 숨는다."""
    m = EvidenceMatrix(entity="BSX", topic="해자", as_of="2026-08-19")
    m.add(Claim(claim_id="C1", statement="x"))
    rep = m.report()
    assert not any(k in rep for k in ("score", "total_score", "evidence_score"))
    assert "점수를 내지 않는다" in rep["note"]


def test_material_claim_without_primary_backing_is_flagged():
    """TYL 사고의 조기 경보 — 판정에 영향 줄 수치가 2차 출처에만 기댄 상태."""
    m = EvidenceMatrix(entity="TYL", topic="SBC", as_of="2026-08-19")
    c = Claim(claim_id="SBC", statement="SBC/FCF가 62%다", materiality="HIGH")
    c.add(Evidence(summary="웹 요약", direction="supports",
                   citation=cite(source_key="web_research", location="미확인"),
                   verification="VERIFIED_SECONDARY", confidence="MEDIUM"))
    m.add(c)
    rep = m.report()
    assert rep["n_material_without_primary"] == 1
    assert rep["material_without_primary"][0]["sources"] == ["web_research"]


def test_duplicate_claim_id_is_rejected():
    m = EvidenceMatrix(entity="BSX", topic="t", as_of="2026-08-19")
    m.add(Claim(claim_id="C1", statement="x"))
    with pytest.raises(EvidenceError, match="중복 claim_id"):
        m.add(Claim(claim_id="C1", statement="y"))


# ── ⑤ 삼각검증 ──────────────────────────────────────────────────────────
def test_triangulation_requires_two_different_sources():
    """
    같은 출처를 두 번 인용하는 건 삼각검증이 아니다 — IWM P/E 사건이 보여준
    대로 한 출처의 집계방식 편향은 반복해도 드러나지 않는다.
    """
    c = Claim(claim_id="C1", statement="x")
    c.add(Evidence(summary="a", direction="supports", citation=cite(),
                   verification="VERIFIED_PRIMARY", confidence="HIGH"))
    c.add(Evidence(summary="b", direction="supports", citation=cite(location="Item 9"),
                   verification="VERIFIED_PRIMARY", confidence="HIGH"))
    assert c.is_triangulated() is False          # 같은 출처 2건
    c.add(Evidence(summary="c", direction="supports",
                   citation=cite(source_key="stockanalysis", location="미확인"),
                   verification="VERIFIED_SECONDARY", confidence="MEDIUM"))
    assert c.is_triangulated() is True


# ── 어휘·인식론 ──────────────────────────────────────────────────────────
def test_llm_output_is_not_an_allowed_source_kind():
    """§15: LLM 출력 자체를 source로 인정하지 않는다."""
    from engine.provenance import SOURCE_KINDS
    assert not any("llm" in k or "model" in k for k in SOURCE_KINDS)


def test_confidence_is_declared_uncalibrated():
    assert "UNCALIBRATED" in VALIDATION_STATUS["confidence_levels"]
    assert set(CONFIDENCE_LEVELS) == {"HIGH", "MEDIUM", "LOW"}
    assert "UNVERIFIED" in VERIFICATION_STATES
    assert "CONTRADICTED" in VERIFICATION_STATES


def test_matrix_serializes_with_full_citations():
    import json
    m = EvidenceMatrix(entity="BSX", topic="t", as_of="2026-08-19")
    c = Claim(claim_id="C1", statement="x")
    c.add(Evidence(summary="a", direction="supports", citation=cite(),
                   verification="VERIFIED_PRIMARY", confidence="HIGH"))
    m.add(c)
    d = json.loads(json.dumps(m.as_dict()))
    assert d["claims"][0]["evidence"][0]["citation"]["location"] == "Item 8 F-12"
