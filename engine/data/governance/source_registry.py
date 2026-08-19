"""
Source Registry (P0-01, 2026-08-19) — "이 출처를 이 용도로 써도 되는가"에 답한다.

# SOURCE:
https://github.com/simonlin1212/global-stock-data  (Apache-2.0)

# CAPABILITY:
official-source-first / source registry / source authority / compliance tier /
licensing metadata / rate limits / freshness / reliability

# IRS_TARGET:
engine/data/governance/source_registry.py
(계획서의 `irs/data/governance/`에 대응 — 이 저장소의 기존 패키지 루트가
`engine/`이므로 `irs/`를 새로 만들지 않고 그 아래로 매핑했다. 통합 원칙 §1.7·§1.14
"IRS의 기존 architecture를 최우선으로, 외부 repo가 architecture를 바꾸게 하지 않는다".)

# METHOD:
REIMPLEMENT — 코드를 가져오지 않고 **데이터 모델과 거버넌스 규칙**만 재구현했다.
원본은 SKILL.md 한 파일에 수집 코드와 티어표가 함께 들어 있는 구조라 그대로
쓸 수 없고, 이 저장소는 이미 자체 수집 경로(`engine/filing_dates.py`)를 갖고 있다.

# WHY:
IRS는 SEC XBRL·Alpha Vantage·FMP·웹 2차출처를 섞어 쓰면서 **각 출처를 무슨
근거로 쓰는지 어디에도 기록하지 않았다.** 실제로 생긴 문제 두 가지:
  1. `engine/filing_dates.py`가 SEC에 **레이트리밋 없이** 요청한다. SEC 공식
     상한은 10 req/s이며(1차 확인, 아래 주석) 초과 시 차단된다.
  2. TYL SBC 3배 오류(2026-08-05)는 2차 웹출처를 1차 자료 대조 없이 인용해
     생겼다. 출처의 **권위 등급**이 어디에도 없어 그 위험이 보이지 않았다.

# TEST:
tests/test_source_registry.py

---

## 원본에서 가져온 것 / 바꾼 것

가져온 것: 출처를 **자유 문자열이 아니라 구조화된 레코드**로 다루고, 라이선스·
상업이용·재배포·레이트리밋을 **출처별로 명시**하며, "공식 출처라고 자동으로
자유 사용이 가능한 것은 아니다"를 원칙으로 못박는 설계.

바꾼 것(IRS-native):
  - **`UNVERIFIED`를 1급 상태로 만들었다.** 원본은 C급("조건 미확인")에 미확인을
    섞어 넣는데, 이 프로젝트는 "확인 못하면 미확인으로 정직하게 남길 것"을
    반복 원칙으로 확립했다(WCN FCF CAGR 원인불명, 상장일 미확인 등). 미확인을
    "제한적 허용"과 같은 칸에 넣으면 그 구분이 사라진다.
  - **`last_verified` staleness를 코드로 검사한다.** 약관은 바뀐다. 원본은
    검증일을 적기만 하고 낡았는지는 판단하지 않는다.
  - **재배포를 원자료/파생분석으로 분리했다.** IRS는 `ledger/*.json`에 벤더에서
    받은 **원자료 수치를 그대로** 저장해 공개 저장소에 올린다 — 파생 분석
    공개와는 성격이 다른 행위이고, 이 구분 없이는 그 사실이 드러나지 않는다.
  - **`provenance.SOURCE_KINDS`와 연결했다.** provider 단위 거버넌스(이 모듈)와
    값 단위 출처(`engine/provenance.py`)가 같은 어휘를 쓰게 해서 두 계층이
    어긋나지 않도록 테스트로 고정한다.

## 이 모듈이 하지 않는 것

- **데이터를 가져오지 않는다.** 레지스트리는 "써도 되는가"와 "얼마나 빨리
  요청해도 되는가"에만 답한다. 수집은 provider 계층(P0-02~04)의 몫이다.
- **자동으로 차단하지 않는다.** `check_use()`는 판정을 **반환**할 뿐이다.
  차단이 필요한 호출부만 `require_use()`를 명시적으로 쓴다 — 기존 스크립트를
  조용히 깨뜨리지 않기 위해서다("병기, 자동판정 안 함"과 같은 계열).
  단 **레이트리밋만은 예외**다(아래 참고).
- **약관을 해석해주지 않는다.** 여기 적힌 것은 확인한 문구와 그 출처뿐이며,
  법률 자문이 아니다.
"""

