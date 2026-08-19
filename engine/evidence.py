"""
Evidence Engine (P0-12, 2026-08-19) — 주장에 근거를 강제로 붙인다.

# SOURCE:
https://github.com/noahnan-max/private-equity-investment-dd-skill
https://github.com/DimaMerc/TieOutBench  (source-traced numbers / fabricated-number 탐지)

# CAPABILITY:
Hypothesis → Claim → Evidence → Source → Gap → Contradiction → Investment Implication /
Evidence Matrix · Triangulation · Material Boundary · Red Flags

# IRS_TARGET:
engine/evidence.py

# METHOD:
REIMPLEMENT — 원본은 LLM 프롬프트/스킬 문서(SKILL.md)라 옮길 코드가 없다.
가져온 것은 **구조**다: 가설을 주장으로 쪼개고, 각 주장에 증거를 붙이고,
증거가 없는 지점(gap)과 서로 어긋나는 지점(contradiction)을 **명시적으로 남긴다.**

# WHY — 이 저장소의 구체적 결함

`engine/thesis.py`의 `build_evidence(observed_date, summary, direction, source, ...)`에서
`source`는 **자유 문자열**이다. §15 CORE EVIDENCE CONTRACT가 요구하는
Document·Location·Verification·Confidence가 전혀 없다. 그래서:

- **TYL SBC 3배 오류**(2026-08-05): 리서치 에이전트가 2차 출처의 잘못된 FCF를
  인용해 SBC/FCF를 62%로 적었고 실제는 24.4%였다. 인용에 문서·위치가 없어
  **어디서 왔는지 되짚을 수 없었다.**
- **S/A등급 13종목 정성조사**(2026-08-03/04): 발견 전부가 채팅 요약으로만
  남아 있다. CLAUDE.md가 스스로 "ledger나 Notion에 반영 안 됨"이라 적어뒀다.
- **B/C/D등급 20종목 경량검증**: 같은 상태.

즉 이 프로젝트의 정량 경로에는 ledger·provenance·PIT가 있는데 **정성 경로에는
아무 계약이 없다.**

# TEST:
tests/test_evidence.py

---

## ⚠️ 이 모듈이 하지 않는 것

- **LLM 출력을 출처로 인정하지 않는다**(§15 마지막 문장). `SOURCE_KINDS`에
  그런 항목을 두지 않으며, 근거는 항상 사람이 확인할 수 있는 문서·데이터를
  가리켜야 한다.
- **주장의 참·거짓을 판정하지 않는다.** 증거가 붙어 있는지, 어긋나는지,
  비어 있는지만 본다. 판정은 분석자의 몫이다.
- **신뢰도를 자동 계산하지 않는다.** `confidence`는 분석자가 고르는 라벨이며
  확률이 아니다(이 저장소의 `Confidence`가 UNCALIBRATED인 것과 같은 이유).
"""

from dataclasses import asdict, dataclass, field

from engine.data.governance.source_registry import get_source

# 검증 상태. **"확인 안 함"과 "확인했으나 불일치"를 구분한다** — 둘을 섞으면
# 미확인이 안전 신호로 오독된다(P0-01 UNVERIFIED와 같은 계열).
VERIFICATION_STATES = (
    "VERIFIED_PRIMARY",     # 1차 자료로 직접 확인
    "VERIFIED_SECONDARY",   # 2차 출처끼리 교차확인(1차는 못 봄)
    "UNVERIFIED",           # 확인하지 않았다
    "CONTRADICTED",         # 확인했더니 다른 출처와 어긋난다
)

# 증거가 주장에 대해 갖는 방향.
EVIDENCE_DIRECTIONS = ("supports", "contradicts", "neutral")

# 신뢰도 라벨. **확률이 아니다.**
CONFIDENCE_LEVELS = ("HIGH", "MEDIUM", "LOW")

VALIDATION_STATUS = {
    "confidence_levels": (
        "UNCALIBRATED — HIGH/MEDIUM/LOW는 분석자가 고르는 라벨이며 확률로 "
        "해석하면 안 된다. 실현 결과와 대조된 적이 없다."
    ),
    "claim_status": (
        "SOFTWARE_VALIDATED — 집계 규칙은 투명하고 테스트로 고정돼 있으나, "
        "이 상태가 투자 성과와 관계있다는 증거는 0건이다."
    ),
}


class EvidenceError(ValueError):
    """증거 계약 위반. 조용히 넘어가면 계약 자체가 무의미해진다."""


def _require(value, label):
    text = str(value or "").strip()
    if not text:
        raise EvidenceError(
            f"{label}이(가) 비어 있다. 증거 계약은 빈칸을 허용하지 않는다 — "
            f"모르면 그 사실을 적을 것(예: location='미확인')."
        )
    return text


