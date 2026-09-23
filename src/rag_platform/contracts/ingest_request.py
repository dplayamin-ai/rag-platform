"""GENERATED — 수정 금지. 재생성: `uv run python tools/contracts_gen.py`

역할: `schemas/*.schema.json`의 계약 스키마 하나를 그대로 옮긴 Pydantic v2 모델(계층 L0) — 파이프라인 단계 간에 주고받는 데이터의 타입을 정의한다.
설계 근거: 바이블 §5.1(계약이 정본), §6.4(kebab 스키마 이름 ↔ snake_case 모듈명), §12(레이어 지도).
구성: 클래스명은 스키마의 `title`(또는 `$defs`의 각 항목)과 동일하며, 필드는 스키마의 `properties`/`required`를 그대로 반영한다.
불변식: `tools/contracts_gen.py`만 이 파일을 쓴다 — 손으로 고친 내용은 다음 재생성 때 사라진다.
검증 계층: 1층(여기서 검증) — tests/contracts, tools/validate-contracts.mjs.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import AnyUrl, ConfigDict, Field, RootModel, constr

from rag_platform.contracts.contract_model import ContractModel

from . import common_types


class Author(RootModel[str]):
    root: str = Field(..., max_length=256, min_length=1)


class Tag(RootModel[str]):
    root: str = Field(..., max_length=128, min_length=1)


class CustomMetadata1(RootModel[str]):
    root: str = Field(..., max_length=1024)


class CustomMetadata(RootModel[dict[constr(pattern=r"^[a-z][a-z0-9_]{0,63}$"), CustomMetadata1 | float | bool]]):
    root: dict[constr(pattern=r"^[a-z][a-z0-9_]{0,63}$"), CustomMetadata1 | float | bool] = Field(
        ...,
        description="열린 객체(00-contract-overview §8.2). 키는 snake_case ≤ 64자, 값은 스칼라(string ≤ 1,024 | number | boolean). 키 ≤ 64개(02 SourceMetadata.custom 과 동일).",
        max_length=64,
    )


class Event(StrEnum):
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
    job_state_changed_1 = "job.state.changed"
    ingest_document_fetched_1 = "ingest.document.fetched"
    ingest_document_parsed_1 = "ingest.document.parsed"
    ingest_document_normalized_1 = "ingest.document.normalized"
    ingest_document_chunked_1 = "ingest.document.chunked"
    ingest_document_enriched_1 = "ingest.document.enriched"
    ingest_document_embedded_1 = "ingest.document.embedded"
    ingest_document_indexed_1 = "ingest.document.indexed"
    ingest_document_retried_1 = "ingest.document.retried"
    ingest_document_failed_1 = "ingest.document.failed"
    index_commit_published_1 = "index.commit.published"
    index_commit_rolled_back_1 = "index.commit.rolled_back"


class IngestCallback(ContractModel):
    """
    잡 단위 웹훅 콜백. webhook_url 은 테넌트의 등록 구독(subscriptions.webhook_url)과 일치해야 서명 키(secret_ref)를 해소할 수 있다.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    webhook_url: AnyUrl = Field(
        ...,
        description="https 기본, http 는 테넌트 옵트인(EgressPolicy.allowed_schemes). userinfo 금지",
    )
    events: list[Event] | None = Field(
        None,
        description="구독 이벤트(바이블 §5.7 카탈로그 중 이 잡이 발행하는 부분집합). 생략 시 [job.state.changed]",
        max_length=12,
        min_length=1,
    )