import threading
import time
from dataclasses import asdict, dataclass, field
from datetime import date
from urllib.parse import urlparse

from engine.provenance import SOURCE_KINDS

# ── 상태 어휘 ────────────────────────────────────────────────────────────
# 이 프로젝트의 다른 "모름" 어휘(PIT_UNKNOWN·PROVENANCE_UNKNOWN)와 같은 계열이다.
UNVERIFIED = "UNVERIFIED"


class ComplianceTier:
    """
    출처의 사용 자유도. **신뢰도 등급이 아니다** — 데이터가 정확한지와
    법적으로 써도 되는지는 별개 질문이라 섞지 않는다(정확도는 `reliability`).
    """

    FREE_COMMERCIAL = "FREE_COMMERCIAL"    # 상업이용·재배포 모두 명시적으로 허용
    ATTRIBUTION = "ATTRIBUTION"            # 허용되나 출처 표기 등 조건 있음
    NON_COMMERCIAL = "NON_COMMERCIAL"      # 비상업 용도로 한정된다고 약관이 명시
    AUTHORIZATION_REQUIRED = "AUTHORIZATION_REQUIRED"  # 사전 서면 승인 필요
    UNVERIFIED = UNVERIFIED                # 약관을 확인하지 못했다 ← 추측 금지

    ALL = (FREE_COMMERCIAL, ATTRIBUTION, NON_COMMERCIAL,
           AUTHORIZATION_REQUIRED, UNVERIFIED)


class Authority:
    """출처의 권위. TYL SBC 3배 오류가 보여준 대로 2차 출처는 1차와 다르게 다뤄야 한다."""

    PRIMARY_FILING = "PRIMARY_FILING"      # 발행사가 규제기관에 직접 제출
    REGULATOR = "REGULATOR"                # 규제기관·정부가 직접 발행
    VENDOR = "VENDOR"                      # 2차 가공 벤더(재작성·매핑 오류 가능)
    AGGREGATOR_WEB = "AGGREGATOR_WEB"      # 웹 집계 사이트(가장 약함)
    ANALYST = "ANALYST"                    # 분석자 주관 입력

    ALL = (PRIMARY_FILING, REGULATOR, VENDOR, AGGREGATOR_WEB, ANALYST)


# 사용 목적. 같은 출처라도 목적에 따라 허용 여부가 갈린다.
USE_PURPOSES = (
    "internal_research",     # 내부 분석에만 사용
    "derived_publication",   # 파생 결론(Gap·판정)을 공개
    "raw_redistribution",    # 원자료 수치를 그대로 공개 저장소에 저장·배포
    "commercial",            # 상업적 이용
)

# `last_verified`가 이보다 오래되면 재확인 대상. 약관은 예고 없이 바뀐다.
VERIFICATION_STALE_DAYS = 365


