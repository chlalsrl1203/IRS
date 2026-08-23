"""
engine/base_rates.py 불변조건 (v3.66, 2026-08-23).

이 표는 **외부 1차자료를 그대로 옮긴 것**이라 가장 중요한 테스트는
"옮겨적기가 정확한가"다 - 원문 표는 각 열이 100%로 합산돼야 하므로 그
성질 자체로 전사 오류를 잡을 수 있다.
"""
import pytest

from engine.base_rates import (
    DEFAULT_INFLATION,
    GROWTH_BINS,
    HORIZONS,
    SALES_GROWTH_BASE_RATES,
    SIZE_CLASSES,
    VALIDATION_STATUS,
    assess_growth_plausibility,
    base_rate_at_least,
    deflate_to_2015,
    format_plausibility,
    median_growth,
    nominal_to_real,
    size_class_for,
)

# 원문에서 이미 합계가 안 맞는 유일한 표(89~93%). 파싱 오류가 아니라 출처의 흠.
SOURCE_DEFECTIVE = {"325-700"}


# ── 전사 정확성: 열 합계가 100%인가 ──────────────────────────────────
@pytest.mark.parametrize("size_class", sorted(SALES_GROWTH_BASE_RATES))
@pytest.mark.parametrize("horizon", sorted(HORIZONS))
def test_each_column_sums_to_100(size_class, horizon):
    col = HORIZONS[horizon]
    total = sum(SALES_GROWTH_BASE_RATES[size_class][name][col]
                for name, _, _ in GROWTH_BINS)
    if size_class in SOURCE_DEFECTIVE:
        # 원문 자체가 89.2~92.7%. 이 범위를 벗어나면 전사 오류를 의심할 것.
        assert 88.0 <= total <= 94.0, f"{size_class} {horizon}Y 합계 {total}"
    else:
        assert 99.5 <= total <= 100.5, (
            f"{size_class} {horizon}Y 합계가 {total}% - 전사 오류 의심")


def test_all_tables_have_all_growth_bins():
    for sc, table in SALES_GROWTH_BASE_RATES.items():
        assert set(table) == {n for n, _, _ in GROWTH_BINS}, f"{sc} 행 누락"
        for name, vals in table.items():
            assert len(vals) == 4, f"{sc}/{name}: 1/3/5/10년 4개 열이어야 함"


def test_source_defect_is_documented_not_silently_accepted():
    """
    325-700 구간이 원문에서 합계 미달이라는 사실은 반드시 문서에 남아 있어야
    한다 - 조용히 넘어가면 나중에 이 구간 base rate가 낮게 나오는 이유를
    아무도 모른다.
    """
    import engine.base_rates as br
    assert "325-700" in br.__doc__
    assert "89" in br.__doc__


# ── 단위 함정 (이 프로젝트가 반복해서 겪은 유형) ──────────────────────
def test_nominal_to_real_actually_converts():
    """
    표가 실질인데 명목을 그대로 넣으면 인플레율만큼 낙관 편향된다
    (v3.35 실질/명목 EPS 함정과 동일 계열).
    """
    assert nominal_to_real(0.25, 0.025) == pytest.approx(0.2195, abs=1e-4)
    assert nominal_to_real(0.0, 0.025) < 0          # 명목 0%는 실질 마이너스
    assert nominal_to_real(0.10, 0.0) == pytest.approx(0.10)


def test_assessment_uses_real_not_nominal():
    """
    assess_...가 명목값을 그대로 표에 넣으면 base rate가 실제보다 낮게(=더
    희귀하게) 나온다. 반환값이 두 값을 모두 노출하고 서로 다른지 확인한다.
    """
    a = assess_growth_plausibility(1_000_000_000, 0.25, inflation=0.025)
    assert a["growth_nominal_pct"] == pytest.approx(25.0)
    assert a["growth_real_pct"] == pytest.approx(21.95, abs=0.01)
    assert a["growth_real_pct"] < a["growth_nominal_pct"]


def test_deflator_applied_to_size_class():
    """
    매출 규모 구간도 2015년 달러다. 명목 매출을 그대로 넣으면 더 큰 구간으로
    잘못 배정돼 base rate가 실제보다 낮게 나온다.
    """
    # 명목 $30B -> 2015년 기준 $22.2B -> 12000-25000 구간(25000+ 아님)
    a = assess_growth_plausibility(30_000_000_000, 0.10)
    assert a["size_class"] == "12000-25000"
    assert a["sales_2015_usd_mn"] == pytest.approx(22222.2, abs=1.0)


