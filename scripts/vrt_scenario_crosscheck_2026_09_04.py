"""
VRT 시나리오 크로스체크 - 2026-09-04. **보유 2순위(19.2%) 종목.**

공식 판정(ledger/VRT_2026-09-04.json, Gap -1.24%p "적정가/경계선")은 그대로
두고, 판정을 흔드는 **두 축을 교차**해 병기한다 - `is_insurer`/
`sbc_cross_check`/ROP·KEYS 크로스체크와 동일한 "병기, 자동판정 안 함" 원칙.

## 왜 이 종목만 2차원으로 보는가

VRT는 이 트래커에서 **모델선택 취약성이 가장 큰 종목군**에 속한다
(v3.51 gap_range: 모델선택 단독으로 Gap이 12~20%p 움직이는 9종목).
이번 재분석에서도 single_stage 9.07% vs two_stage 19.95%로 **10.88%p**
벌어져 경고 임계값(3%p)의 3.6배다. 동시에 회사 자체 FY2026 가이던스
(오가닉 +30~32%)가 엔진 Realistic Growth(18.71%)를 크게 웃돈다.

두 축은 **서로 독립**이다 - Implied Growth는 시총·FCF0·r·n에서만 나오고
Realistic Growth 입력과 무관하므로(ROP·KEYS 크로스체크가 쓴 것과 같은
성질), 격자를 그려도 계산이 오염되지 않는다.

## 축 1: Realistic Growth (세로)

  - `official_18.71`   : 엔진 계산값(매출 3y/5y CAGR 가중평균 x 구조적할인)
  - `size_cap_23.00`   : v3.67 규모조건부 상한. 매출 $10.23B(2015년 달러
                         $7,577.7M) 구간에서 실질 20% 이상을 10년 유지한
                         기업이 1.1%뿐이라는 Credit Suisse HOLT base rate에서
                         나온 **역사적 지속가능 상한**.
  - `guidance_30.00`   : 회사 FY2026 가이던스 오가닉 성장 하단(+30~32%).
                         ⚠️ **1개년 예측이지 다년 실현실적이 아니다** -
                         ROP(다년 실현 오가닉)가 확립한 override 자격에
                         못 미치므로 공식 판정으로 승격하지 않는다(KEYS 선례).

## 축 2: Implied Growth 모델 (가로)

  - `two_stage`(공식)  : 고성장 -> terminal 수렴 경로를 명시적으로 모형화
  - `single_stage`     : Gordon 정상상태 가정

## 축 3(병기): SBC 차감

FY2025 SBC $45.9M = FCF의 **2.4%**(트래커 최하위권) - 이 종목에서는
SBC가 판정을 흔들 만한 크기가 아님을 확인하는 용도다.

실행: python3 scripts/vrt_scenario_crosscheck_2026_09_04.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.expectation_gap_engine import judgment_from_gap, judgment_grade_from_gap

LEDGER = "ledger/VRT_2026-09-04.json"
OUT = "reports/vrt_scenario_crosscheck_2026-09-04.json"

RG_SCENARIOS = {
    "official_18.71": None,          # ledger에서 읽는다
    "size_cap_23.00": 0.2300,        # v3.67 base_rates 역사적 상한(명목)
    "guidance_30.00": 0.3000,        # 회사 FY2026 오가닉 가이던스 하단
}


def main() -> int:
    d = json.load(open(LEDGER, encoding="utf-8"))
    rg_official = d["growth"]["realistic_growth"]
    ig = d["implied_growth"]
    models = {
        "two_stage(공식)": ig["models"]["two_stage"],
        "single_stage": ig["models"]["single_stage"],
    }
    sbc = d["sbc_cross_check"]

    RG_SCENARIOS["official_18.71"] = rg_official

    rows = []
    for rg_label, rg in RG_SCENARIOS.items():
        for m_label, ig_v in models.items():
            gap = rg - ig_v
            rows.append({
                "realistic_growth_scenario": rg_label,
                "implied_growth_model": m_label,
                "realistic_growth": rg,
                "implied_growth": ig_v,
                "gap": gap,
                "judgment": judgment_from_gap(gap),
                "grade": judgment_grade_from_gap(gap),
            })

    # SBC 차감(공식 RG + 공식 모델)
    rows.append({
        "realistic_growth_scenario": "official_18.71",
        "implied_growth_model": "two_stage(공식) + SBC차감",
        "realistic_growth": rg_official,
        "implied_growth": sbc["implied_growth_sbc_adjusted"],
        "gap": sbc["gap_sbc_adjusted"],
        "judgment": sbc["judgment_sbc_adjusted"],
        "grade": judgment_grade_from_gap(sbc["gap_sbc_adjusted"]),
    })

    official = next(r for r in rows
                    if r["realistic_growth_scenario"] == "official_18.71"
                    and r["implied_growth_model"] == "two_stage(공식)")
    differing = [r for r in rows if r["judgment"] != official["judgment"]]

    print(f"{'RG 시나리오':>18} {'IG 모델':>26} {'RG':>8}{'IG':>8}{'Gap':>10}  판정(등급)")
    for r in rows:
        print(f"{r['realistic_growth_scenario']:>18} {r['implied_growth_model']:>26}"
              f"{r['realistic_growth']*100:>7.2f}%{r['implied_growth']*100:>7.2f}%"
              f"{r['gap']*100:>+9.2f}%p  {r['judgment']}({r['grade']})")
    print()
    print(f"공식 판정('{official['judgment']}')과 다른 시나리오: "
          f"{len(differing)}/{len(rows)-1}건")

    payload = {
        "ticker": "VRT",
        "as_of": "2026-09-04",
        "purpose": "보유 2순위(19.2%) 종목의 판정 취약성 2차원 점검",
        "official_ledger": LEDGER,
        "official": official,
        "affects_official_judgment": False,
        "scenarios": rows,
        "n_scenarios_differing_from_official": len(differing),
        "reading": (
            "실측 격자 7칸 중 공식 판정('적정가/경계선')이 나오는 것은 "
            "**Implied Growth를 two_stage로 잡은 3칸뿐**이고, 나머지 4칸은 "
            "전부 '저평가 가능성'(A 3칸, S 1칸)이다. 특히 **RG를 엔진 "
            "계산값 그대로 두고 모델만 single_stage로 바꾸면 -1.24%p -> "
            "+9.64%p(A등급)로 뒤집힌다** - 이 종목의 판정을 실제로 결정하는 "
            "것은 성장률 추정이 아니라 **모델 선택**이라는 뜻이다. "
            "⚠️ 이것을 '사실은 저평가'로 읽으면 안 된다 - 반대로 "
            "**이 종목의 판정은 가정에 심하게 좌우되며 어떤 방향으로도 "
            "확신할 근거가 없다**는 뜻이다(v3.51 robust=False 종목). "
            "2026-08-16 모델선택 연구가 '이론 기준이 실제 선택을 전혀 "
            "분리하지 못한다'며 규칙화를 REJECT한 축이 바로 이것이다."
        ),
        "known_limitation": (
            "guidance_30.00은 회사의 **1개년 예측**이고 엔진 Realistic Growth는 "
            "n≈12년 개념이라 기간이 다르다. 두 값을 같은 자리에 대입하는 것은 "
            "근사이며, ROP처럼 다년 실현 오가닉 실적으로 검증된 대체가 아니다 - "
            "그래서 공식 판정으로 승격하지 않는다(KEYS 크로스체크가 확립한 기준). "
            "size_cap_23.00도 Credit Suisse HOLT base rate에서 나온 역사적 "
            "분포의 상한일 뿐 이 회사의 예측치가 아니다."
        ),
    }
    os.makedirs("reports", exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"\nsaved: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
