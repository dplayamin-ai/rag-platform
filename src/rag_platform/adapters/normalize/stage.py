"""`normalizer.chain` 스테이지 — `ParsedDocument`를 축소 범위 `NormalizedDocument`로 만든다(F1-06).

역할: 04-pipelines/09 §2 체인 정본 순서 중 이 WP가 다루는 부분(N1 `unicode`, N2 `linebreaks`, N6
`language`, N7 `furniture`, N8 `dedup`, N9 `heading`)을 블록별로 실행하고 `NormalizedDocument`를 조립한다.
문자 편집은 `korean/unicode.py`·`korean/layout.py`에 위임하고, 이 파일은 블록 순회·판정(furniture·dedup·
heading·language)·문서 조립만 맡는다. PII(N3)·리스크(N5)·장르 휴리스틱 본체(N10)·렉시컬 한자/띄어쓰기
본체(N11)·파생 메타(N12)·문장 분리(N13)·표 셀 뷰(N14)·상세 리포트(N15)는 WP-106 범위 밖(DEFERRED,
`docs/13-implementation/wp/WP-106-normalize-korean.md` 참조) — `pii_report.policy_applied="keep"`으로
고정하고 문장은 블록 전체를 단일 span으로 두는 자리표시자를 쓴다.
설계 근거: 바이블 §4.1(5멤버 스테이지 프로토콜)·§4.2 `normalize` 행·§5.4 `NormalizedDocument`·
`NormalizedBlock`; 04-pipelines/09 §2(체인 순서)·§3.1/§3.2/§3.6~§3.9(N1·N2·N6~N9)·§4(오프셋 규칙);
계약 `contracts/normalized_document`·`contracts/parsed_document`.
구성: `NormalizerChainConfig` — `config_schema`; `NormalizerChainStage` — 5멤버(`plugin_id`/
`config_schema`/`capabilities()`/`fingerprint()`/`run()`).
불변식·주의: 블록 물리 제거·병합·생성 없음(furniture·dedup은 `boilerplate=true`로만 표시). `adapters`는
`storage`/`security`를 import하지 않는다. `StageError` 코드는 §5.7 철자만
(`contract.violation`/`normalize.nfd_residual`).
검증 계층: 1층(여기서 검증) — `tests/adapters/normalize/test_normalize.py`. `needs_docker`/`needs_model`/
`needs_gpu`/`needs_network` 해당 없음(순수 함수, 외부 자원 없음).
"""

from __future__ import annotations

import json
import unicodedata
from dataclasses import dataclass
from datetime import UTC
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict

from rag_platform.adapters.normalize.korean.layout import merge_linebreaks
from rag_platform.contracts import common_types as ct
from rag_platform.contracts.normalized_document import (
    Annotations,
    BoilerplateRemovedItem,
    HeadingNode,
    LineageRefs,
    NormalizationReport,
    NormalizationStats,
    NormalizedDocument,
    ParsedRef,
    PiiReport,
)
from rag_platform.contracts.normalized_document.NormalizedDocument import GenreSource
from rag_platform.korean.unicode import apply_edits, clean_unicode, fold_lexical
from rag_platform.sdk.hashing import blake3_hex, hash_of
from rag_platform.sdk.stage import StageError

if TYPE_CHECKING:
    from datetime import datetime

    from rag_platform.contracts.parsed_document import Block, DocumentMetadata, ParsedDocument

__all__ = ["NormalizerChainConfig", "NormalizerChainStage"]

