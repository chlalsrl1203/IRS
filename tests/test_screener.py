import glob
import json

import pytest

from engine.screener import (
    MAX_IMPLIED_GROWTH,
    MIN_REALISTIC_GROWTH,
    VALIDATION_STATUS,
    Candidate,
    estimate_drs,
    implied_growth_from_fcf_yield,
    required_fcf_yield,
    screen,
)


def _ledger_candidates():
    """저장된 ledger에서 '스크리닝 단계에 관측 가능한 값'만 뽑아 후보로 만든다."""
    out = []
    for path in sorted(glob.glob("ledger/*.json")):
        d = json.load(open(path, encoding="utf-8"))
        tick = d["meta"]["ticker"]
        date = d["meta"]["analyzed_at"][:10]
        # WCN/WM/IDXX는 2026-07-26판이 공식 기록(그 전 판은 건너뜀)
        if date != "2026-07-26" and tick in ("WCN", "WM", "IDXX"):
            continue
        inp, dv = d["inputs"], d["derived"]
        out.append((
            Candidate(
                ticker=tick, name=inp["company_name"], market_cap=inp["market_cap"],
                fcf0=dv["fcf0"], revenue_cagr_5y=dv["revenue_cagr_5y"],
                fcf_cagr_5y=dv["fcf_cagr_5y"],
                net_debt_to_ebitda=dv["net_debt_to_ebitda"],
                worst_yoy_revenue=dv["worst_yoy_revenue_growth"],
            ),
            d,
        ))
    return out


def test_implied_growth_formula_matches_engine_exactly():
    """
    y = FCF0/시총 -> g = (r-y)/(1+y) 항등식이 엔진의 single_stage 값과 정확히
    일치해야 한다. ledger 전건에서 오차 0이 확인된 관계다.
    """
    for c, d in _ledger_candidates():
        ig_engine = d["implied_growth"]["models"].get("single_stage")
        if ig_engine is None:
            continue
        r = d["discount_rate"]["r"]
        ig_formula = implied_growth_from_fcf_yield(c.fcf0 / c.market_cap, r)
        assert ig_formula == pytest.approx(ig_engine, abs=1e-12), c.ticker


def test_required_fcf_yield_is_inverse_of_implied_growth():
    r = 0.105
    for g in (-0.02, 0.0, 0.0411, 0.055, 0.08):
        y = required_fcf_yield(g, r)
        assert implied_growth_from_fcf_yield(y, r) == pytest.approx(g, abs=1e-12)


