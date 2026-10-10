# QSI 판독 루브릭 v1 (2026-10-07 사전 고정)

QSI 3단계 — 규칙으로 뽑을 수 없는 질문을 **사람(분석자)이 원문을 읽고** 답한다. 이 문서는 판독을 시작하기
**전에** 고정했고, 결과를 보고 바꾸지 않는다. 두 판독자(1차·2차)가 서로의 답을 보지 않고 같은 증거 묶음을
읽으며, **두 답이 같을 때만** 채택한다. 다르면 `unknown`(사유: 판독 불일치)으로 남긴다.

## 공통 원칙

1. 증거 묶음 안의 원문만 근거로 쓴다. 기억·외부 지식으로 답하지 않는다.
2. 모든 답에는 근거 인용 1개 이상(증거 묶음의 문장 **그대로**, 40~400자)이 필요하다. 코드가 원문과 글자 단위로
   대조하며, 일치하지 않으면 그 답은 버려진다.
3. 확신이 없으면 `unknown`. 판단 보류가 틀린 답보다 낫다.
4. 위험요인의 가정문('could', 'may')은 사실의 근거가 아니다.

## 질문별 결정 규칙

### gov.key_person_no_succession (bool) — 핵심 인물 의존이 크면서 승계 계획이 없는가?
- **True**: 회사가 특정 인물(이름 또는 창업자/CEO 직함)에 대한 의존을 명시하고, 증거 묶음 어디에도 이사회의
  CEO(경영진) 승계 계획이 언급되지 않는다.
- **False**: 이사회·위원회가 **CEO 또는 경영진 승계 계획**을 수립·검토한다는 진술이 있다(이사회 승계만으로는 부족).
- 그 밖: unknown.

### gov.ceo_succession_policy (bool) — CEO 승계 정책이 공시돼 있는가?
- **True**: CEO(또는 최고경영진) 승계 계획을 이사회/위원회가 책임진다는 진술.
- **False**: 위임장·연차보고서의 지배구조 절을 읽었는데 CEO 승계 언급이 없다(이사회 승계만 있음).
- 증거 묶음에 지배구조 절이 없으면 unknown.

### gov.chair_separated (bool) — 의장과 CEO가 분리돼 있는가?
- 현재 의장과 현재 CEO가 다른 사람이면 True, 같은 사람이면 False. 공동 CEO 중 1명이 의장이면 False.
- 과거·타사 이력 문장은 쓰지 않는다.

### gov.material_litigation (enum: none / immaterial / material)
- **material**: 회사가 결과에 따라 재무에 중대한 영향이 있을 수 있다고 진술하거나, 손실 충당·합의금이 연간
  영업이익의 5% 이상이거나, 핵심 사업 모델(예: 독점·규제 위반 집단소송)을 겨냥한 진행 중 소송.
- **immaterial**: 회사가 진행 중 소송이 중대한 영향을 주지 않을 것이라고 진술(경영진 판단 포함).
- **none**: 회사가 진행 중 소송이 없다고 진술.

### acc.material_one_time_items (bool) — FCF·영업이익을 흔들 만한 일회성 항목이 있는가?
- 최근 회계연도(또는 최근 4개 분기) 실적 보도자료의 GAAP↔비GAAP 조정표·현금흐름에서, 주식보상비용·무형자산
  상각을 **제외한** 일회성 항목(구조조정·손상·소송합의·처분손익·인수 관련 비용·세금 일회성) 합계가 GAAP
  영업이익(또는 FCF)의 **10% 이상**이면 True, 미만이면 False.
- 조정표가 없거나 금액을 확인할 수 없으면 unknown.

### acc.voluntary_bad_news (bool) — 나쁜 소식을 먼저 자발적으로 공시한 이력이 있는가?
- **True**: 최근 3년 내 회사가 스스로 가이던스를 하향·철회했거나, 정기 실적 발표 외에 부정적 사실(실적 미달
  예고, 대형 고객 이탈, 제품 문제)을 먼저 공시한 증거가 있다. 인수·처분으로 인한 기계적 조정은 제외.
