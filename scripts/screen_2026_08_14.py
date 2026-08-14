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

**후속 조사(동일 08-14 세션, 사용자 "계속" 요청) - NOW(ServiceNow) 추가.**
Trefis 52주 저점 풀이 소진돼(최신 리스트가 이미 다룬 종목만 반복) Morningstar
"3 Stocks to Buy in August" 등 대체 출처로 확장, ServiceNow(NOW)를 발견했다 -
"AI 에이전트가 엔터프라이즈 SW 좌석을 대체한다"는 공포 서사(2026-01 촉발)로
52주 고점($194.73) 대비 -53% 하락. Alpha Vantage 실측: 분기 매출 YoY가 오히려
가속(Q3'25 +21.8% → Q4'25 +20.7% → Q1'26 +22.1% → **Q2'26 +24.0%**) - 공포
서사와 정반대라 처음엔 RBA와 같은 '서사 vs 실측 반전' 사례로 보였다. **그런데
대차대조표 확인 중 goodwill이 Q1'26 $4.54B → Q2'26 $9.84B로 한 분기만에
2배 이상 급증**한 걸 발견해 조사를 확장했고, ServiceNow가 최근 M&A를
공격적으로 진행 중임을 확인했다(Moveworks $2.85B 2025-12 종결, Veza
2026H1 종결, Armis $7.75B - 사상 최대 규모 - 2026H2 종결 예정). **RBA와
동일한 'M&A가 성장구간에 걸리는' 패턴**이 이번엔 단일 인수가 아니라 연쇄
인수라 더 심하게 오염됐을 가능성이 높다 - 방금 확인한 "가속하는" 분기 매출
성장이 순수 유기적성장이 아니라 상당부분 인수효과일 수 있다는 뜻. 게다가
애초 서사 조사에서 확인한 "organic cRPO growth decelerating to high teens"
(연결매출과 별개로 보고되는 유기적 계약잔액 지표)는 M&A 오염과 무관하게
**실제 유기적 성장 둔화 신호**였다 - 즉 이 종목은 공포과잉이 아니라 (a)
연결 실적은 M&A로 부풀려져 5y CAGR 프레임에 넣을 수 없고, (b) 그 왜곡을
걷어낸 유기적 지표조차 이미 감속 중이라는 이중의 문제를 가진다. RBA처럼
FRAMEWORK_MISMATCH로 분류하되, RBA와 달리 "정량모델만 못 쓸 뿐 서사는
과장됐다"고 볼 근거가 약해 재무데이터를 추가로 긁지 않고 여기서 멈췄다.

**후속 조사 2차(동일 08-14 세션, 사용자 "계속 스크리닝" 요청) - 러셀3000
확장, 8종목 전수탈락.** S&P500 52주 저점 풀이 완전히 소진돼 Trefis
"11 Stocks Hit 52-Week Lows On Thursday"(2026-08-14, Russell 3000 전체
대상)로 범위를 넓혔다. 11종목 중 ROL/RBA/AGCO는 이미 처리 완료, 신규
8종목(GPI/UVV/AMSF/LMB/ARDX/WBTN/EMAT/SECZ)을 확인했으나 **전부 정량
스크리닝 이전 단계에서 제외됐다** - 이번엔 서사-실측 반전 같은 흥미로운
발견은 없었고, 규모·업종구조·상장이력·재무프레임 부적합이 반복 확인된
배치다:
- GPI(자동차 딜러)·UVV(담배잎 공급): CL과 동일하게 업종 자체가
  MIN_REALISTIC_GROWTH(8%)와 구조적으로 안 맞음, 시총도 소형($4.14B/$1.31B).
- AMSF(소형 워커스컴프 보험사, 시총 $556.82M): is_insurer 경로는 있지만
  관측 사례(ACGL·PGR, 둘 다 대형 종합보험사) 2건뿐이라 이 정도 소형
  특화보험사에 적용할 근거가 약함.
