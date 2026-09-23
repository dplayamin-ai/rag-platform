"""`embedder.pipeline`(`adapters/embed/stage.py`)·`embedder.sparse_bm25`(`adapters/embed/sparse_bm25.py`)
컴포넌트·단위 테스트(F3-01, WP-301).

설계 근거: 04-pipelines/12 §2.2(`EmbedderStageBase.run` 단계)·§2.4(절단)·§6.1(배치)·§12.3(sparse_bm25
공간 레시피), 바이블 §5.4 `EmbeddedChunkSet`/`VectorBundle`(ADR-0032 5멤버 스테이지).
불변식·주의: level=1(부모)은 절대 임베딩하지 않는다, dense는 재정규화 후 반드시 재검증한다,
`sparse_bm25.indices`/`values`는 토큰이 없어도 빈 리스트(`None` 금지)다.

무엇을 검증하는지: (1) `tokens_to_sparse_bm25`가 `qdrant.bm25_sparse.saturate`/`bm25_index` 참조
계산과 정확히 일치하고 해시 충돌 시 tf를 합산하는지, 빈 토큰이면 빈(≠ `None`) 벡터를 내는지.
(2) `sparse_bm25_space_id`/`sparse_bm25_revision`이 04-pipelines/12 §12.3 레시피(모델 ID·차원·
비정규화·무프롬프트) 그대로이고 `k1`/`b`/`avgdl`/`dictionary_hash` 변경이 공간을 바꾸는지.
(3) `EmbedStage.run`이 level 0·2만 선별하고 level 1은 제외하는지, dense가 L2 정규화되는지, 절단·
경고·`quality=degraded`가 doc 12 §2.4/§2.2 규칙을 따르는지, `embedding_space_ids`/
`embedding_profile_hash`가 정의식과 일치하는지, `ctx.analyzer`가 있으면 그것을 우선하는지,
`ctx.enriched_ref`/`ctx.lineage["ChunkSet"]` 부재가 `contract.violation`인지. (4) `plan_batches`가
doc 12 §6.1 알고리즘(토큰 내림차순·동률 오름차순·단독 배치·상한)대로인지.
픽스처 출처: 계약 필드만으로 구성한 최소 `EnrichedChunkSet`(외부 샘플 불필요, WP-106 테스트와 같은
방식) + `_FakeChunkSet`/`_FakeCtx`(WP-106 `_FakeCtx`처럼 `ctx.lineage["ChunkSet"]`/`ctx.enriched_ref`
같은 아직 공식화되지 않은 `StageContext` 확장만 담는 최소 이중 — normalize의 `ctx.parsed_ref`
관례와 동일선상).
검증 계층: 1층. tests/adapters/ 하위이므로 conftest.py가 `component` 마커를 붙인다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import pytest

from rag_platform.adapters.embed import space_id as space_id_fn
from rag_platform.adapters.embed.inprocess_fake import InprocessFakeEmbedder
from rag_platform.adapters.embed.sparse_bm25 import (
    PLUGIN_ID,
    SparseBm25Embedder,
    sparse_bm25_revision,
    sparse_bm25_space_id,
    tokens_to_sparse_bm25,
)
from rag_platform.adapters.embed.stage import EmbedStage, EmbedStageConfig, embed_cache_key, plan_batches
from rag_platform.adapters.index.qdrant.bm25_sparse import (
    BM25_B,
    BM25_K1,
    DEFAULT_AVGDL,
    WhitespaceTokenizer,
    bm25_index,
    saturate,
)
from rag_platform.contracts import common_types as ct
from rag_platform.contracts.embedded_chunk_set import EnrichedRef
from rag_platform.contracts.enriched_chunk_set import (
    BudgetUsed,
    ChunkSetRef,
    EnrichedChunkSet,
    EnrichStats,
    LineageRefs as EnrichedLineageRefs,
    Source as EnrichedSource,
)
from rag_platform.sdk.hashing import blake3_hex, hash_of
from rag_platform.sdk.stage import StageError

_HEX64 = "0" * 64
_TENANT_ID = "01J9ZQ4K7X2M8N3P5R6S7T8V9W"
_COLLECTION_ID = "01J9ZQ5A1B2C3D4E5F6G7H8J9K"
_DOCUMENT_ID = "01J9ZQ8D4N2P6R8T0V3W5X7Y9Z"
_CHUNK_SET_ID = "01J9ZQ9F6R8T0V2W4X6Y8Z1A3B"

_LEAF_ID = ("a" * 64)[:64]
_PARENT_ID = ("b" * 64)[:64]
_SUMMARY_ID = ("c" * 64)[:64]


# -------------------------------------------------------------------------------------------------
# fixtures: 계약 최소 픽스처 + 아직 공식화되지 않은 ctx 확장(ctx.enriched_ref/ctx.lineage["ChunkSet"])
# -------------------------------------------------------------------------------------------------


class _FakeTokenCounter:
    """문자 수 = 토큰 수(단조 증가 보장, 절단 이분 탐색 테스트를 결정적으로 만든다)."""

    tokenizer_id = "test:chars"

    def count(self, text: str) -> int:
        return len(text)


class _FakeAnalyzer:
    """`sdk.ports.KoreanAnalyzer` 최소 대역 — 공백 분리, 기본 토크나이저와 다른 `analyzer_id`."""

    analyzer_id = "fake-analyzer:1.0"

    def normalize(self, text: str) -> str:
        return text

    def tokenize(self, text: str) -> tuple[str, ...]:
        return tuple(text.split())


@dataclass
class _FakeArtifacts:
    stored: list[bytes] = field(default_factory=list)

    async def put_derived(self, data: bytes, *, kind: str, ext: str, media_type: str) -> ct.ArtifactRef:
        self.stored.append(data)
        return ct.ArtifactRef(
            uri=f"file:///derived/x.{ext}", blake3=blake3_hex(data), media_type=media_type, size_bytes=len(data)
        )

    async def put_source(self, data: bytes, *, media_type: str) -> ct.ArtifactRef:  # pragma: no cover - unused
        raise NotImplementedError


@dataclass
class _FakeChunk:
    chunk_id: str
    level: int


@dataclass
class _FakeChunkSet:
    chunks: list[_FakeChunk]


class _FakeCtx:
    def __init__(self, *, enriched_ref: Any, chunk_set: Any, analyzer: Any = None) -> None:
        self.enriched_ref = enriched_ref
        self.lineage: dict[str, Any] = {} if chunk_set is None else {"ChunkSet": chunk_set}
        self.analyzer = analyzer
        self.token_counter = _FakeTokenCounter()
        self.artifacts = _FakeArtifacts()

    def now(self) -> datetime:
        return datetime(2026, 9, 23, 9, 0, tzinfo=UTC)


def _enriched_ref() -> EnrichedRef:
    return EnrichedRef(
        uri="file:///enriched.json",
        blake3=_HEX64,
        media_type="application/vnd.rag.enriched-chunk-set+json",
        schema_type="EnrichedChunkSet",
        schema_version="1.0.0",
        size_bytes=10,
    )


def _artifact_ref() -> ct.ArtifactRef:
    return ct.ArtifactRef(uri="file:///x.json", blake3=_HEX64, media_type="application/json", size_bytes=1)


def _source_ref() -> EnrichedSource:
    return EnrichedSource(
        uri="file:///source.bin",
        blake3=_HEX64,
        media_type="application/vnd.rag.source-document+json",
        schema_type="SourceDocument",
        schema_version="1.0.0",
        size_bytes=1,
    )


def _enrichment(embed_text: str, index_text: str) -> ct.Enrichment:
    return ct.Enrichment(
        embed_text=embed_text,
        index_text=index_text,
        strip_offsets=ct.StripOffsets(text_start_in_embed=0, text_start_in_index=0),
        keywords=[],
        entities=[],
        risk_flags=[],
        risk_score=0.0,
        pii_entity_counts={},
        status=ct.EnrichStatus.complete,
    )


def _enriched_chunk_set(
    enrichments: dict[str, ct.Enrichment], *, quality: ct.Quality = ct.Quality.full
) -> EnrichedChunkSet:
    producer = ct.Producer(plugin_id="enricher.pipeline", plugin_version="0.1.0", config_hash=_HEX64, image_digest=None)
    lineage_refs = EnrichedLineageRefs(
        source=_source_ref(), parsed=_artifact_ref(), normalized=_artifact_ref(), chunk_set=_artifact_ref()
    )
    budget_used = BudgetUsed(
        provider=None,
        model_id=None,
        llm_tokens_in=0,
        llm_tokens_out=0,
        cost_usd=0.0,
        calls=0,
        budget_remaining_tokens=0,
    )
    return EnrichedChunkSet(
        schema_version="1.0.0",
        schema_type="EnrichedChunkSet",
        tenant_id=_TENANT_ID,
        collection_id=_COLLECTION_ID,
        producer=producer,
        quality=quality,
        warnings=[],
        created_at="2026-09-23T09:00:00.000Z",
        lineage_refs=lineage_refs,
        chunk_set_id=_CHUNK_SET_ID,
        document_id=_DOCUMENT_ID,
        doc_version=_HEX64,
        chunk_set_ref=ChunkSetRef(
            uri="file:///chunks.json",
            blake3=_HEX64,
            media_type="application/vnd.rag.chunk-set+json",
            schema_type="ChunkSet",
            schema_version="1.0.0",
            size_bytes=1,
        ),
        enricher_fingerprint=_HEX64,
        policy_hash=_HEX64,
        status=ct.EnrichStatus.complete,
        budget_used=budget_used,
        enrichments=enrichments,
        stats=EnrichStats(chunks_enriched=len(enrichments), llm_cache_hits=0, entities_total=0),
    )


def _three_level_chunk_set() -> _FakeChunkSet:
    """leaf(level 0)·parent(level 1)·summary(level 2) — parent만 임베딩 대상에서 빠져야 한다."""
    return _FakeChunkSet(
        chunks=[
            _FakeChunk(chunk_id=_LEAF_ID, level=0),
            _FakeChunk(chunk_id=_PARENT_ID, level=1),
            _FakeChunk(chunk_id=_SUMMARY_ID, level=2),
        ]
    )


def _stage(**overrides: Any) -> EmbedStage:
    kwargs: dict[str, Any] = {
        "embedder": InprocessFakeEmbedder(dim=4),
        "sparse_bm25": SparseBm25Embedder(tokenizer=WhitespaceTokenizer()),
    }
    kwargs.update(overrides)
    return EmbedStage(**kwargs)


# -------------------------------------------------------------------------------------------------
# sparse_bm25.py
# -------------------------------------------------------------------------------------------------


def test_tokens_to_sparse_bm25_matches_reference_saturation() -> None:
    tokens = ["한국", "정보", "한국"]  # "한국" repeats -> tf=2 at its hash index
    vector = tokens_to_sparse_bm25(tokens, vocab_id="whitespace:1.0:none")
    counts: dict[int, int] = {}
    for token in tokens:
        counts[bm25_index(token)] = counts.get(bm25_index(token), 0) + 1
    expected_indices = sorted(counts)
    expected_values = [
        round(saturate(float(counts[i]), 3.0, DEFAULT_AVGDL, BM25_K1, BM25_B), 6) for i in expected_indices
    ]
    assert [i.root for i in vector.indices] == expected_indices
    assert vector.values == expected_values
    assert vector.vocab_id == "whitespace:1.0:none"
    assert vector.name == "sparse_bm25"


def test_tokens_to_sparse_bm25_empty_tokens_yields_empty_not_none() -> None:
    vector = tokens_to_sparse_bm25([], vocab_id="whitespace:1.0:none")
    assert vector.indices == []
    assert vector.values == []


def test_sparse_bm25_space_id_matches_doc_recipe_and_is_hex64() -> None:
    space = sparse_bm25_space_id(analyzer_id="whitespace:1.0:none", dictionary_hash=hash_of("dict"))
    ct.Hex64(space)  # must not raise
    revision = sparse_bm25_revision(dictionary_hash=hash_of("dict"))
    expected = space_id_fn(
        model_id="rag_platform/sparse_bm25",
        revision=revision,
        dim=2**32,
        normalized=False,
        prompt_hash_value=hash_of("config", "{}"),
        quantization="none",
        vocab_id="whitespace:1.0:none",
    )
    assert space == expected


def test_sparse_bm25_space_id_changes_with_k1_b_avgdl_and_dictionary_hash() -> None:
    base = sparse_bm25_space_id(analyzer_id="whitespace:1.0:none", dictionary_hash=hash_of("dict"))
    assert base != sparse_bm25_space_id(analyzer_id="whitespace:1.0:none", dictionary_hash=hash_of("dict"), k1=1.5)
    assert base != sparse_bm25_space_id(analyzer_id="whitespace:1.0:none", dictionary_hash=hash_of("dict"), b=0.5)
    assert base != sparse_bm25_space_id(analyzer_id="whitespace:1.0:none", dictionary_hash=hash_of("dict"), avgdl=200)
    assert base != sparse_bm25_space_id(analyzer_id="whitespace:1.0:none", dictionary_hash=hash_of("other"))


def test_sparse_bm25_embedder_default_tokenizer_id_and_embed_documents() -> None:
    embedder = SparseBm25Embedder(tokenizer=WhitespaceTokenizer())
    assert embedder.plugin_id == PLUGIN_ID
    assert embedder.analyzer_id == "whitespace:1.0:none"
    vectors = embedder.embed_documents(["hello world", ""])
    assert vectors[0].vocab_id == "whitespace:1.0:none"
    assert vectors[1].indices == []


# -------------------------------------------------------------------------------------------------
# stage.py batching and cache-key helpers
# -------------------------------------------------------------------------------------------------


def test_plan_batches_orders_by_token_desc_then_chunk_id_asc() -> None:
    items = [("b", 10), ("a", 10), ("c", 5)]
    batches = plan_batches(items, batch_max_tokens=1000, batch_max_items=10)
    assert batches == [["a", "b", "c"]]  # tie (10==10) broken by chunk_id ascending, then the short one


def test_plan_batches_splits_on_token_and_item_caps() -> None:
    items = [("a", 6), ("b", 6), ("c", 6)]
    assert plan_batches(items, batch_max_tokens=10, batch_max_items=10) == [["a"], ["b"], ["c"]]
    items2 = [("a", 1), ("b", 1), ("c", 1)]
    assert plan_batches(items2, batch_max_tokens=1000, batch_max_items=2) == [["a", "b"], ["c"]]


def test_plan_batches_solo_over_tokens_gets_its_own_batch() -> None:
    items = [("big", 5000), ("small", 10)]
    batches = plan_batches(items, batch_max_tokens=8192, batch_max_items=32, solo_over_tokens=4096)
    assert batches == [["big"], ["small"]]


def test_embed_cache_key_is_deterministic_and_space_sensitive() -> None:
    key_a = embed_cache_key("space-a", "hello")
    key_b = embed_cache_key("space-b", "hello")
    assert key_a == embed_cache_key("space-a", "hello")
    assert key_a != key_b
    assert key_a == hash_of("embed", "space-a", "document", "hello")


# -------------------------------------------------------------------------------------------------
# EmbedStage.run
# -------------------------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_selects_level_0_and_2_and_excludes_level_1() -> None:
    inp = _enriched_chunk_set(
        {
            _LEAF_ID: _enrichment("leaf text", "leaf lexical"),
            _PARENT_ID: _enrichment("parent text", "parent lexical"),
            _SUMMARY_ID: _enrichment("summary text", "summary lexical"),
        }
    )
    ctx = _FakeCtx(enriched_ref=_enriched_ref(), chunk_set=_three_level_chunk_set())
    result = await _stage().run(inp, ctx)
    assert set(result.vectors) == {_LEAF_ID, _SUMMARY_ID}
    assert result.stats.vectors_total == 2


@pytest.mark.asyncio
async def test_run_dense_offsets_follow_target_order_and_are_l2_normalized() -> None:
    inp = _enriched_chunk_set(
        {
            _LEAF_ID: _enrichment("leaf text", "leaf lexical"),
            _SUMMARY_ID: _enrichment("summary text", "summary lexical"),
        }
    )
    chunk_set = _FakeChunkSet(
        chunks=[_FakeChunk(chunk_id=_LEAF_ID, level=0), _FakeChunk(chunk_id=_SUMMARY_ID, level=2)]
    )
    ctx = _FakeCtx(enriched_ref=_enriched_ref(), chunk_set=chunk_set)
    result = await _stage().run(inp, ctx)
    leaf_bundle = result.vectors[_LEAF_ID].root
    summary_bundle = result.vectors[_SUMMARY_ID].root
    assert leaf_bundle.dense.offset == 0
    assert summary_bundle.dense.offset == 1
    # dense values live in vectors_ref (npz-in-JSON placeholder), not in the bundle; recompute via the
    # embedder directly to check normalization (doc 12 sec 2.2 step 7 is re-verified inside run()).
    fake = InprocessFakeEmbedder(dim=4)
    for text in ("leaf text", "summary text"):
        vector = fake.embed_documents([text])[0]
        norm = sum(v * v for v in vector) ** 0.5
        assert abs(norm - 1.0) < 1e-4


@pytest.mark.asyncio
async def test_run_sparse_bm25_matches_index_text_tokenization() -> None:
    inp = _enriched_chunk_set({_LEAF_ID: _enrichment("embed body", "leaf lexical body")})
    chunk_set = _FakeChunkSet(chunks=[_FakeChunk(chunk_id=_LEAF_ID, level=0)])
    ctx = _FakeCtx(enriched_ref=_enriched_ref(), chunk_set=chunk_set)
    result = await _stage().run(inp, ctx)
    bundle = result.vectors[_LEAF_ID].root
    expected = tokens_to_sparse_bm25(
        WhitespaceTokenizer().tokenize("leaf lexical body"), vocab_id="whitespace:1.0:none"
    )
    assert [i.root for i in bundle.sparse_bm25.indices] == [i.root for i in expected.indices]
    assert bundle.sparse_bm25.values == expected.values
    assert bundle.sparse_learned is None


@pytest.mark.asyncio
async def test_run_embedding_space_ids_are_hex64_and_profile_hash_matches_formula() -> None:
    inp = _enriched_chunk_set({_LEAF_ID: _enrichment("leaf text", "leaf lexical")})
    chunk_set = _FakeChunkSet(chunks=[_FakeChunk(chunk_id=_LEAF_ID, level=0)])
    ctx = _FakeCtx(enriched_ref=_enriched_ref(), chunk_set=chunk_set)
    result = await _stage().run(inp, ctx)
    spaces = result.embedding_space_ids.root
    assert isinstance(spaces, ct.EmbeddingSpaceIds2)
    ct.Hex64(spaces.dense.root)
    ct.Hex64(spaces.sparse_bm25.root)
    expected_profile = hash_of(
        "spaces", *sorted([f"dense={spaces.dense.root}", f"sparse_bm25={spaces.sparse_bm25.root}"])
    )
    assert result.embedding_profile_hash.root == expected_profile


@pytest.mark.asyncio
async def test_run_truncates_overlong_embed_text_and_marks_degraded() -> None:
    config = EmbedStageConfig(max_input_tokens=5)
    inp = _enriched_chunk_set({_LEAF_ID: _enrichment("0123456789", "index text")})
    chunk_set = _FakeChunkSet(chunks=[_FakeChunk(chunk_id=_LEAF_ID, level=0)])
    ctx = _FakeCtx(enriched_ref=_enriched_ref(), chunk_set=chunk_set)
    result = await _stage(config=config).run(inp, ctx)
    bundle = result.vectors[_LEAF_ID].root
    assert bundle.truncated is True
    assert result.quality == ct.Quality.degraded
    assert any(w.code == ct.ErrorCodeCatalog.embed_token_overflow for w in result.warnings)
    assert result.stats.truncated_count == 1


@pytest.mark.asyncio
async def test_run_no_truncation_when_within_budget() -> None:
    inp = _enriched_chunk_set({_LEAF_ID: _enrichment("short", "index text")})
    chunk_set = _FakeChunkSet(chunks=[_FakeChunk(chunk_id=_LEAF_ID, level=0)])
    ctx = _FakeCtx(enriched_ref=_enriched_ref(), chunk_set=chunk_set)
    result = await _stage().run(inp, ctx)
    bundle = result.vectors[_LEAF_ID].root
    assert bundle.truncated is False
    assert result.quality == ct.Quality.full
    assert result.warnings == []


@pytest.mark.asyncio
async def test_run_prefers_ctx_analyzer_over_default_tokenizer() -> None:
    inp = _enriched_chunk_set({_LEAF_ID: _enrichment("embed", "hello world")})
    chunk_set = _FakeChunkSet(chunks=[_FakeChunk(chunk_id=_LEAF_ID, level=0)])
    ctx = _FakeCtx(enriched_ref=_enriched_ref(), chunk_set=chunk_set, analyzer=_FakeAnalyzer())
    stage = _stage()
    result = await stage.run(inp, ctx)
    expected_space = sparse_bm25_space_id(
        analyzer_id="fake-analyzer:1.0", dictionary_hash=stage._sparse_bm25.dictionary_hash
    )
    assert result.embedding_space_ids.root.sparse_bm25.root == expected_space
    bundle = result.vectors[_LEAF_ID].root
    assert bundle.sparse_bm25.vocab_id == "fake-analyzer:1.0"


@pytest.mark.asyncio
async def test_run_missing_enriched_ref_raises_contract_violation() -> None:
    inp = _enriched_chunk_set({_LEAF_ID: _enrichment("leaf text", "leaf lexical")})
    chunk_set = _FakeChunkSet(chunks=[_FakeChunk(chunk_id=_LEAF_ID, level=0)])
    ctx = _FakeCtx(enriched_ref=None, chunk_set=chunk_set)
    with pytest.raises(StageError) as exc_info:
        await _stage().run(inp, ctx)
    assert exc_info.value.code == "contract.violation"


@pytest.mark.asyncio
async def test_run_missing_chunk_set_lineage_raises_contract_violation() -> None:
    inp = _enriched_chunk_set({_LEAF_ID: _enrichment("leaf text", "leaf lexical")})
    ctx = _FakeCtx(enriched_ref=_enriched_ref(), chunk_set=None)
    with pytest.raises(StageError) as exc_info:
        await _stage().run(inp, ctx)
    assert exc_info.value.code == "contract.violation"


@pytest.mark.asyncio
async def test_run_cache_hits_defaults_to_zero_no_cache_backend_wired() -> None:
    """DEFERRED (WP-301 문서): 청크 임베딩 캐시 백엔드 미배선 — `cache_hits`는 항상 0."""
    inp = _enriched_chunk_set({_LEAF_ID: _enrichment("leaf text", "leaf lexical")})
    chunk_set = _FakeChunkSet(chunks=[_FakeChunk(chunk_id=_LEAF_ID, level=0)])
    ctx = _FakeCtx(enriched_ref=_enriched_ref(), chunk_set=chunk_set)
    result = await _stage().run(inp, ctx)
    assert result.cache_hits == 0


@pytest.mark.asyncio
async def test_run_lineage_refs_enriched_points_at_input_and_embedded_is_none() -> None:
    inp = _enriched_chunk_set({_LEAF_ID: _enrichment("leaf text", "leaf lexical")})
    chunk_set = _FakeChunkSet(chunks=[_FakeChunk(chunk_id=_LEAF_ID, level=0)])
    ctx = _FakeCtx(enriched_ref=_enriched_ref(), chunk_set=chunk_set)
    result = await _stage().run(inp, ctx)
    assert result.lineage_refs.enriched.blake3.root == _HEX64
    assert result.lineage_refs.embedded is None
    assert str(result.enriched_ref.uri.root) == "file:///enriched.json"


def test_capabilities_and_fingerprint_are_stable() -> None:
    stage = _stage()
    caps = stage.capabilities()
    assert caps.supports_resumable is False
    assert stage.fingerprint() == stage.fingerprint()
    other = _stage(config=EmbedStageConfig(max_input_tokens=1))
    assert stage.fingerprint() != other.fingerprint()
