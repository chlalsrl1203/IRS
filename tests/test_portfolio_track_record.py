"""
engine/portfolio_track_record.py 고정 테스트 (2026-09-19).

고정하는 것 넷:
  ① 가격조회/파싱을 재구현하지 않는다 - engine.track_record를 그대로 쓴다
     (Simplicity First - 중복 구현이 두 계산을 미묘하게 어긋나게 만든다)
  ② 공통 진입일(매수리스트 발행일) 기준 비중가중 수익률이 올바르게 계산된다
  ③ 가격 미확보 종목은 0%로 취급되지 않고 커버리지에서 정직하게 빠진다
  ④ 판정/사이징에 되먹임하는 함수가 없고, 어떤 파일에도 쓰지 않는다
     (병기, 자동판정 안 함 - v3.42)
"""
import ast
import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.portfolio_track_record import (  # noqa: E402
    MEASUREMENT_STATUS,
    _is_dated_buylist,
    fetch_inception_prices,
    format_snapshot,
    load_history,
    load_latest_buylist,
    snapshot,
)


def _series_response(rows):
    payload = json.dumps({"data": rows}).encode()

    class _Resp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return payload

    return lambda req, timeout=None: _Resp()


def _row(date, close):
    return {"t": date, "c": close, "a": close}


# ── ① 재구현 금지 - engine.track_record 함수를 재사용한다 ─────────────
def test_does_not_redefine_price_fetching_or_parsing():
    src = (ROOT / "engine" / "portfolio_track_record.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    names = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    banned = {"fetch_daily_series", "parse_series", "price_on_or_before",
              "entry_bar_as_known_at", "measure"}
    assert not (names & banned), (
        f"engine.track_record 함수를 재구현했다: {names & banned}")
    assert "from engine.track_record import" in src


