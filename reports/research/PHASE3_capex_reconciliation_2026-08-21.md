# PHASE 3 — MCK capex 불일치: ledger가 옳고 provider가 좁았다

**날짜** 2026-08-21 · **재현** `scripts/capex_definition_audit_2026_08_21.py` ·
**산출물** `reports/capex_definition_audit_2026-08-21.json` ·
**코드 변경** `engine/data/providers/sec.py` · **테스트** `tests/test_sec_provider.py`(+4건)

**공식 Gap·판정·등급·비중·ledger는 하나도 바꾸지 않았다.**

---

## Finding

RQ-002 부수 소견이 **원인 미확인**으로 남긴 항목:

> MCK: ledger capex 745M vs SEC 436M — ledger가 71% 높다. OCF는 정확히 일치하므로
> 연도 문제가 아니라 정의 차이다(원인 **미확인**).

**규명 완료 — ledger가 옳고 SEC provider가 좁은 정의를 골랐다.**

MCK 8개년 전수 대조(FY2019~FY2026):

```
ledger capex == PaymentsToAcquirePropertyPlantAndEquipment
              + PaymentsToAcquireSoftware                  (8/8 완전 일치)
```

MCK는 FY2020~2025에 대해 그 합을 `PaymentsToAcquireProductiveAssets`(넓은 정의)로
**직접 태깅**하기도 한다. 즉 ledger는 회사가 현금흐름표에 보고하는 **총 자본지출**을
일관되게 쓴다. 반면 `METRIC_TAGS["capex"]`의 우선순위가

1. `PaymentsToAcquirePropertyPlantAndEquipment` ← **좁은 정의**
2. `PaymentsToAcquireProductiveAssets` ← 넓은 정의

이라, 두 태그를 **모두** 보고하는 회사에서 좁은 정의가 채택된다.

## Evidence — 넓은 태그가 있으면 그게 정답이다 (39개년 전수)

| 종목 | 넓은 태그 값이 있는 연도 | ledger와 일치 |
|---|---|---|
| ACGL | 11 | **11/11** |
| MCK | 7 | **7/7** |
| WCN | 9 | **9/9** |
| WM | 12 | **12/12** |

**39/39 일치.** MCK는 `좁은 정의 + 소프트웨어 == 넓은 정의`로 교차확인까지 된다.

## Root cause 분류 (§11)

**B. IRS-wide reconciliation issue** — 단, 범위가 명확하다.

이것은 MCK의 특성이 아니라 **provider 로직의 성질**이다. 넓은 태그를 보고하는
어떤 종목에서도 재발하며, 실제로 34종목 중 3종목(MCK·WCN·WM)에서 이미 발생 중이었다.

⚠️ **P0-07 reconcile 결과의 해석이 뒤집힌다.** P0-07(2026-08-19)은 "capex 28/84
mismatches, 최대 71.9%"를 material divergence로 보고했는데, 그 상당수가
**provider 결함이지 ledger 오류가 아니었다.** "SEC가 1차 자료이니 ledger를 고치자"고
판단했다면 정반대로 갔을 것이다.

## Code Change (§17 gate 통과)

| 게이트 | 판정 |
|---|---|
| 문제 존재 입증 | MCK 8/8 · WM 12/12 · WCN 9/12 실측 |
| 투자판단 영향 | 현재 자본 영향 **0**(provider가 공식 판정 경로에 미배선). 그러나 reconcile 결과가 **틀린 방향을 가리키고 있었다** |
| 원인이 코드에 있음 | `METRIC_TAGS["capex"]` 우선순위 |
| 수정안 명확 | 넓은 정의를 1순위로 |
| regression risk | 넓은 태그가 없는 31종목은 **동작 불변**(폴백) |
| 검증 방법 | 34종목 provider 출력 before/after diff |

**변경 1 — 우선순위 역전**: `PaymentsToAcquireProductiveAssets`를 1순위로.

실측 영향 — **34종목 중 3종목만 변경, 전부 ledger 일치가 개선**:

| 종목 | before | after |
|---|---|---|
| MCK | 0/8 일치 | **7/8** |
| WCN | 7/12 | **11/12** |
| WM | 5/12 | **12/12** |

**변경 2 — 조용히 해결하지 않는다**: 두 정의가 같은 해에 공존하며 값이 다르면
`[capex 정의 공존]` 경고를 남긴다(넓은 쪽을 채택했음과 두 값을 함께 표시).

**변경 3 — 소프트웨어는 자동 합산하지 않는다**: MCK FY2026은 넓은 태그가 아직
없어 좁은 정의(436M)가 채택되는데, 회사 보고 총액은 745M(= 436 + 소프트웨어 309)이다.
**자동으로 더하지 않았다** — 회사에 따라 유형자산 취득에 이미 포함됐을 수 있어
이중계상 위험이 있고, 관측이 **1종목뿐**이라 일반 규칙을 만들 근거가 없다
(§21 LEVEL 1). 대신 `[capex 소프트웨어 별도 보고]` 경고로 누락 가능성을 드러낸다.

## ⚠️ 자체 정정 — 초판 가설을 실측으로 기각했다

조사 초반에 나는 "MCK ledger 시계열 내부에서 capex 정의가 바뀐다(FY2023~2025는
PPE만, FY2026은 PPE+소프트웨어)"고 잠정 판단했다. **틀렸다.** 실제 ledger 값을
확인하니 8/8 전 연도가 `PPE+소프트웨어`로 일관됐다 — 내가 비교표에 옮겨 적은
ledger 값(390/431/537)이 실은 PPE 단독 값이었고, 실제 ledger는 558/687/859였다.

가설이 맞았다면 훨씬 심각한 결함(FCF 수준과 성장률이 다른 정의로 계산됨)이었으므로,
검증 없이 보고했다면 존재하지 않는 문제를 만들 뻔했다.

## Remaining Uncertainty

1. **WCN FY2025 1.28% 차이**(ledger 1,194,366,000 vs SEC 1,179,228,000) —
   그 해에는 넓은 태그가 없고 좁은 정의와도 1.28% 어긋난다. **원인 미확인.**
   WCN은 C등급(유니버스 밖)이라 자본 영향 없음.
2. **MCK FY2026** — 넓은 태그 부재로 여전히 436M(ledger 745M). 경고로만 드러낸다.
3. **나머지 10종목의 capex 불일치**(GWRE 71.9% · MNDY 24.5% 등) — 이들은 넓은 태그도
   소프트웨어 태그도 없고 ledger 값이 SEC 태그 어느 것과도 일치하지 않는다.
   **원인이 다르며 이번 조사 범위 밖**이다(출처 자체가 다를 가능성). 별도 기록.
4. **ledger는 수정하지 않았다** — provider가 개선됐을 뿐이고, 두 값 중 어느 것을
   공식 입력으로 쓸지는 여전히 분석자 판단이다(P0-07 `requires_review` 원칙).

## Validation

| 항목 | 결과 |
|---|---|
| 전체 테스트 | 693 → **697 통과** (신규 4) |
| provider 출력 변경 | 34종목 중 **3종목만**, 전부 ledger 일치 개선 |
| 34종목 골든 재현(8지표) | **불일치 0건** |
| baseline fingerprint | `fbd34322…` **불변** |
| ledger · 매수리스트 | **0건 수정** |
| `ENGINE_VERSION` | v3.59 → **v3.60** (v3.32 규칙: `engine/` 변경 시 상수 갱신) |
