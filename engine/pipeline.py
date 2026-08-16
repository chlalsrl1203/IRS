"""
Analysis Pipeline (v3.19 신규)

왜 만들었나 (2026-07-25 감사 결과):
지금까지 모든 종목 분석은 세션마다 파이썬 코드를 손으로 다시 배선해서 돌렸다.
그 결과 반복된 사고가 셋 있다.

1. **단위 사고**: rar()에 소수를 넣어 100배 틀린 값이 4종목에 기록됨(v3.19에서
   가드 추가). 체인을 손으로 이을 때마다 재발 위험이 있다.
2. **계산 유실**: 큐22(Cadence)는 "엔진계산은 했다"는 기록만 남고 입력값·중간값이
   전부 사라져 전면 재수행해야 했다. CDNS/MNST/PH의 과거 RAR과 대조검증도
   불가능했다.
3. **모델선택 실수**: PH를 single_stage로 계산해 Gap이 -1.48%p(적정가)로 나왔으나
   실제 확립된 컨벤션은 two_stage(-8.59%p, 과대평가)였다. 기존 기록과 우연히
   비교해봐서 잡았을 뿐, 코드가 잡아준 게 아니다.

이 모듈은 셋 다 구조적으로 막는다:
- 체인을 한 곳에서만 배선한다(단위 실수 원천 차단)
- 입력값·중간값·최종값을 전부 ledger JSON으로 저장한다(재현·대조검증 가능)
- 두 모델을 항상 같이 계산해 괴리가 크면 경고하고, 선택 사유를 필수로 받는다
"""

import json
import os
from dataclasses import dataclass, field, asdict
from datetime import date, datetime, timezone

from engine.expectation_gap_engine import (
    DRSInputs,
    ENGINE_VERSION,
    LYNCH_TYPE_CAPS,
    bull_bear_base_growth_rates,
    capex_intensity_from_series,
    capped_n,
    check_deceleration_double_count,
    check_scale_plausibility,
    fcf_conservatism_adjustment,
    check_stalwart_two_stage_bias,
    classify_lynch_type,
    competition_intensity_score,
    confidence_score,
    cyclicality_score,
    default_terminal_growth,
    erp_from_drs,
    expectation_gap_sensitivity_check,
    expected_return,
    implied_growth_single_stage,
    implied_growth_two_stage,
    judgment_from_gap,
    judgment_grade_from_gap,
    leverage_score,
    margin_volatility_score,
    rar_from_decimal_return,
    realistic_growth_estimate,
    revenue_volatility_score,
    scenario_probabilities_from_drs,
    scenario_return_from_growth,
    structural_discount_rate,
)
from engine.provenance import PROVENANCE_UNKNOWN

MODEL_DIVERGENCE_WARNING_THRESHOLD = 0.03  # 3%p 이상 벌어지면 경고
INSURER_GROWTH_DIVERGENCE_THRESHOLD = 0.05  # 5%p 이상 벌어지면 경고(v3.22)


def compare_implied_growth_models(
    market_cap: float,
    fcf0: float,
    r: float,
    n: int,
    g_terminal: float,
) -> dict:
    """
    v3.19 신규: single_stage와 two_stage를 **항상 둘 다** 계산해 비교한다.

    왜 강제 비교인가: 어느 모델이 옳은지 판정하는 확립된 규칙이 이 프로젝트에
    문서화된 적이 없다(GOOGL은 two_stage 오사용이 v3.11 감사에서 발견돼
    single_stage로 정정하며 판정 자체가 뒤집혔고, PH는 반대로 two_stage가
    관행이었다). 규칙이 없는 상태에서 코드가 임의로 하나를 고르면 그게 곧
    근거 없는 자동화다. 그래서 고르지 않고, **둘의 괴리를 드러내서 분석자가
    의식적으로 선택하고 사유를 남기도록** 만든다.

    반환값: {single_stage, two_stage, divergence, divergence_warning}
    두 모델 중 하나가 계산 불가면(Model N/A) 해당 값은 None, error에 사유.
    """
    result = {"single_stage": None, "two_stage": None, "errors": {}}

    try:
        result["single_stage"] = implied_growth_single_stage(market_cap, fcf0, r)
    except ValueError as e:
        result["errors"]["single_stage"] = str(e)

    try:
        g2, _, _ = implied_growth_two_stage(market_cap, fcf0, r, n, g_terminal)
        result["two_stage"] = g2
    except (ValueError, RuntimeError) as e:
        result["errors"]["two_stage"] = str(e)

    if result["single_stage"] is not None and result["two_stage"] is not None:
        divergence = abs(result["single_stage"] - result["two_stage"])
        result["divergence"] = divergence
        if divergence >= MODEL_DIVERGENCE_WARNING_THRESHOLD:
            result["divergence_warning"] = (
                f"[모델 괴리 경고] single_stage({result['single_stage']*100:.2f}%)와 "
                f"two_stage({result['two_stage']*100:.2f}%)가 {divergence*100:.2f}%p 벌어져 있다. "
                f"어느 쪽을 쓰느냐에 따라 Expectation Gap 판정이 바뀔 수 있으므로, "
                f"model_choice_reason에 선택 근거를 반드시 남길 것(v3.19). "
                f"과거 같은 종목 기록이 있으면 그 내재성장률과 대조해볼 것 - "
                f"PH가 이 방법으로 모델선택 실수를 잡은 사례다(2026-07-25)."
            )
        else:
            result["divergence_warning"] = None
    else:
        result["divergence"] = None
        result["divergence_warning"] = None

    return result


