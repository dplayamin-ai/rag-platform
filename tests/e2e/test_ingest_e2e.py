"""수집 파이프라인 e2e — `pipelines.ingest.run()`을 `LocalRunner`로 hwpx·txt·md·html에 대해 끝까지 돌린다.

역할: F1(fetch·parse·normalize)·F2(chunk·enrich 결정적 보강)가 만든 실제 스테이지 어댑터와 F3(embed
fake·index qdrant local)의 최소 골격을 하나의 `PipelineContext` 구현으로 엮어 바이블 §4.2 체인
(fetch→detect·parse→normalize→chunk→enrich→embed→index→publish) 전체를 `lite` 프로파일 값으로
실행하고, `IndexCommit` 커밋·Qdrant 로컬 레코드 존재·재실행 `stage_key` 캐시 히트·멱등을 검증한다.
설계 근거: 바이블 §4.2(수집 파이프라인 표)·§11.1(`LocalRunner`)·§4.1(`stage_key` 캐시); ADR-0037
(캐시 스코프, `fetch`/`index` 캐시 예외); `docs/13-implementation/wp/WP-303-ingest-pipeline-e2e.md`.
구성: `_E2EPipeline` — `PipelineContext.run(stage, inp_ref, out_type, policy)`을 스테이지 1개짜리
`LocalRunner.run([...])` 호출로 옮기는 이 파일 전용 셸(아직 없는 `orchestration/context.py`의
자리표시자); `_build_*_payload` — enrich/embed/index 산출물을 실제 상류 계약 값으로 조립하는 순수
함수; `test_ingest_pipeline_*` — hwpx 3종 + txt/md/html에 대한 파라미터화 e2e 케이스.
불변식·주의: 모델 가중치 다운로드 없음(`embedder.inprocess_fake`); Docker·GPU·네트워크 없음(Qdrant
`:memory:` 로컬 모드, `WhitespaceTokenizer` BM25). `parse` 스테이지 자체는 `fetch`의 캐시 예외
(`fetch_report.duration_ms` 등 타이밍 필드) 때문에 재실행마다 캐시 히트가 보장되지 않는다(문서화된
설계 갭, DEFERRED 참조) — 캐시 히트 단언은 그 영향을 받지 않는 `normalize`·`chunk`·`enrich`·`embed`만
확인한다.
검증 계층: 1층(여기서 검증, 로컬 실행기 + Qdrant 로컬 모드). `needs_docker`/`needs_model`/`needs_gpu`/
`needs_network` 해당 없음.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from ulid import ULID

from rag_platform.adapters.chunk.structure_aware import StructureAwareChunkerConfig, StructureAwareChunkerStage
from rag_platform.adapters.embed.inprocess_fake import InprocessFakeEmbedder
from rag_platform.adapters.enrich.derived_meta import DerivedMetaEnricher
from rag_platform.adapters.enrich.deterministic_prefix import DeterministicPrefixEnricher
from rag_platform.adapters.enrich.korean_keywords import KoreanKeywordsEnricher
from rag_platform.adapters.fetch.fsspec_httpx import FetchConfig, FsspecHttpxFetcher
from rag_platform.adapters.index.qdrant.backend import CollectionLayout, QdrantIndexBackend, physical_collection_name
from rag_platform.adapters.index.qdrant.bm25_sparse import WhitespaceTokenizer, document_vector
from rag_platform.adapters.index.qdrant.filters import scope_filter
from rag_platform.adapters.normalize.stage import NormalizerChainConfig, NormalizerChainStage
from rag_platform.adapters.parse.html_trafilatura_docling import HtmlParserConfig, HtmlTrafilaturaDoclingParser
from rag_platform.adapters.parse.hwpx_python_hwpx import HwpxParserConfig, HwpxPythonHwpxParser
from rag_platform.adapters.parse.router import ParseRouterStage
from rag_platform.adapters.parse.text_charset_markdown_it import TextCharsetMarkdownItParser, TextParserConfig
from rag_platform.contracts import common_types as ct
from rag_platform.contracts.chunk_set import ChunkSet, NormalizedRef
from rag_platform.contracts.cloud_event_envelope import CloudEventEnvelope
from rag_platform.contracts.embedded_chunk_set import EmbeddedChunkSet
from rag_platform.contracts.enriched_chunk_set import EnrichedChunkSet
from rag_platform.contracts.index_commit import IndexCommit
from rag_platform.contracts.index_record import IndexRecord
from rag_platform.contracts.ingest_request import IngestRequest
from rag_platform.contracts.normalized_document import NormalizedDocument, ParsedRef
from rag_platform.contracts.parsed_document import ParsedDocument
from rag_platform.contracts.source_document import SourceDocument
from rag_platform.orchestration.local.runner import LocalRunner, StageSpec
from rag_platform.pipelines import ingest as ingest_pipeline
from rag_platform.sdk.hashing import blake3_hex, hash_of, point_id_for_record, record_id
from rag_platform.sdk.policy import StagePolicy
from rag_platform.storage.artifact_store import ArtifactRef as StoreRef, FileArtifactStore

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

_ROOT = Path(__file__).resolve().parents[2]
_FIXED_NOW = datetime(2026, 9, 23, 9, 0, 0, tzinfo=UTC)
_PROFILE_HASH = hash_of("profile", "lite")
_WIN_DRIVE_URI_RE = re.compile(r"^file:///([A-Za-z]:)")

# Bible §5.4 "application/vnd.rag.{kebab-name}+json" media type per contract schema_type — the
# literal each generated `EnrichedChunkSet`/`EmbeddedChunkSet`/`IndexCommit` LineageRefs sub-model
# requires (unlike the looser `common_types.MediaType` pattern the F1/F2 adapters' own lineage_refs
# fields use; see `_fixup_lineage_media_types` docstring, open_issues).
_MEDIA_TYPE_OF: dict[str, str] = {
    "SourceDocument": "application/vnd.rag.source-document+json",
    "ParsedDocument": "application/vnd.rag.parsed-document+json",
    "NormalizedDocument": "application/vnd.rag.normalized-document+json",
    "ChunkSet": "application/vnd.rag.chunk-set+json",
    "EnrichedChunkSet": "application/vnd.rag.enriched-chunk-set+json",
    "EmbeddedChunkSet": "application/vnd.rag.embedded-chunk-set+json",
}

_FIXTURES: tuple[tuple[str, Path], ...] = (
    ("txt", _ROOT / "tests" / "fixtures" / "e2e" / "sample.txt"),
    ("md", _ROOT / "tests" / "fixtures" / "e2e" / "sample.md"),
    ("html", _ROOT / "tests" / "fixtures" / "e2e" / "sample.html"),
    ("hwpx-outlook", _ROOT / "samples" / "hwpx" / "kogl1-moef-oecd-outlook-20260923.hwpx"),
    ("hwpx-emergency-care", _ROOT / "samples" / "hwpx" / "kogl1-mohw-emergency-care-20260923.hwpx"),
    ("hwpx-synthetic", _ROOT / "samples" / "hwpx" / "synthetic-owpml-features.hwpx"),
)


def _root_value(value: Any) -> Any:
    """Unwrap a Pydantic `RootModel` (`Uri`, `Hex64`, `MediaType`, ...) to its plain Python value."""
    return value.root if hasattr(value, "root") else value


def _normalize_file_uri(uri: str) -> str:
    """Undo `AnyUrl`'s `file:///C:/...` (3-slash) re-normalization of a Windows drive path.

    `FileArtifactStore` writes/reads `file://C:/...` (2-slash) URIs directly by string prefix
    (bible §13.3); once a URI round-trips through any Pydantic `Uri`/`AnyUrl` field (every contract
    `ArtifactRef.uri` is one), pydantic canonicalizes it to the RFC 8089 3-slash form, which
    `FileArtifactStore.get_bytes` then misreads as an absolute POSIX path (`/C:/...`) on Windows.
    This is a Windows-only, test-harness-local workaround (`storage/artifact_store.py` is out of
    this WP's target-file scope) — see open_issues.
    """
    return _WIN_DRIVE_URI_RE.sub(r"file://\1", uri)


def _to_store_ref(ref: Any) -> StoreRef:
    """Convert any `ArtifactRef`-shaped contract value into the plain `storage` dataclass ref."""
    return StoreRef(
        uri=_normalize_file_uri(str(_root_value(ref.uri))),
        blake3=str(_root_value(ref.blake3)),
        media_type=str(_root_value(ref.media_type)),
        size_bytes=ref.size_bytes,
    )


def _as_contract_ref(ref: StoreRef) -> ct.ArtifactRef:
    """Wrap a `storage.ArtifactRef` dataclass as the contract `common_types.ArtifactRef` model.

    `sdk.context.DerivedArtifacts.put_source`/`put_derived` are documented to return the contract
    type (`sdk/context.py`'s `TYPE_CHECKING` import); some F1 parser adapters (e.g.
    `text_charset_markdown_it.py`) call `ct.ArtifactRef.model_validate(value)` on what `ctx.artifacts`
    hands back and do not accept a bare dataclass, so this harness's `_Artifacts` port must return
    the contract shape, not the raw storage dataclass.
    """
    return ct.ArtifactRef(
        uri=ref.uri,
        blake3=ref.blake3,
        media_type=ref.media_type,
        size_bytes=ref.size_bytes,
        schema_type=ref.schema_type,
        schema_version=ref.schema_version,
        stage_key=ref.stage_key,
    )


def _ref_dict(ref: StoreRef, schema_type: str) -> dict[str, Any]:
    """Build a `{source,parsed,...}` lineage_refs entry with the exact literal shape it needs."""
    return {
        "uri": ref.uri,
        "blake3": ref.blake3,
        "media_type": _MEDIA_TYPE_OF[schema_type],
        "schema_type": schema_type,
        "schema_version": "1.0.0",
        "size_bytes": ref.size_bytes,
        "stage_key": ref.stage_key,
    }


def _fixup_lineage_media_types(lineage_refs: dict[str, Any]) -> dict[str, Any]:
    """Re-stamp an upstream `lineage_refs` dict's per-key literal `media_type`/`schema_type`.

    The real F1/F2 adapters (`normalize/stage.py`, `chunk/structure_aware.py`) build their own
    `lineage_refs.{parsed,normalized}` through the generic `common_types.MediaType` pattern (any
    well-formed media type string passes), but `EnrichedChunkSet`/`EmbeddedChunkSet`/`IndexCommit`'s
    own generated `LineageRefs` sub-model requires each key's `Literal[...]` media type plus
    `schema_type`/`schema_version` (open issue: the codegen output has two incompatible
    `lineage_refs` shapes). Re-derive the correct literal per key so the payload validates.
    """
    key_to_schema_type = {
        "source": "SourceDocument",
        "parsed": "ParsedDocument",
        "normalized": "NormalizedDocument",
        "chunk_set": "ChunkSet",
        "enriched": "EnrichedChunkSet",
        "embedded": "EmbeddedChunkSet",
    }
    fixed: dict[str, Any] = {}
    for key, value in lineage_refs.items():
        schema_type = key_to_schema_type.get(key)
        if value is None or schema_type is None:
            continue
        fixed[key] = {
            "uri": value["uri"],
            "blake3": value["blake3"],
            "media_type": _MEDIA_TYPE_OF[schema_type],
            "schema_type": schema_type,
            "schema_version": "1.0.0",
            "size_bytes": value["size_bytes"],
            "stage_key": value.get("stage_key"),
        }
    return fixed


class _Artifacts:
    """`sdk.context.DerivedArtifacts` port over a tenant-bound `FileArtifactStore` slice."""

    def __init__(self, store: FileArtifactStore, tenant_id: str) -> None:
        self._store = store
        self._tenant_id = tenant_id

    async def put_source(self, data: bytes, *, media_type: str) -> ct.ArtifactRef:
        """Store envelope-free original bytes; see module docstring for the contract-ref return."""
        ref = await self._store.put_source(data, tenant_id=self._tenant_id, media_type=media_type)
        return _as_contract_ref(ref)

    async def put_derived(self, data: bytes, *, kind: str, ext: str, media_type: str) -> ct.ArtifactRef:
        """Store an envelope-free derived byte object; see module docstring for the return shape."""
        ref = await self._store.put_derived(data, tenant_id=self._tenant_id, kind=kind, ext=ext, media_type=media_type)
        return _as_contract_ref(ref)


class _StageCtx:
    """Minimal, freely-extensible `StageContext` stand-in (bible §4.1 members + per-stage extras)."""

    def __init__(self, **kwargs: Any) -> None:
        self.heartbeats: list[dict[str, Any]] = []
        self.lineage: dict[str, Any] = {}
        self.plan = None
        self.resume_details = None
        self.cancelled = False
        for key, value in kwargs.items():
            setattr(self, key, value)

    def now(self) -> datetime:
        """Return the harness's fixed clock (bible §4.1 `ctx.now()`; determinism for cache hits)."""
        return _FIXED_NOW

    def heartbeat(self, details: dict[str, Any]) -> None:
        """Record a resume-cursor detail (bible §4.1 `ctx.heartbeat`); this harness never resumes."""
        self.heartbeats.append(dict(details))

    def remaining_ms(self) -> int | None:
        """Return `None` (unbounded) — the router's per-candidate budget check never trips."""
        return None


class _FakeTokenCounter:
    """`sdk.ports.TokenCounter` stand-in bound to `chunker.structure_aware`'s default tokenizer."""

    tokenizer_id = "hf:BAAI/bge-m3"

    def count(self, text: str) -> int:
        """Return a crude character-based approximation (exact count is not asserted here)."""
        return max(1, len(text) // 3)


class _ParserBuilder:
    """`parser.router`'s `StageBuilder` port over a small closed set of format-specific parsers."""

    def __init__(self, factories: dict[str, Callable[[], Any]]) -> None:
        self._factories = factories

    def build_stage(self, plugin_id: str, _config: dict[str, Any], _services: Any = None) -> Any:
        """Build the candidate stage for `plugin_id`, or raise `KeyError` (§4.1 "installed" check)."""
        if plugin_id not in self._factories:
            raise KeyError(plugin_id)
        return self._factories[plugin_id]()


@dataclass
class _AdapterStage:
    """Bridges one real `Stage[In, Out]` (or hand-composed callable) into `LocalRunner`'s `Stage[bytes, bytes]`."""

    plugin_id: str
    in_type: type[Any]
    fp: str
    call: Callable[[Any, Any], Awaitable[Any]]
    config_schema: type = object
    requires_lineage: tuple[str, ...] = ()

    def capabilities(self) -> Any:
        """Return `None` — `LocalRunner` never calls this; only `Stage`'s 5-member shape needs it."""
        return None

    def fingerprint(self) -> str:
        """Return the wrapped real stage's own fingerprint (unchanged `stage_key` composition)."""
        return self.fp

    async def run(self, inp: bytes, ctx: Any) -> bytes:
        """Decode `inp` as `in_type`, run the wrapped stage, re-encode its output as JSON bytes."""
        model_in = self.in_type.model_validate_json(inp)
        model_out = await self.call(model_in, ctx)
        return model_out.model_dump_json().encode("utf-8")


def _dense_space_id(dim: int) -> str:
    return hash_of("space", "embedder.inprocess_fake", "dense", str(dim))


def _sparse_space_id(analyzer_id: str) -> str:
    return hash_of("space", "sparse_bm25", analyzer_id)


def _build_enriched_payload(
    *, chunk_set: ChunkSet, self_ref: StoreRef, enricher_fp: str, enrichments: dict[str, Any]
) -> dict[str, Any]:
    """Assemble the `EnrichedChunkSet` envelope around a already-computed `enrichments` mapping."""
    chunk_set_dump = chunk_set.model_dump(mode="json")
    return {
        "schema_version": "1.0.0",
        "schema_type": "EnrichedChunkSet",
        "tenant_id": chunk_set_dump["tenant_id"],
        "collection_id": chunk_set_dump["collection_id"],
        "producer": {
            "plugin_id": "enricher.pipeline_e2e",
            "plugin_version": "0.1.0",
            "config_hash": hash_of("config", "e2e"),
            "image_digest": None,
            "model_ids": [],
        },
        "quality": chunk_set_dump["quality"],
        "warnings": [],
        "created_at": "2026-09-23T09:00:00.000Z",
        "lineage_refs": {
            **_fixup_lineage_media_types(chunk_set_dump["lineage_refs"]),
            "chunk_set": _ref_dict(self_ref, "ChunkSet"),
        },
        "chunk_set_id": chunk_set_dump["chunk_set_id"],
        "document_id": chunk_set_dump["document_id"],
        "doc_version": chunk_set_dump["doc_version"],
        "chunk_set_ref": _ref_dict(self_ref, "ChunkSet"),
        "enricher_fingerprint": enricher_fp,
        "policy_hash": hash_of("policy", "e2e"),
        "status": "complete",
        "budget_used": {
            "provider": None,
            "model_id": None,
            "llm_tokens_in": 0,
            "llm_tokens_out": 0,
            "cost_usd": 0,
            "calls": 0,
            "budget_remaining_tokens": 0,
        },
        "enrichments": enrichments,
        "stats": {
            "chunks_enriched": len(enrichments),
            "llm_cache_hits": 0,
            "entities_total": 0,
            "chunks_partial": 0,
        },
    }


def _build_embedded_payload(
    *,
    enriched: EnrichedChunkSet,
    self_ref: StoreRef,
    embedder: InprocessFakeEmbedder,
    vectors: dict[str, Any],
    vectors_ref: ct.ArtifactRef,
    dense_space: str,
    sparse_space: str,
) -> dict[str, Any]:
    """Assemble the `EmbeddedChunkSet` envelope around already-computed per-chunk `vectors`."""
    enriched_dump = enriched.model_dump(mode="json")
    embedding_profile_hash = hash_of("spaces", f"dense={dense_space}", f"sparse_bm25={sparse_space}")
    return {
        "schema_version": "1.0.0",
        "schema_type": "EmbeddedChunkSet",
        "tenant_id": enriched_dump["tenant_id"],
        "collection_id": enriched_dump["collection_id"],
        "producer": {
            "plugin_id": embedder.plugin_id,
            "plugin_version": "0.1.0",
            "config_hash": hash_of("config", "e2e"),
            "image_digest": None,
            "model_ids": [],
        },
        "quality": enriched_dump["quality"],
        "warnings": [],
        "created_at": "2026-09-23T09:00:00.000Z",
        "lineage_refs": {
            **_fixup_lineage_media_types(enriched_dump["lineage_refs"]),
            "enriched": _ref_dict(self_ref, "EnrichedChunkSet"),
        },
        "chunk_set_id": enriched_dump["chunk_set_id"],
        "document_id": enriched_dump["document_id"],
        "doc_version": enriched_dump["doc_version"],
        "enriched_ref": _ref_dict(self_ref, "EnrichedChunkSet"),
        "embedding_space_ids": {"dense": dense_space, "sparse_bm25": sparse_space},
        "embedding_profile_hash": embedding_profile_hash,
        "embedder_fingerprint": hash_of(
            "embedder", embedder.plugin_id, "0.1.0", hash_of("config", "e2e"), "", embedding_profile_hash
        ),
        "mode": "document",
        "pooling": "cls",
        "vectors_ref": {
            "uri": _root_value(vectors_ref.uri),
            "blake3": _root_value(vectors_ref.blake3),
            "media_type": "application/json",
            "size_bytes": vectors_ref.size_bytes,
        },
        "vectors": vectors,
        "cache_hits": 0,
        "stats": {
            "vectors_total": len(vectors),
            "bytes_dense": len(vectors) * embedder.dim * 4,
            "bytes_sparse": 0,
            "bytes_late_interaction": 0,
        },
    }


def _build_index_record(
    *,
    chunk: ct.Chunk,
    enrichment: Any,
    dense_vector: list[float],
    sparse_bm25: dict[str, Any],
    source_dump: dict[str, Any],
    chunk_set_dump: dict[str, Any],
    embedded_dump: dict[str, Any],
    scope: tuple[str, str, str],
    commit_id: str,
    generation: int,
    title: str,
) -> IndexRecord:
    """Build one leaf/level-2 `IndexRecord` from real upstream `Chunk`/`SourceDocument` fields."""
    tenant_id, collection_id, document_id = scope
    chunk_dump = chunk.model_dump(mode="json")
    chunk_id = chunk_dump["chunk_id"]
    acl = source_dump["acl"]
    metadata = source_dump.get("metadata") or {}
    text = chunk_dump["text"]
    rid = record_id(tenant_id, collection_id, document_id, generation, chunk_id)
    payload = {
        "record_id": rid,
        "point_id": str(point_id_for_record(rid)),
        "chunk_id": chunk_id,
        "tenant_id": tenant_id,
        "collection_id": collection_id,
        "document_id": document_id,
        "doc_version": chunk_set_dump["doc_version"],
        "commit_id": commit_id,
        "index_generation": generation,
        "is_current": False,
        "item_kind": chunk_dump["item_kind"],
        "level": chunk_dump["level"],
        "parent_chunk_id": chunk_dump.get("parent_chunk_id"),
        "ordinal": chunk_dump["ordinal"],
        "vectors": {"dense": list(dense_vector), "sparse_bm25": sparse_bm25},
        "index_text": enrichment.index_text,
        "lexical_terms": sorted({keyword.term for keyword in enrichment.keywords}),
        "text": text[:8192],
        "text_preview": text[:200],
        "text_truncated": False,
        "context_prefix": chunk_dump["context_prefix"]["deterministic"] or "",
        "block_refs": chunk_dump["block_refs"],
        "sentence_spans": chunk_dump["sentence_spans"],
        "title": title[:512],
        "heading_path": chunk_dump["heading_path"],
        "numbering_path": chunk_dump.get("numbering_path") or [],
        "source_uri": source_dump["source_uri"],
        "external_id": source_dump.get("external_id"),
        "doc_date": metadata.get("doc_date"),
        "doc_type": metadata.get("doc_type"),
        "department": metadata.get("department"),
        "tags": metadata.get("tags"),
        "lang": chunk_dump["lang"],
        "genre": chunk_set_dump["genre_route"],
        "page_start": None,
        "page_end": None,
        "text_source": chunk_dump["text_source"],
        "ocr_confidence_min": chunk_dump.get("ocr_confidence_min"),
        "acl_allow": acl["allow_principals"],
        "acl_deny": acl.get("deny_principals") or [],
        "acl_visibility": acl.get("visibility", "tenant"),
        "acl_classification": acl.get("classification", "internal"),
        "acl_embargo_until": acl.get("embargo_until"),
        "acl_expires_at": acl.get("expires_at"),
        "acl_hash": source_dump["acl_hash"],
        "content_hash": chunk_dump["content_hash"],
        "token_count_primary": chunk_dump["token_counts"].get(chunk_set_dump["primary_tokenizer_id"], 0),
        "risk_score": enrichment.risk_score,
        "pii_policy_applied": chunk_set_dump["pii_policy_applied"],
        "embedding_space_ids": embedded_dump["embedding_space_ids"],
        "embedding_profile_hash": embedded_dump["embedding_profile_hash"],
        "analyzer_id": chunk_set_dump["analyzer_id"],
        "dictionary_hash": chunk_set_dump["dictionary_hash"],
        "chunk_set_blake3": embedded_dump["lineage_refs"]["chunk_set"]["blake3"],
        "updated_at": "2026-09-23T09:00:00.000Z",
    }
    return IndexRecord.model_validate(payload)


def _build_index_commit_payload(
    *,
    embedded_dump: dict[str, Any],
    chunk_set_dump: dict[str, Any],
    self_ref: StoreRef,
    scope: tuple[str, str, str],
    job_id: str,
    commit_id: str,
    generation: int,
    records: list[IndexRecord],
    backend: QdrantIndexBackend,
    physical: str,
    fingerprints: tuple[str, str, str],
) -> dict[str, Any]:
    """Assemble the `IndexCommit` envelope around an already-committed record batch."""
    tenant_id, collection_id, document_id = scope
    parser_fp, normalizer_fp, enricher_fp = fingerprints
    commit_hash = hash_of("commit", commit_id, str(generation), *(record.record_id.root for record in records))
    embedded_lineage = {
        **_fixup_lineage_media_types(embedded_dump["lineage_refs"]),
        "embedded": _ref_dict(self_ref, "EmbeddedChunkSet"),
    }
    return {
        "schema_version": "1.0.0",
        "schema_type": "IndexCommit",
        "tenant_id": tenant_id,
        "collection_id": collection_id,
        "producer": {
            "plugin_id": backend.plugin_id,
            "plugin_version": "0.1.0",
            "config_hash": hash_of("config", "e2e"),
            "image_digest": None,
            "model_ids": [],
        },
        "quality": embedded_dump["quality"],
        "warnings": [],
        "created_at": "2026-09-23T09:00:00.000Z",
        "lineage_refs": embedded_lineage,
        "commit_id": commit_id,
        "document_id": document_id,
        "doc_version": chunk_set_dump["doc_version"],
        "job_id": job_id,
        "kind": "upsert",
        "previous_commit_id": None,
        "supersedes_commit_ids": [],
        "status": "committed",
        "index_generation": generation,
        "profile_id": "lite",
        "profile_hash": _PROFILE_HASH,
        "parser_fingerprint_hash": parser_fp,
        "normalizer_fingerprint": normalizer_fp,
        "chunker_config_hash": chunk_set_dump["chunker_config_hash"],
        "enricher_fingerprint": enricher_fp,
        "embedder_fingerprint": embedded_dump["embedder_fingerprint"],
        "embedding_space_ids": embedded_dump["embedding_space_ids"],
        "embedding_profile_hash": embedded_dump["embedding_profile_hash"],
        "analyzer_id": chunk_set_dump["analyzer_id"],
        "dictionary_hash": chunk_set_dump["dictionary_hash"],
        "record_count": len(records),
        "commit_hash": commit_hash,
        "backend_results": [
            {
                "backend_id": backend.plugin_id,
                "backend_version": backend.backend_version or "local",
                "physical_name": physical,
                "alias": physical,
                "upserted": len(records),
                "deleted": 0,
                "duration_ms": 1,
                "status": "ok",
            }
        ],
        "artifact_refs": embedded_lineage,
        "stats": {
            "bytes_dense": len(records) * 16 * 4,
            "bytes_sparse": 0,
            "bytes_lexical": 0,
            "bytes_late_interaction": 0,
            "leaf_count": len(records),
            "parent_count": max(0, len(chunk_set_dump["chunks"]) - len(records)),
            "llm_tokens": 0,
            "wall_seconds": 0.01,
        },
        "events_emitted": [],
        "started_at": "2026-09-23T09:00:00.000Z",
        "committed_at": "2026-09-23T09:00:00.500Z",
        "updated_at": "2026-09-23T09:00:00.500Z",
    }


@dataclass
class _E2EContext:
    """`LocalRunner`'s `context: LocalContext`-shaped collaborator (bible §11.1's local runtime)."""

    tenant_id: str
    collection_id: str
    store: FileArtifactStore
    extra: dict[str, Any] = field(default_factory=dict)

    def now(self) -> datetime:
        """Return the harness's fixed clock."""
        return _FIXED_NOW

    async def sleep(self, _duration: timedelta) -> None:
        """No-op: this harness's stages never raise a `RETRYABLE` `StageError`."""
        return

    def build_stage_context(
        self, *, stage_token_counter: Any, document_id: str | None = None, job_id: str | None = None
    ) -> _StageCtx:
        """Build the `StageContext` for one `Stage.run` call, folding in `self.extra` for this stage."""
        return _StageCtx(
            tenant_id=self.tenant_id,
            collection_id=self.collection_id,
            document_id=document_id,
            job_id=job_id,
            trace_id="e2e-trace",
            profile_hash=_PROFILE_HASH,
            token_counter=stage_token_counter,
            analyzer=None,
            artifacts=_Artifacts(self.store, self.tenant_id),
            **self.extra,
        )


class _E2EPipeline:
    """`PipelineContext` implementation (bible §11.1) driving every stage through `LocalRunner`.

    Stands in for the not-yet-built `orchestration/context.py` shell: per `ctx.run(stage, ...)`
    call, resolves the input bytes, injects the stage-specific extra `StageContext` members the F1
    adapters already expect (`source_bytes`, `parsed_ref`, `normalized_ref` — bible §4.1 open gaps,
    see open_issues) and runs a length-1 `LocalRunner.run([...])` chain so `stage_key` caching
    (ADR-0037) applies per stage exactly as it would inside a real multi-stage run.
    """

    def __init__(
        self,
        *,
        store: FileArtifactStore,
        tenant_id: str,
        collection_id: str,
        document_id: str,
        job_id: str,
        backend: QdrantIndexBackend,
        physical: str,
    ) -> None:
        self.store = store
        self.tenant_id = tenant_id
        self.collection_id = collection_id
        self.document_id = document_id
        self.job_id = job_id
        self.backend = backend
        self.physical = physical
        self.context = _E2EContext(tenant_id=tenant_id, collection_id=collection_id, store=store)
        self.runner = LocalRunner(context=self.context, store=store, token_counter=_FakeTokenCounter())

        builder = _ParserBuilder(
            {
                "parser.hwpx_python_hwpx": lambda: HwpxPythonHwpxParser(HwpxParserConfig()),
                "parser.text_charset_markdown_it": lambda: TextCharsetMarkdownItParser(TextParserConfig()),
                "parser.html_trafilatura_docling": lambda: HtmlTrafilaturaDoclingParser(HtmlParserConfig()),
            }
        )
        self._router = ParseRouterStage(builder)
        self._normalizer = NormalizerChainStage(NormalizerChainConfig())
        self._chunker = StructureAwareChunkerStage(StructureAwareChunkerConfig())
        self._fetcher = FsspecHttpxFetcher(FetchConfig(file_allowed_roots=(str(_ROOT),)))
        self._enrichers = (DeterministicPrefixEnricher(), KoreanKeywordsEnricher(), DerivedMetaEnricher())
        self._embedder = InprocessFakeEmbedder(embedding_space_id="fake:e2e", dim=16)
        self._tokenizer = WhitespaceTokenizer()
        self.backend.ensure_collection(physical, CollectionLayout(dense_dim=16, sparse_bm25=True, sparse_learned=False))

        self._source: SourceDocument | None = None
        self._chunk_set: ChunkSet | None = None
        self._enriched: EnrichedChunkSet | None = None
        self._dense_vectors: dict[str, list[float]] = {}
        self._index_generation = 0

        enrich_fp = hash_of("producer", "enricher.pipeline_e2e")
        self._stage_of: dict[str, _AdapterStage] = {
            "fetch": _AdapterStage(
                self._fetcher.plugin_id, IngestRequest, self._fetcher.fingerprint(), self._call_fetch
            ),
            "parse": _AdapterStage(
                self._router.plugin_id, SourceDocument, self._router.fingerprint(), self._call_parse
            ),
            "normalize": _AdapterStage(
                self._normalizer.plugin_id, ParsedDocument, self._normalizer.fingerprint(), self._call_normalize
            ),
            "chunk": _AdapterStage(
                self._chunker.plugin_id, NormalizedDocument, self._chunker.fingerprint(), self._call_chunk
            ),
            "enrich": _AdapterStage("enricher.pipeline_e2e", ChunkSet, enrich_fp, self._call_enrich),
            "embed": _AdapterStage(
                self._embedder.plugin_id,
                EnrichedChunkSet,
                hash_of("producer", self._embedder.plugin_id, "0.1.0", str(self._embedder.dim)),
                self._call_embed,
            ),
            "index": _AdapterStage(
                self.backend.plugin_id, EmbeddedChunkSet, hash_of("producer", self.backend.plugin_id), self._call_index
            ),
            "publish": _AdapterStage(
                "publish.local_ledger", IndexCommit, hash_of("producer", "publish.local_ledger"), self._call_publish
            ),
        }
        self.run_log: list[Any] = []
        self.last_index_commit: IndexCommit | None = None

    # -- stage bodies (each wraps one real adapter or a hand-composed group) -----------------

    async def _call_fetch(self, req: IngestRequest, ctx: Any) -> SourceDocument:
        source = await self._fetcher.run(req, ctx)
        self._source = source
        return source

    async def _call_parse(self, source: SourceDocument, ctx: Any) -> ParsedDocument:
        async def _source_bytes() -> bytes:
            return await self.store.get_bytes(_to_store_ref(source.artifact))

        ctx.source_bytes = _source_bytes
        return await self._router.run(source, ctx)

    async def _call_normalize(self, parsed: ParsedDocument, ctx: Any) -> NormalizedDocument:
        return await self._normalizer.run(parsed, ctx)

    async def _call_chunk(self, normalized: NormalizedDocument, ctx: Any) -> ChunkSet:
        chunk_set = await self._chunker.run(normalized, ctx)
        self._chunk_set = chunk_set
        return chunk_set

    async def _call_enrich(self, chunk_set: ChunkSet, ctx: Any) -> EnrichedChunkSet:
        acc: dict[str, dict[str, Any]] = {}
        for enricher in self._enrichers:
            await enricher.enrich(chunk_set.chunks, ctx, acc)

        leaf_levels = (ct.ChunkLevel.integer_0, ct.ChunkLevel.integer_2)
        indexable = [chunk for chunk in chunk_set.chunks if chunk.level in leaf_levels]
        enrichments = {
            chunk.chunk_id.root: _enrichment_dict(acc.get(chunk.chunk_id.root, {}), chunk) for chunk in indexable
        }
        payload = _build_enriched_payload(
            chunk_set=chunk_set, self_ref=ctx.self_ref, enricher_fp=self._stage_of["enrich"].fp, enrichments=enrichments
        )
        enriched = EnrichedChunkSet.model_validate(payload)
        self._enriched = enriched
        return enriched

    async def _call_embed(self, enriched: EnrichedChunkSet, ctx: Any) -> EmbeddedChunkSet:
        chunk_ids = sorted(enriched.enrichments.keys())
        embed_texts = [enriched.enrichments[cid].embed_text for cid in chunk_ids]
        dense_vectors = self._embedder.embed_documents(embed_texts) if embed_texts else []
        analyzer_id = self._tokenizer.analyzer_id

        vectors: dict[str, Any] = {}
        for offset, cid in enumerate(chunk_ids):
            sparse = document_vector(self._tokenizer.tokenize(enriched.enrichments[cid].index_text))
            sparse_payload = (
                sparse.model_dump(mode="json") if sparse is not None else {"indices": [0], "values": [0.0001]}
            )
            vectors[cid] = {
                "dense": {"name": "dense", "dim": self._embedder.dim, "offset": offset},
                "sparse_bm25": {"name": "sparse_bm25", "vocab_id": analyzer_id, **sparse_payload},
                "embed_text_hash": blake3_hex(embed_texts[offset]),
                "truncated": False,
            }
        vectors_ref = await ctx.artifacts.put_derived(
            json.dumps({"chunk_ids": chunk_ids, "dense": dense_vectors}).encode("utf-8"),
            kind="vectors",
            ext="json",
            media_type="application/json",
        )
        payload = _build_embedded_payload(
            enriched=enriched,
            self_ref=ctx.self_ref,
            embedder=self._embedder,
            vectors=vectors,
            vectors_ref=vectors_ref,
            dense_space=_dense_space_id(self._embedder.dim),
            sparse_space=_sparse_space_id(analyzer_id),
        )
        embedded = EmbeddedChunkSet.model_validate(payload)
        self._dense_vectors = dict(zip(chunk_ids, dense_vectors, strict=True))
        return embedded

    async def _call_index(self, embedded: EmbeddedChunkSet, ctx: Any) -> IndexCommit:
        if self._source is None or self._chunk_set is None or self._enriched is None:
            msg = "index stage needs the source/chunk_set/enriched state a prior stage call sets"
            raise RuntimeError(msg)
        source_dump = self._source.model_dump(mode="json")
        chunk_set_dump = self._chunk_set.model_dump(mode="json")
        embedded_dump = embedded.model_dump(mode="json")
        by_chunk_id = {chunk.chunk_id.root: chunk for chunk in self._chunk_set.chunks}
        metadata = source_dump.get("metadata") or {}
        title = metadata.get("title") or source_dump["source_uri"].rsplit("/", 1)[-1]
        scope = (self.tenant_id, self.collection_id, self.document_id)

        self._index_generation += 1
        generation = self._index_generation
        commit_id = str(ULID())
        records = [
            _build_index_record(
                chunk=by_chunk_id[chunk_id],
                enrichment=self._enriched.enrichments[chunk_id],
                dense_vector=self._dense_vectors[chunk_id],
                sparse_bm25={
                    "indices": vector_bundle["sparse_bm25"]["indices"],
                    "values": vector_bundle["sparse_bm25"]["values"],
                },
                source_dump=source_dump,
                chunk_set_dump=chunk_set_dump,
                embedded_dump=embedded_dump,
                scope=scope,
                commit_id=commit_id,
                generation=generation,
                title=title,
            )
            for chunk_id, vector_bundle in embedded_dump["vectors"].items()
        ]
        self.backend.upsert(self.physical, records, commit_id=commit_id, index_generation=generation)
        self.backend.set_current(
            self.physical,
            tenant_id=self.tenant_id,
            collection_id=self.collection_id,
            document_id=self.document_id,
            index_generation=generation,
        )
        payload = _build_index_commit_payload(
            embedded_dump=embedded_dump,
            chunk_set_dump=chunk_set_dump,
            self_ref=ctx.self_ref,
            scope=scope,
            job_id=self.job_id,
            commit_id=commit_id,
            generation=generation,
            records=records,
            backend=self.backend,
            physical=self.physical,
            fingerprints=(self._router.fingerprint(), self._normalizer.fingerprint(), self._stage_of["enrich"].fp),
        )
        commit = IndexCommit.model_validate(payload)
        self.last_index_commit = commit
        return commit

    async def _call_publish(self, commit: IndexCommit, _ctx: Any) -> CloudEventEnvelope:
        commit_dump = commit.model_dump(mode="json")
        payload = {
            "specversion": "1.0",
            "id": str(ULID()),
            "source": "urn:rag:worker",
            "type": "ingest.document.indexed",
            "time": "2026-09-23T09:00:00.600Z",
            "subject": f"tenant/{self.tenant_id}/document/{self.document_id}",
            "datacontenttype": "application/json",
            "tenantid": self.tenant_id,
            "data": {
                "job_id": self.job_id,
                "document_id": self.document_id,
                "collection_id": self.collection_id,
                "stage": "index",
                "doc_version": commit_dump["doc_version"],
                "quality": commit_dump["quality"],
                "commit_id": commit_dump["commit_id"],
                "index_generation": commit_dump["index_generation"],
                "commit_hash": commit_dump["commit_hash"],
                "record_count": commit_dump["record_count"],
                "job_state": "succeeded",
            },
        }
        return CloudEventEnvelope.model_validate(payload)

    # -- PipelineContext protocol (bible §11.1) ----------------------------------------------

    def _extra_for(self, stage: str, inp_ref: StoreRef) -> dict[str, Any]:
        """Bible §4.1 open gap: `ctx.parsed_ref`/`ctx.normalized_ref` (this stage's own input ref)."""
        if stage == "normalize":
            return {
                "parsed_ref": ParsedRef(
                    uri=inp_ref.uri,
                    blake3=inp_ref.blake3,
                    media_type=inp_ref.media_type,
                    schema_type="ParsedDocument",
                    schema_version="1.0.0",
                    size_bytes=inp_ref.size_bytes,
                )
            }
        if stage == "chunk":
            return {
                "normalized_ref": NormalizedRef(
                    uri=inp_ref.uri,
                    blake3=inp_ref.blake3,
                    media_type=inp_ref.media_type,
                    schema_type="NormalizedDocument",
                    schema_version="1.0.0",
                    size_bytes=inp_ref.size_bytes,
                )
            }
        if stage in ("enrich", "embed", "index", "publish"):
            return {"self_ref": inp_ref}
        return {}

    async def _rehydrate_state(self, stage: str, ref: StoreRef) -> None:
        """Re-derive instance state a later hand-composed stage needs, even on a cache hit.

        ADR-0037 cache hits skip `Stage.run()` entirely (`LocalRunner.run`), so `_call_chunk`/
        `_call_fetch`/`_call_enrich`/`_call_embed` never execute on a rerun; without this, `index`
        would see stale (or, on a fresh `_E2EPipeline` instance, absent) `self._source`/
        `self._chunk_set`/`self._enriched`/`self._dense_vectors`.
        """
        if stage not in ("fetch", "chunk", "enrich", "embed"):
            return
        out_bytes = await self.store.get_bytes(ref)
        if stage == "fetch":
            self._source = SourceDocument.model_validate_json(out_bytes)
        elif stage == "chunk":
            self._chunk_set = ChunkSet.model_validate_json(out_bytes)
        elif stage == "enrich":
            self._enriched = EnrichedChunkSet.model_validate_json(out_bytes)
        else:
            embedded = EmbeddedChunkSet.model_validate_json(out_bytes)
            vectors_blob = json.loads(await self.store.get_bytes(_to_store_ref(embedded.vectors_ref)))
            self._dense_vectors = dict(zip(vectors_blob["chunk_ids"], vectors_blob["dense"], strict=True))

    async def run(self, stage: str, inp_ref: Any, out_type: type[Any], policy: StagePolicy) -> Any:
        """Bible §11.1 `PipelineContext.run`: one stage, through a length-1 `LocalRunner.run([...])`."""
        spec = StageSpec(name=stage, stage=self._stage_of[stage], policy=policy, schema_type=out_type.__name__)
        input_bytes = await self.store.get_bytes(inp_ref)
        self.context.extra = self._extra_for(stage, inp_ref)
        result = await self.runner.run([spec], input_bytes, document_id=self.document_id, job_id=self.job_id)
        self.run_log.extend(result.log)
        if result.status != "succeeded":
            errors = result.errors
            if errors:
                raise errors[0]
            msg = f"stage {stage!r} ended in status {result.status!r}"
            raise RuntimeError(msg)
        await self._rehydrate_state(stage, result.ref)
        return result.ref

    async def emit(self, _event: Any) -> None:
        """Local mode has no outbox relay (bible §11.1); this harness does not assert on it."""
        return

    def now(self) -> datetime:
        """Return the harness's fixed clock (bible §11.1 `PipelineContext.now`)."""
        return _FIXED_NOW

    async def sleep(self, _duration: timedelta) -> None:
        """No-op: `pipelines.ingest.run` never calls this directly."""
        return


def _enrichment_dict(bucket: dict[str, Any], chunk: ct.Chunk) -> dict[str, Any]:
    """Fill the platform-synthesis fields (§2.1 chain order 5) the deterministic enrichers skip."""
    return {
        "embed_text": bucket.get("embed_text", chunk.text),
        "index_text": bucket.get("index_text", chunk.lexical_text),
        "strip_offsets": bucket.get("strip_offsets", {"text_start_in_embed": 0, "text_start_in_index": 0}),
        "keywords": bucket.get("keywords", []),
        "entities": [],
        "dates": bucket.get("dates"),
        "law_refs": bucket.get("law_refs"),
        "risk_flags": [],
        "risk_score": 0.0,
        "pii_entity_counts": {},
        "status": "complete",
    }


class _Profile:
    """`pipelines.ingest.PipelineProfile` stand-in: every stage on, `recount` off (bible §4.2)."""

    _policy = StagePolicy(
        task_queue="ingest-cpu", start_to_close=timedelta(minutes=5), heartbeat=None, max_attempts=3, resumable=False
    )

    def has_stage(self, stage: str) -> bool:
        """`recount` is unneeded: the fake embedder's tokenizer already matches the chunker's."""
        return stage != "recount"

    def stage_policy(self, _stage: str) -> StagePolicy:
        """Return one fixed, generous policy for every stage (no retries are expected to fire)."""
        return self._policy


async def _make_req_ref(store: FileArtifactStore, *, tenant_id: str, collection_id: str, source_uri: str) -> StoreRef:
    req = IngestRequest.model_validate(
        {
            "schema_version": "1.0.0",
            "request_id": str(ULID()),
            "collection_id": collection_id,
            "source_uri": source_uri,
            "acl": {"allow_principals": ["tenant:*"], "visibility": "tenant"},
            "requested_at": "2026-09-22T09:00:00.000Z",
        }
    )
    return await store.put_artifact(
        req.model_dump_json().encode("utf-8"),
        tenant_id=tenant_id,
        schema_type="IngestRequest",
        media_type="application/vnd.rag.ingest-request+json",
    )


@dataclass
class _Harness:
    store: FileArtifactStore
    backend: QdrantIndexBackend
    physical: str
    tenant_id: str
    collection_id: str
    profile: _Profile


@pytest.fixture(scope="module")
def harness(tmp_path_factory: pytest.TempPathFactory) -> _Harness:
    """One shared `FileArtifactStore` + local Qdrant collection for every fixture in this module."""
    store = FileArtifactStore(tmp_path_factory.mktemp("e2e-store"))
    backend = QdrantIndexBackend.local()
    tenant_id = str(ULID())
    physical = physical_collection_name(_PROFILE_HASH, tenant_id)
    return _Harness(
        store=store,
        backend=backend,
        physical=physical,
        tenant_id=tenant_id,
        collection_id=str(ULID()),
        profile=_Profile(),
    )


async def _run_once(harness_: _Harness, *, document_id: str, job_id: str, req_ref: StoreRef) -> _E2EPipeline:
    pipeline = _E2EPipeline(
        store=harness_.store,
        tenant_id=harness_.tenant_id,
        collection_id=harness_.collection_id,
        document_id=document_id,
        job_id=job_id,
        backend=harness_.backend,
        physical=harness_.physical,
    )
    await ingest_pipeline.run(pipeline, req_ref, harness_.profile)
    return pipeline


@pytest.mark.parametrize(("_case_id", "source_path"), _FIXTURES, ids=[case_id for case_id, _ in _FIXTURES])
async def test_ingest_pipeline_commits_indexes_and_is_idempotent_on_rerun(
    harness: _Harness, _case_id: str, source_path: Path
) -> None:
    """fetch→detect·parse→normalize→chunk→enrich→embed→index→publish, twice, over `source_path`.

    Bible §4.2 acceptance: first run commits an `IndexCommit` and the leaf/level-2 chunk count is
    visible (`is_current=true`) in the local Qdrant collection; the second run over the same
    `document_id` hits the `stage_key` cache for every content-addressed stage `fetch`/`index` do
    not exempt (ADR-0037) and leaves the visible record count unchanged (idempotent re-ingest).
    """
    document_id = str(ULID())
    job_id = str(ULID())
    req_ref = await _make_req_ref(
        harness.store, tenant_id=harness.tenant_id, collection_id=harness.collection_id, source_uri=source_path.as_uri()
    )

    first = await _run_once(harness, document_id=document_id, job_id=job_id, req_ref=req_ref)
    assert first.last_index_commit is not None
    assert first.last_index_commit.status == "committed"
    assert first.last_index_commit.record_count >= 1

    current_filter = scope_filter(
        harness.tenant_id, collection_id=harness.collection_id, document_id=document_id, is_current=True
    )
    first_count = harness.backend.count(harness.physical, current_filter)
    assert first_count == first.last_index_commit.record_count

    second = await _run_once(harness, document_id=document_id, job_id=job_id, req_ref=req_ref)
    cache_hit_stages = {entry.name for entry in second.run_log if entry.cache_hit}
    # `parse`'s own stage_key input is `fetch`'s full output bytes, which carries a non-cacheable
    # timing field (`fetch_report.duration_ms`/`bytes_per_sec`, bible §4.2 "fetch: 캐시 없음") — so
    # `parse` itself is not a guaranteed cache hit (open_issues). Everything downstream of it is,
    # since none of their real inputs read those timing fields.
    assert {"normalize", "chunk", "enrich", "embed"} <= cache_hit_stages

    second_count = harness.backend.count(harness.physical, current_filter)
    assert second_count == first_count


def test_stage_output_types_are_the_real_generated_contracts() -> None:
    """`pipelines.ingest.STAGE_OUTPUT_TYPES` (WP-303) must resolve to the codegen'd contract classes."""
    assert ingest_pipeline.STAGE_OUTPUT_TYPES["fetch"] is SourceDocument
    assert ingest_pipeline.STAGE_OUTPUT_TYPES["parse"] is ParsedDocument
    assert ingest_pipeline.STAGE_OUTPUT_TYPES["normalize"] is NormalizedDocument
    assert ingest_pipeline.STAGE_OUTPUT_TYPES["chunk"] is ChunkSet
    assert ingest_pipeline.STAGE_OUTPUT_TYPES["recount"] is ChunkSet
    assert ingest_pipeline.STAGE_OUTPUT_TYPES["enrich"] is EnrichedChunkSet
    assert ingest_pipeline.STAGE_OUTPUT_TYPES["embed"] is EmbeddedChunkSet
    assert ingest_pipeline.STAGE_OUTPUT_TYPES["index"] is IndexCommit
    assert ingest_pipeline.STAGE_OUTPUT_TYPES["publish"] is CloudEventEnvelope
