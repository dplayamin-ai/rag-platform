"""HTML 파서(`parser.html_trafilatura_docling`) 컴포넌트 테스트 — 한국어 공공기관 게시판 픽스처 2건 전량 파싱,
블록 트리 무결성, 표 격자(rowspan/colspan), 이미지·코드·인용·목록 매핑, 메타데이터, 오류 코드.

설계 근거: 04-pipelines/07 §2(처리 개요)·§3(디코딩)·§6(구조 보존 파싱)·§8(메타데이터)·§10(Provenance)·
§13(실패 모드), 바이블 §5.4 `ParsedDocument` 불변식(블록 평탄 리스트·`parent_block_id`·`ordinal`·`block_id`
결정 규칙). WP-104(F1-04)가 좁힌 범위(DOM 경로 정본, Docling은 `needs_model` 자리)를 그대로 검증한다.
구성: 픽스처는 `tests/fixtures/parse_html/board_notice_utf8.html`(UTF-8, 지방세 납부 안내 보도자료 형태),
`board_notice_cp949.html`(CP949/EUC-KR 선언, 정보공개 절차 안내 형태) — 둘 다 이 저장소를 위해 새로
작성한 합성 표본이며 실제 기관 페이지의 발췌·인용이 아니다. `SourceDocument` 봉투는
`tests/contracts/fixtures/source-document/001.json`에서 바이트·포맷·해시만 바꿔 쓴다.
검증 계층: 1층(여기서 검증). Docker·모델·GPU·외부 네트워크 불필요.
"""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from rag_platform.adapters.parse.html_trafilatura_docling import (
    HtmlParserConfig,
    HtmlTrafilaturaDoclingParser,
    docling_table_backend_placeholder,
)
from rag_platform.contracts import common_types as ct
from rag_platform.contracts.common_types.TableCell import HeaderKind
from rag_platform.contracts.parsed_document import Block, ParsedDocument
from rag_platform.contracts.source_document import SourceDocument
from rag_platform.sdk.hashing import blake3_hex, block_id
from rag_platform.sdk.stage import StageError

ROOT = Path(__file__).resolve().parents[3]
FIXTURES = ROOT / "tests" / "fixtures" / "parse_html"
SOURCE_FIXTURE = ROOT / "tests" / "contracts" / "fixtures" / "source-document" / "001.json"

_UTF8_URI = (
    "https://www.mois.example.go.kr/frt/bbs/type010/commonSelectBoardArticle.do?bbsId=BBSMSTR_000000000008&nttId=118732"
)
_CP949_URI = "https://www.acrc.example.go.kr/board/view.do?id=55"


class _MemoryArtifacts:
    """쓰기 전용 파생 산출물 포트의 인메모리 가짜(콘텐츠 주소화)."""

    def __init__(self) -> None:
        self.items: dict[str, tuple[str, bytes]] = {}

    async def put_derived(self, data: bytes, *, kind: str, ext: str, media_type: str) -> ct.ArtifactRef:
        digest = blake3_hex(data)
        self.items[digest] = (kind, data)
        return ct.ArtifactRef(
            uri=f"file:///tenants/t/derived/{kind}/{digest[:2]}/{digest}.{ext}",
            blake3=digest,
            media_type=media_type,
            size_bytes=len(data),
        )


class _Ctx:
    def __init__(self) -> None:
        self.artifacts = _MemoryArtifacts()

    def now(self) -> datetime:
        return datetime(2026, 9, 23, 9, 0, tzinfo=UTC)


class _CtxWithPort(_Ctx):
    def __init__(self, data: bytes) -> None:
        super().__init__()
        self._data = data

    async def source_bytes(self) -> bytes:
        return self._data


