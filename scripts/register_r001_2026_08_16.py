"""
R-001 사전등록 (2026-08-16, STAGE 3): 투자판정 강건성 감사의 가정공간.

⚠️ **결과를 보기 전에 등록한다**(§8). 등록 후 범위를 바꾸려면 새 실험 ID가 필요하다.

## 왜 새 실험 ID인가 (§2 불일치 해결)

`engine/gap_analysis.ASSUMPTION_GRID`는 n ∈ {10,12,14}만 보는데 엔진 자신은
`capped_n(8~15)`을 허용한다 — §24가 열거한 False Robustness 1번("Grid가 실제
허용범위보다 좁음")에 정확히 해당한다. 그러나 그 상수는 **H-005가 `robust` 정의로
사전등록**했으므로 수정하면 사후조정이 된다(결정 #16 REJECTED).

결정 #16이 남긴 재개조건은 "새 실험 ID로 재등록하는 경우에 한해"였다. R-001이
그 조건을 충족한다: **H-005의 격자는 그대로 두고**, Stage 3는 자신의 가정공간을
독립적으로 사전등록한다. 두 실험은 서로 다른 질문에 답하므로 공존한다.

## §9 근거수준

LEVEL 1 기업 고유 직접 데이터 / LEVEL 2 기업 과거 데이터 / LEVEL 3 산업 데이터
LEVEL 4 외부 연구 / LEVEL 5 분석자 판단 / LEVEL 6 근거 없음
→ **LEVEL 6은 핵심 결론의 근거로 쓰지 않는다.**
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.experiment_registry import Experiment, register_experiment  # noqa: E402

# ── §8 가정범위 사전정의 (결과를 보기 전에 고정) ──────────────────────────
ASSUMPTION_SPACE = {
    "growth_duration_n": {
        "low": 8, "base": "ledger n (전 종목 12)", "high": 15,
        "evidence_level": "LEVEL 5",
        "economic_basis": (
            "엔진 자신의 capped_n(n_min=8, n_max=15)이 허용하는 전 범위. "
            "임의로 고른 폭이 아니라 **코드가 이미 정당하다고 선언한 공간**이라는 "
            "점이 근거다. 값 8·15 자체의 경제적 근거는 없다(LEVEL 5)."
        ),
        "pit_availability": "가능 - 계산 파라미터이며 데이터가 아니다",
        "range_quality": "엔진 허용범위와 정확히 일치(과대·과소 아님)",
        "applies_to": "two_stage only (single_stage는 n을 쓰지 않음)",
    },
    "required_return_r": {
        "low": "base − 0.01", "base": "ledger r", "high": "base + 0.01",
        "evidence_level": "LEVEL 5",
        "economic_basis": (
            "r = rf + erp(DRS)이며 erp는 0.05~0.08로 사상된다. DRS 전 범위를 흔들어도 "
            "erp는 3%p만 움직이므로 ±1%p는 그 절반 수준의 보수적 폭이다. "
            "H-005가 쓴 폭과 동일하게 두어 두 실험을 비교 가능하게 유지한다."
        ),
        "pit_availability": "가능", "range_quality": "보수적(실제 DRS 변동폭보다 좁음)",
    },
    "terminal_growth": {
        "low": "base − 0.01", "base": "ledger g_terminal", "high": "base + 0.01",
        "evidence_level": "LEVEL 4",
        "economic_basis": (
            "`default_terminal_growth(rf)`가 floor 2.0% · ceiling 4.5%로 클리핑하며 "
            "무위험금리에 연동된다. ±1%p는 그 밴드(2.5%p 폭) 안쪽이다."
        ),
        "pit_availability": "가능", "range_quality": "엔진 자체 밴드 내부",
        "applies_to": "two_stage only",
    },
    "model_choice": {
        "low": "single_stage", "base": "ledger model_used", "high": "two_stage",
        "evidence_level": "LEVEL 5",
        "economic_basis": (
            "이산 선택이며 연속 범위가 아니다. 2026-08-16 모델선택 연구가 "
            "**관측 가능한 성장프로파일로 실제 선택을 분리할 수 없음**을 실증했으므로"
            "(구간 거의 완전 중첩, 동일 관측치 반대선택 3쌍) 두 모델을 모두 "
            "VALID로 취급한다. 이건 파라미터가 아니라 model uncertainty다(§16)."
        ),
        "pit_availability": "가능", "range_quality": "이산 2점 전수",
    },
    "realistic_growth": {
        "low": "min(3y/5y/10y 매출 CAGR)", "base": "ledger realistic_growth",
        "high": "max(3y/5y/10y 매출 CAGR)",
        "evidence_level": "LEVEL 2",
        "economic_basis": (
            "**기업 자신의 과거 데이터**에서 나온 범위이며 분석자가 고른 폭이 아니다. "
            "2026-08-16 동결한 34종목 예측(predictions/)이 쓴 범위와 **동일 정의**라 "
            "Stage 5에서 예측오차와 직접 연결된다."
        ),
        "pit_availability": "가능 - ledger derived에 이미 저장됨",
        "range_quality": (
            "⚠️ 상한 캡이 바인딩된 종목(RG가 원시계산이 아니라 캡 그 자체)에서는 "
            "base가 이 범위 밖일 수 있다. 그 경우 base를 범위에 강제 포함시키고 "
            "cap_bound 플래그를 남긴다 - 범위를 조작하지 않는다."
        ),
    },
    "fcf0": {
        "low": "SBC 차감 FCF(sbc_cross_check 보유 종목만)", "base": "ledger fcf0",
        "high": "base (상향 조정 근거 없음)",
        "evidence_level": "LEVEL 1",
        "economic_basis": (
            "SBC 차감치는 v3.23이 이미 SEC 원자료로 계산해 둔 **기업 고유 직접 "
            "데이터**다. 상향 방향은 근거가 없으므로 만들지 않는다 - 없는 범위를 "
            "지어내지 않는다(§8)."
        ),
        "pit_availability": "가능",
        "range_quality": "비대칭(하방만). 8/34 종목만 적용 가능 → 나머지는 NOT_APPLICABLE",
    },
}

# ── §11 시나리오 제약 (VALID 판정 규칙) ──────────────────────────────────
SCENARIO_CONSTRAINTS = {
    "mathematical": [
        "r > terminal_growth (Gordon·2단계 모두 발산 방지)",
        "fcf0 > 0",
        "market_cap > 0",
    ],
    "accounting": [
        "FCF 정의 고정: OCF − capex (시나리오마다 정의를 바꾸지 않는다)",
        "SBC 차감은 fcf0 축에서만 1회 - 다른 축과 이중차감 금지(§20)",
    ],
    "economic": [
        "realistic_growth 범위는 기업 자신의 과거 CAGR 범위 안 - 외삽 금지",
        "n은 엔진 허용범위(8~15) 안 - 임의 확장 금지",
        "single_stage 시나리오에서는 n·terminal_growth를 흔들지 않는다"
        "(모델이 그 값을 쓰지 않으므로 흔들면 가짜 시나리오가 생긴다, §25)",
    ],
}


exp = Experiment(
    experiment_id="R-001",
    hypothesis=(
        "**이것은 수익률 가설이 아니라 감사 프로토콜의 사전등록이다.** "
        "질문: 34종목 각각의 투자판정이 사전에 정의된 경제적으로 타당한 가정공간 "
        "안에서 유지되는가? 유지되지 않는다면 어느 가정이, 어느 경계를, 어느 방향으로 "
        "넘게 만드는가? **판정이 안정적일 것이라고도 취약할 것이라고도 가정하지 "
        "않는다** - 강건한 것은 강건하다고, 취약한 것은 취약하다고 기록하는 것이 목적이다."
    ),
    universe=(
        "ledger/ 34종목 전부. 표본 선택 없음(§27: 이 34종목은 EXPLORATORY SAMPLE이며 "
        "여기서 threshold·range·cutoff를 최적화하지 않는다)."
    ),
    entry_rule=(
        "위 ASSUMPTION_SPACE의 Low/Base/High를 사전 고정해 시나리오를 생성하고, "
        "SCENARIO_CONSTRAINTS로 VALID/INVALID/INFEASIBLE/NOT_APPLICABLE을 분류한다. "
        "**VALID만 decision stability 계산에 포함**한다(§10). 기존 Base Case는 "
        "변경하지 않으며 robustness는 감사 계층으로만 계산한다(§33)."
    ),
    exit_rule=(
        "감사는 1회 실행으로 종료한다. 결과를 본 뒤 범위·격자·robustness 정의를 "
        "바꾸지 않는다(§34). 변경이 필요하면 R-002로 새로 등록한다."
    ),
    test_period="해당 없음 - 시점 실험이 아니라 현재 Base Case의 가정 의존성 감사",
    oos_period=(
        "해당 없음. 단 이 감사의 산출물(가정정의·범위·근거·PIT상태·시나리오규칙·"
        "모델버전)은 Stage 4 Historical Replay에서 과거 시점 재현이 가능하도록 저장한다(§31)."
    ),
    benchmark=(
        "귀무기준 없음(가설검정이 아님). 비교 기준은 각 종목의 **동결된 Base Case** "
        "(reports/baseline_frozen_2026-08-16.json, fingerprint fbd34322…)이다."
    ),
    analysis_as_of="2026-08-16",
    data_version="ledger/ 34종목 + baseline_frozen_2026-08-16.json",
    methodology_version="v3.53",
    transaction_cost_assumption=(
        "해당 없음 - 매매를 수반하지 않는 감사이며 수익률을 주장하지 않는다."
    ),
    parameters={
        "assumption_space": ASSUMPTION_SPACE,
        "scenario_constraints": SCENARIO_CONSTRAINTS,
        "relationship_to_H005": (
            "H-005가 사전등록한 ASSUMPTION_GRID(n∈{10,12,14})는 **수정하지 않는다**. "
            "R-001은 엔진 허용범위 전체(n∈{8..15})를 쓰는 독립 가정공간이며, "
            "두 실험은 서로 다른 질문에 답한다. 결정 #16의 재개조건 충족."
        ),
        "stability_is_not_probability": (
            "Judgment Stability는 '유효 가정공간 중 같은 판정이 나온 비율'이며 "
            "**확률이 아니다**(§15). 보정된 적이 없다."
        ),
        "multiple_testing_note": (
            "가정 6축 × 다중 시나리오를 검사하므로 우연한 단일 flip이 발생할 수 있다"
            "(§26). 단일 flip을 핵심 발견으로 과장하지 않으며, 시나리오 수를 결과에 기록한다."
        ),
    },
    depends_on=[],
    registered_date="2026-08-16",
    note=(
        "STAGE 3 투자판정 강건성 감사. ⚠️ §2 검증에서 Stage 2(Growth Duration)가 "
        "실행된 적 없음을 확인했다 - n은 34종목 전부 12로 균일하며 경제적 차등화 "
        "근거가 없는 상태다. R-001은 그 사실을 **전제로** n의 판정영향을 측정하며, "
        "n을 차등화하는 것은 이 실험의 범위가 아니다(Stage 2의 몫)."
    ),
)

if __name__ == "__main__":
    print(f"등록 완료: {register_experiment(exp, status='REGISTERED')}")
