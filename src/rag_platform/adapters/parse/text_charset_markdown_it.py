"""`parser.text_charset_markdown_it` 파서 스테이지 — TXT·Markdown 원본 바이트를 `ParsedDocument`로 만든다.

역할: `SourceDocument{format ∈ {txt, md}}`(CSV/TSV는 `format=txt`의 힌트 기반 하위 경로)를 받아
인코딩 판정(`charset-normalizer`, EUC-KR/CP949 등 한국어 레거시 인코딩 포함) → 구조 추론(TXT
heading·개조식 목록 / Markdown `markdown-it-py` 토큰 / CSV 표) → `ParsedDocument`로 변환한다.
설계 근거: 04-pipelines/08(파서 TXT·MD·CSV) §2~§6, 바이블 §4.1(5멤버 스테이지)·§5.4
`ParsedDocument`/`Block`/`TableData`, ADR-0002·ADR-0004. `WP-103`(docs/13-implementation/wp) 참조 —
JSON/JSONL/XML 하위 경로, ftfy 모지바케 재투표, mdit_py_plugins(각주·태스크리스트·수식), 대용량
스트리밍·문단 병합 모드는 이 WP 범위 밖(허용 패키지·지시 사양 요지에 없음, WP 문서 참조).
구성: `TextParserConfig`(+ 하위 `EncodingConfig`/`TxtConfig`/`MdConfig`/`CsvConfig`) — `config_schema`;
`TextCharsetMarkdownItParser` — 스테이지 5멤버; 내부 `_decode`(인코딩)·`_segment_txt`/`_classify_segments`/
`_assemble_txt_blocks`(TXT 구조)·`_build_md_blocks`(Markdown)·`_build_csv_blocks`(CSV).
불변식: 파일시스템·네트워크 접근 없음(`ctx.artifacts.put_derived`·`ctx.now()`만). `Block.text`는 원문
(NFC 미적용, 마커 원문 보존). `element_path`는 문서 내 유일. `page`·`bbox`는 항상 null(흐름 포맷).
검증 계층: 1층(여기서 검증) — `tests/adapters/parse/test_text_markdown.py`.
"""

from __future__ import annotations

import codecs
import csv
import inspect
import io
import json
import re
from dataclasses import dataclass
from datetime import UTC as _UTC, date, datetime
from importlib.metadata import version as package_version
from typing import TYPE_CHECKING, Any, Literal

import charset_normalizer
import yaml
from markdown_it import MarkdownIt
from markdown_it.tree import SyntaxTreeNode
from pydantic import BaseModel, ConfigDict, Field

from rag_platform.contracts import common_types as ct
from rag_platform.contracts.common_types.TableCell import HeaderKind
from rag_platform.contracts.common_types.TableData.quality import StructureSource
from rag_platform.contracts.parsed_document import (
    Block,
    Code,
    DerivedArtifact,
    DocumentMetadata,
    LineageRefs,
    ParsedDocument,
    ParserFingerprint,
)
from rag_platform.contracts.parsed_document.ParsedDocument.artifacts import Kind as ArtifactKind
from rag_platform.sdk.hashing import block_id as make_block_id, hash_of
from rag_platform.sdk.stage import StageError

if TYPE_CHECKING:
    from rag_platform.contracts.source_document import SourceDocument

__all__ = ["CsvConfig", "EncodingConfig", "MdConfig", "TextCharsetMarkdownItParser", "TextParserConfig", "TxtConfig"]

PLUGIN_ID = "parser.text_charset_markdown_it"
PLUGIN_VERSION = "0.1.0"
SCHEMA_VERSION = "1.0.0"
PROFILE_OPTION_TXT = "txt_standard"
PROFILE_OPTION_MD = "md_standard"
PROFILE_OPTION_CSV = "csv_experimental"
_BCP47_DEFAULT = "ko"
_CONVERSION_FAILED = "parse.conversion_failed"
_UNSUPPORTED_VARIANT = "parse.unsupported_variant"


def _rfc3339_ms(moment: datetime) -> str:
    utc = moment.astimezone(_UTC)
    return utc.strftime("%Y-%m-%dT%H:%M:%S.") + f"{utc.microsecond // 1000:03d}Z"


# ---------------------------------------------------------------------------------------------
# config_schema (04 §1.4 표의 구현 부분집합 — WP-103 사양 요지로 축소, WP 문서 참조)
# ---------------------------------------------------------------------------------------------


class EncodingConfig(BaseModel):
    """인코딩 판정 설정(04 §3.1~§3.3)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    korean_first: bool = Field(default=True, description="동점·저신뢰 시 cp949 우선(§3.2)")
    hangul_min_ratio: float = Field(0.05, ge=0.0, le=1.0, description="language_hint=ko일 때 한글 비율 하한(§3.3)")
    fallback: Literal["utf_8_replace", "fail"] = Field("utf_8_replace", description="모든 후보 실패 시 조치(§3.1)")
    replace_max_ratio: float = Field(0.01, ge=0.0, le=1.0, description="utf_8_replace 경로의 U+FFFD 비율 상한")
    nul_ratio_max: float = Field(0.01, ge=0.0, le=1.0, description="바이너리 위장 판정 NUL 비율 상한(§3.6)")


class TxtConfig(BaseModel):
    """TXT 구조 추론 설정(04 §4)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    paragraph_mode: Literal["blank_line", "line", "auto"] = Field("auto", description="문단 분할 모드(§4.1)")
    heading_inference: bool = Field(default=True, description="heading 추론(§4.2)")
    heading_max_chars: int = Field(80, ge=1, description="heading 후보 최대 길이(코드포인트)")
    heading_max_level: int = Field(5, ge=1, le=6, description="추론 heading 최대 레벨(P1 압축 배정은 제외)")
    list_inference: bool = Field(default=True, description="개조식 목록 추론(§4.3)")
    indent_width: int = Field(2, ge=1, description="들여쓰기 1레벨의 공백 수(탭 = 1레벨)")


class MdConfig(BaseModel):
    """Markdown 파서 설정(04 §5) — WP 범위: heading/list/table/code/quote, 프론트매터."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    frontmatter_to_metadata: bool = Field(default=True, description="YAML 프론트매터 → metadata(§5.7)")


class CsvConfig(BaseModel):
    """CSV/TSV 하위 경로 설정(04 §6)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    mode: Literal["off", "hint_only", "auto"] = Field("hint_only", description="CSV 하위 경로 진입 조건(§6.1)")
    header: Literal["auto", "first_row", "none"] = Field("auto", description="헤더 행 판정(§6.2)")
    rows_per_block: int = Field(1_000, ge=1, description="표 블록 1개의 최대 데이터 행(§6.3)")
    max_cols: int = Field(256, ge=1, description="열 상한. 초과는 parse.unsupported_variant")


