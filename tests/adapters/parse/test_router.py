"""`format_detector.detect()`·`FormatDetectorStage`·`ParseRouterStage` 컴포넌트 테스트.

설계 근거: 04-pipelines/03 §2(판별 알고리즘: 신호 우선순위·패밀리·텍스트 계열·신뢰도)·§4.1(후보 선별)·
§6(부분 성공과 폴백: 진행/중단 조건·빈 산출 트리거·`quality` 승격)·§9(라우터 의사코드).
픽스처: ZIP은 표준 라이브러리 `zipfile`로, OLE2 CFB(hwp5·doc·암호화 docx)는 이 파일이 직접 구성하는
최소 유효 컴파운드 파일 빌더(`_build_cfb`, 헤더+FAT+디렉터리+MiniFAT/미니스트림)로 만든다.
`SourceDocument` 봉투는 `tests/contracts/fixtures/source-document/001.json`에서 바이트·해시·힌트만
바꿔 쓴다(`tests/adapters/parse/test_hwpx.py`와 같은 패턴).
구성: `_build_cfb`/`_build_zip` — 합성 컨테이너 빌더; `_fetch_source_document` — fetch 잠정 출력
흉내; `_FakeBuilder`/`_FakeStage` — `router.StageBuilder` 구조적 대역; `_fake_parsed` — 최소 유효
`ParsedDocument`. `detect()` 직접 호출 테스트, `FormatDetectorStage` 병합 테스트, `ParseRouterStage`
폴백·부분 성공·budget·terminal-code 테스트로 구성한다.
불변식·주의: 후보 어댑터 출력을 라우터가 그대로 신뢰하는 현재 구현을 전제로 검증한다(03 계약 불변식
P-1~P-14 재검증은 이 WP 밖, DEFERRED).
검증 계층: 1층(여기서 검증). Docker·모델·GPU·네트워크 불필요.
"""

from __future__ import annotations

import asyncio
import io
import json
import struct
import zipfile
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from rag_platform.adapters.parse import format_detector as fd, router as rt
from rag_platform.contracts import common_types as ct
from rag_platform.contracts.parsed_document import Block, LineageRefs, ParsedDocument, ParserFingerprint
from rag_platform.contracts.source_document import SourceDocument
from rag_platform.sdk.hashing import blake3_hex, block_id
from rag_platform.sdk.stage import StageError

ROOT = Path(__file__).resolve().parents[3]
SOURCE_FIXTURE = ROOT / "tests" / "contracts" / "fixtures" / "source-document" / "001.json"

# ---------------------------------------------------------------------------------------------
# 합성 컨테이너 빌더 — OLE2 CFB(MiniFAT/미니스트림 포함)·ZIP. 벤더 라이브러리 없이 표준 라이브러리와
# `struct`만으로 [MS-CFB] 최소 유효 파일을 구성한다(단일 FAT 섹터, 섹터 512B로 제한된 소형 테스트 전용).
# ---------------------------------------------------------------------------------------------

_SECTOR = 512
_MINI = 64
_CUTOFF = 4096


def _cfb_dir_entry(name: str, object_type: int, start_sector: int, size: int) -> bytes:
    raw_name = name.encode("utf-16-le")
    name_len = len(raw_name) + 2
    block = bytearray(128)
    block[: len(raw_name)] = raw_name
    struct.pack_into("<H", block, 64, name_len)
    block[66] = object_type
    block[67] = 1
    struct.pack_into("<i", block, 68, -1)
    struct.pack_into("<i", block, 72, -1)
    struct.pack_into("<i", block, 76, -1)
    struct.pack_into("<I", block, 116, start_sector & 0xFFFFFFFF)
    struct.pack_into("<Q", block, 120, size)
    return bytes(block)


