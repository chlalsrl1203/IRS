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

# ── 2차 배치 (같은 날 확장 실행) ──
# CNY 재무제표 기업은 시총이 USD(ADR)라 통화를 맞춰야 한다. 환율을 추정하지 않고
# 확인했다: USD/CNY = 6.7716 (2026-07-24, federalreserve.gov H.10 등 교차확인).
# 이 환율을 적용하니 stockanalysis 통계페이지의 P/FCF와 직접계산 FCF수익률이
# 거의 정확히 일치해(PDD 13.28% vs 13.39%, NTES 9.57% vs 9.91%) 데이터 정합성이
# 상호검증됐다. (처음에 7.15로 가정했을 때는 어긋났다 - 추정하지 말 것의 사례)
USDCNY = 6.7716

# ── PDD Holdings (NASDAQ ADR, CNY 재무제표) ──
_rev = {2021: 93950e6, 2022: 130558e6, 2023: 247639e6, 2024: 393836e6, 2025: 431846e6}
_fcf = {2021: 25496e6, 2022: 47872e6, 2023: 93579e6, 2024: 120962e6, 2025: 105794e6}
CANDIDATES.append(Candidate(
    ticker="PDD", name="PDD Holdings", exchange="NASDAQ(ADR)",
    market_cap=117.66e9, fcf0=_fcf[2025] / USDCNY,
    revenue_cagr_5y=cagr(_rev[2021], _rev[2025], 4),
    fcf_cagr_5y=cagr(_fcf[2021], _fcf[2025], 4),
    net_debt_to_ebitda=(0.7426e9 - 63.22e9) / 14.49e9,
    worst_yoy_revenue=worst_yoy(_rev),
    note="순현금 -4.31배(현금 632억달러). FY2025 FCF가 전년比 -12.5% 꺾인 점은 "
         "성장둔화 신호일 수 있음. 중국 규제·미중 통상 리스크는 DRS 경쟁강도/"
         "정성리스크로 별도 반영 필요(스크리너 미반영).",
))

# ── McKesson (NYSE, FY 3월결산) ──
_rev = {2022: 263966e6, 2023: 276711e6, 2024: 308951e6, 2025: 359051e6, 2026: 403430e6}
_fcf = {2022: 4046e6, 2023: 4769e6, 2024: 3883e6, 2025: 5548e6, 2026: 5719e6}
CANDIDATES.append(Candidate(
    ticker="MCK", name="McKesson", exchange="NYSE",
    market_cap=98.45e9, fcf0=_fcf[2026],
    revenue_cagr_5y=cagr(_rev[2022], _rev[2026], 4),
    fcf_cagr_5y=cagr(_fcf[2022], _fcf[2026], 4),
    net_debt_to_ebitda=(8.79e9 - 3.98e9) / 6.94e9,
    worst_yoy_revenue=worst_yoy(_rev),
    note="P/FCF 17.21과 직접계산 5.81%가 정확히 일치(데이터 정합성 양호). "
         "통과폭이 얇다(FCF CAGR 9.03% vs 필요 8.90%) - 의약품 유통 저마진 구조상 "
         "매출 CAGR보다 FCF CAGR이 제약이 되는 점 유의.",
))

# ── Progressive (NYSE) ──
_rev = {2021: 47702e6, 2022: 49611e6, 2023: 62109e6, 2024: 75372e6, 2025: 87671e6}
_fcf = {2021: 7518e6, 2022: 6557e6, 2023: 10391e6, 2024: 14834e6, 2025: 17200e6}
CANDIDATES.append(Candidate(
    ticker="PGR", name="Progressive", exchange="NYSE",
    market_cap=124.32e9, fcf0=_fcf[2025],
    revenue_cagr_5y=cagr(_rev[2021], _rev[2025], 4),
    fcf_cagr_5y=cagr(_fcf[2021], _fcf[2025], 4),
    net_debt_to_ebitda=(8.39e9 - 1.98e9) / 15.08e9,
    worst_yoy_revenue=worst_yoy(_rev),
    note="⚠️보험사 방법론 경고: 보험사 OCF는 보험료를 먼저 받고 보험금을 나중에 "
         "지급하는 float 증가분을 포함해 '주주에게 귀속되는 잉여현금'과 다르다. "
         "FCF수익률 13.84%가 과대평가일 수 있음. 단 ACGL(저평가, RAR 3.003)이 "
         "같은 업종에서 이미 분석된 선례가 있으므로 그 방법론과 대조할 것.",
))

