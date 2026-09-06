"""
engine/portfolio_pipeline.py (2026-09-06) — 포트폴리오 계층을 하나로 합친다.

## 왜 이 모듈이 필요했나

2026-09-05 하루에만 매수리스트 산출물이 5개 생겼다: `build_buylist_2026_08_03.py`
(구, 12종목) / `build_sa_portfolio_2026_09_05.py`(32종목, 미필터) /
`portfolio_screen_2026_09_05.py`(Stage 0-1 게이트, 20종목) /
`build_conviction_portfolio_2026_09_05.py`(Stage 2-3, 18종목) /
`publish_buylist_2026_09_06.py`(스키마 변환). ledger가 하나 늘 때마다 이
체인을 손으로 순서대로 돌려야 했다 - screener.py·deep_screen.py·
research_queue.py가 이미 engine/으로 승격돼 재사용되는 것과 달리, 포트폴리오
계층만 반복되는 "한 번짜리 스크립트"로 남아 있었다.

이 모듈은 그 셋(portfolio_screen + build_conviction_portfolio + publish_buylist)의
**로직**을 하나로 합친다. 새 밸류에이션 로직은 0줄 - 세 스크립트가 이미 검증한
계산을 그대로 옮겼을 뿐이다.

## 하드코딩된 사전을 "파생 가능한 소스"로 바꿨다 - 이게 진짜 통합이다

과거 두 스크립트는 사람 판단을 **스크립트 안에 직접** 하드코딩했다:

  - `FALSIFICATION_CONFIRMED = {"TTD": "..."}` (G3) - 그런데 이 사실은 이미
    `monitor/acknowledgements.json`에 `verdict: "TRIGGERED"`로 기록돼 있다
    (v3.64가 만든 그 파일). 하드코딩은 **같은 사실의 두 번째 사본**이었다 -
    누군가 새로 TRIGGERED를 확인해도 이 스크립트를 손으로 안 고치면 반영이
    안 된다. `confirmed_falsifications()`가 그 파일에서 직접 파생한다.
  - `RESEARCH`/`CLUSTER`/`G6_EXCLUDED` 딕셔너리 - 이건 정말 사람이 쓴
    정성판단(model_choice_reason/subjective_input_basis와 같은 성격)이라
    파생할 소스가 없다. `portfolio/qualitative_overrides.json`(사람이
    유지하는 작은 레지스트리, `portfolio/holdings.json`과 같은 성격)으로
    옮겼을 뿐 - 그래야 스크립트를 고치지 않고 데이터만 갱신할 수 있다.

## 이 모듈이 하지 않는 것 (engine/portfolio.py·research_queue.py와 동일 원칙)

- **액션/판정을 자동으로 고르지 않는다.** `decide()`류 함수 없음 - AST 테스트로 고정.
- **목표비중을 발명하지 않는다.** PHASE 2 감사(2026-08-21) 실측: 근거 없는
  버킷목표가 자본의 16.75~18.82%를 좌우한 반면 CONFIDENCE_ADJ는 2.33%뿐이었다.
  이 모듈은 quality_score 순위 + 종목당 상한만 쓴다.
- **ledger·holdings.json에 쓰지 않는다.** 이 모듈이 만드는 것은 매수리스트
  산출물(`reports/buylist_<날짜>.json`)뿐이다.
- **정성 리서치를 자동 생성하지 않는다.** 신규 Stage-1 생존종목에 레지스트리
  항목이 없으면 크래시하지 않고 엔진 원시 Confidence로 폴백하며
  `confidence_status="미검증"`을 명시한다 - `build_buylist_2026_08_03.py`가
  이미 쓰던 폴백과 동일 원칙.
"""
from __future__ import annotations

import glob
import json
import os

from engine.expectation_gap_engine import judgment_grade_from_gap
from engine.gap_analysis import gap_range_over_assumptions
from engine.monitor_state import load_acknowledgements
from engine.validated_scope import out_of_scope_reasons

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORTS = os.path.join(ROOT, "reports")
QUALITATIVE_PATH = os.path.join(ROOT, "portfolio", "qualitative_overrides.json")

