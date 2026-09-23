"""`embedder.pipeline` 스테이지 — `EnrichedChunkSet`를 `EmbeddedChunkSet`로 만든다(F3-01, WP-301).

역할: dense(`sdk.ports.Embedder` 포트, 기본 `InprocessFakeEmbedder`)와 sparse(`embedder.sparse_bm25`,
`lite` 프로파일)를 한 번에 팬아웃하는 합성 스테이지(04-pipelines/12 §9(2) "슬롯별 다른 플러그인 →
플랫폼 소유 합성 스테이지 `embedder.pipeline`"). 대상 선별(level ∈ {0,2}), 토큰 절단·배치, dense L2
재검증, `embedding_space_id`/`embedding_profile_hash`/`embedder_fingerprint` 조립까지 이 파일이 맡는다.
설계 근거: 바이블 §4.1(5멤버 스테이지 프로토콜)·§4.2 `embed` 행·§5.4 `EmbeddedChunkSet`/`VectorBundle`
표(ADR-0032); 04-pipelines/12 §2.2(`EmbedderStageBase.run` 10단계, 이 WP는 1·2(부분)·4·5·6·7·9·10만
구현)·§6.1(배치 알고리즘)·§7(캐시 키 식)·§9(named vectors 합성)·§12(sparse 책임 경계).
구성: `EmbedStageConfig` — `config_schema`; `plan_batches` — §6.1 배치 계획(순수 함수); `embed_cache_key`
— §7 캐시 키; `EmbedStage` — 5멤버(`plugin_id="embedder.pipeline"`/`config_schema`/`capabilities()`/
`fingerprint()`/`run()`), `requires_lineage=("ChunkSet",)`.
불변식·주의: level=1(부모)은 절대 임베딩하지 않는다. `sparse_bm25` 입력은 `index_text`(embed_text 아님).
dense는 재정규화 후에도 반드시 `assert_l2_normalized`로 재검증한다. `ctx.enriched_ref`는 WP-106
`ctx.parsed_ref`와 같은 임시 관례(설계 갭, open_issues)다. `adapters`는 `storage`/`security`를 import하지
않는다. `StageError` 코드는 §5.7 철자만.
검증 계층: 1층(여기서 검증) — `tests/adapters/embed/test_embed_stage.py`. `needs_model`: 실 BGE-M3/TEI/
vLLM dense·`sparse_learned` 조합은 DEFERRED(WP 문서 참조). `vectors_ref` 실 npz 직렬화·청크 임베딩
캐시 백엔드·`ResumeCursor` 재개도 DEFERRED(numpy 미도입 결정 포함, WP 문서 참조).
"""

from __future__ import annotations

import json
import re
from datetime import UTC
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict

from rag_platform.adapters.embed import assert_l2_normalized, l2_normalize, space_id
from rag_platform.adapters.embed.inprocess_fake import InprocessFakeEmbedder
from rag_platform.adapters.embed.sparse_bm25 import SparseBm25Embedder, sparse_bm25_space_id, tokens_to_sparse_bm25
from rag_platform.contracts import common_types as ct
from rag_platform.contracts.embedded_chunk_set import EmbeddedChunkSet, EmbedStats, EnrichedRef, LineageRefs, Source
from rag_platform.sdk.hashing import blake3_hex, hash_of
from rag_platform.sdk.stage import StageError

if TYPE_CHECKING:
    from datetime import datetime

    from rag_platform.contracts.enriched_chunk_set import EnrichedChunkSet
    from rag_platform.sdk.ports import Embedder, TokenCounter

__all__ = ["EmbedStage", "EmbedStageConfig", "embed_cache_key", "plan_batches"]

PLUGIN_VERSION = "0.1.0"
_CONTRACT_VIOLATION = "contract.violation"
_TARGET_LEVELS = frozenset({0, 2})  # bible sec 5.4 Chunk invariant (5): level=1 parents are not embedded
_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
_EMPTY_PROMPT_HASH = hash_of("config", "{}")
_BYTES_PER_DENSE_VALUE = 4  # vectors_ref default dtype float32 (doc 12 sec 8.3, VectorLayout.dense.dtype)
_BYTES_PER_SPARSE_ENTRY = 8  # indices(4B) + values(4B), EmbedStats.bytes_sparse docstring


class EmbedStageConfig(BaseModel):
    """`embedder.pipeline`의 설정 스키마 — `config_hash` → `fingerprint()` 입력(바이블 §6.2).

    doc 12 sec 6.1/6.2의 배치 초안 목표(`lite`: 배치 토큰 8,192·항목 32·단독 배치 임계 4,096)와
    sec 2.4의 절단 상한(`lite` 8,192 토큰)을 기본값으로 둔다.
    """

    model_config = ConfigDict(extra="forbid")

    max_input_tokens: int = 8192
    batch_max_tokens: int = 8192
    batch_max_items: int = 32
    solo_over_tokens: int = 4096


