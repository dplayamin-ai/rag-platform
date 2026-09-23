"""GENERATED — 수정 금지. 재생성: `uv run python tools/contracts_gen.py`

역할: `schemas/*.schema.json`의 계약 스키마 하나를 그대로 옮긴 Pydantic v2 모델(계층 L0) — 파이프라인 단계 간에 주고받는 데이터의 타입을 정의한다.
설계 근거: 바이블 §5.1(계약이 정본), §6.4(kebab 스키마 이름 ↔ snake_case 모듈명), §12(레이어 지도).
구성: 클래스명은 스키마의 `title`(또는 `$defs`의 각 항목)과 동일하며, 필드는 스키마의 `properties`/`required`를 그대로 반영한다.
불변식: `tools/contracts_gen.py`만 이 파일을 쓴다 — 손으로 고친 내용은 다음 재생성 때 사라진다.
검증 계층: 1층(여기서 검증) — tests/contracts, tools/validate-contracts.mjs.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .. import common_types
from ..common_types.Block import figure as figure_1, footnote as footnote_1
from .ParsedDocument import annotations as annotations_1, artifacts as artifacts_1


class LineageRefs(BaseModel):
    """
    parse 출력은 정확히 {source}(SourceDocument 계약 산출물 참조)
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    source: common_types.ArtifactRef
    parsed: common_types.ArtifactRef | None = None
    normalized: common_types.ArtifactRef | None = None
    chunk_set: common_types.ArtifactRef | None = None
    enriched: common_types.ArtifactRef | None = None
    embedded: common_types.ArtifactRef | None = None


