"""
오늘의 실행 브리핑 — 이 저장소에서 «실제로 무엇을 할지»를 한 화면에 낸다.

## 왜 이게 필요했나 (2026-08-28 실측)

지금까지 매일 자동 실행되는 것은 두 가지뿐이었다:
  - `daily_screen_ci.py`  : 신규 후보 탐색 → 실측상 후보의 약 88%가 FCF-DCF
                            적용 불가라 대부분의 날에 «후보 없음»만 출력한다
  - `daily_monitor_ci.py` : 반증조건 기한 감시 → 실제로 작동한다

그런데 **정작 «그래서 오늘 뭘 사고 뭘 보나»에 답하는 산출물이 없었다.**
구체적으로 세 가지가 끊겨 있었다:

1. 매수리스트(`reports/buylist_*.json`)는 **비중만** 있고 금액이 없다.
   즉 그대로는 주문을 낼 수 없다.
2. 미국 개별주식 12종목과 KRX ETF 31종목이 **서로 다른 계좌**에서만 살 수
   있는데(ISA는 국내 상장분만 매수 가능) 두 목록이 한 번도 같이 제시된 적이
   없다.
3. 감시 알림은 별도 산출물이라, 매수 결정과 분리돼 있었다.

이 스크립트는 **새 분석도 새 밸류에이션도 하지 않는다.** 이미 저장된 결과를
사람이 실행할 수 있는 형태로 합치기만 한다.

## 설계상 못박은 것

- **네트워크 의존 0.** 저장된 파일만 읽는다. Finviz·SEC·시세 API가 전부
  죽어도 브리핑은 항상 나온다. 자동화가 조용히 실패하던 경로(v3.68)를
  브리핑까지 전파시키지 않기 위해서다.
- **새 배분 규칙을 만들지 않는다.** 미국 개별주는 이미 근거가 기록된
  `weight_final`을 금액으로 환산할 뿐이고, KRX ETF는 **비중 배분 규칙이
  존재하지 않으므로 후보 순위만** 낸다(없는 규칙을 지어내지 않는다).
- **주수를 계산하지 않는다.** 이 시스템은 실시간 시세를 보지 않는다.
  금액까지만 내고 주수는 체결 시점에 사람이 정한다.
- **검증되지 않은 사실을 브리핑 하단에 매번 반복한다.** 실현 수익률 관측이
  0건이라는 사실은 매수표 옆에 항상 붙어 있어야 한다.
"""

import argparse
import json
import os
import re
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 감시 로직은 이미 daily_monitor_ci에 있다 — 다시 구현하지 않고 그대로 부른다
# (중복 구현이 두 계산을 미묘하게 어긋나게 만든다는 이 프로젝트의 반복 교훈).
from scripts.daily_monitor_ci import run_monitor  # noqa: E402

LEDGER_DIR = "ledger"
REPORTS = "reports"
WEEKDAY_KR = ["월", "화", "수", "목", "금", "토", "일"]


# ── 저장된 산출물 로드 (네트워크 없음) ──────────────────────────────────
def _latest(prefix: str, folder: str = None):
    """
    `<prefix>YYYY-MM-DD.json` 중 가장 늦은 것. 없으면 None.

    ⚠️ 단순 startswith로 고르면 안 된다 — `buylist_`가 `buylist_boundary_review_`
    까지 잡아 공식 매수리스트 대신 경계검토 리포트를 골랐던 실제 사고가 있다.
    날짜로 끝나는 파일만 매칭한다.
    """
    # ⚠️ 기본값을 `folder=REPORTS`로 두면 **정의 시점에 바인딩**돼 모듈 상수를
    # 바꿔도 반영되지 않는다(이 프로젝트가 사이징 감사에서 이미 한 번 밟은
    # 함정 — 그때는 절제실험이 조용히 무력화됐다). 호출 시점에 해석한다.
    folder = REPORTS if folder is None else folder
    if not os.path.isdir(folder):
        return None
    pat = re.compile(r"^" + re.escape(prefix) + r"\d{4}-\d{2}-\d{2}\.json$")
    names = sorted(n for n in os.listdir(folder) if pat.match(n))
    return os.path.join(folder, names[-1]) if names else None


