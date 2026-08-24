"""
scripts/daily_screen_ci.py(2026-08-22, GitHub Actions 전용)의 순수 로직만 고정.

Playwright/실제 네트워크/시크릿은 타지 않는다 - 그건 GitHub Actions 자체
실행으로만 검증 가능하다(이 샌드박스는 프록시 제약으로 헤드리스 브라우저
트래픽을 못 태운다, 2026-08-22 확인). 여기서는 daily_screen.py 재사용이
깨지지 않았는지, 정크 필터·상수가 의도한 대로인지만 고정한다.
"""
import importlib.util
import os
import pathlib
import sys
import types

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


# ── 심층분석 통합 (2026-08-23, v3.65) ────────────────────────────────
def _fake_screen_result(ticker, market_cap=50_000_000_000):
    """screen_all()이 반환하는 ScreenResult 흉내(테스트 전용)."""
    from engine.screener import Candidate, ScreenResult
    c = Candidate(ticker=ticker, name=ticker, market_cap=market_cap, fcf0=1,
                  revenue_cagr_5y=0.1, fcf_cagr_5y=0.1, net_debt_to_ebitda=0.4,
                  worst_yoy_revenue=0.0)
    return ScreenResult(c, fcf_yield=0.05, implied_growth_est=0.03,
                        binding_cagr=0.1, realistic_growth_est=0.09,
                        expectation_gap_est=0.06, passed=True, tier="A")


def test_run_deep_dive_writes_snapshot_and_detects_no_prior_change(tmp_path, monkeypatch):
    monkeypatch.setattr(MOD, "DEEP_SCREEN_DIR", str(tmp_path))

    def fake_fetch(ticker, today):
        years = list(range(2015, 2026))
        return {
            "revenue_by_year": {y: 1000 * (1.1 ** i) for i, y in enumerate(years)},
            "operating_cashflow_by_year": {y: 300 * (1.1 ** i) for i, y in enumerate(years)},
            "capex_by_year": {y: 50 * (1.05 ** i) for i, y in enumerate(years)},
            "operating_income_by_year": {y: 200 * (1.1 ** i) for i, y in enumerate(years)},
        }, []

    monkeypatch.setattr(MOD.ds, "fetch_deep_series", fake_fetch)
    rows = MOD.run_deep_dive([_fake_screen_result("TEST")], "2026-08-23")
    assert len(rows) == 1
    assert rows[0]["ticker"] == "TEST"
    assert "error" not in rows[0]
    assert "change_vs_prior" not in rows[0]  # 첫 스냅샷이니 비교대상 없음
    assert os.path.exists(os.path.join(str(tmp_path), "TEST_2026-08-23.json"))


def test_run_deep_dive_detects_change_vs_prior_snapshot(tmp_path, monkeypatch):
    monkeypatch.setattr(MOD, "DEEP_SCREEN_DIR", str(tmp_path))
    years = list(range(2015, 2026))
    series = {
        "revenue_by_year": {y: 1000 * (1.1 ** i) for i, y in enumerate(years)},
        "operating_cashflow_by_year": {y: 300 * (1.1 ** i) for i, y in enumerate(years)},
        "capex_by_year": {y: 50 * (1.05 ** i) for i, y in enumerate(years)},
        "operating_income_by_year": {y: 200 * (1.1 ** i) for i, y in enumerate(years)},
    }
    monkeypatch.setattr(MOD.ds, "fetch_deep_series", lambda t, d: (series, []))

    MOD.run_deep_dive([_fake_screen_result("TEST")], "2026-08-20")
    # 이틀 뒤 재실행 - 시가총액이 달라져 Gap도 달라진다
    rows = MOD.run_deep_dive([_fake_screen_result("TEST", market_cap=40_000_000_000)],
                             "2026-08-22")
    assert "change_vs_prior" in rows[0]
    assert rows[0]["change_vs_prior"]["prior_date"] == "2026-08-20"
    assert rows[0]["change_vs_prior"]["gap_delta"] != 0


def test_run_deep_dive_failure_is_per_ticker_not_fatal(monkeypatch, tmp_path):
    """
    한 종목의 SEC 데이터가 이상해도(Model N/A 등) 나머지·기본 스크리닝
    보고는 계속 나가야 한다 - 예외가 전체를 죽이면 안 된다.
    """
    monkeypatch.setattr(MOD, "DEEP_SCREEN_DIR", str(tmp_path))
    monkeypatch.setattr(MOD.ds, "fetch_deep_series",
                        lambda t, d: (None, ["SEC 조회 실패"]))
    rows = MOD.run_deep_dive([_fake_screen_result("BADTICKER")], "2026-08-23")
    assert len(rows) == 1
    assert "error" in rows[0]


