"""
Portfolio Review (v3.82 신규, 2026-09-05) - 보유 포트폴리오를 감시 가능한
상태로 만든다.

## 이 프로젝트에 없던 것

IRS는 종목 하나하나에 대해 "싼가"(`judgment`)를 답하고, `build_buylist`가
S/A 등급으로 **가상의** 매수리스트를 만든다. 그런데 **사용자가 실제로 무엇을
얼마나 들고 있는지**는 코드 어디에도 없었다. 그래서 다음 질문에 답할 수단이
전혀 없었다:

  - 내가 든 종목 중 지금 유효한 판정이 없는 게 몇 %인가?
  - 어느 종목을 어떤 순서로 다시 봐야 하는가?
  - 엔진이 S/A로 본 종목 중 내가 안 든 게 뭔가?

이 모듈이 그 셋에 답한다. **새 밸류에이션 로직은 0줄**이다 - 이미 저장된
ledger·리포트를 읽어 대조할 뿐이다.

## ⚠️ 설계상 하지 않는 것 세 가지 (전부 테스트로 고정)

**① 액션을 고르지 않는다.** `decide(gap) -> BUY` 같은 함수를 만들지 않는다.
`engine/thesis.py`가 v3.48에서 확립한 경계 그대로다 - Gap을 넣으면 매수가
나오는 함수가 생기는 순간, 검증되지 않은 신호(`gap_analysis.
GAP_SIGNAL_STATUS = RESEARCH_HYPOTHESIS`)가 곧바로 자본배분이 된다.
이 모듈은 **"어느 종목을 왜 다시 봐야 하는가"**만 낸다.

**② 목표비중을 계산하지 않는다.** 2026-08-21 PHASE 2 사이징 감사가 실측한
것: `build_buylist`의 버킷 목표비중(근거 없는 상수)이 자본의 **16.75~18.82%**를
좌우하는 반면, 이 프로젝트가 가장 많은 노력을 들인 축(`CONFIDENCE_ADJ`,
정성 심층조사 33종목)은 **2.33%**만 움직였다 - 노력과 자본영향이 8배
역비례한다. 여기서 새 배분 공식을 또 만들면 그 문제를 복제할 뿐이다.

**③ holdings.json에 쓰지 않는다.** 보유 상태는 사람이 유지한다(v3.64
`monitor_state`가 확립한 "확인은 사람의 행위" 원칙). 코드가 보유량을 고치기
시작하면 기록의 신뢰성이 무너진다.

## 왜 가격 드리프트가 1차 트리거가 아닌가

리밸런싱 문헌(Vanguard 등)의 임계값 방식은 **자산배분 드리프트**를 다루고,
그 근거(위험조정 15~25bp, 거래비용 1/4)는 집중형 개별주 포트폴리오로 그대로
전이되지 않는다. 더 결정적인 이유는 이 프로젝트가 **실측한 사실**이다:

  주가가 빠지면 Gap은 **반드시** 벌어진다(Implied Growth만 내려가고
  Realistic Growth는 재무제표에서만 나오므로 불변). 즉 **사업이 나빠져서
  주가가 빠진 경우에도 이 엔진의 핵심 지표는 "더 사라"고 말한다.**

TTD가 그 실례다 - 주가 -26.3%에 Gap이 +17.01%p -> +20.96%p로 벌어지는
동안 반증조건 3개가 동시에 발동해 서사가 무너져 있었다(v3.42).
따라서 1차 트리거는 **가격이 아니라 논거·데이터 유효성**이어야 한다.

## 플래그 규칙은 결과를 보기 전에 고정했다

아래 `REVIEW_RULES`의 임계값은 **이 모듈을 처음 실행하기 전에** 정했다.
결과를 보고 조정하면 사후합리화와 구분되지 않는다(이 프로젝트가
LYNCH_TYPE_CAPS·P/B 임계값·ERP 매핑에서 반복 거부한 수법).

임계값 근거:
  - `STALE_DAYS = 90`: 분기 실적 주기. 한 분기가 지나면 재무 시계열이
    바뀔 수 있다. **검증된 값이 아니라 회계 주기에서 온 서술적 기준이다.**
  - `MODEL_DIVERGENCE = 0.03`: 엔진이 이미 쓰는 경고 임계값(v3.19)을
    그대로 재사용한다 - 새 숫자를 발명하지 않는다.
  - `CONCENTRATION = 0.25`: `build_buylist`의 종목당 상한(12%)의 약 2배.
    ⚠️ 이 값만은 이 모듈이 새로 정한 것이라 근거가 가장 약하다.
  - `DEEP_LOSS = -0.20`: 판정 불가 종목이 큰 손실 중일 때 우선 확인하기
    위한 기준. 역시 서술적이다.
"""

