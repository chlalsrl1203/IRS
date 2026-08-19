"""
Hard Gates (P0-13, 2026-08-19) — 조용히 메모를 오염시키는 오류를 자동 실패시킨다.

# SOURCE:
https://github.com/DimaMerc/TieOutBench  (MIT)

# CAPABILITY:
hard gates / auto-fail / source-traced numbers / numerical·unit·fiscal-period
validation / fabricated-number detection / calibrated uncertainty

# IRS_TARGET:
engine/evaluation/gates.py

# METHOD:
REIMPLEMENT — 원본은 LLM 평가 벤치마크(워크플로·루브릭 데이터셋)라 IRS가 그대로
실행할 대상이 아니다. 가져온 것은 **채점 철학**이다:

> 작은 오류는 감점. 그러나 **조작된 수치·잘못된 회계기간·단위 오독·대조되지 않은
> 수치**는 감점이 아니라 **자동 실패**다.

그리고 하나 더 — **"자료상 판단 불가"라고 말하는 것을 실패가 아니라 credit으로
인정한다**(원본의 refusal probe). 이 저장소가 "확인 못하면 미확인으로 정직하게
남길 것"을 반복 원칙으로 세운 것과 정확히 같은 방향이라, 그 원칙을 채점에서
불리하게 만들지 않는다.

# WHY — 감점으로는 못 막는 것들이 실제로 있었다

| 사고 | 게이트 |
|---|---|
| TYL SBC/FCF 62% vs 실제 24.4%(2026-08-05) — 2차 출처의 잘못된 FCF 인용 | `GATE.FABRICATION` |
| RAR 100배 오류(v3.19, 4종목) | `GATE.SCALE` |
| capex 부호 사고 | `GATE.DIRECTION` |
| P0-07이 찾은 벤더-SEC 물질적 불일치(336개 중 67건) | `GATE.RECON` |
| v3.47~v3.49 PIT — 미래정보로 계산하면 전제 자체가 무너진다 | `GATE.LOOKAHEAD` |

전부 "값이 그럴듯해 보이는데 틀린" 유형이라, 감점 몇 점으로 처리하면 총점이
높아 통과해버린다.

# TEST:
tests/test_gates.py

---

## ⚠️ 원본에서 **가져오지 않은** 게이트

`GATE.BRIDGE`(DCF 순부채 브리지 누락)·`GATE.FREELUNCH`(비용 없는 보호 주장)·
`GATE.BASIS`(레버드/언레버드 혼동)는 넣지 않았다. IRS의 DCF는 FCF 기반 역산
단일 경로라 이 셋에 해당하는 실증 사고가 **한 건도 없다**. 실증 없이 게이트를
늘리면 통과 의례만 늘어난다(Simplicity First).

## ⚠️ `self_check_v2`와 중복하지 않는다

메모 기재값 vs 계산값 대조(`GATE.MATCH`)는 `engine/self_check_v2.py`가 이미
한다. 여기서 다시 구현하지 않고 **호출**한다(§1.11).
"""

import re
from dataclasses import asdict, dataclass

from engine.data.canonical import detect_scale_mismatch

VALIDATION_STATUS = {
    "hard_gates": (
        "SOFTWARE_VALIDATED — 각 게이트는 이 저장소에서 **실제로 일어난 사고** "
        "하나씩에 대응하며 테스트로 고정돼 있다. 다만 '게이트를 통과한 메모가 "
        "더 나은 투자 성과를 낸다'는 증거는 0건이다."
    ),
    "calibrated_uncertainty": (
        "IMPLEMENTED_NOT_VALIDATED — '판단 불가'를 credit으로 인정하는 것이 "
        "옳다는 판단은 이 저장소의 원칙에서 나왔을 뿐 실증된 바 없다."
    ),
}

# 자료상 판단 불가를 나타내는 표현. **이런 표현은 감점 대상이 아니라 credit이다.**
UNCERTAINTY_MARKERS = (
    "판단 불가", "판정 불가", "확인 못함", "확인하지 못했다", "미확인",
    "원인불명", "원인 미상", "자료 부족", "측정 불가", "알 수 없",
    "not determinable", "UNVERIFIED", "PIT_UNKNOWN", "PROVENANCE_UNKNOWN",
)


