# RQ-001 — Growth Quality 증분정보 연구 (STAGE 1)

작성일: 2026-08-16 · 재현: `scripts/growth_quality_profile_2026_08_16.py` ·
사전등록: `experiments/H-007.json` · 구현: `engine/growth_quality.py`

## Research Question

기존 IRS의 Realistic Growth가 제공하는 정보 대비, **Growth Quality를 표현하기 위해
어떤 추가 변수가 실제로 증분정보를 제공하는가?**

## 현재 IRS가 실제로 쓰는 것 (문서가 아닌 코드 확인)

| 데이터 | 입력 지위 | 엔진이 실제로 쓰는 방식 |
|---|---|---|
| `revenue_by_year` | **필수** | 3y/5y/10y CAGR → Realistic Growth, worst YoY → cyclicality |
| `operating_income_by_year` | **필수** | **오직 `margin_volatility_score`(표준편차) 하나.** 수준은 어디에도 안 쓰임 |
| `capex_by_year` | **필수** | FCF=OCF−capex. `capex_intensity_from_series`는 주관적 `capex_classification`이 있을 때만 작동 → **34종목 중 실제 사용 0건** |
| `shareholders_equity_by_year` | opt-in | `is_insurer` 전용(2종목) |
| `net_debt`, `ebitda` | 필수(스칼라) | 최신 1개값만. **시계열 없음** |

→ **핵심 사실: 영업이익률 32.8%(BKNG)와 3.4%(GWRE)가 변동성 말고는 동일 취급된다.**

## 후보별 평가

### ① 영업이익률 수준 (operating margin level) — **ADOPT**

| 항목 | 내용 |
|---|---|
| Definition | 최근연도 영업이익 / 매출 |
| Economic meaning | 사업이 매출 1원당 남기는 이익. 가격결정력·비용구조의 결과물 |
| Data requirement | **없음** — `operating_income_by_year`·`revenue_by_year` 둘 다 이미 필수 입력 |
| PIT availability | 기존 입력과 동일. 신규 누출 위험 없음 |
| Measurement risk | 낮음. 단 매출≤0 연도는 정의 불가 → 제외하고 기록 |
| **Overlap with existing IRS** | **거의 없음**: 마진변동성 −0.069 / DRS −0.043 / Gap −0.190 / RealisticGrowth −0.323 |
| Expected incremental info | 높음 — IRS가 현재 **전혀** 표현하지 못하는 축 |
| Industry limitations | 보험사는 영업이익 개념이 다름(별도 경로 존재). 적자기업은 수준이 음수 → 플래그 |
| Implementation complexity | 매우 낮음(순수함수 2개) |
| Validation possibility | H-007로 사전등록 |

### ② capex/매출 수준 — **ADOPT**

| 항목 | 내용 |
|---|---|
| Definition | 최근연도 capex / 매출 |
| Economic meaning | 매출을 유지·성장시키는 데 필요한 재투자 강도의 **약한 대리지표** |
| Data requirement | **없음** — 이미 필수 입력 |
| Overlap | 마진수준과 **0.047**(거의 독립) / DRS 0.148 → 별개 축 |
| Measurement risk | **중간** — 투하자본이 아니라 매출 대비다. ROIC의 분모를 대체하지 못함 |
| 이름 규약 | `capex_to_revenue_level`. **자본집약도라고 부르되 ROIC/ROIIC라 부르지 않는다** |
| Implementation complexity | 매우 낮음 |

### ③ 마진 추세 / FCF전환 추세 / 자본집약도 추세 — **REJECT**

**가설이 실측으로 기각됐다.** 초기 가설은 "추세가 새 정보"였으나 반대였다:

| 추세 후보 | vs 마진변동성 | vs RealisticGrowth | vs Gap |
|---|---|---|---|
| 마진추세 slope | **0.675** | **0.594** | **0.512** |
| FCF전환 추세 | 0.351 | 0.371 | 0.329 |
| 자본집약도 추세 | −0.421 | −0.344 | −0.417 |

