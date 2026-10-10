"""
QSI v1 파일럿 — ACGL(보험 변형) · DLO(표준) · PTC(표준), as_of 2026-10-06

목적은 **형식 시험**이다: 질문 은행·근거 계약·봉인이 실제 조사를 담는지 본다. 이 조사가
옳다는 검증이 아니다.

⚠️ 원칙
  - 인용은 이번 세션에서 **직접 조회한 출처만** 쓴다(SEC 원문/companyfacts). 인용문(quote)은
    조회한 원문과 글자 그대로 일치하는 것만 넣었고 작성 시 일치를 확인했다.
  - 확인하지 못한 질문은 추측하지 않고 `unknown` + 사유로 남긴다.
  - 기존 thesis·ledger·공식 판정은 수정하지 않는다(병기).
  - 숫자 근거 중 SBC/FCF의 분모(fcf0)는 IRS ledger 값이다(같은 10-K의 OCF에서 파생).

실행: python -m scripts.qsi_pilot_2026_10_06 [--dry-run]
"""

import sys
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from engine import qualitative_input as Q  # noqa: E402

AS_OF = "2026-10-06"
FACTS = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"


def sec(document, location, url, quote=""):
    return {"source_key": "sec_edgar", "document": document, "location": location,
            "observed_date": AS_OF, "url": url, "quote": quote}


def ev(summary, citation, direction="supports", metric=None, value=None, note=""):
    return {"summary": summary, "direction": direction, "verification": "VERIFIED_PRIMARY",
            "confidence": "HIGH", "citation": citation, "metric": metric, "value": value,
            "note": note}


def claim(cid, statement, materiality, *evs):
    return {"claim_id": cid, "statement": statement, "materiality": materiality,
            "evidence": list(evs)}


def ans(qid, answer, *claim_ids, note=""):
    return {"qid": qid, "status": "answered", "answer": answer,
            "claim_ids": list(claim_ids), "note": note}


def unk(qid, note):
    return {"qid": qid, "status": "unknown", "note": note}


def finding(lens, effect, summary, *claim_ids):
    return {"lens": lens, "effect": effect, "summary": summary,
            "claim_ids": list(claim_ids)}


