"""
daily_screen_ci.py (2026-08-22) — GitHub Actions에서 도는 완전 자율 버전.

왜 별도 파일인가: `scripts/daily_screen.py`는 클로드 세션 안에서(WebFetch/
Alpha Vantage MCP/Notion MCP 도구를 써서) 대화형으로 돌리는 걸 전제한다.
이 파일은 **클로드 세션이 전혀 없는 GitHub Actions 러너**에서 돌아가야 해서
그 세 가지를 전부 직접 구현한다:
  - Finviz  -> Playwright(헤드리스 브라우저, JS 렌더링 필요 - 순수 HTTP로는
              테이블이 안 나온다는 걸 2026-08-22 curl 테스트로 확인함)
  - 시가총액 -> Alpha Vantage REST API 직접 호출(MCP 아님, 사용자 개인 무료
              키 - 저녁 대화에서 쓰는 MCP 쿼터와 완전히 분리된다)
  - 결과기록 -> GitHub Issue(REST API, 워크플로가 자동으로 받는 GITHUB_TOKEN
              사용 - 별도 발급·시크릿 등록이 전혀 필요 없다)

SEC 재무 계산·screener.py 판정 로직은 **재구현하지 않는다** - daily_screen.py를
그대로 import해서 쓴다(중복 계산이 두 계산을 미묘하게 어긋나게 만든다는
Simplicity First 원칙).

⚠️ Finviz 접근은 반드시 화이트리스트 프리셋만 쓴다(robots.txt, source_registry.py
의 finviz 항목 참고). 커스텀 필터(f=)는 여기서도 금지.

2026-08-23: Notion을 결과기록 경로로 썼다가 사용자가 발급한 통합 토큰이
계속 401(API token is invalid)로 거부돼 GitHub Issue로 교체했다 - 별도
발급·시크릿 등록 없이 워크플로가 자동으로 받는 `GITHUB_TOKEN`만으로 되고,
사용자가 이미 쓰는 GitHub 앱에서 이슈 알림(Watch)까지 공짜로 딸려온다.

시크릿 없이도 죽지 않는다 - ALPHA_VANTAGE_API_KEY가 없으면 그 단계만
건너뛰고 로그에 명시한다(Finviz+SEC 부분만 검증하는 드라이런이 가능해야
하므로). GITHUB_TOKEN은 워크플로가 항상 자동으로 제공하므로 미설정 분기가
없다.
"""
import json
import os
import re
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))  # repo root -> engine.*
sys.path.insert(0, _HERE)                   # scripts/ 자체 -> daily_screen 모듈

import daily_screen as ds  # noqa: E402  (scripts/daily_screen.py 재사용)
from engine.screener import screen_all  # noqa: E402

FINVIZ_PRESETS = [
    ("ta_newlow", "https://finviz.com/screener?v=340&s=ta_newlow"),
    ("it_latestbuys", "https://finviz.com/screener?v=340&s=it_latestbuys"),
]
MAX_PAGES_PER_PRESET = 3            # 10종목/페이지 * 3 = 최대 30종목/프리셋
MAX_CANDIDATES_TOTAL = 25           # SEC 조회 대상 상한(정크 필터 후)
MAX_AV_CALLS = 20                   # 하루 25회 중 5회는 여유로 남긴다
MIN_MARKET_CAP = 300_000_000        # 3억달러 미만은 정크로 간주
AV_CALL_INTERVAL_SEC = 13           # 분당 5회 제한(60/5=12초) + 여유


def log(msg):
    print(msg, flush=True)


# ── 1) Finviz (Playwright, 화이트리스트 프리셋만) ────────────────────────
# ⚠️ 2026-08-22 workflow_dispatch 실측(run 32571772267)으로 확인: Finviz가
# 사이트를 리뉴얼하면서 티커 링크가 `quote.ashx?t=TICKER`에서 `stock?t=TICKER`
# 로 바뀌었다(구 셀렉터로 첫 실행 시 후보 0개, HTML을 직접 대조해 확정).
# DOM 순회 대신 렌더된 HTML을 정규식으로 훑는다 - 같은 티커가 차트링크
# (내부 텍스트 없음)·인사이더 매도 링크(다른 사람 이름)에도 나타나서, 앵커
# 텍스트가 href의 티커와 **정확히 일치**하는 것만 채택해야 오탐이 없다.
_TICKER_LINK_RE = re.compile(
    r'<a[^>]*href="stock\?t=([A-Za-z.]+)[^"]*"[^>]*>([^<]*)</a>')


