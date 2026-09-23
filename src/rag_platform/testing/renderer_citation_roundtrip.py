"""렌더러 `cite_id` 왕복(round-trip) 적합성 검사 — `d1..dK`가 팩 항목과 1:1이고 역매핑되는지 확인한다.

역할: 적합성 키트 구성원. `RenderedContext.citation_map[]`(공급자 인용 위치 → `cite_id` → 청크
provenance 역매핑)이 `ContextPack.items[]`와 정확히 1:1이고 출처·`segments[]` 범위로 돌아오는지 검사한다.
설계 근거: 바이블 §9.3 공통 규칙 (3)(`cite_id`는 최종 항목 연속 `d1..dK`), §5.5 `cite_id = d{rank}`
및 `citation_map`(역매핑, 항목 K개와 1:1). 필드명은 `contracts/context_pack`(`ContextItem`)·
`contracts/rendered_context.py`(`CitationMapEntry`)의 생성물을 따른다.
구성: `assert_cite_ids_bijective_with_items` — `cite_id == d{rank}`이고 집합이 `{d1..dK}`와 일치;
`assert_citation_map_round_trips_to_items` — `citation_map`이 `cite_id` 기준 항목과 1:1이며
`chunk_id`/`collection_id`/`document_id`·`segment_range`가 역매핑되는지 검사; `assert_renderer_citation_roundtrip`
— 위 두 검사를 함께 실행하는 진입점.
불변식·주의: `items`·`citation_map`은 속성 객체·매핑 어느 쪽이든 구조적으로 받아들인다. `omitted[]`는
`cite_id`가 없으므로 검사 대상이 아니다(§9.3 공통 규칙 3).
검증 계층: 1층 — `tests/unit/testing/test_renderer_citation_roundtrip.py`.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

__all__ = [
    "assert_citation_map_round_trips_to_items",
    "assert_cite_ids_bijective_with_items",
    "assert_renderer_citation_roundtrip",
]

_IDENTIFIER_FIELDS = ("chunk_id", "collection_id", "document_id")


def _field(record: Any, name: str) -> Any:
    """`record`(매핑 또는 속성 객체)에서 `name` 필드를 읽는다."""
    if isinstance(record, Mapping):
        return record[name]
    return getattr(record, name)


def assert_cite_ids_bijective_with_items(items: Sequence[Any]) -> None:
    """`ContextPack.items[]`의 `cite_id` 집합이 정확히 `{d1..dK}`와 1:1인지 검사한다.

    각 항목은 `cite_id == f"d{rank}"`(관련도순, §5.5)를 만족해야 하고, `rank`는 1..K를
    중복 없이 채워야 한다(K = `len(items)`).
    """
    k_total = len(items)
    seen_cite_ids: set[str] = set()
    for item in items:
        cite_id = str(_field(item, "cite_id"))
        rank = int(_field(item, "rank"))
        expected_cite_id = f"d{rank}"
        if cite_id != expected_cite_id:
            msg = f"item rank={rank} has cite_id={cite_id!r}, expected {expected_cite_id!r}"
            raise AssertionError(msg)
        if cite_id in seen_cite_ids:
            msg = f"duplicate cite_id {cite_id!r} among items"
            raise AssertionError(msg)
        seen_cite_ids.add(cite_id)
    expected = {f"d{rank}" for rank in range(1, k_total + 1)}
    if seen_cite_ids != expected:
        msg = f"cite_id set {seen_cite_ids} != expected {expected} for K={k_total}"
        raise AssertionError(msg)


def _assert_segment_range_within_bounds(entry: Any, item: Any) -> None:
    """`entry.segment_range`가 `item.segments[]`(비어 있으면 `[0, 0]`)의 유효 범위 안인지 검사한다."""
    start, end = (int(bound) for bound in _field(entry, "segment_range"))
    if start > end:
        msg = f"segment_range start {start} > end {end}"
        raise AssertionError(msg)
    segments = _field(item, "segments")
    segment_count = len(segments)
    if segment_count == 0:
        if (start, end) != (0, 0):
            msg = f"item without segments must have segment_range [0, 0], got [{start}, {end}]"
            raise AssertionError(msg)
    elif not (0 <= start <= segment_count and 0 <= end <= segment_count):
        msg = f"segment_range [{start}, {end}] out of bounds for {segment_count} segments"
        raise AssertionError(msg)


def assert_citation_map_round_trips_to_items(items: Sequence[Any], citation_map: Sequence[Any]) -> None:
    """`citation_map[]`이 `items[]`와 `cite_id` 기준 1:1이고, 항목의 출처·세그먼트 범위로 역매핑되는지 검사한다.

    각 `citation_map` 행에 대해 같은 `cite_id`를 가진 `items` 원소를 찾아 `chunk_id`/`collection_id`/
    `document_id`가 일치하는지, `segment_range`가 그 항목의 `segments[]` 범위 안인지 검사한다.
    """
    items_by_cite_id: dict[str, Any] = {}
    for item in items:
        cite_id = str(_field(item, "cite_id"))
        if cite_id in items_by_cite_id:
            msg = f"duplicate cite_id {cite_id!r} among items"
            raise AssertionError(msg)
        items_by_cite_id[cite_id] = item

    seen: set[str] = set()
    for entry in citation_map:
        cite_id = str(_field(entry, "cite_id"))
        if cite_id in seen:
            msg = f"duplicate citation_map entry for cite_id {cite_id!r}"
            raise AssertionError(msg)
        seen.add(cite_id)
        item = items_by_cite_id.get(cite_id)
        if item is None:
            msg = f"citation_map cite_id {cite_id!r} has no matching ContextPack item"
            raise AssertionError(msg)
        for field_name in _IDENTIFIER_FIELDS:
            item_value = _field(item, field_name)
            entry_value = _field(entry, field_name)
            if item_value != entry_value:
                msg = f"citation_map[{cite_id!r}].{field_name}={entry_value!r} != item.{field_name}={item_value!r}"
                raise AssertionError(msg)
        _assert_segment_range_within_bounds(entry, item)

    if seen != set(items_by_cite_id):
        msg = f"citation_map cite_id set {seen} != items cite_id set {set(items_by_cite_id)}"
        raise AssertionError(msg)


def assert_renderer_citation_roundtrip(items: Sequence[Any], citation_map: Sequence[Any]) -> None:
    """`assert_cite_ids_bijective_with_items`와 `assert_citation_map_round_trips_to_items`를 함께 실행한다."""
    assert_cite_ids_bijective_with_items(items)
    assert_citation_map_round_trips_to_items(items, citation_map)
