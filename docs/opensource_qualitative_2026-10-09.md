# 정성평가용 오픈소스·공개데이터 조사 판정 (2026-10-09)

목적: QSI(정성평가 표준입력) v3.98 기준 남은 빈칸을 메울 수 있는 오픈소스 코드·공개 데이터를 찾고,
IRS에 **병합(코드 가져오기) / 재구현(아이디어만) / 보류 / 기각** 중 무엇이 맞는지 판정한다.
이 문서는 판정만 한다 — 구현·배선은 하지 않았다(판정·비중·ledger 무변경).

판정 기준은 기존 원장(`docs/repo_integration_ledger_2026-08-19.md`)과 같다:
런타임 의존성 0개(stdlib만), §31 안티기능(단일 합성점수·LLM 직접 계산·멀티에이전트 금지),
라이선스, 그리고 **실제로 남은 빈칸을 채우는가**.

## 0. 출발점 — 지금 비어 있는 칸 (19종목 최신 기록, unknown 수)

| 질문 | unknown | 질문 | unknown |
|---|---|---|---|
| acc.voluntary_bad_news | 14/15 | acc.material_one_time_items | 9/15 |
| cmp.share_trend | 11/15 | cap.debt_funded_buyback | 8/15 |
| cap.ma_discipline | 11/15 | acc.guidance_miss_3y / promise_kept | 8/15 |
| cmp.lifecycle_shakeout_or_decline | 10/15 | gov.ceo_succession_policy | 6/19 |
| gov.material_litigation | 9/19 | gov.insider_group_ownership | 5/19 |

추가로 v3.85가 "companyfacts로는 원리적으로 측정 불가"로 확정한 희석 공백 3종목(ERIE·HLNE·RYAN, 다중클래스)이 있다.

## 1. 핵심 발견 3건 (전부 실측으로 확인)

### ① SEC Financial Statement Data Sets에 **주식 클래스별·세그먼트별** 수치가 있다
2026q2 파일(60MB zip, stdlib `zipfile`+`csv`로 읽힘)의 `num.txt`에 `segments` 열이 있고 실제 값이 들어 있다:

- HLNE `CommonStockSharesOutstanding` ClassOfStock=CommonClassA 43,697,484 / CommonClassB 11,836,450
- RYAN Class A 129,603,426 / Class B 134,508,885, `CommonUnitsExchangedForCommonStockShares`(LLC 유닛 교환)까지
- ERIE `WeightedAverageNumberOfDilutedSharesOutstanding` Class A 52,304,384 / Class B 2,542
- HLNE 매출의 `ProductOrService` 분해(관리·자문보수 vs 성과보수)

**v3.85의 "원리적으로 못 가져온다"는 companyfacts에 한해서만 참이었다.** 같은 SEC가 다른 경로로 차원 데이터를 준다.
⚠️ RYAN 같은 Up-C는 Class B가 LLC 유닛과 짝지어진 경제 지분이라, 클래스 수치를 얻어도 "무엇을 합산할지"는 별도 판단이 필요하다(TW는 Class C/D 경제권 0 — CLAUDE.md 기록).
⚠️ `segments` 열은 2024-12 재처리로 추가됐다고 SEC가 안내한다. 이번엔 2026q2 한 분기만 확인했다 — 과거 분기 커버리지는 미확인.

### ② 위임장(DEF 14A)·분기보고서에 **표준 XBRL(ecd 택소노미)** 이 붙어 있고 정규식으로 읽힌다
companyfacts에는 `ecd`가 없다(ADBE 실측: dei·invest·us-gaap·srt·ffd뿐). 그러나 원문 HTML의 inline XBRL은 stdlib로 파싱된다.
ADBE 2026 DEF 14A에서 실제로 뽑힌 값:

