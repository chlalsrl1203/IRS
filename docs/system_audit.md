# IRS System Audit (Phase 0)

작성일: 2026-08-15
작성 근거: 저장소 실제 코드 정독 + 실행 검증. 이 문서의 모든 구조·흐름 기술은
추정이 아니라 실제 import 관계와 실행 결과에서 재구성했다. 확인하지 못한 것은
`UNKNOWN`/`NOT_VERIFIABLE`로 명시한다.

감사 시점 상태: `ENGINE_VERSION = v3.45`, 테스트 255개 전부 통과,
회사 ledger 34종목 / ETF ledger 23건 / KRX ledger 31건 / reports 12건 /
scripts 55개.

---

## 1. Actual Architecture

**추정하지 않고 실제 `import` 관계에서 재구성한 의존 그래프.**

```
expectation_gap_engine.py   (엔진 의존 없음 - 최하위 계산 원본)
        ▲        ▲        ▲        ▲        ▲
        │        │        │        │        │
   pipeline  screener  gap_dist  growth_   etf_engine
        │        ▲     ribution  scorecard      ▲
        │        └──────────────────────────────┘
        │                                  (etf_engine이 screener도 import)
        │                                       ▲
        │                                  etf_pipeline
        │                                       ▲
        │                                  krx_etf_pipeline ◄── krx_etf_engine
        │
   thesis_monitor (지연 import: 함수 내부에서 pipeline을 부름 - L185, L205)

독립 모듈(엔진 의존 없음):
   self_check_v2      - 메모 텍스트 ↔ 계산값 대조(정규식 파싱)
   market_relative    - 저장된 ledger dict 산술만 수행
   krx_etf_engine     - KRX 래퍼 고유 비용/구조 계산
```

관측 사실:
- `expectation_gap_engine.py`가 **유일한 최하위 계산 원본**이며 다른 엔진
  모듈을 전혀 import하지 않는다. 계층 위반 없음.
- `etf_engine`이 `screener`를 import한다 — ETF 엔진이 회사 스크리너의 일부
  함수를 재사용하는 구조(공유 원시함수 재사용 원칙의 실제 구현).
- `thesis_monitor`만 지연 import를 쓴다(순환 참조 회피 목적으로 보이나
  주석에 명시되어 있지 않음 → `UNKNOWN`).

**진입점 실측**: `scripts/*.py` 55개 중 `run_analysis()` 호출 30개,
`save_ledger()` 호출 26개, `cross_check_prior_record()` 호출 **1개**(BKNG).

---

## 2. Actual Data Flow

계약서 10.2의 표준 흐름과 대조한 **실제** 흐름이다.

```
[SOURCE]  Alpha Vantage MCP / SEC XBRL companyfacts API / WebSearch
              │  ※ 사람이 수동 전사 — 자동 수집 파이프라인 없음
              ▼
[RAW]     scripts/analyze_<ticker>_<date>.py 안의 파이썬 dict 리터럴
              │  ※ RAW 원본은 저장소에 별도 보존되지 않는다(아래 Data Risk 참조)
              ▼
[NORMALIZE] AnalysisInputs.__post_init__
              │  capex 음수 거부(v3.19) / SBC 음수 거부(v3.23) /
              │  margin_years 기본값 설정 / 각종 사유 필수 검증
              ▼
[DERIVE]   run_analysis() 내부
              │  fcf = ocf - capex, _cagr(3y/5y/10y), op_margins,
              │  net_debt_to_ebitda, worst_yoy
              ▼
[MODEL]    DRS 5항목 → erp_from_drs → r = rf + erp
              │  realistic_growth_estimate(+ capex/override 분기)
              │  compare_implied_growth_models(single·two 항상 둘 다)
              ▼
[JUDGE]    gap = realistic - implied → judgment_from_gap()
              │  judgment_grade_from_gap() / confidence_score()
              │  sensitivity_check / stalwart bias / insurer / SBC 병기
              ▼
[LEDGER]   save_ledger() → ledger/<TICKER>_<날짜>.json
              ▼
[REPORT]   별도 스크립트(rank_portfolio / build_buylist / thesis_monitor 등)
           가 ledger를 다시 읽어 reports/*.json 생성
```

**표준 흐름과 다른 점(사실 기술)**:
- `Source → Raw → Normalization`이 **분리된 코드 계층으로 존재하지 않는다.**
  원자료는 분석 스크립트 안에 하드코딩된 dict이고, 그 dict가 곧 RAW이자
  NORMALIZED다. 계약서 17절이 요구하는 3계층 분리는 현재 미구현이다.
- 검증(Validation)은 별도 단계가 아니라 `__post_init__`과 `run_analysis()`
  본문에 분산돼 있다.
