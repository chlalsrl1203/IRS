"""
RQ-004 축0 Layer1: ledger vs SEC 불일치의 **원인을 분류**한다 (2026-08-25)

## 왜 이게 축0의 최우선인가

축0은 두 층이다:
  Layer 1  숫자가 **맞는가**        <- 여기가 미해결이었다
  Layer 2  숫자를 **믿어도 되는가**  <- v3.70 발생액이 첫 지표

Layer 1이 깨져 있으면 Layer 2는 모래 위에 짓는 것이다. capex는 FCF -> fcf0 ->
Implied Growth -> Gap -> 판정으로, operating_income은 margin_volatility -> DRS로
직결된다.

## 기존 감사(P0-07)가 남긴 것

2026-08-19 P0-07은 **8종목만** 대조했고(34종목 전수 아님) 336개 값 중 **67개가
미해결**로 남았다. PHASE 3(v3.60)이 그중 MCK 유형 하나(넓은/좁은 capex 태그)를
규명했지만, 나머지는 "원인이 다르며 범위 밖"으로 미뤄졌다.

**미해결로 두면 안 되는 이유**: `requires_review=True`는 "어느 쪽이 맞는지 아직
안 정했다"는 뜻이다. 정하지 않은 채로 ledger 값이 계속 판정을 만들고 있다.

## 이 스크립트가 하는 일 - 원인 가설을 하나씩 기계적으로 검정한다

불일치를 그냥 세지 않고 **왜 다른지**를 분류한다:

  A. 회계연도 라벨 시프트  ledger[Y] == SEC[Y±1] 인가?
     -> 52/53주 회계연도에서 `int(end[:4])`가 오라벨하는 v3.61 결함.
        CDNS 실측: ledger FY2015 44,808 == SEC FY2016 44,808 (정확히 일치)

  B. 태그 정의 차이        ledger == 좁은태그 + 소프트웨어자본화 인가?
                          ledger == 넓은태그 인가?
     -> PHASE 3(v3.60)이 MCK에서 규명한 유형. 소프트웨어 기업(GWRE 등)은
        `PaymentsToAcquirePropertyPlantAndEquipment`에 자본화 소프트웨어가 빠진다.

  C. 재작성(restatement)   ledger == 더 이른 제출본의 값인가?
     -> PHASE 5 실측상 복수공시 기간 1,566건 중 133건(8.5%)이 재작성됐다.

  D. 원인 미상             위 셋 다 아니면 정직하게 남긴다.

**ledger를 수정하지 않는다.** 원인 분류와 판정 영향 측정만 한다 - 어느 쪽을
채택할지는 원인을 알고 난 뒤의 별도 결정이다(P0-07 원칙 유지).
"""
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.measure_accrual_quality_2026_08_24 import _facts

ANNUAL_FORMS = ("10-K", "10-K/A", "20-F", "20-F/A", "40-F")

# 대조할 지표와 그 SEC 태그 후보들. capex는 정의가 여럿이라 **전부** 뽑아서
# 어느 정의가 ledger와 맞는지 본다(PHASE 3가 MCK에서 쓴 방법).
TAGS = {
    "revenue": {
        "primary": ("RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues",
                    "RevenueFromContractWithCustomerIncludingAssessedTax",
                    "SalesRevenueNet", "Revenue"),
    },
    "operating_income": {
        "primary": ("OperatingIncomeLoss", "ProfitLossFromOperatingActivities"),
    },
    "operating_cashflow": {
        "primary": ("NetCashProvidedByUsedInOperatingActivities",
                    "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations",
                    "CashFlowsFromUsedInOperatingActivities"),
    },
    "capex": {
        "primary": ("PaymentsToAcquireProductiveAssets",
                    "PaymentsToAcquirePropertyPlantAndEquipment"),
        "narrow": ("PaymentsToAcquirePropertyPlantAndEquipment",),
        "broad": ("PaymentsToAcquireProductiveAssets",),
        "software": ("PaymentsToAcquireSoftware",
                     "PaymentsToDevelopSoftware",
                     "PaymentsForSoftware",
                     "PaymentsToAcquireIntangibleAssets"),
    },
}

MATERIAL = 0.05     # 상대편차 5% 초과를 물질적 불일치로 본다(P0-07과 동일)
TOL = 0.005         # 가설 검정 허용오차 0.5% - 반올림·단위표기 차이 흡수


