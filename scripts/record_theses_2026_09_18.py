"""
2026-09-18 - VRT·NOW 투자논거 최초 기록.

## 왜 이 두 종목인가

2026-09-16 보유 포트폴리오 심화 재분석(`reports/holdings_deep_review_
2026-09-16.json`)에서 실보유 8종목 중 PTC·ACGL·DLO는 이미 `thesis/`에
기록이 있었지만(2026-09-07/09-10), VRT·NOW는 없었다 - Gap·등급만으로
"보유 유지"를 판단해왔고 `record_decision()`의 6관문을 거친 적이 없었다.
SE는 다음 기회에 별도로 다룬다(매출 태그 정의전환 이슈가 있어 우선순위를
VRT·NOW 뒤로 뒀다).

## 무엇을 새로 만들지 않았는가

밸류에이션 로직 0줄. ledger에 이미 저장된 Gap/RG/Confidence/model_choice_
reason/subjective_input_basis/falsification_conditions/sbc_cross_check와
2026-09-16 가격재계산(holdings_deep_review) 결과를 그대로 인용해 6관문
텍스트를 채운다. 액션은 사람(나)이 직접 고른다 - 둘 다 이미 실보유 중이고
반증조건이 하나도 발동하지 않아 HOLD.
"""
import glob
import json
import sys

sys.path.insert(0, ".")

from engine.thesis import (
    InvestmentThesis, build_decision, save_thesis, record_decision,
)

TODAY = "2026-09-18"


def ledger(ticker):
    path = sorted(glob.glob(f"ledger/{ticker}_*.json"))[-1]
    return path, json.load(open(path, encoding="utf-8"))


def holdings_weight(ticker):
    d = json.load(open("portfolio/holdings.json", encoding="utf-8"))
    total = d["total_market_value_krw"]
    for p in d["positions"]:
        if p["ticker"] == ticker:
            return p["market_value_krw"] / total
    return None


