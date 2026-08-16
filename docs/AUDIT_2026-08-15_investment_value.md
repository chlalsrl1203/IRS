# IRS 투자가치 감사 — "실제 투자판단을 개선하는가?"

감사일: 2026-08-15 · 대상 커밋: `ceb8f30` (v3.50) · 방법: 저장소 직접 실행

이 감사는 코드 품질이 아니라 **투자판단 개선 여부**를 묻는다. 모든 수치는
저장소의 34개 ledger를 실제로 재계산해 얻었다. 확인하지 못한 것은 태그로 표시한다.

---

## 1. Executive Verdict

**NOT READY** — 단, 이유가 지금까지 생각해온 것과 다르다.

이 프로젝트는 계산 정합성·기록 무결성 면에서 이례적으로 잘 통제돼 있다(테스트
425건, 34종목 8개 지표 재현 일치, 단위/도메인 가드). 그러나 **투자판단의
품질을 결정하는 축과 이 시스템이 공들여 통제해 온 축이 서로 어긋나 있다.**

실측 3건이 이를 보여준다:

| 요인 | Gap 변화 중앙값 | 판정 뒤집힘 |
|---|---|---|
| **Realistic Growth 예측오차**(관측 대비) | **8.70%p** | 4/11 |
| **모델 선택**(single↔two stage) | 2.04%p | **11/34 (32%)** |
| **DRS 전체 제거** | 0.23%p | 1/34 (3%) |

판정 밴드는 ±5%p다. **가장 큰 오차원(8.70%p)이 판정 밴드보다 크고, 가장 정교하게
통제된 축(DRS)은 판정을 거의 바꾸지 않는다.**

그리고 이 시스템이 보유한 유일한 강건성 도구(`sensitivity_check`,
`gap_distribution`)는 **둘 다 DRS 축만 검사한다** — 즉 판정을 안 바꾸는 축을
검사하고, 판정을 바꾸는 축은 검사하지 않는다.

---

## 2. Current Repository State (실측)

```
커밋            ceb8f30 (v3.50), 원격과 일치
엔진            16개 모듈 7,638줄
테스트          425건 전부 통과
ledger          회사 34 / ETF 23 / KRX 31
reports         13
experiments     5 (EXP-001 SUPERSEDED, H-001~H-004 전부 BLOCKED)
predictions     0
thesis          0
```

---

## 3. Already Solved (실행으로 확인)

| 항목 | 상태 | 근거 |
|---|---|---|
| 결정적 실행 | **FIXED** | 동일 입력 2회 실행 시 `analyzed_at` 외 전 필드 동일(테스트 고정) |
| ledger 무결성 | **FIXED** | 티커당 1건·파일명 일치·판정 자기일관성 테스트 |
| 과거기록 자동대조 | **FIXED** | v3.47 `save_ledger()` 배선 — 누락이 구조적으로 불가능 |
| 스케일 검증 | **PARTIALLY FIXED** | 자릿수 오류는 탐지, **7배 통화오류는 저수익률 종목에서 미탐지**(문서화된 한계) |
| 도메인 검증 | **FIXED** | EBITDA≤0·CAGR 음수시작·수렴조건 전부 가드 |
| 회귀 테스트 | **FIXED** | 425건, CI 자동 실행 |
| PIT 인프라 | **FIXED** | 필드·검증규칙·SEC 조회 수단 |
| PIT 데이터 | **OPEN** | `PIT_VALID` **0/34** |
| Historical Replay | **NOT IMPLEMENTED** | PIT 데이터 0건이라 원리적으로 불가 |
| 스크리닝 안전장치 | **PARTIALLY FIXED** | BSX 거짓탈락이 문서화된 알려진 실패 |

⚠️ **Implemented ≠ Validated**: 위 FIXED는 전부 **LEVEL 1**(단위/회귀 테스트)이다.
투자 결과로 검증된 항목은 **0건**이다.

---

## 4. Current Investment Bottleneck

### SINGLE MOST IMPORTANT BOTTLENECK

> **판정 밴드(±5%p)가 입력의 측정오차(중앙값 8.70%p)보다 좁다.
> 즉 IRS는 자신이 갖지 못한 정밀도로 3단계 판정을 발행하고 있다.**