- LMB(Limbach Holdings): 52주 고점 대비 -61.1%, Q2 EPS 컨센서스 대비
  -30.9% 큰 폭 미스+마진압박+가이던스 하회 - 서사가 아니라 실적으로 이미
  악화가 확인된 4분류 3번.
- ARDX(Ardelyx): OCF 여전히 마이너스(상업화 초기 제약사) - ORCL과 동일하게
  FCF0<=0 Model N/A 가드에 걸릴 후보, 가이던스도 하향 조정됨.
- WBTN(WEBTOON)·EMAT(Evolution Metals): 각각 2024년 IPO(상장이력 부족,
  PODD/APP과 동일 유형)·신생 투기적 소형주(하루새 +39.38% 급등할 정도의
  변동성) - 프레임워크 부적합.
- SECZ: WebSearch로 실체를 확인하지 못함 - 추측하지 않고 확인불가로 남김.

**후속 조사 3차(동일 08-14 세션, 사용자 "스크리닝 계속" 요청) - ONON(On
Holding).** Trefis 풀이 소진돼 "quality stock oversold" 계열 검색으로 확장,
On Holding(ONON)을 발견했다 - 52주 고점 대비 큰 폭 하락에도 Q2 2026 순매출
+21.6%(CC), DTC +34%, 총마진 사상최대 65.4%로 서사만 보면 공포과잉(4분류
1번) 후보였다. FCF 원자료를 확보하는 과정에서 처음엔 출처 간 불일치가
발견됐다 - Alpha Vantage INCOME_STATEMENT의 FY2025 매출(CHF 2,878.5M)이
회사 1차 출처(공식 보도자료+20-F 표지, CHF 3,014.0M, +30.0%YoY)와 4.7%
차이났고, CASH_FLOW 엔드포인트는 아예 실패했다. HTML 기반 2차 출처도 서로
모순됐다.

**후속 조사 4차(동일 세션, 사용자 "계속 더 파고들어봐" 요청) - SEC XBRL
API로 원자료 신뢰도 문제를 실제로 해결했다.** HTML 스크레이핑을 포기하고
`data.sec.gov/api/xbrl/companyfacts/CIK0001858985.json`(회사가 SEC에 직접
제출한 구조화 XBRL 원자료)을 조회한 결과 stockanalysis.com 2차 조회값과
정확히 일치했다(FY2025 매출 CHF 3,014.0M/OCF 359.5M/capex 72.9M) - Alpha
Vantage 매출이 부정확했던 것으로 확정. **그런데 정확한 원자료를 확보하고
나니 새로운 문제가 드러났다** - FCF(OCF-capex)가 2022년 재고 CHF 273M
급증(급성장기 스케일업, WebSearch로 구조적 악화가 아님을 확인)으로 심각한
적자(-287.3M)를 기록해, 5y CAGR의 표준 시작점 후보(2020년 -25.7M/2021년
-7.7M) 둘 다 음수라 CAGR 자체가 정의되지 않는다(v3.19 가드 해당 - PODD와
같은 유형이나 '흑자→성장통 적자→흑자 재개'라는 비단조 패턴이 PODD의 단조
패턴과는 다르다). 결국 PREFILTERED_OUT이 아니라 FRAMEWORK_MISMATCH로
재분류했다 - 매출 자체는 견조(5y CAGR 47.9%)하지만 5y CAGR 프레임에 억지로
밀어넣지 않는다는 PODD/APP 원칙을 그대로 적용한 것.

