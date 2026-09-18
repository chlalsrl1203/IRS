"""확신 포트폴리오(2026-09-05, 18종목)를 daily_brief.py가 읽는 매수리스트
스키마로 변환해 발행한다.

## 왜 필요한가

`scripts/daily_brief.py::section_overseas()`는 `_latest("buylist_")`로
`reports/buylist_<날짜>.json`만 찾는다. 그런데 2026-09-05에 만든 새 포트폴리오
산출물(`sa_portfolio_2026-09-05.json`, `conviction_portfolio_2026-09-05.json`)은
파일명이 `buylist_` 접두어가 아니라서 daily_brief가 구조적으로 못 찾는다 -
그 결과 2026-09-04까지도 daily_brief는 2026-08-03에 만든 낡은 12종목 매수리스트
(TTD 포함, 이후 여러 종목이 배제/추가된)를 계속 보여주고 있었다.

## 왜 build_buylist_2026_08_03.py를 고치지 않는가

Simplicity First 관행 - 날짜 붙은 스크립트는 재현성 아티팩트라 손대지 않고,
새 로직은 새 날짜 스크립트로 만든다. 이 스크립트는 **새 계산을 전혀 하지 않는다**
- `conviction_portfolio_2026-09-05.json`(이미 3단계 게이트를 거쳐 확정된 18종목)을
그대로 읽어 `section_overseas()`가 기대하는 필드명으로 매핑만 한다:
`weight` -> `weight_final`, `confidence_adj` -> `conf_adj`,
`confidence_status`(자유 문자열) -> `conf_status`(정확히 "미검증"일 때만 플래그).

## 의도적으로 비워두는 필드

`thesis_broken_flag`/`severe_flag`/`model_dependent_universe`/
`sbc_dependent_universe`는 옮기지 않는다 - 그 네 플래그가 표현하던 위험
(TTD의 논거반증·거버넌스, 모델선택 취약, SBC 거짓편입)은 이번 포트폴리오를
만든 `portfolio_screen_2026_09_05.py`의 G1(등급취약)·G2(SBC 거짓편입)·
G3(반증확정) 게이트가 이미 그 위험이 있는 종목을 배제한 뒤에 남은 18종목이라
falsy로 두는 게 정확하다(TTD 자체가 이 18종목에 없다). `cap_bound`는 그대로
옮긴다 - 캡바인딩은 배제 사유가 아니라 병기 사유였다.
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE = os.path.join(ROOT, "reports", "conviction_portfolio_2026-09-05.json")
DATE = "2026-09-06"
OUT = os.path.join(ROOT, "reports", f"buylist_{DATE}.json")


def build_rows(conviction):
    rows = []
    for p in conviction["positions"]:
        rows.append(
            {
                "ticker": p["ticker"],
                "company": p["company"],
                "weight_final": p["weight"],
                "grade": p["grade"],
                "conf_adj": p["confidence_adj"],
                "conf_status": (
                    "미검증" if p["confidence_status"] == "미검증" else p["confidence_status"]
                ),
                "cap_bound": p["cap_bound"],
                "cluster": p["cluster"],
                "gap_pct": p["gap_pct"],
                "analyzed_at": p["analyzed_at"],
                "source_pipeline": "conviction_portfolio_2026-09-05",
            }
        )
    return rows


def main():
    with open(SOURCE, encoding="utf-8") as f:
        conviction = json.load(f)

    rows = build_rows(conviction)
    total = sum(r["weight_final"] for r in rows)
    assert abs(total - 1.0) < 1e-6, f"비중 합계가 1.0이 아니다: {total}"

    payload = {
        "generated_at": DATE,
        "source": os.path.basename(SOURCE),
        "note": (
            "확신 포트폴리오(v3.82, G1/G2/G3 게이트 통과 18종목)를 daily_brief.py "
            "스키마로 변환한 발행본. 새 밸류에이션/사이징 로직 없음 - "
            "conviction_portfolio_2026-09-05.json을 그대로 재매핑."
        ),
        "n_positions": len(rows),
        "positions": rows,
    }

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"published {len(rows)} positions -> {OUT}")
    print(f"weight sum = {total:.10f}")


if __name__ == "__main__":
    main()
