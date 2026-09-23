"""`parser.html_trafilatura_docling` 파서 스테이지 — `SourceDocument`(format=html) 바이트를 `ParsedDocument`로 만든다.

설계 근거: 04-pipelines/07 §1(profile_option=html_standard)·§2(처리 개요)·§3(디코딩)·§4(DOM 전처리)·
§5(Trafilatura 본문 추출)·§6(구조 보존 파싱)·§8(메타데이터)·§10(Provenance), 바이블 §4.1(5멤버 프로토콜)·
§5.4 `ParsedDocument`·§6.2(지문 해시), ADR-0002. 이 WP(WP-104)는 지시 사양 요지로 범위를 좁혔다 — 정본
블록 경로는 (07 §7.1의 정제 XML 경로가 아니라) **전처리된 원본 DOM 경로**이며, Trafilatura는 메타데이터
보조 원천으로만 쓴다(스파이크 결과 §11 확인 필요 1·11과 일치).
구성: `HtmlParserConfig`/`HtmlSiteRule` — 설정, `HtmlTrafilaturaDoclingParser` — 스테이지 5멤버,
`docling_table_backend_placeholder` — Docling 구조 보조 자리(`needs_model`, 미구현).
불변식: 원본 바이트는 `ctx.source_bytes()` 포트로만 받는다. `ctx.artifacts.put_derived`만 쓰며 시계는
`ctx.now()`만 쓴다(순수성). 원격 자원은 가져오지 않는다(`data:` URI 이미지만 `figure`가 된다).
검증 계층: 1층(여기서 검증) — `tests/adapters/parse/test_html.py`(가짜 `StageContext`·인메모리 아티팩트).
"""

from __future__ import annotations

import base64
import codecs
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from html import escape
from importlib.metadata import version as package_version
from typing import TYPE_CHECKING, Any, Literal
from urllib.parse import unquote_to_bytes, urljoin, urlsplit, urlunsplit
from zoneinfo import ZoneInfo

import lxml.html
from pydantic import AnyUrl, BaseModel, ConfigDict, Field
from trafilatura import bare_extraction
from trafilatura.settings import Document as TrafilaturaDocument

from rag_platform.contracts import common_types as ct
from rag_platform.contracts.common_types.Block import figure as figure_kind_mod
from rag_platform.contracts.common_types.TableCell import HeaderKind
from rag_platform.contracts.common_types.TableData.quality import StructureSource
from rag_platform.contracts.parsed_document import (
    Block,
    Code,
    DerivedArtifact,
    DocumentMetadata,
    Figure,
    LineageRefs,
    Link,
    ParsedDocument,
    ParserFingerprint,
    WebMetadata,
)
from rag_platform.contracts.parsed_document.ParsedDocument.artifacts import Kind as ArtifactKind
from rag_platform.sdk.hashing import block_id as make_block_id, hash_of
from rag_platform.sdk.stage import StageError

if TYPE_CHECKING:
    from lxml.html import HtmlElement

    from rag_platform.contracts.source_document import SourceDocument

__all__ = [
    "PLUGIN_ID",
    "HtmlParserConfig",
    "HtmlSiteRule",
    "HtmlTrafilaturaDoclingParser",
    "docling_table_backend_placeholder",
]

PLUGIN_ID = "parser.html_trafilatura_docling"
PLUGIN_VERSION = "1.0.0"
SCHEMA_VERSION = "1.0.0"
_BCP47_DEFAULT = "ko"
_CONVERSION_FAILED = "parse.conversion_failed"


# ---------------------------------------------------------------------------------------------
# 설정(07 §12 부분집합 — cssselect 미설치로 선택자는 CSS 대신 XPath, WP 문서 "의도적 축소" 참조)
# ---------------------------------------------------------------------------------------------


class HtmlSiteRule(BaseModel):
    """사이트 규칙 한 항목. `main_selectors`/`remove_selectors`는 XPath(cssselect 미설치)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    rule_id: str
    hosts: tuple[str, ...] = ()
    main_selectors: tuple[str, ...] = ()
    remove_selectors: tuple[str, ...] = ()
    default_timezone: str = "Asia/Seoul"


class HtmlParserConfig(BaseModel):
    """`ingest.parse.options.html`의 이 WP 구현 부분집합(07 §12)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    mode: Literal["standard", "docs_site", "news"] = "standard"
    include_links: bool = True
    include_images: bool = True
    remove_hidden: bool = True
    min_main_text_chars: int = Field(200, ge=0)
    default_timezone: str = "Asia/Seoul"
    site_rules: tuple[HtmlSiteRule, ...] = ()
    use_docling_table_backend: bool = Field(
        default=False, description="needs_model 자리 — 참이면 NotImplementedError(모델 미탑재)"
    )


# ---------------------------------------------------------------------------------------------
# 디코딩(07 §3)
# ---------------------------------------------------------------------------------------------

_CP949_LABELS = frozenset(
    {
        "euc-kr",
        "euckr",
        "ks_c_5601-1987",
        "ks_c_5601-1989",
        "ksc5601",
        "ksc_5601",
        "korean",
        "windows-949",
        "x-windows-949",
        "uhc",
        "cp949",
    }
)
_UTF8_LABELS = frozenset({"utf8", "unicode-1-1-utf-8", "utf-8"})
_META_CHARSET_RE = re.compile(rb'charset\s*=\s*["\']?\s*([a-zA-Z0-9_\-:.]+)', re.IGNORECASE)


def _normalize_label(label: str) -> str:
    key = label.strip().lower()
    if key in _CP949_LABELS:
        return "cp949"
    if key in _UTF8_LABELS:
        return "utf-8"
    return key


