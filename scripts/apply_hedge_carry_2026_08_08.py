"""
환헤지형 KRX 래퍼 4종에 캐리비용 추정치 반영 - 2026-08-08.

경위: v3.38부터 `estimated_hedge_carry`가 opt-in 필드로 열려 있었지만 실제
값을 넣은 적이 없어 헤지형 4종목(KODEX 미국S&P500(H)/미국나스닥100(H)/
미국러셀2000(H)/미국부동산리츠(H)) 전부 "[환헤지 비용 미반영]" 경고만 달고
있었다. 한국은행 기준금리(2.75%, 2026-07-16 인상 이후)와 미국 연준 정책금리
(3.50~3.75%, 중간값 3.625%)를 확인해 차이 0.875%p를 캐리비용 추정치로
병기한다.

⚠️ 이 값은 **자동으로 Gap에 반영되지 않는다** - `hedge_cost_warning()`이
설계된 "병기, 자동판정 안 함" 원칙(is_insurer/sbc_cross_check와 동일)에
따라 `data_limitations`에 별도 경고 문구로만 남는다. 실제 헤지 캐리비용은
스팟 정책금리 차이가 아니라 통화선물 스왑레이트(FX swap points)로 결정되며
시장 수급에 따라 정책금리차와 괴리될 수 있다 - 이 값은 근사치임을 명시한다.

전체 KRX 스크립트(17개 종목)를 재실행하지 않는다 - 헤지형이 아닌 24종목까지
불필요하게 오늘 날짜로 재저장되면 대량의 파일 교체가 발생한다(v3.32/v3.35/
v3.36이 경계한 사고와 같은 계열의 낭비). 이 스크립트는 **헤지형 4종목만**
다룬다. 재계산 결과는 캐리비용 경고 문구 추가를 빼면 Gap·판정 등 전부
기존과 동일함을 diff로 확인한 뒤 구 파일을 git rm하고 교체한다.

실행: python3 scripts/apply_hedge_carry_2026_08_08.py
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.krx_etf_pipeline import KRXWrapperInputs, run_krx_wrapper_analysis, save_krx_ledger

ETF_LEDGER_DIR = "ledger_etf"

# 2026-08-08 확인: 한국은행 기준금리 2.75%(2026-07-16 인상), 미국 연준
# 정책금리 3.50~3.75%(중간값 3.625%) - 차이 0.875%p.
HEDGE_CARRY_ESTIMATE = 0.00875
HEDGE_CARRY_SOURCE = "한국은행 기준금리 2.75% vs 미국 연준 3.50~3.75%(중간값), 2026-08-08 확인"


def load_us_result(ticker: str, date: str) -> dict:
    path = os.path.join(ETF_LEDGER_DIR, f"{ticker}_{date}.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


CANDIDATES = [
    dict(
        krx_ticker="449180", krx_name="KODEX 미국S&P500(H)",
        tracks_same_index_as="S&P500 - KODEX 미국S&P500과 동일 지수의 환헤지형",
        us_reference_ticker="VOO", expense_ratio=0.0011, hedged=True,
        estimated_hedge_carry=HEDGE_CARRY_ESTIMATE,
        aum_krw=9_937 * 1e8, listed_date="미확인", us_date="2026-08-07",
        data_sources=["etfshopping.com/best/us-etf(2026-08-07)", HEDGE_CARRY_SOURCE],
    ),
    dict(
        krx_ticker="449190", krx_name="KODEX 미국나스닥100(H)",
        tracks_same_index_as="나스닥100 - KODEX 미국나스닥100과 동일 지수의 환헤지형",
        us_reference_ticker="QQQ", expense_ratio=0.0010, hedged=True,
        estimated_hedge_carry=HEDGE_CARRY_ESTIMATE,
        aum_krw=5_605 * 1e8, listed_date="미확인", us_date="2026-08-07",
        data_sources=["etfshopping.com/etf/index/nasdaq-100(2026-08-07)", HEDGE_CARRY_SOURCE],
    ),
    dict(
        krx_ticker="280930", krx_name="KODEX 미국러셀2000(H)",
        tracks_same_index_as="FTSE Russell 2000 Index - 공식페이지에서 IWM과 동일 지수 확인",
        us_reference_ticker="IWM", expense_ratio=0.0045, hedged=True,
        estimated_hedge_carry=HEDGE_CARRY_ESTIMATE,
        aum_krw=266.0 * 1e8, listed_date="미확인", us_date="2026-08-07",
        data_sources=["samsungfund.com/etf/product/view.do?id=2ETF95(2026-08-07)", HEDGE_CARRY_SOURCE],
    ),
    dict(
        krx_ticker="352560", krx_name="KODEX 미국부동산리츠(H)",
        tracks_same_index_as=(
            "Dow Jones US Real Estate 지수 - IYR(iShares U.S. Real Estate ETF)의 "
            "'Dow Jones U.S. Real Estate Capped Index'와 같은 계열. ⚠️ 'Capped' "
            "적용 여부까지 완전히 일치하는지는 확정 못함(XLE/KODEX에너지와 동일 "
            "수준의 불확실성으로 취급)."
        ),
        us_reference_ticker="IYR", expense_ratio=0.0009, hedged=True,
        estimated_hedge_carry=HEDGE_CARRY_ESTIMATE,
        aum_krw=358.92 * 1e8, listed_date="2020-05-13", us_date="2026-08-08",
        data_sources=["funddoctor.co.kr/ast/etf/etf_02.jsp?fund_cd=KR7352560007(2026-08-08)",
                      HEDGE_CARRY_SOURCE],
    ),
]


def main():
    for raw in CANDIDATES:
        cand = dict(raw)
        us_date = cand.pop("us_date")
        us_result = load_us_result(cand["us_reference_ticker"], us_date)
        inputs = KRXWrapperInputs(**cand)
        result = run_krx_wrapper_analysis(inputs, us_result)
        path = save_krx_ledger(result)
        print(f"[{result['meta']['ticker']}] {result['meta']['name']} -> {path}")
        for x in result["data_limitations"]:
            if "환헤지" in x:
                print(f"    ✓ {x}")


if __name__ == "__main__":
    main()
