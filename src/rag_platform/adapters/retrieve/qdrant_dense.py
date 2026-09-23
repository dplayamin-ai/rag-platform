"""`retriever.qdrant_dense` — Qdrant `query_points(using="dense")` 단일 호출로 `dense` 채널 런을 만든다.

역할: `channels.ChannelRunInput.query_vectors.dense`(미리 계산된 임베딩)와 `PlanFilters`로부터 만든
사전 필터로 `QdrantIndexBackend.search_dense`를 호출하고, 결과를 원점수 내림차순·`rank` 1..n의
`ChannelRun`으로 감싼다.
설계 근거: docs/04-pipelines/15 §3.1(공통 인터페이스)·§3.2(`dense` 항목별 값), 바이블 §4.3 `retrieve` 행;
계약 `Candidate`/`ChannelRun`/`PayloadSlim`(`contracts/candidate_set.py`); 어댑터
`adapters/index/qdrant/backend.py`(`QdrantIndexBackend.search_dense`)·`adapters/index/qdrant/filters.py`
(`from_plan_filters`).
구성: `QdrantDenseRetrieverConfig` — `hnsw_ef`/`exact`(초안 §3.2 파라미터); `QdrantDenseRetriever` —
`Stage` 5멤버 중 실행에 필요한 3개(`plugin_id="retriever.qdrant_dense"`, `channel=Channel.dense`)를
구현하는 `channels.Retriever`.
불변식·주의: 질의 벡터가 없으면(임베딩 서버 실패) `embed.server_unavailable`을 던진다(§2.2 "질의 벡터
부재" 규칙) — 백엔드를 호출하지 않는다. 사후 필터 없음(사전 필터만, §4.1). 사전 필터에 `collection_id
== channel.collection_id`를 항상 고정한다 — 공유 물리 컬렉션(§13.4)에서 다른 컬렉션 후보가 섞이는
것을 막는다. 동기 `QdrantClient` 호출은 `asyncio.to_thread`로 뗀다(이벤트 루프를 막으면 채널 타임아웃이
걸리지 않는다). `storage`·`security`를 import하지 않는다; Qdrant 벤더 타입(`models.*`)은 이 모듈 밖으로
새지 않는다(반환은 계약 `ChannelRun`).
검증 계층: 1층(여기서 검증) — `tests/retrieval/test_fusion_channels.py`. DEFERRED: 실 Qdrant 서버 대상
타임아웃 강제(§8.1 7단계 250ms) 검증은 `needs_docker`(open_issues) — 여기는 로컬 모드 + 이벤트 루프
비블로킹 자체만 검증한다.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict
from qdrant_client import models

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
    from rag_platform.sdk.channel_run import ChannelRunInput
    from rag_platform.sdk.context import StageContext

__all__ = ["PLUGIN_ID", "PLUGIN_VERSION", "QdrantDenseRetriever", "QdrantDenseRetrieverConfig"]

PLUGIN_ID = "retriever.qdrant_dense"
PLUGIN_VERSION = "0.1.0"
_EMBED_SERVER_UNAVAILABLE = "embed.server_unavailable"
_BACKEND_ERROR = "retrieve.backend_error"
_PLATFORM_RUN_CAP = 300  # 바이블 §5.1 CandidateSet 한계: 런당 후보 상한
#: `Candidate`의 식별자 필드(payload_slim 10키 + 이들) — `with_payload` 요청에 필요.
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


class QdrantDenseRetrieverConfig(BaseModel):
    """§3.2 초안 검색 파라미터. `hnsw_ef`는 `top_k` 미만이면 어댑터가 `top_k`로 올린다."""

    model_config = ConfigDict(extra="forbid")

    hnsw_ef: int = 128
    exact: bool = False


def _build_query_filter(inp: ChannelRunInput) -> models.Filter:
    """`PlanFilters`를 Qdrant 사전 필터로 변환하고 `collection_id` 고정·`exclude_ids`를 더한다(§4.1).

    `filters.security.collection_ids`는 이 요청이 허용된 컬렉션 전체(플래너가 요청 ∩ 보안으로 좁혀
    두지만, 다중 컬렉션 요청에서는 여전히 여러 값일 수 있다)이고, `collection_alias`는 여러 컬렉션이
    가리키는 공유 물리 컬렉션(§13.4)일 수 있다 — 이 런은 정확히 `channel.collection_id` 하나만
    담당하므로 여기서 고정해야 다른 컬렉션 후보가 섞여 들어오지 않는다(리뷰 지적: 그렇지 않으면 같은
    채널·다른 컬렉션 두 런이 서로의 후보를 중복 반환해 §8.1 "컬렉션 차원 무중복 기여"를 어긴다).
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


