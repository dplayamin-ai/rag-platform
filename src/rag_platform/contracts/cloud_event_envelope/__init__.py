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

from pydantic import AnyUrl, ConfigDict, Field, RootModel

from rag_platform.contracts.contract_model import ContractModel

from .. import common_types, job_status
from . import (
    AuditDocumentAccessedData as AuditDocumentAccessedData_1,
    CollectionProfileChangedData as CollectionProfileChangedData_1,
)


class Type(StrEnum):
    """
    바이블 §5.7 이벤트 이름 카탈로그(domain.entity.action). CloudEventEnvelope.type. 1.3.0: tenant.policies.changed 추가(AM-38, 25종).
    """

    ingest_document_fetched = "ingest.document.fetched"
    ingest_document_parsed = "ingest.document.parsed"
    ingest_document_normalized = "ingest.document.normalized"
    ingest_document_chunked = "ingest.document.chunked"
    ingest_document_enriched = "ingest.document.enriched"
    ingest_document_embedded = "ingest.document.embedded"
    ingest_document_indexed = "ingest.document.indexed"
    ingest_document_retried = "ingest.document.retried"
    ingest_document_failed = "ingest.document.failed"
    ingest_document_deleted = "ingest.document.deleted"
    job_state_changed = "job.state.changed"
    index_commit_published = "index.commit.published"
    index_commit_rolled_back = "index.commit.rolled_back"
    index_consistency_mismatch = "index.consistency.mismatch"
    acl_document_updated = "acl.document.updated"
    collection_profile_changed = "collection.profile.changed"
    collection_reindex_completed = "collection.reindex.completed"
    audit_query_executed = "audit.query.executed"
    audit_document_accessed = "audit.document.accessed"
    audit_acl_changed = "audit.acl.changed"
    audit_admin_action = "audit.admin.action"
    feedback_query_cited = "feedback.query.cited"
    feedback_query_rated = "feedback.query.rated"
    eval_run_completed = "eval.run.completed"
    tenant_policies_changed = "tenant.policies.changed"


class Stage(StrEnum):
    chunk = "chunk"
    recount = "recount"


class Kind(StrEnum):
    """
    N(바이블 §5.7 1.3.0, 04-pipelines/13 §10 불일치 종류; 요청 #172). 메트릭 rag_consistency_mismatch_total{outcome} 라벨과 같은 값 집합
    """

    missing_records = "missing_records"
    hash_mismatch = "hash_mismatch"
    stale_current = "stale_current"
    orphan = "orphan"
    acl_hash_mismatch = "acl_hash_mismatch"
    artifact_missing = "artifact_missing"


class ObservedGeneration(RootModel[int]):
    root: int = Field(..., ge=1)


class ObservedGenerations(RootModel[list[ObservedGeneration]]):
    root: list[ObservedGeneration] = Field(..., min_length=1)


