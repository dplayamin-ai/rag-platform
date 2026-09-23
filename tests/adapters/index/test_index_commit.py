"""`index` 스테이지 조립·`IndexCommit` 세대 사가(F3-02, WP-302) 단위·통합 테스트.

무엇을 검증하는지: (1) `build_index_records`가 `EmbeddedChunkSet.vectors`의 리프 2개만(부모 제외)
`IndexRecord`로 조립하고 `record_id`/`point_id`가 `sdk.hashing`과 대조 일치하는지, `acl_*`·`title`·
`tags`·`custom`·`lexical_terms`·`entity_ids`·`chunk_set_blake3`가 정확히 투영되는지. (2) 8,192바이트를
넘는 합성 텍스트가 문장 경계에서 절단되고 `block_refs`가 그 경계로 클리핑되는지. (3) `IndexSaga.commit`
정상 경로 — Qdrant 로컬 모드에 `is_current=true`로 플립되어 조회되고 원장 `documents.current_generation`
이 전진하는지. (4) 재실행 멱등성 — 같은 입력의 `record_id`/`commit_hash_of`가 결정적이고, 같은
`commit_id`로 두 번째 `commit()` 호출이 백엔드를 다시 건드리지 않는 no-op인지. (5) 롤백 — 플립 전
백엔드 실패는 신규 세대만 삭제, 플립 후 실패는 이전 세대 복원 후 신규 세대 삭제. (6) 세대 할당
불변식 — `index_generation`은 문서별 `max(index_commits.index_generation) + 1`로 할당되어(`Ledger.
list_commits`), 롤백된 세대 번호를 다음 커밋이 재사용하지 않는지.
설계 근거: 04-pipelines/13 §3(조립·검증 순서)·§6(단일 백엔드 no-op 전이)·§7(커밋 프로토콜), 바이블
§5.4(`IndexRecord`/`IndexCommit` 표)·§11.4(세대 사가), ADR-0026.
픽스처 출처: `tests/contracts/fixtures/index-record/001.json`·`chunk-set/001.json`·
`enriched-chunk-set/001.json`·`embedded-chunk-set/001.json`·`source-document/001.json`의 필드 모양을
참고해 이 파일이 직접 구성한 자체 정합 픽스처(부모 1 + 리프 2, 같은 `tenant_id`/`document_id`/
`chunk_id` 체인).
검증 계층: 1층(여기서 검증) — `QdrantIndexBackend.local()` + `testing.doubles.InMemoryLedger`.
"""

from __future__ import annotations

import hashlib
import math
from datetime import UTC, datetime
from typing import Any

import pytest

from rag_platform.adapters.index.qdrant.backend import QdrantIndexBackend, physical_collection_name
from rag_platform.adapters.index.qdrant.filters import scope_filter
from rag_platform.adapters.index.saga import IndexSaga
from rag_platform.adapters.index.stage import (
    IndexLineage,
    IndexStage,
    build_index_records,
    commit_hash_of,
    resolve_lineage,
)
from rag_platform.contracts.chunk_set import ChunkSet
from rag_platform.contracts.common_types import ArtifactRef, SentenceSpan1
from rag_platform.contracts.embedded_chunk_set import EmbeddedChunkSet
from rag_platform.contracts.enriched_chunk_set import EnrichedChunkSet
from rag_platform.contracts.source_document import SourceDocument
from rag_platform.sdk.hashing import blake3_hex, point_id_for_record, record_id as record_id_of
from rag_platform.sdk.stage import StageError
from rag_platform.testing.doubles.in_memory_ledger import InMemoryLedger

TENANT = "01J9ZQ4K7X2M8N3P5R6S7T8V9W"
COLLECTION = "01J9ZQ5A1B2C3D4E5F6G7H8J9K"
DOCUMENT = "01JAB3C4D5E6F7G8H9JKMNPQRS"
CHUNK_SET_ID = "01JAB3C4D5E6F7G8H9JKMNPQST"
REQUEST_ID = "01J9ZQ7B8C9D0E1F2G3H4J5K6M"
JOB_ID = "01JAB3D0E1F2G3H4J5K6M7N8P9"
NOW = datetime(2026, 9, 22, 9, 13, 40, tzinfo=UTC)


def _hex64(seed: str) -> str:
    return hashlib.sha256(seed.encode()).hexdigest()


def _hex32(seed: str) -> str:
    return hashlib.sha256(seed.encode()).hexdigest()[:32]


