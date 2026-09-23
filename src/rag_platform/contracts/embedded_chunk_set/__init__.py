"""GENERATED — 수정 금지. 재생성: `uv run python tools/contracts_gen.py`

역할: `schemas/*.schema.json`의 계약 스키마 하나를 그대로 옮긴 Pydantic v2 모델(계층 L0) — 파이프라인 단계 간에 주고받는 데이터의 타입을 정의한다.
설계 근거: 바이블 §5.1(계약이 정본), §6.4(kebab 스키마 이름 ↔ snake_case 모듈명), §12(레이어 지도).
구성: 클래스명은 스키마의 `title`(또는 `$defs`의 각 항목)과 동일하며, 필드는 스키마의 `properties`/`required`를 그대로 반영한다.
불변식: `tools/contracts_gen.py`만 이 파일을 쓴다 — 손으로 고친 내용은 다음 재생성 때 사라진다.
검증 계층: 1층(여기서 검증) — tests/contracts, tools/validate-contracts.mjs.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, RootModel, constr

from .. import common_types
from .EmbeddedChunkSet import vector_layout as vector_layout_1


class Source(BaseModel):
    """
    detect 출력 SourceDocument 계약 산출물(00 §3.2 대응표·I-7). 원본 바이트가 아니다 — index가 requires_lineage로 로드해 acl_*·acl_hash·title·source_uri·metadata를 조립한다
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    uri: common_types.Uri = Field(..., description="s3:// 또는 file:// URI(오브젝트 키 규약 §13.3)")
    blake3: common_types.Hex64 = Field(..., description="산출물 바이트의 BLAKE3 콘텐츠 해시")
    media_type: Literal["application/vnd.rag.source-document+json"] = Field(
        ...,
        description="application/vnd.rag.{kebab-name}+json 또는 원본 MIME",
        pattern="^[a-z]+/[A-Za-z0-9!#$&^_.+-]+$",
    )
    schema_type: Literal["SourceDocument"] = Field(
        ...,
        description="계약 산출물이면 PascalCase 타입명. 봉투 schema_type과 일치해야 로드",
        pattern="^[A-Z][A-Za-z0-9]*$",
    )
    schema_version: common_types.Semver = Field(..., description="계약 산출물이면 계약 버전")
    size_bytes: int = Field(..., description="바이트 크기(인라인 금지 검증·계량)", ge=0)
    stage_key: common_types.Hex64 | None = Field(None, description="생산 스테이지 멱등성 키(계보 자기 서술)")


class LineageRefs(BaseModel):
    """
    embed 출력의 상류 참조 {source, parsed, normalized, chunk_set, enriched}. 자기 자신(embedded) 금지. 각 키의 schema_type은 00 §3.2 대응표와 일치(I-7)
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    source: Source = Field(
        ...,
        description="detect 출력 SourceDocument 계약 산출물(00 §3.2 대응표·I-7). 원본 바이트가 아니다 — index가 requires_lineage로 로드해 acl_*·acl_hash·title·source_uri·metadata를 조립한다",
    )
    parsed: common_types.ArtifactRef
    normalized: common_types.ArtifactRef
    chunk_set: common_types.ArtifactRef
    enriched: common_types.ArtifactRef
    embedded: common_types.ArtifactRef | None = None


class EnrichedRef(BaseModel):
    """
    입력 EnrichedChunkSet 산출물. lineage_refs.enriched와 blake3 동일
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    uri: common_types.Uri = Field(..., description="s3:// 또는 file:// URI(오브젝트 키 규약 §13.3)")
    blake3: common_types.Hex64 = Field(..., description="산출물 바이트의 BLAKE3 콘텐츠 해시")
    media_type: Literal["application/vnd.rag.enriched-chunk-set+json"] = Field(
        ...,
        description="application/vnd.rag.{kebab-name}+json 또는 원본 MIME",
        pattern="^[a-z]+/[A-Za-z0-9!#$&^_.+-]+$",
    )
    schema_type: Literal["EnrichedChunkSet"] = Field(
        ...,
        description="계약 산출물이면 PascalCase 타입명. 봉투 schema_type과 일치해야 로드",
        pattern="^[A-Z][A-Za-z0-9]*$",
    )
    schema_version: common_types.Semver = Field(..., description="계약 산출물이면 계약 버전")
    size_bytes: int = Field(..., description="바이트 크기(인라인 금지 검증·계량)", ge=0)
    stage_key: common_types.Hex64 | None = Field(None, description="생산 스테이지 멱등성 키(계보 자기 서술)")


