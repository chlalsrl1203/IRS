"""
Accounting Quality (v3.70, 2026-08-24) — "이 숫자를 믿어도 되는가"를 묻는다.

## 왜 필요한가 - 실측된 공백

2026-08-24 축별 감사에서 확인: IRS는 재무수치를 **정확히 계산**하지만(34종목
골든재현 1e-12), **회계품질 판별은 검색 히트 0건**이었다. 발생액·M-score·
매출인식 이상·재작성 이력 - 아무것도 없다. `etf_engine.earnings_quality_score`는
*ETF 구성종목 중 적자기업 비중*이라 기업 회계품질과 무관하다.

즉 "이 숫자가 맞는가"는 계산하면서 **"이 숫자를 믿어도 되는가"는 아예 묻지
않고** 있었다.

## 외부 근거

  Sloan, Richard G. (1996) "Do stock prices fully reflect information in accruals
  and cash flows about future earnings?" The Accounting Review 71(3), 289-315.

핵심 주장: 이익의 **발생액 성분이 현금흐름 성분보다 지속성이 낮다**. 발생액이
높은(회계이익이 현금이익을 크게 앞서는) 기업의 이익은 덜 지속된다.

⚠️ **출처 검증 수준을 정직하게 구분한다**:
  - 서지정보: **VERIFIED** - 4개 이상 독립 학술출처(ScienceDirect·NBER·
    Wharton·AAA)가 저자/연도/저널/권/페이지에 일치.
  - 계산식 본문: **UNVERIFIED** - 원문 PDF가 1996년 스캔본(JBIG2 이미지)이라
    직접 파싱에 실패했다. 그래서 아래는 Sloan의 대차대조표식 발생액이 아니라
    **현금흐름표 기반 근사**이며 `PROXY_ONLY`로 라벨한다(growth_quality.py의
    capex proxy와 동일 처리).

## ⚠️ 합성점수를 만들지 않는다 (§31 안티기능 등록부)

이 영역의 표준 도구인 Piotroski F-Score(2000)는 9개 신호를 0~9 정수로 합산하는
**합성점수**다. 이 프로젝트는 §31에 "단일 합성점수"를 의도적으로 만들지 않는
것으로 이미 등록했고(research_lenses의 6차원 별점을 같은 이유로 REJECT), 사유는
"중요도가 다른 축이 같은 무게가 되고 공백이 점수 뒤에 숨는다"였다. 그 등록을
뒤집을 새 증거가 없으므로 **개별 진단값만** 낸다.

추가로 F-Score는 **고 book-to-market(가치주), 1976-1996** 표본에서 검증됐다.
IRS 유니버스는 FCF-DCF를 적용하는 성장주 쪽이라 검증 도메인 밖이다.

## ⭐ SBC를 반드시 되돌린다 - 이게 이 모듈의 핵심 설계 결정

순진한 발생액 `(NI - OCF) / 평균총자산`은 **SBC 강도를 재는 아티팩트**다.
SBC가 OCF에 가산되는 비현금비용이기 때문이다. 34종목 실측:

| | 순진한 형태 | SBC 되돌린 형태 |
|---|---|---|
| SBC/FCF와 순위상관 | **−0.717** 🔴중복 | **+0.200** 🟢독립 |
| Gap | −0.448 | −0.216 |
| Realistic Growth | −0.564 | −0.314 |

순진한 형태에서 발생액이 가장 음수인 종목이 정확히 고SBC SaaS(MNDY·DUOL·
WDAY·SE)였다. **RQ-001이 `FCF/영업이익`을 같은 이유로 기각한 함정에 그대로
빠졌던 것**이고, 측정이 그걸 잡아냈다. D&A는 Sloan의 원 측정에도 포함되므로
되돌리지 않는다(capex 집약도와의 상관 +0.020으로 혼동 없음을 확인).

## 이 모듈은 `run_analysis()`에 배선돼 있지 않다

growth_quality.py와 동일한 판단이다 - 이 지표가 **투자 성과와 관계있다는 증거가
IRS 표본에 0건**이다(수익률 관측 자체가 없다). 배선하면 미검증 변수가 34종목
판정을 즉시 바꾼다. 병기·독립보관하고, 승격은 별도 실증 이후에 결정한다.
"""

VALIDATION_STATUS = {
    "accrual_ratio": (
        "PROXY_ONLY / ECONOMICALLY_SUPPORTED — 방향은 Sloan(1996)과 일치하나 "
        "계산식은 현금흐름표 기반 근사다(원문 스캔본이라 본문 미검증). "
        "IRS 표본에서 투자성과와의 관계는 **검증된 바 없다**."
    ),
    "composite_score": (
        "DELIBERATELY_ABSENT — Piotroski F-Score류 합성점수는 §31 안티기능 "
        "등록부 항목이라 만들지 않는다."
    ),
    "cross_company_comparison": (
        "IMPLEMENTED_NOT_VALIDATED — 업종별 구조적 차이(자본집약도·운전자본 "
        "회전)가 섞여 있어 **기업 간 절대 비교보다 같은 기업의 시계열 변화**가 "
        "더 해석 가능하다. 34종목 관측 기반 시작점이며 임계값은 검증되지 않았다."
    ),
}