UNIVERSE_GRADES = ("S", "A")
PER_STOCK_CAP = 0.12
CAP_BOUND_DISCOUNT = 0.85  # build_buylist_2026_08_03.py가 쓰던 값 그대로
MODEL_DIVERGENCE_THRESHOLD = 0.03    # v3.19가 이미 쓰는 값
INSURER_DIVERGENCE_THRESHOLD = 0.05  # v3.22가 이미 쓰는 값


# ── 입력 로딩 - 전부 "저장소의 사실"에서 읽는다, 하드코딩 없음 ──────────────

def load_sbc_verdicts(reports_dir: str = REPORTS) -> dict:
    """PHASE 1(2026-08-21) 계열의 SBC 신호 판정(CANCELLED/SURVIVES/NO_SIGNAL).

    특정 날짜 파일을 하드코딩하지 않고 최신 `signal_independence_*.json`을
    쓴다 - 다음에 이 검증이 재실행되면 자동으로 반영된다.
    """
    paths = sorted(glob.glob(os.path.join(reports_dir, "signal_independence_*.json")))
    if not paths:
        return {}
    data = json.loads(open(paths[-1], encoding="utf-8").read())
    return {row["ticker"]: row.get("verdict")
            for row in data.get("results", []) if row.get("ticker")}


def confirmed_falsifications(acks: dict | None = None) -> dict:
    """
    v3.42 thesis_monitor 반증조건 중 **사람이 TRIGGERED로 확인**한 것만
    파생한다(`monitor/acknowledgements.json`, v3.64). TTD를 스크립트 안에
    하드코딩하던 것을 대체한다 - 새 TRIGGERED가 기록되면 자동으로 반영된다.

    ⚠️ 이 함수는 반증조건 발동 여부를 **판정하지 않는다**(v3.42 원칙 그대로) -
    이미 사람이 확인해 파일에 적어 넣은 TRIGGERED만 읽는다.
    """
    acks = acks if acks is not None else load_acknowledgements()
    out: dict[str, list] = {}
    for entries in (acks.get("entries") or {}).values():
        for e in entries:
            if e.get("verdict") == "TRIGGERED":
                out.setdefault(e["ticker"], []).append(e)
    return out


def load_qualitative_overrides(path: str = QUALITATIVE_PATH) -> dict:
    """사람이 유지하는 정성판단 레지스트리. 없으면 빈 dict(전부 미검증 폴백)."""
    if not os.path.exists(path):
        return {"overrides": {}, "g6_substitutes": {}}
    data = json.loads(open(path, encoding="utf-8").read())
    return {"overrides": data.get("overrides", {}),
            "g6_substitutes": data.get("g6_substitutes", {})}


# ── Stage 0-1: 사전등록 게이트(G1/G2/G3) ────────────────────────────────

def evidence_row(led: dict, sbc_verdicts: dict, overrides: dict) -> dict:
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

    ov = overrides.get(t, {})

    return {
        "ticker": t,
        "company": led["meta"].get("company_name"),
        "grade": grade,
        "gap": gap,
        "realistic_growth": led["growth"]["realistic_growth"],
        "confidence_engine": led["confidence"]["final"],
        "confidence_researched": ov.get("confidence_adj"),
        "drs": led["drs"]["score"],
        "market_cap": mc,
        "analyzed_at": led["meta"]["analyzed_at"][:10],
        "gap_min": gap_min,
        "gap_max": rng.get("gap_max"),
        "grade_at_gap_min": grade_at_min,
        "gap_range_status": rng.get("status"),
        "flip_drivers": {k: v for k, v in (rng.get("flip_drivers") or {}).items()
                         if v is True},
        "gap_sbc_adjusted": gap_sbc,
        "grade_sbc_adjusted": grade_sbc,
        "sbc_to_fcf_pct": sbc.get("sbc_to_fcf_pct"),
        "sbc_signal_verdict": sbc_verdicts.get(t),
        "cap_applied": cap,
        "model_divergence": div,
        "insurer_divergence": ins_div,
        "out_of_scope": out_of_scope_reasons(gap=gap, market_cap=mc),
        "n_data_limitations": len(led.get("data_limitations") or []),
        "pit_status": (led["meta"].get("point_in_time") or {}).get("status"),
    }


