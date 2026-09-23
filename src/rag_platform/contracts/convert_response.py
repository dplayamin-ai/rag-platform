"""GENERATED — do not edit; run `uv run python tools/contracts_gen.py` to regenerate.

Source of truth: schemas/*.schema.json (bible §5.1, §6.4, §12)."""

from __future__ import annotations

from pydantic import AnyUrl, BaseModel, ConfigDict, Field

from . import common_types


class Output(BaseModel):
    """
    오브젝트 스토리지 산출물 참조. 오케스트레이터 경계를 넘는 유일한 페이로드(바이블 §4.1, §5.3).
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


class DerivedItem(BaseModel):
    """
    오브젝트 스토리지 산출물 참조. 오케스트레이터 경계를 넘는 유일한 페이로드(바이블 §4.1, §5.3).
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


class Producer(BaseModel):
    """
    plugin_id=사이드카 어댑터({extension_point}.{implementation}), plugin_version, config_hash, image_digest(sha256 digest, 비-null), model_ids(OCR 모델 등)
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    plugin_id: common_types.PluginId
    plugin_version: common_types.Semver = Field(..., description="패키지 버전")
    config_hash: common_types.Hex64 = Field(..., description='H("config", canonical_json(config))')
    image_digest: common_types.ImageDigest | None = Field(
        ..., description="사이드카·서빙 이미지 digest. 인프로세스는 null"
    )
    model_ids: list[common_types.ModelId] | None = Field(None, description="{model_id}@{revision} 목록")


class ConvertResponse(BaseModel):
    """
    변환 사이드카 → 워커 POST /v1/convert 200 응답(바이블 §5.6·§14, ADR-0033). 변환 실패는 200 + output=null + error(StageError, stage=parse); ProblemDetails 는 전송·검증 오류(400 contract.violation, 503 parse.sidecar_unavailable)에만 쓴다(13-error-model §6.4). output·derived[] 는 tenants/{tenant_id}/derived/{kind}/ 아래 콘텐츠 주소화 산출물이고 producer.image_digest 는 사이드카 자기 보고(비-null)다. 공용 타입은 urn:rag:schema:common-types:1 을 참조한다. 소유 문서: docs/03-contracts/16-eval-feedback-and-sidecar-contracts.md
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    schema_version: common_types.Semver | None = Field(
        None,
        description='선택(N). 계약 버전 "1.0.0". 바이블 §5.6 미등재(미해결 이슈 1)',
    )
    output: Output | None = Field(
        ...,
        description="Y(nullable). 요청된 주 산출물 1개(HWPX 변환본·DOCX 변환본·OCR 결과). null 이면 error 필수(allOf)",
    )
    derived: list[DerivedItem] = Field(
        ...,
        description="부속 파생물(페이지 이미지 매니페스트·변환 보고서·표 HTML). 빈 배열 허용. ParsedDocument.artifacts[] 로 전파. 페이지 단위 산출물은 매니페스트 1개로 묶는다(미해결 이슈 9)",
        max_length=64,
    )
    warnings: list[common_types.Warning] = Field(
        ...,
        description="stage.reason 경고 코드(§5.7 카탈로그). 콘텐츠 미포함",
        max_length=64,
    )
    error: common_types.StageError | None = Field(
        None,
        description="선택(N, null 허용). output=null 이면 필수: stage=parse, plugin_id=사이드카 어댑터, code 는 parse.* 카탈로그 코드(parse.sidecar_unavailable 제외 — 그것은 503 전송 계층). retryable 은 카탈로그 값",
    )
    took_ms: int = Field(
        ...,
        description="사이드카 처리 시간(ms). deadline_ms 초과면 output=null(불변식 EF-26)",
        ge=0,
    )
    producer: Producer = Field(
        ...,
        description="plugin_id=사이드카 어댑터({extension_point}.{implementation}), plugin_version, config_hash, image_digest(sha256 digest, 비-null), model_ids(OCR 모델 등)",
    )