# ── Trip.com (NASDAQ ADR, CNY 재무제표) ──
_rev = {2021: 20023e6, 2022: 20039e6, 2023: 44510e6, 2024: 53294e6, 2025: 62409e6}
_fcf = {2021: 1905e6, 2022: 2144e6, 2023: 21398e6, 2024: 19034e6, 2025: 13582e6}
CANDIDATES.append(Candidate(
    ticker="TCOM", name="Trip.com Group", exchange="NASDAQ(ADR)",
    market_cap=27.48e9, fcf0=_fcf[2025] / USDCNY,
    revenue_cagr_5y=cagr(_rev[2021], _rev[2025], 4),
    fcf_cagr_5y=cagr(_fcf[2021], _fcf[2025], 4),
    net_debt_to_ebitda=(4.55e9 - 11.75e9) / 2.39e9,
    worst_yoy_revenue=worst_yoy(_rev),
    note="⚠️기저 왜곡 심각: 2021~2022가 코로나로 짓눌린 해라 CAGR이 구조적으로 "
         "부풀려졌다(엔진 structural_discount_rate의 baseline_distorted_by_recovery "
         "플래그 대상). 게다가 FY2025 FCF가 전년比 -28.7%로 이미 꺾이는 중 - "
         "정식 분석시 회복기저를 제거한 재계산 필수.",
))

# ── 3차 배치 (유럽/일본/미국 추가 확장) ──

# ── Booking Holdings (NASDAQ) ──
_rev = {2021: 10958e6, 2022: 17090e6, 2023: 21365e6, 2024: 23739e6, 2025: 26917e6}
_fcf = {2021: 2516e6, 2022: 6186e6, 2023: 6999e6, 2024: 7894e6, 2025: 9087e6}
CANDIDATES.append(Candidate(
    ticker="BKNG", name="Booking Holdings", exchange="NASDAQ",
    market_cap=137.51e9, fcf0=_fcf[2025],
    revenue_cagr_5y=cagr(_rev[2021], _rev[2025], 4),
    fcf_cagr_5y=cagr(_fcf[2021], _fcf[2025], 4),
    net_debt_to_ebitda=(19.18e9 - 16.02e9) / 9.63e9,
    worst_yoy_revenue=worst_yoy(_rev),
    note="P/FCF 15.22와 직접계산 6.61% 일치(정합성 양호). ⚠️TCOM과 동일한 코로나 "
         "기저왜곡: 2021년이 짓눌린 해라 4년 CAGR이 부풀려졌다. 2022년 기준 3년 "
         "매출CAGR은 16.3%로 여전히 양호하나, 정식 분석시 baseline_distorted_by_"
         "recovery 플래그로 재계산할 것.",
))

# ── 4차 배치: capex 집약 업종 집중 탐색 (v3.20 배선 후) ──
# 기존 기준에서는 FCF CAGR만 보고 자동 탈락하던 영역이다. capex 시계열을 함께
# 넣어 '눌린 것'인지 '나빠지는 것'인지 구분한다.

# Alphabet: OCF는 CAGR 15.8%(91,652 -> 164,713)로 훌륭한데 FCF는 2.26%뿐.
# capex가 24,640 -> 91,447로 3.7배 폭증(AI 데이터센터)해 전부 흡수했다.
_rev = {2021: 257637e6, 2022: 282836e6, 2023: 307394e6, 2024: 350018e6, 2025: 402836e6}
_fcf = {2021: 67012e6, 2022: 60010e6, 2023: 69495e6, 2024: 72764e6, 2025: 73266e6}
_capex = {2021: 24640e6, 2022: 31485e6, 2023: 32251e6, 2024: 52535e6, 2025: 91447e6}
CANDIDATES.append(Candidate(
    ticker="GOOGL", name="Alphabet", exchange="NASDAQ",
    market_cap=3.91e12, fcf0=_fcf[2025],
    revenue_cagr_5y=cagr(_rev[2021], _rev[2025], 4),
    fcf_cagr_5y=cagr(_fcf[2021], _fcf[2025], 4),
    net_debt_to_ebitda=(120.79e9 - 242.47e9) / 173.16e9,
    worst_yoy_revenue=worst_yoy(_rev),
    capex_to_revenue_current=_capex[2025] / _rev[2025],
    capex_to_revenue_avg=sum(_capex[y] / _rev[y] for y in _rev) / len(_rev),
    note="NVO보다 극단적인 capex 억눌림 사례. 다만 FCF수익률 1.87%로 밸류에이션도 "
         "크게 미달이라 재분류만으로는 통과 불가 - 기존 트래커의 v3.11.1 판정"
         "(적정가/경계선)과 방향이 일치한다.",
))