@dataclass
class DataSource:
    """
    §4.4가 요구한 최소 metadata를 전부 담는다.

    ⚠️ 모르는 값을 빈칸으로 두거나 그럴듯하게 채우지 말 것 — `UNVERIFIED`를 쓴다.
    빈칸은 "제약이 없다"로 오독되지만 `UNVERIFIED`는 오독되지 않는다.
    """

    provider: str
    authority: str
    data_type: str
    license: str
    commercial_use: str            # "ALLOWED" / "PROHIBITED" / UNVERIFIED
    redistribution_raw: str        # 원자료 재배포
    redistribution_derived: str    # 파생 분석 공개
    rate_limit_per_sec: float      # None이면 미상(그래도 기본 제한이 걸린다)
    freshness: str                 # 갱신 주기
    reliability: str               # 정확도에 대해 **관측된** 사실만
    last_verified: str             # YYYY-MM-DD, 또는 UNVERIFIED
    allowed_use: tuple             # USE_PURPOSES 부분집합
    source_kind: str               # provenance.SOURCE_KINDS와 연결
    hosts: tuple = ()              # 레이트리밋 매칭용 도메인
    terms_url: str = ""
    verification_note: str = ""    # 무엇을 어디서 확인했는가 (또는 왜 못 했는가)
    tier: str = field(default=UNVERIFIED)

    def __post_init__(self):
        if self.authority not in Authority.ALL:
            raise ValueError(f"알 수 없는 권위 등급: {self.authority}")
        if self.tier not in ComplianceTier.ALL:
            raise ValueError(f"알 수 없는 컴플라이언스 티어: {self.tier}")
        if self.source_kind not in SOURCE_KINDS:
            raise ValueError(
                f"source_kind '{self.source_kind}'가 provenance.SOURCE_KINDS에 없다. "
                f"provider 거버넌스와 값 단위 출처가 어긋나면 두 계층을 대조할 수 없다."
            )
        for p in self.allowed_use:
            if p not in USE_PURPOSES:
                raise ValueError(f"알 수 없는 사용목적: {p} (허용: {USE_PURPOSES})")
        if self.tier == ComplianceTier.UNVERIFIED and self.last_verified != UNVERIFIED:
            # 미확인인데 확인일이 있으면 둘 중 하나가 거짓말이다.
            raise ValueError(
                f"{self.provider}: tier가 UNVERIFIED인데 last_verified가 "
                f"'{self.last_verified}'로 채워져 있다 — 확인했다면 티어를 정하고, "
                f"못 했다면 last_verified도 UNVERIFIED로 둘 것."
            )

    def verification_age_days(self, today: str = None) -> int:
        """확인일로부터 며칠 지났는가. 미확인이면 None."""
        if self.last_verified == UNVERIFIED:
            return None
        t = date.fromisoformat(today) if today else date.today()
        return (t - date.fromisoformat(self.last_verified)).days

    def is_stale(self, today: str = None) -> bool:
        age = self.verification_age_days(today)
        return age is None or age > VERIFICATION_STALE_DAYS


# ── 등록부 ───────────────────────────────────────────────────────────────
# ⚠️ **IRS가 실제로 쓰는 출처만** 등록한다. 쓰지도 않는 출처를 미리 채우면
# 등록부가 "무엇을 쓰고 있는가"를 말해주지 못하게 된다(Simplicity First).

