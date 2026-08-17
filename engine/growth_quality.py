"""
Growth Quality (STAGE 1 prototype, 2026-08-16) — 성장의 **양**과 **경제성**을 분리한다.

## 이 모듈이 푸는 IRS 문제

IRS는 성장률을 정교하게 추정하지만 **그 성장이 어떤 경제성 위에서 일어나는지**를
전혀 보지 않는다. 실측 확인(2026-08-16):

- `operating_income_by_year`는 **필수 입력**인데, 엔진은 이걸 `margin_volatility_score`
  (표준편차) 하나로만 쓴다 — **마진 수준(level)은 어디에도 쓰이지 않는다.**
  즉 영업이익률 32.8%인 BKNG과 3.4%인 GWRE가 변동성 말고는 동일 취급된다.
- `capex_by_year`도 필수 입력인데 `capex_intensity_from_series`는 주관적
  `capex_classification`이 있을 때만 작동하며, **34종목 중 실제 사용 0건**이다.

## ⚠️ 이것은 ROIC도 ROIIC도 아니다 (이름을 정확히 쓴다)

진짜 성장의 질 축은 ROIIC(신규 투하자본의 한계수익률)인데, IRS의 입력 스키마에
**투하자본 시계열이 없다**(`shareholders_equity_by_year`는 보험사 전용 opt-in,
`net_debt`는 최신 스칼라 1개). 따라서 ROIC/ROIIC는 **BLOCKED**이며, 이 모듈은
그 대체물이 아니라 **별개의, 더 약한, 그러나 계산 가능한 두 축**만 제공한다:

  1. `operating_margin_level`  — 사업이 매출 1원당 얼마를 남기는가
  2. `capex_to_revenue_level`  — 그 매출을 유지·성장시키는 데 매출 1원당 얼마를 쓰는가

**이 둘을 곱하거나 더해 단일 점수를 만들지 않는다**(설명력이 입증되지 않은 종합점수
금지). 두 축은 실측상 서로 거의 독립이다(순위상관 0.047, n=34).

## §16 증분정보 검정 결과 (2026-08-16, ledger 34종목)

채택한 두 축은 기존 IRS 변수와 **거의 무상관**이다:

| 후보 | vs 마진변동성 | vs RealisticGrowth | vs Gap | vs DRS |
|---|---|---|---|---|
| **마진 수준(채택)** | **−0.069** | −0.323 | −0.190 | **−0.043** |
| **자본집약도 수준(채택)** | — | — | — | 0.148 |

반대로 **추세(trend) 지표는 기각**했다 — 기존 정보와 크게 중복된다:
마진추세 slope는 마진변동성과 0.675, RealisticGrowth와 0.594, Gap과 0.512.
(가설은 "추세가 새 정보"였으나 실측이 기각했다. 수준이 새 정보였다.)

`FCF/영업이익`도 기각했다 — SBC/FCF와 순위상관 **+0.571**(n=8)로, "현금전환 우수"가
실은 SBC 강도를 재는 아티팩트다(GWRE 6.83·WDAY 3.85·DUOL 2.73이 전부 고SBC).

## 인식론적 지위

이 모듈의 어떤 값도 **판정·Gap·비중을 바꾸지 않는다**. 두 축이 미래 수익률이나
성장 지속성과 관계가 있다는 증거는 이 저장소에 **아직 없다** — 그 검증은
`experiments/H-007.json`으로 사전등록돼 있다. 병기만 한다.
"""
import statistics

# 계약서 40절 어휘. expectation_gap_engine.VALIDATION_STATUS와 같은 체계.
VALIDATION_STATUS = {
    "operating_margin_level": (
        "SOFTWARE_VALIDATED / RESEARCH_HYPOTHESIS — 회계 실측치이므로 계산은 정확하나, "
        "이 값이 미래 성장 지속성이나 수익률과 관계가 있다는 증거는 없다(H-007로 사전등록)"
    ),
    "capex_to_revenue_level": (
        "SOFTWARE_VALIDATED / PROXY_ONLY — 투하자본이 아니라 매출 대비 capex다. "
        "자본집약도의 약한 대리지표이며 ROIC의 분모를 대체하지 못한다"
    ),
    "roic_roiic": "BLOCKED — 투하자본 시계열이 AnalysisInputs에 없다",
}

MIN_YEARS = 3


def _validate_series(name, by_year):
    if not isinstance(by_year, dict) or not by_year:
        raise ValueError(f"{name}: 연도별 dict가 필요하다")
    try:
        years = sorted(by_year, key=int)
    except (TypeError, ValueError):
        raise ValueError(f"{name}: 연도 키가 정수로 해석되지 않는다 - {list(by_year)[:3]}")
    return years


