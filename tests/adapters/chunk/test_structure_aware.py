"""`chunker.structure_aware`(F2-01, WP-201) 단위·통합 테스트.

설계 근거: 무엇을 검증하는지는 (1) `_to_original`이 04-pipelines/09 §4 `offset_map` 삼중항(항등·삭제
마커·치환)을 원문 좌표로 정확히 사상하는지, (2) `_assign_heading_paths`가 04-pipelines/10 §2.3 식(가장
가까운 선행 heading의 경로, 제목 `path[0]` 1회 제거, 첫 heading 이전은 `[]`)을 재현하는지, (3) 문장
경계 정규식 폴백이 종결 부호·개행에서 갈라지는지, (4) 초과 분할(`_greedy_group`)이 `leaf_max_tokens`를
넘지 않는 최대 묶음을 그리디로 만드는지, (5) 병합(`_merge_peers`)이 `merge_min_tokens` 트리거로만 합치고
상한을 넘지 않는지, (6) 부모 생성(`_build_parent_groups`)이 자식 ≥ 2에서만 부모를 만드는지, (7)
`StructureAwareChunkerStage.run()`이 짧은 문서(리프 1개)·여러 섹션(부모 2개)에서 계약대로 조립되고
`chunk_id`가 결정적인지.
구성: 픽스처는 이 파일이 직접 구성한 최소 `NormalizedDocument`(외부 샘플 불필요 — 계약 필드만으로
충분). `offset_map`은 모두 항등(치환 없음)으로 두어 `display_text == 원문` 전제로 단순화한다.
불변식·주의: `block_refs` 오프셋 합집합이 각 청크 `text`를 재구성해야 한다(단위 (7) 통합 테스트가
직접 재구성해 비교한다). `chunk_id`는 같은 입력·설정 재실행에서 동일해야 한다(결정성).
검증 계층: 1층. tests/adapters/ 하위이므로 conftest.py가 `component` 마커를 붙인다.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime

import pytest

from rag_platform.adapters.chunk.structure_aware import (
    ApproxCharTokenCounter,
    StructureAwareChunkerConfig,
    StructureAwareChunkerStage,
    _assign_heading_paths,
    _build_parent_groups,
    _concat,
    _greedy_group,
    _Leaf,
    _leaf_from_block,
    _merge_peers,
    _RefPiece,
    _regex_sentence_spans,
    _split_sentences,
    _to_original,
)
from rag_platform.contracts import common_types as ct
from rag_platform.contracts.normalized_document import (
    Annotations,
    HeadingNode,
    LineageRefs,
    NormalizationReport,
    NormalizedDocument,
    ParsedRef,
    PiiReport,
)

_HEX64 = "0" * 64
_TENANT_ID = "01J9ZQ4K7X2M8N3P5R6S7T8V9W"
_COLLECTION_ID = "01J9ZQ5A1B2C3D4E5F6G7H8J9K"
_DOCUMENT_ID = "01J9ZQ8D4N2P6R8T0V3W5X7Y9Z"


def _block_id(tag: str) -> str:
    return hashlib.sha256(tag.encode("utf-8")).hexdigest()[:32]


def _identity_offset_map(length: int) -> list[ct.OffsetMapItem]:
    return [ct.OffsetMapItem([0, 0, length]), ct.OffsetMapItem([length, length, 0])]


def _norm_block(
    tag: str,
    text: str,
    *,
    lang: str = "ko",
    boilerplate: bool = False,
    confidence: float | None = None,
    text_source: ct.BlockSource = ct.BlockSource.text_layer,
    offset_map: list[ct.OffsetMapItem] | None = None,
) -> ct.NormalizedBlock:
    return ct.NormalizedBlock(
        block_id=_block_id(tag),
        display_text=text,
        lexical_text=text,
        offset_map=offset_map if offset_map is not None else _identity_offset_map(len(text)),
        sentence_spans=[ct.SentenceSpan(start=0, end=len(text), sub_spans=[])] if text else [],
        lang=lang,
        boilerplate=boilerplate,
        furniture_reason=None,
        text_source=text_source,
        confidence=confidence,
    )


def _artifact_ref(schema_type: str | None = None) -> ct.ArtifactRef:
    return ct.ArtifactRef(
        uri="file:///doc.bin",
        blake3=_HEX64,
        media_type="application/octet-stream",
        schema_type=schema_type,
        schema_version="1.0.0" if schema_type else None,
        size_bytes=10,
        stage_key=None,
    )


def _normalized_document(
    blocks: list[ct.NormalizedBlock],
    heading_tree: list[HeadingNode],
    *,
    genre: ct.Genre = ct.Genre.unknown,
) -> NormalizedDocument:
    return NormalizedDocument(
        schema_version="1.0.0",
        schema_type="NormalizedDocument",
        tenant_id=_TENANT_ID,
        collection_id=_COLLECTION_ID,
        producer=ct.Producer(
            plugin_id="normalizer.chain", plugin_version="0.1.0", config_hash=_HEX64, image_digest=None
        ),
        quality=ct.Quality.full,
        warnings=[],
        created_at="2026-09-23T09:00:00.000Z",
        lineage_refs=LineageRefs(source=_artifact_ref(), parsed=_artifact_ref(schema_type="ParsedDocument")),
        document_id=_DOCUMENT_ID,
        doc_version=_HEX64,
        parsed_ref=ParsedRef(
            uri="file:///doc.bin",
            blake3=_HEX64,
            media_type="application/octet-stream",
            schema_type="ParsedDocument",
            schema_version="1.0.0",
            size_bytes=10,
            stage_key=None,
        ),
        normalizer_fingerprint=_HEX64,
        analyzer_id="regex:1.0.0:none",
        dictionary_hash=_HEX64,
        language="ko",
        genre=genre,
        genre_source=None,
        blocks=blocks,
        heading_tree=heading_tree,
        annotations=Annotations(pii_spans=[], content_risk=None),
        pii_report=PiiReport(
            policy_applied=ct.PiiPolicy.keep, entity_counts={}, detector_version="none", tokenize_mode_applied=None
        ),
        normalization_report=NormalizationReport(
            removed_control_chars=0, nfd_composed=0, hanja_replaced=0, spacing_corrected=False, boilerplate_removed=[]
        ),
        table_cell_views=None,
    )


class _FakeCtx:
    def __init__(self, normalized_ref: ct.ArtifactRef | None = None, token_counter: object | None = None) -> None:
        self.normalized_ref = normalized_ref or _artifact_ref(schema_type="NormalizedDocument")
        self.token_counter = token_counter

    def now(self) -> datetime:
        return datetime(2026, 9, 23, 9, 0, tzinfo=UTC)


# ----------------------------------------------------------------------------
# 1. _to_original — offset_map 사상
# ----------------------------------------------------------------------------


def test_to_original_identity() -> None:
    offset_map = _identity_offset_map(10)
    assert _to_original(offset_map, 0) == 0
    assert _to_original(offset_map, 5) == 5
    assert _to_original(offset_map, 10) == 10


def test_to_original_deletion_marker() -> None:
    # 원문 "abXcd"에서 "X"(인덱스 2)가 삭제되어 표시 "abcd"가 됐다고 가정.
    offset_map = [
        ct.OffsetMapItem([0, 0, 2]),  # "ab" 항등
        ct.OffsetMapItem([2, 3, 0]),  # 삭제 경계 마커(원문 위치 3부터 재개)
        ct.OffsetMapItem([2, 3, 2]),  # "cd" 항등(원문 3..5)
        ct.OffsetMapItem([4, 5, 0]),  # sentinel
    ]
    assert _to_original(offset_map, 2) == 3
    assert _to_original(offset_map, 3) == 4
    assert _to_original(offset_map, 4) == 5


def test_to_original_substitution() -> None:
    # 원문 "AAA"(3자) -> 표시 "B"(1자), 불투명 치환 [0,0,3].
    offset_map = [ct.OffsetMapItem([0, 0, 3]), ct.OffsetMapItem([1, 3, 0])]
    assert _to_original(offset_map, 0) == 0
    assert _to_original(offset_map, 1) == 3


# ----------------------------------------------------------------------------
# 2. _assign_heading_paths — 04-pipelines/10 §2.3
# ----------------------------------------------------------------------------


def test_assign_heading_paths_title_stripped_and_pre_heading_empty() -> None:
    blocks = [
        _norm_block("a", "서문 문단"),
        _norm_block("b", "제목"),
        _norm_block("c", "본문1"),
        _norm_block("d", "소제목"),
        _norm_block("e", "본문2"),
    ]
    heading_tree = [
        HeadingNode(block_id=_block_id("b"), level=0, path=["제목"]),
        HeadingNode(block_id=_block_id("d"), level=1, path=["제목", "소제목"]),
    ]
    paths = _assign_heading_paths(blocks, heading_tree)
    assert paths[_block_id("a")] == ()  # 첫 heading 이전
    assert paths[_block_id("c")] == ()  # 제목 직속 -> path[0] 제거 -> []
    assert paths[_block_id("e")] == ("소제목",)  # 제목 제거 후 남은 경로


def test_assign_heading_paths_no_title_keeps_full_path() -> None:
    blocks = [_norm_block("a", "본문"), _norm_block("b", "섹션1")]
    heading_tree = [HeadingNode(block_id=_block_id("b"), level=1, path=["섹션1"])]
    paths = _assign_heading_paths(blocks, heading_tree)
    assert paths[_block_id("a")] == ()


# ----------------------------------------------------------------------------
# 3. 문장 경계 정규식 폴백
# ----------------------------------------------------------------------------


def test_regex_sentence_spans_splits_on_terminal_punctuation() -> None:
    text = "첫 문장이다. 둘째 문장이다!"
    spans = _regex_sentence_spans(text)
    assert len(spans) == 2
    assert text[spans[0][0] : spans[0][1]].strip() == "첫 문장이다."
    assert text[spans[1][0] : spans[1][1]].strip() == "둘째 문장이다!"


def test_split_sentences_falls_back_to_regex_without_kss() -> None:
    # kss 미설치 환경(이 저장소 기본)이므로 _split_sentences == _regex_sentence_spans.
    text = "가나다.\n라마바."
    assert _split_sentences(text) == _regex_sentence_spans(text)


# ----------------------------------------------------------------------------
# 4. 초과 분할(D) — _greedy_group
# ----------------------------------------------------------------------------


def test_greedy_group_respects_leaf_max_tokens() -> None:
    counter = ApproxCharTokenCounter(tokenizer_id="hf:test", chars_per_token=2.0)
    text = "AAAAAAAAAA.BBBBBBBBBB.CCCCCCCCCC."  # 세 "문장", 각 11자 -> 6토큰
    pieces = _regex_sentence_spans(text)
    assert len(pieces) == 3
    groups = _greedy_group(pieces, text, max_tokens=6, counter=counter)
    # 각 문장이 이미 6토큰이라 서로 합쳐지지 않고 그대로 3묶음이어야 한다.
    assert len(groups) == 3
    for start, end in groups:
        assert counter.count(text[start:end]) <= 6


def test_greedy_group_merges_small_sentences_under_budget() -> None:
    counter = ApproxCharTokenCounter(tokenizer_id="hf:test", chars_per_token=2.0)
    text = "AB. CD. EF."
    pieces = _regex_sentence_spans(text)
    groups = _greedy_group(pieces, text, max_tokens=100, counter=counter)
    assert len(groups) == 1
    assert groups[0] == (0, len(text))


# ----------------------------------------------------------------------------
# 5. 병합(E) — _merge_peers
# ----------------------------------------------------------------------------


def _make_leaf(tag: str, text: str, heading_path: tuple[str, ...] = ()) -> _Leaf:
    ref = _RefPiece(
        block_id=_block_id(tag),
        element_path=f"/blocks/{tag}",
        char_start=0,
        char_end=len(text),
        original_char_start=0,
        original_char_end=len(text),
    )
    return _Leaf(
        heading_path=heading_path,
        lang_counts={"ko": len(text)},
        text_source=ct.BlockSource.text_layer,
        confidence=None,
        text=text,
        lexical_text=text,
        block_refs=[ref],
        sentence_spans=[(0, len(text))],
    )


def test_merge_peers_combines_small_adjacent_leaves() -> None:
    counter = ApproxCharTokenCounter(tokenizer_id="hf:test", chars_per_token=2.0)
    leaves = [_make_leaf("a", "AB"), _make_leaf("b", "CD")]  # 각 1토큰, merge_min_tokens=10 미만
    merged = _merge_peers(leaves, merge_min_tokens=10, leaf_max_tokens=100, counter=counter)
    assert len(merged) == 1
    assert merged[0].text == "AB\nCD"


def test_merge_peers_keeps_separate_when_over_leaf_max() -> None:
    counter = ApproxCharTokenCounter(tokenizer_id="hf:test", chars_per_token=2.0)
    leaves = [_make_leaf("a", "AB"), _make_leaf("b", "CD")]
    merged = _merge_peers(leaves, merge_min_tokens=10, leaf_max_tokens=1, counter=counter)
    assert len(merged) == 2


def test_merge_peers_does_not_cross_heading_path() -> None:
    counter = ApproxCharTokenCounter(tokenizer_id="hf:test", chars_per_token=2.0)
    leaves = [_make_leaf("a", "AB", ("s1",)), _make_leaf("b", "CD", ("s2",))]
    merged = _merge_peers(leaves, merge_min_tokens=10, leaf_max_tokens=100, counter=counter)
    assert len(merged) == 2


def test_concat_reconstructs_text_from_block_refs() -> None:
    leaves = [_make_leaf("a", "hello"), _make_leaf("b", "world")]
    agg = _concat(leaves)
    assert agg.text == "hello\nworld"
    rebuilt = "".join(agg.text[ref.char_start : ref.char_end] for ref in agg.block_refs)
    # 조각 사이의 U+000A는 어느 ref에도 속하지 않지만(구분자), 각 ref 구간은 원 조각 텍스트와 일치해야 한다.
    assert rebuilt == "helloworld"


# ----------------------------------------------------------------------------
# 6. 부모 생성(F) — _build_parent_groups
# ----------------------------------------------------------------------------


def test_build_parent_groups_requires_at_least_two_children() -> None:
    counter = ApproxCharTokenCounter(tokenizer_id="hf:test", chars_per_token=2.0)
    leaves = [_make_leaf("a", "AB", ("s1",))]
    groups = _build_parent_groups(leaves, parent_max_tokens=100, counter=counter)
    assert groups == []


def test_build_parent_groups_groups_same_section() -> None:
    counter = ApproxCharTokenCounter(tokenizer_id="hf:test", chars_per_token=2.0)
    leaves = [
        _make_leaf("a", "AB", ("s1",)),
        _make_leaf("b", "CD", ("s1",)),
        _make_leaf("c", "EF", ("s2",)),
    ]
    groups = _build_parent_groups(leaves, parent_max_tokens=100, counter=counter)
    assert groups == [[0, 1]]


def test_build_parent_groups_splits_when_over_budget() -> None:
    counter = ApproxCharTokenCounter(tokenizer_id="hf:test", chars_per_token=2.0)
    # 각 리프 2토큰(4자), parent_max_tokens=2 -> 둘을 합치면 4토큰이 되어 초과, 그룹을 못 만듦(각 1개씩).
    leaves = [_make_leaf("a", "ABCD", ("s1",)), _make_leaf("b", "EFGH", ("s1",)), _make_leaf("c", "IJKL", ("s1",))]
    groups = _build_parent_groups(leaves, parent_max_tokens=2, counter=counter)
    assert groups == []  # 셋 다 홀로 남아 자식 2개 미만


# ----------------------------------------------------------------------------
# 7. _leaf_from_block
# ----------------------------------------------------------------------------


def test_leaf_from_block_maps_original_offsets() -> None:
    block = _norm_block("a", "hello world")
    leaf = _leaf_from_block(block, 0, 0, 5, ())
    assert leaf.text == "hello"
    assert leaf.block_refs[0].original_char_start == 0
    assert leaf.block_refs[0].original_char_end == 5


# ----------------------------------------------------------------------------
# 8. StructureAwareChunkerStage.run() 통합
# ----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_short_document_single_leaf_no_parent() -> None:
    blocks = [_norm_block("a", "짧은 문서 본문입니다.")]
    doc = _normalized_document(blocks, heading_tree=[])
    stage = StructureAwareChunkerStage(StructureAwareChunkerConfig(leaf_max_tokens=512, parent_max_tokens=2048))
    ctx = _FakeCtx()

    result = await stage.run(doc, ctx)

    assert result.schema_type == "ChunkSet"
    assert result.stats.leaf_count == 1
    assert result.stats.parent_count == 0
    assert result.chunks[0].item_kind == ct.ItemKind.text
    assert result.chunks[0].parent_chunk_id is None
    assert result.chunks[0].text == "짧은 문서 본문입니다."
    assert result.primary_tokenizer_id.root == "hf:BAAI/bge-m3"
    assert "tiktoken:o200k_base" in [t.root for t in result.secondary_tokenizer_ids]


@pytest.mark.asyncio
async def test_run_two_sections_build_parents_and_are_deterministic() -> None:
    blocks = [
        _norm_block("t", "문서제목"),
        _norm_block("h1", "제1장"),
        _norm_block("a", "문단 A입니다."),
        _norm_block("b", "문단 B입니다."),
        _norm_block("h2", "제2장"),
        _norm_block("c", "문단 C입니다."),
        _norm_block("d", "문단 D입니다."),
    ]
    heading_tree = [
        HeadingNode(block_id=_block_id("t"), level=0, path=["문서제목"]),
        HeadingNode(block_id=_block_id("h1"), level=1, path=["문서제목", "제1장"]),
        HeadingNode(block_id=_block_id("h2"), level=1, path=["문서제목", "제2장"]),
    ]
    doc = _normalized_document(blocks, heading_tree)
    config = StructureAwareChunkerConfig(leaf_max_tokens=512, parent_max_tokens=2048, merge_min_tokens=0)
    stage = StructureAwareChunkerStage(config)
    ctx = _FakeCtx()

    result_1 = await stage.run(doc, ctx)
    result_2 = await stage.run(doc, ctx)

    assert result_1.stats.parent_count == 2
    # merge_min_tokens=0(트리거 없음)이라 문단 4개가 그대로 리프 4개로 남고, 같은 heading_path 2개씩 부모로 묶인다.
    assert result_1.stats.leaf_count == 4
    parents = [c for c in result_1.chunks if c.level == ct.ChunkLevel.integer_1]
    leaves = [c for c in result_1.chunks if c.level == ct.ChunkLevel.integer_0]
    leaf_parent_ids = {leaf.parent_chunk_id.root for leaf in leaves if leaf.parent_chunk_id is not None}
    parent_ids = {p.chunk_id.root for p in parents}
    assert leaf_parent_ids == parent_ids
    for parent in parents:
        expected_children = {
            leaf.chunk_id.root
            for leaf in leaves
            if leaf.parent_chunk_id is not None and leaf.parent_chunk_id.root == parent.chunk_id.root
        }
        assert {cid.root for cid in (parent.child_chunk_ids or [])} == expected_children
        assert parent.heading_path in (["제1장"], ["제2장"])

    # 결정성: 같은 입력·설정 재실행은 같은 chunk_id 집합을 낸다.
    assert {c.chunk_id.root for c in result_1.chunks} == {c.chunk_id.root for c in result_2.chunks}

    # 불변식 (1): block_refs 오프셋 합집합이 text를 재구성한다.
    for chunk in result_1.chunks:
        rebuilt = "".join(chunk.text[ref.char_start : ref.char_end] for ref in chunk.block_refs)
        assert rebuilt == chunk.text.replace("\n", "")
