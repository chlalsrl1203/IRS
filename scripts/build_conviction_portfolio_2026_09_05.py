"""
확신 포트폴리오 (Stage 2-3) - 2026-09-05

`portfolio_screen_2026_09_05.py`(Stage 0-1)가 S/A 32종목 → 20종목으로 좁힌 뒤,
미검증 12종목에 정성 심층조사를 수행한 결과를 반영해 최종 유니버스와 비중을
확정한다.

이 스크립트는 **새 밸류에이션 로직을 0줄 추가하지 않는다.** ledger에 저장된
Gap과 정성조사가 확정한 Confidence만 재조합한다.

═══════════════════════════════════════════════════════════════════
Stage 2 게이트 (사전등록) - G6 회사공시 성장률 배치
═══════════════════════════════════════════════════════════════════

조건: 회사가 별도 공시하는 **다년 실현** 성장률(오가닉 또는 인수효과 제거 후)
      로 Realistic Growth를 대체했을 때 등급이 S/A를 벗어나면 배제.
근거: ROP(v3.28) - 회사 공시 오가닉 성장률로 대체하니 Gap +7.74%p→+1.24%p,
      A→C로 실제 이탈했고 사용자 승인 후 공식판정으로 승격됐다.

⚠️ **1개년 가이던스만으로는 적용하지 않는다.** KEYS(2026-08-04)가 확립한
   기준 - 검증 안 된 1개년 예측으로 다년 개념(n≈12)을 대체하는 것은 근거
   부족이다. 1개년 가이던스 괴리는 배제가 아니라 **Confidence 하향**으로
   반영한다(그러면 quality_score를 통해 비중이 자동으로 줄어든다).

═══════════════════════════════════════════════════════════════════
Stage 3 비중 - 기존 공식 재사용, 새 숫자 발명 금지
═══════════════════════════════════════════════════════════════════

quality_score = Gap%p × (Confidence_adj / 100)
  - `build_buylist_2026_08_03.py`가 쓰던 공식 그대로. 새 지표가 아니다.
종목당 상한 12% (기존 `PER_STOCK_CAP`), 상한흡수 루프도 v3.67 수정판 그대로.

**목표비중을 두지 않는다.** PHASE 2 감사(2026-08-21) 실측: 근거 없는 버킷
목표비중이 자본의 16.75~18.82%를 좌우한 반면, 가장 노력을 들인 축
(`CONFIDENCE_ADJ`)은 2.33%만 움직였다. 목표비중을 두면 그 8배 역비례를
복제할 뿐이다. 군집은 **배분이 아니라 진단**으로만 쓴다.

**기계적 할인은 캡바인딩 하나만 남긴다.** SBC 취약·등급 취약 종목은 Stage 1
게이트가 이미 배제했고, 모델취약·정책리스크는 이번 조사에서 Confidence에
직접 반영했다 - 같은 증거로 두 번 벌점을 주지 않는다(v3.19
`check_deceleration_double_count`가 경고하는 이중반영).
"""
from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from engine.expectation_gap_engine import judgment_grade_from_gap

REPO = pathlib.Path(__file__).resolve().parents[1]
REPORTS = REPO / "reports"
SCREEN = REPORTS / "portfolio_screen_2026-09-05.json"

PER_STOCK_CAP = 0.12
CAP_BOUND_DISCOUNT = 0.85   # 기존 build_buylist가 쓰던 값 그대로

