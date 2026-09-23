"""GENERATED — 수정 금지. 재생성: `uv run python tools/contracts_gen.py`

역할: `schemas/*.schema.json`의 계약 스키마 하나를 그대로 옮긴 Pydantic v2 모델(계층 L0) — 파이프라인 단계 간에 주고받는 데이터의 타입을 정의한다.
설계 근거: 바이블 §5.1(계약이 정본), §6.4(kebab 스키마 이름 ↔ snake_case 모듈명), §12(레이어 지도).
구성: 클래스명은 스키마의 `title`(또는 `$defs`의 각 항목)과 동일하며, 필드는 스키마의 `properties`/`required`를 그대로 반영한다.
불변식: `tools/contracts_gen.py`만 이 파일을 쓴다 — 손으로 고친 내용은 다음 재생성 때 사라진다.
검증 계층: 1층(여기서 검증) — tests/contracts, tools/validate-contracts.mjs.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import ConfigDict, Field

from rag_platform.contracts.contract_model import ContractModel

from . import common_types


class CompatLevel(StrEnum):
    patch = "patch"
    minor = "minor"
    major = "major"


class SchemaChangeKind(StrEnum):
    annotation_changed = "annotation_changed"
    property_added_optional = "property_added_optional"
    property_added_required = "property_added_required"
    property_removed = "property_removed"
    property_required_added = "property_required_added"
    property_required_removed = "property_required_removed"
    type_changed = "type_changed"
    nullable_added = "nullable_added"
    nullable_removed = "nullable_removed"
    enum_value_added = "enum_value_added"
    enum_value_removed = "enum_value_removed"
    const_changed = "const_changed"
    constraint_relaxed = "constraint_relaxed"
    constraint_tightened = "constraint_tightened"
    additional_properties_opened = "additional_properties_opened"
    additional_properties_closed = "additional_properties_closed"
    ref_target_changed = "ref_target_changed"
    deprecated_added = "deprecated_added"
    default_changed = "default_changed"
    defs_renamed = "defs_renamed"
    id_changed = "id_changed"


class SchemaChange(ContractModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    kind: SchemaChangeKind
    level: CompatLevel
    path: str = Field(
        ...,
        description="head 스키마 내 위치(JSON Pointer, RFC 6901); 제거는 base 기준 경로",
        pattern="^(/[^/]*)*$",
    )
    detail: str | None = Field(None, description="사람이 읽는 설명(콘텐츠 미포함)")
    before: Any | None = Field(None, description="base 값(선택; 임의 JSON)")
    after: Any | None = Field(None, description="head 값(선택; 임의 JSON)")


class GoldenExampleResult(ContractModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    checked: int = Field(..., ge=0)
    passed: int = Field(..., ge=0)
    failed: list[str] = Field(
        ...,
        description="새 스키마에 유효하지 않은 이전 minor(또는 업캐스팅된 이전 major) 골든 예시 경로",
    )


class EnumMismatch(ContractModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    type_name: common_types.SchemaTypeName = Field(..., description="열거 타입명(바이블 §5.7 첫 열)")
    missing_in_schema: list[str]
    missing_in_bible: list[str]


class EnumCheckResult(ContractModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    passed: bool
    mismatches: list[EnumMismatch]


class SchemaDiffReport(ContractModel):
    """
    두 버전의 계약 JSON Schema를 비교해 변경을 분류하고 선언된 버전 증분(declared_level)이 계산된 등급(computed_level) 이상인지, 이전 minor 골든 예시가 새 스키마에 유효한지, 열거가 바이블 §5.7과 일치하는지를 기록하는 CI 도구 산출물. schemas/ 인벤토리에 속하지 않는다.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    schema_version: common_types.Semver = Field(
        ...,
        description="이 리포트 형식의 버전. 1.0.0. 사전 릴리스·빌드 메타데이터 없음(§1.2, 불변식 1)",
    )
    schema_type: Literal["SchemaDiffReport"]
    contract: common_types.KebabName = Field(..., description="비교 대상 스키마 파일 이름(kebab-name)")
    schema_id: common_types.SchemaId = Field(..., description="head 스키마의 $id")
    base_version: common_types.Semver = Field(..., description="비교 기준(배포된 최신) 계약 버전")
    head_version: common_types.Semver = Field(..., description="제안 계약 버전")
    declared_level: CompatLevel = Field(..., description="base→head 버전 증분에서 계산한 선언 등급")
    computed_level: CompatLevel = Field(..., description="changes[].level의 최댓값")
    passed: bool = Field(
        ...,
        description="declared_level ≥ computed_level AND golden_examples.failed = [] AND enum_check.passed",
    )
    changes: list[SchemaChange] = Field(..., max_length=500)
    golden_examples: GoldenExampleResult
    enum_check: EnumCheckResult
    generated_at: common_types.DateTime
    tool_version: common_types.Semver = Field(..., description="rag schema diff 도구 버전(사전 릴리스 허용)")