def _source_document(data: bytes, *, resolved_uri: str, language_hint: str | None = None) -> SourceDocument:
    raw = json.loads(SOURCE_FIXTURE.read_text(encoding="utf-8"))
    digest = blake3_hex(data)
    raw["doc_version"] = raw["content_hash"] = digest
    raw["size_bytes"] = len(data)
    raw["artifact"] = {**raw["artifact"], "blake3": digest, "size_bytes": len(data), "media_type": "text/html"}
    raw["media_type"] = "text/html"
    raw["format"] = "html"
    raw["source_uri"] = resolved_uri
    raw["resolved_uri"] = resolved_uri
    raw["metadata"] = {**raw["metadata"], "genre": None, "language_hint": language_hint}
    raw.pop("detect_report", None)
    return SourceDocument.model_validate(raw)


def _parse(
    name: str, resolved_uri: str, config: HtmlParserConfig | None = None, *, language_hint: str | None = None
) -> tuple[ParsedDocument, _Ctx]:
    data = (FIXTURES / name).read_bytes()
    ctx = _Ctx()
    parsed = asyncio.run(
        HtmlTrafilaturaDoclingParser(config).parse_bytes(
            data, _source_document(data, resolved_uri=resolved_uri, language_hint=language_hint), ctx
        )
    )
    return parsed, ctx


_CACHE: dict[str, tuple[ParsedDocument, _Ctx]] = {}


def _utf8() -> tuple[ParsedDocument, _Ctx]:
    if "utf8" not in _CACHE:
        _CACHE["utf8"] = _parse("board_notice_utf8.html", _UTF8_URI)
    return _CACHE["utf8"]


def _cp949() -> tuple[ParsedDocument, _Ctx]:
    if "cp949" not in _CACHE:
        _CACHE["cp949"] = _parse("board_notice_cp949.html", _CP949_URI)
    return _CACHE["cp949"]


def _bid(value: Any) -> str | None:
    return None if value is None else str(value.root if hasattr(value, "root") else value)


def _by_type(pd: ParsedDocument, btype: ct.BlockType) -> list[Block]:
    return [b for b in pd.blocks if b.type == btype]


# ---------------------------------------------------------------------------------------------
# 트리 무결성(바이블 §5.4·07 §10 불변식)
# ---------------------------------------------------------------------------------------------


def _assert_table(b: Block) -> None:
    table = b.table
    assert table is not None
    assert table.html_ref is not None
    if table.quality.merged_cells_preserved:
        grid = [[0] * table.n_cols for _ in range(table.n_rows)]
        for cell in table.cells:
            for r in range(cell.row, cell.row + cell.row_span):
                for c in range(cell.col, cell.col + cell.col_span):
                    grid[r][c] += 1
        assert all(v == 1 for row in grid for v in row), "anchor cells must tile the grid exactly"
    for cell in table.cells:
        assert cell.provenance is not None
        assert b.text[cell.provenance.char_start : cell.provenance.char_end] == cell.text


def _assert_tree(pd: ParsedDocument) -> None:
    blocks = pd.blocks
    index = {_bid(b.block_id): i for i, b in enumerate(blocks)}
    assert pd.block_count == len(blocks)
    assert pd.text_length == sum(len(b.text) for b in blocks)
    assert len(index) == len(blocks), "block_id must be unique"
    paths = [b.provenance.element_path for b in blocks]
    assert len(set(paths)) == len(paths), "element_path must be unique"
    ordinals: dict[str | None, int] = {}
    for i, b in enumerate(blocks):
        assert _bid(b.block_id) == block_id(pd.doc_version.root, b.provenance.element_path)
        assert b.provenance.page is None
        assert b.provenance.bbox is None
        assert b.provenance.section_index is None
        assert b.provenance.char_start == 0
        assert b.provenance.char_end == len(b.text)
        assert b.furniture is False
        assert b.source == ct.BlockSource.text_layer
        parent = _bid(b.parent_block_id)
        if parent is not None:
            assert parent in index, "parent must exist"
            assert index[parent] < i, "parent precedes child in document order"
        expected = ordinals.get(parent, 0)
        assert b.ordinal == expected, f"ordinal gap at {b.provenance.element_path}"
        ordinals[parent] = expected + 1
        if b.type == ct.BlockType.caption:
            target = blocks[index[str(b.caption_of)]]
            assert _bid(b.block_id) in [_bid(x) for x in target.caption_block_ids or []]
        if b.caption_block_ids:
            for cid in b.caption_block_ids:
                assert blocks[index[_bid(cid)]].caption_of == _bid(b.block_id)
        if b.type == ct.BlockType.table:
            _assert_table(b)
        if b.type == ct.BlockType.figure:
            assert b.figure is not None
    for link in pd.links or []:
        target = blocks[index[_bid(link.block_id)]]
        assert 0 <= link.char_start <= link.char_end <= len(target.text)


