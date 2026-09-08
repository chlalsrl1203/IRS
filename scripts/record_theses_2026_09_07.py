"""
2026-09-07 - "우선순위 2" 실행: 확신 포트폴리오 상위 보유종목에 실제로
`engine/thesis.py`를 건다.

## 왜 이 세 종목인가

v3.82 포트폴리오 검토(2026-09-05)와 확신 포트폴리오(2026-09-05) 양쪽에서
동시에 상위권으로 잡힌 종목 중, 실제 `portfolio/holdings.json` 보유종목과
겹치는 ACGL·DLO(둘 다 실보유) + 확신 포트폴리오 3위 PGR(미보유, S등급)을
골랐다. 지금까지 이 세 종목은 Gap·등급만으로 자본 배분에 반영돼 있었고
`record_decision()`의 6관문을 거친 적이 단 한 번도 없었다 - 이 스크립트가
그 첫 사례다.

## 무엇을 새로 만들지 않았는가

밸류에이션 로직 0줄. ledger에 이미 저장된 Gap/RG/Confidence/
falsification_conditions와 `portfolio/qualitative_overrides.json`의
정성조사 결론을 그대로 인용해 6관문 텍스트를 채운다. thesis.py의
`decide()`가 없다는 설계(§5)를 그대로 따라 액션은 여기서 사람(나)이
직접 고른다:
  - ACGL·DLO: 이미 `portfolio/holdings.json`에 실보유 중 -> HOLD
  - PGR: 확신 포트폴리오에는 있으나 실보유는 아님 -> WATCH(매수 실행 아님,
    포지션 사이징은 thesis.py의 책임범위 밖 - build_buylist가 담당)
"""
import json
import sys

sys.path.insert(0, ".")

from engine.thesis import (
    InvestmentThesis, build_decision, build_evidence,
    save_thesis, record_decision, record_evidence,
)

TODAY = "2026-09-07"


def ledger(ticker):
    import glob
    path = sorted(glob.glob(f"ledger/{ticker}_*.json"))[-1]
    return path, json.load(open(path))


def overrides(ticker):
    d = json.load(open("portfolio/qualitative_overrides.json"))
    return d["overrides"].get(ticker, {})


