# IRS 전용 Skill 구성 (2026-09-05)

사용자 요청: GitHub의 Claude Code Skills(15개 후보명)를 조사해 IRS에
최적화된 코딩 환경을 구축할 것 - 토큰 최소화·코드 품질·디버깅 정확도·
아키텍처 안정성·테스트 강화·안전한 git workflow, 불필요한 skill 설치
금지.

## 조사 결과 요약

15개 후보명은 **단일 저장소가 아니라 여러 서로 다른 3rd-party 저장소에
흩어져 있다**(WebSearch로 실제 SKILL.md 소재를 확인). 주요 출처:
`obra/superpowers`(test-driven-development·systematic-debugging·
subagent-driven-development의 실제 원본), 여러 개별 커뮤니티 저장소
(token-efficiency/token-optimization - `Delphine-L/claude_global`,
`khasky/claude-code-token-optimization` 등 품질이 검증되지 않은 소규모
저장소 다수), `awesome-claude-skills`류 큐레이션 목록(test-gaps·
comprehensive-review 등). **하나로 정리된 "IRS에 맞는 패키지"가 시중에
없으므로, 그대로 설치하지 않고 개념만 추출해 IRS 전용으로 재작성했다.**

## 설치한 것 - `.claude/skills/irs-*` 4개(전부 신규 작성, 재사용은 개념만)

| Skill | 원 아이디어 출처 | IRS 커스터마이징 |
|---|---|---|
| `irs-systematic-debugging` | systematic-debugging (obra/superpowers) | 4단계 프레임에 IRS 실제 사고 계보(fcf0 키 오타 3연속 재발, `ImportError`를 가드발동으로 오집계 등)를 근거로 붙임 |
| `irs-fresh-eyes-verification` | fresh-eyes + comprehensive-review + codex-review(단, 외부모델 호출 부분은 제외) | 3개 스킬의 "발행 전 재검토"라는 공통 핵심만 뽑아 하나로 병합. TYL SBC 3배 오류·RAR 100배·CAGR 기준연도 함정 등 IRS 고유 체크리스트로 구성 |
| `irs-test-gap-analysis` | test-gaps | `engine/`에만 적용되도록 범위를 좁히고, Simplicity First 원칙에 따라 `scripts/analyze_*.py`는 명시적으로 제외 |
| `irs-token-efficient-research` | token-efficiency + token-optimization + subagent-driven-development(위임 판단 부분만) | 2026-09-04 세션에서 실측 검증된 전환(종목당 리서치 에이전트 30만+ 토큰 → 직접 WebSearch)을 근거로 삼음 - 추측이 아니라 이 프로젝트가 이미 겪은 A/B 비교 |

## 제외한 것과 사유

| 후보 | 사유 |
|---|---|
| `code-review` | 이 하니스가 이미 내장 skill로 제공(`code-review`, effort 레벨 low~max 지원) - 설치하면 중복 |
| `security-review` | 내장 skill 중복(`security-review`) |
| `refactor` | 내장 skill 중복(`simplify`가 동일 역할 - reuse/simplification/efficiency 정리) |
| `comprehensive-review` | 내장 `code-review`의 effort=high/max가 이미 이 역할을 커버함(별도 skill 불필요) |
| `design-review` | IRS는 UI 제품이 아니다(연구·계산 엔진). 가끔 만드는 HTML 리포트 아티팩트는 이 하니스의 내장 `artifact-design` skill이 이미 커버 |
| `git-commit` | IRS 시스템 프롬프트·CLAUDE.md가 이미 매우 구체적인 자체 git 컨벤션을 갖고 있다(never amend, ENGINE_VERSION 갱신규칙, ledger `git rm` 후 rename 관행, attribution footer 형식). 범용 3rd-party skill을 얹으면 **상충하는 일반론**이 끼어들 위험이 이득보다 크다 |
| `github-standards` | 시스템 프롬프트에 이미 IRS 전용 PR/CI 감시 프로토콜(subscribe_pr_activity, drive-to-green 루프)이 있다 - 범용 skill과 중복·상충 위험 |
| `codex-review` | 외부 모델(gpt-5-codex 등) 호출을 전제로 한다 - IRS는 `engine/`에 신규 의존성을 추가하지 않는다는 원칙(P0-03, 2026-08-19)을 이미 확정했다. "두 번째 의견"이 필요하면 이 하니스의 Agent 도구 + code-reviewer 서브에이전트 유형으로 이미 충분 |
| `test-driven-development`(블랭킷 정책으로 설치) | IRS의 Simplicity First 원칙이 `scripts/analyze_*.py`(현재 작업 대부분)를 엄격도에서 **명시적으로 제외**하고 있다. "발견한 버그는 반드시 회귀 테스트로 고정"이라는 TDD의 핵심 실천은 이미 CLAUDE.md 전체에 문화로 확립돼 있어 새 skill이 불필요 - `engine/` 변경에 한해서만 이 규율을 적용하도록 `irs-test-gap-analysis`에 흡수 |
| `subagent-driven-development`(블랭킷 정책으로 설치) | IRS의 주 워크플로는 단일 세션의 순차 종목분석이지 다중 에이전트 개발 파이프라인이 아니다. 유용한 부분(언제 위임할지 판단)만 `irs-token-efficient-research`에 흡수 |