# ---------------------------------------------------------------------------------------------
# UTF-8 게시판 픽스처
# ---------------------------------------------------------------------------------------------


def test_utf8_tree_integrity_quality_and_determinism() -> None:
    pd, _ = _utf8()
    again = ParsedDocument.model_validate(pd.model_dump(mode="json"))
    assert again == pd
    assert pd.quality == ct.Quality.full
    assert pd.source_kind == ct.SourceKind.flow
    assert pd.page_count is None
    assert [c.root for c in pd.parser_chain] == ["parser.html_trafilatura_docling"]
    _assert_tree(pd)
    second, _ = _parse("board_notice_utf8.html", _UTF8_URI)
    assert second.model_dump(mode="json") == pd.model_dump(mode="json")


def test_utf8_encoding_detected() -> None:
    pd, _ = _utf8()
    assert pd.source_encoding == "utf-8"


def test_utf8_metadata_mapping() -> None:
    pd, _ = _utf8()
    assert pd.metadata is not None
    assert pd.metadata.title == "2026년 하반기 지방세 납부 일정 안내"
    assert pd.metadata.web is not None
    assert pd.metadata.web.site_name == "행정안전부"
    assert str(pd.metadata.web.canonical_url.root).startswith(
        "https://www.mois.example.go.kr/frt/bbs/type010/commonSelectBoardArticle.do"
    )
    assert pd.metadata.created_at is not None
    assert pd.metadata.created_at.root == "2026-09-15T01:00:00.000Z"
    assert pd.metadata.web.published_at is not None
    assert pd.metadata.web.published_at.root == "2026-09-15T01:00:00.000Z"
    assert pd.metadata.genre == ct.Genre.web_article
    assert pd.language.root == "ko"


def test_utf8_navigation_text_collected_and_removed() -> None:
    pd, _ = _utf8()
    nav = pd.metadata.navigation_text if pd.metadata else None
    assert nav is not None
    assert any("보도자료" in t for t in nav)
    assert any("Copyright" in t for t in nav)


def test_utf8_headings_and_seg_split_paragraphs() -> None:
    pd, _ = _utf8()
    headings = [(b.level, b.text) for b in _by_type(pd, ct.BlockType.heading)]
    assert headings == [(2, "2026년 하반기 지방세 납부 일정 안내"), (3, "납부 일정"), (3, "첨부파일")]
    paragraphs = [b.text for b in _by_type(pd, ct.BlockType.paragraph)]
    assert paragraphs[0] == "행정안전부는 2026년 하반기 지방세 납부 일정을 다음과 같이 안내한다."
    assert paragraphs[1].startswith("□ 납부 기한이 지나면")
    assert "○ 위택스" in paragraphs[1]
    assert "SEO 키워드" not in " ".join(paragraphs), "display:none paragraph must be dropped"


def test_utf8_meta_table_is_form_role_with_row_headers() -> None:
    pd, _ = _utf8()
    meta_table = _by_type(pd, ct.BlockType.table)[0]
    assert meta_table.table is not None
    assert meta_table.table.role == ct.TableRole.form
    assert meta_table.table.header_row_indices == []
    row_headers = {c.text for c in meta_table.table.cells if c.header_kind == HeaderKind.row}
    assert row_headers == {"담당부서", "등록일"}


