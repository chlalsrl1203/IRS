"""
update_research_queue.py (2026-08-30) — 스크리닝 결과를 연구 우선순위 큐에 병합.

주간 대규모 스크리닝이 끝난 뒤 실행한다. 하는 일은 셋뿐이다:

  1. 최신 `reports/broad_screen/broad_screen_*.json`을 읽는다
  2. 동일법인(CIK) 중복을 제거한 뒤 `engine.research_queue`로 큐에 병합한다
  3. ledger·매수리스트에서 상태를 **파생**해 우선순위 순으로 저장한다

**새 밸류에이션 로직 0줄.** 판정을 만들지도, 바꾸지도 않는다 - 이미 나온
결과에 "무엇을 다음에 분석할 것인가"라는 순서만 붙인다.

⚠️ 이 스크립트는 매수리스트를 **건드리지 않는다.** 스크리닝 후보가 매수리스트에
들어가려면 정식분석(`run_analysis`)과 정성조사가 필요하고, 그건 사람의 주관적
입력이 있어야 한다(v3.19). 큐는 그 사람 작업의 **입력 순서**를 정할 뿐이다.
"""
import argparse
import datetime
import glob
import json
import os
import sys
import urllib.request

_HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(_HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, _HERE)

from engine.filing_dates import DEFAULT_USER_AGENT  # noqa: E402
from engine.research_queue import (  # noqa: E402
    annotate, merge_run, next_to_research, persistence_available, priority_order,
)

from broad_screen import dedupe_by_cik  # noqa: E402

QUEUE_PATH = os.path.join(ROOT, "reports", "research_queue.json")
BROAD_GLOB = os.path.join(ROOT, "reports", "broad_screen", "broad_screen_*.json")
LEDGER_GLOB = os.path.join(ROOT, "ledger", "*.json")
BUYLIST_GLOB = os.path.join(ROOT, "reports", "buylist_[0-9]*.json")


def log(m):
    print(m, flush=True)


def ledger_tickers():
    out = set()
    for p in glob.glob(LEDGER_GLOB):
        try:
            t = (json.load(open(p, encoding="utf-8")).get("meta") or {}).get("ticker")
        except (OSError, json.JSONDecodeError):
            continue
        if t:
            out.add(t)
    return out


