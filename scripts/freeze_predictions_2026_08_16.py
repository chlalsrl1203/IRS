"""
34종목 예측 봉인 (2026-08-16) — Historical Replay 감사의 #1 우선순위 개선.

## 근본원인

`engine/prediction_ledger.py`(v3.48)는 완성돼 있고 435개 테스트 중 상당수가
그 무결성(결과를 알고 난 뒤 수정 불가)을 검증한다. 그런데 `predictions/`
디렉터리는 파일시스템에 **존재하지도 않는다** — 실제 종목에 단 한 번도
적용된 적이 없다(2026-08-16 Historical Replay 감사 Phase 1 확인).

이게 왜 문제인가: 이 프로젝트가 "IRS가 실제로 투자판단을 개선하는가"를
검증하려면 **미래 결과와 대조할 사전동결된 예측**이 있어야 하는데, 지금
없으면 3개월 뒤에도, 1년 뒤에도 여전히 없다. 인프라가 있어도 안 쓰면
검증은 영원히 시작되지 않는다.

## 이 스크립트가 하지 않는 것 - 새로운 판단을 발명하지 않는다

각 예측의 `expected_range`는 **엔진이 Realistic Growth를 계산하며 이미
산출해둔 원시 CAGR 구성요소**(`growth.breakdown.revenue_cagr_inputs`의
3y/5y/10y, 존재하는 것만)의 최소~최대다. 새 가중치·새 밴드폭을 지어내지
않았다 — 이미 저장된 숫자를 그대로 재사용한다(이 감사의
`ablation_analysis.md`가 확인한 값과 동일 출처).

## thesis_id를 정직하게 남긴다

34종목 중 실제 Investment Thesis(6관문 결정)가 기록된 종목은 **0건**이다.
`thesis_id="NO_THESIS_SIGNAL_ONLY"`로 이 사실을 그대로 남긴다 - 있지도 않은
thesis를 지어내 연결하지 않는다.

## prediction_date는 오늘이다 - 원분석일이 아니다

예측이 실제로 "동결"된 시점은 이 스크립트를 실행하는 지금(2026-08-16)이다.
원분석일(2026-07-25~08-13)로 backdate하면 "그때 이미 예측을 걸어뒀다"는
거짓 인상을 준다 - `source` 필드에 원분석일과 데이터 출처를 남기되,
`prediction_date`는 진짜 동결 시점을 쓴다(계약서 §4/§6의 period≠availability
원칙을 예측 동결에도 동일 적용).
"""

import glob
import json
import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.prediction_ledger import Prediction, record_prediction  # noqa: E402

FREEZE_DATE = "2026-08-16"


def main():
    n_ok, n_skip = 0, 0
    for path in sorted(glob.glob("ledger/*.json")):
        led = json.load(open(path, encoding="utf-8"))
        ticker = led["meta"]["ticker"]
        analyzed_at = led["meta"]["analyzed_at"][:10]
        ci = led["growth"]["breakdown"]["revenue_cagr_inputs"]
        vals = [v for v in ci.values() if v is not None]

        if len(vals) < 2:
            print(f"  {ticker:6s} 건너뜀 - CAGR 구성요소 {len(vals)}개뿐(범위 무의미)")
            n_skip += 1
            continue

        pred = Prediction(
            thesis_id="NO_THESIS_SIGNAL_ONLY",
            ticker=ticker,
            prediction_date=FREEZE_DATE,
            horizon=f"다음 공식 회계연도 실적 발표(원분석 {analyzed_at} 기준)",
            metric="매출 YoY 성장률(연간)",
            expected_low=round(min(vals), 6),
            expected_high=round(max(vals), 6),
            assumption=(
                f"realistic_growth_estimate()가 이미 계산한 3y/5y/10y 매출 CAGR "
                f"구성요소({ {k: (round(v,4) if v is not None else None) for k,v in ci.items()} })의 "
                f"최소~최대 범위가 다음 회계연도에도 유지된다는 가정. 새 밴드폭을 "
                f"발명하지 않고 엔진이 이미 산출한 값만 재사용했다."
            ),
            source=(
                f"{os.path.basename(path)} (engine_version="
                f"{led['meta'].get('engine_version')}, 원분석일={analyzed_at})"
            ),
        )
        record_prediction(pred)
        n_ok += 1

    print()
    print(f"동결 완료 {n_ok}건, 건너뜀 {n_skip}건 (총 {n_ok + n_skip}종목)")


if __name__ == "__main__":
    main()
