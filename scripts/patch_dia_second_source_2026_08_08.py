"""
DIA 2차 P/E 출처 추가 - 2026-08-08 (v3.41 후반, 단일출처 해소 마무리).

경위: "그대로 순서대로 실행해" 워크플로 3단계(단일 P/E 출처 종목 2차 출처
보강). DIA는 `scripts/analyze_etfs_2026_08_06.py`의 8종목 배치에 속해있는데,
그 스크립트를 통째로 재실행하면 이미 2개 이상 출처를 가진 나머지 7종목까지
불필요하게 오늘 날짜로 재저장된다(v3.32/v3.35/v3.36과 같은 계열의 낭비) -
DIA만 분리해서 재실행한다. 입력값은 `analyze_etfs_2026_08_06.py`의 DIA
항목과 완전히 동일하며 `pe_by_source`에 2차 출처(worldperatio.com, 트레일링
25.49x, 2026-08-08 기준일 확인)만 추가했다.

실행: python3 scripts/patch_dia_second_source_2026_08_08.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.etf_pipeline import ETFInputs, run_etf_analysis, save_etf_ledger

RF = 0.0461

COMMON_SOURCES = [
    "stockanalysis.com/etf/{ticker} (트레일링 P/E·배당수익률·1년수익률, 2026-08-06 조회)",
    "totalrealreturns.com (YTD·1년 총수익률, 2026-08-05 기준)",
    "tradingeconomics / FRED DGS10 (미국10Y 4.61%, 2026-08-05/06)",
    "worldperatio.com/index/dow-jones (2차 트레일링 P/E, 2026-08-08 기준일 확인)",
]

DIA_INPUTS = ETFInputs(
    ticker="DIA", name="SPDR Dow Jones Industrial Average ETF",
    tracks="Dow Jones Industrial Avg",
    pe_by_source={"stockanalysis(trailing)": 25.57, "worldperatio(trailing)": 25.49},
    expense_ratio=0.0016, n_holdings=31, top10_weight=0.52,
    risk_free_rate=RF,
    expected_earnings_growth=0.07,
    expected_earnings_growth_basis=(
        "다우30은 성숙 대형 우량주 중심이라 S&P500(8%)보다 소폭 낮은 장기 "
        "이익성장률을 가정 [추정치]. 가격가중 지수라 시총가중 지수와 성격이 "
        "달라 S&P500 실적 앵커를 그대로 쓸 수 없다는 점도 감안."
    ),
    dividend_yield=0.0133, return_1y=0.2384, return_ytd=0.1383,
    top10_holdings={
        "GS": 0.1166, "CAT": 0.0920, "MSFT": 0.0513, "UNH": 0.0479,
        "AMGN": 0.0441, "TRV": 0.0428, "V": 0.0417, "JPM": 0.0399,
        "SHW": 0.0392, "AXP": 0.0384,
    },
    data_sources=COMMON_SOURCES,
)


def main():
    result = run_etf_analysis(DIA_INPUTS)
    for src, s in result["valuation"]["by_source"].items():
        print(f"  - {src:24} P/E {s['pe_ratio']:6.2f}x -> Gap {s['gap']*100:+.2f}%p  {s['judgment']}")
    for x in result["data_limitations"]:
        print(f"    ⚠️ {x}")
    path = save_etf_ledger(result)
    print(f"ledger 저장: {path}")


if __name__ == "__main__":
    main()
