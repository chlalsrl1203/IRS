"""
Thesis Monitor 1차 실행 - 2026-08-13 (v3.42, 프로젝트 최초의 외부 검증 루프).

경위: 사용자가 "프로젝트를 다른 차원으로 발전시킬 아이디어"를 요청 - 전수
점검 결과 이 프로젝트의 모든 통제가 내부 일관성에만 걸려 있고 외부 타당성
(계산이 현실과 맞았는가)에는 장치가 전무하다는 것이 가장 큰 구조적 공백이었다.
2026-08-01 감사가 High-1로 이미 지적했고 그때 전제조건(`falsification_
conditions`/`price_at_analysis`)만 만들어둔 채 12일이 지났다.

**확인해보니 그 전제조건이 이미 데이터로 익어 있었다** - 반증조건에 적어둔
트리거 날짜 5건이 전부 기한이 지났는데 아무도 열어보지 않은 상태였다.
`engine/thesis_monitor.py`로 그 루프를 닫고, 이 스크립트가 1차 실행이다.

## 이번 실행이 확인한 것

**A. 반증조건 기한도래 5건 전건 검증(WebSearch, 2026-08-13)** - 결과가
극적으로 갈렸다. 사전등록된 예측이 아니었으면 전부 사후해석이 됐을 것들이다:

  - **TTD: 4개 조건 중 3개 동시 발동 -> 사실상 반증됨.** 이 프로젝트
    반증장치가 실제로 발동한 첫 사례.
  - **SE: 미발동 + 우려가 정면 반전** -> 판정 강화.
  - **DUOL: 미발동 + 핵심지표 가속** -> 판정 강화.
  - **PGR: 미발동이나 방향은 악화** -> 관찰 유지.
  - **MNDY: 확인 불충분** - 조건이 지정한 코호트별 NDR 미확보(전사 NDR만
    공개). 정직하게 "확인필요"로 남긴다.

**B. 시가총액 부식(Gap decay)** - 펀더멘털 입력을 전부 고정하고 시가총액만
오늘 값으로 갈아끼워 재계산. **TTD가 가장 중요한 교훈을 준다** - 주가가
-26.3% 빠져 Gap은 오히려 더 벌어지는데(더 싸 보이는데) 정작 사업 서사는
같은 기간에 반증됐다. **DCF의 Gap 지표만 보면 "더 사라"는 신호가 나오는
전형적 가치함정** - Gap과 반증조건을 반드시 함께 봐야 하는 이유가 실측으로
드러난 셈이다.

⚠️ **분석시점 주가가 없는 ledger 24건은 부식 계산 자체가 불가능하다.**
`price_at_analysis`는 v3.24(2026-08-01)에 도입돼 그 이후 분석에만 있다 -
그 필드의 부재 비용이 오늘 처음 실측으로 드러난 셈이다(TTD는 예외적으로
과거 시세를 별도 조회해 메웠다 - 가장 중요한 종목이라). **앞으로 모든
분석에서 `price_at_analysis`를 반드시 채울 것.**

실행: python3 scripts/thesis_monitor_2026_08_13.py
"""

import json
import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.thesis_monitor import (
    recompute_gap_at_market_cap,
    scan_falsification_conditions,
)

TODAY = date(2026, 8, 13)
LEDGER_DIR = "ledger"
REPORT_PATH = "reports/thesis_monitor_2026-08-13.json"

# ── 현재가: Alpha Vantage GLOBAL_QUOTE, 2026-08-12 종가(최신 거래일) ──────
# 분석시점 주가(price_at_analysis)가 ledger에 있는 종목만 부식 계산이 가능하다.
CURRENT_PRICE = {
    "ACGL": 97.29, "DUOL": 134.63, "MNDY": 85.95, "ROP": 395.23,
    "SE": 128.11, "TCOM": 45.58, "UBER": 75.36, "WDAY": 175.29,
    "TTD": 13.49,
}

