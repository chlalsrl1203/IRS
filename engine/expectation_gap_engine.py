"""
Expectation Gap Engine (현재 버전은 아래 ENGINE_VERSION 참조)

투자 분석 프롬프트 v3.0의 5번/6번/7번 섹션을 실제로 계산하는 스크립트.
LLM이 텍스트로 "시행착오로 근사했다"고 서술하는 대신, 이 스크립트를 실행해서
검증 가능한 숫자를 뽑아낸다.

사용법:
    python3 expectation_gap_engine.py  # 입력값은 아래 __main__ 블록에서 직접 수정

출처: investment_research_system_v3_9_integrated.docx 부록 B
      (2026-07-08 기준 실행 검증 완료 원본 코드, GOOGL 실데이터로 전체 파이프라인 검증)
"""

from dataclasses import dataclass, field
import statistics

# ======================================================================
# 엔진 버전 - 단일 진실원천 (v3.32에서 도입)
# ======================================================================
# ⚠️ 왜 상수로 뽑았나 (2026-08-05 감사에서 발견한 실제 결함):
# 버전 문자열이 `pipeline.py`의 `run_analysis()` 반환 dict 안에 리터럴로
# 박혀 있었고("engine_version": "v3.27"), v3.28에서 `realistic_growth_override`
# (계산 결과를 실제로 바꾸는 기능)를 배선하면서 아무도 그 리터럴을 올리지
# 않았다. 그 결과 `ledger/ROP_2026-08-04.json`은 **v3.27로 스탬프돼 있으면서
# v3.27에는 존재하지도 않는 필드(realistic_growth_override_applied)를 담고
# 있다** - 스탬프가 거짓말을 하는 상태다.
#
# 이 프로젝트가 v3.12 "가짜 버전 사건"에서 배운 게 정확히 이것이다: 버전
# 라벨과 실제 코드가 어긋나면 다음 세션이 재현을 시도할 때 어느 코드로
# 계산된 값인지 특정할 수 없다. 리터럴을 함수 본문 800줄 안쪽에 두는 한
# 같은 누락이 반복될 수밖에 없으므로 모듈 최상단 상수로 올린다.
#
# **새 기능을 배선하면 여기를 올릴 것** - CHANGELOG에 버전 항목을 쓰면서
# 이 상수를 그대로 두면 ledger 전체가 다시 거짓말을 시작한다.
ENGINE_VERSION = "v3.56"

# ======================================================================
# 모델 검증 상태 - v3.46에서 도입(2026-08-15 Phase 0 감사 C-05)
# ======================================================================
# 계약서 36·40·50절: 모델의 **인식론적 지위**를 기계 판독 가능하게 남긴다.
# 이 프로젝트가 반복해서 겪은 오독 위험 - 코드가 계산해서 숫자가 나오면
# 그 숫자가 검증된 것처럼 보인다는 점 - 을 최소한 라벨로는 막는다.
#
# 단계 정의(계약서 40절):
#   IMPLEMENTED_NOT_VALIDATED  구현만 됨
#   SOFTWARE_VALIDATED         테스트가 명세대로 동작함을 보장
#   ECONOMICALLY_SUPPORTED     경제적 근거가 문서화됨
#   EMPIRICALLY_SUPPORTED      실증 데이터로 뒷받침됨
#   CALIBRATED                 실제 결과로 보정됨
#
# ⚠️ 아래 어느 항목도 EMPIRICALLY_SUPPORTED 이상이 아니다. 특히
# confidence_score는 **확률이 아니다** - Confidence 85는 "85% 확률로 맞다"는
# 뜻이 절대 아니며, 실현결과로 보정된 적이 한 번도 없다(계약서 50·149절).
VALIDATION_STATUS = {
    "erp_from_drs": "SOFTWARE_VALIDATED (매핑 자체는 HEURISTIC_MAPPING - 실증근거 없음)",
    "lynch_type_caps": "SOFTWARE_VALIDATED (상하한값 근거 없음 - v3.24 문서화)",
    "confidence_score": "SOFTWARE_VALIDATED / UNCALIBRATED (확률로 해석 금지)",
    "rar": "SOFTWARE_VALIDATED (ER<0 구간에서 방향 반전 - v3.26 경고 배선)",
    "judgment_band": "SOFTWARE_VALIDATED (±5%p는 33종목 관측 기반 시작점)",
    "implied_growth": "SOFTWARE_VALIDATED (Gordon/2단계 DCF - 수학적으로는 정확)",
    "structural_discount_rate": (
        "trend_delta 메커니즘: ECONOMICALLY_SUPPORTED (Chan/Karceski/Lakonishok "
        "2003 JF - 장기 이익성장은 우연 이상 지속되지 않음, 방향 일치·계수 미검증). "
        "초대형주 가산(+3%p/+1%p): IMPLEMENTED_NOT_VALIDATED (근거 문헌 못 찾음 - "
        "2026-08-16 외부연구, reports/historical_validation/structural_discount_research.md)"
    ),
}

# ======================================================================
# DRS 원점수 구간 임계값 - v3.7에서 모듈 상단으로 노출
# v3.6까지는 각 score 함수 안에 숫자가 흩어져 있어 "이 경계값이 왜 이 값인지"
# 검토하기 어려웠다. 여기 한곳에 모으고 근거를 명시한다. 업종별로 이 임계값이
# 부적절하면 (예: 반도체처럼 원래 변동성이 큰 업종) 사유를 기록하고 수정할 것.
# 각 항목은 (경계값, 점수) 튜플의 리스트로, 값이 경계 미만이면 해당 점수를 준다.
# ======================================================================

# 표준편차 기반(매출 변동성, 마진 변동성): 절대 변동폭이 클수록 위험
_STDEV_BUCKETS = [(0.02, 4.0), (0.05, 8.0), (0.10, 14.0), (float("inf"), 20.0)]
# 순부채/EBITDA: 음수(순현금)면 최저, 3배 초과부터 급격히 위험
_LEVERAGE_BUCKETS = [(0.0, 2.0), (1.0, 6.0), (2.0, 10.0), (3.0, 14.0), (4.0, 18.0), (float("inf"), 20.0)]
# 과거 최악 YoY 매출성장(역성장이 심할수록 위험): 경계 이하이면 해당 점수
_CYCLICALITY_BUCKETS = [(-0.15, 20.0), (-0.05, 16.0), (0.0, 12.0), (0.08, 8.0), (float("inf"), 4.0)]


def _bucket_score(value: float, buckets: list, ascending: bool = True) -> float:
    """
    value를 buckets에 대입해 점수 반환.
    ascending=True: value < 경계값 이면 그 점수 채택(작을수록 낮은 점수 구간).
    ascending=False: value <= 경계값 이면 그 점수 채택(_CYCLICALITY_BUCKETS처럼
                     값이 낮을(=역성장이 심할)수록 높은 점수인 경우).
    """
    if ascending:
        for boundary, score in buckets:
            if value < boundary:
                return score
    else:
        for boundary, score in buckets:
            if value <= boundary:
                return score
    return buckets[-1][1]

# ----------------------------------------------------------------------
# 1. Implied Growth 역산 - 단일단계 (Gordon Growth, 성숙기업용)
# ----------------------------------------------------------------------

def implied_growth_single_stage(market_cap: float, fcf0: float, r: float) -> float:
    """
    MarketCap = FCF0(1+g) / (r-g) 를 g에 대해 역산.
    g = (MarketCap*r - FCF0) / (MarketCap + FCF0)
    """
    if market_cap <= 0 or fcf0 == 0:
        raise ValueError("MarketCap과 FCF0는 0이 될 수 없음 (Data Missing 처리 필요)")
    if market_cap + fcf0 <= 0:
        raise ValueError(
            f"MarketCap+FCF0({market_cap+fcf0:.1f})<=0: FCF 적자 규모가 시총과 맞먹거나 초과함(v3.4 가드). "
            f"Gordon Growth 모델 자체가 성립하지 않음. [Model Not Applicable]로 표기할 것."
        )
    g = (market_cap * r - fcf0) / (market_cap + fcf0)
    if g >= r:
        raise ValueError(
            f"g({g*100:.2f}%) >= r({r*100:.2f}%): Gordon Growth 무한등비급수가 수렴하지 않음. "
            f"이 결과는 수학적으로 무의미하다(발산하는 급수의 형식적 값일 뿐). "
            f"FCF0가 음수이거나 0에 가까운 Turnaround 기업에서 주로 발생한다(INTC 실전 테스트에서 확인, 2026-07-07). "
            f"이런 경우 5번 Expectation Gap 섹션을 [Model Not Applicable]로 표기하고, "
            f"9번 밸류에이션 섹션에서 EV/Sales 등 매출 기반 지표로 대체할 것."
        )
    return g

