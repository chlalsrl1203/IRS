"""
S/A등급 32종목 신규 포트폴리오 구성 - 2026-09-05.

경위: 기존 매수리스트(`build_buylist_2026_08_03.py`)는 2026-08-02 시점
S/A등급 13종목(과반이 growth_platform 단일 팩터)을 대상으로 만들어졌다.
그 뒤 3주간 정식분석이 12종목 -> 32종목으로 늘었는데, 이 스크립트는
`reports/portfolio_ranking_2026-08-02.json`(생성 시점에 고정된 스냅샷)을
읽어 신규 종목을 구조적으로 못 본다 - v3.32가 "노후화로 아예 고려조차
안 된 종목"이라 부른 문제가 이제 종목 1개(BSX)가 아니라 사실상 전체
신규분석분(20종목)에 해당한다. **기존 리스트를 패치하는 대신 `ledger/`
전수에서 다시 시작**한다.

## 설계가 기존 스크립트와 다른 지점 - PHASE 2 감사 결과를 반영

2026-08-21 PHASE 2 사이징 감사가 실측한 것: 근거 없는 버킷 목표비중
(40/30/20/10)이 자본의 **16.75~18.82%**를 좌우하는데, 이 프로젝트가
가장 공들인 축(정성 심층조사 `CONFIDENCE_ADJ`)은 **2.33%**만 움직였다 -
"가장 많은 노력을 들인 축이 자본에는 가장 적게 영향을 준다"는 역비례가
실측으로 확인된 상태다. 32종목으로 유니버스가 늘고 위험군집도 4개에서
11개로 늘어난 지금, 그 목표비중 메커니즘을 그대로 확장하면 근거 없는
숫자 4개가 근거 없는 숫자 11개로 늘어날 뿐이다.

**그래서 이번엔 버킷 목표비중 자체를 두지 않는다.** 대신:
  1. `quality_score = Gap%p x (Confidence_adj/100)`(기존 공식 재사용,
     새 지표 발명 없음)로 32종목 전체를 한 번에 순위매김한다.
  2. 종목당 상한 12%(`PER_STOCK_CAP`, 기존 값 그대로 재사용)만 강제한다.
  3. 위험군집(11개)은 **배분에 쓰지 않고 진단에만** 쓴다 - 배분 후 군집별
     실제 집중도를 계산해 보여준다. 목표를 정하지 않으므로 "근거 없는
     목표비중" 문제 자체가 원천적으로 생기지 않는다. 이게 PHASE 2가 지목한
     결함에 대한 가장 직접적인 대응이다 - 목표를 없애면 목표의 근거를
     따질 필요도 없어진다.

## 어느 것을 재사용하고 어느 것을 새로 만들었나

**재사용(발명 아님)**:
  - `quality_score` 공식, `PER_STOCK_CAP=0.12`, 종목당 상한 강제 알고리즘
    (반복 흡수 루프, v3.67에서 수렴버그를 고친 버전 그대로 이식).
  - 12종목 중 이미 정성 심층조사를 마친 종목의 `CONFIDENCE_ADJ`(TTD의
    2026-08-13 하향 포함) - 근거·수치 전부 `build_buylist_2026_08_03.py`
    에서 그대로 가져왔다. 손대지 않았다.
  - `cap_bound`(Lynch/규모상한 바인딩) x0.85 할인 - 기존 스크립트의 조정.
  - `SEVERE_FLAG`/`THESIS_BROKEN_FLAG`(TTD) x0.85 x2 - 기존 그대로.

**새로 만든 것(단, 새 숫자는 발명하지 않고 기존 0.85x를 재사용)**:
  - `SBC_FRAGILE_UNVERIFIED` x0.85: SBC 차감 시 판정이 뒤집히는데
    (`sbc_cross_check.judgment_flipped=True`) 아직 "일관 적용해도 신호가
    살아남는지"(PHASE 1, 2026-08-21) 검증되지 않은 신규종목
    (PINS/TENB/DOCU/NOW). **TCOM은 이미 PHASE 1에서 CANCELLED로 확인돼
    이 할인을 적용하지 않는다** - 같은 유형의 신호를 검증 여부로 구분하지
    않으면 TCOM에 근거 없는 페널티를 준 2026-09-04 RQ-002 초판 오류를
    반복하는 셈이다(같은 세션 PHASE 1이 이미 이 실수를 자체 정정한 바
    있다). WDAY는 이미 `CONFIDENCE_ADJ=81`의 근거 문구 자체가 이 SBC
    취약성을 명시적으로 반영하고 있어 중복 할인하지 않는다(이중계상 방지).
  - `MODEL_FRAGILE` x0.85: 모델괴리 >=3%p(엔진이 이미 쓰는 v3.19 경고
    임계값, `engine/portfolio.py::MODEL_DIVERGENCE_THRESHOLD`와 동일값
    재사용)인데 Confidence 점수 자체에는 이 축에 대한 감점이 없는 종목
    (NXT 3.3%p, NOW 5.4%p) - 두 값 모두 원시 Confidence=94를 그대로
    받고 있어 이 취약성이 반영되지 않은 상태였다.

**32종목 중 새로 분석돼 정성 심층조사가 아직 없는 20종목**은 엔진
원시 Confidence를 그대로 쓰고 `status="미검증"`으로 명시한다 - 2026-08-04
배치 이전 A등급 6종목이 정성조사 전에 받았던 것과 정확히 같은 표시다.
이 종목들의 raw_score=94는 "확신도가 높다"가 아니라 "아직 확인 안 된
확신도"라는 뜻이므로 표에서 반드시 구분해서 읽을 것.

## 이 스크립트가 하지 않는 것

  - 공분산 기반 최적화(수익률 상관행렬 데이터 없음 - 알려진 스코프 갭).
  - 단일 합성 "IRS 점수"(§31 안티기능 등록부 - quality_score는 이미
    확립된 2-요인 곱이지 새 합성지표가 아니다).
  - 위험군집 목표비중(위 설계 근거).
  - TTD·MNDY 등 이미 확인된 서사훼손(thesis-broken) 종목의 완전 배제 -
    남은 근거를 0으로 취급하는 건 과도하다는 기존 판단(2026-08-13)을
    유지한다. 대신 Confidence·이중 할인으로 비중을 실질적으로 축소한다.

실행: python3 scripts/build_sa_portfolio_2026_09_05.py
산출물: reports/sa_portfolio_2026-09-05.json
"""
import glob
import json
import os

