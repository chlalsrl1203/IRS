# CHANGELOG

## v3.19 RAR 전수감사 7종목 전건 처리 완료 (2026-07-26)

2026-07-25 전수감사에서 나온 소수규약 의심 7종목(VRSN/WCN/WM/IDXX/BRO/
ZTS(v3.15판)/DVN(프로포르마))을 전건 처리했다. 앞의 5종목(VRSN/WCN/WM/IDXX/
BRO)은 이미 SEC EDGAR 원본으로 완전 재검증했고(별도 항목 참고), 나머지
2건을 오늘 마무리했다:

- **ZTS(v3.15판)**: ledger가 없어(원 입력값 소실) 독립 재현검증은 불가능했다.
  RAR×DRS 함의 기대수익률(0.09%→8.98%, 정정 후 정상범위 진입)만으로 같은
  100배 스케일 오류로 판단해 +0.0022→+0.22로 기계적 정정만 적용했다. 이
  종목은 이미 이번 세션에서 완전한 v3.19 재분석(RAR +0.1425, Confidence 94,
  ledger/ZTS_2026-07-25.json)이 트래커에 존재하므로, 이 v3.15 ad-hoc 행은
  사실상 폐기 권장으로 표시하고 향후 참조를 v3.19판으로 유도했다.
- **DVN(프로포르마)**: 마찬가지로 ledger 부재로 기계적 정정만
  적용(+0.0007→+0.07). 이 분석은 애초에 Devon-Coterra 합병 직후 결합
  10-Q(2026-08-04 예정) 발표 전 예비 스크리닝으로 Confidence 25(최저권)
  라 투자판단 근거로 쓰지 말라고 명시돼 있었고, 그 성격은 이번 RAR
  정정으로도 바뀌지 않는다. 실측 기반 전면 재검증은 계획대로 8/4 발표 후
  진행한다(오늘 2026-07-26 기준 아직 발표 전이라 물리적으로 불가능).

이 2건은 5건과 달리 "다른 지표도 거의 그대로 재현되는지" 독립 검증을 하지
못했다는 점을 트래커에 명시했다 — ledger가 없는 과거 기록은 스케일 오류
여부는 판별 가능해도 전면 재현검증은 근본적으로 불가능하다는 걸 보여주는
사례다(v3.19 Ledger 필드 의무화의 배경이기도 하다).

이로써 2026-07-25 감사에서 나온 7건 전체가 처리 완료됐다.

## v3.19 강건성점검(sensitivity_check) 모델불일치 근본 수정 (2026-07-26)

