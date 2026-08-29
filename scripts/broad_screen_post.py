"""
broad_screen_post.py (2026-08-29) — broad_screen.py의 결과를 GitHub Issue로.

일일 스크리닝(daily_screen_ci.py)과 **별도 이슈 스레드**를 쓴다 - 주 1회
전체 유니버스 결과를 매일 도는 이슈에 섞으면 알림 피로가 생기고, "오늘
급락한 종목"과 "전체 유니버스 구조적 저평가 후보"는 성격이 다른 정보라
분리해야 나중에 훑어보기도 쉽다.
"""
import glob
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))

ISSUE_TITLE = "📈 IRS 대규모 스크리닝 결과(주간)"
REPORTS_DIR = os.path.join(os.path.dirname(_HERE), "reports", "broad_screen")


def log(msg):
    print(msg, flush=True)


def latest_report():
    paths = sorted(glob.glob(os.path.join(REPORTS_DIR, "broad_screen_*.json")))
    if not paths:
        return None
    with open(paths[-1], encoding="utf-8") as f:
        return json.load(f)


def format_body(d):
    lines = [
        f"## {d['retrieved_at']} 대규모 스크리닝(Stage 1, SEC 전용)",
        "",
        f"원본 유니버스 **{d['universe_total']}종목** -> 이름 사전필터 후 "
        f"**{d['attempted']}종목** 시도 -> SEC 재무계산 성공 **{d['sec_ok']}종목** "
        f"-> 채점 **{d['scored']}종목** -> 통과 **{d['passed']}종목**",
        "",
        "⚠️ **1차 추정치일 뿐 정식 판정이 아니다.** 시가총액은 SEC "
        "`EntityPublicFloat`(10-K 표지, 계열주주 제외·최대 2년까지 낡을 수 "
        "있음) 근사치이고, 경쟁강도·마진변동성 등은 corpus 중앙값 가정이다 - "
        "`engine.deep_screen`/`run_analysis()`로 정밀 재확인 전에는 매수 "
        "판단에 쓰지 말 것.",
        "",
    ]
    passed = d.get("passed_tickers") or []
    if passed:
        lines.append("### 통과 후보")
        lines.append("| 종목 | 등급 | Gap(추정) | 시총(근사) | 비고 |")
        lines.append("|---|:--:|---:|---:|---|")
        for r in sorted(passed, key=lambda x: -x["expectation_gap_est"]):
            lines.append(
                f"| **{r['ticker']}** | {r['tier']} "
                f"| {r['expectation_gap_est'] * 100:+.2f}%p "
                f"| ${r['market_cap'] / 1e9:.1f}B | {r.get('note', '')} |")
    else:
        lines.append("**통과 후보 없음.**")

    lines.append("")
    lines.append("<details><summary>제외 사유 분포</summary>\n")
    for g in d.get("skip_breakdown", []):
        mark = "🔧 " if g.get("infra_failure") else ""
        shown = ", ".join(g["sample"])
        more = f" 외 {g['count'] - len(g['sample'])}종목" if g["count"] > len(g["sample"]) else ""
        lines.append(f"- {mark}{g['label']} — **{g['count']}종목**: {shown}{more}")
    lines.append("\n</details>")
    return "\n".join(lines)


def _find_or_create_issue(token, owner, repo):
    import requests

    headers = {"Authorization": f"Bearer {token}",
              "Accept": "application/vnd.github+json"}
    r = requests.get(
        f"https://api.github.com/repos/{owner}/{repo}/issues",
        headers=headers, params={"state": "open", "per_page": 100}, timeout=15)
    r.raise_for_status()
    for issue in r.json():
        if issue.get("title") == ISSUE_TITLE and "pull_request" not in issue:
            return issue["number"]
    body = (
        "매주 토요일 자동으로 SEC 등록 전체 상장기업(약 1만개)을 훑은 결과가 "
        "이 이슈에 댓글로 쌓입니다.\n\n"
        "⚠️ **1차 추정치일 뿐 정식 판정이 아닙니다** - `engine/broad_screen`은 "
        "`engine.screener.screen()`을 그대로 재사용하되 시가총액을 SEC "
        "`EntityPublicFloat`으로 근사합니다. 정식 분석은 "
        "`engine/pipeline.py`의 `run_analysis()`로만 확정됩니다."
    )
    r = requests.post(
        f"https://api.github.com/repos/{owner}/{repo}/issues",
        headers=headers, json={"title": ISSUE_TITLE, "body": body}, timeout=15)
    r.raise_for_status()
    return r.json()["number"]


def post(body):
    import requests

    token = os.environ.get("GITHUB_TOKEN")
    repo_full = os.environ.get("GITHUB_REPOSITORY", "")
    if not token or "/" not in repo_full:
        log("[broad_screen_post] GITHUB_TOKEN/GITHUB_REPOSITORY 미확보 - 게시 건너뜀")
        return False
    owner, repo = repo_full.split("/", 1)
    try:
        num = _find_or_create_issue(token, owner, repo)
        r = requests.post(
            f"https://api.github.com/repos/{owner}/{repo}/issues/{num}/comments",
            headers={"Authorization": f"Bearer {token}",
                     "Accept": "application/vnd.github+json"},
            json={"body": body}, timeout=15)
        if r.status_code >= 300:
            log(f"[broad_screen_post] 게시 실패 {r.status_code}: {r.text[:300]}")
            return False
    except Exception as e:  # noqa: BLE001
        log(f"[broad_screen_post] 게시 실패: {e!r}")
        return False
    log(f"[broad_screen_post] Issue #{num}에 게시 완료")
    return True


def main():
    d = latest_report()
    if d is None:
        log("[broad_screen_post] reports/broad_screen/*.json이 없다 - 게시 건너뜀"
            "(broad_screen.py가 먼저 실행돼야 한다)")
        return
    post(format_body(d))


if __name__ == "__main__":
    main()
