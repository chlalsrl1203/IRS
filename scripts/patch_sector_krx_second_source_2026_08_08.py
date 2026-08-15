"""
XLI/XLV/XLC/XLP 국내 래퍼 재연결 - 2026-08-08 (2차 P/E 출처 반영 후속).

경위: `scripts/analyze_etfs_sectors_2026_08_07.py`에 2차 P/E 출처를 추가하며
XLI/XLV/XLC/XLP 원본 ledger가 갱신됐다(단일출처 경고 해소). 이 4종을 재사용
하는 국내 래퍼(KODEX 미국S&P500산업재/헬스케어/필수소비재/커뮤니케이션)는
아직 구 버전(단일출처) 원본을 참조한 채로 남아있어 재연결이 필요하다. 입력값은
`analyze_krx_etfs_2026_08_07.py`의 해당 항목과 완전히 동일하다.

실행: python3 scripts/patch_sector_krx_second_source_2026_08_08.py
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
        krx_ticker="200030", krx_name="KODEX 미국S&P500산업재(합성)",
        tracks_same_index_as="S&P Industrial Select Sector Index(원화환산) - 공식페이지에서 확인, XLI와 동일 계열",
        us_reference_ticker="XLI", expense_ratio=0.0025, hedged=False,
        aum_krw=499 * 1e8, listed_date="미확인",
        data_sources=["funetf.co.kr/product/etf/view/KR7200030005(2026-08-07)"],
    ),
    dict(
        krx_ticker="453640", krx_name="KODEX 미국S&P500헬스케어",
        tracks_same_index_as="S&P Health Care Select Sector Index - 공식페이지에서 확인, XLV와 동일 계열",
        us_reference_ticker="XLV", expense_ratio=0.0025, hedged=False,
        aum_krw=15_460 * 1e8, listed_date="미확인",
        data_sources=["funetf.co.kr/product/etf/view/KR7453640005(2026-08-07)"],
    ),
    dict(
        krx_ticker="463690", krx_name="KODEX 미국S&P500커뮤니케이션",
        tracks_same_index_as=(
            "S&P Communication Services Select Sector Index(Price Return) - "
            "공식페이지에서 확인, XLC와 동일 계열"
        ),
        us_reference_ticker="XLC", expense_ratio=0.0025, hedged=False,
        aum_krw=131.10 * 1e8, listed_date="미확인",
        data_sources=["funetf.co.kr/product/etf/view/KR7463690008(2026-08-07)"],
    ),
    dict(
        krx_ticker="453630", krx_name="KODEX 미국S&P500필수소비재",
        tracks_same_index_as="S&P Consumer Staples Select Sector Index - 공식페이지에서 확인, XLP와 동일 계열",
        us_reference_ticker="XLP", expense_ratio=0.0025, hedged=False,
        aum_krw=119.36 * 1e8, listed_date="미확인",
        data_sources=["funetf.co.kr/product/etf/view/KR7453630006(2026-08-07)"],
    ),
]


def main():
    for cand in CANDIDATES:
        us_result = load_us_result(cand["us_reference_ticker"])
        inputs = KRXWrapperInputs(**cand)
        result = run_krx_wrapper_analysis(inputs, us_result)
        n_sources = len(result["valuation"]["by_source"])
        path = save_krx_ledger(result)
        print(f"[{result['meta']['ticker']}] {result['meta']['name']} - "
              f"{n_sources}개 출처 -> {path}")


if __name__ == "__main__":
    main()