SOURCE_REGISTRY = {
    "sec_edgar": DataSource(
        provider="SEC EDGAR / XBRL companyfacts",
        authority=Authority.PRIMARY_FILING,
        data_type="공시 원문·XBRL 재무수치·제출일",
        license="미국 정부 저작물(17 U.S.C. §105) — 저작권 대상 아님",
        commercial_use="ALLOWED",
        redistribution_raw="ALLOWED",
        redistribution_derived="ALLOWED",
        # 1차 확인: sec.gov/os/webmaster-faq — "our current maximum access rate
        # is 10 requests per second". 상한을 그대로 쓰지 않고 8로 낮춰 잡는다
        # (동시 실행·재시도가 겹치면 상한을 넘길 수 있다).
        rate_limit_per_sec=8.0,
        freshness="제출 즉시(실시간)",
        reliability=(
            "발행사 제출 원자료. ONON(2026-08-14)에서 2차 출처끼리 어긋났을 때 "
            "이 경로로 확정했다. 단 재작성(restatement)은 반영되므로 '그 시점 값'과 "
            "다를 수 있다(engine/filing_dates.py 경고 참조)."
        ),
        last_verified="2026-08-19",
        allowed_use=("internal_research", "derived_publication",
                     "raw_redistribution", "commercial"),
        source_kind="sec_xbrl",
        hosts=("sec.gov", "www.sec.gov", "data.sec.gov"),
        terms_url="https://www.sec.gov/os/webmaster-faq",
        verification_note=(
            "2026-08-19 SEC 공식 FAQ 직접 확인: 최대 10 req/s, User-Agent 선언 요구"
            "(\"Sample Company Name AdminContact@<domain>.com\" 형식), "
            "\"All Government-created content on sec.gov and EDGAR public filing "
            "content are free to access and reuse\", 스크립트 접근 명시적 허용."
        ),
        tier=ComplianceTier.FREE_COMMERCIAL,
    ),
    "alpha_vantage": DataSource(
        provider="Alpha Vantage (MCP)",
        authority=Authority.VENDOR,
        data_type="손익계산서·현금흐름표·대차대조표·시세",
        license=UNVERIFIED,
        commercial_use=UNVERIFIED,
        redistribution_raw=UNVERIFIED,
        redistribution_derived=UNVERIFIED,
        rate_limit_per_sec=None,
        freshness="일 단위(분기 실적 반영 지연 관측됨)",
        reliability=(
            "⚠️ 관측된 오류 있음: ONON(2026-08-14) FY2025 매출이 회사 1차 공시 대비 "
            "4.7% 차이(CHF 2,878.5M vs 3,014.0M)로 **부정확**했고, 같은 심볼에서 "
            "CASH_FLOW 엔드포인트가 실패했다. 1차 자료 대조 없이 단독 신뢰 금지."
        ),
        last_verified=UNVERIFIED,
        allowed_use=("internal_research",),
        source_kind="vendor_api",
        hosts=("alphavantage.co", "www.alphavantage.co"),
        terms_url="https://www.alphavantage.co/terms_of_service/",
        verification_note=(
            "2026-08-19 약관 확인 **실패** — 공개 약관이 PDF이며 본문이 판독되지 "
            "않아 재배포·상업이용 조항을 확인하지 못했다. **추측해 채우지 않는다.** "
            "별개로 이 저장소는 2026-08-14 세션에서 일일 25회 쿼터 도달을 실측했다"
            "(약관 문구가 아니라 관측치다)."
        ),
        tier=ComplianceTier.UNVERIFIED,
    ),
    "fmp": DataSource(
        provider="Financial Modeling Prep (MCP)",
        authority=Authority.VENDOR,
        data_type="시세·시가총액·기업개요·스크리너",
        license=UNVERIFIED,
        commercial_use=UNVERIFIED,
        redistribution_raw=UNVERIFIED,
        redistribution_derived=UNVERIFIED,
        rate_limit_per_sec=None,
        freshness="일 단위",
        reliability=(
            "⚠️ 2026-08-13 세션에서 동일 엔드포인트가 심볼에 따라 비일관적으로 "
            "플랜 제한에 걸렸다(AAPL/META/MSFT는 성공, MCO/BSX/PODD는 실패) — "
            "원인 미특정. 가용성 자체를 신뢰하지 말 것."
        ),
        last_verified=UNVERIFIED,
        allowed_use=("internal_research",),
        source_kind="vendor_api",
        hosts=("financialmodelingprep.com",),
        verification_note="2026-08-19 약관 미확인. 플랜별 제한이 관측되나 문서화 안 함.",
        tier=ComplianceTier.UNVERIFIED,
    ),
    "stockanalysis": DataSource(
        provider="stockanalysis.com",
        authority=Authority.AGGREGATOR_WEB,
        data_type="ETF P/E·보수율·보유종목 top10·지수 구성",
        license=UNVERIFIED,
        commercial_use=UNVERIFIED,
        redistribution_raw=UNVERIFIED,
        redistribution_derived=UNVERIFIED,
        rate_limit_per_sec=None,
        freshness="일 단위",
        reliability=(
            "ETF 엔진(v3.33~)의 주 출처. IWM에서 같은 지표가 다른 출처와 29.5% "
            "괴리(트레일링 vs forward)를 보인 사례가 있어 **단일 출처 신뢰 금지** "
            "원칙이 여기서 나왔다. 값 자체가 틀렸다는 뜻은 아니고 집계방식이 다르다."
        ),
        last_verified=UNVERIFIED,
        allowed_use=("internal_research",),
        source_kind="web_research",
        hosts=("stockanalysis.com",),
        verification_note="2026-08-19 약관 미확인. 웹 집계 출처이므로 1차 대조 필요.",
        tier=ComplianceTier.UNVERIFIED,
    ),
    "web_research": DataSource(
        provider="일반 웹 검색(WebSearch/WebFetch)",
        authority=Authority.AGGREGATOR_WEB,
        data_type="정성 조사·뉴스·경쟁구도·가이던스",
        license=UNVERIFIED,
        commercial_use=UNVERIFIED,
        redistribution_raw="PROHIBITED",   # 원문 그대로 재배포는 하지 않는다
        redistribution_derived=UNVERIFIED,
        rate_limit_per_sec=None,
        freshness="가변",
        reliability=(
            "⚠️ 이 저장소에서 가장 큰 단일 오류가 여기서 났다 — TYL SBC/FCF를 "
            "62%로 인용했으나 SEC 원자료 대조 결과 24.4%로 **약 1/3**이었다"
            "(2026-08-05). 리서치 에이전트가 2차 출처의 잘못된 FCF를 인용한 결과. "
            "판정에 영향을 줄 수 있는 수치는 반드시 1차 자료로 재확인할 것."
        ),
        last_verified=UNVERIFIED,
        allowed_use=("internal_research",),
        source_kind="web_research",
        verification_note="출처가 매번 달라 일괄 검증이 불가능하다 — 개별 확인이 원칙.",
        tier=ComplianceTier.UNVERIFIED,
    ),
    "analyst_input": DataSource(
        provider="분석자 주관 입력",
        authority=Authority.ANALYST,
        data_type="경쟁강도·수요민감도·모델선택·Lynch 유형",
        license="해당 없음(자체 생성)",
        commercial_use="ALLOWED",
        redistribution_raw="ALLOWED",
        redistribution_derived="ALLOWED",
        rate_limit_per_sec=None,
        freshness="분석 시점",
        reliability=(
            "근거는 `subjective_input_basis`로 필수화돼 있으나 **보정된 적이 없다**. "
            "R-001 감사에서 이 입력들이 판정을 실제로 뒤집는 것이 확인됐다."
        ),
        last_verified="2026-08-19",
        allowed_use=("internal_research", "derived_publication",
                     "raw_redistribution", "commercial"),
        source_kind="analyst_input",
        verification_note="자체 생성 데이터라 외부 약관이 없다.",
        tier=ComplianceTier.FREE_COMMERCIAL,
    ),
}


