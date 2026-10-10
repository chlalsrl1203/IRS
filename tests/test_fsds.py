"""engine/fsds.py — SEC 재무제표 데이터셋 리더 (v3.99) 테스트. 네트워크 없음."""

import ast
import csv
import io
import json
import os
import zipfile

import pytest

from engine import fsds
from engine.dilution import (STATUS_FY_COLLISION, STATUS_NO_SHARES, STATUS_OK,
                             dilution_drag_from_fsds)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SUB_HDR = "adsh\tcik\tname\tform\tperiod\tfy\tfp\tfiled\n"
NUM_HDR = "adsh\ttag\tversion\tddate\tqtrs\tuom\tsegments\tcoreg\tvalue\tfootnote\n"


def _dr(text):
    return csv.DictReader(io.StringIO(text), delimiter="\t")


def _num(rows):
    return NUM_HDR + "".join(
        f"{a}\t{t}\tus-gaap/2025\t{d}\t{q}\tUSD\t{s}\t{c}\t{v}\t\n"
        for a, t, d, q, s, v, c in rows)


SUBS = _dr(SUB_HDR
           + "A1\t42\tX CO\t10-K\t20251231\t2025\tFY\t20260220\n"
           + "A0\t42\tX CO\t10-K\t20221231\t2022\tFY\t20230220\n"
           + "Q1\t42\tX CO\t10-Q\t20250930\t2025\tQ3\t20251101\n"
           + "Z9\t99\tOTHER\t10-K\t20251231\t2025\tFY\t20260220\n")


def _erie_like(ni_by_year, a_shares, eps_a, nci=None):
    rows = []
    for y, ni in ni_by_year.items():
        adsh = "A1" if y >= 2023 else "A0"
        d = f"{y}1231"
        rows.append((adsh, "NetIncomeLoss", d, 4, "", ni, ""))
        rows.append((adsh, "WeightedAverageNumberOfDilutedSharesOutstanding", d, 4,
                     "ClassOfStock=CommonClassA;", a_shares[y], ""))
        rows.append((adsh, "EarningsPerShareDiluted", d, 4, "ClassOfStock=CommonClassA;",
                     eps_a[y], ""))
        # Class B: 주식수는 적고 EPS는 크다 — EPS x 주식수가 순이익을 재현하지 않는다
        rows.append((adsh, "WeightedAverageNumberOfDilutedSharesOutstanding", d, 4,
                     "ClassOfStock=CommonClassB;", 2542, ""))
        rows.append((adsh, "EarningsPerShareDiluted", d, 4, "ClassOfStock=CommonClassB;",
                     900.0, ""))
        if nci:
            rows.append((adsh, "NetIncomeLossAttributableToNoncontrollingInterest", d, 4, "",
                         nci[y], ""))
    return rows


def _load(rows):
    subs = fsds.read_submissions(_dr(SUB_HDR
                                     + "A1\t42\tX CO\t10-K\t20251231\t2025\tFY\t20260220\n"
                                     + "A0\t42\tX CO\t10-K\t20221231\t2022\tFY\t20230220\n"),
                                 ["0000000042"])
    return subs, fsds.read_num(_dr(_num(rows)), set(subs), fsds.SHARE_TAGS + fsds.REVENUE_TAGS)


YEARS = range(2020, 2026)
NI = {y: 300e6 + 20e6 * (y - 2020) for y in YEARS}
SH = {y: 52_300_000 for y in YEARS}
EPS = {y: round(NI[y] / SH[y], 2) for y in YEARS}


def test_parse_segments_and_quarter_of():
    assert fsds.parse_segments("ClassOfStock=CommonClassA;EquityComponents=X;") == {
        "ClassOfStock": "CommonClassA", "EquityComponents": "X"}
    assert fsds.parse_segments("") == {}
    assert fsds.quarter_of("2026-02-23") == (2026, 1)
    assert fsds.quarter_of("20230525") == (2023, 2)
    assert fsds.quarter_of("2025-12-31") == (2025, 4)


