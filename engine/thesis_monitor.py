"""
Thesis Monitor (v3.42 신규, 2026-08-13) - 판정을 낸 뒤 그 판정이 아직 살아있는지 감시한다.

**왜 만들었나 - 이 프로젝트의 모든 통제가 '내부 일관성'에만 걸려 있었다.**
단위규약·버전스탬프·ledger무결성·골든테스트·판정규칙 단일화는 전부 "계산이
자기 자신과 일치하는가"를 묻는다. 2026-08-01 방법론 감사가 High-1로 지적한
"계산이 현실과 일치하는가"(외부 타당성)에 답하는 장치는 그때 **전제조건만**
만들어졌다 - `falsification_conditions`(반증조건 사전기록)와
`price_at_analysis`(분석시점 주가). 둘 다 **쓰기 전용 필드**였다.

12일 뒤(2026-08-13) 확인해보니 그 전제조건들이 이미 데이터로 익어 있었다:
반증조건에 적어둔 트리거 날짜 5건(DUOL 08-05 / PGR 08-04 / TTD 08-06 /
MNDY 08-10 / SE 08-11 Q2 실적)이 **전부 기한이 지났는데 아무도 열어보지
않았다.** 이 모듈은 그 루프를 닫는다.

## 두 가지를 본다

1. **반증조건 기한도래**(`scan_falsification_conditions`): 반증조건 원문에서
   날짜를 추출해 오늘 기준으로 지난 것을 골라낸다. 사전등록된 이진 예측이라
   **통계적 검정력이 필요 없다** - 3주짜리 짧은 이력에서도 유효한 유일한
   종류의 검증이다.

2. **시가총액 변동에 의한 Gap 부식**(`recompute_gap_at_market_cap`):
   펀더멘털 입력을 **전부 고정**하고 시가총액만 오늘 값으로 갈아끼워 Gap을
   재계산한다. 새 방법론이 0줄이다 - 판정이 주가 움직임만으로 이미 죽었는지
   알려준다(매수리스트가 지금 이 순간 유효한지와 직결).

## ⚠️ 설계상 반드시 지킨 것 두 가지

**(1) 재계산 결과를 절대 `ledger/`에 저장하지 않는다.** `run_analysis()`를
재호출하면 오늘 날짜로 스탬프된 완전한 결과가 나오는데, 이걸 `save_ledger()`
하면 같은 티커의 ledger가 2개가 되어 `tests/test_ledger_integrity.py`의
"종목당 1건" 규칙이 즉시 깨진다(v3.32에서 WM/WCN/IDXX 중복이 CLAUDE.md
통계까지 오염시킨 사고와 정확히 같은 유형). 이 모듈은 **메모리에서만**
계산하고 결과는 `reports/`로 나간다. 재계산값은 공식 판정이 아니라
모니터링 신호다 - is_insurer/sbc_cross_check와 동일한 "병기, 자동판정
안 함" 원칙.

**(2) 기한이 지난 날짜를 자동으로 '반증됨'이라 판정하지 않는다.** 날짜
추출은 정규식이라 "트리거 날짜"와 "서술적 날짜"를 구분하지 못한다 - 실제로
TCOM 반증조건의 `2024-04-30~2026-01-13`은 증권소송 집단기간(과거를 서술한
것)이지 확인해야 할 미래 이벤트가 아니다. 그래서 이 모듈은 **날짜 주변
문맥을 함께 반환해 분석자가 즉시 분류할 수 있게만** 한다. 자동 필터링을
넣으면 진짜 트리거를 조용히 놓칠 위험이 있어(false negative가 이 용도에서
가장 나쁜 오류다) 일부러 넣지 않았다.
"""

import re
from dataclasses import replace
from datetime import date

