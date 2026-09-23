"""GENERATED — do not edit; run `uv run python tools/contracts_gen.py` to regenerate.

Source of truth: schemas/*.schema.json (bible §5.1, §6.4, §12)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, RootModel

from . import common_types


class ChunkerId(RootModel[str]):
    root: str = Field(
        ...,
        description="chunker 확장 지점의 plugin_id({extension_point}.{implementation}, 바이블 §6.1). 코어 구현 3종은 examples 참조",
        examples=[
            "chunker.structure_aware",
            "chunker.flat_text",
            "chunker.docling_hybrid_adapter",
        ],
        pattern="^chunker\\.[a-z][a-z0-9_]*$",
    )


class ChunkSetStats(BaseModel):
    """
    세트 통계(바이블 §5.4 stats). 각 값은 chunks[]에서 재계산한 값과 같아야 한다(불변식 C-7)
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    leaf_count: int = Field(..., description="level=0 청크 수", ge=0)
    parent_count: int = Field(..., description="level=1 청크 수", ge=0)
    table_part_count: int = Field(..., description="item_kind=table_part 청크 수", ge=0)
    summary_count: int = Field(..., description="item_kind=summary 청크 수(level 2)", ge=0)
    oversized_blocks: int = Field(
        ...,
        description="leaf_max_tokens 초과로 강제 분할된 블록 수(= chunk.block_oversized 경고 수)",
        ge=0,
    )


class TokenBudgets(BaseModel):
    """
    청킹에 적용된 토큰 예산(primary_tokenizer_id 기준). 프로파일 ingest.chunk.* 값의 스냅숏
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    leaf_max_tokens: int = Field(..., description="리프 상한(기본 512)", ge=1)
    parent_max_tokens: int = Field(..., description="부모 상한(기본 2048)", ge=1)
    merge_min_tokens: int = Field(..., description="동일 heading 병합 하한(기본 64)", ge=0)
    table_row_group_tokens: int = Field(..., description="표 행 그룹 예산(기본 256)", ge=1)
    fallback_max_tokens: int | None = Field(
        None,
        description="N. ingest.chunk.fallback.max_tokens(기본 384). chunker_id = chunker.flat_text이면 불변식 (2)의 리프 상한",
        ge=1,
    )
    fallback_overlap_ratio: float | None = Field(
        None,
        description="N. ingest.chunk.fallback_overlap_ratio(기본 0.10). flat_text 오버랩(§8)",
        ge=0.0,
        le=1.0,
    )
    sentence_window_n: int | None = Field(
        None,
        description="N. ingest.chunk.sentence_window_n(기본 2). window.before/after_chunk_ids 길이 상한(C-13)",
        ge=0,
    )


class LineageRefs(BaseModel):
    """
    상류 산출물 참조 {source, parsed, normalized}. 자기 자신(chunk_set)과 하류 키(enriched, embedded) 미포함(C-1, 00 I-7); recount 출력은 입력 그대로
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    source: common_types.ArtifactRef
    parsed: common_types.ArtifactRef
    normalized: common_types.ArtifactRef
    chunk_set: common_types.ArtifactRef | None = None
    enriched: common_types.ArtifactRef | None = None
    embedded: common_types.ArtifactRef | None = None