같은 날 앞서 추가한 [강건성점검 해석주의] 경고문은 임시 우회책이었다("근본
수정은... 엔진 원본 함수 시그니처를 건드리는 범위라 보류 중"). 사용자 요청으로
근본 수정을 진행했다.

**수정**: `expectation_gap_sensitivity_check()`에 `model_used` 파라미터를
추가(기본값 `"two_stage"`로 과거 호출 하위호환 유지). 내부에서 이제
`model_used`에 따라 `implied_growth_single_stage()` 또는
`implied_growth_two_stage()`를 선택해서 쓴다. `pipeline.py`가
`inputs.model_used`(Section 5가 실제로 쓴 모델)를 그대로 넘기도록 수정하고,
더 이상 필요 없어진 [강건성점검 해석주의] 임시 경고문 블록은 제거했다.

**실제 영향 확인** (9종목 전체를 저장된 ledger 입력값으로 재실행해 대조):
RAR·Gap·판정은 9종목 모두 완전히 동일(이 부분은 애초에 sensitivity_check와
무관한 경로였다). 그러나 **WCN/WM/IDXX 세 종목은 confidence와 강건성점검
flip 상태가 실제로 바뀌었다** - 이는 "우연히 값이 같았다"가 아니라 이 셋이
정확히 가설대로(single_stage + 큰 모델괴리) 영향받은 사례였다는 뜻이다:

| 종목 | flip(구)→(신) | Confidence(구)→(신) |
|---|---|---|
| WCN | True→**False** | 59→**74** |
| WM  | True→**False** | 64→**79** |
| IDXX| True→**False** | 59→**74** |

즉 이 세 종목의 "강건성점검 flip"은 처음부터 DRS 민감도가 아니라 순수히
sensitivity_check가 Section 5와 다른 모델(two_stage)을 썼기 때문에 발생한
가짜 신호였다. 근본 수정 후 셋 다 robust로 판정되고 confidence가 15점씩
올랐다. CDNS/MNST/ZTS/PH/VRSN/BRO 6종목은 (two_stage를 쓴 PH 포함) 전혀
영향받지 않았다.

테스트: `test_engine.py`에 model_used 라우팅/기본값 하위호환/잘못된 값 거부
3건 추가. `test_pipeline.py`의 기존 2건(임시 경고문 검증용)을 삭제하고
sensitivity_check가 Section 5와 같은 모델을 쓰는지 직접 검증하는 3건으로
교체. 전체 58개 테스트 통과.

WCN/WM/IDXX ledger를 재생성(2026-07-26)하고 Notion 트래커의 강건성점검
필드·Confidence·핵심노트를 정정했다.

## v3.19 강건성점검(sensitivity_check) 모델불일치 경고 추가 (2026-07-26, 대체됨)

**⚠️ 위 근본수정 항목으로 대체됨 - 아래는 그 전 단계의 임시 우회책 기록으로만
남긴다.**

WM/IDXX/WCN 재검증 결과를 다시 점검하다가 `expectation_gap_sensitivity_check()`가
엔진 원본 구현상 **항상 two_stage 모델로만 판정**한다는 것을 발견했다. 이 셋은
모두 Section 5에서 `model_used="single_stage"`를 썼고 두 모델 괴리가 6.5~7.5%p로
큰데, 강건성점검은 그와 무관하게 항상 two_stage로 재계산해 flip 여부를 판정하고
있었다. 즉 "강건성점검에서 flip됐다"는 라벨이 DRS 민감도 때문인지, 애초에 Section
5와 다른 모델을 쓴 결과인지 구분되지 않는 상태였다.

`run_analysis()`에 조건부 경고를 추가: `model_used != "two_stage"` AND 모델괴리
≥3%p AND `judgment_flipped=True`이면 `data_limitations`에 `[강건성점검 해석주의]`
문구를 남긴다. WCN/WM/IDXX 3종목 모두 이 조건에 해당해 신규 경고 1건씩 발생,
VRSN/BRO는 flip이 아니라서 발생하지 않음을 ledger 재생성으로 확인했다(5종목
전부 RAR·판정값은 기존과 완전히 동일 — 이번 변경은 해석 주석만 추가하는 순수
가산적 변경).

테스트 2건 추가(CDNS 골든케이스로 flip+괴리 조합 시 경고 발생, two_stage
사용 시 경고 미발생). 전체 54개 테스트 통과.

**미해결로 남긴 것**: 이 경고는 fix가 아니라 주석이다 — sensitivity_check 자체가
model_used를 인자로 받아 같은 모델로 재계산하도록 고치는 것이 근본 해결이지만,
엔진 원본 함수 시그니처를 건드리는 범위라 이번엔 손대지 않았다. 향후 필요시
검토할 것.

## v3.19 VRSN/WCN/WM/IDXX/BRO 5종목 재검증 및 오류 정정 (2026-07-25)

RAR 전수 감사(아래 항목)에서 나온 소수규약 의심 7종목 중 5종목을 SEC EDGAR
원본 10-K(as-filed R.htm)로 재계산했다.

- **VRSN/BRO/IDXX**: RAR 외 모든 지표(Implied Growth, Realistic Growth,
  Gap, Lynch유형)가 오차 1%p 이내로 재현됨 — 소수규약 오류라는 진단이
  확정적으로 입증됨. 정정: VRSN -0.0038→-0.2675, BRO +0.0030→+0.3492,
  IDXX -0.0068→-0.4886. 판정 불변.
- **WCN/WM**: RAR 스케일 오류는 동일하게 확인되나(WCN -0.0055→-0.2718,
  WM -0.0060→-0.2863), FCF CAGR이 과거 기록과 크게 벌어져(WCN 5.04%→
  9~10%대, WM 2.60%→9.72%) 5개 조회창을 테스트해도 재현되지 않았다.
  **처음엔 "FY2025 10-K가 새로 나와서"라고 설명했으나 이는 오판이었다** —
  두 종목의 FY2025 10-K는 각각 2026-02-09/2026-02-12 제출되어 과거
  분석일(2026-07-18)보다 5개월 앞선다. 진짜 원인은 확인하지 못한 채
  "원인불명"으로 정정 기록했다(CLAUDE.md에 이 실수 자체를 교훈으로 남김).
  WM은 추가로 Lynch유형이 자동분류상 Stalwart→Cyclical로 재분류됨
  (cyclicality 12.6→16.8, 12년 조회창에 2015년 실제 역성장 -7.39% 포함).

부수 발견: Fiscal.ai는 capex를 음수(현금유출)로 반환해 `fcf = ocf - capex`
계산 시 부호가 반대로 들어가면 FCF가 2×capex만큼 과대계상되는 함정이 있어
`AnalysisInputs`에 가드 추가(음수 capex 입력 시 거부). SEC XBRL
`companyconcept` API도 자체 오류가 있음을 발견(WM 2021 capex: API $2,039M
vs as-filed 10-K $1,904M) — 원본 제출서류가 API 집계값보다 신뢰도가 높다.

## v3.19 트래커 RAR 전수 감사 (2026-07-25)

`rar()` 단위 함정을 고친 뒤, **과거 기록도 같은 병에 걸려 있는지** 트래커
74건을 전수 점검했다. ledger가 없어 재계산은 불가능하지만, `RAR × DRS`가
함의하는 기대수익률의 현실성으로 판별할 수 있다.

결과: **7건이 소수 규약(100배 축소)으로 기록됨** — VRSN(큐18), WCN(큐26),
WM(큐27), IDXX(큐25), BRO(큐28), ZTS(v3.15판), DVN(프로포르마).
정상 59건의 함의 기대수익률은 1.7~110%(중앙값 19%)인데, 이 7건은 전부
|0.3%| 미만으로 비현실적이다. 버전 분포는 v3.13 4건 / v3.15 2건 / v3.16 1건.

**중요한 2차 영향**: 이 7건은 대부분 "stalwart 구조적 편향"(v3.13) 사례로
인용돼온 행들이다. 편향 주장 자체는 *부호*에 관한 것이라 100배 스케일
오류에도 영향받지 않아 **여전히 유효**하다. 그러나 다음 서술들은 서로 다른
규약의 값을 비교한 결과이므로 근거가 되지 않는다:
- WCN "낙폭 최대", "DRS 높을수록 two_stage 편향 증폭 추정"
- IDXX/WM "6번째/8번째 사례" 누적 카운트(FICO/SPGI/MSCI/Keyence는 퍼센트 규약)
- BRO "stalwart 9종목 중 유일 양수"(+0.0030 → 퍼센트 규약이면 +0.30으로
  '간신히 양수'가 아니라 '양호한 양수')

7건 모두 트래커 RAR 필드에 감사 표시를 달았다(원 값은 보존). ledger가 없어
재계산은 불가하므로, **해당 종목을 재검증할 때 확인**한다.

## v3.19 (반영일: 2026-07-25) — RAR 단위 함정 수정

**버전번호 주의**: v3.17/v3.18을 건너뛰고 v3.19를 쓴다. 두 라벨은 이미 Notion
트래커에서 다른 작업(아래 CLAUDE.md 참고)에 사용 중이라, 같은 번호에 다른 내용을
넣으면 v3.12 때와 같은 "가짜 버전" 혼란이 재발한다.

`rar()`의 단위 규약이 암묵적이어서 **조용히 100배 틀리는 함정**이 있었음을
2026-07-25 감사에서 발견. 경위:

- `scenario_return_from_growth()`와 `expected_return()`은 **소수**를 반환(-0.2239)
- `rar(expected_return_pct, drs)`는 파라미터명이 `_pct`이고 실제 컨벤션도 **퍼센트 숫자**(-22.39)
- 따라서 `rar(expected_return(...), drs)`로 자연스럽게 연결하면 100배 작은 값이
  아무 경고 없이 산출됨

실제로 이 세션에서 CDNS/MNST/ZTS/PH 4종목이 이 실수로 잘못 기록됐다(CDNS
-0.006 vs 정답 -0.5994 등). 트래커에 축적된 과거 RAR 값들(ADBE 1.7231,
CSU 1.6564, ACGL 3.003, ANET 0.5895 등)은 모두 퍼센트 컨벤션이 맞았고, 이번
오류는 신규 발생분이었다. 4건 모두 Notion에서 정정 완료(부호는 불변이라
판정·편향플래그·Confidence는 변화 없음).

조치(v3.15/v3.16과 동일 원칙 — 문서가 아니라 코드로 막는다):
- `rar()`에 가드 추가: `|expected_return_pct| < 1.0`이면 소수를 잘못 넣은 것으로
  간주해 ValueError. 진짜로 ±1% 미만이면 `allow_sub_one_pct=True` 명시 필요.
- `rar_from_decimal_return()` 신규: `expected_return()`의 소수 출력을 그대로 받아
  내부에서 100을 곱한다. 권장 경로.
- 단위 규약과 이번 사고 경위를 docstring에 명문화.
- 회귀 테스트 5건 추가(퍼센트 정상동작, 소수 거부, 명시적 예외 허용,
  두 경로 일치, expected_return 체이닝 안전성).

## v3.16 (반영일: 2026-07-25) — v3.9→v3.16 재구성 완료

confidence_score()를 v3.15와 동일한 원칙으로 하드닝. robustness_check_passed/
section_5_7_aligned 순수 bool 파라미터를 제거하고, expectation_gap_sensitivity_check()의
실제 반환 dict(sensitivity_check_result)와 gap/rar 실수치를 직접 받아 함수
내부에서 정합성을 계산하도록 변경. 구 방식 호출은 TypeError.

claim/lock 프로토콜을 CLAUDE.md에 문서화(원 배경: VRSN/ROP 중복 분석 사고).

**이번 재구성 전체 요약**: v3.9(검증된 원문 복원) → v3.13(stalwart+two_stage
구조적 편향 플래그, 원문 그대로) → v3.14(confidence_score 최초 도입, 원본
소실로 스펙 기반 재설계) → v3.15(self_check_v2로 장식용 검증 교체) →
v3.16(confidence_score 하드닝 + claim/lock 프로토콜). v3.10/3.11/3.11.1/3.12는
근거 없어 결번 처리, v3.17/3.18은 이 저장소에 어떤 형태로도 존재하지 않아
사용 보류.

## v3.15 (반영일: 2026-07-25)

run_self_check(answers: dict)가 장식용(decorative)이었음이 감사로 확인됨 —
불리언 자기신고만 받고 메모 텍스트를 전혀 검증하지 않아, 18개 호출
인스턴스 전체에서 실질적 검증 기능을 하지 못했음. self_check_v2.py 신규
도입: run_self_check_v2(memo_text, ctx)가 메모 원문에서 Implied
Growth/Realistic Growth/Expectation Gap/DRS/RAR 수치를 직접 파싱해 계산
컨텍스트와 대조하고, Bear Case 섹션·최종 결론 존재 여부까지 검증하는 7개
실제 체크를 수행. 기존 run_self_check()는 DEPRECATED 표시 후 코드에는
보존(과거 메모 참고용), 신규 분석에서는 사용 금지.

## v3.14 (반영일: 2026-07-25)

confidence_score() 신규 도입. **주의: 이 함수의 원래 원본 코드는 세션
파일시스템 리셋으로 소실되어 존재하지 않음.** 남아있던 근거는 스펙 조각뿐
(base=50 확정, base=70은 점수가 80~90대에 몰려 구분력 상실 확인됨, ANET
종목에서 최초 재현 Confidence=71). 2026-07-25에 이 스펙에 맞춰 가산/감산
항목을 새로 설계해 재구성. 원본과 정확히 같다는 보장 없음 — 향후 재검증
시 이 사실을 감안할 것.

## v3.13 (반영일: 2026-07-25, 원 배경: CTAS/AME 등 실전 stalwart 분석)

stalwart 유형이 two_stage 모델에서 구조적으로 음수 RAR을 보이는 패턴을
확인. min_spread 가드가 거의 모든 stalwart 기본 시나리오에서 발동하는
것이 원인. 모델은 그대로 유지하되(model="two_stage" 기본값), 이 편향을
`check_stalwart_two_stage_bias()`로 감지해 메모에 명시적으로 플래그하도록
강제. 근본 원인을 숨기지 않고 문서화하는 방향으로 대응(v3.16 이후 정신과
동일 원칙 선반영).
