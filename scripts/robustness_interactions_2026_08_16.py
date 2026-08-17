"""
STAGE 3 후속 분석 (2026-08-16): §23 상호작용 · §24 거짓 강건성 · §25 거짓 취약성 · §26 다중검정.

⚠️ 연구 코드다(§35). `engine/`·ledger를 건드리지 않는다. R-001 가정공간을 **그대로** 쓴다 -
결과를 보고 범위를 바꾸지 않는다(§34).

global_robustness_research_2026_08_16.py가 종목별 stability를 냈다면, 이 스크립트는
그 숫자가 **왜** 그렇게 나왔는지를 캔다:
  §23 판정을 바꾸는 데 필요한 **최소 동시변경 축 개수**와 그 조합
  §24 강건해 보이지만 가정공간 자체가 한쪽으로 치우친 경우
  §25 판정은 흔들리지만 자본배분에는 도달하지 않는 경우
  §26 검사한 시나리오 총수(우연한 단일 flip을 과장하지 않기 위해)
"""
import itertools
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.global_robustness_research_2026_08_16 import (  # noqa: E402
    BUY_GRADES, _grade, load_base, scenarios,
)
from engine.expectation_gap_engine import judgment_from_gap  # noqa: E402
from engine.gap_analysis import _implied_growth_at  # noqa: E402

AXES = ("model_choice", "required_return_r", "terminal_growth",
        "growth_duration_n", "realistic_growth", "fcf0")


def _off_base(x, row):
    """이 시나리오에서 base와 다른 축들의 집합."""
    off = set()
    if x["model"] != row["model"]:
        off.add("model_choice")
    if x["r_delta"] != 0.0:
        off.add("required_return_r")
    if x["g_terminal_delta"] != 0.0:
        off.add("terminal_growth")
    if x["n"] != row["n"]:
        off.add("growth_duration_n")
    if x["realistic_growth"] != "base":
        off.add("realistic_growth")
    if x["fcf0"] != "base":
        off.add("fcf0")
    return off


def evaluate(row):
    out = []
    for s in scenarios(row):
        if s["status"] != "VALID":
            continue
        try:
            ig = _implied_growth_at(row["mc"], s["fcf0"], s["r"], s["n"], s["gt"], s["model"])
        except Exception:
            continue
        gap = s["rg"] - ig
        out.append({**s["labels"], "gap": gap, "judgment": judgment_from_gap(gap),
                    "grade": _grade(gap), "off": _off_base(s["labels"], row)})
    return out


def minimal_flip(results, row, key):
    """
    판정(또는 유니버스 소속)을 바꾸는 데 필요한 **최소 동시변경 축 개수**와
    그 최소 조합들. 한 축만으로 되면 1, 두 축이 겹쳐야 하면 2.
    """
    base_in = row["grade"] in BUY_GRADES
    flips = []
    for x in results:
        changed = (x["judgment"] != row["judgment"]) if key == "judgment" \
            else ((x["grade"] in BUY_GRADES) != base_in)
        if changed:
            flips.append(x)
    if not flips:
        return {"changeable": False}
    k = min(len(f["off"]) for f in flips)
    combos = sorted({tuple(sorted(f["off"])) for f in flips if len(f["off"]) == k})
    worst = min(flips, key=lambda f: abs(f["gap"] - row["gap"]))   # 경계에 가장 가까운 flip
    return {"changeable": True, "min_axes": k,
            "minimal_combinations": [list(c) for c in combos],
            "n_flip_scenarios": len(flips),
            "nearest_flip": {"gap": worst["gap"], "judgment": worst["judgment"],
                             "grade": worst["grade"], "axes": sorted(worst["off"])}}