class EnrichGeneratedPrefix(ContractModel):
    """
    LLM 접두어 켬/끔. 켜려면 llm_enrichment_allowed 와 테넌트·컬렉션 정책이 모두 참이어야 한다(O-05)
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    enabled: bool


class ProfileOverrides(ContractModel):
    """
    요청 단위 프로파일 오버라이드. 키는 프로파일 YAML 경로(점 구분). 허용 키 집합은 컬렉션 프로파일이 선언하며 스키마는 바이블 §5.4 의 두 예시 키만 형태를 고정한다. 허용 밖 키·값은 422 profile.invalid.
    """

    model_config = ConfigDict(
        extra="allow",
    )
    parse_pdf_route: str | None = Field(
        None,
        alias="parse.pdf.route",
        description="PDF 라우트 이름(pdf_fast_cpu, pdf_standard, pdf_scanned_gpu, pdf_airgapped 등 프로파일 정의)",
        pattern="^[a-z][a-z0-9_]{0,63}$",
    )
    enrich_generated_prefix: EnrichGeneratedPrefix | None = Field(
        None,
        alias="enrich.generated_prefix",
        description="LLM 접두어 켬/끔. 켜려면 llm_enrichment_allowed 와 테넌트·컬렉션 정책이 모두 참이어야 한다(O-05)",
    )


class CredentialsRef(RootModel[str]):
    root: str = Field(
        ...,
        description="{provider}:{path}. 형식만 검증하며 provider(RAG_SECRETS__PROVIDER env|openbao|aws_kms, 바이블 §6.6) 유효성은 KeyProvider 해소 시 워커가 판정한다. 상한 256 은 SourceDocument.credentials_ref(02)와 동일. 값은 SourceDocument·ConvertRequest 로 그대로 전파되고 로그·트레이스·이벤트에는 기록하지 않는다",
        max_length=256,
        min_length=1,
        pattern="^[a-z][a-z0-9_]*:[^\\s]{1,240}$",
    )


class IdempotencyKey(RootModel[str]):
    root: str = Field(
        ...,
        description="Idempotency-Key 헤더 값(draft-ietf-httpapi-idempotency-key-header-07). 가시 ASCII, 서버에 불투명. 권장 UUIDv4 또는 ULID. 스코프 (tenant_id, key), TTL 24h(초안 목표)",
        max_length=255,
        min_length=1,
        pattern="^[\\x21-\\x7E]+$",
    )


class IngestAccepted(ContractModel):
    """
    POST /v1/ingest 202 응답 본문(D-08, 바이블 §14 {job_id, status_url, events_url}). request_id·document_id 는 선택(N; 바이블 §14 반영 제안). 같은 Idempotency-Key 재전송의 200 응답도 동일 본문.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    job_id: common_types.Ulid = Field(..., description="ingest.document.v1 워크플로우 ID")
    request_id: common_types.Ulid | None = Field(
        None,
        description="서버 발급 IngestRequest.request_id. 선택(N) — 바이블 §14 응답 표에 없음(§5.4 와 상충), 반영 제안",
    )
    document_id: common_types.Ulid | None = Field(
        None,
        description="접수 시 확정된 문서 ID(바이블 §11.2). 선택(N) — 바이블 §14 응답 표에 없어 반영 제안",
    )
    status_url: common_types.Uri = Field(..., description="GET /v1/jobs/{job_id} 절대 URL")
    events_url: common_types.Uri = Field(..., description="GET /v1/jobs/{job_id}/events SSE 절대 URL")


class IngestBatchAccepted(ContractModel):
    """
    POST /v1/ingest/batch 202 응답 본문. jobs[i] 는 요청 배열 i 번째 항목의 접수 결과.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    jobs: list[IngestAccepted] = Field(..., max_length=100, min_length=1)


class IngestMetadata(ContractModel):
    """
    예약 메타데이터 키(바이블 §5.4). doc_date·doc_type·department·tags·language_hint(→lang)·genre 는 §5.7 FilterableField 와 정합. 정규화(01-ingest-request §6)는 스키마 검증 전에 수행되므로 uniqueItems·패턴·길이는 정규화된 저장 인스턴스에 대한 제약이다. canonical_json 크기 ≤ 16KB(바이블 §5.1). authors·tags·custom 상한은 02 SourceMetadata 와 동일.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    title: str | None = Field(
        None,
        description="문서 제목. NFC·trim·공백 축약. 부재 시 파서 메타 → 첫 heading level 0 → source_uri 마지막 경로 요소 순으로 보완",
        max_length=512,
        min_length=1,
    )
    authors: list[Author] | None = Field(
        None,
        description="작성자·작성 기관(NFC·trim·순서 보존 중복 제거 후)",
        max_length=64,
    )
    doc_date: common_types.Date | None = Field(
        None, description="문서 일자(YYYY-MM-DD). 팩 헤더·상충 판정·필터 doc_date"
    )
    doc_type: str | None = Field(
        None,
        description="문서 종류 keyword(snake_case). 예 regulation, press_release, report. 필터 doc_type",
        pattern="^[a-z][a-z0-9_]{0,63}$",
    )
    department: str | None = Field(
        None,
        description="소관 부서·기관(NFC·trim). 필터 department",
        max_length=256,
        min_length=1,
    )
    language_hint: common_types.Bcp47 | None = Field(
        None,
        description="기본 ko. 힌트만(블록 단위 lang 은 normalize 가 판정). 필터 lang 의 문서 기본값",
    )
    tags: list[Tag] | None = Field(
        None,
        description="필터용 keyword(정확 일치). NFC·trim·순서 보존 중복 제거(정규화) 후의 값에 uniqueItems 적용",
        max_length=64,
    )
    genre: common_types.Genre | None = Field(None, description="청커 장르 라우팅(law_article 등). 생략 시 unknown")
    custom: CustomMetadata | None = Field(
        None,
        description="테넌트 정의 keyword 메타. 컬렉션 filterable_fields 에 선언된 키만 필터·IndexRecord.custom 투영",
    )


