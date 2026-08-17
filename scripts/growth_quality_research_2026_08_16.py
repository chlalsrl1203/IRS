"""
Growth Quality 연구 실행 (2026-08-16) — D-2 / D-3 / D-5·D-6.

⚠️ **연구 코드다. `engine/`을 수정하지 않으며 ledger를 쓰지 않는다**(§21).
산출물은 `reports/growth_quality_research_2026-08-16.json` 하나뿐이다.

D-2 (§17) 입력품질과 정보문제 분리
    FCF CAGR의 근사-0 기준연도 문제 규모를 확정한다. 이 문제가 큰 종목에서는
    FCF 파생 변수를 "정보"로 해석하면 안 된다.

D-3 (§8) ROIIC 계산가능성 3분류
    Exact / Accounting Approximation / Proxy 중 무엇이 가능한지 판정한다.
    proxy를 ROIIC라고 부르지 않는다.

D-5·D-6 (§11·§13) 구조 A/B/C/D 판정영향 측정
    ⚠️ 아래 k는 **의도적으로 임의값**이며 제안이 아니다. 목적은 "이 축을 RG나
    Duration에 넣으면 판정이 얼마나 움직이는가"의 **크기**를 재는 것이고,
    34종목 결과에 맞춰 k를 고르는 것은 STOP CONDITION B라 하지 않는다.
"""
import glob
import json
import os
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.gap_analysis import _implied_growth_at  # noqa: E402
from engine.expectation_gap_engine import judgment_from_gap, judgment_grade_from_gap  # noqa: E402
from engine.growth_quality import economic_profile  # noqa: E402

# §11 민감도 탐침용 임의계수. **제안이 아니다.** 결과를 보고 조정하지 않는다.
PROBE_K = (0.5, 1.0)
PROBE_N_SHIFT = (-2, +2)   # 구조 B(Duration) 탐침: n을 마진 상하위로 ±2년
BUY_GRADES = ("S", "A")


def _grade(gap):
    g = judgment_grade_from_gap(gap)
    return g["grade"] if isinstance(g, dict) else g


def load():
    out = []
    for p in sorted(glob.glob("ledger/*.json")):
        d = json.load(open(p, encoding="utf-8"))
        I, D = d["inputs"], d["derived"]
        years = sorted(I["revenue_by_year"], key=int)
        fcf = {y: I["operating_cashflow_by_year"][y] - I["capex_by_year"][y] for y in years}
        # ⚠️ v3.21 이전(v3.19 스탬프 9종목)에는 cagr_5y_base_year 필드가 없다.
        # 그 버전에는 override 기능 자체가 없었으므로 기본 기준연도 years[-6]가 확정이다.
        schema_has_base_year = "cagr_5y_base_year" in D
        base = str(D["cagr_5y_base_year"]) if schema_has_base_year else years[-6]
        span = D.get("cagr_5y_span", 5)
        prof = economic_profile(I["revenue_by_year"], I["operating_income_by_year"],
                               I["capex_by_year"])
        out.append({
            "ticker": d["meta"]["ticker"],
            "rg": d["growth"]["realistic_growth"],
            "gap": d["expectation_gap"],
            "judgment": d["judgment"],
            "grade": _grade(d["expectation_gap"]),
            "model": d["implied_growth"]["model_used"],
            "mc": I["market_cap"], "fcf0": D["fcf0"],
            "r": d["discount_rate"]["r"], "n": d["discount_rate"]["n"],
            "gt": d["discount_rate"]["g_terminal"],
            "fcf_cagr_5y": D.get("fcf_cagr_5y"),
            "fcf_base": fcf[base], "fcf_last": fcf[years[-1]],
            "span": span, "schema_has_base_year": schema_has_base_year,
            "override_base_year": I.get("cagr_base_year_override"),
            "margin": prof["operating_margin_level"],
            "capex_rev": prof["capex_to_revenue_level"],
            "has_equity_series": bool(I.get("shareholders_equity_by_year")),
            "has_sbc": bool(I.get("sbc_by_year")),
            "fcf_used_by_min": bool(d["growth"]["breakdown"]["fcf_conservatism_applied"]),
        })
    return out


