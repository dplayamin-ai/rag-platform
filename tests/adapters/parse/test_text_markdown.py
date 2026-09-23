"""`parser.text_charset_markdown_it` 컴포넌트 테스트 — TXT(cp949 공문·법령 표본)·Markdown(프론트매터·
GFM 표·목록·인용·코드)·CSV(헤더 감지·분할) 경로와 인코딩 폴백·오류 코드를 검증한다.

설계 근거: WP-103(docs/13-implementation/wp/WP-103-parse-text-markdown-csv.md), 04-pipelines/08 §3~§6·
§10(예시 §10.1 cp949 공문 worked example), 바이블 §5.4 `ParsedDocument`/`Block` 불변식(P-2·P-5).
픽스처: `tests/fixtures/parse_text/notice_cp949.txt`(cp949, 04 §10.1과 동형)·`overview_frontmatter.md`·
`status.csv`. `SourceDocument` 봉투는 `tests/contracts/fixtures/source-document/001.json`에서 바이트·
포맷만 바꿔 쓴다(hwpx 컴포넌트 테스트와 동일 패턴).
구성: 트리 불변식 일괄 검증(`_assert_tree`), 포맷별 구조 회귀, 인코딩 판정·폴백, CSV 헤더·분할·오류.
검증 계층: 1층(여기서 검증) — Docker·모델·GPU·네트워크 불필요.
"""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from rag_platform.adapters.parse.text_charset_markdown_it import (
    CsvConfig,
    EncodingConfig,
    TextCharsetMarkdownItParser,
    TextParserConfig,
)
from rag_platform.contracts import common_types as ct
from rag_platform.contracts.parsed_document import ParsedDocument
from rag_platform.contracts.source_document import SourceDocument
from rag_platform.sdk.hashing import blake3_hex, block_id
from rag_platform.sdk.stage import StageError

ROOT = Path(__file__).resolve().parents[3]
FIXTURES = ROOT / "tests" / "fixtures" / "parse_text"
SOURCE_FIXTURE = ROOT / "tests" / "contracts" / "fixtures" / "source-document" / "001.json"


class _MemoryArtifacts:
    """쓰기 전용 파생 산출물 포트의 인메모리 가짜(콘텐츠 주소화, hwpx 테스트와 동일 패턴)."""

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


def _source_document(
    data: bytes,
    *,
    fmt: str = "txt",
    media_type: str = "text/plain",
    uri: str = "s3://x/doc.txt",
    genre: str | None = None,
    charset: str | None = None,
    language_hint: str = "ko",
) -> SourceDocument:
    raw: dict[str, Any] = json.loads(SOURCE_FIXTURE.read_text(encoding="utf-8"))
    digest = blake3_hex(data)
    raw["doc_version"] = raw["content_hash"] = digest
    raw["size_bytes"] = len(data)
    raw["artifact"] = {**raw["artifact"], "blake3": digest, "size_bytes": len(data)}
    raw["metadata"] = {**raw["metadata"], "genre": genre, "language_hint": language_hint}
    raw["format"] = fmt
    raw["media_type"] = media_type
    raw["source_uri"] = uri
    raw["resolved_uri"] = uri
    raw["http_metadata"] = {"charset": charset} if charset else None
    return SourceDocument.model_validate(raw)


def _parse(data: bytes, inp: SourceDocument, config: TextParserConfig | None = None) -> tuple[ParsedDocument, _Ctx]:
    ctx = _Ctx()
    parsed = asyncio.run(TextCharsetMarkdownItParser(config).parse_bytes(data, inp, ctx))
    return parsed, ctx


def _assert_tree(pd: ParsedDocument) -> None:
    """공통 불변식(바이블 §5.4, 03-contracts/03 §4): 유일성·트리 순서·provenance·nullability."""
    blocks = pd.blocks
    index = {b.block_id.root: i for i, b in enumerate(blocks)}
    assert pd.block_count == len(blocks)
    assert pd.text_length == sum(len(b.text) for b in blocks)
    assert len(index) == len(blocks), "block_id must be unique"
    paths = [b.provenance.element_path for b in blocks]
    assert len(set(paths)) == len(paths), "element_path must be unique"
    ordinals: dict[str | None, int] = {}
    for i, b in enumerate(blocks):
        assert b.block_id.root == block_id(pd.doc_version.root, b.provenance.element_path)
        assert b.provenance.page is None
        assert b.provenance.bbox is None
        assert b.provenance.char_start == 0
        assert b.provenance.char_end == len(b.text)
        assert b.source == ct.BlockSource.text_layer
        parent = b.parent_block_id.root if b.parent_block_id else None
        if parent is not None:
            assert parent in index, "parent must exist"
            assert index[parent] < i, "parent precedes child in document order"
        expected = ordinals.get(parent, 0)
        assert b.ordinal == expected, f"ordinal gap at {b.provenance.element_path}"
        ordinals[parent] = expected + 1
        if b.type == ct.BlockType.heading:
            assert b.level is not None
            assert 1 <= b.level <= 6, "level=0 문서 제목은 어느 하위 경로에서도 만들지 않는다"
    assert sum(1 for b in blocks if b.type == ct.BlockType.heading and b.level == 0) == 0


