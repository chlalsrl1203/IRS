"""
PHASE 3 — capex 정의 대조 감사 (2026-08-21)

## 조사 대상 — 이미 발견된 불일치 하나

RQ-002(2026-08-21) 부수 소견:

> **MCK: ledger capex 745M vs SEC 436M — ledger가 71% 높다.** OCF는 정확히
> 일치하므로 연도 문제가 아니라 정의 차이다(**원인 미확인**).

§11에 따라 원인을 규명하고 시스템적 의미(MCK-specific인가 IRS-wide인가)를
판정한다. **판정을 바꾸기 위한 조사가 아니다.**

## 규명된 원인 — ledger가 옳고 provider가 좁다

MCK 8개년 전수 대조(FY2019~FY2026):

    ledger capex == PaymentsToAcquirePropertyPlantAndEquipment
                  + PaymentsToAcquireSoftware          (8/8 완전 일치)

즉 ledger는 회사가 현금흐름표에 보고하는 **총 자본지출**을 일관되게 쓴다
(MCK는 FY2020~2025에 대해 그 합을 `PaymentsToAcquireProductiveAssets`로도
직접 태깅한다). 반면 `engine/data/providers/sec.py`의 `METRIC_TAGS["capex"]`는

    1) PaymentsToAcquirePropertyPlantAndEquipment   <- 좁은 정의
    2) PaymentsToAcquireProductiveAssets            <- 넓은 정의
    3) PurchaseOfPropertyPlantAndEquipment...(ifrs)

우선순위라, 두 태그를 **모두** 보고하는 회사에서 1순위(좁은 정의)가 채택된다.
**소프트웨어 자본화를 별도 태그로 보고하는 회사에서 총 capex를 과소 포착한다.**

⚠️ 초판에서 나는 "ledger 시계열 내부에서 정의가 바뀐다"고 잠정 판단했다가
실제 ledger 값을 확인해 **기각**했다(내가 비교값을 잘못 옮겨 적은 것이 원인).
8/8 일치가 정답이며, 그 경위는 리포트에 남긴다.

## 이 스크립트가 하는 일

캐시된 SEC companyfacts로 34종목의 capex 태그 사용 패턴을 스캔해
`PaymentsToAcquireSoftware` / `PaymentsToAcquireProductiveAssets`를 함께
보고하는 종목을 찾고, ledger 값과 대조해 **좁은 정의 채택이 어디서 얼마나
발생하는지** 잰다. 네트워크를 다시 치지 않는다(캐시만 사용).

**ledger를 수정하지 않고 공식 판정을 바꾸지 않는다.**
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.filing_dates import ANNUAL_FORMS, _days_between  # noqa: E402
from scripts.sbc_harvest_2026_08_21 import CACHE_DIR, _load_ledgers  # noqa: E402

NARROW = "PaymentsToAcquirePropertyPlantAndEquipment"
SOFTWARE = "PaymentsToAcquireSoftware"
BROAD = "PaymentsToAcquireProductiveAssets"
TOL = 0.005          # ledger 손입력 반올림 허용


def _cached(ticker):
    p = os.path.join(CACHE_DIR, f"{ticker}.json")
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def _annual(facts, tag):
    """{회계연도: 최초공시 값}. 연간 구간(330~400일)만."""
    out = {}
    for _tax, d in (facts.get("facts") or {}).items():
        if tag not in d:
            continue
        for _unit, entries in (d[tag].get("units") or {}).items():
            for e in entries:
                if e.get("form") not in ANNUAL_FORMS:
                    continue
                s, en, fl, v = e.get("start"), e.get("end"), e.get("filed"), e.get("val")
                if not (s and en and fl) or v is None:
                    continue
                try:
                    if not 330 <= _days_between(s, en) <= 400:
                        continue
                except ValueError:
                    continue
                fy = int(en[:4])
                if fy not in out or fl < out[fy][1]:
                    out[fy] = (float(v), fl)
    return {y: v for y, (v, _) in out.items()}


def _match(a, b):
    if a is None or b is None or not b:
        return False
    return abs(a - b) / abs(b) <= TOL


def audit_ticker(ticker, ledger):
    facts = _cached(ticker)
    if facts is None:
        return {"ticker": ticker, "status": "NO_CACHE"}
    narrow, soft, broad = (_annual(facts, NARROW), _annual(facts, SOFTWARE),
                           _annual(facts, BROAD))
    led = {int(y): v for y, v in ledger["inputs"]["capex_by_year"].items()}

    per_year = []
    for y in sorted(led):
        n, s, b = narrow.get(y), soft.get(y), broad.get(y)
        combined = (n + s) if (n is not None and s is not None) else None
        # ledger 값이 어느 정의와 일치하는가
        if _match(led[y], combined):
            which = "narrow+software"
        elif _match(led[y], b):
            which = "broad"
        elif _match(led[y], n):
            which = "narrow"
        else:
            which = "none"
        per_year.append({
            "fy": y, "ledger": led[y], "narrow": n, "software": s, "broad": b,
            "ledger_matches": which,
            "provider_would_pick": n if n is not None else b,
        })

    picked = [p for p in per_year if p["provider_would_pick"] is not None]
    understated = [p for p in picked
                   if p["ledger"] > 0
                   and (p["ledger"] - p["provider_would_pick"]) / p["ledger"] > TOL]
    kinds = {p["ledger_matches"] for p in per_year}
    return {
        "ticker": ticker,
        "status": "OK",
        "reports_software_tag": bool(soft),
        "reports_broad_tag": bool(broad),
        "ledger_definition_kinds": sorted(kinds),
        "ledger_definition_consistent": len(kinds - {"none"}) <= 1,
        "years_checked": len(per_year),
        "years_provider_understates": len(understated),
        "max_understatement_pct": (
            max((p["ledger"] - p["provider_would_pick"]) / p["ledger"]
                for p in understated) if understated else 0.0),
        "per_year": per_year,
    }


def main():
    ledgers = _load_ledgers()
    rows = [audit_ticker(t, d) for t, (_fn, d) in sorted(ledgers.items())]
    ok = [r for r in rows if r["status"] == "OK"]
    no_cache = [r["ticker"] for r in rows if r["status"] == "NO_CACHE"]

    affected = [r for r in ok if r["years_provider_understates"] > 0]
    affected.sort(key=lambda r: -r["max_understatement_pct"])

    print(f"캐시 보유 {len(ok)}/{len(rows)}종목"
          + (f" · 캐시 없음: {no_cache}" if no_cache else ""))
    print("\nSEC provider가 ledger보다 capex를 과소 포착하는 종목")
    hdr = f"{'종목':6} {'과소연도':>8} {'최대과소':>9} {'SW태그':>7} {'넓은태그':>8} {'ledger 정의':>18}"
    print(hdr)
    print("-" * len(hdr))
    for r in affected:
        print(f"{r['ticker']:6} {r['years_provider_understates']:>4}/{r['years_checked']:<3} "
              f"{r['max_understatement_pct'] * 100:8.1f}% "
              f"{'Y' if r['reports_software_tag'] else '-':>7} "
              f"{'Y' if r['reports_broad_tag'] else '-':>8} "
              f"{','.join(r['ledger_definition_kinds']):>18}")
    if not affected:
        print("  (없음)")

    incons = [r for r in ok if not r["ledger_definition_consistent"]]
    print(f"\nledger capex 정의가 시계열 내부에서 갈리는 종목: "
          f"{[r['ticker'] for r in incons] or '없음'}")

    out = {
        "generated_at": "2026-08-21",
        "phase": "PHASE 3 — capex definition reconciliation",
        "affects_official_judgment": False,
        "root_cause": (
            "engine/data/providers/sec.py의 METRIC_TAGS['capex'] 우선순위가 "
            "PaymentsToAcquirePropertyPlantAndEquipment(좁은 정의)를 1순위로 두어, "
            "소프트웨어 자본화를 별도 태그로 보고하는 회사에서 총 자본지출을 "
            "과소 포착한다. ledger 쪽이 회사 보고 총액과 일치한다."
        ),
        "results": rows,
    }
    path = "reports/capex_definition_audit_2026-08-21.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"\n저장: {path}")


if __name__ == "__main__":
    main()