def test_read_submissions_filters_cik_and_annual_forms():
    subs = fsds.read_submissions(SUBS, ["0000000042"])
    assert set(subs) == {"A1", "A0"}          # 10-Q와 다른 CIK는 제외


def test_read_num_drops_coreg_and_bad_values():
    subs, _ = _load([])
    text = _num([("A1", "NetIncomeLoss", "20251231", 4, "", 1.0, ""),
                 ("A1", "NetIncomeLoss", "20241231", 4, "", 2.0, "SubsidiaryCo"),
                 ("A1", "NetIncomeLoss", "20231231", 4, "", "", "")])
    rows = fsds.read_num(_dr(text), set(subs), ["NetIncomeLoss"])
    assert [r["value"] for r in rows] == [1.0]


def test_read_quarter_zip_roundtrip(tmp_path):
    p = tmp_path / "2026q1.zip"
    with zipfile.ZipFile(p, "w") as z:
        z.writestr("sub.txt", SUB_HDR + "A1\t42\tX\t10-K\t20251231\t2025\tFY\t20260220\n")
        z.writestr("num.txt", _num([("A1", "NetIncomeLoss", "20251231", 4, "", 5.0, "")]))
    subs, rows = fsds.read_quarter_zip(str(p), ["42"], ["NetIncomeLoss"])
    assert list(subs) == ["A1"] and rows[0]["value"] == 5.0


def test_as_converted_picks_class_whose_eps_reproduces_net_income():
    subs, rows = _load(_erie_like(NI, SH, EPS))
    r = fsds.as_converted_share_series(subs, rows, "42")
    assert r["status"] == "OK" and r["class"] == "CommonClassA"
    assert r["series"] == SH
    assert all(c["rel_err"] <= fsds.EPS_RECONCILE_TOL for c in r["checks"])


def test_as_converted_refuses_when_nci_present():
    """Up-C: 상장 클래스 증가가 유닛 교환인지 희석인지 구분 불가 -> 거부."""
    subs, rows = _load(_erie_like(NI, SH, EPS, nci={y: 0.3 * NI[y] for y in YEARS}))
    r = fsds.as_converted_share_series(subs, rows, "42")
    assert r["status"] == "NCI_PRESENT" and r["series"] == {}


def test_as_converted_refuses_when_one_year_fails_reconciliation():
    eps = dict(EPS)
    eps[2022] = EPS[2022] * 1.10           # 한 해라도 재현 실패면 그 클래스 탈락
    subs, rows = _load(_erie_like(NI, SH, eps))
    r = fsds.as_converted_share_series(subs, rows, "42")
    assert r["status"] == "CLASS_UNRESOLVED"


def test_as_converted_no_class_rows():
    subs, rows = _load([("A1", "NetIncomeLoss", "20251231", 4, "", 1.0, "")])
    assert fsds.as_converted_share_series(subs, rows, "42")["status"] == "NO_CLASS_SHARES"


def test_latest_filing_wins_for_restated_period():
    subs, rows = _load([("A0", "NetIncomeLoss", "20221231", 4, "", 1.0, ""),
                        ("A1", "NetIncomeLoss", "20221231", 4, "", 2.0, "")])
    got = fsds.latest_by_period(subs, rows, "42", "NetIncomeLoss", 4, lambda s: not s)
    assert got["20221231"][1] == 2.0


def test_segment_revenue_single_axis_only():
    rows = [
        ("A1", "Revenues", "20251231", 4, "BusinessSegments=Alpha;", 60.0, ""),
        ("A1", "Revenues", "20251231", 4, "BusinessSegments=Beta;", 40.0, ""),
        ("A1", "Revenues", "20251231", 4, "BusinessSegments=Alpha;Geographical=US;", 30.0, ""),
        ("A1", "Revenues", "20251231", 4, "", 100.0, ""),
    ]
    subs, num = _load(rows)
    seg = fsds.segment_revenue(subs, num, "42")
    assert seg["BusinessSegments"]["members"] == {"Alpha": {2025: 60.0}, "Beta": {2025: 40.0}}
    assert fsds.consolidated_revenue(subs, num, "42")["by_year"] == {2025: 100.0}