# ── Stage 2 정성 심층조사 결과 (2026-09-05, 직접 WebSearch) ─────────────
# 형식: ticker -> (confidence_adj, 상태, 근거)
# 기존 12종목은 2026-08-02/04 정성조사 확정값을 그대로 승계한다.
RESEARCH = {
    # ── 2026-08-02/04 정성조사 확정 (승계) ──
    "ACGL": (83, "검증(2026-08-03)",
             "준비금 적정성·자본배분(BVPS +22.6%)·거버넌스 전부 양호, 신용등급 상향. "
             "재보험 ex-cat 컴바인드레이쇼 2분기 연속 소폭 악화, 대재해리스크는 "
             "평활화된 FCF로 미반영."),
    "PGR":  (87, "검증(2026-08-03)",
             "지속가능성장률이 Realistic Growth와 2%p 이내로 성장추정 정합. "
             "텔레매틱스 데이터우위가 손해율 우위로 미연결(합산비율 3위), "
             "신규계약 증가율 11%→8% 둔화."),
    "SE":   (79, "검증(2026-08-03)",
             "Shopee EBITDA가 사상최대 GMV에도 전년比 감소(TikTok Shop 방어비용), "
             "그룹 이익성장이 사실상 Garena 단독부담. SBC/희석 양호(FCF의 14%)."),
    "PDD":  (75, "검증(2026-08-02)",
             "희석 문제없음(SBC 6~8%, 트래커 하위권). 2026-01 SAMR 물리적 충돌·"
             "임원 체포로 확대된 사기·탈세 조사, 2026-04 RMB15.1억 벌금 - "
             "거버넌스·컴플라이언스 리스크."),
    "DUOL": (78, "검증(2026-08-02)",
             "주가 66~80% 하락 구간 내내 내부자 순매도만, 매수 전무. 성장서사 과장 "
             "의혹 증권소송 진행. OpenAI 펀드 투자 경쟁사 Speak 급성장하나 DAU는 "
             "여전히 +21%YoY."),
    "MNDY": (65, "검증(2026-08-02)",
             "가장 우려스러운 케이스 - FY2027 매출목표 철회 + 주가 하루 -21% 급락이 "
             "원분석에 누락, 증권소송 진행(S.D.N.Y.). 회사 자체 FY2026 조정FCF "
             "가이던스도 전년대비 감소 제시."),
    "GEN":  (70, "검증(2026-08-04)",
             "ROIC 9.15%로 5y평균 20.74% 대비 급락 추정(단일출처, 10-K 미대조). "
             "MoneyLion 세그먼트 마진 30%로 Cyber Safety(61%)의 절반. 매도데스크 "
             "2곳이 beat-and-raise 이후에도 중립 유지. SBC/FCF 15.6%는 양호."),
    "UBER": (83, "검증(2026-08-04)",
             "Prop 22 CA대법원 만장일치 합헌으로 최대 과거리스크 durably 해소. "
             "반대로 Waymo Phoenix 철수완료·Atlanta/Austin 배타권 종료로 '파트너' "
             "프레이밍 약화. EU Platform Work Directive 미해결."),

    # ── 2026-09-05 신규 정성조사 (직접 WebSearch) ──
    "NBIX": (88, "검증(2026-09-05)",
             "⭐특허절벽 우려 해소 - ANDA 소송 합의로 제네릭 진입일이 **2038-03-01**로 "
             "확정(핵심물질특허 8,039,627은 PTE 552일 반영해 2031 만료, Orange Book "
             "22개 특허가 2027~2040 분포). 엔진의 n=12년 성장기간 가정이 정확히 "
             "성립한다. 남는 리스크는 Ingrezza 단일제품 의존과 SBC/FCF 29.1%."),
    "HLNE": (87, "검증(2026-09-05)",
             "⭐DCF의 반복현금흐름 가정이 성립 - FY2026 관리·자문보수 $584M(+14%)가 "
             "수수료수익의 77%, 성과보수 $175M은 23%. FRE +25% $345M, FEAUM $82B "
             "(+13%), 에버그린 $17.5B(+64%)로 성장이 반복매출 쪽에서 나온다. "
             "엔진 RG 12.72%가 관리보수 +14%·FEAUM +13%와 정합. 성과보수 23% 변동성은 "
             "잔존 리스크."),
    "DLO":  (84, "검증(2026-09-05)",
             "⭐성장상한(25%)이 회사 가이던스로 정당화됨 - 2H2026 TPV 성장 60~70%, "
             "총이익 성장 25~30%, FY2026 영업이익 성장 27.5~32.5%로 회사 스스로 "
             "캡 이상을 제시한다(ROP형 하방 괴리가 아니라 상방). 다만 테이크레이트가 "
             "0.84%까지 압축됐고 TPV 확대에도 처리비용이 안 떨어지는 점, 신흥국 통화·"
             "자본통제·규제 리스크는 그대로."),
    "SKYW": (85, "검증(2026-09-05)",
             "CPA 계약 기반이 오히려 강화 - 2026-01 United E175 40대·Delta 13대 만기 "
             "연장, Embraer와 2028~2032년 E175 44대 인도포지션 확보, 2028년말 300대+ "
             "목표. 엔진 RG 9.35%가 최근 실현(2024 +20.2%, 2025 +15.0%)보다 이미 "
             "보수적이다. 시총 $3.69B가 코퍼스 최소($3.74B) 바로 아래라 estimate_drs "
             "중앙값 대체가 이 규모에서 검증된 적 없다는 점만 남는다."),
    "ADBE": (84, "검증(2026-09-05)",
             "성장추정이 정합 - 최근 4년 매출 YoY가 10.2~11.5%로 극히 안정적이고 "
             "FY2026 가이던스 +9%가 엔진 RG 10.95%와 근접. AI First ARR이 전년比 3배 "
             "$500M 돌파, Firefly ARR $300M 근접(+50%QoQ)으로 'SaaSpocalypse' 서사가 "
             "실측으로 뒷받침되지 않는다. 다만 organic ARR 성장이 6분기 연속 감속"
             "(10.9%→10.5%)이고 freemium 전환으로 단기 ARR을 의도적으로 희생 중."),
    "CINF": (76, "검증(2026-09-05)",
             "원분석 가정보다 실제가 나았다 - 1H2026 합산비율 98.2%(전년 103.8%에서 "
             "5.6%p 개선), 유리한 전년도 준비금 발전 Q1 $81M·Q2 $42M 확인, Q2 주식 "
             "평가익 세후 $882M. 그러나 ①외부 밸류에이션 모델이 초과수익 기준 약 21% "
             "고평가로 평가(P/B 1.62)해 엔진 S등급과 정면 충돌하고 ②지속가능성장률 "
             "10.01% vs RG 15.22% 괴리 5.21%p가 미해소이며 ③주식 40% 포트폴리오가 "
             "BVPS 변동성의 구조적 원천이다."),
    "DECK": (74, "검증(2026-09-05)",
             "⚠️감속이 실현으로 확인 - HOKA 성장이 24%→mid-teens→high-single로 "
             "단계적 둔화, 연결 매출 YoY도 16.3%(FY25)→9.8%(FY26). FY2027 가이던스 "
             "매출 $5.86~5.91B(FY26 $5.47B 대비 +7.2~8.0%), EPS 성장 4~6%로 FY26의 "
             "11%에서 반토막, 관세 $120M·마케팅 증액이 마진 압박. 가이던스 기준으로 "
             "재계산해도 Gap +8.6%p로 A는 유지되나 여유가 얇다."),
    "SIGI": (74, "검증(2026-09-05)",
             "⚠️성장상한(12%)이 실현과 정면 배치 - 순보험료가 전년比 **−5% 역성장**"
             "($1.221B, 표준상업 −6%). 회사는 '2년간 언더라이팅 포트폴리오 품질 개선을 "
             "위한 의도적 조치'라 설명하고 실제로 Q2 전년도 준비금 발전이 중립(전년 "
             "−3.8%p 불리에서 개선), FY 합산비율 가이던스 96.5~97.5%. 그러나 갱신 "
             "순수요율 +6.5%가 전년比 3.4%p 둔화해 연화 국면 진입 신호. Gap이 A를 "
             "유지하는 근거는 Implied Growth −11.67%가 워낙 음수라서인데, 그 음수 "
             "자체가 보험 플로트로 부풀려진 FCF의 산물일 수 있다(ACGL v3.13 경고)."),
    "TW":   (70, "검증(2026-09-05)",
             "⚠️급격한 감속과 경쟁구도 재편이 동시에 - Q2 2026 매출 $559M(+9%YoY)로 "
             "다년 실현(3y CAGR 19.97%)의 절반 이하, 매출 미스로 주가 -12%. "
             "2026-07 ICE가 MarketAxess를 $60억에 인수해 자본력을 갖춘 통합 경쟁자 "
             "등장. 반면 점유율은 계속 확대 중(글로벌 스왑 24.1% 사상최고 +207bp, "
             "美국채 9분기 연속 50%+, 2026-06 신용채권에서 MarketAxess 사상 첫 추월). "
             "최근 분기 성장률(+9%)로 재계산하면 Gap +2.6%p로 C등급이 되나, 1개 분기는 "
             "KEYS 기준상 다년 개념을 대체할 근거가 못 돼 배제하지 않고 비중으로 반영."),
    "NXT":  (70, "검증(2026-09-05)",
             "⚠️회사 가이던스가 엔진을 10%p 하회 - FY2027 매출 가이던스 $3.8~4.1B"
             "(2026-05 상향)는 FY2026 실적 $3.56B 대비 중간값 기준 **+11.0%**인데 "
             "엔진 RG는 21.16%다. 가이던스 기준 Gap은 +1.3%p로 C등급. 다년 실현"
             "(2025 +18.4%, 2026 +20.3%)이 아직 뒷받침해 배제하지 않았으나 취약. "
             "백로그 $5.25B 사상최고·100% 미국산 트래커로 ITC 국내조달 10% 보너스 "
             "확보는 긍정. 반면 회사 스스로 'ITC 요건 강화 시 활동 둔화'를 예고했고 "
             "모델괴리 3.31%p로 판정이 모델선택에도 민감하다."
             "\n⚠️조사 중 2차 출처 오류를 잡았다 - 첫 검색이 '$4.1~4.4B'를 보고했으나 "
             "회사 IR 원문 재확인 결과 $3.8~4.1B였다(TYL SBC 3배 오류와 같은 유형)."),
}

