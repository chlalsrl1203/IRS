"""
Monitor Acknowledgement State (v3.64 신규, 2026-08-23)

왜 만들었나 - 자동화 직전에 발견한 구조적 결함:

`thesis_monitor.scan_falsification_conditions()`는 2026-08-13에 **단 한 번**
수동 실행됐고, 그때 past_due 6건을 전부 실제로 검증했다(TTD 반증 확정 등,
`reports/thesis_monitor_2026-08-13.json`). 그런데 10일이 지난 2026-08-23에
같은 스캔을 다시 돌리면 **똑같은 6건이 그대로 다시 나온다.** 검증했다는
사실이 어디에도 기록되지 않기 때문이다.

이 상태로 매일 자동 실행하면 결과는 개선이 아니라 악화다 - 매일 같은 6건이
알림으로 오고, 사람은 며칠 만에 그 알림을 무시하게 되며, 그러면 **진짜 신규
항목이 묻힌다.** 이 프로젝트가 v3.42에서 이미 겪은 실패("반증조건 트리거
날짜 5건이 전부 기한이 지났는데 12일간 아무도 열어보지 않았다")가 알림
피로라는 다른 경로로 재발하는 것이다.

그래서 자동화의 전제조건은 "매일 돌리기"가 아니라 **"확인된 것을 확인됐다고
기록할 곳"**이다.

## 설계 원칙 (전부 기존 IRS 원칙의 재적용)

1. **자동 판정 안 함** - 이 모듈은 반증조건이 발동했는지 **판정하지 않는다.**
   v3.42가 확립한 대로 정규식은 트리거 날짜와 서술적 날짜를 구분하지 못하며
   (TCOM의 소송 집단기간 2024-04-30이 실제 오탐 사례), 발동 여부는 실적을
   읽어야만 알 수 있다. 이 모듈이 하는 일은 오직 **"사람이 확인했는가"**를
   추적하는 것뿐이다.

2. **확인은 사람의 행위** - CI는 이 파일을 **읽기만** 한다. 쓰기는 저녁
   검토 세션에서 사람(또는 사람이 지시한 Claude)이 한다. CI에 쓰기 권한을
   주지 않으므로 자동 커밋 사고가 원천적으로 불가능하다.

3. **append-only** - 기존 항목을 수정하지 않는다. 같은 항목을 다시 확인하면
   새 엔트리를 덧붙인다(가장 최근 것이 유효). prediction_ledger·
   experiment_registry와 동일 원칙.

4. **"확인 못함"은 닫힌 상태가 아니다** - INCONCLUSIVE는 재부상한다.
   2026-08-13 실측에서 MNDY가 정확히 이 경우였다(조건이 지정한 코호트별 NDR을
   회사가 공개하지 않아 판정 불가). 이걸 '확인 완료'로 닫으면 영영 안 돌아온다
   - 이 프로젝트의 "데이터 없음을 유리한 값으로 오독하지 않는다" 원칙
   (is_insurer·sbc_cross_check·holdings_overlap과 동일)의 시간축 버전이다.
"""

import json
import os
from datetime import date, timedelta

# ──────────────────────────────────────────────────────────────────────
# 확인 결과 어휘
# ──────────────────────────────────────────────────────────────────────
# ⚠️ 이 어휘는 "조건이 발동했는가"가 아니라 "사람이 확인했는가"를 기록한다.
# TRIGGERED조차 이 모듈이 판정한 게 아니라 사람이 확인해 적어 넣은 것이다.
VERDICTS = {
    # 닫힌 상태 - 다시 떠오르지 않는다
    "TRIGGERED": "조건이 실제로 발동함(사람이 확인) - 별도 재검토 절차로 넘어감",
    "NOT_TRIGGERED": "확인했고 발동하지 않음",
    "NOT_A_TRIGGER_DATE": (
        "날짜 추출 오탐 - 트리거가 아니라 서술적 날짜였음"
        "(예: 증권소송 집단기간). 영구히 닫힘"
    ),
    # 열린 상태 - 재부상한다
    "INCONCLUSIVE": (
        "확인을 시도했으나 필요한 데이터가 공개되지 않아 판정 불가. "
        "**닫힌 게 아니다** - recheck_after 이후 다시 떠오른다"
    ),
}
CLOSED_VERDICTS = frozenset({"TRIGGERED", "NOT_TRIGGERED", "NOT_A_TRIGGER_DATE"})
OPEN_VERDICTS = frozenset({"INCONCLUSIVE"})

