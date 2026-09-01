"""
SBC 하방 미검증 25종목 — SEC 원자료 확보 실험 (2026-08-21)

## 왜 지금인가 — 재개조건이 실제로 충족됐다

`docs/research_decision_record.md` 결정 #40:

    | 40 | SBC 미확보 25종목 `sbc_by_year` 확보 | **EXPERIMENT** |
    | 확보된 9종목 중 1건(WDAY)에서 실제로 판정이 뒤집혔다 |
    | 25/34의 회계 하방이 **미검증일 뿐 안전한 것이 아니다** | **SEC 원자료 확보** |

재개조건이 "SEC 원자료 확보"였고, 그 수단은 2026-08-19 P0-03에서 생겼다
(`engine/data/providers/sec.py`, METRIC_TAGS에 `sbc` 이미 포함).
`AnalysisInputs.sbc_by_year`는 v3.23부터 배선돼 있다.

**따라서 새 방법론도 새 기능도 필요 없다.** 막고 있던 것은 데이터 하나였고
그게 풀렸다. 이 스크립트는 그 데이터를 가져와 기존 계산을 그대로 돌린다.

## 왜 WebSearch 추정치로 대신하지 않는가

TYL 사건(2026-08-05): 경량검증이 SBC/FCF ≈ 62%라고 보고했으나 SEC 원자료
기준 실제는 **24.4%** — 약 3배 오차였다. 원인은 리서치 에이전트가 2차 출처의
잘못된 FCF를 인용한 것이었다. 판정을 흔들 수 있는 수치는 1차 자료로만 확정한다.

## 이 스크립트가 하는 일 / 하지 않는 일

**한다**: ledger에 이미 저장된 값(market_cap·r·n·g_terminal·realistic_growth·
fcf0)을 그대로 읽고, SEC에서 SBC만 새로 가져와 `pipeline.run_analysis()`의
`sbc_cross_check` 블록과 **동일한 계산**을 재현한다.

**하지 않는다**: `ledger/`에 쓰지 않는다. 공식 Gap·판정·등급을 바꾸지 않는다.
이건 실험이고, 통합 여부는 결과를 보고 별도로 판단한다(§STEP 11 → 17).

## ⚠️ 회계연도 라벨을 신뢰하지 않고 fcf0로 정렬을 확인한다

ledger의 `revenue_by_year` 키는 회사가 쓰는 회계연도 라벨이고, SEC 쪽 연도는
`period_end`의 **역년(calendar year)**이다. 둘이 어긋나면 다른 해의 SBC를
같은 해 FCF0에서 빼게 된다 — 조용히 틀리는 유형이라 라벨을 맞추는 대신
**SEC의 OCF−capex가 ledger의 fcf0와 일치하는 연도**를 찾아 그 해의 SBC를 쓴다.
일치하는 해가 없으면 추측하지 않고 `UNRESOLVED`로 남긴다.

이 대조는 부수적으로 P0-07이 8종목에서 발견한 "ledger 손입력값 vs SEC 원자료"
불일치를 25종목으로 확장 점검하는 효과도 낸다.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.expectation_gap_engine import (  # noqa: E402
    judgment_from_gap, judgment_grade_from_gap,
)
from engine.pipeline import compare_implied_growth_models  # noqa: E402

LEDGER_DIR = "ledger"
CACHE_DIR = os.environ.get(
    "SBC_CACHE_DIR",
    "/tmp/claude-0/-home-user-IRS/1fb7a46a-ee0b-5b39-806f-ff7ee862da26/scratchpad/secfacts",
)
RETRIEVED_AT = "2026-08-21"

# fcf0 정합성 허용오차. ledger 값은 손입력이라 반올림 단위가 종목마다 다르다
# (백만 단위 반올림이 흔하다). 0.5%를 넘으면 "같은 해가 아닐 수 있다"로 본다.
FCF0_MATCH_TOL = 0.005


def _load_ledgers():
    out = {}
    for fn in sorted(os.listdir(LEDGER_DIR)):
        if not fn.endswith(".json"):
            continue
        with open(os.path.join(LEDGER_DIR, fn), encoding="utf-8") as f:
            d = json.load(f)
        out[d["meta"]["ticker"]] = (fn, d)
    return out


def _missing_sbc_ledgers(ledgers=None):
    """
    이 실험이 실제로 다루는 모집단 - `sbc_by_year`를 이미 갖춰
    `run_analysis()`가 자체적으로 `sbc_cross_check`를 채운 ledger는 제외한다.

    2026-09-01: CROX가 처음부터 `sbc_by_year`를 채워 분석돼(정식분석 시점에
    이미 SBC를 확보) 이 harvest가 다룰 대상이 아니게 됐다 - `_load_ledgers()`
    가 반환하는 전체 집합과 이 실험의 모집단(당시 미확보 25종목)이 갈라지는
    첫 사례다. `main()`이 이미 이 필터를 인라인으로 썼는데, 테스트도 같은
    필터가 필요해 여기로 뽑아 재사용한다(중복 구현하면 둘이 어긋난다).
    """
    ledgers = ledgers if ledgers is not None else _load_ledgers()
    return {t: v for t, v in ledgers.items() if not v[1].get("sbc_cross_check")}


def _cached_facts(ticker, user_agent=None):
    """companyfacts 원본을 로컬에 캐시한다(수 MB · 재실행 시 재조회 방지)."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    path = os.path.join(CACHE_DIR, f"{ticker}.json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    from engine.filing_dates import fetch_company_facts, ticker_to_cik

    cik = ticker_to_cik(ticker, user_agent)
    if not cik:
        return None
    facts = fetch_company_facts(cik, user_agent)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(facts, f)
    return facts


