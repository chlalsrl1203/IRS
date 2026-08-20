# 오픈소스 통합 기록 (§18 SOURCE ATTRIBUTION / §21 COMPLETION REPORT)

각 단계는 `SOURCE URL → CAPABILITY → IRS TARGET → METHOD → IMPLEMENTATION →
TEST`가 추적 가능해야 한다. 이 문서는 그 추적표이며, 상세 근거는 각 모듈의
docstring 상단 attribution 블록에 함께 남아 있다.

## 경로 매핑 원칙

통합 계획서는 `irs/data/...` 형태의 target을 쓰지만, 이 저장소의 기존 패키지
루트는 `engine/`이고 모든 import가 `from engine.X`다. §1.7("IRS의 기존
architecture와 domain model을 최우선으로 한다")·§1.14("외부 repository가 IRS
architecture를 무리하게 바꾸도록 하지 않는다")에 따라 **`irs/`를 새로 만들지
않고 `engine/` 아래로 1:1 매핑**한다.

| 계획서 경로 | 실제 경로 |
|---|---|
| `irs/data/governance/` | `engine/data/governance/` |
| `irs/data/providers/` | `engine/data/providers/` (P0-02~04 예정) |
| `irs/data/pit/` | 기존 `engine/filing_dates.py` + PIT 필드가 이미 담당 |
| `irs/evidence/` | P0-12 예정 |
| `irs/thesis/` | 기존 `engine/thesis.py`가 이미 존재 |

---

# P0-01 — Source Registry ✅ 완료 (2026-08-19)

## Source
https://github.com/simonlin1212/global-stock-data (Apache-2.0)

**실제 확인한 것**(§1.4 — README만 믿지 않는다):
- 저장소 실재·라이선스(Apache-2.0)·구조(`SKILL.md` 단일 파일에 수집 코드와
  티어표가 함께 들어 있음)
- `SKILL.md` 원문에서 컴플라이언스 티어 정의(S/B/C)와 출처별 속성 스키마,
  `_RateLimiter` 도메인별 상한 구현을 직접 확인
- 원본이 인용한 SEC 조건을 **1차 출처로 재확인**했다
  (https://www.sec.gov/os/webmaster-faq): *"our current maximum access rate is
  10 requests per second"*, User-Agent 선언 요구, *"All Government-created
  content on sec.gov and EDGAR public filing content are free to access and
  reuse"*, 스크립트 접근 명시적 허용.

## Capability
official-source-first · source registry · source authority · compliance tier ·
licensing metadata · rate limits · freshness · reliability

## IRS Target
- `engine/data/governance/source_registry.py` (신규)
- `engine/data/__init__.py` · `engine/data/governance/__init__.py` (신규 패키지)
- `engine/filing_dates.py` (레이트리밋 배선, 4줄)

## Method
**REIMPLEMENT** — 코드를 가져오지 않고 데이터 모델·거버넌스 규칙만 재구현.
원본은 수집 코드와 티어표가 한 파일에 섞여 있어 그대로 쓸 수 없고, 이 저장소는
이미 자체 수집 경로(`engine/filing_dates.py`)를 갖고 있다.

## Implementation

**IRS-native로 바꾼 것 4가지:**

1. **`UNVERIFIED`를 1급 상태로 승격.** 원본은 C급("조건 미확인")에 미확인을
   섞어 넣지만, 이 프로젝트는 "확인 못하면 미확인으로 정직하게 남길 것"을
   반복 원칙으로 확립했다. 미확인을 "제한적 허용"과 같은 칸에 넣으면 그
   구분이 사라진다. `check_use()`는 `ALLOWED`/`PROHIBITED`/`UNVERIFIED` 3값을
   반환하며, **`UNVERIFIED`는 허용도 금지도 아니다.**
2. **`last_verified` staleness를 코드로 검사.** 약관은 바뀐다. 365일이 지나면
   허용 범위 안이어도 판정이 `UNVERIFIED`로 강등된다(원본은 검증일을 적기만 한다).
3. **재배포를 원자료/파생분석으로 분리.** `redistribution_raw` vs
   `redistribution_derived` — IRS는 `ledger/*.json`에 벤더 원자료 수치를
   **그대로** 담아 공개 저장소에 올리므로, 파생 결론 공개와는 성격이 다른
   행위다. 이 구분 없이는 그 사실 자체가 드러나지 않는다.
4. **`provenance.SOURCE_KINDS`와 연결.** provider 단위 거버넌스(이 모듈)와
   값 단위 출처(`engine/provenance.py`)가 같은 어휘를 쓰도록 `__post_init__`에서
   강제하고 테스트로 고정했다.

**레이트리밋만 자동 적용한다.** 이 저장소의 다른 판정은 전부 "병기, 자동판정
안 함"인데 여기만 예외인 이유: 레이트리밋 초과는 해석의 여지가 있는 판단이
아니라 상대 서버가 차단하는 **기술적 사실**이고, 차단되면 분석이 중단된다.
SEC 상한(10/s)을 그대로 쓰지 않고 8/s로 낮춰 잡았다(동시 실행·재시도가 겹칠 수
있으므로). 등록부에 상한이 없는 호스트는 보수적 기본값 2/s.

## Tests
`tests/test_source_registry.py` — 14건 신규. 482 → **496개 전부 통과.**

고정한 불변조건: 미확인이 허용으로 오독되지 않음 / 두 계층이 같은 어휘를 씀 /
확인일 staleness / 레이트리밋이 실제 대기를 강제 / 미등록 출처가 조용히
통과하지 않음 / **`filing_dates`가 실제로 리미터를 호출함**(문서로만 둔 규칙이
무력화된 실패를 이미 네 번 겪었다).

## Verification

- 전체 테스트 **496개 통과**
- 34종목 골든재현 **8개 지표 완전 동일**(실패 0건)
- baseline fingerprint `fbd34322…` **불변**
- `ENGINE_VERSION` v3.53 → **v3.54**(`engine/` 변경 시 상수를 올리는 v3.32 규칙)
- ledger 파일 **무수정**

### ⚠️ 테스트가 실제 결함을 하나 잡았다

`RateLimiter._last`를 `0.0`으로 초기화하면 **첫 요청도 대기한다.**
`time.monotonic()`은 큰 값이라 우연히 안 걸리지만, 0에서 시작하는 시계에서는
걸린다. `None` 초기화로 고쳤다.

### ⚠️ 등록부가 즉시 드러낸 사실 — 6건 중 4건이 미확인

| key | 티어 | 권위 | 확인일 |
|---|---|---|---|
| `sec_edgar` | FREE_COMMERCIAL | PRIMARY_FILING | 2026-08-19 |
| `analyst_input` | FREE_COMMERCIAL | ANALYST | 2026-08-19 |
| `alpha_vantage` | **UNVERIFIED** | VENDOR | — |
| `fmp` | **UNVERIFIED** | VENDOR | — |
| `stockanalysis` | **UNVERIFIED** | AGGREGATOR_WEB | — |
| `web_research` | **UNVERIFIED** | AGGREGATOR_WEB | — |

Alpha Vantage 약관은 실제로 **확인에 실패**했다 — 공개 약관이 PDF이며 본문이
판독되지 않아 재배포·상업이용 조항을 읽을 수 없었다. **추측해 채우지 않았다.**

리포트: `reports/source_registry_audit_2026-08-19.json`

## Remaining Risk

1. **`ledger/*.json`은 벤더 원자료 수치를 그대로 담아 공개 저장소에 올린다.**
   Alpha Vantage·FMP·stockanalysis의 `raw_redistribution` 조항이 미확인이므로
   **이 행위의 적법성은 현재 미확정**이다. 등록부가 그 사실을 숨기지 않도록
   테스트로 고정해뒀다(`test_raw_redistribution_of_vendor_data_is_not_claimed_as_allowed`).
   해소하려면 각 벤더 약관을 실제로 확인해야 한다(다음 세션 과제).
2. 등록부는 **강제하지 않는다**(레이트리밋 제외). 기존 분석 스크립트는
   `check_use()`를 부르지 않으므로, 미확인 출처를 계속 쓸 수 있다. 강제 지점을
   어디에 둘지는 P0-02 provider 인터페이스에서 결정한다.
3. 신뢰도(`reliability`) 서술은 **이 저장소가 실제로 관측한 사례**만 담았고
   (ONON 4.7% 오차, TYL SBC 3배 오류, FMP 비일관 실패) 벤더 전반의 정확도를
   측정한 것이 아니다.

## Commit
`89d15d7`

## Next
**P0-02 Provider Interface** — 등록부를 실제 수집 경로에 연결하는 추상 계층.
여기서 "미확인 출처를 어디서 차단할 것인가"를 결정한다.

---

# P0-02 — Provider Interface ✅ 완료 (2026-08-19)

## Source
- https://github.com/dgunning/edgartools — typed filing abstraction, adapter 경계
- https://github.com/eddmpython/dartlab — SEC/DART 통합 Company 추상화
- https://github.com/simonlin1212/global-stock-data — source governance 연결

## Capability
provider abstraction · typed domain object · adapter 경계 · 시장 중립 인터페이스

## IRS Target
- `engine/data/providers/base.py` (신규)
- `engine/data/providers/__init__.py` (신규)

## Method
**REIMPLEMENT** — 어느 라이브러리의 클래스도 상속하거나 재노출하지 않는다.
가져온 것은 **경계 설계**뿐이다: 외부 객체가 도메인으로 새지 않게 하는 구조
(§1.8)와, SEC/DART처럼 서로 다른 시장을 같은 인터페이스로 다루는 발상(DartLab).

## Implementation

**`FinancialFact`** — §14 CORE DATA CONTRACT를 이 계층이 실제로 보장할 수 있는
만큼 담는다. 핵심은 **`period` ≠ `available_at`**: 무엇에 대한 수치인가(FY2023
매출)와 언제부터 알 수 있었는가(그 10-K 제출일)를 분리한다. 섞이면 PIT 검증이
통째로 무의미해지며, 이 저장소는 v3.47~v3.49에서 이미 그 대가를 치렀다.
`available_at < period_end`면 **예외**를 던진다(기간이 끝나기 전에 그 기간
실적이 공시될 수는 없다).

`version`·`restated_at`은 **의도적으로 넣지 않았다.** 재작성 이력을 추적하려면
같은 사실의 여러 판본을 저장해야 하고 그건 스냅샷 계층(P0-09)이 생겨야 의미가
있다 — 지금 만들면 항상 None인 칸이 된다(Simplicity First).

**`ProviderResult`** — `to_series()`가 `AnalysisInputs.*_by_year`에 바로 넣을
수 있는 형태를 주되, **같은 연도에 다른 값이 둘 오면 예외를 던진다.** provider가
임의로 고르면 어느 값이 살아남았는지 알 수 없다(대조·선택은 P0-07의 몫).

### P0-01이 남긴 질문에 답했다 — "미확인 출처를 어디서 차단할 것인가"

| 판정 | provider 동작 |
|---|---|
| `PROHIBITED` | **거부**(`ProviderGovernanceError`) |
| `UNVERIFIED` | **진행하되 결과에 경고를 싣는다** |
| `ALLOWED` | 진행 |

`UNVERIFIED`에서 차단하지 않는 이유: 현재 등록된 6건 중 4건이 미확인이라 여기서
막으면 돌아가던 스크리닝이 전부 멈춘다. **그러나 조용히 통과시키지도 않는다** —
모든 `ProviderResult`가 `governance` 판정과 경고 문자열을 들고 다니므로
ledger·리포트까지 따라간다. "미확인이니 일단 진행"과 "미확인인 줄 모르고 진행"은
다르다.

## Tests
`tests/test_provider_base.py` — 17건 신규. 496 → **514개 전부 통과.**

## Verification

- 전체 테스트 **514개 통과**
- 34종목 골든재현 **8개 지표 완전 동일**
- baseline fingerprint `fbd34322…` **불변**, ledger 무수정

### ⚠️ 테스트가 P0-01의 논리 결함을 잡았다 — 불확실성이 "아니오"를 완화하고 있었다

`check_use()` 초판은 `UNVERIFIED` 티어를 **먼저** 검사해서, 허용 범위 **밖**인
목적까지 "아마도"로 만들었다(`web_research` + `raw_redistribution`이
PROHIBITED가 아니라 UNVERIFIED로 나왔다). 불확실성이 "아니오"를 약화시키면
보수적 방향과 정반대로 작동한다. 판정 순서를 고쳐 **허용 범위 밖은 티어와
무관하게 먼저 막도록** 했고, 어휘를 명확히 정의했다:

- `PROHIBITED` — 이 등록부가 그 목적을 **승인하지 않는다**(약관이 금지하거나,
  확인 전까지 스스로 하지 않기로 한 경우 둘 다. 어느 쪽인지는 `reason`이 말한다)
- `UNVERIFIED` — 목적은 허용 범위 안이지만 그 근거인 약관을 확인하지 못했다

회귀 테스트: `test_uncertainty_never_softens_a_no_into_a_maybe`

### ⚠️ 그 결과 드러난 사실 — 현재 관행이 "승인되지 않음"으로 나온다

| 출처 | internal_research | derived_publication | raw_redistribution | commercial |
|---|---|---|---|---|
| `sec_edgar` | ALLOWED | ALLOWED | ALLOWED | ALLOWED |
| `analyst_input` | ALLOWED | ALLOWED | ALLOWED | ALLOWED |
| `alpha_vantage` | UNVERIFIED | **PROHIBITED** | **PROHIBITED** | **PROHIBITED** |
| `fmp` | UNVERIFIED | **PROHIBITED** | **PROHIBITED** | **PROHIBITED** |
| `stockanalysis` | UNVERIFIED | **PROHIBITED** | **PROHIBITED** | **PROHIBITED** |
| `web_research` | UNVERIFIED | **PROHIBITED** | **PROHIBITED** | **PROHIBITED** |

IRS는 실제로 Alpha Vantage 원자료를 `ledger/*.json`에 담아 공개 저장소에 올리고
(raw_redistribution), 그로부터 나온 Gap·판정을 공개한다(derived_publication).
**이것이 위법이라는 뜻이 아니라 "확인한 적이 없다"는 뜻이다** — 등록부는
승인하지 않은 것을 승인했다고 말하지 않는다. 해소하려면 각 벤더 약관을 실제로
확인해야 한다.

## Remaining Risk

1. 위 표의 미확인 4건이 그대로 남아 있다. 벤더 약관 확인이 선행되지 않으면
   provider를 만들어도 경고가 계속 붙는다.
2. `FinancialProvider`는 아직 **구현체가 없다**(P0-03 SEC 어댑터에서 처음
   생긴다). 인터페이스만으로는 아무 데이터도 들어오지 않는다.
3. 기존 분석 스크립트는 여전히 dict 리터럴로 원자료를 넣는다 — provider 경로로
   옮기는 것은 별개 작업이며, 옮기기 전까지 `data_sources` 자유문자열 상태가
   유지된다.

## Commit
`336f9e1`

## Next
**P0-03 SEC / EDGAR Adapter** — `FinancialProvider`의 첫 구현체. edgartools를
ADAPT할지, 기존 `engine/filing_dates.py`의 companyfacts 경로를 확장할지를
**실제 코드·라이선스·의존성을 확인한 뒤** 결정한다(§1.4).

---

# P0-03 — SEC / EDGAR Adapter ✅ 완료 (2026-08-19)

## Source
https://github.com/dgunning/edgartools (MIT)

## Capability
SEC EDGAR · XBRL 표준화 재무제표 · typed filing abstraction

## IRS Target
`engine/data/providers/sec.py` — `SecCompanyFactsProvider`

## Method
### ⚠️ 계획서의 **ADAPT → REIMPLEMENT로 변경**했다. 근거는 실제 확인이다(§1.4)

| 확인 항목 | 사실 |
|---|---|
| edgartools 런타임 의존성 | **21개**(pyproject.toml 직접 확인): httpx·pandas·pyarrow·lxml·pydantic·rich·orjson·rapidfuzz 등 |
| IRS 현재 런타임 의존성 | **0개** — `engine/` 전체가 stdlib만 쓴다. `requirements.txt`·`pyproject.toml` 없음 |
| CI | `.github/workflows/tests.yml`이 `pip install pytest` 한 줄뿐 |
| IRS가 실제로 필요한 것 | 연간 재무수치 + 제출일 — `engine/filing_dates.py`가 **이미 stdlib으로** 가져오고 있다(ONON 사건에서 실전 검증) |

ADAPT는 의존성 0개 프로젝트에 21개 트리를 들이고, 의존성 관리 파일을 신설하고,
CI를 바꾸는 일이다 — §1.14·§1.15에 정면으로 걸린다.

**REJECT가 아니라 REIMPLEMENT다.** edgartools에서 실제로 가져온 설계는 둘:
**XBRL 태그 표준화**(회사·연도마다 태그가 달라 우선순위 목록으로 정규화)와
**어댑터 경계**(외부 응답 객체를 도메인에 노출하지 않음, §1.8).

## Implementation

8개 지표에 대한 태그 우선순위(us-gaap + ifrs-full), 연간/시점 구분, 최초 공시본
선택, `available_at` 추출. 네트워크는 `engine/filing_dates.py`에 위임한다
(P0-01 레이트리밋이 거기 걸려 있어 우회 경로를 새로 만들지 않는다).

### ⚠️ 실측이 잡은 결함 — 긴 시계열이 한 태그로 덮이지 않는다

BSX 실데이터로 돌리자 **FY2015 매출이 통째로 사라졌다.** 원인은 초판의 "첫 태그에서
멈춤"이었다 — ASC 606(2018) 전후로 회사가 쓰는 태그가 갈린다(`Revenues` →
`RevenueFromContractWithCustomerExcludingAssessedTax`). 우선순위 태그부터 훑되
**비어 있는 연도만** 하위 태그로 보충하도록 고쳤고, 태그가 섞이면
`[태그 혼재]` 경고를 남긴다(정의가 구간마다 다를 수 있으므로).
회귀 테스트: `test_long_series_spanning_a_tag_change_is_not_silently_truncated`

## Tests
`tests/test_sec_provider.py` — 15건 신규(**네트워크 없이** 합성 companyfacts).
514 → **529개 전부 통과.**

## Verification

- 34종목 골든재현 **8개 지표 완전 동일**, baseline fingerprint `fbd34322…` **불변**
- ledger 파일 **무수정**

### ⭐ 실데이터 대조 — BSX 11개년, ledger(벤더) vs SEC 1차자료

| 지표 | 일치 | 비고 |
|---|---|---|
| `operating_cashflow` | **11/11** | 완전 일치 |
| `revenue` | 10/11 | FY2015만 불일치(7,477 vs 8,068, +7.9% — 태그 정의 차이) |
| `capex` | 9/11 | FY2022 −3.9%, FY2023 −11.1% |
| `operating_income` | **0/11** | **전 연도 불일치**, −141% ~ +7.4% |

`operating_income`이 전 연도 어긋난다. 벤더가 정규화(일회성 항목 제외)한 값을
주고 SEC는 GAAP 원값을 주기 때문으로 보이나 **원인을 확정하지 않았다** — 확정은
P0-07 reconcile의 몫이다.

**영향 정량화**(공식 판정은 건드리지 않고 측정만):

| | ledger(벤더) | SEC |
|---|---|---|
| margin_volatility | 4.00 | **8.00** |
| DRS | 43.80 | **47.80** |
| Implied Growth | 8.00% | 8.21% |
| **Expectation Gap** | **+5.87%p** | **+5.65%p** |
| RAR | +0.4926 | +0.4235 |
| 판정 | 저평가 가능성 | 저평가 가능성 (**불변**) |

판정은 뒤집히지 않았다. 다만 **BSX의 Gap은 +5%p 경계 바로 위(+5.87%p)라 이
0.22%p 이동이 남은 여유의 약 25%를 먹는다** — 무시할 만한 차이가 아니다.

리포트: `reports/sec_provider_crosscheck_2026-08-19.json`

## Remaining Risk

1. **`operating_income` 불일치의 원인이 미확정이다.** 어느 쪽이 "옳은" 값인지
   이 단계에서 판정하지 않는다(P0-07). 지금 확정된 것은 **두 출처가 다르다는
   사실과 그 크기**뿐이다.
2. **기존 34종목 ledger를 SEC 값으로 바꾸지 않았다.** 소급 교체는 (a) 어느
   정의가 옳은지 미확정이고 (b) 34종목 전체 판정에 영향을 주므로, 대조 계층이
   완성된 뒤 사용자 승인 아래 결정할 사안이다.
3. `[태그 혼재]` 구간은 정의가 연도마다 다를 수 있어 그 구간을 지나는 CAGR은
   경계 연도를 확인해야 한다.
4. 재작성(restatement)은 여전히 구분하지 못한다 — 스냅샷 계층(P0-09) 사안.

## Commit
`f60513b`

## Next
**P0-04 DART Adapter** — DartLab을 확인해 한국 시장을 같은 `FinancialProvider`
인터페이스로 들일 수 있는지 판단한다. 그 다음 P0-05~07(canonical model ·
normalize · reconcile)에서 이번에 발견한 `operating_income` 불일치를 다룬다.

---

# P0-04 — DART Adapter ⏸ DEFER (2026-08-19)

## Source
https://github.com/eddmpython/dartlab (코드 Apache-2.0 / 데이터셋 CC BY 4.0)

**실제 확인한 것**(§1.4): 저장소 실재·이중 라이선스·구조(`src/dartlab/`·`tests/`·
`ui/`·`pyodide/` 등), 런타임은 **Polars·numpy·HuggingFace 연동**에 의존하며
사전구축 데이터를 HuggingFace에서 자동 다운로드해 캐시한다. DART API 키는
`dartlab collect`(원자료 재수집)에만 필요하다.

## Decision: **DEFER** (REJECT 아님)

계획서 순서상 P0-04지만 **지금 만들지 않는다.** 근거는 저장소 실측이다:

| 확인 | 사실 |
|---|---|
| `ledger/` | 미국 기업 **34건** |
| `ledger_krx/` | **31건 전부 ETF 래퍼** — `inputs`가 `pe_by_source`·`expense_ratio`·`top10_weight`이고 기업 재무제표(revenue/OCF/capex)가 **없다** |
| 한국 **기업** 재무분석 | **0건** |

즉 DART 어댑터는 **IRS가 한 번도 분석한 적 없는 시장**을 위한 데이터 경로다.
CLAUDE.md의 Simplicity First가 정확히 이 경우를 겨냥한다 — *"지금 분석 중인
종목이 실제로 이 기능을 요구하는가, 아니면 '나중에 필요할 것 같아서'인가?
후자면 넣지 않는다."* 게다가 DartLab 채택은 Polars·numpy·HuggingFace를
의존성 0개 프로젝트에 들이는 일이라 P0-03에서 edgartools를 REIMPLEMENT로
돌린 것과 같은 문제에 걸린다.

## 그래도 가져온 것 — 이미 반영돼 있다

DartLab의 핵심 아이디어(**SEC와 DART를 하나의 Company 인터페이스로**)는
P0-02에서 이미 흡수했다: `FinancialProvider`는 시장 중립이며
`SecCompanyFactsProvider`는 그 구현체 중 하나일 뿐이다. 한국 기업을 실제로
분석할 일이 생기면 `DartProvider(FinancialProvider)`를 추가하는 것으로 끝나고,
도메인 코드는 바뀌지 않는다 — **인터페이스가 이미 그 자리를 비워뒀다.**

## 재개 조건

IRS가 한국 **기업**(ETF 래퍼가 아니라)을 실제로 분석하기로 할 때. 그 시점에도
DartLab 채택보다 `engine/filing_dates.py`처럼 stdlib으로 DART Open API를 직접
호출하는 편이 이 저장소 구조에 맞을 가능성이 높다(P0-03과 동일 판단).

## Next
**P0-05~07**(Canonical Financial Data Model · Normalization · Reconciliation) —
P0-03이 발견한 `operating_income` 벤더-SEC 불일치(BSX 11/11 연도)를 다룰 계층.
지금 확정된 것은 "두 출처가 다르다"는 사실뿐이고, 어느 쪽을 쓸지는 이 계층이
만들어져야 답할 수 있다.

---

# P0-05 / P0-06 / P0-07 — Canonical Model · Normalization · Reconciliation ✅ 완료 (2026-08-19)

세 단계를 한 데이터 흐름으로 묶어 구현했다(§4.1의 목표 구조
`Raw → Normalize → Compare → Reconcile → Validate → Canonical`). 각각 따로 만들면
어느 하나도 단독으로는 쓸 수 없어 검증이 불가능하다.

## Source
https://github.com/chenditc/investment_data (Apache-2.0)

**실제 확인한 것**(§1.4): 저장소 실재·라이선스, `final_a_stock_eod_price` 대조
테이블 전략(출처별 원본 테이블 `ts_*`/`yahoo_*`을 **남긴 채** 별도 canonical 층을
만든다), `ts_link_table`을 통한 교차검증, `qlib_bin.manifest.json` 버저닝.

## Capability
multi-source normalization · source comparison · reconciliation ·
conflict detection · missing-data handling · canonical("final") 계층 분리

## IRS Target
- `engine/data/canonical.py` — 정규화 + `CanonicalValue`/`CanonicalSeries`
- `engine/data/reconcile.py` — 불일치 등급화 + 대조 정책
- `scripts/reconcile_ledgers_vs_sec_2026_08_19.py` — 실측 대조

## Method
**REIMPLEMENT** — 원본은 SQL 테이블 + shell 파이프라인이고 대상이 **가격
시계열**이다. IRS가 다루는 것은 **회계 수치**이며, 회계 수치의 불일치는 "둘 중
하나가 틀렸다"보다 **"정의가 다르다"**인 경우가 많아(정규화 영업이익 vs GAAP)
원본의 자동 정렬(`adjust_ratio` 재계산)을 옮겨오지 않았다. 가져온 것은 두 가지:
**출처별 원본을 지우지 않고 대조본을 별도 계층으로 둔다**는 원칙과 **교차검증을
상시 절차로 둔다**는 원칙.

## Implementation

### 정규화가 다루는 3가지 — 전부 이 저장소가 실제로 겪은 사고

| 항목 | 처리 | 근거 사고 |
|---|---|---|
| 스케일 | `detect_scale_mismatch()` — **의심만 보고, 자동수정 안 함** | RAR 100배 오류(v3.19) |
| 부호 | `normalize_sign()` — 뒤집기가 아니라 **절댓값** | capex 부호 사고 |
| 통화 | 혼입 시 **오류**(환율 변환 안 함) | M-6, PDD의 CNY 미표기 |

부호를 `-value`로 뒤집지 않고 `abs()`로 맞춘 이유: 뒤집기는 이미 올바른 부호로
온 값까지 망가뜨려, 어느 벤더가 들어왔느냐에 따라 결과가 달라진다.

### ⚠️ 핵심 결정 — 물질적 불일치를 자동 해결하지 않는다

권위 서열(1차 공시 > 규제기관 > 벤더 > 웹)로 자동 선택하는 것이 손쉽지만, BSX
사례가 그러면 안 되는 이유를 보여준다: 벤더 영업이익이 **틀린 것이 아니라 다른
정의**(일회성 항목 제외)일 수 있다. 자동으로 SEC를 택하면 34종목 입력이 조용히
바뀌고 그 변화를 추적할 수 없다.

- 작은 차이(≤1%)는 자동 해결 — 판단할 것이 없다
- 물질적 차이는 `requires_review=True`, 권위 서열은 **제안**으로만
  (`suggested_source_key`), 채택은 분석자가 정한다
- **부호가 갈리면 편차 크기와 무관하게 무조건 MATERIAL**(BSX FY2015: 벤더
  +790M 이익 vs SEC −327M 손실 — 같은 것을 재고 있지 않다는 뜻)

`TOLERANCE_TIERS`는 `VALIDATION_STATUS`에 **IMPLEMENTED_NOT_VALIDATED**로 명시했다.

## Tests
`tests/test_canonical_reconcile.py` — 16건 신규. 529 → **545개 전부 통과.**

### ⚠️ 테스트가 또 실질 결함을 잡았다

`strict=False`로 미해결 충돌을 감수할 때 `{2025: None}`이 시계열에 섞여
`AnalysisInputs`로 흘러갔다. `None`은 값이 아니므로 시계열에서 제외하도록 고쳤다
(빠진 연도는 `unresolved_conflicts()`·리포트에 그대로 드러난다).

## Verification

- 전체 **545개 통과**, 34종목 골든재현 8개 지표 완전 동일
- baseline fingerprint `fbd34322…` **불변**, **ledger 파일 무수정**

### ⭐ 실측 — 8종목 336개 값을 SEC 1차자료와 전수 대조

`scripts/reconcile_ledgers_vs_sec_2026_08_19.py` (BSX·CDNS·ROP·TYL·GWRE·PGR·ACGL·WM)

| 지표 | 값수 | EXACT | ROUNDING | MINOR | **MATERIAL** | 중앙편차 | 최대편차 |
|---|---|---|---|---|---|---|---|
| revenue | 84 | 75 | 1 | 2 | **6** | 7.33% | 27.2% |
| operating_income | 84 | 63 | 0 | 0 | **21** | 16.15% | **141.4%** |
| operating_cashflow | 84 | 71 | 1 | 0 | **12** | 13.58% | 26.4% |
| capex | 84 | 52 | 0 | 4 | **28** | 14.17% | 71.9% |

**BSX 1종목에서 본 문제가 전반적이다.** 건수로는 **capex(28건)**가 가장 많고
크기로는 **operating_income(141%)**이 가장 크다. 둘 다 FCF·DRS를 통해 판정에
직결되는 입력이다.

**분포가 이봉(bimodal)이다** — 중간 등급(ROUNDING·MINOR)이 8건뿐이고 나머지는
EXACT 아니면 MATERIAL이다. 이는 차이가 "측정 잡음"이 아니라 **"정의가 다르다"**
쪽임을 시사한다(임계값을 이 데이터에 맞춰 조정하지 않았다 — 실행 전에 고정했다).

### 판정 영향 — 8/8 불변, 그러나 DRS는 크게 움직인다

SEC 값으로 전면 대체한 **시나리오**(옳은 값이라는 뜻이 아니다):

| 종목 | Gap(ledger) | Gap(SEC) | 차이 | DRS 변화 | 판정 |
|---|---|---|---|---|---|
| ROP | +1.24% | +0.41% | **−0.83%p** | **31.5 → 47.5** | 불변 |
| BSX | +5.87% | +5.56% | −0.31%p | 43.8 → 47.8 | 불변 |
| TYL | +2.77% | +3.09% | +0.31%p | 33.0 → 33.0 | 불변 |
| GWRE | +3.15% | +3.27% | +0.12%p | 39.1 → 39.1 | 불변 |
| PGR·ACGL·WM | — | — | 0.00%p | 불변 | 불변 |
| CDNS | **측정 불가** | | | | SEC 시계열이 불완전 |

**판정은 하나도 뒤집히지 않았다** — 안심할 근거다. 다만 **ROP의 DRS가 출처
선택만으로 16점 움직인다**(31.5→47.5). R-001 감사가 DRS를 정의역 전체로 흔들어
Gap 중앙 4.90%p를 얻었던 것과 대비하면, **데이터 출처 선택이 그 축의 상당 부분을
차지할 수 있다**는 뜻이다.

리포트: `reports/ledger_vs_sec_reconciliation_2026-08-19.json` ·
`reports/ledger_vs_sec_impact_2026-08-19.json`

## Remaining Risk

1. **어느 값이 옳은지는 여전히 미확정이다.** 이 계층은 "다르다"와 "얼마나"를
   확정했을 뿐이다. `operating_income`이 벤더의 정규화값인지 SEC가 GAAP 원값인지는
   원자료(10-K 손익계산서 주석)를 봐야 한다.
2. **34종목 중 8종목만 대조했다.** 나머지 26종목은 미측정이다.
3. **CDNS는 SEC 시계열이 불완전해 영향 측정 자체가 불가능했다** — 태그 커버리지
   문제일 수 있다(미해결).
4. ledger 측 `available_at`은 **미상**이라 회계기간 종료일로 표시만 했다(기존
   34종목에 PIT 필드가 없다). 대조 계산에는 쓰이지 않는다.
5. 재작성(restatement) 구분은 여전히 불가 — 스냅샷 계층(P0-09) 사안.

## Commit
`a1781d8`

## Next
**P0-08 Provenance**(이미 `engine/provenance.py` 존재 — 이 계층과 연결이 필요한지
확인) → **P0-09 Snapshot**(재작성 추적의 전제) → **P0-10 PIT/As-of Engine**
(`engine/filing_dates.py`가 이미 담당하는 부분과 중복 여부 확인 필요).

---

# P0-08 / P0-09 / P0-10 — Provenance 연결 · Snapshot · PIT 연결 ✅ 완료 (2026-08-19)

## Source
https://github.com/chenditc/investment_data (Apache-2.0) — `qlib_bin.manifest.json`
버저닝/재현 아카이브

## Method
- **P0-08 Provenance: DUPLICATE → 연결**. `engine/provenance.py`(v3.50)가 이미
  존재한다. 새로 만들지 않고 `FinancialFact.to_provenance()`로 **변환**했다 —
  두 타입이 같은 7개 축을 담는 중복을 새 타입 없이 해소한다(§1.11).
- **P0-10 PIT: DUPLICATE → 연결**. `engine/filing_dates.py`가 이미 담당한다.
- **P0-09 Snapshot: REIMPLEMENT**. 원본은 릴리스 tarball + manifest로 **배포**가
  목적이지만, IRS가 필요한 것은 **"그때 무엇을 봤는가"의 증거**라 값 단위 해시와
  매니페스트만 가져오고 아카이브 포맷은 옮기지 않았다.

## Implementation

### ⭐ P0-10에서 발견한 실질적 결함 — PIT가 쓰지도 않은 값의 날짜를 검사할 수 있었다

`pit_inputs_for()`는 제출일을 **별도로 다시 조회**한다. 값이 벤더에서 오고
날짜가 SEC에서 오면, **PIT 검증이 실제로 쓰지도 않은 값의 날짜를 검사**하게 된다
(현재 34종목이 정확히 그 구조 — 값은 Alpha Vantage, PIT는 미기입).

`ProviderResult.to_pit_inputs()`는 **이미 가져온 사실에서** PIT 필드를 만든다.
값과 날짜가 같은 `FinancialFact`에서 나오므로 그 괴리가 원천적으로 생기지 않고,
SEC 호출도 한 번 줄어든다. `pit_inputs_for()`는 provider를 쓰지 않는 기존 경로용으로
그대로 둔다.

### P0-09 스냅샷 — 여러 곳에서 미뤄둔 항목의 공통 전제조건

| 미뤄둔 곳 | 답하지 못하던 질문 |
|---|---|
| `filing_dates.py` docstring | "그때 숫자가 이거였는가"(재작성 여부) |
| v3.49 PIT 감사 | 34종목을 `PIT_VALID`로 못 올린 유일한 이유 |
| `docs/change_plan.md` C-09 | Provenance를 DEFERRED로 둔 사유 |
| P0-02 `FinancialFact` | `version`·`restated_at`을 안 넣은 이유 |

전부 하나에 걸려 있었다 — **원자료를 조회 시점 그대로 보관해야 한다.**

두 가지를 못박았다: (a) **소급 스냅샷을 만들지 않는다**(오늘 조회값을 그때 값인
양 저장하면 허위 증거 — provenance v3.50과 동일 판단), (b) **스냅샷 1개로
"재작성 없음"이라 말하지 않는다**(`comparable=False`, "알 수 없음" — 데이터
부재를 안전 신호로 오독하지 않는다, v3.37 겹침 측정의 교훈).

같은 날 내용이 다른 스냅샷은 **거부**한다(v3.46이 `save_ledger()`에서 잡은 사고).

## Tests
`tests/test_snapshot_pit_provenance.py` — 16건 신규. 545 → **561개 전부 통과.**

## Verification

### ⭐ 전 계층 관통 — 이 저장소 **최초의 `PIT_VALID` 분석**

BSX 실데이터로 provider → 스냅샷 → provenance → PIT → `run_analysis()`까지:

```
스냅샷      snapshots/sec_edgar/BSX_2026-08-19.json
provenance  PROVENANCE_RECORDED / 커버 44건 / 누락 0건
PIT 입력    analysis_as_of=2026-08-19, filing_dates 11개년
```

| | 현재 ledger(PIT 미기입) | provider PIT |
|---|---|---|
| `point_in_time.status` | `PIT_UNKNOWN` | **`PIT_VALID`** (위반 0건) |
| Gap | 0.058653 | 0.058653 |
| 판정 / DRS / Confidence | 저평가 가능성 / 43.8 / 94 | **완전 동일** |

v3.47이 PIT 필드를 만든 뒤 **34종목 중 채운 것이 0건**이었고, v3.49가 조회 수단을
만들었지만 여전히 0건이었다. 그 경로가 실제로 끝까지 통한 첫 사례다.
계산 경로에는 전혀 관여하지 않는다(순수 기록 경로).

### ⚠️ 실측이 드러낸 미묘함 — `available_at`의 정확한 의미

BSX FY2016·2017·2018의 제출일이 전부 `2019-02-19`로 나왔다. 세 해 모두
`Revenues` 태그로는 FY2018 10-K에서 처음 등장하기 때문이다(ASC 606 전환).

즉 이 값은 **"그 회계연도 실적이 처음 공시된 날"이 아니라 "그 수치가 이 태그로
처음 등장한 날"**이다. PIT 관점에서는 **보수적**이라(실제보다 늦은 날짜) 미래정보
사용을 놓치지 않지만, 분석일이 원 공시일과 태그 최초등장일 사이면 **거짓 양성**이
날 수 있다. `sec.py` docstring에 명시했다.

## Remaining Risk

1. **스냅샷은 오늘 1건뿐이다.** 재작성 탐지는 시간이 지나 2건 이상 쌓여야
   작동한다 — 지금은 `comparable=False`가 정확한 상태다.
2. 기존 34종목은 여전히 `PIT_UNKNOWN`이며 **소급하지 않는다.**
3. `available_at` 거짓 양성 가능성(위).

## Commit
`8efc325`

## Next
**P0-11 Financial Document Intelligence** 이후는 성격이 다르다(문서 파싱·평가·
논거). 지금까지의 P0-01~10은 **데이터 계층**을 세운 것이고, 그 계층이 실제로
관통됨을 BSX로 확인했다.

---

# P0-11 / P0-12 / P0-13 — Document Index · Evidence Engine · Hard Gates ✅ 완료 (2026-08-19)

## Source
- https://github.com/dgunning/edgartools (MIT) — filing 접근·typed abstraction
- https://github.com/noahnan-max/private-equity-investment-dd-skill — Evidence Matrix·Triangulation
- https://github.com/DimaMerc/TieOutBench (MIT) — hard gates·auto-fail·calibrated uncertainty

**TieOutBench 실제 확인**(§1.4): MIT, 하드 게이트가 `GATE.SCALE`·`GATE.RECON`·
`GATE.MATCH`·`GATE.BRIDGE`·`GATE.FABRICATION`·`GATE.FREELUNCH`·`GATE.DIRECTION`·
`GATE.BASIS`로 명명돼 있고, *"not determinable from this packet"*이라 말하면
**감점이 아니라 credit**을 받는 refusal probe 구조.

## Method — 전부 REIMPLEMENT

## P0-11: 범위를 의도적으로 좁혔다 — **본문 파싱을 하지 않는다**

계획서는 "Financial Document Intelligence"지만 10-K 본문 섹션 추출을 하지 않았다:

1. **실증 사례가 0건이다.** IRS의 정성 조사는 전부 WebSearch로 했고, 본문 파싱이
   없어서 막힌 분석이 하나도 없다.
2. **HTML/PDF 파싱은 lxml·beautifulsoup4를 부른다** — P0-03에서 edgartools를
   돌린 것과 같은 벽(의존성 0개).
3. **정작 막혀 있던 것은 본문이 아니라 인용이다.** 본문을 긁어와도 담을 계약이
   없으면 또 자유 문자열이 된다.

그래서 **문서 신원(identity)만** 다룬다 — SEC submissions API로 어떤 서식이 언제
제출됐고 원문이 어디 있는가. `filing_date`(제출일)와 `report_date`(대상 기간)를
분리하고, SEC가 오래된 공시를 별도 파일로 분리하는 사실을 `truncated`로 드러낸다
(**"여기 없다"가 "공시가 없다"는 아니다**).

## P0-12: 이 저장소 정성 경로에는 계약이 아예 없었다

`thesis.build_evidence()`의 `source`가 **자유 문자열**이라 §15가 요구하는
Document·Location·Verification·Confidence가 전혀 없었다. 그 결과:

- **TYL SBC 3배 오류**: 인용에 문서·위치가 없어 **어디서 왔는지 되짚을 수 없었다**
- **S/A등급 13종목 + B/C/D등급 20종목 정성조사**: 전부 채팅 요약으로만 존재

`Citation`(source_key·document·**location 필수**·observed_date·url·quote) →
`Evidence`(direction·verification·confidence) → `Claim` → `EvidenceMatrix`.

핵심 강제 3가지:
- **2차 출처를 `VERIFIED_PRIMARY`로 표시할 수 없다** — TYL 사고가 정확히 이 형태였다
- **반대 증거는 찬성 증거 수와 무관하게 우선한다**(`CONTRADICTED`) — "그래도 좋아
  보인다"가 사후합리화다(`thesis.py`의 INVALIDATED와 같은 계열)
- **삼각검증은 서로 다른 출처 2개 이상을 요구한다** — 같은 출처를 두 번 인용하는
  것은 삼각검증이 아니다(IWM P/E 사건: 한 출처의 집계방식 편향은 반복해도 안 드러난다)

**점수를 내지 않는다.** 지지된 주장 수를 세어 단일 점수로 만들면 공백(gap)이 점수
뒤에 숨는다 — §31 안티기능 등록부의 "단일 합성점수"와 같은 이유. 리포트는
**공백과 모순을 먼저** 보여주고, 중요도 HIGH인데 1차 확인이 없는 주장을
`material_without_primary`로 따로 뽑는다(TYL 사고의 조기 경보).

## P0-13: 실증 사고가 있는 게이트만 골랐다

| 게이트 | 대응하는 실제 사고 |
|---|---|
| `GATE.FABRICATION` | TYL SBC/FCF 62% vs 실제 24.4% |
| `GATE.SCALE` | RAR 100배 오류(v3.19, 4종목) |
| `GATE.DIRECTION` | capex 부호 사고 |
| `GATE.RECON` | P0-07이 찾은 336개 중 67건 물질적 불일치 |
| `GATE.LOOKAHEAD` | v3.47~v3.49 PIT |
| `GATE.MATCH` | **`self_check_v2`에 위임**(§1.11 중복 금지) |

**원본의 `GATE.BRIDGE`·`GATE.FREELUNCH`·`GATE.BASIS`는 넣지 않았다** — IRS의 DCF는
FCF 기반 역산 단일 경로라 해당 사고가 한 건도 없다. 실증 없이 게이트를 늘리면
통과 의례만 늘어난다(테스트로 부재를 고정: `test_unimplemented_upstream_gates_are_absent_on_purpose`).

두 가지를 못박았다:
- **`vacuous` 게이트를 통과로 세지 않는다.** 데이터가 없어 검사를 안 한 게이트는
  통과했지만 아무것도 보증하지 않으며, 그 수를 따로 담는다.
- **`PIT_UNKNOWN`은 실패가 아니다.** 34종목이 전부 그 상태이고, 모른다고 말하는
  것을 실패로 처리하면 이 저장소의 정직성 원칙과 충돌한다.

**calibrated uncertainty**: "판단 불가"라고 말한 것을 credit으로 인정한다(원본의
refusal probe). 다만 **점수를 매기지 않고**, 시스템이 아는 미확인 상태를 메모가
언급하지 않으면 `acknowledged=False`로 **누락 표시**만 한다.

## Tests
`tests/test_evidence_documents.py` 24건 + `tests/test_gates.py` 21건 = 45건 신규.
561 → **606개 전부 통과.**

## Verification

- 34종목 골든재현 8개 지표 완전 동일, fingerprint `fbd34322…` 불변, ledger 무수정

### ⭐ 실제 BSX 분석에 게이트를 걸었더니 — **`GATE.RECON` 실패**

| 게이트 | 결과 |
|---|---|
| GATE.FABRICATION | 통과 (라벨 3건 계산값과 대응) |
| GATE.SCALE / GATE.DIRECTION | 통과 |
| **GATE.RECON** | **실패 — 미해결 출처 충돌 14건** |
| GATE.LOOKAHEAD | 통과 (PIT 미기입) |
| GATE.MATCH | 통과 (self_check_v2 7항목) |

calibrated uncertainty: 명시 표현 0개인데 시스템이 아는 미확인이 3건
(PIT 미검증 · 값 단위 출처 미기록 · Alpha Vantage 약관 미확인) → `acknowledged=False`.

**이것이 BSX 판정을 무효화한다는 뜻이 아니다.** "출처를 대조하지 않은 채 발행됐고,
그 사실을 이제야 탐지할 수 있게 됐다"는 뜻이다. 리포트:
`reports/hard_gates_bsx_2026-08-19.json`

## Remaining Risk

1. **게이트가 어떤 분석 경로에도 자동 배선돼 있지 않다.** 지금은 명시적으로
   호출해야 한다 — 자동 배선하면 34종목 기존 분석이 전부 막힌다(대부분 GATE.RECON
   실패할 것). 어디서 강제할지는 실사용 후 판단한다.
2. `GATE.FABRICATION`은 `labeled_values`에 **분석자가 명시한 라벨만** 검사한다.
   라벨을 안 적으면 아무것도 보증하지 않으며, 그 사실이 `vacuous`로 결과에 남는다.
3. **Evidence Matrix에 실제 데이터가 0건이다.** 구조만 만들었고, 과거 정성조사
   33종목을 소급 입력하지 않았다(소급 작성은 사후합리화 — `falsification_conditions`
   원칙과 동일).
4. 문서 이력이 `filings.recent`로 제한된다(오래된 공시는 별도 파일).

## Commit
`ce0d773`

## Next
P0-14~P0-18은 대부분 기존 모듈과 겹친다 — P0-15 Valuation은 `expectation_gap_engine.py`,
P0-16 Thesis/Memory는 `thesis.py`, P0-17 Historical Replay는 **STOP CONDITION이
이미 공식 발동**(분석 이력 22일), P0-18 Evaluation Lab은 `prediction_ledger.py`·
`experiment_registry.py`가 담당한다. 각각 DUPLICATE 여부를 실제 코드로 확인해
판정할 차례다.

---

# P0-14 / P0-16 — Research Lenses · Refresh Boundary ✅ 완료 (2026-08-19)
# P0-15 / P0-17 / P0-18 — DUPLICATE · DEFER 판정

## P0-14 Research Lenses — ADAPT

**Source**: https://github.com/xbtlin/ai-berkshire (MIT)
**확인한 것**(§1.4): 4대 관점(段永平·버핏·멍거·리루) 렌즈, 快速否决清单(rapid
rejection), 강제 inversion("怎么会死"), PASS/CONDITIONAL/GRAY 어휘, 6차원 별점,
Benford's Law 이상탐지.

**IRS Target**: `engine/research_lenses.py`

### ⚠️ 원본의 4대 렌즈를 그대로 안 가져왔다 — 축은 IRS 것을 쓴다

IRS는 이미 자체 5축을 갖고 있고 그건 상상한 게 아니라 **33종목에 실제로 적용해
축적한 절차**다(CLAUDE.md "정성 심층조사 절차", S등급 7 + A등급 6 + B/C/D 20종목):

> 자본배분 품질 · 회계품질 · 거버넌스 · 희석 추이 · 경쟁환경 최신동향

남의 분류로 갈아타면 **그 33종목 관측이 새 축에 매핑되지 않아 축적이 끊긴다.**
업종 변형(보험사·복합기업)도 실제 사례(ACGL·PGR·SE)를 그대로 옮겼다.

### 가져온 것 2가지

1. **Disqualifier(快速否决清单)** — 감점이 아니라 즉시 탈락. 다만 **근거를 필수**로
   요구한다(BSX 스크리너 거짓탈락 사건: 배제된 종목은 아무도 다시 안 본다).
2. **Mandatory Inversion** — `falsification_conditions`와 **다르다.** 반증조건은
   "이런 실적이 나오면 틀린 것"이라는 미래 트리거, inversion은 "실패 경로"의
   열거다. 전자는 검증 **시점**을, 후자는 검증 **대상**을 정한다.

### ⚠️ 가져오지 않은 것

| 원본 기능 | 판정 | 사유 |
|---|---|---|
| 6차원 별점(★★★★★) | **REJECT** | 정확히 "단일 합성점수" — §31 안티기능 등록부 항목. 중요도가 다른 축이 같은 무게가 되고 공백이 점수 뒤에 숨는다 |
| 4대 관점 가중 종합 | **REJECT** | 계획서 §7.1도 "단순 가중평균하지 않는다"고 명시 |
| Benford's Law | **DEFER** | 실증 필요 0건. P0-03 이후 SEC 1차자료를 직접 쓴다 |
| PASS/CONDITIONAL/GRAY | **DUPLICATE** | `investment_case.py`에 이미 7개 어휘가 있다 |

**핵심 강제**: `effect="not_examined"`가 1급 값이다(조사 안 함 ≠ 별 게 없음) /
방향을 주장하려면 EvidenceMatrix의 주장을 가리켜야 한다 / **점수를 내지 않는다**.

**Tests**: `tests/test_research_lenses.py` 21건.

## P0-16 Refresh Boundary — ADAPT

**Source**: https://github.com/byteseek/Mira (Apache-2.0)
**확인한 것**: Expectation · Event Delta · Decision Log · Postmortem ·
**Refresh Boundary**(`stale_after` / `must_refresh_if`).

**대조 결과**: Mira의 5개 개념 중 4개는 IRS에 **이미 있다** —
`thesis.py`(expectation·decision log), `thesis_monitor.py`(event delta),
`gap_analysis.decompose_drift`(3분할), `prediction_ledger.py`(postmortem).
**빠진 것은 Refresh Boundary 하나뿐**이라 그것만 기존 타입에 얹었다(§1.11).

**근거는 실증이다**: 이 저장소는 **반증조건 트리거 날짜 5건이 전부 지났는데
12일간 아무도 열어보지 않은** 사건을 겪었다(v3.42가 뒤늦게 발견). 논거가 언제부터
재확인이 필요한지 **논거 자신이 말하지 않으면** 그 확인은 누군가 기억하는 것에
의존한다 — 이 프로젝트가 네 번 실패한 방식이다.

**핵심 강제**:
- **`UNBOUNDED`는 `FRESH`가 아니다.** 경계 미설정은 "아직 신선하다"가 아니라
  "언제 낡는지 정한 적이 없다"이다.
- **조건 발동이 기한보다 우선한다.** "아직 기한 전이니 괜찮다"가 정확히 그 실패
  방식이었다.
- 파싱 안 되는 경계는 거부하고, `stale_after <= thesis_date`도 거부한다
  (만들자마자 낡은 논거는 논거가 아니다).
- 발동 표시는 분석자가 명시적으로 한다(정규식은 트리거 날짜와 서술적 날짜를
  구분 못 한다, v3.42).

**Tests**: `tests/test_refresh_boundary.py` 14건. 기존 `test_thesis.py` 20건 무변경 통과
(필드는 opt-in, 비파괴).

## P0-15 Valuation Calculation Engine — **DUPLICATE**

`engine/expectation_gap_engine.py`(1,187줄·35개 함수)가 이미 담당한다 —
`implied_growth_single_stage`/`two_stage`, `structural_discount_rate`,
`erp_from_drs`, `judgment_from_gap`, `confidence_score`, `rar`. 게다가 이 계산
경로는 34종목 골든재현으로 매 커밋마다 고정돼 있다. **PyPortfolioOpt·okama류를
넣으면 검증된 산출물이 흔들린다**(§1.15).

## P0-17 Historical Replay / Validation — **DEFER (STOP CONDITION 기발동)**

**Source**: https://github.com/ishtiaqrahman/capitalbench ·
https://github.com/HKUSTDial/DeepFund

이 저장소는 2026-08-16에 **§66 STOP CONDITION을 공식 발동**했다
(`reports/historical_validation/limitations.md`). 사유는 데이터 품질이 아니라
**시간**이다 — 전체 프로젝트 이력이 22일뿐이고 ledger 34종목 분석일이 그 안에
전부 몰려 있어 12개월 보유수익률 구간이 **존재하지 않는다.**

CapitalBench의 frozen inputs·as-of evaluation·decision timestamp는 IRS에 이미
있다(`experiments/` 사전등록 + SHA-256 코어해시, `predictions/` 34건 동결,
P0-09 스냅샷). **빠진 것은 도구가 아니라 시간이다.** T0를 3주 전으로 재정의하는
유혹은 거부했다 — 그건 결과가 나왔다는 사실 자체를 성과로 포장하는 것이다.

## P0-18 Evaluation Lab — **대부분 DUPLICATE, 이번에 마지막 조각을 채움**

| §17 평가 축 | IRS 현황 |
|---|---|
| Data Accuracy | P0-07 reconciliation (이번 통합) |
| Numerical Accuracy | `self_check_v2` + `GATE.MATCH` |
| Evidence Quality / Citation Fidelity | **P0-12 evidence.py (이번 통합)** |
| Research Quality | P0-14 lenses (이번 통합) |
| Decision Quality / Historical Outcome | `prediction_ledger` + `thesis` (STOP CONDITION) |
| Stability | `gap_analysis`·R-001 감사 |
| Reproducibility | 골든재현 + baseline fingerprint + P0-09 스냅샷 |
| Calibration | **UNCALIBRATED로 명시** — 표본 부족 |
| 치명적 오류 hard gate | **P0-13 gates.py (이번 통합)** |

§17이 요구한 **"단일 점수로 평가하지 않는다"**는 이미 이 저장소의 원칙이다
(§31 안티기능). 축별 집계기를 새로 만들지 않았다 — 각 축이 이미 자기 리포트를
내고 있고, 그걸 하나로 묶는 순간 §17이 금지한 단일 점수에 가까워진다.

## Verification (P0-14/16 공통)

- 전체 **641개 통과**(606 → 641, 신규 35건)
- 34종목 골든재현 8개 지표 완전 동일, fingerprint `fbd34322…` 불변, ledger 무수정

## Remaining Risk

1. **`research_lenses`·`evidence`에 실제 데이터가 0건이다.** 구조만 만들었고
   과거 정성조사 33종목을 **소급 입력하지 않았다** — 소급 작성은 사후합리화다
   (`falsification_conditions` 원칙과 동일).
2. **`thesis/` 디렉터리가 여전히 비어 있다.** refresh boundary를 만들었지만
   적용할 논거가 0건이다. 실사용은 다음 분석부터.
3. 5축이 옳다는 근거는 "이 저장소가 33종목에 써봤다"뿐이고, **투자 성과와의
   관계는 증거 0건**이다(`VALIDATION_STATUS`에 명시).

## Commit
`(아래 커밋)`

## Next
P0 단계 완료. P1(Research DSL · Agent/Skill Orchestration · Screening ·
Portfolio · Intelligence)은 성격이 또 다르다 — 특히 §31 안티기능 등록부가
**멀티에이전트·벡터DB·상관행렬최적화를 이미 "의도적으로 만들지 않는 것"으로
등록**해뒀으므로, P1-02(Agent/Skill)와 P1-04(Portfolio/Risk)는 그 등록과
정면으로 대조해 판정해야 한다.