# BSX(2026-08-13): 정식분석은 "저평가 가능성"(Gap +5.87%p)이나 screen()은
# 탈락한다 - screener.py "알려진 한계 2건째"의 반대방향 실사례로 조사·문서화
# 완료(engine/screener.py 참고). 원인은 estimate_drs()가 competition_intensity
# 를 상수(12.0)로 가정하는데 BSX의 실제 연구된 값(5.4, RMD와 동일 - 경쟁자 2곳
# 모두 위협도가 낮음)이 그보다 훨씬 낮아 DRS가 50.6까지 과대평가되기 때문이다.
# ledger 34종목 전수 재확인 결과 상수 12.0 자체는 여전히 정확한 중앙값(median
# 12.0)이라 상수를 조정할 문제가 아니다 - median 대체 방식의 구조적 한계이 첫
# 실제 사례라 여기 문서화된 예외로 남긴다(screen()을 고쳐서 억지로 통과시키면
# 다른 종목의 판정이 조용히 바뀔 위험이 있다).
#
# MEDP(2026-09-02): 정식분석 "저평가 가능성"(Gap +9.80%p)이나 screen()은
# 탈락한다(estimate_drs()가 상수 competition_intensity=12.0을 가정하는데,
# 실제 연구된 값 4.2 - CRO 업종 내 중소형 바이오텍 특화 니치, IQVIA/ICON과의
# 직접경쟁 강도가 낮음 - 가 그보다 훨씬 낮아 DRS가 34.6까지 과대평가된다).
# BSX와 정확히 같은 메커니즘의 두 번째 실사례.
#
# NXT(2026-09-02): 정식분석 "저평가 가능성"(Gap +11.49%p)이나 screen()은
# 탈락한다(competition_intensity 상수 12.0 vs 실제 연구된 값 - 태양광
# 트래커 3사 과점 시장에서 NXT가 시장선도라 위협도를 낮게 평가 - 가 그보다
# 낮아 DRS가 30.6까지 과대평가된다). 세 번째 실사례.
# NOW(2026-09-04): 정식분석 "저평가 가능성"(Gap +8.30%p)이나 screen()은
# 탈락한다. ⚠️ **앞의 셋과 원인이 다르다** - DRS 추정(30.6)이 과대평가된
# 게 아니라 `MAX_IMPLIED_GROWTH`(5.5%)라는 **절대 컷오프**에 걸린다
# (내재성장률 추정 7.03% > 5.5%, FCF수익률 3.13% < 필요 4.63%). 정식분석이
# 통과한 이유는 Realistic Growth가 21.01%로 높아 Gap이 크게 벌어지기
# 때문인데, screen()의 절대 임계값은 그 성장률을 참조하지 않는다.
# 2026-08-23 외부검증(v3.63 Finding 2)이 이미 "MIN_REALISTIC_GROWTH/
# MAX_IMPLIED_GROWTH의 절대 하한 설계에는 학계 반례가 있다"고 기록해둔
# 한계의 첫 실사례다. 임계값은 바꾸지 않는다(바꾸면 다른 종목 판정이
# 조용히 이동한다 - v3.63 결정 #16 REJECT 유지).
KNOWN_SCREENER_FALSE_REJECTIONS = {"BSX", "MEDP", "NXT", "NOW"}


def test_screener_reproduces_known_buy_verdicts():
    """
    ledger 보유 12종목 중 실제 저평가 판정이 난 BRO/BSY는 반드시 통과해야 한다.
    (거짓 탈락은 후보를 영영 놓치므로 스크리너에서 가장 나쁜 오류다)
    """
    for c, d in _ledger_candidates():
        if d["judgment"] == "저평가 가능성":
            if c.ticker in KNOWN_SCREENER_FALSE_REJECTIONS:
                continue
            r = screen(c)
            assert r.passed, f"{c.ticker}(실제 저평가)가 탈락함: {r.failures}"


def test_bsx_false_rejection_is_still_reproducible():
    """
    KNOWN_SCREENER_FALSE_REJECTIONS에 BSX를 넣어둔 근거가 아직 유효한지
    확인한다. estimate_drs()의 competition_intensity 상수(12.0)가 BSX의
    실제 연구된 값(5.4)보다 훨씬 높아 DRS가 과대평가되고, 그 결과 screen()이
    탈락시킨다는 게 원인이었다 - 이 테스트가 실패하면(즉 BSX가 갑자기 통과
    하면) 예외 목록에서 빼야 한다는 신호다.
    """
    for c, d in _ledger_candidates():
        if c.ticker != "BSX":
            continue
        assert d["judgment"] == "저평가 가능성"
        r = screen(c)
        assert not r.passed
        assert r.drs_est == pytest.approx(50.6, abs=0.01)
        return
    pytest.fail("ledger/BSX_*.json을 찾지 못했다 - 예외 근거를 재확인할 수 없음")


def test_medp_false_rejection_is_still_reproducible():
    """
    KNOWN_SCREENER_FALSE_REJECTIONS에 MEDP를 넣어둔 근거가 아직 유효한지
    확인한다. BSX와 동일 메커니즘(competition_intensity 상수 12.0이 실제
    연구된 값 4.2보다 훨씬 높음) - 이 테스트가 실패하면 예외 목록에서
    빼야 한다는 신호다.
    """
    for c, d in _ledger_candidates():
        if c.ticker != "MEDP":
            continue
        assert d["judgment"] == "저평가 가능성"
        r = screen(c)
        assert not r.passed
        assert r.drs_est == pytest.approx(34.6, abs=0.01)
        return
    pytest.fail("ledger/MEDP_*.json을 찾지 못했다 - 예외 근거를 재확인할 수 없음")


