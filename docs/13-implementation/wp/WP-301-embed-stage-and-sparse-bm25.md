---
title: "WP-301 embed-stage-and-sparse-bm25"
status: done
owner: implementation
---

# WP-301 embed-stage-and-sparse-bm25 (F3-01)

## 목표

`embed` 스테이지(바이블 §4.2 `embed` 행, ADR-0032 5멤버)를 `lite` 프로파일 범위로 구현한다:
`EnrichedChunkSet` → `EmbeddedChunkSet`. dense는 `sdk.ports.Embedder` 포트(기본
`InprocessFakeEmbedder`, 실 모델은 `needs_model`), sparse는 플랫폼 측 BM25(`embedder.sparse_bm25`,
`adapters/index/qdrant/bm25_sparse`의 토큰화·TF 포화 로직을 재사용)로 낸다. 대상 선별(level ∈
{0,2}), 토큰 기준 배치·절단, dense L2 정규화 재검증, `embedding_space_id`/`embedding_profile_hash`/
`embedder_fingerprint` 합성, 청크 캐시 키 함수(`H("embed", space, "document", embed_text)`)를
포함한다. `sparse_learned`(BGE-M3 단일 패스, `standard`)·실 서빙 캐시 백엔드·npz 실물 직렬화·
`ResumeCursor`/`partial_ref` 재개는 이 WP 범위 밖(DEFERRED, 아래 참조).

## 파일

- `src/rag_platform/adapters/embed/sparse_bm25.py` — `tokens_to_sparse_bm25(tokens, vocab_id, avgdl,
  k1, b) -> common_types.SparseBm25`(순수 함수, 해시 충돌 시 tf 합산 후 포화); `sparse_bm25_revision`/
  `sparse_bm25_space_id`(04-pipelines/12 §12.3 공간 입력 그대로); `SparseBm25Embedder` —
  `embedder.sparse_bm25` 플러그인 표면(기본 토크나이저 폴백, `ctx.analyzer` 있으면 스테이지가 대신
  그것을 쓴다).
- `src/rag_platform/adapters/embed/stage.py` — `EmbedStageConfig`(config_schema); `plan_batches`
  (04-pipelines/12 §6.1 배치 알고리즘 그대로, 순수 함수); `embed_cache_key`(§7 캐시 키 함수);
  `EmbedStage` — 5멤버(`plugin_id="embedder.pipeline"`/`config_schema`/`capabilities()`/
  `fingerprint()`/`run()`), `requires_lineage=("ChunkSet",)`.
- `tests/adapters/embed/test_embed_stage.py` — 위 두 모듈의 단위·통합 테스트.

## 시그니처

```python
# sparse_bm25.py
def tokens_to_sparse_bm25(
    tokens: Sequence[str], *, vocab_id: str, avgdl: float = DEFAULT_AVGDL, k1: float = BM25_K1, b: float = BM25_B
) -> common_types.SparseBm25: ...

def sparse_bm25_revision(*, k1: float = BM25_K1, b: float = BM25_B, avgdl: float = DEFAULT_AVGDL, dictionary_hash: str) -> str: ...
def sparse_bm25_space_id(*, analyzer_id: str, dictionary_hash: str, k1: float = BM25_K1, b: float = BM25_B, avgdl: float = DEFAULT_AVGDL) -> str: ...

class SparseBm25Embedder:
    plugin_id = "embedder.sparse_bm25"
    def __init__(self, *, tokenizer: SparseTokenizer | None = None, k1=BM25_K1, b=BM25_B, avgdl=DEFAULT_AVGDL, dictionary_hash: str | None = None) -> None: ...
    analyzer_id: str            # property, = tokenizer.analyzer_id
    embedding_space_id: str      # property, sparse_bm25_space_id(...)
    def tokenize(self, text: str) -> list[str]: ...
    def embed_documents(self, texts: list[str]) -> list[common_types.SparseBm25]: ...

# stage.py
class EmbedStageConfig(BaseModel):
    max_input_tokens: int = 8192
    batch_max_tokens: int = 8192
    batch_max_items: int = 32
    solo_over_tokens: int = 4096

def plan_batches(items: list[tuple[str, int]], *, batch_max_tokens: int, batch_max_items: int, solo_over_tokens: int = 4096) -> list[list[str]]: ...
def embed_cache_key(embedding_space_id: str, embed_text: str) -> str: ...

class EmbedStage:
    plugin_id = "embedder.pipeline"
    config_schema = EmbedStageConfig
    requires_lineage: tuple[str, ...] = ("ChunkSet",)
    def __init__(self, *, embedder: Embedder | None = None, sparse_bm25: SparseBm25Embedder | None = None, config: EmbedStageConfig | None = None) -> None: ...
    def capabilities(self) -> ct.Capabilities: ...
    def fingerprint(self) -> str: ...
    async def run(self, inp: EnrichedChunkSet, ctx: Any) -> EmbeddedChunkSet: ...
```

