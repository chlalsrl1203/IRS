# Repository 01~30 통합 판정 원장 (2026-08-19)

Master Execution Prompt §23 형식. **기능 단위 판정**(§1: "Repository 전체에 하나의
판단을 내리지 말고 기능 단위로 판단한다").

## 판정 요약

| # | Repository | 판정 | 상태 |
|---|---|---|---|
| 01 | chenditc/investment_data | REIMPLEMENT | ✅ 완료 (P0-05/06/07) |
| 02 | dgunning/edgartools | REIMPLEMENT | ✅ 완료 (P0-02/03/11) |
| 03 | microsoft/qlib | PIT=DUPLICATE, backtest=DEFER | ✅ 판정 |
| 04 | stefan-jansen/mlfortrading | **부분 REIMPLEMENT** | ✅ 완료 (신규) |
| 05 | DimaMerc/finance-llm-evals | REIMPLEMENT | ✅ 완료 (=TieOutBench, P0-13) |
| 06 | xbtlin/ai-berkshire | ADAPT | ✅ 완료 (P0-14) |
| 07 | eddmpython/dartlab | 인터페이스=ADAPT, DART=DEFER | ✅ 판정 (P0-02/04) |
| 08 | byteseek/Mira | ADAPT | ✅ 완료 (P0-16) |
| 09 | PE investment-dd-skill | REIMPLEMENT | ✅ 완료 (P0-12) |
| 10 | ishtiaqrahman/capitalbench | DEFER | ✅ 판정 (P0-17) |
| 11 | HKUSTDial/DeepFund | DEFER | 판정 |
| 12 | Alpha-Dojo/DojoAgents | REJECT | 판정 |
| 13 | myinvestpilot/ai-architecture | DEFER | 판정 |
| 14 | questflowai/investorskills | DUPLICATE | 판정 |
| 15 | skfolio/skfolio | REJECT | 판정 |
| 16 | PyPortfolioOpt | REJECT | 판정 |
| 17 | CPZ-Lab/cpz-quant | **부분 REIMPLEMENT** | ✅ 완료 (신규) |
| 18 | financial-knowledge-graphs | DEFER | 판정 |
| 19 | financial-research-agent | 부분 DUPLICATE | 판정 |
| 20 | VanekPetr/investment-funnel | DUPLICATE | 판정 |
| 21 | TradingView-Screener | DEFER | 판정 |
| 22 | deepentropy/tvscreener | DEFER | 판정 |
| 23 | mbk-dev/okama | REJECT | 판정 |
| 24 | NVIDIA portfolio-optimization | REJECT | 판정 |
| 25 | koala73/worldmonitor | DEFER | 판정 |
| 26 | simonlin1212/investment-news | DEFER | 판정 |
| 27 | B-M-Capital/honeclaw | DUPLICATE | 판정 |
| 28 | ryze-labs/investment-theses | DUPLICATE | 판정 |
| 29 | agno-agi/investment-team | REJECT | 판정 |
| 30 | mattpocock/skills | DEFER | 판정 |

**이번 세션 신규 구현: Repo 04 + Repo 17의 일부 기능** (아래 상세).
나머지는 이전 P0 통합에서 완료됐거나, IRS의 실증 근거 부족·§31 안티기능 등록부와
충돌해 REJECT/DEFER로 판정된다.

---

# Repository: machine-learning-for-trading (Repo 04) + cpz-quant (Repo 17)

URL: https://github.com/stefan-jansen/machine-learning-for-trading
URL: https://github.com/CPZ-Lab/cpz-quant

Overall Value: **72** (IRS Relevance 20 / Technical Quality 13 / Data Integrity 14 /
Research Value 13 / Feasibility 5 / Maintainability 3 / Validation 4)

Integration: **부분 REIMPLEMENT** (기능별로 갈림)

## 1. IRS Gap

이 저장소는 **같은 34종목 표본에 반복해서** 분석을 돌려왔다. 2026-08-19 실측:
`reports/` **28건** + `experiments/` **9건**, 집계 검정 횟수 **9,702회**
(R-001 하나가 9,675 시나리오). R-001이 §26에서 다중검정을 **인지**했지만
저장소 전체 검정 횟수를 센 적은 없었다.

생존편향도 마찬가지다 — 스크리닝 탈락 기록(`PREFILTERED_OUT`·`FRAMEWORK_MISMATCH`·
`PASSED_INITIAL_SCREEN`)은 남아 있는데 **한 번도 집계되지 않았다.**

## 2. Useful Components

**실제 확인**(§1.4·§22 STEP 3): cpz-quant는 Apache-2.0이며
`CombinatorialPurgedCV` 스플리터, `probability_of_backtest_overfitting`(CSCV 기반),
Deflated/Probabilistic Sharpe Ratio 게이트, `WalkForward` 스플리터를 **실제로**
제공한다(§18이 "존재를 가정하지 말라"고 경고한 항목을 직접 확인함).

## 3. Capability

look-ahead bias · survivorship bias · data leakage · multiple testing ·
overfitting detection · walk-forward · PBO · DSR

## 4. IRS Target

`engine/quant/validation.py` (신규) · `engine/quant/__init__.py` (신규)

## 5. Integration Method — **기능마다 다르다**

| 기능 | 판정 | 근거 |
|---|---|---|
| look-ahead / PIT | **DUPLICATE** | `filing_dates.check_lookahead` · `GATE.LOOKAHEAD` · `FinancialFact.available_at`이 이미 담당 |
| **multiple testing** | **REIMPLEMENT** | 지금 계산 가능하고 실제로 필요 |
| **survivorship bias** | **REIMPLEMENT** | 탈락 기록이 남아 있어 계산 가능 |
| data leakage (시계열 분할) | **DEFER** | 분할할 시계열이 없다 |
| Purged CV / Walk-Forward | **DEFER** | 시계열 부재 |
| PBO / DSR | **DEFER** | Sharpe를 계산할 수익률 시계열이 없다 |

cpz-quant를 **의존성으로 채택하지 않은 이유**: 라이브러리 자체는 품질이 좋지만
입력(수익률 시계열)이 IRS에 없다. 넣으면 쓰이지 않는 의존성이 되고, 억지로
돌리면 "정밀해 보이는 허구"가 된다(§31 등록부의 포트폴리오 최적화 REJECT와
같은 판단).

## 6. Implementation

- `count_tests_on_sample()` — 리포트가 시나리오 수를 **스스로 밝히면 그 수를**,
  안 밝히면 1로 세되 그 사실을 `unknown_scenario_counts`에 남긴다(모르는 것을
  1로 확정하지 않는다).
- `familywise_error()` — FWER 상한 + Bonferroni + 기대 위양성. **독립 가정이
  성립하지 않음을 명시**하고, FWER이 1.0으로 포화하면 `fwer_saturated=True`로
  표시한다(계산 오류로 오독되지 않게).
- `survivorship_report()` — 스크리닝 버킷을 정규식으로 파싱. **AST 실행이 아닌
  이유**: 스크립트를 import하면 네트워크 호출·분석이 실행된다.
- `sharpe_based_metrics_available()` — PBO·DSR **계산 가능 여부를 먼저 검사하고
  불가능하면 그 사실만 반환**한다. 계산을 흉내낸 필드를 만들지 않는다.

### ⚠️ 구현 중 테스트가 잡은 결함 2건

1. **`CANDIDATES`가 항상 0건으로 나왔다.** 스크리닝 스크립트는 `CANDIDATES = []`로
   시작한 뒤 `CANDIDATES.append(Candidate(ticker="META", ...))`로 채운다 —
   리터럴 블록만 파싱한 초판은 후보를 통째로 놓쳤다(83종목 → 20종목으로 과소집계).
2. **딕셔너리 키가 `"KR(Kroger)"` 형태**라 괄호를 벗기지 않으면 매칭이 안 됐다.

두 결함 다 **탈락 종목을 과소집계**하는 방향이라, 고치지 않았으면 생존편향이
실제보다 작아 보였을 것이다.

## 7. Dependencies

**추가 없음.** stdlib만 사용(`glob`·`json`·`os`·`re`). 테스트가 numpy·pandas·scipy
import 부재를 고정한다(`test_module_adds_no_third_party_dependency`).

## 8. Tests

`tests/test_quant_validation.py` — **25건 신규**. 641 → **666개 전부 통과.**

## 9. Regression

34종목 골든재현 8개 지표 완전 동일, baseline fingerprint `fbd34322…` 불변,
ledger·공식 판정 무수정.

## 10. License

cpz-quant Apache-2.0 · mlfortrading은 코드를 가져오지 않고 **개념만** 참고.
코드 복사 없음 — 전부 IRS-native 재구현.

## 11. Expected Benefit — 실측 결과

| 항목 | 실측 |
|---|---|
| 같은 표본 검정 횟수 | **9,702회** (리포트 28 + 실험 9) |
| 기대 위양성(α=0.05, 독립가정 상한) | **485건** |
| 스크리닝 고려 종목 | **83종목** |
| 탈락 | **75종목** |
| ledger 34 중 스크리닝 경로 | **8종목** (나머지 26은 스크리닝 이전 큐 경로) |
| 생존율 하한(스크리닝 부분집합) | **9.6%** |

⚠️ **이 수치들은 "IRS가 틀렸다"는 뜻이 아니다.** IRS의 분석 대부분은 가설검정이
아니라 감사·서술이라 nominal p값이 없고, 따라서 보정을 적용할 대상 자체가 없다.
이 리포트의 목적은 **"같은 표본을 몇 번 봤는가"를 처음으로 세는 것**이다.

## 12. Decision

**KEEP** (multiple testing + survivorship) / **DEFER** (PBO·DSR·Purged CV·
Walk-Forward — 수익률 시계열 확보 시 재개)

---

# Repository 03: microsoft/qlib

Integration: **PIT=DUPLICATE, backtest/feature pipeline=DEFER**

**IRS Gap**: 없음. qlib의 핵심 기여인 `period ≠ available_at` 구분과
`available_at <= decision_timestamp` 강제는 v3.47~v3.49 + P0-02/10에서 이미
구현됐고(`FinancialFact.available_at`, `check_lookahead`, `PIT_INVALID` 실행 거부),
**이 저장소 최초의 `PIT_VALID` 분석**까지 달성했다(BSX, P0-08/09/10).

backtest·feature pipeline은 수익률 시계열 부재로 DEFER(Repo 04·17과 같은 벽).
의존성도 무겁다(pandas·numpy·pytorch 계열).

**Decision: DEFER** (신규 코드 없음)

---

# Repository 11~14, 29: Agent / Orchestration 계열

DeepFund(11) · DojoAgents(12) · ai-architecture(13) · investorskills(14) ·
investment-team(29)

**§31 ANTI-FEATURE REGISTER 정면 충돌**:
> 멀티에이전트 리서치 오케스트레이션 — 현재 병목은 조율이 아니라 **입력의 근거
> 부재**(n·w). 에이전트를 늘려도 미검증 파라미터는 그대로다.

R-001 STAGE 3 감사가 이 판단을 재확인했다 — 진짜 취약점은 `realistic_growth`·
`model_choice`·`fcf0` 같은 **입력 가정의 근거 부족**이고, BRO 6.75%가 "과거 기록
답습"이라 원 근거를 복원할 수 없는 상태가 그 증거다. 에이전트를 병렬로 띄워도
그 입력을 검증된 근거로 바꿔주지 않는다.

**기능 단위 예외**:
- DeepFund의 **point-in-time replay**(11) → P0-17과 같은 이유로 DEFER(시간 부족)
- investorskills(14)의 **skill 구조**(worldview·signals·filters·risk·monitoring)
  → `engine/research_lenses.py`(P0-14)가 이미 5축으로 담당 → **DUPLICATE**
- ai-architecture(13)의 **schema-driven contract** → `AnalysisInputs`·
  `experiments/*.json`(SHA-256 코어해시)·`Citation`이 이미 부분 구현 → DEFER

**Decision: 12·29 REJECT / 11·13 DEFER / 14 DUPLICATE**

---

# Repository 15, 16, 23, 24: Portfolio / Risk 계열

skfolio(15) · PyPortfolioOpt(16) · okama(23) · NVIDIA blueprint(24)

**§31 ANTI-FEATURE REGISTER 정면 충돌**:
> 상관행렬 기반 포트폴리오 최적화 — 수익률 시계열이 저장소에 없다. 없는
> 데이터로 최적화하면 정밀해 보이는 허구가 된다.

2026-08-19 실측 재확인: `price_at_analysis` **9/34종목**, 수익률 시계열 파일
**0건**. 넷 다 공분산 행렬을 입력으로 요구하는데, 그 입력을 만드는 순간
없는 데이터로 있는 척하는 행렬이 된다.

`scripts/build_buylist_2026_08_03.py`가 "공분산 최적화가 아니라 투명한 규칙기반
배분"이라고 스스로 명시한 것도 같은 판단이다.

**Decision: 전부 REJECT** (재개 조건: 20종목 이상 6개월 이상 수익률 시계열 확보)

---

# Repository 18, 25, 26, 27: Knowledge / Memory / News 계열

financial-knowledge-graphs(18) · worldmonitor(25) · investment-news(26) ·
honeclaw(27)

- **18 지식그래프**: entity·관계에 `valid_from`/`valid_to`/`source`/`confidence`를
  붙이는 발상은 `Citation`(P0-12)·`FinancialFact`(P0-02)가 값 단위로 이미 하고
  있다. 그래프 구조 자체는 실증 필요가 0건 → **DEFER**
- **25·26 뉴스/이벤트**: `thesis_monitor.py`(반증조건 스캔)·`growth_scorecard.py`가
  좁은 범위에서 "외부 신호 대조"를 담당한다. 뉴스 집계 파이프라인은 IRS의 현재
  병목(입력 근거 부족)과 무관 → **DEFER**
- **27 honeclaw**: company memory · thesis monitoring → `thesis.py` +
  `thesis_monitor.py` + P0-16 refresh boundary가 담당 → **DUPLICATE**

---

# Repository 19: financial-research-agent

**부분 DUPLICATE**. "검색 결과 하나만으로 중요한 결론을 확정하지 않는다"(§12)는
`Claim.is_triangulated()`(P0-12)가 이미 강제한다 — **서로 다른 출처 2개 이상**을
요구하며, 같은 출처 반복은 삼각검증으로 인정하지 않는다(IWM P/E 사건).

"Evidence가 없으면 NEGATIVE가 아니라 UNKNOWN"도 `Claim.status()`가
`UNSUPPORTED`(gap=True)로 처리해 이미 구현돼 있다.

재검색 루프(Query→Retrieve→Evaluate→부족하면 Re-search)는 LLM 실행 루프라
코드 계층의 문제가 아니다 → **DEFER**

---

# Repository 20, 21, 22: Screening 계열

investment-funnel(20) · TradingView-Screener(21) · tvscreener(22)

- **20 DUPLICATE**: `engine/screener.py`(380줄)가 DRS추정 → 필요FCF수익률 역산 →
  4분류 체크리스트 → 일괄 스크리닝 → 표 출력까지 전체 파이프라인을 담당한다.
  25개 분석 스크립트가 반복 사용했고 BSX false-rejection으로 한계까지 실측·
  문서화됐다(`KNOWN_SCREENER_FALSE_REJECTIONS`).
- **21·22 DEFER**: 필터 DSL·필드 발견 패턴은 자연어 프론트엔드가 필요해질 때
  참고 가치가 있으나 지금은 함수 호출로 충분하다. 또한 TradingView 데이터는
  Source Registry에 **미등록**이라 P0-01 거버넌스를 통과하지 못한다.

---

# Repository 28, 30

- **28 investment-theses DUPLICATE**: thesis versioning·lifecycle·change tracking은
  `thesis.py`(thesis_id = ticker-date, append-only decisions/evidence) +
  P0-16 refresh boundary가 담당.
- **30 mattpocock/skills DEFER**: SKILL.md 패턴은 엔지니어링 절차용이고, 투자
  방법론은 `research_lenses.py`가 담당한다. skill versioning(§21)은 실증 필요
  0건.

---

## 최종 정리

**신규 구현 1건**(Repo 04+17의 multiple testing · survivorship).
나머지 28건은 이전 P0 통합에서 완료됐거나, IRS의 실증 근거 부족 또는 §31
안티기능 등록부와의 충돌로 REJECT/DEFER.

⚠️ **REJECT/DEFER가 "그 저장소가 나쁘다"는 뜻이 아니다.** skfolio·PyPortfolioOpt·
qlib은 각자 영역에서 훌륭한 라이브러리이고, IRS에 맞지 않는 이유는 전부
**IRS 쪽 입력 부재**(수익률 시계열)나 **이미 담당하는 모듈 존재**다.
재개 조건을 각 항목에 명시해뒀다.
