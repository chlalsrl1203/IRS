"""
실전 트랙레코드 - 이 시스템의 판정이 실제로 뭘 예측했는지 계속 쌓는다
(2026-09-18 신설).

## 왜 이게 이 프로젝트의 병목인가

CLAUDE.md 전체에 같은 문장이 반복된다 - "실현결과와의 관계 증거가 **0건**
이다". growth_quality(v3.53)·accounting_quality(v3.70)·dilution(v3.84)이
전부 계산은 되지만 판정에 배선되지 않은 이유가 이 하나이고, Confidence가
`UNCALIBRATED`인 이유도, H-001~H-006이 BLOCKED인 이유도 같다.

v3.73~v3.78의 PIT 백테스트는 **합성**(과거로 되돌아가 재구성)이었다.
이 모듈은 다르다 - v3.24 `price_at_analysis`가 실제로 채워지기 시작한
뒤부터, **우리가 그날 실제로 내린 판정**과 그 이후 실제 주가를 대조한다.
한 번 재보고 끝내면 의미가 없고(2026-09-18 1차 측정이 그랬다), 주기적으로
쌓여야 몇 달 뒤 진짜 표본이 된다.

## 무엇을 하지 않는가

- **판정을 바꾸지 않는다.** `ledger/`에 쓰지 않고 `reports/`에만 남긴다
  (v3.42 원칙). 이 측정값이 Gap·등급·Confidence에 되먹임되지 않는다.
- **결론을 내지 않는다.** 표본이 수십 건·수 주 단위인 동안 여기서 나오는
  숫자는 방향성 참고용이다. 사전등록된 실험(`experiments/`)을 대체하지
  않으며, 그 실험들의 exit_rule(H-006은 최소 15건)을 우회하는 근거로도
  쓰지 않는다.

## 수익률 정의 - 배당조정 시계열 안에서만 계산한다

ledger의 `price_at_analysis`는 그날의 **원종가**다. 현재가를 조정종가로
잡고 원종가로 나누면 그 사이 배당만큼 조용히 틀린다. 그래서 진입·청산
둘 다 **같은 조정 시계열**에서 뽑고, ledger에 기록된 원종가는 별도로
그날 원종가와 대조해 데이터 무결성 점검에만 쓴다(불일치하면 숨기지 않고
`price_mismatch`로 드러낸다).
"""
import datetime
import glob
import json
import os
import statistics

# 5년치 일봉. `range=1M`을 넣어도 서버가 1년치를 주는 것을 실측 확인했고
# (2026-09-18), 코호트가 늙어도 진입일이 시계열 안에 남아야 하므로 5Y로
# 넉넉히 잡는다.
PRICE_API = ("https://stockanalysis.com/api/symbol/s/{sym}/history"
             "?range=5Y&period=Daily")
USER_AGENT = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/120 Safari/537.36")

# 무료 공개 서비스를 연속 호출하므로 자발적으로 간격을 둔다
# (pit_price_validation.py가 쓰는 값과 동일).
REQUEST_INTERVAL_SEC = 0.7

# ledger 원종가와 시계열 원종가의 허용 오차. 이걸 넘으면 둘 중 하나가
# 틀린 것이므로 조용히 계산하지 않고 드러낸다.
LEDGER_PRICE_TOLERANCE = 0.005

# 이 프로젝트의 단위 규약 - 통화가 섞이면 조용히 틀린다(RAR 100배·실질/명목
# EPS 사고와 같은 계열). 가격 출처가 USD 기준이므로 USD 표기 ledger만 쓴다.
SUPPORTED_CURRENCY = "USD"


def collect_cohort(ledger_dir="ledger"):
    """
    `price_at_analysis`가 채워진 ledger를 모은다(순수 함수).

    반환: (cohort, skipped) - skipped는 왜 빠졌는지 사유를 갖는다
    ("데이터 없음"을 조용히 0건으로 만들지 않는다는 이 프로젝트의 원칙).
    """
    cohort, skipped = [], []
    for path in sorted(glob.glob(os.path.join(ledger_dir, "*.json"))):
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        meta = d.get("meta", {})
        ticker = meta.get("ticker")
        price = meta.get("price_at_analysis")
        analyzed_at = meta.get("analyzed_at")
        currency = meta.get("currency", SUPPORTED_CURRENCY)

        if price is None or not analyzed_at:
            skipped.append({"ticker": ticker, "ledger": os.path.basename(path),
                            "reason": "price_at_analysis 또는 analyzed_at 없음"})
            continue
        if currency != SUPPORTED_CURRENCY:
            skipped.append({"ticker": ticker, "ledger": os.path.basename(path),
                            "reason": f"통화가 {currency} - USD 가격 시계열과 "
                                      f"섞으면 조용히 틀린다"})
            continue

        cohort.append({
            "ticker": ticker,
            "ledger": os.path.basename(path),
            "analyzed_at": str(analyzed_at),
            "analysis_date": str(analyzed_at)[:10],
            "price_at_analysis": float(price),
            "currency": currency,
            "judgment": d.get("judgment"),
            "judgment_grade": d.get("judgment_grade"),
            "expectation_gap": d.get("expectation_gap"),
        })
    return cohort, skipped


