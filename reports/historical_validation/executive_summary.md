# Executive Summary — Point-in-Time Historical Replay 감사

작성일: 2026-08-16 · 대상 커밋: 실행 시점 `main` HEAD

## 한 줄 결론

**진짜 Historical Replay(§2의 A/B/C 실험)는 지금 수행할 수 없다** — 데이터
품질 문제가 아니라 전체 프로젝트 이력이 22일이라 미래가 아직 오지 않았기
때문이다(`limitations.md` STOP CONDITION 공식 발동). 대신 (1) 실제로 존재하는
17건의 초단기(9~11일) T0→결과 관측을 엄격 재분석했고, (2) 기존 감사 주장
5건을 독립 재현해 전부 일치시켰으며, (3) 이 프로젝트가 안고 있던 진짜
구조적 공백(예측 인프라 실사용 0건)을 찾아 최소한의 방식으로 메웠다.

## §0 원칙 적용 결과 — 문서 서술과 코드 사실의 괴리 2건 발견

| 문서 서술(DOCUMENTED CLAIM) | 코드 실측(CODE-VERIFIED FACT) |
|---|---|
| "기존 34종목은 PIT_UNKNOWN" | `meta.point_in_time` 키 **자체가 없음** — 상태값이 아니라 필드 부재(v3.47 이전 엔진으로 생성돼 재실행 안 됨) |
| "예측/논거 인프라 완성"(v3.48) | `predictions/`·`thesis/` **디렉터리 자체가 존재하지 않음** — 완성됐으나 실사용 0건 |

두 괴리 모두 이번 감사가 정정 기록으로 남겼다(`limitations.md`).

## §60 최종 스코어카드 — 축별 분리 (단일 점수 만들지 않음, §61)

§61의 요구대로 단일 "IRS 점수"를 만들지 않는다. 대신 이번 감사가 실제로
측정할 수 있었던 축만 보고한다:

| 축 | 상태 | 근거 |
|---|---|---|
| Reproducibility | **강함** | 5개 핵심 주장 100% 재현 일치(`baseline_comparison.md`) |
| Forecast accuracy(단기) | 약함, 표본극소 | n=10, abs error 중앙값 8.7~10.9%p, [표본 부족으로 결론 보류] |
| Decision Robustness | 중간 | DRS 영향 3% ≪ 모델선택 영향 32% ≪ 구조적할인/캡 영향 12% — 셋의 상대순위는 명확, 절대적 "충분함" 여부는 미판정 |
| Decision Attribution(§36 컴포넌트) | 6건 중 정오 판정 가능 4건(CORRECT 2, INCORRECT 1, PARTIALLY 1), UNRESOLVED 2건 | `decision_attribution.md` |
| Decision Attribution(§63 최종성과) | **전건 INCONCLUSIVE** | 수익률 데이터 0건 |
| Out-of-Sample Validity | **없음** | §66 STOP |
| PIT Integrity | 인프라 있음/데이터 없음 | 34/34 필드부재 |
| Data Provenance | 인프라 있음/데이터 없음 | 34/34 미기록 |

## §64 시스템 실패 순위 — 정당화된 공식 없이 축별 보고

빈도×심각도×투자영향×탐지격차의 임의 정규화 공식을 만들지 않는다(§64
명시적 금지). 대신 순서만 보고한다(정성적 순위, 가중치 없음):

1. **예측/논거 인프라 실사용 0건** — 빈도: 프로젝트 전체(34/34) / 탐지격차: 큼(아무도 몰랐음) / 이번에 조치함
2. **모델선택 재량이 판정의 32% 결정** — 빈도: 34종목 중 11 / 탐지격차: 중간(v3.51이 이미 노출시킴)
3. **PIT/Provenance 서술-실제 괴리** — 빈도: 34/34 / 탐지격차: 이번 감사로 처음 노출
4. **구조적할인율(HEURISTIC)이 판정의 12% 결정** — 신규 발견(`ablation_analysis.md`), 미해결

## #1 우선순위 조치 (§65)

`model_improvements.md` 참고. **34종목 예측을 오늘(2026-08-16) 봉인**해
3~12개월 뒤 진짜 검증의 시작점을 만들었다. 새 밸류에이션 로직 0줄,
`engine/` 무변경, 테스트 441개 전부 통과, 34종목 8지표 골든재현 무변동.

## 다음 감사가 반드시 할 일

1. `predictions/` 34건 중 해소 가능한 것부터 `resolve_prediction()` 실행(3개월 뒤~)
2. ~~이번에 신규 발견한 `structural_discount_rate()` 12% 영향력에 대한 경제적
   근거 조사~~ — **2026-08-16 완료(v3.52)**. trend_delta 메커니즘은
   Chan/Karceski/Lakonishok(JF 2003)로 `ECONOMICALLY_SUPPORTED` 승격, 초대형주
   가산(+3%p/+1%p)은 근거 못 찾아 `IMPLEMENTED_NOT_VALIDATED` 유지 - 코드는
   무변경, 라벨만 정직화. 상세는
   `reports/historical_validation/structural_discount_research.md`.
3. ~~TCOM류 "조합축에서만 취약한" 6종목(`ablation_analysis.md`)의 개별 축
   분해~~ — **2026-08-16 완료**. BRO·COR·TYL·VRSN은 model_choice+discount_rate
   2축 조합, TCOM은 model_choice가 빠진 3축(discount_rate+terminal_growth+
   growth_duration_n), ZTS는 4축 전부가 필요(30격자 중 1지점만 flip, 6종목 중
   가장 강건). 공통 메커니즘: 각 축은 단독으로는 ±5%p 경계를 못 넘지만 같은
   방향으로 겹치면 넘는다 - 상세는
   `reports/historical_validation/combination_flip_decomposition.md`.
