# Growth Quality 연구 — §33 사전 산출물 (A/B/C/D)

작성일: 2026-08-16 · **코드 미수정 단계**(§0-1) · 후속: §4 기준선 동결 → 연구 실행

⚠️ 이 문서는 v3.53 RQ-001(`reports/research/RQ-001_growth_quality_2026-08-16.md`)의
후속이자 **더 엄격한 재수행**이다. v3.53이 이미 확정한 것은 재계산하지 않고 참조하며,
이번에 새로 요구된 것(§4 기준선 동결 / §8 ROIIC 3분류 / §11 판정영향 측정 /
§13 A~D 8기준 비교 / §14 이중계산 / §18 분할)에 노력을 집중한다.

---

## ⚠️ 먼저: 이전 세션 서술 1건 정정 (§1 "문서보다 코드 실행 결과 우선")

**과거 기록**: "MNDY·UBER의 음수 FCF 기준연도는 v3.19 가드가 **자동으로** 앞당겨
해결한다(2020→2021)."

**코드 실측**: `_cagr(start, end, years)`는 `start <= 0`이면 **예외를 던져 차단만
한다.** 기준연도를 앞당기는 자동 로직은 `pipeline.py` 어디에도 없다
(`base_5y = years[-6]` 고정). MNDY 2021·UBER 2022·BKNG 2019는 전부 분석자가
`cagr_base_year_override`를 **수동 입력**한 결과이며(34종목 중 4건), 각각
사유가 기록돼 있다(예: MNDY "FY2020 OCF −$37.175M 적자라 FCF 음수").

**함의**: 근사-0 기준연도는 "가드가 조용히 만든 부작용"이 아니라 **분석자가
하드 제약 아래 선택한 주관적 입력**이다. 사유가 남아 있다는 점에서 이전 서술보다
상태가 낫지만, 동시에 **주관적 입력이 성장률 전체를 좌우한다**는 뜻이기도 하다.

---

## A. 현재 Realistic Growth 계산 그래프

```
AnalysisInputs
├─ revenue_by_year ─────────────┬─► rev_cagr_3y  = _cagr(rev[-4], rev[-1], 3)
│                               ├─► rev_cagr_5y  = _cagr(rev[base_5y], rev[-1], span_5y)
│                               └─► rev_cagr_10y = _cagr(rev[-11], rev[-1], 10)  또는 None
│                                     └─(None이면 5y로 대체 + data_limitations 기록)
│
├─ operating_cashflow_by_year ──┐
├─ capex_by_year ───────────────┴─► fcf[y] = OCF[y] − capex[y]
│                                     ├─► fcf_cagr_5y = _cagr(fcf[base_5y], fcf[-1], span_5y)
│                                     └─► fcf0 = fcf[-1]        (Implied Growth로)
│
├─ cagr_base_year_override ─────────► base_5y, span_5y  (수동, 4/34, 사유 필수)
│
├─ market_cap ──┬──────────────────► structural_discount_rate(
├─ (rev_cagr_3y)┤                        rev_cagr_3y, rev_cagr_10y|5y, market_cap_b)
│               │                     = 0.10 + (10y−3y)·0.5 + 시총가산(+3%p/+1%p)
│               │                       └─ 클리핑 [0.05, 0.30]
│               └──────────────────► classify_lynch_type(rev_cagr_5y, cyclicality, mc_b)
│                                        └─► lynch_type (override 가능)
│
└─ capex_classification (opt-in, 실사용 0/34)
                                      └─► capex_intensity_from_series
                                          + fcf_conservatism_adjustment → fcf_cagr 재조정

                    ▼
        realistic_growth_estimate(rev 3y/5y/10y, fcf_cagr_5y,
                                  structural_discount_pct, lynch_type)
          ① base_growth = Σ(cagr_i · w_i)/Σw_i,  w = (0.5, 0.3, 0.2)   ← 매출만
          ② if fcf_cagr_5y < base_growth:  base_growth = fcf_cagr_5y   ← min() 보수화
          ③ discounted = base_growth · (1 − structural_discount_pct)
          ④ capped = clip(discounted, LYNCH_TYPE_CAPS[lynch_type])
                    ▼
        realistic_growth_override (opt-in, 1/34=ROP) 가 있으면 ①~④ 전부 우회
                    ▼
              Realistic Growth (RG)
                    ▼
        Gap = RG − Implied Growth(market_cap, fcf0, r, n, g_terminal, model)
                    ▼
        judgment(±5%p) → judgment_grade(S~F) → ranking → buylist(grade in S/A)
```

