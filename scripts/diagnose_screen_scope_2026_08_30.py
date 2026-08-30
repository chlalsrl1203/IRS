"""
diagnose_screen_scope_2026_08_30.py — 스크리너의 **적용범위**를 실측한다.

## 문제

2026-08-30 첫 전체 유니버스 실행에서 259개 법인이 통과했다. 매수 후보로 쓰기엔
너무 많고, Gap 상위가 VATE($30M, +93%p)·JANL($10M, +78%p)·HTZ 같은 초소형·
부실회복주에 몰려 있다.

## 무엇을 하면 안 되는가 — 임계값을 결과 보고 조정하는 것

이 프로젝트는 그 수법을 반복해서 금지해왔다(LYNCH_TYPE_CAPS·P/B 임계값·
ERP 매핑·screener competition_intensity 상수). "259개는 많으니 시총 10억 컷"은
정확히 그 금지 대상이다 - 근거 없이 유지하던 걸 근거 없는 다른 숫자로 바꾸는
것은 개선이 아니다.

## 대신 무엇을 하는가 — 관측범위 밖 외삽인지 실측한다

`engine/screener.py`의 임계값과 상수(`estimate_drs`의 corpus 중앙값 대체 포함)는
**전부 34종목 ledger 코퍼스에서 나왔다.** 그 코퍼스의 실제 관측범위는:

    Gap        : -14.36%p ~ **+24.38%p**  (최대 ACGL)
    시가총액   : **$3.74B**(MNDY) ~ $817.9B  (중앙값 $42.6B)

대규모 스크리닝 통과 259개 중에는 Gap +93%p(코퍼스 최대의 3.8배)와 시총
$10M(코퍼스 최소의 1/374)이 있다. 즉 **한 번도 검증된 적 없는 범위에 상수를
그대로 외삽**하고 있다 - 이건 임계값 취향 문제가 아니라 적용범위 문제다.

BSX 거짓탈락 사건이 정확히 같은 구조였다: `estimate_drs`가 competition_intensity를
코퍼스 중앙값(12.0)으로 대체하는데, 중앙값에서 멀리 떨어진 종목(BSX 실제 5.4)에서는
구조적으로 오분류한다. 그때는 median에서 벗어난 **한 종목**이었고, 지금은 median을
만든 코퍼스 **범위 자체를 벗어난 집단**이다.

## 이 스크립트가 답하는 질문

**"관측범위를 벗어난 구간에서도 이 스크린이 실제로 작동했는가?"**

PIT 백테스트(6개 T0 × 1,200종목)에 이미 실현수익률이 있고, 그 안에도 극단 Gap
종목이 들어 있다(PJT +118%p 등). 그러니 추측할 필요 없이 **직접 잰다.**

## ⚠️ 구간 경계는 결과를 보기 전에 고정했다

아래 두 상수는 **34종목 ledger 코퍼스의 실측 관측범위**이며, PIT 수익률을
보기 전에 정해졌다(위 docstring에 근거를 남긴 것이 그 기록이다). 결과가
마음에 안 든다고 이 값을 움직이면 그 순간 이 분석은 무효다.
"""
import datetime
import json
import os
import statistics
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))
sys.path.insert(0, _HERE)

from engine.data.providers.sec import public_float_from_facts  # noqa: E402
from engine.filing_dates import DEFAULT_USER_AGENT, full_ticker_universe  # noqa: E402

from pit_backtest import cached_company_facts  # noqa: E402

ROOT = os.path.dirname(_HERE)
PIT_DIR = os.path.join(ROOT, "reports", "pit_backtest")
OUT_DIR = os.path.join(ROOT, "reports", "research")

# ── 검증 코퍼스(34종목 ledger)의 실측 관측범위 — 결과를 보기 전에 고정 ──────
CORPUS_MAX_GAP = 0.2438          # ACGL +24.38%p
CORPUS_MIN_MARKET_CAP = 3.74e9   # MNDY $3.74B


def log(m):
    print(m, flush=True)


def load_t0(t0):
    """T0 하나의 (flagged Gap, 실현수익률) 조인. 반환 [(ticker, gap, ret_pct)]."""
    bt = json.load(open(os.path.join(PIT_DIR, f"pit_backtest_{t0}.json")))
    rt = json.load(open(os.path.join(PIT_DIR, f"pit_returns_{t0}.json")))
    gap = {r["ticker"]: r["expectation_gap_est"] for r in bt["passed_detail"]}
    rows = []
    for r in rt["flagged"]:
        if r["ticker"] in gap:
            rows.append((r["ticker"], gap[r["ticker"]], r["return_pct"]))
    bench = (rt.get("benchmark") or {}).get("return_pct")
    return rows, bench


