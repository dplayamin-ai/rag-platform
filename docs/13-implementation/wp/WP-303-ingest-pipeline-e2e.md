---
title: "WP-303 ingest-pipeline-e2e"
status: active
owner: implementation
version: 1.0.0
last_updated: 2026-09-23
implementation_status: done
depends_on: ["../README.md", "../../12-appendix/10-implementation-design-gaps.md"]
---
# WP-303 ingest-pipeline-e2e (F3-03)

## 목표

바이블 §11.1(`pipelines.ingest.run(ctx, req_ref, profile) -> IndexCommit`)의 파이프라인 정의를
완성하고(`out_type` 자리표시자 `object`를 실제 생성 계약 클래스로 교체), `lite` 프로파일 값으로
`fetch → detect·parse → normalize → chunk → enrich → embed → index → publish` 전체 체인을
`LocalRunner`(바이블 §11.1 `local` 모드)로 실행하는 e2e 테스트를 작성한다. F1(`fetch`/`parse`/
`normalize`)·F2(`chunk`/`enrich` 결정적 보강 3종)가 만든 실제 스테이지 어댑터를 그대로 쓰고,
`embed`/`index`는 이 배치(F3)의 다른 병렬 WP(F3-01/02)가 아직 만들지 않은 5멤버 `Stage` 합성
래퍼를 이 e2e 테스트 파일 안에서만 최소로 조립한다(§4.2 `embed`=`embedder.inprocess_fake`,
`index`=`index_backend.qdrant` 로컬 모드).

## 파일

- `src/rag_platform/pipelines/ingest.py` — `STAGE_OUTPUT_TYPES`(`STAGE_OUTPUT_SCHEMA_TYPES`와 같은
  매핑을 실제 계약 클래스 값으로 둔 것) 추가, `run()`이 `ctx.run(stage, ref, object, ...)` 대신
  `ctx.run(stage, ref, STAGE_OUTPUT_TYPES[stage], ...)`을 호출하도록 교체. `STAGES`·`from_stage`·
  `recount` 생략 로직은 변경 없음.
- `tests/e2e/test_ingest_e2e.py` — `_E2EPipeline`(`PipelineContext` 구현, 스테이지 1개짜리
  `LocalRunner.run([...])` 호출로 매 `ctx.run` 호출을 옮기는 이 파일 전용 셸) + `_build_*_payload`
  (enrich/embed/index 산출물 조립 순수 함수) + 파라미터화 e2e 테스트 2종.
- `tests/fixtures/e2e/{sample.txt,sample.md,sample.html}` — 새 최소 한국어 픽스처(기존
  `tests/fixtures/parse_text`·`parse_html`는 인코딩 엣지케이스 전용이라 재사용하지 않음).

## 시그니처

```python
# pipelines/ingest.py
STAGE_OUTPUT_TYPES: dict[str, type[Any]] = {
    "fetch": SourceDocument, "parse": ParsedDocument, "normalize": NormalizedDocument,
    "chunk": ChunkSet, "recount": ChunkSet, "enrich": EnrichedChunkSet,
    "embed": EmbeddedChunkSet, "index": IndexCommit, "publish": CloudEventEnvelope,
}
async def run(ctx: PipelineContext, req_ref: Any, profile: PipelineProfile, *, from_stage: str = "fetch") -> Any: ...

# tests/e2e/test_ingest_e2e.py
class _E2EPipeline:
    async def run(self, stage: str, inp_ref: Any, out_type: type[Any], policy: StagePolicy) -> Any: ...
    async def emit(self, event: Any) -> None: ...
    def now(self) -> datetime: ...
    async def sleep(self, duration: timedelta) -> None: ...

async def test_ingest_pipeline_commits_indexes_and_is_idempotent_on_rerun(
    harness: _Harness, _case_id: str, source_path: Path
) -> None: ...
def test_stage_output_types_are_the_real_generated_contracts() -> None: ...
```

## 입출력 계약 발췌 (철자 정본)

- 바이블 §4.2 `STAGES` 표(파이프라인이 그대로 재현): `fetch`(`IngestRequest`→`SourceDocument`),
  `parse`(`SourceDocument`→`ParsedDocument`, `detect` 서브스테이지 포함), `normalize`
  (→`NormalizedDocument`), `chunk`(→`ChunkSet`), `enrich`(→`EnrichedChunkSet`), `embed`
  (→`EmbeddedChunkSet`), `index`(→`IndexCommit`), `publish`(→`CloudEventEnvelope[]`).