# ----------------------------------------------------------------------
# 2. Implied Growth 역산 - 2단계 (고성장기업용, 이분탐색)
# ----------------------------------------------------------------------

def _two_stage_market_cap(g: float, fcf0: float, r: float, n: int, g_terminal: float) -> float:
    """주어진 g에서 이론적 시가총액(PV of FCF + PV of terminal value) 계산"""
    if r <= g_terminal:
        raise ValueError("r은 g_terminal보다 커야 함")
    pv_explicit = 0.0
    fcf_t = fcf0
    for t in range(1, n + 1):
        fcf_t = fcf_t * (1 + g)
        pv_explicit += fcf_t / ((1 + r) ** t)
    terminal_fcf = fcf_t * (1 + g_terminal)
    terminal_value = terminal_fcf / (r - g_terminal)
    pv_terminal = terminal_value / ((1 + r) ** n)
    return pv_explicit + pv_terminal

def implied_growth_two_stage(
    market_cap: float,
    fcf0: float,
    r: float,
    n: int,
    g_terminal: float,
    g_low: float = -0.20,
    g_high: float = 0.60,
    tolerance: float = 1e-6,
    max_iter: int = 200,
):
    """
    이분탐색으로 MarketCap을 만족하는 g를 찾는다.
    반환값: (수렴한 g, 반복 로그 리스트, 최종 오차율)
    """
    if fcf0 <= 0:
        raise ValueError(
            f"FCF0({fcf0:.1f})<=0: two-stage 모델은 FCF0*(1+g)^t 형태로 부호를 그대로 유지하므로 "
            f"g를 아무리 바꿔도 음수 궤적이 반전되지 않는다. 즉 이 모델은 흑자전환(적자->흑자) "
            f"경로 자체를 표현할 수 없는 구조적 한계가 있다(v3.5). "
            f"이런 경우 5번 섹션 전체를 [Model Not Applicable]로 표기하고 9번에서 EV/Sales로 대체할 것."
        )
    log = []
    lo, hi = g_low, g_high
    f_lo = _two_stage_market_cap(lo, fcf0, r, n, g_terminal) - market_cap
    f_hi = _two_stage_market_cap(hi, fcf0, r, n, g_terminal) - market_cap

    if f_lo * f_hi > 0:
        raise ValueError(
            f"탐색 구간 [{g_low}, {g_high}] 안에 해가 없음. "
            f"구간을 넓히거나 입력값(r, N, g_terminal)을 재검토할 것."
        )

    for i in range(1, max_iter + 1):
        mid = (lo + hi) / 2
        f_mid = _two_stage_market_cap(mid, fcf0, r, n, g_terminal) - market_cap
        error_pct = abs(f_mid) / market_cap * 100
        # v3.32 버그수정: implied_cap 자리에 g_guess와 똑같은 mid가 들어가 있었다
        # (복붙 실수). 로그 전용 필드라 계산 결과에는 영향이 없었지만, 수렴이
        # 이상할 때 이 로그를 보고 원인을 찾으려 하면 "이 g에서 시총이 얼마로
        # 나왔는가"라는 핵심 정보가 통째로 없는 셈이었다.
        log.append({
            "iter": i,
            "g_guess": round(mid, 6),
            "implied_cap": round(f_mid + market_cap, 2),
            "error_pct": round(error_pct, 6),
        })

        if abs(f_mid) < market_cap * tolerance:
            return mid, log, error_pct

        if f_lo * f_mid < 0:
            hi = mid
            f_hi = f_mid
        else:
            lo = mid
            f_lo = f_mid

    raise RuntimeError(f"{max_iter}회 반복 후 수렴 실패. 입력값 재검토 필요.")

# ----------------------------------------------------------------------
# 3. ERP(에쿼티 리스크 프리미엄) - DRS 연동 명시적 매핑
# ----------------------------------------------------------------------

def erp_from_drs(drs: float, base_erp: float = 0.05, max_add: float = 0.03) -> float:
    """
    ERP = base_erp + (DRS/100) * max_add
    DRS 0 -> ERP 5%, DRS 100 -> ERP 8%

    ⚠️ **Validation Status: HEURISTIC_MAPPING (경험적 미검증)** — v3.46에서 명시.
    기존 docstring은 "고정 규칙이며 임의 조정 금지"라는 **규범**만 말하고 이
    매핑의 **인식론적 지위**는 말하지 않았다. 사실관계를 분명히 한다:

    - 이 선형 매핑(5%~8%)의 근거는 이 코드베이스·문서 어디에도 없다. 어떤
      실증 데이터로도 보정(calibrate)된 적이 없다.
    - 따라서 이것은 경제이론적 사실이 아니라 **이 프로젝트가 채택한 휴리스틱**
      이다. "DRS가 높으면 요구수익률도 높다"는 방향성만 가정할 뿐, 그 기울기
      (100점당 3%p)에 실증 근거가 없다.
    - 실측된 부작용: DRS 0~100 전 구간이 ERP 3%p 폭으로만 사상되기 때문에,
      DRS 주관입력을 관측범위 끝에서 끝까지 흔들어도 Gap이 판정 경계를
      넘지 못한다(v3.44 gap_distribution이 34종목 전건에서 확인 -
      "취약성은 성장률 축에 있지 DRS 축에는 없다").

    **값은 바꾸지 않는다.** 근거 없이 유지하던 숫자를 근거 없는 다른 숫자로
    바꾸는 것은 개선이 아니며(LYNCH_TYPE_CAPS·P/B 임계값과 동일 판단),
    바꾸면 축적된 과거 ledger 전체와 비교 불가능해진다.

    규칙 자체를 바꾸고 싶으면 base_erp/max_add 값을 바꾸되 반드시 사유를 기록.
    """
    if not (0 <= drs <= 100):
        raise ValueError("DRS는 0~100 범위")
    return base_erp + (drs / 100) * max_add

# ----------------------------------------------------------------------
# 4. N(성장 지속기간) 캡
# ----------------------------------------------------------------------

# ----------------------------------------------------------------------
# 3-1. 스케일/통화 이상 탐지 - v3.46 신규(2026-08-15 Phase 2)
# ----------------------------------------------------------------------

# ⚠️ 관측 기반 탐지 밴드이지 밸류에이션 판단이 아니다.
# 2026-08-15 기준 ledger 34종목의 FCF수익률(FCF0/시가총액) 실측 범위는
# 1.50%(KLAC) ~ 17.95%(ACGL), 중앙값 5.64%다. 아래 밴드는 그 범위에 여유를
# 두고(하단 3배, 상단 1.4배) **자릿수 오류만** 걸리도록 잡았다 - 34종목 중
# 어느 것도 발동하지 않는다.
FCF_YIELD_PLAUSIBLE_MIN = 0.005   # 0.5%
FCF_YIELD_PLAUSIBLE_MAX = 0.25    # 25%