마진추세가 마진변동성과 0.675로 강하게 겹치는 이유는 명확하다 — **적자에서
흑자로 전환한 기업이 큰 slope와 큰 변동성을 동시에 갖는다**(MNDY slope
+17.34pp/yr·변동성 32.68%, PDD +13.58·35.60%). 즉 추세는 IRS가 이미 잡고 있는
"턴어라운드" 신호를 다시 재는 것이다. §0-2의 중복 테스트를 통과하지 못한다.

⚠️ 게다가 MNDY는 slope +17.34pp/yr(최고)인데 **최근 마진이 −0.14%로 여전히 적자**다.
추세는 "훌륭한 개선"이라 말하고 수준은 "아직 적자"라 말한다 — 투자판단에는 수준이 우선한다.

### ④ FCF / 영업이익 (현금전환) — **REJECT (아티팩트)**

겉보기엔 가장 "현금의 질"다운 지표이나 실측이 기각한다.
SBC 데이터 보유 8종목에서 **FCF/영업이익 vs SBC/FCF 순위상관 +0.571**:

| 종목 | FCF/영업이익 | SBC/FCF |
|---|---|---|
| GWRE | 6.83 | 57.6% |
| WDAY | 3.85 | 58.6% |
| DUOL | 2.73 | 37.2% |

상위 3종목이 전부 고SBC다. **"현금전환 우수"가 실은 SBC 강도를 재고 있다** —
영업이익은 SBC로 눌리고 OCF에서는 가산되기 때문이다. 이는 v3.23 `sbc_cross_check`가
드러내려던 바로 그 편향을 새 지표로 다시 들여오는 셈이다.
⚠️ n=8이고 TTD(SBC 61.7%인데 FCF/OI 1.35)가 패턴을 벗어나므로 **결정적이진 않다**.
그러나 채택을 정당화할 근거는 되지 못한다.

### ⑤ FCF전환 / 매출 — **REJECT (중복)**

마진수준과 순위상관 **0.565**. 둘 다 수익성을 재며, 마진수준이 더 해석이 명확하다.
둘 중 하나만 채택한다는 원칙에 따라 마진수준을 택한다.

### ⑥ ROIC / incremental ROIC(ROIIC) — **BLOCKED**

이론적으로 가장 중요한 축이며 품질투자 진영의 표준 도구다. 그러나
**`AnalysisInputs`에 투하자본 시계열이 없다** — `shareholders_equity_by_year`는
보험사 opt-in, `net_debt`는 최신 스칼라 1개. 34종목분 신규 입력 수집이 선행돼야 한다.
**재개조건**: SEC XBRL companyfacts로 자기자본·총부채 시계열 확보(경로는
`engine/filing_dates.py`가 이미 사용 중) → 그 후 별도 RQ로 재검토.

### ⑦ reinvestment rate — **DEFER**

capex/OCF는 계산 가능하나 진짜 재투자는 capex + 인수 + R&D − 감가상각이다.
인수·R&D가 입력에 없어 **부분 대리지표에 그친다.** ROIC와 함께 다뤄야 의미가 있으므로
⑥과 함께 보류.

### ⑧ dilution / SBC 부담 — **DUPLICATE**

v3.23 `sbc_cross_check`가 이미 구현돼 있다(7종목 실사용). 재구현하지 않는다.
단 주식수 자체는 수집되지 않아 **희석 채널은 여전히 미측정**(별도 공백으로 기록).

### ⑨ acquisition dependence — **BLOCKED**

입력에 인수금액이 없다. CLAUDE.md가 GEN/BRO/ROP에서 반복 지적한 M&A 왜곡 문제와
직결되나 현재 데이터로는 계산 불가.

### ⑩ market share trajectory — **DUPLICATE**

`market_share_trend_pp_per_year`가 이미 **필수 입력**이며 DRS의
competition_intensity로 들어간다. 재구현하지 않는다.

## §3-5 구조 결정: A / B / C / D 중 무엇인가

