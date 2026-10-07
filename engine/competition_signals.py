"""
경쟁·해자 신호 — 회사 공시만으로 계산할 수 있는 대리지표 (v3.97)

QSI 경쟁 축 4문항(`cmp.*`)은 19종목 중 한 종목도 답하지 못했다. 해자는 판단의 영역이지만 출발점은
숫자와 회사 자신의 문장으로 만들 수 있다. 이 모듈은 **세 가지 대리지표만** 계산하고 판정·점수는 내지 않는다.

1. 가격결정력 대리(`pricing_power_from_margins`) — 매출총이익률의 3년 추세와 수준.
   버핏식 해자 판단의 고전적 대리지표지만 **가격결정력 그 자체는 아니다**(원가 하락으로도 마진은 오른다).
2. 동종업계 대비 상대 성장(`relative_growth`) — 회사가 10-K/20-F에서 **직접 이름을 댄** 상장 경쟁사
   매출 합계와 비교. 시장점유율이 아니라 '경쟁사 묶음 대비 성장 격차'다. 비교군 선택은 사람이 하며
   회사 원문 인용을 근거로 남긴다(`data/peer_baskets.json`).
3. 위험요인 신규 문장(`new_competition_sentences`) — 전년 10-K/20-F 위험요인 대비 **새로 추가된**
   경쟁 관련 문장. Cohen·Malloy·Nguyen "Lazy Prices"(Journal of Finance, 2020)가 10-K 문장 변화의
   정보성을 보였다 — 여기서는 수익률 예측이 아니라 '회사가 스스로 새로 인정한 위협'을 모으는 데만 쓴다.

모든 임계값은 사전 고정이며 검증되지 않았다(IMPLEMENTED_NOT_VALIDATED). 순수 함수만 둔다.
"""

import re

VALIDATION_STATUS = "IMPLEMENTED_NOT_VALIDATED"

# --- 1. 가격결정력 대리 -------------------------------------------------------------------
GM_WINDOW = 3                 # 연
GM_ERODING_PP = -3.0          # 3년 총이익률 변화가 이 이하이면 eroding
GM_RISING_PP = 1.0            # 이 이상 오르며 매출이 성장하면 evidenced
GM_HIGH_LEVEL = 70.0          # 이 수준 이상을 3년간(−1%p 이내) 유지하며 매출이 성장해도 evidenced
GM_HOLD_PP = -1.0


def gross_margins(revenue: dict, gross_profit: dict = None, cost: dict = None) -> dict:
    """{연: 총이익률 %}. 매출총이익 태그가 없으면 매출 − 매출원가."""
    out = {}
    for y, r in revenue.items():
        if not r or r <= 0:
            continue
        if gross_profit and y in gross_profit:
            out[y] = gross_profit[y] / r * 100
        elif cost and y in cost:
            out[y] = (r - cost[y]) / r * 100
    return out


def pricing_power_from_margins(revenue: dict, gm: dict) -> dict:
    if not gm:
        return {"answer": None, "reason": "매출총이익(또는 매출원가) 값이 없다 — 금융업 등 원가 구조가 다른 업종일 수 있다"}
    end = max(gm)
    start = end - GM_WINDOW
    if start not in gm or start not in revenue or end not in revenue:
        return {"answer": None, "reason": f"FY{start}·FY{end} 총이익률·매출이 모두 있어야 한다"}
    d = gm[end] - gm[start]
    growing = revenue[end] > revenue[start]
    base = {"fy_start": start, "fy_end": end, "gm_start": round(gm[start], 2), "gm_end": round(gm[end], 2),
            "gm_change_pp": round(d, 2), "revenue_growing": growing,
            "rule": (f"3년 총이익률 변화 ≤ {GM_ERODING_PP}%p → eroding / 변화 ≥ +{GM_RISING_PP}%p 또는 "
                     f"{GM_HIGH_LEVEL:.0f}% 이상을 {GM_HOLD_PP}%p 이내로 유지하면서 매출 성장 → evidenced / "
                     "그 밖 → unevidenced (사전 고정 · 대리지표)")}
    if d <= GM_ERODING_PP:
        return base | {"answer": "eroding"}
    if growing and (d >= GM_RISING_PP or (gm[end] >= GM_HIGH_LEVEL and d > GM_HOLD_PP)):
        return base | {"answer": "evidenced"}
    return base | {"answer": "unevidenced"}


