"""
나쁜 소식의 자발적 선제 공시 — 비정기 가이던스 하향 탐지 (v4.01, 2026-10-10)

`acc.voluntary_bad_news`("나쁜 소식을 먼저 자발적으로 공시한 이력이 있는가?")는 19종목 중 14개가
비어 있던, QSI에서 가장 빈 칸이다. 이를 직접 다루는 오픈소스는 찾지 못했다(2026-10-09 조사).
대신 이미 있는 두 경로 — 제출 목록(`sec_events`)과 가이던스 추출(`guidance_ledger`, v3.96) —
만으로 **좁고 확인 가능한 한 가지 사건**을 잡는다.

## 사전 고정 규칙 (수집 전 고정, 결과를 보고 바꾸지 않는다)

- **정기 실적 발표** = 각 정기보고서(10-Q·10-K) 제출일 기준 직전 45일 안에 나온 Item 2.02 8-K 중
  **가장 늦은 것** 하나. 그 밖의 2.02·7.01·8.01 보도자료는 **비정기**다.
- **가이던스 하향** = 같은 회계연도 연간 총매출 가이던스의 중간값이 **직전 제시보다 1% 넘게** 낮아진 것
  (`guidance_ledger.extract_annual_revenue_guidance` 그대로 — 새 추출 로직 없음).
- 비정기 보도자료에서 하향이 1건 이상 → **True**(회사가 정기 일정을 기다리지 않고 나쁜 소식을 먼저 냈다).
- 그 밖에는 전부 **unknown**:
  - 하향이 정기 발표에서만 있었다 → 선제 공시할 만한 사건이었는지 판단할 수 없다.
  - 하향이 없었다 → 나쁜 소식이 없었을 수 있다. "선제 공시 이력 없음(False)"으로 쓰면 나쁜 소식이 없던
    회사를 정직성에서 깎는 꼴이 된다.
  ⚠️ 그래서 이 규칙은 **True만 단언한다**(`cap.dividend_predictable`과 같은 구조).
- 외국 발행사(6-K)는 정기/비정기를 구분할 Item 번호가 없어 다루지 않는다.

## 하지 않는 것

가이던스가 없는 실적 사전경고(분기 실적이 기대 이하라는 문장만 있는 경우)는 방향을 기계적으로 읽을 수
없어 잡지 않는다 — 놓치는 사례가 있다는 뜻이고, 그 사실을 unknown 사유에 적는다. 판정·점수 없음.
"""

import datetime

VALIDATION_STATUS = "IMPLEMENTED_NOT_VALIDATED"
SCHEDULED_WINDOW_DAYS = 45
CUT_THRESHOLD = 0.01


def _d(s):
    return datetime.date.fromisoformat(s)


def scheduled_releases(release_dates_202, periodic_dates, window=SCHEDULED_WINDOW_DAYS) -> set:
    """정기보고서마다 직전 window일 안의 가장 늦은 2.02 하나를 정기 발표로 본다."""
    rel = sorted(set(release_dates_202))
    out = set()
    for p in periodic_dates:
        cands = [r for r in rel if _d(p) - datetime.timedelta(days=window) <= _d(r) <= _d(p)]
        if cands:
            out.add(cands[-1])
    return out


def _mid(g):
    return (g["low"] + g["high"]) / 2


def guidance_cuts(releases: list) -> list:
    """releases: [{filed, accession, url, items, scheduled, guidance: [...]}] (시간순 무관).

    같은 FY의 직전 제시 대비 중간값이 CUT_THRESHOLD 넘게 낮아진 제시를 돌려준다.
    같은 날 여러 문서가 같은 FY를 제시하면 하나로 본다(먼저 읽힌 것).
    """
    seq = {}
    for rel in sorted(releases, key=lambda r: (r["filed"], r.get("accession") or "")):
        for g in rel["guidance"]:
            hist = seq.setdefault(g["fy"], [])
            if hist and hist[-1]["filed"] == rel["filed"]:
                continue
            hist.append(dict(g, filed=rel["filed"], accession=rel.get("accession"),
                             url=g.get("url") or rel.get("url"), items=rel.get("items"),
                             scheduled=rel.get("scheduled")))
    cuts = []
    for fy, hist in seq.items():
        for prev, cur in zip(hist, hist[1:]):
            if _mid(cur) < _mid(prev) * (1 - CUT_THRESHOLD):
                cuts.append({"fy": fy, "filed": cur["filed"], "accession": cur["accession"],
                             "url": cur["url"], "items": cur["items"], "scheduled": cur["scheduled"],
                             "prev": {"low": prev["low"], "high": prev["high"], "filed": prev["filed"]},
                             "new": {"low": cur["low"], "high": cur["high"]},
                             "change_pct": _mid(cur) / _mid(prev) - 1, "excerpt": cur["excerpt"]})
    return sorted(cuts, key=lambda c: c["filed"])


def voluntary_bad_news(cuts: list, n_releases: int, n_with_guidance: int) -> dict:
    """규칙 적용 결과. True만 단언하고 나머지는 사유와 함께 unknown."""
    unscheduled = [c for c in cuts if not c["scheduled"]]
    if unscheduled:
        return {"status": "answered", "answer": True, "evidence": unscheduled,
                "rule": ("정기 실적 발표가 아닌 보도자료에서 연간 매출 가이던스 중간값을 "
                         f"{CUT_THRESHOLD:.0%} 넘게 낮췄다")}
    if cuts:
        why = (f"가이던스 하향 {len(cuts)}건이 모두 정기 실적 발표에서 나왔다 — 선제 공시할 만한 "
               "사건이었는지 판단할 수 없다")
    elif n_with_guidance:
        why = ("창 안에서 연간 매출 가이던스 하향이 없었다 — 나쁜 소식이 없었을 수 있어 "
               "'선제 공시 이력 없음'으로 단정하지 않는다")
    else:
        why = (f"보도자료 {n_releases}건에서 연간 매출 가이던스를 읽지 못했다(미제시 또는 형식 상이). "
               "가이던스 없는 실적 사전경고는 이 규칙이 잡지 못한다")
    return {"status": "unknown", "reason": why, "cuts": cuts}