# 캐나다국철: FCF가 4,080 -> 3,391로 감소(capex는 증가). FCF 자체가 줄어드는
# 유형이라 capex 재검토 플래그 대상이 아니다(가드가 작동하는지 확인용).
_fcf = {2021: 4080e6, 2022: 3917e6, 2023: 3778e6, 2024: 3150e6, 2025: 3391e6}
CANDIDATES.append(Candidate(
    ticker="CNR.TO", name="Canadian National Railway", exchange="TSX",
    market_cap=85e9, fcf0=_fcf[2025],
    revenue_cagr_5y=0.04, fcf_cagr_5y=cagr(_fcf[2021], _fcf[2025], 4),
    net_debt_to_ebitda=2.0, worst_yoy_revenue=0.0,
    note="시총·레버리지·매출CAGR [추정치] - FCF 감소로 탈락이 확정적이라 정밀화 "
         "불필요. capex 증가 중이지만 FCF CAGR이 음수라 재검토 플래그 미대상.",
))

# ── 이하 탈락군 (기록 보존: 왜 떨어졌는지가 기준의 판별력을 보여준다) ──

# QUALCOMM: FCF수익률 7.28%로 싼 편이고 FCF CAGR 10.3%도 통과하는데,
# 매출이 FY2022(442억)~FY2025(443억) 3년째 사실상 제자리라 매출 CAGR에서 탈락.
_rev = {2021: 33566e6, 2022: 44200e6, 2023: 35820e6, 2024: 38962e6, 2025: 44284e6}
_fcf = {2021: 8648e6, 2022: 6834e6, 2023: 9849e6, 2024: 11161e6, 2025: 12820e6}
CANDIDATES.append(Candidate(
    ticker="QCOM", name="QUALCOMM", exchange="NASDAQ",
    market_cap=175.99e9, fcf0=_fcf[2025],
    revenue_cagr_5y=cagr(_rev[2021], _rev[2025], 4),
    fcf_cagr_5y=cagr(_fcf[2021], _fcf[2025], 4),
    net_debt_to_ebitda=(15.27e9 - 9.80e9) / 12.93e9,
    worst_yoy_revenue=worst_yoy(_rev),
    note="P/FCF 14.08과 직접계산 7.28% 일치. FY2023 매출 -19.0% 역성장 이력도 "
         "있어(스마트폰 사이클) DRS cyclicality가 높게 나올 종목.",
))

# Recruit Holdings: FCF수익률 3.93%로 이미 비싸고, 매출 CAGR 6.51%도 미달 - 이중 탈락.
_rev = {2022: 2871705e6, 2023: 3429519e6, 2024: 3416492e6, 2025: 3557478e6, 2026: 3697351e6}
_fcf = {2022: 426477e6, 2023: 416168e6, 2024: 524225e6, 2025: 602412e6, 2026: 658729e6}
CANDIDATES.append(Candidate(
    ticker="6098.T", name="Recruit Holdings", exchange="TSE",
    market_cap=16.75e12, fcf0=_fcf[2026],
    revenue_cagr_5y=cagr(_rev[2022], _rev[2026], 4),
    fcf_cagr_5y=cagr(_fcf[2022], _fcf[2026], 4),
    net_debt_to_ebitda=(186.28e9 - 725.58e9) / 697.93e9,
    worst_yoy_revenue=worst_yoy(_rev),
    note="P/FCF 25.42와 직접계산 3.93% 정확히 일치(정합성 양호). 순현금이고 FCF "
         "CAGR 11.5%로 사업은 좋으나 밸류에이션·매출성장 양쪽에서 미달.",
))