## 기존 설치분과의 충돌 확인 - `task-observer`

이 저장소에는 이미 `task-observer`(Tessl "One Skill to Rule Them All",
2026-08-24 이전 설치)가 있다. 이 skill의 description은 **"모든 작업의
시작에 항상 호출할 것"**을 자체적으로 요구하는데, 이는 사용자의 이번
요청 목표(#5 "모든 작업에 모든 Skill을 실행하지 말고 위험도에 따라
필요한 Skill만 호출")·(#1 "토큰 사용 최소화")와 정면으로 어긋난다.

**이번 작업 범위 밖이라 삭제하지 않았다**(사용자가 지정한 15개 후보에
없음). 대신 아래 호출정책에서 이 skill을 상시자동호출 대상에서
명시적으로 제외해 충돌을 무력화한다 - 필요하면 사용자가 명시적으로
"skill 개선점 관찰해줘"라고 요청할 때만 부를 것.

## 위험도 기반 호출 정책 (요청 #5·#6·#7 실행)

| 작업 유형 | 호출할 것 | 모델 |
|---|---|---|
| `engine/` 계산식·판정 규칙·`ENGINE_VERSION` 변경 | `irs-fresh-eyes-verification`(반드시, 커밋 직전) + `irs-test-gap-analysis` | **Opus 유지** |
| ledger 신규 생성(종목 정식분석) | `irs-fresh-eyes-verification`(저장 직전) | Opus 권장(단위·CAGR 함정이 실제 자본에 영향) |
| 종목 다수 1차 스크리닝/서사 확인 | `irs-token-efficient-research`(직접조회 vs 위임 판단) | Sonnet으로 충분 |
| 버그·이상현상·설명 안 되는 결과 | `irs-systematic-debugging` | 이상 정도에 따라 판단 - engine/에 영향 가능성 있으면 Opus |
| 단순 파일 탐색·grep·반복 조회 | 없음(직접 도구 호출, skill 오버헤드 자체가 낭비) | Sonnet |
| `task-observer` | **상시 자동호출 안 함** - 사용자가 명시적으로 요청할 때만 | - |

이 표가 요청 #6("핵심 투자로직·계산로직·아키텍처 변경은 Opus 유지")과
#7("단순 탐색·반복 작업은 token-efficient 방식")을 실제로 강제하는
지점이다. `CLAUDE.md`에는 이 표로의 짧은 포인터만 남기고 전문은 여기
둔다 - CLAUDE.md가 이미 8,000줄을 넘어 전문을 옮기면 그 자체가 토큰
낭비다.

## 설치 후 검증 - 중복 instruction 여부

4개 신규 skill과 하니스 내장 skill(`code-review`/`security-review`/
`simplify`/`artifact-design`) 사이에 description 텍스트 중복이 없는지
확인했다: 4개 신규 skill 전부 "IRS" 고유명사·IRS 파일 경로(`engine/`,
`ledger/`, `scripts/analyze_*.py`)·IRS가 실제로 겪은 사건명(TYL, MU,
BSX, R-001)을 description과 본문에 담고 있어 범용 내장 skill과
트리거 조건이 겹치지 않는다(내장 skill은 프로젝트에 무관한 범용
설명이라 상호 배타적). 4개 신규 skill 상호간에도 트리거 조건이 서로
다른 작업 단계(디버깅/발행전검증/테스트공백/위임판단)를 가리켜 중복
호출될 소지가 없다.
