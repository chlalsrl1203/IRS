"""
RQ-005 측정: 축0 L2(회계 품질) 두 번째·세 번째 후보 (2026-08-26)

## 무엇을 묻는가

L1(데이터 정확성)은 RQ-004에서 원인 전수 규명까지 끝냈고, L2(회계 품질)에는
지금 **발생액 하나뿐**이다(v3.70). 후보 둘을 G1~G8 관문에 태운다:

  ① **AR/매출 추세** — 매출이 현금회수보다 빨리 늘고 있는가(매출인식 공격성)
  ② **재작성 이력** — 이 회사가 과거에 숫자를 얼마나 자주 고쳤는가

⚠️ **새 지표는 방금 채택한 발생액과도 독립이어야 한다.** RQ-003에서 순진한
발생액이 SBC 강도를 재는 아티팩트였던 것처럼, AR 추세도 발생액의 한 성분일
수 있다(외상매출 증가는 발생액을 구성한다). G5 컷을 실행 **전에** 고정한다:
  |rho| >= 0.7 중복 -> REJECT / 0.4~0.7 부분중복 -> 재설계 후 재측정 / < 0.4 독립

## 외부 근거 - 검증 수준을 구분해 기록한다

① AR/매출: 외상매출 증가는 **운전자본 발생액의 주요 구성요소**이며, Sloan(1996)
   이 지속성이 낮다고 본 발생액 성분에 포함된다. Beneish(1999) M-score의
   DSRI(Days Sales in Receivables Index)가 정확히 같은 구성을 쓰지만,
   **원문 계산식을 직접 검증하지 못했으므로 특정 공식을 인용하지 않고**
   원자료 비율(AR/Revenue)과 그 추세만 낸다. 합성 M-score는 §31 안티기능
   등록부(단일 합성점수)에 걸려 어차피 만들지 않는다.

② 재작성: 외부 문헌이 필요 없는 **직접 관측 사실**이다. SEC XBRL은 같은
   (태그, 기간)을 여러 공시가 각각 보고하므로, 값이 달라진 기간을 세면
   그 회사가 과거 숫자를 고친 빈도가 그대로 나온다. PHASE 5(2026-08-21)가
   전체 1,566개 기간 중 133개(8.5%)를 이미 이 방식으로 셌다 - 이번엔 그걸
   **종목별 비율**로 분해한다.

## 측정 전용

`engine/`·`ledger/`를 건드리지 않는다. 채택 여부는 측정 후에 결정한다.
"""
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.accounting_quality import (  # noqa: E402
    accrual_ratio_series,
    ar_to_revenue_trend,
)
from engine.data.providers.sec import restatement_profile  # noqa: E402
from scripts.measure_accrual_quality_2026_08_24 import (  # noqa: E402
    ANNUAL_FORMS,
    EXTRA_TAGS,
    _facts,
    annual_series,
)

# G5 컷 - **실행 전에 고정한다**(결과를 보고 옮기지 않는다).
REDUNDANT = 0.70
PARTIAL = 0.40

AR_TAGS = (
    "AccountsReceivableNetCurrent",
    "AccountsReceivableGrossCurrent",
    "ReceivablesNetCurrent",
    "AccountsAndOtherReceivablesNetCurrent",
    "AccountsReceivableNet",
    "TradeAndOtherCurrentReceivables",
)
REVENUE_TAGS = (
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "RevenueFromContractWithCustomerIncludingAssessedTax",
    "Revenues",
    "SalesRevenueNet",
    "RevenueFromContractsWithCustomers",
)
SBC_TAGS = ("ShareBasedCompensation", "AllocatedShareBasedCompensationExpense")

# ⚠️ 재작성 탐지의 대상지표·임계값·실체변경 컷은 전부 엔진
# (`engine/data/providers/sec.py`)에 있다 - 여기서 다시 정의하지 않는다.