@dataclass
class GateResult:
    gate: str
    passed: bool
    reason: str
    detail: dict = None

    def as_dict(self):
        return asdict(self)


def _numbers_in(text: str):
    """메모에 등장하는 백분율 수치(소수로). 통화 금액은 표기가 너무 다양해 제외한다."""
    return [float(m) / 100 for m in re.findall(r"(-?\d+\.?\d*)\s*%", text or "")]


# ── GATE.FABRICATION ─────────────────────────────────────────────────────
def gate_fabrication(memo_text: str, ctx: dict) -> GateResult:
    """
    메모의 핵심 수치가 **계산 결과 어디에도 없는** 값인가.

    TYL 사고의 형태: 리서치 에이전트가 2차 출처에서 잘못된 FCF를 인용해 SBC/FCF를
    62%로 적었고, 그 값은 엔진이 계산한 어떤 값과도 대응하지 않았다.

    ⚠️ **메모의 모든 숫자를 검사하지 않는다.** 정성 서술에는 계산과 무관한 수치가
    당연히 많다(점유율·주가 등). 검사 대상은 `ctx["labeled_values"]`에 분석자가
    **명시한 라벨**뿐이다 — 라벨을 안 적으면 검사되지 않는다는 뜻이고, 그건
    이 게이트의 한계로 결과에 남는다.
    """
    labeled = ctx.get("labeled_values") or {}
    if not labeled:
        return GateResult(
            "GATE.FABRICATION", True,
            "검사할 라벨이 없다 — ctx['labeled_values']를 넣지 않으면 이 게이트는 "
            "아무것도 보증하지 않는다.",
            {"checked": 0, "vacuous": True})

    tol = ctx.get("tolerance", 0.001)
    bad = []
    for label, computed in labeled.items():
        if computed is None:
            continue
        pattern = re.escape(label) + r".{0,40}?(-?\d+\.?\d*)\s*%"
        m = re.search(pattern, memo_text or "")
        if not m:
            bad.append({"label": label, "issue": "메모에 없음"})
            continue
        stated = float(m.group(1)) / 100
        if abs(stated - computed) > tol:
            bad.append({"label": label, "stated": stated, "computed": computed,
                        "abs_diff": abs(stated - computed)})
    if bad:
        return GateResult(
            "GATE.FABRICATION", False,
            f"메모의 수치 {len(bad)}건이 계산 결과와 대응하지 않는다 — 출처를 "
            f"되짚을 수 없는 수치는 감점이 아니라 자동 실패다(TYL SBC 3배 오류).",
            {"mismatches": bad})
    return GateResult("GATE.FABRICATION", True,
                      f"라벨 {len(labeled)}건이 모두 계산값과 대응한다",
                      {"checked": len(labeled)})


# ── GATE.SCALE ───────────────────────────────────────────────────────────
def gate_scale(memo_text: str, ctx: dict) -> GateResult:
    """
    단위/스케일 오독. RAR 100배 오류(v3.19)가 정확히 이것이었다.

    메모 기재값이 계산값의 10·100·1000배(또는 그 역수)면 **부호·자릿수 사고**로
    본다. 단순 불일치(GATE.FABRICATION)와 분리한 이유는 원인과 조치가 다르기
    때문이다 — 스케일 오류는 값이 아니라 규약을 고쳐야 한다.
    """
    labeled = ctx.get("labeled_values") or {}
    hits = []
    for label, computed in labeled.items():
        if not computed:
            continue
        m = re.search(re.escape(label) + r".{0,40}?(-?\d+\.?\d*)\s*%", memo_text or "")
        if not m:
            continue
        stated = float(m.group(1)) / 100
        d = detect_scale_mismatch(stated, computed)
        if d.get("suspected"):
            hits.append({"label": label, "stated": stated, "computed": computed,
                         **{k: d[k] for k in ("factor", "ratio")}})
        elif computed and abs(stated / computed - 100) < 0.5:      # 100배 사고
            hits.append({"label": label, "stated": stated, "computed": computed,
                         "factor": 100, "ratio": stated / computed})
    if hits:
        return GateResult(
            "GATE.SCALE", False,
            f"메모 기재값 {len(hits)}건이 계산값의 배수 관계다 — 단위/자릿수 "
            f"오독으로 본다(RAR 100배 오류, v3.19).", {"hits": hits})
    return GateResult("GATE.SCALE", True, "배수 관계 이상 없음")


