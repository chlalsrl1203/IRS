"""
watchlist_ci.py (v3.69, 2026-08-24) — 정해둔 관심종목을 IRS 엔진으로 자동 추적한다.

## 스크리너와 무엇이 다른가

`daily_screen_ci.py`는 **발굴**이다 - Finviz가 매일 새로 뱉는 후보를 1차 필터링한다.
이 스크립트는 **감시**다 - `watchlist.json`에 사람이 정해둔 목록만 본다. 둘은
목적도 모집단도 다르므로 섞지 않는다.

## 세 갈래 중 무엇을 자동화하는가

| 대상 | 함수 | 자동화 |
|---|---|---|
| ledger 있는 종목 → 시총만 갱신, Gap 부식 추적 | `recompute_gap_at_market_cap` (v3.42) | 한다 |
| ledger 없는 종목 → SEC 원자료 전면 재계산 | `deep_screen` (v3.65) | 한다 |
| **공식 판정(ledger 생성)** | `run_analysis` | **하지 않는다** |

세 번째를 자동화하지 않는 이유는 성능이 아니라 설계다. `run_analysis()`는
`model_choice_reason`·`subjective_input_basis`(경쟁강도·수요민감도) 없이는 실행을
거부하도록 만들어져 있고(v3.19), 자동 파이프라인이 그 자리를 채우면 그게 정확히
"빈칸 채우기"(추측을 근거로 위장)다. 2026-08-16 모델선택 연구는 그 선택을 규칙으로
만드는 것을 **REJECT**했다 - 교과서 기준이 실제 선택을 전혀 분리하지 못했기 때문이다.

## 절대 하지 않는 것

**`ledger/`에 쓰지 않는다.** `recompute_gap_at_market_cap`은 오늘 날짜로 스탬프된
완전한 결과를 만들지만, 그걸 저장하면 같은 티커 ledger가 2개가 되어 "종목당 1건"
규칙이 즉시 깨진다(v3.32 WM/WCN/IDXX 중복이 CLAUDE.md 통계까지 오염시킨 사고와
동일 유형). 결과는 `reports/watchlist/`에만 남는다 - 공식 판정이 아니라 모니터링
신호다("병기, 자동판정 안 함").

## 시가총액 예산 - 이 파이프라인의 유일한 실제 제약

Alpha Vantage 무료 한도가 25회/일인데 스크리너가 최대 20회를 잡아둔다. 그런데
**실측상 스크리너는 하루 1~3회밖에 안 쓴다**(SEC가 후보의 약 88%를 FCF-DCF 적용
불가로 걸러내기 때문 - 2026-08-24 실측: Finviz 39 → 정크필터 25 → SEC 성공 3).
그래서 남는 몫을 관심종목이 쓴다. 그래도 34종목을 하루에 다 볼 수는 없으므로
**날짜 기반 결정적 회전**으로 나눠 본다(상태 파일 없이 재현 가능 - day-of-year를
쓰므로 같은 날 재실행하면 같은 종목이 나온다).
"""
import datetime
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts import daily_screen as ds
from scripts import daily_screen_ci as ci

WATCHLIST_PATH = os.environ.get("IRS_WATCHLIST", "watchlist.json")
WATCHLIST_DIR = os.path.join("reports", "watchlist")
LEDGER_DIR = "ledger"

# 하루에 볼 관심종목 수. 스크리너가 실측상 1~3회만 쓰므로 그 나머지를 쓴다.
# 34종목이면 이 값으로 2일이면 한 바퀴 돈다.
DEFAULT_DAILY_BUDGET = 18

# Gap이 이만큼 이상 움직이면 리포트에서 강조한다. ±5%p 판정밴드의 절반 -
# 밴드를 넘지 않아도 "절반을 잠식했다"는 사실 자체가 볼 가치가 있다는 뜻이고,
# 검증된 임계값이 아니라 관측용 시작점이다.
NOTABLE_GAP_MOVE = 0.025


def log(msg):
    print(msg, flush=True)


def load_watchlist(path=WATCHLIST_PATH):
    with open(path, encoding="utf-8") as f:
        doc = json.load(f)
    tickers = [t.strip().upper() for t in doc.get("tickers", []) if t and t.strip()]
    # 중복 제거하되 순서는 보존한다(회전이 결정적이어야 하므로).
    seen, out = set(), []
    for t in tickers:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out


def latest_ledger_for(ticker, ledger_dir=LEDGER_DIR):
    """티커의 최신 ledger. 없으면 None(= deep_screen 경로로 간다)."""
    import glob

    paths = sorted(glob.glob(os.path.join(ledger_dir, f"{ticker}_*.json")))
    if not paths:
        return None
    with open(paths[-1], encoding="utf-8") as f:
        return json.load(f)


