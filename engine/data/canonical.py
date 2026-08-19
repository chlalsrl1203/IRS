"""
Canonical Data Model + Normalization (P0-05/P0-06, 2026-08-19).

# SOURCE:
https://github.com/chenditc/investment_data  (Apache-2.0)

# CAPABILITY:
multi-source normalization / canonical("final") 계층 분리 / versioned dataset

# IRS_TARGET:
engine/data/canonical.py

# METHOD:
REIMPLEMENT — 원본은 SQL 테이블(`ts_*`/`yahoo_*` 원본 + `final_a_stock_eod_price`
대조본)과 shell 파이프라인으로 돼 있어 그대로 옮길 수 없다. 가져온 것은
**계층 분리 원칙** 하나다: *출처별 원본을 지우지 않고, 대조 결과를 **별도**
canonical 층으로 만든다.* 원본을 덮어쓰면 "왜 이 값이 선택됐는가"를 영원히 잃는다.

# WHY:
P0-03이 실제 불일치를 찾아냈다 — BSX `operating_income`이 ledger(벤더)와 SEC
1차자료 사이에서 **11개 연도 전부** 어긋난다(−141% ~ +7.4%). 그런데 그 사실을
담을 자료구조가 없었다. `AnalysisInputs`는 `{연도: 값}` 하나만 받으므로,
값을 고르는 순간 **고르지 않은 값과 고른 이유가 사라진다.**

# TEST:
tests/test_canonical.py

---

## 정규화가 다루는 3가지 — 전부 이 저장소가 실제로 겪은 사고다

| 항목 | 실제 사고 |
|---|---|
| **스케일** | RAR 100배 오류(v3.19). 천 단위/단위 표기가 섞이면 조용히 1000배 틀린다 |
| **부호** | capex 부호 사고. XBRL `Payments*`는 유출을 양수로, 일부 벤더는 음수로 준다 |
| **통화** | M-6 — PDD가 CNY인데 ledger에 아무 표시가 없었다 |

셋 다 "값이 그럴듯해 보이는데 틀린" 유형이라 사람 눈으로는 안 잡힌다.

## 이 모듈이 하지 않는 것

- **어느 값이 옳은지 고르지 않는다.** 그건 `engine/data/reconcile.py`(P0-07)이며,
  거기서도 물질적 불일치는 자동 해결하지 않는다.
- **환율 변환을 하지 않는다.** 통화가 다르면 **오류로 처리**한다 — 환율을 어느
  시점 것으로 잡느냐가 또 하나의 주관 입력이 되고, 이 프로젝트에 그 실증
  사례가 아직 없다(Simplicity First).
"""

from dataclasses import dataclass, field

from engine.data.providers.base import METRICS, FinancialFact

# 유출을 **양수**로 적는 지표. IRS 규약이며 XBRL `Payments*` 태그와 일치한다
# (BSX FY2025: OCF 4,534 − capex 876 = FCF 3,658로 ledger와 대조 확인).
OUTFLOW_POSITIVE_METRICS = frozenset({"capex", "dividends_paid"})

# 스케일 후보. 벤더가 천/백만 단위로 주는 경우를 잡는다.
KNOWN_SCALES = (1, 1_000, 1_000_000, 1_000_000_000)

# 스케일 오인식을 판정하는 허용오차. 값 자체가 우연히 1000배 차이 날 수도 있으므로
# **자동으로 고치지 않고 의심만 보고한다**(아래 `detect_scale_mismatch` 참조).
SCALE_MATCH_TOLERANCE = 0.005      # 0.5%


class NormalizationError(ValueError):
    """정규화 단계에서 **조용히 넘어가면 안 되는** 문제."""


def normalize_sign(metric: str, value: float) -> float:
    """
    부호 규약을 IRS 기준으로 맞춘다(유출은 양수).

    ⚠️ 부호를 **뒤집는 것이 아니라 절댓값을 취한다.** 뒤집기(`-value`)를 쓰면
    이미 올바른 부호로 온 값까지 망가지고, 어느 쪽이 들어왔는지에 따라 결과가
    달라진다. capex가 음수로 오는 벤더와 양수로 오는 SEC를 같은 코드로 다루려면
    "유출의 크기"만 남기는 것이 안전하다.
    """
    if metric not in METRICS:
        raise ValueError(f"알 수 없는 지표: {metric}")
    if metric in OUTFLOW_POSITIVE_METRICS:
        return abs(value)
    return value


