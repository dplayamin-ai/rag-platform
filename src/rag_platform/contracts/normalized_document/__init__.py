"""GENERATED — do not edit; run `uv run python tools/contracts_gen.py` to regenerate.

Source of truth: schemas/*.schema.json (bible §5.1, §6.4, §12)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, RootModel, constr

from .. import common_types
from . import NormalizedDocument as NormalizedDocument_1
from .NormalizedDocument.annotations import pii_spans as pii_spans_1
from .NormalizedDocument.derived_meta import (
    entities_normalized as entities_normalized_1,
)


class LineageRefs(BaseModel):
    """
    봉투. 정확히 {source, parsed}. parsed는 parsed_ref와 같은 참조. 자기 자신(normalized)과 하류 키(chunk_set, enriched, embedded) 미포함(I-3, 00 I-7)
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    source: common_types.ArtifactRef
    parsed: common_types.ArtifactRef
    normalized: common_types.ArtifactRef | None = None
    chunk_set: common_types.ArtifactRef | None = None
    enriched: common_types.ArtifactRef | None = None
    embedded: common_types.ArtifactRef | None = None


class ParsedRef(BaseModel):
    """
    원 ParsedDocument 산출물. 구조 계층의 정본
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    uri: common_types.Uri = Field(..., description="s3:// 또는 file:// URI(오브젝트 키 규약 §13.3)")
    blake3: common_types.Hex64 = Field(..., description="산출물 바이트의 BLAKE3 콘텐츠 해시")
    media_type: common_types.MediaType = Field(..., description="application/vnd.rag.{kebab-name}+json 또는 원본 MIME")
    schema_type: Literal["ParsedDocument"] = Field(
        ...,
        description="계약 산출물이면 PascalCase 타입명. 봉투 schema_type과 일치해야 로드",
        pattern="^[A-Z][A-Za-z0-9]*$",
    )
    schema_version: common_types.Semver = Field(..., description="계약 산출물이면 계약 버전")
    size_bytes: int = Field(..., description="바이트 크기(인라인 금지 검증·계량)", ge=0)
    stage_key: common_types.Hex64 | None = Field(None, description="생산 스테이지 멱등성 키(계보 자기 서술)")


class HeadingNode(BaseModel):
    """
    heading_tree[] 원소. path는 조상 heading의 display_text(루트→현재), 마지막 원소 = 이 블록의 display_text.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    block_id: common_types.Hex32
    level: int = Field(..., description="Block.level 복사(0 = 문서 제목)", ge=0, le=6)
    path: list[str] = Field(..., max_length=7, min_length=1)


class LawRef(RootModel[str]):
    root: str = Field(..., pattern="^[^/\\s][^/]*(/제[0-9]+조(의[0-9]+)?)?(/제[0-9]+항)?$")


class EntityNormalized(BaseModel):
    """
    display_text 기준 코드포인트 구간과 정규화 값.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    block_id: common_types.Hex32
    kind: entities_normalized_1.Kind
    char_start: int = Field(..., ge=0)
    char_end: int = Field(..., ge=0)
    value: str = Field(
        ...,
        description="date: YYYY-MM-DD, law_article: {법령명}/제n조[/제m항], unit: SI 정규화 값, org: 정규 기관명",
        min_length=1,
    )


class PiiSpan(BaseModel):
    """
    display_text 기준 구간(row·col이 있으면 table_cell_views 셀 뷰의 display_text 기준). exclude는 start == end(빈 구간, 원문 범위는 offset_map 경계 마커로 복원). 바이블 §5.4 필드 + 선택 row/col(N, 둘 다 있거나 둘 다 없음).
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    block_id: common_types.Hex32
    row: int | None = Field(None, description="N. 셀 뷰 좌표(TableCell.row). col과 함께만", ge=0)
    col: int | None = Field(None, description="N. 셀 뷰 좌표(TableCell.col). row와 함께만", ge=0)
    entity_type: str = Field(
        ...,
        description="탐지기 엔티티 타입(KR_RRN, KR_PHONE, EMAIL_ADDRESS 등)",
        max_length=64,
        pattern="^[A-Z][A-Z0-9_]*$",
    )
    start: int = Field(..., ge=0)
    end: int = Field(..., ge=0)
    score: float = Field(..., ge=0.0, le=1.0)
    operator: pii_spans_1.Operator = Field(..., description="v1에서는 pii_report.policy_applied와 같다")


