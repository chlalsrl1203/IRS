"""
저평가 후보 9건 심층 정량분석 - 2026-08-01.

경위: "9건 세부분석" 요청. 기존 stress_test_se_rmd_2026_07_31.py는 SE/RMD
2종목만, 방법1/방법2만 계산했다. 이 스크립트는 ledger가 있는 6종목 전부에
대해 아래 4가지를 일괄 산출한다(CRM/ADBE/DECK는 v3.18 분석이라 ledger가
없어 정량 재현이 불가능 - 이 스크립트 대상에서 제외되며, 그 사실 자체가
'재확인 필요' 근거다).

1) 결합 스트레스테스트 (기존 방법1/방법2 확장)
   방법1: DRS=100(ERP 상한 8%) 가정, 성장률 불변
   방법2: 방법1 + Realistic Growth 반토막
   -> "얼마나 나빠져야 판정이 뒤집히는가"의 하한선

2) **판정 뒤집힘 임계 성장률(break-even growth)** [신규]
   현재 r을 그대로 두고, Realistic Growth가 어디까지 떨어지면 Gap=0이
   되는가. 답은 곧 Implied Growth 자체다(Gap = RG - IG). 이걸 현재 RG
   대비 **몇 % 하락 여유가 있는가**로 환산하면 종목간 안전마진 비교가
   된다. 방법1/2가 이산적 시나리오라면 이건 연속적 여유폭이다.

3) **적정가 역산 상승여력(implied upside)** [신규]
   시장이 Realistic Growth를 그대로 인정할 경우의 이론적 시가총액을
   _two_stage_market_cap()으로 계산해 현재 시총 대비 배수를 낸다.
   ⚠️이건 "목표주가"가 아니다 - DCF 상승여력은 g가 r에 가까워질수록
   발산하므로(수학적 성질), 고성장주에서 비현실적으로 큰 값이 나온다.
   그래서 아래 4)의 로그 압축 점수에만 쓰고, 원값은 참고로만 표시한다.

4) **매수 확신도(Conviction Score, 0~100)** [신규 - 이 스크립트의 산출물]
   ⚠️**엔진이 내놓는 값이 아니라 이 스크립트가 정의한 파생 휴리스틱**이다.
   CLAUDE.md의 "근거 없는 자동판정보다 숫자를 드러내고 분석자가 해석하게
   하라"(v3.22 보험업 P/B 선례)는 원칙에 따라, 단일 점수만 내놓지 않고
   5개 구성요소를 전부 노출한다. 가중치는 이 프로젝트가 실제로 겪은
   사고에서 역산했다:
     - 안전마진 30점: Gap 자체보다 "얼마나 버티는가"가 중요하다는 건
       RMD 사례(Gap +5.82%p인데 결합스트레스에서 뒤집힘)가 실증
     - RAR 25점: 프로젝트 표준 위험조정수익 지표
     - Confidence 20점: 엔진 자체 신뢰도(강건성·데이터완결성 반영)
     - 정성리스크 -15~0점: DRS에 안 잡히는 소송·경영진이탈 등
       (WDAY Mobley 소송, TTD 임원이탈이 실제 사례)
     - 데이터신선도 -15~0점: 분석 후 경과일·미확인 실적발표
       (DECK가 분석 익일 실적발표 후 미확인인 게 실제 사례)

실행: python3 scripts/deep_analysis_9_2026_08_01.py
"""

import json
import math
import os
import sys
from datetime import date, datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.expectation_gap_engine import (
    _two_stage_market_cap,
    erp_from_drs,
    implied_growth_two_stage,
)

RF = 0.0447
R_MAX = RF + erp_from_drs(100)  # DRS 최악값에서의 할인율 상한
TODAY = date(2026, 8, 1)

LEDGERS = {
    "SE": "ledger/SE_2026-08-02.json",
    "RMD": "ledger/RMD_2026-08-02.json",
    "DUOL": "ledger/DUOL_2026-08-02.json",
    "TTD": "ledger/TTD_2026-08-02.json",
    "MNDY": "ledger/MNDY_2026-08-02.json",
    "WDAY": "ledger/WDAY_2026-08-02.json",
}