# --- ACGL (insurance 변형) ---------------------------------------------------
def acgl():
    facts = FACTS.format(cik="0000947484")
    k10 = "ACGL 10-K FY2025 (filed 2026-02-26, acc 0000947484-26-000017)"
    proxy = "ACGL DEF 14A (filed 2026-03-24, acc 0000947484-26-000038)"
    purl = "https://www.sec.gov/Archives/edgar/data/947484/000094748426000038/acgl-20260324.htm"
    return {
        "entity": "ACGL", "as_of": AS_OF, "lens_set": "insurance",
        "price_at_analysis": 94.36, "currency": "USD",
        "claims": [
            claim("ACGL.CHAIR", "이사회 의장과 CEO가 분리돼 있다", "MEDIUM", ev(
                "이사회가 의장·CEO 분리를 결정했고 의장(Pasquesi)은 독립이사",
                sec(proxy, "Corporate Governance — Board Leadership Structure", purl,
                    "The Board has determined that a split in the role of Chair of the Board "
                    "and CEO is appropriate and in the best interests of the Company’s shareholders"))),
            claim("ACGL.SUCC", "CEO 승계 계획을 이사회가 감독한다", "MEDIUM", ev(
                "CEO 승계 감독 책임을 Nominating and Governance Committee에 위임",
                sec(proxy, "Corporate Governance — succession planning", purl,
                    "Our Board has delegated primary oversight responsibility for succession "
                    "planning for our CEO to our Nominating and Governance Committee"))),
            claim("ACGL.SBC", "SBC가 FCF 대비 미미하다(2.4%)", "HIGH", ev(
                "FY2025 SBC 148,000,000 USD / fcf0 6,128,000,000 USD",
                sec(k10, "us-gaap:ShareBasedCompensation FY2025 = 148,000,000 USD", facts),
                metric="SBC/FCF", value=0.0242,
                note="분모 fcf0는 IRS ledger 값(같은 10-K의 OCF 6,172,000,000 USD에서 capex 차감)")),
            claim("ACGL.SHARES", "최근 3년 희석주식수가 줄었다(-0.45%)", "HIGH", ev(
                "가중평균 희석주식수 FY2022 377,600,000 -> FY2025 375,900,000",
                sec(k10, "us-gaap:WeightedAverageNumberOfDilutedSharesOutstanding FY2022·FY2025",
                    facts), metric="net_share_change_3y", value=-0.0045,
                note="ACGL은 2022~2025 사이 주식분할이 없다(분할 보정 불필요)")),
            claim("ACGL.RESERVE", "최근 3개 연도 준비금 발전이 유리했다", "HIGH", ev(
                "전기 손해액 조정(prior-year claims expense) FY2023 -538M, FY2024 -507M, "
                "FY2025 -600M USD (음수 = 비용 감소 = 유리한 발전)",
                sec(k10, "us-gaap:SupplementalInformationForPropertyCasualtyInsuranceUnderwriters"
                         "PriorYearClaimsAndClaimsAdjustmentExpense FY2023~FY2025", facts),
                metric="prior_year_claims_expense_usd", value=-600000000.0,
                note="부호 해석(음수=유리)은 보험회계 관행이며 10-K MD&A 문장으로는 대조하지 않았다")),
        ],
        "answers": [
            ans("gov.chair_separated", True, "ACGL.CHAIR"),
            ans("gov.ceo_succession_policy", True, "ACGL.SUCC"),
            unk("gov.dual_class", "투표권 9.9% 상한은 확인했으나 차등의결 주식이 없다는 직접 문장은 못 찾았다"),
            unk("gov.insider_pattern", "Form 4 매매 내역을 조회하지 않았다"),
            unk("gov.material_litigation", "10-K Item 3을 읽지 않았다"),
            ans("dil.sbc_to_fcf_pct", 0.0242, "ACGL.SBC"),
            ans("dil.net_share_change_3y_pct", -0.0045, "ACGL.SHARES"),
            ans("res.reserve_development", "favorable", "ACGL.RESERVE"),
            unk("uw.combined_ratio_pct", "합산비율은 XBRL 태그가 없고 10-K MD&A 원문을 조회하지 않았다"),
            unk("cat.cat_exposure", "대재해 노출·재보험 방어 원문을 조회하지 않았다"),
        ],
        "findings": [
            finding("reserve_adequacy", "strengthens",
                    "3년 연속 유리한 준비금 발전(전기 손해액 -538M/-507M/-600M)", "ACGL.RESERVE"),
            finding("catastrophe_risk", "not_examined", "대재해 노출 원문 미조회"),
            finding("underwriting_discipline", "not_examined", "합산비율 원문 미조회"),
            finding("governance", "neutral",
                    "의장·CEO 분리와 승계 감독은 확인. 내부자 매매·소송·차등의결은 미확인이라 방향 판단 보류"),
            finding("dilution", "strengthens", "SBC/FCF 2.4%, 3년 희석주식수 -0.45%",
                    "ACGL.SBC", "ACGL.SHARES"),
        ],
        "disqualifiers": [],
        "inversion": [
            "대재해 손실이 평활화된 FCF 가정을 깨뜨린다(엔진의 알려진 한계)",
            "보험 플로트 성장이 유기적 성장으로 과대평가됐을 수 있다",
        ],
        "confidence_recommendation": None,
    }