def buylist_tickers():
    paths = sorted(glob.glob(BUYLIST_GLOB))
    if not paths:
        return set()
    try:
        rows = json.load(open(paths[-1], encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set()
    return {r.get("ticker") for r in rows if isinstance(r, dict)}


def _dedupe(passed, user_agent):
    """
    동일법인 중복 제거. CIK가 필요하므로 SEC 티커목록을 한 번 받는다 -
    실패하면 중복 제거를 **건너뛰되 그 사실을 남긴다**(조용히 다르게 굴지 않게).
    """
    try:
        req = urllib.request.Request(
            "https://www.sec.gov/files/company_tickers.json",
            headers={"User-Agent": user_agent})
        raw = json.load(urllib.request.urlopen(req, timeout=30))
    except Exception as e:  # noqa: BLE001
        return passed, f"CIK 조회 실패로 동일법인 중복 제거를 건너뜀: {e!r}"
    t2c = {r["ticker"].upper(): str(r["cik_str"]).zfill(10) for r in raw.values()}
    rows = [{**x, "cik": t2c.get(x["ticker"], x["ticker"])} for x in passed]
    kept, removed = dedupe_by_cik(rows)
    return kept, (f"동일법인 중복 {removed}티커 병합" if removed else None)


def run(broad_path=None, queue_path=QUEUE_PATH, today=None, user_agent=None):
    today = today or datetime.date.today().isoformat()
    user_agent = user_agent or DEFAULT_USER_AGENT

    paths = sorted(glob.glob(BROAD_GLOB))
    broad_path = broad_path or (paths[-1] if paths else None)
    if not broad_path:
        raise FileNotFoundError(
            f"대규모 스크리닝 결과가 없다({BROAD_GLOB}) - 큐를 갱신할 입력이 없다")
    bs = json.load(open(broad_path, encoding="utf-8"))
    run_date = bs.get("retrieved_at") or today
    log(f"[큐] 입력: {os.path.basename(broad_path)} (실행일 {run_date})")

    passed, note = _dedupe(bs.get("passed_tickers") or [], user_agent)
    if note:
        log(f"[큐] {note}")
    log(f"[큐] 통과 {len(passed)}개 법인 병합")

    queue = {}
    if os.path.exists(queue_path):
        try:
            queue = json.load(open(queue_path, encoding="utf-8")).get("entries", {})
        except (OSError, json.JSONDecodeError) as e:
            log(f"[큐] 기존 큐를 읽지 못했다({e!r}) - 새로 시작한다")

    queue = merge_run(queue, passed, run_date)
    entries = annotate(queue, ledger_tickers(), buylist_tickers(), today)
    ordered = priority_order(list(entries.values()))
    persistence = persistence_available(entries)

    by_state = {}
    for e in ordered:
        by_state[e["state"]] = by_state.get(e["state"], 0) + 1
    log(f"[큐] 총 {len(ordered)}종목 · 상태 {by_state}")
    log(f"[큐] 스크린 실행 이력 {persistence['n_runs']}회 "
        f"-> 지속성 축 {'작동' if persistence['discriminating'] else '미작동(1회뿐)'}")

    out = {
        "updated_at": today,
        "latest_run": run_date,
        "source": os.path.basename(broad_path),
        "persistence": persistence,
        "counts": {"total": len(ordered), **by_state},
        "next_to_research": next_to_research(ordered, n=15),
        "entries": {e["ticker"]: e for e in ordered},
        "notes": [
            "우선순위는 합성 점수가 아니라 사전식 정렬이다(검증범위 -> 미분석 "
            "-> 지속 등장 -> Gap). 각 단계가 확인 가능한 사실이다.",
            "상태(IN_BUYLIST/ANALYZED/QUEUED)는 ledger·매수리스트에서 파생한다 - "
            "사람이 유지하는 상태 파일이 아니다.",
            "이 큐는 매수리스트를 바꾸지 않는다. 정식분석에는 사람의 주관적 "
            "입력이 필요하므로(run_analysis가 없으면 실행 거부) 큐는 그 작업의 "
            "**순서**만 정한다.",
        ] + ([note] if note else []),
    }
    os.makedirs(os.path.dirname(queue_path), exist_ok=True)
    with open(queue_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    log(f"[큐] 저장: {queue_path}")
    return out


def main():
    ap = argparse.ArgumentParser(description="연구 우선순위 큐 갱신")
    ap.add_argument("--broad", default=None, help="특정 스크리닝 결과 파일")
    ap.add_argument("--out", default=QUEUE_PATH)
    args = ap.parse_args()
    out = run(broad_path=args.broad, queue_path=args.out)

    nxt = out["next_to_research"]
    if not nxt:
        log("\n다음에 분석할 신규 후보 없음(범위 안 미분석 종목이 없다)")
        return
    log(f"\n=== 다음에 분석할 후보 상위 {len(nxt)} ===")
    for i, e in enumerate(nxt, 1):
        log(f"{i:2}. {e['ticker']:6} [{e.get('tier')}] "
            f"Gap {(e.get('latest_gap') or 0)*100:+6.2f}%p  "
            f"${(e.get('market_cap') or 0)/1e9:7.2f}B  |  {e['priority_reason']}")
    if not out["persistence"]["discriminating"]:
        log("\n⚠️ 스크린 실행이 1회뿐이라 '연속통과' 축은 아직 아무것도 "
            "구분하지 못한다 - 주가 쌓이면 작동한다.")


if __name__ == "__main__":
    main()