def _artifact_ref(seed: str, *, media_type: str, schema_type: str | None = None) -> dict[str, Any]:
    ref: dict[str, Any] = {
        "uri": f"s3://rag-artifacts/tenants/{TENANT}/artifacts/{seed}.json",
        "blake3": _hex64(seed),
        "media_type": media_type,
        "size_bytes": 1024,
    }
    if schema_type is not None:
        ref["schema_type"] = schema_type
        ref["schema_version"] = "1.0.0"
    return ref


def _unit(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(x * x for x in vector))
    return [x / norm for x in vector]


DOC_VERSION = _hex64("doc-version")
LEAF1 = _hex64("leaf-1")
LEAF2 = _hex64("leaf-2")
PARENT = _hex64("parent")
LEAF1_TEXT = "① 공공기관의 장은 정보보호 업무를 총괄하는 정보보호 책임자를 지정하여야 한다."
LEAF2_TEXT = "② 제1항에 따른 정보보호 책임자는 개인정보 보호법 제31조에 따른 개인정보 보호책임자를 겸임할 수 있다."
HEADING_PATH = ["Ⅲ. 정보보호 조직", "제5조(정보보호 책임자의 지정)"]
_PREFIX_HEAD = "공공기관 정보보호 업무 지침(행정안전부고시 제2026-12호)"
DETERMINISTIC_PREFIX = f"{_PREFIX_HEAD} › Ⅲ. 정보보호 조직 › 제5조(정보보호 책임자의 지정)"  # noqa: RUF001 - 바이블 §5.4 context_prefix 구분자 정본


def _chunk(
    chunk_id: str, *, text: str, ordinal: int, parent_chunk_id: str | None, block_id_seed: str
) -> dict[str, Any]:
    length = len(text)
    return {
        "chunk_id": chunk_id,
        "span": f"{_hex32(block_id_seed)}:0-{_hex32(block_id_seed)}:{length}",
        "item_kind": "text",
        "level": 0,
        "parent_chunk_id": parent_chunk_id,
        "ordinal": ordinal,
        "text": text,
        "lexical_text": text,
        "heading_path": HEADING_PATH,
        "numbering_path": ["Ⅲ", "제5조"],
        "block_refs": [
            {
                "block_id": _hex32(block_id_seed),
                "element_path": f"/hp:sec[0]/hp:p[{ordinal}]",
                "char_start": 0,
                "char_end": length,
                "original_char_start": 0,
                "original_char_end": length,
                "page": None,
                "bbox": None,
                "section_index": 0,
            }
        ],
        "sentence_spans": [[0, length]],
        "token_counts": {"hf:BAAI/bge-m3": 20, "tiktoken:o200k_base": 30},
        "lang": "ko",
        "context_prefix": {"deterministic": DETERMINISTIC_PREFIX, "generated": None, "generated_by": None},
        "text_source": "text_layer",
        "ocr_confidence_min": None,
        "content_hash": blake3_hex(text),
    }


def _parent_chunk() -> dict[str, Any]:
    text = f"{LEAF1_TEXT}\n{LEAF2_TEXT}"
    return {
        "chunk_id": PARENT,
        "span": f"{_hex32('parent-block')}:0-{_hex32('parent-block')}:{len(text)}",
        "item_kind": "parent",
        "level": 1,
        "parent_chunk_id": None,
        "child_chunk_ids": [LEAF1, LEAF2],
        "ordinal": 0,
        "text": text,
        "lexical_text": text,
        "heading_path": HEADING_PATH[:1],
        "numbering_path": ["Ⅲ"],
        "block_refs": [
            {
                "block_id": _hex32("parent-block"),
                "element_path": "/hp:sec[0]/hp:p[0]",
                "char_start": 0,
                "char_end": len(text),
                "original_char_start": 0,
                "original_char_end": len(text),
                "page": None,
                "bbox": None,
                "section_index": 0,
            }
        ],
        "sentence_spans": [[0, len(text)]],
        "token_counts": {"hf:BAAI/bge-m3": 40, "tiktoken:o200k_base": 60},
        "lang": "ko",
        "context_prefix": {"deterministic": HEADING_PATH[0], "generated": None, "generated_by": None},
        "text_source": "text_layer",
        "ocr_confidence_min": None,
        "content_hash": blake3_hex(text),
    }


