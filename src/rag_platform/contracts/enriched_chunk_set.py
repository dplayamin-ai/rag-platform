"""GENERATED — do not edit; run `uv run python tools/contracts_gen.py` to regenerate.

Source of truth: schemas/*.schema.json (bible §5.1, §6.4, §12)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, constr

from . import common_types


class Source(BaseModel):
    """
    detect 출력 SourceDocument 계약 산출물(원본 바이트 참조 아님; 원본 바이트는 SourceDocument.artifact). index가 requires_lineage로 로드해 acl·metadata를 읽는다(00 §3.2·I-7, 바이블 §4.1·§5.2)
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
    enrich 출력의 상류 참조 {source, parsed, normalized, chunk_set}. source·parsed·normalized는 입력 ChunkSet.lineage_refs 복사, 각 키의 schema_type은 00 §3.2 대응표와 일치(I-7). 자기 자신(enriched)·하류(embedded) 금지
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    source: Source = Field(
        ...,
        description="detect 출력 SourceDocument 계약 산출물(원본 바이트 참조 아님; 원본 바이트는 SourceDocument.artifact). index가 requires_lineage로 로드해 acl·metadata를 읽는다(00 §3.2·I-7, 바이블 §4.1·§5.2)",
    )
    parsed: common_types.ArtifactRef
    normalized: common_types.ArtifactRef
    chunk_set: common_types.ArtifactRef
    enriched: common_types.ArtifactRef | None = None
    embedded: common_types.ArtifactRef | None = None


class ChunkSetRef(BaseModel):
    """
    원 ChunkSet 산출물(청크 본문 미복제). lineage_refs.chunk_set과 blake3 동일
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    uri: common_types.Uri = Field(..., description="s3:// 또는 file:// URI(오브젝트 키 규약 §13.3)")
    blake3: common_types.Hex64 = Field(..., description="산출물 바이트의 BLAKE3 콘텐츠 해시")
    media_type: Literal["application/vnd.rag.chunk-set+json"] = Field(
        ...,
        description="application/vnd.rag.{kebab-name}+json 또는 원본 MIME",
        pattern="^[a-z]+/[A-Za-z0-9!#$&^_.+-]+$",
    )
    schema_type: Literal["ChunkSet"] = Field(
        ...,
        description="계약 산출물이면 PascalCase 타입명. 봉투 schema_type과 일치해야 로드",
        pattern="^[A-Z][A-Za-z0-9]*$",
    )
    schema_version: common_types.Semver = Field(..., description="계약 산출물이면 계약 버전")
    size_bytes: int = Field(..., description="바이트 크기(인라인 금지 검증·계량)", ge=0)
    stage_key: common_types.Hex64 | None = Field(None, description="생산 스테이지 멱등성 키(계보 자기 서술)")


class BudgetUsed(BaseModel):
    """
    LLM 보강 비용 기록(바이블 §5.4 EnrichedChunkSet.budget_used 7키) → usage_ledger·JobStatus.cost. LLM 호출이 없으면 calls=0, provider·model_id=null, 토큰·비용 0. prompt_hashes는 이 문서가 추가한 선택 필드
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    provider: str | None = Field(
        ...,
        description="LLM 서빙 공급자(vllm, anthropic, openai_compatible 등 어댑터 식별자). 호출 없음이면 null",
        min_length=1,
    )
    model_id: common_types.ModelId | None = Field(..., description="{repo}@{revision}. 호출 없음이면 null")
    llm_tokens_in: int = Field(..., description="입력 토큰 합(캐시 적중 제외; 템플릿·문서 문맥 포함)", ge=0)
    llm_tokens_out: int = Field(..., ge=0)
    cost_usd: float = Field(..., ge=0.0)
    calls: int = Field(..., description="실제 LLM 호출 수(모든 산출물 종류 합, 캐시 적중 제외)", ge=0)
    budget_remaining_tokens: int = Field(
        ...,
        description="이 잡 종료 시점 컬렉션 enrichment_budget_tokens 잔여. 초과 종료면 0",
        ge=0,
    )
    prompt_hashes: dict[constr(pattern=r"^enricher\.[a-z][a-z0-9_]*$"), common_types.Hex64] | None = Field(
        None,
        description='선택(N). LLM 산출물 종류별 프롬프트 템플릿 해시 object<plugin_id, hex64>. 캐시 키 H("llm-enrich", model_id, prompt_hashes[plugin_id], embed_text) 재계산 입력. LLM 비활성이면 존재하지 않는다',
        min_length=1,
    )
    charged_tokens: int | None = Field(
        None,
        description="N(바이블 §5.4 1.3.0, AM-32). 예산 대조 기준 토큰 수(캐시 적중분 포함 여부는 llm_tokens_in 과 달리 프로파일 enrichment_budget_tokens 잔여 계산에 실제 청구된 값). LLM 비활성이면 존재하지 않는다",
        ge=0,
    )