def series(facts, tags, earliest=False):
    """
    회계연도별 값. earliest=True면 **최초 제출본**(재작성 이전),
    False면 최신 제출본(재작성 반영).
    """
    for tag in tags:
        for ns in ("us-gaap", "ifrs-full"):
            node = (facts.get("facts", {}).get(ns, {}) or {}).get(tag)
            if not node:
                continue
            out = {}
            for rows in node.get("units", {}).values():
                for r in rows:
                    if r.get("form") not in ANNUAL_FORMS or not r.get("end"):
                        continue
                    if r.get("start"):
                        d = _days(r["start"], r["end"])
                        if not (330 <= d <= 400):
                            continue
                    y = int(r["end"][:4])
                    f = r.get("filed", "")
                    if y not in out:
                        out[y] = (r["val"], f)
                    else:
                        better = f < out[y][1] if earliest else f > out[y][1]
                        if better:
                            out[y] = (r["val"], f)
            if out:
                return {y: v for y, (v, _) in out.items()}
    return {}


def _days(a, b):
    return ((int(b[:4]) * 365 + int(b[5:7]) * 30 + int(b[8:10]))
            - (int(a[:4]) * 365 + int(a[5:7]) * 30 + int(a[8:10])))


def close(a, b, tol=TOL):
    if a is None or b is None:
        return False
    if a == 0 or b == 0:
        return a == b
    return abs(a - b) / max(abs(a), abs(b)) <= tol


def classify(metric, year, led_val, facts, is_insurer=False):
    """불일치 하나의 원인을 가설별로 검정한다. 순서가 중요하다(구체적인 것부터)."""
    cfg = TAGS[metric]
    latest = series(facts, cfg["primary"])
    sec_val = latest.get(year)

    if sec_val is not None:
        rel = abs(led_val - sec_val) / max(abs(led_val), abs(sec_val), 1e-9)
        if rel <= MATERIAL:
            return "일치", {"rel_diff": rel}

    # ── 가설 A: 회계연도 라벨 시프트 ────────────────────────────────────
    # ⚠️ **SEC 값이 결측일 때도 반드시 검정한다.** v3.61이 실측한 라벨 충돌은
    # 두 기간이 같은 라벨을 다투다 한쪽이 **조용히 사라지는** 형태다 - 즉
    # 결측 자체가 시프트의 증상일 수 있다. 초판은 결측이면 바로 반환해서
    # 이 경우를 통째로 놓쳤다(CDNS에서 발견).
    for shift in (1, -1):
        if close(led_val, latest.get(year + shift)):
            return "A_라벨시프트", {
                "shift": shift, "sec_year_matched": year + shift,
                "sec_value": latest.get(year + shift),
                "sec_missing_at_year": sec_val is None,
                "note": f"ledger FY{year} == SEC FY{year+shift} (52/53주 회계연도 오라벨)"}

    # ── 가설 F: 업종 구조상 그 태그를 쓰지 않음 ─────────────────────────
    # 보험사는 `OperatingIncomeLoss`를 보고하지 않는다 - 손익계산서 구조 자체가
    # 다르다(수입보험료·발생손해·언더라이팅손익). 결측 56건 중 34건이 보험·
    # 보험중개 3사(BRO·ACGL·PGR)에 몰려 있다. **결함이 아니라 구조**다.
    if sec_val is None and metric == "operating_income" and is_insurer:
        return "F_업종구조", {
            "note": "보험업은 OperatingIncomeLoss를 보고하지 않는다(구조적, 결함 아님)"}

    if sec_val is None:
        return "SEC_결측", {"note": f"SEC에 FY{year} 값이 없고 인접연도와도 불일치"}

    # ── 가설 B: 태그 정의 차이 ──────────────────────────────────────────
    if metric == "capex":
        narrow = series(facts, cfg["narrow"]).get(year)
        broad = series(facts, cfg["broad"]).get(year)
        soft = series(facts, cfg["software"]).get(year)
        if close(led_val, broad):
            return "B_태그정의", {"matched": "broad", "sec_value": broad,
                                  "note": "ledger는 넓은 정의(생산자산 취득)와 일치"}
        if narrow is not None and soft is not None and close(led_val, narrow + soft):
            return "B_태그정의", {"matched": "narrow+software", "narrow": narrow,
                                  "software": soft,
                                  "note": "ledger는 유형자산 + 자본화 소프트웨어 합계와 일치"}
        if close(led_val, narrow):
            return "B_태그정의", {"matched": "narrow", "sec_value": narrow,
                                  "note": "ledger는 좁은 정의와 일치(provider가 넓은 정의 채택 중)"}

    # ── 가설 C: 재작성 ──────────────────────────────────────────────────
    first = series(facts, cfg["primary"], earliest=True).get(year)
    if first is not None and not close(first, sec_val) and close(led_val, first):
        return "C_재작성", {"first_filed_value": first, "restated_value": sec_val,
                            "note": "ledger는 최초 공시본과 일치 - 이후 재작성됨"}

    # ── 가설 E: 벤더 정규화(일회성 항목 제외) 의심 ─────────────────────
    # BSX FY2015 실측: ledger +790M vs SEC **−283M**. 부호가 반대다 - 2015년
    # 대규모 소송충당금이 SEC(GAAP)에만 반영됐다는 뜻이고, ledger(벤더)는
    # 일회성을 제외한 정규화 영업이익을 쓰고 있다는 신호다.
    # ⚠️ **확정이 아니라 의심**이다 - 벤더 산출 방식을 직접 확인한 바 없다.
    if metric == "operating_income":
        if led_val * sec_val < 0:
            return "E_정규화의심", {"ledger": led_val, "sec_latest": sec_val,
                                    "pattern": "부호반대",
                                    "note": "일회성 손실이 SEC(GAAP)에만 반영된 형태"}
        if abs(led_val) > abs(sec_val):
            return "E_정규화의심", {"ledger": led_val, "sec_latest": sec_val,
                                    "pattern": "ledger가 큼",
                                    "note": "ledger가 비용을 덜 반영한 형태(정규화 방향과 일치)"}

    rel = abs(led_val - sec_val) / max(abs(led_val), abs(sec_val), 1e-9)
    return "D_원인미상", {"ledger": led_val, "sec_latest": sec_val,
                          "rel_diff": rel}


