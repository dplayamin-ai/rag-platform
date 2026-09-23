"""PDF 빠른 경로 파서(`parser.pdf_fast_pdftext`) 컴포넌트 테스트 — 순수 헬퍼 단위 테스트 +
최소 PDF 픽스처로 만든 전체 파이프라인 통합 테스트.

설계 근거: `WP-105-parse-pdf-fast-pypdfium2.md` §테스트, 04-pipelines/05 §4·§7.2·§7.3·§7.7·§11,
바이블 §5.4 `ParsedDocument` 불변식(블록 평탄 리스트·`parent_block_id`·`ordinal`·`block_id` 결정 규칙).
픽스처: `tests/fixtures/pdf_fast/pdf_builder.py`(reportlab 없이 순수 Python으로 만든 최소 PDF 바이트),
`SourceDocument` 봉투는 `tests/contracts/fixtures/source-document/001.json`에서 바이트·포맷만 바꿔 쓴다.
구성: 순수 헬퍼(`_cluster_font_sizes`·`_pattern_heading_level`·`_detect_columns`·
`_merge_reading_order`) 단위 테스트와, 제목+문단·페이지 나눔·저밀도(스캔 유사)·빈 페이지·2단 컬럼·
암호화·손상 바이트·결정성 통합 테스트, 트리 불변식 일괄 검증.
검증 계층: 1층(여기서 검증). 실제 스캔 OCR·Docling 레이아웃 경로는 `needs_model`(WP 참조) — 이 파일에는
그 경로의 스텁조차 없어 마커 대상 테스트가 없다.
"""

from __future__ import annotations

import asyncio
import importlib.util
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

from rag_platform.adapters.parse.pdf_fast_pdftext import (
    PdfFastParserConfig,
    PdfFastPdftextParser,
    _cluster_font_sizes,
    _ColBlock,
    _detect_columns,
    _merge_reading_order,
    _pattern_heading_level,
)
from rag_platform.contracts import common_types as ct
from rag_platform.contracts.source_document import SourceDocument
from rag_platform.sdk.hashing import blake3_hex
from rag_platform.sdk.stage import StageError

if TYPE_CHECKING:
    from rag_platform.contracts.parsed_document import ParsedDocument

ROOT = Path(__file__).resolve().parents[3]
SOURCE_FIXTURE = ROOT / "tests" / "contracts" / "fixtures" / "source-document" / "001.json"
_BUILDER_PATH = ROOT / "tests" / "fixtures" / "pdf_fast" / "pdf_builder.py"

_spec = importlib.util.spec_from_file_location("pdf_fast_builder", _BUILDER_PATH)
assert _spec is not None
assert _spec.loader is not None
_builder = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_builder)
build_text_pdf = _builder.build_text_pdf
build_image_page_pdf = _builder.build_image_page_pdf
text_run = _builder.text_run


class _Ctx:
    def now(self) -> datetime:
        return datetime(2026, 9, 23, 9, 0, tzinfo=UTC)


def _source_document(data: bytes, *, encrypted: bool = False) -> SourceDocument:
    raw = json.loads(SOURCE_FIXTURE.read_text(encoding="utf-8"))
    digest = blake3_hex(data)
    raw["doc_version"] = raw["content_hash"] = digest
    raw["size_bytes"] = len(data)
    raw["artifact"] = {**raw["artifact"], "blake3": digest, "size_bytes": len(data), "media_type": "application/pdf"}
    raw["format"] = "pdf"
    raw["media_type"] = "application/pdf"
    raw["metadata"] = {**raw["metadata"], "genre": None}
    raw["container_flags"] = {**raw["container_flags"], "encrypted": encrypted}
    return SourceDocument.model_validate(raw)


def _parse(data: bytes, *, encrypted: bool = False) -> ParsedDocument:
    doc = _source_document(data, encrypted=encrypted)
    return asyncio.run(PdfFastPdftextParser().parse_bytes(data, doc, _Ctx()))


# ---------------------------------------------------------------------------------------------
# 순수 헬퍼 단위 테스트(PDF 불필요)
# ---------------------------------------------------------------------------------------------


def test_cluster_font_sizes_descending_levels() -> None:
    sizes = [24.0, 24.0, 18.0, 18.0, 14.0, 14.0, 11.0, 11.0]
    levels = _cluster_font_sizes(sizes, max_clusters=4)
    assert levels[24.0] == 1
    assert levels[18.0] == 2
    assert levels[14.0] == 3
    assert levels[11.0] == 4