# ── ACGL ──────────────────────────────────────────────────────────────
def acgl():
    path, led = ledger("ACGL")
    ov = overrides("ACGL")
    t = InvestmentThesis(
        ticker="ACGL",
        thesis_date=TODAY,
        why_buy=(
            "Gap +24.45%p(S등급, 2026-09-05 재실행) - Realistic Growth 15.74%가 "
            "지속가능성장률(ROE x 유보율 15.46%)과 0.28%p 이내로 근접해 성장추정 "
            "자체가 정합적이다. 준비금 적정성·자본배분(BVPS +22.6%)·거버넌스가 "
            "모두 양호하고 신용등급이 오히려 상향됐다(2026-08-03 정성조사)."
        ),
        market_assumption=(
            "Implied Growth가 두 시나리오 모두 음수(-8.7%~-10.7%, r 포함/제외)로 "
            "역산된다 - 시장가가 이미 매출 역성장을 전제한 밸류에이션에 근접해 "
            "있다는 뜻이다. 보험업 FCF-DCF가 플로트 성장을 유기적 성장으로 "
            "과대평가할 위험(ACGL v3.13 원 경고)을 감안해도, 시장의 가격설정이 "
            "그 위험을 이미 상당폭 반영한 상태로 보인다."
        ),
        irs_view=(
            "엔진의 `insurer_cross_check`가 지속가능성장률과 Realistic Growth의 "
            "괴리를 5%p 경고 임계값 안(0.28%p)으로 확인해줬다는 게 이 종목이 "
            "34종목 중 드물게 '성장 추정 자체는 의심할 이유가 약한' 사례라는 "
            "뜻이다. 재보험 ex-cat 컴바인드레이쇼 소폭 악화는 실재하나 추세로 "
            "확정된 것은 아니다(2분기 연속 소폭)."
        ),
        key_drivers=[
            "재보험·1차보험 언더라이팅 마진 유지",
            "BVPS(주당순자산) 지속 성장(+22.6%, 자본배분 규율의 직접 증거)",
            "신용등급 상향 추세",
        ],
        expected_outcomes=[
            "재보험 ex-cat 컴바인드레이즈가 3분기 연속 악화되지 않고 안정화",
            "대재해(허리케인·산불 등) 관련 대형 단일사건 손실 없이 분기 경과",
        ],
        catalysts=[
            "다음 분기 실적발표에서 컴바인드레이쇼·준비금 발전 공개",
        ],
        risks=[
            "대재해 리스크가 평활화된 FCF에 구조적으로 반영되지 않음(엔진의 "
            "알려진 한계)",
            "보험 플로트 성장이 유기적 성장으로 과대평가될 위험(ACGL v3.13 "
            "핵심노트 - 이번엔 지표상 5%p 경고 임계값 안이지만 여전히 감시 필요)",
        ],
        invalidation_conditions=[
            {"condition": "재보험 ex-cat 컴바인드레이쇼가 세 분기 연속 전년比 "
                          "악화되면 텔레매틱스/언더라이팅 규율 서사 재검토",
             "check_by": None},
            {"condition": "단일 대재해로 분기 세전손실이 발생하면 재검토 "
                          "(엔진 FCF가 이 리스크를 구조적으로 못 봄)",
             "check_by": None},
            {"condition": "insurer_cross_check 괴리(RG vs 지속가능성장률)가 "
                          "5%p를 넘으면 성장 추정 신뢰도 재검토",
             "check_by": None},
        ],
        holding_horizon="12-24개월(보험업 사이클 감안 장기 보유 전제)",
        linked_ledger=path.split("/")[-1],
        author_note=(
            "이미 portfolio/holdings.json에 실보유 중(2.34%). 확신 포트폴리오"
            "(2026-09-05)에서는 9.36%로 최상위 편입 - 실보유 비중과 목표 비중의"
            "차이는 daily_brief.py의 reconciliation 섹션이 이미 드러내고 있으며,"
            "이 thesis는 사이징을 다루지 않는다(§5 범위 밖 - build_portfolio.py 소관)."
        ),
    )
    p = save_thesis(t)

    d = build_decision(
        thesis_id=t.thesis_id,
        decision_date=TODAY,
        action="HOLD",
        gates={
            "signal_summary": (
                "Gap +24.45%p(S등급), RAR +2.056, Confidence 94(엔진 원값)/"
                f"{ov.get('confidence_adj')}(정성조사 반영값). 34종목 중 상위권 Gap."
            ),
            "business_quality": (
                "특수보험·재보험 복합 언더라이터. BVPS +22.6%로 자본배분 규율 "
                "확인, 신용등급 상향. 준비금 적정성·거버넌스 정성조사(2026-08-03) "
                "전부 양호 판정."
            ),
            "financial_quality": (
                "insurer_cross_check: 지속가능성장률(ROE 평균 x 유보율)이 "
                "Realistic Growth와 0.28%p 이내 근접 - 성장 추정이 보험 플로트 "
                "착시 우려에 비해 상대적으로 견고. SBC 교차검증 미실시(보험업 "
                "특성상 낮을 것으로 예상되나 미확인)."
            ),
            "risk_assessment": (
                "대재해 리스크가 FCF-DCF의 평활화 구조로 원리적으로 미반영 - "
                "이 엔진이 구조적으로 못 보는 유일한 축. ex-cat 컴바인드레이쇼 "
                "2분기 연속 소폭 악화(추세 확정 아님)."
            ),
            "valuation_assessment": (
                "Implied Growth 두 시나리오(DRS 포함/제외) 모두 음수(-8.7%~"
                "-10.7%)로 이미 상당히 비관적인 시장가정을 시사 - 추가 하방 "
                "여지가 제한적이라는 방향의 신호."
            ),
            "portfolio_context": (
                "이미 실보유 중(holdings.json 2.34%, insurance_underwriting "
                "군집). 같은 군집 내 PGR·SIGI·CINF·RLI·BRO도 확신 포트폴리오에 "
                "동시 편입돼 있어 보험업 군집 집중도를 감안해야 함(단일종목 "
                "리스크는 아니나 업종 공통 리스크(금리·재해) 노출은 군집 합산 "
                "기준으로 볼 것)."
            ),
        },
        rationale=(
            "실보유 포지션을 유지한다. 지속가능성장률과 Realistic Growth의 "
            "근접(0.28%p)이 34종목 중에서도 드물게 견고한 신호이고, 반증조건 "
            "3개(컴바인드레이쇼 3분기 연속 악화·대재해 단일손실·괴리 5%p 초과) "
            "중 어느 것도 아직 발동하지 않았다."
        ),
        position_pct=None,
    )
    record_decision(p, d)
    print("ACGL thesis+decision recorded:", p)