def _extract_tickers_from_html(html):
    out = []
    for href_t, text in _TICKER_LINK_RE.findall(html):
        text = text.strip()
        if text and text.isupper() and text == href_t:
            out.append(text)
    return out


def fetch_finviz_tickers():
    from playwright.sync_api import sync_playwright

    tickers = []
    seen = set()
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120 Safari/537.36"
        ))
        for name, base_url in FINVIZ_PRESETS:
            for i in range(MAX_PAGES_PER_PRESET):
                url = base_url if i == 0 else f"{base_url}&r={i * 10 + 1}"
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    page.wait_for_timeout(1500)
                except Exception as e:  # noqa: BLE001
                    log(f"[Finviz] {name} 페이지{i+1} 로드 실패: {e}")
                    break
                html = page.content()
                page_tickers = _extract_tickers_from_html(html)
                if not page_tickers:
                    log(f"[Finviz][진단] {name} 페이지{i+1}: title={page.title()!r} "
                        f"html길이={len(html)} url={page.url} - 후보 0건")
                    dump_path = f"/tmp/finviz_debug_{name}_{i}.html"
                    with open(dump_path, "w", encoding="utf-8") as f:
                        f.write(html)
                    break
                for t in page_tickers:
                    if t not in seen:
                        seen.add(t)
                        tickers.append(t)
        browser.close()
    log(f"[Finviz] 화이트리스트 프리셋 2건에서 중복제거 후 {len(tickers)}종목 확보")
    return tickers


# ── 2) 정크 필터(1차, 정성) ────────────────────────────────────────────
def looks_like_junk(ticker):
    """숫자/특수문자 섞인 티커, 지나치게 짧은 워런트류를 걸러낸다(대략적)."""
    return not ticker.isalpha() or len(ticker) > 5


# ── 3) Alpha Vantage 시가총액(직접 REST, MCP 아님) ────────────────────
def fetch_market_cap_av(ticker, api_key):
    import requests

    r = requests.get("https://www.alphavantage.co/query", params={
        "function": "OVERVIEW", "symbol": ticker, "apikey": api_key,
    }, timeout=15)
    data = r.json()
    cap = data.get("MarketCapitalization")
    if not cap or cap in ("None", "0"):
        return None
    try:
        return float(cap)
    except ValueError:
        return None


# ── 4) GitHub Issue (직접 REST, 워크플로 자동 제공 GITHUB_TOKEN) ─────────
# 노션 대신 쓰는 이유(2026-08-23): 노션은 사용자가 직접 통합을 발급하고
# GitHub 시크릿에 등록하고 페이지에 연결해야 하는 3단계가 필요했고, 실제로
# 토큰이 계속 401로 거부돼 완전자동화의 병목이 됐다. GitHub Actions는
# `secrets.GITHUB_TOKEN`을 실행마다 자동으로 만들어 넘겨주므로 이 경로는
# 발급·등록 절차 자체가 없다 - 실패 지점 하나가 통째로 사라진다.
ISSUE_TITLE = "📊 IRS 일일 스크리닝 결과"


def _find_or_create_issue(token, owner, repo):
    import requests

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }
    r = requests.get(
        f"https://api.github.com/repos/{owner}/{repo}/issues",
        headers=headers, params={"state": "open", "per_page": 100}, timeout=15,
    )
    r.raise_for_status()
    for issue in r.json():
        if issue.get("title") == ISSUE_TITLE and "pull_request" not in issue:
            return issue["number"]

    body = (
        "매일 아침 자동 스크리닝 결과가 이 이슈에 댓글로 쌓입니다.\n\n"
        "⚠️ **1차 추정치일 뿐 정식 판정이 아닙니다** - "
        "`engine/screener.py`의 근사 계산(estimate_drs 등)이며, "
        "정식 분석은 `engine/pipeline.py`의 `run_analysis()`로만 확정됩니다."
    )
    r = requests.post(
        f"https://api.github.com/repos/{owner}/{repo}/issues",
        headers=headers, json={"title": ISSUE_TITLE, "body": body}, timeout=15,
    )
    r.raise_for_status()
    return r.json()["number"]


