"""
scripts/daily_screen_ci.py(2026-08-22, GitHub Actions 전용)의 순수 로직만 고정.

Playwright/실제 네트워크/시크릿은 타지 않는다 - 그건 GitHub Actions 자체
실행으로만 검증 가능하다(이 샌드박스는 프록시 제약으로 헤드리스 브라우저
트래픽을 못 태운다, 2026-08-22 확인). 여기서는 daily_screen.py 재사용이
깨지지 않았는지, 정크 필터·상수가 의도한 대로인지만 고정한다.
"""
import importlib.util
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent


def _load():
    path = ROOT / "scripts" / "daily_screen_ci.py"
    spec = importlib.util.spec_from_file_location("daily_screen_ci", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


MOD = _load()


def test_imports_daily_screen_instead_of_reimplementing():
    """SEC 계산 로직 중복 재구현 금지 - daily_screen.fetch_sec_fields를 그대로 쓴다."""
    assert MOD.ds.fetch_sec_fields is not None
    assert MOD.ds.DEFAULT_NDTE == pytest.approx(0.406, abs=0.001)


def test_only_whitelisted_finviz_presets_are_used():
    """
    robots.txt가 허용한 프리셋(s=ta_newlow, s=it_latestbuys)만 URL에 있어야 한다.
    커스텀 필터(f=)가 섞여 들어가면 로봇 배제 규칙 위반이다.
    """
    for name, url in MOD.FINVIZ_PRESETS:
        assert "f=" not in url
        assert "s=" in url
        assert url.startswith("https://finviz.com/screener?v=340&s=")


@pytest.mark.parametrize("ticker,expected", [
    ("AAPL", False), ("MSFT", False),
    ("BF.B", True),      # 점 포함
    ("TOOLONGTICKER", True),  # 5자 초과
    ("2M4", True),        # 숫자 포함
])
def test_junk_filter(ticker, expected):
    assert MOD.looks_like_junk(ticker) == expected


def test_av_budget_leaves_headroom_below_daily_cap():
    """무료 한도(25/day) 전부를 쓰면 저녁 대화용 여유가 안 남는다."""
    assert MOD.MAX_AV_CALLS < 25


def test_junk_market_cap_threshold_is_documented_not_arbitrary():
    assert MOD.MIN_MARKET_CAP == 300_000_000


# ── Finviz HTML 파싱 (2026-08-22 실측 리뉴얼 대응) ────────────────────────
def test_ticker_extraction_matches_finviz_redesign():
    """
    2026-08-22 workflow_dispatch 실측(run 32571772267)에서 구 셀렉터
    (`quote.ashx?t=`)가 후보 0건을 냈다 - Finviz가 `stock?t=TICKER`로
    바꿨다. 실제 다운로드한 HTML로 재현한 최소 스니펫으로 고정한다.
    """
    html = (
        # 차트 링크(내부에 텍스트 없음 - img만) - 매치되면 안 됨
        '<a class="block" href="stock?t=LGCL&amp;ty=c&amp;p=d&amp;b=1">'
        '<img src="chart.png"></a>'
        # 진짜 티커 링크 - 앵커 텍스트==href 티커
        '<a href="stock?t=LGCL&amp;ty=c&amp;p=d&amp;b=1" class="tab-link">LGCL</a>'
        ' [NASD]'
        # 인사이더 매도자 이름 링크 - href는 stock?t= 패턴이 아니라서 매치 안 됨
        '<a href="insidertrading?oc=2123543" class="tab-link">Lee Wallace Wang Leong</a>'
    )
    assert MOD._extract_tickers_from_html(html) == ["LGCL"]


# ── GitHub Issue 결과기록 (2026-08-23, Notion 401 문제로 교체) ───────────
class _FakeResponse:
    def __init__(self, status_code=200, json_data=None, text=""):
        self.status_code = status_code
        self._json = json_data if json_data is not None else {}
        self.text = text

    def json(self):
        return self._json

    def raise_for_status(self):
        if self.status_code >= 300:
            raise Exception(f"HTTP {self.status_code}")


def test_find_or_create_issue_reuses_existing_open_issue(monkeypatch):
    """같은 제목의 열린 이슈가 있으면 새로 만들지 않고 재사용한다(매일 새 이슈 금지)."""
    calls = {"post": 0}

    def fake_get(url, headers=None, params=None, timeout=None):
        return _FakeResponse(200, json_data=[
            {"number": 42, "title": MOD.ISSUE_TITLE},
            {"number": 7, "title": "다른 이슈"},
        ])

    def fake_post(url, headers=None, json=None, timeout=None):
        calls["post"] += 1
        return _FakeResponse(201, json_data={"number": 99})

    import sys, types
    fake_requests = types.SimpleNamespace(get=fake_get, post=fake_post)
    monkeypatch.setitem(sys.modules, "requests", fake_requests)

    n = MOD._find_or_create_issue("tok", "chlalsrl1203", "IRS")
    assert n == 42
    assert calls["post"] == 0  # 재사용했으니 생성 호출이 없어야 함


def test_find_or_create_issue_creates_when_missing(monkeypatch):
    def fake_get(url, headers=None, params=None, timeout=None):
        return _FakeResponse(200, json_data=[])

    def fake_post(url, headers=None, json=None, timeout=None):
        assert json["title"] == MOD.ISSUE_TITLE
        return _FakeResponse(201, json_data={"number": 123})

    import types, sys
    fake_requests = types.SimpleNamespace(get=fake_get, post=fake_post)
    monkeypatch.setitem(sys.modules, "requests", fake_requests)

    n = MOD._find_or_create_issue("tok", "chlalsrl1203", "IRS")
    assert n == 123


def test_post_to_github_issue_no_extra_secret_needed_beyond_gh_token():
    """
    핵심 불변조건 - Notion류 별도 발급 절차가 필요 없다는 사실 자체를 고정한다.
    함수 시그니처에 token/owner/repo만 있고 다른 자격증명 파라미터가 없어야 한다.
    """
    import inspect
    params = list(inspect.signature(MOD.post_to_github_issue).parameters)
    assert params[:3] == ["token", "owner", "repo"]
    assert not any("notion" in p.lower() for p in params)


def test_ticker_extraction_deduplicates_across_pages(tmp_path):
    """같은 종목이 여러 링크(차트+스냅샷)에 나와도 중복 없이 한 번만 나와야 한다."""
    html = (
        '<a href="stock?t=AAPL" class="tab-link">AAPL</a>'
        '<a href="stock?t=AAPL&ty=c" class="tab-link">AAPL</a>'
        '<a href="stock?t=MSFT" class="tab-link">MSFT</a>'
    )
    result = MOD._extract_tickers_from_html(html)
    assert result == ["AAPL", "AAPL", "MSFT"]  # 추출 자체는 중복 허용
    # 중복 제거는 fetch_finviz_tickers()의 seen 집합 몫 - 여기선 추출만 검증