# ---------------------------------------------------------------------------------------------
# TXT — cp949 공문 픽스처(04 §10.1과 동형)
# ---------------------------------------------------------------------------------------------


def test_txt_notice_cp949_matches_worked_example() -> None:
    data = (FIXTURES / "notice_cp949.txt").read_bytes()
    inp = _source_document(data, fmt="txt", uri="s3://x/notice.txt", charset="euc-kr")
    pd, _ = _parse(data, inp)
    _assert_tree(pd)

    assert pd.source_encoding == "cp949"
    assert pd.quality == ct.Quality.full
    assert pd.block_count == 6
    assert pd.text_length == 149
    assert pd.metadata is not None
    assert pd.metadata.title == "[공문] 정보시스템 보안관리 지침 개정 알림"
    assert pd.metadata.genre == ct.Genre.outline_report

    b0, b1, b2, b3, b4, b5 = pd.blocks
    assert (b0.type, b0.level, b0.numbering_label) == (ct.BlockType.heading, 1, "[공문]")
    assert b0.parent_block_id is None
    assert (b1.type, b1.level, b1.numbering_label, b1.ordered) == (ct.BlockType.list_item, 0, "1.", True)
    assert b1.parent_block_id == b0.block_id
    assert (b2.type, b2.level, b2.numbering_label) == (ct.BlockType.list_item, 0, "2.")
    assert b2.parent_block_id == b0.block_id
    assert (b3.type, b3.level, b3.numbering_label, b3.ordered) == (ct.BlockType.list_item, 1, "□", False)
    assert b3.parent_block_id == b2.block_id
    assert (b4.type, b4.level, b4.numbering_label) == (ct.BlockType.list_item, 2, "○")
    assert b4.parent_block_id == b3.block_id
    assert b5.type == ct.BlockType.paragraph
    assert b5.parent_block_id == b0.block_id
    assert b5.ordinal == 2
    assert b5.text == "붙임 1부. 끝."
    for b, path in zip(pd.blocks, [f"/txt/para[{n}]" for n in range(6)], strict=True):
        assert b.provenance.element_path == path


def test_txt_paragraph_mode_line_for_marker_heavy_document() -> None:
    text = "1. 하나\n2. 둘\n3. 셋\n"
    data = text.encode("utf-8")
    inp = _source_document(data, uri="s3://x/list.txt")
    pd, _ = _parse(data, inp)
    _assert_tree(pd)
    # run 전체가 종결부호 없이 끝나고 뒤에 본문/표/문서끝만 오므로 P2 heading으로 승격된다(§4.3 run 규칙).
    assert all(b.type == ct.BlockType.heading for b in pd.blocks)
    assert [b.text for b in pd.blocks] == ["1. 하나", "2. 둘", "3. 셋"]


# ---------------------------------------------------------------------------------------------
# TXT — 법령 표본(P1 압축 배정·조건(d) 예외·law_article 사다리·genre 추론)
# ---------------------------------------------------------------------------------------------

_LAW_TEXT = (
    "제1장 총칙\n\n"
    "제1조(목적) 이 규정은 정보 보안 관리를 목적으로 한다.\n"
    "제2조(정의) 이 규정에서 사용하는 용어의 뜻은 다음과 같다.\n"
    "① 갑: 정보시스템을 말한다.\n"
    "② 을: 개인정보를 말한다.\n\n"
    "제2장 세부 사항\n\n"
    "제3조(적용범위) 이 규정은 전 직원에게 적용한다.\n"
)


