"""
TIGER 미국다우존스30 재연결 - 2026-08-08 (DIA 2차 출처 반영 후속).

경위: `scripts/patch_dia_second_source_2026_08_08.py`가 DIA 원본에 2차 P/E
출처를 추가하며 ledger 날짜가 2026-08-07 -> 08-08로 바뀌었다. TIGER
미국다우존스30(245340)은 이 DIA 원본을 재사용하므로, 참조가 끊기지 않도록
새 날짜로 재연결한다. 입력값은 `analyze_krx_etfs_2026_08_07.py`의 245340
항목과 완전히 동일하다 - us_reference만 새 DIA 원본을 가리킨다.

실행: python3 scripts/patch_dia_krx_wrapper_2026_08_08.py
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.krx_etf_pipeline import KRXWrapperInputs, run_krx_wrapper_analysis, save_krx_ledger


def load_us_result(ticker: str, date: str) -> dict:
    path = os.path.join("ledger_etf", f"{ticker}_{date}.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main():
    us_result = load_us_result("DIA", "2026-08-08")
    inputs = KRXWrapperInputs(
        krx_ticker="245340", krx_name="TIGER 미국다우존스30",
        tracks_same_index_as=(
            "Dow Jones Industrial Average - 미래에셋 공식페이지에서 기초지수명 "
            "'Dow Jones Industrial Average' 직접 확인(DIA와 동일)"
        ),
        us_reference_ticker="DIA", expense_ratio=0.0035, hedged=False,
        aum_krw=1_491 * 1e8, listed_date="2016-07-01",
        data_sources=["investments.miraeasset.com(공식 상품페이지, 2026-08-07)"],
    )
    result = run_krx_wrapper_analysis(inputs, us_result)
    for src, s in result["valuation"]["by_source"].items():
        print(f"  - {src:24} P/E {s['pe_ratio']:6.2f}x -> Gap {s['gap']*100:+.2f}%p  {s['judgment']}")
    path = save_krx_ledger(result)
    print(f"ledger 저장: {path}")


if __name__ == "__main__":
    main()
