"""HWPX 파서(`parser.hwpx_python_hwpx`) 컴포넌트 테스트 — 표본 전량 파싱·트리 무결성·병합 셀·heading 회귀 스냅샷.

설계 근거: 04-pipelines/04 §3(매핑·`element_path`·heading·표·각주·필드·변경 추적)·§6(오류 코드)·§8(테스트 코퍼스),
바이블 §5.4 `ParsedDocument` 불변식(블록 평탄 리스트·`parent_block_id`·`ordinal`·`block_id` 결정 규칙).
픽스처: `samples/hwpx/*.hwpx`(공공누리 제1유형 보도자료 3건 + python-hwpx 합성 표본, 출처·해시는 `MANIFEST.json`),
`SourceDocument` 봉투는 `tests/contracts/fixtures/source-document/001.json`에서 바이트·해시만 바꿔 쓴다.
스냅샷: `tests/adapters/parse/snapshots/hwpx_blocks.json` — 갱신은 `RAG_UPDATE_SNAPSHOTS=1 uv run pytest <이 파일>`.
구성: 표본 전량 파싱 성공 확인, 블록 트리 무결성(`parent_block_id`/`ordinal`) 검증, 병합 셀 처리,
heading 회귀는 스냅샷 대조로 검증.
검증 계층: 1층(여기서 검증). 원격 표본 재다운로드 대조만 `needs_network`(DEFERRED 주석 참조).
"""

from __future__ import annotations

import asyncio
import hashlib
import io
import json
import os
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from rag_platform.adapters.parse.hwpx_python_hwpx import HwpxParserConfig, HwpxPythonHwpxParser
from rag_platform.contracts import common_types as ct
from rag_platform.contracts.parsed_document import Block, ParsedDocument
from rag_platform.contracts.source_document import SourceDocument
from rag_platform.sdk.hashing import blake3_hex, block_id
from rag_platform.sdk.stage import StageError

ROOT = Path(__file__).resolve().parents[3]
SAMPLES = ROOT / "samples" / "hwpx"
MANIFEST = json.loads((SAMPLES / "MANIFEST.json").read_text(encoding="utf-8"))
SAMPLE_FILES = [entry["file"] for entry in MANIFEST["samples"]]
SNAPSHOT = Path(__file__).parent / "snapshots" / "hwpx_blocks.json"
SOURCE_FIXTURE = ROOT / "tests" / "contracts" / "fixtures" / "source-document" / "001.json"
SYNTHETIC = "synthetic-owpml-features.hwpx"


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
    def __init__(self, data: bytes | None = None) -> None:
        self.artifacts = _MemoryArtifacts()
        self._data = data

    def now(self) -> datetime:
        return datetime(2026, 9, 23, 9, 0, tzinfo=UTC)


class _CtxWithPort(_Ctx):
    async def source_bytes(self) -> bytes:
        assert self._data is not None
        return self._data


def _source_document(data: bytes, *, encrypted: bool = False) -> SourceDocument:
    raw = json.loads(SOURCE_FIXTURE.read_text(encoding="utf-8"))
    digest = blake3_hex(data)
    raw["doc_version"] = raw["content_hash"] = digest
    raw["size_bytes"] = len(data)
    raw["artifact"] = {**raw["artifact"], "blake3": digest, "size_bytes": len(data)}
    raw["metadata"] = {**raw["metadata"], "genre": None}
    raw["container_flags"] = {**raw["container_flags"], "encrypted": encrypted}
    return SourceDocument.model_validate(raw)


def _parse(name: str, config: HwpxParserConfig | None = None) -> tuple[ParsedDocument, _Ctx]:
    data = (SAMPLES / name).read_bytes()
    ctx = _Ctx()
    parsed = asyncio.run(HwpxPythonHwpxParser(config).parse_bytes(data, _source_document(data), ctx))
    return parsed, ctx


_CACHE: dict[str, tuple[ParsedDocument, _Ctx]] = {}


