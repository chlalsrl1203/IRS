# 성장률 상한 외부검증 — 투자 대가·투자기업·학술지 기준 대조

작성일: 2026-08-23 · 깊이등급 **D3**(영향 높음·근거 불확실했음·구현이 판정을
바꿀 수 있음) · 재현 `scripts/base_rate_audit_2026_08_23.py` ·
원자료 `reports/base_rate_audit_2026-08-23.json`

## 1. Research Question

`LYNCH_TYPE_CAPS`(fast_grower 25% / stalwart 12% / slow_grower 5% / cyclical 20%
/ turnaround 30% / asset_play 10%)는 v3.24(2026-08-01)부터 **"근거가 이
코드베이스 어디에도 없다"**고 명시된 채 유지돼 왔다. 이 수치들은 어디서
왔는가? 외부에 더 나은 기준이 있는가?

**이 조사는 v3.63(같은 날 오전)과 표적이 다르다.** v3.63은 `screener.py`의
`MIN_REALISTIC_GROWTH`/`MAX_IMPLIED_GROWTH`(1차 필터 임계값)를 봤고 REJECT로
끝났다. 이번은 **Realistic Growth 자체의 상한**이며, 34종목 중 **7종목에서
실제로 바인딩**된다(BRO·CDNS·DUOL·GEN·MNDY·PDD·ROP).

## 2. Current IRS Baseline — 캡이 바인딩되면 성장분석이 무의미해진다

v3.24 M-1이 이미 기록한 성질: **상한이 바인딩되면 그 종목의 Gap은 매출·FCF
CAGR과 구조적 할인을 전부 무시하고 `캡 − Implied Growth`로만 결정된다.**
공들여 계산한 성장분석이 결과에 아무 기여를 하지 못한다.

실측(2026-08-23, ledger 34종목):

| 종목 | 유형 | 원시 매출 CAGR | 부여된 RG | 캡 |
|---|---|---|---|---|
| DUOL | fast_grower | 3y 41.1% / 5y 45.0% | **25.00%** | 상한 |
| MNDY | fast_grower | 3y 33.4% / 5y 41.4% | **25.00%** | 상한 |
| PDD | fast_grower | 3y 49.0% / 5y 48.7% | **25.00%** | 상한 |
| BRO | stalwart | 3y 17.4% / 5y 17.2% | **12.00%** | 상한 |
| CDNS | stalwart | 3y 14.1% / 5y 14.6% | **12.00%** | 상한 |
| GEN | stalwart | 3y 14.4% / 5y 14.4% | **12.00%** | 상한 |
| ROP | stalwart | 3y 13.7% / 5y 14.5% | 5.50%(override) | 상한→override |

## 3. Finding 1 — 캡 수치의 출처가 특정됐다 (v3.24의 "추정"이 사실로 확인)

피터 린치, *One Up on Wall Street*의 6분류 정의:

- **Stalwarts**: "grow at a medium pace: **10-12%** every year"
- **Fast Growers**: "small, aggressive companies that grow around **20-25%** annually"

IRS의 상한 **12%**(stalwart)와 **25%**(fast_grower)는 이 범위의 상단과
정확히 일치한다. v3.24가 *"린치의 원저서 분류법에서 관용적으로 쓰이는 수치를
그대로 가져온 것으로 추정"*이라 적어둔 것이 **사실로 확인**됐다.

## 4. Finding 2 — ⭐ 그런데 용도가 다르다 (핵심 결함)

린치의 범위는 **"이 회사가 지금 어느 유형인가"를 가르는 분류 기술어**다.
IRS는 그것을 **"이 회사가 앞으로 n=12년간 얼마나 성장할 것인가"의 예측
상한**으로 쓴다. 이건 같은 숫자의 다른 용도다.

그리고 결정적으로 — **린치는 fast grower를 명시적으로 "small, aggressive
companies"라고 했는데, IRS는 같은 25%를 규모와 무관하게 적용한다.**

