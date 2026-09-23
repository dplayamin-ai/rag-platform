"""`pack` 3단계 `reorder` — `litm_alternating`/`document_order`/`relevance_desc`로 `position`을 매긴다.

역할: `budget_cut`이 확정한 최종 K개(`PackedItem`)에 렌더 순서(`position`, 0-based)를 부여한다.
기본 `litm_alternating`은 바이블 §9.2 정본 공식(`r1` 항상 마지막, `r2` 항상 처음)을 쓰고,
`document_order`는 문서 간은 최고 관련도, 문서 내는 원문 순서로 정렬한다.
설계 근거: 04-pipelines/17 §3.4, 바이블 §9.1(pack 내부 고정 순서 3번째)·§9.2(`litm_alternating`
정본 공식), `rag_platform.testing.litm_order`(적합성 키트, K=1..5 고정 표).
구성: `litm_position(k, K)` — §9.2 정본 공식; `apply` — 세 전략 + `document_order` 폴백.
불변식·주의: `document_order`는 최종 K개 전원이 `block_refs`를 가져야 적용된다(하나라도 없으면
`relevance_desc`로 폴백하고 `Ordering.applied=False`, 문서 §3.4 P-3). `relevance_desc`·
`litm_alternating`은 항상 `applied=True`(K≤1 포함).
검증 계층: 1층(여기서 검증) — tests/retrieval/test_postprocess_pack.py,
`rag_platform.testing.litm_order.assert_pinned_table`로 K=1..5 회귀.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from rag_platform.contracts import common_types

if TYPE_CHECKING:
    from collections.abc import Sequence

    from rag_platform.retrieval.pack.budget_cut import PackedItem

__all__ = ["apply", "litm_position"]

_DIGIT_RUN = re.compile(r"(\d+)")


def _root(value: Any) -> Any:
    """RootModel 래퍼(`Hex64`·`Ulid` 등)를 순수 값으로 벗긴다. 평범한 값은 그대로."""
    return value.root if hasattr(value, "root") else value


def litm_position(k: int, k_total: int) -> int:
    """바이블 §9.2 정본 공식: 홀수 `k` → `K-(k+1)//2`, 짝수 `k` → `k//2-1`."""
    if k % 2 == 1:
        return k_total - (k + 1) // 2
    return k // 2 - 1


def _natural_key(path: str) -> tuple[Any, ...]:
    """`element_path`의 정수 인덱스 열을 자연 정렬하는 키(문서 §3.4 `document_order`)."""
    return tuple(int(tok) if tok.isdigit() else tok for tok in _DIGIT_RUN.split(path))


def _within_document_key(item: PackedItem) -> tuple[Any, ...]:
    r = item.result
    if not r.block_refs:
        # `apply`의 `document_order` 분기가 `all(...block_refs...)`를 이미 확인했다 — 도달 불가.
        msg = "document_order 분기는 block_refs 존재를 이미 확인했다"
        raise ValueError(msg)
    b = r.block_refs[0]
    return (b.page or 0, b.section_index or 0, _natural_key(b.element_path), b.original_char_start)


def apply(items: Sequence[PackedItem], strategy: common_types.OrderingStrategy) -> tuple[list[PackedItem], bool]:
    """문서 §3.4 세 전략으로 `position`을 매긴다. 두 번째 반환값은 `Ordering.applied`."""
    ranked = sorted(items, key=lambda p: p.result.final_rank)
    k_total = len(ranked)

    if strategy == common_types.OrderingStrategy.relevance_desc:
        for rank, item in enumerate(ranked, start=1):
            item.position = rank - 1
        return list(ranked), True

    if strategy == common_types.OrderingStrategy.document_order:
        can_order = k_total > 0 and all(p.result.block_refs for p in ranked)
        if not can_order:
            for rank, item in enumerate(ranked, start=1):
                item.position = rank - 1
            return list(ranked), False
        best_rank_of_doc: dict[str, int] = {}
        for p in ranked:
            doc_id = _root(p.result.document_id)
            best_rank_of_doc[doc_id] = min(best_rank_of_doc.get(doc_id, p.result.final_rank), p.result.final_rank)
        doc_sorted = sorted(
            ranked, key=lambda p: (best_rank_of_doc[_root(p.result.document_id)], _within_document_key(p))
        )
        for position, item in enumerate(doc_sorted):
            item.position = position
        return doc_sorted, True

    # litm_alternating(기본).
    for rank, item in enumerate(ranked, start=1):
        item.position = litm_position(rank, k_total) if k_total >= 1 else 0
    ordered = sorted(ranked, key=lambda p: p.position if p.position is not None else 0)
    return ordered, True