# ── 통계 (stdlib만, 의존성 0 원칙) ──────────────────────────────────────
def _rank(xs):
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    ranks = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        avg = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    return ranks


def spearman(pairs):
    """(x, y) 쌍에서 순위상관. 표본 3 미만이면 None."""
    pairs = [(a, b) for a, b in pairs if a is not None and b is not None]
    if len(pairs) < 3:
        return None, len(pairs)
    rx = _rank([p[0] for p in pairs])
    ry = _rank([p[1] for p in pairs])
    n = len(pairs)
    mx, my = sum(rx) / n, sum(ry) / n
    num = sum((rx[i] - mx) * (ry[i] - my) for i in range(n))
    dx = sum((rx[i] - mx) ** 2 for i in range(n)) ** 0.5
    dy = sum((ry[i] - my) ** 2 for i in range(n)) ** 0.5
    if dx == 0 or dy == 0:
        return None, n
    return num / (dx * dy), n


# ── 후보 ①·② — **엔진 함수를 그대로 부른다** ──────────────────────────
#
# 초판은 이 스크립트 안에 두 지표를 따로 구현했다가, 채택 후 엔진 구현과
# 숫자가 갈렸다(VRT 재작성률 0.217 vs 0.105 - 대상 지표와 태그 우선순위가
# 달랐다). 리포트가 엔진을 재현하지 못하면 둘 중 어느 쪽이 사실인지 알 수
# 없다. Simplicity First가 반복 경고한 "중복 구현이 두 계산을 미묘하게
# 어긋나게 만든다"가 그대로 재현된 셈이라, 스크립트 사본을 지우고 엔진을
# 호출한다. AR 원계열 추출만 여기 남는다(엔진은 순수 dict만 받는다).
def ar_series(facts):
    """AR·매출 원계열을 뽑아 엔진 `ar_to_revenue_trend`에 넘긴다."""
    ar = annual_series(facts, AR_TAGS)
    rev = annual_series(facts, REVENUE_TAGS)
    if not ar or not rev:
        return None
    return ar_to_revenue_trend(ar, rev)


