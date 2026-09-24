---
title: "WP-404 렌더러와 질의 파이프라인"
status: active
owner: implementation
version: 0.1.0
last_updated: 2026-09-24
implementation_status: done
depends_on: ["../README.md", "../../12-appendix/10-implementation-design-gaps.md"]
---
# WP-404 렌더러와 질의 파이프라인 (F4-04, render-and-query-pipeline)

## 0. 실행 배경(병렬 배치 주의)

F4 배치는 `tools/phase6/wf-6f.js`가 F4-01(planner·filters)·F4-02(channels·fusion·hydrate)·
F4-03(postprocess·pack)·F4-04(본 WP)를 **병렬** 에이전트로 실행한다. 이 WP를 쓰는 시점에
`src/rag_platform/retrieval/{planner,channels,fusion,hydrate}.py`,
`src/rag_platform/retrieval/postprocess/{relevance_gate,dedup,mmr,parent_expand}.py`,
`src/rag_platform/retrieval/pack/*.py`, `src/rag_platform/adapters/retrieve/*.py`는
아직 존재하지 않는다(디렉터리에 `__init__.py`만 있음). 따라서 `pipelines/query.py`는
**의존성 주입(Protocol) 경계**로 설계해 이 파일만으로 임포트·단위 테스트가 되게 하고,
실 모듈 배선은 지연 임포트(`build_default_deps`)로 분리한다. 실제 F3 산출물 위의 전체
체인 통합은 `tools/phase6/wf-6f.js`의 배치 검증자(F4 Verify 단계)가 최종 실행·수정한다.

## 1. 목표

1. `ContextPack → RenderedContext` 렌더러 2종(`markdown`, `anthropic_search_result`)을
   바이블 §9.3(렌더러 정본)·§4.1(공통 렌더 규칙)에 맞게 구현한다.
2. `citation_map.py`에 `CitationMapEntry` 빌더와 §4.6 `map_back` 역매핑을 구현한다.
3. `pipelines/query.py`에 plan→retrieve→fuse/hydrate→postprocess→pack→render 인프로세스
   체인을 Protocol 기반으로 구현한다(ADR-0034: PostgreSQL 비의존, 오케스트레이터 미경유).

## 2. 파일

- `src/rag_platform/render/markdown.py`
- `src/rag_platform/render/anthropic_search_result.py`
- `src/rag_platform/render/citation_map.py`
- `src/rag_platform/pipelines/query.py`
- `tests/retrieval/test_query_e2e.py`

## 3. 시그니처

```python
# render/citation_map.py
@dataclass(frozen=True)
class CitationResolution:
    status: Literal["resolved", "unresolved"]
    cite_id: str | None
    chunk_id: str | None
    collection_id: str | None
    document_id: str | None
    segment_indices: list[int]
    provenance: list[common_types.Provenance]
    cited_text_match: bool | None
    reason: str | None  # unknown_key | out_of_range | text_mismatch | hallucinated_id

def build_entry(item: ContextItem, provider_key: int | str, *, block_offset=None,
                char_range=None, segment_range=None) -> CitationMapEntry: ...
def map_back(rendered: RenderedContext, pack: ContextPack, citation: ProviderCitation) -> CitationResolution: ...

# render/markdown.py
def render(pack: ContextPack, *, query_text: str, instructions_text: str | None = None) -> RenderedContext: ...

# render/anthropic_search_result.py
def render(pack: ContextPack, *, query_text: str | None = None, system_text: str | None = None,
           tool_result: bool = False, cache_control: bool = True,
           empty_policy: Literal["text", "error"] = "text") -> RenderedContext: ...

# pipelines/query.py
class Planner(Protocol):
    def __call__(self, request: QueryRequest, security: SecurityContext) -> QueryPlan: ...
class ChannelRetriever(Protocol):
    async def __call__(self, plan: QueryPlan, security: SecurityContext) -> CandidateSet: ...
class Fuser(Protocol):
    def __call__(self, candidates: CandidateSet, plan: QueryPlan) -> RankedSet: ...
class Hydrator(Protocol):
    async def __call__(self, ranked: RankedSet, plan: QueryPlan, security: SecurityContext) -> RankedSet: ...
class Postprocessor(Protocol):
    def __call__(self, ranked: RankedSet, plan: QueryPlan) -> RankedSet: ...
class Packer(Protocol):
    def __call__(self, ranked: RankedSet, plan: QueryPlan, security: SecurityContext) -> ContextPack: ...
class RendererFn(Protocol):
    def __call__(self, pack: ContextPack, *, query_text: str) -> RenderedContext: ...

@dataclass(frozen=True)
class QueryPipelineDeps:
    plan: Planner; retrieve: ChannelRetriever; fuse: Fuser; hydrate: Hydrator
    postprocess: Postprocessor; pack: Packer
    renderers: dict[Renderer, RendererFn] | None = None

async def run_query(request: QueryRequest, security: SecurityContext, deps: QueryPipelineDeps,
                     *, render: bool = True) -> QueryPipelineResult: ...
def resolve_renderer(request: QueryRequest) -> Renderer: ...
def build_default_deps() -> QueryPipelineDeps: ...  # 지연 임포트, F4-01~03 배선
```

