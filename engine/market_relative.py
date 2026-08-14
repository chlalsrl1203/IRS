"""
Market-Relative Gap (v3.45 신규, 2026-08-13) - 회사 Gap을 "시장(VOO)을 그냥
사는 것" 대비로 다시 읽는다.

**왜 만들었나 - "이 종목이 싼가, 시장 전체가 싼가"라는 질문에 이 프로젝트는
아직 답한 적이 없다.** 회사 엔진의 Gap은 절대적 진술이라("+17.01%p 저평가"),
시장 전체가 이미 재평가된 상태라면 그 절대값이 실제로 뭘 뜻하는지 기준이
없었다. ETF 엔진(v3.33~)이 계산하는 VOO의 시장요구성장(breakeven, ≈7.07%)이
정확히 그 기준선인데, 두 엔진이 만들어진 이후 한 번도 연결된 적이 없었다.

## ⚠️ 이것은 "체계적 vs 고유" 요인분해가 **아니다** - 정직하게 못박는다

처음 구상은 팩터모델처럼 Gap을 "시장 재평가분 + 종목 고유분"으로 가르는
것이었으나, 실제로 짜보니 그 분해는 **이 코드베이스의 구조상 정당화할 수
없다는 걸 확인했다**: 회사 엔진의 할인율 r은 DRS(개별 위험도)에서, ETF
엔진의 r은 ERS(지수 위험도)에서 나오며 **공유하는 계산 경로가 전혀 없다**
(팩터모델이라면 공통 베타·공통 할인율원천이 있어야 "시장이 움직이면 이만큼
같이 움직인다"는 인과적 분해가 성립하는데, 이 두 엔진은 애초에 독립적으로
설계됐다). 그래서 이 모듈이 실제로 하는 건 훨씬 더 겸손하고 더 정직한
비교다 - **"이 종목 vs 그냥 인덱스(VOO)를 사는 것"이라는 벤치마크
차감**이다. 투자자의 실제 선택지가 "이 종목이냐 시장 평균 공정가치냐"가
아니라 "이 종목이냐 그냥 VOO를 사느냐"이므로, 오히려 이쪽이 실무적으로
더 맞는 질문이기도 하다.

## ⚠️ 분자가 다르다는 한계도 명시한다

회사 엔진의 Implied Growth는 **FCF** 기반 Gordon 역산이고, ETF 엔진(VOO)의
Implied Growth는 **이익(EPS)** 기반 Gordon 역산이다. 둘 다 "현재가를
정당화하려면 필요한 장기 성장률"이라는 같은 **개념**의 값이지만, FCF
성장과 이익 성장은 일반적으로 다르다(capex·운전자본 차이). 그래서 이 모듈이
내놓는 수치는 **레벨(절대값)로 "저평가폭이 정확히 몇 %p 더 크다"까지
정밀하게 읽으면 안 되고**, 방향과 대략적 크기(상대적 순위)만 신뢰할 것 -
이 프로젝트가 다른 곳에서 이미 반복해온 "단일 지표를 검증 없이 확정하지
말 것" 원칙과 같은 계열의 주의다.

## 무엇을 계산하는가

  - `relative_gap`  = Gap_company - Gap_VOO  ("VOO를 사는 것보다 이 종목이
    몇 %p 더/덜 싸 보이는가")
  - `growth_premium` = Implied_Growth_company - Implied_Growth_VOO ("시장이
    이 종목에 시장평균보다 몇 %p 더/덜 낙관적인 성장을 이미 가격에
    반영했는가" - Gap과는 다른 축이다. Growth Premium이 깊은 음수인데
    Gap도 크게 양수인 종목은 "시장이 이 종목을 시장평균보다 비관적으로
    보고 있는데, 그 비관이 실제 펀더멘털보다 과하다"는 조합이라 해석이
    분명하다.

VOO 쪽 값은 **가장 비싼 P/E(=가장 높은 Implied Growth) 기준**을 쓴다 -
`etf_pipeline.format_comparison_table()`이 이미 확립한 "보수적 기준" 규칙과
동일(IWM 사건 이후 이 프로젝트가 일관되게 지켜온 원칙).
"""


def market_baseline(voo_ledger: dict) -> dict:
    """
    VOO ledger에서 가장 보수적인(가장 비싼 P/E) 출처의 Implied Growth·Gap을
    뽑는다. etf_pipeline.format_comparison_table()의 규칙과 동일하게
    `max(implied_growth)`를 보수적 기준으로 삼는다.
    """
    by_source = voo_ledger["valuation"]["by_source"]
    worst = max(by_source.values(), key=lambda s: s["implied_growth"])
    return {
        "source": next(k for k, v in by_source.items() if v is worst),
        "implied_growth": worst["implied_growth"],
        "gap": worst["gap"],
        "expected_growth": voo_ledger["growth"]["net_expected_growth"],
    }


def relative_to_market(company_ledger: dict, baseline: dict) -> dict:
    """
    회사 ledger 1건을 시장 기준선과 비교한다. 공식 Gap/판정은 건드리지
    않는다 - 병기용 파생값만 계산한다(is_insurer/sbc_cross_check와 동일
    원칙).
    """
    ig_company = company_ledger["implied_growth"]["value"]
    gap_company = company_ledger["expectation_gap"]

    return {
        "ticker": company_ledger["meta"]["ticker"],
        "gap": gap_company,
        "judgment": company_ledger["judgment"],
        "implied_growth": ig_company,
        "market_implied_growth": baseline["implied_growth"],
        "market_gap": baseline["gap"],
        "growth_premium": ig_company - baseline["implied_growth"],
        "relative_gap": gap_company - baseline["gap"],
    }
