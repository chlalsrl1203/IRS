# CHANGELOG

## v3.16 (반영일: 2026-07-25) — v3.9→v3.16 재구성 완료

confidence_score()를 v3.15와 동일한 원칙으로 하드닝. robustness_check_passed/
section_5_7_aligned 순수 bool 파라미터를 제거하고, expectation_gap_sensitivity_check()의
실제 반환 dict(sensitivity_check_result)와 gap/rar 실수치를 직접 받아 함수
내부에서 정합성을 계산하도록 변경. 구 방식 호출은 TypeError.

claim/lock 프로토콜을 CLAUDE.md에 문서화(원 배경: VRSN/ROP 중복 분석 사고).

**이번 재구성 전체 요약**: v3.9(검증된 원문 복원) → v3.13(stalwart+two_stage
구조적 편향 플래그, 원문 그대로) → v3.14(confidence_score 최초 도입, 원본
소실로 스펙 기반 재설계) → v3.15(self_check_v2로 장식용 검증 교체) →
v3.16(confidence_score 하드닝 + claim/lock 프로토콜). v3.10/3.11/3.11.1/3.12는
근거 없어 결번 처리, v3.17/3.18은 이 저장소에 어떤 형태로도 존재하지 않아
사용 보류.

## v3.15 (반영일: 2026-07-25)

run_self_check(answers: dict)가 장식용(decorative)이었음이 감사로 확인됨 —
불리언 자기신고만 받고 메모 텍스트를 전혀 검증하지 않아, 18개 호출
인스턴스 전체에서 실질적 검증 기능을 하지 못했음. self_check_v2.py 신규
도입: run_self_check_v2(memo_text, ctx)가 메모 원문에서 Implied
Growth/Realistic Growth/Expectation Gap/DRS/RAR 수치를 직접 파싱해 계산
컨텍스트와 대조하고, Bear Case 섹션·최종 결론 존재 여부까지 검증하는 7개
실제 체크를 수행. 기존 run_self_check()는 DEPRECATED 표시 후 코드에는
보존(과거 메모 참고용), 신규 분석에서는 사용 금지.

## v3.14 (반영일: 2026-07-25)

confidence_score() 신규 도입. **주의: 이 함수의 원래 원본 코드는 세션
파일시스템 리셋으로 소실되어 존재하지 않음.** 남아있던 근거는 스펙 조각뿐
(base=50 확정, base=70은 점수가 80~90대에 몰려 구분력 상실 확인됨, ANET
종목에서 최초 재현 Confidence=71). 2026-07-25에 이 스펙에 맞춰 가산/감산
항목을 새로 설계해 재구성. 원본과 정확히 같다는 보장 없음 — 향후 재검증
시 이 사실을 감안할 것.

## v3.13 (반영일: 2026-07-25, 원 배경: CTAS/AME 등 실전 stalwart 분석)

stalwart 유형이 two_stage 모델에서 구조적으로 음수 RAR을 보이는 패턴을
확인. min_spread 가드가 거의 모든 stalwart 기본 시나리오에서 발동하는
것이 원인. 모델은 그대로 유지하되(model="two_stage" 기본값), 이 편향을
`check_stalwart_two_stage_bias()`로 감지해 메모에 명시적으로 플래그하도록
강제. 근본 원인을 숨기지 않고 문서화하는 방향으로 대응(v3.16 이후 정신과
동일 원칙 선반영).