def detect_scale_mismatch(a: float, b: float) -> dict:
    """
    두 값이 **스케일만 다른 같은 값**인지 본다(천/백만/십억 단위 혼입).

    ⚠️ 자동으로 고치지 않는다. 값 하나가 다른 하나의 정확히 1000배인 것은
    단위 문제일 수도, 실제로 그만큼 다른 것일 수도 있다 — 판정 없이 **의심을
    보고**하고 분석자가 원자료를 확인하게 한다(RAR 100배 사고의 교훈:
    그럴듯한 원인을 검증 없이 확정하지 말 것).
    """
    if not a or not b:
        return {"suspected": False, "reason": "0 또는 결측이라 판정 불가"}
    hi, lo = (abs(a), abs(b)) if abs(a) >= abs(b) else (abs(b), abs(a))
    ratio = hi / lo
    for scale in KNOWN_SCALES[1:]:
        if abs(ratio - scale) / scale <= SCALE_MATCH_TOLERANCE:
            return {
                "suspected": True, "factor": scale, "ratio": ratio,
                "reason": (
                    f"두 값이 약 {scale:,}배 차이(비율 {ratio:,.2f}) — 단위 혼입"
                    f"(천/백만/십억) 의심. **자동으로 고치지 않는다**: 원자료의 "
                    f"단위 표기를 직접 확인할 것."
                ),
            }
    return {"suspected": False, "ratio": ratio, "reason": "알려진 스케일 배수 아님"}


@dataclass
class CanonicalValue:
    """
    한 (지표, 회계연도)에 대해 **선택된 값 + 선택되지 않은 값 + 선택 이유**.

    선택되지 않은 후보를 버리지 않는 것이 이 타입의 존재 이유다 — 원본을
    덮어쓰면 "왜 이 값인가"를 영원히 잃는다(chenditc/investment_data가 원본
    테이블을 남기고 `final_*`를 따로 두는 것과 같은 이유).
    """

    metric: str
    fiscal_year: int
    value: float
    currency: str
    chosen_source_key: str
    chosen_reason: str
    available_at: str
    candidates: list = field(default_factory=list)   # [{source_key, value, source}]
    conflict: dict = None                            # reconcile 결과(있으면)

    @property
    def has_unresolved_conflict(self) -> bool:
        return bool(self.conflict and self.conflict.get("requires_review"))


@dataclass
class CanonicalSeries:
    """
    한 종목의 canonical 재무 시계열. `AnalysisInputs`에 넣을 수 있는 형태를
    `to_inputs_kwargs()`로 준다 — 다만 **분석자가 명시적으로 호출해야 한다.**
    자동 주입하지 않는 이유는 P0-02와 같다(주관 입력이 자동 생성된 것처럼 보이면 안 된다).
    """

    entity: str
    values: dict = field(default_factory=dict)       # {(metric, fy): CanonicalValue}
    limitations: list = field(default_factory=list)

    def series(self, metric: str) -> dict:
        """
        ⚠️ **값이 `None`인 연도는 제외한다.** 미해결 충돌은 "값이 None"이 아니라
        "값이 없다"이며, `None`을 시계열에 남기면 `AnalysisInputs`로 흘러가 CAGR
        계산에서 터지거나(운이 좋으면) 조용히 틀린다(운이 나쁘면). 빠진 연도는
        `unresolved_conflicts()`·`reconciliation_report()`에 그대로 드러난다.
        """
        return {fy: v.value for (m, fy), v in sorted(self.values.items())
                if m == metric and v.value is not None}

    def available_at(self, metric: str = "revenue") -> dict:
        return {fy: v.available_at for (m, fy), v in sorted(self.values.items())
                if m == metric}

    def unresolved_conflicts(self) -> list:
        return [v for v in self.values.values() if v.has_unresolved_conflict]

    def to_inputs_kwargs(self, metrics=None, strict: bool = True) -> dict:
        """
        `AnalysisInputs(**kwargs)`에 넣을 `{metric}_by_year` 딕셔너리들.

        `strict=True`(기본)면 **미해결 충돌이 있을 때 거부한다.** 충돌을 안은 채
        분석을 돌리면 그 분석은 "어느 출처를 썼는지 모르는 결과"가 된다 —
        이 저장소가 v3.32에서 정리한 기록 무결성 원칙과 같은 계열이다.
        """
        conflicts = self.unresolved_conflicts()
        if strict and conflicts:
            raise NormalizationError(
                f"{self.entity}: 미해결 출처 충돌 {len(conflicts)}건이 있어 분석 "
                f"입력으로 쓸 수 없다 — "
                + "; ".join(
                    f"{c.metric} FY{c.fiscal_year}({c.conflict.get('severity')})"
                    for c in conflicts[:5]
                )
                + ". 원자료를 확인해 정책을 정하거나 strict=False로 명시적으로 "
                "감수할 것(그 경우 어느 출처가 쓰였는지 반드시 기록할 것)."
            )
        want = set(metrics or METRICS)
        out = {}
        for metric in want:
            s = self.series(metric)
            if s:
                out[f"{metric}_by_year"] = s
        return out


