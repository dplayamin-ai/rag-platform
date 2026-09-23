"""GENERATED — 수정 금지. 재생성: `uv run python tools/contracts_gen.py`

역할: `schemas/*.schema.json`의 계약 스키마 하나를 그대로 옮긴 Pydantic v2 모델(계층 L0) — 파이프라인 단계 간에 주고받는 데이터의 타입을 정의한다.
설계 근거: 바이블 §5.1(계약이 정본), §6.4(kebab 스키마 이름 ↔ snake_case 모듈명), §12(레이어 지도).
구성: 클래스명은 스키마의 `title`(또는 `$defs`의 각 항목)과 동일하며, 필드는 스키마의 `properties`/`required`를 그대로 반영한다.
불변식: `tools/contracts_gen.py`만 이 파일을 쓴다 — 손으로 고친 내용은 다음 재생성 때 사라진다.
검증 계층: 1층(여기서 검증) — tests/contracts, tools/validate-contracts.mjs.
"""

from __future__ import annotations

from typing import Literal

from pydantic import AnyUrl, ConfigDict, Field, RootModel, constr

from rag_platform.contracts.contract_model import ContractModel

from . import common_types


class LineageRefs(ContractModel):
    """
    fetch·detect 출력 모두 빈 객체 {}. 원본 바이트는 artifact로 참조하고(00 §3.2 fetch 행), detect는 같은 schema_type을 출력하므로 fetch 출력을 source 키에 넣지 않는다(02 §1.2; fetch→detect 관계는 lineage 원장 행)
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    source: common_types.ArtifactRef | None = None
    parsed: common_types.ArtifactRef | None = None
    normalized: common_types.ArtifactRef | None = None
    chunk_set: common_types.ArtifactRef | None = None
    enriched: common_types.ArtifactRef | None = None
    embedded: common_types.ArtifactRef | None = None


class ContainerFlags(ContractModel):
    """
    detect가 채우는 컨테이너 플래그(바이블 §5.4). 판정만 하며 오류(parse.document_encrypted, parse.distribution_document)는 parse가 결정한다.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    encrypted: bool = Field(..., description="HWP FileHeader 암호 비트·HWPX manifest 암호화·PDF /Encrypt")
    distribution: bool = Field(..., description="HWP 배포용 문서 비트(ViewText)")
    compressed: bool = Field(..., description="HWP FileHeader 압축 비트 또는 ZIP 컨테이너(hwpx·docx·odt)")
    hwp_version: str | None = Field(
        None,
        description="HWP FileHeader 버전(5.0.x.x). hwp5·hwp3 외 포맷은 null 또는 생략",
        pattern="^\\d+\\.\\d+\\.\\d+\\.\\d+$",
    )


class HttpMetadata(ContractModel):
    """
    원천이 준 검증자·인코딩(바이블 §5.4). 조건부 재수집(If-None-Match/If-Modified-Since)과 TXT/HTML 디코딩 힌트에 쓴다.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    etag: str | None = Field(
        None,
        description="HTTP ETag 또는 S3 호환 ETag(따옴표 포함 원문)",
        max_length=256,
        min_length=1,
    )
    last_modified: str | None = Field(None, description="HTTP-date 원문(RFC 9110 §5.6.7)", max_length=64, min_length=1)
    charset: str | None = Field(
        None,
        description="Content-Type charset 파라미터(원 인코딩 힌트)",
        max_length=64,
        min_length=1,
        pattern="^[A-Za-z0-9][A-Za-z0-9._:-]*$",
    )


class Author(RootModel[str]):
    root: str = Field(..., max_length=256, min_length=1)


class Tag(RootModel[str]):
    root: str = Field(..., max_length=128, min_length=1)


class Custom(RootModel[str]):
    root: str = Field(..., max_length=1024)


class SourceMetadata(ContractModel):
    """
    IngestRequest.metadata 복사(바이블 §5.4). 제약은 urn:rag:schema:ingest-request:1#/$defs/IngestMetadata와 자구까지 동일(01 §2.2·§2.3·V10; 공용 $defs 승격 전까지 복제). 모든 키 선택. 정규화(NFC·trim·중복 제거)는 01이 접수 시 수행했으므로 여기서는 검증만 한다. custom은 열린 객체(값 string ≤ 1,024 | number | boolean).
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    title: str | None = Field(None, description="IndexRecord.title 1순위 원천", max_length=512, min_length=1)
    authors: list[Author] | None = Field(None, description="작성자·작성 기관", max_length=64)
    doc_date: common_types.Date | None = Field(None, description="팩 헤더·상충 판정·필터")
    doc_type: str | None = Field(
        None,
        description="문서 종류 keyword(snake_case). 예 regulation, press_release, report",
        pattern="^[a-z][a-z0-9_]{0,63}$",
    )
    department: str | None = Field(None, description="소관 부서·기관", max_length=256, min_length=1)
    language_hint: common_types.Bcp47 | None = Field(None, description="기본 ko. 파서·OCR 언어 힌트")
    tags: list[Tag] | None = Field(None, description="필터용 keyword(정확 일치, 중복 없음)", max_length=64)
    genre: common_types.Genre | None = Field(None, description="청커 장르 라우팅. 생략 시 unknown(01 §2.2)")
    custom: dict[constr(pattern=r"^[a-z][a-z0-9_]{0,63}$"), Custom | float | bool] | None = Field(
        None,
        description="테넌트 정의 keyword 메타(01 $defs/CustomMetadata와 동일). 컬렉션 filterable_fields에 선언된 키만 필터 가능(custom.{key})",
        max_length=64,
    )


