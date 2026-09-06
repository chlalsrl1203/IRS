"""
research_queue.py (2026-08-30) — 스크리닝과 매수리스트 **사이의 빠진 계층**.

## 무엇이 끊겨 있었나

2026-08-30 실측:

    주간 대규모 스크리닝 통과       259개 법인
    그중 검증 코퍼스 관측범위 안     86개
    이미 정식분석(ledger) 완료        5개  (ACGL·BSY·COR·GEN·PGR)
    이미 매수리스트 보유              3개  (ACGL·GEN·PGR)
    **한 번도 분석된 적 없는 신규**  **81개**

그런데 매수리스트(`scripts/build_buylist_2026_08_03.py`)는 종목마다
`BUCKET`(팩터 분류)·`CONFIDENCE_ADJ`(정성 심층조사 결과)를 요구하고, 그
앞단인 `run_analysis()`는 `model_choice_reason`·`subjective_input_basis` 없이는
**실행 자체를 거부한다**(v3.19). 즉 스크리닝 결과를 매수리스트에 자동으로
밀어 넣는 경로는 **원리적으로 존재할 수 없다** - 넣으려면 그 빈칸을 지어내야
하고, 그건 이 프로젝트가 반복해서 금지해온 짓이다.

## 그래서 연결의 정체는 "자동 승격"이 아니라 "분석 우선순위"다

진짜 병목은 **"81개 중 무엇을 다음에 분석할 것인가"**다. 정식 분석 한 건에는
사람의 주관적 입력과 정성조사가 들어가므로 81개를 다 할 수 없다. 이 모듈은
그 선택을 돕는다.

## ⭐ 지금 버려지고 있던 신호 — 지속성

주간 스크린은 매번 결과 파일을 새로 쓰고 **이전 주와 대조하지 않는다.** 그런데
4주 연속 통과한 종목과 한 주만 반짝 통과한 종목은 전혀 다르다(후자는 시총
근사치 오차나 일시적 재무 왜곡일 수 있다). 큐가 실행 이력을 누적하면 그
구분이 **공짜로** 생긴다.

⚠️ 지금은 스크린 실행이 1회뿐이라 전 종목이 `times_seen=1`이다. 이 축은
**주가 쌓여야 작동한다** - 오늘은 아무것도 구분하지 못한다는 사실을 그대로
기록해둔다(없는 신호를 있는 척하지 않는다).

## ⚠️ 합성 점수를 만들지 않는다

우선순위를 하나의 숫자로 합치지 않는다(§31 안티기능 등록부 - 단일 합성점수).
대신 **객관적 사실의 사전식(lexicographic) 정렬**을 쓴다:

    1. 검증 코퍼스 관측범위 **안**인가        (engine/validated_scope.py)
    2. 아직 정식분석(ledger)이 **없는가**      (있으면 새 연구가 필요 없다)
    3. 몇 주 **연속** 통과했는가 (내림차순)
    4. 스크린 추정 Gap (내림차순) — 동점 처리용

각 단계가 전부 확인 가능한 사실이고 가중치가 없다. 3·4의 순서가 이 모듈의
유일한 판단인데, Gap을 마지막에 둔 이유는 **그 값이 이 파이프라인에서 가장
거친 추정치**이기 때문이다(시총은 public_float 근사, DRS는 코퍼스 중앙값 대체).

## 상태는 손으로 관리하지 않는다 — 파생한다

`monitor/acknowledgements.json`처럼 사람이 유지하는 상태 파일을 하나 더
만들면 낡는다. 상태는 **저장소의 사실에서 파생**한다:

    IN_BUYLIST : 현재 매수리스트에 있음
    ANALYZED   : ledger에 정식분석이 있음(매수리스트에는 없음)
    EXCLUDED   : 조사했고 정량모델 대상이 아니라고 결정함(아래 참고)
    QUEUED     : 위 셋 다 아님 — 사람이 아직 안 본 종목

## ⚠️ EXCLUDED는 이 원칙의 유일한 예외다 - 파생할 소스가 없기 때문

IN_BUYLIST/ANALYZED는 다른 파일(매수리스트/ledger)이 이미 진실을 담고
있어 거기서 읽기만 하면 된다. 그런데 "조사했고 FRAMEWORK_MISMATCH로
제외했다"는 사실은 **ledger를 안 만드는 게 결정 그 자체라서** 파생할
소스가 원리적으로 없다 - 2026-08-30~09-04 사이 30개 넘는 종목이 이렇게
제외됐는데 전부 CLAUDE.md 산문에만 남아, LNTH가 실제로 큐에 재등장해
사람이 또 조사해야 했다.

그래서 `data/excluded_tickers.json`(사람이 유지하는 작은 레지스트리,
`portfolio/holdings.json`과 같은 성격)을 뒀다 - 단, **은행/REIT/원자재
사이클처럼 회사의 사업구조 자체가 DCF 가정과 안 맞는 "구조적" 배제**와
**피인수 확정처럼 시장에서 곧 사라지는 배제**만 담는다. "실적이 실제로
나빠져서" 뺀 종목(예: KR·AGCO)은 넣지 않는다 - 그건 시점부 판단이라
나중에 실적이 개선되면 재조사할 가치가 있고, 큐가 그런 턴어라운드
후보를 다시 골라내는 건 버그가 아니라 스크리닝의 목적 중 하나다.

ledger/매수리스트에 등재된 종목이 우선한다(과거 제외 결정이 나중에
번복된 경우 - 예: NOW는 2026-08-14 FRAMEWORK_MISMATCH로 잘못 판단됐다가
2026-09-05 정정돼 정식 ledger가 생겼다) - EXCLUDED는 그 둘 다 없을
때만 적용된다.
"""
import datetime