# --- 2. 동종업계 대비 상대 성장 -------------------------------------------------------------
REL_WINDOW = 3
REL_GAIN_PP = 3.0             # 연환산 성장 격차(%p)
LIFECYCLE_DECLINE = 0.0       # 묶음 전체 매출 CAGR이 이 미만이면 쇠퇴
LIFECYCLE_GROWTH = 3.0        # 이 이상이면 쇠퇴 아님


def _cagr(a: float, b: float, n: int) -> float:
    return ((b / a) ** (1 / n) - 1) * 100


ALIGN_DAYS = 200              # 비교군 결산일을 회사 결산일에 맞출 때 허용 거리


def align_to(company: dict, peer: dict) -> dict:
    """{연: (값, 결산일, …)} 둘을 받아, 회사 각 연도에 **결산일이 가장 가까운** 비교군 값을 붙인다.

    결산월이 다르면(NXT 3월 vs ARRY 12월) 연도 라벨이 한 해 어긋난다 — 라벨이 아니라 결산일로 맞춘다.
    """
    import datetime as _dt
    out = {}
    pe = [(_dt.date.fromisoformat(t[1]), t[0]) for t in peer.values()]
    for y, t in company.items():
        ce = _dt.date.fromisoformat(t[1])
        best = min(pe, key=lambda x: abs((x[0] - ce).days), default=None)
        if best and abs((best[0] - ce).days) <= ALIGN_DAYS:
            out[y] = best[1]
    return out


def relative_growth(company: dict, peers: dict) -> dict:
    """company: {연: 매출}, peers: {티커: {연: 매출}}(회사 연도 라벨로 이미 맞춘 값) — 3년 CAGR 비교.

    시장점유율이 아니라 '회사가 직접 지명한 상장 경쟁사 묶음 대비 성장 격차'다.
    """
    if not company:
        return {"answer": None, "reason": "회사 매출 값이 없다"}
    end = max(company)
    start = end - REL_WINDOW
    if start not in company or company[start] <= 0:
        return {"answer": None, "reason": f"회사 FY{start} 매출이 없다"}
    usable = {t: s for t, s in peers.items() if s.get(start, 0) > 0 and s.get(end, 0) > 0}
    if not usable:
        return {"answer": None, "reason": f"비교군 중 FY{start}·FY{end} 매출이 모두 있는 회사가 없다"}
    c = _cagr(company[start], company[end], REL_WINDOW)
    ps = sum(s[start] for s in usable.values())
    pe = sum(s[end] for s in usable.values())
    p = _cagr(ps, pe, REL_WINDOW)
    whole = _cagr(ps + company[start], pe + company[end], REL_WINDOW)
    gap = c - p
    share = "gaining" if gap >= REL_GAIN_PP else ("losing" if gap <= -REL_GAIN_PP else "stable")
    life = True if whole < LIFECYCLE_DECLINE else (False if whole >= LIFECYCLE_GROWTH else None)
    return {"answer": share, "lifecycle_decline": life, "fy_start": start, "fy_end": end,
            "company_cagr_pct": round(c, 2), "peer_cagr_pct": round(p, 2), "basket_cagr_pct": round(whole, 2),
            "gap_pp": round(gap, 2), "peers_used": sorted(usable),
            "peers_dropped": sorted(set(peers) - set(usable)),
            "rule": (f"3년 매출 CAGR − 지명 경쟁사 합계 CAGR ≥ +{REL_GAIN_PP}%p → gaining, ≤ −{REL_GAIN_PP}%p → "
                     f"losing, 그 밖 stable. 회사+경쟁사 합계 CAGR < {LIFECYCLE_DECLINE}% → 쇠퇴, "
                     f"≥ {LIFECYCLE_GROWTH}% → 쇠퇴 아님 (사전 고정 · 생존 경쟁사만 — 퇴출 기업이 빠져 "
                     "쇠퇴를 과소평가한다)")}


