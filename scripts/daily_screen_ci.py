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
  - 결과기록 -> Notion REST API 직접 호출(MCP 아님, 사용자가 발급한 통합 토큰)

SEC 재무 계산·screener.py 판정 로직은 **재구현하지 않는다** - daily_screen.py를
그대로 import해서 쓴다(중복 계산이 두 계산을 미묘하게 어긋나게 만든다는
Simplicity First 원칙).

⚠️ Finviz 접근은 반드시 화이트리스트 프리셋만 쓴다(robots.txt, source_registry.py
의 finviz 항목 참고). 커스텀 필터(f=)는 여기서도 금지.

시크릿 없이도 죽지 않는다 - ALPHA_VANTAGE_API_KEY/NOTION_TOKEN/NOTION_PAGE_ID가
없으면 그 단계만 건너뛰고 로그에 명시한다(Finviz+SEC 부분만 검증하는 드라이런이
가능해야 하므로).
"""
import json
import os
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
                offset = i * 20 + 1  # v=340 프리셋은 페이지당 10개, r=오프셋
                url = base_url if i == 0 else f"{base_url}&r={i * 10 + 1}"
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    page.wait_for_timeout(1500)
                except Exception as e:  # noqa: BLE001
                    log(f"[Finviz] {name} 페이지{i+1} 로드 실패: {e}")
                    break
                links = page.locator('a[href*="quote.ashx?t="]')
                count = links.count()
                if count == 0:
                    log(f"[Finviz][진단] {name} 페이지{i+1}: title={page.title()!r} "
                        f"html길이={len(page.content())} url={page.url}")
                    dump_path = f"/tmp/finviz_debug_{name}_{i}.html"
                    with open(dump_path, "w", encoding="utf-8") as f:
                        f.write(page.content())
                    log(f"[Finviz][진단] HTML 저장: {dump_path}")
                    break
                for j in range(count):
                    t = links.nth(j).inner_text().strip()
                    if t and t.isupper() and t not in seen:
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


# ── 4) Notion (직접 REST, MCP 아님) ────────────────────────────────────
def post_to_notion(token, page_id, date_str, passed_results, skipped_count, note):
    import requests

    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }
    children = [
        {"object": "block", "type": "heading_2",
         "heading_2": {"rich_text": [{"text": {"content": f"{date_str} 실행 결과"}}]}},
    ]
    if note:
        children.append({"object": "block", "type": "paragraph", "paragraph": {
            "rich_text": [{"text": {"content": f"⚠️ {note}"}}]}})
    if not passed_results:
        children.append({"object": "block", "type": "paragraph", "paragraph": {
            "rich_text": [{"text": {"content": "오늘은 통과 후보 없음."}}]}})
    else:
        for r in passed_results:
            c = r.candidate
            text = (f"{c.ticker} [{r.tier}] FCF수익률 {r.fcf_yield*100:.2f}% · "
                    f"내재성장(추정) {r.implied_growth_est*100:.2f}% · "
                    f"현실성장(추정) {r.realistic_growth_est*100:.2f}% · "
                    f"Gap(추정) {r.expectation_gap_est*100:+.2f}%p")
            children.append({"object": "block", "type": "bulleted_list_item",
                              "bulleted_list_item": {"rich_text": [{"text": {"content": text}}]}})
    children.append({"object": "block", "type": "paragraph", "paragraph": {
        "rich_text": [{"text": {
            "content": f"(SEC 재무데이터 확보 실패로 제외된 종목 {skipped_count}개 - "
                       f"1차 추정치일 뿐 정식 판정 아님)"}}]}})

    resp = requests.patch(
        f"https://api.notion.com/v1/blocks/{page_id}/children",
        headers=headers, json={"children": children}, timeout=15,
    )
    if resp.status_code >= 300:
        log(f"[Notion] 기록 실패 {resp.status_code}: {resp.text[:300]}")
        return False
    log("[Notion] 오늘자 결과 기록 완료")
    return True


def main():
    import datetime
    today = datetime.date.today().isoformat()
    log(f"=== IRS 일일 스크리닝 {today} ===")

    av_key = os.environ.get("ALPHA_VANTAGE_API_KEY")
    notion_token = os.environ.get("NOTION_TOKEN")
    notion_page_id = os.environ.get("NOTION_PAGE_ID")

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

    if notion_token and notion_page_id:
        post_to_notion(notion_token, notion_page_id, today, passed,
                        len(sec_out["skipped"]), note)
    else:
        log("[Notion] NOTION_TOKEN/NOTION_PAGE_ID 시크릿 미설정 - 기록을 건너뛴다.")

    out_path = f"/tmp/daily_screen_ci_{today}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({
            "date": today, "raw_tickers": raw_tickers, "sec": sec_out,
            "passed": [r.candidate.ticker for r in passed],
        }, f, ensure_ascii=False, indent=2)
    log(f"-> {out_path}")


if __name__ == "__main__":
    main()