# ── 정성 리스크: DRS/엔진에 반영되지 않는 항목만 (-15 ~ 0) ───────────────
# 근거는 전부 각 종목 analyze_*.py docstring과 CHANGELOG에 기록된 실사실.
QUALITATIVE_RISK = {
    "SE":   (0,   "DRS(52.40)에 이미 경쟁강도·변동성이 충분히 반영됨. 별도 미반영 리스크 없음"),
    "RMD":  (-3,  "Philips Respironics 美 재진입 가능성이 competition_intensity(5.40, 9건 최저)에 "
                  "충분히 반영되지 않았을 여지"),
    "DUOL": (-5,  "회사 자체 가이던스 인하(bookings 10~12%) - 감속은 인정되나 전략적 투자 성격"),
    "TTD":  (-14, "CFO 복수교체+CRO 이탈(경영진 불안정) + 대형광고대행사 고객감사 진행 + "
                  "Amazon DSP 실측 점유율 잠식 - 3중 복합, DRS competition_intensity(15.00)로 "
                  "일부만 반영"),
    "MNDY": (-6,  "좌석과금->AI에이전트 사업모델 전환의 실제 매출영향 미검증(회사 주장만 존재). "
                  "20% 감원 후 실행리스크"),
    "WDAY": (-10, "Mobley v. Workday AI채용차별 집단소송 - 2026-06-22 본안심리 허용, 배상액 "
                  "미확정. 고용차별 소송이라 active_antitrust 필드에 미반영(구조적 공백)"),
    "CRM":  (-8,  "실제 AI발 고객이탈 사례 보도 확인됨(9건 중 유일하게 구체적 이탈 정황). "
                  "애널리스트 의견 3주간 상향->강등->강등 극심 변동"),
    "ADBE": (-4,  "AI 파괴 서사가 지속 중이나 하드데이터(FCF +26% 가속)와 배치 - 서사 리스크"),
    "DECK": (-5,  "소비재 브랜드(HOKA/UGG) 유행 의존성 - 실적 모멘텀 반전시 급격, "
                  "Realistic Growth가 FCF 기저효과로 상한캡에 걸려 신뢰도 주의 이미 명시됨"),
}

# ── 데이터 신선도: 경과일 + 미확인 실적발표 (-15 ~ 0) ────────────────────
# ⚠️2026-08-01 조사로 DECK의 미확인 실적발표를 **해소**했다(아래 EXTERNAL 참고).
# 조사 전에는 -15(9건 중 최대 감점)였으나, 실적이 확인됐고 내용이 우호적이라
# 경과일 감점만 남긴다. "모르는 것"과 "확인해보니 좋은 것"은 다르게 취급해야 한다.
FRESHNESS = {
    # ⚠️SE 실적일은 자료마다 8/11~8/18로 엇갈린다(earningstoday 8/11 vs 종합 8/18).
    #   확정 못 했으므로 이 불확실성을 기록에 남긴다(임의로 하나를 고르지 않는다).
    "SE":   (date(2026, 7, 30), date(2026, 8, 18),  "최근 분석. 다음 실적 8월 중순 "
                                                    "(자료마다 8/11~8/18 엇갈림 - 확정 필요)"),
    "RMD":  (date(2026, 7, 31), date(2026, 8, 6),   "2026-08-06 FY26 Q4 실적발표 예정 - 임박"),
    "DUOL": (date(2026, 7, 31), date(2026, 8, 5),   "2026-08-05 Q2 실적발표 예정 - 4일 후, 9건 중 최임박"),
    "TTD":  (date(2026, 7, 31), date(2026, 8, 6),   "2026-08-06 Q2 실적발표 예정 - 임박"),
    "MNDY": (date(2026, 7, 31), date(2026, 8, 10),  "2026-08-10 Q2 실적발표 예정"),
    "WDAY": (date(2026, 7, 31), date(2026, 8, 21),  "2026-08-21 Q2 실적발표 예정"),
    "CRM":  (date(2026, 7, 22), date(2026, 8, 26),  "10일 경과 + ledger 미보관(v3.18) - 정량 재현 불가"),
    "ADBE": (date(2026, 7, 22), date(2026, 9, 10),  "10일 경과 + ledger 미보관(v3.18) - 정량 재현 불가"),
    "DECK": (date(2026, 7, 22), None,               "✅7/23 실적 확인완료(2026-08-01 조사) - 공백 해소. "
                                                    "다만 ledger 미보관은 그대로"),
}