def load_json(path):
    if not path or not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def iter_ledgers(ledger_dir=LEDGER_DIR):
    """티커당 최신 1건(구 파일 잔존 시 중복계상 방지 — v3.32 사고)."""
    latest = {}
    if not os.path.isdir(ledger_dir):
        return []
    for name in sorted(os.listdir(ledger_dir)):
        if not name.endswith(".json"):
            continue
        with open(os.path.join(ledger_dir, name), encoding="utf-8") as f:
            d = json.load(f)
        t = d["meta"]["ticker"]
        if t not in latest or name > latest[t][0]:
            latest[t] = (name, d)
    return [d for _, d in latest.values()]


def won(x):
    return f"{round(x):,}원"


# ── ① 오늘 확인할 것 ────────────────────────────────────────────────────
def section_today(today):
    r = run_monitor(today)
    t, p = r["falsification"], r["predictions"]
    need, due = t["needs_review"], p["due"]

    out = ["## 🚨 오늘 확인할 것"]
    if t.get("state_file_missing"):
        out += ["", "⚠️ `monitor/acknowledgements.json`이 없어 **전부 미확인**으로 "
                    "취급 중이다."]
    if not need and not due:
        out += ["", "**없음.** 기한이 도래한 반증조건·예측 중 미확인 항목이 없다."]
    if need:
        out += ["", f"### 반증조건 {len(need)}건",
                "확인 전에는 해당 종목 비중을 늘리지 말 것.", ""]
        for it in need:
            ctx = (it.get("context") or "").strip().replace("\n", " ")
            out.append(f"- **{it['ticker']}** · 기한 {it['trigger_date']} "
                       f"({it['days_past']}일 경과) — {it.get('reason', '')}")
            if ctx:
                out.append(f"  > {ctx[:200]}")
        out += ["", "확인을 마치면 `monitor/acknowledgements.json`에 결과를 기록한다"
                    "(사람이 커밋 — CI는 이 파일을 쓰지 않는다)."]
    if due:
        out += ["", f"### 예측 해소기한 {len(due)}건", ""]
        for d in due[:10]:
            out.append(f"- **{d['ticker']}** · {d['metric']} · 기한 "
                       f"{d['resolution_date']} ({d['days_past']}일 경과)")
    if t["triggered"]:
        names = ", ".join(f"{x['ticker']}({x['trigger_date']})" for x in t["triggered"])
        out += ["", f"🔴 반증조건 발동상태 유지: {names} — 조치 완료분, 재알림 아님."]
    out += ["", f"<sub>감시 대상 {r['n_ledgers']}종목 · 반증조건 미기재 "
                f"{len(t['no_conditions'])}종목 (⚠️ 미기재는 '안전'이 아니라 "
                f"'감시근거 없음')</sub>"]
    return out, len(need) + len(due)


# ── ② 해외주식 계좌 — 실제 금액이 붙은 매수표 ───────────────────────────
def section_overseas(capital):
    path = _latest("buylist_")
    data = load_json(path)
    out = ["## 💰 해외주식 계좌 — 매수 실행표"]
    if not data:
        out += ["", "매수리스트 파일을 찾지 못했다(`reports/buylist_*.json`)."]
        return out
    rows = data if isinstance(data, list) else data.get("positions") or []
    rows = sorted(rows, key=lambda r: -r["weight_final"])

    out.append("")
    out.append(f"기준 파일 `{os.path.basename(path)}` · 총 투자금 **{won(capital)}**")
    out.append("")
    out.append("| 종목 | 비중 | 금액 | 등급 | 모델점수* | 주의 |")
    out.append("|---|---:|---:|:--:|---:|---|")
    total_w = 0.0
    for r in rows:
        w = r["weight_final"]
        total_w += w
        flags = []
        if r.get("thesis_broken_flag"):
            flags.append("논거 반증")
        if r.get("severe_flag"):
            flags.append("거버넌스")
        if r.get("cap_bound"):
            flags.append("성장상한 바인딩")
        if r.get("model_dependent_universe"):
            flags.append("모델선택 의존")
        if r.get("sbc_dependent_universe"):
            flags.append("SBC 의존")
        if r.get("conf_status") == "미검증":
            flags.append("정성조사 미실시")
        out.append(f"| **{r['ticker']}** | {w * 100:.2f}% | {won(capital * w)} "
                   f"| {r.get('grade', '-')} | {r.get('conf_adj', '-')} "
                   f"| {' · '.join(flags) if flags else '—'} |")
    out.append(f"| **합계** | **{total_w * 100:.2f}%** | **{won(capital * total_w)}** "
               f"| | | |")
    out.append("")
    out.append("⚠️ **주수는 여기서 계산하지 않는다.** 이 시스템은 실시간 시세를 "
               "보지 않으므로, 금액까지만 내고 주수는 체결 시점 시세로 정한다.")
    out.append("⚠️ **\\*모델점수는 확률이 아니다.** `confidence_score()`는 base 50에 "
               "가감점을 더한 미보정 순위점수일 뿐, 실현결과로 검증(calibration)된 "
               "적이 한 번도 없다 — \"70점은 70% 확률로 맞다\"는 뜻이 아니다.")
    out.append("⚠️ ISA 계좌로는 이 종목들을 매수할 수 없다(국내 상장분만 가능). "
               "해외주식 계좌가 필요하다.")
    return out