- `self_check_v2`는 파이프라인 **밖**에 있다 — 메모 발행 시 사람이 별도
  호출하며, `run_analysis()`가 자동으로 부르지 않는다.

---

## 3. Module Responsibilities

| 모듈 | Purpose | Inputs | Outputs | Side Effects | Known Risks |
|---|---|---|---|---|---|
| `expectation_gap_engine` | 순수 계산 함수 원본(Implied Growth, DRS, RAR, 판정) | 스칼라/리스트 | 스칼라/dict | 없음 | ERP 매핑·Lynch 캡이 경험적으로 미검증(코드에 명시됨) |
| `pipeline` | 유일한 공식 분석 진입점 | `AnalysisInputs` | 결과 dict | `save_ledger` 호출 시 파일 쓰기 | 도메인 가드 누락(F-01/F-03), ledger 덮어쓰기(F-02) |
| `self_check_v2` | 메모 원문 ↔ 계산값 대조 | memo_text, ctx | None(실패 시 예외) | stdout 출력 | 정규식 파싱이라 메모 서식 변화에 취약 |
| `screener` | 1차 후보 필터(재무데이터 최소 입력) | `Candidate` | 통과/탈락+사유 | 없음 | competition_intensity 상수 대체(문서화된 한계, BSX 오탈락 실사례) |
| `etf_engine`/`etf_pipeline` | ETF 자체 밸류에이션 | `ETFInputs` | 결과 dict | ledger_etf 쓰기 | 성장률 가정이 결과를 1:1 지배(v3.34에서 자체 진단·문서화) |
| `krx_etf_engine`/`krx_etf_pipeline` | 국내 래퍼 ETF(미국 원본 재사용) | `KRXWrapperInputs` | 결과 dict | ledger_krx 쓰기 | 지수 동일성 검증이 수동 필드에 의존 |
| `thesis_monitor` | 반증조건 기한도래 감시 + 시총 부식 재계산 | ledger dict | 리포트 dict | **ledger 쓰기 없음(설계상 금지, 테스트로 고정)** | 날짜 정규식이 서술적 날짜를 오탐(설계상 사람이 분류) |
| `growth_scorecard` | 엔진 성장률 vs 회사 실적/가이던스 대조 | ledger + 관측치 | 채점 dict | 없음 | 관측치 종류 혼용 금지가 규약으로만 존재 |
| `gap_distribution` | DRS 주관입력 섭동에 대한 Gap 분포 | ledger corpus | 몬테카를로 결과 | 없음 | ERP 폭이 좁아 판별력 자체가 낮음(v3.44에서 실측 확인) |
| `market_relative` | 회사 Gap을 VOO 대비로 재해석 | 회사·ETF ledger | dict | 없음 | 분자 상이(FCF vs 이익) — 레벨 해석 금지(문서화됨) |

---

## 4. Current Failure Modes

실행으로 **직접 재현**한 것만 기록한다. 재현 명령과 관측값을 함께 남긴다.

### FM-1. EBITDA ≤ 0에서 레버리지 위험이 정반대로 산출됨 (재현됨)

`pipeline.py:447` `net_debt_to_ebitda = inputs.net_debt / inputs.ebitda`에
도메인 가드가 없다. `leverage_score()`는 음수 비율을 "순현금"으로 해석해
최저 위험점수(2.0)를 준다 — 그런데 EBITDA가 적자여도 비율은 음수가 된다.

동일 기업(순부채 +$30억) 실행 결과:

| EBITDA | net_debt/EBITDA | leverage 점수 | DRS 총점 | 경고 |
|---|---|---|---|---|
| **-$5억(적자)** | -6.00 | **2.0 (최저위험)** | **22.4** | 없음 |
| +$5억(흑자) | +6.00 | 20.0 (최고위험) | 40.4 | 없음 |

**부실한 쪽이 DRS 18점 더 안전하게 나온다.** DRS는 ERP→할인율→Implied
Growth→Gap→판정, 그리고 시나리오확률·Confidence·RAR까지 전부를 타고 흐른다.

`EBITDA = 0`이면 `ZeroDivisionError: float division by zero`가 원인 설명
없이 발생한다(계약서 107절 Error Contract 위배).

**과거 영향: 없음.** ledger 34종목 전수 확인 결과 EBITDA ≤ 0인 분석은 0건이다
(순부채 음수=순현금인 정상 사례는 13건이며 이는 의도된 경로다).

### FM-2. `save_ledger()`가 같은 날짜 분석을 경고 없이 덮어씀 (재현됨)