| 태그 | 값 |
|---|---|
| `ecd:PeoTotalCompAmt` (5년) | 51.2M · 52.4M · 44.9M · 31.6M · 36.1M |
| `ecd:PeoActuallyPaidCompAmt` | 17.4M · 10.1M · 127.7M · 95.3M · 104.7M |
| `ecd:TotalShareholderRtnAmt` vs `PeerGroupTotalShareholderRtnAmt` | 67.11 vs 187.96 (최근) |
| `ecd:CoSelectedMeasureName` / `MeasureName` | Revenue / Non-GAAP EPS / Relative TSR / Net New Sales |
| `ecd:InsiderTrdPoliciesProcAdoptedFlag` | 있음 |

ADBE 10-Q에는 `ecd:Rule10b51ArrAdoptedFlag`·`Rule10b51ArrTrmntdFlag`(임원 10b5-1 계획 채택·해지, 분기별)가 붙어 있다.
→ 새 축 후보: **보수와 성과의 정렬**(실지급 보수 vs TSR), **경영진이 무엇으로 보상받는가**(매출·EPS면 성장 편향, ROIC면 자본규율),
그리고 `gov.insider_pattern` 보강(10b5-1 계획 채택·해지 시점).
⚠️ 주의: "Compensation Actually Paid"는 주가 변동이 섞인 값이라 보수 크기 판단에 그대로 쓰면 안 된다(규정상 정의).

### ③ SEC 의견서한(UPLOAD/CORRESP)은 이미 우리가 받는 제출목록에 있다
edgartools(MIT)의 `correspondence.py`는 "Re:" 블록에서 참조 양식·파일번호를 뽑아 스레드를 재구성한다.
SEC 직원이 10-K의 비GAAP 지표·수익인식·세그먼트를 지적한 서한은 `acc.material_one_time_items`·`acc.unfaithful_disclosure`의
1차 근거가 될 수 있다. 공개는 검토 종료 20일 이후라 지연이 있다.

## 2. 후보별 판정

| # | 대상 | 라이선스 | 무엇을 채우나 | 판정 | 사유 |
|---|---|---|---|---|---|
| 1 | **SEC Financial Statement Data Sets** (공개 데이터) + `HansjoergW/sec-fincancial-statement-data-set`(secfsdstools) | 데이터: SEC 공개 / 코드: Apache-2.0 | 다중클래스 희석 3종목, 세그먼트 매출(M&A 분리·GEN/ROP형), 수수료 구성 | **데이터 채택 · 코드 REIMPLEMENT** | 라이브러리는 pandas·numpy·pyarrow·pandera 등 8개 의존 — 쓸 필요 없음. 탭 구분 텍스트라 stdlib로 충분(실측) |
| 2 | **ecd inline XBRL** (DEF 14A·10-Q·10-K) — 참조 구현 edgartools `proxy/core.py` | 코드: MIT | 보수-성과 정렬, 보상지표, 내부자거래 정책, 10b5-1 계획 | **REIMPLEMENT** | 태그 목록만 필요. 정규식 20줄로 실제 값 추출 확인 |
| 3 | edgartools `proxy/html_extractor.py` 표 추출(수익자 지분표·보수표·감사수수료) | MIT | `gov.insider_group_ownership`(5/19 unknown) | **ADAPT(방식만)** | 헤더 점수로 표를 고르는 방식이 현행 정규식보다 견고. bs4·lxml 의존이라 코드는 못 가져옴 |
| 4 | edgartools `correspondence.py` | MIT | 의견서한 건수·주제 | **REIMPLEMENT** | 제출목록에 이미 있음. Re: 블록 파싱 규칙만 참고 |
| 5 | `lefterisloukas/edgar-crawler` (10-K/10-Q/8-K 항목 분리) | **GPL-3.0** | 위험요인·소송 절 추출 실패(교차참조형 20-F) | **아이디어만, 코드 복제 금지** | GPL 전염 + click·pandas·bs4·pathos 의존. 목차를 건너뛰고 마지막 항목 머리를 고르는 규칙은 참고 가치 |
| 6 | Hoberg-Phillips TNIC/ETNIC (경쟁사 네트워크) | 인용 요청, 라이선스 문구 없음 | `cmp.share_trend` 비교군(지금 4종목만) | **데이터 기각 · 개념 DEFER** | Compustat **gvkey** 키(CIK 연결표는 WRDS 유료). 개념(10-K Item 1 명사 코사인)은 재구현 가능하나 대형 작업 |
| 7 | Hoberg-Maksimovic 제품 생애주기 데이터 | 인용 요청 | `cmp.lifecycle_shakeout_or_decline` (10/15) | **기각** | gvkey 키 + readme상 **2019년까지**. 쓸 수 있는 시점 데이터가 아님 |
| 8 | CourtListener (Free Law Project) API | 코드 AGPL, 데이터 공개 | `gov.material_litigation` (9/19) | **DEFER** | 무료 토큰 필요, RECAP 기여분만 있어 커버리지 편차 큼, 회사명→당사자 매칭이 모호. 쓰면 "있다"만 단언 가능, "없다"는 못 함 |
| 9 | Stanford SCAC (증권 집단소송) | 개인·비상업 연구 허용 | 소송 | **기각(현재)** | API 없음, 사이트 재구성으로 **업데이트 중단** 안내 |
| 10 | Loughran-McDonald 사전 (Litigious·Uncertainty 목록) | 비상업 연구용 표기(마스터 사전 원문 약관은 미확인) | 8-K 어조 | **DEFER** | 어조는 사실이 아니다. QSI는 판정 없이 사실만 받는 구조라 맞물리는 질문이 없음 |
| 11 | ProsusAI/finBERT | 저장소에 라이선스 파일 확인 안 됨 | 어조 분류 | **기각** | torch·transformers 의존, 감성 점수는 §31 단일점수류 |
| 12 | virattt/ai-hedge-fund | MIT | — | **기각** | `signals/buffett.py`가 56줄짜리 **프롬프트**뿐. 계산 없음. ai-berkshire(P0-14)와 중복 |
| 13 | AI4Finance FinRobot / TauricResearch TradingAgents | Apache-2.0 | — | **기각** | 멀티에이전트 LLM 프레임워크(§31 등록 사유: 병목은 조율이 아니라 입력 근거) |
| 14 | Arelle (XBRL 처리기) | Apache-2.0 | 차원 XBRL | **기각** | 대형 의존. ①·②가 stdlib로 같은 데이터를 준다 |

