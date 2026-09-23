"""파이프라인 정의 `ingest`, `reindex`, `query`(L2 계층; 바이블 §12 `pipelines`).

정의는 `PipelineContext`에만 의존해 `LocalRunner`와 Temporal shell이 같은 코드를 실행한다
(ADR-0003). `temporalio`·`fastapi`·`starlette`·`rag_platform.ledger`·`rag_platform.orchestration`
임포트는 금지(import-linter, D-17).
"""

from __future__ import annotations
