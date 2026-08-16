# Decision Attribution — TTD 5-Why + 6종목 §36/§63 분류

작성일: 2026-08-16 · 데이터: `data/historical_validation/decision_attribution.csv`
(재현 가능) · [CODE-VERIFIED]

## §36(논거 컴포넌트) vs §63(최종 투자성과) — 반드시 분리

| 종목 | horizon | §36 컴포넌트 정오 | 근거(실측) | §63 최종귀속 |
|---|---|---|---|---|
| DUOL | 11일 | **CORRECT** | DAU +23%YoY로 전분기 대비 가속 - AI대체 우려 반박 | INCONCLUSIVE |
| MNDY | 11일 | **UNRESOLVED** | 코호트별(50K+/100K+ ARR) NDR 미공개, 전사 NDR(109%)만으로 판정 불가 | INCONCLUSIVE |
| PGR | 10일 | **PARTIALLY_CORRECT** | 임계값(CR≥90) 미도달이나 방향은 악화(86.2%→87.3%, 6월 단월 90.0%) | INCONCLUSIVE |
| SE | 10일 | **CORRECT** | Shopee EBITDA +12.2%YoY - 원우려(전년比 감소)가 정면 반전 | INCONCLUSIVE |
| TCOM | 9일 | **UNRESOLVED** | 날짜추출이 소송 집단기간(서술적 날짜)을 오탐 - 실제 검증 미실시 | INCONCLUSIVE |
| TTD | 10일 | **INCORRECT** | 4개 조건 중 3개 동시 발동 | INCONCLUSIVE |

**§63이 전건 INCONCLUSIVE인 이유**: §63의 6개 분류(IRS CORRECT AND
VALUE-ADDING 등)는 전부 **실제 투자성과**(수익률)를 전제한다. 이 저장소엔
어떤 종목도 수익률 관측이 없다(TTD의 발표 당일 -21.8%는 누적수익률이 아니라
단일 이벤트 반응이라 §33의 1M조차 못 채운다). §31("Never evaluate IRS only
by stock return")과 이 사실을 혼동하지 않는다 — 여기선 수익률 평가를 아예
안 하는 게 아니라 **할 데이터가 없다.**

## TTD — 유일한 INCORRECT 사례, 5-Why

**표면 관찰**: TTD는 원분석(2026-08-03)에서 S등급·"저평가 가능성"·Gap
+17.01%p로 판정됐다. 10일 뒤(2026-08-13) 재검증에서 사전등록 반증조건 4개 중
3개가 동시 발동했다(Q2 매출 가이던스 하회, Q3 가이던스 역성장, 경영진
추가교체).

```
WHY 1: 왜 판정이 무너졌는가?
  → Q3 가이던스가 컨센서스($804.8M) 대비 -12.1%YoY 역성장을 회사 스스로 제시.

WHY 2: 왜 이 정보가 원분석 시점(08-03)에 반영 안 됐는가?
  → 원분석은 그 시점 재무제표(과거 CAGR)로 Realistic Growth 16.70%를 산출했고,
    그 값은 **정의상 미래 실적을 포함할 수 없다**(다년 CAGR 요약이지 예측
    모델이 아님 - docs/AUDIT_2026-08-15_investment_value.md §5.1 기존 발견 재확인).

WHY 3: 왜 Realistic Growth가 미래정보를 못 담는가?
  → realistic_growth_estimate()의 입력이 revenue_cagr_3y/5y/10y·fcf_cagr_5y뿐
    이다(engine/expectation_gap_engine.py, 이번 감사에서 재확인). 경영진
    안정성·경쟁강도 추세·거버넌스 리스크는 애초에 이 함수의 입력이 아니다.

WHY 4: 그런 정성적 위험은 어디서 다뤄지는가?
  → 2026-08-03 정성조사(CLAUDE.md 기록)가 이미 "S등급 7종목 중 최심각 -
    연방 증권사기소송+CEO 내부자거래 혐의+CFO 14개월새 4명 교체"를 발견해
    Confidence를 94→72로 낮췄다. **경고 자체는 있었다.**

WHY 5: 경고가 있었는데 왜 공식 Gap/판정은 그대로였나?
  → "병기, 자동판정 안 함" 원칙(is_insurer/sbc_cross_check와 동일 설계)이
    정성적 발견을 Gap 계산에 자동 반영하지 않도록 **의도적으로** 막고 있다.
    Confidence 하향만 매수리스트 가중치에 반영됐다(72→45, 2026-08-13).
```

**근본원인(시스템 수준, 재발방지 가능한 지점)**: Realistic Growth가 구조적으로
"과거 재무제표 요약"이며 거버넌스·경영진 리스크를 담을 그릇이 아니다.
"병기, 자동판정 안 함" 원칙 자체는 유지할 가치가 있다(사후합리화 방지) —
문제는 **병기된 정성적 경고가 매수리스트 비중에는 반영됐지만 공식 Gap/판정
이력에는 반영되지 않아, 이 사례처럼 반증조건이 실제 발동하기 전까지는
"S등급·저평가"라는 라벨이 그대로 유지된다**는 점이다. 이는 결함이 아니라
설계된 트레이드오프이나, 그 트레이드오프의 비용(TTD처럼 라벨이 늦게
갱신됨)이 이번에 실측으로 확인됐다.

**Decision Impact 판정(§29)**: 이 오차는 §29 기준으로 **HIGH DECISION
IMPACT**다 — 반증조건 발동 즉시 매수리스트 비중이 4.80%→2.70%로 실제로
축소됐다(2026-08-13, 사용자 승인). 공식 판정은 안 바뀌었지만 **실제 자본배분
결정은 바뀌었다.**

## 표본 크기 경고 (§38)

TTD 1건을 "시스템의 구조적 약점"의 **예시**로 쓰되, "Realistic Growth는
거버넌스 리스크를 놓친다"는 것을 **일반 법칙**으로 주장하지 않는다 — n=1이다.
다른 5건 중 INCORRECT는 0건, PARTIALLY_CORRECT 1건(PGR), UNRESOLVED 2건뿐이라
"이 시스템은 자주 틀린다"는 결론도, "이 시스템은 대체로 맞는다"는 결론도
표본으로 뒷받침되지 않는다. **INDIVIDUAL ERROR로 분류하고 SYSTEMATIC이라
부르지 않는다.**
