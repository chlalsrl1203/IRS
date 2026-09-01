"""
issue_reporting.py (2026-09-01) — 자동 실행 결과를 **날짜별 이슈**로 올린다.

## 왜 바꿨나

지금까지 모든 자동 실행(일일 스크리닝·브리핑·감시·관심종목)이 제목이 고정된
**단 하나의 이슈**(`📊 IRS 일일 스크리닝 결과`)에 댓글을 쌓았다. 주간 대규모
스크리닝만 별도 이슈였다. 그 결과 두 가지가 안 됐다:

  1. **알림 제목이 매일 똑같아서** 폰 알림만 봐서는 오늘 볼 게 있는지 없는지
     알 수 없다. 열어봐야만 안다 - 그러면 며칠 뒤부터는 안 열어보게 되고,
     그건 v3.64가 막으려던 알림 피로 그 자체다.
  2. 하루치 기록을 찾으려면 수백 개 댓글을 스크롤해야 한다.

그래서 **하루에 이슈 하나**를 쓰고, 제목에 날짜와 **긴급도**를 박는다.
알림 제목만 보고 열어볼지 말지 결정할 수 있어야 한다.

    2026-09-01 · 📊 일일 스크리닝 · 🛑 긴급 (감시 3건)
    2026-09-01 · 📊 일일 스크리닝 · ⚪ 정상
    2026-08-30 · 📈 주간 대규모 스크리닝 · 🔵 후보 (범위 안 12종목)

## 하루 알림 1건은 그대로 유지한다

**이슈를 여러 개 만들지 않는다.** 그날 **먼저 올리는 쪽이 이슈를 만들고**
나머지는 같은 이슈에 댓글을 단다(제목 앞부분 `날짜 · 마커`로 찾는다).
스크리닝·브리핑·감시가 각자 이슈를 만들면 하루에 알림이 3~4건이 되어 위
1번 문제가 형태만 바꿔 재발한다.

## ⚠️ 긴급도는 **올라가기만** 한다

나중에 올리는 쪽이 더 낮은 긴급도를 들고 와도 제목을 내리지 않는다. 감시가
`🛑 긴급`으로 만들어둔 제목을 뒤이어 도는 브리핑이 `⚪ 정상`으로 덮으면
**이미 발견한 조치사항이 제목에서 사라진다** - 이 프로젝트가 반복해서
경계해온 "데이터 없음/미확인을 안전으로 표시하는" 실패의 제목판이다.

## 긴급도 서열의 근거

    action     🛑 긴급  — 반증조건 기한도래·예측 해소기한 등 **사람이 볼 것**
    broken     🔧 장애  — 파이프라인이 실행되지 못함(정상적인 빈 결과와 다름)
    candidates 🔵 후보  — 통과 후보가 나옴
    routine    ⚪ 정상  — 아무 일 없음

**감시(action)가 장애(broken)보다 위**인 이유: 감시는 네트워크 의존이 전혀
없고(ledger와 날짜만 본다) 스크리닝이 통째로 죽어도 정상 작동한다(v3.64).
즉 감시가 조치사항을 찾았다면 그건 파이프라인 상태와 무관하게 확실한
사실이고, 장애는 "오늘 결과를 못 얻었다"는 뜻이라 조치 우선순위가 낮다.

라벨은 붙이지 않는다 - 제목이 이미 날짜·종류·긴급도를 전부 담고 있어
라벨이 추가로 거르는 게 없고, 라벨 생성 실패라는 실패 지점만 늘어난다
(Simplicity First - 실증된 필요만큼만).
"""
import os

URGENCY_RANK = {"routine": 0, "candidates": 1, "broken": 2, "action": 3}
URGENCY_LABEL = {
    "action": "🛑 긴급",
    "broken": "🔧 장애",
    "candidates": "🔵 후보",
    "routine": "⚪ 정상",
}
KIND_MARKER = {
    "daily": "📊 일일 스크리닝",
    "broad": "📈 주간 대규모 스크리닝",
}


# ── 제목 (순수 함수) ─────────────────────────────────────────────────────
def kind_label(kind):
    if kind not in KIND_MARKER:
        raise ValueError(f"알 수 없는 종류: {kind!r} (가능: {sorted(KIND_MARKER)})")
    return KIND_MARKER[kind]


