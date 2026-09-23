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

from pydantic import ConfigDict, Field, RootModel, constr

from rag_platform.contracts.contract_model import ContractModel

from .. import common_types
from .IndexCommit import backend_results as backend_results_1


class BackendResult(ContractModel):
    """
    바이블 §5.4 backend_results[] 한 항목. backend_id는 CollectionSpec.backends[].backend_id(플러그인 ID)
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    backend_id: common_types.PluginId = Field(..., description="예 index_backend.qdrant, index_backend.opensearch")
    backend_version: str = Field(
        ...,
        description="서버 버전 문자열(capabilities 보고값)",
        max_length=64,
        min_length=1,
    )
    physical_name: str = Field(
        ...,
        description="물리 컬렉션·인덱스 이름(바이블 §13.4: rag_vec_{hash12}, rag_lex_{hash12}, 테넌트 전용 _t_{tenant_id})",
        max_length=255,
        min_length=1,
    )
    alias: str = Field(
        ...,
        description="논리 alias(col_{collection_id}_vec / col_{collection_id}_lex). blue/green 중에는 아직 이 물리명을 가리키지 않을 수 있다",
        max_length=255,
        min_length=1,
    )
    upserted: int = Field(
        ...,
        description="이 커밋으로 upsert한 레코드 수(kind=upsert·status ok면 = record_count)",
        ge=0,
    )
    deleted: int = Field(
        ...,
        description="이 커밋이 삭제한 레코드 수(kind=delete의 delete_by_filter 또는 보상 삭제)",
        ge=0,
    )
    duration_ms: int = Field(..., description="이 백엔드에 대한 쓰기·플립·보상 호출 시간 합", ge=0)
    status: backend_results_1.Status


class Source(ContractModel):
    """
    detect 출력 SourceDocument 산출물(media_type application/vnd.rag.source-document+json, schema_version 동반; 바이블 §5.2·§4.1 index requires_lineage). index가 acl·metadata를 읽는 원천. 원본 바이트(sources/{blake3})가 아니다
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    uri: common_types.Uri = Field(..., description="s3:// 또는 file:// URI(오브젝트 키 규약 §13.3)")
    blake3: common_types.Hex64 = Field(..., description="산출물 바이트의 BLAKE3 콘텐츠 해시")
    media_type: common_types.MediaType = Field(..., description="application/vnd.rag.{kebab-name}+json 또는 원본 MIME")
    schema_type: Literal["SourceDocument"] = Field(
        ...,
        description="계약 산출물이면 PascalCase 타입명. 봉투 schema_type과 일치해야 로드",
        pattern="^[A-Z][A-Za-z0-9]*$",
    )
    schema_version: common_types.Semver | None = Field(None, description="계약 산출물이면 계약 버전")
    size_bytes: int = Field(..., description="바이트 크기(인라인 금지 검증·계량)", ge=0)
    stage_key: common_types.Hex64 | None = Field(None, description="생산 스테이지 멱등성 키(계보 자기 서술)")


class Parsed(ContractModel):
    """
    오브젝트 스토리지 산출물 참조. 오케스트레이터 경계를 넘는 유일한 페이로드(바이블 §4.1, §5.3).
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    uri: common_types.Uri = Field(..., description="s3:// 또는 file:// URI(오브젝트 키 규약 §13.3)")
    blake3: common_types.Hex64 = Field(..., description="산출물 바이트의 BLAKE3 콘텐츠 해시")
    media_type: common_types.MediaType = Field(..., description="application/vnd.rag.{kebab-name}+json 또는 원본 MIME")
    schema_type: Literal["ParsedDocument"] = Field(
        ...,
        description="계약 산출물이면 PascalCase 타입명. 봉투 schema_type과 일치해야 로드",
        pattern="^[A-Z][A-Za-z0-9]*$",
    )
    schema_version: common_types.Semver | None = Field(None, description="계약 산출물이면 계약 버전")
    size_bytes: int = Field(..., description="바이트 크기(인라인 금지 검증·계량)", ge=0)
    stage_key: common_types.Hex64 | None = Field(None, description="생산 스테이지 멱등성 키(계보 자기 서술)")


class Normalized(ContractModel):
    """
    오브젝트 스토리지 산출물 참조. 오케스트레이터 경계를 넘는 유일한 페이로드(바이블 §4.1, §5.3).
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
    schema_version: common_types.Semver | None = Field(None, description="계약 산출물이면 계약 버전")
    size_bytes: int = Field(..., description="바이트 크기(인라인 금지 검증·계량)", ge=0)
    stage_key: common_types.Hex64 | None = Field(None, description="생산 스테이지 멱등성 키(계보 자기 서술)")


