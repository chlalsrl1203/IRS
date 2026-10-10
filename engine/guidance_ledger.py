"""
가이던스 원장 — 회사가 스스로 제시한 연간 매출 가이던스를 실제 결과와 짝짓는다 (v3.96)

## 왜 필요한가

QSI의 정직성 질문 두 개(`acc.guidance_miss_3y`, `acc.promise_kept_record`)는 19종목 중
**한 종목도 답하지 못한 상태**였다. 판단이 어려워서가 아니라 수집 경로가 없어서였다 —
가이던스는 실적 보도자료(8-K Item 2.02 Exhibit 99.1)에 회사가 직접 쓴 숫자이고, 실제 결과는
같은 회사가 낸 10-K(companyfacts)에 있다. 둘을 짝짓는 데 판단은 필요 없다.

## 무엇만 다루는가 — 좁게 잡았다

- **GAAP 총매출의 연간 범위 가이던스만.** 세그먼트·구독·ARR·비GAAP EPS는 제외한다
  (정의가 회사마다 다르고 실제값을 1차 자료로 맞출 수 없는 경우가 많다).
- **범위(하단~상단)로 제시된 것만.** "약 $X" 같은 점 추정은 미달 판정 규칙이 모호하다.
- 기간이 분기로 읽히면 버린다. 연간인지 확신할 수 없으면 버린다(거짓 짝짓기보다 누락이 낫다).

## 사전 고정 규칙 (검증된 값이 아니며 결과를 보고 조정하지 않는다)

- 한 회계연도의 **최초 가이던스** = 그 연도에 대한 가장 이른 제시. 그것이 회계연도 시작 후
  150일(1분기 실적 발표) 안에 나오지 않았으면 그 해는 평가하지 않는다(`LATE_INITIAL`) — 연중에
  처음 제시한 숫자로 '약속을 지켰다'고 하면 관대해진다(실측: DECK FY2026은 5월 관세 불확실성으로
  연간 가이던스를 내지 않고 10월에야 냈다).
- '약 $X' 점 추정은 하단=상단=X로 두고, 실제가 X보다 1% 넘게 낮을 때만 미달로 본다.
  미달(miss) = 실제 매출 < 최초 가이던스 하단.
- 평가 대상 = 실제값이 확정된 최근 3개 회계연도 중 최초 가이던스가 있는 해.
- `guidance_miss_3y` = 평가 ≥2개 연도 중 미달 ≥2 → True, 미달 ≤1 → False.
- `promise_kept_record` = 평가 ≥2개 연도, 미달 0 → True / 미달 ≥2 → False / 미달 1 → 판단 보류.
- 실제값과 가이던스 중간값이 ±30% 넘게 벌어지면 짝짓기 오류로 보고 그 해를 버린다
  (회계연도 라벨 어긋남·단위 오류를 조용히 통과시키지 않기 위한 안전장치).

## 하지 않는 것

판정·등급·비중에 반영하지 않는다(QSI와 같은 "병기, 자동판정 안 함"). 가이던스를 상향한 뒤
상단에 걸쳤는지, 보수적으로 낮게 제시했는지(sandbagging) 같은 해석은 하지 않는다 —
그 정보는 원장에 숫자로 남기만 한다.

순수 함수만 둔다. 네트워크는 스크립트가 주입한다.
"""

import datetime
import re

VALIDATION_STATUS = "IMPLEMENTED_NOT_VALIDATED"
INITIAL_DEADLINE_DAYS = 150    # 최초 가이던스가 회계연도 시작 후 이 기간 안에 나와야 평가한다(1분기 실적 발표까지)
MATCH_TOLERANCE = 0.30          # 가이던스 중간값 대비 실제값 괴리 허용(짝짓기 안전장치, 사전 고정)
EVAL_YEARS = 3
MIN_EVAL = 2