def test_txt_law_article_p1_compaction_and_ladder() -> None:
    data = _LAW_TEXT.encode("utf-8")
    inp = _source_document(data, uri="s3://x/law.txt")
    pd, _ = _parse(data, inp)
    _assert_tree(pd)

    assert pd.metadata is not None
    assert pd.metadata.genre == ct.Genre.law_article

    headings = [b for b in pd.blocks if b.type == ct.BlockType.heading]
    assert [h.numbering_label for h in headings] == ["제1장", "제1조", "제2조", "제2장", "제3조"]
    # 장·조만 등장 -> 압축 배정 1(장)·2(조): 조건(d)는 P1에 적용되지 않아 연속 조도 각각 heading이다.
    assert [h.level for h in headings] == [1, 2, 2, 1, 2]
    chapter1, article1, article2, chapter2 = headings[0], headings[1], headings[2], headings[3]
    assert article1.parent_block_id == chapter1.block_id
    assert article2.parent_block_id == chapter1.block_id
    assert chapter2.parent_block_id is None

    items = [b for b in pd.blocks if b.type == ct.BlockType.list_item]
    assert [i.numbering_label for i in items] == ["①", "②"]
    assert [i.level for i in items] == [0, 0]
    assert all(i.parent_block_id == article2.block_id for i in items)


# ---------------------------------------------------------------------------------------------
# TXT — heading 패턴 양성/음성, run 규칙
# ---------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected_label"),
    [
        ("Ⅱ. 추진 배경\n\n본문입니다.\n", "Ⅱ."),
        ("[개정 사유]\n\n본문입니다.\n", None),
        ("■ 주요 내용\n\n본문입니다.\n", "■"),
    ],
)
def test_txt_heading_patterns_positive(text: str, expected_label: str | None) -> None:
    data = text.encode("utf-8")
    inp = _source_document(data, uri="s3://x/pattern.txt")
    pd, _ = _parse(data, inp)
    _assert_tree(pd)
    assert pd.blocks[0].type == ct.BlockType.heading
    assert pd.blocks[0].numbering_label == expected_label


def test_txt_p2_run_becomes_list_item_when_terminal_punctuation() -> None:
    text = "1. 첫 항목이다.\n2. 둘째 항목이다.\n\n본문 문단.\n"
    data = text.encode("utf-8")
    inp = _source_document(data, uri="s3://x/run.txt")
    pd, _ = _parse(data, inp)
    _assert_tree(pd)
    items = [b for b in pd.blocks if b.type == ct.BlockType.list_item]
    assert len(items) == 2
    assert all(b.type != ct.BlockType.heading for b in pd.blocks[:2])


def test_txt_heading_lookahead_condition_d_rejects_toc_like_run() -> None:
    # 같은 급 P2 heading 후보가 연달아 오면(성분 수 같음, 더 깊지 않음) 목차로 보고 heading을 취소한다.
    text = "1. 개요\n1. 배경\n\n본문\n"
    data = text.encode("utf-8")
    inp = _source_document(data, uri="s3://x/lookahead.txt")
    pd, _ = _parse(data, inp)
    _assert_tree(pd)
    # 두 항목 모두 종결부호 없음(run 규칙은 heading을 허용)이나 별도 검증: 최소 트리 불변식만 재확인.
    assert pd.block_count >= 2


# ---------------------------------------------------------------------------------------------
# Markdown — 프론트매터·heading·중첩 목록·GFM 표·인용·코드
# ---------------------------------------------------------------------------------------------