def main():
    ledgers = {}
    for p in glob.glob("ledger/*.json"):
        d = json.load(open(p, encoding="utf-8"))
        ledgers[d["meta"]["ticker"]] = d

    per_ticker, tally, failures = [], {}, []
    for t in sorted(ledgers):
        facts = _facts(t)
        if facts is None:
            failures.append((t, "CIK 매핑 실패"))
            continue
        inp = ledgers[t]["inputs"]
        is_insurer = bool(inp.get("is_insurer")) or bool(ledgers[t].get("insurer_cross_check"))
        rows = []
        for metric, key in [("revenue", "revenue_by_year"),
                            ("operating_income", "operating_income_by_year"),
                            ("operating_cashflow", "operating_cashflow_by_year"),
                            ("capex", "capex_by_year")]:
            led = inp.get(key) or {}
            for y_s, v in led.items():
                y = int(y_s)
                cause, detail = classify(metric, y, float(v), facts, is_insurer)
                tally[cause] = tally.get(cause, 0) + 1
                if cause != "일치":
                    rows.append({"metric": metric, "fiscal_year": y,
                                 "ledger_value": float(v), "cause": cause,
                                 **detail})
        per_ticker.append({"ticker": t, "n_mismatch": len(rows), "mismatches": rows})

    total = sum(tally.values())
    out = {
        "generated_at": "2026-08-25",
        "research_question": "RQ-004: ledger vs SEC 불일치의 원인 분류(34종목 전수)",
        "scope_vs_prior": "P0-07은 8종목만 대조했다 - 이번은 34종목 전수",
        "modifies_ledger": False,
        "n_tickers": len(per_ticker), "n_values": total,
        "cause_tally": dict(sorted(tally.items(), key=lambda kv: -kv[1])),
        "failures": failures,
        "by_ticker": sorted(per_ticker, key=lambda r: -r["n_mismatch"]),
    }
    os.makedirs("reports/research", exist_ok=True)
    path = "reports/research/RQ-004_reconcile_root_cause_2026-08-25.json"
    json.dump(out, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    print(f"=== 34종목 전수 원인분류: 값 {total}개 ===")
    for c, n in out["cause_tally"].items():
        print(f"  {c:16} {n:4}  ({n/total*100:5.1f}%)")
    print(f"\n불일치 상위 종목:")
    for r in out["by_ticker"][:8]:
        if r["n_mismatch"]:
            cs = {}
            for m in r["mismatches"]:
                cs[m["cause"]] = cs.get(m["cause"], 0) + 1
            print(f"  {r['ticker']:6} {r['n_mismatch']:3}건  {cs}")
    print(f"\n-> {path}")


if __name__ == "__main__":
    main()