def test_nxt_false_rejection_is_still_reproducible():
    """
    KNOWN_SCREENER_FALSE_REJECTIONS에 NXT를 넣어둔 근거가 아직 유효한지
    확인한다. BSX/MEDP와 동일 메커니즘 - 이 테스트가 실패하면 예외
    목록에서 빼야 한다는 신호다.
    """
    for c, d in _ledger_candidates():
        if c.ticker != "NXT":
            continue
        assert d["judgment"] == "저평가 가능성"
        r = screen(c)
        assert not r.passed
        assert r.drs_est == pytest.approx(30.6, abs=0.01)
        return
    pytest.fail("ledger/NXT_*.json을 찾지 못했다 - 예외 근거를 재확인할 수 없음")


def test_screener_rejects_known_overvalued():
    """실제 과대평가 판정이 난 PH는 탈락해야 한다."""
    for c, d in _ledger_candidates():
        if d["judgment"] == "과대평가 가능성":
            r = screen(c)
            assert not r.passed, f"{c.ticker}(실제 과대평가)가 통과함"


def test_leverage_is_not_a_hard_filter_anymore():
    """
    v3.19 역검증에서 잡은 이중반영 회귀 방지: 순부채/EBITDA가 2.5배를 넘어도
    다른 조건이 좋으면 통과해야 한다. BRO(3.50배)/BSY(2.63배)가 실제로
    저평가 판정을 받은 사례가 근거다.
    """
    levered = Candidate(
        ticker="TEST", name="고레버리지 우량성장주", market_cap=10_000_000_000,
        fcf0=650_000_000,          # FCF수익률 6.5%
        revenue_cagr_5y=0.15, fcf_cagr_5y=0.15,
        net_debt_to_ebitda=3.5,    # 구 하드필터(2.5배)에 걸리던 값
        worst_yoy_revenue=0.02,
    )
    result = screen(levered)
    assert result.passed
    assert not any("순부채" in f for f in result.failures)


def test_negative_fcf_is_model_not_applicable():
    c = Candidate(
        ticker="LOSS", name="FCF 적자기업", market_cap=1_000_000_000,
        fcf0=-50_000_000, revenue_cagr_5y=0.30, fcf_cagr_5y=0.30,
        net_debt_to_ebitda=1.0, worst_yoy_revenue=0.10,
    )
    r = screen(c)
    assert not r.passed
    assert any("Model N/A" in f for f in r.failures)


def test_fcf_cagr_binds_when_lower_than_revenue():
    """
    AJG/AZO/ELV가 RG 0%대로 추락한 메커니즘: 매출은 좋은데 FCF가 안 따라오면
    FCF CAGR이 제약이 되어 탈락해야 한다.
    """
    c = Candidate(
        ticker="TRAP", name="매출만 성장하고 FCF는 정체", market_cap=10_000_000_000,
        fcf0=700_000_000,
        revenue_cagr_5y=0.18,   # 매출은 훌륭
        fcf_cagr_5y=0.01,       # FCF는 정체 -> 이쪽이 제약
        net_debt_to_ebitda=1.0, worst_yoy_revenue=0.05,
    )
    r = screen(c)
    assert not r.passed
    assert any("FCF CAGR" in f for f in r.failures)


def test_estimate_drs_moves_with_leverage_and_cyclicality():
    low = estimate_drs(net_debt_to_ebitda=-1.0, worst_yoy_revenue=0.05)
    high = estimate_drs(net_debt_to_ebitda=4.5, worst_yoy_revenue=-0.20)
    assert low < high
    assert 0 <= low <= 100 and 0 <= high <= 100