PLUGIN_VERSION = "0.1.0"
#: 실 형태소 분석기가 배선되지 않았을 때 쓰는 자리표시자(`common_types.AnalyzerId` 철자 규칙 준수).
_DEFAULT_ANALYZER_ID = "regex:1.0.0:none"
#: 04-pipelines/09 §2 N2 대상 타입(표·그림·수식·코드·페이지 나눔 제외).
_LINEBREAK_TYPES = frozenset(
    {ct.BlockType.paragraph, ct.BlockType.list_item, ct.BlockType.heading, ct.BlockType.caption, ct.BlockType.footnote}
)
#: 빈 `text`가 정상인 타입(표·그림·수식·코드·페이지 나눔) — N8 빈 블록 판정에서 제외한다.
_EMPTY_OK_TYPES = frozenset(
    {ct.BlockType.table, ct.BlockType.figure, ct.BlockType.formula, ct.BlockType.code, ct.BlockType.page_break}
)
_MAX_HEADING_PATH = 7
_MAX_BOILERPLATE_ITEMS = 1000
_MAX_BOILERPLATE_CHARS = 512
_HANGUL_SYLLABLE_LO, _HANGUL_SYLLABLE_HI = 0xAC00, 0xD7A3
_JAMO_LO, _JAMO_HI = 0x1100, 0x11FF
_COMPAT_JAMO_LO, _COMPAT_JAMO_HI = 0x3130, 0x318F


class NormalizerChainConfig(BaseModel):
    """`normalizer.chain`의 설정 스키마 — `Producer.config_hash`·`fingerprint()` 입력(바이블 §6.2).

    `linebreaks_enabled`은 계약 04 I-8 개정 전제(04-pipelines/09 §3.2, 미해결 이슈 1)라 기본 꺼짐이고,
    `spacing_correction_enabled`(Kiwi opt-in)도 기본 꺼짐이다(작업 지시 사양 요지). `analyzer_id`/
    `dictionary_hash`를 비우면 `ctx.analyzer`(있으면) 또는 자리표시자를 쓴다.
    """

    model_config = ConfigDict(extra="forbid")

    linebreaks_enabled: bool = False
    furniture_enabled: bool = True
    dedup_enabled: bool = True
    heading_reinfer_enabled: bool = True
    spacing_correction_enabled: bool = False
    analyzer_id: str | None = None
    dictionary_hash: str | None = None


@dataclass
class _BlockEdit:
    """N1·N2 편집이 끝난 블록 하나 — `_judge_blocks`가 furniture·dedup·heading·language를 판정한다."""

    block: Block
    display_text: str
    lexical_text: str
    offset_map: list[list[int]]


def _rfc3339_ms(moment: datetime) -> str:
    utc = moment.astimezone(UTC)
    return utc.strftime("%Y-%m-%dT%H:%M:%S.") + f"{utc.microsecond // 1000:03d}Z"


def _resolve_parsed_ref(ctx: Any, plugin_id: str) -> ParsedRef:
    """`ctx.parsed_ref`(이 스테이지 입력 `ParsedDocument`의 산출물 참조)를 읽는다.

    `StageContext`(sdk/context.py)에는 아직 이 멤버가 없다 — hwpx 파서의 `ctx.source_bytes` 관례를 따라
    포트 부재를 `contract.violation`으로 올린다(WP-106 open issue, 공용 파일 변경 없이 방어적으로 처리).
    """
    ref = getattr(ctx, "parsed_ref", None)
    if ref is None:
        code = "contract.violation"
        detail = (
            "StageContext has no parsed_ref port (WP-106 design gap: no ctx convention yet for a "
            "stage's own input ArtifactRef; cf. parse's ctx.source_bytes precedent)"
        )
        raise StageError(code, stage="normalize", plugin_id=plugin_id, detail=detail)
    if isinstance(ref, ParsedRef):
        return ref
    if hasattr(ref, "model_dump"):
        return ParsedRef.model_validate(ref.model_dump(mode="json"))
    return ParsedRef.model_validate(ref)


def _should_merge_linebreaks(block: Block, source_kind: ct.SourceKind) -> bool:
    """04-pipelines/09 §2 N2 행의 대상 블록 판정."""
    if block.type not in _LINEBREAK_TYPES:
        return False
    if source_kind != ct.SourceKind.flow:
        return True
    return block.source == ct.BlockSource.converted


