---
title: "WP-503 CLI와 전체 e2e"
status: active
owner: implementation
version: 0.1.0
last_updated: 2026-09-24
implementation_status: done
depends_on: ["../README.md", "../../12-appendix/10-implementation-design-gaps.md"]
---
# WP-503 CLI와 전체 e2e (F5-03, cli-and-full-e2e)

## 0. 실행 배경(병렬 배치 주의)

F5 배치는 `tools/phase6/wf-6f.js`가 F5-01(api-ingest-jobs-query)·F5-02(mcp-server)·F5-03(본 WP)을
**병렬** 에이전트로 실행한다. 이 WP를 쓰는 시점에 `src/rag_platform/api/app.py`는 아직 없었고
(F5-01 진행 중), `src/rag_platform/mcp/{server,tools,cursor_store}.py`는 F5-02가 이미 만들어
둔 상태였다(`mcp.tools.search`는 SDK 서버 기동 없이 직접 호출 가능하도록 설계됨). 구현 도중
F5-01도 완료되어 `api/app.py`가 나타났지만, 그 `api/query.py`는 **자신의 모듈 docstring에
명시된 대로 `pipelines.query.run_query`의 6-Protocol을 아직 배선하지 않는다**(`POST /v1/query`는
항상 빈 `ContextPack`을 돌려주는 `_build_empty_context_pack` 스텁). 이 WP는 그래서 (1) CLI 자신의
질의 배선(F4 실 모듈)과 MCP `search`(F5-02, 실 배선을 주입받는 설계)까지는 진짜 결과로 비교하고,
(2) API 비교는 "인증된 요청이 같은 tenant_id/collection_id로 200을 받는지"까지만 확인한다
(§9 DEFERRED 1). `pipelines/ingest.py`·`pipelines/query.py`는 각각 "이 배선은 F5의 몫"이라고
문서화해 뒀다 — 이 WP가 그 공백을 메운다.

## 1. 목표

1. `rag` CLI에 `ingest <paths…> --profile lite-dev --collection`, `query "<질의>" --collection
   [--format text|json]`, `serve api|mcp`, `profile validate <id>` 4개 명령을 구현한다(바이블
   §12 `cli` 명령 목록의 이 WP 범위; §11.6 5분 기동 절차와 같은 모양).
2. `rag ingest`가 실제로 F1~F3 실 어댑터(fetch·parse 라우터·normalize·chunk·enrich·embed 페이크·
   index Qdrant 로컬)를 `LocalRunner`로 엮어 `IndexCommit`을 커밋하게 한다(`pipelines.ingest.run`을
   구동하는 `PipelineContext` 구현).
3. `rag query`가 실제로 F4 실 모듈(planner·channels·fusion·hydrate·postprocess·pack·render)을
   `pipelines.query.run_query`의 6-Protocol(`QueryPipelineDeps`)에 배선해 `ContextPack`을 만들게
   한다.
4. 전체 e2e: CLI 수집 → CLI 질의(`ContextPack`) → `cite_id` 왕복(렌더러 2종) → MCP `search`
   핸들러가 같은 `document_id` 집합을 내는지 확인 → API `TestClient`는 있으면 인증 경로까지 확인.
5. `deploy/compose/compose.lite.yaml`을 작성한다(기동 검증은 `needs_docker`, 이 WP는 작성만).

## 2. 파일

- `src/rag_platform/cli/main.py`(신규)
- `tests/e2e/test_full_e2e.py`(신규)
- `deploy/compose/compose.lite.yaml`(신규)

## 3. 시그니처

