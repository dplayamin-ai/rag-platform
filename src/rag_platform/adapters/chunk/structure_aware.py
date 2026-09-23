"""`chunker.structure_aware` 스테이지 — `NormalizedDocument`를 축소 범위 `ChunkSet`으로 만든다(F2-01).

역할: 04-pipelines/10 §2(단계 A~G: 요소 필터·섹션 경로·블록 그룹·초과 분할·병합·부모 생성·좌표/ID/접두어)
와 §3(부모-자식 계층)·§7.2(파라미터 기본값)을 `NormalizedDocument` 위에서 재현해 `ChunkSet`을 만든다.
`NormalizedBlock`에는 `Block.type`이 없어(구조는 `ParsedDocument`가 정본) heading 여부는
`heading_tree`의 `block_id` 집합으로만 판정하고, 그 외 비-boilerplate 블록은 모두 `item_kind=text` 리프
후보 1개로 취급한다 — 표·그림·목록·각주·장르 규칙(`genre_rules`)·`flat_text` 폴백은 `ParsedDocument`
구조 필드가 필요해 이 WP 범위 밖(DEFERRED, `docs/13-implementation/wp/WP-201-chunk-structure-aware.md`).
설계 근거: 바이블 §4.1(5멤버 스테이지 프로토콜)·§4.2 `chunk` 행·§5.4 `ChunkSet`·`Chunk`·`BlockRef`·§6.2
(`chunk_id`·`chunker_config_hash` 결합식); 04-pipelines/10 §2·§3·§7.2; ADR-0019(토큰 예산·카운터 역할
분리)·ADR-0020(구조 인식 청커·부모-자식)·ADR-0004(결정적 `chunk_id`)·ADR-0029(3-텍스트 규칙, 참조만).
구성: `StructureAwareChunkerConfig` — `config_schema`; `StructureAwareChunkerStage` — 5멤버(`plugin_id`/
`config_schema`/`capabilities()`/`fingerprint()`/`run()`); `default_token_counter`/
`ApproxCharTokenCounter` — `sdk.ports.TokenCounter` 포트의 기본 구현(문자 기반 근사, tiktoken 있으면
사용); `_split_sentences` — kss 있으면 사용, 없으면 정규식 폴백; 단계 D~G 순수 함수들.
불변식·주의: `block_refs` 오프셋 합집합이 `text`를 재구성한다(병합·부모 생성은 U+000A 결합 + 오프셋
누적 이동만). `level=0`은 `token_counts[primary] ≤ leaf_max_tokens`. `context_prefix.deterministic`은
`text`와 분리 저장. `adapters`는 `storage`/`security`/`plugins`/`orchestration`을 import하지 않는다
(`sdk`/`contracts`만). `StageError` 코드는 §5.7 철자만.
검증 계층: 1층(여기서 검증) — `tests/adapters/chunk/test_structure_aware.py`. `needs_docker`/`needs_model`/
`needs_gpu`/`needs_network` 해당 없음(순수 함수; tiktoken·kss는 optional import + 폴백).
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, replace
from datetime import UTC
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict, Field
from ulid import ULID

from rag_platform.contracts import common_types as ct
from rag_platform.contracts.chunk_set import (
    ChunkSet,
    ChunkSetStats,
    LineageRefs as ChunkSetLineageRefs,
    NormalizedRef,
    TokenBudgets,
)
from rag_platform.sdk.hashing import blake3_hex, chunk_id as compute_chunk_id, hash_of
from rag_platform.sdk.stage import StageError

if TYPE_CHECKING:
    from collections.abc import Sequence
    from datetime import datetime

    from rag_platform.contracts.normalized_document import HeadingNode, NormalizedDocument
    from rag_platform.sdk.ports import TokenCounter

__all__ = [
    "ApproxCharTokenCounter",
    "StructureAwareChunkerConfig",
    "StructureAwareChunkerStage",
    "default_token_counter",
]

PLUGIN_VERSION = "0.1.0"
DEFAULT_TOKENIZER = "hf:BAAI/bge-m3"
DEFAULT_SECONDARY_TOKENIZERS = ("tiktoken:o200k_base",)
#: 표는 이 WP 범위 밖이지만 `TokenBudgets.table_row_group_tokens`는 필수 필드다(바이블 §7.2 기본값 그대로).
_DEFAULT_TABLE_ROW_GROUP_TOKENS = 256
#: 04-pipelines/10 §2.7 — 자식이 이 수 미만인 묶음은 부모를 만들지 않는다(부모=자식 반복 방지).
_MIN_PARENT_CHILDREN = 2
_CONTEXT_PREFIX_SEP = f" {chr(0x203A)} "  # U+203A SINGLE RIGHT-POINTING ANGLE QUOTATION MARK, 04-pipelines/10 §2.8
_SOURCE_RANK: dict[ct.BlockSource, int] = {
    ct.BlockSource.text_layer: 0,
    ct.BlockSource.converted: 1,
    ct.BlockSource.vlm: 2,
    ct.BlockSource.ocr: 3,
}
_SENTENCE_BOUNDARY_RE = re.compile(r"[.!?…]+[\"')\]]*|\n+")
_WORD_RE = re.compile(r"\S+\s*")


# ----------------------------------------------------------------------------
# TokenCounter 포트 기본 구현 (sdk.ports.TokenCounter; 모델 다운로드 금지 — 근사 + optional tiktoken)
# ----------------------------------------------------------------------------


@dataclass(frozen=True)
class ApproxCharTokenCounter:
    """`TokenCounter` 포트 기본 구현 — 문자 수 기반 근사(모델 가중치 다운로드 금지, ADR-0019 F1 참고).

    실 임베딩/LLM 토크나이저(HF `tokenizers`·`tiktoken`)를 내려받지 않고도 예산 판정이 가능하도록 하는
    자리표시자다. 실 카운터는 `ctx.token_counter`로 주입되면 이 클래스보다 우선한다.
    """

    tokenizer_id: str
    chars_per_token: float = 2.0

    def count(self, text: str) -> int:
        """`ceil(len(text) / chars_per_token)`, 빈 문자열은 0."""
        if not text:
            return 0
        return max(1, math.ceil(len(text) / self.chars_per_token))


@dataclass
class _TiktokenTokenCounter:
    """tiktoken이 설치·해소 가능할 때만 쓰는 정확 카운터(선택, ADR-0020 §6.7 `secondary_tokenizers`)."""

    tokenizer_id: str
    _encoding: Any

    def count(self, text: str) -> int:
        return len(self._encoding.encode(text)) if text else 0


def default_token_counter(tokenizer_id: str) -> TokenCounter:
    """`tokenizer_id`에 대한 기본 `TokenCounter`: `tiktoken:*`는 가능하면 tiktoken, 그 외 문자 근사.

    tiktoken은 선택 의존성이다(ADR-0020 잠금 대상이나 이 WP는 `uv add`하지 않는다) — 미설치이거나
    인코딩 해소가 실패하면(오프라인 등) 조용히 근사 카운터로 내려간다.
    """
    if tokenizer_id.startswith("tiktoken:"):
        encoding_name = tokenizer_id.split(":", 1)[1]
        try:
            import tiktoken  # type: ignore[import-not-found] # noqa: PLC0415 - 선택 의존성, 지연 임포트

            encoding = tiktoken.get_encoding(encoding_name)
        except Exception:  # noqa: BLE001 - 선택 의존성 부재/네트워크 불가는 모두 근사로 폴백
            return ApproxCharTokenCounter(tokenizer_id=tokenizer_id)
        return _TiktokenTokenCounter(tokenizer_id=tokenizer_id, _encoding=encoding)
    return ApproxCharTokenCounter(tokenizer_id=tokenizer_id)


# ----------------------------------------------------------------------------
# 문장 경계 (D1 대상; kss 있으면 사용, 없으면 정규식 폴백)
# ----------------------------------------------------------------------------


def _regex_sentence_spans(text: str) -> list[tuple[int, int]]:
    """정규식 폴백 — 종결 부호(`. ! ? …`) 뒤 공백/끝, 또는 개행을 경계로 삼는다."""
    spans: list[tuple[int, int]] = []
    start = 0
    for match in _SENTENCE_BOUNDARY_RE.finditer(text):
        end = match.end()
        if end <= start:
            continue
        if text[start:end].strip():
            spans.append((start, end))
        start = end
    if start < len(text) and text[start:].strip():
        spans.append((start, len(text)))
    return spans or [(0, len(text))]


def _split_sentences(text: str) -> list[tuple[int, int]]:
    """kss(설치돼 있으면) 우선, 실패·미설치면 정규식 폴백(04-pipelines/10 §2.5 D1)."""
    if not text:
        return [(0, 0)]
    try:
        import kss  # type: ignore[import-not-found] # noqa: PLC0415 - 선택 의존성, 지연 임포트

        sentences = kss.split_sentences(text)
    except Exception:  # noqa: BLE001 - 선택 의존성 부재/실행 실패는 모두 정규식 폴백
        return _regex_sentence_spans(text)
    spans: list[tuple[int, int]] = []
    cursor = 0
    for sentence in sentences:
        idx = text.find(sentence, cursor)
        if idx == -1:
            return _regex_sentence_spans(text)
        spans.append((idx, idx + len(sentence)))
        cursor = idx + len(sentence)
    return spans or [(0, len(text))]


def _char_window_split(text: str, max_tokens: int, counter: TokenCounter) -> list[tuple[int, int]]:
    """최종 폴백 — 예산을 넘지 않는 최대 창을 코드포인트 단위로 그리디하게 늘린다."""
    spans: list[tuple[int, int]] = []
    n = len(text)
    start = 0
    while start < n:
        end = start + 1
        while end < n and counter.count(text[start : end + 1]) <= max_tokens:
            end += 1
        spans.append((start, end))
        start = end
    return spans or [(0, n)]


def _hard_split(text: str, max_tokens: int, counter: TokenCounter) -> list[tuple[int, int]]:
    """D3 대체 — semchunk 미배선(ADR-0020 잠금 전, DEFERRED) 상태의 공백 경계 그리디 폴백."""
    if not text:
        return [(0, 0)]
    if counter.count(text) <= max_tokens:
        return [(0, len(text))]
    words = list(_WORD_RE.finditer(text))
    if not words:
        return _char_window_split(text, max_tokens, counter)
    spans: list[tuple[int, int]] = []
    seg_start = 0
    seg_end = 0
    for word in words:
        candidate_end = word.end()
        if seg_end > seg_start and counter.count(text[seg_start:candidate_end]) > max_tokens:
            spans.append((seg_start, seg_end))
            seg_start = seg_end
        seg_end = candidate_end
    if seg_start < len(text):
        remainder = text[seg_start:]
        if counter.count(remainder) > max_tokens:
            spans.extend((seg_start + s, seg_start + e) for s, e in _char_window_split(remainder, max_tokens, counter))
        else:
            spans.append((seg_start, len(text)))
    return spans or [(0, len(text))]


def _greedy_group(
    pieces: Sequence[tuple[int, int]], text: str, max_tokens: int, counter: TokenCounter
) -> list[tuple[int, int]]:
    """D1 그리디 누적 — 문장 경계를 순서대로 합쳐 `max_tokens`를 넘지 않는 최대 묶음을 만든다."""
    groups: list[tuple[int, int]] = []
    group_start: int | None = None
    group_end: int | None = None
    for start, end in pieces:
        if counter.count(text[start:end]) > max_tokens:
            if group_start is not None:
                groups.append((group_start, group_end))  # type: ignore[arg-type]
                group_start = None
            groups.extend((start + s, start + e) for s, e in _hard_split(text[start:end], max_tokens, counter))
            continue
        if group_start is None:
            group_start, group_end = start, end
            continue
        if counter.count(text[group_start:end]) <= max_tokens:
            group_end = end
        else:
            groups.append((group_start, group_end))  # type: ignore[arg-type]
            group_start, group_end = start, end
    if group_start is not None:
        groups.append((group_start, group_end))  # type: ignore[arg-type]
    return groups


# ----------------------------------------------------------------------------
# 원문 좌표 사상 (offset_map: [disp, orig, len] 삼중항, 04-pipelines/09 §4 정본)
# ----------------------------------------------------------------------------


def _unwrap(value: Any) -> Any:
    """중첩 `RootModel`(`OffsetMapItem`/`OffsetMapItemItem`)을 평범한 값으로 벗긴다."""
    return value.root if hasattr(value, "root") else value


def _to_original(offset_map: Sequence[Any], pos: int) -> int:
    """`display` 좌표 `pos`를 `offset_map`으로 원문(`Block.text`) 좌표로 사상한다."""
    best: tuple[int, int, int] | None = None
    for item in offset_map:
        raw = _unwrap(item)
        disp, orig, length = (int(_unwrap(x)) for x in raw)
        if disp <= pos:
            best = (disp, orig, length)
        else:
            break
    if best is None:
        return pos
    disp, orig, length = best
    if length == 0:
        return orig
    return orig + min(pos - disp, length)


# ----------------------------------------------------------------------------
# heading_path 유도 (04-pipelines/10 §2.3 식; 03-contracts/05 §9 정본 인용)
# ----------------------------------------------------------------------------


def _assign_heading_paths(
    blocks: Sequence[ct.NormalizedBlock], heading_tree: Sequence[HeadingNode]
) -> dict[str, tuple[str, ...]]:
    """각 블록에 "가장 안쪽 선행 heading"의 경로를 부여한다(제목 `path[0]`은 한 번만 제거)."""
    order = {block.block_id.root: i for i, block in enumerate(blocks)}
    headings_sorted = sorted(heading_tree, key=lambda node: order.get(node.block_id.root, 0))
    title_path0: str | None = None
    for node in headings_sorted:
        if node.level == 0:
            title_path0 = node.path[0]
            break
    paths: dict[str, tuple[str, ...]] = {}
    ptr = 0
    current_path: tuple[str, ...] = ()
    for i, block in enumerate(blocks):
        while ptr < len(headings_sorted) and order.get(headings_sorted[ptr].block_id.root, 0) <= i:
            node = headings_sorted[ptr]
            path = list(node.path)
            if title_path0 is not None and path and path[0] == title_path0:
                path = path[1:]
            current_path = tuple(path)
            ptr += 1
        paths[block.block_id.root] = current_path
    return paths


def _resolve_title(doc: NormalizedDocument) -> str:
    """`context_prefix.deterministic`의 `title` — 문서 제목(level 0) heading, 없으면 결정적 자리표시자.

    `ParsedDocument.metadata.title`/`SourceDocument.source_uri`(04-pipelines/10 §2.8 2·3차 폴백)는
    이 WP의 `ctx.lineage` 범위 밖이라 DEFERRED다.
    """
    for node in doc.heading_tree:
        if node.level == 0:
            return node.path[0]
    if doc.heading_tree:
        return doc.heading_tree[0].path[0]
    return f"document:{doc.document_id.root}"


def _build_context_prefix(
    title: str, heading_path: tuple[str, ...], counter: TokenCounter, prefix_max_tokens: int
) -> str:
    """title과 heading_path를 U+203A로 조인한다. `prefix_max_tokens` 초과 시 얕은 단계 제거 후 title 절단."""

    def render(current_title: str, path: list[str]) -> str:
        if not path:
            return current_title
        return f"{current_title}{_CONTEXT_PREFIX_SEP}{_CONTEXT_PREFIX_SEP.join(path)}"

    path = list(heading_path)
    prefix = render(title, path)
    while counter.count(prefix) > prefix_max_tokens and path:
        path.pop(0)
        prefix = render(title, path)
    while counter.count(prefix) > prefix_max_tokens and len(title) > 1:
        title = title[: max(1, len(title) - 10)]
        prefix = render(title, path)
    return prefix


# ----------------------------------------------------------------------------
# 리프 후보 표현과 병합/부모 집계 (block_refs·sentence_spans 오프셋을 로컬 좌표로 들고 다닌다)
# ----------------------------------------------------------------------------


@dataclass(frozen=True)
class _RefPiece:
    block_id: str
    element_path: str
    char_start: int
    char_end: int
    original_char_start: int
    original_char_end: int
    page: int | None = None
    bbox: list[float] | None = None
    section_index: int | None = None


@dataclass
class _Leaf:
    heading_path: tuple[str, ...]
    lang_counts: dict[str, int]
    text_source: ct.BlockSource
    confidence: float | None
    text: str
    lexical_text: str
    block_refs: list[_RefPiece]
    sentence_spans: list[tuple[int, int]]


def _dominant_lang(leaf: _Leaf) -> str:
    """포함 블록 `lang` 중 코드포인트 수 최다(04-pipelines/10 §2.8)."""
    if not leaf.lang_counts:
        return "und"
    return max(leaf.lang_counts.items(), key=lambda kv: (kv[1], kv[0]))[0]


def _concat(members: Sequence[_Leaf]) -> _Leaf:
    """여러 리프를 U+000A로 이어붙이며 `block_refs`/`sentence_spans` 오프셋을 누적 이동한다(E·F 공용)."""
    text_parts: list[str] = []
    lexical_parts: list[str] = []
    block_refs: list[_RefPiece] = []
    sentence_spans: list[tuple[int, int]] = []
    lang_counts: dict[str, int] = {}
    confidence_values: list[float] = []
    text_source = members[0].text_source
    offset = 0
    for member in members:
        text_parts.append(member.text)
        lexical_parts.append(member.lexical_text)
        block_refs.extend(
            replace(ref, char_start=ref.char_start + offset, char_end=ref.char_end + offset)
            for ref in member.block_refs
        )
        sentence_spans.extend((s + offset, e + offset) for s, e in member.sentence_spans)
        for lang, count in member.lang_counts.items():
            lang_counts[lang] = lang_counts.get(lang, 0) + count
        if member.confidence is not None:
            confidence_values.append(member.confidence)
        if _SOURCE_RANK[member.text_source] > _SOURCE_RANK[text_source]:
            text_source = member.text_source
        offset += len(member.text) + 1  # +1: 다음 조각과 이어붙일 U+000A
    return _Leaf(
        heading_path=members[0].heading_path,
        lang_counts=lang_counts,
        text_source=text_source,
        confidence=min(confidence_values) if confidence_values else None,
        text="\n".join(text_parts),
        lexical_text="\n".join(lexical_parts),
        block_refs=block_refs,
        sentence_spans=sentence_spans,
    )


def _leaf_from_block(block: ct.NormalizedBlock, idx: int, start: int, end: int, heading_path: tuple[str, ...]) -> _Leaf:
    """블록(또는 초과 분할 조각) 하나를 `_Leaf`로 만든다 — `offset_map`으로 원문 좌표를 사상한다."""
    text = block.display_text[start:end]
    lexical_text = block.lexical_text[start:end]
    ref = _RefPiece(
        block_id=block.block_id.root,
        element_path=f"/blocks/{idx}",  # DEFERRED: Block.provenance.element_path 필요(WP-201 open_issue)
        char_start=0,
        char_end=len(text),
        original_char_start=_to_original(block.offset_map, start),
        original_char_end=_to_original(block.offset_map, end),
    )
    return _Leaf(
        heading_path=heading_path,
        lang_counts={block.lang.root: len(text)},
        text_source=block.text_source,
        confidence=block.confidence,
        text=text,
        lexical_text=lexical_text,
        block_refs=[ref],
        sentence_spans=_split_sentences(text),
    )


def _merge_peers(
    leaves: Sequence[_Leaf], merge_min_tokens: int, leaf_max_tokens: int, counter: TokenCounter
) -> list[_Leaf]:
    """단계 E — 같은 `heading_path`·우세 언어인 인접 리프를 `merge_min_tokens` 트리거로 합친다."""
    if not leaves:
        return []
    out: list[_Leaf] = []
    window: list[_Leaf] = [leaves[0]]
    for nxt in leaves[1:]:
        head = window[-1]
        mergeable = head.heading_path == nxt.heading_path and _dominant_lang(head) == _dominant_lang(nxt)
        if mergeable:
            window_tokens = counter.count("\n".join(m.text for m in window))
            next_tokens = counter.count(nxt.text)
            joined_tokens = counter.count("\n".join(m.text for m in (*window, nxt)))
            below_trigger = window_tokens < merge_min_tokens or next_tokens < merge_min_tokens
            if below_trigger and joined_tokens <= leaf_max_tokens:
                window.append(nxt)
                continue
        out.append(_concat(window))
        window = [nxt]
    out.append(_concat(window))

    if len(out) >= _MIN_PARENT_CHILDREN:
        prev, last = out[-2], out[-1]
        if (
            prev.heading_path == last.heading_path
            and _dominant_lang(prev) == _dominant_lang(last)
            and counter.count(last.text) < merge_min_tokens
            and counter.count(prev.text + "\n" + last.text) <= leaf_max_tokens
        ):
            out[-2:] = [_concat([prev, last])]
    return out


def _build_parent_groups(leaves: Sequence[_Leaf], parent_max_tokens: int, counter: TokenCounter) -> list[list[int]]:
    """단계 F — 같은 `heading_path`의 연속 리프를 `parent_max_tokens` 예산으로 묶는다(자식 ≥ 2만)."""
    groups: list[list[int]] = []
    run: list[int] = []
    run_path: tuple[str, ...] | None = None

    def flush() -> None:
        if run:
            groups.append(list(run))
        run.clear()

    for i, leaf in enumerate(leaves):
        if run_path is not None and leaf.heading_path == run_path:
            candidate = counter.count("\n".join(leaves[j].text for j in (*run, i)))
            if candidate <= parent_max_tokens:
                run.append(i)
                continue
        flush()
        run.append(i)
        run_path = leaf.heading_path
    flush()
    return [group for group in groups if len(group) >= _MIN_PARENT_CHILDREN]


# ----------------------------------------------------------------------------
# 좌표·ID·접두어 (단계 G)
# ----------------------------------------------------------------------------


def _span_and_chunk_id(
    refs: Sequence[_RefPiece], level: int, doc_version: str, chunker_config_hash: str
) -> tuple[str, str]:
    ordered = sorted(refs, key=lambda r: r.char_start)
    first, last = ordered[0], ordered[-1]
    span = f"{first.block_id}:{first.original_char_start}-{last.block_id}:{last.original_char_end}"
    return span, compute_chunk_id(doc_version, chunker_config_hash, level, span)


def _finalize_chunk(
    leaf: _Leaf,
    *,
    level: int,
    ordinal: int,
    parent_chunk_id: str | None,
    child_chunk_ids: list[str] | None,
    span: str,
    chunk_id: str,
    primary_counter: TokenCounter,
    secondary_counters: Sequence[TokenCounter],
    title: str,
    prefix_max_tokens: int,
) -> ct.Chunk:
    """단계 G — 한 `_Leaf`를 계약 `Chunk`로 조립한다(`span`·`chunk_id`는 사전 계산해 받는다)."""
    block_refs = [
        ct.BlockRef(
            block_id=ref.block_id,
            element_path=ref.element_path,
            char_start=ref.char_start,
            char_end=ref.char_end,
            original_char_start=ref.original_char_start,
            original_char_end=ref.original_char_end,
            page=ref.page,
            bbox=ref.bbox,
            section_index=ref.section_index,
        )
        for ref in sorted(leaf.block_refs, key=lambda r: r.char_start)
    ]
    sentence_spans = leaf.sentence_spans or [(0, len(leaf.text))]
    token_counts: dict[str, int] = {primary_counter.tokenizer_id: primary_counter.count(leaf.text)}
    for counter in secondary_counters:
        token_counts[counter.tokenizer_id] = counter.count(leaf.text)
    return ct.Chunk(
        chunk_id=chunk_id,
        span=span,
        item_kind=ct.ItemKind.text if level == 0 else ct.ItemKind.parent,
        level=ct.ChunkLevel(level),
        parent_chunk_id=parent_chunk_id,  # type: ignore[arg-type]
        child_chunk_ids=child_chunk_ids,  # type: ignore[arg-type]
        ordinal=ordinal,
        text=leaf.text,
        lexical_text=leaf.lexical_text,
        heading_path=list(leaf.heading_path),
        numbering_path=None,
        block_refs=block_refs,
        sentence_spans=[[s, e] for s, e in sentence_spans],  # type: ignore[misc]
        token_counts=token_counts,  # type: ignore[arg-type]
        lang=_dominant_lang(leaf),
        table_ref=None,
        window=None,
        context_prefix=ct.ContextPrefix(
            deterministic=_build_context_prefix(title, leaf.heading_path, primary_counter, prefix_max_tokens),
            generated=None,
            generated_by=None,
        ),
        tree_level=None,
        page_image_ref=None,
        text_source=leaf.text_source,
        ocr_confidence_min=leaf.confidence,
        content_hash=blake3_hex(leaf.text),
    )


# ----------------------------------------------------------------------------
# config_schema / Stage
# ----------------------------------------------------------------------------


class StructureAwareChunkerConfig(BaseModel):
    """`chunker.structure_aware`의 설정 스키마(04-pipelines/10 §1.4 축소 범위) — `chunker_config_hash` 입력."""

    model_config = ConfigDict(extra="forbid")

    tokenizer: str = DEFAULT_TOKENIZER
    secondary_tokenizers: list[str] = Field(default_factory=lambda: list(DEFAULT_SECONDARY_TOKENIZERS))
    leaf_max_tokens: int = 512
    parent_max_tokens: int = 2048
    merge_min_tokens: int = 64
    prefix_max_tokens: int = 100


def _resolve_normalized_ref(ctx: Any, plugin_id: str) -> NormalizedRef:
    """`ctx.normalized_ref`(이 스테이지 입력 `NormalizedDocument`의 산출물 참조)를 읽는다.

    `StageContext`에는 아직 이 멤버가 없다(WP-106 `_resolve_parsed_ref`와 같은 공백, open_issue) —
    포트 부재를 `contract.violation`으로 올린다.
    """
    ref = getattr(ctx, "normalized_ref", None)
    if ref is None:
        code = "contract.violation"
        detail = (
            "StageContext has no normalized_ref port (same design gap as WP-106's ctx.parsed_ref "
            "precedent: no ctx convention yet for a stage's own input ArtifactRef)"
        )
        raise StageError(code, stage="chunk", plugin_id=plugin_id, detail=detail)
    if isinstance(ref, NormalizedRef):
        return ref
    if hasattr(ref, "model_dump"):
        return NormalizedRef.model_validate(ref.model_dump(mode="json"))
    return NormalizedRef.model_validate(ref)


def _rfc3339_ms(moment: datetime) -> str:
    utc = moment.astimezone(UTC)
    return utc.strftime("%Y-%m-%dT%H:%M:%S.") + f"{utc.microsecond // 1000:03d}Z"


class StructureAwareChunkerStage:
    """`chunker.structure_aware` — 플랫폼 소유 기본 청커(ADR-0020)의 축소 범위(F2-01) 구현."""

    plugin_id = "chunker.structure_aware"
    config_schema = StructureAwareChunkerConfig
    requires_lineage: tuple[str, ...] = ()

    def __init__(self, config: StructureAwareChunkerConfig | None = None) -> None:
        """설정을 고정한다(설정은 `chunker_config_hash` → `fingerprint` → `stage_key` 입력)."""
        self.config = config or StructureAwareChunkerConfig()

    def config_hash(self) -> str:
        """`chunker_config_hash = H("config", canonical_json(config))`(바이블 §6.2)."""
        canonical = json.dumps(
            self.config.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), ensure_ascii=False
        )
        return hash_of("config", canonical)

    def capabilities(self) -> ct.Capabilities:
        """`isolation_modes=[in_process]`, 재개 미지원, GPU 불필요(순수 함수 스테이지)."""
        return ct.Capabilities(
            isolation_modes=[ct.IsolationMode.in_process],
            supports_resumable=False,
            contracts_compat=ct.ContractsCompat(">=1.0,<2.0"),
            input_formats=[],
            requires_gpu=False,
        )

    def fingerprint(self) -> str:
        """`H("producer", plugin_id, plugin_version, config_hash, "", "tokenizer:{primary}")`(ADR-0019)."""
        model_ids = f"tokenizer:{self.config.tokenizer}"
        return hash_of("producer", self.plugin_id, PLUGIN_VERSION, self.config_hash(), "", model_ids)

    async def run(self, inp: NormalizedDocument, ctx: Any) -> ChunkSet:
        """`NormalizedDocument` → `ChunkSet`(단계 A~G 축소 범위; 표·genre_rules 등은 WP-201 DEFERRED)."""
        normalized_ref = _resolve_normalized_ref(ctx, self.plugin_id)
        primary_counter: TokenCounter = getattr(ctx, "token_counter", None) or default_token_counter(
            self.config.tokenizer
        )
        secondary_counters = [default_token_counter(tid) for tid in self.config.secondary_tokenizers]

        heading_ids = {node.block_id.root for node in inp.heading_tree}
        paths = _assign_heading_paths(inp.blocks, inp.heading_tree)

        warnings: list[ct.Warning] = []
        oversized = 0
        leaves: list[_Leaf] = []
        for idx, block in enumerate(inp.blocks):
            block_id = block.block_id.root
            if block.boilerplate or block_id in heading_ids:
                continue
            text = block.display_text
            if not text.strip():
                continue
            path = paths.get(block_id, ())
            if primary_counter.count(text) <= self.config.leaf_max_tokens:
                leaves.append(_leaf_from_block(block, idx, 0, len(text), path))
                continue
            pieces = _split_sentences(text)
            for start, end in _greedy_group(pieces, text, self.config.leaf_max_tokens, primary_counter):
                leaves.append(_leaf_from_block(block, idx, start, end, path))
            warnings.append(
                ct.Warning(
                    code=ct.ErrorCodeCatalog.chunk_block_oversized,
                    message="block exceeds leaf_max_tokens; split at sentence/regex boundaries",
                    block_id=block.block_id,
                )
            )
            oversized += 1

        merged = _merge_peers(leaves, self.config.merge_min_tokens, self.config.leaf_max_tokens, primary_counter)

        chunker_config_hash = self.config_hash()
        doc_version = inp.doc_version.root
        title = _resolve_title(inp)

        leaf_span_ids = [_span_and_chunk_id(leaf.block_refs, 0, doc_version, chunker_config_hash) for leaf in merged]
        parent_groups = _build_parent_groups(merged, self.config.parent_max_tokens, primary_counter)
        parent_aggregates = [_concat([merged[i] for i in group]) for group in parent_groups]
        parent_span_ids = [
            _span_and_chunk_id(agg.block_refs, 1, doc_version, chunker_config_hash) for agg in parent_aggregates
        ]
        grouped_index: dict[int, int] = {i: gi for gi, group in enumerate(parent_groups) for i in group}

        leaf_chunks: list[ct.Chunk] = []
        no_parent_ordinal = 0
        for i, leaf in enumerate(merged):
            span, cid = leaf_span_ids[i]
            group_id = grouped_index.get(i)
            if group_id is None:
                parent_chunk_id = None
                ordinal = no_parent_ordinal
                no_parent_ordinal += 1
            else:
                parent_chunk_id = parent_span_ids[group_id][1]
                ordinal = parent_groups[group_id].index(i)
            leaf_chunks.append(
                _finalize_chunk(
                    leaf,
                    level=0,
                    ordinal=ordinal,
                    parent_chunk_id=parent_chunk_id,
                    child_chunk_ids=None,
                    span=span,
                    chunk_id=cid,
                    primary_counter=primary_counter,
                    secondary_counters=secondary_counters,
                    title=title,
                    prefix_max_tokens=self.config.prefix_max_tokens,
                )
            )

        parent_chunks: list[ct.Chunk] = []
        for gi, (agg, group) in enumerate(zip(parent_aggregates, parent_groups, strict=True)):
            span, cid = parent_span_ids[gi]
            parent_chunks.append(
                _finalize_chunk(
                    agg,
                    level=1,
                    ordinal=gi,
                    parent_chunk_id=None,
                    child_chunk_ids=[leaf_span_ids[i][1] for i in group],
                    span=span,
                    chunk_id=cid,
                    primary_counter=primary_counter,
                    secondary_counters=secondary_counters,
                    title=title,
                    prefix_max_tokens=self.config.prefix_max_tokens,
                )
            )

        quality = ct.Quality.degraded if inp.quality == ct.Quality.degraded or warnings else ct.Quality.full
        normalized_artifact_ref = ct.ArtifactRef(
            uri=normalized_ref.uri,
            blake3=normalized_ref.blake3,
            media_type=normalized_ref.media_type,
            schema_type=ct.SchemaTypeName(normalized_ref.schema_type),
            schema_version=normalized_ref.schema_version,
            size_bytes=normalized_ref.size_bytes,
            stage_key=normalized_ref.stage_key,
        )

        return ChunkSet(
            schema_version="1.0.0",
            schema_type="ChunkSet",
            tenant_id=inp.tenant_id,
            collection_id=inp.collection_id,
            producer=ct.Producer(
                plugin_id=self.plugin_id,
                plugin_version=PLUGIN_VERSION,
                config_hash=chunker_config_hash,
                image_digest=None,
                model_ids=None,
            ),
            quality=quality,
            warnings=warnings,
            created_at=_rfc3339_ms(ctx.now()),
            lineage_refs=ChunkSetLineageRefs(
                source=inp.lineage_refs.source,
                parsed=inp.lineage_refs.parsed,
                normalized=normalized_artifact_ref,
                chunk_set=None,
                enriched=None,
                embedded=None,
            ),
            chunk_set_id=str(ULID()),
            document_id=inp.document_id,
            doc_version=inp.doc_version,
            normalized_ref=normalized_ref,
            document_hash=normalized_ref.blake3,
            chunker_id="chunker.structure_aware",
            chunker_config_hash=chunker_config_hash,
            primary_tokenizer_id=primary_counter.tokenizer_id,
            secondary_tokenizer_ids=[counter.tokenizer_id for counter in secondary_counters],  # type: ignore[misc]
            genre_route=inp.genre,
            analyzer_id=inp.analyzer_id,
            dictionary_hash=inp.dictionary_hash,
            language=inp.language,
            pii_policy_applied=inp.pii_report.policy_applied,
            stats=ChunkSetStats(
                leaf_count=len(leaf_chunks),
                parent_count=len(parent_chunks),
                table_part_count=0,
                summary_count=0,
                oversized_blocks=oversized,
            ),
            token_budgets=TokenBudgets(
                leaf_max_tokens=self.config.leaf_max_tokens,
                parent_max_tokens=self.config.parent_max_tokens,
                merge_min_tokens=self.config.merge_min_tokens,
                table_row_group_tokens=_DEFAULT_TABLE_ROW_GROUP_TOKENS,
                fallback_max_tokens=None,
                fallback_overlap_ratio=None,
                sentence_window_n=None,
            ),
            chunks=[*leaf_chunks, *parent_chunks],
        )