def _detect_lang(display_text: str, *, default: str) -> str:
    """N6 간단 휴리스틱 — 한글(음절·조합형·호환 자모) 대 라틴 문자 수 비교."""
    hangul = 0
    latin = 0
    for ch in display_text:
        cp = ord(ch)
        if (
            _HANGUL_SYLLABLE_LO <= cp <= _HANGUL_SYLLABLE_HI
            or _JAMO_LO <= cp <= _JAMO_HI
            or (_COMPAT_JAMO_LO <= cp <= _COMPAT_JAMO_HI)
        ):
            hangul += 1
        elif ch.isascii() and ch.isalpha():
            latin += 1
    if hangul == 0 and latin == 0:
        return default
    return "ko" if hangul >= latin else "en"


def _furniture_reason(block: Block, display_text: str, metadata: DocumentMetadata | None) -> ct.FurnitureReason | None:
    """N7 — 페이지 헤더·꼬리말 컨테이너, `toc`, 파서 메타(`page_header_text` 등), 원 `furniture` 신호."""
    if block.container in (ct.BlockContainer.page_header, ct.BlockContainer.page_footer):
        return ct.FurnitureReason.repeated_header
    if block.type == ct.BlockType.toc:
        return ct.FurnitureReason.nav
    stripped = display_text.strip()
    if metadata is not None and stripped:
        header_footer: set[str] = set()
        for candidates in (metadata.page_header_text, metadata.page_footer_text):
            if candidates:
                header_footer.update(c.strip() for c in candidates)
        if stripped in header_footer:
            return ct.FurnitureReason.repeated_header
        if metadata.navigation_text and stripped in {c.strip() for c in metadata.navigation_text}:
            return ct.FurnitureReason.nav
    if block.furniture:
        return ct.FurnitureReason.repeated_header
    return None


def _judge_blocks(
    edited: list[_BlockEdit],
    *,
    metadata: DocumentMetadata | None,
    document_lang: str,
    config: NormalizerChainConfig,
) -> tuple[list[ct.NormalizedBlock], list[HeadingNode], list[str]]:
    """N6~N9 판정 + `NormalizedBlock`/`heading_tree`/제거된 boilerplate 텍스트 목록 조립."""
    normalized_blocks: list[ct.NormalizedBlock] = []
    heading_tree: list[HeadingNode] = []
    heading_stack: list[tuple[int, str]] = []
    prev_body_text: str | None = None
    boilerplate_texts: list[str] = []

    for item in edited:
        block = item.block
        display_text = item.display_text
        reason = _furniture_reason(block, display_text, metadata) if config.furniture_enabled else None
        if reason is None and config.dedup_enabled:
            stripped = display_text.strip()
            is_unexpected_empty = not stripped and block.type not in _EMPTY_OK_TYPES
            is_adjacent_duplicate = bool(stripped) and stripped == prev_body_text
            if is_unexpected_empty or is_adjacent_duplicate:
                reason = ct.FurnitureReason.boilerplate
        boilerplate = reason is not None
        if not boilerplate and display_text.strip():
            prev_body_text = display_text.strip()
        if boilerplate:
            boilerplate_texts.append(display_text)

        if config.heading_reinfer_enabled and block.type == ct.BlockType.heading and not boilerplate:
            declared = block.level if block.level is not None else 0
            corrected = min(declared, heading_stack[-1][0] + 1) if heading_stack else max(declared, 0)
            corrected = min(max(corrected, 0), 6)
            while heading_stack and heading_stack[-1][0] >= corrected:
                heading_stack.pop()
            path = [*[text for _, text in heading_stack], display_text][-_MAX_HEADING_PATH:]
            heading_stack.append((corrected, display_text))
            heading_tree.append(HeadingNode(block_id=block.block_id, level=corrected, path=path))

        lang = _detect_lang(display_text, default=document_lang)
        sentence_spans = [] if not display_text else [ct.SentenceSpan(start=0, end=len(display_text), sub_spans=[])]
        normalized_blocks.append(
            ct.NormalizedBlock(
                block_id=block.block_id,
                display_text=display_text,
                lexical_text=item.lexical_text,
                offset_map=item.offset_map,  # type: ignore[arg-type]  # pydantic coerces list[list[int]]
                sentence_spans=sentence_spans,
                lang=lang,
                boilerplate=boilerplate,
                furniture_reason=reason,
                text_source=block.source,
                confidence=block.confidence,
            )
        )
    return normalized_blocks, heading_tree, boilerplate_texts