이것이 근본 원인이고, 아래 TOP 3은 전부 이것의 발현이다.

### TOP 3

1. **Realistic Growth에 미래정보가 0이다** (§11 확인)
2. **Implied Growth가 단일값으로 식별되지 않는다** (§10 확인)
3. **강건성 검사가 판정을 안 바꾸는 축만 본다** (§16 확인)

### TOP 5 (위 3 + )

4. 모델 선택이 분석자 재량인데 판정의 32%를 결정한다
5. 검증 데이터가 존재하지 않는다(예측 0건·진입가 9/34·PIT 0/34)

### TOP 10 (위 5 + )

6. `cap_applied`가 6종목에서 캡 바인딩인데 상위 필드로는 읽히지 않았다(감사 중 수정)
7. Confidence가 UNCALIBRATED인데 매수리스트 가중치로 쓰인다
8. `build_buylist`가 여전히 `grade in ("S","A")` — Gap→BUY 직결 경로가 남아있다
9. 통화 오류가 저수익률 종목에서 미탐지(문서화된 한계)
10. LYNCH_TYPE_CAPS 상하한값에 근거가 없다(6종목에서 실제 바인딩)

---

## 5. Evidence for Bottleneck

### 5.1 Realistic Growth는 과거 요약이다 (§11)

`realistic_growth_estimate()`의 **입력 전체**:

```
revenue_cagr_3y, revenue_cagr_5y, revenue_cagr_10y, fcf_cagr_5y,
structural_discount_pct, lynch_type
```

계산: 과거 매출 CAGR 가중평균 → FCF CAGR이 더 낮으면 교체 → 구조적 할인 →
Lynch 캡 클램프.

| 요소 | 사용 여부 |
|---|---|
| Revenue Growth (과거) | **USED** |
| FCF Conversion (과거) | **USED** |
| Cyclicality | PARTIALLY (structural_discount 경유) |
| ROIC / Reinvestment | **NOT USED** |
| Margin 궤적 | **NOT USED** |
| Capex / Working Capital | PARTIALLY (opt-in `capex_classification`만) |
| Pricing / Market Share / TAM | **NOT USED** |
| Competition | PARTIALLY (DRS 경유, 성장률에는 미반영) |
| M&A / Dilution | **NOT USED** |
| Guidance / Consensus | **NOT USED** |

**답: 미래 성장률을 예측하지 않는다. 감속 보정된 과거 성장률 요약이다.**

### 5.2 그 요약과 현실의 괴리 (실측, `reports/growth_scorecard_2026-08-13.json`)

관측 11건 / 9종목:

| 구분 | 값 |
|---|---|
| 절대괴리 중앙값 | **8.70%p** |
| 최대 | 28.80%p (TTD) |
| 판정 뒤집힘 | 4/11 |
| 엔진이 관측보다 **높았던** 경우 | **8/10** (0 제외) |

⚠️ **해석 주의**: Realistic Growth는 n≈12년 개념이고 관측치는 분기실적·1개년
가이던스다. 직접적인 "예측오차"가 아니다. 그러나 **가장 가까운 현실 대조점과의
괴리가 판정 밴드보다 크다**는 사실 자체는 유효하다. 표본 11건(종목 9)으로
작다 — [표본 부족].

### 5.3 Implied Growth 식별 불가 (§10, BSX 실측)

BSX Gap +5.87%p, 판정 경계까지 여유 **0.87%p**. 각 가정을 하나씩 흔들면:

| 가정 | 변화 | ΔImplied Growth |
|---|---|---|
| r | ±1%p | **−1.85 / +1.73%p** |
| g_terminal | ±1%p | +0.81 / −0.95%p |
| n | ±2~3년 | ±0.6%p |
| FCF0 | ±10% | ±1.2%p |
| **모델 선택** | two→single | **2.21%p** |

**여유(0.87%p)보다 큰 민감도가 4개다.** Implied Growth는 단일 숫자가 아니라
(g, r, n, g_term) 조합의 다양체 위 한 점이다 — 허위 정밀성.

34종목 전체:

