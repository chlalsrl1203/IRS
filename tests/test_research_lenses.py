"""
P0-14 Research Lenses 테스트.

# SOURCE:
https://github.com/xbtlin/ai-berkshire (MIT)

고정하는 불변조건:
  ① 축은 IRS 자신의 5축이다 (33종목 축적이 끊기지 않도록)
  ② "조사 안 함"과 "조사했는데 별 게 없음"을 구분한다
  ③ 판정 방향을 주장하려면 근거 주장을 가리켜야 한다
  ④ 즉시 탈락에도 근거가 필요하다 (BSX 거짓탈락 사건)
  ⑤ 점수를 내지 않는다 (원본의 6차원 별점 = 안티기능)
  ⑥ inversion을 안 하면 미완료로 표시된다
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.evidence import Citation, Evidence, EvidenceError  # noqa: E402
from engine.research_lenses import (  # noqa: E402
    LENS_EFFECTS, SECTOR_LENS_OVERRIDES, STANDARD_LENSES, VALIDATION_STATUS,
    Disqualifier, LensError, LensFinding, claim, new_review,
)


def cite(source_key="sec_edgar"):
    return Citation(source_key=source_key, document="TTD 10-K (2026-02-14)",
                    location="Item 3 Legal Proceedings", observed_date="2026-08-19")


def ev(direction="contradicts", verification="VERIFIED_PRIMARY"):
    return Evidence(summary="증권사기 집단소송 기각동의 기각", direction=direction,
                    citation=cite(), verification=verification, confidence="HIGH")


def review_with_claim(cid="G1", materiality="HIGH"):
    r = new_review("TTD", "2026-08-19")
    claim(r, cid, "CEO가 내부자거래 혐의로 지목됐다", materiality).add(ev())
    return r


# ── ① IRS 자신의 축 ──────────────────────────────────────────────────────
def test_standard_lenses_are_the_five_axes_this_project_actually_used():
    """
    CLAUDE.md 2026-08-02 절차의 5축. 남의 분류로 갈아타면 33종목 관측이
    새 축에 매핑되지 않아 축적이 끊긴다.
    """
    assert STANDARD_LENSES == (
        "capital_allocation", "accounting_quality", "governance",
        "dilution", "competitive_landscape")


def test_sector_overrides_match_the_documented_real_cases():
    """보험사(ACGL·PGR)·복합기업(SE)은 실제로 축을 변형해 조사했다."""
    assert "reserve_adequacy" in SECTOR_LENS_OVERRIDES["insurance"]
    assert "affiliate_relationships" in SECTOR_LENS_OVERRIDES["conglomerate"]


def test_unknown_sector_is_rejected_rather_than_invented():
    with pytest.raises(LensError, match="실제 사례가 생겼을 때"):
        new_review("X", "2026-08-19", lens_set="biotech")


def test_lens_outside_the_set_is_rejected():
    r = new_review("ACGL", "2026-08-19", lens_set="insurance")
    with pytest.raises(LensError, match="축을 즉석에서 늘리면"):
        r.add_finding(LensFinding(lens="competitive_landscape", effect="neutral",
                                  summary="x"))


# ── ② 조사 안 함 vs 별 게 없음 ───────────────────────────────────────────
def test_not_examined_is_a_first_class_value():
    """미조사를 안전 신호로 오독하지 않는다."""
    assert "not_examined" in LENS_EFFECTS
    r = new_review("TTD", "2026-08-19")
    r.add_finding(LensFinding(lens="dilution", effect="not_examined",
                              summary="SBC 자료를 확보하지 못했다"))
    assert "dilution" in r.unexamined_lenses()          # 조사한 것으로 세지 않는다


def test_neutral_finding_counts_as_examined():
    r = new_review("TTD", "2026-08-19")
    r.add_finding(LensFinding(lens="dilution", effect="neutral",
                              summary="SBC/FCF 19%로 특이사항 없음"))
    assert "dilution" not in r.unexamined_lenses()


def test_empty_summary_is_rejected():
    with pytest.raises(LensError, match="빈칸으로 두면"):
        LensFinding(lens="governance", effect="not_examined", summary="  ")


def test_report_lists_unexamined_lenses_explicitly():
    r = review_with_claim()
    r.add_finding(LensFinding(lens="governance", effect="weakens",
                              summary="CEO 내부자거래 혐의", claim_ids=["G1"]))
    rep = r.report()
    assert rep["n_examined"] == 1
    assert set(rep["unexamined_lenses"]) == set(STANDARD_LENSES) - {"governance"}


# ── ③ 방향 주장에는 근거가 필요하다 ──────────────────────────────────────
def test_directional_finding_without_claims_is_rejected():
    """근거 없는 정성 판단이 정확히 이 프로젝트가 경계해온 것이다."""
    with pytest.raises(LensError, match="근거 없는 정성 판단"):
        LensFinding(lens="governance", effect="weakens", summary="느낌이 안 좋다")


def test_finding_pointing_to_nonexistent_claim_is_rejected():
    r = new_review("TTD", "2026-08-19")
    with pytest.raises(EvidenceError, match="존재하지 않는 근거는 근거가 아니다"):
        r.add_finding(LensFinding(lens="governance", effect="weakens",
                                  summary="x", claim_ids=["NOPE"]))


def test_finding_backed_by_a_real_claim_is_accepted():
    r = review_with_claim()
    r.add_finding(LensFinding(lens="governance", effect="weakens",
                              summary="CEO 내부자거래 혐의 소송 본안 진행",
                              claim_ids=["G1"]))
    assert r.report()["weakens"] == ["governance"]


# ── ④ 즉시 탈락에도 근거가 필요하다 ──────────────────────────────────────
def test_disqualifier_requires_evidence():
    """배제된 종목은 아무도 다시 보지 않는다(BSX 거짓탈락 사건)."""
    with pytest.raises(LensError, match="근거 주장 없이 즉시 탈락"):
        Disqualifier(code="DQ.INTEGRITY", statement="경영진 무결성 문제",
                     claim_ids=[])


def test_disqualifier_pointing_to_unknown_claim_is_rejected():
    r = new_review("TTD", "2026-08-19")
    with pytest.raises(EvidenceError, match="없는 주장"):
        r.add_disqualifier(Disqualifier(code="DQ.X", statement="x",
                                        claim_ids=["GHOST"]))


def test_disqualifier_is_surfaced_in_the_report():
    r = review_with_claim()
    r.add_disqualifier(Disqualifier(
        code="DQ.INTEGRITY",
        statement="CEO가 내부자거래 혐의로 직접 지목된 집단소송이 본안 진행 중",
        claim_ids=["G1"]))
    rep = r.report()
    assert rep["n_disqualifiers"] == 1
    assert rep["disqualifiers"][0]["code"] == "DQ.INTEGRITY"


# ── ⑤ 점수를 내지 않는다 ─────────────────────────────────────────────────
def test_report_contains_no_composite_score():
    """
    원본의 6차원 별점(★★★★★)은 정확히 '단일 합성점수'다 — §31 안티기능
    등록부 항목이며, 조사하지 않은 축이 평균 뒤에 숨는다.
    """
    rep = review_with_claim().report()
    for banned in ("score", "stars", "rating", "total", "average"):
        assert not any(banned in k for k in rep), banned
    assert "점수를 내지 않는다" in rep["note"]


def test_review_never_claims_to_change_official_judgment():
    assert review_with_claim().report()["affects_official_judgment"] is False


# ── ⑥ inversion ──────────────────────────────────────────────────────────
def test_missing_inversion_is_flagged_incomplete():
    """'무엇이 이 회사를 죽이는가'를 안 물으면 강세 근거만 쌓인다."""
    assert review_with_claim().report()["inversion_complete"] is False


def test_inversion_present_marks_complete():
    r = review_with_claim()
    r.inversion = ["Amazon DSP가 점유율을 계속 배증하면 광고주 이탈",
                   "소송 패소 시 경영진 교체와 신뢰 상실"]
    rep = r.report()
    assert rep["inversion_complete"] is True and len(rep["inversion"]) == 2


# ── 인식론적 지위 / 직렬화 ───────────────────────────────────────────────
def test_validation_status_declares_no_outcome_evidence():
    assert "증거는 0건" in VALIDATION_STATUS["lenses"]
    assert "IMPLEMENTED_NOT_VALIDATED" in VALIDATION_STATUS["disqualifiers"]


def test_review_serializes_with_evidence_matrix():
    import json
    r = review_with_claim()
    r.add_finding(LensFinding(lens="governance", effect="weakens",
                              summary="x", claim_ids=["G1"]))
    d = json.loads(json.dumps(r.as_dict()))
    assert d["matrix"]["claims"][0]["claim_id"] == "G1"
    assert d["findings"][0]["lens"] == "governance"


def test_duplicate_lens_is_rejected():
    r = new_review("TTD", "2026-08-19")
    r.add_finding(LensFinding(lens="dilution", effect="neutral", summary="a"))
    with pytest.raises(LensError, match="중복 lens"):
        r.add_finding(LensFinding(lens="dilution", effect="neutral", summary="b"))