# 반증조건 원문에서 날짜를 뽑는다. 이 프로젝트가 실제로 쓴 표기만 지원한다
# (없는 형식을 미리 넣지 않는다 - Simplicity First).
#   "2026-08-05" / "2026.08.05" / "2027-08" / "2026년 8월 31일" / "Q3 2026"
_DATE_PATTERNS = [
    # 2026-08-05 · 2026.8.5 · 2026/08/05
    (re.compile(r"(20\d{2})[-./](\d{1,2})[-./](\d{1,2})"), "ymd"),
    # 2026-08 · 2027-10 (일 없음)
    (re.compile(r"(20\d{2})[-./](\d{1,2})(?![-./\d])"), "ym"),
    # 2026년 8월 31일 · 2026년 8월
    (re.compile(r"(20\d{2})년\s*(\d{1,2})월(?:\s*(\d{1,2})일)?"), "kr"),
    # Q3 2026 · Q2 FY2026
    (re.compile(r"Q([1-4])\s*(?:FY)?\s*(20\d{2})"), "q"),
    # FY2026 Q3 · 2026 Q3
    (re.compile(r"(?:FY)?(20\d{2})\s*Q([1-4])"), "yq"),
]

# 분기 -> 그 분기의 마지막 날(보수적으로 분기 종료일을 트리거로 본다.
# 실적발표는 분기 종료 후이므로 이 날짜가 지났다고 곧바로 발표된 건 아니다 -
# 그 판단은 분석자 몫이라 context와 함께 돌려준다).
_QUARTER_END = {1: (3, 31), 2: (6, 30), 3: (9, 30), 4: (12, 31)}

CONTEXT_CHARS = 90


def _safe_date(y: int, m: int, d: int):
    """달력에 없는 날짜(예: 2월 30일)는 조용히 버린다 - 오탐이 무해한 방향."""
    try:
        return date(y, m, d)
    except ValueError:
        return None


def extract_trigger_dates(text: str) -> list:
    """
    반증조건 원문 -> [{"date": date, "raw": str, "context": str}] (날짜 오름차순).

    ⚠️ 여기서 나온 날짜가 전부 '확인해야 할 트리거'인 것은 아니다 - 과거를
    서술한 날짜(예: 소송 집단기간)도 같이 잡힌다. 그래서 context를 반드시
    함께 돌려준다(모듈 docstring 설계원칙 (2) 참고).
    """
    if not text:
        return []

    found = {}   # (start_pos) -> record. 같은 위치를 여러 패턴이 잡으면 첫 패턴 우선
    for pattern, kind in _DATE_PATTERNS:
        for m in pattern.finditer(text):
            if any(s <= m.start() < e for s, e in found):
                continue
            g = m.groups()
            if kind == "ymd":
                dt = _safe_date(int(g[0]), int(g[1]), int(g[2]))
            elif kind == "ym":
                dt = _safe_date(int(g[0]), int(g[1]), 1)
            elif kind == "kr":
                dt = _safe_date(int(g[0]), int(g[1]), int(g[2]) if g[2] else 1)
            elif kind == "q":
                mm, dd = _QUARTER_END[int(g[0])]
                dt = _safe_date(int(g[1]), mm, dd)
            else:  # "yq"
                mm, dd = _QUARTER_END[int(g[1])]
                dt = _safe_date(int(g[0]), mm, dd)
            if dt is None:
                continue
            lo = max(0, m.start() - CONTEXT_CHARS)
            hi = min(len(text), m.end() + CONTEXT_CHARS)
            found[(m.start(), m.end())] = {
                "date": dt,
                "raw": m.group(0),
                "context": text[lo:hi].replace("\n", " ").strip(),
            }

    return sorted(found.values(), key=lambda x: x["date"])


