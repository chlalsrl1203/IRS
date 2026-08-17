"""
STAGE 3 투자판정 강건성 감사 (2026-08-16) — R-001 사전등록 가정공간 기준.

⚠️ **연구 코드다**(§35). `engine/`을 수정하지 않고 ledger를 쓰지 않는다. Base Case는
읽기 전용이며, 이 계층의 목적은 Base Case를 고치는 것이 아니라 **취약성을 재는 것**이다(§33).

⚠️ 가정범위는 `experiments/R-001.json`에 **사전등록**돼 있다. 결과를 보고 범위를
바꾸지 않는다(§34). 바꿔야 하면 R-002로 새로 등록한다.

⚠️ Judgment Stability는 **확률이 아니다**(§15) — "유효 가정공간 중 같은 판정이 나온
비율"일 뿐이며 보정된 적이 없다.
"""
import glob
import itertools
import json
import os
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.expectation_gap_engine import (  # noqa: E402
    JUDGMENT_BAND, capped_n, judgment_from_gap, judgment_grade_from_gap,
)
from engine.gap_analysis import _implied_growth_at  # noqa: E402

BUY_GRADES = ("S", "A")
R_DELTA = (-0.01, 0.0, 0.01)
GT_DELTA = (-0.01, 0.0, 0.01)
N_VALUES = tuple(range(8, 16))          # capped_n 허용 전 범위(§2 불일치 해결)
MODELS = ("single_stage", "two_stage")

# §21 불확실성 유형
UNCERTAINTY_TYPE = {
    "realistic_growth": "GROWTH_UNCERTAINTY",
    "growth_duration_n": "DURATION_UNCERTAINTY",
    "required_return_r": "VALUATION_UNCERTAINTY",
    "terminal_growth": "VALUATION_UNCERTAINTY",
    "model_choice": "MODEL_UNCERTAINTY",
    "fcf0": "ACCOUNTING_UNCERTAINTY",
}
# §29 취약성 → 추가조사 매핑
RESEARCH_ACTION = {
    "GROWTH_UNCERTAINTY": "회사 가이던스·세그먼트 오가닉 성장률 확보(다년 실현치 우선)",
    "DURATION_UNCERTAINTY": "경쟁우위 지속기간 근거(재투자 여력·시장침투율) — Stage 2 미실행",
    "VALUATION_UNCERTAINTY": "무위험금리·DRS 구성요소 재확인(주관입력 competition_intensity 우선)",
    "MODEL_UNCERTAINTY": "내재성장률이 회사 가이던스 대비 달성가능한지 대조(GWRE/KLAC 절차)",
    "ACCOUNTING_UNCERTAINTY": "SEC 원자료로 SBC·FCF 정의 재확인",
}


def _grade(gap):
    g = judgment_grade_from_gap(gap)
    return g["grade"] if isinstance(g, dict) else g


def load_base():
    rows = []
    for p in sorted(glob.glob("ledger/*.json")):
        d = json.load(open(p, encoding="utf-8"))
        dc, ci = d["discount_rate"], d["growth"]["breakdown"].get("revenue_cagr_inputs") or {}
        cagrs = [v for v in ci.values() if v is not None]
        rg = d["growth"]["realistic_growth"]
        # ⚠️ 키 이름 주의: ledger 스키마는 `fcf0_sbc_adjusted`다. 초판이 존재하지 않는
        # 키(`fcf0_after_sbc`)를 읽어 **fcf0 축이 34종목 전부에서 조용히 비활성화**됐다
        # (사전등록 공간보다 좁게 감사됨). 범위를 바꾼 게 아니라 구현을 R-001에 맞춘 수정이다.
        sbc = d.get("sbc_cross_check") or {}
        fcf_sbc = sbc.get("fcf0_sbc_adjusted") if isinstance(sbc, dict) else None
        rows.append({
            "ticker": d["meta"]["ticker"], "rg": rg, "gap": d["expectation_gap"],
            "judgment": d["judgment"], "grade": _grade(d["expectation_gap"]),
            "model": d["implied_growth"]["model_used"],
            "mc": d["inputs"]["market_cap"], "fcf0": d["derived"]["fcf0"],
            "r": dc["r"], "n": dc["n"], "gt": dc["g_terminal"],
            # LEVEL 2: 기업 자신의 과거 CAGR 범위. base가 캡 바인딩으로 밖이면 포함시킨다.
            "rg_low": min(cagrs + [rg]) if cagrs else rg,
            "rg_high": max(cagrs + [rg]) if cagrs else rg,
            "rg_range_from_own_history": bool(cagrs),
            "cap_bound": bool(d["growth"]["breakdown"].get("cap_applied")),
            "fcf0_sbc": fcf_sbc,
        })
    return rows