@dataclass
class AnalysisInputs:
    """
    한 종목 분석에 필요한 모든 입력. 여기 담긴 값만으로 결과가 100% 재현되어야 한다.

    재무 시계열은 {회계연도: 값} 딕셔너리로 받는다(연도 정렬은 내부에서 처리).
    market_cap/net_debt/ebitda/fcf 등 금액은 **원 단위 그대로**(예: 92_952_756_000).
    """

    ticker: str
    company_name: str

    revenue_by_year: dict
    operating_income_by_year: dict
    operating_cashflow_by_year: dict
    capex_by_year: dict

    market_cap: float
    net_debt: float
    ebitda: float
    risk_free_rate: float

    # 주관적 입력 - 반드시 근거를 함께 남길 것(v3.19: 사유 필수화)
    competitor_threat_weights: list
    market_share_trend_pp_per_year: float
    active_antitrust_or_regulatory_case: bool
    demand_sensitivity_pct: float
    subjective_input_basis: str

    # 모델 선택 - v3.19부터 명시 필수
    model_used: str  # "single_stage" | "two_stage"
    model_choice_reason: str

    margin_years: list = None
    n_requested: int = 12
    # v3.25(2026-08-01 방법론 감사 M-4): capped_n()은 8~15년을 허용해 해자
    # 강도에 따라 성장지속기간을 차등화하도록 설계됐으나, 지금까지의 36종목
    # ledger 전부가 기본값 12를 그대로 썼다 - 실제로 아무도 이 유연성을 쓴
    # 적이 없다. 코드 버그는 아니지만(누구도 오버라이드하지 않았을 뿐),
    # lynch_type_override/cagr_base_year_override와 동일하게 기본값에서
    # 벗어나면 근거를 남기게 한다. n_requested=12(기본값)면 사유 불필요 -
    # 기존 36개 ledger는 전부 이 경로라 영향 없음.
    n_requested_reason: str = None
    data_completeness_pct: float = 0.9
    lynch_type_override: str = None
    lynch_type_override_reason: str = None
    data_sources: list = field(default_factory=list)

    # capex 급증 분류 - v3.20에서 배선(그 전까지는 엔진에만 있고 미사용이었다).
    # None이면 기존 동작(realistic_growth_estimate의 기본 FCF보수원칙)을 그대로 쓴다.
    # 값을 넣으면 capex_intensity_from_series + fcf_conservatism_adjustment 경로를 탄다.
    capex_classification: str = None          # "growth_investment" | "margin_erosion"
    capex_classification_basis: str = None

    # 5년 CAGR 기준연도 override - v3.21에서 추가(BKNG 실사례).
    # 기본값은 years[-6](= 최근년도 5년 전)인데, 그 해가 코로나 같은 일회성
    # 충격에 걸리면 두 가지가 동시에 망가진다:
    #   (1) FCF가 음수면 CAGR 자체가 정의되지 않아 실행이 거부된다
    #   (2) 매출이 저점이면 CAGR이 '회복 반등'을 '성장'으로 착각해 과대계상된다
    # 이 값을 지정하면 매출·FCF CAGR **양쪽 모두** 같은 기준연도를 쓴다
    # (둘을 다른 창으로 계산하면 min() 비교 자체가 성립하지 않는다).
    cagr_base_year_override: int = None
    cagr_base_year_override_reason: str = None

    # 보험업 FCF-DCF 교차검증 - v3.22에서 배선(ACGL/PGR 실증 2건 기반).
    # 보험사의 OCF는 플로트(float, 보험료 선수취-보험금 후지급) 성장이 섞여
    # 회계이익보다 구조적으로 부풀려진다 - FCF-DCF를 그대로 적용하면 내재가치가
    # 체계적으로 과대평가될 수 있다. is_insurer=True면 net_income_by_year/
    # shareholders_equity_by_year/dividends_paid_by_year로 지속가능성장률
    # (ROE x 유보율)과 P/B를 자동 계산해 Realistic Growth와 대조 경고한다.
    is_insurer: bool = False
    net_income_by_year: dict = None
    shareholders_equity_by_year: dict = None
    dividends_paid_by_year: dict = None

    # 주식보상비용(SBC) 병기 교차검증 - v3.23에서 배선(2026-08-01 방법론 감사 Critical-1).
    # FCF = OCF - capex 정의는 SBC를 비현금비용으로 가산하는 회계처리를 그대로
    # 따라가므로, SBC를 암묵적으로 주주 귀속 현금처럼 취급한다. SBC는 회계적으로만
    # 비현금일 뿐 지분 희석을 통한 실질적 가치이전이다. 감사에서 TTD(SBC/FCF 62%)·
    # WDAY(59%)처럼 업종별 편차가 극심함을 확인했고, WDAY는 SBC를 차감하면 판정 자체가
    # 뒤집혔다(저평가 가능성 -> 적정가). None이면 기존 동작(SBC를 FCF에 포함) 그대로다 -
    # 값을 넣으면 SBC를 차감한 대안 Implied Growth/Gap을 **병기**한다(어느 쪽이
    # 맞는지 자동 판정하지 않는다 - is_insurer가 지속가능성장률을 병기만 하는 것과
    # 동일 원칙). 최근 회계연도 값만 쓴다(fcf0와 동일 시점 비교를 위해).
    sbc_by_year: dict = None

    # 종목별 반증조건 사전기록 - v3.24에서 배선(2026-08-01 방법론 감사 권고 #2).
    # High-1(실현수익률로 검증된 적이 단 한 번도 없음)의 최소 대응책 - "이런
    # 실적이 나오면 이 판정은 틀린 것"을 분석 시점에 미리 적어두면 사후합리화를
    # 막을 수 있다(감사 원문: "사후합리화를 막는 유일한 실질적 장치"). 필수화하지는
    # 않는다 - 과거 분석에 소급 작성하면 그 자체가 사후합리화이므로 허위 기록이
    # 된다. 새 분석부터 opt-in으로 채워나간다.
    falsification_conditions: str = None

    # 분석시점 주가·통화 - v3.24에서 배선(2026-08-01 방법론 감사 권고 #3).
    # 향후 백테스트(실현수익률 검증, High-1)의 전제조건은 "그때 얼마였는지"를
    # 기록해두는 것이다. currency 미기재시 기존 관행대로 USD로 간주한다(PDD만
    # CNY 예외 - M-6 참고. 과거 ledger에는 이 필드가 없어 소급 판별 불가하므로
    # 새 ledger부터 명시적으로 남긴다).
    price_at_analysis: float = None
    currency: str = "USD"

    # ── 값 단위 출처 기록 - v3.50에서 배선(계약서 §6) ─────────────────────
    # `data_sources`(자유 문자열)로는 "FY2023 매출이 어느 공시에서 왔고 언제
    # 공개됐는가"에 답할 수 없다. `engine/provenance.py`가 만드는 기록을 그대로
    # 담는 opt-in 필드다 - None이면 기존 동작 그대로이며, 기존 34종목은
    # PROVENANCE_UNKNOWN으로 남는다(소급 생성 금지, §6).
    #
    # 생성은 `provenance.provenance_from_sec_facts()`로 자동화한다 - 손으로
    # 적게 만들면 결국 아무도 안 적는다(이 프로젝트가 문서 규칙에서 네 번 겪은 실패).
    provenance: dict = None

    # Realistic Growth 직접 오버라이드 - v3.28에서 배선(2026-08-04, ROP 유기적
    # 성장률 교차검증이 실증사례). M&A 롤업 성장 종목(GEN/ROP/BRO 패턴)은
    # 매출·FCF CAGR 기반 계산이 Lynch 성장상한에 항상 걸려버려(M-1) 계산 자체가
    # 결과에 기여하지 못하는데, 그 상한값이 회사가 실제로 공시한 성장률과
    # 크게 괴리될 수 있다(ROP: 캡 12% vs 오가닉 공시 5-6%, 캡이 만든 여유폭이
    # 실제로는 근거가 약했음을 교차검증으로 확인). 값을 넣으면 CAGR 계산·Lynch
    # 캡을 모두 우회하고 이 값을 Realistic Growth로 직접 사용한다 - 근거 없이
    # 강제하지 않기 위해 반드시 subjective_input_basis 수준의 사유를 요구한다.
    # None이면 기존 동작(CAGR 계산 + 캡) 그대로다.
    realistic_growth_override: float = None
    realistic_growth_override_reason: str = None

    # ── Point-in-Time 토대 - v3.47에서 배선(2026-08-15 Phase 3) ──────────
    # 계약서 20~22절의 **최소 요건만** 넣는다. Historical Replay를 만드는 게
    # 아니라, replay가 언젠가 가능해지려면 반드시 있어야 하는 두 날짜를 지금부터
    # 모으기 시작하는 것이다(v3.24가 price_at_analysis를 "백테스트의 전제조건"
    # 이라며 먼저 넣은 것과 같은 패턴).
    #
    # analysis_as_of      : "이 분석이 어느 시점의 정보로 이뤄졌는가"(ISO 날짜)
    #                       meta.analyzed_at(코드 실행 시각)과 다르다 - 실행
    #                       시각은 그 시점에 무엇이 공시돼 있었는지 보증하지 않는다.
    # filing_dates_by_year: {회계연도: 그 연도 실적이 공시된 ISO 날짜}
    #                       최근 회계연도(fcf0를 결정하는 해)는 반드시 포함해야 한다.
    #
    # ⚠️ 둘 다 None이면 PIT_UNKNOWN이다 - 기존 34종목이 전부 여기 해당하며,
    # 그 사실을 "검증됨"으로 위장하지 않는다(계약서 22절).
    analysis_as_of: str = None
    filing_dates_by_year: dict = None

    def __post_init__(self):
        if self.model_used not in ("single_stage", "two_stage"):
            raise ValueError('model_used는 "single_stage" 또는 "two_stage"여야 함')
        if not self.model_choice_reason or not self.model_choice_reason.strip():
            raise ValueError(
                "model_choice_reason 필수(v3.19): 어느 모델을 왜 골랐는지 남기지 않으면 "
                "다음 세션이 PH처럼 반대 모델로 계산해 판정이 뒤집힐 수 있다."
            )
        if not self.subjective_input_basis or not self.subjective_input_basis.strip():
            raise ValueError(
                "subjective_input_basis 필수(v3.19): competitor_threat_weights/"
                "market_share_trend/demand_sensitivity는 [추정치]이므로 근거를 "
                "남기지 않으면 종목간 DRS 비교가 불가능해진다."
            )
        if self.lynch_type_override is not None and not self.lynch_type_override_reason:
            raise ValueError("lynch_type을 수동 오버라이드하려면 사유 필수")

        if self.realistic_growth_override is not None and not (
            self.realistic_growth_override_reason
            and self.realistic_growth_override_reason.strip()
        ):
            raise ValueError(
                "realistic_growth_override 필수 사유 누락(v3.28): CAGR 계산과 "
                "Lynch 캡을 모두 우회하는 값이라 근거 없이 쓰면 판정을 조용히 "
                "뒤집을 수 있다."
            )

        # v3.25(M-4): n_requested를 기본값(12)에서 벗어나게 쓰려면 사유 필수.
        if self.n_requested != 12 and not (
            self.n_requested_reason and self.n_requested_reason.strip()
        ):
            raise ValueError(
                "n_requested_reason 필수(v3.25): n_requested를 기본값(12)에서 "
                "벗어나게 쓰려면 해자 강도 등 근거를 남길 것 - capped_n()의 "
                "docstring이 경고하듯 이 값은 '해자 강도를 이유로 밸류에이션을 "
                "정당화'하는 데 오남용되기 쉽다."
            )

        # v3.20: capex 분류는 판정을 뒤집을 수 있는 주관적 입력이므로
        # model_choice_reason/lynch_type_override_reason과 동일하게 근거를 강제한다.
        if self.capex_classification is not None:
            if self.capex_classification not in ("growth_investment", "margin_erosion"):
                raise ValueError(
                    'capex_classification은 "growth_investment" 또는 '
                    '"margin_erosion"만 허용'
                )
            if not self.capex_classification_basis or not self.capex_classification_basis.strip():
                raise ValueError(
                    "capex_classification_basis 필수(v3.20): capex 급증을 '성장투자'로 "
                    "부르면 FCF CAGR이 상향조정되어 판정이 뒤집힐 수 있다. 무엇을 근거로 "
                    "그렇게 분류했는지(증설계획 공시, 수주잔고, 가동률 등) 남기지 않으면 "
                    "검증 불가능한 낙관이 된다."
                )

        # v3.21: CAGR 기준연도 override는 성장률을 통째로 바꾸므로 근거 필수.
        # 기준연도를 고르는 행위 자체가 결과를 좌우하기 때문에(저점을 고르면
        # 성장률이 부풀고 고점을 고르면 눌린다) 반드시 사유를 남기게 한다.
        if self.cagr_base_year_override is not None:
            if not self.cagr_base_year_override_reason or not self.cagr_base_year_override_reason.strip():
                raise ValueError(
                    "cagr_base_year_override_reason 필수(v3.21): 기준연도 선택은 "
                    "성장률을 통째로 바꾼다. 왜 기본값(5년 전)을 쓸 수 없는지, 왜 "
                    "하필 그 해인지를 남기지 않으면 유리한 해를 고른 것과 구별되지 않는다."
                )
            if self.cagr_base_year_override not in self.revenue_by_year:
                raise ValueError(
                    f"cagr_base_year_override={self.cagr_base_year_override}가 "
                    f"revenue_by_year에 없다"
                )
            if self.cagr_base_year_override >= max(self.revenue_by_year):
                raise ValueError(
                    "cagr_base_year_override는 최근 회계연도보다 앞서야 함"
                )

        # v3.22: 보험업 교차검증은 3개 시계열이 모두 있어야 계산 가능.
        if self.is_insurer:
            missing = [
                name for name, d in [
                    ("net_income_by_year", self.net_income_by_year),
                    ("shareholders_equity_by_year", self.shareholders_equity_by_year),
                    ("dividends_paid_by_year", self.dividends_paid_by_year),
                ] if not d
            ]
            if missing:
                raise ValueError(
                    f"is_insurer=True면 {', '.join(missing)}이(가) 필수(v3.22): "
                    f"보험업 ROE x 유보율 교차검증(ACGL/PGR 선례)을 계산하려면 "
                    f"순이익·자기자본·배당 시계열이 있어야 한다."
                )

        # ⚠️ v3.19에서 실제로 겪은 사고(2026-07-25 BRO 재검증): 데이터 소스마다
        # capex 부호 규약이 다르다. Alpha Vantage는 양수(지출액), Fiscal.ai는
        # 음수(현금유출)로 준다. 파이프라인은 fcf = ocf - capex 이므로 음수를 그대로
        # 넣으면 capex를 빼는 대신 **더해서** FCF가 과대계상된다(BRO FY25 기준
        # 1,382M -> 1,518M, +9.8%). RAR 100배 사고와 같은 유형의 조용한 단위 사고라
        # 코드로 막는다.
        negative_capex = {y: v for y, v in self.capex_by_year.items() if v < 0}
        if negative_capex:
            raise ValueError(
                f"capex에 음수 값이 있다: {negative_capex}. capex는 **지출액(양수)**으로 "
                f"넣어야 한다(fcf = ocf - capex). 데이터 소스가 현금유출을 음수로 주면"
                f"(Fiscal.ai 등) abs()로 부호를 정규화할 것. 그대로 넣으면 FCF가 "
                f"capex의 2배만큼 과대계상된다(v3.19 가드)."
            )

        # ⚠️ v3.46 가드(2026-08-15 Phase 0 감사 C-01): EBITDA<=0이면
        # net_debt/EBITDA는 정의되지 않는다. 가드가 없을 때 무슨 일이 벌어지는지
        # 실행으로 확인했다 - EBITDA가 적자면 비율이 **음수**가 되고,
        # leverage_score()는 음수를 "순현금"으로 해석해 최저 위험점수(2.0)를 준다.
        #
        #   동일 기업(순부채 +$30억):
        #     EBITDA -$5억(적자) -> 비율 -6.00 -> leverage 2.0  -> DRS 22.4
        #     EBITDA +$5억(흑자) -> 비율 +6.00 -> leverage 20.0 -> DRS 40.4
        #
        # 부실한 쪽이 DRS 18점 더 "안전"하게 나오고 경고조차 없었다. DRS는
        # ERP -> 할인율 -> Implied Growth -> Gap -> 판정, 그리고 시나리오확률·
        # Confidence·RAR까지 전부를 타고 흐르므로 조용히 판정을 뒤집을 수 있다
        # (capex 부호 사고와 같은 계열: 단위/부호가 조용히 반대로 작동하는 유형).
        #
        # EBITDA=0이면 원인 설명 없는 ZeroDivisionError가 났다.
        #
        # ⚠️ 순현금(net_debt<0, EBITDA>0)은 **정상 경로**다 - 34종목 중 13종목이
        # 여기 해당하며(MNDY -138.13 등) 그 종목들의 leverage 2.0은 옳다.
        # 이 가드는 분모만 검사하므로 그 경로를 건드리지 않는다.
        if self.ebitda is None or self.ebitda <= 0:
            raise ValueError(
                f"ebitda={self.ebitda}: EBITDA가 0 이하면 net_debt/EBITDA가 "
                f"정의되지 않는다(v3.46 가드). 그대로 두면 EBITDA 적자 기업이 "
                f"'순현금'으로 오인되어 레버리지 위험이 **정반대로** 산출된다"
                f"(부실기업일수록 DRS가 낮게 나옴). EBITDA가 실제로 적자인 "
                f"기업이라면 leverage 항목을 DRS에서 제외하고 "
                f"DRSInputs.excluded_reasons에 사유를 남기는 경로를 쓸 것 - "
                f"이 파이프라인은 그 종목을 자동으로 처리하지 않는다."
            )

        # v3.23: SBC도 capex와 동일한 부호규약 함정이 있다(현금흐름표에
        # 비현금비용 가산 항목으로 항상 양수 표기됨) - 음수가 들어오면 데이터
        # 소스 부호규약을 의심할 것.
        if self.sbc_by_year is not None:
            negative_sbc = {y: v for y, v in self.sbc_by_year.items() if v < 0}
            if negative_sbc:
                raise ValueError(
                    f"sbc_by_year에 음수 값이 있다: {negative_sbc}. SBC는 항상 "
                    f"양수(비용 규모)로 넣어야 한다."
                )
            latest_year = max(self.revenue_by_year)
            if latest_year not in self.sbc_by_year:
                raise ValueError(
                    f"sbc_by_year에 최근 회계연도({latest_year})가 없다 - fcf0와 "
                    f"동일 시점의 SBC가 있어야 병기 계산이 가능하다."
                )

        # v3.47: PIT 입력 형식 검증(값이 있을 때만). 형식이 틀리면 조용히
        # PIT_UNKNOWN으로 떨어지는 대신 즉시 거부한다 - "기록했다고 생각했는데
        # 사실은 안 된" 상태가 가장 나쁘다.
        if self.analysis_as_of is not None:
            _parse_iso_date(self.analysis_as_of, "analysis_as_of")
        if self.filing_dates_by_year is not None:
            if not self.filing_dates_by_year:
                raise ValueError(
                    "filing_dates_by_year가 빈 dict다 - 모르면 None으로 둘 것"
                    "(PIT_UNKNOWN으로 정직하게 기록된다)."
                )
            for year, value in self.filing_dates_by_year.items():
                _parse_iso_date(value, f"filing_dates_by_year[{year}]")
            latest_fy = max(self.revenue_by_year)
            if latest_fy not in self.filing_dates_by_year:
                raise ValueError(
                    f"filing_dates_by_year에 최근 회계연도({latest_fy})가 없다 - "
                    f"그 해가 fcf0를 결정하므로 PIT 검증의 핵심이다. 모르면 "
                    f"filing_dates_by_year 자체를 None으로 둘 것."
                )
            if self.analysis_as_of is None:
                raise ValueError(
                    "filing_dates_by_year를 넣으려면 analysis_as_of도 필요하다 - "
                    "비교 기준일이 없으면 filing_date만으로는 미래정보 여부를 "
                    "판정할 수 없다(계약서 22절)."
                )

        if self.margin_years is None:
            self.margin_years = sorted(self.revenue_by_year)[-5:]


