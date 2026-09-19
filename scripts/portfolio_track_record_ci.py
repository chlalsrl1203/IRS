"""
scripts/portfolio_track_record_ci.py — 공식 매수리스트의 가중 트랙레코드를
필요할 때마다(또는 주기적으로) 갱신한다.

`scripts/track_record_ci.py`(종목별 T0 측정)와 같은 재사용 패턴을 그대로
따른다 - 새 가격조회/집계 로직은 없고 `engine.portfolio_track_record`를
호출해 `reports/portfolio_track_record/portfolio_track_record_<날짜>.json`에
스냅샷 하나를 남긴다. 하루에 여러 번 돌려도 같은 날짜 파일을 덮어써
그날의 최신 관측으로 유지한다(ledger의 "같은 날 다른 내용은 거부" 가드와
다르게, 이건 관측 스냅샷이라 재조회 시 갱신이 곧 목적이다).

같은 내용을 `latest.json`으로도 한 벌 더 쓴다 - 대시보드
(`dashboard/portfolio_track_record.html`)가 브라우저에서 직접 읽어가는
**고정 경로**가 필요하기 때문이다. 날짜가 박힌 파일명만 있으면 페이지가
"오늘 날짜를 추측해서" 요청해야 하고, 주말·휴일·CI 실패로 그날 파일이
없으면 조용히 빈 화면이 된다.

⚠️ 이 복사본은 **포인터일 뿐 별도 기록이 아니다** - 같은 실행에서 같은
객체를 두 번 직렬화하므로 내용이 갈릴 수 없고, 갈리지 않는다는 사실 자체를
테스트로 고정했다(`test_latest_json_equals_newest_dated_snapshot`).
v3.32가 실측한 "구 ledger가 안 지워져 33종목이 36건으로 집계되고 그 중복이
통계를 오염시킨" 사고와 성격이 다르다 - 이 디렉터리는 어디에서도 개수를
세지 않는다.
"""
import argparse
import datetime
import json
import os

from engine.portfolio_track_record import (
    LATEST_NAME, OUT_DIR, format_snapshot, load_latest_buylist, snapshot,
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

    # 대시보드가 읽어가는 고정 경로(위 docstring 참고). 같은 객체를 다시
    # 직렬화할 뿐이라 내용이 갈릴 수 없다.
    latest_path = os.path.join(args.out_dir, LATEST_NAME)
    with open(latest_path, "w", encoding="utf-8") as f:
        json.dump(snap, f, ensure_ascii=False, indent=2)

    log("")
    log(format_snapshot(snap))
    log("")
    log(f"저장: {path}")
    log(f"저장: {latest_path} (대시보드 고정 경로)")
    return snap


if __name__ == "__main__":
    main()