def test_format_deep_dive_section_handles_errors_and_empty():
    assert MOD.format_deep_dive_section([]) == ""
    section = MOD.format_deep_dive_section([{"ticker": "X", "error": "실패사유"}])
    assert "실패사유" in section


def test_post_to_github_issue_includes_deep_dive_section_when_present(monkeypatch):
    """deep_rows가 있으면 코멘트 본문에 심층분석 섹션이 실제로 포함돼야 한다."""
    captured = {}

    def fake_get(url, headers=None, params=None, timeout=None):
        return _FakeResponse(200, json_data=[{"number": 1, "title": MOD.ISSUE_TITLE}])

    def fake_post(url, headers=None, json=None, timeout=None):
        captured["body"] = json["body"]
        return _FakeResponse(201)

    fake_requests = types.SimpleNamespace(get=fake_get, post=fake_post)
    monkeypatch.setitem(sys.modules, "requests", fake_requests)
    monkeypatch.setattr(MOD, "build_monitor_section", lambda d: "")

    deep_rows = [{"ticker": "AAA", "judgment": "저평가 가능성", "realistic_growth": 0.1,
                  "implied_growth": 0.03, "gap": 0.07, "drs": 40.0,
                  "lynch_type": "stalwart", "data_limitations": []}]
    MOD.post_to_github_issue("tok", "o", "r", "2026-08-23", [], {}, None, deep_rows)
    assert "심층분석" in captured["body"]
    assert "AAA" in captured["body"]


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


# ── 실패 사유 보존 (v3.68) ────────────────────────────────────────────────
# 2026-08-23/24 정규 실행에서 25종목 중 24종목이 SEC 단계에서 탈락했는데
# 리포트는 "오늘은 통과 후보 없음"이라고만 적었다. 채점이 0건인 것과 후보가
# 정말 없는 것이 구분되지 않으면, 파이프라인 고장이 정상 결과로 위장된다.

def _capture_issue_body(monkeypatch, **kwargs):
    """post_to_github_issue가 실제로 올리는 본문을 가로챈다."""
    seen = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        seen["body"] = json["body"]
        return _FakeResponse(201, json_data={"id": 1})

    fake_requests = types.SimpleNamespace(
        get=lambda *a, **k: _FakeResponse(200, json_data=[
            {"number": 42, "title": MOD.ISSUE_TITLE}]),
        post=fake_post,
        RequestException=Exception,
    )
    monkeypatch.setitem(sys.modules, "requests", fake_requests)
    MOD.post_to_github_issue("tok", "o", "r", "2026-08-24", **kwargs)
    return seen["body"]


def test_zero_scored_is_not_reported_as_no_candidates_passed(monkeypatch):
    """채점 0건은 '통과 후보 없음'이 아니라 실행 실패로 보고돼야 한다."""
    body = _capture_issue_body(
        monkeypatch,
        passed_results=[],
        skipped={f"T{i}": ["companyfacts 조회 실패(CIK 000): HTTP 403"]
                 for i in range(24)},
        note=None,
        funnel={"finviz": 60, "after_junk": 25, "sec_ok": 1, "sec_skipped": 24,
                "with_cap": 0, "scored": 0, "passed": 0},
    )
    # 경고문 자체가 그 표현을 인용하므로, "결과 한 줄로 그렇게 적었는가"를 본다.
    assert "오늘은 통과 후보 없음." not in body.splitlines()
    assert "채점된 종목이 0개" in body
    assert "인프라 장애로 제외 24종목" in body


def test_scored_but_none_passed_is_reported_as_a_normal_empty_result(monkeypatch):
    """반대로 실제로 채점했는데 통과가 없으면 정상 결과로 적어야 한다."""
    body = _capture_issue_body(
        monkeypatch,
        passed_results=[],
        skipped={"UVV": ["FCF 기준연도(2020) 또는 최종연도(2025)가 0 이하"]},
        note=None,
        funnel={"finviz": 60, "after_junk": 25, "sec_ok": 24, "sec_skipped": 1,
                "with_cap": 12, "scored": 12, "passed": 0},
    )
    assert "채점된 종목이 0개" not in body
    assert "12종목을 채점했고 통과 후보는 없음" in body
    assert "인프라 장애" not in body   # 정상 제외는 장애로 표시하지 않는다


