"""`parser.pdf_fast_pdftext` 파서 스테이지 — 디지털 PDF를 pypdfium2만으로 빠르게 `ParsedDocument`로 만든다.

`profile_option=pdf_fast_cpu`, 격리 `in_process`.

설계 근거: `04-pipelines/05-parser-pdf.md` §4(빠른 경로)·§7.2(heading 레벨 추론)·
§7.3(읽기 순서·2단 컬럼)·§7.7(provenance·좌표계)·§11(품질 게이트), 바이블 §5.4 `ParsedDocument`·
§4.1(5멤버 스테이지 프로토콜), ADR-0006. `WP-105-parse-pdf-fast-pypdfium2.md`가 범위·설계 결정을 기록한다.
구성: `PdfFastPdftextParser` — 스테이지 5멤버(`plugin_id`·`config_schema`·`capabilities()`·
`fingerprint()`·`run()`)와 테스트용 `parse_bytes(data, inp, ctx)`; 문자 bbox·폰트 크기 추출·줄/문단
병합·heading 클러스터링·2단 컬럼 읽기 순서·provenance 좌표 변환을 담당하는 순수 헬퍼 함수들
(`_char_records`·`_group_lines`·`_group_paragraphs`·`_cluster_font_sizes`·`_pattern_heading_level`·
`_detect_columns`·`_merge_reading_order`).
불변식: `pdftext`(PyPI) 패키지는 쓰지 않는다 — `pdftext>=0.7.1`이 요구하는 `pypdfium2==5.10.1`이 이
프로젝트의 `pypdfium2>=5.13.0` 고정과 충돌해 `uv add pdftext`가 해결 불가함을 확인했다(WP §패키지 결정).
대신 이미 고정된 `pypdfium2`의 raw ctypes API로 동등 기능을 구현한다. 표·그림·목록·머리말/꼬리말·
outline heading 보정·`garbled`/`pre_ocr` 페이지 분류는 이 WP 범위 밖(`paragraph`로만 남는다). OCR·
레이아웃 모델 경로는 만들지 않는다(`needs_model`) — 저밀도 페이지는 블록을 만들지 않고
`page_status=skipped` + 경고로만 표시한다.
검증 계층: 1층(여기서 검증) — `tests/adapters/parse/test_pdf_fast.py`(순수 pypdfium2 최소 PDF 픽스처,
Docker·모델·GPU·네트워크 불필요).
"""

from __future__ import annotations

import inspect
import json
import re
from dataclasses import dataclass
from datetime import UTC
from importlib.metadata import version as package_version
from itertools import pairwise
from typing import TYPE_CHECKING, Any

import pypdfium2 as pdfium
import pypdfium2.raw as pdfium_raw
from pydantic import BaseModel, ConfigDict, Field

from rag_platform.contracts import common_types as ct
from rag_platform.contracts.parsed_document import (
    Block,
    LineageRefs,
    PageStatusEntry,
    ParsedDocument,
    ParserFingerprint,
)
from rag_platform.sdk.hashing import block_id as make_block_id, hash_of
from rag_platform.sdk.stage import StageError

if TYPE_CHECKING:
    from collections.abc import Sequence
    from datetime import datetime

    from rag_platform.contracts.source_document import SourceDocument

__all__ = ["PdfFastParserConfig", "PdfFastPdftextParser"]

PLUGIN_ID = "parser.pdf_fast_pdftext"
PLUGIN_VERSION = "0.1.0"
PROFILE_OPTION = "pdf_fast_cpu"
SCHEMA_VERSION = "1.0.0"
_BCP47_DEFAULT = "ko"
_DOCUMENT_ENCRYPTED = "parse.document_encrypted"
_CORRUPT_CONTAINER = "parse.corrupt_container"
_CONVERSION_FAILED = "parse.conversion_failed"

