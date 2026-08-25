"""
RQ-003 측정: 회계품질(발생액) 지표가 IRS에 **증분 정보**를 주는가 (2026-08-24)

## 왜 이 측정을 먼저 하는가

이 프로젝트의 확립된 순서는 **측정 -> 결정 -> 배선**이다(RQ-001이 후보 10개를
측정해 2개만 ADOPT한 선례). 아직 `engine/`을 건드리지 않는다 - 지표가 기존
지표와 중복이면 REJECT해야 하고, 중복 여부는 코퍼스 실측으로만 알 수 있다.

## 무엇을 재는가

IRS는 "이 숫자가 맞는가"는 계산하지만 **"이 숫자를 믿어도 되는가"는 아예 묻지
않는다**(2026-08-24 실측: 발생액·M-score·매출인식 이상 검색 히트 0).
`etf_engine.earnings_quality_score`가 있으나 그건 *ETF 구성종목 중 적자기업
비중*이라 기업 회계품질과 무관하다.

발생액(accruals) = 회계이익 - 현금이익. 외부 근거:

  Sloan, Richard G. (1996) "Do stock prices fully reflect information in accruals
  and cash flows about future earnings?" The Accounting Review 71(3), 289-315.
  핵심: 이익의 **발생액 성분이 현금흐름 성분보다 지속성이 낮다**.

⚠️ **출처 검증 수준을 정직하게 기록한다.** 서지정보는 4개 이상 독립 학술출처
(ScienceDirect·NBER·Wharton·AAA)로 삼각검증했으나, **원문 PDF가 1996년 스캔본
(JBIG2 이미지)이라 계산식 본문은 직접 확인하지 못했다.** 따라서 아래 구현은
Sloan의 정확한 대차대조표식 발생액이 아니라 **현금흐름표 기반 근사**이며,
`PROXY_ONLY`로 라벨한다(growth_quality.py의 capex proxy 선례와 동일 처리).

## 왜 F-Score(합성점수)를 쓰지 않는가

Piotroski F-Score(2000)는 이 영역의 표준 도구지만 **9개 신호를 0~9 정수로
합산하는 합성점수**다. 이 프로젝트는 §31 안티기능 등록부에 "단일 합성점수"를
**의도적으로 만들지 않는 것**으로 이미 등록했고(research_lenses의 6차원 별점을
같은 이유로 REJECT), 사유는 "중요도가 다른 축이 같은 무게가 되고 공백이 점수
뒤에 숨는다"였다. 그 등록을 이번에 뒤집을 새 증거가 없다.

추가로 F-Score는 **고 book-to-market(가치주) 표본 1976-1996**에서 검증됐다.
IRS의 유니버스는 FCF-DCF를 적용하는 성장주 쪽이라 검증 도메인 밖이다 - 이
프로젝트가 반복 경계해온 "검증 범위를 넘겨 적용하는" 오류에 해당한다.

그래서 **개별 진단값 하나**(발생액 강도)만 후보로 올린다.
"""
import json
import os
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.filing_dates import DEFAULT_USER_AGENT, fetch_company_facts, ticker_to_cik

CACHE_DIR = os.environ.get(
    "SEC_CACHE_DIR",
    "/tmp/claude-0/-home-user-IRS/1fb7a46a-ee0b-5b39-806f-ff7ee862da26/scratchpad/secfacts",
)

# 발생액 계산에 필요한데 IRS AnalysisInputs에는 없는 항목.
# net_income: 회계이익. operating_cashflow: 현금이익. assets: 문헌 표준 스케일러.
EXTRA_TAGS = {
    "net_income": ("NetIncomeLoss", "ProfitLoss"),
    "assets": ("Assets",),
    "operating_cashflow": (
        "NetCashProvidedByUsedInOperatingActivities",
        "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations",
        "CashFlowsFromUsedInOperatingActivities",
    ),
}
ANNUAL_FORMS = ("10-K", "10-K/A", "20-F", "20-F/A", "40-F")


def _facts(ticker):
    os.makedirs(CACHE_DIR, exist_ok=True)
    p = os.path.join(CACHE_DIR, f"{ticker}.json")
    if os.path.exists(p):
        return json.load(open(p, encoding="utf-8"))
    cik = ticker_to_cik(ticker)
    if not cik:
        return None
    f = fetch_company_facts(cik)
    json.dump(f, open(p, "w", encoding="utf-8"))
    return f


