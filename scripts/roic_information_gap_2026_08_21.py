"""
PHASE 4 — Realistic Growth 정보 공백: ROIC/ROIIC blocker 해소 여부 검증 (2026-08-21)

## 왜 지금인가 — BLOCKED 사유가 바뀌었을 수 있다

`docs/research_decision_record.md`가 세 번에 걸쳐 같은 이유로 막아둔 항목이 있다:

| # | 대상 | 결정 | 재개조건 |
|---|---|---|---|
| 24 | ROIC / incremental ROIC | **BLOCKED** | SEC XBRL companyfacts로 자기자본·부채 시계열 34종목분 확보 |
| 30 | Exact ROIIC | **BLOCKED** | 유효세율·투하자본 시계열·goodwill 분리 **0/34 계산 불가** |
| 31 | Accounting Approximation ROIIC | **BLOCKED** | **2/34만 가능**(보험사 opt-in `shareholders_equity_by_year`뿐) |

2026-08-19 P0-03 SEC provider와 PHASE 3 검증을 거친 지금, 캐시된 companyfacts
실측 결과는 다음과 같다:

    equity 34/34 · assets 34/34 · 유효세율(tax·pretax) 34/34 ·
    cash 33/34 · goodwill 31/34 · 총부채 29/34 · 이자부부채 27/34

**재개조건이 충족됐다.** RQ-002(SBC)에서 blocker가 데이터 하나였고 그것이
P0-03으로 풀린 것과 같은 패턴이다.

## 이 스크립트가 답하는 질문 (§12)

1. **Data availability** — 실제로 몇 종목에서 계산되는가
2. **Measurement quality** — 투하자본 정의에 따라 얼마나 달라지는가
3. **Information overlap** — 기존 지표(RG·Gap·DRS·마진수준·capex강도)와 중복인가
4. **Incremental information** — 새 정보를 주는가
5. **Proxy risk** — ROIIC 분모(ΔIC)가 근사-0/음수가 되는 빈도

## 하지 않는 것

**RG나 성장지속기간에 반영하지 않는다.** 결정 #29·#33이 이미 REJECTED로
판정했다(판정영향이 정보가 아니라 임의계수 k에 전적으로 의존). 구조 D
(독립 진단축)만이 채택된 구조이며, 이 조사도 그 틀 안에 있다.

`engine/`을 수정하지 않는다 — 문제 존재가 입증되기 전에는 코드를 바꾸지
않는다(§17). 조사에 필요한 SEC 항목은 여기서 직접 읽는다.
"""
import json
import os
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.filing_dates import ANNUAL_FORMS, _days_between  # noqa: E402
from scripts.sbc_harvest_2026_08_21 import _cached_facts, _load_ledgers  # noqa: E402

# 잔액(시점) 항목 — companyfacts에 `start`가 없다.
INSTANT = {
    "equity": ("StockholdersEquity",
               "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"),
    "assets": ("Assets",),
    "liabilities": ("Liabilities",),
    "debt_lt": ("LongTermDebtNoncurrent", "LongTermDebt"),
    "debt_st": ("LongTermDebtCurrent", "ShortTermBorrowings"),
    "cash": ("CashAndCashEquivalentsAtCarryingValue",),
    "goodwill": ("Goodwill",),
}
# 기간 항목
DURATION = {
    "tax": ("IncomeTaxExpenseBenefit",),
    "pretax": (
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments",
    ),
}


def _series(facts, tags, instant):
    """태그 우선순위로 {회계연도: 최초공시 값}. 앞 태그가 비운 연도만 뒤가 채운다."""
    out = {}
    tx = facts.get("facts") or {}
    for tag in tags:
        for _tax, d in tx.items():
            if tag not in d:
                continue
            for _unit, entries in (d[tag].get("units") or {}).items():
                for e in entries:
                    if e.get("form") not in ANNUAL_FORMS:
                        continue
                    end, filed, v = e.get("end"), e.get("filed"), e.get("val")
                    if not (end and filed) or v is None:
                        continue
                    if not instant:
                        s = e.get("start")
                        if not s:
                            continue
                        try:
                            if not 330 <= _days_between(s, end) <= 400:
                                continue
                        except ValueError:
                            continue
                    fy = int(end[:4])
                    prev = out.get(fy)
                    if prev is None or filed < prev[1]:
                        out[fy] = (float(v), filed)
    return {y: v for y, (v, _) in out.items()}


