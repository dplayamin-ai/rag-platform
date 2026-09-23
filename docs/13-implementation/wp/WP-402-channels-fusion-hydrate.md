---
title: "WP-402 channels-fusion-hydrate"
status: done
owner: implementation
---

# WP-402 channels-fusion-hydrate (F4-02)

## 목표

검색 경로의 세 단계를 `lite` 프로파일 범위로 구현한다: (1) `retrieve` 코디네이터 —
`QueryPlan.channels[] x rewritten_queries[]`를 곱집합으로 펼친 런을 `asyncio`로 병렬 실행해
`CandidateSet`을 만든다(세마포어 32, 런별 타임아웃, 부분 실패는 `degraded[]`, 전 채널 실패는
`retrieve.unavailable`). (2) `fuse` — RRF(`k=60`, 채널 가중 1:1:1, 변형 0.5)로 `CandidateSet`을
`RankedSet(stage=fused, hydrated=false)`로 바꾼다(`Σcontribution = fused` 불변식,
`testing/fuser_equivalence` 골든 동치). (3) `hydrate` 서브스텝 — 상위 `hydrate.top_n`의 payload를
벡터 백엔드에서 1회 배치 조회해 `hydrated=true`로 바꾼다(누락은 `partial_result`). 두 `retriever`
어댑터(`qdrant_dense`, `qdrant_sparse_bm25`)도 이 WP에서 구현한다. 결과 캐시는 어디서도 하지 않는다
(ACL 시점성).

## 파일

- `src/rag_platform/retrieval/channels.py` — `QueryVectors`/`ChannelRunInput`(SDK 내부 타입, 계약
  아님)·`Retriever` 프로토콜·`PAYLOAD_SLIM_KEYS`·`run_one`·`retrieve_once`.
- `src/rag_platform/retrieval/fusion.py` — `fuse_ranks`(§8.1 "단순화된 어댑터 형태", 골든 동치성
  검사에 직결)·`fuse`(`CandidateSet` -> `RankedSet(fused)`)·`RrfFuser`(Stage 5멤버 래퍼).
- `src/rag_platform/retrieval/hydrate.py` — `HYDRATE_PAYLOAD_KEYS`·`HydrateBackend` 프로토콜·
  `QdrantHydrateBackend`·`hydrate`.
- `src/rag_platform/adapters/retrieve/qdrant_dense.py` — `retriever.qdrant_dense`.
- `src/rag_platform/adapters/retrieve/qdrant_sparse_bm25.py` — `retriever.qdrant_sparse_bm25`
  (`channel=lexical`, `lite`).
- `tests/retrieval/test_fusion_channels.py` — 위 다섯 모듈의 단위·통합 테스트.

## 시그니처

```python
# channels.py
@dataclass(frozen=True, slots=True)
class QueryVectors:
    dense: tuple[float, ...] | None = None
    sparse_learned: SparseVector | None = None
    sparse_bm25: SparseVector | None = None
    late_interaction: tuple[tuple[float, ...], ...] | None = None

@dataclass(frozen=True, slots=True)
class ChannelRunInput:
    channel: ChannelPlan
    variant: RewrittenQuery
    query_vectors: QueryVectors
    query_text: str                    # 결정적 토큰화 채널(lexical/BM25)의 임베딩/토큰화 입력
    filters: PlanFilters
    exclude_ids: tuple[str, ...]
    security: SecurityContext
    payload_slim_keys: tuple[str, ...] = PAYLOAD_SLIM_KEYS
    lexical_terms: tuple[LexicalTerm, ...] = ()

class Retriever(Protocol):
    channel: Channel
    plugin_id: str
    def capabilities(self) -> Capabilities: ...
    async def run(self, inp: ChannelRunInput, ctx: StageContext) -> ChannelRun: ...

async def run_one(channel, variant, query_vectors, plan, ctx, *, retrievers: Mapping[str, Retriever]) -> ChannelRun: ...
async def retrieve_once(
    plan: QueryPlan, query_vectors: Mapping[str, QueryVectors], ctx, *,
    retrievers: Mapping[str, Retriever], concurrency: int = 32,
) -> CandidateSet: ...

# fusion.py
def fuse_ranks(channel_runs, *, k: int, weights: Mapping[str, float], variant_query_weight: float) -> list[dict]: ...
def fuse(cs: CandidateSet, plan: QueryPlan, *, now: datetime) -> RankedSet: ...
class RrfFuser:
    plugin_id = "fuser.rrf"
    async def run(self, inp: CandidateSet, ctx) -> RankedSet: ...  # ctx.plan 사용

# hydrate.py
class HydrateBackend(Protocol):
    async def retrieve_by_ids(self, alias, record_ids, *, security: SecurityFilter, with_payload) -> list[Mapping]: ...
class QdrantHydrateBackend:
    backend: QdrantIndexBackend
async def hydrate(rs: RankedSet, plan: QueryPlan, backend: HydrateBackend, *, now: datetime) -> RankedSet: ...

# adapters/retrieve/qdrant_dense.py, qdrant_sparse_bm25.py
class QdrantDenseRetriever:       # channel = Channel.dense
    plugin_id = "retriever.qdrant_dense"
    async def run(self, inp: ChannelRunInput, ctx) -> ChannelRun: ...
class QdrantSparseBm25Retriever:  # channel = Channel.lexical (lite)
    plugin_id = "retriever.qdrant_sparse_bm25"
    async def run(self, inp: ChannelRunInput, ctx) -> ChannelRun: ...
```

