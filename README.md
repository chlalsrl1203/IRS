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
  expectation_gap_engine.py   # 계산 원본 함수들(Implied Growth, DRS, RAR 등)
  pipeline.py                 # 실제 분석 진입점 - run_analysis(), 항상 이걸 쓸 것
  self_check_v2.py            # 메모 발행 전 대조검증
ledger/                       # 종목별 입력값+중간값+결과 JSON (재현/대조검증용)
scripts/                      # 과거 세션의 일회성 분석/감사 스크립트(참고용 보존)
tests/                        # pytest - 매 push마다 CI가 자동 실행
CLAUDE.md                     # 버전 이력, 단위 규약, 사고 기록과 그 교훈
CHANGELOG.md                  # 버전별 변경사항
```

## 테스트

```bash
python3 -m pytest tests/ -v
```

`.github/workflows/tests.yml`이 모든 push에서 자동으로 이 명령을 실행한다.

## 재현/대조검증

과거 기록이 있는 종목을 재검증할 때는 `engine/pipeline.cross_check_prior_record()`로
새 결과와 트래커의 과거 값을 자동 대조한다(RAR 스케일/부호, Gap 괴리, 모델
불일치, DRS 괴리를 잡아준다). `ledger/`에 파일이 없는 과거 기록은 원 입력값이
사라져 독립 재현이 불가능하므로, 새 분석은 반드시 `save_ledger()`로 ledger를
남길 것.
