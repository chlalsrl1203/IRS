"""
2026-07-26 매수관점 후보 스크리닝 (글로벌).

기준 도출 근거: 트래커 74건 전수분석에서 저평가/매수군(13건)과 과대평가/회피군(18건)이
두 축으로 갈렸다 - 상세는 engine/screener.py docstring 참고.

이 스크립트를 남기는 이유: 스크리닝 결과만 남기고 입력값이 사라지면 큐22(Cadence)
사고가 반복된다. 모든 원자료를 출처·조회일과 함께 코드에 박아둔다.

원자료 출처: stockanalysis.com (2026-07-26 조회), 단 PYPL의 OCF/capex는
Alpha Vantage CASH_FLOW, 시총/netDebtToEBITDA는 FMP key-metrics-ttm.

실행: python3 scripts/screen_2026_07_26.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.screener import Candidate, screen


def cagr(start, end, years):
    return (end / start) ** (1 / years) - 1


def worst_yoy(series):
    ys = sorted(series)
    return min(series[ys[i]] / series[ys[i - 1]] - 1 for i in range(1, len(ys)))


# ----------------------------------------------------------------------
# 후보군 - 전부 stockanalysis.com 실측(2026-07-26). 연도는 회계연도 라벨 그대로.
# 확보 가능한 구간이 5개년(=4년 CAGR)인 경우가 많아 그 사실을 note에 명시했다.
# ----------------------------------------------------------------------

CANDIDATES = []

# ── Gen Digital (NASDAQ, FY 4월결산) ──
_rev = {2022: 2796e6, 2023: 3317e6, 2024: 3800e6, 2025: 3935e6, 2026: 5000e6}
_fcf = {2022: 968e6, 2023: 751e6, 2024: 2044e6, 2025: 1206e6, 2026: 1523e6}
CANDIDATES.append(Candidate(
    ticker="GEN", name="Gen Digital", exchange="NASDAQ",
    market_cap=15.57e9, fcf0=_fcf[2026],
    revenue_cagr_5y=cagr(_rev[2022], _rev[2026], 4),
    fcf_cagr_5y=cagr(_fcf[2022], _fcf[2026], 4),
    net_debt_to_ebitda=(8.26e9 - 0.402e9) / 2.61e9,
    worst_yoy_revenue=worst_yoy(_rev),
    note="4년 CAGR(5개년 확보). 성장이 M&A 주도(Avast 2022, MoneyLion 2025) - "
         "BRO와 동일 유형이라 유기적 성장 분리검증 필수. 레버리지 3.01배로 높음.",
))

# ── NAVER (KRX) ──
_rev = {2021: 6817600e6, 2022: 8220079e6, 2023: 9670644e6, 2024: 10737719e6, 2025: 12035007e6}
_fcf = {2021: 625963e6, 2022: 752657e6, 2023: 1361610e6, 2024: 2035877e6, 2025: 1861057e6}
CANDIDATES.append(Candidate(
    ticker="035420.KS", name="NAVER", exchange="KRX",
    market_cap=31.05e12, fcf0=_fcf[2025],
    revenue_cagr_5y=cagr(_rev[2021], _rev[2025], 4),
    fcf_cagr_5y=cagr(_fcf[2021], _fcf[2025], 4),
    net_debt_to_ebitda=(5.31e12 - 8.96e12) / 3.01e12,
    worst_yoy_revenue=worst_yoy(_rev),
    note="순현금(-1.21배). ⚠️출처 내부 불일치: 통계페이지 P/FCF 20.28(=수익률 4.93%)과 "
         "FY2025 FCF 기준 5.99%가 다름(TTM 기준 차이 추정) - 정식 분석시 재확인 필요.",
))

# ── Cencora (NYSE, FY 9월결산) ──
_rev = {2021: 213989e6, 2022: 238587e6, 2023: 262173e6, 2024: 293959e6, 2025: 321333e6}
_fcf = {2021: 2228e6, 2022: 2207e6, 2023: 3453e6, 2024: 2998e6, 2025: 3207e6}
CANDIDATES.append(Candidate(
    ticker="COR", name="Cencora", exchange="NYSE",
    market_cap=60.29e9, fcf0=_fcf[2025],
    revenue_cagr_5y=cagr(_rev[2021], _rev[2025], 4),
    fcf_cagr_5y=cagr(_fcf[2021], _fcf[2025], 4),
    net_debt_to_ebitda=(15.09e9 - 2.18e9) / 3.84e9,
    worst_yoy_revenue=worst_yoy(_rev),
    note="⚠️출처 내부 불일치: 통계페이지 P/FCF 38.70인데 시총/FY2025 FCF는 18.8배 - "
         "FCF 정의 차이로 보이나 확정 못함. 통과폭이 얇아 이 불일치가 판정을 뒤집을 수 있음.",
))

# ── 이하 탈락군 (기록 보존: 왜 떨어졌는지가 기준의 판별력을 보여준다) ──

_fcf = {2020: 5353e6, 2021: 4889e6, 2022: 5107e6, 2023: 4220e6, 2024: 6767e6, 2025: 5564e6}
CANDIDATES.append(Candidate(
    ticker="PYPL", name="PayPal Holdings", exchange="NASDAQ",
    market_cap=49.53e9, fcf0=_fcf[2025],
    revenue_cagr_5y=0.0946, fcf_cagr_5y=cagr(_fcf[2020], _fcf[2025], 5),
    net_debt_to_ebitda=0.3250, worst_yoy_revenue=0.05,
    note="OCF/capex=Alpha Vantage, 시총/레버리지=FMP. 전형적 밸류트랩 - "
         "FCF수익률 11.2%로 매우 싸지만 FCF가 5년째 제자리.",
))

_rev = {2021: 560118e6, 2022: 554552e6, 2023: 609015e6, 2024: 660257e6, 2025: 751766e6}
_fcf = {2021: 145884e6, 2022: 123412e6, 2023: 200954e6, 2024: 195594e6, 2025: 215570e6}
CANDIDATES.append(Candidate(
    ticker="0700.HK", name="Tencent Holdings", exchange="HKEX",
    market_cap=3.65e12, fcf0=_fcf[2025],
    revenue_cagr_5y=cagr(_rev[2021], _rev[2025], 4),
    fcf_cagr_5y=cagr(_fcf[2021], _fcf[2025], 4),
    net_debt_to_ebitda=0.0, worst_yoy_revenue=worst_yoy(_rev),
    note="시총은 HKD434.60 x 약9.2B주의 CNY 환산 [추정치] - 성장조건에서 이미 "
         "탈락해 정밀화하지 않음. 아깝게 탈락(매출 7.63% vs 필요 8.90%).",
))

_fcf = {2021: 19889e6, 2022: 23404e6, 2023: 25682e6, 2024: 20705e6, 2025: 16075e6}
CANDIDATES.append(Candidate(
    ticker="UNH", name="UnitedHealth Group", exchange="NYSE",
    market_cap=300e9, fcf0=_fcf[2025],
    revenue_cagr_5y=0.10, fcf_cagr_5y=cagr(_fcf[2021], _fcf[2025], 4),
    net_debt_to_ebitda=1.0, worst_yoy_revenue=0.05,
    note="시총·레버리지는 미확보 [추정치] - FCF가 2023년 고점에서 37% 감소해 "
         "성장조건에서 명확히 탈락하므로 정밀화 불필요.",
))

_fcf = {2021: 812.45e6, 2022: 888.7e6, 2023: 655.37e6, 2024: 808.4e6, 2025: 687.4e6}
CANDIDATES.append(Candidate(
    ticker="OTEX", name="Open Text", exchange="NASDAQ/TSX",
    market_cap=6.0e9, fcf0=_fcf[2025],
    revenue_cagr_5y=0.05, fcf_cagr_5y=cagr(_fcf[2021], _fcf[2025], 4),
    net_debt_to_ebitda=3.0, worst_yoy_revenue=0.0,
    note="시총·레버리지 [추정치] - FCF가 5년간 감소해 성장조건 탈락이 확정적.",
))

_fcf = {2022: 282074e6, 2023: 300653e6, 2024: 445974e6, 2025: -6939e6, 2026: 262620e6}
CANDIDATES.append(Candidate(
    ticker="7974.T", name="Nintendo", exchange="TSE",
    market_cap=1.0e13, fcf0=_fcf[2026],
    revenue_cagr_5y=0.05, fcf_cagr_5y=cagr(_fcf[2022], _fcf[2026], 4),
    net_debt_to_ebitda=-3.0, worst_yoy_revenue=-0.20,
    note="시총 [추정치]. FY2025 FCF 적자(-69억엔) 등 콘솔 사이클로 변동성 극심.",
))

# SK Hynix: FCF CAGR 37%로 성장은 최상위권이나 FCF수익률 2.0~3.3%로 이미 비싸다.
CANDIDATES.append(Candidate(
    ticker="000660.KS", name="SK hynix", exchange="KRX",
    market_cap=1282.07e12, fcf0=25854202e6,
    revenue_cagr_5y=0.25, fcf_cagr_5y=cagr(7311013e6, 25854202e6, 4),
    net_debt_to_ebitda=(21.83e12 - 54.36e12) / 91.69e12,
    worst_yoy_revenue=-0.30,
    note="매출CAGR·최악YoY는 [추정치](메모리 사이클). FY2022~2023 FCF 연속 적자 이력. "
         "⚠️출처 내부 불일치: 시총/FY25FCF=49.6배 vs 통계페이지 P/FCF 30.68배.",
))

# 아래 2건은 최근년도 FCF가 음수라 모델 자체가 성립하지 않는다(Model N/A).
CANDIDATES.append(Candidate(
    ticker="9988.HK", name="Alibaba Group", exchange="HKEX",
    market_cap=2.0e12, fcf0=-49850e6,
    revenue_cagr_5y=0.06, fcf_cagr_5y=-0.30,
    net_debt_to_ebitda=-0.5, worst_yoy_revenue=0.0,
    note="FY2026(3월결산) FCF -498억CNY - AI 데이터센터 capex 급증(126,063 vs 전년 85,972).",
))
CANDIDATES.append(Candidate(
    ticker="3690.HK", name="Meituan", exchange="HKEX",
    market_cap=6.0e11, fcf0=-27086e6,
    revenue_cagr_5y=0.20, fcf_cagr_5y=-0.30,
    net_debt_to_ebitda=-1.0, worst_yoy_revenue=0.0,
    note="FY2025 OCF까지 적자 전환(-138억CNY) - 배달 경쟁 심화.",
))


def main():
    results = [(c, screen(c)) for c in CANDIDATES]
    passed = [(c, r) for c, r in results if r.passed]
    failed = [(c, r) for c, r in results if not r.passed]
    passed.sort(key=lambda x: -x[1].expectation_gap_est)

    print("=" * 108)
    print(f"매수관점 후보 스크리닝 결과 - {len(passed)}/{len(results)} 통과")
    print("=" * 108)
    for c, r in passed:
        print(f"\n[{r.tier}등급] {c.ticker:11} {c.name}  ({c.exchange})")
        print(f"   FCF수익률 {r.fcf_yield*100:5.2f}%  ->  내재성장률 추정 {r.implied_growth_est*100:+5.2f}%"
              f"   (DRS추정 {r.drs_est:.1f})")
        print(f"   매출CAGR {c.revenue_cagr_5y*100:5.2f}% / FCF CAGR {c.fcf_cagr_5y*100:6.2f}%"
              f"  ->  제약 {r.binding_cagr*100:.2f}%  ->  현실적성장률 추정 {r.realistic_growth_est*100:.2f}%")
        print(f"   ** Gap 추정 {r.expectation_gap_est*100:+.2f}%p **   순부채/EBITDA {c.net_debt_to_ebitda:.2f}배")
        if c.note:
            print(f"   ※ {c.note}")

    print("\n" + "=" * 108)
    print("탈락 (기준의 판별력 기록용)")
    print("=" * 108)
    for c, r in failed:
        print(f"  {c.ticker:11} {c.name:22} : {r.failures[0]}")

    print("\n" + "=" * 108)
    print("⚠️ 이 결과는 후보를 좁힌 1차 필터일 뿐 판정이 아니다.")
    print("   통과 종목은 반드시 engine/pipeline.py의 run_analysis()로 정식 분석할 것.")
    print("=" * 108)


if __name__ == "__main__":
    main()