def test_classify_skips_separates_infrastructure_from_legitimate_exclusion():
    groups = {lbl: (ts, infra) for lbl, ts, infra in MOD.classify_skips({
        "A": ["companyfacts 조회 실패(CIK 1): HTTP 403"],
        "B": ["SEC 티커 매핑표에 없음(ETF·신규상장·비SEC 등록 가능)"],
        "C": ["FCF 기준연도(2020) 또는 최종연도(2025)가 0 이하 - CAGR 계산 불가"],
        "D": ["매출·OCF·capex 공통 확보 연도가 1개뿐 - CAGR 계산 불가"],
    })}
    infra = {lbl for lbl, (_, is_infra) in groups.items() if is_infra}
    assert len(infra) == 1, "조회 실패만 인프라 장애여야 한다"
    assert groups["SEC 요청 거부·네트워크"][0] == ["A"]
    # 나머지 셋은 데이터 성질상의 정상 제외 - 조치 대상이 아니다
    assert all(not is_infra for lbl, (_, is_infra) in groups.items()
               if lbl != "SEC 요청 거부·네트워크")


def test_cached_facts_returns_reason_instead_of_bare_none(monkeypatch, tmp_path):
    """실패 사유를 잃어버리면 고칠 수 없다 - None이 아니라 (None, 사유)."""
    import urllib.error
    monkeypatch.setattr(MOD.ds, "CACHE_DIR", str(tmp_path))

    import engine.filing_dates as fd
    monkeypatch.setattr(fd, "ticker_to_cik", lambda t, ua=None: "0000000001")

    def boom(cik, user_agent=None):
        raise RuntimeError("SEC companyfacts 조회 실패") from urllib.error.HTTPError(
            "u", 403, "Forbidden", None, None)

    monkeypatch.setattr(fd, "fetch_company_facts", boom)
    facts, reason = MOD.ds._cached_facts("ZZZZ")
    assert facts is None
    assert "HTTP 403" in reason, f"HTTP 상태가 사유에 남아야 한다: {reason}"


def test_cached_facts_distinguishes_unlisted_ticker_from_request_failure(
        monkeypatch, tmp_path):
    monkeypatch.setattr(MOD.ds, "CACHE_DIR", str(tmp_path))
    import engine.filing_dates as fd
    monkeypatch.setattr(fd, "ticker_to_cik", lambda t, ua=None: None)
    facts, reason = MOD.ds._cached_facts("SPY")
    assert facts is None
    assert "매핑표에 없음" in reason
    assert "HTTP" not in reason


def test_sec_ticker_map_is_fetched_once_per_process():
    """
    티커마다 1MB 매핑표를 새로 받으면 25종목 조회가 25회 다운로드가 된다 -
    그 자체가 차단 위험이라 프로세스 내 1회로 고정한다.
    """
    import engine.filing_dates as fd
    calls = {"n": 0}
    original = fd._http_json
    fd._TICKER_MAP_CACHE.clear()
    try:
        def counting(url, user_agent=None):
            calls["n"] += 1
            return {"0": {"ticker": "AAPL", "cik_str": 320193},
                    "1": {"ticker": "MSFT", "cik_str": 789019}}
        fd._http_json = counting
        for _ in range(10):
            assert fd.ticker_to_cik("AAPL") == "0000320193"
        assert fd.ticker_to_cik("MSFT") == "0000789019"
        assert fd.ticker_to_cik("NOPE") is None
        assert calls["n"] == 1, f"매핑표를 {calls['n']}번 받았다(1번이어야 함)"
    finally:
        fd._http_json = original
        fd._TICKER_MAP_CACHE.clear()


def test_http_404_is_not_counted_as_infrastructure_failure():
    """
    ETF·펀드는 CIK는 있어도 XBRL이 없어 404를 받는다(SPY 실측). 이걸 장애로
    세면 목록에 ETF가 섞일 때마다 가짜 경보가 뜨고 진짜 장애가 묻힌다.
    """
    groups = {lbl: (ts, infra) for lbl, ts, infra in MOD.classify_skips({
        "SPY": ["companyfacts 조회 실패(CIK 0000884394): HTTP 404"],
        "AAA": ["companyfacts 조회 실패(CIK 0000000001): HTTP 403"],
        "BBB": ["CIK 매핑표 조회 실패: 네트워크 오류(timed out)"],
    })}
    infra = {t for _, (ts, is_infra) in groups.items() if is_infra for t in ts}
    assert infra == {"AAA", "BBB"}, f"404가 장애로 잘못 분류됨: {infra}"