**후속 조사 5차(동일 세션, 사용자 "계속 스크리닝" 요청) - AMD, 이번 배치
유일의 실제 screen() 통과 시도.** "analyst buy rating maintained despite
selloff" 계열 검색으로 AMD를 발견 - 2026-08-04 Q2 실적발표에서 매출
$11.54B(+50.1%YoY, 컨센서스 상회)·데이터센터 매출 2배 이상($6.72B)·EPS
컨센서스 상회에도 시간외 -8.82% 급락. 원인은 실적 미스가 아니라 실적발표
직전 5거래일간 +21% 랠리로 기대치가 '블로아웃'급으로 과열된 상태에서
Q3 매출총이익률 가이던스가 전분기와 동일(약 56%)했던 점 - 공포과잉과는
결이 다른 '기대치 과열' 유형이라 판단해 재무데이터를 확보, 이번 배치에서
유일하게 CANDIDATES에 넣어 screen()을 실제로 실행했다. **결과: FAIL** -
내재성장률 추정 9.76%가 임계값(5.5%)을 크게 상회, FCF수익률(0.79%)이
필요치(4.86%)에 크게 못 미쳤다. 매출 5y CAGR 28.82%·FCF CAGR 53.85%(마진
확장 중, capex 재검토 대상 아님)로 성장 자체는 넉넉히 통과했지만, 시가
총액이 이미 $847.59B(주가가 52주 범위 상단 $584.73 근처까지 반등한 상태 -
급락 이벤트가 이미 지나갔고 시장이 그 이후 되돌린 것으로 추정)로 워낙 커
밸류에이션 단계에서 탈락했다 - META와 동일한 4분류 2번('실적은 훌륭한데
이미 비쌈') 패턴으로 확인된 사례.
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

# ── AMD (Advanced Micro Devices) - 실적 서프라이즈에도 급락, 후속조사 5차 ──
# 원자료: Alpha Vantage INCOME_STATEMENT/CASH_FLOW/BALANCE_SHEET(2026-08-14).
# 시가총액은 WebSearch 여러 출처 중 가장 보수적(비싼) 값 채택($847.59B,
# ETF/KRX 비교표와 동일 관행). 하락배경: 2026-08-04 Q2 실적발표 - 매출
# $11.54B(+50.1%YoY, 컨센서스 상회), 데이터센터 매출 2배 이상($6.72B), EPS도
# 컨센서스 상회했음에도 시간외 -8.82% 급락(WebSearch, 2026-08-14). 원인은
# 실적 미스가 아니라 (1) 이미 실적발표 전 5거래일간 +21% 랠리로 기대치가
# '블로아웃'급으로 과열돼 있었고, (2) Q3 비GAAP 매출총이익률 가이던스가
# 전분기와 동일한 약 56%로 제시(믹스개선 기대에 못미침), (3) capex 급증(순차
# 2배 이상)으로 FCF가 분기 기준 순차 -39% 감소한 점 - "실적은 좋았으나
# 블로아웃은 아니었다"는 전형적 기대치 과열 패턴(공포과잉과는 결이 다른
# '기대치 과열' 유형).
_rev_amd = {2020: 9763, 2021: 16434, 2022: 23601, 2023: 22680, 2024: 25785, 2025: 34639}
_fcf_amd = {2020: 1071 - 294, 2021: 3521 - 301, 2022: 3565 - 450,
            2023: 1667 - 546, 2024: 3041 - 636, 2025: 7709 - 1012}
_capex_amd = {2020: 294, 2021: 301, 2022: 450, 2023: 546, 2024: 636, 2025: 1012}
CANDIDATES.append(Candidate(
    ticker="AMD", name="Advanced Micro Devices", exchange="NASDAQ",
    market_cap=847590, fcf0=_fcf_amd[2025],
    revenue_cagr_5y=cagr(_rev_amd[2020], _rev_amd[2025], 5),
    fcf_cagr_5y=cagr(_fcf_amd[2020], _fcf_amd[2025], 5),
    net_debt_to_ebitda=-0.91,  # 총부채 $44.72억 - 현금+ST투자 $105.52억(FY2025), 순현금 상태
    worst_yoy_revenue=worst_yoy(_rev_amd),  # 2023년 -3.90%(PC수요침체+Xilinx 통합비용)
    capex_to_revenue_current=_capex_amd[2025] / _rev_amd[2025],
    capex_to_revenue_avg=sum(_capex_amd[y] / _rev_amd[y] for y in range(2020, 2025)) / 5,
    note=(
        "FY2025 실측: 매출 5y CAGR 28.82%, FCF CAGR 53.85%(매출보다 훨씬 "
        "빠름 - 마진 확장 중, capex/매출도 2020-2024 평균 2.32% -> 2025 "
        "2.92%로 소폭 상승에 그쳐 META급 급증(+14.05%p)과는 성격이 다름, "
        "v3.20 capex 재검토 대상 아님). worst_yoy_revenue -3.90%(2023년 "
        "PC수요침체+Xilinx 인수통합비용 반영, Xilinx 인수가 2022년 종결이라 "
        "5y창 초입에 걸리지만 매출 자체는 그 해에도 견조했고 왜곡은 크지 "
        "않다고 판단)."
    ),
))

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
    "NOW(ServiceNow)": (
        "**RBA와 유형은 같으나 결론은 다른 사례(후속 조사, 동일 08-14 세션).** "
        "'AI 에이전트가 SW 좌석을 대체한다'는 공포 서사(52주 고점 대비 -53%)와 "
        "달리 Alpha Vantage 분기 매출은 오히려 가속(Q3'25 +21.8% -> Q2'26 "
        "+24.0%YoY) - 그러나 같은 기간 goodwill이 $4.54B(Q1'26) -> "
        "$9.84B(Q2'26)로 급증해 확인해보니 Moveworks($2.85B, 2025-12 종결)/"
        "Veza(2026H1 종결)/Armis($7.75B, 사상최대, 2026H2 종결예정) 연쇄 인수가 "
        "진행 중이었다 - RBA(IAA 1건)보다 더 심하게 5y CAGR을 오염시킬 가능성이 "
        "높다. 게다가 M&A와 무관하게 보고되는 유기적 지표(cRPO organic growth)"
        "조차 'high teens로 감속 중'이라는 서사가 앞선 서사조사로 이미 확인된 "
        "상태다 - RBA는 프레임워크만 못 쓸 뿐 서사가 과장됐다는 근거가 있었지만, "
        "NOW는 프레임워크도 못 쓰고 서사가 과장됐다는 근거도 약해(유기적 성장 "
        "자체가 실제로 둔화 중) 재무데이터를 추가로 긁지 않고 정량모델에서 "
        "제외한다."
    ),
}

