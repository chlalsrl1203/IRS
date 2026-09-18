"""
Thesis 반증조건 체크 자동 준비 (2026-09-18 신설).

## 문제 - "기억해서 열어봐야" 확인되는 상태

`engine/thesis.py`(v3.48)는 `invalidation_conditions`에 `check_by` 날짜를
opt-in으로 남길 수 있지만, 그 날짜가 와도 아무도 자동으로 알려주지 않는다.
v3.42가 이미 겪은 실패(반증조건 트리거 날짜 5건이 전부 지났는데 12일간
아무도 안 열어봄)가 thesis 계층에서 또 반복될 수 있는 구조다.

## 이 모듈이 하는 것과 하지 않는 것

**한다**: check_by 날짜가 지났거나(due) 다가오는(approaching) 조건을 찾아
목록화하고, 그 종목의 ledger가 참조한 연차 대비 SEC에 더 최신 연차 데이터가
있는지("새로 볼 게 생겼다")를 붙인다.

**하지 않는다**: 그 조건이 실제로 발동했는지 판정하지 않는다. 반증조건
문구는 자연어("ARR 성장률이 9%를 밑돌면")라 코드가 그 의미를 이해하고
YES/NO를 낼 수 없고, 설령 낼 수 있어도 v3.42가 확립한 원칙("정규식은 트리거
날짜와 서술적 날짜를 구분 못 한다" - 여기서는 "구조화된 조건 문구도 자동
판정 대상이 아니다"로 확장 적용)을 어기게 된다. `mark_invalidation_
triggered()`는 여전히 사람이 명시적으로 호출해야 한다.

**"기한이 지났다/다가온다"는 날짜 산술이지 반증조건이 실제로 맞았는지
판단이 아니다** - 이 구분이 이 모듈 전체의 존재 이유다.
"""
import datetime
import glob
import json
import os

from engine.thesis import THESIS_DIR

DEFAULT_WARN_WINDOW_DAYS = 30


def _iter_thesis_records(thesis_dir):
    for path in sorted(glob.glob(os.path.join(thesis_dir, "*.json"))):
        with open(path, encoding="utf-8") as f:
            yield path, json.load(f)


def due_conditions(today, thesis_dir=THESIS_DIR,
                    warn_window_days=DEFAULT_WARN_WINDOW_DAYS):
    """
    `check_by`가 있고 아직 `triggered=False`인 조건을 세 갈래로 분류한다:

      due         - check_by <= today (지금 확인할 것)
      approaching - today < check_by <= today+warn_window_days (곧 도래)
      no_date     - check_by가 아예 없음(날짜 무관 상시감시, 여기선 안 다룸)

    순수 날짜 산술 함수라 네트워크가 필요 없고, 어떤 리스트에 들어가든
    반증조건의 참/거짓과는 무관하다.
    """
    if isinstance(today, str):
        today = datetime.date.fromisoformat(today)

    out = {"due": [], "approaching": [], "no_date": []}
    for path, record in _iter_thesis_records(thesis_dir):
        t = record.get("thesis", {})
        for i, c in enumerate(t.get("invalidation_conditions", [])):
            if c.get("triggered"):
                continue
            entry = {
                "ticker": t.get("ticker"),
                "thesis_id": t.get("thesis_id"),
                "thesis_path": path,
                "condition_index": i,
                "condition": c.get("condition"),
                "check_by": c.get("check_by"),
                "linked_ledger": t.get("linked_ledger"),
            }
            check_by = c.get("check_by")
            if check_by is None:
                out["no_date"].append(entry)
                continue
            check_date = datetime.date.fromisoformat(check_by)
            days_until = (check_date - today).days
            entry["days_until_check_by"] = days_until
            if days_until <= 0:
                out["due"].append(entry)
            elif days_until <= warn_window_days:
                out["approaching"].append(entry)
    return out