# ── D-2: 입력품질 (§17) ────────────────────────────────────────────────
def d2_input_quality(rows):
    out = []
    for r in rows:
        ratio = r["fcf_base"] / r["fcf_last"] if r["fcf_last"] else None
        # 기준연도 FCF가 최종연도의 10% 미만이면 CAGR이 기준값 잡음에 지배된다.
        fragile = ratio is not None and 0 < ratio < 0.10
        out.append({
            "ticker": r["ticker"], "fcf_base": r["fcf_base"], "fcf_last": r["fcf_last"],
            "base_to_last_ratio": ratio, "fcf_cagr_5y": r["fcf_cagr_5y"],
            "span_years": r["span"], "field_says_5y_but_span_is": r["span"],
            "base_year_from_schema": r["schema_has_base_year"],
            "base_year_manually_overridden": r["override_base_year"] is not None,
            "base_fragile": fragile,
            "fcf_actually_used_in_rg": r["fcf_used_by_min"],
            # 취약하면서 실제로 RG에 채택된 경우가 진짜 위험
            "fragile_and_used": fragile and r["fcf_used_by_min"],
        })
    return out


# ── D-3: ROIIC 계산가능성 (§8) ──────────────────────────────────────────
def d3_roiic_feasibility(rows):
    """
    Exact ROIIC       : ΔNOPAT / ΔInvestedCapital — 세율·투하자본 시계열 필요
    Accounting Approx : Δ영업이익(1−t) / Δ(자기자본+총부채) — 자기자본·부채 시계열 필요
    Proxy             : Δ영업이익 / 누적capex — 입력만으로 계산 가능하나 투하자본이 아님
    """
    n = len(rows)
    have_equity = sum(r["has_equity_series"] for r in rows)
    return {
        "exact_roiic": {
            "computable_tickers": 0, "of": n,
            "blocking_inputs": ["세율(유효세율) 시계열", "투하자본 시계열", "goodwill 분리"],
            "status": "BLOCKED",
        },
        "accounting_approximation": {
            "computable_tickers": have_equity, "of": n,
            "blocking_inputs": ["shareholders_equity_by_year(보험사 opt-in 전용)",
                                "총부채 시계열(net_debt는 최신 스칼라 1개)"],
            "status": "BLOCKED",
        },
        "proxy_delta_oi_over_cumcapex": {
            "computable_tickers": n, "of": n,
            "status": "COMPUTABLE_BUT_NOT_ROIIC",
            "why_not_roiic": (
                "분모가 투하자본이 아니라 누적 capex다. 인수(goodwill)·운전자본·R&D가 "
                "빠져 있어 자본집약 업종과 자산경량 업종을 비교할 수 없다. "
                "ROIIC라고 부르면 안 된다."
            ),
        },
    }


