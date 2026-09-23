"""GENERATED — do not edit; run `uv run python tools/contracts_gen.py` to regenerate.

Source of truth: schemas/*.schema.json (bible §5.1, §6.4, §12)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, RootModel, constr

from . import common_types


class LexicalTerm(RootModel[str]):
    root: str = Field(..., min_length=1)


class Tag(RootModel[str]):
    root: str = Field(..., max_length=128, min_length=1)


class Custom(RootModel[str]):
    root: str = Field(..., max_length=1024)


class EntityId(RootModel[str]):
    root: str = Field(..., min_length=1)


class Range2Item(RootModel[int]):
    root: int = Field(..., ge=0)


class Range2(RootModel[list[Range2Item]]):
    """
    [start, end) 0-based 정수 구간
    """

    root: list[Range2Item] = Field(..., description="[start, end) 0-based 정수 구간", max_length=2, min_length=2)


class Indice(RootModel[int]):
    root: int = Field(..., ge=0)


class Value(RootModel[float]):
    root: float = Field(..., gt=0.0)


class SparseVector(BaseModel):
    """
    Qdrant sparse named vector 본문. indices·values 길이 동일, indices 오름차순·중복 없음. vocab_id는 embedding_space_ids의 공간이 함의한다
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    indices: list[Indice] = Field(..., min_length=1)
    values: list[Value] = Field(..., min_length=1)


class LateInteractionItem(RootModel[list[float]]):
    root: list[float] = Field(..., min_length=1)


