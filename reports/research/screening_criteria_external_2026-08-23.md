# 스크리닝·밸류에이션 기준 외부검증 — 학술문헌·오픈소스 대조

작성일: 2026-08-23 · 깊이등급 **D2**(다수 기준 병렬조사·개별 항목은 얕음, 단
implied-growth 아키텍처 항목은 D3 수준) · 사용자 요청: "저명한 학술지와 논문,
기업분석 스크리닝 오픈소스 등에서 기준을 자료조사하고 분석 후 다시 반영."

## 1. Research Question

`engine/screener.py`(MIN_REALISTIC_GROWTH=8%, MAX_IMPLIED_GROWTH=5.5%, tier
경계 0%/4.11%)와 `engine/expectation_gap_engine.py`(`default_terminal_growth`
ceiling 4.5%)의 수치·설계가 **저명 학술문헌과 오픈소스 스크리닝 프로젝트 대비
어디까지 근거가 있는가?** 근거가 없는 항목을 발견했을 때, 이 프로젝트의 반복
원칙("근거 없이 유지하던 걸 근거 없는 다른 숫자로 바꾸는 것은 개선이 아니다" —
LYNCH_TYPE_CAPS·P/B임계값·ERP매핑·초대형주가산 전부 이 원칙으로 무변경 유지)을
그대로 적용한다: **숫자를 바꾸는 것이 아니라 근거 수준을 정확히 라벨링하는 것이
기본 결정**이며, 예외는 (a) 실제 영향범위가 0건으로 검증 가능하고 (b) 인용 가능한
1차 출처가 구체적 수치를 제시하는 경우로 제한한다(이번 조사에서 `default_
terminal_growth`가 이 조건에 해당하는지 §6에서 검증).

## 2. Current IRS Baseline

| 상수 | 값 | 위치 | 기존 근거 |
|---|---|---|---|
| `MIN_REALISTIC_GROWTH` | 8.0% | `screener.py` | 트래커 74건 전수, 저평가군 13/13이 이 위 |
| `MAX_IMPLIED_GROWTH` | 5.5% | `screener.py` | 과대평가군 18/18이 이 위(전부 탈락) |
| `STRUCTURAL_DISCOUNT_MEDIAN` | 10.1% | `screener.py` | ledger 12건 실측 중앙값 |
| tier 경계 | IG≤0.0=S, ≤4.11%=A, else B | `screener.py` | 저평가군 내재성장률 중앙값 |
| `default_terminal_growth` ceiling | 4.5% (floor 2.0%) | `expectation_gap_engine.py` | 근거 문서화 없음(단순 극단값 방지) |
| 실제 계산값(rf−1%) | 3.47~3.69% (34/34) | ledger | rf=4.47%에서 파생 |

전부 **내부 34~74종목 corpus에서 도출된 경험적 값**이며, 도입 시점에 외부
학술문헌이나 업계 표준과 대조된 적이 없다(`grep -rn "Damodaran\|Greenblatt\|
Piotroski\|Gebhardt\|Rappaport" engine/` → 이번 조사 이전 결과 0건).

## 3. Sources Surveyed

**학술/1차 문헌(citation count·저널 명시)**:
1. **Gebhardt, Lee & Swaminathan (2001), "Toward an Implied Cost of Capital,"
   *Journal of Accounting Research* 39, 135-176.** [피어리뷰, 2000+ 인용] — DCF를
   역산해 시장이 가격에 반영한 값을 추출하는 방법론의 학술적 원조. IRS는 이걸
   "할인율"이 아니라 "성장률"을 역산 대상으로 바꿔 쓴다(수학적으로 동형).
2. **Chan, Karceski & Lakonishok (2003), *Journal of Finance* 58(2), 643-684.**
   [이미 v3.52에서 structural_discount_rate 근거로 확보·인용됨 - 이번엔 growth
   floor 설계에 대한 반대증거로 재사용]
3. **Piotroski (2000), "Value Investing: The Use of Historical Financial
   Statement Information to Separate Winners from Losers," *Journal of
   Accounting Research* 38(Supplement).** [피어리뷰] — 9개 이진 신호 기반 재무
   건전성 스코어. DRS의 "위험점수를 합산해 할인율에 반영" 설계와 구조적으로
   유사하나 이진/검증된 신호 대신 연속 휴리스틱을 쓴다는 차이가 있음.
4. **Aswath Damodaran (NYU Stern)** — terminal growth를 명목GDP성장률에
   앵커링해야 한다는 지침(`growthandtermvalue.pdf`, Stern 강의자료·다수 재인용).
   1차 슬라이드 원문 직접 열람은 실패(PDF 텍스트 추출 불가, WebSearch 요약만
   확보 — 아래 §9에서 이 한계를 명시).