def build_canonical_series(entity: str, facts_by_source: dict,
                           reconcile_fn=None) -> CanonicalSeries:
    """
    출처별 `FinancialFact` 목록 -> `CanonicalSeries`.

    `facts_by_source`: `{source_key: [FinancialFact, ...]}`
    `reconcile_fn(candidates) -> dict`: 후보가 둘 이상일 때 호출된다. 없으면
    **후보가 둘 이상인 지점을 전부 미해결로 남긴다** — 조용히 하나를 고르지 않는다.
    """
    buckets = {}
    limitations = []
    for source_key, facts in facts_by_source.items():
        for f in facts:
            if not isinstance(f, FinancialFact):
                raise TypeError("FinancialFact만 받는다(외부 객체 유입 금지, §1.8)")
            buckets.setdefault((f.metric, f.fiscal_year), []).append(f)

    values = {}
    for (metric, fy), cands in sorted(buckets.items()):
        currencies = {c.currency for c in cands}
        if len(currencies) > 1:
            # 환율 변환을 하지 않는다 — 통화 혼입은 오류다(M-6: PDD의 CNY 미표기).
            raise NormalizationError(
                f"{entity} {metric} FY{fy}: 출처마다 통화가 다르다({currencies}). "
                f"환율 변환은 이 계층이 하지 않는다 — 어느 시점 환율을 쓸지가 "
                f"또 하나의 주관 입력이 되기 때문이다. 같은 통화로 맞춰 넣을 것."
            )
        norm = [(c, normalize_sign(metric, c.value)) for c in cands]
        candidates = [{"source_key": c.source_key, "value": v, "source": c.source,
                       "available_at": c.available_at} for c, v in norm]

        distinct = {round(v, 6) for _, v in norm}
        if len(distinct) == 1:
            chosen, val = norm[0]
            values[(metric, fy)] = CanonicalValue(
                metric=metric, fiscal_year=fy, value=val, currency=chosen.currency,
                chosen_source_key=chosen.source_key,
                chosen_reason=("단일 값" if len(norm) == 1
                               else f"{len(norm)}개 출처가 동일한 값을 보고"),
                available_at=min(c.available_at for c, _ in norm),
                candidates=candidates,
            )
            continue

        if reconcile_fn is None:
            # 조용히 고르지 않는다.
            values[(metric, fy)] = CanonicalValue(
                metric=metric, fiscal_year=fy, value=None,
                currency=cands[0].currency, chosen_source_key=None,
                chosen_reason="미해결 — 대조 정책(reconcile_fn)이 주어지지 않았다",
                available_at=min(c.available_at for c in cands),
                candidates=candidates,
                conflict={"requires_review": True, "severity": "UNRESOLVED",
                          "reason": "출처마다 값이 다른데 대조 정책이 없다"},
            )
            limitations.append(
                f"[미해결 충돌] {metric} FY{fy}: 출처별 값이 다르다 "
                f"({[c['value'] for c in candidates]})"
            )
            continue

        decision = reconcile_fn(candidates)
        values[(metric, fy)] = CanonicalValue(
            metric=metric, fiscal_year=fy, value=decision.get("value"),
            currency=cands[0].currency,
            chosen_source_key=decision.get("chosen_source_key"),
            chosen_reason=decision.get("reason", ""),
            available_at=min(c.available_at for c in cands),
            candidates=candidates, conflict=decision,
        )
        if decision.get("requires_review"):
            limitations.append(
                f"[검토 필요] {metric} FY{fy}: {decision.get('severity')} — "
                f"{decision.get('reason')}"
            )

    return CanonicalSeries(entity=entity, values=values, limitations=limitations)
