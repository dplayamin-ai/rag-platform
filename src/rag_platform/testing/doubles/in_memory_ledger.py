"""`InMemoryLedger`: `ledger.repo.Ledger` double, dict-backed, no PostgreSQL.

# DEFERRED: verify against a real PostgreSQL-backed `Ledger` (RLS `FORCE`, `SET LOCAL
# app.tenant_id`, Alembic migrations under `ledger/migrations/`) — `needs_docker`
# (phase-6 plan §8 tier 2). Track in `docs/12-appendix/09-deferred-verification-ledger.md`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rag_platform.ledger.repo import CommitRecord, DocumentRecord, JobRecord

__all__ = ["InMemoryLedger"]


class InMemoryLedger:
    """`Ledger` double; every record is scoped by `(tenant_id, id)`, matching bible §13.1 RLS."""

    def __init__(self) -> None:
        """Start with empty document/job/commit tables."""
        self._documents: dict[tuple[str, str], DocumentRecord] = {}
        self._jobs: dict[tuple[str, str], JobRecord] = {}
        self._commits: dict[tuple[str, str], CommitRecord] = {}

    async def upsert_document(self, record: DocumentRecord) -> None:
        """Insert or replace the `(tenant_id, document_id)` row."""
        self._documents[(record.tenant_id, record.document_id)] = record

    async def get_document(self, tenant_id: str, document_id: str) -> DocumentRecord | None:
        """Return the document row, or `None` if absent for this tenant."""
        return self._documents.get((tenant_id, document_id))

    async def upsert_job(self, record: JobRecord) -> None:
        """Insert or replace the `(tenant_id, job_id)` row."""
        self._jobs[(record.tenant_id, record.job_id)] = record

    async def get_job(self, tenant_id: str, job_id: str) -> JobRecord | None:
        """Return the job row, or `None` if absent for this tenant."""
        return self._jobs.get((tenant_id, job_id))

    async def list_jobs(self, tenant_id: str, *, document_id: str | None = None) -> list[JobRecord]:
        """List jobs for `tenant_id`, optionally filtered to one `document_id`."""
        return [
            job
            for (job_tenant_id, _), job in self._jobs.items()
            if job_tenant_id == tenant_id and (document_id is None or job.document_id == document_id)
        ]

    async def upsert_commit(self, record: CommitRecord) -> None:
        """Insert or replace the `(tenant_id, commit_id)` row."""
        self._commits[(record.tenant_id, record.commit_id)] = record

    async def get_commit(self, tenant_id: str, commit_id: str) -> CommitRecord | None:
        """Return the commit row, or `None` if absent for this tenant."""
        return self._commits.get((tenant_id, commit_id))
