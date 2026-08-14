"""
2026-08-14 매수관점 후보 스크리닝 (screener.py 4분류 체크리스트 적용).

기준·방법론은 engine/screener.py docstring 참고. 원자료 출처: Alpha Vantage
MCP(INCOME_STATEMENT/CASH_FLOW, 2026-08-14 조회, SEC 공시 기반) + WebSearch
(하락 배경 확인, 2026-08-13~14).

**절차**: Trefis 52주 저점 연재(2026-08-13/14)로 후보를 수집했으나 대부분
소형주였다. 그 중 시총 규모가 있는 AGCO(농기계)·RBA(산업장비 경매)를
확인했고, 별도 "저평가 우량주 52주 저점" 서사 기사에서 Kroger(KR)를 확인했다.
**이번 배치는 3개 후보 전부 정량 스크리닝(screen()) 이전 단계에서 제외됐다**
- 재무데이터를 실제로 긁어 검증한 결과, 서사만으로 판단했다면 오분류했을
  후보(RBA)가 있었다는 게 이번 배치의 소득이다.

- **KR(Kroger) - 4분류 3번(진짜나빠짐), Alpha Vantage 실측으로 확정.**
  WebSearch로 발견한 "flat sales" 서사를 그대로 믿지 않고 Alpha Vantage
  연간 손익계산서로 직접 대조했다: 매출은 실제로 정체(FY2023 $150.04B ->
  FY2024 $147.12B -> FY2025 $147.64B, 4년째 $147~150B 박스권) - 이건 서사와
  일치. 그런데 **영업이익이 훨씬 심각하게 무너지고 있었다**: FY2023 $4.13B
  -> FY2024 $3.10B -> FY2025 $3.85B -> **FY2026(FYE 2026-01-31) $1.89B로
  최근 1년새 -50.9%**. 자동화 물류창고 축소·점포 구조조정 비용, 할인점
  (Aldi/Lidl) 경쟁강도 심화가 마진에서 직접 확인됨 - 매출 정체 서사보다
  영업이익 붕괴가 훨씬 더 위험한 신호였다. 재무데이터를 긁어보니 서사가
  오히려 실제보다 관대했던 사례(BSX와 정반대 방향).
- **AGCO(AGCO Corp, 농기계) - 4분류 3번(진짜나빠짐), 확정.** 매출이 FY2023
  고점 $14.41B에서 FY2024 $11.66B(-19.1%YoY) -> FY2025 $10.08B(-13.5%YoY)로
  **2년 연속 두 자릿수 역성장**, 영업이익은 같은 기간 $1.70B -> $698.7M로
  -59% 급감. 독일 등 유럽 수요 예상치 하회, 남미 여신경색, 가이던스 하향이
  전부 서사가 아니라 손익계산서에 그대로 찍혀 있다 - 재무데이터 확보 없이도
  이미 명확했지만 확인차 긁어 재검증.
- **RBA(RB Global, 산업장비 경매) - 프레임워크 부적합(M&A가 5y CAGR 구간에
  걸침), FRAMEWORK_MISMATCH로 분류.** WebSearch 서사(서비스 테이크레이트
  -110bp, 사업믹스 저마진화)만 보면 4분류 3번처럼 보였으나, Alpha Vantage
  분기 실측을 대조하니 **정반대였다** - 가장 최근 분기(2026Q2) 매출이
  +11.05%YoY, 2026Q1 +11.37%YoY로 감속 기미가 전혀 없고 영업이익도 분기마다
  $2.0~3.2억대로 견조하다. 문제는 5y 연간 CAGR 쪽에서 나왔다 - IAA(자동차
  경매) 인수가 2023년에 종결되며 매출이 2022년 $1.73B에서 2023년 $3.68B로
  +112% 급증(GEN/BRO/ROP/SNPS/NRG와 동일한 'M&A가 CAGR 구간 중간에 걸리는'
  패턴), 5y CAGR(2020->2025)이 매출·FCF 둘 다 27~28%로 나오지만 이건 유기적
  성장이 아니라 대부분 인수 단계상승이다. 인수 이후로만 깨끗한 분기별
  YoY(+7~11%, 전부 2024Q3 이후 구간)는 오히려 견조한 성장을 보여주지만,
  screener.py의 5y CAGR 프레임(MIN_REALISTIC_GROWTH=8% 등 5y 기준으로 보정된
  임계값)에 억지로 밀어넣으면 왜곡된 숫자가 된다 - SNPS/NRG와 동일하게
  세그먼트조정 없이는 정량모델에 넣지 않기로 했다. **서사만 보고 판단했다면
  '진짜나빠짐'으로 잘못 분류했을 후보** - 재무데이터 대조가 실제로 방향을
  바꾼 사례로 기록해둔다.

**결과: 이번 배치는 screen() 자체를 한 번도 호출하지 않았다** - 3개 후보
전부 이전 단계에서 걸러졌다(KR/AGCO는 진짜나빠짐 확정, RBA는 프레임워크
부적합). CANDIDATES 리스트가 비어 있는 게 처음이지만, 이것도 "재무데이터를
긁어 검증했다"는 방법론적 원칙은 동일하게 지켰다 - 특히 RBA는 서사와 실측이
갈린 유일한 사례라 documented.
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

# ── 아래는 WebSearch/Alpha Vantage 확인 단계에서 4분류 3번(진짜나빠짐)으로 제외 ──
PREFILTERED_OUT = {
    "KR(Kroger)": (
        "Alpha Vantage INCOME_STATEMENT 실측(2026-08-14): 매출은 4년째 "
        "$147~150B 박스권(FY2023 $150.04B -> FY2024 $147.12B -> FY2025 "
        "$147.64B)으로 서사('flat sales')와 일치하지만, **영업이익이 훨씬 "
        "심각하게 무너지고 있었다** - FY2023 $4.13B -> FY2024 $3.10B -> "
        "FY2025 $3.85B -> FY2026(FYE 2026-01-31) $1.89B로 최근 1년새 -50.9%. "
        "자동화 물류창고 축소·점포 구조조정 비용, 할인점(Aldi/Lidl) 경쟁강도 "
        "심화가 마진 붕괴로 직접 확인됨. 매출 정체보다 영업이익 붕괴가 훨씬 "
        "더 위험한 신호라 4분류 3번(진짜나빠짐)으로 확정, 재무데이터 확보 후 "
        "제외."
    ),
    "AGCO(AGCO Corp)": (
        "Alpha Vantage INCOME_STATEMENT 실측(2026-08-14): 매출이 FY2023 "
        "고점 $14.41B에서 FY2024 $11.66B(-19.1%YoY) -> FY2025 "
        "$10.08B(-13.5%YoY)로 2년 연속 두 자릿수 역성장, 영업이익은 같은 "
        "기간 $1.70B -> $698.7M로 -59% 급감. 유럽(특히 독일) 수요 예상치 "
        "하회, 남미 여신경색, 가이던스 하향이 손익계산서에 그대로 반영됨 - "
        "4분류 3번(진짜나빠짐) 확정."
    ),
}

# ── 프레임워크 자체가 5y CAGR과 안 맞는 경우 - 재무데이터는 확보했으나 정량모델 제외 ──
FRAMEWORK_MISMATCH = {
    "RBA(RB Global)": (
        "**서사와 실측이 갈린 사례** - WebSearch 서사(서비스 테이크레이트 "
        "-110bp, 사업믹스 저마진화)만 보면 4분류 3번처럼 보였으나, Alpha "
        "Vantage 분기 실측(2026-08-14)은 정반대다: 가장 최근 분기(2026Q2) "
        "매출 +11.05%YoY, 2026Q1 +11.37%YoY로 감속 없이 견조, 영업이익도 "
        "분기마다 $2.0~3.2억대로 안정적. 문제는 5y 연간 CAGR 쪽 - IAA(자동차 "
        "경매) 인수가 2023년 종결되며 매출이 2022년 $1.73B -> 2023년 "
        "$3.68B(+112%)로 급증(GEN/BRO/ROP/SNPS/NRG와 동일한 'M&A가 CAGR "
        "구간 중간에 걸리는' 패턴) - 5y CAGR(2020->2025, 매출·FCF 둘 다 "
        "27~28%)은 유기적성장이 아니라 대부분 인수 단계상승이다. 인수 이후 "
        "구간만의 분기별 YoY(+7~11%, 전부 2024Q3 이후)는 오히려 견조하지만, "
        "screener.py의 5y CAGR 프레임(5y 기준으로 보정된 임계값)에 억지로 "
        "밀어넣으면 왜곡된다 - SNPS/NRG와 동일 판단으로 세그먼트조정 없이는 "
        "정량모델 제외. 서사만 믿었다면 오분류했을 후보라 그대로 기록해둔다."
    ),
}


def main():
    if not CANDIDATES:
        print("=" * 108)
        print("2026-08-14 스크리닝 결과")
        print("=" * 108)
        print("이번 배치는 4분류 체크리스트 단계에서 후보 전부 제외됨 - screen() 미호출.")
        print()
        print(f"1차 분류에서 제외된 후보 ({len(PREFILTERED_OUT)}건):")
        for k, v in PREFILTERED_OUT.items():
            print(f"  - {k}: {v}")
        print()
        print(f"프레임워크 부적합으로 정량모델 제외 ({len(FRAMEWORK_MISMATCH)}건):")
        for k, v in FRAMEWORK_MISMATCH.items():
            print(f"  - {k}: {v}")
        return

    results = screen_all(CANDIDATES)
    print("=" * 108)
    print("2026-08-14 스크리닝 결과")
    print("=" * 108)
    print(format_table(results))


if __name__ == "__main__":
    main()
