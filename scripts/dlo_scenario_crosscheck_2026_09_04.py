"""
DLO 시나리오 크로스체크 - 2026-09-04. **보유 4순위(11.1%) 종목.**

공식 판정(ledger/DLO_2026-09-04.json, Gap +23.74%p "저평가 가능성" S등급)은
그대로 두고, **그 S등급이 어떤 가정 위에 서 있는지**를 드러낸다 -
`is_insurer`/`sbc_cross_check`/ROP·KEYS 크로스체크와 동일한 "병기, 자동판정
안 함" 원칙.

## 왜 이 종목이 특별히 위험한가 - 세 가지가 동시에 걸린다

  1. **성장상한 바인딩**: Realistic Growth 25.00%는 CAGR 계산값(36.37%)이
     아니라 **Lynch fast_grower 상한 그 자체**다. 즉 Gap = 25.00% -
     Implied Growth이고, 성장분석은 결과에 전혀 기여하지 않는다(M-1).
  2. **FCF0가 한 해짜리 극단값**: 결제대행업의 OCF는 가맹점 정산 타이밍에
     관통당한다. FY2024 FCF -$34.5M -> FY2025 +$413.2M. 공식 판정은
     $413.2M을 쓰는데 3년평균은 **$223.7M**(54%)뿐이다.
  3. **회사 자신의 가이던스가 더 낮다**: 총이익 성장 +25~30%, 영업이익
     성장 +27.5~32.5%. TPV는 +92%인데 총이익은 +29% - 테이크레이트 압축.

## 격자

  - 세로(FCF0): `official_413.2M`(최근연도) / `avg3y_223.7M`(정규화)
  - 가로(RG):   `cap_25.00`(공식, 상한 바인딩) / `guidance_27.50`(회사
                영업이익 성장 가이던스 중간값 근사)

⚠️ Implied Growth는 FCF0에 따라 **다시 계산해야 한다**(RG와 달리 독립이
아니다). 엔진의 `implied_growth_two_stage`를 그대로 호출해 재계산한다 -
새 밸류에이션 로직은 0줄이다.

실행: python3 scripts/dlo_scenario_crosscheck_2026_09_04.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.expectation_gap_engine import (
    implied_growth_single_stage,
    implied_growth_two_stage,
    judgment_from_gap,
    judgment_grade_from_gap,
)

LEDGER = "ledger/DLO_2026-09-04.json"
OUT = "reports/dlo_scenario_crosscheck_2026-09-04.json"

FCF_SCENARIOS = {
    "official_최근연도": 413175000.0,          # FY2025 OCF - capex
    "avg3y_정규화": (293453000.0 - 965000.0
                     + (-32784000.0) - 1705000.0
                     + 415457000.0 - 2282000.0) / 3.0,
}
RG_SCENARIOS = {
    "cap_25.00(공식)": 0.2500,
    "guidance_27.50": 0.2750,   # 회사 FY2026 영업이익 성장 가이던스 중간값
}


def main() -> int:
    d = json.load(open(LEDGER, encoding="utf-8"))
    dr = d["discount_rate"]
    r, n, g_term = dr["r"], dr["n"], dr["g_terminal"]
    market_cap = d["inputs"]["market_cap"]
    official_gap = d["expectation_gap"]

    rows = []
    for fcf_label, fcf0 in FCF_SCENARIOS.items():
        ig_two, _, _ = implied_growth_two_stage(market_cap, fcf0, r, n, g_term)
        ig_single = implied_growth_single_stage(market_cap, fcf0, r)
        for rg_label, rg in RG_SCENARIOS.items():
            gap = rg - ig_two
            rows.append({
                "fcf0_scenario": fcf_label,
                "fcf0": fcf0,
                "rg_scenario": rg_label,
                "realistic_growth": rg,
                "implied_growth_two_stage": ig_two,
                "implied_growth_single_stage": ig_single,
                "gap": gap,
                "judgment": judgment_from_gap(gap),
                "grade": judgment_grade_from_gap(gap),
            })

    official = rows[0]
    assert abs(official["gap"] - official_gap) < 1e-9, (
        f"공식 재현 실패: {official['gap']} vs {official_gap} - "
        "격자 계산이 ledger와 어긋나면 나머지 시나리오도 전부 무의미하다"
    )

    print(f"{'FCF0 시나리오':>20}{'RG 시나리오':>18}{'FCF0($M)':>11}"
          f"{'IG':>8}{'Gap':>10}  판정(등급)")
    for x in rows:
        print(f"{x['fcf0_scenario']:>20}{x['rg_scenario']:>18}"
              f"{x['fcf0']/1e6:>10,.1f}{x['implied_growth_two_stage']*100:>7.2f}%"
              f"{x['gap']*100:>+9.2f}%p  {x['judgment']}({x['grade']})")

    differing = [x for x in rows[1:] if x["judgment"] != official["judgment"]]
    print(f"\n공식 재현 확인: Gap {official['gap']*100:+.2f}%p == "
          f"ledger {official_gap*100:+.2f}%p ✓")
    print(f"공식 판정과 다른 시나리오: {len(differing)}/{len(rows)-1}건")

    payload = {
        "ticker": "DLO",
        "as_of": "2026-09-04",
        "purpose": "최초 정식분석 S등급이 어떤 가정 위에 서 있는지 드러내기",
        "official_ledger": LEDGER,
        "affects_official_judgment": False,
        "scenarios": rows,
        "n_scenarios_differing_from_official": len(differing),
        "reading": (
            "네 칸 전부 '저평가 가능성'이 유지된다 - **Gap의 크기는 FCF0 "
            "정규화에 크게 반응하지만(약 -8%p) 판정 방향은 뒤집히지 않는다**. "
            "이 종목의 저평가 신호 자체는 FCF0 한 해짜리 극단값 때문에 생긴 "
            "것이 아니라는 뜻이므로, S등급을 액면 그대로 믿지는 않되 방향은 "
            "유지해도 된다. ⚠️ 단, Realistic Growth 25.00%가 Lynch 상한 "
            "그 자체라 이 Gap은 사실상 '상한 - Implied Growth'이며, 상한값의 "
            "근거는 이 저장소 어디에도 검증돼 있지 않다(M-1). 상한을 회사 "
            "가이던스 수준(27.5%)으로 올려도 결론이 같다는 점만 확인된다."
        ),
        "known_limitation": (
            "(1) 결제대행업의 OCF는 가맹점 정산 타이밍에 관통당해 FCF-DCF의 "
            "전제(FCF가 주주 귀속 현금)를 정확히 만족하지 않는다 - 보험업 "
            "플로트(v3.22)와 같은 계열의 구조적 왜곡이며 전용 경로를 만들 만큼 "
            "실증사례가 쌓이지 않았다. (2) 3년평균 FCF0는 정규화의 한 방법일 "
            "뿐 검증된 기준이 아니다. (3) guidance_27.50은 회사의 1개년 "
            "영업이익 성장 예측이고 Realistic Growth는 n=12년 개념이라 기간이 "
            "다르다 - ROP가 확립한 override 자격(다년 실현실적)에 못 미치므로 "
            "공식 판정으로 승격하지 않는다."
        ),
    }
    os.makedirs("reports", exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"\nsaved: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
