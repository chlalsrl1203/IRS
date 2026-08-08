"""
국내 상장(KRX) 미국지수 추종 ETF 분석 - 2026-08-08 추가분 (경기소비재/XLY).

경위: "계속해서 섹터 확장" 요청. v3.38/v3.39가 이미 11개 지수를 커버했는데,
이번에 `scripts/analyze_etfs_sectors_2026_08_08.py`로 새로 분석한 XLY(임의
소비재) 국내 래퍼를 추가한다. 기존 `analyze_krx_etfs_2026_08_07.py`를 통째로
재실행하지 않는다 - 그러면 안 바뀐 종목들까지 오늘 날짜로 재저장되어
`ledger_krx/`에 어제·오늘 중복 파일이 생긴다(v3.32/v3.35/v3.36이 반복 경계한
바로 그 사고). 이 스크립트는 **오늘 새로 추가되는 종목만** 다룬다.

⚠️ 이번 조사에서 소재(Materials/XLB)는 국내 상장 상품을 찾지 못했고, 부동산
(리츠/XLRE)은 국내 상품(KODEX 미국부동산리츠(H))이 있으나 기초지수가 달라
(Dow Jones US Real Estate Index ≠ Real Estate Select Sector Index) 재사용
전제가 깨진다 - 둘 다 정직한 공백으로 남긴다(추측 금지). 상세 근거는
`scripts/analyze_etfs_sectors_2026_08_08.py` 모듈독스트링 참고.

실행: python3 scripts/analyze_etfs_sectors_2026_08_08.py 먼저 실행해 XLY
원본을 채운 뒤 python3 scripts/analyze_krx_etfs_2026_08_08.py 실행.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.krx_etf_pipeline import (
    KRXWrapperInputs,
    format_krx_comparison_table,
    run_krx_wrapper_analysis,
    save_krx_ledger,
)
from engine.krx_etf_pipeline import compare_krx_wrappers

ETF_LEDGER_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ledger_etf")


def load_us_result(ticker: str, date: str) -> dict:
    path = os.path.join(ETF_LEDGER_DIR, f"{ticker}_{date}.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


CANDIDATES = [
    dict(
        krx_ticker="453660", krx_name="KODEX 미국S&P500경기소비재",
        tracks_same_index_as=(
            "S&P Consumer Discretionary Select Sector Index(Price Return) - "
            "공식페이지에서 확인, XLY와 동일 계열"
        ),
        us_reference_ticker="XLY", expense_ratio=0.0025, hedged=False,
        aum_krw=None,  # 검색으로 확인 못함 - "미확인"으로 정직하게 남김
        listed_date="미확인",
        data_sources=["funetf.co.kr/product/etf/view(2026-08-08)",
                       "samsungfund.com/etf/product/view.do?id=2ETFI8"],
    ),
]


def main():
    results = []
    for cand in CANDIDATES:
        us_result = load_us_result(cand["us_reference_ticker"], "2026-08-08")
        inputs = KRXWrapperInputs(**cand)
        result = run_krx_wrapper_analysis(inputs, us_result)
        results.append(result)
        path = save_krx_ledger(result)
        print(f"[{result['meta']['ticker']}] {result['meta']['name']} "
              f"({cand['us_reference_ticker']} 래퍼) -> {path}")

    print()
    print(format_krx_comparison_table(compare_krx_wrappers(results)))
    print("⚠️ 소재(Materials/XLB)·부동산(리츠/XLRE)은 이번 조사에서 국내 래퍼를 "
          "찾지 못했거나(소재) 기초지수가 달라 재사용할 수 없었다(리츠) - GICS 11섹터 "
          "중 이 둘만 아직 커버 안 됨.")
    print("⚠️ 테크놀로지(KODEX 미국S&P500테크놀로지, 463680)는 총보수를 이번에도 "
          "확인하지 못해 계속 제외 상태다.")


if __name__ == "__main__":
    main()