def _build_cfb(streams: dict[str, bytes]) -> bytes:  # noqa: PLR0912, PLR0915 - 단일 소형 파일 빌더, 분리하면 더 읽기 어렵다
    """최소 유효 OLE2 CFB 파일(버전 3, 섹터 512B, 단일 FAT 섹터)을 만든다.

    `_CUTOFF`(4096B) 미만 스트림은 MiniFAT/미니스트림 경로로, 그 이상은 일반 FAT 경로로 저장해
    `format_detector`의 두 읽기 경로를 모두 테스트가 실제로 통과하게 한다.
    """
    names = list(streams.keys())
    small = [n for n in names if len(streams[n]) < _CUTOFF]
    big = [n for n in names if len(streams[n]) >= _CUTOFF]

    mini_chain: list[int] = []
    mini_start: dict[str, int] = {}
    ministream_parts: list[bytes] = []
    cursor = 0
    for name in small:
        data = streams[name]
        n_sec = -(-len(data) // _MINI) if data else 0
        if n_sec == 0:
            mini_start[name] = 0xFFFFFFFE
            continue
        start = cursor
        mini_start[name] = start
        for i in range(n_sec):
            chunk = data[i * _MINI : (i + 1) * _MINI]
            ministream_parts.append(chunk + b"\x00" * (_MINI - len(chunk)))
            mini_chain.append(start + i + 1 if i + 1 < n_sec else 0xFFFFFFFE)
        cursor += n_sec
    ministream_bytes = b"".join(ministream_parts)
    minifat_bytes = b"".join(struct.pack("<I", v) for v in mini_chain)

    entries_per_sector = _SECTOR // 128
    n_dir_sectors = -(-(1 + len(names)) // entries_per_sector)

    def sectors_for(nbytes: int) -> int:
        return -(-nbytes // _SECTOR) if nbytes else 0

    n_minifat_sectors = sectors_for(len(minifat_bytes))
    n_ministream_sectors = sectors_for(len(ministream_bytes))

    layout: list[bytes] = [b""] * n_dir_sectors
    minifat_start = len(layout) if n_minifat_sectors else 0xFFFFFFFE
    padded_minifat = minifat_bytes + b"\x00" * (n_minifat_sectors * _SECTOR - len(minifat_bytes))
    layout.extend(padded_minifat[i * _SECTOR : (i + 1) * _SECTOR] for i in range(n_minifat_sectors))

    root_start = len(layout) if n_ministream_sectors else 0xFFFFFFFE
    root_size = len(ministream_bytes)
    padded_root = ministream_bytes + b"\x00" * (n_ministream_sectors * _SECTOR - len(ministream_bytes))
    layout.extend(padded_root[i * _SECTOR : (i + 1) * _SECTOR] for i in range(n_ministream_sectors))

    big_start: dict[str, int] = {}
    for name in big:
        data = streams[name]
        n_sec = sectors_for(len(data))
        big_start[name] = len(layout)
        padded = data + b"\x00" * (n_sec * _SECTOR - len(data))
        layout.extend(padded[i * _SECTOR : (i + 1) * _SECTOR] for i in range(n_sec))

    fat_sector_index = len(layout)
    if fat_sector_index + 1 > _SECTOR // 4:
        msg = "test helper only supports small fixtures (<=128 sectors)"
        raise ValueError(msg)

    fat = [0xFFFFFFFF] * (_SECTOR // 4)
    for i in range(n_dir_sectors):
        fat[i] = i + 1 if i + 1 < n_dir_sectors else 0xFFFFFFFE
    for i in range(n_minifat_sectors):
        fat[minifat_start + i] = minifat_start + i + 1 if i + 1 < n_minifat_sectors else 0xFFFFFFFE
    for i in range(n_ministream_sectors):
        fat[root_start + i] = root_start + i + 1 if i + 1 < n_ministream_sectors else 0xFFFFFFFE
    for name in big:
        n_sec = sectors_for(len(streams[name]))
        start = big_start[name]
        for i in range(n_sec):
            fat[start + i] = start + i + 1 if i + 1 < n_sec else 0xFFFFFFFE
    fat[fat_sector_index] = 0xFFFFFFFD
    fat_bytes = b"".join(struct.pack("<I", v) for v in fat)

    dir_entries = [_cfb_dir_entry("Root Entry", 5, root_start, root_size)]
    for name in names:
        start = mini_start[name] if name in small else big_start[name]
        dir_entries.append(_cfb_dir_entry(name, 2, start, len(streams[name])))
    while len(dir_entries) < n_dir_sectors * entries_per_sector:
        dir_entries.append(bytes(128))
    dir_bytes = b"".join(dir_entries)
    for i in range(n_dir_sectors):
        layout[i] = dir_bytes[i * _SECTOR : (i + 1) * _SECTOR]

    header = bytearray(512)
    header[0:8] = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
    struct.pack_into("<H", header, 24, 0x003E)
    struct.pack_into("<H", header, 26, 3)
    struct.pack_into("<H", header, 28, 0xFFFE)
    struct.pack_into("<H", header, 30, 9)
    struct.pack_into("<H", header, 32, 6)
    struct.pack_into("<I", header, 44, 1)
    struct.pack_into("<I", header, 48, 0)
    struct.pack_into("<I", header, 56, _CUTOFF)
    struct.pack_into("<I", header, 60, minifat_start)
    struct.pack_into("<I", header, 64, n_minifat_sectors)
    struct.pack_into("<I", header, 68, 0xFFFFFFFE)
    struct.pack_into("<I", header, 76, fat_sector_index)
    for i in range(1, 109):
        struct.pack_into("<I", header, 76 + i * 4, 0xFFFFFFFF)

    return bytes(header) + b"".join(layout) + fat_bytes


def _build_zip(entries: dict[str, bytes]) -> bytes:
    """`entries`(경로 → 내용)만 담은 최소 ZIP 아카이브."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, data in entries.items():
            zf.writestr(name, data)
    return buf.getvalue()


def _hwp5_file_header(*, compressed: bool, encrypted: bool, distribution: bool) -> bytes:
    flags = (int(compressed) << 0) | (int(encrypted) << 1) | (int(distribution) << 2)
    return b"HWP Document File" + b"\x00" * (32 - 17) + bytes([5, 0, 3, 0]) + struct.pack("<I", flags)


# ---------------------------------------------------------------------------------------------
# `SourceDocument` fetch 잠정 출력(detect 이전) 흉내
# ---------------------------------------------------------------------------------------------


def _fetch_source_document(
    data: bytes, *, resolved_uri: str = "s3://b/doc.bin", media_type_hint: str = ""
) -> SourceDocument:
    raw = json.loads(SOURCE_FIXTURE.read_text(encoding="utf-8"))
    digest = blake3_hex(data)
    raw["doc_version"] = raw["content_hash"] = digest
    raw["size_bytes"] = len(data)
    raw["artifact"] = {
        **raw["artifact"],
        "blake3": digest,
        "size_bytes": len(data),
        "media_type": media_type_hint or "application/octet-stream",
    }
    raw["metadata"] = {**raw["metadata"], "genre": None}
    raw["resolved_uri"] = raw["source_uri"] = resolved_uri
    raw["media_type"] = media_type_hint or "application/octet-stream"
    raw["format"] = "unknown"  # fetch 잠정값(힌트뿐)
    raw["format_confidence"] = 0.0
    raw["container_flags"] = {"encrypted": False, "distribution": False, "compressed": False}
    raw["detect_report"] = None
    return SourceDocument.model_validate(raw)


# ---------------------------------------------------------------------------------------------
# 가짜 `StageContext`(`sdk.context.StageContext` 구조적 대역)
# ---------------------------------------------------------------------------------------------


@dataclass
class _Ctx:
    data: bytes
    budget_ms: int | None = None

    def now(self) -> datetime:
        return datetime(2026, 9, 23, 9, 0, tzinfo=UTC)

    def source_bytes(self) -> bytes:
        return self.data

    def remaining_ms(self) -> int | None:
        return self.budget_ms


# ---------------------------------------------------------------------------------------------
# 가짜 후보 스테이지·빌더(`router.StageBuilder`와 구조적으로만 호환)
# ---------------------------------------------------------------------------------------------


@dataclass
class _FakeStage:
    """`outcome`이 `Exception`이면 던지고, 아니면 그대로 반환한다. `calls`로 호출 여부를 검증한다."""

    outcome: ParsedDocument | Exception
    calls: list[str] = field(default_factory=list)

    async def run(self, source: SourceDocument, _ctx: Any) -> ParsedDocument:
        self.calls.append(source.format.value)
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return self.outcome


@dataclass
class _FakeBuilder:
    stages: dict[str, _FakeStage]

    def build_stage(self, plugin_id: str, _config: dict[str, Any], _services: Any = None) -> Any:
        if plugin_id not in self.stages:
            raise KeyError(plugin_id)
        return self.stages[plugin_id]


def _fake_parsed(
    source: SourceDocument, *, plugin_id: str, text: str = "hello world", empty: bool = False
) -> ParsedDocument:
    doc_version = source.doc_version.root
    blocks: list[Block] = []
    if not empty:
        element_path = "/txt/para[0]"
        provenance = ct.Provenance(element_path=element_path, char_start=0, char_end=len(text), page=None, bbox=None)
        blocks = [
            Block(
                block_id=block_id(doc_version, element_path),
                type=ct.BlockType.paragraph,
                parent_block_id=None,
                ordinal=0,
                text=text,
                furniture=False,
                container=ct.BlockContainer.body,
                source=ct.BlockSource.text_layer,
                provenance=provenance,
            )
        ]
    return ParsedDocument(
        schema_version="1.0.0",
        schema_type="ParsedDocument",
        tenant_id=source.tenant_id,
        collection_id=source.collection_id,
        producer=ct.Producer(plugin_id=plugin_id, plugin_version="1.0.0", config_hash="0" * 64, image_digest=None),
        quality=ct.Quality.full,
        warnings=[],
        created_at="2026-09-23T09:00:00.000Z",
        lineage_refs=LineageRefs(source=source.artifact),
        document_id=source.document_id,
        doc_version=source.doc_version,
        source_ref=source.artifact,
        parser_fingerprint=ParserFingerprint(
            parser_id=plugin_id, parser_version="fake==1.0.0", sidecar_image_digest=None, profile_option="fake_standard"
        ),
        parser_chain=[plugin_id],
        source_kind=ct.SourceKind.flow,
        page_count=None,
        language="ko",
        blocks=blocks,
        text_length=sum(len(b.text) for b in blocks),
        block_count=len(blocks),
    )


def _run(coro: Any) -> Any:
    return asyncio.run(coro)


# ===================================================================================================
# `detect()` — 매직 바이트·컨테이너 내부 검사(§2.2·§2.3)
# ===================================================================================================


def test_detect_pdf_plain() -> None:
    result = fd.detect(b"%PDF-1.7\n" + b"filler" * 10)
    assert result.format == ct.SourceFormat.pdf
    assert result.format_confidence == 1.0
    assert result.container_flags.encrypted is False
    assert result.media_type == "application/pdf"


def test_detect_pdf_encrypted_trailer() -> None:
    result = fd.detect(b"%PDF-1.7\n...\n/Encrypt 5 0 R\n%%EOF")
    assert result.format == ct.SourceFormat.pdf
    assert result.container_flags.encrypted is True


def test_detect_zip_hwpx_via_mimetype() -> None:
    data = _build_zip({"mimetype": "application/hwp+zip", "Contents/content.hpf": "<x/>", "version.xml": "<v/>"})
    result = fd.detect(data)
    assert result.format == ct.SourceFormat.hwpx
    assert result.format_confidence == 1.0
    assert result.container_flags.compressed is True


def test_detect_zip_hwpx_via_hpf_without_mimetype() -> None:
    data = _build_zip({"Contents/content.hpf": "<x/>", "version.xml": "<v/>"})
    result = fd.detect(data)
    assert result.format == ct.SourceFormat.hwpx


def test_detect_zip_hwpx_manifest_encrypted() -> None:
    data = _build_zip(
        {
            "mimetype": "application/hwp+zip",
            "Contents/content.hpf": "<x/>",
            "version.xml": "<v/>",
            "META-INF/manifest.xml": "<manifest><encryption-data/></manifest>",
        }
    )
    result = fd.detect(data)
    assert result.format == ct.SourceFormat.hwpx
    assert result.container_flags.encrypted is True


def test_detect_zip_docx() -> None:
    data = _build_zip({"[Content_Types].xml": "<t/>", "word/document.xml": "<d/>"})
    result = fd.detect(data)
    assert result.format == ct.SourceFormat.docx
    assert result.format_confidence == 1.0


def test_detect_zip_odt() -> None:
    data = _build_zip({"mimetype": "application/vnd.oasis.opendocument.text"})
    result = fd.detect(data)
    assert result.format == ct.SourceFormat.odt


def test_detect_zip_unknown_entries_raises_unsupported_format() -> None:
    data = _build_zip({"xl/workbook.xml": "<w/>"})
    with pytest.raises(StageError) as excinfo:
        fd.detect(data)
    assert excinfo.value.code == "parse.unsupported_format"


def test_detect_zip_bad_archive_raises_corrupt_container() -> None:
    with pytest.raises(StageError) as excinfo:
        fd.detect(b"PK\x03\x04" + b"not a real zip payload")
    assert excinfo.value.code == "parse.corrupt_container"


def test_detect_zip_empty_archive_raises_unsupported_format() -> None:
    with pytest.raises(StageError) as excinfo:
        fd.detect(b"PK\x05\x06" + b"\x00" * 18)
    assert excinfo.value.code == "parse.unsupported_format"


def test_detect_ole_hwp5_via_minifat_stream() -> None:
    """`FileHeader`(<4096B)는 MiniFAT/미니스트림 경로로 저장된다 — 실물 HWP 5.0과 같은 크기대."""
    streams = {"FileHeader": _hwp5_file_header(compressed=True, encrypted=False, distribution=False)}
    data = _build_cfb(streams)
    result = fd.detect(data)
    assert result.format == ct.SourceFormat.hwp5
    assert result.format_confidence == 1.0
    assert result.container_flags.compressed is True
    assert result.container_flags.encrypted is False
    assert result.container_flags.hwp_version == "5.0.3.0"


def test_detect_ole_hwp5_view_text_flag_mismatch_logged() -> None:
    streams = {
        "FileHeader": _hwp5_file_header(compressed=False, encrypted=True, distribution=False),
        "ViewText": b"x" * 10,
    }
    data = _build_cfb(streams)
    result = fd.detect(data)
    assert result.format == ct.SourceFormat.hwp5
    signals = [str(s.root) for s in result.detect_report.signals]
    assert "ole:ViewText" in signals
    assert "ole:ViewText_flag_mismatch" in signals


def test_detect_ole_doc() -> None:
    data = _build_cfb({"WordDocument": b"\x00" * 100})
    result = fd.detect(data)
    assert result.format == ct.SourceFormat.doc
    assert result.format_confidence == 1.0


def test_detect_ole_encrypted_docx() -> None:
    data = _build_cfb({"EncryptedPackage": b"\x01" * 50, "EncryptionInfo": b"\x02" * 20})
    result = fd.detect(data)
    assert result.format == ct.SourceFormat.docx
    assert result.format_confidence == 0.7
    assert result.container_flags.encrypted is True


def test_detect_ole_unknown_stream_raises_unsupported_format() -> None:
    data = _build_cfb({"SomeOtherStream": b"x" * 10})
    with pytest.raises(StageError) as excinfo:
        fd.detect(data)
    assert excinfo.value.code == "parse.unsupported_format"


def test_detect_ole_truncated_header_raises_corrupt_container() -> None:
    with pytest.raises(StageError) as excinfo:
        fd.detect(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\x00" * 10)
    assert excinfo.value.code == "parse.corrupt_container"


def test_detect_rtf() -> None:
    result = fd.detect(b"{\\rtf1\\ansi hello}")
    assert result.format == ct.SourceFormat.rtf
    assert result.format_confidence == 1.0


def test_detect_hwp3_legacy_signature() -> None:
    result = fd.detect(b"HWP Document File V3.00" + b"\x00" * 40)
    assert result.format == ct.SourceFormat.hwp3
    assert result.format_confidence == 1.0


def test_detect_binary_unknown_raises_unsupported_format() -> None:
    with pytest.raises(StageError) as excinfo:
        fd.detect(bytes(range(256)))
    assert excinfo.value.code == "parse.unsupported_format"


# ===================================================================================================
# `detect()` — 텍스트 계열(§2.4)과 신뢰도(§2.5)
# ===================================================================================================


def test_detect_json_small() -> None:
    result = fd.detect(b'{"a": 1, "b": [1, 2, 3]}')
    assert result.format == ct.SourceFormat.json
    assert result.format_confidence == 0.9


def test_detect_json_oversized_uses_probe_confidence() -> None:
    payload = b'{"a": "' + b"x" * (17 * 1024 * 1024) + b'"}'
    result = fd.detect(payload)
    assert result.format == ct.SourceFormat.json
    assert result.format_confidence == 0.8


def test_detect_html_root_marker() -> None:
    result = fd.detect(b"<!DOCTYPE html><html><head></head><body>hi</body></html>")
    assert result.format == ct.SourceFormat.html
    assert result.format_confidence == 0.8


def test_detect_markdown_atx_heading_signal() -> None:
    result = fd.detect("# 제목\n\n본문 문단입니다.\n".encode())
    assert result.format == ct.SourceFormat.md
    assert result.format_confidence == 0.6


def test_detect_markdown_frontmatter_signal() -> None:
    result = fd.detect(b"---\ntitle: x\n---\n\nbody text\n")
    assert result.format == ct.SourceFormat.md


def test_detect_markdown_hint_only_no_bonus() -> None:
    result = fd.detect(b"just plain prose with no markdown syntax at all here", hint_extension=".md")
    assert result.format == ct.SourceFormat.md
    assert result.format_confidence == 0.5


def test_detect_plain_txt_fallback() -> None:
    result = fd.detect("일반 텍스트 문단입니다.".encode())
    assert result.format == ct.SourceFormat.txt
    assert result.format_confidence == 0.6


def test_detect_hint_agreement_bonus_capped_at_one() -> None:
    result = fd.detect(b'{"a": 1}', hint_media_type="application/json")
    assert result.format_confidence == 1.0
    assert result.detect_report.hint_agrees is True


def test_detect_hint_disagreement_recorded() -> None:
    result = fd.detect(b"plain text body", hint_media_type="application/json")
    assert result.format == ct.SourceFormat.txt
    assert result.detect_report.hint_agrees is False


def test_detect_no_hint_leaves_hint_agrees_none() -> None:
    result = fd.detect(b"plain text body")
    assert result.detect_report.hint_agrees is None


# ===================================================================================================
# `FormatDetectorStage` — `SourceDocument` 병합
# ===================================================================================================


def test_format_detector_stage_merges_detection_into_source_document() -> None:
    data = _build_zip({"mimetype": "application/hwp+zip", "Contents/content.hpf": "<x/>", "version.xml": "<v/>"})
    source = _fetch_source_document(data, resolved_uri="s3://b/doc.hwpx")
    ctx = _Ctx(data=data)
    out = _run(fd.FormatDetectorStage().run(source, ctx))
    assert out.format == ct.SourceFormat.hwpx
    assert out.format_confidence == 1.0
    assert out.media_type.root == "application/hwp+zip"
    assert out.producer.plugin_id.root == "parser.format_detector"
    assert out.tenant_id == source.tenant_id  # 봉투 필드는 fetch 출력에서 복사


def test_format_detector_stage_extension_hint_from_resolved_uri() -> None:
    data = b"plain text with no markdown syntax whatsoever in it at all"
    source = _fetch_source_document(data, resolved_uri="s3://b/notes.md")
    ctx = _Ctx(data=data)
    out = _run(fd.FormatDetectorStage().run(source, ctx))
    assert out.format == ct.SourceFormat.md
    assert out.format_confidence == 0.5


# ===================================================================================================
# `ParseRouterStage` — 후보 체인·폴백·부분 성공(§4.1·§6·§7.2)
# ===================================================================================================


def test_router_first_candidate_success_keeps_quality() -> None:
    data = _build_zip({"mimetype": "application/hwp+zip", "Contents/content.hpf": "<x/>", "version.xml": "<v/>"})
    source = _fetch_source_document(data)
    ctx = _Ctx(data=data)
    hwpx_source = source.model_copy(update={"format": ct.SourceFormat.hwpx})
    parsed_stub = _fake_parsed(hwpx_source, plugin_id="parser.hwpx_python_hwpx")
    builder = _FakeBuilder({"parser.hwpx_python_hwpx": _FakeStage(outcome=parsed_stub)})
    stage = rt.ParseRouterStage(builder)
    out = _run(stage.run(source, ctx))
    assert out.quality == ct.Quality.full
    assert [p.root for p in out.parser_chain] == ["parser.hwpx_python_hwpx"]


def test_router_fallback_to_second_candidate_marks_degraded() -> None:
    data = _build_cfb({"FileHeader": _hwp5_file_header(compressed=True, encrypted=False, distribution=False)})
    source = _fetch_source_document(data)
    ctx = _Ctx(data=data)
    fake_source = source.model_copy(update={"format": ct.SourceFormat.hwp5})
    ok = _fake_parsed(fake_source, plugin_id="parser.hwp5_unhwp")
    builder = _FakeBuilder(
        {
            "parser.hwp5_java_sidecar": _FakeStage(
                outcome=StageError("parse.conversion_failed", stage="parse", plugin_id="parser.hwp5_java_sidecar")
            ),
            "parser.hwp5_unhwp": _FakeStage(outcome=ok),
        }
    )
    stage = rt.ParseRouterStage(builder)
    out = _run(stage.run(source, ctx))
    assert out.quality == ct.Quality.degraded
    assert [p.root for p in out.parser_chain] == ["parser.hwp5_java_sidecar", "parser.hwp5_unhwp"]


def test_router_non_retryable_error_stops_chain_immediately() -> None:
    route_table = {ct.SourceFormat.txt: ("fake.a", "fake.b")}
    data = b"plain text body for routing"
    source = _fetch_source_document(data)
    ctx = _Ctx(data=data)
    stage_b = _FakeStage(outcome=_fake_parsed(source, plugin_id="fake.b"))
    builder = _FakeBuilder(
        {
            "fake.a": _FakeStage(outcome=StageError("parse.document_encrypted", stage="parse", plugin_id="fake.a")),
            "fake.b": stage_b,
        }
    )
    stage = rt.ParseRouterStage(builder, route_table=route_table)
    with pytest.raises(StageError) as excinfo:
        _run(stage.run(source, ctx))
    assert excinfo.value.code == "parse.document_encrypted"
    assert stage_b.calls == []  # 두 번째 후보는 시도되지 않는다


def test_router_contract_violation_stops_chain() -> None:
    route_table = {ct.SourceFormat.txt: ("fake.a", "fake.b")}
    data = b"plain text body for routing two"
    source = _fetch_source_document(data)
    ctx = _Ctx(data=data)
    stage_b = _FakeStage(outcome=_fake_parsed(source, plugin_id="fake.b"))
    builder = _FakeBuilder(
        {
            "fake.a": _FakeStage(outcome=StageError("contract.violation", stage="parse", plugin_id="fake.a")),
            "fake.b": stage_b,
        }
    )
    stage = rt.ParseRouterStage(builder, route_table=route_table)
    with pytest.raises(StageError) as excinfo:
        _run(stage.run(source, ctx))
    assert excinfo.value.code == "contract.violation"
    assert stage_b.calls == []


def test_router_chain_exhausted_raises_conversion_failed_with_cause() -> None:
    route_table = {ct.SourceFormat.txt: ("fake.a", "fake.b")}
    data = b"plain text body for routing three"
    source = _fetch_source_document(data)
    ctx = _Ctx(data=data)
    err_b = StageError("parse.conversion_failed", stage="parse", plugin_id="fake.b", detail="fake.b failed")
    builder = _FakeBuilder(
        {
            "fake.a": _FakeStage(outcome=StageError("parse.conversion_failed", stage="parse", plugin_id="fake.a")),
            "fake.b": _FakeStage(outcome=err_b),
        }
    )
    stage = rt.ParseRouterStage(builder, route_table=route_table)
    with pytest.raises(StageError) as excinfo:
        _run(stage.run(source, ctx))
    assert excinfo.value.code == "parse.conversion_failed"
    assert excinfo.value.plugin_id == "fake.b"
    assert excinfo.value.cause is err_b


def test_router_empty_output_not_last_falls_back() -> None:
    route_table = {ct.SourceFormat.txt: ("fake.a", "fake.b")}
    data = b"plain text body for routing four"
    source = _fetch_source_document(data)
    ctx = _Ctx(data=data)
    empty_out = _fake_parsed(source, plugin_id="fake.a", empty=True)
    real_out = _fake_parsed(source, plugin_id="fake.b")
    builder = _FakeBuilder({"fake.a": _FakeStage(outcome=empty_out), "fake.b": _FakeStage(outcome=real_out)})
    stage = rt.ParseRouterStage(builder, route_table=route_table)
    out = _run(stage.run(source, ctx))
    assert [p.root for p in out.parser_chain] == ["fake.a", "fake.b"]
    assert out.quality == ct.Quality.degraded


def test_router_empty_output_last_candidate_accepted_as_full() -> None:
    route_table = {ct.SourceFormat.txt: ("fake.a",)}
    data = b"plain text body for routing five"
    source = _fetch_source_document(data)
    ctx = _Ctx(data=data)
    empty_out = _fake_parsed(source, plugin_id="fake.a", empty=True)
    builder = _FakeBuilder({"fake.a": _FakeStage(outcome=empty_out)})
    stage = rt.ParseRouterStage(builder, route_table=route_table)
    out = _run(stage.run(source, ctx))
    assert out.quality == ct.Quality.full
    assert out.block_count == 0


def test_router_missing_candidate_falls_through_to_unsupported_format() -> None:
    """`docx`의 `needs_model` 자리: 후보가 등록되지 않으면 §4.1 3단계로 건너뛰어 후보 0개가 된다."""
    data = _build_zip({"[Content_Types].xml": "<t/>", "word/document.xml": "<d/>"})
    source = _fetch_source_document(data)
    ctx = _Ctx(data=data)
    builder = _FakeBuilder({})
    stage = rt.ParseRouterStage(builder)
    with pytest.raises(StageError) as excinfo:
        _run(stage.run(source, ctx))
    assert excinfo.value.code == "parse.unsupported_format"


def test_router_terminal_code_route_for_hwp3() -> None:
    data = b"HWP Document File V3.00" + b"\x00" * 40
    source = _fetch_source_document(data)
    ctx = _Ctx(data=data)
    builder = _FakeBuilder({})
    stage = rt.ParseRouterStage(builder)
    with pytest.raises(StageError) as excinfo:
        _run(stage.run(source, ctx))
    assert excinfo.value.code == "parse.unsupported_variant"


def test_router_insufficient_budget_raises_conversion_failed() -> None:
    route_table = {ct.SourceFormat.txt: ("fake.a",)}
    data = b"plain text body for routing six"
    source = _fetch_source_document(data)
    ctx = _Ctx(data=data, budget_ms=100)  # < _MIN_CANDIDATE_BUDGET_MS
    stage_a = _FakeStage(outcome=_fake_parsed(source, plugin_id="fake.a"))
    builder = _FakeBuilder({"fake.a": stage_a})
    stage = rt.ParseRouterStage(builder, route_table=route_table)
    with pytest.raises(StageError) as excinfo:
        _run(stage.run(source, ctx))
    assert excinfo.value.code == "parse.conversion_failed"
    assert stage_a.calls == []


def test_router_detect_unknown_format_propagates_before_routing() -> None:
    """라우터는 `detect()`가 던진 `parse.unsupported_format`을 그대로 전파한다(§9: "unknown은 여기서 종료")."""
    data = bytes(range(256))
    source = _fetch_source_document(data)
    ctx = _Ctx(data=data)
    stage = rt.ParseRouterStage(_FakeBuilder({}))
    with pytest.raises(StageError) as excinfo:
        _run(stage.run(source, ctx))
    assert excinfo.value.code == "parse.unsupported_format"


def test_router_fingerprint_and_capabilities_are_stable() -> None:
    stage = rt.ParseRouterStage(_FakeBuilder({}))
    assert stage.capabilities().isolation_modes == [ct.IsolationMode.in_process]
    assert stage.fingerprint() == stage.fingerprint()