from engine.validated_scope import out_of_scope_reasons

STATES = ("IN_BUYLIST", "ANALYZED", "EXCLUDED", "QUEUED")

_MISSING = object()


def derive_state(ticker, ledger_tickers, buylist_tickers, excluded_tickers=None):
    """상태를 저장소의 사실에서 파생한다(EXCLUDED만 예외 - 모듈 docstring 참고).

    ledger·매수리스트 사실이 excluded_tickers보다 우선한다 - 과거 제외
    결정이 나중에 번복돼 정식분석이 생긴 경우(NOW 선례) 그 최신 사실을
    따라야 한다.
    """
    if ticker in buylist_tickers:
        return "IN_BUYLIST"
    if ticker in ledger_tickers:
        return "ANALYZED"
    if excluded_tickers and ticker in excluded_tickers:
        return "EXCLUDED"
    return "QUEUED"


def merge_run(queue, passed_rows, run_date):
    """
    한 번의 스크린 결과를 큐에 병합한다. **순수 함수** - 파일·네트워크 없음.

    queue       : {ticker: entry} (없으면 빈 dict)
    passed_rows : broad_screen 결과의 `passed_tickers` 항목들
                  (ticker / tier / expectation_gap_est / market_cap /
                   out_of_validated_scope)
    run_date    : 이 실행의 날짜(ISO)

    ⚠️ **이번에 안 나온 종목을 큐에서 지우지 않는다.** 지웠다가 다음 주에
    다시 나오면 `times_seen`이 1로 초기화돼 지속성 신호가 통째로 사라진다.
    대신 `last_seen`이 오래된 항목을 `weeks_since_seen`으로 드러낸다 -
    "안 보인다"와 "본 적 없다"는 다르다.
    """
    queue = {t: dict(e) for t, e in (queue or {}).items()}
    for row in passed_rows:
        t = row["ticker"]
        e = queue.get(t)
        if e is None:
            e = {"ticker": t, "first_seen": run_date, "times_seen": 0,
                 "runs_seen": []}
            queue[t] = e
        if run_date not in e["runs_seen"]:
            e["runs_seen"].append(run_date)
            e["times_seen"] = len(e["runs_seen"])
        e["last_seen"] = run_date
        e["latest_gap"] = row.get("expectation_gap_est")
        e["tier"] = row.get("tier")
        e["market_cap"] = row.get("market_cap")

        # ⚠️ **"키 없음"을 "범위 안"으로 읽지 않는다.** v3.76 이전에 생성된
        # 스크리닝 결과에는 `out_of_validated_scope` 필드가 아예 없는데,
        # `row.get(...) or []`로 받으면 범위 밖 종목이 전부 "범위 안"이 된다 -
        # 실제로 첫 실행에서 VATE(Gap +93%p, 시총 $0.03B)가 최우선 분석 후보로
        # 올라왔다. 데이터 없음을 안전으로 오독하는 이 프로젝트의 반복 패턴이라,
        # 필드가 없으면 gap·시총으로 **다시 계산한다**(둘 다 이미 갖고 있다).
        scope = row.get("out_of_validated_scope", _MISSING)
        if scope is _MISSING:
            scope = out_of_scope_reasons(
                gap=row.get("expectation_gap_est"),
                market_cap=row.get("market_cap"))
            e["scope_recomputed"] = True
        e["out_of_validated_scope"] = scope or []
        e["best_gap"] = max(e.get("best_gap", float("-inf")),
                            row.get("expectation_gap_est", float("-inf")))
    return queue