def market_caps_at(tickers, t0, ua=None):
    """T0 시점 public_float(시총 근사치). 캐시에 없는 종목은 건너뛴다."""
    ua = ua or DEFAULT_USER_AGENT
    t2c = {r["ticker"]: r["cik"] for r in full_ticker_universe(ua)}
    out, missing = {}, 0
    for t in tickers:
        cik = t2c.get(t)
        if not cik:
            missing += 1
            continue
        path = os.path.join(ROOT, ".cache", "companyfacts", f"{cik}.json")
        if not os.path.exists(path):
            missing += 1
            continue
        try:
            with open(path, encoding="utf-8") as f:
                facts = json.load(f)
        except (OSError, json.JSONDecodeError):
            missing += 1
            continue
        pf = public_float_from_facts(facts, as_of=t0)
        if pf:
            out[t] = pf[max(pf)]
        else:
            missing += 1
    return out, missing


def summarize(rows, bench):
    """[(t,gap,ret)] -> 서술통계. p-value는 내지 않는다(다중검정 포화, v3.74 참고)."""
    if not rows:
        return {"n": 0}
    rets = [r for _, _, r in rows]
    s = sorted(rets)
    out = {
        "n": len(rets),
        "median_pct": statistics.median(rets),
        "mean_pct": statistics.fmean(rets),
        "min_pct": s[0],
        "max_pct": s[-1],
        "positive_rate": sum(1 for x in rets if x > 0) / len(rets),
    }
    if bench is not None:
        out["beat_benchmark_rate"] = sum(1 for x in rets if x > bench) / len(rets)
    return out


def survivorship_exposure(t0, listing_csv_active, listing_csv_delisted):
    """
    ⚠️ **이 백테스트의 유니버스가 구조적으로 놓친 회사를 센다.**

    `full_ticker_universe()`는 SEC의 **오늘자** `company_tickers.json`을 읽는다.
    그래서 T0 이후 상장폐지된 회사는 애초에 유니버스에 들어오지 못한다 -
    그리고 하필 그 집단이 **성과가 나빴던 회사들**이다.

    이건 `pit_price_validation.py`가 세던 "가격 확보 실패"와 **다른 층위의
    문제**다. 그쪽은 "유니버스에 들어온 뒤 가격을 못 구한 종목"(실측 flagged
    0건)이고, 이쪽은 "유니버스에 애초에 못 들어온 종목"이라 확보 실패로도
    잡히지 않는다 - 즉 리포트상 완전히 보이지 않는다.

    입력은 Alpha Vantage `LISTING_STATUS`의 CSV 텍스트 두 개
    (state=active&date=T0, state=delisted).
    """
    import csv
    import io
    import urllib.request

    act = {r["symbol"] for r in csv.DictReader(io.StringIO(listing_csv_active))
           if r.get("assetType") == "Stock"}
    gone = {r["symbol"] for r in csv.DictReader(io.StringIO(listing_csv_delisted))
            if r.get("assetType") == "Stock"
            and (r.get("delistingDate") or "") >= t0}
    overlap = act & gone

    req = urllib.request.Request(
        "https://www.sec.gov/files/company_tickers.json",
        headers={"User-Agent": DEFAULT_USER_AGENT})
    today = {r["ticker"].upper()
             for r in json.load(urllib.request.urlopen(req, timeout=30)).values()}
    still = overlap & today
    return {
        "t0": t0,
        "listed_stocks_at_t0": len(act),
        "delisted_since_t0": len(overlap),
        "delisting_rate": len(overlap) / len(act) if act else None,
        "still_in_todays_sec_list": len(still),
        "structurally_absent_from_backtest": len(overlap) - len(still),
        "interpretation": (
            "백테스트 유니버스는 오늘자 SEC 티커목록에서 만들어지므로 이 "
            "종목들은 애초에 채점 대상이 되지 못했다. 죽은 회사만 빠졌으므로 "
            "flagged·not_flagged **양쪽 수익률이 모두 위로 편향**된다. "
            "편향의 크기는 이 데이터만으로는 알 수 없다(폐지 종목의 T0 시총· "
            "수익률이 없으므로) - 방향만 확실하다."),
    }


