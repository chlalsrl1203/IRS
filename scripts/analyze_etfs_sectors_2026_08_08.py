"""
미국 섹터/테마 ETF 추가 분석 - 2026-08-08 (XLY, SMH, IYR).

경위: "계속해서 섹터 확장" 요청에 따른 v3.39 후속. 이번 조사에서 확인한 것:
  - KODEX 미국S&P500경기소비재(453660)가 "S&P Consumer Discretionary Select
    Sector Index(Price Return)"를 추종한다는 걸 확인해 XLY 원본을 새로 분석한다.
  - **소재(Materials/XLB)는 KODEX/TIGER/ACE 어디서도 국내 상장 상품을 찾지
    못했다** - 추측하지 않고 정직한 공백으로 남긴다(GICS 11섹터 중 유일하게
    국내 래퍼가 없는 섹터).
  - **테크놀로지(463680)는 v3.39부터 총보수 미확인으로 계속 제외 중** - 이번에도
    재시도했으나 확인 못함.

**2026-08-08 후반 - 사용자가 제공한 실제 거래앱 "지금 뜨고 있는 카테고리"
스크린샷(GICS 섹터보다 훨씬 세분화된 테마 목록, 반도체 밸류체인이 상위 11개
중 6개를 차지)을 근거로 두 섹터를 추가한다:**

  - **반도체(SMH)**: KODEX 미국반도체(390390)가 "MVIS US Listed Semiconductor
    25 Index"를 추종한다는 걸 확인해, **같은 지수를 추종하는 SMH(VanEck
    Semiconductor ETF)**를 미국 원본으로 신규 분석한다. ⚠️ 처음엔 TIGER
    미국필라델피아반도체나스닥(381180, PHLX Semiconductor Sector Index 추종)에
    맞춰 SOXX를 원본으로 쓰려 했으나, **SOXX는 2021-06-21에 PHLX Semiconductor
    Sector Index에서 NYSE Semiconductor Index로 추종지수를 변경했다**(공식
    확인) - 그대로 썼으면 TIGER 미국필라델피아반도체나스닥과 다른 지수를
    재사용하는 함정에 빠질 뻔했다(다우존스30/배당다우존스, 리츠 사례와 같은
    계열). TIGER 미국필라델피아반도체나스닥은 지수가 진짜로 일치하는 미국
    상장 ETF를 찾지 못해 이번 배치에서 보류한다.
  - **리츠(IYR)**: v3.39에서 KODEX 미국부동산리츠(H)(352560, "Dow Jones US
    Real Estate Index" 추종)를 XLRE와 지수가 달라 제외했었는데, **IYR(iShares
    U.S. Real Estate ETF)가 "Dow Jones U.S. Real Estate Capped Index"를
    추종**한다는 걸 확인해 새로 짝지었다. ⚠️ "Capped"(집중도 상한 적용) 여부가
    KODEX 쪽 표기("Dow Jones US Real Estate 지수")와 정확히 일치하는지는
    확정하지 못했다 - XLE/KODEX에너지 때와 동일한 "같은 지수 계열이되 완전
    동일 여부 미확정"으로 취급한다.

원자료: stockanalysis.com/etf/{ticker} (2026-08-08 조회).

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
    ETFInputs(
        ticker="SMH", name="VanEck Semiconductor ETF", tracks="반도체 섹터",
        pe_by_source={"stockanalysis(trailing)": 44.71},
        expense_ratio=0.0035, n_holdings=26, top10_weight=0.7146,
        risk_free_rate=RF,
        expected_earnings_growth=0.12,
        expected_earnings_growth_basis=(
            "AI 데이터센터 투자 슈퍼사이클의 직접 수혜 섹터(상위비중 NVIDIA "
            "21.70%+TSM 9.51%+Broadcom 6.73%). CLAUDE.md에 기록된 KEYS/KLAC "
            "패턴(trailing CAGR이 AI 수요 인플렉션을 과소추정)과 반대 방향의 "
            "함정을 피하려 12%로 XLK(12%)와 동일하게 잡되, 반도체는 역사적으로 "
            "가장 극심한 boom/bust 사이클을 가진 섹터라 사이클 반전 리스크가 "
            "XLK보다도 크다는 점을 감안해 그 이상으로는 올리지 않았다 [추정치]."
        ),
        dividend_yield=0.0019, return_1y=1.0393,
        data_sources=["stockanalysis.com/etf/smh (2026-08-08 조회)"],
    ),
    ETFInputs(
        ticker="IYR", name="iShares U.S. Real Estate ETF", tracks="리츠(부동산) 섹터",
        pe_by_source={"stockanalysis(trailing)": 27.83},
        expense_ratio=0.0038, n_holdings=65, top10_weight=0.5218,
        risk_free_rate=RF,
        expected_earnings_growth=0.05,
        expected_earnings_growth_basis=(
            "리츠는 임대료 상승률+신규개발 기반 성장이라 유틸리티(5%)와 비슷한 "
            "완만한 성장률을 채택 [추정치]. 금리 민감도가 매우 높은 섹터라 "
            "(REIT 배당수익률이 국채금리와 경쟁) 성장률 자체보다 할인율 변화가 "
            "밸류에이션을 더 크게 흔든다는 점을 감안해서 볼 것."
        ),
        dividend_yield=0.0216, return_1y=0.1246,
        data_sources=["stockanalysis.com/etf/iyr (2026-08-08 조회)"],
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
