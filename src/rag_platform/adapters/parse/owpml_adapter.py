"""OWPML(HWPX) 어댑터 코어 — HWPX 패키지를 열어 `Block` 트리·표·그림·각주·필드·메타데이터로 변환하는 순수 변환기.

설계 근거: 04-pipelines/04 §2·§3.1~§3.17(매핑 표·`element_path`·heading 추론·표·BinData·각주·필드·변경 추적)·§6,
바이블 §5.4 `ParsedDocument`/`Block`/`TableData`, ADR-0002. 파트는 python-hwpx `HwpxPackage`로 읽고 본문은 lxml 순회.
구성:
- `HwpxParserConfig` — 어댑터 설정(§10 제안 키의 구현 부분집합), `OwpmlPackage.open(data)` — 패키지 열기·파트 적재
- `HeaderIndex` — `header.xml` 색인, `prescan(...)` — 1패스 원시 통계(`H_body`·장르·랭크 사상표·제목·BinData)
- `build_blocks(...)` — 2패스 블록 생성 → `OwpmlResult`, `render_table_html(table)` — `html_ref`용 HTML
불변식: 결정성(XML 문서 순서, 통계는 1패스에서 고정). `Block.text`는 NFC 미적용 원문, `page`·`bbox`는 항상 null.
오류 코드는 §5.7 철자만 쓰고 `detail`에 본문을 넣지 않는다. 스토리지 접근 없음(그림 `ArtifactRef`는 호출자가 저장).
검증 계층: 1층(여기서 검증) — `tests/adapters/parse/test_hwpx.py`(공공누리 표본 3건 + 합성 표본, 회귀 스냅샷).
"""

from __future__ import annotations

import re
import statistics
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta, timezone
from html import escape
from typing import Any, Literal
from zipfile import BadZipFile

from hwpx import HwpxPackage
from hwpx.opc.package import HwpxPackageError
from hwpx.opc.security import HwpxSecurityError
from pydantic import BaseModel, ConfigDict, Field

from rag_platform.contracts import common_types as ct
from rag_platform.contracts.common_types.Block import figure as figure_enum, footnote as footnote_enum
from rag_platform.contracts.common_types.TableCell import HeaderKind
from rag_platform.contracts.common_types.TableData.quality import StructureSource
from rag_platform.contracts.parsed_document import (
    Annotation,
    Block,
    DerivedArtifact,
    DocumentMetadata,
    Figure,
    Footnote,
    FormFieldEntry,
    Formula,
    Link,
    PageBreak,
)
from rag_platform.contracts.parsed_document.ParsedDocument.annotations import Kind as AnnotationKind
from rag_platform.contracts.parsed_document.ParsedDocument.artifacts import Kind as ArtifactKind
from rag_platform.sdk.hashing import block_id as make_block_id
from rag_platform.sdk.stage import StageError

__all__ = [
    "PLUGIN_ID",
    "HeaderIndex",
    "HeadingInferenceConfig",
    "HwpxParserConfig",
    "OwpmlPackage",
    "OwpmlPlan",
    "OwpmlResult",
    "build_blocks",
    "prescan",
    "read_metadata",
    "render_table_html",
]

PLUGIN_ID = "parser.hwpx_python_hwpx"

# lxml 요소: lxml에는 타입 스텁이 없어 python-hwpx `get_xml()` 반환형이 mypy에서 Any로 풀린다(어댑터 경계).
type XmlElement = Any

MAX_BLOCK_TEXT = 1_000_000  # 03 §9: 블록 텍스트 ≤ 1MB — 코드포인트 기준 보수적 분할 단위
MAX_BLOCKS = 200_000
MAX_NESTING = 3  # 중첩 표·그룹 깊이 상한(§3.6·§3.10)

_OBJECT_TAGS = frozenset(
    {
        "tbl",
        "pic",
        "equation",
        "ole",
        "container",
        "rect",
        "ellipse",
        "arc",
        "polygon",
        "curve",
        "line",
        "connectLine",
        "chart",
        "video",
        "textart",
    }
)
_SHAPE_TAGS = frozenset({"rect", "ellipse", "arc", "polygon", "curve", "line", "connectLine"})
_SKIPPED_OBJECT_TAGS = frozenset({"chart", "video", "textart"})
_T_CHARS = {"tab": "\t", "lineBreak": "\n", "nbSpace": "\u00a0", "fwSpace": "\u3000", "hyphen": "\u2010"}
_T_SILENT = frozenset({"markpenBegin", "markpenEnd", "titleMark", "bookmark"})
_TRACK_MARKS = {
    "insertBegin": ("insert", 1),
    "insertEnd": ("insert", -1),
    "deleteBegin": ("delete", 1),
    "deleteEnd": ("delete", -1),
}
_BULLET_RANK = {"□": 0, "○": 1, "●": 1, "-": 2, "·": 3, "▪": 3}
_PARAGRAPH_LEADS = ("※", "붙임", "참고")
_HANGUL_ITEMS = "가나다라마바사아자차카타파하"
_AUTO_SHAPE_COMMENT = re.compile(r"^(그림|수식|OLE 개체|개체|표)입니다\.(\s|$)")
_STYLE_HEADING = re.compile(r"^(개요|Outline|제목)\s*([1-9])$")
_TITLE_STYLES = frozenset({"제목", "Title"})
_ARTICLE = re.compile(r"^\s*제\s?\d+조")
# 목차 표: 지시선(.. ·· … 또는 연속 공백) 뒤 쪽번호로 끝나는 셀, 또는 우측 열 전부 쪽번호(초안, §3.6 `toc` 행 강화)
_TOC_LEADER = re.compile(r".{3,}(?:\.{2,}|·{2,}|…+|\s{2,})\s*\d{1,4}$")
_PAGE_NO = re.compile(r"^\d{1,4}$")

# §3.4 3순위 번호 패턴(선두 공백 허용은 호출부에서 처리). (정규식, 정렬 키 함수) — 라벨은 그룹 1.
_PATTERNS: tuple[tuple[re.Pattern[str], int], ...] = (
    (re.compile(r"^(제\s?\d+\s?편)"), 1),
    (re.compile(r"^(제\s?\d+\s?장)"), 2),
    (re.compile(r"^(제\s?\d+\s?절)"), 3),
    (re.compile(r"^(제\s?\d+\s?관)"), 4),
    (re.compile(r"^(제\s?\d+조(?:의\s?\d+)?)(?=\s*(?:\([^)]{1,40}\))?)"), 5),
    (re.compile(r"^([ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩ]+\.|[IVX]+\.)"), 6),
    (re.compile(r"^(\d+(?:\.\d+)+\.?)"), 7),  # 정렬 키 = 7 + 점 개수(`_match_pattern`)
    (re.compile(r"^(\d+\.)(?!\d)"), 7),
    (re.compile(rf"^([{_HANGUL_ITEMS}]\.)"), 10),
    (re.compile(r"^(\d+\))"), 11),
    (re.compile(rf"^([{_HANGUL_ITEMS}]\))"), 12),
    (re.compile(rf"^(\(\d+\)|\([{_HANGUL_ITEMS}]\))"), 13),
    (re.compile(r"^([①-⑳])"), 14),
)
_ARTICLE_KEY = 5
_DECIMAL_KEY = 7
_CIRCLED_KEY = 14
# §3.4 장르 추론·§3.6 표 role 휴리스틱 임계(초안 — 골든셋으로 조정)
_ARTICLE_GENRE_MIN = 5
_FORM_GENRE_MAX_BODY = 20
_OUTLINE_GENRE_RATIO = 0.6
_FORM_EMPTY_RATIO = 0.3
_TOC_RATIO = 0.5
_TOC_MIN_ROWS = 3
_SHORT_LABEL = 12
_TITLE_WINDOW = 5

_KST = timezone(timedelta(hours=9))  # Asia/Seoul(1988년 이후 DST 없음) — 시간대 없는 메타 날짜 해석(§3.15 초안 규칙)


class HeadingInferenceConfig(BaseModel):
    """§3.4 3순위 heading 휴리스틱 설정(§10 `heading_inference`)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    enabled: bool = True
    min_score: int = Field(4, ge=1, le=5)
    max_label_free_len: int = Field(40, ge=1)
    font_delta: int = Field(100, ge=0, description="`hh:charPr/@height` 단위(1/100pt) 차이")


class HwpxParserConfig(BaseModel):
    """`parser.hwpx_python_hwpx` 설정 — §10 `ingest.parse.options.hwpx` 제안 키의 구현 부분집합."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    namespaces: tuple[str, ...] = (
        "http://www.hancom.co.kr/hwpml/2011",
        "http://www.hancom.co.kr/hwpml/2016",
        "http://www.owpml.org/owpml/2024",
    )
    heading_inference: HeadingInferenceConfig = HeadingInferenceConfig()
    tracked_changes: Literal["accept_all", "reject_all"] = "accept_all"
    max_bindata_bytes: int = Field(52_428_800, ge=0)
    drop_auto_shape_comment: bool = Field(
        default=True,
        description="한컴 자동 생성 `hp:shapeComment`('그림입니다.' + 원본 그림 이름·크기)는 대체 텍스트로 쓰지 않는다",
    )
    emit_table_html: bool = True