import glob
import json
import os
import re
from datetime import date as _date

HOLDINGS_PATH = "portfolio/holdings.json"
LEDGER_DIR = "ledger"

# ── 사전등록 플래그 규칙(결과를 보기 전에 고정) ──────────────────────────
STALE_DAYS = 90
MODEL_DIVERGENCE_THRESHOLD = 0.03      # v3.19 엔진 경고 임계값 재사용
CONCENTRATION_THRESHOLD = 0.25
DEEP_LOSS_THRESHOLD = -0.20

RULE_STATUS = "PRE_REGISTERED_NOT_VALIDATED"
"""
⚠️ 이 규칙들은 **사전등록됐을 뿐 검증된 적이 없다.** 플래그가 붙은 종목이
실제로 더 나쁜 결과를 냈는지 확인하려면 실현수익률 관측이 필요한데, 이
프로젝트는 그게 0건이다(예측 34건 동결 / 해소 0건, EXP-001 BLOCKED).
플래그를 '위험 신호'가 아니라 '아직 확인 안 한 것'으로 읽을 것.
"""

REVIEW_RULES = {
    "NO_JUDGMENT": "이 종목에 대한 공식 ledger가 없다 - 엔진이 판정한 적이 없거나 FRAMEWORK_MISMATCH로 제외됐다",
    "JUDGMENT_STALE": f"공식 판정이 {STALE_DAYS}일보다 오래됐다 - 그 사이 분기 실적이 최소 한 번 나왔다",
    "SBC_FLIP": "SBC를 실제 비용으로 차감하면 판정이 뒤집힌다 - 회계 가정 하나에 판정이 달려 있다",
    "MODEL_FRAGILE": f"내재성장률 모델 간 괴리가 {MODEL_DIVERGENCE_THRESHOLD*100:.0f}%p 이상이다 - 판정이 모델 선택에 좌우된다",
    "GROWTH_CAP_BINDING": "Realistic Growth가 상한값 그 자체다 - 성장분석이 결과에 기여하지 않고 Gap이 사실상 Implied Growth 단독으로 결정된다",
    "CONCENTRATION": f"단일 종목 비중이 {CONCENTRATION_THRESHOLD*100:.0f}%를 넘는다",
    "DEEP_LOSS_NO_JUDGMENT": f"수익률이 {DEEP_LOSS_THRESHOLD*100:.0f}% 이하인데 공식 판정이 없다 - 손실 원인을 엔진이 설명하지 못하는 상태",
    "OVERVALUED": "공식 판정이 '과대평가 가능성'이다",
}

_FNAME_RE = re.compile(r"^(?P<ticker>[A-Z.]+)_(?P<date>\d{4}-\d{2}-\d{2})\.json$")


def load_holdings(path: str = HOLDINGS_PATH) -> dict:
    """
    보유 상태를 **읽기만** 한다. 이 모듈에는 쓰기 경로가 없다(테스트로 고정).
    """
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_ledgers(ledger_dir: str = LEDGER_DIR) -> dict:
    """{티커: ledger dict}. 종목당 1건 규칙(v3.32)을 전제한다."""
    out = {}
    for p in sorted(glob.glob(os.path.join(ledger_dir, "*.json"))):
        m = _FNAME_RE.match(os.path.basename(p))
        if not m:
            continue
        with open(p, encoding="utf-8") as f:
            d = json.load(f)
        out[d["meta"]["ticker"]] = d
    return out