```python
# cli/main.py — 공개 진입점(테스트·main() 공용)
def resolve_profile_id(profile: str) -> str: ...                 # "lite-dev" -> "lite" (open_issues)
def physical_alias_for(collection_id: str) -> str: ...            # "col_{collection_id}_vec"
async def ingest_paths(
    paths: Sequence[Path], *, collection: str, profile: str = "lite-dev",
    state_dir: Path = Path(".rag"),
) -> list[dict[str, Any]]: ...                                    # [{path, document_id, commit_id, record_count, status}]
def build_query_deps(backend: QdrantIndexBackend, embedder: InprocessFakeEmbedder) -> query_pipeline.QueryPipelineDeps: ...
def resolve_collection(collection: str, *, state_dir=...) -> tuple[str, str]: ...  # (tenant_id, collection_id)
def build_backend(state_dir=...) -> QdrantIndexBackend: ...
def build_embedder() -> InprocessFakeEmbedder: ...
def security_context_for(*, tenant_id: str, collection_id: str) -> ct.SecurityContext: ...
async def run_query_lite(
    query_text: str, *, collection: str, state_dir: Path = ..., render: bool = True,
) -> query_pipeline.QueryPipelineResult: ...
def build_arg_parser() -> argparse.ArgumentParser: ...
def main(argv: Sequence[str] | None = None) -> int: ...
```

## 4. 입출력 계약 발췌(정본 필드·열거 철자)

- `pipelines.ingest.STAGES = ("fetch","parse","normalize","chunk","recount","enrich","embed","index")`,
  `pipelines.ingest.run(ctx: PipelineContext, req_ref, profile: PipelineProfile, *, from_stage="fetch")`.
- `sdk.context.PipelineContext`: `async run(stage, inp_ref, out_type, policy) -> ArtifactRef`,
  `async emit(event)`, `now() -> datetime`, `async sleep(d)`.
- `pipelines.query.QueryPipelineDeps` 6-Protocol: `plan(request, security) -> QueryPlan`,
  `async retrieve(plan, security) -> CandidateSet`, `fuse(candidates, plan) -> RankedSet`,
  `async hydrate(ranked, plan, security) -> RankedSet`, `postprocess(ranked, plan) -> RankedSet`,
  `pack(ranked, plan, security) -> ContextPack`, `renderers: dict[Renderer, RendererFn]`.
- `retrieval.planner.plan(request, security, *, plan_id=None, defaults=None) -> QueryPlan` —
  `PlannerDefaults.channels`에 `retriever.qdrant_dense`(`Channel.dense`)·
  `retriever.qdrant_sparse_bm25`(`Channel.lexical`) 두 채널만 있다(규칙 경로, LLM 없음).
- `retrieval.channels.retrieve_once(plan, query_vectors: Mapping[str, QueryVectors], ctx, *,
  retrievers: Mapping[str, Retriever]) -> CandidateSet` — `retrievers` 키는 `channel.retriever_id`
  문자열(위 두 plugin_id).
- `retrieval.postprocess.relevance_gate.apply(results, *, tau) -> StepResult`,
  `retrieval.postprocess.dedup.apply(results, *, cosine_threshold, minhash_threshold, num_perm,
  seed) -> StepResult` — lite는 `mmr`·`parent_expand`를 끈다(바이블 §7.2 "끔").
- `retrieval.pack.packer.pack(ranked: RankedSet, cfg: PackConfig, *, now) -> ContextPack` — `pack`
  내부가 `acl_recheck→budget_cut→reorder→citation_align`을 순서대로 실행한다(호출자는 배선만).
- `mcp.tools.ToolDeps(query_runner, document_reader, collection_lister, cursor_store,
  max_result_tokens=...)`; `QueryRunner.__call__(request: QueryRequest, security) -> ContextPack`;
  `search(args: dict, security, deps) -> ToolResult`.
- `security.security_context.ApiKeyRegistry.register(api_key, *, tenant_id, subject, roles=(),
  allowed_collection_ids=None)`, `authenticate(registry, "Bearer <key>") -> ApiKeyRecord`.
- Qdrant 물리 별칭 규약(양쪽이 반드시 같은 문자열을 써야 같은 컬렉션을 본다):
  `retrieval.planner._build_channels`의 `f"col_{collection_id.root}{alias_suffix}"`
  (`alias_suffix = "_vec"` — lite의 두 채널 모두 `backend_id="index_backend.qdrant"`) ==
  이 WP의 `physical_alias_for(collection_id)`.

## 5. 불변식·금지

- `cli`는 바이블 §12 계층상 `api`/`mcp`와 같은 층의 **독립 형제**다(import-linter `layers`
  contract) — `rag_platform.api`/`rag_platform.mcp`를 import하지 않는다. `serve api|mcp`는
  `subprocess.run([sys.executable, "-m", ...])`으로만 띄운다.
