"""`QdrantIndexBackend` — `IndexRecord`를 Qdrant 컬렉션(named vectors `dense`·`sparse_bm25`)에 적재·검색하는 어댑터.

설계 근거: 04-pipelines/13 §2(포트·능력)·§3(적재 전 검증 순서)·§4.1(컬렉션·payload 인덱스)·§4.2(배치 256,
`wait=True`)·§4.4(검색 호출 형태)·§6(`lite`), 바이블 §13.4(명명: `rag_vec_{hash12}`, alias `col_{collection_id}_vec`),
§11.4(`is_current` 플립), ADR-0012(테넌트 범위 IDF). 계약 타입: `IndexRecord`, `SparseVector`.

구성:
- `physical_collection_name(profile_hash, tenant_id)` / `alias_name(collection_id)` — §13.4 명명
- `CollectionLayout` — 물리 컬렉션의 named vector 구성(차원·sparse 슬롯)
- `QdrantIndexBackend.local(path)` — qdrant-client 로컬 모드(`:memory:` 또는 디렉터리) 생성자
- `ensure_collection` — 생성 + payload 인덱스, 기존이면 차원·거리·벡터 집합·`modifier` 대조(`profile.invalid`)
- `upsert` / `set_current` / `delete` / `count` — 적재(보안 필드·키 검증 후), 세대 플립, 필터 삭제·계수
- `search_dense` / `search_sparse` — 사전 필터 단일 호출(서버 융합 미사용); `sparse_bm25`는 테넌트 코퍼스 IDF
- `swap_alias` / `resolve_alias` — blue/green alias 교체(단일 `update_collection_aliases` 호출)

불변식: 검색은 `assert_search_secured`, 쓰기·계수는 `assert_tenant_scoped`를 통과한 필터만 받는다(E7). 적재
레코드는 `is_current=false`이며 `record_id`/`point_id`를 재계산 대조한다(E17). `index_text`·`vectors`는 payload 제외.
검증 계층: 1층(여기서 검증, 로컬 모드) — `tests/adapters/index/test_qdrant_local.py`.
DEFERRED: 로컬 모드는 payload 인덱스를 무시한다(`is_tenant`·`prefix` 인덱스, HNSW `payload_m` 효과, insert-only 충돌)
— 서버 대상 검증은 `needs_docker`(같은 테스트 파일의 서버 테스트).
"""

from __future__ import annotations

import importlib.metadata
import warnings
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from qdrant_client import QdrantClient, models

from rag_platform.adapters.index.qdrant.bm25_sparse import validate_sparse
from rag_platform.adapters.index.qdrant.filters import (
    assert_search_secured,
    assert_tenant_scoped,
    scope_filter,
)
from rag_platform.adapters.index.qdrant.point_id import verify_record_keys
from rag_platform.sdk.stage import StageError

if TYPE_CHECKING:
    from collections.abc import Sequence

    from rag_platform.contracts.index_record import IndexRecord, SparseVector

__all__ = [
    "DENSE",
    "PAYLOAD_INDEXES",
    "SPARSE_BM25",
    "SPARSE_LEARNED",
    "UPSERT_BATCH_SIZE",
    "CollectionLayout",
    "QdrantIndexBackend",
    "SearchHit",
    "alias_name",
    "physical_collection_name",
]

_CONTRACT_VIOLATION = "contract.violation"
_SECURITY_FIELDS_MISSING = "index.security_fields_missing"
_SPACE_MISMATCH = "embed.space_mismatch"
_PROFILE_INVALID = "profile.invalid"

PLUGIN_ID = "index_backend.qdrant"
DENSE = "dense"
SPARSE_LEARNED = "sparse_learned"
SPARSE_BM25 = "sparse_bm25"
#: Bible §5.1 "upsert 배치 256".
UPSERT_BATCH_SIZE = 256
#: 13 §3 step 3 (E5): a batch with any record lacking one of these is never sent.
SECURITY_FIELDS = ("tenant_id", "collection_id", "acl_allow", "acl_visibility", "acl_hash")
#: Payload never stored in Qdrant: vectors go to named vectors, `index_text` only feeds `sparse_bm25` (13 §3).
_PAYLOAD_EXCLUDE = {"vectors", "index_text"}
_LOCAL_INDEX_WARNING = "Payload indexes have no effect in the local Qdrant"


