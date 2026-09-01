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
# 2026-09-01: 고정 제목 단일 이슈(`📊 IRS 일일 스크리닝 결과`)에 매일 댓글을
# 쌓던 방식을 **날짜별 이슈**로 바꿨다 - 제목이 매일 똑같으면 폰 알림만 보고는
# 오늘 볼 게 있는지 없는지 알 수 없고, 그러면 며칠 뒤부터 안 열어보게 된다.
# 제목 생성·긴급도 판정·이슈 탐색은 전부 scripts/issue_reporting.py에 있다
# (일일·주간·감시·관심종목이 같은 규칙을 쓰도록 한 곳에 모았다).


DEEP_SCREEN_DIR = os.path.join(os.path.dirname(_HERE), "reports", "deep_screen")


def run_deep_dive(passed_results, today_str):
    """
    2026-08-23(v3.65): screener 통과 후보(보통 0~2종목/일)에 대해
    engine/deep_screen.py로 자동 심층분석을 돌린다.

    이 단계가 하는 일과 하지 않는 일을 명확히 구분한다:
    - 한다: SEC에서 최대 11개년을 다시 받아 실제 3y/5y/10y CAGR·구조적할인율·
      Realistic Growth를 공식 엔진 함수로 재계산(screener.py의 6개년/상수
      근사보다 훨씬 정밀함).
    - 안 한다: model_choice_reason·competition_intensity·demand_sensitivity_pct
      같은 정성적 판단을 지어내지 않는다 - engine/deep_screen.py 자체가
      LLM 없이 이 판단들을 corpus 중앙값으로 고정하도록 설계돼 있다(문서
      참고). 그래서 이 출력도 여전히 "심층 **추정**"이지 공식 판정이 아니다.

    실패는 개별 종목 단위로만 처리한다 - 한 종목의 SEC 데이터가 이상해도
    (`Model N/A`, 창 부족 등) 나머지 종목·기본 스크리닝 보고는 계속 나가야
    한다.
    """
    from engine.deep_screen import deep_screen

    os.makedirs(DEEP_SCREEN_DIR, exist_ok=True)
    rows = []
    for r in passed_results:
        ticker = r.candidate.ticker
        try:
            series, limitations = ds.fetch_deep_series(ticker, today_str)
            if series is None:
                rows.append({"ticker": ticker, "error": f"데이터 부족: {limitations}"})
                continue
            deep = deep_screen(ticker, series, market_cap=r.candidate.market_cap)
        except Exception as e:  # noqa: BLE001 - 종목 하나의 실패가 전체를 막으면 안 됨
            log(f"[deep] {ticker} 심층분석 실패: {e!r}")
            rows.append({"ticker": ticker, "error": repr(e)})
            continue

        row = {
            "ticker": ticker, "date": today_str,
            "revenue_cagr_3y": deep.revenue_cagr_3y,
            "revenue_cagr_5y": deep.revenue_cagr_5y,
            "revenue_cagr_10y": deep.revenue_cagr_10y,
            "drs": deep.drs, "lynch_type": deep.lynch_type,
            "structural_discount_pct": deep.structural_discount_pct,
            "realistic_growth": deep.realistic_growth,
            "implied_growth": deep.implied_growth, "gap": deep.gap,
            "judgment": deep.judgment,
            "assumed_inputs": deep.assumed_inputs,
            "data_limitations": deep.data_limitations,
        }

        # 전일 대비 의미있는 변화 탐지 - 같은 종목의 가장 최근 스냅샷과 대조.
        # 통과 후보가 하루이틀 연속으로 뜨는 경우(가격이 더 빠지는 중 등)에만
        # 발생하므로 대부분은 prior=None이고 그건 정상이다.
        prior = _latest_deep_snapshot(ticker, before_date=today_str)
        if prior:
            row["change_vs_prior"] = {
                "prior_date": prior["date"],
                "gap_delta": deep.gap - prior["gap"],
                "realistic_growth_delta": deep.realistic_growth - prior["realistic_growth"],
                "judgment_changed": deep.judgment != prior["judgment"],
            }

        out_path = os.path.join(DEEP_SCREEN_DIR, f"{ticker}_{today_str}.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(row, f, ensure_ascii=False, indent=2)
        rows.append(row)
    return rows


def _latest_deep_snapshot(ticker, before_date):
    """같은 종목의 직전 심층분석 스냅샷(있으면)을 읽는다."""
    if not os.path.isdir(DEEP_SCREEN_DIR):
        return None
    candidates = sorted(
        f for f in os.listdir(DEEP_SCREEN_DIR)
        if f.startswith(f"{ticker}_") and f.endswith(".json") and f < f"{ticker}_{before_date}.json"
    )
    if not candidates:
        return None
    with open(os.path.join(DEEP_SCREEN_DIR, candidates[-1]), encoding="utf-8") as f:
        return json.load(f)


def format_deep_dive_section(rows):
    if not rows:
        return ""
    lines = ["\n### 🔬 통과 후보 심층분석(자동, 1차 추정 - 공식판정 아님)"]
    for row in rows:
        if "error" in row:
            lines.append(f"- **{row['ticker']}**: 심층분석 실패 - {row['error']}")
            continue
        lines.append(
            f"- **{row['ticker']}** [{row['judgment']}] "
            f"현실성장(심층) {row['realistic_growth']*100:.2f}% · "
            f"내재성장(Gordon) {row['implied_growth']*100:.2f}% · "
            f"Gap {row['gap']*100:+.2f}%p · DRS {row['drs']:.1f} · "
            f"{row['lynch_type']}"
        )
        cvp = row.get("change_vs_prior")
        if cvp:
            lines.append(
                f"  전일({cvp['prior_date']}) 대비 Gap {cvp['gap_delta']*100:+.2f}%p"
                + (" ⚠️ 판정변화" if cvp["judgment_changed"] else ""))
        if row["data_limitations"]:
            lines.append(f"  ⚠️ {row['data_limitations'][0]}")
    lines.append(
        "\n<sub>가정: 경쟁강도·수요민감도·순부채는 corpus 중앙값(정성조사 "
        "안 함), 모델은 항상 single_stage(Gordon). run_analysis()로 정식 "
        "확정할 것.</sub>")
    return "\n".join(lines)


def build_monitor_section(today_str):
    """
    보유종목 감시 섹션(v3.64). 스크리닝과 **같은 코멘트**에 실어 하루 알림을
    1건으로 유지한다 - 알림이 늘어나면 사람이 전체를 무시하게 되고, 그건 이
    감시가 막으려는 실패 그 자체다.

    ⚠️ 절대 예외를 밖으로 던지지 않는다. 감시는 스크리닝의 부가기능이므로
    감시가 깨져도 스크리닝 결과 보고는 반드시 나가야 한다(반대로 만들면
    부가기능 하나가 본체를 멈춘다).
    """
    return run_monitor_safe(today_str)[1]


def run_monitor_safe(today_str):
    """
    감시를 돌려 `(결과dict|None, 표시용 텍스트)`를 준다.

    결과 dict가 필요한 이유는 이슈 **제목의 긴급도**를 정하기 위해서다 -
    텍스트만 받으면 조치사항이 있는지를 문자열 파싱으로 되짚어야 하고, 그건
    v3.42가 반증조건 날짜 추출에서 이미 겪은 오탐 경로다.
    """
    try:
        from datetime import date as _date

        from daily_monitor_ci import format_monitor_section, run_monitor
        result = run_monitor(_date.fromisoformat(today_str))
        return result, format_monitor_section(result)
    except Exception as e:  # noqa: BLE001
        log(f"[monitor] 감시 섹션 생성 실패(스크리닝은 계속 진행): {e!r}")
        return None, f"### 🔭 보유종목 감시\n⚠️ 감시 실행 실패: `{e!r}`"


# 제외 사유 분류 - **인프라 장애와 정상 제외를 구분하는 것이 목적이다.**
# 전에는 둘 다 "SEC 재무데이터 확보 실패"로 뭉개져서, 파이프라인이 아무것도
# 채점하지 못한 날과 후보가 정말 없는 날이 리포트상 똑같아 보였다(2026-08-23/24
# 실측: 25종목 중 24종목 실패인데 "오늘은 통과 후보 없음"으로만 표시됨).
#
# ⚠️ HTTP 404는 인프라 장애가 **아니다.** ETF·펀드는 CIK는 있어도 XBRL
# companyfacts가 없어서 404를 돌려준다(SPY 실측). 404를 장애로 세면 Finviz
# 목록에 ETF가 섞일 때마다 가짜 경보가 뜨고, 그러면 진짜 장애가 묻힌다 -
# 이 수정이 막으려는 알림 피로가 다른 경로로 재발한다.
SKIP_CATEGORIES = (
    # (라벨, 매칭 부분문자열들, 인프라 장애인가)  ※ 위에서부터 먼저 매칭
    ("XBRL 재무제표 없음(ETF·펀드 등)", ("HTTP 404",), False),
    ("SEC 요청 거부·네트워크", ("조회 실패",), True),
    ("SEC 등록 없음(신규상장·비SEC 등)", ("티커 매핑표에 없음",), False),
    ("FCF 기준·최종연도 0 이하(모델 적용불가)", ("0 이하",), False),
    ("연도 데이터 부족", ("공통 확보 연도", "최소 구간"), False),
)


def classify_skips(skipped):
    """{ticker: [limitation, ...]} -> [(라벨, [티커...], 인프라장애 여부)]"""
    buckets = {}
    for ticker, limitations in skipped.items():
        text = " ".join(str(x) for x in (limitations or []) if x)
        label, is_infra = "기타·미분류", False
        for lbl, needles, infra in SKIP_CATEGORIES:
            if any(n in text for n in needles):
                label, is_infra = lbl, infra
                break
        buckets.setdefault((label, is_infra), []).append(ticker)
    return [(lbl, sorted(ts), infra) for (lbl, infra), ts in buckets.items()]


def format_funnel(funnel, skipped):
    """깔때기 각 단계를 그대로 보여준다 - 어디서 끊겼는지 숨기지 않는다."""
    lines = [
        "",
        "<details><summary>파이프라인 깔때기</summary>",
        "",
        f"- Finviz 수집: **{funnel['finviz']}종목** → 정크필터 후 "
        f"**{funnel['after_junk']}종목**",
        f"- SEC 재무계산 성공: **{funnel['sec_ok']}종목** "
        f"(제외 {funnel['sec_skipped']}종목)",
        f"- 시가총액 확보: **{funnel['with_cap']}종목** "
        f"(3억달러 미만·조회실패 제외)",
        f"- 채점: **{funnel['scored']}종목** → 통과 **{funnel['passed']}종목**",
    ]
    groups = sorted(classify_skips(skipped), key=lambda g: (not g[2], -len(g[1])))
    if groups:
        lines.append("")
        lines.append("제외 사유:")
        for label, tickers, infra in groups:
            mark = "🔧 " if infra else ""
            shown = ", ".join(tickers[:10]) + (" 외" if len(tickers) > 10 else "")
            lines.append(f"- {mark}{label} — {len(tickers)}종목: {shown}")
    lines.append("")
    lines.append("</details>")
    return "\n".join(lines)


def post_to_github_issue(token, owner, repo, date_str, passed_results,
                          skipped, note, deep_rows=None, funnel=None):
    import issue_reporting as IR

    lines = [f"## {date_str} 실행 결과"]
    if note:
        lines.append(f"⚠️ {note}")

    scored = (funnel or {}).get("scored")
    groups = classify_skips(skipped)
    infra_tickers = sorted(t for _, ts, infra in groups if infra for t in ts)

    if passed_results:
        for r in passed_results:
            c = r.candidate
            lines.append(
                f"- **{c.ticker}** [{r.tier}] FCF수익률 {r.fcf_yield*100:.2f}% · "
                f"내재성장(추정) {r.implied_growth_est*100:.2f}% · "
                f"현실성장(추정) {r.realistic_growth_est*100:.2f}% · "
                f"Gap(추정) {r.expectation_gap_est*100:+.2f}%p"
            )
    elif scored == 0:
        # ⚠️ 이 분기가 이 수정의 핵심이다. 채점 자체가 0건인 것을 "통과 후보
        # 없음"으로 적으면, 정상적인 빈 결과와 파이프라인 고장이 구분되지 않는다.
        lines.append(
            "🛑 **채점된 종목이 0개다 — '통과 후보 없음'이 아니라 스크리닝이 "
            "실행되지 못했다는 뜻이다.** 아래 깔때기에서 끊긴 지점을 확인할 것.")
    else:
        lines.append(f"{scored}종목을 채점했고 통과 후보는 없음.")

    if infra_tickers:
        lines.append(
            f"\n🔧 **인프라 장애로 제외 {len(infra_tickers)}종목** "
            f"(데이터 문제가 아니라 조회 자체가 실패 — 조치 필요): "
            f"{', '.join(infra_tickers[:12])}"
            f"{' 외' if len(infra_tickers) > 12 else ''}")

    if funnel:
        lines.append(format_funnel(funnel, skipped))
    lines.append("\n(1차 추정치일 뿐 정식 판정 아님)")
    if deep_rows:
        lines.append(format_deep_dive_section(deep_rows))
    lines.append("\n---\n")
    monitor_result, monitor_text = run_monitor_safe(date_str)
    lines.append(monitor_text)

    # 제목에 박을 긴급도. 감시 조치사항 > 파이프라인 장애 > 통과 후보 > 정상
    # (근거는 issue_reporting 모듈 docstring 참고).
    urgency, detail = IR.daily_urgency(
        monitor_result=monitor_result, n_passed=len(passed_results or []),
        scored=scored, infra_failures=len(infra_tickers))
    num = IR.report("daily", date_str, "\n".join(lines),
                    urgency_key=urgency, detail=detail, log=log,
                    creds=(token, owner, repo))
    return num is not None


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
    for label, ts, infra in sorted(classify_skips(sec_out["skipped"]),
                                    key=lambda g: (not g[2], -len(g[1]))):
        log(f"[SEC] {'🔧 ' if infra else ''}{label}: {len(ts)}종목 "
            f"({', '.join(ts[:8])}{' 외' if len(ts) > 8 else ''})")

    funnel = {
        "finviz": len(raw_tickers),
        "after_junk": len(tickers),
        "sec_ok": len(sec_out["candidates"]),
        "sec_skipped": len(sec_out["skipped"]),
        "with_cap": 0,
        "scored": 0,
        "passed": 0,
    }

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
        funnel["with_cap"] = len(caps)
        funnel["scored"] = len(candidates)
        funnel["passed"] = len(passed)
        log(f"[판정] {len(candidates)}종목 채점, {len(passed)}종목 통과")
        for r in passed:
            log(f"  PASS {r.candidate.ticker} [{r.tier}] "
                f"Gap(추정) {r.expectation_gap_est*100:+.2f}%p")

    deep_rows = []
    if passed:
        log(f"[deep] 통과 후보 {len(passed)}종목 심층분석 시작")
        try:
            deep_rows = run_deep_dive(passed, today)
        except Exception as e:  # noqa: BLE001 - 심층분석 실패가 스크리닝 보고를 막으면 안 됨
            log(f"[deep] 전체 실패(스크리닝 결과는 그대로 보고): {e!r}")
            deep_rows = []
        for row in deep_rows:
            if "error" not in row:
                log(f"  DEEP {row['ticker']} [{row['judgment']}] "
                    f"Gap(심층) {row['gap']*100:+.2f}%p")

    if gh_token and "/" in repo_full:
        owner, repo = repo_full.split("/", 1)
        post_to_github_issue(gh_token, owner, repo, today, passed,
                              sec_out["skipped"], note, deep_rows, funnel)
    else:
        log("[GitHub Issue] GITHUB_TOKEN/GITHUB_REPOSITORY 미확보 - 기록을 건너뛴다"
            "(로컬 실행 등 Actions 환경이 아닐 때 발생 가능).")

    out_path = f"/tmp/daily_screen_ci_{today}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({
            "date": today, "raw_tickers": raw_tickers, "sec": sec_out,
            "funnel": funnel,
            "skip_groups": [
                {"label": lbl, "infrastructure_failure": infra, "tickers": ts}
                for lbl, ts, infra in classify_skips(sec_out["skipped"])
            ],
            "passed": [r.candidate.ticker for r in passed],
            "deep_screen": deep_rows,
        }, f, ensure_ascii=False, indent=2)
    log(f"-> {out_path}")


if __name__ == "__main__":
    main()