# Novo Nordisk: OCF는 견조한데 capex가 5년새 6,335 -> 60,140백만DKK로 9.5배 폭증해
# FCF가 눌렸다. 엔진의 capex_intensity/growth_investment 분류(v3.6/v3.7, 현재
# pipeline 미배선)가 실제로 필요한 첫 사례 - CLAUDE.md '알려진 한계' 참고.
# Novo Nordisk: 재무제표 DKK, 시총 USD. 환율은 추정하지 않고 교차검증했다 -
# 통계페이지 P/FCF 23.49로 역산한 DKK/USD 6.414가 유로페그(7.46 DKK/EUR ÷
# 1.163 USD/EUR = 6.414)와 정확히 일치한다.
USDDKK = 6.414
_rev = {2021: 140800e6, 2022: 176954e6, 2023: 232261e6, 2024: 290403e6, 2025: 309064e6}
_fcf = {2021: 48665e6, 2022: 66741e6, 2023: 83102e6, 2024: 73804e6, 2025: 58962e6}
CANDIDATES.append(Candidate(
    ticker="NVO", name="Novo Nordisk", exchange="NYSE(ADR)/CPH",
    market_cap=215.94e9, fcf0=_fcf[2025] / USDDKK,
    revenue_cagr_5y=cagr(_rev[2021], _rev[2025], 4),
    fcf_cagr_5y=cagr(_fcf[2021], _fcf[2025], 4),
    net_debt_to_ebitda=(22.58e9 - 3.34e9) / 25.88e9,
    worst_yoy_revenue=worst_yoy(_rev),
    capex_to_revenue_current=60140e6 / 309064e6,
    capex_to_revenue_avg=sum(
        {2021: 6335e6, 2022: 12146e6, 2023: 25806e6, 2024: 47164e6, 2025: 60140e6}[y]
        / _rev[y] for y in _rev
    ) / len(_rev),
    note="매출 CAGR 21.7%로 성장은 최상위권인데 FCF CAGR은 4.92%뿐 - capex가 "
         "5년새 6,335 -> 60,140백만DKK로 9.5배 폭증(GLP-1 증설)해 FCF를 눌렀다. "
         "min() 제약이 정확히 작동한 사례이자, 엔진의 capex_intensity_from_series/"
         "fcf_conservatism_adjustment(v3.6/v3.7, 현재 pipeline 미배선)가 실제로 "
         "필요해지는 첫 실사례 - CLAUDE.md '알려진 한계' 항목 참고. "
         "'성장투자'로 분류되면 FCF CAGR을 상향조정해 판정이 바뀔 수 있다.",
))

# Cigna: FCF수익률 10.95%로 충분히 싼데 FCF CAGR 8.57%가 필요치 8.90%에 간발로 미달.
_rev = {2021: 174069e6, 2022: 180518e6, 2023: 195265e6, 2024: 247121e6, 2025: 274900e6}
_fcf = {2021: 6037e6, 2022: 7361e6, 2023: 10240e6, 2024: 8957e6, 2025: 8389e6}
CANDIDATES.append(Candidate(
    ticker="CI", name="The Cigna Group", exchange="NYSE",
    market_cap=76.60e9, fcf0=_fcf[2025],
    revenue_cagr_5y=cagr(_rev[2021], _rev[2025], 4),
    fcf_cagr_5y=cagr(_fcf[2021], _fcf[2025], 4),
    net_debt_to_ebitda=(30.90e9 - 7.85e9) / 12.34e9,
    worst_yoy_revenue=worst_yoy(_rev),
    capex_to_revenue_current=1212e6 / 274900e6,
    capex_to_revenue_avg=sum(
        {2021: 1154e6, 2022: 1295e6, 2023: 1573e6, 2024: 1406e6, 2025: 1212e6}[y]
        / _rev[y] for y in _rev
    ) / len(_rev),
    note="가장 아깝게 탈락한 종목. FCF수익률 10.95%(매우 쌈) + 매출 CAGR 12.1%인데 "
         "FCF CAGR 8.57%가 min() 제약이 되어 현실적성장률 7.71%로 기준(8.0%)에 "
         "0.29%p 부족. FY2023 정점 후 2년 연속 FCF 감소라 추세도 불리 - UNH(FCF "
         "-5.18%)와 같은 미국 건강보험 업종 압박이 공통 배경으로 보인다.",
))