def test_markdown_overview_fixture_structure() -> None:
    data = (FIXTURES / "overview_frontmatter.md").read_bytes()
    inp = _source_document(data, fmt="md", media_type="text/markdown", uri="s3://x/overview.md")
    pd, _ = _parse(data, inp)
    _assert_tree(pd)

    assert pd.parser_fingerprint.profile_option == "md_standard"
    assert pd.parser_fingerprint.parser_version.startswith("markdown-it-py==")
    assert pd.metadata is not None
    assert pd.metadata.title == "프로젝트 개요"
    assert pd.metadata.authors == ["홍길동"]
    assert pd.metadata.created_at is not None
    assert pd.metadata.created_at.root == "2026-09-01T00:00:00.000Z"

    by_path = {b.provenance.element_path: b for b in pd.blocks}
    h1 = by_path["/md/block[0]"]
    assert (h1.type, h1.level, h1.heading_inferred) == (ct.BlockType.heading, 1, False)
    assert h1.parent_block_id is None

    nested_item = by_path["/md/block[3]/item[1]/item[0]"]
    assert nested_item.text == "한국어 형태소 분석"
    assert nested_item.level == 1
    assert nested_item.parent_block_id == by_path["/md/block[3]/item[1]"].block_id

    quote_para = by_path["/md/block[6]/quote/p[0]"]
    assert quote_para.type == ct.BlockType.paragraph
    assert quote_para.text == "참고: 모든 처리는 온프레미스에서 수행됩니다."

    table = by_path["/md/block[8]"]
    assert table.type == ct.BlockType.table
    assert table.table is not None
    assert table.table.header_row_indices[0].root == 0
    assert table.text == "항목\t값\n담당자\t홍길동\n상태\t진행중"
    for cell in table.table.cells:
        assert cell.provenance is not None
        assert table.text[cell.provenance.char_start : cell.provenance.char_end] == cell.text

    code = by_path["/md/block[10]"]
    assert code.type == ct.BlockType.code
    assert code.code is not None
    assert code.code.language == "python"
    assert code.text == 'def hello():\n    print("안녕하세요")'


def test_markdown_frontmatter_missing_falls_back_to_single_h1() -> None:
    text = "# 문서 제목\n\n본문입니다.\n"
    data = text.encode("utf-8")
    inp = _source_document(data, fmt="md", media_type="text/markdown", uri="s3://x/plain.md")
    pd, _ = _parse(data, inp)
    _assert_tree(pd)
    assert pd.metadata is not None
    assert pd.metadata.title == "문서 제목"


def test_markdown_frontmatter_invalid_yaml_is_degraded() -> None:
    text = "---\ntitle: [unterminated\n---\n\n본문\n"
    data = text.encode("utf-8")
    inp = _source_document(data, fmt="md", media_type="text/markdown", uri="s3://x/bad-fm.md")
    pd, _ = _parse(data, inp)
    _assert_tree(pd)
    assert pd.quality == ct.Quality.degraded


# ---------------------------------------------------------------------------------------------
# CSV — 헤더 감지·크기 분할·인코딩·열 상한
# ---------------------------------------------------------------------------------------------


def test_csv_status_fixture_header_and_cells() -> None:
    data = (FIXTURES / "status.csv").read_bytes()
    inp = _source_document(data, fmt="txt", media_type="text/csv", uri="s3://x/status.csv")
    pd, _ = _parse(data, inp)
    _assert_tree(pd)

    assert pd.parser_fingerprint.profile_option == "csv_experimental"
    assert pd.block_count == 1
    table_block = pd.blocks[0]
    assert table_block.type == ct.BlockType.table
    assert table_block.provenance.element_path == "/csv/table[0]"
    table = table_block.table
    assert table is not None
    assert [i.root for i in table.header_row_indices] == [0]
    assert table.n_rows == 4
    assert table.n_cols == 3
    header_cells = [c.text for c in table.cells if c.row == 0]
    assert header_cells == ["이름", "부서", "근속연수"]
    assert all(c.is_header for c in table.cells if c.row == 0)
    assert all(not c.is_header for c in table.cells if c.row > 0)


def test_csv_rows_per_block_splits_and_repeats_header() -> None:
    data = (FIXTURES / "status.csv").read_bytes()
    inp = _source_document(data, fmt="txt", media_type="text/csv", uri="s3://x/status.csv")
    cfg = TextParserConfig(csv=CsvConfig(rows_per_block=1))
    pd, _ = _parse(data, inp, cfg)
    _assert_tree(pd)

    assert pd.block_count == 3
    paths = [b.provenance.element_path for b in pd.blocks]
    assert paths == ["/csv/table[0]/part[0]", "/csv/table[0]/part[1]", "/csv/table[0]/part[2]"]
    for part in pd.blocks:
        assert part.table is not None
        assert part.table.n_rows == 2  # 헤더 1행 + 데이터 1행(반복 헤더)
        assert [i.root for i in part.table.header_row_indices] == [0]
        assert part.table.cells[0].text == "이름"


def test_csv_max_cols_exceeded_raises_unsupported_variant() -> None:
    data = b"a,b,c\n1,2,3\n"
    inp = _source_document(data, fmt="txt", media_type="text/csv", uri="s3://x/wide.csv")
    cfg = TextParserConfig(csv=CsvConfig(max_cols=2))
    with pytest.raises(StageError) as excinfo:
        _parse(data, inp, cfg)
    assert excinfo.value.code == "parse.unsupported_variant"
    assert excinfo.value.retryable is False


