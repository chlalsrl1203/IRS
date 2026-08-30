"""
after_cost.py (2026-08-29) — 총수익을 한국 투자자의 **실수령**으로 환산한다.

## 왜 필요한가

PIT 성적표(`scripts/pit_scorecard.py`)는 배당조정 총수익 기준이라 "거래비용·
세금 미반영"을 한계로 명시하고 있었다. 그런데 이 저장소의 사용자는 한국에서
해외주식을 사므로, 총수익과 실수령의 차이가 **작지 않다**:

  - 해외주식 양도소득세 **22%**(지방소득세 포함), 연 **250만원 기본공제**
  - 환전 스프레드(원↔달러 왕복)
  - 매매 수수료

특히 양도세는 **수익에만** 붙는 비대칭 비용이라, 수익률이 높은 그룹일수록
더 많이 깎인다. 즉 flagged가 not_flagged보다 총수익이 높다면 **세후 격차는
반드시 총수익 격차보다 작다.** 성적표를 총수익으로만 읽으면 실제 우위를
과대평가한다.

## ⚠️ 이 모듈이 하지 않는 것 - 세무 자문이 아니다

세법은 개인 상황(다른 소득, 손익통산, 연도별 실현 시점, 계좌 종류)에 따라
달라진다. 여기 있는 것은 **단일 시나리오 계산기**일 뿐이며 다음을 가정한다:

  1. T0에 사서 최신 시점에 **한 번에 전량 매도**(중간 매매 없음)
  2. 그 해에 이 매도 외 다른 해외주식 양도차익이 없음
  3. 손실 종목의 손익통산을 **적용하지 않음**(종목별 독립 계산)
  4. 배당소득세는 별도로 반영하지 않음(가격이 배당조정이라 배당이 수익에
     포함돼 있으나, 배당은 양도세가 아니라 배당소득세 대상이다 - 이 차이는
     **미반영**이며 아래 한계에 명시한다)

가정 3은 **보수적인 방향이 아니다** - 손익통산을 하면 세금이 줄어 실수령이
늘어난다. 즉 이 계산은 손실 종목이 많은 그룹에 불리하게 작동한다. 그래서
그룹 비교에는 `apply_offset=True`(그룹 내 손익통산)도 함께 낸다.

## 세율·공제는 상수로 두되 근거를 남긴다

이 프로젝트는 근거 없는 상수를 싫어하지만, 세율은 **법으로 정해진 값**이라
추정이 아니다. 다만 법은 바뀌므로 확인 시점을 함께 기록한다.
"""

# 해외주식 양도소득세율(지방소득세 포함). 2026-08-29 기준 통용되는 값을
# 상수로 둔다. ⚠️ 세법은 개정되므로 이 값을 그대로 신뢰하지 말고 실제
# 신고 시점의 세율을 확인할 것.
CAPITAL_GAINS_TAX_RATE = 0.22

# 연간 기본공제(원). 양도차익에서 먼저 빼고 과세한다.
ANNUAL_EXEMPTION_KRW = 2_500_000

# 환전 왕복 스프레드(매수 시 원→달러, 매도 시 달러→원). 증권사·우대율에
# 따라 크게 다르므로 **기본값은 보수적으로** 잡고 호출부가 바꿀 수 있게 한다.
FX_SPREAD_ROUNDTRIP = 0.002      # 0.2%

# 매매 수수료 왕복. 온라인 해외주식 기준 대략치이며 증권사마다 다르다.
COMMISSION_ROUNDTRIP = 0.002     # 0.2%

VALIDATION_STATUS = {
    "tax_rate": ("LEGAL_CONSTANT - 추정이 아니라 법정 세율(2026-08-29 확인). "
                 "다만 세법 개정 가능성이 있어 신고 시점 재확인 필요"),
    "fx_spread": ("UNVALIDATED_DEFAULT - 증권사·우대율에 따라 0.02%~1%까지 "
                  "차이난다. 기본값 0.2%는 보수적 가정이며 실측치가 아니다"),
    "commission": ("UNVALIDATED_DEFAULT - 증권사마다 다르다. 기본값 0.2%는 "
                   "보수적 가정이며 실측치가 아니다"),
}


def after_cost_return(gross_return_pct, principal_krw=10_000_000,
                      tax_rate=CAPITAL_GAINS_TAX_RATE,
                      exemption_krw=ANNUAL_EXEMPTION_KRW,
                      fx_spread=FX_SPREAD_ROUNDTRIP,
                      commission=COMMISSION_ROUNDTRIP,
                      apply_exemption=True):
    """
    총수익률(%) -> 세후·비용후 수익률(%).

    principal_krw: 이 종목에 넣은 원금. 기본공제가 **금액** 기준이라
    수익률만으로는 세후 수익률이 정해지지 않는다 - 원금이 클수록 공제
    효과가 희석된다. 이 의존성 자체가 중요해서 인자로 드러낸다.

    apply_exemption=False로 두면 공제를 적용하지 않는다(여러 종목을 합산해
    공제를 한 번만 적용하려는 호출부용).
    """
    if principal_krw <= 0:
        raise ValueError("principal_krw는 0보다 커야 한다")

    # 왕복 거래비용은 원금과 매도대금 양쪽에 걸리므로 근사적으로 총액에 적용
    cost_rate = fx_spread + commission
    gross = gross_return_pct / 100.0
    proceeds = principal_krw * (1 + gross) * (1 - cost_rate / 2)
    invested = principal_krw * (1 + cost_rate / 2)

    gain = proceeds - invested
    if gain > 0:
        taxable = gain - (exemption_krw if apply_exemption else 0)
        tax = max(taxable, 0) * tax_rate
    else:
        # 손실이면 양도세 없음(손익통산은 이 함수 밖에서 다룬다)
        tax = 0.0
    net = proceeds - tax
    return (net / principal_krw - 1) * 100.0


def portfolio_after_cost(gross_returns_pct, total_principal_krw=10_000_000,
                         tax_rate=CAPITAL_GAINS_TAX_RATE,
                         exemption_krw=ANNUAL_EXEMPTION_KRW,
                         fx_spread=FX_SPREAD_ROUNDTRIP,
                         commission=COMMISSION_ROUNDTRIP,
                         offset_losses=True):
    """
    동일가중 포트폴리오의 세후 수익률(%).

    offset_losses=True면 **그룹 내 손익통산**을 적용한다 - 같은 해에 전량
    매도하는 시나리오이므로 손실 종목이 이익 종목의 과세표준을 줄인다.
    이걸 끄면 손실 종목이 많은 그룹이 불리하게 나오므로, 그룹 비교에는
    켜는 쪽이 공정하다.
    """
    n = len(gross_returns_pct)
    if n == 0:
        return None
    per = total_principal_krw / n
    cost_rate = fx_spread + commission

    invested = sum(per * (1 + cost_rate / 2) for _ in gross_returns_pct)
    proceeds = sum(per * (1 + g / 100.0) * (1 - cost_rate / 2)
                   for g in gross_returns_pct)

    if offset_losses:
        gain = proceeds - invested
        taxable = max(gain - exemption_krw, 0)
        tax = taxable * tax_rate
    else:
        tax = 0.0
        for g in gross_returns_pct:
            p = per * (1 + g / 100.0) * (1 - cost_rate / 2)
            i = per * (1 + cost_rate / 2)
            if p > i:
                tax += (p - i) * tax_rate      # 공제는 종목별로 주지 않는다
    net = proceeds - tax
    return (net / total_principal_krw - 1) * 100.0