def scan_falsification_conditions(ledger: dict, today: date) -> dict:
    """
    ledger 1건의 반증조건을 훑어 기한도래 여부를 분류한다.

    status:
      "no_conditions" - 반증조건 자체가 없음(과거 분석에 소급 작성 금지 원칙상
                        빈 게 정상인 ledger도 많다 - 결함이 아니다)
      "undated"       - 반증조건은 있으나 날짜가 없음(사건 기반 조건. 예: ACGL의
                        "3개 분기 연속 악화되면" - 달력이 아니라 실적을 봐야 함)
      "past_due"      - 날짜가 지난 항목이 있음 -> **확인 필요**
      "pending"       - 날짜가 전부 미래
    """
    fc = (ledger.get("inputs") or {}).get("falsification_conditions")
    ticker = ledger["meta"]["ticker"]
    analyzed_at = ledger["meta"]["analyzed_at"][:10]

    if not fc or not fc.strip():
        return {"ticker": ticker, "analyzed_at": analyzed_at,
                "status": "no_conditions", "past_due": [], "pending": []}

    dates = extract_trigger_dates(fc)
    if not dates:
        return {"ticker": ticker, "analyzed_at": analyzed_at,
                "status": "undated", "past_due": [], "pending": [],
                "conditions_text": fc}

    past = [d for d in dates if d["date"] <= today]
    future = [d for d in dates if d["date"] > today]
    return {
        "ticker": ticker,
        "analyzed_at": analyzed_at,
        "status": "past_due" if past else "pending",
        "past_due": past,
        "pending": future,
        "conditions_text": fc,
    }


# ────────────────────────────────────────────────────────────────────────
# 시가총액 변동에 의한 Gap 부식
# ────────────────────────────────────────────────────────────────────────

# 연도별 시계열 입력 필드 - JSON 왕복하면 키가 전부 문자열이 되므로 정수로
# 되돌려야 한다(v3.38에서 KRX 래퍼가 "2014"-"2015" TypeError로 실제로 겪은 함정).
_YEAR_KEYED_FIELDS = (
    "revenue_by_year", "operating_income_by_year", "operating_cashflow_by_year",
    "capex_by_year", "net_income_by_year", "shareholders_equity_by_year",
    "dividends_paid_by_year", "sbc_by_year",
)


def inputs_from_ledger(ledger: dict):
    """
    저장된 ledger의 inputs를 그대로 AnalysisInputs로 복원한다.

    구 ledger에는 나중에 추가된 필드(realistic_growth_override 등)가 없는데,
    dataclass 기본값이 그 자리를 메우므로 그대로 통과한다 - 값이 없을 때
    기존 동작을 유지하는 opt-in 설계 덕분이다.
    """
    from engine.pipeline import AnalysisInputs

    raw = dict(ledger["inputs"])
    for f in _YEAR_KEYED_FIELDS:
        if raw.get(f):
            raw[f] = {int(k): v for k, v in raw[f].items()}

    valid = set(AnalysisInputs.__dataclass_fields__)
    return AnalysisInputs(**{k: v for k, v in raw.items() if k in valid})


def recompute_gap_at_market_cap(ledger: dict, new_market_cap: float) -> dict:
    """
    펀더멘털 입력을 전부 고정하고 **시가총액만** 바꿔 재계산한다.

    Realistic Growth는 재무 시계열에서만 나오므로 불변이고, Implied Growth만
    움직인다 - 즉 Gap 변화는 전적으로 주가 변동에서 온다.

    ⚠️ 반환값을 `save_ledger()`에 넘기지 말 것(모듈 docstring 설계원칙 (1)).
    """
    from engine.pipeline import run_analysis

    if new_market_cap <= 0:
        raise ValueError("new_market_cap은 0보다 커야 한다")

    base_inputs = inputs_from_ledger(ledger)
    fresh = run_analysis(replace(base_inputs, market_cap=new_market_cap))

    old_mc = ledger["inputs"]["market_cap"]
    return {
        "ticker": ledger["meta"]["ticker"],
        "analyzed_at": ledger["meta"]["analyzed_at"][:10],
        "market_cap_then": old_mc,
        "market_cap_now": new_market_cap,
        "market_cap_change_pct": new_market_cap / old_mc - 1.0,
        "gap_then": ledger["expectation_gap"],
        "gap_now": fresh["expectation_gap"],
        "gap_decay_pp": fresh["expectation_gap"] - ledger["expectation_gap"],
        "judgment_then": ledger["judgment"],
        "judgment_now": fresh["judgment"],
        "judgment_flipped": fresh["judgment"] != ledger["judgment"],
        "grade_then": ledger.get("judgment_grade"),
        "grade_now": fresh.get("judgment_grade"),
        # Realistic Growth는 불변이어야 한다 - 아래 두 값이 다르면 버그다
        # (시가총액이 성장추정에 영향을 주면 안 된다).
        "realistic_growth_then": ledger["growth"]["realistic_growth"],
        "realistic_growth_now": fresh["growth"]["realistic_growth"],
    }