def collect(ticker):
    facts = _cached_facts(ticker)
    if facts is None:
        return None
    got = {k: _series(facts, tags, True) for k, tags in INSTANT.items()}
    got.update({k: _series(facts, tags, False) for k, tags in DURATION.items()})
    return got


def invested_capital(s, fy, definition):
    """
    두 정의를 **둘 다** 계산한다 — 어느 쪽이 옳은지 이 저장소가 판정할 근거가 없고,
    정의에 따라 값이 크게 달라진다는 사실 자체가 §12의 'Measurement quality' 답이다.

    - `equity_plus_debt` : 자기자본 + 이자부부채 − 현금 (표준 정의에 가장 가까움)
    - `assets_minus_cash`: 총자산 − 현금 (커버리지는 넓지만 무이자 영업부채 포함 -> 과대)
    """
    if definition == "equity_plus_debt":
        eq = s["equity"].get(fy)
        lt, st = s["debt_lt"].get(fy), s["debt_st"].get(fy)
        cash = s["cash"].get(fy)
        if eq is None or (lt is None and st is None) or cash is None:
            return None
        return eq + (lt or 0.0) + (st or 0.0) - cash
    if definition == "assets_minus_cash":
        a, cash = s["assets"].get(fy), s["cash"].get(fy)
        if a is None or cash is None:
            return None
        return a - cash
    raise ValueError(definition)


def effective_tax_rate(s, fy):
    t, p = s["tax"].get(fy), s["pretax"].get(fy)
    if t is None or p is None or p <= 0:
        return None            # 세전적자면 유효세율이 의미를 잃는다 - 추정하지 않는다
    r = t / p
    return r if 0.0 <= r <= 0.6 else None   # 일회성 항목으로 튄 해는 버린다


def analyse(ticker, ledger):
    s = collect(ticker)
    if s is None:
        return {"ticker": ticker, "status": "NO_CACHE"}
    op = {int(y): v for y, v in ledger["inputs"]["operating_income_by_year"].items()}
    years = sorted(op)
    row = {"ticker": ticker, "status": "OK", "years": years}

    for definition in ("equity_plus_debt", "assets_minus_cash"):
        roic, nopat, ic = {}, {}, {}
        for fy in years:
            tr = effective_tax_rate(s, fy)
            cap = invested_capital(s, fy, definition)
            if tr is None or cap is None or cap <= 0 or op.get(fy) is None:
                continue
            n = op[fy] * (1 - tr)
            nopat[fy], ic[fy] = n, cap
            roic[fy] = n / cap
        row[definition] = {
            "roic_by_year": roic,
            "roic_latest": roic.get(max(roic)) if roic else None,
            "roic_mean": statistics.fmean(roic.values()) if roic else None,
            "n_years": len(roic),
        }
        # ROIIC — 분모가 근사-0/음수면 폭발한다. 그 빈도 자체가 측정 품질 지표다.
        ys = sorted(set(nopat) & set(ic))
        roiic, bad = None, None
        if len(ys) >= 4:
            a, b = ys[-4], ys[-1]
            d_ic, d_np = ic[b] - ic[a], nopat[b] - nopat[a]
            bad = abs(d_ic) < 0.10 * ic[a] or d_ic <= 0
            roiic = None if bad else d_np / d_ic
        row[definition]["roiic_3y"] = roiic
        row[definition]["roiic_denominator_unusable"] = bad
    return row