# ── 외부 교차검증: Forward PE 방향 + 애널리스트 목표가 방향 (-10 ~ +4) ────
# [신규, 2026-08-01 조사] 엔진의 FCF-DCF 판정을 **독립된 외부 지표**로 대조한다.
# 이 프로젝트는 지금까지 엔진 내부 일관성(모델괴리·강건성)만 검증했지 시장
# 컨센서스와의 대조는 하지 않았다. 엔진이 틀릴 수도 있으므로 방향이 어긋나면
# 감점한다. 특히 Forward PE > Trailing PE는 "애널리스트가 이익 급감을 예상"
# 한다는 뜻이라 성장률 가정과 정면 충돌한다.
EXTERNAL = {
    #        (점수, 현재가, PE,    FwdPE, 목표가,   목표가괴리%, 노트)
    "SE":   (+3,  107.41, 42.02, 25.96, 142.26, +33.3,
             "애널 컨센서스 Strong Buy(29명), 목표가 +33.3% - 엔진 판정과 방향 일치"),
    "RMD":  (+2,  214.29, 20.34, 17.76, 248.60, +17.8,
             "Buy(18명), 목표가 +17.8%. FwdPE<PE로 이익개선 예상 - 방향 일치하나 "
             "엔진 Gap(+5.82%p) 자체가 작아 여유 없음"),
    "DUOL": (-10, 134.81, 15.45, 50.11, 114.91, -14.8,
             "⚠️9건 중 유일하게 정면 배치. FwdPE 50.11 > PE 15.45(애널이 이익 "
             "급감 예상) + 목표가가 현재가보다 14.8% 낮음(Hold). 엔진의 Realistic "
             "Growth 25%(상한캡)가 근시일 과대추정일 가능성을 시사"),
    "TTD":  (+4,   18.04, 20.34,  9.25,  24.32, +34.8,
             "FwdPE 9.25로 9건 중 최저 - 이익 대비 가장 싸다. 목표가 +34.8%. "
             "엔진의 Implied Growth 마이너스 판정과 독립적으로 저평가 시사"),
    "MNDY": (+3,   87.15, 38.05, 18.38, 108.54, +24.5,
             "Buy(25명), 목표가 +24.5%. FwdPE 18.38로 PE 절반 - 이익개선 예상, "
             "엔진 판정과 일치. 단 EV/EBITDA 119.3은 절대수준이 높음"),
    "WDAY": (-2,  160.34, 49.93, 14.42, 168.64,  +5.2,
             "FwdPE 14.42로 이익개선 예상은 일치하나, 목표가 상승여력이 +5.2%로 "
             "9건 중 최저 - 시장은 이미 적정가로 본다는 뜻"),
    "CRM":  (+3,  184.02, 21.36, 13.21, 241.72, +31.4,
             "목표가 +31.4%, FwdPE 13.21. 방향 일치 - 다만 애널 의견이 3주간 "
             "상향->강등->강등으로 흔들린 이력"),
    "ADBE": (-1,  250.41, 14.32,  9.66, 269.61,  +7.7,
             "FwdPE 9.66로 매우 저렴하나 컨센서스가 Hold(40명)이고 목표가 "
             "상승여력 +7.7%로 낮다 - 시장은 저평가로 보지 않는다"),
    "DECK": (+4,   96.88, 13.66,  None,   None,  None,
             "✅7/23 실적 확인: EPS $0.94(컨센 상회), 매출 +5.7% 사상 첫 분기 $1B 돌파, "
             "HOKA +7.7%/UGG +4.9%, GM 56.4%, **FY27 가이던스 상향**($5.86~5.91B). "
             "EPS 가이던스가 컨센($7.49)에 근소 미달해 -14% 급락했으나 이후 회복. "
             "현재 $96.88은 분석시점($103.31) 대비 -6.2% -> **Gap은 기록보다 더 "
             "벌어졌다**. PE 13.66으로 9건 중 최저"),
}

