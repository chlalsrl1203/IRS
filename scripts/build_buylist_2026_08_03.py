"""
S/A등급 13종목 팩터 진단 + 사이징 규칙 + 최종 매수리스트 - 2026-08-03.

경위: "S/A등급만 투자하는 건 비추천"(집중도·미검증확신도·사이징부재 지적) ->
"그럼 실제 매수리스트는 어떻게 만드나" -> 3단계 계획(1.정성심층조사
2.팩터/섹터 집중도 진단 3.사이징규칙+최종리스트) 중 1단계(S등급 7종목
전수 정성조사)를 마친 뒤, 이 스크립트로 2·3단계를 실행한다.

⚠️ 이 스크립트는 공분산 기반 포트폴리오 최적화가 아니다. 그런 최적화를
하려면 종목간 수익률 상관행렬이 필요한데 이 프로젝트는 그런 시계열
데이터를 갖고 있지 않다(포지션 사이징 자체가 알려진 스코프 갭). 대신
투명하고 검증 가능한 규칙 기반 배분이다 - CLAUDE.md의 "근거 없는 자동판정
보다 숫자를 드러내고 분석자가 해석하게 하라" 원칙과 동일하게, 가중치
산출 로직 전부를 코드로 노출한다.

**팩터 버킷 4개** (Lynch유형만으로는 못 잡는 실제 사업모델·리스크요인
군집화 - 예: PDD/MNDY/DUOL/SE/TTD/UBER/WDAY 7종목 전부 fast_grower지만
공통점은 그게 아니라 "최근 대폭락 스크리닝으로 발굴된 고베타 소비자/
플랫폼주"라는 점이다):
  growth_platform: PDD MNDY DUOL SE TTD UBER WDAY (7) - 폭락발굴 고성장주,
                   단일 팩터(위험선호 국면)에 몰빵될 위험
  insurance:       ACGL PGR BRO (3) - 손해율·준비금 사이클, 다른 리스크축
  industrial_stalwart: GEN (원래 ROP 포함 2종목 설계였으나 2026-08-04 ROP가
                   유기적성장 재검증으로 C등급 이탈 - 현재 GEN 단독, 아래
                   갱신 참고) - M&A영향권+성장상한 바인딩, 안정형
  travel:          TCOM (1) - 경기소비재 최상단

**버킷 목표비중**(관측: growth_platform이 종목수 7/13=54%를 차지해
그대로 두면 사실상 단일 베팅 - 40%로 강제 캡):
  growth_platform 40% / insurance 30% / industrial_stalwart 20% / travel 10%

**버킷 내 배분**: quality_score = Gap%p x (Confidence_adj/100), 정규화 후
버킷 목표비중에 곱함. 조정치:
  - 캡바인딩(성장분석이 결과에 기여 안 함, M-1): x0.85
  - 중대 거버넌스 적신호(TTD 증권사기소송+CEO 내부자거래 혐의): x0.85 추가
  - 종목당 상한 12%(단일종목 과다집중 방지)

**Confidence_adj**: 2026-08-02~04 정성심층조사를 거친 S/A등급 종목 전부
조사 결과를 반영한 조정치(CLAUDE.md/Notion에 기록된 범위의 중간값 또는 각
세션에서 직접 판단한 값). A등급 나머지 6종목(GEN/UBER/WDAY/ROP/TCOM/BRO)은
2026-08-04 배치에서 심층조사를 마쳐 전부 '검증' 상태로 전환됐다 - S등급
7종목과 마찬가지로 엔진이 볼 수 없는 영역(자본배분・회계품질・거버넌스・
희석・경쟁동향)을 확인한 상태다.

**2026-08-04 갱신 - ROP 등급이탈**: ROP의 정성심층조사가 유기적성장 교차
검증(Gap +7.74%p→+1.24%p, 판정 뒤집힘)을 실제로 공식판정에 반영
(`realistic_growth_override`, engine/pipeline.py v3.28)하면서 ROP가
A등급에서 C등급으로 빠져 S/A 유니버스가 13종목→12종목이 됐다.
`industrial_stalwart` 버킷이 GEN 1종목만 남아 목표비중(20%)을 못 채우는
구조적 문제가 생겼고(GEN 혼자 12%캡에 막혀 최대 12%까지만 가능), 이 과정
에서 **버킷 재분배 이후 전역 정규화가 이미 캡된 종목까지 12% 넘게
재상승시키는 버그**를 발견해 고쳤다(정규화 후 2차 전역 캡 강제 패스 추가 -
버킷당 목표 미달은 그대로 두되 종목당 12% 상한만큼은 어떤 경우에도 지킨다).
industrial_stalwart 버킷 구조(현재 GEN 단독) 자체를 재설계할지는 이후
세션 판단 사안으로 남긴다.

실행: python3 scripts/build_buylist_2026_08_03.py
"""

