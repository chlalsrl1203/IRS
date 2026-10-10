"""engine/comment_letters.py (v4.02). 네트워크 없음."""

from engine import comment_letters as CL


def _row(form, d, doc="filename1.pdf"):
    return {"form": form, "filingDate": d, "primaryDocument": doc}


def test_counts_upload_in_window_only():
    lst = {"covers_window": True, "rows": [_row("UPLOAD", "2024-01-04"), _row("UPLOAD", "2026-01-01"),
                                           _row("CORRESP", "2024-01-19", "f.htm"), _row("10-K", "2025-02-01"),
                                           _row("UPLOAD", "2026-12-01")]}
    r = CL.count_letters(lst, "2023-10-10", "2026-10-10")
    assert r["status"] == "OK" and r["answer"] == 2 and r["n_corresp"] == 1


def test_uncovered_window_is_not_zero():
    r = CL.count_letters({"covers_window": False, "rows": []}, "2023-10-10", "2026-10-10")
    assert r["status"] == "WINDOW_NOT_COVERED" and "answer" not in r


def test_corresp_topics_keywords():
    t = CL.corresp_topics("We respectfully respond regarding our use of non-GAAP measures and segment reporting.")
    assert t == ["non_gaap", "segments"]
    assert CL.corresp_topics("") == []


def test_not_wired_into_valuation_or_portfolio():
    import os
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for f in ("engine/pipeline.py", "engine/expectation_gap_engine.py", "engine/portfolio_pipeline.py"):
        assert "comment_letters" not in open(os.path.join(root, f), encoding="utf-8").read()