class ContentRisk(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    block_id: common_types.Hex32
    kind: str = Field(
        ...,
        description="예 injection_pattern, hidden_text, encoded_payload",
        max_length=64,
        pattern="^[a-z][a-z0-9_]*$",
    )
    score: float = Field(..., ge=0.0, le=1.0)


class EntityCounts(RootModel[int]):
    root: int = Field(..., ge=0)


class PiiReport(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    policy_applied: common_types.PiiPolicy = Field(
        ...,
        description="실제 적용 정책(= SourceDocument.pii_policy). ChunkSet·IndexRecord.pii_policy_applied로 전파",
    )
    entity_counts: dict[constr(pattern=r"^[A-Z][A-Z0-9_]*$"), EntityCounts] = Field(
        ..., description="엔티티 타입별 구간 수(= pii_spans 집계)"
    )
    detector_version: str = Field(
        ...,
        description="탐지기 플러그인·모델 버전 문자열(normalizer_fingerprint 입력)",
        max_length=256,
        min_length=1,
    )
    tokenize_mode_applied: common_types.PiiTokenizeMode | None = Field(
        None,
        description="N. policy_applied=tokenize일 때 적용된 모드(= SourceDocument.pii_tokenize_mode)",
    )


class BoilerplateRemovedItem(RootModel[str]):
    root: str = Field(..., max_length=512)


class NormalizationReport(BaseModel):
    """
    감사·재현성용 집계. 콘텐츠는 boilerplate_removed(정규화된 furniture 문자열)만.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    removed_control_chars: int = Field(..., description="제거된 제어·PUA·zero-width·BOM 코드포인트 수(문서 합)", ge=0)
    nfd_composed: int = Field(..., description="NFC 합성으로 줄어든 코드포인트 수(문서 합)", ge=0)
    hanja_replaced: int = Field(..., description="lexical_text에서 독음으로 치환된 한자 코드포인트 수", ge=0)
    spacing_corrected: bool = Field(..., description="띄어쓰기 교정(opt-in, lexical_text만) 적용 여부")
    boilerplate_removed: list[BoilerplateRemovedItem] = Field(
        ...,
        description='boilerplate=true 블록의 display_text(중복 제거·코드포인트 순 정렬). 512 코드포인트 초과 display_text는 "h:" + blake3_hex(utf8(display_text))로 대체 기록; 서로 다른 항목이 1,000개를 넘으면 문서 순 앞 1,000개만(I-12)',
        max_length=1000,
    )


class NormalizationStats(BaseModel):
    """
    N. 통계(계량·크기 검증). analyzer_token_count는 형태소 분석기 토큰 수이며 임베딩 토크나이저 토큰 수는 Chunk.token_counts(TokenCounts)가 정본.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    block_count: int = Field(..., ge=0)
    body_block_count: int = Field(..., description="boilerplate=false 블록 수", ge=0)
    furniture_block_count: int = Field(..., description="boilerplate=true 블록 수", ge=0)
    display_chars: int = Field(..., description="display_text 코드포인트 합", ge=0)
    lexical_chars: int = Field(..., description="lexical_text 코드포인트 합", ge=0)
    sentence_count: int = Field(..., ge=0)
    pii_span_count: int = Field(..., ge=0)
    analyzer_token_count: int | None = Field(
        None,
        description="N. ctx.analyzer(analyzer_id) 형태소 토큰 수(lexical_text 합)",
        ge=0,
    )


class OffsetMapItem1Item(RootModel[int]):
    root: int = Field(..., ge=0)


class OffsetMapItem(RootModel[list[OffsetMapItem1Item]]):
    root: list[OffsetMapItem1Item] = Field(..., min_length=3)


class TableCellView(BaseModel):
    """
    조건(policy_applied != keep이면 필수). TableData.cells[] 앵커 셀 text의 텍스트 뷰(display_text NFC + PII 연산자, lexical_text NFKC 호환 자모 보존). offset_map은 셀 text 기준(NormalizedBlock.offset_map과 같은 정규형).
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    block_id: common_types.Hex32
    row: int = Field(..., ge=0)
    col: int = Field(..., ge=0)
    display_text: str
    lexical_text: str
    offset_map: list[OffsetMapItem] = Field(..., min_length=1)


class DerivedMeta(BaseModel):
    """
    규칙 기반 파생 메타(LLM 미사용). 필터·부스트·법령 경로 원천. 모든 필드 N.
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    dates: list[common_types.Date] | None = Field(None, description="ISO 변환(연도 필수 패턴만), 중복 제거·정렬")
    law_refs: list[LawRef] | None = Field(None, description="{법령명}/제n조/제m항 경로, 중복 제거·정렬")
    entities_normalized: list[EntityNormalized] | None = Field(
        None,
        description="규칙 기반 엔티티 구간. 상한 100,000(초안 목표)",
        max_length=100000,
    )


class Annotations(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    pii_spans: list[PiiSpan] = Field(
        ...,
        description="Y. 탐지·적용된 PII 구간(빈 배열 허용). display_text 기준(치환 후 자리); row·col이 있으면 table_cell_views 셀 뷰 기준. 상한 100,000(초안 목표)",
        max_length=100000,
    )
    content_risk: list[ContentRisk] | None = Field(None, description="N. 인젠션 L1 규칙 판정")


class NormalizedDocument(BaseModel):
    """
    normalize 스테이지 출력(설계 바이블 §5.4 NormalizedDocument·NormalizedBlock, §6.3). ParsedDocument 블록과 block_id로 1:1 대응하는 텍스트 뷰 계층 — display_text(NFC, 표시·인용 원문) / lexical_text(NFKC, BM25·키워드 입력) / offset_map(display → 원문 Block.text 코드포인트 사상) — 과 문장 구간, furniture 판정, 장르, 언어, PII 정책 적용 기록, 정규화 리포트를 담는다. 구조(type·parent_block_id·provenance·table)는 parsed_ref가 가리키는 ParsedDocument가 정본이다. 소유 문서: docs/03-contracts/04-normalized-document.md
    """

    model_config = ConfigDict(
        extra="forbid",
    )
    schema_version: str = Field(
        ...,
        description='봉투. 계약 버전, 초기 "1.0.0"',
        pattern="^1.(0|[1-9]d*).(0|[1-9]d*)$",
    )
    schema_type: Literal["NormalizedDocument"] = Field(
        ...,
        description="봉투. ArtifactRef.schema_type과 일치해야 로드",
        pattern="^[A-Z][A-Za-z0-9]*$",
    )
    tenant_id: common_types.Ulid = Field(..., description="봉투. 보안 삼중항 1")
    collection_id: common_types.Ulid = Field(..., description="봉투. 보안 삼중항 2(수집 측 단수)")
    producer: common_types.Producer = Field(..., description="봉투. normalize 스테이지 플러그인 지문")
    quality: common_types.Quality = Field(
        ...,
        description="봉투. 입력 ParsedDocument가 degraded이거나 warnings가 비어 있지 않으면 degraded",
    )
    warnings: list[common_types.Warning] = Field(
        ...,
        description="봉투. 경고 코드(normalize.segmenter_fallback 등), 콘텐츠 미포함, 빈 배열 허용",
    )
    created_at: common_types.DateTime = Field(..., description="봉투. RFC 3339 UTC")
    lineage_refs: LineageRefs = Field(
        ...,
        description="봉투. 정확히 {source, parsed}. parsed는 parsed_ref와 같은 참조. 자기 자신(normalized)과 하류 키(chunk_set, enriched, embedded) 미포함(I-3, 00 I-7)",
    )
    document_id: common_types.Ulid
    doc_version: common_types.Hex64 = Field(
        ...,
        description="= SourceDocument.content_hash(ADR-0005). ParsedDocument.doc_version과 동일",
    )
    parsed_ref: ParsedRef = Field(..., description="원 ParsedDocument 산출물. 구조 계층의 정본")
    normalizer_fingerprint: common_types.Hex64 = Field(
        ...,
        description='H("normalizer", plugin_id, plugin_version, config_hash, analyzer_id, dictionary_hash, pii_policy, pii_detector_version)(바이블 §6.2)',
    )
    analyzer_id: common_types.AnalyzerId
    dictionary_hash: common_types.Hex64 = Field(
        ..., description='컬렉션 사용자 사전 해시 H("dict", *sorted(entry 정규화 행))'
    )
    language: common_types.Bcp47 = Field(..., description="문서 주 언어(= ParsedDocument.language)")
    genre: common_types.Genre = Field(
        ...,
        description="최종 장르(요청 힌트 > 파서 > 휴리스틱). ChunkSet.genre_route의 원천",
    )
    genre_source: NormalizedDocument_1.GenreSource | None = Field(None, description="N. genre를 결정한 원천")
    blocks: list[common_types.NormalizedBlock] = Field(
        ...,
        description="ParsedDocument.blocks와 block_id 집합·순서가 같다(1:1). furniture는 제거하지 않고 boilerplate=true로 표시",
        max_length=200000,
    )
    heading_tree: list[HeadingNode] = Field(
        ...,
        description="boilerplate=false인 heading 블록의 문서 순서 목록. 청커·결정적 접두어용 사전 계산",
    )
    derived_meta: DerivedMeta | None = None
    annotations: Annotations
    pii_report: PiiReport
    normalization_report: NormalizationReport
    stats: NormalizationStats | None = None
    table_cell_views: list[TableCellView] | None = Field(
        None,
        description="조건. type=table 블록의 모든 앵커 셀 텍스트 뷰(TableData.cells[].text의 display/lexical/offset_map). pii_report.policy_applied != keep이면 필수(표가 없으면 [])이고 앵커 셀과 (block_id,row,col) 1:1(I-22); keep이면 선택. 셀 PII가 Chunk.text로 새는 것을 막는 경로(문서 §2.9)",
    )