_UNIT = {"billion": 1e9, "million": 1e6, "billions": 1e9, "millions": 1e6, "thousands": 1e3, "bn": 1e9, "b": 1e9, "m": 1e6, "mm": 1e6}
_NUM = r"\$\s?(\d[\d,]*(?:\.\d+)?)\s*(billion|million|bn|mm|b|m)?"
_RANGE = re.compile(_NUM + r"\s*(?:to|and|-|–|—)\s*" + _NUM, re.I)
# 매출 앞의 수식어가 세그먼트·제품 단위면 총매출이 아니다.
_REV = re.compile(r"\b((?:[A-Za-z&\-]+\s+){0,3})(?:revenues?|net sales)\b", re.I)
_TOTAL_OK = {"total", "net", "gaap", "consolidated", "fiscal", "year", "full", "full-year", "annual",
             "of", "for", "and", "the", "its", "company", "range", "expects", "expect", "guidance",
             "outlook", "targets", "target"}
_SEGMENT_HINT = re.compile(
    r"(segment|subscription|product|service|license|licence|recurring|platform|cloud|support|"
    r"professional|hardware|software|ads?|advertising|transaction|marketplace|mobility|delivery|"
    r"freight|premium|commission|organic|arr|digital|creative|experience|consumer|business)", re.I)
_QUARTER = re.compile(r"\b(first|second|third|fourth)\s+(fiscal\s+)?quarter\b|\bQ[1-4]\b|\bquarterly\b", re.I)
_ANNUAL = re.compile(
    r"\b(?:fiscal\s+(?:year\s+)?(20\d\d)|FY\s?['’]?(20\d\d|\d\d)\b|full[\s-]year\s+(?:fiscal\s+)?(20\d\d)|"
    r"(20\d\d)\s+(?:full[\s-]year|fiscal\s+year|annual|outlook|guidance|targets?)|"
    r"(?:twelve|12)[\s-]month\s+period\s+ending\s+[A-Z][a-z]+\s+\d{1,2},\s+(20\d\d))", re.I)
_ATTACH = re.compile(r"[\s,]*(?:of\s+)?(?:the\s+)?(?:fiscal\s+)?(?:year\s+)?")
_UNIT_HDR = re.compile(r"in\s+(millions|billions|thousands)", re.I)
UNIT_LOOKBACK = 2500  # 표 머리 단위 표기를 찾는 거리
_POINT = re.compile(r"(?:expected|projected|anticipated)\s+to\s+(?:be\s+)?(?:increase\s+|grow\s+)?approximately\s+"
                    r"(?:\d+(?:\.\d+)?%\s+to\s+)?" + _NUM, re.I)
POINT_TOLERANCE = 0.01   # '약 $X' 가이던스의 미달 허용폭(사전 고정·비검증)
_HEADING = re.compile(
    r"Outlook\s+for\s+(?:the\s+)?(?:(?P<months>Three|Six|Nine|Twelve|3|6|9|12)[\s-]Month\s+Period\s+"
    r"Ending\s+[A-Z][a-z]+\s+\d{1,2},\s+|(?:Fiscal|Full)\s+(?:Year\s+)?)(?P<y>20\d\d)", re.I)
HEADING_LOOKBACK = 3000
HEADER_GAP = 40       # 표 머리에서 분기 열과 연간 열 사이 최대 거리
_VALUE = re.compile(r"\$\s?\d[\d,]*(?:\.\d+)?\s*(?:billion|million|bn|mm|b|m)?"
                    r"(?:\s*(?:to|-|–|—)\s*\$\s?\d[\d,]*(?:\.\d+)?\s*(?:billion|million|bn|mm|b|m)?)?", re.I)
WINDOW = 260          # 범위 앞에서 기간 표현을 찾는 거리(사전 고정)
REV_GAP = 140         # '매출' 단어와 범위 사이 최대 거리