class GeneratedPrefix(BaseModel):
    """
    LLM 생성 접두어 기록(O-05 슬롯). generated는 embed_text[len(deterministic)+1 : text_start_in_embed-1] 과 같다. 프롬프트 해시는 budget_used.prompt_hashes["enricher.llm_context_prefix"]
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    generated: str = Field(
        ...,
        description="LLM 문맥(NFC). text에 포함되지 않는다. 규칙 2(b)면 Enrichment.summary와 같다",
        min_length=1,
    )
    generated_by: common_types.ModelId
    cache_hit: bool = Field(
        ...,
        description='H("llm-enrich", model_id, prompt_hash, embed_text)(규칙 2(b)는 section_text 키) 캐시 적중 여부(true면 budget_used.calls에 미계수). 한 요약을 공유하는 청크는 모두 같은 값',
    )


class EnrichStats(BaseModel):
    """
    바이블 §5.4 stats {chunks_enriched, llm_cache_hits, entities_total}
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    chunks_enriched: int = Field(..., description="= enrichments 키 수", ge=0)
    llm_cache_hits: int = Field(
        ...,
        description="모든 LLM 산출물 종류의 캐시 적중 수 합(키 조회 단위; ≥ generated_prefixes 중 cache_hit=true 인 고유 (generated, generated_by) 쌍 수)",
        ge=0,
    )
    entities_total: int = Field(..., description="= Σ len(enrichments[*].entities)", ge=0)
    chunks_partial: int | None = Field(None, description="선택(N). Enrichment.status=partial 인 청크 수", ge=0)


class EnrichedChunkSet(BaseModel):
    """
    enrich 스테이지 출력(바이블 §5.4). 청크 본문은 chunk_set_ref로 참조하고 enrichments(object<chunk_id, Enrichment>)만 담는다. 3-텍스트 규칙(ADR-0029): embed_text = deterministic + "\\n" + (generated + "\\n")? + text, index_text = prefix(lexical) + "\\n" + lexical_text (+ hypothetical_questions). LLM 보강은 기본 끔(ADR-0016). 공용 타입·열거는 urn:rag:schema:common-types:1 을 참조한다. 소유 문서: docs/03-contracts/06-enriched-chunk-set.md
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    schema_version: str = Field(
        ...,
        description='계약 버전. 초기 "1.0.0"',
        pattern="^1.(0|[1-9]d*).(0|[1-9]d*)$",
    )
    schema_type: Literal["EnrichedChunkSet"] = Field(
        ..., description="PascalCase 타입명. ArtifactRef.schema_type와 일치해야 로드"
    )
    tenant_id: common_types.Ulid = Field(..., description="보안 삼중항 1")
    collection_id: common_types.Ulid = Field(..., description="보안 삼중항 2(수집 측 단수)")
    producer: common_types.Producer = Field(
        ...,
        description="재현성 지문. plugin_id는 플랫폼 합성 보강기 enricher.pipeline, model_ids는 LLM·VLM 보강 모델(없으면 빈 배열). image_digest는 LLM 비활성(인프로세스)이면 null, LLM/VLM 활성(외부 서빙)이면 서빙 이미지 digest(00 I-20)",
    )
    quality: common_types.Quality = Field(
        ...,
        description="품질 삼중항 1. 입력 ChunkSet의 값을 전파(되돌리지 않음)하고 status=partial이면 degraded(allOf[1])",
    )
    warnings: list[common_types.Warning] = Field(
        ...,
        description="품질 삼중항 2. enrich.extractor_timeout(chunk_id 포함), enrich.budget_exceeded(세트당 1건), enrich.content_policy_violation(chunk_id 포함, 초안) 등 콘텐츠 미포함",
    )
    created_at: common_types.DateTime
    lineage_refs: LineageRefs = Field(
        ...,
        description="enrich 출력의 상류 참조 {source, parsed, normalized, chunk_set}. source·parsed·normalized는 입력 ChunkSet.lineage_refs 복사, 각 키의 schema_type은 00 §3.2 대응표와 일치(I-7). 자기 자신(enriched)·하류(embedded) 금지",
    )
    chunk_set_id: common_types.Ulid = Field(..., description="입력 ChunkSet.chunk_set_id 복사")
    document_id: common_types.Ulid
    doc_version: common_types.Hex64 = Field(..., description="= SourceDocument.content_hash(ADR-0005)")
    chunk_set_ref: ChunkSetRef = Field(
        ...,
        description="원 ChunkSet 산출물(청크 본문 미복제). lineage_refs.chunk_set과 blake3 동일",
    )
    enricher_fingerprint: common_types.Hex64 = Field(
        ...,
        description='H("enricher", *sorted(f"{plugin_id}@{plugin_version}:{config_hash}"), policy_hash)(바이블 §6.2). IndexCommit 재현성 조건이며 stage_key 입력은 producer 지문(fingerprint)이다',
    )
    policy_hash: common_types.Hex64 = Field(
        ...,
        description='컬렉션 보강 정책 해시. 초안 결합식 H("enrich-policy", canonical_json(policy))',
    )
    status: common_types.EnrichStatus = Field(
        ...,
        description="세트 단위. 예산 초과·추출기 타임아웃·콘텐츠 정책 거부가 하나라도 있으면 partial(그때 quality=degraded)",
    )
    budget_used: BudgetUsed
    enrichments: dict[constr(pattern=r"^[0-9a-f]{64}$"), common_types.Enrichment] = Field(
        ...,
        description="object<chunk_id, Enrichment>. 키 집합 = 입력 ChunkSet.chunks[].chunk_id 집합(모든 레벨)",
    )
    generated_prefixes: dict[constr(pattern=r"^[0-9a-f]{64}$"), GeneratedPrefix] | None = Field(
        None,
        description="선택(N). LLM 생성 접두어의 기록 object<chunk_id, GeneratedPrefix>. 키는 enrichments 키의 부분집합이며 LLM 비활성(budget_used.calls == 0 이고 stats.llm_cache_hits == 0)이면 존재하지 않는다. 규칙 2(b)에서는 같은 섹션의 청크가 요약 하나를 공유하므로 항목 수가 calls + llm_cache_hits를 넘을 수 있다 — E-7·E-10은 고유 (generated, generated_by) 쌍 수를 계수한다(Pydantic·셸 검사)",
    )
    stats: EnrichStats
