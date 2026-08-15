# IRS Change Plan (Phase 0 산출물)

작성일: 2026-08-15
근거: `docs/system_audit.md`

분류 체계(계약서 11·12·6.1절):
- **Category**: SOFTWARE / DATA / MODEL / RESEARCH / DOCUMENTATION
- **Priority**: P0(정확성·무결성·재현성) / P1(연구품질) / P2(인프라) / P3(선택)
- **Status**: REQUIRED_NOW / REQUIRED_LATER / OPTIONAL / DEFERRED / UNRESOLVED / NOT_JUSTIFIED

---

## 요약표

| ID | Category | Pri | 제목 | Status |
|---|---|---|---|---|
| C-01 | SOFTWARE | P0 | EBITDA≤0에서 레버리지 위험 반전 | REQUIRED_NOW |
| C-02 | DATA | P0 | ledger 같은 날짜 무경고 덮어쓰기 | REQUIRED_NOW |
| C-03 | SOFTWARE | P0 | 보험사 유보율 정의역 미검증 | REQUIRED_NOW |
| C-04 | SOFTWARE | P0 | 결정성 테스트 부재 | REQUIRED_NOW |
| C-05 | MODEL | P1 | 휴리스틱/미검증 지위 표기 없음 | REQUIRED_NOW |
| C-06 | RESEARCH | P1 | `data_completeness_pct`가 상수로 굳음 | REQUIRED_NOW |
| C-07 | DOCUMENTATION | P1 | README가 engine/ 12개 중 3개만 기술 | REQUIRED_NOW |
| C-08 | SOFTWARE | P2 | DEPRECATED `run_self_check()` 잔존 | OPTIONAL |
| C-09 | DATA | P2 | Provenance(수치 단위 출처 추적) | DEFERRED |
| C-10 | DATA | P2 | Point-in-Time 상태 관리 | DEFERRED |
| C-11 | RESEARCH | P2 | Historical Replay | DEFERRED |
| C-12 | RESEARCH | P3 | Outcome Validation / Calibration | DEFERRED |
| C-13 | SOFTWARE | P3 | RAW/NORMALIZED/DERIVED 3계층 분리 | NOT_JUSTIFIED |
| C-14 | SOFTWARE | P3 | Database 도입 | NOT_JUSTIFIED |
| C-15 | DATA | P0 | 시총 스케일/통화 오류가 무경고 통과 | **DONE (v3.46 Phase 2)** |

---

## C-01. EBITDA ≤ 0에서 레버리지 위험이 반전됨

- **Category**: SOFTWARE (도메인 검증 누락) · **Priority**: P0 · **Status**: REQUIRED_NOW
- **Current Behavior**: `pipeline.py:447`이 가드 없이 `net_debt / ebitda`를
  계산한다. EBITDA가 적자면 비율이 음수가 되고 `leverage_score()`는 이를
  "순현금"으로 해석해 최저 위험점수(2.0)를 준다. EBITDA=0이면 원인 설명 없는
  `ZeroDivisionError`가 난다.
- **Expected Behavior**: EBITDA ≤ 0은 `net_debt/EBITDA`가 **정의되지 않는
  정의역**이므로 계산을 거부하거나(예외), 최소한 레버리지 항목을 제외하고
  그 사실을 기록해야 한다. 순현금(net_debt<0, EBITDA>0)은 정상 경로로 유지.
- **Evidence**: 동일 기업 순부채 +$30억 기준 — EBITDA −$5억 → leverage 2.0 /
  DRS 22.4(경고 없음), EBITDA +$5억 → leverage 20.0 / DRS 40.4.
  `docs/system_audit.md` FM-1 재현표.
- **Impact**: DRS는 ERP·할인율·Implied Growth·Gap·판정·시나리오확률·
  Confidence·RAR 전부를 타고 흐른다. 부실기업일수록 안전하게 평가되는 방향의
  오류라 가장 위험한 유형이다. **과거 영향 없음**(34/34 ledger가 EBITDA>0).
- **Proposed Change**: `AnalysisInputs.__post_init__`에 EBITDA ≤ 0 거부 가드를
  추가한다(capex 음수 가드와 동일 위치·동일 양식). 예외 메시지에 왜 정의되지
  않는지와 대안(해당 항목 제외 후 `excluded_reasons` 기록)을 명시한다.