def test_tier_s_requires_nonpositive_implied_growth():
    """
    S등급은 시장이 역성장을 가격에 반영한 상태(ACGL/ADBE/TIGR/EVO 패턴).
    내재성장률 <= 0 이어야 한다.
    """
    deep = Candidate(
        ticker="DEEP", name="딥밸류 성장주", market_cap=10_000_000_000,
        fcf0=1_200_000_000,     # FCF수익률 12% -> 내재성장률 음수
        revenue_cagr_5y=0.15, fcf_cagr_5y=0.15,
        net_debt_to_ebitda=0.5, worst_yoy_revenue=0.03,
    )
    r = screen(deep)
    assert r.passed
    assert r.tier == "S"
    assert r.implied_growth_est <= 0


# ----------------------------------------------------------------------
# v3.20: capex에 눌린 후보를 단순 탈락과 분리 (NVO 사례에서 도출)
# ----------------------------------------------------------------------

def _nvo_like(**overrides):
    """
    NVO 실측 패턴을 축소 재현: 매출은 강하게 성장(21.7%)하는데 capex 폭증으로
    FCF CAGR(4.92%)만 낮은 케이스.
    """
    base = dict(
        ticker="CAPEXHEAVY", name="capex 폭증 성장주", market_cap=10_000_000_000,
        fcf0=600_000_000,          # FCF수익률 6% - 밸류에이션은 통과권
        revenue_cagr_5y=0.217, fcf_cagr_5y=0.0492,
        net_debt_to_ebitda=0.74, worst_yoy_revenue=0.06,
    )
    base.update(overrides)
    return Candidate(**base)


def test_capex_suppressed_candidate_is_flagged_for_review_not_silently_dropped():
    r = screen(_nvo_like())
    assert not r.passed                      # 기준상 탈락은 맞다
    assert r.review_flags                     # 그러나 재검토 대상으로 표시돼야 한다
    assert "capex 재검토 대상" in r.review_flags[0]


def test_capex_flag_sharpens_when_capex_series_provided():
    r = screen(_nvo_like(capex_to_revenue_current=0.19, capex_to_revenue_avg=0.08))
    assert r.review_flags
    assert "growth_investment" in r.review_flags[0]   # 3%p 임계값 초과를 인지


def test_no_capex_flag_when_revenue_growth_also_insufficient():
    """
    매출 자체가 부진하면 capex 문제가 아니라 그냥 성장이 없는 것이다
    (PYPL 유형) - 재검토 플래그를 붙이면 안 된다.
    """
    r = screen(_nvo_like(revenue_cagr_5y=0.02, fcf_cagr_5y=0.008))
    assert not r.passed
    assert not r.review_flags


def test_no_capex_flag_when_candidate_passes():
    r = screen(_nvo_like(fcf_cagr_5y=0.20))
    assert r.passed
    assert not r.review_flags


def test_no_capex_flag_when_fcf_is_outright_declining():
    """
    FCF가 절대금액으로 줄고 있으면 capex에 '눌린' 게 아니라 사업이 나빠지는
    것이다. capex를 성장투자로 재분류해도 구제되지 않으므로 플래그 대상이
    아니다(UNH: 매출 +10%인데 FCF CAGR -5.18%).
    """
    r = screen(_nvo_like(revenue_cagr_5y=0.10, fcf_cagr_5y=-0.0518))
    assert not r.passed
    assert not r.review_flags


def test_capex_flag_distinguishes_whether_reclassification_can_actually_flip():
    """
    growth_investment 재분류는 FCF CAGR만 올리고 FCF0(내재성장률의 입력)는
    건드리지 않는다. 따라서 밸류에이션까지 탈락한 종목은 재분류해도 통과 못 한다.
    두 경우를 구분하지 않으면 '판정이 바뀔 수 있다'가 거짓 기대를 준다.
    """
    # 밸류에이션 통과(FCF수익률 6%) + 성장만 미달 -> 재분류로 통과 가능
    can_flip = screen(_nvo_like())
    assert can_flip.review_flags
    assert "재분류만으로 통과 가능" in can_flip.review_flags[0]

    # 밸류에이션도 미달(FCF수익률 1.9%, GOOGL 유형) -> 재분류해도 불가
    cannot_flip = screen(_nvo_like(fcf0=190_000_000))
    assert cannot_flip.review_flags
    assert "재분류만으로는 통과 못" in cannot_flip.review_flags[0]