class ChunkSet(ContractModel):
    """
    오브젝트 스토리지 산출물 참조. 오케스트레이터 경계를 넘는 유일한 페이로드(바이블 §4.1, §5.3).
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    uri: common_types.Uri = Field(..., description="s3:// 또는 file:// URI(오브젝트 키 규약 §13.3)")
    blake3: common_types.Hex64 = Field(..., description="산출물 바이트의 BLAKE3 콘텐츠 해시")
    media_type: common_types.MediaType = Field(..., description="application/vnd.rag.{kebab-name}+json 또는 원본 MIME")
    schema_type: Literal["ChunkSet"] = Field(
        ...,
        description="계약 산출물이면 PascalCase 타입명. 봉투 schema_type과 일치해야 로드",
        pattern="^[A-Z][A-Za-z0-9]*$",
    )
    schema_version: common_types.Semver | None = Field(None, description="계약 산출물이면 계약 버전")
    size_bytes: int = Field(..., description="바이트 크기(인라인 금지 검증·계량)", ge=0)
    stage_key: common_types.Hex64 | None = Field(None, description="생산 스테이지 멱등성 키(계보 자기 서술)")


class Enriched(ContractModel):
    """
    오브젝트 스토리지 산출물 참조. 오케스트레이터 경계를 넘는 유일한 페이로드(바이블 §4.1, §5.3).
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    uri: common_types.Uri = Field(..., description="s3:// 또는 file:// URI(오브젝트 키 규약 §13.3)")
    blake3: common_types.Hex64 = Field(..., description="산출물 바이트의 BLAKE3 콘텐츠 해시")
    media_type: common_types.MediaType = Field(..., description="application/vnd.rag.{kebab-name}+json 또는 원본 MIME")
    schema_type: Literal["EnrichedChunkSet"] = Field(
        ...,
        description="계약 산출물이면 PascalCase 타입명. 봉투 schema_type과 일치해야 로드",
        pattern="^[A-Z][A-Za-z0-9]*$",
    )
    schema_version: common_types.Semver | None = Field(None, description="계약 산출물이면 계약 버전")
    size_bytes: int = Field(..., description="바이트 크기(인라인 금지 검증·계량)", ge=0)
    stage_key: common_types.Hex64 | None = Field(None, description="생산 스테이지 멱등성 키(계보 자기 서술)")


class Embedded(ContractModel):
    """
    오브젝트 스토리지 산출물 참조. 오케스트레이터 경계를 넘는 유일한 페이로드(바이블 §4.1, §5.3).
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    uri: common_types.Uri = Field(..., description="s3:// 또는 file:// URI(오브젝트 키 규약 §13.3)")
    blake3: common_types.Hex64 = Field(..., description="산출물 바이트의 BLAKE3 콘텐츠 해시")
    media_type: common_types.MediaType = Field(..., description="application/vnd.rag.{kebab-name}+json 또는 원본 MIME")
    schema_type: Literal["EmbeddedChunkSet"] = Field(
        ...,
        description="계약 산출물이면 PascalCase 타입명. 봉투 schema_type과 일치해야 로드",
        pattern="^[A-Z][A-Za-z0-9]*$",
    )
    schema_version: common_types.Semver | None = Field(None, description="계약 산출물이면 계약 버전")
    size_bytes: int = Field(..., description="바이트 크기(인라인 금지 검증·계량)", ge=0)
    stage_key: common_types.Hex64 | None = Field(None, description="생산 스테이지 멱등성 키(계보 자기 서술)")


class CommitArtifactRefs(ContractModel):
    """
    바이블 §5.4 artifact_refs {source, parsed, normalized, chunk_set, enriched, embedded} — 재적재(replay) 복구 1순위. lineage_refs와 같은 키·같은 값. 여섯 키 모두 계약 산출물이며 키별 schema_type은 00 §3.2 대응표와 1:1(const). 원본 바이트는 source가 가리키는 SourceDocument.artifact(02) 또는 ParsedDocument.source_ref(03)로 도달한다
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    source: Source | None = Field(
        None,
        description="detect 출력 SourceDocument 산출물(media_type application/vnd.rag.source-document+json, schema_version 동반; 바이블 §5.2·§4.1 index requires_lineage). index가 acl·metadata를 읽는 원천. 원본 바이트(sources/{blake3})가 아니다",
    )
    parsed: Parsed | None = Field(
        None,
        description="오브젝트 스토리지 산출물 참조. 오케스트레이터 경계를 넘는 유일한 페이로드(바이블 §4.1, §5.3).",
    )
    normalized: Normalized | None = Field(
        None,
        description="오브젝트 스토리지 산출물 참조. 오케스트레이터 경계를 넘는 유일한 페이로드(바이블 §4.1, §5.3).",
    )
    chunk_set: ChunkSet | None = Field(
        None,
        description="오브젝트 스토리지 산출물 참조. 오케스트레이터 경계를 넘는 유일한 페이로드(바이블 §4.1, §5.3).",
    )
    enriched: Enriched | None = Field(
        None,
        description="오브젝트 스토리지 산출물 참조. 오케스트레이터 경계를 넘는 유일한 페이로드(바이블 §4.1, §5.3).",
    )
    embedded: Embedded | None = Field(
        None,
        description="오브젝트 스토리지 산출물 참조. 오케스트레이터 경계를 넘는 유일한 페이로드(바이블 §4.1, §5.3).",
    )