def plan_batches(
    items: list[tuple[str, int]], *, batch_max_tokens: int, batch_max_items: int, solo_over_tokens: int = 4096
) -> list[list[str]]:
    """Doc 12 sec 6.1 배치 계획 알고리즘 그대로(순수 함수, 같은 입력이면 같은 계획).

    `items`를 토큰 수 내림차순(동률은 `chunk_id` 오름차순, 결정성)으로 정렬한 뒤 그리디로 채운다.
    `solo_over_tokens`를 넘는 항목은 단독 배치(어텐션 활성화 제곱 증가 보호).

    Args:
        items: `(chunk_id, tokens_after_truncation)` 목록.
        batch_max_tokens: 배치 하나의 토큰 합 상한.
        batch_max_items: 배치 하나의 항목 수 상한.
        solo_over_tokens: 이 토큰 수를 넘는 항목은 항상 단독 배치.

    Returns:
        `chunk_id` 목록의 목록(각 원소가 배치 하나).
    """
    ordered = sorted(items, key=lambda it: (-it[1], it[0]))
    batches: list[list[str]] = []
    cur: list[str] = []
    cur_tokens = 0
    for chunk_id, tokens in ordered:
        if tokens > solo_over_tokens:
            batches.append([chunk_id])
            continue
        if cur and (cur_tokens + tokens > batch_max_tokens or len(cur) >= batch_max_items):
            batches.append(cur)
            cur, cur_tokens = [], 0
        cur.append(chunk_id)
        cur_tokens += tokens
    if cur:
        batches.append(cur)
    return batches


def embed_cache_key(embedding_space_id: str, embed_text: str) -> str:
    """청크 임베딩 캐시 키(바이블 §6.2, doc 12 sec 7): `H("embed", embedding_space_id, "document", embed_text)`.

    이 WP는 캐시 백엔드를 배선하지 않는다(DEFERRED, WP 문서 참조) — 이 함수는 미래의 캐시 조회·기록이
    쓸 결정적 키만 낸다.
    """
    return hash_of("embed", embedding_space_id, "document", embed_text)


def _rfc3339_ms(moment: datetime) -> str:
    utc = moment.astimezone(UTC)
    return utc.strftime("%Y-%m-%dT%H:%M:%S.") + f"{utc.microsecond // 1000:03d}Z"


def _chunk_id_str(value: Any) -> str:
    """`Hex64`(RootModel) 또는 평범한 `str` 어느 쪽이든 청크 ID 문자열을 뽑는다(테스트 이중 대비)."""
    root = getattr(value, "root", None)
    return root if isinstance(root, str) else str(value)


def _resolve_enriched_ref(ctx: Any, plugin_id: str) -> EnrichedRef:
    """`ctx.enriched_ref`(이 스테이지 입력 `EnrichedChunkSet`의 산출물 참조)를 읽는다.

    `StageContext`(sdk/context.py)에는 아직 이 멤버가 없다 — normalize의 `ctx.parsed_ref`/parse의
    `ctx.source_bytes`와 같은 임시 관례를 따라 포트 부재를 `contract.violation`으로 올린다(WP-106과
    같은 open issue, 공용 파일 변경 없이 방어적으로 처리).
    """
    ref = getattr(ctx, "enriched_ref", None)
    if ref is None:
        detail = (
            "StageContext has no enriched_ref port (same WP-106 design gap: no ctx convention yet "
            "for a stage's own input ArtifactRef; cf. normalize's ctx.parsed_ref precedent)"
        )
        raise StageError(_CONTRACT_VIOLATION, stage="embed", plugin_id=plugin_id, detail=detail)
    if isinstance(ref, EnrichedRef):
        return ref
    if hasattr(ref, "model_dump"):
        return EnrichedRef.model_validate(ref.model_dump(mode="json"))
    return EnrichedRef.model_validate(ref)