def main():
    t0s = sorted(
        f[len("pit_backtest_"):-len(".json")]
        for f in os.listdir(PIT_DIR) if f.startswith("pit_backtest_")
    )
    log(f"[진단] T0 {len(t0s)}개: {t0s}")
    log(f"[진단] 사전 고정 경계 — Gap {CORPUS_MAX_GAP*100:.2f}%p / "
        f"시총 ${CORPUS_MIN_MARKET_CAP/1e9:.2f}B (34종목 코퍼스 관측범위)")

    per_t0, pooled = {}, {"gap_in": [], "gap_out": [], "cap_in": [], "cap_out": []}
    bench_by_t0 = {}
    for t0 in t0s:
        rows, bench = load_t0(t0)
        bench_by_t0[t0] = bench
        caps, missing = market_caps_at([t for t, _, _ in rows], t0)

        gin = [r for r in rows if r[1] <= CORPUS_MAX_GAP]
        gout = [r for r in rows if r[1] > CORPUS_MAX_GAP]
        cin = [r for r in rows if caps.get(r[0], 0) >= CORPUS_MIN_MARKET_CAP]
        cout = [r for r in rows if 0 < caps.get(r[0], 0) < CORPUS_MIN_MARKET_CAP]

        for k, v in (("gap_in", gin), ("gap_out", gout),
                     ("cap_in", cin), ("cap_out", cout)):
            pooled[k] += v

        per_t0[t0] = {
            "benchmark_pct": bench,
            "n_flagged_with_return": len(rows),
            "market_cap_unavailable": missing,
            "gap_within_corpus_range": summarize(gin, bench),
            "gap_beyond_corpus_range": summarize(gout, bench),
            "size_within_corpus_range": summarize(cin, bench),
            "size_below_corpus_min": summarize(cout, bench),
        }
        log(f"  {t0}: flagged {len(rows)} (시총미확보 {missing}) "
            f"| Gap 범위내 {len(gin)} / 범위밖 {len(gout)} "
            f"| 시총 범위내 {len(cin)} / 미만 {len(cout)}")

    # ⚠️ 생존편향 노출 — 위 수익률 전부에 걸리는 상위 경고다
    surv = None
    lp = os.path.join(ROOT, "data", "listing_status")
    a_path = os.path.join(lp, "active_2018-06-30.csv")
    d_path = os.path.join(lp, "delisted_all_2026-08-30.csv")
    if os.path.exists(a_path) and os.path.exists(d_path):
        surv = survivorship_exposure(
            "2018-06-30",
            open(a_path, encoding="utf-8").read(),
            open(d_path, encoding="utf-8").read())
        log(f"\n[생존편향] T0=2018-06-30 상장주식 {surv['listed_stocks_at_t0']:,} 중 "
            f"{surv['delisted_since_t0']:,}건({surv['delisting_rate']*100:.1f}%) 폐지 "
            f"-> 백테스트에서 구조적 누락 "
            f"{surv['structurally_absent_from_backtest']:,}건")

    result = {
        "generated_at": datetime.date.today().isoformat(),
        "survivorship_exposure": surv,
        "question": ("34종목 코퍼스의 관측범위를 벗어난 구간에서도 "
                     "screen()의 저평가 판정이 실제 수익률과 관계있는가"),
        "prefixed_boundaries": {
            "corpus_max_gap": CORPUS_MAX_GAP,
            "corpus_min_market_cap": CORPUS_MIN_MARKET_CAP,
            "note": ("34종목 ledger 실측 관측범위. PIT 수익률을 보기 전에 "
                     "고정했다 - 결과에 맞춰 조정하면 이 분석은 무효다."),
        },
        "per_t0": per_t0,
        "pooled": {k: summarize(v, None) for k, v in pooled.items()},
        "caveats": [
            "p-value를 내지 않는다 - 같은 표본을 반복 검정해 FWER가 이미 "
            "포화 상태다(engine/quant/validation.py).",
            "T0마다 보유기간이 다르므로 T0끼리 절대 수익률을 비교하지 말 것.",
            "PIT 유니버스는 SEC 티커목록 앞부분 1,200종목이라 대형주 편중이다 - "
            "코퍼스 범위 밖(소형) 표본이 실제 전체 유니버스보다 적다.",
        ],
    }

    os.makedirs(OUT_DIR, exist_ok=True)
    out_path = os.path.join(OUT_DIR, "screen_scope_diagnosis_2026-08-30.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    log(f"\n[진단] 저장: {out_path}")

    log("\n=== 통합(모든 T0 합산) ===")
    for k, label in (("gap_in", f"Gap ≤ 코퍼스최대(+{CORPUS_MAX_GAP*100:.1f}%p)"),
                     ("gap_out", "Gap > 코퍼스최대 (범위 밖 외삽)"),
                     ("cap_in", f"시총 ≥ 코퍼스최소(${CORPUS_MIN_MARKET_CAP/1e9:.2f}B)"),
                     ("cap_out", "시총 < 코퍼스최소 (범위 밖 외삽)")):
        s = result["pooled"][k]
        if not s.get("n"):
            log(f"  {label:44} 표본 없음")
            continue
        log(f"  {label:44} n={s['n']:4}  중앙값 {s['median_pct']:+8.1f}%  "
            f"평균 {s['mean_pct']:+8.1f}%  플러스비율 {s['positive_rate']*100:3.0f}%")


if __name__ == "__main__":
    main()
