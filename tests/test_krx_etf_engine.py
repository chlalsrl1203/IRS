"""
KRX 래퍼 ETF 엔진 테스트 (v3.38, 2026-08-07)

골든 데이터는 2026-08-07 실제 조사값이다(총보수·순자산은 stockanalysis.com/
etfshopping.com/삼성자산운용/미래에셋 공식 페이지 기준). 미국 원본은 이미
`ledger_etf/`에 저장된 VOO/QQQ 분석 결과를 재현하는 golden 입력을 그대로 쓴다
(회사 엔진 테스트가 CDNS 실데이터를 고정한 것과 같은 방식).
"""

import json

import pytest

from engine.etf_pipeline import ETFInputs, run_etf_analysis
from engine.krx_etf_engine import expense_ratio_delta, hedge_cost_warning
from engine.krx_etf_pipeline import (
    KRXWrapperInputs,
    compare_krx_wrappers,
    format_krx_comparison_table,
    run_krx_wrapper_analysis,
    save_krx_ledger,
)


def voo_us_result():
    """ledger_etf/VOO_2026-08-07.json을 재현하는 골든 입력."""
    inputs = ETFInputs(
        ticker="VOO",
        name="Vanguard S&P 500 ETF",
        tracks="S&P 500",
        pe_by_source={"stockanalysis(trailing)": 27.53, "FactSet(forward)": 19.6},
        expense_ratio=0.0003,
        n_holdings=505,
        top10_weight=0.37,
        risk_free_rate=0.0461,
        expected_earnings_growth=0.08,
        expected_earnings_growth_basis=(
            "S&P500 장기 명목 EPS 성장률 근사(과거 수십년 실적 7~8%대) [추정치]"
        ),
        dividend_yield=0.0104,
        pct_unprofitable_constituents=0.03,
    )
    return run_etf_analysis(inputs)


def qqq_us_result():
    inputs = ETFInputs(
        ticker="QQQ",
        name="Invesco QQQ Trust",
        tracks="나스닥100",
        pe_by_source={"stockanalysis(trailing)": 33.04, "GoldmanSachs(forward)": 24.0},
        expense_ratio=0.002,
        n_holdings=101,
        top10_weight=0.51,
        risk_free_rate=0.0461,
        expected_earnings_growth=0.11,
        expected_earnings_growth_basis="나스닥100 메가캡 기술주 비중 반영 [추정치]",
        pct_unprofitable_constituents=0.05,
    )
    return run_etf_analysis(inputs)


# 2026-08-07 실측 - TIGER 미국S&P500
def tiger_sp500_inputs(**overrides):
    base = dict(
        krx_ticker="360750",
        krx_name="TIGER 미국S&P500",
        tracks_same_index_as="S&P500 - 미국 원본(VOO)과 동일 지수, 기초지수 원문 확인",
        us_reference_ticker="VOO",
        expense_ratio=0.0006,
        hedged=False,
        aum_krw=204_640 * 1e8,
        listed_date="2020-08-07",
        data_sources=["etfshopping.com(2026-08-07)"],
    )
    base.update(overrides)
    return KRXWrapperInputs(**base)


# ----------------------------------------------------------------------
# expense_ratio_delta / hedge_cost_warning
# ----------------------------------------------------------------------

def test_expense_ratio_delta_basic():
    assert expense_ratio_delta(0.0006, 0.0003) == pytest.approx(0.0003)


def test_expense_ratio_delta_rejects_percent_numbers():
    with pytest.raises(ValueError, match="3% 이상"):
        expense_ratio_delta(0.35, 0.03)  # 35%로 잘못 넣은 경우


def test_expense_ratio_delta_rejects_negative():
    with pytest.raises(ValueError):
        expense_ratio_delta(-0.001, 0.0003)


def test_hedge_cost_warning_none_when_unhedged():
    assert hedge_cost_warning(False) is None


def test_hedge_cost_warning_warns_when_hedged_without_estimate():
    w = hedge_cost_warning(True)
    assert "환헤지 비용 미반영" in w