동일 티커·동일 날짜로 두 번 저장하면 파일 경로가 같아 **1차 결과가 조용히
소실**된다. 재현 결과: Gap `+0.10`(판정 A) 저장 후 Gap `-0.30`(판정 B)을
저장하니 디렉터리에 파일 1개만 남고 내용은 B였다. 경고·예외·백업 없음.

계약서 5.4/63절(ledger는 immutable research record, overwrite 금지)에 정면
위배된다. 다만 이 프로젝트는 **정성조사 결과를 같은 날짜 파일에 반영하는
운용 관행**을 의도적으로 써왔다(CLAUDE.md에 명시). 따라서 단순 금지가 아니라
"의도한 갱신"과 "사고에 의한 소실"을 구분하는 설계가 필요하다.

**과거 영향: NOT_VERIFIABLE.** 덮어쓰기가 발생했는지 여부를 사후에 알 방법이
저장소에 없다(그것이 바로 이 결함의 성질이다).

### FM-3. 보험사 유보율이 정의역을 벗어나도 통과됨 (재현됨)

`pipeline.py:715` `payout_ratio = total_dividends / total_net_income`에 가드가
없다. 3년 창에 손실 연도가 섞이면:

| 순이익 합계 | 배당성향 | 유보율 | 지속가능성장률(ROE 12% 가정) |
|---|---|---|---|
| +1000 (정상) | +0.30 | +0.70 | +8.40% |
| **-200 (합산 손실)** | **-1.50** | **+2.50** | **+30.00%** |
| +250 (배당>순이익) | +1.20 | **-0.20** | **-2.40%** |

유보율은 정의상 0~1이어야 하는데 2.50 또는 -0.20이 나오고, 그 값이 그대로
Realistic Growth와 대조되어 경고를 내거나(또는 내지 않아) 판정 신뢰도 판단에
쓰인다. 대재해 노출 재보험사(ACGL 유형)에서 손실 연도는 충분히 현실적이다.

**과거 영향: 없음.** ACGL·PGR 두 보험사 ledger 모두 순이익 음수 연도 0건,
유보율 0.848/0.838로 정상 범위다.

### FM-4. 결정성(determinism)이 테스트로 고정되어 있지 않음 (재현됨)

동일 입력 2회 실행 시 `meta.analyzed_at`(마이크로초 타임스탬프)만 다르고
**나머지 전 필드는 완전히 동일**함을 확인했다. 즉 엔진은 실제로 결정적이다.
그러나 이를 보장하는 테스트가 없어(`grep`로 확인: 결정성 테스트 0건) 향후
비결정적 요소(dict 순회 순서 의존, 난수, 시각 의존 분기)가 들어와도 잡히지
않는다.

---

## 5. Technical Debt

- **T-1. 문서-코드 불일치**: `README.md`는 `engine/`을 3개 파일
  (`expectation_gap_engine`, `pipeline`, `self_check_v2`)로 기술하지만 실제로는
  12개다. ETF·KRX·screener·thesis_monitor·growth_scorecard·gap_distribution·
  market_relative 7개 계열이 README에 전혀 등장하지 않는다.
- **T-2. `cross_check_prior_record()` 사실상 미사용**: 55개 스크립트 중 1개
  (BKNG)만 호출한다. CLAUDE.md는 "과거 기록이 있는 종목을 재검증할 때" 쓰라고
  규정하지만 강제 수단이 없다. (CLAUDE.md가 이미 이 사실과 자동화 시 부작용을
  기록해뒀다 — 중복 인지이므로 신규 발견은 아니다.)
- **T-3. `run_self_check()`(v1) 잔존**: DEPRECATED 표시는 있으나 코드에 남아
  있어 새 코드가 실수로 호출할 수 있다. 호출부는 현재 0건.
- **T-4. RAW 계층 부재**: 원자료가 분석 스크립트 안 dict 리터럴로만 존재해
  "출처 → 원값 → 정규화값" 추적이 코드 수준에서 불가능하다.

---

## 6. Model Risk

소프트웨어 버그와 **구분해서** 기록한다. 아래는 고칠 대상이 아니라 표시·
검증 대상이다(계약서 12절: MODEL DESIGN ISSUE를 SOFTWARE BUG처럼 고치지 말 것).

- **M-1. `erp_from_drs`는 휴리스틱이다.** DRS 0→ERP 5%, 100→8%의 선형 매핑에
  경험적 근거가 코드·문서 어디에도 없다. 현재 docstring은 "고정 규칙이며
  임의 조정 금지"라고만 쓰여 있어 **규범적 강제력**은 표현하지만 **인식론적
  지위**(=검증되지 않은 휴리스틱)는 표현하지 않는다. 계약서 36절이 요구하는
  `HEURISTIC_MAPPING` 라벨이 없다.
