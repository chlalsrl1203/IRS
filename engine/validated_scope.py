"""
validated_scope.py (2026-08-30) — 스크리너 결과가 **검증된 범위 안인지** 표시한다.

## 왜 필요한가

`engine/screener.py`의 임계값(`MIN_REALISTIC_GROWTH`=8%, `MAX_IMPLIED_GROWTH`=5.5%,
tier 경계)과 `estimate_drs()`의 상수 대체값(competition_intensity=12.0,
margin_volatility=8.0 등)은 **전부 34종목 ledger 코퍼스에서 나왔다.** 그 코퍼스의
실측 관측범위는 좁다:

    Gap        : -14.36%p ~ **+24.38%p**   (최대 ACGL)
    시가총액   : **$3.74B**(MNDY) ~ $817.9B (중앙값 $42.6B)

그런데 2026-08-30 첫 전체 유니버스 실행(8,897종목)의 통과 목록에는 Gap
**+93%p**(코퍼스 최대의 3.8배)와 시총 **$10M**(코퍼스 최소의 1/374)이 들어 있다.
즉 한 번도 검증된 적 없는 구간에 코퍼스 상수를 그대로 외삽하고 있다.

BSX 거짓탈락 사건이 같은 구조였다 - `estimate_drs`가 중앙값(12.0)으로 대체하는
competition_intensity가 BSX 실제값(5.4)과 크게 달라 판정이 뒤집혔다. 그때는
중앙값에서 벗어난 **한 종목**이었고, 지금은 코퍼스 **범위 자체를 벗어난 집단**이다.

## ⚠️ 거르지 않는다 — 표시만 한다

`is_insurer`·`sbc_cross_check`·`holdings_overlap`과 동일한 "병기, 자동판정 안 함"
원칙이다. 범위 밖이라는 것이 "틀렸다"는 뜻은 아니다 - **확인된 적이 없다**는
뜻이다. 컷오프를 새로 만들면 이 프로젝트가 반복해서 금지해온 짓(근거 없이
유지하던 값을 근거 없는 다른 값으로 교체)을 하는 것이 된다.

## ⚠️ 실측으로 답하려 했으나 도구가 편향돼 있었다

PIT 백테스트(6개 T0)로 "범위 밖에서도 스크린이 작동했는가"를 재보니 오히려
소형주가 더 나은 수익률을 보였다(중앙값 +237.7% vs 범위내 +76.0%). **그러나
이 수치는 신뢰할 수 없다** - 백테스트 유니버스가 SEC의 **오늘자** 티커 목록에서
만들어지는데, 2018-06-30 시점 상장주식 5,773개 중 **2,321개(40.2%)가 이후
상장폐지됐고 그중 2,148개는 오늘 목록에 없다.** 즉 죽은 회사만 통째로 빠진
표본이라 수익률이 위로 편향돼 있고, 폐지율이 높은 소형주 구간이 특히 심하다.

따라서 **범위 밖 구간의 유효성은 현재 미검증 상태로 남는다.** 이 모듈은 그
사실을 결과에 드러내는 역할만 한다(상세: `scripts/diagnose_screen_scope_
2026_08_30.py`, `reports/research/screen_scope_diagnosis_2026-08-30.json`).
"""

# 34종목 ledger 코퍼스의 **실측** 관측범위. 임의로 고른 컷오프가 아니라
# "지금까지 정식 분석으로 확인해본 적이 있는 구간"의 경계다.
# 코퍼스가 늘어나면 이 값도 갱신해야 한다(그때는 실측으로).
CORPUS_GAP_MAX = 0.2438           # ACGL +24.38%p
CORPUS_GAP_MIN = -0.1436          # KEYS -14.36%p
CORPUS_MARKET_CAP_MIN = 3.74e9    # MNDY $3.74B
CORPUS_MARKET_CAP_MAX = 817.9e9   # PDD $817.9B

VALIDATION_STATUS = {
    "corpus_range": (
        "OBSERVED_RANGE_ONLY - 34종목 ledger의 실측 최소·최대일 뿐이며, 이 "
        "범위 안이라고 판정이 옳다는 뜻이 아니다. 범위 밖 구간의 유효성은 "
        "생존편향 40.2% 때문에 현재 실측 불가."),
}


def out_of_scope_reasons(gap=None, market_cap=None):
    """
    검증 코퍼스 관측범위를 벗어난 축을 문자열 리스트로 돌려준다.
    범위 안이거나 값이 없으면 빈 리스트 - **거르지 않는다.**
    """
    reasons = []
    if gap is not None:
        if gap > CORPUS_GAP_MAX:
            reasons.append(
                f"Gap {gap * 100:+.1f}%p가 코퍼스 최대(+{CORPUS_GAP_MAX * 100:.1f}%p)의 "
                f"{gap / CORPUS_GAP_MAX:.1f}배 - 검증된 적 없는 구간")
        elif gap < CORPUS_GAP_MIN:
            reasons.append(
                f"Gap {gap * 100:+.1f}%p가 코퍼스 최소({CORPUS_GAP_MIN * 100:.1f}%p) 아래")
    if market_cap is not None and market_cap > 0:
        if market_cap < CORPUS_MARKET_CAP_MIN:
            reasons.append(
                f"시총 ${market_cap / 1e9:.2f}B가 코퍼스 최소(${CORPUS_MARKET_CAP_MIN / 1e9:.2f}B)의 "
                f"1/{CORPUS_MARKET_CAP_MIN / market_cap:.0f} - estimate_drs의 중앙값 "
                f"대체가 이 규모에서 검증된 적 없다")
        elif market_cap > CORPUS_MARKET_CAP_MAX:
            reasons.append(
                f"시총 ${market_cap / 1e9:.0f}B가 코퍼스 최대(${CORPUS_MARKET_CAP_MAX / 1e9:.0f}B) 위")
    return reasons
