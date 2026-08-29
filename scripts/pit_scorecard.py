"""
pit_scorecard.py (2026-08-29) — PIT 백테스트 성적표를 읽는다.

`pit_price_validation.py`가 만든 실현 수익률을 flagged/not_flagged로 나눠
비교한다. **새 통계 방법론을 만들지 않는다** - 중앙값·평균·승률·벤치마크
초과 비율 같은 서술통계와, 분포를 그대로 드러내는 분위수만 낸다.

## 왜 p-value를 내지 않는가

이 저장소는 `engine/quant/validation.py`에서 이미 **같은 34종목을 9,702회
검정했고 기대 위양성이 485건**이라는 사실을 스스로 측정해뒀다(FWER 1.0으로
포화). 여기에 또 하나의 nominal p-value를 더하면 그 문제를 키울 뿐이다.
게다가 이 표본은 **단일 T0·단일 기간**이라 독립 관측이 아니다(같은 5년
시장 국면을 128종목이 공유한다) - p-value의 전제가 성립하지 않는다.

대신 정직하게 읽을 수 있는 것만 낸다:
  - 두 그룹의 수익률 분포(중앙값·평균·사분위)
  - 벤치마크(SPY) 대비 초과 비율
  - **동일가중 포트폴리오 수익률** - "flagged를 전부 같은 금액씩 샀다면"

## ⚠️ 이 성적표가 증명하지 못하는 것

1. **단일 기간·단일 T0.** 2021-06~2026-08은 특정 시장 국면 하나다. 다른
   T0에서 재현되는지는 이 결과로 알 수 없다.
2. **생존편향.** T0 이후 상장폐지·피인수된 종목은 가격 시계열이 끊겨
   `unavailable`로 빠진다 - 그 종목들이 대체로 나빴다면 두 그룹 모두
   실제보다 좋아 보인다. 확보 실패 건수를 반드시 함께 볼 것.
3. **유니버스 앞부분 300종목.** SEC 티커 목록 순서라 성과와 무관하지만,
   시가총액 큰 종목이 앞에 몰려 있어 대형주 편중이다.
4. **거래비용·세금 미반영.**
"""
import json
import os
import statistics
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_HERE))

from engine.after_cost import portfolio_after_cost  # noqa: E402


def quantiles(xs):
    xs = sorted(xs)
    if not xs:
        return {}
    def q(p):
        if len(xs) == 1:
            return xs[0]
        i = p * (len(xs) - 1)
        lo, hi = int(i), min(int(i) + 1, len(xs) - 1)
        return xs[lo] + (xs[hi] - xs[lo]) * (i - lo)
    return {"min": xs[0], "p25": q(0.25), "median": q(0.5),
            "p75": q(0.75), "max": xs[-1]}


def summarize(rows, bench_ret=None):
    rets = [r["return_pct"] for r in rows]
    if not rets:
        return {"n": 0}
    out = {
        "n": len(rets),
        "mean_pct": statistics.fmean(rets),
        "equal_weight_portfolio_pct": statistics.fmean(rets),
        **{k + "_pct": v for k, v in quantiles(rets).items()},
        "positive_rate": sum(1 for x in rets if x > 0) / len(rets),
    }
    if bench_ret is not None:
        out["beat_benchmark_rate"] = sum(1 for x in rets if x > bench_ret) / len(rets)

    # ⚠️ 집중도 강건성 - "소수 종목이 전체 결과를 만들었는가"에 답한다.
    # 2021-06-30 T0 실측에서 이게 결정적이었다: 동일가중 +283%가 대단해 보이지만
    # 상위 몇 종목을 빼면 급격히 무너진다. **평균만 보면 반드시 오독한다.**
    # 섹터 분류를 코드에 하드코딩하지 않는 이유는 이 프로젝트가 근거 없는
    # 분류체계를 상수로 박지 않기 때문이다(P/B 임계값·Lynch 캡과 동일 판단) -
    # 대신 분류에 의존하지 않는 일반 지표로 집중도를 드러낸다.
    s = sorted(rets, reverse=True)
    out["concentration"] = {
        f"mean_excl_top{k}_pct": (statistics.fmean(s[k:]) if len(s) > k else None)
        for k in (1, 3, 5)
    }
    total = sum(x for x in rets if x > 0)
    if total > 0:
        out["concentration"]["top3_share_of_positive_sum"] = sum(s[:3]) / total
    return out