- 그 밖: unknown(나쁜 소식이 없었는지, 숨겼는지 구분할 수 없다). **False는 쓰지 않는다.**

### gov.insider_group_ownership (enum: lt_1pct / 1_to_5pct / 5_to_20pct / gte_20pct)
- 위임장(DEF 14A) 또는 20-F 지분표의 '모든 이사·임원 합계(as a group)' 행의 **경제적 지분 %**.
  클래스별로 나뉘면 전체 보통주 대비 합산 지분을 쓰고, 의결권 %는 쓰지 않는다. 읽을 수 없으면 unknown.

### cap.ma_discipline (enum: disciplined / mixed / undisciplined / no_material_ma)
- **undisciplined**: 최근 5년 인수 관련 영업권·무형자산 손상이 있거나, 대형 거래가 해지돼 해지 수수료를 냈다.
- **disciplined**: 최근 5년 중대한 인수가 있었으나 관련 손상이 없고, 회사가 인수 후 성과(통합 완료·목표 달성)를
  공시했다.
- **mixed**: 둘 다 해당하거나 판단 근거가 엇갈린다.
- **no_material_ma**: 5년 현금 인수가 영업현금흐름의 10% 이하이고 해지·대형 주식 인수도 없다.
- 근거가 부족하면 unknown.

### cmp.share_trend (enum: gaining / stable / losing), cmp.lifecycle_shakeout_or_decline (bool)
- 회사가 **스스로** 점유율 확대/유지/하락, 또는 시장 성장/정체/위축을 수치·서술로 밝힌 문장만 근거.
  회사 매출 성장률만으로는 점유율을 판단하지 않는다(시장 성장률을 모르면 unknown).
- lifecycle: 회사가 자신의 시장이 성장하고 있다고 진술 → False, 위축·통합(shakeout)을 진술 → True.

### acc.guidance_miss_3y / acc.promise_kept_record (bool)
- 매출 외 지표(예: 총거래액, 제품 매출, 순보험료) 가이던스라도 회사가 연간(또는 분기) 범위로 제시하고 실제를
  보고했다면 그 지표로 판정한다. 규칙은 매출 원장과 같다(최초 가이던스 하단 미달 = 미달, 미달 ≥2 → True).
- 회사가 '가이던스를 제공하지 않는다'고 명시하면 두 질문 모두 not_applicable.

### cap.dividend_predictable (bool)
- 회사가 무배당 정책을 진술 → not_applicable. 정기 배당을 5년 이상 감소 없이 지급 → True. 감소·중단·
  특별배당만 → False.

### cap.debt_funded_buyback (bool)
- 회사가 차입금이 없다고 진술(또는 차입 잔액 0)하고 자사주를 매입했다 → False. 매입이 없으면 not_applicable.

### uw.combined_ratio_pct (number, 소수 0.87=87%)
- 최근 회계연도 연차보고서 MD&A의 연결(또는 전사) GAAP 합산비율 그대로. 사업부별 수치만 있으면 unknown.

### cat.cat_exposure (text)
- 최근 회계연도 재해손실 금액(또는 합산비율 기여 포인트)과 재보험 방어(재해 재보험 한도·보유액)를 원문 수치로
  한 문장에 요약. 수치가 하나도 없으면 unknown.

### cap.buyback_effect (enum), dil.net_share_change_3y_pct (number)
- 기계 규칙이 측정을 거부한 종목(IPO·다중 클래스)만 대상. 회사가 공시한 주식수 표를 근거로, 3년 전 대비
  희석주식수가 줄었으면 reduces_share_count, ±1% 이내 offsets_dilution_only, 늘었으면 share_count_rising.
  매입이 없으면 cap.buyback_effect는 not_applicable.