def _sniff_meta_charset(prefix: bytes) -> str | None:
    match = _META_CHARSET_RE.search(prefix)
    return match.group(1).decode("ascii", errors="ignore") if match else None


def _decode_html(data: bytes, http_charset: str | None) -> tuple[str, str]:
    """BOM → meta 프리스캔 → `http_metadata.charset` → UTF-8(07 §3 순서, cp949 라벨 정규화)."""
    if data.startswith(codecs.BOM_UTF8):
        return data[len(codecs.BOM_UTF8) :].decode("utf-8"), "utf-8"
    if data.startswith(codecs.BOM_UTF16_LE):
        return data[2:].decode("utf-16-le"), "utf-16-le"
    if data.startswith(codecs.BOM_UTF16_BE):
        return data[2:].decode("utf-16-be"), "utf-16-be"

    candidates: list[str] = []
    meta_label = _sniff_meta_charset(data[:2048])
    if meta_label:
        candidates.append(_normalize_label(meta_label))
    if http_charset:
        candidates.append(_normalize_label(http_charset))
    candidates.append("utf-8")

    for encoding in dict.fromkeys(candidates):
        try:
            codecs.lookup(encoding)
        except LookupError:
            continue
        try:
            return data.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace"), "utf-8"


# ---------------------------------------------------------------------------------------------
# DOM 전처리(07 §4)
# ---------------------------------------------------------------------------------------------

_REMOVE_ALWAYS_TAGS = frozenset(
    {
        "script",
        "style",
        "noscript",
        "template",
        "object",
        "embed",
        "applet",
        "canvas",
        "audio",
        "video",
        "map",
        "area",
        "input",
        "select",
        "textarea",
        "button",
        "option",
        "datalist",
        "svg",
        "link",
        "meta",
    }
)

_HIDDEN_XPATH = (
    ".//*[@hidden] | .//*[@aria-hidden='true'] | "
    ".//*[@style and ("
    "contains(translate(@style,' \t',''),'display:none') or "
    "contains(translate(@style,' \t',''),'visibility:hidden') or "
    "contains(translate(@style,' \t',''),'opacity:0') or "
    "contains(translate(@style,' \t',''),'font-size:0'))]"
)

_LANDMARK_XPATH = (
    ".//nav | .//aside | .//footer | .//header[not(ancestor::article)] | "
    ".//*[@role='navigation' or @role='banner' or @role='contentinfo' or @role='complementary']"
)

_DEFAULT_MAIN_XPATHS = (
    ".//article",
    ".//main",
    ".//*[@role='main']",
    ".//div[contains(concat(' ',normalize-space(@class),' '),' board_view ')]"
    "//div[contains(concat(' ',normalize-space(@class),' '),' cont ')]",
    ".//td[contains(concat(' ',normalize-space(@class),' '),' content ')]",
    ".//*[@id='content']//*[contains(concat(' ',normalize-space(@class),' '),' view_cont ')]",
    ".//*[contains(concat(' ',normalize-space(@class),' '),' bbs_content ')]",
    ".//div[contains(concat(' ',normalize-space(@class),' '),' cont ')]",
)

_LINK_ATTR_TAGS = (("a", "href"), ("img", "src"), ("source", "src"))


def _text_of(elem: HtmlElement) -> str:
    return " ".join("".join(elem.itertext()).split())


def _collect_navigation_text(tree: HtmlElement) -> list[str]:
    """랜드마크 텍스트를 `navigation_text`로 모으고 트리에서 제거한다(07 §7.2)."""
    seen: list[str] = []
    for elem in list(tree.xpath(_LANDMARK_XPATH)):
        text = _text_of(elem)
        if text and text not in seen:
            seen.append(text)
        parent = elem.getparent()
        if parent is not None:
            parent.remove(elem)
    return seen[:200]


def _remove_non_content(tree: HtmlElement, *, remove_hidden: bool) -> None:
    for elem in list(tree.iter()):
        if not isinstance(elem.tag, str):
            parent = elem.getparent()
            if parent is not None:
                parent.remove(elem)
    for elem in list(tree.iter()):
        if isinstance(elem.tag, str) and elem.tag in _REMOVE_ALWAYS_TAGS:
            parent = elem.getparent()
            if parent is not None:
                parent.remove(elem)
    if remove_hidden:
        for elem in list(tree.xpath(_HIDDEN_XPATH)):
            parent = elem.getparent()
            if parent is not None:
                parent.remove(elem)


def _strip_userinfo(url: str) -> str:
    parts = urlsplit(url)
    if "@" not in parts.netloc:
        return url
    netloc = parts.netloc.rsplit("@", 1)[-1]
    return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))


def _absolutize_links(tree: HtmlElement, base_url: str) -> None:
    for tag, attr in _LINK_ATTR_TAGS:
        for elem in tree.iter(tag):
            value = elem.get(attr)
            if not value or value.startswith(("javascript:", "#")):
                continue
            elem.set(attr, _strip_userinfo(urljoin(base_url, value)))


# ---------------------------------------------------------------------------------------------
# 메타데이터(07 §8 부분집합 — title, og:*, published_time, lang, canonical)
# ---------------------------------------------------------------------------------------------


def _meta_content(tree: HtmlElement, *, prop: str | None = None, name: str | None = None) -> str | None:
    if prop:
        found = tree.xpath(f".//meta[@property='{prop}']/@content")
    else:
        found = tree.xpath(f".//meta[@name='{name}']/@content")
    value = str(found[0]).strip() if found else ""
    return value or None


def _rfc3339_ms(moment: datetime) -> str:
    utc = moment.astimezone(UTC)
    return utc.strftime("%Y-%m-%dT%H:%M:%S.") + f"{utc.microsecond // 1000:03d}Z"


