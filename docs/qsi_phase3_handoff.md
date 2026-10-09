# QSI 3단계 인계 메모 (2026-10-09)

상태: 증거 묶음 19종목·루브릭·프로토콜·병합 스크립트(`scripts/qsi_apply_reading.py`) 완료. 독립 판독(A/B)은 세션 한도로 중단돼 일부만 있음.
다음 세션에서 할 일:
1. `reports/qsi_reading/passA|passB/`에서 **빠진 종목만** 판독 에이전트로 채운다(양쪽이 서로 폴더를 열지 않게). 종목당 파일이 있으면 건너뜀.
2. 에이전트 한도에 걸리면 종목 1~2개씩 작게 나눠 순차 실행.
3. `python -m scripts.qsi_apply_reading --dry-run` → 일치율 확인 → 실제 실행(A·B 둘 다 있는 종목만 처리됨).
4. `python -m scripts.qualitative_intake coverage`, 전체 테스트, ENGINE_VERSION v3.98, CLAUDE.md v3.98 절, 커밋·푸시.
주의: 한쪽만 있는 종목은 병합하지 않는다. 판정·ledger·매수리스트는 건드리지 않는다.