def _parse_iso_date(value, label: str) -> date:
    """ISO 날짜 문자열(YYYY-MM-DD)을 date로. 형식이 틀리면 즉시 거부한다."""
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError):
        raise ValueError(
            f"{label}={value!r}: ISO 날짜(YYYY-MM-DD) 형식이어야 한다(v3.47)."
        )


# Point-in-Time 상태 어휘 - 계약서 21절
PIT_VALID = "PIT_VALID"
PIT_INVALID = "PIT_INVALID"
PIT_UNKNOWN = "PIT_UNKNOWN"


def evaluate_point_in_time(inputs: "AnalysisInputs") -> dict:
    """
    이 분석이 "그 시점에 실제로 이용 가능했던 정보만 썼는가"를 판정한다.

    계약서 22절의 규칙 그대로다:
        filing_date <= analysis_as_of  -> 사용 가능
        filing_date >  analysis_as_of  -> 미래정보(사용 금지)
        filing_date 미상               -> PIT_UNKNOWN (valid로 위장하지 않는다)

    ⚠️ **이 함수는 Historical Replay가 아니다.** replay는 계약서 70절의 7개
    조건을 전부 만족해야 하는데, 이 저장소는 아직 원자료 스냅샷도 소스 타이밍
    검증도 갖추지 못했다(docs/change_plan.md C-09~C-11 참고). 여기서 하는 것은
    그 7개 조건 중 **2개(분석일 확정, 소스 타이밍 검증 가능)의 토대**를 지금부터
    쌓기 시작하는 것뿐이다.

    반환값: {"status", "analysis_as_of", "filing_dates_by_year", "violations"}
    """
    if inputs.analysis_as_of is None or inputs.filing_dates_by_year is None:
        return {
            "status": PIT_UNKNOWN,
            "analysis_as_of": inputs.analysis_as_of,
            "filing_dates_by_year": inputs.filing_dates_by_year,
            "violations": [],
            "note": (
                "analysis_as_of 또는 filing_dates_by_year가 없어 그 시점에 이 "
                "데이터가 공시돼 있었는지 검증할 수 없다. meta.analyzed_at은 "
                "코드를 실행한 시각일 뿐 공시 여부를 보증하지 않는다."
            ),
        }

    as_of = _parse_iso_date(inputs.analysis_as_of, "analysis_as_of")
    violations = [
        {
            "fiscal_year": year,
            "filing_date": str(value),
            "days_after_analysis": (_parse_iso_date(value, "filing_date") - as_of).days,
        }
        for year, value in sorted(inputs.filing_dates_by_year.items())
        if _parse_iso_date(value, "filing_date") > as_of
    ]
    return {
        "status": PIT_INVALID if violations else PIT_VALID,
        "analysis_as_of": inputs.analysis_as_of,
        "filing_dates_by_year": {
            str(k): str(v) for k, v in sorted(inputs.filing_dates_by_year.items())
        },
        "violations": violations,
        "note": None,
    }