def _ledger_path_for(entry, ledger_dir):
    linked = entry.get("linked_ledger")
    if linked:
        candidate = os.path.join(ledger_dir, linked)
        if os.path.exists(candidate):
            return candidate
    matches = sorted(glob.glob(os.path.join(ledger_dir, f"{entry['ticker']}_*.json")))
    return matches[-1] if matches else None


def enrich_with_sec_freshness(entries, provider, retrieved_at, ledger_dir="ledger"):
    """
    각 항목에 "연결된 ledger가 쓴 최신 연차 대비 SEC에 더 최신 연차가
    있는가"를 붙인다. **판정하지 않는다** - 새 데이터가 있다는 사실만
    드러내고, 그 데이터를 보고 조건이 발동했는지는 사람이 판단한다.

    provider는 `fetch_annual_financials(entity, retrieved_at=...)`를 갖는
    객체(예: `SecCompanyFactsProvider`) - 테스트에서는 가짜 provider를
    주입해 네트워크 없이 검증한다.
    """
    out = []
    for entry in entries:
        e = dict(entry)
        ledger_path = _ledger_path_for(e, ledger_dir)
        if not ledger_path:
            e["sec_freshness"] = {"status": "LEDGER_NOT_FOUND"}
            out.append(e)
            continue
        with open(ledger_path, encoding="utf-8") as f:
            ledger = json.load(f)
        rev_by_year = ledger.get("inputs", {}).get("revenue_by_year") or {}
        if not rev_by_year:
            e["sec_freshness"] = {"status": "LEDGER_HAS_NO_REVENUE_SERIES"}
            out.append(e)
            continue
        ledger_latest_fy = max(int(y) for y in rev_by_year)

        try:
            res = provider.fetch_annual_financials(
                e["ticker"], metrics=("revenue",), retrieved_at=retrieved_at)
        except Exception as exc:  # noqa: BLE001 - 조회 실패도 사실이다(v3.68)
            e["sec_freshness"] = {
                "status": "SEC_FETCH_FAILED",
                "error": f"{type(exc).__name__}: {exc}",
            }
            out.append(e)
            continue

        sec_years = {int(fact.fiscal_year) for fact in res.facts
                     if fact.metric == "revenue"}
        if not sec_years:
            e["sec_freshness"] = {"status": "SEC_REVENUE_MISSING"}
            out.append(e)
            continue

        sec_latest_fy = max(sec_years)
        e["sec_freshness"] = {
            "status": "OK",
            "ledger_latest_fy": ledger_latest_fy,
            "sec_latest_fy": sec_latest_fy,
            "new_annual_available": sec_latest_fy > ledger_latest_fy,
        }
        out.append(e)
    return out


def format_checkpoint_report(due, approaching):
    """사람이 읽는 요약 - '확인할 것'과 '곧 온다'를 분리해서 보여준다."""
    lines = []
    if not due and not approaching:
        lines.append("확인이 필요한 thesis 반증조건 없음(check_by 도래분 0건).")
        return "\n".join(lines)

    if due:
        lines.append(f"🚨 지금 확인할 것 ({len(due)}건)")
        for e in due:
            fresh = e.get("sec_freshness", {})
            note = ""
            if fresh.get("status") == "OK" and fresh.get("new_annual_available"):
                note = (f" - SEC에 FY{fresh['sec_latest_fy']} 신규 확보됨"
                        f"(ledger는 FY{fresh['ledger_latest_fy']}까지)")
            elif fresh.get("status") == "OK":
                note = " - SEC 연차 데이터는 아직 ledger와 동일(신규 없음)"
            elif fresh.get("status"):
                note = f" - SEC 조회 상태: {fresh['status']}"
            days_late = -e.get("days_until_check_by", 0)
            lines.append(f"  {e['ticker']} (기한 {e['check_by']}, {days_late}일 경과)"
                         f"{note}")
            lines.append(f"    조건: {e['condition']}")
    if approaching:
        lines.append(f"\n📅 곧 도래 ({len(approaching)}건)")
        for e in approaching:
            lines.append(f"  {e['ticker']} - {e['check_by']}까지 "
                         f"{e['days_until_check_by']}일")
    return "\n".join(lines)