# ── 조회 / 판정 ──────────────────────────────────────────────────────────
def get_source(key: str) -> DataSource:
    if key not in SOURCE_REGISTRY:
        raise KeyError(
            f"등록되지 않은 출처: {key}. **등록 없이 쓰지 말 것** — 등록부에 없는 "
            f"출처를 쓰면 그 사용이 어디에도 기록되지 않는다. "
            f"등록된 출처: {sorted(SOURCE_REGISTRY)}"
        )
    return SOURCE_REGISTRY[key]


def check_use(key: str, purpose: str, today: str = None) -> dict:
    """
    "이 출처를 이 목적으로 써도 되는가"에 대한 **판정을 반환**한다(차단하지 않는다).

    반환 `decision`:
      ALLOWED     — 약관을 확인했고 이 목적이 허용 범위 안이다
      PROHIBITED  — 약관을 확인했고 이 목적은 허용 범위 밖이다
      UNVERIFIED  — 약관을 확인하지 못했다. **허용도 금지도 아니다** —
                    "아마 괜찮겠지"로 넘어가는 것이 정확히 이 등급이 막으려는 것이다
    """
    if purpose not in USE_PURPOSES:
        raise ValueError(f"알 수 없는 사용목적: {purpose} (허용: {USE_PURPOSES})")
    src = get_source(key)
    stale = src.is_stale(today)

    if src.tier == ComplianceTier.UNVERIFIED:
        decision = UNVERIFIED
        reason = (
            f"{src.provider}의 약관을 확인하지 못했다 — {src.verification_note} "
            f"확인 전에는 '{purpose}' 허용 여부를 말할 수 없다."
        )
    elif purpose in src.allowed_use:
        decision = "ALLOWED"
        reason = f"{src.provider}: {src.license}"
        if stale:
            decision = UNVERIFIED
            reason = (
                f"{src.provider}: 허용 범위에는 들지만 마지막 확인이 "
                f"{src.verification_age_days(today)}일 전이라 "
                f"{VERIFICATION_STALE_DAYS}일 기준을 넘었다 — 약관은 바뀐다. 재확인 필요."
            )
    else:
        decision = "PROHIBITED"
        reason = (
            f"{src.provider}의 허용 목적은 {src.allowed_use}이며 '{purpose}'는 "
            f"포함되지 않는다."
        )

    return {
        "source": key, "provider": src.provider, "purpose": purpose,
        "decision": decision, "reason": reason,
        "tier": src.tier, "authority": src.authority,
        "last_verified": src.last_verified, "stale": stale,
        "reliability": src.reliability,
    }


def require_use(key: str, purpose: str, today: str = None) -> dict:
    """
    `check_use()`가 ALLOWED가 아니면 **예외를 던진다**.

    ⚠️ 기본 경로에 자동으로 끼워넣지 않는다. 차단이 실제로 옳은 호출부
    (예: 원자료를 외부로 내보내는 코드)에서만 명시적으로 쓴다 — 조용히 전역
    차단을 걸면 기존 스크립트가 이유 없이 깨진다.
    """
    r = check_use(key, purpose, today)
    if r["decision"] != "ALLOWED":
        raise PermissionError(f"[{r['decision']}] {r['reason']}")
    return r