def scenarios(row):
    """
    §10 유효 가정공간 생성. VALID만 stability에 포함한다.
    §11 economic constraint: single_stage는 n·g_terminal을 쓰지 않으므로 흔들지 않는다
    (흔들면 결과가 같은 가짜 시나리오가 대량 생성돼 stability가 인위적으로 부풀려진다).
    """
    fcf_opts = [("base", row["fcf0"])]
    if row["fcf0_sbc"] and row["fcf0_sbc"] > 0:
        fcf_opts.append(("sbc_adjusted", row["fcf0_sbc"]))
    rg_opts = [("low", row["rg_low"]), ("base", row["rg"]), ("high", row["rg_high"])]

    out = []
    for model, dr, rg_lab_val, (fcf_lab, fcf) in itertools.product(
            MODELS, R_DELTA, rg_opts, fcf_opts):
        rg_lab, rg_val = rg_lab_val
        r = row["r"] + dr
        gts = GT_DELTA if model == "two_stage" else (0.0,)
        ns = N_VALUES if model == "two_stage" else (row["n"],)
        for dgt, n in itertools.product(gts, ns):
            gt = row["gt"] + dgt
            n_eff = capped_n(n)
            status = "VALID"
            if r <= gt:
                status = "INFEASIBLE"          # 수학적 제약: 발산
            elif fcf <= 0:
                status = "INFEASIBLE"
            elif n_eff != n:
                status = "INVALID"             # 허용범위 밖(방어적 - N_VALUES상 발생 안 함)
            out.append({
                "model": model, "r": r, "gt": gt, "n": n_eff, "rg": rg_val,
                "fcf0": fcf, "status": status,
                "labels": {"model": model, "r_delta": dr, "g_terminal_delta": dgt,
                           "n": n_eff, "realistic_growth": rg_lab, "fcf0": fcf_lab},
            })
    return out


def audit(row):
    scen = scenarios(row)
    valid, results = [], []
    for s in scen:
        if s["status"] != "VALID":
            continue
        try:
            ig = _implied_growth_at(row["mc"], s["fcf0"], s["r"], s["n"], s["gt"], s["model"])
        except Exception:
            s["status"] = "INFEASIBLE"
            continue
        gap = s["rg"] - ig
        valid.append(s)
        results.append({**s["labels"], "gap": gap,
                        "judgment": judgment_from_gap(gap), "grade": _grade(gap)})

    n_valid = len(results)
    if not n_valid:
        return {"ticker": row["ticker"], "status": "NOT_COMPUTABLE"}

    same_j = sum(x["judgment"] == row["judgment"] for x in results)
    same_g = sum(x["grade"] == row["grade"] for x in results)
    base_in_uni = row["grade"] in BUY_GRADES
    same_u = sum((x["grade"] in BUY_GRADES) == base_in_uni for x in results)
    gaps = [x["gap"] for x in results]

    # §12 one-at-a-time: 각 축만 단독으로 흔들었을 때 판정이 바뀌는가
    oat = {}
    for axis in ("model_choice", "required_return_r", "terminal_growth",
                 "growth_duration_n", "realistic_growth", "fcf0"):
        flips = []
        for x in results:
            others_at_base = (
                (x["model"] == row["model"] or axis == "model_choice")
                and (x["r_delta"] == 0.0 or axis == "required_return_r")
                and (x["g_terminal_delta"] == 0.0 or axis == "terminal_growth")
                and (x["n"] == row["n"] or axis == "growth_duration_n")
                and (x["realistic_growth"] == "base" or axis == "realistic_growth")
                and (x["fcf0"] == "base" or axis == "fcf0")
            )
            if others_at_base and x["judgment"] != row["judgment"]:
                flips.append(x)
        oat[axis] = {"flips": len(flips),
                     "uncertainty_type": UNCERTAINTY_TYPE[axis],
                     "worst_gap": min((f["gap"] for f in flips), default=None),
                     "example": flips[0] if flips else None}

    # §22 flip driver: 판정을 바꾸는 축을 영향 크기로 정렬
    drivers = sorted((a for a, v in oat.items() if v["flips"]),
                     key=lambda a: -oat[a]["flips"])
    primary = drivers[0] if drivers else None

    return {
        "ticker": row["ticker"],
        "base": {"gap": row["gap"], "judgment": row["judgment"], "grade": row["grade"],
                 "model": row["model"], "n": row["n"], "cap_bound": row["cap_bound"]},
        "scenario_counts": {"total": len(scen), "valid": n_valid,
                            "infeasible": sum(1 for s in scen if s["status"] == "INFEASIBLE")},
        "stability": {  # ⚠️ 확률 아님(§15)
            "judgment": same_j / n_valid, "grade": same_g / n_valid,
            "universe": same_u / n_valid,
            "gap_sign": sum((g > 0) == (row["gap"] > 0) for g in gaps) / n_valid,
        },
        "gap_range": {"min": min(gaps), "max": max(gaps),
                      "median": statistics.median(gaps), "base": row["gap"]},
        "one_at_a_time": oat,
        "flip_drivers": drivers,
        "primary_uncertainty_type": UNCERTAINTY_TYPE[primary] if primary else None,
        "research_priority": RESEARCH_ACTION[UNCERTAINTY_TYPE[primary]] if primary else None,
        "rg_range_from_own_history": row["rg_range_from_own_history"],
    }