# 34종목 실측 분포(2026-08-24, SBC 되돌린 형태)에서 나온 관측 기반 시작점.
# ⚠️ 검증된 컷이 아니다 - LYNCH_TYPE_CAPS·P/B 임계값과 동일하게 취급할 것.
OBSERVED_MEDIAN = -0.0259
OBSERVED_RANGE = (-0.0829, 0.0169)


def _require_series(name, by_year):
    if not by_year:
        raise ValueError(f"{name}가 비어 있다")
    return {int(y): float(v) for y, v in by_year.items()}


def accrual_ratio_series(net_income_by_year, operating_cashflow_by_year,
                         assets_by_year, sbc_by_year=None):
    """
    연도별 발생액 비율 = (순이익 − 영업현금흐름 + SBC) / 평균총자산.

    - **평균총자산**을 쓰는 이유: 기간 항목(손익·현금흐름)을 시점 항목(자산)으로
      나누는 왜곡을 줄이는 문헌 표준. 기초·기말 평균이라 **첫 해는 계산되지
      않는다**(직전 연도 자산이 필요).
    - `sbc_by_year`가 None이면 SBC를 되돌리지 않는다 — 그 경우 결과는 SBC 강도와
      크게 겹치므로(모듈 docstring 표) 해석에 주의해야 하고, 호출부가 그 사실을
      알 수 있도록 `accounting_quality_profile`이 명시적으로 경고를 남긴다.

    부호 규약: **양수 = 회계이익이 현금이익을 앞섬**(Sloan 기준 주의 방향),
    음수 = 현금이익이 회계이익을 앞섬(보수적).
    """
    ni = _require_series("net_income_by_year", net_income_by_year)
    ocf = _require_series("operating_cashflow_by_year", operating_cashflow_by_year)
    ta = _require_series("assets_by_year", assets_by_year)
    sbc = {int(y): float(v) for y, v in (sbc_by_year or {}).items()}

    years = sorted(set(ni) & set(ocf) & set(ta))
    if sbc:
        years = [y for y in years if y in sbc]

    out = {}
    for i, y in enumerate(years):
        if i == 0:
            continue                      # 평균총자산에 직전 연도가 필요하다
        avg_assets = (ta[y] + ta[years[i - 1]]) / 2.0
        if avg_assets <= 0:
            continue                      # 자산이 0 이하면 비율이 정의되지 않는다
        out[y] = (ni[y] - ocf[y] + sbc.get(y, 0.0)) / avg_assets
    return out


def accounting_quality_profile(net_income_by_year, operating_cashflow_by_year,
                               assets_by_year, sbc_by_year=None, window=5):
    """
    발생액 진단 묶음. **합성점수를 만들지 않는다** — 개별 값과 사실만 낸다.

    반환 dict에 `judgment`류 키가 없는 것은 의도된 것이다: 어느 발생액 수준이
    "나쁜가"에 대한 외부 컷을 확보하지 못했고, IRS 표본으로 검증한 적도 없다.
    """
    series = accrual_ratio_series(net_income_by_year, operating_cashflow_by_year,
                                  assets_by_year, sbc_by_year)
    notes = []
    if not sbc_by_year:
        notes.append(
            "[SBC 미반영] SBC를 되돌리지 않아 이 값은 SBC 강도와 크게 겹친다"
            "(34종목 실측 순위상관 −0.717). 고SBC 기업에서 발생액이 실제보다 "
            "보수적으로 보인다 — 해석에 주의할 것.")
    if not series:
        notes.append("[계산 불가] 공통 연도가 부족하거나 평균총자산이 0 이하다.")
        return {"accrual_ratio_by_year": {}, "latest": None, "mean_window": None,
                "cash_exceeds_earnings_latest": None, "notes": notes,
                "validation_status": VALIDATION_STATUS}

    years = sorted(series)
    win = years[-window:]
    latest = series[years[-1]]
    mean_win = sum(series[y] for y in win) / len(win)

    if latest > OBSERVED_RANGE[1] or latest < OBSERVED_RANGE[0]:
        notes.append(
            f"[관측범위 밖] 최근 발생액 {latest:+.4f}가 34종목 관측범위 "
            f"{OBSERVED_RANGE[0]:+.4f}~{OBSERVED_RANGE[1]:+.4f}를 벗어난다 — "
            f"임계값이 아니라 '지금까지 본 적 없는 값'이라는 뜻이다.")

    return {
        "accrual_ratio_by_year": series,
        "latest": latest,
        "latest_year": years[-1],
        "mean_window": mean_win,
        "window_years": win,
        # Piotroski ACCRUAL 신호와 같은 방향의 사실 기술(합성점수로 합산하지 않는다)
        "cash_exceeds_earnings_latest": latest < 0,
        "observed_median": OBSERVED_MEDIAN,
        "sbc_adjusted": bool(sbc_by_year),
        "notes": notes,
        "validation_status": VALIDATION_STATUS,
    }