class FetchReport(ContractModel):
    """
    fetch 진단(바이블 §5.4 {attempts, bytes_per_sec, redirects}). http_status·conditional_request·not_modified·duration_ms는 바이블 미등재 선택 키(02 미해결 이슈 3). URI·헤더 원문·콘텐츠는 담지 않는다.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    attempts: int = Field(..., description="성공까지의 시도 횟수(StagePolicy.max_attempts 대비)", ge=1)
    bytes_per_sec: float = Field(..., description="전송 처리량. 304면 0", ge=0.0)
    redirects: int = Field(..., description="따라간 리다이렉트 수(EgressPolicy.max_redirects 이하)", ge=0)
    http_status: int | None = Field(None, description="최종 응답 상태(http·https만)", ge=100, le=599)
    conditional_request: bool | None = Field(None, description="검증자로 조건부 GET을 보냈는지")
    not_modified: bool | None = Field(None, description="304 → 이전 원본 바이트 재사용")
    duration_ms: int | None = Field(None, description="연결 시작~저장 완료", ge=0)


class Signal(RootModel[str]):
    root: str = Field(..., max_length=256, min_length=1)


class Candidate(ContractModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    format: common_types.SourceFormat
    confidence: float = Field(..., ge=0.0, le=1.0)


class DetectReport(ContractModel):
    """
    포맷 판별 근거(바이블 미등재 선택 하위 타입, 02 미해결 이슈 3). detect 출력에만 존재한다. 판별기 지문은 봉투 producer가 담으므로 반복하지 않는다. 콘텐츠 미포함(시그니처 이름·컨테이너 항목 이름만).
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    signals: list[Signal] = Field(
        ...,
        description="판정에 쓴 신호 이름(예 zip:mimetype=application/hwp+zip, ole:FileHeader, pdf:header)",
        max_length=32,
        min_length=1,
    )
    hint_media_type: str | None = Field(None, description="IngestRequest.media_type_hint 원문", max_length=256)
    hint_agrees: bool | None = Field(None, description="힌트와 판정이 일치하는지(힌트 없으면 null)")
    candidates: list[Candidate] | None = Field(
        None,
        description="후보 포맷과 신뢰도(내림차순). 첫 항목 = format·format_confidence",
        max_length=13,
    )