## 입출력 계약 발췌 (철자 정본)

- `CandidateSet{schema_version, schema_type="CandidateSet", tenant_id, collection_ids, producer,
  warnings, degraded, created_at, candidate_set_id, plan_id, query_id, channel_runs[], filters_applied,
  security_context_hash, total_unique, total_latency_ms}`. `channel_runs[]`는 `ChannelRun{
  channel_run_id="{channel}:{collection_id}:{variant_id}", channel, collection_id, variant_id,
  retriever_id, backend_id, collection_alias, embedding_profile_hash, index_generation_seen[],
  status(ok|timeout|error|disabled), took_ms, returned, total_hits, truncated, error?, candidates[]}`.
  `Candidate{record_id, chunk_id, collection_id, document_id, doc_version, item_kind, level,
  parent_chunk_id, score, rank, payload_slim: PayloadSlim{heading_path, page_start, page_end,
  doc_date, acl_classification, acl_hash, token_count_primary, text_preview, content_hash,
  text_source}, graph_path?}`(바이블 §5.5, `contracts/candidate_set.py`).
- `RankedSet{..., stage, hydrated, fusion: FusionReport{method, k, weights, variant_query_weight,
  candidates_in, candidates_out, downgraded_from?}, results: list[Result], stats: RankedSetStats{
  n_in, n_out, hydrated_n, gate_passed}}`. `Result(=RankedResult)`의 `score_breakdown:
  ScoreBreakdown{dense|sparse|lexical|...: ChannelScore{score, rank, contribution, variant_ids}|
  null, fused, fused_rank, rerank_raw, rerank_normalized, normalization, boosts?}` — 불변식
  `Σcontribution(non-null 채널) = fused`(`contracts/ranked_set.py`, `contracts/common_types`).
  `hydrated=true` 조건 필수: `text`, `context_prefix`, `heading_path`, `numbering_path`, `page_start`,
  `page_end`, `lang`, `text_source`, `chunk_set_blake3`, `acl`, `block_refs`, `sentence_spans`.
- RRF(§6.2): `contribution = w_run / (k + rank)`, `w_run = channel_weight * (1.0 원 질의 | 0.5 변형)`,
  `fused_score = Σ contribution`, 정렬 `(-fused_score, record_id)`. 채널당 병합 규칙(변형 여러 개가
  같은 채널을 적중): `contribution` 합산, `score`/`rank`는 원 질의 런 우선(없으면 최고 순위 런).
- `ErrorCodeCatalog` 철자(§5.7): `retrieve.security_context_missing`(E7, NON_RETRYABLE),
  `retrieve.channel_timeout`/`retrieve.backend_error`/`retrieve.unavailable`(RETRYABLE),
  `embed.server_unavailable`(RETRYABLE), `hydrate.backend_error`(RETRYABLE). `DegradedComponent`:
  `channel.dense|channel.sparse|channel.lexical`, `hydrate`. `DegradedReason`: `timeout`,
  `unavailable`, `partial_result`. `ExplainCode`: `dense_only_hit`, `sparse_only_hit`,
  `lexical_only_hit`, `multi_channel_hit`, `hydrate_missing`.
- 어댑터 재사용(계약 발췌 아님, 행동 발췌): `QdrantIndexBackend.search_dense`/`search_sparse`
  (`adapters/index/qdrant/backend.py`) — 사전 필터 단일 호출, `SearchHit{record_id, point_id, score,
  payload}`. `from_plan_filters`/`build_filter`(`adapters/index/qdrant/filters.py`) — `PlanFilters`
  -> Qdrant `Filter`, `assert_search_secured`가 E7을 검사. `query_vector(tokens)`
  (`adapters/index/qdrant/bm25_sparse.py`) — 질의 측 `tf_q` sparse 벡터.