def operating_margin_series(operating_income_by_year: dict, revenue_by_year: dict) -> dict:
    """
    연도별 영업이익률. 매출이 0 이하인 해는 마진이 정의되지 않으므로 **제외하고
    그 사실을 남긴다**(조용히 건너뛰지 않는다).
    """
    _validate_series("revenue_by_year", revenue_by_year)
    _validate_series("operating_income_by_year", operating_income_by_year)
    years = sorted(set(revenue_by_year) & set(operating_income_by_year), key=int)
    out, skipped = {}, []
    for y in years:
        rev = revenue_by_year[y]
        if rev is None or rev <= 0:
            skipped.append(y)
            continue
        out[y] = operating_income_by_year[y] / rev
    return {"by_year": out, "skipped_years_nonpositive_revenue": skipped}


def capex_to_revenue_series(capex_by_year: dict, revenue_by_year: dict) -> dict:
    """
    연도별 capex/매출. capex는 **양수 지출**로 들어온다는 전제이며(파이프라인이
    음수 capex를 이미 거부한다), 음수가 오면 부호 규약이 어긋난 것이므로 예외.
    """
    _validate_series("revenue_by_year", revenue_by_year)
    _validate_series("capex_by_year", capex_by_year)
    years = sorted(set(revenue_by_year) & set(capex_by_year), key=int)
    out, skipped = {}, []
    for y in years:
        rev, cap = revenue_by_year[y], capex_by_year[y]
        if cap is not None and cap < 0:
            raise ValueError(
                f"capex_by_year[{y}]={cap} - capex는 양수 지출로 입력해야 한다"
                "(부호 규약 위반은 자본집약도를 정반대로 만든다)"
            )
        if rev is None or rev <= 0:
            skipped.append(y)
            continue
        out[y] = cap / rev
    return {"by_year": out, "skipped_years_nonpositive_revenue": skipped}


def economic_profile(revenue_by_year: dict, operating_income_by_year: dict,
                     capex_by_year: dict) -> dict:
    """
    IRS가 현재 보지 않는 두 축의 **수준**을 낸다.

    ⚠️ 반환값 어디에도 종합점수가 없다. 두 축은 서로 독립이며(실측 0.047),
    합치면 그 독립성이 사라진다.

    ⚠️ 추세(slope)는 **의도적으로 내지 않는다** — 2026-08-16 실측에서 기존
    변수와 중복(마진변동성 0.675 / RealisticGrowth 0.594)임이 확인돼 REJECT됐다.
    """
    m = operating_margin_series(operating_income_by_year, revenue_by_year)
    c = capex_to_revenue_series(capex_by_year, revenue_by_year)

    limitations = []
    m_years = sorted(m["by_year"], key=int)
    c_years = sorted(c["by_year"], key=int)
    if len(m_years) < MIN_YEARS:
        limitations.append(
            f"[DATA MISSING] 영업이익률 산출 연도가 {len(m_years)}개뿐(최소 {MIN_YEARS})"
        )
    if m["skipped_years_nonpositive_revenue"]:
        limitations.append(
            f"[DATA MISSING] 매출≤0으로 마진 제외된 연도: "
            f"{m['skipped_years_nonpositive_revenue']}"
        )
    if c["skipped_years_nonpositive_revenue"]:
        limitations.append(
            f"[DATA MISSING] 매출≤0으로 capex비율 제외된 연도: "
            f"{c['skipped_years_nonpositive_revenue']}"
        )

    def _latest(d, years):
        return d[years[-1]] if years else None

    margin_latest = _latest(m["by_year"], m_years)
    capex_latest = _latest(c["by_year"], c_years)

    # 최근 마진이 음수면 "성장의 경제성"을 논할 단계가 아니다 - 숨기지 않고 표시한다.
    if margin_latest is not None and margin_latest <= 0:
        limitations.append(
            f"[UNPROFITABLE] 최근 영업이익률 {margin_latest*100:.2f}% - "
            "이 기업은 아직 영업 단계에서 이익을 내지 못한다"
        )

    return {
        "operating_margin_level": margin_latest,
        "operating_margin_latest_year": m_years[-1] if m_years else None,
        "operating_margin_median": (
            statistics.median(m["by_year"].values()) if m_years else None
        ),
        "capex_to_revenue_level": capex_latest,
        "capex_to_revenue_latest_year": c_years[-1] if c_years else None,
        "capex_to_revenue_median": (
            statistics.median(c["by_year"].values()) if c_years else None
        ),
        "n_years_margin": len(m_years),
        "n_years_capex": len(c_years),
        "data_limitations": limitations,
        "validation_status": VALIDATION_STATUS,
        # 이 모듈은 판정에 관여하지 않는다는 사실을 결과에 박아둔다.
        "affects_official_judgment": False,
    }
