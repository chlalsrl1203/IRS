"""
PIT 감사 (2026-08-15) - 34종목이 **분석일 이후에 공시된 데이터를 썼는지** 확인한다.

## 이 감사가 답하는 것과 답하지 않는 것

**답한다**: "분석에 쓴 회계연도가 분석일 시점에 이미 공시돼 있었는가?"
SEC companyfacts의 `filed`(최초 제출일)와 ledger의 `analyzed_at`을 대조한다.
위반이 나오면 그건 **확정적인 결함**이다 - 나오지 않은 실적으로 계산한 셈이다.

**답하지 않는다**: "ledger에 들어간 숫자가 그 시점의 숫자였는가?"
재무데이터는 분석 시점에 Alpha Vantage에서 가져왔고, 이후 재작성됐다면 지금
조회한 값과 다를 수 있다. 그 검증은 원자료 스냅샷이 있어야 가능하다
(change_plan C-09 Provenance, 여전히 DEFERRED).

## ⚠️ 그래서 이 감사 결과로 ledger를 PIT_VALID로 바꾸지 않는다

위반 0건이어도 `PIT_UNKNOWN`은 그대로 둔다 - 검증하지 못한 축(재작성)이
남아 있는데 VALID로 표시하면 **검증하지 않은 것을 검증했다고 주장**하는 게
된다(계약서 5.1절). 이 스크립트는 `reports/`에만 쓴다.

v3.47이 금지한 것은 filing_date를 **추정**해 넣는 것이지, 1차 자료에서
**조회**하는 것이 아니다 - 그 구분이 이 감사를 가능하게 한다.
"""

import json
import os
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import glob  # noqa: E402

from engine.filing_dates import (  # noqa: E402
    SEC_TICKERS_URL,
    _http_json,
    annual_filing_dates,
    check_lookahead,
    fetch_company_facts,
)

OUT_PATH = f"reports/pit_audit_{datetime.now(timezone.utc):%Y-%m-%d}.json"


def build_cik_map():
    """티커->CIK 매핑을 한 번만 받는다(종목마다 받으면 낭비다)."""
    data = _http_json(SEC_TICKERS_URL)
    return {row["ticker"].upper(): str(row["cik_str"]).zfill(10)
            for row in data.values()}


def main():
    ledgers = []
    for p in sorted(glob.glob("ledger/*.json")):
        with open(p, encoding="utf-8") as f:
            ledgers.append((os.path.basename(p), json.load(f)))

    print(f"PIT 감사 대상: {len(ledgers)}종목")
    cik_map = build_cik_map()

    results, violations_found, unresolved = [], [], []

    for name, led in ledgers:
        ticker = led["meta"]["ticker"]
        analyzed_at = led["meta"]["analyzed_at"][:10]
        fys = sorted(int(y) for y in led["inputs"]["revenue_by_year"])

        cik = cik_map.get(ticker.upper())
        if cik is None:
            unresolved.append({"ticker": ticker, "reason": "SEC 티커 목록에 없음"})
            print(f"  {ticker:6s} CIK 미확인 - 건너뜀(추측하지 않음)")
            continue

        try:
            facts = fetch_company_facts(cik)
        except Exception as e:
            unresolved.append({"ticker": ticker, "reason": f"{type(e).__name__}: {e}"})
            print(f"  {ticker:6s} 조회 실패: {e}")
            continue

        filing_dates = annual_filing_dates(facts)
        check = check_lookahead(filing_dates, analyzed_at, fys)

        # 분석의 fcf0를 결정하는 최근 회계연도가 특히 중요하다
        latest_fy = max(fys)
        latest_filed = filing_dates.get(latest_fy)

        row = {
            "ticker": ticker,
            "ledger": name,
            "analyzed_at": analyzed_at,
            "cik": cik,
            "latest_fiscal_year": latest_fy,
            "latest_fy_filed": latest_filed,
            "latest_fy_available_at_analysis": (
                None if latest_filed is None else latest_filed <= analyzed_at
            ),
            "n_violations": len(check["violations"]),
            "violations": check["violations"],
            "unknown_years": check["unknown_years"],
            "filing_dates_by_year": {str(k): v for k, v in filing_dates.items()
                                     if k in fys},
        }
        results.append(row)

        if check["violations"]:
            violations_found.append(row)
            print(f"  {ticker:6s} ⚠️ 미래정보 사용 흔적 {len(check['violations'])}건")
        else:
            mark = "?" if latest_filed is None else "✓"
            print(f"  {ticker:6s} {mark} 위반 없음 "
                  f"(최근 FY{latest_fy} 제출 {latest_filed}, 분석 {analyzed_at}, "
                  f"미상 {len(check['unknown_years'])}개년)")

        time.sleep(0.15)   # SEC 권장 요청 간격 준수

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": "ledger/*.json 전건 - 분석일 이후 공시 데이터 사용 여부",
        "method": (
            "SEC XBRL companyfacts의 최초 제출일(filed)과 ledger의 analyzed_at 대조. "
            "회계연도는 연간 구간(330~400일) 종료일 연도 기준."
        ),
        "limitation": (
            "재작성(restatement)은 검증하지 못한다 - 이 감사는 '그 시점에 공시돼 "
            "있었는가'만 답하며, 'ledger의 숫자가 그 시점 값이었는가'는 원자료 "
            "스냅샷(change_plan C-09 Provenance)이 있어야 답할 수 있다. "
            "따라서 위반 0건이어도 PIT_VALID로 표시하지 않는다."
        ),
        "n_checked": len(results),
        "n_with_violations": len(violations_found),
        "n_unresolved": len(unresolved),
        "unresolved": unresolved,
        "results": results,
    }

    os.makedirs("reports", exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print()
    print("=" * 72)
    print(f"검사 {len(results)}종목 / 미래정보 사용 흔적 {len(violations_found)}종목 "
          f"/ 조회 실패 {len(unresolved)}종목")
    print(f"리포트: {OUT_PATH}")
    print("⚠️ 위반 0건이어도 ledger의 PIT 상태는 PIT_UNKNOWN 그대로 유지한다")
    print("   (재작성 여부는 이 방법으로 검증되지 않는다)")
    print("=" * 72)


if __name__ == "__main__":
    main()