def make_chunk_set() -> ChunkSet:
    """자체 정합 `ChunkSet`(부모 1 + 리프 2)."""
    chunks = [
        _chunk(LEAF1, text=LEAF1_TEXT, ordinal=0, parent_chunk_id=PARENT, block_id_seed="leaf1-block"),
        _chunk(LEAF2, text=LEAF2_TEXT, ordinal=1, parent_chunk_id=PARENT, block_id_seed="leaf2-block"),
        _parent_chunk(),
    ]
    data: dict[str, Any] = {
        "schema_version": "1.0.0",
        "schema_type": "ChunkSet",
        "tenant_id": TENANT,
        "collection_id": COLLECTION,
        "producer": {
            "plugin_id": "chunker.structure_aware",
            "plugin_version": "1.0.0",
            "config_hash": _hex64("chunker-config"),
            "image_digest": None,
        },
        "quality": "full",
        "warnings": [],
        "created_at": "2026-09-22T09:12:34.567Z",
        "lineage_refs": {
            "source": _artifact_ref("source-document", media_type="application/vnd.rag.source-document+json"),
            "parsed": _artifact_ref("parsed-document", media_type="application/vnd.rag.parsed-document+json"),
            "normalized": _artifact_ref(
                "normalized-document", media_type="application/vnd.rag.normalized-document+json"
            ),
        },
        "chunk_set_id": CHUNK_SET_ID,
        "document_id": DOCUMENT,
        "doc_version": DOC_VERSION,
        "normalized_ref": _artifact_ref(
            "normalized-document",
            media_type="application/vnd.rag.normalized-document+json",
            schema_type="NormalizedDocument",
        ),
        "document_hash": _hex64("normalized-document"),
        "chunker_id": "chunker.structure_aware",
        "chunker_config_hash": _hex64("chunker-config"),
        "primary_tokenizer_id": "hf:BAAI/bge-m3",
        "secondary_tokenizer_ids": ["tiktoken:o200k_base"],
        "genre_route": "law_article",
        "analyzer_id": "mecab-ko:1.3.7:ko-dic-2.1.1",
        "dictionary_hash": _hex64("dictionary"),
        "language": "ko",
        "pii_policy_applied": "mask",
        "stats": {
            "leaf_count": 2,
            "parent_count": 1,
            "table_part_count": 0,
            "summary_count": 0,
            "oversized_blocks": 0,
        },
        "chunks": chunks,
    }
    return ChunkSet.model_validate(data)


def _enrichment(chunk_id: str, *, index_text: str) -> dict[str, Any]:
    return {
        "embed_text": f"{DETERMINISTIC_PREFIX}\n{index_text}",
        "index_text": index_text,
        "strip_offsets": {"text_start_in_embed": len(DETERMINISTIC_PREFIX) + 1, "text_start_in_index": 0},
        "keywords": [
            {"term": "정보보호", "weight": 1.0, "source": "analyzer_nng"},
            {"term": "책임자", "weight": 0.5, "source": "analyzer_nng"},
            {"term": "정보보호", "weight": 1.0, "source": "analyzer_nng"},  # duplicate: dedup check
        ],
        "entities": [
            {
                "name": "개인정보 보호법",
                "type": "law",
                "canonical_id": "law:개인정보보호법",
                "confidence": 0.9,
                "extractor": "gliner2",
            },
            {"name": "무명 역할", "type": "role", "canonical_id": None, "confidence": 0.5, "extractor": "gliner2"},
        ],
        "risk_flags": [],
        "risk_score": 0.1,
        "pii_entity_counts": {},
        "status": "complete",
    }


def make_enriched_chunk_set() -> EnrichedChunkSet:
    """`ChunkSet.chunks`의 모든 `chunk_id`(부모 포함)를 채운 `EnrichedChunkSet`."""
    data: dict[str, Any] = {
        "schema_version": "1.0.0",
        "schema_type": "EnrichedChunkSet",
        "tenant_id": TENANT,
        "collection_id": COLLECTION,
        "producer": {
            "plugin_id": "enricher.pipeline",
            "plugin_version": "1.0.0",
            "config_hash": _hex64("enrich-config"),
            "image_digest": None,
            "model_ids": [],
        },
        "quality": "full",
        "warnings": [],
        "created_at": "2026-09-22T09:12:30.000Z",
        "lineage_refs": {
            "source": _artifact_ref(
                "source-document", media_type="application/vnd.rag.source-document+json", schema_type="SourceDocument"
            ),
            "parsed": _artifact_ref("parsed-document", media_type="application/vnd.rag.parsed-document+json"),
            "normalized": _artifact_ref(
                "normalized-document", media_type="application/vnd.rag.normalized-document+json"
            ),
            "chunk_set": _artifact_ref("chunk-set", media_type="application/vnd.rag.chunk-set+json"),
        },
        "chunk_set_id": CHUNK_SET_ID,
        "document_id": DOCUMENT,
        "doc_version": DOC_VERSION,
        "chunk_set_ref": _artifact_ref(
            "chunk-set", media_type="application/vnd.rag.chunk-set+json", schema_type="ChunkSet"
        ),
        "enricher_fingerprint": _hex64("enricher-fp"),
        "policy_hash": _hex64("policy"),
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
        "enrichments": {
            LEAF1: _enrichment(LEAF1, index_text=LEAF1_TEXT),
            LEAF2: _enrichment(LEAF2, index_text=LEAF2_TEXT),
            PARENT: _enrichment(PARENT, index_text=f"{LEAF1_TEXT}\n{LEAF2_TEXT}"),
        },
        "stats": {"chunks_enriched": 3, "llm_cache_hits": 0, "entities_total": 2, "chunks_partial": 0},
    }
    return EnrichedChunkSet.model_validate(data)


