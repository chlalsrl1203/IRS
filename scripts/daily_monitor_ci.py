"""
일일 보유종목 감시 (v3.64 신규, 2026-08-23) - GitHub Actions에서 매일 실행.

## 왜 필요했나 (실측 근거)

기존 자동화(`daily_screen_ci.py`)는 매일 **신규 후보**만 찾는다. 그런데 이미
정식분석을 마친 **34종목과 매수리스트 12종목은 아무도 감시하지 않았다.**

- `engine/thesis_monitor.py`는 2026-08-13에 **수동 1회** 실행됐고, 그때 TTD의
  반증조건 3개 동시 발동을 실제로 잡아냈다(이 프로젝트 유일의 외부검증 성공
  사례, 매수비중 4.80%->2.70% 축소로 이어짐).
- 그런데 그 뒤 **10일간 한 번도 다시 돌지 않았다.** 즉 v3.42가 발견했던 실패
  ("반증조건 트리거 날짜 5건이 전부 기한이 지났는데 12일간 아무도 열어보지
  않았다")가 감시도구 자체에서 그대로 재발했다.

## 이 스크립트가 하지 않는 것 (중요)

**반증조건이 발동했는지 판정하지 않는다.** v3.42가 확립한 원칙 그대로다 -
정규식은 트리거 날짜와 서술적 날짜를 구분하지 못하고(TCOM의 소송 집단기간이
실제 오탐이었다), 발동 여부는 실적을 읽어야만 알 수 있다. 이 스크립트는
**"오늘 사람이 봐야 할 것"만 골라낸다.**

또한 **LLM을 계산 경로에 넣지 않는다.** 전부 결정론적이다(날짜 비교 + 기존
엔진 함수 호출). 같은 입력이면 같은 출력이 나온다.

## 상태 파일은 CI가 쓰지 않는다

`monitor/acknowledgements.json`은 **읽기 전용**으로 다룬다. 확인은 사람의
행위이므로 저녁 검토 세션에서 사람이 커밋한다 - CI에 쓰기 권한을 주지 않아
자동 커밋 사고가 원천적으로 불가능하다.
"""

import json
import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.monitor_state import (  # noqa: E402
    STATE_PATH, load_acknowledgements, triage,
)
from engine.thesis_monitor import scan_falsification_conditions  # noqa: E402

LEDGER_DIR = "ledger"
PREDICTIONS_DIR = "predictions"


def _iter_ledgers(ledger_dir: str):
    """티커당 최신 1건만 사용(구 파일 잔존 시 중복계상 방지 - v3.32 사고)."""
    latest = {}
    if not os.path.isdir(ledger_dir):
        return []
    for name in sorted(os.listdir(ledger_dir)):
        if not name.endswith(".json"):
            continue
        with open(os.path.join(ledger_dir, name), encoding="utf-8") as f:
            d = json.load(f)
        t = d["meta"]["ticker"]
        prev = latest.get(t)
        if prev is None or d["meta"]["analyzed_at"] > prev["meta"]["analyzed_at"]:
            latest[t] = d
    return [latest[k] for k in sorted(latest)]


def check_predictions_due(predictions_dir: str, today: date) -> dict:
    """
    2026-08-16에 동결한 예측 34건 중 해소기한이 지난 것을 골라낸다.

    ⚠️ 해소(실제값 입력)는 자동으로 하지 않는다 - prediction_ledger가 코어
    해시로 사후수정을 막고 있고, 실제값 확보는 사람이 1차 자료를 봐야 한다.
    여기서는 **기한이 됐다는 사실만** 알린다.
    """
    due, pending, resolved = [], 0, 0
    if not os.path.isdir(predictions_dir):
        return {"due": [], "pending": 0, "resolved": 0, "dir_missing": True}
    for name in sorted(os.listdir(predictions_dir)):
        if not name.endswith(".json"):
            continue
        with open(os.path.join(predictions_dir, name), encoding="utf-8") as f:
            d = json.load(f)
        if d.get("status") == "RESOLVED" or d.get("actual_value") is not None:
            resolved += 1
            continue
        core = d.get("core", {})
        target = core.get("resolution_date") or core.get("target_date")
        if not target:
            pending += 1
            continue
        t = date.fromisoformat(str(target)[:10])
        if t <= today:
            due.append({
                "prediction_id": d.get("prediction_id"),
                "ticker": core.get("ticker"),
                "metric": core.get("metric"),
                "resolution_date": str(target)[:10],
                "days_past": (today - t).days,
            })
        else:
            pending += 1
    due.sort(key=lambda x: -x["days_past"])
    return {"due": due, "pending": pending, "resolved": resolved,
            "dir_missing": False}