PER_STOCK_CAP = 0.12
MODEL_DIVERGENCE_THRESHOLD = 0.03  # engine/portfolio.py와 동일값 재사용

# (조정 Confidence, 상태, 근거) - 12종목은 build_buylist_2026_08_03.py에서
# 그대로 가져왔다(TTD는 2026-08-13 하향판). 나머지 20종목은 아래 루프에서
# 엔진 원시 Confidence로 채운다.
RESEARCHED_CONFIDENCE_ADJ = {
    "PDD":  (75, "검증", "2026-08-02 심층조사: SAMR 물리충돌·확대된 사기조사(신규 거버넌스 리스크). 희석은 무해."),
    "MNDY": (65, "검증", "2026-08-02 심층조사: S/A 중 최우려 - FY2027목표 철회+주가-21%급락(원분석 누락)+진행중 증권소송."),
    "DUOL": (78, "검증", "2026-08-02 심층조사: 내부자 순매도만 확인(매수 없음)+증권소송(초기)+신규 AI경쟁사 Speak, 다만 DAU는 여전히 견조."),
    "ACGL": (83, "검증", "2026-08-03 심층조사: 준비금·자본배분·거버넌스 양호(신용등급 상향), ex-cat 마진 2분기연속 소폭악화."),
    "PGR":  (87, "검증", "2026-08-03 심층조사: 성장추정 정합적이나 텔레매틱스 모트가 손해율 우위로 미이어짐(GEICO/Allstate가 더 나음)."),
    "SE":   (79, "검증", "2026-08-03 심층조사: Shopee EBITDA 역성장(TikTok Shop 방어비용), 그룹이익은 Garena 단독부담."),
    "TTD":  (45, "검증(하향)", "2026-08-13 재검토: 반증조건 4개 중 3개 동시 발동(thesis_monitor) - Q2 매출 $715M<가이던스, "
             "Q3 가이던스 -12.1%YoY 역성장, CFO·CMO·커머셜총괄 동시교체. growth_scorecard·gap_decay 독립경로도 동일결론. "
             "공식 Gap/RAR/판정은 유지(usable_as_override 아님)하되 Confidence만 하향."),
    "GEN":  (70, "검증", "2026-08-04 심층조사: ROIC 9.15%(5y평균 20.74%대비 급락)+세그먼트마진 30%vs61%+시장은 27%매출성장에도 -9%로 반응."),
    "UBER": (83, "검증", "2026-08-04 심층조사: Prop22로 CA 리스크는 durably 해소됐으나 Waymo 배타권 종료로 파트너 프레이밍 약화, EU Directive 미해결."),
    "WDAY": (81, "검증", "2026-08-04 심층조사: 자사주매입이 SBC 2배속 상회(긍정적)하나 Mobley소송 확대+AI네이티브경쟁 실측화 - "
             "SBC교차검증 플립 근접종목이라 이 하향에 이미 반영됨(별도 SBC 할인 미적용)."),
    "TCOM": (80, "검증", "2026-08-04 심층조사: 中규제리스크 공시완화 이력+자체가이던스가 Realistic Growth를 크게 하회. "
             "SBC 이탈신호는 2026-08-21 PHASE 1에서 부분적용의 산물(CANCELLED)로 확인 - SBC 근거로 추가 할인하지 않음."),
    "BRO":  (70, "검증", "2026-08-04 심층조사: 오가닉성장률 7분기연속감속(2회 마이너스) - 시장이 이미 멀티플 재평가 완료. "
             "M&A주식대가 다일루션 ~19%(SBC와 별개) 확인. model_choice_reason 순환참조는 2026-09 P0-2로 경제논리 재확정됨."),
}

