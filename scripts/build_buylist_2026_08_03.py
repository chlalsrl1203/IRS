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
그대로 두면 사실상 단일 베팅 - 40%로 강제 캡). 아래는 **명목 목표비중**이다:
  growth_platform 40% / insurance 30% / industrial_stalwart 20% / travel 10%

**v3.29(2026-08-04) - 목표비중 동적 상한 재설계**: 명목 목표비중은 종목수와
무관한 고정값이라, 버킷 종목수가 줄면(1종목 x 12%캡 = 최대 12%인데 명목
목표가 20%인 경우처럼) 구조적으로 달성 불가능한 목표가 생긴다. ROP가
A등급에서 이탈(아래 갱신 참고)하며 industrial_stalwart가 정확히 이 상태에
빠졌다 - 실증사례가 생겼으므로 하드코딩된 예외 처리 대신 일반 규칙을
`effective_bucket_targets()`로 배선했다: 버킷 목표가 `종목수 x 종목당상한`
을 넘으면 그 상한까지 깎고, 초과분을 나머지(캡에 안 걸린) 버킷들에 **명목
목표비중 비율대로** 재분배한다. industrial_stalwart(GEN 1종목)를 억지로
다른 버킷과 합치거나(공통 리스크축이 없는 종목끼리 묶는 건 이 스크립트의
"실제 사업모델·리스크요인 군집화" 원칙에 위배) 20% 목표를 그냥 방치하지도
않는, 재사용 가능한 일반 해법이다. 향후 어느 버킷이든 종목수가 줄어들면
(또는 새 종목 편입으로 다시 늘어나면) 자동으로 재계산된다.

**v3.30(2026-08-04, 사용자 요청 "모두 실사용목표 90%까지 올려") - 버킷
목표 최소 달성률 바닥**: v3.29는 달성 불가능한 목표를 "달성 가능한 데까지"
깎기만 해서, industrial_stalwart가 명목 20% 대비 12%(달성률 60%)까지
떨어지는 걸 그대로 뒀다. `MIN_BUCKET_TARGET_ACHIEVEMENT = 0.90`을 도입해
**어떤 버킷도 명목목표의 90% 밑으로는 내려가지 않게** 바닥을 깔았다.

⚠️ **이 바닥은 종목당 상한(PER_STOCK_CAP)과 직접 충돌한다**. 1종목뿐인
버킷은 상한 때문에 애초에 12%가 최대인데 바닥은 18%를 요구하므로, 둘 중
하나는 포기해야 한다. 이 규칙은 **버킷 목표 달성을 단일종목 과다집중
방지보다 우선**하도록 정했고(사용자 요청 그대로), 해당 버킷에 한해
종목당 상한을 필요한 만큼(여기서는 12%→18%) 완화한다. 전역 상한을 올리는
게 아니라 **버킷별 상한**으로 관리해, 상한 완화가 필요 없는 버킷
(growth_platform/insurance/travel)은 12%를 그대로 유지한다.

실측 영향: GEN이 12%→**18%로 최대 보유종목**이 됐다. GEN은 Confidence
70으로 최하위권(BRO와 공동)이고 M&A 연결효과로 성장상한이 바인딩된
종목이라, 이 집중이 의도된 것인지 매 실행마다 확인할 것 - 실행 시
완화된 상한과 해당 종목 비중을 경고문으로 명시 출력한다.

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
`industrial_stalwart` 버킷이 GEN 1종목만 남아 명목목표(20%)를 구조적으로
못 채우게 됐다. 1차로 정규화 후 2차 전역 캡 강제 패스를 추가해 "이미
캡된 종목까지 재상승"하는 버그는 막았지만, 그것만으로는 industrial_
stalwart의 미달분이 여전히 암묵적으로 나머지 버킷에 흘러들어가는 문제가
남아 있었다 - 바로 위 v3.29 항목의 `effective_bucket_targets()`로
근본적으로 재설계해 명시적·비례적 재분배로 바꿨다(2차 전역 캡 패스는
안전망으로 유지).

