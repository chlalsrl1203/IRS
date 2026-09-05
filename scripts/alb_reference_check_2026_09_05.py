"""
Albemarle Corporation(ALB) 참조 점검 - 2026-09-05. **보유 7순위(3.1%) 종목.**

이 프로젝트가 한 번도 분석한 적 없는 종목이다(ledger 없음). 보유비중은
작지만(3.1%) 사용자 수익률이 **-34.3%**로 8종목 중 최악이라 "왜 판단을
안 하고 있는가"에 답할 필요가 있다.

## 결론: FRAMEWORK_MISMATCH - 그리고 이번엔 **엔진이 실제로 실행을 거부한다**

MU는 계산은 되지만 낡은 데이터라 무의미한 경우였는데, ALB는 그보다 앞
단계에서 막힌다. 두 사유가 겹친다:

### 사유 1 - v3.19 CAGR 가드가 실제로 발동한다(추정이 아니라 실행 확인)

FCF(=OCF-capex) 실측(단위 $M):
  2015 +133 / 2016 **+539** / 2017 -14 / 2018 -154 / 2019 -133 /
  2020 **-51** / 2021 -610 / 2022 +646 / 2023 -828 / 2024 -993 / 2025 +692

5년 CAGR의 기본 기준연도(`years[-6]`)는 **FY2020(FCF -$51M)**이고, v3.19
가드는 시작값이 음수면 예외를 던진다(파이썬이 복소수를 조용히 반환하는 것을
막기 위한 설계). **최근 11년 중 7년이 FCF 음수**라 `cagr_base_year_override`로
피하려 해도 쓸 수 있는 기준연도가 FY2016(+$539M) 하나뿐인데, 그건 리튬
사이클의 특정 국면을 임의로 고르는 것이라 근거가 없다.

이 스크립트는 그 가드가 실제로 발동함을 **실행으로 확인**한다(문서로만
주장하지 않는다).

### 사유 2 - 리튬 가격 사이클: 이 트래커에서 본 가장 큰 진폭

매출: 3,328(2021) -> **7,320**(2022, +120%) -> 9,617(2023, +31%) ->
**5,378**(2024, **-44%**) -> 5,143(2025) - 고점 대비 **-47%**.
영업이익: 798 -> 2,470 -> 252 -> **-1,777** -> **-367**(2년 연속 영업손실).

AA·NRG·MP·EQT·CDE·COP·DINO·EOG·EXE·NEM·OVV·CF·HL과 동일한 '자본집약
원자재' 유형이며, `demand_sensitivity_pct`·`competitor_threat_weights` 같은
경쟁구도 기반 주관 입력으로는 가격 사이클을 표현할 수 없다.

### 사유 3(MU와 공통) - 연차 데이터가 이미 사이클 전환을 놓쳤다

2026-09-05 WebSearch로 확인한 Q2 2026(2026-08-06 발표):
  - 조정 EBITDA **$858M, +155%YoY**, 전사 마진 **49.2%**
  - 에너지저장 부문 매출 $1.28B(+78%), 실현 리튬가격 **+60%**
  - 분기 영업현금흐름 $710M, **분기 FCF $638M** - FY2025 연간 FCF($692M)에
    거의 맞먹는다
  - FY2026 capex 가이던스를 약 **$500M로 하향**(FY2023 $2,155M의 1/4)
  - ⚠️ 다만 회사 스스로 **Q3는 리튬가격 하락 가정으로 순차 감소**를 예고

즉 FY2025 연간(영업손실 -$367M)과 현재 국면이 정반대다. MU와 같은 구조의
노후화이며, 방향은 반대로 **과소평가** 쪽으로 작동한다.

## 그래서 사용자에게 무엇을 말할 수 있는가

**엔진은 이 종목에 대해 저평가/과대평가 어느 쪽도 말할 수 없다.** 대신
검증된 사실만 남긴다:
  - 2년 연속 영업손실(FY2024 -$1,777M, FY2025 -$367M) 후 FY2026 상반기
    급반등(Q2 조정 EBITDA +155%)
  - FCF가 최근 11년 중 7년 음수 - 이 사업은 구조적으로 현금흐름이 불안정하다
  - capex를 $2,155M(2023) -> $500M(2026 가이던스)로 급감축 - 성장투자에서
    현금보존으로 전환한 국면
  - 회사 스스로 Q3 순차 감소를 예고 - 반등이 이어질지 미확인

**정식분석 재개 조건**: FCF가 2개 회계연도 연속 플러스가 되어 5년 CAGR
기준연도를 정상적으로 잡을 수 있게 되는 시점. 그 전까지는 이 엔진의
FCF-DCF 프레임이 원리적으로 적용되지 않는다.

실행: python3 scripts/alb_reference_check_2026_09_05.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

OUT = "reports/alb_reference_check_2026-09-05.json"

# ── SEC XBRL companyfacts 실측(CIK 0000915913, 2026-09-05 조회) ─────────
REVENUE = {  # us-gaap:Revenues
    2016: 2677e6, 2017: 3072e6, 2018: 3375e6, 2019: 3589e6, 2020: 3129e6,
    2021: 3328e6, 2022: 7320e6, 2023: 9617e6, 2024: 5378e6, 2025: 5143e6,
}
OPERATING_INCOME = {
    2015: 345e6, 2016: 601e6, 2017: 572e6, 2018: 912e6, 2019: 666e6,
    2020: 506e6, 2021: 798e6, 2022: 2470e6, 2023: 252e6, 2024: -1777e6,
    2025: -367e6,
}
OPERATING_CASHFLOW = {
    2015: 361e6, 2016: 736e6, 2017: 304e6, 2018: 546e6, 2019: 719e6,
    2020: 799e6, 2021: 344e6, 2022: 1908e6, 2023: 1327e6, 2024: 688e6,
    2025: 1282e6,
}
CAPEX = {
    2015: 228e6, 2016: 197e6, 2017: 318e6, 2018: 700e6, 2019: 852e6,
    2020: 850e6, 2021: 954e6, 2022: 1262e6, 2023: 2155e6, 2024: 1681e6,
    2025: 590e6,
}
NET_INCOME = {
    2015: 335e6, 2016: 644e6, 2017: 55e6, 2018: 694e6, 2019: 533e6,
    2020: 376e6, 2021: 124e6, 2022: 2690e6, 2023: 1573e6, 2024: -1179e6,
    2025: -511e6,
}


def main() -> int:
    years = sorted(OPERATING_CASHFLOW)
    fcf = {y: OPERATING_CASHFLOW[y] - CAPEX[y] for y in years}
    base_5y = years[-6]
    negatives = [y for y in years if fcf[y] < 0]

    # ── 사유 1을 실행으로 확인한다 - 가드가 정말 발동하는가 ───────────────
    # ⚠️ 초판에서 존재하지 않는 심볼을 import하다 난 ImportError를 '가드 발동'
    # 으로 세고 있었다 - 검증한 척이 되는 전형적 오류라 실제 가드 함수
    # (engine.pipeline._cagr)를 직접 부르도록 고쳤다. ValueError만 발동으로 센다.
    from engine.pipeline import _cagr
    guard_fired, guard_msg = False, None
    try:
        _cagr(fcf[base_5y], fcf[years[-1]], years[-1] - base_5y, "fcf_cagr_5y")
    except ValueError as e:
        guard_fired, guard_msg = True, f"{type(e).__name__}: {e}"

    print("=== ALB 참조 점검 2026-09-05 (ledger 미생성) ===")
    print(f"FCF($M): " + "  ".join(f"{y}:{fcf[y]/1e6:+,.0f}" for y in years))
    print(f"5년 CAGR 기본 기준연도: FY{base_5y} (FCF {fcf[base_5y]/1e6:+,.0f}M)")
    print(f"FCF 음수 연도: {negatives} ({len(negatives)}/{len(years)}년)")
    print(f"v3.19 CAGR 가드 발동: {guard_fired}")
    if guard_msg:
        print(f"  -> {guard_msg}")
    print()
    print("매출 YoY:")
    ry = sorted(REVENUE)
    for a, b in zip(ry, ry[1:]):
        print(f"  {b}: {REVENUE[b]/1e6:>8,.0f}M  ({(REVENUE[b]/REVENUE[a]-1)*100:+.1f}%)")
    print()
    print("영업이익 최근 3년: " + "  ".join(
        f"{y}:{OPERATING_INCOME[y]/1e6:+,.0f}M" for y in (2023, 2024, 2025)))
    print()
    print("-> 공식 판정 없음(FRAMEWORK_MISMATCH). 재개 조건: FCF가 2개 회계연도")
    print("   연속 플러스가 되어 5년 CAGR 기준연도를 정상적으로 잡을 수 있을 때.")

    payload = {
        "ticker": "ALB",
        "as_of": "2026-09-05",
        "status": "FRAMEWORK_MISMATCH",
        "ledger_written": False,
        "reasons": [
            {
                "id": "negative_fcf_base_year",
                "detail": (
                    f"5년 CAGR 기본 기준연도 FY{base_5y}의 FCF가 "
                    f"${fcf[base_5y]/1e6:,.0f}M(음수)라 v3.19 가드가 실행을 "
                    f"거부한다. 최근 {len(years)}년 중 {len(negatives)}년이 "
                    f"FCF 음수({negatives})라 override로 피할 기준연도도 "
                    f"FY2016 하나뿐인데 그건 사이클 국면을 임의로 고르는 것이다."
                ),
                "verified_by_execution": guard_fired,
                "guard_message": guard_msg,
            },
            {
                "id": "commodity_price_cycle",
                "detail": (
                    "매출이 2021 $3,328M -> 2023 $9,617M(+189%) -> 2025 "
                    "$5,143M(고점 대비 -47%)로 요동치고 영업이익은 FY2024 "
                    "-$1,777M / FY2025 -$367M로 2년 연속 손실이다. "
                    "AA·MP·CDE·HL·CF·NEM 등과 동일한 자본집약 원자재 유형."
                ),
            },
            {
                "id": "annual_data_stale",
                "detail": (
                    "Q2 2026 조정 EBITDA $858M(+155%YoY)·마진 49.2%·분기 FCF "
                    "$638M으로 사이클이 이미 전환했다 - FY2025 연간(영업손실 "
                    "-$367M)과 정반대 국면이다. MU와 같은 구조의 노후화이며 "
                    "방향은 반대(과소평가 쪽)로 작동한다."
                ),
            },
        ],
        "observed_facts": {
            "fcf_by_year": {str(y): fcf[y] for y in years},
            "revenue_by_year": {str(y): REVENUE[y] for y in sorted(REVENUE)},
            "operating_income_by_year": {str(y): OPERATING_INCOME[y]
                                         for y in sorted(OPERATING_INCOME)},
            "net_income_by_year": {str(y): NET_INCOME[y]
                                   for y in sorted(NET_INCOME)},
            "capex_peak_to_guidance": {
                "FY2023_actual": CAPEX[2023], "FY2026_guidance": 500e6},
        },
        "reopen_condition": (
            "FCF가 2개 회계연도 연속 플러스가 되어 5년 CAGR 기준연도를 "
            "정상적으로 잡을 수 있게 되는 시점"
        ),
        "data_sources": [
            "SEC XBRL companyfacts (CIK 0000915913 Albemarle, 조회 2026-09-05)",
            "WebSearch: ALB Q2 2026 실적(조정EBITDA $858M +155%, 마진 49.2%, "
            "리튬가격 +60%, 분기 FCF $638M, FY2026 capex 가이던스 ~$500M, "
            "Q3 순차 감소 예고) - Investing.com/BigGo Finance/StockTitan, "
            "2026-09-05 재인용",
        ],
    }
    os.makedirs("reports", exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"\nsaved: {OUT}  (ledger는 만들지 않았다)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
