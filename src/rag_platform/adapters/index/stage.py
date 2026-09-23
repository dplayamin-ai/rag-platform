"""`index` 스테이지 — `EmbeddedChunkSet`(+`requires_lineage`)을 `IndexRecord[]`로 조립한다.

역할: `EmbeddedChunkSet.vectors`의 각 `chunk_id`(level ∈ {0, 2})마다 `ChunkSet`(CS)·
`EnrichedChunkSet`(ENR)·`SourceDocument`(SRC)·`EmbeddedChunkSet`(EMB)·사가 인자(IDX)에서 값을 모아
`IndexRecord`를 만드는 순수 조립 로직과, 이를 감싼 5멤버 `Stage` 프로토콜(`IndexStage`)을 담는다.
설계 근거: 바이블 §4.2 `index` 행("원천"은 §5.4 `IndexRecord` 표 열), §5.4 `IndexRecord`/
`IndexCommit` 표, §11.4 세대 사가, ADR-0026, 04-pipelines/13 §3(조립·검증 순서), ADR-0004(`record_id`/
`point_id` 단일 구현).
구성: `IndexLineage` — `requires_lineage` 3종을 묶은 dataclass; `resolve_lineage(ctx)` — `ctx.lineage`
읽기(`fsspec_httpx.py`의 `ctx.lineage["SourceDocument"]` 관례와 동일); `build_index_records(...)` —
핵심 변환(순수 함수, I/O 없음); `commit_hash_of(...)` — 커밋 재현성 해시; `IndexStage` — `Stage`
프로토콜(`plugin_id="index_backend.pipeline"`), 실행은 `IndexSaga`(`saga.py`)에 위임.
불변식: `record_id`/`point_id`는 `sdk.hashing`만 호출(재구현 금지). 조립된 레코드는 항상
`is_current=false`(플립은 백엔드가 한다). `text`가 8,192 UTF-8 바이트를 넘으면 문장 경계에서 절단하고
`block_refs`/`sentence_spans`를 그 경계로 재계산한다(단순화 버전, WP 문서 DEFERRED 참조). 어댑터는
`storage`를 모르므로 `vectors_ref`(npz) 실물 배열은 `dense_vectors` 인자로 이미 역참조된 값을 받는다.
검증 계층: 1층(여기서 검증) — `tests/adapters/index/test_index_commit.py`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict, RootModel

from rag_platform.contracts import common_types as ct
from rag_platform.contracts.chunk_set import ChunkSet
from rag_platform.contracts.enriched_chunk_set import EnrichedChunkSet
from rag_platform.contracts.index_record import IndexRecord
from rag_platform.contracts.source_document import SourceDocument
from rag_platform.sdk.hashing import hash_of, point_id_for_record, record_id as record_id_of
from rag_platform.sdk.stage import StageError

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from datetime import datetime

    from rag_platform.contracts.embedded_chunk_set import EmbeddedChunkSet

__all__ = [
    "PLUGIN_VERSION",
    "IndexLineage",
    "IndexStage",
    "IndexStageConfig",
    "build_index_records",
    "commit_hash_of",
    "resolve_lineage",
    "rfc3339_ms",
]

PLUGIN_VERSION = "0.1.0"
PLUGIN_ID = "index_backend.pipeline"

_CONTRACT_VIOLATION = "contract.violation"
#: 04-pipelines/13 §3 step 5 / ADR-0034: payload `text`는 8,192 UTF-8 바이트를 넘지 않는다.
_MAX_TEXT_BYTES = 8192
#: IndexRecord.text_preview 상한(바이블 §5.4).
_MAX_PREVIEW_CHARS = 200
#: IndexRecord.title 상한(바이블 §5.4 대체 순서).
_MAX_TITLE_CHARS = 512

_REQUIRED_LINEAGE = ("ChunkSet", "EnrichedChunkSet", "SourceDocument")


@dataclass(frozen=True, slots=True)
class IndexLineage:
    """`index`의 `requires_lineage` 3종(바이블 §4.2 index 행)을 한데 묶은 자리표."""

    chunk_set: ChunkSet
    enriched: EnrichedChunkSet
    source: SourceDocument


def _violation(detail: str) -> StageError:
    return StageError(_CONTRACT_VIOLATION, stage="index", plugin_id=PLUGIN_ID, detail=detail)


def _from_lineage(lineage_map: Mapping[str, Any], key: str, model: type[Any]) -> Any:
    value = lineage_map.get(key)
    if value is None:
        detail = f"ctx.lineage[{key!r}] missing (index requires_lineage: {_REQUIRED_LINEAGE})"
        raise _violation(detail)
    if isinstance(value, model):
        return value
    if hasattr(value, "model_dump"):
        return model.model_validate(value.model_dump(mode="json"))
    return model.model_validate(value)


def resolve_lineage(ctx: Any, *, plugin_id: str = PLUGIN_ID) -> IndexLineage:
    """`ctx.lineage`에서 `ChunkSet`/`EnrichedChunkSet`/`SourceDocument`를 읽어 `IndexLineage`로 감싼다.

    `fsspec_httpx.py`의 `ctx.lineage["SourceDocument"]` 관례(문자열 `schema_type` 키)를 그대로
    따른다. 셋 중 하나라도 없거나 대상 계약으로 검증되지 않으면 `contract.violation`.
    """
    lineage_map = getattr(ctx, "lineage", None)
    if not lineage_map:
        detail = f"ctx.lineage empty; index requires_lineage={_REQUIRED_LINEAGE}"
        raise StageError(_CONTRACT_VIOLATION, stage="index", plugin_id=plugin_id, detail=detail)
    return IndexLineage(
        chunk_set=_from_lineage(lineage_map, "ChunkSet", ChunkSet),
        enriched=_from_lineage(lineage_map, "EnrichedChunkSet", EnrichedChunkSet),
        source=_from_lineage(lineage_map, "SourceDocument", SourceDocument),
    )


def rfc3339_ms(moment: datetime) -> str:
    """`common_types.DateTime` 패턴(`...Z`, 밀리초 3자리)에 맞춘 RFC 3339 문자열(UTC로 변환)."""
    utc = moment.astimezone(UTC)
    return utc.strftime("%Y-%m-%dT%H:%M:%S.") + f"{utc.microsecond // 1000:03d}Z"


def _utf8_len(text: str) -> int:
    return len(text.encode("utf-8"))


def _max_codepoints_within_budget(text: str, budget: int) -> int:
    """Return the largest prefix length (code points) whose UTF-8 encoding fits `budget` bytes."""
    total = 0
    for index, char in enumerate(text):
        total += len(char.encode("utf-8"))
        if total > budget:
            return index
    return len(text)


def _truncate_text(
    text: str,
    block_refs: list[dict[str, Any]],
    sentence_spans: list[list[int]],
) -> tuple[str, list[dict[str, Any]], list[list[int]], bool]:
    """04-pipelines/13 §3 step 5 / 07 §9 단순화판: 마지막 완결 문장 경계에서 절단.

    블록 경계 우선 규칙의 축소판이다 — 마지막 `block_refs` 항목만 `char_end`를 절단 경계로
    클리핑하고(`original_char_*`는 불변), 경계를 넘는 항목은 제거한다. 전수 코너 케이스는 이 WP
    범위 밖(WP 문서 DEFERRED).
    """
    if _utf8_len(text) <= _MAX_TEXT_BYTES:
        return text, block_refs, sentence_spans, False
    cutoff = _max_codepoints_within_budget(text, _MAX_TEXT_BYTES)
    boundary = 0
    for _start, end in sentence_spans:
        if end <= cutoff:
            boundary = max(boundary, end)
        else:
            break
    if boundary == 0:
        boundary = cutoff
    new_text = text[:boundary]
    new_spans = [span for span in sentence_spans if span[1] <= boundary]
    new_refs: list[dict[str, Any]] = []
    for ref in block_refs:
        if ref["char_start"] >= boundary:
            continue
        clipped = dict(ref)
        clipped["char_end"] = min(clipped["char_end"], boundary)
        new_refs.append(clipped)
    return new_text, new_refs, new_spans, True


def _title_for(source: SourceDocument, chunk_set: ChunkSet) -> str:
    """바이블 §5.4 대체 순서(축소: `ParsedDocument.metadata.title`은 `requires_lineage` 밖).

    `IngestMetadata.title`(= `SourceDocument.metadata.title`) → 첫 `heading level 0` 텍스트 →
    `source_uri` 마지막 경로 요소, 512자 절단.
    """
    if source.metadata.title:
        return source.metadata.title[:_MAX_TITLE_CHARS]
    for chunk in chunk_set.chunks:
        if chunk.heading_path:
            return chunk.heading_path[0][:_MAX_TITLE_CHARS]
    tail = str(source.source_uri).rstrip("/").rsplit("/", 1)[-1]
    return tail[:_MAX_TITLE_CHARS]


def _page_bounds(block_refs: list[dict[str, Any]]) -> tuple[int | None, int | None]:
    pages = [ref["page"] for ref in block_refs if ref.get("page") is not None]
    if not pages:
        return None, None
    return min(pages), max(pages)


def build_index_records(
    embedded: EmbeddedChunkSet,
    lineage: IndexLineage,
    dense_vectors: Mapping[str, Sequence[float]],
    *,
    commit_id: str,
    index_generation: int,
    now: datetime,
) -> list[IndexRecord]:
    """`EmbeddedChunkSet.vectors`의 각 `chunk_id`를 `IndexRecord`로 조립한다(순수 함수).

    Args:
        embedded: `index` 입력(EMB).
        lineage: `requires_lineage`로 읽은 `ChunkSet`(CS)/`EnrichedChunkSet`(ENR)/
            `SourceDocument`(SRC).
        dense_vectors: `chunk_id -> dense 벡터`(이미 `vectors_ref`에서 역참조된 값; 셸 책임).
        commit_id: 이 사가가 발급한 커밋 ID(IDX).
        index_generation: 이 사가가 할당한 세대(IDX).
        now: 레코드 `updated_at`(주입된 시각; 여기서 `datetime.now()`를 호출하지 않는다).

    Returns:
        `chunk_id` 오름차순이 아니라 `embedded.vectors`(삽입 순서 = 결정적) 순서의 `IndexRecord` 목록.

    Raises:
        StageError: `contract.violation` — 청크/보강/밀집 벡터 중 하나라도 대응 항목이 없을 때.
    """
    chunk_by_id = {chunk.chunk_id.root: chunk for chunk in lineage.chunk_set.chunks}
    tenant_id = str(embedded.tenant_id.root)
    collection_id = str(embedded.collection_id.root)
    document_id = str(embedded.document_id.root)
    doc_version = str(lineage.source.doc_version.root)
    acl = lineage.source.acl
    title = _title_for(lineage.source, lineage.chunk_set)
    chunk_set_blake3 = str(embedded.lineage_refs.chunk_set.blake3.root)

    records: list[IndexRecord] = []
    for chunk_id, bundle in embedded.vectors.items():
        chunk = chunk_by_id.get(chunk_id)
        if chunk is None:
            detail = f"chunk_id {chunk_id!r} in EmbeddedChunkSet.vectors missing from ChunkSet.chunks"
            raise _violation(detail)
        enrichment = lineage.enriched.enrichments.get(chunk_id)
        if enrichment is None:
            detail = f"chunk_id {chunk_id!r} missing from EnrichedChunkSet.enrichments"
            raise _violation(detail)
        dense = dense_vectors.get(chunk_id)
        vector = bundle.root
        if dense is None:
            detail = f"chunk_id {chunk_id!r} missing from dense_vectors"
            raise _violation(detail)

        block_refs = [ref.model_dump(mode="json") for ref in chunk.block_refs]
        sentence_spans = [[span.root[0].root, span.root[1].root] for span in chunk.sentence_spans]
        text, block_refs, sentence_spans, truncated = _truncate_text(chunk.text, block_refs, sentence_spans)
        page_start, page_end = _page_bounds(block_refs)

        vectors: dict[str, Any] = {"dense": list(dense)}
        if vector.sparse_learned is not None:
            vectors["sparse_learned"] = {
                "indices": [i.root for i in vector.sparse_learned.indices],
                "values": list(vector.sparse_learned.values),
            }
        if vector.sparse_bm25 is not None:
            vectors["sparse_bm25"] = {
                "indices": [i.root for i in vector.sparse_bm25.indices],
                "values": list(vector.sparse_bm25.values),
            }

        table_ref = chunk.table_ref.model_dump(mode="json") if chunk.table_ref is not None else None
        html_ref = chunk.table_ref.html_ref if chunk.table_ref is not None else None

        rid = record_id_of(tenant_id, collection_id, document_id, index_generation, chunk_id)
        entity_ids = sorted({e.canonical_id for e in enrichment.entities if e.canonical_id})
        token_counts = chunk.token_counts.root
        token_count_primary = token_counts[lineage.chunk_set.primary_tokenizer_id.root].root
        custom = {
            key: (value.root if isinstance(value, RootModel) else value)
            for key, value in (lineage.source.metadata.custom or {}).items()
        } or None

        payload: dict[str, Any] = {
            "record_id": rid,
            "point_id": str(point_id_for_record(rid)),
            "chunk_id": chunk_id,
            "tenant_id": tenant_id,
            "collection_id": collection_id,
            "document_id": document_id,
            "doc_version": doc_version,
            "commit_id": commit_id,
            "index_generation": index_generation,
            "is_current": False,
            "item_kind": chunk.item_kind.value,
            "level": int(chunk.level),
            "parent_chunk_id": chunk.parent_chunk_id.root if chunk.parent_chunk_id else None,
            "ordinal": chunk.ordinal,
            "tree_level": chunk.tree_level,
            "vectors": vectors,
            "index_text": enrichment.index_text,
            "lexical_terms": sorted({kw.term for kw in enrichment.keywords}),
            "text": text,
            "text_preview": text[:_MAX_PREVIEW_CHARS],
            "text_truncated": truncated,
            "context_prefix": chunk.context_prefix.deterministic,
            "block_refs": block_refs,
            "sentence_spans": sentence_spans,
            "table_ref": table_ref,
            "html_ref": html_ref.model_dump(mode="json") if html_ref is not None else None,
            "title": title,
            "heading_path": list(chunk.heading_path),
            "numbering_path": list(chunk.numbering_path or []),
            "source_uri": str(lineage.source.source_uri),
            "external_id": lineage.source.external_id,
            "doc_date": lineage.source.metadata.doc_date.root if lineage.source.metadata.doc_date else None,
            "doc_type": lineage.source.metadata.doc_type,
            "department": lineage.source.metadata.department,
            "tags": (
                [t.root for t in lineage.source.metadata.tags] if lineage.source.metadata.tags is not None else None
            ),
            "lang": chunk.lang.root,
            "genre": lineage.chunk_set.genre_route.value,
            "custom": custom,
            "page_start": page_start,
            "page_end": page_end,
            "text_source": chunk.text_source.value,
            "ocr_confidence_min": chunk.ocr_confidence_min,
            "acl_allow": [p.root for p in acl.allow_principals],
            "acl_deny": [p.root for p in acl.deny_principals] if acl.deny_principals is not None else None,
            "acl_visibility": acl.visibility.value,
            "acl_classification": (acl.classification or ct.Classification.internal).value,
            "acl_embargo_until": acl.embargo_until.root if acl.embargo_until else None,
            "acl_expires_at": acl.expires_at.root if acl.expires_at else None,
            "acl_hash": str(lineage.source.acl_hash.root),
            "entity_ids": entity_ids or None,
            "content_hash": str(chunk.content_hash.root),
            "token_count_primary": token_count_primary,
            "risk_score": enrichment.risk_score,
            "pii_policy_applied": lineage.chunk_set.pii_policy_applied.value,
            "embedding_space_ids": embedded.embedding_space_ids.model_dump(mode="json"),
            "embedding_profile_hash": str(embedded.embedding_profile_hash.root),
            "analyzer_id": str(lineage.chunk_set.analyzer_id.root),
            "dictionary_hash": str(lineage.chunk_set.dictionary_hash.root),
            "chunk_set_blake3": chunk_set_blake3,
            "updated_at": rfc3339_ms(now),
        }
        records.append(IndexRecord.model_validate(payload))
    return records


def commit_hash_of(records: Sequence[IndexRecord], embedded: EmbeddedChunkSet, *, profile_hash: str) -> str:
    """`H("commit", profile_hash, *sorted(f"{chunk_id}:{content_hash}:{embed_text_hash}"))`(바이블 §5.4).

    `commit_id`·세대·시각과 무관해 재실행 멱등성(같은 입력 → 같은 값)을 만든다.
    """
    parts = []
    for record in records:
        bundle = embedded.vectors[record.chunk_id.root].root
        parts.append(f"{record.chunk_id.root}:{record.content_hash.root}:{bundle.embed_text_hash.root}")
    return hash_of("commit", profile_hash, *sorted(parts))


class IndexStageConfig(BaseModel):
    """`index_backend.pipeline`의 설정 스키마 — 조정 가능한 필드 없음(백엔드·원장은 생성자 주입)."""

    model_config = ConfigDict(extra="forbid")


class IndexStage:
    """`index_backend.pipeline` — `Stage` 프로토콜(ADR-0032 5멤버); 실행은 `IndexSaga`에 위임한다.

    `saga`는 생성자로 주입한다(백엔드·원장은 `StageContext` 표면이 아니다 — `sdk.ports` docstring과
    같은 이유). `run()`은 `resolve_lineage(ctx)` 후 `ctx`가 제공하는 나머지 사가 인자(`dense_vectors`,
    `embedded_ref`, `job_id`, `profile_id`, `profile_hash`, `commit_id`)를 읽어 `saga.commit(...)`을
    호출한다 — 이 인자들을 위한 `StageContext` 관례는 아직 없다(WP 문서 DEFERRED, `structure_aware.py`
    `_resolve_normalized_ref`와 같은 공백).
    """

    plugin_id = PLUGIN_ID
    config_schema = IndexStageConfig
    requires_lineage: tuple[str, ...] = _REQUIRED_LINEAGE

    def __init__(self, saga: Any, config: IndexStageConfig | None = None) -> None:
        """`saga`(`saga.IndexSaga`)를 고정한다; `config`는 조정 가능한 값이 없어 항상 비어 있다."""
        self.saga = saga
        self.config = config or IndexStageConfig()

    def config_hash(self) -> str:
        """`H("config", canonical_json(config))`(바이블 §6.2) — 필드가 없어 항상 고정값."""
        canonical = json.dumps(
            self.config.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), ensure_ascii=False
        )
        return hash_of("config", canonical)

    def capabilities(self) -> ct.Capabilities:
        """`isolation_modes=[in_process]`, 재개 미지원(사가 보상이 실패 처리를 대신함)."""
        return ct.Capabilities(
            isolation_modes=[ct.IsolationMode.in_process],
            supports_resumable=False,
            contracts_compat=ct.ContractsCompat(">=1.0,<2.0"),
            input_formats=[],
            requires_gpu=False,
            extra={"backend_role": "vector"},
        )

    def fingerprint(self) -> str:
        """`H("producer", plugin_id, plugin_version, config_hash, "", "")`(모델 없음)."""
        return hash_of("producer", self.plugin_id, PLUGIN_VERSION, self.config_hash(), "", "")

    async def run(self, inp: EmbeddedChunkSet, ctx: Any) -> Any:
        """`EmbeddedChunkSet` → `IndexCommit`; 조립은 `build_index_records`, 사가는 `self.saga`."""
        lineage = resolve_lineage(ctx, plugin_id=self.plugin_id)
        dense_vectors = getattr(ctx, "dense_vectors", None) or {}
        embedded_ref = getattr(ctx, "embedded_ref", None)
        if embedded_ref is None:
            detail = "ctx.embedded_ref missing (no StageContext convention yet, see WP DEFERRED)"
            raise _violation(detail)
        return await self.saga.commit(
            inp,
            lineage,
            dense_vectors=dense_vectors,
            embedded_ref=embedded_ref,
            job_id=getattr(ctx, "job_id", None) or "",
            profile_id=getattr(ctx, "profile_id", None) or "",
            profile_hash=ctx.profile_hash,
            now=ctx.now(),
            commit_id=getattr(ctx, "commit_id", None),
        )
