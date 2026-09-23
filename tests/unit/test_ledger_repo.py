"""Unit tests for `rag_platform.ledger.repo` (bible §13.1 document/job/commit records)."""

from __future__ import annotations

from rag_platform.ledger.repo import CommitRecord, DocumentRecord, JobRecord, Ledger
from rag_platform.testing.doubles.in_memory_ledger import InMemoryLedger


def test_document_record_defaults() -> None:
    record = DocumentRecord(tenant_id="t1", document_id="d1", collection_id="c1")
    assert record.current_generation == 0
    assert record.current_doc_version is None


def test_job_record_defaults() -> None:
    record = JobRecord(tenant_id="t1", job_id="j1", kind="ingest_document", state="queued")
    assert record.attempts == 0
    assert record.document_id is None


def test_commit_record_fields() -> None:
    record = CommitRecord(tenant_id="t1", commit_id="cm1", document_id="d1", index_generation=1, status="pending")
    assert record.index_generation == 1


def test_in_memory_ledger_satisfies_ledger_protocol() -> None:
    assert isinstance(InMemoryLedger(), Ledger)


def test_ledger_protocol_rejects_incomplete_implementation() -> None:
    class _Incomplete:
        async def upsert_document(self, record: DocumentRecord) -> None:
            return

    assert not isinstance(_Incomplete(), Ledger)


async def test_in_memory_ledger_list_jobs_filters_by_document_id() -> None:
    ledger = InMemoryLedger()
    await ledger.upsert_job(
        JobRecord(tenant_id="t1", job_id="j1", kind="ingest_document", state="running", document_id="d1")
    )
    await ledger.upsert_job(
        JobRecord(tenant_id="t1", job_id="j2", kind="ingest_document", state="running", document_id="d2")
    )
    jobs = await ledger.list_jobs("t1", document_id="d1")
    assert [job.job_id for job in jobs] == ["j1"]