# ── 추가 후보 검토 결과 서사 확인 단계에서 재무데이터 없이 제외 ──
PREFILTERED_OUT["CL(Colgate-Palmolive)"] = (
    "-14%YTD로 완만한 조정(52주 저점 급락이 아님). 서사(북미 매출감소·마진압박"
    "21.1%->19%·관세·소비심리위축)는 실측(EPS -6%, 매출량 정체)과 일치해 "
    "4분류 3번에 가깝다. 다만 근본적으로 **이 스크리너의 MIN_REALISTIC_"
    "GROWTH(8%) 임계값과 구조적으로 안 맞는 종목** - 완숙 소비재 stalwart로 "
    "호황기에도 8%대 성장을 낸 이력이 드물어 공포/실제 구분과 무관하게 "
    "재무데이터를 긁을 실익이 낮다고 판단, 확보 전 제외."
)
PREFILTERED_OUT["AA(Alcoa)/NBIS(Nebius)"] = (
    "AA는 알루미늄 원자재 경기순환주로 NRG(발전설비)와 유사하게 이 프로젝트의 "
    "표준 FCF-DCF 틀과 자본구조가 크게 다른 자본집약 업종. NBIS는 AI인프라 "
    "고성장주(매출 YoY ~280%)이나 상장·재무이력이 5y CAGR 프레임을 채우기엔 "
    "너무 짧다(PODD/APP과 유사한 프레임워크 부적합 소지, 다만 이번엔 확인 전 "
    "단계에서 제외). 둘 다 이번 배치에서는 재무데이터를 확보하지 않았다."
)