def test_hedge_cost_warning_reports_estimate_when_given():
    w = hedge_cost_warning(True, estimated_hedge_carry=0.018)
    assert "1.80%p" in w
    assert "미반영" not in w


# ----------------------------------------------------------------------
# run_krx_wrapper_analysis - 핵심: 밸류에이션 재사용
# ----------------------------------------------------------------------

def test_wrapper_reuses_us_valuation_exactly():
    """
    ⭐ 이 엔진의 존재 이유 - 국내 상장 래퍼의 P/E·Gap·판정은 미국 원본과
    완전히 동일해야 한다(같은 주식 바스켓이므로). 바뀌는 건 보수율뿐이라
    net_expected_growth와 최종 Gap만 총보수 차이만큼 달라진다.
    """
    us = voo_us_result()
    krx = run_krx_wrapper_analysis(tiger_sp500_inputs(), us)

    # P/E·기대성장률(차감 전)·위험점수는 완전히 동일해야 한다
    assert krx["pe_divergence"]["min"] == us["pe_divergence"]["min"]
    assert krx["pe_divergence"]["max"] == us["pe_divergence"]["max"]
    assert krx["ers"]["score"] == us["ers"]["score"]
    assert krx["growth"]["expected_earnings_growth"] == us["growth"]["expected_earnings_growth"]

    # 보수율만 다르므로 net_expected_growth와 Gap이 그만큼만 달라져야 한다
    expense_delta = 0.0006 - 0.0003
    assert krx["growth"]["net_expected_growth"] == pytest.approx(
        us["growth"]["net_expected_growth"] - expense_delta, abs=1e-9
    )
    gap_diff = us["valuation"]["gap_min"] - krx["valuation"]["gap_min"]
    assert gap_diff == pytest.approx(expense_delta, abs=1e-9)


def test_wrapper_meta_tags_analysis_type_and_provenance():
    us = voo_us_result()
    krx = run_krx_wrapper_analysis(tiger_sp500_inputs(), us)
    assert krx["meta"]["analysis_type"] == "krx_wrapper"
    assert krx["meta"]["wrapper_of"]["us_reference_ticker"] == "VOO"
    assert krx["meta"]["wrapper_of"]["tracks_same_index_as"]
    assert any("래퍼 재사용" in x for x in krx["data_limitations"])


def test_wrapper_rejects_missing_index_justification():
    with pytest.raises(ValueError, match="tracks_same_index_as"):
        tiger_sp500_inputs(tracks_same_index_as="")


def test_wrapper_rejects_non_plain_product_type():
    """레버리지/인버스/커버드콜은 기초지수를 그대로 복제하지 않아 재사용 전제가 깨진다."""
    with pytest.raises(ValueError, match="product_type"):
        tiger_sp500_inputs(product_type="leveraged")


def test_wrapper_rejects_percent_expense_ratio():
    with pytest.raises(ValueError):
        tiger_sp500_inputs(expense_ratio=0.35)  # 0.35%를 그대로 넣은 실수


def test_hedged_wrapper_gets_hedge_warning():
    us = voo_us_result()
    krx = run_krx_wrapper_analysis(
        tiger_sp500_inputs(krx_ticker="449180", krx_name="KODEX 미국S&P500(H)",
                            hedged=True, expense_ratio=0.0011, aum_krw=9_937 * 1e8),
        us,
    )
    assert any("환헤지 비용" in x for x in krx["data_limitations"])
    assert krx["wrapper"]["hedged"] is True


# ----------------------------------------------------------------------
# compare_krx_wrappers - 같은 지수 그룹 내 비용 비교
# ----------------------------------------------------------------------