# ---------------------------------------------------------------------------------------------
# XML 헬퍼
# ---------------------------------------------------------------------------------------------


def _local(el: XmlElement) -> str:
    """요소의 로컬 이름(주석·처리 지시는 빈 문자열)."""
    tag = el.tag
    if not isinstance(tag, str):
        return ""
    return tag.rsplit("}", 1)[-1]


def _namespace(el: XmlElement) -> str:
    tag = el.tag
    if isinstance(tag, str) and tag.startswith("{"):
        return tag[1 : tag.index("}")]
    return ""


def _attr(el: XmlElement, name: str) -> str | None:
    value = el.get(name)
    return value if isinstance(value, str) else None


def _int_attr(el: XmlElement | None, name: str, default: int) -> int:
    if el is None:
        return default
    raw = _attr(el, name)
    try:
        return int(raw) if raw is not None else default
    except ValueError:
        return default


def _children(el: XmlElement, name: str | None = None) -> list[XmlElement]:
    return [c for c in el if _local(c) and (name is None or _local(c) == name)]


def _child(el: XmlElement, name: str) -> XmlElement | None:
    for c in el:
        if _local(c) == name:
            return c
    return None


def _descendants(el: XmlElement, name: str) -> list[XmlElement]:
    return [d for d in el.iter() if _local(d) == name]


def _switch_branch(switch: XmlElement) -> XmlElement | None:
    """`hp:switch`의 읽을 가지: `hp:default` 우선, 없으면 첫 `hp:case`(lxml 요소 진리값은 자식 수라 `or` 금지)."""
    branch = _child(switch, "default")
    return branch if branch is not None else _child(switch, "case")


def _script(equation: XmlElement) -> str:
    """`hp:equation/hp:script` 원문(한컴 수식 스크립트, §3.11)."""
    return "".join(str(s) for c in _children(equation, "script") for s in c.itertext())


def _plain_text(el: XmlElement) -> str:
    """요소 아래 `hp:t` 텍스트만 문서 순서로 연결(요약·사전 스캔용)."""
    return "".join("".join(str(s) for s in t.itertext()) for t in _descendants(el, "t"))


def _stage_error(detail: str, *, code: str) -> StageError:
    return StageError(code, stage="parse", plugin_id=PLUGIN_ID, detail=detail)


# ---------------------------------------------------------------------------------------------
# 패키지·헤더
# ---------------------------------------------------------------------------------------------


@dataclass
class OwpmlPackage:
    """열린 HWPX 패키지 — 구역·헤더 트리와 BinData 매니페스트(id → href, media-type)."""

    package: HwpxPackage
    sections: list[XmlElement]
    header: XmlElement
    manifest: dict[str, tuple[str, str]]
    content_hpf: XmlElement

    @classmethod
    def open(cls, data: bytes) -> OwpmlPackage:
        """바이트를 열어 필수 파트를 적재한다. 컨테이너·XML 손상은 `parse.corrupt_container`(§6)."""
        try:
            pkg = HwpxPackage.open(data)
            section_paths = pkg.section_paths()
            header_paths = pkg.header_paths()
            if not section_paths or not header_paths:
                msg = "OWPML required part missing (header or section)"
                raise _stage_error(msg, code="parse.corrupt_container")
            sections = [pkg.get_xml(path) for path in section_paths]
            header = pkg.get_xml(header_paths[0])
            content_hpf = pkg.manifest_tree()
            encrypted = pkg.has_part(pkg.MANIFEST_PATH) and bool(
                _descendants(pkg.get_xml(pkg.MANIFEST_PATH), "encryption-data")
            )
        except StageError:
            raise
        except (BadZipFile, HwpxPackageError, HwpxSecurityError, SyntaxError, OSError, KeyError) as exc:
            # lxml `XMLSyntaxError`는 `SyntaxError` 하위형, `HwpxSecurityError`는 `ValueError` 하위형(실측).
            msg = f"HWPX container open failed: {type(exc).__name__}"
            raise _stage_error(msg, code="parse.corrupt_container") from exc
        if encrypted:
            msg = "META-INF/manifest.xml declares encryption-data"
            raise _stage_error(msg, code="parse.document_encrypted")
        manifest: dict[str, tuple[str, str]] = {}
        for item in _descendants(content_hpf, "item"):
            item_id, href = _attr(item, "id"), _attr(item, "href")
            if item_id and href:
                manifest[item_id] = (href, _attr(item, "media-type") or "application/octet-stream")
        return cls(package=pkg, sections=sections, header=header, manifest=manifest, content_hpf=content_hpf)

    def binary(self, item_id: str) -> tuple[bytes, str, str] | None:
        """BinData 항목의 (바이트, 확장자, media type). 매니페스트·파트가 없으면 `None`."""
        entry = self.manifest.get(item_id)
        if entry is None or not self.package.has_part(entry[0]):
            return None
        href, media_type = entry
        ext = href.rsplit(".", 1)[-1].lower() if "." in href else "bin"
        return self.package.read(href), ext, media_type


@dataclass(frozen=True)
class _ParaHead:
    text: str
    num_format: str
    start: int


@dataclass
class HeaderIndex:
    """`Contents/header.xml` 색인(§2.2). 모든 키는 원문 id 문자열."""

    char_height: dict[str, int] = field(default_factory=dict)
    char_bold: dict[str, bool] = field(default_factory=dict)
    para_heading: dict[str, tuple[str, str, int]] = field(default_factory=dict)
    styles: dict[str, tuple[str, str]] = field(default_factory=dict)
    numberings: dict[str, dict[int, _ParaHead]] = field(default_factory=dict)
    bullets: dict[str, str] = field(default_factory=dict)
    borderless: dict[str, bool] = field(default_factory=dict)
    track_change_count: int = 0

    @classmethod
    def from_xml(cls, head: XmlElement) -> HeaderIndex:
        """`hh:head` 트리를 색인한다(로컬 이름 매칭 — 2011/2024 네임스페이스 공통)."""
        idx = cls()
        for el in head.iter():
            name = _local(el)
            el_id = _attr(el, "id")
            if name == "charPr" and el_id is not None:
                idx.char_height[el_id] = _int_attr(el, "height", 1000)
                idx.char_bold[el_id] = _child(el, "bold") is not None
            elif name == "paraPr" and el_id is not None:
                heading = next(iter(_descendants(el, "heading")), None)
                if heading is not None:
                    idx.para_heading[el_id] = (
                        _attr(heading, "type") or "NONE",
                        _attr(heading, "idRef") or "0",
                        _int_attr(heading, "level", 0),
                    )
            elif name == "style" and el_id is not None:
                idx.styles[el_id] = (_attr(el, "name") or "", _attr(el, "engName") or "")
            elif name == "numbering" and el_id is not None:
                idx.numberings[el_id] = {
                    _int_attr(ph, "level", 1): _ParaHead(
                        text="".join(str(s) for s in ph.itertext()),
                        num_format=_attr(ph, "numFormat") or "DIGIT",
                        start=_int_attr(ph, "start", 1),
                    )
                    for ph in _children(el, "paraHead")
                }
            elif name == "bullet" and el_id is not None:
                idx.bullets[el_id] = _attr(el, "char") or ""
            elif name == "borderFill" and el_id is not None:
                sides = [_child(el, s) for s in ("leftBorder", "rightBorder", "topBorder", "bottomBorder")]
                idx.borderless[el_id] = all(s is not None and _attr(s, "type") == "NONE" for s in sides)
            elif name == "trackChange":
                idx.track_change_count += 1
        return idx

    def heading_of(self, para_pr: str | None) -> tuple[str, str, int]:
        """`paraPrIDRef` → `hh:heading`의 (type, idRef, level). 없으면 `("NONE", "0", 0)`."""
        return self.para_heading.get(para_pr or "", ("NONE", "0", 0))

    def style_of(self, style_id: str | None) -> tuple[str, str]:
        """`styleIDRef` → (name, engName)."""
        return self.styles.get(style_id or "", ("", ""))


def _circled(n: int, first: int, count: int) -> str:
    return chr(first + n - 1) if 1 <= n <= count else str(n)


def _roman(n: int) -> str:
    table = (
        (1000, "M"),
        (900, "CM"),
        (500, "D"),
        (400, "CD"),
        (100, "C"),
        (90, "XC"),
        (50, "L"),
        (40, "XL"),
        (10, "X"),
        (9, "IX"),
        (5, "V"),
        (4, "IV"),
        (1, "I"),
    )
    out = []
    for value, sym in table:
        while n >= value:
            out.append(sym)
            n -= value
    return "".join(out) or "0"