# ── G6 배제 (Stage 2 게이트) ────────────────────────────────────────
# 회사가 별도 공시하는 다년 실현 성장률로 대체 시 등급이 S/A 이탈.
G6_EXCLUDED = {
    "RYAN": {
        "engine_rg": 0.1926,
        "company_growth": 0.05,
        "basis": "회사 별도공시 오가닉 성장률",
        "detail":
            "FY2026 오가닉 성장 가이던스를 high-single-digit에서 **mid-single-digit"
            "(4~6%)**으로 하향, Q2 오가닉은 **0% 근처**로 안내. 경영진이 '2026년 "
            "의미 있는 인수 없음'을 명시하고 M&A 대신 자사주매입(Q2 $260M + 신규 "
            "$300M 승인)으로 선회 - 엔진 RG 19.26%를 떠받치던 M&A 기여분이 사라진다. "
            "연결 매출 YoY는 2022~2025년 내내 +18~22%였으나 그 격차가 곧 인수효과다. "
            "부동산 요율 하락·경쟁심화로 조정EBITDAC 마진도 100~150bp 하향. "
            "ROP(v3.28)가 확립한 구조와 정확히 동일 - 회사가 오가닉을 매 분기 별도 "
            "공시하는 다년 지표이므로 1개년 가이던스 한계(KEYS 기준)에 걸리지 않는다.",
    },
    "CROX": {
        "engine_rg": 0.1034,
        "company_growth": 0.03,
        "basis": "인수효과 제거 후 다년 실현 CAGR + 회사 가이던스",
        "detail":
            "HEYDUDE 인수(2022-02) 이후로만 깨끗한 3년 실현 CAGR이 **4.36%**이고, "
            "최근 2년 실현 YoY는 +3.5%(2025) → **−1.5%(2026)**로 이미 역성장 전환. "
            "회사 FY2026 가이던스도 매출 **+1~2%**에 그친다. 엔진 RG 10.34%는 5년 "
            "CAGR 23.86%(HEYDUDE 단계상승 포함)에 끌려간 값이다. HEYDUDE는 Q2 매출 "
            "−5.7%($179M)에 FY 가이던스 −2~4%이며 상표권·영업권 손상차손까지 "
            "인식했다(구조적 훼손 확인). Crocs 본 브랜드만 +4.3%. "
            "다년 실현 실적이 뒷받침하므로 ROP 기준 충족.",
    },
}