# ── GATE.DIRECTION ───────────────────────────────────────────────────────
def gate_direction(memo_text: str, ctx: dict) -> GateResult:
    """
    부호 반전. 메모 기재값과 계산값의 **부호가 다르면** 크기와 무관하게 실패다 —
    이익을 손실로, 저평가를 과대평가로 적는 것은 감점 사안이 아니다.
    """
    labeled = ctx.get("labeled_values") or {}
    flipped = []
    for label, computed in labeled.items():
        if computed is None or computed == 0:
            continue
        m = re.search(re.escape(label) + r".{0,40}?(-?\d+\.?\d*)\s*%", memo_text or "")
        if not m:
            continue
        stated = float(m.group(1)) / 100
        if stated != 0 and (stated > 0) != (computed > 0):
            flipped.append({"label": label, "stated": stated, "computed": computed})
    if flipped:
        return GateResult(
            "GATE.DIRECTION", False,
            f"부호가 반대인 수치 {len(flipped)}건 — 크기와 무관하게 자동 실패다.",
            {"flipped": flipped})
    return GateResult("GATE.DIRECTION", True, "부호 반전 없음")


# ── GATE.RECON ───────────────────────────────────────────────────────────
def gate_recon(memo_text: str, ctx: dict) -> GateResult:
    """
    대조되지 않은 수치로 결론을 냈는가.

    P0-07이 8종목 336개 값 중 **67건의 물질적 불일치**를 찾았다. 미해결 충돌을
    안은 채 분석을 발행하면 "어느 출처를 썼는지 모르는 결론"이 된다.

    ⚠️ 대조 정보 자체가 없으면 **실패시키지 않는다**(vacuous). 대조를 안 한 것과
    대조 결과 어긋난 것은 다르며, 전자를 실패로 처리하면 아직 provider 경로로
    옮기지 않은 기존 분석이 전부 막힌다.
    """
    rep = ctx.get("reconciliation")
    if not rep:
        return GateResult(
            "GATE.RECON", True,
            "대조 정보가 없다 — 이 게이트는 아무것도 보증하지 않는다"
            "(대조를 안 한 것과 대조 결과 어긋난 것은 다르다).",
            {"vacuous": True})
    n = rep.get("n_unresolved", 0)
    if n:
        return GateResult(
            "GATE.RECON", False,
            f"미해결 출처 충돌 {n}건을 안은 채 결론을 냈다 — 어느 출처를 썼는지 "
            f"모르는 결론이 된다.", {"unresolved": rep.get("unresolved", [])[:5]})
    return GateResult("GATE.RECON", True,
                      f"대조 완료(값 {rep.get('n_values', 0)}건, 미해결 0)")


# ── GATE.LOOKAHEAD ───────────────────────────────────────────────────────
def gate_lookahead(memo_text: str, ctx: dict) -> GateResult:
    """
    미래정보 사용. `run_analysis()`가 이미 `PIT_INVALID`면 실행을 거부하지만,
    메모·리포트 단계에서도 상태를 확인한다.

    `PIT_UNKNOWN`은 **실패가 아니다** — 34종목이 전부 그 상태이고, 모른다고
    말하는 것을 실패로 처리하면 이 저장소의 정직성 원칙과 충돌한다. 대신
    calibrated uncertainty 쪽에서 그 사실이 기록된다.
    """
    pit = (ctx.get("point_in_time") or {})
    status = pit.get("status")
    if status == "PIT_INVALID" or pit.get("violations"):
        return GateResult(
            "GATE.LOOKAHEAD", False,
            "분석일보다 나중에 공시된 데이터가 쓰였다 — 계산 전제 자체가 무너진다.",
            {"violations": pit.get("violations", [])})
    return GateResult("GATE.LOOKAHEAD", True,
                      f"미래정보 사용 흔적 없음(status={status or '미기입'})",
                      {"pit_unknown": status in (None, "PIT_UNKNOWN")})


