"""GENERATED — do not edit; run `uv run python tools/contracts_gen.py` to regenerate.

Source of truth: schemas/*.schema.json (bible §5.1, §6.4, §12)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, RootModel

from . import common_types


class RetrieverId(RootModel[str]):
    root: str = Field(
        ...,
        description="retriever 확장 지점의 plugin_id(바이블 §6.1). 예 retriever.qdrant_sparse_bm25",
        pattern="^retriever\\.[a-z][a-z0-9_]*$",
    )


class IndexGenerationSeenItem(RootModel[int]):
    root: int = Field(..., ge=0)


class PayloadSlim(BaseModel):
    """
    IndexRecord payload의 슬림 투영(≤ 1KB). 융합·설명·사전 예산에 필요한 값만
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    heading_path: list[str]
    page_start: int | None = Field(..., ge=1)
    page_end: int | None = Field(..., ge=1)
    doc_date: common_types.Date | None
    acl_classification: common_types.Classification
    acl_hash: common_types.Hex64 = Field(..., description="E9 회수 힌트 대조 키")
    token_count_primary: int = Field(..., description="임베딩 토크나이저 기준 토큰 수(패킹 사전 예산)", ge=0)
    text_preview: str = Field(..., description="≤ 200자(MCP concise·디버그). 본문 대체 불가", max_length=200)
    content_hash: common_types.Hex64 = Field(..., description="blake3_hex(utf8(Chunk.text)). 1차 dedup 키")
    text_source: common_types.BlockSource


class Candidate(BaseModel):
    """
    개별 리트리버가 반환한 후보(브리프 §10 Candidate). 본문·인용 좌표·전체 ACL은 hydrate가 채운다
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    record_id: common_types.Hex64 = Field(
        ...,
        description='H("record", tenant_id, collection_id, document_id, str(index_generation), chunk_id). hydrate 조회 키이자 융합 후 후보 식별자',
    )
    chunk_id: common_types.Hex64 = Field(..., description="콘텐츠 주소 청크 ID(세대·스코프 무관)")
    collection_id: common_types.Ulid = Field(..., description="= 소속 런의 collection_id")
    document_id: common_types.Ulid
    doc_version: common_types.Hex64
    item_kind: common_types.ItemKind = Field(
        ..., description="전략 필터 item_kinds 안의 값(parent는 후보가 될 수 없다)"
    )
    level: common_types.ChunkLevel = Field(..., description="전략 필터 level_in 안의 값")
    parent_chunk_id: common_types.Hex64 | None = Field(..., description="small-to-big 확장 키")
    score: float = Field(..., description="채널 원점수(cosine / dot / BM25 / MaxSim)")
    rank: int = Field(..., description="채널 내 1-based 순위", ge=1, le=300)
    payload_slim: PayloadSlim
    graph_path: list[str] | None = Field(None, description="그래프 채널 설명(엔티티·관계 경로)", max_length=32)


class ChannelRun(BaseModel):
    """
    채널 런 하나(채널 × 컬렉션 × 변형). 후보는 정확히 하나의 컬렉션에 속한다
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    channel_run_id: common_types.ChannelRunId
    channel: common_types.Channel = Field(..., description="lite의 sparse_bm25 벡터 질의는 channel=lexical")
    collection_id: common_types.Ulid
    variant_id: common_types.Ulid = Field(
        ..., description="QueryPlan.rewritten_queries[].variant_id(original은 query_id)"
    )
    retriever_id: RetrieverId = Field(..., description="= QueryPlan.channels[].retriever_id(09 §6.5)")
    backend_id: common_types.PluginId = Field(
        ...,
        description="= QueryPlan.channels[].backend_id(index_backend.{implementation}, 09 §6.5) = 컬렉션 backends[].backend_id(15 §2.2)",
    )
    collection_alias: str = Field(
        ...,
        description="물리 alias(col_{collection_id}_vec | _lex, 바이블 §13.4)",
        max_length=128,
        min_length=1,
    )
    embedding_profile_hash: common_types.Hex64 = Field(
        ..., description="컬렉션의 embedding_profile_hash(convex_* 적격성 판정 근거)"
    )
    index_generation_seen: list[IndexGenerationSeenItem] = Field(
        ...,
        description="이 런의 후보가 속한 문서 세대 집합(ContextPack.diagnostics.index_generations_seen 원천)",
    )
    status: common_types.ChannelRunStatus
    took_ms: int = Field(..., ge=0)
    returned: int = Field(..., description="= candidates.length", ge=0, le=300)
    total_hits: int | None = Field(
        ...,
        description="필터 후 총량(recall 진단; 근사 허용, 백엔드 미제공 시 null)",
        ge=0,
    )
    truncated: bool = Field(..., description="top_k 또는 런당 상한 300으로 절단되었는가")
    error: common_types.StageError | None = Field(
        None,
        description="채널 제외 사유(retrieve.channel_timeout, retrieve.backend_error 등). status ∈ {timeout, error}면 필수",
    )
    candidates: list[Candidate] = Field(
        ...,
        description="채널 원점수 내림차순, rank 1..n(런당 상한 300)",
        max_length=300,
    )