def parse_series(payload):
    """
    가격 API 응답 -> {날짜: {"close": float, "adj": float}}.

    ⚠️ 정렬순서를 신뢰하지 않는다. 이 API는 `range=1M`을 줘도 1년치를
    **최신순(내림차순)**으로 돌려준다 - 2026-09-18 1차 측정에서 `raw[-1]`을
    "최신"으로 가정했다가 1년 전 종가를 채택해 BSX +92%/MNDY +116% 같은
    결과가 나왔었다. 날짜를 키로 쓰면 순서 가정 자체가 사라진다.
    """
    raw = payload.get("data")
    if isinstance(raw, dict):
        raw = raw.get("data")
    if not raw:
        return {}
    out = {}
    for row in raw:
        date, close, adj = row.get("t"), row.get("c"), row.get("a")
        if not date or close is None:
            continue
        out[date] = {"close": float(close),
                     "adj": float(adj if adj is not None else close)}
    return out


def fetch_daily_series(ticker, opener=None):
    """
    일봉 시계열을 받는다. 실패하면 (None, 사유) - 사유를 살려 보낸다(v3.68).

    opener: `urlopen`과 같은 시그니처의 호출가능 객체. 테스트에서 주입해
    네트워크 없이 검증한다.
    """
    import urllib.parse
    import urllib.request

    opener = opener or urllib.request.urlopen
    url = PRICE_API.format(sym=urllib.parse.quote(ticker.lower()))
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with opener(req, timeout=20) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except Exception as e:  # noqa: BLE001
        return None, f"조회 실패: {e!r}"

    series = parse_series(payload)
    if not series:
        return None, "가격 시계열 없음(상장폐지·인수합병·심볼 변경 가능)"
    return series, None


def price_on_or_before(series, date_str):
    """
    해당 날짜 또는 그 이전 가장 가까운 거래일. 분석일이 주말·휴장일이면
    직전 거래일을 쓴다(분석 시점에 볼 수 있었던 마지막 가격).
    """
    candidates = [d for d in series if d <= date_str]
    if not candidates:
        return None, None
    d = max(candidates)
    return d, series[d]


# 미국 정규장 마감(현지 16:00). DST는 zoneinfo(stdlib)가 처리한다 -
# 여름 20:00 UTC / 겨울 21:00 UTC로 한 시간 밀리는데, 이걸 상수 하나로
# 고정하면 계절에 따라 하루씩 어긋난다.
US_MARKET_CLOSE_LOCAL = datetime.time(16, 0)
US_MARKET_TZ = "America/New_York"


