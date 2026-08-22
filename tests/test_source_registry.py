"""
P0-01 Source Registry 테스트.

# SOURCE:
https://github.com/simonlin1212/global-stock-data

# METHOD:
REIMPLEMENT — 데이터 모델과 거버넌스 규칙만 재구현했으므로, 테스트도 원본
테스트를 옮기지 않고 **IRS가 지키기로 한 불변조건**을 직접 고정한다.

고정하는 불변조건:
  ① 미확인을 허용으로 오독하지 않는다 (이 등록부의 존재 이유)
  ② provider 거버넌스와 값 단위 출처(provenance)가 같은 어휘를 쓴다
  ③ 확인일이 낡으면 자동으로 재확인 대상이 된다
  ④ 레이트리밋이 실제로 대기를 강제한다 (SEC 10 req/s 상한)
  ⑤ 등록되지 않은 출처는 조용히 통과하지 않는다
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.data.governance.source_registry import (  # noqa: E402
    DEFAULT_RATE_LIMIT_PER_SEC, SOURCE_REGISTRY, UNVERIFIED, Authority,
    ComplianceTier, DataSource, RateLimiter, USE_PURPOSES,
    VERIFICATION_STALE_DAYS, check_use, get_source, rate_limiter_for,
    registry_audit, require_use,
)
from engine.provenance import SOURCE_KINDS  # noqa: E402


# ── ① 미확인을 허용으로 오독하지 않는다 ──────────────────────────────────
def test_unverified_source_is_neither_allowed_nor_prohibited():
    """
    이 등록부가 존재하는 이유. Alpha Vantage 약관은 실제로 확인에 실패했고
    (PDF 판독 불가), 허용 범위 안의 목적조차 ALLOWED로 표시되면 안 된다.
    """
    r = check_use("alpha_vantage", "internal_research")   # allowed_use 안에 있다
    assert r["decision"] == UNVERIFIED
    assert r["decision"] != "ALLOWED"
    assert "확인하지 못했다" in r["reason"]


def test_uncertainty_never_softens_a_no_into_a_maybe():
    """
    ⚠️ P0-02가 잡은 실제 결함의 회귀 테스트. 초판은 UNVERIFIED를 먼저 검사해
    허용 범위 **밖**인 목적까지 '아마도'로 만들었다. 불확실성이 "아니오"를
    약화시키면 보수적 방향과 반대로 작동한다.
    """
    r = check_use("alpha_vantage", "commercial")          # allowed_use 밖
    assert r["decision"] == "PROHIBITED"
    assert "포함되지 않는다" in r["reason"]
    assert "보수적으로 승인하지 않는다" in r["reason"]   # 미확인 사실도 함께 남는다


def test_require_use_raises_on_unverified_not_just_prohibited():
    """'미확인이니 일단 진행'이 코드 경로로 존재하면 안 된다."""
    with pytest.raises(PermissionError):
        require_use("alpha_vantage", "raw_redistribution")   # PROHIBITED
    with pytest.raises(PermissionError):
        require_use("web_research", "commercial")            # PROHIBITED
    with pytest.raises(PermissionError):
        require_use("alpha_vantage", "internal_research")    # UNVERIFIED


def test_verified_free_source_is_allowed_for_all_purposes():
    """SEC는 1차 확인을 마쳤다(2026-08-19 sec.gov/os/webmaster-faq)."""
    for purpose in USE_PURPOSES:
        r = check_use("sec_edgar", purpose, today="2026-08-19")
        assert r["decision"] == "ALLOWED", (purpose, r["reason"])
    assert get_source("sec_edgar").tier == ComplianceTier.FREE_COMMERCIAL


def test_tier_and_last_verified_cannot_contradict_each_other():
    """UNVERIFIED인데 확인일이 채워져 있으면 둘 중 하나가 거짓말이다."""
    with pytest.raises(ValueError, match="UNVERIFIED"):
        DataSource(
            provider="가짜", authority=Authority.VENDOR, data_type="x",
            license=UNVERIFIED, commercial_use=UNVERIFIED,
            redistribution_raw=UNVERIFIED, redistribution_derived=UNVERIFIED,
            rate_limit_per_sec=None, freshness="x", reliability="x",
            last_verified="2026-08-19",      # ← 확인일이 있는데
            allowed_use=(), source_kind="vendor_api",
            tier=ComplianceTier.UNVERIFIED,  # ← 티어는 미확인
        )


# ── ② 두 계층이 같은 어휘를 쓴다 ─────────────────────────────────────────
def test_every_registered_source_kind_exists_in_provenance():
    """
    provider 거버넌스(이 모듈)와 값 단위 출처(engine/provenance.py)가 어긋나면
    "이 값이 어느 provider에서 왔는가"를 대조할 수 없다.
    """
    for key, src in SOURCE_REGISTRY.items():
        assert src.source_kind in SOURCE_KINDS, key


# ── ③ 확인일 staleness ───────────────────────────────────────────────────
def test_stale_verification_downgrades_allowed_to_unverified():
    """약관은 바뀐다 — 오래된 확인을 현재의 허가로 취급하지 않는다."""
    fresh = check_use("sec_edgar", "commercial", today="2026-08-19")
    assert fresh["decision"] == "ALLOWED" and fresh["stale"] is False

    later = f"{2026 + 2}-08-19"       # 확인일로부터 2년 뒤
    stale = check_use("sec_edgar", "commercial", today=later)
    assert stale["stale"] is True
    assert stale["decision"] == UNVERIFIED
    assert str(VERIFICATION_STALE_DAYS) in stale["reason"]


def test_unverified_source_reports_none_age_not_zero():
    """미확인을 '오늘 확인함'(age 0)으로 계산하면 staleness가 무의미해진다."""
    src = get_source("web_research")
    assert src.verification_age_days() is None
    assert src.is_stale() is True


# ── ④ 레이트리밋 ─────────────────────────────────────────────────────────
def test_rate_limiter_enforces_interval():
    clock = {"t": 0.0}
    slept = []

    def fake_sleep(s):
        slept.append(s)
        clock["t"] += s

    def fake_now():
        return clock["t"]

    rl = RateLimiter(8.0)                      # 0.125s 간격
    assert rl.wait(fake_sleep, fake_now) == 0.0   # 첫 요청은 즉시
    gap = rl.wait(fake_sleep, fake_now)            # 연속 요청은 대기
    assert gap == pytest.approx(0.125)
    assert slept == [pytest.approx(0.125)]


def test_sec_urls_get_the_registered_limit_and_unknown_hosts_get_conservative_default():
    sec = rate_limiter_for("https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json")
    assert sec._interval == pytest.approx(1 / 8.0)
    # 서브도메인도 같은 정책을 받아야 한다
    assert rate_limiter_for("https://www.sec.gov/files/company_tickers.json") is sec
    unknown = rate_limiter_for("https://example.invalid/data.json")
    assert unknown._interval == pytest.approx(1 / DEFAULT_RATE_LIMIT_PER_SEC)


def test_filing_dates_actually_calls_the_limiter():
    """
    등록부를 만들어놓고 호출부에 배선하지 않으면 아무 효과가 없다 — 이
    프로젝트가 문서로만 둔 규칙에서 네 번 겪은 실패를 반복하지 않는다.
    """
    import engine.filing_dates as fd

    calls, opened = [], []

    class _Resp:
        def read(self):
            return b'{"ok": 1}'

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    class _FakeLimiter:
        def wait(self):
            calls.append(1)

    orig_limiter, orig_open = fd.rate_limiter_for, fd.urllib.request.urlopen
    fd.rate_limiter_for = lambda url: _FakeLimiter()
    fd.urllib.request.urlopen = lambda req, timeout=None: opened.append(req) or _Resp()
    try:
        assert fd._http_json("https://data.sec.gov/x.json") == {"ok": 1}
    finally:
        fd.rate_limiter_for, fd.urllib.request.urlopen = orig_limiter, orig_open

    assert calls == [1], "레이트리밋이 호출되지 않았다"
    assert opened and opened[0].get_header("User-agent")


# ── ⑤ 미등록 출처 ────────────────────────────────────────────────────────
def test_unknown_source_raises_instead_of_silently_passing():
    with pytest.raises(KeyError, match="등록되지 않은 출처"):
        get_source("bloomberg_terminal")


def test_unknown_purpose_raises():
    with pytest.raises(ValueError, match="알 수 없는 사용목적"):
        check_use("sec_edgar", "world_domination")


# ── 감사 산출물 ──────────────────────────────────────────────────────────
def test_audit_surfaces_unverified_rather_than_hiding_it():
    a = registry_audit()
    assert a["n_sources"] == len(SOURCE_REGISTRY)
    assert a["n_unverified"] >= 1
    # 현재 실제 상태: 벤더·웹 출처 4건이 미확인이다. 확인되면 이 테스트가
    # 실패하며 등록부와 문서를 함께 갱신하라는 신호를 준다.
    assert set(a["unverified"]) == {
        "alpha_vantage", "fmp", "stockanalysis", "web_research", "finviz",
    }
    assert "확인하지 않음" in a["note"]


def test_raw_redistribution_of_vendor_data_is_not_claimed_as_allowed():
    """
    ledger/*.json은 벤더 원자료 수치를 그대로 담아 공개 저장소에 올린다.
    그 행위가 허용된다고 등록부가 **주장하지 않는지** 고정한다.
    """
    for key in ("alpha_vantage", "fmp", "stockanalysis"):
        assert check_use(key, "raw_redistribution")["decision"] != "ALLOWED"


# ── Finviz (2026-08-22, 자동 스크리닝 루틴 추가) ──────────────────────────
def test_finviz_only_scoped_to_internal_research():
    """
    자동화가 Finviz 결과를 노션에 적재하는 건 raw_redistribution이 아니라
    internal_research 범위 안이어야 한다(원자료를 그대로 재배포하는 게 아니라
    내부 판단에만 쓰는 것).
    """
    assert get_source("finviz").allowed_use == ("internal_research",)


def test_finviz_reliability_documents_the_custom_filter_prohibition():
    """
    robots.txt가 `Disallow: /screener?*`로 커스텀 필터(f=)를 막고 프리셋(s=)만
    Allow한다는 사실이 사라지면, 나중에 누군가 v=121+f= 조합을 자동화에 그대로
    쓸 위험이 있다(2026-08-22 발견 - 최초 조사 때는 커스텀 필터로 조사했었다).
    """
    src = get_source("finviz")
    assert "Disallow: /screener?*" in src.reliability
    assert "화이트리스트" in src.reliability