| 구조 | 판단 |
|---|---|
| A. Realistic Growth에 직접 반영 | **REJECT** — 두 축이 성장률과 관계있다는 증거가 0건이다. 반영하면 미검증 변수가 34종목 판정을 즉시 바꾼다 |
| B. Growth Duration에 반영 | **REJECT** — 같은 이유. 게다가 Duration 자체가 아직 미고정(STAGE 2) |
| C. 둘 다 | **REJECT** — 위 둘의 합 |
| **D. 독립 보관** | **채택** — 병기하되 어떤 공식 숫자도 바꾸지 않는다 |

**미리 C를 정답으로 가정하지 말라는 지시대로, 실증 근거가 0건이라는 사실이 D를 강제한다.**
H-007이 귀무를 기각한 뒤에야 A/B/C를 다시 논의한다.

## §12 STAGE 1 완료 조건 검증

> "빠르게 성장하는 기업" vs "좋은 경제성을 가진 상태에서 성장하는 기업"을 구분할 수 있는가

관측 중앙값(RealisticGrowth 12.19%, 영업이익률 21.01%) 기준 사분면:

| 집단 | 종목수 | RealisticGrowth 중앙값 | 영업이익률 중앙값 |
|---|---|---|---|
| 고성장·고마진 | 8 (ACGL·BKNG·BRO·CDNS·DSGX·GEN·PDD·TCOM) | 12.19% | **27.4%** |
| 고성장·저마진 | 9 (BSX·DUOL·MNDY·PGR·SE·TTD·UBER·VRT·WDAY) | 16.87% | **13.1%** |

**성장률은 오히려 저마진 집단이 높은데 마진은 2배 이상 갈린다.** 기존 IRS는 이 차이를
전혀 표현하지 못했다 → **완료 조건 충족.**

## 실제 포트폴리오에 미치는 함의 (병기, 자동판정 안 함)

현행 매수리스트 12종목을 두 축에 대보면:

- 고성장·고마진 **56.07%** (GEN 18.00 · ACGL 12.00 · TCOM 10.25 · PDD 9.07 · BRO 6.75)
- 고성장·저마진 **43.93%** (PGR 12.00 · SE 7.39 · DUOL 6.29 · MNDY 6.27 · UBER 4.77 · WDAY 4.51 · TTD 2.70)

⚠️ **MNDY(6.27% 보유)는 최근 영업이익률이 −0.14%로 적자다.** 엔진은 이 종목에
Realistic Growth 25.00%(Lynch 상한 바인딩)를 부여하고 Gap +23.28%p로 S등급을 줬다.
**비중은 이 발견으로 조정하지 않았다** — 두 축의 예측력이 검증되지 않았으므로
근거 없는 조정이 된다(§13 금지사항). 사실만 병기한다.

## Decision 요약

| 후보 | 결정 |
|---|---|
| 영업이익률 수준 | **ADOPT** (독립 보관) |
| capex/매출 수준 | **ADOPT** (독립 보관, PROXY_ONLY 라벨) |
| 마진·FCF전환·자본집약도 **추세** | **REJECT** (기존 정보와 중복) |
| FCF/영업이익 | **REJECT** (SBC 아티팩트) |
| FCF전환/매출 | **REJECT** (마진수준과 0.565 중복) |
| ROIC / ROIIC | **BLOCKED** (투하자본 시계열 부재) |
| reinvestment rate | **DEFER** |
| dilution/SBC | **DUPLICATE** |
| acquisition dependence | **BLOCKED** |
| market share trajectory | **DUPLICATE** |

10개 후보 중 **2개만 채택**했다. "가장 정보가치가 높은 1~3개만 구현하라"는 지시대로다.

## 한계 (정직하게)

1. **n=34, 전부 개발 데이터.** 상관계수는 탐색적 관측이며 통계적 유의성을 주장하지 않는다.
2. SBC 아티팩트 검정은 **n=8**이고 반례(TTD)가 있다.
3. 두 축이 미래 성과를 설명한다는 증거는 **0건**이다. H-007 검정 전까지 어떤 판정에도
   쓰지 않는다.
4. `capex_to_revenue_level`은 자본집약도의 **약한 대리지표**이며 ROIC를 대체하지 않는다.