# ── VRT ──────────────────────────────────────────────────────────────
def vrt():
    path, led = ledger("VRT")
    weight = holdings_weight("VRT")
    t = InvestmentThesis(
        ticker="VRT",
        thesis_date=TODAY,
        why_buy=(
            "실보유 포지션(19.12%, 2026-09-17 기준 holdings.json)의 정기 "
            "재검토 - AI 데이터센터 열관리·전력관리 업체로 C등급(적정가/"
            "경계선, Gap -1.24%p)이나, 회사 자체 가이던스(오가닉 +30~32%, "
            "수주잔고 $15B/book-to-bill 2.9x)가 trailing 매출 CAGR을 크게 "
            "웃도는 고성장 국면이다. 2026-09-02 UtilityInnovation Group "
            "인수($1.45B 현금+최대 $1.15B 언아웃) 발표 이후 주가가 "
            "$280.53->$234.61(-16.4%, 2026-09-04->09-16)로 하락해 재검토가 "
            "필요했다."
        ),
        market_assumption=(
            "시장은 AI 인프라 capex 사이클의 정점 통과 우려와 인수 관련 "
            "불확실성(조달구조·통합리스크)을 가격에 반영 중인 것으로 보인다. "
            "2026-09-16 재계산에서 시총 -16.4%가 Gap을 -1.24%p->+0.83%p로 "
            "벌렸는데(v3.42 가치함정 성질 - 주가하락은 반드시 Gap을 넓힌다), "
            "이 확대가 정당한 저평가 신호인지 여전히 비싼 상태에서의 단순 "
            "가격조정인지는 이 데이터만으로 구분되지 않는다."
        ),
        irs_view=(
            "이 종목의 가장 중요한 사실은 판정 방향이 아니라 **모델선택에 "
            "대한 극단적 민감도**다 - single_stage(9.07%)와 two_stage"
            "(19.95%)의 내재성장률 괴리가 10.88%p로 이 프로젝트 34종목+ "
            "코퍼스 중 최대급이고, v3.51 gap_range 분석이 '모델선택 단독으로 "
            "Gap이 12~20%p 움직이는' 취약종목군에 포함시켰다. two_stage를 "
            "쓰는 이유(model_choice_reason)는 타당하나(trailing CAGR이 "
            "terminal growth를 압도적으로 웃돌고 v3.67 규모조건부 상한이 "
            "장기 지속가능 성장을 23.00%로 제시해 언젠가 수렴이 불가피함을 "
            "시사), Gap 절대값을 액면 그대로 신뢰하지 말라는 게 ledger 자신의 "
            "경고다. 다행히 SBC 완전차감·DRS 포함제외 강건성점검 양쪽 다 "
            "판정(C)이 흔들리지 않아, 최소한 '등급'은 안정적이다."
        ),
        key_drivers=[
            "AI 데이터센터 열관리·전력관리 수요(수주잔고 $15B, book-to-bill "
            "2.9x)",
            "UtilityInnovation Group 인수를 통한 사업영역 확장(2026-09-02 "
            "발표)",
            "하이퍼스케일러(Microsoft/Google/Amazon/Meta) capex 사이클 "
            "직접 수혜",
        ],
        expected_outcomes=[
            "Q3 2026 실적에서 수주잔고가 전분기 대비 유지·증가, book-to-bill "
            "1.0x 이상",
            "FY2026 오가닉 성장이 가이던스 하단(+30%) 이상",
            "조정영업마진이 가이던스 하단(23.3%) 이상",
        ],
        catalysts=[
            "Q3 2026 실적발표(2026-11월경) - falsification_conditions "
            "①②④ 확인 시점",
            "하이퍼스케일러 4사 데이터센터 capex 가이던스 발표",
            "UtilityInnovation Group 인수 종결·통합 진행상황",
        ],
        risks=[
            "모델선택 취약(single/two-stage 괴리 10.88%p) - Gap 절대값 "
            "신뢰도가 이 프로젝트 코퍼스 중 최하위권",
            "AI 데이터센터 capex 사이클 고점 통과 리스크(2026-09-04 이후 "
            "주가 -16.4%가 이미 이 우려를 일부 반영 중일 가능성)",
            "Schneider Electric·Eaton과의 경쟁이 가격 압박으로 번질 경우 "
            "조정영업마진 훼손",
            "신규 인수(UtilityInnovation)가 다음 정식분석 시 GEN/BRO/ROP류 "
            "'M&A가 CAGR 계산구간을 오염시키는' 패턴을 만들 가능성 - 아직 "
            "ledger(2026-09-04)의 CAGR 창에는 반영되지 않음",
        ],
        invalidation_conditions=[
            {"condition": "2026-11월경 Q3 2026 실적에서 수주잔고($15B)가 "
                          "전분기 대비 감소하거나 book-to-bill이 1.0x 아래로 "
                          "떨어지면 - AI 데이터센터 수주 사이클의 정점 통과 "
                          "신호이므로 재검토",
             "check_by": "2026-11-30"},
            {"condition": "FY2026 오가닉 성장이 가이던스 하단(+30%)을 "
                          "밑돌면 - trailing CAGR을 크게 웃도는 성장 전제가 "
                          "무너지는 것이므로 재검토",
             "check_by": None},
            {"condition": "하이퍼스케일러(Microsoft/Google/Amazon/Meta) "
                          "데이터센터 capex 가이던스가 하향되면 - "
                          "demand_sensitivity 0.45의 근거가 되는 외생 "
                          "수요원이 흔들리는 것이므로 재검토",
             "check_by": None},
            {"condition": "조정영업마진이 가이던스 하단(23.3%)을 밑돌면 - "
                          "Schneider/Eaton과의 경쟁이 가격으로 번지고 있다는 "
                          "신호이므로 재검토",
             "check_by": None},
        ],
        holding_horizon="12개월 이상(FY2026 오가닉 성장 가이던스 달성 여부 "
                        "확인 후 재평가)",
        linked_ledger=path.split("/")[-1],
        author_note=(
            "이미 portfolio/holdings.json에 실보유 중(19.12%, 8종목 중 "
            "두 번째로 큰 비중이나 25% CONCENTRATION 임계값 미만). 확신 "
            "포트폴리오(2026-09-05)에는 VRT가 포함돼 있지 않다(C등급이라 "
            "S/A 유니버스 밖). 이 thesis는 사이징을 다루지 않는다(§5 범위 "
            "밖). 2026-09-02 인수 발표에 따른 순부채 증가 시나리오를 "
            "2026-09-16 심화재분석에서 검증했으나 leverage_score가 계단함수라 "
            "$1.45B 반영해도 판정이 안 바뀜을 확인했다(reports/holdings_"
            "deep_review_2026-09-16.json)."
        ),
    )
    p = save_thesis(t)

    d = build_decision(
        thesis_id=t.thesis_id,
        decision_date=TODAY,
        action="HOLD",
        gates={
            "signal_summary": (
                "Gap -1.24%p(ledger 2026-09-04) -> +0.83%p(2026-09-16 "
                "가격재계산, C등급 불변). RAR -0.0299(기대수익률 음수라 RAR "
                "방향성 경고 발동 - Expectation Gap 우선 참고). Confidence "
                "94(엔진 원값, 정성조사 미실시)."
            ),
            "business_quality": (
                "AI 데이터센터 열관리·전력관리 시장에서 정밀냉각 점유율 "
                "23%로 선두권. Schneider·ABB·Eaton·Delta와 합계 41~43% "
                "과점시장(2026-09-04 WebSearch). UtilityInnovation "
                "인수로 사업영역 확장 중."
            ),
            "financial_quality": (
                "SBC/FCF 2.42%로 낮음(SBC 차감해도 판정 C 불변, flip 없음). "
                "10년 CAGR 데이터 부족(6개년만 확보)으로 5년 CAGR을 "
                "대체입력 - revenue_volatility·구조적할인율이 실제보다 "
                "관대할 수 있음(ledger data_limitations 명시)."
            ),
            "risk_assessment": (
                "모델선택 괴리 10.88%p(single_stage 9.07% vs two_stage "
                "19.95%) - 이 프로젝트 코퍼스 중 최고 수준의 취약종목. "
                "AI capex 사이클 고점 통과 리스크. 신규 인수가 향후 CAGR "
                "왜곡을 만들 가능성(다음 분석 시 확인 필요)."
            ),
            "valuation_assessment": (
                "두 모델 다 판정(C, 적정가/경계선)은 불변이지만 Gap 절대값 "
                "(-1.24%p~+0.83%p vs two_stage 채택시 실질적으로 더 큰 폭)은 "
                "신뢰하지 말 것 - model_choice_reason이 명시한 v3.51 "
                "robust=False 종목."
            ),
            "portfolio_context": (
                "실보유 19.12%(8종목 중 2위 비중) - CONCENTRATION 임계값"
                "(25%) 미만이나 PTC(37.7%)에 이은 대형 포지션. 확신 "
                "포트폴리오에는 미포함(C등급)."
            ),
        },
        rationale=(
            "실보유 포지션을 유지한다(HOLD). C등급(적정가/경계선)이 두 "
            "모델·강건성점검·SBC조정 전부에서 안정적으로 재현돼 판정 자체는 "
            "신뢰할 만하지만, 그 판정이 '싸다'가 아니라 '적정가'라는 점에서 "
            "추가매수 근거가 되지 않는다. 반증조건 4개 중 어느 것도 아직 "
            "발동하지 않았고, 2026-09-02 신규 인수는 현재 밸류에이션에 "
            "실질적 영향을 주지 않음을 확인했다(순부채 시나리오 검증)."
        ),
        position_pct=weight,
    )
    record_decision(p, d)
    print("VRT thesis+decision recorded:", p)


