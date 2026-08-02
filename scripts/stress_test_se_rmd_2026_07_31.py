"""
SE / RMD 심층 강건성 스트레스테스트 - 2026-07-31.

경위: "더 깊이 분석" 요청. 두 종목 모두 강건성점검(expectation_gap_sensitivity_
check)이 flip=False로 통과했지만, 이 내장 체크는 ERP를 완전히 0으로 빼는
단일 시나리오 하나뿐이다. 더 현실적인 "얼마나 나빠져야 판정이 뒤집히는가"를
직접 계산한다.

방법 1 - DRS 최악값(=100) 가정시 Gap: erp_from_drs()는 DRS 0~100을 ERP
5~8%에 매핑하는 구조적 상한이 있다(base_erp=0.05, max_add=0.03) - 즉 DRS를
아무리 나쁘게 잡아도 ERP는 8%를 못 넘는다. 이 상한에서의 Gap을 계산하면
"경쟁강도・레버리지・경기민감도가 아무리 나빠도 견디는가"를 순수하게 본다.

방법 2 - 성장률 반토막 + DRS=100 동시가정: 방법 1은 Realistic Growth를
그대로 둔 채 할인율만 움직인다. 실제 악재(GLP-1 수요파괴, TikTok Shop
점유율 추가잠식)는 할인율뿐 아니라 성장률 자체도 깎아먹는다 - 그래서
Realistic Growth를 절반으로 낮추고 DRS=100을 동시에 적용하는 결합
시나리오도 계산한다. 이게 실질적인 "얼마나 나빠져야 뒤집히는가"에 더
가까운 답이다.

실행: python3 scripts/stress_test_se_rmd_2026_07_31.py
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.expectation_gap_engine import erp_from_drs, implied_growth_two_stage

RF = 0.0447
R_MAX = RF + erp_from_drs(100)  # DRS=100 최악값에서의 r


def load_ledger(path):
    d = json.load(open(path))
    return {
        "fcf0": d["derived"]["fcf0"],
        "market_cap": d["inputs"]["market_cap"],
        "n": d["discount_rate"]["n"],
        "g_terminal": d["discount_rate"]["g_terminal"],
        "r_actual": d["discount_rate"]["r"],
        "realistic_growth": d["growth"]["realistic_growth"],
        "gap_actual": d["expectation_gap"],
    }


def stress(name, ledger_path):
    x = load_ledger(ledger_path)
    print(f"\n{'='*90}\n{name}\n{'='*90}")
    print(f"  실제 판정: Realistic Growth {x['realistic_growth']*100:.2f}% / "
          f"r {x['r_actual']*100:.2f}% / Gap {x['gap_actual']*100:+.2f}%p")

    # 방법 1: DRS=100 (ERP 최댓값 8%) 가정, 성장률은 그대로
    g_worst1, _, _ = implied_growth_two_stage(
        x["market_cap"], x["fcf0"], R_MAX, x["n"], x["g_terminal"])
    gap1 = x["realistic_growth"] - g_worst1
    print(f"  [방법1] DRS=100(ERP상한 8%, r={R_MAX*100:.2f}%) 가정, 성장률 불변:")
    print(f"          Implied Growth {g_worst1*100:.2f}% -> Gap {gap1*100:+.2f}%p "
          f"-> {'저평가 유지' if gap1 > 0 else '판정 뒤집힘'}")

    # 방법 2: 방법1 + 성장률 반토막
    rg_half = x["realistic_growth"] / 2
    gap2 = rg_half - g_worst1
    print(f"  [방법2] 방법1 + Realistic Growth 반토막({rg_half*100:.2f}%) 동시가정:")
    print(f"          Gap {gap2*100:+.2f}%p -> {'저평가 유지' if gap2 > 0 else '판정 뒤집힘(과대평가 전환)'}")

    return {"gap_method1": gap1, "gap_method2": gap2}


if __name__ == "__main__":
    r1 = stress("Sea Limited(SE)", "ledger/SE_2026-08-02.json")
    r2 = stress("ResMed(RMD)", "ledger/RMD_2026-08-02.json")

    print(f"\n{'='*90}\n요약\n{'='*90}")
    print(f"  SE : 결합 스트레스(방법2)에서도 Gap {r1['gap_method2']*100:+.2f}%p로 저평가 유지 - 매우 견고")
    print(f"  RMD: 결합 스트레스(방법2)에서 Gap {r2['gap_method2']*100:+.2f}%p로 판정 뒤집힘 - 마진 얇음")
    print("\n  ⚠️ 이 스트레스테스트는 '만약 이렇게 나빠진다면'을 계산한 것이지,")
    print("     실제로 그렇게 나빠질 확률을 추정한 것이 아니다. RMD의 경우 최근 실적")
    print("     (FY2026 Q3 매출 +11%, 마진 확대)이 이 비관 시나리오와 반대 방향으로")
    print("     움직이고 있다는 점도 함께 볼 것(본문 CHANGELOG 참고).")