def check_scale_plausibility(fcf0: float, market_cap: float) -> tuple:
    """
    FCF0와 시가총액의 자릿수가 맞는지 점검한다. 반환값: (ok: bool, warning: str|None)

    **왜 필요한가 (2026-08-15 Phase 2 감사에서 실측으로 확인한 조용한 실패):**
    시가총액에 스케일/통화 오류가 있어도 single_stage 경로는 **경고 없이 그대로
    실행되어 판정까지 흘러간다.** BRO 실데이터로 검증한 결과:

        정상            FCF수익률   6.03% -> Gap  +7.43%p (저평가)
        통화혼재(÷7.1)  FCF수익률  42.79% -> Gap +34.35%p (저평가, A등급→S등급)
        100배 과소      FCF수익률 602.62% -> Gap +96.22%p (저평가, 매수리스트 1위감)
        100배 과대      FCF수익률   0.06% -> Gap  +1.19%p (판정이 적정가로 뒤집힘)

    넷 다 실행에 성공했고 경고가 하나도 없었다. two_stage는 이분탐색이 해를 못
    찾아 우연히 막히지만, 그 오류 메시지가 "r/N/g_terminal을 재검토하라"고
    **엉뚱한 곳을 가리켜** 분석자가 원인을 찾지 못한다.

    이 프로젝트는 같은 계열의 사고를 이미 두 번 겪었다 - RAR 100배 오류(4종목),
    TYL SBC 3배 오류(2차 출처 인용). 자릿수가 조용히 어긋나는 것이 이 프로젝트의
    가장 반복적인 실패 유형이다.

    ⚠️ **자동으로 고치지 않는다**(계약서 30절): "100배 차이나니 100으로 나눈다"는
    식의 자동보정은 금지다 - 어느 쪽이 틀렸는지 코드가 알 수 없기 때문이다.
    탐지해서 드러내기만 하고, 판단과 수정은 분석자가 한다. 실행도 막지 않는다
    (진짜로 저 구간에 있는 종목이 있을 수 있으므로).

    ⚠️ **알려진 한계 - 이 가드가 잡지 못하는 것(2026-08-15 실측)**:
    탐지 여부가 **그 종목의 기저 FCF수익률에 의존**한다. 100배 오류는 기저와
    무관하게 전부 잡히지만, 통화 오류(7.1배)는 기저가 낮은 종목에서 밴드를
    벗어나지 못한다:

        CDNS(기저 1.71%) x7.1 -> 12.14%  탐지 실패 (PDD 정상값 12.94%와 구별 불가)
        KLAC(기저 1.50%) x7.1 -> 10.65%  탐지 실패
        BRO (기저 6.03%) x7.1 -> 42.81%  탐지 성공
        PGR (기저13.71%) x7.1 -> 97.34%  탐지 성공

    **어떤 임계값으로도 이 둘은 분리되지 않는다** - 오류값 12.14%와 정상값
    12.94%가 겹치기 때문이다. 즉 이 가드는 **자릿수(약 100배) 오류의 안전망일
    뿐, 통화 오류 전반을 막아주지 않는다.** 비USD 종목(PDD=CNY, ONON=CHF)은
    여전히 `currency` 필드와 수작업 대조로 확인해야 한다.
    """
    if market_cap <= 0:
        return False, (
            f"[스케일 점검 불가] market_cap={market_cap:,.0f}이 0 이하다."
        )
    fcf_yield = fcf0 / market_cap
    if FCF_YIELD_PLAUSIBLE_MIN <= fcf_yield <= FCF_YIELD_PLAUSIBLE_MAX:
        return True, None
    return False, (
        f"[스케일/통화 이상 의심] FCF수익률(FCF0/시가총액)이 {fcf_yield*100:.2f}%로 "
        f"탐지 밴드({FCF_YIELD_PLAUSIBLE_MIN*100:.1f}~{FCF_YIELD_PLAUSIBLE_MAX*100:.0f}%)를 "
        f"벗어났다. 2026-08-15 기준 ledger 34종목 실측 범위는 1.50~17.95%(중앙값 "
        f"5.64%)다. **밸류에이션 판단이 아니라 자릿수 점검 신호**이므로 다음을 "
        f"먼저 확인할 것: (1) 시가총액과 재무제표의 **통화가 같은가**(PDD는 CNY, "
        f"ONON은 CHF - USD 시총과 섞으면 7배 어긋난다) (2) 단위가 같은가(원 단위 "
        f"vs 백만 단위) (3) FCF0가 최근 회계연도가 맞는가. 확인 결과 값이 정말 "
        f"맞다면 이 경고는 무시해도 되나, 무시했다는 사실을 메모에 남길 것 - "
        f"자동보정은 하지 않는다(계약서 30절)."
    )


def capped_n(n_requested: int, n_min: int = 8, n_max: int = 15) -> int:
    """
    해자 강도를 이유로 N을 임의로 늘려 밸류에이션을 정당화하는 것을 막기 위한 캡.
    n_max를 벗어나려면 프롬프트 상에서 별도 정당화 섹션 작성 의무.
    """
    return max(n_min, min(n_requested, n_max))

# ----------------------------------------------------------------------
# 5-0. DRS 원점수(0~20) 산출 규칙 - v3.6 신규
# ----------------------------------------------------------------------

def revenue_volatility_score(revenue_cagr_3y: float, revenue_cagr_5y: float, revenue_cagr_10y: float) -> float:
    """3/5/10y 매출 CAGR 간 표준편차를 _STDEV_BUCKETS 구간으로 매핑."""
    stdev = statistics.pstdev([revenue_cagr_3y, revenue_cagr_5y, revenue_cagr_10y])
    return _bucket_score(stdev, _STDEV_BUCKETS, ascending=True)


def margin_volatility_score(operating_margins: list) -> float:
    """최근 5년 안팎의 연간 영업이익률 리스트의 표준편차를 _STDEV_BUCKETS 구간으로 매핑."""
    if len(operating_margins) < 2:
        raise ValueError("영업이익률은 최소 2개 연도 이상 필요함")
    stdev = statistics.pstdev(operating_margins)
    return _bucket_score(stdev, _STDEV_BUCKETS, ascending=True)


def leverage_score(net_debt_to_ebitda: float) -> float:
    """순부채/EBITDA를 _LEVERAGE_BUCKETS 구간으로 매핑. 순현금이면(음수) 최저점."""
    return _bucket_score(net_debt_to_ebitda, _LEVERAGE_BUCKETS, ascending=False)


def cyclicality_score(worst_yoy_revenue_growth: float, demand_sensitivity_pct: float = 0.0) -> float:
    """
    worst_yoy_revenue_growth: 관측 가능한 과거 구간 중 최악 분기/연도의 YoY 매출 성장률
    (역성장이면 음수). demand_sensitivity_pct(0~1): 이 매출이 거시경기/수요 사이클에 얼마나
    강하게 연동되는지에 대한 근거 있는 추정치.
    """
    base = _bucket_score(worst_yoy_revenue_growth, _CYCLICALITY_BUCKETS, ascending=False)
    adjustment = min(max(demand_sensitivity_pct, 0.0), 1.0) * 4.0
    return min(base + adjustment, 20.0)


def competition_intensity_score(
    competitor_threat_weights: list,
    market_share_trend_pp_per_year: float,
    active_antitrust_or_regulatory_case: bool,
) -> float:
    """
    competitor_threat_weights: 실질적 위협이 되는 경쟁자들의 상대적 위협도 리스트, 각 0~1.
    market_share_trend_pp_per_year: 연간 시장점유율 변화(pp, 하락이면 음수).
    active_antitrust_or_regulatory_case: 진행 중인 반독점/규제 소송 여부.
    """
    score = min(sum(w * 12.0 for w in competitor_threat_weights), 12.0)
    if market_share_trend_pp_per_year < 0:
        score += min(abs(market_share_trend_pp_per_year) * 20.0, 6.0)
    if active_antitrust_or_regulatory_case:
        score += 2.0
    return min(score, 20.0)


def classify_lynch_type(revenue_cagr_5y: float, cyclicality_raw_score: float, market_cap: float) -> tuple:
    """
    성장률/경기민감도/시총 규모로 fast_grower/stalwart/slow_grower/cyclical을 규칙 기반 분류.
    turnaround/asset_play는 정성적 사건이라 이 함수로 자동 분류하지 않는다.
    v3.9: 반환값이 (lynch_type, note) 튜플. cyclicality>=14와 fast_grower 조건이 동시 충족되면
    note에 dual-fit 경고를 남긴다.
    """
    if cyclicality_raw_score >= 14:
        also_fits_fast_grower = (
            (revenue_cagr_5y >= 0.20 and market_cap < 500) or
            (revenue_cagr_5y >= 0.15 and market_cap < 1000)
        )
        note = None
        if also_fits_fast_grower:
            note = (
                f"[분류 애매] cyclicality_raw_score={cyclicality_raw_score}로 cyclical 기준을 "
                f"충족하지만 revenue_cagr_5y={revenue_cagr_5y*100:.1f}%도 fast_grower 기준을 "
                "충족한다. cyclical을 기본 채택했으나, cyclicality 점수의 원인이 이미 지나간 "
                "일회성 위기(예: 팬데믹)뿐이라면 fast_grower로 오버라이드할지 검토할 것."
            )
        return "cyclical", note
    if revenue_cagr_5y >= 0.20 and market_cap < 500:
        return "fast_grower", None
    if revenue_cagr_5y >= 0.15 and market_cap < 1000:
        return "fast_grower", None
    if revenue_cagr_5y <= 0.05:
        return "slow_grower", None
    return "stalwart", None

# ----------------------------------------------------------------------
# 5. DRS (Downside Risk Score) - 업종별 가중치 반영
# ----------------------------------------------------------------------