def build(path):
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    bench = d.get("benchmark") or {}
    bench_ret = bench.get("return_pct")

    flagged = summarize(d["flagged"], bench_ret)
    not_flagged = summarize(d["not_flagged"], bench_ret)

    lines = [
        f"# PIT 백테스트 성적표 — T0={d['as_of_t0']} → {d.get('validated_at')}",
        "",
        f"가격 출처: {d['price_source']}",
        f"수익률 정의: {d['return_definition']}",
        "",
    ]
    if bench_ret is not None:
        lines.append(f"**벤치마크 {bench['ticker']}: {bench_ret:+.1f}%**")
        lines.append("")

    lines += [
        "| | flagged(저평가 판정) | not flagged |",
        "|---|---:|---:|",
        f"| 종목수 | {flagged.get('n', 0)} | {not_flagged.get('n', 0)} |",
    ]
    for key, label in [("equal_weight_portfolio_pct", "동일가중 포트폴리오"),
                       ("median_pct", "중앙값"),
                       ("p25_pct", "1사분위"), ("p75_pct", "3사분위"),
                       ("min_pct", "최저"), ("max_pct", "최고")]:
        a = flagged.get(key)
        b = not_flagged.get(key)
        if a is None or b is None:
            continue
        lines.append(f"| {label} | {a:+.1f}% | {b:+.1f}% |")
    for key, label in [("positive_rate", "플러스 비율"),
                       ("beat_benchmark_rate", "벤치마크 초과 비율")]:
        a, b = flagged.get(key), not_flagged.get(key)
        if a is None or b is None:
            continue
        lines.append(f"| {label} | {a * 100:.0f}% | {b * 100:.0f}% |")

    # 집중도 - 평균만 보면 오독한다
    lines += ["", "**집중도(소수 종목이 결과를 만들었는가)**", "",
              "| | flagged | not flagged |", "|---|---:|---:|"]
    for k in (1, 3, 5):
        key = f"mean_excl_top{k}_pct"
        a = (flagged.get("concentration") or {}).get(key)
        b = (not_flagged.get("concentration") or {}).get(key)
        if a is None or b is None:
            continue
        lines.append(f"| 상위 {k}종목 제외 평균 | {a:+.1f}% | {b:+.1f}% |")

    # 세후 - 양도세는 이익에만 붙는 비대칭 비용이라 격차를 반드시 좁힌다.
    # 총수익으로만 읽으면 우위를 과대평가한다.
    fl_net = portfolio_after_cost([r["return_pct"] for r in d["flagged"]])
    nf_net = portfolio_after_cost([r["return_pct"] for r in d["not_flagged"]])
    if fl_net is not None and nf_net is not None:
        gross_gap = (flagged["equal_weight_portfolio_pct"]
                     - not_flagged["equal_weight_portfolio_pct"])
        lines += ["", "**세후·비용후(한국 투자자 기준, 원금 1,000만원 동일가중)**", "",
                  "| | flagged | not flagged |", "|---|---:|---:|",
                  f"| 총수익 | {flagged['equal_weight_portfolio_pct']:+.1f}% "
                  f"| {not_flagged['equal_weight_portfolio_pct']:+.1f}% |",
                  f"| 세후 | {fl_net:+.1f}% | {nf_net:+.1f}% |",
                  "",
                  f"격차 {gross_gap:+.1f}%p → 세후 {fl_net - nf_net:+.1f}%p "
                  f"(양도세 22%가 이익에만 붙어 격차를 좁힌다)",
                  "",
                  "⚠️ 양도세율·기본공제는 법정값이지만 환전 스프레드(0.2%)·"
                  "수수료(0.2%)는 **실측이 아닌 가정**이다. 배당소득세·개인별 "
                  "다른 소득·연도 분할 매도는 미반영 — 세무 자문이 아니다."]

    n_un = d["n_unavailable"]
    if n_un:
        lines += ["", f"⚠️ 확보 실패(상장폐지·피인수 등): **{n_un}종목** — 그 종목들이 "
                      f"대체로 나빴다면 두 그룹 모두 실제보다 좋아 보인다(생존편향)."]
    else:
        lines += ["", "확보 실패 **0종목** — 이 표본에서는 상장폐지·피인수로 인한 "
                      "생존편향이 발생하지 않았다(다만 T0 유니버스 자체가 "
                      "대형주 편중이라는 별개 한계는 그대로다)."]
    return {"flagged": flagged, "not_flagged": not_flagged,
            "benchmark": bench, "n_unavailable": d["n_unavailable"]}, "\n".join(lines)


def main():
    import argparse
    ap = argparse.ArgumentParser(description="PIT 성적표")
    ap.add_argument("--returns", required=True)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    summary, text = build(args.returns)
    print(text)
    if args.out:
        os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
