# QSI 판독 작업 지시 (판독자용)

당신은 QSI 3단계 판독자다. 다른 판독자가 같은 증거를 독립적으로 읽는다 — **다른 판독자의 결과 파일
(`reports/qsi_reading/passA/`, `passB/`)을 절대 열지 말 것.** 서로 독립이어야 일치도가 의미를 갖는다.

1. 먼저 `docs/qsi_reading_rubric.md`(결정 규칙)를 읽는다.
2. 질문 정의(허용값·타입)는 `engine/qualitative_input.py`의 `QUESTION_BANK`에 있다.
3. 배정된 종목마다 `reports/qsi_reading/packs/<T>.json`을 읽는다. `targets`의 각 질문에 답한다.
   증거 묶음의 `excerpts[].text` **안의 문장만** 근거로 쓴다. 웹 검색·기억·다른 파일 사용 금지.
4. 결과를 `reports/qsi_reading/pass<X>/<T>.json`에 아래 형식으로 쓴다(X는 배정된 판독자 기호).

```json
{"ticker": "ADBE", "reader": "A", "based_on_record": "<pack의 based_on_record 그대로>",
 "answers": [
   {"qid": "gov.chair_separated", "status": "answered", "answer": false,
    "excerpt_id": "ADBE-12", "quote": "<excerpt text에서 그대로 복사한 40~400자 연속 구간>",
    "reason": "한국어 한 줄 근거"},
   {"qid": "acc.voluntary_bad_news", "status": "unknown", "answer": null, "excerpt_id": null, "quote": null,
    "reason": "가이던스 하향 증거 없음 — 루브릭상 False를 쓰지 않는다"}
 ]}
```

규칙:
- `targets`의 모든 질문에 정확히 한 번 답한다(answered / unknown / not_applicable).
- `answer` 타입: bool은 true/false, enum은 허용값 문자열, number는 숫자(비율은 소수 0.87), text는 한국어 한두 문장.
- `quote`는 해당 `excerpt_id`의 `text`에서 **글자 하나 바꾸지 않고** 잘라낸 연속 구간이어야 한다
  (공백 포함 그대로). 코드가 대조하며 다르면 답이 버려진다.
- not_applicable은 루브릭이 허용한 경우(무배당 진술, 가이던스 미제공 명시, 매입 없음)에만 쓰고, 그때도
  근거 quote를 단다.
- 확신이 없으면 unknown. 틀린 답보다 판단 보류가 낫다.
- 작업이 끝나면 종목별로 answered/unknown/not_applicable 개수만 한 줄씩 보고한다.