# ────────────────────────────────────────────────────────────────────────
# Drift 3분할 (v3.50, 계약서 §9)
# ────────────────────────────────────────────────────────────────────────
#
# 위 `recompute_gap_at_market_cap`은 "주가만 변했을 때"를 본다. 그런데 실제로
# thesis가 흔들리는 원인은 세 가지이고, **셋을 구분하지 못하면 정반대로
# 대응하게 된다**:
#
#   Price Drift        가격만 변함        -> Gap이 벌어져도 사업은 그대로
#   Fundamental Drift  기업 현실이 변함   -> 근거 기반 기대(Realistic Growth)가 변함
#   Expectation Drift  시장 요구가 변함   -> Implied Growth가 변함
#
# v3.42가 TTD에서 실측한 함정이 정확히 이 지점이다 - 주가가 26.3% 빠지자 Gap이
# +17.01%p -> +20.96%p로 벌어졌는데, 같은 기간 반증조건 3개가 동시 발동했다.
# Gap만 보면 "더 싸졌다"지만 Fundamental Drift를 함께 보면 "서사가 무너지는 중"
# 이다. 셋을 분리하는 것이 가치함정을 구분하는 유일한 방법이다.
#
# ⚠️ Expectation Drift는 Price Drift를 **포함한다**(Implied Growth가 시총과
# FCF0 둘 다에 의존하므로). 두 값을 더해서 쓰지 말 것 - 이중계상이다.
# 그래서 아래 함수는 합계를 만들지 않고 셋을 나란히 놓기만 한다.

DRIFT_KINDS = ("price", "fundamental", "expectation")