def _cagr(start: float, end: float, years: int, label: str = "") -> float:
    """
    CAGR 계산. start<=0이면 계산이 성립하지 않으므로 예외를 던진다.

    ⚠️ v3.19 자체감사에서 발견: 가드가 없으면 start가 음수일 때 파이썬이
    **복소수를 조용히 반환**한다((100/-50)**(1/5) -> -0.07+0.68j). 그 복소수가
    DRS/성장률 계산을 타고 흘러 들어가면 어디서 틀렸는지 추적조차 어렵다.
    FCF 적자 연도가 기준연도가 되는 경우(INTC/BYND 등)에 실제로 발생 가능하다.
    """
    if start <= 0:
        raise ValueError(
            f"CAGR 계산 불가{f'({label})' if label else ''}: 시작값이 {start:,.0f}로 0 이하다. "
            f"FCF 적자 등으로 기준연도가 음수면 CAGR은 정의되지 않는다(v3.19 가드). "
            f"해당 지표를 제외하거나 [Model Not Applicable] 처리할 것."
        )
    if end <= 0:
        raise ValueError(
            f"CAGR 계산 불가{f'({label})' if label else ''}: 종료값이 {end:,.0f}로 0 이하다. "
            f"흑자->적자 전환은 CAGR로 표현할 수 없다(v3.19 가드)."
        )
    return (end / start) ** (1 / years) - 1