def post_to_github_issue(token, owner, repo, date_str, passed_results,
                          skipped_count, note):
    import requests

    lines = [f"## {date_str} 실행 결과"]
    if note:
        lines.append(f"⚠️ {note}")
    if not passed_results:
        lines.append("오늘은 통과 후보 없음.")
    else:
        for r in passed_results:
            c = r.candidate
            lines.append(
                f"- **{c.ticker}** [{r.tier}] FCF수익률 {r.fcf_yield*100:.2f}% · "
                f"내재성장(추정) {r.implied_growth_est*100:.2f}% · "
                f"현실성장(추정) {r.realistic_growth_est*100:.2f}% · "
                f"Gap(추정) {r.expectation_gap_est*100:+.2f}%p"
            )
    lines.append(
        f"\n(SEC 재무데이터 확보 실패로 제외된 종목 {skipped_count}개 - "
        f"1차 추정치일 뿐 정식 판정 아님)"
    )

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }
    try:
        issue_number = _find_or_create_issue(token, owner, repo)
        resp = requests.post(
            f"https://api.github.com/repos/{owner}/{repo}/issues/"
            f"{issue_number}/comments",
            headers=headers, json={"body": "\n".join(lines)}, timeout=15,
        )
        if resp.status_code >= 300:
            log(f"[GitHub Issue] 기록 실패 {resp.status_code}: {resp.text[:300]}")
            return False
    except requests.RequestException as e:  # noqa: BLE001
        log(f"[GitHub Issue] 기록 실패: {e}")
        return False
    log(f"[GitHub Issue] #{issue_number}에 오늘자 결과 기록 완료")
    return True


def main():
    import datetime
    today = datetime.date.today().isoformat()
    log(f"=== IRS 일일 스크리닝 {today} ===")

    av_key = os.environ.get("ALPHA_VANTAGE_API_KEY")
    gh_token = os.environ.get("GITHUB_TOKEN")
    repo_full = os.environ.get("GITHUB_REPOSITORY", "")  # "owner/repo" (Actions 자동 제공)

    raw_tickers = fetch_finviz_tickers()
    tickers = [t for t in raw_tickers if not looks_like_junk(t)][:MAX_CANDIDATES_TOTAL]
    log(f"[정크필터] {len(raw_tickers)} -> {len(tickers)}종목")

    sec_out = {"candidates": {}, "skipped": {}}
    for t in tickers:
        fields, limitations = ds.fetch_sec_fields(t, today)
        if fields is None:
            sec_out["skipped"][t] = limitations
        else:
            sec_out["candidates"][t] = fields
    log(f"[SEC] 계산 성공 {len(sec_out['candidates'])} / 실패(skip) {len(sec_out['skipped'])}")

    note = None
    if not av_key:
        note = "ALPHA_VANTAGE_API_KEY 시크릿 미설정 - 시가총액 조회를 건너뛰어 판정을 못 냈다."
        log(f"[AV] {note}")
        passed = []
    else:
        caps = {}
        n_calls = 0
        for t in list(sec_out["candidates"]):
            if n_calls >= MAX_AV_CALLS:
                log(f"[AV] 일일 예산({MAX_AV_CALLS}회) 소진 - 나머지는 다음날")
                break
            mc = fetch_market_cap_av(t, av_key)
            n_calls += 1
            time.sleep(AV_CALL_INTERVAL_SEC)
            if mc is None or mc < MIN_MARKET_CAP:
                continue
            caps[t] = mc
        log(f"[AV] {n_calls}회 호출, 시가총액 확보 {len(caps)}종목(3억달러 미만 제외)")

        candidates = []
        for t, mc in caps.items():
            fields = sec_out["candidates"][t]
            candidates.append(ds.Candidate(
                ticker=t, name=t, market_cap=mc, fcf0=fields["fcf0"],
                revenue_cagr_5y=fields["revenue_cagr_5y"],
                fcf_cagr_5y=fields["fcf_cagr_5y"],
                net_debt_to_ebitda=ds.DEFAULT_NDTE,
                worst_yoy_revenue=fields["worst_yoy_revenue"] or 0.0,
            ))
        results = screen_all(candidates)
        passed = [r for r in results if r.passed]
        log(f"[판정] {len(candidates)}종목 채점, {len(passed)}종목 통과")
        for r in passed:
            log(f"  PASS {r.candidate.ticker} [{r.tier}] "
                f"Gap(추정) {r.expectation_gap_est*100:+.2f}%p")

    if gh_token and "/" in repo_full:
        owner, repo = repo_full.split("/", 1)
        post_to_github_issue(gh_token, owner, repo, today, passed,
                              len(sec_out["skipped"]), note)
    else:
        log("[GitHub Issue] GITHUB_TOKEN/GITHUB_REPOSITORY 미확보 - 기록을 건너뛴다"
            "(로컬 실행 등 Actions 환경이 아닐 때 발생 가능).")

    out_path = f"/tmp/daily_screen_ci_{today}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({
            "date": today, "raw_tickers": raw_tickers, "sec": sec_out,
            "passed": [r.candidate.ticker for r in passed],
        }, f, ensure_ascii=False, indent=2)
    log(f"-> {out_path}")


if __name__ == "__main__":
    main()
