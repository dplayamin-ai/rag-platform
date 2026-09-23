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

from pydantic import ConfigDict, Field, RootModel

from rag_platform.contracts.contract_model import ContractModel

from .. import common_types
from .CollectionSpec import backends as backends_1


class FilterableField(RootModel[str]):
    root: str = Field(..., max_length=64, pattern="^custom\\.[a-z0-9_]+$")


class MappingVersion(RootModel[str]):
    root: str = Field(
        ...,
        description='렉시컬 인덱스 매핑 버전(04-pipelines/13 §5.1 템플릿 _meta.mapping_version; 십진 문자열, 선행 0 금지). 매핑·분석기 설정 변경마다 증가하며 lexical_profile_hash 를 바꾼다(14 §6.3). 예 "1"',
        max_length=16,
        pattern="^[1-9][0-9]*$",
    )


class MaxGrade(StrEnum):
    """
    허용 최고 등급. PluginMeta.license_grade <= max_grade
    """

    A = "A"
    B = "B"
    C = "C"
    D = "D"
    X = "X"
    A_1 = "A"
    B_1 = "B"
    C_1 = "C"
    D_1 = "D"


class TerritoryItem(RootModel[str]):
    root: str = Field(..., pattern="^[A-Z]{2}$")


class LicensePolicy(ContractModel):
    """
    바이블 §5.6 CollectionSpec.license_policy·Profile.license_policy. max_grade는 §5.7 나열 순 비교(A<B<C<D), X(사용 비허가)는 상한이 될 수 없다
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    max_grade: MaxGrade = Field(..., description="허용 최고 등급. PluginMeta.license_grade <= max_grade")
    territory: list[TerritoryItem] = Field(
        ...,
        description="배포 지역 ISO 3166-1 alpha-2. PluginMeta.territory가 비어 있지 않으면 이 값 전부를 포함해야 한다(ADR-0001)",
        min_length=1,
    )


class CollectionStats(ContractModel):
    """
    바이블 §5.6 stats. 현재 세대(is_current=true) 기준
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    document_count: int = Field(..., ge=0)
    leaf_count: int = Field(
        ...,
        description="level=0 레코드 수. TieringPolicy.shard_key_threshold_chunks 판정 입력(테넌트 합산)",
        ge=0,
    )
    parent_count: int = Field(..., description="level=1 부모 수(ChunkTextStore 번들 항목)", ge=0)
    bytes_dense: int = Field(..., ge=0)
    bytes_sparse: int = Field(..., ge=0)
    bytes_lexical: int = Field(..., description="렉시컬 백엔드 저장 바이트. lite(Qdrant 단독)는 0", ge=0)


class CollectionBackend(ContractModel):
    """
    바이블 §5.6 backends[] 한 항목. IndexCommit.backend_results[].backend_id·physical_name·alias의 원천
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    backend_id: common_types.PluginId = Field(
        ..., description="index_backend.{implementation}. 예 index_backend.qdrant"
    )
    role: backends_1.Role
    physical_name: str = Field(
        ...,
        description="물리 컬렉션·인덱스 이름(§13.4: rag_vec_{hash12}, rag_lex_{hash12}, 테넌트 전용 _t_{tenant_id} 접미)",
        max_length=255,
        pattern="^[a-z][a-z0-9_]*$",
    )
    alias: str = Field(
        ...,
        description="논리 alias col_{collection_id}_{vec|lex}(§13.4). blue/green 교체 단위",
        max_length=255,
        pattern="^col_[0-9A-HJKMNP-TV-Z]{26}_[a-z]+$",
    )


class CollectionPolicies(ContractModel):
    """
    바이블 §5.6 policies. tenants.policies와 AND로 판정
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    pii_policy: common_types.PiiPolicy = Field(
        ...,
        description="normalize 기본 정책. IngestRequest.pii_policy가 있으면 더 엄격한 쪽",
    )
    pii_tokenize_mode: common_types.PiiTokenizeMode = Field(
        ..., description="pii_policy=tokenize일 때 hash | encrypt(OpenBao DEK)"
    )
    llm_enrichment_allowed: bool = Field(..., description="LLM 보강 허용(O-05). 테넌트 정책과 AND")
    allow_distribution_documents: bool = Field(
        ...,
        description="배포용 HWP 텍스트 전용 파싱 허용(quality=degraded, O-07). 테넌트 정책과 AND",
    )
    enrichment_budget_tokens: int = Field(
        ..., description="문서당 LLM 보강 토큰 예산(ADR-0016). 0 = LLM 보강 없음", ge=0
    )
    corpus_multiplier_max: float = Field(
        ...,
        description="코퍼스 대비 LLM 보강 생성 토큰 상한 배수(초과 시 잡 partial, ADR-0016)",
        ge=1.0,
    )