- 모델 가중치 다운로드 금지: 임베더는 `adapters/embed/inprocess_fake.InprocessFakeEmbedder`만
  쓴다(testing.doubles.FakeEmbedder를 감싼 것).
- `retrieve`는 결과를 캐시하지 않는다(ACL 시점성, 바이블 §4.3) — CLI 배선도 매 질의 새 플랜.
- `SecurityContext`는 서버(셸)가 주입한다(ADR-0027) — CLI는 요청 본문에 tenant/보안 필드를
  받지 않고 레지스트리에서 유도한 값을 직접 만든다.
- 온디스크 로컬 Qdrant(`QdrantClient(path=...)`)는 파일 잠금을 쓴다 — 같은 프로세스 안에서
  `ingest`→`query`를 이으려면 이전 `QdrantIndexBackend`를 명시적으로 `backend.client.close()`
  해야 한다(`_LitePipelineContext.context = self` 자기 참조 순환 때문에 단순 refcount로는
  즉시 해제되지 않음, open_issues).
- lite 채널 기본 `timeout_ms=250`(`lite.yaml`, 서버 Qdrant 기준)은 이 WP의 "매 질의마다 온디스크
  Qdrant를 새로 여는" 개발 편의와 맞지 않아 콜드 스타트 시 간헐적으로 `retrieve.unavailable`을
  낼 수 있다 — CLI 전용 `PlannerDefaults`(채널 `timeout_ms=5000`)로 완화했다(`lite.yaml` 자체는
  손대지 않음, open_issues).
- `cli/main.py`는 이 WP의 유일한 대상 소스 파일이다 — `src/rag_platform/cli/__init__.py`,
  `profiles/builtin/*.yaml`, `pyproject.toml`은 수정하지 않는다(§ open_issues에 두 가지 공용
  파일 이슈를 남긴다).

## 6. 단계

1. 읽기: 바이블 §12(cli 명령 목록·모듈 의존 방향)·§7.1(lite 컴포넌트 표)·§11.6(5분 기동),
   `pipelines/ingest.py`·`pipelines/query.py`(Protocol과 "배선은 F5의 몫" 공백),
   `docs/09-operations/01-deployment-guide.md` §3.1~§3.4(lite 서비스 목록·compose 스케치),
   `tests/e2e/test_ingest_e2e.py`·`tests/retrieval/test_query_e2e.py`(F3/F4가 검증에 쓴 하네스
   패턴 — 실 어댑터 호출 관례의 정본 예시), F1~F4가 만든 실 어댑터·모듈 헤더.
2. `cli/main.py` 작성: 레지스트리(`_Registry`, 상태 디렉터리에 tenant/collection/document ID
   영속화) → 수집 측 `_LitePipelineContext`(F1~F3 어댑터 배선, `test_ingest_e2e.py`의
   `_E2EPipeline` 패턴을 프로덕션 코드로 재구성) → 질의 측 6-Protocol 어댑터(F4 실 모듈 배선,
   `planner.plan`/`channels.retrieve_once`/`fusion.fuse`/`hydrate.hydrate`/자체
   `relevance_gate`+`dedup` 후처리/`packer.pack`/`markdown`·`anthropic_search_result` 렌더러) →
   argparse 명령 4개.
3. 수동 스모크(`uv run python -c "..."`)로 ingest→query→MCP 배선을 프로세스 내에서 확인 —
   `profile_id`/`profile_hash`가 `RootModel`이라 `PackConfig`에 그대로 넣으면 `ValidationError`가
   나는 것과 온디스크 Qdrant 잠금 충돌(§5)을 이 단계에서 발견·수정했다.
4. `tests/e2e/test_full_e2e.py` 작성 — CLI 공개 함수 경로(직접 호출) + argparse `main()` 경로
   양쪽, MCP `search` 동일 결과, API(있으면) 인증 경로, `serve` 서브프로세스 argv(모의).
5. `deploy/compose/compose.lite.yaml` 작성 — 배포 가이드 §3.4 스케치를 그대로 따르되 "개발"
   4-컨테이너 토폴로지(app/postgres/qdrant/valkey)만(§ open_issues에 "worker" 문구 해석 기록).
