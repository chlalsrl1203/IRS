"""
조합축에서만 취약한 6종목(BRO/COR/TCOM/TYL/VRSN/ZTS) 개별 축 분해 (2026-08-16).

executive_summary.md "다음 감사가 반드시 할 일" 3번 - v3.51 gap_range_over_assumptions()의
flip_drivers는 축을 하나씩만 흔들어(OAT) 판정이 뒤집히는지 본다. 이 6종목은
OAT 4개 축(model_choice/discount_rate/terminal_growth/growth_duration_n) 전부
False인데도 robust=False다 - 즉 전체 격자(30조합) 어딘가에서는 뒤집히지만
단일 축만으로는 절대 안 뒤집힌다. "왜 조합에서만 뒤집히는가"를 답한다.

새 밸류에이션 로직 0줄 - engine/gap_analysis.py의 ASSUMPTION_GRID·
_implied_growth_at·judgment_from_gap을 그대로 재사용한다(중복 계산 금지 원칙).
"""
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.gap_analysis import ASSUMPTION_GRID, _implied_growth_at  # noqa: E402
from engine.expectation_gap_engine import judgment_from_gap  # noqa: E402

TICKERS = ["BRO", "COR", "TCOM", "TYL", "VRSN", "ZTS"]


def load_ledger(ticker):
    matches = sorted(glob.glob(f"ledger/{ticker}_*.json"))
    assert len(matches) == 1, f"{ticker}: ledger 파일 {len(matches)}개(1개여야 함)"
    return json.load(open(matches[0], encoding="utf-8")), matches[0]


def decompose(ledger):
    rg = ledger["growth"]["realistic_growth"]
    mc = ledger["inputs"]["market_cap"]
    fcf0 = ledger["derived"]["fcf0"]
    disc = ledger["discount_rate"]
    r0, n0, gt0 = disc["r"], disc["n"], disc["g_terminal"]
    base_model = ledger["implied_growth"]["model_used"]
    base_j = ledger["judgment"]

    points = []
    for model in ASSUMPTION_GRID["models"]:
        for dr in ASSUMPTION_GRID["r_delta"]:
            for dgt in ASSUMPTION_GRID["g_terminal_delta"]:
                for dn in ASSUMPTION_GRID["n_delta"]:
                    if model == "single_stage" and (dgt != 0.0 or dn != 0):
                        continue
                    try:
                        ig = _implied_growth_at(mc, fcf0, r0 + dr, n0 + dn, gt0 + dgt, model)
                    except Exception:
                        continue
                    gap = rg - ig
                    j = judgment_from_gap(gap)
                    active = {
                        "model_choice": model != base_model,
                        "discount_rate": dr != 0.0,
                        "terminal_growth": dgt != 0.0 and model == "two_stage",
                        "growth_duration_n": dn != 0 and model == "two_stage",
                    }
                    n_active = sum(active.values())
                    points.append({
                        "model": model, "r_delta": dr, "g_terminal_delta": dgt,
                        "n_delta": dn, "gap": gap, "judgment": j,
                        "active_axes": [k for k, v in active.items() if v],
                        "n_active": n_active,
                    })

    flips = [p for p in points if p["judgment"] != base_j]
    if not flips:
        return {"base_judgment": base_j, "flips_found": False}

    min_n_active = min(p["n_active"] for p in flips)
    minimal_flips = [p for p in flips if p["n_active"] == min_n_active]

    # 각 minimal flip 조합에 대해, 관여한 축들을 "혼자서는" 얼마나 움직이는지
    # 참고용으로 계산한다(이미 flip_drivers가 낸 결론 - 단독으로는 base_j를
    # 못 넘는다 - 을 구체적 Gap 수치로 재확인하는 용도).
    solo_effects = {}
    for p in minimal_flips:
        for axis in p["active_axes"]:
            if axis in solo_effects:
                continue
            if axis == "model_choice":
                other_model = "single_stage" if base_model == "two_stage" else "two_stage"
                try:
                    ig = _implied_growth_at(mc, fcf0, r0, n0, gt0, other_model)
                    solo_effects[axis] = {"gap": rg - ig, "judgment": judgment_from_gap(rg - ig)}
                except Exception:
                    solo_effects[axis] = None
            elif axis == "discount_rate":
                d = p["r_delta"]
                ig = _implied_growth_at(mc, fcf0, r0 + d, n0, gt0, base_model)
                solo_effects[axis] = {"gap": rg - ig, "judgment": judgment_from_gap(rg - ig), "delta": d}
            elif axis == "terminal_growth":
                d = p["g_terminal_delta"]
                ig = _implied_growth_at(mc, fcf0, r0, n0, gt0 + d, base_model)
                solo_effects[axis] = {"gap": rg - ig, "judgment": judgment_from_gap(rg - ig), "delta": d}
            elif axis == "growth_duration_n":
                d = p["n_delta"]
                ig = _implied_growth_at(mc, fcf0, r0, n0 + d, gt0, base_model)
                solo_effects[axis] = {"gap": rg - ig, "judgment": judgment_from_gap(rg - ig), "delta": d}

    return {
        "base_judgment": base_j,
        "official_gap": ledger["expectation_gap"],
        "flips_found": True,
        "n_total_flips": len(flips),
        "min_n_active_axes": min_n_active,
        "minimal_flip_examples": minimal_flips[:3],
        "solo_effects_of_involved_axes": solo_effects,
    }


def main():
    report = {"generated_at": "2026-08-16", "tickers": {}}
    print(f"{'종목':6s} {'기준판정':16s} {'최소조합축수':8s} {'관여축'}")
    for t in TICKERS:
        ledger, path = load_ledger(t)
        result = decompose(ledger)
        report["tickers"][t] = {"ledger_file": os.path.basename(path), **result}
        if result["flips_found"]:
            axes = result["minimal_flip_examples"][0]["active_axes"]
            print(f"{t:6s} {result['base_judgment']:16s} {result['min_n_active_axes']:^8d} {'+'.join(axes)}")
        else:
            print(f"{t:6s} {result['base_judgment']:16s} {'해당없음(재현안됨)'}")

    out_path = "reports/combination_flip_decomposition_2026-08-16.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n저장: {out_path}")


if __name__ == "__main__":
    main()