class Omitted(ContractModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    acl_denied: int = Field(..., ge=0)
    risk_flagged: int = Field(..., ge=0)


class Resource(ContractModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    type: str = Field(..., max_length=32, pattern="^[a-z_]+$")
    id: str = Field(..., max_length=128, min_length=1)


class Kind1(StrEnum):
    cited = "cited"
    rated = "rated"
    corrected = "corrected"


class Kind2(StrEnum):
    cited = "cited"
    rated = "rated"
    corrected = "corrected"
    rated_1 = "rated"
    corrected_1 = "corrected"


class DocumentSubject(RootModel[str]):
    root: str = Field(..., pattern="^tenant/[0-9A-HJKMNP-TV-Z]{26}/document/[0-9A-HJKMNP-TV-Z]{26}$")


class CollectionSubject(RootModel[str]):
    root: str = Field(..., pattern="^tenant/[0-9A-HJKMNP-TV-Z]{26}/collection/[0-9A-HJKMNP-TV-Z]{26}$")


class QuerySubject(RootModel[str]):
    root: str = Field(..., pattern="^tenant/[0-9A-HJKMNP-TV-Z]{26}/query/[0-9A-HJKMNP-TV-Z]{26}$")


class StageName(RootModel[str]):
    root: str = Field(..., max_length=32, pattern="^[a-z][a-z0-9_]*$")


class CountMap1(RootModel[int]):
    root: int = Field(..., ge=0)


class CountMap(RootModel[dict[str, CountMap1]]):
    """
    {backend_id 또는 이름: 정수}
    """

    root: dict[str, CountMap1] = Field(..., max_length=8)


class Kind3(StrEnum):
    """
    N(바이블 §5.7 1.3.0, 04-pipelines/13 §10 불일치 종류; 요청 #172). 메트릭 rag_consistency_mismatch_total{outcome} 라벨과 같은 값 집합
    """

    missing_records = "missing_records"
    hash_mismatch = "hash_mismatch"
    stale_current = "stale_current"
    orphan = "orphan"
    acl_hash_mismatch = "acl_hash_mismatch"
    artifact_missing = "artifact_missing"


class ObservedGenerations1Item(RootModel[int]):
    root: int = Field(..., ge=1)


class ObservedGenerations1(RootModel[list[ObservedGenerations1Item]]):
    root: list[ObservedGenerations1Item] = Field(..., min_length=1)


class AuditDecision(StrEnum):
    """
    Cedar 결정. 바이블 §5.7 미등재(미해결 이슈 8)
    """

    allow = "allow"
    deny = "deny"


class Data6(ContractModel):
    """
    ID·해시·상태만. 콘텍스트 본문 금지(E12)
    """

    model_config = ConfigDict(
        extra="allow",
    )
    job_id: common_types.Ulid
    document_id: common_types.Ulid
    collection_id: common_types.Ulid | None = None
    stage: Literal["index"]
    doc_version: common_types.Hex64
    quality: common_types.Quality
    commit_id: common_types.Ulid
    index_generation: int = Field(..., ge=1)
    commit_hash: common_types.Hex64
    record_count: int = Field(..., ge=0)
    job_state: common_types.JobState = Field(..., description="JobState 부분집합(바이블 §6.4)")


class CloudEventEnvelope7(ContractModel):
    """
    CloudEvents 1.0.2 봉투(바이블 §5.3·§6.5, ADR-0017)의 정제 래퍼. 봉투 자체는 urn:rag:schema:common-types:1#/$defs/CloudEventEnvelope 을 참조하고, 이 파일은 바이블 §5.7 이벤트 카탈로그 24종의 type ↔ data·subject 바인딩(oneOf)과 이벤트별 data 타입($defs)만 더한다. data는 ID·해시·상태·계수만 담고 콘텍스트 본문을 담지 않는다(E12). 소유 문서: docs/03-contracts/12-jobs-events-and-status.md
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    specversion: Literal["1.0"]
    id: common_types.Ulid = Field(..., description="event_id(소비자 멱등 키)")
    source: AnyUrl = Field(..., description="urn:rag:{component}")
    type: Literal["ingest.document.indexed"] = Field(
        ...,
        description="바이블 §5.7 이벤트 이름 카탈로그(domain.entity.action). CloudEventEnvelope.type. 1.3.0: tenant.policies.changed 추가(AM-38, 25종).",
    )
    time: common_types.DateTime
    subject: str = Field(
        ...,
        description="tenant/{tenant_id}/{entity}/{id}",
        pattern="^tenant/[0-9A-HJKMNP-TV-Z]{26}/[a-z_]+/[^/\\s]+$",
    )
    datacontenttype: Literal["application/json"]
    dataschema: common_types.SchemaId | None = None
    tenantid: common_types.Ulid = Field(..., description="CloudEvents 확장 속성(릴레이 테넌트 스코프)")
    data: Data6 = Field(..., description="ID·해시·상태만. 콘텍스트 본문 금지(E12)")


class Data8(ContractModel):
    """
    ID·해시·상태만. 콘텍스트 본문 금지(E12)
    """

    model_config = ConfigDict(
        extra="allow",
    )
    job_id: common_types.Ulid
    document_id: common_types.Ulid
    collection_id: common_types.Ulid | None = None
    stage: StageName
    code: common_types.ErrorCodeCatalog
    retryable: bool
    attempt: int = Field(..., ge=1)
    next_attempt_at: common_types.DateTime | None = None


class CloudEventEnvelope9(ContractModel):
    """
    CloudEvents 1.0.2 봉투(바이블 §5.3·§6.5, ADR-0017)의 정제 래퍼. 봉투 자체는 urn:rag:schema:common-types:1#/$defs/CloudEventEnvelope 을 참조하고, 이 파일은 바이블 §5.7 이벤트 카탈로그 24종의 type ↔ data·subject 바인딩(oneOf)과 이벤트별 data 타입($defs)만 더한다. data는 ID·해시·상태·계수만 담고 콘텍스트 본문을 담지 않는다(E12). 소유 문서: docs/03-contracts/12-jobs-events-and-status.md
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    specversion: Literal["1.0"]
    id: common_types.Ulid = Field(..., description="event_id(소비자 멱등 키)")
    source: AnyUrl = Field(..., description="urn:rag:{component}")
    type: Literal["ingest.document.failed"] = Field(
        ...,
        description="바이블 §5.7 이벤트 이름 카탈로그(domain.entity.action). CloudEventEnvelope.type. 1.3.0: tenant.policies.changed 추가(AM-38, 25종).",
    )
    time: common_types.DateTime
    subject: str = Field(
        ...,
        description="tenant/{tenant_id}/{entity}/{id}",
        pattern="^tenant/[0-9A-HJKMNP-TV-Z]{26}/[a-z_]+/[^/\\s]+$",
    )
    datacontenttype: Literal["application/json"]
    dataschema: common_types.SchemaId | None = None
    tenantid: common_types.Ulid = Field(..., description="CloudEvents 확장 속성(릴레이 테넌트 스코프)")
    data: Data8 = Field(..., description="ID·해시·상태만. 콘텍스트 본문 금지(E12)")


class Data9(ContractModel):
    """
    ID·해시·상태만. 콘텍스트 본문 금지(E12)
    """

    model_config = ConfigDict(
        extra="allow",
    )
    job_id: common_types.Ulid
    document_id: common_types.Ulid
    collection_id: common_types.Ulid
    commit_id: common_types.Ulid = Field(..., description="kind=delete tombstone 커밋(항상 존재)")
    index_generation: int = Field(..., ge=1)
    deleted_counts: CountMap = Field(..., description="백엔드별 삭제 레코드 수. current 커밋이 없던 문서는 모두 0")


class CloudEventEnvelope10(ContractModel):
    """
    CloudEvents 1.0.2 봉투(바이블 §5.3·§6.5, ADR-0017)의 정제 래퍼. 봉투 자체는 urn:rag:schema:common-types:1#/$defs/CloudEventEnvelope 을 참조하고, 이 파일은 바이블 §5.7 이벤트 카탈로그 24종의 type ↔ data·subject 바인딩(oneOf)과 이벤트별 data 타입($defs)만 더한다. data는 ID·해시·상태·계수만 담고 콘텍스트 본문을 담지 않는다(E12). 소유 문서: docs/03-contracts/12-jobs-events-and-status.md
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    specversion: Literal["1.0"]
    id: common_types.Ulid = Field(..., description="event_id(소비자 멱등 키)")
    source: AnyUrl = Field(..., description="urn:rag:{component}")
    type: Literal["ingest.document.deleted"] = Field(
        ...,
        description="바이블 §5.7 이벤트 이름 카탈로그(domain.entity.action). CloudEventEnvelope.type. 1.3.0: tenant.policies.changed 추가(AM-38, 25종).",
    )
    time: common_types.DateTime
    subject: str = Field(
        ...,
        description="tenant/{tenant_id}/{entity}/{id}",
        pattern="^tenant/[0-9A-HJKMNP-TV-Z]{26}/[a-z_]+/[^/\\s]+$",
    )
    datacontenttype: Literal["application/json"]
    dataschema: common_types.SchemaId | None = None
    tenantid: common_types.Ulid = Field(..., description="CloudEvents 확장 속성(릴레이 테넌트 스코프)")
    data: Data9 = Field(..., description="ID·해시·상태만. 콘텍스트 본문 금지(E12)")


class Error(ContractModel):
    """
    StageError 투영(13 J3)
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    code: common_types.ErrorCodeCatalog
    retryable: bool
    attempt: int = Field(..., ge=1)


class Data11(ContractModel):
    """
    ID·해시·상태만. 콘텍스트 본문 금지(E12)
    """

    model_config = ConfigDict(
        extra="allow",
    )
    commit_id: common_types.Ulid
    job_id: common_types.Ulid
    document_id: common_types.Ulid
    collection_id: common_types.Ulid
    doc_version: common_types.Hex64
    index_generation: int = Field(..., ge=1)
    status: common_types.CommitStatus = Field(..., description="CommitStatus 고정값(바이블 §6.4)")
    kind: common_types.CommitKind | None = None
    commit_hash: common_types.Hex64
    record_count: int = Field(..., ge=0)
    previous_commit_id: common_types.Ulid | None = None


class CloudEventEnvelope12(ContractModel):
    """
    CloudEvents 1.0.2 봉투(바이블 §5.3·§6.5, ADR-0017)의 정제 래퍼. 봉투 자체는 urn:rag:schema:common-types:1#/$defs/CloudEventEnvelope 을 참조하고, 이 파일은 바이블 §5.7 이벤트 카탈로그 24종의 type ↔ data·subject 바인딩(oneOf)과 이벤트별 data 타입($defs)만 더한다. data는 ID·해시·상태·계수만 담고 콘텍스트 본문을 담지 않는다(E12). 소유 문서: docs/03-contracts/12-jobs-events-and-status.md
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    specversion: Literal["1.0"]
    id: common_types.Ulid = Field(..., description="event_id(소비자 멱등 키)")
    source: AnyUrl = Field(..., description="urn:rag:{component}")
    type: Literal["index.commit.published"] = Field(
        ...,
        description="바이블 §5.7 이벤트 이름 카탈로그(domain.entity.action). CloudEventEnvelope.type. 1.3.0: tenant.policies.changed 추가(AM-38, 25종).",
    )
    time: common_types.DateTime
    subject: str = Field(
        ...,
        description="tenant/{tenant_id}/{entity}/{id}",
        pattern="^tenant/[0-9A-HJKMNP-TV-Z]{26}/[a-z_]+/[^/\\s]+$",
    )
    datacontenttype: Literal["application/json"]
    dataschema: common_types.SchemaId | None = None
    tenantid: common_types.Ulid = Field(..., description="CloudEvents 확장 속성(릴레이 테넌트 스코프)")
    data: Data11 = Field(..., description="ID·해시·상태만. 콘텍스트 본문 금지(E12)")


class Data12(ContractModel):
    """
    ID·해시·상태만. 콘텍스트 본문 금지(E12)
    """

    model_config = ConfigDict(
        extra="allow",
    )
    commit_id: common_types.Ulid
    job_id: common_types.Ulid
    document_id: common_types.Ulid
    collection_id: common_types.Ulid
    doc_version: common_types.Hex64 | None = None
    index_generation: int = Field(..., ge=1)
    status: common_types.CommitStatus = Field(..., description="CommitStatus 고정값")
    failed_at_status: common_types.CommitStatus = Field(
        ...,
        description="CommitStatus 부분집합(바이블 §6.4) = IndexCommit.compensation.failed_at_status: 보상 시작 시점의 전종결 상태(종결·rolling_back 불가). pending~lexical_written = 플립 전 모드, flipping_* = 플립 후 모드",
    )
    restored_generation: int | None = Field(
        ...,
        description="= compensation.restored_generation. 플립 후 보상이 복원한 세대. 플립 전·첫 세대는 null",
        ge=1,
    )
    code: common_types.ErrorCodeCatalog | None = Field(
        None,
        description="선택(N). 최종 IndexCommit.error.code(retryable=false; 촉발 원인은 error.cause.code이며 이벤트에 없음). reason=job_cancelled(취소, error 없음)면 없고 그 외는 reason과 같다(08 IC-15)",
    )
    reason: str = Field(
        ...,
        description="= IndexCommit.compensation.reason: 최종 error.code({stage}.{reason}) 또는 job_cancelled",
        max_length=64,
        pattern="^[a-z][a-z0-9_]*(\\.[a-z][a-z0-9_]*)?$",
    )


class CloudEventEnvelope13(ContractModel):
    """
    CloudEvents 1.0.2 봉투(바이블 §5.3·§6.5, ADR-0017)의 정제 래퍼. 봉투 자체는 urn:rag:schema:common-types:1#/$defs/CloudEventEnvelope 을 참조하고, 이 파일은 바이블 §5.7 이벤트 카탈로그 24종의 type ↔ data·subject 바인딩(oneOf)과 이벤트별 data 타입($defs)만 더한다. data는 ID·해시·상태·계수만 담고 콘텍스트 본문을 담지 않는다(E12). 소유 문서: docs/03-contracts/12-jobs-events-and-status.md
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    specversion: Literal["1.0"]
    id: common_types.Ulid = Field(..., description="event_id(소비자 멱등 키)")
    source: AnyUrl = Field(..., description="urn:rag:{component}")
    type: Literal["index.commit.rolled_back"] = Field(
        ...,
        description="바이블 §5.7 이벤트 이름 카탈로그(domain.entity.action). CloudEventEnvelope.type. 1.3.0: tenant.policies.changed 추가(AM-38, 25종).",
    )
    time: common_types.DateTime
    subject: str = Field(
        ...,
        description="tenant/{tenant_id}/{entity}/{id}",
        pattern="^tenant/[0-9A-HJKMNP-TV-Z]{26}/[a-z_]+/[^/\\s]+$",
    )
    datacontenttype: Literal["application/json"]
    dataschema: common_types.SchemaId | None = None
    tenantid: common_types.Ulid = Field(..., description="CloudEvents 확장 속성(릴레이 테넌트 스코프)")
    data: Data12 = Field(..., description="ID·해시·상태만. 콘텍스트 본문 금지(E12)")


class Data13(ContractModel):
    """
    ID·해시·상태만. 콘텍스트 본문 금지(E12)
    """

    model_config = ConfigDict(
        extra="allow",
    )
    job_id: common_types.Ulid = Field(..., description="보상 실패 잡 또는 consistency_check 잡")
    document_id: common_types.Ulid
    collection_id: common_types.Ulid
    commit_id: common_types.Ulid | None
    index_generation: int | None = Field(..., ge=1)
    expected_record_count: int = Field(..., ge=0)
    observed_record_counts: CountMap
    content_hash_mismatch: bool
    repair_job_id: common_types.Ulid | None = Field(None, description="재적재(from_stage=index) 잡")
    kind: Kind | None = Field(
        None,
        description="N(바이블 §5.7 1.3.0, 04-pipelines/13 §10 불일치 종류; 요청 #172). 메트릭 rag_consistency_mismatch_total{outcome} 라벨과 같은 값 집합",
    )
    observed_generations: dict[str, ObservedGenerations] | None = Field(
        None,
        description="N(바이블 §5.7 1.3.0; 요청 #172). object(키 backend_id, 값 index_generation 배열) — 백엔드별로 관측된 세대 목록(stale_current 등 세대 분포 진단)",
    )


class CloudEventEnvelope14(ContractModel):
    """
    CloudEvents 1.0.2 봉투(바이블 §5.3·§6.5, ADR-0017)의 정제 래퍼. 봉투 자체는 urn:rag:schema:common-types:1#/$defs/CloudEventEnvelope 을 참조하고, 이 파일은 바이블 §5.7 이벤트 카탈로그 24종의 type ↔ data·subject 바인딩(oneOf)과 이벤트별 data 타입($defs)만 더한다. data는 ID·해시·상태·계수만 담고 콘텍스트 본문을 담지 않는다(E12). 소유 문서: docs/03-contracts/12-jobs-events-and-status.md
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    specversion: Literal["1.0"]
    id: common_types.Ulid = Field(..., description="event_id(소비자 멱등 키)")
    source: AnyUrl = Field(..., description="urn:rag:{component}")
    type: Literal["index.consistency.mismatch"] = Field(
        ...,
        description="바이블 §5.7 이벤트 이름 카탈로그(domain.entity.action). CloudEventEnvelope.type. 1.3.0: tenant.policies.changed 추가(AM-38, 25종).",
    )
    time: common_types.DateTime
    subject: str = Field(
        ...,
        description="tenant/{tenant_id}/{entity}/{id}",
        pattern="^tenant/[0-9A-HJKMNP-TV-Z]{26}/[a-z_]+/[^/\\s]+$",
    )
    datacontenttype: Literal["application/json"]
    dataschema: common_types.SchemaId | None = None
    tenantid: common_types.Ulid = Field(..., description="CloudEvents 확장 속성(릴레이 테넌트 스코프)")
    data: Data13 = Field(..., description="ID·해시·상태만. 콘텍스트 본문 금지(E12)")


class Data14(ContractModel):
    """
    ID·해시·상태만. 콘텍스트 본문 금지(E12)
    """

    model_config = ConfigDict(
        extra="allow",
    )
    job_id: common_types.Ulid
    document_id: common_types.Ulid
    collection_id: common_types.Ulid
    acl_hash: common_types.Hex64
    previous_acl_hash: common_types.Hex64 | None
    visibility: common_types.Visibility = Field(
        ..., description="갱신 후 Acl.visibility(원천 생략 시 기본 tenant를 채워 기록)"
    )
    classification: common_types.Classification = Field(
        ...,
        description="갱신 후 Acl.classification. 원천(common-types Acl, N)이 생략되었으면 기본 internal을 채워 기록 — 이벤트에서는 항상 필수",
    )
    backends_updated: list[common_types.PluginId] = Field(..., max_length=8, min_length=1)
    revocation_hint_recorded: bool = Field(..., description="aclrev: 회수 힌트 기록 여부(E9)")
    propagation_ms: int | None = Field(None, description="접수 → 백엔드 갱신 완료(rag_acl_propagation_seconds)", ge=0)


class CloudEventEnvelope15(ContractModel):
    """
    CloudEvents 1.0.2 봉투(바이블 §5.3·§6.5, ADR-0017)의 정제 래퍼. 봉투 자체는 urn:rag:schema:common-types:1#/$defs/CloudEventEnvelope 을 참조하고, 이 파일은 바이블 §5.7 이벤트 카탈로그 24종의 type ↔ data·subject 바인딩(oneOf)과 이벤트별 data 타입($defs)만 더한다. data는 ID·해시·상태·계수만 담고 콘텍스트 본문을 담지 않는다(E12). 소유 문서: docs/03-contracts/12-jobs-events-and-status.md
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    specversion: Literal["1.0"]
    id: common_types.Ulid = Field(..., description="event_id(소비자 멱등 키)")
    source: AnyUrl = Field(..., description="urn:rag:{component}")
    type: Literal["acl.document.updated"] = Field(
        ...,
        description="바이블 §5.7 이벤트 이름 카탈로그(domain.entity.action). CloudEventEnvelope.type. 1.3.0: tenant.policies.changed 추가(AM-38, 25종).",
    )
    time: common_types.DateTime
    subject: str = Field(
        ...,
        description="tenant/{tenant_id}/{entity}/{id}",
        pattern="^tenant/[0-9A-HJKMNP-TV-Z]{26}/[a-z_]+/[^/\\s]+$",
    )
    datacontenttype: Literal["application/json"]
    dataschema: common_types.SchemaId | None = None
    tenantid: common_types.Ulid = Field(..., description="CloudEvents 확장 속성(릴레이 테넌트 스코프)")
    data: Data14 = Field(..., description="ID·해시·상태만. 콘텍스트 본문 금지(E12)")


class Data15(ContractModel):
    """
    ID·해시·상태만. 콘텍스트 본문 금지(E12)
    """

    model_config = ConfigDict(
        extra="allow",
    )
    collection_id: common_types.Ulid
    change_kind: CollectionProfileChangedData_1.ChangeKind
    profile_id: str = Field(..., max_length=64, pattern="^[a-z][a-z0-9]*(-[a-z0-9]+)*$")
    profile_hash: common_types.Hex64 = Field(..., description="변경 후 프로파일 해시")
    previous_profile_hash: common_types.Hex64 | None = Field(
        ...,
        description="변경 전 프로파일 해시(최초 지정은 null). change_kind ∈ {dictionary, policy}면 profile_hash와 같다",
    )
    embedding_profile_hash: common_types.Hex64
    analyzer_id: str = Field(
        ...,
        description="변경 후 analyzer_id({engine}:{version}:{dictionary}, 바이블 §6.1)",
        max_length=128,
        pattern="^[a-z][a-z0-9-]*:[^:\\s]+:[^\\s]+$",
    )
    previous_analyzer_id: str | None = Field(
        None,
        description="선택(N). 분석기가 바뀐 경우만(변경 전 analyzer_id)",
        max_length=128,
        pattern="^[a-z][a-z0-9-]*:[^:\\s]+:[^\\s]+$",
    )
    dictionary_hash: common_types.Hex64 = Field(..., description="변경 후 dictionary_hash(16 EF-23)")
    previous_dictionary_hash: common_types.Hex64 | None = Field(
        None,
        description="선택(N, null 허용). 변경 전 dictionary_hash(사전이 없었으면 null). change_kind=dictionary면 필수 — 16 §6.2 API 응답 previous_dictionary_hash와 같은 값",
    )
    reindex_required: bool = Field(
        ...,
        description="재색인이 필요한 변경인지(사전 변경은 16 §6.2 reindex_suggested와 같은 값)",
    )
    reindex_job_id: common_types.Ulid | None = Field(None, description="선택(N). 함께 접수된 reindex_collection 잡")


class CloudEventEnvelope16(ContractModel):
    """
    CloudEvents 1.0.2 봉투(바이블 §5.3·§6.5, ADR-0017)의 정제 래퍼. 봉투 자체는 urn:rag:schema:common-types:1#/$defs/CloudEventEnvelope 을 참조하고, 이 파일은 바이블 §5.7 이벤트 카탈로그 24종의 type ↔ data·subject 바인딩(oneOf)과 이벤트별 data 타입($defs)만 더한다. data는 ID·해시·상태·계수만 담고 콘텍스트 본문을 담지 않는다(E12). 소유 문서: docs/03-contracts/12-jobs-events-and-status.md
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    specversion: Literal["1.0"]
    id: common_types.Ulid = Field(..., description="event_id(소비자 멱등 키)")
    source: AnyUrl = Field(..., description="urn:rag:{component}")
    type: Literal["collection.profile.changed"] = Field(
        ...,
        description="바이블 §5.7 이벤트 이름 카탈로그(domain.entity.action). CloudEventEnvelope.type. 1.3.0: tenant.policies.changed 추가(AM-38, 25종).",
    )
    time: common_types.DateTime
    subject: str = Field(
        ...,
        description="tenant/{tenant_id}/{entity}/{id}",
        pattern="^tenant/[0-9A-HJKMNP-TV-Z]{26}/[a-z_]+/[^/\\s]+$",
    )
    datacontenttype: Literal["application/json"]
    dataschema: common_types.SchemaId | None = None
    tenantid: common_types.Ulid = Field(..., description="CloudEvents 확장 속성(릴레이 테넌트 스코프)")
    data: Data15 = Field(..., description="ID·해시·상태만. 콘텍스트 본문 금지(E12)")


class Data16(ContractModel):
    """
    ID·해시·상태만. 콘텍스트 본문 금지(E12)
    """

    model_config = ConfigDict(
        extra="allow",
    )
    job_id: common_types.Ulid
    collection_id: common_types.Ulid
    profile_hash: common_types.Hex64
    document_count: int = Field(..., ge=0)
    succeeded_count: int = Field(..., ge=0)
    partial_count: int = Field(..., ge=0)
    failed_count: int = Field(..., ge=0)
    alias_swapped: bool
    gate_passed: bool | None = Field(..., description="게이트 미실행은 null")
    run_id: common_types.Ulid | None = Field(
        None,
        description="선택(N). 게이트 평가 EvalRun.run_id(바이블 §6.1; 게이트 미실행이면 생략)",
    )


class CloudEventEnvelope17(ContractModel):
    """
    CloudEvents 1.0.2 봉투(바이블 §5.3·§6.5, ADR-0017)의 정제 래퍼. 봉투 자체는 urn:rag:schema:common-types:1#/$defs/CloudEventEnvelope 을 참조하고, 이 파일은 바이블 §5.7 이벤트 카탈로그 24종의 type ↔ data·subject 바인딩(oneOf)과 이벤트별 data 타입($defs)만 더한다. data는 ID·해시·상태·계수만 담고 콘텍스트 본문을 담지 않는다(E12). 소유 문서: docs/03-contracts/12-jobs-events-and-status.md
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    specversion: Literal["1.0"]
    id: common_types.Ulid = Field(..., description="event_id(소비자 멱등 키)")
    source: AnyUrl = Field(..., description="urn:rag:{component}")
    type: Literal["collection.reindex.completed"] = Field(
        ...,
        description="바이블 §5.7 이벤트 이름 카탈로그(domain.entity.action). CloudEventEnvelope.type. 1.3.0: tenant.policies.changed 추가(AM-38, 25종).",
    )
    time: common_types.DateTime
    subject: str = Field(
        ...,
        description="tenant/{tenant_id}/{entity}/{id}",
        pattern="^tenant/[0-9A-HJKMNP-TV-Z]{26}/[a-z_]+/[^/\\s]+$",
    )
    datacontenttype: Literal["application/json"]
    dataschema: common_types.SchemaId | None = None
    tenantid: common_types.Ulid = Field(..., description="CloudEvents 확장 속성(릴레이 테넌트 스코프)")
    data: Data16 = Field(..., description="ID·해시·상태만. 콘텍스트 본문 금지(E12)")


class Returned(ContractModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    document_ids: list[common_types.Ulid] = Field(..., max_length=100)
    chunk_count: int = Field(..., ge=0)


class Data17(ContractModel):
    """
    ID·해시·상태만. 콘텍스트 본문 금지(E12)
    """

    model_config = ConfigDict(
        extra="allow",
    )
    query_id: common_types.Ulid
    plan_id: common_types.Ulid
    pack_id: common_types.Ulid | None = Field(..., description="route=no_retrieval이면 null")
    trace_id: str = Field(..., pattern="^[0-9a-f]{32}$")
    auth_method: common_types.AuthMethod
    principal_hash: common_types.Hex64 = Field(..., description='H("principal", tenant_id, subject)(07 문서 제안)')
    actor_client_id: str | None = Field(None, max_length=128)
    collection_ids: list[common_types.Ulid] = Field(..., max_length=20, min_length=1)
    query_hash: common_types.Hex64 = Field(
        ...,
        description="blake3_hex(utf8(normalized_query)) — 07 §8.2 hash_only 정책(라벨 없음; 미해결 이슈 8)",
    )
    filters_effective_hash: common_types.Hex64
    security_context_hash: common_types.Hex64
    profile_hash: common_types.Hex64
    returned: Returned
    omitted: Omitted
    degraded: list[common_types.DegradedEntry] = Field(..., max_length=64)
    latency_ms: int = Field(..., ge=0)


class CloudEventEnvelope18(ContractModel):
    """
    CloudEvents 1.0.2 봉투(바이블 §5.3·§6.5, ADR-0017)의 정제 래퍼. 봉투 자체는 urn:rag:schema:common-types:1#/$defs/CloudEventEnvelope 을 참조하고, 이 파일은 바이블 §5.7 이벤트 카탈로그 24종의 type ↔ data·subject 바인딩(oneOf)과 이벤트별 data 타입($defs)만 더한다. data는 ID·해시·상태·계수만 담고 콘텍스트 본문을 담지 않는다(E12). 소유 문서: docs/03-contracts/12-jobs-events-and-status.md
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    specversion: Literal["1.0"]
    id: common_types.Ulid = Field(..., description="event_id(소비자 멱등 키)")
    source: AnyUrl = Field(..., description="urn:rag:{component}")
    type: Literal["audit.query.executed"] = Field(
        ...,
        description="바이블 §5.7 이벤트 이름 카탈로그(domain.entity.action). CloudEventEnvelope.type. 1.3.0: tenant.policies.changed 추가(AM-38, 25종).",
    )
    time: common_types.DateTime
    subject: str = Field(
        ...,
        description="tenant/{tenant_id}/{entity}/{id}",
        pattern="^tenant/[0-9A-HJKMNP-TV-Z]{26}/[a-z_]+/[^/\\s]+$",
    )
    datacontenttype: Literal["application/json"]
    dataschema: common_types.SchemaId | None = None
    tenantid: common_types.Ulid = Field(..., description="CloudEvents 확장 속성(릴레이 테넌트 스코프)")
    data: Data17 = Field(..., description="ID·해시·상태만. 콘텍스트 본문 금지(E12)")


class Data18(ContractModel):
    """
    ID·해시·상태만. 콘텍스트 본문 금지(E12)
    """

    model_config = ConfigDict(
        extra="allow",
    )
    document_id: common_types.Ulid
    collection_id: common_types.Ulid | None = None
    view: AuditDocumentAccessedData_1.View
    principal_hash: common_types.Hex64
    decision: AuditDecision
    acl_hash: common_types.Hex64 | None = Field(..., description="거부(존재 비노출)면 null")


class CloudEventEnvelope19(ContractModel):
    """
    CloudEvents 1.0.2 봉투(바이블 §5.3·§6.5, ADR-0017)의 정제 래퍼. 봉투 자체는 urn:rag:schema:common-types:1#/$defs/CloudEventEnvelope 을 참조하고, 이 파일은 바이블 §5.7 이벤트 카탈로그 24종의 type ↔ data·subject 바인딩(oneOf)과 이벤트별 data 타입($defs)만 더한다. data는 ID·해시·상태·계수만 담고 콘텍스트 본문을 담지 않는다(E12). 소유 문서: docs/03-contracts/12-jobs-events-and-status.md
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    specversion: Literal["1.0"]
    id: common_types.Ulid = Field(..., description="event_id(소비자 멱등 키)")
    source: AnyUrl = Field(..., description="urn:rag:{component}")
    type: Literal["audit.document.accessed"] = Field(
        ...,
        description="바이블 §5.7 이벤트 이름 카탈로그(domain.entity.action). CloudEventEnvelope.type. 1.3.0: tenant.policies.changed 추가(AM-38, 25종).",
    )
    time: common_types.DateTime
    subject: str = Field(
        ...,
        description="tenant/{tenant_id}/{entity}/{id}",
        pattern="^tenant/[0-9A-HJKMNP-TV-Z]{26}/[a-z_]+/[^/\\s]+$",
    )
    datacontenttype: Literal["application/json"]
    dataschema: common_types.SchemaId | None = None
    tenantid: common_types.Ulid = Field(..., description="CloudEvents 확장 속성(릴레이 테넌트 스코프)")
    data: Data18 = Field(..., description="ID·해시·상태만. 콘텍스트 본문 금지(E12)")


class Data19(ContractModel):
    """
    ID·해시·상태만. 콘텍스트 본문 금지(E12)
    """

    model_config = ConfigDict(
        extra="allow",
    )
    document_id: common_types.Ulid
    collection_id: common_types.Ulid | None = None
    principal_hash: common_types.Hex64
    acl_hash_before: common_types.Hex64 | None
    acl_hash_after: common_types.Hex64
    job_id: common_types.Ulid = Field(..., description="acl.update.v1 잡")


class CloudEventEnvelope20(ContractModel):
    """
    CloudEvents 1.0.2 봉투(바이블 §5.3·§6.5, ADR-0017)의 정제 래퍼. 봉투 자체는 urn:rag:schema:common-types:1#/$defs/CloudEventEnvelope 을 참조하고, 이 파일은 바이블 §5.7 이벤트 카탈로그 24종의 type ↔ data·subject 바인딩(oneOf)과 이벤트별 data 타입($defs)만 더한다. data는 ID·해시·상태·계수만 담고 콘텍스트 본문을 담지 않는다(E12). 소유 문서: docs/03-contracts/12-jobs-events-and-status.md
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    specversion: Literal["1.0"]
    id: common_types.Ulid = Field(..., description="event_id(소비자 멱등 키)")
    source: AnyUrl = Field(..., description="urn:rag:{component}")
    type: Literal["audit.acl.changed"] = Field(
        ...,
        description="바이블 §5.7 이벤트 이름 카탈로그(domain.entity.action). CloudEventEnvelope.type. 1.3.0: tenant.policies.changed 추가(AM-38, 25종).",
    )
    time: common_types.DateTime
    subject: str = Field(
        ...,
        description="tenant/{tenant_id}/{entity}/{id}",
        pattern="^tenant/[0-9A-HJKMNP-TV-Z]{26}/[a-z_]+/[^/\\s]+$",
    )
    datacontenttype: Literal["application/json"]
    dataschema: common_types.SchemaId | None = None
    tenantid: common_types.Ulid = Field(..., description="CloudEvents 확장 속성(릴레이 테넌트 스코프)")
    data: Data19 = Field(..., description="ID·해시·상태만. 콘텍스트 본문 금지(E12)")


class Data20(ContractModel):
    """
    ID·해시·상태만. 콘텍스트 본문 금지(E12)
    """

    model_config = ConfigDict(
        extra="allow",
    )
    action: str = Field(
        ...,
        description="Cedar 액션명(예 collection.update, job.cancel)",
        max_length=64,
        pattern="^[a-z][a-z0-9_]*(\\.[a-z][a-z0-9_]*)*$",
    )
    resource: Resource
    principal_hash: common_types.Hex64
    decision: AuditDecision
    policy_version: str = Field(..., max_length=64, min_length=1)
    request_id: common_types.Ulid
    job_id: common_types.Ulid | None = None


class CloudEventEnvelope21(ContractModel):
    """
    CloudEvents 1.0.2 봉투(바이블 §5.3·§6.5, ADR-0017)의 정제 래퍼. 봉투 자체는 urn:rag:schema:common-types:1#/$defs/CloudEventEnvelope 을 참조하고, 이 파일은 바이블 §5.7 이벤트 카탈로그 24종의 type ↔ data·subject 바인딩(oneOf)과 이벤트별 data 타입($defs)만 더한다. data는 ID·해시·상태·계수만 담고 콘텍스트 본문을 담지 않는다(E12). 소유 문서: docs/03-contracts/12-jobs-events-and-status.md
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    specversion: Literal["1.0"]
    id: common_types.Ulid = Field(..., description="event_id(소비자 멱등 키)")
    source: AnyUrl = Field(..., description="urn:rag:{component}")
    type: Literal["audit.admin.action"] = Field(
        ...,
        description="바이블 §5.7 이벤트 이름 카탈로그(domain.entity.action). CloudEventEnvelope.type. 1.3.0: tenant.policies.changed 추가(AM-38, 25종).",
    )
    time: common_types.DateTime
    subject: str = Field(
        ...,
        description="tenant/{tenant_id}/{entity}/{id}",
        pattern="^tenant/[0-9A-HJKMNP-TV-Z]{26}/[a-z_]+/[^/\\s]+$",
    )
    datacontenttype: Literal["application/json"]
    dataschema: common_types.SchemaId | None = None
    tenantid: common_types.Ulid = Field(..., description="CloudEvents 확장 속성(릴레이 테넌트 스코프)")
    data: Data20 = Field(..., description="ID·해시·상태만. 콘텍스트 본문 금지(E12)")


class Data23(ContractModel):
    """
    ID·해시·상태만. 콘텍스트 본문 금지(E12)
    """

    model_config = ConfigDict(
        extra="allow",
    )
    run_id: common_types.Ulid
    dataset_id: common_types.Ulid
    profile_id: str = Field(..., max_length=64, pattern="^[a-z][a-z0-9]*(-[a-z0-9]+)*$")
    profile_hash: common_types.Hex64
    status: common_types.EvalRunStatus
    index_commit_ids: list[common_types.Ulid] = Field(..., max_length=1000)
    gate_passed: bool | None
    metrics: dict[str, float] = Field(
        ...,
        description="EvalReport.metrics 사본(ndcg@10, recall@20, mrr 등)",
        max_length=64,
    )


class CloudEventEnvelope24(ContractModel):
    """
    CloudEvents 1.0.2 봉투(바이블 §5.3·§6.5, ADR-0017)의 정제 래퍼. 봉투 자체는 urn:rag:schema:common-types:1#/$defs/CloudEventEnvelope 을 참조하고, 이 파일은 바이블 §5.7 이벤트 카탈로그 24종의 type ↔ data·subject 바인딩(oneOf)과 이벤트별 data 타입($defs)만 더한다. data는 ID·해시·상태·계수만 담고 콘텍스트 본문을 담지 않는다(E12). 소유 문서: docs/03-contracts/12-jobs-events-and-status.md
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    specversion: Literal["1.0"]
    id: common_types.Ulid = Field(..., description="event_id(소비자 멱등 키)")
    source: AnyUrl = Field(..., description="urn:rag:{component}")
    type: Literal["eval.run.completed"] = Field(
        ...,
        description="바이블 §5.7 이벤트 이름 카탈로그(domain.entity.action). CloudEventEnvelope.type. 1.3.0: tenant.policies.changed 추가(AM-38, 25종).",
    )
    time: common_types.DateTime
    subject: str = Field(
        ...,
        description="tenant/{tenant_id}/{entity}/{id}",
        pattern="^tenant/[0-9A-HJKMNP-TV-Z]{26}/eval_run/[0-9A-HJKMNP-TV-Z]{26}$",
    )
    datacontenttype: Literal["application/json"]
    dataschema: common_types.SchemaId | None = None
    tenantid: common_types.Ulid = Field(..., description="CloudEvents 확장 속성(릴레이 테넌트 스코프)")
    data: Data23 = Field(..., description="ID·해시·상태만. 콘텍스트 본문 금지(E12)")


class IngestStageEventData(ContractModel):
    """
    ingest.document.{fetched, parsed, normalized, chunked, enriched, embedded}. 스테이지 래퍼 commit_stage가 산출물 저장 트랜잭션에서 기록. 스테이지별 선택 계수는 표 §6.1
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    job_id: common_types.Ulid
    document_id: common_types.Ulid
    collection_id: common_types.Ulid | None = None
    stage: StageName
    doc_version: common_types.Hex64
    quality: common_types.Quality
    artifact_blake3: common_types.Hex64 = Field(..., description="산출물 바이트 해시(ArtifactRef.blake3)")
    stage_key: common_types.Hex64 | None = Field(None, description="fetch 이후 스테이지 필수")
    cache_hit: bool | None = None
    warning_count: int | None = Field(None, ge=0)
    size_bytes: int | None = Field(None, ge=0)
    format: common_types.SourceFormat | None = None
    block_count: int | None = Field(None, ge=0)
    page_count: int | None = Field(None, description="흐름 포맷은 null", ge=0)
    pii_policy_applied: common_types.PiiPolicy | None = None
    chunk_count: int | None = Field(None, ge=0)
    parent_count: int | None = Field(None, ge=0)
    chunker_config_hash: common_types.Hex64 | None = None
    enrich_status: common_types.EnrichStatus | None = None
    llm_tokens_in: int | None = Field(None, ge=0)
    llm_tokens_out: int | None = Field(None, ge=0)
    record_count: int | None = Field(None, ge=0)
    embedding_profile_hash: common_types.Hex64 | None = None


class IngestDocumentIndexedData(ContractModel):
    """
    ingest.document.indexed. publish가 succeeded·partial 종결 트랜잭션에서 기록
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    job_id: common_types.Ulid
    document_id: common_types.Ulid
    collection_id: common_types.Ulid | None = None
    stage: Literal["index"]
    doc_version: common_types.Hex64
    quality: common_types.Quality
    commit_id: common_types.Ulid
    index_generation: int = Field(..., ge=1)
    commit_hash: common_types.Hex64
    record_count: int = Field(..., ge=0)
    job_state: common_types.JobState = Field(..., description="JobState 부분집합(바이블 §6.4)")


class IngestFailureEventData(ContractModel):
    """
    ingest.document.retried·failed. StageError 투영 {job_id, document_id, stage, code, retryable, attempt}(13 J3) — detail·artifact_ref·location·cause 없음
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    job_id: common_types.Ulid
    document_id: common_types.Ulid
    collection_id: common_types.Ulid | None = None
    stage: StageName
    code: common_types.ErrorCodeCatalog
    retryable: bool
    attempt: int = Field(..., ge=1)
    next_attempt_at: common_types.DateTime | None = None


class IngestDocumentDeletedData(ContractModel):
    """
    ingest.document.deleted. publish가 delete.document.v1 종결 트랜잭션에서 기록. 삭제 잡은 current 커밋 유무와 무관하게 항상 kind=delete tombstone 커밋(record_count=0)을 만들므로(바이블 §11.2·§5.4) commit_id·index_generation은 nullable이 아니다
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    job_id: common_types.Ulid
    document_id: common_types.Ulid
    collection_id: common_types.Ulid
    commit_id: common_types.Ulid = Field(..., description="kind=delete tombstone 커밋(항상 존재)")
    index_generation: int = Field(..., ge=1)
    deleted_counts: CountMap = Field(..., description="백엔드별 삭제 레코드 수. current 커밋이 없던 문서는 모두 0")


class IndexCommitPublishedData(ContractModel):
    """
    index.commit.published. IndexCommit 투영(08 문서 미해결 이슈 12, 14 예시 4)
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    commit_id: common_types.Ulid
    job_id: common_types.Ulid
    document_id: common_types.Ulid
    collection_id: common_types.Ulid
    doc_version: common_types.Hex64
    index_generation: int = Field(..., ge=1)
    status: common_types.CommitStatus = Field(..., description="CommitStatus 고정값(바이블 §6.4)")
    kind: common_types.CommitKind | None = None
    commit_hash: common_types.Hex64
    record_count: int = Field(..., ge=0)
    previous_commit_id: common_types.Ulid | None = None


class IndexCommitRolledBackData(ContractModel):
    """
    index.commit.rolled_back. IndexCommit.compensation(08 §2.6) 투영: failed_at_status·restored_generation·reason은 compensation의 같은 이름 필드와 값이 같고 code는 최종 IndexCommit.error.code다
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    commit_id: common_types.Ulid
    job_id: common_types.Ulid
    document_id: common_types.Ulid
    collection_id: common_types.Ulid
    doc_version: common_types.Hex64 | None = None
    index_generation: int = Field(..., ge=1)
    status: common_types.CommitStatus = Field(..., description="CommitStatus 고정값")
    failed_at_status: common_types.CommitStatus = Field(
        ...,
        description="CommitStatus 부분집합(바이블 §6.4) = IndexCommit.compensation.failed_at_status: 보상 시작 시점의 전종결 상태(종결·rolling_back 불가). pending~lexical_written = 플립 전 모드, flipping_* = 플립 후 모드",
    )
    restored_generation: int | None = Field(
        ...,
        description="= compensation.restored_generation. 플립 후 보상이 복원한 세대. 플립 전·첫 세대는 null",
        ge=1,
    )
    code: common_types.ErrorCodeCatalog | None = Field(
        None,
        description="선택(N). 최종 IndexCommit.error.code(retryable=false; 촉발 원인은 error.cause.code이며 이벤트에 없음). reason=job_cancelled(취소, error 없음)면 없고 그 외는 reason과 같다(08 IC-15)",
    )
    reason: str = Field(
        ...,
        description="= IndexCommit.compensation.reason: 최종 error.code({stage}.{reason}) 또는 job_cancelled",
        max_length=64,
        pattern="^[a-z][a-z0-9_]*(\\.[a-z][a-z0-9_]*)?$",
    )


class IndexConsistencyMismatchData(ContractModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    job_id: common_types.Ulid = Field(..., description="보상 실패 잡 또는 consistency_check 잡")
    document_id: common_types.Ulid
    collection_id: common_types.Ulid
    commit_id: common_types.Ulid | None
    index_generation: int | None = Field(..., ge=1)
    expected_record_count: int = Field(..., ge=0)
    observed_record_counts: CountMap
    content_hash_mismatch: bool
    repair_job_id: common_types.Ulid | None = Field(None, description="재적재(from_stage=index) 잡")
    kind: Kind3 | None = Field(
        None,
        description="N(바이블 §5.7 1.3.0, 04-pipelines/13 §10 불일치 종류; 요청 #172). 메트릭 rag_consistency_mismatch_total{outcome} 라벨과 같은 값 집합",
    )
    observed_generations: dict[str, ObservedGenerations1] | None = Field(
        None,
        description="N(바이블 §5.7 1.3.0; 요청 #172). object(키 backend_id, 값 index_generation 배열) — 백엔드별로 관측된 세대 목록(stale_current 등 세대 분포 진단)",
    )


class AclDocumentUpdatedData(ContractModel):
    """
    acl.document.updated. 주체 문자열 없음(acl_hash·열거만)
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    job_id: common_types.Ulid
    document_id: common_types.Ulid
    collection_id: common_types.Ulid
    acl_hash: common_types.Hex64
    previous_acl_hash: common_types.Hex64 | None
    visibility: common_types.Visibility = Field(
        ..., description="갱신 후 Acl.visibility(원천 생략 시 기본 tenant를 채워 기록)"
    )
    classification: common_types.Classification = Field(
        ...,
        description="갱신 후 Acl.classification. 원천(common-types Acl, N)이 생략되었으면 기본 internal을 채워 기록 — 이벤트에서는 항상 필수",
    )
    backends_updated: list[common_types.PluginId] = Field(..., max_length=8, min_length=1)
    revocation_hint_recorded: bool = Field(..., description="aclrev: 회수 힌트 기록 여부(E9)")
    propagation_ms: int | None = Field(None, description="접수 → 백엔드 갱신 완료(rag_acl_propagation_seconds)", ge=0)


class CollectionProfileChangedData(ContractModel):
    """
    collection.profile.changed. 프로파일(PATCH /v1/collections/{collection_id}·재색인 alias 교체)·사전(PUT /v1/collections/{collection_id}/dictionary, 16 §6.2 dictionary_hash 변경)·정책 변경 커밋의 투영. change_kind가 무엇이 바뀌었는지 밝힌다 — dictionary·policy 변경은 profile_hash가 불변이라 previous_profile_hash == profile_hash다(I-21)
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    collection_id: common_types.Ulid
    change_kind: CollectionProfileChangedData_1.ChangeKind
    profile_id: str = Field(..., max_length=64, pattern="^[a-z][a-z0-9]*(-[a-z0-9]+)*$")
    profile_hash: common_types.Hex64 = Field(..., description="변경 후 프로파일 해시")
    previous_profile_hash: common_types.Hex64 | None = Field(
        ...,
        description="변경 전 프로파일 해시(최초 지정은 null). change_kind ∈ {dictionary, policy}면 profile_hash와 같다",
    )
    embedding_profile_hash: common_types.Hex64
    analyzer_id: str = Field(
        ...,
        description="변경 후 analyzer_id({engine}:{version}:{dictionary}, 바이블 §6.1)",
        max_length=128,
        pattern="^[a-z][a-z0-9-]*:[^:\\s]+:[^\\s]+$",
    )
    previous_analyzer_id: str | None = Field(
        None,
        description="선택(N). 분석기가 바뀐 경우만(변경 전 analyzer_id)",
        max_length=128,
        pattern="^[a-z][a-z0-9-]*:[^:\\s]+:[^\\s]+$",
    )
    dictionary_hash: common_types.Hex64 = Field(..., description="변경 후 dictionary_hash(16 EF-23)")
    previous_dictionary_hash: common_types.Hex64 | None = Field(
        None,
        description="선택(N, null 허용). 변경 전 dictionary_hash(사전이 없었으면 null). change_kind=dictionary면 필수 — 16 §6.2 API 응답 previous_dictionary_hash와 같은 값",
    )
    reindex_required: bool = Field(
        ...,
        description="재색인이 필요한 변경인지(사전 변경은 16 §6.2 reindex_suggested와 같은 값)",
    )
    reindex_job_id: common_types.Ulid | None = Field(None, description="선택(N). 함께 접수된 reindex_collection 잡")


class CollectionReindexCompletedData(ContractModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    job_id: common_types.Ulid
    collection_id: common_types.Ulid
    profile_hash: common_types.Hex64
    document_count: int = Field(..., ge=0)
    succeeded_count: int = Field(..., ge=0)
    partial_count: int = Field(..., ge=0)
    failed_count: int = Field(..., ge=0)
    alias_swapped: bool
    gate_passed: bool | None = Field(..., description="게이트 미실행은 null")
    run_id: common_types.Ulid | None = Field(
        None,
        description="선택(N). 게이트 평가 EvalRun.run_id(바이블 §6.1; 게이트 미실행이면 생략)",
    )


class AuditQueryExecutedData(ContractModel):
    """
    audit.query.executed(바이블 §8.1 14단계). 질의 원문 없음 — query_hash만
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    query_id: common_types.Ulid
    plan_id: common_types.Ulid
    pack_id: common_types.Ulid | None = Field(..., description="route=no_retrieval이면 null")
    trace_id: str = Field(..., pattern="^[0-9a-f]{32}$")
    auth_method: common_types.AuthMethod
    principal_hash: common_types.Hex64 = Field(..., description='H("principal", tenant_id, subject)(07 문서 제안)')
    actor_client_id: str | None = Field(None, max_length=128)
    collection_ids: list[common_types.Ulid] = Field(..., max_length=20, min_length=1)
    query_hash: common_types.Hex64 = Field(
        ...,
        description="blake3_hex(utf8(normalized_query)) — 07 §8.2 hash_only 정책(라벨 없음; 미해결 이슈 8)",
    )
    filters_effective_hash: common_types.Hex64
    security_context_hash: common_types.Hex64
    profile_hash: common_types.Hex64
    returned: Returned
    omitted: Omitted
    degraded: list[common_types.DegradedEntry] = Field(..., max_length=64)
    latency_ms: int = Field(..., ge=0)


class AuditDocumentAccessedData(ContractModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    document_id: common_types.Ulid
    collection_id: common_types.Ulid | None = None
    view: AuditDocumentAccessedData_1.View
    principal_hash: common_types.Hex64
    decision: AuditDecision
    acl_hash: common_types.Hex64 | None = Field(..., description="거부(존재 비노출)면 null")


class AuditAclChangedData(ContractModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    document_id: common_types.Ulid
    collection_id: common_types.Ulid | None = None
    principal_hash: common_types.Hex64
    acl_hash_before: common_types.Hex64 | None
    acl_hash_after: common_types.Hex64
    job_id: common_types.Ulid = Field(..., description="acl.update.v1 잡")


class AuditAdminActionData(ContractModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    action: str = Field(
        ...,
        description="Cedar 액션명(예 collection.update, job.cancel)",
        max_length=64,
        pattern="^[a-z][a-z0-9_]*(\\.[a-z][a-z0-9_]*)*$",
    )
    resource: Resource
    principal_hash: common_types.Hex64
    decision: AuditDecision
    policy_version: str = Field(..., max_length=64, min_length=1)
    request_id: common_types.Ulid
    job_id: common_types.Ulid | None = None


class FeedbackQueryEventData(ContractModel):
    """
    feedback.query.cited·rated. comment 없음(PII)
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    feedback_id: common_types.Ulid
    query_id: common_types.Ulid
    pack_id: common_types.Ulid
    kind: common_types.FeedbackKind
    cite_ids: list[common_types.CiteId] = Field(..., max_length=20)
    rating: int | None = Field(None, ge=1, le=5)


class EvalRunCompletedData(ContractModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    run_id: common_types.Ulid
    dataset_id: common_types.Ulid
    profile_id: str = Field(..., max_length=64, pattern="^[a-z][a-z0-9]*(-[a-z0-9]+)*$")
    profile_hash: common_types.Hex64
    status: common_types.EvalRunStatus
    index_commit_ids: list[common_types.Ulid] = Field(..., max_length=1000)
    gate_passed: bool | None
    metrics: dict[str, float] = Field(
        ...,
        description="EvalReport.metrics 사본(ndcg@10, recall@20, mrr 등)",
        max_length=64,
    )


class Data(IngestStageEventData):
    """
    ID·해시·상태만. 콘텍스트 본문 금지(E12)
    """

    model_config = ConfigDict(
        extra="allow",
    )
    stage: Literal["fetch"] = Field(..., max_length=32, pattern="^[a-z][a-z0-9_]*$")


class CloudEventEnvelope1(ContractModel):
    """
    CloudEvents 1.0.2 봉투(바이블 §5.3·§6.5, ADR-0017)의 정제 래퍼. 봉투 자체는 urn:rag:schema:common-types:1#/$defs/CloudEventEnvelope 을 참조하고, 이 파일은 바이블 §5.7 이벤트 카탈로그 24종의 type ↔ data·subject 바인딩(oneOf)과 이벤트별 data 타입($defs)만 더한다. data는 ID·해시·상태·계수만 담고 콘텍스트 본문을 담지 않는다(E12). 소유 문서: docs/03-contracts/12-jobs-events-and-status.md
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    specversion: Literal["1.0"]
    id: common_types.Ulid = Field(..., description="event_id(소비자 멱등 키)")
    source: AnyUrl = Field(..., description="urn:rag:{component}")
    type: Literal["ingest.document.fetched"] = Field(
        ...,
        description="바이블 §5.7 이벤트 이름 카탈로그(domain.entity.action). CloudEventEnvelope.type. 1.3.0: tenant.policies.changed 추가(AM-38, 25종).",
    )
    time: common_types.DateTime
    subject: str = Field(
        ...,
        description="tenant/{tenant_id}/{entity}/{id}",
        pattern="^tenant/[0-9A-HJKMNP-TV-Z]{26}/[a-z_]+/[^/\\s]+$",
    )
    datacontenttype: Literal["application/json"]
    dataschema: common_types.SchemaId | None = None
    tenantid: common_types.Ulid = Field(..., description="CloudEvents 확장 속성(릴레이 테넌트 스코프)")
    data: Data = Field(..., description="ID·해시·상태만. 콘텍스트 본문 금지(E12)")


class Data1(IngestStageEventData):
    """
    ID·해시·상태만. 콘텍스트 본문 금지(E12)
    """

    model_config = ConfigDict(
        extra="allow",
    )
    stage: Literal["parse"] = Field(..., max_length=32, pattern="^[a-z][a-z0-9_]*$")
    stage_key: common_types.Hex64 = Field(..., description="fetch 이후 스테이지 필수")


class CloudEventEnvelope2(ContractModel):
    """
    CloudEvents 1.0.2 봉투(바이블 §5.3·§6.5, ADR-0017)의 정제 래퍼. 봉투 자체는 urn:rag:schema:common-types:1#/$defs/CloudEventEnvelope 을 참조하고, 이 파일은 바이블 §5.7 이벤트 카탈로그 24종의 type ↔ data·subject 바인딩(oneOf)과 이벤트별 data 타입($defs)만 더한다. data는 ID·해시·상태·계수만 담고 콘텍스트 본문을 담지 않는다(E12). 소유 문서: docs/03-contracts/12-jobs-events-and-status.md
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    specversion: Literal["1.0"]
    id: common_types.Ulid = Field(..., description="event_id(소비자 멱등 키)")
    source: AnyUrl = Field(..., description="urn:rag:{component}")
    type: Literal["ingest.document.parsed"] = Field(
        ...,
        description="바이블 §5.7 이벤트 이름 카탈로그(domain.entity.action). CloudEventEnvelope.type. 1.3.0: tenant.policies.changed 추가(AM-38, 25종).",
    )
    time: common_types.DateTime
    subject: str = Field(
        ...,
        description="tenant/{tenant_id}/{entity}/{id}",
        pattern="^tenant/[0-9A-HJKMNP-TV-Z]{26}/[a-z_]+/[^/\\s]+$",
    )
    datacontenttype: Literal["application/json"]
    dataschema: common_types.SchemaId | None = None
    tenantid: common_types.Ulid = Field(..., description="CloudEvents 확장 속성(릴레이 테넌트 스코프)")
    data: Data1 = Field(..., description="ID·해시·상태만. 콘텍스트 본문 금지(E12)")


class Data2(IngestStageEventData):
    """
    ID·해시·상태만. 콘텍스트 본문 금지(E12)
    """

    model_config = ConfigDict(
        extra="allow",
    )
    stage: Literal["normalize"] = Field(..., max_length=32, pattern="^[a-z][a-z0-9_]*$")
    stage_key: common_types.Hex64 = Field(..., description="fetch 이후 스테이지 필수")


class CloudEventEnvelope3(ContractModel):
    """
    CloudEvents 1.0.2 봉투(바이블 §5.3·§6.5, ADR-0017)의 정제 래퍼. 봉투 자체는 urn:rag:schema:common-types:1#/$defs/CloudEventEnvelope 을 참조하고, 이 파일은 바이블 §5.7 이벤트 카탈로그 24종의 type ↔ data·subject 바인딩(oneOf)과 이벤트별 data 타입($defs)만 더한다. data는 ID·해시·상태·계수만 담고 콘텍스트 본문을 담지 않는다(E12). 소유 문서: docs/03-contracts/12-jobs-events-and-status.md
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    specversion: Literal["1.0"]
    id: common_types.Ulid = Field(..., description="event_id(소비자 멱등 키)")
    source: AnyUrl = Field(..., description="urn:rag:{component}")
    type: Literal["ingest.document.normalized"] = Field(
        ...,
        description="바이블 §5.7 이벤트 이름 카탈로그(domain.entity.action). CloudEventEnvelope.type. 1.3.0: tenant.policies.changed 추가(AM-38, 25종).",
    )
    time: common_types.DateTime
    subject: str = Field(
        ...,
        description="tenant/{tenant_id}/{entity}/{id}",
        pattern="^tenant/[0-9A-HJKMNP-TV-Z]{26}/[a-z_]+/[^/\\s]+$",
    )
    datacontenttype: Literal["application/json"]
    dataschema: common_types.SchemaId | None = None
    tenantid: common_types.Ulid = Field(..., description="CloudEvents 확장 속성(릴레이 테넌트 스코프)")
    data: Data2 = Field(..., description="ID·해시·상태만. 콘텍스트 본문 금지(E12)")


class Data3(IngestStageEventData):
    """
    ID·해시·상태만. 콘텍스트 본문 금지(E12)
    """

    model_config = ConfigDict(
        extra="allow",
    )
    stage: Stage
    stage_key: common_types.Hex64 = Field(..., description="fetch 이후 스테이지 필수")


class CloudEventEnvelope4(ContractModel):
    """
    CloudEvents 1.0.2 봉투(바이블 §5.3·§6.5, ADR-0017)의 정제 래퍼. 봉투 자체는 urn:rag:schema:common-types:1#/$defs/CloudEventEnvelope 을 참조하고, 이 파일은 바이블 §5.7 이벤트 카탈로그 24종의 type ↔ data·subject 바인딩(oneOf)과 이벤트별 data 타입($defs)만 더한다. data는 ID·해시·상태·계수만 담고 콘텍스트 본문을 담지 않는다(E12). 소유 문서: docs/03-contracts/12-jobs-events-and-status.md
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    specversion: Literal["1.0"]
    id: common_types.Ulid = Field(..., description="event_id(소비자 멱등 키)")
    source: AnyUrl = Field(..., description="urn:rag:{component}")
    type: Literal["ingest.document.chunked"] = Field(
        ...,
        description="바이블 §5.7 이벤트 이름 카탈로그(domain.entity.action). CloudEventEnvelope.type. 1.3.0: tenant.policies.changed 추가(AM-38, 25종).",
    )
    time: common_types.DateTime
    subject: str = Field(
        ...,
        description="tenant/{tenant_id}/{entity}/{id}",
        pattern="^tenant/[0-9A-HJKMNP-TV-Z]{26}/[a-z_]+/[^/\\s]+$",
    )
    datacontenttype: Literal["application/json"]
    dataschema: common_types.SchemaId | None = None
    tenantid: common_types.Ulid = Field(..., description="CloudEvents 확장 속성(릴레이 테넌트 스코프)")
    data: Data3 = Field(..., description="ID·해시·상태만. 콘텍스트 본문 금지(E12)")


class Data4(IngestStageEventData):
    """
    ID·해시·상태만. 콘텍스트 본문 금지(E12)
    """

    model_config = ConfigDict(
        extra="allow",
    )
    stage: Literal["enrich"] = Field(..., max_length=32, pattern="^[a-z][a-z0-9_]*$")
    stage_key: common_types.Hex64 = Field(..., description="fetch 이후 스테이지 필수")


class CloudEventEnvelope5(ContractModel):
    """
    CloudEvents 1.0.2 봉투(바이블 §5.3·§6.5, ADR-0017)의 정제 래퍼. 봉투 자체는 urn:rag:schema:common-types:1#/$defs/CloudEventEnvelope 을 참조하고, 이 파일은 바이블 §5.7 이벤트 카탈로그 24종의 type ↔ data·subject 바인딩(oneOf)과 이벤트별 data 타입($defs)만 더한다. data는 ID·해시·상태·계수만 담고 콘텍스트 본문을 담지 않는다(E12). 소유 문서: docs/03-contracts/12-jobs-events-and-status.md
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    specversion: Literal["1.0"]
    id: common_types.Ulid = Field(..., description="event_id(소비자 멱등 키)")
    source: AnyUrl = Field(..., description="urn:rag:{component}")
    type: Literal["ingest.document.enriched"] = Field(
        ...,
        description="바이블 §5.7 이벤트 이름 카탈로그(domain.entity.action). CloudEventEnvelope.type. 1.3.0: tenant.policies.changed 추가(AM-38, 25종).",
    )
    time: common_types.DateTime
    subject: str = Field(
        ...,
        description="tenant/{tenant_id}/{entity}/{id}",
        pattern="^tenant/[0-9A-HJKMNP-TV-Z]{26}/[a-z_]+/[^/\\s]+$",
    )
    datacontenttype: Literal["application/json"]
    dataschema: common_types.SchemaId | None = None
    tenantid: common_types.Ulid = Field(..., description="CloudEvents 확장 속성(릴레이 테넌트 스코프)")
    data: Data4 = Field(..., description="ID·해시·상태만. 콘텍스트 본문 금지(E12)")


class Data5(IngestStageEventData):
    """
    ID·해시·상태만. 콘텍스트 본문 금지(E12)
    """

    model_config = ConfigDict(
        extra="allow",
    )
    stage: Literal["embed"] = Field(..., max_length=32, pattern="^[a-z][a-z0-9_]*$")
    stage_key: common_types.Hex64 = Field(..., description="fetch 이후 스테이지 필수")


class CloudEventEnvelope6(ContractModel):
    """
    CloudEvents 1.0.2 봉투(바이블 §5.3·§6.5, ADR-0017)의 정제 래퍼. 봉투 자체는 urn:rag:schema:common-types:1#/$defs/CloudEventEnvelope 을 참조하고, 이 파일은 바이블 §5.7 이벤트 카탈로그 24종의 type ↔ data·subject 바인딩(oneOf)과 이벤트별 data 타입($defs)만 더한다. data는 ID·해시·상태·계수만 담고 콘텍스트 본문을 담지 않는다(E12). 소유 문서: docs/03-contracts/12-jobs-events-and-status.md
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    specversion: Literal["1.0"]
    id: common_types.Ulid = Field(..., description="event_id(소비자 멱등 키)")
    source: AnyUrl = Field(..., description="urn:rag:{component}")
    type: Literal["ingest.document.embedded"] = Field(
        ...,
        description="바이블 §5.7 이벤트 이름 카탈로그(domain.entity.action). CloudEventEnvelope.type. 1.3.0: tenant.policies.changed 추가(AM-38, 25종).",
    )
    time: common_types.DateTime
    subject: str = Field(
        ...,
        description="tenant/{tenant_id}/{entity}/{id}",
        pattern="^tenant/[0-9A-HJKMNP-TV-Z]{26}/[a-z_]+/[^/\\s]+$",
    )
    datacontenttype: Literal["application/json"]
    dataschema: common_types.SchemaId | None = None
    tenantid: common_types.Ulid = Field(..., description="CloudEvents 확장 속성(릴레이 테넌트 스코프)")
    data: Data5 = Field(..., description="ID·해시·상태만. 콘텍스트 본문 금지(E12)")


class Data7(IngestFailureEventData):
    """
    ID·해시·상태만. 콘텍스트 본문 금지(E12)
    """

    model_config = ConfigDict(
        extra="allow",
    )
    retryable: Literal[True]


class CloudEventEnvelope8(ContractModel):
    """
    CloudEvents 1.0.2 봉투(바이블 §5.3·§6.5, ADR-0017)의 정제 래퍼. 봉투 자체는 urn:rag:schema:common-types:1#/$defs/CloudEventEnvelope 을 참조하고, 이 파일은 바이블 §5.7 이벤트 카탈로그 24종의 type ↔ data·subject 바인딩(oneOf)과 이벤트별 data 타입($defs)만 더한다. data는 ID·해시·상태·계수만 담고 콘텍스트 본문을 담지 않는다(E12). 소유 문서: docs/03-contracts/12-jobs-events-and-status.md
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    specversion: Literal["1.0"]
    id: common_types.Ulid = Field(..., description="event_id(소비자 멱등 키)")
    source: AnyUrl = Field(..., description="urn:rag:{component}")
    type: Literal["ingest.document.retried"] = Field(
        ...,
        description="바이블 §5.7 이벤트 이름 카탈로그(domain.entity.action). CloudEventEnvelope.type. 1.3.0: tenant.policies.changed 추가(AM-38, 25종).",
    )
    time: common_types.DateTime
    subject: str = Field(
        ...,
        description="tenant/{tenant_id}/{entity}/{id}",
        pattern="^tenant/[0-9A-HJKMNP-TV-Z]{26}/[a-z_]+/[^/\\s]+$",
    )
    datacontenttype: Literal["application/json"]
    dataschema: common_types.SchemaId | None = None
    tenantid: common_types.Ulid = Field(..., description="CloudEvents 확장 속성(릴레이 테넌트 스코프)")
    data: Data7 = Field(..., description="ID·해시·상태만. 콘텍스트 본문 금지(E12)")


class Data10(ContractModel):
    """
    ID·해시·상태만. 콘텍스트 본문 금지(E12)
    """

    model_config = ConfigDict(
        extra="allow",
    )
    job_id: common_types.Ulid
    kind: common_types.JobKind
    collection_id: common_types.Ulid
    from_state: common_types.JobState | None = Field(..., description="접수(첫 queued)는 null")
    to_state: common_types.JobState
    stage: StageName | None
    attempts: int = Field(..., ge=0)
    progress: job_status.JobProgress | None = None
    document_id: common_types.Ulid | None = None
    index_commit_id: common_types.Ulid | None = None
    waiting_for: common_types.Ulid | None = None
    error: Error | None = Field(None, description="StageError 투영(13 J3)")
    reason: str | None = Field(None, description="취소·기한 사유(영문, 콘텐츠 미포함)", max_length=256)


class CloudEventEnvelope11(ContractModel):
    """
    CloudEvents 1.0.2 봉투(바이블 §5.3·§6.5, ADR-0017)의 정제 래퍼. 봉투 자체는 urn:rag:schema:common-types:1#/$defs/CloudEventEnvelope 을 참조하고, 이 파일은 바이블 §5.7 이벤트 카탈로그 24종의 type ↔ data·subject 바인딩(oneOf)과 이벤트별 data 타입($defs)만 더한다. data는 ID·해시·상태·계수만 담고 콘텍스트 본문을 담지 않는다(E12). 소유 문서: docs/03-contracts/12-jobs-events-and-status.md
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    specversion: Literal["1.0"]
    id: common_types.Ulid = Field(..., description="event_id(소비자 멱등 키)")
    source: AnyUrl = Field(..., description="urn:rag:{component}")
    type: Literal["job.state.changed"] = Field(
        ...,
        description="바이블 §5.7 이벤트 이름 카탈로그(domain.entity.action). CloudEventEnvelope.type. 1.3.0: tenant.policies.changed 추가(AM-38, 25종).",
    )
    time: common_types.DateTime
    subject: str = Field(
        ...,
        description="tenant/{tenant_id}/{entity}/{id}",
        pattern="^tenant/[0-9A-HJKMNP-TV-Z]{26}/job/[0-9A-HJKMNP-TV-Z]{26}$",
    )
    datacontenttype: Literal["application/json"]
    dataschema: common_types.SchemaId | None = None
    tenantid: common_types.Ulid = Field(..., description="CloudEvents 확장 속성(릴레이 테넌트 스코프)")
    data: Data10 = Field(..., description="ID·해시·상태만. 콘텍스트 본문 금지(E12)")


class Data21(FeedbackQueryEventData):
    """
    ID·해시·상태만. 콘텍스트 본문 금지(E12)
    """

    model_config = ConfigDict(
        extra="allow",
    )
    kind: Literal["cited"]


class CloudEventEnvelope22(ContractModel):
    """
    CloudEvents 1.0.2 봉투(바이블 §5.3·§6.5, ADR-0017)의 정제 래퍼. 봉투 자체는 urn:rag:schema:common-types:1#/$defs/CloudEventEnvelope 을 참조하고, 이 파일은 바이블 §5.7 이벤트 카탈로그 24종의 type ↔ data·subject 바인딩(oneOf)과 이벤트별 data 타입($defs)만 더한다. data는 ID·해시·상태·계수만 담고 콘텍스트 본문을 담지 않는다(E12). 소유 문서: docs/03-contracts/12-jobs-events-and-status.md
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    specversion: Literal["1.0"]
    id: common_types.Ulid = Field(..., description="event_id(소비자 멱등 키)")
    source: AnyUrl = Field(..., description="urn:rag:{component}")
    type: Literal["feedback.query.cited"] = Field(
        ...,
        description="바이블 §5.7 이벤트 이름 카탈로그(domain.entity.action). CloudEventEnvelope.type. 1.3.0: tenant.policies.changed 추가(AM-38, 25종).",
    )
    time: common_types.DateTime
    subject: str = Field(
        ...,
        description="tenant/{tenant_id}/{entity}/{id}",
        pattern="^tenant/[0-9A-HJKMNP-TV-Z]{26}/[a-z_]+/[^/\\s]+$",
    )
    datacontenttype: Literal["application/json"]
    dataschema: common_types.SchemaId | None = None
    tenantid: common_types.Ulid = Field(..., description="CloudEvents 확장 속성(릴레이 테넌트 스코프)")
    data: Data21 = Field(..., description="ID·해시·상태만. 콘텍스트 본문 금지(E12)")


class Data22(FeedbackQueryEventData):
    """
    ID·해시·상태만. 콘텍스트 본문 금지(E12)
    """

    model_config = ConfigDict(
        extra="allow",
    )
    kind: Kind2


class CloudEventEnvelope23(ContractModel):
    """
    CloudEvents 1.0.2 봉투(바이블 §5.3·§6.5, ADR-0017)의 정제 래퍼. 봉투 자체는 urn:rag:schema:common-types:1#/$defs/CloudEventEnvelope 을 참조하고, 이 파일은 바이블 §5.7 이벤트 카탈로그 24종의 type ↔ data·subject 바인딩(oneOf)과 이벤트별 data 타입($defs)만 더한다. data는 ID·해시·상태·계수만 담고 콘텍스트 본문을 담지 않는다(E12). 소유 문서: docs/03-contracts/12-jobs-events-and-status.md
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    specversion: Literal["1.0"]
    id: common_types.Ulid = Field(..., description="event_id(소비자 멱등 키)")
    source: AnyUrl = Field(..., description="urn:rag:{component}")
    type: Literal["feedback.query.rated"] = Field(
        ...,
        description="바이블 §5.7 이벤트 이름 카탈로그(domain.entity.action). CloudEventEnvelope.type. 1.3.0: tenant.policies.changed 추가(AM-38, 25종).",
    )
    time: common_types.DateTime
    subject: str = Field(
        ...,
        description="tenant/{tenant_id}/{entity}/{id}",
        pattern="^tenant/[0-9A-HJKMNP-TV-Z]{26}/[a-z_]+/[^/\\s]+$",
    )
    datacontenttype: Literal["application/json"]
    dataschema: common_types.SchemaId | None = None
    tenantid: common_types.Ulid = Field(..., description="CloudEvents 확장 속성(릴레이 테넌트 스코프)")
    data: Data22 = Field(..., description="ID·해시·상태만. 콘텍스트 본문 금지(E12)")


class CloudEventEnvelope(
    RootModel[
        CloudEventEnvelope1
        | CloudEventEnvelope2
        | CloudEventEnvelope3
        | CloudEventEnvelope4
        | CloudEventEnvelope5
        | CloudEventEnvelope6
        | CloudEventEnvelope7
        | CloudEventEnvelope8
        | CloudEventEnvelope9
        | CloudEventEnvelope10
        | CloudEventEnvelope11
        | CloudEventEnvelope12
        | CloudEventEnvelope13
        | CloudEventEnvelope14
        | CloudEventEnvelope15
        | CloudEventEnvelope16
        | CloudEventEnvelope17
        | CloudEventEnvelope18
        | CloudEventEnvelope19
        | CloudEventEnvelope20
        | CloudEventEnvelope21
        | CloudEventEnvelope22
        | CloudEventEnvelope23
        | CloudEventEnvelope24
    ]
):
    root: (
        CloudEventEnvelope1
        | CloudEventEnvelope2
        | CloudEventEnvelope3
        | CloudEventEnvelope4
        | CloudEventEnvelope5
        | CloudEventEnvelope6
        | CloudEventEnvelope7
        | CloudEventEnvelope8
        | CloudEventEnvelope9
        | CloudEventEnvelope10
        | CloudEventEnvelope11
        | CloudEventEnvelope12
        | CloudEventEnvelope13
        | CloudEventEnvelope14
        | CloudEventEnvelope15
        | CloudEventEnvelope16
        | CloudEventEnvelope17
        | CloudEventEnvelope18
        | CloudEventEnvelope19
        | CloudEventEnvelope20
        | CloudEventEnvelope21
        | CloudEventEnvelope22
        | CloudEventEnvelope23
        | CloudEventEnvelope24
    ) = Field(
        ...,
        description="CloudEvents 1.0.2 봉투(바이블 §5.3·§6.5, ADR-0017)의 정제 래퍼. 봉투 자체는 urn:rag:schema:common-types:1#/$defs/CloudEventEnvelope 을 참조하고, 이 파일은 바이블 §5.7 이벤트 카탈로그 24종의 type ↔ data·subject 바인딩(oneOf)과 이벤트별 data 타입($defs)만 더한다. data는 ID·해시·상태·계수만 담고 콘텍스트 본문을 담지 않는다(E12). 소유 문서: docs/03-contracts/12-jobs-events-and-status.md",
        title="CloudEventEnvelope",
    )


class JobStateChangedData(ContractModel):
    """
    job.state.changed. 바이블 §11.5 전이 1건(job_events 행의 투영)
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    job_id: common_types.Ulid
    kind: common_types.JobKind
    collection_id: common_types.Ulid
    from_state: common_types.JobState | None = Field(..., description="접수(첫 queued)는 null")
    to_state: common_types.JobState
    stage: StageName | None
    attempts: int = Field(..., ge=0)
    progress: job_status.JobProgress | None = None
    document_id: common_types.Ulid | None = None
    index_commit_id: common_types.Ulid | None = None
    waiting_for: common_types.Ulid | None = None
    error: Error | None = Field(None, description="StageError 투영(13 J3)")
    reason: str | None = Field(None, description="취소·기한 사유(영문, 콘텐츠 미포함)", max_length=256)
