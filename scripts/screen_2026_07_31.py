"""
2026-07-31/08-01 매수관점 후보 스크리닝 (screener.py 4분류 체크리스트 적용).

기준·방법론은 engine/screener.py docstring 참고. 이 스크립트를 남기는
이유는 scripts/screen_2026_07_26.py와 동일 - 스크리닝 결과만 남기고
입력값이 사라지면 큐22(Cadence) 사고가 반복된다.

이 배치의 특징: 이전 배치(07-26)가 "저평가 후보를 찾자"는 열린 탐색이었다면,
이번엔 실제 급락 종목(52주 저점/YoY 대폭 하락)만 먼저 WebSearch로 확인한
뒤 재무데이터를 긁는 순서로 진행했다 - 앞선 시행착오(주가를 확인 안 하고
"어려울 것 같은 업종"을 추정만으로 후보에 넣었다가 절반이 오히려 YoY
상승 종목이었던 사고, CHANGELOG 참고)에서 얻은 교훈.

원자료 출처: stockanalysis.com (2026-07-31~08-01 조회). 시총/주가는 조회
시점 스냅샷이라 이후 변동 가능 - 재확인 없이 그대로 재사용하지 말 것.

실행: python3 scripts/screen_2026_07_31.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.screener import Candidate, screen_all, format_table


def cagr(s, e, y):
    return (e / s) ** (1 / y) - 1


def worst_yoy(series):
    ys = sorted(series)
    return min(series[ys[i]] / series[ys[i - 1]] - 1 for i in range(1, len(ys)))


CANDIDATES = []

# ── 1차 배치: SE 발굴 과정에서 함께 훑음 ──
_rev = {2022: 20.58e9, 2023: 24.38e9, 2024: 30.27e9, 2025: 34.53e9}
_fcf = {2022: -259e6, 2023: 1756e6, 2024: 1007e6, 2025: 522e6}
CANDIDATES.append(Candidate(
    ticker="CPNG", name="Coupang", exchange="NYSE",
    market_cap=27.72e9, fcf0=_fcf[2025],
    revenue_cagr_5y=cagr(_rev[2022], _rev[2025], 3), fcf_cagr_5y=cagr(1756e6, 522e6, 2),
    net_debt_to_ebitda=-1.0, worst_yoy_revenue=0.20,
    note="FCF가 FY2023 $1.76B 정점 찍고 2년 연속 감소(FY24 $1.01B->FY25 $0.52B) - "
         "탈락(SE는 반대로 FCF가 계속 가속 중이라 대비됨).",
))

_rev = {2021: 951592e6, 2022: 1046236e6, 2023: 1084662e6, 2024: 1158819e6, 2025: 1257678e6}
_fcf = {2021: 20046e6, 2022: 34906e6, 2023: 39506e6, 2024: 44276e6, 2025: 4807e6}
CANDIDATES.append(Candidate(
    ticker="JD", name="JD.com", exchange="NASDAQ(ADR)",
    market_cap=45e9, fcf0=_fcf[2025] / 6.7716,
    revenue_cagr_5y=cagr(_rev[2021], _rev[2025], 4), fcf_cagr_5y=cagr(_fcf[2022], _fcf[2025], 3),
    net_debt_to_ebitda=-1.0, worst_yoy_revenue=0.03,
    note="FY2025 FCF가 전년比 -89% 붕괴($44.3B->$4.8B, 위안화) - 인스턴트리테일/"
         "배달 경쟁 심화로 인한 투자확대(Alibaba/Meituan과 동일 패턴 원인 추정). 탈락.",
))

# ── 2차 배치: 헬스케어/의료기기 급락군 (RMD 발굴) ──
_rev = {2021: 4194e6, 2022: 4718e6, 2023: 4982e6, 2024: 5341e6, 2025: 5195e6}
_ocf = {2021: 515.5e6, 2022: 302.3e6, 2023: 736.2e6, 2024: 945.7e6, 2025: 757.6e6}
_capex = {2021: 106.8e6, 2022: 101.1e6, 2023: 250.2e6, 2024: 163.6e6, 2025: 118.8e6}
_fcf = {y: _ocf[y] - _capex[y] for y in _rev}
CANDIDATES.append(Candidate(
    ticker="LII", name="Lennox International", exchange="NYSE",
    market_cap=14.43e9, fcf0=_fcf[2025],
    revenue_cagr_5y=cagr(_rev[2021], _rev[2025], 4), fcf_cagr_5y=cagr(_fcf[2021], _fcf[2025], 4),
    net_debt_to_ebitda=1.5, worst_yoy_revenue=worst_yoy(_rev),
    note="최근 2년 매출 역성장(-2.7%) - 진짜 둔화. 탈락.",
))

_rev = {2021: 2449e6, 2022: 2910e6, 2023: 3622e6, 2024: 4033e6, 2025: 4662e6}
_ocf = {2021: 442.5e6, 2022: 669.5e6, 2023: 748.5e6, 2024: 989.5e6, 2025: 1441e6}
_capex = {2021: 389.2e6, 2022: 364.8e6, 2023: 236.6e6, 2024: 358.8e6, 2025: 363.5e6}
_fcf = {y: _ocf[y] - _capex[y] for y in _rev}
CANDIDATES.append(Candidate(
    ticker="DXCM", name="Dexcom", exchange="NASDAQ",
    market_cap=28.76e9, fcf0=_fcf[2025],
    revenue_cagr_5y=cagr(_rev[2021], _rev[2025], 4), fcf_cagr_5y=cagr(_fcf[2021], _fcf[2025], 4),
    net_debt_to_ebitda=-0.5, worst_yoy_revenue=worst_yoy(_rev),
    note="성장은 견조하나(매출CAGR 17.5%) FCF수익률 3.75%로 여전히 비쌈 - 밸류에이션 탈락.",
))

_rev = {2021: 17108e6, 2022: 18449e6, 2023: 20498e6, 2024: 22595e6, 2025: 25116e6}
_ocf = {2021: 3263e6, 2022: 2624e6, 2023: 3711e6, 2024: 4242e6, 2025: 5044e6}
_capex = {2021: 525e6, 2022: 588e6, 2023: 575e6, 2024: 755e6, 2025: 761e6}
_fcf = {y: _ocf[y] - _capex[y] for y in _rev}
CANDIDATES.append(Candidate(
    ticker="SYK", name="Stryker", exchange="NYSE",
    market_cap=133.42e9, fcf0=_fcf[2025],
    revenue_cagr_5y=cagr(_rev[2021], _rev[2025], 4), fcf_cagr_5y=cagr(_fcf[2021], _fcf[2025], 4),
    net_debt_to_ebitda=2.3, worst_yoy_revenue=worst_yoy(_rev),
    note="FCF수익률 3.21%로 밸류에이션 탈락.",
))

_rev = {2022: 4223e6, 2023: 4536e6, 2024: 5139e6, 2025: 5460e6, 2026: 5936e6}
_ocf = {2022: 684.81e6, 2023: 756.95e6, 2024: 973.3e6, 2025: 1148e6, 2026: 1341e6}
_capex = {2022: 287.56e6, 2023: 361.97e6, 2024: 360.3e6, 2025: 370.1e6, 2026: 369e6}
_fcf = {y: _ocf[y] - _capex[y] for y in _rev}
CANDIDATES.append(Candidate(
    ticker="STE", name="STERIS", exchange="NYSE",
    market_cap=22.53e9, fcf0=_fcf[2026],
    revenue_cagr_5y=cagr(_rev[2022], _rev[2026], 4), fcf_cagr_5y=cagr(_fcf[2022], _fcf[2026], 4),
    net_debt_to_ebitda=1.5, worst_yoy_revenue=worst_yoy(_rev),
    note="현실적성장률 7.99% - 기준(8.0%)에 0.01%p 근소 미달. 가장 아깝게 탈락.",
))

_rev = {2021: 2424e6, 2022: 2696e6, 2023: 3073e6, 2024: 3389e6, 2025: 3761e6}
_ocf = {2021: 401.81e6, 2022: 465.93e6, 2023: 528.37e6, 2024: 607.65e6, 2025: 678.11e6}
_capex = {2021: 27.19e6, 2022: 30.63e6, 2023: 32.47e6, 2024: 27.57e6, 2025: 28.09e6}
_fcf = {y: _ocf[y] - _capex[y] for y in _rev}
CANDIDATES.append(Candidate(
    ticker="ROL", name="Rollins", exchange="NYSE",
    market_cap=18.45e9, fcf0=_fcf[2025],
    revenue_cagr_5y=cagr(_rev[2021], _rev[2025], 4), fcf_cagr_5y=cagr(_fcf[2021], _fcf[2025], 4),
    net_debt_to_ebitda=1.4, worst_yoy_revenue=worst_yoy(_rev),
    note="성장·안정성 모두 양호하나 FCF수익률 3.52%로 밸류에이션 탈락. YoY -33.5%인데도 안 쌈.",
))

_rev = {2021: 2832e6, 2022: 2887e6, 2023: 2950e6, 2024: 2893e6, 2025: 3074e6}
_ocf = {2021: 584e6, 2022: 724e6, 2023: 776.5e6, 2024: 653.4e6, 2025: 754.8e6}
_capex = {2021: 253.4e6, 2022: 284.6e6, 2023: 362e6, 2024: 377e6, 2025: 285.9e6}
_fcf = {y: _ocf[y] - _capex[y] for y in _rev}
CANDIDATES.append(Candidate(
    ticker="WST", name="West Pharmaceutical", exchange="NYSE",
    market_cap=15e9, fcf0=_fcf[2025],
    revenue_cagr_5y=cagr(_rev[2021], _rev[2025], 4), fcf_cagr_5y=cagr(_fcf[2021], _fcf[2025], 4),
    net_debt_to_ebitda=0.5, worst_yoy_revenue=worst_yoy(_rev),
    note="FY22~24 매출 사실상 정체(2887->2893) - 매출성장 탈락(공식 큐 50번, 아직 정식분석 전).",
))

_rev = {2021: 6257e6, 2022: 8111e6, 2023: 9619e6, 2024: 10588e6, 2025: 11103e6}
_ocf = {2021: 1389e6, 2022: 966.46e6, 2023: 2296e6, 2024: 2273e6, 2025: 1602e6}
_capex = {2021: 394.5e6, 2022: 638.66e6, 2023: 651.87e6, 2024: 689.23e6, 2025: 680.8e6}
_fcf = {y: _ocf[y] - _capex[y] for y in _rev}
CANDIDATES.append(Candidate(
    ticker="LULU", name="Lululemon", exchange="NASDAQ",
    market_cap=15e9, fcf0=_fcf[2025],
    revenue_cagr_5y=cagr(_rev[2021], _rev[2025], 4), fcf_cagr_5y=cagr(_fcf[2021], _fcf[2025], 4),
    net_debt_to_ebitda=0.0, worst_yoy_revenue=worst_yoy(_rev),
    note="매출성장 42%->4%대로 급격 둔화, FCF도 최근 감소(1644->922) - 진짜 나빠짐. 탈락.",
))

# ── 3차 배치: 소비재/미디어/항공/HVAC (대부분 실제로는 YoY 상승 - 교훈용) ──
_rev = {2021: 16214e6, 2022: 17737e6, 2023: 15910e6, 2024: 15607e6, 2025: 14631e6}
_ocf = {2021: 3631e6, 2022: 3040e6, 2023: 1731e6, 2024: 2360e6, 2025: 1272e6}
_capex = {2021: 637e6, 2022: 1040e6, 2023: 1003e6, 2024: 919e6, 2025: 602e6}
_fcf = {y: _ocf[y] - _capex[y] for y in _rev}
CANDIDATES.append(Candidate(
    ticker="EL", name="Estee Lauder", exchange="NYSE",
    market_cap=30.71e9, fcf0=_fcf[2025],
    revenue_cagr_5y=cagr(_rev[2021], _rev[2025], 4), fcf_cagr_5y=cagr(_fcf[2021], _fcf[2025], 4),
    net_debt_to_ebitda=2.0, worst_yoy_revenue=worst_yoy(_rev),
    note="FCF FY21 $2.99B -> FY25 $0.67B로 급감(중국/면세 부진). 매출도 역성장 중. 탈락.",
))

_rev = {2021: 2329e6, 2022: 2566e6, 2023: 2748e6, 2024: 2808e6, 2025: 2884e6}
_ocf = {2021: 651.55e6, 2022: 683.61e6, 2023: 705.51e6, 2024: 752.47e6, 2025: 693.41e6}
_capex = {2021: 11.25e6, 2022: 10.24e6, 2023: 12.95e6, 2024: 14.21e6, 2025: 15.39e6}
_fcf = {y: _ocf[y] - _capex[y] for y in _rev}
CANDIDATES.append(Candidate(
    ticker="ETSY", name="Etsy", exchange="NASDAQ",
    market_cap=7.89e9, fcf0=_fcf[2025],
    revenue_cagr_5y=cagr(_rev[2021], _rev[2025], 4), fcf_cagr_5y=cagr(_fcf[2021], _fcf[2025], 4),
    net_debt_to_ebitda=1.5, worst_yoy_revenue=worst_yoy(_rev),
    note="매출 정체(3%대 성장) - 저성장 탈락.",
))

_rev = {2022: 4100e6, 2023: 4393e6, 2024: 4527e6, 2025: 4665e6, 2026: 4869e6}
_ocf = {2022: 1605e6, 2023: 1290e6, 2024: 1599e6, 2025: 1945e6, 2026: 1989e6}
_capex = {2022: 132.59e6, 2023: 103.83e6, 2024: 126.95e6, 2025: 136.56e6, 2026: 64.96e6}
_fcf = {y: _ocf[y] - _capex[y] for y in _rev}
CANDIDATES.append(Candidate(
    ticker="ZM", name="Zoom", exchange="NASDAQ",
    market_cap=27.07e9, fcf0=_fcf[2026],
    revenue_cagr_5y=cagr(_rev[2022], _rev[2026], 4), fcf_cagr_5y=cagr(_fcf[2022], _fcf[2026], 4),
    net_debt_to_ebitda=-1.5, worst_yoy_revenue=worst_yoy(_rev),
    note="매출성장 4~5%대 정체 - 저성장 탈락.",
))

_rev = {2021: 51682e6, 2022: 54022e6, 2023: 54607e6, 2024: 55085e6, 2025: 54774e6}
_ocf = {2021: 16239e6, 2022: 14925e6, 2023: 14433e6, 2024: 14430e6, 2025: 16077e6}
_capex = {2021: 7635e6, 2022: 9376e6, 2023: 11115e6, 2024: 11269e6, 2025: 11659e6}
_fcf = {y: _ocf[y] - _capex[y] for y in _rev}
CANDIDATES.append(Candidate(
    ticker="CHTR", name="Charter Communications", exchange="NASDAQ",
    market_cap=19.14e9, fcf0=_fcf[2025],
    revenue_cagr_5y=cagr(_rev[2021], _rev[2025], 4), fcf_cagr_5y=cagr(_fcf[2021], _fcf[2025], 4),
    net_debt_to_ebitda=4.0, worst_yoy_revenue=worst_yoy(_rev),
    note="YoY 주가 -53%로 이 배치 최대낙폭이지만 FCF -49%(망투자 capex 급증)/매출 정체 - "
         "전형적 밸류트랩(PYPL 선례와 동일 유형). 탈락.",
))

_rev = {2022: 34220e6, 2023: 37845e6, 2024: 38692e6, 2025: 40612e6, 2026: 42724e6}
_ocf = {2022: 2866e6, 2023: 1985e6, 2024: 2392e6, 2025: 2996e6, 2026: 3635e6}
_capex = {2022: 1070e6, 2023: 1561e6, 2024: 1700e6, 2025: 1310e6, 2026: 1241e6}
_fcf = {y: _ocf[y] - _capex[y] for y in _rev}
CANDIDATES.append(Candidate(
    ticker="DG", name="Dollar General", exchange="NYSE",
    market_cap=28.12e9, fcf0=_fcf[2026],
    revenue_cagr_5y=cagr(_rev[2022], _rev[2026], 4), fcf_cagr_5y=cagr(_fcf[2022], _fcf[2026], 4),
    net_debt_to_ebitda=2.5, worst_yoy_revenue=worst_yoy(_rev),
    note="FCF는 저점(FY23) 회복 중이나 매출성장 5%대로 저성장 탈락.",
))

_rev = {2022: 8821e6, 2023: 9453e6, 2024: 9962e6, 2025: 10209e6, 2026: 9139e6}
_ocf = {2022: 2705e6, 2023: 2757e6, 2024: 2780e6, 2025: 3152e6, 2026: 2669e6}
_capex = {2022: 1027e6, 2023: 1035e6, 2024: 1269e6, 2025: 1214e6, 2026: 875e6}
_fcf = {y: _ocf[y] - _capex[y] for y in _rev}
CANDIDATES.append(Candidate(
    ticker="STZ", name="Constellation Brands", exchange="NYSE",
    market_cap=22.26e9, fcf0=_fcf[2026],
    revenue_cagr_5y=cagr(_rev[2022], _rev[2026], 4), fcf_cagr_5y=cagr(_fcf[2022], _fcf[2026], 4),
    net_debt_to_ebitda=3.0, worst_yoy_revenue=worst_yoy(_rev),
    note="FY26 매출 -9.99%(와인/증류주 매각+주류소비 위축) - 역성장 탈락.",
))

_rev = {2021: 67418e6, 2022: 82722e6, 2023: 88898e6, 2024: 91361e6, 2025: 94425e6}
_ocf = {2021: 5566e6, 2022: 6002e6, 2023: 9866e6, 2024: 13971e6, 2025: 18101e6}
_capex = {2021: 3578e6, 2022: 4943e6, 2023: 4969e6, 2024: 5412e6, 2025: 8024e6}
_fcf = {y: _ocf[y] - _capex[y] for y in _rev}
CANDIDATES.append(Candidate(
    ticker="DIS", name="Disney", exchange="NYSE",
    market_cap=166.98e9, fcf0=_fcf[2025],
    revenue_cagr_5y=cagr(_rev[2021], _rev[2025], 4), fcf_cagr_5y=cagr(_fcf[2021], _fcf[2025], 4),
    net_debt_to_ebitda=1.5, worst_yoy_revenue=worst_yoy(_rev),
    note="⚠️FY21이 팬데믹 저점(파크폐쇄)이라 CAGR이 왜곡돼 있다(BKNG 선례와 동일 유형) - "
         "현실적성장률 7.90%로 기준(8.0%)에 근소 미달, 정상화하면 실제로는 더 낮을 가능성.",
))

_rev = {2021: 97287e6, 2022: 100338e6, 2023: 91039e6, 2024: 91070e6, 2025: 89150e6}
_ocf = {2021: 15007e6, 2022: 14104e6, 2023: 10238e6, 2024: 10122e6, 2025: 8450e6}
_capex = {2021: 4194e6, 2022: 4769e6, 2023: 5158e6, 2024: 3909e6, 2025: 3685e6}
_fcf = {y: _ocf[y] - _capex[y] for y in _rev}
CANDIDATES.append(Candidate(
    ticker="UPS", name="UPS", exchange="NYSE",
    market_cap=89.48e9, fcf0=_fcf[2025],
    revenue_cagr_5y=cagr(_rev[2021], _rev[2025], 4), fcf_cagr_5y=cagr(_fcf[2021], _fcf[2025], 4),
    net_debt_to_ebitda=2.5, worst_yoy_revenue=worst_yoy(_rev),
    note="매출·FCF 둘다 감소추세(아마존 물량축소, 인건비상승) - 진짜 나빠짐. 탈락.",
))

# ── 4차 배치: 반도체/중국테크 (대부분 구조적 감소 또는 FCF 적자) ──
_rev = {2021: 27705e6, 2022: 30758e6, 2023: 15540e6, 2024: 25111e6, 2025: 37378e6}
_fcf = {2021: 2438e6, 2022: 3114e6, 2023: -6117e6, 2024: 121e6, 2025: 1668e6}
CANDIDATES.append(Candidate(
    ticker="MU", name="Micron", exchange="NASDAQ",
    market_cap=180e9, fcf0=_fcf[2025],
    revenue_cagr_5y=cagr(_rev[2021], _rev[2025], 4), fcf_cagr_5y=cagr(2438e6, 1668e6, 4),
    net_debt_to_ebitda=0.5, worst_yoy_revenue=worst_yoy(_rev),
    note="⚠️AI HBM 수퍼사이클로 TTM매출이 FY25의 2.4배(연간창이 못 따라감)로 보였으나, "
         "확인 결과 연초대비(YTD) +197% 폭등 후 조정 중인 종목 - '싸다'가 아니라 "
         "'많이 올랐다가 일부 되돌림'. SanDisk도 동일유형(YTD+471%). 후보 아님.",
))

_rev = {2021: 6740e6, 2022: 8326e6, 2023: 8253e6, 2024: 7082e6, 2025: 5995e6}
CANDIDATES.append(Candidate(
    ticker="ON", name="ON Semiconductor", exchange="NASDAQ",
    market_cap=20e9, fcf0=1418.8e6,
    revenue_cagr_5y=cagr(_rev[2021], _rev[2025], 4), fcf_cagr_5y=0.05,
    net_debt_to_ebitda=0.0, worst_yoy_revenue=worst_yoy(_rev),
    note="매출 구조적 감소(자동차/산업용 반도체 수요둔화) - 역성장 탈락.",
))

_rev = {2022: 4646e6, 2023: 3569e6, 2024: 3770e6, 2025: 3719e6, 2026: 3645e6}
CANDIDATES.append(Candidate(
    ticker="QRVO", name="Qorvo", exchange="NASDAQ",
    market_cap=8e9, fcf0=679.56e6,
    revenue_cagr_5y=cagr(_rev[2022], _rev[2026], 4), fcf_cagr_5y=0.0,
    net_debt_to_ebitda=1.0, worst_yoy_revenue=worst_yoy(_rev),
    note="매출 정체/감소(핸드셋 칩 점유율 잠식) - 탈락.",
))

_rev = {2021: 5109e6, 2022: 5486e6, 2023: 4772e6, 2024: 4178e6, 2025: 4087e6}
CANDIDATES.append(Candidate(
    ticker="SWKS", name="Skyworks Solutions", exchange="NASDAQ",
    market_cap=12e9, fcf0=1106e6,
    revenue_cagr_5y=cagr(_rev[2021], _rev[2025], 4), fcf_cagr_5y=-0.05,
    net_debt_to_ebitda=0.5, worst_yoy_revenue=worst_yoy(_rev),
    note="매출 감소세(Apple 의존도 高, 점유율 잠식) - 탈락.",
))

_rev = {2021: 18344e6, 2022: 20028e6, 2023: 17519e6, 2024: 15641e6, 2025: 17682e6}
CANDIDATES.append(Candidate(
    ticker="TXN", name="Texas Instruments", exchange="NASDAQ",
    market_cap=150e9, fcf0=2603e6,
    revenue_cagr_5y=cagr(_rev[2021], _rev[2025], 4), fcf_cagr_5y=-0.15,
    net_debt_to_ebitda=1.0, worst_yoy_revenue=worst_yoy(_rev),
    note="FCF가 대규모 신규 팹투자로 눌려있으나(NVO 패턴처럼 보일 수 있음) 매출 자체가 "
         "FY21 대비 정체(CAGR 거의 0%) - NVO와 달리 매출성장이 없어 capex 재분류로도 "
         "구제 안 됨. 탈락.",
))

_rev = {2021: 124493e6, 2022: 123675e6, 2023: 134598e6, 2024: 133125e6, 2025: 129079e6}
_fcf = {2025: -3013e6 - 12073e6}
CANDIDATES.append(Candidate(
    ticker="BIDU", name="Baidu", exchange="NASDAQ(ADR)",
    market_cap=35e9, fcf0=_fcf[2025],
    revenue_cagr_5y=cagr(_rev[2021], _rev[2025], 4), fcf_cagr_5y=-0.3,
    net_debt_to_ebitda=-0.5, worst_yoy_revenue=worst_yoy(_rev),
    note="매출 정체(~1%)+FY25 OCF 마이너스 전환 - Model N/A + 저성장 이중 탈락.",
))

_rev = {2021: 27010e6, 2022: 45287e6, 2023: 123851e6, 2024: 144460e6, 2025: 112313e6}
CANDIDATES.append(Candidate(
    ticker="LI", name="Li Auto", exchange="NASDAQ(ADR)",
    market_cap=15e9, fcf0=-8611e6 - 4206e6,
    revenue_cagr_5y=cagr(_rev[2021], _rev[2025], 4), fcf_cagr_5y=-0.3,
    net_debt_to_ebitda=-0.5, worst_yoy_revenue=worst_yoy(_rev),
    note="FY25 매출 -22%(중국 EV 수요둔화+경쟁심화), FCF도 마이너스 전환 - Model N/A.",
))

_rev = {2022: 46710e6, 2023: 51217e6, 2024: 51362e6, 2025: 46309e6, 2026: 46398e6}
CANDIDATES.append(Candidate(
    ticker="NKE", name="Nike", exchange="NYSE",
    market_cap=110e9, fcf0=2184e6,
    revenue_cagr_5y=cagr(_rev[2022], _rev[2026], 4), fcf_cagr_5y=-0.2,
    net_debt_to_ebitda=0.5, worst_yoy_revenue=worst_yoy(_rev),
    note="매출 정체+FCF 급감(6617->2184, 2년간 -67%) - 진짜 나빠짐(재고과잉/DTC축소/"
         "On·Hoka 경쟁). 탈락.",
))

_rev = {2021: 106005e6, 2022: 109120e6, 2023: 107412e6, 2024: 106566e6, 2025: 104780e6}
CANDIDATES.append(Candidate(
    ticker="TGT", name="Target", exchange="NYSE",
    market_cap=42e9, fcf0=2835e6,
    revenue_cagr_5y=cagr(_rev[2021], _rev[2025], 4), fcf_cagr_5y=-0.1,
    net_debt_to_ebitda=1.5, worst_yoy_revenue=worst_yoy(_rev),
    note="매출 정체/소폭역성장, FCF도 변동성 크고 최근 감소 - 탈락.",
))

# ── 5차 배치: 실제 52주 저점 확인 종목(Trefis) ──
_rev = {2021: 57350e6, 2022: 60530e6, 2023: 61860e6, 2024: 62753e6, 2025: 67535e6}
_fcf = {2021: 10734e6, 2025: 12102e6}
CANDIDATES.append(Candidate(
    ticker="IBM", name="IBM", exchange="NYSE",
    market_cap=208.91e9, fcf0=_fcf[2025],
    revenue_cagr_5y=cagr(_rev[2021], _rev[2025], 4), fcf_cagr_5y=cagr(_fcf[2021], _fcf[2025], 4),
    net_debt_to_ebitda=1.0, worst_yoy_revenue=worst_yoy(_rev),
    note="YoY -14.8%(2026-07-14 실적쇼크 -25% 단일일 하락 포함)이나 매출성장 4%대로 "
         "저성장 탈락.",
))

# ⚠️ 이 딕셔너리를 처음 작성할 때 실수로 DUOL 데이터를 그대로 복붙했었다(발견 즉시
# 정정) - PODD 실제 원자료(SEC 10-K 계열 스크레이핑, FY2021~2025)로 교체.
_rev = {2021: 1099e6, 2022: 1305e6, 2023: 1697e6, 2024: 2072e6, 2025: 2708e6}
_ocf = {2021: -68.1e6, 2022: 119e6, 2023: 145.7e6, 2024: 430.2e6, 2025: 569.3e6}
_capex = {2021: 111.9e6, 2022: 122.9e6, 2023: 75.6e6, 2024: 124.9e6, 2025: 191.6e6}
_fcf = {y: _ocf[y] - _capex[y] for y in _rev}
CANDIDATES.append(Candidate(
    ticker="PODD", name="Insulet", exchange="NASDAQ",
    market_cap=11.48e9, fcf0=_fcf[2025],
    revenue_cagr_5y=cagr(_rev[2021], _rev[2025], 4), fcf_cagr_5y=cagr(_fcf[2023], _fcf[2025], 2),
    net_debt_to_ebitda=0.5, worst_yoy_revenue=worst_yoy(_rev),
    note="YoY -44.2%인데 매출은 +31.9%(가속 중)로 이 배치 최고 성장주. 그런데도 "
         "FCF수익률 3.29%로 여전히 안 쌈(내재성장률 요구 6.99%>기준5.5%). "
         "PODD/CMG/DXCM/ROL/SYK 공통 - '떨어져도 안 싸다' 유형.",
))

# ── 6차 배치: Chewy/Zscaler (DUOL 발굴 과정) ──
_rev = {2021: 8967e6, 2022: 10119e6, 2023: 11148e6, 2024: 11861e6, 2025: 12602e6}
_ocf = {2021: 191.74e6, 2022: 349.78e6, 2023: 486.2e6, 2024: 596.3e6, 2025: 691.6e6}
_capex = {2021: 183.19e6, 2022: 230.31e6, 2023: 143.3e6, 2024: 143.8e6, 2025: 129.2e6}
_fcf = {y: _ocf[y] - _capex[y] for y in _rev}
CANDIDATES.append(Candidate(
    ticker="CHWY", name="Chewy", exchange="NYSE",
    market_cap=9.34e9, fcf0=_fcf[2025],
    revenue_cagr_5y=cagr(_rev[2021], _rev[2025], 4), fcf_cagr_5y=cagr(_fcf[2022], _fcf[2025], 3),
    net_debt_to_ebitda=-3.0, worst_yoy_revenue=worst_yoy(_rev),
    note="매출성장 25%->6%대로 뚜렷한 둔화 - 현실적성장률 7.98%로 기준(8.0%) 근소 미달.",
))

_rev = {2021: 673.1e6, 2022: 1091e6, 2023: 1617e6, 2024: 2168e6, 2025: 2673e6}
_ocf = {2021: 202.04e6, 2022: 321.91e6, 2023: 462.34e6, 2024: 779.85e6, 2025: 972.45e6}
_capex = {2021: 48.17e6, 2022: 69.3e6, 2023: 97.2e6, 2024: 144.59e6, 2025: 164.25e6}
_fcf = {y: _ocf[y] - _capex[y] for y in _rev}
CANDIDATES.append(Candidate(
    ticker="ZS", name="Zscaler", exchange="NASDAQ",
    market_cap=24.00e9, fcf0=_fcf[2025],
    revenue_cagr_5y=cagr(_rev[2021], _rev[2025], 4), fcf_cagr_5y=cagr(_fcf[2021], _fcf[2025], 4),
    net_debt_to_ebitda=-3.0, worst_yoy_revenue=worst_yoy(_rev),
    note="핵심임원 이탈+보수적 가이던스로 YoY -46.7%, 매출성장은 24.6%로 견조하나 "
         "FCF수익률 3.37%로 밸류에이션 탈락.",
))

# ── 7차 배치: Seeking Alpha "30 for 30"(S&P500 -30%+ 30종목, 2026-07-15) 잔여 -
# TTD 발굴 과정. INTU/TTD/BSX는 통과해 정식분석(analyze_ttd_2026_07_31.py 등).
# CRM/ADBE/DECK/TYL/ZTS/CSGP/APP/ORCL/NKE/CHTR/PODD/LULU는 기존 기록·이미
# 스크리닝된 종목이라 이 파일에서 제외(중복 방지).
_rev = {2021: 4994e6, 2022: 5709e6, 2023: 6061e6, 2024: 6507e6, 2025: 6889e6}
_ocf = {2021: 640.1e6, 2022: 443.5e6, 2023: 823.3e6, 2024: 1056e6, 2025: 1171e6}
_capex = {2021: 51.9e6, 2022: 29e6, 2023: 38.4e6, 2024: 57.4e6, 2025: 43.8e6}
_fcf = {y: _ocf[y] - _capex[y] for y in _rev}
CANDIDATES.append(Candidate(
    ticker="BR", name="Broadridge Financial Solutions", exchange="NYSE",
    market_cap=17.81e9, fcf0=_fcf[2025],
    revenue_cagr_5y=cagr(_rev[2021], _rev[2025], 4), fcf_cagr_5y=cagr(_fcf[2021], _fcf[2025], 4),
    net_debt_to_ebitda=1.8, worst_yoy_revenue=worst_yoy(_rev),
    note="YoY -38.9%, FCF수익률 6.33%로 밸류에이션은 양호하나 현실적성장률 7.53%로 "
         "기준(8.0%) 근소 미달(STE와 유사한 근소탈락 유형). 가장 아까운 탈락.",
))


def main():
    results = screen_all(CANDIDATES)
    passed = [(c, r) for c, r in [(res.candidate, res) for res in results] if r.passed]
    failed = [(c, r) for c, r in [(res.candidate, res) for res in results] if not r.passed]

    print("=" * 108)
    print(f"2026-07-31/08-01 스크리닝 결과 - {len(passed)}/{len(results)} 통과")
    print("=" * 108)
    for c, r in passed:
        print(f"\n[{r.tier}등급] {c.ticker:11} {c.name}  ({c.exchange})")
        print(f"   FCF수익률 {r.fcf_yield*100:5.2f}%  ->  내재성장률 추정 {r.implied_growth_est*100:+5.2f}%"
              f"   (DRS추정 {r.drs_est:.1f})")
        print(f"   ** Gap 추정 {r.expectation_gap_est*100:+.2f}%p **")
        if c.note:
            print(f"   ※ {c.note}")

    print("\n" + "=" * 108)
    print("탈락 (사유 기록 - 재스크리닝 방지용)")
    print("=" * 108)
    for c, r in failed:
        print(f"  {c.ticker:11} {c.name:26} : {c.note}")

    print("\n" + "=" * 108)
    print("⚠️ 아래는 재무데이터를 긁기 전 '실제로 하락했는가' 확인 단계에서 이미 제외된 종목")
    print("   (Candidate 객체를 만들지 않았으므로 위 표에는 없음 - 재조회 방지용 기록)")
    print("=" * 108)
    excluded = {
        "TSLA": "52주 저점 언급됐으나 YoY +16.2%(변동성만 큼, 실제 하락 아님)",
        "MRNA/REGN/CVS/PFE/EW/MRK": "바이오/제약 다수가 오히려 YoY 급등 중 - 하락 후보군 자체가 아님",
        "BAX/ZBH": "YoY -3~-6% 소폭 하락, 급락 아님",
        "ALGN": "YoY -17.3%로 소폭, 매출성장도 4%대 낮아 후순위",
        "DAL/UAL": "항공은 이미 YoY 크게 반등(+34~60%). 설사 하락해도 코로나 저점(FY21)이 "
                   "CAGR을 왜곡하는 업종(BKNG 선례) - 스크리너 신뢰 안 함",
        "FSLR": "매출성장 양호(15.6%)하나 FCF가 FY21~24 내내 적자였다가 FY25에 막 흑자전환 "
                "- 1개년 데이터로는 판단 이름, 재무제표는 확보했으나 후보 보류",
        "XYZ(Block)": "FCF FY24~25 급개선 중이나 FY23까지 적자라 데이터 얇음 - 보류",
        "GLW": "TTM은 AI데이터센터發 가속 조짐 있으나 5년 CAGR 자체는 2.64%로 약함 - 후순위",
        "CCI": "매출 -35.7%가 파이버/스몰셀 사업매각 때문(PTC/GEN 선례와 동일 유형 왜곡) - "
               "세그먼트 조정 없이는 스크리닝 불가",
        "ORCL": "매출+17%/순이익+37%로 우량하나 AI데이터센터 capex가 1년새 6배 폭증해 "
                "FCF -$2.4B 적자전환 - Model N/A, capex 사이클 진정 후 재확인",
        "TRLV(Trulieve)": "대마초 - 연방 불법+280E 세제로 GAAP 손익이 정상기업과 비교 불가, "
                          "프레임워크 자체가 안 맞아 제외",
        "SOFI": "은행/대출업 특유 회계구조로 OCF가 매년 대규모 마이너스(대출자산 매입/매각이 "
                "지배) - FCF-DCF 계산 자체가 안 됨. 은행 전용 방법론 없어 제외(PGR/ACGL의 "
                "is_insurer처럼 별도 배선 필요하나 실증사례 더 필요)",
        "CSGP": "capex가 최근 2년 급증(마케팅 투자, Homes.com)해 FCF가 FY2024 마이너스 - "
                "변동성 과다로 제외",
        "APP(AppLovin)": "FY2023 모바일게임 매각으로 매출이 기준연도에 걸쳐 왜곡(PTC식 "
                          "구조단절) - 특별처리 필요, 보류",
        "LVS(Las Vegas Sands)": "YoY -11.9%로 하락폭이 작음(리스트에는 있었으나 실질적 "
                                 "'급락' 아님) - 후순위",
        "TRMB(Trimble)": "YoY -35.1%이나 순이익 -69.9% 급감 - 진짜 나빠짐",
        "INSM(Insmed)": "YoY +11.8%(하락 아님), 매출 급성장이나 대규모 순손실(-$1.18B) - "
                         "적자 바이오, 프레임워크 부적합",
        "UHS(Universal Health Services)": "YoY -2.8%로 하락폭 미미 - 후순위",
        "IT(Gartner)": "YoY -62.5%로 낙폭 크나 순이익 -40.9% 동반급감 - 진짜 나빠짐",
        "PNR(Pentair)": "YoY -37.7%이나 매출 자체가 역성장(-2.1%) - 진짜 나빠짐",
        "TSCO(Tractor Supply)": "YoY -48.1%이나 매출+4.0%/순이익-6.9% - 저성장+진짜나빠짐",
        "LDOS(Leidos)": "YoY -29.9%이나 매출성장 2.3%로 낮아 저성장 탈락 유력, 미정밀화",
        "PSKY(Paramount Skydance)": "YoY -0.3%(하락 아님), 대규모 순손실 - 제외",
    }
    for tickers, reason in excluded.items():
        print(f"  {tickers:24} : {reason}")

    print("\n" + "=" * 108)
    print("⚠️ 아래는 screen() 자체는 통과(A~B등급)했으나, 정식분석 직전 WebSearch로")
    print("   최근 동향을 확인한 결과 '진짜나빠짐'(4분류 3번)으로 판단돼 정식분석을")
    print("   보류한 종목 - screen()의 트레일링 CAGR에는 아직 반영 안 된 리스크")
    print("=" * 108)
    passed_but_deteriorating = {
        "INTU(Intuit, 2026-07-31 TTD와 함께 발굴)": (
            "screen() A등급 통과(트레일링 매출 CAGR 20%+, YoY-61.6%)하나, 2026-05-21 "
            "실적발표에서 회사 스스로 'TurboTax 저가필터 구간에서 가격경쟁 패배'를 "
            "인정하고 연매출 가이던스 하향 + 전체인력 17% 감원 발표, 주가 당일 -20%. "
            "IRS 신고건수 자체가 업계 전체 -30bp(코로나 이후 최대 위축)로 시장 축소 "
            "동반. 증권사기 소송(주가급락 관련 집단소송, 2026-09-08 마감)도 진행 중. "
            "이 미스는 FY2026(2026-07-31 마감, 아직 10-K 미제출)에 발생해 SEC EDGAR "
            "트레일링 데이터(FY2020~2025)에는 전혀 반영되지 않으므로, 지금 정식분석을 "
            "돌리면 이미 꺾인 성장세를 트레일링 CAGR로 낙관 추정하는 오류가 생긴다 - "
            "FY2026 10-K 제출(2026-09 예상) 후 재확인할 것."
        ),
        "BSX(Boston Scientific, 2026-07-31 TTD와 함께 발굴)": (
            "screen() B등급 통과(YoY-57%대)하나, 2026년 들어 가이던스를 반복 "
            "하향(연간 유기적성장 전망 6.5~8%로 재차 하향, Q2/Q3 순차 성장 사실상 "
            "정체 예고)했고 주력제품 Watchman(심장삽입기기) 매출이 정체 국면에 "
            "진입했다는 CEO 발언, CRE/CRE Pro 내시경장비 Class II 리콜(품질관리 "
            "이슈)까지 겹쳤다. 여기에 Penumbra 인수가 성장둔화 국면에서 레버리지를 "
            "크게 늘리는 시점과 맞물려 불확실성 가중. '가이던스 반복 하향'은 이 "
            "프로젝트가 여러 종목에서 확인한 진짜나빠짐의 전형적 패턴(TRMB/IT/PNR과 "
            "동일 계열) - 정식분석 보류."
        ),
    }
    for ticker, reason in passed_but_deteriorating.items():
        print(f"  {ticker}")
        print(f"    -> {reason}")

    print("\n" + "=" * 108)
    print("⚠️ 이 결과는 후보를 좁힌 1차 필터일 뿐 판정이 아니다.")
    print("   통과 종목은 반드시 engine/pipeline.py의 run_analysis()로 정식 분석할 것.")
    print("=" * 108)


if __name__ == "__main__":
    main()