def run_analysis(inputs: AnalysisInputs) -> dict:
    """
    전체 파이프라인을 한 번에 실행하고 모든 중간값을 담은 dict를 반환한다.

    단위 처리는 전부 여기서 책임진다(호출부가 소수/퍼센트를 헷갈릴 여지 없음):
    - 성장률·수익률은 전부 소수로 흐른다
    - rar만 퍼센트 규약이므로 rar_from_decimal_return()으로 안전하게 변환
    - structural_discount_rate/classify_lynch_type에는 10억 단위 시총을 넘긴다
    """
    years = sorted(inputs.revenue_by_year)
    rev = inputs.revenue_by_year
    fcf = {
        y: inputs.operating_cashflow_by_year[y] - inputs.capex_by_year[y] for y in years
    }

    if len(years) < 6:
        raise ValueError(
            f"재무 시계열이 {len(years)}개 연도뿐이라 5년 CAGR도 계산할 수 없다. "
            f"최소 6개 연도가 필요하다."
        )

    data_limitations = []

    # ── v3.21: 5년 CAGR 기준연도 ──────────────────────────────────────────
    # 기본은 years[-6](5년 전). override가 있으면 매출·FCF **양쪽 모두** 그 해를
    # 기준으로 쓴다(서로 다른 창을 쓰면 realistic_growth_estimate의 min() 비교가
    # 성립하지 않는다). BKNG에서 실제로 필요해져 추가한 기능이다.
    base_5y = years[-6]
    span_5y = 5
    if inputs.cagr_base_year_override is not None:
        base_5y = inputs.cagr_base_year_override
        span_5y = years[-1] - base_5y
        data_limitations.append(
            f"[CAGR 기준연도 변경] 기본 기준연도({years[-6]}) 대신 {base_5y}년을 "
            f"기준으로 {span_5y}년 CAGR을 산출했다(매출·FCF 동일 적용). "
            f"기준연도 선택은 성장률을 통째로 바꾸므로 사유를 반드시 대조할 것: "
            f"{inputs.cagr_base_year_override_reason}"
        )

    rev_cagr_3y = _cagr(rev[years[-4]], rev[years[-1]], 3, "revenue 3y")
    rev_cagr_5y = _cagr(rev[base_5y], rev[years[-1]], span_5y, "revenue 5y")
    if len(years) >= 11:
        rev_cagr_10y = _cagr(rev[years[-11]], rev[years[-1]], 10, "revenue 10y")
    else:
        # ⚠️ v3.19 자체감사에서 발견: 예전 구현은 10년치가 없으면 아무 기록 없이
        # 5y 값을 10y 자리에 끼워 넣었다. 그러면 revenue_volatility_score가 보는
        # 표준편차가 인위적으로 줄어 DRS가 실제보다 낮게 나오고, 아무도 그 사실을
        # 알 수 없다. 대체는 유지하되 반드시 명시적으로 기록한다.
        rev_cagr_10y = None
        data_limitations.append(
            f"10년 CAGR 산출 불가({len(years)}개 연도만 확보). revenue_volatility_score와 "
            f"structural_discount_rate에 5년 CAGR({rev_cagr_5y*100:.2f}%)을 대체 입력했다. "
            f"3/5/10y 편차가 인위적으로 축소되므로 DRS의 revenue_volatility 항목과 "
            f"구조적 할인율이 모두 실제보다 낮게(=관대하게) 나왔을 수 있다."
        )

    fcf_cagr_5y = _cagr(fcf[base_5y], fcf[years[-1]], span_5y, "FCF 5y")
    fcf0 = fcf[years[-1]]

    # ⚠️ v3.46(2026-08-15 Phase 2): 시가총액의 스케일/통화 오류는 single_stage
    # 경로에서 경고 없이 판정까지 흘러간다(BRO 실측: 100배 과소 시 Gap이
    # +7.43%p -> +96.22%p로 부풀어도 무경고 통과). 자동보정 없이 탐지만 한다.
    _scale_ok, _scale_warning = check_scale_plausibility(fcf0, inputs.market_cap)
    if not _scale_ok:
        data_limitations.append(_scale_warning)

    # ── v3.47: Point-in-Time 판정(계산에는 관여하지 않는 순수 기록·검증) ──
    point_in_time = evaluate_point_in_time(inputs)
    if point_in_time["status"] == PIT_INVALID:
        raise ValueError(
            f"[미래정보 사용] analysis_as_of({inputs.analysis_as_of}) 이후에 "
            f"공시된 데이터가 입력에 섞여 있다: {point_in_time['violations']}. "
            f"그 시점에 존재하지 않던 정보로 그 시점의 판단을 만드는 것이라 "
            f"결과가 무의미하다(계약서 5.5절). analysis_as_of를 실제 분석 시점으로 "
            f"고치거나, 해당 회계연도를 입력에서 제외할 것."
        )
    if point_in_time["status"] == PIT_UNKNOWN:
        data_limitations.append(
            f"[PIT 미검증] {point_in_time['note']} 이 분석은 Historical Replay "
            f"대상이 될 수 없다(계약서 70절 조건 미충족). 새 분석부터 "
            f"analysis_as_of와 filing_dates_by_year를 채워나갈 것."
        )

    yoy = [(years[i], rev[years[i]] / rev[years[i - 1]] - 1) for i in range(1, len(years))]
    worst_yoy = min(g for _, g in yoy)
    worst_year = [y for y, g in yoy if g == worst_yoy][0]

    op_margins = [
        inputs.operating_income_by_year[y] / rev[y] for y in inputs.margin_years
    ]
    net_debt_to_ebitda = inputs.net_debt / inputs.ebitda

    drs_components = {
        "revenue_volatility": revenue_volatility_score(
            rev_cagr_3y, rev_cagr_5y, rev_cagr_10y if rev_cagr_10y is not None else rev_cagr_5y
        ),
        "margin_volatility": margin_volatility_score(op_margins),
        "leverage": leverage_score(net_debt_to_ebitda),
        "cyclicality": cyclicality_score(worst_yoy, inputs.demand_sensitivity_pct),
        "competition_intensity": competition_intensity_score(
            inputs.competitor_threat_weights,
            inputs.market_share_trend_pp_per_year,
            inputs.active_antitrust_or_regulatory_case,
        ),
    }
    drs = DRSInputs(**drs_components).score()

    market_cap_b = inputs.market_cap / 1e9
    auto_lynch_type, lynch_note = classify_lynch_type(
        rev_cagr_5y, drs_components["cyclicality"], market_cap_b
    )
    lynch_type = inputs.lynch_type_override or auto_lynch_type

    # ⚠️ v3.24 버그수정(2026-08-01 방법론 감사 M-3): 10년 데이터가 없을 때 위
    # data_limitations 경고문은 "5년 CAGR을 대체 입력했다"고 명시하는데, 실제
    # 코드는 여태 rev_cagr_3y를 대체값으로 넣고 있었다 - trend_delta가
    # rev_cagr_3y - rev_cagr_3y = 0으로 항상 정확히 0이 되어 구조적 할인율이
    # 신호 없이 base_discount(10%)+시총가산으로만 고정되는 결과를 낳았다
    # (감사 시점 36종목 중 16개가 정확히 10.00%였던 원인). 경고문이 이미
    # 약속한 대로 rev_cagr_5y로 맞춘다 - 18개 ledger에서 재계산해보니 편차는
    # -1.91%p(GWRE)~+8.35%p(SE)로, 특히 SE는 판정에 영향을 줄 수 있는 크기다.
    structural_discount = structural_discount_rate(
        rev_cagr_3y,
        rev_cagr_10y if rev_cagr_10y is not None else rev_cagr_5y,
        market_cap_b,
    )

    # ⚠️ v3.19 전면점검에서 발견(2026-07-26): check_deceleration_double_count()는
    # v3.8부터 엔진에 있었지만 pipeline.py가 만들어진 이래 한 번도 import되지
    # 않아 실행 경로에서 호출된 적이 없었다("손배선 대신 pipeline.py를 쓰라"는
    # 원칙이 있어도 pipeline.py 자체가 엔진 안전장치를 빠뜨리면 무력화된다).
    # "하향 오버라이드"는 lynch_type_override의 성장상한(g_max)이 자동분류보다
    # 낮은 경우로 기계적으로 정의한다(주관적 판단 불필요, LYNCH_TYPE_CAPS만 비교).
    lynch_type_overridden_down = (
        inputs.lynch_type_override is not None
        and LYNCH_TYPE_CAPS[lynch_type][1] < LYNCH_TYPE_CAPS[auto_lynch_type][1]
    )
    _, double_count_warning = check_deceleration_double_count(
        structural_discount, lynch_type_overridden_down
    )
    if double_count_warning:
        data_limitations.append(double_count_warning)

    realistic_growth, growth_breakdown = realistic_growth_estimate(
        revenue_cagr_3y=rev_cagr_3y,
        revenue_cagr_5y=rev_cagr_5y,
        revenue_cagr_10y=rev_cagr_10y,
        fcf_cagr_5y=fcf_cagr_5y,
        structural_discount_pct=structural_discount,
        lynch_type=lynch_type,
    )

    # ── v3.20: capex 급증 분류 배선 ──────────────────────────────────────
    # v3.6/v3.7부터 엔진에 있었으나 pipeline이 import조차 하지 않아 한 번도
    # 실행되지 않던 경로. NVO(매출CAGR 21.7% vs FCF CAGR 4.92%, capex 5년새
    # 9.5배 폭증)가 스크리닝에서 걸리면서 실제 필요성이 실증되어 배선했다.
    #
    # ⚠️ 순서가 중요하다: fcf_conservatism_adjustment는 revenue_weighted_cagr을
    # 요구하는데, 이를 여기서 다시 계산하면 realistic_growth_estimate 내부의
    # 가중평균 로직(3y/5y/10y, 0.5/0.3/0.2)과 미묘하게 어긋나는 새 버그가 생긴다.
    # 그래서 위에서 이미 계산된 breakdown["base_growth_before_fcf_check"]를
    # 그대로 재사용하고, 조정된 FCF CAGR로 한 번 더 호출한다.
    capex_adjustment = None
    if inputs.capex_classification is not None:
        capex_years = years[-5:]
        capex_intensity = capex_intensity_from_series(
            [inputs.capex_by_year[y] for y in capex_years],
            [rev[y] for y in capex_years],
        )
        adjusted_fcf_cagr, capex_reason = fcf_conservatism_adjustment(
            revenue_weighted_cagr=growth_breakdown["base_growth_before_fcf_check"],
            fcf_cagr_5y=fcf_cagr_5y,
            capex_to_revenue_current=capex_intensity["current"],
            capex_to_revenue_5y_avg=capex_intensity["avg"],
            classification=inputs.capex_classification,
            revenue_cagr_3y=rev_cagr_3y,
            revenue_cagr_10y=rev_cagr_10y,
        )
        capex_adjustment = {
            "classification": inputs.capex_classification,
            "basis": inputs.capex_classification_basis,
            "capex_intensity": capex_intensity,
            "fcf_cagr_before": fcf_cagr_5y,
            "fcf_cagr_after": adjusted_fcf_cagr,
            "reason": capex_reason,
        }
        if adjusted_fcf_cagr != fcf_cagr_5y:
            realistic_growth, growth_breakdown = realistic_growth_estimate(
                revenue_cagr_3y=rev_cagr_3y,
                revenue_cagr_5y=rev_cagr_5y,
                revenue_cagr_10y=rev_cagr_10y,
                fcf_cagr_5y=adjusted_fcf_cagr,
                structural_discount_pct=structural_discount,
                lynch_type=lynch_type,
            )
            data_limitations.append(
                f"[capex 분류 조정] capex/매출 비중이 "
                f"{capex_intensity['delta']*100:+.1f}%p 변동했고 "
                f"'{inputs.capex_classification}'로 분류해 FCF CAGR을 "
                f"{fcf_cagr_5y*100:.2f}% -> {adjusted_fcf_cagr*100:.2f}%로 조정했다. "
                f"이 분류는 주관적 입력이며 판정을 뒤집을 수 있으므로 근거를 "
                f"반드시 대조할 것: {inputs.capex_classification_basis}"
            )
        if "정합성 경고" in (capex_reason or ""):
            data_limitations.append(f"[capex 정합성] {capex_reason}")

    # ⚠️ v3.24(2026-08-01 방법론 감사 M-1, 권고 #6): Lynch 유형별 성장상한이
    # 바인딩되면 Realistic Growth는 매출·FCF CAGR 계산과 무관하게 상한값
    # 그대로 고정된다 - 즉 Gap = 상한 - Implied Growth가 되어, 이 종목의
    # 순위는 오직 "누가 더 싼가(Implied Growth)"로만 결정되고 공들여 계산한
    # 성장분석은 결과에 기여하지 않는다. 이 상한값 자체의 근거는 코드에 없다
    # (LYNCH_TYPE_CAPS 주석 참고) - 최소한 그 사실을 눈에 보이게 남긴다.
    if growth_breakdown["cap_applied"] and "상한" in growth_breakdown["cap_applied"]:
        data_limitations.append(
            f"[성장상한 바인딩] {lynch_type} 유형의 성장상한"
            f"({realistic_growth*100:.2f}%)이 매출·FCF CAGR 기반 계산값을 덮어썼다 - "
            f"Realistic Growth는 이 상한값 그대로이며 성장분석 자체는 결과에 기여하지 "
            f"않는다. 이 종목의 Expectation Gap은 사실상 Implied Growth 단독으로 "
            f"결정되므로, 다른 종목과 순위를 비교할 때 이 점을 감안할 것(상한 근거 "
            f"자체가 코드/문서 어디에도 검증된 바 없음 - 2026-08-01 방법론 감사 M-1)."
        )

    # ── v3.28: Realistic Growth 직접 오버라이드 배선 ────────────────────
    # 위 캡바인딩 경고까지 전부 계산된 뒤 적용한다 - "원래는 캡이 걸렸었다"는
    # 사실 자체가 진단정보로서 남아있어야 다음 분석자가 왜 오버라이드가
    # 필요했는지 추적할 수 있다.
    if inputs.realistic_growth_override is not None:
        pre_override_growth = realistic_growth
        pre_override_cap_note = growth_breakdown.get("cap_applied")
        realistic_growth = inputs.realistic_growth_override
        growth_breakdown = dict(growth_breakdown)
        growth_breakdown["realistic_growth_override_applied"] = {
            "pre_override_growth": pre_override_growth,
            "pre_override_cap_note": pre_override_cap_note,
            "override_value": inputs.realistic_growth_override,
            "reason": inputs.realistic_growth_override_reason,
        }
        growth_breakdown["final_realistic_growth"] = realistic_growth
        # v3.32 버그수정: 오버라이드로 캡을 우회했는데도 cap_applied에 캡 문구가
        # 그대로 남아 있어 (a) ledger가 자기모순을 일으키고(ROP: realistic_growth
        # 5.5%인데 cap_applied는 "상한 캡 적용(12.0%)") (b) 그 값이 그대로
        # confidence_score(lynch_type_cap_applied=...)로 흘러가 걸리지도 않은 캡을
        # 근거로 -5점이 붙었다. 캡은 실제로 적용되지 않았으므로 None으로 되돌리고
        # (원래 문구는 위 pre_override_cap_note에 보존된다), 감점은 실제 원인인
        # realistic_growth_overridden 항목이 동일하게 -5로 이어받는다.
        growth_breakdown["cap_applied"] = None
        data_limitations.append(
            f"[Realistic Growth 오버라이드] CAGR 계산·Lynch 캡 기반값"
            f"({pre_override_growth*100:.2f}%, {pre_override_cap_note or '캡 미적용'})을 "
            f"우회하고 {realistic_growth*100:.2f}%를 직접 사용했다. 사유: "
            f"{inputs.realistic_growth_override_reason}"
        )

    erp = erp_from_drs(drs)
    r = inputs.risk_free_rate + erp
    n = capped_n(inputs.n_requested)
    g_terminal = default_terminal_growth(inputs.risk_free_rate)

    models = compare_implied_growth_models(inputs.market_cap, fcf0, r, n, g_terminal)
    if models.get("divergence_warning"):
        data_limitations.append(models["divergence_warning"])
    implied_growth = models[inputs.model_used]
    if implied_growth is None:
        raise ValueError(
            f"선택한 모델({inputs.model_used})로 Implied Growth 계산 불가: "
            f"{models['errors'].get(inputs.model_used)} -> [Model Not Applicable] 처리할 것"
        )
    gap = realistic_growth - implied_growth

    growth_rates = bull_bear_base_growth_rates(realistic_growth, lynch_type)
    scenario_returns = {
        key: scenario_return_from_growth(
            inputs.market_cap, fcf0, r, n, g_terminal, growth_rates[g_key]
        )
        for key, g_key in [("bull", "g_bull"), ("base", "g_base"), ("bear", "g_bear")]
    }
    p_bull, p_base, p_bear, prob_rationale = scenario_probabilities_from_drs(drs)
    er_decimal = expected_return(
        p_bull, scenario_returns["bull"],
        p_base, scenario_returns["base"],
        p_bear, scenario_returns["bear"],
    )
    # ⚠️ 여기가 v3.19 사고 지점. 반드시 decimal 전용 함수를 쓴다.
    rar_value = rar_from_decimal_return(er_decimal, drs)

    # v3.26(2026-08-02 방법론 감사 M-2): RAR=ER/DRS는 ER이 음수일 때 방향이
    # 뒤집힌다 - 음수를 더 큰 DRS로 나누면 0에 가까워져(=덜 나빠 보여) DRS가
    # 높을수록 오히려 "개선된" 것처럼 보인다. CDNS 원자료로 DRS만 20→80으로
    # 올려 검증: RAR -0.95→-0.36(같은 종목, ER은 오히려 더 나빠졌는데도).
    # ER>=0에서는 반대로 정상 작동한다(DRS 클수록 RAR 작아짐, PDD로 검증).
    # RAR 공식 자체를 바꾸면 트래커에 축적된 과거 RAR 전체와 비교불가능해지므로
    # (v3.19 단위규약과 동일한 이유로) 값은 그대로 두고 경고만 남긴다.
    if er_decimal < 0:
        data_limitations.append(
            f"[RAR 방향성 경고] 기대수익률이 음수({er_decimal*100:.2f}%)라 "
            f"RAR=ER/DRS 공식이 의도와 반대로 움직이는 구간이다 - DRS(위험도)가 "
            f"높을수록 음수 RAR이 0에 가깝게 압축돼 실제로는 위험이 클수록 "
            f"'덜 나빠 보이는' 착시가 생긴다(2026-08-02 방법론 감사 M-2, CDNS 원자료로 "
            f"기계적 검증: DRS 20→80일 때 같은 종목 RAR이 -0.95→-0.36로 개선돼 보임). "
            f"이 종목은 RAR 절대값만으로 판단하지 말고 Expectation Gap을 우선 참고할 것."
        )

    # ⚠️ 여기에 inputs.model_used를 넘기면 안 된다(v3.19 골든테스트가 잡아낸 버그).
    # RAR은 scenario_return_from_growth() -> _two_stage_market_cap() 경로라
    # **Section 5에서 single_stage를 썼더라도 항상 two_stage로 산출**된다.
    # v3.13 구조적 편향은 그 two_stage 경로의 min_spread 가드에서 나오는 것이므로,
    # Section 5 모델이 아니라 시나리오 모델(=항상 two_stage)로 판정해야 한다.
    SCENARIO_MODEL = "two_stage"
    bias_flag, bias_note = check_stalwart_two_stage_bias(
        lynch_type, rar_value, SCENARIO_MODEL
    )
    # ⚠️ v3.19 근본수정(2026-07-26): 2026-07-25에는 이 함수가 항상 two_stage로만
    # 판정해 Section 5가 single_stage를 쓴 경우 서로 다른 모델을 비교하는
    # 오류가 있었다(WCN/WM/IDXX에서 발견, 당시엔 [강건성점검 해석주의] 경고문으로
    # 임시 우회). 이제 engine.expectation_gap_engine.expectation_gap_sensitivity_check가
    # model_used를 받으므로, Section 5가 실제로 쓴 모델을 그대로 넘겨 같은 모델끼리
    # 비교되도록 근본 수정했다. 이전 경고문 우회책은 더 이상 필요 없어 제거함.
    sensitivity = expectation_gap_sensitivity_check(
        inputs.market_cap, fcf0, r, 0.05, inputs.risk_free_rate,
        realistic_growth, n, g_terminal,
        model_used=inputs.model_used,
    )
    confidence = confidence_score(
        sensitivity_check_result=sensitivity,
        gap=gap,
        rar=rar_value,
        data_completeness_pct=inputs.data_completeness_pct,
        lynch_type_cap_applied=(growth_breakdown["cap_applied"] is not None),
        stalwart_two_stage_bias_flagged=bias_flag,
        realistic_growth_overridden=(inputs.realistic_growth_override is not None),
    )

    # ⚠️ v3.46 가시화(2026-08-15 Phase 0 감사 C-06): data_completeness_pct는
    # confidence_score에 최대 15점(round(0.9*15)=14점)을 기여하는데, ledger
    # 34종목 **전부**가 기본값 0.9를 그대로 쓰고 있었다 - 실제 데이터 완전성에서
    # 산출된 적이 한 번도 없다. 즉 Confidence는 "데이터 완전성을 반영한다"고
    # 표방하면서 그 축의 판별력이 정확히 0이다(계약서 3절 False Precision).
    #
    # 자동 계산하지 않는다 - 무엇이 "완전한 데이터"인지에 대한 근거가 이
    # 프로젝트에 없고, 근거 없는 새 공식을 만드는 것은 계약서 5.2절(금융 가정
    # 발명 금지) 위반이다. 점수도 바꾸지 않는다(기존 34종목 Confidence 불변).
    # 대신 기본값을 그대로 썼다는 사실만 눈에 보이게 남긴다.
    if inputs.data_completeness_pct == 0.9:
        data_limitations.append(
            f"[데이터 완전성 미실측] data_completeness_pct가 기본값(0.9)이다 - "
            f"Confidence에 자동 부여된 {round(0.9 * 15)}점은 실제 데이터 완전성을 "
            f"측정한 결과가 아니다(2026-08-15 감사 기준 ledger 34종목 전부가 이 "
            f"기본값). 이 종목의 Confidence를 다른 종목과 비교할 때 이 항목은 "
            f"판별력이 없다고 보고 나머지 항목으로 해석할 것."
        )

    # v3.32: 판정 규칙 사본을 제거하고 engine의 judgment_from_gap() 하나만 쓴다.
    judgment = judgment_from_gap(gap)

    # v3.27(2026-08-02): 기존 3단계 경계는 그대로 두고 6단계로 세분화만
    # 추가한다(S/A/B가 "저평가 가능성"의 부분집합, D/F가 "과대평가 가능성"의
    # 부분집합 - judgment_grade_from_gap() docstring 참고).
    judgment_grade = judgment_grade_from_gap(gap)

    # ── v3.22: 보험업 FCF-DCF 교차검증(ACGL/PGR 실증사례 기반) ──────────────
    # ROE x 유보율(지속가능성장률)과 P/B를 계산해 Realistic Growth와 대조한다.
    # ROE는 최근 최대 5개년 평균(단일연도는 언더라이팅 사이클 왜곡이 커서
    # PGR 사례에서 5개년 평균을 채택했다), 배당성향은 최근 최대 3개년 합산
    # 기준(연간 변동배당 관행이 있는 보험사가 있어 단일연도는 왜곡될 수 있다).
    insurer_cross_check = None
    if inputs.is_insurer:
        eq_years = sorted(inputs.shareholders_equity_by_year)
        roe_years = eq_years[-min(5, len(eq_years)):]
        roes = [
            inputs.net_income_by_year[y] / inputs.shareholders_equity_by_year[y]
            for y in roe_years
        ]
        avg_roe = sum(roes) / len(roes)

        div_years = sorted(inputs.dividends_paid_by_year)[-min(3, len(inputs.dividends_paid_by_year)):]
        total_dividends = sum(inputs.dividends_paid_by_year[y] for y in div_years)
        total_net_income = sum(inputs.net_income_by_year[y] for y in div_years)

        # ⚠️ v3.46 가드(2026-08-15 Phase 0 감사 C-03): 합산 순이익이 0 이하면
        # 배당성향이 정의되지 않는다. 가드가 없을 때의 실측 결과:
        #     순이익합계 -200, 배당 300 -> 배당성향 -1.50 -> 유보율 +2.50
        #                                 -> 지속가능성장률이 ROE보다 커짐(30%)
        #     배당 > 순이익            -> 유보율 음수 -> 성장률 부호 반전
        # 유보율은 정의상 0~1인데 그 밖의 값이 그대로 Realistic Growth와 대조돼
        # 경고를 내거나(또는 내지 않아) 판정 신뢰도 판단에 쓰였다. 대재해 노출
        # 재보험사(ACGL 유형)에서 손실 연도는 충분히 현실적이다.
        #
        # is_insurer는 "병기, 자동판정 안 함" 경로이므로 여기서 예외를 던져
        # 분석 전체를 막지 않는다 - 교차검증만 건너뛰고 그 사실을 남긴다.
        # (ACGL·PGR 기존 2건은 순이익 음수 연도가 0건이라 이 분기를 타지 않는다.)
        if total_net_income <= 0:
            insurer_cross_check = None
            data_limitations.append(
                f"[보험업 교차검증 불가] 배당성향 산출 구간({div_years})의 합산 "
                f"순이익이 {total_net_income:,.0f}으로 0 이하다 - 배당성향/유보율이 "
                f"정의되지 않아 지속가능성장률(ROE x 유보율) 교차검증을 건너뛴다"
                f"(v3.46 가드). 손실 연도가 창에 걸린 것이라면 창을 옮기지 말고 "
                f"(유리한 구간 선택이 된다) 이 종목은 FCF-DCF 결과를 보험업 "
                f"플로트 왜곡 관점에서 별도 수작업 검증할 것."
            )
        else:
            payout_ratio = total_dividends / total_net_income
            retention_ratio = 1 - payout_ratio
            sustainable_growth = avg_roe * retention_ratio
            if not (0.0 <= retention_ratio <= 1.0):
                data_limitations.append(
                    f"[보험업 유보율 정의역 이탈] 유보율이 {retention_ratio:.3f}로 "
                    f"0~1 범위를 벗어났다(배당성향 {payout_ratio:.3f}) - 배당이 "
                    f"순이익을 초과했거나 특별배당이 섞인 구간일 수 있다. "
                    f"지속가능성장률({sustainable_growth*100:.2f}%)을 그대로 "
                    f"신뢰하지 말 것(v3.46)."
                )

            latest_equity_year = max(inputs.shareholders_equity_by_year)
            price_to_book = (
                inputs.market_cap
                / inputs.shareholders_equity_by_year[latest_equity_year]
            )

            insurer_cross_check = {
                "roe_years_used": roe_years,
                "avg_roe": avg_roe,
                "dividend_years_used": div_years,
                "payout_ratio": payout_ratio,
                "retention_ratio": retention_ratio,
                "sustainable_growth": sustainable_growth,
                "price_to_book": price_to_book,
            }

            divergence = abs(realistic_growth - sustainable_growth)
            if divergence >= INSURER_GROWTH_DIVERGENCE_THRESHOLD:
                data_limitations.append(
                    f"[보험업 교차검증 경고] Realistic Growth({realistic_growth*100:.2f}%)와 "
                    f"지속가능성장률(ROE x 유보율={sustainable_growth*100:.2f}%, "
                    f"평균ROE {avg_roe*100:.2f}%/유보율 {retention_ratio*100:.2f}%)이 "
                    f"{divergence*100:.2f}%p 벌어져 있다(경고임계값 "
                    f"{INSURER_GROWTH_DIVERGENCE_THRESHOLD*100:.0f}%p). FCF-DCF가 보험업의 "
                    f"플로트 성장을 유기적 성장으로 착각했을 가능성이 있다(ACGL 선례: "
                    f"Gap 31.44%p가 이 방식으로 과장 확인됨). P/B={price_to_book:.2f}배도 "
                    f"함께 참고할 것 - 낮으면(~1.5배 이하) 시장이 아직 재평가하지 않았다는 "
                    f"뜻이라 방향은 유지하되 크기를 할인, 높으면(~3배 이상) 이미 재평가됐을 "
                    f"수 있어 판정 신뢰도를 더 낮출 것."
                )
            else:
                data_limitations.append(
                    f"[보험업 교차검증] Realistic Growth({realistic_growth*100:.2f}%)와 "
                    f"지속가능성장률({sustainable_growth*100:.2f}%)이 {divergence*100:.2f}%p "
                    f"이내로 근접해 FCF-DCF 성장추정이 비교적 정합적이다(PGR 선례). "
                    f"P/B={price_to_book:.2f}배는 별도로 판정 신뢰도 판단에 참고할 것."
                )

    # ── v3.23: SBC 병기 교차검증(2026-08-01 방법론 감사 Critical-1) ─────────
    # FCF = OCF - capex는 SBC를 암묵적으로 주주 귀속 현금으로 취급한다.
    # sbc_by_year가 있으면 최근연도 SBC를 fcf0에서 추가로 차감한 대안 시나리오를
    # 같은 model_used로 계산해 병기한다 - 어느 쪽이 "맞다"고 자동 판정하지 않는다
    # (is_insurer가 지속가능성장률만 병기하고 판정을 덮어쓰지 않는 것과 동일 원칙).
    sbc_cross_check = None
    if inputs.sbc_by_year is not None:
        sbc0 = inputs.sbc_by_year[years[-1]]
        fcf0_sbc_adjusted = fcf0 - sbc0
        if fcf0_sbc_adjusted <= 0:
            sbc_cross_check = {
                "sbc0": sbc0,
                "sbc_to_fcf_pct": sbc0 / fcf0 if fcf0 else None,
                "fcf0_sbc_adjusted": fcf0_sbc_adjusted,
                "implied_growth_sbc_adjusted": None,
                "gap_sbc_adjusted": None,
                "judgment_sbc_adjusted": None,
                "judgment_flipped": None,
            }
            data_limitations.append(
                f"[SBC 교차검증] SBC(${sbc0:,.0f})를 FCF0(${fcf0:,.0f})에서 차감하면 "
                f"음수가 되어 SBC차감 시나리오는 [Model Not Applicable]이다 - SBC가 "
                f"FCF보다 큰 비중을 차지한다는 뜻으로 그 자체가 경고 신호다."
            )
        else:
            models_sbc = compare_implied_growth_models(
                inputs.market_cap, fcf0_sbc_adjusted, r, n, g_terminal
            )
            ig_sbc = models_sbc[inputs.model_used]
            gap_sbc = realistic_growth - ig_sbc if ig_sbc is not None else None
            # v3.32: 여기도 판정 규칙 사본이 있었다 - judgment_from_gap()으로 통일.
            judgment_sbc = judgment_from_gap(gap_sbc) if gap_sbc is not None else None
            judgment_flipped = judgment_sbc is not None and judgment_sbc != judgment
            sbc_cross_check = {
                "sbc0": sbc0,
                "sbc_to_fcf_pct": sbc0 / fcf0,
                "fcf0_sbc_adjusted": fcf0_sbc_adjusted,
                "implied_growth_sbc_adjusted": ig_sbc,
                "gap_sbc_adjusted": gap_sbc,
                "judgment_sbc_adjusted": judgment_sbc,
                "judgment_flipped": judgment_flipped,
            }
            sbc_pct = sbc0 / fcf0
            if judgment_flipped:
                data_limitations.append(
                    f"[SBC 교차검증 경고] SBC가 FCF0의 {sbc_pct*100:.0f}%를 차지한다. "
                    f"SBC를 실제 비용으로 차감하면 판정이 '{judgment}' -> "
                    f"'{judgment_sbc}'로 **뒤집힌다**(Gap {gap*100:+.2f}%p -> "
                    f"{gap_sbc*100:+.2f}%p, 2026-08-01 방법론 감사에서 WDAY가 실제로 "
                    f"이 경로로 뒤집힌 선례가 있음). 이 종목의 판정은 SBC 처리방식에 "
                    f"민감하므로 액면 그대로 신뢰하지 말 것."
                )
            elif sbc_pct >= 0.30:
                data_limitations.append(
                    f"[SBC 교차검증] SBC가 FCF0의 {sbc_pct*100:.0f}%로 상당히 크다 "
                    f"(SBC차감 시 Gap {gap*100:+.2f}%p -> {gap_sbc*100:+.2f}%p). "
                    f"판정은 유지되나 여유폭이 SBC 처리방식에 따라 크게 흔들린다."
                )

    return {
        "meta": {
            "ticker": inputs.ticker,
            "company_name": inputs.company_name,
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
            "engine_version": ENGINE_VERSION,
            "data_sources": inputs.data_sources,
            "falsification_conditions": inputs.falsification_conditions,
            "price_at_analysis": inputs.price_at_analysis,
            "currency": inputs.currency,
            "point_in_time": point_in_time,
            # v3.50 §6: 값 단위 출처. 없으면 PROVENANCE_UNKNOWN이 정확한 상태다
            # (기존 34종목이 전부 여기 해당 - 소급 생성하지 않는다).
            "provenance": inputs.provenance or {"status": PROVENANCE_UNKNOWN},
        },
        "data_limitations": data_limitations,
        "inputs": asdict(inputs),
        "derived": {
            "revenue_cagr_3y": rev_cagr_3y,
            "revenue_cagr_5y": rev_cagr_5y,
            "cagr_5y_base_year": base_5y,
            "cagr_5y_span": span_5y,
            "revenue_cagr_10y": rev_cagr_10y,
            "fcf_cagr_5y": fcf_cagr_5y,
            "fcf0": fcf0,
            "fcf_by_year": fcf,
            "worst_yoy_revenue_growth": worst_yoy,
            "worst_yoy_year": worst_year,
            "operating_margins": op_margins,
            "net_debt_to_ebitda": net_debt_to_ebitda,
        },
        "drs": {"components": drs_components, "score": drs},
        "lynch": {
            "auto_classified": auto_lynch_type,
            "auto_note": lynch_note,
            "used": lynch_type,
            "override_reason": inputs.lynch_type_override_reason,
            "overridden_down": lynch_type_overridden_down,
        },
        "discount_rate": {"rf": inputs.risk_free_rate, "erp": erp, "r": r,
                          "n": n, "g_terminal": g_terminal},
        "growth": {
            "structural_discount_pct": structural_discount,
            "realistic_growth": realistic_growth,
            "breakdown": growth_breakdown,
            "capex_adjustment": capex_adjustment,
        },
        "implied_growth": {
            "models": models,
            "model_used": inputs.model_used,
            "model_choice_reason": inputs.model_choice_reason,
            "value": implied_growth,
        },
        "expectation_gap": gap,
        "scenarios": {
            "growth_rates": growth_rates,
            "returns": scenario_returns,
            "probabilities": {"bull": p_bull, "base": p_base, "bear": p_bear},
            "probability_rationale": prob_rationale,
            "expected_return_decimal": er_decimal,
        },
        "rar": rar_value,
        "stalwart_bias": {"flagged": bias_flag, "note": bias_note},
        "sensitivity_check": sensitivity,
        "confidence": confidence,
        "judgment": judgment,
        "judgment_grade": judgment_grade,
        "insurer_cross_check": insurer_cross_check,
        "sbc_cross_check": sbc_cross_check,
    }