## 입출력 계약 발췌 (철자 정본)

- 입력 `enriched_chunk_set.EnrichedChunkSet{tenant_id, collection_id, quality, warnings,
  lineage_refs{source, parsed, normalized, chunk_set, enriched?, embedded?}, chunk_set_id,
  document_id, doc_version, enrichments: dict<chunk_id, common_types.Enrichment{embed_text,
  index_text, ...}>}`.
- 출력 `embedded_chunk_set.EmbeddedChunkSet{schema_version="1.0.0", schema_type="EmbeddedChunkSet",
  tenant_id, collection_id, producer, quality, warnings, created_at, lineage_refs{source, parsed,
  normalized, chunk_set, enriched(필수), embedded=None}, chunk_set_id, document_id, doc_version,
  enriched_ref: EnrichedRef, embedding_space_ids: common_types.EmbeddingSpaceIds({dense,
  sparse_bm25} — `EmbeddingSpaceIds2` 분기), embedding_profile_hash, embedder_fingerprint,
  mode="document"(const), pooling: common_types.Pooling, vectors_ref: ArtifactRef, vector_layout=None
  (이 WP 미구현, 아래 DEFERRED), vectors: dict<chunk_id, common_types.VectorBundle>, cache_hits: int,
  stats: EmbedStats{vectors_total, bytes_dense, bytes_sparse, bytes_late_interaction, truncated_count}}`.
- `common_types.VectorBundle = RootModel[VectorBundle1 | VectorBundle2]`; `lite`는 `VectorBundle2`
  (`dense: Dense{name:"dense", dim, offset}`(필수), `sparse_learned=None`, `sparse_bm25:
  SparseBm251{name:"sparse_bm25", vocab_id, indices[], values[]}`(필수), `embed_text_hash: Hex64`,
  `truncated: bool`).
- `common_types.EmbeddingSpaceIds2{dense: Hex64, sparse_learned?: Hex64, sparse_bm25: Hex64,
  late_interaction?: Hex64}`(lite 분기: sparse_bm25 필수, sparse_learned 없음).
- 해시 공식(바이블 §6.2, 04-pipelines/12 §2.1/§6.2/§9/§12.3): `embedding_space_id = H("space",
  model_id, revision, str(dim), str(normalized), prompt_hash, quantization, vocab_id or "")`;
  `embedding_profile_hash = H("spaces", *sorted(f"{name}={space_id}"))`; `embedder_fingerprint =
  H("embedder", plugin_id, plugin_version, config_hash, image_digest or "", embedding_profile_hash)`;
  `Stage.fingerprint() = H("producer", plugin_id, plugin_version, config_hash, image_digest or "",
  ",".join(model_ids))`; 청크 캐시 키 `H("embed", embedding_space_id, "document", embed_text)`;
  `lite` `sparse_bm25` 공간 입력(§12.3, 이 문서가 확정): `model_id="rag_platform/sparse_bm25"`,
  `revision=H("config", canonical_json({"k1":1.2,"b":0.75,"avgdl":400,"dictionary_hash":<hex64>}))`,
  `dim=4294967296`, `normalized=false`, `prompt_hash=H("config","{}")`, `quantization="none"`,
  `vocab_id=analyzer_id`.
- `embed.token_overflow`(§5.7 카탈로그, PARTIAL 분류) truncate 시 봉투 `quality=degraded` +
  `Warning{code, message, chunk_id}`(§4.2 embed 행 확정).
- `sdk.ports.Embedder{embedding_space_id: str, dim: int, normalized: bool, embed_documents(texts)
  -> list[list[float]], embed_query(text) -> list[float]}`(dense 전용, 04-pipelines/12 §2.1의
  더 넓은 제안 포트가 아니라 실제 배선된 최소 포트 — 미해결 이슈, 아래 참조).

## 불변식·금지