6. `uv run ruff check`/`ruff format` 대상 파일 통과, `uv run pytest -q tests/e2e/test_full_e2e.py`
   반복 실행(연속 3회 안정, 온디스크 Qdrant 타이밍 플레이크 없음 확인) 후 종료.

## 7. 테스트(파일·케이스)

`tests/e2e/test_full_e2e.py`:

1. `test_ingest_then_query_produces_context_pack_with_citation_roundtrip` — CLI 수집(txt/md/html
   픽스처 3종) → CLI 질의 → `ContextPack.items` 비지 않음, `testing.renderer_citation_roundtrip.
   assert_cite_ids_bijective_with_items` + 렌더러 2종(`markdown`, `anthropic_search_result`) 각각
   `assert_renderer_citation_roundtrip`.
2. `test_requerying_unknown_collection_raises_keyerror` — 수집한 적 없는 컬렉션은 `KeyError`.
3. `test_mcp_search_handler_matches_cli_query_document_ids` — 같은 백엔드로 배선한
   `mcp.tools.search`가 CLI 질의와 같은 `document_id` 집합을 낸다(REST/CLI ↔ MCP 항등성).
4. `test_api_testclient_query_reaches_shared_tenant` — `rag_platform.api.app` 있으면: API 키를
   CLI와 같은 tenant_id로 등록 → `POST /v1/query` 200, 응답의 `tenant_id`/`collection_ids`가
   CLI와 같음(현재는 실 검색 미배선이라 `items == []`인 것까지 확인, §9 DEFERRED 1).
5. `test_cli_main_ingest_then_query_json_round_trip` — argparse `main(["ingest", ...])` →
   `main(["query", ..., "--format", "json"])`, stdout JSON 파싱 + cite_id 왕복.
6. `test_cli_main_query_unknown_collection_exits_nonzero` — 종료 코드 2.
7. `test_cli_profile_validate`(parametrize `lite`/`lite-dev`) — 통과 + `profile_hash` 출력.
8. `test_cli_serve_builds_expected_subprocess_argv` — `subprocess.run`을 모의해 `serve api`/
   `serve mcp`의 argv만 확인(실 서버 기동 없음).

## 8. 완료 기준

`uv run pytest -q tests/e2e/test_full_e2e.py` 9개 전부 통과(연속 2회 재실행 안정), `uv run ruff
check src/rag_platform/cli/main.py tests/e2e/test_full_e2e.py` 통과, `deploy/compose/
compose.lite.yaml`이 `yaml.safe_load`로 파싱 가능하고 서비스 4개(app/postgres/qdrant/valkey)를
포함.

## 9. 검증 계층·DEFERRED

1층(여기서 검증) — 위 테스트 파일, 모델·Docker·GPU·외부 네트워크 불필요(온디스크 로컬 Qdrant +
페이크 임베더, MCP는 인메모리 KV 커서 저장소).

- DEFERRED 1: `api/query.py`가 자신의 docstring대로 아직 `pipelines.query.run_query`의
  6-Protocol을 배선하지 않아(`_build_empty_context_pack` 스텁) CLI 질의와의 `document_id`
  동등성 비교는 할 수 없다 — `api/query.py`가 실 배선을 마친 뒤 배치 검증자(또는 후속 WP)가
  `test_api_testclient_query_reaches_shared_tenant`를 동등성 검사로 확장해야 한다.
- DEFERRED 2: `rag serve api|mcp`의 실제 서버 기동(포트 바인딩, uvicorn/`mcp` stdio 헬스체크)은
  장수명 프로세스라 이 스위트에서 실행하지 않는다(`test_cli_serve_builds_expected_subprocess_argv`
  는 `subprocess.run`을 모의해 argv만 확인) — `uvicorn`이 `pyproject.toml` 의존성에 아직 없다는
  점도 함께 남긴다(open_issues, `2b`류가 아니라 순수 의존성 공백).
- DEFERRED 3: `deploy/compose/compose.lite.yaml`의 실제 `docker compose config`/기동 검증은
  `needs_docker` — `tools/verify/run-deferred.sh`가 Docker 있는 머신에서 수행한다
  (`HANDOFF.md` §"Docker 재확인" 절차와 같은 모양).

결과: 통과 9 / xfail 0 / DEFERRED 3