# 04-pipelines/05 §7.2 규칙 4의 두 정본 패턴 계열(순서가 우선순위: 긴 소수점 패턴을 먼저 검사).
_PATTERN_RULES: tuple[tuple[re.Pattern[str], int], ...] = (
    (re.compile(r"^제\s*\d+\s*편"), 1),
    (re.compile(r"^제\s*\d+\s*장"), 2),
    (re.compile(r"^제\s*\d+\s*절"), 3),
    (re.compile(r"^제\s*\d+\s*조"), 4),
    (re.compile(r"^\d+\.\d+\.\d+(?!\d)"), 3),
    (re.compile(r"^\d+\.\d+(?!\d)"), 2),
    (re.compile(r"^\d+\.(?!\d)"), 1),
)
# 보조 마커(§7.2 규칙 4 "상위 패턴 + 1") — 직전 패턴 레벨 + 1로 근사(WP 의도적 축소 참조).
_SUBLEVEL_PATTERN = re.compile(r"^([가-힣]\.|\(\d+\)|[①-⑳])")
_HEADING_END_PUNCT = (".",)
_MIN_COLUMN_BODY_BLOCKS = 2  # §7.3 — 컬럼 판정에 필요한 최소 본문 블록 수
_SCANNED_RATIO_HIGH = 0.8  # §3.3 간이 규칙 — 이상이면 source_kind=scanned
_SCANNED_RATIO_LOW = 0.2  # §3.3 간이 규칙 — 이하면 source_kind=born_digital