@dataclass(frozen=True)
class Citation:
    """
    §15의 Source → Document → Location → Time.

    `location`을 **필수**로 둔 이유: TYL SBC 3배 오류가 "어느 문서 어디"를
    적지 않아 되짚을 수 없었다. 모르면 `"미확인"`이라고 적게 하되 빈칸은 막는다 —
    빈칸은 "위치가 없다"로 오독되지만 "미확인"은 오독되지 않는다.
    """

    source_key: str            # SOURCE_REGISTRY 키
    document: str              # 문서 신원 (예: "BSX 10-K (2026-02-17)")
    location: str              # 문서 내 위치 (예: "Item 7 MD&A", "미확인")
    observed_date: str         # 우리가 본 날
    url: str = ""
    quote: str = ""            # 원문 인용(선택). 요약이 아니라 그대로 옮긴 것만

    def __post_init__(self):
        get_source(self.source_key)          # 미등록 출처면 KeyError
        _require(self.document, "document")
        _require(self.location, "location")
        _require(self.observed_date, "observed_date")

    @classmethod
    def from_filing(cls, doc, location: str, observed_date: str, quote: str = ""):
        """`FilingDocument`(P0-11)에서 만든다 — 문서 신원을 손으로 안 적게."""
        return cls(source_key="sec_edgar", document=doc.citation(),
                   location=location, observed_date=observed_date,
                   url=doc.url, quote=quote)

    @property
    def authority(self) -> str:
        return get_source(self.source_key).authority


@dataclass
class Evidence:
    """§15의 Evidence → Verification → Confidence."""

    summary: str
    direction: str
    citation: Citation
    verification: str
    confidence: str
    metric: str = None
    value: float = None
    note: str = ""

    def __post_init__(self):
        _require(self.summary, "summary")
        if self.direction not in EVIDENCE_DIRECTIONS:
            raise EvidenceError(f"알 수 없는 방향: {self.direction}")
        if self.verification not in VERIFICATION_STATES:
            raise EvidenceError(f"알 수 없는 검증상태: {self.verification}")
        if self.confidence not in CONFIDENCE_LEVELS:
            raise EvidenceError(f"알 수 없는 신뢰도: {self.confidence}")
        if not isinstance(self.citation, Citation):
            raise EvidenceError(
                "citation은 Citation이어야 한다. 자유 문자열 출처는 "
                "되짚을 수 없다(TYL SBC 3배 오류)."
            )
        # 2차 출처를 1차로 표시하는 것을 막는다 — 이게 정확히 TYL 사고의 형태다.
        if (self.verification == "VERIFIED_PRIMARY"
                and self.citation.authority not in ("PRIMARY_FILING", "REGULATOR")):
            raise EvidenceError(
                f"VERIFIED_PRIMARY인데 인용 출처의 권위가 "
                f"'{self.citation.authority}'다. 2차 출처를 1차 확인으로 "
                f"표시할 수 없다 — TYL SBC 3배 오류가 정확히 이 형태였다."
            )


@dataclass
class Claim:
    """
    검증 대상 주장 하나. **증거 없이 만들 수 있다** — 그게 gap이고, gap을
    숨기지 않는 것이 이 구조의 목적이다(원본 스킬의 Evidence Matrix).
    """

    claim_id: str
    statement: str
    materiality: str = "MEDIUM"          # 투자판단에 얼마나 중요한가
    evidence: list = field(default_factory=list)

    def __post_init__(self):
        _require(self.claim_id, "claim_id")
        _require(self.statement, "statement")
        if self.materiality not in CONFIDENCE_LEVELS:
            raise EvidenceError(f"알 수 없는 중요도: {self.materiality}")

    def add(self, ev: Evidence):
        if not isinstance(ev, Evidence):
            raise EvidenceError("Evidence만 붙일 수 있다")
        self.evidence.append(ev)
        return self

    def status(self) -> dict:
        """
        주장의 상태. **투명한 집계이며 숨은 가중치가 없다**(thesis.py와 동일 원칙).

        - `UNSUPPORTED`  증거 0건 -> gap
        - `CONTRADICTED` 반대 증거가 있다. **찬성 증거가 아무리 많아도 이긴다** —
          "그래도 좋아 보인다"고 넘어가는 것이 사후합리화다(thesis.py의
          INVALIDATED 규칙과 같은 계열)
        - `SUPPORTED`    찬성 증거만 있다
        - `NEUTRAL`      중립 증거만 있다
        """
        if not self.evidence:
            return {"claim_id": self.claim_id, "status": "UNSUPPORTED",
                    "n_evidence": 0, "gap": True,
                    "reason": "증거가 하나도 없다"}
        dirs = [e.direction for e in self.evidence]
        contra = [e for e in self.evidence if e.direction == "contradicts"]
        if contra:
            status = "CONTRADICTED"
            reason = (f"반대 증거 {len(contra)}건이 있다. 찬성 증거 수와 무관하게 "
                      f"이 상태가 우선한다.")
        elif "supports" in dirs:
            status = "SUPPORTED"
            reason = f"찬성 증거 {dirs.count('supports')}건"
        else:
            status = "NEUTRAL"
            reason = "중립 증거만 있다"
        return {
            "claim_id": self.claim_id, "status": status, "gap": False,
            "n_evidence": len(self.evidence), "reason": reason,
            "verification": {v: sum(1 for e in self.evidence if e.verification == v)
                             for v in VERIFICATION_STATES
                             if any(e.verification == v for e in self.evidence)},
            "triangulated": self.is_triangulated(),
            "primary_backed": any(e.verification == "VERIFIED_PRIMARY"
                                  for e in self.evidence),
        }

    def is_triangulated(self) -> bool:
        """
        **서로 다른 출처** 2개 이상이 같은 방향을 가리키는가(원본 스킬의
        Triangulation). 같은 출처를 두 번 인용하는 것은 삼각검증이 아니다 —
        IWM P/E 사건이 보여준 대로 한 출처의 집계방식 편향은 반복해도 안 드러난다.
        """
        for d in ("supports", "contradicts"):
            keys = {e.citation.source_key for e in self.evidence if e.direction == d}
            if len(keys) >= 2:
                return True
        return False


