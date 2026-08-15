# IRS Invariants

작성일: 2026-08-15

계약서 14절 준수: **현재 코드가 실제로 보장하는 조건**과 **향후 보장해야 할
조건**을 엄격히 분리한다. 코드에 존재하지 않는 invariant를 사실인 것처럼
적지 않는다. 각 항목은 강제 위치(파일·함수)와 검증 수단(테스트)을 명시한다.

---

## A. 현재 코드가 실제로 강제하는 불변조건 (ENFORCED)

실행 또는 테스트로 확인한 것만 기록한다.

### A-1. 수학적 정의역

| ID | 조건 | 강제 위치 | 위반 시 |
|---|---|---|---|
| A-1-1 | `r > g_terminal` | `_two_stage_market_cap()` | ValueError (실행 확인) |
| A-1-2 | `0 <= DRS <= 100` | `erp_from_drs()` | ValueError (실행 확인) |
| A-1-3 | CAGR 시작값 > 0 | `pipeline._cagr()` | ValueError — 없으면 파이썬이 **복소수를 조용히 반환**(v3.19) |
| A-1-4 | CAGR 종료값 > 0 | `pipeline._cagr()` | ValueError |
| A-1-5 | `market_cap > 0`, `fcf0 != 0` | `implied_growth_single_stage()` | ValueError |
| A-1-6 | `market_cap + fcf0 > 0` | `implied_growth_single_stage()` | ValueError (v3.4) |
| A-1-7 | 수렴 조건 `g < r` | `implied_growth_single_stage()` | ValueError — 발산 급수의 형식값 방지 |
| A-1-8 | `fcf0 > 0` (two-stage) | `implied_growth_two_stage()` | ValueError (v3.5) |
| A-1-9 | 시나리오 확률 합 = 1 | `expected_return()` | ValueError |
| A-1-10 | `0 <= structural_discount_pct <= 1` | `realistic_growth_estimate()` | ValueError |
| A-1-11 | `0 <= data_completeness_pct <= 1` | `confidence_score()` | ValueError |

### A-2. 단위 규약

| ID | 조건 | 강제 위치 | 비고 |
|---|---|---|---|
| A-2-1 | `rar()` 첫 인자는 **퍼센트 숫자** | `rar()` v3.19 가드 | `abs(x) < 1.0`이면 소수 오입력으로 간주해 거부 |
| A-2-2 | 소수→RAR 경로는 전용 함수 사용 | `rar_from_decimal_return()` | `test_expected_return_to_rar_chain_is_unit_safe` |
| A-2-3 | capex는 양수(지출액) | `AnalysisInputs.__post_init__` | 음수면 FCF가 capex 2배만큼 과대계상(BRO 실사고, v3.19) |
| A-2-4 | SBC는 양수 | `AnalysisInputs.__post_init__` | v3.23 |
| A-2-5 | `structural_discount_rate`·`classify_lynch_type`은 **10억 단위** 시총 | `run_analysis()`가 `market_cap/1e9` 변환 | 호출부가 헷갈릴 여지를 파이프라인이 흡수 |

### A-3. 주관적 입력 근거 필수화

| ID | 조건 | 강제 위치 |
|---|---|---|
| A-3-1 | `model_choice_reason` 필수 | `__post_init__` (v3.19) |
| A-3-2 | `subjective_input_basis` 필수 | `__post_init__` (v3.19) |
| A-3-3 | `lynch_type_override` 시 사유 필수 | `__post_init__` |
| A-3-4 | `capex_classification` 시 근거 필수 | `__post_init__` (v3.20) |
| A-3-5 | `cagr_base_year_override` 시 사유 필수 + 연도 유효성 | `__post_init__` (v3.21) |
| A-3-6 | `realistic_growth_override` 시 사유 필수 | `__post_init__` (v3.28) |
| A-3-7 | `n_requested != 12`면 사유 필수 | `__post_init__` (v3.25) |
| A-3-8 | `is_insurer=True`면 3개 시계열 필수 | `__post_init__` (v3.22) |
| A-3-9 | DRS 항목 제외 시 `excluded_reasons` 필수 | `DRSInputs.score()` (v3.5) |

### A-4. 판정 규칙 단일화

| ID | 조건 | 강제 위치 |
|---|---|---|
| A-4-1 | 3단계 판정 규칙 구현체는 `judgment_from_gap()` **하나뿐** | v3.32에서 4곳 사본 통합 |
| A-4-2 | 판정 경계값은 `JUDGMENT_BAND` 상수 하나 | v3.35 (`test_judgment_band_is_single_source`) |
| A-4-3 | 6단계 등급은 3단계의 **엄격한 상위호환** | `test_judgment_grade_is_strict_subset_of_judgment` |
| A-4-4 | 엔진 버전은 `ENGINE_VERSION` 상수 하나 | v3.32 (`test_engine_version_comes_from_single_constant`) |

### A-5. 기록 무결성 (ledger)