def make_source_document() -> SourceDocument:
    """`title`/`tags`/`custom`/`acl`가 채워진 자체 정합 `SourceDocument`."""
    data: dict[str, Any] = {
        "schema_version": "1.0.0",
        "schema_type": "SourceDocument",
        "tenant_id": TENANT,
        "collection_id": COLLECTION,
        "producer": {
            "plugin_id": "parser.format_detector_puremagic",
            "plugin_version": "1.0.0",
            "config_hash": _hex64("detect-config"),
            "image_digest": None,
        },
        "quality": "full",
        "warnings": [],
        "created_at": "2026-09-22T09:00:05.120Z",
        "lineage_refs": {},
        "document_id": DOCUMENT,
        "request_id": REQUEST_ID,
        "source_uri": "s3://mois-records/notices/2026/mois-notice-2026-12.hwpx",
        "resolved_uri": "s3://mois-records/notices/2026/mois-notice-2026-12.hwpx",
        "artifact": {
            "uri": f"s3://rag-artifacts/tenants/{TENANT}/sources/{_hex64('source-bytes')[:2]}/{_hex64('source-bytes')}",
            "blake3": DOC_VERSION,
            "media_type": "application/hwp+zip",
            "size_bytes": 12345,
        },
        "content_hash": DOC_VERSION,
        "doc_version": DOC_VERSION,
        "size_bytes": 12345,
        "media_type": "application/hwp+zip",
        "format": "hwpx",
        "format_confidence": 1.0,
        "container_flags": {"encrypted": False, "distribution": False, "compressed": True},
        "metadata": {
            "title": "공공기관 정보보호 업무 지침(행정안전부고시 제2026-12호)",
            "doc_date": "2026-03-02",
            "doc_type": "notice",
            "department": "정보보호정책과",
            "language_hint": "ko",
            "tags": ["정보보호", "고시", "공공기관"],
            "genre": "law_article",
            "custom": {"notice_no": "2026-12", "in_force": True},
        },
        "metadata_hash": _hex64("metadata"),
        "acl": {
            "allow_principals": ["group:mois_records", "group:mois_infosec"],
            "deny_principals": [],
            "visibility": "tenant",
            "classification": "internal",
            "embargo_until": None,
            "expires_at": None,
        },
        "acl_hash": _hex64("acl"),
        "pii_policy": "mask",
        "external_id": "MOIS-NOTICE-2026-12",
        "fetched_at": "2026-09-22T09:00:04.512Z",
    }
    return SourceDocument.model_validate(data)


