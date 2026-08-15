# IRS (Investment Research System)

개별 종목의 Implied Growth(내재성장률) / Realistic Growth(현실적 성장률) /
Expectation Gap / DRS(하방위험점수) / RAR(위험조정수익률)을 서술형 근사가
아니라 실제 코드 실행으로 산출하는 투자분석 엔진과, 결과를 기록하는 Notion
트래커("기업분석 결과 트래커")로 구성된다.

## 시작하기 전에

**`CLAUDE.md`를 먼저 읽을 것.** 이 프로젝트가 겪은 실제 사고(RAR 100배 오류,
모델선택 실수, 큐22 입력값 유실, 가짜 버전 등)와 그 사고를 막기 위해 코드에
박아넣은 가드가 전부 기록돼 있다. 여기 README는 빠른 시작용 요약일 뿐이고,
단위 규약이나 버전 이력 같은 세부사항의 근거는 CLAUDE.md에 있다.

## 종목 분석 실행

**엔진 함수를 손으로 배선하지 말 것.** 반드시 `engine/pipeline.py`의
`run_analysis()`를 쓴다 — 단위 처리(퍼센트 vs 소수, 원화 vs 10억 단위),
두 모델(single/two-stage) 비교, 데이터 한계 기록이 전부 여기 내장돼 있고,
손배선은 이 프로젝트에서 실제로 여러 번 사고를 냈다(RAR 100배, 모델선택
실수, 입력값 유실).

```python
from engine.pipeline import AnalysisInputs, run_analysis, save_ledger

inputs = AnalysisInputs(
    ticker="...", company_name="...",
    revenue_by_year={...}, operating_income_by_year={...},
    operating_cashflow_by_year={...}, capex_by_year={...},
    market_cap=..., net_debt=..., ebitda=..., risk_free_rate=...,
    competitor_threat_weights=[...], market_share_trend_pp_per_year=...,
    active_antitrust_or_regulatory_case=False, demand_sensitivity_pct=...,
    subjective_input_basis="...",       # 필수: 주관적 입력의 근거
    model_used="single_stage",          # 또는 "two_stage"
    model_choice_reason="...",          # 필수: 모델을 고른 이유
)
result = run_analysis(inputs)
path = save_ledger(result)              # ledger/<TICKER>_<날짜>.json
```

`model_choice_reason`과 `subjective_input_basis`가 없으면 실행 자체가
거부된다. 실행 예시는 `scripts/build_ledgers_2026_07_25.py`를 참고할 것.

메모(투자 노트)를 발행하기 전에는 `engine/self_check_v2.run_self_check_v2(memo_text, ctx)`로
메모 원문과 계산값을 대조한다.

## 구조

```
engine/
  # ── 회사 분석(핵심 경로) ──
  expectation_gap_engine.py   # 계산 원본 함수들(Implied Growth, DRS, RAR, 판정)
  pipeline.py                 # 실제 분석 진입점 - run_analysis(), 항상 이걸 쓸 것
  self_check_v2.py            # 메모 발행 전 대조검증(수동 호출)
  screener.py                 # 1차 후보 필터(정식분석 전 스크리닝)
  # ── 외부 검증 루프(v3.42~v3.45) ──
  thesis_monitor.py           # 반증조건 기한도래 감시 + 시총 부식 재계산
  growth_scorecard.py         # 엔진 성장률 vs 회사 실적/가이던스 대조
  gap_distribution.py         # DRS 주관입력 섭동에 대한 Gap 분포(몬테카를로)
  market_relative.py          # 회사 Gap을 VOO(시장) 대비로 재해석
  # ── ETF 분석(별도 엔진) ──
  etf_engine.py               # 미국 상장 ETF 자체 밸류에이션
  etf_pipeline.py             # ETF 분석 진입점
  krx_etf_engine.py           # 국내 상장 래퍼 ETF 고유 비용/구조
  krx_etf_pipeline.py         # KRX 래퍼 진입점(미국 원본 결과 재사용)

ledger/                       # 회사 분석 JSON (입력값+중간값+결과, 재현/대조검증용)
ledger_etf/                   # 미국 ETF 분석 JSON (스키마가 달라 디렉터리 분리)
ledger_krx/                   # 국내 래퍼 ETF 분석 JSON
reports/                      # ledger를 재조합한 리포트(순위·매수리스트·감시 결과)
scripts/                      # 종목별 분석/감사 스크립트(재현용 보존)
tests/                        # pytest - 매 push마다 CI가 자동 실행
docs/                         # 감사 산출물(아래 참고)
CLAUDE.md                     # 버전 이력, 단위 규약, 사고 기록과 그 교훈
CHANGELOG.md                  # 버전별 변경사항
```

