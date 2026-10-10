"""
QSI 심화 2차 — 소송 질문(gov.material_litigation) TTD·MNDY (as_of 2026-10-10)

규칙은 v3.94와 동일하다: **회사 자기 진술만** 쓴다(중요성 한정이 있으면 immaterial, 없으면 단정하지 않음).
진행 중인 증권집단소송이 있다는 사실은 claim으로 병기하되, 회사가 '중대한 악영향 가능성 낮음'이라고
진술하므로 답은 immaterial이다. **심각도를 우리가 판단한 것이 아니다.**
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from engine import qualitative_input as Q  # noqa: E402
from scripts import qsi_rollout_2026_10_06 as R  # noqa: E402
from scripts.qsi_deep_claims_2026_10_10 import AS_OF, E  # noqa: E402
from scripts.qsi_sec_events import _claim, merge  # noqa: E402


def main():
    out = {}
    _, u, _ = R.doc_of("TTD", "10-K")
    d = "TTD 10-K (filed 2026-02-27)"
    out["TTD"] = ([_claim("TTD.LIT", "증권집단소송(2025) 진행·CEO 성과옵션 파생소송은 기각 확정, 회사는 중대한 악영향 가능성이 낮다고 진술", "HIGH",
                          E("회사 진술", d, "Note — Litigation", u,
                            "management does not believe it is probable that any of these proceedings or other claims will have a material adverse effect",
                            note="회사 진술이며 우리가 심각도를 평가한 것이 아니다"),
                          E("2025년 증권집단소송", d, "Risk Factors", u,
                            "securities class action litigation was filed against us following a drop in our stock price"),
                          E("CEO 성과옵션 파생소송 종결", d, "Note — Litigation", u,
                            "the Delaware Supreme Court issued an order affirming the lower court ruling dismissing the action with prejudice"))],
                  [{"qid": "gov.material_litigation", "status": "answered", "answer": "immaterial",
                    "claim_ids": ["TTD.LIT"],
                    "note": "회사 자기 진술 기준(v3.94 규칙). 2025년 증권집단소송 진행 중이라는 사실은 claim에 병기"}])
    _, u, _ = R.doc_of("MNDY", "20-F")
    d = "MNDY 20-F (filed 2026-03-13)"
    out["MNDY"] = ([_claim("MNDY.LIT", "2026-03-10 제기된 증권집단소송(가이던스 관련) 초기 단계, 회사는 중대한 영향 가능성 낮다고 진술", "HIGH",
                           E("진행 상황", d, "Legal proceedings", u, "The case is currently in a preliminary stage"),
                           E("회사 진술", d, "Legal proceedings", u,
                             "we do not believe that any of these matters are likely to have a material impact on our financial condition, results, or operations",
                             note="회사 진술이며 우리가 심각도를 평가한 것이 아니다"))],
                   [{"qid": "gov.material_litigation", "status": "answered", "answer": "immaterial",
                     "claim_ids": ["MNDY.LIT"],
                     "note": "회사 자기 진술 기준. 소송 내용은 '가이던스 관련 허위·과장 주장'이라 성장 서사와 직결되므로 결과를 추적할 것"}])
    for t, (claims, answers) in out.items():
        prior = Q.latest_record(t)
        findings = [{"lens": "governance", "effect": "neutral", "claim_ids": [claims[0]["claim_id"]],
                     "summary": "진행 중 증권집단소송과 회사의 중요성 진술을 병기"}]
        core, _ = merge(prior, claims, answers, findings, AS_OF)
        rec = Q.build_record(core)
        print(t, prior["coverage"]["n_answered"], "->", rec["coverage"]["n_answered"])
        print("  ->", os.path.relpath(Q.save_record(rec, supersedes=prior["sealed_core_hash"]), ROOT))


if __name__ == "__main__":
    main()