def make_embedded_chunk_set() -> EmbeddedChunkSet:
    """리프 2개만 담은(부모 제외) 자체 정합 `EmbeddedChunkSet`(`sparse_bm25` 슬롯, `lite`)."""
    data: dict[str, Any] = {
        "schema_version": "1.0.0",
        "schema_type": "EmbeddedChunkSet",
        "tenant_id": TENANT,
        "collection_id": COLLECTION,
        "producer": {
            "plugin_id": "embedder.inprocess_fake",
            "plugin_version": "0.1.0",
            "config_hash": _hex64("embed-config"),
            "image_digest": None,
            "model_ids": None,
        },
        "quality": "full",
        "warnings": [],
        "created_at": "2026-09-22T09:13:05.000Z",
        "lineage_refs": {
            "source": _artifact_ref(
                "source-document", media_type="application/vnd.rag.source-document+json", schema_type="SourceDocument"
            ),
            "parsed": _artifact_ref(
                "parsed-document", media_type="application/vnd.rag.parsed-document+json", schema_type="ParsedDocument"
            ),
            "normalized": _artifact_ref(
                "normalized-document",
                media_type="application/vnd.rag.normalized-document+json",
                schema_type="NormalizedDocument",
            ),
            "chunk_set": _artifact_ref(
                "chunk-set", media_type="application/vnd.rag.chunk-set+json", schema_type="ChunkSet"
            ),
            "enriched": _artifact_ref(
                "enriched-chunk-set",
                media_type="application/vnd.rag.enriched-chunk-set+json",
                schema_type="EnrichedChunkSet",
            ),
        },
        "chunk_set_id": CHUNK_SET_ID,
        "document_id": DOCUMENT,
        "doc_version": DOC_VERSION,
        "enriched_ref": _artifact_ref(
            "enriched-chunk-set",
            media_type="application/vnd.rag.enriched-chunk-set+json",
            schema_type="EnrichedChunkSet",
        ),
        "embedding_space_ids": {"dense": _hex64("space-dense"), "sparse_bm25": _hex64("space-sparse-bm25")},
        "embedding_profile_hash": _hex64("profile"),
        "embedder_fingerprint": _hex64("embedder-fp"),
        "mode": "document",
        "pooling": "cls",
        "vectors_ref": {
            "uri": f"s3://rag-artifacts/tenants/{TENANT}/derived/vectors/{_hex64('vectors')}.npz",
            "blake3": _hex64("vectors"),
            "media_type": "application/x-npz",
            "size_bytes": 4096,
        },
        "vectors": {
            LEAF1: {
                "dense": {"name": "dense", "dim": 4, "offset": 0},
                "sparse_bm25": {
                    "name": "sparse_bm25",
                    "vocab_id": "mecab-ko:1.3.7:ko-dic-2.1.1",
                    "indices": [1, 5, 9],
                    "values": [0.5, 0.3, 0.2],
                },
                "embed_text_hash": _hex64("embed-text-leaf1"),
                "truncated": False,
            },
            LEAF2: {
                "dense": {"name": "dense", "dim": 4, "offset": 1},
                "sparse_bm25": {
                    "name": "sparse_bm25",
                    "vocab_id": "mecab-ko:1.3.7:ko-dic-2.1.1",
                    "indices": [2, 6, 10],
                    "values": [0.4, 0.35, 0.25],
                },
                "embed_text_hash": _hex64("embed-text-leaf2"),
                "truncated": False,
            },
        },
        "cache_hits": 0,
        "stats": {"vectors_total": 2, "bytes_dense": 32, "bytes_sparse": 24, "bytes_late_interaction": 0},
    }
    return EmbeddedChunkSet.model_validate(data)


def make_lineage() -> IndexLineage:
    """`resolve_lineage`가 만드는 것과 같은 모양의 `IndexLineage`(직접 조립, `ctx` 없이)."""
    return IndexLineage(chunk_set=make_chunk_set(), enriched=make_enriched_chunk_set(), source=make_source_document())


DENSE_VECTORS = {LEAF1: _unit([1.0, 0.0, 0.0, 0.0]), LEAF2: _unit([0.0, 1.0, 0.0, 0.0])}


def _embedded_ref() -> dict[str, Any]:
    return _artifact_ref(
        "embedded-chunk-set", media_type="application/vnd.rag.embedded-chunk-set+json", schema_type="EmbeddedChunkSet"
    )


# --- build_index_records ---------------------------------------------------------------------


def test_build_index_records_assembles_leaves_only() -> None:
    embedded = make_embedded_chunk_set()
    lineage = make_lineage()
    records = build_index_records(embedded, lineage, DENSE_VECTORS, commit_id=JOB_ID, index_generation=1, now=NOW)
    assert {r.chunk_id.root for r in records} == {LEAF1, LEAF2}
    assert all(r.is_current is False for r in records)
    assert all(r.index_generation == 1 for r in records)

    leaf = next(r for r in records if r.chunk_id.root == LEAF1)
    expected_rid = record_id_of(TENANT, COLLECTION, DOCUMENT, 1, LEAF1)
    assert leaf.record_id.root == expected_rid
    assert leaf.point_id.root == str(point_id_for_record(expected_rid))
    assert leaf.title == "공공기관 정보보호 업무 지침(행정안전부고시 제2026-12호)"
    assert leaf.tags is not None
    assert [t.root for t in leaf.tags] == ["정보보호", "고시", "공공기관"]
    assert leaf.custom is not None
    custom = {k: (v.root if hasattr(v, "root") else v) for k, v in leaf.custom.items()}
    assert custom == {"notice_no": "2026-12", "in_force": True}
    assert [p.root for p in leaf.acl_allow] == ["group:mois_records", "group:mois_infosec"]
    assert leaf.acl_deny == []
    assert leaf.acl_classification.value == "internal"
    assert leaf.lexical_terms is not None
    assert [t.root for t in leaf.lexical_terms] == sorted({"정보보호", "책임자"})  # dedup
    assert leaf.entity_ids is not None
    assert [e.root for e in leaf.entity_ids] == ["law:개인정보보호법"]  # None canonical_id dropped
    assert leaf.chunk_set_blake3.root == _hex64("chunk-set")
    assert leaf.parent_chunk_id is not None
    assert leaf.parent_chunk_id.root == PARENT
    assert leaf.text == LEAF1_TEXT
    assert leaf.text_truncated is False


