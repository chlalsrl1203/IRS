"""
SEC Financial Statement Data Sets 리더 — 차원(dimension) 사실을 stdlib로 (v3.99, 2026-10-10)

## 왜 필요한가

companyfacts(`data.sec.gov/api/xbrl/companyfacts`)는 **무차원 사실만** 담는다. 그래서
주식 클래스별(ClassOfStock=…)·세그먼트별(BusinessSegments=…, ProductOrService=…) 값이
통째로 빠진다. v3.85는 이 때문에 ERIE·HLNE·RYAN 희석을 "원리적으로 못 가져온다"고
기록했다 — companyfacts에 한해서만 참이었다(2026-10-09 조사,
`docs/opensource_qualitative_2026-10-09.md`).

같은 SEC가 분기마다 내는 Financial Statement Data Sets(`sub.txt`·`num.txt`, 탭 구분
텍스트 zip)에는 2024-12 재처리 이후 `segments` 열이 있고, 과거 분기(2023q1 실측)에도
채워져 있다. 이 모듈은 그 파일을 **외부 라이브러리 없이** 읽는다.

참조 구현 `HansjoergW/sec-fincancial-statement-data-set`(secfsdstools, Apache-2.0)은
pandas·numpy·pyarrow·pandera 등 8개에 의존한다 — 코드를 가져오지 않고 파일 형식만
SEC 문서대로 다시 읽는다(REIMPLEMENT).

## 하는 것 / 하지 않는 것

- 순수 함수만 둔다. 다운로드·캐시는 호출부(`scripts/fsds_extract.py`)가 한다.
- 값을 고르거나 해석하지 않는다. "어느 클래스를 경제적 총주식수로 볼 것인가"는
  `as_converted_share_series()`의 **회사 자신의 EPS로 증명되는 경우에만** 답한다.
- 판정·점수 함수가 없다(테스트로 고정). `run_analysis()`·포트폴리오에 미배선.
"""

import csv
import io
import zipfile

QUARTER_URL = ("https://www.sec.gov/files/dera/data/financial-statement-data-sets/"
               "{year}q{q}.zip")

ANNUAL_FORMS = ("10-K", "10-K/A", "20-F", "20-F/A", "40-F", "40-F/A")

# 주식수·EPS 검증에 필요한 태그(무차원·클래스별 모두 받는다).
SHARE_TAGS = (
    "WeightedAverageNumberOfDilutedSharesOutstanding",
    "WeightedAverageNumberOfSharesOutstandingBasic",
    "EarningsPerShareDiluted",
    "NetIncomeLoss",
    "ProfitLoss",
    "NetIncomeLossAttributableToNoncontrollingInterest",
    "CommonStockSharesOutstanding",
)

REVENUE_TAGS = (
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "Revenues",
    "SalesRevenueNet",
    "RevenueFromContractWithCustomerIncludingAssessedTax",
    # IFRS(20-F) 발행사 — FSDS의 tag 열은 접두어 없는 이름이라 ifrs-full 태그도 이렇게 온다
    "Revenue",
    "RevenueFromContractsWithCustomers",
)

# 세그먼트 대조에 쓰는 축. 지역(Geographical)은 사업 분리가 아니라 쓰지 않는다.
SEGMENT_AXES = ("BusinessSegments", "ProductOrService")

# EPS x 희석주식수 가 회사 전체 순이익을 이만큼 안에서 재현해야 그 클래스의 희석
# 주식수를 "회사 전체의 전환가정 주식수"로 인정한다. EPS가 센트 단위로 반올림되므로
# (예: 5.61의 반올림 오차 0.09%) 1%면 반올림은 통과하고 클래스 혼동은 걸린다.
# ⚠️ 사전 고정값 — 결과를 보고 조정하지 말 것.
EPS_RECONCILE_TOL = 0.01

# 비지배지분(NCI)이 순이익의 이 비율을 넘으면 Up-C·자회사 구조로 보고 거부한다.
# 상장 클래스의 주식수가 늘어도 그것이 LLC 유닛 교환(지분 이동)인지 희석인지
# 구분할 수 없기 때문이다(RYAN `CommonUnitsExchangedForCommonStockShares` 실측).
NCI_TOL = 0.01

VALIDATION_STATUS = {
    "fsds_reader": "IMPLEMENTED_NOT_VALIDATED",
    "as_converted_share_series": "IMPLEMENTED_NOT_VALIDATED",
    "segment_revenue": "IMPLEMENTED_NOT_VALIDATED",
}


def quarter_of(iso_date: str):
    """제출일(YYYY-MM-DD 또는 YYYYMMDD) -> (연도, 분기)."""
    d = iso_date.replace("-", "")
    return int(d[:4]), (int(d[4:6]) - 1) // 3 + 1


def parse_segments(s: str) -> dict:
    """'ClassOfStock=CommonClassA;EquityComponents=X;' -> {'ClassOfStock': 'CommonClassA', ...}."""
    out = {}
    for part in (s or "").split(";"):
        if "=" in part:
            k, v = part.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def _reader(fh):
    csv.field_size_limit(1 << 30)
    return csv.DictReader(io.TextIOWrapper(fh, encoding="utf-8", errors="replace"),
                          delimiter="\t")