def fetch_metrics(ticker, years):
    """SEC에서 sbc/OCF/capex를 가져온다. 캐시된 companyfacts를 주입해 재사용."""
    from engine.data.providers.sec import SecCompanyFactsProvider

    facts = _cached_facts(ticker)
    if facts is None:
        return None
    prov = SecCompanyFactsProvider(
        purpose="internal_research",
        fetch_facts=lambda cik, ua=None: facts,
        resolve_cik=lambda t, ua=None: "0000000000",
    )
    return prov.fetch_annual_financials(
        ticker, metrics=("sbc", "operating_cashflow", "capex"),
        fiscal_years=years, retrieved_at=RETRIEVED_AT,
    )


def _closest(cands, target):
    """{연도: 값} 중 target에 상대오차가 가장 작은 (연도, 오차)."""
    best, best_err = None, None
    for y, v in sorted(cands.items()):
        err = abs(v - target) / abs(target)
        if best_err is None or err < best_err:
            best, best_err = y, err
    return best, best_err


def align_year(result, fcf0, ocf_ledger):
    """
    ledger의 최근 회계연도가 SEC의 어느 연도인지 확정한다.

    ⚠️ **정렬 키를 실행 중에 바꿨다 — 그 사실을 남긴다.** 초판은 SEC의
    `OCF−capex`가 ledger `fcf0`와 맞는 해를 찾았는데, 25종목 중 3종목
    (WCN·MCK·PDD)이 실패했다. 원인을 파보니 WCN·MCK는 **OCF가 소수점까지
    정확히 일치**하고 capex만 어긋났다:

        WCN FY2025  capex  ledger 1,194,366,000 vs SEC 1,179,228,000 (+1.3%)
        MCK FY2026  capex  ledger   745,000,000 vs SEC   436,000,000 (+71%)

    즉 연도가 틀린 게 아니라 **capex 정의가 다른 것**이다(엔진 자신도 WCN
    capex에 `[태그 혼재]` 경고를 낸다 — `PaymentsToAcquireProductiveAssets`와
    `PaymentsToAcquirePropertyPlantAndEquipment`가 섞였다). 정렬은 "어느 해인가"만
    답하면 되므로, 다중 태그 모호성이 문서화된 capex를 키에 넣은 것이 방법 결함이었다.

    **이건 결과를 보고 임계값을 완화한 것이 아니다** — 허용오차 0.5%는 그대로이고
    키만 모호성이 없는 항목으로 바꿨다. 실제로 이 수정으로 풀린 두 종목의 SBC/FCF는
    MCK 4.57%·WCN 6.51%로 **판정을 하나도 바꾸지 않는다**(유리한 결과를 만들어내지
    않았음을 확인). capex 괴리 자체는 별도 소견으로 보고한다(P0-07 대조 결과의 연장).

    반환: (연도, 근거, 상세) — 확정 못 하면 (None, "UNRESOLVED", 상세).
    """
    ocf = {f.fiscal_year: f.value for f in result.facts if f.metric == "operating_cashflow"}
    cap = {f.fiscal_year: f.value for f in result.facts if f.metric == "capex"}
    detail = {}

    fcf_cands = {y: ocf[y] - cap[y] for y in set(ocf) & set(cap)}
    if fcf_cands and fcf0:
        y, err = _closest(fcf_cands, fcf0)
        detail["fcf0_rel_error"] = err
        if err <= FCF0_MATCH_TOL:
            detail["capex_sec"] = cap.get(y)
            return y, "FCF0_MATCH", detail

    # 2순위: OCF 단독. 단일 라인아이템이라 정의 모호성이 없다.
    if ocf and ocf_ledger:
        y, err = _closest(ocf, ocf_ledger)
        detail["ocf_rel_error"] = err
        if err <= FCF0_MATCH_TOL:
            detail["capex_sec"] = cap.get(y)
            detail["capex_ledger_vs_sec"] = (
                None if y not in cap or not cap[y]
                else (ocf_ledger - fcf0 - cap[y]) / cap[y]
            )
            return y, "OCF_MATCH_CAPEX_DIVERGES", detail

    return None, "UNRESOLVED", detail