def test_acl_classification_defaults_to_internal_when_absent() -> None:
    lineage = make_lineage()
    lineage.source.acl.classification = None
    embedded = make_embedded_chunk_set()
    records = build_index_records(embedded, lineage, DENSE_VECTORS, commit_id=JOB_ID, index_generation=1, now=NOW)
    assert all(r.acl_classification.value == "internal" for r in records)


_SENTENCE_UNIT = "abcdefghij. "  # 10 ASCII chars of content + ". " separator, 12 bytes/chars total
_SENTENCE_COUNT = 700  # 700 * 12 = 8,400 bytes, comfortably over the 8,192 budget


def test_text_truncation_clips_block_refs_and_sentence_spans() -> None:
    long_text = _SENTENCE_UNIT * _SENTENCE_COUNT
    sentence_spans = [[i * 12, i * 12 + 10] for i in range(_SENTENCE_COUNT)]  # spans exclude ". "
    expected_boundary = max(end for _, end in sentence_spans if end <= 8192)

    chunk_set = make_chunk_set()
    chunk = next(c for c in chunk_set.chunks if c.chunk_id.root == LEAF1)
    chunk.text = long_text
    chunk.block_refs = [
        chunk.block_refs[0].model_copy(update={"char_end": len(long_text), "original_char_end": len(long_text)})
    ]
    chunk.sentence_spans = [SentenceSpan1.model_validate(span) for span in sentence_spans]

    lineage = IndexLineage(chunk_set=chunk_set, enriched=make_enriched_chunk_set(), source=make_source_document())
    embedded = make_embedded_chunk_set()
    records = build_index_records(embedded, lineage, DENSE_VECTORS, commit_id=JOB_ID, index_generation=1, now=NOW)
    leaf = next(r for r in records if r.chunk_id.root == LEAF1)

    assert leaf.text_truncated is True
    assert len(leaf.text) == expected_boundary
    assert len(leaf.text.encode("utf-8")) <= 8192
    assert leaf.block_refs[-1].char_end == expected_boundary
    assert leaf.block_refs[-1].original_char_end == len(long_text)  # original coordinates untouched
    assert leaf.sentence_spans[-1].root[1].root == expected_boundary


def test_commit_hash_is_deterministic_and_input_only() -> None:
    embedded = make_embedded_chunk_set()
    lineage = make_lineage()
    commit_id_a = "01JAB3D0E1F2G3H4J5K6M7N8P9"
    commit_id_b = "01JAB3D0E1F2G3H4J5K6M7N8PA"
    records_a = build_index_records(
        embedded, lineage, DENSE_VECTORS, commit_id=commit_id_a, index_generation=1, now=NOW
    )
    records_b = build_index_records(
        embedded, lineage, DENSE_VECTORS, commit_id=commit_id_b, index_generation=7, now=NOW
    )
    hash_a = commit_hash_of(records_a, embedded, profile_hash=_hex64("profile"))
    hash_b = commit_hash_of(records_b, embedded, profile_hash=_hex64("profile"))
    assert hash_a == hash_b  # commit_id/generation-independent (bible sec. 5.4)
    assert [r.record_id.root for r in records_a] != [r.record_id.root for r in records_b]  # generation differs


# --- resolve_lineage ---------------------------------------------------------------------------


class _FakeCtx:
    def __init__(self, lineage: dict[str, Any]) -> None:
        self.lineage = lineage


def test_resolve_lineage_reads_ctx_lineage_by_schema_type() -> None:
    chunk_set = make_chunk_set()
    enriched = make_enriched_chunk_set()
    source = make_source_document()
    ctx = _FakeCtx({"ChunkSet": chunk_set, "EnrichedChunkSet": enriched, "SourceDocument": source})
    lineage = resolve_lineage(ctx)
    assert lineage.chunk_set is chunk_set
    assert lineage.enriched is enriched
    assert lineage.source is source


def test_resolve_lineage_missing_key_is_contract_violation() -> None:
    ctx = _FakeCtx({"ChunkSet": make_chunk_set()})
    with pytest.raises(StageError) as exc:
        resolve_lineage(ctx)
    assert exc.value.code == "contract.violation"


# --- IndexSaga: happy path, idempotent re-run --------------------------------------------------


