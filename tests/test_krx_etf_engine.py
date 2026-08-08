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
    format_krx_overlap_table,
    krx_holdings_overlap_report,
    run_krx_wrapper_analysis,
    save_krx_ledger,
)

# 2026-08-07 실측 top10 - test_etf_engine.py와 동일한 골든 데이터 재사용
VOO_TOP10 = {"NVDA": 0.0750, "AAPL": 0.0658, "MSFT": 0.0429, "AMZN": 0.0361,
             "GOOGL": 0.0324, "AVGO": 0.0277, "GOOG": 0.0258, "MU": 0.0201,
             "META": 0.0191, "TSLA": 0.0183}
QQQ_TOP10 = {"AAPL": 0.0815, "NVDA": 0.0786, "MSFT": 0.0558, "MU": 0.0453,
             "AMZN": 0.0422, "AMD": 0.0364, "GOOGL": 0.0323, "AVGO": 0.0306,
             "GOOG": 0.0303, "META": 0.0266}


def voo_us_result(top10_holdings=None):
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
        top10_holdings=top10_holdings,
    )
    return run_etf_analysis(inputs)


def qqq_us_result(top10_holdings=None):
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
        top10_holdings=top10_holdings,
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


def test_unconfirmed_aum_sorts_last_and_renders_as_unconfirmed():
    """
    ⭐ v3.38 후반 완화 - 검색으로 AUM을 못 찾은 종목(KODEX 미국S&P500유틸리티
    등 실제 사례)을 억지 숫자 없이 다룰 수 있어야 한다. aum_krw=None은
    "0원"이 아니라 "모름"이므로 비교 정렬에서 최하위로 밀려야 하고(0원으로
    취급하면 부호 함정으로 최상위에 잘못 뜰 위험이 있다), 표에는 "미확인"으로
    나와야 한다.
    """
    us = voo_us_result()
    known = run_krx_wrapper_analysis(
        tiger_sp500_inputs(krx_ticker="379800", krx_name="KODEX 미국S&P500",
                            expense_ratio=0.0006, aum_krw=100 * 1e8),
        us,
    )
    unknown_aum = run_krx_wrapper_analysis(
        tiger_sp500_inputs(krx_ticker="360200", krx_name="ACE 미국S&P500",
                            expense_ratio=0.0006, aum_krw=None),
        us,
    )
    groups = compare_krx_wrappers([unknown_aum, known])
    ordered = [r["meta"]["ticker"] for r in groups["VOO"]]
    assert ordered == ["379800", "360200"]  # AUM 확인된 쪽이 먼저

    table = format_krx_comparison_table(groups)
    assert "미확인" in table


# ----------------------------------------------------------------------
# krx_holdings_overlap_report - v3.39 후속: 국내 래퍼끼리의 실제 중복노출
# ----------------------------------------------------------------------

def test_overlap_report_measures_between_different_index_krx_wrappers():
    """
    ⭐ 이 기능의 존재 이유 - TIGER 미국S&P500(VOO 재사용)과 TIGER 미국나스닥100
    (QQQ 재사용)을 같이 담으면, 실제로는 각각의 미국 원본(VOO/QQQ)이 공유하는
    메가캡 겹침을 그대로 물려받는다. 새 데이터 없이 이미 있는 미국 원본
    top10_holdings로 이걸 측정할 수 있어야 한다.
    """
    voo_us = voo_us_result(top10_holdings=VOO_TOP10)
    qqq_us = qqq_us_result(top10_holdings=QQQ_TOP10)

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

    report = krx_holdings_overlap_report(
        [tiger_sp500, tiger_nasdaq],
        {"VOO": voo_us, "QQQ": qqq_us},
    )
    assert len(report["pairs"]) == 1
    pair = report["pairs"][0]
    assert pair["pair"] == ("360750", "133690")
    assert pair["us_pair"] == ("VOO", "QQQ")
    # VOO∩QQQ top10 겹침(2026-08-07 실측)과 동일해야 한다 - 새 계산이 아니므로
    assert pair["shared_weight"] == pytest.approx(0.3448, abs=1e-3)
    assert pair["warning"] is not None
    assert "중복노출 경고" in pair["warning"]