def rotate(tickers, today, budget):
    """
    날짜 기반 결정적 회전 - 상태 파일 없이 모든 종목이 고정 주기로 돌아온다.

    상태 파일을 쓰지 않는 이유: 커밋 타이밍이나 실행 실패에 따라 상태가 어긋나면
    어떤 종목이 조용히 영영 안 뽑힐 수 있다. day-of-year만 쓰면 그런 표류가
    구조적으로 불가능하고, 같은 날 재실행 시 같은 결과가 나와 검증도 쉽다.
    """
    if not tickers or budget <= 0:
        return []
    n = len(tickers)
    if budget >= n:
        return list(tickers)
    start = (today.timetuple().tm_yday * budget) % n
    return [tickers[(start + i) % n] for i in range(budget)]


def track_existing(ticker, ledger, market_cap):
    """ledger 있는 종목: 시총만 갱신해 Gap 부식을 본다(펀더멘털 전부 고정)."""
    from engine.thesis_monitor import recompute_gap_at_market_cap

    row = recompute_gap_at_market_cap(ledger, market_cap)
    row["mode"] = "gap_decay"

    # 시가총액은 성장추정에 영향을 주면 안 된다. 어긋나면 계산 경로 버그다 -
    # 조용히 넘기지 않고 드러낸다(이 프로젝트가 반복 확인해온 자기일치 검증).
    rg_then = row["realistic_growth_then"]
    rg_now = row["realistic_growth_now"]
    if abs(rg_then - rg_now) > 1e-12:
        row["integrity_error"] = (
            f"Realistic Growth가 시총 변경만으로 움직였다({rg_then} -> {rg_now}) - "
            f"계산 경로 버그")
    return row


def analyze_new(ticker, today, market_cap):
    """ledger 없는 종목: SEC 원자료로 전면 재계산(공식 ledger는 만들지 않는다)."""
    from engine.deep_screen import deep_screen

    series, limitations = ds.fetch_deep_series(ticker, today)
    if series is None:
        return {"ticker": ticker, "mode": "deep_screen",
                "error": (limitations or ["원인 미상"])[0]}

    r = deep_screen(ticker, series, market_cap)
    return {
        "ticker": ticker,
        "mode": "deep_screen",
        "market_cap_now": market_cap,
        "gap_now": r.expectation_gap,
        "judgment_now": r.judgment,
        "realistic_growth_now": r.realistic_growth,
        "implied_growth_now": r.implied_growth,
        "drs": r.drs,
        "assumed_inputs": r.assumed_inputs,
        "data_limitations": r.data_limitations,
    }


def prior_snapshot(ticker, today, out_dir=WATCHLIST_DIR):
    """가장 최근(오늘 제외) 스냅샷 - 전일 대비 변화를 보기 위함."""
    import glob

    paths = sorted(glob.glob(os.path.join(out_dir, f"{ticker}_*.json")))
    paths = [p for p in paths if not p.endswith(f"{ticker}_{today}.json")]
    if not paths:
        return None
    with open(paths[-1], encoding="utf-8") as f:
        return json.load(f)


def run_watchlist(tickers, today, av_key, budget, out_dir=WATCHLIST_DIR):
    import time

    os.makedirs(out_dir, exist_ok=True)
    picked = rotate(tickers, datetime.date.fromisoformat(today), budget)
    log(f"[관심종목] 전체 {len(tickers)}종목 중 오늘 {len(picked)}종목 회전 선택: "
        f"{', '.join(picked)}")

    rows, calls = [], 0
    for t in picked:
        ledger = latest_ledger_for(t)
        try:
            mc = ci.fetch_market_cap_av(t, av_key)
            calls += 1
            time.sleep(ci.AV_CALL_INTERVAL_SEC)
        except Exception as e:  # noqa: BLE001 - 한 종목 실패가 전체를 막으면 안 됨
            rows.append({"ticker": t, "mode": "skipped",
                         "error": f"시가총액 조회 실패: {type(e).__name__}"})
            continue
        if mc is None or mc <= 0:
            rows.append({"ticker": t, "mode": "skipped",
                         "error": "시가총액 미확보(AV 응답 없음 또는 한도 소진)"})
            continue

        try:
            row = (track_existing(t, ledger, mc) if ledger
                   else analyze_new(t, today, mc))
        except Exception as e:  # noqa: BLE001
            rows.append({"ticker": t, "mode": "error",
                         "error": f"{type(e).__name__}: {str(e)[:150]}"})
            continue

        prior = prior_snapshot(t, today, out_dir)
        if prior and prior.get("gap_now") is not None and row.get("gap_now") is not None:
            row["change_vs_prior"] = {
                "prior_date": prior.get("date"),
                "gap_prior": prior["gap_now"],
                "gap_move_pp": row["gap_now"] - prior["gap_now"],
                "judgment_changed": prior.get("judgment_now") != row.get("judgment_now"),
            }

        row["date"] = today
        rows.append(row)
        with open(os.path.join(out_dir, f"{t}_{today}.json"), "w",
                  encoding="utf-8") as f:
            json.dump(row, f, ensure_ascii=False, indent=2)

    log(f"[관심종목] AV {calls}회 호출, {len([r for r in rows if 'error' not in r])}종목 처리")
    return rows


