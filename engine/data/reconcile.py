"""
Reconciliation (P0-07, 2026-08-19) — 출처가 어긋날 때 무엇을 할 것인가.

# SOURCE:
https://github.com/chenditc/investment_data  (Apache-2.0)

# CAPABILITY:
source comparison / conflict detection / cross-validation / missing-data handling

# IRS_TARGET:
engine/data/reconcile.py

# METHOD:
REIMPLEMENT — 원본은 가격 시계열을 대상으로 `adjust_ratio`를 재계산해 출처를
정렬하는 SQL 파이프라인이다. IRS가 다루는 것은 가격이 아니라 **회계 수치**이고,
회계 수치의 불일치는 "둘 중 하나가 틀렸다"보다 **"정의가 다르다"**인 경우가
많다(정규화 영업이익 vs GAAP 영업이익). 그래서 자동 정렬을 옮겨오지 않았다.
가져온 것은 **교차검증을 상시 절차로 둔다**는 원칙이다.

# WHY — P0-03이 만든 구체적 요구
BSX `operating_income`이 ledger(벤더)와 SEC 사이에서 **11개 연도 전부** 어긋났고
(−141% ~ +7.4%), 그 차이가 margin_volatility 4.00→8.00, DRS 43.80→47.80,
Gap +5.87%p→+5.65%p로 흘렀다. 판정은 안 뒤집혔지만 BSX Gap은 경계 바로 위라
남은 여유의 약 25%를 먹는다. **이걸 담아 판단할 자료구조가 없었다.**

# TEST:
tests/test_reconcile.py

---

## ⚠️ 이 모듈의 핵심 결정 — 물질적 불일치를 **자동 해결하지 않는다**

권위 서열(1차 공시 > 규제기관 > 벤더 > 웹)로 자동 선택하는 것이 손쉽지만,
BSX 사례가 정확히 그러면 안 되는 이유를 보여준다: 벤더의 영업이익이 **틀린 것이
아니라 다른 정의**(일회성 항목 제외)일 수 있다. 자동으로 SEC를 택하면 34종목의
입력이 조용히 바뀌고, 그 변화가 어디서 왔는지 나중에 추적할 수 없다.

그래서:
- **작은 차이**(반올림·표기)는 자동 해결한다 — 판단할 것이 없다.
- **물질적 차이**는 `requires_review=True`로 남긴다. 권위 서열은 **제안**으로만
  제시하고(`suggested_source_key`), 채택 여부는 분석자가 정한다.

이 프로젝트가 is_insurer·sbc_cross_check·성장상한에서 반복해온 "병기, 자동판정
안 함" 원칙의 데이터 계층 판이다.

## ⚠️ 임계값의 인식론적 지위

`TOLERANCE_TIERS`는 **검증된 값이 아니다.** 회계 수치의 출처간 편차 분포를
이 저장소가 측정한 적이 없다. 아래 값은 BSX 1종목 실측(매출 10/11 완전일치,
capex 3.9%·11.1% 차이, 영업이익 1.2%~141% 차이)에서 "완전 일치 / 작은 차이 /
정의가 다름"이 갈리는 지점을 관측한 **시작점**이며, LYNCH_TYPE_CAPS·
demand_sensitivity 앵커표와 동일하게 취급한다 — 관측이 쌓이면 갱신하되,
결과를 보고 조정하지 않는다.
"""

from engine.data.canonical import detect_scale_mismatch
from engine.data.governance.source_registry import Authority, get_source

VALIDATION_STATUS = {
    "tolerance_tiers": (
        "IMPLEMENTED_NOT_VALIDATED — BSX 1종목 관측 기반 시작점. 출처간 편차 "
        "분포를 측정한 적이 없다."
    ),
    "authority_ranking": (
        "ECONOMICALLY_SUPPORTED — 1차 공시가 벤더 가공본보다 원본에 가깝다는 것은 "
        "정의상 참이다. 다만 **더 정확하다는 뜻은 아니다**(정의가 다를 수 있다). "
        "그래서 제안으로만 쓰고 자동 채택하지 않는다."
    ),
}

# (상한 비율, 등급, 자동해결 가능 여부)
TOLERANCE_TIERS = (
    (0.0,    "EXACT",             True),
    (0.001,  "ROUNDING",          True),    # 0.1% 이내 — 반올림·표기 차이
    (0.01,   "MINOR",             True),    # 1% 이내
    (float("inf"), "MATERIAL",    False),   # 그 이상 — 정의 차이일 수 있다
)

# 권위 서열. **선택 근거가 아니라 제안 근거다**(위 VALIDATION_STATUS 참조).
AUTHORITY_RANK = {
    Authority.PRIMARY_FILING: 0,
    Authority.REGULATOR: 1,
    Authority.VENDOR: 2,
    Authority.AGGREGATOR_WEB: 3,
    Authority.ANALYST: 4,
}