# --- DLO (표준) --------------------------------------------------------------
def dlo():
    facts = FACTS.format(cik="0001846832")
    f20 = "DLO 20-F FY2025 (filed 2026-03-18, acc 0002070979-26-000113)"
    return {
        "entity": "DLO", "as_of": AS_OF, "lens_set": "standard",
        "price_at_analysis": 14.52, "currency": "USD",
        "claims": [
            claim("DLO.DUAL", "Class B 주식이 5표를 갖는 차등의결 구조다", "HIGH", ev(
                "Class B 5표 vs Class A 1표(경제적 권리는 동일, 전환권·비례유지권만 상이)",
                sec(f20, "Item 7 Major Shareholders — voting rights note",
                    "https://www.sec.gov/Archives/edgar/data/1846832/000207097926000113/dlo-20251231.htm",
                    "holders of Class B common shares are entitled to five votes per share, "
                    "whereas holders of our Class A common shares are entitled to one vote per share"))),
            claim("DLO.SBC", "SBC가 FCF 대비 낮다(5.8%)", "HIGH", ev(
                "FY2025 SBC 24,136,000 USD / fcf0 413,175,000 USD",
                sec(f20, "ifrs-full:AdjustmentsForSharebasedPayments FY2025 = 24,136,000 USD", facts),
                metric="SBC/FCF", value=0.0584,
                note="분모 fcf0는 IRS ledger 값(같은 20-F의 OCF 415,457,000 USD에서 capex 차감)")),
            claim("DLO.SHARES", "최근 3년 희석주식수가 줄었다(-3.64%)", "HIGH", ev(
                "조정 가중평균주식수 FY2022 313,138,646 -> FY2025 301,742,797",
                sec(f20, "ifrs-full:AdjustedWeightedAverageShares FY2022·FY2025", facts),
                metric="net_share_change_3y", value=-0.0364,
                note="2021-10 IPO 이후라 FY2022 이후 구간은 상장 전 우선주 기준 문제가 없다")),
        ],
        "answers": [
            ans("gov.dual_class", True, "DLO.DUAL"),
            unk("gov.chair_separated", "의장 선임 규정은 확인했으나 현 의장과 CEO의 겸직 여부를 직접 확인하지 못했다"),
            unk("gov.insider_pattern", "20-F 발행사라 Form 4 대상이 아니다 — 대체 공시를 확인하지 못했다"),
            unk("gov.material_litigation", "20-F Item 8을 읽지 않았다"),
            ans("dil.sbc_to_fcf_pct", 0.0584, "DLO.SBC"),
            ans("dil.net_share_change_3y_pct", -0.0364, "DLO.SHARES"),
        ],
        "findings": [
            finding("governance", "weakens",
                    "Class B 5표 구조로 창업자 의결권이 경제 지분보다 크다. 의장·소송은 미확인",
                    "DLO.DUAL"),
            finding("capital_allocation", "not_examined", "자사주·M&A 원문 미조회"),
            finding("accounting_quality", "not_examined", "재작성·가이던스 이력 미조회"),
            finding("dilution", "strengthens", "SBC/FCF 5.8%, 3년 주식수 -3.64%",
                    "DLO.SBC", "DLO.SHARES"),
            finding("competitive_landscape", "not_examined", "경쟁 구도는 이번 파일럿에서 조사하지 않았다"),
        ],
        "disqualifiers": [],
        "inversion": [
            "테이크레이트가 이미 낮아 추가 압축 여지가 작고, 대형 가맹점 가격구간 이동이 반복되면 구조적 경쟁압력이다",
            "신흥국 통화·자본통제·규제 리스크가 상시 존재한다",
        ],
        "confidence_recommendation": None,
    }


