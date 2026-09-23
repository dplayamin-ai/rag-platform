"""실행 셸(shell 계층; 바이블 §11, §12 `orchestration`).

설계 근거: 바이블 §11(오케스트레이션), §12(모듈 맵).
구성 예정: `context`(`StagePolicy` 적용, `run_stage`)와 `dispatcher`(문서별 직렬화, 테넌트
동시성); 하위 패키지 `local`, `temporal`, `outbox`.
불변식: `pipelines`/`retrieval`/`render`(그리고 이들이 쓰는 `adapters`·`sdk`·`contracts`)는
`temporalio`·`fastapi`·`ledger`를 절대 import하지 않는다(D-17).
검증 계층: 1층(여기서 검증) — `uv run lint-imports`(계약 D-17), `src/rag_platform/orchestration/local`.
"""

from __future__ import annotations
