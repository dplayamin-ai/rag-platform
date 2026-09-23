"""`parser.format_detector` — `detect` 서브스테이지: 매직 바이트로 `SourceFormat`을 판별한다.

설계 근거: 04-pipelines/03 §2(판별 알고리즘 전체)·§2.1(신호 우선순위: 매직 바이트 → 컨테이너 내부 검사 →
선언 콘텐츠 타입 → 확장자)·§2.2(패밀리·시그니처)·§2.3(컨테이너 내부 검사 규칙)·§2.4(텍스트 계열 판별)·
§2.5(신뢰도 표), 바이블 §4.2 `detect` 행·§5.7 `SourceFormat` 철자·오류 코드 카탈로그
(`parse.unsupported_format`·`parse.corrupt_container`), ADR-0036.
구성: `detect()` — 순수 판별 함수(바이트 → `DetectionResult`); `FormatDetectorStage` — 5멤버 스테이지
래퍼(`run`/`detect_source`, `SourceDocument` → `SourceDocument`, `producer` 지문 포함). ZIP은
`zipfile`(중앙 디렉터리)로, OLE2 CFB(HWP 5.0·DOC·암호화 OOXML)는 벤더 의존 없이 직접 구현한 최소
FAT/MiniFAT 리더로 스트림 이름·내용을 읽는다.
불변식·주의: `unknown`·손상 컨테이너는 이 함수 안에서 `StageError(parse.unsupported_format |
parse.corrupt_container)`로 종료한다 — 호출자(`router.py`)는 정상 반환된 `format`이 언제나 지원 포맷
13종 중 하나(`unknown` 제외)임을 가정할 수 있다. 콘텐츠 문자열은 어떤 신호·오류 메시지에도 담지 않는다
(00 I-16). OLE 리더는 `FileHeader` 비트 위치를 문서가 "확인 필요"로 표시한 값 그대로 구현했다(미해결).
검증 계층: 1층(여기서 검증) — `tests/adapters/parse/test_router.py`. Docker·모델·GPU·네트워크 불필요.
"""

from __future__ import annotations

import inspect
import json
import re
import struct
import zipfile
from dataclasses import dataclass
from datetime import UTC
from io import BytesIO
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict

from rag_platform.contracts import common_types as ct
from rag_platform.contracts.source_document import Candidate, ContainerFlags, DetectReport, Signal
from rag_platform.sdk.hashing import hash_of
from rag_platform.sdk.stage import StageError

if TYPE_CHECKING:
    from datetime import datetime

    from rag_platform.contracts.source_document import SourceDocument

__all__ = [
    "FORMAT_MEDIA_TYPE",
    "PLUGIN_ID",
    "PLUGIN_VERSION",
    "DetectionResult",
    "FormatDetectorConfig",
    "FormatDetectorStage",
    "detect",
]

PLUGIN_ID = "parser.format_detector"
PLUGIN_VERSION = "0.1.0"

# §5.7 오류 코드 카탈로그 철자 정본(이 모듈에서 raise하는 종결 코드).
_UNSUPPORTED_FORMAT = "parse.unsupported_format"
_CORRUPT_CONTAINER = "parse.corrupt_container"
_CONVERSION_FAILED = "parse.conversion_failed"

# 04-pipelines/03 §2.1: 신호 4개 고정 우선순위. 매직 바이트·컨테이너 내부 검사가 확정하면 힌트·확장자는
# 동점 해소·기록용(hint_agrees)으로만 쓴다.
_HEADER_PROBE = 1024
_TEXT_PROBE = 65536
_MAX_INSPECT_BYTES = 1024 * 1024  # §2.6 안전 한계: 판정용 항목 각 1MiB
_JSON_FULL_PARSE_LIMIT = 16 * 1024 * 1024
_MD_LIST_LINK_RATIO = 0.05
_HINT_BONUS = 0.1
_MAX_ZIP_ENTRIES = 10_000
_MAX_ZIP_UNCOMPRESSED_TOTAL = 1024**3
_MAX_ZIP_RATIO = 100

_PDF_MAGIC = b"%PDF-"
_ZIP_MAGIC = b"PK\x03\x04"
_ZIP_EMPTY_MAGIC = b"PK\x05\x06"
_OLE_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
_RTF_MAGIC = b"{\\rtf"
_HWP3_MAGIC = b"HWP Document File V3.00"  # 04-pipelines/03 §2.2: 시그니처 원문 확인 필요(as of 2026-09)
_HTML_MARKERS = (b"<!doctype html", b"<html", b"<head", b"<body")

_HWPX_MIMETYPES = frozenset({"application/hwp+zip", "application/hwpml-package+xml", "application/vnd.hancom.hwpx"})
_ODT_MIMETYPE = "application/vnd.oasis.opendocument.text"
_MANIFEST_ENTRY = "META-INF/manifest.xml"
_HWPX_HPF_ENTRY = "Contents/content.hpf"
_HWPX_VERSION_ENTRY = "version.xml"
_OOXML_CONTENT_TYPES = "[Content_Types].xml"
_OOXML_DOCUMENT_ENTRY = "word/document.xml"