def test_overlap_report_flags_same_us_reference_as_same_index():
    """
    ⭐ 같은 미국 원본을 재사용하는 국내 래퍼 두 개(TIGER/KODEX 미국S&P500)는
    정의상 동일 바스켓이다 - '중복노출 경고'가 아니라 '동일지수 경고'로
    구분해서 보고해야 한다(이유가 다르므로 다른 메시지가 필요).
    """
    voo_us = voo_us_result(top10_holdings=VOO_TOP10)
    tiger = run_krx_wrapper_analysis(tiger_sp500_inputs(), voo_us)
    kodex = run_krx_wrapper_analysis(
        tiger_sp500_inputs(krx_ticker="379800", krx_name="KODEX 미국S&P500",
                            expense_ratio=0.0007, aum_krw=100_701 * 1e8),
        voo_us,
    )

    report = krx_holdings_overlap_report([tiger, kodex], {"VOO": voo_us})
    assert len(report["same_index_pairs"]) == 1
    assert report["pairs"] == []  # 동일지수 쌍은 일반 pairs에 안 섞인다
    ov = report["same_index_pairs"][0]
    assert "동일지수 경고" in ov["warning"]
    # 같은 dict를 자기 자신과 비교하므로 shared_weight = VOO_TOP10 비중의 합
    assert ov["shared_weight"] == pytest.approx(sum(VOO_TOP10.values()), abs=1e-6)


def test_overlap_report_skips_wrapper_without_us_holdings():
    """미국 원본에 top10_holdings가 없으면 '겹침 0'이 아니라 skipped로 빠져야 한다."""
    voo_us = voo_us_result(top10_holdings=None)  # holdings 미확보 원본
    qqq_us = qqq_us_result(top10_holdings=QQQ_TOP10)

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

    report = krx_holdings_overlap_report(
        [tiger_sp500, tiger_nasdaq], {"VOO": voo_us, "QQQ": qqq_us},
    )
    assert report["skipped_no_holdings"] == ["360750"]
    assert report["pairs"] == []


def test_overlap_report_does_not_affect_individual_valuation():
    """겹침 측정은 순수 병기 - 개별 KRX 래퍼의 Gap·판정에는 전혀 영향을 주지 않는다."""
    voo_us_no_holdings = voo_us_result(top10_holdings=None)
    voo_us_with_holdings = voo_us_result(top10_holdings=VOO_TOP10)
    a = run_krx_wrapper_analysis(tiger_sp500_inputs(), voo_us_no_holdings)
    b = run_krx_wrapper_analysis(tiger_sp500_inputs(), voo_us_with_holdings)
    assert a["valuation"]["gap_min"] == pytest.approx(b["valuation"]["gap_min"])


def test_format_overlap_table_runs_without_error():
    voo_us = voo_us_result(top10_holdings=VOO_TOP10)
    qqq_us = qqq_us_result(top10_holdings=QQQ_TOP10)
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
    report = krx_holdings_overlap_report(
        [tiger_sp500, tiger_nasdaq], {"VOO": voo_us, "QQQ": qqq_us},
    )
    table = format_krx_overlap_table(report)
    assert "360750" in table
    assert "133690" in table


def test_save_krx_ledger_writes_to_separate_dir(tmp_path):
    us = voo_us_result()
    krx = run_krx_wrapper_analysis(tiger_sp500_inputs(), us)
    path = save_krx_ledger(krx, ledger_dir=str(tmp_path))
    assert "360750" in path
    import json
    with open(path) as f:
        saved = json.load(f)
    assert saved["meta"]["analysis_type"] == "krx_wrapper"