# NetEase: FCF는 훌륭한데(CAGR 20.8%, 매우 안정적) 매출 CAGR 6.48%가 발목을 잡는다.
_rev = {2021: 87606e6, 2022: 96496e6, 2023: 103468e6, 2024: 105295e6, 2025: 112626e6}
_fcf = {2021: 23325e6, 2022: 25609e6, 2023: 33030e6, 2024: 38401e6, 2025: 49674e6}
CANDIDATES.append(Candidate(
    ticker="NTES", name="NetEase", exchange="NASDAQ(ADR)",
    market_cap=76.62e9, fcf0=_fcf[2025] / USDCNY,
    revenue_cagr_5y=cagr(_rev[2021], _rev[2025], 4),
    fcf_cagr_5y=cagr(_fcf[2021], _fcf[2025], 4),
    net_debt_to_ebitda=(1.59e9 - 24.78e9) / 5.94e9,
    worst_yoy_revenue=worst_yoy(_rev),
    note="아깝게 탈락. FCF수익률 9.57%(싸다) + FCF CAGR 20.8%(5년 단조증가로 "
         "매우 안정적)인데 매출 CAGR 6.48%가 min() 제약이 됐다. 기준을 "
         "'FCF CAGR 단독'으로 바꾸면 통과하지만, 그건 AJG/AZO/ELV를 걸러낸 "
         "min() 원칙 자체를 훼손하므로 바꾸지 않는다.",
))

_fcf = {2020: 5353e6, 2021: 4889e6, 2022: 5107e6, 2023: 4220e6, 2024: 6767e6, 2025: 5564e6}
CANDIDATES.append(Candidate(
    ticker="PYPL", name="PayPal Holdings", exchange="NASDAQ",
    market_cap=49.53e9, fcf0=_fcf[2025],
    revenue_cagr_5y=0.0946, fcf_cagr_5y=cagr(_fcf[2020], _fcf[2025], 5),
    net_debt_to_ebitda=0.3250, worst_yoy_revenue=0.05,
    capex_to_revenue_current=852e6 / 33734e6,
    capex_to_revenue_avg=sum(
        c / r for c, r in [
            (866e6, 21454e6), (908e6, 25371e6), (706e6, 27518e6),
            (623e6, 29771e6), (683e6, 31797e6), (852e6, 33734e6),
        ]
    ) / 6,
    note="OCF/capex=Alpha Vantage, 시총/레버리지=FMP. 전형적 밸류트랩 - "
         "FCF수익률 11.2%로 매우 싸지만 FCF가 5년째 제자리. capex는 오히려 "
         "감소중(2.83%->2.53%)이라 capex 억눌림이 아님이 확인됨.",
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
        # 탈락 사유를 전부 표시한다. 첫 줄만 보여주면 어떤 조건이 진짜 결정적이었는지
        # 오해할 수 있다(NVO를 임시 시총값으로 돌렸을 때 실제로 그 혼동이 발생했다).
        print(f"  {c.ticker:11} {c.name:22} : {r.failures[0]}")
        for extra in r.failures[1:]:
            print(f"  {'':11} {'':22}   + {extra}")

    review = [(c, r) for c, r in results if r.review_flags]
    if review:
        print("\n" + "=" * 108)
        print("🔍 capex 재검토 대상 (탈락했으나 분류에 따라 판정이 바뀔 수 있음)")
        print("=" * 108)
        for c, r in review:
            print(f"\n  {c.ticker:11} {c.name}")
            for f in r.review_flags:
                print(f"      {f}")

    print("\n" + "=" * 108)
    print("⚠️ 이 결과는 후보를 좁힌 1차 필터일 뿐 판정이 아니다.")
    print("   통과 종목은 반드시 engine/pipeline.py의 run_analysis()로 정식 분석할 것.")
    print("=" * 108)


if __name__ == "__main__":
    main()
