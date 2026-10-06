# 정성평가 표준입력 구현 브리프 (QSI v1) — 초안, 승인 전

작성일: 2026-10-06 · 상태: **프롬프트 초안(코드 변경 없음)** · 승인 후 구현

## 0. 목적 한 줄

종목마다 제가 WebSearch로 즉흥 조사해 `portfolio/qualitative_overrides.json`에 자유서술로 적던 정성평가를,
**고정된 질문 · 필수 인용 · 빈칸 허용(미확인 명시)** 형식의 **구조화 입력**으로 바꾼다.
그 입력이 (a) `engine/research_lenses.py`의 `QualitativeReview`, (b) `engine/scorecard_core.py`의 B(해자)·C(품질)·D(경영진) 하위지표 입력,
(c) `engine/thesis.py`의 근거 게이트로 **같은 데이터에서 파생**되게 한다.

## 1. 하지 않는 것 (§31 + 기존 원칙, 어기면 실패)

- **단일 종합점수·종합 정성등급 금지.** 축별 값만 낸다. 합산 함수·`overall`·`total` 류 공개 이름 금지(AST 테스트).
- **Gap·RAR·등급·Confidence·비중을 자동 변경 금지.** "병기, 자동판정 안 함". 정성값은 `reports/`·`portfolio/`에만 남고 `run_analysis()`에 배선하지 않는다.
- **런타임 의존성 0개**(stdlib만). LLM API 호출을 코드에 넣지 않는다 — 조사는 세션 안에서 사람/Claude가 하고, 코드는 **형식 검증과 저장**만 한다.
- **소급 작성 금지.** 기존 33종목 정성조사를 새 스키마로 "다시 써서" 사후합리화하지 않는다. 신규 분석부터 적용, 기존분은 `LEGACY_FREEFORM`으로 라벨만.
- **추측으로 빈칸 채우기 금지.** 확인 못하면 `not_examined`/`unknown`으로 둔다(P0-01 UNVERIFIED와 동일).

## 2. 재사용할 기존 자산 (새로 만들지 않는다)

| 자산 | 용도 |
|---|---|
| `engine/evidence.py` — `Citation`(location 필수) · `Evidence` · `Claim` · `EvidenceMatrix` | 모든 정성 주장의 근거 계약. 2차 출처의 `VERIFIED_PRIMARY` 표시 불가, 반대 증거 우선, 삼각검증은 서로 다른 출처 2개 |
| `engine/research_lenses.py` — `STANDARD_LENSES`(5축) · `SECTOR_LENS_OVERRIDES` · `LensFinding`(`not_examined` 1급) · `Disqualifier` · `QualitativeReview` | 정성 조사 1회의 컨테이너. 축은 **바꾸지 않는다**(33종목 축적 보존) |
| `engine/scorecard_core.py` 입력 필드(`spread_series`, `gm_cv_10y`, `share_trend_5y`, `kcg_compliance`, `honesty_checklist`, `opp_insider_net_*` …) | 해자·경영진 정량 입력의 목적지 |
| `engine/data/providers/sec.py` + `provenance.py` + `snapshot.py` | 수치 입력의 1차 출처·재현성 |
| `portfolio/qualitative_overrides.json` | 현행 레지스트리 — 스키마 이관 대상(삭제 아님) |

## 3. 새로 만들 것 (최소)

### 3.1 `engine/qualitative_input.py` (순수 함수, 새 계산 0줄)

**질문 은행(Question Bank)** — 축마다 고정 질문 5~7개. 자유서술 대신 질문별 답을 받는다.

- 질문 항목: `qid`, `lens`, `question`, `answer_type`(`enum|bool|number|text`), `allowed`(enum 값), `requires_primary`(bool)
- 답 항목: `qid`, `answer`, `status`(`answered|unknown|not_applicable`), `claim_ids`(필수 — answered일 때), `as_of`
- **`status=unknown`을 1급 값으로**. unknown이 많으면 `coverage`가 낮게 나와 그대로 노출(미조사를 안전으로 오독 금지).

축 매핑(기존 5축 유지 + scorecard 입력 연결):

| 축 | 질문 예 | scorecard 입력으로의 파생 |
|---|---|---|
| governance | 이중주식? 내부자 기회적 순매도/순매수? 진행 중 소송? 의장·CEO 분리? | `opp_insider_net_sell/buy`, `chair_separated`, `ceo_succession_policy` |
| capital_allocation | 자사주 매입 시점 규율? M&A 가격 규율? 배당 예측가능성? | `buyback_timing`, `div_predictable` |
| accounting_quality | 최근 3년 하향 재작성? 비신뢰 공시? 가이던스 미스? 공약 이행? | `honesty_checklist`(증거 URL 있는 항목만 반영 — 모듈 규칙 그대로) |
| dilution | SBC/FCF? 순주식수 증감(분할 보정)? | 기존 `engine/dilution.py` 값 인용(재계산 금지) |
| competitive_landscape | 신규 위협? 점유율 추세? 가격결정력 증거? | `share_trend_5y`, `lifecycle_shakeout_or_decline`, `key_person_no_succession` |

**산업 적합성 게이트** — 업종이 5축에 안 맞으면(`insurance`, `conglomerate` 외) 억지 적용하지 않고 `sector_fit="UNMAPPED"`로 표시, 해당 종목은 정성 입력 보류.

### 3.2 저장 위치

