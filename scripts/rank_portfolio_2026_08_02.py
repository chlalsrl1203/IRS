"""
전체 종목 재순위 - 2026-08-02.

경위: 기존 3단계 판정(저평가/적정가/과대평가, ±5%p 경계)이 "저평가 가능성"
한 칸에 33종목 중 17개(52%)를 몰아넣어 PDD(+29.16%p)와 BSY(+5.70%p)를
구분하지 못했다. v3.27에서 judgment_grade_from_gap()을 엔진에 배선해
기존 3단계 경계(±5%p)를 그대로 유지한 채 6단계(S/A/B/C/D/F)로 세분화했다
(engine/expectation_gap_engine.py 참고 - 근거·경계값 설정 이유 전부 문서화됨).

이 스크립트는 순수 함수(judgment_grade_from_gap)로 기존 ledger를 재실행 없이
소급 재순위한다 - Gap 자체는 바뀌지 않으므로 엔진 재실행이 필요 없다.

실행: python3 scripts/rank_portfolio_2026_08_02.py
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.expectation_gap_engine import JUDGMENT_GRADE_LABELS, judgment_grade_from_gap

GRADE_ORDER = {"S": 0, "A": 1, "B": 2, "C": 3, "D": 4, "F": 5}


def load_latest_ledgers(ledger_dir="ledger"):
    latest = {}
    for fname in sorted(os.listdir(ledger_dir)):
        if not fname.endswith(".json"):
            continue
        d = json.load(open(os.path.join(ledger_dir, fname)))
        ticker = d["meta"]["ticker"]
        date = d["meta"]["analyzed_at"][:10]
        if ticker not in latest or date > latest[ticker][0]:
            latest[ticker] = (date, d)
    return {t: d for t, (date, d) in latest.items()}


def build_ranking(ledgers: dict) -> list:
    rows = []
    for ticker, d in ledgers.items():
        gap = d["expectation_gap"]
        grade = judgment_grade_from_gap(gap)
        rows.append({
            "ticker": ticker,
            "company_name": d["meta"]["company_name"],
            "grade": grade,
            "grade_label": JUDGMENT_GRADE_LABELS[grade],
            "judgment": d["judgment"],
            "gap_pct": gap * 100,
            "realistic_growth_pct": d["growth"]["realistic_growth"] * 100,
            "implied_growth_pct": d["implied_growth"]["value"] * 100,
            "drs": d["drs"]["score"],
            "rar": d["rar"],
            "confidence": d["confidence"]["final"],
            "robust": not d["sensitivity_check"].get("judgment_flipped"),
            "cap_bound": d["growth"]["breakdown"]["cap_applied"] is not None,
            "lynch_type": d["lynch"]["used"],
            "analyzed_at": d["meta"]["analyzed_at"][:10],
        })
    rows.sort(key=lambda r: (GRADE_ORDER[r["grade"]], -r["gap_pct"]))
    return rows


def format_table(rows: list) -> str:
    lines = []
    header = (f"{'#':>3} {'등급':^4} {'종목':6} {'Gap':>9} {'현실성장':>9} "
              f"{'내재성장':>9} {'DRS':>6} {'RAR':>9} {'Conf':>5} {'강건':>5} "
              f"{'캡바인딩':>7} {'Lynch':10} 판정(3단계)")
    lines.append(header)
    lines.append("-" * len(header))
    for i, r in enumerate(rows, 1):
        lines.append(
            f"{i:3} {r['grade']:^4} {r['ticker']:6} {r['gap_pct']:+8.2f}%p "
            f"{r['realistic_growth_pct']:8.2f}% {r['implied_growth_pct']:8.2f}% "
            f"{r['drs']:6.1f} {r['rar']:+9.4f} {r['confidence']:5} "
            f"{'Y' if r['robust'] else 'N':>5} {'Y' if r['cap_bound'] else '':>7} "
            f"{r['lynch_type']:10} {r['judgment']}"
        )
    return "\n".join(lines)


def main():
    ledgers = load_latest_ledgers()
    rows = build_ranking(ledgers)

    print("=" * 130)
    print(f"전체 종목 재순위 ({len(rows)}종목, judgment_grade v3.27 기준, 2026-08-02)")
    print("=" * 130)
    print(format_table(rows))
    print()

    from collections import Counter
    grade_counts = Counter(r["grade"] for r in rows)
    print("등급 분포:")
    for g in ["S", "A", "B", "C", "D", "F"]:
        n = grade_counts.get(g, 0)
        print(f"  {g}({JUDGMENT_GRADE_LABELS[g]:8}): {n:2}종목")

    out_path = "reports/portfolio_ranking_2026-08-02.json"
    os.makedirs("reports", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
    print(f"\n결과 저장: {out_path}")

    return rows


if __name__ == "__main__":
    main()
