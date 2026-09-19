"""
scripts/portfolio_track_record_ci.py — 공식 매수리스트의 가중 트랙레코드를
필요할 때마다(또는 주기적으로) 갱신한다.

`scripts/track_record_ci.py`(종목별 T0 측정)와 같은 재사용 패턴을 그대로
따른다 - 새 가격조회/집계 로직은 없고 `engine.portfolio_track_record`를
호출해 `reports/portfolio_track_record/portfolio_track_record_<날짜>.json`에
스냅샷 하나를 남긴다. 하루에 여러 번 돌려도 같은 날짜 파일을 덮어써
그날의 최신 관측으로 유지한다(ledger의 "같은 날 다른 내용은 거부" 가드와
다르게, 이건 관측 스냅샷이라 재조회 시 갱신이 곧 목적이다).
"""
import argparse
import datetime
import json
import os

from engine.portfolio_track_record import (
    OUT_DIR, format_snapshot, load_latest_buylist, snapshot,
)


def log(msg):
    print(msg, flush=True)


def run(as_of=None):
    buylist = load_latest_buylist()
    if buylist is None:
        log("공식 매수리스트(reports/buylist_<날짜>.json)를 찾지 못했다.")
        return None
    log(f"매수리스트: {buylist['_source_path']} "
        f"(발행일 {buylist['generated_at']}, {len(buylist['positions'])}종목)")
    return snapshot(buylist, as_of=as_of)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--as-of", default=None, help="YYYY-MM-DD (기본값: 오늘)")
    ap.add_argument("--out-dir", default=OUT_DIR)
    args = ap.parse_args()

    as_of = args.as_of or datetime.date.today().isoformat()
    snap = run(as_of)
    if snap is None:
        return None

    os.makedirs(args.out_dir, exist_ok=True)
    path = os.path.join(args.out_dir, f"portfolio_track_record_{as_of}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(snap, f, ensure_ascii=False, indent=2)

    log("")
    log(format_snapshot(snap))
    log("")
    log(f"저장: {path}")
    return snap


if __name__ == "__main__":
    main()
