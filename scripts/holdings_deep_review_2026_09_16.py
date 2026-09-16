"""
보유 포트폴리오 8종목 심화 재분석 (2026-09-16, 사용자 요청 "내 원래 포트폴리오
기업들 심화 재분석").

⚠️ `ledger/`에 한 줄도 쓰지 않는다(v3.42 원칙) - 가격 재계산·시나리오 교차검증은
공식 판정이 아니라 모니터링 신호다. 산출물은 `reports/`에만 남긴다.
새 밸류에이션 로직 0줄 - 기존 검증된 함수만 호출한다:
  engine.thesis_monitor.recompute_gap_at_market_cap / inputs_from_ledger
  engine.pipeline.run_analysis
  engine.deep_screen.deep_screen / implied_growth_from_fcf_yield
  engine.data.providers.sec.SecCompanyFactsProvider

네 갈래로 본다:
  ① 가격 드리프트 - ledger 분석일 이후 주가 변화가 Gap·등급을 어디까지 옮겼나
  ② 데이터 노후화 감사 - ledger 입력값이 지금 SEC 원자료와 같은가
  ③ 시나리오 교차검증 - ①②에서 드러난 쟁점이 판정을 실제로 흔드는가
  ④ 미판정 2종목(MU·ALB) - 이 엔진이 답할 수 있는 만큼까지만 답한다
"""
import dataclasses
import datetime
import glob
import json
import os

from engine.data.providers.sec import SecCompanyFactsProvider
from engine.deep_screen import deep_screen, implied_growth_from_fcf_yield
from engine.expectation_gap_engine import judgment_from_gap, judgment_grade_from_gap
from engine.pipeline import run_analysis
from engine.thesis_monitor import inputs_from_ledger, recompute_gap_at_market_cap

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AS_OF = "2026-09-16"

# Alpha Vantage GLOBAL_QUOTE, latestDay 2026-09-15 종가.
PRICES = {"PTC": 132.75, "VRT": 234.61, "SE": 102.65, "DLO": 14.45,
          "NOW": 141.90, "MU": 927.60, "ALB": 113.45, "ACGL": 97.04}

# SEC 10-Q 표지(dei:EntityCommonStockSharesOutstanding) 실측.
SHARES = {"MU": 1_129_393_151, "ALB": 118_005_057}


def load_holdings():
    with open(os.path.join(ROOT, "portfolio", "holdings.json"), encoding="utf-8") as f:
        return json.load(f)


def latest_ledger(ticker):
    files = sorted(glob.glob(os.path.join(ROOT, "ledger", f"{ticker}_*.json")))
    if not files:
        return None, None
    with open(files[-1], encoding="utf-8") as f:
        return os.path.relpath(files[-1], ROOT), json.load(f)


# ── ① 가격 드리프트 ─────────────────────────────────────────────────────
def price_drift(ticker, ledger):
    old_price = ledger["inputs"]["price_at_analysis"]
    new_price = PRICES[ticker]
    new_mcap = ledger["inputs"]["market_cap"] * new_price / old_price
    r = recompute_gap_at_market_cap(ledger, new_mcap)
    r["price_then"] = old_price
    r["price_now"] = new_price
    r["price_change_pct"] = new_price / old_price - 1.0
    return r


# ── ② 데이터 노후화 감사 ─────────────────────────────────────────────────
def staleness(ticker, ledger, provider, retrieved_at):
    """ledger 입력값이 지금 SEC 원자료와 같은가.

    ⚠️ 불일치를 자동 해소하지 않는다(P0-07 원칙) - 어느 쪽이 옳은지는
    분석자가 1차 자료로 판정한다.
    """
    try:
        res = provider.fetch_annual_financials(ticker, retrieved_at=retrieved_at)
    except Exception as exc:                     # noqa: BLE001 - 조회 실패도 사실
        return {"status": "SEC_FETCH_FAILED", "error": f"{type(exc).__name__}: {exc}"}
    sec_rev = {int(f.fiscal_year): f.value for f in res.facts if f.metric == "revenue"}
    if not sec_rev:
        return {"status": "SEC_REVENUE_MISSING"}
    out = {"status": "OK", "sec_latest_fy": max(sec_rev), "mismatches": []}
    if ledger is None:
        out["ledger_latest_fy"] = None
        return out
    led_rev = {int(k): v for k, v in ledger["inputs"]["revenue_by_year"].items()}
    out["ledger_latest_fy"] = max(led_rev)
    out["new_annual_available"] = max(sec_rev) > max(led_rev)
    for y in sorted(set(sec_rev) & set(led_rev)):
        a, b = led_rev[y], sec_rev[y]
        if abs(a - b) / max(abs(a), abs(b)) > 0.005:
            out["mismatches"].append({"fiscal_year": y, "ledger": a, "sec_now": b,
                                      "delta_pct": b / a - 1.0})
    return out