def _days_between(a: str, b: str) -> int:
    return (_date.fromisoformat(b) - _date.fromisoformat(a)).days


def review_position(position: dict, weight: float, ledger, today: str) -> dict:
    """
    보유 종목 하나에 사전등록 규칙을 적용해 **플래그와 근거**만 낸다.

    ⚠️ 반환값에 액션(BUY/SELL 등)도 목표비중도 없다 - 의도된 경계다.
    """
    flags = []

    def flag(code, detail):
        flags.append({"code": code, "rule": REVIEW_RULES[code], "detail": detail})

    if weight >= CONCENTRATION_THRESHOLD:
        flag("CONCENTRATION", f"비중 {weight*100:.2f}%")

    ret = position.get("return_pct")

    if ledger is None:
        flag("NO_JUDGMENT", "ledger/에 이 티커의 공식 분석이 없다")
        if ret is not None and ret / 100.0 <= DEEP_LOSS_THRESHOLD:
            flag("DEEP_LOSS_NO_JUDGMENT", f"수익률 {ret:+.1f}%")
        return {
            "ticker": position["ticker"], "weight": weight, "return_pct": ret,
            "has_judgment": False, "judgment": None, "grade": None,
            "expectation_gap": None, "confidence": None,
            "analyzed_at": None, "engine_version": None, "age_days": None,
            "flags": flags,
        }

    meta = ledger["meta"]
    analyzed = meta["analyzed_at"][:10]
    age = _days_between(analyzed, today)
    if age > STALE_DAYS:
        flag("JUDGMENT_STALE", f"분석일 {analyzed} ({age}일 경과)")

    if ledger.get("judgment") == "과대평가 가능성":
        flag("OVERVALUED", f"Gap {ledger['expectation_gap']*100:+.2f}%p")

    sbc = ledger.get("sbc_cross_check") or {}
    if sbc.get("judgment_flipped"):
        flag("SBC_FLIP",
             f"SBC/FCF {sbc['sbc_to_fcf_pct']*100:.1f}%, "
             f"Gap {ledger['expectation_gap']*100:+.2f}%p -> "
             f"{sbc['gap_sbc_adjusted']*100:+.2f}%p "
             f"({ledger['judgment']} -> {sbc['judgment_sbc_adjusted']})")

    models = (ledger.get("implied_growth") or {}).get("models") or {}
    div = models.get("divergence")
    if div is not None and div >= MODEL_DIVERGENCE_THRESHOLD:
        flag("MODEL_FRAGILE",
             f"single {models['single_stage']*100:.2f}% vs "
             f"two {models['two_stage']*100:.2f}% (괴리 {div*100:.2f}%p)")

    cap = ((ledger.get("growth") or {}).get("breakdown") or {}).get("cap_applied")
    if cap:
        flag("GROWTH_CAP_BINDING", str(cap))

    return {
        "ticker": position["ticker"],
        "weight": weight,
        "return_pct": ret,
        "has_judgment": True,
        "judgment": ledger.get("judgment"),
        "grade": ledger.get("judgment_grade"),
        "expectation_gap": ledger.get("expectation_gap"),
        "confidence": (ledger.get("confidence") or {}).get("final"),
        "analyzed_at": analyzed,
        "engine_version": meta.get("engine_version"),
        "age_days": age,
        "flags": flags,
    }