# ledger가 없는 3종목: Notion 트래커 기록값(엔진 v3.18)
NO_LEDGER = {
    "CRM":  {"drs": 39.00, "rg": 0.0911, "ig": 0.0036, "gap": 0.0875, "rar": 0.7855},
    "ADBE": {"drs": 31.00, "rg": 0.0812, "ig": -0.0037, "gap": 0.0849, "rar": 1.7231},
    "DECK": {"drs": 23.75, "rg": 0.1200, "ig": 0.0243, "gap": 0.0957, "rar": 1.1954},
}


def load(path):
    d = json.load(open(path))
    return {
        "fcf0": d["derived"]["fcf0"],
        "market_cap": d["inputs"]["market_cap"],
        "n": d["discount_rate"]["n"],
        "g_terminal": d["discount_rate"]["g_terminal"],
        "r": d["discount_rate"]["r"],
        "drs": d["drs"]["score"],
        "rg": d["growth"]["realistic_growth"],
        "ig": d["implied_growth"]["value"],
        "gap": d["expectation_gap"],
        "rar": d["rar"],
        "confidence": d["confidence"]["final"],
        "rg_capped": d["growth"]["breakdown"]["cap_applied"] is not None,
    }


def analyze(ticker, x):
    """1)~3) 정량 산출."""
    # 1) 결합 스트레스테스트
    g_w, _, _ = implied_growth_two_stage(
        x["market_cap"], x["fcf0"], R_MAX, x["n"], x["g_terminal"])
    gap_m1 = x["rg"] - g_w
    gap_m2 = x["rg"] / 2 - g_w

    # 2) 판정 뒤집힘 임계 성장률 = 현재 IG. 여유폭 = (RG-IG)/RG
    headroom = (x["rg"] - x["ig"]) / x["rg"]  # RG가 몇 % 깎여도 버티는가

    # 3) 적정가 역산: 시장이 RG를 그대로 인정할 때의 이론 시총
    fair_cap = _two_stage_market_cap(
        x["rg"], x["fcf0"], x["r"], x["n"], x["g_terminal"])
    upside = fair_cap / x["market_cap"] - 1

    return {
        "gap_m1": gap_m1, "gap_m2": gap_m2,
        "stress_survives": gap_m2 > 0,
        "headroom": headroom,
        "fair_cap": fair_cap, "upside": upside,
    }


