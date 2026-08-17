"""
H-007 사전등록 (2026-08-16, STAGE 1): 성장의 경제성이 성장 예측오차와 관계있는가.

⚠️ **결과가 존재하기 전에 등록한다.** 2026-08-16 기준 34종목 예측은 전부 OPEN이고
실현 성장률 관측치는 0건이다. 이 실험은 STAGE 1에서 새로 계산 가능해진 두 축
(영업이익률 수준 / capex-매출비율 수준)이 **실제로 무언가를 설명하는지** 검정한다.

검정 전까지 두 축은 어떤 공식 판정·Gap·비중에도 관여하지 않는다.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.experiment_registry import Experiment, register_experiment  # noqa: E402

exp = Experiment(
    experiment_id="H-007",
    hypothesis=(
        "STAGE 1에서 도입한 성장의 경제성 두 축(영업이익률 수준, capex/매출 수준)이 "
        "**Realistic Growth의 예측오차와 관계가 있는가?** 구체적으로: 종목을 "
        "영업이익률 관측중앙값 기준 고/저 두 집단으로 나눴을 때, (RealisticGrowth − "
        "실현 매출성장률)의 분포가 두 집단 간에 다른가? **방향은 가정하지 않는다** — "
        "저마진 기업의 성장이 덜 지속된다는 것이 통상적 직관이나, 반대로 저마진 "
        "기업이 마진 회복 여지가 커 성장이 더 오래갈 가능성도 열어둔다. capex/매출 "
        "축도 동일하게 검정한다(두 축은 실측 순위상관 0.047로 거의 독립이라 별도로 본다)."
    ),
    universe=(
        "2026-08-16 predictions/에 동결된 34종목. 생존편향 통제: 동결 시점 34건을 "
        "모두 포함하며 이후 실적이 안 나오는 종목은 제외하지 않고 UNRESOLVABLE로 기록."
    ),
    entry_rule=(
        "각 종목의 영업이익률 수준·capex/매출 수준을 **2026-08-16 시점 ledger 입력값으로 "
        "고정**한다(reports/growth_quality_profile_2026-08-16.json). 이후 갱신하지 않는다 — "
        "결과를 본 뒤 축 값을 다시 계산하면 검정이 무의미해진다. 집단 경계는 등록 시점 "
        "관측중앙값(영업이익률 21.0063%, capex/매출 1.6454%)으로 **코드가 아닌 이 문서에 고정**한다."
    ),
    exit_rule=(
        "H-006과 동일하게 해소 가능한 예측이 최소 15건 확보되면 검정한다. 15건 미만이면 "
        "INCONCLUSIVE로 닫는다. 중간에 들여다보고 경계나 표본기준을 조정하지 않는다."
    ),
    test_period="2026-08-16 동결분의 다음 회계연도 실적 공시 시점(종목별 상이)",
    oos_period=(
        "이 가설을 만든 데이터는 예측오차가 아니라 **횡단면 상관구조**(축 간 독립성, "
        "기존 변수와의 중복도)뿐이다. 예측오차는 아직 한 건도 관측되지 않았으므로 "
        "검정 표본 전체가 out-of-sample이다."
    ),
    benchmark=(
        "귀무가설: 두 집단의 예측오차 분포가 같다. Mann-Whitney U(비모수, 소표본). "
        "부가로 H-006의 전체 부호검정 결과와 대조해 '과대추정이 특정 집단에 "
        "몰려 있는가'를 본다."
    ),
    analysis_as_of="2026-08-16",
    data_version=(
        "ledger/ 34종목 + reports/growth_quality_profile_2026-08-16.json(축 값 동결) "
        "+ predictions/ 34건(2026-08-16 동결)"
    ),
    methodology_version="v3.53",
    transaction_cost_assumption=(
        "해당 없음 - 예측정확도 검정이며 매매를 수반하지 않는다. 수익률을 주장하지 않으므로 "
        "비용 가정이 결과에 개입하지 않는다."
    ),
    parameters={
        "axis_1": "operating_margin_level (영업이익률 수준, 최근연도)",
        "axis_2": "capex_to_revenue_level (capex/매출 수준, 최근연도)",
        "axis_correlation_at_registration": 0.047,
        "group_split": "등록 시점 관측중앙값",
        "operating_margin_median_at_registration": 0.210063,
        "capex_to_revenue_median_at_registration": 0.016454,
        "test": "Mann-Whitney U (양측)",
        "min_sample_for_test": 15,
        "depends_on_note": "H-006이 산출하는 예측오차를 입력으로 쓴다",
        "median_source": "reports/growth_quality_profile_2026-08-16.json (동결)",
        "explicitly_not_prespecified": (
            "방향(어느 집단이 더 과대추정되는가). 예상을 적으면 그 예상에 맞는 "
            "검정만 하게 된다."
        ),
        "measured_overlap_with_existing_irs": {
            "operating_margin_level_vs_margin_volatility": -0.069,
            "operating_margin_level_vs_realistic_growth": -0.323,
            "operating_margin_level_vs_gap": -0.190,
            "operating_margin_level_vs_drs": -0.043,
        },
    },
    depends_on=["H-006"],
    registered_date="2026-08-16",
    note=(
        "STAGE 1 Growth Quality prototype에서 파생. ⚠️ 최초 등록(2026-08-16)에서 집단경계 중앙값을 0.2035/0.0159로 잘못 적어 즉시 삭제 후 실측값(0.210063/0.016454)으로 재등록했다 - 결과 관측 0건 시점의 정정이므로 사후조정이 아니다. 이 실험이 귀무를 기각하지 못하면 "
        "**두 축은 기록으로만 남기고 어떤 판정 경로에도 넣지 않는다** - 그것도 유용한 "
        "결론이다(REJECT도 성공적인 연구 결과다). 기각하더라도 그 즉시 Realistic Growth나 "
        "Growth Duration에 배선하지 않는다 - 배선 방식(A/B/C/D 구조)은 별도 결정이다."
    ),
)

if __name__ == "__main__":
    print(f"등록 완료: {register_experiment(exp, status='REGISTERED')}")
