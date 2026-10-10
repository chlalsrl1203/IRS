"""engine/bad_news.py — 비정기 가이던스 하향 규칙 (v4.01). 네트워크 없음."""

import ast
import os
import re

from engine import bad_news as BN

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_scheduled_release_is_latest_202_within_45_days_of_periodic():
    rel = ["2026-01-10", "2026-02-05", "2026-04-28", "2026-06-15"]
    per = ["2026-02-20", "2026-05-02"]
    s = BN.scheduled_releases(rel, per)
    assert s == {"2026-02-05", "2026-04-28"}       # 01-10 사전경고·06-15 중간발표는 비정기


def _g(fy, low, high):
    return {"fy": fy, "low": low, "high": high, "kind": "range", "excerpt": f"revenue {low}-{high}"}


def _rel(filed, sched, *gs, acc=None, items="2.02,9.01"):
    return {"filed": filed, "accession": acc or filed, "items": items, "scheduled": sched,
            "guidance": list(gs)}


def test_cut_detected_only_beyond_threshold_and_same_fy():
    rels = [_rel("2026-02-05", True, _g(2026, 100e6, 110e6)),
            _rel("2026-03-01", False, _g(2026, 99.5e6, 109.5e6)),   # -0.5% → 하향 아님
            _rel("2026-04-10", False, _g(2026, 90e6, 100e6)),        # 하향
            _rel("2026-05-01", True, _g(2027, 80e6, 90e6))]          # 다른 FY
    cuts = BN.guidance_cuts(rels)
    assert [c["filed"] for c in cuts] == ["2026-04-10"]
    assert cuts[0]["change_pct"] < -0.01 and cuts[0]["scheduled"] is False


def test_unscheduled_cut_answers_true():
    cuts = BN.guidance_cuts([_rel("2026-02-05", True, _g(2026, 100e6, 110e6)),
                             _rel("2026-04-10", False, _g(2026, 90e6, 100e6), items="7.01,9.01")])
    r = BN.voluntary_bad_news(cuts, 2, 2)
    assert r["status"] == "answered" and r["answer"] is True


def test_scheduled_only_cut_stays_unknown():
    cuts = BN.guidance_cuts([_rel("2026-02-05", True, _g(2026, 100e6, 110e6)),
                             _rel("2026-05-05", True, _g(2026, 90e6, 100e6))])
    r = BN.voluntary_bad_news(cuts, 2, 2)
    assert r["status"] == "unknown" and "정기" in r["reason"]


def test_no_cut_never_answers_false():
    """하향이 없었다는 것은 '선제 공시 이력 없음'이 아니다 — 나쁜 소식이 없었을 수 있다."""
    r = BN.voluntary_bad_news([], 5, 3)
    assert r["status"] == "unknown" and r.get("answer") is None
    assert BN.voluntary_bad_news([], 5, 0)["status"] == "unknown"


def test_same_day_duplicate_guidance_is_one_observation():
    cuts = BN.guidance_cuts([_rel("2026-02-05", True, _g(2026, 100e6, 110e6), acc="a"),
                             _rel("2026-02-05", False, _g(2026, 50e6, 60e6), acc="b")])
    assert cuts == []


def test_module_has_no_score_or_verdict_function_and_is_not_wired():
    tree = ast.parse(open(os.path.join(ROOT, "engine", "bad_news.py"), encoding="utf-8").read())
    names = [n.name for n in tree.body if isinstance(n, ast.FunctionDef)]
    assert not [n for n in names if re.search(r"score|verdict|judge|grade|recommend", n)]
    for f in ("engine/pipeline.py", "engine/expectation_gap_engine.py", "engine/portfolio_pipeline.py"):
        assert "bad_news" not in open(os.path.join(ROOT, f), encoding="utf-8").read()