- **M-2. `LYNCH_TYPE_CAPS` 미검증.** 이미 코드 주석에 상세히 문서화돼 있음
  (v3.24). 상한 바인딩 시 성장분석이 결과에 기여하지 않는다는 사실도
  `data_limitations`로 경고된다. **추가 조치 불필요 — 이미 적절히 처리됨.**
- **M-3. RAR은 ER<0에서 방향이 반전된다.** 이미 v3.26에서 기계적 검증 후
  경고 배선 완료. **추가 조치 불필요.**
- **M-4. Confidence는 확률이 아니다.** `confidence_score()`는 base 50에
  가감점을 더한 점수이며 calibration된 적이 없다. 계약서 50/149절 기준
  `UNCALIBRATED` 상태다. 코드에 이 상태를 명시하는 표기가 없다.
- **M-5. `data_completeness_pct` 기본값 0.9가 사실상 상수로 굳어 있다.**
  ledger 34종목 **전부** 0.9다 — 실제 데이터 완전성에서 산출된 적이 한 번도
  없다. `confidence_score`에서 `round(0.9*15) = 14`점이 무조건 부여되므로,
  Confidence는 "데이터 완전성을 반영한다"고 표방하면서 그 축에서 판별력이
  정확히 0이다.
- **M-6. Single/Two-stage 모델 선택 규칙이 없다.** 이는 결함이 아니라 의도된
  설계다(`compare_implied_growth_models` docstring: 규칙이 없는 상태에서 코드가
  임의로 고르면 그게 곧 근거 없는 자동화). 괴리 경고 + 사유 필수화로 대응 중.

---

## 7. Data Risk

- **D-1. Point-in-Time 미지원.** `filing_date`, `analysis_as_of`,
  `retrieval_date` 개념이 스키마에 존재하지 않는다. `meta.analyzed_at`은
  "코드를 실행한 시각"이지 "그 시점에 어떤 데이터가 공시돼 있었는가"를
  보증하지 않는다. 따라서 계약서 67~70절이 정의하는 Historical Replay는
  **현재 구조에서 원리적으로 불가능**하다(→ change_plan에서 `DEFERRED`).
- **D-2. Provenance 미지원.** `data_sources`는 자유형 문자열 리스트일 뿐,
  개별 수치가 어느 문서/어느 태그에서 왔는지 추적할 수 없다.
  CLAUDE.md에 기록된 실제 사고가 이 위험을 실증한다: TYL의 SBC/FCF가 2차
  출처 인용 오류로 62%→24.4%(약 3배)로 정정됐고, ONON은 Alpha Vantage 매출이
  1차 출처와 4.7% 어긋나 SEC XBRL로 재확인해야 했다.
- **D-3. 통화 혼재.** `currency` 필드는 v3.24에 추가됐으나 기본값이 `"USD"`라,
  그 이전 ledger는 통화 미상이다. PDD(CNY)·ONON(CHF)처럼 비USD 종목이 실재한다.
- **D-4. 단위 규약 비대칭이 남아 있다.** `rar()`만 퍼센트를 받고 나머지는 전부
  소수다. 이는 **의도적으로 동결된 설계**다(트래커 과거값과의 비교가능성 유지).
  `rar_from_decimal_return()` + v3.19 가드로 방어 중이며 골든테스트도 있다.
  **추가 조치 불필요 — 알려진 한계로 유지.**

---

## 8. 감사 결론

이 저장소는 "테스트가 없어서 사고가 났다"는 단계는 이미 지났다. 255개 테스트,
CI 자동 실행, 골든 회귀 테스트, 단위 가드, ledger 무결성 테스트가 모두 존재하고
실제로 과거 사고를 재발 방지하고 있다.

이번 감사에서 새로 확인된 **실제 결함은 도메인 검증 공백 3건**(FM-1, FM-3와
그 파생인 ZeroDivisionError)과 **기록 무결성 1건**(FM-2), **결정성 미고정
1건**(FM-4)이다. 셋 다 과거 결과에 영향을 주지 않은 잠재 결함이지만, 전부
"조용히 틀린 값이 흘러가는" 유형이라 이 프로젝트가 반복적으로 피해를 입어온
바로 그 계열이다.

모델 수준 위험(M-1~M-6)은 대부분 이미 코드에 문서화·경고 배선돼 있다. 남은
것은 **인식론적 지위 표기**(휴리스틱/미검증 라벨)이며, 이는 계산을 바꾸지 않는
순수 문서화 작업이다.

Point-in-Time과 Provenance는 현재 구조에서 부분 구현이 불가능하며, 무리하게
착수하면 계약서 6절(과잉 설계 방지)에 위배된다 → `DEFERRED`로 분류하고 그
이유를 change_plan에 명시한다.