def _parsed(name: str) -> tuple[ParsedDocument, _Ctx]:
    if name not in _CACHE:
        _CACHE[name] = _parse(name)
    return _CACHE[name]


def _bid(value: Any) -> str | None:
    return None if value is None else str(value.root if hasattr(value, "root") else value)


# ---------------------------------------------------------------------------------------------
# 트리 무결성(바이블 §5.4·03-contracts/03 §4 불변식)
# ---------------------------------------------------------------------------------------------


def _assert_tree(pd: ParsedDocument) -> None:  # noqa: PLR0912, PLR0915 - 불변식 목록을 한곳에서 검사
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
        assert b.provenance.section_index is not None
        assert b.provenance.element_path.startswith("/hp:sec[")
        assert b.provenance.char_start == 0
        assert b.provenance.char_end == len(b.text)
        assert b.source == ct.BlockSource.text_layer
        parent = _bid(b.parent_block_id)
        if parent is not None:
            assert parent in index, "parent must exist"
            assert index[parent] < i, "parent precedes child in document order"
        expected = ordinals.get(parent, 0)
        assert b.ordinal == expected, f"ordinal gap at {b.provenance.element_path}"
        ordinals[parent] = expected + 1
        if b.type == ct.BlockType.heading:
            assert b.level is not None
            assert 0 <= b.level <= 6
            anc = parent
            while anc is not None and blocks[index[anc]].type != ct.BlockType.heading:
                anc = _bid(blocks[index[anc]].parent_block_id)
            if anc is not None:
                assert (blocks[index[anc]].level or 0) < b.level
        parent_block = blocks[index[parent]] if parent is not None else None
        if (
            b.type == ct.BlockType.list_item
            and parent_block is not None
            and parent_block.type == ct.BlockType.list_item
        ):
            assert (parent_block.level or 0) < (b.level or 0)
        if parent is not None and blocks[index[parent]].type == ct.BlockType.table:
            assert b.container == ct.BlockContainer.table_cell
        if b.type == ct.BlockType.table:
            _assert_table(b)
        if b.type == ct.BlockType.caption:
            target = blocks[index[str(b.caption_of)]]
            assert _bid(b.block_id) in [_bid(x) for x in target.caption_block_ids or []]
        if b.caption_block_ids:
            for cid in b.caption_block_ids:
                assert blocks[index[_bid(cid)]].caption_of == _bid(b.block_id)
        if b.type == ct.BlockType.footnote:
            assert b.footnote is not None
            assert b.container == ct.BlockContainer.footnote_body
            anchor = _bid(b.footnote.anchor_block_id)
            if anchor is not None:
                assert b.footnote.anchor_char_offset is not None
                assert 0 <= b.footnote.anchor_char_offset <= len(blocks[index[anchor]].text)
        if b.type == ct.BlockType.figure:
            assert b.figure is not None
            refs = {(a.kind.value, _bid(a.block_id)) for a in pd.artifacts or []}
            assert ("figure_crop", _bid(b.block_id)) in refs
    assert sum(1 for b in blocks if b.type == ct.BlockType.heading and b.level == 0) <= 1
    for item in [*(pd.links or []), *(pd.annotations or [])]:
        target = blocks[index[_bid(item.block_id)]]
        assert 0 <= item.char_start <= item.char_end <= len(target.text)
    for f in pd.fields or []:
        assert _bid(f.block_id) in index


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
        assert all(v == 1 for row in grid for v in row), "anchor cells must tile the grid exactly (P-12)"
    for cell in table.cells:
        assert cell.provenance is not None
        assert b.text[cell.provenance.char_start : cell.provenance.char_end] == cell.text
        assert cell.provenance.element_path.startswith(b.provenance.element_path + "/hp:tr[")


# ---------------------------------------------------------------------------------------------
# 표본 전량
# ---------------------------------------------------------------------------------------------