## 3. 그래도 비는 칸 — 오픈소스로는 안 채워진다

- **acc.voluntary_bad_news (14/15)**: 이걸 하는 오픈소스는 찾지 못했다. 대안은 오픈소스가 아니라 **규칙**이다 —
  정기 실적일 밖에 나온 8-K 2.02(실적 사전 경고), 가이던스 하향 8-K 7.01/8.01. 기존 `guidance_ledger`(v3.96)와
  `sec_events`의 제출목록만으로 만들 수 있다(새 의존 없음).
- **cmp.lifecycle / share_trend**: 무료 경로 없음. 업계 비교군을 직접 만들려면 ⑥의 개념을 재구현해야 한다.
- **cat.cat_exposure**: 자유서술이라 판독 일치 규칙 문제이지 데이터 문제가 아니다(v3.98 기록).

## 4. 권고 순서 (가치 대비 비용)

1. **SEC 재무제표 데이터셋 stdlib 리더** — 다중클래스 희석 3종목(ERIE·HLNE·RYAN)을 되살리고,
   세그먼트 매출로 M&A·사업다각화 분리(GEN/ROP/BRO형 함정)를 자동 대조할 수 있다. 가장 구체적인 공백을 메운다.
2. **ecd 파서** — 보수-성과 정렬·보상지표·10b5-1 계획. 질문 은행에 새 질문 2~3개를 추가해야 하므로
   판독 전 규칙을 먼저 고정할 것(v3.98 원칙).
3. **의견서한 집계** — 회계 축 2문항 보강.
4. **수익자 지분표 추출 개선** — `gov.insider_group_ownership` 5칸.

전부 IMPLEMENTED_NOT_VALIDATED로 시작한다. 이 사실들이 더 나은 판단·성과로 이어진다는 증거는 여전히 0건이다.

## 5. 확인 방법(재현용)