SEVERE_FLAG = {"TTD"}
THESIS_BROKEN_FLAG = {"TTD"}

# SBC 차감시 판정 flip이 있으나, "일관 적용해도 신호가 살아남는지"(PHASE 1,
# 2026-08-21)가 아직 검증되지 않은 종목만 여기 넣는다. TCOM은 검증 완료
# (CANCELLED)라 제외, WDAY는 CONFIDENCE_ADJ 근거에 이미 반영돼 제외.
SBC_FRAGILE_UNVERIFIED = {"PINS", "TENB", "DOCU", "NOW"}

# 위험군집 - 배분에는 쓰지 않고 진단에만 쓴다(설계 근거는 상단 docstring).
CLUSTER = {
    "PDD": "growth_platform", "MNDY": "growth_platform", "DUOL": "growth_platform",
    "SE": "growth_platform", "TTD": "growth_platform", "UBER": "growth_platform",
    "WDAY": "growth_platform", "PINS": "growth_platform",
    "NOW": "enterprise_software", "PCTY": "enterprise_software", "ADBE": "enterprise_software",
    "TW": "enterprise_software", "DOCU": "enterprise_software", "TENB": "enterprise_software",
    "ACGL": "insurance_underwriting", "PGR": "insurance_underwriting",
    "SIGI": "insurance_underwriting", "RLI": "insurance_underwriting", "CINF": "insurance_underwriting",
    "BRO": "insurance_distribution", "RYAN": "insurance_distribution",
    "HLNE": "financial_services_other", "DLO": "financial_services_other",
    "DECK": "consumer_brand", "CROX": "consumer_brand",
    "NBIX": "healthcare_lifesci", "MEDP": "healthcare_lifesci", "MMS": "healthcare_lifesci",
    "GEN": "industrial_stalwart",
    "TCOM": "travel",
    "SKYW": "transportation",
    "NXT": "industrial_energy_transition",
}