def _parse_published_time(raw: str | None, *, default_timezone: str) -> str | None:
    if not raw:
        return None
    try:
        moment = datetime.fromisoformat(raw.strip())
    except ValueError:
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=ZoneInfo(default_timezone))
    return _rfc3339_ms(moment)


def _extract_metadata(
    tree: HtmlElement, *, base_url: str, language_hint: str | None, config: HtmlParserConfig
) -> tuple[DocumentMetadata, str]:
    """제거 전 트리에서 title/og:*/published_time/lang/canonical을 읽는다(07 §8)."""
    og_title = _meta_content(tree, prop="og:title")
    title_tag = tree.xpath(".//title/text()")
    title_tag_text = str(title_tag[0]).strip() if title_tag else None
    h1_tag = tree.xpath(".//h1")
    h1_text = _text_of(h1_tag[0]) if h1_tag else None
    title = og_title or title_tag_text or h1_text or None

    canonical = tree.xpath(".//link[@rel='canonical']/@href")
    canonical_url = urljoin(base_url, str(canonical[0])) if canonical else _meta_content(tree, prop="og:url")

    site_name = _meta_content(tree, prop="og:site_name")
    published_raw = _meta_content(tree, prop="article:published_time")
    published = _parse_published_time(published_raw, default_timezone=config.default_timezone)

    html_lang = tree.get("lang") if tree.tag == "html" else None
    content_language = _meta_content(tree, name="content-language")
    og_locale = _meta_content(tree, prop="og:locale")
    language = (
        language_hint
        or (html_lang.strip() if html_lang else None)
        or content_language
        or (og_locale.replace("_", "-") if og_locale else None)
        or _BCP47_DEFAULT
    )

    og_type = _meta_content(tree, prop="og:type")
    genre = ct.Genre.web_article if og_type == "article" else None

    published_at = ct.DateTime(published) if published else None
    web = None
    if canonical_url or site_name or published_at:
        canonical_uri = ct.Uri(AnyUrl(canonical_url)) if canonical_url else None
        web = WebMetadata(canonical_url=canonical_uri, site_name=site_name, published_at=published_at, author=None)

    metadata = DocumentMetadata(title=title, created_at=published_at, web=web, genre=genre)
    return metadata, language


def _run_trafilatura_metadata(text: str, base_url: str, config: HtmlParserConfig) -> dict[str, Any]:
    """Trafilatura 본문 추출 — 메타데이터 보조 원천·본문 충분성 신호(07 §5, WP "의도적 축소" 참조)."""
    favor_recall = config.mode == "docs_site"
    favor_precision = config.mode == "news"
    try:
        document = bare_extraction(
            text,
            url=base_url,
            output_format="xml",
            with_metadata=True,
            include_tables=True,
            include_links=config.include_links,
            include_images=config.include_images,
            include_comments=False,
            include_formatting=False,
            favor_recall=favor_recall,
            favor_precision=favor_precision,
            deduplicate=False,
        )
    except Exception:  # noqa: BLE001 - Trafilatura는 보조 원천, 실패해도 DOM 경로로 계속 진행
        return {"used": False}
    if document is None or not isinstance(document, TrafilaturaDocument):
        # `as_dict`를 넘기지 않았으므로 런타임 값은 항상 Document | None이다(dict 분기는
        # 정적 시그니처상으로만 존재) — 방어적으로만 처리하고 dict 분기는 보조 원천 미사용으로 본다.
        return {"used": False}
    body_text = "".join(document.body.itertext()) if document.body is not None else ""
    return {
        "used": True,
        "title": document.title,
        "author": document.author,
        "date": document.date,
        "sitename": document.sitename,
        "text_length": len(body_text.split()),
    }


# ---------------------------------------------------------------------------------------------
# DOM 경로(07 §10 DOM 모드 열 — 0-based 같은 이름 형제)
# ---------------------------------------------------------------------------------------------


def _dom_path(elem: HtmlElement) -> str:
    parts: list[str] = []
    node: HtmlElement | None = elem
    while node is not None:
        parent = node.getparent()
        if parent is None:
            parts.append(f"{node.tag}[0]")
            break
        index = 0
        for sib in parent:
            if sib is node:
                break
            if sib.tag == node.tag:
                index += 1
        parts.append(f"{node.tag}[{index}]")
        node = parent
    return "/" + "/".join(reversed(parts))


# ---------------------------------------------------------------------------------------------
# 텍스트 규칙(07 §6.3)
# ---------------------------------------------------------------------------------------------

_LABEL_RE = re.compile(r"^(\d{1,3}[.)]|[가-힣][.)]|[①-⑳]|[-•·○□■▶])\s+")
_ASCII_WS_RUN_RE = re.compile(r"[ \t\f\v]+")
_LINE_EDGE_WS_RE = re.compile(r"(?:^[ \t]+)|(?:[ \t]+$)", re.MULTILINE)


def _inline_text(elem: HtmlElement, *, skip_ids: frozenset[int] = frozenset()) -> str:
    r"""텍스트 노드를 문서 순서로 이어 붙인다(`br`→`\n`, NBSP·전각 보존)."""
    parts: list[str] = []

    def walk(node: HtmlElement) -> None:
        if node.text:
            parts.append(node.text)
        for child in node:
            tag = child.tag
            if not isinstance(tag, str) or id(child) in skip_ids:
                pass
            elif tag == "br":
                parts.append("\n")
            else:
                walk(child)
            if child.tail:
                parts.append(child.tail)

    walk(elem)
    return "".join(parts)


def _normalize_paragraph_text(raw: str) -> str:
    collapsed = _ASCII_WS_RUN_RE.sub(" ", raw)
    trimmed = _LINE_EDGE_WS_RE.sub("", collapsed)
    return trimmed.strip("\n")