# ── DLO ───────────────────────────────────────────────────────────────
def dlo():
    path, led = ledger("DLO")
    ov = overrides("DLO")
    t = InvestmentThesis(
        ticker="DLO",
        thesis_date=TODAY,
        why_buy=(
            "Gap +23.74%p(S등급). fast_grower 25% 성장상한이 바인딩됐지만 "
            "회사 자체 FY2026 가이던스(총이익 +25~30%, 영업이익 +27.5~32.5%)가 "
            "그 상한 자체를 상회한다고 명시해, 이 종목의 cap 바인딩은 ROP/BRO형 "
            "'회사 실적이 캡보다 낮은' 하방 괴리가 아니라 정반대인 상방 신호다 "
            "- 캡바인딩 할인(0.85x)을 유일하게 면제받은 이유."
        ),
        market_assumption=(
            "Implied Growth가 두 시나리오에서 약 +1.3%/-1.5%(DRS 포함/제외)로 "
            "낮게 형성돼 있다 - 시장이 신흥국 결제처리업체 특유의 규제·통화 "
            "리스크를 크게 할인해 반영 중이라는 뜻."
        ),
        irs_view=(
            "2026-09-06 1차출처(globenewswire Q2 2026 보도자료) 대조로 "
            "가이던스 수치를 직접 재확인했다 - TPV 60-70%/총이익 25-30%/"
            "영업이익 27.5-32.5% 전부 정확히 일치. 시장의 할인이 회사가 직접 "
            "제시한 가속 국면과 정합적이지 않다고 판단한다."
        ),
        key_drivers=[
            "TPV(총결제액) 고성장 지속(2H2026 가이던스 +60~70%)",
            "테이크레이트 압축(0.84%)에도 불구한 총이익률 확대",
            "FY2026 영업현금흐름 흑자 전환 지속",
        ],
        expected_outcomes=[
            "Q3 2026 실적에서 총이익 성장률이 가이던스 하단(+25%) 이상 유지",
            "순 테이크레이트가 추가로 2분기 연속 하락하지 않음",
            "NRR 140% 이상 유지",
        ],
        catalysts=["다음 분기 실적발표(총이익·NRR·테이크레이트 공개)"],
        risks=[
            "테이크레이트가 이미 0.84%까지 압축돼 추가 압축 여지가 크지 않음",
            "신흥국 통화·자본통제·규제 리스크(구조적, 상시 존재)",
            "'대형 승차공유 가맹점 가격구간 이동'이라는 일회성 설명이 반복되면 "
            "구조적 경쟁압력으로 재해석 필요",
        ],
        invalidation_conditions=[
            {"condition": "Q3 2026 실적에서 총이익 성장률이 가이던스 하단(+25%)을 "
                          "밑돌면 재검토",
             "check_by": None},
            {"condition": "순 테이크레이트가 두 분기 연속 하락하면 구조적 경쟁 "
                          "압력으로 재평가",
             "check_by": None},
            {"condition": "NRR이 140% 아래로 떨어지면 land-and-expand 서사 재검토",
             "check_by": None},
            {"condition": "FY2026 영업현금흐름이 다시 음수로 전환되면 재검토",
             "check_by": None},
        ],
        holding_horizon="12-18개월",
        linked_ledger=path.split("/")[-1],
        author_note=(
            "이미 portfolio/holdings.json에 실보유 중(11.12%, 8종목 중 4위 "
            "비중). 확신 포트폴리오에서도 9.19%로 2위 편입 - 실보유와 목표 "
            "비중이 비교적 근접한 몇 안 되는 종목."
        ),
    )
    p = save_thesis(t)

    d = build_decision(
        thesis_id=t.thesis_id,
        decision_date=TODAY,
        action="HOLD",
        gates={
            "signal_summary": (
                f"Gap +23.74%p(S등급), RAR +1.448, Confidence 94(엔진)/"
                f"{ov.get('confidence_adj')}(정성조사 반영, cap_discount_exempt 적용)."
            ),
            "business_quality": (
                "신흥국(라틴아메리카·아프리카·아시아) 특화 크로스보더 결제처리. "
                "TPV 고성장 지속, 다만 테이크레이트 압축 추세."
            ),
            "financial_quality": (
                "SBC/FCF 낮음(엔진 무flip 확인). FY2026 영업현금흐름 흑자 전환. "
                "성장상한 바인딩이 회사 가이던스로 1차출처 검증됨(2026-09-06)."
            ),
            "risk_assessment": (
                "신흥국 통화·자본통제·규제 리스크가 상시 존재(구조적, 축소 "
                "불가). 테이크레이트 압축이 계속되면 총이익률 방어가 관건."
            ),
            "valuation_assessment": (
                "Implied Growth 약 -1.5%~+1.3%로 시장이 신흥국 리스크를 상당폭 "
                "할인 중 - 회사 자체 가이던스(총이익 +25~30%)와의 괴리가 "
                "Gap의 원천."
            ),
            "portfolio_context": (
                "실보유 11.12%(전체 8종목 중 2위 비중) - 이미 상당히 집중돼 "
                "있어 추가 매수보다는 유지가 적절. financial_services_other "
                "군집 단일 종목."
            ),
        },
        rationale=(
            "실보유 포지션을 유지한다. 성장상한 바인딩의 정당성을 1차출처로 "
            "재확인했고(2026-09-06), 반증조건 4개 중 어느 것도 발동하지 않았다."
        ),
        position_pct=None,
    )
    record_decision(p, d)
    print("DLO thesis+decision recorded:", p)