def test_cluster_font_sizes_caps_at_max_clusters() -> None:
    sizes = [20.0, 17.0, 14.0, 11.0, 9.0]  # 5개 서로 다른 크기, k<=4
    levels = _cluster_font_sizes(sizes, max_clusters=4)
    assert set(levels.values()) == {1, 2, 3, 4}
    assert levels[11.0] == 4
    assert levels[9.0] == 4  # 가장 작은 두 크기가 level 4로 합쳐짐


@pytest.mark.parametrize(
    ("text", "expected_level"),
    [
        ("제1편 총칙", 1),
        ("제2장 정의", 2),
        ("제3절 범위", 3),
        ("제4조 목적", 4),
        ("1. 개요", 1),
        ("1.1 배경", 2),
        ("1.1.1 세부", 3),
    ],
)
def test_pattern_heading_level_primary_families(text: str, expected_level: int) -> None:
    last = [0]
    result = _pattern_heading_level(text, last)
    assert result is not None
    level, label = result
    assert level == expected_level
    assert label
    assert last[0] == expected_level


def test_pattern_heading_level_sublevel_markers_cascade_from_last_pattern() -> None:
    last = [2]  # 직전에 "1.1"(level 2) 패턴이 매칭됐다고 가정
    level, _label = _pattern_heading_level("가. 세부항목", last)
    assert level == 3
    level2, _label2 = _pattern_heading_level("(1) 세부", last)
    assert level2 == 4
    level3, _label3 = _pattern_heading_level("① 세부", last)
    assert level3 == 5


def test_pattern_heading_level_no_match_returns_none() -> None:
    assert _pattern_heading_level("일반 본문 문장입니다.", [0]) is None


def test_detect_columns_positive_case() -> None:
    left = [_ColBlock(left=10.0, right=100.0, top=100.0, bottom=90.0) for _ in range(3)]
    right = [_ColBlock(left=300.0, right=390.0, top=100.0, bottom=90.0) for _ in range(3)]
    columns = _detect_columns([*left, *right], page_width=400.0)
    assert len(columns) == 2
    assert columns[0][0] == 0.0
    assert columns[1][1] == 400.0
    assert columns[0][1] == columns[1][0]  # 중간 경계 일치


def test_detect_columns_falls_back_to_single_when_gap_too_small() -> None:
    blocks = [
        _ColBlock(left=0.0, right=50.0, top=100.0, bottom=90.0),
        _ColBlock(left=5.0, right=55.0, top=80.0, bottom=70.0),
    ]
    columns = _detect_columns(blocks, page_width=400.0)
    assert columns == [(0.0, 400.0)]


def test_detect_columns_falls_back_when_coverage_is_lopsided() -> None:
    # 왼쪽에 9개, 오른쪽에 1개 뿐이면 커버리지 조건(>0.3)을 오른쪽이 만족하지 못해 단일 컬럼으로 폴백.
    left = [_ColBlock(left=10.0 + i, right=100.0 + i, top=100.0, bottom=90.0) for i in range(9)]
    right = [_ColBlock(left=300.0, right=390.0, top=100.0, bottom=90.0)]
    columns = _detect_columns([*left, *right], page_width=400.0)
    assert columns == [(0.0, 400.0)]


def test_merge_reading_order_inserts_cross_block_by_y_position() -> None:
    left = [_ColBlock(left=0, right=50, top=90, bottom=80), _ColBlock(left=0, right=50, top=50, bottom=40)]
    right = [_ColBlock(left=100, right=150, top=85, bottom=75), _ColBlock(left=100, right=150, top=45, bottom=35)]
    title = _ColBlock(left=0, right=200, top=100, bottom=95)
    ordered = _merge_reading_order([left, right], [title])
    assert ordered[0] is title
    assert ordered[1] is left[0]
    assert ordered[2] is left[1]
    assert ordered[3] is right[0]
    assert ordered[4] is right[1]


def test_merge_reading_order_without_cross_blocks_is_left_then_right() -> None:
    left = [_ColBlock(0, 50, 90, 80)]
    right = [_ColBlock(100, 150, 90, 80)]
    assert _merge_reading_order([left, right], []) == [*left, *right]


# ---------------------------------------------------------------------------------------------
# 통합 테스트 — 최소 PDF 픽스처
# ---------------------------------------------------------------------------------------------