def test_compare_ranks_same_index_group_by_cost_not_valuation():
    us = voo_us_result()
    tiger = run_krx_wrapper_analysis(tiger_sp500_inputs(), us)
    kodex = run_krx_wrapper_analysis(
        tiger_sp500_inputs(krx_ticker="379800", krx_name="KODEX 미국S&P500",
                            expense_ratio=0.0007, aum_krw=100_701 * 1e8),
        us,
    )
    ace = run_krx_wrapper_analysis(
        tiger_sp500_inputs(krx_ticker="360200", krx_name="ACE 미국S&P500",
                            expense_ratio=0.0007, aum_krw=40_405 * 1e8),
        us,
    )
    groups = compare_krx_wrappers([kodex, ace, tiger])
    assert list(groups.keys()) == ["VOO"]
    ordered = [r["meta"]["ticker"] for r in groups["VOO"]]
    # TIGER(0.06%)가 가장 저렴하므로 1위, KODEX·ACE(둘 다 0.07%)는 순자산 큰 순
    assert ordered == ["360750", "379800", "360200"]

    # 밸류에이션(Gap)은 보수율이 같은 KODEX·ACE끼리는 완전히 동일해야 한다
    kodex_gap = groups["VOO"][1]["valuation"]["gap_min"]
    ace_gap = groups["VOO"][2]["valuation"]["gap_min"]
    assert kodex_gap == pytest.approx(ace_gap)


def test_compare_groups_by_us_reference_separately():
    voo_us = voo_us_result()
    qqq_us = qqq_us_result()
    tiger_sp500 = run_krx_wrapper_analysis(tiger_sp500_inputs(), voo_us)
    tiger_nasdaq = run_krx_wrapper_analysis(
        KRXWrapperInputs(
            krx_ticker="133690", krx_name="TIGER 미국나스닥100",
            tracks_same_index_as="나스닥100 - 미국 원본(QQQ)과 동일 지수",
            us_reference_ticker="QQQ", expense_ratio=0.0009, hedged=False,
            aum_krw=114_540 * 1e8, listed_date="2010-10-18",
        ),
        qqq_us,
    )
    groups = compare_krx_wrappers([tiger_sp500, tiger_nasdaq])
    assert set(groups.keys()) == {"VOO", "QQQ"}
    assert len(groups["VOO"]) == 1
    assert len(groups["QQQ"]) == 1


def test_format_table_runs_without_error():
    us = voo_us_result()
    tiger = run_krx_wrapper_analysis(tiger_sp500_inputs(), us)
    table = format_krx_comparison_table(compare_krx_wrappers([tiger]))
    assert "360750" in table
    assert "TIGER 미국S&P500" in table


def test_wrapper_handles_json_roundtripped_realized_eps_keys():
    """
    ⭐ 실제 스크립트 실행 중 발견한 버그의 회귀 테스트 - `us_result`를
    `ledger_etf/*.json`에서 `json.load()`로 불러오면 dict 키가 전부 문자열로
    바뀐다(JSON 객체 키는 문자열만 허용). `realized_eps_growth()`는 연도(int)
    뺄셈을 하므로, 변환 없이 그대로 넘기면 "2014"-"2015"에서 TypeError가 난다.
    """
    us = voo_us_result()
    # JSON 왕복을 그대로 재현 - dict 키가 str로 바뀐 상태를 만든다
    us_roundtripped = json.loads(json.dumps(us, default=str))
    # 실측 VOO EPS 앵커를 흉내낸 realized_eps_by_year를 주입(문자열 키)
    us_roundtripped["inputs"]["realized_eps_by_year"] = {
        "2014": 145.51, "2015": 122.17, "2025": 247.98,
    }
    us_roundtripped["inputs"]["realized_eps_basis"] = "nominal"

    # 예외 없이 실행돼야 한다
    krx = run_krx_wrapper_analysis(tiger_sp500_inputs(), us_roundtripped)
    assert krx["growth"]["anchor_cross_check"] is not None


def test_save_krx_ledger_writes_to_separate_dir(tmp_path):
    us = voo_us_result()
    krx = run_krx_wrapper_analysis(tiger_sp500_inputs(), us)
    path = save_krx_ledger(krx, ledger_dir=str(tmp_path))
    assert "360750" in path
    import json
    with open(path) as f:
        saved = json.load(f)
    assert saved["meta"]["analysis_type"] == "krx_wrapper"
