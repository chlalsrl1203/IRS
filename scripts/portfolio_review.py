"""
포트폴리오 점검 실행 - `engine/portfolio.py`를 돌려 리포트를 낸다.

실행:
    python3 scripts/portfolio_review.py               # 오늘 기준
    python3 scripts/portfolio_review.py 2026-09-05    # 날짜 지정

산출물: reports/portfolio_review_<날짜>.json

⚠️ 이 스크립트는 `ledger/`·`portfolio/holdings.json` 어느 쪽에도 쓰지 않는다.
"""
import json
import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.portfolio import review_portfolio

BAR = "─" * 78


def main(argv) -> int:
    today = argv[1] if len(argv) > 1 else date.today().isoformat()
    r = review_portfolio(today)

    cov = r["coverage"]
    print(BAR)
    print(f"포트폴리오 점검 {today}   (보유 기준일 {r['holdings_as_of']}, "
          f"{r['n_positions']}종목)")
    print(BAR)
    print(f"유효 판정 커버리지: {cov['positions_with_judgment']}/{r['n_positions']}종목, "
          f"비중 {cov['weight_with_judgment']*100:.1f}%  "
          f"(판정 없음 {cov['weight_without_judgment']*100:.1f}%)")
    print(f"등급 분포: " + "  ".join(
        f"{g}:{','.join(v)}" for g, v in r["grade_distribution"].items()))
    print()

    print(f"{'티커':<6}{'비중':>7}{'수익률':>8}{'Gap':>10}{'등급':>4}"
          f"{'Conf':>5}{'경과':>6}  플래그")
    for p in r["positions"]:
        gap = f"{p['expectation_gap']*100:+.2f}%p" if p["expectation_gap"] is not None else "-"
        grade = p["grade"] or "-"
        conf = p["confidence"] if p["confidence"] is not None else "-"
        age = f"{p['age_days']}d" if p["age_days"] is not None else "-"
        ret = f"{p['return_pct']:+.1f}%" if p["return_pct"] is not None else "-"
        codes = ",".join(f["code"] for f in p["flags"]) or "-"
        print(f"{p['ticker']:<6}{p['weight']*100:>6.2f}%{ret:>8}{gap:>10}"
              f"{grade:>4}{str(conf):>5}{age:>6}  {codes}")

    print()
    print("검토 우선순위(플래그 수 -> 비중 순, 합성 점수 아님):")
    for i, q in enumerate(r["review_queue"], 1):
        if q["n_flags"] == 0:
            continue
        print(f"  {i}. {q['ticker']:<6} 비중 {q['weight']*100:>5.2f}%  "
              f"플래그 {q['n_flags']}건: {', '.join(q['flags'])}")

    print()
    cands = r["unheld_sa_candidates"]
    print(f"미보유 S/A 후보 {len(cands)}종목(엔진 판정 기준, 매수 권고 아님):")
    for c in cands:
        notes = []
        if c["sbc_flip"]:
            notes.append("SBC뒤집힘")
        if c["growth_cap_binding"]:
            notes.append("성장상한바인딩")
        if (c["model_divergence"] or 0) >= 0.03:
            notes.append(f"모델괴리{c['model_divergence']*100:.1f}%p")
        print(f"  {c['grade']} {c['ticker']:<6} Gap {c['expectation_gap']*100:>+7.2f}%p  "
              f"Conf {c['confidence']}  {c['analyzed_at']}  "
              f"{'· '.join(notes) if notes else ''}")

    print()
    print("⚠️ 이 리포트가 제공하지 않는 것:")
    for x in r["not_provided"]:
        print(f"  - {x}")
    print(f"⚠️ 플래그 규칙 상태: {r['rule_status']}")

    out = f"reports/portfolio_review_{today}.json"
    os.makedirs("reports", exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(r, f, ensure_ascii=False, indent=2)
    print(f"\nsaved: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