def test_heading_and_paragraph_merge_single_page() -> None:
    content = (
        text_run(72, 700, 18, "Document Title")
        + text_run(72, 670, 11, "First paragraph line one continues onto the next line naturally.")
        + text_run(72, 655, 11, "second line of the same paragraph here.")
        + text_run(72, 625, 11, "Second paragraph starts after a gap here in the body text.")
        + text_run(72, 595, 11, "Third paragraph adds one more block so the heading ratio stays low.")
    )
    data = build_text_pdf([content])
    pd = _parse(data)

    assert pd.quality == ct.Quality.full
    assert pd.source_kind == ct.SourceKind.born_digital
    assert pd.page_count == 1
    assert pd.language.root == "ko"
    assert [b.type for b in pd.blocks] == [
        ct.BlockType.heading,
        ct.BlockType.paragraph,
        ct.BlockType.paragraph,
        ct.BlockType.paragraph,
    ]
    heading = pd.blocks[0]
    assert heading.level == 1
    assert heading.heading_inferred is True
    assert heading.parent_block_id is None
    assert heading.text == "Document Title"
    assert heading.provenance.element_path == "/page[0]/block[0]"
    assert heading.provenance.char_start == 0
    assert heading.provenance.char_end == len(heading.text)
    assert heading.provenance.page == 1
    assert heading.provenance.bbox is not None
    assert heading.furniture is False

    for para in pd.blocks[1:]:
        assert para.parent_block_id == heading.block_id
    assert [b.ordinal for b in pd.blocks[1:]] == [0, 1, 2]
    assert pd.text_length == sum(len(b.text) for b in pd.blocks)
    assert pd.block_count == len(pd.blocks)


def test_page_break_blocks_inserted_from_second_page() -> None:
    pages = [
        text_run(72, 700, 11, "Page one paragraph with enough characters to pass the density gate."),
        text_run(72, 700, 11, "Page two paragraph with enough characters to pass the density gate."),
        text_run(72, 700, 11, "Page three paragraph with enough characters to pass the density gate."),
    ]
    data = build_text_pdf(pages)
    pd = _parse(data)

    assert pd.page_count == 3
    types = [(b.type, b.provenance.page) for b in pd.blocks]
    assert types == [
        (ct.BlockType.paragraph, 1),
        (ct.BlockType.page_break, 2),
        (ct.BlockType.paragraph, 2),
        (ct.BlockType.page_break, 3),
        (ct.BlockType.paragraph, 3),
    ]
    page_breaks = [b for b in pd.blocks if b.type == ct.BlockType.page_break]
    assert all(b.provenance.bbox is None for b in page_breaks)
    assert all(b.provenance.element_path == f"/page[{b.provenance.page - 1}]/break" for b in page_breaks)


def test_low_density_page_is_marked_skipped_and_degraded() -> None:
    data = build_image_page_pdf()
    pd = _parse(data)

    assert pd.blocks == []
    assert pd.quality == ct.Quality.degraded
    assert pd.source_kind == ct.SourceKind.scanned
    assert pd.page_status is not None
    assert len(pd.page_status) == 1
    assert pd.page_status[0].page == 1
    assert pd.page_status[0].status == ct.PageStatus.skipped
    assert pd.page_status[0].ocr_confidence is None
    assert len(pd.warnings) == 1
    assert pd.warnings[0].code == ct.ErrorCodeCatalog.parse_page_skipped
    assert pd.warnings[0].page == 1


def test_empty_page_without_text_or_image_stays_full_quality() -> None:
    data = build_text_pdf([""])
    pd = _parse(data)

    assert pd.blocks == []
    assert pd.quality == ct.Quality.full
    assert pd.source_kind == ct.SourceKind.born_digital
    assert pd.page_status is None
    assert pd.warnings == []
    assert pd.text_length == 0
    assert pd.block_count == 0


def test_two_column_reading_order_left_then_right_with_cross_title() -> None:
    content = (
        text_run(72, 750, 20, "Wide Title Spanning Both Columns Below Here")
        + text_run(72, 700, 11, "Left column line one text sample.")
        + text_run(72, 650, 11, "Left column line two text sample.")
        + text_run(72, 600, 11, "Left column line three sample text.")
        + text_run(320, 690, 11, "Right column line one sample text.")
        + text_run(320, 640, 11, "Right column line two sample text.")
        + text_run(320, 590, 11, "Right column line three text here.")
    )
    data = build_text_pdf([content])
    pd = _parse(data)

    texts = [b.text for b in pd.blocks]
    assert texts == [
        "Wide Title Spanning Both Columns Below Here",
        "Left column line one text sample.",
        "Left column line two text sample.",
        "Left column line three sample text.",
        "Right column line one sample text.",
        "Right column line two sample text.",
        "Right column line three text here.",
    ]
    assert pd.blocks[0].type == ct.BlockType.heading  # 큰 폰트 + 전체 폭을 가로지르는 제목


def test_encrypted_flag_without_credentials_is_rejected() -> None:
    content = text_run(72, 700, 11, "Some content that would parse fine if not encrypted flagged here.")
    data = build_text_pdf([content])
    with pytest.raises(StageError) as err:
        _parse(data, encrypted=True)
    assert err.value.code == "parse.document_encrypted"
    assert err.value.retryable is False


