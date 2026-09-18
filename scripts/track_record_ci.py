"""
실전 트랙레코드 주기 측정 - CI 진입점 (2026-09-18 신설).

`engine/track_record.py`를 실행만 한다(새 로직 0줄). 매주 실행돼
`reports/track_record/track_record_<날짜>.json`에 스냅샷을 쌓는다 -
**한 번 재고 끝내면 의미가 없고, 쌓여야 표본이 된다**는 게 이 자동화의
존재 이유다(2026-09-18 1차 측정이 일회성 스크립트였다).

⚠️ `ledger/`에 쓰지 않는다. 측정 결과는 `reports/`에만 남고 Gap·등급·
Confidence 어디에도 되먹임되지 않는다(v3.42 원칙).

⚠️ 결론을 내지 않는다. 표본이 충분해지기 전까지 이 숫자는 방향성
참고용이며, `experiments/`의 사전등록 실험을 대체하지 않는다.
"""
import argparse
import datetime
import json
import os
import sys
import time

sys.path.insert(0, ".")

from engine.track_record import (  # noqa: E402
    PRICE_API, REQUEST_INTERVAL_SEC, build_report, collect_cohort,
    fetch_daily_series, format_report, measure,
)

OUT_DIR = os.path.join("reports", "track_record")
PRICE_SOURCE = "stockanalysis.com 일봉(배당·분할 조정종가, robots.txt 확인됨)"


def log(msg):
    print(msg, flush=True)


def run(as_of, ledger_dir="ledger", sleep_sec=REQUEST_INTERVAL_SEC):
    cohort, skipped = collect_cohort(ledger_dir)
    log(f"코호트 {len(cohort)}종목(price_at_analysis 확보) · "
        f"제외 {len(skipped)}건")

    measured, failures = [], []
    for i, entry in enumerate(cohort, 1):
        series, err = fetch_daily_series(entry["ticker"])
        if err:
            failures.append({**entry, "error": err})
            log(f"[{i}/{len(cohort)}] {entry['ticker']}: 실패 - {err}")
            time.sleep(sleep_sec)
            continue
        row = measure(entry, series)
        measured.append(row)
        if "error" in row:
            log(f"[{i}/{len(cohort)}] {entry['ticker']}: {row['error']}")
        else:
            flag = " ⚠️기록가불일치" if row.get("price_mismatch") else ""
            log(f"[{i}/{len(cohort)}] {entry['ticker']}: "
                f"{row['entry_adj']:.2f} -> {row['latest_adj']:.2f} "
                f"({row['return_pct']:+.2f}%, {row['days_held']}일){flag}")
        time.sleep(sleep_sec)

    return build_report(measured, failures, skipped, as_of, PRICE_SOURCE)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--as-of", default=None, help="YYYY-MM-DD (기본값: 오늘)")
    ap.add_argument("--out-dir", default=OUT_DIR)
    args = ap.parse_args()

    as_of = args.as_of or datetime.date.today().isoformat()
    report = run(as_of)

    os.makedirs(args.out_dir, exist_ok=True)
    path = os.path.join(args.out_dir, f"track_record_{as_of}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    log("")
    log(format_report(report))
    log("")
    log(f"저장: {path}")
    return report


if __name__ == "__main__":
    main()
