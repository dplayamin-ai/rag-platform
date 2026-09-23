"""`adapters.chunk.table_rows`·`adapters.chunk.recount` 단위 테스트(F2-02, WP-202).

설계 근거: 무엇을 검증하는지는 (1) 직렬화 헬퍼(`render_markdown`/`render_triplet`) — 이스케이프,
헤더 없는 표의 `열{j}` 대체, 행 헤더 스타일; (2) `build_table_chunks`의 판정 흐름(04-pipelines/10 §4.1)
— 작은 표 단일 리프, 큰 표 `table_part` N개 + 표 부모(level 1); (3) 04 §4.2 규칙 — 병합 셀 경계 밀기
(`chunk.block_oversized` 경고), 단독 행 초과, 열 미분할(`col_range=[0, n_cols)`); (4) 세트 상한 근접
시 `table_row_group_tokens` 2배 escalation과 `chunk.count_exceeded`; (5) `chunk_id`/`content_hash`
결정성; (6) `RecountStage.run()` — 대상 tokenizer_id 추가, `secondary_tokenizer_ids` 누적,
`lineage_refs`/`chunk_set_id`/`chunks[].span` 불변, tokenizer 불일치 시 `chunk.tokenizer_missing`.
픽스처 출처: 이 파일이 직접 구성한 최소 `TableData`/`TableCell`(외부 샘플 불필요 — 계약 필드만으로
충분), 04-pipelines/10 §4.2 규칙표.
불변식·주의: 그룹화 예산 판정은 markdown 기준(04 §4.2)이라 단어수 기반 가짜 토크나이저로도 그리디
경계를 정확히 예측할 수 있다(토큰 수 = 10 + 5*행수, 아래 `_WordCounter` 참조).
검증 계층: 1층. tests/adapters/ 하위이므로 conftest.py가 `component` 마커를 붙인다.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime

import pytest

from rag_platform.adapters.chunk.recount import RecountConfig, RecountStage
from rag_platform.adapters.chunk.table_rows import (
    TableChunkContext,
    build_table_chunks,
    render_markdown,
    render_triplet,
)
from rag_platform.contracts import common_types as ct
from rag_platform.contracts.chunk_set import ChunkSet, ChunkSetStats, LineageRefs, NormalizedRef
from rag_platform.contracts.common_types.TableCell import HeaderKind
from rag_platform.sdk.stage import StageError

_HEX64 = "0" * 64
_ULID = "0" * 26
_TABLE_BLOCK_ID = "a" * 32


@dataclass
class _WordCounter:
    """`sdk.ports.TokenCounter` 더블 — 공백 분리 토큰 수(테스트 전용, 실 토크나이저 아님)."""

    tokenizer_id: str = "hf:BAAI/bge-m3"

    def count(self, text: str) -> int:
        return len(text.split())


@dataclass
class _StubCtx:
    """`RecountStage.run()`이 쓰는 두 멤버(`token_counter`, `now()`)만 채운 최소 컨텍스트 더블."""

    token_counter: _WordCounter
    _now: datetime = field(default_factory=lambda: datetime(2026, 6, 15, 12, 0, 0, tzinfo=UTC))

    def now(self) -> datetime:
        return self._now


def _cell(
    row: int,
    col: int,
    text: str,
    *,
    is_header: bool = False,
    header_kind: HeaderKind = HeaderKind.none,
    row_span: int = 1,
    col_span: int = 1,
) -> ct.TableCell:
    return ct.TableCell(
        row=row,
        col=col,
        row_span=row_span,
        col_span=col_span,
        text=text,
        is_header=is_header,
        header_kind=header_kind,
        provenance=None,
        nested_table_block_id=None,
    )


def _table_data(cells: list[ct.TableCell], *, n_rows: int, n_cols: int, header_row_indices: list[int]) -> ct.TableData:
    return ct.TableData(
        n_rows=n_rows,
        n_cols=n_cols,
        cells=cells,
        header_row_indices=header_row_indices,  # type: ignore[arg-type]
        header_inferred=False,
        role=ct.TableRole.data,
        quality=ct.Quality1(
            merged_cells_preserved=True, structure_source=ct.quality_1.StructureSource.native, structure_confidence=None
        ),
        html_ref=None,
    )


def _ctx(**overrides: object) -> TableChunkContext:
    defaults: dict[str, object] = {
        "table_block_id": _TABLE_BLOCK_ID,
        "doc_version": _HEX64,
        "chunker_config_hash": "1" * 64,
        "heading_path": ("1장",),
        "lang": "ko",
        "text_source": ct.BlockSource.text_layer,
        "ocr_confidence_min": None,
        "context_prefix": ct.ContextPrefix(
            deterministic="문서 › 1장",  # noqa: RUF001 - 바이블 §5.4 context_prefix 구분자 정본
            generated=None,
            generated_by=None,
        ),
        "element_path": "table[0]",
        "page": 1,
        "bbox": None,
    }
    defaults.update(overrides)
    return TableChunkContext(**defaults)  # type: ignore[arg-type]


def _small_table() -> ct.TableData:
    """헤더 1 + 데이터 2행, 2열 — 예산 안에 충분히 들어가는 표."""
    cells = [
        _cell(0, 0, "이름", is_header=True, header_kind=HeaderKind.column),
        _cell(0, 1, "나이", is_header=True, header_kind=HeaderKind.column),
        _cell(1, 0, "철수"),
        _cell(1, 1, "10"),
        _cell(2, 0, "영희"),
        _cell(2, 1, "20"),
    ]
    return _table_data(cells, n_rows=3, n_cols=2, header_row_indices=[0])


def _rows_table(n_data_rows: int, *, row_span_at: int | None = None) -> ct.TableData:
    """헤더 1 + `n_data_rows`행, 2열. `row_span_at`(데이터 행 0-based)가 주어지면 그 행이 다음 행까지
    `row_span=2`로 병합된다 — 앵커 셀 하나만 두고(병합 셀은 앵커 1개, `TableCell` 불변식) 다음 데이터
    행은 건너뛴다(그 칸은 그리드에서 빈 문자열로 남는다, `_build_grid`).
    """
    cells = [
        _cell(0, 0, "헤더1", is_header=True, header_kind=HeaderKind.column),
        _cell(0, 1, "헤더2", is_header=True, header_kind=HeaderKind.column),
    ]
    i = 0
    while i < n_data_rows:
        row = i + 1
        if row_span_at is not None and i == row_span_at and i + 1 < n_data_rows:
            cells.append(_cell(row, 0, f"행{i}", row_span=2))
            cells.append(_cell(row, 1, f"값{i}", row_span=2))
            i += 2
        else:
            cells.append(_cell(row, 0, f"행{i}"))
            cells.append(_cell(row, 1, f"값{i}"))
            i += 1
    return _table_data(cells, n_rows=n_data_rows + 1, n_cols=2, header_row_indices=[0])


# --------------------------------------------------------------------------------------------
# 직렬화 헬퍼
# --------------------------------------------------------------------------------------------


def test_render_markdown_escapes_pipe_and_newline() -> None:
    text, ranges = render_markdown(["열|A", "열B"], [["a\nb", "c"]], 2)
    assert "\\|" in text
    lines = text.split("\n")
    assert lines[0] == "| 열\\|A | 열B |"
    assert lines[1] == "| --- | --- |"
    assert lines[2] == "| a b | c |"
    assert len(ranges) == 2  # 헤더 줄 + 데이터 줄 1개(구분선 제외)
    assert text[ranges[0][0] : ranges[0][1]] == lines[0]
    assert text[ranges[1][0] : ranges[1][1]] == lines[2]


def test_render_markdown_blank_header_when_none() -> None:
    text, _ranges = render_markdown(None, [["x", "y"]], 2)
    assert text.split("\n")[0] == "|  |  |"


def test_render_triplet_no_header_uses_column_labels() -> None:
    text, ranges = render_triplet(None, [["a", "b"]], 2)
    assert text == "열1: a; 열2: b"
    assert len(ranges) == 1


def test_render_triplet_row_header_style_skips_first_cell() -> None:
    text, _ranges = render_triplet(["열A", "열B"], [["행헤더", "값"]], 2, header_style="row")
    assert text == "행헤더 · 열B: 값"


# --------------------------------------------------------------------------------------------
# build_table_chunks — 판정 흐름
# --------------------------------------------------------------------------------------------


def test_small_table_single_leaf() -> None:
    result = build_table_chunks(_small_table(), _ctx(), token_counters=[_WordCounter()])
    assert len(result.chunks) == 1
    assert result.warnings == []
    chunk = result.chunks[0]
    assert chunk.item_kind == ct.ItemKind.table
    assert chunk.level == 0
    assert chunk.parent_chunk_id is None
    assert chunk.child_chunk_ids is None
    assert [item.root for item in chunk.table_ref.row_range] == [1, 3]
    assert [item.root for item in chunk.table_ref.col_range] == [0, 2]
    assert chunk.table_ref.serialization == ct.TableSerialization.markdown
    assert "이름" in chunk.text
    assert "나이" in chunk.text
    assert chunk.token_counts.root["hf:BAAI/bge-m3"].root == _WordCounter().count(chunk.text)


def test_small_table_with_section_parent_id() -> None:
    result = build_table_chunks(
        _small_table(), _ctx(), token_counters=[_WordCounter()], section_parent_chunk_id="f" * 64, ordinal_offset=3
    )
    chunk = result.chunks[0]
    assert chunk.parent_chunk_id.root == "f" * 64
    assert chunk.ordinal == 3


def test_large_table_produces_parts_and_parent() -> None:
    table = _rows_table(6)
    result = build_table_chunks(table, _ctx(), token_counters=[_WordCounter()], table_row_group_tokens=25)
    parts = [c for c in result.chunks if c.item_kind == ct.ItemKind.table_part]
    parents = [c for c in result.chunks if c.item_kind == ct.ItemKind.parent]
    assert len(parents) == 1
    assert len(parts) >= 2
    parent = parents[0]
    assert parent.level == 1
    assert parent.parent_chunk_id is None
    assert sorted(item.root for item in parent.child_chunk_ids) == sorted(p.chunk_id.root for p in parts)
    for i, part in enumerate(parts):
        assert part.parent_chunk_id == parent.chunk_id
        assert part.level == 0
        assert part.ordinal == i
        # 헤더가 모든 조각의 text 앞에 반복된다(04 §4.2 "큰 표").
        assert "헤더1" in part.text
        assert "헤더2" in part.text
    # row_range는 조각마다 다르고 헤더 행(0) 인덱스를 포함하지 않는다.
    all_rows = [
        row for part in parts for row in range(part.table_ref.row_range[0].root, part.table_ref.row_range[1].root)
    ]
    assert 0 not in all_rows
    assert sorted(all_rows) == list(range(1, 7))
    assert result.warnings == []


def test_merged_cell_forces_group_extension_and_warns() -> None:
    # 데이터 2행, row_span=2가 0번 데이터 행에 걸려 있어 두 행이 강제로 한 그룹이 된다.
    # 단일 행 markdown 텍스트 토큰 수 = 15(헤더5+구분선5+행5), budget=15로 두면
    # 병합이 없다면 두 그룹(각 1행)으로 나뉘겠지만, 병합 때문에 한 그룹(20토큰)으로 합쳐져야 한다.
    table = _rows_table(2, row_span_at=0)
    result = build_table_chunks(table, _ctx(), token_counters=[_WordCounter()], table_row_group_tokens=15)
    assert len(result.chunks) == 1  # 강제 병합으로 그룹이 1개뿐이라 표 부모 없이 단일 리프
    chunk = result.chunks[0]
    assert chunk.item_kind == ct.ItemKind.table
    assert [item.root for item in chunk.table_ref.row_range] == [1, 3]
    assert len(result.warnings) == 1
    assert result.warnings[0].code == ct.ErrorCodeCatalog.chunk_block_oversized
    assert result.warnings[0].chunk_id == chunk.chunk_id


def test_single_row_oversized_still_forms_own_group_and_warns() -> None:
    # budget=5인데 행 하나만으로도 15토큰 -> 모든 행이 단독 그룹 + 경고.
    table = _rows_table(3)
    result = build_table_chunks(table, _ctx(), token_counters=[_WordCounter()], table_row_group_tokens=5)
    parts = [c for c in result.chunks if c.item_kind == ct.ItemKind.table_part]
    assert len(parts) == 3
    oversized_chunk_ids = {
        w.chunk_id.root for w in result.warnings if w.code == ct.ErrorCodeCatalog.chunk_block_oversized
    }
    assert oversized_chunk_ids == {p.chunk_id.root for p in parts}
    # 표 부모 자체는 5*3+10=25 << parent_max_tokens(2048)라 오버사이즈 아님.
    parent = next(c for c in result.chunks if c.item_kind == ct.ItemKind.parent)
    assert parent.chunk_id.root not in oversized_chunk_ids


def test_max_parts_escalation_doubles_budget() -> None:
    table = _rows_table(4)
    result = build_table_chunks(
        table,
        _ctx(),
        token_counters=[_WordCounter()],
        table_row_group_tokens=15,
        max_parts=1,
        leaf_max_tokens=512,
    )
    assert result.applied_table_row_group_tokens == 30
    assert len(result.chunks) == 1  # 예산이 30으로 늘면서 4행이 한 그룹으로 합쳐진다.


def test_max_parts_raises_count_exceeded_when_leaf_cap_reached() -> None:
    table = _rows_table(4)
    with pytest.raises(StageError) as exc_info:
        build_table_chunks(
            table,
            _ctx(),
            token_counters=[_WordCounter()],
            table_row_group_tokens=15,
            max_parts=1,
            leaf_max_tokens=15,  # 초기값과 같아 escalation이 일어나지 않는다.
        )
    assert exc_info.value.code == "chunk.count_exceeded"


def test_chunk_id_and_content_hash_are_deterministic() -> None:
    counters = [_WordCounter()]
    result_a = build_table_chunks(_small_table(), _ctx(), token_counters=counters)
    result_b = build_table_chunks(_small_table(), _ctx(), token_counters=counters)
    assert result_a.chunks[0].chunk_id == result_b.chunks[0].chunk_id
    assert result_a.chunks[0].content_hash == result_b.chunks[0].content_hash


def test_col_range_never_splits() -> None:
    result = build_table_chunks(_rows_table(6), _ctx(), token_counters=[_WordCounter()], table_row_group_tokens=25)
    for chunk in result.chunks:
        if chunk.table_ref is not None:
            assert [item.root for item in chunk.table_ref.col_range] == [0, 2]


# --------------------------------------------------------------------------------------------
# RecountStage
# --------------------------------------------------------------------------------------------


def _artifact_ref(schema_type: str) -> ct.ArtifactRef:
    return ct.ArtifactRef(
        uri=f"file:///tmp/{schema_type}.json",  # type: ignore[arg-type]
        blake3=_HEX64,  # type: ignore[arg-type]
        media_type=f"application/vnd.rag.{schema_type.lower()}+json",  # type: ignore[arg-type]
        schema_type=schema_type,  # type: ignore[arg-type]
        schema_version="1.0.0",  # type: ignore[arg-type]
        size_bytes=0,
        stage_key=None,
    )


def _chunk_set(chunks: list[ct.Chunk]) -> ChunkSet:
    return ChunkSet(
        schema_version="1.0.0",
        schema_type="ChunkSet",
        tenant_id=_ULID,  # type: ignore[arg-type]
        collection_id=_ULID,  # type: ignore[arg-type]
        producer=ct.Producer(
            plugin_id="chunker.structure_aware", plugin_version="0.1.0", config_hash=_HEX64, image_digest=None
        ),
        quality=ct.Quality.full,
        warnings=[],
        created_at="2026-01-01T00:00:00.000Z",  # type: ignore[arg-type]
        lineage_refs=LineageRefs(
            source=_artifact_ref("SourceDocument"),
            parsed=_artifact_ref("ParsedDocument"),
            normalized=_artifact_ref("NormalizedDocument"),
        ),
        chunk_set_id=_ULID,  # type: ignore[arg-type]
        document_id=_ULID,  # type: ignore[arg-type]
        doc_version=_HEX64,  # type: ignore[arg-type]
        normalized_ref=NormalizedRef(
            uri="file:///tmp/normalized.json",  # type: ignore[arg-type]
            blake3=_HEX64,  # type: ignore[arg-type]
            media_type="application/vnd.rag.normalized-document+json",  # type: ignore[arg-type]
            schema_type="NormalizedDocument",
            schema_version="1.0.0",  # type: ignore[arg-type]
            size_bytes=0,
            stage_key=None,
        ),
        document_hash=_HEX64,  # type: ignore[arg-type]
        chunker_id="chunker.structure_aware",  # type: ignore[arg-type]
        chunker_config_hash="1" * 64,  # type: ignore[arg-type]
        primary_tokenizer_id="hf:BAAI/bge-m3",  # type: ignore[arg-type]
        secondary_tokenizer_ids=[],  # type: ignore[arg-type]
        genre_route=ct.Genre.unknown,
        analyzer_id="regex:1.0.0:none",  # type: ignore[arg-type]
        dictionary_hash=_HEX64,  # type: ignore[arg-type]
        language="ko",  # type: ignore[arg-type]
        pii_policy_applied=ct.PiiPolicy.keep,
        stats=ChunkSetStats(
            leaf_count=len(chunks), parent_count=0, table_part_count=0, summary_count=0, oversized_blocks=0
        ),
        chunks=chunks,
    )


def _base_chunk_set() -> ChunkSet:
    result = build_table_chunks(_small_table(), _ctx(), token_counters=[_WordCounter()])
    return _chunk_set(result.chunks)


def test_recount_adds_target_tokenizer_and_preserves_identity() -> None:
    original = _base_chunk_set()
    stage = RecountStage(RecountConfig(tokenizer_id="tiktoken:o200k_base"))
    ctx = _StubCtx(token_counter=_WordCounter(tokenizer_id="tiktoken:o200k_base"))

    updated = asyncio.run(stage.run(original, ctx))

    assert updated.chunk_set_id == original.chunk_set_id
    assert updated.lineage_refs == original.lineage_refs
    assert updated.chunks[0].span == original.chunks[0].span
    assert updated.chunks[0].chunk_id == original.chunks[0].chunk_id
    counts = updated.chunks[0].token_counts.root
    assert "hf:BAAI/bge-m3" in counts
    assert counts["tiktoken:o200k_base"].root == _WordCounter().count(updated.chunks[0].text)
    assert any(item.root == "tiktoken:o200k_base" for item in updated.secondary_tokenizer_ids)
    assert updated.producer.plugin_id.root == "recount.token_counter"
    assert updated.created_at.root != original.created_at.root


def test_recount_is_idempotent_on_already_tracked_tokenizer() -> None:
    original = _base_chunk_set()
    stage = RecountStage(RecountConfig(tokenizer_id="tiktoken:o200k_base"))
    first = asyncio.run(stage.run(original, _StubCtx(token_counter=_WordCounter(tokenizer_id="tiktoken:o200k_base"))))
    second = asyncio.run(stage.run(first, _StubCtx(token_counter=_WordCounter(tokenizer_id="tiktoken:o200k_base"))))
    assert len(second.secondary_tokenizer_ids) == 1


def test_recount_raises_on_tokenizer_mismatch() -> None:
    original = _base_chunk_set()
    stage = RecountStage(RecountConfig(tokenizer_id="tiktoken:o200k_base"))
    ctx = _StubCtx(token_counter=_WordCounter(tokenizer_id="hf:BAAI/bge-m3"))
    with pytest.raises(StageError) as exc_info:
        asyncio.run(stage.run(original, ctx))
    assert exc_info.value.code == "chunk.tokenizer_missing"