# TTD만 예외 - ledger에 price_at_analysis가 없어 분석일 종가를 별도 조회했다
# (Alpha Vantage TIME_SERIES_DAILY, 2026-08-03 종가 $18.30). 반증조건이 실제로
# 발동한 종목이라 부식까지 반드시 봐야 해서 이 한 건만 메웠다.
PRICE_AT_ANALYSIS_BACKFILL = {"TTD": 18.30}

# ── 반증조건 기한도래분 검증 결과(WebSearch 2026-08-13, 1차 출처는 각 사 실적발표) ──
# 자동판정하지 않는다 - 사람이 확인한 결과를 근거와 함께 기록만 한다.
VERIFICATION = {
    "TTD": {
        "verdict": "TRIGGERED",
        "summary": (
            "4개 조건 중 3개 동시 발동. (4) Q2 매출 $715M으로 가이던스 $750M "
            "하회 - 조건 문구 그대로 발동. (3) 매출성장 +3%YoY에 그쳤고 Q3 "
            "가이던스 $650M(중간값)은 컨센서스 $804.8M을 크게 밑돌며 -12.1%YoY "
            "역성장을 회사 스스로 제시 - '낮은 한자릿수 밑으로 재차 둔화'를 "
            "넘어 아예 역성장이라 조건 충족. (2) 실적발표와 동시에 CFO·CMO· "
            "커머셜총괄 교체 - CLAUDE.md에 기록된 '14개월새 CFO 4명'에 이어 "
            "5번째 교체라 조건 충족. 주가는 발표 후 -21.8%."
        ),
        "action": (
            "재검토 완료(2026-08-13, 사용자 승인): 매수리스트 CONFIDENCE_ADJ "
            "72->45 하향 + THESIS_BROKEN_FLAG 추가(0.85x) - 비중 4.80%->2.70%로 "
            "축소(scripts/build_buylist_2026_08_03.py). 공식 ledger의 Gap/RAR/"
            "판정은 변경하지 않음(growth_scorecard 원칙상 realized_quarterly· "
            "guidance_annual은 usable_as_override 아님 - 다년 실적 확인 전까지 "
            "병기만)."
        ),
    },
    "SE": {
        "verdict": "NOT_TRIGGERED",
        "summary": (
            "조건(1) 'Shopee EBITDA가 전년比 추가 감소'가 정면 반전됐다 - "
            "Shopee 조정EBITDA $255.4M으로 **+12.2%YoY 증가**(단위경제성·운영 "
            "효율 개선), 그룹 조정EBITDA도 $917.2M/+10.6%YoY로 가이던스(전년 "
            "수준 유지)를 상회. 매출 $7.8B/+48.1%YoY 서프라이즈. 회사는 FY2026 "
            "Shopee EBITDA $10억 달성 자신감 표명. 2026-08-03 정성조사가 "
            "지적했던 '사상최대 GMV에도 Shopee EBITDA 감소, 그룹이익을 Garena가 "
            "단독부담' 구도가 이번 분기에 해소된 것으로 확인된다."
        ),
        "action": "판정 유지·강화",
    },
    "DUOL": {
        "verdict": "NOT_TRIGGERED",
        "summary": (
            "조건(2) 'DAU 성장률이 20%YoY 밑으로 떨어지면'이 명확히 미발동 - "
            "DAU +23%YoY(58.7백만)로 **전분기 대비 오히려 가속**했다. 이는 "
            "2026-08-02 정성조사의 미해결 쟁점('AI가 실제로 사용자를 대체 "
            "중이라는 직접 증거는 미확인')에 대한 실측 반박에 해당한다. 매출 "
            "$298.5M/+18.3%YoY 컨센서스 상회, EPS $0.66로 8.2% 상회, 유료 "
            "구독자 +17%(1,270만명). ⚠️ 조건(1)이 지정한 '유료구독자 **순증**' "
            "(전분기 30만명 대비)의 분기 순증 수치 자체는 확보하지 못해 조건(1)은 "
            "미확인으로 남긴다 - 다만 방향은 명백히 긍정적이다."
        ),
        "action": "판정 유지·강화(조건1 순증 수치는 차기 확인)",
    },
    "PGR": {
        "verdict": "NOT_TRIGGERED",
        "summary": (
            "조건(3) '컴바인드레이쇼가 90 이상으로 뛰면' 미발동 - Q2 CR 87.3%로 "
            "임계값 아래. 다만 **방향은 조건이 우려한 쪽으로 움직였다**: 전년 "
            "동기 86.2%에서 87.3%로 악화했고, 분기 마지막 달인 6월 단월 CR은 "
            "정확히 90.0%까지 올랐다. 조건(1) 관련 PIF 증가율도 +7%로 CLAUDE.md "
            "기록(11%->8%)에 이어 추가 둔화 - '한 자릿수 초반'까지는 아직 아니라 "
            "미발동이나 임계값에 접근 중이다. 순이익 $3,311M/+4%YoY."
        ),
        "action": "판정 유지, 다음 분기 우선 관찰대상",
    },
    "MNDY": {
        "verdict": "INCONCLUSIVE",
        "summary": (
            "조건(1)이 지정한 것은 '**$50K+/$100K+ ARR 코호트** NDR이 110% "
            "미만'인데, 공개된 건 **전사 NDR 109%**뿐이라 해당 코호트별 수치를 "
            "확보하지 못했다. 전사 109%는 110% 아래지만 조건은 상단 코호트를 "
            "특정했고(원 논리: '상단 코호트 강세로 하단 약세가 상쇄되는 구도'가 "
            "무너지는지), 통상 상단 코호트는 전사 대비 높게 나오므로 전사값만으로 "
            "발동을 단정할 수 없다. 헤드라인은 오히려 강세 - 매출 $364.6M/+22%YoY "
            "(컨센서스 $355M 상회), 조정EPS $1.48(컨센서스 $1.11 대폭 상회), "
            "AI ARR 전분기 대비 2배, 7월 ARR $15억 돌파. **추측하지 않고 "
            "'확인필요'로 남긴다** - 10-Q/실적자료에서 코호트별 NDR 확인 필요."
        ),
        "action": "코호트별 NDR 확보 후 재판정",
    },
}


