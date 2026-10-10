# IRS 인수인계 (2026-10-10) — Claude 없이 쓰는 법

## 1. 필요한 설정 (저장소 Settings)
- Actions 활성화. Workflow permissions: **Read and write**.
- Secret `ALPHA_VANTAGE_API_KEY` (선택): 없으면 시가총액이 낡은 근사치가 되고 관심종목 경로는 건너뛴다. 그 외 Secret 없음(`GITHUB_TOKEN`은 자동).
- 예약 실행은 **기본 브랜치(main)** 의 워크플로만 돈다. 60일간 저장소 활동이 없으면 GitHub이 예약을 끈다(커밋이 있으면 유지).

## 2. 자동으로 도는 것 (비용 0, stdlib만)
| 워크플로 | 주기 | 하는 일 | 산출물 |
|---|---|---|---|
| daily-screen | 평일 09:00 KST | Finviz 후보 1차 필터, 반증조건 감시, 관심종목 추적, 브리핑 | 날짜별 GitHub 이슈, `reports/` |
| auto-analysis | 평일 07:30 KST | 큐·watchlist 종목을 규칙 기반 정식분석(비공식) | `ledger_auto/`, 이슈 댓글 |
| broad-screen | 토 10:00 KST | SEC 전체 스크리닝, 연구 큐 갱신, 실전 트랙레코드 | `reports/broad_screen/`, `reports/research_queue.json` |
| tests | push마다 | `pytest tests/` | |

이슈 제목에 날짜와 긴급도(🛑긴급/🔧장애/🔵후보/⚪정상)가 붙는다. **🛑가 뜬 날만 열어 보면 된다.**

## 3. 로컬 실행
```
git clone <저장소> && cd IRS
python -m pytest tests/                       # 기준선 확인
python -m scripts.daily_brief --capital 10000000
python -m scripts.freeze_baseline_2026_08_16  # 기존 판정이 안 바뀌었는지 검증
```

## 4. 사람이 해야 하는 일 (자동화되지 않음)
1. **자동분석에서 S/A가 나온 종목의 공식 분석.** `scripts/analyze_*.py` 하나를 복사해 데이터와 `model_choice_reason`·`subjective_input_basis`를 직접 쓴다. 경쟁강도는 웹에서 경쟁사를 확인해 판단. 규칙은 `CLAUDE.md` v3.19절.
2. **반증조건 확인.** 이슈에 기한 도래가 뜨면 실적을 읽고 `monitor/acknowledgements.json`에 사람이 기록.
3. **보유 조정.** `portfolio/holdings.json`은 코드가 쓰지 않는다. 매수리스트와의 차이는 `daily_brief`가 보여 주기만 한다.
4. **새 종목 지정.** `watchlist.json`의 `tickers`에 추가하면 공식 분석이 없는 종목은 자동분석 대상이 된다(키 필요).

## 5. 절대 섞지 말 것
- `ledger_auto/`(자동·비공식) 결과를 `ledger/`, 매수리스트, thesis에 옮기지 않는다.
- 자동 결과는 후보 압축용이다. 경쟁강도·수요민감도가 중앙값 대체라 거짓 탈락/등급 오차가 구조적으로 있다.
- 백테스트 수치를 "시장을 이긴다"는 근거로 인용하지 않는다(생존편향, 실현 검증 3건뿐).

## 6. 쌓아야 하는 것 (이 시스템의 진짜 병목)
- 새 분석마다 `price_at_analysis`와 PIT 입력(`engine/filing_dates.pit_inputs_for`) 기록.
- `predictions/`의 동결 예측 34건은 FYE 후 `engine/prediction_ledger.resolve_prediction()`으로 해소 기록. 15건이 되면 H-006 검정 가능.

## 7. 다른 AI에게 맡길 때
`CLAUDE.md`(규칙·이력), `docs/qsi_reading_rubric.md`·`docs/qsi_reading_protocol.md`(판독), 기존 `ledger/` 예시를 같이 줄 것.
인용문은 코드가 원문과 글자 단위로 대조하므로 틀린 인용은 걸러진다.