def entry_bar_as_known_at(series, analyzed_at_iso):
    """
    **분석 시각에 실제로 알 수 있었던** 마지막 종가를 고른다(순수 함수).

    ⚠️ 이게 필요한 이유를 실측으로 확인했다(2026-09-18). ledger의
    `analyzed_at`은 UTC 타임스탬프인데, 이 프로젝트의 분석은 대부분 한국
    시간 기준 오전(= UTC 01~11시 = 미국 동부 전일 21시~당일 07시,
    **개장 전**)에 돌았다. 그래서 그 시각에 쓴 `price_at_analysis`는
    그날 종가가 아니라 **직전 거래일 종가**다:

        ADBE  analyzed_at 09-04 09:24 UTC(개장 전) -> ledger 285.75 = 09-03 종가
        VRT   analyzed_at 09-04 23:02 UTC(마감 후) -> ledger 280.53 = 09-04 종가

    날짜만 보고 그날 종가를 진입가로 쓰면 하루치가 통째로 어긋난다.
    """
    from zoneinfo import ZoneInfo

    # 시각 없이 날짜만 있으면 "그날 종가"로 읽는다 - 시점을 모르는데 개장
    # 전이라고 가정하면 그것도 추측이다. (실제 ledger는 전부 타임스탬프를
    # 갖고 있어 이 경로는 합성 입력에만 해당된다.)
    if len(analyzed_at_iso) == 10:
        return price_on_or_before(series, analyzed_at_iso)

    dt = datetime.datetime.fromisoformat(analyzed_at_iso.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    local = dt.astimezone(ZoneInfo(US_MARKET_TZ))
    cal_date = local.date().isoformat()

    if local.time() >= US_MARKET_CLOSE_LOCAL:
        # 마감 후 - 그날 종가를 이미 알 수 있다
        return price_on_or_before(series, cal_date)
    # 마감 전 - 그날 종가는 아직 없다. 직전 거래일까지만.
    prior = [d for d in series if d < cal_date]
    if not prior:
        return None, None
    d = max(prior)
    return d, series[d]


def measure(entry, series):
    """
    한 종목의 진입->현재 수익률(순수 함수).

    **배당조정 시계열 안에서만** 계산한다 - ledger의 원종가는 무결성
    점검용으로만 쓴다.
    """
    row = dict(entry)
    analyzed_at = entry.get("analyzed_at") or entry["analysis_date"]
    entry_date, entry_bar = entry_bar_as_known_at(series, analyzed_at)
    if entry_bar is None:
        row["error"] = (f"분석일({entry['analysis_date']}) 이전 가격이 시계열에 "
                        f"없음(상장이 분석일보다 늦거나 시계열이 짧음)")
        return row

    latest_date = max(series)
    if latest_date <= entry_date:
        row["error"] = f"분석일 이후 거래일 없음(최신 {latest_date})"
        return row

    latest_bar = series[latest_date]
    row["entry_date_used"] = entry_date
    row["entry_close"] = entry_bar["close"]
    row["entry_adj"] = entry_bar["adj"]
    row["latest_date"] = latest_date
    row["latest_close"] = latest_bar["close"]
    row["latest_adj"] = latest_bar["adj"]
    row["days_held"] = (datetime.date.fromisoformat(latest_date)
                        - datetime.date.fromisoformat(entry_date)).days
    row["return_pct"] = (latest_bar["adj"] / entry_bar["adj"] - 1.0) * 100.0

    # ledger에 적힌 원종가가 그날 실제 원종가와 같은가(무결성 점검).
    ledger_price = entry["price_at_analysis"]
    delta = abs(entry_bar["close"] - ledger_price) / max(abs(ledger_price), 1e-9)
    row["ledger_price_delta_pct"] = delta * 100.0
    row["price_mismatch"] = delta > LEDGER_PRICE_TOLERANCE
    if row["price_mismatch"]:
        # 어긋났으면 "얼마나"가 아니라 **어느 날 종가였는지**를 알려준다 -
        # 실측 6건이 전부 "1~2거래일 묵은 시세를 썼다"로 설명됐다(2026-09-18).
        row["ledger_price_traced_to"] = trace_ledger_price(
            series, ledger_price, entry_date)
    return row


def trace_ledger_price(series, ledger_price, entry_date, lookback_days=10):
    """
    ledger에 적힌 가격이 **어느 거래일 종가였는지** 역추적한다(순수 함수).

    못 찾으면 None - 추측해서 채우지 않는다. 찾으면 진입일 대비 며칠 전
    시세였는지까지 돌려줘서 "묵은 시세를 썼다"를 구체적으로 말할 수 있게 한다.
    """
    window = sorted(d for d in series if d <= entry_date)[-lookback_days:]
    best = None
    for d in window:
        delta = abs(series[d]["close"] - ledger_price) / max(abs(ledger_price), 1e-9)
        if delta <= LEDGER_PRICE_TOLERANCE and (best is None or delta < best[1]):
            best = (d, delta)
    if best is None:
        return None
    matched_date, delta = best
    trading_days_stale = len([d for d in window if matched_date < d <= entry_date])
    return {"date": matched_date,
            "trading_days_before_entry": trading_days_stale,
            "delta_pct": round(delta * 100.0, 3)}


def bucket_stats(rows, key):
    """버킷별 수익률 요약(순수 집계 - 어떤 판정도 하지 않는다)."""
    buckets = {}
    for r in rows:
        buckets.setdefault(r.get(key), []).append(r["return_pct"])
    out = {}
    for k, vals in buckets.items():
        out[k] = {
            "n": len(vals),
            "median_return_pct": round(statistics.median(vals), 2),
            "mean_return_pct": round(statistics.mean(vals), 2),
            "min_return_pct": round(min(vals), 2),
            "max_return_pct": round(max(vals), 2),
            "pct_positive": round(sum(1 for v in vals if v > 0) / len(vals) * 100, 1),
        }
    return out


GRADE_ORDER = ("S", "A", "B", "C", "D", "F")

# 이 측정의 인식론적 지위. v3.46 VALIDATION_STATUS와 같은 어휘를 쓴다.
MEASUREMENT_STATUS = (
    "OBSERVATIONAL_NOT_INFERENTIAL - 실제 관측이지만 사전등록된 실험이 아니다. "
    "표본·보유기간이 충분해지기 전까지 여기서 나온 숫자는 방향성 참고용이며, "
    "판정·사이징·Confidence 어디에도 되먹임되지 않는다."
)


def build_report(measured, failures, skipped, as_of, price_source):
    """측정 결과를 리포트 dict로. 실패·제외 건수를 항상 함께 낸다."""
    ok = [r for r in measured if "error" not in r]
    errored = [r for r in measured if "error" in r]
    returns = [r["return_pct"] for r in ok]
    days = [r["days_held"] for r in ok]
    mismatches = [r for r in ok if r.get("price_mismatch")]

    return {
        "as_of": as_of,
        "measurement_status": MEASUREMENT_STATUS,
        "price_source": price_source,
        "return_definition": (
            "배당조정 종가 기준 총수익률(진입·청산 둘 다 같은 조정 시계열에서 "
            "뽑는다). ledger의 price_at_analysis는 무결성 점검용으로만 쓴다."
        ),
        "n_cohort": len(measured) + len(failures),
        "n_measured": len(ok),
        "n_error": len(errored) + len(failures),
        "n_skipped_from_ledgers": len(skipped),
        "n_price_mismatch": len(mismatches),
        "horizon_days": {
            "min": min(days) if days else None,
            "max": max(days) if days else None,
            "median": round(statistics.median(days), 1) if days else None,
        },
        "overall": {
            "median_return_pct": round(statistics.median(returns), 2) if returns else None,
            "mean_return_pct": round(statistics.mean(returns), 2) if returns else None,
            "pct_positive": round(sum(1 for v in returns if v > 0) / len(returns) * 100, 1) if returns else None,
        },
        "by_judgment_grade": bucket_stats(ok, "judgment_grade"),
        "by_judgment": bucket_stats(ok, "judgment"),
        "rows": ok,
        "errors": errored + list(failures),
        "skipped_from_ledgers": skipped,
        "price_mismatches": [
            {"ticker": r["ticker"], "ledger_price": r["price_at_analysis"],
             "entry_date_used": r["entry_date_used"],
             "series_close": r["entry_close"],
             "delta_pct": round(r["ledger_price_delta_pct"], 3),
             "traced_to": r.get("ledger_price_traced_to")}
            for r in mismatches
        ],
    }


def format_report(report):
    """사람이 읽는 요약."""
    L = [f"## 실전 트랙레코드 ({report['as_of']})", ""]
    if not report["n_measured"]:
        L.append("측정된 종목 없음 - 코호트나 가격 조회를 확인할 것.")
        return "\n".join(L)

    h = report["horizon_days"]
    o = report["overall"]
    L.append(f"측정 {report['n_measured']}종목 / 실패 {report['n_error']}건 · "
             f"보유기간 {h['min']}~{h['max']}일(중앙값 {h['median']}일)")
    L.append(f"전체: 중앙값 {o['median_return_pct']:+.2f}% · "
             f"평균 {o['mean_return_pct']:+.2f}% · 양(+) {o['pct_positive']}%")
    L.append("")
    L.append("| 등급 | n | 중앙값 | 평균 | 양(+) 비율 |")
    L.append("|---|---:|---:|---:|---:|")
    for g in GRADE_ORDER:
        s = report["by_judgment_grade"].get(g)
        if s:
            L.append(f"| {g} | {s['n']} | {s['median_return_pct']:+.2f}% | "
                     f"{s['mean_return_pct']:+.2f}% | {s['pct_positive']}% |")
    L.append("")
    for j, s in report["by_judgment"].items():
        L.append(f"- {j}: n={s['n']}, 중앙값 {s['median_return_pct']:+.2f}%, "
                 f"양(+) {s['pct_positive']}%")

    if report["n_price_mismatch"]:
        L.append("")
        L.append(f"⚠️ ledger 기록가와 시계열 원종가 불일치 "
                 f"{report['n_price_mismatch']}건:")
        for m in report["price_mismatches"]:
            traced = m.get("traced_to")
            where = (f" -> 실제로는 {traced['date']} 종가"
                     f"({traced['trading_days_before_entry']}거래일 묵은 시세)"
                     if traced else " -> 근방 거래일 어디에도 없음(원인 미상)")
            L.append(f"  - {m['ticker']}: ledger {m['ledger_price']} vs "
                     f"{m['entry_date_used']} 종가 {m['series_close']}"
                     f"({m['delta_pct']:+.2f}%){where}")

    L.append("")
    L.append("⚠️ " + MEASUREMENT_STATUS)
    return "\n".join(L)