def _resolve_chunk_levels(ctx: Any, plugin_id: str) -> dict[str, int]:
    """`ctx.lineage["ChunkSet"]`에서 `chunk_id -> level` 맵을 만든다(doc 12 sec 2.2 step 1 대상 선별).

    `requires_lineage=("ChunkSet",)`가 선언하는 바로 그 산출물이며, `EnrichedChunkSet.enrichments`에는
    `level`이 없어 이 조회가 필요하다(doc 12 sec 2.2 step 1).
    """
    lineage = getattr(ctx, "lineage", None) or {}
    chunk_set = lineage.get("ChunkSet")
    if chunk_set is None:
        detail = "ctx.lineage['ChunkSet'] missing (doc 12 sec 2.2 step 1 requires_lineage=('ChunkSet',))"
        raise StageError(_CONTRACT_VIOLATION, stage="embed", plugin_id=plugin_id, detail=detail)
    return {_chunk_id_str(chunk.chunk_id): int(chunk.level) for chunk in chunk_set.chunks}


def _truncate(text: str, max_tokens: int, token_counter: TokenCounter) -> tuple[str, bool]:
    """`text`가 `max_tokens`를 넘으면 꼬리를 잘라 문자 길이 이분 탐색으로 절단한다(doc 12 sec 2.4).

    `TokenCounter`는 개수(`count`)만 내고 인코딩 위치를 주지 않으므로, 접두 길이에 대해 토큰 수가
    단조 비감소라는(거의 모든 서브워드 토크나이저에 성립하는) 가정으로 이분 탐색한다. 문장 경계
    후퇴(doc 12 sec 2.4 "단위" 행)는 이 WP 범위 밖(DEFERRED, WP 문서 참조) — 토큰 경계에서 멈춘다.

    Returns:
        `(가능하면 원문 그대로, else 잘린 텍스트, truncated 여부)`.
    """
    if token_counter.count(text) <= max_tokens:
        return text, False
    lo, hi = 0, len(text)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if token_counter.count(text[:mid]) <= max_tokens:
            lo = mid
        else:
            hi = mid - 1
    return text[:lo], True


def _as_artifact_ref(ref: Any) -> ct.ArtifactRef:
    """`EnrichedRef`(자기 참조 로컬 타입) → `common_types.ArtifactRef`(embedded의 `lineage_refs.enriched`)."""
    return ct.ArtifactRef(
        uri=ref.uri,
        blake3=ref.blake3,
        media_type=ref.media_type,
        schema_type=ct.SchemaTypeName(ref.schema_type),
        schema_version=ref.schema_version,
        size_bytes=ref.size_bytes,
        stage_key=ref.stage_key,
    )


def _as_embedded_source(ref: Any) -> Source:
    """`EnrichedChunkSet.lineage_refs.source`(같은 필드 모양의 로컬 타입) → embedded 쪽 `Source`."""
    return Source(
        uri=ref.uri,
        blake3=ref.blake3,
        media_type=ref.media_type,
        schema_type=ref.schema_type,
        schema_version=ref.schema_version,
        size_bytes=ref.size_bytes,
        stage_key=ref.stage_key,
    )


def _to_bundle_sparse_bm25(vector: ct.SparseBm25) -> ct.SparseBm251:
    """`common_types.SparseBm25`(공용 반환 타입) → `VectorBundle2.sparse_bm25`가 요구하는 `SparseBm251`.

    두 클래스는 스키마 `$defs` 중복 생성으로 이름만 다를 뿐 필드가 같다(둘 다
    `{name, vocab_id, indices, values}`) — 계약 손편집 없이 값만 옮겨 담는다.
    """
    return ct.SparseBm251(name="sparse_bm25", vocab_id=vector.vocab_id, indices=vector.indices, values=vector.values)