## 불변식·금지

- 결과 캐시 금지(모든 모듈, ACL 시점성). `retrieve.security_context_missing`은 부분 실패로 감싸지
  않고 요청 전체를 실패시킨다(E7) — `retrieve_once`가 이 코드를 `StageError`에서 감지해 다시 던진다.
- RRF만 구현한다 — `convex_minmax`/`convex_zscore`/`dbsf`/`combmnz`·강등 판정(`downgraded_from`)·
  `late_interaction_rerank` 순서 필터는 범위 밖(open_issues).
- `hydrate`는 재조회에도 `PlanFilters.security`를 다시 적용한다(E10) — `record_id`가 구조적으로
  교차 테넌트 조회를 막아도 필터를 생략하지 않는다.
- 필터 빌더(코디네이터 -> 백엔드 네이티브)는 이 WP에서 통합하지 않는다: `channels.py`는
  `PlanFilters`·`exclude_ids`를 그대로 각 `Retriever`에 넘기고, 각 어댑터가 `from_plan_filters`로
  직접 변환한다(다중 백엔드 통합 빌더는 범위 밖, open_issues).
- 임베딩(무거운 벡터, dense/sparse_learned)은 이 모듈이 계산하지 않는다 — 호출자가
  `variant_id -> QueryVectors`를 미리 만들어 넘긴다. 결정적 토큰화(lexical/BM25)는 코디네이터가
  계산한 `query_text`를 받아 리트리버가 직접 tf_q 벡터를 만든다.
- `adapters/retrieve/*`는 `storage`/`security`를 import하지 않으며 Qdrant 벤더 타입을 밖으로
  새지 않는다(반환은 항상 계약 `ChannelRun`). 계약 생성물(`contracts/*`)은 손대지 않는다.
- 코드 규약: 모든 파일 첫 줄 한국어 헤더, `StageError` 코드는 §5.7 철자만, 커밋·이모지 금지.

## 단계

1. `channels.py`: `QueryVectors`/`ChannelRunInput`/`Retriever` 정의 -> `run_one`(리트리버 조회 +
   호출) -> `retrieve_once`(런 목록 구성 -> 세마포어 + `wait_for` 병렬 실행 -> 상태별 분류 ->
   `CandidateSet` 조립, `security_context_hash`/`filters_applied` 포함).
2. `fusion.py`: `_fuse_runs`(record_id x 채널 누적, §6.2 그대로) -> `fuse_ranks`(축소 어댑터 형태,
   골든 동치성 대상) -> `fuse`(`CandidateSet` 채널 런을 `_Run`으로 사상 -> 상위 `hydrate.top_n` 절단
   -> `ScoreBreakdown`/`explain`/`final_score`(min-max) 조립 -> `RankedSet`).
3. `hydrate.py`: `HydrateBackend` 프로토콜 + `QdrantHydrateBackend`(`HasIdCondition` + 보안 재필터
   스크롤) -> `hydrate`(컬렉션별 alias 그룹화 -> 배치 조회 -> 누락 처리(`omitted`/`degraded`/
   `explain`/`final_rank` 재부여) -> 신규 `RankedSet(hydrated=true)`).
4. `adapters/retrieve/qdrant_dense.py`, `qdrant_sparse_bm25.py`: `Stage` 5멤버(`capabilities`/
   `fingerprint`/`run`) 구현 — 사전 필터 조립 -> 백엔드 검색 1회 호출 -> `Candidate[]`/`ChannelRun`
   조립(원점수 내림차순, `rank` 1..n).

## 테스트(파일·케이스)

`tests/retrieval/test_fusion_channels.py`:

- `fusion.fuse_ranks` 골든 동치성: `testing.fuser_equivalence.assert_fuser_matches_rrf_golden(
  fusion.fuse_ranks, load_golden_case("tests/fixtures/fusion/rrf_3ch_5cand.json"))` 통과(Σcontribution
  불변식·`record_id` 타이브레이크 포함, 적합성 키트 자체가 검사).
- `fusion.fuse`: 소형 2채널 `CandidateSet`으로 (1) `Σcontribution == fused_score`(오차 1e-9), (2)
  동점 `record_id` 오름차순, (3) `final_score ∈ [0,1]`이고 최하위 절단 항목이 `0.0`, (4)
  `channels_hit`/`explain`(`multi_channel_hit`/`*_only_hit`) 정확, (5) 변형 런의 가중이 0.5로
  적용, (6) `stage="fused"`·`hydrated=False`.