class CollectionSpec(ContractModel):
    """
    컬렉션 레지스트리 행(바이블 §5.6). 관리 API가 생산하고 plan·index·프로파일 검증기가 소비한다. 컬렉션은 정확히 하나의 profile_hash·embedding_profile_hash·analyzer_id·dictionary_hash에 바인딩되며 값 변경은 blue/green 재색인이다. 렉시컬 백엔드가 있으면 lexical_profile_hash = H("lex", analyzer_id, dictionary_hash, mapping_version)(§6.2)와 그 입력 mapping_version 을 함께 기록한다(선택 N, 이 문서 추가). 봉투 없음. 공용 타입·열거는 urn:rag:schema:common-types:1 을 참조하고, embedding_space_ids는 urn:rag:schema:embedded-chunk-set:1#/$defs/EmbeddingSpaceIds 와 같은 정의의 사본을 자기 $defs에 둔다(계약 간 교차 $ref 회피; CI가 두 정의의 동치를 대조한다). 소유 문서: docs/03-contracts/15-collection-profile-and-policy-contracts.md
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    schema_version: common_types.Semver = Field(..., description='계약 버전. 초기 "1.0.0"')
    schema_type: Literal["CollectionSpec"] | None = Field(
        None,
        description="선택(N, 이 문서 추가). API 응답·산출물 식별용 PascalCase 타입명",
    )
    collection_id: common_types.Ulid = Field(..., description="발급형 ID(§6.1). 보안 삼중항 2")
    tenant_id: common_types.Ulid = Field(..., description="소유 테넌트. 보안 삼중항 1")
    name: str = Field(
        ...,
        description="테넌트 내 표시 이름(유일성은 테넌트 스코프, 관리 API가 강제)",
        max_length=128,
        min_length=1,
    )
    profile_id: common_types.ProfileId = Field(..., description="바인딩된 프로파일 ID(kebab-case, §6.1)")
    profile_hash: common_types.Hex64 = Field(
        ...,
        description='H("profile", canonical_json(해소된 프로파일)). 컬렉션은 정확히 하나의 프로파일 해시에 바인딩(§5.6)',
    )
    embedding_space_ids: common_types.EmbeddingSpaceIds = Field(
        ...,
        description='{dense, sparse_learned?, sparse_bm25?, late_interaction?} 각 값은 H("space", model_id, revision, str(dim), str(normalized), prompt_hash, quantization, vocab_id or "")(라벨 제외 입력 7개, §6.2). EmbeddedChunkSet·IndexRecord와 동일 값',
    )
    embedding_profile_hash: common_types.Hex64 = Field(
        ...,
        description='H("spaces", *sorted(name=space_id)). Qdrant 물리 컬렉션 rag_vec_{[:12]} 결정(§13.4)',
    )
    analyzer_id: common_types.AnalyzerId = Field(
        ...,
        description="{engine}:{version}:{dictionary}(§6.1). 색인·질의 동일 값이어야 BM25 자기 일관",
    )
    dictionary_hash: common_types.Hex64 = Field(
        ...,
        description='H("dict", *sorted(UserDictEntry 정규화 행)). 변경 → 렉시컬 재색인 제안(§14 dictionary)',
    )
    dictionary_ref: common_types.Uri = Field(
        ...,
        description="사용자 사전 스냅샷 산출물 URI(tenants/{tenant_id}/derived/dictionaries/{blake3[:2]}/{blake3}.json). 바이블 §5.6 타입 string",
    )
    mapping_version: MappingVersion | None = Field(
        None,
        description="선택(N, 이 문서 추가; 바이블 §5.6 minor 제안). 렉시컬 인덱스 매핑·분석기 설정 버전(04-pipelines/13 §5.1 인덱스 템플릿 _meta.mapping_version). lexical_profile_hash 의 세 번째 입력. role=lexical 백엔드가 있으면 lexical_profile_hash 와 함께 존재(C-7)",
    )
    lexical_profile_hash: common_types.Hex64 | None = Field(
        None,
        description='선택(N, 이 문서 추가; 바이블 §5.6 minor 제안). H("lex", analyzer_id, dictionary_hash, mapping_version)(§6.2). OpenSearch 물리 인덱스 rag_lex_{[:12]}(§13.4; IndexCommit.backend_results[].physical_name)와 재색인 범위 판정(14 §6.3, 16 §6.2)의 입력. role=lexical 백엔드가 있으면 mapping_version 과 함께 존재하고 lite(Qdrant 단독)는 둘 다 생략(C-7)',
    )
    tenant_isolation_tier: common_types.TenantIsolationTier = Field(
        ..., description="현재 물리 배치 등급(§10.4). 승격은 tier_promotion 잡(E15)"
    )
    backends: list[CollectionBackend] = Field(
        ...,
        description="백엔드별 물리명·alias. backend_id 유일, role=vector 정확히 1개",
        max_length=8,
        min_length=1,
    )
    policies: CollectionPolicies = Field(
        ...,
        description="컬렉션 정책(테넌트 정책과 AND: llm_enrichment_allowed·allow_distribution_documents는 둘 다 참일 때만 유효)",
    )
    filterable_fields: list[FilterableField] = Field(
        ...,
        description="FilterNode.field 로 허용되는 custom.* 키 화이트리스트(§5.7 FilterableField). 고정 필드는 항상 허용",
        max_length=64,
    )
    license_policy: LicensePolicy = Field(
        ...,
        description="이 컬렉션에서 로딩 가능한 플러그인·모델의 라이선스 상한(ADR-0001)",
    )
    calibration_ref: str | None = Field(
        None,
        description="calibrations 행 참조(confidence_tier·tau 보정). 미보정이면 null 또는 생략",
        max_length=128,
    )
    stats: CollectionStats = Field(
        ...,
        description="현재 세대 기준 집계(consistency_check·tier_promotion 판정 입력)",
    )
    created_at: common_types.DateTime
    updated_at: common_types.DateTime
