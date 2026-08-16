# structural_discount_rate() 외부 경제적 근거 조사 (§49-51)

작성일: 2026-08-16 · 트리거: `ablation_analysis.md`가 발견한 12% 판정영향력
(구조적할인/캡 절제실험, DRS영향 3% ≪ 모델선택영향 32% 사이) · 기존 코드 라벨:
`VALIDATION_STATUS`에 항목 자체가 없었음(HEURISTIC이라고도 명시적으로 안 돼
있었다 - 이번 조사로 처음 라벨을 붙인다)

## PROBLEM

`engine/expectation_gap_engine.py`의 `structural_discount_rate()`는 34종목
판정의 12%를 좌우하는데(ablation 실측), 근거 문서가 코드 주석 한 줄
("최근 성장이 장기 평균보다 느려지면 할인폭을 키운다")뿐이고 외부 문헌
검증이 한 번도 없었다. 함수는 사실 두 개의 서로 다른 메커니즘을 하나의
숫자로 합쳐놓았다:

1. **추세둔화 조정**: `trend_delta = revenue_cagr_10y - revenue_cagr_3y`가
   양수(최근 성장이 장기평균보다 느림)면 할인을 키우고, 음수(가속)면 줄인다.
2. **초대형주 가산**: `market_cap >= 1000`(10억원 단위, 즉 시총 ≥1,000)이면
   +3%p, `>= 200`이면 +1%p를 추가로 더한다.

## ROOT CAUSE

v3.9 도입 당시(CLAUDE.md 이력상 가장 이른 버전대) 직관적으로 설계됐고,
그 이후 어떤 버전에서도 외부 학술문헌과 대조된 적이 없다. `VALIDATION_STATUS`
딕셔너리(v3.46, 계약서 40절 5단계 인식론적 사다리 - IMPLEMENTED_NOT_VALIDATED
/ SOFTWARE_VALIDATED / ECONOMICALLY_SUPPORTED / EMPIRICALLY_SUPPORTED /
CALIBRATED)에 `erp_from_drs`·`lynch_type_caps`·`rar` 등은 항목이 있는데
`structural_discount_rate`는 **누락**돼 있었다 - 라벨조차 안 붙어 있던
상태였다.

## EXTERNAL EVIDENCE (§49 우선순위 - 1차 학술문헌부터)

### 근거 1 — Chan, Karceski, Lakonishok (2003), *Journal of Finance* Vol 58 No 2, pp.643-684 / NBER Working Paper w8282

**존재 검증**: 3개 독립 출처(SSRN 등재정보, NBER 논문페이지, Illinois
Experts 저자소속기관 초록페이지)가 동일한 저자·저널·권호·페이지를 일치되게
보고해 실재하는 1차 학술문헌임을 확인했다. **원문 PDF 추출은 2회 시도
모두 실패**했다(NBER PDF·저자 소속사 LSV Asset Management PDF 둘 다
FlateDecode 압축 바이너리만 반환 - 텍스트 추출 불가, 정밀 수치는 확보 못함).
아래는 Illinois Experts 초록 페이지(HTML, 추출 성공)에서 확인한 내용이다.

**확인된 헤드라인 발견**(초록 원문 인용):
- "There is no persistence in long-term earnings growth beyond chance"
  (장기 이익성장에 우연 이상의 지속성이 없다) — `trend_delta` 메커니즘의
  핵심 전제(최근 고성장을 그대로 미래에 연장하면 안 된다)와 방향이 정확히
  일치한다.
- "low predictability even with a wide variety of predictor variables"
  (다양한 예측변수를 써도 예측력이 낮다) — 밸류에이션 비율을 포함한 여러
  예측변수로도 미래 성장을 못 맞춘다는 뜻.
- IBES 애널리스트 장기성장 전망은 "too optimistic"이고 예측력이 미미하다.

**⚠️ 기업규모(firm size) 관련**: 초록에는 규모 관련 구체적 언급이 **없다**
("broad cross section of stocks"라고만 서술). 즉 이 논문이 `structural_
discount_rate()`의 **초대형주 가산 메커니즘을 직접 지지한다는 근거는
확보하지 못했다** - 지지도 반박도 아니고 [원문 미확인]이다.

### 근거 2 — Dechow & Sloan (1997) [WebSearch 스니펫으로만 확인, 1차 검증 안 됨]

WebSearch 결과 요약으로만 확인 - "미래 이익성장률은 평균회귀하는데 시장이
이를 충분히 반영하지 못한다"는, 근거1과 같은 방향의 별개 회계/재무 문헌으로
언급됐다. **원문에 직접 접근해 검증하지 않았으므로 [WEBSEARCH-SNIPPET-ONLY]
로 표시한다** - §51이 요구하는 "1차 출처 우선"에는 못 미치지만, 독립된
2번째 문헌이 같은 방향을 가리킨다는 정황증거로만 취급한다.

### 근거 3 — 기업규모×성장평균회귀 관계 자체 검색