_HWP5_STREAM = "FileHeader"
_DOC_STREAM = "WordDocument"
_ENCRYPTED_PACKAGE_STREAM = "EncryptedPackage"
_ENCRYPTION_INFO_STREAM = "EncryptionInfo"
_VIEWTEXT_STREAM = "ViewText"
_HWP5_SIGNATURE = b"HWP Document File"

_ATX_HEADING = re.compile(r"^ {0,3}#{1,6}[ \t]", re.MULTILINE)
_FENCE = re.compile(r"^ {0,3}(```|~~~)", re.MULTILINE)
_MD_LIST_OR_LINK = re.compile(r"^\s*([-*+]\s|\d+\.\s)|\[[^\]]+\]\([^)]+\)")

#: detect 출력이 재기입하는 `media_type`(04-pipelines/03 §2 대응표). `unknown`은 없다 — `detect()`가
#: 그 전에 예외를 던진다.
FORMAT_MEDIA_TYPE: dict[ct.SourceFormat, str] = {
    ct.SourceFormat.hwpx: "application/hwp+zip",
    ct.SourceFormat.hwp5: "application/x-hwp",
    ct.SourceFormat.hwp3: "application/x-hwp3",
    ct.SourceFormat.pdf: "application/pdf",
    ct.SourceFormat.docx: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ct.SourceFormat.doc: "application/msword",
    ct.SourceFormat.rtf: "application/rtf",
    ct.SourceFormat.odt: "application/vnd.oasis.opendocument.text",
    ct.SourceFormat.html: "text/html",
    ct.SourceFormat.txt: "text/plain",
    ct.SourceFormat.md: "text/markdown",
    ct.SourceFormat.json: "application/json",
}

_MEDIA_TYPE_TO_FORMAT: dict[str, ct.SourceFormat] = {
    "application/pdf": ct.SourceFormat.pdf,
    "application/hwp+zip": ct.SourceFormat.hwpx,
    "application/hwpml-package+xml": ct.SourceFormat.hwpx,
    "application/vnd.hancom.hwpx": ct.SourceFormat.hwpx,
    "application/x-hwp": ct.SourceFormat.hwp5,
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ct.SourceFormat.docx,
    "application/msword": ct.SourceFormat.doc,
    "application/rtf": ct.SourceFormat.rtf,
    "text/rtf": ct.SourceFormat.rtf,
    "application/vnd.oasis.opendocument.text": ct.SourceFormat.odt,
    "text/html": ct.SourceFormat.html,
    "application/xhtml+xml": ct.SourceFormat.html,
    "text/plain": ct.SourceFormat.txt,
    "text/markdown": ct.SourceFormat.md,
    "application/json": ct.SourceFormat.json,
}

_EXTENSION_TO_FORMAT: dict[str, ct.SourceFormat] = {
    ".hwpx": ct.SourceFormat.hwpx,
    ".hwp": ct.SourceFormat.hwp5,
    ".pdf": ct.SourceFormat.pdf,
    ".docx": ct.SourceFormat.docx,
    ".doc": ct.SourceFormat.doc,
    ".rtf": ct.SourceFormat.rtf,
    ".odt": ct.SourceFormat.odt,
    ".html": ct.SourceFormat.html,
    ".htm": ct.SourceFormat.html,
    ".txt": ct.SourceFormat.txt,
    ".md": ct.SourceFormat.md,
    ".markdown": ct.SourceFormat.md,
    ".json": ct.SourceFormat.json,
}

# CFB(OLE2) 상수 — [MS-CFB] 2.1·2.2. FREE/END/FAT/DIF는 FAT 항목의 예약값, 나머지는 128B 디렉터리
# 엔트리의 고정 오프셋이다.
_CFB_HEADER_SIZE = 512
_CFB_DIR_ENTRY_SIZE = 128
_CFB_HEADER_DIFAT_ENTRIES = 109
_SECTOR_FREE = 0xFFFFFFFF
_SECTOR_END = 0xFFFFFFFE
_SECTOR_DIF = 0xFFFFFFFC
_ENTRY_UNALLOCATED = 0
_ENTRY_STREAM = 2
_ENTRY_ROOT_STORAGE = 5


@dataclass(frozen=True)
class DetectionResult:
    """`detect()`의 순수 반환값 — 계약 `SourceDocument`의 판정 필드 다섯 개에 그대로 대응한다."""

    media_type: str
    format: ct.SourceFormat
    format_confidence: float
    container_flags: ContainerFlags
    detect_report: DetectReport


def _hint_format(hint_media_type: str | None, hint_extension: str | None) -> ct.SourceFormat | None:
    """선언 콘텐츠 타입(신호 3) 우선, 없으면 확장자(신호 4)로 힌트 포맷을 추정한다(04-pipelines/03 §2.1)."""
    if hint_media_type:
        base = hint_media_type.split(";", 1)[0].strip().lower()
        resolved = _MEDIA_TYPE_TO_FORMAT.get(base)
        if resolved is not None:
            return resolved
    if hint_extension:
        ext = hint_extension.lower()
        if not ext.startswith("."):
            ext = f".{ext}"
        return _EXTENSION_TO_FORMAT.get(ext)
    return None


@dataclass(frozen=True)
class _Hints:
    """신호 3(선언 콘텐츠 타입)·신호 4(확장자) 한 쌍 — `_finalize`의 인자 수를 줄이는 묶음일 뿐이다."""

    media_type: str | None
    extension: str | None