def test_corrupt_bytes_map_to_corrupt_container() -> None:
    with pytest.raises(StageError) as err:
        _parse(b"not a pdf file at all, just garbage bytes 1234567890")
    assert err.value.code == "parse.corrupt_container"
    assert err.value.retryable is False


def test_run_without_source_bytes_port_raises_conversion_failed() -> None:
    content = text_run(72, 700, 11, "Content for the run()-without-port regression test case here.")
    data = build_text_pdf([content])
    doc = _source_document(data)
    with pytest.raises(StageError) as err:
        asyncio.run(PdfFastPdftextParser().run(doc, _Ctx()))
    assert err.value.code == "parse.conversion_failed"


class _CtxWithPort(_Ctx):
    def __init__(self, data: bytes) -> None:
        self._data = data

    async def source_bytes(self) -> bytes:
        return self._data


def test_run_uses_source_bytes_port() -> None:
    content = text_run(72, 700, 11, "Content served through the async source_bytes port for this test.")
    data = build_text_pdf([content])
    doc = _source_document(data)
    parser = PdfFastPdftextParser()
    via_port = asyncio.run(parser.run(doc, _CtxWithPort(data)))
    direct = asyncio.run(parser.parse_bytes(data, doc, _Ctx()))
    assert via_port.model_dump(mode="json") == direct.model_dump(mode="json")


def test_determinism_same_bytes_same_hash() -> None:
    content = (
        text_run(72, 700, 18, "Determinism Title")
        + text_run(72, 670, 11, "Body paragraph number one with enough characters here.")
        + text_run(72, 640, 11, "Body paragraph number two with enough characters here.")
    )
    data = build_text_pdf([content])
    first = _parse(data)
    second = _parse(data)
    assert first.model_dump(mode="json") == second.model_dump(mode="json")


def test_fingerprint_and_capabilities() -> None:
    base = PdfFastPdftextParser()
    assert base.fingerprint() == PdfFastPdftextParser().fingerprint()
    assert base.fingerprint() != PdfFastPdftextParser(PdfFastParserConfig(min_page_chars=5)).fingerprint()
    caps = base.capabilities()
    assert caps.isolation_modes == [ct.IsolationMode.in_process]
    assert caps.supports_resumable is False
    assert caps.input_formats == ["pdf"]
    assert caps.requires_gpu is False


# ---------------------------------------------------------------------------------------------
# 트리 불변식(hwpx 테스트와 동형)
# ---------------------------------------------------------------------------------------------


def _assert_tree(pd: ParsedDocument) -> None:
    blocks = pd.blocks
    index = {_bid(b.block_id): i for i, b in enumerate(blocks)}
    assert pd.block_count == len(blocks)
    assert pd.text_length == sum(len(b.text) for b in blocks)
    assert len(index) == len(blocks), "block_id must be unique"
    paths = [b.provenance.element_path for b in blocks]
    assert len(set(paths)) == len(paths), "element_path must be unique"
    ordinals: dict[str | None, int] = {}
    for b in blocks:
        parent = _bid(b.parent_block_id)
        if parent is not None:
            assert parent in index, "parent_block_id must reference an earlier block"
            assert index[parent] < index[_bid(b.block_id)]
        expected = ordinals.get(parent, 0)
        assert b.ordinal == expected, f"ordinal must be sequential per parent (got {b.ordinal}, want {expected})"
        ordinals[parent] = expected + 1
        if b.type != ct.BlockType.page_break:
            assert b.provenance.bbox is not None
        else:
            assert b.provenance.bbox is None


def _bid(value: Any) -> str | None:
    return None if value is None else str(value.root if hasattr(value, "root") else value)


@pytest.mark.parametrize(
    "data_factory",
    [
        lambda: build_text_pdf(
            [
                text_run(72, 700, 18, "Tree Title")
                + text_run(72, 670, 11, "Paragraph one has enough characters to pass the gate here.")
                + text_run(72, 640, 11, "Paragraph two has enough characters to pass the gate here.")
                + text_run(72, 610, 11, "Paragraph three has enough characters to pass the gate here.")
            ]
        ),
        lambda: build_text_pdf(
            [
                text_run(72, 700, 11, "Page one paragraph with enough characters to pass the gate."),
                text_run(72, 700, 11, "Page two paragraph with enough characters to pass the gate."),
            ]
        ),
    ],
    ids=["heading-tree", "multi-page"],
)
def test_tree_invariants(data_factory: Any) -> None:
    _assert_tree(_parse(data_factory()))