def _amt(num: str, unit: str, fallback_unit: str = None) -> float:
    v = float(num.replace(",", ""))
    u = (unit or fallback_unit or "").lower()
    return v * _UNIT.get(u, 1.0)


def _year_of(m) -> int:
    y = next(g for g in m.groups() if g)
    y = int(y)
    return y + 2000 if y < 100 else y


def _period_before(text: str, pos: int):
    """범위 직전 창의 기간 표현 → ('annual', FY, 열 번호) / ('quarter', None, 0) / None.

    - 분기 표현이 연도 표현에 **붙어 있으면**('fourth quarter fiscal year 2025', 'Q4 FY25')
      그 연도 표현은 분기를 수식한다.
    - 분기·연간 표현이 붙지 않고 **나란히** 있으면 표 머리다('Q4 2025 FY 2025') — 연간 열이
      몇 번째인지 돌려준다. 첫 범위를 연간으로 읽으면 분기 가이던스를 연간으로 착각한다(실측 DUOL).
    - 창 안에 기간이 없으면 더 앞의 'Outlook for …' 제목을 찾는다(실측 DECK — 제목과 표 사이에
      긴 면책 문단이 끼어 있다).
    """
    win = text[max(0, pos - WINDOW):pos]
    ann = list(_ANNUAL.finditer(win))
    qtr = list(_QUARTER.finditer(win))
    if not ann and not qtr:
        return _heading_period(text, pos)
    last_a = ann[-1] if ann else None
    last_q = qtr[-1] if qtr else None
    if last_a is None:
        return ("quarter", None, 0)
    for q in qtr:
        gap = win[q.end():last_a.start()]
        if q.end() <= last_a.start() and _ATTACH.fullmatch(gap):
            return ("quarter", None, 0)
    if last_q is not None:
        lo, hi = sorted((last_q, last_a), key=lambda m: m.start())
        if hi.start() - lo.end() <= HEADER_GAP:            # 나란한 표 머리
            return ("annual", _year_of(last_a), 1 if last_q.start() < last_a.start() else 0)
        if last_q.start() > last_a.start():
            return ("quarter", None, 0)
    return ("annual", _year_of(last_a), 0)


def _heading_period(text: str, pos: int):
    heads = list(_HEADING.finditer(text[max(0, pos - HEADING_LOOKBACK):pos]))
    if not heads:
        return None
    h = heads[-1]
    if h.group("months") and h.group("months").lower() not in ("twelve", "12"):
        return ("quarter", None, 0)
    return ("annual", int(h.group("y")), 0)


def _unit_hint(text: str, pos: int):
    """표 머리의 단위 표기('$ in millions', '(in millions)')."""
    m = None
    for m in _UNIT_HDR.finditer(text[max(0, pos - UNIT_LOOKBACK):pos]):
        pass
    return m.group(1).lower() if m else None


