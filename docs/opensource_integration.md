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
`3061497`

## Next
**P0-02 Provider Interface** — 등록부를 실제 수집 경로에 연결하는 추상 계층.
여기서 "미확인 출처를 어디서 차단할 것인가"를 결정한다.