def sbc_cross_check_from_ledger(d, sbc0):
    """
    `pipeline.run_analysis()`의 sbc_cross_check 블록과 동일한 계산.

    새 로직을 쓰지 않는다 — ledger에 저장된 r/n/g_terminal/market_cap/
    realistic_growth/model_used를 그대로 넣어 같은 함수를 부른다.
    """
    inp, dr = d["inputs"], d["discount_rate"]
    fcf0 = d["derived"]["fcf0"]
    rg = d["growth"]["realistic_growth"]
    model = d["implied_growth"]["model_used"]
    gap = d["expectation_gap"]

    fcf0_adj = fcf0 - sbc0
    if fcf0_adj <= 0:
        return {
            "sbc0": sbc0, "sbc_to_fcf_pct": sbc0 / fcf0 if fcf0 else None,
            "fcf0_sbc_adjusted": fcf0_adj, "implied_growth_sbc_adjusted": None,
            "gap_sbc_adjusted": None, "judgment_sbc_adjusted": None,
            "judgment_flipped": None, "model_not_applicable": True,
        }
    models = compare_implied_growth_models(
        inp["market_cap"], fcf0_adj, dr["r"], dr["n"], dr["g_terminal"]
    )
    ig = models[model]
    gap_adj = rg - ig if ig is not None else None
    j_adj = judgment_from_gap(gap_adj) if gap_adj is not None else None
    return {
        "sbc0": sbc0,
        "sbc_to_fcf_pct": sbc0 / fcf0,
        "fcf0_sbc_adjusted": fcf0_adj,
        "implied_growth_sbc_adjusted": ig,
        "gap_sbc_adjusted": gap_adj,
        "judgment_sbc_adjusted": j_adj,
        "judgment_flipped": j_adj is not None and j_adj != d["judgment"],
        "grade_base": judgment_grade_from_gap(gap),
        "grade_sbc_adjusted": judgment_grade_from_gap(gap_adj) if gap_adj is not None else None,
        "model_not_applicable": False,
    }


def rows_from_existing(ledgers):
    """
    이미 ledger에 `sbc_cross_check`가 있는 9종목을 같은 스키마로 옮긴다.

    SEC를 다시 부르지 않는다 — 값이 이미 확정돼 있고, 재조회하면 그 사이
    재작성(restatement)된 값으로 조용히 바뀔 수 있다. 다만 구 스키마에는
    등급이 없어 `judgment_grade_from_gap`으로 **파생만** 한다(새 계산 아님).
    """
    out = []
    for t, (fn, d) in sorted(ledgers.items()):
        cc = d.get("sbc_cross_check")
        if not cc:
            continue
        gap, gap_adj = d["expectation_gap"], cc.get("gap_sbc_adjusted")
        out.append({
            "ticker": t, "ledger_file": fn, "status": "OK",
            "source_of_sbc": "ledger (기존 확보분 - 재조회하지 않음)",
            "fcf0_ledger": d["derived"]["fcf0"],
            "judgment_base": d["judgment"], "gap_base": gap,
            "grade_base": judgment_grade_from_gap(gap),
            "grade_sbc_adjusted": (judgment_grade_from_gap(gap_adj)
                                   if gap_adj is not None else None),
            **{k: cc.get(k) for k in (
                "sbc0", "sbc_to_fcf_pct", "fcf0_sbc_adjusted",
                "implied_growth_sbc_adjusted", "gap_sbc_adjusted",
                "judgment_sbc_adjusted", "judgment_flipped")},
        })
    return out