# ── ③ ISA 계좌 — KRX ETF 후보 (배분 규칙 없음을 명시) ───────────────────
def section_isa(top_n):
    rows = load_json(_latest("krx_etf_ranking_"))
    overlap = load_json(_latest("krx_overlap_"))
    out = ["## 🏦 ISA 계좌 — 국내 상장 ETF 후보"]
    if not rows:
        out += ["", "KRX ETF 순위 파일을 찾지 못했다."]
        return out

    out.append("")
    out.append("**시장요구성장률**이 낮을수록 시장이 이미 요구하는 기대가 낮다는 뜻이다"
               " — 분석자 주관이 개입하지 않는 유일한 비교축이라 이 값으로 정렬한다.")
    out.append("")
    out.append("| 순위 | 종목 | 코드 | 추종 | 시장요구성장 | 총보수 | 순자산(억) | 주의 |")
    out.append("|--:|---|---|---|---:|---:|---:|---|")
    for i, r in enumerate(rows[:top_n], 1):
        flags = list(r.get("fragile_flags") or [])
        if r.get("n_pe_sources", 0) < 2:
            flags.append("단일 P/E 출처")
        aum = r.get("aum_eok")
        out.append(f"| {i} | {r['krx_name']} | {r['krx_ticker']} | {r.get('tracks', '')} "
                   f"| {r['breakeven_pct']:.2f}% | {r['expense_ratio_pct']:.2f}% "
                   f"| {'미확인' if aum is None else f'{aum:,.0f}'} "
                   f"| {' · '.join(flags) if flags else '—'} |")

    out.append("")
    out.append("⚠️ **비중 배분 규칙이 없다.** 이 표는 후보 순위이지 매수 비중이 "
               "아니다 — 근거 없는 배분 규칙을 지어내지 않기 위해 의도적으로 "
               "비중을 내지 않는다.")
    out.append("⚠️ **시장요구성장이 낮다 = 사라**가 아니다. 그 성장조차 못 낼 "
               "섹터면 낮은 게 정상이다(경기민감·원자재 특히 주의).")

    if overlap:
        pairs = (overlap.get("same_index_pairs") or [])[:3]
        real = sorted((overlap.get("pairs") or []),
                      key=lambda p: -p.get("shared_weight", 0))[:3]
        if pairs:
            out.append("")
            out.append("**같이 담아도 분산 효과가 없는 조합**(같은 지수 추종):")
            for p in pairs:
                a, b = p.get("pair_names", ["?", "?"])
                out.append(f"- {a} ↔ {b} — 같은 지수를 재사용하므로 총보수·"
                           f"유동성만 비교해 하나만 고를 것")
        if real:
            out.append("")
            out.append("**겹침이 큰 조합**(상위 10 보유종목 기준 하한):")
            for p in real:
                a, b = p.get("pair_names", ["?", "?"])
                out.append(f"- {a} ↔ {b} — {p.get('shared_weight', 0) * 100:.1f}%p "
                           f"겹침(상위10 기준 하한이므로 실제는 더 크다)")
    return out


# ── ④ 오늘 새로 나온 후보 ───────────────────────────────────────────────
def section_new_candidates(today):
    path = os.path.join(REPORTS, "deep_screen")
    out = ["## 🔍 오늘 새로 나온 후보"]
    stamp = today.isoformat()
    hits = []
    if os.path.isdir(path):
        hits = sorted(n for n in os.listdir(path) if stamp in n)
    out.append("")
    if not hits:
        out.append("**없음.** 신규 후보가 없는 것은 정상이다 — 실측상 스크리닝 "
                   "후보의 대부분이 FCF-DCF 적용 대상이 아니다(적자·상장이력 부족·"
                   "M&A로 인한 성장률 왜곡).")
    else:
        for n in hits:
            d = load_json(os.path.join(path, n)) or {}
            out.append(f"- **{d.get('ticker', n)}** — "
                       f"Gap {d.get('expectation_gap', 0) * 100:+.2f}%p · "
                       f"{d.get('judgment', '')}")
        out.append("")
        out.append("⚠️ 심층 스크리닝은 **정식 분석이 아니다**(경쟁강도·순부채는 "
                   "코퍼스 중앙값으로 가정). 정식 분석 전에는 매수 판단에 쓰지 말 것.")
    return out