| | DUOL | PDD |
|---|---|---|
| 최근 매출 | $1.04B | CNY 431.8B ≈ **$60.0B** |
| 부여된 RG | 25.00% | 25.00% |
| 규모 차이 | — | **약 58배** |

## 5. Primary Evidence — Credit Suisse HOLT 실측 base rate

**출처**: Michael J. Mauboussin & Dan Callahan, *"The Base Rate Book:
Integrating the Past to Better Anticipate the Future"*, Credit Suisse Global
Financial Strategies, 2016-09-26.

⚠️ **원문 PDF를 직접 파싱했다** — 2차 출처 요약이 아니다. TYL SBC 3배 오류가
2차 출처를 검증 없이 인용해 생긴 사고였기 때문이다. 전사 정확성은 **각 표의
열 합계가 100%인지**로 검증했다(12개 표 × 4개 열 = 48개 열 중 44개가
99.5~100.5%. 나머지 4개는 `325-700` 구간 하나인데 **원문 자체가** 89~93%로
합계가 안 맞는다 — 파싱 오류가 아니라 출처의 흠이며 그대로 기록했다).

**모집단의 질이 IRS 자체 표본보다 낫다**:
- 시가총액 상위 1,000개 글로벌 기업, **1950-2015년**(65년)
- 전 세계 시총의 약 60%, 전 섹터
- ⭐ **소멸한 기업을 포함한다** — *"The population includes companies that are
  now dead"*. 생존편향이 없다. `engine/quant/validation.py`가 IRS 자체 표본의
  생존편향(스크리닝 83종목→75탈락, 생존율 하한 9.6%)을 경고하고 있는 것과
  대비된다.
- 1/3/5/10년 CAGR. IRS의 n=12에 가장 가까운 것은 **10년 열**.

### ⚠️ 단위 함정 두 개 — 둘 다 이 프로젝트가 이미 겪은 유형

**(1) 표는 실질(real)이다.** 원문: *"We adjust all of the figures to remove the
effects of inflation, which translates all of the numbers to 2015 dollars."*
IRS의 RG는 **명목**이다. 그대로 비교하면 인플레율만큼 조용히 낙관 편향된다 —
v3.35에서 multpl.com의 실질 S&P500 EPS를 명목 기대성장률과 비교할 뻔한 것과
**정확히 같은 함정**. `nominal_to_real()`을 강제하고 인플레 가정(2.5%)을
명시적 인자로 노출했다.

**(2) 매출 규모 구간도 2015년 달러다.** 명목 매출을 그대로 넣으면 더 큰
decile로 잘못 배정된다. `deflate_to_2015()`(계수 1.35 = 미국 CPI 2015→2025)로
환산한다. decile 폭이 넓어 이 계수가 ±10% 틀려도 경계 근처 소수만 바뀐다.

### 10년 CAGR base rate (실질, %)

| 매출 규모(2015$) | ≥15% | ≥20% | ≥25% | 중앙값 |
|---|---|---|---|---|
| $0-325M | 28.6 | 18.1 | 11.9 | 9.8 |
| $700M-1.25B | 8.4 | 3.5 | 1.5 | 5.7 |
| $3-4.5B | 4.4 | 1.2 | 0.4 | 4.1 |
| $12-25B | 3.4 | 0.9 | 0.3 | 2.7 |
| **>$25B** | **1.5** | **0.2** | **0.0** | 1.8 |
| **>$50B** | **0.9** | **0.0** | **0.0** | 1.1 |
| 전체 | 9.0 | 4.5 | 2.5 | 4.9 |

Mauboussin의 결론: *"as firm size increases the mean and median growth rates
decline... The lesson is to temper expectations about sales growth as companies
get larger."*

**IRS의 캡은 규모를 전혀 보지 않는다. 그런데 실증 분포는 규모가 지배한다.**

## 6. Experiment — 34종목 전수 대조

