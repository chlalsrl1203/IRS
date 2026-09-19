"""
dashboard/portfolio_track_record.html 고정 테스트 (2026-09-19).

이 대시보드는 **스스로 원자료를 가져온다** - GitHub Actions가 매일 새로 쓴
`reports/portfolio_track_record/latest.json`을 브라우저에서 직접 읽으므로
페이지를 다시 발행하지 않아도 갱신된다. 그래서 이 구조가 조용히 깨지는
경로가 둘 있고, 둘 다 여기서 고정한다:

  ① **스키마 드리프트** - 파이썬 스냅샷의 키 이름이 바뀌어도 자바스크립트는
     `undefined`를 읽고 예외 없이 빈칸을 그린다. 테스트가 없으면 아무도
     모른다. 이 프로젝트가 반복 겪은 "조용한 실패"(R-001 fcf0 키 오타로
     사전등록 6축 중 1축이 죽어 있던 사고)의 웹 버전이다.
  ② **고정 경로 드리프트** - `latest.json`이라는 이름이 CI 스크립트·엔진
     상수·HTML 세 곳에 각자 박히면 한쪽만 바뀌었을 때 404가 난다(v3.35가
     판정 경계값에서 실제로 겪은 형태).

추가로 "실패 시 낡은 값을 보여주지 않는다"는 설계 결정도 고정한다 -
빌드 시점 스냅샷을 내장하면 네트워크가 죽었을 때 낡은 값이 최신인 척
표시된다("데이터 없음을 안전으로 오독").
"""
import glob
import json
import os
import pathlib
import re
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.portfolio_track_record import LATEST_NAME, OUT_DIR  # noqa: E402

DASHBOARD = ROOT / "dashboard" / "portfolio_track_record.html"
SNAP_DIR = ROOT / OUT_DIR


def _html():
    return DASHBOARD.read_text(encoding="utf-8")


def _newest_dated_snapshot():
    paths = sorted(glob.glob(os.path.join(
        str(SNAP_DIR), "portfolio_track_record_*.json")))
    if not paths:
        pytest.skip("스냅샷이 아직 없다")
    return json.loads(pathlib.Path(paths[-1]).read_text(encoding="utf-8")), paths[-1]


# ── 존재와 자족성 ─────────────────────────────────────────────────
def test_dashboard_exists_and_needs_no_build_step():
    """
    HTML은 빌드 산출물이 아니라 그대로 발행하는 소스다. 템플릿 치환자가
    남아 있으면(예: __PF_RETURN__) 파이썬 생성기가 다시 끼어든 것이고,
    그러면 "매일 자동 갱신"이 성립하지 않는다(재발행해야 숫자가 바뀐다).
    """
    assert DASHBOARD.exists(), "대시보드 HTML이 없다"
    src = _html()
    leftovers = re.findall(r"__[A-Z_]{3,}__", src)
    assert not leftovers, f"빌드 치환자가 남아 있다(빌드 의존): {sorted(set(leftovers))}"


def test_dashboard_reads_the_stable_latest_path():
    """고정 경로가 엔진 상수와 일치해야 한다(세 곳 드리프트 방지)."""
    src = _html()
    expected = f"reports/portfolio_track_record/{LATEST_NAME}"
    assert expected in src, f"대시보드가 고정 경로({expected})를 읽지 않는다"
    assert "raw.githubusercontent.com" in src


# ── ⭐ 스키마 드리프트: JS가 읽는 키가 실제 스냅샷에 존재하는가 ──────
def _js_snapshot_keys(src):
    """`snap.<key>` 형태로 참조되는 최상위 키를 추출한다."""
    return set(re.findall(r"\bsnap\.([a-z_][a-z0-9_]*)", src))


def _js_row_keys(src):
    """`r.<key>` 형태로 참조되는 종목 행 키를 추출한다."""
    return set(re.findall(r"\br\.([a-z_][a-z0-9_]*)", src))


def test_every_top_level_key_the_dashboard_reads_exists_in_a_real_snapshot():
    snap, path = _newest_dated_snapshot()
    referenced = _js_snapshot_keys(_html())
    assert referenced, "키 추출에 실패했다(정규식이 코드와 어긋났을 수 있다)"
    missing = sorted(k for k in referenced if k not in snap)
    assert not missing, (
        f"대시보드가 읽는 키가 스냅샷({path})에 없다: {missing} — "
        "화면에는 예외 없이 빈칸으로 나온다")


