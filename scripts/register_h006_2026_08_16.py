"""
H-006 사전등록 (2026-08-16): Realistic Growth의 체계적 과대추정 가설.

⚠️ **결과가 존재하기 전에 등록한다.** 2026-08-16 기준 34종목 예측은 전부
status=OPEN이며 실현 매출성장률 관측치는 0건이다. 동기가 된 n=10 관측은
전부 **표본내**이고, 그중 최적 축소계수(w≈0.25~0.45)는 5개 점에 1-파라미터를
적합한 값이라 **과적합이다** - 그 수치를 대체 파라미터로 쓰지 않는다.
이 실험은 방향 가설만 사전 고정하고, 검정은 향후 해소되는 예측으로만 한다.

H-001~H-005와 달리 **주가 데이터가 필요 없다**(실현 매출성장률만 필요)는 점이
중요하다 - 그래서 BLOCKED가 아니라 REGISTERED로 등록한다.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.experiment_registry import Experiment, register_experiment  # noqa: E402

exp = Experiment(
    experiment_id="H-006",
    hypothesis=(
        "IRS의 Realistic Growth는 실현 매출성장률을 **체계적으로 과대추정하는가?** "
        "구체적으로: 부호검정에서 (RealisticGrowth - 실현성장률) > 0 인 비율이 "
        "귀무가설 50%와 유의하게 다른가? 배경 메커니즘 가설은 '축소 부족'이다 - "
        "realistic_growth_estimate()는 원시 CAGR 가중평균을 구조적할인율과 Lynch "
        "상한으로 축소하는데, 2026-08-16 실측상 함의된 축소계수 w(=(RG-g_term)/"
        "(raw-g_term))의 중앙값이 0.807로 원시값의 19%만 당긴다. Chan/Karceski/"
        "Lakonishok(JF 2003)의 '장기 이익성장은 우연 이상 지속되지 않는다'가 맞다면 "
        "최적 축소는 이보다 공격적이어야 한다. **다만 얼마나 공격적이어야 하는지는 "
        "가설에 포함하지 않는다** - 그 값을 지금 정하면 표본내 적합이 된다."
    ),
    universe=(
        "2026-08-16에 predictions/에 동결된 34종목 전부. 생존편향 통제: 동결 시점 "
        "34건을 모두 포함하며, 이후 상장폐지·피인수로 실적이 안 나오는 종목은 "
        "제외하지 않고 UNRESOLVABLE로 명시 기록한다(§13)."
    ),
    entry_rule=(
        "각 종목의 다음 공식 회계연도 매출 YoY 성장률이 공시되면 해소한다. "
        "비교 대상은 해당 종목 ledger의 growth.realistic_growth(동결 시점 값, "
        "재계산 금지). 부호 = sign(realistic_growth - 실현성장률)."
    ),
    exit_rule=(
        "해소 가능한 예측이 최소 15건 확보되면 1차 검정을 수행하고 종료한다. "
        "15건 미만이면 INCONCLUSIVE로 닫고 표본을 더 기다린다 - 중간에 들여다보고 "
        "임계값을 조정하지 않는다."
    ),
    test_period="2026-08-16 동결분의 다음 회계연도 실적 공시 시점(종목별 상이)",
    oos_period=(
        "동기가 된 n=10 관측(growth_scorecard 2026-08-13)은 이 실험의 표본에서 "
        "**완전히 제외**한다 - 그 10건이 가설을 만든 데이터이므로 같은 데이터로 "
        "검정하면 순환이다. 34건 동결분만 검정에 쓴다."
    ),
    benchmark=(
        "귀무가설: 과대추정 비율 50%(부호가 무작위). 부가 비교로 원시 CAGR "
        "가중평균(base_growth_before_fcf_check)과 터미널성장률 고정값의 절대오차를 "
        "같은 표본에서 함께 보고한다 - IRS가 순진한 베이스라인을 이기는지 별도 확인."
    ),
    analysis_as_of="2026-08-16",
    data_version="predictions/ 34건 동결분(2026-08-16) + ledger/ 34종목",
    methodology_version="v3.52",
    transaction_cost_assumption=(
        "해당 없음 - 이 실험은 매매를 수반하지 않는 예측정확도 검정이다. "
        "수익률 주장을 하지 않으므로 비용 가정이 결과에 개입하지 않는다."
    ),
    parameters={
        "signal": "growth.realistic_growth vs 실현 매출 YoY 성장률",
        "test": "이항 부호검정(양측)",
        "null_proportion": 0.5,
        "min_sample_for_test": 15,
        "implied_shrinkage_w_median_at_registration": 0.807,
        "implied_shrinkage_w_mean_at_registration": 0.741,
        "implied_shrinkage_w_range_at_registration": [0.19, 1.12],
        "in_sample_motivating_evidence": {
            "n": 10,
            "over_estimation_count": 8,
            "note": "표본내. 이 10건은 검정 표본에서 제외한다.",
        },
        "explicitly_not_prespecified": (
            "대체 축소계수 w. 표본내 최적값(realized_quarterly 0.45 / "
            "guidance_annual 0.25)은 n=5에 적합한 과적합값이라 사전등록하지 않는다."
        ),
    },
    depends_on=[],
    registered_date="2026-08-16",
    note=(
        "2026-08-16 성장추정 D3 연구에서 파생. 이 실험이 확인하는 것은 IRS 성장추정의 "
        "**방향 편향**뿐이며, 그것이 투자 성과와 관계가 있는지는 별개 질문이다"
        "(그건 H-001 계열이 다룬다). 결과가 귀무를 기각하지 못해도 그 자체가 유용한 "
        "결론이다 - 현행 축소 수준이 정당하다는 뜻이 되므로."
    ),
)

if __name__ == "__main__":
    path = register_experiment(exp, status="REGISTERED")
    print(f"등록 완료: {path}")