def _format_number(n: int, num_format: str) -> str:
    """`hh:paraHead/@numFormat`·`hp:autoNumFormat/@type` 값으로 번호 문자열 생성(미지 형식은 아라비아 숫자)."""
    cyc = (n - 1) % 14 if n >= 1 else 0
    formats = {
        "DIGIT": lambda: str(n),
        "CIRCLED_DIGIT": lambda: _circled(n, 0x2460, 20),
        "ROMAN_CAPITAL": lambda: _roman(n),
        "ROMAN_SMALL": lambda: _roman(n).lower(),
        "LATIN_CAPITAL": lambda: chr(ord("A") + (n - 1) % 26),
        "LATIN_SMALL": lambda: chr(ord("a") + (n - 1) % 26),
        "CIRCLED_LATIN_CAPITAL": lambda: _circled(n, 0x24B6, 26),
        "CIRCLED_LATIN_SMALL": lambda: _circled(n, 0x24D0, 26),
        "HANGUL_SYLLABLE": lambda: _HANGUL_ITEMS[cyc],
        "CIRCLED_HANGUL_SYLLABLE": lambda: chr(0x326E + cyc),
        "HANGUL_JAMO": lambda: "ㄱㄴㄷㄹㅁㅂㅅㅇㅈㅊㅋㅌㅍㅎ"[cyc],
        "CIRCLED_HANGUL_JAMO": lambda: chr(0x3260 + cyc),
        "IDEOGRAPH": lambda: "一二三四五六七八九十"[(n - 1) % 10],
        "CIRCLED_IDEOGRAPH": lambda: _circled(n, 0x3280, 10),
    }
    return formats.get(num_format, formats["DIGIT"])()


class _NumberingCounter:
    """`(numbering id, level)`별 문서 순서 카운터(§3.5). 상위 레벨이 나오면 하위 레벨을 되돌린다."""

    def __init__(self, header: HeaderIndex) -> None:
        self._header = header
        self._counts: dict[str, dict[int, int]] = {}

    def next_label(self, numbering_id: str, level: int) -> str | None:
        """`level`(1-based, `hh:paraHead/@level` 기준)의 다음 번호 라벨. 형식 문자열이 비면 `None`."""
        heads = self._header.numberings.get(numbering_id, {})
        counts = self._counts.setdefault(numbering_id, {})
        head = heads.get(level)
        start = head.start if head else 1
        counts[level] = counts.get(level, start - 1) + 1
        for deeper in [lv for lv in counts if lv > level]:
            del counts[deeper]
        if head is None or not head.text:
            return None

        def substitute(match: re.Match[str]) -> str:
            lv = int(match.group(1))
            ph = heads.get(lv)
            value = counts.get(lv, ph.start if ph else 1)
            return _format_number(value, ph.num_format if ph else "DIGIT")

        return re.sub(r"\^(\d+)", substitute, head.text).strip() or None


# ---------------------------------------------------------------------------------------------
# 문단 텍스트 수집(§3.17)
# ---------------------------------------------------------------------------------------------


@dataclass
class _Inline:
    tag: str
    el: XmlElement
    offset: int
    path: str


@dataclass
class _NoteRef:
    kind: Literal["footnote", "endnote"]
    el: XmlElement
    offset: int
    path: str


@dataclass
class _FieldSpan:
    type: str
    name: str
    start: int
    end: int
    href: str | None


@dataclass
class _ParaContent:
    text: str = ""
    heights: list[int] = field(default_factory=list)
    bold: bool = False
    objects: list[_Inline] = field(default_factory=list)
    notes: list[_NoteRef] = field(default_factory=list)
    fields: list[_FieldSpan] = field(default_factory=list)
    changes: list[tuple[int, str]] = field(default_factory=list)
    headers: list[str] = field(default_factory=list)
    footers: list[str] = field(default_factory=list)
    tracked: bool = False


@dataclass
class _Report:
    """`vendor_json` 파서 리포트 누적기(본문 문자열 없음 — 요소명·개수·경로만)."""

    unknown_elements: dict[str, int] = field(default_factory=dict)
    skipped_objects: dict[str, int] = field(default_factory=dict)
    controls: dict[str, int] = field(default_factory=dict)
    dropped: list[dict[str, str]] = field(default_factory=list)
    foreign_namespaces: set[str] = field(default_factory=set)

    @staticmethod
    def bump(counter: dict[str, int], key: str) -> None:
        counter[key] = counter.get(key, 0) + 1

    def to_json(self) -> dict[str, Any]:
        return {
            "unknown_elements": dict(sorted(self.unknown_elements.items())),
            "skipped_objects": dict(sorted(self.skipped_objects.items())),
            "controls": dict(sorted(self.controls.items())),
            "dropped": self.dropped,
            "foreign_namespaces": sorted(self.foreign_namespaces),
        }


def _hyperlink_href(field_begin: XmlElement) -> str | None:
    """HYPERLINK 필드의 대상. `hp:parameters/hp:stringParam[@name=Command]`(한컴) → 없으면 `@name`(python-hwpx 실측)."""
    command = next(
        (
            "".join(str(s) for s in p.itertext())
            for p in _descendants(field_begin, "stringParam")
            if _attr(p, "name") == "Command"
        ),
        "",
    )
    href = command.split(";", 1)[0].replace("\\:", ":") if command else (_attr(field_begin, "name") or "")
    return href.strip() or None


class _ParagraphCollector:
    """한 `hp:p`의 런 텍스트·인라인 객체·컨트롤을 문서 순서로 수집한다(블록 생성 없음, 순수)."""

    def __init__(self, header: HeaderIndex, cfg: HwpxParserConfig, report: _Report, path: str) -> None:
        self._header = header
        self._cfg = cfg
        self._report = report
        self._path = path
        self._parts: list[str] = []
        self._pos = 0
        self._excluded: list[str] = []
        self._depth = {"insert": 0, "delete": 0}
        self._counters: dict[str, int] = {}
        self._open_fields: dict[str, tuple[str, str, int, str | None]] = {}
        self.out = _ParaContent()

    # -- 텍스트 방출 ------------------------------------------------------------------------
    def _is_excluded(self) -> bool:
        if self._cfg.tracked_changes == "accept_all":
            return self._depth["delete"] > 0
        return self._depth["insert"] > 0

    def _emit(self, text: str | None, char_pr: str | None) -> None:
        if not text:
            return
        if self._is_excluded():
            self._excluded.append(text)
            return
        self._parts.append(text)
        self._pos += len(text)
        if char_pr is not None and text.strip():
            self.out.heights.append(self._header.char_height.get(char_pr, 1000))
            self.out.bold = self.out.bold or self._header.char_bold.get(char_pr, False)

    def _flush_excluded(self) -> None:
        if self._excluded:
            self.out.changes.append((self._pos, "".join(self._excluded)))
            self._excluded = []

    def _next_index(self, tag: str) -> int:
        k = self._counters.get(tag, 0)
        self._counters[tag] = k + 1
        return k

    def _check_namespace(self, el: XmlElement) -> None:
        ns = _namespace(el)
        if ns and not any(ns.startswith(prefix) for prefix in self._cfg.namespaces):
            self._report.foreign_namespaces.add(ns)

    # -- 순회 ------------------------------------------------------------------------------
    def collect(self, p: XmlElement) -> _ParaContent:
        for child in p:
            name = _local(child)
            if name == "run":
                self._visit_run(child)
            elif name == "switch":
                branch = _switch_branch(child)
                if branch is not None:
                    for sub in branch:
                        if _local(sub) == "run":
                            self._visit_run(sub)
            elif name in {"linesegarray", ""}:
                continue
            else:
                self._unknown(child, None)
        self._flush_excluded()
        for ftype, fname, start, href in self._open_fields.values():
            self.out.fields.append(_FieldSpan(ftype, fname, start, self._pos, href))
        self._open_fields.clear()
        self.out.text = "".join(self._parts)
        return self.out

    def _visit_run(self, run: XmlElement) -> None:
        char_pr = _attr(run, "charPrIDRef")
        for child in run:
            name = _local(child)
            self._check_namespace(child)
            if name == "t":
                self._visit_t(child, char_pr)
            elif name == "ctrl":
                self._visit_ctrl(child, self._next_index("ctrl"))
            elif name in {"fieldBegin", "fieldEnd"}:
                self._visit_ctrl_child(child, f"{self._path}/hp:{name}[{self._next_index(name)}]")
            elif name in _OBJECT_TAGS:
                k = self._next_index(name)
                self.out.objects.append(_Inline(name, child, self._pos, f"{self._path}/hp:{name}[{k}]"))
            elif name == "switch":
                branch = _switch_branch(child)
                if branch is not None:
                    self._visit_run(branch)
            elif name in {"secPr", ""}:
                continue
            elif name == "dutmal":
                main = _child(child, "mainText")
                self._emit("".join(str(s) for s in (main if main is not None else child).itertext()), char_pr)
            elif name == "compose":
                self._emit(_attr(child, "composeText") or "".join(str(s) for s in child.itertext()), char_pr)
            else:
                self._unknown(child, char_pr)

    def _visit_t(self, t: XmlElement, char_pr: str | None) -> None:
        self._emit(t.text, char_pr)
        for child in t:
            name = _local(child)
            if name in _T_CHARS:
                self._emit(_T_CHARS[name], char_pr)
            elif name in _TRACK_MARKS:
                kind, delta = _TRACK_MARKS[name]
                self.out.tracked = True
                was_excluded = self._is_excluded()
                self._depth[kind] = max(0, self._depth[kind] + delta)
                if was_excluded and not self._is_excluded():
                    self._flush_excluded()
            elif name in _T_SILENT or not name:
                pass
            else:
                self._unknown(child, char_pr)
            self._emit(child.tail, char_pr)

    def _visit_ctrl(self, ctrl: XmlElement, k: int) -> None:
        for child in ctrl:
            name = _local(child)
            if name:
                self._visit_ctrl_child(child, f"{self._path}/hp:ctrl[{k}]/hp:{name}[0]")

    def _visit_ctrl_child(self, child: XmlElement, path: str) -> None:
        name = _local(child)
        if name in {"footNote", "endNote"}:
            kind: Literal["footnote", "endnote"] = "footnote" if name == "footNote" else "endnote"
            self.out.notes.append(_NoteRef(kind, child, self._pos, path))
        elif name in {"header", "footer"}:
            text = _flow_text(child, self._header, self._cfg, self._report, path)
            (self.out.headers if name == "header" else self.out.footers).append(text)
        elif name == "fieldBegin":
            ftype = _attr(child, "type") or ""
            href = _hyperlink_href(child) if ftype == "HYPERLINK" else None
            self._open_fields[_attr(child, "id") or path] = (ftype, _attr(child, "name") or "", self._pos, href)
        elif name == "fieldEnd":
            begin = self._open_fields.pop(_attr(child, "beginIDRef") or "", None)
            if begin is not None:
                self.out.fields.append(_FieldSpan(begin[0], begin[1], begin[2], self._pos, begin[3]))
        else:
            _Report.bump(self._report.controls, name)

    def _unknown(self, el: XmlElement, char_pr: str | None) -> None:
        """화이트리스트 밖 요소: `hp:t` 텍스트만 수집하고 요소명을 리포트에 남긴다(§3.1)."""
        _Report.bump(self._report.unknown_elements, _local(el))
        self._emit(_plain_text(el), char_pr)


