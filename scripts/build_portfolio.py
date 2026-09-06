"""
build_portfolio.py (2026-09-06) — 포트폴리오 계층의 유일한 진입점.

`engine/portfolio_pipeline.py`가 합친 로직(Stage 0-1 게이트 → Stage 2 G6 →
Stage 3 사이징 → 발행)을 실행해 `reports/buylist_<날짜>.json`을 쓴다.
`portfolio_screen_2026_09_05.py`/`build_conviction_portfolio_2026_09_05.py`/
`publish_buylist_2026_09_06.py` 세 단계를 손으로 순서대로 돌리던 것을 대체한다.

ledger가 새로 추가될 때마다(연구 큐에서 새 종목을 정식분석했을 때) 이 스크립트
하나만 다시 실행하면 된다 - `daily_screen_ci.py`/`update_research_queue.py`와
같은 성격의 **반복 실행 진입점**이다(날짜 붙은 일회성 스크립트가 아니다).

⚠️ **Stage 2 정성판단(g6_substitutes)·Confidence 조정치는 이 스크립트가 만들지
않는다** - `portfolio/qualitative_overrides.json`에 사람이 미리 적어둔 것만
읽는다. 새 Stage-1 생존종목에 그 항목이 없으면 크래시하지 않고 엔진 원시
Confidence로 폴백하며 `미검증`으로 표시한다 - 정성조사가 필요하다는 신호를
숨기지 않는다.

옛 스크립트(`build_buylist_2026_08_03.py` 등)는 손대지 않는다 - 날짜 붙은
스크립트는 재현성 아티팩트라는 이 프로젝트의 관행 그대로다.
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.portfolio import load_ledgers  # noqa: E402
from engine.portfolio_pipeline import (  # noqa: E402
    apply_g6,
    confirmed_falsifications,
    load_qualitative_overrides,
    load_sbc_verdicts,
    screen_universe,
    size_portfolio,
    to_buylist_rows,
)
from engine.monitor_state import load_acknowledgements  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORTS = os.path.join(ROOT, "reports")


def run(today: str | None = None) -> dict:
    today = today or datetime.date.today().isoformat()

    ledgers = load_ledgers()
    sbc_verdicts = load_sbc_verdicts()
    acks = load_acknowledgements()
    falsification_confirmed = confirmed_falsifications(acks)
    qual = load_qualitative_overrides()
    overrides, g6_subs = qual["overrides"], qual["g6_substitutes"]

    survivors, excluded_stage1 = screen_universe(
        ledgers, sbc_verdicts, falsification_confirmed, overrides)
    kept, excluded_g6 = apply_g6(survivors, g6_subs)
    sized = size_portfolio(kept, overrides)
    rows = to_buylist_rows(sized)

    n_unresearched = sum(1 for r in sized if r["confidence_status"] == "미검증")

    diagnostics = {
        "generated_at": today,
        "pipeline": "engine/portfolio_pipeline.py (Stage 0-1 게이트 -> Stage 2 G6 -> Stage 3 사이징)",
        "n_universe": len(survivors) + len(excluded_stage1),
        "n_stage1_survivors": len(survivors),
        "n_stage1_excluded": len(excluded_stage1),
        "n_g6_excluded": len(excluded_g6),
        "n_final": len(sized),
        "n_unresearched_in_final": n_unresearched,
        "not_provided": [
            "공분산 기반 최적화 (수익률 상관행렬이 이 저장소에 없다)",
            "군집 목표비중 (의도적 - PHASE 2 감사가 근거 없는 목표비중의 자본영향을 실측)",
            "실현수익률 검증 (관측 0건)",
            "Confidence의 확률적 해석 (VALIDATION_STATUS = UNCALIBRATED)",
        ],
        "stage1_excluded": [
            {k: v for k, v in r.items() if k != "flags"} for r in excluded_stage1
        ],
        "g6_excluded": [
            {k: v for k, v in r.items() if k != "flags"} for r in excluded_g6
        ],
        "positions": sized,
    }

    buylist_path = os.path.join(REPORTS, f"buylist_{today}.json")
    diag_path = os.path.join(REPORTS, f"portfolio_pipeline_{today}.json")

    payload = {
        "generated_at": today,
        "source": "engine/portfolio_pipeline.py",
        "n_positions": len(rows),
        "positions": rows,
    }
    with open(buylist_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    with open(diag_path, "w", encoding="utf-8") as f:
        json.dump(diagnostics, f, ensure_ascii=False, indent=2)

    return {
        "diagnostics": diagnostics,
        "buylist_path": buylist_path,
        "diag_path": diag_path,
    }


def main():
    ap = argparse.ArgumentParser(description="포트폴리오 계층 통합 진입점")
    ap.add_argument("--date", default=None, help="발행 날짜(기본: 오늘)")
    args = ap.parse_args()

    result = run(today=args.date)
    d = result["diagnostics"]

    print("=" * 100)
    print(f"S/A 유니버스 {d['n_universe']}종목 -> Stage1 생존 {d['n_stage1_survivors']} "
          f"-> Stage2(G6) 배제 {d['n_g6_excluded']} -> 최종 {d['n_final']}종목")
    print("=" * 100)

    for r in d["stage1_excluded"]:
        print(f"[Stage1 배제] {r['ticker']:6s} {r['grade']}  Gap {r['gap']*100:+7.2f}%p")
        for e in r["excluded_by"]:
            print(f"         └ {e}")

    for r in d["g6_excluded"]:
        g = r["g6"]
        print(f"[Stage2 배제] {r['ticker']:6s} {r['grade']}등급  Gap {r['gap']*100:+.2f}%p "
              f"-> 회사공시 대입 시 Gap {g['gap_at_company_growth']*100:+.2f}%p "
              f"-> {g['grade_at_company_growth']}등급")

    print(f"\n[최종 {d['n_final']}종목]")
    for r in d["positions"]:
        conf_flag = "" if r["confidence_status"] != "미검증" else "  ⚠️미검증"
        print(f"  {r['ticker']:6s} {r['cluster']:26s} {r['grade']:3s} "
              f"{r['gap_pct']:+8.2f}%p  conf={r['confidence_adj']:>3d}  "
              f"비중={r['weight']*100:6.2f}%{conf_flag}")

    if d["n_unresearched_in_final"]:
        print(f"\n⚠️ {d['n_unresearched_in_final']}종목이 정성 심층조사 없이 "
              f"엔진 원시 Confidence로 편입됐다 - portfolio/qualitative_overrides.json에 "
              f"항목을 채울 것.")

    print(f"\n저장: {os.path.relpath(result['buylist_path'], ROOT)}")
    print(f"저장: {os.path.relpath(result['diag_path'], ROOT)}")


if __name__ == "__main__":
    main()