@pytest.fixture
def backend() -> QdrantIndexBackend:
    return QdrantIndexBackend.local()


@pytest.fixture
def ledger() -> InMemoryLedger:
    return InMemoryLedger()


async def _commit(
    backend: QdrantIndexBackend,
    ledger: InMemoryLedger,
    *,
    commit_id: str | None = None,
    saga: IndexSaga | None = None,
) -> Any:
    saga = saga or IndexSaga(backend=backend, ledger=ledger)
    return await saga.commit(
        make_embedded_chunk_set(),
        make_lineage(),
        dense_vectors=DENSE_VECTORS,
        embedded_ref=_embedded_ref_model(),
        job_id=JOB_ID,
        profile_id="lite",
        profile_hash=_hex64("profile"),
        now=NOW,
        commit_id=commit_id,
    )


def _embedded_ref_model() -> Any:
    return ArtifactRef.model_validate(_embedded_ref())


async def test_saga_commit_flips_records_visible_and_advances_ledger(
    backend: QdrantIndexBackend, ledger: InMemoryLedger
) -> None:
    commit = await _commit(backend, ledger)
    assert commit.status.value == "committed"
    assert commit.index_generation == 1
    assert commit.record_count == 2
    assert len(commit.backend_results) == 1
    assert commit.backend_results[0].status.value == "ok"

    physical = physical_collection_name(_hex64("profile"))
    flt = scope_filter(TENANT, collection_id=COLLECTION, document_id=DOCUMENT, is_current=True)
    assert backend.count(physical, flt) == 2

    doc = await ledger.get_document(TENANT, DOCUMENT)
    assert doc is not None
    assert doc.current_generation == 1
    assert doc.current_commit_id == commit.commit_id.root


async def test_rerun_same_commit_id_is_deterministic_and_noop(
    backend: QdrantIndexBackend, ledger: InMemoryLedger
) -> None:
    saga = IndexSaga(backend=backend, ledger=ledger)
    first = await _commit(backend, ledger, commit_id=JOB_ID, saga=saga)
    second = await _commit(backend, ledger, commit_id=JOB_ID, saga=saga)
    assert first is second  # process-local cache no-op (bible sec. 4.2 "same commit_id -> no-op")
    assert first.commit_hash == second.commit_hash
    physical = physical_collection_name(_hex64("profile"))
    flt = scope_filter(TENANT, collection_id=COLLECTION, document_id=DOCUMENT, is_current=True)
    assert backend.count(physical, flt) == 2  # not doubled


async def test_build_index_records_reruns_yield_same_record_ids(
    backend: QdrantIndexBackend, ledger: InMemoryLedger
) -> None:
    embedded = make_embedded_chunk_set()
    lineage = make_lineage()
    first = build_index_records(embedded, lineage, DENSE_VECTORS, commit_id=JOB_ID, index_generation=1, now=NOW)
    second = build_index_records(embedded, lineage, DENSE_VECTORS, commit_id=JOB_ID, index_generation=1, now=NOW)
    assert [r.record_id.root for r in first] == [r.record_id.root for r in second]
    assert commit_hash_of(first, embedded, profile_hash=_hex64("profile")) == commit_hash_of(
        second, embedded, profile_hash=_hex64("profile")
    )


# --- IndexSaga: rollback -----------------------------------------------------------------------


class _FailingUpsertBackend:
    """`upsert`가 항상 실패하는 페이크(플립 전 실패 경로)."""

    def __init__(self, inner: QdrantIndexBackend) -> None:
        self._inner = inner
        self.backend_version = inner.backend_version

    def ensure_collection(self, *args: Any, **kwargs: Any) -> bool:
        return self._inner.ensure_collection(*args, **kwargs)

    def upsert(self, *args: Any, **kwargs: Any) -> int:
        code = "index.backend_unavailable"
        raise StageError(code, stage="index", plugin_id="index_backend.qdrant", detail="down")

    def set_current(self, *args: Any, **kwargs: Any) -> None:
        self._inner.set_current(*args, **kwargs)

    def delete(self, *args: Any, **kwargs: Any) -> None:
        self._inner.delete(*args, **kwargs)

    def count(self, *args: Any, **kwargs: Any) -> int:
        return self._inner.count(*args, **kwargs)