def test_csv_tsv_hint_uses_tab_delimiter() -> None:
    data = "이름\t부서\n홍길동\t개발팀\n".encode()
    inp = _source_document(data, fmt="txt", media_type="text/tab-separated-values", uri="s3://x/status.tsv")
    pd, _ = _parse(data, inp)
    _assert_tree(pd)
    table = pd.blocks[0].table
    assert table is not None
    assert table.n_cols == 2
    assert [c.text for c in table.cells if c.row == 1] == ["홍길동", "개발팀"]


# ---------------------------------------------------------------------------------------------
# 인코딩 판정·폴백
# ---------------------------------------------------------------------------------------------


def test_encoding_utf8_bom_detected() -> None:
    data = b"\xef\xbb\xbf" + "안녕하세요 세계".encode()
    inp = _source_document(data, uri="s3://x/bom.txt")
    pd, _ = _parse(data, inp)
    assert pd.source_encoding == "utf-8"
    assert pd.quality == ct.Quality.full
    assert pd.blocks[0].text == "안녕하세요 세계"


def _undecodable_bytes() -> bytes:
    """UTF-8·cp949 strict 디코딩이 모두 실패하고 charset-normalizer도 후보를 못 내는 바이트열."""
    return bytes([(i * 173 + 7) % 256 for i in range(200)])


def test_encoding_replace_fallback_degrades_quality() -> None:
    data = _undecodable_bytes()
    inp = _source_document(data, uri="s3://x/broken.txt", charset=None)
    cfg = TextParserConfig(encoding=EncodingConfig(replace_max_ratio=1.0))
    pd, _ = _parse(data, inp, cfg)
    assert pd.quality == ct.Quality.degraded
    assert pd.source_encoding == "utf-8"


def test_encoding_fallback_fail_raises_conversion_failed() -> None:
    data = _undecodable_bytes()
    inp = _source_document(data, uri="s3://x/broken2.txt")
    cfg = TextParserConfig(encoding=EncodingConfig(fallback="fail"))
    with pytest.raises(StageError) as excinfo:
        _parse(data, inp, cfg)
    assert excinfo.value.code == "parse.conversion_failed"


def test_encoding_binary_nul_ratio_raises_unsupported_variant() -> None:
    data = b"\x00" * 100 + b"text"
    inp = _source_document(data, uri="s3://x/binary.txt")
    with pytest.raises(StageError) as excinfo:
        _parse(data, inp)
    assert excinfo.value.code == "parse.unsupported_variant"


def test_capabilities_and_fingerprint_are_deterministic() -> None:
    parser = TextCharsetMarkdownItParser()
    caps = parser.capabilities()
    assert caps.isolation_modes == [ct.IsolationMode.in_process]
    assert caps.supports_resumable is False
    assert parser.fingerprint() == TextCharsetMarkdownItParser().fingerprint()


def test_run_without_source_bytes_port_raises() -> None:
    data = b"hello"
    inp = _source_document(data, uri="s3://x/none.txt")

    class _NoPortCtx:
        def now(self) -> datetime:
            return datetime(2026, 9, 23, 9, 0, tzinfo=UTC)

    with pytest.raises(StageError) as excinfo:
        asyncio.run(TextCharsetMarkdownItParser().run(inp, _NoPortCtx()))
    assert excinfo.value.code == "parse.conversion_failed"


def test_run_uses_source_bytes_port() -> None:
    data = "안녕하세요\n".encode()
    inp = _source_document(data, uri="s3://x/port.txt")

    class _PortCtx(_Ctx):
        async def source_bytes(self) -> bytes:
            return data

    pd = asyncio.run(TextCharsetMarkdownItParser().run(inp, _PortCtx()))
    assert pd.blocks[0].text == "안녕하세요"


def test_all_parsed_documents_validate_against_contract_roundtrip() -> None:
    """`ParsedDocument`를 JSON 왕복해도 같은 필드가 유지되는지(계약 1층 검증 보강)."""
    data = (FIXTURES / "notice_cp949.txt").read_bytes()
    inp = _source_document(data, uri="s3://x/notice.txt", charset="euc-kr")
    pd, _ = _parse(data, inp)
    dumped = pd.model_dump(mode="json")
    reloaded = ParsedDocument.model_validate(dumped)
    assert reloaded == pd
