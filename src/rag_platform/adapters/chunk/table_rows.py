"""표 청킹 순수 함수 모듈 — `TableData` 하나를 `Chunk` 목록(리프·부모)으로 그룹화·직렬화한다(F2-02).

역할: `structure_aware` 청커(별도 WP, 미구현)가 표 블록마다 호출하는 헬퍼. 작은 표는 단일 리프
(`item_kind=table`), 큰 표는 헤더 반복 `table_part` 리프 N개 + 전체 표를 나르는 `parent`(level 1) 1개를
만든다. 셀 텍스트 소스 선택(`NormalizedDocument.table_cell_views` vs `TableData.cells[].text`)과
중첩 표 재귀 호출은 호출자 책임이다(`cell_texts` 오버레이로 주입).
설계 근거: 04-pipelines/10-chunking-strategies.md §4(판정 흐름·규칙·직렬화 옵션), 바이블 §5.4
`Chunk`/`TableRef`/`TableData`/`TableCell`, §3.2 O-09(예산 256/2048/512), ADR-0004(`chunk_id`),
ADR-0020(기본 청커); 계약 `contracts/chunk_set.py`, `contracts/common_types`.
구성: `TableChunkContext` — 표 하나의 모든 조각이 공유하는 메타데이터; `TableChunkResult` — 산출
`chunks`/`warnings`/실 적용 예산; `build_table_chunks()` — 진입점(판정→그룹화→직렬화→조립); 직렬화
헬퍼 4종(`render_markdown`/`render_triplet`/`render_row_json`/`render_html`).
불변식·주의: 순수 함수(시간·난수·IO 없음, `ctx.now()` 미사용). `chunk_id`/`content_hash`는
`sdk.hashing`만 사용(직접 `blake3` import 금지). 그룹화 예산 판정은 04 §4.2 규칙대로 항상 markdown
직렬화 기준(저장되는 `text`의 `text_format`과 무관). `span`/`char_*`는 표 전체의 정본(header 1회)
markdown 렌더 안에서의 데이터 행 줄 오프셋이라 그룹마다 유일하다(원문 `NormalizedBlock.offset_map`
사상은 DEFERRED, WP-202 참조).
검증 계층: 1층(여기서 검증) — tests/adapters/chunk/test_table_rows.py. `needs_docker`/`needs_model`/
`needs_gpu`/`needs_network` 해당 없음.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from rag_platform.contracts import common_types as ct
from rag_platform.contracts.common_types.TableCell import HeaderKind
from rag_platform.sdk.hashing import blake3_hex, chunk_id as compute_chunk_id
from rag_platform.sdk.stage import StageError

if TYPE_CHECKING:
    from rag_platform.sdk.ports import TokenCounter

__all__ = [
    "TableChunkContext",
    "TableChunkResult",
    "build_table_chunks",
    "render_html",
    "render_markdown",
    "render_row_json",
    "render_triplet",
]

#: 04-pipelines/10 §7 파라미터 기본값(O-09).
_DEFAULT_TABLE_ROW_GROUP_TOKENS = 256
_DEFAULT_PARENT_MAX_TOKENS = 2048
_DEFAULT_LEAF_MAX_TOKENS = 512
_COLUMN_LABEL_FMT = "열{n}"
_ROW_COL_JOIN = " · "


@dataclass(frozen=True)
class TableChunkContext:
    """표 하나의 모든 조각·부모 청크가 공유하는 메타데이터(호출자가 이미 해석해 넘긴다).

    `context_prefix`는 `caption_of=table_block_id` 캡션·`heading_path`를 04-pipelines/10 §4.2 "표
    캡션" 규칙대로 조립한 값을 호출자가 미리 만들어 전달한다(이 모듈은 재조립하지 않는다).
    """

    table_block_id: str
    doc_version: str
    chunker_config_hash: str
    heading_path: tuple[str, ...]
    lang: str
    text_source: ct.BlockSource
    ocr_confidence_min: float | None
    context_prefix: ct.ContextPrefix
    element_path: str
    page: int | None = None
    bbox: tuple[float, float, float, float] | None = None


@dataclass(frozen=True)
class TableChunkResult:
    """`build_table_chunks()`의 반환값."""

    chunks: list[ct.Chunk]
    warnings: list[ct.Warning]
    applied_table_row_group_tokens: int


def _escape_markdown_cell(text: str) -> str:
    r"""`|`는 `\|`로 이스케이프하고 개행은 공백으로 접는다(04 §4.3)."""
    return text.replace("|", "\\|").replace("\r\n", " ").replace("\n", " ").replace("\r", " ")


def _join_lines_with_ranges(lines: Sequence[str]) -> tuple[str, list[tuple[int, int]]]:
    """`lines`를 U+000A로 이어 붙이고, 각 줄의 `(start, end)` 문자 오프셋을 함께 반환한다."""
    ranges: list[tuple[int, int]] = []
    offset = 0
    for line in lines:
        start = offset
        end = start + len(line)
        ranges.append((start, end))
        offset = end + 1
    return "\n".join(lines), ranges


def render_markdown(
    header_cells: Sequence[str] | None, data_rows: Sequence[Sequence[str]], n_cols: int
) -> tuple[str, list[tuple[int, int]]]:
    """GFM 표(헤더 행 + `| --- |` 구분선 + 데이터 행). 헤더 없으면 빈 칸(04 §4.2 "헤더 없는 표").

    Returns:
        `(text, content_line_ranges)` — `content_line_ranges`는 구분선을 제외한 헤더·데이터 줄의
        `text` 내 문자 오프셋(`Chunk.sentence_spans` 원천, 04 §4.3).
    """
    header = list(header_cells) if header_cells is not None else [""] * n_cols
    header_line = "| " + " | ".join(_escape_markdown_cell(c) for c in header) + " |"
    separator_line = "| " + " | ".join(["---"] * n_cols) + " |"
    data_lines = ["| " + " | ".join(_escape_markdown_cell(c) for c in row) + " |" for row in data_rows]
    text, ranges = _join_lines_with_ranges([header_line, separator_line, *data_lines])
    content_ranges = [ranges[0], *ranges[2:]]
    return text, content_ranges


def _default_headers(n_cols: int) -> list[str]:
    """헤더 행이 없을 때 쓰는 `"열{n}"` 자리표시자(04 §4.2 "헤더 없는 표")."""
    return [_COLUMN_LABEL_FMT.format(n=i + 1) for i in range(n_cols)]


def render_triplet(
    header_cells: Sequence[str] | None,
    data_rows: Sequence[Sequence[str]],
    n_cols: int,
    *,
    header_style: Literal["column", "row"] = "column",
) -> tuple[str, list[tuple[int, int]]]:
    """`lexical_text` 고정 직렬화(04 §4.3): 데이터 행마다 `"{열 헤더}: {셀}; ..."`.

    `header_style="row"`이면 각 행의 첫 칸을 행 헤더로 취급해 `"{행 헤더} · {열 헤더}: {셀}"`을 쓰고
    첫 칸 자신은 반복하지 않는다(04 §4.2 "행 헤더").
    """
    headers = list(header_cells) if header_cells is not None else _default_headers(n_cols)
    lines: list[str] = []
    for row in data_rows:
        if header_style == "row" and row:
            row_header = row[0]
            parts = [f"{row_header}{_ROW_COL_JOIN}{headers[j]}: {row[j]}" for j in range(1, len(row))]
        else:
            parts = [f"{headers[j]}: {row[j]}" for j in range(len(row))]
        lines.append("; ".join(parts))
    return _join_lines_with_ranges(lines)


def render_row_json(
    header_cells: Sequence[str] | None, data_rows: Sequence[Sequence[str]], n_cols: int
) -> tuple[str, list[tuple[int, int]]]:
    """옵션 직렬화(04 §4.3): 행마다 `{"열": "값"}` JSON 객체 1줄(폼·키-값 표)."""
    headers = list(header_cells) if header_cells is not None else _default_headers(n_cols)
    lines = [
        json.dumps({headers[j]: row[j] for j in range(len(row))}, ensure_ascii=False, sort_keys=False)
        for row in data_rows
    ]
    return _join_lines_with_ranges(lines)


def render_html(
    header_cells: Sequence[str] | None, data_rows: Sequence[Sequence[str]], n_cols: int
) -> tuple[str, list[tuple[int, int]]]:
    """옵션 직렬화(04 §4.3): `html_ref` 없이 HTML 자체를 `text`로 쓰고 싶을 때(무손실 1차는 아님)."""
    header = list(header_cells) if header_cells is not None else [""] * n_cols
    header_line = "<tr>" + "".join(f"<th>{c}</th>" for c in header) + "</tr>"
    data_lines = ["<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>" for row in data_rows]
    lines = ["<table>", header_line, *data_lines, "</table>"]
    text, ranges = _join_lines_with_ranges(lines)
    content_ranges = ranges[1:-1]
    return text, content_ranges


_RenderFn = Callable[[Sequence[str] | None, Sequence[Sequence[str]], int], tuple[str, list[tuple[int, int]]]]


def _render_text(
    fmt: ct.TableSerialization,
    header_cells: Sequence[str] | None,
    data_rows: Sequence[Sequence[str]],
    n_cols: int,
    *,
    header_style: Literal["column", "row"],
) -> tuple[str, list[tuple[int, int]]]:
    """`text_format`에 따라 4종 직렬화 중 하나로 렌더한다(`triplet`만 `header_style`을 쓴다)."""
    if fmt == ct.TableSerialization.triplet:
        return render_triplet(header_cells, data_rows, n_cols, header_style=header_style)
    renderers: dict[ct.TableSerialization, _RenderFn] = {
        ct.TableSerialization.markdown: render_markdown,
        ct.TableSerialization.row_json: render_row_json,
        ct.TableSerialization.html: render_html,
    }
    return renderers[fmt](header_cells, data_rows, n_cols)


def _combined_header(grid: Sequence[Sequence[str]], header_row_indices: Sequence[int], n_cols: int) -> list[str] | None:
    """헤더 행이 여러 개면 열마다 `" / "`로 합친다(단일 헤더 행이 일반 경우)."""
    if not header_row_indices:
        return None
    if len(header_row_indices) == 1:
        return list(grid[header_row_indices[0]])
    combined: list[str] = []
    for col in range(n_cols):
        parts = [grid[r][col] for r in header_row_indices if grid[r][col]]
        combined.append(" / ".join(parts))
    return combined


def _header_style(table: ct.TableData) -> Literal["column", "row"]:
    """어느 셀이라도 `header_kind=row`이면 행 헤더 표로 취급한다(04 §4.2 "행 헤더")."""
    if any(cell.header_kind == HeaderKind.row for cell in table.cells):
        return "row"
    return "column"


def _build_grid(
    table: ct.TableData, cell_texts: Mapping[tuple[int, int], tuple[str, str]] | None
) -> tuple[list[list[str]], list[list[str]]]:
    """앵커 셀 → `n_rows x n_cols` display/lexical 그리드(병합으로 덮이는 칸은 빈 문자열).

    `cell_texts`에 `(row, col)` 항목이 있으면 그 `(display, lexical)`을 쓰고(05 §7
    `table_cell_views` 경로), 없으면 `TableCell.text`를 두 값 모두에 쓴다(`policy_applied=keep`
    폴백 경로) — 소스 선택 자체는 호출자 책임(WP-202 open issue).
    """
    display = [["" for _ in range(table.n_cols)] for _ in range(table.n_rows)]
    lexical = [["" for _ in range(table.n_cols)] for _ in range(table.n_rows)]
    for cell in table.cells:
        override = cell_texts.get((cell.row, cell.col)) if cell_texts else None
        disp, lex = override if override is not None else (cell.text, cell.text)
        display[cell.row][cell.col] = disp
        lexical[cell.row][cell.col] = lex
    return display, lexical


def _cells_by_row(table: ct.TableData) -> dict[int, list[ct.TableCell]]:
    mapping: dict[int, list[ct.TableCell]] = {}
    for cell in table.cells:
        mapping.setdefault(cell.row, []).append(cell)
    return mapping


def _blocked_boundaries(
    data_row_indices: Sequence[int], cells_by_row: Mapping[int, Sequence[ct.TableCell]]
) -> list[bool]:
    """위치 `p`·`p+1` 사이 분할 가능 여부(04 §4.2 "병합 셀" — 경계가 `row_span`을 가르면 뒤로 민다)."""
    n = len(data_row_indices)
    can_split_after = [True] * max(n - 1, 0)
    for pos, row_idx in enumerate(data_row_indices):
        reach = max((cell.row_span - 1 for cell in cells_by_row.get(row_idx, ())), default=0)
        if reach:
            last_blocked = min(pos + reach, n - 1)
            for boundary in range(pos, last_blocked):
                can_split_after[boundary] = False
    return can_split_after


def _greedy_ranges(n: int, fits: Callable[[int, int], bool], can_split_after: Sequence[bool]) -> list[tuple[int, int]]:
    """`fits(start, end)`가 참인 동안, 또는 `can_split_after`가 분할을 막는 동안 그리디로 확장한다."""
    ranges: list[tuple[int, int]] = []
    start = 0
    while start < n:
        end = start + 1
        while end < n and (fits(start, end + 1) or not can_split_after[end - 1]):
            end += 1
        ranges.append((start, end))
        start = end
    return ranges


def _make_block_ref(ctx: TableChunkContext, char_start: int, char_end: int) -> ct.BlockRef:
    """표 블록 전체를 가리키는 근사 `BlockRef`(원문 좌표 사상은 DEFERRED, WP-202 참조)."""
    return ct.BlockRef(
        block_id=ctx.table_block_id,
        element_path=ctx.element_path,
        char_start=char_start,
        char_end=char_end,
        original_char_start=char_start,
        original_char_end=char_end,
        page=ctx.page,
        bbox=list(ctx.bbox) if ctx.bbox is not None else None,
    )


def _make_chunk(
    *,
    ctx: TableChunkContext,
    text: str,
    lexical_text: str,
    sentence_ranges: Sequence[tuple[int, int]],
    span_char_start: int,
    span_char_end: int,
    item_kind: ct.ItemKind,
    level: int,
    parent_chunk_id: str | ct.Hex64 | None,
    child_chunk_ids: Sequence[str | ct.Hex64] | None,
    ordinal: int,
    table_ref: ct.TableRef | None,
    token_counters: Sequence[TokenCounter],
) -> ct.Chunk:
    """`Chunk`(바이블 §5.4) 조립 — `chunk_id = H("chunk", doc_version, chunker_config_hash, level, span)`."""
    span = f"{ctx.table_block_id}:{span_char_start}-{ctx.table_block_id}:{span_char_end}"
    cid = compute_chunk_id(ctx.doc_version, ctx.chunker_config_hash, level, span)
    token_counts = {counter.tokenizer_id: counter.count(text) for counter in token_counters}
    return ct.Chunk(
        chunk_id=cid,
        span=span,
        item_kind=item_kind,
        level=level,  # type: ignore[arg-type]
        parent_chunk_id=parent_chunk_id,  # type: ignore[arg-type]
        child_chunk_ids=list(child_chunk_ids) if child_chunk_ids is not None else None,  # type: ignore[arg-type]
        ordinal=ordinal,
        text=text,
        lexical_text=lexical_text,
        heading_path=list(ctx.heading_path),
        block_refs=[_make_block_ref(ctx, span_char_start, span_char_end)],
        sentence_spans=[[start, end] for start, end in sentence_ranges],  # type: ignore[misc]
        token_counts=token_counts,  # type: ignore[arg-type]
        lang=ctx.lang,
        table_ref=table_ref,
        context_prefix=ctx.context_prefix,
        text_source=ctx.text_source,
        ocr_confidence_min=ctx.ocr_confidence_min,
        content_hash=blake3_hex(text),
    )


def build_table_chunks(  # noqa: PLR0915 - 표 그룹화·직렬화·조립은 지역 변수가 많은 하나의 절차(04 §4)
    table: ct.TableData,
    ctx: TableChunkContext,
    *,
    token_counters: Sequence[TokenCounter],
    cell_texts: Mapping[tuple[int, int], tuple[str, str]] | None = None,
    text_format: ct.TableSerialization = ct.TableSerialization.markdown,
    table_row_group_tokens: int = _DEFAULT_TABLE_ROW_GROUP_TOKENS,
    parent_max_tokens: int = _DEFAULT_PARENT_MAX_TOKENS,
    leaf_max_tokens: int = _DEFAULT_LEAF_MAX_TOKENS,
    section_parent_chunk_id: str | None = None,
    ordinal_offset: int = 0,
    max_parts: int | None = None,
) -> TableChunkResult:
    """표 하나를 판정→그룹화→직렬화→`Chunk` 조립(04-pipelines/10 §4).

    작은 표(그룹이 1개로 판정)는 `item_kind=table` 단일 리프(`parent_chunk_id=
    section_parent_chunk_id`)를, 큰 표(그룹 2개 이상)는 `table_part` 리프 N개 + 표 전체를 나르는
    `parent`(level 1, `child_chunk_ids`에 리프 전부) 1개를 만든다(04 §4.4 결정). 예산 판정은 항상
    markdown 직렬화 기준(04 §4.2)이며, `max_parts`를 넘으면 `table_row_group_tokens`를
    `leaf_max_tokens`까지 2배씩 늘려 재시도하고 그래도 넘으면 `chunk.count_exceeded`.

    Raises:
        ValueError: `token_counters`가 비었거나 표에 데이터 행이 없을 때(호출자 전처리 오류).
        StageError: `chunk.count_exceeded` — 예산을 최대로 늘려도 `max_parts`를 넘을 때.
    """
    if not token_counters:
        msg = "table_rows.build_table_chunks requires at least one TokenCounter (primary, O-09)"
        raise ValueError(msg)
    primary = token_counters[0]
    header_style = _header_style(table)
    display_grid, lexical_grid = _build_grid(table, cell_texts)
    header_row_indices = sorted(item.root for item in table.header_row_indices)
    header_set = set(header_row_indices)
    data_row_indices = [row for row in range(table.n_rows) if row not in header_set]
    if not data_row_indices:
        msg = f"table {ctx.table_block_id}: no data rows (all {table.n_rows} rows are header rows)"
        raise ValueError(msg)

    header_display = _combined_header(display_grid, header_row_indices, table.n_cols)
    header_lexical = _combined_header(lexical_grid, header_row_indices, table.n_cols)
    cells_by_row = _cells_by_row(table)
    can_split_after = _blocked_boundaries(data_row_indices, cells_by_row)

    applied_budget = table_row_group_tokens
    groups: list[tuple[int, int]] = []
    while True:

        def _fits(start: int, end: int, *, _budget: int = applied_budget) -> bool:
            rows = [display_grid[data_row_indices[i]] for i in range(start, end)]
            text, _ranges = render_markdown(header_display, rows, table.n_cols)
            return primary.count(text) <= _budget

        groups = _greedy_ranges(len(data_row_indices), _fits, can_split_after)
        if max_parts is None or len(groups) <= max_parts or applied_budget >= leaf_max_tokens:
            break
        applied_budget = min(applied_budget * 2, leaf_max_tokens)

    if max_parts is not None and len(groups) > max_parts:
        code = "chunk.count_exceeded"
        detail = (
            f"table {ctx.table_block_id}: {len(groups)} table_part groups exceed max_parts={max_parts} "
            f"even after escalating table_row_group_tokens to leaf_max_tokens={leaf_max_tokens} (04 §4.2)"
        )
        raise StageError(code, stage="chunk", detail=detail)

    # 정본(header 1회) 전체 렌더 — span 문자 오프셋 원천(그룹마다 유일, 04 §4.2 불변식 (1) 완화).
    canonical_data_rows = [display_grid[r] for r in data_row_indices]
    canonical_text, canonical_ranges = render_markdown(header_display, canonical_data_rows, table.n_cols)
    data_line_ranges = canonical_ranges[1:]  # index 0 = header line

    warnings: list[ct.Warning] = []

    def _oversized_check(chunk: ct.Chunk, markdown_text: str, budget: int) -> None:
        if primary.count(markdown_text) > budget:
            warnings.append(
                ct.Warning(
                    code=ct.ErrorCodeCatalog.chunk_block_oversized,
                    message="table row group exceeds table_row_group_tokens (merged-cell boundary "
                    "push or a single oversized row, 04 §4.2)",
                    block_id=ctx.table_block_id,  # type: ignore[arg-type]
                    chunk_id=chunk.chunk_id,
                )
            )

    if len(groups) == 1:
        start, end = groups[0]
        rows_display = [display_grid[data_row_indices[i]] for i in range(start, end)]
        rows_lexical = [lexical_grid[data_row_indices[i]] for i in range(start, end)]
        text, text_ranges = _render_text(
            text_format, header_display, rows_display, table.n_cols, header_style=header_style
        )
        lexical_text, _lex_ranges = render_triplet(
            header_lexical, rows_lexical, table.n_cols, header_style=header_style
        )
        char_start = data_line_ranges[start][0]
        char_end = data_line_ranges[end - 1][1]
        table_ref = ct.TableRef(
            table_block_id=ctx.table_block_id,
            header_row_indices=table.header_row_indices,
            row_range=[data_row_indices[start], data_row_indices[end - 1] + 1],  # type: ignore[list-item]
            col_range=[0, table.n_cols],  # type: ignore[list-item]
            serialization=text_format,
            html_ref=table.html_ref,
        )
        chunk = _make_chunk(
            ctx=ctx,
            text=text,
            lexical_text=lexical_text,
            sentence_ranges=text_ranges,
            span_char_start=char_start,
            span_char_end=char_end,
            item_kind=ct.ItemKind.table,
            level=0,
            parent_chunk_id=section_parent_chunk_id,
            child_chunk_ids=None,
            ordinal=ordinal_offset,
            table_ref=table_ref,
            token_counters=token_counters,
        )
        fit_text, _fit_ranges = render_markdown(header_display, rows_display, table.n_cols)
        _oversized_check(chunk, fit_text, applied_budget)
        return TableChunkResult(chunks=[chunk], warnings=warnings, applied_table_row_group_tokens=applied_budget)

    # 큰 표: 표 부모(level 1, 표 전체 직렬화) 먼저 조립 — chunk_id는 span(레벨 포함)만으로 결정되므로
    # 자식 chunk_id를 몰라도 먼저 계산할 수 있다(부모↔자식은 필드 배선만 순서 의존).
    parent_char_start = data_line_ranges[0][0]
    parent_char_end = data_line_ranges[-1][1]
    parent_text, parent_ranges = _render_text(
        text_format, header_display, canonical_data_rows, table.n_cols, header_style=header_style
    )
    parent_lexical, _parent_lex_ranges = render_triplet(
        header_lexical, [lexical_grid[r] for r in data_row_indices], table.n_cols, header_style=header_style
    )
    parent_span = f"{ctx.table_block_id}:{parent_char_start}-{ctx.table_block_id}:{parent_char_end}"
    parent_chunk_id = compute_chunk_id(ctx.doc_version, ctx.chunker_config_hash, 1, parent_span)

    child_chunks: list[ct.Chunk] = []
    for group_ordinal, (start, end) in enumerate(groups):
        rows_display = [display_grid[data_row_indices[i]] for i in range(start, end)]
        rows_lexical = [lexical_grid[data_row_indices[i]] for i in range(start, end)]
        text, text_ranges = _render_text(
            text_format, header_display, rows_display, table.n_cols, header_style=header_style
        )
        lexical_text, _lex_ranges = render_triplet(
            header_lexical, rows_lexical, table.n_cols, header_style=header_style
        )
        char_start = data_line_ranges[start][0]
        char_end = data_line_ranges[end - 1][1]
        table_ref = ct.TableRef(
            table_block_id=ctx.table_block_id,
            header_row_indices=table.header_row_indices,
            row_range=[data_row_indices[start], data_row_indices[end - 1] + 1],  # type: ignore[list-item]
            col_range=[0, table.n_cols],  # type: ignore[list-item]
            serialization=text_format,
            html_ref=table.html_ref,
        )
        chunk = _make_chunk(
            ctx=ctx,
            text=text,
            lexical_text=lexical_text,
            sentence_ranges=text_ranges,
            span_char_start=char_start,
            span_char_end=char_end,
            item_kind=ct.ItemKind.table_part,
            level=0,
            parent_chunk_id=parent_chunk_id,
            child_chunk_ids=None,
            ordinal=group_ordinal,
            table_ref=table_ref,
            token_counters=token_counters,
        )
        fit_text, _fit_ranges = render_markdown(header_display, rows_display, table.n_cols)
        _oversized_check(chunk, fit_text, applied_budget)
        child_chunks.append(chunk)

    parent_chunk = _make_chunk(
        ctx=ctx,
        text=parent_text,
        lexical_text=parent_lexical,
        sentence_ranges=parent_ranges,
        span_char_start=parent_char_start,
        span_char_end=parent_char_end,
        item_kind=ct.ItemKind.parent,
        level=1,
        parent_chunk_id=None,
        child_chunk_ids=[chunk.chunk_id for chunk in child_chunks],
        ordinal=ordinal_offset,
        table_ref=None,
        token_counters=token_counters,
    )
    _oversized_check(parent_chunk, canonical_text, parent_max_tokens)

    return TableChunkResult(
        chunks=[*child_chunks, parent_chunk], warnings=warnings, applied_table_row_group_tokens=applied_budget
    )
