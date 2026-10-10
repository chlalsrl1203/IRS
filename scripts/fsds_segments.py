"""
세그먼트 매출 대조 — 연결 성장이 어느 부문에서 왔는가 (v3.99, 진단 전용)

    python -m scripts.fsds_segments            # data/fsds/*.json 전부

GEN 사례(2026-07-28)가 이 리포트의 존재 이유다. 3y·5y 연결 매출 CAGR이 14%대로
"튀지 않았는데" 세그먼트 공시를 손으로 대조해서야 핵심사업은 +5%대이고 나머지는 전혀
다른 산업(소비자대출)의 연결효과임이 드러났다. 그 대조를 SEC 재무제표 데이터셋의
세그먼트 차원 값으로 자동화한다.

규칙(사전 고정):
  - 축은 BusinessSegments, ProductOrService만(지역은 사업 분리가 아니다).
  - 구성원 합이 연결 매출과 **양 끝 연도 모두 1% 안에서** 맞을 때만 "가산적"으로 보고
    부문별 성장 기여도를 낸다. 안 맞으면(계층 구성원 혼재·일부만 공시) 기여도를 내지
    않고 그 사실만 적는다 — 합이 안 맞는 분해로 기여도를 내면 숫자가 지어진다.
  - 판정하지 않는다. "M&A 왜곡이 있다"고 결론내지 않으며 QSI 답에 쓰지 않는다.
"""

import glob
import json
import os
import sys
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from engine import fsds  # noqa: E402

OUT = os.path.join(ROOT, "reports", "fsds_segments.json")
ADDITIVE_TOL = 0.01


def analyze(x):
    subs, rows, cik = x["submissions"], x["rows"], x["cik"]
    cons = fsds.consolidated_revenue(subs, rows, cik)
    total = cons["by_year"]
    out = {"ticker": x["ticker"], "consolidated_tag": cons["tag"], "consolidated": total,
           "source": [q["accession"] for q in x["quarters"]], "axes": {}}
    for axis, d in fsds.segment_revenue(subs, rows, cik).items():
        members = d["members"]
        years = sorted(set.intersection(*(set(v) for v in members.values())) & set(total))
        res = {"tag": d["tag"], "members": members, "common_years": years}
        if len(years) >= 2:
            y0, y1 = years[0], years[-1]
            s0 = sum(v[y0] for v in members.values())
            s1 = sum(v[y1] for v in members.values())
            additive = (abs(s0 / total[y0] - 1) <= ADDITIVE_TOL
                        and abs(s1 / total[y1] - 1) <= ADDITIVE_TOL)
            res.update({"first_year": y0, "last_year": y1,
                        "sum_ratio": [s0 / total[y0], s1 / total[y1]], "additive": additive})
            n = y1 - y0
            cons_cagr = (total[y1] / total[y0]) ** (1 / n) - 1 if total[y0] > 0 else None
            res["consolidated_cagr"] = cons_cagr
            seg = {}
            for m, v in members.items():
                row = {"share_last": v[y1] / total[y1] if total[y1] else None}
                if v[y0] > 0 and v[y1] > 0:
                    row["cagr"] = (v[y1] / v[y0]) ** (1 / n) - 1
                if additive and total[y1] != total[y0]:
                    row["contribution_to_growth"] = (v[y1] - v[y0]) / (total[y1] - total[y0])
                seg[m] = row
            res["by_member"] = seg
            if not additive:
                res["note"] = ("구성원 합이 연결 매출과 맞지 않는다(계층 구성원 혼재 또는 일부만 "
                               "공시) — 성장 기여도를 계산하지 않았다")
        else:
            res["note"] = "구성원과 연결 매출이 함께 있는 연도가 2개 미만"
        out["axes"][axis] = res
    if not out["axes"]:
        out["note"] = "단일 축 세그먼트 매출이 데이터셋에 없다(단일 부문 기업이거나 공시 형식 상이)"
    return out


def main():
    results = []
    for p in sorted(glob.glob(os.path.join(ROOT, "data", "fsds", "*.json"))):
        x = json.load(open(p, encoding="utf-8"))
        r = analyze(x)
        results.append(r)
        line = f"{r['ticker']:5}"
        for axis, a in r["axes"].items():
            if a.get("additive"):
                top = sorted(a["by_member"].items(),
                             key=lambda kv: -(kv[1].get("contribution_to_growth") or 0))[:2]
                line += (f"  {axis}: 연결 {a['consolidated_cagr'] * 100:+.1f}%/년 "
                         f"({a['first_year']}→{a['last_year']}), 기여 상위 "
                         + ", ".join(f"{m} {v['contribution_to_growth'] * 100:.0f}%"
                                     for m, v in top))
            else:
                line += f"  {axis}: 비가산"
        print(line if r["axes"] else f"{line}  (세그먼트 없음)")
    doc = {"generated_at": date.today().isoformat(), "engine_module": "engine/fsds.py",
           "validation_status": fsds.VALIDATION_STATUS["segment_revenue"],
           "affects_official_judgment": False,
           "rule": ("구성원 합이 양 끝 연도 모두 연결 매출의 1% 안일 때만 성장 기여도를 낸다. "
                    "판정·QSI 답에 쓰지 않는 진단 리포트."),
           "results": results}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print("저장:", os.path.relpath(OUT, ROOT))


if __name__ == "__main__":
    main()
