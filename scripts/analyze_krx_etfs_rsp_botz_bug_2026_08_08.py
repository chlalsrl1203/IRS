"""
TIGER 미국S&P500동일가중(488500)/TIGER 글로벌AI&로보틱스INDXX(464310)/
TIGER 글로벌AI사이버보안(418670) 국내 래퍼 연결 - 2026-08-08 (v3.39 후속
6차 마무리).

경위: `scripts/analyze_etfs_rsp_botz_bug_2026_08_08.py`로 RSP/BOTZ/BUG
미국 원본을 신규 분석했다. 지수 일치는 v3.39 후속 6차에서 이미 확인해뒀고
(488500=RSP의 S&P 500 Equal Weight Index, 464310=BOTZ의 Indxx Global
Robotics & AI Thematic Index, 418670=BUG의 Indxx Cybersecurity 지수),
이번에 총보수도 미래에셋 공식 상품페이지에서 전부 확인해(0.20%/0.49%/0.49%)
드디어 3종 모두 연결할 수 있게 됐다.

⚠️ 418670은 검색 중 상장공시에서 구 상품명("TIGER 글로벌사이버보안INDXX")
확인 - 2025-06-27 "ETF변경등록"으로 개명된 것으로 보인다. 기초지수 자체는
바뀌지 않았다(Indxx Cybersecurity 지수(PR)로 계속 확인됨) - 개명 사실만
참고로 남긴다.

실행: python3 scripts/analyze_krx_etfs_rsp_botz_bug_2026_08_08.py
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.krx_etf_pipeline import KRXWrapperInputs, run_krx_wrapper_analysis, save_krx_ledger


def load_us_result(ticker: str, date: str = "2026-08-08") -> dict:
    path = os.path.join("ledger_etf", f"{ticker}_{date}.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


CANDIDATES = [
    dict(
        krx_ticker="488500", krx_name="TIGER 미국S&P500동일가중",
        tracks_same_index_as=(
            "S&P 500 Equal Weight Index(PR) - 여러 조회창(thinkpool/funetf 등)에서 "
            "기초지수명 확인, RSP(Invesco S&P 500 Equal Weight ETF)와 동일 지수."
        ),
        us_reference_ticker="RSP", expense_ratio=0.0020, hedged=False,
        aum_krw=1_133 * 1e8, listed_date="2024-07-23",
        data_sources=[
            "investments.miraeasset.com(공식 상품페이지, 총보수 0.20%, 2026-08-08 확인)",
            "thinkpool.com/funetf.co.kr(AUM·상장일·기초지수, 2026-08-08 조회)",
        ],
    ),
    dict(
        krx_ticker="464310", krx_name="TIGER 글로벌AI&로보틱스INDXX",
        tracks_same_index_as=(
            "Indxx Global Robotics & Artificial Intelligence Thematic Index - "
            "v3.39 후속 6차에서 확인, BOTZ(Global X Robotics & AI ETF)와 동일 지수. "
            "KODEX 글로벌로봇(276990)이 추종하는 ROBO Global Robotics & Automation "
            "Index와는 다른 별개 지수이므로 혼동 주의."
        ),
        us_reference_ticker="BOTZ", expense_ratio=0.0049, hedged=False,
        aum_krw=1_341 * 1e8, listed_date="2023-08-17",
        data_sources=[
            "investments.miraeasset.com(공식 상품페이지, 총보수 0.49%, 2026-08-08 확인)",
            "funetf.co.kr/hankyung.com(AUM·상장일, 2026-08-08 조회)",
        ],
    ),
    dict(
        krx_ticker="418670", krx_name="TIGER 글로벌AI사이버보안",
        tracks_same_index_as=(
            "Indxx Cybersecurity 지수(PR) - 검색으로 기초지수 확인, "
            "BUG(Global X Cybersecurity ETF)와 동일 지수. 구 상품명 'TIGER "
            "글로벌사이버보안INDXX'에서 2025-06-27 ETF변경등록으로 개명된 것으로 "
            "보이나 기초지수는 동일하게 유지됨."
        ),
        us_reference_ticker="BUG", expense_ratio=0.0049, hedged=False,
        aum_krw=446 * 1e8, listed_date="2022-02-22",
        data_sources=[
            "investments.miraeasset.com(공식 상품페이지, 총보수 0.49%, 2026-08-08 확인)",
            "funetf.co.kr(AUM·상장일·기초지수, 2026-08-08 조회)",
        ],
    ),
]


def main():
    for cand in CANDIDATES:
        us_result = load_us_result(cand["us_reference_ticker"])
        inputs = KRXWrapperInputs(**cand)
        result = run_krx_wrapper_analysis(inputs, us_result)
        for src, s in result["valuation"]["by_source"].items():
            print(f"  - {src:24} P/E {s['pe_ratio']:6.2f}x -> Gap {s['gap']*100:+.2f}%p  {s['judgment']}")
        path = save_krx_ledger(result)
        print(f"[{result['meta']['ticker']}] {result['meta']['name']} -> {path}")


if __name__ == "__main__":
    main()
