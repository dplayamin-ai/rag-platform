"""Pipeline definitions ``ingest``, ``reindex`` and ``query`` (layer L2; bible §12 ``pipelines``).

Definitions depend only on ``PipelineContext`` so that ``LocalRunner`` and the Temporal shell run
the same code (ADR-0003). Importing ``temporalio``, ``fastapi``, ``starlette``,
``rag_platform.ledger`` or ``rag_platform.orchestration`` is forbidden (import-linter, D-17).
"""

from __future__ import annotations