실행: python3 scripts/build_buylist_2026_08_03.py
"""

import glob
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

# 명목 목표비중 - 종목수와 무관한 "이상적" 분산 목표. 실제 배분에는
# effective_bucket_targets()로 계산한 실사용 목표비중을 쓴다.
NOMINAL_BUCKET_TARGET = {
    "growth_platform": 0.40,
    "insurance": 0.30,
    "industrial_stalwart": 0.20,
    "travel": 0.10,
}

# 버킷 목표 최소 달성률 - v3.30(2026-08-04 사용자 요청 "모두 실사용목표 90%까지
# 올려"). 어떤 버킷도 명목 목표의 이 비율 밑으로는 내려가지 않는다.
# ⚠️ 이 바닥은 PER_STOCK_CAP(종목당 상한)과 **직접 충돌한다** - 종목수가 적은
# 버킷은 상한 때문에 애초에 목표를 못 채우기 때문이다(예: 1종목 x 12% = 12%가
# 최대인데 명목목표가 20%면 달성률 60%). 둘 중 하나를 포기해야 하고, 이 규칙은
# **버킷 바닥을 우선**해 해당 버킷에 한해 종목당 상한을 필요한 만큼 완화한다.
# 즉 종목수가 적은 버킷일수록 개별 종목 집중도가 높아진다 - 이 트레이드오프가
# 눈에 보이도록 실행 시 완화된 상한을 명시적으로 출력한다.
MIN_BUCKET_TARGET_ACHIEVEMENT = 0.90


def effective_bucket_targets(
    bucket_counts: dict,
    nominal_targets: dict,
    per_stock_cap: float,
    min_achievement: float = MIN_BUCKET_TARGET_ACHIEVEMENT,
) -> tuple:
    """
    버킷별 실사용 목표비중과 **버킷별 종목당 상한**을 함께 계산한다.

    규칙:
      1) 버킷 목표가 `종목수 x 종목당상한`을 넘으면 달성 가능한 데까지 깎되,
      2) 명목목표의 min_achievement(기본 90%) 밑으로는 내리지 않는다 - 그
         아래로 갈 상황이면 대신 **그 버킷의 종목당 상한을 완화**해서
         바닥을 지킨다(v3.30).
      3) 깎인 만큼의 미달분은 캡에 안 걸린 나머지 버킷들에 명목 비중
         비율대로 재분배해 합계 100%를 유지한다.

    종목수가 늘거나 줄면 자동 재계산되는 일반 규칙 - 특정 버킷을
    하드코딩으로 예외처리하지 않는다.

    반환: (실사용 목표비중 dict, 버킷별 종목당 상한 dict)
    """
    targets = dict(nominal_targets)
    caps = {b: per_stock_cap for b in nominal_targets}
    capped = set()

    for _ in range(5):
        newly_capped = False
        for bucket, n in bucket_counts.items():
            if bucket in capped or n == 0:
                continue
            max_achievable = n * caps[bucket]
            if targets[bucket] > max_achievable + 1e-12:
                floor = nominal_targets[bucket] * min_achievement
                if max_achievable < floor:
                    caps[bucket] = floor / n   # 바닥을 지키려 상한을 완화
                    targets[bucket] = floor
                else:
                    targets[bucket] = max_achievable
                capped.add(bucket)
                newly_capped = True

        deficit = 1.0 - sum(targets.values())
        remaining = [b for b in targets if b not in capped and bucket_counts.get(b, 0) > 0]
        if abs(deficit) < 1e-12 or not remaining:
            break
        remaining_nominal_sum = sum(nominal_targets[b] for b in remaining)
        for bucket in remaining:
            targets[bucket] += deficit * (nominal_targets[bucket] / remaining_nominal_sum)
        if not newly_capped:
            break

    return targets, caps

# (조정 Confidence, 검증상태, 근거)
CONFIDENCE_ADJ = {
    "PDD":  (75, "검증", "2026-08-02 심층조사: SAMR 물리충돌·확대된 사기조사(신규 거버넌스 리스크). 희석은 무해."),
    "MNDY": (65, "검증", "2026-08-02 심층조사: S등급 7종목 중 최우려 - FY2027목표 철회+주가-21%급락(원분석 누락)+진행중 증권소송."),
    "DUOL": (78, "검증", "2026-08-02 심층조사: 내부자 순매도만 확인(매수 없음)+증권소송(초기)+신규 AI경쟁사 Speak, 다만 DAU는 여전히 견조."),
    "ACGL": (83, "검증", "2026-08-03 심층조사: 준비금·자본배분·거버넌스 양호(신용등급 상향), ex-cat 마진 2분기연속 소폭악화."),
    "PGR":  (87, "검증", "2026-08-03 심층조사: 성장추정 정합적이나 텔레매틱스 모트가 손해율 우위로 미이어짐(GEICO/Allstate가 더 나음)."),
    "SE":   (79, "검증", "2026-08-03 심층조사: Shopee EBITDA 역성장(TikTok Shop 방어비용), 그룹이익은 Garena 단독부담."),
    "TTD":  (45, "검증(하향)", "2026-08-13 재검토: 반증조건 4개 중 3개 동시 발동(thesis_monitor) - "
             "Q2 매출 $715M<가이던스$750M, Q3 가이던스 -12.1%YoY 역성장(회사 자체 제시), "
             "CFO·CMO·커머셜총괄 동시교체(2026-08-06). growth_scorecard 교차검증도 독립적으로 "
             "동일결론(저평가 판정 최소선 4.69% vs 회사 Q3 가이던스 -12.1% - 판정 자체가 뒤집힘). "
             "gap_decay: 주가 -26.3%로 공식 Gap이 오히려 +17.01%p->+20.96%p로 벌어짐(가치함정 "
             "패턴 - 사업이 나빠져도 시총만 빠지면 Gap은 개선된 것처럼 보인다). 2026-08-03 원조사"
             "(증권사기소송+CEO내부자거래혐의, 당시 72)가 예상한 거버넌스 리스크가 이번에 실적・"
             "가이던스로 실현됨 - governance-risk 단계에서 confirmed-deterioration 단계로 격상. "
             "다만 공식 Gap/RAR/판정은 변경하지 않는다(growth_scorecard 원칙상 realized_quarterly"
             "・guidance_annual은 usable_as_override 아님 - 다년 실적 확인 전까지는 병기만)."),
    "GEN":  (70, "검증", "2026-08-04 심층조사: ROIC 9.15%(5y평균 20.74%대비 급락, 단일출처 미검증)+TBS세그먼트마진 30%vs61%+시장은 27%매출성장에도 -9%로 반응(멀티플압축)."),
    "UBER": (83, "검증", "2026-08-04 심층조사: Prop22로 CA 리스크는 durably 해소됐으나 Waymo가 Atlanta/Austin 배타권 종료(자체앱 2028-01)로 파트너 프레이밍 약화, EU Directive(2026-12) 미해결."),
    "WDAY": (81, "검증", "2026-08-04 심층조사: 자사주매입이 SBC 2배속 상회(긍정적)하나 Mobley소송 확대(3월 기각argument 패소)+AI네이티브경쟁 실측화(Ramp/Rippling ARR$1B+) - SBC교차검증 플립 근접종목이라 특히 주의."),
    "ROP":  (77, "검증", "2026-08-04 심층조사: 회사공시 오가닉성장률 5-6%(3년연속감속)가 12%Lynch캡과 큰 괴리 확인 - Gap크기의 근거가 약함(재실행시 +1~5%p로 축소 가능), 레버리지도 2.9x→3.4x 상승."),
    "TCOM": (80, "검증", "2026-08-04 심층조사: SEC CORRESP로 확인된 中규제리스크 공시완화 이력(증권소송과 직결)+자체가이던스(+3~8%)가 Realistic Growth(12.39%) 크게 하회. DRS73.6(트래커최고)은 타당성 재확인됨."),
    "BRO":  (70, "검증", "2026-08-04 심층조사: 오가닉성장률 7분기연속감속해 2회 마이너스(-2.8%/-0.7%) 확인 - 시장이 이미 멀티플 17.8x→12.9x로 재평가 완료. 레버리지 2.77x, M&A주식대가 다일루션 ~19%(SBC와 별개) 신규 확인."),
}

SEVERE_FLAG = {"TTD"}  # 중대 거버넌스 적신호 - 추가 0.85x
# 반증조건 실제 발동(v3.42 thesis_monitor, 2026-08-13) - SEVERE_FLAG(거버넌스
# 리스크, 2026-08-03 시점)와는 축이 다른 별개 패널티다. 저건 "소송이 진행
# 중이다"라는 리스크였고 이건 "매출·가이던스가 실제로 꺾였다"는 확인된
# 결과라 둘 다 유효하게 별도로 곱한다. TTD가 이 시점 기준 유일한 해당 종목.
THESIS_BROKEN_FLAG = {"TTD"}  # 반증조건 3/4 발동 확인(thesis_monitor) - 추가 0.85x
PER_STOCK_CAP = 0.12

# 2026-08-16 모델선택 D3 연구의 ADOPT 결정을 결정경로에 배선하기 위한 입력.
# 그 연구가 실측한 것: 유니버스 편입 여부가 모델선택에 달린 종목이 4개이고
# (BRO·BSX·DSGX·VRT), 그중 BRO는 **이미 보유 중**인데 A등급 근거가 v3.15대
# 과거기록 답습이다. 그런데 이 스크립트는 그 사실을 전혀 참조하지 않고 있었다.
MODEL_SENSITIVITY_PATH = "reports/model_choice_sensitivity_2026-08-16.json"


def load_model_dependence(path=MODEL_SENSITIVITY_PATH):
    """
    티커별 모델선택 민감도를 읽어 dict로 돌려준다. 파일이 없으면 None.

    ⚠️ 파일이 없을 때 조용히 '의존 없음'으로 처리하지 않는다 - **데이터 없음을
    유리한 값으로 오독하지 않는다**는 원칙(is_insurer·sbc_cross_check·
    holdings_overlap의 '측정 불가 != 없음'과 동일)에 따라 None을 돌려주고
    호출부가 '미확인'으로 명시하게 한다.
    """
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return {r["ticker"]: r for r in json.load(f)["results"]}


SBC_HARVEST_PATH = "reports/sbc_harvest_2026-08-21.json"


def load_sbc_dependence(path=SBC_HARVEST_PATH):
    """
    티커별 SBC 차감 시나리오를 읽어 dict로 돌려준다. 파일이 없으면 None.

    `load_model_dependence`와 **같은 이유로** None을 돌려준다 - SBC 미확보를
    조용히 '무해'로 처리하면 정확히 R-001 감사가 §24 False Robustness로 등록한
    상태가 재발한다(25/34가 `FCF_DOWNSIDE_NOT_TESTED`인데 안정도는 높게 나옴).

    ⚠️ SBC 차감은 Gap을 **반드시 낮춘다**(fcf0 감소 -> Implied Growth 상승).
    따라서 이 검토는 유니버스 **이탈만** 만들 수 있고 진입은 만들 수 없다 -
    모델선택 검토가 양방향인 것과 구조적으로 다르므로 '진입' 절을 두지 않는다.
    """
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        rows = json.load(f)["results"]
    return {r["ticker"]: r for r in rows if r.get("status") == "OK"}


SIGNAL_INDEPENDENCE_PATH = "reports/signal_independence_2026-08-21.json"


def load_sbc_signal_verdict(path=SIGNAL_INDEPENDENCE_PATH):
    """
    SBC 이탈 신호가 **일관 적용 후에도 살아남는지**(PHASE 1, 2026-08-21).

    ⚠️ 왜 필요한가 — 실측으로 확인된 인공물이 있다.
    `sbc_cross_check`는 SBC를 **수준(fcf0)에만** 적용하고 성장경로(FCF CAGR)에는
    적용하지 않는다. RG가 FCF CAGR로 결정되고 Lynch 캡이 안 걸린 종목에서는
    두 효과가 반대 방향이라, 부분 적용이 신호를 **만들어내거나 지울 수 있다**:

        TCOM  부분 +5.28%p(B, 이탈)  ->  일관 +7.50%p(A, 이탈 안 함)   CANCELLED
        TTD   부분 +5.51%p(B, 이탈)  ->  일관 −5.24%p(D, 더 심함)      SURVIVES

    즉 어제(RQ-002) TCOM을 SBC 근거로 지목한 것은 틀렸다 — TCOM의 진짜 신호는
    성장률 축 하나다. 이 파일이 그 구분을 자본배분 경로에 전달한다.

    파일이 없으면 None — '왜곡 없음'이 아니라 '미확인'이다(기존 두 로더와 동일).
    """
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        rows = json.load(f)["results"]
    return {r["ticker"]: r for r in rows}


def main():
    data = json.load(open("reports/portfolio_ranking_2026-08-02.json"))
    universe = {r["ticker"]: r for r in data if r["grade"] in ("S", "A")}
    n_universe = len(universe)

    # ── 2단계: 팩터/섹터 집중도 진단 ────────────────────────────────────
    print("=" * 100)
    print(f"2단계 - 팩터/섹터 집중도 진단 (현재 상태: S/A등급 {n_universe}종목 단순 동일가중 가정시)")
    print("=" * 100)
    bucket_count = {b: 0 for b in NOMINAL_BUCKET_TARGET}
    for t in universe:
        bucket_count[BUCKET[t]] += 1
    for b, n in sorted(bucket_count.items(), key=lambda x: -x[1]):
        tickers = [t for t in universe if BUCKET[t] == b]
        print(f"  {b:22} {n:2}종목 ({n/n_universe*100:4.1f}%)  {', '.join(tickers)}")
    print(f"\n  -> growth_platform 단일 버킷이 종목수 기준 {bucket_count['growth_platform']}/{n_universe}="
          f"{bucket_count['growth_platform']/n_universe*100:.0f}%를 차지 - 사실상 '폭락한 고베타 성장주'라는")
    print("     단일 팩터에 몰빵된 상태. 동일가중 매수는 분산이 아니라 집중이다.")

    bucket_target, bucket_cap = effective_bucket_targets(
        bucket_count, NOMINAL_BUCKET_TARGET, PER_STOCK_CAP
    )
    print(f"\n  버킷별 목표비중 (명목 -> 실사용, 최소 달성률 {MIN_BUCKET_TARGET_ACHIEVEMENT*100:.0f}% 보장):")
    for b in NOMINAL_BUCKET_TARGET:
        nominal, effective, cap = NOMINAL_BUCKET_TARGET[b], bucket_target[b], bucket_cap[b]
        achievement = effective / nominal if nominal else 1.0
        if cap > PER_STOCK_CAP + 1e-9:
            note = (f"  <- {bucket_count[b]}종목뿐이라 기본상한({PER_STOCK_CAP*100:.0f}%)으로는 "
                    f"{bucket_count[b]*PER_STOCK_CAP*100:.0f}%가 최대 - 달성률 바닥을 지키려 "
                    f"**이 버킷 종목당 상한을 {cap*100:.1f}%로 완화**")
        elif effective > nominal + 1e-9:
            note = "  <- 다른 버킷의 미달분을 명목비중 비율로 흡수"
        else:
            note = ""
        print(f"    {b:22} 명목 {nominal*100:4.1f}%  ->  실사용 {effective*100:5.2f}% "
              f"(달성률 {achievement*100:5.1f}%){note}")

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
        if t in THESIS_BROKEN_FLAG:
            quality *= 0.85
        rows.append({
            "ticker": t, "bucket": bucket, "grade": r["grade"],
            "gap_pct": r["gap_pct"], "conf_engine": r["confidence"],
            "conf_adj": conf_adj, "conf_status": status,
            "cap_bound": r["cap_bound"], "severe_flag": t in SEVERE_FLAG,
            "thesis_broken_flag": t in THESIS_BROKEN_FLAG,
            "quality_score": quality, "basis": basis,
        })

    bucket_quality_sum = {}
    for row in rows:
        bucket_quality_sum.setdefault(row["bucket"], 0)
        bucket_quality_sum[row["bucket"]] += row["quality_score"]

    for row in rows:
        within_bucket_share = row["quality_score"] / bucket_quality_sum[row["bucket"]]
        row["weight_raw"] = within_bucket_share * bucket_target[row["bucket"]]

    # 종목당 상한 적용 + 초과분은 **같은 버킷 안에서만** 재분배한다(버킷
    # 목표비중을 지키기 위함 - 버킷을 넘나들며 재분배하면 insurance가 캡에
    # 걸렸다고 growth_platform 비중이 몰래 늘어나는 부작용이 생긴다). 이제
    # bucket_target 자체가 이미 종목수 제약을 반영했으므로(v3.29), 이
    # 패스는 버킷 "내부"에서 quality_score 편차가 큰 경우의 잔여 안전망이다.
    # 상한은 전역 PER_STOCK_CAP이 아니라 **버킷별 상한**(v3.30에서 달성률
    # 바닥을 지키려 완화됐을 수 있음)을 쓴다.
    for bucket_name in bucket_target:
        bucket_rows = [r for r in rows if r["bucket"] == bucket_name]
        cap = bucket_cap[bucket_name]
        for _ in range(5):
            excess = 0.0
            uncapped = []
            for row in bucket_rows:
                if row["weight_raw"] > cap:
                    excess += row["weight_raw"] - cap
                    row["weight_raw"] = cap
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
    # 균일하게 끌어올리면서 **이미 캡된 종목까지 상한을 넘게 재상승**하는
    # 부작용이 생긴다(2026-08-04 ROP 등급이탈로 실제 발생 확인 - industrial_
    # stalwart가 20%→13.04%로 미달되며 ACGL/PGR/GEN이 전부 13.04%로 상승).
    # 종목당 상한은 버킷 재분배 이후에도 다시 강제해야 한다 - 여기서도
    # 전역 PER_STOCK_CAP이 아니라 **각 종목이 속한 버킷의 상한**을 쓴다.
    for _ in range(5):
        excess = 0.0
        uncapped = []
        for row in rows:
            cap = bucket_cap[row["bucket"]]
            if row["weight_final"] > cap:
                excess += row["weight_final"] - cap
                row["weight_final"] = cap
            else:
                uncapped.append(row)
        if excess < 1e-9 or not uncapped:
            break
        total_uncapped = sum(r["weight_final"] for r in uncapped)
        for row in uncapped:
            row["weight_final"] += excess * (row["weight_final"] / total_uncapped)

    # 적용된 버킷별 상한을 행마다 기록해둔다 - 나중에 리포트만 보고도
    # "이 종목이 왜 12%를 넘겼나"를 추적할 수 있어야 한다(v3.30).
    for row in rows:
        row["bucket_cap_applied"] = bucket_cap[row["bucket"]]
        row["bucket_target_effective"] = bucket_target[row["bucket"]]

    rows.sort(key=lambda r: -r["weight_final"])

    print("\n" + "=" * 100)
    print("3단계 - 최종 매수리스트 (규칙기반 배분, 공분산 최적화 아님)")
    print("=" * 100)
    header = (f"{'종목':6} {'버킷':20} {'Gap':>8} {'Conf(엔진)':>10} {'Conf(조정)':>10} "
              f"{'상태':10} {'캡바인딩':>7} {'적신호':>6} {'반증발동':>7} {'비중':>7}")
    print(header)
    print("-" * len(header))
    for row in rows:
        print(f"{row['ticker']:6} {row['bucket']:20} {row['gap_pct']:+7.2f}%p "
              f"{row['conf_engine']:10} {row['conf_adj']:10} {row['conf_status']:10} "
              f"{'Y' if row['cap_bound'] else '':>7} {'Y' if row['severe_flag'] else '':>6} "
              f"{'Y' if row['thesis_broken_flag'] else '':>7} "
              f"{row['weight_final']*100:6.2f}%")

    print("\n버킷별 실제 배분 합계 (실사용 목표치·명목 달성률과 대조):")
    actual_bucket = {b: 0.0 for b in NOMINAL_BUCKET_TARGET}
    for row in rows:
        actual_bucket[row["bucket"]] += row["weight_final"]
    for b, target in bucket_target.items():
        nominal = NOMINAL_BUCKET_TARGET[b]
        print(f"  {b:22} 실사용목표 {target*100:5.2f}%  ->  실제 {actual_bucket[b]*100:5.2f}% "
              f"(명목 {nominal*100:4.1f}% 대비 달성률 {actual_bucket[b]/nominal*100:5.1f}%)")

    relaxed = {b: c for b, c in bucket_cap.items() if c > PER_STOCK_CAP + 1e-9}
    if relaxed:
        print(f"\n⚠️ 달성률 바닥({MIN_BUCKET_TARGET_ACHIEVEMENT*100:.0f}%)을 지키느라 종목당 상한이 완화된 버킷:")
        for b, cap in relaxed.items():
            holders = [r for r in rows if r["bucket"] == b]
            names = ", ".join(f"{r['ticker']} {r['weight_final']*100:.2f}%" for r in holders)
            print(f"   {b}: 기본 {PER_STOCK_CAP*100:.0f}% -> {cap*100:.1f}%  ({names})")
        print("   이 규칙은 '버킷 목표 달성'을 '단일종목 과다집중 방지'보다 우선한 결과다.")
        print("   종목수가 적은 버킷일수록 개별 종목 비중이 커지므로, 해당 종목의")
        print("   Confidence·정성리스크를 특히 함께 볼 것(현재 GEN은 Conf 70으로 최하위권이며")
        print("   M&A 연결효과로 성장상한이 바인딩된 종목이다).")

    # ── 경계 검토: 유니버스 편입이 모델선택에 달려 있는가 ────────────────
    # 2026-08-16 모델선택 D3 연구의 ADOPT 결정("등급·유니버스 수준 모델의존성
    # 병기")을 실제 결정경로에 배선한 것이다. **비중은 하나도 바꾸지 않는다** -
    # 병기·자동판정 안 함 원칙 그대로이며 회귀 테스트가 이를 고정한다.
    # 이 블록은 weight_final이 전부 확정된 **뒤**에 키만 덧붙인다.
    dep = load_model_dependence()
    boundary = {"generated_at": "2026-08-16", "status": None,
                "held_but_model_dependent": [], "excluded_but_would_enter": [],
                "missing_from_ranking": []}
    # 노후화 점검: ledger에는 있는데 순위 파일에 없는 종목은 **어떤 판정도 받지
    # 않은 채** 유니버스에서 빠진다. 2026-08-16 실측에서 BSX가 정확히 이 경우였다
    # (순위는 08-02 생성, BSX 분석은 08-13). 판정에 의한 탈락과 파일 노후화에
    # 의한 탈락은 전혀 다른 것이므로 구분해서 드러낸다.
    ranked = {r["ticker"] for r in data}
    for p in sorted(glob.glob("ledger/*.json")):
        with open(p, encoding="utf-8") as f:
            led = json.load(f)
        t = led["meta"]["ticker"]
        if t not in ranked:
            boundary["missing_from_ranking"].append({
                "ticker": t, "gap_pct": led["expectation_gap"] * 100,
                "judgment": led["judgment"], "analyzed_at": led["meta"]["analyzed_at"][:10],
            })
    print("\n" + "=" * 100)
    print("경계 검토 - 유니버스 편입이 모델선택 하나에 달려 있는 종목 (비중 미변경)")
    print("=" * 100)
    if dep is None:
        boundary["status"] = "미확인"
        print(f"  ⚠️ {MODEL_SENSITIVITY_PATH}가 없어 **확인하지 못했다**.")
        print("     '의존 없음'이 아니라 '미확인'이다 - scripts/model_choice_sensitivity_2026_08_16.py를 먼저 실행할 것.")
        for row in rows:
            row["model_dependent_universe"] = None
    else:
        boundary["status"] = "확인"
        for row in rows:
            d = dep.get(row["ticker"])
            row["model_dependent_universe"] = (
                bool(d["buy_universe_depends_on_model"]) if d else None
            )
            if d and d["buy_universe_depends_on_model"]:
                row["grade_alternative_model"] = d["grade_alternative"]
                row["gap_alternative_model_pct"] = d["gap_alternative"] * 100
                boundary["held_but_model_dependent"].append({
                    "ticker": row["ticker"], "weight_final": row["weight_final"],
                    "grade": row["grade"], "grade_alternative": d["grade_alternative"],
                    "gap_pct": row["gap_pct"],
                    "gap_alternative_pct": d["gap_alternative"] * 100,
                    "model_chosen": d["model_chosen"],
                    "reason_is_prior_record": d["reason_is_prior_record"],
                })
        for r in data:
            d = dep.get(r["ticker"])
            if (r["grade"] not in ("S", "A") and d
                    and d["buy_universe_depends_on_model"]
                    and d["grade_alternative"] in ("S", "A")):
                boundary["excluded_but_would_enter"].append({
                    "ticker": r["ticker"], "grade": r["grade"],
                    "grade_alternative": d["grade_alternative"],
                    "gap_pct": r["gap_pct"],
                    "gap_alternative_pct": d["gap_alternative"] * 100,
                    "model_chosen": d["model_chosen"],
                    "reason_is_prior_record": d["reason_is_prior_record"],
                })

        held = boundary["held_but_model_dependent"]
        excl = boundary["excluded_but_would_enter"]
        if held:
            print("  [보유 중인데 편입 근거가 모델선택에 달림 - 거짓편입 위험]")
            for h in held:
                pr = " ⚠️사유가 과거기록 답습" if h["reason_is_prior_record"] else ""
                print(f"    {h['ticker']:6} 비중 {h['weight_final']*100:5.2f}%  "
                      f"{h['grade']}({h['gap_pct']:+.2f}%p) -> 대안모델이면 "
                      f"{h['grade_alternative']}({h['gap_alternative_pct']:+.2f}%p) 유니버스 이탈{pr}")
        if excl:
            print("  [유니버스 밖인데 대안모델이면 진입 - 거짓탈락 위험, BSX 스크리너 사건과 같은 유형]")
            for e in excl:
                pr = " ⚠️사유가 과거기록 답습" if e["reason_is_prior_record"] else ""
                print(f"    {e['ticker']:6}         "
                      f"{e['grade']}({e['gap_pct']:+.2f}%p) -> 대안모델이면 "
                      f"{e['grade_alternative']}({e['gap_alternative_pct']:+.2f}%p) 유니버스 진입{pr}")
        if not held and not excl:
            print("  모델의존 해당 종목 없음.")
        if boundary["missing_from_ranking"]:
            print("  [순위 파일 노후화로 아예 고려조차 안 된 종목 - 판정에 의한 탈락이 아님]")
            for m in boundary["missing_from_ranking"]:
                print(f"    {m['ticker']:6}         분석일 {m['analyzed_at']} "
                      f"Gap {m['gap_pct']:+.2f}%p '{m['judgment']}' - "
                      f"순위 파일(2026-08-02)이 이 종목보다 먼저 만들어져 누락됨")
        print("  ⚠️ 어느 모델이 옳은지는 판정하지 않는다 - 34종목 실측상 관측 가능한 성장")
        print("     프로파일이 두 모델 선택집단을 분리하지 못해 판정 근거가 이 저장소에 없다.")
        print("     비중은 이 검토로 조정되지 않았다(reports/research/model_choice_2026-08-16.md).")

    # ── 경계 검토 2: 유니버스 편입이 SBC 미차감 가정에 달려 있는가 ────────
    # 2026-08-21 실험(결정 #40 재개조건 충족 - SEC 원자료 확보)의 ADOPT 결과를
    # 같은 자리에 배선했다. 위 모델선택 검토와 완전히 같은 성질이다: **비중을
    # 바꾸지 않고**, weight_final이 확정된 뒤 키만 덧붙이며, 어느 쪽이 옳은지
    # 판정하지 않는다(SBC 전액차감/전액가산 둘 다 업계에서 논쟁적 - v3.23 원칙).
    sbc_dep = load_sbc_dependence()
    sig = load_sbc_signal_verdict()
    boundary["sbc"] = {"status": None, "held_but_sbc_dependent": [],
                       "unverified": [],
                       "signal_independence_checked": sig is not None}
    print("\n" + "=" * 100)
    print("경계 검토 2 - 유니버스 편입이 SBC 미차감 가정에 달려 있는 종목 (비중 미변경)")
    print("=" * 100)
    if sbc_dep is None:
        boundary["sbc"]["status"] = "미확인"
        for row in rows:
            row["sbc_dependent_universe"] = None
        print(f"  ⚠️ {SBC_HARVEST_PATH}가 없어 **확인하지 못했다**.")
        print("     '의존 없음'이 아니라 '미확인'이다 - scripts/sbc_harvest_2026_08_21.py를 먼저 실행할 것.")
    else:
        boundary["sbc"]["status"] = "확인"
        for row in rows:
            s = sbc_dep.get(row["ticker"])
            if s is None:
                # 확보 실패를 '무해'로 적지 않는다. None은 '모른다'는 뜻이다.
                row["sbc_dependent_universe"] = None
                boundary["sbc"]["unverified"].append(
                    {"ticker": row["ticker"], "weight_final": row["weight_final"]})
                continue
            leaves = (row["grade"] in ("S", "A")
                      and s.get("grade_sbc_adjusted") not in ("S", "A"))
            row["sbc_dependent_universe"] = bool(leaves)
            row["sbc_to_fcf_pct"] = s.get("sbc_to_fcf_pct")
            row["gap_sbc_adjusted_pct"] = (
                s["gap_sbc_adjusted"] * 100 if s.get("gap_sbc_adjusted") is not None else None)
            v = (sig or {}).get(row["ticker"], {})
            # SURVIVES / CANCELLED / UNKNOWN / NO_SIGNAL / NOT_IN_UNIVERSE
            row["sbc_signal_verdict"] = v.get("verdict")
            if leaves:
                boundary["sbc"]["held_but_sbc_dependent"].append({
                    "ticker": row["ticker"], "weight_final": row["weight_final"],
                    "grade": row["grade"], "grade_sbc_adjusted": s["grade_sbc_adjusted"],
                    "signal_verdict": v.get("verdict"),
                    "gap_sbc_consistent_pct": (
                        v["sbc_consistent"]["gap"] * 100
                        if v.get("sbc_consistent") else None),
                    "grade_sbc_consistent": (
                        v["sbc_consistent"]["grade"] if v.get("sbc_consistent") else None),
                    "gap_pct": row["gap_pct"],
                    "gap_sbc_adjusted_pct": s["gap_sbc_adjusted"] * 100,
                    "sbc_to_fcf_pct": s["sbc_to_fcf_pct"],
                })

        held_sbc = boundary["sbc"]["held_but_sbc_dependent"]
        if held_sbc:
            print("  [보유 중인데 편입 근거가 'SBC를 비용으로 보지 않는다'는 가정에 달림]")
            for h in held_sbc:
                print(f"    {h['ticker']:6} 비중 {h['weight_final']*100:5.2f}%  "
                      f"{h['grade']}({h['gap_pct']:+.2f}%p) -> SBC 차감시 "
                      f"{h['grade_sbc_adjusted']}({h['gap_sbc_adjusted_pct']:+.2f}%p) 유니버스 이탈  "
                      f"[SBC/FCF {h['sbc_to_fcf_pct']*100:.1f}%]")
                # 이 신호가 SBC의 경제적 효과인가, 부분 적용의 산물인가(PHASE 1).
                vd, gc, cc = (h.get("signal_verdict"),
                              h.get("gap_sbc_consistent_pct"),
                              h.get("grade_sbc_consistent"))
                if vd == "CANCELLED":
                    print(f"           ⚠️ 이 이탈은 **부분 적용의 산물이다** - SBC를 성장경로에도 "
                          f"일관 적용하면 {cc}({gc:+.2f}%p)로 이탈하지 않는다.")
                    print("              SBC를 이 종목의 재검토 근거로 삼지 말 것.")
                elif vd == "SURVIVES":
                    print(f"           일관 적용에서도 이탈 유지: {cc}({gc:+.2f}%p) - SBC 고유 신호.")
                elif vd == "UNKNOWN":
                    print("           ⚠️ 일관 적용을 계산하지 못했다 - '무해'가 아니라 '미확인'.")
                elif vd is None:
                    print(f"           ⚠️ {SIGNAL_INDEPENDENCE_PATH} 미확인 - "
                          "scripts/signal_independence_2026_08_21.py를 먼저 실행할 것.")
        else:
            print("  SBC 차감으로 유니버스를 이탈하는 보유 종목 없음.")
        if boundary["sbc"]["unverified"]:
            print("  [SBC 미확보 - '무해'가 아니라 '미확인']")
            for u in boundary["sbc"]["unverified"]:
                print(f"    {u['ticker']:6} 비중 {u['weight_final']*100:5.2f}%")
        # 경계 여유를 함께 보여준다 - 이탈하지 않았다고 안전한 것이 아니다.
        near = sorted(
            (r for r in rows if r.get("gap_sbc_adjusted_pct") is not None
             and r["grade"] in ("S", "A")),
            key=lambda r: abs(r["gap_sbc_adjusted_pct"] - 7.0))[:3]
        if near:
            print("  [A/B 경계(+7.00%p)까지 남은 여유 - SBC 차감 후 기준, 가까운 순]")
            for r in near:
                print(f"    {r['ticker']:6} 비중 {r['weight_final']*100:5.2f}%  "
                      f"SBC차감후 {r['gap_sbc_adjusted_pct']:+.2f}%p "
                      f"(여유 {r['gap_sbc_adjusted_pct'] - 7.0:+.2f}%p)")
        print("  ⚠️ SBC를 비용으로 볼지는 판정하지 않는다(전액차감/전액가산 둘 다 논쟁적).")
        print("     비중은 이 검토로 조정되지 않았다(reports/sbc_harvest_2026-08-21.json).")

    os.makedirs("reports", exist_ok=True)
    with open("reports/buylist_boundary_review_2026-08-16.json", "w", encoding="utf-8") as f:
        json.dump(boundary, f, ensure_ascii=False, indent=2)

    out_path = "reports/buylist_2026-08-03.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
    print(f"\n결과 저장: {out_path}")
    return rows


if __name__ == "__main__":
    main()