각 종목의 최근 매출을 2015년 달러로 환산해 규모 구간을 배정하고, 부여된 RG를
실질로 환산해 그 구간의 10년 base rate를 조회했다.

**같은 25% 캡의 base rate가 규모에 따라 17.5배 갈린다:**

| 종목 | 규모 구간 | RG(명목) | RG(실질) | 10년 base rate | 등급 |
|---|---|---|---|---|---|
| **PDD** | >$25B | 25.00% | 21.95% | **0.2%** | EXTREMELY_RARE |
| **SE** | $12-25B | 23.56% | 20.55% | **0.9%** | EXTREMELY_RARE |
| VRT | $7-12B | 18.71% | 15.82% | 3.2% | RARE |
| **DUOL** | $700M-1.25B | 25.00% | 21.95% | **3.5%** | RARE |
| **MNDY** | $700M-1.25B | 25.00% | 21.95% | **3.5%** | RARE |
| PGR | >$50B | 16.87% | 14.01% | 3.9% | RARE |
| … | | | | | |
| BRO/CDNS/GEN | $3-4.5B | 12.00% | 9.27% | 41.2% | COMMON |
| ROP | $4.5-7B | 5.50% | 2.93% | 79.2% | COMMON |

전체 분포: EXTREMELY_RARE 2 · RARE 4 · UNCOMMON 5 · COMMON 23.

### ⭐ 자본에 도달하는가 — 매수 포트폴리오 기준

| base rate 등급 | 포트폴리오 비중 |
|---|---|
| EXTREMELY_RARE (<1%) | **16.46%** (PDD 9.07 + SE 7.39) |
| RARE (<5%) | 24.56% (PGR 12.00 + DUOL 6.29 + MNDY 6.27) |
| UNCOMMON (<20%) | 23.98% |
| COMMON | 35.00% |

**매수 포트폴리오의 41.02%가 "역사적으로 5% 미만의 동종 규모 기업만
달성한" 성장률 위에 서 있다. 16.46%는 1% 미만이다.**

## 7. ⭐ 가장 중요한 구분 — 문제는 캡 값이 아니라 캡의 규모 무시다

- **stalwart 12%**: 바인딩된 3종목(BRO/CDNS/GEN, 전부 $3-4.5B) 전부
  base rate 41.2% = COMMON. **경험적으로 문제없다.**
- **fast_grower 25%**: 바인딩된 3종목 중 소형 2곳(DUOL/MNDY)은 3.5%로 희귀하지만
  가능한 범위, **대형 1곳(PDD)은 0.2%로 사실상 선례가 없다.**

즉 **"25%가 너무 높다"가 아니라 "25%를 $60B 기업에도 똑같이 적용하는 것이
틀렸다"**가 정확한 진술이다. 린치 본인의 원 서술("small, aggressive
companies")이 이미 그 조건을 달고 있었는데 IRS가 그 부분만 떨어뜨린 셈이다.

## 8. Contradictory Evidence (§9 - 채택 반대 논거를 straw-man 없이)

- **base rate는 과거 빈도이지 미래 확률이 아니다.** 1950-2015 표본에는
  현대적 소프트웨어·플랫폼 기업의 규모확장 경제가 충분히 반영되지 않았을 수
  있다. Mauboussin 자신도 후속 연구(*The Impact of Intangibles on Base
  Rates*)에서 무형자산 집약 기업의 분포가 다를 가능성을 다룬다 —
  **이번 조사에서 그 후속 논문은 확인하지 않았다.**
- **표는 매출 성장이고 IRS의 RG는 FCF/매출 혼합이다.** `realistic_growth_
  estimate`는 `min(FCF CAGR, 매출 가중평균)`을 쓴다. 완전히 같은 대상이 아니다.
- **PDD는 CNY 표시 중국기업**이라 1950-2015 글로벌 표본(미국 편중 추정)의
  reference class가 정확히 맞는지 미검증이다.