## 4. 입출력 계약 발췌(정본 철자)

- `ContextItem`(contracts/common_types): `cite_id`(`d{rank}`), `rank`, `position`, `chunk_id`
  (Hex64), `collection_id`/`document_id`(Ulid), `header{title, section_path, doc_date, doc_type,
  source_uri, lang, doc_version_label}`, `text`, `text_source`(`text_layer|ocr|vlm|converted`),
  `ocr_confidence_min`, `segments[]{index, text, char_start, char_end, block_id}`, `tables[]
  {format_used: html|markdown|json, html, markdown, json_records, caption}`, `figures[]{caption,
  alt_text}`, `conflicts_with[]{cite_id, kind, note}`, `provenance[]`.
- `ContextPack.render_hints{preferred_renderer, citation_style: native|bracket_id,
  instructions_template_id, table_format_preference, language, expose_confidence, data_marking:
  none|delimit|datamark}`, `.items`(position 오름차순, cite_id = d1..dK 연속), `.tenant_id`,
  `.collection_ids`, `.pack_id`, `.content_hash`.
- `RenderedContext`(contracts/rendered_context.py): `schema_type="RenderedContext"`, `pack_id`,
  `renderer`(enum `Renderer`), `tenant_id`, `collection_ids`, `provider_payload`(dict|str),
  `stable_prefix`(dict|str|None), `volatile_suffix`(dict|str), `citation_map[]
  {provider_key, cite_id, chunk_id, collection_id, document_id, segment_range:[start,end),
  block_offset?, char_range?}`, `token_count_rendered`, `count_method`(`exact_api|exact_local|
  approximate`), `warnings[]`.
- 바이블 §9.3 표: `anthropic_search_result` 블록 = `{"type":"search_result","source":
  "rag://{collection_id}/{document_id}/{chunk_id}","title": 헤더 라인,"content":[...],
  "citations":{"enabled":true}}`(`source`에 `tenant_id` 없음). 렌더러는 `model`을 넣지 않는다
  (§4.4 "모델" 행 — 모델 ID 하드코딩 금지).
- 헤더 라인(§4.1): `"{title} › {section_path 조인} ({doc_date}) [{confidence_tier}]"` +
  `[ocr X.XX]`/`[vlm]`/`[converted]` 접미(`expose_confidence=true`일 때 ocr 소수 2자리).
- §9.2 `litm_alternating`: `items`는 이미 `position` 오름차순으로 주어짐(패커 산출물) — 렌더러는
  이를 그대로 순회한다(재계산 금지).

## 5. 불변식·금지

1. 공급자 페이로드에 `tenant_id`·주체 문자열·`acl_*`·`record_id`·원시 점수를 넣지 않는다(§9.3
   공통 규칙 1). 내부 식별자는 `RenderedContext.citation_map`에만.
2. `cite_id`는 최종 항목과 연속 `d1..dK`(공통 규칙 3) — `omitted[]`는 렌더하지 않는다.
3. 렌더러는 `model` 필드를 만들지 않는다(모델 ID 하드코딩 금지, §4.4).
4. `anthropic_search_result`의 `citations.enabled`는 all-or-nothing(전 블록 true).
5. `pipelines/query.py`는 `temporalio`·`fastapi`·`starlette`·`rag_platform.ledger`·
   `rag_platform.orchestration`을 임포트하지 않는다(import-linter D-17, `pipelines/__init__.py`
   불변식). `retrieve`는 결과를 캐시하지 않는다(ACL 시점성, §4.3).
