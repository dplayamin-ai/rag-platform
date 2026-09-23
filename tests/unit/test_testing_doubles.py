"""Unit tests for `rag_platform.testing.doubles` (bible §12 `testing`, conformance kit fakes)."""

from __future__ import annotations

import asyncio
import math

import pytest

from rag_platform.ledger.repo import CommitRecord, DocumentRecord, JobRecord
from rag_platform.testing.doubles.fake_embedder import FakeEmbedder
from rag_platform.testing.doubles.in_memory_index_backend import InMemoryIndexBackend
from rag_platform.testing.doubles.in_memory_kv import InMemoryKV
from rag_platform.testing.doubles.in_memory_ledger import InMemoryLedger


def test_fake_embedder_is_deterministic() -> None:
    embedder = FakeEmbedder(dim=8)
    assert embedder.embed_query("정보공개 청구") == embedder.embed_query("정보공개 청구")


def test_fake_embedder_default_vectors_are_unit_normalized() -> None:
    embedder = FakeEmbedder(dim=32, normalized=True)
    vector = embedder.embed_query("any text")
    norm = math.sqrt(sum(v * v for v in vector))
    assert math.isclose(norm, 1.0, rel_tol=1e-9)


def test_fake_embedder_respects_configured_dimension() -> None:
    embedder = FakeEmbedder(dim=4)
    assert len(embedder.embed_query("x")) == 4
    assert all(len(v) == 4 for v in embedder.embed_documents(["a", "b"]))


def test_fake_embedder_rejects_non_positive_dimension() -> None:
    with pytest.raises(ValueError, match="dim"):
        FakeEmbedder(dim=0)


def test_in_memory_index_backend_search_dense_ranks_by_cosine_similarity() -> None:
    backend = InMemoryIndexBackend()
    embedder = FakeEmbedder(dim=8)
    backend.upsert(
        [
            {"id": "r1", "tenant_id": "t1", "vector": embedder.embed_query("apple banana"), "text": "apple banana"},
            {"id": "r2", "tenant_id": "t1", "vector": embedder.embed_query("completely unrelated"), "text": "other"},
        ]
    )
    results = backend.search_dense("t1", embedder.embed_query("apple banana"), top_k=2)
    assert results[0][0] == "r1"
    assert results[0][1] > results[1][1]


def test_in_memory_index_backend_search_scopes_by_tenant_id() -> None:
    backend = InMemoryIndexBackend()
    embedder = FakeEmbedder(dim=8)
    vector = embedder.embed_query("shared text")
    backend.upsert([{"id": "r1", "tenant_id": "t1", "vector": vector, "text": "shared text"}])
    assert backend.search_dense("t2", vector, top_k=5) == []  # E17: no cross-tenant leakage


def test_in_memory_index_backend_search_lexical_scores_term_overlap() -> None:
    backend = InMemoryIndexBackend()
    backend.upsert(
        [
            {"id": "r1", "tenant_id": "t1", "text": "정보공개 청구 절차 안내"},
            {"id": "r2", "tenant_id": "t1", "text": "예산 편성 지침"},
        ]
    )
    results = backend.search_lexical("t1", "정보공개 청구", top_k=5)
    assert results
    assert results[0][0] == "r1"


async def test_in_memory_kv_ttl_expiry_uses_monotonic_clock() -> None:
    kv = InMemoryKV()
    await kv.set("k", b"v", ttl_s=0)
    await asyncio.sleep(0.01)
    assert await kv.get("k") is None


async def test_in_memory_ledger_round_trips_document_job_and_commit_records() -> None:
    ledger = InMemoryLedger()
    await ledger.upsert_document(DocumentRecord(tenant_id="t1", document_id="d1", collection_id="c1"))
    await ledger.upsert_job(JobRecord(tenant_id="t1", job_id="j1", kind="ingest_document", state="queued"))
    await ledger.upsert_commit(
        CommitRecord(tenant_id="t1", commit_id="cm1", document_id="d1", index_generation=1, status="pending")
    )
    assert (await ledger.get_document("t1", "d1")).collection_id == "c1"
    assert (await ledger.get_job("t1", "j1")).state == "queued"
    assert (await ledger.get_commit("t1", "cm1")).status == "pending"


async def test_in_memory_ledger_is_scoped_per_tenant() -> None:
    ledger = InMemoryLedger()
    await ledger.upsert_document(DocumentRecord(tenant_id="t1", document_id="d1", collection_id="c1"))
    assert await ledger.get_document("t2", "d1") is None  # E17: no cross-tenant leakage