# ── 계산 성질 ────────────────────────────────────────────────────────
def test_base_rate_is_monotonically_decreasing_in_growth():
    for sc in SALES_GROWTH_BASE_RATES:
        prev = 101.0
        for target in (-10, 0, 5, 10, 15, 20, 25, 30, 40, 50):
            r = base_rate_at_least(sc, target, 10)
            assert r <= prev + 1e-9, f"{sc}: {target}%에서 단조성 위반"
            prev = r


def test_larger_companies_have_lower_high_growth_base_rates():
    """
    Mauboussin의 핵심 관측("as firm size increases the mean and median growth
    rates decline") - 이게 재현되지 않으면 규모 구간 배정이 뒤집힌 것이다.
    """
    small = base_rate_at_least("700-1250", 20.0, 10)
    large = base_rate_at_least("25000+", 20.0, 10)
    mega = base_rate_at_least("50000+", 20.0, 10)
    assert small > large >= mega


def test_size_class_boundaries_are_contiguous():
    for i in range(len(SIZE_CLASSES) - 1):
        assert SIZE_CLASSES[i][1] == SIZE_CLASSES[i + 1][0]
    assert size_class_for(0.0) == "0-325"
    assert size_class_for(324.9) == "0-325"
    assert size_class_for(325.0) == "325-700"
    assert size_class_for(10 ** 9) == "50000+"


def test_deflate_rejects_nonpositive():
    with pytest.raises(ValueError):
        deflate_to_2015(0)
    with pytest.raises(ValueError):
        deflate_to_2015(-5)


def test_unknown_size_class_and_horizon_raise():
    with pytest.raises(ValueError):
        base_rate_at_least("nope", 10.0, 10)
    with pytest.raises(ValueError, match="지원하지 않는 구간"):
        base_rate_at_least("ALL", 10.0, 7)


def test_median_growth_declines_with_size():
    assert median_growth("700-1250", 10) > median_growth("25000+", 10)


# ── 핵심: 판정하지 않는다 ────────────────────────────────────────────
def test_module_never_rejects_or_overrides():
    """
    Mauboussin 자신이 base rate를 'reality check'로 쓰라고 했지 하드컷으로
    쓰라고 하지 않았고, IRS는 v3.19에서 하드 필터가 이중 반영을 만든다는 걸
    이미 실증했다(BRO·BSY 오탈락). 이 모듈에 탈락/수정 함수가 생기면 그
    교훈이 깨진 것이다.
    """
    import engine.base_rates as br
    banned = ("reject", "fail", "filter", "cap_growth", "override", "adjust")
    for name in dir(br):
        if name.startswith("_"):
            continue
        assert not any(b in name.lower() for b in banned), (
            f"{name}: 이 모듈은 병기만 하고 판정하지 않는다")


def test_assessment_carries_caveat_and_source():
    a = assess_growth_plausibility(1_000_000_000, 0.15)
    assert "Credit Suisse HOLT" in a["source"]
    assert "미래 확률이 아니다" in a["caveat"]


def test_validation_status_separates_data_from_method():
    """
    표 자체(관측된 빈도)와 그걸 '희귀'로 부르는 구간(임의 라벨)의 근거
    등급이 다르다는 걸 흐리면 안 된다.
    """
    assert VALIDATION_STATUS["base_rate_table"].startswith("EMPIRICALLY_SUPPORTED")
    assert "IMPLEMENTED_NOT_VALIDATED" in VALIDATION_STATUS["plausibility_tiers"]
    assert "린치" in VALIDATION_STATUS["lynch_type_caps_provenance"]


# ── 실측 회귀: 원문에서 직접 읽은 값 ─────────────────────────────────
def test_verbatim_spot_checks_against_source_pdf():
    """
    원문 PDF에서 눈으로 확인한 셀을 그대로 고정한다. 표를 다시 만지면
    여기서 잡힌다.
    """
    # Full Universe, 3년, 15-20% 구간 = 6.7% (원문 본문이 예시로 직접 서술)
    assert SALES_GROWTH_BASE_RATES["ALL"]["15-20"][HORIZONS[3]] == 6.7
    # >$50,000Mn, 10년, 20-25% = 0.0%
    assert SALES_GROWTH_BASE_RATES["50000+"]["20-25"][HORIZONS[10]] == 0.0
    # $12,000-25,000Mn, 10년, 0-5% = 41.7%
    assert SALES_GROWTH_BASE_RATES["12000-25000"]["0-5"][HORIZONS[10]] == 41.7