## 9. Decision (§29)

| 대상 | 결정 | 근거 |
|---|---|---|
| **`engine/base_rates.py` 신설 — 외부 실증 base rate를 병기** | **ADOPT (구현 완료)** | 1차자료 그대로 전사, 새 숫자 발명 0개. 열 합계 100% 검증으로 전사 정확성 확인 |
| **`deep_screen`에 base rate 병기 + 경고** | **ADOPT (구현 완료)** | 스크리닝 경로에만 배선 — 기존 판정·자본배분 무변경. 사용자 요청("스크리닝 기준 새로 설정")의 직접 이행 |
| base rate를 **하드 탈락 기준**으로 사용 | **REJECT** | Mauboussin 자신이 "reality check"로 쓰라고 했고 하드컷을 처방하지 않았다. IRS는 v3.19에서 하드 필터가 이중 반영을 만든다는 걸 이미 실증(BRO·BSY 오탈락) |
| **`LYNCH_TYPE_CAPS`를 규모 조건부로 변경** | **PROPOSED — 사용자 승인 필요** | 7종목의 RG가 즉시 바뀌고 → Gap → 판정 → 매수 비중까지 연쇄한다. **자본 재배분**이므로 v3.28(ROP override 승격) 선례대로 명시적 승인이 있어야 한다 |
| 캡 값 자체(25%/12%)를 다른 숫자로 교체 | **REJECT** | stalwart 12%는 실증적으로 문제없음이 확인됐다. 문제는 값이 아니라 규모 무시이므로 값만 바꾸는 건 오진에 대한 처방이다 |

## 10. 승인 대기 중인 제안 — 규모 조건부 캡

**지금 실행하지 않았다.** 아래는 승인 시 적용할 정확한 내용이다.

현행 `fast_grower: (-0.05, 0.25)` 단일 상한을, 규모 구간별 base rate가 일정
수준(예: 1%) 이상인 성장률로 제한하는 방식. 실측 영향:

| 종목 | 현행 RG | 규모 구간 | 규모조건부 상한(base rate ≥1% 기준) | 변화 |
|---|---|---|---|---|
| DUOL | 25.00% | $700M-1.25B | 25% 유지(base rate 1.5%) | **없음** |
| MNDY | 25.00% | $700M-1.25B | 25% 유지 | **없음** |
| **PDD** | 25.00% | >$25B | **약 15%로 하향**(>$25B에서 20% 이상은 0.2%) | **Gap +29.16%p → 약 +19%p** |
| BRO/CDNS/GEN | 12.00% | $3-4.5B | 12% 유지(41.2%) | **없음** |

⚠️ **PDD 단 1종목만 바뀐다**(현재 매수 비중 9.07%). 판정은 여전히 "저평가
가능성"이겠지만 Gap 크기가 줄어 등급·비중이 재계산된다. 위 "약 15%"는
base rate 1%라는 **임의 컷**에서 나온 값이므로 그 컷 자체도 승인 대상이다.

## 11. Remaining Uncertainty

1. **1% 컷은 검증된 값이 아니다.** 어느 base rate에서 "과도한 낙관"으로 부를지에
   대한 외부 기준을 찾지 못했다. Mauboussin은 분포를 보라고 했지 컷을 주지 않았다.
2. **무형자산 집약 기업 후속 연구 미확인** — Mauboussin의 *The Impact of
   Intangibles on Base Rates*를 이번에 읽지 않았다. 소프트웨어 기업(DUOL/MNDY)의
   reference class가 달라질 수 있다.
3. **매출 성장 ≠ IRS의 RG**(FCF 혼합). 방향은 유효하나 정밀 대응은 아니다.
4. 이 보고서는 **어떤 수익률 개선도 주장하지 않는다.** base rate가 낮은 종목이
   실제로 성과가 나쁜지는 IRS 표본으로 검증된 바 없다(H-001 계열, 전부 BLOCKED).