def main():
    rows = load_base()
    audit = {r["ticker"]: r for r in json.load(
        open("reports/global_robustness_2026-08-16.json", encoding="utf-8"))["results"]}

    out, total_scen = [], 0
    for row in rows:
        res = evaluate(row)
        total_scen += len(res)
        a = audit[row["ticker"]]
        jm = minimal_flip(res, row, "judgment")
        um = minimal_flip(res, row, "universe")

        # §24 거짓 강건성: 가정공간이 한쪽으로만 열려 있는가
        one_sided = row["rg_low"] >= row["rg"] or row["rg_high"] <= row["rg"]
        flags = []
        if one_sided and row["cap_bound"]:
            flags.append("RG_RANGE_ONE_SIDED_BY_CAP")
        if not row["fcf0_sbc"]:
            flags.append("FCF_DOWNSIDE_NOT_TESTED")   # SBC 차감치 없음 → 회계 하방 미검증
        if row["model"] == "single_stage":
            flags.append("N_AND_TERMINAL_NOT_PERTURBED_BY_DESIGN")

        # §25 거짓 취약성: 판정은 바뀌지만 자본배분에는 도달하지 않는가
        false_fragility = (a["stability"]["judgment"] < 1.0
                           and a["stability"]["universe"] == 1.0)

        out.append({
            "ticker": row["ticker"], "base_grade": row["grade"],
            "base_judgment": row["judgment"], "cap_bound": row["cap_bound"],
            "judgment_minimal_flip": jm, "universe_minimal_flip": um,
            "false_robustness_flags": flags,
            "false_fragility_no_capital_impact": false_fragility,
            "n_valid_scenarios": len(res),
        })

    print("=== §23 판정/유니버스를 바꾸는 최소 동시변경 축 개수 ===")
    print(f"{'종목':6s}{'등급':>4s}{'판정변경':>9s}{'유니버스변경':>13s}  최소조합(유니버스 우선)")
    for o in sorted(out, key=lambda x: (
            x["universe_minimal_flip"].get("min_axes", 99),
            x["judgment_minimal_flip"].get("min_axes", 99))):
        j = o["judgment_minimal_flip"]; u = o["universe_minimal_flip"]
        js = f"{j['min_axes']}축" if j["changeable"] else "불변"
        us = f"{u['min_axes']}축" if u["changeable"] else "불변"
        combo = (u if u["changeable"] else j).get("minimal_combinations", [[]])[0]
        print(f"{o['ticker']:6s}{o['base_grade']:>4s}{js:>9s}{us:>13s}  {'+'.join(combo) or '—'}")

    ff = [o["ticker"] for o in out if o["false_fragility_no_capital_impact"]]
    print(f"\n=== §25 판정은 흔들리나 자본배분 불변: {len(ff)}종목 {ff}")

    cap_one = [o["ticker"] for o in out if "RG_RANGE_ONE_SIDED_BY_CAP" in o["false_robustness_flags"]]
    print(f"=== §24 캡 때문에 RG 가정공간이 상방으로만 열린 종목: {len(cap_one)}종목 {cap_one}")
    print("    → 이 종목들의 '판정안정 100%'는 하방 시나리오가 공간에 없어서일 수 있다.")

    nosbc = sum(1 for o in out if "FCF_DOWNSIDE_NOT_TESTED" in o["false_robustness_flags"])
    print(f"=== §24 SBC 차감 하방을 검증하지 못한 종목: {nosbc}/{len(out)}")
    print(f"\n=== §26 다중검정: 검사한 유효 시나리오 총 {total_scen:,}개 "
          f"(종목당 평균 {total_scen/len(out):.0f}개)")
    print("    단일 시나리오 flip 1건을 핵심 발견으로 과장하지 않는다.")

    rep = {"generated_at": "2026-08-16", "experiment_id": "R-001",
           "affects_official_judgment": False,
           "total_valid_scenarios_examined": total_scen,
           "results": out}
    p = "reports/robustness_interactions_2026-08-16.json"
    with open(p, "w", encoding="utf-8") as f:
        json.dump(rep, f, ensure_ascii=False, indent=2)
    print(f"\n저장: {p}")


if __name__ == "__main__":
    main()
