"""
전체 워크플로 실행 데모 (2026-08-15) - §12 완료 기준이 실제로 동작하는지 증명한다.

    기업 분석 -> 경제적 현실 -> 가격이 요구하는 조건 -> Expectation Gap
    -> 왜 다른가 -> Investment Thesis -> BUY/WATCH/HOLD/SELL
    -> Invalidation 조건 기록 -> 미래 예측 기록 -> (나중에) 예측 vs 실제

⚠️ **기본값은 임시 디렉터리다.** 여기 적힌 투자논거는 ledger와 CLAUDE.md에
이미 기록된 사실만으로 구성한 **동작 확인용 예시**이지 사용자의 실제 투자
판단이 아니다. 사용자가 검토하지 않은 투자논거를 저장소에 남기면 그 자체가
이 프로젝트가 금지해온 "빈칸 채우기"가 된다.

실제로 쓰려면 내용을 직접 검토·수정한 뒤 출력 디렉터리를 지정해 실행할 것:

    python3 scripts/workflow_demo_2026_08_15.py --thesis-dir thesis \\
        --prediction-dir predictions

사용 종목: BSX(Boston Scientific). 이 저장소에서 가장 최근 정식분석이고
(2026-08-13), price_at_analysis가 기록돼 있으며, screen()이 거짓 탈락시킨
사례라 신호와 결정을 분리해 볼 가치가 특히 큰 종목이다.
"""

import argparse
import glob
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.gap_analysis import analyze_gap  # noqa: E402
from engine.prediction_ledger import (  # noqa: E402
    Prediction,
    record_prediction,
    resolve_prediction,
)
from engine.thesis import (  # noqa: E402
    InvestmentThesis,
    build_decision,
    build_evidence,
    evaluate_thesis_status,
    load_thesis,
    record_decision,
    record_evidence,
    save_thesis,
)

TICKER = "BSX"