@pytest.mark.parametrize("name", SAMPLE_FILES)
def test_manifest_hashes_match_files(name: str) -> None:
    entry = next(e for e in MANIFEST["samples"] if e["file"] == name)
    data = (SAMPLES / name).read_bytes()
    assert len(data) == entry["size_bytes"]
    assert hashlib.sha256(data).hexdigest() == entry["sha256"]
    assert blake3_hex(data) == entry["blake3"]
    assert entry["license"]
    if entry["kind"] == "public":
        assert entry["license"] == "KOGL-Type1"
        assert entry["attribution"].startswith("출처:")


@pytest.mark.parametrize("name", SAMPLE_FILES)
def test_parse_sample_tree_integrity(name: str) -> None:
    pd, ctx = _parsed(name)
    again = ParsedDocument.model_validate(pd.model_dump(mode="json"))  # 계약 왕복(extra=forbid)
    assert again == pd
    assert pd.parser_fingerprint.parser_id.root == "parser.hwpx_python_hwpx"
    assert pd.parser_fingerprint.parser_version.startswith("python-hwpx==")
    assert pd.parser_fingerprint.profile_option == "hwpx_standard"
    assert [c.root for c in pd.parser_chain] == ["parser.hwpx_python_hwpx"]
    assert pd.source_kind == ct.SourceKind.flow
    assert pd.page_count is None
    assert pd.quality == ct.Quality.full
    assert pd.blocks
    _assert_tree(pd)
    kinds = {a.kind.value for a in pd.artifacts or []}
    assert "vendor_json" in kinds
    for a in pd.artifacts or []:
        assert a.ref.blake3.root in ctx.artifacts.items


@pytest.mark.parametrize("name", SAMPLE_FILES)
def test_parse_is_deterministic(name: str) -> None:
    first, _ = _parsed(name)
    second, _ = _parse(name)
    assert first.model_dump(mode="json") == second.model_dump(mode="json")


def _summary(pd: ParsedDocument) -> dict[str, Any]:
    index = {_bid(b.block_id): i for i, b in enumerate(pd.blocks)}
    blocks = []
    for b in pd.blocks:
        row: dict[str, Any] = {
            "type": b.type.value,
            "path": b.provenance.element_path,
            "parent": index.get(_bid(b.parent_block_id)),
            "ordinal": b.ordinal,
            "container": b.container.value,
            "text": b.text[:40],
        }
        if b.level is not None:
            row["level"] = b.level
        if b.numbering_label is not None:
            row["label"] = b.numbering_label
        if b.heading_inferred:
            row["inferred"] = True
        if b.table is not None:
            row["table"] = {
                "n_rows": b.table.n_rows,
                "n_cols": b.table.n_cols,
                "role": b.table.role.value,
                "header_rows": [h.root for h in b.table.header_row_indices],
                "header_inferred": b.table.header_inferred,
                "merged_cells_preserved": b.table.quality.merged_cells_preserved,
                "spans": [[c.row, c.col, c.row_span, c.col_span] for c in b.table.cells if c.row_span * c.col_span > 1],
            }
        if b.footnote is not None:
            row["footnote"] = [b.footnote.kind.value, b.footnote.marker, b.footnote.anchor_char_offset]
        blocks.append(row)
    meta = pd.metadata
    return {
        "quality": pd.quality.value,
        "genre": meta.genre.value if meta and meta.genre else None,
        "has_tracked_changes": bool(meta and meta.has_tracked_changes),
        "page_header_text": meta.page_header_text if meta else None,
        "fields": [[f.type, f.name] for f in pd.fields or []],
        "links": [[link.href, link.char_start, link.char_end] for link in pd.links or []],
        "annotations": [[a.kind.value, a.text] for a in pd.annotations or []],
        "blocks": blocks,
    }