# ── D-5·D-6: 구조 A/B/C/D 판정영향 (§11·§13) ────────────────────────────
def d5_architecture_impact(rows):
    med_margin = statistics.median(r["margin"] for r in rows)
    results = {}

    def summarize(label, mutate):
        changed_j = changed_g = changed_u = 0
        dgaps = []
        detail = []
        for r in rows:
            rg2, n2 = mutate(r, med_margin)
            try:
                ig2 = _implied_growth_at(r["mc"], r["fcf0"], r["r"], n2, r["gt"], r["model"])
            except Exception:
                continue
            gap2 = rg2 - ig2
            j2, g2 = judgment_from_gap(gap2), _grade(gap2)
            dgaps.append(gap2 - r["gap"])
            jf, gf = j2 != r["judgment"], g2 != r["grade"]
            uf = (g2 in BUY_GRADES) != (r["grade"] in BUY_GRADES)
            changed_j += jf; changed_g += gf; changed_u += uf
            if jf or uf:
                detail.append({"ticker": r["ticker"], "gap_before": r["gap"],
                               "gap_after": gap2, "judgment_before": r["judgment"],
                               "judgment_after": j2, "grade_before": r["grade"],
                               "grade_after": g2, "universe_changed": uf,
                               "why_changed": (
                                   f"마진 {r['margin']*100:.1f}%가 중앙값 "
                                   f"{med_margin*100:.1f}% 대비 "
                                   f"{'높아' if r['margin']>=med_margin else '낮아'} "
                                   f"RG {r['rg']*100:.2f}%→{rg2*100:.2f}%, n {r['n']}→{n2}")})
        results[label] = {
            "judgment_flips": changed_j, "grade_changes": changed_g,
            "buy_universe_changes": changed_u,
            "gap_delta_median_pp": statistics.median(dgaps) * 100 if dgaps else None,
            "gap_delta_max_abs_pp": max(abs(d) for d in dgaps) * 100 if dgaps else None,
            "detail": detail,
        }

    for k in PROBE_K:
        summarize(f"A_rate_only_k={k}",
                  lambda r, m, k=k: (r["rg"] * (1 + k * (r["margin"] - m)), r["n"]))
    summarize("B_duration_only",
              lambda r, m: (r["rg"], max(8, min(15, r["n"] + (PROBE_N_SHIFT[1]
                            if r["margin"] >= m else PROBE_N_SHIFT[0])))))
    summarize("C_both_k=0.5",
              lambda r, m: (r["rg"] * (1 + 0.5 * (r["margin"] - m)),
                            max(8, min(15, r["n"] + (PROBE_N_SHIFT[1]
                                if r["margin"] >= m else PROBE_N_SHIFT[0])))))
    summarize("D_diagnostic_only", lambda r, m: (r["rg"], r["n"]))
    return {"median_margin_used": med_margin, "probe_k": list(PROBE_K),
            "probe_n_shift": list(PROBE_N_SHIFT),
            "probe_disclaimer": (
                "k와 n_shift는 의도적 임의값이며 제안이 아니다. 34종목 결과에 맞춰 "
                "고르지 않았고(STOP CONDITION B), 목적은 크기 측정뿐이다."),
            "by_architecture": results}


def main():
    rows = load()
    d2 = d2_input_quality(rows)
    d3 = d3_roiic_feasibility(rows)
    d5 = d5_architecture_impact(rows)

    frag = [x for x in d2 if x["base_fragile"]]
    frag_used = [x for x in d2 if x["fragile_and_used"]]
    span_mismatch = [x for x in d2 if x["span_years"] != 5]

    print("=== D-2 입력품질 (§17) ===")
    print(f"  기준연도 FCF가 최종연도의 10% 미만(취약): {len(frag)}/{len(rows)} "
          f"{[x['ticker'] for x in frag]}")
    print(f"  그중 실제로 RG에 채택된 경우: {len(frag_used)} {[x['ticker'] for x in frag_used]}")
    print(f"  필드명은 _5y인데 실제 span이 5가 아님: {len(span_mismatch)} "
          f"{[(x['ticker'], x['span_years']) for x in span_mismatch]}")

    print("\n=== D-3 ROIIC 계산가능성 (§8) ===")
    for k, v in d3.items():
        print(f"  {k:34s} {v['status']:26s} {v['computable_tickers']}/{v['of']}")

    print("\n=== D-5·D-6 구조별 판정영향 (§11) ===")
    print(f"  {'구조':22s}{'판정flip':>9s}{'등급변경':>9s}{'유니버스변경':>13s}{'Gap변동중앙':>12s}")
    for label, v in d5["by_architecture"].items():
        print(f"  {label:22s}{v['judgment_flips']:>9d}{v['grade_changes']:>9d}"
              f"{v['buy_universe_changes']:>13d}{v['gap_delta_median_pp']:>11.2f}%p")

    report = {"generated_at": "2026-08-16", "affects_official_judgment": False,
              "baseline_fingerprint_ref": "reports/baseline_frozen_2026-08-16.json",
              "d2_input_quality": d2, "d3_roiic_feasibility": d3,
              "d5_architecture_impact": d5}
    os.makedirs("reports", exist_ok=True)
    out = "reports/growth_quality_research_2026-08-16.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n저장: {out}")


if __name__ == "__main__":
    main()