def format_watchlist_section(rows, total_tickers):
    if not rows:
        return ""
    ok = [r for r in rows if "error" not in r]
    failed = [r for r in rows if "error" in r]

    lines = ["", "---", "",
             f"### 📋 관심종목 추적 ({len(ok)}/{total_tickers}종목, 회전)"]

    flipped = [r for r in ok if r.get("judgment_flipped")]
    integrity = [r for r in ok if r.get("integrity_error")]
    moved = [r for r in ok
             if abs((r.get("change_vs_prior") or {}).get("gap_move_pp") or 0)
             >= NOTABLE_GAP_MOVE]

    if integrity:
        lines.append(f"🛑 **계산 무결성 오류 {len(integrity)}종목** — "
                     + ", ".join(f"{r['ticker']}: {r['integrity_error']}"
                                 for r in integrity))
    if flipped:
        lines.append("⚠️ **시총 변동만으로 판정이 바뀐 종목** — " + ", ".join(
            f"{r['ticker']}({r['judgment_then']}→{r['judgment_now']})"
            for r in flipped))
    if moved:
        lines.append(f"📈 전일 대비 Gap {NOTABLE_GAP_MOVE*100:.1f}%p 이상 이동 — "
                     + ", ".join(
                         f"{r['ticker']} {r['change_vs_prior']['gap_move_pp']*100:+.2f}%p"
                         for r in moved))
    if not (integrity or flipped or moved):
        lines.append("판정 변화·주목할 Gap 이동 없음.")

    lines.append("")
    lines.append("<details><summary>종목별 상세</summary>")
    lines.append("")
    lines.append("| 종목 | 모드 | Gap | 판정 | 시총 변동 |")
    lines.append("|---|---|---|---|---|")
    for r in sorted(ok, key=lambda x: x["ticker"]):
        mc_chg = r.get("market_cap_change_pct")
        lines.append(
            f"| {r['ticker']} | {'부식추적' if r['mode']=='gap_decay' else '심층재계산'} "
            f"| {r['gap_now']*100:+.2f}%p | {r.get('judgment_now','-')} "
            f"| {f'{mc_chg*100:+.1f}%' if mc_chg is not None else '-'} |")
    if failed:
        lines.append("")
        lines.append("제외: " + ", ".join(
            f"{r['ticker']}({r['error'][:40]})" for r in failed))
    lines.append("")
    lines.append("</details>")
    lines.append("")
    lines.append("<sub>⚠️ 공식 판정이 아니다 — `ledger/`는 변경되지 않는다. "
                 "부식추적은 시총만 갱신한 값이고, 심층재계산은 경쟁강도·수요민감도를 "
                 "corpus 중앙값으로 고정한 추정치다.</sub>")
    return "\n".join(lines)


def main():
    today = os.environ.get("IRS_TODAY") or datetime.date.today().isoformat()
    av_key = os.environ.get("ALPHA_VANTAGE_API_KEY")
    budget = int(os.environ.get("IRS_WATCHLIST_BUDGET", DEFAULT_DAILY_BUDGET))

    log(f"=== IRS 관심종목 추적 {today} ===")
    if not av_key:
        log("[관심종목] ALPHA_VANTAGE_API_KEY 미설정 - 시가총액을 못 받아 중단한다.")
        return

    tickers = load_watchlist()
    if not tickers:
        log(f"[관심종목] {WATCHLIST_PATH}에 티커가 없다 - 할 일 없음.")
        return

    rows = run_watchlist(tickers, today, av_key, budget)

    out_path = f"/tmp/watchlist_ci_{today}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"date": today, "n_watchlist": len(tickers), "rows": rows},
                  f, ensure_ascii=False, indent=2)
    log(f"-> {out_path}")

    if "--post" in sys.argv:
        import issue_reporting as IR

        # 관심종목 추적도 그날 이슈에 붙는다(하루 알림 1건 유지). 긴급도는
        # 올리지 않는다 - 여기서 나오는 Gap 부식은 반증조건 감시와 **함께**
        # 봐야 의미가 있고(주가가 빠지면 Gap은 반드시 벌어진다, v3.42 가치함정),
        # 단독으로 긴급 신호를 만들면 정확히 그 오독을 제목에 박게 된다.
        IR.report("daily", today,
                  f"## {today} 관심종목 추적\n"
                  + format_watchlist_section(rows, len(tickers)),
                  urgency_key="routine", log=log)


if __name__ == "__main__":
    main()