def main():
    rows = load_base()
    audits = [audit(r) for r in rows]
    ok = [a for a in audits if a.get("status") != "NOT_COMPUTABLE"]

    print(f"대상 {len(ok)}종목 · R-001 사전등록 가정공간 · 유효시나리오 "
          f"중앙 {statistics.median(a['scenario_counts']['valid'] for a in ok):.0f}개")
    print("⚠️ Stability는 확률이 아니라 '유효 가정공간 중 같은 판정 비율'이다(§15)\n")
    print(f"{'종목':6s}{'판정':>16s}{'판정안정':>9s}{'등급안정':>9s}{'유니버스':>9s}"
          f"{'Gap범위(%p)':>18s}  주요취약축")
    for a in sorted(ok, key=lambda x: x["stability"]["judgment"]):
        gr = a["gap_range"]
        print(f"{a['ticker']:6s}{a['base']['judgment']:>16s}"
              f"{a['stability']['judgment']*100:8.0f}%{a['stability']['grade']*100:8.0f}%"
              f"{a['stability']['universe']*100:8.0f}%"
              f"{gr['min']*100:8.1f}~{gr['max']*100:6.1f}  "
              f"{a['flip_drivers'][0] if a['flip_drivers'] else '—'}")

    from collections import Counter
    types = Counter(a["primary_uncertainty_type"] for a in ok if a["primary_uncertainty_type"])
    print(f"\n주요 불확실성 유형 분포: {dict(types)}")
    fully = [a for a in ok if a["stability"]["judgment"] == 1.0]
    print(f"유효 가정공간 전체에서 판정 유지: {len(fully)}/{len(ok)} "
          f"{[a['ticker'] for a in fully]}")

    report = {"generated_at": "2026-08-16", "experiment_id": "R-001",
              "baseline_ref": "reports/baseline_frozen_2026-08-16.json",
              "affects_official_judgment": False,
              "stability_is_not_probability": True,
              "assumption_space": {"r_delta": list(R_DELTA), "g_terminal_delta": list(GT_DELTA),
                                   "n_values": list(N_VALUES), "models": list(MODELS),
                                   "realistic_growth": "기업 자신의 3y/5y/10y CAGR min~max (LEVEL 2)",
                                   "fcf0": "reported / SBC차감 (LEVEL 1, 보유 종목만)"},
              "results": audits}
    os.makedirs("reports", exist_ok=True)
    out = "reports/global_robustness_2026-08-16.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n저장: {out}")


if __name__ == "__main__":
    main()
