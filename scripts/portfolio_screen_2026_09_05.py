"""
S/A 유니버스 선별 스크리닝 (Stage 0-1) - 2026-09-05

사용자 요청: "그냥 심층 조사 없이 어물쩡 만든게 아니라 선별하고 선별해서
필요한 종목들만" 담은 포트폴리오.

이 스크립트는 **비중을 정하지 않는다**. S/A 32종목 중 어느 것이 정성
심층조사를 받을 자격이 있는지(=엔진이 이미 아는 취약성을 통과하는지)만
가른다. 비중은 심층조사가 끝난 뒤 별도 스크립트가 정한다.

═══════════════════════════════════════════════════════════════════
사전등록 게이트 - 결과를 보기 전에 여기 고정한다(§21 LEVEL 원칙)
═══════════════════════════════════════════════════════════════════

게이트는 **이 저장소가 실제 사고·감사로 확립한 것만** 쓴다. 새 임계값을
발명하지 않는다(LYNCH_TYPE_CAPS·P/B 임계값·ERP 매핑에서 반복 거부한 형태).

G1 등급취약 (하드 게이트)
    조건: 정당화 가능한 가정공간(v3.51 `ASSUMPTION_GRID`) 전체에서
          최악값 `gap_min`의 등급이 S/A를 벗어나면 배제.
    근거: 2026-08-16 모델선택 연구가 "판정 취약 ≠ 자본 취약"을 실측으로
          구분했고(판정 11종목 vs 등급 13종목 vs 유니버스 4종목),
          R-001(2026-08-21)이 자본에 실제로 닿는 경계는 매수 유니버스
          경계(S/A)임을 재확인했다. 판정(±5%p)이 아니라 **등급 경계
          (+7%p)** 를 쓰는 이유가 이것이다.
    ⚠️ 이 범위는 Realistic Growth를 고정한 **하한**이다(v3.51 명시).

G2 SBC 거짓편입 (하드 게이트)
    조건: SBC 차감 시 등급이 S/A를 벗어나면 배제.
          단 PHASE 1(2026-08-21)이 CANCELLED로 판정한 종목은 예외
          - 그 신호는 부분적용(fcf0에만 차감)의 아티팩트이며 성장경로에도
          일관 적용하면 소멸한다(TCOM 실측: +5.28%p→+7.50%p).
    근거: RQ-002(2026-08-21) - SBC>0이면 Gap은 반드시 감소하므로(34종목
          위반 0건) 이 검증은 구조적으로 **거짓편입만** 걸러내고 거짓탈락은
          만들지 않는다. WDAY가 실제로 이 경로로 뒤집힌 선례.

G3 반증확정 (하드 게이트)
    조건: 사전등록 반증조건이 실제로 발동한 것으로 확인된 종목은 배제.
    근거: v3.42 thesis_monitor 1차 실행에서 TTD가 4개 중 3개 동시 발동.
    ⚠️ 2026-08-13에는 **기존 보유분 축소**(4.80%→2.70%)로 처리했으나,
       이번은 **신규 편입 여부** 판단이라 결론이 다르다 - "반증조건이
       이미 발동한 종목을 지금 새로 살 것인가"의 답은 아니오다.

── 배제가 아니라 "조사 우선순위" 플래그(하드 게이트 아님) ──

F1 성장상한 바인딩: Realistic Growth가 원시 계산값이 아니라 상한 그 자체.
    Gap이 사실상 `상한 − Implied Growth`만 남아 성장분석이 결과에 기여하지
    않는다(v3.24 M-1). ROP는 회사 공시 오가닉으로 대체하니 A→C로 이탈했다.
    → 자동 배제하지 않는다. 회사 공시 성장률 대조가 필요하다는 신호다.

F2 모델취약: 모델괴리 ≥3%p(v3.19가 이미 쓰는 임계값 재사용).
F3 보험 지속가능성장률 괴리 ≥5%p(v3.22가 이미 쓰는 임계값 재사용).
F4 검증범위 밖: v3.76 `out_of_scope_reasons`. **하드 게이트로 쓰지 않는다**
    - 코퍼스 상수가 34종목 시절 값이라 이미 낡았다(ACGL 자신이 상한이다).
F5 Confidence 미검증: 정성 심층조사 이력 없음.

═══════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from engine.expectation_gap_engine import judgment_grade_from_gap
from engine.gap_analysis import gap_range_over_assumptions
from engine.portfolio import load_ledgers
from engine.validated_scope import out_of_scope_reasons

REPO = pathlib.Path(__file__).resolve().parents[1]
REPORTS = REPO / "reports"

UNIVERSE_GRADES = ("S", "A")

# PHASE 1(2026-08-21)이 확인한 SBC 신호 판정. CANCELLED는 부분적용
# 아티팩트이므로 G2에서 면제한다.
SIGNAL_INDEPENDENCE = REPORTS / "signal_independence_2026-08-21.json"

# v3.42 thesis_monitor가 실제 발동을 확인한 종목(2026-08-13).
FALSIFICATION_CONFIRMED = {
    "TTD": "2026-08-13 thesis_monitor: 사전등록 반증조건 4개 중 3개 동시 발동"
           "(Q2 매출 $715M < 가이던스 $750M, Q3 가이던스 -12.1% 역성장, "
           "경영진 5번째 교체). 성장률 채점표·Gap 부식까지 3개 독립 축이 동시 지목.",
}

# 정성 심층조사 완료 이력(2026-08-02 S등급 7종목, 2026-08-04 A등급 6종목).
RESEARCHED = {
    "PDD": 75, "MNDY": 65, "DUOL": 78, "ACGL": 83, "PGR": 87, "SE": 79,
    "TTD": 45, "GEN": 70, "UBER": 83, "WDAY": 81, "TCOM": 80, "BRO": 70,
}

MODEL_DIVERGENCE_THRESHOLD = 0.03   # v3.19가 이미 쓰는 값
INSURER_DIVERGENCE_THRESHOLD = 0.05  # v3.22가 이미 쓰는 값


def load_sbc_verdicts() -> dict:
    """PHASE 1의 SBC 신호 판정(CANCELLED / SURVIVES / NO_SIGNAL)."""
    if not SIGNAL_INDEPENDENCE.exists():
        return {}
    data = json.loads(SIGNAL_INDEPENDENCE.read_text(encoding="utf-8"))
    out = {}
    for row in data.get("results", []):
        t = row.get("ticker")
        if t:
            out[t] = row.get("verdict")
    return out


def evidence_row(led: dict, sbc_verdicts: dict) -> dict:
    """한 종목의 취약성 신호를 전부 모은다. 판정은 하지 않는다."""
    t = led["meta"]["ticker"]
    gap = led["expectation_gap"]
    grade = led["judgment_grade"]
    mc = led["inputs"]["market_cap"]

    rng = gap_range_over_assumptions(led)
    gap_min = rng.get("gap_min")
    grade_at_min = judgment_grade_from_gap(gap_min) if gap_min is not None else None

    sbc = led.get("sbc_cross_check") or {}
    gap_sbc = sbc.get("gap_sbc_adjusted")
    grade_sbc = judgment_grade_from_gap(gap_sbc) if gap_sbc is not None else None

    cap = (led.get("growth", {}).get("breakdown", {}) or {}).get("cap_applied")
    div = (led.get("implied_growth", {}).get("models", {}) or {}).get("divergence")

    ins = led.get("insurer_cross_check") or {}
    ins_div = None
    if ins.get("sustainable_growth") is not None:
        ins_div = abs(ins["sustainable_growth"] - led["growth"]["realistic_growth"])

    return {
        "ticker": t,
        "company": led["meta"].get("company_name"),
        "grade": grade,
        "gap": gap,
        "confidence_engine": led["confidence"]["final"],
        "confidence_researched": RESEARCHED.get(t),
        "drs": led["drs"]["score"],
        "market_cap": mc,
        "analyzed_at": led["meta"]["analyzed_at"][:10],
        # G1
        "gap_min": gap_min,
        "gap_max": rng.get("gap_max"),
        "grade_at_gap_min": grade_at_min,
        "gap_range_status": rng.get("status"),
        "flip_drivers": {k: v for k, v in (rng.get("flip_drivers") or {}).items()
                         if v is True},
        # G2
        "gap_sbc_adjusted": gap_sbc,
        "grade_sbc_adjusted": grade_sbc,
        "sbc_to_fcf_pct": sbc.get("sbc_to_fcf_pct"),
        "sbc_signal_verdict": sbc_verdicts.get(t),
        # 플래그
        "cap_applied": cap,
        "model_divergence": div,
        "insurer_divergence": ins_div,
        "out_of_scope": out_of_scope_reasons(gap=gap, market_cap=mc),
        "n_data_limitations": len(led.get("data_limitations") or []),
        "pit_status": (led["meta"].get("point_in_time") or {}).get("status"),
    }


def apply_gates(row: dict) -> dict:
    """사전등록 게이트 적용. 위 docstring의 정의를 그대로 코드로 옮긴 것."""
    t = row["ticker"]
    excluded, flags = [], []

    # G1 등급취약
    gmin = row["grade_at_gap_min"]
    if gmin is None:
        flags.append("G1_계산불가(가정공간 수렴실패) - 배제 아님, 확인 필요")
    elif gmin not in UNIVERSE_GRADES:
        excluded.append(
            f"G1 등급취약: 가정공간 최악값 Gap {row['gap_min']*100:+.2f}%p "
            f"→ {gmin}등급(S/A 이탈). 뒤집는 축: "
            f"{', '.join(row['flip_drivers']) or '조합에서만'}"
        )

    # G2 SBC 거짓편입
    gsbc = row["grade_sbc_adjusted"]
    if gsbc is None:
        flags.append("G2_SBC 미확보 - '무해'가 아니라 '미확인'")
    elif gsbc not in UNIVERSE_GRADES:
        if row["sbc_signal_verdict"] == "CANCELLED":
            flags.append(
                f"G2_면제(PHASE 1 CANCELLED): SBC 차감 시 {gsbc}등급이나 "
                f"성장경로까지 일관 적용하면 신호가 소멸하는 부분적용 아티팩트"
            )
        else:
            excluded.append(
                f"G2 SBC 거짓편입: SBC 차감 시 Gap {row['gap_sbc_adjusted']*100:+.2f}%p "
                f"→ {gsbc}등급(S/A 이탈), SBC/FCF {row['sbc_to_fcf_pct']*100:.1f}%"
            )

    # G3 반증확정
    if t in FALSIFICATION_CONFIRMED:
        excluded.append(f"G3 반증확정: {FALSIFICATION_CONFIRMED[t]}")

    # 조사 우선순위 플래그
    if row["cap_applied"]:
        flags.append(f"F1 성장상한 바인딩({row['cap_applied']}) - 회사 공시 성장률 대조 필요")
    if row["model_divergence"] and row["model_divergence"] >= MODEL_DIVERGENCE_THRESHOLD:
        flags.append(f"F2 모델취약: 괴리 {row['model_divergence']*100:.2f}%p")
    if row["insurer_divergence"] and row["insurer_divergence"] >= INSURER_DIVERGENCE_THRESHOLD:
        flags.append(f"F3 보험 지속가능성장률 괴리 {row['insurer_divergence']*100:.2f}%p")
    if row["out_of_scope"]:
        flags.append(f"F4 검증범위 밖: {'; '.join(row['out_of_scope'])}")
    if row["confidence_researched"] is None:
        flags.append("F5 Confidence 미검증 - 정성 심층조사 이력 없음")

    row["excluded_by"] = excluded
    row["flags"] = flags
    row["survives"] = not excluded
    return row


def main():
    sbc_verdicts = load_sbc_verdicts()
    ledgers = load_ledgers()
    universe = [l for l in ledgers.values()
                if l.get("judgment_grade") in UNIVERSE_GRADES]

    rows = [apply_gates(evidence_row(l, sbc_verdicts)) for l in universe]
    rows.sort(key=lambda r: -r["gap"])

    survivors = [r for r in rows if r["survives"]]
    excluded = [r for r in rows if not r["survives"]]

    print("=" * 100)
    print(f"S/A 유니버스 선별 스크리닝 - {len(rows)}종목 → 생존 {len(survivors)} / 배제 {len(excluded)}")
    print("=" * 100)

    print(f"\n[배제] {len(excluded)}종목 - 사전등록 게이트 위반\n")
    for r in excluded:
        print(f"  {r['ticker']:6s} {r['grade']}  Gap {r['gap']*100:+7.2f}%p  conf={r['confidence_engine']}")
        for e in r["excluded_by"]:
            print(f"         └ {e}")

    print(f"\n[생존] {len(survivors)}종목\n")
    hdr = (f"  {'티커':6s} {'등급':4s} {'Gap':>9s} {'최악Gap':>9s} {'최악등급':>6s} "
           f"{'SBC후':>9s} {'Conf':>5s} {'검증':>5s}  플래그")
    print(hdr)
    print("  " + "-" * 98)
    for r in survivors:
        conf = r["confidence_researched"] or r["confidence_engine"]
        ver = "검증" if r["confidence_researched"] else "미검증"
        sbc = f"{r['gap_sbc_adjusted']*100:+.2f}" if r["gap_sbc_adjusted"] is not None else "n/a"
        nflag = len(r["flags"])
        print(f"  {r['ticker']:6s} {r['grade']:4s} {r['gap']*100:+8.2f}%p "
              f"{r['gap_min']*100:+8.2f}%p {r['grade_at_gap_min']:>6s} "
              f"{sbc:>8s}%p {conf:>5d} {ver:>5s}  {nflag}건")

    print(f"\n[생존 종목 플래그 상세]\n")
    for r in survivors:
        if r["flags"]:
            print(f"  {r['ticker']}:")
            for f in r["flags"]:
                print(f"    - {f}")

    n_unver = sum(1 for r in survivors if r["confidence_researched"] is None)
    print(f"\n{'='*100}")
    print(f"심층조사 필요: {n_unver}종목 "
          f"({', '.join(r['ticker'] for r in survivors if r['confidence_researched'] is None)})")
    print(f"이미 검증됨:   {len(survivors)-n_unver}종목 "
          f"({', '.join(r['ticker'] for r in survivors if r['confidence_researched'])})")
    print("=" * 100)

    out = {
        "generated_at": "2026-09-05",
        "stage": "0-1 (증거수집 + 사전등록 게이트)",
        "note": "이 산출물은 비중을 정하지 않는다. 심층조사 대상 선별까지만 한다.",
        "gates_preregistered": {
            "G1": "가정공간 최악값(gap_min) 등급이 S/A 이탈 → 배제 (v3.51 격자, R-001 등급경계)",
            "G2": "SBC 차감 시 등급 S/A 이탈 → 배제 (RQ-002, PHASE 1 CANCELLED는 면제)",
            "G3": "사전등록 반증조건 실제 발동 → 배제 (v3.42)",
        },
        "n_universe": len(rows),
        "n_survivors": len(survivors),
        "n_excluded": len(excluded),
        "survivors": survivors,
        "excluded": excluded,
    }
    path = REPORTS / "portfolio_screen_2026-09-05.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n저장: {path.relative_to(REPO)}")


if __name__ == "__main__":
    main()
