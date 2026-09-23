"""인용 역매핑(citation round-trip) — `RenderedContext.citation_map` 행 생성과 공급자 인용 → 원문 좌표 역매핑.

역할: 렌더러(`markdown.py`, `anthropic_search_result.py`)가 항목마다 만드는
`CitationMapEntry`(cite_id ↔ chunk provenance) 빌더와, 바이블 §4.6 `CitationResolution`/
`map_back` 의사코드를 구현해 공급자 인용 위치를 원문 `Provenance`까지 되돌린다.
설계 근거: 바이블 §9.3 공통 규칙(3)(`cite_id` 연속 `d1..dK`), §5.5 `citation_map`
(`contracts/rendered_context.py`의 `CitationMapEntry`), §4.6(`CitationResolution`은 계약이
아닌 이 문서 제안 타입 — `answer` 응답·평가 하네스 내부 값).
구성: `SearchResultLocation`/`ContentBlockLocation`/`CharRange` — 공급자 인용 키 3종;
`CitationResolution` — 역매핑 결과; `build_entry` — 항목 하나에서 `CitationMapEntry` 생성;
`map_back` — §4.6 알고리즘(불명 키·환각 ID·범위 밖·본문 불일치를 `unresolved`로 표시).
불변식·주의: `ContextItem`에는 §4.6 의사코드가 참조하는 `block_refs`가 없다(계약에는
`provenance[]`만 있음) — `map_back`은 `len(provenance) == len(segments)`(다단락 병합 부모처럼
블록당 세그먼트 1개)일 때만 정확히 좁히고, 그 외에는 최선 근사로 첫 provenance를 쓴다(설계 갭,
open_issues에 기록).
검증 계층: 1층(여기서 검증) — `tests/retrieval/test_query_e2e.py`.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal

from rag_platform.contracts import common_types
from rag_platform.contracts.rendered_context import CharRangeItem, CitationMapEntry, RenderedContext, SegmentRangeItem

if TYPE_CHECKING:
    from rag_platform.contracts.context_pack import ContextPack

__all__ = [
    "CharRange",
    "CitationResolution",
    "ContentBlockLocation",
    "ProviderCitation",
    "SearchResultLocation",
    "as_str",
    "build_entry",
    "map_back",
]


@dataclass(frozen=True)
class SearchResultLocation:
    """`anthropic_search_result`/`anthropic_document`의 native 인용 위치(§4.4 응답 인용 행)."""

    search_result_index: int
    start_block_index: int
    end_block_index: int
    cited_text: str | None = None


@dataclass(frozen=True)
class ContentBlockLocation:
    """`anthropic_document`의 native 인용 위치(§9.3 표 `content_block_location`)."""

    document_index: int
    start_block_index: int
    end_block_index: int
    cited_text: str | None = None


@dataclass(frozen=True)
class CharRange:
    """문자열 렌더러(gemini `start_index/end_index`, `char_range` 기반) 인용 위치(§4.6)."""

    start: int
    end: int
    cited_text: str | None = None


#: bracket_id 계열([dN] 마커만): `provider_key`(=cite_id 문자열)를 직접 넘긴다.
ProviderCitation = SearchResultLocation | ContentBlockLocation | CharRange

_REASON_UNKNOWN_KEY = "unknown_key"
_REASON_OUT_OF_RANGE = "out_of_range"
_REASON_TEXT_MISMATCH = "text_mismatch"
_REASON_HALLUCINATED_ID = "hallucinated_id"


@dataclass(frozen=True)
class CitationResolution:
    """공급자 인용 1건의 역매핑 결과(바이블 §4.6). 계약이 아닌 제안 타입."""

    status: Literal["resolved", "unresolved"]
    cite_id: str | None
    chunk_id: str | None
    collection_id: str | None
    document_id: str | None
    segment_indices: list[int]
    provenance: list[common_types.Provenance]
    cited_text_match: bool | None
    reason: str | None


def _unresolved(reason: str) -> CitationResolution:
    return CitationResolution(
        status="unresolved",
        cite_id=None,
        chunk_id=None,
        collection_id=None,
        document_id=None,
        segment_indices=[],
        provenance=[],
        cited_text_match=None,
        reason=reason,
    )


def _int(value: Any) -> int:
    """`RootModel[int]`(`SegmentRangeItem`/`CharRangeItem`) 또는 순수 `int`에서 값을 뽑는다."""
    root = getattr(value, "root", None)
    return int(root) if root is not None else int(value)


def as_str(value: object) -> str:
    """`RootModel[str]`(`CiteId`/`Hex64`/`Ulid`/`Uri`/`Date`...) 또는 순수 값에서 평문 문자열을 뽑는다.

    주의: `str(root_model_instance)`는 pydantic 기본 `__str__`이 `"root='d2'"` 같은 표현을
    돌려주는 함정이 있다 — 렌더러가 만드는 모든 문자열(헤더 라인, `rag://` 출처, `[dN]` 마커)은
    이 함수로 값을 뽑아야 한다.
    """
    root = getattr(value, "root", None)
    return str(root) if root is not None else str(value)


def build_entry(
    item: common_types.ContextItem,
    provider_key: int | str,
    *,
    block_offset: int | None = None,
    char_range: tuple[int, int] | None = None,
    segment_range: tuple[int, int] | None = None,
) -> CitationMapEntry:
    """`item` 하나에서 `CitationMapEntry` 한 행을 만든다(바이블 §5.5 `citation_map`).

    `segment_range`를 생략하면 항목 전체(`[0, len(segments))`, 표 항목의 §4.4 규칙과 동일)로
    잡는다. `char_range`는 문자열 렌더러에서 항목 본문이 최종 렌더 문자열에서 차지하는
    코드포인트 범위(끝 미포함)다.
    """
    start, end = segment_range if segment_range is not None else (0, len(item.segments))
    return CitationMapEntry(
        provider_key=provider_key,
        cite_id=item.cite_id,
        chunk_id=item.chunk_id,
        collection_id=item.collection_id,
        document_id=item.document_id,
        segment_range=(SegmentRangeItem(start), SegmentRangeItem(end)),
        block_offset=block_offset,
        char_range=(CharRangeItem(char_range[0]), CharRangeItem(char_range[1])) if char_range is not None else None,
    )


def _normalize(text: str) -> str:
    """NFC + 공백 정규화(바이블 §4.6 `normalize`; 데이터마킹 마커 제거는 호출자 책임)."""
    return " ".join(unicodedata.normalize("NFC", text).split())


def _narrow_provenance(item: common_types.ContextItem, segment_index: int) -> common_types.Provenance:
    """세그먼트 하나가 속한 원문 `Provenance`를 좁혀 돌려준다.

    두 경우만 정확히 처리한다: (1) `len(provenance) == len(segments)`(블록당 세그먼트 1개, 다단락
    병합 부모의 일반형) — 같은 인덱스의 `provenance[i]`를 그대로 쓴다(이미 그 블록 좌표라 추가
    좁히기가 필요 없다, §6.3 예시). (2) 리프 항목처럼 `provenance`가 1개뿐이면 세그먼트의
    `char_start`를 그 하나의 블록 오프셋에 더해 좁힌다. 그 외(블록 경계와 세그먼트 경계가 어긋나는
    혼합형)는 `block_refs`가 계약에 없어(설계 갭) 첫 provenance를 근사로 반환한다.
    """
    provenance = item.provenance
    segment = item.segments[segment_index]
    if len(provenance) == len(item.segments):
        return provenance[segment_index]
    if len(provenance) == 1:
        base = provenance[0]
        return common_types.Provenance(
            element_path=base.element_path,
            char_start=base.char_start + segment.char_start,
            char_end=min(base.char_end, base.char_start + segment.char_end),
            page=base.page,
            bbox=base.bbox,
            section_index=base.section_index,
        )
    return provenance[0]


def _provider_key_of(citation: ProviderCitation | str) -> int | str:
    """공급자 인용에서 `citation_map`을 찾을 키를 뽑는다(§4.6: native는 블록 인덱스, 문자열은 자기 자신)."""
    if isinstance(citation, SearchResultLocation):
        return citation.search_result_index
    if isinstance(citation, ContentBlockLocation):
        return citation.document_index
    if isinstance(citation, CharRange):
        return citation.cited_text or ""
    return citation


def _segment_indices_of(
    citation: ProviderCitation | str,
    entry: CitationMapEntry,
    item: common_types.ContextItem,
    bounds: tuple[int, int],
) -> list[int]:
    """`citation`의 위치 표현(블록 인덱스/문자 범위/마커뿐)에서 세그먼트 인덱스 목록을 뽑는다."""
    seg_start, _seg_end = bounds
    if isinstance(citation, SearchResultLocation | ContentBlockLocation):
        block_offset = entry.block_offset or 0
        block_start = seg_start + citation.start_block_index - block_offset
        block_end = seg_start + citation.end_block_index - block_offset
        return list(range(block_start, block_end))
    if isinstance(citation, CharRange) and entry.char_range is not None:
        range_start = _int(entry.char_range[0])
        off = (citation.start - range_start, citation.end - range_start)
        return [s.index for s in item.segments if s.char_start < off[1] and off[0] < s.char_end]
    return list(range(*bounds))


def _cited_text_of(citation: ProviderCitation | str) -> str | None:
    """`citation`이 `cited_text`를 실어 오는 종류면 그 값을, 마커뿐이면 `None`을 돌려준다."""
    if isinstance(citation, SearchResultLocation | ContentBlockLocation | CharRange):
        return citation.cited_text
    return None


def map_back(rendered: RenderedContext, pack: ContextPack, citation: ProviderCitation | str) -> CitationResolution:
    """공급자 인용 하나를 팩 `provenance`까지 되돌린다(바이블 §4.6 `map_back` 의사코드).

    `citation`이 `str`이면 bracket_id 마커([dN])로 해석해 그 문자열 자체를 `provider_key`로
    쓴다(마커 계열은 `citation_map`의 `provider_key == cite_id`). 실패는 예외를 던지지 않고
    `status="unresolved"` + 고정 어휘 `reason`으로 표시한다(§4.6: 인용을 버리지 않는다).
    """
    by_key = {entry.provider_key: entry for entry in rendered.citation_map}
    entry = by_key.get(_provider_key_of(citation))
    if entry is None:
        return _unresolved(_REASON_UNKNOWN_KEY)

    items_by_cite_id = {as_str(pack_item.cite_id): pack_item for pack_item in pack.items}
    item = items_by_cite_id.get(as_str(entry.cite_id))
    if item is None:
        return _unresolved(_REASON_HALLUCINATED_ID)

    bounds = (_int(entry.segment_range[0]), _int(entry.segment_range[1]))
    seg_start, seg_end = bounds
    seg = _segment_indices_of(citation, entry, item, bounds)
    if any(i < seg_start or i >= seg_end for i in seg):
        return _unresolved(_REASON_OUT_OF_RANGE)

    provenance = [_narrow_provenance(item, i) for i in seg]
    cited_text = _cited_text_of(citation)
    match = None
    if cited_text is not None:
        joined = " ".join(item.segments[i].text for i in seg)
        match = _normalize(cited_text) in _normalize(joined)
    if match is False:
        return _unresolved(_REASON_TEXT_MISMATCH)

    return CitationResolution(
        status="resolved",
        cite_id=as_str(entry.cite_id),
        chunk_id=as_str(entry.chunk_id),
        collection_id=as_str(entry.collection_id),
        document_id=as_str(entry.document_id),
        segment_indices=seg,
        provenance=provenance,
        cited_text_match=match,
        reason=None,
    )
