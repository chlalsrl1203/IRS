"""
RSP/BOTZ/BUG 미국 원본 3종 신규 분석 - 2026-08-08 (v3.39 후속 6차 마무리,
동일가중·사이버보안 보수 확보 후속).

경위: v3.39 후속 6차에서 TIGER 미국S&P500동일가중(488500)·TIGER 글로벌AI&
로보틱스INDXX(464310)·TIGER 글로벌AI사이버보안(418670) 3종 전부 지수 일치는
이미 확인해뒀으나(각각 RSP/BOTZ/BUG와 동일 지수), 국내 래퍼 총보수를 그때
못 찾아 보류했었다. 이번에 미래에셋 공식 상품페이지에서 3종 전부 확인했다
(488500=0.20%, 464310=0.49%, 418670=0.49%). 재사용 전제(미국 원본 결과가
있어야 국내 래퍼를 연결할 수 있음)를 채우기 위해 RSP/BOTZ/BUG 3종을 이 엔진
에서는 처음으로 신규 분석한다.

**RSP(동일가중)**: VOO/QQQ와 같은 S&P500 유니버스이지만 동일가중이라 상위
10종목 비중이 2.57%뿐(VOO/QQQ의 메가캡 집중과 정반대) - 메가캡 쏠림 리스크를
줄이는 대신 개별 대형기술주의 초과성장을 덜 반영한다. 성장률은 VOO의
관측앵커(v3.35, 명목 7.59%)보다 소폭 낮춰 잡았다 - 동일가중은 메가캡
빅테크(마진·성장률이 시장평균보다 높은 기업들)의 비중을 구조적으로 낮추기
때문이다.

**BOTZ(로봇·AI)**: v3.39 3차에서 이미 매칭한 ROBO(KODEX 글로벌로봇)와는
**다른 지수**(Indxx Global Robotics & AI Thematic Index vs ROBO Global
Robotics & Automation Index)를 추종하는 별개 종목이다. 상위비중이 산업용
로봇(ABB/Keyence/Fanuc/SMC/Daifuku, 일본·유럽 비중 큼)과 AI/헬스케어
로보틱스(NVIDIA/Intuitive Surgical)로 갈려 ROBO보다 집중도가 높다
(top10 60.19% vs ROBO 17.59%).

**BUG(사이버보안)**: Fortinet/Palo Alto/CrowdStrike/Okta 등 고성장 SaaS형
보안기업 중심(top10 60.87%). 엔터프라이즈 보안 지출은 경기와 무관하게
구조적으로 증가하는 편이라 성장률을 XLK(12%)에 준하는 수준으로 잡되,
그 이상으로는 올리지 않았다 - 이미 상당한 밸류에이션 프리미엄이 반영돼
있어(P/E 27~38x) 추가로 낙관을 얹지 않는다.

2차 P/E 출처는 investing.com(트레일링, 2026-08-08 조회)에서 확보 -
3종 모두 stockanalysis.com 대비 낮게 나온다(집계방식 차이, IWM/XLV급
극단은 아님).

실행: python3 scripts/analyze_etfs_rsp_botz_bug_2026_08_08.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.etf_pipeline import ETFInputs, run_etf_analysis, save_etf_ledger

RF = 0.0461  # 미국 10Y, 기존 배치와 동일 시점 유지

CANDIDATES = [
    ETFInputs(
        ticker="RSP", name="Invesco S&P 500 Equal Weight ETF",
        tracks="S&P 500 동일가중",
        pe_by_source={"stockanalysis(trailing)": 21.02,
                      "investing.com(trailing)": 17.25},
        expense_ratio=0.0020, n_holdings=509, top10_weight=0.0257,
        risk_free_rate=RF,
        expected_earnings_growth=0.07,
        expected_earnings_growth_basis=(
            "VOO의 v3.35 관측앵커(S&P500 실적 CAGR 기반 명목 7.59%)를 출발점으로 "
            "삼되, 동일가중은 마진·성장률이 시장평균보다 높은 메가캡 빅테크의 "
            "비중을 구조적으로 낮추고(top10 비중 2.57%로 VOO/QQQ와 정반대) 중소형 "
            "S&P500 구성종목 비중을 높이므로 소폭 낮춰 7%로 잡았다 [추정치]. "
            "동일가중 자체의 실적 EPS 시계열은 확보하지 못해 앵커가 아니라 VOO "
            "값을 보수적으로 조정한 값이다."
        ),
        dividend_yield=0.0146, return_1y=0.2236,
        top10_holdings={
            "PYPL": 0.0027, "GPN": 0.0027, "TECH": 0.0026, "IP": 0.0026,
            "EXPE": 0.0026, "ZBRA": 0.0025, "BAX": 0.0025, "DASH": 0.0025,
            "IQV": 0.0025, "GRMN": 0.0025,
        },
        data_sources=[
            "stockanalysis.com/etf/rsp (2026-08-08 조회)",
            "investing.com/etfs/rydex-s-p-equal-weight (2026-08-08 조회)",
        ],
    ),
    ETFInputs(
        ticker="BOTZ", name="Global X Robotics & Artificial Intelligence ETF",
        tracks="로봇·AI 테마(Indxx Global Robotics & AI)",
        pe_by_source={"stockanalysis(trailing)": 36.58,
                      "investing.com(trailing)": 28.58},
        expense_ratio=0.0068, n_holdings=66, top10_weight=0.6019,
        risk_free_rate=RF,
        expected_earnings_growth=0.10,
        expected_earnings_growth_basis=(
            "상위비중이 산업용 로봇(ABB 9.73%+Keyence 9.55%+Fanuc 8.63%+SMC "
            "4.72%+Daifuku 3.42%, 일본·유럽 제조업 자동화 중심)과 AI/헬스케어 "
            "로보틱스(NVIDIA 9.55%+Intuitive Surgical 5.75%)로 나뉜다 - 산업재 "
            "자동화 쪽은 설비투자 사이클에 민감해 XLI(산업재, 관측 미확보이나 "
            "성숙섹터 추정)보다는 높지만 NVDA 비중이 낮아 SMH(반도체, 12%)만큼 "
            "높이지는 않았다 [추정치]. ROBO(KODEX 글로벌로봇이 추종, 9%)보다 "
            "NVDA·Intuitive Surgical 비중이 커 1%p 높인 10%로 잡았다."
        ),
        dividend_yield=0.0047, return_1y=0.1247, return_ytd=0.0181,
        top10_holdings={
            "ABB": 0.0973, "NVDA": 0.0955, "6861.T": 0.0955, "6954.T": 0.0863,
            "ISRG": 0.0575, "6273.T": 0.0472, "300124.SZ": 0.0408,
            "6383.T": 0.0342, "CGNX": 0.0244, "AUR": 0.0232,
        },
        data_sources=[
            "stockanalysis.com/etf/botz (2026-08-08 조회)",
            "investing.com/etfs/global-x-robotics---ai-usd (2026-08-08 조회)",
        ],
    ),
    ETFInputs(
        ticker="BUG", name="Global X Cybersecurity ETF",
        tracks="사이버보안 테마(Indxx Cybersecurity)",
        pe_by_source={"stockanalysis(trailing)": 37.51,
                      "investing.com(trailing)": 27.09},
        expense_ratio=0.0050, n_holdings=34, top10_weight=0.6087,
        risk_free_rate=RF,
        expected_earnings_growth=0.12,
        expected_earnings_growth_basis=(
            "Fortinet·Palo Alto·CrowdStrike·Okta 등 고성장 SaaS형 보안기업 "
            "중심(top10 60.87%) - 엔터프라이즈 보안예산은 경기와 비교적 무관하게 "
            "구조적으로 증가하는 항목이라 XLK(기술섹터, 12%)에 준하는 수준으로 "
            "잡았다. 다만 P/E가 이미 27~38x로 상당한 프리미엄을 반영하고 있어 "
            "그 이상으로는 올리지 않았다 [추정치] - 밸류에이션과 성장기대가 "
            "이미 상당 부분 가격에 반영됐을 가능성을 감안."
        ),
        dividend_yield=0.0003, return_1y=0.2253,
        top10_holdings={
            "FTNT": 0.0794, "PANW": 0.0794, "OKTA": 0.0789, "CRWD": 0.0746,
            "QLYS": 0.0548, "TENB": 0.0515, "ZS": 0.0485, "VRNS": 0.0482,
            "AKAM": 0.0470, "SAIL": 0.0464,
        },
        data_sources=[
            "stockanalysis.com/etf/bug (2026-08-08 조회)",
            "investing.com/etfs/bug (2026-08-08 조회)",
        ],
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