def _split_segments(raw: str) -> list[str]:
    r"""2개 이상 연속 `\n`(≈ `<br><br>`)을 문단 경계로 본다(07 §6.3)."""
    out: list[str] = []
    for chunk in re.split(r"\n{2,}", raw):
        text = _normalize_paragraph_text(chunk)
        if text:
            out.append(text)
    return out


def _extract_numbering_label(text: str) -> tuple[str, str | None]:
    match = _LABEL_RE.match(text)
    if not match:
        return text, None
    return text[match.end() :], match.group(1)


def _is_inline_only(elem: HtmlElement) -> bool:
    block_tags = _BLOCK_DISPATCH_TAGS
    return not any(isinstance(d.tag, str) and d.tag in block_tags for d in elem.iterdescendants())


_BLOCK_DISPATCH_TAGS = frozenset(
    {"h1", "h2", "h3", "h4", "h5", "h6", "p", "ul", "ol", "table", "pre", "blockquote", "figure", "div"}
)


# ---------------------------------------------------------------------------------------------
# 표(07 §6.5) — Docling 없이 원본 rowspan/colspan에서 직접 격자를 세운다(native)
# ---------------------------------------------------------------------------------------------


@dataclass(slots=True)
class _RawCell:
    """표 격자 계산용 임시 앵커 셀(07 §6.5). `ct.TableCell`로 변환되기 전 중간 표현."""

    row: int
    col: int
    row_span: int
    col_span: int
    text: str
    is_header: bool
    path: str


def _int_attr(elem: HtmlElement, name: str, default: int) -> int:
    raw = elem.get(name)
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return value if value >= 1 else default


def _direct_rows(table: HtmlElement) -> list[HtmlElement]:
    rows: list[HtmlElement] = []

    def walk(node: HtmlElement) -> None:
        for child in node:
            tag = child.tag
            if tag == "tr":
                rows.append(child)
            elif tag == "table":
                continue
            elif isinstance(tag, str):
                walk(child)

    walk(table)
    return rows


def _direct_cells(tr: HtmlElement) -> list[HtmlElement]:
    return [c for c in tr if isinstance(c.tag, str) and c.tag in ("td", "th")]


def _cell_text(cell: HtmlElement) -> str:
    nested_tables = frozenset(id(t) for t in cell.iter("table"))
    return _normalize_paragraph_text(_inline_text(cell, skip_ids=nested_tables))


def _row_in_thead(tr: HtmlElement) -> bool:
    parent = tr.getparent()
    return parent is not None and parent.tag == "thead"


def _build_table_grid(table: HtmlElement, table_path: str) -> tuple[list[_RawCell], int, int]:
    rows = _direct_rows(table)
    occupied: dict[int, set[int]] = {}
    raw_cells: list[_RawCell] = []
    n_cols = 0
    for r, tr in enumerate(rows):
        col_cursor = 0
        row_occupied = occupied.setdefault(r, set())
        for cell in _direct_cells(tr):
            while col_cursor in row_occupied:
                col_cursor += 1
            row_span = _int_attr(cell, "rowspan", 1)
            col_span = _int_attr(cell, "colspan", 1)
            raw_cells.append(
                _RawCell(
                    row=r,
                    col=col_cursor,
                    row_span=row_span,
                    col_span=col_span,
                    text=_cell_text(cell),
                    is_header=cell.tag == "th",
                    path=f"{table_path}/cell[{r}][{col_cursor}]",
                )
            )
            for rr in range(r, r + row_span):
                occupied.setdefault(rr, set()).update(range(col_cursor, col_cursor + col_span))
            col_cursor += col_span
            n_cols = max(n_cols, col_cursor)
    return raw_cells, len(rows), n_cols


def _grid_ok(cells: list[_RawCell], n_rows: int, n_cols: int) -> bool:
    if n_rows <= 0 or n_cols <= 0:
        return not cells
    grid = [[False] * n_cols for _ in range(n_rows)]
    for cell in cells:
        if cell.row + cell.row_span > n_rows or cell.col + cell.col_span > n_cols:
            return False
        for rr in range(cell.row, cell.row + cell.row_span):
            for cc in range(cell.col, cell.col + cell.col_span):
                if grid[rr][cc]:
                    return False
                grid[rr][cc] = True
    return all(all(row) for row in grid)


def _header_rows(table: HtmlElement, cells: list[_RawCell], n_rows: int, role: ct.TableRole) -> tuple[list[int], bool]:
    """Thead 행 또는 첫 행 전부 `th` → 확정 헤더; 그 외 `form`이 아니고 2행 이상이면 0행을 추정 헤더로 본다.

    `form`(키-값) 표는 열 헤더가 아니라 행 헤더(첫 열)를 쓰므로 0행 추정 폴백에서 제외한다(07 §6.5).
    """
    rows = _direct_rows(table)
    thead_rows = [i for i, tr in enumerate(rows) if _row_in_thead(tr)]
    if thead_rows:
        return thead_rows, False
    first_row = [c for c in cells if c.row == 0]
    if first_row and all(c.is_header for c in first_row):
        return [0], False
    if role != ct.TableRole.form and n_rows > 1:
        return [0], True
    return [], False


_FORM_ROLE_COLS = 2


def _table_role(cells: list[_RawCell], n_rows: int, n_cols: int, *, presentation: bool) -> ct.TableRole:
    """`layout`(장식·`presentation`)·`form`(2열 키-값)·`data`(그 외) 판정(07 §6.5 축소판)."""
    if presentation or (n_rows == 1 and n_cols == 1):
        return ct.TableRole.layout
    first_col = [c.text.strip() for c in cells if c.col == 0 and c.text.strip()]
    if n_cols == _FORM_ROLE_COLS and first_col and len(first_col) >= max(n_rows - 1, 1):
        return ct.TableRole.form
    return ct.TableRole.data