# ── NOW ──────────────────────────────────────────────────────────────
def now():
    path, led = ledger("NOW")
    weight = holdings_weight("NOW")
    t = InvestmentThesis(
        ticker="NOW",
        thesis_date=TODAY,
        why_buy=(
            "실보유 포지션(7.22%, 2026-09-17 기준 holdings.json)의 정기 "
            "재검토 - A등급(저평가 가능성, Gap +8.30%p) 클라우드 워크플로 "
            "자동화 플랫폼. FY2015-2025 매출 YoY가 38.4%->20.9%로 매끄럽게 "
            "감속하는 교과서적 수렴경로를 그리고 있어(M&A 단계상승 없는 "
            "유기적 감속), 모델선택 자의성이 VRT(모델괴리 10.88%p) 같은 "
            "종목보다 작다(모델괴리 5.35%p)."
        ),
        market_assumption=(
            "구독형 좌석과금(seat-based) 모델이 AI로 인해 축소될 것이라는 "
            "서사, Microsoft(Power Platform+Copilot 번들)·Salesforce의 "
            "인접시장 경쟁 심화 우려가 밸류에이션에 일부 반영돼 있을 "
            "가능성이 있다."
        ),
        irs_view=(
            "회사 자체 선행지표(cRPO 상수통화 +21.5%YoY, 가이던스 2%p+ "
            "초과 / ServiceNow AI ACV $10억 돌파)는 아직 이 우려를 뒷받침 "
            "하지 않는다 - 'AI가 좌석 수를 줄인다'는 서사가 서사 단계에 "
            "머물러 있다는 뜻이다. 다만 이 종목의 가장 중요한 취약점은 "
            "경쟁 서사가 아니라 **SBC**다 - SBC/FCF 42.7%로 실제 비용 차감 "
            "시 판정이 '저평가 가능성'->'적정가/경계선'으로 실제 뒤집힌다"
            "(2026-08-01 방법론 감사에서 WDAY가 이 경로로 뒤집힌 선례가 "
            "있음). 또한 FY2026부터 Armis($7.75B, 이미 종결)·Veza·"
            "Moveworks 인수가 연결에 들어와 GEN/BRO/ROP류 M&A CAGR 왜곡이 "
            "다음 분석부터는 실제로 발생할 것이다 - 지금 ledger(FY2015-"
            "2025 기준)가 깨끗하다는 사실이 다음 분석에도 그대로 이어진다는 "
            "뜻은 아니다."
        ),
        key_drivers=[
            "cRPO(선행지표) 상수통화 성장률 20%+ 유지",
            "비좌석(non-seat) 가격모델 신규계약 비중 확대(현재 50%)",
            "ServiceNow AI ACV 성장 지속($10억 돌파)",
        ],
        expected_outcomes=[
            "cRPO 상수통화 성장률이 두 분기 연속 20% 아래로 떨어지지 않음",
            "non-seat 신규계약 비중이 50%에서 후퇴하지 않음",
            "FY2026 10-K에서 구독매출 유기적 성장률이 연결 성장률 대비 "
            "3%p 이내로 근접(M&A 왜곡이 크지 않음을 확인)",
        ],
        catalysts=[
            "FY2026 10-K(2027-01경) - Armis/Veza/Moveworks 편입 이후 "
            "최초로 유기적/비유기적 성장 분리대조가 가능해지는 시점",
            "분기별 cRPO·AI ACV 발표",
        ],
        risks=[
            "SBC/FCF 42.7% - 판정이 SBC 처리방식 하나로 실제 뒤집히는 "
            "종목(가장 중요한 리스크)",
            "FY2026부터 M&A(Armis 등)로 CAGR 계산구간이 왜곡되기 시작 - "
            "GEN/BRO/ROP와 동일 패턴이 다음 분석부터 실제 발생",
            "차입금이 Armis 인수 자금조달로 $1,491M->$5,435M 급증 - "
            "추가 대형 M&A 시 재무 유연성 추가 잠식 가능",
            "Microsoft/Salesforce의 번들링 경쟁이 아직 점유율 실측 증거는 "
            "없으나 서사 자체는 계속 진행 중",
        ],
        invalidation_conditions=[
            {"condition": "FY2026 10-K(2027-01경)에서 회사 공시 구독매출 "
                          "유기적 성장률이 연결 성장률보다 3%p 이상 낮으면 "
                          "- M&A CAGR 왜곡이 실제로 발생한 것이므로 재검토",
             "check_by": "2027-01-31"},
            {"condition": "cRPO 상수통화 성장률이 두 분기 연속 20% 아래로 "
                          "떨어지면 - cRPO는 매출보다 먼저 움직이는 "
                          "선행지표이므로 재검토",
             "check_by": None},
            {"condition": "비좌석(non-seat) 가격모델 신규계약 비중이 50%에서 "
                          "후퇴하면 - 'AI가 좌석 수를 줄인다'는 위협에 대한 "
                          "회사 대응이 실패하고 있다는 신호이므로 재검토",
             "check_by": None},
            {"condition": "ServiceNow AI ACV 성장이 정체되면 재검토",
             "check_by": None},
            {"condition": "차입금이 Armis 인수 자금조달($1,491M->$5,435M) "
                          "이후 추가로 크게 늘면 - 연쇄 M&A 자금조달이 재무 "
                          "유연성을 잠식하는 것이므로 재검토",
             "check_by": None},
        ],
        holding_horizon="12개월 이상(FY2026 10-K에서 유기적성장 분리대조 "
                        "확인 후 재평가)",
        linked_ledger=path.split("/")[-1],
        author_note=(
            "이미 portfolio/holdings.json에 실보유 중(7.22%, 8종목 중 "
            "가장 작은 비중의 정식판정 보유종목). 확신 포트폴리오(2026-"
            "09-05)에는 NOW가 포함돼 있지 않다(A등급이나 quality_score "
            "순위에서 상위 18위 밖). 2026-08-14에는 goodwill이 한 분기 "
            "만에 2배 급증(Q1'26 $4.54B->Q2'26 $9.84B)한 것만 보고 "
            "FRAMEWORK_MISMATCH로 잘못 배제한 이력이 있었으나, 2026-09-13 "
            "정식분석에서 실제 FY2015-2025 연차 매출 시계열에 단계상승이 "
            "전혀 없는 단조 감속임을 확인해 판정을 A등급으로 정정했다 - "
            "분기 대차대조표만 보고 연차 손익의 오염을 추정한 것이 오류의 "
            "원인이었다(같은 프로젝트가 반복 겪은 유형)."
        ),
    )
    p = save_thesis(t)

    d = build_decision(
        thesis_id=t.thesis_id,
        decision_date=TODAY,
        action="HOLD",
        gates={
            "signal_summary": (
                "Gap +8.30%p(ledger 2026-09-05) -> +8.24%p(2026-09-16 "
                "가격재계산, 거의 불변). RAR +0.8547. Confidence 94(엔진 "
                "원값, 정성조사 미실시)."
            ),
            "business_quality": (
                "클라우드 워크플로 자동화 플랫폼. FY2015-2025 매출 YoY가 "
                "38.4%->20.9%로 매끄럽게 감속(M&A 단계상승 없음). RPO "
                "$29.0B/cRPO $13.2B 계약잔액 견조."
            ),
            "financial_quality": (
                "⚠️ SBC/FCF 42.7% - SBC를 실제 비용으로 차감하면 판정이 "
                "'저평가 가능성'->'적정가/경계선'으로 뒤집힌다(Gap +8.30%p"
                "->+1.88%p). 이 종목의 재무품질 평가에서 가장 중요한 사실."
            ),
            "risk_assessment": (
                "FY2026부터 Armis($7.75B)·Veza·Moveworks 인수가 연결돼 "
                "M&A CAGR 왜곡이 다음 분석부터 실제 발생할 전망. 차입금 "
                "$1,491M->$5,435M 급증. Microsoft/Salesforce 경쟁 서사는 "
                "아직 점유율 실측 증거 없음."
            ),
            "valuation_assessment": (
                "모델괴리 5.35%p(single_stage 7.36% vs two_stage 12.71%)로 "
                "VRT보다는 작으나 SBC 처리방식에 판정이 뒤집히는 취약점이 "
                "더 크다 - Gap +8.30%p를 액면 그대로 신뢰하지 말 것."
            ),
            "portfolio_context": (
                "실보유 7.22%(8종목 중 최소 비중) - 집중도 리스크 없음. "
                "확신 포트폴리오에는 미포함."
            ),
        },
        rationale=(
            "실보유 포지션을 유지한다(HOLD). 회사 자체 선행지표(cRPO·AI "
            "ACV)가 아직 견조하고 반증조건 5개 중 어느 것도 발동하지 "
            "않았지만, SBC 차감 시 판정이 실제로 뒤집히는 종목이라 추가 "
            "매수 근거로 삼지 않는다. FY2026 10-K(2027-01경)에서 M&A "
            "왜곡 여부를 반드시 재확인할 것 - 이 시점 이전까지는 지금의 "
            "'깨끗한 유기적 성장' 서사가 다음 분석에도 유효하다고 가정하지 "
            "말 것."
        ),
        position_pct=weight,
    )
    record_decision(p, d)
    print("NOW thesis+decision recorded:", p)


if __name__ == "__main__":
    vrt()
    now()