**실무/준학술(책·CFA 커리큘럼·SSRN)**:
5. Rappaport & Mauboussin, *Expectations Investing* (Columbia Business School
   Publishing, 2021 개정판) — reverse-DCF/implied-growth 프레임워크의 실무
   canonical text.
6. CFA Institute 커리큘럼(주식가치평가 리딩)이 implied-growth 분석을 명시적으로
   다룬다는 사실은 WebSearch 요약으로만 확인(1차 커리큘럼 문서 직접 대조 안 함 —
   §9 한계).
7. Greenblatt, *The Little Book That Beats the Market* (Magic Formula) — 원 저자
   백테스트(1988-2004, 연 ~30% vs S&P500 ~12%) + 독립 재현 다수(유럽·핀란드
   등에서 방향 일치, 크기는 축소).

**오픈소스 프로젝트(GitHub, 직접 열람)**:
8. `hjones20/fundamental-analysis` — DCF 스크리너, README에 **수치 임계값이
   전혀 없음**(사용자가 지정하는 파라미터일 뿐).
9. `JerBouma/FinanceToolkit`, `terzim/StockScreener`, `asafravid/sss` 등 —
   FCF수익률·PER 등 지표 계산 함수는 제공하나 "이 값 이상이면 매수"류의 canonical
   컷오프는 어디에도 하드코딩돼 있지 않음(WebSearch 요약 수준 확인, 소스코드
   전문 대조는 안 함).

## 4. Finding 1 — Implied-growth 비교 아키텍처 자체는 강하게 지지된다 (ECONOMICALLY_SUPPORTED)

IRS의 핵심 설계(`implied_growth_from_fcf_yield` + `realistic_growth_estimate`를
비교해 Gap을 낸다)는 **독립적인 4갈래 출처가 수렴한다**:
- 피어리뷰 학술 원조(Gebhardt/Lee/Swaminathan 2001, JAR) — DCF 역산으로 시장
  내재값을 추출하는 방법론 자체가 회계학 최상위 저널에서 확립됨.
- 실무 canonical text(Rappaport & Mauboussin)가 정확히 같은 구조(가격→역산→
  내재성장률 도출→독립적 성장추정과 비교)를 "Expectations Investing"이라는
  이름으로 프레임화.
- Damodaran(NYU Stern)이 "모든 시장가격은 이미 하나의 DCF"라며 같은 관점을
  수십 년간 반복 교육.
- CFA 커리큘럼에 명시(단, 1차 문서 미대조 — §9).

**이건 IRS가 34종목에서 처음 발견한 우연이 아니라 회계·재무 학계와 실무 양쪽에서
독립적으로 도달한 표준적 방법론이라는 뜻이다.** 다만 이 지지는 **아키텍처
(implied growth를 비교축으로 쓴다는 것) 자체에 대한 것이지, IRS가 고른 특정
숫자(5.5%, 8%, ±5%p 밴드)를 정당화하지 않는다** — 이 구분을 흐리면 "권위 있는
문헌이 우리 임계값도 확인해줬다"는 거짓 주장이 된다(v3.52가 structural_
discount_rate에서 이미 지킨 것과 동일한 경계: trend_delta 메커니즘은 지지됐지만
deceleration_sensitivity=0.5 계수는 그대로 미검증으로 남겼다).

## 5. Finding 2 — 절대 성장 하한선(8%)은 학계에 정면 반례가 있다

두 출처가 **"성장 예측 자체에 의존하지 마라"**는 방향으로 IRS의 8% 하한과
반대를 가리킨다:
- **Greenblatt의 Magic Formula는 성장 입력이 아예 없다.** 이익수익률(EY)과
  ROIC만으로 스크리닝하며, 이는 저자가 명시적으로 "성장 예측은 신뢰할 수 없다"고
  본 설계 선택이다.
- **Chan/Karceski/Lakonishok(2003, JF)** — "장기 이익성장에 우연 이상의
  지속성이 없다"(이미 v3.52가 structural_discount_rate 근거로 인용한 동일
  문헌). 이 발견은 논리적으로 **"과거 CAGR로 미래 성장을 8% 이상 요구하는
  하드 필터"**와 긴장 관계에 있다 — RQ-001(2026-08-16)가 이미 독립적으로 확인한
  것과 같은 결론이다("Realistic Growth는 예측이 아니라 축소(shrinkage)로 작동한다").

