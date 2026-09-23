"""후처리 `parent_expand` — small-to-big 병합: 다수 적중 자식 묶음을 부모 항목 하나로 교체한다.

역할: 같은 `(chunk_set_blake3, parent_chunk_id)` 자식 집합 C가 (a) `n_children` 대비 비율
또는 (b) 자식 토큰 합 ≥ 부모 토큰의 60%를 만족하면 `ChunkTextStore`에서 부모 텍스트 번들을
읽어 자식 중 최상위(`final_rank` 최소)의 자리를 부모 항목으로 바꾼다.
설계 근거: 04-pipelines/17 §2.5(의사코드·표), 바이블 §8.2·§13.2. `n_children` 부재 시 조건
(a)는 §2.5 결정문("|C|≥2로 대체")을 따른다 — 의사코드 `ratio_ok = n_children is not None`은
이와 불일치하므로(미해결 이슈 3) 결정문을 우선(WP-403 §6.4).
구성: `ParentTextMiss`/`ChunkTextStore`/`ParentEntry` — `sdk.ports`에서 재노출(F4 배치 검증으로
정식 SDK 포트로 승격, 바이블 §13.2 — `retrieval`은 이 포트를 구현할 Valkey/오브젝트 스토리지
어댑터를 import할 수 없어 `sdk`에 둔다); `apply` — 의사코드 구현.
불변식·주의: 부모 항목은 `model_validate(dict)`로 재구성한다(`model_copy`는 검증을 건너뛰어
RootModel 필드에 원시 문자열이 남을 위험). 부모 ACL은 자식과 같아 권한을 올리지 않는다(E10).
검증 계층: 1층(여기서 검증) — tests/retrieval/test_postprocess_pack.py.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from rag_platform.contracts import common_types
from rag_platform.contracts.common_types import RankedResult
from rag_platform.retrieval.postprocess.relevance_gate import StepResult
from rag_platform.sdk.ports import ChunkTextStore, ParentEntry, ParentTextMiss

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from rag_platform.sdk.ports import TokenCounter

__all__ = ["ChunkTextStore", "ParentEntry", "ParentTextMiss", "apply", "child_tokens"]

_MIN_CHILDREN_FOR_MERGE = 2
_TOKEN_RATIO_FOR_MERGE = 0.6


def _root(value: Any) -> Any:
    """RootModel 래퍼(`Hex64`·`Ulid` 등)를 순수 값으로 벗긴다. 평범한 값은 그대로."""
    return value.root if hasattr(value, "root") else value


def child_tokens(r: RankedResult, token_counter: TokenCounter) -> int:
    """`token_count_primary`(바이블 §5.5 1.3.0 선택 필드) 우선, 없으면 재카운트(문서 §2.5)."""
    if r.token_count_primary is not None:
        return r.token_count_primary
    return token_counter.count(r.text or "")


def _document_order_key(r: RankedResult) -> tuple[int, int, int]:
    """`ordinal` 부재 시 폴백 원문 순서 키(문서 §2.5: `block_refs[0]` 기반)."""
    if r.block_refs:
        b = r.block_refs[0]
        return (b.page or 0, b.section_index or 0, b.original_char_start)
    return (0, 0, 0)


def _group_key(r: RankedResult) -> tuple[str, str] | None:
    """`level=0`이고 부모·청크세트가 모두 있는 자식만 그룹 대상(§2.5)."""
    is_leaf_child = r.level == common_types.ChunkLevel.integer_0 and r.parent_chunk_id is not None
    if is_leaf_child and r.chunk_set_blake3 is not None:
        return (_root(r.chunk_set_blake3), _root(r.parent_chunk_id))
    return None


def _group_children(results: Sequence[RankedResult]) -> dict[tuple[str, str], list[tuple[int, RankedResult]]]:
    groups: dict[tuple[str, str], list[tuple[int, RankedResult]]] = {}
    for idx, r in enumerate(results):
        key = _group_key(r)
        if key is not None:
            groups.setdefault(key, []).append((idx, r))
    return {k: g for k, g in groups.items() if len(g) >= _MIN_CHILDREN_FOR_MERGE}


def _load_parent_bundles(
    wanted: dict[tuple[str, str], list[tuple[int, RankedResult]]],
    *,
    text_store: ChunkTextStore,
    security: common_types.SecurityContext,
    remaining_ms: Callable[[], int] | None,
    min_bundle_ms: int,
) -> tuple[dict[str, ParentEntry], common_types.DegradedEntry | None]:
    """세트별로 1회 `get_many`(§2.5 "번들 로드"). 지연 예산·조회 실패 시 `(부분 결과, 저하 항목)`."""
    bundles: dict[str, set[str]] = {}
    for cs_hash, parent_id in wanted:
        bundles.setdefault(cs_hash, set()).add(parent_id)

    parents: dict[str, ParentEntry] = {}
    for cs_hash, pids in bundles.items():
        if remaining_ms is not None and remaining_ms() < min_bundle_ms:
            return parents, common_types.DegradedEntry(
                component=common_types.DegradedComponent.parent_expand,
                reason=common_types.DegradedReason.latency_budget,
            )
        try:
            parents.update(text_store.get_many(cs_hash, sorted(pids), security))
        except ParentTextMiss:
            return parents, common_types.DegradedEntry(
                component=common_types.DegradedComponent.parent_expand, reason=common_types.DegradedReason.unavailable
            )
    return parents, None


def _build_parent_item(
    top: RankedResult, parent_id: str, children: Sequence[RankedResult], parent: ParentEntry
) -> RankedResult:
    ordered_children = sorted(
        children,
        key=lambda c: (0, c.ordinal) if c.ordinal is not None else (1, *_document_order_key(c)),
    )
    channels_hit = sorted({ch for c in children for ch in c.channels_hit})
    variant_ids = sorted({_root(v) for c in children for v in c.variant_ids})
    explain = list(dict.fromkeys([*top.explain, common_types.ExplainCode.parent_of_n_hits]))
    base = top.model_dump(mode="json")
    base.update(
        {
            "record_id": None,
            "chunk_id": parent_id,
            "item_kind": common_types.ItemKind.parent.value,
            "level": int(common_types.ChunkLevel.integer_1),
            "parent_chunk_id": None,
            "expanded_from": [_root(c.chunk_id) for c in ordered_children],
            "channels_hit": [c.value for c in channels_hit],
            "variant_ids": variant_ids,
            "explain": [e.value for e in explain],
            "text": parent.text,
            "block_refs": [b.model_dump(mode="json") for b in parent.block_refs] if parent.block_refs else None,
            "sentence_spans": [s.model_dump(mode="json") for s in parent.sentence_spans]
            if parent.sentence_spans
            else None,
            "text_source": parent.text_source.value if parent.text_source else None,
            "ocr_confidence_min": parent.ocr_confidence_min,
            "heading_path": parent.heading_path,
            "numbering_path": parent.numbering_path,
            "page_start": parent.page_start,
            "page_end": parent.page_end,
        }
    )
    return RankedResult.model_validate(base)


def _should_merge(
    children: Sequence[RankedResult],
    parent: ParentEntry,
    *,
    tokenizer_id: str,
    token_counter: TokenCounter,
    ratio_threshold: float,
    max_parent_tokens: int,
    max_parent_text_bytes: int,
    used_tokens: int,
    budget_guard: float,
) -> tuple[int, int] | None:
    """병합 조건(§2.5 (a)/(b) + 크기·예산 사전검사)을 만족하면 `(p_tokens, c_tokens)`, 아니면 `None`."""
    p_tokens = parent.token_counts.get(tokenizer_id)
    if p_tokens is None:
        return None
    c_tokens = sum(child_tokens(c, token_counter) for c in children)
    ratio_ok = parent.n_children is None or (len(children) / parent.n_children) >= ratio_threshold
    token_ok = c_tokens >= _TOKEN_RATIO_FOR_MERGE * p_tokens
    if not (ratio_ok or token_ok):
        return None
    if p_tokens > max_parent_tokens or len(parent.text.encode("utf-8")) > max_parent_text_bytes:
        return None
    if used_tokens - c_tokens + p_tokens > budget_guard:
        return None
    return p_tokens, c_tokens


def apply(
    results: Sequence[RankedResult],
    *,
    text_store: ChunkTextStore,
    security: common_types.SecurityContext,
    token_counter: TokenCounter,
    ratio_threshold: float = 0.5,
    max_parent_tokens: int = 2048,
    max_parent_text_bytes: int = 32_768,
    max_context_tokens: int,
    reserved_answer_tokens: int,
    budget_guard_ratio: float = 0.8,
    remaining_ms: Callable[[], int] | None = None,
    min_bundle_ms: int = 15,
) -> StepResult:
    """문서 §2.5 `parent_expand(results, plan, ctx)`의 구현."""
    wanted = _group_children(results)
    if not wanted:
        return StepResult(results=list(results), omitted=[], removed=0, added=0, degraded=[])

    parents, degraded = _load_parent_bundles(
        wanted, text_store=text_store, security=security, remaining_ms=remaining_ms, min_bundle_ms=min_bundle_ms
    )
    if degraded is not None:
        return StepResult(results=list(results), omitted=[], removed=0, added=0, degraded=[degraded])

    budget_guard = budget_guard_ratio * (max_context_tokens - reserved_answer_tokens)
    used = sum(child_tokens(r, token_counter) for r in results)
    out = list(results)
    added = 0
    tokenizer_id = token_counter.tokenizer_id
    ordered_groups = sorted(wanted.items(), key=lambda kv: min(c.final_rank for _i, c in kv[1]))
    for (_cs_hash, parent_id), indexed_children in ordered_groups:
        children = [c for _i, c in indexed_children]
        parent = parents.get(parent_id)
        if parent is None:
            continue
        merge = _should_merge(
            children,
            parent,
            tokenizer_id=tokenizer_id,
            token_counter=token_counter,
            ratio_threshold=ratio_threshold,
            max_parent_tokens=max_parent_tokens,
            max_parent_text_bytes=max_parent_text_bytes,
            used_tokens=used,
            budget_guard=budget_guard,
        )
        if merge is None:
            continue
        p_tokens, c_tokens = merge
        top_idx, top = min(indexed_children, key=lambda ic: ic[1].final_rank)
        out[top_idx] = _build_parent_item(top, parent_id, children, parent)
        used += p_tokens - c_tokens
        added += 1
    return StepResult(results=out, omitted=[], removed=0, added=added, degraded=[])