**핵심 관찰**: 이 그래프의 입력 중 **수익성(마진)·자본수익률·재투자수익률은 하나도
없다.** 매출과 FCF의 *증가율*만 들어가고, 그 성장이 어떤 경제성 위에서 일어나는지는
어디에도 반영되지 않는다.

## B. 현재 Realistic Growth에 실제로 쓰이는 변수 전체 (§5의 9필드)

| 변수 | Definition | Economic meaning | Current role | Source | PIT | Measurement risk | Overlap | Decision impact | Validation status |
|---|---|---|---|---|---|---|---|---|---|
| `rev_cagr_3y` | 3년 매출 CAGR | 최근 성장 속도 | RG 가중평균 w=0.5 · structural_discount의 최근항 · revenue_volatility | 10-K 매출 | 가능 | 기준연도 1개에 좌우 | 5y/10y와 강한 상관 | 높음(가중치 최대) | SOFTWARE_VALIDATED |
| `rev_cagr_5y` | 5년 매출 CAGR | 중기 성장 속도 | RG w=0.3 · Lynch 분류 · 10y 없을 때 대체 | 동상 | 가능 | **base_5y 선택에 좌우**(4/34 수동 override) | 3y/10y와 상관 | 높음 | SOFTWARE_VALIDATED |
| `rev_cagr_10y` | 10년 매출 CAGR | 장기 성장 속도 | RG w=0.2 · structural_discount의 장기항 | 동상 | 가능 | 없으면 5y 대체(경고 기록) | — | 중간 | SOFTWARE_VALIDATED |
| `fcf_cagr_5y` | 5년 FCF CAGR | 현금 성장 속도 | ② min() 비교로 RG 보수화 | OCF−capex | 가능 | **근사-0 기준연도 시 폭주**(11/34 의심, §17) | 매출 CAGR과 부분중복 | 중간(8/34에서 실제 채택) | SOFTWARE_VALIDATED / 입력품질 취약 |
| `structural_discount` | 0.10+(10y−3y)·0.5+시총가산 | 성장 둔화·규모의 평균회귀 압력 | ③ RG를 곱셈 축소 | 파생 | 가능 | 계수 0.5·가산 3%p 근거 없음 | trend_delta는 CAGR들의 함수 | **12%**(절제실험) | trend_delta=ECONOMICALLY_SUPPORTED / 시총가산=IMPLEMENTED_NOT_VALIDATED |
| `lynch_type` | 6유형 자동분류(+override) | 기업 성장 단계 | ④ RG 상하한 캡 | rev_cagr_5y·cyclicality·시총 | 가능 | 캡 값 6개 전부 근거 없음 | rev_cagr_5y 재사용 | 높음(4종목 상한 바인딩) | IMPLEMENTED_NOT_VALIDATED |
| `cagr_base_year_override` | 기준연도 수동 지정 | 폭락·적자 연도 회피 | base_5y·span_5y 교체 | **분석자 주관** | 가능 | 저점을 고르면 성장률 부풀림 | — | 높음(성장률 전체 변동) | 사유 필수화만 있음 |
| `realistic_growth_override` | RG 직접 지정 | 회사 공시 오가닉 성장 반영 | ①~④ 전부 우회 | **분석자 주관** | 가능 | 근거 품질에 전적 의존 | — | 매우 높음(ROP 판정 뒤집힘) | v3.28 사유 필수화 |
| `capex_classification` | growth_investment/margin_erosion | capex 급증의 성격 | fcf_cagr 재조정 | **분석자 주관** | 가능 | — | — | **0**(실사용 0/34) | 미실증 |

**§5가 요구한 역추적 결론**: RG를 결정하는 9개 입력 중 **3개가 분석자 주관**이고
(`cagr_base_year_override`·`realistic_growth_override`·`capex_classification`),
나머지 6개는 전부 **매출/FCF 증가율의 변형**이다. 수익성·자본효율 축은 **0개**.

## C. Growth Quality 후보군의 정보가치 가설 (§6 TIER 분류)

TIER 기준: ①경제적 중요 ②측정 가능 ③기존 정보와 중복 낮음 ④향후 검증 가능