class NormalizedRef(BaseModel):
    """
    입력 NormalizedDocument 산출물. lineage_refs.normalized와 같은 blake3
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    uri: common_types.Uri = Field(..., description="s3:// 또는 file:// URI(오브젝트 키 규약 §13.3)")
    blake3: common_types.Hex64 = Field(..., description="산출물 바이트의 BLAKE3 콘텐츠 해시")
    media_type: common_types.MediaType = Field(..., description="application/vnd.rag.{kebab-name}+json 또는 원본 MIME")
    schema_type: Literal["NormalizedDocument"] = Field(
        ...,
        description="계약 산출물이면 PascalCase 타입명. 봉투 schema_type과 일치해야 로드",
        pattern="^[A-Z][A-Za-z0-9]*$",
    )
    schema_version: common_types.Semver = Field(..., description="계약 산출물이면 계약 버전")
    size_bytes: int = Field(..., description="바이트 크기(인라인 금지 검증·계량)", ge=0)
    stage_key: common_types.Hex64 | None = Field(None, description="생산 스테이지 멱등성 키(계보 자기 서술)")


class ChunkSet(BaseModel):
    """
    chunk·recount 스테이지의 출력(바이블 §5.4). 한 문서 버전의 리프(level 0)·부모(level 1)·상위 파생(level 2) 청크를 한 세트에 담는다. Chunk·BlockRef·TokenCounts·ArtifactRef·Producer·Warning·LineageRefs와 모든 열거는 urn:rag:schema:common-types:1의 $defs를 참조하며 재정의하지 않는다. 소유 문서: docs/03-contracts/05-chunk-set.md.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    schema_version: str = Field(
        ...,
        description='계약 버전. 초기 "1.0.0"',
        pattern="^1.(0|[1-9]d*).(0|[1-9]d*)$",
    )
    schema_type: Literal["ChunkSet"] = Field(
        ..., description="PascalCase 타입명. ArtifactRef.schema_type와 일치해야 로드"
    )
    tenant_id: common_types.Ulid = Field(..., description="보안 삼중항 1")
    collection_id: common_types.Ulid = Field(..., description="보안 삼중항 2(수집 측 단수)")
    producer: common_types.Producer = Field(
        ...,
        description="이 산출물을 마지막으로 쓴 스테이지의 재현성 지문(chunk 출력은 chunker 플러그인, recount 출력은 token_counter 플러그인)",
    )
    quality: common_types.Quality = Field(
        ...,
        description="품질 삼중항 1. degraded ⇔ 입력 NormalizedDocument.quality == degraded 또는 warnings가 비어 있지 않음(C-18; 바이블 §4.1 부분 성공 규약)",
    )
    warnings: list[common_types.Warning] = Field(
        ...,
        description="품질 삼중항 2. chunk.block_oversized 등 경고 코드(빈 배열 허용)",
    )
    created_at: common_types.DateTime = Field(..., description="RFC 3339 UTC")
    lineage_refs: LineageRefs = Field(
        ...,
        description="상류 산출물 참조 {source, parsed, normalized}. 자기 자신(chunk_set)과 하류 키(enriched, embedded) 미포함(C-1, 00 I-7); recount 출력은 입력 그대로",
    )
    chunk_set_id: common_types.Ulid = Field(..., description="세트 발급형 ID. recount는 보존한다")
    document_id: common_types.Ulid = Field(..., description="문서 ID(봉투 스코프)")
    doc_version: common_types.Hex64 = Field(
        ...,
        description="= 원본 바이트 content_hash(ADR-0005). chunk_id 결합식의 첫 part",
    )
    normalized_ref: NormalizedRef = Field(
        ...,
        description="입력 NormalizedDocument 산출물. lineage_refs.normalized와 같은 blake3",
    )
    document_hash: common_types.Hex64 = Field(..., description="= normalized_ref.blake3")
    chunker_id: ChunkerId = Field(
        ...,
        description="청커 플러그인 ID(코어: chunker.structure_aware, chunker.flat_text, chunker.docling_hybrid_adapter)",
    )
    chunker_config_hash: common_types.Hex64 = Field(
        ...,
        description='H("config", canonical_json(config)). chunk_id 결합식의 두 번째 part',
    )
    primary_tokenizer_id: common_types.TokenizerId = Field(
        ..., description="예산 토크나이저(기본 hf:BAAI/bge-m3). 불변식 (2)의 기준"
    )
    secondary_tokenizer_ids: list[common_types.TokenizerId] = Field(
        ...,
        description="병기 토크나이저(기본 [tiktoken:o200k_base]). recount가 추가한 tokenizer_id도 여기에 누적된다",
    )
    genre_route: common_types.Genre = Field(..., description="적용된 장르 규칙(genre_rules 키)")
    analyzer_id: common_types.AnalyzerId = Field(..., description="NormalizedDocument.analyzer_id 전파")
    dictionary_hash: common_types.Hex64 = Field(..., description="NormalizedDocument.dictionary_hash 전파")
    language: common_types.Bcp47 = Field(..., description="NormalizedDocument.language 전파(문서 주 언어)")
    pii_policy_applied: common_types.PiiPolicy = Field(
        ..., description="NormalizedDocument.pii_report.policy_applied 전파"
    )
    stats: ChunkSetStats
    token_budgets: TokenBudgets | None = Field(
        None,
        description="선택(N). 청킹에 적용된 토큰 예산 스냅숏(프로파일 ingest.chunk.*). 있으면 불변식 (2)·C-6을 프로파일 없이 검증할 수 있다. 바이블 §5.4 미등재(미해결 이슈 5)",
    )
    chunks: list[common_types.Chunk] = Field(
        ...,
        description="리프·부모·표·요약 모두. 세트 상한 50,000(초과는 chunk.count_exceeded)",
        max_length=50000,
    )
