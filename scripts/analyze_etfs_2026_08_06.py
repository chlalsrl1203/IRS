"""
미국 상장 ETF 8종 정식 분석 - 2026-08-06(v3.35 데이터 보강).

경위: 사용자가 "voo같은 미국에 상장된 etf 조사하라고, 개별 종목이 아니라"를
요청했을 때, 이 프로젝트에는 ETF를 다룰 코드가 아예 없었다(회사 엔진은 10-K
재무제표 전용). 1차 대응은 WebSearch 스냅샷을 JSON 리포트로 남기는 것이었고
(`reports/etf_valuation_comparison_2026-08-06.json`) 재현성이 낮다는 한계를
스스로 명시했었다. 이 스크립트는 그 조사를 `engine/etf_engine.py` +
`engine/etf_pipeline.py`로 정식 재실행해 ledger로 남긴다.

원자료(전부 2026-08-06 조회):
  - stockanalysis.com/etf/{ticker}: 트레일링 P/E, 배당수익률, 1년 수익률
  - FactSet Earnings Insight(2026-08 초): S&P500 12개월 forward P/E 19.6x
  - GuruFocus: 나스닥100 P/E
  - Goldman Sachs 인용(24/7 Wall St, Benzinga 2026-07): Russell2000 forward 26x,
    Nasdaq100 24x, S&P500 20x - **stockanalysis 수치와 정면 배치되는 출처라
    일부러 함께 넣는다**(이 엔진의 핵심 설계 근거)
  - allinvestview.com/compare/{A}-vs-{B} (2026-08-06 기준): 섹터 ETF 4종의
    **2차 트레일링 P/E**. v3.34까지 섹터 ETF는 출처가 1개뿐이라 IWM식 집계왜곡을
    검증할 수단이 없었는데(엔진이 [단일 출처 경고]로 표시), v3.35에서 해소했다.
  - multpl.com S&P500 Earnings by Year: VOO의 실적 EPS 앵커(⚠️**실질** 기준)
  - totalrealreturns.com: YTD·1년 총수익률
  - tradingeconomics/FRED DGS10: 10년 국채금리 4.61%

⚠️ 보유종목수·상위10비중·무이익비중은 각 운용사 팩트시트/ETF 데이터 사이트의
공표치를 옮긴 것으로, 일부는 근사치다(주석에 개별 명시). 이 값들은 ERS(위험점수)
에만 영향을 주고 Gap 계산에는 관여하지 않는다.

실행: python3 scripts/analyze_etfs_2026_08_06.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.etf_pipeline import (
    ETFInputs,
    compare_etfs,
    format_comparison_table,
    format_overlap_table,
    portfolio_overlap_report,
    run_etf_analysis,
    save_etf_ledger,
)

RF = 0.0461  # 미국 10Y, 2026-08-06

COMMON_SOURCES = [
    "stockanalysis.com/etf/{ticker} (트레일링 P/E·배당수익률·1년수익률, 2026-08-06 조회)",
    "totalrealreturns.com (YTD·1년 총수익률, 2026-08-05 기준)",
    "tradingeconomics / FRED DGS10 (미국10Y 4.61%, 2026-08-05/06)",
]

CANDIDATES = [
    ETFInputs(
        ticker="VOO", name="Vanguard S&P 500 ETF", tracks="S&P 500",
        # 트레일링(stockanalysis)과 forward(FactSet) 둘 다 확보 - 이 괴리는
        # 정상적인 것이다(forward가 낮은 건 이익 성장 기대가 반영된 결과).
        pe_by_source={"stockanalysis(trailing)": 27.53, "FactSet(forward)": 19.6},
        expense_ratio=0.0003, n_holdings=505, top10_weight=0.37,
        risk_free_rate=RF,
        expected_earnings_growth=0.08,
        expected_earnings_growth_basis=(
            "S&P500 장기 명목 EPS 성장률. 과거 수십년 실적이 7~8%대(명목 GDP 성장 "
            "+ 마진확장)라는 통념을 채택 [추정치] - 이 프로젝트가 자체 검증한 값이 "
            "아니라 시장 통념이므로 ±2%p 민감도를 감안해서 볼 것."
        ),
        dividend_yield=0.0104, return_1y=0.2341, return_ytd=0.1352,
        pct_unprofitable_constituents=0.03,  # 대형주 지수라 적자기업 비중 낮음(근사)
        # v3.35 방향A: 실측 앵커. multpl.com S&P500 EPS는 **실질(constant June
        # 2026 dollars)** 기준이라 basis="real" + 인플레이션 환산이 필수다
        # (명목 기대성장률과 그대로 비교하면 인플레율만큼 조용히 어긋난다).
        # ⚠️ 기준연도를 2020(코로나 저점 EPS 120.68)으로 잡으면 실질 CAGR이
        # 15%대로 튄다 - BKNG에서 배운 저점 기저효과다. 저점을 피해 전체
        # 구간(2014~2025)을 쓴다.
        realized_eps_by_year={
            2014: 145.51, 2015: 122.17, 2016: 130.78, 2017: 148.85,
            2018: 175.98, 2019: 181.25, 2020: 120.68, 2021: 237.01,
            2022: 194.38, 2023: 209.50, 2024: 222.39, 2025: 247.98,
        },
        realized_eps_basis="real",
        inflation_for_conversion=0.025,
        top10_holdings={
            "NVDA": 0.0750, "AAPL": 0.0658, "MSFT": 0.0429, "AMZN": 0.0361,
            "GOOGL": 0.0324, "AVGO": 0.0277, "GOOG": 0.0258, "MU": 0.0201,
            "META": 0.0191, "TSLA": 0.0183,
        },
        data_sources=COMMON_SOURCES + [
            "FactSet Earnings Insight 2026-08 초: S&P500 12M forward P/E 19.6x "
            "(5년평균 19.9x / 10년평균 19.0x)",
            "multpl.com S&P500 Earnings by Year (2014~2025, 실질 constant "
            "June 2026 dollars 기준, 2026-08-07 조회)",
        ],
    ),
    ETFInputs(
        ticker="QQQ", name="Invesco QQQ Trust", tracks="Nasdaq-100",
        pe_by_source={"stockanalysis(trailing)": 33.04, "GoldmanSachs(forward)": 24.0},
        expense_ratio=0.0020, n_holdings=101, top10_weight=0.51,
        risk_free_rate=RF,
        expected_earnings_growth=0.11,
        expected_earnings_growth_basis=(
            "나스닥100은 메가캡 기술주 비중이 높아 S&P500(8%)보다 높은 장기 이익성장을 "
            "가정. 다만 AI 자본지출 사이클 의존도가 커 지속가능성이 검증되지 않았다 "
            "[추정치] - 이 값이 Gap을 좌우하므로 특히 보수적으로 볼 것."
        ),
        dividend_yield=0.0042, return_1y=0.2777, return_ytd=0.1704,
        pct_unprofitable_constituents=0.05,
        top10_holdings={
            "AAPL": 0.0815, "NVDA": 0.0786, "MSFT": 0.0558, "MU": 0.0453,
            "AMZN": 0.0422, "AMD": 0.0364, "GOOGL": 0.0323, "AVGO": 0.0306,
            "GOOG": 0.0303, "META": 0.0266,
        },
        data_sources=COMMON_SOURCES + ["GuruFocus 나스닥100 PE(2026-08)"],
    ),
    ETFInputs(
        # ⭐ 이 엔진을 만든 이유. 출처에 따라 '가장 쌈'과 '가장 비쌈'이 갈린다.
        ticker="IWM", name="iShares Russell 2000 ETF", tracks="Russell 2000 (소형주)",
        pe_by_source={"stockanalysis(trailing)": 20.07, "GoldmanSachs(forward)": 26.0},
        expense_ratio=0.0019, n_holdings=1954, top10_weight=0.041,
        risk_free_rate=RF,
        expected_earnings_growth=0.11,
        expected_earnings_growth_basis=(
            "소형주 이익성장 전망 17~18%(2026-08 컨센서스, 2년 연속)를 그대로 쓰지 "
            "않고 크게 할인한 값. 근거: 이 전망 자체가 '아직 증명되지 않았다'는 "
            "지적이 병존하고(Benzinga 2026-07 valuation trap 경고), Russell2000은 "
            "무이익 기업 비중이 커 컨센서스 이익전망의 실현률이 낮은 경향이 있다 "
            "[추정치]."
        ),
        dividend_yield=0.0089, return_1y=0.3784, return_ytd=0.2229,
        # Russell2000 무이익 기업 비중은 널리 인용되는 30~40% 구간의 중간값 근사.
        # 이 값이 곧 P/E 출처 괴리의 근본 원인이다.
        pct_unprofitable_constituents=0.35,
        # 소형주 지수라 top10 비중이 개별 0.3%대로 극히 낮다(합계 3.2%).
        # 광범위지수·섹터ETF와 겹칠 여지가 구조적으로 거의 없다는 뜻이다.
        top10_holdings={
            "MOG.A": 0.0036, "UMBF": 0.0034, "VSAT": 0.0034, "HUT": 0.0033,
            "CYTK": 0.0032, "BTSG": 0.0032, "GKOS": 0.0031, "ONB": 0.0030,
            "EAT": 0.0029, "FROG": 0.0029,
        },
        data_sources=COMMON_SOURCES + [
            "24/7 Wall St(2026-07): 연초 Russell2000 forward P/E ~18x vs S&P500 26x "
            "(30년래 최대 할인이라는 견해)",
            "Benzinga(2026-07) 인용 Goldman Sachs: Russell2000 forward 26x로 "
            "Nasdaq100(24x)·S&P500(20x)보다 오히려 비싸다는 정반대 견해 + "
            "'valuation trap' 경고",
        ],
        falsification_conditions=(
            "2026 하반기~2027 상반기 실적에서 Russell2000 실현 이익성장률이 "
            "컨센서스(17~18%)의 절반(약 9%)에도 못 미치면, 트레일링 P/E가 싸 보이던 "
            "것이 이익 기저의 착시였다는 뜻이므로 이 판정을 재검토할 것."
        ),
    ),
    ETFInputs(
        ticker="XLK", name="Technology Select Sector SPDR", tracks="기술 섹터",
        pe_by_source={"stockanalysis(trailing)": 37.37,
                      "allinvestview(trailing)": 34.96},
        expense_ratio=0.0008, n_holdings=69, top10_weight=0.60,
        risk_free_rate=RF,
        expected_earnings_growth=0.12,
        expected_earnings_growth_basis=(
            "기술섹터 장기 이익성장률. AI 사이클 수혜가 크나 그만큼 사이클 반전 "
            "리스크도 크다 [추정치]."
        ),
        dividend_yield=0.0043, return_1y=0.4250,
        top10_holdings={
            "NVDA": 0.1391, "AAPL": 0.1298, "MSFT": 0.0988, "AVGO": 0.0527,
            "AMD": 0.0423, "MU": 0.0366, "CSCO": 0.0320, "INTC": 0.0298,
            "AMAT": 0.0281, "LRCX": 0.0256,
        },
        data_sources=COMMON_SOURCES,
    ),
    ETFInputs(
        ticker="XLE", name="Energy Select Sector SPDR", tracks="에너지 섹터",
        pe_by_source={"stockanalysis(trailing)": 20.94,
                      "allinvestview(trailing)": 22.10},
        expense_ratio=0.0008, n_holdings=23, top10_weight=0.75,
        risk_free_rate=RF,
        expected_earnings_growth=0.04,
        expected_earnings_growth_basis=(
            "에너지는 유가 사이클에 종속돼 장기 이익성장률을 구조적으로 낮게 잡는다 "
            "(장기적으로 실질 성장보다 인플레이션 연동에 가깝다) [추정치]."
        ),
        dividend_yield=0.0265, return_1y=0.3840,
        top10_holdings={
            "XOM": 0.2099, "CVX": 0.1506, "COP": 0.0606, "MPC": 0.0494,
            "PSX": 0.0494, "VLO": 0.0477, "EOG": 0.0450, "SLB": 0.0430,
            "KMI": 0.0388, "WMB": 0.0387,
        },
        data_sources=COMMON_SOURCES,
    ),
    ETFInputs(
        ticker="XLF", name="Financial Select Sector SPDR", tracks="금융 섹터",
        pe_by_source={"stockanalysis(trailing)": 17.85,
                      "allinvestview(trailing)": 18.03},
        expense_ratio=0.0008, n_holdings=73, top10_weight=0.56,
        risk_free_rate=RF,
        expected_earnings_growth=0.07,
        expected_earnings_growth_basis=(
            "금융섹터 장기 이익성장률. 명목GDP 성장에 레버리지가 얹히는 구조라 "
            "S&P500 평균과 비슷하거나 소폭 낮게 잡음 [추정치]."
        ),
        dividend_yield=0.0139, return_1y=0.1347,
        top10_holdings={
            "JPM": 0.1175, "BRK.B": 0.1161, "V": 0.0746, "MA": 0.0562,
            "BAC": 0.0504, "GS": 0.0382, "WFC": 0.0333, "MS": 0.0319,
            "C": 0.0286, "AXP": 0.0227,
        },
        data_sources=COMMON_SOURCES,
    ),
    ETFInputs(
        ticker="XLU", name="Utilities Select Sector SPDR", tracks="유틸리티 섹터",
        pe_by_source={"stockanalysis(trailing)": 22.88,
                      "allinvestview(trailing)": 20.50},
        expense_ratio=0.0008, n_holdings=31, top10_weight=0.62,
        risk_free_rate=RF,
        expected_earnings_growth=0.05,
        expected_earnings_growth_basis=(
            "규제산업 특성상 요금인상률 + 설비투자 기반 성장으로 제한된다 "
            "(전통적으로 4~6%) [추정치]. AI 데이터센터 전력수요가 상방요인이나 "
            "아직 실적으로 확인되지 않았다."
        ),
        dividend_yield=0.0274, return_1y=0.0279,
        top10_holdings={
            "NEE": 0.1300, "SO": 0.0755, "DUK": 0.0698, "CEG": 0.0630,
            "AEP": 0.0503, "D": 0.0435, "SRE": 0.0413, "ETR": 0.0356,
            "VST": 0.0356, "XEL": 0.0349,
        },
        data_sources=COMMON_SOURCES,
    ),
    ETFInputs(
        # v3.35에서 추가 - v3.34까지는 P/E 미확보로 빠져 있던 종목.
        ticker="DIA", name="SPDR Dow Jones Industrial Average ETF",
        tracks="Dow Jones Industrial Avg",
        pe_by_source={"stockanalysis(trailing)": 25.57},
        expense_ratio=0.0016, n_holdings=31, top10_weight=0.52,
        risk_free_rate=RF,
        expected_earnings_growth=0.07,
        expected_earnings_growth_basis=(
            "다우30은 성숙 대형 우량주 중심이라 S&P500(8%)보다 소폭 낮은 장기 "
            "이익성장률을 가정 [추정치]. 가격가중 지수라 시총가중 지수와 성격이 "
            "달라 S&P500 실적 앵커를 그대로 쓸 수 없다는 점도 감안."
        ),
        dividend_yield=0.0133, return_1y=0.2384, return_ytd=0.1383,
        # ⚠️ 다우는 **가격가중** 지수라 비중이 시총이 아니라 주가에 비례한다
        # (GS 11.66%가 1위인 이유). 시총가중 ETF와 겹침을 비교할 때 이 차이를
        # 감안할 것 - 같은 종목이라도 비중 산정 원리가 다르다.
        top10_holdings={
            "GS": 0.1166, "CAT": 0.0920, "MSFT": 0.0513, "UNH": 0.0479,
            "AMGN": 0.0441, "TRV": 0.0428, "V": 0.0417, "JPM": 0.0399,
            "SHW": 0.0392, "AXP": 0.0384,
        },
        data_sources=COMMON_SOURCES,
    ),
]


def main():
    results = [run_etf_analysis(c) for c in CANDIDATES]
    ordered = compare_etfs(results)

    print("=" * 118)
    print(f"미국 상장 ETF 정식 분석 ({len(results)}종목, 엔진 "
          f"{results[0]['meta']['engine_version']}, 2026-08-06)")
    print("=" * 118)
    print(format_comparison_table(ordered))
    print()
    print("정렬 규칙: 신뢰할 수 없는 ETF(P/E 출처간 판정불일치 또는 성장률 가정 취약)를\n"
          "          뒤로 보내고, 나머지는 보수적 Gap(가장 비싼 P/E 기준) 내림차순.")
    print()
    print("⚠️ 이 표에서 객관적인 값은 '시장요구성장'(P/E와 r만으로 결정)뿐이다.\n"
          "   '가정성장'과 'Gap'은 분석자가 입력한 성장률에 1:1로 좌우되므로,\n"
          "   Gap 순위를 그대로 투자 순위로 쓰지 말 것(v3.34 자체 진단: 성장률을\n"
          "   전부 8%로 통일하면 순위가 거의 정반대로 뒤집혔다).")
    print()

    print("=" * 118)
    print("⚠️ ETF간 중복노출 - '여러 개를 같이 사면 분산되는가'")
    print("=" * 118)
    overlap = portfolio_overlap_report(ordered)
    print(format_overlap_table(overlap))
    print()
    print("개별 ETF 판정만 보면 절대 드러나지 않는 위험이다 - 각각은 '적정가'라도")
    print("함께 사면 같은 메가캡을 두세 번 사는 것일 수 있다.")
    print()
    print("⚠️ '측정 불가' 쌍을 '겹침 없음'으로 읽지 말 것(v3.37 정정) - 예를 들어")
    print("XLF(금융섹터)는 정의상 S&P500 구성종목의 부분집합이라 VOO와 실제로는")
    print("상당히 겹친다. top10 표본끼리만 우연히 안 겹쳤을 뿐이며, 전체 구성종목")
    print("데이터가 확보돼야 이 쌍들의 실제 겹침을 측정할 수 있다.")
    print()

    print("=" * 118)
    print("종목별 상세")
    print("=" * 118)
    for res in ordered:
        m, v = res["meta"], res["valuation"]
        print(f"\n[{m['ticker']}] {m['name']} - {m['tracks']}")
        print(f"  ERS(위험점수) {res['ers']['score']:.1f} "
              f"-> ERP {res['discount_rate']['erp']*100:.2f}% "
              f"-> 요구수익률 r {res['discount_rate']['r']*100:.2f}%")
        print(f"  ERS 구성: " + " / ".join(
            f"{k} {val:.0f}" for k, val in res["ers"]["components"].items()))
        print(f"  가정한 장기 이익성장률: "
              f"{res['growth']['expected_earnings_growth']*100:.2f}%")
        for src, s in v["by_source"].items():
            print(f"    - {src:28} P/E {s['pe_ratio']:6.2f}x "
                  f"-> 내재성장 {s['implied_growth']*100:6.2f}% "
                  f"-> Gap {s['gap']*100:+7.2f}%p  {s['judgment']}")
        print(f"  보수율 {res['cost']['expense_ratio']*100:.2f}% "
              f"-> {res['cost']['holding_years']}년 누적 확정비용 "
              f"{res['cost']['cumulative_drag']*100:.2f}%")
        print(f"  Fed모델 스프레드(참고용, 판정 미반영): "
              f"{res['fed_model']['spread']*100:+.2f}%p")
        if res["data_limitations"]:
            for x in res["data_limitations"]:
                print(f"    ⚠️ {x}")

        path = save_etf_ledger(res)
        print(f"  ledger 저장: {path}")

    print("\n" + "=" * 118)
    print("이 결과는 지수 수준 집계지표 기반 상대비교이며, 회사 단위 "
          "run_analysis()와 달리 개별 기업 재무제표를 보지 않는다.")
    print("특히 P/E 출처가 1개뿐인 섹터 ETF(XLK/XLE/XLF/XLU)는 IWM 같은 "
          "집계방식 왜곡을 검증할 수단이 없으므로 forward P/E를 추가 확보할 것.")
    print("=" * 118)

    return ordered


if __name__ == "__main__":
    main()