class PdfFastParserConfig(BaseModel):
    """`parser.pdf_fast_pdftext` 설정 — §10 `ingest.parse.options.pdf` 제안 키의 구현 부분집합."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    min_page_chars: int = Field(20, ge=0, description="§3.1 chars 임계값(미만이면 empty 또는 저밀도)")
    min_image_area_ratio: float = Field(0.05, ge=0.0, le=1.0, description="§3.1 image_area_ratio 임계값")
    heading_size_ratio: float = Field(1.15, gt=1.0, description="§7.2 규칙 3 — 본문 대비 heading 후보 배율")
    heading_max_len: int = Field(120, ge=1, description="§7.2 규칙 3 — heading 후보 최대 길이")
    max_heading_clusters: int = Field(4, ge=1, le=6, description="§7.2 규칙 3 — 폰트 크기 클러스터 상한 k")
    heading_page_ratio_gate: float = Field(0.4, gt=0.0, le=1.0, description="§7.2 규칙 6 / §11")
    heading_doc_ratio_gate: float = Field(0.25, gt=0.0, le=1.0, description="§7.2 규칙 6 / §11")
    column_min_gap_ratio: float = Field(0.05, gt=0.0, le=1.0, description="§7.3 2단 판정 최소 간격 비율")
    column_min_coverage: float = Field(0.3, gt=0.0, le=1.0, description="§7.3 2단 판정 최소 커버리지")
    cross_column_width_ratio: float = Field(0.6, gt=0.0, le=1.0, description="§7.3 컬럼 가로지름 폭 비율")


def _rfc3339_ms(moment: datetime) -> str:
    utc = moment.astimezone(UTC)
    return utc.strftime("%Y-%m-%dT%H:%M:%S.") + f"{utc.microsecond // 1000:03d}Z"


# ---------------------------------------------------------------------------------------------
# 순수 헬퍼 — 폰트 크기 클러스터링·번호 패턴·컬럼 감지(PDF 불필요, 직접 단위 테스트 대상)
# ---------------------------------------------------------------------------------------------


def _cluster_font_sizes(sizes: list[float], *, max_clusters: int = 4, tolerance: float = 0.5) -> dict[float, int]:
    """내림차순 폰트 크기를 인접 허용오차로 묶어 `level 1..max_clusters`를 배정한다(§7.2 규칙 3)."""
    uniq = sorted({round(s, 1) for s in sizes}, reverse=True)
    if not uniq:
        return {}
    clusters: list[list[float]] = [[uniq[0]]]
    for s in uniq[1:]:
        if abs(clusters[-1][-1] - s) <= tolerance:
            clusters[-1].append(s)
        else:
            clusters.append([s])
    if len(clusters) > max_clusters:
        tail = [v for c in clusters[max_clusters - 1 :] for v in c]
        clusters = [*clusters[: max_clusters - 1], tail]
    return {v: level for level, cluster in enumerate(clusters, start=1) for v in cluster}


def _pattern_heading_level(text: str, last_level: list[int]) -> tuple[int, str] | None:
    """§7.2 규칙 4 — 번호 패턴이 있으면 `(level, numbering_label)`, 없으면 `None`.

    `last_level`은 길이 1의 가변 리스트(직전에 매칭된 패턴 레벨을 문서 전체에 걸쳐 추적하는 상태 —
    `가./(N)/①` 같은 보조 마커의 "상위 패턴 + 1" 근사에 쓰인다).
    """
    stripped = text.strip()
    for pattern, level in _PATTERN_RULES:
        m = pattern.match(stripped)
        if m:
            last_level[0] = level
            return level, m.group(0).strip()
    m = _SUBLEVEL_PATTERN.match(stripped)
    if m:
        level = min(last_level[0] + 1, 6)
        last_level[0] = level
        return level, m.group(0)
    return None


@dataclass
class _ColBlock:
    """`_detect_columns`/`_merge_reading_order`가 다루는 최소 형태(실제 `_RawBlock`도 만족)."""

    left: float
    right: float
    top: float
    bottom: float


def _largest_gap(xs: list[float]) -> tuple[float, float]:
    left, right, size = xs[0], xs[0], 0.0
    for a, b in pairwise(xs):
        gap = b - a
        if gap > size:
            size, left, right = gap, a, b
    return left, right


def _detect_columns(
    blocks: Sequence[_ColBlock],
    page_width: float,
    *,
    min_gap_ratio: float = 0.05,
    min_coverage: float = 0.3,
    cross_width_ratio: float = 0.6,
) -> list[tuple[float, float]]:
    """04-pipelines/05 §7.3 의사코드 그대로 — 2단이면 `[(0,mid),(mid,W)]`, 아니면 단일 컬럼."""
    body = [b for b in blocks if (b.right - b.left) < page_width * cross_width_ratio]
    if len(body) < _MIN_COLUMN_BODY_BLOCKS or page_width <= 0:
        return [(0.0, page_width)]
    xs = sorted((b.left + b.right) / 2 for b in body)
    left, right = _largest_gap(xs)
    gap_size = right - left
    if gap_size <= 0:
        return [(0.0, page_width)]
    coverage_left = sum(1 for x in xs if x <= left) / len(xs)
    coverage_right = sum(1 for x in xs if x >= right) / len(xs)
    if gap_size > page_width * min_gap_ratio and coverage_left > min_coverage and coverage_right > min_coverage:
        mid = (left + right) / 2
        return [(0.0, mid), (mid, page_width)]
    return [(0.0, page_width)]


def _merge_reading_order(columns: list[list[Any]], cross_blocks: list[Any]) -> list[Any]:
    """왼→오 컬럼 순서에 가로지르는 블록을 y(top) 위치 그대로 끼워 넣는다(§7.3)."""
    if not cross_blocks:
        return [b for col in columns for b in col]
    cross_sorted = sorted(cross_blocks, key=lambda b: -b.top)
    result: list[Any] = []
    col_idx = [0] * len(columns)
    for cb in cross_sorted:
        for ci, col in enumerate(columns):
            while col_idx[ci] < len(col) and col[col_idx[ci]].top > cb.top:
                result.append(col[col_idx[ci]])
                col_idx[ci] += 1
        result.append(cb)
    for ci, col in enumerate(columns):
        result.extend(col[col_idx[ci] :])
    return result


# ---------------------------------------------------------------------------------------------
# pypdfium2 문자 추출 — 줄(line) → 문단 후보 블록(`_RawBlock`)
# ---------------------------------------------------------------------------------------------


@dataclass
class _Line:
    text: str
    left: float
    bottom: float
    right: float
    top: float
    font_size: float
    n_chars: int


@dataclass
class _RawBlock(_ColBlock):
    page: int  # 0-based
    text: str = ""
    font_size: float = 0.0
    n_chars: int = 0
    type: ct.BlockType = ct.BlockType.paragraph
    level: int | None = None
    numbering_label: str | None = None
    heading_inferred: bool | None = None
    font_promoted: bool = False


def _char_records(textpage: pdfium.PdfTextPage) -> list[tuple[str, float, float, float, float, float]]:
    """`(text, left, bottom, right, top, font_size)` per 문자 인덱스(개별 실패는 방어적으로 0 처리)."""
    n = textpage.count_chars()
    if n <= 0:
        return []
    full_text = textpage.get_text_range()
    records: list[tuple[str, float, float, float, float, float]] = []
    last_size = 0.0
    for i in range(min(n, len(full_text))):
        ch = full_text[i]
        try:
            left, bottom, right, top = textpage.get_charbox(i)
        except pdfium.PdfiumError:
            left = bottom = right = top = 0.0
        try:
            size = float(pdfium_raw.FPDFText_GetFontSize(textpage, i))
        except Exception:  # noqa: BLE001 - ctypes 실패는 직전 크기로 방어적 대체
            size = last_size
        last_size = size or last_size
        records.append((ch, left, bottom, right, top, size))
    return records


def _group_lines(records: list[tuple[str, float, float, float, float, float]]) -> list[_Line]:
    lines: list[_Line] = []
    buf: list[tuple[str, float, float, float, float, float]] = []

    def flush() -> None:
        if not buf:
            return
        text = "".join(r[0] for r in buf).strip()
        boxed = [r for r in buf if r[0].strip()]
        if text and boxed:
            sizes = sorted(r[5] for r in boxed if r[5] > 0) or [0.0]
            lines.append(
                _Line(
                    text=text,
                    left=min(r[1] for r in boxed),
                    bottom=min(r[2] for r in boxed),
                    right=max(r[3] for r in boxed),
                    top=max(r[4] for r in boxed),
                    font_size=sizes[len(sizes) // 2],
                    n_chars=len(text),
                )
            )
        buf.clear()

    for rec in records:
        if rec[0] in "\r\n":
            flush()
            continue
        buf.append(rec)
    flush()
    return lines


def _group_paragraphs(lines: list[_Line], page: int) -> list[_RawBlock]:
    """인접 줄을 폰트 크기 동일성 + 수직 간격(줄높이 이하) + 좌측 정렬(같은 컬럼)로 문단 후보로 병합한다.

    좌측 정렬 조건이 없으면 2단 컬럼 문서에서 왼쪽 컬럼 마지막 줄과 오른쪽 컬럼 첫 줄이 수직으로
    가까울 때 하나의 문단으로 잘못 합쳐진다(컬럼을 가로질러 텍스트가 섞임) — §7.3 컬럼 감지 이전 단계의
    불변식.
    """
    blocks: list[_RawBlock] = []
    current: list[_Line] = []

    def flush() -> None:
        if not current:
            return
        sizes = sorted(ln.font_size for ln in current)
        blocks.append(
            _RawBlock(
                page=page,
                text="\n".join(ln.text for ln in current),
                left=min(ln.left for ln in current),
                bottom=min(ln.bottom for ln in current),
                right=max(ln.right for ln in current),
                top=max(ln.top for ln in current),
                font_size=sizes[len(sizes) // 2],
                n_chars=sum(ln.n_chars for ln in current),
            )
        )
        current.clear()

    prev: _Line | None = None
    for line in lines:
        same_para = False
        if prev is not None:
            line_height = max(prev.font_size, line.font_size, 1.0)
            same_size = abs(line.font_size - prev.font_size) <= max(0.5, 0.05 * line_height)
            same_left = abs(line.left - prev.left) <= max(2.0 * line_height, 12.0)
            gap = prev.bottom - line.top
            same_para = same_size and same_left and gap <= line_height
        if not same_para:
            flush()
        current.append(line)
        prev = line
    flush()
    return blocks


def _image_area_ratio(page: pdfium.PdfPage, page_area: float) -> float:
    if page_area <= 0:
        return 0.0
    total = 0.0
    for obj in page.get_objects(filter=[pdfium_raw.FPDF_PAGEOBJ_IMAGE]):
        left, bottom, right, top = obj.get_bounds()
        total += max(0.0, right - left) * max(0.0, top - bottom)
    return total / page_area


def _weighted_median_font_size(blocks: list[_RawBlock]) -> float:
    """§7.2 규칙 3 — "전체 스팬의 글자 수 가중 중앙값"(본문 크기 기준선)."""
    weighted = sorted((b.font_size, b.n_chars) for b in blocks if b.n_chars > 0)
    total_chars = sum(w for _, w in weighted)
    if total_chars <= 0:
        return 0.0
    acc = 0
    half = total_chars / 2
    body_size = 0.0
    for size, weight in weighted:
        acc += weight
        body_size = size
        if acc >= half:
            break
    return body_size


def _is_heading_candidate(b: _RawBlock, body_size: float, cfg: PdfFastParserConfig) -> bool:
    """§7.2 규칙 3 — 크기가 본문 크기 x 비율 이상, 길이 상한, 종결 부호로 끝나지 않음(굵기는 클러스터링이 흡수)."""
    return (
        b.font_size >= body_size * cfg.heading_size_ratio
        and len(b.text) <= cfg.heading_max_len
        and not b.text.rstrip().endswith(_HEADING_END_PUNCT)
    )


def _infer_headings(blocks: list[_RawBlock], cfg: PdfFastParserConfig) -> None:
    """§7.2 규칙 3·4·6 — 폰트 클러스터링 + 번호 패턴, heading 과다 게이트로 폰트 전용 승격 되돌림."""
    if not blocks:
        return
    body_size = _weighted_median_font_size(blocks)
    candidate_sizes = [b.font_size for b in blocks if _is_heading_candidate(b, body_size, cfg)]
    size_levels = _cluster_font_sizes(candidate_sizes, max_clusters=cfg.max_heading_clusters)

    last_pattern_level = [0]
    for b in blocks:
        font_candidate = _is_heading_candidate(b, body_size, cfg)
        pattern = _pattern_heading_level(b.text, last_pattern_level)
        if pattern is not None:
            level, label = pattern
            b.type = ct.BlockType.heading
            b.level = level
            b.numbering_label = label
            b.heading_inferred = True
            b.font_promoted = False
        elif font_candidate:
            size_level = size_levels.get(round(b.font_size, 1))
            if size_level is not None:
                b.type = ct.BlockType.heading
                b.level = size_level
                b.heading_inferred = True
                b.font_promoted = True

    # §7.2 규칙 6 / §11 — heading 비율 게이트: 폰트 전용 승격만 되돌린다(패턴 매칭은 유지).
    doc_headings = sum(1 for b in blocks if b.type == ct.BlockType.heading)
    if blocks and doc_headings / len(blocks) > cfg.heading_doc_ratio_gate:
        _revert_font_promotions(blocks)
        return
    for page in {b.page for b in blocks}:
        page_blocks = [b for b in blocks if b.page == page]
        page_headings = sum(1 for b in page_blocks if b.type == ct.BlockType.heading)
        if page_blocks and page_headings / len(page_blocks) > cfg.heading_page_ratio_gate:
            _revert_font_promotions(page_blocks)

    # §7.2 규칙 5 — 정합: 부모 없는 level>1 heading은 직전 heading level+1로 당긴다.
    last_level = 0
    for b in blocks:
        if b.type != ct.BlockType.heading or b.level is None:
            continue
        b.level = min(b.level, last_level + 1, 6)
        last_level = b.level


def _revert_font_promotions(blocks: list[_RawBlock]) -> None:
    for b in blocks:
        if b.font_promoted:
            b.type = ct.BlockType.paragraph
            b.level = None
            b.heading_inferred = None
            b.font_promoted = False


@dataclass
class _PageScan:
    """`_scan_pages`의 결과 — 문단 후보 블록과 페이지별 분류(§3.1·§3.2 간이 규칙)."""

    raw_blocks: list[_RawBlock]
    page_widths: dict[int, float]
    page_heights: dict[int, float]
    digital_pages: set[int]
    empty_pages: set[int]
    skipped_pages: set[int]


def _scan_pages(pdf: pdfium.PdfDocument, cfg: PdfFastParserConfig) -> _PageScan:
    """페이지를 순회해 문자를 추출하고 밀도로 분류한다(저밀도는 §3.2 `empty`/저밀도 두 갈래)."""
    scan = _PageScan([], {}, {}, set(), set(), set())
    for p in range(len(pdf)):
        page = pdf[p]
        try:
            width, height = page.get_size()
            scan.page_widths[p] = width
            scan.page_heights[p] = height
            textpage = page.get_textpage()
            try:
                records = _char_records(textpage)
            finally:
                textpage.close()
            lines = _group_lines(records)
            chars = sum(ln.n_chars for ln in lines)
            if chars < cfg.min_page_chars:
                image_ratio = _image_area_ratio(page, width * height)
                if image_ratio <= cfg.min_image_area_ratio:
                    scan.empty_pages.add(p)
                else:
                    scan.skipped_pages.add(p)
                continue
            scan.digital_pages.add(p)
            scan.raw_blocks.extend(_group_paragraphs(lines, p))
        finally:
            page.close()
    return scan


def _reorder_page_blocks(blocks: list[_RawBlock], page_width: float, cfg: PdfFastParserConfig) -> list[_RawBlock]:
    columns = _detect_columns(
        blocks,
        page_width,
        min_gap_ratio=cfg.column_min_gap_ratio,
        min_coverage=cfg.column_min_coverage,
        cross_width_ratio=cfg.cross_column_width_ratio,
    )
    if len(columns) == 1:
        return sorted(blocks, key=lambda b: (-b.top, b.left))
    threshold = page_width * cfg.cross_column_width_ratio
    cross: list[_RawBlock] = []
    non_cross: list[_RawBlock] = []
    for b in blocks:
        (cross if (b.right - b.left) >= threshold else non_cross).append(b)
    last_idx = len(columns) - 1
    col_blocks: list[list[_RawBlock]] = []
    for i, (lo, hi) in enumerate(columns):
        if i == last_idx:
            col = [b for b in non_cross if lo <= (b.left + b.right) / 2 <= hi]
        else:
            col = [b for b in non_cross if lo <= (b.left + b.right) / 2 < hi]
        col_blocks.append(sorted(col, key=lambda b: -b.top))
    return _merge_reading_order(col_blocks, cross)


# ---------------------------------------------------------------------------------------------
# 스테이지
# ---------------------------------------------------------------------------------------------


class PdfFastPdftextParser:
    """PDF 디지털 빠른 경로 파서(A 등급, `in_process`). OCR·레이아웃 모델 경로는 만들지 않는다."""

    plugin_id = PLUGIN_ID
    config_schema = PdfFastParserConfig
    requires_lineage: tuple[str, ...] = ()

    def __init__(self, config: PdfFastParserConfig | None = None) -> None:
        """설정을 고정한다(설정은 `config_hash` → `fingerprint` → `stage_key` 입력)."""
        self.config = config or PdfFastParserConfig()

    def config_hash(self) -> str:
        """`H("config", canonical_json(config))`(바이블 §6.2 근사)."""
        canonical = json.dumps(
            self.config.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), ensure_ascii=False
        )
        return hash_of("config", canonical)

    def capabilities(self) -> ct.Capabilities:
        """`isolation_modes=[in_process]`, `input_formats=[pdf]`, 재개 미지원(shard/`ResumeCursor` 미구현)."""
        return ct.Capabilities(
            isolation_modes=[ct.IsolationMode.in_process],
            supports_resumable=False,
            contracts_compat=ct.ContractsCompat(">=1.0,<2.0"),
            input_formats=["pdf"],
            requires_gpu=False,
        )

    def fingerprint(self) -> str:
        """`H("producer", plugin_id, plugin_version, config_hash, "", "")`(인프로세스: image digest·모델 없음)."""
        return hash_of("producer", self.plugin_id, PLUGIN_VERSION, self.config_hash(), "", "")

    async def run(self, inp: SourceDocument, ctx: Any) -> ParsedDocument:
        """셸이 제공하는 원본 바이트 포트(`ctx.source_bytes()`, 동기·비동기 모두 허용)로 파싱한다."""
        port = getattr(ctx, "source_bytes", None)
        if port is None:
            raise StageError(
                _CONVERSION_FAILED,
                stage="parse",
                plugin_id=self.plugin_id,
                detail="StageContext has no source_bytes port (04-pipelines/04 open issue 18)",
            )
        data = port()
        if inspect.isawaitable(data):
            data = await data
        return await self.parse_bytes(bytes(data), inp, ctx)

    async def parse_bytes(self, data: bytes, inp: SourceDocument, ctx: Any) -> ParsedDocument:
        """PDF 바이트 → `ParsedDocument`. `ctx.artifacts`는 이 WP에서 쓰지 않는다(표·그림 범위 밖)."""
        if inp.container_flags.encrypted and inp.credentials_ref is None:
            raise StageError(
                _DOCUMENT_ENCRYPTED,
                stage="parse",
                plugin_id=self.plugin_id,
                detail="container_flags.encrypted=true and no credentials_ref (04-pipelines/05 §8.1)",
            )
        try:
            pdf = pdfium.PdfDocument(data)
        except pdfium.PdfiumError as exc:
            raise StageError(
                _CORRUPT_CONTAINER,
                stage="parse",
                plugin_id=self.plugin_id,
                detail=f"pypdfium2 failed to open document: {exc}",
            ) from exc

        try:
            return self._build(pdf, inp, ctx)
        finally:
            pdf.close()

    def _build(self, pdf: pdfium.PdfDocument, inp: SourceDocument, ctx: Any) -> ParsedDocument:
        cfg = self.config
        n_pages = len(pdf)
        scan = _scan_pages(pdf, cfg)
        _infer_headings(scan.raw_blocks, cfg)

        ordered: list[_RawBlock] = []
        for p in range(n_pages):
            page_blocks = [b for b in scan.raw_blocks if b.page == p]
            ordered.extend(_reorder_page_blocks(page_blocks, scan.page_widths.get(p, 0.0), cfg))

        blocks, warnings, page_status = self._assemble_blocks(
            ordered,
            doc_version=inp.doc_version.root,
            n_pages=n_pages,
            page_heights=scan.page_heights,
            empty_pages=scan.empty_pages,
            skipped_pages=scan.skipped_pages,
        )
        return self._assemble_envelope(
            inp, ctx, page_count=n_pages, scan=scan, blocks=blocks, warnings=warnings, page_status=page_status
        )

    def _assemble_envelope(
        self,
        inp: SourceDocument,
        ctx: Any,
        *,
        page_count: int,
        scan: _PageScan,
        blocks: list[Block],
        warnings: list[ct.Warning],
        page_status: list[PageStatusEntry],
    ) -> ParsedDocument:
        total_non_empty = len(scan.digital_pages) + len(scan.skipped_pages)
        scanned_ratio = (len(scan.skipped_pages) / total_non_empty) if total_non_empty else 0.0
        if total_non_empty == 0:
            source_kind = ct.SourceKind.born_digital
        elif scanned_ratio >= _SCANNED_RATIO_HIGH:
            source_kind = ct.SourceKind.scanned
        elif scanned_ratio <= _SCANNED_RATIO_LOW:
            source_kind = ct.SourceKind.born_digital
        else:
            source_kind = ct.SourceKind.mixed

        quality = ct.Quality.degraded if scan.skipped_pages else ct.Quality.full
        language = _BCP47_DEFAULT
        if inp.metadata.language_hint is not None:
            language = inp.metadata.language_hint.root

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
            quality=quality,
            warnings=warnings,
            created_at=_rfc3339_ms(ctx.now()),
            lineage_refs=LineageRefs(source=inp.artifact),
            document_id=inp.document_id,
            doc_version=inp.doc_version,
            source_ref=inp.artifact,
            parser_fingerprint=ParserFingerprint(
                parser_id=self.plugin_id,
                parser_version=f"pypdfium2=={package_version('pypdfium2')}",
                sidecar_image_digest=None,
                profile_option=PROFILE_OPTION,
            ),
            parser_chain=[ct.PluginId(self.plugin_id)],
            source_kind=source_kind,
            page_count=page_count,
            page_status=page_status or None,
            language=language,
            metadata=None,
            blocks=blocks,
            artifacts=None,
            annotations=None,
            fields=None,
            links=None,
            text_length=sum(len(b.text) for b in blocks),
            block_count=len(blocks),
        )

    def _assemble_blocks(
        self,
        ordered: list[_RawBlock],
        *,
        doc_version: str,
        n_pages: int,
        page_heights: dict[int, float],
        empty_pages: set[int],
        skipped_pages: set[int],
    ) -> tuple[list[Block], list[ct.Warning], list[PageStatusEntry]]:
        blocks: list[Block] = []
        warnings: list[ct.Warning] = []
        page_status: list[PageStatusEntry] = []
        heading_stack: list[tuple[int, str]] = []  # (level, block_id) 최상단이 현재 부모
        ordinal_by_parent: dict[str | None, int] = {}

        def next_ordinal(parent: str | None) -> int:
            n = ordinal_by_parent.get(parent, 0)
            ordinal_by_parent[parent] = n + 1
            return n

        blocks_by_page: dict[int, list[_RawBlock]] = {}
        for b in ordered:
            blocks_by_page.setdefault(b.page, []).append(b)

        for p in range(n_pages):
            if p >= 1:
                self._append_page_break(blocks, doc_version, p, next_ordinal)
            if p in skipped_pages:
                page_status.append(PageStatusEntry(page=p + 1, status=ct.PageStatus.skipped, ocr_confidence=None))
                warnings.append(
                    ct.Warning(
                        code=ct.ErrorCodeCatalog.parse_page_skipped,
                        message="text density low; OCR path not implemented in fast path (needs_model)",
                        page=p + 1,
                    )
                )
            if p in empty_pages or p in skipped_pages:
                continue
            height = page_heights.get(p, 0.0)
            for b_idx, raw in enumerate(blocks_by_page.get(p, [])):
                path = f"/page[{p}]/block[{b_idx}]"
                bid = make_block_id(doc_version, path)
                if raw.type == ct.BlockType.heading and raw.level is not None:
                    while heading_stack and heading_stack[-1][0] >= raw.level:
                        heading_stack.pop()
                    parent = heading_stack[-1][1] if heading_stack else None
                    heading_stack.append((raw.level, bid))
                else:
                    parent = heading_stack[-1][1] if heading_stack else None
                bbox = [
                    round(raw.left, 2),
                    round(height - raw.top, 2),
                    round(raw.right, 2),
                    round(height - raw.bottom, 2),
                ]
                blocks.append(
                    Block(
                        block_id=bid,
                        type=raw.type,
                        parent_block_id=ct.Hex32(parent) if parent is not None else None,
                        ordinal=next_ordinal(parent),
                        text=raw.text,
                        level=raw.level,
                        numbering_label=raw.numbering_label,
                        heading_inferred=raw.heading_inferred,
                        furniture=False,
                        container=ct.BlockContainer.body,
                        source=ct.BlockSource.text_layer,
                        confidence=None,
                        provenance=ct.Provenance(
                            element_path=path,
                            char_start=0,
                            char_end=len(raw.text),
                            page=p + 1,
                            bbox=bbox,
                            section_index=None,
                        ),
                    )
                )
        return blocks, warnings, page_status

    def _append_page_break(self, blocks: list[Block], doc_version: str, p: int, next_ordinal: Any) -> None:
        path = f"/page[{p}]/break"
        bid = make_block_id(doc_version, path)
        blocks.append(
            Block(
                block_id=bid,
                type=ct.BlockType.page_break,
                parent_block_id=None,
                ordinal=next_ordinal(None),
                text="",
                furniture=False,
                container=ct.BlockContainer.body,
                source=ct.BlockSource.text_layer,
                confidence=None,
                provenance=ct.Provenance(
                    element_path=path, char_start=0, char_end=0, page=p + 1, bbox=None, section_index=None
                ),
            )
        )
