"""`rag_platform.testing.renderer_citation_roundtrip` 단위 테스트 — `cite_id` 왕복 검사기를 검증한다.

설계 근거: 바이블 §9.3 공통 규칙 (3)(`cite_id`는 최종 항목 연속 `d1..dK`), §5.5 `citation_map`
(공급자 인용 위치 → `cite_id`·`chunk_id`·`segment_range` 역매핑, 항목 K개와 1:1). 계약 필드명은
`ContextItem`(`cite_id, rank, chunk_id, collection_id, document_id, segments`)·
`CitationMapEntry`(`cite_id, chunk_id, collection_id, document_id, segment_range`)를 따른다
(`src/rag_platform/contracts/common_types/__init__.py`, `rendered_context.py`).

구성: `test_assert_renderer_citation_roundtrip_accepts_consistent_pack` — 정상 K=3 팩 통과.
`test_assert_cite_ids_bijective_with_items_rejects_*` — `cite_id != d{rank}` / 중복 / 집합 불일치 검출.
`test_assert_citation_map_round_trips_to_items_rejects_*` — 식별자 불일치·범위 밖·누락·초과 항목 검출.

불변식: `cite_id`는 최종 항목과 1:1로 연속(`d1..dK`)해야 하며 중복·누락이 없어야 한다(§9.3).
검증 계층: 1층(여기서 검증).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from rag_platform.testing.renderer_citation_roundtrip import (
    assert_citation_map_round_trips_to_items,
    assert_cite_ids_bijective_with_items,
    assert_renderer_citation_roundtrip,
)


@dataclass(frozen=True, slots=True)
class _Item:
    cite_id: str
    rank: int
    chunk_id: str
    collection_id: str
    document_id: str
    segments: tuple[int, ...] = field(default_factory=lambda: (0,))


@dataclass(frozen=True, slots=True)
class _CitationMapEntry:
    cite_id: str
    chunk_id: str
    collection_id: str
    document_id: str
    segment_range: tuple[int, int]


def _consistent_items() -> list[_Item]:
    return [
        _Item(cite_id="d1", rank=1, chunk_id="chunk-a", collection_id="col-1", document_id="doc-1"),
        _Item(cite_id="d2", rank=2, chunk_id="chunk-b", collection_id="col-1", document_id="doc-1"),
        _Item(cite_id="d3", rank=3, chunk_id="chunk-c", collection_id="col-2", document_id="doc-2"),
    ]


def _consistent_citation_map() -> list[_CitationMapEntry]:
    return [
        _CitationMapEntry(
            cite_id="d1", chunk_id="chunk-a", collection_id="col-1", document_id="doc-1", segment_range=(0, 1)
        ),
        _CitationMapEntry(
            cite_id="d2", chunk_id="chunk-b", collection_id="col-1", document_id="doc-1", segment_range=(0, 1)
        ),
        _CitationMapEntry(
            cite_id="d3", chunk_id="chunk-c", collection_id="col-2", document_id="doc-2", segment_range=(0, 1)
        ),
    ]


def test_assert_renderer_citation_roundtrip_accepts_consistent_pack() -> None:
    assert_renderer_citation_roundtrip(_consistent_items(), _consistent_citation_map())


def test_assert_renderer_citation_roundtrip_accepts_mapping_records() -> None:
    items = [
        {"cite_id": "d1", "rank": 1, "chunk_id": "c1", "collection_id": "col", "document_id": "doc", "segments": [0]},
    ]
    citation_map = [
        {"cite_id": "d1", "chunk_id": "c1", "collection_id": "col", "document_id": "doc", "segment_range": (0, 1)},
    ]
    assert_renderer_citation_roundtrip(items, citation_map)


def test_assert_cite_ids_bijective_with_items_rejects_wrong_cite_id() -> None:
    items = [_Item(cite_id="d2", rank=1, chunk_id="c1", collection_id="col", document_id="doc")]
    with pytest.raises(AssertionError, match="expected 'd1'"):
        assert_cite_ids_bijective_with_items(items)


def test_assert_cite_ids_bijective_with_items_rejects_duplicate_cite_id() -> None:
    items = [
        _Item(cite_id="d1", rank=1, chunk_id="c1", collection_id="col", document_id="doc"),
        _Item(cite_id="d1", rank=1, chunk_id="c2", collection_id="col", document_id="doc"),
    ]
    with pytest.raises(AssertionError, match="duplicate cite_id"):
        assert_cite_ids_bijective_with_items(items)


def test_assert_citation_map_round_trips_to_items_rejects_identifier_mismatch() -> None:
    items = _consistent_items()
    citation_map = _consistent_citation_map()
    citation_map[0] = _CitationMapEntry(
        cite_id="d1", chunk_id="wrong-chunk", collection_id="col-1", document_id="doc-1", segment_range=(0, 1)
    )
    with pytest.raises(AssertionError, match="chunk_id"):
        assert_citation_map_round_trips_to_items(items, citation_map)


def test_assert_citation_map_round_trips_to_items_rejects_out_of_bounds_segment_range() -> None:
    items = [_Item(cite_id="d1", rank=1, chunk_id="c1", collection_id="col", document_id="doc", segments=(0,))]
    citation_map = [
        _CitationMapEntry(cite_id="d1", chunk_id="c1", collection_id="col", document_id="doc", segment_range=(0, 5)),
    ]
    with pytest.raises(AssertionError, match="out of bounds"):
        assert_citation_map_round_trips_to_items(items, citation_map)


def test_assert_citation_map_round_trips_to_items_rejects_missing_entry() -> None:
    items = _consistent_items()
    citation_map = _consistent_citation_map()[:-1]
    with pytest.raises(AssertionError, match="cite_id set"):
        assert_citation_map_round_trips_to_items(items, citation_map)


def test_assert_citation_map_round_trips_to_items_rejects_unmatched_cite_id() -> None:
    items = _consistent_items()
    citation_map = [
        *_consistent_citation_map(),
        _CitationMapEntry(
            cite_id="d4", chunk_id="chunk-x", collection_id="col-1", document_id="doc-1", segment_range=(0, 1)
        ),
    ]
    with pytest.raises(AssertionError, match="no matching ContextPack item"):
        assert_citation_map_round_trips_to_items(items, citation_map)
