"""
QSI 기초 봉인 — S등급 10종목 중 정성 기록이 없던 PINS·TTD (as_of 2026-10-10)

qsi_rollout_2026_10_06의 부품(인용 원문 대조, SBC·희석주식수·자사주 자동 산출)을 그대로 재사용한다.
이 스크립트가 추가하는 것은 두 종목의 지배구조 사실(의결권·의장·승계)뿐이다. 모든 quote는
실행 시 SEC 원문과 글자 단위로 대조된다. 판정·비중·ledger는 건드리지 않는다.

TTD의 최신 DEF 14A는 정기 총회가 아니라 **2026-10-19 특별총회**(스톡옵션 재가격 안건)다.
정기 총회 위임장의 의장·승계 문장은 이 문서에 없으므로 TTD는 승계를 unknown으로 둔다.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from engine import qualitative_input as Q  # noqa: E402
from scripts import qsi_rollout_2026_10_06 as R  # noqa: E402

AS_OF = "2026-10-10"
P, K = "DEF 14A", "10-K"

GOV = {
    "PINS": ("standard", K, P, [
        ("gov.dual_class", True, "Class B 주식이 주당 20표를 갖는다", P,
         "Proxy — voting rights",
         "each share of our Class B common stock entitled to 20 votes per share", "HIGH",
         "경제적 권리는 동일(투표권만 상이)로 보이나 문서에서 직접 대조하지 않았다"),
        ("gov.chair_separated", True, "의장은 CEO와 다른 비상임(Non-Executive) 의장이다", P,
         "Board leadership", "Benjamin Silbermann Non-Executive Chair", "MEDIUM",
         "공동창업자가 비상임 의장 — 독립이사 여부와는 별개(선임 독립이사는 Andrea Wishom)"),
        ("gov.ceo_succession_policy", True, "핵심 임원 승계 계획을 매년 검토한다", P,
         "Governance highlights", "annual review of succession plans for key officers", "MEDIUM",
         "CEO를 명시하지 않고 '핵심 임원'으로 쓴다 — 약한 증거"),
    ]),
    "TTD": ("standard", K, P, [
        ("gov.dual_class", True, "Class B 주식이 주당 10표를 갖는다", P,
         "Special meeting proxy — voting",
         "each share of Class B common stock is entitled to ten votes on each proposal", "HIGH",
         "특별총회 위임장 문장이다. 경제적 권리 동일 여부는 직접 대조하지 않았다"),
        ("gov.chair_separated", False, "Jeff Green이 의장과 CEO를 겸한다", P,
         "Special meeting proxy — signature", "Jeff T. Green Chairman and Chief Executive Officer",
         "MEDIUM", ""),
    ]),
}


def main():
    R.AS_OF = AS_OF
    R.GOV.update(GOV)
    for t in GOV:
        rec = Q.build_record(R.build(t))
        c = rec["coverage"]
        print(f"{t:5} 답 {c['n_answered']:>2}/{c['n_questions']:<2} 해시 {rec['sealed_core_hash'][:10]}")
        print("      ->", os.path.relpath(Q.save_record(rec), ROOT))


if __name__ == "__main__":
    main()
