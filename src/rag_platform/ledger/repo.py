"""`Ledger` 프로토콜 — `documents`/`jobs`/`index_commits` 세 테이블에 대한 최소 읽기/쓰기 계약.

역할: PostgreSQL 원장(ledger) 접근을 위한 `Protocol` 정의. 실제 구현 이전에도 conformance kit과
단위 테스트가 `testing.doubles.InMemoryLedger`를 통해 이 인터페이스를 검증할 수 있게 한다.
설계 근거: 바이블 §13.1(PostgreSQL 핵심 테이블 — 모든 테이블 `tenant_id` 스코프 + row level
security `FORCE`).

구성:
- `DocumentRecord` — `documents` 행 부분집합(식별자 + 현재 버전/세대)
- `JobRecord` — `jobs` 행 부분집합(식별자, kind/state/stage, 재시도 횟수)
- `CommitRecord` — `index_commits` 행 부분집합(식별자, 세대, 상태)
- `Ledger` — 위 레코드에 대한 CRUD 프로토콜(항상 `tenant_id` 스코프); `list_commits`는 문서별
  `index_commits` 이력 전체(성공·롤백·실패 포함)를 반환해 호출자가 `max(index_generation) + 1`을
  계산하게 한다(F3 배치 검증 open_issue — `adapters.index.saga.IndexSaga`가 이 메서드 부재로
  `documents.current_generation + 1`을 근사했던 것을 이 메서드 추가로 해소, 계약 문서
  `contracts/index_commit.py`의 "documents 행 FOR UPDATE 잠금 아래 그 문서의
  max(index_commits.index_generation) + 1로 할당(current_generation + 1 아님; 롤백·폐기된 세대
  번호 재사용 없음)" 정의를 그대로 구현)

불변식·주의: 실 PostgreSQL 구현(`ledger/models.py`, `ledger/migrations/`)은 이 작업 범위 밖이며
프로토콜과 인메모리 대역만 제공한다.
검증 계층: 1층(여기서 검증) — `tests/unit/test_ledger_repo.py`.
DEFERRED: 실 PostgreSQL 기반 `Ledger`(asyncpg/SQLAlchemy, `SET LOCAL app.tenant_id`, RLS `FORCE`,
Alembic 마이그레이션)는 `needs_docker`(phase-6 계획 §8 tier 2).
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

    async def list_commits(self, tenant_id: str, document_id: str) -> list[CommitRecord]:
        """Return every `index_commits` row for this document (any status), for generation allocation."""
        ...
