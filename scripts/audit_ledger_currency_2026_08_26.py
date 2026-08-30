"""
ledger `meta.currency` 라벨 전수 감사 (2026-08-26, RQ-005 측정 중 우연히 발견)

## 발단

RQ-005(L2 후보 측정)에서 PDD·TCOM의 '재작성률'이 0.83~0.87로 극단적으로 높게
나왔다. 편차가 **정확히 629.9%**로 반복돼 확인해보니 재작성이 아니라
**같은 태그를 CNY와 USD 두 단위로 동시에 보고**하는 것을 내 탐지기가 합쳐서
비교한 것이었다(7.299 = 위안/달러 환율).

그 과정에서 별개의 문제가 드러났다 - **TCOM의 ledger는 값이 CNY인데
`meta.currency`가 "USD"로 적혀 있다.**

## 왜 중요한가 - 지금은 무해하지만 v3.67이 이걸 읽는다

Gap은 시총/FCF 비율에서 나오므로 **통화가 약분돼 판정에 영향이 없다**(실제로
TCOM Gap +7.55%p는 옳다). 문제는 v3.67 규모 조건부 성장상한이
`currency != "USD"`일 때만 `usd_fx_rate`로 환산한다는 것이다 - "USD"로 잘못
적힌 CNY 매출은 **7.3배 큰 기업으로 취급**돼 훨씬 엄격한 상한을 받는다.

TCOM ledger는 2026-08-04판이라 아직 v3.67을 통과한 적이 없다. 즉 **아직
피해는 없고, 다음 재실행 때 터진다** - 그때는 매수리스트 10.36%를 차지하는
종목의 성장상한이 단위 버그로 깎이면서 정당한 발견처럼 보일 것이다.

## 판별 방법 - 추측하지 않는다

SEC XBRL은 단위별로 값을 따로 담는다. ledger 값이 어느 단위 시계열과
일치하는지 **직접 대조**한다(1% 허용오차). 어느 쪽과도 안 맞으면 '판별불가'로
정직하게 남긴다 - 이 감사는 라벨을 고치는 근거를 만드는 것이지 빈칸을 채우는
게 아니다.
"""
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.measure_accrual_quality_2026_08_24 import ANNUAL_FORMS, _facts  # noqa: E402

REVENUE_TAGS = (
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "RevenueFromContractWithCustomerIncludingAssessedTax",
    "Revenues",
    "SalesRevenueNet",
    "RevenueFromContractsWithCustomers",
)
TOL = 0.01


def revenue_by_unit(facts):
    """단위별 연간 매출 시계열. **단위를 절대 합치지 않는다**(이번 사고의 원인)."""
    for tag in REVENUE_TAGS:
        for ns in ("us-gaap", "ifrs-full"):
            node = (facts.get("facts", {}).get(ns, {}) or {}).get(tag)
            if not node:
                continue
            out = {}
            for unit, rows in node.get("units", {}).items():
                for r in rows:
                    if r.get("form") not in ANNUAL_FORMS or not r.get("start"):
                        continue
                    days = (int(r["end"][:4]) * 365 + int(r["end"][5:7]) * 30
                            + int(r["end"][8:10])) - (
                           int(r["start"][:4]) * 365 + int(r["start"][5:7]) * 30
                           + int(r["start"][8:10]))
                    if not (330 <= days <= 400):
                        continue
                    out.setdefault(unit, {}).setdefault(int(r["end"][:4]), r["val"])
            if out:
                return out
    return {}


def match_unit(ledger_rev, by_unit):
    """ledger 매출이 어느 단위와 맞는지. 겹치는 해가 3개 미만이면 판별불가."""
    best = None
    for unit, series in by_unit.items():
        common = sorted(set(ledger_rev) & set(series))
        if len(common) < 3:
            continue
        ok = sum(1 for y in common
                 if series[y] and abs(ledger_rev[y] - series[y]) / abs(series[y]) < TOL)
        cand = {"unit": unit, "matched": ok, "compared": len(common)}
        if best is None or ok > best["matched"]:
            best = cand
    return best


def main():
    rows, mislabeled, undetermined = [], [], []
    for p in sorted(glob.glob("ledger/*.json")):
        d = json.load(open(p, encoding="utf-8"))
        t = d["meta"]["ticker"]
        declared = d["meta"].get("currency", "USD")
        rev = {int(k): float(v) for k, v in d["inputs"]["revenue_by_year"].items()}
        facts = _facts(t)
        if facts is None:
            undetermined.append((t, "CIK 매핑 실패"))
            continue
        by_unit = revenue_by_unit(facts)
        m = match_unit(rev, by_unit)
        if not m or m["matched"] < 3:
            undetermined.append((t, "SEC 단위 시계열과 3개년 이상 일치 없음"))
            rows.append({"ticker": t, "declared": declared, "detected": None,
                         "verdict": "판별불가", "units_available": sorted(by_unit)})
            continue
        detected = m["unit"]
        agree = (detected == declared)
        if not agree:
            mislabeled.append((t, declared, detected, m))
        rows.append({
            "ticker": t, "declared": declared, "detected": detected,
            "matched_years": m["matched"], "compared_years": m["compared"],
            "units_available": sorted(by_unit),
            "dual_reported": len(by_unit) > 1,
            "verdict": "일치" if agree else "라벨 불일치",
        })

    out = {
        "generated_at": "2026-08-26",
        "question": "ledger meta.currency 라벨이 실제 값의 통화와 맞는가",
        "method": "SEC XBRL 단위별 매출 시계열과 직접 대조(허용오차 1%, 최소 3개년)",
        "audit_only": "이 스크립트는 감사 전용 - ledger를 수정하지 않는다",
        "n": len(rows),
        "mislabeled": [{"ticker": t, "declared": d_, "detected": x} for t, d_, x, _ in mislabeled],
        "undetermined": undetermined,
        "rows": rows,
    }
    os.makedirs("reports", exist_ok=True)
    path = "reports/ledger_currency_audit_2026-08-26.json"
    json.dump(out, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    print(f"감사 {len(rows)}종목 -> {path}")
    dual = [r["ticker"] for r in rows if r.get("dual_reported")]
    print(f"복수통화 보고 종목: {dual or '없음'}")
    print(f"라벨 불일치: {len(mislabeled)}건")
    for t, dec, det, m in mislabeled:
        print(f"  ⚠️ {t}: 선언={dec} 실제={det} "
              f"({m['matched']}/{m['compared']}개년 일치)")
    print(f"판별불가: {len(undetermined)}건 " +
          (str([t for t, _ in undetermined]) if undetermined else ""))


if __name__ == "__main__":
    main()
