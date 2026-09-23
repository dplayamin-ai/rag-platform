"""`InMemoryLedger` — `ledger.repo.Ledger` 대역(double). 딕셔너리 기반, 실제 PostgreSQL 없음.

역할: 실 PostgreSQL 없이 `Ledger` 프로토콜(문서/잡/커밋 CRUD) 호출부를 검증하는 대역.
설계 근거: 바이블 §13.1(모든 테이블 `tenant_id` + RLS `FORCE`) — `ledger.repo.Ledger`의
conformance 대역이며 각 레코드를 `(tenant_id, id)` 키로 스코프해 RLS 의미를 근사한다.

구성: `InMemoryLedger` — `upsert_document`/`get_document`, `upsert_job`/`get_job`/`list_jobs`,
`upsert_commit`/`get_commit`.

불변식·주의: 모든 레코드는 `(tenant_id, id)` 복합 키로 저장·조회되어 다른 테넌트 레코드가
섞이지 않는다(바이블 §13.1 RLS와 동일한 격리 의도).
검증 계층: 1층(대역 자체는 여기서 검증) — `tests/unit/test_testing_doubles.py`.
DEFERRED: 실 PostgreSQL 기반 `Ledger`(RLS `FORCE`, `SET LOCAL app.tenant_id`, `ledger/migrations/`
Alembic 마이그레이션) 대상 검증은 `needs_docker`(phase-6 계획 §8 tier 2) —
`docs/12-appendix/09-deferred-verification-ledger.md`에서 추적.
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
