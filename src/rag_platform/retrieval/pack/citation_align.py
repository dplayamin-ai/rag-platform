"""`pack` 4단계 `citation_align` — `cite_id`·`segments`·`provenance`·`conflicts_with`를 확정한다.

역할: `reorder`가 매긴 `position`은 그대로 두고, `final_rank` 오름차순 최종 K개에 연속
`cite_id = d1..dK`를 부여한 뒤(문서 04-pipelines/17 §3.5 1항) `segments[]`(`sentence_spans`
없으면 `block_refs` 단위, 2항)·`provenance[]`(`block_refs`의 `original_char_*` 복사, 3항)를
만들고 규칙 기반 `conflicts_with[]`(6항)를 붙여 `ContextItem`을 완성한다.
설계 근거: 04-pipelines/17 §3.5, 바이블 §9.1(pack 내부 고정 순서 4번째)·§5.5 `ContextItem`.
구성: `apply` — `PackedItem[]` → `list[ContextItem]` + `Warning[]`(`pack.conflict_unlabeled`).
불변식·주의: `text_format`은 `RankedResult`에 원천 필드가 없어 `markdown` 고정(WP-403 §7).
`conflicts_with`의 `date` 규칙은 `doc_version_label`이 이 계층에 전혀 없으므로 `doc_date` 유무
만으로 완전성을 판정한다(같은 가정). `parent`(자식 쪽 `Parent` 서브객체)는 항상 `None`.
검증 계층: 1층(여기서 검증) — tests/retrieval/test_postprocess_pack.py.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from rag_platform.contracts import common_types
from rag_platform.contracts.common_types import ConflictsWithItem, ContextItem

if TYPE_CHECKING:
    from collections.abc import Sequence

    from rag_platform.retrieval.pack.budget_cut import PackedItem

__all__ = ["apply"]

_CONFLICT_NOTE = "candidate contradiction detected by rule-based citation_align heuristic"


def _root(value: Any) -> Any:
    """RootModel 래퍼(`Hex64`·`Ulid` 등)를 순수 값으로 벗긴다. 평범한 값은 그대로."""
    return value.root if hasattr(value, "root") else value


def _block_id_for_offset(block_refs: Sequence[common_types.BlockRef], start: int) -> common_types.Hex32:
    for b in block_refs:
        if b.char_start <= start < b.char_end:
            return b.block_id
    return block_refs[0].block_id


def _segments(item: PackedItem) -> list[common_types.Segment]:
    r = item.result
    text = r.text or ""
    block_refs = r.block_refs
    # `Segment.block_id`는 필수(Hex32) — `block_refs` 없이는 만들 수 없어(계약 갭, open_issues) 그 조합은
    # 빈 목록으로 폴백한다(§0). `sentence_spans`만 있고 `block_refs`가 없는 항목은 현재 픽스처에 없다.
    if r.sentence_spans and block_refs:
        spans = [tuple(s.model_dump(mode="json")) for s in r.sentence_spans]
    elif block_refs:
        spans = [(b.char_start, b.char_end) for b in block_refs]
    else:
        return []
    segments: list[common_types.Segment] = []
    for index, (start, end) in enumerate(spans):
        block_id = _block_id_for_offset(block_refs, start)
        segments.append(
            common_types.Segment(index=index, text=text[start:end], char_start=start, char_end=end, block_id=block_id)
        )
    return segments


def _provenance(item: PackedItem) -> list[common_types.Provenance]:
    r = item.result
    if not r.block_refs:
        return []
    return [
        common_types.Provenance(
            element_path=b.element_path,
            char_start=b.original_char_start,
            char_end=b.original_char_end,
            page=b.page,
            bbox=b.bbox,
            section_index=b.section_index,
        )
        for b in r.block_refs
    ]


def _confidence_tier(score: float, *, high: float, medium: float) -> common_types.ConfidenceTier:
    if score >= high:
        return common_types.ConfidenceTier.high
    if score >= medium:
        return common_types.ConfidenceTier.medium
    return common_types.ConfidenceTier.low


def _normalize_section_path(path: Sequence[str]) -> str:
    return "/".join(p.strip() for p in path if p.strip())


def _conflict_kind(a: PackedItem, b: PackedItem) -> common_types.ConflictKind | None:
    """문서 §3.5 6항의 `version`/`source` 규칙(`date`는 `doc_date` 라벨 검사가 필요해 `apply`에서 처리)."""
    ra, rb = a.result, b.result
    same_doc = _root(ra.document_id) == _root(rb.document_id)
    if same_doc:
        if _root(ra.doc_version) != _root(rb.doc_version):
            return common_types.ConflictKind.version
        return None
    section_a = _normalize_section_path(a.header.section_path)
    section_b = _normalize_section_path(b.header.section_path)
    if bool(section_a) and section_a == section_b:
        return common_types.ConflictKind.source
    return None


def apply(
    items: Sequence[PackedItem],
    *,
    as_of: str,
    include_scores: bool = False,
    confidence_high: float = 0.7,
    confidence_medium: float = 0.4,
) -> tuple[list[ContextItem], list[common_types.Warning]]:
    """문서 §3.5 1~6항을 적용해 `PackedItem[]`을 `ContextItem[]`으로 확정한다."""
    ranked = sorted(items, key=lambda p: p.result.final_rank)
    k_total = len(ranked)
    conflicts_map: dict[int, list[ConflictsWithItem]] = {i: [] for i in range(k_total)}
    unlabeled = False

    for i in range(k_total):
        for j in range(i + 1, k_total):
            section_i = _normalize_section_path(ranked[i].header.section_path)
            section_j = _normalize_section_path(ranked[j].header.section_path)
            same_title = bool(ranked[i].header.title) and ranked[i].header.title == ranked[j].header.title
            same_section = bool(section_i) and section_i == section_j
            date_candidate = (
                same_title
                and same_section
                and _root(ranked[i].result.document_id) != _root(ranked[j].result.document_id)
            )
            kind = _conflict_kind(ranked[i], ranked[j])
            if kind is None and date_candidate:
                if ranked[i].header.doc_date is None or ranked[j].header.doc_date is None:
                    unlabeled = True
                elif _root(ranked[i].header.doc_date) != _root(ranked[j].header.doc_date):
                    kind = common_types.ConflictKind.date
            if kind is None:
                continue
            cite_a, cite_b = f"d{i + 1}", f"d{j + 1}"
            conflicts_map[i].append(ConflictsWithItem(cite_id=cite_b, kind=kind, note=_CONFLICT_NOTE))
            conflicts_map[j].append(ConflictsWithItem(cite_id=cite_a, kind=kind, note=_CONFLICT_NOTE))

    context_items: list[ContextItem] = []
    for idx, item in enumerate(ranked):
        rank = idx + 1
        r = item.result
        acl2 = item.acl2 or common_types.Acl2(
            classification=common_types.Classification.internal,
            checked=True,
            checked_at=as_of,
            source=common_types.AclCheckSource.payload,
        )
        context_items.append(
            ContextItem(
                cite_id=f"d{rank}",
                rank=rank,
                position=item.position if item.position is not None else rank - 1,
                record_id=r.record_id,
                chunk_id=r.chunk_id,
                collection_id=r.collection_id,
                document_id=r.document_id,
                doc_version=r.doc_version,
                parent_chunk_id=r.parent_chunk_id,
                item_kind=r.item_kind,
                level=r.level,
                confidence_tier=_confidence_tier(r.final_score, high=confidence_high, medium=confidence_medium),
                header=item.header,
                text=r.text or "",
                text_format=common_types.TextFormat.markdown,
                text_source=r.text_source or common_types.BlockSource.text_layer,
                ocr_confidence_min=r.ocr_confidence_min,
                segments=_segments(item),
                context_prefix=r.context_prefix,
                tables=item.tables,
                figures=item.figures,
                parent=None,
                duplicates_of=r.duplicates_of,
                conflicts_with=conflicts_map[idx] or None,
                provenance=_provenance(item),
                acl=acl2,
                scores=r.score_breakdown if include_scores else None,
                token_count=item.token_count,
            )
        )
    warnings: list[common_types.Warning] = []
    if unlabeled:
        warnings.append(
            common_types.Warning(
                code=common_types.ErrorCodeCatalog.pack_conflict_unlabeled,
                message="doc_date missing for a candidate conflict pair",
            )
        )
    return context_items, warnings
