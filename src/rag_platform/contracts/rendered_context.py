"""GENERATED — 수정 금지. 재생성: `uv run python tools/contracts_gen.py`

역할: `schemas/*.schema.json`의 계약 스키마 하나를 그대로 옮긴 Pydantic v2 모델(계층 L0) — 파이프라인 단계 간에 주고받는 데이터의 타입을 정의한다.
설계 근거: 바이블 §5.1(계약이 정본), §6.4(kebab 스키마 이름 ↔ snake_case 모듈명), §12(레이어 지도).
구성: 클래스명은 스키마의 `title`(또는 `$defs`의 각 항목)과 동일하며, 필드는 스키마의 `properties`/`required`를 그대로 반영한다.
불변식: `tools/contracts_gen.py`만 이 파일을 쓴다 — 손으로 고친 내용은 다음 재생성 때 사라진다.
검증 계층: 1층(여기서 검증) — tests/contracts, tools/validate-contracts.mjs.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, RootModel, conint, constr
from typing_extensions import TypeAliasType

from . import common_types

ProviderPayloadString = TypeAliasType("ProviderPayloadString", Annotated[str, Field(min_length=1)])


VolatileSuffixString = TypeAliasType("VolatileSuffixString", Annotated[str, Field(min_length=1)])


class SegmentRangeItem(RootModel[int]):
    root: int = Field(..., ge=0)


class CharRangeItem(RootModel[int]):
    root: int = Field(..., ge=0)


class CitationMapEntry(BaseModel):
    """
    공급자 인용 위치 → cite_id → chunk provenance 역매핑 한 행(바이블 §5.5 citation_map)
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    provider_key: conint(ge=0) | constr(min_length=1) = Field(
        ...,
        description="공급자 인용 키. anthropic_search_result(native): search_result_index(정수, 요청 내 등장 순서 = position); anthropic_document(native): document_index; 마커 계열(bracket_id: xml_documents·openai_messages·gemini_messages·markdown·mcp_tool_result, anthropic_* + bracket_id): cite_id 문자열",
    )
    cite_id: common_types.CiteId
    chunk_id: common_types.Hex64
    collection_id: common_types.Ulid
    document_id: common_types.Ulid
    segment_range: tuple[SegmentRangeItem, SegmentRangeItem] = Field(
        ...,
        description="[start_index, end_index) — 이 항목의 segments[] 인덱스 범위(끝 미포함). 공급자 블록 인덱스 b는 segments[start_index + b − block_offset]. segments가 빈 항목(level 2 파생)은 [0, 0] = 항목 전체",
    )
    block_offset: int | None = Field(
        None,
        description="선택(기본 0). 공급자 content[] 앞에 놓인 비세그먼트 블록 수(팩 수준 안내 문구가 첫 항목 content[0]에 실린 경우 1)",
        ge=0,
    )
    char_range: tuple[CharRangeItem, CharRangeItem] | None = Field(
        None,
        description="선택. 문자열 렌더러(xml_documents·markdown·openai_messages·gemini_messages)에서 항목 본문(text)이 차지하는 렌더 문자열 내 코드포인트 범위(끝 미포함). 공급자 문자 오프셋 → 세그먼트 역매핑용",
    )


class RenderedContext(BaseModel):
    """
    render 서브스테이지 출력(바이블 §5.5 RenderedContext, §9.3 렌더러 규칙, §9.4 프롬프트 캐싱). ContextPack의 뷰(D-05)이며 경계 타입을 추가하지 않는다. provider_payload는 공급자 네이티브 블록/메시지/XML 문자열, stable_prefix/volatile_suffix는 프롬프트 캐시 브레이크포인트 기준으로 나눈 같은 내용, citation_map은 공급자 인용 위치 → cite_id·chunk_id·segment_range 역매핑이다. 공급자 페이로드에는 tenant_id·주체·acl_*·record_id를 넣지 않는다(바이블 §9.3 공통 규칙 1). 공용 타입·열거는 urn:rag:schema:common-types:1 을 참조한다. 소유 문서: docs/03-contracts/11-context-pack.md
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    schema_version: common_types.Semver = Field(..., description='계약 버전. 초기 "1.0.0"')
    schema_type: Literal["RenderedContext"] | None = Field(
        None, description="선택. PascalCase 타입명(바이블 §5.5 미등재, 11 미해결 이슈)"
    )
    pack_id: common_types.Ulid = Field(..., description="원 ContextPack.pack_id")
    renderer: common_types.Renderer
    tenant_id: common_types.Ulid = Field(..., description="내부 계약에만 존재. provider_payload에 넣지 않는다")
    collection_ids: list[common_types.Ulid] = Field(..., max_length=20, min_length=1)
    provider_payload: dict[str, Any] | ProviderPayloadString = Field(
        ...,
        description='공급자 네이티브 페이로드 = stable_prefix와 volatile_suffix의 조립(객체: {**stable_prefix, **volatile_suffix}, 최상위 키 서로소; 문자열: stable_prefix + "\\n\\n" + volatile_suffix; stable_prefix가 null이면 volatile_suffix와 동일). anthropic_*: {system?, messages} 또는 {type: tool_result, tool_use_id, content}; openai_messages: {instructions?, input, text?}; gemini_messages: {system_instruction?, contents}; xml_documents·markdown: 문자열; mcp_tool_result: {content, structuredContent}; plain_records·dify_external_knowledge: {records}',
    )
    stable_prefix: dict[str, Any] | str | None = Field(
        ...,
        description="Y(nullable). 지시문 템플릿 본문·도구 정의·컬렉션 고정 문맥(캐시 브레이크포인트 앞). 렌더러가 접두어를 만들지 않으면 null. 메타(instructions_template_id 등)는 넣지 않는다",
    )
    volatile_suffix: dict[str, Any] | VolatileSuffixString = Field(
        ..., description="이번 팩 항목 + 질의(캐시 브레이크포인트 뒤)"
    )
    citation_map: list[CitationMapEntry] = Field(
        ...,
        description="공급자 인용 위치 → 세그먼트 역매핑. 항목 K개와 1:1(cite_id 집합 = d1..dK). source URI에 의존하지 않는다",
    )
    token_count_rendered: int = Field(
        ...,
        description="렌더 후 재카운트(대상 LLM 토크나이저). ContextPack.budget.used_tokens 갱신 원천",
        ge=0,
    )
    count_method: common_types.CountMethod
    warnings: list[common_types.Warning]
    created_at: common_types.DateTime | None = Field(None, description="선택. 렌더 시각(render_key 계산에서 제외)")
    pack_content_hash: common_types.Hex64 | None = Field(None, description="선택. 원 ContextPack.content_hash")
    options_hash: common_types.Hex64 | None = Field(
        None, description='선택. H("config", canonical_json(render options))'
    )
    render_key: common_types.Hex64 | None = Field(
        None,
        description='선택. H("render", content_hash, renderer, options_hash)(바이블 §4.3 render 캐시 키)',
    )