def apply_gates(row: dict, falsification_confirmed: dict) -> dict:
    """G1/G2/G3 하드 게이트 + F1~F5 조사우선순위 플래그. `portfolio_screen_
    2026_09_05.py`의 정의를 그대로 옮긴 것 - 값을 하나도 바꾸지 않았다."""
    t = row["ticker"]
    excluded, flags = [], []

    gmin = row["grade_at_gap_min"]
    if gmin is None:
        flags.append("G1_계산불가(가정공간 수렴실패) - 배제 아님, 확인 필요")
    elif gmin not in UNIVERSE_GRADES:
        excluded.append(
            f"G1 등급취약: 가정공간 최악값 Gap {row['gap_min']*100:+.2f}%p "
            f"→ {gmin}등급(S/A 이탈). 뒤집는 축: "
            f"{', '.join(row['flip_drivers']) or '조합에서만'}"
        )

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

    if t in falsification_confirmed:
        entries = falsification_confirmed[t]
        detail = "; ".join(e.get("note", "")[:120] for e in entries)
        excluded.append(f"G3 반증확정(monitor/acknowledgements.json TRIGGERED): {detail}")

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


def screen_universe(ledgers: dict, sbc_verdicts: dict, falsification_confirmed: dict,
                     overrides: dict) -> tuple[list, list]:
    """Stage 0-1 전체 실행. (생존, 배제) 튜플을 Gap 내림차순으로 반환."""
    universe = [led for led in ledgers.values()
                if led.get("judgment_grade") in UNIVERSE_GRADES]
    rows = [apply_gates(evidence_row(led, sbc_verdicts, overrides), falsification_confirmed)
            for led in universe]
    rows.sort(key=lambda r: -r["gap"])
    survivors = [r for r in rows if r["survives"]]
    excluded = [r for r in rows if not r["survives"]]
    return survivors, excluded


# ── Stage 2: G6 회사공시 다년 성장률 대체 게이트 ────────────────────────

def apply_g6(survivors: list, g6_substitutes: dict) -> tuple[list, list]:
    """
    회사가 별도 공시하는 다년 실현 성장률로 Realistic Growth를 대체했을 때
    등급이 S/A를 벗어나면 배제한다(ROP 선례, v3.28). Implied Growth는 성장률
    입력과 독립이라 그대로 고정하고 Realistic Growth 자리에만 대입한다.

    ⚠️ g6_substitutes에 있다고 무조건 배제하는 게 아니라 **실제로 등급이
    이탈할 때만** 배제한다 - 회사 가이던스가 오히려 상향인 경우(DLO 선례,
    `qualitative_overrides.json`의 cap_discount_exempt로 처리)까지 이
    게이트가 자동으로 배제하면 안 된다.
    """
    kept, excluded = [], []
    for r in survivors:
        t = r["ticker"]
        sub = g6_substitutes.get(t)
        if sub is None:
            kept.append(r)
            continue
        # Implied Growth는 성장률 입력과 완전히 독립이므로 IG = 엔진RG - Gap로
        # 역산해 고정한다(ROP 크로스체크와 동일한 방식). engine_rg는 ledger가
        # 이미 갖고 있는 값이라 레지스트리에 중복 저장하지 않는다.
        engine_rg = r["realistic_growth"]
        ig = engine_rg - r["gap"]
        company_growth = sub["company_growth"]
        gap_at_company = company_growth - ig
        grade_at_company = judgment_grade_from_gap(gap_at_company)
        g6 = {
            **sub,
            "implied_growth": ig,
            "gap_at_company_growth": gap_at_company,
            "grade_at_company_growth": grade_at_company,
        }
        if grade_at_company not in UNIVERSE_GRADES:
            excluded.append({**r, "g6": g6})
        else:
            kept.append({**r, "gap": gap_at_company, "grade": grade_at_company,
                         "g6_applied": g6})
    return kept, excluded