def run_monitor(today: date, ledger_dir: str = LEDGER_DIR,
                ack_path: str = STATE_PATH,
                predictions_dir: str = PREDICTIONS_DIR) -> dict:
    """일일 감시 1회 실행. 순수 함수 - 파일을 쓰지 않는다."""
    ledgers = _iter_ledgers(ledger_dir)
    scans = [scan_falsification_conditions(d, today) for d in ledgers]
    acks = load_acknowledgements(ack_path)
    t = triage(scans, acks, today)
    preds = check_predictions_due(predictions_dir, today)
    return {
        "generated_for": today.isoformat(),
        "n_ledgers": len(ledgers),
        "falsification": t,
        "predictions": preds,
        "action_required": bool(t["needs_review"]) or bool(preds["due"]),
    }


def format_monitor_section(result: dict) -> str:
    """GitHub Issue 코멘트에 붙일 마크다운 섹션."""
    t = result["falsification"]
    p = result["predictions"]
    L = [f"### 🔭 보유종목 감시 ({result['n_ledgers']}종목)"]

    if t.get("state_file_missing"):
        L.append(
            "⚠️ `monitor/acknowledgements.json`이 없다 - 확인 기록 없이 "
            "**전부 미확인**으로 취급 중.")

    if t["needs_review"]:
        L.append(f"**🚨 확인 필요 {len(t['needs_review'])}건**")
        for r in t["needs_review"]:
            L.append(
                f"- **{r['ticker']}** 트리거 {r['trigger_date']} "
                f"({r['days_past']}일 경과) — {r['reason']}")
            ctx = (r.get("context") or "").strip().replace("\n", " ")
            if ctx:
                L.append(f"  > {ctx[:180]}")
    else:
        L.append("확인 필요 신규 항목 **없음**.")

    if t["triggered"]:
        names = ", ".join(f"{r['ticker']}({r['trigger_date']})"
                          for r in t["triggered"])
        L.append(f"🔴 반증조건 발동상태 유지: {names} — 조치 완료분, 재알림 아님.")

    if p["due"]:
        L.append(f"**📌 예측 해소기한 도래 {len(p['due'])}건**")
        for d in p["due"][:10]:
            L.append(
                f"- {d['ticker']} · {d['metric']} · 기한 {d['resolution_date']} "
                f"({d['days_past']}일 경과)")

    L.append(
        f"\n<sub>대기 {len(t['pending_future'])} · 확인완료 "
        f"{len(t['acknowledged'])} · 날짜없는 사건기반 {len(t['undated'])} · "
        f"반증조건 미기재 {len(t['no_conditions'])} "
        f"(⚠️ 미기재는 '안전'이 아니라 '감시근거 없음') · "
        f"예측 미도래 {p['pending']}</sub>")
    return "\n".join(L)


def post_standalone(result: dict, today_str: str) -> bool:
    """
    감시 결과만 단독으로 GitHub Issue에 올린다.

    평소에는 `daily_screen_ci.py`가 스크리닝 결과와 **한 코멘트**로 합쳐
    올리므로 이 경로는 안 쓴다. Finviz/Playwright 장애로 스크리닝 단계가
    죽었을 때만 쓰는 대체 경로다 - 감시는 네트워크 의존이 없는데(ledger와
    날짜만 본다) 스크리닝 하류에 있다는 이유로 같이 멈추면, 이 감시가
    막으려는 실패("아무도 안 본다")가 그대로 재발한다.
    """
    token = os.environ.get("GITHUB_TOKEN")
    repo_full = os.environ.get("GITHUB_REPOSITORY", "")
    if not token or "/" not in repo_full:
        print("[monitor] GITHUB_TOKEN/REPOSITORY 미확보 - 단독 게시 건너뜀")
        return False
    owner, repo = repo_full.split("/", 1)
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from daily_screen_ci import _find_or_create_issue  # 이슈 탐색 로직 재사용

    import requests
    body = (f"## {today_str} 감시 단독 실행\n"
            f"⚠️ 스크리닝 단계가 실패해 감시만 별도로 보고한다.\n\n"
            + format_monitor_section(result))
    try:
        num = _find_or_create_issue(token, owner, repo)
        r = requests.post(
            f"https://api.github.com/repos/{owner}/{repo}/issues/{num}/comments",
            headers={"Authorization": f"Bearer {token}",
                     "Accept": "application/vnd.github+json"},
            json={"body": body}, timeout=15)
        if r.status_code >= 300:
            print(f"[monitor] 게시 실패 {r.status_code}: {r.text[:200]}")
            return False
    except Exception as e:  # noqa: BLE001
        print(f"[monitor] 게시 실패: {e!r}")
        return False
    print(f"[monitor] Issue #{num}에 단독 게시 완료")
    return True


def main():
    today = date.fromisoformat(os.environ.get("IRS_TODAY", date.today().isoformat()))
    result = run_monitor(today)
    out_path = f"/tmp/daily_monitor_{today.isoformat()}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2, default=str)
    print(format_monitor_section(result))
    print(f"\n[monitor] 결과 저장: {out_path}")
    print(f"[monitor] action_required={result['action_required']}")
    if "--post" in sys.argv:
        post_standalone(result, today.isoformat())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