# ── ③ 시나리오 교차검증 ──────────────────────────────────────────────────
def scenario(ledger, label, **overrides):
    inp = inputs_from_ledger(ledger)
    if overrides:
        inp = dataclasses.replace(inp, **overrides)
    r = run_analysis(inp)
    return {"label": label, "gap": r["expectation_gap"], "grade": r["judgment_grade"],
            "judgment": r["judgment"], "drs": r["drs"]["score"],
            "realistic_growth": r["growth"]["realistic_growth"],
            "implied_growth": r["implied_growth"]["value"]}


# ── ④ 미판정 종목 참조 스크린 ────────────────────────────────────────────
def reference_screen(ticker, provider, retrieved_at):
    res = provider.fetch_annual_financials(ticker, retrieved_at=retrieved_at)
    by = {}
    for f in res.facts:
        by.setdefault(f.metric, {})[int(f.fiscal_year)] = f.value
    series = {f"{k}_by_year": by.get(k, {}) for k in
              ("revenue", "operating_income", "operating_cashflow", "capex")}
    mcap = SHARES[ticker] * PRICES[ticker]
    d = dataclasses.asdict(deep_screen(ticker, series, market_cap=mcap))
    d["market_cap"] = mcap
    d["shares_outstanding"] = SHARES[ticker]
    return d


def mu_fcf0_range(ref):
    """MU: FCF0를 어느 국면에서 잡느냐로 판정이 갈리는지 직접 측정.

    메모리 사이클은 연차 FY2025(저점 국면)와 TTM(고점 국면)이 15배 이상
    차이난다 - 어느 쪽도 '정상 상태 FCF'가 아니다. 판정이 그 선택에 따라
    실제로 바뀌는지가 FRAMEWORK_MISMATCH 판단의 핵심 근거다.
    """
    mcap, rg, r = ref["market_cap"], ref["realistic_growth"], ref["r"]
    rows = []
    for label, fcf0, note in [
        ("FY2025 연차", 1.668e9, "메모리 사이클 저점 국면(현재 deep_screen 경로)"),
        ("TTM", 26.169e9, "FY2025 Q4 + FY2026 9M - 사이클 고점 국면"),
        ("FY2026 9M 연환산", 26.100e9 * 4 / 3, "9M FCF x 4/3"),
    ]:
        y = fcf0 / mcap
        ig = implied_growth_from_fcf_yield(y, r)
        gap = rg - ig
        rows.append({"label": label, "note": note, "fcf0": fcf0, "fcf_yield": y,
                     "implied_growth": ig, "gap": gap,
                     "grade": judgment_grade_from_gap(gap),
                     "judgment": judgment_from_gap(gap)})
    return rows