@dataclass
class DRSInputs:
    """
    v3.5: 5개 항목을 Optional로 변경. 진짜로 평가 불가/무의미하면 None으로 두되,
    반드시 excluded_reasons에 사유를 적어야 한다.
    """
    revenue_volatility: float = None
    margin_volatility: float = None
    leverage: float = None
    cyclicality: float = None
    competition_intensity: float = None
    weights: dict = field(default_factory=lambda: {
        "revenue_volatility": 1.0,
        "margin_volatility": 1.0,
        "leverage": 1.0,
        "cyclicality": 1.0,
        "competition_intensity": 1.0,
    })
    excluded_reasons: dict = field(default_factory=dict)

    def score(self) -> float:
        raw = {
            "revenue_volatility": self.revenue_volatility,
            "margin_volatility": self.margin_volatility,
            "leverage": self.leverage,
            "cyclicality": self.cyclicality,
            "competition_intensity": self.competition_intensity,
        }
        applicable = {k: v for k, v in raw.items() if v is not None}
        excluded = [k for k in raw if raw[k] is None]
        if not applicable:
            raise ValueError("DRS 5개 항목 중 최소 1개는 평가값이 있어야 함")
        missing_reason = [k for k in excluded if k not in self.excluded_reasons]
        if missing_reason:
            raise ValueError(
                f"항목을 제외(None)하려면 excluded_reasons에 사유를 반드시 적어야 함. 사유 없는 제외 항목: {missing_reason}"
            )
        total_weight = sum(self.weights[k] for k in applicable)
        weighted_sum = sum(applicable[k] * self.weights[k] for k in applicable)
        return (weighted_sum / total_weight) * 5

# ----------------------------------------------------------------------
# 6. Realistic Growth 산출 (v3.2 신규: 서술형 근사 금지, 규칙 기반 계산)
# ----------------------------------------------------------------------

# ⚠️ v3.24 문서화(2026-08-01 방법론 감사 M-1, 권고 #6): 이 상하한값들의 근거(왜
# 하필 25%/12%/5%/20%/30%/10%인가)는 이 코드베이스 어디에도 없다 - 피터 린치의
# 원저서 분류법에서 관용적으로 쓰이는 수치를 그대로 가져온 것으로 추정되며,
# 이 프로젝트가 자체 데이터로 검증한 값이 아니다. 특히 fast_grower 25%는
# 12년 성장 지속(capped_n() 기본값)과 결합하면 FCF 14.6배를 의미하는데, 이는
# 역사적으로 극소수만 달성한 궤적이다.
#
# **상한이 실제로 바인딩되면 그 종목의 Gap은 Realistic Growth 계산 전체(매출·
# FCF CAGR, 구조적 할인)를 무시하고 순수하게 `cap - Implied Growth`가 된다** -
# 즉 공들여 계산한 성장분석이 결과에 아무 기여를 하지 못하고, 종목 간 순위는
# 오직 "누가 더 싼가(Implied Growth)"로만 결정된다. 2026-08-01 감사 시점
# 36종목 중 DUOL/MNDY/PDD/SE 4종목이 정확히 25.00%로 이 상한에 걸려 있었다.
#
# 하향 조정은 하지 않기로 결정했다 - 이 프로젝트가 이미 채택한 원칙(P/B 임계값을
# ACGL/PGR 2건만으로 고정하지 않은 것과 동일)대로, 근거 없이 임의의 새 숫자로
# 바꾸는 것은 근거 없이 유지하는 것보다 나을 게 없다. 대신 상한이 바인딩될 때마다
# `run_analysis()`가 이 사실과 함의를 `data_limitations`에 명시적으로 남긴다
# (아래 `realistic_growth_estimate` 호출부 및 pipeline.py 참고) - 캡이 조용히
# 순위를 결정하는 상황을 최소한 눈에 보이게는 만든다.
LYNCH_TYPE_CAPS = {
    "fast_grower": (-0.05, 0.25),
    "stalwart": (0.00, 0.12),
    "slow_grower": (-0.05, 0.05),
    "cyclical": (-0.10, 0.20),
    "turnaround": (-0.20, 0.30),
    "asset_play": (-0.05, 0.10),
}

def structural_discount_rate(
    revenue_cagr_3y: float,
    revenue_cagr_10y: float,
    market_cap: float,
    base_discount: float = 0.10,
    deceleration_sensitivity: float = 0.5,
    min_discount: float = 0.05,
    max_discount: float = 0.30,
    baseline_distorted_by_recovery: bool = False,
) -> float:
    """
    최근 성장(3y)이 장기 평균(10y)보다 느려지고 있으면(trend_delta>0) 할인폭을 키우고,
    가속 중이면 줄인다. 초대형주는 규모 자체의 평균회귀 압력을 반영해 가산한다.
    v3.9: baseline_distorted_by_recovery=True면 trend_delta의 절반만 반영(V자 반등 왜곡 보정).
    """
    trend_delta = revenue_cagr_10y - revenue_cagr_3y
    if baseline_distorted_by_recovery and trend_delta > 0:
        trend_delta *= 0.5
    discount = base_discount + trend_delta * deceleration_sensitivity
    if market_cap >= 1000:
        discount += 0.03
    elif market_cap >= 200:
        discount += 0.01
    return max(min_discount, min(max_discount, discount))


def check_deceleration_double_count(
    structural_discount_applied: float,
    lynch_type_overridden_down: bool,
    deceleration_threshold: float = 0.10,
) -> tuple:
    """
    v3.8 신규: structural_discount와 lynch_type 하향 오버라이드가 같은 둔화 증거를
    이중 반영하는지 점검. 반환값: (경고 없음 여부, 경고 문자열|None)
    """
    if lynch_type_overridden_down and structural_discount_applied > deceleration_threshold:
        return False, (
            f"[이중 반영 경고] structural_discount_rate가 매출 둔화를 반영해 이미 "
            f"{structural_discount_applied*100:.1f}% 할인을 적용했는데, lynch_type도 하향"
            "오버라이드했다. 두 조치가 같은 둔화 증거를 근거로 한 것이라면 과도한 이중 페널티일 "
            "수 있다. lynch_type 하향의 근거가 매출 둔화와 무관하다면(예: 리더십 리스크) 이 "
            "경고는 무시해도 되나, 그 사유를 명시적으로 서술할 것."
        )
    return True, None


def default_terminal_growth(
    rf: float,
    spread_below_rf: float = 0.01,
    floor: float = 0.02,
    ceiling: float = 0.045,
) -> float:
    """g_terminal을 무위험금리(rf)에서 spread_below_rf만큼 뺀 값으로 강제(floor/ceiling으로 극단값 방지)."""
    return max(floor, min(ceiling, rf - spread_below_rf))


def operating_margin_from_series(operating_income_by_year: list, revenue_by_year: list) -> list:
    """
    v3.8 신규: margin_volatility_score()에 넣을 영업이익률을 EBITDA마진 등 근사치로
    대체하는 관행을 막기 위한 헬퍼. 영업이익 원자료에서 직접 연도별 영업이익률 계산.
    """
    if len(operating_income_by_year) != len(revenue_by_year) or len(operating_income_by_year) < 2:
        raise ValueError("operating_income/revenue 리스트는 길이가 같고 최소 2개 연도 이상이어야 함")
    if any(rev <= 0 for rev in revenue_by_year):
        raise ValueError("revenue는 모두 0보다 커야 함")
    return [oi / rev for oi, rev in zip(operating_income_by_year, revenue_by_year)]


def capex_intensity_from_series(capex_by_year: list, revenue_by_year: list) -> dict:
    """
    v3.7 신규: capex/매출 비중을 연도별 원자료에서 직접 계산.
    반환값: {"current": ..., "avg": ..., "delta": ..., "by_year": [...]}
    """
    if len(capex_by_year) != len(revenue_by_year) or len(capex_by_year) < 2:
        raise ValueError("capex/revenue 리스트는 길이가 같고 최소 2개 연도 이상이어야 함")
    if any(rev <= 0 for rev in revenue_by_year):
        raise ValueError("revenue는 모두 0보다 커야 함")
    ratios = [c / r for c, r in zip(capex_by_year, revenue_by_year)]
    current = ratios[-1]
    avg = sum(ratios) / len(ratios)
    return {"current": current, "avg": avg, "delta": current - avg, "by_year": ratios}


