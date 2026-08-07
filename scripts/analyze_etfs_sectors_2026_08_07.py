"""
미국 Select Sector SPDR 추가 4종 분석 - 2026-08-07 (XLI/XLV/XLC/XLP).

경위: "섹터 다양한 방면으로" 요청에 따라 KRX 래퍼 엔진(v3.38)의 커버리지를
넓히는 첫 단계다. v3.33~v3.37은 8개 미국 ETF(VOO/QQQ/IWM/XLK/XLE/XLF/XLU/DIA)
만 분석했는데, KODEX가 GICS 11개 섹터 중 다수를 국내 상장으로 커버하고
있다는 걸 확인했다(금융/기술/에너지/유틸리티/산업재/헬스케어/커뮤니케이션/
필수소비재). 그중 산업재(XLI)·헬스케어(XLV)·커뮤니케이션서비스(XLC)·
필수소비재(XLP) 4종은 미국 원본 자체가 아직 이 저장소에 없어 먼저 분석한다.
(금융/기술/유틸리티는 이미 ledger_etf/에 있어 국내 래퍼만 추가하면 된다.)

원자료(전부 stockanalysis.com/etf/{ticker}, 2026-08-07 조회): 트레일링 P/E,
보수율, 보유종목수, 상위10비중, 배당수익률, 1년수익률.

⚠️ 이 4종은 forward P/E 등 2차 출처를 확보하지 못해 **단일 출처**다 - 엔진이
`[단일 출처 경고]`로 자동 표시한다. 기존 XLE/XLU가 v3.35에서 2차 출처(트레일링)
를 확보한 것과 달리, 이번엔 시간 관계상 1차 출처만으로 진행했다 - 후속 보강
대상으로 남긴다.

실행: python3 scripts/analyze_etfs_sectors_2026_08_07.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.etf_pipeline import ETFInputs, run_etf_analysis, save_etf_ledger

RF = 0.0461  # 미국 10Y, 기존 배치와 동일 시점 유지

SOURCES = ["stockanalysis.com/etf/{ticker} (트레일링 P/E·배당수익률·1년수익률, 2026-08-07 조회)"]

CANDIDATES = [
    ETFInputs(
        ticker="XLI", name="Industrial Select Sector SPDR Fund", tracks="산업재 섹터",
        pe_by_source={"stockanalysis(trailing)": 29.48},
        expense_ratio=0.0008, n_holdings=85, top10_weight=0.3975,
        risk_free_rate=RF,
        expected_earnings_growth=0.07,
        expected_earnings_growth_basis=(
            "산업재는 항공우주·방산(GE Aerospace·RTX·Boeing)과 중장비(Caterpillar·"
            "Deere)가 상위비중을 차지해 설비투자·리쇼어링 사이클에 연동된다. "
            "명목GDP+α 수준으로 S&P500과 비슷하게 잡음 [추정치] - 관세·공급망 "
            "재편이 상방/하방 어느 쪽으로도 작용할 수 있어 불확실성이 크다."
        ),
        dividend_yield=0.0111, return_1y=0.2427,
        data_sources=SOURCES,
    ),
    ETFInputs(
        ticker="XLV", name="Health Care Select Sector SPDR Fund", tracks="헬스케어 섹터",
        pe_by_source={"stockanalysis(trailing)": 24.53},
        expense_ratio=0.0008, n_holdings=63, top10_weight=0.6096,
        risk_free_rate=RF,
        expected_earnings_growth=0.07,
        expected_earnings_growth_basis=(
            "헬스케어는 인구 고령화로 수요가 구조적으로 방어적이나, 미국 약가인하 "
            "압력(IRA 약가협상)·특허절벽이 상위비중 대형제약사(Eli Lilly·JNJ·"
            "AbbVie)에 지속적인 역풍이다. 전통적인 방어주 프리미엄 성장률(6~8%대) "
            "을 채택 [추정치]."
        ),
        dividend_yield=0.0153, return_1y=0.2917,
        data_sources=SOURCES,
    ),
    ETFInputs(
        ticker="XLC", name="Communication Services Select Sector SPDR Fund",
        tracks="커뮤니케이션서비스 섹터",
        pe_by_source={"stockanalysis(trailing)": 15.14},
        expense_ratio=0.0008, n_holdings=27, top10_weight=0.6753,
        risk_free_rate=RF,
        expected_earnings_growth=0.09,
        expected_earnings_growth_basis=(
            "이 섹터는 성격이 완전히 다른 두 그룹의 혼합이다 - 고성장 플랫폼"
            "(Meta·Alphabet, 광고+AI)과 저성장/쇠퇴 통신(AT&T·Verizon, 유선전화"
            "가입자 감소). 상위비중이 플랫폼 쪽에 크게 쏠려 있어(Meta+Alphabet"
            "만 상위10의 상당부분) S&P500(8%)보다 소폭 높게 잡되, 통신주가 끌어"
            "내리는 효과도 감안해 나스닥100(11%)보다는 낮춘다 [추정치]."
        ),
        dividend_yield=0.0129, return_1y=0.0457,
        data_sources=SOURCES,
    ),
    ETFInputs(
        ticker="XLP", name="Consumer Staples Select Sector SPDR Fund", tracks="필수소비재 섹터",
        pe_by_source={"stockanalysis(trailing)": 22.57},
        expense_ratio=0.0008, n_holdings=38, top10_weight=0.6195,
        risk_free_rate=RF,
        expected_earnings_growth=0.05,
        expected_earnings_growth_basis=(
            "필수소비재(Walmart·Costco·P&G)는 이 프로젝트가 다룬 섹터 중 가장 "
            "경기방어적이고 가격결정력이 낮아 성장률도 가장 낮게 잡는다 - "
            "유틸리티(5%)와 비슷한 수준 [추정치]. 물량 성장은 인구증가율 수준, "
            "가격 성장은 인플레이션 연동에 가깝다."
        ),
        dividend_yield=0.0258, return_1y=0.0718,
        data_sources=SOURCES,
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