def _collect(p: XmlElement, header: HeaderIndex, cfg: HwpxParserConfig, report: _Report, path: str) -> _ParaContent:
    return _ParagraphCollector(header, cfg, report, path).collect(p)


def _flow_text(container: XmlElement, header: HeaderIndex, cfg: HwpxParserConfig, report: _Report, path: str) -> str:
    """`hp:subList/hp:p*`(머리말·각주·캡션 등)를 줄바꿈으로 병합한 텍스트."""
    sub = _child(container, "subList")
    if sub is None:
        return ""
    texts = [
        _collect(p, header, cfg, report, f"{path}/hp:subList/hp:p[{m}]").text for m, p in enumerate(_children(sub, "p"))
    ]
    return "\n".join(t for t in texts if t.strip())


# ---------------------------------------------------------------------------------------------
# 1패스: 사전 스캔(§3.4 결정성 표)
# ---------------------------------------------------------------------------------------------


def _match_pattern(text: str) -> tuple[int, str, str] | None:
    """선두 번호 패턴 → (정렬 키, 라벨, 라벨 뒤 본문). 불일치면 `None`."""
    stripped = text.lstrip()
    for regex, base_key in _PATTERNS:
        m = regex.match(stripped)
        if m is None:
            continue
        label = m.group(1)
        key = base_key
        if base_key == _DECIMAL_KEY:  # 1.2 = 8, 3.1.4 = 9 (점 개수만큼 가산, "1." = 7)
            key = _DECIMAL_KEY + label.rstrip(".").count(".")
        rest = stripped[m.end(1) :].lstrip()
        return key, re.sub(r"\s+", "", label), rest
    return None


def _match_bullet(text: str) -> tuple[int, str, str] | None:
    stripped = text.lstrip()
    if not stripped or stripped[0] not in _BULLET_RANK:
        return None
    marker = stripped[0]
    rest = stripped[1:]
    if marker == "-" and rest and not rest[0].isspace():
        return None
    return _BULLET_RANK[marker], marker, rest.lstrip()


@dataclass(frozen=True)
class OwpmlPlan:
    """1패스 결과 — 2패스 동안 읽기 전용(§3.1 결정성)."""

    header: HeaderIndex
    body_height: int | None
    n_article: int
    n_marker: int
    n_body: int
    n_form_tbl: int
    rank_map: dict[int, int]
    title_path: str | None
    outline_ids: tuple[str, ...]
    binary_ids: tuple[str, ...]
    genre: ct.Genre | None
    opf_title: str | None


def _norm_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


@dataclass
class _ScanCounts:
    """1패스 원시 카운트(블록 분류 결과를 쓰지 않는다 — §3.4 순환 방지)."""

    heights: list[int] = field(default_factory=list)
    n_article: int = 0
    n_marker: int = 0
    n_body: int = 0
    n_form_tbl: int = 0
    keys: set[int] = field(default_factory=set)
    first_nonempty: list[tuple[str, str, XmlElement]] = field(default_factory=list)
    outline_ids: list[str] = field(default_factory=list)
    binary_ids: set[str] = field(default_factory=set)

    def paragraph(self, p: XmlElement, pc: _ParaContent, path: str, header: HeaderIndex) -> None:
        if not pc.text.strip():
            return
        self.n_body += 1
        if len(self.first_nonempty) < _TITLE_WINDOW:
            self.first_nonempty.append((path, pc.text, p))
        if header.heading_of(_attr(p, "paraPrIDRef"))[0] == "NONE":
            self.heights.extend(pc.heights)
        if _ARTICLE.match(pc.text):
            self.n_article += 1
        pattern = _match_pattern(pc.text)
        if pattern is not None:
            self.keys.add(pattern[0])
            self.n_marker += 1
        elif _match_bullet(pc.text) is not None:
            self.n_marker += 1

    def objects(self, sec: XmlElement) -> None:
        for tbl in _descendants(sec, "tbl"):
            cells = _descendants(tbl, "tc")
            empty = sum(1 for tc in cells if not _plain_text(tc).strip())
            if cells and empty / len(cells) >= _FORM_EMPTY_RATIO:
                self.n_form_tbl += 1
        for el in sec.iter():
            ref = _attr(el, "binaryItemIDRef") if _local(el) in {"img", "ole"} else None
            if ref:
                self.binary_ids.add(ref)

    def genre(self, hint: ct.Genre | None) -> ct.Genre | None:
        """§3.4 장르 추론(첫 일치): 힌트 → 조문 → 서식 → 개조식 → 생략."""
        if hint is not None:
            return hint
        if self.n_article >= _ARTICLE_GENRE_MIN:
            return ct.Genre.law_article
        if self.n_form_tbl >= 1 and self.n_body <= _FORM_GENRE_MAX_BODY:
            return ct.Genre.form
        if self.n_body > 0 and self.n_marker / self.n_body >= _OUTLINE_GENRE_RATIO:
            return ct.Genre.outline_report
        return None

    def title_path(self, header: HeaderIndex, opf_title: str | None) -> str | None:
        """순위 0 제목: 선두 5개 비어 있지 않은 문단 중 `제목`/`Title` 스타일, 없으면 `opf:title` 일치 문단."""
        for path, _text, p in self.first_nonempty:
            name, eng = header.style_of(_attr(p, "styleIDRef"))
            if name in _TITLE_STYLES or eng in _TITLE_STYLES:
                return path
        if not opf_title:
            return None
        return next((path for path, text, _ in self.first_nonempty if _norm_ws(text) == _norm_ws(opf_title)), None)


def prescan(pkg: OwpmlPackage, header: HeaderIndex, cfg: HwpxParserConfig, *, genre_hint: ct.Genre | None) -> OwpmlPlan:
    """1패스: 원시 카운트만 수집해 `genre`·랭크 사상표·제목 후보·참조 BinData를 고정한다."""
    report = _Report()
    counts = _ScanCounts()
    for sec_idx, sec in enumerate(pkg.sections):
        sec_pr = next(iter(_descendants(sec, "secPr")), None)
        counts.outline_ids.append((_attr(sec_pr, "outlineShapeIDRef") or "1") if sec_pr is not None else "1")
        for j, p in enumerate(_children(sec, "p")):
            path = f"/hp:sec[{sec_idx}]/hp:p[{j}]"
            counts.paragraph(p, _collect(p, header, cfg, report, path), path, header)
        counts.objects(sec)
    meta = pkg.package.document_metadata()
    opf_title = meta.title if meta is not None and meta.title else None
    return OwpmlPlan(
        header=header,
        body_height=statistics.median_low(counts.heights) if counts.heights else None,
        n_article=counts.n_article,
        n_marker=counts.n_marker,
        n_body=counts.n_body,
        n_form_tbl=counts.n_form_tbl,
        rank_map={key: min(pos, 6) for pos, key in enumerate(sorted(counts.keys), start=1)},
        title_path=counts.title_path(header, opf_title),
        outline_ids=tuple(counts.outline_ids),
        binary_ids=tuple(sorted(counts.binary_ids)),
        genre=counts.genre(genre_hint),
        opf_title=opf_title,
    )