def test_module_defines_no_action_or_write_function():
    """
    Gap을 액션으로 매핑하거나(engine/thesis.py 원칙) 리밸런싱을 실행하는
    함수가 생기면 이 모듈은 관측 도구에서 자본배분 도구로 넘어간다.
    """
    src = (ROOT / "engine" / "portfolio_track_record.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    names = [n.name.lower() for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
    banned_substrings = ("decide", "judge", "rebalance", "verdict", "recommend",
                          "should_buy", "should_sell", "trade", "execute_order")
    for n in names:
        for b in banned_substrings:
            assert b not in n, f"자동판정/거래 함수가 생겼다: {n}"


def test_module_only_ever_opens_files_for_reading():
    """
    engine/portfolio_track_record.py는 순수 계산+읽기 전용이다(파일 쓰기는
    CLI 스크립트의 몫). `load_latest_buylist`가 `open(path, ...)`으로 매수
    리스트를 읽는 건 정상이다 - 단, 그 호출에 쓰기/추가 모드('w'/'a')가
    지정돼 있으면 안 된다(기본 모드가 없으면 읽기 전용 'r'이다).
    """
    src = (ROOT / "engine" / "portfolio_track_record.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    open_calls = [n for n in ast.walk(tree)
                  if isinstance(n, ast.Call) and getattr(n.func, "id", None) == "open"]
    assert open_calls, "load_latest_buylist가 open()으로 읽어야 한다(회귀 시 이 가정 확인)"
    for node in open_calls:
        mode_args = list(node.args[1:2])
        mode_args += [kw.value for kw in node.keywords if kw.arg == "mode"]
        for m in mode_args:
            if isinstance(m, ast.Constant):
                assert "w" not in m.value and "a" not in m.value, (
                    "engine 모듈에 쓰기/추가 모드 open()이 있으면 안 된다")


# ── load_latest_buylist: 스키마 함정(2026-08-28) 회귀 ─────────────────
def test_is_dated_buylist_rejects_non_dated_schema_files():
    assert _is_dated_buylist("reports/buylist_2026-09-06.json")
    assert not _is_dated_buylist("reports/buylist_boundary_review_2026-08-16.json")
    assert not _is_dated_buylist("reports/portfolio_screen_2026-09-05.json")


def test_load_latest_buylist_picks_newest_dated_file_and_ignores_decoys(tmp_path, monkeypatch):
    reports = tmp_path / "reports"
    reports.mkdir()
    decoy = {"generated_at": "2026-08-16", "positions": []}
    (reports / "buylist_boundary_review_2026-08-16.json").write_text(
        json.dumps(decoy), encoding="utf-8")
    old = {"generated_at": "2026-08-03", "positions": [{"ticker": "A", "weight_final": 1.0}]}
    (reports / "buylist_2026-08-03.json").write_text(json.dumps(old), encoding="utf-8")
    new = {"generated_at": "2026-09-06", "positions": [{"ticker": "B", "weight_final": 1.0}]}
    (reports / "buylist_2026-09-06.json").write_text(json.dumps(new), encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    loaded = load_latest_buylist()
    assert loaded["generated_at"] == "2026-09-06"
    assert loaded["positions"][0]["ticker"] == "B"
    assert loaded["_source_path"].endswith("buylist_2026-09-06.json")


def test_load_latest_buylist_returns_none_when_absent(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert load_latest_buylist() is None


# ── fetch_inception_prices: 실패를 사유와 함께 돌려준다 ────────────────
def test_fetch_inception_prices_records_failure_reason():
    def boom(req, timeout=None):
        raise OSError("network down")
    prices, errors, cache = fetch_inception_prices(["AAA"], "2026-09-06", opener=boom)
    assert prices == {} and "network down" in errors["AAA"]


def test_fetch_inception_prices_uses_price_on_or_before_for_weekend_gap():
    opener = _series_response([_row("2026-09-04", 100.0), _row("2026-09-08", 110.0)])
    # 2026-09-06 = 일요일, 시계열에 없다 -> 직전 거래일(09-04) 종가를 진입가로.
    prices, errors, cache = fetch_inception_prices(["AAA"], "2026-09-06", opener=opener)
    assert errors == {}
    assert prices["AAA"]["entry_date"] == "2026-09-04"
    assert prices["AAA"]["entry_adj"] == 100.0


# ── ② 비중가중 수익률 계산 ─────────────────────────────────────────────
def _buylist(positions, generated_at="2026-09-06"):
    return {"generated_at": generated_at, "positions": positions,
            "_source_path": "reports/buylist_2026-09-06.json"}


def test_snapshot_computes_weight_averaged_return_correctly():
    """
    A: 진입 100 -> 최신 110 (+10%), 비중 0.6
    B: 진입 50  -> 최신 55  (+10%), 비중 0.4
    둘 다 +10%면 포트폴리오도 +10%여야 한다(가중평균의 자명한 검산).
    """
    positions = [{"ticker": "A", "weight_final": 0.6, "grade": "S"},
                 {"ticker": "B", "weight_final": 0.4, "grade": "A"}]

    def opener(req, timeout=None):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        if "/a/" in url:
            rows = [_row("2026-09-06", 100.0), _row("2026-09-19", 110.0)]
        else:
            rows = [_row("2026-09-06", 50.0), _row("2026-09-19", 55.0)]
        payload = json.dumps({"data": rows}).encode()

        class _Resp:
            def __enter__(self_):
                return self_

            def __exit__(self_, *a):
                return False

            def read(self_):
                return payload

        return _Resp()

    snap = snapshot(_buylist(positions), as_of="2026-09-19", opener=opener,
                     benchmark_ticker=None)
    assert snap["covered_weight"] == pytest.approx(1.0)
    assert snap["uncovered_weight"] == pytest.approx(0.0)
    assert snap["portfolio_return_pct"] == pytest.approx(10.0, abs=1e-9)
    assert snap["n_covered"] == 2


def test_trajectory_reuses_fetched_series_no_extra_network_calls():
    """
    trajectory는 snapshot()이 이미 받아온 series_cache/bseries만 쓴다 -
    opener 호출횟수가 종목수+벤치마크(여기선 2종목+SPY=3회)를 넘으면
    안 된다(추가 fetch가 생기면 이 테스트가 잡는다).
    """
    calls = {"n": 0}
    positions = [{"ticker": "A", "weight_final": 0.5},
                 {"ticker": "B", "weight_final": 0.5}]

    def opener(req, timeout=None):
        calls["n"] += 1
        url = req.full_url if hasattr(req, "full_url") else str(req)
        if "/spy/" in url:
            rows = [_row("2026-09-04", 500.0), _row("2026-09-11", 505.0),
                    _row("2026-09-18", 510.0)]
        elif "/a/" in url:
            rows = [_row("2026-09-04", 100.0), _row("2026-09-11", 110.0),
                    _row("2026-09-18", 120.0)]
        else:
            rows = [_row("2026-09-04", 100.0), _row("2026-09-11", 95.0),
                    _row("2026-09-18", 90.0)]
        payload = json.dumps({"data": rows}).encode()

        class _Resp:
            def __enter__(self_):
                return self_

            def __exit__(self_, *a):
                return False

            def read(self_):
                return payload

        return _Resp()

    snap = snapshot(_buylist(positions, generated_at="2026-09-04"), as_of="2026-09-19",
                     opener=opener, benchmark_ticker="SPY")
    assert calls["n"] == 3, "종목 2개 + 벤치마크 1개 = 정확히 3회여야 한다"

    traj = snap["trajectory"]
    assert [p["date"] for p in traj] == ["2026-09-04", "2026-09-11", "2026-09-18"]
    # 진입일 첫 점 = 지수 100(A/B 둘 다 자기 진입가 대비 1.0)
    assert traj[0]["portfolio_index"] == pytest.approx(100.0, abs=1e-9)
    assert traj[0]["benchmark_index"] == pytest.approx(100.0, abs=1e-9)
    # 마지막 점의 (지수-100)은 snapshot()의 portfolio_return_pct와 정확히 일치해야 한다
    assert traj[-1]["portfolio_index"] - 100.0 == pytest.approx(
        snap["portfolio_return_pct"], abs=1e-9)
    assert traj[-1]["benchmark_index"] - 100.0 == pytest.approx(
        snap["benchmark"]["return_pct"], abs=1e-9)
    # 중간점도 같은 규칙으로 계산돼야 한다: A +10%(0.5) / B -5%(0.5) -> +2.5%
    assert traj[1]["portfolio_index"] == pytest.approx(102.5, abs=1e-9)


def test_trajectory_is_empty_when_nothing_covered():
    positions = [{"ticker": "A", "weight_final": 1.0}]

    def boom(req, timeout=None):
        raise OSError("down")

    snap = snapshot(_buylist(positions), opener=boom, benchmark_ticker=None)
    assert snap["trajectory"] == []


def test_snapshot_gives_unequal_returns_a_correctly_weighted_average():
    """A +20%(비중0.75) / B -10%(비중0.25) -> 0.75*20 + 0.25*(-10) = 12.5%"""
    positions = [{"ticker": "A", "weight_final": 0.75},
                 {"ticker": "B", "weight_final": 0.25}]

    def opener(req, timeout=None):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        if "/a/" in url:
            rows = [_row("2026-09-06", 100.0), _row("2026-09-19", 120.0)]
        else:
            rows = [_row("2026-09-06", 100.0), _row("2026-09-19", 90.0)]
        payload = json.dumps({"data": rows}).encode()

        class _Resp:
            def __enter__(self_):
                return self_

            def __exit__(self_, *a):
                return False

            def read(self_):
                return payload

        return _Resp()

    snap = snapshot(_buylist(positions), as_of="2026-09-19", opener=opener,
                     benchmark_ticker=None)
    assert snap["portfolio_return_pct"] == pytest.approx(12.5, abs=1e-9)
    rows_by_ticker = {r["ticker"]: r for r in snap["rows"]}
    assert rows_by_ticker["A"]["contribution_pct"] == pytest.approx(15.0, abs=1e-9)
    assert rows_by_ticker["B"]["contribution_pct"] == pytest.approx(-2.5, abs=1e-9)


# ── ③ 미확보 종목은 0%가 아니라 커버리지에서 빠진다 ────────────────────
def test_snapshot_excludes_uncoverable_ticker_instead_of_treating_as_zero():
    """
    A(비중0.5, +100%) / B(비중0.5, 가격조회 실패) - 만약 B를 0%로 취급하면
    포트폴리오 수익률이 +50%가 된다(틀렸다). 커버리지 안에서만 정규화하면
    A 혼자 +100%가 되어야 한다 - 손실/실패 종목이 빠졌을 때 포트폴리오가
    실제보다 좋아 보이는 함정을 피한다.
    """
    positions = [{"ticker": "A", "weight_final": 0.5},
                 {"ticker": "B", "weight_final": 0.5}]

    def opener(req, timeout=None):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        if "/a/" in url:
            rows = [_row("2026-09-06", 100.0), _row("2026-09-19", 200.0)]
            payload = json.dumps({"data": rows}).encode()

            class _Resp:
                def __enter__(self_):
                    return self_

                def __exit__(self_, *a):
                    return False

                def read(self_):
                    return payload

            return _Resp()
        raise OSError("symbol delisted")

    snap = snapshot(_buylist(positions), as_of="2026-09-19", opener=opener,
                     benchmark_ticker=None)
    assert snap["covered_weight"] == pytest.approx(0.5)
    assert snap["uncovered_weight"] == pytest.approx(0.5)
    assert snap["portfolio_return_pct"] == pytest.approx(100.0, abs=1e-9)
    assert "B" in snap["errors"]
    errored_rows = [r for r in snap["rows"] if "error" in r]
    assert errored_rows and errored_rows[0]["ticker"] == "B"


def test_snapshot_returns_none_when_nothing_covered():
    positions = [{"ticker": "A", "weight_final": 1.0}]

    def boom(req, timeout=None):
        raise OSError("down")

    snap = snapshot(_buylist(positions), opener=boom, benchmark_ticker=None)
    assert snap["portfolio_return_pct"] is None
    assert snap["covered_weight"] == 0.0
    assert "가중수익률 계산 불가" in format_snapshot(snap)


# ── 벤치마크 비교 ──────────────────────────────────────────────────────
def test_snapshot_computes_alpha_vs_benchmark():
    positions = [{"ticker": "A", "weight_final": 1.0}]

    def opener(req, timeout=None):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        if "/spy/" in url:
            rows = [_row("2026-09-06", 500.0), _row("2026-09-19", 520.0)]  # +4%
        else:
            rows = [_row("2026-09-06", 100.0), _row("2026-09-19", 115.0)]  # +15%
        payload = json.dumps({"data": rows}).encode()

        class _Resp:
            def __enter__(self_):
                return self_

            def __exit__(self_, *a):
                return False

            def read(self_):
                return payload

        return _Resp()

    snap = snapshot(_buylist(positions), as_of="2026-09-19", opener=opener,
                     benchmark_ticker="SPY")
    assert snap["portfolio_return_pct"] == pytest.approx(15.0, abs=1e-9)
    assert snap["benchmark"]["return_pct"] == pytest.approx(4.0, abs=1e-9)
    assert snap["alpha_vs_benchmark_pct"] == pytest.approx(11.0, abs=1e-9)


def test_snapshot_handles_missing_benchmark_gracefully():
    positions = [{"ticker": "A", "weight_final": 1.0}]

    def opener(req, timeout=None):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        if "/spy/" in url:
            raise OSError("benchmark fetch failed")
        rows = [_row("2026-09-06", 100.0), _row("2026-09-19", 115.0)]
        payload = json.dumps({"data": rows}).encode()

        class _Resp:
            def __enter__(self_):
                return self_

            def __exit__(self_, *a):
                return False

            def read(self_):
                return payload

        return _Resp()

    snap = snapshot(_buylist(positions), as_of="2026-09-19", opener=opener,
                     benchmark_ticker="SPY")
    assert snap["portfolio_return_pct"] == pytest.approx(15.0, abs=1e-9)
    assert snap["benchmark"] is None
    assert snap["alpha_vs_benchmark_pct"] is None
    assert "SPY" in snap["errors"]


# ── ④ 입력 불변성 + 상태 라벨 ───────────────────────────────────────────
def test_snapshot_does_not_mutate_input_buylist():
    positions = [{"ticker": "A", "weight_final": 1.0}]
    buylist = _buylist(positions)
    before = json.dumps(buylist, sort_keys=True)
    opener = _series_response([_row("2026-09-06", 100.0), _row("2026-09-19", 110.0)])
    snapshot(buylist, as_of="2026-09-19", opener=opener, benchmark_ticker=None)
    assert json.dumps(buylist, sort_keys=True) == before


def test_snapshot_carries_measurement_status_label():
    positions = [{"ticker": "A", "weight_final": 1.0}]
    opener = _series_response([_row("2026-09-06", 100.0), _row("2026-09-19", 110.0)])
    snap = snapshot(_buylist(positions), opener=opener, benchmark_ticker=None)
    assert snap["measurement_status"] == MEASUREMENT_STATUS
    assert "OBSERVATIONAL_NOT_INFERENTIAL" in MEASUREMENT_STATUS


def test_load_history_returns_empty_list_when_no_snapshots_yet(tmp_path):
    assert load_history(str(tmp_path / "does_not_exist")) == []


def test_load_history_reads_snapshots_in_date_order(tmp_path):
    d = tmp_path / "ptr"
    d.mkdir()
    (d / "portfolio_track_record_2026-09-19.json").write_text(
        json.dumps({"as_of": "2026-09-19"}), encoding="utf-8")
    (d / "portfolio_track_record_2026-09-06.json").write_text(
        json.dumps({"as_of": "2026-09-06"}), encoding="utf-8")
    hist = load_history(str(d))
    assert [h["as_of"] for h in hist] == ["2026-09-06", "2026-09-19"]


# ── CLI 스크립트: 산출물 경로 격리 ──────────────────────────────────────
def test_ci_script_writes_only_into_its_own_out_dir():
    """
    이 스크립트가 쓰기 모드로 여는 곳은 **전부** 자신의 `--out-dir`
    (기본값 `reports/portfolio_track_record/`) 아래여야 한다 -
    `ledger/`·`portfolio/holdings.json`·`watchlist.json`·공식 매수리스트
    (`reports/buylist_*.json`)에 쓰는 코드가 섞여 들어오면 이 테스트가
    잡는다.

    ⚠️ 원래 이 테스트는 "쓰기 호출이 정확히 1곳"임을 단언했는데, 그건
    지켜야 할 성질이 아니라 그 시점의 상태였다 - 2026-09-19에 대시보드용
    고정 경로(`latest.json`)를 추가하자 정당한 두 번째 쓰기가 생기면서
    실패했다. 개수가 아니라 **모든 쓰기 경로가 out_dir에서 조립됐는가**를
    확인하도록 고쳤다(BRO model_choice_reason·test_every_prediction_
    starts_open과 같은 처리 - 상태를 단언하던 테스트를 진짜 불변조건으로
    다시 쓴다). 개수를 세지 않으므로 전보다 약해진 게 아니라, 새로 생기는
    쓰기 하나하나를 전부 검사하므로 오히려 강해졌다.
    """
    src = (ROOT / "scripts" / "portfolio_track_record_ci.py").read_text(encoding="utf-8")
    tree = ast.parse(src)

    def _open_path_source(node):
        """open()의 첫 인자(경로)를 소스코드 조각으로 되돌린다."""
        return ast.get_source_segment(src, node.args[0]) if node.args else ""

    forbidden_writes = ("ledger/", "portfolio/holdings.json", "watchlist.json",
                        "buylist_")
    write_calls = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "open":
            mode_args = list(node.args[1:2])
            mode_args += [kw.value for kw in node.keywords if kw.arg == "mode"]
            path_src = _open_path_source(node)
            for forbidden in forbidden_writes:
                assert forbidden not in path_src, (
                    f"open() 경로에 금지된 대상이 있다: {path_src!r}")
            if any(isinstance(m, ast.Constant) and "w" in m.value for m in mode_args):
                write_calls.append(node)
    assert write_calls, "쓰기 호출이 하나도 없다 - 스냅샷을 저장하지 않는다"

    # 쓰기 호출은 지역변수(예: path)를 받는다 - 그 변수가 실제로 out_dir로
    # 조립됐는지 대입식까지 따라가서 확인한다(변수명만 보면 우회 가능).
    for call in write_calls:
        path_arg_name = _open_path_source(call)
        assignments_to_path_var = [
            ast.get_source_segment(src, n.value)
            for n in ast.walk(tree)
            if isinstance(n, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == path_arg_name for t in n.targets)
        ]
        assert assignments_to_path_var and any(
            "out_dir" in seg for seg in assignments_to_path_var
        ), (f"쓰기 경로 {path_arg_name!r}가 --out-dir에서 조립되지 않았다: "
            f"{assignments_to_path_var}")