def _finalize(
    fmt: ct.SourceFormat,
    confidence: float,
    flags: ContainerFlags,
    signals: list[str],
    hints: _Hints,
    *,
    allow_bonus: bool,
) -> DetectionResult:
    """신호 목록·힌트 일치를 `DetectReport`로 조립하거나, `unknown`이면 종결 코드로 예외를 던진다."""
    if fmt == ct.SourceFormat.unknown:
        detail = "; ".join(signals) if signals else "no recognizable signature"
        raise StageError(_UNSUPPORTED_FORMAT, stage="parse", plugin_id=PLUGIN_ID, detail=detail)
    hint_fmt = _hint_format(hints.media_type, hints.extension)
    hint_agrees = None if hint_fmt is None else hint_fmt == fmt
    if allow_bonus and hint_agrees:
        confidence = min(1.0, confidence + _HINT_BONUS)
    report = DetectReport(
        signals=[Signal(s) for s in (signals or ["none"])],
        hint_media_type=hints.media_type,
        hint_agrees=hint_agrees,
        candidates=[Candidate(format=fmt, confidence=confidence)],
    )
    return DetectionResult(
        media_type=FORMAT_MEDIA_TYPE[fmt],
        format=fmt,
        format_confidence=confidence,
        container_flags=flags,
        detect_report=report,
    )


def _read_zip_entry(zf: zipfile.ZipFile, name: str) -> bytes:
    """이름이 있는 항목만 개별로 풀되(§2.3), 판정용 항목 1MiB 상한(§2.6)을 넘으면 손상으로 취급한다."""
    info = zf.getinfo(name)
    if info.file_size > _MAX_INSPECT_BYTES:
        msg = f"zip entry {name!r} exceeds inspection limit ({_MAX_INSPECT_BYTES} bytes)"
        raise StageError(_CORRUPT_CONTAINER, stage="parse", plugin_id=PLUGIN_ID, detail=msg)
    try:
        return zf.read(name)
    except (zipfile.BadZipFile, RuntimeError, KeyError) as exc:
        msg = f"zip entry {name!r} unreadable: {exc}"
        raise StageError(_CORRUPT_CONTAINER, stage="parse", plugin_id=PLUGIN_ID, detail=msg) from exc


def _check_zip_bomb(zf: zipfile.ZipFile, names: list[str]) -> None:
    """항목 수·펼친 총량·압축비 상한(§2.6 "ZIP 폭탄")을 넘으면 `parse.corrupt_container`."""
    if len(names) > _MAX_ZIP_ENTRIES:
        msg = f"zip entry count {len(names)} exceeds limit {_MAX_ZIP_ENTRIES}"
        raise StageError(_CORRUPT_CONTAINER, stage="parse", plugin_id=PLUGIN_ID, detail=msg)
    total = 0
    for info in zf.infolist():
        total += info.file_size
        if info.compress_size > 0 and info.file_size / info.compress_size > _MAX_ZIP_RATIO:
            msg = f"zip entry {info.filename!r} exceeds compression ratio limit {_MAX_ZIP_RATIO}"
            raise StageError(_CORRUPT_CONTAINER, stage="parse", plugin_id=PLUGIN_ID, detail=msg)
    if total > _MAX_ZIP_UNCOMPRESSED_TOTAL:
        msg = f"zip uncompressed total {total} exceeds limit {_MAX_ZIP_UNCOMPRESSED_TOTAL}"
        raise StageError(_CORRUPT_CONTAINER, stage="parse", plugin_id=PLUGIN_ID, detail=msg)


def _hwpx_flags(zf: zipfile.ZipFile, names: list[str], signals: list[str]) -> ContainerFlags:
    """HWPX `container_flags` — `META-INF/manifest.xml`의 암호화 항목 유무만 판정(§2.3)."""
    encrypted = False
    if _MANIFEST_ENTRY in names:
        manifest = _read_zip_entry(zf, _MANIFEST_ENTRY)
        if b"encryption-data" in manifest:
            encrypted = True
            signals.append("zip:manifest_encrypted")
    return ContainerFlags(encrypted=encrypted, distribution=False, compressed=True)