def load_ledger(ticker):
    paths = sorted(glob.glob(f"ledger/{ticker}_*.json"))
    if not paths:
        raise SystemExit(f"ledger/{ticker}_*.json 이 없다")
    with open(paths[-1], encoding="utf-8") as f:
        return os.path.basename(paths[-1]), json.load(f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--thesis-dir", default=None)
    ap.add_argument("--prediction-dir", default=None)
    args = ap.parse_args()

    tmp = tempfile.mkdtemp(prefix="irs_workflow_")
    thesis_dir = args.thesis_dir or os.path.join(tmp, "thesis")
    prediction_dir = args.prediction_dir or os.path.join(tmp, "predictions")
    persisted = bool(args.thesis_dir or args.prediction_dir)

    ledger_name, ledger = load_ledger(TICKER)

    print("=" * 78)
    print(f"IRS 전체 워크플로 데모 - {TICKER} ({ledger_name})")
    print("=" * 78)
    if not persisted:
        print(f"⚠️ 임시 디렉터리에 기록한다(저장소에 남지 않음): {tmp}")
    print()

    # ── 1~4. 경제적 현실 / 가격이 요구하는 조건 / Gap / 왜 다른가 ──────────
    signal = analyze_gap(ledger)
    lv = signal["gap_level"]

    print("[1] 기업의 경제적 현실 (재무제표에서만 나오는 값)")
    print(f"    매출 5y CAGR      : {ledger['derived']['revenue_cagr_5y']*100:6.2f}%")
    print(f"    FCF 5y CAGR       : {ledger['derived']['fcf_cagr_5y']*100:6.2f}%")
    print(f"    근거 기반 기대성장 : {lv['evidence_supported_expectation']*100:6.2f}%")
    print()
    print("[2] 현재 가격이 요구하는 조건 (분석자 주관이 개입할 수 없는 축)")
    print(f"    Valuation-Implied Requirement : {lv['valuation_implied_requirement']*100:6.2f}%")
    print(f"    저평가 판정 최소선            : {lv['undervalued_floor']*100:6.2f}%")
    print()
    print("[3] Expectation Gap")
    print(f"    Gap      : {lv['gap']*100:+6.2f}%p   판정: {lv['judgment']}")
    print(f"    신호 지위 : {lv['signal_status']}")
    print()
    print("[4] 왜 다른가 / 근거는 얼마나 강한가 / 모델 불확실성")
    ev, mu = signal["evidence_strength"], signal["model_uncertainty"]
    print(f"    외부 관측 증거     : {ev['n_observations']}건 "
          f"(최강: {ev['strongest_evidence_kind']})")
    print(f"    모델 괴리          : {(mu['model_divergence'] or 0)*100:.2f}%p "
          f"(채택: {mu['model_used']})")
    print(f"    DRS 민감도 판정flip: {mu['drs_sensitivity_flips_judgment']}")
    print(f"    성장상한 바인딩    : {lv['growth_cap_binding']}")
    print()

    # ── 5. Investment Thesis ────────────────────────────────────────────
    # 아래 내용은 전부 ledger와 CLAUDE.md에 이미 기록된 사실에서만 가져온다.
    thesis = InvestmentThesis(
        ticker=TICKER,
        thesis_date="2026-08-15",
        why_buy=(
            f"근거 기반 기대성장률({lv['evidence_supported_expectation']*100:.2f}%)이 "
            f"현재 가격이 요구하는 성장률({lv['valuation_implied_requirement']*100:.2f}%)을 "
            f"{lv['gap']*100:.2f}%p 상회한다. [예시 - 분석자 검토 필요]"
        ),
        market_assumption=(
            "시장은 리콜·소송·WATCHMAN 성장둔화 우려로 EP 성장의 지속성을 "
            "할인하고 있다(2026-08-13 스크리닝 시 확인된 하락 서사)."
        ),
        irs_view=(
            "PFA 하위세그먼트에서 Farapulse가 Medtronic 대비 74% 점유로 앞서 있어 "
            "경쟁강도 입력이 5.4(RMD와 동일 수준)로 낮게 산출됐고, 이것이 "
            "screen()의 상수 가정(12.0)과 갈려 거짓 탈락을 만든 지점이다."
        ),
        key_drivers=["EP(전기생리학) 부문 성장", "PFA 점유율 방어", "영업레버리지"],
        expected_outcomes=["FY2026 매출 성장률이 두 자릿수를 유지"],
        catalysts=["FY2026 Q3 실적", "J&J의 PFA 반격 제품 출시 여부"],
        risks=[
            "J&J가 '매우 개인적인 싸움'이라 표현할 만큼 반격 강도가 높음",
            "리콜·제조품질 이슈 재발 시 EP 성장 서사 훼손",
        ],
        invalidation_conditions=[
            {"condition": "FY2026 Q3 실적에서 EP 부문 성장률이 한 자릿수로 둔화되면 재검토",
             "check_by": "2026-11-30"},
            {"condition": "PFA 시장점유율이 Medtronic에 역전당하면 irs_view의 전제가 깨짐",
             "check_by": "2027-06-30"},
        ],
        holding_horizon="3~5년",
        linked_ledger=ledger_name,
        author_note="⚠️ 동작 확인용 예시. 실제 투자 전 분석자가 전면 검토할 것.",
    )
    path = save_thesis(thesis, thesis_dir=thesis_dir)
    print(f"[5] Investment Thesis 기록 -> {path}")
    print(f"    thesis_id: {thesis.thesis_id}")
    print()

    # ── 6. 결정 - 신호가 아니라 관문을 통과해야 한다 ────────────────────
    gates = {
        "signal_summary": (
            f"Gap {lv['gap']*100:+.2f}%p / {lv['judgment']} "
            f"(RESEARCH_HYPOTHESIS - 검증된 alpha 아님)"
        ),
        "business_quality": (
            "EP 전체시장은 J&J 54% vs BSX 9%지만 고성장 PFA 하위세그먼트에서는 "
            "Farapulse가 앞선다. 전환비용 있는 의료기기."
        ),
        "financial_quality": (
            f"FCF 5y CAGR {ledger['derived']['fcf_cagr_5y']*100:.2f}%, "
            f"Confidence {ledger['confidence']['final']}/100."
        ),
        "risk_assessment": (
            f"DRS {ledger['drs']['score']:.1f}. 강건성점검 판정flip "
            f"{ledger['sensitivity_check']['judgment_flipped']}."
        ),
        "valuation_assessment": (
            f"Implied {lv['valuation_implied_requirement']*100:.2f}% vs "
            f"현실적 {lv['evidence_supported_expectation']*100:.2f}%. "
            f"저평가 문턱까지 여유 {lv['headroom_vs_undervalued_floor']*100:+.2f}%p."
        ),
        "portfolio_context": (
            "기존 매수리스트(2026-08-04)에 미편입. 의료기기 익스포저는 "
            "RMD·IDXX·ZTS와 일부 중첩되나 EP는 별개 축."
        ),
    }
    decision = build_decision(
        thesis_id=thesis.thesis_id,
        decision_date="2026-08-15",
        action="WATCH",   # ⚠️ 엔진이 고른 값이 아니라 분석자가 고른 값
        gates=gates,
        rationale=(
            "Gap이 판정밴드를 갓 넘긴 수준(+5.87%p)이고 외부 관측 증거가 0건이라 "
            "자본을 넣기 전에 Q3 실적으로 EP 성장 지속성을 먼저 확인한다. "
            "[예시 - 분석자 검토 필요]"
        ),
    )
    record_decision(path, decision)
    print(f"[6] 결정 기록: {decision['action']} ({decision['action_source']})")
    print(f"    관문 {len(decision['gates'])}개 전부 근거 기록됨")
    print()

    # ── 7. 미래 예측 사전등록 ───────────────────────────────────────────
    pred = Prediction(
        thesis_id=thesis.thesis_id,
        ticker=TICKER,
        prediction_date="2026-08-15",
        horizon="FY2026 Q3 실적 발표(2026-11 예상)",
        metric="EP 부문 매출 YoY 성장률",
        expected_low=0.10,
        expected_high=0.20,
        assumption="Farapulse PFA 점유율이 현 수준에서 크게 훼손되지 않는다",
        source=f"{ledger_name}의 realistic_growth "
               f"{lv['evidence_supported_expectation']*100:.2f}%와 EP 부문 프리미엄 반영",
    )
    ppath = record_prediction(pred, prediction_dir=prediction_dir)
    print(f"[7] 예측 사전등록 -> {ppath}")
    print(f"    {pred.metric}: {pred.expected_low*100:.0f}~{pred.expected_high*100:.0f}% "
          f"({pred.horizon})")
    print(f"    코어 해시: {pred.core_hash()[:16]}... (봉인됨)")
    print()

    # ── 8. 시간이 지난 뒤 - 증거 반영과 예측 채점 ────────────────────────
    print("[8] (가상 시나리오) 실적 발표 후 - 증거 반영 및 예측 채점")
    record_evidence(path, build_evidence(
        observed_date="2026-11-20",
        summary="EP 부문 매출 +8% YoY - 예측 하단(10%)에 미달",
        direction="contradicts",
        source="회사 FY2026 Q3 실적발표",
        metric="EP 부문 매출 YoY 성장률",
        value=0.08,
    ))
    resolved = resolve_prediction(ppath, actual_value=0.08, actual_date="2026-11-20",
                                  note="가상 시나리오 - 실제 실적 아님")
    status = evaluate_thesis_status(load_thesis(TICKER, "2026-08-15",
                                                thesis_dir=thesis_dir))

    print(f"    예측 채점 : {resolved['status']} "
          f"(오차 {resolved['forecast_error']:+.4f} - 부호가 있어 편향 추적 가능)")
    print(f"    thesis 상태: {status['status']} "
          f"(지지 {status['n_supports']} / 반대 {status['n_contradicts']})")
    print()
    print("=" * 78)
    print("§12 완료 기준 충족: 분석 -> Gap -> Thesis -> 결정 -> 반증조건 -> 예측 -> 실제 비교")
    print("=" * 78)
    if not persisted:
        print(f"\n※ 저장소에는 아무것도 기록되지 않았다(임시: {tmp}).")
        print("   실제로 쓰려면 내용을 검토·수정한 뒤 --thesis-dir/--prediction-dir 지정.")


if __name__ == "__main__":
    main()
