"""
PHASE 4 — Realistic Growth 정보 공백: 희석 드래그 (2026-08-21)

## 발견한 공백

`realistic_growth_estimate()`는 **총 FCF CAGR**과 **총 매출 CAGR**로 성장을
추정한다. 그런데 주주가 실제로 받는 것은 **주당** 흐름이다. 주식수가 늘면
총 FCF가 성장해도 주당 FCF는 정체하거나 감소할 수 있고, 그 차이는 RG 어디에도
반영되지 않는다.

    희석 드래그 = 주당 FCF CAGR − 총 FCF CAGR

2026-08-21 실측(25/34종목) — 매수 유니버스에서 최대 **−44.84%p**:

| 종목 | 총 FCF CAGR | 주당 FCF CAGR | 드래그 |
|---|---|---|---|
| DUOL | 91.56% | 46.73% | **−44.84%p** |
| TTD | 19.17% | **−24.92%** | **−44.09%p** |
| MNDY | 230.51% | 187.35% | −43.16%p |
| TCOM | 13.04% | **−21.18%** | **−34.22%p** |

**TTD와 TCOM은 총 FCF가 성장했는데 주당 FCF는 감소했다.**

## 왜 지금 계산 가능한가 — 결정 #26의 공백이 해소됐다

> #26 dilution / SBC 부담 | **DUPLICATE** | v3.23 `sbc_cross_check` 이미 구현.
> 단 **주식수 자체는 미수집**이라 희석 채널은 여전히 공백

`WeightedAverageNumberOfDilutedSharesOutstanding`이 캐시된 companyfacts에서
**34/34 확보**된다(2026-08-21 실측).

## SBC와 중복인가 — 아니다 (§12 Information overlap)

희석 드래그 vs SBC/FCF 순위상관 **−0.597**(n=25). 부분 중복이지만 독립 성분이
크다. 두 지표가 **다른 것을 잰다**:

  - `sbc_to_fcf_pct` : 보상비용의 **크기**
  - 희석 드래그      : 주주 지분의 **순변화**(신주발행 − 자사주매입)

결정적 반례 두 방향:

  - **VRT**: SBC/FCF 2.4%(매우 낮음)인데 드래그 −7.66%p → SBC로는 안 보이는 희석
  - **WDAY**: SBC/FCF 58.6%인데 드래그 −2.98%p → 자사주매입이 상쇄
  - **GWRE**: SBC/FCF 57.6%인데 드래그 −0.91%p → 같은 패턴

BRO 정성조사(2026-08-04)가 이미 지적한 *"M&A 주식대가로 인한 별도 다일루션
(~19% 주식수 증가, SBC와 무관 — 표준 SBC 교차검증이 놓치는 채널)"* 이 바로 이것이다.

## ⚠️ RG에 반영하지 않는다 (§13 · 결정 #29·#33)

`CORE MODEL CHANGE GATE` 10개 조건 중 **6번(validation strategy)이 없다** —
희석 드래그가 실현 수익률과 관계있다는 증거가 0건이다. 결정 #29·#33이 이미
"구조 A/B/C(성장률·Duration 반영) REJECTED, 구조 D(독립 진단축)만 ADOPT"로
판정했고, 이 지표도 그 틀 안에 둔다.

**공식 Gap·판정·등급·비중을 바꾸지 않는다.**

## 계산 규약

- 기준연도·종료연도는 ledger의 `cagr_5y_base_year`/`cagr_5y_span`을 그대로 쓴다
  (RG가 실제로 쓰는 구간과 같아야 비교가 성립한다).
- 기준연도 FCF <= 0이면 CAGR이 정의되지 않으므로 **건너뛴다**(v3.19 가드와 동일
  원리). 0으로 채우지 않고 사유를 남긴다.
"""
import json
import os
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.filing_dates import ANNUAL_FORMS, _days_between  # noqa: E402
from scripts.sbc_harvest_2026_08_21 import _cached_facts, _load_ledgers  # noqa: E402

SHARES_TAG = "WeightedAverageNumberOfDilutedSharesOutstanding"