def load_ledgers() -> list:
    out = []
    for fn in sorted(os.listdir(LEDGER_DIR)):
        if not fn.endswith(".json"):
            continue
        with open(os.path.join(LEDGER_DIR, fn), encoding="utf-8") as f:
            out.append(json.load(f))
    return out


def main():
    ledgers = load_ledgers()
    report = {"generated_at": str(TODAY), "n_ledgers": len(ledgers)}

    # ── A. 반증조건 감시 ────────────────────────────────────────────────
    scans = [scan_falsification_conditions(d, TODAY) for d in ledgers]
    by_status = {}
    for s in scans:
        by_status.setdefault(s["status"], []).append(s)

    print("=" * 100)
    print(f"Thesis Monitor - 반증조건 감시 ({TODAY}, ledger {len(ledgers)}건)")
    print("=" * 100)
    for st in ("past_due", "pending", "undated", "no_conditions"):
        items = by_status.get(st, [])
        print(f"  {st:15} {len(items):3}건  "
              f"{' '.join(sorted(x['ticker'] for x in items))}")
    print()

    print("── 기한도래 항목 (확인 필요) " + "─" * 65)
    for s in sorted(by_status.get("past_due", []), key=lambda x: x["ticker"]):
        t = s["ticker"]
        v = VERIFICATION.get(t)
        print(f"\n[{t}] 분석일 {s['analyzed_at']}")
        for x in s["past_due"]:
            print(f"    · {x['date']}  …{x['context'][:150]}…")
        if v:
            print(f"    => 검증결과: {v['verdict']} / {v['action']}")
            print(f"       {v['summary']}")
        else:
            print("    => 검증결과: 미확인 - ⚠️ 정규식이 잡은 날짜가 실제 트리거가 "
                  "아닐 수 있다(예: 소송 집단기간처럼 과거를 서술한 날짜). "
                  "위 문맥으로 직접 분류할 것.")
    print()

    report["falsification_scan"] = {
        "counts": {k: len(v) for k, v in by_status.items()},
        "past_due": [
            {
                "ticker": s["ticker"],
                "analyzed_at": s["analyzed_at"],
                "dates": [{"date": str(x["date"]), "raw": x["raw"],
                           "context": x["context"]} for x in s["past_due"]],
                "verification": VERIFICATION.get(s["ticker"]),
            }
            for s in sorted(by_status.get("past_due", []), key=lambda x: x["ticker"])
        ],
        "pending": [
            {"ticker": s["ticker"],
             "dates": [str(x["date"]) for x in s["pending"]]}
            for s in sorted(by_status.get("pending", []), key=lambda x: x["ticker"])
        ],
    }

    # ── B. 시가총액 부식 ────────────────────────────────────────────────
    print("── 시가총액 부식(펀더멘털 고정, 시총만 갱신) " + "─" * 50)
    head = (f"{'종목':6} {'분석일':11} {'주가변동':>9} {'Gap(당시)':>10} "
            f"{'Gap(현재)':>10} {'부식':>9}  판정변화")
    print(head)
    print("-" * len(head))

    # 스킵 사유를 두 가지로 나눈다 - 뭉뚱그리면 라벨이 사실과 어긋난다
    # (v3.32가 통째로 다룬 "기록이 거짓말을 하는" 유형의 오류).
    decay_rows, no_price_then, no_price_now = [], [], []
    for d in ledgers:
        t = d["meta"]["ticker"]
        p_then = (d["inputs"].get("price_at_analysis")
                  or PRICE_AT_ANALYSIS_BACKFILL.get(t))
        p_now = CURRENT_PRICE.get(t)
        if not p_then:
            no_price_then.append(t)
            continue
        if not p_now:
            no_price_now.append(t)
            continue

        mc_then = d["inputs"]["market_cap"]
        # 방어적 확인: 시총/주가로 역산한 주식수가 상식적인 범위인지
        # (price_at_analysis와 market_cap의 기준일이 어긋나 있으면 여기서 티가 난다)
        implied_shares = mc_then / p_then
        mc_now = mc_then * (p_now / p_then)

        r = recompute_gap_at_market_cap(d, mc_now)
        r["price_then"], r["price_now"] = p_then, p_now
        r["price_change_pct"] = p_now / p_then - 1.0
        r["implied_shares"] = implied_shares
        # Realistic Growth는 시총과 무관해야 한다 - 어긋나면 버그다
        assert abs(r["realistic_growth_then"] - r["realistic_growth_now"]) < 1e-12, t
        decay_rows.append(r)

    for r in sorted(decay_rows, key=lambda x: x["gap_decay_pp"]):
        flip = "→ " + r["judgment_now"] if r["judgment_flipped"] else "불변"
        print(f"{r['ticker']:6} {r['analyzed_at']} {r['price_change_pct']*100:+8.1f}% "
              f"{r['gap_then']*100:+9.2f}%p {r['gap_now']*100:+9.2f}%p "
              f"{r['gap_decay_pp']*100:+8.2f}%p  {flip}")

    print()
    print(f"  계산 불가 A - 분석시점 주가 없음 {len(no_price_then)}건: "
          f"{' '.join(sorted(no_price_then))}")
    print("  ⚠️ price_at_analysis는 v3.24(2026-08-01) 도입 필드라 그 이전 분석에는 "
          "없다.\n     이 필드가 비면 부식 계산 자체가 불가능하다 - 앞으로 반드시 채울 것.")
    if no_price_now:
        print(f"  계산 불가 B - 현재가 미조회 {len(no_price_now)}건: "
              f"{' '.join(sorted(no_price_now))} (분석시점 주가는 있음)")

    report["gap_decay"] = {
        "rows": decay_rows,
        "skipped_no_price_at_analysis": sorted(no_price_then),
        "skipped_no_current_price": sorted(no_price_now),
    }

    os.makedirs("reports", exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n  리포트 저장: {REPORT_PATH}")
    return report


if __name__ == "__main__":
    main()