def section_broad_screen(top_n=10):
    """
    주간 대규모 스크리닝(scripts/broad_screen.py) 최신 결과.

    ⚠️ 이게 없으면 주간 스크리닝이 **별도 이슈에만 쌓이고 실행 브리핑에는
    안 들어온다** - 실제로 v3.72에서 배선한 뒤 daily_brief가 그 결과를 한
    번도 읽지 않는 상태였다. 이 프로젝트가 반복해서 겪은 "데이터는 있는데
    결정 경로에 배선이 안 된" 패턴(sbc_cross_check가 매수리스트에 안 닿던
    것과 같은 유형)이라 즉시 연결한다.
    """
    path = _latest("broad_screen_", os.path.join(REPORTS, "broad_screen"))
    d = load_json(path)
    out = ["## 🌐 주간 대규모 스크리닝(미국 상장 전체)"]
    if not d:
        out += ["", "아직 결과 파일이 없다(`reports/broad_screen/`). 주간 워크플로가 "
                    "한 번도 완주하지 않았거나 커밋되지 않았다."]
        return out

    passed = d.get("passed_tickers") or []
    out += ["", f"기준 `{os.path.basename(path)}` · 유니버스 "
                f"{d.get('universe_total', 0):,}종목 → 채점 {d.get('scored', 0):,}종목 "
                f"→ 통과 **{len(passed)}종목**", ""]
    if not passed:
        out.append("**통과 후보 없음.**")
    else:
        out.append("| 종목 | 등급 | Gap(추정) | 시총(근사) |")
        out.append("|---|:--:|---:|---:|")
        for r in sorted(passed, key=lambda x: -x["expectation_gap_est"])[:top_n]:
            out.append(f"| **{r['ticker']}** | {r.get('tier', '-')} "
                       f"| {r['expectation_gap_est'] * 100:+.2f}%p "
                       f"| ${r.get('market_cap', 0) / 1e9:.1f}B |")
        if len(passed) > top_n:
            out.append(f"\n(상위 {top_n}종목만 표시 · 전체 {len(passed)}종목)")
    out += ["", "⚠️ **정식 분석이 아니다.** 시가총액은 SEC `EntityPublicFloat` "
                "근사치이고 경쟁강도·순부채는 코퍼스 중앙값 가정이다.",
            "⚠️ 백테스트상 이 스크린은 **상방 선택보다 하방 방어에서 재현성이 "
            "높았다**(하위25%·최저종목 3/3, 중앙값 2/3) — 매수 확신보다 "
            "**제외 근거**로 읽는 것이 근거에 맞다."]
    return out


def section_scorecard():
    """
    PIT 백테스트 성적표 요약.

    ⚠️ 2026-08-29까지 이 브리핑은 "실현 수익률을 **한 번도 관측한 적이 없다**"
    라고 매일 단언했다. 그날 3개 T0 백테스트가 나오면서 그 문장은 **사실이
    아니게 됐다** - 브리핑이 스스로 낡은 주장을 반복하는 상태였다. 이제
    실제 성적표를 읽어 재현 횟수를 그대로 보여준다.

    성적표가 없으면 원래 문구(미검증)를 유지한다 - 없는 검증을 있다고 하지
    않는다.
    """
    path = os.path.join(REPORTS, "pit_backtest", "pit_multi_t0_summary.json")
    rows = load_json(path)
    out = ["## 📊 이 엔진의 성적표(과거시점 재현)"]
    if not rows:
        out += ["", "**실현 수익률 검증 없음** — 위 순위와 비중은 내부 계산의 "
                    "결과이지 성과로 검증된 값이 아니다."]
        return out

    labels = {"min_pct": "최저 종목", "p25_pct": "하위25%",
              "median_pct": "중앙값", "equal_weight_portfolio_pct": "동일가중",
              "beat_benchmark_rate": "벤치마크 초과비율",
              "mean_excl_top5_pct": "상위5 제외 평균"}
    t0s = ", ".join(r["t0"] for r in rows)
    out += ["", f"과거 {len(rows)}개 시점({t0s})에서 그 시점 공시자료만으로 "
                f"판정을 재현하고 이후 실제 수익률과 대조한 결과다.", ""]
    for key in ("min_pct", "p25_pct", "median_pct", "mean_excl_top5_pct",
                "beat_benchmark_rate"):
        wins = sum(1 for r in rows if (r["metrics"].get(key) or {}).get("flagged_better"))
        have = sum(1 for r in rows if key in r["metrics"])
        if not have:
            continue
        mark = "✅" if wins == have else ("⚠️" if wins else "❌")
        out.append(f"- {mark} **{labels.get(key, key)}**: {wins}/{have} 시점에서 "
                   f"저평가 판정군이 앞섬")
    out += ["", "⚠️ **읽는 법** — 재현율이 높은 축(최저 종목·하위25%)은 **하방 "
                "방어**이고, 중앙값·초과비율 같은 상방 선택력은 재현이 덜 됐다. "
                "즉 이 엔진은 지금 근거상 *뭘 사라*보다 ***뭘 피하라***에 더 강하다.",
            "⚠️ 시점당 표본이 수십 종목이고 단일 시장국면이라 "
            "**'시장을 이긴다'는 근거가 아니다**(거래비용·세금 미반영)."]
    return out