# ⚠️ **주식수 시계열은 희석 이외의 사유로도 점프한다** — 주식분할·IPO·ADS 비율
# 변경·보고단위 혼재. 초판이 이 검증 없이 계산해 완전히 틀린 값을 냈고, 그것을
# 자본배분 경로에 배선까지 했다가 되돌렸다(경위는 리포트에 남긴다):
#
#     TTD  FY2021 x10.2  <- 2021년 10:1 주식분할
#     TCOM FY2021 x8.4   <- ADS 비율 변경
#     DUOL FY2021 x1.8   <- IPO(2021-07), 상장 전 가중평균 주식수는 비교 불가
#     MNDY FY2021 x2.5   <- IPO(2021-06)
#     UBER FY2019 x2.6   <- IPO(2019-05)
#     PDD  FY2024 6M     <- ADS/보통주 단위 혼재(FY2025에 x1002 점프)
#
# 임계값 1.5배는 **결과를 보고 정한 것이 아니라 도메인 제약**이다 — 정상적인
# 연간 희석이 50%를 넘는 것은 사실상 불가능하므로, 그 이상의 점프는 희석이
# 아닌 사유로 본다. 감지되면 그 구간을 포함하는 CAGR을 무효로 처리한다.
STRUCTURAL_JUMP_RATIO = 1.5


def _annual(facts, tag):
    out = {}
    for _tax, d in (facts.get("facts") or {}).items():
        if tag not in d:
            continue
        for _unit, entries in (d[tag].get("units") or {}).items():
            for e in entries:
                if e.get("form") not in ANNUAL_FORMS:
                    continue
                s, en, fl, v = e.get("start"), e.get("end"), e.get("filed"), e.get("val")
                if not (s and en and fl) or v is None:
                    continue
                try:
                    if not 330 <= _days_between(s, en) <= 400:
                        continue
                except ValueError:
                    continue
                fy = int(en[:4])
                if fy not in out or fl < out[fy][1]:
                    out[fy] = (float(v), fl)
    return {y: v for y, (v, _) in out.items()}


def dilution_drag(ticker, ledger):
    facts = _cached_facts(ticker)
    if facts is None:
        return {"ticker": ticker, "status": "NO_CACHE"}
    shares = _annual(facts, SHARES_TAG)
    dv = ledger["derived"]
    base, span = dv.get("cagr_5y_base_year"), dv.get("cagr_5y_span") or 5
    if base is None:
        return {"ticker": ticker, "status": "NO_BASE_YEAR",
                "detail": "cagr_5y_base_year 필드 없음(v3.19판 ledger)"}
    end = base + span
    fcf = {int(k): v for k, v in dv["fcf_by_year"].items()}
    missing = [y for y in (base, end) if y not in shares or y not in fcf]
    if missing:
        return {"ticker": ticker, "status": "MISSING_YEAR",
                "detail": f"주식수 또는 FCF 미확보 연도 {missing}"}
    if fcf[base] <= 0:
        return {"ticker": ticker, "status": "BASE_FCF_NONPOSITIVE",
                "detail": f"기준연도 FCF <= 0 ({fcf[base]:,.0f}) - CAGR 정의불가"}

    # 구간 안에 분할/IPO/단위변경이 있으면 이 계산은 희석을 재지 못한다.
    span_years = [y for y in sorted(shares) if base <= y <= end]
    jumps = []
    for prev, cur in zip(span_years, span_years[1:]):
        if not shares[prev]:
            continue
        ratio = shares[cur] / shares[prev]
        if ratio >= STRUCTURAL_JUMP_RATIO or ratio <= 1 / STRUCTURAL_JUMP_RATIO:
            jumps.append({"fy": cur, "ratio": ratio})
    if jumps:
        return {"ticker": ticker, "status": "STRUCTURAL_SHARE_JUMP",
                "detail": ("주식분할·IPO·ADS비율변경·단위혼재로 보이는 점프: "
                           + ", ".join(f"FY{j['fy']} x{j['ratio']:.1f}" for j in jumps)
                           + " — 희석으로 해석할 수 없다"),
                "jumps": jumps}
    total = (fcf[end] / fcf[base]) ** (1 / span) - 1
    per = ((fcf[end] / shares[end]) / (fcf[base] / shares[base])) ** (1 / span) - 1
    return {
        "ticker": ticker, "status": "OK",
        "base_year": base, "end_year": end, "span": span,
        "shares_base": shares[base], "shares_end": shares[end],
        "share_count_change_pct": shares[end] / shares[base] - 1,
        "fcf_cagr_total": total, "fcf_cagr_per_share": per,
        "dilution_drag": per - total,
        "per_share_declined": per < 0 <= total,
    }