def _linearize_cells(cells: list[_RawCell], header_rows: list[int]) -> tuple[list[ct.TableCell], str]:
    header_set = frozenset(header_rows)
    order = sorted(range(len(cells)), key=lambda i: (cells[i].row, cells[i].col))
    parts: list[str] = []
    spans: dict[int, tuple[int, int]] = {}
    pos = 0
    current_row: int | None = None
    for i in order:
        cell = cells[i]
        if current_row is not None:
            sep = "\t" if cell.row == current_row else "\n"
            parts.append(sep)
            pos += 1
        current_row = cell.row
        spans[i] = (pos, pos + len(cell.text))
        parts.append(cell.text)
        pos += len(cell.text)
    first_col_headers = {c.row for c in cells if c.col == 0} - header_set
    row_header_rows = {r for r in first_col_headers if all(c.is_header for c in cells if c.row == r and c.col == 0)}
    result: list[ct.TableCell] = []
    for i, cell in enumerate(cells):
        in_header = cell.row in header_set
        is_row_header = cell.col == 0 and cell.row in row_header_rows
        kind = HeaderKind.column if in_header else HeaderKind.row if is_row_header else HeaderKind.none
        start, end = spans[i]
        result.append(
            ct.TableCell(
                row=cell.row,
                col=cell.col,
                row_span=cell.row_span,
                col_span=cell.col_span,
                text=cell.text,
                is_header=in_header or is_row_header,
                header_kind=kind,
                provenance=ct.Provenance(
                    element_path=cell.path, char_start=start, char_end=end, page=None, bbox=None, section_index=None
                ),
                nested_table_block_id=None,
            )
        )
    return result, "".join(parts)


def render_table_html(table: ct.TableData) -> str:
    """`TableData` → `<table>`(thead/tbody, rowspan/colspan) — `table_html` 파생물용(07 §6.5)."""
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


# ---------------------------------------------------------------------------------------------
# 이미지(07 §9.3)
# ---------------------------------------------------------------------------------------------

_DATA_URI_RE = re.compile(r"^data:(?P<mime>[^;,]*)?(?:;[^;,]+)*(?P<b64>;base64)?,(?P<data>.*)$", re.DOTALL)
_FILENAME_ALT_RE = re.compile(r"\.(?:jpe?g|png|gif|svg|webp|bmp)$", re.IGNORECASE)
_EXT_FOR_MIME = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/gif": "gif",
    "image/svg+xml": "svg",
    "image/webp": "webp",
    "image/bmp": "bmp",
}


def _decode_data_uri(src: str) -> tuple[bytes, str] | tuple[None, None]:
    match = _DATA_URI_RE.match(src)
    if not match:
        return None, None
    mime = match.group("mime") or "application/octet-stream"
    raw = match.group("data")
    try:
        payload = base64.b64decode(raw, validate=False) if match.group("b64") else unquote_to_bytes(raw)
    except (ValueError, base64.binascii.Error):  # type: ignore[attr-defined]
        return None, None
    return payload, mime


_MIN_MEANINGFUL_ALT_LEN = 2


def _meaningful_alt(alt: str) -> bool:
    stripped = alt.strip()
    return len(stripped) >= _MIN_MEANINGFUL_ALT_LEN and not _FILENAME_ALT_RE.search(stripped)


# ---------------------------------------------------------------------------------------------
# Docling 구조 보조 — needs_model 자리(모델 가중치 다운로드 금지)
# ---------------------------------------------------------------------------------------------


def docling_table_backend_placeholder(table_html: str) -> None:
    """Docling `HTMLDocumentBackend` 연동 자리(07 §6.5·§7.1). 모델 사이드카 환경에서만 구현 가능.

    # DEFERRED: needs_model — 실제 Docling 표 재구조화 연동은 모델 가중치가 있는 환경(사이드카)에서
    # 별도 후속 WP로 구현한다. 이 스테이지는 표를 원본 `rowspan`/`colspan`에서 직접(native) 세우므로
    # 정상 경로에서는 이 함수가 호출되지 않는다.
    """
    del table_html
    msg = "Docling HTMLDocumentBackend integration requires model weights (needs_model); not implemented here"
    raise NotImplementedError(msg)


# ---------------------------------------------------------------------------------------------
# 블록 빌더
# ---------------------------------------------------------------------------------------------


class _State:
    def __init__(self, doc_version: str, source: ct.BlockSource) -> None:
        self.doc_version = doc_version
        self.source = source
        self.blocks: list[Block] = []
        self.links: list[Link] = []
        self.artifacts: list[DerivedArtifact] = []
        self._paths: set[str] = set()
        self._ordinals: dict[str | None, int] = {}
        self._index_by_id: dict[str, int] = {}
        self.heading_stack: list[tuple[int, str]] = []
        self.degraded = False
        self.last_figure_id: str | None = None

    def current_heading(self) -> str | None:
        return self.heading_stack[-1][1] if self.heading_stack else None

    def index_of(self, block_id_value: str) -> int | None:
        return self._index_by_id.get(block_id_value)

    def add_block(
        self,
        *,
        btype: ct.BlockType,
        text: str,
        path: str,
        parent: str | None,
        container: ct.BlockContainer = ct.BlockContainer.body,
        **extra: Any,
    ) -> str:
        if path in self._paths:
            msg = f"duplicate element_path: {path}"
            raise StageError(_CONVERSION_FAILED, stage="parse", plugin_id=PLUGIN_ID, detail=msg)
        self._paths.add(path)
        bid = make_block_id(self.doc_version, path)
        ordinal = self._ordinals.get(parent, 0)
        self._ordinals[parent] = ordinal + 1
        self._index_by_id[bid] = len(self.blocks)
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
                    element_path=path, char_start=0, char_end=len(text), page=None, bbox=None, section_index=None
                ),
                **extra,
            )
        )
        return bid