| 후보 | TIER | 근거 |
|---|---|---|
| **영업이익률 수준** | **1** | 입력에 이미 있음 · 기존과 무상관(v3.53 실측 −0.069/−0.043) · H-007로 검증 예약 |
| **capex/매출 수준** | **1** | 입력에 이미 있음 · 마진과 0.047로 독립 · 단 PROXY |
| ROIC | **2** | 경제적으로 최상위 중요하나 **투하자본 시계열 부재** |
| ROIIC | **2** | 동상 + 정의 자체가 불안정(§8) |
| Reinvestment rate | **2** | capex/OCF만 가능, 인수·R&D 부재 → 부분 대리 |
| Gross margin trajectory | **2** | **매출총이익이 입력에 아예 없음** |
| Working capital intensity | **2** | 운전자본 항목 미수집 |
| Share count CAGR / 희석 | **2** | **주식수 미수집**(SBC만 7/34 opt-in) |
| Organic vs inorganic | **2** | 인수금액 미수집. GEN/BRO/ROP에서 반복 지적된 공백 |
| 마진·FCF전환·capex 추세(slope) | **3** | v3.53 실측: 마진변동성 0.675·RG 0.594·Gap 0.512로 중복 |
| FCF전환/매출 | **3** | 마진수준과 0.565 중복 |
| FCF/영업이익 | **3** | SBC/FCF와 +0.571 — 현금품질이 아니라 SBC 강도를 잼 |
| Market share trend | **3** | 이미 필수 입력이며 DRS로 유입 |
| SBC 부담 | **3** | `sbc_cross_check` 이미 구현 |
| Pricing power / Moat stability | **4** | 정성 판단이며 수치화 근거 없음. LLM 서술을 숫자로 바꾸는 것은 금지 |
| Customer concentration | **4** | 미수집 + 판정 연결 근거 없음 |

**TIER 1은 2개뿐**이며 둘 다 v3.53에서 이미 ADOPT(진단축)됐다. → **이번 Stage의
신규 가치는 새 변수 추가가 아니라, TIER 2의 최상위(ROIC/ROIIC)가 왜 BLOCKED인지
정밀하게 규정하고 그 해제 조건을 확정하는 것**에 있다.

## D. STAGE 1 연구 설계

| 단계 | 내용 | STOP 조건 |
|---|---|---|
| D-1 | §4 기준선 동결: 34종목 9개 지표를 해시 고정 | — |
| D-2 | §17 입력품질 분리: FCF CAGR 근사-0 문제를 **정보 문제와 분리**해 규모 확정 | D — proxy를 정확값처럼 쓰면 중단 |
| D-3 | §8 ROIIC 3분류(Exact / Accounting Approx / Proxy)로 계산 가능성 판정 | D |
| D-4 | §9 증분정보: baseline 3종(rev CAGR / FCF CAGR / 현행 RG) 대비 | A — 상관만으로 예측력 주장 금지 |
| D-5 | §11 판정영향: ΔRG·ΔGap·Δ판정·Δ등급·Δ순위·Δ매수리스트 측정 | G — 좋아 보인다고 배선 금지 |
| D-6 | §13 A~D 구조를 8기준(이중계산·복잡도·해석가능성·PIT·과적합·경제논리·민감도·검증가능성)으로 비교 | — |
| D-7 | §14 decision ownership 지정 및 이중계산 점검 | C |
| D-8 | §27 최종 판정 + 재개조건 기록 | B — 임계값 사후 최적화 금지 |

**§18 분할 판단(사전)**: n=34에서 dev/holdout을 나누면 각 17건이며, TIER 1 후보가
2개뿐이라 분할이 통계적 의미를 갖지 못한다. **분할하지 않되, 동일 표본에서 찾은
어떤 값도 validation이라 부르지 않는다**(이미 v3.53에서 지킨 원칙 — 표본내 최적
축소계수를 REJECT한 근거와 동일).

**이번 Stage에서 새 변수를 production 계산식에 넣을 사전 확률은 낮다**고 본다 —
TIER 1 두 개는 이미 진단축으로 채택됐고 검증(H-007)은 결과 대기 중이므로,
지금 계산식에 넣으면 §22의 "Decision Impact / Validation Path" 기준을 통과하지
못한다. 이 예상 자체도 결과를 보고 바꾸지 않도록 여기 미리 적어둔다.

---

# 연구 실행 결과 (D-1 ~ D-6)

재현: `scripts/growth_quality_research_2026_08_16.py` ·
원자료: `reports/growth_quality_research_2026-08-16.json` ·
기준선: `reports/baseline_frozen_2026-08-16.json` (fingerprint `fbd34322…`)