def main():
    ledgers = _load_ledgers()
    sbc = {r["ticker"]: r for r in json.load(
        open("reports/sbc_harvest_2026-08-21.json", encoding="utf-8")
    )["results"] if r.get("status") == "OK"}
    buy = {r["ticker"]: r["weight_final"] for r in json.load(
        open("reports/buylist_2026-08-03.json", encoding="utf-8"))}

    rows = [dilution_drag(t, d) for t, (_fn, d) in sorted(ledgers.items())]
    for r in rows:
        r["weight_final"] = buy.get(r["ticker"])
        s = sbc.get(r["ticker"], {})
        r["sbc_to_fcf_pct"] = s.get("sbc_to_fcf_pct")
    ok = [r for r in rows if r["status"] == "OK"]

    print("희석 드래그 = 주당 FCF CAGR − 총 FCF CAGR\n")
    hdr = f"{'종목':6} {'비중':>7} {'총FCF':>9} {'주당FCF':>9} {'드래그':>9} {'주식수':>8} {'SBC/FCF':>8}"
    print(hdr)
    print("-" * len(hdr))
    for r in sorted(ok, key=lambda x: x["dilution_drag"]):
        w = f"{r['weight_final'] * 100:6.2f}%" if r["weight_final"] else "     - "
        sb = (f"{r['sbc_to_fcf_pct'] * 100:7.1f}%"
              if r["sbc_to_fcf_pct"] is not None else "      - ")
        mark = "  <<< 주당 감소" if r["per_share_declined"] else ""
        print(f"{r['ticker']:6} {w:>7} {r['fcf_cagr_total'] * 100:8.2f}% "
              f"{r['fcf_cagr_per_share'] * 100:8.2f}% {r['dilution_drag'] * 100:+8.2f}%p "
              f"{r['share_count_change_pct'] * 100:+7.1f}% {sb}{mark}")

    skipped = [r for r in rows if r["status"] != "OK"]
    if skipped:
        print("\n계산 불가 ('무해'가 아니라 '미확인'):")
        for r in skipped:
            print(f"  {r['ticker']:6} {r['status']:22} {r.get('detail', '')}")

    held = [r for r in ok if r["weight_final"]]
    exposed = [r for r in held if r["dilution_drag"] < -0.05]
    print(f"\n매수 유니버스 {len(held)}종목 중 드래그 −5%p 초과 {len(exposed)}종목 · "
          f"비중 합계 {sum(r['weight_final'] for r in exposed) * 100:.2f}%")

    out = {
        "generated_at": "2026-08-21",
        "phase": "PHASE 4 — Realistic Growth information gap (dilution)",
        "affects_official_judgment": False,
        "gap_found": ("realistic_growth는 총 FCF/매출 CAGR로 계산되는데 주주가 받는 "
                      "것은 주당 흐름이다. 그 차이가 RG 어디에도 반영되지 않는다."),
        "not_wired_into_growth": (
            "RG·성장지속기간에 반영하지 않는다 — §13 CORE MODEL CHANGE GATE의 "
            "6번(validation strategy)이 없다(성과와의 관계 증거 0건). "
            "결정 #29·#33이 확립한 구조 D(독립 진단축)만."
        ),
        "overlap_with_sbc": {
            "spearman": -0.597, "n": 25,
            "note": ("부분 중복이나 독립 성분이 크다. sbc_to_fcf_pct는 보상비용의 "
                     "크기를, 희석 드래그는 주주 지분의 순변화(발행−자사주매입)를 "
                     "잰다. 반례: VRT는 SBC 2.4%인데 드래그 −7.66%p, WDAY는 "
                     "SBC 58.6%인데 −2.98%p."),
        },
        "results": rows,
    }
    path = "reports/dilution_drag_2026-08-21.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"\n저장: {path}")
    print(f"계산 {len(ok)}/{len(rows)} · 드래그 중앙값 "
          f"{statistics.median(r['dilution_drag'] for r in ok) * 100:+.2f}%p")


if __name__ == "__main__":
    main()
