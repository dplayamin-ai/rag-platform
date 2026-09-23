"""GENERATED — 수정 금지. 재생성: `uv run python tools/contracts_gen.py`

역할: `schemas/*.schema.json`의 계약 스키마 하나를 그대로 옮긴 Pydantic v2 모델(계층 L0) — 파이프라인 단계 간에 주고받는 데이터의 타입을 정의한다.
설계 근거: 바이블 §5.1(계약이 정본), §6.4(kebab 스키마 이름 ↔ snake_case 모듈명), §12(레이어 지도).
구성: 클래스명은 스키마의 `title`(또는 `$defs`의 각 항목)과 동일하며, 필드는 스키마의 `properties`/`required`를 그대로 반영한다.
불변식: `tools/contracts_gen.py`만 이 파일을 쓴다 — 손으로 고친 내용은 다음 재생성 때 사라진다.
검증 계층: 1층(여기서 검증) — tests/contracts, tools/validate-contracts.mjs.
"""

from __future__ import annotations

from typing import Any

from pydantic import AnyUrl, ConfigDict, Field, RootModel

from rag_platform.contracts.contract_model import ContractModel

from . import common_types


class Input(ContractModel):
    """
    원본(sources/{blake3}) 또는 상류 파생물 참조. uri 스킴은 s3·file(개발)만(E16). media_type 은 원본 MIME
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    uri: AnyUrl = Field(..., description="s3:// 또는 file:// URI(오브젝트 키 규약 §13.3)")
    blake3: common_types.Hex64 = Field(..., description="산출물 바이트의 BLAKE3 콘텐츠 해시")
    media_type: common_types.MediaType = Field(..., description="application/vnd.rag.{kebab-name}+json 또는 원본 MIME")
    schema_type: common_types.SchemaTypeName | None = Field(
        None,
        description="계약 산출물이면 PascalCase 타입명. 봉투 schema_type과 일치해야 로드",
    )
    schema_version: common_types.Semver | None = Field(None, description="계약 산출물이면 계약 버전")
    size_bytes: int = Field(..., description="바이트 크기(인라인 금지 검증·계량)", ge=0)
    stage_key: common_types.Hex64 | None = Field(None, description="생산 스테이지 멱등성 키(계보 자기 서술)")


class CredentialsRef(RootModel[str]):
    root: str = Field(
        ...,
        description="선택(N, null 허용). {provider}:{path} 간접 참조(IngestRequest.credentials_ref 그대로 전파, 바이블 §6.6). 비밀 값 자체를 넣으면 400 contract.violation",
        max_length=512,
        pattern="^[a-z][a-z0-9_]*:[^\\s]{1,480}$",
    )


class ConvertRequest(ContractModel):
    """
    워커 → 변환 사이드카 POST /v1/convert 요청(바이블 §5.6·§14, ADR-0033). 본문은 ArtifactRef 참조만(원본 바이트·base64 인라인 금지), 비밀은 credentials_ref 간접 참조만. 사이드카(parser-workers·lo-sidecar·ocr-gpu)는 input.uri 를 자기 스토리지 자격 증명으로 직접 읽고 파생물을 tenants/{tenant_id}/derived/ 아래에 콘텐츠 주소화 저장한다. 공용 타입은 urn:rag:schema:common-types:1 을 참조한다. 소유 문서: docs/03-contracts/16-eval-feedback-and-sidecar-contracts.md
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    schema_version: common_types.Semver | None = Field(
        None,
        description='선택(N). 계약 버전 "1.0.0". 사이드카는 contracts_compat 범위 밖이면 400 contract.violation. 바이블 §5.6 미등재(미해결 이슈 1)',
    )
    input: Input = Field(
        ...,
        description="원본(sources/{blake3}) 또는 상류 파생물 참조. uri 스킴은 s3·file(개발)만(E16). media_type 은 원본 MIME",
    )
    options: dict[str, Any] | None = Field(
        None,
        description='선택(N). 사이드카별 옵션(예 {"target": "hwpx"}, OCR 언어·페이지 범위). 스키마는 각 사이드카가 게시. URL·비밀·본문 텍스트 금지(불변식 EF-25). 열린 객체(14 §2.3)',
        max_length=32,
    )
    tenant_id: common_types.Ulid = Field(
        ...,
        description='파생물 키 접두 tenants/{tenant_id}/derived/ 와 감사용(보안 삼중항 1). derived 캐시 키 H("derived", content_hash, image_digest) 에는 들어가지 않는다',
    )
    document_id: common_types.Ulid = Field(..., description="감사·트레이스 상관용. 캐시 키에 들어가지 않는다")
    deadline_ms: int = Field(
        ...,
        description="요청 시점 기준 잔여 예산(ms). 워커가 StagePolicy.start_to_close 잔여에서 파생(parse 15m, OCR 60m 상한). 사이드카는 초과 전에 output=null + error 로 반환한다",
        ge=1,
        le=3600000,
    )
    trace_id: str = Field(
        ...,
        description="W3C Trace Context trace-id(소문자 hex 32). 사이드카 스팬은 rag.ingest.parse 의 자식(바이블 §6.5)",
        pattern="^[0-9a-f]{32}$",
    )
    credentials_ref: CredentialsRef | None = Field(
        None,
        description="선택(N, null 허용). {provider}:{path} 간접 참조(IngestRequest.credentials_ref 그대로 전파, 바이블 §6.6). 비밀 값 자체를 넣으면 400 contract.violation",
    )