class Mode(StrEnum):
    """
    항상 document. 질의 측 임베딩(query)은 이 계약에 나타나지 않는다
    """

    document = "document"
    query = "query"


class Shape2Item(RootModel[int]):
    root: int = Field(..., ge=0)


class Shape2Item1(RootModel[int]):
    root: int = Field(..., ge=1)


class Shape2(RootModel[list[Shape2Item | Shape2Item1]]):
    """
    2차원 배열 형상 [rows, dim]
    """

    root: list[Shape2Item | Shape2Item1] = Field(
        ..., description="2차원 배열 형상 [rows, dim]", max_length=2, min_length=2
    )


class Dense(BaseModel):
    """
    dense 행렬 [rows, dim]; rows = stats.vectors_total; normalized는 항상 true(L2 정규화 완료, 바이블 §5.4)
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    array_key: str = Field(..., min_length=1)
    dtype: vector_layout_1.Dtype
    normalized: Literal[True]
    shape: Shape2


class LateInteraction(BaseModel):
    """
    토큰 벡터를 이어 붙인 [total_tokens, dim]; VectorBundle.late_interaction.offset·count가 행 구간
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    array_key: str = Field(..., min_length=1)
    dtype: vector_layout_1.Dtype
    shape: Shape2


class VectorLayout(BaseModel):
    """
    선택(N). vectors_ref 파생물의 물리 배치. 소비자(index 어댑터)가 dtype·정규화 가정을 검증할 수 있게 한다
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    format: vector_layout_1.Format = Field(..., description="vectors_ref 컨테이너 형식")
    dense: Dense = Field(
        ...,
        description="dense 행렬 [rows, dim]; rows = stats.vectors_total; normalized는 항상 true(L2 정규화 완료, 바이블 §5.4)",
    )
    late_interaction: LateInteraction | None = Field(
        None,
        description="토큰 벡터를 이어 붙인 [total_tokens, dim]; VectorBundle.late_interaction.offset·count가 행 구간",
    )


class EmbedStats(BaseModel):
    """
    바이블 §5.4 stats {vectors_total, bytes_dense, bytes_sparse, bytes_late_interaction} → rag_index_bytes_total{vector}·IndexCommit.stats
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    vectors_total: int = Field(..., description="= vectors 키 수", ge=0)
    bytes_dense: int = Field(..., description="vectors_ref 내 dense 행렬 바이트(dtype 기준)", ge=0)
    bytes_sparse: int = Field(
        ...,
        description="sparse_learned + sparse_bm25의 indices(4B)·values(4B) 합",
        ge=0,
    )
    bytes_late_interaction: int = Field(..., description="late_interaction 행렬 바이트. 슬롯이 없으면 0", ge=0)
    truncated_count: int | None = Field(
        None,
        description="선택(N). VectorBundle.truncated=true 수(= embed.token_overflow 경고 수)",
        ge=0,
    )