def read_submissions(lines_or_fh, ciks, forms=ANNUAL_FORMS) -> dict:
    """sub.txt -> {adsh: {...}} (대상 CIK·양식만). `ciks`는 앞자리 0 없는 문자열 집합."""
    want = {str(int(c)) for c in ciks}
    out = {}
    rows = lines_or_fh if isinstance(lines_or_fh, csv.DictReader) else _reader(lines_or_fh)
    for r in rows:
        if r.get("cik") in want and r.get("form") in forms:
            out[r["adsh"]] = {k: r.get(k) for k in
                              ("adsh", "cik", "name", "form", "period", "fy", "fp", "filed")}
    return out


def read_num(lines_or_fh, adsh_set, tags) -> list:
    """num.txt에서 대상 공시·태그만. 연결대상(coreg) 행은 버린다(자회사 단독 수치)."""
    tags = set(tags)
    out = []
    rows = lines_or_fh if isinstance(lines_or_fh, csv.DictReader) else _reader(lines_or_fh)
    for r in rows:
        if r.get("adsh") in adsh_set and r.get("tag") in tags and not r.get("coreg"):
            try:
                val = float(r["value"])
            except (TypeError, ValueError):
                continue
            out.append({"adsh": r["adsh"], "tag": r["tag"], "ddate": r["ddate"],
                        "qtrs": int(r["qtrs"] or 0), "segments": parse_segments(r["segments"]),
                        "value": val})
    return out


def read_quarter_zip(path, ciks, tags) -> tuple:
    """분기 zip 하나 -> (submissions, num rows). 파일 전체를 메모리에 올리지 않는다."""
    with zipfile.ZipFile(path) as z:
        with z.open("sub.txt") as f:
            subs = read_submissions(f, ciks)
        with z.open("num.txt") as f:
            rows = read_num(f, set(subs), tags)
    return subs, rows


def _year(ddate: str) -> int:
    return int(ddate[:4])


def latest_by_period(subs, rows, cik, tag, qtrs, segment_filter):
    """{ddate: (filed, value)} — 같은 기간이 여러 공시본에 있으면 **최신 공시본**.

    소급재표시(분할 등)가 있으면 최신 공시본이 하나의 일관된 기준이다(dilution.py와
    같은 규칙). `segment_filter(segdict) -> bool`.
    """
    cik = str(int(cik))
    out = {}
    for r in rows:
        s = subs.get(r["adsh"])
        if not s or s["cik"] != cik or r["tag"] != tag or r["qtrs"] != qtrs:
            continue
        if not segment_filter(r["segments"]):
            continue
        prev = out.get(r["ddate"])
        if prev is None or s["filed"] > prev[0]:
            out[r["ddate"]] = (s["filed"], r["value"])
    return out


def _no_seg(seg):
    return not seg


def _class_is(name):
    return lambda seg: set(seg) == {"ClassOfStock"} and seg["ClassOfStock"] == name


def share_classes(subs, rows, cik) -> list:
    """희석 가중평균 주식수가 보고된 클래스 목록."""
    cik = str(int(cik))
    out = set()
    for r in rows:
        s = subs.get(r["adsh"])
        if (s and s["cik"] == cik and r["tag"] == "WeightedAverageNumberOfDilutedSharesOutstanding"
                and set(r["segments"]) == {"ClassOfStock"}):
            out.add(r["segments"]["ClassOfStock"])
    return sorted(out)