# INCONCLUSIVE 항목이 다시 떠오르기까지의 기본 간격.
# ⚠️ 검증된 값이 아니다 - 분기 실적 주기(약 90일)보다 짧게 잡아 "다음 분기에는
# 확인 가능해졌는지" 물어보게 하는 시작점일 뿐이다. 항목별로 recheck_after를
# 명시하면 그쪽이 우선한다.
DEFAULT_RECHECK_DAYS = 30

STATE_PATH = os.path.join("monitor", "acknowledgements.json")


def item_key(ticker: str, trigger_date) -> str:
    """
    확인 항목의 안정적 식별자.

    (종목, 트리거날짜) 쌍으로 잡는다 - 반증조건 원문은 재분석 때 바뀔 수
    있지만 "이 종목의 이 날짜 항목"은 안 바뀌기 때문이다. 원문 해시로 잡으면
    오탈자 하나만 고쳐도 확인 기록이 통째로 유실된다.
    """
    return f"{ticker}:{str(trigger_date)[:10]}"


def load_acknowledgements(path: str = STATE_PATH) -> dict:
    """
    확인 기록을 읽어 {item_key: [엔트리...]} 로 반환한다.

    파일이 없으면 **조용히 빈 dict를 주되 그 사실을 숨기지 않는다** - 호출측이
    "확인 기록 없음"과 "전부 미확인"을 구분할 수 있어야 한다(반환값의
    `_missing` 키로 표시).
    """
    if not os.path.exists(path):
        return {"_missing": True, "entries": {}}
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    entries = {}
    for e in raw.get("acknowledgements", []):
        key = e.get("item_key") or item_key(e["ticker"], e["trigger_date"])
        entries.setdefault(key, []).append(e)
    for key in entries:
        entries[key].sort(key=lambda x: x.get("acknowledged_on", ""))
    return {"_missing": False, "entries": entries}


def latest_verdict(acks: dict, key: str):
    """해당 항목의 가장 최근 확인 엔트리(없으면 None)."""
    lst = (acks.get("entries") or {}).get(key)
    return lst[-1] if lst else None


def is_open(entry: dict, today: date) -> bool:
    """
    이 확인 엔트리가 아직 '열려 있는가'(=다시 떠올라야 하는가).

    - 닫힌 verdict(TRIGGERED/NOT_TRIGGERED/NOT_A_TRIGGER_DATE) -> False
    - INCONCLUSIVE -> recheck_after(없으면 확인일+DEFAULT_RECHECK_DAYS)가
      지났으면 True
    - 모르는 verdict -> **True**(안전한 쪽). 어휘가 늘어났는데 이 함수를
      안 고치면 조용히 닫히는 것보다 시끄럽게 열려 있는 게 낫다.
    """
    verdict = entry.get("verdict")
    if verdict in CLOSED_VERDICTS:
        return False
    if verdict in OPEN_VERDICTS:
        recheck = entry.get("recheck_after")
        if recheck:
            return date.fromisoformat(str(recheck)[:10]) <= today
        ack_on = entry.get("acknowledged_on")
        if not ack_on:
            return True
        due = date.fromisoformat(str(ack_on)[:10]) + timedelta(
            days=DEFAULT_RECHECK_DAYS)
        return due <= today
    return True


