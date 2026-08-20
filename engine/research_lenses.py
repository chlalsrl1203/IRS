"""
Research Lenses (P0-14, 2026-08-19) — 정성 조사를 구조로 강제한다.

# SOURCE:
https://github.com/xbtlin/ai-berkshire  (MIT)

# CAPABILITY:
investment lenses / disqualifiers(快速否决清单) / mandatory inversion
("怎么会死" — 무엇이 이 회사를 죽이는가) / 독립적 관점 유지

# IRS_TARGET:
engine/research_lenses.py

# METHOD:
**ADAPT** — 구조는 가져오되 **축은 IRS 자신의 것을 쓴다.**

## 왜 원본의 4대 렌즈를 그대로 안 가져왔나

원본은 段永平·버핏·멍거·리루 4인의 관점을 축으로 삼는다. IRS는 이미 자체 5축을
갖고 있고, 그건 상상한 것이 아니라 **33종목에 실제로 적용해 축적한 절차**다
(CLAUDE.md "정성 심층조사 절차", 2026-08-02 확립 · S등급 7 + A등급 6 + B/C/D 20종목):

    자본배분 품질 · 회계품질 · 거버넌스 · 희석 추이 · 경쟁환경 최신동향

남의 분류 체계로 갈아타면 그 33종목 관측이 새 축에 매핑되지 않아 **축적이
끊긴다.** 그래서 축은 IRS 것을 쓰고, 원본에서는 아래 둘만 가져왔다.

## 가져온 것 2가지

1. **Disqualifier(快速否决清单)** — 감점이 아니라 **즉시 탈락**. IRS의 하드 게이트
   철학(P0-13)과 같은 계열이고, 실제 사례가 있다: TTD의 CEO 내부자거래 혐의
   집단소송, MNDY의 FY2027 목표 철회.
2. **Mandatory Inversion("무엇이 이 회사를 죽이는가")** — `falsification_conditions`
   와 **다르다.** 반증조건은 "이런 실적이 나오면 판정이 틀린 것"이라는 미래
   트리거이고, inversion은 "이 사업이 실패하는 경로"의 열거다. 전자는 검증
   시점을 정하고 후자는 검증 대상을 찾는다 — 보완 관계다.

## ⚠️ 가져오지 **않은** 것과 그 이유

| 원본 기능 | 판정 | 사유 |
|---|---|---|
| 6차원 별점(★★★★★) | **REJECT** | 정확히 "단일 합성점수"다. `docs/irs_evolution_report`의 §31 안티기능 등록부에 이미 등록돼 있고, 중요도가 다른 축을 같은 무게로 만들며 공백을 점수 뒤에 숨긴다 |
| 4대 관점 가중 종합 | **REJECT** | 계획서 §7.1도 "여러 투자 대가를 단순 가중평균하지 않는다"고 명시. 렌즈는 독립적으로 남는다 |
| Benford's Law 이상탐지 | **DEFER** | 흥미롭지만 실증 필요가 0건이다. IRS는 P0-03 이후 SEC 1차자료를 직접 쓴다 |
| PASS/CONDITIONAL/GRAY 어휘 | **DUPLICATE** | `engine/investment_case.py`에 이미 BUY/ADD/HOLD/WATCH/REDUCE/SELL/PASS가 있다. 어휘를 늘리지 않는다 |

# TEST:
tests/test_research_lenses.py
"""

from dataclasses import asdict, dataclass, field

from engine.evidence import Claim, EvidenceMatrix, EvidenceError

# IRS가 33종목에 실제로 적용한 5축(CLAUDE.md 2026-08-02 절차).
STANDARD_LENSES = (
    "capital_allocation",       # 자본배분 품질 — buyback/M&A 가격규율
    "accounting_quality",       # 회계품질 — FCF의 질, 일회성 항목
    "governance",               # 거버넌스 — 내부자 매매, 이중주식, 진행중 소송
    "dilution",                 # 희석 추이 — SBC/FCF, 실제 주식수 증감
    "competitive_landscape",    # 경쟁환경 — 엔진의 주관 가중치가 놓친 신규 위협
)

# 업종별 변형. CLAUDE.md가 "업종별로 5축을 변형할 것"이라 명시하며 실제로 그렇게
# 했다(보험사 ACGL/PGR, 복합기업 SE). 그 사례를 그대로 코드로 옮긴 것이며,
# **새 업종을 상상해서 추가하지 않는다.**
SECTOR_LENS_OVERRIDES = {
    "insurance": (
        "reserve_adequacy",          # 준비금 적정성
        "catastrophe_risk",          # 대재해 리스크
        "underwriting_discipline",   # 언더라이팅 규율
        "governance",
        "dilution",
    ),
    "conglomerate": (
        "segment_capital_allocation",  # 세그먼트별 자본배분
        "affiliate_relationships",     # 계열사 관계(SE-Tencent 등)
        "accounting_quality",
        "governance",
        "dilution",
    ),
}