def decompose_drift(ledger: dict, current_result: dict) -> dict:
    """
    저장된 공식 분석과 새 분석 결과를 대조해 drift를 세 갈래로 나눈다.

    `current_result`: 새 재무데이터(또는 새 시총)로 다시 돌린 `run_analysis()`
    결과. 이걸 만들려면 어차피 분석을 다시 해야 하므로, **이 함수는 새 계산을
    하지 않는다** - 두 결과를 비교만 한다.

    정확한 항등식(발명 아님):

        Gap = RealisticGrowth - ImpliedGrowth
        ΔGap = ΔRealisticGrowth - ΔImpliedGrowth
             = (Fundamental Drift) - (Expectation Drift)

    Price Drift는 Expectation Drift의 **하위 성분**이라 `gap_analysis.gap_drivers`
    의 OAT 분해를 재사용해 시총 기여분만 뽑는다(잔차도 함께 온다).

    ⚠️ 이 함수는 상태(STRENGTHENING 등)를 판정하지 않는다. drift의 크기와
    방향만 내놓고, thesis 상태는 분석자가 기록한 증거로 `thesis.
    evaluate_thesis_status()`가 정한다(§9: "완전 자동 판정을 서두르지 마라").
    """
    from engine.gap_analysis import gap_drivers

    rg_then = ledger["growth"]["realistic_growth"]
    rg_now = current_result["growth"]["realistic_growth"]
    ig_then = ledger["implied_growth"]["value"]
    ig_now = current_result["implied_growth"]["value"]
    gap_then = ledger["expectation_gap"]
    gap_now = current_result["expectation_gap"]

    mc_then = ledger["inputs"]["market_cap"]
    mc_now = current_result["inputs"]["market_cap"]

    # Price Drift: 시총만 바뀌었다고 볼 때의 Implied Growth 변화(OAT)
    drivers = gap_drivers(ledger, market_cap_now=mc_now)
    price_component = drivers["contributions"]["market_cap"]

    fundamental = rg_now - rg_then
    expectation = ig_now - ig_then

    return {
        "ticker": ledger["meta"]["ticker"],
        "analyzed_at": ledger["meta"]["analyzed_at"][:10],
        "gap_then": gap_then,
        "gap_now": gap_now,
        "gap_change_pp": gap_now - gap_then,

        # ── 세 갈래 ──────────────────────────────────────────────
        "price_drift": {
            "market_cap_then": mc_then,
            "market_cap_now": mc_now,
            "market_cap_change_pct": (mc_now / mc_then - 1.0) if mc_then else None,
            # 시총 변화가 Implied Growth에 기여한 몫(OAT - 유일한 분해 아님)
            "implied_growth_contribution": price_component,
            "method": drivers["method"],
            "residual_is_material": drivers["residual_is_material"],
        },
        "fundamental_drift": {
            "realistic_growth_then": rg_then,
            "realistic_growth_now": rg_now,
            "change_pp": fundamental,
            "note": (
                "재무제표에서만 나오는 값이다 - 여기가 움직였다면 기업의 경제적 "
                "현실이 실제로 변한 것이고, 주가와 무관하다."
            ),
        },
        "expectation_drift": {
            "implied_growth_then": ig_then,
            "implied_growth_now": ig_now,
            "change_pp": expectation,
            "note": (
                "시장이 요구하는 성장률의 변화. **price_drift를 포함한다**"
                "(Implied Growth가 시총과 FCF0 양쪽에 의존) - 둘을 더하지 말 것."
            ),
        },

        # ── 항등식 자기검증 ──────────────────────────────────────
        "identity": {
            "formula": "ΔGap = ΔRealisticGrowth - ΔImpliedGrowth",
            "residual": (gap_now - gap_then) - (fundamental - expectation),
        },

        # ── 해석 보조(판정 아님) ─────────────────────────────────
        "dominant_drift": _dominant_drift(fundamental, expectation),
        "interpretation": _drift_interpretation(fundamental, expectation,
                                                gap_now - gap_then),
    }


def _dominant_drift(fundamental: float, expectation: float) -> str:
    """
    어느 축이 더 크게 움직였는가. **판정이 아니라 읽기 보조**다 -
    크기가 크다고 중요한 것은 아니다(작은 fundamental drift가 반증조건을
    건드리면 그쪽이 결정적이다).
    """
    if abs(fundamental) < 1e-12 and abs(expectation) < 1e-12:
        return "none"
    return "fundamental" if abs(fundamental) > abs(expectation) else "expectation"


def _drift_interpretation(fundamental: float, expectation: float,
                          gap_change: float) -> str:
    """
    ⚠️ 이건 **경고문이지 판정이 아니다.** 가장 위험한 조합(사업이 나빠졌는데
    Gap이 벌어짐 = 가치함정 패턴)을 눈에 보이게 만드는 것이 목적이다.
    """
    if fundamental < 0 and gap_change > 0:
        return (
            "[가치함정 주의] 근거 기반 기대가 **낮아졌는데** Gap은 오히려 벌어졌다. "
            "주가 하락이 펀더멘털 악화를 앞질렀다는 뜻이며, v3.42 TTD가 정확히 "
            "이 패턴이었다(주가 -26.3%에 Gap +3.95%p, 동시에 반증조건 3개 발동). "
            "Gap을 매수 근거로 쓰기 전에 반증조건부터 확인할 것."
        )
    if fundamental > 0 and gap_change < 0:
        return (
            "[선반영 주의] 펀더멘털은 좋아졌는데 Gap은 좁아졌다 - 좋은 소식이 "
            "이미 가격에 반영됐을 가능성(v3.42 SE 실측 패턴)."
        )
    if abs(fundamental) < 1e-12:
        return (
            "펀더멘털 불변, 기대/가격만 변동 - 사업 자체에 대한 판단은 "
            "그대로 유지된다."
        )
    return "펀더멘털과 기대가 같은 방향으로 움직였다 - 특이 신호 없음."