class CommitStats(ContractModel):
    """
    바이블 §5.4 stats → usage_ledger(bytes_indexed, llm_tokens)·rag_index_bytes_total{vector}
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    bytes_dense: int = Field(..., description="dense 벡터 바이트(레코드 수 × dim × 4, fp32 기준)", ge=0)
    bytes_sparse: int = Field(..., description="sparse_learned·sparse_bm25 바이트 합", ge=0)
    bytes_lexical: int = Field(
        ...,
        description="index_text·context_prefix·lexical_terms 바이트(OpenSearch 적재분; lite는 0)",
        ge=0,
    )
    bytes_late_interaction: int = Field(..., description="late_interaction 멀티벡터 바이트(끔이면 0)", ge=0)
    leaf_count: int = Field(..., description="level=0 리프 수(색인됨)", ge=0)
    parent_count: int = Field(..., description="level=1 부모 수(색인 안 됨; ChunkTextStore 번들)", ge=0)
    llm_tokens: int = Field(
        ...,
        description="EnrichedChunkSet.budget_used.llm_tokens_in + llm_tokens_out",
        ge=0,
    )
    wall_seconds: float = Field(..., description="pending → 종결 상태까지 벽시계 초", ge=0.0)


class FailedAtStatus(StrEnum):
    """
    실패 시점 상태(종결·rolling_back 불가). reason=job_cancelled도 다섯 값 모두 가능(플립 구간 취소는 진행 중 플립 호출 완료 후 상태 경계에서 수용, 플립 후 모드 보상)
    """

    pending = "pending"
    vector_written = "vector_written"
    lexical_written = "lexical_written"
    flipping_lexical = "flipping_lexical"
    flipping_vector = "flipping_vector"
    committed = "committed"
    rolling_back = "rolling_back"
    rolled_back = "rolled_back"
    failed = "failed"
    pending_1 = "pending"
    vector_written_1 = "vector_written"
    lexical_written_1 = "lexical_written"
    flipping_lexical_1 = "flipping_lexical"
    flipping_vector_1 = "flipping_vector"


class DeletedCounts(RootModel[int]):
    root: int = Field(..., ge=0)


class Compensation(ContractModel):
    """
    바이블 §5.4 compensation. 플립 전 실패(pending~lexical_written)는 새 세대 삭제만(restored_generation=null), 플립 후 실패(flipping_*)는 previous_commit_id 세대 복원 후 새 세대 삭제(restored_generation=이전 세대). 취소(reason=job_cancelled)는 다섯 전종결 상태 모두에서 가능하며 같은 모드 규칙을 따른다(§3 규칙 (6); 바이블 §11.5 cancelling → cancelled는 보상 완료 전제)
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    reason: str = Field(
        ...,
        description="롤백 사유: 최종 error.code({stage}.{reason}, 13-error-model; 예 index.partial_commit — ADR-0026 예시와 같은 어휘) 또는 job_cancelled(취소 시그널, error 없음)",
        max_length=64,
        pattern="^[a-z][a-z0-9_]*(\\.[a-z][a-z0-9_]*)?$",
    )
    failed_at_status: FailedAtStatus = Field(
        ...,
        description="실패 시점 상태(종결·rolling_back 불가). reason=job_cancelled도 다섯 값 모두 가능(플립 구간 취소는 진행 중 플립 호출 완료 후 상태 경계에서 수용, 플립 후 모드 보상)",
    )
    deleted_counts: dict[constr(pattern=r"^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$"), DeletedCounts] = Field(
        ..., description="{backend_id: 삭제된 새 세대 레코드 수}(열린 객체, 14 §2.3)"
    )
    restored_generation: int | None = Field(
        ...,
        description="복원한 이전 세대(플립 후 실패이고 previous_commit_id가 있을 때만 non-null)",
        ge=1,
    )
    completed_at: common_types.DateTime = Field(..., description="보상 절차 종료 시각(성공·실패 무관)")