def annual_series(facts, tags):
    """연차보고서(10-K/20-F) 기준 회계연도별 값. 같은 해 중복이면 최초 제출본."""
    for tag in tags:
        for ns in ("us-gaap", "ifrs-full"):
            node = (facts.get("facts", {}).get(ns, {}) or {}).get(tag)
            if not node:
                continue
            out = {}
            for unit_rows in node.get("units", {}).values():
                for r in unit_rows:
                    if r.get("form") not in ANNUAL_FORMS or not r.get("end"):
                        continue
                    # 연간 구간만(분기 제외). start가 있으면 기간, 없으면 시점(Assets).
                    if r.get("start"):
                        days = (
                            int(r["end"][:4]) * 365 + int(r["end"][5:7]) * 30
                            + int(r["end"][8:10])
                        ) - (
                            int(r["start"][:4]) * 365 + int(r["start"][5:7]) * 30
                            + int(r["start"][8:10])
                        )
                        if not (330 <= days <= 400):
                            continue
                    y = int(r["end"][:4])
                    if y not in out or r.get("filed", "") < out[y][1]:
                        out[y] = (r["val"], r.get("filed", ""))
            if out:
                return {y: v for y, (v, _) in out.items()}
    return {}


def main():
    ledgers = {}
    import glob
    for p in glob.glob("ledger/*.json"):
        d = json.load(open(p, encoding="utf-8"))
        ledgers[d["meta"]["ticker"]] = d

    rows, failed = [], []
    for t in sorted(ledgers):
        facts = _facts(t)
        if facts is None:
            failed.append((t, "CIK 매핑 실패"))
            continue
        ni = annual_series(facts, EXTRA_TAGS["net_income"])
        ocf = annual_series(facts, EXTRA_TAGS["operating_cashflow"])
        ta = annual_series(facts, EXTRA_TAGS["assets"])
        common = sorted(set(ni) & set(ocf) & set(ta))
        if len(common) < 2:
            failed.append((t, f"공통 연도 {len(common)}개"))
            continue

        # 발생액 = 회계이익 - 현금이익. 문헌 표준대로 **평균 총자산**으로 스케일.
        # (평균: 기초·기말 자산의 평균 - 기간 항목을 시점 항목으로 나누는 왜곡 완화)
        per_year = {}
        for i, y in enumerate(common):
            if i == 0:
                continue
            avg_assets = (ta[y] + ta[common[i - 1]]) / 2
            if avg_assets <= 0:
                continue
            per_year[y] = (ni[y] - ocf[y]) / avg_assets

        if not per_year:
            failed.append((t, "평균 총자산 계산 불가"))
            continue

        years = sorted(per_year)
        recent = years[-1]
        window = years[-5:]
        rows.append({
            "ticker": t,
            "years_used": len(years),
            "accrual_ratio_latest": per_year[recent],
            "accrual_ratio_mean5": sum(per_year[y] for y in window) / len(window),
            "latest_year": recent,
            "ni_latest": ni[recent],
            "ocf_latest": ocf[recent],
            # Piotroski ACCRUAL 신호와 같은 방향의 이진 판정(합성점수로 쓰지 않는다)
            "cash_exceeds_earnings": ocf[recent] > ni[recent],
            # 기존 IRS 지표(중복 검사용)
            "gap": ledgers[t]["expectation_gap"],
            "drs": ledgers[t]["drs"]["score"],
            "realistic_growth": ledgers[t]["growth"]["realistic_growth"],
            "margin_volatility": ledgers[t]["drs"]["components"].get("margin_volatility"),
            "sbc_to_fcf": (ledgers[t].get("sbc_cross_check") or {}).get("sbc_to_fcf_pct"),
        })

    out = {
        "generated_at": "2026-08-24",
        "research_question": "RQ-003: 발생액 기반 회계품질이 IRS에 증분 정보를 주는가",
        "measurement_only": "이 스크립트는 측정 전용 - engine/·ledger/를 건드리지 않는다",
        "proxy_disclosure": (
            "Sloan(1996)의 대차대조표식 발생액이 아니라 현금흐름표 기반 근사"
            "((NI-OCF)/평균총자산). 원문이 스캔본이라 계산식 직접 검증 실패."
        ),
        "n": len(rows), "failed": failed, "rows": rows,
    }
    os.makedirs("reports/research", exist_ok=True)
    path = "reports/research/RQ-003_accrual_quality_2026-08-24.json"
    json.dump(out, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"측정 완료: {len(rows)}종목 성공, {len(failed)}종목 실패 -> {path}")
    for t, why in failed:
        print(f"  실패 {t}: {why}")


if __name__ == "__main__":
    main()