# --- PTC (표준) --------------------------------------------------------------
def ptc():
    facts = FACTS.format(cik="0000857005")
    k10 = "PTC 10-K FY2025 (filed 2025-11-21, acc 0001193125-25-291326)"
    proxy = "PTC DEF 14A (filed 2025-12-23, acc 0001104659-25-124170)"
    purl = "https://www.sec.gov/Archives/edgar/data/857005/000110465925124170/tm2526581-1_def14a.htm"
    k8 = "PTC 8-K (filed 2026-10-05, acc 0001193125-26-413124, Items 1.01/7.01/9.01)"
    k8url = "https://www.sec.gov/Archives/edgar/data/857005/000119312526413124/d174191d8k.htm"
    return {
        "entity": "PTC", "as_of": AS_OF, "lens_set": "standard",
        # 2026-10-05 종가. 인수 발표(+33.5%) 이후 가격이다 — 인수 전 가격이 아니다.
        "price_at_analysis": 192.26, "currency": "USD",
        "claims": [
            claim("PTC.DEAL", "PTC는 Schneider Electric의 확정 현금 인수 대상이다", "HIGH", ev(
                "2026-10-04 합병계약 체결, 보통주당 $205 현금, 해지수수료 $700M",
                sec(k8, "Item 1.01 Agreement and Plan of Merger", k8url,
                    "will be converted into the right to receive $205 in cash, without interest"),
                metric="merger_consideration_usd", value=205.0,
                note="해지수수료: 'the Company will be required to pay Schneider Electric a "
                     "termination fee of $700 million'. 종결은 주주 승인·규제 승인 조건부")),
            claim("PTC.CHAIR", "이사회 의장이 독립이사이며 CEO와 분리돼 있다", "MEDIUM", ev(
                "독립 이사회 의장(Janice Chaffin)이 이사회를 이끈다",
                sec(proxy, "Proposal 1 — Board Leadership Structure", purl,
                    "Our Board is led by an independent Chair."))),
            claim("PTC.SUCC", "CEO 승계 계획이 유지되도록 위원회가 보장한다", "MEDIUM", ev(
                "Corporate Governance Committee의 책임에 CEO 승계 계획 유지가 포함",
                sec(proxy, "Corporate Governance — Committee responsibilities", purl,
                    "Ensures a CEO succession plan is maintained to ensure continuity of "
                    "leadership for PTC."))),
            claim("PTC.SBC", "SBC/FCF가 25%로 높은 편이다", "HIGH", ev(
                "FY2025 SBC 216,205,000 USD / fcf0 856,688,000 USD",
                sec(k10, "us-gaap:ShareBasedCompensation FY2025 = 216,205,000 USD", facts),
                metric="SBC/FCF", value=0.2524,
                note="분모 fcf0는 IRS ledger 값(같은 10-K의 OCF 867,696,000 USD에서 capex 차감)")),
            claim("PTC.SHARES", "최근 3년 희석주식수가 늘었다(+2.15%)", "HIGH", ev(
                "가중평균 희석주식수 FY2022 118,233,000 -> FY2025 120,777,000",
                sec(k10, "us-gaap:WeightedAverageNumberOfDilutedSharesOutstanding FY2022·FY2025",
                    facts), direction="contradicts", metric="net_share_change_3y", value=0.0215,
                note="희석 가중평균은 주가에 따라 변하는 희석 증권 효과를 포함한다. 기본주식수와 "
                     "매입액은 확인하지 않았다")),
        ],
        "answers": [
            ans("gov.chair_separated", True, "PTC.CHAIR"),
            ans("gov.ceo_succession_policy", True, "PTC.SUCC"),
            unk("gov.dual_class", "프록시에서 단일 클래스 여부를 직접 확인하지 못했다"),
            unk("gov.insider_pattern", "Form 4 매매 내역을 조회하지 않았다"),
            unk("gov.material_litigation", "합병 관련 주주 소송 가능성은 있으나 현재 확인한 소송이 없다"),
            ans("dil.sbc_to_fcf_pct", 0.2524, "PTC.SBC"),
            ans("dil.net_share_change_3y_pct", 0.0215, "PTC.SHARES"),
            unk("cap.buyback_effect",
                "모순 미해소: 2026-08-04 경량검증은 '자사주매입이 SBC의 6~7배(anti-dilutive)'라 했으나 "
                "희석 가중평균 주식수는 3년 +2.15%다. 기본주식수·매입액 원문을 아직 대조하지 않았다"),
        ],
        "findings": [
            finding("governance", "neutral",
                    "독립 의장과 CEO 승계 계획은 확인. 차등의결·내부자·소송은 미확인"),
            finding("capital_allocation", "not_examined",
                    "자사주 효과에 모순이 있어 판단 보류(cap.buyback_effect 참조)"),
            finding("accounting_quality", "not_examined", "재작성·가이던스 이력 미조회"),
            finding("dilution", "weakens",
                    "SBC/FCF 25%이고 3년 희석주식수 +2.15%. 엔진은 희석을 모형화하지 않는다",
                    "PTC.SBC", "PTC.SHARES"),
            finding("competitive_landscape", "not_examined", "경쟁 구도는 이번 파일럿에서 조사하지 않았다"),
        ],
        "disqualifiers": [{
            "code": "PENDING_ACQUISITION",
            "statement": "확정된 현금 인수 대상이다. 주가는 독립적 성장 전망이 아니라 딜 조건·성사 "
                         "확률을 반영하므로 Implied Growth 역산이 '시장의 성장 기대'를 뜻하지 않는다 "
                         "(LNTH 제외와 같은 이유)",
            "claim_ids": ["PTC.DEAL"]}],
        "inversion": [
            "딜이 무산되면(주주 반대·규제 불허) 주가가 독립 가치로 되돌아가며 종전 GAAP-ARR 괴리·가이던스 리스크가 재부각된다",
            "GAAP 매출·ARR 괴리가 반복되는 구조(ASC 606 라이선스 인식 타이밍)",
        ],
        "confidence_recommendation": None,
    }


def main(dry_run=False) -> int:
    for build in (acgl, dlo, ptc):
        rec = Q.build_record(build())
        c = rec["coverage"]
        print(f"{rec['entity']}: 답 {c['n_answered']}/{c['n_questions']}, "
              f"미조사 축 {c['unexamined_lenses']}, 해시 {rec['sealed_core_hash'][:10]}")
        if not dry_run:
            print("  ->", os.path.relpath(Q.save_record(rec), ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main("--dry-run" in sys.argv))