def main():
    holdings = load_holdings()
    provider = SecCompanyFactsProvider()
    retrieved_at = datetime.date.today().isoformat()
    total = holdings["total_market_value_krw"]

    report = {
        "as_of": AS_OF,
        "holdings_as_of": holdings["as_of"],
        "price_source": "Alpha Vantage GLOBAL_QUOTE (latestDay 2026-09-15 종가)",
        "affects_official_judgment": False,
        "_note": [
            "보유 포트폴리오 심화 재분석. ledger/를 수정하지 않는다(v3.42).",
            "가격 재계산·시나리오는 공식 판정이 아니라 모니터링 신호다",
            "(is_insurer·sbc_cross_check와 동일한 '병기, 자동판정 안 함' 원칙).",
        ],
        "positions": [],
    }

    for pos in holdings["positions"]:
        t = pos["ticker"]
        weight = pos["market_value_krw"] / total
        path, ledger = latest_ledger(t)
        row = {"ticker": t, "weight": weight,
               "market_value_krw": pos["market_value_krw"],
               "return_pct_app": pos["return_pct"],
               "ledger": path,
               "ledger_analyzed_at": ledger["meta"]["analyzed_at"] if ledger else None}
        row["staleness"] = staleness(t, ledger, provider, retrieved_at)
        if ledger is not None:
            row["price_drift"] = price_drift(t, ledger)
            row["model_divergence"] = ledger["implied_growth"]["models"]["divergence"]
            row["sbc_cross_check"] = ledger.get("sbc_cross_check")
        else:
            row["reference_screen"] = reference_screen(t, provider, retrieved_at)
            row["official_judgment"] = None
        report["positions"].append(row)

    # ── 시나리오 교차검증 ────────────────────────────────────────────────
    se = latest_ledger("SE")[1]
    provider_rev = {2020: 4375664000.0, 2021: 9955190000.0, 2022: 12449705000.0,
                    2023: 13063560000.0, 2024: 16819866000.0, 2025: 19625021000.0}
    vrt = latest_ledger("VRT")[1]
    report["scenarios"] = {
        "SE_revenue_tag_definition": {
            "issue": (
                "Sea Limited가 FY2025 20-F(2026-04-17 제출)에서 매출 태깅을 재분류했다."
                " `us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax`는 FY2024까지"
                " 총매출이었으나 FY2025부터 ASC 606 계약매출만 담고(19.625B), 총매출은"
                " `us-gaap:Revenues`(22.938B)로 옮겨졌다. 차액 3.313B은 Monee(구 SeaMoney)"
                " 이자수익 등 비계약 매출이다."),
            "primary_source_check": (
                "회사 FY2025 실적발표 원문: GAAP 총매출 US$22.9B(+36.4% YoY),"
                " Monee GAAP 매출 US$3.8B(+60.1%) - ledger의 22,938,469,000이 맞다."),
            "hazard_class": (
                "⚠️ 신규 유형 - **같은 태그 안에서 정의가 바뀐다**. provider의"
                " `[태그 혼재]` 경고는 여러 태그에 걸칠 때만 발동하므로 이 경우"
                " 아무 경고도 나오지 않는다(FY2016~2025 전부 같은 태그)."),
            "runs": [scenario(se, "① ledger 그대로(총매출)"),
                     scenario(se, "② provider 현재 시리즈(정의 혼재)",
                              revenue_by_year=provider_rev)],
        },
        "VRT_utilityinnovation_acquisition": {
            "issue": (
                "2026-09-02 UtilityInnovation Group 인수 발표($1.45B 현금 + 최대"
                " $1.15B 언아웃). ledger(2026-09-04)의 순부채는 2026-06-30 10-Q"
                " 기준이라 이 현금유출이 반영돼 있지 않다."),
            "runs": [scenario(vrt, "① ledger 그대로(순부채 $129.2M)"),
                     scenario(vrt, "② 인수대금 $1.45B 현금유출 반영",
                              net_debt=vrt["inputs"]["net_debt"] + 1_450_000_000),
                     scenario(vrt, "③ + 언아웃 전액 $1.15B까지",
                              net_debt=vrt["inputs"]["net_debt"] + 2_600_000_000)],
        },
    }

    mu_ref = next(p["reference_screen"] for p in report["positions"]
                  if p["ticker"] == "MU")
    report["scenarios"]["MU_fcf0_cycle_phase"] = {
        "issue": ("메모리 사이클 - FY2025 연차 FCF $1.668B vs TTM FCF $26.169B(15.7배)."
                  " 어느 쪽도 정상 상태 FCF가 아니다."),
        "runs": mu_fcf0_range(mu_ref),
    }

    out = os.path.join(ROOT, "reports", f"holdings_deep_review_{AS_OF}.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print("저장:", os.path.relpath(out, ROOT))

    # ── 콘솔 요약 ────────────────────────────────────────────────────────
    print(f"\n{'티커':5} {'비중':>6}  {'ledger':11} {'Gap(분석시)':>10} -> {'Gap(현재)':>9}  등급   주가")
    for p in report["positions"]:
        if "price_drift" in p:
            d = p["price_drift"]
            print(f"{p['ticker']:5} {p['weight']*100:5.2f}%  {p['ledger_analyzed_at'][:10]}  "
                  f"{d['gap_then']*100:+9.2f}%p -> {d['gap_now']*100:+7.2f}%p  "
                  f"{d['grade_then']}->{d['grade_now']}  {d['price_change_pct']*100:+6.1f}%")
        else:
            rs = p["reference_screen"]
            print(f"{p['ticker']:5} {p['weight']*100:5.2f}%  {'ledger 없음':11} "
                  f"{'참조스크린':>13} {rs['gap']*100:+7.2f}%p  "
                  f"{judgment_grade_from_gap(rs['gap'])}      "
                  f"({rs['judgment']})")
    stale = [p["ticker"] for p in report["positions"]
             if p["staleness"].get("mismatches")]
    print(f"\nSEC 원자료 불일치 종목: {stale or '없음'}")
    print(f"미판정(공식 ledger 없음): "
          f"{[p['ticker'] for p in report['positions'] if p['ledger'] is None]}")


if __name__ == "__main__":
    main()