def _keyword(*, tenant: bool = False, prefix: bool = False, cold: bool = False) -> models.KeywordIndexParams:
    return models.KeywordIndexParams(
        type=models.KeywordIndexType.KEYWORD,
        is_tenant=tenant or None,
        prefix=prefix or None,
        memory=models.Memory.COLD if cold else None,
    )


_INTEGER = models.IntegerIndexParams(type=models.IntegerIndexType.INTEGER, lookup=True, range=True)
# Spike (qdrant-client 1.19.1): DatetimeIndexParams has only is_principal/on_disk/memory/enable_hnsw — no range.
_DATETIME = models.DatetimeIndexParams(type=models.DatetimeIndexType.DATETIME)

#: 13 §4.1 payload index table (bible §13.4 + 04 §4.4 additions). `prefix=True` on user-filterable
#: string keys enables `MatchPrefix` (FilterOp.prefix) on the server.
PAYLOAD_INDEXES: dict[
    str, models.PayloadSchemaType | models.KeywordIndexParams | models.IntegerIndexParams | models.DatetimeIndexParams
] = {
    "tenant_id": _keyword(tenant=True),
    **{
        key: _keyword()
        for key in (
            "collection_id",
            "document_id",
            "chunk_id",
            "commit_id",
            "doc_version",
            "parent_chunk_id",
            "item_kind",
            "acl_visibility",
            "acl_classification",
            "lang",
            "genre",
            "acl_allow",
            "acl_deny",
        )
    },
    **{key: _keyword(prefix=True) for key in ("external_id", "doc_type", "department", "heading_path", "tags")},
    **{key: _keyword(cold=True) for key in ("lexical_terms", "entity_ids")},
    "is_current": models.PayloadSchemaType.BOOL,
    **dict.fromkeys(("index_generation", "level", "tree_level", "page_start", "page_end"), _INTEGER),
    **dict.fromkeys(("acl_embargo_until", "acl_expires_at", "doc_date"), _DATETIME),
}


def physical_collection_name(embedding_profile_hash: str, tenant_id: str | None = None) -> str:
    """Bible §13.4: `rag_vec_{hash[:12]}` (shared) or `rag_vec_{hash12}_t_{tenant_id}` (`index_per_tenant`)."""
    base = f"rag_vec_{embedding_profile_hash[:12]}"
    return f"{base}_t_{tenant_id}" if tenant_id else base


def alias_name(collection_id: str) -> str:
    """Bible §13.4: the blue/green alias `col_{collection_id}_vec`."""
    return f"col_{collection_id}_vec"


@dataclass(frozen=True, slots=True)
class CollectionLayout:
    """Named-vector layout of one physical collection (13 §4.1 table; `lite` default)."""

    dense_dim: int
    sparse_bm25: bool = True
    sparse_learned: bool = False

    def vector_names(self) -> frozenset[str]:
        """Return the named vector set (dense + declared sparse slots)."""
        names = {DENSE}
        if self.sparse_bm25:
            names.add(SPARSE_BM25)
        if self.sparse_learned:
            names.add(SPARSE_LEARNED)
        return frozenset(names)


@dataclass(frozen=True, slots=True)
class SearchHit:
    """One channel hit: `record_id` (from payload), Qdrant `point_id`, raw score and returned payload."""

    record_id: str
    point_id: str
    score: float
    payload: dict[str, Any]


def _profile_invalid(detail: str) -> StageError:
    return StageError(_PROFILE_INVALID, stage="index", plugin_id=PLUGIN_ID, detail=detail)


def _sparse(vector: SparseVector) -> models.SparseVector:
    indices = [i.root for i in vector.indices]
    values = [v.root for v in vector.values]
    validate_sparse(indices, values)
    return models.SparseVector(indices=indices, values=values)