def test_utf8_data_table_merged_cells_and_column_header() -> None:
    pd, ctx = _utf8()
    data_table = _by_type(pd, ct.BlockType.table)[1]
    assert data_table.table is not None
    assert (data_table.table.n_rows, data_table.table.n_cols) == (3, 3)
    assert data_table.table.header_row_indices == [ct.HeaderRowIndice(0)]
    assert data_table.table.header_inferred is False
    assert data_table.table.quality.merged_cells_preserved is True
    assert data_table.table.quality.structure_source.value == "native"
    spans = {(c.row, c.col): (c.row_span, c.col_span) for c in data_table.table.cells}
    assert spans[(1, 0)] == (2, 1)
    html_ref = data_table.table.html_ref
    assert html_ref is not None
    html = ctx.artifacts.items[html_ref.blake3.root][1].decode("utf-8")
    assert "<thead>" in html
    assert 'rowspan="2"' in html


def test_utf8_attachments_become_list_items_with_absolute_links() -> None:
    pd, _ = _utf8()
    items = _by_type(pd, ct.BlockType.list_item)
    assert [b.text for b in items] == [
        "2026년 하반기 지방세 납부 일정 안내(보도자료).hwpx",
        "납부 일정표.pdf",
    ]
    links = pd.links or []
    assert len(links) == 2
    assert all(link.href.startswith("https://www.mois.example.go.kr/cmm/fms/FileDown.do") for link in links)


def test_utf8_derived_artifacts_present() -> None:
    pd, ctx = _utf8()
    kinds = {a.kind.value for a in pd.artifacts or []}
    assert {"vendor_json", "derived_source", "table_html"} <= kinds
    for artifact in pd.artifacts or []:
        assert artifact.ref.blake3.root in ctx.artifacts.items


# ---------------------------------------------------------------------------------------------
# CP949/EUC-KR 게시판 픽스처
# ---------------------------------------------------------------------------------------------


def test_cp949_tree_integrity_and_encoding() -> None:
    pd, _ = _cp949()
    _assert_tree(pd)
    assert pd.source_encoding == "cp949"
    assert pd.quality == ct.Quality.full


def test_cp949_metadata_date_only_published_time_uses_default_timezone() -> None:
    pd, _ = _cp949()
    assert pd.metadata is not None
    assert pd.metadata.created_at is not None
    assert pd.metadata.created_at.root == "2026-09-19T15:00:00.000Z"
    assert pd.metadata.web is not None
    assert pd.metadata.web.published_at is not None
    assert pd.metadata.web.published_at.root == "2026-09-19T15:00:00.000Z"
    assert str(pd.metadata.web.canonical_url.root) == "https://www.acrc.example.go.kr/board/view.do?id=55"
    assert pd.metadata.genre == ct.Genre.web_article


def test_cp949_ordered_and_nested_lists_with_numbering_labels() -> None:
    pd, _ = _cp949()
    items = [(b.level, b.ordered, b.numbering_label, b.text) for b in _by_type(pd, ct.BlockType.list_item)]
    assert items == [
        (0, True, "1.", "청구서 접수"),
        (0, True, "2.", "담당부서 배정"),
        (1, False, "-", "부서장 검토"),
        (1, False, "-", "공개 여부 결정"),
        (0, True, "3.", "결과 통지"),
    ]
    nested = items[2]
    top = _by_type(pd, ct.BlockType.list_item)[1]
    child = _by_type(pd, ct.BlockType.list_item)[2]
    assert child.parent_block_id == top.block_id
    assert nested is not None  # nested tuple sanity (level=1 asserted above)


def test_cp949_blockquote_children_become_separate_paragraphs() -> None:
    pd, _ = _cp949()
    paragraphs = [b.text for b in _by_type(pd, ct.BlockType.paragraph)]
    assert "비공개 결정 시 이의신청은 접수일로부터 30일 이내에 제기해야 합니다." in paragraphs
    assert "자세한 절차는 관련 법령을 참고하시기 바랍니다." in paragraphs


def test_cp949_code_block_language_and_whitespace_preserved() -> None:
    pd, _ = _cp949()
    codes = _by_type(pd, ct.BlockType.code)
    assert len(codes) == 1
    assert codes[0].text == "GET /v1/requests/{id}"
    assert codes[0].code is not None
    assert codes[0].code.language == "text"