# ---------------------------------------------------------------------------------------------
# 2패스: 블록 생성
# ---------------------------------------------------------------------------------------------


@dataclass
class _Kind:
    type: ct.BlockType
    text: str
    strip: int = 0
    level: int | None = None
    label: str | None = None
    ordered: bool | None = None
    inferred: bool | None = None


@dataclass
class _RawCell:
    row: int
    col: int
    row_span: int
    col_span: int
    text: str
    header: bool
    border: str | None
    path: str
    nested: str | None


@dataclass
class OwpmlResult:
    """2패스 산출물. `ParsedDocument` 봉투 조립은 스테이지(`hwpx_python_hwpx`)가 한다."""

    blocks: list[Block]
    annotations: list[Annotation]
    fields: list[FormFieldEntry]
    links: list[Link]
    artifacts: list[DerivedArtifact]
    table_html: dict[str, str]
    page_header_text: list[str]
    page_footer_text: list[str]
    has_tracked_changes: bool
    warnings: list[ct.Warning]
    degraded: bool
    report: dict[str, Any]


class _Builder:
    """§3.2 매핑 표를 문서 순서로 적용한다. 부모 규칙: heading 스택·list 스택(§3.4·§3.5)."""

    def __init__(
        self,
        *,
        plan: OwpmlPlan,
        doc_version: str,
        cfg: HwpxParserConfig,
        figure_refs: dict[str, ct.ArtifactRef],
        source: ct.BlockSource,
    ) -> None:
        self.plan = plan
        self.header = plan.header
        self.doc_version = doc_version
        self.cfg = cfg
        self.figure_refs = figure_refs
        self.source = source
        self.report = _Report()
        self.blocks: list[Block] = []
        self._paths: set[str] = set()
        self._ordinals: dict[str | None, int] = {}
        self._headings: list[tuple[int, str]] = []
        self._lists: list[tuple[int, str]] = []
        self._numbering = _NumberingCounter(self.header)
        self._outline_id = "1"
        self._endnotes: list[tuple[_NoteRef, str | None, int, int]] = []
        self._note_counter = {"footnote": 0, "endnote": 0}
        self.annotations: list[Annotation] = []
        self.fields: list[FormFieldEntry] = []
        self.links: list[Link] = []
        self.artifacts: list[DerivedArtifact] = []
        self.table_html: dict[str, str] = {}
        self.headers: list[str] = []
        self.footers: list[str] = []
        self.tracked = self.header.track_change_count > 0
        self.warnings: list[ct.Warning] = []
        self.degraded = False

    # -- 공통 --------------------------------------------------------------------------------
    def _warn(self, code: str, message: str, block_id: str | None = None) -> None:
        self.warnings.append(
            ct.Warning(
                code=ct.ErrorCodeCatalog(code), message=message, block_id=ct.Hex32(block_id) if block_id else None
            )
        )

    def _add(
        self,
        *,
        btype: ct.BlockType,
        path: str,
        parent: str | None,
        container: ct.BlockContainer,
        sec: int,
        text: str,
        **extra: Any,
    ) -> str:
        """블록 1개를 추가하고 `block_id`를 돌려준다. 1MB 초과 텍스트는 `/part[n]`로 분할(§3.1 크기)."""
        if len(text) > MAX_BLOCK_TEXT and btype != ct.BlockType.table:
            pieces = _split_text(text)
            self._warn("parse.block_oversized", f"block text split into {len(pieces)} parts")
            first = ""
            for n, piece in enumerate(pieces):
                bid = self._add(
                    btype=btype,
                    path=f"{path}/part[{n}]",
                    parent=parent,
                    container=container,
                    sec=sec,
                    text=piece,
                    **(extra if n == 0 else {}),
                )
                first = first or bid
            return first
        if path in self._paths:
            msg = "duplicate element_path generated"
            raise _stage_error(msg, code="parse.conversion_failed")
        if len(self.blocks) >= MAX_BLOCKS:
            msg = f"more than {MAX_BLOCKS} blocks"
            raise _stage_error(msg, code="parse.block_limit_exceeded")
        self._paths.add(path)
        bid = make_block_id(self.doc_version, path)
        ordinal = self._ordinals.get(parent, 0)
        self._ordinals[parent] = ordinal + 1
        self.blocks.append(
            Block(
                block_id=bid,
                type=btype,
                parent_block_id=ct.Hex32(parent) if parent is not None else None,
                ordinal=ordinal,
                text=text,
                furniture=False,
                container=container,
                source=self.source,
                confidence=None,
                provenance=ct.Provenance(
                    element_path=path, char_start=0, char_end=len(text), page=None, bbox=None, section_index=sec
                ),
                **extra,
            )
        )
        return bid

    def _current_heading(self) -> str | None:
        return self._headings[-1][1] if self._headings else None

    # -- 구역 --------------------------------------------------------------------------------
    def visit_section(self, sec_idx: int, sec: XmlElement) -> None:
        self._outline_id = self.plan.outline_ids[sec_idx] if sec_idx < len(self.plan.outline_ids) else "1"
        if sec_idx > 0:
            self._add(
                btype=ct.BlockType.page_break,
                path=f"/hp:sec[{sec_idx}]/hp:p[0]/hp:secPr[0]",
                parent=None,
                container=ct.BlockContainer.body,
                sec=sec_idx,
                text="",
                page_break=PageBreak(page_no=None, section_index=sec_idx),
            )
        j = 0
        for child in sec:
            name = _local(child)
            if name == "p":
                self._body_paragraph(child, f"/hp:sec[{sec_idx}]/hp:p[{j}]", sec_idx)
                j += 1
            elif name == "memogroup":
                self._memos(child)
            elif name:
                _Report.bump(self.report.unknown_elements, name)

    def _memos(self, group: XmlElement) -> None:
        for memo in _children(group, "memo"):
            text = "\n".join(t for t in (_plain_text(p) for p in _descendants(memo, "p")) if t)
            if not self.blocks:
                self.report.dropped.append({"element": "memo", "reason": "no anchor block"})
                continue
            # 메모 앵커(MEMO 필드) 해석은 미구현 — 직전 블록에 위치 0으로 귀속한다(스파이크 한계).
            self.annotations.append(
                Annotation(
                    kind=AnnotationKind.memo, block_id=self.blocks[-1].block_id, char_start=0, char_end=0, text=text
                )
            )

    # -- 분류(§3.4·§3.5) ---------------------------------------------------------------------
    def _classify(self, p: XmlElement, pc: _ParaContent, path: str) -> _Kind:
        text = pc.text
        htype, id_ref, hlevel = self.header.heading_of(_attr(p, "paraPrIDRef"))
        if path == self.plan.title_path:
            return _Kind(ct.BlockType.heading, text, level=0, inferred=False)
        if htype == "OUTLINE":
            numbering_id = id_ref if id_ref != "0" else self._outline_id
            label = self._numbering.next_label(numbering_id, hlevel + 1)
            return _Kind(ct.BlockType.heading, text, level=min(hlevel + 1, 6), label=label, inferred=False)
        name, eng = self.header.style_of(_attr(p, "styleIDRef"))
        style_match = _STYLE_HEADING.match(name) or _STYLE_HEADING.match(eng)
        if style_match:
            return _Kind(ct.BlockType.heading, text, level=min(int(style_match.group(2)), 6), inferred=False)
        if htype == "NUMBER":
            label = self._numbering.next_label(id_ref, hlevel + 1)
            return _Kind(ct.BlockType.list_item, text, level=hlevel, label=label, ordered=True)
        if htype == "BULLET":
            return _Kind(
                ct.BlockType.list_item, text, level=hlevel, label=self.header.bullets.get(id_ref) or None, ordered=False
            )
        return self._classify_text(pc)

    def _classify_text(self, pc: _ParaContent) -> _Kind:
        text = pc.text
        stripped = text.lstrip()
        if not self.cfg.heading_inference.enabled or stripped.startswith(_PARAGRAPH_LEADS):
            return _Kind(ct.BlockType.paragraph, text)
        pattern = _match_pattern(text)
        if pattern is not None:
            key, label, rest = pattern
            strip = len(text) - len(rest)
            rank = self.plan.rank_map.get(key, 1)
            hi = self.cfg.heading_inference
            body = self.plan.body_height
            big = bool(pc.heights) and body is not None and max(pc.heights) >= body + hi.font_delta
            score = 2 + int(len(rest.strip()) <= hi.max_label_free_len) + int(big or pc.bold)
            score += int(not rest.rstrip().endswith((".", "다", "함")))
            as_list = key == _CIRCLED_KEY or (key == _ARTICLE_KEY and self.plan.genre != ct.Genre.law_article)
            if score >= hi.min_score and not as_list:
                return _Kind(ct.BlockType.heading, rest, strip=strip, level=rank, label=label, inferred=True)
            return _Kind(ct.BlockType.list_item, rest, strip=strip, level=max(rank - 1, 0), label=label, ordered=True)
        bullet = _match_bullet(text)
        if bullet is not None:
            rank, marker, rest = bullet
            return _Kind(
                ct.BlockType.list_item, rest, strip=len(text) - len(rest), level=rank, label=marker, ordered=False
            )
        return _Kind(ct.BlockType.paragraph, text)

    def _place(self, kind: _Kind) -> str | None:
        """분류 결과의 부모 블록(스택 갱신 전)."""
        if kind.type == ct.BlockType.heading:
            level = kind.level or 0
            while self._headings and self._headings[-1][0] >= level:
                self._headings.pop()
            return self._current_heading()
        if kind.type == ct.BlockType.list_item:
            depth = kind.level or 0
            while self._lists and self._lists[-1][0] >= depth:
                self._lists.pop()
            if depth > 0 and self._lists:
                return self._lists[-1][1]
            return self._current_heading()
        return self._current_heading()

    def _push(self, kind: _Kind, bid: str) -> None:
        if kind.type == ct.BlockType.heading:
            self._headings.append((kind.level or 0, bid))
            self._lists.clear()
        elif kind.type == ct.BlockType.list_item:
            self._lists.append((kind.level or 0, bid))

    # -- 문단 --------------------------------------------------------------------------------
    def _body_paragraph(self, p: XmlElement, path: str, sec: int) -> None:
        pc = _collect(p, self.header, self.cfg, self.report, path)
        self._absorb(pc)
        kind = self._classify(p, pc, path) if pc.text.strip() else _Kind(ct.BlockType.paragraph, pc.text)
        bid: str | None = None
        if kind.text.strip():
            parent = self._place(kind)
            extra: dict[str, Any] = {}
            if kind.level is not None:
                extra["level"] = kind.level
            if kind.label is not None:
                extra["numbering_label"] = kind.label
            if kind.type == ct.BlockType.heading:
                extra["heading_inferred"] = bool(kind.inferred)
            if kind.ordered is not None:
                extra["ordered"] = kind.ordered
            bid = self._add(
                btype=kind.type,
                path=path,
                parent=parent,
                container=ct.BlockContainer.body,
                sec=sec,
                text=kind.text,
                **extra,
            )
            self._push(kind, bid)
            sibling_parent = parent
        else:
            sibling_parent = self._current_heading()
        self._attach_inline(
            pc, bid=bid, strip=kind.strip, parent=sibling_parent, container=ct.BlockContainer.body, sec=sec, depth=0
        )

    def _flow_paragraph(
        self, p: XmlElement, path: str, *, parent: str | None, container: ct.BlockContainer, sec: int, depth: int
    ) -> None:
        """글상자 등 흐름 컨테이너 안 문단(§3.10): heading·목록 추론 없이 `paragraph`."""
        pc = _collect(p, self.header, self.cfg, self.report, path)
        self._absorb(pc)
        bid = None
        if pc.text.strip():
            bid = self._add(
                btype=ct.BlockType.paragraph, path=path, parent=parent, container=container, sec=sec, text=pc.text
            )
        self._attach_inline(pc, bid=bid, strip=0, parent=parent, container=container, sec=sec, depth=depth)

    def _absorb(self, pc: _ParaContent) -> None:
        self.tracked = self.tracked or pc.tracked
        for text in pc.headers:
            if text and text not in self.headers:
                self.headers.append(text)
        for text in pc.footers:
            if text and text not in self.footers:
                self.footers.append(text)

    def _attach_inline(
        self,
        pc: _ParaContent,
        *,
        bid: str | None,
        strip: int,
        parent: str | None,
        container: ct.BlockContainer,
        sec: int,
        depth: int,
    ) -> None:
        """문단 뒤따름: 객체 블록(형제) → 각주(형제) → 필드·링크·변경 추적 주석(§3.2·§3.8·§3.12·§3.13)."""
        for obj in pc.objects:
            self._emit_object(obj, parent=parent, anchor=bid, container=container, sec=sec, depth=depth)
        for note in pc.notes:
            self._emit_note(note, anchor=bid, offset=max(0, note.offset - strip), parent=parent, sec=sec)
        if bid is None:
            if pc.fields or pc.changes:
                self.report.dropped.append({"element": "field_or_change", "reason": "empty anchor paragraph"})
            return
        anchor_text = next((b.text for b in reversed(self.blocks) if b.block_id.root == bid), "")
        text_len = len(anchor_text)
        for f in pc.fields:
            start = min(max(0, f.start - strip), text_len)
            end = min(max(start, f.end - strip), text_len)
            if f.type == "HYPERLINK" and f.href:
                self.links.append(Link(block_id=bid, char_start=start, char_end=end, href=f.href))
            else:
                self.fields.append(FormFieldEntry(name=f.name, type=f.type, value=anchor_text[start:end], block_id=bid))
        for pos, removed in pc.changes:
            at = min(max(0, pos - strip), text_len)
            self.annotations.append(
                Annotation(kind=AnnotationKind.tracked_change, block_id=bid, char_start=at, char_end=at, text=removed)
            )

    # -- 객체 --------------------------------------------------------------------------------
    def _emit_object(
        self,
        obj: _Inline,
        *,
        parent: str | None,
        anchor: str | None,
        container: ct.BlockContainer,
        sec: int,
        depth: int,
    ) -> None:
        if obj.tag == "tbl":
            self._emit_table(obj.el, obj.path, parent=parent, container=container, sec=sec, depth=depth + 1)
        elif obj.tag in {"pic", "ole"}:
            kind = figure_enum.Kind.image if obj.tag == "pic" else figure_enum.Kind.ole
            self._emit_figure(obj.el, obj.path, parent=parent, container=container, sec=sec, kind=kind)
        elif obj.tag == "equation":
            script = _script(obj.el)
            if script:
                self._add(
                    btype=ct.BlockType.formula,
                    path=obj.path,
                    parent=parent,
                    container=container,
                    sec=sec,
                    text=script,
                    formula=Formula(script=script, latex=None),
                )
        elif obj.tag == "container":
            if depth >= MAX_NESTING:
                self.degraded = True
                self._warn("parse.container_limit_exceeded", "shape group nesting deeper than 3")
                return
            counters: dict[str, int] = {}
            for child in obj.el:
                name = _local(child)
                if name in _OBJECT_TAGS:
                    k = counters.get(name, 0)
                    counters[name] = k + 1
                    inner = _Inline(name, child, obj.offset, f"{obj.path}/hp:{name}[{k}]")
                    self._emit_object(
                        inner, parent=parent, anchor=anchor, container=container, sec=sec, depth=depth + 1
                    )
        elif obj.tag in _SHAPE_TAGS:
            draw = _child(obj.el, "drawText")
            sub = _child(draw, "subList") if draw is not None else None
            if sub is None:
                _Report.bump(self.report.skipped_objects, obj.tag)
                return
            box_container = ct.BlockContainer.text_box if container == ct.BlockContainer.body else container
            for m, p in enumerate(_children(sub, "p")):
                self._flow_paragraph(
                    p,
                    f"{obj.path}/hp:drawText/hp:subList/hp:p[{m}]",
                    parent=anchor or parent,
                    container=box_container,
                    sec=sec,
                    depth=depth,
                )
        else:
            _Report.bump(self.report.skipped_objects, obj.tag)

    def _alt_text(self, el: XmlElement) -> str | None:
        comment = _child(el, "shapeComment")
        text = "".join(str(s) for s in comment.itertext()).strip() if comment is not None else ""
        if not text or (self.cfg.drop_auto_shape_comment and _AUTO_SHAPE_COMMENT.match(text)):
            return None
        return text

    def _caption(
        self,
        el: XmlElement,
        path: str,
        *,
        parent: str | None,
        container: ct.BlockContainer,
        sec: int,
        target: str,
        before: bool,
    ) -> str | None:
        cap = _child(el, "caption")
        if cap is None:
            return None
        side = (_attr(cap, "side") or "BOTTOM").upper()
        if (side in {"TOP", "LEFT"}) != before:
            return None
        cap_path = f"{path}/hp:caption[0]"
        text = _flow_text(cap, self.header, self.cfg, self.report, cap_path)
        if not text:
            return None
        return self._add(
            btype=ct.BlockType.caption,
            path=cap_path,
            parent=parent,
            container=container,
            sec=sec,
            text=text,
            caption_of=target,
        )

    def _caption_id(self, el: XmlElement, path: str) -> list[str] | None:
        cap = _child(el, "caption")
        if cap is None or not _flow_text(cap, self.header, self.cfg, _Report(), f"{path}/hp:caption[0]"):
            return None
        return [make_block_id(self.doc_version, f"{path}/hp:caption[0]")]

    def _emit_figure(
        self,
        el: XmlElement,
        path: str,
        *,
        parent: str | None,
        container: ct.BlockContainer,
        sec: int,
        kind: figure_enum.Kind,
    ) -> None:
        img = next(iter(_descendants(el, "img")), None)
        bin_id = _attr(el, "binaryItemIDRef") or (_attr(img, "binaryItemIDRef") if img is not None else None)
        ref = self.figure_refs.get(bin_id or "")
        if ref is None:
            # 계약상 `Figure.artifact`는 필수라 바이트가 없으면 블록을 만들 수 없다(§3.1 크기 행과 충돌 — 미해결).
            self.degraded = True
            self.report.dropped.append({"element": _local(el), "path": path, "reason": "binary missing or too large"})
            return
        fid = make_block_id(self.doc_version, path)
        self._caption(el, path, parent=parent, container=container, sec=sec, target=fid, before=True)
        alt = self._alt_text(el)
        self._add(
            btype=ct.BlockType.figure,
            path=path,
            parent=parent,
            container=container,
            sec=sec,
            text=alt or "",
            figure=Figure(artifact=ref, kind=kind, alt_text=alt),
            caption_block_ids=self._caption_id(el, path),
        )
        self.artifacts.append(DerivedArtifact(kind=ArtifactKind.figure_crop, ref=ref, block_id=ct.Hex32(fid)))
        self._caption(el, path, parent=parent, container=container, sec=sec, target=fid, before=False)

    # -- 각주(§3.8) --------------------------------------------------------------------------
    def _note_marker(self, note: _NoteRef) -> str:
        self._note_counter[note.kind] += 1
        auto = next(iter(_descendants(note.el, "autoNum")), None)
        number = _int_attr(auto, "num", _int_attr(note.el, "number", self._note_counter[note.kind]))
        fmt = _child(auto, "autoNumFormat") if auto is not None else None
        if fmt is None:
            return f"{number})"
        body = _attr(fmt, "userChar") if _attr(fmt, "type") == "USER_CHAR" else None
        body = body or _format_number(number, _attr(fmt, "type") or "DIGIT")
        return f"{_attr(fmt, 'prefixChar') or ''}{body}{_attr(fmt, 'suffixChar') or ''}"

    def _emit_note(self, note: _NoteRef, *, anchor: str | None, offset: int, parent: str | None, sec: int) -> None:
        if note.kind == "endnote":
            self._endnotes.append((note, anchor, offset, sec))
            return
        self._note_block(note, anchor=anchor, offset=offset, parent=parent, sec=sec)

    def _note_block(self, note: _NoteRef, *, anchor: str | None, offset: int, parent: str | None, sec: int) -> None:
        text = _flow_text(note.el, self.header, self.cfg, self.report, note.path)
        marker = self._note_marker(note)
        kind = footnote_enum.Kind.footnote if note.kind == "footnote" else footnote_enum.Kind.endnote
        bid = self._add(
            btype=ct.BlockType.footnote,
            path=note.path,
            parent=parent,
            container=ct.BlockContainer.footnote_body,
            sec=sec,
            text=text,
            footnote=Footnote(
                kind=kind, anchor_block_id=anchor, anchor_char_offset=offset if anchor else None, marker=marker
            ),
        )
        if anchor is None:
            self._warn("parse.footnote_unanchored", "footnote anchor paragraph has no text block", bid)

    def finish_endnotes(self) -> None:
        for note, anchor, offset, sec in self._endnotes:
            self._note_block(note, anchor=anchor, offset=offset, parent=None, sec=sec)
        self._endnotes.clear()

    # -- 표(§3.6) ----------------------------------------------------------------------------
    def _collect_cells(
        self, el: XmlElement, path: str, depth: int
    ) -> tuple[list[_RawCell], list[_Inline], list[tuple[_NoteRef, int]], bool]:
        """셀 순회: 앵커 셀(XML 순서)·셀 안 자식 객체·셀 안 각주(셀 인덱스)·중첩 깊이 보존 여부."""
        raw: list[_RawCell] = []
        children: list[_Inline] = []
        notes: list[tuple[_NoteRef, int]] = []
        preserved = True
        for r, tr in enumerate(_children(el, "tr")):
            for c, tc in enumerate(_children(tr, "tc")):
                cell_path = f"{path}/hp:tr[{r}]/hp:tc[{c}]"
                addr, span = _child(tc, "cellAddr"), _child(tc, "cellSpan")
                sub = _child(tc, "subList")
                texts: list[str] = []
                nested: str | None = None
                for m, p in enumerate(_children(sub, "p") if sub is not None else []):
                    pc = _collect(p, self.header, self.cfg, self.report, f"{cell_path}/hp:subList/hp:p[{m}]")
                    self._absorb(pc)
                    inserts: list[tuple[int, str]] = []
                    for obj in pc.objects:
                        if obj.tag == "tbl" and depth + 1 > MAX_NESTING:
                            inserts.append((obj.offset, _plain_text(obj.el)))  # 깊이 초과: 텍스트 평탄화(§3.6)
                            preserved = False
                            continue
                        if obj.tag == "tbl":
                            nested = make_block_id(self.doc_version, obj.path)
                        inserts.append((obj.offset, self._cell_placeholder(obj, nested)))
                        children.append(obj)
                    notes.extend((n, len(raw)) for n in pc.notes)
                    if pc.fields:
                        _Report.bump(self.report.controls, "field_in_table_cell")
                    texts.append(_splice(pc.text, inserts))
                raw.append(
                    _RawCell(
                        row=_int_attr(addr, "rowAddr", r),
                        col=_int_attr(addr, "colAddr", c),
                        row_span=max(1, _int_attr(span, "rowSpan", 1)),
                        col_span=max(1, _int_attr(span, "colSpan", 1)),
                        text="\n".join(texts),
                        header=_attr(tc, "header") == "1",
                        border=_attr(tc, "borderFillIDRef"),
                        path=cell_path,
                        nested=nested,
                    )
                )
        return raw, children, notes, preserved

    def _cell_placeholder(self, obj: _Inline, nested: str | None) -> str:
        """셀 텍스트 안 객체 자리: 중첩 표 `[table:{block_id}]`, 그림 `alt_text`, 수식 `script`(§3.6)."""
        if obj.tag == "tbl":
            return f"[table:{nested}]"
        if obj.tag in {"pic", "ole"}:
            return self._alt_text(obj.el) or ""
        if obj.tag == "equation":
            return _script(obj.el)
        return ""

    def _emit_table(
        self, el: XmlElement, path: str, *, parent: str | None, container: ct.BlockContainer, sec: int, depth: int
    ) -> None:
        tid = make_block_id(self.doc_version, path)
        raw, children, notes, preserved = self._collect_cells(el, path, depth)
        if not preserved:
            self.degraded = True
        n_rows, n_cols = _int_attr(el, "rowCnt", 0), _int_attr(el, "colCnt", 0)
        if not _grid_ok(raw, n_rows, n_cols):
            n_rows = max((cell.row + cell.row_span for cell in raw), default=0)
            n_cols = max((cell.col + cell.col_span for cell in raw), default=0)
            preserved = False
            self.degraded = True
            self._warn("parse.table_structure_fallback", "declared grid does not match cell spans", tid)
        role, header_rows, header_inferred = self._table_role(el, raw, n_rows, n_cols)
        cells, linear = _linearize(raw, header_rows, role, n_cols, sec)
        table = ct.TableData(
            n_rows=n_rows,
            n_cols=n_cols,
            cells=cells,
            header_row_indices=header_rows,
            header_inferred=header_inferred,
            role=role,
            quality=ct.Quality1(
                merged_cells_preserved=preserved, structure_source=StructureSource.native, structure_confidence=None
            ),
        )
        self._caption(el, path, parent=parent, container=container, sec=sec, target=tid, before=True)
        self._add(
            btype=ct.BlockType.table,
            path=path,
            parent=parent,
            container=container,
            sec=sec,
            text=linear,
            table=table,
            caption_block_ids=self._caption_id(el, path),
        )
        if self.cfg.emit_table_html:
            self.table_html[tid] = render_table_html(table)
        for obj in children:
            self._emit_object(obj, parent=tid, anchor=tid, container=ct.BlockContainer.table_cell, sec=sec, depth=depth)
        for note, cell_index in notes:
            prov = cells[cell_index].provenance
            start = prov.char_start if prov is not None else 0
            self._emit_note(note, anchor=tid, offset=start, parent=parent, sec=sec)
        self._caption(el, path, parent=parent, container=container, sec=sec, target=tid, before=False)

    def _table_role(
        self, el: XmlElement, raw: list[_RawCell], n_rows: int, n_cols: int
    ) -> tuple[ct.TableRole, list[ct.HeaderRowIndice], bool]:
        explicit = sorted({c.row for c in raw if c.header and all(o.header for o in raw if o.row == c.row)})
        if not explicit and _attr(el, "repeatHeader") == "1" and n_rows > 1:
            explicit = [0]
        borders = [_attr(el, "borderFillIDRef"), *(c.border for c in raw)]
        borderless = all(self.header.borderless.get(b or "", False) for b in borders)
        texts = [c.text for c in raw]
        nonempty = [t for t in texts if t.strip()]
        empty_ratio = (len(texts) - len(nonempty)) / len(texts) if texts else 0.0
        first_col = [c.text.strip() for c in raw if c.col == 0 and c.text.strip()]
        if (n_rows == 1 and n_cols == 1) or (borderless and not explicit):
            return ct.TableRole.layout, [], False
        last_col = [c.text.strip() for c in raw if c.col + c.col_span == n_cols and c.row not in explicit]
        leader_ratio = sum(1 for t in nonempty if _TOC_LEADER.match(t.strip())) / len(nonempty) if nonempty else 0.0
        page_column = n_cols > 1 and len(last_col) >= _TOC_MIN_ROWS and all(_PAGE_NO.match(t) for t in last_col)
        if leader_ratio >= _TOC_RATIO or page_column:
            role = ct.TableRole.toc
        elif empty_ratio >= _FORM_EMPTY_RATIO and first_col and all(len(t) <= _SHORT_LABEL for t in first_col):
            role = ct.TableRole.form
        else:
            role = ct.TableRole.data
        if explicit:
            return role, [ct.HeaderRowIndice(r) for r in explicit], False
        if n_rows > 1:
            return role, [ct.HeaderRowIndice(0)], True
        return role, [], False

    # -- 마무리 ------------------------------------------------------------------------------
    def result(self) -> OwpmlResult:
        return OwpmlResult(
            blocks=self.blocks,
            annotations=self.annotations,
            fields=self.fields,
            links=self.links,
            artifacts=self.artifacts,
            table_html=self.table_html,
            page_header_text=self.headers,
            page_footer_text=self.footers,
            has_tracked_changes=self.tracked,
            warnings=self.warnings,
            degraded=self.degraded or bool(self.report.dropped),
            report=self.report.to_json(),
        )