6. `rerank`는 이 WP 범위에 어댑터가 없다(모델 다운로드 금지) — `postprocess`는 hydrate 직후
   `RankedSet`을 그대로 받는다. 이는 바이블 §4.3이 이미 정의한 rerank 실패 폴백(`rerank.applied=
   false`, `explain += rerank_skipped`)과 같은 모양이라 새 계약을 만들지 않는다.
7. 계약 생성물(`contracts/*`)은 손대지 않는다.

## 6. 단계

1. `render/citation_map.py`: `CitationResolution`, `build_entry`, `map_back`(+ 위치 타입
   `SearchResultLocation`/`ContentBlockLocation`/`CharRange`) 구현.
2. `render/markdown.py`: 헤더 라인·출처 줄·표/그림 인라인·`data_marking`(`none/delimit/datamark`)
   구분자 처리·`[dN]` 마커 렌더.
3. `render/anthropic_search_result.py`: `search_result` 블록 조립(세그먼트=텍스트 블록 1:1, 표
   항목은 블록 1개), 상충 안내 문구(있으면 첫 `text` 블록), `cache_control` 브레이크포인트 2곳,
   `citations.enabled=true`, K=0 폴백, `tool_result` 옵션.
4. `pipelines/query.py`: Protocol 6종 + `QueryPipelineDeps`/`QueryPipelineResult` + `run_query`
   + `resolve_renderer`(§4.3 provider→renderer 표) + `build_default_deps`(지연 임포트).
5. `tests/retrieval/test_query_e2e.py`: 페이크 `QueryPipelineDeps`로 한국어 질의 3종 실행,
   `testing.renderer_citation_roundtrip`으로 cite_id 왕복 검증.

## 7. 테스트

- `tests/retrieval/test_query_e2e.py`
  - `test_run_query_markdown_roundtrip` — 질의 1, `renderer=markdown` 명시, 3항목 팩.
  - `test_run_query_anthropic_search_result_roundtrip` — 질의 2, `renderer=anthropic_search_result`
    명시, `citations.enabled`·`source` 무-tenant_id·`model` 키 부재 검증.
  - `test_run_query_renderer_derived_from_target_model` — 질의 3, `renderer` 미지정 +
    `target_model.provider=anthropic` → `resolve_renderer`가 `anthropic_search_result` 도출.
  - `test_anthropic_search_result_conflict_notice` — `conflicts_with` 있는 팩에서 안내 문구
    첫 텍스트 블록 검증.
  - `test_markdown_data_marking_delimit` — `data_marking=delimit`일 때 `<<<DATA dN>>>` 구분자.
  - `test_citation_map_back_resolves_and_rejects_hallucination` — `map_back` 정상 해석 +
    `hallucinated_id`/`out_of_range` 케이스.

## 8. 완료 기준

`uv run pytest -q tests/retrieval/test_query_e2e.py` 전부 통과, `uv run ruff check` 대상 5개
파일 통과. 실 F4-01~03 모듈과의 전체 배선(F3 샘플 → 실 검색 → 실 팩)은 F4 배치 검증자가 최종
실행(위 §0).

## 9. 검증 계층·DEFERRED

1층(여기서 검증) — 위 테스트 파일. `uv run lint-imports`로 확인한 실제 계층 규칙(바이블 §12):
`pipelines`는 `retrieval`·`render`(형제 계층)를 임포트할 수 없다 — 최초 초안의 `build_default_deps`
(F4-01~03 실 모듈 지연 임포트)는 이 규칙을 어겨 제거했다. `pipelines/query.py`는 순수
`contracts.*` + Protocol만 남기고, 실 F4-01~03 모듈 + 렌더러 2종을 이 Protocol에 맞춰 묶는
배선은 F5(api/mcp/cli, 상위 계층) 또는 F4 배치 검증자의 몫이다 — `# DEFERRED: F5 또는 F4 배치
검증자가 retrieval.planner/channels/fusion/hydrate/postprocess.*/pack.packer + render.markdown/
anthropic_search_result를 QueryPipelineDeps로 묶어 tests/retrieval의 전체 체인 e2e를 F3 샘플
위에서 실행한다`. 모델·Docker·GPU 의존 없음.

결과: 통과 7 / xfail 0 / DEFERRED 1(F5 또는 F4 배치 검증자의 실 모듈 배선·전체 체인 e2e)
