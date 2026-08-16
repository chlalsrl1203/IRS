# Case Results — §59 Master Case Table (축소판)

작성일: 2026-08-16 · 전체 34종목: `data/historical_validation/cases.csv` ·
실관측 6종목 상세: `data/historical_validation/decision_attribution.csv`

## 왜 §59 전체 표를 채우지 않는가

§59가 요구하는 필드(1Y/3Y/5Y Return, Benchmark, Excess Return, Max Drawdown
등)의 상당수는 이 저장소 **34종목 전부**에서 [NOT AVAILABLE]이다 — 데이터
누락이 아니라 시간이 아직 흐르지 않았다(`limitations.md`). 존재하지 않는
값을 N/A로 34행 채우는 건 정보가 없고 표만 길다. 대신 **실제 값이 있는
필드만** 요약하고, 나머지는 이 문서 하단에 "구조적으로 비어있는 이유"로
한 번만 설명한다.

## 34종목 판정 분포(실제 값)

| 판정 | 종목수 |
|---|---|
| 저평가 가능성 | 17 |
| 적정가/경계선 | 15 |
| 과대평가 가능성 | 2 |

## 실관측 6종목 요약(§59 필드 중 실제 값이 있는 것만)

| Ticker | T0 | Historical Decision | Current IRS Decision | Realistic Growth | Implied Growth | Gap | Thesis Result(§36) | Decision Impact | gap_range robust?(v3.51 실측) |
|---|---|---|---|---|---|---|---|---|---|
| TTD | 2026-08-03 | 저평가가능성(S) | 저평가가능성(불변) | 16.70% | −0.31%(2단계) | +17.01%p | **INCORRECT** | **HIGH**(매수리스트 비중 4.80%→2.70%) | robust=True |
| DUOL | 2026-08-02 | 저평가가능성(S) | 불변 | 25.00%(캡) | 5.55% | +19.45%p | CORRECT | LOW(변화없음) | robust=True |
| MNDY | 2026-08-02 | 저평가가능성(S) | 불변 | 25.00%(캡) | 1.72% | +23.28%p | UNRESOLVED | — | robust=True |
| PGR | 2026-08-03 | 저평가가능성(S) | 불변 | 16.87% | −4.89%(음수IG,RAR방향경고) | +21.76%p | PARTIALLY_CORRECT | LOW | robust=True |
| SE | 2026-08-03 | 저평가가능성(S) | 불변 | 23.56%(캡) | 4.38% | +19.18%p | CORRECT | LOW | robust=True |
| TCOM | 2026-08-04 | 저평가가능성(A) | 불변 | 12.39% | 4.84% | +7.55%p | UNRESOLVED(오탐) | — | **robust=False**(단일축 아닌 축 조합효과) |

⚠️ **이전 초안에 있던 오류를 여기서 정정한다**: 초판은 DUOL·SE를 "모델선택
flip 취약"이라 적었으나, `reports/gap_range_2026-08-16.json`을 직접 대조하니
**둘 다 `robust=True`, `flip_drivers` 전부 빈 값**이었다 - 검증 없이 서술한
것이 오류였다. 실제로 이 6종목 중 취약한 것은 **TCOM 하나뿐**이고, 그마저도
단일 축이 아니라 축 조합에서만 발생한다(v3.51 `ablation_analysis.md`의
"조합으로만 뒤집힘 6종목" 그룹에 TCOM이 포함됨).

**"Current IRS Decision"이 전부 "불변"인 이유**: 이 감사는 §63 절차(진짜
재실행 A vs B 비교)를 문자 그대로 수행하지 않았다 — 저장된 ledger의 `growth`/
`implied_growth`는 v3.51 엔진으로 재실행해도 **바뀌지 않음이 34종목 전건
골든재현으로 이미 확인돼 있다**(입력이 동일하므로 v3.19~v3.51 사이 수식
변경이 결과값을 바꾸지 않는 종목들). 즉 이 6건은 "역사적 결정=현재 IRS
재실행"이 우연이 아니라 **입력 자체가 재분석된 적이 없어서** 같다 —
Experiment A와 B가 진짜로는 분리되지 않은 상태다.

## §59가 구조적으로 못 채우는 필드 (34종목 전부)

Revenue/EBIT/FCF/ROIC Actual, 1Y/3Y/5Y Return, Benchmark, Excess Return,
Max Drawdown — **전부 [NOT AVAILABLE], 사유는 `limitations.md`의 STOP
CONDITION 1건**(시간 미경과). `model_improvements.md`가 동결한 34건의
예측이 이 공백을 앞으로 메울 후보다.