# ── Stage 3: 비중 - quality_score 순위, 목표비중 없음 ───────────────────

def apply_cap(rows: list, cap: float = PER_STOCK_CAP) -> list:
    """상한흡수(v3.67 수정판) - 경계 EPS 처리 + 수렴 실패 시 예외를 던진다
    (조용히 위반을 통과시키지 않는다)."""
    eps = 1e-12
    for _ in range(50):
        over = [r for r in rows if r["weight"] > cap + eps]
        if not over:
            break
        excess = sum(r["weight"] - cap for r in over)
        for r in over:
            r["weight"] = cap
        room = [r for r in rows if r["weight"] < cap - eps]
        base = sum(r["quality_score"] for r in room)
        if not room or base <= 0:
            raise RuntimeError("상한흡수 실패: 재분배할 여유 종목이 없다")
        for r in room:
            r["weight"] += excess * r["quality_score"] / base
    else:
        raise RuntimeError("상한흡수가 50회 안에 수렴하지 않았다")
    return rows


def size_portfolio(survivors_after_g6: list, overrides: dict,
                    per_stock_cap: float = PER_STOCK_CAP,
                    cap_bound_discount: float = CAP_BOUND_DISCOUNT) -> list:
    """
    quality_score = Gap%p x (Confidence_adj/100) x 캡바인딩할인.
    `build_buylist_2026_08_03.py`가 쓰던 공식 그대로 - 새 지표 아니다.

    정성 레지스트리에 없는 종목은 크래시하지 않고 엔진 원시 Confidence로
    폴백하며 confidence_status="미검증"을 명시한다.
    """
    final = []
    for r in survivors_after_g6:
        t = r["ticker"]
        ov = overrides.get(t, {})
        conf = ov.get("confidence_adj", r["confidence_engine"])
        status = ov.get("confidence_status", "미검증")
        basis = ov.get("confidence_basis")
        cluster = ov.get("cluster", "미분류")
        cap_bound = bool(r["cap_applied"])
        exempt = ov.get("cap_discount_exempt", False)
        discount = 1.0 if (not cap_bound or exempt) else cap_bound_discount
        qs = r["gap"] * 100 * (conf / 100) * discount
        final.append({
            "ticker": t, "company": r["company"], "cluster": cluster,
            "grade": r["grade"], "gap_pct": r["gap"] * 100,
            "gap_min_pct": (r["gap_min"] * 100) if r.get("gap_min") is not None else None,
            "confidence_engine": r["confidence_engine"],
            "confidence_adj": conf, "confidence_status": status,
            "confidence_basis": basis,
            "cap_bound": r["cap_applied"],
            "cap_discount_applied": discount != 1.0,
            "cap_discount_exempt_reason": ov.get("cap_discount_exempt_reason")
            if exempt else None,
            "quality_score": qs,
            "analyzed_at": r["analyzed_at"],
        })

    total = sum(r["quality_score"] for r in final)
    for r in final:
        r["weight"] = r["quality_score"] / total
    apply_cap(final, per_stock_cap)
    final.sort(key=lambda r: -r["weight"])
    return final


# ── 발행 - daily_brief.py가 읽는 스키마로 변환 ──────────────────────────

def to_buylist_rows(sized: list) -> list:
    """`scripts/daily_brief.py::section_overseas()`가 기대하는 필드명으로
    재매핑한다(`publish_buylist_2026_09_06.py`의 역할을 대체)."""
    rows = []
    for r in sized:
        rows.append({
            "ticker": r["ticker"],
            "company": r["company"],
            "weight_final": r["weight"],
            "grade": r["grade"],
            "conf_adj": r["confidence_adj"],
            "conf_status": r["confidence_status"],
            "cap_bound": r["cap_bound"],
            "cluster": r["cluster"],
            "gap_pct": r["gap_pct"],
            "analyzed_at": r["analyzed_at"],
        })
    return rows