def title_prefix(kind, date_str):
    """그날 그 종류의 이슈를 찾는 열쇠. 긴급도가 바뀌어도 이 부분은 불변이다."""
    return f"{date_str} · {kind_label(kind)}"


def issue_title(kind, date_str, urgency_key, detail=None):
    if urgency_key not in URGENCY_RANK:
        raise ValueError(f"알 수 없는 긴급도: {urgency_key!r}")
    title = f"{title_prefix(kind, date_str)} · {URGENCY_LABEL[urgency_key]}"
    if detail:
        title += f" ({detail})"
    return title


def urgency_of_title(title):
    """제목에서 긴급도를 되읽는다. 없으면 None(=아직 등급이 없는 제목)."""
    for key, label in URGENCY_LABEL.items():
        if label in (title or ""):
            return key
    return None


def escalates(current_title, new_urgency):
    """
    제목을 바꿔야 하는가. **올라갈 때만 True** - 내려가는 갱신은 하지 않는다.
    등급을 못 읽는 제목(수동 생성 등)은 갱신 대상으로 본다.
    """
    cur = urgency_of_title(current_title)
    return URGENCY_RANK[new_urgency] > URGENCY_RANK.get(cur, -1)


# ── 긴급도 판정 (순수 함수) ──────────────────────────────────────────────
def daily_urgency(monitor_result=None, n_passed=0, scored=None, infra_failures=0):
    """
    일일 실행의 긴급도. 반환 `(key, detail)`.

    `scored == 0`은 "통과 후보 없음"이 아니라 **채점 자체를 못 했다**는 뜻이라
    장애로 센다(v3.68에서 실제로 이 둘이 리포트상 구분되지 않아 고장을 놓쳤다).
    `scored`가 None이면 스크리닝이 아예 안 돈 경우이므로 장애로 판정하지
    않는다 - 감시 단독 실행 등 정상적인 경로가 있다.
    """
    if monitor_result and monitor_result.get("action_required"):
        # ⚠️ 키 이름을 여기서 다시 적는 순간 조용히 어긋날 수 있다(R-001 감사에서
        # `fcf0` 키 오타 하나로 사전등록 6축 중 1축이 통째로 죽어 있었다).
        # `run_monitor()`의 실제 반환 스키마와 일치하는지를 테스트가 확인한다:
        # tests/test_issue_reporting.py::test_daily_urgency_reads_real_monitor_keys
        t = monitor_result.get("falsification") or {}
        p = monitor_result.get("predictions") or {}
        n = len(t.get("needs_review") or []) + len(p.get("due") or [])
        return "action", (f"감시 {n}건" if n else "감시 조치필요")
    if scored == 0 or infra_failures:
        if scored == 0:
            return "broken", "채점 0건"
        return "broken", f"장애 {infra_failures}종목"
    if n_passed:
        return "candidates", f"후보 {n_passed}종목"
    return "routine", None


def broad_urgency(result):
    """
    주간 대규모 스크리닝의 긴급도. 반환 `(key, detail)`.

    ⚠️ 후보 수는 **검증범위 안**만 센다. 2026-08-30 첫 전체 실행에서 통과
    259종목 중 173종목이 코퍼스 관측범위 밖(초소형주·극단 Gap)이었다 -
    259를 제목에 적으면 실제로 볼 만한 게 얼마인지 알림에서 알 수 없다.
    """
    scored = result.get("scored")
    if not scored:
        return "broken", "채점 0건"
    rows = result.get("passed_tickers") or []
    in_scope = [r for r in rows if not r.get("out_of_validated_scope")]
    if in_scope:
        return "candidates", f"범위 안 {len(in_scope)}종목"
    if rows:
        return "candidates", f"전부 범위 밖 {len(rows)}종목"
    return "routine", None


# ── GitHub (네트워크) ────────────────────────────────────────────────────
def github_env():
    """`(token, owner, repo)` 또는 미확보 시 `(None, None, None)`."""
    token = os.environ.get("GITHUB_TOKEN")
    repo_full = os.environ.get("GITHUB_REPOSITORY", "")
    if not token or "/" not in repo_full:
        return None, None, None
    owner, repo = repo_full.split("/", 1)
    return token, owner, repo


