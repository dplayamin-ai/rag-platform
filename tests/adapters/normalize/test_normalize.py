"""`normalizer.chain`(F1-06, WP-106) 컴포넌트·단위 테스트.

설계 근거: 무엇을 검증하는지는 (1) `korean/unicode.py`의 `apply_edits`가 04-pipelines/09 §4의
오프셋 맵 예시 4종을 글자 그대로 재현하는지(라틴 분철, 한글 줄바꿈 결합, CRLF, 동일 길이 개행→공백),
`clean_unicode`가 NBSP·zero-width·PUA·NFC 자모 합성을 U1~U5대로 처리하는지, `fold_lexical`이
호환 자모를 보존하는지. (2) `korean/layout.py`의 `merge_linebreaks`가 `enabled=False`일 때
무변화이고 하이픈·한글 줄바꿈을 결합하는지. (3) `NormalizerChainStage.run()`이 최소
`ParsedDocument`(제목·레벨 점프 소제목·반복 머리말·본문·인접 중복·빈 블록·분철 문단)로부터
`NormalizedDocument`를 조립할 때 furniture/dedup/heading_tree/offset_map/quality가 기대대로
나오는지.
구성: 픽스처 출처는 04-pipelines/09 §4(오프셋 맵 예시), 이 파일이 직접 구성한 최소 `ParsedDocument`
(외부 샘플 불필요 — 계약 필드만으로 충분).
불변식·주의: 오프셋 맵은 원문 좌표계를 벗어나지 않아야 하고(각 항목이 원문 범위 내), furniture 판정은
멱등적이어야 한다(같은 입력 재실행 시 같은 결과).
검증 계층: 1층. tests/adapters/ 하위이므로 conftest.py가 `component` 마커를 붙인다.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any

import pytest

from rag_platform.adapters.normalize.korean.layout import merge_linebreaks
from rag_platform.adapters.normalize.korean.unicode import Edit, apply_edits, clean_unicode, fold_lexical
from rag_platform.adapters.normalize.stage import NormalizerChainConfig, NormalizerChainStage
from rag_platform.contracts import common_types as ct
from rag_platform.contracts.normalized_document import NormalizedDocument, ParsedRef
from rag_platform.contracts.parsed_document import (
    Block,
    DocumentMetadata,
    LineageRefs,
    ParsedDocument,
    ParserFingerprint,
)
from rag_platform.sdk.stage import StageError

_HEX64 = "0" * 64
_TENANT_ID = "01J9ZQ4K7X2M8N3P5R6S7T8V9W"
_COLLECTION_ID = "01J9ZQ5A1B2C3D4E5F6G7H8J9K"
_DOCUMENT_ID = "01J9ZQ8D4N2P6R8T0V3W5X7Y9Z"

# 이스케이프 표기 없이 문자 코드로 참조(RUF001 애매한 유사 문자·PLE2515 회피).
_NBSP = chr(0x00A0)
_ZERO_WIDTH_SPACE = chr(0x200B)
_PRIVATE_USE_CHAR = chr(0xE000)
_CHOSEONG_G = chr(0x1100)
_JUNGSEONG_A = chr(0x1161)
_FULLWIDTH_A = chr(0xFF21)


class _FakeCtx:
    def __init__(self, parsed_ref: ParsedRef | None, *, analyzer: Any = None) -> None:
        self.parsed_ref = parsed_ref
        self.analyzer = analyzer

    def now(self) -> datetime:
        return datetime(2026, 9, 23, 9, 0, tzinfo=UTC)


def _block_id(tag: str) -> str:
    return (tag * 32)[:32]


def _provenance(start: int, end: int) -> ct.Provenance:
    return ct.Provenance(element_path=f"/p[{start}]", char_start=start, char_end=end, page=1, bbox=None)


def _block(
    tag: str,
    text: str,
    *,
    type_: ct.BlockType = ct.BlockType.paragraph,
    container: ct.BlockContainer = ct.BlockContainer.body,
    level: int | None = None,
    furniture: bool = False,
) -> Block:
    return Block(
        block_id=_block_id(tag),
        type=type_,
        parent_block_id=None,
        ordinal=0,
        text=text,
        level=level,
        furniture=furniture,
        container=container,
        source=ct.BlockSource.text_layer,
        confidence=None,
        provenance=_provenance(0, len(text)),
    )


def _parsed_document(blocks: list[Block], *, source_kind: ct.SourceKind = ct.SourceKind.born_digital) -> ParsedDocument:
    source_ref = ct.ArtifactRef(
        uri="file:///tenants/t/sources/aa/aa.bin",
        blake3=_HEX64,
        media_type="application/octet-stream",
        size_bytes=10,
    )
    return ParsedDocument(
        schema_version="1.0.0",
        schema_type="ParsedDocument",
        tenant_id=_TENANT_ID,
        collection_id=_COLLECTION_ID,
        producer=ct.Producer(
            plugin_id="parser.pdf_fast_pdftext", plugin_version="1.0.0", config_hash=_HEX64, image_digest=None
        ),
        quality=ct.Quality.full,
        warnings=[],
        created_at="2026-09-23T09:00:00.000Z",
        lineage_refs=LineageRefs(source=source_ref),
        document_id=_DOCUMENT_ID,
        doc_version=_HEX64,
        source_ref=source_ref,
        parser_fingerprint=ParserFingerprint(
            parser_id="parser.pdf_fast_pdftext", parser_version="pdftext==1.0.0", profile_option="pdf_fast_cpu"
        ),
        parser_chain=["parser.pdf_fast_pdftext"],
        source_kind=source_kind,
        page_count=1 if source_kind != ct.SourceKind.flow else None,
        language="ko",
        metadata=DocumentMetadata(page_header_text=["반복 머리말"]),
        blocks=blocks,
        text_length=sum(len(b.text) for b in blocks),
        block_count=len(blocks),
    )


def _parsed_ref() -> ParsedRef:
    return ParsedRef(
        uri="file:///tenants/t/artifacts/parsed-document/aa/aa.json",
        blake3=_HEX64,
        media_type="application/vnd.rag.parsed-document+json",
        schema_type="ParsedDocument",
        schema_version="1.0.0",
        size_bytes=100,
        stage_key=None,
    )


# --- korean/unicode.py --------------------------------------------------------------------------


def test_apply_edits_latin_dehyphenation_matches_doc_example() -> None:
    display, offset_map = apply_edits("infor-\nmation", [Edit(5, 2, "")])
    assert display == "information"
    assert offset_map == [[0, 0, 5], [5, 5, 0], [5, 7, 6], [11, 13, 0]]


def test_apply_edits_korean_linebreak_join_matches_doc_example() -> None:
    display, offset_map = apply_edits("보안관\n리에서", [Edit(3, 1, "")])
    assert display == "보안관리에서"
    assert offset_map == [[0, 0, 3], [3, 3, 0], [3, 4, 3], [6, 7, 0]]


def test_apply_edits_crlf_matches_doc_example() -> None:
    display, offset_map = apply_edits("가\r\n나", [Edit(1, 1, "")])
    assert display == "가\n나"
    assert offset_map == [[0, 0, 1], [1, 1, 0], [1, 2, 2], [3, 4, 0]]


def test_apply_edits_no_edits_is_single_identity_span() -> None:
    display, offset_map = apply_edits("the quick brown", [])
    assert display == "the quick brown"
    assert offset_map == [[0, 0, 15], [15, 15, 0]]


def test_apply_edits_rejects_overlap() -> None:
    with pytest.raises(ValueError, match="overlapping"):
        apply_edits("abcdef", [Edit(0, 3, ""), Edit(2, 2, "")])


def test_clean_unicode_nbsp_is_cosmetic_single_span() -> None:
    working, edits, stats = clean_unicode(f"a{_NBSP}b")
    assert working == "a b"
    assert edits == []
    assert stats["removed_control_chars"] == 0


def test_clean_unicode_removes_control_and_pua_chars() -> None:
    text = f"a{_ZERO_WIDTH_SPACE}b{_PRIVATE_USE_CHAR}c\rd"
    working, edits, stats = clean_unicode(text)
    display, _offset_map = apply_edits(working, edits)
    assert display == "abcd"
    assert stats["removed_control_chars"] == 3


def test_clean_unicode_composes_conjoining_jamo() -> None:
    # U+1100(초성 ㄱ) + U+1161(중성 ㅏ) -> U+AC00 "가"
    working, edits, stats = clean_unicode(f"{_CHOSEONG_G}{_JUNGSEONG_A}")
    display, _offset_map = apply_edits(working, edits)
    assert display == "가"
    assert stats["nfd_composed"] == 1


def test_fold_lexical_preserves_compat_jamo_but_folds_fullwidth() -> None:
    assert fold_lexical("ㅋㅋ") == "ㅋㅋ"
    assert fold_lexical("ABC") == fold_lexical("ABC")
    assert fold_lexical(_FULLWIDTH_A) == "A"


# --- korean/layout.py ----------------------------------------------------------------------------


def test_merge_linebreaks_noop_when_disabled() -> None:
    text = "infor-\nmation"
    working, edits, _stats = merge_linebreaks(text, enabled=False)
    assert working == text
    assert edits == []


def test_merge_linebreaks_dehyphenates_latin() -> None:
    working, edits, stats = merge_linebreaks("infor-\nmation", enabled=True)
    display, _offset_map = apply_edits(working, edits)
    assert display == "information"
    assert stats["dehyphenated"] == 1


def test_merge_linebreaks_joins_korean_across_lines() -> None:
    working, edits, stats = merge_linebreaks("보안관\n리에서", enabled=True)
    display, _offset_map = apply_edits(working, edits)
    assert display == "보안관리에서"
    assert stats["linebreaks_merged"] == 1


def test_merge_linebreaks_replaces_other_newlines_with_space() -> None:
    working, edits, _stats = merge_linebreaks("the quick\nbrown", enabled=True)
    assert edits == []
    assert working == "the quick brown"


# --- stage.py: NormalizerChainStage --------------------------------------------------------------


def test_stage_five_members_and_deterministic_fingerprint() -> None:
    stage = NormalizerChainStage()
    assert stage.plugin_id == "normalizer.chain"
    assert stage.config_schema is NormalizerChainConfig
    caps = stage.capabilities()
    assert caps.isolation_modes == [ct.IsolationMode.in_process]
    assert stage.fingerprint() == stage.fingerprint()


async def _run(stage: NormalizerChainStage, doc: ParsedDocument, *, analyzer: Any = None) -> NormalizedDocument:
    return await stage.run(doc, _FakeCtx(_parsed_ref(), analyzer=analyzer))


def test_run_requires_parsed_ref_port() -> None:
    stage = NormalizerChainStage()
    doc = _parsed_document([_block("1", "본문")])
    with pytest.raises(StageError) as exc_info:
        asyncio.run(stage.run(doc, _FakeCtx(None)))
    assert exc_info.value.code == "contract.violation"


def test_run_builds_normalized_document_with_furniture_dedup_and_heading() -> None:
    title = _block("1", "문서 제목", type_=ct.BlockType.heading, level=0)
    subheading = _block("2", "소제목", type_=ct.BlockType.heading, level=3)  # 레벨 점프 -> 1로 보정
    header = _block("3", "반복 머리말", container=ct.BlockContainer.page_header)
    body = _block("4", "본문 문장입니다.")
    duplicate = _block("5", "본문 문장입니다.")  # 직전 본문과 동일 -> dedup
    empty = _block("6", "")
    hyphenated = _block("7", "infor-\nmation")

    doc = _parsed_document([title, subheading, header, body, duplicate, empty, hyphenated])
    stage = NormalizerChainStage(NormalizerChainConfig(linebreaks_enabled=True))
    normalized = asyncio.run(_run(stage, doc))

    assert normalized.schema_type == "NormalizedDocument"
    assert normalized.document_id.root == _DOCUMENT_ID
    assert [b.block_id for b in normalized.blocks] == [b.block_id for b in doc.blocks]

    by_id = {b.block_id.root: b for b in normalized.blocks}
    assert by_id[title.block_id.root].boilerplate is False
    assert by_id[header.block_id.root].boilerplate is True
    assert by_id[header.block_id.root].furniture_reason == ct.FurnitureReason.repeated_header
    assert by_id[body.block_id.root].boilerplate is False
    assert by_id[duplicate.block_id.root].boilerplate is True
    assert by_id[duplicate.block_id.root].furniture_reason == ct.FurnitureReason.boilerplate
    assert by_id[empty.block_id.root].boilerplate is True
    assert by_id[hyphenated.block_id.root].display_text == "information"

    levels = {node.block_id.root: node.level for node in normalized.heading_tree}
    assert levels[title.block_id.root] == 0
    assert levels[subheading.block_id.root] == 1  # 0 -> 1로 클램프(점프 3 거부)

    assert normalized.pii_report.policy_applied == ct.PiiPolicy.keep
    assert normalized.quality == ct.Quality.degraded  # 문장 분리기 미배선 경고(WP-106 DEFERRED)
    assert normalized.stats is not None
    assert normalized.stats.block_count == len(doc.blocks)