def triage(scan_results: list, acks: dict, today: date) -> dict:
    """
    thesis_monitor.scan_falsification_conditions() 결과 목록을 확인 기록과
    대조해 **오늘 사람이 봐야 할 것만** 골라낸다.

    scan_results: scan_falsification_conditions()가 반환한 dict의 리스트
    반환:
      needs_review   - 미확인이거나 재부상한 항목(=알림 대상)
      acknowledged   - 확인 완료로 닫힌 항목(조용히 통과)
      triggered      - 사람이 TRIGGERED로 확인해둔 항목(계속 눈에 보이게)
      pending_future - 아직 기한 미도래
      undated        - 날짜 없는 사건기반 조건
      no_conditions  - 반증조건 자체가 없음

    ⚠️ `no_conditions`를 '안전'으로 읽지 말 것 - 반증조건을 소급 작성하지
    않는다는 원칙(v3.24) 때문에 과거 분석에는 원래 비어 있다. '감시 대상이
    아니다'가 아니라 '감시할 근거가 기록돼 있지 않다'는 뜻이다.
    """
    out = {
        "needs_review": [], "acknowledged": [], "triggered": [],
        "pending_future": [], "undated": [], "no_conditions": [],
        "state_file_missing": bool(acks.get("_missing")),
    }
    for r in scan_results:
        status = r.get("status")
        ticker = r.get("ticker")
        if status == "no_conditions":
            out["no_conditions"].append(ticker)
            continue
        if status == "undated":
            out["undated"].append(
                {"ticker": ticker, "conditions_text": r.get("conditions_text", "")})
            continue
        for d in r.get("pending", []):
            out["pending_future"].append(
                {"ticker": ticker, "trigger_date": str(d["date"])})
        for d in r.get("past_due", []):
            key = item_key(ticker, d["date"])
            entry = latest_verdict(acks, key)
            row = {
                "ticker": ticker,
                "trigger_date": str(d["date"]),
                "item_key": key,
                "days_past": (today - d["date"]).days,
                "context": d.get("context", ""),
                "analyzed_at": r.get("analyzed_at"),
            }
            if entry is None:
                row["reason"] = "미확인 - 한 번도 검토된 적 없음"
                out["needs_review"].append(row)
                continue
            row["last_verdict"] = entry.get("verdict")
            row["last_acknowledged_on"] = entry.get("acknowledged_on")
            row["last_note"] = entry.get("note", "")
            if entry.get("verdict") == "TRIGGERED":
                out["triggered"].append(row)
            elif is_open(entry, today):
                row["reason"] = (
                    f"재부상 - {entry.get('verdict')}로 기록됐으나 아직 닫히지 "
                    f"않은 상태(확인일 {entry.get('acknowledged_on')})")
                out["needs_review"].append(row)
            else:
                out["acknowledged"].append(row)
    out["needs_review"].sort(key=lambda x: (-x["days_past"], x["ticker"]))
    return out


def build_acknowledgement(ticker: str, trigger_date, verdict: str,
                          acknowledged_on: str, note: str,
                          evidence_ref: str = None,
                          recheck_after: str = None) -> dict:
    """
    확인 엔트리 1건을 만든다(저장은 호출측 몫 - append-only 파일에 덧붙일 것).

    note는 **필수**다. 근거 없는 확인은 확인이 아니다 - `model_choice_reason`·
    `subjective_input_basis`가 확립한 "근거 없으면 거부" 패턴 그대로다.
    """
    if verdict not in VERDICTS:
        raise ValueError(
            f"알 수 없는 verdict: {verdict!r} (허용: {sorted(VERDICTS)})")
    if not note or not note.strip():
        raise ValueError(
            f"{ticker} {trigger_date}: note는 필수 - 무엇을 보고 그렇게 "
            f"판단했는지 없으면 나중에 재현할 수 없다")
    if verdict == "INCONCLUSIVE" and not note.strip():
        raise ValueError("INCONCLUSIVE는 무엇이 없어서 판정 못했는지 적을 것")
    entry = {
        "item_key": item_key(ticker, trigger_date),
        "ticker": ticker,
        "trigger_date": str(trigger_date)[:10],
        "verdict": verdict,
        "acknowledged_on": str(acknowledged_on)[:10],
        "note": note.strip(),
    }
    if evidence_ref:
        entry["evidence_ref"] = evidence_ref
    if recheck_after:
        entry["recheck_after"] = str(recheck_after)[:10]
    return entry
