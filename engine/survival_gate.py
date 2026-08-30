"""
survival_gate.py (2026-08-30) — 1차 스크리닝의 "B" 게이트: 극단적 존속위험만 거른다.

## 이 게이트가 존재하는 이유 — v3.19가 이미 겪은 실패를 반복하지 않는다

`engine/screener.py`에는 이미 다음 경고가 있다:

    최초 구현은 순부채/EBITDA<=2.5, 최악YoY>=-5%를 **하드 필터**로 걸었는데,
    이는 check_deceleration_double_count가 경고하는 것과 같은 유형의
    **이중 반영**이었다. 레버리지와 경기민감도는 이미 DRS -> ERP -> r ->
    내재성장률 경로로 반영되고 있어 별도 컷을 또 걸면 같은 증거로 두 번
    페널티를 준다. 실제로 이 때문에 BRO(3.50배)와 BSY(2.63배)가 탈락했는데
    둘 다 실전에서 저평가 판정이 난 종목이었다.

이 게이트는 **그 실수를 반복하지 않는다.** DRS가 이미 연속적으로(하드컷이
아니라 스코어로) 다루는 축 — 레버리지 비율, 매출변동성, 경기민감도,
마진변동성, 경쟁강도 — 은 여기서 절대 다시 컷하지 않는다. 대신 DRS가
원리적으로 볼 수 없는 것만 거른다: **장부(자기자본)와 현금흐름이 동시에
잠식되는 상태**, 즉 재무제표 두 축이 동시에 파산 방향을 가리키는 경우다.

## 왜 "자기자본 마이너스" 단독으로는 안 되는가

자기자본이 마이너스인 것 자체는 부실의 증거가 아니다. AutoZone·Domino's·
Colgate·MCD 같은 우량기업도 공격적 자사주매입으로 장부상 자기자본이
마이너스인 경우가 흔하다 — 이들은 영업현금흐름이 강하게 플러스라 재무적
위험과 무관하다. 자기자본 마이너스만으로 거르면 정확히 이런 우량주를
대거 오탈락시킨다(BRO/BSY와 같은 유형의 사고 재발).

## 이 게이트의 기준

**최근 회계연도 기준 (자기자본 < 0) AND (영업현금흐름 < 0)**일 때만 거른다.
장부도 잠식되고 현금도 유출되는 상태는 자사주매입형 마이너스 자기자본과
명확히 구분되는 실제 존속위험 신호다. 둘 중 하나만 마이너스면 통과시킨다.

## 데이터가 없으면 거르지 않는다

`is_insurer`/`sbc_cross_check`와 동일한 원칙 — 데이터 부재를 "위험 없음"이
아니라 "판단 불가"로 취급한다. 자기자본 태그가 없는 종목(예: 20-F 외국발행사,
XBRL 태깅 이전 시기)은 이 게이트를 통과시키되, 그 사실을 사유로 남긴다.

## 아직 배선되지 않은 것 — 의도적으로

Going concern(감사의견 미확인 존속능력 우려) 문구 탐지는 구조화 XBRL로는
불가능하고(텍스트 마이닝이 필요), 대규모 스크리닝(현재 1,200~1만종목) 규모에서
비용이 너무 크다. 지금은 구조화 데이터로 확인 가능한 최소 신호만 쓴다.
"""


def extreme_survival_risk(shareholders_equity_by_year, operating_cashflow_by_year):
    """
    최근 회계연도 기준 (자기자본<0 AND 영업현금흐름<0)이면 (True, 사유),
    아니면 (False, 사유_또는_None).

    두 시계열의 "최근 연도"가 다를 수 있다(자기자본은 instant, OCF는
    period라 공시 주기가 다를 수 있음) — 각자의 최신 연도를 독립적으로 쓴다.
    """
    if not shareholders_equity_by_year or not operating_cashflow_by_year:
        return False, "자기자본 또는 영업현금흐름 데이터 미확보 - 게이트 미적용"

    latest_eq_year = max(shareholders_equity_by_year)
    latest_ocf_year = max(operating_cashflow_by_year)
    eq = shareholders_equity_by_year[latest_eq_year]
    ocf = operating_cashflow_by_year[latest_ocf_year]

    if eq < 0 and ocf < 0:
        return True, (
            f"극단적 존속위험: 자기자본 마이너스(FY{latest_eq_year}: "
            f"{eq:,.0f}) AND 영업현금흐름 마이너스(FY{latest_ocf_year}: "
            f"{ocf:,.0f}) — 자사주매입형 마이너스자본과 구분되는 신호")
    return False, None