def cross_check_prior_record(result: dict, prior: dict) -> list:
    """
    v3.19 신규: 새로 계산한 결과를 **과거 기록과 자동 대조**한다.

    왜 코드로 넣는가: "기존 기록이 있으면 대조하라"는 규칙을 문서로만 두면
    지켜지지 않는다는 걸 이 프로젝트가 세 번 겪었다(self_check, confidence_score,
    claim/lock 모두 문서에만 있다가 무력화됐다). PH 모델선택 실수도 사람이
    우연히 대조해서 잡았을 뿐이다.

    prior: 트래커에 남아있는 과거 값 {"rar":..., "drs":..., "gap":...,
           "implied_growth":..., "engine_version":..., "analyzed_at":...}
           (모르는 항목은 생략 가능)

    반환값: 경고 문자열 리스트(문제 없으면 빈 리스트)
    """
    warnings = []

    prior_rar, new_rar = prior.get("rar"), result["rar"]
    if prior_rar is not None and new_rar and abs(new_rar) > 1e-9:
        ratio = abs(prior_rar / new_rar)
        if ratio > 20 or ratio < 0.05:
            warnings.append(
                f"[RAR 스케일 경고] 과거 기록 {prior_rar:.4f} vs 재계산 {new_rar:.4f} "
                f"(배율 {ratio:.0f}x). 100배 근처면 rar() 단위 사고(v3.19)일 가능성이 크다. "
                f"어느 쪽이 퍼센트 규약인지 확인할 것 - RARxDRS가 함의하는 기대수익률이 "
                f"|1%| 미만이면 그쪽이 잘못된 값이다."
            )
        if (prior_rar >= 0) != (new_rar >= 0):
            warnings.append(
                f"[RAR 부호 반전] 과거 {prior_rar:+.4f} -> 재계산 {new_rar:+.4f}. "
                f"부호가 바뀌면 5·7번 정합성 판정과 confidence가 함께 달라진다. "
                f"입력값 차이인지 로직 변경인지 특정할 것."
            )

    prior_gap, new_gap = prior.get("gap"), result["expectation_gap"]
    if prior_gap is not None:
        if abs(prior_gap - new_gap) > 0.03:
            warnings.append(
                f"[Gap 괴리] 과거 {prior_gap*100:+.2f}%p vs 재계산 {new_gap*100:+.2f}%p "
                f"({abs(prior_gap-new_gap)*100:.2f}%p 차이). 모델선택(single/two stage)이 "
                f"다른 경우가 대표적 원인이다 - PH가 정확히 이 사례였다."
            )

    prior_ig = prior.get("implied_growth")
    if prior_ig is not None:
        models = result["implied_growth"]["models"]
        best = min(
            ((k, v) for k, v in (("single_stage", models["single_stage"]),
                                 ("two_stage", models["two_stage"])) if v is not None),
            key=lambda kv: abs(kv[1] - prior_ig), default=None,
        )
        if best and best[0] != result["implied_growth"]["model_used"]:
            warnings.append(
                f"[모델 불일치 의심] 과거 내재성장률 {prior_ig*100:.2f}%는 "
                f"{best[0]}({best[1]*100:.2f}%)에 더 가까운데, 이번 분석은 "
                f"{result['implied_growth']['model_used']}를 썼다. 과거 관행과 다른 모델을 "
                f"쓰는 것이라면 model_choice_reason에 그 사실과 이유를 명시할 것."
            )

    prior_drs = prior.get("drs")
    if prior_drs is not None and abs(prior_drs - result["drs"]["score"]) > 10:
        warnings.append(
            f"[DRS 괴리] 과거 {prior_drs:.2f} vs 재계산 {result['drs']['score']:.2f}. "
            f"주관적 입력(경쟁강도/수요민감도)이 세션마다 달라진 결과일 수 있다 - "
            f"양쪽 subjective_input_basis를 대조할 것."
        )

    return warnings