def validate_growth_investment_claim(
    classification: str,
    revenue_cagr_3y: float,
    revenue_cagr_10y: float,
    deceleration_tolerance: float = 0.03,
) -> tuple:
    """
    v3.7 신규: classification="growth_investment" 주장이 최근 매출 둔화와 모순되는지
    최소한의 정합성 가드. 반환값: (is_consistent: bool, warning: str|None)
    """
    if classification != "growth_investment":
        return True, None
    deceleration = revenue_cagr_10y - revenue_cagr_3y
    if deceleration > deceleration_tolerance:
        return False, (
            f"[정합성 경고] growth_investment로 분류했으나 최근 매출성장(3y {revenue_cagr_3y*100:.1f}%)이 "
            f"장기(10y {revenue_cagr_10y*100:.1f}%) 대비 {deceleration*100:.1f}%p 둔화 중임. "
            f"capex 급증을 성장투자로 보려면 매출 재가속 또는 유지 근거를 명시적으로 제시할 것. "
            f"근거가 약하면 margin_erosion으로 재분류 권고."
        )
    return True, None


def fcf_conservatism_adjustment(
    revenue_weighted_cagr: float,
    fcf_cagr_5y: float,
    capex_to_revenue_current: float,
    capex_to_revenue_5y_avg: float,
    classification: str,
    growth_investment_capex_delta_threshold: float = 0.03,
    revenue_cagr_3y: float = None,
    revenue_cagr_10y: float = None,
) -> tuple:
    """
    v3.6/v3.7: FCF CAGR이 매출 가중평균보다 낮으면 채택하되, capex 급증이 성장투자인지
    마진훼손인지 명시적으로 구분. 반환값: (실제 채택할 fcf_cagr_5y, 근거 설명 문자열)
    """
    if classification not in ("growth_investment", "margin_erosion"):
        raise ValueError('classification은 "growth_investment" 또는 "margin_erosion"만 허용')
    consistency_warning = None
    if revenue_cagr_3y is not None and revenue_cagr_10y is not None:
        _, consistency_warning = validate_growth_investment_claim(
            classification, revenue_cagr_3y, revenue_cagr_10y
        )
    capex_intensity_delta = capex_to_revenue_current - capex_to_revenue_5y_avg
    if classification == "growth_investment" and capex_intensity_delta > growth_investment_capex_delta_threshold:
        blended = 0.7 * fcf_cagr_5y + 0.3 * revenue_weighted_cagr
        adjusted = min(blended, revenue_weighted_cagr)
        reason = (
            f"capex/매출 비중이 {capex_intensity_delta*100:.1f}%p 급증했고 성장투자로 판단(근거 필요). "
            f"FCF CAGR({fcf_cagr_5y*100:.2f}%)과 매출 가중평균({revenue_weighted_cagr*100:.2f}%)을 "
            f"70:30 블렌드하여 {adjusted*100:.2f}% 채택."
        )
        if consistency_warning:
            reason += " " + consistency_warning
        return adjusted, reason
    reason = (
        f"FCF CAGR({fcf_cagr_5y*100:.2f}%) 그대로 채택(보수적 유지). "
        f"classification={classification}, capex_intensity_delta={capex_intensity_delta*100:.1f}%p"
    )
    if consistency_warning:
        reason += " " + consistency_warning
    return fcf_cagr_5y, reason


def realistic_growth_estimate(
    revenue_cagr_3y: float = None,
    revenue_cagr_5y: float = None,
    revenue_cagr_10y: float = None,
    fcf_cagr_5y: float = None,
    structural_discount_pct: float = 0.0,
    lynch_type: str = None,
    weights: tuple = (0.5, 0.3, 0.2),
):
    """
    Realistic Growth를 규칙 기반으로 산출한다. 서술형 근사 금지.
    반환값: (최종 Realistic Growth, breakdown 딕셔너리)
    """
    cagrs = [revenue_cagr_3y, revenue_cagr_5y, revenue_cagr_10y]
    available = [(c, w) for c, w in zip(cagrs, weights) if c is not None]
    if not available:
        raise ValueError("Revenue CAGR이 최소 1개 구간이라도 필요함")
    total_w = sum(w for _, w in available)
    base_growth = sum(c * w for c, w in available) / total_w

    conservative_note = None
    if fcf_cagr_5y is not None and fcf_cagr_5y < base_growth:
        conservative_note = f"FCF CAGR({fcf_cagr_5y*100:.2f}%) < Revenue 가중평균({base_growth*100:.2f}%) -> FCF CAGR 채택"
        base_growth = fcf_cagr_5y

    if not (0.0 <= structural_discount_pct <= 1.0):
        raise ValueError("structural_discount_pct는 0~1 범위")
    discounted_growth = base_growth * (1 - structural_discount_pct)

    capped_growth = discounted_growth
    cap_applied = None
    if lynch_type is not None:
        if lynch_type not in LYNCH_TYPE_CAPS:
            raise ValueError(f"알 수 없는 lynch_type: {lynch_type}")
        g_min, g_max = LYNCH_TYPE_CAPS[lynch_type]
        if discounted_growth < g_min:
            capped_growth = g_min
            cap_applied = f"하한 캡 적용({g_min*100:.1f}%)"
        elif discounted_growth > g_max:
            capped_growth = g_max
            cap_applied = f"상한 캡 적용({g_max*100:.1f}%): 벗어나려면 별도 정당화 필요"

    breakdown = {
        "revenue_cagr_inputs": {"3y": revenue_cagr_3y, "5y": revenue_cagr_5y, "10y": revenue_cagr_10y},
        "weights_used": [w for _, w in available],
        "base_growth_before_fcf_check": sum(c * w for c, w in available) / total_w,
        "fcf_conservatism_applied": conservative_note,
        "base_growth_after_fcf_check": base_growth,
        "structural_discount_pct": structural_discount_pct,
        "discounted_growth": discounted_growth,
        "lynch_type": lynch_type,
        "cap_applied": cap_applied,
        "final_realistic_growth": capped_growth,
    }
    return capped_growth, breakdown

# ----------------------------------------------------------------------
# 8. Scenario 확률 산출 - DRS 연동 (v3.2 신규: 임의 확률 배정 금지)
# ----------------------------------------------------------------------

def scenario_probabilities_from_drs(
    drs: float,
    base_bull: float = 0.30,
    base_bear: float = 0.20,
    sensitivity: float = 0.30,
):
    """
    Bull/Base/Bear 확률을 DRS(0~100)에 연동하여 결정론적으로 산출한다.
    반환값: (p_bull, p_base, p_bear, 근거 설명 문자열)
    """
    if not (0 <= drs <= 100):
        raise ValueError("DRS는 0~100 범위")
    deviation = (drs - 50) / 50
    p_bull = base_bull - (sensitivity / 2) * deviation
    p_bear = base_bear + (sensitivity / 2) * deviation
    p_bull = max(0.05, min(0.50, p_bull))
    p_bear = max(0.05, min(0.60, p_bear))
    p_base = 1 - p_bull - p_bear
    if p_base < 0:
        raise ValueError(f"DRS={drs}에서 p_base가 음수({p_base:.3f})가 됨. sensitivity 조정 필요")
    rationale = (
        f"DRS={drs:.1f} (중립점 50 대비 편차 {deviation:+.2f}) 기준: "
        f"p_bull={p_bull*100:.1f}%, p_base={p_base*100:.1f}%, p_bear={p_bear*100:.1f}%. "
        f"DRS가 높을수록(위험 클수록) Bear 확률이 커지고 Bull 확률이 작아지는 방향으로 자동 조정됨."
    )
    return p_bull, p_base, p_bear, rationale

# ----------------------------------------------------------------------
# 9. RAR (Risk-Adjusted Return)
# ----------------------------------------------------------------------

def expected_return(p_bull: float, r_bull: float, p_base: float, r_base: float, p_bear: float, r_bear: float) -> float:
    total_p = p_bull + p_base + p_bear
    if abs(total_p - 1.0) > 1e-6:
        raise ValueError(f"확률 합이 1이 아님: {total_p}")
    return p_bull * r_bull + p_base * r_base + p_bear * r_bear

