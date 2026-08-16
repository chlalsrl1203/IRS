"""
모델선택 민감도 - 등급·매수유니버스 수준 (2026-08-16).

기존 v3.51 gap_range_over_assumptions()는 **judgment**(3단계) 수준에서만 모델선택
취약성을 봤다. 그런데 실제 투자결정을 만드는 건 judgment가 아니라
judgment_grade(S/A/B/C/D/F)와 그로부터 나오는 매수 유니버스(grade in S/A)다.
BSX 스크리너 사건이 확립했듯 **가장 나쁜 오류는 거짓 탈락**이다 - 배제된 종목은
아무도 다시 보지 않기 때문이다. 이 스크립트는 "모델을 반대로 골랐다면 매수
유니버스가 어떻게 달라졌는가"에 답한다.

새 밸류에이션 로직 0줄 - engine/gap_analysis.py의 _implied_growth_at와
engine/expectation_gap_engine.py의 judgment/grade 함수를 그대로 재사용한다.

⚠️ 이 리포트는 **어느 모델이 옳은지 판정하지 않는다.** 34종목 실측으로 확인된
바에 따르면 관측 가능한 성장프로파일(RG - g_terminal)은 실제 모델선택을 전혀
분리하지 못하며(두 집단 구간이 거의 완전히 겹침), 따라서 이 저장소에는 어느
쪽이 옳은지 판정할 근거가 없다. 병기만 한다.
"""
import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.gap_analysis import _implied_growth_at  # noqa: E402
from engine.expectation_gap_engine import (  # noqa: E402
    judgment_from_gap,
    judgment_grade_from_gap,
)

# 사유가 "과거 기록을 답습했다"는 뜻인지 탐지한다. "대조할 과거 기록이 없다"
# (정반대 의미)를 잘못 잡지 않도록 '기록을 실제로 채택한' 표현만 매칭한다.
PRIOR_RECORD_RE = re.compile(r"(과거 큐\d+ 기록|기존 [A-Z]{2,6} 기록|기존 v3\.\d+ 기록)")

BUY_UNIVERSE_GRADES = ("S", "A")  # scripts/build_buylist_2026_08_03.py와 동일 기준


def _grade(gap):
    g = judgment_grade_from_gap(gap)
    return g["grade"] if isinstance(g, dict) else g


def analyze(ledger):
    chosen = ledger["implied_growth"]["model_used"]
    other = "single_stage" if chosen == "two_stage" else "two_stage"
    rg = ledger["growth"]["realistic_growth"]
    dc = ledger["discount_rate"]
    mc, fcf0 = ledger["inputs"]["market_cap"], ledger["derived"]["fcf0"]

    ig_alt = _implied_growth_at(mc, fcf0, dc["r"], dc["n"], dc["g_terminal"], other)
    gap_official = ledger["expectation_gap"]
    gap_alt = rg - ig_alt

    g_off, g_alt = _grade(gap_official), _grade(gap_alt)
    in_off = g_off in BUY_UNIVERSE_GRADES
    in_alt = g_alt in BUY_UNIVERSE_GRADES

    reason = ledger["implied_growth"].get("model_choice_reason", "") or ""
    return {
        "ticker": ledger["meta"]["ticker"],
        "model_chosen": chosen,
        "model_alternative": other,
        "gap_official": gap_official,
        "gap_alternative": gap_alt,
        "judgment_official": ledger["judgment"],
        "judgment_alternative": judgment_from_gap(gap_alt),
        "grade_official": g_off,
        "grade_alternative": g_alt,
        "judgment_depends_on_model": ledger["judgment"] != judgment_from_gap(gap_alt),
        "grade_depends_on_model": g_off != g_alt,
        # 결정적 항목: 매수 유니버스 편입 여부가 모델선택에 달려 있는가
        "buy_universe_depends_on_model": in_off != in_alt,
        "universe_direction": (
            "대안모델이면 진입(현재 거짓탈락 가능)" if (in_alt and not in_off)
            else "대안모델이면 이탈(현재 거짓편입 가능)" if (in_off and not in_alt)
            else None
        ),
        # 선택 근거가 경제논리인가, 과거기록 답습인가
        "reason_is_prior_record": bool(PRIOR_RECORD_RE.search(reason)),
        "model_choice_reason": reason,
    }


def main():
    results = [analyze(json.load(open(p, encoding="utf-8")))
               for p in sorted(glob.glob("ledger/*.json"))]

    j_dep = [r for r in results if r["judgment_depends_on_model"]]
    g_dep = [r for r in results if r["grade_depends_on_model"]]
    u_dep = [r for r in results if r["buy_universe_depends_on_model"]]
    prior = [r for r in results if r["reason_is_prior_record"]]
    both = [r for r in results if r["reason_is_prior_record"] and r["judgment_depends_on_model"]]

    print(f"대상 {len(results)}종목")
    print(f"  판정이 모델선택에 의존      : {len(j_dep)}  {[r['ticker'] for r in j_dep]}")
    print(f"  등급이 모델선택에 의존      : {len(g_dep)}  {[r['ticker'] for r in g_dep]}")
    print(f"  매수유니버스가 모델선택에 의존: {len(u_dep)}  {[r['ticker'] for r in u_dep]}")
    print(f"  선택근거가 과거기록 답습    : {len(prior)}  {[r['ticker'] for r in prior]}")
    print(f"  >>> 둘 다 해당(가장 취약)   : {len(both)}  {[r['ticker'] for r in both]}")
    print()
    if u_dep:
        print("=== 매수 유니버스가 모델선택에 달려 있는 종목 ===")
        for r in u_dep:
            print(f"  {r['ticker']:6s} {r['grade_official']}({r['gap_official']*100:+.2f}%p)"
                  f" -> {r['grade_alternative']}({r['gap_alternative']*100:+.2f}%p)"
                  f"  {r['universe_direction']}")

    report = {
        "generated_at": "2026-08-16",
        "method": "모델선택만 교체하고 나머지 입력은 전부 고정. 새 밸류에이션 로직 없음.",
        "buy_universe_grades": list(BUY_UNIVERSE_GRADES),
        "n_tickers": len(results),
        "n_judgment_dependent": len(j_dep),
        "n_grade_dependent": len(g_dep),
        "n_buy_universe_dependent": len(u_dep),
        "n_reason_is_prior_record": len(prior),
        "tickers_prior_record_and_judgment_dependent": [r["ticker"] for r in both],
        "caveat": (
            "어느 모델이 옳은지 판정하지 않는다. 34종목 실측상 RG-g_terminal 성장"
            "프로파일이 두 모델 선택집단을 분리하지 못해(구간 거의 완전 중첩) "
            "이 저장소에는 판정 근거가 없다. 병기만 한다."
        ),
        "results": results,
    }
    out = "reports/model_choice_sensitivity_2026-08-16.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n저장: {out}")


if __name__ == "__main__":
    main()