def _ledger_payload_without_timestamp(obj: dict) -> str:
    """
    두 ledger 내용이 '실질적으로 같은지' 비교하기 위한 정규화 문자열.

    제외 대상 2개:
    - `meta.analyzed_at` — 같은 입력으로 재실행하면 이 값만 달라진다는 것을
      실측으로 확인했다(감사 FM-4: analyzed_at 외 전 필드 동일).
    - `prior_cross_check` — v3.47에서 save_ledger가 저장 직전에 덧붙이는
      **파생 필드**다. `run_analysis()` 결과에는 없고 저장본에만 있으므로,
      제외하지 않으면 동일 입력 재실행이 "내용 다름"으로 오판된다
      (테스트 `test_save_ledger_allows_identical_rerun`이 실제로 잡아냈다).
      대조 결과는 조언일 뿐 분석 내용 자체가 아니므로 동일성 판단에서 뺀다.
    """
    trimmed = dict(obj)
    meta = dict(trimmed.get("meta", {}))
    meta.pop("analyzed_at", None)
    trimmed["meta"] = meta
    trimmed.pop("prior_cross_check", None)
    return json.dumps(trimmed, ensure_ascii=False, sort_keys=True, default=str)


def _find_prior_ledger(ticker: str, current_path: str, ledger_dir: str):
    """
    같은 티커의 **직전** ledger를 찾는다(현재 저장하려는 파일은 제외).
    파일명이 `<TICKER>_<YYYY-MM-DD>.json`이라 이름 정렬 = 날짜 정렬이다.
    """
    import glob as _glob

    candidates = [
        p
        for p in _glob.glob(os.path.join(ledger_dir, f"{ticker}_*.json"))
        if os.path.abspath(p) != os.path.abspath(current_path)
    ]
    if not candidates:
        return None, None
    prior_path = sorted(candidates)[-1]
    try:
        with open(prior_path, encoding="utf-8") as f:
            return prior_path, json.load(f)
    except (OSError, json.JSONDecodeError):
        return None, None


