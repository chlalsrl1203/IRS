# Forecast Validation — Realistic Growth 예측오차

작성일: 2026-08-16 · 데이터: `reports/growth_scorecard_2026-08-13.json`(재검증) ·
[CODE-VERIFIED]

## ⚠️ 표본이 매우 작다 — 모든 수치를 이 전제 아래 읽을 것

n=11 관측 중 **1건(ROP)은 순환참조라 제외한다.** ROP는 `realistic_growth_
override`로 엔진 값 자체를 관측치(5.5%)와 정확히 일치하도록 **설정**한
통제사례다(v3.28) — 그 자체가 예측 정확도의 증거가 아니라 "엔진이 오버라이드를
정확히 반영하는가"의 소프트웨어 검증이다. **독립적 예측오차 표본은 n=10.**

n=10은 §19가 명시적으로 경고한 "통계적 주장을 하기엔 너무 작은 표본"에
해당한다. 아래 수치는 **기술통계**(descriptive)일 뿐 유의성 검정이 아니다.

## 증거등급별 분리 (§18 원칙 — 절대 섞어 평균내지 않는다)

| 증거등급 | n | signed error 중앙값 | abs error 중앙값 | 의미 |
|---|---|---|---|---|
| `realized_quarterly` | 5 | −6.70%p | 10.87%p | 분석 이후 1개 분기 실적 — 진짜 out-of-sample이나 노이즈 큼 |
| `guidance_annual` | 5 | −6.89%p | 8.70%p | 회사의 1개년 예측 — **실적이 아니라 회사의 forward guess** |
| `realized_multiyear` | 1 (제외) | — | — | ROP는 오버라이드 통제사례, 순환참조 |

두 등급 모두 signed error가 **음수 방향으로 몰려 있다**(엔진이 관측치보다
높게 나옴). n=10 중 8건이 엔진 과대추정, 2건이 과소추정 — 방향성이 있어
보이지만 **n=10으로 이 방향성을 "체계적 편향"이라 부르지 않는다**(§38: 
INDIVIDUAL vs RECURRING PATTERN vs SYSTEMATIC — 여기선 RECURRING PATTERN
후보 정도로만 기록, SYSTEMATIC 주장 안 함).

## ⚠️ 등급 혼용 위험이 실제로 존재한다

Realistic Growth는 n≈12년 개념인데 `guidance_annual`은 **1개년** 예측이다.
5건 중 다수가 이 등급 불일치를 안고 있다(TTD·DUOL·TCOM·GEN·KEYS). 코드
(`growth_scorecard.OBSERVATION_KINDS`)가 이미 이 구분을 강제하고
`usable_as_override=False`로 막아두고 있어 **공식판정에는 영향이 없다** —
다만 이 오차 통계 자체를 "예측력 검증"으로 과대해석하면 안 된다는 뜻이다.

## 개별 값

| 종목 | 등급 | 엔진RG | 관측 | 오차(부호) |
|---|---|---|---|---|
| TTD | quarterly | 16.70% | 3.00% | −13.70%p |
| SE | quarterly | 23.56% | 48.10% | **+24.54%p**(엔진 과소추정 - 유일하게 큰 양의 오차) |
| DUOL | quarterly | 25.00% | 18.30% | −6.70%p |
| MNDY | quarterly | 25.00% | 22.00% | −3.00%p |
| PGR | quarterly | 16.87% | 6.00% | −10.87%p |
| TTD | guidance | 16.70% | −12.10% | −28.80%p(최대) |
| DUOL | guidance | 25.00% | 16.30% | −8.70%p |
| TCOM | guidance | 12.39% | 5.50% | −6.89%p |
| GEN | guidance | 12.00% | 7.50% | −4.50%p |
| KEYS | guidance | 1.47% | 28.00% | **+26.53%p**(엔진 과소추정 - trailing CAGR이 AI수요인플렉션 놓침, CLAUDE.md 기 문서화 패턴) |

## 점 예측 vs 구간 예측 (§20)

엔진의 공식 산출물은 **점 예측**(Realistic Growth 스칼라)이다 — 이 표는
점 예측 오차만 평가한다.

v3.51의 `gap_range_over_assumptions()`가 **구간**(가정집합 Gap 범위)을
만들지만, ⚠️ **그 구간의 커버리지·보정(calibration)을 실제 결과로 검증한
적은 없다** — 검증하려면 "관측치가 구간 안에 들어왔는가"를 여러 사례에서
누적해야 하는데, 지금 있는 것조차 서로 다른 두 종류(점 예측 오차 10건 vs
구간 자체는 34건이지만 관측 대조가 안 됨)라 짝지을 수 없다. **CRPS/커버리지
평가는 [NOT TESTABLE] — 관측-구간 짝을 이룬 사례가 0건이기 때문이다.**

## 결론

- 방향성 후보(엔진이 대체로 관측보다 높게 나옴)는 있으나 **n=10으로 통계적
  주장을 하지 않는다.**
- KEYS·SE는 정반대 방향(엔진 과소추정)이라 이 프로젝트가 이미 스스로
  경고해온 "반도체/AI장비 섹터 trailing CAGR 과소추정" 패턴과 일치한다
  (CLAUDE.md 기존 기록, 이번 감사가 n=1 추가 확인).
- 이 10건은 **모두 3주 이내 초단기 out-of-sample**이다. 다년 개념(Realistic
  Growth)을 단기 관측으로 검증하는 것 자체가 구조적 한계이며, 이는 없앨 수
  없다 — 다년 성장률은 다년이 지나야 검증된다.