| 흔든 가정 | 판정 뒤집힘 |
|---|---|
| r ±1%p | 6/34 (18%) |
| 모델 선택 교체 | **11/34 (32%)** |

모델 교체 시 Gap 변화 중앙값 2.04%p, 최대 12.85%p — **10종목은 판정 밴드
전체(±5%p)보다 큰 변화**를 겪는다.

### 5.4 DRS는 잘 만들어졌으나 판정에 거의 무관하다 (§16)

구성요소 5개는 **중복이 없다**(모든 쌍 |r|<0.5, 각 제거 시 |ΔDRS| 3.7~5.9점).
구조적으로 건전하다.

그런데 **DRS 전체를 중앙값으로 대체(=정보 제거)하면**:

| 지표 | 값 |
|---|---|
| 판정 변경 | **1/34 (3%)** — RMD만 |
| Gap 변화 중앙값 | **0.23%p** |
| ERP 실제 분포 폭 | 1.49%p (5.72~7.21%) |

원인: `erp_from_drs`가 DRS 0~100을 ERP 5~8%로만 사상하고, 실제 DRS 범위
(24.0~73.6)는 그 중 1.49%p만 쓴다.

**DRS는 성장 예측오차보다 약 38배(8.70÷0.23) 판정 영향이 작다.**

### 5.5 강건성 도구가 잘못된 축을 본다

| 도구 | 검사 축 | 그 축의 판정 영향 |
|---|---|---|
| `sensitivity_check`(v3.19) | DRS on/off | 3% |
| `gap_distribution`(v3.44) | DRS 주관입력 섭동 | **0%** (34/34 P=100%/0%) |
| **미검사** | **모델 선택** | **32%** |
| **미검사** | **성장 추정** | **판정 밴드 초과** |

v3.44는 "취약 판정 0건"을 발견하고 "취약성은 성장률 축에 있다"고 정확히
결론냈으나, **그 결론에 따른 도구는 만들어지지 않았다.**

---

## 6. Incremental Information Test (§8·§9)

### H0: Expectation Gap은 fundamental+valuation 대비 증분정보가 없다

**H0를 기각할 증거가 없다.** 다만 완전히 지지되지도 않는다.

측정된 것:

| 지표 | 값 | 해석 |
|---|---|---|
| corr(Gap, FCF수익률) | **+0.801** | R²=0.64 — Gap 분산의 64%가 단순 FCF수익률로 설명됨 |
| corr(Implied Growth, FCF수익률) | −0.913 | IG는 사실상 FCF수익률의 단조변환 |
| Gap 분산 기여: RG | 54.0% | |
| Gap 분산 기여: −IG | 46.0% | |

**구조적 결론**: Gap = (과거성장 요약) − (밸류에이션의 성장률 환산). 두 항 모두
표준적 입력이다. Gap의 고유 기여는 **"가격을 성장률 단위로 환산해 비교 가능하게
만든 것"**이며, 이는 Mauboussin 계열 expectations investing의 표준 프레이밍이다.

⚠️ **증분정보 여부는 측정 불가**: 미래 수익률 관측이 **0건**이라 H0/H1 검정
자체가 불가능하다. [DATA MISSING]

---

## 7~9. Screening / False Positive / False Negative

**[DATA MISSING — 원리적으로 산출 불가]**

False positive/negative를 정의하려면 "실제로 좋은 투자였는가"가 필요한데:

- 기록된 투자판단: **0건**
- 진입가 보유: **9/34**
- 최장 보유기간: 분석일 2026-07-25~08-13 → 최대 3주

문서화된 실패 사례는 1건뿐이다:
- **BSX 거짓탈락**(FALSE NEGATIVE) — `screen()`이 `competition_intensity`를
  상수 12.0으로 가정해 실제값 5.4인 종목을 탈락시켰다. 정식분석은 "저평가
  가능성"으로 통과. `KNOWN_SCREENER_FALSE_REJECTIONS`로 테스트 고정됨.

이 1건은 §14가 요구한 유형별 분석을 하기엔 부족하다. [표본 부족]

---

## 10~11. Implied / Realistic Growth Audit

§5.1·§5.3 참조. 요약:

| | Implied Growth | Realistic Growth |
|---|---|---|
| 수학적 정확성 | 정확(Gordon/2단계 DCF) | 정확(가중평균+클램프) |
| 식별 가능성 | **불가** — 4개 가정과 상호대체 | 해당 없음 |
| 미래정보 함량 | 시장가격에 내재된 기대(정의상 forward) | **0** |
| 판정 영향 | 큼 | 큼 |
| 검증 수준 | LEVEL 1 | LEVEL 1 |

---

## 12. Forecasting Comparison

**[NOT TESTED]** — 대안(ROIC×재투자, 가이던스, 컨센서스, 시나리오)과의 OOS
비교는 미래 fundamental 관측이 필요하다. 현재 0건.

단, **관측 11건 중 8/10이 엔진 과대**라는 방향성은 기록해둔다(표본 부족).

---

## 13. Expectation Gap Audit → §6 참조

## 14~15. Decision Value / DRS·RAR → §5.4 참조

RAR 추가 확인: `rar_from_decimal_return(ER, DRS) = ER/DRS`는 **ER<0에서 방향이
반전**된다(v3.26에서 CDNS 기계검증: DRS 20→80일 때 RAR −0.9523→−0.3551).
경고는 배선됐으나 공식은 유지 중 — 과거값 비교가능성 때문. [HEURISTIC]

---

## 16. Threshold Audit (§17)

| threshold | 값 | 근거 | 판정 |
|---|---|---|---|
| `JUDGMENT_BAND` | ±5%p | 33종목 관측 기반 시작점 | **HEURISTIC** |
| `LYNCH_TYPE_CAPS` | 6종 | **근거 없음**(v3.24 자체 문서화) | **HEURISTIC** — 6종목 실제 바인딩 |
| `erp_from_drs` | 5~8% 선형 | 실증근거 없음 | **HEURISTIC** |
| DRS 버킷(변동성/레버리지/경기민감) | 다수 | 코드 주석에 경제적 논리만 | **HEURISTIC** |
| FCF수익률 밴드 | 0.5~25% | 34종목 실측 1.50~17.95% 기반 | 관측 기반 |

`VALIDATION_STATUS`가 이미 앞의 셋을 HEURISTIC/UNCALIBRATED로 표기하고 있다 —
**정직성은 확보돼 있고, 근거가 없다는 사실 자체가 문제다.**

---

## 17. Industry Robustness

**[NOT TESTED]** — 섹터별 성과 비교에 필요한 결과 데이터 없음.

기록된 구조적 mismatch(코드/문서로 확인된 것만):

| 유형 | 확인된 문제 |
|---|---|
| 반도체·AI장비 | trailing CAGR이 수요 인플렉션 과소추정(KEYS 1.47% vs 가이던스 28%, KLAC 10.33% vs 20%+) |
| M&A 롤업 | CAGR 구간 양끝에 인수가 걸리면 왜곡이 통계적으로 상쇄돼 안 보임(GEN) |
| 보험 | FCF-DCF 부적합 — `is_insurer` 병기로 우회 |
| 경기민감·여행 | 조회창 밖 폭락기 누락 시 성장 과대·DRS 과소(BKNG) |
| 적자→흑자 전환 | 5y CAGR 프레임 성립 안 함(PODD/ONON/MU 세 가지 다른 함정) |

---

## 18. Data / Accounting Risk

| 위험 | 발생확률 | 영향 | 탐지가능성 | 상태 |
|---|---|---|---|---|
| 시총 자릿수 오류 | 낮음 | 치명적 | **탐지됨**(v3.46) | FIXED |
| 통화 혼재(비USD) | 중간 | 치명적 | **저수익률 종목 미탐지** | PARTIALLY |
| SBC 미차감 | 높음 | 큼 | 병기로 노출 | PARTIALLY (opt-in) |
| 재작성(restatement) | 중간 | 중간 | **검증 수단 없음** | OPEN |
| filing timing | 낮음 | 큼 | **v3.49 감사 위반 0건** | 확인됨 |
| 2차 출처 오류 | 높음 | 큼 | TYL SBC 3배 오류 실사례 | OPEN |

---

## 19~20. PIT / Replay Status

§19의 4단 구분을 엄격히 적용한다:

| 단계 | 상태 |
|---|---|
| PIT Infrastructure | **있음** (필드·규칙·SEC 조회) |
| PIT Data | **0/34** |
| Historical Replay | **NOT IMPLEMENTED** |
| Validated Historical Performance | **없음** |

⚠️ **"PIT validated"라고 부를 수 있는 것이 하나도 없다.** v3.49 감사는 34종목에서
미래정보 사용 흔적 0건을 확인했으나, 이는 "그 시점에 공시돼 있었는가"만 답하고
재작성 여부는 답하지 못한다.

---

## 21. External Research

**[NOT PERFORMED]** — §22가 요구한 1차 학술문헌 조사를 이번 감사에서 수행하지
않았다. 이유: §23이 "연구가 결정을 바꾸지 않으면 구현하지 않는다"고 요구하는데,
현재 병목(측정오차 > 판정밴드)은 **외부 연구 없이도 저장소 내부 데이터만으로
확정**됐고, 그 해결책도 새 방법론이 아니라 기존 계산의 재표현이다.

향후 필요 시점: Realistic Growth를 forward-looking 모델로 교체할 때
(ROIC×재투자, forecast calibration 문헌이 그때 필요).

---

## 22. Root Cause Analysis

```
IRS가 3단계 판정을 발행한다 (저평가 / 적정가 / 과대평가, ±5%p)
        ↑
판정은 Gap 한 점에서 나온다
        ↑
Gap = RealisticGrowth − ImpliedGrowth
        ↑            ↑
   과거 요약       (g,r,n,g_term) 다양체 위 한 점
   오차 8.70%p     모델선택만으로 2.04%p(최대 12.85%p) 이동
        ↓
두 항의 불확실성 합 > 판정 밴드 ±5%p
        ↓
판정의 32%가 분석자 재량(모델선택) 하나로 뒤집힌다
        ↓
그런데 강건성 도구는 판정을 3%만 바꾸는 축(DRS)만 검사한다
        ↓
결과: 시스템이 자신의 불확실성을 스스로 볼 수 없다
```

---

## 23. Candidate Solutions

| # | 안 | 투자영향 | 근거강도 | 구현비용 | 검증가능성 |
|---|---|---|---|---|---|
| A | **가정집합 Gap 범위** — 점 대신 범위 발행, 강건성 재정의 | 높음 | 높음(실측) | 낮음 | 즉시 |
| B | 모델선택 규칙화(재량 제거) | 중간 | 중간 | 낮음 | 12개월 후 |
| C | Realistic Growth를 forward 모델로 교체 | 높음 | 낮음(미검증) | 높음 | 12개월 후 |
| D | DRS→ERP 매핑 확대(영향력 증대) | 낮음 | **없음** | 낮음 | 불가 |
| E | 판정 밴드 확대(±5→±10%p) | 중간 | 낮음 | 낮음 | 불가 |
| F | 예측·논거 기록 시작(검증 데이터 축적) | 장기 높음 | 높음 | 낮음 | 12개월 후 |

---

## 24. Rejected Solutions

**D. DRS→ERP 매핑 폭 확대**
- 매력적으로 보이는 이유: DRS가 판정에 3%만 기여하니 영향력을 키우면 리스크가
  반영될 것 같다.
- **기각 사유**: 매핑값에 실증근거가 없다(`VALIDATION_STATUS`가 HEURISTIC 명시).
  근거 없는 값을 근거 없는 다른 값으로 바꾸는 것은 개선이 아니다. 더 나쁜 것은
  이것이 **결과를 보고 파라미터를 조정하는 행위**(§21 금지)라는 점이다.
- 대안: DRS를 판정이 아니라 **포지션 사이징**에 쓴다(별도 검증 필요).

**E. 판정 밴드 확대**
- 매력적으로 보이는 이유: 측정오차가 8.70%p니 밴드를 넓히면 오분류가 준다.
- **기각 사유**: ±5%p는 33종목 분포에서 나온 값이고, 이를 결과를 보고 바꾸면
  축적된 34종목 판정 전체가 재해석돼 과거 비교가 불가능해진다. 또 밴드를
  넓히는 것은 불확실성을 **숨기는** 방향이다 — 드러내는 방향(A)이 맞다.