- 대상 선별은 `common_types.ChunkLevel ∈ {0, 2}`만(레벨 1 부모 제외, `Chunk` 불변식 (5), 07 V-4);
  `ctx.lineage["ChunkSet"]`(`requires_lineage=("ChunkSet",)`)가 없으면 `contract.violation`.
- dense 벡터는 항상 재검증한다(`adapters.embed.assert_l2_normalized`, ‖v‖₂=1±1e-4) — 임베더가
  이미 정규화했다고 신뢰하지 않는다(§2.2 7단계).
- `sparse_bm25`의 입력은 `index_text`이지 `embed_text`가 아니다(§12 표 "책임 경계"). `ctx.analyzer`가
  있으면 그 토크나이저를 쓰고 `SparseBm25Embedder`의 내장 토크나이저는 하네스 폴백일 뿐이다(§12.3
  "token은 ctx.analyzer가 낸 형태소").
- `adapters`는 `storage`/`security`를 import하지 않는다. `qdrant/bm25_sparse.py`는 손대지 않고
  공개 심볼(`bm25_index`/`saturate`/`default_tokenizer`/토크나이저 클래스/상수)만 재사용한다 —
  BM25 산술은 한 곳(그 모듈)에만 있고 이 파일은 계약 조립(`SparseBm25`/공간 ID)만 더한다.
  (04-pipelines/12 §9(2)가 "SDK 단일 구현"을 제안하지만 `sdk/`로 옮기는 것은 공용 파일 변경이라
  이 WP 범위 밖 — open_issues.)
- `StageError` 코드는 §5.7 철자만(`contract.violation`). 커밋·이모지 금지.

## 단계

1. `ctx.enriched_ref`(WP-106 `ctx.parsed_ref`와 같은 임시 관례 — 이 스테이지 자기 입력 참조) +
   `ctx.lineage["ChunkSet"]`를 읽어 대상 `chunk_id` 목록(level ∈ {0,2} ∧ `inp.enrichments`에 존재)을
   만든다.
2. 각 대상 청크의 `embed_text`를 `ctx.token_counter`로 `max_input_tokens` 초과 시 꼬리 절단(문자
   길이 이분 탐색 — 토크나이저가 접두 단조롭다는 가정; 문장 경계 후퇴는 DEFERRED)하고
   `truncated`/`Warning`을 기록한다. `index_text`는 절단하지 않는다.
3. `plan_batches`(§6.1 그대로)로 토큰 내림차순 배치를 만들고 `self._embedder.embed_documents(batch)`를
   순서대로 호출 → 재정규화·재검증.
4. `ctx.analyzer`(있으면) 또는 `self._sparse_bm25`의 폴백 토크나이저로 `index_text`를 토큰화 →
   `tokens_to_sparse_bm25`로 `SparseBm251` 조립.
5. `embedding_space_ids`(dense: 임베더 자체 ID가 이미 `Hex64`면 그대로, 아니면(`FakeEmbedder`처럼
   플레이스홀더 문자열이면) `space_id(model_id=f"rag_platform/{cls}", revision=raw_id, dim,
   normalized, prompt_hash="{}"해시, quantization="none")`로 유효 `Hex64`를 만든다; sparse_bm25:
   `sparse_bm25_space_id`) → `embedding_profile_hash` → `embedder_fingerprint`.
6. `vectors_ref`는 dense 행렬을 JSON 파생물로 `ctx.artifacts.put_derived(kind="vectors", ext="json",
   media_type="application/vnd.rag.embedded-vectors+json")`에 저장(오프셋 = 정렬된 대상 청크 순번) —
   실 npz/parquet 직렬화는 DEFERRED(아래).
7. `VectorBundle2` 조립(`dense{offset}` + `sparse_bm25`) → `stats`(바이트 계량) → 봉투 `quality`
   (`degraded` ⇔ 입력이 이미 degraded 이거나 경고 있음) → `EmbeddedChunkSet` 반환.

## 테스트(파일·케이스)

`tests/adapters/embed/test_embed_stage.py`:
- `sparse_bm25`: (1) `tokens_to_sparse_bm25`가 해시 충돌 시 tf 합산 후 포화(참조 `saturate()` 직접
  호출과 일치, 오차 0). (2) 빈 토큰 목록 → 빈 `indices`/`values`(아직 필수 필드라 `None` 대신 빈
  벡터). (3) `sparse_bm25_space_id`가 §12.3 레시피(`model_id`/`dim=2**32`/`normalized=False`)와
  일치하고 `Hex64` 유효. (4) `SparseBm25Embedder` 기본 토크나이저 = `WhitespaceTokenizer`(kiwipiepy
  미설치 환경 가정), `dictionary_hash`/`k1`/`b`/`avgdl` 변경이 공간 ID를 바꾼다.