| ID | 조건 | 강제 위치 |
|---|---|---|
| A-5-1 | 티커당 ledger 파일 1건 | `test_one_ledger_file_per_ticker` |
| A-5-2 | 파일명과 meta의 티커·날짜 일치 | `test_ledger_filename_matches_content` |
| A-5-3 | ledger 내부 판정 라벨 자기일관성 | `test_every_ledger_is_self_consistent_on_judgment` |
| A-5-4 | 회사/ETF/KRX ledger 디렉터리 혼입 금지 | `test_*_is_not_mixed_into_*` |
| A-5-5 | 판정 라벨 어휘는 3종뿐 | 실측: 저평가 17 / 적정가·경계선 15 / 과대평가 2 |

### A-6. 병기 원칙 (자동판정 금지)

| ID | 조건 | 강제 위치 |
|---|---|---|
| A-6-1 | `insurer_cross_check`는 공식 판정을 덮어쓰지 않는다 | `run_analysis()` — 경고만 기록 |
| A-6-2 | `sbc_cross_check`는 공식 판정을 덮어쓰지 않는다 | v3.23 — 병기만 |
| A-6-3 | `thesis_monitor`는 `ledger/`에 쓰지 않는다 | `test_recompute_never_writes_to_ledger_dir` |
| A-6-4 | ETF 겹침 측정은 개별 판정에 영향 없음 | `test_overlap_does_not_affect_individual_judgment` |

---

## B. 이번 Phase 1에서 새로 강제하는 불변조건 (TO BE ENFORCED)

`docs/change_plan.md`의 C-01~C-04에 대응한다.

| ID | 조건 | 근거 |
|---|---|---|
| B-1 | `EBITDA > 0` (net_debt/EBITDA 정의역) | C-01 — EBITDA≤0에서 위험도가 반전됨 |
| B-2 | `save_ledger`는 내용이 다른 기존 파일을 덮어쓰지 않는다 | C-02 — 무경고 소실 |
| B-3 | 보험사 합산 순이익 > 0 (배당성향 정의역) | C-03 — 유보율이 [0,1] 밖으로 나감 |
| B-4 | 동일 입력 2회 실행 시 `analyzed_at` 제외 전 필드 동일 | C-04 — 결정성 |
| B-5 | FCF수익률이 탐지밴드(0.5~25%) 밖이면 경고 기록 | C-15 — 자릿수 오류 무경고 통과 |

## B'. Phase 3(v3.47)에서 새로 강제하는 불변조건

`docs/change_plan.md`의 C-10(토대)·C-16에 대응한다.

| ID | 조건 | 강제 위치 | 검증 테스트 |
|---|---|---|---|
| B-6 | PIT 필드가 없으면 `PIT_UNKNOWN`이며 **`PIT_VALID`로 위장되지 않는다** | `evaluate_point_in_time()` | `test_existing_analyses_are_pit_unknown_not_pit_valid` |
| B-7 | `filing_date > analysis_as_of`면 **실행 거부**(경고 아님) | `run_analysis()` (계약서 5.5절) | `test_future_filing_date_is_rejected_not_merely_warned` |
| B-8 | PIT 날짜는 ISO(YYYY-MM-DD)여야 하고, 형식 오류는 조용히 UNKNOWN으로 떨어지지 않는다 | `_parse_iso_date()` + `__post_init__` | `test_malformed_pit_date_is_rejected_at_construction` |
| B-9 | `filing_dates_by_year`에는 **최근 회계연도**가 반드시 포함(fcf0 결정 연도) | `__post_init__` | `test_filing_dates_require_latest_fiscal_year_and_analysis_date` |
| B-10 | PIT 필드는 계산값에 **영향 없음**(순수 기록 경로) | — | `test_pit_fields_do_not_change_any_computed_value` |
| B-11 | `save_ledger()`는 직전 ledger와 **자동 대조**한다(배선 누락 구조적 불가) | `save_ledger()` → `_find_prior_ledger()` | `test_save_ledger_auto_cross_checks_prior_record` |
| B-12 | 대조는 **예외를 던지지 않는다**(조언이지 차단이 아님) | `save_ledger()` try/except | `test_cross_check_never_blocks_saving` |
| B-13 | 대조 결과는 병기만 하고 공식 수치를 바꾸지 않는다 | `payload["prior_cross_check"]` | `test_cross_check_does_not_alter_official_numbers` |

## B''. v3.48에서 새로 강제하는 불변조건 — 신호/결정 분리와 기록 봉인