def main():
    ledgers = _load_ledgers()
    rows = [analyse(t, d) for t, (_fn, d) in sorted(ledgers.items())]
    ok = [r for r in rows if r["status"] == "OK"]

    def cov(defn, key="roic_latest"):
        return sum(1 for r in ok if r[defn][key] is not None)

    print(f"ledger {len(rows)}종목 · 캐시 보유 {len(ok)}\n")
    print("§12 Data availability — 정의별 ROIC 계산 가능 종목")
    for defn in ("equity_plus_debt", "assets_minus_cash"):
        n = cov(defn)
        roiic_ok = sum(1 for r in ok if r[defn]["roiic_3y"] is not None)
        print(f"  {defn:20} ROIC {n:2}/{len(rows)}   ROIIC(3y) {roiic_ok:2}/{len(rows)}")

    print("\n§12 Measurement quality — 두 정의의 ROIC 차이")
    both = [r for r in ok if r["equity_plus_debt"]["roic_latest"] is not None
            and r["assets_minus_cash"]["roic_latest"] is not None]
    if both:
        ratios = [r["equity_plus_debt"]["roic_latest"] / r["assets_minus_cash"]["roic_latest"]
                  for r in both if r["assets_minus_cash"]["roic_latest"]]
        print(f"  둘 다 계산된 종목 {len(both)}개 · 비율(좁은/넓은) 중앙값 "
              f"{statistics.median(ratios):.2f} · 범위 {min(ratios):.2f}~{max(ratios):.2f}")

    # ── 기존 지표와의 중복도 ────────────────────────────────────────────
    def spearman(xs, ys):
        n = len(xs)
        if n < 5:
            return None
        def rank(v):
            order = sorted(range(n), key=lambda i: v[i])
            rk = [0.0] * n
            i = 0
            while i < n:
                j = i
                while j + 1 < n and v[order[j + 1]] == v[order[i]]:
                    j += 1
                avg = (i + j) / 2 + 1
                for k in range(i, j + 1):
                    rk[order[k]] = avg
                i = j + 1
            return rk
        rx, ry = rank(xs), rank(ys)
        mx, my = statistics.fmean(rx), statistics.fmean(ry)
        num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
        den = (sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry)) ** 0.5
        return num / den if den else None

    paired, existing = [], {"realistic_growth": [], "gap": [], "drs": [],
                            "op_margin_level": [], "capex_intensity": []}
    for r in ok:
        v = r["equity_plus_debt"]["roic_mean"]
        if v is None:
            continue
        _fn, d = ledgers[r["ticker"]]
        inp = d["inputs"]
        yrs = sorted(int(y) for y in inp["revenue_by_year"])
        last = str(yrs[-1])
        rev = inp["revenue_by_year"][last]
        paired.append(v)
        existing["realistic_growth"].append(d["growth"]["realistic_growth"])
        existing["gap"].append(d["expectation_gap"])
        existing["drs"].append(d["drs"]["score"])
        existing["op_margin_level"].append(
            inp["operating_income_by_year"][last] / rev if rev else 0.0)
        existing["capex_intensity"].append(
            inp["capex_by_year"][last] / rev if rev else 0.0)

    print(f"\n§12 Information overlap — ROIC(평균, equity+debt) vs 기존 지표 "
          f"순위상관 (n={len(paired)})")
    overlaps = {}
    for k, v in existing.items():
        c = spearman(paired, v)
        overlaps[k] = c
        print(f"  {k:20} {c:+.3f}" if c is not None else f"  {k:20} n/a")

    out = {
        "generated_at": "2026-08-21",
        "phase": "PHASE 4 — Realistic Growth information gap (ROIC/ROIIC)",
        "affects_official_judgment": False,
        "blocked_status_change": (
            "결정 #24/#30/#31의 재개조건(자기자본·부채 시계열 34종목분)이 "
            "P0-03 SEC provider로 충족됐다. 이 조사는 그 확인이다."
        ),
        "not_wired_into_growth": (
            "RG·성장지속기간에 반영하지 않는다 — 결정 #29·#33이 이미 REJECTED "
            "(판정영향이 정보가 아니라 임의계수 k에 전적 의존). 구조 D(독립 진단축)만."
        ),
        "overlap_with_existing": overlaps,
        "results": rows,
    }
    path = "reports/roic_information_gap_2026-08-21.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"\n저장: {path}")


if __name__ == "__main__":
    main()