class IngestRequest(ContractModel):
    """
    수집 요청 계약(바이블 §5.4). 클라이언트가 POST /v1/ingest 로 제출하는 문서 위치(URI)·메타데이터·ACL·정책. tenant_id 는 본문에 없고(SecurityContext 에서 도출, E1) request_id 는 서버가 발급한다(readOnly). 비밀 값은 credentials_ref 간접 참조로만 받는다. 소비: fetch, API.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    schema_version: str = Field(
        ...,
        description='계약 버전. 초기 "1.0.0"; 이 스키마($id major 1)는 1.x 만 수용',
        pattern="^1\\.(0|[1-9]\\d*)\\.(0|[1-9]\\d*)$",
    )
    request_id: common_types.Ulid = Field(
        ...,
        description="서버 발급(접수 시 ULID). 클라이언트 본문에 존재하면 400 contract.violation. 202 응답 IngestAccepted.request_id(N)로 job_id 와 함께 반환",
    )
    collection_id: common_types.Ulid = Field(
        ...,
        description="프로파일이 고정된 컬렉션. SecurityContext.collection_ids(Cedar allowed_collections) 밖이면 403 auth.forbidden(E2, 존재 비노출)",
    )
    source_uri: AnyUrl = Field(
        ...,
        description="절대 URI. s3://, gs://, az://, file://, http(s)://, smb://(플러그인). authority 에 userinfo(user:pass@) 금지. 스킴·호스트 허용 여부는 fetch 가 EgressPolicy(E16)로 판정 — 위반은 fetch.scheme_unsupported / fetch.egress_denied",
    )
    media_type_hint: common_types.MediaType | None = Field(None, description="힌트만. 시그니처 판정(detect)이 우선")
    external_id: str | None = Field(
        None,
        description="원천 시스템 문서 ID. document_id 재사용 키(갱신·삭제 조회 키)",
        max_length=512,
        min_length=1,
    )
    external_version: str | None = Field(
        None,
        description="원천 버전 라벨(etag 등). 참고 정보이며 doc_version 은 content_hash 로만 결정된다(ADR-0005)",
        max_length=256,
        min_length=1,
    )
    metadata: IngestMetadata | None = Field(
        None, description="예약 메타데이터 키(바이블 §5.4)와 custom. 생략 시 {} 로 취급"
    )
    acl: common_types.Acl = Field(
        ...,
        description="문서 단위 ACL(D-09, 바이블 §10.1). 모든 레벨 레코드·부모 번들이 상속",
    )
    pii_policy: common_types.PiiPolicy | None = Field(
        None,
        description="생략 시 컬렉션 기본값 상속(확정값은 SourceDocument.pii_policy)",
    )
    pii_tokenize_mode: common_types.PiiTokenizeMode | None = Field(
        None, description="pii_policy=tokenize 일 때만 존재 가능. 생략 시 encrypt"
    )
    credentials_ref: CredentialsRef | None = Field(
        None,
        description="KeyProvider 간접 참조(암호화 문서 비밀번호·원천 토큰). 비밀 값 자체를 본문에 넣으면 400 contract.violation",
    )
    allow_distribution_documents: bool | None = Field(
        None,
        description="배포용 HWP 텍스트 폴백 허용(테넌트 정책과 AND). 생략 시 false",
    )
    llm_enrichment_allowed: bool | None = Field(
        None,
        description="외부 LLM 보강 옵트인(테넌트·컬렉션 정책과 AND). 생략 시 false",
    )
    dedup_policy: common_types.DedupPolicy | None = Field(
        None,
        description="생략 시 skip_if_same_hash. reindex_always 는 같은 chunk_id 집합이라도 새 index_generation 으로 적재(§11.4)",
    )
    priority: int | None = Field(None, description="생략 시 5. PATCH /v1/jobs/{job_id} 로 변경 가능", ge=0, le=9)
    callback: IngestCallback | None = Field(
        None,
        description="잡 단위 웹훅 콜백. 릴레이가 EgressPolicy(E16)로 검사하고 subscriptions.secret_ref 로 HMAC 서명",
    )
    split_hint: common_types.SplitHint | None = Field(
        None,
        description="컨테이너 내 다중 문서 분할. 생략 시 none. json_array 는 멤버 분할 후 txt 라우팅(바이블 §7.3)",
    )
    profile_overrides: ProfileOverrides | None = Field(
        None,
        description="컬렉션 프로파일이 허용한 키만(parse.pdf.route, enrich.generated_prefix). 그 외 키는 422 profile.invalid",
    )
    deadline_at: common_types.DateTime | None = Field(
        None,
        description="이 시각까지 시작하지 못하면 cancelled. requested_at 보다 뒤여야 한다",
    )
    requested_at: common_types.DateTime = Field(
        ...,
        description="클라이언트 요청 시각(RFC 3339 UTC). 멱등 본문 지문에 포함되므로 재전송 시 같은 값을 보낸다",
    )


class IngestBatchRequest(RootModel[list[IngestRequest]]):
    """
    POST /v1/ingest/batch 본문: IngestRequest 배열(1..100, 바이블 §14). 배열 순서가 응답 jobs[] 순서다. 검증은 전체 원자적(한 건이라도 위반이면 400 + errors[].location.pointer /{index}/{field}).
    """

    root: list[IngestRequest] = Field(
        ...,
        description="POST /v1/ingest/batch 본문: IngestRequest 배열(1..100, 바이블 §14). 배열 순서가 응답 jobs[] 순서다. 검증은 전체 원자적(한 건이라도 위반이면 400 + errors[].location.pointer /{index}/{field}).",
        max_length=100,
        min_length=1,
    )