# ── 후속 조사(동일 08-14 세션, 사용자 "계속 스크리닝" 요청) - 러셀3000 확장 ──
# Trefis "11 Stocks Hit 52-Week Lows On Thursday"(2026-08-14, Russell 3000
# 전체 대상)에서 ROL/RBA/AGCO(이미 처리 완료) 외 신규 8종목을 확인. 전부 규모·
# 구조·이미 확인된 악화 중 하나의 사유로 정량 스크리닝 이전 단계에서 제외.
PREFILTERED_OUT["GPI(Group 1 Automotive)/UVV(Universal Corp)"] = (
    "각각 자동차 딜러(경기순환 저마진 소매업)·담배잎 공급업체(저성장 성숙산업)"
    "로, CL(Colgate)과 동일하게 이 스크리너의 MIN_REALISTIC_GROWTH(8%) "
    "임계값과 업종 자체가 구조적으로 안 맞는다. 시총도 GPI $4.14B, UVV $1.31B로 "
    "이 프로젝트가 지금까지 다뤄온 종목군 대비 소형이라 확인 전 단계에서 제외."
)
PREFILTERED_OUT["AMSF(AMERISAFE)"] = (
    "산재보험(워커스컴프) 특화 소형 보험사, 시총 $556.82M. is_insurer 경로 "
    "(v3.22, ROE x 유보율 교차검증)가 있지만 지금까지 관측 사례가 ACGL·PGR "
    "단 2건뿐이고 둘 다 대형 종합보험사라, 이 정도 소형 특화보험사에 그대로 "
    "적용할 근거가 약하다고 판단해 확인 전 단계에서 제외."
)
PREFILTERED_OUT["LMB(Limbach Holdings)"] = (
    "52주 고점 대비 -61.1%. WebSearch로 하락원인이 이미 실적으로 확인됨 - "
    "Q2 2026 EPS가 컨센서스 대비 -30.9% 큰 폭 미스, 매출도 소폭 미달($173.5M "
    "vs 컨센서스 $177.3M), 헬스케어·기관시장 마진압박, FY EBITDA 가이던스도 "
    "컨센서스 하회. 서사가 아니라 실적 자체로 악화가 확인돼 4분류 3번(진짜 "
    "나빠짐) 확정, 재무데이터 추가 확보 전 제외."
)
PREFILTERED_OUT["ARDX(Ardelyx)"] = (
    "상업화 초기 제약사(IBSRELA) - OCF가 여전히 마이너스(2026년 상반기 현금 "
    "소진 -39% 개선됐으나 여전히 적자)라 FCF0<=0일 가능성이 매우 높다. "
    "ORCL(2026-08-13 배치)과 동일하게 screener.py 가드상 Model N/A로 즉시 "
    "탈락 처리되는 경우라 재무데이터를 긁을 실익이 없다. 게다가 FY2026 "
    "가이던스도 payer 장벽으로 $410~430M -> $350~370M로 하향 조정돼 서사도 "
    "약화 중 - 확인 전 단계에서 제외."
)
PREFILTERED_OUT["WBTN(WEBTOON Entertainment)/EMAT(Evolution Metals & Technologies)"] = (
    "WBTN은 2024년 IPO로 상장이력이 5y CAGR 프레임을 채우기엔 너무 짧다"
    "(PODD/APP과 동일한 프레임워크 부적합 소지). EMAT는 핵심광물·희토류 "
    "관련 신생 소형주로 하루 만에 +39.38% 급등하는 등 변동성이 극심해 "
    "안정적 재무이력 자체가 부재하다. 둘 다 확인 전 단계에서 제외."
)
# SECZ: WebSearch로 실체를 확인하지 못함(존재하지 않거나 상장폐지 가능성) -
# 추측하지 않고 "확인불가"로 정직하게 남긴다.