def save_ledger(result: dict, ledger_dir: str = "ledger", overwrite: bool = False,
                cross_check: bool = True) -> str:
    """
    분석 결과 전체(입력값 포함)를 JSON으로 저장한다.

    왜 필요한가: 큐22(Cadence)가 "계산은 했다"는 기록만 남고 입력값이 사라져
    전면 재수행해야 했고, CDNS/MNST/PH의 과거 RAR과 대조검증도 불가능했다.
    ledger 파일이 있으면 다음 세션이 같은 입력으로 재현하거나 차이를 특정할 수 있다.

    ⚠️ v3.46 덮어쓰기 가드(2026-08-15 Phase 0 감사 C-02): 파일명이
    `<TICKER>_<날짜>.json`이라 **같은 날 재실행하면 경로가 충돌**한다. 그전까지
    이 함수는 경고 없이 덮어썼고, 실측으로 재현했다 - Gap +0.10짜리 분석을
    저장한 뒤 Gap -0.30짜리를 저장하니 파일 1개만 남고 1차 결과는 흔적 없이
    사라졌다. ledger는 이 프로젝트의 유일한 재현 근거이므로(계약서 5.4/63절)
    조용한 소실은 가장 나쁜 실패 유형이다.

    설계 판단 - 무조건 금지하지 않는다:
    - **내용이 같으면(analyzed_at 제외) 그대로 통과**시킨다. 이 프로젝트의 표준
      관행인 "같은 입력으로 재실행해 값이 같은지 확인"(v3.19 sensitivity 근본수정,
      v3.32 33종목 전건 재실행 등)이 깨지면 안 되기 때문이다.
    - **내용이 다르면 예외**를 던진다. 의도한 갱신이면(정성조사 결과 반영 등)
      `overwrite=True`를 명시하게 해 "의도한 갱신"과 "사고에 의한 소실"을 구분한다.
    """
    os.makedirs(ledger_dir, exist_ok=True)
    date = result["meta"]["analyzed_at"][:10]
    path = os.path.join(ledger_dir, f"{result['meta']['ticker']}_{date}.json")

    if os.path.exists(path) and not overwrite:
        with open(path, encoding="utf-8") as f:
            try:
                existing = json.load(f)
            except json.JSONDecodeError:
                existing = None
        if existing is None or _ledger_payload_without_timestamp(
            existing
        ) != _ledger_payload_without_timestamp(result):
            raise FileExistsError(
                f"{path}에 내용이 다른 ledger가 이미 있다(v3.46 가드). 그대로 쓰면 "
                f"기존 분석이 흔적 없이 사라진다 - ledger는 이 프로젝트의 유일한 "
                f"재현 근거다. 의도한 갱신이라면(정성조사 결과 반영 등) "
                f"save_ledger(..., overwrite=True)로 명시할 것. 같은 입력을 "
                f"재실행한 것이라면 값이 달라진 이유를 먼저 특정할 것 - "
                f"analyzed_at을 제외한 전 필드가 같으면 이 예외는 발생하지 않는다."
            )

    # ── v3.47: 과거 기록 자동 대조(2026-08-15 Phase 3) ─────────────────────
    # 감사 T-2에서 확인한 사실: cross_check_prior_record()는 55개 스크립트 중
    # **1개(BKNG)**에서만 호출된다. CLAUDE.md는 "과거 기록이 있는 종목을
    # 재검증할 때 대조하라"고 규정하지만 강제 수단이 없었다.
    #
    # 이 프로젝트는 **문서로만 둔 규칙이 지켜지지 않는 것을 이미 세 번 겪었다**
    # (run_self_check·confidence_score·claim/lock). PH 모델선택 실수도 사람이
    # 우연히 대조해서 잡았을 뿐이다. 네 번째를 만들지 않는다.
    #
    # CLAUDE.md v3.32가 이미 "부작용이 가장 작은 방향"으로 지목한 설계를 그대로
    # 따른다 - save_ledger()가 같은 티커의 직전 ledger를 찾아 위임하는 것.
    # 모든 분석 스크립트가 이미 save_ledger()를 부르므로 **배선 누락이 구조적으로
    # 불가능**하다.
    #
    # 부작용 억제:
    #   - 절대 예외를 던지지 않는다(대조는 조언이지 차단이 아니다)
    #   - 결과를 저장 JSON에 병기만 한다(판정은 건드리지 않는다 - 병기 원칙)
    #   - cross_check=False로 끌 수 있다(골든테스트가 저장소 상태에 의존하지
    #     않아야 하는 경우 대비)
    prior_warnings = []
    prior_ref = None
    if cross_check:
        prior_path, prior = _find_prior_ledger(
            result["meta"]["ticker"], path, ledger_dir
        )
        if prior:
            prior_ref = os.path.basename(prior_path)
            try:
                prior_warnings = cross_check_prior_record(
                    result,
                    {
                        "rar": prior.get("rar"),
                        "gap": prior.get("expectation_gap"),
                        "drs": (prior.get("drs") or {}).get("score"),
                        "implied_growth": (prior.get("implied_growth") or {}).get("value"),
                    },
                )
            except Exception as e:  # 대조 실패가 저장을 막아선 안 된다
                prior_warnings = [
                    f"[과거기록 대조 실패] {type(e).__name__}: {e} "
                    f"(대조는 조언이므로 저장은 계속 진행됨)"
                ]
            if prior_warnings:
                print(f"⚠️ 과거 기록({prior_ref}) 대조 경고 {len(prior_warnings)}건:")
                for w in prior_warnings:
                    print(f"   - {w}")

    payload = dict(result)
    payload["prior_cross_check"] = {
        "prior_ledger": prior_ref,
        "warnings": prior_warnings,
        "checked": bool(cross_check),
    }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, default=str)
    return path
