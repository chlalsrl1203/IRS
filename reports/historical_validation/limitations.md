# Limitations — STOP CONDITIONS 공식 기록

작성일: 2026-08-16

§66이 요구한 대로, 결과를 억지로 만들어내는 대신 방법론적 한계를 정직하게
기록한다. 각 항목은 "지금 해결 불가"와 "재개 조건"을 구분한다.

## 발동된 STOP CONDITION

| # | 조건 | 근거 | 재개 조건 |
|---|---|---|---|
| 1 | historical source availability cannot be established | 전체 프로젝트 이력이 22일(2026-07-25~08-16)뿐. "역사적" 소스 자체가 존재하지 않는다 | 시간 경과 외에 방법 없음 |
| 2 | sample size is insufficient | 실제 T0→결과 관측 **17건**(9~11일 단기), 진입가 보유 9/34, 수익률 관측 0건 | 종목당 1건씩이라도 12개월 경과 필요 |
| 3 | holdout is no longer untouched | **홀드아웃이 존재한 적이 없다** — 개발/검증/홀드아웃 분할 자체가 불가능한 표본크기 | H-001 계열 실험이 사전등록한 재개조건(분위당 5건 이상, 12개월 경과) 충족 시 |

## 발동되지 않았으나 근접한 조건

- **restatement contamination**: 재무제표 재작성 대조 수단이 이 저장소에 없다
  (`docs/change_plan.md` C-09, DEFERRED로 이미 문서화됨). 이번 감사에서 이
  문제가 실제로 발현된 사례는 발견하지 못했으나, **찾을 수단 자체가 없어서**
  발견하지 못한 것이지 없다고 확인한 것이 아니다. [NO EVIDENCE] ≠ [확인됨]
- **survivorship bias**: 34종목 전부 현재 시점 스크리닝 생존자다(상장폐지·
  피인수 종목 없음). §8이 요구한 대로 SURVIVORSHIP LIMITATION으로 명시한다 -
  대표성을 주장하지 않는다.
- **benchmark selection**: 아웃컴 데이터 자체가 없어 벤치마크 선정 시점의
  outcome-dependent 여부를 판정할 필요조차 없었다(발동 전 단계).

## PIT 관련 - 이번 감사에서 새로 확인된 사실

`docs/AUDIT_2026-08-15_investment_value.md`와 CLAUDE.md v3.47/v3.49는
"기존 34종목은 PIT_UNKNOWN"이라 서술했다. 이번 감사(Phase 1)가 실제
ledger JSON을 파싱해 확인한 결과:

```
meta.point_in_time 키 존재: 0/34
```

**[CODE-VERIFIED]** 34종목 전부 `PIT_UNKNOWN` 상태값이 아니라 **필드 자체가
없다.** 결과적 의미(PIT 검증 안 됨)는 같지만, 메커니즘 서술이 부정확했다 —
`PIT_UNKNOWN`은 v3.47이 신설한 `run_analysis()`가 반환하는 상태값인데, 이
34종목은 v3.19~v3.41 엔진으로 생성돼 v3.47 이후 재실행된 적이 없다. 문서를
정정한다(본 보고서가 정정 기록).

## `predictions/`·`thesis/` 디렉터리 부재

v3.48이 두 모듈을 신설하고 425개(현재 435개) 테스트로 검증했으나, **실제
투자 종목에 적용된 적이 없다.** 두 디렉터리는 파일시스템에 존재하지도
않는다(`ls`가 "No such file or directory" 반환, 이번 감사에서 확인).
이는 "완성된 기능이 검증됐다"와 "실사용됐다"가 다르다는 것을 보여주는
직접적 증거다 — `model_improvements.md`가 이 간극을 #1 우선순위로 다룬다.

## 이번 감사 자체의 한계

- 이 보고서가 인용하는 17건의 실제 관측(growth_scorecard 11 + falsification_scan 6)은
  **이번 감사가 새로 만든 것이 아니라 2026-08-13에 이미 생성돼 있던 것**을
  재검증·재분류한 것이다. 새 관측을 만들지 않았다 — 만들 수 없었다(관측
  대상 실적이 아직 발표되지 않았거나, 발표됐어도 이미 저 리포트들이 포착했다).
- 5-why 근본원인 분석(TTD)은 1개 사례에 대한 것이다. §38이 요구한 대로
  "RECURRING PATTERN"이나 "SYSTEMATIC FAILURE"라 부르지 않고
  "INDIVIDUAL ERROR"로 명시한다(표본 1건).
