"""`rag_platform.testing.litm_order` 단위 테스트 — `litm_alternating` 정본 공식·표·불변식을 검증한다.

설계 근거: 바이블 §9.2(정본 공식 — 홀수 `k`: `position = K - (k+1)/2`, 짝수 `k`: `position = k/2 - 1`;
`r1` 항상 마지막, `r2` 항상 처음; K=1..5 고정 표).

구성: `test_render_order_matches_bible_table_for_k_1_to_5` — 표 K=1..5 직접 대조.
`test_assert_pinned_table_passes` — 회귀 검사기 자체가 통과.
`test_assert_litm_alternating_invariants_*` — 순열 위반/`r1` 위치 위반/`r2` 위치 위반을 검출.
`test_assert_items_follow_litm_alternating_*` — 매핑·속성 객체 양쪽에서 성공/실패를 검출.

검증 계층: 1층(여기서 검증).
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from rag_platform.testing.litm_order import (
    LITM_ALTERNATING_TABLE,
    assert_items_follow_litm_alternating,
    assert_litm_alternating_invariants,
    assert_pinned_table,
    position_for_rank,
    render_order,
)


@dataclass(frozen=True, slots=True)
class _Item:
    rank: int
    position: int


@pytest.mark.parametrize("k_total", [1, 2, 3, 4, 5])
def test_render_order_matches_bible_table_for_k_1_to_5(k_total: int) -> None:
    assert render_order(k_total) == LITM_ALTERNATING_TABLE[k_total]


def test_assert_pinned_table_passes() -> None:
    assert_pinned_table()


def test_position_for_rank_rejects_out_of_range_rank() -> None:
    with pytest.raises(ValueError, match="rank must be within"):
        position_for_rank(6, 5)


def test_position_for_rank_rejects_non_positive_k_total() -> None:
    with pytest.raises(ValueError, match="k_total must be >= 1"):
        position_for_rank(1, 0)


def test_assert_litm_alternating_invariants_accepts_k5_table() -> None:
    assert_litm_alternating_invariants(LITM_ALTERNATING_TABLE[5], 5)


def test_assert_litm_alternating_invariants_rejects_non_permutation() -> None:
    with pytest.raises(AssertionError, match="permutation"):
        assert_litm_alternating_invariants([2, 4, 5, 3, 3], 5)


def test_assert_litm_alternating_invariants_rejects_r1_not_last() -> None:
    with pytest.raises(AssertionError, match="rank 1"):
        assert_litm_alternating_invariants([1, 4, 5, 3, 2], 5)


def test_assert_litm_alternating_invariants_rejects_r2_not_first() -> None:
    with pytest.raises(AssertionError, match="rank 2"):
        assert_litm_alternating_invariants([4, 2, 5, 3, 1], 5)


def test_assert_items_follow_litm_alternating_accepts_mapping_items() -> None:
    items = [{"rank": rank, "position": position} for position, rank in enumerate(LITM_ALTERNATING_TABLE[4])]
    assert_items_follow_litm_alternating(items)


def test_assert_items_follow_litm_alternating_accepts_attribute_items() -> None:
    items = [_Item(rank=rank, position=position) for position, rank in enumerate(LITM_ALTERNATING_TABLE[3])]
    assert_items_follow_litm_alternating(items)


def test_assert_items_follow_litm_alternating_rejects_wrong_position_order() -> None:
    items = [_Item(rank=2, position=1), _Item(rank=1, position=0)]
    with pytest.raises(AssertionError, match="position-ascending"):
        assert_items_follow_litm_alternating(items)


def test_assert_items_follow_litm_alternating_rejects_relevance_desc_order() -> None:
    """`relevance_desc`(관련도 내림차순, position=rank-1) 배치는 litm_alternating과 다르므로 K>=3에서 거부돼야 한다."""
    items = [_Item(rank=rank, position=rank - 1) for rank in (1, 2, 3)]
    with pytest.raises(AssertionError):
        assert_items_follow_litm_alternating(items)
