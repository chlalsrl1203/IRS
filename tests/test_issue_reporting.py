"""
issue_reporting.py 테스트 (2026-09-01).

고정하는 것:
  ① 제목에 날짜·종류·긴급도가 들어간다(알림 제목만 보고 열지 말지 결정 가능)
  ② 긴급도는 **올라가기만** 한다 - 나중 게시가 조치사항을 제목에서 지우지 못한다
  ③ 하루에 이슈 하나 - 뒤에 오는 게시는 같은 이슈에 댓글을 단다
  ④ 감시 조치사항이 파이프라인 장애보다 높다(감시는 네트워크 의존이 없다)
  ⑤ 채점 0건은 '통과 후보 없음'이 아니라 장애다
  ⑥ 주간 스크리닝은 **검증범위 안**만 세어 제목에 적는다
  ⑦ 게시 실패가 호출부를 멈추지 않는다
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import issue_reporting as IR  # noqa: E402


class _Resp:
    def __init__(self, status=200, data=None):
        self.status_code = status
        self._data = data if data is not None else {}
        self.text = ""

    def json(self):
        return self._data

    def raise_for_status(self):
        if self.status_code >= 300:
            raise AssertionError(f"HTTP {self.status_code}")


class _FakeHttp:
    """requests 호환 최소 구현 - 호출을 전부 기록한다."""

    def __init__(self, issues=None):
        self.issues = issues or []
        self.gets, self.posts, self.patches = [], [], []

    def get(self, url, headers=None, params=None, timeout=None):
        self.gets.append((url, params))
        return _Resp(200, self.issues)

    def post(self, url, headers=None, json=None, timeout=None):
        self.posts.append((url, json))
        return _Resp(201, {"number": 777})

    def patch(self, url, headers=None, json=None, timeout=None):
        self.patches.append((url, json))
        return _Resp(200, {})


# ── ① 제목 ────────────────────────────────────────────────────────────────
def test_title_carries_date_kind_and_urgency():
    t = IR.issue_title("daily", "2026-09-01", "action", "감시 3건")
    assert t.startswith("2026-09-01")
    assert "일일 스크리닝" in t and "🛑 긴급" in t and "(감시 3건)" in t


def test_daily_and_broad_titles_are_distinguishable():
    """사용자 요청의 핵심 - 주간 결과가 일일 제목에 섞이면 안 된다."""
    d = IR.issue_title("daily", "2026-09-01", "routine")
    b = IR.issue_title("broad", "2026-09-01", "routine")
    assert d != b
    assert not b.startswith(IR.title_prefix("daily", "2026-09-01"))


def test_prefix_is_stable_across_urgency_changes():
    """제목 앞부분(날짜·종류)이 불변이어야 긴급도가 바뀌어도 같은 이슈를 찾는다."""
    p = IR.title_prefix("daily", "2026-09-01")
    for key in IR.URGENCY_RANK:
        assert IR.issue_title("daily", "2026-09-01", key).startswith(p)


def test_urgency_is_recoverable_from_title():
    for key in IR.URGENCY_RANK:
        t = IR.issue_title("daily", "2026-09-01", key, "x")
        assert IR.urgency_of_title(t) == key


# ── ② 긴급도는 올라가기만 한다 ────────────────────────────────────────────
def test_escalation_only_upward():
    routine = IR.issue_title("daily", "2026-09-01", "routine")
    action = IR.issue_title("daily", "2026-09-01", "action")
    assert IR.escalates(routine, "action") is True
    assert IR.escalates(action, "routine") is False
    assert IR.escalates(action, "action") is False


def test_untagged_title_gets_upgraded():
    """등급을 못 읽는 제목(수동 생성 등)은 갱신 대상이다."""
    assert IR.escalates("2026-09-01 · 📊 일일 스크리닝", "routine") is True


def test_later_routine_post_does_not_erase_urgent_title():
    """
    감시가 🛑 긴급으로 만들어둔 제목을 뒤이어 도는 브리핑이 지우면 안 된다 -
    조치사항이 제목에서 사라지는 것이 이 설계가 막으려는 실패다.
    """
    http = _FakeHttp([{"number": 5,
                       "title": IR.issue_title("daily", "2026-09-01", "action",
                                               "감시 2건")}])
    n = IR.find_or_create_dated_issue("tok", "o", "r", "daily", "2026-09-01",
                                      "routine", http=http)
    assert n == 5
    assert http.patches == []      # 제목 갱신 없음
    assert http.posts == []        # 새 이슈 생성도 없음


def test_higher_urgency_patches_title_in_place():
    http = _FakeHttp([{"number": 5,
                       "title": IR.issue_title("daily", "2026-09-01", "routine")}])
    n = IR.find_or_create_dated_issue("tok", "o", "r", "daily", "2026-09-01",
                                      "action", "감시 1건", http=http)
    assert n == 5
    assert len(http.patches) == 1
    assert "🛑 긴급" in http.patches[0][1]["title"]
    assert http.posts == []        # 이슈를 새로 만들지 않는다


# ── ③ 하루에 이슈 하나 ────────────────────────────────────────────────────
def test_creates_issue_when_none_exists_for_the_day():
    http = _FakeHttp([{"number": 9,
                       "title": IR.issue_title("daily", "2026-08-31", "routine")}])
    n = IR.find_or_create_dated_issue("tok", "o", "r", "daily", "2026-09-01",
                                      "routine", http=http)
    assert n == 777
    assert len(http.posts) == 1
    assert http.posts[0][1]["title"].startswith("2026-09-01")


def test_closed_issue_of_the_day_is_reused_not_recreated():
    """
    사람이 오늘 이슈를 이미 닫았다면 새로 만들지 않는다 - 자동화가 사람이
    일부러 닫은 것을 되살리는 셈이 된다(닫힌 이슈에도 댓글은 달린다).
    """
    http = _FakeHttp([{"number": 5, "state": "closed",
                       "title": IR.issue_title("daily", "2026-09-01", "routine")}])
    n = IR.find_or_create_dated_issue("tok", "o", "r", "daily", "2026-09-01",
                                      "routine", http=http)
    assert n == 5 and http.posts == []
    assert http.gets[0][1]["state"] == "all"


def test_pull_requests_are_not_mistaken_for_issues():
    http = _FakeHttp([{"number": 3, "pull_request": {"url": "..."},
                       "title": IR.issue_title("daily", "2026-09-01", "routine")}])
    n = IR.find_or_create_dated_issue("tok", "o", "r", "daily", "2026-09-01",
                                      "routine", http=http)
    assert n == 777  # PR을 건너뛰고 새로 만들었다


# ── ④⑤ 일일 긴급도 판정 ──────────────────────────────────────────────────
def _monitor(action=True, needs=2, due=1):
    return {"action_required": action,
            "falsification": {"needs_review": ["x"] * needs},
            "predictions": {"due": ["y"] * due}}


def test_daily_urgency_reads_real_monitor_keys():
    """
    ⚠️ 이 테스트가 이 파일에서 가장 중요하다. `daily_urgency`는 `run_monitor()`의
    반환 dict 키를 손으로 다시 적는데, 그 이름이 어긋나도 예외가 나지 않고
    **조용히 0건으로 세진다**(초판이 실제로 `thesis`라고 적어 그 상태였다).
    R-001 감사에서 `fcf0` 키 오타 하나로 사전등록 6축 중 1축이 죽어 있던 것과
    같은 유형이라, 가짜 dict가 아니라 **실제 실행 결과**로 확인한다.
    """
    from datetime import date

    from daily_monitor_ci import run_monitor
    real = run_monitor(date(2026, 9, 1))
    assert "falsification" in real and "predictions" in real
    assert "needs_review" in real["falsification"]
    assert "due" in real["predictions"]

    # 조치사항이 있는 실제 스키마를 만들어 건수가 실제로 세어지는지 확인
    forced = dict(real, action_required=True)
    forced["falsification"] = dict(real["falsification"], needs_review=["a", "b"])
    forced["predictions"] = dict(real["predictions"], due=["c"])
    key, detail = IR.daily_urgency(monitor_result=forced)
    assert key == "action" and detail == "감시 3건"


def test_monitor_action_outranks_infrastructure_failure():
    """
    감시는 네트워크 의존이 없어(ledger·날짜만) 스크리닝이 통째로 죽어도
    정상 작동한다 - 감시가 찾은 조치사항은 파이프라인 상태와 무관한 사실이다.
    """
    key, detail = IR.daily_urgency(monitor_result=_monitor(),
                                   scored=0, infra_failures=24)
    assert key == "action" and "3건" in detail


def test_zero_scored_is_broken_not_routine():
    key, detail = IR.daily_urgency(monitor_result=_monitor(action=False),
                                   n_passed=0, scored=0)
    assert key == "broken" and "채점 0건" in detail


def test_scored_none_is_not_treated_as_broken():
    """스크리닝이 아예 안 돈 경우(감시 단독 등)를 장애로 오분류하지 않는다."""
    key, _ = IR.daily_urgency(monitor_result=None, scored=None)
    assert key == "routine"


def test_passed_candidates_outrank_routine():
    key, detail = IR.daily_urgency(n_passed=2, scored=25)
    assert key == "candidates" and "2종목" in detail


def test_urgency_rank_ordering_is_explicit():
    r = IR.URGENCY_RANK
    assert r["action"] > r["broken"] > r["candidates"] > r["routine"]


# ── ⑥ 주간 스크리닝은 검증범위 안만 센다 ──────────────────────────────────
def test_broad_urgency_counts_only_in_scope_candidates():
    """
    2026-08-30 첫 전체 실행에서 통과 259종목 중 173종목이 코퍼스 관측범위
    밖이었다 - 259를 제목에 적으면 실제로 볼 게 얼마인지 알림에서 알 수 없다.
    """
    result = {"scored": 500, "passed_tickers": [
        {"ticker": "A", "out_of_validated_scope": []},
        {"ticker": "B", "out_of_validated_scope": ["시총 범위 밖"]},
        {"ticker": "C", "out_of_validated_scope": ["Gap 범위 밖"]},
    ]}
    key, detail = IR.broad_urgency(result)
    assert key == "candidates" and "1종목" in detail and "3" not in detail


def test_broad_urgency_flags_all_out_of_scope_case():
    result = {"scored": 500, "passed_tickers": [
        {"ticker": "B", "out_of_validated_scope": ["시총 범위 밖"]}]}
    key, detail = IR.broad_urgency(result)
    assert "범위 밖" in detail


def test_broad_urgency_zero_scored_is_broken():
    key, _ = IR.broad_urgency({"scored": 0, "passed_tickers": []})
    assert key == "broken"


# ── ⑦ 게시 실패가 호출부를 멈추지 않는다 ─────────────────────────────────
def test_report_returns_none_instead_of_raising(monkeypatch):
    class _Boom:
        def get(self, *a, **k):
            raise RuntimeError("네트워크 죽음")

    monkeypatch.setenv("GITHUB_TOKEN", "tok")
    monkeypatch.setenv("GITHUB_REPOSITORY", "o/r")
    logged = []
    assert IR.report("daily", "2026-09-01", "본문", log=logged.append,
                     http=_Boom()) is None
    assert any("게시 실패" in m for m in logged)


def test_report_skips_quietly_without_credentials(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)
    logged = []
    assert IR.report("daily", "2026-09-01", "본문", log=logged.append) is None
    assert any("미확보" in m for m in logged)


def test_report_posts_comment_to_the_found_issue():
    http = _FakeHttp([{"number": 5,
                       "title": IR.issue_title("daily", "2026-09-01", "action")}])
    n = IR.report("daily", "2026-09-01", "본문입니다", urgency_key="routine",
                  log=lambda m: None, http=http, creds=("tok", "o", "r"))
    assert n == 5
    assert http.posts[-1][0].endswith("/issues/5/comments")
    assert http.posts[-1][1]["body"] == "본문입니다"


def test_unknown_kind_is_rejected():
    """오타로 새 종류가 조용히 생기면 그날 이슈가 갈라진다."""
    for bad in ("weekly", "Daily", ""):
        try:
            IR.issue_title(bad, "2026-09-01", "routine")
        except ValueError:
            continue
        raise AssertionError(f"{bad!r}가 통과했다")