**이것이 "8% 하한을 없애라"는 근거는 아니다.** IRS의 8% 필터는 예측 정확도를
주장하지 않고 34~74종목의 관측된 판정과의 상관을 근거로 쓰는 1차 스크린일
뿐이며(screener.py docstring이 이미 "판별력은 시장 대비가 아니라 엔진 자기
라벨 대비"라고 스스로 경고함), 그 용도에서는 CKL(2003)의 반박이 직접 적용되지
않는다. 그러나 **"8%라는 절대 하한선 자체에 대한 외부 학술 근거는 없다"**는
사실은 정확히 기록해야 한다 — 지금까지 이 사실이 명시된 적이 없었다.

## 6. Finding 3 — `default_terminal_growth` ceiling(4.5%)이 Damodaran 지침보다 100bp 높다 (실제 영향 0건 확인)

Damodaran의 반복 지침: 성숙기업의 영구성장률은 **장기 명목GDP성장률에
앵커링**해야 하며, 통상 인용되는 범위는 **2.0~3.5%**(무위험금리를 초과해선 안
된다는 더 엄격한 버전도 있음). IRS의 `default_terminal_growth(rf, spread_
below_rf=0.01, floor=0.02, ceiling=0.045)`는 ceiling이 **4.5%**로, 이 통상
범위보다 100bp(1%p) 높다.

**영향범위를 직접 측정했다** (`ledger/*.json` 34건 전수, `discount_rate.g_terminal`):

```
전 종목 rf=4.47% 고정 → g_terminal = rf - 1% = 3.47~3.69% (34/34)
ceiling(4.5%)에 도달한 종목: 0/34
```

즉 **ceiling은 지금까지 단 한 번도 바인딩된 적이 없다** — floor(2.0%)도
마찬가지다. 실제 계산값(3.47~3.69%)은 Damodaran의 통상 범위(2.0~3.5%) 상단에
거의 붙어 있지만 벗어나지는 않는다(3.69% > 3.5%인 BSX 1건만 근소 초과 — 다만
"통상 범위"가 문헌마다 3.5%든 4%든 조금씩 다르게 인용되는 연성 기준이라 이
근소한 초과 자체를 결함으로 확정하기는 어렵다).

**결정: ceiling 상수는 바꾸지 않는다.** 이유는 v3.52가 초대형주 가산(+3%p/
+1%p)에 적용한 것과 동일한 원칙이다 — 지금 4.5%→3.5%로 좁히면 "근거 없이
유지하던 숫자를 다른 숫자로 바꾸는" 것과 형식적으로 다르지 않다(이번엔 인용
가능한 출처가 있다는 점이 다르지만, 그 출처 자체가 1차 원문 직접 대조 실패로
근거 수준이 제한적이다 - §9). 대신 (a) VALIDATION_STATUS에 이 발견을 정확히
기록하고 (b) `docs/research_decision_record.md`에 재개조건을 명시한다: **향후
어느 분석에서든 rf 상승 등으로 실제 g_terminal이 4.0%를 넘는 사례가 나오면
즉시 재검토할 것.**

## 7. Finding 4 — 오픈소스 생태계에도 "표준 임계값"은 존재하지 않는다

