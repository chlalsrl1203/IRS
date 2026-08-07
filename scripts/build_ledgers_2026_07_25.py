"""
2026-07-25 세션에서 분석한 4종목(CDNS/MNST/ZTS/PH)의 ledger를 생성한다.

이 스크립트를 남기는 이유: 큐22(Cadence)가 "엔진계산은 했다"는 기록만 남고
입력값이 사라져 전면 재수행해야 했던 사고(2026-07-25 확인)를 되풀이하지 않기
위함이다. 원자료 출처와 주관적 입력의 근거까지 코드에 박아둔다.

실행: python3 scripts/build_ledgers_2026_07_25.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.pipeline import AnalysisInputs, run_analysis, save_ledger

RF = 0.0447  # 미국 10Y 국채, Alpha Vantage TREASURY_YIELD 2026-06 기준
AV = "Alpha Vantage (조회일 2026-07-25)"

SPECS = [
    dict(
        ticker="CDNS",
        company_name="Cadence Design Systems, Inc.",
        revenue_by_year={
            2014: 1580932000, 2015: 1702091000, 2016: 1816083000, 2017: 1943032000,
            2018: 2138022000, 2019: 2336319000, 2020: 2682891000, 2021: 2988244000,
            2022: 3561718000, 2023: 4089986000, 2024: 4641264000, 2025: 5296759000,
        },
        operating_income_by_year={
            2014: 206644000, 2015: 285430000, 2016: 244901000, 2017: 323955000,
            2018: 396209000, 2019: 491796000, 2020: 645552000, 2021: 779089000,
            2022: 1073686000, 2023: 1251225000, 2024: 1350763000, 2025: 1649781000,
        },
        operating_cashflow_by_year={
            2014: 316722000, 2015: 378200000, 2016: 444879000, 2017: 470740000,
            2018: 604751000, 2019: 729600000, 2020: 904922000, 2021: 1100958000,
            2022: 1241894000, 2023: 1349176000, 2024: 1260551000, 2025: 1728781000,
        },
        capex_by_year={
            2014: 39810000, 2015: 44808000, 2016: 53712000, 2017: 57901000,
            2018: 61503000, 2019: 74605000, 2020: 94813000, 2021: 66881000,
            2022: 124215000, 2023: 102503000, 2024: 142542000, 2025: 141871000,
        },
        market_cap=92952756000,
        net_debt=2480150000 - (3001317000 + 154213000),
        ebitda=1649781000 + 233844000,
        competitor_threat_weights=[0.75, 0.35, 0.15],
        market_share_trend_pp_per_year=-1.0,
        active_antitrust_or_regulatory_case=False,
        demand_sensitivity_pct=0.15,
        subjective_input_basis=(
            "Synopsys 0.75(2025-07 Ansys $35B 인수완료로 EDA 35~40% 점유, Cadence 30~35%), "
            "Siemens EDA 0.35, Keysight 0.15. 점유율추세 -1.0pp/년은 시장조사 기사 기반 [추정치]. "
            "2025-07 DOJ/BIS 수출통제 유죄인정($140.6M)은 반독점/규제소송이 아니라 "
            "active_antitrust_or_regulatory_case=False로 두고 정성리스크로만 서술."
        ),
        model_used="single_stage",
        model_choice_reason=(
            "성숙 stalwart(매출 CAGR 12~14%, 순현금)로 Gordon Growth 적용. "
            "two_stage(19.69%)와 11%p 괴리가 있어 v3.19 모델괴리 경고 대상이며, "
            "메모 5번에 '모델선택에 따라 결론이 갈린다'고 명시함."
        ),
        data_sources=[AV, "WebSearch: EDA market share / DOJ-BIS settlement"],
    ),
    dict(
        ticker="MNST",
        company_name="Monster Beverage Corporation",
        revenue_by_year={
            2014: 2464867000, 2015: 2722564000, 2016: 3049393000, 2017: 3369045000,
            2018: 3807183000, 2019: 4200819000, 2020: 4598638000, 2021: 5541352000,
            2022: 6311050000, 2023: 7140027000, 2024: 7492709000, 2025: 8294343000,
        },
        operating_income_by_year={
            2014: 747505000, 2015: 893653000, 2016: 1085338000, 2017: 1198787000,
            2018: 1283619000, 2019: 1402939000, 2020: 1633153000, 2021: 1797467000,
            2022: 1584721000, 2023: 1953355000, 2024: 1930294000, 2025: 2419354000,
        },
        operating_cashflow_by_year={
            2014: 585567000, 2015: 207986000, 2016: 701355000, 2017: 987731000,
            2018: 1161881000, 2019: 1113762000, 2020: 1364163000, 2021: 1155741000,
            2022: 887699000, 2023: 1717753000, 2024: 1928533000, 2025: 2098177000,
        },
        capex_by_year={
            2014: 31363000, 2015: 42493000, 2016: 105337000, 2017: 93128000,
            2018: 74925000, 2019: 110398000, 2020: 67272000, 2021: 57453000,
            2022: 212153000, 2023: 234724000, 2024: 264074000, 2025: 132275000,
        },
        market_cap=91433976000,
        net_debt=0 - (2088117000 + 677084000),  # 무차입, 순현금
        ebitda=2419354000 + 114441000,
        competitor_threat_weights=[0.6, 0.4, 0.2],
        market_share_trend_pp_per_year=-0.5,
        active_antitrust_or_regulatory_case=False,
        demand_sensitivity_pct=0.10,
        subjective_input_basis=(
            "Red Bull 0.6(글로벌 43% vs Monster 39%), Celsius 0.4(US 10%이나 "
            "PepsiCo 지분 11%+Rockstar 인수로 급성장), 기타 0.2. "
            "점유율추세 -0.5pp/년은 Celsius 잠식 관련 기사 기반 [추정치]."
        ),
        model_used="single_stage",
        model_choice_reason=(
            "성숙 stalwart, 순현금 구조. 기존 MNST 기록들(v3.13 +1.44%p, v3.17 +0.43%p)이 "
            "모두 소규모 Gap 패턴이라 single_stage 컨벤션과 일치."
        ),
        data_sources=[AV, "WebSearch: energy drink market share 2026"],
    ),
    dict(
        ticker="ZTS",
        company_name="Zoetis Inc.",
        revenue_by_year={
            2014: 4785000000, 2015: 4765000000, 2016: 4888000000, 2017: 5307000000,
            2018: 5825000000, 2019: 6260000000, 2020: 6675000000, 2021: 7776000000,
            2022: 8080000000, 2023: 8544000000, 2024: 9256000000, 2025: 9467000000,
        },
        operating_income_by_year={
            2014: 970000000, 2015: 1082000000, 2016: 1404000000, 2017: 1727000000,
            2018: 1881000000, 2019: 2018000000, 2020: 2269000000, 2021: 2803000000,
            2022: 2928000000, 2023: 3069000000, 2024: 3392000000, 2025: 3597000000,
        },
        operating_cashflow_by_year={
            2014: 626000000, 2015: 664000000, 2016: 713000000, 2017: 1346000000,
            2018: 1790000000, 2019: 1795000000, 2020: 2126000000, 2021: 2213000000,
            2022: 1912000000, 2023: 2353000000, 2024: 2953000000, 2025: 2904000000,
        },
        capex_by_year={
            2014: 195000000, 2015: 224000000, 2016: 216000000, 2017: 224000000,
            2018: 338000000, 2019: 460000000, 2020: 453000000, 2021: 477000000,
            2022: 586000000, 2023: 732000000, 2024: 655000000, 2025: 621000000,
        },
        market_cap=31945181000,
        net_debt=9493000000 - 2312000000,
        ebitda=3597000000 + 487000000,
        competitor_threat_weights=[0.6, 0.3, 0.25],
        market_share_trend_pp_per_year=-2.0,
        active_antitrust_or_regulatory_case=False,
        demand_sensitivity_pct=0.10,
        subjective_input_basis=(
            "Elanco 0.6(Zenrelia=Apoquel 저가대체, Credelio Quattro=Trio 대비 광범위+저가로 "
            "실제 처방 점유율 잠식중), Merck Animal Health 0.3, Boehringer 0.25. "
            "점유율추세 -2.0pp/년은 2026-05-07 실적공시(처방/내원/가격민감도 동시악화) 기반 [추정치]. "
            "증권집단소송은 반독점/규제소송이 아니므로 active_case=False, 정성리스크로 서술."
        ),
        model_used="single_stage",
        model_choice_reason=(
            "성숙 stalwart. 이 종목은 single_stage(3.52%)와 two_stage(3.57%)가 거의 같은 값이라 "
            "모델 선택에 강건함(v3.19 괴리경고 미발동)."
        ),
        data_sources=[AV, "WebSearch: Zoetis Librela lawsuit / Elanco competition"],
    ),
    dict(
        ticker="PH",
        company_name="Parker-Hannifin Corporation",
        revenue_by_year={
            2014: 13215971000, 2015: 12711744000, 2016: 11360753000, 2017: 12029312000,
            2018: 14302392000, 2019: 14320324000, 2020: 13695520000, 2021: 14347640000,
            2022: 15861608000, 2023: 19065194000, 2024: 19929606000, 2025: 19850000000,
        },
        operating_income_by_year={
            2014: 1489230000, 2015: 1468066000, 2016: 1297957000, 2017: 1450128000,
            2018: 2013704000, 2019: 2123764999, 2020: 1986786000, 2021: 2402287000,
            2022: 2814745000, 2023: 3220662000, 2024: 3901280000, 2025: 4060000000,
        },
        operating_cashflow_by_year={
            2014: 1387893000, 2015: 1363233000, 2016: 1210778000, 2017: 1300563000,
            2018: 1596700000, 2019: 1730140000, 2020: 2070949000, 2021: 2575001000,
            2022: 2441730000, 2023: 2979930000, 2024: 3384329000, 2025: 3776000000,
        },
        capex_by_year={
            2014: 216340000, 2015: 215527000, 2016: 149407000, 2017: 203748000,
            2018: 247667000, 2019: 195089000, 2020: 232591000, 2021: 209957000,
            2022: 230044000, 2023: 380747000, 2024: 400112000, 2025: 435000000,
        },
        market_cap=124255617000,
        net_debt=9640000000 - 467000000,
        ebitda=4060000000 + 907000000,
        competitor_threat_weights=[0.5, 0.35, 0.3],
        market_share_trend_pp_per_year=0.0,
        active_antitrust_or_regulatory_case=False,
        demand_sensitivity_pct=0.35,
        subjective_input_basis=(
            "Eaton 0.5, Emerson 0.35, Honeywell 0.3. 산업재 특성상 demand_sensitivity 0.35로 "
            "높게 설정(2016년 -10.63% 실제 역성장 이력). 점유율추세 0.0은 M&A로 매출은 늘지만 "
            "유기적 점유율 변화 근거가 없어 중립 처리 [추정치]. 회계연도는 6월 결산."
        ),
        model_used="two_stage",
        model_choice_reason=(
            "기존 v3.13 기록의 내재성장률 ~15.9%와 two_stage 재계산 15.09%가 거의 일치해 "
            "이 종목의 확립된 컨벤션으로 확인. single_stage로 계산하면 7.99%가 나와 Gap이 "
            "-1.48%p(적정가)로 판정이 뒤집히므로 반드시 two_stage를 쓸 것 - "
            "2026-07-25 세션에서 실제로 이 실수를 했다가 기존기록과 대조해 잡았다."
        ),
        data_sources=[AV, "WebSearch: Parker Filtration Group / CIRCOR / S&P outlook"],
    ),
]


def main():
    for spec in SPECS:
        inputs = AnalysisInputs(risk_free_rate=RF, **spec)
        result = run_analysis(inputs)
        path = save_ledger(result)
        print(
            f"{result['meta']['ticker']:6} "
            f"DRS={result['drs']['score']:5.2f} "
            f"Gap={result['expectation_gap']*100:+7.2f}%p "
            f"RAR={result['rar']:+8.4f} "
            f"Conf={result['confidence']['final']:3d} "
            f"{result['judgment']:12} -> {path}"
        )


if __name__ == "__main__":
    main()