def extract_annual_revenue_guidance(text: str) -> list:
    """보도자료 본문(정규화된 텍스트)에서 연간 GAAP 총매출 범위 가이던스를 뽑는다.

    반환: [{fy, low, high, excerpt}] — 같은 FY가 여러 번 나오면 첫 번째만 남긴다.
    """
    out = {}
    for rm in _REV.finditer(text):
        lead = rm.group(1) or ""
        words = [w.lower() for w in lead.split()]
        if words and words[-1] not in _TOTAL_OK and _SEGMENT_HINT.search(" ".join(words)):
            continue
        if any(_SEGMENT_HINT.fullmatch(w) for w in words[-2:]):
            continue
        per = _period_before(text, rm.start() + 1)
        if per is None or per[0] != "annual":
            continue
        if re.search(r"[®™]", text[max(0, rm.start() - 80):rm.end()]):
            continue                  # 제품(상표) 매출 가이던스 — 총매출이 아니다(실측 NBIX INGREZZA)
        tail = text[rm.end(): rm.end() + REV_GAP]
        if per[2] > 0:
            # 표의 n번째 열 값만 본다. 열 값이 모자라면 버린다.
            vals = list(_VALUE.finditer(tail))
            if len(vals) <= per[2]:
                continue
            tail = tail[vals[per[2]].start():]
        r = _RANGE.match(tail.lstrip()) if per[2] > 0 else _RANGE.search(tail)
        if per[2] > 0:
            tail = tail.lstrip()
        kind = "range"
        p = None if per[2] > 0 else _POINT.search(tail)
        if p and (r is None or p.start() < r.start()):
            r, kind = p, "point"
        if not r:
            continue
        # 범위 앞에 다른 지표가 끼어 있으면(예: '... revenue growth ... EPS $3 to $4') 버린다.
        between = tail[: r.start()]
        if re.search(r"(EPS|per share|margin|ARR|income|earnings|growth|%)", between, re.I):
            continue
        if kind == "range":
            hint = None if (r.group(2) or r.group(4)) else _unit_hint(text, rm.start())
            low = _amt(r.group(1), r.group(2), r.group(4) or hint)
            high = _amt(r.group(3), r.group(4), r.group(2) or hint)
        else:
            hint = None if r.group(2) else _unit_hint(text, rm.start())
            low = high = _amt(r.group(1), r.group(2) or hint)
        if not (0 < low <= high) or low < 1e6:
            continue
        fy = per[1]
        if fy in out:
            continue
        s0 = max(0, rm.start() - 120)
        out[fy] = {"fy": fy, "low": low, "high": high, "kind": kind,
                   "excerpt": text[s0: rm.end() + r.end()].strip()}
    return list(out.values())


def annual_revenue_actuals(facts: dict, tags, unit: str = "USD") -> dict:
    """{FY(결산 연도): (값, 결산일, 공시일, 태그)} — 10-K 연간(330~400일) 값, 같은 결산일은 최신 공시본.

    ⚠️ 단위를 하나로 고정한다. 여러 통화를 섞으면 TCOM처럼 7배씩 틀린다(v3.71).
    """
    best = {}
    for tag in tags:
        for _tax, tagmap in (facts.get("facts") or {}).items():
            node = tagmap.get(tag)
            if not node:
                continue
            for e in (node.get("units") or {}).get(unit, []):
                if e.get("form") not in ("10-K", "10-K/A", "20-F", "20-F/A"):
                    continue
                s, en, fd, v = e.get("start"), e.get("end"), e.get("filed"), e.get("val")
                if not (s and en and fd) or v is None:
                    continue
                d = (datetime.date.fromisoformat(en) - datetime.date.fromisoformat(s)).days
                if not 330 <= d <= 400:
                    continue
                fy = int(en[:4])
                cur = best.get(fy)
                if cur is None or (cur[3] == tag and fd > cur[2]) or \
                        (cur[3] != tag and tags.index(tag) < tags.index(cur[3])):
                    best[fy] = (float(v), en, fd, tag)
        # 우선순위 높은 태그가 채운 연도는 낮은 태그가 덮지 못한다(위 조건).
    return best


def _miss_floor(g: dict) -> float:
    return g["low"] * (1 - POINT_TOLERANCE) if g.get("kind") == "point" else g["low"]


