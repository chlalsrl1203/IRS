"""
sec_full_index.py (2026-08-30) — 과거 시점의 **실제 유니버스**를 재구성한다.

## 왜 필요한가 — 생존편향 52.9%

PIT 백테스트(`scripts/pit_backtest.py`)는 유니버스를 `full_ticker_universe()`로
만드는데, 그건 SEC의 **오늘자** `company_tickers.json`이다. 그래서 T0 이후
상장폐지·인수·등록말소된 회사는 **애초에 채점 대상이 되지 못한다** — 그리고
하필 그 집단이 성과가 나빴던 쪽이다.

2026-08-30 실측:

    T0=2018-06-30 직전 12개월 연차보고서 제출 CIK : 7,784개
    그중 오늘자 SEC 티커목록에 없는 CIK           : 4,118개 (52.9%)

즉 백테스트가 볼 수 있었던 것은 그 시점 공시기업의 절반뿐이다. (4,118개
전부가 "폐지된 상장사"는 아니다 — 티커를 가진 적 없는 사모·펀드 필자도
섞여 있다. 그래도 "백테스트가 구조적으로 못 보는 집단"의 크기로는 정확하다.)

⚠️ 이건 `pit_price_validation.py`가 세던 "가격 확보 실패"(flagged 0건)와
**다른 층위**라 리포트상 전혀 보이지 않았다: 그쪽은 "유니버스에 들어온 뒤
가격을 못 구한 종목", 이쪽은 "유니버스에 애초에 못 들어온 종목".

## 왜 이름 매칭이 아니라 full-index인가

Alpha Vantage `LISTING_STATUS`는 폐지 종목의 **심볼과 이름**은 주지만 CIK를
주지 않는다. SEC `cik-lookup-data.txt`로 이름 매칭을 시도해봤으나 단일 CIK로
확정되는 비율이 **65.9%**뿐이었다(모호 18.2%, 미매칭 15.9%) — 이 프로젝트가
TYL·다우존스30 사례에서 반복 확인한 "이름이 비슷하다고 같은 것이 아니다"
문제가 그대로 걸린다.

full-index는 **CIK를 직접** 담고 있어 매칭이 아예 필요 없다. 게다가 이
스크리너가 실제로 요구하는 조건("연차 재무제표가 그 시점에 존재했는가")과
정의상 일치한다 — 연차보고서를 낸 기업만 들어오므로.

## ⚠️ 이 모듈이 해결하지 못하는 것 — 폐지 종목의 주가

유니버스는 바로잡을 수 있지만, 폐지된 회사의 **주가 시계열은 여전히 못
구한다**(stockanalysis.com은 상장 종목만 제공하고, 폐지 종목 가격은 유료
데이터). 따라서 이 모듈만으로 성과 편향이 완전히 사라지지는 않는다 -
대신 "폐지된 flagged 종목이 몇 개인가"를 셀 수 있게 되므로, 최악(-100%)·
최선(인수 프리미엄) 가정으로 **성과를 구간으로 묶는** 것이 가능해진다.
그게 이 데이터로 도달 가능한 정직한 한계다.
"""
import re
import time

from engine.filing_dates import ANNUAL_FORMS, _http_text

FULL_INDEX_URL = (
    "https://www.sec.gov/Archives/edgar/full-index/{year}/QTR{qtr}/company.idx"
)

# company.idx 줄 형식은 고정폭이다: 회사명(62) 서식(12) CIK 제출일 파일경로.
# 회사명에 공백·콜론이 자유롭게 들어가므로 고정폭으로 잘라야 안전하다.
_LINE_RE = re.compile(r"^(.{62})(.{12})\s*(\d+)\s+(\d{4}-\d{2}-\d{2})")


def quarter_index_url(year, qtr):
    return FULL_INDEX_URL.format(year=year, qtr=qtr)


def parse_company_idx(text, forms=ANNUAL_FORMS):
    """
    company.idx 본문 -> {CIK(10자리): (회사명, 최신 제출일)}.

    `forms` 기본값은 `ANNUAL_FORMS` **그대로 재사용**한다 - 스크리너가 읽는
    서식과 유니버스 정의가 어긋나면 "재무제표가 없는데 유니버스에는 있는"
    기업이 생긴다(집합을 복제하지 않는 이유는 sec_daily_index와 동일).
    """
    out = {}
    for line in text.splitlines():
        m = _LINE_RE.match(line)
        if not m:
            continue
        if m.group(2).strip() not in forms:
            continue
        cik = m.group(3).zfill(10)
        name, filed = m.group(1).strip(), m.group(4)
        prev = out.get(cik)
        if prev is None or filed > prev[1]:
            out[cik] = (name, filed)
    return out