def annotate(queue, ledger_tickers, buylist_tickers, today=None, excluded_tickers=None):
    """큐 항목에 파생 상태와 경과 주수를 붙인다.

    excluded_tickers: {ticker: {"reason_category": ..., "reason": ...}} 형태의
    `data/excluded_tickers.json` 항목들(선택). 넘기지 않으면 기존 동작 그대로
    (EXCLUDED 상태가 나오지 않는다) - opt-in.
    """
    today = today or datetime.date.today().isoformat()
    excluded_tickers = excluded_tickers or {}
    out = {}
    for t, e in queue.items():
        e = dict(e)
        e["state"] = derive_state(t, ledger_tickers, buylist_tickers, excluded_tickers)
        if e["state"] == "EXCLUDED":
            e["exclusion_reason"] = excluded_tickers[t]
        e["in_validated_scope"] = not e.get("out_of_validated_scope")
        try:
            d0 = datetime.date.fromisoformat(e.get("last_seen", today))
            d1 = datetime.date.fromisoformat(today)
            e["days_since_seen"] = (d1 - d0).days
        except ValueError:
            e["days_since_seen"] = None
        out[t] = e
    return out


def priority_order(entries):
    """
    분석 우선순위 정렬. **합성 점수 없음** - 사전식 정렬이다(모듈 docstring 참고).

    반환은 정렬된 리스트이며, 각 항목에 `priority_reason`(왜 이 순위인지)이
    붙는다 - 순위만 주고 근거를 안 주면 사람이 검증할 수 없다.
    """
    def key(e):
        return (
            0 if e.get("in_validated_scope") else 1,      # 범위 안 먼저
            0 if e.get("state") == "QUEUED" else 1,       # 미분석 먼저
            -(e.get("times_seen") or 0),                  # 오래 살아남은 것 먼저
            -(e.get("latest_gap") or float("-inf")),      # 동점 처리
        )

    ordered = sorted(entries, key=key)
    for e in ordered:
        bits = []
        bits.append("검증범위 안" if e.get("in_validated_scope") else "범위 밖")
        bits.append({"QUEUED": "미분석", "ANALYZED": "분석완료",
                     "IN_BUYLIST": "보유중", "EXCLUDED": "제외됨"}[e["state"]])
        bits.append(f"{e.get('times_seen', 0)}회 연속통과")
        e["priority_reason"] = " · ".join(bits)
    return ordered


def next_to_research(entries, n=10):
    """
    사람이 다음에 분석할 후보 상위 n개. **범위 밖·이미 분석된 것은 제외한다** -
    새 연구가 필요한 종목만 남긴다.
    """
    cand = [e for e in entries
            if e.get("in_validated_scope") and e.get("state") == "QUEUED"]
    return priority_order(cand)[:n]


def persistence_available(queue):
    """
    지속성 축이 실제로 작동하는지. 실행이 1회뿐이면 전 종목 times_seen=1이라
    **아무것도 구분하지 못한다** - 그 사실을 호출부가 표시할 수 있게 알려준다.
    """
    runs = set()
    for e in queue.values():
        runs.update(e.get("runs_seen") or [])
    return {"n_runs": len(runs), "runs": sorted(runs),
            "discriminating": len(runs) >= 2}