조사한 오픈소스 스크리닝 프로젝트(hjones20/fundamental-analysis, FinanceToolkit,
StockScreener, sss 등) 전부 성장률·FCF수익률·PER의 **구체적 컷오프 값을
하드코딩하지 않는다** — 지표 계산 함수만 제공하고 임계값은 사용자 파라미터로
남긴다. Magic Formula·O'Shaughnessy Growth 스크린도 "성장률이 0보다 크다" 정도의
느슨한 최소조건만 쓰거나(O'Shaughnessy Growth Market Leaders: EPS성장 > 0)
아예 성장 입력이 없다(Magic Formula).

**이건 부정적으로만 읽을 발견이 아니다.** IRS가 "8%/5.5%라는 정밀한 숫자를 34~74
종목 corpus에서 도출하고 그 출처를 명시한다"는 방식 자체가, 조사한 오픈소스
생태계 어느 프로젝트보다 임계값의 출처를 더 투명하게 기록하고 있다는 뜻이기도
하다 — 다만 "34~74종목 자체 corpus"가 "저명 학술문헌"과 같은 근거 수준이
아니라는 것은 별개로 명확히 해야 한다.

## 8. Finding 5 — PEG 경계값과의 느슨한 구조적 유사성 (약한 신호, 검증 아님)

GARP 실무자 관행(GeminIQ 등 요약 기준)은 PEG < 1.0을 "매력적", 1.0~1.5를
"합리적"로 본다. IRS의 통과 경계(RG=8%, IG=5.5%)를 억지로 PEG류 비율로
환산하면 IG/RG = 0.6875로 "매력적" 구간(<1.0) 안에 들어온다. **이건 검증이
아니라 방향성 신호일 뿐이다** — PEG는 P/E와 EPS성장률의 비율이고 IRS는
FCF수익률과 DCF역산 성장률을 쓰므로 분자·분모의 정의 자체가 다르다(같은
숫자가 우연히 같은 구간에 들어온 것을 "PEG 이론이 IRS를 검증했다"고 읽으면
v3.52가 경계한 "표면 유사성을 구조적 유사성으로 오독"(Fama-French 38%
평균회귀율을 성장축소계수로 잘못 앵커링하려다 REJECTED된 사례, 결정#4)의
반복이다. 기록만 하고 어떤 결정에도 쓰지 않는다.

## 9. Limitations (이번 조사 자체의 한계)

1. **Damodaran 원문 PDF 직접 열람 실패** — WebSearch 요약(구글 스니펫 수준)만
   확보했다. TYL SBC 사건(2차 출처 인용 오류로 3배 틀림)과 같은 위험 계열이라,
   §6의 "2.0~3.5%" 수치는 **[2차 출처 확인, 1차 원문 미대조]**로 표시해야 한다.
2. **CFA 커리큘럼 직접 대조 안 함** — "CFA 커리큘럼에 명시됨"은 WebSearch 요약
   문장을 그대로 신뢰한 것이며, 실제 커리큘럼 리딩 원문은 확인하지 않았다.
3. **오픈소스 프로젝트는 README/WebFetch 요약 수준**으로만 확인했다 — 소스코드
   전문을 클론해 정독하지 않았으므로 "임계값이 전혀 없다"는 결론이 완전할
   보장은 없다(다만 스크리닝 프로젝트 다수에서 일관되게 같은 패턴이 나온 것은
   신뢰도를 높인다).
4. Piotroski F-score와 DRS의 유사성(§3-3)은 이번 조사에서 깊이 파지 않았다 —
   RQ-001(growth_quality, v3.53)이 이미 ROIC/ROIIC 배선을 BLOCKED로 판정한
   맥락과 겹치므로 중복 조사를 피했다.

## 10. Decision (§29 형식)

| 대상 | 결정 | 근거 |
|---|---|---|
| `MIN_REALISTIC_GROWTH`(8%)/`MAX_IMPLIED_GROWTH`(5.5%)/tier 경계 수치 변경 | **REJECT** | 외부 학술문헌·오픈소스 어디에도 대응하는 절대 컷오프가 없다 — 근거 없는 숫자를 근거 없는 다른 숫자로 바꾸는 것과 다르지 않다. |
| implied-growth 비교 아키텍처를 `ECONOMICALLY_SUPPORTED`로 라벨 승격 | **ADOPT** | Gebhardt/Lee/Swaminathan(2001, JAR)·Rappaport&Mauboussin·Damodaran 3갈래 수렴. 숫자는 안 바꾸고 VALIDATION_STATUS 라벨만 갱신(코드 동작 무변경). |
| `default_terminal_growth` ceiling(4.5%→3.5%) 변경 | **REJECT(지금은)** | 실제 34/34 영향 0건으로 확인됐고, 유일한 근거(Damodaran)가 1차 원문 미대조 상태다. v3.52의 초대형주가산 처리와 동일 원칙 적용. |
| ceiling 발견을 VALIDATION_STATUS + 결정기록에 등재 | **ADOPT** | 향후 rf 상승으로 실제 바인딩되는 순간 즉시 참조할 수 있어야 한다. |
| 성장 하한(8%)과 CKL(2003)/Magic Formula의 긴장관계 기록 | **ADOPT** | 지금까지 명시된 적 없는 사실 — 정직하게 남긴다. RQ-001의 "성장은 축소이지 예측이 아니다" 결론과 정합적. |
| PEG 경계값 유사성 | **기록만, 결정 없음** | 구조가 다른 지표의 표면적 일치 — 어떤 코드 변경 근거로도 안 쓴다. |

## 11. Remaining Uncertainty

1. Damodaran/CFA 인용은 2차 출처 요약이다 — 1차 원문 대조가 이뤄지기 전까지는
   §6의 "100bp 높다"는 주장도 잠정적으로 다뤄야 한다.
2. Greenblatt Magic Formula의 "성장 없이도 작동한다"는 설계가 IRS 맥락(개별
   기업 심층분석, Magic Formula는 대규모 분산 포트폴리오 전제)에 그대로
   전이되는지는 검증하지 않았다 — 두 방법론의 전제(집중 vs 분산)가 다르다.
3. 오픈소스 생태계 전수조사가 아니라 검색 상위 노출 프로젝트 위주 표본이다.