def rar(expected_return_pct: float, drs: float, allow_sub_one_pct: bool = False) -> float:
    """
    RAR = 기대수익률(%) / DRS

    ⚠️ 단위 규약 (v3.19에서 명문화): expected_return_pct는 **퍼센트 숫자**다.
    기대수익률이 -22.39%라면 -22.39를 넣어야 하며, 소수 -0.2239를 넣으면 안 된다.

    이 규약은 트래커에 축적된 과거 RAR 값들(ADBE 1.7231, CSU 1.6564, ACGL 3.003,
    ANET 0.5895 등)이 모두 퍼센트 입력 기준으로 산출됐음이 2026-07-25 감사에서
    확인되어 확정한 것이다.

    ⚠️ 함정 주의: expected_return()과 scenario_return_from_growth()는 **소수**를
    반환한다(-0.2239). 따라서 rar(expected_return(...), drs)로 그대로 연결하면
    100배 작은 값이 조용히 나온다. 실제로 2026-07-25 세션에서 CDNS/MNST/PH
    세 종목이 이 실수로 잘못 계산됐다(RAR -0.006 vs 정답 -0.599 등).
    소수를 갖고 있다면 rar_from_decimal_return()을 쓸 것.

    v3.19 가드: |expected_return_pct| < 1.0 이면 소수를 잘못 넣은 것으로 간주해
    ValueError를 던진다. 기대수익률이 진짜로 ±1% 미만인 드문 경우에만
    allow_sub_one_pct=True로 명시적으로 통과시킬 것.
    """
    if drs <= 0:
        raise ValueError("DRS는 0보다 커야 함 (0이면 무위험이라는 뜻인데 현실적으로 불가)")
    if not allow_sub_one_pct and abs(expected_return_pct) < 1.0:
        raise ValueError(
            f"expected_return_pct={expected_return_pct}: 절대값이 1.0 미만이라 "
            f"소수(예: -0.2239)를 퍼센트 자리에 잘못 넣은 것으로 보인다(v3.19 가드). "
            f"퍼센트 숫자(예: -22.39)를 넣거나, 소수를 갖고 있다면 "
            f"rar_from_decimal_return()을 쓸 것. 기대수익률이 진짜로 ±1% 미만이면 "
            f"allow_sub_one_pct=True를 명시할 것."
        )
    return expected_return_pct / drs


def rar_from_decimal_return(expected_return_decimal: float, drs: float) -> float:
    """
    v3.19 신규: expected_return()이 반환하는 **소수**를 그대로 받아 RAR을 계산한다.
    내부에서 100을 곱해 퍼센트로 변환하므로 rar()의 단위 함정을 피할 수 있다.

    권장 사용법:
        er = expected_return(p_bull, r_bull, p_base, r_base, p_bear, r_bear)
        rar_value = rar_from_decimal_return(er, drs)
    """
    return rar(expected_return_decimal * 100.0, drs, allow_sub_one_pct=True)

# ----------------------------------------------------------------------
# 10. Scenario 수익률(r_bull/r_base/r_bear) 산출 - v3.5 신규
# ----------------------------------------------------------------------

BULL_PREMIUM_MULTIPLIER = 1.5
BEAR_GROWTH_MULTIPLIER = 0.5


def bull_bear_base_growth_rates(final_realistic_growth: float, lynch_type: str) -> dict:
    """
    g_base/g_bull/g_bear를 규칙 기반으로 확정한다.
    Base = Realistic Growth. Bear = Realistic Growth * BEAR_GROWTH_MULTIPLIER.
    Bull = Realistic Growth * BULL_PREMIUM_MULTIPLIER (LYNCH_TYPE_CAPS 상한 내).
    """
    if lynch_type not in LYNCH_TYPE_CAPS:
        raise ValueError(f"알 수 없는 lynch_type: {lynch_type}")
    _, g_max = LYNCH_TYPE_CAPS[lynch_type]
    g_base = final_realistic_growth
    g_bear = final_realistic_growth * BEAR_GROWTH_MULTIPLIER
    g_bull_candidate = final_realistic_growth * BULL_PREMIUM_MULTIPLIER
    bull_capped_at_base = False
    g_bull = min(g_bull_candidate, g_max)
    if g_bull <= g_base:
        g_bull = g_base
        bull_capped_at_base = True
    return {
        "g_base": g_base,
        "g_bull": g_bull,
        "g_bear": g_bear,
        "bull_capped_at_base": bull_capped_at_base,
        "lynch_type_cap_max": g_max,
    }


def scenario_return_from_growth(
    market_cap_current: float,
    fcf0: float,
    r: float,
    n: int,
    g_terminal: float,
    g_scenario: float,
    fcf_margin_multiplier: float = 1.0,
    convergence_years: float = 3.0,
    annualized: bool = True,
) -> float:
    """
    주어진 g_scenario를 _two_stage_market_cap()에 넣어 정당화되는 시가총액을 구하고,
    현재 시가총액 대비 괴리율을 연율화(기본 3년 수렴 가정)해서 반환한다.
    fcf0가 음수인 turnaround 기업에는 사용 불가.
    """
    if convergence_years <= 0:
        raise ValueError("convergence_years는 0보다 커야 함")
    adjusted_fcf0 = fcf0 * fcf_margin_multiplier
    target_cap = _two_stage_market_cap(g_scenario, adjusted_fcf0, r, n, g_terminal)
    price_ratio = target_cap / market_cap_current
    if not annualized:
        return price_ratio - 1
    if price_ratio <= 0:
        raise ValueError("target_cap/current<=0: 연율화 불가(정상 데이터에서는 발생하지 않음)")
    return price_ratio ** (1.0 / convergence_years) - 1

# ----------------------------------------------------------------------
# 10-1. Stalwart + two_stage RAR 구조적 편향 감지 - v3.13 신규
# ----------------------------------------------------------------------

def check_stalwart_two_stage_bias(lynch_type: str, rar_value: float, model_used: str) -> tuple:
    """
    v3.13 신규: stalwart 유형이 two_stage 모델에서 구조적으로 음수 RAR을
    보이는 경향이 실전 데이터(CTAS, AME 등)에서 반복 확인됨. min_spread
    가드가 거의 모든 stalwart 기본 시나리오에서 발동하기 때문.

    모델을 바꾸는 대신(model="two_stage" 기본값 유지), 이 함수로 편향
    가능성을 감지해 메모에 명시적으로 플래그하도록 강제한다.

    반환값: (bias_flag_required: bool, note: str|None)
    """
    if lynch_type == "stalwart" and model_used == "two_stage" and rar_value < 0:
        return True, (
            "[구조적 편향 플래그] lynch_type=stalwart, model=two_stage에서 "
            f"RAR={rar_value:.3f}(음수)이 산출됨. 이는 사업의 질이 나빠서가 "
            "아니라 two_stage 모델의 min_spread 가드가 stalwart 기본 시나리오 "
            "대부분에서 발동하는 구조적 모델 한계로 알려져 있다(v3.13). "
            "메모 7번(RAR) 섹션에 이 사실을 반드시 명시하고, 다른 stalwart "
            "종목과의 상대 비교로 해석할 것(절대값으로 '나쁜 종목'이라 판단 금지)."
        )
    return False, None

# ----------------------------------------------------------------------
# 10-2. Confidence Score - v3.14 신규 (v3.16에서 하드닝)
# ----------------------------------------------------------------------

