"""
ecd(Executive Compensation Disclosure) inline XBRL 파서 — 위임장·정기보고서 (v4.00, 2026-10-10)

`docs/opensource_qualitative_2026-10-09.md` §4 ②. companyfacts에는 `ecd` 택소노미가 없다
(ADBE 실측: dei·invest·us-gaap·srt·ffd뿐). 그러나 DEF 14A·10-Q·10-K 원문 HTML에 inline
XBRL(`<ix:nonFraction name="ecd:...">`)로 붙어 있고 stdlib `html.parser`로 읽힌다.
참조 구현은 edgartools(MIT) `proxy/core.py`의 태그 목록 — 코드는 가져오지 않았다(lxml·pandas 의존).

## 세 질문과 사전 고정 규칙(판독·수집 전에 고정, 결과를 보고 바꾸지 않는다)

1. `gov.pay_measure_category` — 회사가 위임장 '보수 대 성과(PvP)' 표에서 고른 **가장 중요한
   재무 지표**(`ecd:CoSelectedMeasureName`)를 키워드로 분류한다. 순서대로 먼저 맞는 것:
   return_on_capital → shareholder_return → cash_flow → earnings → revenue_growth → other.
   이 지표가 "경영진이 무엇으로 보상받는가"를 회사 스스로 밝힌 것이다. 좋고 나쁨은 판단하지 않는다.
2. `gov.pvp_tsr_vs_peer` — 같은 표의 최근 연도 `TotalShareholderRtnAmt / PeerGroupTotalShareholderRtnAmt − 1`.
   두 값 모두 같은 시점 $100 투자의 누적 가치다. 비교군은 회사가 고른 것(지수일 수도 있다).
3. `gov.trading_plan_adoptions_12m` — 최근 12개월 정기보고서(10-Q·10-K, Item 408)가 공시한
   임원·이사 매매계획(10b5-1 및 비10b5-1) **채택 건수** = `ecd:TrdArrAdoptionDate` 사실의 수.
   창 안 정기보고서가 3건 미만이거나, 한 건이라도 ecd 공시 블록(`*ArrAdoptedFlag`)이 없으면 모른다.
   (채택 0건과 '공시 블록 없음'을 구분한다 — 없음을 0으로 읽으면 거짓 청정 신호가 된다.)

외국 발행사(20-F)는 PvP·Item 408 의무가 없다 → 세 질문 모두 not_applicable(제도 부재).

## ⚠️ '실지급 보수(CAP)'는 쓰지 않는다

`PeoActuallyPaidCompAmt`는 규정상 주가 변동이 섞인 값이라 TSR과 기계적으로 같이 움직인다.
"보수가 성과와 정렬됐다"는 주장의 근거로 쓰면 동어반복이 된다 — 수집 리포트에 병기만 하고
질문의 답으로 쓰지 않는다.

판정·점수 함수 없음, `run_analysis()`·포트폴리오 미배선(테스트로 고정).
"""

import re
from html.parser import HTMLParser

VALIDATION_STATUS = {
    "pay_measure_category": "IMPLEMENTED_NOT_VALIDATED",
    "pvp_tsr_vs_peer": "IMPLEMENTED_NOT_VALIDATED",
    "trading_plan_adoptions_12m": "IMPLEMENTED_NOT_VALIDATED",
}

MIN_PERIODIC_REPORTS = 3        # 12개월 창에 기대되는 정기보고서는 4건(10-Q 3 + 10-K 1)

# 순서가 규칙이다 — 앞에서 먼저 맞는 범주를 쓴다(예: "Return on Invested Capital"은 earnings가 아니다).
MEASURE_RULES = (
    ("return_on_capital", r"\breturn on (invested |average )?(capital|equity|assets)\b|\broic\b|\broe\b|\broa\b|\broce\b"),
    ("shareholder_return", r"\btsr\b|total shareholder return|total stockholder return"),
    ("cash_flow", r"cash flow|\bfcf\b|cash from operations|operating cash"),
    ("earnings", r"\beps\b|earnings|net income|operating income|\bebitda?\b|profit|margin|\bebt\b|\bnoi\b|\bffo\b|\baffo\b"),
    ("revenue_growth", r"revenue|sales|bookings|\barr\b|recurring|premium|subscriber|net new|growth|volume|transaction"),
)
MEASURE_CATEGORIES = tuple(c for c, _ in MEASURE_RULES) + ("other",)


def classify_measure(name: str) -> str:
    s = (name or "").lower()
    for cat, pat in MEASURE_RULES:
        if re.search(pat, s):
            return cat
    return "other"