def _split_text(text: str) -> list[str]:
    pieces: list[str] = []
    while len(text) > MAX_BLOCK_TEXT:
        cut = text.rfind("\n", 0, MAX_BLOCK_TEXT)
        cut = cut + 1 if cut > 0 else MAX_BLOCK_TEXT
        pieces.append(text[:cut])
        text = text[cut:]
    pieces.append(text)
    return pieces


def _splice(text: str, inserts: list[tuple[int, str]]) -> str:
    if not inserts:
        return text
    out: list[str] = []
    last = 0
    for offset, value in sorted(inserts, key=lambda item: item[0]):
        out.extend((text[last:offset], value))
        last = offset
    out.append(text[last:])
    return "".join(out)


def _grid_ok(raw: list[_RawCell], n_rows: int, n_cols: int) -> bool:
    """앵커 셀이 선언 격자를 겹침 없이 빈틈없이 덮는지(P-12)."""
    if n_rows <= 0 or n_cols <= 0:
        return not raw
    occupied = [[False] * n_cols for _ in range(n_rows)]
    for cell in raw:
        if cell.row + cell.row_span > n_rows or cell.col + cell.col_span > n_cols:
            return False
        for rr in range(cell.row, cell.row + cell.row_span):
            for cc in range(cell.col, cell.col + cell.col_span):
                if occupied[rr][cc]:
                    return False
                occupied[rr][cc] = True
    return all(all(row) for row in occupied)


