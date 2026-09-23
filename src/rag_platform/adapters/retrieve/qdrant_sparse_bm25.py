"""`retriever.qdrant_sparse_bm25` — `lite`의 `lexical` 채널을 Qdrant named sparse vector `sparse_bm25`로 낸다.

역할: `ChannelRunInput.query_text`를 토큰화해 질의 측 `tf_q(t)` sparse 벡터(`bm25_sparse.query_vector`)를
만들고, `PlanFilters`로부터 만든 사전 필터로 `QdrantIndexBackend.search_sparse(using="sparse_bm25")`를
호출한다. 채널 열거값은 항상 `lexical`(§3.5) — `standard`의 OpenSearch BM25 채널과 같은 키를 쓴다.
설계 근거: docs/04-pipelines/15 §3.1(공통 인터페이스)·§3.5(`lexical`(lite) 항목별 값·질의 `values` 규약
`tf_q`); ADR-0012; 계약 `Candidate`/`ChannelRun`/`PayloadSlim`; 어댑터
`adapters/index/qdrant/backend.py`(`search_sparse`)·`adapters/index/qdrant/filters.py`
(`from_plan_filters`)·`adapters/index/qdrant/bm25_sparse.py`(`query_vector`, `default_tokenizer`).
구성: `QdrantSparseBm25RetrieverConfig` — 옵션 없음(토크나이저는 생성자 주입, `embed/stage.py`의
`embedder` 주입과 같은 관례); `QdrantSparseBm25Retriever` — `channels.Retriever` 구현
(`plugin_id="retriever.qdrant_sparse_bm25"`, `channel=Channel.lexical`).
불변식·주의: 서버는 IDF만 곱한다(`modifier: idf`, 테넌트 코퍼스) — TF 포화·길이 정규화는 문서 색인 시
계산되어 있다(§3.5 서버 측 행). 토큰이 하나도 없으면(빈 질의) 후보 없는 빈 런을 낸다(오류 아님). 사전
필터에 `collection_id == channel.collection_id`를 항상 고정한다(공유 물리 컬렉션 혼입 방지, 리뷰
지적). 동기 `QdrantClient` 호출은 `asyncio.to_thread`로 뗀다. `storage`·`security`를 import하지
않는다; Qdrant 벤더 타입은 이 모듈 밖으로 새지 않는다.
검증 계층: 1층(여기서 검증) — `tests/retrieval/test_fusion_channels.py`. DEFERRED: 실 서버 타임아웃
강제 검증은 `needs_docker`(open_issues) — 여기는 로컬 모드 + 이벤트 루프 비블로킹만 검증한다.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict
from qdrant_client import models

from rag_platform.adapters.index.qdrant.bm25_sparse import default_tokenizer, query_vector
from rag_platform.adapters.index.qdrant.filters import from_plan_filters
from rag_platform.contracts.candidate_set import Candidate, ChannelRun, PayloadSlim
from rag_platform.contracts.common_types import (
    Capabilities,
    Channel,
    ChannelRunStatus,
    ContractsCompat,
    IsolationMode,
)
from rag_platform.sdk.hashing import hash_of
from rag_platform.sdk.stage import StageError

if TYPE_CHECKING:
    from rag_platform.adapters.index.qdrant.backend import QdrantIndexBackend, SearchHit
    from rag_platform.adapters.index.qdrant.bm25_sparse import SparseTokenizer
    from rag_platform.sdk.channel_run import ChannelRunInput
    from rag_platform.sdk.context import StageContext

__all__ = ["PLUGIN_ID", "PLUGIN_VERSION", "QdrantSparseBm25Retriever", "QdrantSparseBm25RetrieverConfig"]

PLUGIN_ID = "retriever.qdrant_sparse_bm25"
PLUGIN_VERSION = "0.1.0"
_BACKEND_ERROR = "retrieve.backend_error"
_PLATFORM_RUN_CAP = 300  # 바이블 §5.1 CandidateSet 한계: 런당 후보 상한
_IDENTITY_KEYS: tuple[str, ...] = (
    "record_id",
    "chunk_id",
    "collection_id",
    "document_id",
    "doc_version",
    "item_kind",
    "level",
    "parent_chunk_id",
    "index_generation",
)


def _root_str(value: Any) -> str:
    root = getattr(value, "root", None)
    return root if isinstance(root, str) else str(value)


class QdrantSparseBm25RetrieverConfig(BaseModel):
    """옵션 없음 — 토큰화 규칙은 `analyzer_id`(컬렉션 값)에 묶인 토크나이저 주입으로 고정된다(§3.5)."""

    model_config = ConfigDict(extra="forbid")


def _build_query_filter(inp: ChannelRunInput) -> models.Filter:
    """`PlanFilters`를 Qdrant 사전 필터로 변환하고 `collection_id` 고정·`exclude_ids`를 더한다(§4.1).

    `qdrant_dense._build_query_filter`와 같은 이유(공유 물리 컬렉션에서 다른 컬렉션 후보가 섞이는
    것을 막는다, 리뷰 지적) — 두 어댑터가 같은 로직을 복제하는 것은 `retrieval`↔`adapters`가 서로
    모르는 형제 계층이라 공유 헬퍼를 둘 곳이 이 WP 범위에는 없기 때문이다(open_issues).
    """
    base = from_plan_filters(inp.filters)
    pin = models.FieldCondition(
        key="collection_id", match=models.MatchValue(value=_root_str(inp.channel.collection_id))
    )
    must = [*(base.must or []), pin]
    if not inp.exclude_ids:
        return models.Filter(must=must, must_not=base.must_not)
    exclude = models.FieldCondition(key="chunk_id", match=models.MatchAny(any=list(inp.exclude_ids)))
    return models.Filter(must=must, must_not=[*(base.must_not or []), exclude])


def _candidate(hit: SearchHit, rank: int) -> Candidate:
    payload = hit.payload
    return Candidate(
        record_id=payload["record_id"],
        chunk_id=payload["chunk_id"],
        collection_id=payload["collection_id"],
        document_id=payload["document_id"],
        doc_version=payload["doc_version"],
        item_kind=payload["item_kind"],
        level=payload["level"],
        parent_chunk_id=payload.get("parent_chunk_id"),
        score=hit.score,
        rank=rank,
        payload_slim=PayloadSlim(
            heading_path=payload.get("heading_path", []),
            page_start=payload.get("page_start"),
            page_end=payload.get("page_end"),
            doc_date=payload.get("doc_date"),
            acl_classification=payload["acl_classification"],
            acl_hash=payload["acl_hash"],
            token_count_primary=payload["token_count_primary"],
            text_preview=payload["text_preview"],
            content_hash=payload["content_hash"],
            text_source=payload["text_source"],
        ),
        graph_path=None,
    )


def _empty_run(inp: ChannelRunInput, *, took_ms: int) -> ChannelRun:
    """빈 질의(토큰 0개)는 오류가 아니라 후보 없는 정상 런이다."""
    variant_id = _root_str(inp.variant.variant_id)
    return ChannelRun(
        channel_run_id=f"lexical:{_root_str(inp.channel.collection_id)}:{variant_id}",
        channel=Channel.lexical,
        collection_id=inp.channel.collection_id,
        variant_id=inp.variant.variant_id,
        retriever_id=PLUGIN_ID,
        backend_id=inp.channel.backend_id,
        collection_alias=inp.channel.collection_alias,
        embedding_profile_hash=inp.channel.embedding_profile_hash,
        index_generation_seen=[],
        status=ChannelRunStatus.ok,
        took_ms=took_ms,
        returned=0,
        total_hits=None,
        truncated=False,
        error=None,
        candidates=[],
    )


@dataclass
class QdrantSparseBm25Retriever:
    """`retriever.qdrant_sparse_bm25` — `channels.Retriever` 구현. 채널 열거값은 항상 `lexical`(§3.5)."""

    backend: QdrantIndexBackend
    tokenizer: SparseTokenizer = field(default_factory=default_tokenizer)
    config: QdrantSparseBm25RetrieverConfig = field(default_factory=QdrantSparseBm25RetrieverConfig)
    channel: Channel = Channel.lexical
    plugin_id: str = PLUGIN_ID
    config_schema: type[BaseModel] = QdrantSparseBm25RetrieverConfig
    requires_lineage: tuple[str, ...] = ()

    def config_hash(self) -> str:
        """`H("config", canonical_json(config))`(토크나이저의 `analyzer_id`를 config에 포함)."""
        payload = {**self.config.model_dump(mode="json"), "analyzer_id": self.tokenizer.analyzer_id}
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return hash_of("config", canonical)

    def capabilities(self) -> Capabilities:
        """`extra.requires_query_vector=None`(임베딩 서버 불필요 — 결정적 토큰화, §3.5)."""
        return Capabilities(
            isolation_modes=[IsolationMode.in_process],
            supports_resumable=False,
            contracts_compat=ContractsCompat(">=1.0,<2.0"),
            input_formats=None,
            requires_gpu=False,
            extra={"requires_query_vector": None, "supports_total_hits": False},
        )

    def fingerprint(self) -> str:
        """`H("producer", plugin_id, plugin_version, config_hash, "", "")`(인프로세스, 모델 없음)."""
        return hash_of("producer", self.plugin_id, PLUGIN_VERSION, self.config_hash(), "", "")

    async def run(self, inp: ChannelRunInput, ctx: StageContext) -> ChannelRun:
        """§3.5: `query_text`를 토큰화 → `tf_q` sparse 벡터 → `search_sparse(using="sparse_bm25")`."""
        started = ctx.now()
        tokens = list(self.tokenizer.tokenize(inp.query_text))
        vector = query_vector(tokens)
        if vector is None:
            took_ms = max(0, int((ctx.now() - started).total_seconds() * 1000))
            return _empty_run(inp, took_ms=took_ms)

        query_filter = _build_query_filter(inp)
        effective_top_k = min(inp.channel.top_k, _PLATFORM_RUN_CAP)
        try:
            # `qdrant_dense.run`과 같은 이유로 별도 스레드로 뗀다(동기 클라이언트가 이벤트 루프를
            # 막으면 §8.1 7단계 채널 타임아웃이 강제되지 않는다, 리뷰 지적).
            hits = await asyncio.to_thread(
                self.backend.search_sparse,
                inp.channel.collection_alias,
                vector,
                query_filter=query_filter,
                using="sparse_bm25",
                top_k=effective_top_k,
                tenant_idf=True,
                with_payload=[*inp.payload_slim_keys, *_IDENTITY_KEYS],
            )
        except StageError:
            raise
        except Exception as exc:
            raise StageError(_BACKEND_ERROR, stage="retrieve", plugin_id=self.plugin_id, detail=str(exc)) from exc

        candidates = [_candidate(hit, rank) for rank, hit in enumerate(hits, start=1)]
        generations = sorted({gen for hit in hits if (gen := hit.payload.get("index_generation")) is not None})
        took_ms = max(0, int((ctx.now() - started).total_seconds() * 1000))
        variant_id = _root_str(inp.variant.variant_id)
        return ChannelRun(
            channel_run_id=f"lexical:{_root_str(inp.channel.collection_id)}:{variant_id}",
            channel=Channel.lexical,
            collection_id=inp.channel.collection_id,
            variant_id=inp.variant.variant_id,
            retriever_id=self.plugin_id,
            backend_id=inp.channel.backend_id,
            collection_alias=inp.channel.collection_alias,
            embedding_profile_hash=inp.channel.embedding_profile_hash,
            index_generation_seen=generations,
            status=ChannelRunStatus.ok,
            took_ms=took_ms,
            returned=len(candidates),
            total_hits=None,
            truncated=inp.channel.top_k > _PLATFORM_RUN_CAP,
            error=None,
            candidates=candidates,
        )