def test_every_row_key_the_dashboard_reads_exists_in_a_real_snapshot():
    snap, path = _newest_dated_snapshot()
    rows = [r for r in snap.get("rows", []) if "error" not in r]
    if not rows:
        pytest.skip("정상 행이 없다")
    referenced = _js_row_keys(_html())
    # `error`는 미확보 행에만 있는 선택 키다 - 정상 행에 없는 게 정상이다.
    referenced.discard("error")
    missing = sorted(k for k in referenced if k not in rows[0])
    assert not missing, (
        f"대시보드가 읽는 행 키가 스냅샷({path})에 없다: {missing}")


def test_trajectory_and_benchmark_field_names_match():
    snap, path = _newest_dated_snapshot()
    src = _html()
    if snap.get("trajectory"):
        point = snap["trajectory"][0]
        for key in ("date", "portfolio_index", "benchmark_index"):
            assert key in point, f"추이 점에 {key}가 없다({path})"
            assert key in src, f"대시보드가 추이 키 {key}를 안 쓴다"
    if snap.get("benchmark"):
        for key in ("ticker", "return_pct"):
            assert key in snap["benchmark"], f"벤치마크에 {key}가 없다({path})"


# ── 실패 시 낡은 값을 보여주지 않는다 ─────────────────────────────
def test_dashboard_embeds_no_snapshot_data():
    """
    빌드 시점 스냅샷을 내장하면 조회 실패 시 낡은 값이 최신인 척 표시된다.
    수치가 통째로 박혀 있지 않은지 확인한다(측정값 문자열·JSON 블롭).
    """
    src = _html()
    assert "portfolio_return_pct\":" not in src, "스냅샷 JSON이 내장돼 있다"
    assert "OBSERVATIONAL_NOT_INFERENTIAL" not in src, (
        "인식론 문구가 하드코딩돼 있다 - 스냅샷에서 읽어야 한다")


def test_dashboard_has_an_explicit_failure_state():
    src = _html()
    assert "renderError" in src and "불러오지 못했" in src, (
        "조회 실패를 화면에 드러내지 않는다 - 빈 화면은 '문제 없음'으로 오독된다")
    assert "STALE_DAYS" in src, "스냅샷 노후화 경고가 없다"


def test_dashboard_does_not_compute_judgments():
    """관측 표시 도구다 - 등급·비중을 새로 계산하면 안 된다."""
    src = _html()
    for banned in ("function decide", "function judge", "function rebalance",
                   "function recommend"):
        assert banned not in src, f"자동판정 함수가 생겼다: {banned}"


# ── 포인터 파일이 갈리지 않는다 ───────────────────────────────────
def test_latest_json_equals_newest_dated_snapshot():
    latest_path = SNAP_DIR / LATEST_NAME
    if not latest_path.exists():
        pytest.skip("latest.json이 아직 없다")
    newest, path = _newest_dated_snapshot()
    latest = json.loads(latest_path.read_text(encoding="utf-8"))
    assert latest == newest, (
        f"{LATEST_NAME}이 최신 스냅샷({path})과 갈렸다 - "
        "대시보드가 낡은 값을 읽게 된다")


# ── CI 배선 ───────────────────────────────────────────────────────
def test_ci_script_writes_both_dated_and_latest():
    src = (ROOT / "scripts" / "portfolio_track_record_ci.py").read_text(encoding="utf-8")
    assert "LATEST_NAME" in src, "CI 스크립트가 고정 경로 상수를 쓰지 않는다"
    assert src.count('open(') >= 2, "dated/latest 두 파일을 쓰지 않는다"


def test_daily_workflow_refreshes_and_commits_the_dashboard_data():
    """
    주간 워크플로만으로는 부족하다 - 이 스냅샷의 입력은 **매일 바뀌는 주가**라
    주 1회면 최대 6일 묵은 값이 대시보드에 뜬다.
    """
    wf = (ROOT / ".github" / "workflows" / "daily_screen.yml").read_text(encoding="utf-8")
    assert "scripts.portfolio_track_record_ci" in wf, (
        "일일 워크플로가 트랙레코드를 갱신하지 않는다 - 대시보드가 매일 갱신되지 않는다")
    assert "reports/portfolio_track_record/" in wf, (
        "갱신분을 커밋하지 않는다 - 러너는 매번 새로 뜨므로 커밋하지 않으면 사라진다")