def _visit_heading(elem: HtmlElement, state: _State) -> None:
    level = int(elem.tag[1])
    text = _normalize_paragraph_text(_inline_text(elem))
    if not text:
        return
    path = _dom_path(elem)
    while state.heading_stack and state.heading_stack[-1][0] >= level:
        state.heading_stack.pop()
    parent = state.heading_stack[-1][1] if state.heading_stack else None
    bid = state.add_block(btype=ct.BlockType.heading, text=text, path=path, parent=parent, level=level)
    state.heading_stack.append((level, bid))


def _visit_paragraph(elem: HtmlElement, state: _State, *, parent: str | None) -> None:
    raw = _inline_text(elem)
    segments = _split_segments(raw)
    if not segments:
        return
    path = _dom_path(elem)
    multi = len(segments) > 1
    for i, segment in enumerate(segments):
        seg_path = f"{path}/seg[{i}]" if multi else path
        state.add_block(btype=ct.BlockType.paragraph, text=segment, path=seg_path, parent=parent)


def _li_own_text(li: HtmlElement, nested_ids: frozenset[int]) -> str:
    return _inline_text(li, skip_ids=nested_ids)


def _anchor_link(li: HtmlElement, text: str) -> tuple[int, int, str] | None:
    """Li 안의 첫 `a[href]`를 정규화된 `text` 안에서 찾아 구간을 만든다(단순 첨부 목록 전용, 07 §9.1)."""
    anchor = next((a for a in li.iter("a") if a.get("href")), None)
    if anchor is None:
        return None
    href = anchor.get("href")
    if not href or href.startswith(("javascript:", "#")):
        return None
    label = _normalize_paragraph_text(_inline_text(anchor))
    if not label:
        return None
    start = text.find(label)
    if start == -1:
        return None
    return start, start + len(label), href


def _visit_list(elem: HtmlElement, state: _State, *, parent: str | None, level: int, config: HtmlParserConfig) -> None:
    ordered = elem.tag == "ol"
    for li in (c for c in elem if isinstance(c.tag, str) and c.tag == "li"):
        nested_lists = [c for c in li if isinstance(c.tag, str) and c.tag in ("ul", "ol")]
        nested_ids = frozenset(id(n) for n in nested_lists)
        raw_text = _li_own_text(li, nested_ids)
        segments = _split_segments(raw_text)
        if not segments and not nested_lists:
            continue
        text = segments[0] if segments else ""
        text, label = _extract_numbering_label(text)
        path = _dom_path(li)
        bid = state.add_block(
            btype=ct.BlockType.list_item,
            text=text,
            path=path,
            parent=parent,
            level=level,
            ordered=ordered,
            numbering_label=label,
        )
        if config.include_links:
            link = _anchor_link(li, text)
            if link is not None:
                start, end, href = link
                state.links.append(Link(block_id=bid, char_start=start, char_end=end, href=href))
        for nested in nested_lists:
            _visit_list(nested, state, parent=bid, level=level + 1, config=config)


def _visit_pre(elem: HtmlElement, state: _State, *, parent: str | None) -> None:
    text = "".join(elem.itertext())
    if not text.strip():
        return
    path = _dom_path(elem)
    code_child = next((c for c in elem if isinstance(c.tag, str) and c.tag == "code"), None)
    target = code_child if code_child is not None else elem
    cls = target.get("class") or ""
    match = re.search(r"(?:language|lang)-([\w+-]+)", cls)
    language = match.group(1) if match else None
    state.add_block(btype=ct.BlockType.code, text=text, path=path, parent=parent, code=Code(language=language))


async def _visit_img(
    elem: HtmlElement, ctx: Any, state: _State, *, parent: str | None, config: HtmlParserConfig
) -> None:
    src = elem.get("src") or ""
    alt = (elem.get("alt") or "").strip()
    path = _dom_path(elem)
    if src.startswith("data:"):
        payload, media_type = _decode_data_uri(src)
        if payload is None or media_type is None:
            state.degraded = True
            return
        ext = _EXT_FOR_MIME.get(media_type, media_type.split("/")[-1] if "/" in media_type else "bin")
        ref = await ctx.artifacts.put_derived(payload, kind="figure_crop", ext=ext, media_type=media_type)
        ref = _to_artifact_ref(ref)
        bid = state.add_block(
            btype=ct.BlockType.figure,
            text="",
            path=path,
            parent=parent,
            figure=Figure(artifact=ref, kind=figure_kind_mod.Kind.image, alt_text=alt or None),
        )
        state.last_figure_id = bid
        state.artifacts.append(DerivedArtifact(kind=ArtifactKind.figure_crop, ref=ref, block_id=ct.Hex32(bid)))
        return
    if config.include_images and _meaningful_alt(alt):
        bid = state.add_block(btype=ct.BlockType.paragraph, text=alt, path=path, parent=parent)
        if config.include_links and src:
            state.links.append(Link(block_id=bid, char_start=0, char_end=len(alt), href=src))


def _visit_caption(elem: HtmlElement, state: _State, *, target: str | None) -> None:
    text = _normalize_paragraph_text(_inline_text(elem))
    if not text or target is None:
        return
    target_index = state.index_of(target)
    if target_index is None:
        return
    target_block = state.blocks[target_index]
    path = f"{target_block.provenance.element_path}/caption[0]"
    bid = state.add_block(btype=ct.BlockType.caption, text=text, path=path, parent=target, caption_of=target)
    target_block.caption_block_ids = [*(target_block.caption_block_ids or []), ct.Hex32(bid)]


