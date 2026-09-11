"""
희석 드래그 측정 — ledger 전수 (engine/dilution.py 구동, v3.84)

PHASE 4(2026-08-21) 1회성 스크립트를 엔진 모듈 + 상시 실행 스크립트로 승격한
것이다. 새 계산은 없다 — 정규화·창 파생·검증만 `engine/dilution.py`로 옮겼다.

재실행: `python -m scripts.dilution_drag`

⚠️ 공식 Gap·판정·등급·비중을 바꾸지 않는다(구조 D 독립 진단축, 결정 #29·#33).
"""
import json
import os
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.dilution import (  # noqa: E402
    STATUS_OK,
    VALIDATION_STATUS,
    dilution_drag,
)
from scripts.sbc_harvest_2026_08_21 import _cached_facts, _load_ledgers  # noqa: E402

OUT_PATH = "reports/dilution_drag.json"
SBC_PATH = "reports/sbc_harvest_2026-08-21.json"


def latest_buylist(folder="reports"):
    """가장 최근 매수리스트. 옛 날짜 파일에 고정하면 새 종목이 조용히 빠진다.

    2026-08-03판은 12종목 bare list, 2026-09-06판부터는 `positions`를 담은
    dict다 — 두 스키마를 모두 읽는다.
    """
    import re
    pat = re.compile(r"^buylist_(\d{4}-\d{2}-\d{2})\.json$")
    cands = sorted(f for f in os.listdir(folder) if pat.match(f))
    if not cands:
        return {}, None
    path = os.path.join(folder, cands[-1])
    doc = json.load(open(path, encoding="utf-8"))
    rows = doc["positions"] if isinstance(doc, dict) else doc
    return {r["ticker"]: r["weight_final"] for r in rows}, cands[-1]


def load_sbc(path=SBC_PATH):
    try:
        doc = json.load(open(path, encoding="utf-8"))
    except FileNotFoundError:
        return {}
    return {r["ticker"]: r.get("sbc_to_fcf_pct")
            for r in doc["results"] if r.get("status") == "OK"}