def conviction(ticker, gap, rar, confidence, gap_m2, headroom, has_ledger):
    """
    4) 매수 확신도 0~100. **엔진 산출값 아님 - 이 스크립트가 정의한 휴리스틱.**
    구성요소를 전부 반환해 분석자가 가중치에 동의하지 않으면 재계산할 수 있게 한다.
    """
    # (a) 안전마진 30점: 결합스트레스 생존 여부 + 연속 여유폭
    #     RMD 사례(Gap은 양수인데 스트레스에서 뒤집힘)가 이 항목을 만든 이유
    if gap_m2 is None:
        margin = 12.0   # ledger 없어 스트레스테스트 불가 -> 중간값 부여 + 신선도에서 별도 감점
        margin_note = "ledger 부재로 스트레스테스트 불가 - 중립값 부여"
    else:
        # 결합스트레스 생존시 18점 기본 + 잔여Gap 크기로 최대 12점
        survive_pts = 18.0 if gap_m2 > 0 else 0.0
        depth_pts = min(12.0, max(0.0, gap_m2 * 100 / 6.0 * 12.0)) if gap_m2 > 0 else 0.0
        margin = survive_pts + depth_pts
        margin_note = (f"결합스트레스 {'생존' if gap_m2 > 0 else '판정뒤집힘'}"
                       f"(잔여Gap {gap_m2*100:+.2f}%p)")
    # 연속 여유폭도 소폭 반영(headroom 0.8 이상이면 만점 근처)
    margin = min(30.0, margin * (0.7 + 0.3 * min(1.0, headroom / 0.8)))

    # (b) RAR 25점: 이 프로젝트 실측 상위권(PDD 2.48)을 상한으로 정규화
    rar_pts = min(25.0, max(0.0, rar / 2.0 * 25.0))

    # (c) Confidence 20점
    conf_pts = confidence / 100.0 * 20.0

    # (d) 정성리스크 감점
    qual_pts, qual_note = QUALITATIVE_RISK[ticker]

    # (e) 데이터 신선도 감점
    analyzed, pending_earnings, fresh_note = FRESHNESS[ticker]
    days = (TODAY - analyzed).days
    fresh_pts = 0.0
    fresh_pts -= min(8.0, days * 0.8)                       # 경과일당 -0.8, 최대 -8
    if pending_earnings and pending_earnings < TODAY:
        fresh_pts -= 7.0                                     # 미확인 실적발표 이미 지남
    elif pending_earnings and (pending_earnings - TODAY).days <= 7:
        fresh_pts -= 2.0                                     # 1주 내 임박(즉시 갱신 대상)
    if not has_ledger:
        fresh_pts -= 4.0                                     # 재현 불가
    fresh_pts = max(-15.0, fresh_pts)

    # (f) Gap 자체는 위 구성요소에 이미 녹아있으나, 절대크기 보너스 5점
    gap_bonus = min(5.0, max(0.0, gap * 100 / 20.0 * 5.0))

    # (g) 외부 교차검증 [신규] - 엔진 판정 vs 시장 컨센서스 방향 일치도
    ext_pts, price, pe, fwd_pe, target, target_pct, ext_note = EXTERNAL[ticker]

    total = margin + rar_pts + conf_pts + qual_pts + fresh_pts + gap_bonus + ext_pts
    total = max(0.0, min(100.0, total))

    return {
        "total": total,
        "margin": margin, "margin_note": margin_note,
        "rar_pts": rar_pts, "conf_pts": conf_pts,
        "qual_pts": qual_pts, "qual_note": qual_note,
        "fresh_pts": fresh_pts, "fresh_note": fresh_note, "days": days,
        "gap_bonus": gap_bonus,
        "ext_pts": ext_pts, "ext_note": ext_note,
        "price": price, "pe": pe, "fwd_pe": fwd_pe,
        "target": target, "target_pct": target_pct,
        "next_earnings": str(pending_earnings) if pending_earnings else None,
    }


def tier(score):
    if score >= 70: return "A · 높음"
    if score >= 58: return "B · 보통상"
    if score >= 45: return "C · 보통"
    return "D · 낮음"