def as_converted_share_series(subs, rows, cik) -> dict:
    """회사 전체의 '전환가정' 희석 주식수 시계열 — **회사 자신의 EPS로 증명될 때만**.

    다중클래스 회사에서 어느 클래스의 주식수가 주주 지분 전체를 대표하는지는 일반
    규칙으로 정할 수 없다(ERIE Class B는 2,400:1 전환, Up-C의 Class B는 경제권 없음).
    그래서 추측하지 않고 다음이 **모든 연도에서** 성립하는 클래스만 받는다:

        EPS_diluted[class] x WeightedDilutedShares[class] ≈ NetIncomeLoss(회사 전체)

    이는 회사가 그 클래스의 희석 주식수를 회사 전체 순이익의 분모로 썼다는 뜻이다
    (ERIE: Class A 희석 = 기본 46.19M + Class B 2,542 x 2,400 = 52.29M — 실측 일치).

    거부 조건(보수적):
      - 비지배지분 순이익이 순이익의 1%를 넘는 해가 있음 → Up-C 등에서 상장 클래스
        증가가 유닛 교환인지 희석인지 구분 불가
      - 조건을 만족하는 클래스가 0개이거나 2개 이상 → 특정 불가
      - 한 해라도 EPS·순이익이 없어 검증할 수 없음 → 그 해는 시계열에서 뺀다

    반환: {"status", "class", "series": {연도: 주식수}, "checks": [...], "detail"}
    """
    classes = share_classes(subs, rows, cik)
    if not classes:
        return {"status": "NO_CLASS_SHARES", "series": {},
                "detail": "클래스별 희석 가중평균 주식수가 데이터셋에 없다"}

    ni = latest_by_period(subs, rows, cik, "NetIncomeLoss", 4, _no_seg)
    pl = latest_by_period(subs, rows, cik, "ProfitLoss", 4, _no_seg)
    nci = latest_by_period(subs, rows, cik,
                           "NetIncomeLossAttributableToNoncontrollingInterest", 4, _no_seg)
    if not ni:
        return {"status": "NO_NET_INCOME", "series": {}, "classes": classes,
                "detail": "회사 전체 NetIncomeLoss가 없어 클래스를 검증할 수 없다"}

    nci_years = []
    for d, (_f, v) in ni.items():
        nci_v = nci.get(d, (None, None))[1]
        if nci_v is None and d in pl:
            nci_v = pl[d][1] - v
        if nci_v is not None and v and abs(nci_v) > NCI_TOL * abs(v):
            nci_years.append(_year(d))
    if nci_years:
        return {"status": "NCI_PRESENT", "series": {}, "classes": classes,
                "detail": (f"비지배지분 순이익이 순이익의 {NCI_TOL:.0%}를 넘는 해 "
                           f"{sorted(set(nci_years))} — Up-C·자회사 구조에서는 상장 클래스 "
                           "주식수 증가가 유닛 교환(지분 이동)인지 희석인지 구분할 수 없다")}

    passing = {}
    checks = []
    for c in classes:
        sh = latest_by_period(subs, rows, cik, "WeightedAverageNumberOfDilutedSharesOutstanding",
                              4, _class_is(c))
        eps = latest_by_period(subs, rows, cik, "EarningsPerShareDiluted", 4, _class_is(c))
        ok_years, bad = {}, []
        for d, (_f, n) in sh.items():
            if d not in eps or d not in ni or not ni[d][1]:
                continue
            implied = eps[d][1] * n
            err = abs(implied / ni[d][1] - 1.0)
            checks.append({"class": c, "fy": _year(d), "eps": eps[d][1], "shares": n,
                           "net_income": ni[d][1], "rel_err": err})
            if err <= EPS_RECONCILE_TOL:
                ok_years[_year(d)] = n
            else:
                bad.append(_year(d))
        if ok_years and not bad:
            passing[c] = ok_years

    if len(passing) != 1:
        return {"status": "CLASS_UNRESOLVED", "series": {}, "classes": classes,
                "checks": checks,
                "detail": (f"EPS x 주식수가 회사 순이익을 재현하는 클래스가 {len(passing)}개 "
                           "— 경제적 총주식수를 대표하는 클래스를 특정할 수 없다")}
    (c, series), = passing.items()
    return {"status": "OK", "class": c, "series": series, "classes": classes,
            "checks": [x for x in checks if x["class"] == c],
            "detail": (f"{c} 희석 주식수 x 희석 EPS가 모든 연도에서 회사 순이익을 "
                       f"{EPS_RECONCILE_TOL:.0%} 안에서 재현 — 전환가정 총주식수로 채택")}


def segment_revenue(subs, rows, cik, tags=REVENUE_TAGS) -> dict:
    """{축: {구성원: {연도: 매출}}} — 단일 축으로만 쪼갠 연차 매출, 최신 공시본 기준.

    두 축 이상이 섞인 행(예: ProductOrService + RelatedParty)은 버린다 — 합산 관계가
    보장되지 않는다. 태그는 우선순위대로 하나만 쓴다(같은 구성원에 두 태그가 섞이면
    정의가 달라질 수 있다).
    """
    cik = str(int(cik))
    out = {}
    for axis in SEGMENT_AXES:
        for tag in tags:
            got = {}
            for r in rows:
                s = subs.get(r["adsh"])
                if (not s or s["cik"] != cik or r["tag"] != tag or r["qtrs"] != 4
                        or set(r["segments"]) != {axis}):
                    continue
                m = r["segments"][axis]
                prev = got.setdefault(m, {}).get(r["ddate"])
                if prev is None or s["filed"] > prev[0]:
                    got[m][r["ddate"]] = (s["filed"], r["value"])
            if got:
                out[axis] = {"tag": tag, "members": {
                    m: {_year(d): v for d, (_f, v) in sorted(per.items())}
                    for m, per in sorted(got.items())}}
                break
    return out


def consolidated_revenue(subs, rows, cik, tags=REVENUE_TAGS) -> dict:
    """무차원 연차 매출 {연도: 값} (세그먼트 합계 대조용)."""
    for tag in tags:
        got = latest_by_period(subs, rows, cik, tag, 4, _no_seg)
        if got:
            return {"tag": tag, "by_year": {_year(d): v for d, (_f, v) in sorted(got.items())}}
    return {"tag": None, "by_year": {}}
