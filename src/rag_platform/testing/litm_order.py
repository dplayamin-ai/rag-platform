"""`litm_alternating` 순서 적합성 검사 — 배치 결과가 바이블 §9.2 정본 공식·표를 만족하는지 확인한다.

역할: 적합성 키트 구성원. `pack`의 `reorder`(§8.2)가 만든 렌더 순서(`position`)가 `litm_alternating`
공식과 일치하는지, §9.2 표(K=1..5)가 회귀 없이 고정되는지 검사한다.
설계 근거: 바이블 §9.2(홀수 `k`: `position = K - (k+1)/2`, 짝수 `k`: `position = k/2 - 1`; `r1`은
항상 마지막(질의 직전), `r2`는 항상 처음). 계약 `ContextItem.rank`/`.position`(`contracts/common_types`).
구성: `LITM_ALTERNATING_TABLE` — §9.2 표(K=1..5) 고정 회귀 기준; `position_for_rank`/`render_order`
— 정본 공식과 그 렌더 순서; `assert_pinned_table` — 표 회귀 검사; `assert_litm_alternating_invariants`/
`assert_items_follow_litm_alternating` — 순열성·`r1` 마지막·`r2`(K≥2) 처음·공식 일치를 검사.
불변식·주의: `litm_alternating_primacy`(r1 처음) 변형은 범위 밖(§9.2, 골든셋 A/B 전용). `items`는
`position` 오름차순으로 주어짐을 전제한다(§5.5).
검증 계층: 1층 — `tests/unit/testing/test_litm_order.py`.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

__all__ = [
    "LITM_ALTERNATING_TABLE",
    "assert_items_follow_litm_alternating",
    "assert_litm_alternating_invariants",
    "assert_pinned_table",
    "position_for_rank",
    "render_order",
]

_PARITY_MOD = 2
_SECOND_RANK = 2

#: 바이블 §9.2 표 그대로: K(최종 항목 수) -> position 0..K-1 순서의 rank 수열.
LITM_ALTERNATING_TABLE: Mapping[int, tuple[int, ...]] = {
    1: (1,),
    2: (2, 1),
    3: (2, 3, 1),
    4: (2, 4, 3, 1),
    5: (2, 4, 5, 3, 1),
}


def position_for_rank(rank: int, k_total: int) -> int:
    """바이블 §9.2 정본 공식으로 `rank`(1-based, 최종 항목 기준)의 렌더 `position`(0-based)을 계산한다."""
    if k_total < 1:
        msg = f"k_total must be >= 1, got {k_total}"
        raise ValueError(msg)
    if not 1 <= rank <= k_total:
        msg = f"rank must be within 1..{k_total}, got {rank}"
        raise ValueError(msg)
    is_odd = rank % _PARITY_MOD == 1
    if is_odd:
        return k_total - (rank + 1) // 2
    return rank // 2 - 1


def render_order(k_total: int) -> tuple[int, ...]:
    """`position_for_rank`로부터 position 0..K-1 순서의 rank 수열(= 렌더 순서)을 구성한다."""
    ranks = range(1, k_total + 1)
    by_position = sorted(ranks, key=lambda rank: position_for_rank(rank, k_total))
    return tuple(by_position)


def assert_pinned_table() -> None:
    """§9.2 표(K=1..5)가 `position_for_rank` 공식과 정확히 일치하는지 검사한다(고정 회귀)."""
    for k_total, expected in LITM_ALTERNATING_TABLE.items():
        actual = render_order(k_total)
        if actual != expected:
            msg = f"litm_alternating table mismatch for K={k_total}: expected {expected}, got {actual}"
            raise AssertionError(msg)


def assert_litm_alternating_invariants(order: Sequence[int], k_total: int) -> None:
    """`order`(position 0..K-1 순서의 rank 수열)가 litm_alternating 불변식을 만족하는지 검사한다.

    검사 항목: (1) 1..K의 순열, (2) `rank=1`(`r1`)이 마지막(질의 직전), (3) `K>=2`면
    `rank=2`(`r2`)가 처음(최상위 두 순위가 양 끝), (4) 각 위치가 `position_for_rank` 공식과 일치.
    """
    if len(order) != k_total:
        msg = f"order length {len(order)} != k_total {k_total}"
        raise AssertionError(msg)
    if sorted(order) != list(range(1, k_total + 1)):
        msg = f"order {order} is not a permutation of 1..{k_total}"
        raise AssertionError(msg)
    if order[-1] != 1:
        msg = f"rank 1 (r1) must be last (immediately before the query), got order[-1]={order[-1]}"
        raise AssertionError(msg)
    if k_total >= _SECOND_RANK and order[0] != _SECOND_RANK:
        msg = f"rank 2 (r2) must be first, got order[0]={order[0]}"
        raise AssertionError(msg)
    for position, rank in enumerate(order):
        expected_position = position_for_rank(rank, k_total)
        if expected_position != position:
            msg = f"rank {rank} placed at position {position}, but formula expects {expected_position}"
            raise AssertionError(msg)


def _rank_of(item: Any) -> int:
    """`item`(속성 객체 또는 매핑)의 `rank` 필드를 읽는다."""
    if isinstance(item, Mapping):
        return int(item["rank"])
    return int(item.rank)


def _position_of(item: Any) -> int:
    """`item`(속성 객체 또는 매핑)의 `position` 필드를 읽는다."""
    if isinstance(item, Mapping):
        return int(item["position"])
    return int(item.position)


def assert_items_follow_litm_alternating(items: Sequence[Any]) -> None:
    """`ContextPack.items[]`류 시퀀스(속성/매핑에 `rank`·`position` 보유)가 litm_alternating 결과인지 검사한다.

    `items`는 `position` 오름차순 0..K-1로 주어져야 한다(`ContextPack.items` 관례, 바이블 §5.5).
    """
    k_total = len(items)
    positions = [_position_of(item) for item in items]
    if positions != list(range(k_total)):
        msg = f"items must be given position-ascending 0..{k_total - 1}, got {positions}"
        raise AssertionError(msg)
    order = [_rank_of(item) for item in items]
    assert_litm_alternating_invariants(order, k_total)