def _ledger(fcf, rev):
    return {"derived": {"fcf_by_year": {str(k): v for k, v in fcf.items()},
                        "cagr_5y_base_year": 2020, "cagr_5y_span": 5},
            "inputs": {"revenue_by_year": {str(k): v for k, v in rev.items()}}}


FCF = {y: 100.0 * 1.1 ** (y - 2020) for y in YEARS}
REV = {y: 1000.0 * 1.08 ** (y - 2020) for y in YEARS}


def test_dilution_from_fsds_ok_matches_hand_calculation():
    shares = {y: 50e6 * 1.02 ** (y - 2020) for y in YEARS}
    ac = {"status": "OK", "class": "CommonClassA", "series": shares, "checks": []}
    r = dilution_drag_from_fsds("X", _ledger(FCF, REV), ac, REV, "fsds:test")
    assert r["status"] == STATUS_OK
    total = (FCF[2025] / FCF[2020]) ** 0.2 - 1
    per = ((FCF[2025] / shares[2025]) / (FCF[2020] / shares[2020])) ** 0.2 - 1
    assert r["dilution_drag"] == pytest.approx(per - total, abs=1e-12)
    assert r["normalization"]["basis"] == "fsds_as_converted_class"


def test_dilution_from_fsds_rejects_shifted_year_labels():
    """FSDS 연도가 ledger를 재현하지 못하면(한 해 밀림) 계산하지 않는다."""
    shifted = {y + 1: v for y, v in REV.items()}
    ac = {"status": "OK", "class": "A", "series": {y: 1e6 for y in YEARS}, "checks": []}
    r = dilution_drag_from_fsds("X", _ledger(FCF, REV), ac, shifted, "fsds:test")
    assert r["status"] == STATUS_FY_COLLISION


def test_dilution_from_fsds_propagates_refusal():
    r = dilution_drag_from_fsds("X", _ledger(FCF, REV),
                                {"status": "NCI_PRESENT", "detail": "Up-C"}, REV, "fsds:test")
    assert r["status"] == STATUS_NO_SHARES and "Up-C" in r["detail"]


def test_real_erie_extract_reconciles_and_shows_no_dilution():
    """2026-10-10 실측: ERIE Class A 희석주식수 x 희석EPS가 6년 모두 순이익을 재현."""
    path = os.path.join(ROOT, "data", "fsds", "ERIE.json")
    if not os.path.exists(path):
        pytest.skip("추출본 없음")
    x = json.load(open(path, encoding="utf-8"))
    r = fsds.as_converted_share_series(x["submissions"], x["rows"], x["cik"])
    assert r["status"] == "OK" and r["class"] == "CommonClassA"
    assert set(r["series"]) >= set(range(2020, 2026))
    assert abs(r["series"][2025] / r["series"][2020] - 1) < 0.01


def test_module_has_no_judgment_or_score_function():
    tree = ast.parse(open(os.path.join(ROOT, "engine", "fsds.py"), encoding="utf-8").read())
    names = [n.name for n in tree.body if isinstance(n, ast.FunctionDef)]
    banned = ("score", "verdict", "judge", "decide", "grade", "recommend")
    assert not [n for n in names if any(b in n.lower() for b in banned)]


def test_not_wired_into_valuation_or_portfolio():
    for f in ("engine/pipeline.py", "engine/expectation_gap_engine.py",
              "engine/portfolio_pipeline.py"):
        assert "fsds" not in open(os.path.join(ROOT, f), encoding="utf-8").read()