## D-1 기준선 동결 (§4)

34종목 9개 항목(engine_version·RG·IG·Gap·judgment·model·n·DRS·confidence)을
SHA-256으로 고정했다. `verify_baseline()`이 연구 종료 시 재확인한다.

⚠️ **부수 발견 — ledger 스키마가 엔진 버전에 따라 균일하지 않다.** 스탬프 분포는
v3.19(9) · v3.21(1) · v3.25(8) · v3.27(15) · v3.41(1)이고, **v3.19판 9종목에는
`cagr_5y_base_year` 필드 자체가 없다**(v3.21에서 추가된 필드). 횡단면 연구는
이 비균일성을 항상 처리해야 한다 — 이번엔 그 9종목이 override 기능 이전 버전이라
기본 기준연도 `years[-6]`가 확정임을 이용해 대체했다.

## D-2 입력품질과 정보문제 분리 (§17) — **이전 서술을 정정한다**

기준을 "기준연도 FCF가 최종연도의 10% 미만"으로 엄밀히 잡으면:

| 종목 | 기준FCF/최종FCF | fcf_cagr_5y | **RG에 실제 채택?** |
|---|---|---|---|
| MNDY | 0.84% | 230.51% | **아니오** |
| DUOL | 3.88% | 91.56% | **아니오** |
| UBER | 3.99% | 192.53% | **아니오** |
| SE | 4.87% | 83.03% | **아니오** |
| VRT | 8.69% | 63.02% | **아니오** |

**취약 5/34, 그중 RG에 실제로 채택된 것은 0건이다.** `min(FCF CAGR, 매출가중
CAGR)`이 이 값들을 전부 걸러낸다 — 폭주한 CAGR은 항상 매출 CAGR보다 크기 때문이다.

→ **이 문제는 실재하나 현재는 잠재적(latent)이며 활성 결함이 아니다.** 이전
세션이 "11/34 의심"이라 적은 것은 느슨한 기준(FCF CAGR > 매출CAGR 2배)을 썼기
때문이고, 그 서술은 문제의 **활성 여부**를 구분하지 않았다. 다만 **FCF 파생 변수를
새로 만들면 즉시 활성화된다** — 그래서 §17이 이 분리를 먼저 요구한 것이다.

**별개 문제(활성)**: 필드명이 `fcf_cagr_5y`인데 실제 span이 5가 아닌 종목이
4건 있다(BKNG 6 · TCOM 6 · MNDY 4 · UBER 3). 이건 오독 위험이 실재하는 명명 결함이다.

## D-3 ROIIC 계산가능성 3분류 (§8)

| 정의 | 계산가능 | 상태 | 차단 입력 |
|---|---|---|---|
| **Exact / Economically Faithful** ΔNOPAT/ΔInvestedCapital | **0/34** | **BLOCKED** | 유효세율 시계열, 투하자본 시계열, goodwill 분리 |
| **Accounting Approximation** Δ영업이익(1−t)/Δ(자기자본+부채) | **2/34** | **BLOCKED** | `shareholders_equity_by_year`가 보험사 opt-in 전용, 총부채 시계열 부재(`net_debt`는 최신 스칼라) |
| **Proxy** Δ영업이익/누적capex | 34/34 | **COMPUTABLE_BUT_NOT_ROIIC** | — |

Proxy는 계산되지만 **분모가 투하자본이 아니라 누적 capex**라 인수(goodwill)·
운전자본·R&D가 빠진다. 자본집약 업종과 자산경량 업종을 비교할 수 없으므로
**ROIIC라고 부르지 않는다**(§8 명령). 이름을 지키기 위해 채택하지 않았다.

## D-5·D-6 구조 A/B/C/D 판정영향 (§11·§13) — **결정적 결과**

⚠️ 아래 k·n_shift는 **의도적 임의값이며 제안이 아니다**. 34종목 결과를 보고 고르지
않았다(STOP CONDITION B 회피). 목적은 크기 측정뿐이다.

| 구조 | 판정flip | 등급변경 | **유니버스변경** | Gap변동 중앙 | Gap 최대변동 |
|---|---|---|---|---|---|
| A 성장률만, k=0.5 | 0 | **0** | **0** | 0.03%p | 2.65%p |
| A 성장률만, k=1.0 | 1 | 4 | **3** | 0.05%p | 5.29%p |
| B Duration만(±2년) | 0 | 1 | 0 | 0.00%p | 2.19%p |
| C 둘 다, k=0.5 | 1 | 2 | 0 | 0.02%p | 2.48%p |
| D 진단축만 | 0 | 0 | 0 | 0.00%p | 0.00%p |