- `EmbedStage.run`: (1) level 1 부모 제외, level 0·2만 `vectors` 키. (2) 각 번들의 `dense.offset`이
  청크 순서와 일치, `sparse_bm25`가 `index_text` 기반(직접 계산한 기대값과 동일). (3) dense 벡터
  ‖v‖₂=1±1e-4. (4) `embedding_space_ids`(dense·sparse_bm25) 둘 다 `Hex64` 유효 +
  `embedding_profile_hash`가 정의식과 일치. (5) `max_input_tokens`보다 긴 `embed_text` → `truncated
  =True` + `embed.token_overflow` 경고 + 봉투 `quality=degraded`. (6) `ctx.analyzer` 주입 시 그
  `analyzer_id`가 `sparse_bm25` 공간 ID에 반영(기본 토크나이저와 다른 ID). (7) `ctx.enriched_ref`
  누락 → `contract.violation`. (8) `ctx.lineage["ChunkSet"]` 누락 → `contract.violation`.
  (9) `cache_hits == 0`(캐시 백엔드 미배선, DEFERRED 문서화). (10) `plan_batches` 단위 테스트 —
  토큰 내림차순 정렬, `solo_over_tokens` 초과 단독 배치, `batch_max_tokens`/`batch_max_items` 상한.

## 완료 기준

`uv run pytest -q tests/adapters/embed/test_embed_stage.py` 전부 통과, `uv run ruff check
src/rag_platform/adapters/embed/stage.py src/rag_platform/adapters/embed/sparse_bm25.py
tests/adapters/embed/test_embed_stage.py` 통과. mypy는 배치 검증자가 별도 실행.

## 검증 계층·DEFERRED

1층(여기서 검증) — 순수 함수 + `FakeEmbedder`/`WhitespaceTokenizer`(외부 자원 없음). `needs_docker`/
`needs_gpu`/`needs_network` 해당 없음.

- DEFERRED: `needs_model` — 실 BGE-M3/TEI/vLLM dense·`sparse_learned`(`standard`/`premium`) 조합,
  동등성 게이트(§11.3), 실 Kiwi 형태소 경로의 `sparse_bm25`(이 WP는 `kiwipiepy` 미설치 가정의
  `WhitespaceTokenizer` 폴백만 검증) — `docs/12-appendix/09-deferred-verification-ledger.md`.
- DEFERRED: `vectors_ref` 실 npz/parquet 직렬화 + `vector_layout` 조립. 이 WP는 `numpy`를 새
  의존성으로 추가하지 않고(작업 지시 "명시된 패키지만") dense 행렬을 JSON 파생물로 대신 저장한다 —
  오프셋 의미론은 동일하되 포맷은 계약 설명("npz 또는 parquet")과 다르다(open_issues).
- DEFERRED: 청크 임베딩 캐시 백엔드(§7) — `embed_cache_key()` 함수만 있고 실제 조회·기록·Valkey
  색인은 없다(`cache_hits`는 항상 0). `ResumeCursor`/`partial_ref`(§6.3) 재개도 미구현
  (`capabilities().supports_resumable=False`로 정직하게 신고).
- DEFERRED: 절단(§2.4)은 문장 경계 후퇴 없이 토큰 이분 탐색 꼬리 절단만 구현(단조성 가정).
- DEFERRED: `sparse_learned`(BGE-M3 단일 패스)·`late_interaction`·`ko-quality` SparseEncoder 슬롯 —
  이 WP는 `lite`(dense-fake + sparse_bm25)만.
- 해소(F3 배치 검증, 2026-09-23): `ctx.enriched_ref`(WP-106 `ctx.parsed_ref`와 같은 임시 관례) 부재
  open_issue는 `sdk/context.py`의 `StageContext`/`_LocalStageContext`에 범용 선택 필드
  `own_input_ref`를 공식 추가해 문서화·타입화했다(`adapters/embed/stage.py`의 `getattr(ctx,
  "enriched_ref", None)` 호출부는 하위 호환을 위해 그대로 두었다 — 동작 변경 없음).

## 결과: 통과 21 / xfail 0 / DEFERRED 5