class QdrantIndexBackend:
    """Qdrant `index_backend` (role `vector`; `lite` sole backend) over a `QdrantClient`."""

    plugin_id = PLUGIN_ID

    def __init__(self, client: QdrantClient, *, backend_version: str | None = None) -> None:
        """Wrap an existing client (server or local mode)."""
        self._client = client
        self.backend_version = backend_version
        self._layouts: dict[str, CollectionLayout] = {}

    @classmethod
    def local(cls, path: str | None = None) -> QdrantIndexBackend:
        """Local-mode backend: in-memory when `path` is None, else persisted under `path`."""
        client = QdrantClient(":memory:") if path is None else QdrantClient(path=path)
        version = f"local:qdrant-client-{importlib.metadata.version('qdrant-client')}"
        return cls(client, backend_version=version)

    @property
    def client(self) -> QdrantClient:
        """The wrapped client (for maintenance jobs and tests)."""
        return self._client

    def capabilities(self) -> dict[str, Any]:
        """Return the `IndexBackendCapabilities` `extra` block (13 §2.2; bible §5.3 fields only)."""
        return {
            "supports_server_bm25": False,
            "korean_analyzer": False,
            "supports_server_fusion": ["rrf", "dbsf"],
            "tenant_isolation": ["payload_filter", "shard_key", "index_per_tenant"],
            "supports_alias_swap": True,
            "supports_multivector": True,
            "max_vector_dim": None,
            "max_multivector_elements": 1048576,
            # Local mode accepts `vector={}` (spike 2026-09-23); server confirmation is needs_docker.
            "supports_payload_only_points": None,
        }

    # -- collection lifecycle -------------------------------------------------------------

    def ensure_collection(self, name: str, layout: CollectionLayout) -> bool:
        """Create `name` with `layout` + payload indexes; if it exists, only compare (13 §4.1).

        Returns True when the collection was created. A mismatch in dense dim/distance, the named
        vector set or the sparse `modifier` raises `profile.invalid`.
        """
        if self._client.collection_exists(name):
            self._verify_layout(name, layout)
            self._layouts[name] = layout
            return False
        sparse: dict[str, models.SparseVectorParams] = {}
        if layout.sparse_bm25:
            sparse[SPARSE_BM25] = models.SparseVectorParams(
                modifier=models.Modifier.IDF, index=models.SparseIndexParams(on_disk=True)
            )
        if layout.sparse_learned:
            sparse[SPARSE_LEARNED] = models.SparseVectorParams(
                modifier=models.Modifier.NONE, index=models.SparseIndexParams(on_disk=True)
            )
        hnsw = models.HnswConfigDiff(m=0, payload_m=16)  # bible §13.4: per-tenant subgraphs only
        self._client.create_collection(
            name,
            vectors_config={
                DENSE: models.VectorParams(
                    size=layout.dense_dim,
                    distance=models.Distance.COSINE,
                    on_disk=True,
                    hnsw_config=models.HnswConfigDiff(m=0, payload_m=16, ef_construct=128),
                )
            },
            sparse_vectors_config=sparse,
            hnsw_config=hnsw,
            on_disk_payload=True,
        )
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message=_LOCAL_INDEX_WARNING, category=UserWarning)
            for field_name, schema in PAYLOAD_INDEXES.items():
                self._client.create_payload_index(name, field_name=field_name, field_schema=schema, wait=True)
        self._layouts[name] = layout
        return True

    def _verify_layout(self, name: str, layout: CollectionLayout) -> None:
        params = self._client.get_collection(name).config.params
        vectors = params.vectors if isinstance(params.vectors, dict) else {}
        sparse = params.sparse_vectors or {}
        names = set(vectors) | set(sparse)
        if names != set(layout.vector_names()):
            msg = f"{name}: named vectors {sorted(names)} != {sorted(layout.vector_names())}"
            raise _profile_invalid(msg)
        dense = vectors[DENSE]
        if dense.size != layout.dense_dim or dense.distance != models.Distance.COSINE:
            msg = f"{name}: dense {dense.size}/{dense.distance} != {layout.dense_dim}/Cosine"
            raise _profile_invalid(msg)
        expected_modifier = {SPARSE_BM25: models.Modifier.IDF, SPARSE_LEARNED: models.Modifier.NONE}
        for slot, cfg in sparse.items():
            if (cfg.modifier or models.Modifier.NONE) != expected_modifier.get(slot):
                msg = f"{name}: sparse {slot} modifier {cfg.modifier}"
                raise _profile_invalid(msg)

    def _layout(self, collection: str) -> CollectionLayout:
        target = self.resolve_alias(collection) or collection
        layout = self._layouts.get(target)
        if layout is None:
            msg = f"collection {collection!r} not ensured by this adapter"
            raise _profile_invalid(msg)
        return layout

    # -- aliases ---------------------------------------------------------------------------

    def resolve_alias(self, alias: str) -> str | None:
        """Return the physical collection behind `alias`, or None."""
        for description in self._client.get_aliases().aliases:
            if description.alias_name == alias:
                return description.collection_name
        return None

    def swap_alias(self, alias: str, physical_name: str) -> str | None:
        """Point `alias` at `physical_name` in one alias-update call; return the previous target (13 §9)."""
        previous = self.resolve_alias(alias)
        operations: list[models.AliasOperations] = []
        if previous is not None:
            operations.append(models.DeleteAliasOperation(delete_alias=models.DeleteAlias(alias_name=alias)))
        operations.append(
            models.CreateAliasOperation(
                create_alias=models.CreateAlias(collection_name=physical_name, alias_name=alias)
            )
        )
        self._client.update_collection_aliases(change_aliases_operations=operations)
        return previous

    # -- writes ----------------------------------------------------------------------------

    def _to_point(self, record: IndexRecord, layout: CollectionLayout) -> models.PointStruct:
        point_id = verify_record_keys(record)
        vectors: dict[str, Any] = {}
        raw = record.vectors
        if raw.dense is not None:
            if len(raw.dense) != layout.dense_dim:
                raise StageError(
                    _CONTRACT_VIOLATION,
                    stage="index",
                    plugin_id=PLUGIN_ID,
                    detail=f"dense length {len(raw.dense)} != space dim {layout.dense_dim}",
                )
            vectors[DENSE] = raw.dense
        if raw.sparse_bm25 is not None:
            vectors[SPARSE_BM25] = _sparse(raw.sparse_bm25)
        if raw.sparse_learned is not None:
            vectors[SPARSE_LEARNED] = _sparse(raw.sparse_learned)
        unknown = set(vectors) - layout.vector_names()
        if unknown:
            raise StageError(
                _SPACE_MISMATCH,
                stage="index",
                plugin_id=PLUGIN_ID,
                detail=f"record vectors {sorted(unknown)} not in collection named vectors",
            )
        payload = record.model_dump(mode="json", exclude=_PAYLOAD_EXCLUDE)
        # 13 §3 step 7: explicit nulls / empty deny list so IsNull filters behave uniformly.
        payload.setdefault("acl_embargo_until", None)
        payload.setdefault("acl_expires_at", None)
        if payload.get("acl_deny") is None:
            payload["acl_deny"] = []
        return models.PointStruct(id=point_id, vector=vectors, payload=payload)

    def _validate_batch(
        self, records: Sequence[IndexRecord], commit_id: str | None, index_generation: int | None
    ) -> None:
        for record in records:
            missing = [f for f in SECURITY_FIELDS if getattr(record, f, None) is None]
            if missing:
                raise StageError(
                    _SECURITY_FIELDS_MISSING,
                    stage="index",
                    plugin_id=PLUGIN_ID,
                    detail=f"record {record.record_id.root} lacks {missing}; batch not sent (E5)",
                )
            wrong_saga = (commit_id is not None and str(record.commit_id.root) != commit_id) or (
                index_generation is not None and record.index_generation != index_generation
            )
            if record.is_current or wrong_saga:
                raise StageError(
                    _CONTRACT_VIOLATION,
                    stage="index",
                    plugin_id=PLUGIN_ID,
                    detail=f"record {record.record_id.root}: is_current must be false and match saga commit",
                )

    def upsert(
        self,
        collection: str,
        records: Sequence[IndexRecord],
        *,
        commit_id: str | None = None,
        index_generation: int | None = None,
    ) -> int:
        """Validate and upsert `records` in batches of 256 with `wait=True`; return the point count.

        Every batch is validated before anything is sent (E5: one bad record rejects all).
        Idempotent: re-upserting the same records rewrites the same point ids.
        """
        layout = self._layout(collection)
        self._validate_batch(records, commit_id, index_generation)
        points = [self._to_point(record, layout) for record in records]
        for start in range(0, len(points), UPSERT_BATCH_SIZE):
            self._client.upsert(collection, points[start : start + UPSERT_BATCH_SIZE], wait=True)
        return len(points)

    def set_current(
        self, collection: str, *, tenant_id: str, collection_id: str, document_id: str, index_generation: int
    ) -> None:
        """Flip `is_current`: generation `index_generation` true first, then every other generation false."""
        new = scope_filter(
            tenant_id, collection_id=collection_id, document_id=document_id, index_generation=index_generation
        )
        self._client.set_payload(collection, payload={"is_current": True}, points=new, wait=True)
        others = scope_filter(tenant_id, collection_id=collection_id, document_id=document_id)
        others.must_not = [
            models.FieldCondition(key="index_generation", match=models.MatchValue(value=index_generation))
        ]
        self._client.set_payload(collection, payload={"is_current": False}, points=others, wait=True)

    def delete(self, collection: str, query_filter: models.Filter) -> None:
        """Delete points matching a tenant-scoped filter (compensation, deletion, cleanup)."""
        assert_tenant_scoped(query_filter)
        self._client.delete(collection, points_selector=models.FilterSelector(filter=query_filter), wait=True)

    def count(self, collection: str, query_filter: models.Filter) -> int:
        """Exact count of points matching a tenant-scoped filter (consistency checks)."""
        assert_tenant_scoped(query_filter)
        return self._client.count(collection, count_filter=query_filter, exact=True).count

    # -- reads -----------------------------------------------------------------------------

    @staticmethod
    def _hits(points: list[models.ScoredPoint]) -> list[SearchHit]:
        hits = []
        for point in points:
            payload = dict(point.payload or {})
            hits.append(SearchHit(str(payload.get("record_id", "")), str(point.id), float(point.score), payload))
        return hits

    def search_dense(
        self,
        collection: str,
        vector: list[float],
        *,
        query_filter: models.Filter,
        top_k: int = 100,
        hnsw_ef: int | None = 128,
        with_payload: list[str] | bool = True,
    ) -> list[SearchHit]:
        """Dense channel: one pre-filtered `query_points(using="dense")` call (13 §4.4)."""
        assert_search_secured(query_filter)
        response = self._client.query_points(
            collection,
            query=vector,
            using=DENSE,
            query_filter=query_filter,
            limit=top_k,
            with_payload=with_payload,
            search_params=models.SearchParams(hnsw_ef=hnsw_ef),
        )
        return self._hits(response.points)

    def search_sparse(
        self,
        collection: str,
        vector: SparseVector,
        *,
        query_filter: models.Filter,
        using: str = SPARSE_BM25,
        top_k: int = 50,
        tenant_idf: bool = True,
        with_payload: list[str] | bool = True,
    ) -> list[SearchHit]:
        """Sparse channel (`sparse_bm25` = lexical, `sparse_learned` = sparse).

        For `sparse_bm25` with `tenant_idf`, IDF statistics are computed over the caller's tenant
        only (`SearchParams.idf = IdfCorpusParams(corpus=tenant filter)`, Qdrant 1.19; ADR-0012).
        """
        tenant_id = assert_search_secured(query_filter)
        params = None
        if using == SPARSE_BM25 and tenant_idf:
            params = models.SearchParams(idf=models.IdfCorpusParams(corpus=scope_filter(tenant_id)))
        response = self._client.query_points(
            collection,
            query=_sparse(vector),
            using=using,
            query_filter=query_filter,
            limit=top_k,
            with_payload=with_payload,
            search_params=params,
        )
        return self._hits(response.points)