class Figure(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    artifact: common_types.ArtifactRef
    kind: figure_1.Kind
    alt_text: str | None = None
    caption_generated: bool | None = None
    caption_model: str | None = None


class Formula(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    script: str = Field(..., description="한컴 수식 script 원문(필수)")
    latex: str | None = None


class Footnote(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    kind: footnote_1.Kind
    anchor_block_id: str | None = None
    anchor_char_offset: int | None = Field(None, ge=0)
    marker: str | None = None


class Code(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    language: str | None = None


class PageBreak(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    page_no: int | None = Field(None, ge=1)
    section_index: int | None = Field(None, ge=0)


class Block(BaseModel):
    """
    ParsedDocument.blocks[] 요소. 문서 순서 평탄 리스트, 계층은 parent_block_id.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    block_id: common_types.Hex32 = Field(..., description='H("block", doc_version, element_path)[:32]')
    type: common_types.BlockType
    parent_block_id: common_types.Hex32 | None
    ordinal: int = Field(..., ge=0)
    text: str = Field(..., description='원문(NFC 미적용; 표·그림은 "" 가능)', max_length=1048576)
    level: int | None = Field(None, description="heading 0..6(0 = 문서 제목), list_item 깊이", ge=0)
    numbering_label: str | None = None
    heading_inferred: bool | None = None
    ordered: bool | None = None
    furniture: bool = Field(..., description="머리말·꼬리말·nav 등 본문 아님(기본 청킹 제외)")
    container: common_types.BlockContainer
    lang: common_types.Bcp47 | None = None
    source: common_types.BlockSource
    confidence: float | None = Field(None, ge=0.0, le=1.0)
    provenance: common_types.Provenance
    caption_of: str | None = None
    caption_block_ids: list[common_types.Hex32] | None = None
    table: common_types.TableData | None = None
    figure: Figure | None = None
    formula: Formula | None = None
    footnote: Footnote | None = None
    code: Code | None = None
    page_break: PageBreak | None = None


class ParserFingerprint(BaseModel):
    """
    파서 지문. parser_fingerprint_hash = H("parser", parser_id, parser_version, ",".join(model_ids), sidecar_image_digest or "", profile_option)(바이블 §6.2)
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    parser_id: common_types.PluginId = Field(
        ...,
        description="예 parser.hwpx_python_hwpx, parser.pdf_docling_standard, parser.pdf_fast_pdftext",
    )
    parser_version: str = Field(
        ...,
        description="래핑 라이브러리 고정 버전 표기 {package}=={version}(예 python-hwpx==6.4.0)",
        min_length=1,
    )
    model_ids: list[common_types.ModelId] | None = Field(None, description="레이아웃·표·OCR 모델 {model_id}@{revision}")
    sidecar_image_digest: common_types.ImageDigest | None = Field(None, description="사이드카 경로일 때만 non-null")
    profile_option: str = Field(
        ...,
        description="예 hwpx_standard, pdf_standard, pdf_fast_cpu, pdf_scanned_gpu",
        pattern="^[a-z][a-z0-9_]*$",
    )


class PageStatusEntry(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    page: int = Field(..., description="1-based", ge=1)
    status: common_types.PageStatus
    ocr_confidence: float | None = Field(
        None,
        description="페이지 OCR 평균 신뢰도. OCR 미수행·실패는 null",
        ge=0.0,
        le=1.0,
    )


class WebMetadata(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    canonical_url: common_types.Uri | None = None
    site_name: str | None = None
    published_at: common_types.DateTime | None = None
    author: str | None = None


class DerivedArtifact(BaseModel):
    """
    derived/ 산출물 참조(봉투 없음, 테넌트 내 공유; 바이블 §13.3)
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    kind: artifacts_1.Kind
    ref: common_types.ArtifactRef
    page: int | None = Field(None, description="page_image의 대상 페이지", ge=1)
    block_id: common_types.Hex32 | None = Field(None, description="figure_crop·table_html의 대상 블록")


class Annotation(BaseModel):
    """
    본문 외 어노테이션. char_*는 대상 Block.text 기준 코드포인트, 끝 미포함
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    kind: annotations_1.Kind
    block_id: common_types.Hex32
    char_start: int = Field(..., ge=0)
    char_end: int = Field(..., ge=0)
    text: str


class FormFieldEntry(BaseModel):
    """
    HWPX 필드(hp:fieldBegin) 메타. 값 텍스트는 본문 블록에도 포함된다
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    name: str
    type: str = Field(..., description="필드 타입 원문(CLICK_HERE, DATE, HYPERLINK 등)")
    value: str
    block_id: common_types.Hex32


class Link(BaseModel):
    """
    하이퍼링크. char_*는 대상 Block.text 기준 코드포인트, 끝 미포함
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    block_id: common_types.Hex32
    char_start: int = Field(..., ge=0)
    char_end: int = Field(..., ge=0)
    href: str = Field(..., min_length=1)


class DocumentMetadata(BaseModel):
    """
    파서가 원본에서 읽은 문서 메타. 모든 필드 선택
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    title: str | None = Field(
        None,
        description="IngestRequest.metadata.title 부재 시 IndexRecord.title 대체 원천 1순위",
    )
    authors: list[str] | None = None
    created_at: common_types.DateTime | None = None
    modified_at: common_types.DateTime | None = None
    page_header_text: list[str] | None = Field(None, description="머리말 원문(보일러플레이트 제거 근거)")
    page_footer_text: list[str] | None = None
    has_tracked_changes: bool | None = Field(None, description="변경 추적 존재. 기본 정책 accept_all")
    navigation_text: list[str] | None = Field(None, description="HTML nav/aside 텍스트")
    web: WebMetadata | None = None
    genre: common_types.Genre | None = Field(None, description="요청 힌트 또는 파서 추론")


class ParsedDocument(BaseModel):
    """
    포맷 독립 표준 문서 모델(바이블 §5.4, D-04, ADR-0002). parse 스테이지가 생산하고 normalize·get_document가 소비한다. 블록은 문서 순서 평탄 리스트이며 계층은 parent_block_id·ordinal로 복원한다. 공용 타입·열거는 urn:rag:schema:common-types:1을 참조한다.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    schema_version: str = Field(
        ...,
        description="계약 버전. 초판 1.0.0; MAJOR.MINOR.PATCH 세 정수만(14 불변식 1, P-1). 이 스키마($id major 1)는 1.x만 수용",
        pattern="^1\\.(0|[1-9]\\d*)\\.(0|[1-9]\\d*)$",
    )
    schema_type: Literal["ParsedDocument"]
    tenant_id: common_types.Ulid = Field(..., description="보안 삼중항 1")
    collection_id: common_types.Ulid = Field(..., description="보안 삼중항 2(수집 측 단수)")
    producer: common_types.Producer = Field(
        ...,
        description="실제 산출 파서 플러그인의 재현성 지문. plugin_id = parser_fingerprint.parser_id",
    )
    quality: common_types.Quality = Field(..., description="손실이 하나라도 있으면 degraded")
    warnings: list[common_types.Warning] = Field(..., description="품질 삼중항 2. 빈 배열 허용, 콘텐츠 미포함")
    created_at: common_types.DateTime
    lineage_refs: LineageRefs = Field(..., description="parse 출력은 정확히 {source}(SourceDocument 계약 산출물 참조)")
    document_id: common_types.Ulid
    doc_version: common_types.Hex64 = Field(
        ..., description="= SourceDocument.content_hash = source_ref.blake3(ADR-0005)"
    )
    source_ref: common_types.ArtifactRef = Field(
        ...,
        description="입력 원본 바이트(sources/). blake3 = doc_version, media_type = 원본 MIME",
    )
    parser_fingerprint: ParserFingerprint
    parser_chain: list[common_types.PluginId] = Field(
        ...,
        description="실제 시도 순서. 마지막 원소가 산출 파서(= parser_fingerprint.parser_id)",
        min_length=1,
    )
    source_kind: common_types.SourceKind = Field(..., description="flow = HWP/HWPX/DOCX/HTML/MD/TXT(페이지·bbox 없음)")
    page_count: int | None = Field(..., description="Y(nullable). 흐름 포맷은 null", ge=1)
    page_status: list[PageStatusEntry] | None = Field(
        None,
        description="페이지 단위 처리 결과. 페이지 포맷만, 페이지당 최대 1항목. ok 외 상태가 있으면 quality=degraded",
    )
    language: common_types.Bcp47 = Field(..., description="문서 주 언어")
    metadata: DocumentMetadata | None = None
    blocks: list[Block] = Field(
        ...,
        description="문서 순서(읽기 순서) 평탄 리스트. 계층은 parent_block_id, 형제 순서는 ordinal. 블록 텍스트 한계 1MB(UTF-8 바이트; maxLength는 코드포인트 근사)",
        max_length=200000,
    )
    artifacts: list[DerivedArtifact] | None = Field(
        None,
        description="파생 산출물(페이지 이미지·그림 크롭·표 HTML·벤더 JSON·변환 원본) 참조",
    )
    annotations: list[Annotation] | None = Field(None, description="메모·변경 추적·주석. 인덱싱 제외 기본")
    fields: list[FormFieldEntry] | None = Field(None, description="HWPX 필드(누름틀 등) 메타")
    links: list[Link] | None = Field(None, description="하이퍼링크 어노테이션")
    text_length: int = Field(..., description="Σ len(blocks[].text) (유니코드 코드포인트)", ge=0)
    block_count: int = Field(..., description="= len(blocks)", ge=0, le=200000)
    source_encoding: str | None = Field(None, description="TXT/HTML 원 인코딩(예 cp949, utf-8)", min_length=1)
