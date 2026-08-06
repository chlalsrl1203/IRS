"""
미국 상장 ETF 8종 정식 분석 - 2026-08-06.

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
        data_sources=COMMON_SOURCES + [
            "FactSet Earnings Insight 2026-08 초: S&P500 12M forward P/E 19.6x "
            "(5년평균 19.9x / 10년평균 19.0x)"
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
        pe_by_source={"stockanalysis(trailing)": 37.37},
        expense_ratio=0.0008, n_holdings=69, top10_weight=0.60,
        risk_free_rate=RF,
        expected_earnings_growth=0.12,
        expected_earnings_growth_basis=(
            "기술섹터 장기 이익성장률. AI 사이클 수혜가 크나 그만큼 사이클 반전 "
            "리스크도 크다 [추정치]."
        ),
        dividend_yield=0.0043, return_1y=0.4250,
        data_sources=COMMON_SOURCES,
    ),
    ETFInputs(
        ticker="XLE", name="Energy Select Sector SPDR", tracks="에너지 섹터",
        pe_by_source={"stockanalysis(trailing)": 20.94},
        expense_ratio=0.0008, n_holdings=23, top10_weight=0.75,
        risk_free_rate=RF,
        expected_earnings_growth=0.04,
        expected_earnings_growth_basis=(
            "에너지는 유가 사이클에 종속돼 장기 이익성장률을 구조적으로 낮게 잡는다 "
            "(장기적으로 실질 성장보다 인플레이션 연동에 가깝다) [추정치]."
        ),
        dividend_yield=0.0265, return_1y=0.3840,
        data_sources=COMMON_SOURCES,
    ),
    ETFInputs(
        ticker="XLF", name="Financial Select Sector SPDR", tracks="금융 섹터",
        pe_by_source={"stockanalysis(trailing)": 17.85},
        expense_ratio=0.0008, n_holdings=73, top10_weight=0.56,
        risk_free_rate=RF,
        expected_earnings_growth=0.07,
        expected_earnings_growth_basis=(
            "금융섹터 장기 이익성장률. 명목GDP 성장에 레버리지가 얹히는 구조라 "
            "S&P500 평균과 비슷하거나 소폭 낮게 잡음 [추정치]."
        ),
        dividend_yield=0.0139, return_1y=0.1347,
        data_sources=COMMON_SOURCES,
    ),
    ETFInputs(
        ticker="XLU", name="Utilities Select Sector SPDR", tracks="유틸리티 섹터",
        pe_by_source={"stockanalysis(trailing)": 22.88},
        expense_ratio=0.0008, n_holdings=31, top10_weight=0.62,
        risk_free_rate=RF,
        expected_earnings_growth=0.05,
        expected_earnings_growth_basis=(
            "규제산업 특성상 요금인상률 + 설비투자 기반 성장으로 제한된다 "
            "(전통적으로 4~6%) [추정치]. AI 데이터센터 전력수요가 상방요인이나 "
            "아직 실적으로 확인되지 않았다."
        ),
        dividend_yield=0.0274, return_1y=0.0279,
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
    print("정렬 규칙: 판정이 출처간에 갈린 ETF를 뒤로 보내고, 나머지는 보수적 Gap"
          "(가장 비싼 P/E 기준) 내림차순.")
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
