"""
Market-Relative Gap 1차 실행 - 2026-08-13 (v3.45).

경위: 사용자가 제안한 "다른 차원으로 발전시킬 아이디어" 4개 중 마지막
(회사 엔진 x ETF 엔진 연결). 회사 34종목의 Gap을 VOO(시장 전체)의 Gap
대비로 다시 읽는다 - "이 종목이 싼가, 아니면 그냥 시장 전체가 싼가"에
처음으로 답한다.

⚠️ 요인분해가 아니라 벤치마크 차감이다(engine/market_relative.py 모듈
docstring 참고 - 두 엔진의 할인율 계산 경로가 완전히 독립이라 "체계적/
고유" 분해는 이 코드베이스에서 정당화되지 않는다). 분자도 다르다(회사는
FCF, VOO는 이익) - 그래서 레벨을 정밀하게 읽지 말고 방향과 대략적 순위만
볼 것.

VOO 기준선(가장 보수적 = 가장 비싼 P/E 출처, stockanalysis 27.53x):
  Implied Growth 7.0708%, Gap +0.8992%p (적정가/경계선)

실행: python3 scripts/market_relative_2026_08_13.py
"""

import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.market_relative import market_baseline, relative_to_market

REPORT_PATH = "reports/market_relative_2026-08-13.json"


def load(ticker, dirpath="ledger"):
    path = sorted(glob.glob(f"{dirpath}/{ticker}_*.json"))[-1]
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main():
    voo = load("VOO", dirpath="ledger_etf")
    baseline = market_baseline(voo)

    print("=" * 100)
    print("Market-Relative Gap - VOO(시장 전체) 대비 회사 34종목 (2026-08-13)")
    print("=" * 100)
    print(f"\nVOO 기준선({baseline['source']}): Implied Growth {baseline['implied_growth']*100:.2f}%, "
          f"Gap {baseline['gap']*100:+.2f}%p")
    print("⚠️ 요인분해 아님(벤치마크 차감), 분자 상이(FCF vs 이익) - 방향·순위만 볼 것\n")

    tickers = sorted(os.path.basename(p).split("_")[0]
                     for p in glob.glob("ledger/*.json"))
    rows = [relative_to_market(load(t), baseline) for t in tickers]
    rows.sort(key=lambda r: r["relative_gap"], reverse=True)

    head = (f"{'종목':6} {'Gap(절대)':>10} {'Gap(대VOO)':>11} {'성장프리미엄':>12}  "
            f"{'판정':14} 해석")
    print(head)
    print("-" * len(head))
    for r in rows:
        # 해석: Gap도 양수인데 Growth Premium이 크게 음수 -> "시장평균보다
        # 비관적으로 가격됐는데 그 비관이 과하다"는 조합 신호
        note = ""
        if r["gap"] > 0.05 and r["growth_premium"] < -0.05:
            note = "시장평균보다 비관적 가격 + 실제론 저평가"
        elif r["gap"] < -0.05 and r["growth_premium"] > 0.05:
            note = "시장평균보다 낙관적 가격 + 실제론 고평가"
        print(f"{r['ticker']:6} {r['gap']*100:+9.2f}%p {r['relative_gap']*100:+10.2f}%p "
              f"{r['growth_premium']*100:+11.2f}%p  {r['judgment']:14} {note}")

    os.makedirs("reports", exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump({
            "generated_at": "2026-08-13",
            "market_baseline": baseline,
            "rows": rows,
            "caveat": (
                "요인분해가 아니라 벤치마크(VOO) 차감이다. 회사 엔진과 ETF 엔진의 "
                "할인율 계산 경로가 독립이라 체계적/고유 분해는 정당화되지 않는다. "
                "분자도 다르다(회사=FCF, VOO=이익) - 레벨을 정밀하게 읽지 말 것."
            ),
        }, f, ensure_ascii=False, indent=2)
    print(f"\n리포트 저장: {REPORT_PATH}")
    return rows


if __name__ == "__main__":
    main()