def main():
    ledgers = _load_ledgers()
    missing = _missing_sbc_ledgers(ledgers)
    print(f"ledger {len(ledgers)}종목 · SBC 미확보 {len(missing)}종목\n")

    rows = []
    for t, (fn, d) in sorted(missing.items()):
        fcf0 = d["derived"]["fcf0"]
        yrs = sorted(int(y) for y in d["inputs"]["revenue_by_year"])
        # 회계연도 라벨과 역년이 어긋날 수 있어 ±1년 여유를 두고 조회한다.
        probe = range(min(yrs) - 1, max(yrs) + 2)
        row = {"ticker": t, "ledger_file": fn, "fcf0_ledger": fcf0,
               "latest_year_label": yrs[-1]}
        try:
            res = fetch_metrics(t, probe)
        except Exception as e:                      # noqa: BLE001
            row.update(status="FETCH_FAILED", detail=str(e)[:200])
            rows.append(row)
            print(f"{t:6s} FETCH_FAILED {str(e)[:70]}")
            continue
        if res is None:
            row.update(status="CIK_UNRESOLVED")
            rows.append(row)
            print(f"{t:6s} CIK_UNRESOLVED")
            continue

        row["sec_limitations"] = res.limitations
        ocf_ledger = d["inputs"]["operating_cashflow_by_year"].get(str(yrs[-1]))
        year, basis, detail = align_year(res, fcf0, ocf_ledger)
        row["fcf0_match_year"] = year
        row["alignment_basis"] = basis
        row["alignment_detail"] = detail
        if year is None:
            row.update(status="YEAR_UNRESOLVED")
            rows.append(row)
            print(f"{t:6s} YEAR_UNRESOLVED  {detail}")
            continue

        sbc = {f.fiscal_year: (f.value, f.source, f.available_at)
               for f in res.facts if f.metric == "sbc"}
        if year not in sbc:
            row.update(status="SBC_NOT_TAGGED",
                       sbc_years_available=sorted(sbc))
            rows.append(row)
            print(f"{t:6s} SBC_NOT_TAGGED (FY{year}) · 확보연도={sorted(sbc)}")
            continue

        val, src, avail = sbc[year]
        cc = sbc_cross_check_from_ledger(d, val)
        row.update(status="OK", sbc_source=src, sbc_available_at=avail,
                   judgment_base=d["judgment"], gap_base=d["expectation_gap"],
                   **cc)
        rows.append(row)
        flip = "FLIP" if cc["judgment_flipped"] else "    "
        note = "*" if basis != "FCF0_MATCH" else " "
        print(f"{t:6s} OK  FY{year}{note} SBC/FCF {cc['sbc_to_fcf_pct'] * 100:6.2f}%  "
              f"Gap {row['gap_base'] * 100:+7.2f} -> "
              f"{(cc['gap_sbc_adjusted'] or 0) * 100:+7.2f}%p  "
              f"{cc.get('grade_base')}->{cc.get('grade_sbc_adjusted')}  {flip}")

    rows += rows_from_existing(ledgers)
    rows.sort(key=lambda r: r["ticker"])

    out = {
        "generated_at": RETRIEVED_AT,
        "purpose": "결정 #40(SBC 미확보 25종목) 재개조건 충족에 따른 실험",
        "affects_official_judgment": False,
        "method": "ledger 저장값 + SEC SBC만 신규 · pipeline sbc_cross_check와 동일 계산",
        "self_consistency": (
            "기존 확보 9종목에 같은 재구성 계산을 적용하면 ledger의 "
            "sbc_cross_check와 1e-12 정밀도로 일치한다(tests/test_sbc_harvest.py)."
        ),
        "monotonicity": (
            "SBC>0이면 fcf0가 줄어 Implied Growth가 오르므로 Gap은 **반드시 감소**한다. "
            "따라서 이 교차검증은 유니버스 이탈만 만들 수 있고 진입은 만들 수 없다 - "
            "구조적으로 거짓편입(false positive) 필터다."
        ),
        "known_limitation_growth_path": (
            "SBC를 수준(fcf0)에만 적용하고 성장경로(FCF CAGR)에는 적용하지 않는 "
            "비대칭이 있다. 2026-08-21 실측: 성장경로에도 적용하면 FCF CAGR이 "
            "GEN -1.07%p ~ PTC +13.41%p로 움직이며 대부분 상방이다(= 현행이 SBC "
            "순영향을 과대평가할 수 있음). 그렇다고 확장이 정답은 아니다 - 기준연도 "
            "FCF에서 SBC를 빼면 기준값이 작아져 CAGR이 부풀려지는 경로가 생긴다"
            "(PTC는 기준연도 FCF의 46%가 SBC, 차감 후 최종연도의 11.5%로 "
            "근사-0 엄격기준 10% 바로 위). 확장은 DEFER하고 크기만 기록한다."
        ),
        "fcf0_match_tolerance": FCF0_MATCH_TOL,
        "results": rows,
    }
    os.makedirs("reports", exist_ok=True)
    path = f"reports/sbc_harvest_{RETRIEVED_AT}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"\n저장: {path}")

    new = [r for r in rows if r["status"] == "OK" and "sbc_source" in r]
    ok = [r for r in rows if r["status"] == "OK"]
    print(f"\n신규 확보 {len(new)}/{len(missing)} · 기존 보유 {len(ok) - len(new)} "
          f"-> 커버리지 {len(ok)}/{len(rows)}종목")
    print(f"판정 flip {sum(1 for r in ok if r.get('judgment_flipped'))} · "
          f"등급 변경 {sum(1 for r in ok if r.get('grade_base') != r.get('grade_sbc_adjusted'))}")
    for s in sorted({r["status"] for r in rows} - {"OK"}):
        print(f"  {s}: {[r['ticker'] for r in rows if r['status'] == s]}")


if __name__ == "__main__":
    main()