- `EnrichedChunkSet.enrichments: object<chunk_id, Enrichment>` — 색인 대상(`level ∈ {0,2}`)만 키로
  담는다(부모 `level=1`은 제외, `EmbeddedChunkSet.vectors` 주석과 동일 규칙).
- `EnrichedChunkSet`/`EmbeddedChunkSet`/`IndexCommit`의 생성 `LineageRefs` 하위 모델은 키별
  `media_type: Literal[...]` + 필수 `schema_type`/`schema_version`(예 `lineage_refs.source.media_type
  == "application/vnd.rag.source-document+json"`) — `NormalizedDocument`/`ChunkSet`의
  `lineage_refs`가 쓰는 일반 `common_types.MediaType` 패턴 타입과 다르다(설계 갭, 아래 불변식·
  open_issues 참조).
- `IndexRecord`(`chunk_set_blake3`·`acl_*`·`embedding_space_ids` 등 §5.4 표 "원천" 열 그대로):
  `record_id = H("record", tenant_id, collection_id, document_id, str(index_generation), chunk_id)`,
  `point_id = uuid5(NAMESPACE_RAG_CHUNK, record_id)`(`sdk.hashing.record_id`/`point_id_for_record`).
- `ADR-0037`: `stage_key = H("stage", stage_name, scope_key, input_hash, fingerprint)`,
  `scope_key = f"{tenant_id}/{collection_id}/{document_id}"`; `fetch`/`index`는 `CACHE_EXEMPT`
  (`orchestration/local/runner.py`)라 매 실행 재계산.

## 불변식·금지

- `pipelines/ingest.py`는 여전히 `PipelineContext`에만 의존하는 순수 정의다 — `temporalio`·
  `fastapi`·`rag_platform.orchestration`·`rag_platform.ledger` 임포트 금지(import-linter
  `pipelines-orchestrator-neutral`, D-17); 계약 클래스 임포트(`rag_platform.contracts.*`)는
  최하단 계층이라 허용된다(바이블 §12).
- e2e 테스트의 `_E2EPipeline`/`_AdapterStage`는 이 파일 전용 테스트 하네스이며 `orchestration/
  context.py`(아직 없음)의 자리표시자다 — 프로덕션 셸 코드가 아니다.
- `_E2EContext`가 쓰는 시계는 **고정 시각**(`2026-09-23T09:00:00Z`)이다 — `fetch`가 캐시 예외라도
  출력 바이트가 재실행마다 바이트 단위로 동일해야 `parse`부터의 `stage_key` 캐시 조회가 의미
  있다(§7.2 "실행 규율"이 요구하는 재현성과 별개로, 이 e2e 자체의 재실행 검증 전제).
- `embed`/`index` 합성 스테이지는 F3-01/02가 최종 배선할 프로덕션 `Stage` 클래스가 아니다 —
  모델 가중치 없는 `embedder.inprocess_fake`(사용자 결정, VDI 다운로드 금지)와 Qdrant 로컬 모드
  (`QdrantIndexBackend.local()`, `:memory:`)만 쓴다. BM25 sparse는 `WhitespaceTokenizer`(Kiwi
  미설치 폴백과 동일 경로)로 계산한다.

## 단계

1. `pipelines/ingest.py`: `STAGE_OUTPUT_SCHEMA_TYPES`와 나란히 `STAGE_OUTPUT_TYPES`(실제 클래스)를
   추가하고 `run()`의 두 `ctx.run(...)` 호출에서 `object`를 `STAGE_OUTPUT_TYPES[stage]`로 교체.
2. `tests/fixtures/e2e/`에 최소 한국어 txt/md/html 픽스처 3종 작성.
3. `_E2EPipeline` 하네스: `fetch`(`FsspecHttpxFetcher`)·`parse`(`ParseRouterStage` + `hwpx_python_
   hwpx`/`text_charset_markdown_it`/`html_trafilatura_docling` 후보)·`normalize`(`NormalizerChain
   Stage`)·`chunk`(`StructureAwareChunkerStage`)는 실제 어댑터를 그대로 `_AdapterStage`로 감싸
   bytes↔계약 JSON 변환만 대신한다. `enrich`는 결정적 보강기 3종(`DeterministicPrefixEnricher`·
   `KoreanKeywordsEnricher`·`DerivedMetaEnricher`)을 순서대로 실행해 만든 `acc`를 `Enrichment`로
   조립한다. `embed`는 `InprocessFakeEmbedder.embed_documents` + BM25 sparse. `index`는
   `IndexRecord` 조립 → `QdrantIndexBackend.upsert` → `set_current`(플립) → `IndexCommit`
   (`status="committed"`) 조립. `publish`는 `CloudEventEnvelope`(`ingest.document.indexed`) 1건.
