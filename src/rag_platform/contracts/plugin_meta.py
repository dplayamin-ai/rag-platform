"""GENERATED — 수정 금지. 재생성: `uv run python tools/contracts_gen.py`

역할: `schemas/*.schema.json`의 계약 스키마 하나를 그대로 옮긴 Pydantic v2 모델(계층 L0) — 파이프라인 단계 간에 주고받는 데이터의 타입을 정의한다.
설계 근거: 바이블 §5.1(계약이 정본), §6.4(kebab 스키마 이름 ↔ snake_case 모듈명), §12(레이어 지도).
구성: 클래스명은 스키마의 `title`(또는 `$defs`의 각 항목)과 동일하며, 필드는 스키마의 `properties`/`required`를 그대로 반영한다.
불변식: `tools/contracts_gen.py`만 이 파일을 쓴다 — 손으로 고친 내용은 다음 재생성 때 사라진다.
검증 계층: 1층(여기서 검증) — tests/contracts, tools/validate-contracts.mjs.
"""

from __future__ import annotations

from pydantic import ConfigDict, Field, RootModel

from rag_platform.contracts.contract_model import ContractModel

from . import common_types


class SpdxExpression(RootModel[str]):
    root: str = Field(
        ...,
        description="SPDX 라이선스 식별자 또는 단순 표현식(Apache-2.0, LGPL-3.0-only, MIT OR Apache-2.0)",
        max_length=256,
        pattern="^[A-Za-z0-9.+-]+( (AND|OR|WITH) [A-Za-z0-9.+-]+)*$",
    )


class Territory(RootModel[str]):
    root: str = Field(..., description="ISO 3166-1 alpha-2(KR, US)", pattern="^[A-Z]{2}$")


class PluginMeta(ContractModel):
    """
    플러그인 자기 선언 메타데이터(바이블 §5.6). 플러그인 pyproject.toml [tool.rag_platform.plugin] 테이블이 생산하고 레지스트리·라이선스 게이트(ADR-0001)·프로파일 검증기(§7.4 (1)(2))가 소비한다. plugin_id 접두는 extension_point와 같고 entry point 그룹은 rag_platform.{extension_point}(D-10 14종, ADR-0032). 봉투 없음. 공용 타입·열거는 urn:rag:schema:common-types:1 을 참조한다. 소유 문서: docs/03-contracts/15-collection-profile-and-policy-contracts.md
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    plugin_id: common_types.PluginId = Field(
        ...,
        description="{extension_point}.{implementation}(§6.1). Producer.plugin_id와 동일 문자열",
    )
    extension_point: common_types.ExtensionPoint = Field(..., description="D-10 14종. plugin_id의 접두와 일치")
    role: str | None = Field(
        None,
        description="서브 역할(korean_analyzer, sentence_splitter, pii_detector, format_detector, token_counter, renderer 등). 확장 지점 수를 늘리지 않는 축(ADR-0032)",
        max_length=64,
        pattern="^[a-z][a-z0-9_]*$",
    )
    version: common_types.Semver = Field(..., description="패키지 버전 = Producer.plugin_version")
    license: SpdxExpression = Field(..., description="배포 wheel 메타데이터 기준 SPDX 식별자·표현식")
    license_grade: common_types.LicenseGrade = Field(..., description="A/B/C/D/X(D-02, ADR-0001). X는 로딩 불가")
    territory: list[Territory] = Field(
        ...,
        description="사용 허가 지역(ISO 3166-1 alpha-2). 빈 배열 = 제한 없음. license_policy.territory 전부를 포함해야 로딩",
    )
    linkage: common_types.Linkage = Field(
        ...,
        description="플러그인 자기 배포물에 번들된 네이티브 코드 링크 형태. license_grade=B 이고 static_bundled 이면 기본 프로파일 거부(§7.4 (1))",
    )
    isolation_supported: list[common_types.IsolationMode] = Field(
        ...,
        description="= capabilities.isolation_modes(집합 동치). C 등급은 [sidecar]만",
        min_length=1,
    )
    model_ids: list[common_types.ModelId] | None = Field(None, description="{repo}@{revision}. models.lock 행과 대응")
    model_license_ack_required: bool | None = Field(
        None, description="D 등급 모델 포함 시 true(사용자 model_license_ack 필요)"
    )
    sidecar_image: str | None = Field(
        None,
        description="sidecar 격리 시 이미지 참조(태그까지; digest는 런타임 Producer.image_digest)",
        max_length=255,
        pattern="^[a-z0-9][a-z0-9._/-]*(:[A-Za-z0-9._-]+)?$",
    )
    contracts_compat: common_types.ContractsCompat = Field(
        ...,
        description="수용하는 계약 schema_version 범위. = capabilities.contracts_compat",
    )
    capabilities: common_types.Capabilities = Field(
        ...,
        description="capabilities() 정적 사본. index_backend 는 extra = IndexBackendCapabilities",
    )