def _quarters_back(as_of, n=4):
    """as_of가 속한 분기부터 과거로 n개 분기의 (year, qtr) 목록."""
    y, m = int(as_of[:4]), int(as_of[5:7])
    q = (m - 1) // 3 + 1
    out = []
    for _ in range(n):
        out.append((y, q))
        q -= 1
        if q == 0:
            q, y = 4, y - 1
    return list(reversed(out))


def universe_at(as_of, user_agent=None, fetch_text=None, quarters=4,
                delisted_before=None, retries=3, allow_partial=False):
    """
    T0 시점에 **연차 재무제표가 존재했던** 기업 전체.

    반환 {CIK: {"name":…, "last_annual_filed":…}}. 기본 4개 분기(=직전 12개월)를
    훑는다 - 연차보고서는 1년에 한 번이므로 그보다 좁으면 회계연도 종료월이
    다른 기업이 통째로 빠진다.

    ⚠️ `filed <= as_of`인 항목만 채택한다. 분기 파일에는 as_of 이후 제출분도
    섞여 있으므로 그대로 쓰면 미래정보가 유니버스 정의에 들어온다.

    ⚠️ **`delisted_before`는 T0 이전에 이미 상장폐지된 기업을 빼는 데 쓴다.**
    초판에는 이 인자가 없었고, 그래서 2026-08-30 파일럿에서 실제로 잘못
    들어온 사례가 나왔다 - WESTMORELAND COAL(폐지 2018-04-24)과 MICROSEMI
    (폐지 2018-05-29)가 T0=2018-06-30 유니버스에 포함됐다. 둘 다 직전 12개월
    안에 10-K를 냈지만 **T0 시점엔 이미 살 수 없는 종목**이었다.
    "그 시점에 재무제표가 있었는가"와 "그 시점에 투자 가능했는가"는 다른
    질문이고, 유니버스는 후자여야 한다.

    `delisted_before`는 {티커나 CIK: 폐지일} 형태가 아니라 **이미 걸러진 CIK
    집합**을 받는다 - 폐지 정보의 출처(Alpha Vantage LISTING_STATUS는 CIK를
    주지 않는다)에 이 모듈이 의존하지 않게 하기 위해서다. 매핑은 호출부 책임.
    """
    fetch_text = fetch_text or (lambda url: _http_text(url, user_agent))
    merged, failed = {}, []
    for year, qtr in _quarters_back(as_of, quarters):
        text = None
        for attempt in range(retries):
            try:
                text = fetch_text(quarter_index_url(year, qtr))
                break
            except Exception as e:  # noqa: BLE001 - 사유를 살려 보낸다
                last = e
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)
        if text is None:
            failed.append((f"{year}Q{qtr}", repr(last)))
            continue
        for cik, (name, filed) in parse_company_idx(text).items():
            if filed > as_of:
                continue                      # 미래 제출분 배제
            prev = merged.get(cik)
            if prev is None or filed > prev["last_annual_filed"]:
                merged[cik] = {"name": name, "last_annual_filed": filed}
    # ⚠️ **부분 실패를 조용히 삼키지 않는다.** 초판은 한 분기가 실패해도 그냥
    # 넘어갔는데, 2026-08-30 T0=2022 실행에서 실제로 그 일이 났다 - 유니버스가
    # 2,867개(다른 T0는 ~7,500)로 40% 수준까지 쪼그라들었는데 **출력에는 아무
    # 표시가 없었다.** 재조회해보니 네 분기 전부 HTTP 200이라 일시적 실패였다.
    # 이 프로젝트가 반복해서 잡아온 "인프라 장애가 정상 결과와 구별되지 않는"
    # 패턴(v3.68)이 그대로 재현된 것이다. 재시도 후에도 실패하면 예외를 던진다.
    if failed and not allow_partial:
        raise RuntimeError(
            f"full-index 분기 조회 실패로 유니버스가 불완전하다({as_of}): {failed}. "
            f"불완전한 채로 진행하려면 allow_partial=True를 명시할 것 - 그 경우 "
            f"유니버스가 실제보다 작아져 '사라진 기업' 집계가 과소평가된다.")
    if delisted_before:
        merged = {c: v for c, v in merged.items() if c not in delisted_before}
    return merged
