"""
SEC 의견서한(UPLOAD/CORRESP) 집계 (v4.02, 2026-10-10)

`docs/opensource_qualitative_2026-10-09.md` §4 ④. SEC 직원이 회사 공시(10-K의 비GAAP 지표·수익인식·
세그먼트 등)를 지적한 서한은 EDGAR에 `UPLOAD`로, 회사 답변은 `CORRESP`로 공개된다. 둘 다 이미 받는 제출
목록(`sec_events.list_filings`)에 들어 있다. edgartools(MIT) `correspondence.py`는 "Re:" 블록으로 스레드를
재구성하지만, 여기서는 **건수와 답변서의 주제 키워드만** 센다(코드는 가져오지 않았다).

## 사전 고정 규칙
- `acc.sec_comment_letters_3y` = 3년 창 안의 UPLOAD 건수. 제출 목록이 창을 덮지 못하면 답하지 않는다.
  ⚠️ UPLOAD에는 등록신고서(S-1·S-3) 검토, "추가 의견 없음" 종결 서한도 섞여 있다 — **사실의 건수일 뿐**
  공시 품질 판정이 아니다. 공개가 검토 종료 후 최소 20일 지연되므로 최근 서한은 아직 없을 수 있다.
- 주제(`topics`)는 회사 답변서(CORRESP, HTML일 때만)에 나온 키워드를 리포트에 병기만 한다(UPLOAD는 대개 PDF라
  stdlib로 못 읽는다). 답으로 쓰지 않는다.
판정·점수 없음, 미배선.
"""

import re

VALIDATION_STATUS = "IMPLEMENTED_NOT_VALIDATED"

TOPICS = {
    "non_gaap": r"non-gaap|non gaap|adjusted ebitda|key performance indicator",
    "revenue_recognition": r"revenue recognition|asc 606|performance obligation",
    "segments": r"segment",
    "impairment": r"impairment|goodwill",
    "mdna": r"management.s discussion|md&a|known trends",
    "income_tax": r"income tax|valuation allowance",
    "registration": r"registration statement|form s-1|form s-3|form s-4|acceleration",
}


def count_letters(listing: dict, since: str, as_of: str) -> dict:
    rows = [r for r in listing["rows"] if since <= r["filingDate"] <= as_of]
    up = sorted(r["filingDate"] for r in rows if r["form"] == "UPLOAD")
    co = [r for r in rows if r["form"] == "CORRESP"]
    if not listing.get("covers_window"):
        return {"status": "WINDOW_NOT_COVERED", "reason": "제출 목록이 3년 창을 덮지 못했다 — 0건 단정 불가"}
    return {"status": "OK", "answer": len(up), "upload_dates": up, "n_corresp": len(co),
            "corresp_rows": co}


def corresp_topics(text: str) -> list:
    t = (text or "").lower()
    return sorted(k for k, pat in TOPICS.items() if re.search(pat, t))
