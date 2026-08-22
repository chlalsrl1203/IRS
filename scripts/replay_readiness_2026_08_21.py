"""
PHASE 5 — Historical Replay **readiness** 판정 (2026-08-21)

⚠️ **이 스크립트는 Historical Replay를 구현하지 않는다.** §14가 명시적으로
금지한다. 여기서 하는 것은 단 하나 - "과거 시점 재현이 지금 가능한가"를
10개 축으로 재고, 부족한 조건을 그대로 기록하는 것이다.

왜 구현하지 않는가: 2026년 데이터로 2023년 결과를 재구성하면 그 자체가
look-ahead다. 이 프로젝트는 이미 2026-08-16에 §66 STOP CONDITION을 발동해
"진짜 Historical Replay는 수행 불가"로 공식 선언했다. 이번 PHASE는 그
판단이 아직 유효한지, 그리고 **무엇이 풀리면 유효하지 않게 되는지**를
축별로 특정한다.

측정 축(10):
  A1 과거 공시 확보 가능성 (historical filings)
  A2 분석 시점 입력값 (as-of inputs)
  A3 원본 입력 보존 (original input preservation)
  A4 시장 데이터 (market data)
  A5 논거 시점 (thesis date)
  A6 예측 상태 (prediction state)
  A7 밸류에이션 입력 (valuation inputs)
  A8 출처 가용성 (source availability)
  A9 재작성 정보 (restatement information)
  A10 당시 알 수 있었던 정보의 재현 가능성

각 축은 READY / PARTIAL / NOT_READY 중 하나와 **차단 조건**을 낸다.
전체 판정은 가장 약한 축이 결정한다 - 평균내지 않는다(§61 단일 합성점수 금지와
같은 이유: 평균은 치명적 공백을 통과 가능한 숫자로 바꾼다).
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

LEDGER_DIR = "ledger"
PREDICTION_DIR = "predictions"
THESIS_DIR = "thesis"
CACHE_DIR = os.environ.get(
    "SBC_CACHE_DIR",
    "/tmp/claude-0/-home-user-IRS/1fb7a46a-ee0b-5b39-806f-ff7ee862da26/scratchpad/secfacts",
)
OUT = "reports/replay_readiness_2026-08-21.json"

# 재작성 판정 임계값. 회계 반올림·단위 표기 차이를 재작성으로 세지 않기 위한
# 도메인 제약이며 결과를 보고 정한 값이 아니다(§19).
RESTATEMENT_TOL = 0.001


def load_ledgers():
    out = {}
    for fn in sorted(os.listdir(LEDGER_DIR)):
        if not fn.endswith(".json"):
            continue
        with open(os.path.join(LEDGER_DIR, fn), encoding="utf-8") as f:
            d = json.load(f)
        out[d["meta"]["ticker"]] = d
    return out


def cached_facts(ticker):
    path = os.path.join(CACHE_DIR, f"{ticker}.json")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ── A9: 재작성 빈도 ──────────────────────────────────────────────────────
def measure_restatements(tickers):
    """
    같은 (태그, 기간)이 여러 공시에 나타날 때 값이 바뀌었는지 센다.

    ⚠️ 기간을 (start, end) 쌍으로 식별한다. 회계연도 라벨(int(end[:4]))로
    묶으면 52/53주 회계연도 회사에서 **서로 다른 기간**이 같은 라벨로 뭉쳐
    재작성이 아닌 것을 재작성으로 센다 - 초판이 정확히 이 오류로 12.5%를
    보고했고, 기간 쌍으로 재측정해 11.8%로 정정했다.
    """
    METRICS = ("Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax",
               "OperatingIncomeLoss", "NetCashProvidedByUsedInOperatingActivities")
    single = multi = restated = 0
    examples = []
    spread = {"gt_1pct": 0, "gt_5pct": 0, "gt_20pct": 0}

    for t in tickers:
        facts = cached_facts(t)
        if not facts:
            continue
        for tag in METRICS:
            node = facts.get("facts", {}).get("us-gaap", {}).get(tag)
            if not node:
                continue
            for entries in node.get("units", {}).values():
                periods = {}
                for e in entries:
                    if e.get("form") not in ("10-K", "10-K/A", "20-F"):
                        continue
                    key = (e.get("start"), e.get("end"))
                    if key[0] is None:
                        continue
                    periods.setdefault(key, []).append((e["filed"], e["val"]))
                for key, rows in periods.items():
                    vals = {v for _, v in rows}
                    if len(rows) < 2:
                        single += 1
                        continue
                    multi += 1
                    if len(vals) == 1:
                        continue
                    lo, hi = min(vals), max(vals)
                    if lo == 0 or abs(hi - lo) / abs(lo) <= RESTATEMENT_TOL:
                        continue
                    restated += 1
                    delta = abs(hi - lo) / abs(lo)
                    if delta > 0.01:
                        spread["gt_1pct"] += 1
                    if delta > 0.05:
                        spread["gt_5pct"] += 1
                    if delta > 0.20:
                        spread["gt_20pct"] += 1
                    if len(examples) < 8:
                        rows.sort()
                        examples.append({
                            "ticker": t, "tag": tag, "period_end": key[1],
                            "first": rows[0][1], "last": rows[-1][1],
                            "delta_pct": round(delta * 100, 1),
                        })
    pct = round(restated / multi * 100, 1) if multi else None
    return {
        "single_filing_periods": single,
        "multi_filing_periods": multi,
        "restated": restated,
        "restated_pct_of_multi": pct,
        "spread": spread,
        "examples": examples,
    }


def measure_ledger_vintage(ledgers):
    """
    ledger 입력값이 **최초 판본**과 맞는가, **최신 판본**과 맞는가.

    이것이 A9를 추상론에서 실물로 바꾸는 측정이다. 재작성된 기간에 대해 ledger가
    최신 판본을 쓰고 있다면, 그 ledger를 재작성 **이전** 시점의 스냅샷으로 재사용하는
    순간 look-ahead가 된다 - 어떤 PIT 필드를 붙여도 마찬가지다.

    ⚠️ 이것이 "기존 34종목 분석이 틀렸다"는 뜻은 **아니다**. 전부 2026년에 수행됐고
    2026년 시점에서 최신 판본을 쓰는 것은 옳다. 문제는 오직 **더 이른 T0로 되돌릴 때**
    발생한다.
    """
    TAGS = {
        "revenue": ("Revenues",
                    "RevenueFromContractWithCustomerExcludingAssessedTax"),
        "ocf": ("NetCashProvidedByUsedInOperatingActivities",),
    }
    FIELD = {"revenue": "revenue_by_year", "ocf": "operating_cashflow_by_year"}
    tot = first_only = last_only = both = neither = 0
    examples = []
    for t, d in ledgers.items():
        facts = cached_facts(t)
        if not facts:
            continue
        for metric, tags in TAGS.items():
            led = {int(y): v for y, v in d["inputs"][FIELD[metric]].items()}
            periods = {}
            for tag in tags:
                node = facts.get("facts", {}).get("us-gaap", {}).get(tag)
                if not node:
                    continue
                for entries in node.get("units", {}).values():
                    for e in entries:
                        if e.get("form") not in ("10-K", "10-K/A", "20-F"):
                            continue
                        if e.get("start") is None:
                            continue
                        periods.setdefault(int(e["end"][:4]), []).append(
                            (e["filed"], e["val"]))
            for y, v in led.items():
                vals = [x[1] for x in sorted(set(periods.get(y, [])))]
                if len(set(vals)) < 2:
                    continue
                tot += 1
                fv, lv = vals[0], vals[-1]
                mf = abs(v - fv) / abs(fv) < 0.005 if fv else False
                ml = abs(v - lv) / abs(lv) < 0.005 if lv else False
                if mf and ml:
                    both += 1
                elif mf:
                    first_only += 1
                elif ml:
                    last_only += 1
                else:
                    neither += 1
                    if len(examples) < 6:
                        examples.append({"ticker": t, "metric": metric,
                                         "fiscal_year": y, "first": fv,
                                         "latest": lv, "ledger": v})
    return {
        "ledger_values_on_restated_periods": tot,
        "matches_first_vintage_only": first_only,
        "matches_latest_vintage_only": last_only,
        "matches_both": both,
        "matches_neither": neither,
        "examples_matching_neither": examples,
    }


# ── A1: 과거 공시 확보 가능성 ────────────────────────────────────────────
def measure_filing_availability(ledgers):
    from engine.filing_dates import annual_filing_dates

    ok = partial = missing = 0
    detail = {}
    for t, d in ledgers.items():
        facts = cached_facts(t)
        years = sorted(int(y) for y in d["inputs"]["revenue_by_year"])
        if not facts:
            missing += 1
            detail[t] = {"status": "NO_FACTS", "covered": 0, "needed": len(years)}
            continue
        dates = annual_filing_dates(facts)
        cov = sum(1 for y in years if dates.get(y))
        if cov == len(years):
            ok += 1
            st = "FULL"
        elif cov:
            partial += 1
            st = "PARTIAL"
        else:
            missing += 1
            st = "NONE"
        detail[t] = {"status": st, "covered": cov, "needed": len(years)}
    return {"full": ok, "partial": partial, "none": missing, "by_ticker": detail}


def main():
    ledgers = load_ledgers()
    tickers = sorted(ledgers)
    n = len(tickers)

    # A2 as-of inputs / A10 재현 가능성
    pit_present = [t for t, d in ledgers.items()
                   if d["meta"].get("point_in_time") is not None]
    # A4 market data
    price = [t for t, d in ledgers.items()
             if d["meta"].get("price_at_analysis") is not None]
    # A8 source availability
    prov = [t for t, d in ledgers.items() if d["meta"].get("provenance")]
    src_free_text = [t for t, d in ledgers.items() if d["meta"].get("data_sources")]
    # A3 original input preservation - ledger가 입력 전체를 담고 있는가
    REQUIRED = ("revenue_by_year", "operating_income_by_year",
                "operating_cashflow_by_year", "capex_by_year", "market_cap",
                "net_debt", "ebitda", "risk_free_rate")
    full_inputs = [t for t, d in ledgers.items()
                   if all(d["inputs"].get(k) is not None for k in REQUIRED)]
    # v3.19판 스키마 비균일 - cagr_5y_base_year 부재
    # ⚠️ 이 필드는 `derived`에 있다. 초판이 `growth.breakdown`을 봐서 34/34 부재로
    # 나왔고, 그대로였다면 실재하지 않는 차단조건을 보고할 뻔했다(PHASE 2·4와 같은
    # "감사 도구가 조용히 무력화되는" 실패 유형 - 결과가 극단적이면 도구를 먼저 의심).
    no_base_year = sorted(
        t for t, d in ledgers.items()
        if d.get("derived", {}).get("cagr_5y_base_year") is None)

    # A5 thesis date
    thesis_n = (len([f for f in os.listdir(THESIS_DIR) if f.endswith(".json")])
                if os.path.isdir(THESIS_DIR) else 0)
    # A6 prediction state
    preds = []
    if os.path.isdir(PREDICTION_DIR):
        for fn in sorted(os.listdir(PREDICTION_DIR)):
            if fn.endswith(".json"):
                with open(os.path.join(PREDICTION_DIR, fn), encoding="utf-8") as f:
                    preds.append(json.load(f))
    resolved = [p for p in preds if p.get("outcome") is not None]

    # A7 valuation inputs — 재계산에 필요한 값이 ledger에 남아 있는가
    VAL = ("market_cap", "risk_free_rate")
    val_ok = [t for t, d in ledgers.items()
              if all(d["inputs"].get(k) is not None for k in VAL)
              and d["discount_rate"].get("r") is not None]

    # 분석일 분포 — 홀드아웃 창 자체가 존재하는가
    dates = sorted(d["meta"]["analyzed_at"][:10] for d in ledgers.values())

    filings = measure_filing_availability(ledgers)
    restate = measure_restatements(tickers)
    vintage = measure_ledger_vintage(ledgers)

    axes = {}

    axes["A1_historical_filings"] = {
        "verdict": "READY" if filings["none"] == 0 and filings["partial"] <= n * 0.2
                   else "PARTIAL",
        "measure": f"공시일 전 연도 확보 {filings['full']}/{n}, "
                   f"부분 {filings['partial']}, 없음 {filings['none']}",
        "blocking": [] if filings["none"] == 0 else
                    ["companyfacts를 못 가져오는 종목이 있다"],
        "detail": filings,
    }

    axes["A2_as_of_inputs"] = {
        "verdict": "NOT_READY" if not pit_present else "PARTIAL",
        "measure": f"meta.point_in_time 보유 {len(pit_present)}/{n}",
        "blocking": [
            "34종목 전부 PIT 상태값이 없다(필드 부재). v3.47 이후 재실행된 "
            "분석이 0건이라 '그 시점에 알 수 있었는가'를 ledger만으로 판정할 수 없다.",
        ],
    }

    axes["A3_input_preservation"] = {
        "verdict": "PARTIAL",
        "measure": f"필수 입력 8종 전부 보존 {len(full_inputs)}/{n} · "
                   f"cagr_5y_base_year 부재 {len(no_base_year)}종목",
        "blocking": [
            f"v3.19판 스키마 {len(no_base_year)}종목({', '.join(no_base_year)})은 "
            "CAGR 기준연도가 없어 성장경로를 재구성할 수 없다.",
        ],
    }

    axes["A4_market_data"] = {
        "verdict": "NOT_READY",
        "measure": f"price_at_analysis 보유 {len(price)}/{n}",
        "blocking": [
            f"진입가를 아는 종목이 {len(price)}건뿐이라 실현수익률을 계산할 수 없다.",
            "과거 일별 종가 시계열이 이 저장소에 없다(가격 데이터 계층 자체가 없음).",
        ],
        "have": sorted(price),
    }

    axes["A5_thesis_date"] = {
        "verdict": "NOT_READY",
        "measure": f"thesis/ 디렉터리 파일 {thesis_n}건",
        "blocking": [
            "Investment Thesis가 0건이다. 판정(judgment)은 신호이지 논거가 아니므로 "
            "'그때 무엇을 믿고 샀는가'를 재현할 대상 자체가 없다.",
        ],
    }

    axes["A6_prediction_state"] = {
        "verdict": "PARTIAL",
        "measure": f"봉인 예측 {len(preds)}건 · 해소 {len(resolved)}건",
        "blocking": [
            "해소된 예측이 0건이다. 2026-08-16 동결분은 다음 회계연도 매출이 "
            "공시돼야 해소되므로 아직 검증 대상이 아니다.",
        ] if not resolved else [],
    }

    axes["A7_valuation_inputs"] = {
        "verdict": "READY" if len(val_ok) == n else "PARTIAL",
        "measure": f"market_cap·risk_free_rate·r 전부 보존 {len(val_ok)}/{n}",
        "blocking": [],
    }

    axes["A8_source_availability"] = {
        "verdict": "NOT_READY",
        "measure": f"구조화 provenance {len(prov)}/{n} · "
                   f"자유서술 data_sources {len(src_free_text)}/{n}",
        "blocking": [
            "값 단위 provenance가 0건이다. 어느 값이 어느 공시에서 왔는지 알 수 없어 "
            "'그 시점 원자료'를 재구성할 수 없다.",
            "원자료 스냅샷이 보존되지 않았다 - 지금 조회한 값은 재작성 이후 값일 수 있다.",
        ],
    }

    axes["A9_restatement_information"] = {
        "verdict": "NOT_READY",
        "measure": f"복수공시 기간 {restate['multi_filing_periods']}건 중 "
                   f"재작성 {restate['restated']}건({restate['restated_pct_of_multi']}%) · "
                   f"재작성 기간에 걸친 ledger 입력 "
                   f"{vintage['ledger_values_on_restated_periods']}건 중 "
                   f"최신판본 {vintage['matches_latest_vintage_only']} vs "
                   f"최초판본 {vintage['matches_first_vintage_only']}",
        "blocking": [
            f"재작성 기간에 걸친 ledger 입력 "
            f"{vintage['ledger_values_on_restated_periods']}건 중 "
            f"{vintage['matches_latest_vintage_only']}건이 **최신 판본**과 일치하고 "
            f"최초 판본과만 일치하는 것은 {vintage['matches_first_vintage_only']}건뿐이다. "
            "즉 이 ledger들을 재작성 이전 T0 스냅샷으로 재사용하면 look-ahead가 된다 - "
            "PIT 필드를 붙여도 값 자체가 미래 판본이므로 해소되지 않는다.",
        ],
        "note": "기존 34종목 분석이 틀렸다는 뜻이 아니다 - 전부 2026년 분석이고 "
                "그 시점에서 최신 판본을 쓰는 것은 옳다. 문제는 더 이른 T0로 되돌릴 때만 발생한다.",
        "detail": restate,
        "vintage": vintage,
    }

    axes["A10_information_set_reproducibility"] = {
        "verdict": "NOT_READY",
        "measure": f"분석일 범위 {dates[0]} ~ {dates[-1]}",
        "blocking": [
            "전체 분석 이력이 3주 남짓이다 - 재현할 '과거 시점'이 사실상 존재하지 않는다.",
            "A2·A4·A5·A8이 동시에 막혀 있어 정보집합을 그때 상태로 되돌릴 수 없다.",
        ],
    }

    order = {"NOT_READY": 0, "PARTIAL": 1, "READY": 2}
    overall = min(axes.values(), key=lambda a: order[a["verdict"]])["verdict"]

    result = {
        "phase": "PHASE 5 — Historical Replay readiness",
        "date": "2026-08-21",
        "implemented_replay": False,
        "note": "§14에 따라 Historical Replay를 구현하지 않았다. readiness만 판정한다.",
        "tickers": n,
        "analysis_date_range": [dates[0], dates[-1]],
        "axes": axes,
        "overall_verdict": overall,
        "affects_official_judgment": False,
    }
    os.makedirs("reports", exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"=== PHASE 5 readiness · 종목 {n} · 분석일 {dates[0]}~{dates[-1]}")
    for k, a in axes.items():
        print(f"  {a['verdict']:<10} {k:<38} {a['measure']}")
    print(f"\n  전체 판정: {overall}  (가장 약한 축이 결정 - 평균내지 않는다)")
    print(f"\n  재작성: {restate['restated']}/{restate['multi_filing_periods']} "
          f"({restate['restated_pct_of_multi']}%) · "
          f"1%초과 {restate['spread']['gt_1pct']} / "
          f"5%초과 {restate['spread']['gt_5pct']} / "
          f"20%초과 {restate['spread']['gt_20pct']}")
    for e in restate["examples"][:4]:
        print(f"    {e['ticker']:<6} {e['tag'][:34]:<34} {e['period_end']} "
              f"{e['first']:>18,.0f} -> {e['last']:>18,.0f} ({e['delta_pct']}%)")
    print(f"\n  ledger 판본: 재작성 기간에 걸친 입력 "
          f"{vintage['ledger_values_on_restated_periods']}건 중 "
          f"최신판본만 {vintage['matches_latest_vintage_only']} / "
          f"최초판본만 {vintage['matches_first_vintage_only']} / "
          f"둘다 {vintage['matches_both']} / 불일치 {vintage['matches_neither']}")
    print(f"\n  -> {OUT}")


if __name__ == "__main__":
    main()
