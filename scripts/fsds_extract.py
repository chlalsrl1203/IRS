"""
SEC Financial Statement Data Sets에서 대상 종목의 차원 사실만 뽑아 저장한다 (v3.99)

    python -m scripts.fsds_extract ERIE HLNE RYAN GEN ...

종목마다 **최신 연차보고서**와 **그 3년 전 연차보고서**를 고른다. 연차보고서 하나에는
보통 3개 회계연도 비교치가 들어 있으므로 두 개면 연속 6년이 덮인다(희석 드래그의 5년
창 base..base+5와 같은 폭). 그 제출일이 속한 분기 zip(60~120MB)을 `.cache/fsds/`에
캐시하고(.gitignore 대상), 대상 행만 `data/fsds/<TICKER>.json`으로 남긴다(재현용, 커밋).

엔진 계산은 없다 — 파싱은 `engine/fsds.py`, 해석은 호출부가 한다.
"""

import json
import os
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from engine import fsds  # noqa: E402
from engine.filing_dates import DEFAULT_USER_AGENT, ticker_to_cik  # noqa: E402
from engine.sec_events import list_filings  # noqa: E402
from scripts.qsi_sec_events import fetch_json  # noqa: E402

CACHE = os.path.join(ROOT, ".cache", "fsds")
OUT = os.path.join(ROOT, "data", "fsds")
TAGS = fsds.SHARE_TAGS + fsds.REVENUE_TAGS


def quarter_zip(year, q):
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, f"{year}q{q}.zip")
    if not os.path.exists(path):
        req = urllib.request.Request(fsds.QUARTER_URL.format(year=year, q=q),
                                     headers={"User-Agent": DEFAULT_USER_AGENT})
        tmp = path + ".part"
        with urllib.request.urlopen(req, timeout=600) as r, open(tmp, "wb") as f:
            while True:
                b = r.read(1 << 20)
                if not b:
                    break
                f.write(b)
        os.replace(tmp, path)
    return path


def pick_annual_filings(cik):
    """최신 연차보고서와 그보다 3년(±6개월) 앞선 연차보고서."""
    lst = list_filings(cik, "2000-01-01", fetch_json)
    rows = sorted((r for r in lst["rows"] if r["form"] in ("10-K", "20-F", "40-F")),
                  key=lambda r: r["filingDate"], reverse=True)
    if not rows:
        return []
    latest = rows[0]
    y, m = int(latest["filingDate"][:4]), int(latest["filingDate"][5:7])
    target = (y - 3) * 12 + m
    older = min(rows[1:], key=lambda r: abs(int(r["filingDate"][:4]) * 12
                                            + int(r["filingDate"][5:7]) - target),
                default=None)
    return [latest] + ([older] if older else [])


def extract(ticker):
    cik = ticker_to_cik(ticker)
    if not cik:
        return {"ticker": ticker, "error": "CIK 없음"}
    picks = pick_annual_filings(cik)
    subs, rows, used = {}, [], []
    for r in picks:
        yq = fsds.quarter_of(r["filingDate"])
        path = quarter_zip(*yq)
        s, n = fsds.read_quarter_zip(path, [cik], TAGS)
        # 그 분기의 이 회사 연차보고서 전부(원본+정정)를 받는다
        subs.update(s)
        rows.extend(n)
        used.append({"quarter": f"{yq[0]}q{yq[1]}", "accession": r["accessionNumber"],
                     "form": r["form"], "filed": r["filingDate"]})
    doc = {"ticker": ticker, "cik": str(int(cik)), "source": "SEC Financial Statement Data Sets",
           "quarters": used, "submissions": subs, "rows": rows}
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, f"{ticker}.json"), "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=0, sort_keys=True)
        f.write("\n")
    return {"ticker": ticker, "filings": used, "n_rows": len(rows)}


def load_extract(ticker):
    path = os.path.join(OUT, f"{ticker}.json")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main(argv):
    for t in argv:
        try:
            print(extract(t))
        except Exception as e:  # 한 종목 실패가 나머지를 막지 않게
            print({"ticker": t, "error": f"{type(e).__name__}: {e}"})
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