# ── PGR ───────────────────────────────────────────────────────────────
def pgr():
    path, led = ledger("PGR")
    ov = overrides("PGR")
    t = InvestmentThesis(
        ticker="PGR",
        thesis_date=TODAY,
        why_buy=(
            "Gap +17.64%p(S등급, v3.67 규모조건부 상한 반영 후). 지속가능성장률이 "
            "Realistic Growth와 2%p 이내로 근접해 34종목 중 가장 정합적인 성장 "
            "추정 사례 중 하나다(2026-08-03 정성조사)."
        ),
        market_assumption=(
            "Implied Growth가 두 시나리오 모두 음수(-4.9%~-7.0%)로 역산된다 - "
            "시장이 이미 보수적인 성장 가정을 반영 중."
        ),
        irs_view=(
            "텔레매틱스 데이터 우위(Snapshot)가 아직 손해율 우위로 완전히 "
            "전환되지 못했다(점유율 1위, 손해율은 GEICO·Allstate 대비 3위) - "
            "이 격차가 좁혀지면 추가 상방, 안 좁혀지면 서사 재검토가 필요한 "
            "'검증 중'인 논거다. 신규계약 증가율 둔화(11%→8%)는 성장 감속 "
            "신호로 이미 반영."
        ),
        key_drivers=[
            "텔레매틱스(Snapshot) 데이터 우위의 손해율 개선 전환 여부",
            "상업용차 라인 준비금 안정성",
            "신규계약(PIF) 증가율 추세",
        ],
        expected_outcomes=[
            "손해율 격차(GEICO·Allstate 대비)가 확대되지 않고 안정화 또는 개선",
            "상업용차 역발전 준비금이 $140M 수준에서 확대되지 않음",
            "컴바인드레이쇼가 90 미만 유지",
        ],
        catalysts=["다음 분기 실적발표(컴바인드레이쇼·PIF 증가율 공개)"],
        risks=[
            "신규계약 증가율이 한 자릿수 초반까지 추가 둔화될 위험",
            "텔레매틱스 데이터 우위가 손해율 우위로 끝내 전환되지 않을 위험",
            "상업용차 역발전 준비금이 개인용차 라인까지 번질 위험",
        ],
        invalidation_conditions=[
            {"condition": "신규계약(PIF) 증가율이 한 자릿수 초반까지 추가 둔화되거나 "
                          "GEICO/Allstate 대비 손해율 열위가 확대되면 텔레매틱스 "
                          "모트 서사 재검토",
             "check_by": None},
            {"condition": "상업용차 역발전 준비금이 $140M보다 유의미하게 확대되거나 "
                          "개인용차 라인까지 번지면 재검토",
             "check_by": None},
            {"condition": "컴바인드레이쇼가 90 이상으로 뛰면(수리비 인플레이션 "
                          "재점화 신호) 재검토",
             "check_by": None},
        ],
        holding_horizon="12-24개월",
        linked_ledger=path.split("/")[-1],
        author_note=(
            "portfolio/holdings.json에는 없음(미보유) - 확신 포트폴리오"
            "(2026-09-05)에서 7.08%로 3위 편입된 후보다. 이 thesis는 매수 "
            "실행을 의미하지 않는다 - 사이징·집행은 build_portfolio.py/사람의 "
            "판단 영역이며 이 모듈은 신호와 결정을 분리한다(§5)."
        ),
    )
    p = save_thesis(t)

    d = build_decision(
        thesis_id=t.thesis_id,
        decision_date=TODAY,
        action="WATCH",
        gates={
            "signal_summary": (
                f"Gap +17.64%p(S등급, 규모조건부 상한 적용 후), RAR +1.412, "
                f"Confidence 94(엔진)/{ov.get('confidence_adj')}(정성조사 반영)."
            ),
            "business_quality": (
                "자동차보험 대형사, 시장점유율 1위. 텔레매틱스(Snapshot) 데이터 "
                "우위가 핵심 경쟁 논거이나 손해율 순위(3위)에는 아직 완전히 "
                "반영되지 않음."
            ),
            "financial_quality": (
                "지속가능성장률(ROE x 유보율 18.88%)이 Realistic Growth와 "
                "2%p 이내 근접 - is_insurer 교차검증 통과."
            ),
            "risk_assessment": (
                "신규계약 증가율 둔화(11%→8%YoY), 상업용차 라인 소폭 역발전 "
                "준비금($140M). 둘 다 추세 확정은 아니나 감시 필요."
            ),
            "valuation_assessment": (
                "Implied Growth -4.9%~-7.0%로 시장이 이미 보수적 가정을 "
                "반영 중 - Gap의 크기는 성장 낙관이 아니라 시장의 과도한 "
                "비관에서 온다는 방향."
            ),
            "portfolio_context": (
                "미보유. insurance_underwriting 군집(ACGL·SIGI·CINF·RLI·BRO와 "
                "동일 군집)에 신규 편입하면 업종 집중도가 추가로 올라간다 - "
                "ACGL을 이미 실보유 중이므로 군집 합산 리스크를 함께 고려해야 "
                "한다."
            ),
        },
        rationale=(
            "매수를 실행하지 않고 관찰한다(WATCH). 신호와 근거는 충분히 "
            "강하나(성장추정 정합성 최상위권), 미보유 신규 편입은 "
            "insurance_underwriting 군집 집중도를 추가로 높인다는 "
            "포트폴리오 맥락상의 이유로 사이징 판단을 미룬다."
        ),
        position_pct=None,
    )
    record_decision(p, d)
    print("PGR thesis+decision recorded:", p)


if __name__ == "__main__":
    acgl()
    dlo()
    pgr()

    for t in ("ACGL", "DLO", "PGR"):
        from engine.thesis import latest_thesis, evaluate_thesis_status
        path, record = latest_thesis(t)
        status = evaluate_thesis_status(record)
        print(f"{t}: status={status['status']} n_supports={status['n_supports']} "
              f"n_contradicts={status['n_contradicts']}")