**C. Realistic Growth 즉시 교체**
- 매력적으로 보이는 이유: 병목의 가장 큰 항이다.
- **DEFER 사유**: 어떤 forward 모델이 더 나은지 검증할 데이터가 없다(§12
  비교 자체가 불가). 지금 교체하면 **미검증 방법론을 미검증 방법론으로 교체**하는
  것이고, 되돌릴 근거도 없다. A를 먼저 해서 "어느 가정이 실제로 판정을
  좌우하는가"를 드러낸 뒤, 그 축에 집중해 교체하는 것이 순서다.

**F. 예측 기록 시작**
- **DEFER 아님 — 병행 권고**: 비용이 거의 없고 12개월 뒤 모든 검증의 전제다.
  다만 "단 하나의 다음 작업"으로는 A보다 후순위다. F는 **미래**의 판단을
  개선하고, A는 **지금** 34종목의 판단을 개선한다.

---

## 25. Final Scores (0~10, 근거 필수)

| 축 | 점수 | 근거 |
|---|---|---|
| Economic Validity | 6 | reverse DCF 프레이밍은 표준적·정합적. 단 성장측이 backward-only |
| Forecast Quality | **2** | 미래정보 0. 관측 대조 괴리 중앙값 8.70%p |
| Expectation Measurement | 5 | 시장기대 환산은 정확하나 단일값 식별 불가 |
| Incremental Information | **[측정불가]** | 결과 데이터 0건 |
| Decision Quality | **3** | 판정의 32%가 재량적 모델선택으로 뒤집힘 |
| False Positive Control | **[측정불가]** | 결과 데이터 0건 |
| False Negative Control | **[측정불가]** | 확인 사례 1건(BSX)뿐 |
| Data Integrity | 8 | 자릿수·도메인·부호 가드 다층. 통화·재작성은 미해결 |
| PIT Reliability | **2** | 인프라 있음, 데이터 0/34 |
| Industry Robustness | 3 | 5개 유형의 구조적 mismatch가 문서화만 됨 |
| Out-of-Sample Validation | **0** | 수행된 적 없음 |
| Reproducibility | **9** | 34종목 8지표 재현 일치, ledger+테스트 425건 |
| Interpretability | 8 | 모든 중간값이 ledger에 남고 한계가 명시됨 |

**엔진별**

| 엔진 | 점수 | 근거 |
|---|---|---|
| Implied Growth | 5 | 수학적으로 정확하나 4개 가정과 상호대체 — 단일값 허위정밀 |
| Realistic Growth | **2** | 과거 요약. 미래 예측 요소 0 |
| Expectation Gap | 4 | 프레이밍은 유효, 정밀도가 판정 밴드에 못 미침 |
| DRS | 6 | 구성 건전(중복 없음), 판정 영향 3%로 사실상 미사용 |
| RAR | **3** | ER<0에서 방향 반전(기계검증 확인), 경고만 배선 |
| Decision Engine | 7 | Signal/Decision 분리·6관문 강제는 구조적으로 우수. 단 미사용(thesis 0건) |

---

## 26. Final Verdict

**NOT READY**

**WHY**: 시스템이 발행하는 3단계 판정의 정밀도가 입력의 측정오차보다 높다고
암묵적으로 주장하는데, 실측은 그 반대다(오차 8.70%p > 밴드 5%p). 또한 판정의
32%가 검증되지 않은 분석자 재량(모델선택) 하나로 뒤집힌다.

**EVIDENCE**: §5.1~5.5의 실측 전부. 특히 DRS 제거 실험(1/34 변경) vs 모델교체
실험(11/34 변경)의 대비.

**LIMITATION**: 이 감사도 **투자 성과로는 아무것도 검증하지 못했다**. 결과
데이터가 0건이므로 "IRS가 더 나은 투자판단을 하게 하는가"에는 여전히
[NO EVIDENCE]다. 이 감사가 확정한 것은 **내부 일관성 축의 오배치**이지
외부 타당성이 아니다.

**WHAT MUST CHANGE**: 판정을 점이 아니라 **가정집합 위의 범위**로 발행하고,
강건성 검사를 실제로 판정을 바꾸는 축(모델선택·성장가정)으로 옮긴다.