CLUSTER = {
    "PDD": "growth_platform", "MNDY": "growth_platform", "DUOL": "growth_platform",
    "SE": "growth_platform", "UBER": "growth_platform",
    "ADBE": "enterprise_software", "TW": "enterprise_software",
    "ACGL": "insurance_underwriting", "PGR": "insurance_underwriting",
    "SIGI": "insurance_underwriting", "CINF": "insurance_underwriting",
    "HLNE": "financial_services_other", "DLO": "financial_services_other",
    "DECK": "consumer_brand",
    "NBIX": "healthcare_lifesci",
    "GEN": "industrial_stalwart",
    "SKYW": "transportation",
    "NXT": "industrial_energy_transition",
}


def apply_cap(rows, cap):
    """상한흡수 - v3.67 수정판(경계 EPS 처리 + 수렴 실패 시 예외)."""
    eps = 1e-12
    for _ in range(50):
        over = [r for r in rows if r["weight"] > cap + eps]
        if not over:
            break
        excess = sum(r["weight"] - cap for r in over)
        for r in over:
            r["weight"] = cap
        room = [r for r in rows if r["weight"] < cap - eps]
        base = sum(r["quality_score"] for r in room)
        if not room or base <= 0:
            raise RuntimeError("상한흡수 실패: 재분배할 여유 종목이 없다")
        for r in room:
            r["weight"] += excess * r["quality_score"] / base
    else:
        raise RuntimeError("상한흡수가 50회 안에 수렴하지 않았다")
    return rows