| ID | 조건 | 강제 위치 | 검증 테스트 |
|---|---|---|---|
| B-14 | Gap을 인자로 받아 액션을 내는 공개 함수가 **존재하지 않는다** | `engine/thesis.py` 설계 | `test_no_function_maps_gap_to_action` |
| B-15 | 6개 관문 근거가 하나라도 비면 결정 기록 거부 | `build_decision()` | `test_decision_requires_every_gate` |
| B-16 | 액션은 분석자 입력이며 계산되지 않는다(같은 신호로 다른 액션 기록 가능) | `build_decision()` | `test_decision_action_is_analyst_supplied_not_computed` |
| B-17 | thesis 코어는 최초 기록 후 변경 불가 | `save_thesis()` | `test_thesis_core_cannot_be_overwritten` |
| B-18 | decisions/evidence는 append-only | `_append_only()` | `test_decisions_and_evidence_are_append_only` |
| B-19 | 반증조건 발동은 명시적 호출로만(자동판정 없음), 되돌리기 없음 | `mark_invalidation_triggered()` | `test_invalidation_trigger_is_explicit_never_automatic` |
| B-20 | 발동된 반증조건은 지지 증거 수와 무관하게 INVALIDATED | `evaluate_thesis_status()` | `test_triggered_invalidation_overrides_all_supporting_evidence` |
| B-21 | **결과를 알고 난 뒤 예측 수정 불가**(코어 해시 대조) | `resolve_prediction()` | `test_cannot_edit_prediction_after_seeing_outcome` |
| B-22 | 예측 재해소 불가 | `resolve_prediction()` | `test_cannot_resolve_twice` |
| B-23 | 실험 코어는 등록 후 변경 불가(해시 대조), results는 append-only | `record_result()` | `test_core_rules_cannot_change_after_registration` |
| B-24 | 실험 삭제 경로가 코드에 존재하지 않는다 | `experiment_registry` 설계 | `test_no_delete_function_exists` |
| B-25 | 저장소의 모든 실험/예측 기록이 해시 무결성을 유지 | — | `test_experiment_records_keep_their_integrity_hash` · `test_predictions_are_never_silently_edited_after_resolution` |
| B-26 | gap_drivers는 잔차를 숨기지 않는다(합≠전체일 때 드러냄) | `gap_drivers()` | `test_multi_factor_change_reports_interaction_residual_openly` |

⚠️ B-26 실측: CDNS 다인자 변경에서 잔차가 전체 변화의 **108%**이고 개별 기여도
합은 **부호까지 반대**였다. 이 분해는 참고용이며 개별 기여도를 단독 인용하면 안 된다.

---

## C. 아직 보장하지 않는 조건 (NOT ENFORCED — 향후 과제)

**중요**: 아래는 현재 **보장되지 않는다**. 보장되는 것처럼 서술하지 않기 위해
명시적으로 분리한다.

| ID | 조건 | 현재 상태 | 관련 |
|---|---|---|---|
| C-1 | `filing_date <= analysis_as_of` (미래정보 차단) | **규칙은 v3.47에서 강제(B-7)되나 실제로 채운 종목이 0건**이라 34종목 전부 `PIT_UNKNOWN`. 즉 *수단은 생겼고 데이터는 아직 없다* | change_plan C-10 |
| C-2 | 개별 수치의 출처 추적(Provenance) | `data_sources` 자유문자열뿐 | C-09 |
| C-3 | 통화 일관성 검증 | `currency` 기록만, 교차검증 없음. v3.46 스케일 가드는 **자릿수 오류만** 잡고 7배 통화오류는 기저수익률이 낮은 종목에서 놓친다(C-15 한계표) | 감사 D-3 |
| C-4 | Report 숫자 ↔ 엔진 출력 자동 대조 | `self_check_v2`는 **수동 호출** | 계약서 86절 |
| ~~C-5~~ | ~~과거 기록 자동 대조~~ | **해소됨** — v3.47에서 `save_ledger()`에 배선(B-11) | 감사 T-2 |
| C-6 | Confidence의 확률 해석 | **UNCALIBRATED** — 확률 아님 | 감사 M-4 |
| C-7 | 데이터 완전성 실측 | 34/34가 기본값 0.9 | C-06 |
| C-8 | ETF 성장률 가정의 외부 앵커 | VOO 1건만 관측 앵커 | v3.35 기록 |

---

## D. 의도적으로 유지하는 비대칭 (변경 금지)

계약서 5.2절(금융 가정 발명 금지)과 과거값 비교가능성 때문에 **고치지 않는다.**

| ID | 항목 | 유지 사유 |
|---|---|---|
| D-1 | `rar()`만 퍼센트, 나머지는 소수 | 트래커 누적 RAR 전체가 이 규약. 바꾸면 과거값과 비교 불가(v3.19에서 확정) |
| D-2 | `LYNCH_TYPE_CAPS` 값 | 근거 없이 유지 중이나, 근거 없는 다른 숫자로 바꾸는 것은 개선이 아님(v3.24) |
| D-3 | `erp_from_drs` 5~8% 매핑 | 동일. 휴리스틱임을 **표기**하되 값은 불변(C-05) |
| D-4 | 판정 경계 ±5%p | 33종목 관측 기반 시작점. 변경 시 전 ledger 재해석 필요 |
| D-5 | RAR 공식 `ER/DRS` | ER<0에서 방향 반전이 알려져 있으나 경고로 대응(v3.26). 공식 변경 시 과거값 비교 불가 |