---

## 27. SINGLE NEXT ACTION

> ### 가정집합 Gap 범위(Assumption-Set Gap Range) 도입
> — 판정을 점에서 범위로 바꾸고, 강건성 검사를 실제로 판정을 바꾸는 축으로 옮긴다

**WHY**: 지금 IRS의 가장 큰 결함은 틀린 계산이 아니라 **자신의 불확실성을 볼 수
없다**는 것이다. 34종목 중 11종목의 판정이 모델선택 하나로 뒤집히는데, 시스템은
그 사실을 어디에도 표시하지 않는다. 반면 표시하고 있는 강건성 지표
(`sensitivity_check`)는 판정을 3%만 바꾸는 축을 본다.

**ROOT CAUSE**: §22의 인과사슬. 두 불확실성원(성장 요약오차, 다양체 위 한 점
선택)의 합이 판정 밴드를 초과한다.

**EVIDENCE**:
- 모델교체로 11/34(32%) 판정 뒤집힘, Gap 변화 최대 12.85%p
- r±1%p로 6/34(18%) 뒤집힘
- 34종목 중 7종목은 판정 여유가 r 민감도(≈1.8%p)보다 작음
- 기존 도구는 이 축을 전혀 검사하지 않음(DRS만 검사, 3% 영향)

**EXPECTED INVESTMENT IMPACT**: 얇은 마진의 "저평가" 라벨이 강건한 것과
구분된다 → **false positive 감소가 주 효과**. 매수리스트가 등급이 아니라
강건성으로 1차 필터링될 수 있게 된다. 반대로 강건하게 저평가인 종목은 확신을
갖고 비중을 실을 수 있다.

**IMPLEMENTATION** (최소 변경, 새 방법론 0):
1. `engine/gap_analysis.py`에 `gap_range_over_assumptions(ledger)` 추가 —
   기존 `implied_growth_*`를 **재사용**해 다음 격자에서 Gap을 재계산:
   - 모델: single_stage / two_stage (둘 다)
   - r: ledger r ± 1%p
   - g_terminal: ± 1%p
   - n: ± 2년
2. 산출: `gap_min`, `gap_max`, `judgment_set`(격자에서 나온 판정들의 집합),
   `robust`(집합 크기 1이면 True), `flip_drivers`(어느 축이 뒤집었는가)
3. `investment_case.build_case()`가 이 결과를 병기(판정은 **변경하지 않는다** —
   병기 원칙)
4. 격자 경계값은 **하드코딩하지 않고 상수로 노출**하되, 근거를 "관측 기반
   시작점"으로 명시(HEURISTIC 태그)

**TEST**:
- 34종목 전건에서 공식 `judgment`가 격자 결과에 **포함**되는지(자기일관성)
- 격자 폭 0이면 `gap_min == gap_max == 공식 Gap`
- BSX가 `robust=False`로 나오는지(여유 0.87%p < 모델괴리 2.21%p — 실측 확정)
- 34종목 8개 지표 무변동(병기 경로이므로)

**OUT-OF-SAMPLE VALIDATION**: 즉시는 불가. 12개월 뒤 H-001 실행 시
`robust=True` 부분집합과 전체집합의 성과를 비교한다 — **이것 자체가 H-001의
사전등록된 하위가설이 될 수 있으므로, 지금 실험 등록부에 함께 박아둔다**
(결과를 본 뒤 정의를 만들면 튜닝이 된다).

**SUCCESS CRITERION**: 34종목 중 `robust=False`가 8~15종목 범위에서 나오고
(실측 예상 11), 그 목록이 `sensitivity_check`가 잡아낸 것과 **다르다는 것**이
확인된다. 즉 기존 도구가 놓치던 것을 실제로 잡는다.

**FAILURE CRITERION**: `robust=False`가 0종목이거나 30종목 이상이면 격자가
잘못 설계된 것이다(전자는 폭이 너무 좁고, 후자는 너무 넓어 판정 자체가
무의미해진다). 그 경우 격자 폭을 결과에 맞춰 조정하지 말고 **왜 그런지
먼저 규명**한다(§21 금지사항).