import json
import os

BUCKET = {
    "PDD": "growth_platform", "MNDY": "growth_platform", "DUOL": "growth_platform",
    "SE": "growth_platform", "TTD": "growth_platform", "UBER": "growth_platform",
    "WDAY": "growth_platform",
    "ACGL": "insurance", "PGR": "insurance", "BRO": "insurance",
    "GEN": "industrial_stalwart", "ROP": "industrial_stalwart",
    "TCOM": "travel",
}

BUCKET_TARGET = {
    "growth_platform": 0.40,
    "insurance": 0.30,
    "industrial_stalwart": 0.20,
    "travel": 0.10,
}

# (조정 Confidence, 검증상태, 근거)
CONFIDENCE_ADJ = {
    "PDD":  (75, "검증", "2026-08-02 심층조사: SAMR 물리충돌·확대된 사기조사(신규 거버넌스 리스크). 희석은 무해."),
    "MNDY": (65, "검증", "2026-08-02 심층조사: S등급 7종목 중 최우려 - FY2027목표 철회+주가-21%급락(원분석 누락)+진행중 증권소송."),
    "DUOL": (78, "검증", "2026-08-02 심층조사: 내부자 순매도만 확인(매수 없음)+증권소송(초기)+신규 AI경쟁사 Speak, 다만 DAU는 여전히 견조."),
    "ACGL": (83, "검증", "2026-08-03 심층조사: 준비금·자본배분·거버넌스 양호(신용등급 상향), ex-cat 마진 2분기연속 소폭악화."),
    "PGR":  (87, "검증", "2026-08-03 심층조사: 성장추정 정합적이나 텔레매틱스 모트가 손해율 우위로 미이어짐(GEICO/Allstate가 더 나음)."),
    "SE":   (79, "검증", "2026-08-03 심층조사: Shopee EBITDA 역성장(TikTok Shop 방어비용), 그룹이익은 Garena 단독부담."),
    "TTD":  (72, "검증", "2026-08-03 심층조사: 연방 증권사기소송 진행중(CEO 내부자거래 혐의 포함, 기각동의 기각) - S등급 7종목 중 최심각."),
    "GEN":  (70, "검증", "2026-08-04 심층조사: ROIC 9.15%(5y평균 20.74%대비 급락, 단일출처 미검증)+TBS세그먼트마진 30%vs61%+시장은 27%매출성장에도 -9%로 반응(멀티플압축)."),
    "UBER": (83, "검증", "2026-08-04 심층조사: Prop22로 CA 리스크는 durably 해소됐으나 Waymo가 Atlanta/Austin 배타권 종료(자체앱 2028-01)로 파트너 프레이밍 약화, EU Directive(2026-12) 미해결."),
    "WDAY": (81, "검증", "2026-08-04 심층조사: 자사주매입이 SBC 2배속 상회(긍정적)하나 Mobley소송 확대(3월 기각argument 패소)+AI네이티브경쟁 실측화(Ramp/Rippling ARR$1B+) - SBC교차검증 플립 근접종목이라 특히 주의."),
    "ROP":  (77, "검증", "2026-08-04 심층조사: 회사공시 오가닉성장률 5-6%(3년연속감속)가 12%Lynch캡과 큰 괴리 확인 - Gap크기의 근거가 약함(재실행시 +1~5%p로 축소 가능), 레버리지도 2.9x→3.4x 상승."),
    "TCOM": (80, "검증", "2026-08-04 심층조사: SEC CORRESP로 확인된 中규제리스크 공시완화 이력(증권소송과 직결)+자체가이던스(+3~8%)가 Realistic Growth(12.39%) 크게 하회. DRS73.6(트래커최고)은 타당성 재확인됨."),
    "BRO":  (70, "검증", "2026-08-04 심층조사: 오가닉성장률 7분기연속감속해 2회 마이너스(-2.8%/-0.7%) 확인 - 시장이 이미 멀티플 17.8x→12.9x로 재평가 완료. 레버리지 2.77x, M&A주식대가 다일루션 ~19%(SBC와 별개) 신규 확인."),
}