def _zip_detect(data: bytes, signals: list[str]) -> tuple[ct.SourceFormat, ContainerFlags]:
    """ZIP 패밀리(§2.2 표) — 중앙 디렉터리 항목 이름과 `mimetype` 내용으로 hwpx/docx/odt를 가른다."""
    try:
        zf = zipfile.ZipFile(BytesIO(data))
        names = zf.namelist()
    except zipfile.BadZipFile as exc:
        msg = f"corrupt ZIP central directory: {exc}"
        raise StageError(_CORRUPT_CONTAINER, stage="parse", plugin_id=PLUGIN_ID, detail=msg) from exc
    _check_zip_bomb(zf, names)
    signals.append("zip:central_directory")
    if "mimetype" in names:
        raw_mimetype = _read_zip_entry(zf, "mimetype").decode("ascii", errors="replace").strip()
        signals.append(f"zip:mimetype={raw_mimetype}")
        if raw_mimetype in _HWPX_MIMETYPES:
            return ct.SourceFormat.hwpx, _hwpx_flags(zf, names, signals)
        if raw_mimetype == _ODT_MIMETYPE:
            return ct.SourceFormat.odt, ContainerFlags(encrypted=False, distribution=False, compressed=True)
        return ct.SourceFormat.unknown, ContainerFlags(encrypted=False, distribution=False, compressed=False)
    if _HWPX_HPF_ENTRY in names and _HWPX_VERSION_ENTRY in names:
        signals.append(f"zip:entry={_HWPX_HPF_ENTRY}")
        signals.append(f"zip:entry={_HWPX_VERSION_ENTRY}")
        return ct.SourceFormat.hwpx, _hwpx_flags(zf, names, signals)
    if _OOXML_CONTENT_TYPES in names and _OOXML_DOCUMENT_ENTRY in names:
        signals.append(f"zip:entry={_OOXML_CONTENT_TYPES}")
        signals.append(f"zip:entry={_OOXML_DOCUMENT_ENTRY}")
        return ct.SourceFormat.docx, ContainerFlags(encrypted=False, distribution=False, compressed=True)
    signals.append("zip:no_known_entry")
    return ct.SourceFormat.unknown, ContainerFlags(encrypted=False, distribution=False, compressed=False)


# ---------------------------------------------------------------------------------------------
# OLE2 CFB(Compound File Binary) 최소 리더 — [MS-CFB]. 스트림 이름으로 `FileHeader`/`WordDocument`/
# `EncryptedPackage`+`EncryptionInfo`만 찾아 내용을 읽는다(디렉터리 트리 순회는 하지 않고 평탄 스캔).
# ---------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class _CfbLayout:
    """CFB 헤더에서 뽑은 섹터·FAT·MiniFAT 위치표([MS-CFB] 2.2)."""

    sector_size: int
    mini_sector_size: int
    num_fat_sectors: int
    dir_start: int
    mini_fat_start: int
    num_mini_fat_sectors: int
    mini_stream_cutoff: int
    difat_start: int
    num_difat_sectors: int
    header_difat: tuple[int, ...]


@dataclass(frozen=True)
class _CfbEntry:
    """CFB 디렉터리 엔트리 하나(이름·타입·시작 섹터·크기만; 트리 위치는 쓰지 않는다)."""

    name: str
    object_type: int
    start_sector: int
    size: int


def _cfb_layout(data: bytes) -> _CfbLayout:
    """512B 헤더를 파싱한다([MS-CFB] 2.2 고정 오프셋)."""
    if len(data) < _CFB_HEADER_SIZE:
        msg = "OLE header truncated"
        raise ValueError(msg)
    sector_shift = struct.unpack_from("<H", data, 30)[0]
    mini_sector_shift = struct.unpack_from("<H", data, 32)[0]
    num_fat_sectors = struct.unpack_from("<I", data, 44)[0]
    dir_start = struct.unpack_from("<I", data, 48)[0]
    mini_stream_cutoff = struct.unpack_from("<I", data, 56)[0]
    mini_fat_start = struct.unpack_from("<I", data, 60)[0]
    num_mini_fat_sectors = struct.unpack_from("<I", data, 64)[0]
    difat_start = struct.unpack_from("<I", data, 68)[0]
    num_difat_sectors = struct.unpack_from("<I", data, 72)[0]
    header_difat = struct.unpack_from(f"<{_CFB_HEADER_DIFAT_ENTRIES}I", data, 76)
    return _CfbLayout(
        sector_size=1 << sector_shift,
        mini_sector_size=1 << mini_sector_shift,
        num_fat_sectors=num_fat_sectors,
        dir_start=dir_start,
        mini_fat_start=mini_fat_start,
        num_mini_fat_sectors=num_mini_fat_sectors,
        mini_stream_cutoff=mini_stream_cutoff,
        difat_start=difat_start,
        num_difat_sectors=num_difat_sectors,
        header_difat=header_difat,
    )


def _cfb_sector(data: bytes, layout: _CfbLayout, index: int) -> bytes:
    """섹터 `index`의 원문 바이트(헤더는 섹터 -1 자리를 차지하므로 오프셋은 `(index+1)*sector_size`)."""
    offset = (index + 1) * layout.sector_size
    chunk = data[offset : offset + layout.sector_size]
    if len(chunk) != layout.sector_size:
        msg = f"OLE sector {index} out of range"
        raise ValueError(msg)
    return chunk


def _cfb_fat_sector_locations(data: bytes, layout: _CfbLayout) -> list[int]:
    """FAT 섹터 위치 전부 — 헤더 내장 DIFAT(최대 109개) + 체인된 DIFAT 섹터([MS-CFB] 2.3)."""
    locations = [n for n in layout.header_difat if n != _SECTOR_FREE]
    sector = layout.difat_start
    remaining = layout.num_difat_sectors
    entries_per_sector = layout.sector_size // 4 - 1
    while remaining > 0 and sector not in (_SECTOR_END, _SECTOR_FREE):
        block = _cfb_sector(data, layout, sector)
        entries = struct.unpack_from(f"<{entries_per_sector}I", block, 0)
        locations.extend(e for e in entries if e != _SECTOR_FREE)
        sector = struct.unpack_from("<I", block, entries_per_sector * 4)[0]
        remaining -= 1
    return locations[: layout.num_fat_sectors]