class CandidateSet(BaseModel):
    """
    retrieve 스테이지의 출력(바이블 §5.5). 채널 × 컬렉션 × 질의 변형 단위의 채널 런(channel_runs[])과 각 런의 후보(원점수·순위·payload_slim)를 담는다. 소비자는 fuse. 봉투(질의 측)·공용 타입·열거는 urn:rag:schema:common-types:1의 $defs를 참조하며 재정의하지 않는다. 소유 문서: docs/03-contracts/10-candidate-set-and-ranked-set.md.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    schema_version: str = Field(
        ...,
        description='계약 버전. 초기 "1.0.0"; 이 스키마($id major 1)는 1.x 만 수용(바이블 §6.4)',
        pattern="^1\\.(0|[1-9]\\d*)\\.(0|[1-9]\\d*)$",
    )
    schema_type: Literal["CandidateSet"] = Field(..., description="PascalCase 타입명")
    tenant_id: common_types.Ulid = Field(..., description="보안 삼중항 1(SecurityContext.tenant_id와 동일)")
    collection_ids: list[common_types.Ulid] = Field(
        ...,
        description="질의 측 봉투(복수). QueryPlan.collection_ids와 동일",
        max_length=20,
        min_length=1,
    )
    producer: common_types.Producer = Field(
        ...,
        description="retrieve 팬아웃 코디네이터의 재현성 지문. plugin_id는 합성 값 retriever.pipeline(09 QueryPlan.producer의 query_transformer.pipeline 규약과 동일), 채널별 retriever는 channel_runs[].retriever_id",
    )
    warnings: list[common_types.Warning] = Field(..., description="품질 삼중항 2(빈 배열 허용)")
    degraded: list[common_types.DegradedEntry] = Field(
        ..., description="품질 삼중항 3. 채널 제외는 {channel.*, timeout|unavailable}"
    )
    created_at: common_types.DateTime = Field(..., description="RFC 3339 UTC")
    candidate_set_id: common_types.Ulid = Field(..., description="발급형 ID")
    plan_id: common_types.Ulid = Field(..., description="입력 QueryPlan.plan_id")
    query_id: common_types.Ulid = Field(..., description="QueryRequest.query_id")
    channel_runs: list[ChannelRun] = Field(
        ...,
        description="채널 × 컬렉션 × 질의 변형 단위. 실패·비활성 런도 status로 남긴다(최소 1개 ok, 불변식 CS-4)",
        min_length=1,
    )
    filters_applied: FiltersApplied = Field(
        ...,
        description="백엔드에 실제 전송된 필터(감사, 바이블 §5.5). security·strategy·user·self_query 구분 + 실전송 해시 effective_hash",
    )
    security_context_hash: common_types.Hex64 = Field(
        ...,
        description='H("sec", tenant_id, ",".join(sorted(principals)), ",".join(sorted(collection_ids)), as_of, classification_max, ",".join(visible_set))(바이블 §6.2 그대로). 어댑터가 "필터에 tenant_id 포함"을 서명',
    )
    total_unique: int = Field(..., description="전 런의 서로 다른 record_id 수(= fusion.candidates_in)", ge=0)
    total_latency_ms: int = Field(..., description="병렬 검색 전체 경과(max(took_ms) 이상)", ge=0)


class FiltersApplied(BaseModel):
    """
    백엔드에 실제 전송된 필터 트리(바이블 §5.5 filters_applied·§10.2 (a)(b)(c) 구분). security·strategy는 QueryPlan.filters와 동일(변경 불가), user·self_query는 page 변환·0건 완화를 반영한 전송 트리(원형은 QueryPlan.filters에 남음, 09 §5.4), effective_hash는 그 전송 트리의 해시. security·strategy 정의는 09 query-plan $defs의 사본(#/$defs/SecurityFilter·StrategyFilter)
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    security: common_types.SecurityFilter = Field(
        ...,
        description="= QueryPlan.filters.security(보안 불변식 (a), 09 §5.1). 제거·완화·변환 불가",
    )
    strategy: common_types.StrategyFilter = Field(
        ..., description="= QueryPlan.filters.strategy(전략 필터 (b), 09 §5.2)"
    )
    user: common_types.FilterNode | None = Field(
        ...,
        description="Y(nullable). 실제 전송된 사용자 필터 트리(page 변환·0건 완화 반영 후). 원형은 QueryPlan.filters.user",
    )
    self_query: common_types.FilterNode | None = Field(
        ...,
        description="Y(nullable). 실제 전송된 추출 필터 트리(완화 반영 후). 원형은 QueryPlan.filters.self_query",
    )
    effective_hash: common_types.Hex64 = Field(
        ...,
        description='실전송 해시 H("filters", canonical_json(security + strategy + user + self_query; as_of는 바인드 이름 ":as_of"))(바이블 §6.2, 09 §5.4 잠정 해석) — 이 객체의 네 필드로 계산. page 변환·완화가 없으면 QueryPlan.filters.effective_hash(계획 트리 해시)와 같고 있으면 다르다(대조로 변환·완화 유무 판정). audit.query.executed·ContextPack.diagnostics.filters_applied가 복사. Y(바이블 §5.5 patch 전제, 문서 미해결 이슈 3)',
    )


CandidateSet.model_rebuild()
