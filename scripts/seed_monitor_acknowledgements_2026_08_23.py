"""
monitor/acknowledgements.json 최초 생성 (2026-08-23, v3.64)

손으로 JSON을 쓰지 않고 **2026-08-13 실제 검증 기록**
(`reports/thesis_monitor_2026-08-13.json`)에서 그대로 전사한다 - 그 파일의
`verification.verdict`를 임의로 바꾸지 않는다. 기록된 판정을 나중에 고쳐
쓰는 것은 이 프로젝트가 반복해서 금지해온 사후합리화다.

⚠️ TCOM 2건만 예외적으로 리포트가 아니라 CLAUDE.md에서 근거를 가져온다.
그 2건은 08-13 실행에서 `verification`이 비어 있는데(검증 자체를 안 함),
비어 있는 이유가 CLAUDE.md v3.42 항목에 명시돼 있기 때문이다:

  "실제로 TCOM의 `2024-04-30~2026-01-13`은 증권소송 **집단기간**(과거 서술)
   이라 확인할 이벤트가 아니었다. 첫 실행에서 정확히 이 오탐이 났고..."

즉 "확인 안 함"이 아니라 "확인할 것이 아님이 확인됨"이라 NOT_A_TRIGGER_DATE로
기록한다. 이건 추측이 아니라 문서화된 사실의 전사다.

재실행해도 같은 결과가 나온다(멱등). 기존 파일이 있으면 덮어쓰지 않는다 -
append-only 원칙상 이 스크립트는 '최초 1회 생성' 전용이다.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.monitor_state import STATE_PATH, build_acknowledgement  # noqa: E402

SOURCE_REPORT = "reports/thesis_monitor_2026-08-13.json"
ACK_DATE = "2026-08-13"   # 실제 검증이 수행된 날(오늘이 아니다 - backdate 금지
                          # 원칙의 반대 방향: 실제 수행일을 그대로 쓴다)

# CLAUDE.md v3.42에 문서화된 오탐 2건. 리포트에 verification이 없는 이유가
# 문서에 남아 있어 추측 없이 전사 가능하다.
DOCUMENTED_FALSE_POSITIVES = {
    ("TCOM", "2024-04-30"): (
        "정규식 날짜추출 오탐 - De Wilde v. Trip.com 증권소송의 **집단기간 "
        "시작일**(과거 서술)이지 확인할 트리거 이벤트가 아니다. "
        "CLAUDE.md v3.42 항목에 이 오탐이 명시적으로 기록돼 있다."
    ),
    ("TCOM", "2026-01-13"): (
        "정규식 날짜추출 오탐 - 같은 소송의 집단기간 **종료일**. 위와 동일."
    ),
}


def main():
    if os.path.exists(STATE_PATH):
        print(f"이미 존재: {STATE_PATH} - 덮어쓰지 않는다(append-only). 중단.")
        return 1

    with open(SOURCE_REPORT, encoding="utf-8") as f:
        report = json.load(f)

    acks, skipped = [], []
    for entry in report["falsification_scan"]["past_due"]:
        ticker = entry["ticker"]
        ver = entry.get("verification") or {}
        verdict = ver.get("verdict")
        for d in entry["dates"]:
            tdate = str(d["date"])[:10]
            key = (ticker, tdate)

            if verdict:
                note = ver.get("summary", "").strip()
                action = ver.get("action")
                if action:
                    note += f"\n[조치] {action}"
                acks.append(build_acknowledgement(
                    ticker=ticker, trigger_date=tdate, verdict=verdict,
                    acknowledged_on=ACK_DATE, note=note,
                    evidence_ref=SOURCE_REPORT,
                ))
            elif key in DOCUMENTED_FALSE_POSITIVES:
                acks.append(build_acknowledgement(
                    ticker=ticker, trigger_date=tdate,
                    verdict="NOT_A_TRIGGER_DATE",
                    acknowledged_on=ACK_DATE,
                    note=DOCUMENTED_FALSE_POSITIVES[key],
                    evidence_ref="CLAUDE.md v3.42 (Thesis Monitor 항목)",
                ))
            else:
                # 근거 없는 항목은 만들지 않는다 - 미확인으로 남겨 모니터가
                # 계속 물어보게 하는 쪽이 정직하다.
                skipped.append(f"{ticker}:{tdate}")

    payload = {
        "schema": "irs.monitor.acknowledgements/v1",
        "note": (
            "반증조건 확인 기록. **자동 판정이 아니라 사람이 확인한 결과의 "
            "기록이다.** append-only - 기존 엔트리를 수정하지 말고 새 엔트리를 "
            "덧붙일 것(가장 최근 것이 유효). CI는 이 파일을 읽기만 한다."
        ),
        "seeded_from": SOURCE_REPORT,
        "acknowledgements": acks,
    }
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"생성: {STATE_PATH}  ({len(acks)}건)")
    for a in acks:
        print(f"  {a['ticker']:6} {a['trigger_date']}  {a['verdict']}")
    if skipped:
        print(f"근거 없어 미기록(계속 미확인으로 남음): {skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