def main():
    ledgers = {}
    for p in glob.glob("ledger/*.json"):
        d = json.load(open(p, encoding="utf-8"))
        ledgers[d["meta"]["ticker"]] = d

    rows, skipped = [], []
    for t in sorted(ledgers):
        facts = _facts(t)
        if facts is None:
            skipped.append((t, "CIK 매핑 실패"))
            continue
        led = ledgers[t]

        ar = ar_series(facts)
        rs = restatement_profile(facts)

        # 이미 채택된 발생액(SBC 되돌린 형태)도 같이 재현해 독립성을 검사한다.
        ni = annual_series(facts, EXTRA_TAGS["net_income"])
        ocf = annual_series(facts, EXTRA_TAGS["operating_cashflow"])
        ta = annual_series(facts, EXTRA_TAGS["assets"])
        sbc = annual_series(facts, SBC_TAGS)
        accr = None
        if ni and ocf and ta:
            try:
                s = accrual_ratio_series(ni, ocf, ta, sbc or None)
                if s:
                    accr = s[max(s)]
            except ValueError:
                pass

        rows.append({
            "ticker": t,
            # 후보 ①
            "ar_to_revenue_latest": ar["latest"] if ar else None,
            "ar_trend_slope": ar["trend_slope_pp"] if ar else None,
            "ar_trend_relative": ar["trend_relative"] if ar else None,
            "ar_mean_level": ar["mean_level"] if ar else None,
            "ar_notes": ar["notes"] if ar else [],
            # 후보 ②
            "restatement_rate": rs["restatement_rate"],
            "restated_periods": rs["restated_periods"],
            "multi_filed_periods": rs["multi_filed_periods"],
            "worst_restatement": rs["worst_deviation"],
            "has_material_restatement": rs["has_material_restatement"],
            "restatement_detail": rs["restatements"][:5],
            "entity_or_unit_changes": len(rs["entity_or_unit_changes"]),
            "entity_detail": rs["entity_or_unit_changes"][:3],
            # 기존 지표(중복 검사 대상)
            "accrual_ratio": accr,
            "gap": led["expectation_gap"],
            "drs": led["drs"]["score"],
            "realistic_growth": led["growth"]["realistic_growth"],
            "margin_volatility": led["drs"]["components"].get("margin_volatility"),
            "revenue_volatility": led["drs"]["components"].get("revenue_volatility"),
            "sbc_to_fcf": (led.get("sbc_cross_check") or {}).get("sbc_to_fcf_pct"),
        })

    # ── G5: 기존 지표와의 중복 검사 ────────────────────────────────────
    existing = ["accrual_ratio", "gap", "drs", "realistic_growth",
                "margin_volatility", "revenue_volatility", "sbc_to_fcf"]
    corr = {}
    for cand in ("ar_trend_relative", "ar_trend_slope", "ar_to_revenue_latest",
                 "restatement_rate"):
        corr[cand] = {}
        for ex in existing:
            rho, n = spearman([(r[cand], r[ex]) for r in rows])
            verdict = ("표본부족" if rho is None else
                       "중복" if abs(rho) >= REDUNDANT else
                       "부분중복" if abs(rho) >= PARTIAL else "독립")
            corr[cand][ex] = {"rho": rho, "n": n, "verdict": verdict}

    # 두 후보끼리도 독립인지(둘 다 채택할 근거가 되는지) 확인
    rho, n = spearman([(r["ar_trend_relative"], r["restatement_rate"]) for r in rows])
    corr["_between_candidates"] = {"ar_trend_vs_restatement": {"rho": rho, "n": n}}

    def _cov(k):
        return sum(1 for r in rows if r[k] is not None)

    out = {
        "generated_at": "2026-08-26",
        "research_question": (
            "RQ-005: AR/매출 추세와 재작성 이력이 IRS에 증분 정보를 주는가"),
        "measurement_only": "engine/·ledger/를 건드리지 않는다",
        "g5_cut_fixed_before_run": {
            "redundant_reject": REDUNDANT, "partial": PARTIAL,
            "note": "결과를 보고 컷을 옮기지 않는다",
        },
        "coverage": {
            "n": len(rows),
            "ar_trend_relative": _cov("ar_trend_relative"),
            "restatement_rate": _cov("restatement_rate"),
            "accrual_ratio": _cov("accrual_ratio"),
        },
        "skipped": skipped,
        "correlations": corr,
        "rows": rows,
    }
    os.makedirs("reports/research", exist_ok=True)
    path = "reports/research/RQ-005_l2_candidates_2026-08-26.json"
    json.dump(out, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    print(f"측정 {len(rows)}종목 -> {path}")
    print(f"커버리지: AR추세 {_cov('ar_trend_relative')}/{len(rows)}, "
          f"재작성 {_cov('restatement_rate')}/{len(rows)}, "
          f"발생액 {_cov('accrual_ratio')}/{len(rows)}")
    print("\n=== G5: 기존 지표와의 순위상관 ===")
    for cand in ("ar_trend_relative", "ar_trend_slope", "ar_to_revenue_latest",
                 "restatement_rate"):
        print(f"\n[{cand}]")
        for ex in existing:
            c = corr[cand][ex]
            r = "  n/a " if c["rho"] is None else f"{c['rho']:+.3f}"
            print(f"  vs {ex:20s} rho={r} (n={c['n']:2d}) {c['verdict']}")
    c = corr["_between_candidates"]["ar_trend_vs_restatement"]
    shown = "n/a" if c["rho"] is None else f"{c['rho']:+.3f}"
    print(f"\n후보끼리: AR추세 vs 재작성 rho={shown} (n={c['n']})")


if __name__ == "__main__":
    main()