def main():
    ledgers = _load_ledgers()
    buy, buy_file = latest_buylist()
    sbc = load_sbc()

    rows = [dilution_drag(t, d, _cached_facts(t)) for t, (_fn, d) in sorted(ledgers.items())]
    for r in rows:
        r["weight_final"] = buy.get(r["ticker"])
        r["sbc_to_fcf_pct"] = sbc.get(r["ticker"])
    ok = [r for r in rows if r["status"] == STATUS_OK]

    print(f"희석 드래그 = 주당 FCF CAGR − 총 FCF CAGR   (매수리스트: {buy_file})\n")
    hdr = (f"{'종목':6} {'비중':>7} {'총FCF':>9} {'주당FCF':>9} {'드래그':>9} "
           f"{'주식수':>8} {'SBC/FCF':>8}")
    print(hdr)
    print("-" * len(hdr))
    for r in sorted(ok, key=lambda x: x["dilution_drag"]):
        w = f"{r['weight_final'] * 100:6.2f}%" if r["weight_final"] else "     - "
        sb = (f"{r['sbc_to_fcf_pct'] * 100:7.1f}%"
              if r["sbc_to_fcf_pct"] is not None else "      - ")
        mark = "  <<< 주당 감소" if r["per_share_declined"] else ""
        print(f"{r['ticker']:6} {w:>7} {r['fcf_cagr_total'] * 100:8.2f}% "
              f"{r['fcf_cagr_per_share'] * 100:8.2f}% {r['dilution_drag'] * 100:+8.2f}%p "
              f"{r['share_count_change_pct'] * 100:+7.1f}% {sb}{mark}")

    skipped = [r for r in rows if r["status"] != STATUS_OK]
    if skipped:
        print("\n측정 불가 ('무해'가 아니라 '미확인'):")
        for r in sorted(skipped, key=lambda x: (x["status"], x["ticker"])):
            w = f" [보유 {r['weight_final'] * 100:.2f}%]" if r["weight_final"] else ""
            print(f"  {r['ticker']:6} {r['status']:22}{w} {r.get('detail', '')}")

    held = [r for r in rows if r["weight_final"]]
    held_ok = [r for r in held if r["status"] == STATUS_OK]
    held_bad = [r for r in held if r["status"] != STATUS_OK]
    exposed = [r for r in held_ok if r["dilution_drag"] < -0.05]
    unmeasured_w = sum(r["weight_final"] for r in held_bad)
    print(f"\n매수 유니버스 {len(held)}종목 중 측정 {len(held_ok)}종목"
          f"(미측정 비중 {unmeasured_w * 100:.2f}%) · "
          f"드래그 −5%p 초과 {len(exposed)}종목 "
          f"비중 {sum(r['weight_final'] for r in exposed) * 100:.2f}%")

    # ⚠️ 미측정 집단이 무작위가 아니다 — 이 사실이 빠지면 측정된 부분집합의
    #    "희석 온건함"이 유니버스 전체를 대표하는 것처럼 오독된다.
    med_ok = (statistics.median(r["share_count_change_pct"] for r in held_ok)
              if held_ok else None)
    high_sbc_unmeasured = sorted(
        (r["ticker"], r["sbc_to_fcf_pct"]) for r in held_bad
        if (r.get("sbc_to_fcf_pct") or 0) >= 0.30)
    bias = {
        "measured_median_share_change": med_ok,
        "unmeasured_high_sbc": [t for t, _ in high_sbc_unmeasured],
        "direction": "optimistic" if high_sbc_unmeasured else "unknown",
        "note": ("미측정 집단은 무작위가 아니다 — IPO 직후 종목과 고SBC 종목이 "
                 "구조적으로 몰려 있어(주식수 급증 자체가 측정을 막는다) 측정된 "
                 "부분집합은 희석을 **과소**평가하는 방향으로 치우친다. "
                 "부분 커버리지를 전체 신호로 읽지 말 것."),
    }
    if high_sbc_unmeasured:
        print("  ⚠️ 미측정 집단 편향: SBC/FCF 30% 이상인 "
              + ", ".join(f"{t}({p * 100:.0f}%)" for t, p in high_sbc_unmeasured)
              + f"가 측정 불가 — 측정된 종목 주식수 변화 중앙값은 {med_ok * 100:+.1f}%뿐이라"
              " 부분집합이 희석을 과소평가한다")

    out = {
        "generated_at": None,  # 아래에서 채움
        "engine_module": "engine/dilution.py",
        "validation_status": VALIDATION_STATUS,
        "affects_official_judgment": False,
        "buylist_source": buy_file,
        "gap_measured": ("realistic_growth는 총 FCF/매출 CAGR로 계산되는데 주주가 "
                         "받는 것은 주당 흐름이다. 그 차이가 RG 어디에도 없다."),
        "not_wired_into_growth": (
            "RG·성장지속기간·판정 어디에도 반영하지 않는다 — CORE MODEL CHANGE "
            "GATE 6번(validation strategy)이 없다(실현수익률과의 관계 증거 0건). "
            "결정 #29·#33이 확립한 구조 D(독립 진단축)만."
        ),
        "overlap_with_sbc": {
            "spearman": -0.597, "n": 25, "measured_at": "2026-08-21",
            "note": ("sbc_to_fcf_pct는 보상비용의 크기를, 희석 드래그는 주주 지분의 "
                     "순변화(발행−자사주매입)를 잰다. 반례: VRT SBC 2.4%인데 드래그 "
                     "−7.66%p, WDAY SBC 58.6%인데 −2.98%p."),
        },
        "coverage": {
            "measured": len(ok), "total": len(rows),
            "held_measured": len(held_ok), "held_total": len(held),
            "held_unmeasured_weight": unmeasured_w,
        },
        "coverage_bias": bias,
        "results": rows,
    }
    from datetime import date
    out["generated_at"] = date.today().isoformat()
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"\n저장: {OUT_PATH}")
    print(f"측정 {len(ok)}/{len(rows)} · 드래그 중앙값 "
          f"{statistics.median(r['dilution_drag'] for r in ok) * 100:+.2f}%p")


if __name__ == "__main__":
    main()
