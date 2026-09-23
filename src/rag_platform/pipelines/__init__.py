"""파이프라인 정의 `ingest`, `reindex`, `query`(L2 계층; 바이블 §12 `pipelines`).

설계 근거: 바이블 §12(모듈 맵), ADR-0003(실행기 독립성), ADR-0017(D-17 계층 규칙).
구성: 각 파이프라인 정의는 `PipelineContext`에만 의존해 `LocalRunner`와 Temporal shell이
같은 코드를 실행하게 한다(ADR-0003).
불변식: `temporalio`·`fastapi`·`starlette`·`rag_platform.ledger`·`rag_platform.orchestration`
임포트는 금지한다(import-linter, D-17).
검증 계층: 1층(여기서 검증) — `uv run lint-imports`(계약 D-17), 각 파이프라인 구현 시 단위 테스트.
"""

from __future__ import annotations