# ── GATE.MATCH (self_check_v2 위임) ──────────────────────────────────────
def gate_match(memo_text: str, ctx: dict) -> GateResult:
    """
    메모 기재값 vs 계산값 대조. **`engine/self_check_v2.py`에 위임한다** —
    같은 검사를 다시 구현하면 두 구현이 미묘하게 어긋난다(§1.11).
    """
    from engine.self_check_v2 import run_self_check_v2

    if not (memo_text or "").strip():
        return GateResult("GATE.MATCH", True, "메모가 없어 검사 대상 아님",
                          {"vacuous": True})
    try:
        run_self_check_v2(memo_text, ctx)
    except ValueError as e:
        return GateResult("GATE.MATCH", False, str(e).split("\n")[0],
                          {"detail": str(e)})
    return GateResult("GATE.MATCH", True, "self_check_v2 전체 통과")


GATES = {
    "GATE.FABRICATION": gate_fabrication,
    "GATE.SCALE": gate_scale,
    "GATE.DIRECTION": gate_direction,
    "GATE.RECON": gate_recon,
    "GATE.LOOKAHEAD": gate_lookahead,
    "GATE.MATCH": gate_match,
}


def calibrated_uncertainty_credit(memo_text: str, ctx: dict) -> dict:
    """
    "자료상 판단 불가"라고 말한 것을 **credit으로 인정한다**(원본의 refusal probe).

    이 저장소는 "확인 못하면 미확인으로 정직하게 남길 것"을 반복 원칙으로
    세웠다(WCN FCF CAGR 원인불명, 상장일 미확인, Alpha Vantage 약관 확인 실패).
    채점이 그걸 불리하게 만들면 원칙과 채점이 서로 싸운다.

    ⚠️ **점수를 매기지 않는다.** 표현이 몇 개 있었는지와, 시스템이 이미 아는
    미확인 상태(PIT/provenance/거버넌스)를 함께 보고할 뿐이다.
    """
    found = [m for m in UNCERTAINTY_MARKERS if m in (memo_text or "")]
    system_unknowns = []
    if (ctx.get("point_in_time") or {}).get("status") in (None, "PIT_UNKNOWN"):
        system_unknowns.append("PIT 미검증")
    if (ctx.get("provenance") or {}).get("status") == "PROVENANCE_UNKNOWN":
        system_unknowns.append("값 단위 출처 미기록")
    gov = ctx.get("governance") or {}
    if gov.get("decision") == "UNVERIFIED":
        system_unknowns.append(f"출처 약관 미확인({gov.get('provider','')})")
    return {
        "explicit_uncertainty_markers": found,
        "n_markers": len(found),
        "system_known_unknowns": system_unknowns,
        "acknowledged": bool(found) or not system_unknowns,
        "note": (
            "'판단 불가'는 실패가 아니다. 다만 시스템이 아는 미확인 상태가 "
            "있는데 메모가 그것을 언급하지 않으면 acknowledged=False가 되며, "
            "이는 감점이 아니라 **누락 표시**다."
        ),
        "validation_status": VALIDATION_STATUS["calibrated_uncertainty"],
    }


def run_hard_gates(memo_text: str, ctx: dict, gates=None) -> dict:
    """
    하드 게이트 전체 실행. **하나라도 실패하면 전체가 실패다** — 다른 항목이
    아무리 좋아도 총점으로 상쇄하지 않는다(원본의 auto-fail 철학).

    ⚠️ `vacuous=True`인 게이트는 통과했지만 **아무것도 보증하지 않는다.**
    통과 개수만 세면 검사하지 않은 것이 통과로 둔갑하므로, 결과에 그 수를
    따로 담는다.
    """
    chosen = gates or list(GATES)
    results = [GATES[g](memo_text, ctx) for g in chosen]
    failed = [r for r in results if not r.passed]
    vacuous = [r.gate for r in results if (r.detail or {}).get("vacuous")]
    return {
        "passed": not failed,
        "n_gates": len(results),
        "n_failed": len(failed),
        "failed_gates": [r.gate for r in failed],
        "n_vacuous": len(vacuous),
        "vacuous_gates": vacuous,
        "results": [r.as_dict() for r in results],
        "calibrated_uncertainty": calibrated_uncertainty_credit(memo_text, ctx),
        "validation_status": VALIDATION_STATUS["hard_gates"],
        "note": (
            "하드 게이트는 감점이 아니라 자동 실패다. 통과했다고 메모가 옳다는 "
            "뜻은 아니며, vacuous 게이트는 검사 자체를 하지 않았다는 뜻이다."
        ),
    }
