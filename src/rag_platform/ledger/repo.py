"""Minimal `Ledger` protocol: document, job and commit records (bible §13.1).

Canon: design bible §13.1 (PostgreSQL core tables — `documents`, `jobs`, `index_commits`, every
table `tenant_id`-scoped with row level security `FORCE`). This is the read/write surface the
conformance kit and unit tests exercise through `testing.doubles.InMemoryLedger`; the real
PostgreSQL-backed implementation (`ledger/models.py`, `ledger/migrations/`) is a separate work
package.

# DEFERRED: a real PostgreSQL-backed `Ledger` (asyncpg/SQLAlchemy, `SET LOCAL app.tenant_id`, RLS
# `FORCE` policies, Alembic migrations under `ledger/migrations/`), verified against a live
# PostgreSQL instance, is `needs_docker` (phase-6 plan §8 tier 2) and is not part of this work
# package. Only the protocol and an in-memory double are provided here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

__all__ = ["CommitRecord", "DocumentRecord", "JobRecord", "Ledger"]


@dataclass(frozen=True)
class DocumentRecord:
    """Bible §13.1 `documents` row (subset: identity + current version/generation)."""

    tenant_id: str
    document_id: str
    collection_id: str
    external_id: str | None = None
    current_doc_version: str | None = None
    current_generation: int = 0
    current_commit_id: str | None = None


@dataclass(frozen=True)
class JobRecord:
    """Bible §13.1 `jobs` row (subset: identity, kind/state/stage, attempts, document scope)."""

    tenant_id: str
    job_id: str
    kind: str
    state: str
    document_id: str | None = None
    stage: str | None = None
    attempts: int = 0
    waiting_for: str | None = None


@dataclass(frozen=True)
class CommitRecord:
    """Bible §13.1 `index_commits` row (subset: identity, generation, status)."""

    tenant_id: str
    commit_id: str
    document_id: str
    index_generation: int
    status: str


@runtime_checkable
class Ledger(Protocol):
    """Document/job/commit record access, always `tenant_id`-scoped (bible §13.1 RLS `FORCE`)."""

    async def upsert_document(self, record: DocumentRecord) -> None:
        """Insert or replace a `documents` row."""
        ...

    async def get_document(self, tenant_id: str, document_id: str) -> DocumentRecord | None:
        """Return a document row, or `None` if absent for this tenant."""
        ...

    async def upsert_job(self, record: JobRecord) -> None:
        """Insert or replace a `jobs` row."""
        ...

    async def get_job(self, tenant_id: str, job_id: str) -> JobRecord | None:
        """Return a job row, or `None` if absent for this tenant."""
        ...

    async def list_jobs(self, tenant_id: str, *, document_id: str | None = None) -> list[JobRecord]:
        """List jobs for `tenant_id`, optionally filtered to one `document_id`."""
        ...

    async def upsert_commit(self, record: CommitRecord) -> None:
        """Insert or replace an `index_commits` row."""
        ...

    async def get_commit(self, tenant_id: str, commit_id: str) -> CommitRecord | None:
        """Return a commit row, or `None` if absent for this tenant."""
        ...