def build_ledger(releases: list, actuals: dict) -> list:
    """releases: [{filed, url, guidance: [{fy, low, high, kind, excerpt}]}] → 연도별 원장.

    실제값이 있는 연도는 **실제값과 ±30% 넘게 어긋나는 가이던스 항목을 개별로 버린다** —
    분기 가이던스가 연간으로 잘못 읽혔거나 단위를 틀린 항목이다(버린 수를 남긴다).
    """
    by_fy = {}
    for rel in sorted(releases, key=lambda r: r["filed"]):
        for g in rel["guidance"]:
            by_fy.setdefault(g["fy"], []).append(
                dict(g, filed=rel["filed"], url=g.get("url") or rel.get("url")))
    rows = []
    for fy in sorted(by_fy):
        seq = by_fy[fy]
        act = actuals.get(fy)
        dropped = []
        if act is not None:
            val = act[0]
            keep = []
            for g in seq:
                mid = (g["low"] + g["high"]) / 2
                (keep if abs(val - mid) / val <= MATCH_TOLERANCE else dropped).append(g)
            seq = keep
        if not seq:
            rows.append({"fy": fy, "status": "MISMATCH", "n_dropped": len(dropped),
                         "dropped": dropped, "actual": None,
                         "reason": "모든 가이던스 항목이 실제값과 30% 넘게 어긋남 — 짝짓기 오류로 보고 제외"})
            continue
        first, last = seq[0], seq[-1]
        row = {"fy": fy, "initial": first, "final": last, "n_updates": len(seq),
               "n_dropped": len(dropped), "dropped": dropped, "actual": None, "status": "PENDING"}
        if act is not None:
            val, end, filed, tag = act
            fy_start = datetime.date.fromisoformat(end) - datetime.timedelta(days=365)
            late = datetime.date.fromisoformat(first["filed"]) > fy_start + datetime.timedelta(
                days=INITIAL_DEADLINE_DAYS)
            row.update(actual={"value": val, "end": end, "filed": filed, "tag": tag},
                       status=("LATE_INITIAL" if late else
                               ("MISS" if val < _miss_floor(first) else "MET")),
                       vs_initial_low_pct=(val / first["low"] - 1),
                       vs_final_low_pct=(val / last["low"] - 1))
        rows.append(row)
    return rows


def label_ambiguous(actuals: dict) -> bool:
    """결산일이 1월 초(1~15일)인 해가 있으면 결산 연도 라벨이 회사 FY 표기와 어긋날 수 있다(v3.61).

    그 경우 FY2025 가이던스를 FY2024 실적과 짝지어도 매출이 비슷해 ±30% 안전장치가 못 잡는다.
    """
    return any(v[1][5:7] == "01" and int(v[1][8:10]) <= 15 for v in actuals.values())


EX99 = re.compile(r"EX-99(?:\.\d+)?\b")


def exhibit99_urls(index_html: str) -> list:
    """제출 인덱스(-index.htm) 표에서 EX-99.x 문서 URL(상대 경로 → 절대)."""
    out = []
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", index_html, re.S):
        cells = re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)
        if len(cells) >= 4 and EX99.search(re.sub(r"<[^>]+>", "", cells[3])):
            m = re.search(r'href="(?:/ix\?doc=)?([^"]+\.html?)"', cells[2])
            if m:
                out.append("https://www.sec.gov" + m.group(1) if m.group(1).startswith("/") else m.group(1))
    return out


def judge(ledger: list, as_of: str) -> dict:
    """사전 고정 규칙으로 두 질문의 답을 낸다. 확신이 없으면 None + 사유."""
    done = [r for r in ledger if r["status"] in ("MET", "MISS")
            and r["actual"]["filed"] <= as_of]
    done = sorted(done, key=lambda r: r["fy"])[-EVAL_YEARS:]
    n, misses = len(done), sum(r["status"] == "MISS" for r in done)
    years = [r["fy"] for r in done]
    base = {"n_evaluated": n, "n_miss": misses, "years": years}
    if n < MIN_EVAL:
        reason = (f"실제값과 짝지은 최초 연간 매출 가이던스가 {n}개 연도뿐이다(최소 {MIN_EVAL})")
        return base | {"guidance_miss_3y": None, "promise_kept_record": None, "reason": reason}
    miss_ans = misses >= 2
    kept = True if misses == 0 else (False if misses >= 2 else None)
    return base | {"guidance_miss_3y": miss_ans, "promise_kept_record": kept,
                   "reason": "" if kept is not None else "미달 1회 — 이행 기록이 혼재해 판단 보류"}