def test_capex_flag_resolves_itself_when_capex_did_not_actually_spike():
    """
    capex를 확인해봤더니 급증이 아니면 '해소됨'으로 결론내야 한다. 계속
    '확인할 것'으로 열어두면 이미 해결된 항목이 재검토 목록에 쌓인다.
    CI(0.64%->0.44%)/PYPL(2.83%->2.53%)이 실제 이 경우였다.
    """
    r = screen(_nvo_like(capex_to_revenue_current=0.0044,
                         capex_to_revenue_avg=0.0064))
    assert r.review_flags
    assert "해소됨" in r.review_flags[0]
    assert "margin_erosion" in r.review_flags[0]


# ── 외부검증 (2026-08-23, 학술문헌·오픈소스 스크리너 대조) ──────────────────
def test_thresholds_unchanged_by_external_research():
    """
    외부조사 결론은 REJECT(임계값 무변경)였다 - 절대 컷오프에 대응하는 학술
    근거가 없다는 사실 자체가 '숫자를 안 바꾼다'는 결정의 근거였다. 값이
    조용히 바뀌면 이 결정이 무력화된다.
    """
    assert MIN_REALISTIC_GROWTH == pytest.approx(0.08)
    assert MAX_IMPLIED_GROWTH == pytest.approx(0.055)


def test_validation_status_documents_lack_of_external_precedent():
    """
    min_realistic_growth/max_implied_growth 둘 다 '절대 컷오프 근거 없음'을
    정직하게 라벨링해야 한다 - 조용히 EMPIRICALLY_SUPPORTED로 승격시키면
    실제로 확보하지 못한 근거 수준을 주장하는 것이 된다.
    """
    assert "IMPLEMENTED_NOT_VALIDATED" in VALIDATION_STATUS["min_realistic_growth"]
    assert "IMPLEMENTED_NOT_VALIDATED" in VALIDATION_STATUS["max_implied_growth"]
    assert "IMPLEMENTED_NOT_VALIDATED" in VALIDATION_STATUS["tier_thresholds"]


def test_max_implied_growth_label_does_not_overclaim_the_architecture_support():
    """
    implied_growth 아키텍처(reverse-DCF 비교) 자체는 ECONOMICALLY_SUPPORTED로
    승격됐지만, 그 지지가 5.5%라는 특정 숫자까지 정당화한다고 주장하면 안 된다
    (v3.52가 structural_discount_rate에서 이미 지킨 경계와 동일).
    """
    label = VALIDATION_STATUS["max_implied_growth"]
    assert "정당화하지 않는다" in label


def test_now_false_rejection_is_a_threshold_not_a_drs_problem():
    """
    NOW를 예외 목록에 넣은 근거가 아직 유효한지 확인한다.

    ⚠️ BSX/MEDP/NXT와 **다른 메커니즘**임을 고정하는 것이 이 테스트의 요점이다.
    저 셋은 `estimate_drs()`의 competition_intensity 상수(12.0)가 실제 연구값보다
    높아 DRS가 과대평가된 사례인데, NOW는 DRS가 아니라 `MAX_IMPLIED_GROWTH`
    (5.5%) 절대 컷오프에 걸린다. 원인을 뭉뚱그리면 나중에 엉뚱한 곳을 고치게 된다.
    """
    for c, d in _ledger_candidates():
        if c.ticker != "NOW":
            continue
        assert d["judgment"] == "저평가 가능성"
        r = screen(c)
        assert not r.passed
        assert any("내재성장률 추정" in f for f in r.failures), (
            f"NOW의 탈락 사유가 절대 임계값이 아니게 바뀌었다: {r.failures}"
        )
        # DRS 과대평가가 원인이 아님을 명시적으로 고정한다
        assert r.drs_est == pytest.approx(30.6, abs=0.01)
        return
    pytest.fail("ledger/NOW_*.json을 찾지 못했다 - 예외 근거를 재확인할 수 없음")