# 조사 결과가 판정에 미치는 방향. **자동으로 수치를 바꾸지 않는다** —
# "병기, 자동판정 안 함" 원칙(is_insurer·sbc_cross_check와 동일).
LENS_EFFECTS = ("strengthens", "weakens", "neutral", "not_examined")

VALIDATION_STATUS = {
    "lenses": (
        "ECONOMICALLY_SUPPORTED — 5축은 이 저장소가 33종목에 실제로 적용한 절차다. "
        "다만 '이 축들을 보면 더 나은 투자 성과가 난다'는 증거는 0건이다."
    ),
    "disqualifiers": (
        "IMPLEMENTED_NOT_VALIDATED — 즉시 탈락 규칙이 옳다는 실증은 없다. "
        "TTD·MNDY 사례는 사후 관측이지 사전 검증이 아니다."
    ),
}


class LensError(ValueError):
    """정성 조사 계약 위반."""


@dataclass
class LensFinding:
    """
    렌즈 하나의 조사 결과.

    ⚠️ **`effect="not_examined"`를 1급 값으로 둔다.** "조사했는데 별 게 없었다"와
    "조사하지 않았다"는 전혀 다르고, 둘을 섞으면 미조사가 안전 신호로 오독된다
    (P0-01 UNVERIFIED·P0-09 comparable=False와 같은 계열).
    """

    lens: str
    effect: str
    summary: str
    claim_ids: list = field(default_factory=list)   # EvidenceMatrix의 주장 id

    def __post_init__(self):
        if self.effect not in LENS_EFFECTS:
            raise LensError(f"알 수 없는 effect: {self.effect} (허용: {LENS_EFFECTS})")
        if not str(self.summary or "").strip():
            raise LensError(
                f"{self.lens}: summary가 비어 있다. 조사하지 않았다면 "
                f"effect='not_examined'로 그 사실을 적을 것 — 빈칸으로 두면 "
                f"조사한 것처럼 보인다."
            )
        # 조사했다고 주장하려면 근거가 있어야 한다.
        if self.effect in ("strengthens", "weakens") and not self.claim_ids:
            raise LensError(
                f"{self.lens}: effect='{self.effect}'인데 근거 주장(claim_ids)이 "
                f"없다. 판정 방향을 주장하려면 EvidenceMatrix의 주장을 가리켜야 "
                f"한다 — 근거 없는 정성 판단이 정확히 이 프로젝트가 경계해온 것이다."
            )


@dataclass
class Disqualifier:
    """
    즉시 탈락 사유(원본의 快速否决清单). **감점이 아니다.**

    근거를 **필수**로 요구한다 — 근거 없이 종목을 탈락시킬 수 있으면 그 자체가
    임의 판단이 된다(BSX 스크리너 거짓탈락 사건: 배제된 종목은 아무도 다시 안 본다).
    """

    code: str
    statement: str
    claim_ids: list

    def __post_init__(self):
        for f in ("code", "statement"):
            if not str(getattr(self, f) or "").strip():
                raise LensError(f"Disqualifier.{f}가 비어 있다")
        if not self.claim_ids:
            raise LensError(
                f"{self.code}: 근거 주장 없이 즉시 탈락시킬 수 없다. 배제된 종목은 "
                f"아무도 다시 보지 않으므로(BSX 거짓탈락 사건) 근거가 남아야 한다."
            )