# ── 조립 ────────────────────────────────────────────────────────────────
def build(today, capital, top_n):
    lines = [f"# 📋 오늘의 실행 브리핑 — {today.isoformat()} "
             f"({WEEKDAY_KR[today.weekday()]})", ""]
    today_lines, n_need = section_today(today)
    lines += today_lines + [""]
    lines += section_new_candidates(today) + [""]
    lines += section_broad_screen() + [""]
    lines += section_overseas(capital) + [""]
    lines += section_isa(top_n) + [""]
    lines += ["---", ""] + section_scorecard() + [""]
    lines += [
        "<sub>네트워크 의존 없이 저장된 결과만으로 생성 — 외부 API가 죽어도 "
        "이 브리핑은 항상 나온다.</sub>",
    ]
    return "\n".join(lines), n_need


def post(text, today_str):
    """
    브리핑을 GitHub Issue 코멘트로 올린다 — 이게 평일 아침 폰에 도착하는 것이다.

    이슈 탐색은 `daily_screen_ci._find_or_create_issue`를 재사용한다(같은 이슈에
    쌓여야 하루치 기록이 한 곳에 모인다).
    """
    token = os.environ.get("GITHUB_TOKEN")
    repo_full = os.environ.get("GITHUB_REPOSITORY", "")
    if not token or "/" not in repo_full:
        print("[brief] GITHUB_TOKEN/REPOSITORY 미확보 - 게시 건너뜀", file=sys.stderr)
        return False
    owner, repo = repo_full.split("/", 1)
    try:
        import requests
        from scripts.daily_screen_ci import _find_or_create_issue
        num = _find_or_create_issue(token, owner, repo)
        r = requests.post(
            f"https://api.github.com/repos/{owner}/{repo}/issues/{num}/comments",
            headers={"Authorization": f"Bearer {token}",
                     "Accept": "application/vnd.github+json"},
            json={"body": text}, timeout=15)
        if r.status_code >= 300:
            print(f"[brief] 게시 실패 {r.status_code}: {r.text[:200]}", file=sys.stderr)
            return False
    except Exception as e:  # noqa: BLE001
        print(f"[brief] 게시 실패: {e!r}", file=sys.stderr)
        return False
    print(f"[brief] Issue #{num}에 게시 완료", file=sys.stderr)
    return True


def main():
    ap = argparse.ArgumentParser(description="오늘의 실행 브리핑")
    ap.add_argument("--capital", type=float, default=10_000_000,
                    help="해외주식 계좌 총 투자금(원). 기본 1,000만원")
    ap.add_argument("--top", type=int, default=8, help="ISA ETF 후보 표시 개수")
    ap.add_argument("--date", default=None, help="YYYY-MM-DD (기본: 오늘)")
    ap.add_argument("--out", default=None, help="저장 경로(.md)")
    ap.add_argument("--post", action="store_true",
                    help="GitHub Issue에 게시(Actions 환경)")
    args = ap.parse_args()

    today = (date.fromisoformat(args.date) if args.date else date.today())
    text, n_need = build(today, args.capital, args.top)
    print(text)
    if args.out:
        os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text + "\n")
        print(f"[brief] 저장: {args.out}", file=sys.stderr)
    if args.post:
        post(text, today.isoformat())
    print(f"[brief] action_required={bool(n_need)}", file=sys.stderr)


if __name__ == "__main__":
    main()