def test_mega_cap_high_growth_has_no_precedent():
    """
    이 모듈을 만든 직접적 동기 - IRS는 매출 $60B인 PDD에 명목 25%를 12년간
    부여한다. 그 규모에서 그 성장률의 역사적 선례를 확인한다.
    """
    a = assess_growth_plausibility(60_000_000_000, 0.25, horizon_years=10)
    assert a["size_class"] == "25000+"
    assert a["base_rate_pct"] <= 1.0
    assert a["tier"] in ("NO_PRECEDENT", "EXTREMELY_RARE")


def test_format_is_readable():
    s = format_plausibility(assess_growth_plausibility(5_000_000_000, 0.12))
    assert "%" in s and "중앙값" in s


# ── 규모 조건부 성장상한 (v3.67, 2026-08-23 사용자 승인) ─────────────
from engine.base_rates import (  # noqa: E402
    MIN_BASE_RATE_FOR_CAP, size_conditioned_growth_cap,
)


def test_size_cap_returns_nominal_not_real():
    """
    반환값이 실질이면 명목 Realistic Growth와 비교할 때 인플레율만큼 조용히
    느슨해진다(v3.35 함정). 명목이 실질보다 커야 한다.
    """
    c = size_conditioned_growth_cap(1_000_000_000)
    assert c["cap_nominal"] * 100 > c["cap_real_pct"]
    expected = (1 + c["cap_real_pct"] / 100) * (1 + c["inflation_assumed"]) - 1
    assert c["cap_nominal"] == pytest.approx(expected)


def test_size_cap_declines_with_company_size():
    """Mauboussin의 핵심 관측이 캡에 실제로 반영되는가."""
    small = size_conditioned_growth_cap(800_000_000)["cap_nominal"]
    mid = size_conditioned_growth_cap(20_000_000_000)["cap_nominal"]
    mega = size_conditioned_growth_cap(100_000_000_000)["cap_nominal"]
    assert small > mid > mega


def test_size_cap_always_clears_the_configured_threshold():
    for sales in (2e8, 1e9, 5e9, 3e10, 2e11):
        c = size_conditioned_growth_cap(sales)
        assert c["base_rate_at_cap_pct"] >= MIN_BASE_RATE_FOR_CAP


def test_threshold_is_documented_as_unvalidated():
    """
    1.0%는 검증된 값이 아니라 승인으로 채택된 서술적 기준이다 - 그 사실이
    코드에 남아 있지 않으면 다음 분석자가 실증된 값으로 오해한다.
    """
    import engine.base_rates as br
    src = br.__dict__["__doc__"] or ""
    import inspect
    body = inspect.getsource(br)
    assert "검증된 값이 아니다" in body
    assert MIN_BASE_RATE_FOR_CAP == 1.0


def test_approved_impact_reproduces_exactly():
    """
    2026-08-23 승인 시점에 사용자에게 보고한 캡 값이 그대로 나오는지 고정한다.
    이 값이 바뀌면 승인 근거가 달라진 것이다.
    """
    # PDD: 매출 CNY 431.8B / 7.2 = $60.0B -> 25000+ 구간
    pdd = size_conditioned_growth_cap(431_845_713_000 / 7.2)
    assert pdd["size_class"] == "25000+"
    assert pdd["cap_nominal"] == pytest.approx(0.1787, abs=1e-4)
    # PGR: 매출 $87.7B -> 50000+ 구간
    pgr = size_conditioned_growth_cap(87_670_000_000)
    assert pgr["size_class"] == "50000+"
    assert pgr["cap_nominal"] == pytest.approx(0.1275, abs=1e-4)
    # SE: 매출 $22.9B -> 12000-25000 구간
    se = size_conditioned_growth_cap(22_938_469_000)
    assert se["size_class"] == "12000-25000"
    assert se["cap_nominal"] == pytest.approx(0.1787, abs=1e-4)
