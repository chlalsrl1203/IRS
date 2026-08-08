"""
미국 Select Sector SPDR 추가 1종 분석 - 2026-08-08 (XLY, 임의소비재/경기소비재).

경위: "계속해서 섹터 확장" 요청에 따른 v3.39 후속. 이번 조사에서 확인한 것:
  - KODEX 미국S&P500경기소비재(453660)가 "S&P Consumer Discretionary Select
    Sector Index(Price Return)"를 추종한다는 걸 확인해 XLY 원본을 새로 분석한다.
  - **소재(Materials/XLB)는 KODEX/TIGER/ACE 어디서도 국내 상장 상품을 찾지
    못했다** - 추측하지 않고 정직한 공백으로 남긴다(GICS 11섹터 중 유일하게
    국내 래퍼가 없는 섹터).
  - **부동산(리츠/XLRE)은 국내에 KODEX 미국부동산리츠(H)(352560)가 있지만
    기초지수가 "Dow Jones US Real Estate Index"로, XLRE의 "Real Estate
    Select Sector Index"와 명백히 다른 지수 계열이다**(공식 확인, samsungfund
    안내문에 "Real Estate Select Sector와는 다른 지수"라고 명시돼 있음) -
    이 프로젝트의 재사용 전제(같은 지수)가 성립하지 않아 이번 배치에서 제외한다.
    XLRE 자체를 새로 분석해도 국내에 짝지을 지수가 없으므로 당장은 의미가 없다.
  - **테크놀로지(463680)는 v3.39부터 총보수 미확인으로 계속 제외 중** - 이번에도
    재시도했으나 확인 못함.

원자료: stockanalysis.com/etf/xly (2026-08-08 조회).

실행: python3 scripts/analyze_etfs_sectors_2026_08_08.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.etf_pipeline import ETFInputs, run_etf_analysis, save_etf_ledger

RF = 0.0461  # 미국 10Y, 기존 배치와 동일 시점 유지(2026-08 초 수준에서 변동 미미)

CANDIDATES = [
    ETFInputs(
        ticker="XLY", name="Consumer Discretionary Select Sector SPDR Fund",
        tracks="임의소비재(경기소비재) 섹터",
        pe_by_source={"stockanalysis(trailing)": 28.17},
        expense_ratio=0.0008, n_holdings=50, top10_weight=0.675,
        risk_free_rate=RF,
        expected_earnings_growth=0.10,
        expected_earnings_growth_basis=(
            "상위비중이 Amazon(23.18%)·Tesla(15.66%)로 상위 2종목이 39%에 육박해 "
            "사실상 이 두 회사의 성장률이 섹터 성장률을 좌우한다 - 둘 다 고성장 "
            "서사를 가진 종목이라 전통 소매업 중심 섹터보다 높게 잡되, 경기민감 "
            "소비재 특성(Home Depot 등 주택경기 연동)상 나스닥100(11%)보다는 "
            "낮춘다 [추정치]. 상위 2종목 리스크가 이례적으로 커 집중도 위험을 "
            "감안해서 볼 것."
        ),
        dividend_yield=0.0075, return_1y=0.0811,
        data_sources=["stockanalysis.com/etf/xly (2026-08-08 조회)"],
    ),
]


def main():
    for inputs in CANDIDATES:
        result = run_etf_analysis(inputs)
        m = result["meta"]
        print(f"\n[{m['ticker']}] {m['name']} - {m['tracks']}")
        print(f"  ERS(위험점수) {result['ers']['score']:.1f} -> "
              f"요구수익률 r {result['discount_rate']['r']*100:.2f}%")
        print(f"  가정한 장기 이익성장률: {result['growth']['expected_earnings_growth']*100:.2f}%")
        for src, s in result["valuation"]["by_source"].items():
            print(f"    - {src:28} P/E {s['pe_ratio']:6.2f}x -> "
                  f"내재성장 {s['implied_growth']*100:6.2f}% -> "
                  f"Gap {s['gap']*100:+6.2f}%p  {s['judgment']}")
        for x in result["data_limitations"]:
            print(f"    ⚠️ {x}")
        path = save_etf_ledger(result)
        print(f"  ledger 저장: {path}")


if __name__ == "__main__":
    main()
