"""
PTC 시나리오 크로스체크 - 2026-09-04. **보유 최대비중(38.4%) 종목 정밀 점검.**

공식 판정(ledger/PTC_2026-09-04.json, Gap +4.08%p "적정가/경계선")은 그대로
두고, 판정을 흔들 수 있는 두 축을 병기한다 - `is_insurer`/`sbc_cross_check`/
ROP 크로스체크와 동일한 "병기, 자동판정 안 함" 원칙.

Implied Growth는 시가총액·FCF0·r·n에서만 나오고 **Realistic Growth 입력과
완전히 독립**이므로, RG만 갈아끼워 Gap을 재계산하는 것이 수학적으로 정확하다
(ROP·KEYS 크로스체크가 쓴 것과 같은 방법).

## 축 1: 회사 자신의 ARR 성장률(GAAP 매출 CAGR 대신)

엔진은 GAAP 매출 CAGR 가중평균(11.39%)을 쓰지만, PTC는 ASC 606상 온프레미스
라이선스를 **선인식**해 GAAP 매출이 계약 타이밍에 출렁이며 회사 스스로
ARR·FCF로만 가이던스를 준다. 매각분 제외 ARR 성장률(CC): FY26 가이던스
7.5~9.5%, Q3'26 실적 9.1%.

## 축 2: SBC를 실제 비용으로 차감

FY2025 SBC $2.162억 = FCF의 **25.2%**. 공식 ledger의 `sbc_cross_check`가
이미 SBC차감 Implied Growth를 계산해두었으므로 그 값을 그대로 쓴다.

## 축 3(참고): 구독전환기(FY2015~2016)를 창에 포함한 변형

FY2015~2025 창으로 실행하면 DRS 44.4->56.4, Lynch stalwart->cyclical,
Gap +2.94%p가 된다. **채택하지 않았다** - FY2016 매출감소는 경기순환이
아니라 영구라이선스->구독 전환의 회계적 착시임이 SEC 공시로 확인됐다
(docstring of analyze_ptc_2026_09_04.py 참고). 다만 "만약 그 해석이
틀렸다면" 시나리오로 수치만 기록해둔다.

실행: python3 scripts/ptc_scenario_crosscheck_2026_09_04.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.expectation_gap_engine import judgment_from_gap

LEDGER = "ledger/PTC_2026-09-04.json"
OUT = "reports/ptc_scenario_crosscheck_2026-09-04.json"

# 회사 자체 ARR 성장률(매각분 제외, 상수통화) - 2026-09-04 WebSearch 확인
ARR_SCENARIOS = {
    "guidance_low_7.5": 0.075,
    "q3_26_actual_9.1": 0.091,
    "guidance_high_9.5": 0.095,
}


def main() -> int:
    d = json.load(open(LEDGER, encoding="utf-8"))
    rg_official = d["growth"]["realistic_growth"]
    ig_official = d["implied_growth"]["value"]
    gap_official = d["expectation_gap"]
    sbc = d["sbc_cross_check"]
    ig_sbc = sbc["implied_growth_sbc_adjusted"]

    rows = []

    # ── 공식 판정(기준선) ────────────────────────────────────────────────
    rows.append({
        "scenario": "공식(GAAP 매출 CAGR, SBC 미차감)",
        "realistic_growth": rg_official,
        "implied_growth": ig_official,
        "gap": gap_official,
        "judgment": judgment_from_gap(gap_official),
        "note": "ledger/PTC_2026-09-04.json 그대로",
    })

    # ── 축 2 단독: SBC 차감(성장률은 공식 그대로) ────────────────────────
    rows.append({
        "scenario": "SBC 차감(성장률은 GAAP CAGR 그대로)",
        "realistic_growth": rg_official,
        "implied_growth": ig_sbc,
        "gap": sbc["gap_sbc_adjusted"],
        "judgment": sbc["judgment_sbc_adjusted"],
        "note": f"SBC/FCF {sbc['sbc_to_fcf_pct']*100:.1f}%",
    })

    # ── 축 1 단독 + 축1×축2 결합 ─────────────────────────────────────────
    for label, rg in ARR_SCENARIOS.items():
        gap = rg - ig_official
        rows.append({
            "scenario": f"ARR성장 {label}",
            "realistic_growth": rg,
            "implied_growth": ig_official,
            "gap": gap,
            "judgment": judgment_from_gap(gap),
            "note": "회사 자체 지표(매각분 제외 CC), SBC 미차감",
        })
        gap_both = rg - ig_sbc
        rows.append({
            "scenario": f"ARR성장 {label} + SBC차감",
            "realistic_growth": rg,
            "implied_growth": ig_sbc,
            "gap": gap_both,
            "judgment": judgment_from_gap(gap_both),
            "note": "가장 보수적인 조합",
        })

    # ── 축 3(참고): 구독전환기 포함 창 ───────────────────────────────────
    rows.append({
        "scenario": "[미채택 참고] FY2015~2025 창(구독전환기 포함)",
        "realistic_growth": 0.10878436127881694,
        "implied_growth": 0.07942199707031249,
        "gap": 0.02936236420850445,
        "judgment": "적정가/경계선",
        "note": "DRS 56.40(+12.0), Lynch cyclical - FY2016 감소가 회계전환 "
                "착시임이 확인돼 채택하지 않음. 실행 실측값 기록.",
    })

    flips = [r for r in rows if r["judgment"] != rows[0]["judgment"]]

    print(f"{'시나리오':44}{'RG':>8}{'IG':>8}{'Gap':>9}  판정")
    for r in rows:
        print(f"{r['scenario']:44}{r['realistic_growth']*100:>7.2f}%"
              f"{r['implied_growth']*100:>7.2f}%{r['gap']*100:>+8.2f}%p  {r['judgment']}")
    print()
    print(f"공식 판정과 다른 시나리오: {len(flips)}건")
    for r in flips:
        print(f"  - {r['scenario']}: {r['judgment']}")

    payload = {
        "ticker": "PTC",
        "as_of": "2026-09-04",
        "purpose": "보유 포트폴리오 최대비중(38.4%) 종목의 판정 취약성 점검",
        "official_ledger": LEDGER,
        "affects_official_judgment": False,
        "scenarios": rows,
        "n_scenarios_differing_from_official": len(flips),
        "known_limitation": (
            "ARR과 GAAP 매출은 정의가 다른 지표다(ARR은 영구라이선스·전문서비스 "
            "제외). 두 값을 같은 자리에 대입하는 것은 근사이며, ROP처럼 "
            "다년 실현 오가닉 실적으로 검증된 대체가 아니다 - 그래서 공식 "
            "판정으로 승격하지 않는다(KEYS 선례)."
        ),
    }
    os.makedirs("reports", exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"\nsaved: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
