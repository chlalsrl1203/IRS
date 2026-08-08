"""
국내 상장(KRX) 미국지수 추종 ETF 분석 - 2026-08-08 추가분
(경기소비재/XLY, 반도체/SMH, 리츠/IYR, 배터리/LIT, 로봇/ROBO).

경위: "계속해서 섹터 확장" 요청, 이후 사용자가 실제 거래앱의 "지금 뜨고 있는
카테고리" 스크린샷을 제공하며 그 목록 기준으로 확장을 요청했다 - 반도체
밸류체인(스마트폰부품·종합반도체·반도체파운드리·반도체장비·반도체부품소재·
반도체팹리스)이 상위 11개 카테고리 중 6개를 차지할 만큼 압도적이었다. 기존
`analyze_krx_etfs_2026_08_07.py`를 통째로 재실행하지 않는다 - 안 바뀐 종목까지
오늘 날짜로 재저장되면 `ledger_krx/`에 어제·오늘 중복 파일이 생긴다(v3.32/
v3.35/v3.36이 반복 경계한 사고). 이 스크립트는 **오늘 새로 추가되는 종목만**
다룬다.

⚠️ 반도체는 처음엔 TIGER 미국필라델피아반도체나스닥(PHLX Semiconductor Sector
Index 추종)에 맞춰 SOXX를 쓰려 했으나, SOXX가 2021-06-21에 다른 지수(NYSE
Semiconductor Index)로 갈아탔다는 걸 확인해 대신 **같은 지수(MVIS US Listed
Semiconductor 25 Index)를 추종하는 KODEX 미국반도체(390390) + SMH** 조합으로
바꿨다 - TIGER 미국필라델피아반도체나스닥은 지수가 진짜 일치하는 미국 원본을
못 찾아 보류.

⚠️ 리츠는 v3.39에서 XLRE와 지수가 달라 제외했던 KODEX 미국부동산리츠(H)를,
"Dow Jones U.S. Real Estate Capped Index"를 추종하는 **IYR**과 짝지어 되살렸다
- "Capped" 여부까지 완전히 일치하는지는 미확정이라 XLE 때와 같은 수준의
불확실성으로 취급한다. 상세 근거는 `scripts/analyze_etfs_sectors_2026_08_08.py`
모듈독스트링 참고.

⚠️ 소재(Materials/XLB)는 이번에도 국내 상장 상품을 찾지 못해 정직한 공백으로
남긴다. 테크놀로지(463680)도 총보수 미확인으로 계속 제외.

⚠️ 배터리/리튬은 TIGER 글로벌리튬&2차전지SOLACTIVE(합성)(394670, Solactive
Global Lithium 지수)를 LIT와 짝지었다. 로봇/자동화는 KODEX 글로벌로봇(합성)
(276990, ROBO Global Robotics & Automation UCITS PR Index)을 ROBO와 짝지었다
(TIGER 글로벌AI&로보틱스INDXX↔BOTZ는 지수는 일치를 확인했으나 총보수를 못
찾아 보류). 우주항공/방산·은행·클라우드·게임·바이오는 조사 결과 매칭 원본이
없거나(자체 커스텀 지수) 밸류에이션이 원리적으로 불가능해(바이오/XBI, P/E
없음) 전부 제외했다 - 상세 근거는 `scripts/analyze_etfs_sectors_2026_08_08.py`
모듈독스트링 참고.

실행: python3 scripts/analyze_etfs_sectors_2026_08_08.py 먼저 실행해 원본을
채운 뒤 python3 scripts/analyze_krx_etfs_2026_08_08.py 실행.
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
    dict(
        krx_ticker="390390", krx_name="KODEX 미국반도체",
        tracks_same_index_as=(
            "MVIS US Listed Semiconductor 25 Index(KRW) - 공식페이지에서 확인, "
            "SMH(VanEck Semiconductor ETF)와 완전히 동일한 지수(SOXX는 2021년 "
            "다른 지수로 변경돼 제외)."
        ),
        us_reference_ticker="SMH", expense_ratio=0.0009, hedged=False,
        aum_krw=8_738 * 1e8,  # 시가총액 기준(순자산 원자료 확보 못함, 근사치)
        listed_date="2021-06-30",
        data_sources=["funetf.co.kr/product/etf/view/KR7390390003(2026-08-08)",
                       "samsungfund.com/sheet/20250805/2ETFE8_20250731.pdf"],
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
        estimated_hedge_carry=None,
        aum_krw=358.92 * 1e8, listed_date="2020-05-13",
        data_sources=["funddoctor.co.kr/ast/etf/etf_02.jsp?fund_cd=KR7352560007(2026-08-08)"],
    ),
    dict(
        krx_ticker="394670", krx_name="TIGER 글로벌리튬&2차전지SOLACTIVE(합성)",
        tracks_same_index_as=(
            "Solactive Global Lithium 지수(PR) - LIT(Global X Lithium & Battery "
            "Tech ETF)의 'Solactive Global Lithium Index'와 동일 계열."
        ),
        us_reference_ticker="LIT", expense_ratio=0.0049, hedged=False,
        # 순자산 출처가 엇갈림(공식 TIGER 사이트 1,890억원 vs 타 사이트 3,186억원) -
        # 공식 사이트 값을 채택하되 불일치 사실을 남겨둔다.
        aum_krw=1_890 * 1e8, listed_date="2021-07-20",
        data_sources=["tigeretf.com(공식, 2026-08-08) - 순자산 1,890억원 vs "
                      "investing.com 등 2차출처 3,186억원 불일치 확인, 공식값 채택"],
    ),
    dict(
        krx_ticker="276990", krx_name="KODEX 글로벌로봇(합성)",
        tracks_same_index_as=(
            "ROBO Global Robotics & Automation UCITS Price Return Index - "
            "ROBO(ROBO Global Robotics and Automation Index ETF)의 'ROBO Global "
            "Robotics and Automation TR Index'와 동일 계열(UCITS/PR vs 본토/TR "
            "표기 차이, IYR의 Capped 사례와 동일 수준으로 취급)."
        ),
        us_reference_ticker="ROBO", expense_ratio=0.003, hedged=False,
        aum_krw=254.33 * 1e8,  # 2025-09-30 기준(다소 stale, 원자료 그대로 사용)
        listed_date="미확인",
        data_sources=["samsungfund.com/sheet/20251013/2ETF91_20250930.pdf(2026-08-08)"],
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
    print("⚠️ 소재(Materials/XLB)는 이번에도 국내 상장 상품을 찾지 못했다 - "
          "GICS 11섹터 중 유일하게 아직 후보조차 없는 섹터.")
    print("⚠️ 테크놀로지(KODEX 미국S&P500테크놀로지, 463680)는 총보수를 이번에도 "
          "확인하지 못해 계속 제외 상태다.")
    print("⚠️ 반도체(KODEX 미국반도체)·리츠(KODEX 미국부동산리츠(H))·배터리(TIGER "
          "글로벌리튬&2차전지)·로봇(KODEX 글로벌로봇)은 GICS 11섹터에 속하지 않는 "
          "테마/산업 분류다 - 사용자가 제공한 거래앱 트렌드 카테고리를 근거로 추가했다.")
    print("⚠️ 우주항공/방산·은행·클라우드·게임·바이오/AI로보틱스(BOTZ)는 조사했으나 "
          "매칭 원본 부재 또는 방법론 한계로 제외했다(상세: analyze_etfs_sectors_"
          "2026_08_08.py 모듈독스트링).")


if __name__ == "__main__":
    main()
