"""
PHASE 1 — 신호 독립성 적대적 검증 (2026-08-21)

## 검증 대상 — 어제 내가 쓴 결론

RQ-002(2026-08-21)는 이렇게 결론냈다:

> **TCOM은 서로 독립인 두 축에서 동시에 유니버스를 이탈한다**
> (`realistic_growth` R-001 유니버스안정 57% · SBC 차감 A→B)

§6 Evidence Dependency Rule을 **내 자신의 결론에** 적용해 이것이 정말
독립 증거 2개인지 검증한다.

## 핵심 의심 — SBC와 RG는 같은 원자료를 공유한다

TCOM의 Realistic Growth는 `fcf_cagr` 경로로 결정된다(매출 가중평균보다 낮아
FCF CAGR이 채택됨). 그런데 RQ-002가 이미 측정했듯 **SBC를 성장경로에도
적용하면 그 FCF CAGR이 움직인다**(TCOM +2.33%p).

즉 현행 `sbc_cross_check`는 SBC를 **수준(fcf0)에만** 적용하므로:
  - fcf0 하락 -> Implied Growth 상승 -> Gap **하락**
  - 성장경로 미적용 -> RG 불변 -> 상승분 **반영 안 됨**

두 효과가 반대 방향이라면, 현행이 보고하는 "SBC 이탈"이 SBC의 경제적
효과인지 **적용 비대칭의 산물**인지 구분되지 않는다.

## 이 스크립트가 하는 일 / 하지 않는 일

**한다**: 각 종목에 네 시나리오를 계산해 신호가 어디서 오는지 분해한다.
  1. `base`                — 공식 값
  2. `sbc_level_only`      — SBC를 fcf0에만 (= RQ-002가 보고한 것)
  3. `sbc_consistent`      — SBC를 fcf0 **와** 성장경로 양쪽에
  4. `rg_low`              — RG를 기업 자신의 CAGR 최소값으로 (= R-001의 RG축)

**하지 않는다**: "SBC 일관 적용이 옳다"고 주장하지 않는다. 어느 쪽이 옳은지는
이 저장소가 판정할 근거가 없다(v3.23 원칙). 이건 **독립성 진단**이지 방법론
변경 제안이 아니다. `ledger/`에 쓰지 않고 공식 판정을 바꾸지 않는다.

## 계산은 전부 기존 엔진 함수로 한다

`realistic_growth_estimate` / `compare_implied_growth_models` /
`judgment_from_gap` / `judgment_grade_from_gap`을 그대로 부른다 — RG 재계산을
손으로 복제하면 두 계산이 미묘하게 어긋난다(Simplicity First가 반복 경고).

## 제외 규칙 (추측하지 않는다)

- `realistic_growth_override`를 쓴 종목: RG가 CAGR과 무관하므로 시나리오 3·4가
  정의되지 않는다(ROP).
- `capex_adjustment`를 탄 종목: RG 경로가 다르다.
- 기준연도/종료연도 SBC 미확보, 또는 차감 후 기준연도 FCF <= 0: 계산 불가.
  0으로 채우지 않고 사유와 함께 남긴다.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.expectation_gap_engine import (  # noqa: E402
    judgment_from_gap, judgment_grade_from_gap, realistic_growth_estimate,
)
from engine.pipeline import compare_implied_growth_models  # noqa: E402
from scripts.sbc_harvest_2026_08_21 import _load_ledgers, fetch_metrics  # noqa: E402

RETRIEVED_AT = "2026-08-21"
UNIVERSE_GRADES = ("S", "A")


def _sbc_adjusted_fcf_cagr(ticker, ledger):
    """
    기준연도·종료연도 양쪽에서 SBC를 차감한 FCF CAGR.

    ⚠️ 확보 못 하거나 차감 후 기준값이 0 이하면 **추측하지 않고** None + 사유.
    """
    dv = ledger["derived"]
    base = dv.get("cagr_5y_base_year")
    span = dv.get("cagr_5y_span") or 5
    if base is None:
        return None, "cagr_5y_base_year 필드 없음(v3.19판 ledger)"
    fcf_by = {int(k): v for k, v in dv["fcf_by_year"].items()}
    end = base + span
    if base not in fcf_by or end not in fcf_by:
        return None, f"fcf_by_year에 FY{base} 또는 FY{end} 없음"
    res = fetch_metrics(ticker, range(base - 1, end + 2))
    if res is None:
        return None, "SEC 조회 실패"
    sbc = {f.fiscal_year: f.value for f in res.facts if f.metric == "sbc"}
    missing = [y for y in (base, end) if y not in sbc]
    if missing:
        return None, f"SBC 미확보 연도 {missing}"
    b0, b1 = fcf_by[base] - sbc[base], fcf_by[end] - sbc[end]
    if b0 <= 0:
        return None, f"SBC 차감 후 기준연도 FCF <= 0 ({b0:,.0f}) - CAGR 정의불가"
    if b1 <= 0:
        return None, f"SBC 차감 후 종료연도 FCF <= 0 ({b1:,.0f})"
    return (b1 / b0) ** (1 / span) - 1, None


def _rg_with(ledger, fcf_cagr):
    """엔진의 RG 계산을 그대로 재사용. fcf_cagr만 갈아끼운다."""
    b = ledger["growth"]["breakdown"]
    ci = b["revenue_cagr_inputs"]
    rg, _ = realistic_growth_estimate(
        revenue_cagr_3y=ci.get("3y"), revenue_cagr_5y=ci.get("5y"),
        revenue_cagr_10y=ci.get("10y"), fcf_cagr_5y=fcf_cagr,
        structural_discount_pct=b["structural_discount_pct"],
        lynch_type=b["lynch_type"],
    )
    return rg


def _scenario(ledger, rg, fcf0):
    inp, dr = ledger["inputs"], ledger["discount_rate"]
    ig = compare_implied_growth_models(
        inp["market_cap"], fcf0, dr["r"], dr["n"], dr["g_terminal"]
    )[ledger["implied_growth"]["model_used"]]
    if ig is None:
        return None
    gap = rg - ig
    return {"realistic_growth": rg, "implied_growth": ig, "gap": gap,
            "judgment": judgment_from_gap(gap),
            "grade": judgment_grade_from_gap(gap)}


def analyse(ticker, ledger, sbc0):
    b = ledger["growth"]["breakdown"]
    skip = None
    if ledger["inputs"].get("realistic_growth_override") is not None:
        skip = "realistic_growth_override 사용 - RG가 CAGR과 무관"
    elif ledger["growth"].get("capex_adjustment"):
        skip = "capex_adjustment 경로 - RG 계산 경로가 다름"

    fcf0 = ledger["derived"]["fcf0"]
    out = {
        "ticker": ticker,
        "rg_driver": ("fcf_cagr" if b.get("fcf_conservatism_applied")
                      else "revenue_weighted"),
        "cap_applied": b.get("cap_applied"),
        "base": _scenario(ledger, ledger["growth"]["realistic_growth"], fcf0),
        "sbc_level_only": _scenario(
            ledger, ledger["growth"]["realistic_growth"], fcf0 - sbc0),
    }

    # R-001의 RG축(기업 자신의 CAGR 최소값)
    ci = [v for v in b["revenue_cagr_inputs"].values() if v is not None]
    lo = min(ci + ([ledger["derived"]["fcf_cagr_5y"]]
                   if ledger["derived"].get("fcf_cagr_5y") is not None else []))
    out["rg_low"] = _scenario(ledger, _rg_with(ledger, lo), fcf0) if not skip else None

    if skip:
        out["sbc_consistent"] = None
        out["sbc_consistent_blocked"] = skip
        return out

    cagr_sbc, why = _sbc_adjusted_fcf_cagr(ticker, ledger)
    if cagr_sbc is None:
        out["sbc_consistent"] = None
        out["sbc_consistent_blocked"] = why
        return out
    out["fcf_cagr_base"] = ledger["derived"].get("fcf_cagr_5y")
    out["fcf_cagr_sbc_adjusted"] = cagr_sbc
    out["sbc_consistent"] = _scenario(ledger, _rg_with(ledger, cagr_sbc), fcf0 - sbc0)
    return out


def verdict(row):
    """
    SBC 신호가 **일관 적용 후에도** 유니버스 이탈을 만드는가.

    - SURVIVES  : 부분 적용에서도, 일관 적용에서도 이탈 -> SBC 고유 신호
    - CANCELLED : 부분 적용에서만 이탈 -> 적용 비대칭의 산물
    - NO_SIGNAL : 애초에 이탈 안 함
    - UNKNOWN   : 일관 적용을 계산하지 못함 (**무해가 아니라 미확인**)
    """
    base, lvl, cons = row["base"], row["sbc_level_only"], row["sbc_consistent"]
    if not base or base["grade"] not in UNIVERSE_GRADES:
        return "NOT_IN_UNIVERSE"
    leaves_partial = lvl and lvl["grade"] not in UNIVERSE_GRADES
    if not leaves_partial:
        return "NO_SIGNAL"
    if cons is None:
        return "UNKNOWN"
    return "SURVIVES" if cons["grade"] not in UNIVERSE_GRADES else "CANCELLED"


def main():
    ledgers = _load_ledgers()
    sbc = {r["ticker"]: r for r in json.load(
        open(f"reports/sbc_harvest_{RETRIEVED_AT}.json", encoding="utf-8")
    )["results"] if r.get("status") == "OK"}
    buy = {r["ticker"]: r["weight_final"] for r in json.load(
        open("reports/buylist_2026-08-03.json", encoding="utf-8"))}

    rows = []
    for t, (_fn, d) in sorted(ledgers.items()):
        if t not in sbc:
            continue
        row = analyse(t, d, sbc[t]["sbc0"])
        row["weight_final"] = buy.get(t)
        row["verdict"] = verdict(row)
        rows.append(row)

    def pct(s, k="gap"):
        return f"{s[k] * 100:+7.2f}" if s else "      -"

    def gr(s):
        return s["grade"] if s else "-"

    print("SBC 신호 분해 — 부분 적용(fcf0만) vs 일관 적용(fcf0+성장경로)\n")
    hdr = (f"{'종목':6} {'비중':>6} {'base':>8}{'':2} {'부분':>8}{'':2} "
           f"{'일관':>8}{'':2} {'RGlow':>8}{'':2} {'판정':10}")
    print(hdr)
    print("-" * len(hdr))
    for r in sorted(rows, key=lambda x: -(x["weight_final"] or 0)):
        w = f"{r['weight_final'] * 100:5.2f}%" if r["weight_final"] else "    - "
        print(f"{r['ticker']:6} {w:>6} "
              f"{pct(r['base'])} {gr(r['base']):1} "
              f"{pct(r['sbc_level_only'])} {gr(r['sbc_level_only']):1} "
              f"{pct(r['sbc_consistent'])} {gr(r['sbc_consistent']):1} "
              f"{pct(r['rg_low'])} {gr(r['rg_low']):1} {r['verdict']}")

    blocked = [(r["ticker"], r.get("sbc_consistent_blocked")) for r in rows
               if r["sbc_consistent"] is None]
    if blocked:
        print("\n일관 적용을 계산하지 못한 종목 ('무해'가 아니라 '미확인'):")
        for t, why in blocked:
            print(f"  {t:6} {why}")

    out = {
        "generated_at": RETRIEVED_AT,
        "phase": "PHASE 1 — signal independence adversarial case study",
        "affects_official_judgment": False,
        "question": ("RQ-002가 보고한 'SBC 축 유니버스 이탈'이 SBC의 경제적 "
                     "효과인가, 아니면 SBC를 수준에만 적용하고 성장경로에는 "
                     "적용하지 않는 비대칭의 산물인가"),
        "not_a_methodology_proposal": (
            "SBC 일관 적용이 옳다고 주장하지 않는다. 어느 쪽이 옳은지 판정할 "
            "근거가 이 저장소에 없다(v3.23 원칙). 독립성 진단일 뿐이다."
        ),
        "results": rows,
    }
    os.makedirs("reports", exist_ok=True)
    path = f"reports/signal_independence_{RETRIEVED_AT}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"\n저장: {path}")

    from collections import Counter
    print("판정 분포:", dict(Counter(r["verdict"] for r in rows)))


if __name__ == "__main__":
    main()
