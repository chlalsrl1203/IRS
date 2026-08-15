"""
국내 상장(KRX) 미국지수 추종 ETF 분석 - 2026-08-07 (v3.38).

경위: 이 ETF 엔진을 만든 실제 목적이 한국 ISA 계좌에서 살 ETF를 찾는 것이었다
- ISA 계좌는 국내 상장 ETF만 매수 가능해, v3.33~v3.37에서 분석한 VOO/QQQ/DIA/
XLE/XLU/IWM 같은 미국 상장 ETF 자체는 매수 대상이 아니다. 실제 매수 대상은 그
지수를 추종하는 국내 상장 ETF다.

밸류에이션은 새로 계산하지 않는다 - `ledger_etf/`에 이미 저장된 미국 원본
분석(P/E·성장률·위험점수)을 `run_krx_wrapper_analysis()`로 그대로 재사용하고,
국내 상장분 고유의 총보수·환헤지·순자산만 새로 반영한다(근거는
`engine/krx_etf_engine.py` 모듈독스트링 참고).

원자료(전부 2026-08-07 WebSearch 조회, 출처 각 ETF 주석에 명시):
  - etfshopping.com/best/us-etf, etfshopping.com/etf/index/nasdaq-100: 총보수·순자산
  - samsungfund.com, aceetf.co.kr, investments.miraeasset.com: 공식 상품 페이지
  - 상장일 일부는 검색으로 확인 못해 "미확인"으로 정직하게 남긴다(밸류에이션에는
    영향 없는 정보성 필드)

⚠️ TIGER 미국배당다우존스(458730)는 이름이 비슷해 보이지만 다우존스30이 아니라
Dow Jones U.S. Dividend 100 Index(SCHD와 동일 계열)를 추종한다 - 이번 조사에서
직접 확인한 사실이라 DIA 래퍼 후보에서 명시적으로 제외했다. DIA의 실제 국내
래퍼는 TIGER 미국다우존스30(245340, 기초지수 "Dow Jones Industrial Average"
공식 확인)뿐이다.

**섹터 확장(같은 날 추가, "섹터 다양한 방면으로" 요청)**: KODEX가 GICS 섹터별로
"KODEX 미국S&P500{섹터명}" 라인업을 운영 중임을 확인했다 - 전부 총보수
0.25%(운용보수 0.229%)로 통일돼 있고 기초지수가 각 Select Sector Index다.
이미 미국 원본이 있던 금융(XLF)·유틸리티(XLU)에 더해, 이번에
`scripts/analyze_etfs_sectors_2026_08_07.py`로 산업재(XLI)·헬스케어(XLV)·
커뮤니케이션서비스(XLC)·필수소비재(XLP) 미국 원본을 새로 분석해 국내 래퍼를
추가했다.

⚠️ **KODEX 미국S&P500테크놀로지(463680)는 이번 배치에서 제외했다** - 총보수를
여러 경로로 검색했으나 확인하지 못했다(다른 형제 상품은 전부 0.25%로 확인돼
같은 값일 가능성이 높지만, 추측으로 채우지 않는다 - 이 프로젝트의 원칙).
확인되는 대로 추가할 것.

⚠️ 순자산(aum_krw) 일부(KODEX 미국S&P500유틸리티)는 검색으로 확인하지 못해
`None`으로 남겼다 - `compare_krx_wrappers()`가 이를 "0원"이 아니라 "미확인"으로
처리해 비교 정렬 최하위로 두고 표에 "미확인"이라고 표시한다(v3.38 후반 완화,
회귀 테스트: `test_unconfirmed_aum_sorts_last_and_renders_as_unconfirmed`).

실행: python3 scripts/analyze_etfs_sectors_2026_08_07.py 먼저 실행해 미국 원본을
채운 뒤 python3 scripts/analyze_krx_etfs_2026_08_07.py 실행.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.krx_etf_pipeline import (
    KRXWrapperInputs,
    compare_krx_wrappers,
    format_krx_comparison_table,
    run_krx_wrapper_analysis,
    save_krx_ledger,
)

ETF_LEDGER_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ledger_etf")


def load_us_result(ticker: str, date: str = "2026-08-07") -> dict:
    path = os.path.join(ETF_LEDGER_DIR, f"{ticker}_{date}.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# (KRXWrapperInputs kwargs, us_reference_ticker) 튜플 목록.
# 억원 단위로 조사한 순자산은 여기서 원 단위로 환산한다(aum_krw = 억원 * 1e8).
CANDIDATES = [
    # ---- S&P500 (VOO) ----
    dict(
        krx_ticker="360750", krx_name="TIGER 미국S&P500",
        tracks_same_index_as="S&P500 - 공식 상품페이지에서 VOO와 동일 지수 확인",
        us_reference_ticker="VOO", expense_ratio=0.0006, hedged=False,
        aum_krw=204_640 * 1e8, listed_date="2020-08-07",
        data_sources=["etfshopping.com/best/us-etf(2026-08-07)",
                       "markets.hankyung.com/stock/360750(상장일)"],
    ),
    dict(
        krx_ticker="379800", krx_name="KODEX 미국S&P500",
        tracks_same_index_as="S&P500 - 삼성자산운용 공식페이지에서 VOO와 동일 지수 확인",
        us_reference_ticker="VOO", expense_ratio=0.0007, hedged=False,
        aum_krw=100_701 * 1e8, listed_date="미확인",
        data_sources=["etfshopping.com/best/us-etf(2026-08-07)"],
    ),
    dict(
        krx_ticker="360200", krx_name="ACE 미국S&P500",
        tracks_same_index_as="S&P500 - 한투운용 공식페이지에서 VOO와 동일 지수 확인",
        us_reference_ticker="VOO", expense_ratio=0.0007, hedged=False,
        aum_krw=40_405 * 1e8, listed_date="미확인",
        data_sources=["etfshopping.com/best/us-etf(2026-08-07)"],
    ),
    dict(
        krx_ticker="449180", krx_name="KODEX 미국S&P500(H)",
        tracks_same_index_as="S&P500 - KODEX 미국S&P500과 동일 지수의 환헤지형",
        us_reference_ticker="VOO", expense_ratio=0.0011, hedged=True,
        # 2026-08-08 반영: 한국 기준금리 2.75% vs 미국 연준 3.50~3.75%(중간값
        # 3.625%) - 차이 0.875%p를 캐리비용 추정치로 병기(자동 Gap 반영 안 함).
        estimated_hedge_carry=0.00875,
        aum_krw=9_937 * 1e8, listed_date="미확인",
        data_sources=["etfshopping.com/best/us-etf(2026-08-07)"],
    ),
    # ---- 나스닥100 (QQQ) ----
    dict(
        krx_ticker="133690", krx_name="TIGER 미국나스닥100",
        tracks_same_index_as="나스닥100 - 공식 상품페이지에서 QQQ와 동일 지수 확인",
        us_reference_ticker="QQQ", expense_ratio=0.0009, hedged=False,
        aum_krw=114_540 * 1e8, listed_date="2010-10-18",
        data_sources=["etfshopping.com/etf/index/nasdaq-100(2026-08-07)",
                       "funetf.co.kr(상장일)"],
    ),
    dict(
        krx_ticker="379810", krx_name="KODEX 미국나스닥100",
        tracks_same_index_as="나스닥100 - 삼성자산운용 공식페이지에서 QQQ와 동일 지수 확인",
        us_reference_ticker="QQQ", expense_ratio=0.0012, hedged=False,
        aum_krw=90_579 * 1e8, listed_date="미확인",
        data_sources=["etfshopping.com/etf/index/nasdaq-100(2026-08-07)"],
    ),
    dict(
        krx_ticker="367380", krx_name="ACE 미국나스닥100",
        tracks_same_index_as="나스닥100 - 한투운용 공식페이지에서 QQQ와 동일 지수 확인",
        us_reference_ticker="QQQ", expense_ratio=0.0010, hedged=False,
        aum_krw=35_067 * 1e8, listed_date="미확인",
        data_sources=["etfshopping.com/etf/index/nasdaq-100(2026-08-07)"],
    ),
    dict(
        krx_ticker="449190", krx_name="KODEX 미국나스닥100(H)",
        tracks_same_index_as="나스닥100 - KODEX 미국나스닥100과 동일 지수의 환헤지형",
        us_reference_ticker="QQQ", expense_ratio=0.0010, hedged=True,
        estimated_hedge_carry=0.00875,  # 2026-08-08 반영, 근거는 위 449180 주석 참고
        aum_krw=5_605 * 1e8, listed_date="미확인",
        data_sources=["etfshopping.com/etf/index/nasdaq-100(2026-08-07)"],
    ),
    # ---- 다우존스산업평균 (DIA) ----
    # ⚠️ TIGER 미국배당다우존스(458730)는 별개 지수(Dow Jones U.S. Dividend 100)를
    # 추종해 여기서 제외했다 - 위 모듈독스트링 참고.
    dict(
        krx_ticker="245340", krx_name="TIGER 미국다우존스30",
        tracks_same_index_as=(
            "Dow Jones Industrial Average - 미래에셋 공식페이지에서 기초지수명 "
            "'Dow Jones Industrial Average' 직접 확인(DIA와 동일)"
        ),
        us_reference_ticker="DIA", expense_ratio=0.0035, hedged=False,
        aum_krw=1_491 * 1e8, listed_date="2016-07-01",
        data_sources=["investments.miraeasset.com(공식 상품페이지, 2026-08-07)"],
    ),
    # ---- 에너지 섹터 (XLE) ----
    dict(
        krx_ticker="218420", krx_name="KODEX 미국S&P500에너지(합성)",
        tracks_same_index_as=(
            "S&P Select Sector Energy Index - XLE(Energy Select Sector SPDR)와 "
            "같은 Select Sector 지수 계열. 완전히 동일한 지수인지(vs 유사 계열)는 "
            "확정 못함 - 이 재사용은 그 전제 위에 있다는 걸 명시해둔다."
        ),
        us_reference_ticker="XLE", expense_ratio=0.0025, hedged=False,
        aum_krw=265.36 * 1e8, listed_date="미확인",
        data_sources=["samsungfund.com/etf/product/view.do?id=2ETF49(2026-08-07)"],
    ),
    # ---- 러셀2000 (IWM) ----
    # ⚠️ 국내 상장분은 헤지형(H)만 존재한다 - 확인된 범위에서 비헤지 버전 없음.
    dict(
        krx_ticker="280930", krx_name="KODEX 미국러셀2000(H)",
        tracks_same_index_as="FTSE Russell 2000 Index - 공식페이지에서 IWM과 동일 지수 확인",
        us_reference_ticker="IWM", expense_ratio=0.0045, hedged=True,
        estimated_hedge_carry=0.00875,  # 2026-08-08 반영, 근거는 449180 주석 참고
        aum_krw=266.0 * 1e8, listed_date="미확인",
        data_sources=["samsungfund.com/etf/product/view.do?id=2ETF95(2026-08-07)"],
    ),
    # ==== 섹터 확장 (같은 날 추가) - KODEX 미국S&P500{섹터} 라인업 ====
    # 전부 총보수 0.25%(운용보수 0.229%)로 통일 - funetf.co.kr 공식 상품페이지에서
    # 개별 확인(2026-08-07). 테크놀로지(463680)만 총보수 미확인이라 제외.
    dict(
        krx_ticker="453650", krx_name="KODEX 미국S&P500금융",
        tracks_same_index_as="S&P Financial Select Sector Index - 공식페이지에서 확인, XLF와 동일 계열",
        us_reference_ticker="XLF", expense_ratio=0.0025, hedged=False,
        aum_krw=5_195.8 * 1e8, listed_date="2023-03-21",
        data_sources=["funetf.co.kr/product/etf/view/KR7453650004(2026-08-07)"],
    ),
    dict(
        krx_ticker="463640", krx_name="KODEX 미국S&P500유틸리티",
        tracks_same_index_as="S&P Utilities Select Sector Index(Price Return) - 공식페이지에서 확인, XLU와 동일 계열",
        us_reference_ticker="XLU", expense_ratio=0.0025, hedged=False,
        aum_krw=None,  # 검색으로 확인 못함 - "미확인"으로 정직하게 남김(v3.38 후반 완화)
        listed_date="2023-08-01",
        data_sources=["funetf.co.kr/product/etf/view/KR7463640003(2026-08-07)"],
    ),
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
    us_cache = {}
    results = []
    for cand in CANDIDATES:
        us_ticker = cand["us_reference_ticker"]
        if us_ticker not in us_cache:
            us_cache[us_ticker] = load_us_result(us_ticker)
        us_result = us_cache[us_ticker]

        inputs = KRXWrapperInputs(**cand)
        result = run_krx_wrapper_analysis(inputs, us_result)
        results.append(result)

        path = save_krx_ledger(result)
        print(f"[{result['meta']['ticker']}] {result['meta']['name']} "
              f"({us_ticker} 래퍼) -> {path}")

    print()
    print("=" * 118)
    print("국내 상장 ETF 비교 - 같은 지수 그룹 내에서는 밸류에이션(Gap)이 전부 동일하다")
    print("(같은 미국 원본을 재사용했기 때문) - 그룹 내 순위는 비용·유동성으로만 매긴다.")
    print("=" * 118)
    groups = compare_krx_wrappers(results)
    print(format_krx_comparison_table(groups))

    print("⚠️ 환헤지형(H) 상품은 표의 총보수 외에 한미 금리차만큼의 캐리비용이 별도로 "
          "발생한다(추정치 미확보 - data_limitations에 경고 병기됨). 현재 미국 금리가 "
          "한국보다 높아 헤지가 구조적으로 불리한 국면임을 감안할 것.")
    print()
    print("⚠️ KODEX 미국S&P500에너지(합성)의 XLE 재사용은 '같은 Select Sector 지수 "
          "계열'이라는 가정 위에 있다 - 완전 동일 지수인지는 확정하지 못했다(위 주석 참고).")
    print()
    print("⚠️ 러셀2000(IWM)은 국내에 헤지형만 있어, 소형주 환노출 익스포저를 ISA에서 "
          "원하는 대로 담을 수단이 없다는 것 자체가 하나의 제약이다.")


if __name__ == "__main__":
    main()