4. `ctx.parsed_ref`/`ctx.normalized_ref`(`normalize`/`chunk`가 이미 요구하는, 아직 `StageContext`에
   없는 포트, F1 WP가 이미 open issue로 남긴 공백)와 `ctx.source_bytes()`(`parse`)를 `_E2EPipeline.
   run()`이 스테이지별로 주입한다. `enrich`/`embed`/`index`/`publish`는 `ctx.self_ref`(자기 입력의
   `ArtifactRef`)를 주입해 `lineage_refs` 전파에 쓴다.
5. `pipelines.ingest.run(pipeline, req_ref, profile)`을 문서당 2회(최초·재실행) 호출해 커밋·캐시
   히트·멱등을 단언한다.

## 테스트(파일·케이스)

`tests/e2e/test_ingest_e2e.py`:
- `test_ingest_pipeline_commits_indexes_and_is_idempotent_on_rerun`(파라미터화, 6케이스: txt·md·
  html·hwpx 3종) — 1차 실행: `IndexCommit.status == "committed"`·`record_count >= 1`·Qdrant 로컬
  `count(is_current=true 필터) == record_count`. 2차 실행(같은 `document_id`): `normalize`·`chunk`·
  `enrich`·`embed`가 `stage_key` 캐시 히트(`RunResult.log[].cache_hit`), `is_current=true` 레코드
  수가 1차와 동일(멱등, 중복 없음).
- `test_stage_output_types_are_the_real_generated_contracts` — `STAGE_OUTPUT_TYPES` 8개 항목이
  실제 임포트한 계약 클래스와 동일한 객체인지(간단 회귀 방지).

## 완료 기준

`uv run pytest -q tests/e2e/test_ingest_e2e.py` 전부 통과, `uv run ruff check
src/rag_platform/pipelines/ingest.py tests/e2e/test_ingest_e2e.py` 통과. mypy는 배치 검증자가
별도 실행. `tests/unit/test_pipelines_ingest.py`(기존 단위 테스트, `out_type` 인자를 검사하지 않아
이번 변경과 무충돌)도 회귀 확인으로 재실행.

## 검증 계층·DEFERRED

1층(여기서 검증) — Qdrant 로컬 모드(`:memory:`), 모델 가중치 없는 fake 임베더, 실제 fetch는
`file://`만(외부 네트워크 없음). `needs_docker`/`needs_model`/`needs_gpu`/`needs_network` 해당 없음.

- DEFERRED: `embed`/`index`를 5멤버 `Stage` 프로토콜의 재사용 가능한 프로덕션 어댑터
  (`adapters/embed/*`, `adapters/index/*`에 `run(inp, ctx) -> Out` 형태로)로 승격하는 일 — 이
  e2e 파일의 `_AdapterStage` 래퍼는 테스트 전용이며 F3-01/02가 실제로 그런 모듈을 만들면 이
  하네스를 그 모듈 호출로 교체해야 한다(open_issues 참조).
- DEFERRED: `orchestration/context.py`(`run_stage`, `ArtifactRef ↔ 계약 인스턴스` 변환을 하는 진짜
  셸)가 아직 없다 — `_E2EPipeline`은 그 자리를 이 테스트 안에서만 채운 것이다.
- DEFERRED: `IndexCommit`의 사가(§11.4, 플립 순서 렉시컬→벡터·보상·원장 트랜잭션)는 이 WP 범위
  밖 — `index` 스테이지는 Qdrant 업서트 + `set_current` 플립만 하고 원장(PostgreSQL)·OpenSearch·
  보상 경로는 다루지 않는다(`lite`는 애초에 OpenSearch가 없다, 바이블 §7.1).
- DEFERRED: `parse` 스테이지 자체의 재실행 캐시 히트는 보장하지 않는다 — `fetch`가 캐시 예외라서
  매번 새 `SourceDocument`를 만드는데, 그 `fetch_report.duration_ms`/`bytes_per_sec`가 파일 I/O
  타이밍에 따라 달라져 `parse.stage_key`의 `input_hash`(=fetch 출력 전체 바이트 해시)가 바뀔 수
  있다(파일이 실제로는 다시 파싱하지 않을 값들을 해시에 포함). 테스트는 그 뒤의 `normalize`부터만
  캐시 히트를 단언한다.

## 결과: 통과 7 / xfail 0 / DEFERRED 4
