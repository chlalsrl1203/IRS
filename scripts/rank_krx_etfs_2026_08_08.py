"""
국내 상장 ETF 전체 재순위 - 2026-08-08 (판별력 복구).

경위: 25종목을 담았지만 **전부 "적정가/경계선"**이었다 - Gap 기준 판별력이
사실상 0이다. 이건 우연이 아니라 v3.34가 이미 자체진단한 구조적 결함의
재현이다: Gap = 주관적 가정성장률 - 내재성장률인데, 25종목 각각의
가정성장률(4~12%)을 분석자가 섹터 통념으로 골랐기 때문에 애초에 판정
경계(±5%p) 안쪽으로 들어오도록 스스로 보정된 값이나 마찬가지다.

v3.34가 이미 처방한 해법을 여기서도 그대로 쓴다 - **Gap으로 순위를 매기지
않고, `required_growth.breakeven`(시장이 이미 요구하고 있는 성장률 - P/E와
r만으로 결정되어 분석자 주관이 개입할 수 없는 유일한 객관적 비교축)으로
순위를 매긴다.** breakeven이 낮을수록 "이 정도 성장만 실현돼도 저평가가
된다"는 뜻이고, 높을수록 "시장이 이미 낙관을 가격에 반영했다"는 뜻이다 -
이건 종목 간에 정직하게 비교 가능하다(같은 P/E-r 공식이 전부에 동일하게
적용되므로).

⚠️ 이 순위 자체를 "낮을수록 사라"로 곧바로 읽으면 안 된다 - breakeven이
낮다는 건 그 섹터가 실제로 그 성장률조차 못 낼 수도 있다는 뜻일 수 있다
(예: 에너지 섹터는 breakeven이 낮아도 실제 성장이 마이너스로 갈 수 있다).
이 표는 "각 섹터가 시장의 어떤 기대를 뛰어넘어야 하는가"를 보여줄 뿐,
그 기대를 실제로 넘을지는 분석자가 섹터 지식으로 판단해야 한다.

여러 P/E 출처가 있는 종목은 **가장 비싼 P/E(=가장 높은 breakeven, 가장
보수적인 기준)**를 쓴다 - etf_pipeline.format_comparison_table()이 미국
원본 비교에서 쓰는 것과 동일한 원칙.

실행: python3 scripts/rank_krx_etfs_2026_08_08.py
"""

import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def load_krx_ledgers(ledger_dir="ledger_krx") -> list:
    ledgers = []
    for fname in sorted(os.listdir(ledger_dir)):
        if fname.endswith(".json"):
            with open(os.path.join(ledger_dir, fname), encoding="utf-8") as f:
                ledgers.append(json.load(f))
    return ledgers


def build_ranking(ledgers: list) -> list:
    rows = []
    for d in ledgers:
        by_source = d["valuation"]["by_source"]
        # 가장 비싼 P/E(=가장 높은 내재성장/breakeven) 출처를 보수적 기준으로 채택
        worst = max(by_source.values(), key=lambda s: s["implied_growth"])
        n_sources = len(by_source)

        fragile_flags = []
        if d["valuation"]["judgment_flipped_across_sources"]:
            fragile_flags.append("출처갈림")
        if not d["growth"]["sensitivity"]["robust"]:
            fragile_flags.append("성장가정취약")
        if n_sources == 1:
            fragile_flags.append("단일출처")
        if d["wrapper"]["hedged"]:
            # v3.40: estimated_hedge_carry가 실제로 채워졌는지 확인 - 병기됐다면
            # "미반영"이 아니라 "참고용 반영"이라고 정확히 표시한다(자동으로
            # Gap에 반영된 건 아니므로 여전히 주의 플래그이긴 하다).
            if d["wrapper"].get("estimated_hedge_carry") is not None:
                fragile_flags.append("환헤지비용참고반영")
            else:
                fragile_flags.append("환헤지비용미반영")

        rows.append({
            "krx_ticker": d["meta"]["ticker"],
            "krx_name": d["meta"]["name"],
            "us_ticker": d["meta"]["wrapper_of"]["us_reference_ticker"],
            "tracks": d["meta"]["tracks"],
            "breakeven_pct": worst["required_growth"]["breakeven"] * 100,
            "assumed_growth_pct": d["growth"]["net_expected_growth"] * 100,
            "gap_pct": worst["gap"] * 100,
            "judgment": worst["judgment"],
            "expense_ratio_pct": d["wrapper"]["expense_ratio"] * 100,
            "aum_eok": (d["wrapper"]["aum_krw"] / 1e8) if d["wrapper"]["aum_krw"] else None,
            "n_pe_sources": n_sources,
            "fragile_flags": fragile_flags,
        })

    rows.sort(key=lambda r: r["breakeven_pct"])
    return rows


def format_table(rows: list) -> str:
    lines = []
    header = (f"{'#':>3} {'KRX티커':8} {'종목명':30} {'추종':10} "
              f"{'시장요구성장':>10} {'가정성장':>9} {'Gap':>9} {'총보수':>7} "
              f"{'순자산(억)':>10} {'주의'}")
    lines.append(header)
    lines.append("-" * 140)
    for i, r in enumerate(rows, 1):
        aum_str = f"{r['aum_eok']:>10,.0f}" if r["aum_eok"] is not None else f"{'미확인':>10}"
        flags = "+".join(r["fragile_flags"]) if r["fragile_flags"] else ""
        lines.append(
            f"{i:3} {r['krx_ticker']:8} {r['krx_name'][:30]:30} {r['us_ticker']:10} "
            f"{r['breakeven_pct']:9.2f}% {r['assumed_growth_pct']:8.2f}% "
            f"{r['gap_pct']:+8.2f}%p {r['expense_ratio_pct']:6.2f}% "
            f"{aum_str} {flags}"
        )
    return "\n".join(lines)


def main():
    ledgers = load_krx_ledgers()
    rows = build_ranking(ledgers)

    print("=" * 140)
    print(f"국내 상장 ETF 전체 재순위 ({len(rows)}종목) - 시장요구성장(breakeven) 오름차순")
    print("=" * 140)
    print(format_table(rows))
    print()
    print("⚠️ '시장요구성장'이 낮다고 자동으로 매수 신호가 아니다 - 그 섹터가 실제로")
    print("   그 성장조차 못 낼 수도 있다(원자재·경기민감 섹터가 특히 그렇다).")
    print("⚠️ '가정성장'은 분석자 주관이다 - Gap은 이 값에 1:1로 좌우되므로(v3.34 진단)")
    print("   Gap만 보고 종목간 순위를 매기지 말 것. 이 표가 '시장요구성장'을 앞에 둔 이유다.")
    print()

    judgment_counts = Counter(r["judgment"] for r in rows)
    print("판정 분포(가장 보수적 P/E 기준):")
    for j, n in judgment_counts.items():
        print(f"  {j}: {n}종목")

    fragile_n = sum(1 for r in rows if r["fragile_flags"])
    print(f"\n주의 플래그가 붙은 종목: {fragile_n}/{len(rows)}")

    out_path = "reports/krx_etf_ranking_2026-08-08.json"
    os.makedirs("reports", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
    print(f"\n결과 저장: {out_path}")

    return rows


if __name__ == "__main__":
    main()