def _cfb_build_fat(data: bytes, layout: _CfbLayout) -> list[int]:
    """전체 FAT 배열(섹터 인덱스 → 다음 섹터 인덱스, 또는 예약값)을 조립한다."""
    per_sector = layout.sector_size // 4
    fat: list[int] = []
    for sector_index in _cfb_fat_sector_locations(data, layout):
        block = _cfb_sector(data, layout, sector_index)
        fat.extend(struct.unpack_from(f"<{per_sector}I", block, 0))
    return fat


def _cfb_chain(data: bytes, layout: _CfbLayout, fat: list[int], start: int, size: int) -> bytes:
    """일반 FAT 체인을 따라 섹터를 이어 붙이고 `size`로 잘라낸다(순환·범위 밖은 손상으로 간주)."""
    out = bytearray()
    sector = start
    seen: set[int] = set()
    while sector not in (_SECTOR_END, _SECTOR_FREE) and len(out) < size:
        if sector in seen or sector < 0 or sector >= len(fat):
            msg = "OLE FAT chain cycle or out-of-range sector"
            raise ValueError(msg)
        seen.add(sector)
        out.extend(_cfb_sector(data, layout, sector))
        sector = fat[sector]
    return bytes(out[:size])


_DIR_NAME_LEN_OFFSET = 64
_DIR_OBJECT_TYPE_OFFSET = 66
_DIR_START_SECTOR_OFFSET = 116
_DIR_SIZE_OFFSET = 120
_DIR_NAME_NUL_TERMINATOR_BYTES = 2  # UTF-16LE 이름 길이에 포함된 널 종단 문자 2바이트


def _cfb_entry_name(block: bytes) -> str:
    """디렉터리 엔트리 128B 블록에서 UTF-16LE 이름을 뽑는다(널 종단 2바이트 제외)."""
    name_len = struct.unpack_from("<H", block, _DIR_NAME_LEN_OFFSET)[0]
    if name_len < _DIR_NAME_NUL_TERMINATOR_BYTES:
        return ""
    return block[: name_len - _DIR_NAME_NUL_TERMINATOR_BYTES].decode("utf-16-le", errors="replace")