class DedupReport(ContractModel):
    """
    중복 감지 결과(바이블 미등재 선택 하위 타입, 02 미해결 이슈 3). 워크플로우가 dedup_policy 판정에 쓴다.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    policy: common_types.DedupPolicy = Field(..., description="확정 정책(요청 > 컬렉션 기본 skip_if_same_hash)")
    previous_doc_version: common_types.Hex64 | None = Field(
        ..., description="같은 document_id의 documents.current_doc_version(없으면 null)"
    )
    content_unchanged: bool = Field(..., description="content_hash == previous_doc_version")
    source_bytes_reused: bool = Field(
        ...,
        description="tenants/{tenant_id}/sources/에 같은 content_hash 원본이 이미 있어 바이트 저장을 생략했는지",
    )


class SourceDocument(ContractModel):
    """
    fetch(+detect) 출력. 원본 바이트의 콘텐츠 주소(ArtifactRef), 문서 버전(doc_version = content_hash, ADR-0005), 포맷 판별 결과(SourceFormat·format_confidence·container_flags), 문서 ACL(acl·acl_hash), 수집 메타데이터(metadata·metadata_hash)를 나르는 수집 측 첫 산출물 계약. 설계 바이블 §5.4 SourceDocument 표를 같은 철자·같은 필수 여부로 옮겼고, 바이블 미등재 필드(detect_report, dedup_report, fetch_report의 확장 키)는 선택으로만 추가했다. 소유 문서: docs/03-contracts/02-source-document.md
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    schema_version: str = Field(
        ...,
        description='계약 버전. 초기 "1.0.0"; MAJOR.MINOR.PATCH 세 정수만(14 불변식 1, S-1). 이 스키마($id major 1)는 1.x만 수용',
        pattern="^1\\.(0|[1-9]\\d*)\\.(0|[1-9]\\d*)$",
    )
    schema_type: Literal["SourceDocument"] = Field(
        ...,
        description="고정값. ArtifactRef.schema_type와 일치해야 로드(00 I-1)",
        pattern="^[A-Z][A-Za-z0-9]*$",
    )
    tenant_id: common_types.Ulid = Field(
        ...,
        description="보안 삼중항 1. artifact.uri의 tenants/{tenant_id}/ 접두와 같다",
    )
    collection_id: common_types.Ulid = Field(..., description="보안 삼중항 2. IngestRequest.collection_id 복사")
    producer: common_types.Producer = Field(
        ...,
        description="fetch 출력은 fetcher.* 플러그인, detect 출력은 parser.*(role format_detector) 플러그인의 지문",
    )
    quality: common_types.Quality = Field(..., description="fetch·detect는 저하를 만들지 않으므로 v1에서는 full")
    warnings: list[common_types.Warning] = Field(..., description="빈 배열 허용(없음). 콘텐츠 미포함")
    created_at: common_types.DateTime = Field(..., description="이 인스턴스 발급 시각(RFC 3339 UTC). fetched_at 이후")
    lineage_refs: LineageRefs = Field(
        ...,
        description="fetch·detect 출력 모두 빈 객체 {}. 원본 바이트는 artifact로 참조하고(00 §3.2 fetch 행), detect는 같은 schema_type을 출력하므로 fetch 출력을 source 키에 넣지 않는다(02 §1.2; fetch→detect 관계는 lineage 원장 행)",
    )
    document_id: common_types.Ulid = Field(
        ...,
        description="(tenant_id, collection_id, external_id or source_uri) 기준 재사용, 아니면 신규. API 접수 시 확정(jobs.document_id)",
    )
    request_id: common_types.Ulid = Field(..., description="IngestRequest.request_id 역참조")
    source_uri: AnyUrl = Field(
        ...,
        description="IngestRequest.source_uri 그대로. 절대 URI, authority에 userinfo(user:pass@) 금지, 공백 금지, ≤ 2,048자 — urn:rag:schema:ingest-request:1 source_uri와 동일 패턴·상한(공용 $defs 승격 전까지 복제, 02 미해결 이슈 8)",
    )
    resolved_uri: AnyUrl = Field(
        ...,
        description="리다이렉트·프리사인 해소 결과. 서명·자격 증명 쿼리 파라미터 제거(§7). source_uri와 같은 패턴·상한(S-10: userinfo·공백 금지, ≤ 2,048자)",
    )
    artifact: common_types.ArtifactRef = Field(
        ...,
        description="원본 바이트(tenants/{tenant_id}/sources/{blake3[:2]}/{blake3}). 계약 산출물이 아니므로 schema_type·schema_version·stage_key 없음; media_type은 원본 MIME(fetch 출력은 잠정값, detect 출력은 §4.2 대응표 값으로 재작성되어 최상위 media_type과 같다, S-8)",
    )
    content_hash: common_types.Hex64 = Field(
        ...,
        description="blake3_hex(원본 바이트) = artifact.blake3(라벨 없음, 바이블 §6.2)",
    )
    doc_version: common_types.Hex64 = Field(
        ...,
        description="= content_hash. 콘텐츠만; ACL·메타데이터 변경은 버전을 바꾸지 않는다(ADR-0005)",
    )
    size_bytes: int = Field(
        ...,
        description="원본 바이트 크기 = artifact.size_bytes. 상한은 프로파일 ingest.fetch.max_bytes(기본 209,715,200)",
        ge=0,
    )
    media_type: common_types.MediaType = Field(
        ...,
        description="시그니처 판정 결과(파라미터 없음). detect 출력은 format 대응표와 일치",
    )
    format: common_types.SourceFormat = Field(
        ...,
        description="파서 라우터 키(parse.router). fetch 출력은 힌트 기반 잠정값 또는 unknown",
    )
    format_confidence: float = Field(
        ...,
        description="판별 신뢰도. fetch 출력은 0.0, detect 출력은 0 초과",
        ge=0.0,
        le=1.0,
    )
    container_flags: ContainerFlags = Field(
        ...,
        description="detect 출력은 판정값. fetch 출력은 미판정 자리표 {encrypted:false, distribution:false, compressed:false}(02 §1.2; producer.plugin_id가 fetcher.*이고 detect_report가 없으면 자리표)",
    )
    http_metadata: HttpMetadata | None = None
    metadata: SourceMetadata = Field(
        ...,
        description="IngestRequest.metadata 복사. 제약은 urn:rag:schema:ingest-request:1#/$defs/IngestMetadata·CustomMetadata와 자구까지 동일(공용 $defs 승격 전까지 복제, 02 미해결 이슈 8)",
    )
    metadata_hash: common_types.Hex64 = Field(
        ...,
        description='H("meta", canonical_json(metadata)). 입력은 02 §3 정규형: 값 없는 선택 필드(생략·null)와 기본값과 같은 선택 필드(language_hint=ko, genre=unknown)를 제거한 직렬화',
    )
    acl: common_types.Acl = Field(
        ...,
        description="문서 단위 ACL 정본(바이블 §10.1). 하류 수집 산출물은 lineage_refs.source로 도달",
    )
    acl_hash: common_types.Hex64 = Field(
        ...,
        description='H("acl", canonical_json(acl)). 입력은 02 §3 정규형: 값 없는 선택 필드(생략·null)와 기본값과 같은 선택 필드(deny_principals=[], classification=internal)를 제거한 직렬화. IndexRecord.acl_hash·aclrev 회수 힌트 대조 키(E9)',
    )
    pii_policy: common_types.PiiPolicy = Field(..., description="확정값(요청 > 컬렉션 > 테넌트)")
    pii_tokenize_mode: common_types.PiiTokenizeMode | None = Field(
        None, description="pii_policy=tokenize일 때 필수, 기본 encrypt"
    )
    external_id: str | None = Field(
        None,
        description="원천 시스템 문서 ID(갱신·삭제 조회 키)",
        max_length=512,
        min_length=1,
    )
    external_version: str | None = Field(None, description="원천 버전 라벨(etag 등)", max_length=256, min_length=1)
    credentials_ref: str | None = Field(
        None,
        description="IngestRequest.credentials_ref 그대로 전파. {provider}:{path} — urn:rag:schema:ingest-request:1#/$defs/CredentialsRef와 동일 패턴·상한(공용 $defs 승격 전까지 복제, 02 미해결 이슈 8). provider 유효성(RAG_SECRETS__PROVIDER env|openbao|aws_kms, 바이블 §6.6)은 KeyProvider 해소 시 워커가 판정. 값(비밀) 미포함",
        max_length=256,
        min_length=1,
        pattern="^[a-z][a-z0-9_]*:[^\\s]{1,240}$",
    )
    fetched_at: common_types.DateTime = Field(..., description="다운로드 완료(또는 304 확인) 시각")
    fetch_report: FetchReport | None = None
    detect_report: DetectReport | None = None
    dedup_report: DedupReport | None = None