class _FailingFlipBackend:
    """두 번째 세대의 `set_current`만 실패하는 페이크(플립 후 실패 경로)."""

    def __init__(self, inner: QdrantIndexBackend) -> None:
        self._inner = inner
        self.backend_version = inner.backend_version
        self.calls = 0

    def ensure_collection(self, *args: Any, **kwargs: Any) -> bool:
        return self._inner.ensure_collection(*args, **kwargs)

    def upsert(self, *args: Any, **kwargs: Any) -> int:
        return self._inner.upsert(*args, **kwargs)

    def set_current(self, *args: Any, **kwargs: Any) -> None:
        self.calls += 1
        if kwargs.get("index_generation") == 2 and self.calls == 1:
            code = "index.backend_unavailable"
            raise StageError(code, stage="index", plugin_id="index_backend.qdrant", detail="flip down")
        self._inner.set_current(*args, **kwargs)

    def delete(self, *args: Any, **kwargs: Any) -> None:
        self._inner.delete(*args, **kwargs)

    def count(self, *args: Any, **kwargs: Any) -> int:
        return self._inner.count(*args, **kwargs)


async def test_rollback_before_flip_deletes_only_new_generation(
    backend: QdrantIndexBackend, ledger: InMemoryLedger
) -> None:
    failing = _FailingUpsertBackend(backend)
    saga = IndexSaga(backend=failing, ledger=ledger)
    commit = await saga.commit(
        make_embedded_chunk_set(),
        make_lineage(),
        dense_vectors=DENSE_VECTORS,
        embedded_ref=_embedded_ref_model(),
        job_id=JOB_ID,
        profile_id="lite",
        profile_hash=_hex64("profile"),
        now=NOW,
    )
    assert commit.status.value == "rolled_back"
    assert commit.compensation is not None
    assert commit.compensation.restored_generation is None
    physical = physical_collection_name(_hex64("profile"))
    assert backend.count(physical, scope_filter(TENANT, collection_id=COLLECTION, document_id=DOCUMENT)) == 0


async def test_rollback_after_flip_restores_previous_generation(
    backend: QdrantIndexBackend, ledger: InMemoryLedger
) -> None:
    first = await _commit(backend, ledger)
    assert first.status.value == "committed"

    failing = _FailingFlipBackend(backend)
    saga = IndexSaga(backend=failing, ledger=ledger)
    second = await saga.commit(
        make_embedded_chunk_set(),
        make_lineage(),
        dense_vectors=DENSE_VECTORS,
        embedded_ref=_embedded_ref_model(),
        job_id=JOB_ID,
        profile_id="lite",
        profile_hash=_hex64("profile"),
        now=NOW,
    )
    assert second.status.value == "rolled_back"
    assert second.compensation is not None
    assert second.compensation.restored_generation == 1

    physical = physical_collection_name(_hex64("profile"))
    current = scope_filter(TENANT, collection_id=COLLECTION, document_id=DOCUMENT, is_current=True)
    assert backend.count(physical, current) == 2  # generation 1 restored, visible again
    gen2 = scope_filter(TENANT, collection_id=COLLECTION, document_id=DOCUMENT, index_generation=2)
    assert backend.count(physical, gen2) == 0  # generation 2 deleted


async def test_generation_after_rollback_is_not_reused(backend: QdrantIndexBackend, ledger: InMemoryLedger) -> None:
    """`Ledger.list_commits`의 max(index_generation)+1 할당 — 롤백된 세대 번호를 다음 커밋이 재사용하지 않는다.

    `contracts/index_commit.py`의 "documents 행 FOR UPDATE 잠금 아래 그 문서의
    max(index_commits.index_generation) + 1로 할당(current_generation + 1 아님; 롤백·폐기된 세대
    번호 재사용 없음)" 정의를 검증(F3 배치 검증 open_issue 해소).
    """
    failing = _FailingUpsertBackend(backend)
    rolled_back = await IndexSaga(backend=failing, ledger=ledger).commit(
        make_embedded_chunk_set(),
        make_lineage(),
        dense_vectors=DENSE_VECTORS,
        embedded_ref=_embedded_ref_model(),
        job_id=JOB_ID,
        profile_id="lite",
        profile_hash=_hex64("profile"),
        now=NOW,
    )
    assert rolled_back.status.value == "rolled_back"
    assert rolled_back.index_generation == 1  # documents row still has no committed generation

    committed = await _commit(backend, ledger)
    assert committed.status.value == "committed"
    assert committed.index_generation == 2  # not 1 again: generation 1 was rolled back, not reused


# --- IndexStage smoke ---------------------------------------------------------------------------


def test_index_stage_capabilities_and_fingerprint_are_stable() -> None:
    stage = IndexStage(saga=None)
    caps = stage.capabilities()
    assert caps.isolation_modes[0].value == "in_process"
    assert stage.fingerprint() == stage.fingerprint()
    assert stage.requires_lineage == ("ChunkSet", "EnrichedChunkSet", "SourceDocument")