def _cfb_read_directory(data: bytes, layout: _CfbLayout, fat: list[int]) -> list[_CfbEntry]:
    """디렉터리 섹터 체인을 평탄 스캔해 할당된 엔트리를 모두 반환한다(트리 순회 없음)."""
    raw = _cfb_chain(data, layout, fat, layout.dir_start, len(data))
    entries: list[_CfbEntry] = []
    for i in range(len(raw) // _CFB_DIR_ENTRY_SIZE):
        block = raw[i * _CFB_DIR_ENTRY_SIZE : (i + 1) * _CFB_DIR_ENTRY_SIZE]
        object_type = block[_DIR_OBJECT_TYPE_OFFSET]
        if object_type == _ENTRY_UNALLOCATED:
            continue
        start_sector = struct.unpack_from("<I", block, _DIR_START_SECTOR_OFFSET)[0]
        size = struct.unpack_from("<Q", block, _DIR_SIZE_OFFSET)[0]
        entries.append(
            _CfbEntry(name=_cfb_entry_name(block), object_type=object_type, start_sector=start_sector, size=size)
        )
    return entries


def _cfb_build_minifat(data: bytes, layout: _CfbLayout, fat: list[int]) -> list[int]:
    """MiniFAT 배열(작은 스트림용, `mini_stream_cutoff` 미만 크기의 스트림이 쓴다)."""
    if layout.num_mini_fat_sectors == 0:
        return []
    total_bytes = layout.sector_size * layout.num_mini_fat_sectors
    raw = _cfb_chain(data, layout, fat, layout.mini_fat_start, total_bytes)
    return list(struct.unpack_from(f"<{len(raw) // 4}I", raw, 0))


def _cfb_mini_chain(ministream: bytes, minifat: list[int], mini_sector_size: int, start: int, size: int) -> bytes:
    """미니스트림(루트 엔트리의 본문) 안에서 MiniFAT 체인을 따라 작은 스트림 하나를 읽는다."""
    out = bytearray()
    sector = start
    seen: set[int] = set()
    while sector not in (_SECTOR_END, _SECTOR_FREE) and len(out) < size:
        if sector in seen or sector < 0 or sector >= len(minifat):
            msg = "OLE MiniFAT chain cycle or out-of-range sector"
            raise ValueError(msg)
        seen.add(sector)
        offset = sector * mini_sector_size
        out.extend(ministream[offset : offset + mini_sector_size])
        sector = minifat[sector]
    return bytes(out[:size])


def _cfb_named_streams(data: bytes, names: frozenset[str]) -> dict[str, bytes]:
    """`names`에 속하는 최상위 스트림의 내용만 읽어 이름 → 바이트로 돌려준다(손상 시 §2.3 규칙대로 종료)."""
    try:
        layout = _cfb_layout(data)
        fat = _cfb_build_fat(data, layout)
        entries = _cfb_read_directory(data, layout, fat)
        root = next((e for e in entries if e.object_type == _ENTRY_ROOT_STORAGE), None)
        if root is None:
            msg = "OLE root storage entry missing"
            raise ValueError(msg)  # noqa: TRY301 - 아래 except가 일괄 corrupt_container로 변환
        minifat = _cfb_build_minifat(data, layout, fat)
        ministream = _cfb_chain(data, layout, fat, root.start_sector, root.size) if root.size else b""
        result: dict[str, bytes] = {}
        for entry in entries:
            if entry.object_type != _ENTRY_STREAM or entry.name not in names:
                continue
            if entry.size > _MAX_INSPECT_BYTES:
                msg = f"OLE stream {entry.name!r} exceeds inspection limit ({_MAX_INSPECT_BYTES} bytes)"
                raise ValueError(msg)  # noqa: TRY301
            if entry.size >= layout.mini_stream_cutoff:
                result[entry.name] = _cfb_chain(data, layout, fat, entry.start_sector, entry.size)
            else:
                result[entry.name] = _cfb_mini_chain(
                    ministream, minifat, layout.mini_sector_size, entry.start_sector, entry.size
                )
    except (struct.error, IndexError, ValueError) as exc:
        msg = f"OLE container error: {exc}"
        raise StageError(_CORRUPT_CONTAINER, stage="parse", plugin_id=PLUGIN_ID, detail=msg) from exc
    return result


_FILE_HEADER_SIGNATURE_LEN = 32
_FILE_HEADER_VERSION_END = 36
_FILE_HEADER_FLAGS_OFFSET = 36
_FILE_HEADER_MIN_LEN = 40


def _hwp5_from_file_header(
    content: bytes, *, has_view_text: bool, signals: list[str]
) -> tuple[ct.SourceFormat, ContainerFlags]:
    """`FileHeader` 스트림 256B를 시그니처·버전·속성 비트로 분해한다(04-pipelines/03 §2.3 표)."""
    sig = content[:_FILE_HEADER_SIGNATURE_LEN].rstrip(b"\x00")
    if sig != _HWP5_SIGNATURE:
        signals.append("ole:FileHeader_signature_mismatch")
        return ct.SourceFormat.unknown, ContainerFlags(encrypted=False, distribution=False, compressed=False)
    signals.append(f"ole:FileHeader={_HWP5_SIGNATURE.decode('ascii')}")
    has_version = len(content) >= _FILE_HEADER_VERSION_END
    version_bytes = content[_FILE_HEADER_SIGNATURE_LEN:_FILE_HEADER_VERSION_END]
    version = ".".join(str(b) for b in version_bytes) if has_version else None
    has_flags = len(content) >= _FILE_HEADER_MIN_LEN
    flags_int = struct.unpack_from("<I", content, _FILE_HEADER_FLAGS_OFFSET)[0] if has_flags else 0
    compressed = bool(flags_int & 0b1)
    encrypted = bool(flags_int & 0b10)
    distribution = bool(flags_int & 0b100)
    signals.append(f"ole:FileHeader.flags=compressed={compressed}|encrypted={encrypted}|distribution={distribution}")
    if has_view_text:
        signals.append("ole:ViewText")
        if not distribution:
            # §2.3: 플래그와 스트림이 어긋나면 플래그를 따르고 둘 다 신호에 남긴다.
            signals.append("ole:ViewText_flag_mismatch")
    return ct.SourceFormat.hwp5, ContainerFlags(
        encrypted=encrypted, distribution=distribution, compressed=compressed, hwp_version=version
    )


def _ole_detect(data: bytes, signals: list[str]) -> tuple[ct.SourceFormat, ContainerFlags]:
    """OLE CFB 패밀리(§2.2 표) — `FileHeader`/`WordDocument`/`EncryptedPackage`+`EncryptionInfo`로 가른다."""
    signals.append("ole:magic")
    names_of_interest = frozenset(
        {_HWP5_STREAM, _DOC_STREAM, _ENCRYPTED_PACKAGE_STREAM, _ENCRYPTION_INFO_STREAM, _VIEWTEXT_STREAM}
    )
    streams = _cfb_named_streams(data, names_of_interest)
    if _HWP5_STREAM in streams:
        return _hwp5_from_file_header(streams[_HWP5_STREAM], has_view_text=_VIEWTEXT_STREAM in streams, signals=signals)
    if _ENCRYPTED_PACKAGE_STREAM in streams and _ENCRYPTION_INFO_STREAM in streams:
        signals.append(f"ole:{_ENCRYPTED_PACKAGE_STREAM}+{_ENCRYPTION_INFO_STREAM}")
        return ct.SourceFormat.docx, ContainerFlags(encrypted=True, distribution=False, compressed=False)
    if _DOC_STREAM in streams:
        signals.append(f"ole:{_DOC_STREAM}")
        return ct.SourceFormat.doc, ContainerFlags(encrypted=False, distribution=False, compressed=False)
    signals.append("ole:no_known_stream")
    return ct.SourceFormat.unknown, ContainerFlags(encrypted=False, distribution=False, compressed=False)


def _md_list_link_ratio(text: str) -> float:
    """목록·링크 문법 라인 비율(§2.4 3행 "목록·링크 문법 라인 비율 ≥ 0.05")."""
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        return 0.0
    hits = sum(1 for line in lines if _MD_LIST_OR_LINK.search(line))
    return hits / len(lines)


def _detect_json(data: bytes, signals: list[str]) -> float | None:
    """JSON 판정(§2.4 1행) — 16MB 이하는 전체 파싱, 초과는 첫 바이트만으로 판정(균형 미검증, -0.1)."""
    if len(data) <= _JSON_FULL_PARSE_LIMIT:
        try:
            json.loads(data.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            return None
        signals.append("text:json_parsed")
        return 0.9
    signals.append("text:json_truncated_probe")
    return 0.8


def _text_like_detect(
    data: bytes, probe: bytes, signals: list[str], hints: _Hints
) -> tuple[ct.SourceFormat, float, bool]:
    """텍스트 계열 판별(§2.4) — json → html → markdown(신호) → markdown(힌트, 가산 없음) → txt."""
    stripped = data.lstrip(b" \t\r\n\x0c\x0b")
    if stripped[:1] in (b"{", b"["):
        json_confidence = _detect_json(data, signals)
        if json_confidence is not None:
            return ct.SourceFormat.json, json_confidence, True
    lower_probe = probe.lower()
    if any(marker in lower_probe for marker in _HTML_MARKERS):
        signals.append("text:html_root")
        return ct.SourceFormat.html, 0.8, True
    text = probe.decode("utf-8", errors="replace").removeprefix("﻿")
    has_md_signal = text.startswith("---") or bool(_ATX_HEADING.search(text)) or bool(_FENCE.search(text))
    if has_md_signal or _md_list_link_ratio(text) >= _MD_LIST_LINK_RATIO:
        signals.append("text:markdown_signal")
        return ct.SourceFormat.md, 0.6, True
    if _hint_format(hints.media_type, hints.extension) == ct.SourceFormat.md:
        signals.append("text:hint_markdown")
        return ct.SourceFormat.md, 0.5, False
    signals.append("text:plain")
    return ct.SourceFormat.txt, 0.6, True


_MagicResult = tuple[ct.SourceFormat, float, ContainerFlags, bool]
_NO_FLAGS = ContainerFlags(encrypted=False, distribution=False, compressed=False)


def _dispatch_container_magic(data: bytes, header: bytes, signals: list[str]) -> _MagicResult | None:
    """컨테이너 패밀리(PDF·ZIP·OLE, §2.2 표) — 매직 바이트 + 내부 검사."""
    if _PDF_MAGIC in header:
        signals.append("pdf:header")
        encrypted = b"/Encrypt" in data
        if encrypted:
            signals.append("pdf:trailer=/Encrypt")
        flags = ContainerFlags(encrypted=encrypted, distribution=False, compressed=False)
        return ct.SourceFormat.pdf, 1.0, flags, False
    if header.startswith(_ZIP_MAGIC):
        fmt, flags = _zip_detect(data, signals)
        return fmt, (1.0 if fmt != ct.SourceFormat.unknown else 0.0), flags, False
    if header.startswith(_ZIP_EMPTY_MAGIC):
        signals.append("zip:empty_archive")
        return ct.SourceFormat.unknown, 0.0, _NO_FLAGS, False
    if header.startswith(_OLE_MAGIC):
        fmt, flags = _ole_detect(data, signals)
        confidence = 0.7 if fmt == ct.SourceFormat.docx else (1.0 if fmt != ct.SourceFormat.unknown else 0.0)
        return fmt, confidence, flags, False
    return None


def _dispatch_flat_magic(header: bytes, signals: list[str]) -> _MagicResult | None:
    """평문 시그니처 패밀리(RTF·HWP 3.0, §2.2 표) — 컨테이너가 아닌 바이트열 그대로의 매직."""
    if header.startswith(_RTF_MAGIC):
        signals.append("rtf:header")
        return ct.SourceFormat.rtf, 1.0, _NO_FLAGS, False
    if header.startswith(_HWP3_MAGIC):
        signals.append("hwp3:header")
        return ct.SourceFormat.hwp3, 1.0, _NO_FLAGS, False
    return None


def _dispatch_by_magic(data: bytes, signals: list[str]) -> _MagicResult | None:
    """매직 바이트·컨테이너 내부 검사만으로 판정한다(§2.1 신호 1·2). 넷째 반환값은 힌트 가산 허용 여부."""
    header = data[:_HEADER_PROBE]
    return _dispatch_container_magic(data, header, signals) or _dispatch_flat_magic(header, signals)


def detect(data: bytes, *, hint_media_type: str | None = None, hint_extension: str | None = None) -> DetectionResult:
    """04-pipelines/03 §2 알고리즘 전체를 실행한다.

    Args:
        data: 원본 바이트(전체; 판별 자체는 헤더·중앙 디렉터리·특정 항목만 읽는다).
        hint_media_type: 선언 콘텐츠 타입(신호 3; `IngestRequest.media_type_hint`/HTTP `Content-Type`).
        hint_extension: `resolved_uri` 확장자(신호 4).

    Returns:
        판정된 `format`·`format_confidence`·`container_flags`·`detect_report`를 담은 `DetectionResult`.

    Raises:
        StageError: 판정 결과가 `unknown`이면 `parse.unsupported_format`, 컨테이너가 손상됐으면
            `parse.corrupt_container`(둘 다 §5.7 비재시도).
    """
    signals: list[str] = []
    hints = _Hints(media_type=hint_media_type, extension=hint_extension)
    magic_result = _dispatch_by_magic(data, signals)
    if magic_result is not None:
        fmt, confidence, flags, allow_bonus = magic_result
    else:
        probe = data[:_TEXT_PROBE]
        if b"\x00" not in probe:
            fmt, confidence, allow_bonus = _text_like_detect(data, probe, signals, hints)
        else:
            signals.append("binary:no_signature")
            fmt, confidence, allow_bonus = ct.SourceFormat.unknown, 0.0, False
        flags = ContainerFlags(encrypted=False, distribution=False, compressed=False)
    return _finalize(fmt, confidence, flags, signals, hints, allow_bonus=allow_bonus)


def _rfc3339_ms(moment: datetime) -> str:
    """`ctx.now()` 결과를 계약이 요구하는 밀리초 정밀도 RFC 3339 UTC 문자열로 만든다(바이블 §6.3)."""
    utc = moment.astimezone(UTC)
    return utc.strftime("%Y-%m-%dT%H:%M:%S.") + f"{utc.microsecond // 1000:03d}Z"


def _resolved_uri_extension(resolved_uri: str) -> str | None:
    """`resolved_uri` 경로 끝의 확장자(신호 4). 쿼리·프래그먼트는 무시한다."""
    path = resolved_uri.split("?", 1)[0].split("#", 1)[0]
    if "." not in path.rsplit("/", 1)[-1]:
        return None
    return "." + path.rsplit(".", 1)[-1]


class FormatDetectorConfig(BaseModel):
    """`parser.format_detector`의 v1 설정.

    판별 임계값은 코드 상수다(04-pipelines/03 §2.4·§2.5 초안 목표, 확정 전까지 옵션 없음 — 미해결 이슈 3).
    """

    model_config = ConfigDict(extra="forbid", frozen=True)


class FormatDetectorStage:
    """`parser.format_detector`(역할 `format_detector`) — 바이블 §4.2 `detect` 서브스테이지 5멤버 구현.

    입력 `SourceDocument`(fetch 출력, 판정 필드는 잠정값)를 받아 `format`·`format_confidence`·
    `container_flags`·`media_type`·`detect_report`를 재기입한 새 `SourceDocument`를 낸다. 봉투·정책
    필드(`tenant_id` 등)는 입력에서 복사한다(§1 결정: "값은 fetch 출력, 계보 포인터는 detect 출력").
    """

    plugin_id = PLUGIN_ID
    config_schema = FormatDetectorConfig
    requires_lineage: tuple[str, ...] = ()

    def __init__(self, config: FormatDetectorConfig | None = None) -> None:
        """설정을 고정한다(설정은 `config_hash` → `fingerprint` → `stage_key` 입력)."""
        self.config = config or FormatDetectorConfig()

    def config_hash(self) -> str:
        """`H("config", canonical_json(config))`(바이블 §6.2 근사, 정렬 키·구분자 고정 JSON)."""
        canonical = json.dumps(
            self.config.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), ensure_ascii=False
        )
        return hash_of("config", canonical)

    def capabilities(self) -> ct.Capabilities:
        """`isolation_modes=[in_process]`(puremagic 대체 자체 구현 + ZIP/OLE 스니퍼, 04-pipelines/03 §5.1)."""
        return ct.Capabilities(
            isolation_modes=[ct.IsolationMode.in_process],
            supports_resumable=False,
            contracts_compat=ct.ContractsCompat(">=1.0,<2.0"),
            input_formats=None,
            requires_gpu=False,
        )

    def fingerprint(self) -> str:
        """`H("producer", plugin_id, plugin_version, config_hash, "", "")`(인프로세스: image digest 없음)."""
        return hash_of("producer", self.plugin_id, PLUGIN_VERSION, self.config_hash(), "", "")

    async def run(self, inp: SourceDocument, ctx: Any) -> SourceDocument:
        """`ctx.source_bytes()`로 원본 바이트를 받아 판정 필드를 채운 `SourceDocument`를 낸다."""
        port = getattr(ctx, "source_bytes", None)
        if port is None:
            msg = "StageContext has no source_bytes port (04-pipelines/04 open issue 18)"
            raise StageError(_CONVERSION_FAILED, stage="parse", plugin_id=self.plugin_id, detail=msg)
        data = port()
        if inspect.isawaitable(data):
            data = await data
        return self.detect_source(bytes(data), inp, ctx)

    def detect_source(self, data: bytes, inp: SourceDocument, ctx: Any) -> SourceDocument:
        """순수 판별(`detect()`)을 실행하고 결과를 `inp`에 병합한 새 `SourceDocument`를 만든다."""
        hint_extension = _resolved_uri_extension(str(inp.resolved_uri))
        result = detect(data, hint_media_type=str(inp.media_type.root), hint_extension=hint_extension)
        return inp.model_copy(
            update={
                "producer": ct.Producer(
                    plugin_id=self.plugin_id,
                    plugin_version=PLUGIN_VERSION,
                    config_hash=self.config_hash(),
                    image_digest=None,
                ),
                "created_at": _rfc3339_ms(ctx.now()),
                "media_type": ct.MediaType(result.media_type),
                "format": result.format,
                "format_confidence": result.format_confidence,
                "container_flags": result.container_flags,
                "detect_report": result.detect_report,
            }
        )