k=1.0에서 유니버스가 바뀌는 3종목은 **BKNG(B→A, 마진 32.8%) · PTC(B→A, 35.9%) ·
RMD(B→A, 32.8%)** 로 전부 고마진이다 — 방향은 경제적으로 일관된다.

**그러나 결론은 반대다.** 판정영향의 크기가 **정보가 아니라 임의계수 k에 의해
전적으로 결정된다**: k=0.5면 아무것도 안 바뀌고, k를 2배로 하면 매수 유니버스가
3건 바뀐다. §11이 제시한 두 실패조건에 **동시에** 걸린다:

- k=0.5 → "정보가 추가됐는데 판정에 차이가 없다" → diagnostic이 적절
- k=1.0 → "판정을 크게 바꾸는데 경제적 근거(k)가 부족하다" → production 금지

→ **어느 k를 고르든 A/B/C는 정당화되지 않는다. D가 유일하게 남는다.**

## §13 A~D 8기준 비교

| 기준 | A(Rate) | B(Duration) | C(둘 다) | **D(진단축)** |
|---|---|---|---|---|
| 이중계산 위험 | 중 — structural_discount가 이미 성장 둔화를 반영 | 중 — n은 이미 Lynch 캡과 상호작용 | **높음** — 같은 마진 정보가 두 경로 | **없음** |
| 모델 복잡도 | k 1개 추가 | n 규칙 추가 | k+n 규칙 | 0 |
| 해석가능성 | 중 | 낮음(n 변화가 Gap에 비선형) | 낮음 | **높음** |
| PIT 가용성 | 동일 | 동일 | 동일 | 동일 |
| 과적합 위험 | **높음**(k 미검증) | 높음 | **매우 높음** | **없음** |
| 경제논리 | 있음(고마진→지속성) — 단 **미검증** | 있음 | 있음 | 해당없음 |
| 민감도 | k에 전적 의존(실측) | 낮음 | k에 의존 | 없음 |
| 향후 검증가능성 | 낮음(k가 섞여 원인 분리 불가) | 낮음 | **매우 낮음** | **높음**(축이 독립 보존) |

## §14 이중계산 점검 — decision ownership

| 정보 | 현재 소유 경로 | 신규 축과 충돌? |
|---|---|---|
| 성장 둔화 | `structural_discount_rate`(trend_delta) | 마진수준은 둔화가 아니라 **수준**이라 충돌 없음 |
| 성장 단계 | `lynch_type` 캡 | 충돌 없음(캡은 성장률 기준) |
| 자본집약도 | FCF=OCF−capex에 **암묵 반영** | ⚠️ `capex_to_revenue_level`은 같은 capex를 다시 본다 — **부분 이중계산**. 그래서 진단축으로만 두고 계산 경로에 넣지 않는다 |
| 현금전환 | `min()` 비교 | FCF/영업이익을 REJECT한 이유와 동일 |

## 최종 판정 (§27)

| 후보 | 판정 | 근거 | 알려진 한계 | 재개조건 |
|---|---|---|---|---|
| 영업이익률 수준 | **ADOPT AS DIAGNOSTIC** | 기존과 무상관, 입력 이미 존재 | 예측력 미검증 | H-007 |
| capex/매출 수준 | **ADOPT AS DIAGNOSTIC** | 마진과 독립 | PROXY, FCF와 부분 이중계산 | H-007 |
| Exact ROIIC | **BLOCKED** | 0/34 계산불가 | — | 유효세율+투하자본 시계열 확보 |
| Accounting Approx ROIIC | **BLOCKED** | 2/34(보험사만) | — | 자기자본·총부채 시계열 34종목분 |
| Proxy(Δ영업이익/누적capex) | **REJECT** | 계산은 되나 ROIIC가 아니며 업종간 비교 불가 | — | 이름과 용도를 분리해 재정의 시 |
| 구조 A / B / C | **REJECT** | 판정영향이 임의계수 k에 전적 의존(k=0.5→0건, k=1.0→3건) | — | k에 외부·경제적 근거 확보 시 |
| **구조 D** | **ADOPT** | 위 전부의 귀결 | 진단축은 판정을 개선하지 않는다 — 검증 대기 | — |