별도로 "firm size effect on earnings growth mean reversion"을 검색한
결과는 **혼재됐다**: "대형기업일수록 수익성장 프리미엄에 대한 초과수익
효과가 줄어든다"는 결과와 "소형기업이 오히려 평균회귀가 더 낮다"는 결과가
함께 나와, 코드의 `market_cap >= 1000 → +3%p, >= 200 → +1%p`처럼 **규모가
클수록 할인을 단조증가시키는 단순한 계단함수를 직접 지지하는 문헌은
찾지 못했다.**

## HYPOTHESIS

`structural_discount_rate()`의 두 구성요소는 근거 수준이 다르다:
- **추세둔화(trend_delta) 메커니즘**: 방향과 존재 자체는 실재하는 1차
  학술문헌(근거1)이 명확히 지지한다.
- **초대형주 가산**: 어떤 1차 문헌도 이 구체적 계단함수(경계값 1000/200,
  가산폭 +3%p/+1%p)를 지지하지 않는다 - 여전히 근거 없는 임의값이다.

## PROPOSED CHANGE

**없음.** 코드를 바꾸지 않는다.

## ECONOMIC LOGIC vs 코드 대조

| 구성요소 | 코드가 하는 일 | 문헌이 뒷받침하는 정도 |
|---|---|---|
| trend_delta | 최근 3y 성장이 10y 평균보다 느리면 할인 확대 | 방향 일치(근거1 헤드라인) - 다만 `deceleration_sensitivity=0.5`라는 반응계수 자체는 여전히 임의값, 문헌이 이 계수를 직접 준 적 없음 |
| 초대형주 가산 | 시총≥1000이면 +3%p, ≥200이면 +1%p 고정 가산 | 근거 못 찾음 - 방향(대형주가 더 평균회귀)조차 문헌상 혼재 |

## EXPECTED BENEFIT (가산 제거 시)

미검증 - 별도 절제실험이 필요하나 이번 조사 범위 밖(이 조사는 "근거가
있는가"만 답한다, "제거하면 더 나은가"는 별개 질문).

## POTENTIAL FAILURE MODE

혼재된 외부검색 결과만으로 초대형주 가산을 지금 제거하거나 수정하면, 이
프로젝트가 반복 확립한 원칙("근거 없이 유지하던 걸 근거 없는 다른 숫자로
바꾸는 것은 개선이 아니다" - LYNCH_TYPE_CAPS·P/B임계값·ERP매핑과 동일 판단)을
정확히 위반하는 것이 된다. 지지도 반박도 확정 못한 상태에서 손대는 것
자체가 새로운 임의 결정이다.

## IMPLEMENTATION COST

0 — 코드 변경 없음. `engine/expectation_gap_engine.py`의 `VALIDATION_STATUS`
딕셔너리에 이번 조사 결과를 라벨로만 추가한다(로직 무변경, 계약서 40절
5단계 사다리의 정의된 어휘 그대로 사용).

## SUCCESS / FAILURE CRITERION

이번 조사의 목적은 "코드를 바꿀 근거를 만드는 것"이 아니라 "이미 존재하는
근거 수준을 정직하게 라벨링하는 것"이었다 - 그 기준으로는 **완료**(성공)다:
trend_delta 메커니즘은 이제 IMPLEMENTED_NOT_VALIDATED보다 한 단계 위인
ECONOMICALLY_SUPPORTED로 승격할 근거가 생겼고, 초대형주 가산은 여전히
IMPLEMENTED_NOT_VALIDATED(사실상 HEURISTIC)임이 명시적으로 확정됐다.

## VALIDATION DATA / HOLDOUT DATA

없음(그리고 이번 조사 성격상 필요 없음 - 문헌 존재·내용 확인이지 이
프로젝트 데이터로 검증하는 실증연구가 아니다).

## 최종 판정 (§51 체인의 결론)

- **trend_delta 메커니즘**: **REQUIRES_VALIDATION → 이번 조사로 DEFER
  유지, 단 라벨 승격.** 방향은 지지되나 `deceleration_sensitivity=0.5`
  계수 자체의 보정은 여전히 안 됨 - ECONOMICALLY_SUPPORTED이지
  EMPIRICALLY_SUPPORTED나 CALIBRATED는 아니다.
- **초대형주 가산(+3%p/+1%p)**: **DEFER, 라벨 무변경(근거없음 명시).**
  코드도 라벨도 그대로 두되, 이 하위요소가 구조적할인 전체 12% 영향력 중
  상대적으로 더 취약한 부분이라는 사실을 문서에 남긴다 - 다음에 이 함수를
  다시 볼 여력이 생기면 이 하위요소부터 검토할 것.

## 조사 방법론 한계 (정직하게 기록)

- 근거1 논문 원문에 끝내 접근하지 못했다(PDF 텍스트 추출 2회 실패) -
  확보한 것은 초록 수준 요약뿐이며, 방법론·회귀계수·정밀 수치는 확인
  못했다. 규모 관련 세부 내용이 초록에 없다고 해서 원문 본문에도 없다는
  뜻은 아니다 - [원문 미확인]으로 정직하게 남긴다(추측 금지 원칙).
- 근거2(Dechow & Sloan)는 WebSearch 요약만으로 인용했다 - 이 프로젝트의
  1차자료 우선 원칙(§49)에 못 미치는 증거 등급이라 별도로 표시해뒀다.