class _IxParser(HTMLParser):
    """ix:nonFraction / ix:nonNumeric 의 이름·속성·보이는 글자. 중첩을 스택으로 처리."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.facts, self._stack = [], []

    def handle_starttag(self, tag, attrs):
        if tag in ("ix:nonfraction", "ix:nonnumeric"):
            a = dict(attrs)
            self._stack.append({"name": a.get("name", ""), "context": a.get("contextref"),
                                "format": a.get("format") or "", "scale": a.get("scale"),
                                "sign": a.get("sign"), "kind": tag[3:], "text": []})

    def handle_endtag(self, tag):
        if tag in ("ix:nonfraction", "ix:nonnumeric") and self._stack:
            f = self._stack.pop()
            f["text"] = re.sub(r"\s+", " ", "".join(f["text"])).strip()
            self.facts.append(f)

    def handle_data(self, data):
        for f in self._stack:          # 바깥 사실도 안쪽 글자를 포함한다(중첩 블록)
            f["text"].append(data)


def ix_facts(html: str, prefix: str = "ecd:") -> list:
    """prefix로 시작하는 inline XBRL 사실 목록."""
    p = _IxParser()
    p.feed(html)
    p.close()
    return [f for f in p.facts if f["name"].startswith(prefix)]


_CTX = re.compile(r"<xbrli:context\b[^>]*\bid=\"([^\"]+)\"[^>]*>(.*?)</xbrli:context>", re.S | re.I)


def contexts(html: str) -> dict:
    """{id: {"start","end","instant","dims": {축: 구성원}}}"""
    out = {}
    for cid, body in _CTX.findall(html):
        g = lambda t: (re.search(rf"<xbrli:{t}>([^<]+)</xbrli:{t}>", body) or [None, None])[1]  # noqa: E731
        dims = dict(re.findall(r"<xbrldi:explicitMember[^>]*dimension=\"([^\"]+)\"[^>]*>([^<]+)<", body))
        out[cid] = {"start": g("startDate"), "end": g("endDate"), "instant": g("instant"), "dims": dims}
    return out


def numeric_value(fact):
    """ix:nonFraction 값. fixed-zero는 0, 숫자는 scale·sign 반영. 읽을 수 없으면 None."""
    fmt = fact.get("format") or ""
    if "fixed-zero" in fmt or "zerodash" in fmt:
        return 0.0
    txt = re.sub(r"[^\d.]", "", fact.get("text") or "")
    if not txt:
        return None
    try:
        v = float(txt)
    except ValueError:
        return None
    if fact.get("scale"):
        v *= 10 ** int(fact["scale"])
    return -v if fact.get("sign") == "-" else v


def pvp_from_proxy(html: str) -> dict:
    """DEF 14A의 PvP 표에서 회사 선정 지표와 최근 연도 TSR 대 비교군."""
    facts = ix_facts(html)
    if not facts:
        return {"status": "NO_ECD", "reason": "ecd inline XBRL이 없다(PvP 공시 없음 또는 비표준)"}
    ctx = contexts(html)
    out = {"status": "OK"}

    names = [f["text"] for f in facts if f["name"] == "ecd:CoSelectedMeasureName" and f["text"]]
    out["measure_name"] = names[0] if names else None
    out["measure_category"] = classify_measure(names[0]) if names else None

    def by_period(tag):
        got = {}
        for f in facts:
            if f["name"] != tag or f["kind"] != "nonfraction":
                continue
            c = ctx.get(f["context"]) or {}
            if c.get("dims"):          # 개인·조정항목 축이 붙은 사실은 표의 연도 행이 아니다
                continue
            v = numeric_value(f)
            if v is not None and c.get("end"):
                got[c["end"]] = (v, f["text"])
        return got

    tsr, peer = by_period("ecd:TotalShareholderRtnAmt"), by_period("ecd:PeerGroupTotalShareholderRtnAmt")
    common = sorted(set(tsr) & set(peer))
    if common:
        end = common[-1]
        out.update({"period_end": end, "tsr": tsr[end][0], "peer_tsr": peer[end][0],
                    "tsr_text": tsr[end][1], "peer_tsr_text": peer[end][1],
                    "tsr_vs_peer": (tsr[end][0] / peer[end][0] - 1) if peer[end][0] else None,
                    "n_years": len(common)})
    cap = by_period("ecd:PeoActuallyPaidCompAmt")
    out["peo_cap_not_used"] = {k: v[0] for k, v in sorted(cap.items())}   # 병기만(위 docstring)
    return out


def trading_plans_from_periodic(html: str) -> dict:
    """정기보고서 하나의 Item 408 공시: 블록 존재 여부와 채택·해지 건수."""
    facts = ix_facts(html)
    has_block = any(f["name"] in ("ecd:Rule10b51ArrAdoptedFlag", "ecd:NonRule10b51ArrAdoptedFlag")
                    for f in facts)
    adopt = {(f["context"], f["text"]) for f in facts if f["name"] == "ecd:TrdArrAdoptionDate"}
    term = {(f["context"], f["text"]) for f in facts if f["name"] == "ecd:TrdArrTerminationDate"}
    names = sorted({f["text"] for f in facts if f["name"] == "ecd:TrdArrIndName" and f["text"]})
    return {"has_block": has_block, "adoptions": len(adopt), "terminations": len(term),
            "individuals": names}


def trading_plan_adoptions(per_report: list) -> dict:
    """[(filing_date, trading_plans_from_periodic 결과), ...] -> 12개월 합계 또는 사유."""
    if len(per_report) < MIN_PERIODIC_REPORTS:
        return {"status": "INSUFFICIENT", "reason": (f"창 안 정기보고서 {len(per_report)}건 "
                                                     f"(< {MIN_PERIODIC_REPORTS})")}
    missing = [d for d, r in per_report if not r["has_block"]]
    if missing:
        return {"status": "NO_BLOCK", "reason": (f"Item 408 ecd 공시 블록이 없는 보고서 {missing} "
                                                 "— 채택 0건과 구분할 수 없다")}
    return {"status": "OK", "answer": sum(r["adoptions"] for _d, r in per_report),
            "terminations": sum(r["terminations"] for _d, r in per_report),
            "n_reports": len(per_report)}