@dataclass
class EvidenceMatrix:
    """
    한 종목·한 조사의 주장 묶음. §15 계약을 만족하는 최소 단위다.

    ⚠️ **점수를 내지 않는다.** 주장 몇 개가 지지됐는지 세어 단일 점수로 만들면
    (a) 중요도가 다른 주장이 같은 무게가 되고 (b) gap이 점수 뒤에 숨는다.
    이 저장소가 §31 안티기능 등록부에 "단일 합성점수"를 올려둔 것과 같은 이유다.
    """

    entity: str
    topic: str
    as_of: str
    claims: list = field(default_factory=list)

    def add(self, claim: Claim):
        if any(c.claim_id == claim.claim_id for c in self.claims):
            raise EvidenceError(f"중복 claim_id: {claim.claim_id}")
        self.claims.append(claim)
        return self

    def gaps(self) -> list:
        """증거가 없는 주장. **중요도 순으로** 돌려준다 — 중요한 공백이 먼저 보여야 한다."""
        order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        out = [c for c in self.claims if not c.evidence]
        return sorted(out, key=lambda c: order[c.materiality])

    def contradictions(self) -> list:
        return [c for c in self.claims if c.status()["status"] == "CONTRADICTED"]

    def unverified_material_claims(self) -> list:
        """
        중요도 HIGH인데 1차 확인이 없는 주장. **TYL 사고의 조기 경보**다 —
        판정에 영향을 줄 수 있는 수치가 2차 출처에만 기대고 있는 상태.
        """
        return [c for c in self.claims
                if c.materiality == "HIGH" and c.evidence
                and not c.status()["primary_backed"]]

    def report(self) -> dict:
        gaps = self.gaps()
        contra = self.contradictions()
        weak = self.unverified_material_claims()
        return {
            "entity": self.entity, "topic": self.topic, "as_of": self.as_of,
            "n_claims": len(self.claims),
            "n_gaps": len(gaps),
            "gaps": [{"claim_id": c.claim_id, "statement": c.statement,
                      "materiality": c.materiality} for c in gaps],
            "n_contradictions": len(contra),
            "contradictions": [c.status() for c in contra],
            "n_material_without_primary": len(weak),
            "material_without_primary": [
                {"claim_id": c.claim_id, "statement": c.statement,
                 "sources": sorted({e.citation.source_key for e in c.evidence})}
                for c in weak],
            "claims": [c.status() for c in self.claims],
            "validation_status": VALIDATION_STATUS,
            "note": (
                "점수를 내지 않는다. 공백(gap)과 모순(contradiction)을 먼저 "
                "보여주는 것이 이 리포트의 목적이며, 지지된 주장 수를 세어 "
                "단일 점수로 만들면 공백이 점수 뒤에 숨는다."
            ),
        }

    def as_dict(self) -> dict:
        return {
            "entity": self.entity, "topic": self.topic, "as_of": self.as_of,
            "claims": [
                {"claim_id": c.claim_id, "statement": c.statement,
                 "materiality": c.materiality,
                 "evidence": [
                     {**{k: v for k, v in asdict(e).items() if k != "citation"},
                      "citation": asdict(e.citation)}
                     for e in c.evidence]}
                for c in self.claims],
        }