class IndexRecordVectors(BaseModel):
    """
    바이블 §5.4 IndexRecord.vectors {dense, sparse_learned?, sparse_bm25?, late_interaction?} — 백엔드 named vectors(VectorName). EmbeddedChunkSet과 달리 오프셋이 아닌 값 본문이다. level ∈ {0, 2}는 dense 필수 + sparse 하나 이상, item_kind=parent(vector_payload 저장 방식만)는 빈 객체
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    dense: list[float] | None = Field(
        None,
        description="L2 정규화 float 벡터, 길이 = 공간 dim(BGE-M3 1024). Qdrant dense(cosine)",
        min_length=1,
    )
    sparse_learned: SparseVector | None = Field(
        None,
        description="learned sparse(BGE-M3 lexical weights). Qdrant modifier none; channel=sparse",
    )
    sparse_bm25: SparseVector | None = Field(
        None,
        description="lite. 플랫폼 계산 BM25 TF 포화값(k1=1.2, b=0.75). Qdrant modifier idf; channel=lexical(ADR-0012)",
    )
    late_interaction: list[LateInteractionItem] | None = Field(
        None,
        description="토큰 벡터 행렬 [count, dim](KURE-v2 128d 후보). Qdrant MultiVectorConfig(MAX_SIM), m=0 옵션",
        min_length=1,
    )
    page_multivector: dict[str, Any] | None = Field(None, description="visual-pages 슬롯(별도 컬렉션; 미확정)")
    pooled_page_multivector: dict[str, Any] | None = Field(None, description="visual-pages 슬롯(미확정)")
    page_dense: dict[str, Any] | None = Field(None, description="visual-pages 슬롯(미확정)")


class IndexRecord(BaseModel):
    """
    index 스테이지가 EmbeddedChunkSet(EMB) + requires_lineage(EnrichedChunkSet ENR, ChunkSet CS, SourceDocument SRC) + 워크플로우 인자(IDX)에서 조립해 인덱스 백엔드에 쓰는 논리 레코드(바이블 §5.4). 리프 1개 = 레코드 1개(세대별). 물리 키 record_id = H("record", tenant_id, collection_id, document_id, str(index_generation), chunk_id), point_id = uuid5(NAMESPACE_RAG_CHUNK, record_id)(ADR-0004 v1.2, E17). payload는 필터·정렬·설명·리랭크 입력·인용 좌표·ACL 재검증에 필요한 것만 담고(32KB, text ≤ 8,192 UTF-8 바이트) 정본은 ChunkSet 산출물이다(ADR-0034). 봉투 없음. 공용 타입·열거는 urn:rag:schema:common-types:1 을 참조한다. 소유 문서: docs/03-contracts/07-embedded-chunk-set-and-index-record.md
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    schema_version: str | None = Field(
        None,
        description="선택(N). payload 기록 시점의 이 계약 버전(hydrate가 unknown 열거값 처리·업캐스트 판정에 참고; 바이블 §5.4 미등재, 미해결 이슈)",
        pattern="^1.(0|[1-9]d*).(0|[1-9]d*)$",
    )
    record_id: common_types.Hex64 = Field(
        ...,
        description='H("record", tenant_id, collection_id, document_id, str(index_generation), chunk_id) — 스코프·세대 합성 물리 키. OpenSearch _id. 원천 IDX',
    )
    point_id: common_types.Uuid = Field(
        ...,
        description='uuid5(NAMESPACE_RAG_CHUNK, record_id), NAMESPACE_RAG_CHUNK = uuid5(NAMESPACE_URL, "urn:rag:chunk") = 4198d3e2-bdc6-5334-b170-0d5490f26cc7. Qdrant 포인트 ID. 원천 IDX',
    )
    chunk_id: common_types.Hex64 = Field(
        ...,
        description="콘텐츠 주소 키(세대·스코프 무관). exclude_ids·commit_hash·평가 run·duplicates_of 기준. 원천 CS",
    )
    tenant_id: common_types.Ulid = Field(
        ...,
        description="보안 삼중항 1. 필수 사전 필터(Qdrant is_tenant=true, OpenSearch routing). 원천 봉투",
    )
    collection_id: common_types.Ulid = Field(..., description="보안 삼중항 2. 필수 사전 필터. 원천 봉투")
    document_id: common_types.Ulid = Field(..., description="삭제·부모 확장·상충 판정 키. 원천 봉투")
    doc_version: common_types.Hex64 = Field(..., description="= SourceDocument.content_hash. 원천 SRC")
    commit_id: common_types.Ulid = Field(
        ...,
        description="IndexCommit.commit_id — 사가 보상 키(delete_by_filter(commit_id)). 원천 IDX",
    )
    index_generation: int = Field(
        ...,
        description="문서 단위 단조 증가 세대(원장 documents 행 잠금 아래 할당). 원천 IDX",
        ge=1,
    )
    is_current: bool = Field(
        ...,
        description="적재 시 false, 커밋 플립(렉시컬 → 벡터) 시 true, 다음 세대 커밋 시 false(바이블 §11.4). 보안 불변식 (a) 필수 사전 필터. 원천 IDX",
    )
    item_kind: common_types.ItemKind = Field(..., description="전략 필터 item_kind IN :item_kinds. 원천 CS")
    level: common_types.ChunkLevel = Field(..., description="전략 필터 level IN :level_in. 원천 CS")
    parent_chunk_id: common_types.Hex64 | None = Field(
        ..., description="Y(nullable). 같은 세트 내 level+1 청크. 원천 CS"
    )
    ordinal: int = Field(..., description="부모 내 순서(비인덱스). 원천 CS", ge=0)
    tree_level: int | None = Field(None, description="선택. RAPTOR 트리 레벨(리프 0). 원천 CS", ge=0)
    vectors: IndexRecordVectors
    index_text: str | None = Field(
        None,
        description="조건(렉시컬 백엔드 대상이면 Y). Enrichment.index_text — BM25 입력(OpenSearch nori_index/nori_search). lite(Qdrant 단독)는 sparse_bm25 계산 입력으로만 쓰고 payload에 넣지 않는다. 원천 ENR",
    )
    lexical_terms: list[LexicalTerm] = Field(
        ...,
        description="Enrichment.keywords[].term 정렬·중복 제거(keyword 배열; Qdrant 한국어 키워드 필터·부스트). 원천 ENR",
    )
    text: str = Field(
        ...,
        description="표시 원문(Chunk.text) ≤ 8,192 UTF-8 바이트(바이트 검사는 Pydantic; maxLength 8192 코드포인트는 필요조건). 초과 시 §9 절단(블록 경계 우선; 마지막 block_ref의 char_end만 클리핑, original_char_*는 Chunk 값 불변) + text_truncated=true. 전문은 ChunkSet·ChunkTextStore. 원천 CS",
        max_length=8192,
    )
    text_preview: str = Field(
        ...,
        description="≤ 200자(MCP concise·디버그·CandidateSet.payload_slim). 원천 CS",
        max_length=200,
    )
    text_truncated: bool = Field(
        ...,
        description="text가 8,192 바이트 절단본이면 true(마지막 block_ref는 블록 중간에서 잘린 부분 ref일 수 있다, §9 규칙 2). 원천 CS(index 계산)",
    )
    context_prefix: str = Field(
        ...,
        description='Chunk.context_prefix.deterministic — 리랭크 입력(context_prefix + "\\n" + text)·팩 헤더 재생성. OpenSearch text(boost 0.5). 원천 CS',
    )
    block_refs: list[common_types.BlockRef] = Field(
        ...,
        description="인용 좌표(K1). char_*는 text 기준, original_char_*는 원문 Block.text 기준 코드포인트(바이블 §6.3)이며 절단(§9) 시에도 Chunk 값 그대로; 마지막 항목의 char_end == cp(text)(절단 여부 무관). hydrate가 읽어 pack이 segments·provenance 생성. level 0·1은 1개 이상. 원천 CS",
    )
    sentence_spans: list[Range2] = Field(..., description="text 기준 문장 구간. 원천 CS")
    table_ref: common_types.TableRef1 | None = Field(
        None,
        description="조건(item_kind ∈ {table, table_part}). Chunk.table_ref 복사. 원천 CS",
    )
    html_ref: common_types.ArtifactRef | None = Field(
        None,
        description="조건(item_kind ∈ {table, table_part}). 표 전체 HTML 파생물(= table_ref.html_ref; pack이 tables[].html 로드). 원천 CS",
    )
    title: str = Field(
        ...,
        description="문서 제목. 대체 순서: IngestRequest.metadata.title → ParsedDocument.metadata.title → 첫 heading level 0 → source_uri 마지막 경로 요소(대체값이 512 코드포인트를 넘으면 앞 512로 절단). 제약은 01 IngestMetadata.title·02 SourceMetadata.title과 동일(minLength 1, maxLength 512; 공용 $defs 승격 전까지 복제). 원천 SRC(metadata)",
        max_length=512,
        min_length=1,
    )
    heading_path: list[str] = Field(..., description="루트→현재 heading. keyword(첫 2단). 원천 CS")
    numbering_path: list[str] = Field(..., description="Chunk.numbering_path(없으면 빈 배열). 원천 CS")
    source_uri: common_types.Uri = Field(..., description="SourceDocument.source_uri. 원천 SRC")
    external_id: str | None = Field(None, description="선택. SourceDocument.external_id. 원천 SRC")
    doc_date: common_types.Date | None = Field(
        None,
        description="선택. metadata.doc_date(self-query·recency 부스트). 원천 SRC(metadata)",
    )
    doc_type: str | None = Field(
        None,
        description="선택. metadata.doc_type — snake_case keyword(01 IngestMetadata.doc_type·02 SourceMetadata.doc_type과 동일 패턴; 공용 $defs 승격 전까지 복제). 원천 SRC(metadata)",
        pattern="^[a-z][a-z0-9_]{0,63}$",
    )
    department: str | None = Field(
        None,
        description="선택. metadata.department(01·02와 동일 제약 minLength 1, maxLength 256). 원천 SRC(metadata)",
        max_length=256,
        min_length=1,
    )
    tags: list[Tag] | None = Field(
        None,
        description="선택. metadata.tags — 정확 일치 keyword(01·02와 동일 제약: 항목 1..128자, ≤ 64개, 중복 없음; 01 정규화가 순서 보존 중복 제거를 수행한 값을 그대로 투영). 원천 SRC(metadata)",
        max_length=64,
    )
    lang: common_types.Bcp47 = Field(..., description="Chunk.lang. 원천 CS")
    genre: common_types.Genre = Field(..., description="ChunkSet.genre_route. 원천 CS")
    custom: dict[constr(pattern=r"^[a-z][a-z0-9_]{0,63}$"), Custom | float | bool] | None = Field(
        None,
        description="선택. 컬렉션 filterable_fields 선언 키만(FilterableField custom.{key}) — 원천의 부분집합. 키·값 제약은 01 CustomMetadata·02 SourceMetadata.custom과 동일(키 ^[a-z][a-z0-9_]{0,63}$ ≤ 64개, 값 string ≤ 1,024 | number | boolean; 00 §8.2 열린 객체; 공용 $defs 승격 전까지 복제). 원천 SRC(metadata.custom)",
        max_length=64,
    )
    page_start: int | None = Field(
        ...,
        description="Y(nullable). min(block_refs[].page); 흐름 포맷은 null. 사용자 필터 page → page_start <= v <= page_end. 원천 CS(block_refs)",
        ge=1,
    )
    page_end: int | None = Field(
        ...,
        description="Y(nullable). max(block_refs[].page). 원천 CS(block_refs)",
        ge=1,
    )
    text_source: common_types.BlockSource = Field(..., description="청크 텍스트 출처 최저 등급(팩 [ocr] 표기). 원천 CS")
    ocr_confidence_min: float | None = Field(
        ...,
        description="Y(nullable). text_source ∈ {ocr, vlm}이면 non-null. 원천 CS",
        ge=0.0,
        le=1.0,
    )
    acl_allow: list[common_types.PrincipalString] = Field(
        ...,
        description="Acl.allow_principals 평탄화(문서 ACL, 모든 레벨 동일). 보안 불변식 (a). 원천 SRC(acl)",
        max_length=1024,
    )
    acl_deny: list[common_types.PrincipalString] | None = Field(
        None,
        description="선택. Acl.deny_principals 평탄화(항상 우선). 원천 SRC(acl)",
        max_length=1024,
    )
    acl_visibility: common_types.Visibility = Field(..., description="Acl.visibility. 원천 SRC(acl)")
    acl_classification: common_types.Classification = Field(
        ...,
        description="Acl.classification(부재 시 기본 internal). acl_classification <= :classification_max. 원천 SRC(acl)",
    )
    acl_embargo_until: common_types.DateTime | None = Field(
        None,
        description="선택(N | null; 계약 인스턴스는 생략·null 모두 허용, 00 §8.1 4행). Acl.embargo_until. 백엔드 payload(to_payload)에서만 명시적 null로 기록한다(IS NULL 필터). 원천 SRC(acl)",
    )
    acl_expires_at: common_types.DateTime | None = Field(
        None,
        description="선택(N | null; 계약 인스턴스는 생략·null 모두 허용). Acl.expires_at. 백엔드 payload에서만 명시적 null. 원천 SRC(acl)",
    )
    acl_hash: common_types.Hex64 = Field(
        ...,
        description='SourceDocument.acl_hash = H("acl", canonical_json(acl)). E9 회수 힌트 대조 키; E5 필수 보안 필드. 원천 SRC',
    )
    entity_ids: list[EntityId] | None = Field(
        None,
        description="선택. Enrichment.entities[].canonical_id(non-null) 정렬·중복 제거. 부스트(BoostKind entity). 원천 ENR",
    )
    content_hash: common_types.Hex64 = Field(
        ...,
        description="Chunk.content_hash = blake3_hex(utf8(Chunk.text)) — 절단 여부와 무관하게 원 청크 값(정합성 검사·commit_hash). 원천 CS",
    )
    token_count_primary: int = Field(
        ...,
        description="Chunk.token_counts[primary_tokenizer_id](패킹 사전 예산). 원천 CS",
        ge=0,
    )
    risk_score: float = Field(
        ...,
        description="Enrichment.risk_score(pack omitted.reason=risk_flagged 근거). 원천 ENR",
        ge=0.0,
        le=1.0,
    )
    pii_policy_applied: common_types.PiiPolicy = Field(..., description="ChunkSet.pii_policy_applied. 원천 CS")
    embedding_space_ids: common_types.EmbeddingSpaceIds = Field(
        ...,
        description="EmbeddedChunkSet.embedding_space_ids 복사(질의 시 공간 불일치 감지). 원천 EMB",
    )
    embedding_profile_hash: common_types.Hex64 = Field(
        ...,
        description="EmbeddedChunkSet.embedding_profile_hash 복사 = Qdrant 물리 컬렉션 rag_vec_{[:12]} 선택 근거. 원천 EMB",
    )
    analyzer_id: common_types.AnalyzerId = Field(
        ...,
        description="ChunkSet.analyzer_id 복사(R-10) — {engine}:{version}:{dictionary}(바이블 §6.1). 질의 analyzer_id 불일치 → degraded{channel.lexical, analyzer_mismatch}. 원천 CS",
    )
    dictionary_hash: common_types.Hex64 = Field(
        ..., description="ChunkSet.dictionary_hash(변경 시 렉시컬 재색인). 원천 CS"
    )
    chunk_set_blake3: common_types.Hex64 = Field(
        ...,
        description="lineage_refs.chunk_set.blake3 — 부모 텍스트 번들 derived/parent_texts/{chunk_set_blake3}.json 키(§13.2). 원천 CS(ArtifactRef.blake3)",
    )
    updated_at: common_types.DateTime = Field(..., description="레코드 기록·payload 갱신(ACL 갱신·플립) 시각. 원천 IDX")