def confidence_score(
    sensitivity_check_result: dict,
    gap: float,
    rar: float,
    data_completeness_pct: float,
    lynch_type_cap_applied: bool = False,
    stalwart_two_stage_bias_flagged: bool = False,
    realistic_growth_overridden: bool = False,
    base: int = 50,
) -> dict:
    """
    v3.16 하드닝: v3.14의 confidence_score()가 robustness_check_passed와
    section_5_7_aligned를 순수 bool로 받아, 실제로 강건성 점검을 돌리지
    않고도 그냥 True를 적어 넣으면 통과하는 결함이 있었음(run_self_check가
    v3.15에서 무너졌던 것과 동일 유형의 취약점).

    이제 다음을 강제한다:
    - sensitivity_check_result: expectation_gap_sensitivity_check()의 실제
      반환 dict를 그대로 받는다. 'judgment_flipped' 키가 없으면 잘못된
      호출로 간주해 TypeError.
    - gap, rar: 실수치를 직접 받아 함수 내부에서 부호를 비교한다(과거
      section_5_7_aligned bool을 호출부가 임의로 계산해서 넣던 것과 달리,
      정합 여부 판정 자체를 이 함수가 수행).

    ⚠️ **Validation Status: UNCALIBRATED — 이 점수는 확률이 아니다**(v3.46 명시).
    Confidence 85는 "85% 확률로 판정이 맞다"는 뜻이 **아니다**. base 50에
    가감점을 더한 순위용 점수일 뿐이며, 실현결과로 보정(calibration)된 적이
    한 번도 없다(계약서 50·149절). 확률처럼 표현하거나 기대값 계산에 곱하지 말 것.
    또한 `data_completeness_pct`는 2026-08-15 기준 ledger 34종목 전부가
    기본값 0.9를 써서 이 항목의 판별력은 사실상 0이다(pipeline이 그 사실을
    data_limitations에 기록한다).

    반환값: {"score": ..., "base": ..., "adjustments": {...}, "final": ...}
    """
    if "judgment_flipped" not in sensitivity_check_result:
        raise TypeError(
            "sensitivity_check_result는 expectation_gap_sensitivity_check()의 "
            "실제 반환값이어야 함('judgment_flipped' 키 없음). 구 방식(bool 직접 "
            "전달)은 v3.16부터 지원하지 않음."
        )
    if not (0.0 <= data_completeness_pct <= 1.0):
        raise ValueError("data_completeness_pct는 0~1 범위")

    judgment_flipped = sensitivity_check_result["judgment_flipped"]
    if judgment_flipped is None:
        # error 케이스([Model Not Applicable] 등) - 강건성 점검 자체가 불가능했던 상황이므로
        # 보수적으로 미통과 처리
        robustness_check_passed = False
    else:
        robustness_check_passed = not judgment_flipped

    # gap과 rar의 부호가 같은 방향(둘 다 양수=저평가+매력적, 둘 다 음수=고평가+비매력)이면 정합
    section_5_7_aligned = (gap >= 0 and rar >= 0) or (gap < 0 and rar < 0)

    # v3.32 추가: realistic_growth_overridden.
    # 배경 - v3.28에서 realistic_growth_override를 배선했을 때, 오버라이드가
    # 적용된 뒤에도 growth_breakdown["cap_applied"]에 **이미 우회된 캡의 문구가
    # 그대로 남아** 그 값이 lynch_type_cap_applied로 넘어가고 있었다. ROP가 실제
    # 피해자다: Realistic Growth는 5.5%인데 ledger의 cap_applied는 "상한 캡
    # 적용(12.0%)"이라고 적혀 있고, -5점 페널티도 걸리지 않은 캡을 근거로 붙었다.
    #
    # 캡 플래그를 사실대로(=미적용) 되돌리면 페널티가 사라져 Confidence가 그냥
    # 올라가버리는데, 그건 옳지 않다 - 오버라이드는 분석자가 직접 넣은 주관적
    # 입력이라 오히려 신뢰도를 낮출 사유다. 그래서 캡 플래그는 사실대로 고치되
    # 동일 크기(-5)의 오버라이드 페널티를 별도 항목으로 신설한다. 결과적으로
    # **기존 종목의 Confidence 수치는 하나도 바뀌지 않고**(ROP 89 유지), 감점의
    # 근거만 실제 원인으로 정정된다.
    adjustments = {
        "robustness_check_passed": 15 if robustness_check_passed else 0,
        "section_5_7_aligned": 15 if section_5_7_aligned else 0,
        "data_completeness": round(data_completeness_pct * 15),
        "lynch_type_cap_applied": -5 if lynch_type_cap_applied else 0,
        "stalwart_two_stage_bias_flagged": -5 if stalwart_two_stage_bias_flagged else 0,
        "realistic_growth_overridden": -5 if realistic_growth_overridden else 0,
    }
    raw_score = base + sum(adjustments.values())
    final = max(0, min(100, raw_score))

    return {
        "base": base,
        "sensitivity_check_result": sensitivity_check_result,
        "section_5_7_aligned": section_5_7_aligned,
        "adjustments": adjustments,
        "raw_score": raw_score,
        "final": final,
    }

# ----------------------------------------------------------------------
# 10-3. 판정 세분화(Judgment Grade) - v3.27 신규(2026-08-02)
# ----------------------------------------------------------------------

# 기존 3단계 판정(저평가/적정가/과대평가, ±5%p 경계)은 "저평가 가능성"
# 한 칸에 33종목 중 17개(52%)가 몰려 PDD(+29.16%p)와 BSY(+5.70%p)를 구분하지
# 못했다(High-3 감사에서 지적된 높은 기저율과 같은 증상). 이 함수는 **기존
# 3단계 경계값(±5%p, ±15%p)을 그대로 유지한 채** 그 안을 6단계로 세분화한다 -
# 즉 기존 judgment(저평가/적정가/과대평가)는 하나도 바뀌지 않고, S/A/B는
# 전부 "저평가 가능성"의 부분집합, D/F는 전부 "과대평가 가능성"의
# 부분집합이다(엄밀한 상위호환 - 재검증 불필요, 기존 33종목 ledger 전부에
# Gap 하나만으로 소급 계산 가능).
#
# 경계값 근거(2026-08-02 ledger 33종목 실측 분포에서 자연 단절점 확인):
#   +15%p: TTD(+17.01%p)와 GEN(+12.18%p) 사이가 이 표본에서 가장 큰 간극(4.83%p)
#   +7%p : BRO(+7.43%p)와 BKNG(+5.98%p) 사이 단절(1.45%p)
#   -15%p: 현재 표본에 F등급 종목 없음(KEYS -14.36%p가 가장 근접) - 향후
#          더 큰 과대평가 종목이 나올 때를 대비해 대칭으로 미리 설정
# 상하한 비대칭 없이 대칭 설계(±5/±15)를 택한 이유: 표본 대부분이 저평가
# 후보 스크리닝 결과라 과대평가 종목 수가 원천적으로 적어(2/33) 매도 쪽
# 경계를 표본만으로 확정하기엔 근거가 얕다 - 대칭을 기본값으로 삼고 향후
# 과대평가 표본이 쌓이면 재검토할 것(demand_sensitivity 앵커표와 동일하게
# "시작점"으로 취급).
# v3.31(2026-08-04 사용자 지적): B등급 라벨이 "관심(약매수)"였는데
# `scripts/build_buylist_*.py`는 실제로 S/A등급만 매수 유니버스에 넣고
# B등급은 완전히 배제한다 - 라벨은 "조금 사라"고 말하고 코드는 "안 산다"로
# 동작하는 모순이었다. 이 프로젝트는 Gap 하나만으로 자동매수를 결정하지
# 않는다(항상 정성 심층조사 + Confidence 검증을 거쳐야 실제 비중이 잡힘 -
# is_insurer/sbc_cross_check와 동일한 "병기, 자동판정 안 함" 원칙). B등급은
# 그 정성조사조차 아직 매수리스트 편입을 전제하지 않는 단계라 라벨을
# 정직하게 "관찰대상"으로 바꾼다 - 매수 신호가 아니라 다음 스크리닝에서
# 우선 확인할 후보라는 뜻.
JUDGMENT_GRADE_LABELS = {
    "S": "적극매수",
    "A": "매수",
    "B": "관찰대상(매수리스트 미포함)",
    "C": "중립/보유",
    "D": "비중축소",
    "F": "매도",
}

# ⚠️ v3.32(2026-08-05 감사): 3단계 판정 규칙이 **네 곳에 독립적으로 복사**돼
# 있었다 - pipeline.run_analysis(), pipeline의 SBC 병기 블록,
# expectation_gap_sensitivity_check() 내부의 _judge(), 그리고 크로스체크
# 스크립트 2개(rop/keys). 경계값(±5%p)은 넷 다 같았지만 **중립 구간 라벨이
# 이미 갈라져 있었다**: 셋은 "적정가/경계선"인데 sensitivity_check만
# "적정가"였다. 그 결과 지금까지 저장된 ledger 36건 중 13건이 한 파일 안에서
# `judgment="적정가/경계선"`과 `sensitivity_check.judgment_with_drs="적정가"`를
# 동시에 들고 있다 - 같은 규칙의 같은 출력인데 이름이 다르다.
#
# 이것이 정확히 CLAUDE.md의 Simplicity First 항목이 경고한 상황이다("중복
# 자체가 두 계산이 미묘하게 어긋나는 새로운 버그를 만든다"). 지금은 라벨만
# 어긋났지만, 다음에 경계값을 조정하는 사람이 네 곳 중 셋만 고치면
# `judgment_flipped`(두 _judge() 출력의 != 비교)가 조용히 무의미해진다.
#
# 그래서 규칙을 이 함수 하나로 모으고 나머지는 전부 여기를 호출하게 바꾼다.
# 경계값·라벨 자체는 하나도 바꾸지 않는다(중립 라벨은 다수파이자 pipeline이
# ledger의 최상위 `judgment`에 쓰던 "적정가/경계선"으로 통일).
JUDGMENT_UNDERVALUED = "저평가 가능성"
JUDGMENT_NEUTRAL = "적정가/경계선"
JUDGMENT_OVERVALUED = "과대평가 가능성"