def test_regression_snapshot() -> None:
    current = {name: _summary(_parsed(name)[0]) for name in SAMPLE_FILES}
    if os.environ.get("RAG_UPDATE_SNAPSHOTS") == "1" or not SNAPSHOT.exists():
        SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
        SNAPSHOT.write_text(json.dumps(current, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    expected = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    for name in SAMPLE_FILES:
        assert current[name] == expected[name], f"snapshot drift in {name} (RAG_UPDATE_SNAPSHOTS=1 to accept)"


# ---------------------------------------------------------------------------------------------
# 합성 표본: 요소별 매핑
# ---------------------------------------------------------------------------------------------


def _by_type(pd: ParsedDocument, btype: ct.BlockType) -> list[Block]:
    return [b for b in pd.blocks if b.type == btype]


def test_synthetic_outline_headings_and_labels() -> None:
    pd, _ = _parsed(SYNTHETIC)
    headings = [(b.level, b.numbering_label, b.text, b.heading_inferred) for b in _by_type(pd, ct.BlockType.heading)]
    assert headings == [
        (1, "1.", "정보보안 기본지침", False),
        (2, "가.", "적용 범위", False),
        (2, "나.", "점검 절차", False),
    ]
    h1, h2, h3 = _by_type(pd, ct.BlockType.heading)
    assert h1.parent_block_id is None
    assert _bid(h2.parent_block_id) == _bid(h1.block_id)
    assert _bid(h3.parent_block_id) == _bid(h1.block_id)


def test_synthetic_lists() -> None:
    pd, _ = _parsed(SYNTHETIC)
    items = [(b.level, b.numbering_label, b.ordered, b.text) for b in _by_type(pd, ct.BlockType.list_item)]
    assert items == [
        (0, "□", False, "모든 소속 직원에게 적용한다."),
        (1, "○", False, "외부 용역 인력을 포함한다."),
        (0, "1.", True, "첫째 번호 항목"),
        (0, "2.", True, "둘째 번호 항목"),
        (1, "-", False, "글머리 항목"),
    ]


def test_synthetic_merged_cells_nested_table_and_caption() -> None:
    pd, ctx = _parsed(SYNTHETIC)
    outer, inner = _by_type(pd, ct.BlockType.table)
    assert outer.table is not None
    assert inner.table is not None
    assert (outer.table.n_rows, outer.table.n_cols) == (3, 3)
    spans = {(c.row, c.col): (c.row_span, c.col_span) for c in outer.table.cells}
    assert spans[(0, 0)] == (1, 2)
    assert spans[(0, 2)] == (2, 1)
    assert len(outer.table.cells) == 7
    assert outer.table.quality.merged_cells_preserved
    assert outer.table.quality.structure_source.value == "native"
    assert outer.table.header_row_indices == [ct.HeaderRowIndice(0)]
    assert outer.table.header_inferred
    assert outer.text.split("\n")[0] == "R0C0\tR0C2"
    nested_cell = next(c for c in outer.table.cells if (c.row, c.col) == (2, 1))
    assert nested_cell.nested_table_block_id == _bid(inner.block_id)
    assert f"[table:{_bid(inner.block_id)}]" in nested_cell.text
    assert _bid(inner.parent_block_id) == _bid(outer.block_id)
    assert inner.container == ct.BlockContainer.table_cell
    assert inner.provenance.element_path.endswith("/hp:tr[2]/hp:tc[1]/hp:subList/hp:p[1]/hp:tbl[0]")
    (caption,) = _by_type(pd, ct.BlockType.caption)
    assert caption.text == "<표 1> 적용 대상 구분"
    assert caption.caption_of == _bid(outer.block_id)
    assert pd.blocks.index(caption) > pd.blocks.index(inner)  # side=BOTTOM → 표(와 표 자식) 뒤
    html_ref = outer.table.html_ref
    assert html_ref is not None
    html = ctx.artifacts.items[html_ref.blake3.root][1].decode("utf-8")
    assert '<th colspan="2">R0C0</th>' in html
    assert '<th rowspan="2">R0C2</th>' in html


def test_synthetic_footnote_endnote_formula_figure_link() -> None:
    pd, _ = _parsed(SYNTHETIC)
    foot, end = _by_type(pd, ct.BlockType.footnote)
    assert foot.footnote is not None
    assert end.footnote is not None
    anchor = next(b for b in pd.blocks if _bid(b.block_id) == _bid(foot.footnote.anchor_block_id))
    assert (foot.footnote.kind.value, foot.footnote.marker) == ("footnote", "1)")
    assert foot.footnote.anchor_char_offset == len(anchor.text)
    assert foot.parent_block_id == anchor.parent_block_id
    assert pd.blocks.index(foot) == pd.blocks.index(anchor) + 1
    assert end.footnote.kind.value == "endnote"
    assert end.parent_block_id is None
    assert pd.blocks[-1] == end  # 미주는 문서 끝 루트 형제
    (formula,) = _by_type(pd, ct.BlockType.formula)
    assert formula.formula is not None
    assert (formula.text, formula.formula.script, formula.formula.latex) == ("a over b", "a over b", None)
    (figure,) = _by_type(pd, ct.BlockType.figure)
    assert figure.figure is not None
    assert figure.figure.artifact.media_type.root == "image/png"
    assert figure.figure.alt_text is None
    (link,) = pd.links or []
    linked = next(b for b in pd.blocks if _bid(b.block_id) == _bid(link.block_id))
    assert link.href == "https://www.example.go.kr/guide"
    assert linked.text[link.char_start : link.char_end] == "보안 누리집"


def test_synthetic_tracked_changes_header_footer_and_sections() -> None:
    pd, _ = _parsed(SYNTHETIC)
    assert pd.metadata is not None
    assert pd.metadata.has_tracked_changes
    assert pd.metadata.page_header_text == ["정보보안 기본지침"]
    assert pd.metadata.page_footer_text == ["대외비 아님"]
    changed = next(b for b in pd.blocks if b.text.startswith("원래 문장"))
    assert changed.text == "원래 문장 끝추가됨"  # accept_all: 삭제 제외·삽입 포함
    (ann,) = pd.annotations or []
    assert (ann.kind.value, ann.text, ann.char_start) == ("tracked_change", "삭제될 부분 ", len("원래 문장 "))
    (brk,) = _by_type(pd, ct.BlockType.page_break)
    assert brk.page_break is not None
    assert brk.page_break.section_index == 1
    assert brk.parent_block_id is None
    last_para = next(b for b in pd.blocks if b.text == "둘째 구역의 문단이다.")
    assert last_para.provenance.section_index == 1
    assert last_para.provenance.element_path == "/hp:sec[1]/hp:p[1]"


def test_reject_all_policy_keeps_deleted_text() -> None:
    pd, _ = _parse(SYNTHETIC, HwpxParserConfig(tracked_changes="reject_all"))
    changed = next(b for b in pd.blocks if b.text.startswith("원래 문장"))
    assert changed.text == "원래 문장 삭제될 부분 끝"
    assert [a.text for a in pd.annotations or []] == ["추가됨"]


# ---------------------------------------------------------------------------------------------
# 공공 표본: 실측 특성
# ---------------------------------------------------------------------------------------------


def test_public_samples_have_merged_cells_and_bullet_stack() -> None:
    merged = 0
    for name in SAMPLE_FILES:
        if not name.startswith("kogl1-"):
            continue
        pd, _ = _parsed(name)
        for b in _by_type(pd, ct.BlockType.table):
            assert b.table is not None
            merged += sum(1 for c in b.table.cells if c.row_span > 1 or c.col_span > 1)
    assert merged > 0
    pd, _ = _parsed("kogl1-mohw-emergency-care-20260923.hwpx")
    labels = [(b.numbering_label, b.level) for b in _by_type(pd, ct.BlockType.list_item)]
    assert ("□", 0) in labels
    assert ("○", 1) in labels
    assert ("-", 2) in labels
    assert [(f.type, f.name) for f in pd.fields or []] == [("CLICK_HERE", "본문")]
    figures = _by_type(pd, ct.BlockType.figure)
    assert figures
    assert all(f.figure is not None and f.figure.alt_text is None for f in figures)  # 한컴 자동 shapeComment 제외


def test_bindata_limit_drops_figures_and_degrades() -> None:
    pd, _ = _parse(SYNTHETIC, HwpxParserConfig(max_bindata_bytes=0))
    assert not _by_type(pd, ct.BlockType.figure)
    assert pd.quality == ct.Quality.degraded


# ---------------------------------------------------------------------------------------------
# 오류·스테이지 프로토콜
# ---------------------------------------------------------------------------------------------


def _rezip(name: str, drop: str) -> bytes:
    src = zipfile.ZipFile(SAMPLES / name)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as out:
        for info in src.infolist():
            if info.filename != drop:
                out.writestr(info.filename, src.read(info.filename), compress_type=info.compress_type)
    return buf.getvalue()


@pytest.mark.parametrize(
    ("payload", "code"),
    [
        (b"not a zip archive", "parse.corrupt_container"),
        (b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\x00" * 512, "parse.corrupt_container"),
        (_rezip(SYNTHETIC, "Contents/header.xml"), "parse.corrupt_container"),
        (_rezip(SYNTHETIC, "Contents/content.hpf"), "parse.corrupt_container"),
    ],
    ids=["garbage", "ole2-hwp5", "missing-header", "missing-content-hpf"],
)
def test_corrupt_inputs_map_to_catalog_codes(payload: bytes, code: str) -> None:
    with pytest.raises(StageError) as err:
        asyncio.run(HwpxPythonHwpxParser().parse_bytes(payload, _source_document(payload), _Ctx()))
    assert err.value.code == code
    assert err.value.retryable is False


def test_encrypted_flag_is_rejected_before_parsing() -> None:
    data = (SAMPLES / SYNTHETIC).read_bytes()
    with pytest.raises(StageError) as err:
        asyncio.run(HwpxPythonHwpxParser().parse_bytes(data, _source_document(data, encrypted=True), _Ctx()))
    assert err.value.code == "parse.document_encrypted"


def test_run_uses_source_bytes_port() -> None:
    data = (SAMPLES / SYNTHETIC).read_bytes()
    parser = HwpxPythonHwpxParser()
    via_port = asyncio.run(parser.run(_source_document(data), _CtxWithPort(data)))
    assert via_port.model_dump(mode="json") == _parsed(SYNTHETIC)[0].model_dump(mode="json")
    with pytest.raises(StageError) as err:
        asyncio.run(parser.run(_source_document(data), _Ctx()))
    assert err.value.code == "parse.conversion_failed"


def test_fingerprint_and_capabilities() -> None:
    base = HwpxPythonHwpxParser()
    assert base.fingerprint() == HwpxPythonHwpxParser().fingerprint()
    assert base.fingerprint() != HwpxPythonHwpxParser(HwpxParserConfig(tracked_changes="reject_all")).fingerprint()
    caps = base.capabilities()
    assert [m.value for m in caps.isolation_modes] == ["in_process"]
    assert caps.input_formats == ["hwpx"]
    assert caps.supports_resumable is False
    pd, _ = _parsed(SYNTHETIC)
    assert pd.producer.config_hash.root == base.config_hash()


# ---------------------------------------------------------------------------------------------
# 3층(네트워크)
# ---------------------------------------------------------------------------------------------


@pytest.mark.needs_network
@pytest.mark.parametrize("name", [n for n in SAMPLE_FILES if n.startswith("kogl1-")])
def test_public_samples_still_match_origin(name: str) -> None:
    # DEFERRED: 외부 네트워크 가능 환경(프록시 허용 CI 야간 잡)에서 `uv run python tools/dev.py test-deferred`로
    # korea.kr 원본을 다시 받아 MANIFEST sha256과 대조한다. 원본 교체·삭제 시 표본 갱신 신호다.
    import urllib.request  # noqa: PLC0415 - 네트워크 테스트에서만 필요

    entry = next(e for e in MANIFEST["samples"] if e["file"] == name)
    with urllib.request.urlopen(entry["download_url"], timeout=60) as resp:  # noqa: S310 - 고정 https URL
        data = resp.read()
    assert hashlib.sha256(data).hexdigest() == entry["sha256"]