def _headers(token):
    return {"Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json"}


def _default_body(kind):
    common = ("⚠️ **1차 추정치일 뿐 정식 판정이 아닙니다** - 정식 분석은 "
              "`engine/pipeline.py`의 `run_analysis()`로만 확정됩니다.\n\n"
              "제목의 긴급도는 그날 올라온 것 중 **가장 높은 것**이며 "
              "내려가지 않습니다(조치사항이 제목에서 사라지지 않게).")
    if kind == "broad":
        return ("이 이슈에는 그 주 SEC 등록 전체 상장기업(약 1만개) 스크리닝 "
                "결과가 담깁니다. 시가총액은 SEC `EntityPublicFloat` 근사치입니다."
                f"\n\n{common}")
    return ("이 이슈에는 **오늘 하루치** 자동 실행 결과(스크리닝·심층분석·"
            f"보유종목 감시·브리핑)가 댓글로 쌓입니다.\n\n{common}")


def find_or_create_dated_issue(token, owner, repo, kind, date_str,
                               urgency_key, detail=None, http=None):
    """
    그날 그 종류의 이슈를 찾고, 없으면 만든다. 이미 있으면 **긴급도가 올라갈
    때만** 제목을 갱신한다. 반환은 이슈 번호.

    `http`는 테스트용 주입점이다(requests 호환 객체).
    """
    if http is None:
        import requests as http  # noqa: N813

    base = f"https://api.github.com/repos/{owner}/{repo}/issues"
    h = _headers(token)
    # state=all: 사용자가 오늘 이슈를 이미 닫았다면 새로 만들지 않고 그 이슈에
    # 단다(닫힌 이슈에도 댓글은 달린다). 새로 만들면 사람이 일부러 닫은 것을
    # 자동화가 되살리는 셈이 된다.
    r = http.get(base, headers=h,
                 params={"state": "all", "per_page": 100}, timeout=15)
    r.raise_for_status()
    prefix = title_prefix(kind, date_str)
    for issue in r.json():
        title = issue.get("title") or ""
        if "pull_request" in issue or not title.startswith(prefix):
            continue
        num = issue["number"]
        if escalates(title, urgency_key):
            new_title = issue_title(kind, date_str, urgency_key, detail)
            http.patch(f"{base}/{num}", headers=h,
                       json={"title": new_title}, timeout=15)
        return num

    r = http.post(base, headers=h,
                  json={"title": issue_title(kind, date_str, urgency_key, detail),
                        "body": _default_body(kind)}, timeout=15)
    r.raise_for_status()
    return r.json()["number"]


def post_comment(token, owner, repo, number, body, http=None):
    if http is None:
        import requests as http  # noqa: N813
    r = http.post(
        f"https://api.github.com/repos/{owner}/{repo}/issues/{number}/comments",
        headers=_headers(token), json={"body": body}, timeout=15)
    return r.status_code < 300


def report(kind, date_str, body, urgency_key="routine", detail=None,
           log=print, http=None, creds=None):
    """
    한 번에: 그날 이슈를 찾거나 만들고 → 댓글을 단다.

    `creds`가 있으면 `(token, owner, repo)`를 그대로 쓰고, 없으면 환경변수에서
    읽는다(Actions 기본 경로).

    실패해도 예외를 던지지 않는다 - 게시는 부가기능이고, 게시가 죽었다고
    호출부(스크리닝·감시)가 멈추면 부가기능 하나가 본체를 멈추는 것이다.
    """
    token, owner, repo = creds if creds else github_env()
    if not token:
        log("[issue] GITHUB_TOKEN/GITHUB_REPOSITORY 미확보 - 게시 건너뜀")
        return None
    try:
        num = find_or_create_dated_issue(token, owner, repo, kind, date_str,
                                         urgency_key, detail, http=http)
        if not post_comment(token, owner, repo, num, body, http=http):
            log(f"[issue] #{num} 댓글 게시 실패")
            return None
    except Exception as e:  # noqa: BLE001
        log(f"[issue] 게시 실패: {e!r}")
        return None
    log(f"[issue] #{num} ({issue_title(kind, date_str, urgency_key, detail)}) 게시 완료")
    return num