- **Complexity**: 낮음(가드 1개, 계산 로직 무변경).
- **Test Plan**: ① EBITDA 음수 거부 ② EBITDA 0 거부 ③ **순현금(net_debt<0,
  EBITDA>0)은 계속 통과**하고 leverage 점수 2.0을 유지(회귀 방지) ④ CDNS
  골든테스트 불변.
- **BUG FIX vs MODEL CHANGE**: **BUG FIX**. `leverage_score()`의 명세("순현금이면
  최저점")를 EBITDA>0 전제 하에 구현했는데 그 전제가 강제되지 않았던 것이다.
  점수 규칙 자체는 바꾸지 않는다.

## C-02. `save_ledger()`가 같은 날짜 분석을 경고 없이 덮어씀

- **Category**: DATA (기록 무결성) · **Priority**: P0 · **Status**: REQUIRED_NOW
- **Current Behavior**: 파일명이 `<TICKER>_<날짜>.json`이라 같은 날 재실행하면
  경로가 충돌하고 이전 내용이 조용히 사라진다.
- **Expected Behavior**: 덮어쓰기는 **의도했을 때만** 일어나야 하고, 의도하지
  않은 덮어쓰기는 차단되어야 한다.
- **Evidence**: Gap +0.10 저장 → Gap −0.30 저장 시 파일 1개만 남고 내용은
  후자. 경고·예외·백업 없음(`docs/system_audit.md` FM-2 재현).
- **Impact**: 계약서 5.4/63절 정면 위배. 과거 발생 여부는 **NOT_VERIFIABLE** —
  사후 확인 수단이 저장소에 없다는 것 자체가 이 결함의 성질이다.
- **Proposed Change**: `save_ledger(..., overwrite: bool = False)` 기본값을
  **거부**로 바꾸고, 기존 파일이 있으면 예외를 던진다. 예외 메시지에 (a) 의도한
  갱신이면 `overwrite=True`를 명시하라는 안내와 (b) 내용이 동일하면 그대로
  통과시킨다는 사실을 담는다.
  - **내용이 완전히 동일하면(타임스탬프 제외) 예외 없이 통과**시킨다 — 재실행
    검증(같은 입력으로 다시 돌려 값이 같은지 확인하는 이 프로젝트의 표준 관행)이
    깨지면 안 되기 때문이다.
- **Complexity**: 낮음. 다만 26개 스크립트가 `save_ledger()`를 호출하므로
  **기본값을 거부로 바꾸면 기존 스크립트 재실행이 막힌다** → 동일 내용은 통과
  시키는 설계로 이 부작용을 없앤다.
- **Test Plan**: ① 신규 저장 성공 ② 동일 내용 재저장은 예외 없이 통과
  ③ 다른 내용 재저장은 예외 + 원본 보존 ④ `overwrite=True`면 갱신 허용.
- **BUG FIX vs MODEL CHANGE**: **BUG FIX**(기록 무결성 규약을 코드가 지키지
  않던 것). 판정 계산에는 영향 없음.

## C-03. 보험사 유보율이 정의역(0~1)을 벗어나도 통과

- **Category**: SOFTWARE (도메인 검증 누락) · **Priority**: P0 · **Status**: REQUIRED_NOW
- **Current Behavior**: `payout_ratio = total_dividends / total_net_income`에
  가드가 없다. 3년 창에 손실 연도가 섞이면 유보율 2.50 또는 −0.20 같은 값이
  나오고 그대로 지속가능성장률에 곱해진다.
- **Expected Behavior**: 합산 순이익 ≤ 0이면 배당성향이 정의되지 않으므로
  교차검증을 수행하지 않고 그 사실을 `data_limitations`에 남긴다. 유보율이
  0~1을 벗어나면 경고한다.
- **Evidence**: `docs/system_audit.md` FM-3 재현표(순이익 합계 −200 →
  유보율 +2.50 → 지속가능성장률 30%).
- **Impact**: 대재해 노출 재보험사에서 현실적으로 발생 가능. **과거 영향
  없음**(ACGL·PGR 모두 순이익 음수 연도 0건).
- **Proposed Change**: 합산 순이익 ≤ 0이면 `insurer_cross_check`를 계산하지
  않고 `data_limitations`에 사유 기록. 계산되더라도 유보율이 [0,1] 밖이면 경고.
- **Complexity**: 낮음.
- **Test Plan**: ① 손실 연도 포함 시 교차검증 스킵 + 한계 기록 ② 배당>순이익
  시 경고 ③ ACGL/PGR 골든값 불변.
- **BUG FIX vs MODEL CHANGE**: **BUG FIX**.

## C-04. 결정성 테스트 부재

- **Category**: SOFTWARE · **Priority**: P0 · **Status**: REQUIRED_NOW
- **Current Behavior**: 엔진은 실제로 결정적이지만(실측 확인) 이를 고정하는
  테스트가 없다.
- **Expected Behavior**: 동일 입력 2회 실행 시 `meta.analyzed_at`을 제외한
  전 필드가 동일함을 테스트가 보장한다.
- **Evidence**: 동일 입력 2회 실행 결과 `analyzed_at`만 상이, 나머지 완전 일치.
  `grep` 결과 결정성 테스트 0건.
- **Impact**: 계약서 58·111절이 요구하는 재현성의 최소 보장 장치가 없다.
- **Proposed Change**: `tests/test_pipeline.py`에 결정성 테스트 추가.
- **Complexity**: 낮음. **Test Plan**: 그 자체가 테스트.
- **BUG FIX vs MODEL CHANGE**: 둘 다 아님(테스트 추가).

## C-05. 휴리스틱/미검증 모델의 인식론적 지위 표기

- **Category**: MODEL · **Priority**: P1 · **Status**: REQUIRED_NOW
- **Current Behavior**: `erp_from_drs()` docstring은 "고정 규칙, 임의 조정 금지"
  라는 **규범**만 말하고, 이 매핑이 경험적으로 검증된 적 없는 휴리스틱이라는
  **사실**은 말하지 않는다. `confidence_score()`도 calibration 여부를 표기하지
  않는다.
- **Expected Behavior**: 계약서 36·40·50절대로 `HEURISTIC_MAPPING` /
  `UNCALIBRATED` 지위를 코드에 명시한다.
- **Impact**: 다음 분석자가 ERP 매핑을 경제이론적 사실로 오인하거나
  Confidence 85를 "85% 확률"로 오독할 위험.
- **Proposed Change**: 두 함수의 docstring에 지위 라벨과 근거 부재 사실을
  명시(계산 무변경). `VALIDATION_STATUS` 상수로 기계 판독 가능하게 남긴다.
- **Complexity**: 낮음(순수 문서화 + 상수).
- **Test Plan**: 상수 존재·값 검증(문서가 조용히 사라지지 않게).
- **BUG FIX vs MODEL CHANGE**: 둘 다 아님 — 계산을 바꾸지 않는 **문서화**다.
  ⚠️ 여기서 ERP 매핑 숫자를 "더 나은 값"으로 바꾸는 것은 계약서 5.2절
  (금융 가정 발명 금지) 위반이므로 **하지 않는다**.

## C-06. `data_completeness_pct`가 사실상 상수로 굳음

- **Category**: RESEARCH · **Priority**: P1 · **Status**: REQUIRED_NOW
- **Current Behavior**: 기본값 0.9를 ledger 34종목 **전부**가 그대로 쓴다.
  `confidence_score`에서 무조건 14/100점이 부여된다.
- **Expected Behavior**: Confidence가 "데이터 완전성을 반영한다"고 표방한다면
  그 축에서 실제 판별력이 있어야 한다. 아니라면 그 사실이 드러나야 한다.
- **Evidence**: 34/34 종목 값 0.9(실측).
- **Impact**: False Precision(계약서 3절). Confidence 점수가 실제보다 더 많은
  정보를 담은 것처럼 보인다.
- **Proposed Change**: **자동 계산하지 않는다**(무엇이 "완전한 데이터"인지에
  대한 근거가 이 프로젝트에 없다 — 근거 없는 새 공식은 계약서 5.2절 위반).
  대신 기본값을 그대로 쓴 경우 `data_limitations`에 "기본값이 사용됐으며 이
  분석의 Confidence 14점은 실측이 아니다"를 남긴다.
- **Complexity**: 낮음.
- **Test Plan**: ① 기본값 사용 시 한계 기록 ② 명시적으로 값을 넣으면 기록
  없음 ③ Confidence 점수 자체는 불변(골든테스트).
- **BUG FIX vs MODEL CHANGE**: 둘 다 아님 — **가시화**다. 점수는 바꾸지 않는다.

## C-07. README가 실제 구조를 반영하지 않음

- **Category**: DOCUMENTATION · **Priority**: P1 · **Status**: REQUIRED_NOW
- **Current/Expected**: README는 `engine/` 3개 파일만 기술 / 실제 12개.
- **Proposed Change**: 실제 모듈 목록과 역할을 반영하고 `docs/` 산출물을 링크.
- **Complexity**: 낮음. **Test Plan**: 해당 없음(문서).

## C-08. DEPRECATED `run_self_check()` 잔존

- **Priority**: P2 · **Status**: OPTIONAL
- 호출부 0건이며 DEPRECATED 주석이 명확하다. 제거해도 이득이 작고, 과거 메모
  이력 해석용으로 남겨둔다는 기존 판단에 반박할 근거를 찾지 못했다. **보류.**

## C-09 / C-10 / C-11. Provenance · Point-in-Time · Historical Replay

- **Priority**: P2 · **Status**: DEFERRED
- **Deferral 사유**(계약서 6.2절):
  1. 현재 원자료가 분석 스크립트 내 dict 리터럴로만 존재해, Provenance를
     제대로 하려면 **데이터 수집 계층 자체를 신설**해야 한다. 이는 최소 변경이
     아니라 아키텍처 재작성이며 계약서 6.3절이 요구하는 정당화를 충족하지 못한다.
  2. Point-in-Time은 `filing_date`를 확보해야 성립하는데, 과거 34종목의
     filing_date는 지금 알 수 없다. 계약서 22절대로 `PIT_UNKNOWN`으로 두어야
     하며, 이 상태에서 replay를 만들면 "PIT 검증됨"이라는 허위 표시를 낳는다.
  3. Historical Replay는 1·2가 선행되지 않으면 계약서 70절의 7개 조건 중
     3개(source timing verifiable / no future info / input snapshot
     reconstructable)를 만족할 수 없다.
- **재개 조건**: 새 분석부터 `filing_date`·`retrieval_date`를 수집하는 관행이
  자리잡고 최소 1개 종목이 7개 조건을 모두 만족할 때.

## C-12. Outcome Validation / Confidence Calibration

- **Priority**: P3 · **Status**: DEFERRED
- **사유**: 계약서 75·78절이 요구하는 전제(충분한 표본, out-of-sample 기간,
  bias 분석)를 만족할 데이터가 없다. 분석 이력이 약 3주이며 반증조건 검증
  사례는 5건(thesis_monitor 1차 실행)뿐이다. 지금 calibration을 만들면
  표본 5건으로 확률을 주장하는 것이 되어 계약서 138절 위반이다.
- **이미 진행 중인 전제조건**: `falsification_conditions`,
  `price_at_analysis`(v3.24), `thesis_monitor`(v3.42),
  `growth_scorecard`(v3.43)가 그 토대다.

## C-13. RAW/NORMALIZED/DERIVED 3계층 분리

- **Priority**: P3 · **Status**: NOT_JUSTIFIED
- **사유**: 계약서 8절 7개 질문 중 "현재 구조로 해결할 수 없는 이유"에 답할 수
  없다. 현재 `AnalysisInputs`가 정규화된 입력을, `derived`가 파생값을 이미
  분리 보관한다. RAW를 별도 계층으로 만들려면 데이터 수집 자동화가 선행돼야
  하고(C-09와 동일 장벽), 그전까지는 계층만 늘고 실익이 없다.

## C-14. Database 도입

- **Priority**: P3 · **Status**: NOT_JUSTIFIED
- **사유**: 계약서 113절. 현재 규모(회사 34 + ETF 23 + KRX 31 = 88개 JSON)에서
  JSON 파일로 충분하며, 동시성 요구가 없고, `test_ledger_integrity.py`가 이미
  무결성을 검증한다. DB 도입은 재현성을 오히려 낮춘다(파일은 git으로 버전
  관리되지만 DB는 아니다).

---

## Phase 1 실행 순서

P0(C-01 → C-03 → C-02 → C-04) → P1(C-05 → C-06 → C-07).
각 변경마다: 구현 → 테스트 추가 → 전체 회귀(255개) → 골든값 불변 확인 → 문서화.

**금지 사항 재확인**: 이번 Phase에서 ERP 매핑값, Lynch 캡, 판정 경계(±5%p),
DRS 가중치, RAR 공식은 **하나도 바꾸지 않는다**. 전부 근거가 없거나(계약서
5.2절) 과거 기록과의 비교가능성을 깨기 때문이다(단위 규약).


---

## C-15. 시가총액 스케일/통화 오류가 경고 없이 판정까지 흘러감

- **Category**: DATA (무결성) · **Priority**: P0 · **Status**: DONE (v3.46 Phase 2)
- **발견 경위**: 감사 D-3(통화 혼재)을 검증하다 발견. PDD(CNY)는 재무제표·시총이
  모두 CNY로 내부 정합했으나, **혼재를 잡아줄 장치가 없다**는 점을 확인하려다
  single_stage 경로의 조용한 실패를 실측했다.
- **Current Behavior (수정 전, BRO 실데이터)**:

  | 시나리오 | FCF수익률 | Gap | 판정 | 경고 |
  |---|---|---|---|---|
  | 정상 | 6.03% | +7.43%p | 저평가 | — |
  | 통화혼재(÷7.1) | 42.79% | **+34.35%p** | 저평가(A→S등급) | 없음 |
  | 100배 과소 | 602.62% | **+96.22%p** | 저평가(1위감) | 없음 |
  | 100배 과대 | 0.06% | +1.19%p | **적정가로 뒤집힘** | 없음 |

  two_stage는 이분탐색이 해를 못 찾아 우연히 막히지만, 오류 메시지가
  "r/N/g_terminal을 재검토하라"고 **엉뚱한 원인을 가리킨다**(계약서 107절 위배).
- **Evidence**: 이 프로젝트는 같은 계열 사고를 이미 두 번 겪었다 — RAR 100배
  (4종목), TYL SBC 3배(2차 출처 인용 오류).
- **Proposed/Implemented Change**: `check_scale_plausibility(fcf0, market_cap)`
  순수 함수 신설 + `run_analysis()`에서 호출해 `data_limitations`에 기록.
  **자동보정·실행차단 없음**(계약서 30절).
- **밴드 근거(임계값 발명 아님)**: ledger 34종목 실측 FCF수익률 1.50%(KLAC)~
  17.95%(ACGL), 중앙값 5.64%. 밴드는 0.5~25%로 하단 3배·상단 1.4배 여유를 둬
  **34종목 중 어느 것도 발동하지 않음**을 테스트로 고정했다.
- **⚠️ 알려진 한계(테스트로 고정, 임계값 조정으로 회피하지 않음)**:
  탐지 여부가 그 종목의 **기저 FCF수익률에 의존**한다.

  | 종목(기저) | ×7.1 결과 | 탐지 |
  |---|---|---|
  | CDNS(1.71%) | 12.14% | **실패** — PDD 정상값 12.94%와 겹침 |
  | KLAC(1.50%) | 10.65% | **실패** |
  | BRO(6.03%) | 42.81% | 성공 |
  | PGR(13.71%) | 97.34% | 성공 |

  **어떤 임계값으로도 분리 불가능**하다. 즉 이 가드는 **자릿수(≈100배) 오류의
  안전망일 뿐 통화 오류 전반을 막지 않는다.** 비USD 종목(PDD=CNY, ONON=CHF)은
  `currency` 필드와 수작업 대조가 여전히 필요하다.
  테스트 `test_scale_check_currency_error_detected_only_above_yield_floor`가
  이 한계를 사실 그대로 고정한다.
- **검증**: 34종목 전건 재실행 8개 지표 1e-12 일치, ledger 무수정. 테스트 265→270.
