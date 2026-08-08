"""
KRX 래퍼 ETF 중복노출 리포트 - 2026-08-08.

경위: v3.36/v3.37이 미국 원본끼리의 중복노출(VOO+QQQ+XLK를 같이 담으면 같은
메가캡을 여러 번 사는 문제)을 측정했지만, 한국 투자자는 미국 원본을 살 수
없다 - 실제로 담는 건 국내 상장 래퍼다. 이 스크립트는 `ledger_krx/`의 28개
국내 래퍼 전부를 대상으로, 각자의 `us_reference_ticker` 원본이 가진
top10_holdings를 재사용해(신규 데이터 수집 없이) 실제 매수 대상 간의 겹침을
계산한다(`engine/krx_etf_pipeline.py::krx_holdings_overlap_report()`).

실행: python3 scripts/krx_overlap_report_2026_08_08.py
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.krx_etf_pipeline import format_krx_overlap_table, krx_holdings_overlap_report

LEDGER_KRX = "ledger_krx"
LEDGER_ETF = "ledger_etf"


def load_all_krx_results():
    results = []
    for fname in sorted(os.listdir(LEDGER_KRX)):
        if fname.endswith(".json"):
            with open(os.path.join(LEDGER_KRX, fname), encoding="utf-8") as f:
                results.append(json.load(f))
    return results


def load_all_us_results():
    """같은 티커의 최신 ledger만 남긴다(회사/ETF 쪽과 동일한 관행)."""
    latest = {}
    for fname in sorted(os.listdir(LEDGER_ETF)):
        if not fname.endswith(".json"):
            continue
        with open(os.path.join(LEDGER_ETF, fname), encoding="utf-8") as f:
            d = json.load(f)
        ticker = d["meta"]["ticker"]
        date = d["meta"]["analyzed_at"][:10]
        if ticker not in latest or date > latest[ticker][0]:
            latest[ticker] = (date, d)
    return {t: d for t, (date, d) in latest.items()}


def main():
    krx_results = load_all_krx_results()
    us_results = load_all_us_results()

    report = krx_holdings_overlap_report(krx_results, us_results)

    print("=" * 100)
    print(f"KRX 래퍼 ETF 중복노출 리포트 ({len(krx_results)}종목 대상)")
    print("=" * 100)
    print(format_krx_overlap_table(report))
    print()
    print(f"동일지수 쌍: {len(report['same_index_pairs'])} / "
          f"실측 쌍: {len(report['pairs'])} / "
          f"측정불가: {len(report['uninformative_pairs'])} / "
          f"데이터없음: {len(report['skipped_no_holdings'])}")
    print()
    print("⚠️ 이 리포트는 각 KRX 래퍼가 재사용한 미국 원본의 top10 보유종목으로")
    print("   근사한 값이다 - top10 표본 기준 하한이며, 실제 겹침은 이보다 클 수 있다.")
    print("⚠️ '측정불가'는 '안 겹친다'가 아니라 top10 표본끼리 우연히 안 겹친 것뿐이다")
    print("   (예: 섹터 ETF와 광범위지수 ETF는 표본 밖에서 상당히 겹칠 수 있다).")

    out_path = "reports/krx_overlap_2026-08-08.json"
    os.makedirs("reports", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n결과 저장: {out_path}")

    return report


if __name__ == "__main__":
    main()
