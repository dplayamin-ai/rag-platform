"""`IndexCommit` 세대 사가 — 단일 백엔드(`index_backend.qdrant`) 경로로 커밋을 원장에 기록·보상한다.

역할: 세대(`index_generation`) 할당 → `stage.build_index_records`로 조립 → Qdrant 로컬 upsert →
`is_current` 플립 → 원장(`Ledger` 포트 모양) `pending → … → committed` 전이, 실패 시 두 갈래 보상
(플립 전 신규 세대 삭제 / 플립 후 이전 세대 복원 후 신규 세대 삭제)까지 담당한다.
설계 근거: 바이블 §11.4(9단 `CommitStatus`, 두 갈래 보상, 발급·직렬화 규칙), ADR-0026 결정 절,
04-pipelines/13 §6(렉시컬 백엔드가 없으면 `vector_written → lexical_written → flipping_lexical`을
즉시 통과)·§7(가시성 시점). 계약 타입: `IndexCommit`(`contracts/index_commit.py`).
구성: `_DocumentState`/`_CommitState` — `ledger.repo.Ledger`와 같은 필드 모양의 로컬 미러(import 회피,
아래 불변식); `IndexSaga` — `commit(...)`(정상 경로)와 `_rollback(...)`(보상)를 갖는 사가 본체.
불변식: `rag_platform.adapters`는 `rag_platform.ledger`를 import하지 않는다(import-linter
`pipelines-orchestrator-neutral` 계약) — `ledger` 인자는 `get_document`/`upsert_document`/
`upsert_commit`/`get_commit`(모두 `async`)만 구조적으로 요구하고, 넘기는 레코드는 이 파일이 정의한
`_DocumentState`/`_CommitState`(속성 이름만 `ledger.repo`와 동일)다. `commit_id`가 이미 `committed`면
프로세스 내 캐시로 no-op(실 재현은 원장 재적재 경로, WP 문서 DEFERRED).
검증 계층: 1층(여기서 검증) — `tests/adapters/index/test_index_commit.py`(`QdrantIndexBackend.local()`
+ `testing.doubles.InMemoryLedger`).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from ulid import ULID

from rag_platform.adapters.index.qdrant.backend import CollectionLayout, alias_name, physical_collection_name
from rag_platform.adapters.index.qdrant.filters import scope_filter
from rag_platform.adapters.index.stage import build_index_records, commit_hash_of, rfc3339_ms
from rag_platform.contracts.index_commit import IndexCommit
from rag_platform.sdk.stage import StageError

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from datetime import datetime

    from qdrant_client import models

    from rag_platform.adapters.index.stage import IndexLineage
    from rag_platform.contracts import common_types as ct
    from rag_platform.contracts.embedded_chunk_set import EmbeddedChunkSet
    from rag_platform.contracts.index_record import IndexRecord

__all__ = ["IndexBackendPort", "IndexSaga"]

PLUGIN_ID = "index_backend.pipeline"
BACKEND_PLUGIN_ID = "index_backend.qdrant"


@runtime_checkable
class IndexBackendPort(Protocol):
    """`IndexSaga.backend`가 요구하는 최소 표면.

    `adapters.index.qdrant.backend.QdrantIndexBackend`가 구조적으로 만족한다(상속 없이).
    `sdk.ports.IndexBackend`(검색용 최소 표면)보다 넓은, 사가 전용 쓰기 표면(`ensure_collection`/
    `set_current`/`delete` 포함)이라 여기 따로 둔다.
    """

    backend_version: str | None

    def ensure_collection(self, name: str, layout: CollectionLayout) -> bool:
        """컬렉션이 없으면 생성하고, 있으면 대조한다(`QdrantIndexBackend.ensure_collection`)."""
        ...

    def upsert(
        self,
        collection: str,
        records: Sequence[IndexRecord],
        *,
        commit_id: str | None = None,
        index_generation: int | None = None,
    ) -> int:
        """`records`를 검증 후 적재하고 적재된 포인트 수를 반환한다."""
        ...

    def set_current(
        self, collection: str, *, tenant_id: str, collection_id: str, document_id: str, index_generation: int
    ) -> None:
        """`index_generation`의 `is_current`를 `true`로, 다른 세대는 `false`로 플립한다."""
        ...

    def delete(self, collection: str, query_filter: models.Filter) -> None:
        """`query_filter`(테넌트 스코프)에 맞는 포인트를 삭제한다."""
        ...

    def count(self, collection: str, query_filter: models.Filter) -> int:
        """`query_filter`에 맞는 포인트 수를 반환한다."""
        ...


@dataclass(frozen=True)
class _DocumentState:
    """`ledger.repo.DocumentRecord`와 같은 필드 모양의 로컬 미러(그 모듈을 import하지 않는다)."""

    tenant_id: str
    document_id: str
    collection_id: str
    external_id: str | None = None
    current_doc_version: str | None = None
    current_generation: int = 0
    current_commit_id: str | None = None


@dataclass(frozen=True)
class _CommitState:
    """`ledger.repo.CommitRecord`와 같은 필드 모양의 로컬 미러(그 모듈을 import하지 않는다)."""

    tenant_id: str
    commit_id: str
    document_id: str
    index_generation: int
    status: str


@dataclass(frozen=True)
class _CommonArgs:
    """`commit`/`_rollback` 사이에서 공유하는 스코프 값(가독성을 위한 좁은 자리표)."""

    tenant_id: str
    collection_id: str
    document_id: str
    physical: str
    resolved_commit_id: str
    index_generation: int
    previous_generation: int
    previous_commit_id: str | None


@dataclass
class IndexSaga:
    """단일 백엔드(Qdrant) `IndexCommit` 세대 사가. `backend`/`ledger`는 생성자 주입(§sdk/ports 관례)."""

    backend: IndexBackendPort
    ledger: Any
    plugin_version: str = "0.1.0"
    _committed: dict[tuple[str, str], IndexCommit] = field(default_factory=dict, repr=False)

    async def commit(
        self,
        embedded: EmbeddedChunkSet,
        lineage: IndexLineage,
        *,
        dense_vectors: Mapping[str, Sequence[float]],
        embedded_ref: ct.ArtifactRef,
        job_id: str,
        profile_id: str,
        profile_hash: str,
        now: datetime,
        commit_id: str | None = None,
    ) -> IndexCommit:
        """새 세대를 조립·적재·플립하고 원장에 `committed`(또는 보상 후 `rolled_back`)를 기록한다."""
        tenant_id = str(embedded.tenant_id.root)
        collection_id = str(embedded.collection_id.root)
        document_id = str(embedded.document_id.root)

        resolved_commit_id = commit_id or str(ULID())
        cache_key = (tenant_id, resolved_commit_id)
        if cache_key in self._committed:
            return self._committed[cache_key]

        doc_state: _DocumentState | None = await self.ledger.get_document(tenant_id, document_id)
        previous_commit_id = doc_state.current_commit_id if doc_state else None
        previous_generation = doc_state.current_generation if doc_state else 0
        # contracts/index_commit.py: "documents 행 FOR UPDATE 잠금 아래 그 문서의
        # max(index_commits.index_generation) + 1로 할당(current_generation + 1 아님; 롤백·폐기된
        # 세대 번호 재사용 없음)" — `list_commits`(모든 상태 포함)의 max로 할당해 롤백된 세대 번호를
        # 재사용하지 않는다(F3 배치 검증 open_issue 해소).
        existing_commits: Sequence[_CommitState] = await self.ledger.list_commits(tenant_id, document_id)
        max_allocated_generation = max((c.index_generation for c in existing_commits), default=0)
        index_generation = max(previous_generation, max_allocated_generation) + 1

        records = build_index_records(
            embedded,
            lineage,
            dense_vectors,
            commit_id=resolved_commit_id,
            index_generation=index_generation,
            now=now,
        )
        commit_hash = commit_hash_of(records, embedded, profile_hash=profile_hash)
        physical = physical_collection_name(str(embedded.embedding_profile_hash.root))
        dense_dim = len(records[0].vectors.dense) if records and records[0].vectors.dense else 1
        self.backend.ensure_collection(physical, CollectionLayout(dense_dim=dense_dim))

        common = _CommonArgs(
            tenant_id=tenant_id,
            collection_id=collection_id,
            document_id=document_id,
            physical=physical,
            resolved_commit_id=resolved_commit_id,
            index_generation=index_generation,
            previous_generation=previous_generation,
            previous_commit_id=previous_commit_id,
        )

        try:
            self.backend.upsert(physical, records, commit_id=resolved_commit_id, index_generation=index_generation)
        except StageError as exc:
            return await self._rollback(
                common,
                embedded=embedded,
                lineage=lineage,
                commit_hash=commit_hash,
                profile_id=profile_id,
                profile_hash=profile_hash,
                job_id=job_id,
                embedded_ref=embedded_ref,
                records=records,
                started_at=now,
                completed_at=now,
                failed_at_status="pending",
                cause=exc,
            )

        try:
            self.backend.set_current(
                physical,
                tenant_id=tenant_id,
                collection_id=collection_id,
                document_id=document_id,
                index_generation=index_generation,
            )
        except StageError as exc:
            return await self._rollback(
                common,
                embedded=embedded,
                lineage=lineage,
                commit_hash=commit_hash,
                profile_id=profile_id,
                profile_hash=profile_hash,
                job_id=job_id,
                embedded_ref=embedded_ref,
                records=records,
                started_at=now,
                completed_at=now,
                failed_at_status="flipping_vector",
                cause=exc,
            )

        await self.ledger.upsert_document(
            _DocumentState(
                tenant_id=tenant_id,
                document_id=document_id,
                collection_id=collection_id,
                current_doc_version=str(embedded.doc_version.root),
                current_generation=index_generation,
                current_commit_id=resolved_commit_id,
            )
        )
        await self.ledger.upsert_commit(
            _CommitState(
                tenant_id=tenant_id,
                commit_id=resolved_commit_id,
                document_id=document_id,
                index_generation=index_generation,
                status="committed",
            )
        )

        result = IndexCommit.model_validate(
            self._commit_payload(
                embedded=embedded,
                lineage=lineage,
                status="committed",
                commit_id=resolved_commit_id,
                index_generation=index_generation,
                previous_commit_id=previous_commit_id,
                commit_hash=commit_hash,
                records=records,
                profile_id=profile_id,
                profile_hash=profile_hash,
                job_id=job_id,
                embedded_ref=embedded_ref,
                started_at=now,
                committed_at=now,
                backend_status="ok",
                upserted=len(records),
                deleted=0,
            )
        )
        self._committed[cache_key] = result
        return result

    async def _rollback(
        self,
        common: _CommonArgs,
        *,
        embedded: EmbeddedChunkSet,
        lineage: IndexLineage,
        commit_hash: str,
        profile_id: str,
        profile_hash: str,
        job_id: str,
        embedded_ref: ct.ArtifactRef,
        records: list[Any],
        started_at: datetime,
        completed_at: datetime,
        failed_at_status: str,
        cause: StageError,
    ) -> IndexCommit:
        """플립 전은 신규 세대만 삭제, 플립 후는 이전 세대 복원 후 신규 세대 삭제(바이블 §11.4 (3))."""
        restored_generation: int | None = None
        if failed_at_status in ("flipping_lexical", "flipping_vector") and common.previous_commit_id is not None:
            try:
                self.backend.set_current(
                    common.physical,
                    tenant_id=common.tenant_id,
                    collection_id=common.collection_id,
                    document_id=common.document_id,
                    index_generation=common.previous_generation,
                )
                restored_generation = common.previous_generation
            except StageError as restore_exc:
                await self.ledger.upsert_commit(
                    _CommitState(
                        tenant_id=common.tenant_id,
                        commit_id=common.resolved_commit_id,
                        document_id=common.document_id,
                        index_generation=common.index_generation,
                        status="failed",
                    )
                )
                return IndexCommit.model_validate(
                    self._commit_payload(
                        embedded=embedded,
                        lineage=lineage,
                        status="failed",
                        commit_id=common.resolved_commit_id,
                        index_generation=common.index_generation,
                        previous_commit_id=common.previous_commit_id,
                        commit_hash=commit_hash,
                        records=records,
                        profile_id=profile_id,
                        profile_hash=profile_hash,
                        job_id=job_id,
                        embedded_ref=embedded_ref,
                        started_at=started_at,
                        committed_at=None,
                        backend_status="failed",
                        upserted=len(records),
                        deleted=0,
                        error=restore_exc,
                        compensation_reason=restore_exc.code,
                        compensation_failed_at=failed_at_status,
                        restored_generation=None,
                        completed_at=completed_at,
                    )
                )

        self.backend.delete(
            common.physical,
            scope_filter(
                common.tenant_id,
                collection_id=common.collection_id,
                document_id=common.document_id,
                index_generation=common.index_generation,
            ),
        )
        await self.ledger.upsert_commit(
            _CommitState(
                tenant_id=common.tenant_id,
                commit_id=common.resolved_commit_id,
                document_id=common.document_id,
                index_generation=common.index_generation,
                status="rolled_back",
            )
        )
        return IndexCommit.model_validate(
            self._commit_payload(
                embedded=embedded,
                lineage=lineage,
                status="rolled_back",
                commit_id=common.resolved_commit_id,
                index_generation=common.index_generation,
                previous_commit_id=common.previous_commit_id,
                commit_hash=commit_hash,
                records=records,
                profile_id=profile_id,
                profile_hash=profile_hash,
                job_id=job_id,
                embedded_ref=embedded_ref,
                started_at=started_at,
                committed_at=None,
                backend_status="compensated",
                upserted=len(records),
                deleted=len(records),
                error=cause,
                compensation_reason=cause.code,
                compensation_failed_at=failed_at_status,
                restored_generation=restored_generation,
                completed_at=completed_at,
            )
        )

    def _commit_payload(
        self,
        *,
        embedded: EmbeddedChunkSet,
        lineage: IndexLineage,
        status: str,
        commit_id: str,
        index_generation: int,
        previous_commit_id: str | None,
        commit_hash: str,
        records: list[Any],
        profile_id: str,
        profile_hash: str,
        job_id: str,
        embedded_ref: ct.ArtifactRef,
        started_at: datetime,
        committed_at: datetime | None,
        backend_status: str,
        upserted: int,
        deleted: int,
        error: StageError | None = None,
        compensation_reason: str | None = None,
        compensation_failed_at: str | None = None,
        restored_generation: int | None = None,
        completed_at: datetime | None = None,
    ) -> dict[str, Any]:
        """`IndexCommit.model_validate`에 넘길 평면 dict를 조립한다(바이블 §5.4 표)."""
        artifact_refs = {
            "source": embedded.lineage_refs.source.model_dump(mode="json"),
            "parsed": embedded.lineage_refs.parsed.model_dump(mode="json"),
            "normalized": embedded.lineage_refs.normalized.model_dump(mode="json"),
            "chunk_set": embedded.lineage_refs.chunk_set.model_dump(mode="json"),
            "enriched": embedded.lineage_refs.enriched.model_dump(mode="json"),
            "embedded": embedded_ref.model_dump(mode="json"),
        }
        bytes_dense = sum(len(r.vectors.dense or []) * 4 for r in records)
        bytes_sparse = sum(
            len(sv.indices) * 8
            for r in records
            for sv in (r.vectors.sparse_learned, r.vectors.sparse_bm25)
            if sv is not None
        )
        leaf_count = sum(1 for r in records if int(r.level) == 0)
        parent_count = sum(1 for chunk in lineage.chunk_set.chunks if int(chunk.level) == 1)
        wall_seconds = (committed_at - started_at).total_seconds() if committed_at else 0.0
        payload: dict[str, Any] = {
            "schema_version": "1.0.0",
            "schema_type": "IndexCommit",
            "tenant_id": str(embedded.tenant_id.root),
            "collection_id": str(embedded.collection_id.root),
            "producer": {
                "plugin_id": PLUGIN_ID,
                "plugin_version": self.plugin_version,
                "config_hash": "0" * 64,
                "image_digest": None,
            },
            "quality": embedded.quality.value,
            "warnings": [],
            "created_at": rfc3339_ms(started_at),
            "lineage_refs": artifact_refs,
            "commit_id": commit_id,
            "document_id": str(embedded.document_id.root),
            "doc_version": str(embedded.doc_version.root),
            "job_id": job_id or str(ULID()),
            "kind": "upsert",
            "previous_commit_id": previous_commit_id,
            "supersedes_commit_ids": [previous_commit_id] if previous_commit_id else [],
            "status": status,
            "index_generation": index_generation,
            "profile_id": profile_id,
            "profile_hash": profile_hash,
            "parser_fingerprint_hash": "0" * 64,
            "normalizer_fingerprint": "0" * 64,
            "chunker_config_hash": str(lineage.chunk_set.chunker_config_hash.root),
            "enricher_fingerprint": str(lineage.enriched.enricher_fingerprint.root),
            "embedder_fingerprint": str(embedded.embedder_fingerprint.root),
            "embedding_space_ids": embedded.embedding_space_ids.model_dump(mode="json"),
            "embedding_profile_hash": str(embedded.embedding_profile_hash.root),
            "analyzer_id": str(lineage.chunk_set.analyzer_id.root),
            "dictionary_hash": str(lineage.chunk_set.dictionary_hash.root),
            "record_count": len(records),
            "commit_hash": commit_hash,
            "backend_results": [
                {
                    "backend_id": BACKEND_PLUGIN_ID,
                    "backend_version": self.backend.backend_version or "local",
                    "physical_name": physical_collection_name(str(embedded.embedding_profile_hash.root)),
                    "alias": alias_name(str(embedded.collection_id.root)),
                    "upserted": upserted,
                    "deleted": deleted,
                    "duration_ms": 0,
                    "status": backend_status,
                }
            ],
            "artifact_refs": artifact_refs,
            "stats": {
                "bytes_dense": bytes_dense,
                "bytes_sparse": bytes_sparse,
                "bytes_lexical": 0,
                "bytes_late_interaction": 0,
                "leaf_count": leaf_count,
                "parent_count": parent_count,
                "llm_tokens": lineage.enriched.budget_used.llm_tokens_in + lineage.enriched.budget_used.llm_tokens_out,
                "wall_seconds": wall_seconds,
            },
            "events_emitted": [],
            "started_at": rfc3339_ms(started_at),
        }
        if committed_at is not None:
            payload["committed_at"] = rfc3339_ms(committed_at)
        if completed_at is not None:
            payload["updated_at"] = rfc3339_ms(completed_at)
        if error is not None:
            payload["error"] = {
                "code": error.code,
                "type": error.type,
                "retryable": False,
                "stage": error.stage,
                "plugin_id": error.plugin_id,
                "detail": error.detail,
            }
        if compensation_reason is not None:
            payload["compensation"] = {
                "reason": compensation_reason,
                "failed_at_status": compensation_failed_at,
                "deleted_counts": {BACKEND_PLUGIN_ID: deleted},
                "restored_generation": restored_generation,
                "completed_at": rfc3339_ms(completed_at or started_at),
            }
        return payload