# --- 3. 위험요인 신규 경쟁 문장 -------------------------------------------------------------
NEW_SENT_JACCARD = 0.5        # 전년 어떤 문장과도 단어 겹침이 이보다 낮으면 '새 문장'
# 'competent authorities'·'competency'는 경쟁이 아니다(실측: SE·NBIX). 인재 확보 경쟁(보상 문단)과
# 경쟁법 규정 소개도 위협 서술이 아니라 제외한다(실측: NBIX 보상 철학, PDD 반부정경쟁법 개정).
_COMP = re.compile(r"\b(compet(?:e|es|ed|ing|itor|itors|ition|itive|itively)|rivals?|new\s+entrants?|"
                   r"disintermediat\w*|substitut\w*|pricing\s+pressure|market\s+share|take\s+share)\b", re.I)
_NOT_THREAT = re.compile(r"(compensation|salar(?:y|ies)|bonus|talent|employees?|hire|hiring|recruit|retain\s+top|"
                         r"Competition\s+Law|anti-?monopoly|anti-?unfair)", re.I)
_RF_10K = (r"Item\s+1A\s*[.:\-—–]?\s*Risk\s+Factors", r"Item\s+1B\s*[.:\-—–]?\s*Unresolved")
_RF_20F = (r"(?:Item\s+3\.?\s*)?D\.?\s*Risk\s+Factors", r"Item\s+4\s*[.:\-—–]?\s*Information\s+on\s+the\s+Company")
RF_CAP = 400000


def risk_factor_section(body: str, form: str) -> str:
    """10-K Item 1A / 20-F Item 3.D 본문.

    끝 표지마다 **바로 앞의** 시작 표지를 짝지어 가장 긴 구간을 고른다. 시작 표지를 먼저 고르면 본문 중간의
    상호참조('see Part I, Item 1A. Risk Factors')에서 시작해 사업 설명·인력 문단까지 삼킨다(실측: NBIX).
    끝 표지를 못 찾거나 상한에 닿으면 빈 문자열 — 절 경계를 모르는 채로 비교하면 다른 장의 문장이
    '새 위협'으로 섞인다(실측: MNDY 교차참조형 20-F).
    """
    start, end = _RF_10K if form.startswith("10-K") else _RF_20F
    starts = [m.start() for m in re.finditer(start, body, re.I)]
    best = ""
    for e in re.finditer(end, body, re.I):
        prior = [s0 for s0 in starts if s0 < e.start()]
        if not prior:
            continue
        sec = body[prior[-1]: e.start()]
        if len(sec) > len(best):
            best = sec
    return best if len(best) < RF_CAP else ""


def _sentences(sec: str) -> list:
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z•])", sec)
    return [p.strip() for p in parts if 40 <= len(p.strip()) <= 700]


def _tokens(s: str) -> frozenset:
    return frozenset(re.findall(r"[a-z]{3,}", s.lower()))


def new_competition_sentences(new_sec: str, old_sec: str, limit: int = 5) -> dict:
    if not new_sec or not old_sec:
        return {"answer": None, "reason": "올해·전년 위험요인 절을 모두 찾지 못했다"}
    old = [_tokens(s) for s in _sentences(old_sec)]
    added = []
    for s in _sentences(new_sec):
        t = _tokens(s)
        if not t:
            continue
        best = max((len(t & o) / len(t | o) for o in old if o), default=0.0)
        if best < NEW_SENT_JACCARD:
            added.append(s)
    comp = list(dict.fromkeys(s for s in added if _COMP.search(s) and not _NOT_THREAT.search(s)))
    return {"n_new_sentences": len(added), "n_new_competition": len(comp), "sentences": comp[:limit],
            "answer": comp[:limit],
            "rule": f"전년 위험요인 어떤 문장과도 단어 Jaccard < {NEW_SENT_JACCARD}이고 경쟁 어휘를 포함한 문장"}