def main():
    print("=" * 112)
    print(f"저평가 후보 9건 심층 정량분석 ({TODAY}) - DRS=100 기준 r상한 {R_MAX*100:.2f}%")
    print("=" * 112)

    rows = []

    for t, path in LEDGERS.items():
        x = load(path)
        a = analyze(t, x)
        c = conviction(t, x["gap"], x["rar"], x["confidence"],
                       a["gap_m2"], a["headroom"], has_ledger=True)
        rows.append({"t": t, "ledger": True, **x, **a, "conv": c})

    for t, v in NO_LEDGER.items():
        # headroom은 트래커 값으로도 계산 가능(RG/IG 둘 다 기록돼 있음)
        headroom = (v["rg"] - v["ig"]) / v["rg"]
        c = conviction(t, v["gap"], v["rar"], 70,  # confidence 미기록 -> 보수적 70 가정
                       gap_m2=None, headroom=headroom, has_ledger=False)
        rows.append({"t": t, "ledger": False, "drs": v["drs"], "rg": v["rg"],
                     "ig": v["ig"], "gap": v["gap"], "rar": v["rar"],
                     "confidence": None, "headroom": headroom,
                     "gap_m1": None, "gap_m2": None, "stress_survives": None,
                     "fair_cap": None, "upside": None, "rg_capped": None,
                     "conv": c})

    rows.sort(key=lambda r: r["conv"]["total"], reverse=True)

    print(f"\n{'종목':<6} {'확신도':>7} {'등급':<10} {'Gap':>9} {'RAR':>8} {'여유폭':>7} "
          f"{'스트레스잔여':>11} {'FwdPE':>7} {'목표가괴리':>9} {'다음실적':>11}")
    print("-" * 112)
    for r in rows:
        c = r["conv"]
        gm2 = f"{r['gap_m2']*100:+.2f}%p" if r["gap_m2"] is not None else "  N/A"
        fpe = f"{c['fwd_pe']:.2f}" if c["fwd_pe"] else "N/A"
        tp = f"{c['target_pct']:+.1f}%" if c["target_pct"] is not None else "N/A"
        ne = c["next_earnings"] or "-"
        print(f"{r['t']:<6} {c['total']:>6.1f} {tier(c['total']):<10} "
              f"{r['gap']*100:>+8.2f}%p {r['rar']:>+8.4f} {r['headroom']*100:>6.1f}% "
              f"{gm2:>11} {fpe:>7} {tp:>9} {ne:>11}")

    print("\n" + "=" * 112)
    print("확신도 구성요소 분해 (엔진 산출값 아님 - 이 스크립트 정의 휴리스틱)")
    print("=" * 112)
    for r in rows:
        c = r["conv"]
        print(f"\n■ {r['t']}  총점 {c['total']:.1f} = {tier(c['total'])}")
        print(f"    안전마진   {c['margin']:>+6.1f}/30   {c['margin_note']}")
        print(f"    RAR        {c['rar_pts']:>+6.1f}/25   (RAR {r['rar']:+.4f})")
        print(f"    Confidence {c['conf_pts']:>+6.1f}/20   "
              f"({r['confidence'] if r['confidence'] else '미기록->70 가정'})")
        print(f"    Gap보너스  {c['gap_bonus']:>+6.1f}/5    (Gap {r['gap']*100:+.2f}%p)")
        print(f"    정성리스크 {c['qual_pts']:>+6.1f}       {c['qual_note']}")
        print(f"    신선도     {c['fresh_pts']:>+6.1f}       {c['days']}일 경과 · {c['fresh_note']}")
        print(f"    외부교차   {c['ext_pts']:>+6.1f}       {c['ext_note']}")

    print("\n" + "=" * 112)
    print("⚠️ 확신도는 매수 실행 지시가 아니다. 구성요소 가중치는 이 프로젝트가 겪은")
    print("   사고(RMD 스트레스취약·DECK 실적미확인·WDAY 소송)에서 역산한 것이며,")
    print("   분석자가 동의하지 않으면 QUALITATIVE_RISK/FRESHNESS 딕셔너리를 고쳐 재계산할 것.")
    print("=" * 112)

    # ⚠️ledger/ 아래에 두지 말 것. tests/test_screener.py의 _ledger_candidates()가
    #   ledger/*.json을 전부 정식 분석 ledger로 간주하고 d["meta"]["ticker"]를 읽어서,
    #   스키마가 다른 파일이 섞이면 테스트 3건이 KeyError로 깨진다(실제로 겪음).
    os.makedirs("reports", exist_ok=True)
    out = "reports/deep_analysis_9_2026-08-01.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump({
            "generated_at": datetime.now().isoformat(),
            "r_max_at_drs100": R_MAX,
            "rows": [{k: v for k, v in r.items()} for r in rows],
        }, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n결과 저장: {out}")
    return rows


if __name__ == "__main__":
    main()