class EmbedStage:
    """`embedder.pipeline` — dense(`Embedder` 포트) + `sparse_bm25` 합성 embed 스테이지(F3-01, WP-301)."""

    plugin_id = "embedder.pipeline"
    config_schema = EmbedStageConfig
    requires_lineage: tuple[str, ...] = ("ChunkSet",)

    def __init__(
        self,
        *,
        embedder: Embedder | None = None,
        sparse_bm25: SparseBm25Embedder | None = None,
        config: EmbedStageConfig | None = None,
    ) -> None:
        """Dense 임베더(기본 `InprocessFakeEmbedder`)와 sparse_bm25 계산기(기본값 새로 생성)를 고정한다."""
        self.config = config or EmbedStageConfig()
        self._embedder: Embedder = embedder or InprocessFakeEmbedder()
        self._sparse_bm25 = sparse_bm25 or SparseBm25Embedder()

    def config_hash(self) -> str:
        """`H("config", canonical_json(config))`(바이블 §6.2 근사, normalize/fetch와 같은 관례)."""
        canonical = json.dumps(
            self.config.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), ensure_ascii=False
        )
        return hash_of("config", canonical)

    def capabilities(self) -> ct.Capabilities:
        """`isolation_modes=[in_process]`(`lite`), 재개 미구현(DEFERRED), GPU 불필요(FakeEmbedder)."""
        return ct.Capabilities(
            isolation_modes=[ct.IsolationMode.in_process],
            supports_resumable=False,
            contracts_compat=ct.ContractsCompat(">=1.0,<2.0"),
            input_formats=[],
            requires_gpu=False,
        )

    def fingerprint(self) -> str:
        """`H("producer", plugin_id, plugin_version, config_hash, "", ",".join(model_ids))`.

        `sdk.ports.Embedder`(dense 전용 최소 포트)는 `model_id`/`revision`을 노출하지 않아
        `model_ids`는 항상 빈 목록이다(open issue, WP 문서 참조) — 인프로세스(`image_digest=None`)와
        합쳐 `""`이 된다.
        """
        return hash_of("producer", self.plugin_id, PLUGIN_VERSION, self.config_hash(), "", "")

    def _dense_space_id(self) -> str:
        """Dense 채널의 `embedding_space_id`.

        실 서빙 어댑터(`tei_dense`/`vllm_pooling_bge_m3`)는 이미 `space_id()`로 계산한 유효 `Hex64`를
        `embedding_space_id`에 담아 온다 — 그대로 쓴다. 하네스 `InprocessFakeEmbedder`처럼 플레이스홀더
        문자열("fake:sha256-hash")을 낼 때만, 그 라벨을 `revision` 자리에 넣어 스테이지가 유효한
        `Hex64`를 합성한다(dev 전용 관례; 실 모델 공간과 절대 충돌하지 않도록 `model_id`에 클래스명을
        박아 넣는다).
        """
        raw = self._embedder.embedding_space_id
        if _HEX64_RE.fullmatch(raw):
            return raw
        return space_id(
            model_id=f"rag_platform/{type(self._embedder).__name__}",
            revision=raw,
            dim=self._embedder.dim,
            normalized=self._embedder.normalized,
            prompt_hash_value=_EMPTY_PROMPT_HASH,
            quantization="none",
        )

    async def run(self, inp: EnrichedChunkSet, ctx: Any) -> EmbeddedChunkSet:
        """`EnrichedChunkSet` → `EmbeddedChunkSet`(doc 12 sec 2.2 step 1·2(부분)·4·5·6·7·9·10)."""
        enriched_ref = _resolve_enriched_ref(ctx, self.plugin_id)
        chunk_levels = _resolve_chunk_levels(ctx, self.plugin_id)
        target_ids = [
            chunk_id
            for chunk_id, level in chunk_levels.items()
            if level in _TARGET_LEVELS and chunk_id in inp.enrichments
        ]

        analyzer = getattr(ctx, "analyzer", None)
        tokenizer = analyzer if analyzer is not None else self._sparse_bm25
        analyzer_id = tokenizer.analyzer_id

        token_counter: TokenCounter = ctx.token_counter
        embed_texts: dict[str, str] = {}
        index_texts: dict[str, str] = {}
        truncated_flags: dict[str, bool] = {}
        warnings: list[ct.Warning] = []
        for chunk_id in target_ids:
            enrichment = inp.enrichments[chunk_id]
            text, truncated = _truncate(enrichment.embed_text, self.config.max_input_tokens, token_counter)
            embed_texts[chunk_id] = text
            index_texts[chunk_id] = enrichment.index_text
            truncated_flags[chunk_id] = truncated
            if truncated:
                detail = f"embed_text exceeded max_input_tokens={self.config.max_input_tokens}; tail truncated"
                warnings.append(
                    ct.Warning(
                        code=ct.ErrorCodeCatalog.embed_token_overflow,
                        message=detail,
                        chunk_id=ct.Hex64(chunk_id),
                    )
                )

        items = [(chunk_id, token_counter.count(embed_texts[chunk_id])) for chunk_id in target_ids]
        batches = plan_batches(
            items,
            batch_max_tokens=self.config.batch_max_tokens,
            batch_max_items=self.config.batch_max_items,
            solo_over_tokens=self.config.solo_over_tokens,
        )

        dense_by_chunk: dict[str, list[float]] = {}
        for batch in batches:
            batch_dense_vectors = self._embedder.embed_documents([embed_texts[chunk_id] for chunk_id in batch])
            for chunk_id, vector in zip(batch, batch_dense_vectors, strict=True):
                normalized = vector if self._embedder.normalized else l2_normalize(vector)
                assert_l2_normalized(normalized, plugin_id=self.plugin_id)
                dense_by_chunk[chunk_id] = normalized

        sparse_by_chunk: dict[str, ct.SparseBm25] = {
            chunk_id: tokens_to_sparse_bm25(
                tokenizer.tokenize(index_texts[chunk_id]),
                vocab_id=analyzer_id,
                avgdl=self._sparse_bm25.avgdl,
                k1=self._sparse_bm25.k1,
                b=self._sparse_bm25.b,
            )
            for chunk_id in target_ids
        }

        dense_space = self._dense_space_id()
        sparse_space = sparse_bm25_space_id(
            analyzer_id=analyzer_id,
            dictionary_hash=self._sparse_bm25.dictionary_hash,
            k1=self._sparse_bm25.k1,
            b=self._sparse_bm25.b,
            avgdl=self._sparse_bm25.avgdl,
        )
        embedding_space_id_strs = {"dense": dense_space, "sparse_bm25": sparse_space}
        embedding_space_ids = ct.EmbeddingSpaceIds(
            ct.EmbeddingSpaceIds2(dense=ct.Hex64(dense_space), sparse_bm25=ct.Hex64(sparse_space))
        )
        space_parts = sorted(f"{name}={sid}" for name, sid in embedding_space_id_strs.items())
        embedding_profile_hash = hash_of("spaces", *space_parts)
        embedder_fingerprint = hash_of(
            "embedder", self.plugin_id, PLUGIN_VERSION, self.config_hash(), "", embedding_profile_hash
        )

        # DEFERRED: 실 npz/parquet 직렬화(numpy 미도입 결정, WP 문서 참조) — 오프셋 의미론은 같은 JSON 파생물.
        dense_rows = [dense_by_chunk[chunk_id] for chunk_id in target_ids]
        vectors_payload = json.dumps({"dense": dense_rows}, separators=(",", ":")).encode("utf-8")
        vectors_ref = await ctx.artifacts.put_derived(
            vectors_payload, kind="vectors", ext="json", media_type="application/vnd.rag.embedded-vectors+json"
        )

        vectors: dict[str, ct.VectorBundle] = {}
        bytes_dense = 0
        bytes_sparse = 0
        for offset, chunk_id in enumerate(target_ids):
            dense_vector = dense_by_chunk[chunk_id]
            bytes_dense += len(dense_vector) * _BYTES_PER_DENSE_VALUE
            sparse_vector = sparse_by_chunk[chunk_id]
            bytes_sparse += len(sparse_vector.indices) * _BYTES_PER_SPARSE_ENTRY
            bundle = ct.VectorBundle2(
                dense=ct.Dense(name="dense", dim=len(dense_vector), offset=offset),
                sparse_learned=None,
                sparse_bm25=_to_bundle_sparse_bm25(sparse_vector),
                late_interaction=None,
                page_multivector=None,
                pooled_page_multivector=None,
                page_dense=None,
                embed_text_hash=blake3_hex(embed_texts[chunk_id]),
                truncated=truncated_flags[chunk_id],
            )
            vectors[chunk_id] = ct.VectorBundle(bundle)

        quality = ct.Quality.degraded if inp.quality == ct.Quality.degraded or warnings else ct.Quality.full
        lineage_refs = LineageRefs(
            source=_as_embedded_source(inp.lineage_refs.source),
            parsed=inp.lineage_refs.parsed,
            normalized=inp.lineage_refs.normalized,
            chunk_set=inp.lineage_refs.chunk_set,
            enriched=_as_artifact_ref(enriched_ref),
            embedded=None,
        )

        return EmbeddedChunkSet(
            schema_version="1.0.0",
            schema_type="EmbeddedChunkSet",
            tenant_id=inp.tenant_id,
            collection_id=inp.collection_id,
            producer=ct.Producer(
                plugin_id=self.plugin_id,
                plugin_version=PLUGIN_VERSION,
                config_hash=self.config_hash(),
                image_digest=None,
                model_ids=None,
            ),
            quality=quality,
            warnings=warnings,
            created_at=_rfc3339_ms(ctx.now()),
            lineage_refs=lineage_refs,
            chunk_set_id=inp.chunk_set_id,
            document_id=inp.document_id,
            doc_version=inp.doc_version,
            enriched_ref=enriched_ref,
            embedding_space_ids=embedding_space_ids,
            embedding_profile_hash=embedding_profile_hash,
            embedder_fingerprint=embedder_fingerprint,
            mode="document",
            pooling=ct.Pooling.cls,
            vectors_ref=vectors_ref,
            vector_layout=None,
            vectors=vectors,
            cache_hits=0,
            stats=EmbedStats(
                vectors_total=len(vectors),
                bytes_dense=bytes_dense,
                bytes_sparse=bytes_sparse,
                bytes_late_interaction=0,
                truncated_count=sum(truncated_flags.values()),
            ),
        )