def load_universe():
    universe = {}
    for path in sorted(glob.glob("ledger/*.json")):
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        grade = d.get("judgment_grade")
        if grade not in ("S", "A"):
            continue
        ticker = d["meta"]["ticker"]
        gap = d["expectation_gap"]
        conf_engine = (d.get("confidence") or {}).get("final")
        sbc = d.get("sbc_cross_check") or {}
        growth_bd = (d.get("growth") or {}).get("breakdown") or {}
        div = ((d.get("implied_growth") or {}).get("models") or {}).get("divergence")
        universe[ticker] = {
            "ticker": ticker, "grade": grade, "gap_pct": gap * 100,
            "conf_engine": conf_engine,
            "cap_bound": bool(growth_bd.get("cap_applied")),
            "sbc_flip": sbc.get("judgment_flipped"),
            "sbc_to_fcf_pct": sbc.get("sbc_to_fcf_pct"),
            "model_divergence": div,
            "analyzed_at": (d["meta"].get("analyzed_at") or "")[:10],
            "path": path,
        }
    return universe


def main():
    universe = load_universe()
    n = len(universe)
    print("=" * 100)
    print(f"S/A등급 신규 포트폴리오 구성 - ledger 전수({n}종목), 목표비중 없는 quality_score 순위배분")
    print("=" * 100)

    missing_researched = [t for t in RESEARCHED_CONFIDENCE_ADJ if t not in universe]
    if missing_researched:
        print(f"  [참고] 정성조사 완료였으나 현재 S/A 유니버스 밖: {missing_researched}")

    rows = []
    for t, r in universe.items():
        if t in RESEARCHED_CONFIDENCE_ADJ:
            conf_adj, status, basis = RESEARCHED_CONFIDENCE_ADJ[t]
        else:
            conf_adj, status = r["conf_engine"], "미검증"
            basis = "정성 심층조사 미실시(엔진 원시 Confidence 그대로 - 확신도가 아니라 미확인 상태)"

        quality = r["gap_pct"] * (conf_adj / 100)
        discounts = []
        if r["cap_bound"]:
            quality *= 0.85
            discounts.append("cap_bound×0.85")
        if t in SEVERE_FLAG:
            quality *= 0.85
            discounts.append("severe_flag×0.85")
        if t in THESIS_BROKEN_FLAG:
            quality *= 0.85
            discounts.append("thesis_broken×0.85")
        if t in SBC_FRAGILE_UNVERIFIED and r["sbc_flip"]:
            quality *= 0.85
            discounts.append("sbc_fragile_unverified×0.85")
        if (r["model_divergence"] or 0) >= MODEL_DIVERGENCE_THRESHOLD and t not in RESEARCHED_CONFIDENCE_ADJ:
            quality *= 0.85
            discounts.append("model_fragile×0.85")

        rows.append({
            "ticker": t, "cluster": CLUSTER[t], "grade": r["grade"],
            "gap_pct": r["gap_pct"], "conf_engine": r["conf_engine"],
            "conf_adj": conf_adj, "conf_status": status, "conf_basis": basis,
            "cap_bound": r["cap_bound"], "sbc_flip": r["sbc_flip"],
            "sbc_to_fcf_pct": r["sbc_to_fcf_pct"],
            "model_divergence_pct": (r["model_divergence"] * 100) if r["model_divergence"] else None,
            "discounts": discounts, "quality_score": quality,
            "analyzed_at": r["analyzed_at"],
        })

    total_quality = sum(row["quality_score"] for row in rows)
    for row in rows:
        row["weight_raw"] = row["quality_score"] / total_quality

    # 종목당 상한 강제(v3.67 수렴버그 수정판과 동일한 흡수 알고리즘 재사용)
    _EPS = 1e-12
    for _ in range(50):
        excess = 0.0
        absorbers = []
        for row in rows:
            if row["weight_raw"] > PER_STOCK_CAP:
                excess += row["weight_raw"] - PER_STOCK_CAP
                row["weight_raw"] = PER_STOCK_CAP
            elif row["weight_raw"] < PER_STOCK_CAP - _EPS:
                absorbers.append(row)
        if excess < 1e-12 or not absorbers:
            break
        total_absorb = sum(r["weight_raw"] for r in absorbers)
        for row in absorbers:
            row["weight_raw"] += excess * (row["weight_raw"] / total_absorb)
    else:
        over = [(r["ticker"], r["weight_raw"]) for r in rows if r["weight_raw"] > PER_STOCK_CAP + 1e-9]
        if over:
            raise RuntimeError(f"종목당 상한 강제가 수렴하지 못했다: {over}")

    for row in rows:
        row["weight_final"] = row["weight_raw"]

    rows.sort(key=lambda r: -r["weight_final"])

    print(f"\n{'종목':6}{'군집':22}{'등급':4}{'Gap':>9}{'Conf(엔진)':>10}{'Conf(조정)':>10}"
          f"{'상태':10}  할인  {'비중':>8}")
    for row in rows:
        d = ",".join(row["discounts"]) or "-"
        print(f"{row['ticker']:6}{row['cluster']:22}{row['grade']:4}{row['gap_pct']:+8.2f}%p"
              f"{row['conf_engine']:>10}{row['conf_adj']:>10}{row['conf_status']:>10}  {d:38}"
              f"{row['weight_final']*100:7.2f}%")

    print(f"\n합계 비중: {sum(r['weight_final'] for r in rows)*100:.4f}%")
    print(f"종목당 상한({PER_STOCK_CAP*100:.0f}%)에 걸린 종목: "
          f"{[r['ticker'] for r in rows if abs(r['weight_final']-PER_STOCK_CAP) < 1e-9]}")

    print("\n" + "=" * 100)
    print("위험군집 진단(배분에 쓰지 않음 - 목표비중을 두지 않았으므로 결과를 그대로 관찰만 한다)")
    print("=" * 100)
    cluster_weight = {}
    cluster_tickers = {}
    for row in rows:
        cluster_weight.setdefault(row["cluster"], 0.0)
        cluster_weight[row["cluster"]] += row["weight_final"]
        cluster_tickers.setdefault(row["cluster"], []).append(row["ticker"])
    for c, w in sorted(cluster_weight.items(), key=lambda x: -x[1]):
        print(f"  {c:24}{w*100:6.2f}%  ({len(cluster_tickers[c])}종목: {', '.join(cluster_tickers[c])})")
    max_cluster = max(cluster_weight.items(), key=lambda x: x[1])
    print(f"\n  최대 단일군집: {max_cluster[0]} {max_cluster[1]*100:.2f}%")

    unverified = [r for r in rows if r["conf_status"] == "미검증"]
    unverified_weight = sum(r["weight_final"] for r in unverified)
    print(f"\n미검증(정성조사 미실시) 종목 비중 합계: {unverified_weight*100:.2f}% ({len(unverified)}종목)")
    print("  이 종목들의 Confidence 94/89는 '확신도 높음'이 아니라 '아직 확인 안 됨'이다.")

    print("\n" + "=" * 100)
    print("이 포트폴리오가 제공하지 않는 것")
    print("=" * 100)
    for x in [
        "공분산 기반 최적화(수익률 상관행렬 데이터 없음)",
        "위험군집 목표비중(PHASE 2 감사 - 근거 없는 목표가 자본의 16.75~18.82%를 좌우한 선례 반복 방지)",
        "실현수익률 검증(이 포트폴리오 자체가 사전등록된 예측일 뿐 성과 검증 0건)",
        "Confidence의 확률적 해석(UNCALIBRATED - 판정 재현율일 뿐 승률이 아님)",
        f"미검증 20종목({unverified_weight*100:.1f}%)의 정성 심층조사 - S/A 유니버스가 급증한 만큼 다음 우선순위",
    ]:
        print(f"  - {x}")

    out = {
        "generated_at": "2026-09-05",
        "methodology": "quality_score(Gap%p x Confidence_adj/100) 순위배분, 위험군집 목표비중 없음, "
                        "종목당 상한 12%만 강제. 새 밸류에이션 로직 0줄 - 전부 저장된 ledger 재사용.",
        "n_universe": n,
        "positions": rows,
        "cluster_diagnostics": {c: {"weight": w, "tickers": cluster_tickers[c]}
                                  for c, w in cluster_weight.items()},
        "unverified_weight_pct": unverified_weight * 100,
        "not_provided": [
            "공분산 기반 최적화", "위험군집 목표비중", "실현수익률 검증",
            "Confidence의 확률적 해석", "미검증 종목의 정성 심층조사",
        ],
    }
    os.makedirs("reports", exist_ok=True)
    out_path = "reports/sa_portfolio_2026-09-05.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"\n결과 저장: {out_path}")
    return rows


if __name__ == "__main__":
    main()