@dataclass
class QdrantDenseRetriever:
    """`retriever.qdrant_dense` — `channels.Retriever` 구현(`Stage` 5멤버 중 실행에 필요한 3개)."""

    backend: QdrantIndexBackend
    config: QdrantDenseRetrieverConfig = field(default_factory=QdrantDenseRetrieverConfig)
    channel: Channel = Channel.dense
    plugin_id: str = PLUGIN_ID
    config_schema: type[BaseModel] = QdrantDenseRetrieverConfig
    requires_lineage: tuple[str, ...] = ()

    def config_hash(self) -> str:
        """`H("config", canonical_json(config))`(바이블 §6.2 근사, embed/stage.py와 같은 관례)."""
        dumped = self.config.model_dump(mode="json")
        canonical = json.dumps(dumped, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return hash_of("config", canonical)

    def capabilities(self) -> Capabilities:
        """`extra.requires_query_vector="dense"`(§3.1) — 코디네이터가 이 채널에 필요한 벡터 슬롯을 안다."""
        return Capabilities(
            isolation_modes=[IsolationMode.in_process],
            supports_resumable=False,
            contracts_compat=ContractsCompat(">=1.0,<2.0"),
            input_formats=None,
            requires_gpu=False,
            extra={"requires_query_vector": "dense", "supports_total_hits": False},
        )

    def fingerprint(self) -> str:
        """`H("producer", plugin_id, plugin_version, config_hash, "", "")`(인프로세스, 모델 없음)."""
        return hash_of("producer", self.plugin_id, PLUGIN_VERSION, self.config_hash(), "", "")

    async def run(self, inp: ChannelRunInput, ctx: StageContext) -> ChannelRun:
        """§3.2: `search_dense` 한 번 호출 → `Candidate[]`(원점수 내림차순, `rank` 1..n)."""
        started = ctx.now()
        if inp.query_vectors.dense is None:
            raise StageError(
                _EMBED_SERVER_UNAVAILABLE,
                stage="retrieve",
                plugin_id=self.plugin_id,
                detail="dense query vector missing",
            )
        query_filter = _build_query_filter(inp)
        effective_top_k = min(inp.channel.top_k, _PLATFORM_RUN_CAP)
        hnsw_ef = max(self.config.hnsw_ef, effective_top_k)
        try:
            # `QdrantClient`(로컬 모드 포함)는 동기 호출이다 — `await` 없이 그대로 부르면 이벤트
            # 루프가 막혀 `asyncio.gather`가 실질적으로 순차 실행되고 `asyncio.wait_for` 타임아웃도
            # 걸리지 않는다(§8.1 7단계 "채널 타임아웃 시 제외" 위반, 리뷰 지적) — 별도 스레드로 뗀다.
            hits = await asyncio.to_thread(
                self.backend.search_dense,
                inp.channel.collection_alias,
                list(inp.query_vectors.dense),
                query_filter=query_filter,
                top_k=effective_top_k,
                hnsw_ef=hnsw_ef,
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
            channel_run_id=f"dense:{_root_str(inp.channel.collection_id)}:{variant_id}",
            channel=Channel.dense,
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