# ── 원자료 신뢰도 문제를 SEC XBRL 원자료로 해소했으나, 해소하고 보니 별도의
# 프레임워크 부적합이 드러난 경우 ──
# 1차 조사(UNRESOLVED_DATA_QUALITY)에서 Alpha Vantage·2차출처 불일치로 보류
# 했던 ONON을, SEC data.sec.gov/api/xbrl/companyfacts API(회사가 직접 제출한
# XBRL 구조화 원자료, form=20-F)로 재조회해 해결했다 - HTML 스크레이핑이 아닌
# 구조화 데이터라 출처 간 불일치 문제 자체가 발생하지 않는다.
FRAMEWORK_MISMATCH["ONON(On Holding)"] = (
    "**원자료 신뢰도 문제는 SEC XBRL API(data.sec.gov/api/xbrl/companyfacts, "
    "CIK0001858985)로 해결됐다** - RevenueFromContractsWithCustomers/"
    "CashFlowsFromUsedInOperatingActivities/PurchaseOfPropertyPlantAndEquipment"
    "ClassifiedAsInvestingActivities 태그를 직접 조회한 결과 stockanalysis.com "
    "2차 조회값과 정확히 일치했다(FY2025 매출 CHF 3,014.0M/OCF 359.5M/"
    "capex 72.9M) - Alpha Vantage INCOME_STATEMENT의 FY2025 매출(2,878.5M)"
    "이 부정확했던 것으로 확정. **그런데 정확한 원자료를 확보하고 보니 새로운 "
    "프레임워크 부적합이 드러났다** - FCF(OCF-capex)가 2022년 재고 CHF 273M "
    "급증(급성장기 스케일업, 구조적 악화 아님을 WebSearch로 확인)으로 심각한 "
    "적자(-287.3M)를 기록해, 5y CAGR의 표준 시작점 후보(2020년 FCF -25.7M, "
    "2021년 -7.7M) **둘 다 음수라 CAGR 자체가 정의되지 않는다**(v3.19 가드 "
    "해당 - PODD와 같은 유형이나, PODD의 '다년 연속 적자 후 최초 흑자전환' "
    "단조패턴과 달리 ONON은 '흑자(2021)→급성장통 적자(2022)→흑자 재개' "
    "비단조 패턴이라는 점이 다르다). 유일하게 계산 가능한 건 2023→2025 "
    "2년 CAGR(23.04%)뿐인데 이는 screener.py가 요구하는 5y 기준 임계값과 "
    "정합적이지 않아 그대로 못 쓴다. 매출 자체는 견조(5y CAGR 47.9%, "
    "2025 YoY +30.0%)하고 총마진도 사상최대(65.4%)라 서사(공포과잉)는 여전히 "
    "유효해 보이나, PODD/APP과 동일 원칙으로 5y CAGR 프레임에 억지로 밀어넣지 "
    "않고 정량모델에서 제외한다. **교훈**: 2차 출처 간 불일치가 발견되면 "
    "SEC EDGAR HTML을 직접 스크레이핑하기보다 XBRL companyfacts API를 먼저 "
    "시도할 것 - 문서 전체 파싱(10MB 제한, 리스크팩터 방대) 없이 필요한 "
    "태그만 정확히 뽑을 수 있다."
)


def main():
    print("=" * 108)
    print("2026-08-14 스크리닝 결과")
    print("=" * 108)

    if CANDIDATES:
        results = screen_all(CANDIDATES)
        print(format_table(results))
        n_passed = sum(1 for r in results if r.passed)
        print()
        print(f"통과: {n_passed}/{len(results)}")
        print()
        for r in results:
            c = r.candidate
            status = "PASS" if r.passed else "FAIL"
            print(f"[{c.ticker}] {status}")
            if not r.passed:
                for f in r.failures:
                    print(f"    - {f}")
            for f in r.review_flags:
                print(f"    ⚠️ {f}")
            print(f"    note: {c.note}")
            print()
    else:
        print("이번 배치는 4분류 체크리스트 단계에서 후보 전부 제외됨 - screen() 미호출.")
        print()

    print(f"1차 분류에서 제외된 후보 ({len(PREFILTERED_OUT)}건):")
    for k, v in PREFILTERED_OUT.items():
        print(f"  - {k}: {v}")
    print()
    print(f"프레임워크 부적합으로 정량모델 제외 ({len(FRAMEWORK_MISMATCH)}건):")
    for k, v in FRAMEWORK_MISMATCH.items():
        print(f"  - {k}: {v}")


if __name__ == "__main__":
    main()