async def _visit_table(elem: HtmlElement, ctx: Any, state: _State, *, parent: str | None) -> None:
    path = _dom_path(elem)
    raw_cells, n_rows, n_cols = _build_table_grid(elem, path)
    role = _table_role(raw_cells, n_rows, n_cols, presentation=elem.get("role") == "presentation")
    header_rows, header_inferred = _header_rows(elem, raw_cells, n_rows, role)
    preserved = _grid_ok(raw_cells, n_rows, n_cols)
    if not preserved:
        n_rows = max((c.row + c.row_span for c in raw_cells), default=n_rows)
        n_cols = max((c.col + c.col_span for c in raw_cells), default=n_cols)
        state.degraded = True
    cells, linear_text = _linearize_cells(raw_cells, header_rows)
    table_data = ct.TableData(
        n_rows=n_rows,
        n_cols=n_cols,
        cells=cells,
        header_row_indices=[ct.HeaderRowIndice(r) for r in header_rows],
        header_inferred=header_inferred,
        role=role,
        quality=ct.Quality1(
            merged_cells_preserved=preserved, structure_source=StructureSource.native, structure_confidence=None
        ),
    )
    bid = state.add_block(btype=ct.BlockType.table, text=linear_text, path=path, parent=parent, table=table_data)
    html_ref = await ctx.artifacts.put_derived(
        render_table_html(table_data).encode("utf-8"), kind="table_html", ext="html", media_type="text/html"
    )
    html_ref = _to_artifact_ref(html_ref)
    table_data.html_ref = html_ref
    state.artifacts.append(DerivedArtifact(kind=ArtifactKind.table_html, ref=html_ref, block_id=ct.Hex32(bid)))

    caption_elems = elem.xpath("./caption")
    if caption_elems:
        _visit_caption(caption_elems[0], state, target=bid)


async def _visit_blockquote(elem: HtmlElement, ctx: Any, state: _State, *, config: HtmlParserConfig) -> None:
    block_children = [c for c in elem if isinstance(c.tag, str) and c.tag in _BLOCK_DISPATCH_TAGS]
    if not block_children:
        _visit_paragraph(elem, state, parent=state.current_heading())
        return
    for child in elem:
        if isinstance(child.tag, str):
            await _visit(child, ctx, state, config=config)


def _to_artifact_ref(value: Any) -> ct.ArtifactRef:
    if isinstance(value, ct.ArtifactRef):
        return value
    if hasattr(value, "model_dump"):
        return ct.ArtifactRef.model_validate(value.model_dump(mode="json"))
    return ct.ArtifactRef.model_validate(value)


async def _visit(  # noqa: PLR0911 - 태그별 단순 분기 디스패처, 통합하면 오히려 가독성이 떨어진다
    elem: HtmlElement, ctx: Any, state: _State, *, config: HtmlParserConfig
) -> None:
    """DOM 어휘 → `BlockType` 디스패처(07 §6.2). 알 수 없는 태그는 투명 컨테이너로 재귀한다."""
    tag = elem.tag
    if not isinstance(tag, str):
        return
    if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
        _visit_heading(elem, state)
        return
    if tag == "p":
        _visit_paragraph(elem, state, parent=state.current_heading())
        return
    if tag == "div" and _is_inline_only(elem):
        _visit_paragraph(elem, state, parent=state.current_heading())
        return
    if tag in ("ul", "ol"):
        _visit_list(elem, state, parent=state.current_heading(), level=0, config=config)
        return
    if tag == "table":
        await _visit_table(elem, ctx, state, parent=state.current_heading())
        return
    if tag == "img":
        await _visit_img(elem, ctx, state, parent=state.current_heading(), config=config)
        return
    if tag == "pre":
        _visit_pre(elem, state, parent=state.current_heading())
        return
    if tag == "blockquote":
        await _visit_blockquote(elem, ctx, state, config=config)
        return
    if tag == "figcaption":
        _visit_caption(elem, state, target=state.last_figure_id)
        return
    for child in elem:
        await _visit(child, ctx, state, config=config)


# ---------------------------------------------------------------------------------------------
# 스테이지
# ---------------------------------------------------------------------------------------------