def main():
    screen = json.loads(SCREEN.read_text(encoding="utf-8"))
    survivors = {r["ticker"]: r for r in screen["survivors"]}

    final, excluded_g6 = [], []
    for t, r in survivors.items():
        if t in G6_EXCLUDED:
            g = dict(G6_EXCLUDED[t])
            # Implied Growth는 성장률 입력과 완전히 독립이므로 그대로 고정하고
            # Realistic Growth 자리에만 회사 공시 성장률을 대입한다(ROP 크로스체크와
            # 동일한 방식). IG = 엔진RG − Gap.
            ig = g["engine_rg"] - r["gap"]
            g["implied_growth"] = ig
            g["gap_at_company_growth"] = g["company_growth"] - ig
            g["grade_at_company_growth"] = judgment_grade_from_gap(
                g["gap_at_company_growth"])
            excluded_g6.append({**r, "g6": g})
            continue
        conf, status, basis = RESEARCH[t]
        cap_bound = bool(r["cap_applied"])
        # DLO는 이번 조사에서 캡이 회사 가이던스로 정당화됨 → 할인 면제
        discount = CAP_BOUND_DISCOUNT if (cap_bound and t != "DLO") else 1.0
        qs = r["gap"] * 100 * (conf / 100) * discount
        final.append({
            "ticker": t, "company": r["company"], "cluster": CLUSTER[t],
            "grade": r["grade"], "gap_pct": r["gap"] * 100,
            "gap_min_pct": r["gap_min"] * 100,
            "confidence_engine": r["confidence_engine"],
            "confidence_adj": conf, "confidence_status": status,
            "confidence_basis": basis,
            "cap_bound": r["cap_applied"],
            "cap_discount_applied": discount != 1.0,
            "quality_score": qs,
            "analyzed_at": r["analyzed_at"],
        })

    total = sum(r["quality_score"] for r in final)
    for r in final:
        r["weight"] = r["quality_score"] / total
    apply_cap(final, PER_STOCK_CAP)
    final.sort(key=lambda r: -r["weight"])

    print("=" * 104)
    print(f"확신 포트폴리오 - S/A 32 → Stage1 게이트 20 → Stage2 게이트 {len(final)}종목")
    print("=" * 104)
    print(f"\n[Stage 2 배제] G6 회사공시 다년 성장률 배치 - {len(excluded_g6)}종목\n")
    for r in excluded_g6:
        g = r["g6"]
        print(f"  {r['ticker']:6s} {r['grade']}등급  Gap {r['gap']*100:+.2f}%p "
              f"(엔진 RG {g['engine_rg']*100:.2f}%)")
        print(f"         → {g['basis']} {g['company_growth']*100:.1f}% 대입 시 "
              f"Gap {g['gap_at_company_growth']*100:+.2f}%p "
              f"→ **{g['grade_at_company_growth']}등급** (S/A 이탈)")
        print(f"         └ {g['detail']}")

    print(f"\n[최종 편입] {len(final)}종목 - 전원 정성 심층조사 완료\n")
    print(f"  {'티커':6s} {'군집':26s} {'등급':3s} {'Gap':>9s} {'최악Gap':>9s} "
          f"{'엔진Conf':>7s} {'조정Conf':>7s} {'비중':>7s}")
    print("  " + "-" * 100)
    for r in final:
        print(f"  {r['ticker']:6s} {r['cluster']:26s} {r['grade']:3s} "
              f"{r['gap_pct']:+8.2f}%p {r['gap_min_pct']:+8.2f}%p "
              f"{r['confidence_engine']:>7d} {r['confidence_adj']:>7d} "
              f"{r['weight']*100:>6.2f}%")
    print("  " + "-" * 100)
    print(f"  {'합계':6s} {'':26s} {'':3s} {'':9s} {'':9s} {'':7s} {'':7s} "
          f"{sum(r['weight'] for r in final)*100:>6.2f}%")

    clusters = {}
    for r in final:
        c = clusters.setdefault(r["cluster"], {"weight": 0.0, "tickers": []})
        c["weight"] += r["weight"]
        c["tickers"].append(r["ticker"])
    print(f"\n[군집 집중도] 진단용 - 목표비중을 두지 않았는데 실제로 어떻게 분산됐나\n")
    for c, v in sorted(clusters.items(), key=lambda x: -x[1]["weight"]):
        print(f"  {c:28s} {v['weight']*100:6.2f}%  ({len(v['tickers'])}종목: "
              f"{', '.join(v['tickers'])})")

    n_new = sum(1 for r in final if "2026-09-05" in r["confidence_status"])
    conf_vals = [r["confidence_adj"] for r in final]
    print(f"\n{'='*104}")
    print(f"미검증 비중: 0.00% (전원 정성 심층조사 완료 - 이번 신규 {n_new}종목)")
    print(f"조정 Confidence 범위: {min(conf_vals)}~{max(conf_vals)} "
          f"(중앙값 {sorted(conf_vals)[len(conf_vals)//2]}) "
          f"| 엔진 원값은 전원 89~94였다")
    print("=" * 104)

    out = {
        "generated_at": "2026-09-05",
        "stage": "2-3 (정성 심층조사 반영 + 비중 확정)",
        "pipeline": "S/A 32종목 → Stage1 게이트 20 → Stage2 G6 게이트 "
                    f"{len(final)}종목",
        "methodology": (
            "quality_score = Gap%p × (Confidence_adj/100) × 캡바인딩할인(0.85). "
            "목표비중 없음(PHASE 2 감사), 종목당 상한 12%. 새 밸류에이션 로직 0줄."
        ),
        "not_provided": [
            "공분산 기반 최적화 (수익률 상관행렬이 이 저장소에 없다)",
            "군집 목표비중 (의도적 - PHASE 2 감사가 근거 없는 목표비중의 자본영향을 실측)",
            "실현수익률 검증 (관측 0건 - 이 포트폴리오 자체가 사전등록 예측이다)",
            "Confidence의 확률적 해석 (VALIDATION_STATUS = UNCALIBRATED)",
        ],
        "n_final": len(final),
        "positions": final,
        "excluded_stage2": [{k: v for k, v in r.items() if k != "flags"}
                            for r in excluded_g6],
        "cluster_diagnostics": clusters,
    }
    path = REPORTS / "conviction_portfolio_2026-09-05.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n저장: {path.relative_to(REPO)}")


if __name__ == "__main__":
    main()