def classify_difference(values) -> dict:
    """
    후보값들의 상대 편차를 등급으로 분류한다.

    기준값은 **절댓값이 가장 큰 값**이 아니라 후보들의 절댓값 중앙 규모로 잡는다 —
    0 근처 값이 섞이면 상대오차가 발산하기 때문이다. 부호가 갈리면(예: BSX FY2015
    영업이익 +790M vs −327M) 상대오차 계산과 무관하게 **무조건 MATERIAL**이다.
    """
    vals = [v for v in values if v is not None]
    if len(vals) < 2:
        return {"tier": "EXACT", "max_rel_diff": 0.0, "auto_resolvable": True,
                "sign_conflict": False}

    lo, hi = min(vals), max(vals)
    sign_conflict = lo < 0 < hi
    base = max(abs(v) for v in vals)
    rel = float("inf") if base == 0 else (hi - lo) / base

    if sign_conflict:
        return {"tier": "MATERIAL", "max_rel_diff": rel, "auto_resolvable": False,
                "sign_conflict": True}

    for limit, tier, auto in TOLERANCE_TIERS:
        if rel <= limit:
            return {"tier": tier, "max_rel_diff": rel, "auto_resolvable": auto,
                    "sign_conflict": False}
    return {"tier": "MATERIAL", "max_rel_diff": rel, "auto_resolvable": False,
            "sign_conflict": False}


def _rank(source_key):
    try:
        return AUTHORITY_RANK.get(get_source(source_key).authority, 99)
    except KeyError:
        return 99


def reconcile_candidates(candidates) -> dict:
    """
    `build_canonical_series(reconcile_fn=...)`에 넘길 대조 정책.

    `candidates`: `[{"source_key", "value", "source", "available_at"}, ...]`

    반환에 반드시 담기는 것:
      `value`               자동해결된 경우의 채택값. **물질적 불일치면 None**
      `requires_review`     분석자가 봐야 하는가
      `severity`            EXACT / ROUNDING / MINOR / MATERIAL
      `suggested_source_key` 권위 서열상 제안(채택이 아니다)
      `rejected`            채택되지 않은 후보 전부 — 버리지 않는다
    """
    if not candidates:
        raise ValueError("후보가 비어 있다")

    values = [c["value"] for c in candidates]
    cls = classify_difference(values)
    ranked = sorted(candidates, key=lambda c: (_rank(c["source_key"]), c["source_key"]))
    top = ranked[0]
    scale = detect_scale_mismatch(min(values), max(values)) if len(values) > 1 else \
        {"suspected": False}

    base = {
        "severity": cls["tier"],
        "max_rel_diff": cls["max_rel_diff"],
        "sign_conflict": cls["sign_conflict"],
        "suggested_source_key": top["source_key"],
        "scale_mismatch": scale,
        "rejected": [c for c in candidates if c is not top],
        "validation_status": VALIDATION_STATUS["tolerance_tiers"],
    }

    if cls["auto_resolvable"]:
        return {
            **base, "value": top["value"], "chosen_source_key": top["source_key"],
            "requires_review": False,
            "reason": (
                f"편차 {cls['max_rel_diff']*100:.3f}%({cls['tier']})로 "
                f"허용 범위 안이라 권위가 가장 높은 출처({top['source_key']})를 "
                f"자동 채택했다. 판단할 것이 없는 차이다."
            ),
        }

    reason = (
        f"편차 {cls['max_rel_diff']*100:.1f}%({cls['tier']})로 물질적이다. "
        f"**자동 채택하지 않는다** — 회계 수치의 큰 불일치는 '둘 중 하나가 틀렸다'가 "
        f"아니라 '정의가 다르다'인 경우가 많다(BSX 영업이익: 벤더 정규화값 vs "
        f"GAAP 원값). 권위 서열상 제안은 {top['source_key']}이나, 채택은 원자료를 "
        f"확인한 분석자가 정한다."
    )
    if cls["sign_conflict"]:
        reason = "부호가 갈린다(한쪽은 이익, 다른 쪽은 손실). " + reason
    if scale.get("suspected"):
        reason += f" 또한 {scale['reason']}"

    return {**base, "value": None, "chosen_source_key": None,
            "requires_review": True, "reason": reason}


def reconciliation_report(series) -> dict:
    """
    `CanonicalSeries` -> 대조 요약. **해결된 것보다 안 된 것을 먼저 보여준다** —
    커버리지를 자랑하는 리포트는 빠진 것을 숨긴다(provenance·ETF 엔진과 동일 원칙).
    """
    by_severity, unresolved = {}, []
    for (metric, fy), v in sorted(series.values.items()):
        sev = (v.conflict or {}).get("severity", "EXACT")
        by_severity[sev] = by_severity.get(sev, 0) + 1
        if v.has_unresolved_conflict:
            unresolved.append({
                "metric": metric, "fiscal_year": fy,
                "severity": sev,
                "max_rel_diff": (v.conflict or {}).get("max_rel_diff"),
                "candidates": v.candidates,
                "suggested_source_key": (v.conflict or {}).get("suggested_source_key"),
            })
    return {
        "entity": series.entity,
        "n_values": len(series.values),
        "n_unresolved": len(unresolved),
        "by_severity": by_severity,
        "unresolved": unresolved,
        "limitations": list(series.limitations),
        "note": (
            "미해결 항목은 '데이터가 없다'가 아니라 '출처가 갈리는데 어느 쪽을 "
            "쓸지 아직 정하지 않았다'는 뜻이다. 정하지 않은 채 분석에 넣으면 "
            "그 분석은 어느 출처를 썼는지 모르는 결과가 된다."
        ),
    }
