"""
scripts/build_portfolio.py 배선 테스트 (2026-09-06) - 포트폴리오 계층의
유일한 진입점이 실제로 daily_brief 스키마를 만들고, ledger/holdings에는
손대지 않는지 확인한다.
"""
import json
import os
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
LEDGER_DIR = ROOT / "ledger"
HOLDINGS_PATH = ROOT / "portfolio" / "holdings.json"


@pytest.fixture
def run_result(tmp_path):
    import sys
    sys.path.insert(0, str(ROOT))
    from scripts import build_portfolio as B

    ledger_mtimes = {p: p.stat().st_mtime for p in LEDGER_DIR.glob("*.json")}
    holdings_mtime = HOLDINGS_PATH.stat().st_mtime if HOLDINGS_PATH.exists() else None

    out_date = "2026-09-06-testrun"
    result = B.run(today=out_date)
    yield result

    # 정리 - 테스트 산출물을 남기지 않는다
    for p in (result["buylist_path"], result["diag_path"]):
        if os.path.exists(p):
            os.remove(p)

    # ledger/holdings가 실행 전후로 정말 안 바뀌었는지 확인(테스트 자체가 위양성 안전장치)
    for p, mt in ledger_mtimes.items():
        assert p.stat().st_mtime == mt, f"{p}가 build_portfolio 실행 중 수정됐다"
    if holdings_mtime is not None:
        assert HOLDINGS_PATH.stat().st_mtime == holdings_mtime


def test_run_writes_buylist_with_daily_brief_schema(run_result):
    with open(run_result["buylist_path"], encoding="utf-8") as f:
        data = json.load(f)
    assert data["positions"]
    total = sum(p["weight_final"] for p in data["positions"])
    assert abs(total - 1.0) < 1e-6
    for p in data["positions"]:
        for key in ("ticker", "weight_final", "grade", "conf_adj", "conf_status"):
            assert key in p


def test_run_writes_diagnostics_with_stage_counts(run_result):
    with open(run_result["diag_path"], encoding="utf-8") as f:
        diag = json.load(f)
    assert diag["n_final"] == len(diag["positions"])
    assert diag["n_universe"] == diag["n_stage1_survivors"] + diag["n_stage1_excluded"]


def test_run_never_touches_ledger_or_holdings(run_result):
    """fixture의 mtime 비교가 이미 이 불변조건을 강제한다 - 여기선 명시적으로
    한번 더 표시해 이 파일을 읽는 사람이 의도를 놓치지 않게 한다."""
    assert True