- `channels.retrieve_once`: 페이크 `Retriever`로 (1) 두 채널 병렬 성공 -> `total_unique`/
  `channel_runs` 정확. (2) 한 채널 타임아웃 -> `status=timeout` + `degraded{channel.*, timeout}`,
  나머지 채널은 정상. (3) 전 채널 실패 -> `StageError("retrieve.unavailable")`. (4) 리트리버가
  `retrieve.security_context_missing`을 던지면 그대로 전파(다른 런과 섞여 있어도). (5) `enabled=false`
  채널은 `status=disabled`로 유지. (6) 세마포어가 `concurrency`를 넘지 않음(동시 실행 계수기).
- `hydrate.hydrate`: 페이크 `HydrateBackend`로 (1) 전건 hydrate 성공 -> `hydrated=True`,
  `text`/`acl` 등 채움, `final_rank` 1..n. (2) 한 건 누락 -> `omitted += hydrate_missing`,
  `degraded += {hydrate, partial_result}`, `explain` 반영, `final_rank` 재부여(`fused_rank` 유지),
  생존 건수만큼 `stats.hydrated_n`. (3) 이미 `hydrated=True`면 그대로 반환(멱등).
- `qdrant_dense`/`qdrant_sparse_bm25`: `QdrantIndexBackend.local()`(in-memory) 위에 소형
  `IndexRecord` 2~3건을 upsert하고 (1) dense 검색이 코사인 유사도 내림차순 `rank` 부여, `payload_slim`
  10키 채움. (2) `sparse_bm25` 검색이 토큰화 -> `query_vector` -> 검색까지 end-to-end로 동작(색인
  측 `document_vector`와 같은 토크나이저 사용 시 그 문서가 상위). (3) 질의 벡터 없음 ->
  `embed.server_unavailable`(dense). (4) 빈 토큰 질의 -> 빈 런(오류 아님, sparse_bm25).

## 완료 기준

`uv run pytest -q tests/retrieval/test_fusion_channels.py` 전부 통과(최대 3회), `uv run ruff check
src/rag_platform/retrieval/channels.py src/rag_platform/retrieval/fusion.py
src/rag_platform/retrieval/hydrate.py src/rag_platform/adapters/retrieve/qdrant_dense.py
src/rag_platform/adapters/retrieve/qdrant_sparse_bm25.py tests/retrieval/test_fusion_channels.py`
통과. mypy는 배치 검증자가 별도 실행.

## 검증 계층·DEFERRED

1층(여기서 검증) — `QdrantClient(":memory:")`(로컬 모드, 외부 자원 없음) + 순수 함수 + 페이크
`Retriever`/`HydrateBackend`. `needs_docker`/`needs_gpu`/`needs_model`/`needs_network` 해당 없음
(이 WP는 임베딩 서버·OpenSearch·실 Qdrant 서버를 쓰지 않는다).

- DEFERRED(설계 갭, 별도 WP 범위): `convex_minmax`/`convex_zscore`/`dbsf`/`combmnz`, `downgraded_from`
  강등 판정, `late_interaction_rerank`(MaxSim) 순서 필터, `graph`/`tree`/`visual`/`late_interaction`
  단일 적중 `ExplainCode`(10 미해결 이슈 7). `retriever.opensearch_bm25`(standard lexical)·
  `retriever.qdrant_sparse`(sparse_learned) 어댑터.
- DEFERRED: `retrieve()`의 0건 완화 재검색(§4.4, `filters.relaxable_keys` 1회 제거)과 `plan`
  단계의 채널 팬아웃 구성 — 이 WP는 `retrieve_once`(병렬 실행 1회)만 구현한다(코디네이터 상위
  래퍼는 planner WP 범위).
- DEFERRED(`needs_docker`): 서버 모드 Qdrant(payload 인덱스 `is_tenant`/`prefix` 효과, HNSW
  `payload_m` 실측) — `adapters/index/qdrant/backend.py`가 이미 표시한 DEFERRED와 동일 범주.
- 실 async I/O: `QdrantHydrateBackend`/두 리트리버는 동기 `QdrantClient` 위에 `async def`를 얹은
  것이라(로컬 모드는 사실상 non-blocking) 실 서버 대상 논블로킹 I/O(`AsyncQdrantClient`)는
  open_issues로 남긴다.

## 결과: 통과 17 / xfail 0 / DEFERRED 4