# ⚠️ v3.35(2026-08-06): 판정 경계값 자체도 상수로 뽑는다.
# v3.32에서 판정 *규칙*은 단일화했지만 **경계값 숫자(0.05)는 여전히 리터럴**로
# 남아 있었고, v3.34에서 ETF 엔진의 `required_growth_thresholds(band=0.05)`가
# 같은 값을 독립적으로 또 하드코딩하면서 중복이 되살아났다. "저평가가 되려면
# 필요한 성장률"은 정의상 판정 경계와 같아야 하는데, 두 곳에 따로 적혀 있으면
# 한쪽만 바꿨을 때 엔진이 '저평가라 부르려면 X% 필요'라고 안내해놓고 정작
# 그 X%에서 저평가 판정을 안 내리는 자기모순이 생긴다. 같은 죄를 세 번째로
# 반복하지 않도록 여기서 끝낸다(테스트: test_judgment_band_is_single_source).
JUDGMENT_BAND = 0.05


def judgment_from_gap(gap: float) -> str:
    """
    Expectation Gap(소수, 0.05=+5%p)으로 3단계 판정을 내린다 - 이 프로젝트의
    유일한 판정 규칙 구현체다.

    +5%p 이상 -> 저평가 가능성 / -5%p 이하 -> 과대평가 가능성 / 그 사이 -> 적정가·경계선

    `judgment_grade_from_gap()`과 경계가 정확히 일치한다(S/A/B ⊂ 저평가,
    C = 적정가/경계선, D/F ⊂ 과대평가) - 두 함수의 정합성은
    test_judgment_grade_is_strict_subset_of_judgment가 지킨다.
    """
    if gap >= JUDGMENT_BAND:
        return JUDGMENT_UNDERVALUED
    if gap <= -JUDGMENT_BAND:
        return JUDGMENT_OVERVALUED
    return JUDGMENT_NEUTRAL


def judgment_grade_from_gap(gap: float) -> str:
    """
    Expectation Gap(소수, 0.05=+5%p)만으로 6단계 등급을 매긴다.

    S >= +15%p > A >= +7%p > B >= +5%p > C(중립, -5%p~+5%p) > D >= -15%p > F

    순수 함수(부작용 없음) - 이미 저장된 ledger의 expectation_gap 값에도
    엔진 재실행 없이 그대로 적용 가능하다(과거 33종목 소급 랭킹에 사용).
    """
    if gap >= 0.15:
        return "S"
    if gap >= 0.07:
        return "A"
    if gap >= 0.05:
        return "B"
    if gap > -0.05:
        return "C"
    if gap > -0.15:
        return "D"
    return "F"

# ----------------------------------------------------------------------
# 11. DRS 이중 반영 강건성 점검 - v3.6 재설계
# ----------------------------------------------------------------------

def expectation_gap_sensitivity_check(
    market_cap: float,
    fcf0: float,
    r_with_drs: float,
    base_erp: float,
    rf: float,
    realistic_growth: float,
    n: int,
    g_terminal: float,
    model_used: str = "two_stage",
) -> dict:
    """
    DRS를 반영한 r과 반영하지 않은 r로 각각 Implied Growth를 구해 판정이
    바뀌는지(judgment_flipped) 점검한다.

    v3.19 근본수정(2026-07-26): model_used 파라미터 신규 추가. 이전에는
    이 함수가 **항상 two_stage로만** 판정해서, Section 5가 single_stage를
    쓴 종목(WCN/WM/IDXX 등)에서는 강건성점검이 Section 5와 다른 모델로
    수행되고 있었다 - 검증하려던 것과 다른 것을 검증한 셈이다. 이제
    Section 5와 동일한 모델로 판정하도록 고쳤다(2026-07-26 발견,
    2026-07-25 pipeline.py의 임시 경고문 우회책을 대체).

    model_used를 생략하면 기존 동작(two_stage)과 동일하게 유지된다 -
    호출부가 반드시 Section 5에서 실제로 쓴 모델을 명시적으로 넘길 것.
    """
    if model_used not in ("single_stage", "two_stage"):
        raise ValueError('model_used는 "single_stage" 또는 "two_stage"여야 함')
    r_without_drs = rf + base_erp

    # v3.32: 여기 있던 _judge() 사본을 제거하고 judgment_from_gap()으로 통일했다.
    # 이 사본만 중립 라벨이 "적정가"라서 같은 ledger 안에서 최상위 judgment
    # ("적정가/경계선")와 이름이 갈리는 문제가 있었다(13건). judgment_flipped는
    # 두 판정의 != 비교라 라벨 통일로 바뀌지 않는다.
    _judge = judgment_from_gap

    def _try(r):
        try:
            if model_used == "two_stage":
                g, _, _ = implied_growth_two_stage(market_cap, fcf0, r, n, g_terminal)
            else:
                g = implied_growth_single_stage(market_cap, fcf0, r)
            return g, None
        except ValueError as e:
            return None, str(e)

    g_with, err_with = _try(r_with_drs)
    g_without, err_without = _try(r_without_drs)

    result = {"r_with_drs": r_with_drs, "r_without_drs": r_without_drs}
    if err_with or err_without:
        result["error"] = err_with or err_without
        result["judgment_flipped"] = None
        return result

    gap_with = realistic_growth - g_with
    gap_without = realistic_growth - g_without
    judgment_with = _judge(gap_with)
    judgment_without = _judge(gap_without)
    result.update({
        "implied_growth_with_drs": g_with,
        "implied_growth_without_drs": g_without,
        "gap_with_drs": gap_with,
        "gap_without_drs": gap_without,
        "judgment_with_drs": judgment_with,
        "judgment_without_drs": judgment_without,
        "judgment_flipped": judgment_with != judgment_without,
    })
    return result

# ----------------------------------------------------------------------
# 12. 최종 자기검증 강제 - v3.8 신규
# ----------------------------------------------------------------------

FINAL_SELF_CHECK_ITEMS = [
    "데이터 없는 숫자를 추정하지 않았는가",
    "모든 핵심 판단이 Fact -> Interpretation -> Investment Implication 순서를 따르는가",
    "Bear Case를 Bull Case보다 먼저 충분히 검토했는가",
    "업종에 맞지 않는 지표를 억지로 사용하지 않았는가",
    "좋은 회사와 좋은 주식을 구분했는가",
    "현재 주가가 이미 반영하고 있을 기대를 고려했는가",
    "Implied Growth 계산에 사용한 r, N, g_terminal 값의 근거를 명시했는가",
    "RAR의 확률 가중치(Bull/Base/Bear)를 임의로 배정하지 않고 근거를 제시했는가",
    "Implied Growth, DRS 계산을 서술형 근사가 아니라 실제 코드 실행으로 산출했는가",
    "최종 결론이 현재 가격에서의 투자 행동으로 이어지는가",
    "stalwart+two_stage 조합에서 RAR 음수가 나왔다면 구조적 편향으로 플래그했는가",
]


def run_self_check(answers: dict) -> None:
    """
    ⚠️ DEPRECATED (v3.15) — self_check_v2.run_self_check_v2(memo_text, ctx)로
    대체됨. 이 함수는 불리언 자기신고만 받고 메모 텍스트를 전혀 검증하지
    않는 결함이 확인됨(18개 호출 인스턴스 전체 확인). 새 분석에서는 절대
    사용 금지. 과거 메모 이력 참고용으로만 코드 보존.
    """
    missing = [item for item in FINAL_SELF_CHECK_ITEMS if item not in answers]
    if missing:
        raise ValueError(f"self-check 누락 항목(모두 답해야 함): {missing}")
    failed = [item for item in FINAL_SELF_CHECK_ITEMS if not answers[item]]
    if failed:
        raise ValueError(f"self-check 미통과 항목(메모 발행 전 반드시 해결할 것): {failed}")
    print("Self-check 전체 통과. 메모 발행 가능.")


if __name__ == "__main__":
    print("=== 예시: 가상의 성숙기업 (단일단계) ===")
    g1 = implied_growth_single_stage(market_cap=100_000, fcf0=5_000, r=0.09)
    print(f"Implied Growth (single-stage): {g1*100:.2f}%")

    print("\n=== 예시: 가상의 고성장기업 (2단계, 이분탐색) ===")
    drs_example = 55
    erp = erp_from_drs(drs_example)
    r = 0.045 + erp
    n = capped_n(12)
    g2, log, err = implied_growth_two_stage(
        market_cap=500_000, fcf0=8_000, r=r, n=n, g_terminal=0.035
    )
    print(f"ERP: {erp*100:.2f}%, r: {r*100:.2f}%, N(capped): {n}")
    print(f"Implied Growth (two-stage, 수렴): {g2*100:.2f}%")
    print(f"수렴까지 반복 횟수: {len(log)}, 최종 오차율: {err:.6f}%")