def test_cp949_data_uri_image_becomes_figure_with_artifact() -> None:
    pd, ctx = _cp949()
    figures = _by_type(pd, ct.BlockType.figure)
    assert len(figures) == 1
    assert figures[0].figure is not None
    assert figures[0].figure.alt_text == "처리 절차 안내도"
    assert figures[0].figure.artifact.blake3.root in ctx.artifacts.items
    kinds = {a.kind.value for a in pd.artifacts or []}
    assert "figure_crop" in kinds


def test_cp949_remote_image_with_alt_becomes_paragraph_and_link() -> None:
    pd, _ = _cp949()
    paragraphs = [b.text for b in _by_type(pd, ct.BlockType.paragraph)]
    assert "공지 아이콘" in paragraphs
    links = pd.links or []
    icon_links = [link for link in links if link.href.endswith("/images/notice.jpg")]
    assert len(icon_links) == 1
    assert icon_links[0].href == "https://www.acrc.example.go.kr/images/notice.jpg"


def test_cp949_remote_image_without_meaningful_alt_produces_no_extra_block() -> None:
    pd, _ = _cp949()
    # data URI 그림 1개만 figure가 되고 alt="" spacer.gif는 블록도 링크도 만들지 않는다(07 §9.3).
    assert len(_by_type(pd, ct.BlockType.figure)) == 1
    assert not any(link.href.endswith("spacer.gif") for link in pd.links or [])


# ---------------------------------------------------------------------------------------------
# 오류·스테이지 프로토콜
# ---------------------------------------------------------------------------------------------


def test_empty_body_raises_conversion_failed() -> None:
    html = b"<html><head><title>empty</title></head><body></body></html>"
    with pytest.raises(StageError) as err:
        asyncio.run(
            HtmlTrafilaturaDoclingParser().parse_bytes(
                html, _source_document(html, resolved_uri="https://example.go.kr/empty"), _Ctx()
            )
        )
    assert err.value.code == "parse.conversion_failed"
    assert err.value.retryable is False


def test_docling_placeholder_raises_not_implemented() -> None:
    with pytest.raises(NotImplementedError):
        docling_table_backend_placeholder("<table></table>")


def test_use_docling_table_backend_flag_raises_before_parsing() -> None:
    data = (FIXTURES / "board_notice_utf8.html").read_bytes()
    parser = HtmlTrafilaturaDoclingParser(HtmlParserConfig(use_docling_table_backend=True))
    with pytest.raises(NotImplementedError):
        asyncio.run(parser.parse_bytes(data, _source_document(data, resolved_uri=_UTF8_URI), _Ctx()))


def test_fingerprint_capabilities_and_config_hash() -> None:
    base = HtmlTrafilaturaDoclingParser()
    assert base.fingerprint() == HtmlTrafilaturaDoclingParser().fingerprint()
    assert base.fingerprint() != HtmlTrafilaturaDoclingParser(HtmlParserConfig(mode="docs_site")).fingerprint()
    caps = base.capabilities()
    assert [m.value for m in caps.isolation_modes] == ["in_process"]
    assert caps.input_formats == ["html"]
    assert caps.supports_resumable is False
    pd, _ = _utf8()
    assert pd.producer.config_hash.root == base.config_hash()


def test_run_uses_source_bytes_port() -> None:
    data = (FIXTURES / "board_notice_utf8.html").read_bytes()
    parser = HtmlTrafilaturaDoclingParser()
    via_port = asyncio.run(parser.run(_source_document(data, resolved_uri=_UTF8_URI), _CtxWithPort(data)))
    assert via_port.model_dump(mode="json") == _utf8()[0].model_dump(mode="json")
    with pytest.raises(StageError) as err:
        asyncio.run(parser.run(_source_document(data, resolved_uri=_UTF8_URI), _Ctx()))
    assert err.value.code == "parse.conversion_failed"
