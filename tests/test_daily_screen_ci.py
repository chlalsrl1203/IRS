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