def unheld_candidates(ledgers: dict, held: set) -> list:
    """
    엔진이 S/A로 본 종목 중 **보유하지 않은** 것.

    사용자 요청("저평가나 등급이 s,a인 기업들을 한번 더 분석해서 포트폴리오
    꾸준히 갱신")의 후보 공급원이다. ⚠️ 여기서 '사라'고 말하지 않는다 -
    `build_buylist`가 요구하는 버킷·정성조사가 아직 없는 종목이 대부분이다.
    """
    out = []
    for t, d in ledgers.items():
        if t in held:
            continue
        if d.get("judgment_grade") not in ("S", "A"):
            continue
        sbc = d.get("sbc_cross_check") or {}
        models = (d.get("implied_growth") or {}).get("models") or {}
        out.append({
            "ticker": t,
            "grade": d["judgment_grade"],
            "expectation_gap": d["expectation_gap"],
            "confidence": (d.get("confidence") or {}).get("final"),
            "analyzed_at": d["meta"]["analyzed_at"][:10],
            "sbc_flip": bool(sbc.get("judgment_flipped")),
            "model_divergence": models.get("divergence"),
            "growth_cap_binding": bool(
                ((d.get("growth") or {}).get("breakdown") or {}).get("cap_applied")),
        })
    # 정렬은 사전식(등급 -> Gap) - 합성 점수를 만들지 않는다.
    return sorted(out, key=lambda r: ({"S": 0, "A": 1}[r["grade"]],
                                      -r["expectation_gap"]))


def review_portfolio(today: str, holdings_path: str = HOLDINGS_PATH,
                     ledger_dir: str = LEDGER_DIR) -> dict:
    """
    포트폴리오 전체 점검. 새 계산은 하지 않고 저장된 기록만 대조한다.
    """
    h = load_holdings(holdings_path)
    ledgers = load_ledgers(ledger_dir)
    total = h["total_market_value_krw"]

    positions = []
    for pos in h["positions"]:
        w = pos["market_value_krw"] / total
        positions.append(review_position(pos, w, ledgers.get(pos["ticker"]), today))

    # ⚠️ 보유 합계와 개별 평가금액 합이 정확히 일치하지 않을 수 있다(증권앱
    # 표시 반올림). 조용히 맞추지 않고 **차이를 드러낸다** - 이 프로젝트의
    # "불일치를 자동 해소하지 않는다" 원칙(P0-07 requires_review)과 같다.
    sum_positions = sum(p["market_value_krw"] for p in h["positions"])
    reconciliation = {
        "reported_total": total,
        "sum_of_positions": sum_positions,
        "difference": total - sum_positions,
        "relative_difference": (total - sum_positions) / total,
    }

    held = {p["ticker"] for p in positions}
    with_judgment = [p for p in positions if p["has_judgment"]]
    covered_weight = sum(p["weight"] for p in with_judgment)

    # 검토 우선순위: 플래그 개수 -> 비중. 둘 다 관측 가능한 사실이며
    # 가중합(합성 점수)을 만들지 않는다 - §31 안티기능 등록부.
    queue = sorted(positions, key=lambda p: (-len(p["flags"]), -p["weight"]))

    by_grade = {}
    for p in with_judgment:
        by_grade.setdefault(p["grade"], []).append(p["ticker"])

    return {
        "as_of": today,
        "rule_status": RULE_STATUS,
        "holdings_as_of": h.get("as_of"),
        "currency": h.get("currency"),
        "total_market_value": total,
        "reconciliation": reconciliation,
        "n_positions": len(positions),
        "coverage": {
            "positions_with_judgment": len(with_judgment),
            "weight_with_judgment": covered_weight,
            "weight_without_judgment": 1.0 - covered_weight,
        },
        "grade_distribution": {g: sorted(v) for g, v in sorted(by_grade.items())},
        "positions": positions,
        "review_queue": [
            {"ticker": p["ticker"], "weight": p["weight"],
             "n_flags": len(p["flags"]),
             "flags": [f["code"] for f in p["flags"]]}
            for p in queue
        ],
        "unheld_sa_candidates": unheld_candidates(ledgers, held),
        "not_provided": [
            "액션(BUY/SELL 등) - 분석자가 고른다(engine/thesis.py v3.48 경계)",
            "목표비중 - 새 배분 공식을 만들지 않는다(2026-08-21 PHASE 2 감사)",
            "성과 예측 - 실현수익률 관측이 0건이라 근거가 없다",
        ],
    }
