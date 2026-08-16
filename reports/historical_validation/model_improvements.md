# Model Improvements — #1 우선순위 (§65)

작성일: 2026-08-16

## PROBLEM

Historical Replay/OOS 검증이 구조적으로 불가능한 이유를 파고들면 데이터
부족이 아니라 **인프라 미사용**이 근본원인이다: `prediction_ledger.py`·
`thesis.py`(v3.48)는 완성돼 425개(현재 441개) 테스트로 검증돼 있었으나
`predictions/`·`thesis/` 디렉터리가 **파일시스템에 존재하지도 않았다**
(실사용 0건, Phase 1 확인). 3개월 뒤, 1년 뒤에도 이 상태가 유지되면
검증은 영원히 시작되지 않는다.

## EVIDENCE

- `ls predictions/ thesis/` → `No such file or directory` (2026-08-16 확인, 조치 전)
- 435개 테스트 중 상당수가 이 두 모듈의 무결성을 검증하지만, 그 무결성이
  "실제로 쓰였을 때"를 전제로 한다 — 안 쓰이면 검증 대상 자체가 없다.
- 이 프로젝트는 "완성된 기능이 실사용 0건"인 패턴을 이미 한 번 겪었다
  (v3.24 `price_at_analysis` 도입 12일 뒤 "24종목은 부식 계산 자체가 불가능"
  이라는 구체적 비용으로 드러남, CLAUDE.md 기록) — 같은 패턴의 재발이다.

## ROOT CAUSE

인프라를 "opt-in"으로 설계한 것 자체는 옳았다(과거 34종목에 소급 적용하면
사후합리화가 된다는 원칙 때문). 그런데 opt-in은 **누군가 실제로 켜야** 작동한다.
이 프로젝트에 "새 코드를 만들면 실제 종목에 적용해본다"는 마감 단계가
없었다 — 매번 다음 신규 기능으로 넘어갔다.

## AFFECTED MODULE

`engine/prediction_ledger.py`(계산 로직 변경 없음), `predictions/`(신규 데이터)

## AFFECTED DECISIONS

이번 동결 자체는 어떤 공식 판정도 바꾸지 않는다(병기 원칙과 동일 정신 -
새 밸류에이션이 아니라 이미 계산된 값을 기록만 함). **미래**에 영향을
준다 - 3~12개월 뒤 실제 결과가 나오면 이 34건이 최초의 진짜 검증 표본이 된다.

## PROPOSED FIX (구현 완료)

`scripts/freeze_predictions_2026_08_16.py` — 34종목 각각에 대해 매출 YoY
성장률 예측을 봉인한다.

**새 판단을 발명하지 않는다는 원칙을 지킨 설계**:
- `expected_low`/`expected_high` = `growth.breakdown.revenue_cagr_inputs`의
  3y/5y/10y 최소~최대(엔진이 Realistic Growth 계산 중 **이미 산출**한 값).
  새 밴드폭·새 가중치를 만들지 않았다.
- `thesis_id="NO_THESIS_SIGNAL_ONLY"` — 있지도 않은 Investment Thesis를
  지어내지 않고 그 부재를 그대로 기록.
- `prediction_date="2026-08-16"`(실제 동결 시점) — 원분석일로 backdate하지
  않는다. 원분석일·엔진버전은 `source`/`horizon`에 별도 보존.

## EXPECTED BENEFIT

3개월 뒤부터 `resolve_prediction()`으로 실제 실적을 붙이면, 이 프로젝트
최초로 **해시봉인된, 사후조작 불가능한 예측-대-실제 비교 34건**이 생긴다.
지금까지의 growth_scorecard 17건은 사후에 리포트로 만든 것이라 봉인이
없었다 — 이번 것은 처음부터 봉인된 채로 시작한다.

## POTENTIAL FAILURE MODE

- 회계연도 종료·실적발표 정확한 날짜를 특정하지 않아(`horizon`이 서술적)
  해소(resolve) 시점에 "언제 확인할지"를 분석자가 판단해야 한다 — 자동화
  안 됨. 의도적 선택이다(정확한 발표일을 지어내는 것보다 서술적으로 남기는
  게 낫다고 판단).
- expected_range가 CAGR 구성요소의 min~max일 뿐이라 실제 예측력이 얼마나
  될지는 검증된 바 없다 — 이 자체가 §51의 "success criterion"에서 다룰 대상.

## IMPLEMENTATION

`scripts/freeze_predictions_2026_08_16.py` (완료), 34/34종목 성공(0건
스킵 - 최소 CAGR 구성요소 2개 이상 확보).

## TESTS

`tests/test_frozen_predictions.py` 6건 신설 — 범위가 ledger 원본과 정확히
일치하는지, thesis_id가 정직한지, prediction_date가 실제 동결일인지, 해시
무결성이 유효한지 검증. 전체 스위트 441개 전부 통과. **`engine/`는 한 줄도
안 건드렸다**(순수 데이터 동결) — `ENGINE_VERSION` 변경 없음.

## VALIDATION DATA / HOLDOUT DATA

지금은 없다. 이게 정확히 이 개선이 만드는 것 — **미래의** validation
data(3/6/12개월 뒤)의 시작점.

## SUCCESS CRITERION

3개월 이내 최소 5건 이상 실적 발표가 나와 `resolve_prediction()`으로
해소 가능해질 것. 해소된 예측들의 `forecast_error` 분포가 기존
growth_scorecard 17건(비봉인)의 오차 분포와 **유사한 크기**로 나올 것
(전혀 다른 크기라면 CAGR-구성요소 범위 방식 자체가 잘못 설계된 것).

## FAILURE CRITERION

3개월 뒤에도 아무도 `resolve_prediction()`을 호출하지 않아 34건이
전부 OPEN으로 남아 있다면, "인프라를 만들면 쓰인다"는 가정 자체가
틀렸다는 뜻이다 — 그 경우 다음 우선순위는 **자동 해소 스케줄러**
(정기적으로 SEC 신규 공시를 조회해 자동으로 해소 후보를 찾는 것)가
돼야 한다. 이번엔 만들지 않았다 — 이 34건으로 먼저 "수동 해소가
실제로 일어나는지" 관찰하는 게 우선이라 판단했다(§53: 복잡성은 비용).