SEVERE_FLAG = {"TTD"}  # 중대 거버넌스 적신호 - 추가 0.85x
PER_STOCK_CAP = 0.12


def main():
    data = json.load(open("reports/portfolio_ranking_2026-08-02.json"))
    universe = {r["ticker"]: r for r in data if r["grade"] in ("S", "A")}

    # ── 2단계: 팩터/섹터 집중도 진단 ────────────────────────────────────
    print("=" * 100)
    print("2단계 - 팩터/섹터 집중도 진단 (현재 상태: S/A등급 13종목 단순 동일가중 가정시)")
    print("=" * 100)
    bucket_count = {}
    for t in universe:
        bucket_count[BUCKET[t]] = bucket_count.get(BUCKET[t], 0) + 1
    for b, n in sorted(bucket_count.items(), key=lambda x: -x[1]):
        tickers = [t for t in universe if BUCKET[t] == b]
        print(f"  {b:22} {n:2}종목 ({n/13*100:4.1f}%)  {', '.join(tickers)}")
    print(f"\n  -> growth_platform 단일 버킷이 종목수 기준 {bucket_count['growth_platform']}/13="
          f"{bucket_count['growth_platform']/13*100:.0f}%를 차지 - 사실상 '폭락한 고베타 성장주'라는")
    print("     단일 팩터에 몰빵된 상태. 동일가중 매수는 분산이 아니라 집중이다.")

    # ── 3단계: 사이징 규칙 적용 ──────────────────────────────────────────
    rows = []
    for t, r in universe.items():
        bucket = BUCKET[t]
        conf_adj, status, basis = CONFIDENCE_ADJ[t]
        quality = r["gap_pct"] * (conf_adj / 100)
        if r["cap_bound"]:
            quality *= 0.85
        if t in SEVERE_FLAG:
            quality *= 0.85
        rows.append({
            "ticker": t, "bucket": bucket, "grade": r["grade"],
            "gap_pct": r["gap_pct"], "conf_engine": r["confidence"],
            "conf_adj": conf_adj, "conf_status": status,
            "cap_bound": r["cap_bound"], "severe_flag": t in SEVERE_FLAG,
            "quality_score": quality, "basis": basis,
        })

    bucket_quality_sum = {}
    for row in rows:
        bucket_quality_sum.setdefault(row["bucket"], 0)
        bucket_quality_sum[row["bucket"]] += row["quality_score"]

    for row in rows:
        within_bucket_share = row["quality_score"] / bucket_quality_sum[row["bucket"]]
        row["weight_raw"] = within_bucket_share * BUCKET_TARGET[row["bucket"]]

    # 종목당 상한 적용 + 초과분은 **같은 버킷 안에서만** 재분배한다(버킷
    # 목표비중을 지키기 위함 - 버킷을 넘나들며 재분배하면 insurance가 캡에
    # 걸렸다고 growth_platform 비중이 몰래 늘어나는 부작용이 생긴다).
    for bucket_name in BUCKET_TARGET:
        bucket_rows = [r for r in rows if r["bucket"] == bucket_name]
        for _ in range(5):
            excess = 0.0
            uncapped = []
            for row in bucket_rows:
                if row["weight_raw"] > PER_STOCK_CAP:
                    excess += row["weight_raw"] - PER_STOCK_CAP
                    row["weight_raw"] = PER_STOCK_CAP
                else:
                    uncapped.append(row)
            if excess < 1e-9 or not uncapped:
                break
            total_uncapped = sum(r["weight_raw"] for r in uncapped)
            for row in uncapped:
                row["weight_raw"] += excess * (row["weight_raw"] / total_uncapped)

    total_weight = sum(row["weight_raw"] for row in rows)
    for row in rows:
        row["weight_final"] = row["weight_raw"] / total_weight  # 정규화(합계 100%)

    # ⚠️ 버킷 하나가 목표비중을 못 채우면(예: 종목이 1개뿐이라 12%캡에 막혀
    # 20% 목표에 못 미침) total_weight < 1이 되고, 위 정규화가 전체 행을
    # 균일하게 끌어올리면서 **이미 12%로 캡된 종목까지 12% 넘게 재상승**하는
    # 부작용이 생긴다(2026-08-04 ROP 등급이탈로 실제 발생 확인 - industrial_
    # stalwart가 20%→13.04%로 미달되며 ACGL/PGR/GEN이 전부 13.04%로 상승).
    # 종목당 상한은 버킷 재분배 이후에도 전역적으로 다시 강제해야 한다 -
    # 버킷 다양화 목적은 이미 달성됐으므로 이 2차 패스는 버킷 구분 없이
    # 전체 행에 대해 상한을 지키고 초과분을 미캡 종목에 비례 재분배한다.
    for _ in range(5):
        excess = 0.0
        uncapped = []
        for row in rows:
            if row["weight_final"] > PER_STOCK_CAP:
                excess += row["weight_final"] - PER_STOCK_CAP
                row["weight_final"] = PER_STOCK_CAP
            else:
                uncapped.append(row)
        if excess < 1e-9 or not uncapped:
            break
        total_uncapped = sum(r["weight_final"] for r in uncapped)
        for row in uncapped:
            row["weight_final"] += excess * (row["weight_final"] / total_uncapped)

    rows.sort(key=lambda r: -r["weight_final"])

    print("\n" + "=" * 100)
    print("3단계 - 최종 매수리스트 (규칙기반 배분, 공분산 최적화 아님)")
    print("=" * 100)
    header = (f"{'종목':6} {'버킷':20} {'Gap':>8} {'Conf(엔진)':>10} {'Conf(조정)':>10} "
              f"{'상태':6} {'캡바인딩':>7} {'적신호':>6} {'비중':>7}")
    print(header)
    print("-" * len(header))
    for row in rows:
        print(f"{row['ticker']:6} {row['bucket']:20} {row['gap_pct']:+7.2f}%p "
              f"{row['conf_engine']:10} {row['conf_adj']:10} {row['conf_status']:6} "
              f"{'Y' if row['cap_bound'] else '':>7} {'Y' if row['severe_flag'] else '':>6} "
              f"{row['weight_final']*100:6.2f}%")

    print("\n버킷별 실제 배분 합계 (목표치와 대조):")
    actual_bucket = {}
    for row in rows:
        actual_bucket.setdefault(row["bucket"], 0)
        actual_bucket[row["bucket"]] += row["weight_final"]
    for b, target in BUCKET_TARGET.items():
        print(f"  {b:22} 목표 {target*100:4.1f}%  ->  실제 {actual_bucket[b]*100:5.2f}%")

    os.makedirs("reports", exist_ok=True)
    out_path = "reports/buylist_2026-08-03.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
    print(f"\n결과 저장: {out_path}")
    return rows


if __name__ == "__main__":
    main()
