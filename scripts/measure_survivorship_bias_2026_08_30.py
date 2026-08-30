"""
measure_survivorship_bias_2026_08_30.py — 백테스트가 **못 본 집단**을 직접 채점한다.

## 질문

PIT 백테스트는 유니버스를 오늘자 SEC 티커목록으로 만들어, T0=2018-06-30 당시
연차보고서를 낸 7,784개 CIK 중 **4,118개(52.9%)를 원천적으로 보지 못했다.**
그러면 자연히 따라오는 질문이 있다 — **그 집단에서도 저평가 판정이 나왔을까?
나왔다면 몇 개나?**

나왔다면 백테스트의 flagged 표본은 불완전하고, 빠진 종목들의 운명(폐지)이
성과 수치에 반영되지 않은 것이다.

## ⚠️ 편향의 **방향**은 단정하지 않는다 (2026-08-30 자체 정정)

처음에는 "죽은 회사만 빠졌으니 수익률이 위로 편향"이라 적었는데 **부정확했다.**
실제 사라진 목록을 열어보니 셋이 섞여 있다:

  - **AKORN**(2020 파산)·**ACETO**(2019 파산) -> 빠지면 수익률 **위로** 편향
  - **HESS**(2024 셰브론 피인수) -> 프리미엄 인수라 빠지면 **아래로** 편향
  - **ALABAMA POWER**·**SPIRE ALABAMA** -> 자회사 채권 필자, 애초에 티커 없음

즉 "생존하지 않은 회사가 빠졌다"는 맞지만 "그래서 위로 편향됐다"는 근거가
부족하다. 이 스크립트는 방향을 가정하지 않고 **빠진 집단의 크기와 판정
분포만** 잰다. 파산/인수 구분은 이 데이터로는 불가능하다(LISTING_STATUS가
폐지 사유를 주지 않는다) - 정직하게 미해결로 남긴다.

## 표본

`missing = universe_at(T0) - 오늘자 SEC CIK`에서 **CIK 오름차순 앞부분 N개**를
쓴다. CIK는 등록 시점에 부여되므로 생존 여부와 무관하다 - 결과를 보고 표본을
고르는 사후선택이 원천적으로 불가능하다.

⚠️ 자회사 채권 필자는 `EntityPublicFloat`이 없어 파이프라인이 자동으로
걸러낸다(별도 처리가 필요 없다) - 그 제외 건수도 함께 보고한다.
"""
import argparse
import datetime
import json
import os
import sys
import urllib.request

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))
sys.path.insert(0, _HERE)

from engine.data.providers.sec_full_index import universe_at  # noqa: E402
from engine.filing_dates import DEFAULT_USER_AGENT  # noqa: E402
from engine.screener import screen_all  # noqa: E402
from engine.validated_scope import out_of_scope_reasons  # noqa: E402

from broad_screen import build_candidate  # noqa: E402
from pit_backtest import fetch_pit_series  # noqa: E402

ROOT = os.path.dirname(_HERE)
OUT_DIR = os.path.join(ROOT, "reports", "research")


def log(m):
    print(m, flush=True)


def todays_ciks(ua):
    req = urllib.request.Request(
        "https://www.sec.gov/files/company_tickers.json", headers={"User-Agent": ua})
    return {str(r["cik_str"]).zfill(10)
            for r in json.load(urllib.request.urlopen(req, timeout=30)).values()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--as-of", default="2018-06-30")
    ap.add_argument("--limit", type=int, default=600)
    args = ap.parse_args()
    ua = DEFAULT_USER_AGENT
    t0 = args.as_of

    log(f"[편향측정] T0={t0} 유니버스 재구성(SEC full-index)...")
    uni = universe_at(t0, user_agent=ua)
    today = todays_ciks(ua)
    missing = sorted(set(uni) - today)
    log(f"[편향측정] T0 유니버스 {len(uni):,} / 오늘 없음 {len(missing):,} "
        f"({len(missing)/len(uni)*100:.1f}%)")

    targets = missing[:args.limit]
    log(f"[편향측정] CIK 오름차순 앞 {len(targets)}개를 채점한다(사후선택 방지)")

    skipped, candidates = {}, []
    for i, cik in enumerate(targets):
        name = uni[cik]["name"]
        try:
            series, lim = fetch_pit_series(cik, cik, t0, ua)   # 티커 대신 CIK 사용
            if series is None:
                skipped[cik] = lim
                continue
            candidates.append(build_candidate(cik, name, series))
        except Exception as e:  # noqa: BLE001
            skipped[cik] = [repr(e)]
        if (i + 1) % 100 == 0:
            log(f"  진행 {i+1}/{len(targets)} (후보 {len(candidates)}, "
                f"제외 {len(skipped)})")

    results = screen_all(candidates)
    passed = [r for r in results if r.passed]
    log(f"[편향측정] 채점 {len(results)} -> **저평가 판정 {len(passed)}**")

    rows = []
    for r in sorted(passed, key=lambda x: -x.expectation_gap_est):
        rows.append({
            "cik": r.candidate.ticker,
            "name": uni[r.candidate.ticker]["name"],
            "tier": r.tier,
            "expectation_gap_est": r.expectation_gap_est,
            "market_cap": r.candidate.market_cap,
            "out_of_validated_scope": out_of_scope_reasons(
                gap=r.expectation_gap_est, market_cap=r.candidate.market_cap),
        })

    out = {
        "generated_at": datetime.date.today().isoformat(),
        "as_of_t0": t0,
        "question": ("백테스트가 구조적으로 못 본 집단(오늘자 티커목록에 없는 "
                     "T0 공시기업)에서도 저평가 판정이 나오는가"),
        "t0_universe_size": len(uni),
        "invisible_to_backtest": len(missing),
        "invisible_share": len(missing) / len(uni),
        "sampled": len(targets),
        "scored": len(results),
        "passed": len(passed),
        "pass_rate_in_invisible_group": (len(passed) / len(results)
                                         if results else None),
        "skipped": len(skipped),
        "passed_detail": rows,
        "caveats": [
            "폐지 사유(파산 vs 피인수)를 구분할 수 없다 - LISTING_STATUS가 "
            "사유를 주지 않는다. 따라서 편향의 **방향**은 단정하지 않는다.",
            "이 집단의 주가 시계열은 확보 불가(폐지 종목)라 실현수익률은 "
            "여전히 측정할 수 없다 - 이 스크립트는 '빠진 판정의 개수'만 센다.",
            "자회사 채권 필자는 public_float 부재로 자동 제외된다(제외 사유 참고).",
        ],
    }
    os.makedirs(OUT_DIR, exist_ok=True)
    p = os.path.join(OUT_DIR, f"survivorship_bias_{t0}.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    log(f"[편향측정] 저장: {p}")

    if rows:
        log("\n=== 백테스트가 놓친 저평가 판정 상위 10 ===")
        for x in rows[:10]:
            log(f"  {x['name'][:36]:38} {x['tier']}  "
                f"Gap {x['expectation_gap_est']*100:+7.2f}%p  "
                f"${x['market_cap']/1e9:7.2f}B")


if __name__ == "__main__":
    main()