class EmbeddedChunkSet(BaseModel):
    """
    embed 스테이지 출력(바이블 §5.4). 청크 본문·보강은 enriched_ref로 참조하고, 벡터 본문은 vectors_ref(npz/parquet 파생물)에 두며 vectors(object<chunk_id, VectorBundle>)는 이름별 오프셋·sparse 항목만 담는다. 색인 대상(level 0·2)만 포함하고 부모(level 1)는 임베딩하지 않는다. mode는 항상 document(const). 공용 타입·열거는 urn:rag:schema:common-types:1 을 참조한다. 소유 문서: docs/03-contracts/07-embedded-chunk-set-and-index-record.md
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    schema_version: str = Field(
        ...,
        description='계약 버전. 초기 "1.0.0"',
        pattern="^1.(0|[1-9]d*).(0|[1-9]d*)$",
    )
    schema_type: Literal["EmbeddedChunkSet"] = Field(
        ..., description="PascalCase 타입명. ArtifactRef.schema_type와 일치해야 로드"
    )
    tenant_id: common_types.Ulid = Field(..., description="보안 삼중항 1")
    collection_id: common_types.Ulid = Field(..., description="보안 삼중항 2(수집 측 단수)")
    producer: common_types.Producer = Field(
        ...,
        description="재현성 지문. plugin_id는 embedder.{implementation}, model_ids는 임베딩 모델 {repo}@{revision}, image_digest는 외부 서빙(vLLM/TEI)이면 non-null·인프로세스(lite)면 null",
    )
    quality: common_types.Quality = Field(
        ...,
        description="품질 삼중항 1. 입력 EnrichedChunkSet의 값을 전파(되돌리지 않음). VectorBundle.truncated=true가 1건 이상이면 degraded(13 §5.2; 초안, Pydantic 검증)",
    )
    warnings: list[common_types.Warning] = Field(
        ...,
        description="품질 삼중항 2. embed.token_overflow(chunk_id 포함) 등 콘텐츠 미포함",
    )
    created_at: common_types.DateTime
    lineage_refs: LineageRefs = Field(
        ...,
        description="embed 출력의 상류 참조 {source, parsed, normalized, chunk_set, enriched}. 자기 자신(embedded) 금지. 각 키의 schema_type은 00 §3.2 대응표와 일치(I-7)",
    )
    chunk_set_id: common_types.Ulid = Field(..., description="입력 EnrichedChunkSet.chunk_set_id 복사")
    document_id: common_types.Ulid
    doc_version: common_types.Hex64 = Field(..., description="= SourceDocument.content_hash(ADR-0005)")
    enriched_ref: EnrichedRef = Field(
        ...,
        description="입력 EnrichedChunkSet 산출물. lineage_refs.enriched와 blake3 동일",
    )
    embedding_space_ids: common_types.EmbeddingSpaceIds
    embedding_profile_hash: common_types.Hex64 = Field(
        ...,
        description='H("spaces", *sorted(f"{name}={space_id}"))(바이블 §6.2) — 컬렉션 바인딩 단위. CollectionSpec.embedding_profile_hash와 같아야 한다',
    )
    embedder_fingerprint: common_types.Hex64 = Field(
        ...,
        description='H("embedder", plugin_id, plugin_version, config_hash, image_digest or "", embedding_profile_hash)(바이블 §6.2). 서빙 스택 이미지 digest 포함',
    )
    mode: Literal["document"] = Field(
        ...,
        description="항상 document. 질의 측 임베딩(query)은 이 계약에 나타나지 않는다",
    )
    pooling: common_types.Pooling = Field(
        ...,
        description="cls(BGE-M3 dense 기본) / mean / late(late chunking; mean pooling 장문 모델 강제)",
    )
    vectors_ref: common_types.ArtifactRef = Field(
        ...,
        description="벡터 본문 파생물(npz 또는 parquet; 봉투 없음, tenants/{tenant_id}/derived/vectors/{blake3[:2]}/{blake3}.npz). dense·late_interaction 행렬을 담고 vectors[*].{dense,late_interaction}.offset이 행 인덱스다. 계약 산출물이 아니므로 schema_type 없음",
    )
    vector_layout: VectorLayout | None = None
    vectors: dict[constr(pattern=r"^[0-9a-f]{64}$"), common_types.VectorBundle] = Field(
        ...,
        description="object<chunk_id, VectorBundle>. 키 집합 = 입력 ChunkSet에서 level ∈ {0, 2}인 chunk_id 집합(부모 level 1 제외)",
    )
    cache_hits: int = Field(
        ...,
        description='청크 임베딩 캐시 H("embed", embedding_space_id, "document", embed_text) 적중 수(비용 계량)',
        ge=0,
    )
    stats: EmbedStats