class HtmlTrafilaturaDoclingParser:
    """HTML 인프로세스 파서(A 등급, `in_process`). 사다리 없이 DOM 직접 경로 + Trafilatura 메타 보조."""

    plugin_id = PLUGIN_ID
    config_schema = HtmlParserConfig
    requires_lineage: tuple[str, ...] = ()

    def __init__(self, config: HtmlParserConfig | None = None) -> None:
        """설정을 고정한다(설정은 `config_hash` → `fingerprint` → `stage_key` 입력)."""
        self.config = config or HtmlParserConfig()

    def config_hash(self) -> str:
        """`H("config", canonical_json(config))`(바이블 §6.2 근사)."""
        canonical = json.dumps(
            self.config.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), ensure_ascii=False
        )
        return hash_of("config", canonical)

    def capabilities(self) -> ct.Capabilities:
        """`isolation_modes=[in_process]`, `input_formats=[html]`, 재개 미지원(07 §1)."""
        return ct.Capabilities(
            isolation_modes=[ct.IsolationMode.in_process],
            supports_resumable=False,
            contracts_compat=ct.ContractsCompat(">=1.0,<2.0"),
            input_formats=["html"],
            requires_gpu=False,
        )

    def fingerprint(self) -> str:
        """`H("producer", plugin_id, plugin_version, config_hash, "", "")`(인프로세스: 이미지·모델 없음)."""
        return hash_of("producer", self.plugin_id, PLUGIN_VERSION, self.config_hash(), "", "")

    @staticmethod
    def _parser_version() -> str:
        return f"trafilatura=={package_version('trafilatura')};lxml=={package_version('lxml')}"

    async def run(self, inp: SourceDocument, ctx: Any) -> ParsedDocument:
        """셸이 제공하는 원본 바이트 포트(`ctx.source_bytes()`, 동기·비동기 모두 허용)로 파싱한다."""
        port = getattr(ctx, "source_bytes", None)
        if port is None:
            raise StageError(
                _CONVERSION_FAILED,
                stage="parse",
                plugin_id=self.plugin_id,
                detail="StageContext has no source_bytes port",
            )
        data = port()
        if hasattr(data, "__await__"):
            data = await data
        return await self.parse_bytes(bytes(data), inp, ctx)

    async def parse_bytes(
        self, data: bytes, inp: SourceDocument, ctx: Any, *, block_source: ct.BlockSource = ct.BlockSource.text_layer
    ) -> ParsedDocument:
        """HTML 바이트 → `ParsedDocument`. 저장은 `ctx.artifacts.put_derived`로만 한다."""
        if self.config.use_docling_table_backend:
            docling_table_backend_placeholder("")

        http_charset = inp.http_metadata.charset if inp.http_metadata and inp.http_metadata.charset else None
        text, encoding_used = _decode_html(data, http_charset)

        try:
            parser = lxml.html.HTMLParser(
                recover=True, remove_comments=True, remove_pis=True, no_network=True, huge_tree=False
            )
            tree = lxml.html.fromstring(text, parser=parser)
        except Exception as exc:
            raise StageError(
                _CONVERSION_FAILED,
                stage="parse",
                plugin_id=self.plugin_id,
                detail=f"lxml parse error: {type(exc).__name__}",
            ) from exc

        base_url = str(inp.resolved_uri)
        language_hint = inp.metadata.language_hint.root if inp.metadata.language_hint else None
        metadata, language = _extract_metadata(tree, base_url=base_url, language_hint=language_hint, config=self.config)
        navigation_text = _collect_navigation_text(tree)
        _remove_non_content(tree, remove_hidden=self.config.remove_hidden)
        _absolutize_links(tree, base_url)

        traf_meta = _run_trafilatura_metadata(text, base_url, self.config)

        main_root = self._select_main_region(tree, base_url)

        doc_version = inp.doc_version.root
        state = _State(doc_version=doc_version, source=block_source)
        for child in main_root:
            if isinstance(child.tag, str):
                await _visit(child, ctx, state, config=self.config)

        if not state.blocks:
            raise StageError(
                _CONVERSION_FAILED,
                stage="parse",
                plugin_id=self.plugin_id,
                detail="empty_main_content",
                retryable=False,
            )

        if navigation_text:
            metadata = metadata.model_copy(update={"navigation_text": navigation_text})

        artifacts = list(state.artifacts)
        derived_source_html = lxml.html.tostring(main_root, encoding="unicode")
        derived_ref = await ctx.artifacts.put_derived(
            derived_source_html.encode("utf-8"), kind="derived_source", ext="html", media_type="text/html"
        )
        derived_ref = _to_artifact_ref(derived_ref)
        artifacts.append(DerivedArtifact(kind=ArtifactKind.derived_source, ref=derived_ref))

        report = {
            "plugin_id": self.plugin_id,
            "mode": self.config.mode,
            "source_encoding": encoding_used,
            "navigation_text_count": len(navigation_text),
            "trafilatura": traf_meta,
        }
        report_ref = await ctx.artifacts.put_derived(
            json.dumps(report, ensure_ascii=False, sort_keys=True).encode("utf-8"),
            kind="vendor_json",
            ext="json",
            media_type="application/json",
        )
        report_ref = _to_artifact_ref(report_ref)
        artifacts.append(DerivedArtifact(kind=ArtifactKind.vendor_json, ref=report_ref))

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
            quality=ct.Quality.degraded if state.degraded else ct.Quality.full,
            warnings=[],
            created_at=_rfc3339_ms(ctx.now()),
            lineage_refs=LineageRefs(source=inp.artifact),
            document_id=inp.document_id,
            doc_version=doc_version,
            source_ref=inp.artifact,
            parser_fingerprint=ParserFingerprint(
                parser_id=self.plugin_id,
                parser_version=self._parser_version(),
                sidecar_image_digest=None,
                profile_option=f"html_{self.config.mode}",
            ),
            parser_chain=[ct.PluginId(self.plugin_id)],
            source_kind=ct.SourceKind.flow,
            page_count=None,
            language=language,
            metadata=metadata,
            blocks=state.blocks,
            artifacts=artifacts,
            annotations=None,
            fields=None,
            links=state.links or None,
            text_length=sum(len(b.text) for b in state.blocks),
            block_count=len(state.blocks),
            source_encoding=encoding_used,
        )

    def _select_main_region(self, tree: HtmlElement, base_url: str) -> HtmlElement:
        for rule in self.config.site_rules:
            if not rule.hosts or _host_matches(base_url, rule.hosts):
                for xpath in rule.main_selectors:
                    matches = tree.xpath(xpath)
                    if matches:
                        return matches[0]
        for xpath in _DEFAULT_MAIN_XPATHS:
            matches = tree.xpath(xpath)
            if matches and _text_of(matches[0]):
                return matches[0]
        body = tree.xpath(".//body")
        return body[0] if body else tree


def _host_matches(url: str, patterns: tuple[str, ...]) -> bool:
    host = urlsplit(url).netloc
    for pattern in patterns:
        regex = "^" + re.escape(pattern).replace(r"\*", ".*") + "$"
        if re.match(regex, host):
            return True
    return False
