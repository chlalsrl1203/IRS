"""
Thesis 반증조건 체크 자동 준비 - CLI 진입점 (2026-09-18).

`engine/thesis_checkpoints.py`(신규)를 실행만 한다 - 새 로직 0줄. check_by
날짜가 지났거나 곧 다가오는 반증조건을 찾아 SEC에 새 연차 데이터가 있는지
붙여서 보여준다. **아무것도 자동 판정하지 않는다** - 조건이 실제로
발동했는지는 이 리포트를 읽은 사람이 `mark_invalidation_triggered()`로
직접 표시해야 한다.

daily_brief.py에는 아직 배선하지 않았다 - 공유 자동화 표면을 건드리는
결정이라 사용자 확인 없이 넣지 않는다(이번 신설은 독립 실행 스크립트로만
둔다).
"""
import argparse
import datetime
import json
import os
import sys

sys.path.insert(0, ".")

from engine.data.providers.sec import SecCompanyFactsProvider
from engine.thesis_checkpoints import (
    due_conditions, enrich_with_sec_freshness, format_checkpoint_report,
)

REPORTS_DIR = "reports"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--today", default=None,
                    help="YYYY-MM-DD (기본값: 오늘). 재현/테스트용.")
    ap.add_argument("--warn-window-days", type=int, default=30)
    args = ap.parse_args()

    today = args.today or datetime.date.today().isoformat()

    out = due_conditions(today, warn_window_days=args.warn_window_days)

    if out["due"] or out["approaching"]:
        provider = SecCompanyFactsProvider()
        out["due"] = enrich_with_sec_freshness(out["due"], provider,
                                               retrieved_at=today)
        out["approaching"] = enrich_with_sec_freshness(out["approaching"],
                                                        provider,
                                                        retrieved_at=today)

    print(format_checkpoint_report(out["due"], out["approaching"]))

    if out["no_date"]:
        print(f"\n(날짜 없는 상시감시 조건 {len(out['no_date'])}건은 "
              f"이 리포트가 다루지 않음 - daily_monitor_ci.py가 별도로 "
              f"ledger의 falsification_conditions 텍스트를 감시한다)")

    os.makedirs(REPORTS_DIR, exist_ok=True)
    path = os.path.join(REPORTS_DIR, f"thesis_checkpoints_{today}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"\n저장: {path}")


if __name__ == "__main__":
    main()