- 코드: 각 저장소를 `git clone --depth 1`로 받아 라이선스·import·핵심 함수를 직접 읽었다(2026-10-09).
- 데이터: `https://www.sec.gov/files/dera/data/financial-statement-data-sets/2026q2.zip`의 `sub.txt`·`num.txt`;
  ADBE DEF 14A `0000796343-26-000043`, 10-Q `0000796343-26-000156`; companyfacts `CIK0000796343`.
- Hoberg readme: `Readme_tnic3.txt`(gvkey, WRDS CIK 매핑 언급), `Readme_LifeCycleDatabase.txt`(1997~2019).
- 미확인으로 남긴 것: FSDS `segments`의 과거 분기 커버리지, LM 마스터 사전 원문 약관, finBERT 라이선스.

## 6. 구현 결과 (2026-10-10 추가 — §4 권고 ①~④ 실행 후)

판정(§2)과 실제 구현을 대조한다. 상세는 CLAUDE.md의 v3.99~v4.02 절.

| §4 권고 | 버전 | 판정대로 갔나 | 실측 결과 |
|---|---|---|---|
| ① SEC 재무제표 데이터셋 stdlib 리더 | v3.99 | REIMPLEMENT 그대로 | ERIE **회복**(EPS×희석주식수가 6년 모두 순이익 재현). **HLNE·RYAN은 회복 못함** — HLNE는 가중평균 주식수가 표준 태그로 공시되지 않고, RYAN은 비지배지분이 6년 내내 커서 거부. §1 ①의 "되살릴 수 있다"는 3종목 중 **1종목**만 참이었다 |
| ② ecd 파서 | v4.00 | REIMPLEMENT 그대로 | 질문 3개, 44칸 채움. 보험사는 보상 지표가 '합산비율'이라 사전 분류상 other |
| ③ 나쁜 소식 자발 공시 | v4.01 | 오픈소스 없음 → 규칙으로 | **새로 채운 칸 0개**(True만 단언하는 규칙, 국내 12종목 True 0건) |
| ④ 의견서한 + 지분표 | v4.02 | REIMPLEMENT/ADAPT | 의견서한 질문 1개, 지분표 4칸 신규, 기존 답 14종목 회귀 일치 |

해결률 70.9% → **75.1%**(답함 335 → 398, 분모 491 → 563 — 질문 4개 추가).

### 판정과 어긋난 점 (정정)
- **§1 ①의 낙관**: "ERIE·HLNE·RYAN 희석을 되살릴 수 있다"고 썼으나 1/3만 성립했다. 데이터가 SEC에 있다는 것과
  그 데이터로 **주주 지분의 순변화를 증명할 수 있다**는 것은 다른 명제였다(Up-C 구조에선 상장 클래스 증가가 유닛 교환인지
  희석인지 구분 불가).
- **§4 ③의 기대**: 가장 빈 칸(14/15)을 채울 것처럼 적었으나 규칙이 True만 단언하도록 설계돼 채운 칸이 0개다. 채우지 못한
  것이 규칙의 결함이 아니라 설계 의도(없음 ≠ 정직 이력 없음)의 결과임을 CLAUDE.md v4.01에 남겼다.
- **GEN 세그먼트 대조 실패**: 이 대조가 필요했던 바로 그 종목(GEN)에서 공시 구성원 이름 체계가 바뀌어 자동 대조가 안 된다.

### 여전히 비는 칸 (남은 한계)
`acc.voluntary_bad_news` 거의 전부, `cmp.share_trend`·`cmp.lifecycle_shakeout_or_decline`(무료 경로 없음),
`cap.ma_discipline`, `gov.material_litigation`, `cat.cat_exposure`(자유서술은 정확 일치 규칙상 채택 불가).
이 정성 정보가 투자 성과와 관련 있다는 증거는 여전히 0건이다 — 전부 `IMPLEMENTED_NOT_VALIDATED`.

### 재현
`python -m scripts.fsds_extract <T...>` → `scripts.dilution_drag` / `scripts.fsds_segments` / `scripts.qsi_ecd` /
`scripts.qsi_bad_news` / `scripts.qsi_disclosure_extras` (각 `--dry-run` 지원). 분기 zip 60~120MB는 `.cache/`(gitignore).