`qualitative/<TICKER>_<날짜>.json` (종목당 1건 유지 — ledger와 같은 무결성 규칙, `tests/test_ledger_integrity.py` 패턴으로 고정).
**코어는 불변(append-only)**: 질문·답·근거·`as_of`·봉인 해시. 수정은 새 날짜 파일.
봉인은 `engine/prediction_ledger.py::core_hash` 재사용(해시 로직 복제 금지).

### 3.3 `scripts/qualitative_intake.py` — 반자동 절차의 코드 쪽

1. 종목·업종을 받아 질문 은행에서 해당 축 질문 목록을 출력(조사 체크리스트).
2. 조사 결과 JSON을 받아 **검증만** 한다: 필수 인용 누락, `answered`인데 `claim_ids` 없음, 2차 출처를 1차로 표기, 미래 날짜 근거(`as_of` 이후 공시), 서술적 ISO 날짜가 `falsification_conditions`에 섞임(v3.42 함정).
3. 통과하면 `qualitative/`에 봉인 저장하고 `reports/qualitative_coverage.json`에 축별 `answered/unknown` 집계를 갱신.
4. **판정·비중은 건드리지 않는다.**

### 3.4 1차 출처 재검증 단계(수치 주장 한정)

- 판정 경계를 움직일 수 있는 **숫자 주장**(SBC 비율, 성장률, 가이던스, 지분 변동)은 `requires_primary=True` — 회사 IR 원문·SEC 공시로 재확인 후 `primary_source_verified`(날짜·URL) 기록.
- 근거: TYL SBC 3배 오류, RYAN 가이던스 오인용 — 둘 다 2차 출처 무검증 인용이었다.

## 4. 데이터 흐름

```
조사(WebSearch/공시, 세션 내) → qualitative_intake 검증 → qualitative/<T>_<날짜>.json(봉인)
      ├─→ QualitativeReview (research_lenses)    # 기존 계약
      ├─→ scorecard_core 입력 필드 파생           # B/C/D 하위지표(미배선 유지)
      └─→ thesis 근거 게이트(Evidence 연결)       # 결정 기록의 근거
reports/qualitative_coverage.json                 # 축별 answered/unknown 비율 노출
```

## 5. 검증 전략 (정밀함이 근거 없는 허구가 되지 않게)

- **지금 가능한 것**: 형식 무결성, 인용 필수, 미확인 가시화, 재현성(봉인 해시).
- **지금 불가능한 것(명시)**: "정성 점수가 성과와 관계있다"는 증거 0건. 따라서 `VALIDATION_STATUS = IMPLEMENTED_NOT_VALIDATED`를 모듈에 박고, 리포트가 매번 그 사실을 말한다.
- **미래 검증 연결**: 봉인 시점에 `price_at_analysis`·`analysis_as_of`를 같이 기록해 6~12개월 뒤 사전등록 실험(H-008 후보)이 쓸 수 있게 한다. 이 브리프 단계에서 실험은 **등록만**(결과 방향 미지정), 실행하지 않는다.
- 파일럿: 이미 정성조사를 한 S/A 종목 중 **3종목(예: ACGL·DLO·PGR — thesis 보유)** 을 신규 스키마로 **새 날짜로 재조사**해 형식이 현실 조사를 담는지 확인. 기존 서술은 수정하지 않고 `LEGACY_FREEFORM`으로 남긴다.

## 6. 구현 순서

1. 질문 은행 + 검증 함수 + AST 경계 테스트(점수 함수·종합 금지, 자동 판정 금지, 의존성 0).
2. `qualitative_intake.py`(검증·봉인·커버리지 리포트).
3. 파일럿 3종목 실행 → 실패 지점 수정.
4. `qualitative_overrides.json` → 신규 스키마 이관 어댑터(기존 18종목은 `LEGACY_FREEFORM` 라벨).
5. `scorecard_core` 입력 파생 어댑터(**배선 아님** — 입력 dict 생성까지만).
6. CLAUDE.md 절 추가, `ENGINE_VERSION` v3.92 → v3.93(engine/ 변경 시 필수), baseline 골든재현.

## 7. 완료 기준 (전부 충족해야 완료)

- [ ] 테스트 전체 통과 · 34종목 골든재현 8지표 불일치 0 · baseline fingerprint 불변 · `ledger/`·공식 판정 0건 수정
- [ ] 질문 은행이 5축(+insurance/conglomerate 변형)을 모두 덮고, 각 질문에 `requires_primary` 지정
- [ ] `unknown`이 숨겨지지 않음: 커버리지 리포트에 축별 answered/unknown 노출
- [ ] 종합점수·자동판정·LLM 호출·외부 의존성이 코드에 없음(AST 테스트)
- [ ] 파일럿 3종목이 신규 스키마로 봉인되고, 재조사 중 발견된 1차 출처 불일치는 숨기지 않고 기록
- [ ] `docs/` 및 CLAUDE.md에 "무엇이 검증 안 됐는가"를 명시

## 8. 열린 결정 (구현 전 사용자 확인)

1. 조사 방식: **반자동(Claude가 웹검색으로 채우고 코드가 검증)** 권장 vs 사람이 직접 채우는 체크리스트.
2. 파일럿 종목 3개: ACGL·DLO·PGR 제안(thesis·정성조사가 이미 있어 대조 쉬움). 보유 종목(PTC 등)을 우선할지.
3. `scorecard_core` 배선은 이번 범위에서 제외(권장). 입력 파생까지만.
4. 한국 종목(DART)은 P0-04 DEFER 유지 — 이번 범위 밖.
