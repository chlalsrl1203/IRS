# CHANGELOG

## v3.13 (반영일: 2026-07-25, 원 배경: CTAS/AME 등 실전 stalwart 분석)

stalwart 유형이 two_stage 모델에서 구조적으로 음수 RAR을 보이는 패턴을
확인. min_spread 가드가 거의 모든 stalwart 기본 시나리오에서 발동하는
것이 원인. 모델은 그대로 유지하되(model="two_stage" 기본값), 이 편향을
`check_stalwart_two_stage_bias()`로 감지해 메모에 명시적으로 플래그하도록
강제. 근본 원인을 숨기지 않고 문서화하는 방향으로 대응(v3.16 이후 정신과
동일 원칙 선반영).