def _linearize(
    raw: list[_RawCell], header_rows: list[ct.HeaderRowIndice], role: ct.TableRole, n_cols: int, sec: int
) -> tuple[list[ct.TableCell], str]:
    """앵커 셀 행 우선 선형화(셀 U+0009, 행 U+000A) + `TableCell` 구간 provenance(§3.6). 반환 셀은 `raw` 순서."""
    header_set = {h.root for h in header_rows}
    order = sorted(range(len(raw)), key=lambda i: (raw[i].row, raw[i].col))
    spans: dict[int, tuple[int, int]] = {}
    parts: list[str] = []
    pos = 0
    current_row: int | None = None
    for i in order:
        cell = raw[i]
        if current_row is not None:
            sep = "\t" if cell.row == current_row else "\n"
            parts.append(sep)
            pos += 1
        current_row = cell.row
        spans[i] = (pos, pos + len(cell.text))
        parts.append(cell.text)
        pos += len(cell.text)
    cells: list[ct.TableCell] = []
    for i, cell in enumerate(raw):
        in_header = cell.row in header_set
        section_row = (
            not in_header and role == ct.TableRole.data and n_cols > 1 and cell.col == 0 and cell.col_span == n_cols
        )
        kind = HeaderKind.column if in_header else HeaderKind.section if section_row else HeaderKind.none
        start, end = spans[i]
        cells.append(
            ct.TableCell(
                row=cell.row,
                col=cell.col,
                row_span=cell.row_span,
                col_span=cell.col_span,
                text=cell.text,
                is_header=in_header or section_row,
                header_kind=kind,
                provenance=ct.Provenance(
                    element_path=cell.path, char_start=start, char_end=end, page=None, bbox=None, section_index=sec
                ),
                nested_table_block_id=cell.nested,
            )
        )
    return cells, "".join(parts)


