"""engine/ecd.py — 위임장 PvP·Item 408 inline XBRL 파서 (v4.00). 네트워크 없음."""

import ast
import os
import re

import pytest

from engine import ecd
from engine import qualitative_input as Q

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _ctx(cid, end, start="2024-01-01", dims=""):
    seg = (f"<xbrli:segment><xbrldi:explicitMember dimension=\"{dims.split('=')[0]}\">"
           f"{dims.split('=')[1]}</xbrldi:explicitMember></xbrli:segment>") if dims else ""
    return (f'<xbrli:context id="{cid}"><xbrli:entity><xbrli:identifier scheme="x">1</xbrli:identifier>'
            f"{seg}</xbrli:entity><xbrli:period><xbrli:startDate>{start}</xbrli:startDate>"
            f"<xbrli:endDate>{end}</xbrli:endDate></xbrli:period></xbrli:context>")


def _nf(name, ctx, text, **a):
    attrs = " ".join(f'{k}="{v}"' for k, v in a.items())
    return f'<ix:nonFraction name="{name}" contextRef="{ctx}" {attrs}>{text}</ix:nonFraction>'


PROXY = ("<html><body><ix:header><ix:resources>"
         + _ctx("c1", "2025-12-31") + _ctx("c2", "2024-12-31")
         + _ctx("c9", "2025-12-31", dims="ecd:IndividualAxis=x:JaneMember")
         + "</ix:resources></ix:header>"
         + '<p>Most important measure: <ix:nonNumeric name="ecd:CoSelectedMeasureName" contextRef="c1">'
           "Return on Invested Capital</ix:nonNumeric></p>"
         + _nf("ecd:TotalShareholderRtnAmt", "c1", "150.00")
         + _nf("ecd:PeerGroupTotalShareholderRtnAmt", "c1", "120.00")
         + _nf("ecd:TotalShareholderRtnAmt", "c2", "110.00")
         + _nf("ecd:PeerGroupTotalShareholderRtnAmt", "c2", "130.00")
         # 개인 축이 붙은 사실은 표의 연도 행이 아니다 -> 무시
         + _nf("ecd:TotalShareholderRtnAmt", "c9", "999.00")
         + _nf("ecd:PeoActuallyPaidCompAmt", "c1", "17,392,652", sign="-")
         + "</body></html>")


@pytest.mark.parametrize("name,cat", [
    ("Return on Invested Capital", "return_on_capital"),
    ("Operating ROE", "return_on_capital"),
    ("Relative TSR", "shareholder_return"),
    ("Free Cash Flow", "cash_flow"),
    ("Non-GAAP Diluted EPS", "earnings"),
    ("Fee Related Earnings (FRE)", "earnings"),
    ("consolidated operating income", "earnings"),
    ("Revenue", "revenue_growth"),
    ("Net New Sales", "revenue_growth"),
    ("GAAP Combined Ratio", "other"),       # 보험 언더라이팅 지표 — 사전 규칙상 other
    ("", "other"),
])
def test_classify_measure_rule_order(name, cat):
    assert ecd.classify_measure(name) == cat


def test_bank_enum_matches_rule_categories():
    q = next(x for x in Q.QUESTION_BANK if x.qid == "gov.pay_measure_category")
    assert q.allowed == ecd.MEASURE_CATEGORIES


def test_pvp_from_proxy_latest_year_and_ignores_dimensioned_facts():
    r = ecd.pvp_from_proxy(PROXY)
    assert r["status"] == "OK"
    assert r["measure_category"] == "return_on_capital"
    assert r["period_end"] == "2025-12-31"
    assert r["tsr"] == 150.0 and r["peer_tsr"] == 120.0
    assert r["tsr_vs_peer"] == pytest.approx(0.25)
    assert r["n_years"] == 2
    assert r["peo_cap_not_used"]["2025-12-31"] == -17_392_652.0


def test_pvp_without_ecd_is_not_ok():
    assert ecd.pvp_from_proxy("<html><p>no xbrl</p></html>")["status"] == "NO_ECD"


def test_numeric_value_scale_sign_and_fixed_zero():
    assert ecd.numeric_value({"text": "1.5", "scale": "6"}) == 1_500_000
    assert ecd.numeric_value({"text": "2,000", "sign": "-"}) == -2000
    assert ecd.numeric_value({"text": "—", "format": "ixt:fixed-zero"}) == 0.0
    assert ecd.numeric_value({"text": "n/a"}) is None


def test_nested_ix_tags_are_both_captured():
    html = ('<ix:nonNumeric name="ecd:Rule10b51ArrAdoptedFlag" contextRef="c" format="ixt:fixed-false">'
            '<ix:nonNumeric name="ecd:NonRule10b51ArrAdoptedFlag" contextRef="c" format="ixt:fixed-false">'
            "None</ix:nonNumeric></ix:nonNumeric>")
    names = sorted(f["name"] for f in ecd.ix_facts(html))
    assert names == ["ecd:NonRule10b51ArrAdoptedFlag", "ecd:Rule10b51ArrAdoptedFlag"]


def _periodic(n_adopt, block=True):
    s = ('<ix:nonNumeric name="ecd:Rule10b51ArrAdoptedFlag" contextRef="c">true</ix:nonNumeric>'
         if block else "")
    for i in range(n_adopt):
        s += (f'<ix:nonNumeric name="ecd:TrdArrIndName" contextRef="p{i}">Person {i}</ix:nonNumeric>'
              f'<ix:nonNumeric name="ecd:TrdArrAdoptionDate" contextRef="p{i}">May 1, 2026</ix:nonNumeric>')
    return s


def test_trading_plans_count_and_block_detection():
    r = ecd.trading_plans_from_periodic(_periodic(3))
    assert r == {"has_block": True, "adoptions": 3, "terminations": 0,
                 "individuals": ["Person 0", "Person 1", "Person 2"]}
    assert ecd.trading_plans_from_periodic(_periodic(0, block=False))["has_block"] is False


def test_trading_plan_aggregation_requires_blocks_and_enough_reports():
    ok = [(f"2026-0{i}-01", ecd.trading_plans_from_periodic(_periodic(i))) for i in (1, 2, 3, 4)]
    agg = ecd.trading_plan_adoptions(ok)
    assert agg["status"] == "OK" and agg["answer"] == 10
    assert ecd.trading_plan_adoptions(ok[:2])["status"] == "INSUFFICIENT"
    # 공시 블록이 없는 보고서가 하나라도 있으면 0건으로 읽지 않는다(거짓 청정 신호 방지)
    bad = ok[:3] + [("2026-09-01", ecd.trading_plans_from_periodic(_periodic(0, block=False)))]
    assert ecd.trading_plan_adoptions(bad)["status"] == "NO_BLOCK"


def test_module_has_no_judgment_or_score_function():
    tree = ast.parse(open(os.path.join(ROOT, "engine", "ecd.py"), encoding="utf-8").read())
    names = [n.name for n in tree.body if isinstance(n, ast.FunctionDef)]
    banned = ("score", "verdict", "judge", "decide", "grade", "recommend", "align")
    assert not [n for n in names if any(b in n.lower() for b in banned)]


def test_not_wired_into_valuation_or_portfolio():
    for f in ("engine/pipeline.py", "engine/expectation_gap_engine.py",
              "engine/portfolio_pipeline.py"):
        src = open(os.path.join(ROOT, f), encoding="utf-8").read()
        assert not re.search(r"(import|from)\s+[\w.]*\becd\b|engine\.ecd", src), f