def registry_audit(today: str = None) -> dict:
    """
    등록부 전체 상태. **미확인을 숨기지 않는 것이 이 함수의 목적이다** —
    "몇 개가 확인됐나"가 아니라 "무엇이 아직 미확인인가"를 보여준다.
    """
    rows = []
    for k, s in sorted(SOURCE_REGISTRY.items()):
        rows.append({
            "key": k, "provider": s.provider, "tier": s.tier,
            "authority": s.authority, "last_verified": s.last_verified,
            "stale": s.is_stale(today), "allowed_use": list(s.allowed_use),
            "has_rate_limit": s.rate_limit_per_sec is not None,
        })
    unverified = [r["key"] for r in rows if r["tier"] == ComplianceTier.UNVERIFIED]
    return {
        "n_sources": len(rows),
        "n_unverified": len(unverified),
        "unverified": unverified,
        "n_stale": sum(1 for r in rows if r["stale"]),
        "sources": rows,
        "note": (
            "UNVERIFIED는 '문제 없음'이 아니라 '확인하지 않음'이다. "
            "ledger/*.json은 벤더에서 받은 원자료 수치를 그대로 담아 공개 "
            "저장소에 저장하므로, 벤더 출처의 raw_redistribution 조항이 "
            "확인되기 전까지 그 행위의 적법성은 미확정 상태다."
        ),
    }


def registry_as_dict() -> dict:
    """ledger/리포트에 통째로 남길 수 있는 직렬화 형태."""
    return {k: asdict(v) for k, v in SOURCE_REGISTRY.items()}


# ── 레이트리밋 ───────────────────────────────────────────────────────────
class RateLimiter:
    """
    도메인별 최소 요청 간격을 강제한다(thread-safe).

    ⚠️ **이것만은 자동 적용한다.** 다른 판정은 전부 "병기, 자동판정 안 함"인데
    여기만 예외인 이유: 레이트리밋 초과는 해석의 여지가 있는 판단이 아니라
    상대 서버가 차단하는 **기술적 사실**이고, 차단되면 데이터를 못 가져와
    분석 자체가 중단된다. 게다가 SEC는 상한을 문서로 명시하고 있다.
    """

    def __init__(self, per_sec: float):
        if per_sec is None or per_sec <= 0:
            raise ValueError(f"레이트리밋은 양수여야 한다: {per_sec}")
        self._interval = 1.0 / per_sec
        self._lock = threading.Lock()
        # ⚠️ 0.0이 아니라 None으로 시작한다. 0.0으로 두면 **첫 요청도 대기**한다 —
        # time.monotonic()은 큰 값이라 우연히 안 걸리지만 0에서 시작하는 시계
        # (테스트·일부 플랫폼)에서는 걸린다. 테스트가 실제로 이걸 잡았다.
        self._last = None

    def wait(self, _sleep=time.sleep, _now=time.monotonic):
        """다음 요청까지 필요한 만큼 대기하고, 실제 대기한 초를 돌려준다."""
        with self._lock:
            now = _now()
            gap = 0.0 if self._last is None else self._interval - (now - self._last)
            if gap > 0:
                _sleep(gap)
                now = _now()
            self._last = now
            return max(gap, 0.0)


# 등록부에 명시된 상한이 없는 출처의 기본값. 상한을 모른다고 무제한으로
# 때리지 않는다 — 모를 때는 보수적으로 간다.
DEFAULT_RATE_LIMIT_PER_SEC = 2.0

_LIMITERS = {}
_LIMITERS_LOCK = threading.Lock()


def rate_limiter_for(url: str) -> RateLimiter:
    """URL의 호스트에 해당하는 리미터. 등록부에 없으면 보수적 기본값."""
    host = (urlparse(url).hostname or "").lower()
    per_sec = DEFAULT_RATE_LIMIT_PER_SEC
    for src in SOURCE_REGISTRY.values():
        if src.rate_limit_per_sec is None:
            continue
        if any(host == h or host.endswith("." + h) for h in src.hosts):
            per_sec = src.rate_limit_per_sec
            break
    with _LIMITERS_LOCK:
        if per_sec not in _LIMITERS:
            _LIMITERS[per_sec] = RateLimiter(per_sec)
        return _LIMITERS[per_sec]