## 감사 문서 (docs/)

- **`docs/system_audit.md`** — 실제 architecture·data flow·failure mode를
  코드 실행으로 재구성한 감사 보고서. **엔진을 수정하기 전에 읽을 것.**
- **`docs/change_plan.md`** — 발견된 결함의 우선순위(P0~P3)와 처리 상태
  (REQUIRED_NOW / DEFERRED / NOT_JUSTIFIED)와 그 사유.
- **`docs/invariants.md`** — 현재 코드가 **실제로 보장하는** 불변조건과 아직
  보장하지 않는 조건을 분리 기록. 새 기능을 넣기 전 여기 A절을 깨지 않는지 확인.
- **`docs/AUDIT_2026-08-01_methodology.md`** — 방법론 감사(SBC·반증조건 등).

### 아직 보장하지 않는 것(오해 방지)

- **Point-in-Time — 수단은 있으나 데이터가 0건** — v3.47에서 `analysis_as_of` /
  `filing_dates_by_year` 필드와 `filing_date <= analysis_as_of` 검증이
  들어갔지만(위반 시 실행 거부), **실제로 채운 종목은 아직 하나도 없어
  기존 34종목은 전부 `PIT_UNKNOWN`이다.** 즉 "그 시점에 공시돼 있던
  데이터"임을 아직 보증하지 못한다 — 과거 filing_date를 추정해 채우는 것은
  금지(추측을 기록으로 위장하게 됨). **새 분석부터 채울 것.**
- **Historical Replay 미지원** — 위 PIT 데이터가 쌓여야 시작할 수 있다.
- **Confidence는 확률이 아니다** — calibration된 적이 없다(`UNCALIBRATED`).
  Confidence 85는 "85% 확률로 맞다"는 뜻이 아니다.
- **ERP 매핑(DRS→5~8%)은 휴리스틱** — 실증 근거가 없다. `VALIDATION_STATUS`
  상수 참고.

## 테스트

```bash
python3 -m pytest tests/ -v
```

`.github/workflows/tests.yml`이 모든 push에서 자동으로 이 명령을 실행한다.

## 재현/대조검증

**v3.47부터 `save_ledger()`가 같은 티커의 직전 ledger를 찾아 자동으로 대조한다** —
따로 호출할 필요가 없다(모든 분석 스크립트가 이미 `save_ledger()`를 부르므로
배선 누락이 구조적으로 불가능하다). RAR 스케일/부호, Gap 괴리, 모델 불일치,
DRS 괴리를 잡아 결과 JSON의 `prior_cross_check`에 병기한다.

- 대조는 **조언이지 차단이 아니다** — 경고가 떠도 저장은 진행되고 판정은
  바뀌지 않는다(병기 원칙).
- 저장소 상태에 의존하면 안 되는 경우 `save_ledger(..., cross_check=False)`.
- 수동 대조가 필요하면 `engine/pipeline.cross_check_prior_record()`를 직접
  부를 수도 있다.

`ledger/`에 파일이 없는 과거 기록은 원 입력값이 사라져 독립 재현이 불가능하므로,
새 분석은 반드시 `save_ledger()`로 ledger를 남길 것.