def render_table_html(table: ct.TableData) -> str:
    """`TableData` → `<table>`(thead/tbody, rowspan/colspan, 스타일 없음). 셀 줄바꿈은 `<br>`."""
    header_set = {h.root for h in table.header_row_indices}
    rows: dict[int, list[ct.TableCell]] = {}
    for cell in sorted(table.cells, key=lambda c: (c.row, c.col)):
        rows.setdefault(cell.row, []).append(cell)

    def render_row(cells: list[ct.TableCell]) -> str:
        out = []
        for cell in cells:
            tag = "th" if cell.is_header else "td"
            attrs = (f' rowspan="{cell.row_span}"' if cell.row_span > 1 else "") + (
                f' colspan="{cell.col_span}"' if cell.col_span > 1 else ""
            )
            out.append(f"<{tag}{attrs}>{escape(cell.text).replace(chr(10), '<br>')}</{tag}>")
        return "<tr>" + "".join(out) + "</tr>"

    head = [render_row(cells) for r, cells in sorted(rows.items()) if r in header_set]
    body = [render_row(cells) for r, cells in sorted(rows.items()) if r not in header_set]
    thead = f"<thead>{''.join(head)}</thead>" if head else ""
    return f"<table>{thead}<tbody>{''.join(body)}</tbody></table>"


def build_blocks(
    pkg: OwpmlPackage,
    plan: OwpmlPlan,
    *,
    doc_version: str,
    cfg: HwpxParserConfig,
    figure_refs: dict[str, ct.ArtifactRef],
    source: ct.BlockSource = ct.BlockSource.text_layer,
) -> OwpmlResult:
    """2패스: 구역을 문서 순서로 순회해 블록을 만든다. `source`는 HWP 5.0 변환본이면 `converted`(§3.2)."""
    builder = _Builder(plan=plan, doc_version=doc_version, cfg=cfg, figure_refs=figure_refs, source=source)
    for sec_idx, sec in enumerate(pkg.sections):
        builder.visit_section(sec_idx, sec)
    builder.finish_endnotes()
    return builder.result()


# ---------------------------------------------------------------------------------------------
# 메타데이터(§3.15)
# ---------------------------------------------------------------------------------------------


def _rfc3339(raw: str | None) -> str | None:
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.strip())
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=_KST)
    utc = parsed.astimezone(UTC)
    return utc.strftime("%Y-%m-%dT%H:%M:%S.") + f"{utc.microsecond // 1000:03d}Z"


def read_metadata(pkg: OwpmlPackage, result: OwpmlResult, plan: OwpmlPlan) -> tuple[DocumentMetadata, str | None]:
    """`content.hpf` `opf:metadata`(python-hwpx `document_metadata()`) → `DocumentMetadata`와 `opf:language`."""
    meta = pkg.package.document_metadata()
    title = plan.opf_title
    if not title:
        title = next((b.text for b in result.blocks if b.type == ct.BlockType.heading and b.level == 0), None)
    authors: list[str] = []
    language = None
    created = modified = None
    if meta is not None:
        authors = [a.strip() for a in (meta.creator, meta.lastsaveby) if a and a.strip()]
        authors = list(dict.fromkeys(authors))
        language = meta.language.strip().lower() if meta.language else None
        created, modified = _rfc3339(meta.created_date), _rfc3339(meta.modified_date)
    return (
        DocumentMetadata(
            title=title or None,
            authors=authors or None,
            created_at=ct.DateTime(created) if created else None,
            modified_at=ct.DateTime(modified) if modified else None,
            page_header_text=result.page_header_text,
            page_footer_text=result.page_footer_text,
            has_tracked_changes=result.has_tracked_changes,
            genre=plan.genre,
        ),
        language,
    )