class TextParserConfig(BaseModel):
    """`parser.text_charset_markdown_it`의 `config_schema`(04 §1.4). `ingest.parse.options.text` 부분집합."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    encoding: EncodingConfig = Field(default_factory=EncodingConfig)
    txt: TxtConfig = Field(default_factory=TxtConfig)
    md: MdConfig = Field(default_factory=MdConfig)
    csv: CsvConfig = Field(default_factory=CsvConfig)


# ---------------------------------------------------------------------------------------------
# 공통: 인코딩 판정(04 §3)
# ---------------------------------------------------------------------------------------------

# 04 §3.2 한국어 레거시 인코딩 별칭 표: label(소문자) -> (python 코덱명, source_encoding 기록값)
_ENCODING_ALIASES: dict[str, tuple[str, str]] = {
    "euc-kr": ("cp949", "cp949"),
    "euc_kr": ("cp949", "cp949"),
    "euckr": ("cp949", "cp949"),
    "ks_c_5601-1987": ("cp949", "cp949"),
    "ks_c_5601-1989": ("cp949", "cp949"),
    "ksc5601": ("cp949", "cp949"),
    "ksc_5601": ("cp949", "cp949"),
    "korean": ("cp949", "cp949"),
    "iso-ir-149": ("cp949", "cp949"),
    "csiso56011987": ("cp949", "cp949"),
    "cp949": ("cp949", "cp949"),
    "ms949": ("cp949", "cp949"),
    "uhc": ("cp949", "cp949"),
    "windows-949": ("cp949", "cp949"),
    "x-windows-949": ("cp949", "cp949"),
    "johab": ("johab", "johab"),
    "x-johab": ("johab", "johab"),
    "iso-2022-kr": ("iso2022_kr", "iso-2022-kr"),
    "csiso2022kr": ("iso2022_kr", "iso-2022-kr"),
    "utf-8": ("utf-8", "utf-8"),
    "utf8": ("utf-8", "utf-8"),
    "unicode-1-1-utf-8": ("utf-8", "utf-8"),
}


def _normalize_label(label: str) -> tuple[str, str]:
    """IANA/Python 인코딩 라벨을 (python 코덱명, `source_encoding` 기록값)으로 정규화(04 §3.2)."""
    key = label.strip().lower()
    if key in _ENCODING_ALIASES:
        return _ENCODING_ALIASES[key]
    try:
        info = codecs.lookup(key)
    except LookupError:
        return key, key
    return info.name, info.name


def _try_decode(body: bytes, codec: str) -> str | None:
    try:
        return body.decode(codec, errors="strict")
    except (LookupError, UnicodeDecodeError):
        return None


_ASCII_MAX = 0x80
_HANGUL_SYLLABLE_RANGE = (0xAC00, 0xD7A3)
_HANGUL_JAMO_RANGE = (0x1100, 0x11FF)
_HANGUL_COMPAT_JAMO_RANGE = (0x3130, 0x318F)


def _is_hangul(ch: str) -> bool:
    code = ord(ch)
    return any(lo <= code <= hi for lo, hi in (_HANGUL_SYLLABLE_RANGE, _HANGUL_JAMO_RANGE, _HANGUL_COMPAT_JAMO_RANGE))


def _hangul_ratio(text: str) -> float:
    non_space = [ch for ch in text if not ch.isspace()]
    if not non_space:
        return 0.0
    return sum(1 for ch in non_space if _is_hangul(ch)) / len(non_space)


@dataclass
class _DecodeResult:
    text: str
    source_encoding: str
    method: str
    degraded: bool
    report: dict[str, Any]


def _decode(  # noqa: PLR0912, PLR0915 - 04 §3.1 결정 순서(BOM·http·감지기·utf-8·cp949·fallback)를 한곳에 모은다
    data: bytes, *, http_charset: str | None, language_hint: str, cfg: EncodingConfig
) -> _DecodeResult:
    """04 §3.1 결정 순서(BOM > http charset > 감지기 > utf-8 > cp949 > fallback) + §3.2 한글 재투표."""
    if data and (data.count(b"\x00") / len(data)) > cfg.nul_ratio_max:
        raise StageError(_UNSUPPORTED_VARIANT, stage="parse", detail="binary content: NUL ratio exceeds nul_ratio_max")

    body = data
    bom = False
    if body.startswith(b"\xef\xbb\xbf"):
        bom = True
        body = body[3:]
    candidates: list[tuple[str, str, str]] = []
    if bom:
        candidates.append(("utf-8", "utf-8", "bom"))
    if http_charset:
        candidates.append((*_normalize_label(http_charset), "http_charset"))
    # 국소 결정(WP-103 open_issues): charset-normalizer는 짧거나 스크립트가 섞인 텍스트에서 유효한
    # UTF-8을 다른 단일 바이트 인코딩(예 cp874)으로 오판할 수 있다 — 그 오판도 strict 디코딩은
    # 항상 "성공"하므로(단일 바이트 코덱은 모든 바이트를 해석) 04 §3.1 표의 감지기 우선순위를 그대로
    # 따르면 유효한 UTF-8을 깨뜨린다. 비ASCII 바이트를 포함한 바이트열이 이미 유효한 UTF-8이면
    # (여러 바이트 다중 시퀀스가 동시에 요행으로 유효할 확률은 실질적으로 0) 감지기를 건너뛴다.
    is_ascii_only = all(b < _ASCII_MAX for b in body)
    utf8_direct_ok = not is_ascii_only and _try_decode(body, "utf-8") is not None
    detector_report: list[dict[str, float | str]] = []
    if not utf8_direct_ok:
        best = charset_normalizer.from_bytes(body).best()
        if best is not None and best.encoding:
            codec, recorded = _normalize_label(best.encoding)
            candidates.append((codec, recorded, "detector"))
            detector_report.append({"encoding": recorded, "coherence": round(1.0 - best.chaos, 4)})
    candidates.append(("utf-8", "utf-8", "utf_8"))
    candidates.append(("cp949", "cp949", "cp949_fallback"))

    chosen: tuple[str, str, str, str] | None = None
    for codec, recorded, method in candidates:
        text = _try_decode(body, codec)
        if text is None:
            continue
        chosen = (codec, recorded, method, text)
        break

    if chosen is not None and cfg.korean_first and language_hint == "ko" and chosen[2] != "cp949_fallback":
        candidate_text = chosen[3]
        if _hangul_ratio(candidate_text) < cfg.hangul_min_ratio:
            try:
                retry_text = body.decode("cp949", errors="strict")
            except UnicodeDecodeError:
                retry_text = None
            if retry_text is not None and _hangul_ratio(retry_text) >= cfg.hangul_min_ratio:
                chosen = ("cp949", "cp949", "cp949_revote", retry_text)

    degraded = False
    replacement_chars = 0
    if chosen is None:
        if cfg.fallback == "fail":
            raise StageError(_CONVERSION_FAILED, stage="parse", detail="all encoding candidates failed strict decode")
        text = body.decode("utf-8", errors="replace")
        replacement_chars = text.count("�")
        ratio = replacement_chars / max(len(text), 1)
        if ratio > cfg.replace_max_ratio:
            raise StageError(
                _CONVERSION_FAILED, stage="parse", detail=f"U+FFFD ratio {ratio:.4f} exceeds replace_max_ratio"
            )
        chosen = ("utf-8", "utf-8", "replace", text)
        degraded = True

    _codec, recorded, method, text = chosen
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    newline_style = "crlf" if b"\r\n" in data else ("cr" if b"\r" in data else "lf")
    report = {
        "kind": "text_decode_report",
        "bom": bom,
        "http_charset": http_charset,
        "method": method,
        "chosen": recorded,
        "candidates": detector_report,
        "hangul_ratio": round(_hangul_ratio(normalized), 4),
        "replacement_chars": replacement_chars,
        "newline_style": newline_style,
    }
    return _DecodeResult(text=normalized, source_encoding=recorded, method=method, degraded=degraded, report=report)


# ---------------------------------------------------------------------------------------------
# 공유: `Block` 조립·표 선형화
# ---------------------------------------------------------------------------------------------


class _BlockSink:
    """`element_path` 유일성·`ordinal`(부모별 연속)·`block_id` 결정 규칙을 한곳에서 지키는 블록 누산기."""

    def __init__(self, doc_version: str) -> None:
        self.doc_version = doc_version
        self.blocks: list[Block] = []
        self._paths: set[str] = set()
        self._ordinals: dict[str | None, int] = {}

    def add(
        self,
        *,
        block_type: ct.BlockType,
        path: str,
        parent: str | None,
        text: str,
        level: int | None = None,
        numbering_label: str | None = None,
        heading_inferred: bool | None = None,
        ordered: bool | None = None,
        table: ct.TableData | None = None,
        code: Code | None = None,
    ) -> str:
        """블록 1개를 추가하고 `block_id`(str, hex32)를 돌려준다."""
        if path in self._paths:
            msg = f"duplicate element_path generated: {path}"
            raise StageError(_CONVERSION_FAILED, stage="parse", detail=msg)
        self._paths.add(path)
        bid = make_block_id(self.doc_version, path)
        ordinal = self._ordinals.get(parent, 0)
        self._ordinals[parent] = ordinal + 1
        self.blocks.append(
            Block(
                block_id=ct.Hex32(bid),
                type=block_type,
                parent_block_id=ct.Hex32(parent) if parent is not None else None,
                ordinal=ordinal,
                text=text,
                level=level,
                numbering_label=numbering_label,
                heading_inferred=heading_inferred,
                ordered=ordered,
                furniture=False,
                container=ct.BlockContainer.body,
                source=ct.BlockSource.text_layer,
                confidence=None,
                provenance=ct.Provenance(element_path=path, char_start=0, char_end=len(text), page=None, bbox=None),
                table=table,
                code=code,
            )
        )
        return bid


class _LevelStack:
    """heading/list_item 트리 부모 해소 — "가장 가까운 앞선 항목(level < d)", 없으면 fallback(03 §4.1)."""

    def __init__(self) -> None:
        self._stack: list[tuple[int, str]] = []

    def parent_for(self, level: int, fallback: str | None = None) -> str | None:
        while self._stack and self._stack[-1][0] >= level:
            self._stack.pop()
        return self._stack[-1][1] if self._stack else fallback

    def push(self, level: int, block_id: str) -> None:
        self._stack.append((level, block_id))

    def current(self) -> str | None:
        return self._stack[-1][1] if self._stack else None

    def reset(self) -> None:
        self._stack.clear()


def _linearize_table(rows: list[list[str]]) -> tuple[str, dict[tuple[int, int], tuple[int, int]]]:
    """표 선형화(셀 U+0009, 행 U+000A) + 셀 구간(03 §6, 04 §4.4)."""
    parts: list[str] = []
    spans: dict[tuple[int, int], tuple[int, int]] = {}
    pos = 0
    for r, row in enumerate(rows):
        for c, cell in enumerate(row):
            if pos > 0 and (c > 0 or r > 0):
                sep = "\t" if c > 0 else "\n"
                parts.append(sep)
                pos += 1
            spans[r, c] = (pos, pos + len(cell))
            parts.append(cell)
            pos += len(cell)
    return "".join(parts), spans


def _table_data_from_rows(
    rows: list[list[str]],
    *,
    header_row_indices: list[int],
    header_inferred: bool,
    structure_source: StructureSource,
    path: str,
) -> tuple[ct.TableData, str]:
    n_cols = max((len(r) for r in rows), default=0)
    text, spans = _linearize_table(rows)
    header_set = set(header_row_indices)
    cells: list[ct.TableCell] = []
    for r, row in enumerate(rows):
        for c, value in enumerate(row):
            start, end = spans[r, c]
            is_header = r in header_set
            cells.append(
                ct.TableCell(
                    row=r,
                    col=c,
                    row_span=1,
                    col_span=1,
                    text=value,
                    is_header=is_header,
                    header_kind=HeaderKind.column if is_header else HeaderKind.none,
                    provenance=ct.Provenance(
                        element_path=f"{path}/row[{r}]/cell[{c}]", char_start=start, char_end=end, page=None, bbox=None
                    ),
                )
            )
    table = ct.TableData(
        n_rows=len(rows),
        n_cols=n_cols,
        cells=cells,
        header_row_indices=[ct.HeaderRowIndice(i) for i in header_row_indices],
        header_inferred=header_inferred,
        role=ct.TableRole.data,
        quality=ct.Quality1(merged_cells_preserved=True, structure_source=structure_source, structure_confidence=None),
    )
    return table, text


def _to_artifact_ref(value: Any) -> ct.ArtifactRef:
    # `Any`: `put_derived` 반환형은 셸 구현마다 다르다(계약 모델 또는 dict) — 어댑터 경계에서 정규화.
    if isinstance(value, ct.ArtifactRef):
        return value
    if hasattr(value, "model_dump"):
        return ct.ArtifactRef.model_validate(value.model_dump(mode="json"))
    return ct.ArtifactRef.model_validate(value)


# ---------------------------------------------------------------------------------------------
# TXT 구조 추론(04 §4)
# ---------------------------------------------------------------------------------------------

_P1 = re.compile(r"^제\s?(\d+)\s?(편|장|절|관|조)(의\s?\d+)?(?=[\s(.])")
_P1_ORDER = ("편", "장", "절", "관", "조")
_P2 = re.compile(r"^(\d{1,2}(?:\.\d{1,2}){0,5}\.?)\s+\S")
_P3 = re.compile(r"^([ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ]+\.?|[IVX]{1,4}\.)\s+\S")
_P4_FULL = re.compile(r"^(\[[^\]]{1,40}\]|【[^】]{1,40}】|<[^>]{1,40}>|《[^》]{1,40}》)$")
_P4_PREFIX = re.compile(r"^(\[(?![ xXv]\])[^\]]{1,20}\]|【[^】]{1,20}】)\s+\S")
_P6 = re.compile(r"^([■◆◈▣▶◎])\s+\S")
_TERMINAL_PUNCT = (".", ",", ";")

_HANGUL_LIST_LETTERS = frozenset("가나다라마바사아자차카타파하")
_ORDERED_MARKERS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("arabic_dot", re.compile(r"^(\d{1,3})\.\s")),
    ("hangul_dot", re.compile(r"^([가-힣])\.\s")),
    ("arabic_paren_suffix", re.compile(r"^(\d{1,3})\)\s")),
    ("hangul_paren_suffix", re.compile(r"^([가-힣])\)\s")),
    ("arabic_paren_full", re.compile(r"^\((\d{1,3})\)\s")),
    ("hangul_paren_full", re.compile(r"^\(([가-힣])\)\s")),
    ("circled_digit", re.compile(r"^([①-⑳])\s")),
    ("circled_hangul", re.compile(r"^([㉠-㉭㉮-㉻])\s")),
    ("latin_dot", re.compile(r"^([a-zA-Z])\.\s")),
    ("latin_paren_suffix", re.compile(r"^([a-zA-Z])\)\s")),
    ("latin_paren_full", re.compile(r"^\(([a-zA-Z])\)\s")),
)
_SYMBOL_MARKERS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("square", re.compile(r"^([□▢☐])\s")),
    ("circle", re.compile(r"^([○◦〇])\s")),  # noqa: RUF001 - 04 §4.3 마커 표의 원문 기호(동그라미)
    ("dash", re.compile(r"^([\-–—])\s")),  # noqa: RUF001 - 04 §4.3 마커 표의 원문 기호(대시)
    ("dot", re.compile(r"^([·•∙ㆍ*])\s")),
    ("checkbox", re.compile(r"^(\[[ xX]\]|[☑☒])\s")),
)
_OUTLINE_LADDER: dict[str, int] = {
    "arabic_dot": 0,
    "hangul_dot": 1,
    "arabic_paren_suffix": 2,
    "hangul_paren_suffix": 3,
    "arabic_paren_full": 4,
    "hangul_paren_full": 5,
    "circled_digit": 6,
    "circled_hangul": 7,
    "latin_dot": 0,
    "latin_paren_suffix": 2,
    "latin_paren_full": 4,
}
_LAW_LADDER: dict[str, int] = {
    "arabic_dot": 1,
    "hangul_dot": 2,
    "arabic_paren_suffix": 3,
    "hangul_paren_suffix": 4,
    "arabic_paren_full": 5,
    "hangul_paren_full": 6,
    "circled_digit": 0,
    "circled_hangul": 7,
    "latin_dot": 1,
    "latin_paren_suffix": 3,
    "latin_paren_full": 5,
}
_SYMBOL_RANK: dict[str, int] = {"square": 0, "circle": 1, "dash": 2, "dot": 3, "checkbox": 2}


@dataclass(frozen=True)
class _HeadingCandidate:
    pattern: str
    level: int
    numbering_label: str | None
    allows_terminal_punct: bool


def _p1_unit(text: str) -> str | None:
    m = _P1.match(text)
    return m.group(2) if m else None


_EMPTY_LEVEL_MAP: dict[str, int] = {}


def _match_heading(  # noqa: PLR0911 - P1~P4·P6 6갈래 패턴 매치를 한곳에 모은다(04 §4.2)
    text: str, p1_level_map: dict[str, int] = _EMPTY_LEVEL_MAP
) -> _HeadingCandidate | None:
    """P1~P4·P6 패턴 매치(패턴 매치와 (a)~(c) 평가만; (d)·(e)는 호출부가 평가, 04 §4.2).

    `p1_level_map`은 문서 전체 P1 등장 단위(편·장·절·관·조)의 압축 배정(04 §4.2 P1 행) — 순수
    탐지(마커 여부)만 필요한 호출부는 생략해도 된다(레벨은 항상 기본값 1이 된다).
    """
    m = _P1.match(text)
    if m:
        suffix = re.sub(r"\s+", "", m.group(3) or "")
        label = f"제{m.group(1)}{m.group(2)}{suffix}"
        return _HeadingCandidate("P1", p1_level_map.get(m.group(2), 1), label, allows_terminal_punct=True)
    m = _P2.match(text)
    if m:
        label = m.group(1)
        level = len(re.findall(r"\d{1,2}", label))
        return _HeadingCandidate("P2", level, label, allows_terminal_punct=False)
    m = _P3.match(text)
    if m:
        return _HeadingCandidate("P3", 1, m.group(1), allows_terminal_punct=True)
    if _P4_FULL.match(text):
        return _HeadingCandidate("P4", 1, None, allows_terminal_punct=False)
    m = _P4_PREFIX.match(text)
    if m:
        return _HeadingCandidate("P4", 1, m.group(1), allows_terminal_punct=False)
    m = _P6.match(text)
    if m:
        return _HeadingCandidate("P6", 1, m.group(1), allows_terminal_punct=False)
    return None


def _match_list_marker(text: str) -> tuple[str, bool, str] | None:
    """개조식 목록 마커(04 §4.3). 반환: (marker_class, ordered, numbering_label)."""
    for name, pattern in _ORDERED_MARKERS:
        m = pattern.match(text)
        if not m:
            continue
        if "hangul" in name and m.group(1) not in _HANGUL_LIST_LETTERS:
            continue
        return name, True, text[: m.end()].rstrip()
    for name, pattern in _SYMBOL_MARKERS:
        m = pattern.match(text)
        if m:
            return name, False, text[: m.end()].rstrip()
    return None


def _looks_like_marker(text: str) -> bool:
    return _match_heading(text) is not None or _match_list_marker(text) is not None


def _indent_level(line: str, indent_width: int) -> int:
    stripped = line.lstrip(" \t")
    ws = line[: len(line) - len(stripped)]
    if not ws:
        return 0
    tabs = ws.count("\t")
    spaces = len(ws) - tabs
    return tabs + (spaces // indent_width if indent_width else 0)


@dataclass
class _RawSeg:
    text: str
    indent: int
    single_line: bool


def _resolve_paragraph_mode(lines: list[str], mode: str) -> str:
    """04 §4.1 `auto` 판정: 빈 줄 비율 < 0.02이고 마커 비율 ≥ 0.30이면 `line`, 그 외 `blank_line`."""
    if mode != "auto":
        return mode
    total = len(lines) or 1
    blanks = sum(1 for line in lines if line.strip() == "")
    non_blank = [line.strip() for line in lines if line.strip() != ""]
    marker_lines = sum(1 for line in non_blank if _looks_like_marker(line))
    blank_ratio = blanks / total
    marker_ratio = marker_lines / (len(non_blank) or 1)
    return "line" if (blank_ratio < 0.02 and marker_ratio >= 0.30) else "blank_line"  # noqa: PLR2004


def _group_by_blank_lines(lines: list[str]) -> list[list[str]]:
    groups: list[list[str]] = []
    current: list[str] = []
    for line in lines:
        if line.strip(" \t\f") == "":
            if current:
                groups.append(current)
                current = []
            continue
        current.append(line)
    if current:
        groups.append(current)
    return groups


def _merge_continuations(group: list[str], indent_width: int) -> tuple[list[list[str]], list[int]]:
    """마커 없고 직전 줄보다 더 들여쓴 줄은 직전 논리 줄에 연속 줄로 붙인다(04 §4.1·§4.3)."""
    logical: list[list[str]] = []
    indents: list[int] = []
    for line in group:
        stripped = line.strip()
        indent = _indent_level(line, indent_width)
        if logical and not _looks_like_marker(stripped) and indent > indents[-1]:
            logical[-1].append(stripped)
        else:
            logical.append([stripped])
            indents.append(indent)
    return logical, indents


def _segment_txt(lines: list[str], *, mode: str, indent_width: int) -> list[_RawSeg]:
    """빈 줄/`line` 경계로 문단을 나누되, 마커 줄이 연속되는 구간은 줄 단위로 분리한다(04 §4.1)."""
    segments: list[_RawSeg] = []
    for group in _group_by_blank_lines(lines):
        logical, indents = _merge_continuations(group, indent_width)
        n = len(logical)
        if mode == "line":
            for phys, indent in zip(logical, indents, strict=True):
                segments.append(_RawSeg(text="\n".join(phys), indent=indent, single_line=len(phys) == 1))
            continue
        i = 0
        while i < n:
            is_marker = len(logical[i]) == 1 and _looks_like_marker(logical[i][0])
            j = i
            if is_marker:
                while j < n and len(logical[j]) == 1 and _looks_like_marker(logical[j][0]):
                    segments.append(_RawSeg(text=logical[j][0], indent=indents[j], single_line=True))
                    j += 1
            else:
                while j < n and not (len(logical[j]) == 1 and _looks_like_marker(logical[j][0])):
                    j += 1
                merged: list[str] = [ln for k in range(i, j) for ln in logical[k]]
                segments.append(
                    _RawSeg(text="\n".join(merged), indent=indents[i], single_line=(j - i == 1 and len(merged) == 1))
                )
            i = j
    return segments


def _build_p1_level_map(segments: list[_RawSeg]) -> dict[str, int]:
    present = {unit for seg in segments if seg.single_line for unit in (_p1_unit(seg.text),) if unit}
    ordered = [u for u in _P1_ORDER if u in present]
    return {u: i + 1 for i, u in enumerate(ordered)}


def _infer_genre(segments: list[_RawSeg]) -> ct.Genre | None:
    """04 §4.6: P1 후보 ≥ 3 → law_article, 목록 마커 세그먼트 비율 ≥ 0.5 → outline_report."""
    total = len(segments) or 1
    p1_count = sum(1 for seg in segments if seg.single_line and _p1_unit(seg.text))
    if p1_count >= 3:  # noqa: PLR2004
        return ct.Genre.law_article
    marker_count = sum(1 for seg in segments if seg.single_line and _match_list_marker(seg.text) is not None)
    if marker_count / total >= 0.5:  # noqa: PLR2004
        return ct.Genre.outline_report
    return None


def _resolve_list_level(name: str, indent: int, ladder: dict[str, int], last_ordered_level: int | None) -> int:
    if indent > 0:
        return indent
    if name in _SYMBOL_RANK:
        rank = _SYMBOL_RANK[name]
        return rank if last_ordered_level is None else last_ordered_level + 1 + rank
    return ladder.get(name, 0)


@dataclass
class _Classified:
    kind: Literal["heading", "list_item", "paragraph"]
    text: str
    level: int | None = None
    label: str | None = None
    ordered: bool | None = None


def _heading_ok(cand: _HeadingCandidate, text: str, max_chars: int) -> bool:
    if len(text) > max_chars:
        return False
    return cand.allows_terminal_punct or not text.endswith(_TERMINAL_PUNCT)


def _classify_segments(  # noqa: PLR0912, PLR0915 - TXT 분류 규칙(04 §4.2·§4.3)을 한곳에 모은다
    segments: list[_RawSeg], cfg: TxtConfig, ladder: dict[str, int], p1_level_map: dict[str, int]
) -> list[_Classified]:
    results: list[_Classified] = []
    n = len(segments)
    last_ordered_level: int | None = None
    i = 0
    while i < n:
        seg = segments[i]
        heading = _match_heading(seg.text, p1_level_map) if (cfg.heading_inference and seg.single_line) else None
        if heading is not None and heading.pattern == "P2" and heading.level == 1:
            run: list[tuple[int, _HeadingCandidate]] = [(i, heading)]
            j = i + 1
            while j < n:
                cand_j = _match_heading(segments[j].text, p1_level_map) if segments[j].single_line else None
                if cand_j is not None and cand_j.pattern == "P2" and cand_j.level == 1:
                    run.append((j, cand_j))
                    j += 1
                else:
                    break
            run_is_heading = all(_heading_ok(cand, segments[k].text, cfg.heading_max_chars) for k, cand in run)
            for k, cand_k in run:
                if run_is_heading:
                    results.append(
                        _Classified(kind="heading", text=segments[k].text, level=1, label=cand_k.numbering_label)
                    )
                    last_ordered_level = None
                else:
                    level = _resolve_list_level("arabic_dot", segments[k].indent, ladder, last_ordered_level)
                    results.append(
                        _Classified(
                            kind="list_item",
                            text=segments[k].text,
                            level=level,
                            label=cand_k.numbering_label,
                            ordered=True,
                        )
                    )
                    last_ordered_level = level
            i = j
            continue
        is_heading = False
        if heading is not None:
            ok = _heading_ok(heading, seg.text, cfg.heading_max_chars)
            if ok and heading.pattern != "P1":
                nxt = segments[i + 1] if i + 1 < n else None
                if nxt is not None and nxt.single_line:
                    nxt_cand = _match_heading(nxt.text, p1_level_map)
                    if (
                        nxt_cand is not None
                        and nxt_cand.pattern == heading.pattern
                        and nxt_cand.level <= heading.level
                        and _heading_ok(nxt_cand, nxt.text, cfg.heading_max_chars)
                    ):
                        ok = False
            is_heading = ok
        if is_heading:
            assert heading is not None  # noqa: S101 - is_heading implies heading matched above
            level = heading.level if heading.pattern == "P1" else min(heading.level, cfg.heading_max_level)
            results.append(_Classified(kind="heading", text=seg.text, level=level, label=heading.numbering_label))
            last_ordered_level = None
            i += 1
            continue
        first_line = seg.text.split("\n", 1)[0]
        marker = _match_list_marker(first_line) if cfg.list_inference else None
        if marker is not None:
            name, ordered, label = marker
            level = _resolve_list_level(name, seg.indent, ladder, last_ordered_level)
            results.append(_Classified(kind="list_item", text=seg.text, level=level, label=label, ordered=ordered))
            if ordered:
                last_ordered_level = level
            i += 1
            continue
        results.append(_Classified(kind="paragraph", text=seg.text))
        i += 1
    return results


def _assemble_txt_blocks(classified: list[_Classified], doc_version: str) -> tuple[list[Block], str | None]:
    sink = _BlockSink(doc_version)
    heading_stack = _LevelStack()
    list_stack = _LevelStack()
    title: str | None = None
    for idx, item in enumerate(classified):
        path = f"/txt/para[{idx}]"
        if item.kind == "heading":
            level = item.level or 1
            parent = heading_stack.parent_for(level)
            bid = sink.add(
                block_type=ct.BlockType.heading,
                path=path,
                parent=parent,
                text=item.text,
                level=level,
                numbering_label=item.label,
                heading_inferred=True,
            )
            heading_stack.push(level, bid)
            list_stack.reset()
            if title is None and level == 1 and idx < 3:  # noqa: PLR2004 - 04 §4.2 "첫 3세그먼트"
                title = item.text
        elif item.kind == "list_item":
            level = item.level or 0
            parent = list_stack.parent_for(level, heading_stack.current())
            bid = sink.add(
                block_type=ct.BlockType.list_item,
                path=path,
                parent=parent,
                text=item.text,
                level=level,
                numbering_label=item.label,
                ordered=item.ordered,
            )
            list_stack.push(level, bid)
        else:
            sink.add(block_type=ct.BlockType.paragraph, path=path, parent=heading_stack.current(), text=item.text)
    return sink.blocks, title


# ---------------------------------------------------------------------------------------------
# Markdown(04 §5) — WP 범위: heading/list/table/code/quote, 프론트매터
# ---------------------------------------------------------------------------------------------

_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---[ \t]*\n", re.DOTALL)
_MD_KIND: dict[str, str] = {
    "heading": "heading",
    "paragraph": "paragraph",
    "bullet_list": "list",
    "ordered_list": "list",
    "table": "table",
    "fence": "code",
    "code_block": "code",
    "blockquote": "quote",
}
_MD_TAG: dict[str, str] = {"paragraph": "p", "code": "code", "table": "table", "list": "item", "heading": "h"}


def _inline_text(node: SyntaxTreeNode) -> str:
    if node.type in ("text", "code_inline"):
        return str(node.content)
    if node.type in ("softbreak", "hardbreak"):
        return "\n"
    return "".join(_inline_text(c) for c in node.children)


def _extract_frontmatter(text: str) -> tuple[str, dict[str, Any] | None, bool]:
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return text, None, False
    body = text[m.end() :]
    try:
        loaded = yaml.safe_load(m.group(1))
    except yaml.YAMLError:
        return body, None, True
    if not isinstance(loaded, dict):
        return body, None, True
    return body, loaded, False


def _parse_frontmatter_date(value: Any) -> str | None:
    if isinstance(value, datetime):
        return _rfc3339_ms(value if value.tzinfo else value.replace(tzinfo=_UTC))
    if isinstance(value, date):
        return f"{value.isoformat()}T00:00:00.000Z"
    if isinstance(value, str):
        try:
            parsed = date.fromisoformat(value.strip().replace(".", "-"))
        except ValueError:
            return None
        return f"{parsed.isoformat()}T00:00:00.000Z"
    return None


def _frontmatter_to_metadata(data: dict[str, Any]) -> dict[str, Any]:
    """04 §5.7 키 표 매핑. 인식 못하는 키는 조용히 건너뛴다(경고 코드 없음, 미해결 이슈 12)."""
    meta: dict[str, Any] = {}
    lower = {str(k).lower(): v for k, v in data.items()}
    if "title" in lower:
        meta["title"] = str(lower["title"])
    authors = lower.get("author", lower.get("authors"))
    if authors is not None:
        meta["authors"] = [str(authors)] if isinstance(authors, str) else [str(a) for a in authors]
    for key in ("date", "created", "created_at"):
        if key in lower:
            parsed = _parse_frontmatter_date(lower[key])
            if parsed:
                meta["created_at"] = parsed
            break
    for key in ("updated", "modified", "modified_at", "lastmod"):
        if key in lower:
            parsed = _parse_frontmatter_date(lower[key])
            if parsed:
                meta["modified_at"] = parsed
            break
    lang = lower.get("lang", lower.get("language"))
    if isinstance(lang, str):
        meta["language"] = lang.lower()
    genre = lower.get("genre")
    if isinstance(genre, str) and genre in {g.value for g in ct.Genre}:
        meta["genre"] = ct.Genre(genre)
    return meta


def _emit_code(node: SyntaxTreeNode, path: str, parent_id: str | None, sink: _BlockSink) -> None:
    if node.type == "fence":
        info = (node.info or "").strip()
        language = info.split()[0].lower() if info else None
        content = str(node.content)
        text = content.removesuffix("\n")
    else:
        language = None
        text = str(node.content)
    sink.add(block_type=ct.BlockType.code, path=path, parent=parent_id, text=text, code=Code(language=language))


def _emit_table(node: SyntaxTreeNode, path: str, parent_id: str | None, sink: _BlockSink) -> None:
    rows: list[list[str]] = []
    header_rows = 0
    for section in node.children:
        is_head = section.type == "thead"
        for tr in section.children:
            row = [_inline_text(cell.children[0]) if cell.children else "" for cell in tr.children]
            rows.append(row)
            if is_head:
                header_rows += 1
    table, text = _table_data_from_rows(
        rows,
        header_row_indices=list(range(header_rows)),
        header_inferred=False,
        structure_source=StructureSource.native,
        path=path,
    )
    sink.add(block_type=ct.BlockType.table, path=path, parent=parent_id, text=text, table=table)


def _walk_list(
    node: SyntaxTreeNode,
    *,
    ordered: bool,
    path: str,
    parent_id: str | None,
    sink: _BlockSink,
    depth: int,
    start_index: int = 0,
) -> int:
    """목록 항목을 `{path}/item[i]`에 놓는다.

    중첩 목록은 경로를 소비하지 않고(04 §5.3·§5.8 예) 바로 바깥 컨테이너의 `item` 순번을
    이어받는다(`start_index`) — 반환값은 소비한 항목 수.
    """
    markup = node.markup or ("." if ordered else "-")
    counter = int(node.attrs.get("start", 1)) if ordered else 1
    item_idx = start_index
    for item in node.children:
        item_path = f"{path}/item[{item_idx}]"
        item_idx += 1
        children = list(item.children)
        first_para = children[0] if children and children[0].type == "paragraph" else None
        rest = children[1:] if first_para is not None else children
        text = _inline_text(first_para.children[0]) if first_para is not None and first_para.children else ""
        label = f"{counter}{markup}" if ordered else markup
        bid = sink.add(
            block_type=ct.BlockType.list_item,
            path=item_path,
            parent=parent_id,
            text=text,
            level=depth,
            ordered=ordered,
            numbering_label=label,
        )
        counter += 1
        if rest:
            _walk_container(rest, parent_id=bid, path_prefix=item_path, sink=sink, depth=depth + 1)
    return item_idx - start_index


def _walk_container(
    nodes: list[SyntaxTreeNode], *, parent_id: str | None, path_prefix: str, sink: _BlockSink, depth: int
) -> None:
    """항목·인용 내부 컨테이너(04 §5.8: `/p[k]`·`/code[k]`·`/table[k]`·`/item[i]` 종류별 순번).

    중첩 목록·인용은 이 컨테이너 자신의 경로 세그먼트를 소비하지 않는 투명 컨테이너다
    (`/item[i]/item[j]`, `/quote/p[k]` — 04 §5.3·§5.5 예).
    """
    counters: dict[str, int] = {}
    for node in nodes:
        kind = _MD_KIND.get(node.type, "skip")
        if kind == "skip":
            continue
        if kind == "quote":
            _walk_container(
                list(node.children), parent_id=parent_id, path_prefix=f"{path_prefix}/quote", sink=sink, depth=depth
            )
            continue
        if kind == "list":
            start = counters.get("item", 0)
            consumed = _walk_list(
                node,
                ordered=(node.type == "ordered_list"),
                path=path_prefix,
                parent_id=parent_id,
                sink=sink,
                depth=depth,
                start_index=start,
            )
            counters["item"] = start + consumed
            continue
        tag = _MD_TAG[kind]
        k = counters.get(tag, 0)
        counters[tag] = k + 1
        path = f"{path_prefix}/{tag}[{k}]"
        if kind == "heading":
            text = _inline_text(node.children[0])
            sink.add(block_type=ct.BlockType.heading, path=path, parent=parent_id, text=text, level=int(node.tag[1]))
        elif kind == "paragraph":
            sink.add(
                block_type=ct.BlockType.paragraph, path=path, parent=parent_id, text=_inline_text(node.children[0])
            )
        elif kind == "table":
            _emit_table(node, path, parent_id, sink)
        elif kind == "code":
            _emit_code(node, path, parent_id, sink)


def _build_md_blocks(body: str, doc_version: str) -> tuple[list[Block], str | None]:
    md = MarkdownIt("gfm-like")
    md.disable("linkify")
    root = SyntaxTreeNode(md.parse(body))
    sink = _BlockSink(doc_version)
    heading_stack = _LevelStack()
    counter = 0
    for node in root.children:
        kind = _MD_KIND.get(node.type, "skip")
        if kind == "quote":
            path = f"/md/block[{counter}]/quote"
            counter += 1
            _walk_container(
                list(node.children), parent_id=heading_stack.current(), path_prefix=path, sink=sink, depth=0
            )
            continue
        if kind == "skip":
            counter += 1
            continue
        path = f"/md/block[{counter}]"
        counter += 1
        if kind == "heading":
            level = int(node.tag[1])
            text = _inline_text(node.children[0])
            parent = heading_stack.parent_for(level)
            bid = sink.add(
                block_type=ct.BlockType.heading,
                path=path,
                parent=parent,
                text=text,
                level=level,
                heading_inferred=False,
            )
            heading_stack.push(level, bid)
        elif kind == "paragraph":
            sink.add(
                block_type=ct.BlockType.paragraph,
                path=path,
                parent=heading_stack.current(),
                text=_inline_text(node.children[0]),
            )
        elif kind == "table":
            _emit_table(node, path, heading_stack.current(), sink)
        elif kind == "code":
            _emit_code(node, path, heading_stack.current(), sink)
        elif kind == "list":
            _walk_list(
                node,
                ordered=(node.type == "ordered_list"),
                path=path,
                parent_id=heading_stack.current(),
                sink=sink,
                depth=0,
            )
    h1_blocks = [b for b in sink.blocks if b.type == ct.BlockType.heading and b.level == 1]
    title = h1_blocks[0].text if len(h1_blocks) == 1 else None
    return sink.blocks, title


# ---------------------------------------------------------------------------------------------
# CSV/TSV(실험, 04 §6)
# ---------------------------------------------------------------------------------------------


def _is_numeric_cell(value: str) -> bool:
    try:
        float(value)
    except ValueError:
        return False
    return True


def _resolve_csv_header(rows: list[list[str]], mode: str) -> list[int]:
    if mode == "none" or not rows:
        return []
    if mode == "first_row":
        return [0]
    first = rows[0]
    if not first or any(not cell.strip() for cell in first) or len(set(first)) != len(first):
        return []
    if any(_is_numeric_cell(cell) for row in rows[1:] for cell in row):
        return [0]
    return []


def _build_csv_blocks(text: str, doc_version: str, cfg: CsvConfig, *, tsv_hint: bool) -> tuple[list[Block], bool]:
    degraded = False
    if tsv_hint:
        delimiter = "\t"
    else:
        try:
            delimiter = csv.Sniffer().sniff(text[:4096], delimiters=",;\t|").delimiter
        except csv.Error:
            delimiter = ","
            degraded = True
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    rows_raw = [row for row in reader if any(cell.strip() for cell in row)]
    if not rows_raw:
        return [], degraded
    n_cols = max(len(r) for r in rows_raw)
    if n_cols > cfg.max_cols:
        raise StageError(_UNSUPPORTED_VARIANT, stage="parse", detail=f"csv columns {n_cols} exceed max_cols")
    rows: list[list[str]] = []
    for raw_row in rows_raw:
        if len(raw_row) < n_cols:
            normalized = [*raw_row, *([""] * (n_cols - len(raw_row)))]
        elif len(raw_row) > n_cols:
            normalized = [*raw_row[: n_cols - 1], delimiter.join(raw_row[n_cols - 1 :])]
        else:
            normalized = raw_row
        rows.append(normalized)
    header_indices = _resolve_csv_header(rows, cfg.header)
    header_row = rows[0] if header_indices else None
    data_rows = rows[1:] if header_row is not None else rows
    sink = _BlockSink(doc_version)
    chunks = [data_rows[i : i + cfg.rows_per_block] for i in range(0, len(data_rows), cfg.rows_per_block)] or [[]]
    if len(chunks) <= 1:
        table_rows = rows
        table, text_out = _table_data_from_rows(
            table_rows,
            header_row_indices=header_indices,
            header_inferred=True,
            structure_source=StructureSource.native,
            path="/csv/table[0]",
        )
        sink.add(block_type=ct.BlockType.table, path="/csv/table[0]", parent=None, text=text_out, table=table)
    else:
        for n, part in enumerate(chunks):
            table_rows = [header_row, *part] if header_row is not None else part
            path = f"/csv/table[0]/part[{n}]"
            table, text_out = _table_data_from_rows(
                table_rows,
                header_row_indices=([0] if header_row is not None else []),
                header_inferred=True,
                structure_source=StructureSource.native,
                path=path,
            )
            sink.add(block_type=ct.BlockType.table, path=path, parent=None, text=text_out, table=table)
    return sink.blocks, degraded


_CSV_MEDIA_TYPES = frozenset({"text/csv", "text/tab-separated-values"})
_CSV_EXTENSIONS = (".csv", ".tsv", ".tab")


def _looks_like_csv_hint(inp: SourceDocument) -> bool:
    if str(inp.media_type) in _CSV_MEDIA_TYPES:
        return True
    return str(inp.resolved_uri).lower().endswith(_CSV_EXTENSIONS)


def _is_tsv_hint(inp: SourceDocument) -> bool:
    if str(inp.media_type) == "text/tab-separated-values":
        return True
    return str(inp.resolved_uri).lower().endswith((".tsv", ".tab"))


def _choose_subroute(inp: SourceDocument, csv_cfg: CsvConfig) -> str:
    if inp.format == ct.SourceFormat.md:
        return "md"
    if csv_cfg.mode != "off" and _looks_like_csv_hint(inp):
        return "csv"
    return "txt"


# ---------------------------------------------------------------------------------------------
# 스테이지
# ---------------------------------------------------------------------------------------------


class TextCharsetMarkdownItParser:
    """TXT·Markdown 인프로세스 파서(A 등급, `in_process`). CSV/TSV는 `format=txt`의 힌트 하위 경로."""

    plugin_id = PLUGIN_ID
    config_schema = TextParserConfig
    requires_lineage: tuple[str, ...] = ()

    def __init__(self, config: TextParserConfig | None = None) -> None:
        """설정을 고정한다(설정은 `config_hash` → `fingerprint` → `stage_key` 입력)."""
        self.config = config or TextParserConfig()

    def config_hash(self) -> str:
        """`H("config", canonical_json(config))`(바이블 §6.2 근사)."""
        canonical = json.dumps(
            self.config.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), ensure_ascii=False
        )
        return hash_of("config", canonical)

    def capabilities(self) -> ct.Capabilities:
        """`isolation_modes=[in_process]`, `input_formats=[txt, md]`, 재개 미지원(04 §1.4)."""
        return ct.Capabilities(
            isolation_modes=[ct.IsolationMode.in_process],
            supports_resumable=False,
            contracts_compat=ct.ContractsCompat(">=1.0,<2.0"),
            input_formats=["txt", "md"],
            requires_gpu=False,
        )

    def fingerprint(self) -> str:
        """`H("producer", plugin_id, plugin_version, config_hash, "", "")`(인프로세스: 모델·이미지 없음)."""
        return hash_of("producer", self.plugin_id, PLUGIN_VERSION, self.config_hash(), "", "")

    async def run(self, inp: SourceDocument, ctx: Any) -> ParsedDocument:
        """셸이 제공하는 원본 바이트 포트(`ctx.source_bytes()`, 동기·비동기 모두 허용)로 바이트를 받는다."""
        port = getattr(ctx, "source_bytes", None)
        if port is None:
            raise StageError(
                _CONVERSION_FAILED,
                stage="parse",
                plugin_id=self.plugin_id,
                detail="StageContext has no source_bytes port",
            )
        data = port()
        if inspect.isawaitable(data):
            data = await data
        return await self.parse_bytes(bytes(data), inp, ctx)

    async def parse_bytes(self, data: bytes, inp: SourceDocument, ctx: Any) -> ParsedDocument:
        """TXT/Markdown/CSV 바이트 → `ParsedDocument`. 저장은 `ctx.artifacts.put_derived`로만 한다."""
        http_charset = inp.http_metadata.charset if inp.http_metadata else None
        language_hint = inp.metadata.language_hint.root if inp.metadata.language_hint else _BCP47_DEFAULT
        decoded = _decode(data, http_charset=http_charset, language_hint=language_hint, cfg=self.config.encoding)
        doc_version = inp.doc_version.root
        subroute = _choose_subroute(inp, self.config.csv)
        degraded = decoded.degraded
        title: str | None = None
        meta_extra: dict[str, Any] = {}

        if subroute == "md":
            profile_option, library_name = PROFILE_OPTION_MD, "markdown-it-py"
            body = decoded.text
            if self.config.md.frontmatter_to_metadata:
                body, frontmatter, fm_error = _extract_frontmatter(decoded.text)
                degraded = degraded or fm_error
                if frontmatter is not None:
                    meta_extra.update(_frontmatter_to_metadata(frontmatter))
            blocks, inferred_title = _build_md_blocks(body, doc_version)
            title = meta_extra.get("title") or inferred_title
        elif subroute == "csv":
            profile_option, library_name = PROFILE_OPTION_CSV, "charset-normalizer"
            blocks, csv_degraded = _build_csv_blocks(
                decoded.text, doc_version, self.config.csv, tsv_hint=_is_tsv_hint(inp)
            )
            degraded = degraded or csv_degraded
        else:
            profile_option, library_name = PROFILE_OPTION_TXT, "charset-normalizer"
            lines = decoded.text.split("\n")
            mode = _resolve_paragraph_mode(lines, self.config.txt.paragraph_mode)
            segments = _segment_txt(lines, mode=mode, indent_width=self.config.txt.indent_width)
            p1_level_map = _build_p1_level_map(segments) if self.config.txt.heading_inference else {}
            genre = inp.metadata.genre or _infer_genre(segments)
            ladder = _LAW_LADDER if genre == ct.Genre.law_article else _OUTLINE_LADDER
            classified = _classify_segments(segments, self.config.txt, ladder, p1_level_map)
            blocks, title = _assemble_txt_blocks(classified, doc_version)
            if genre is not None:
                meta_extra["genre"] = genre

        metadata = None
        if title is not None or meta_extra:
            metadata = DocumentMetadata(
                title=title,
                authors=meta_extra.get("authors"),
                created_at=meta_extra.get("created_at"),
                modified_at=meta_extra.get("modified_at"),
                genre=meta_extra.get("genre"),
            )
        language = meta_extra.get("language") or language_hint

        report = {"plugin_id": self.plugin_id, "profile_option": profile_option, **decoded.report}
        report_ref = _to_artifact_ref(
            await ctx.artifacts.put_derived(
                json.dumps(report, ensure_ascii=False, sort_keys=True).encode("utf-8"),
                kind="vendor_json",
                ext="json",
                media_type="application/json",
            )
        )
        artifacts = [DerivedArtifact(kind=ArtifactKind.vendor_json, ref=report_ref)]

        return ParsedDocument(
            schema_version=SCHEMA_VERSION,
            schema_type="ParsedDocument",
            tenant_id=inp.tenant_id,
            collection_id=inp.collection_id,
            producer=ct.Producer(
                plugin_id=self.plugin_id,
                plugin_version=PLUGIN_VERSION,
                config_hash=self.config_hash(),
                image_digest=None,
            ),
            quality=ct.Quality.degraded if degraded else ct.Quality.full,
            warnings=[],
            created_at=_rfc3339_ms(ctx.now()),
            lineage_refs=LineageRefs(source=inp.artifact),
            document_id=inp.document_id,
            doc_version=inp.doc_version,
            source_ref=inp.artifact,
            parser_fingerprint=ParserFingerprint(
                parser_id=self.plugin_id,
                parser_version=f"{library_name}=={package_version(library_name)}",
                sidecar_image_digest=None,
                profile_option=profile_option,
            ),
            parser_chain=[ct.PluginId(self.plugin_id)],
            source_kind=ct.SourceKind.flow,
            page_count=None,
            language=language,
            metadata=metadata,
            blocks=blocks,
            artifacts=artifacts,
            text_length=sum(len(b.text) for b in blocks),
            block_count=len(blocks),
            source_encoding=decoded.source_encoding,
        )