def _boilerplate_removed_items(texts: list[str]) -> list[BoilerplateRemovedItem]:
    """계약 `NormalizationReport.boilerplate_removed` — 중복 제거·코드포인트 순 정렬·1000개 상한."""
    seen: list[str] = []
    seen_set: set[str] = set()
    for text in texts:
        if text in seen_set:
            continue
        seen_set.add(text)
        seen.append(text)
        if len(seen) >= _MAX_BOILERPLATE_ITEMS:
            break
    seen.sort()
    return [
        BoilerplateRemovedItem(f"h:{blake3_hex(text)}" if len(text) > _MAX_BOILERPLATE_CHARS else text) for text in seen
    ]


class NormalizerChainStage:
    """`normalizer.chain` — 플랫폼 소유 합성 스테이지(04-pipelines/09 §1)의 축소 범위(F1-06) 구현."""

    plugin_id = "normalizer.chain"
    config_schema = NormalizerChainConfig
    requires_lineage: tuple[str, ...] = ()

    def __init__(self, config: NormalizerChainConfig | None = None) -> None:
        """설정을 고정한다(설정은 `config_hash` → `fingerprint` → `stage_key` 입력)."""
        self.config = config or NormalizerChainConfig()

    def config_hash(self) -> str:
        """`H("config", canonical_json(config))`(바이블 §6.2 근사, hwpx 파서와 같은 규약)."""
        canonical = json.dumps(
            self.config.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), ensure_ascii=False
        )
        return hash_of("config", canonical)

    def capabilities(self) -> ct.Capabilities:
        """`isolation_modes=[in_process]`, 재개 미지원, GPU 불필요(순수 함수 스테이지)."""
        return ct.Capabilities(
            isolation_modes=[ct.IsolationMode.in_process],
            supports_resumable=False,
            contracts_compat=ct.ContractsCompat(">=1.0,<2.0"),
            input_formats=[],
            requires_gpu=False,
        )

    def fingerprint(self) -> str:
        """`H("producer", plugin_id, plugin_version, config_hash, "", analyzer/dict model_ids)`."""
        analyzer_id = self.config.analyzer_id or _DEFAULT_ANALYZER_ID
        dictionary_hash = self.config.dictionary_hash or hash_of("dict")
        model_ids = ",".join(sorted([f"analyzer:{analyzer_id}", f"dict:{dictionary_hash}"]))
        return hash_of("producer", self.plugin_id, PLUGIN_VERSION, self.config_hash(), "", model_ids)

    async def run(self, inp: ParsedDocument, ctx: Any) -> NormalizedDocument:
        """`ParsedDocument` → `NormalizedDocument`(N1·N2·N6~N9만; 나머지는 WP-106 DEFERRED)."""
        parsed_ref = _resolve_parsed_ref(ctx, self.plugin_id)
        analyzer = getattr(ctx, "analyzer", None)
        korean_join = analyzer.normalize if (analyzer is not None and self.config.linebreaks_enabled) else None

        edited: list[_BlockEdit] = []
        removed_control_total = 0
        nfd_composed_total = 0
        for block in inp.blocks:
            working, edits, u_stats = clean_unicode(block.text)
            removed_control_total += u_stats["removed_control_chars"]
            nfd_composed_total += u_stats["nfd_composed"]
            if _should_merge_linebreaks(block, inp.source_kind):
                working, layout_edits, _l_stats = merge_linebreaks(
                    working, enabled=self.config.linebreaks_enabled, korean_join=korean_join
                )
                edits = [*edits, *layout_edits]
            try:
                display_text, offset_map = apply_edits(working, edits)
            except ValueError as exc:
                overlap_code = "contract.violation"
                overlap_detail = f"overlapping normalize edits in block {block.block_id}: {exc}"
                raise StageError(
                    overlap_code, stage="normalize", plugin_id=self.plugin_id, detail=overlap_detail
                ) from exc
            if unicodedata.normalize("NFC", display_text) != display_text:
                nfc_code = "normalize.nfd_residual"
                nfc_detail = f"display_text not NFC after edits in block {block.block_id}"
                raise StageError(nfc_code, stage="normalize", plugin_id=self.plugin_id, detail=nfc_detail)
            lexical_text = fold_lexical(display_text)
            if self.config.spacing_correction_enabled and analyzer is not None:
                lexical_text = analyzer.normalize(lexical_text)
            edited.append(
                _BlockEdit(block=block, display_text=display_text, lexical_text=lexical_text, offset_map=offset_map)
            )

        normalized_blocks, heading_tree, boilerplate_texts = _judge_blocks(
            edited, metadata=inp.metadata, document_lang=inp.language.root, config=self.config
        )

        warnings = [
            ct.Warning(
                code=ct.ErrorCodeCatalog.normalize_segmenter_fallback,
                message="sentence_splitter not wired in WP-106; whole-block placeholder sentence_spans",
            )
        ]
        quality = ct.Quality.degraded if inp.quality == ct.Quality.degraded or warnings else ct.Quality.full

        analyzer_id = (
            self.config.analyzer_id or (analyzer.analyzer_id if analyzer is not None else None) or _DEFAULT_ANALYZER_ID
        )
        dictionary_hash = self.config.dictionary_hash or hash_of("dict")
        pii_policy = ct.PiiPolicy.keep
        normalizer_fingerprint = hash_of(
            "normalizer",
            self.plugin_id,
            PLUGIN_VERSION,
            self.config_hash(),
            analyzer_id,
            dictionary_hash,
            pii_policy.value,
            "none",
        )

        genre = inp.metadata.genre if inp.metadata is not None and inp.metadata.genre else ct.Genre.unknown
        genre_source = GenreSource.parser if inp.metadata is not None and inp.metadata.genre else GenreSource.heuristic

        body_count = sum(1 for b in normalized_blocks if not b.boilerplate)
        furniture_count = len(normalized_blocks) - body_count
        display_chars = sum(len(b.display_text) for b in normalized_blocks)
        lexical_chars = sum(len(b.lexical_text) for b in normalized_blocks)
        sentence_count = sum(len(b.sentence_spans) for b in normalized_blocks)

        parsed_artifact_ref = ct.ArtifactRef(
            uri=parsed_ref.uri,
            blake3=parsed_ref.blake3,
            media_type=parsed_ref.media_type,
            schema_type=ct.SchemaTypeName(parsed_ref.schema_type),
            schema_version=parsed_ref.schema_version,
            size_bytes=parsed_ref.size_bytes,
            stage_key=parsed_ref.stage_key,
        )

        return NormalizedDocument(
            schema_version="1.0.0",
            schema_type="NormalizedDocument",
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
            lineage_refs=LineageRefs(source=inp.lineage_refs.source, parsed=parsed_artifact_ref),
            document_id=inp.document_id,
            doc_version=inp.doc_version,
            parsed_ref=parsed_ref,
            normalizer_fingerprint=normalizer_fingerprint,
            analyzer_id=analyzer_id,
            dictionary_hash=dictionary_hash,
            language=inp.language,
            genre=genre,
            genre_source=genre_source,
            blocks=normalized_blocks,
            heading_tree=heading_tree,
            annotations=Annotations(pii_spans=[], content_risk=None),
            pii_report=PiiReport(
                policy_applied=pii_policy, entity_counts={}, detector_version="none", tokenize_mode_applied=None
            ),
            normalization_report=NormalizationReport(
                removed_control_chars=removed_control_total,
                nfd_composed=nfd_composed_total,
                hanja_replaced=0,
                spacing_corrected=bool(self.config.spacing_correction_enabled and analyzer is not None),
                boilerplate_removed=_boilerplate_removed_items(boilerplate_texts),
            ),
            stats=NormalizationStats(
                block_count=len(normalized_blocks),
                body_block_count=body_count,
                furniture_block_count=furniture_count,
                display_chars=display_chars,
                lexical_chars=lexical_chars,
                sentence_count=sentence_count,
                pii_span_count=0,
                analyzer_token_count=None,
            ),
            table_cell_views=None,
        )