class IndexCommit(ContractModel):
    """
    index 사가의 출력이자 PostgreSQL index_commits 원장 행(바이블 §5.4·§11.4·§13.1, ADR-0026). 한 문서 세대(index_generation)의 색인 결과 단위로 9단 CommitStatus, 세대 관계(previous_commit_id·supersedes_commit_ids·superseded_by), 재현성 지문, commit_hash, 백엔드별 결과, 재적재용 artifact_refs, 보상 기록을 담는다. 정본은 원장 행이며 오브젝트 스토리지 산출물이 아니다. 공용 타입·열거는 urn:rag:schema:common-types:1 을 참조한다. embedding_space_ids는 urn:rag:schema:embedded-chunk-set:1#/$defs/EmbeddingSpaceIds 와 같은 정의의 사본을 자기 $defs에 둔다(계약 간 교차 $ref 회피 — 00 §2·15 결정; CI가 두 정의의 동치를 대조한다). artifact_refs.source·lineage_refs.source는 detect 출력 SourceDocument 산출물 참조다(원본 바이트가 아님; 00 §3.2 대응표). 소유 문서: docs/03-contracts/08-index-commit.md
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    schema_version: str = Field(
        ...,
        description='계약 버전. 초기 "1.0.0"',
        pattern="^1.(0|[1-9]d*).(0|[1-9]d*)$",
    )
    schema_type: Literal["IndexCommit"] = Field(..., description="PascalCase 타입명")
    tenant_id: common_types.Ulid = Field(..., description="보안 삼중항 1")
    collection_id: common_types.Ulid = Field(..., description="보안 삼중항 2(수집 측 단수)")
    producer: common_types.Producer = Field(
        ...,
        description="index 사가 지문. plugin_id는 플랫폼 합성 index_backend.pipeline, image_digest는 null. 백엔드 버전은 backend_results[].backend_version",
    )
    quality: common_types.Quality = Field(..., description="입력 EmbeddedChunkSet.quality 전파(kind=delete는 full)")
    warnings: list[common_types.Warning] = Field(
        ...,
        description="품질 삼중항 2. 콘텐츠 미포함. v1 카탈로그에 index.* 경고 코드가 없어 보통 빈 배열",
        max_length=64,
    )
    created_at: common_types.DateTime = Field(..., description="원장 행 INSERT 시각(= started_at)")
    lineage_refs: common_types.LineageRefs = Field(
        ...,
        description="kind=upsert면 {source, parsed, normalized, chunk_set, enriched, embedded} 6키 전부, kind=delete면 빈 객체. artifact_refs와 같은 값",
    )
    commit_id: common_types.Ulid = Field(
        ...,
        description="워크플로우가 1회 발급(액티비티 재시도에 불변, 바이블 §11.4 (6))",
    )
    document_id: common_types.Ulid
    doc_version: common_types.Hex64 = Field(
        ...,
        description="= SourceDocument.content_hash(ADR-0005). kind=delete면 삭제 시점 documents.current_doc_version",
    )
    job_id: common_types.Ulid = Field(..., description="이 커밋을 만든 잡(jobs.index_commit_id 역참조)")
    kind: common_types.CommitKind = Field(..., description="upsert(새 세대 적재) / delete(tombstone, record_count=0)")
    previous_commit_id: common_types.Ulid | None = Field(
        ...,
        description="세대 할당 시점 documents.current_commit_id(없으면 null). 플립 후 보상이 복원하는 세대의 커밋",
    )
    supersedes_commit_ids: list[common_types.Ulid] = Field(
        ...,
        description="이 커밋이 committed가 될 때 is_current=false로 전환되거나 물리 삭제 대상이 되는 같은 문서의 이전 커밋. previous_commit_id(non-null)를 포함",
        max_length=64,
    )
    superseded_by: common_types.Ulid | None = Field(
        None,
        description="선택(N, null 허용 — 바이블 §5.4 표기 string(ulid) | null, 00 §8.1 4행). 이 커밋을 대체한 다음 커밋. status=committed 행에만 값이 있으며 다음 커밋의 committed 트랜잭션(재색인 모드 A는 ledger.advance_pointers)에서 기록된다",
    )
    status: common_types.CommitStatus = Field(
        ...,
        description="사가 상태 9단(바이블 §11.4). flipping_lexical·flipping_vector가 플립 실패 지점을 남긴다",
    )
    index_generation: int = Field(
        ...,
        description="문서 단위 단조 증가. documents 행 FOR UPDATE 잠금 아래 그 문서의 max(index_commits.index_generation) + 1로 할당(current_generation + 1 아님; 롤백·폐기된 세대 번호 재사용 없음, 02-architecture/06 §2.5·§3.2). record_id 합성 요소",
        ge=1,
    )
    profile_id: str = Field(
        ...,
        description="kebab-case(바이블 §6.1)",
        max_length=64,
        pattern="^[a-z][a-z0-9]*(-[a-z0-9]+)*$",
    )
    profile_hash: common_types.Hex64 = Field(
        ...,
        description='H("profile", canonical_json(해소된 프로파일)). 커밋 시점 CollectionSpec.profile_hash',
    )
    parser_fingerprint_hash: common_types.Hex64 = Field(
        ...,
        description='H("parser", parser_id, parser_version, ",".join(model_ids), sidecar_image_digest or "", profile_option)(바이블 §6.2). 재현성 조건 1',
    )
    normalizer_fingerprint: common_types.Hex64 = Field(
        ...,
        description='H("normalizer", plugin_id, plugin_version, config_hash, analyzer_id, dictionary_hash, pii_policy, pii_detector_version)',
    )
    chunker_config_hash: common_types.Hex64 = Field(
        ...,
        description='H("config", canonical_json(chunker config)). chunk_id 결합 요소',
    )
    enricher_fingerprint: common_types.Hex64 = Field(..., description="= EnrichedChunkSet.enricher_fingerprint")
    embedder_fingerprint: common_types.Hex64 = Field(
        ...,
        description="= EmbeddedChunkSet.embedder_fingerprint(서빙 이미지 digest 포함)",
    )
    embedding_space_ids: common_types.EmbeddingSpaceIds = Field(
        ...,
        description="= EmbeddedChunkSet.embedding_space_ids 복사(07 §2.2 정본과 동일한 사본 $defs; index-record·collection-spec과 같은 방식, CI 동치 대조). {dense, sparse_learned | sparse_bm25, late_interaction?}",
    )
    embedding_profile_hash: common_types.Hex64 = Field(
        ...,
        description='H("spaces", sorted name=id). Qdrant 물리 컬렉션 rag_vec_{[:12]} 결정',
    )
    analyzer_id: str = Field(
        ...,
        description="{engine}:{version}:{dictionary}(바이블 §6.1). 변경 시 렉시컬 재색인 트리거",
        max_length=128,
        pattern="^[a-z][a-z0-9-]*:[^:\\s]+:[^\\s]+$",
    )
    dictionary_hash: common_types.Hex64 = Field(
        ..., description='H("dict", sorted entries). 변경 시 렉시컬 재색인 트리거'
    )
    record_count: int = Field(
        ...,
        description="이 커밋이 적재한 IndexRecord 수(리프 + level 2 파생 항목; 부모 제외). kind=delete는 0",
        ge=0,
    )
    commit_hash: common_types.Hex64 = Field(
        ...,
        description='H("commit", profile_hash, *sorted(f"{chunk_id}:{content_hash}:{embed_text_hash}")). commit_id·세대·시각과 무관(브리프 §7 재현성)',
    )
    backend_results: list[BackendResult] = Field(
        ...,
        description="백엔드별 결과. 사가 진행에 따라 항목이 추가되며 backend_id는 유일",
        max_length=8,
    )
    artifact_refs: CommitArtifactRefs
    stats: CommitStats
    compensation: Compensation | None = Field(
        None,
        description="선택(N, null 허용). status ∈ {rolled_back, failed}에서만 non-null",
    )
    error: common_types.StageError | None = Field(
        None,
        description="선택(N, null 허용). 롤백·실패 사유(최종 인스턴스, retryable=false). 취소로 인한 롤백은 없음",
    )
    events_emitted: list[common_types.Ulid] = Field(
        ...,
        description="이 커밋의 상태 전이 트랜잭션에서 outbox에 기록한 event_id(index.commit.published / index.commit.rolled_back / index.consistency.mismatch)",
        max_length=32,
    )
    started_at: common_types.DateTime = Field(..., description="pending INSERT 시각")
    committed_at: common_types.DateTime | None = Field(None, description="선택(N). status=committed일 때만 존재")
    updated_at: common_types.DateTime | None = Field(
        None,
        description="선택(N). 이 문서 추가. 마지막 상태 전이(또는 superseded_by 기록) 시각",
    )