@dataclass
class QualitativeReview:
    """
    한 종목의 정성 심층조사 1회. **공식 판정을 바꾸지 않는다** — Gap·RAR·등급은
    건드리지 않고, 권고와 근거만 남긴다(CLAUDE.md 정성조사 절차 4항과 동일).
    """

    entity: str
    as_of: str
    lens_set: str = "standard"
    findings: list = field(default_factory=list)
    disqualifiers: list = field(default_factory=list)
    inversion: list = field(default_factory=list)      # "무엇이 이 회사를 죽이는가"
    confidence_recommendation: int = None              # 엔진 Confidence 대비 권고
    matrix: EvidenceMatrix = None

    def lenses(self) -> tuple:
        return SECTOR_LENS_OVERRIDES.get(self.lens_set, STANDARD_LENSES)

    def add_finding(self, finding: LensFinding):
        if finding.lens not in self.lenses():
            raise LensError(
                f"'{finding.lens}'는 lens_set='{self.lens_set}'의 축이 아니다"
                f"(허용: {self.lenses()}). 축을 즉석에서 늘리면 종목 간 비교가 "
                f"불가능해진다."
            )
        if any(f.lens == finding.lens for f in self.findings):
            raise LensError(f"중복 lens: {finding.lens}")
        if self.matrix is not None:
            known = {c.claim_id for c in self.matrix.claims}
            missing = [i for i in finding.claim_ids if i not in known]
            if missing:
                raise EvidenceError(
                    f"{finding.lens}: EvidenceMatrix에 없는 주장을 가리킨다 "
                    f"({missing}) — 존재하지 않는 근거는 근거가 아니다."
                )
        self.findings.append(finding)
        return self

    def add_disqualifier(self, dq: Disqualifier):
        if self.matrix is not None:
            known = {c.claim_id for c in self.matrix.claims}
            missing = [i for i in dq.claim_ids if i not in known]
            if missing:
                raise EvidenceError(
                    f"{dq.code}: EvidenceMatrix에 없는 주장을 가리킨다 ({missing})")
        self.disqualifiers.append(dq)
        return self

    def unexamined_lenses(self) -> list:
        """조사하지 않은 축. **빈 목록이 아니라는 사실 자체가 결과다.**"""
        done = {f.lens for f in self.findings if f.effect != "not_examined"}
        return [l for l in self.lenses() if l not in done]

    def report(self) -> dict:
        """
        ⚠️ **점수를 내지 않는다.** 원본의 6차원 별점을 가져오지 않은 이유와 같다 —
        축을 합산하면 중요도가 다른 것이 같은 무게가 되고, 조사하지 않은 축이
        평균 뒤에 숨는다.

        `inversion`이 비어 있으면 **미완료**로 표시한다. 원본이 이걸 필수로 둔
        이유가 있다 — "무엇이 이 회사를 죽이는가"를 안 물으면 강세 근거만 쌓인다.
        """
        unexamined = self.unexamined_lenses()
        weakens = [f.lens for f in self.findings if f.effect == "weakens"]
        strengthens = [f.lens for f in self.findings if f.effect == "strengthens"]
        return {
            "entity": self.entity, "as_of": self.as_of, "lens_set": self.lens_set,
            "lenses": list(self.lenses()),
            "n_examined": len(self.lenses()) - len(unexamined),
            "unexamined_lenses": unexamined,
            "weakens": weakens, "strengthens": strengthens,
            "n_disqualifiers": len(self.disqualifiers),
            "disqualifiers": [asdict(d) for d in self.disqualifiers],
            "inversion_complete": bool(self.inversion),
            "inversion": list(self.inversion),
            "confidence_recommendation": self.confidence_recommendation,
            "affects_official_judgment": False,
            "validation_status": VALIDATION_STATUS,
            "note": (
                "점수를 내지 않는다. 조사하지 않은 축(unexamined_lenses)과 "
                "즉시탈락 사유를 먼저 보여주는 것이 목적이며, 공식 Gap·RAR·등급은 "
                "이 조사로 바뀌지 않는다(병기, 자동판정 안 함)."
            ),
        }

    def as_dict(self) -> dict:
        return {
            "entity": self.entity, "as_of": self.as_of, "lens_set": self.lens_set,
            "findings": [asdict(f) for f in self.findings],
            "disqualifiers": [asdict(d) for d in self.disqualifiers],
            "inversion": list(self.inversion),
            "confidence_recommendation": self.confidence_recommendation,
            "matrix": self.matrix.as_dict() if self.matrix else None,
        }


def new_review(entity: str, as_of: str, topic: str = "정성 심층조사",
               lens_set: str = "standard") -> QualitativeReview:
    """조사 1회를 시작한다 — EvidenceMatrix가 함께 붙는다(근거 없는 렌즈 금지)."""
    if lens_set != "standard" and lens_set not in SECTOR_LENS_OVERRIDES:
        raise LensError(
            f"알 수 없는 lens_set: {lens_set} "
            f"(허용: standard, {', '.join(SECTOR_LENS_OVERRIDES)}). "
            f"새 업종 축은 실제 사례가 생겼을 때 추가할 것."
        )
    return QualitativeReview(
        entity=entity, as_of=as_of, lens_set=lens_set,
        matrix=EvidenceMatrix(entity=entity, topic=topic, as_of=as_of),
    )


def claim(review: QualitativeReview, claim_id: str, statement: str,
          materiality: str = "MEDIUM") -> Claim:
    """리뷰의 EvidenceMatrix에 주장을 추가하고 그 객체를 돌려준다."""
    c = Claim(claim_id=claim_id, statement=statement, materiality=materiality)
    review.matrix.add(c)
    return c
