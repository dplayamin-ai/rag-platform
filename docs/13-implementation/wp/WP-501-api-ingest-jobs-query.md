---
title: "WP-501 API — 수집 접수·잡 조회·질의·렌더"
status: active
version: 0.1.0
---

# WP-501 API — 수집 접수·잡 조회·질의·렌더 (F5-01, api-ingest-jobs-query)

## 0. 실행 배경(병렬 배치 주의)

F5 배치는 여러 에이전트가 `api`/`mcp`/`cli`를 병렬로 만든다. 이 WP를 쓰는 시점에
`retrieval/*`(F4 실 모듈: `planner`/`channels`/`fusion`/`hydrate`/`postprocess.*`/`pack.packer`)와
`render/*`(F4 렌더러)는 이 WP의 읽기 예산 밖이라 배선하지 않는다 — `pipelines/query.py` 자신의
독스트링이 이미 "실 모듈 배선은 F5 또는 F4 배치 검증자의 몫"이라 적어 둔 대로, 이 WP는 API 표면
(요청 검증·`SecurityContext` 서버 주입·RFC 9457 오류·`LocalRunner` 배선)만 완성하고 실제 검색
결과는 항상 빈 `ContextPack`(`route=no_retrieval` 모양)으로 둔다. `orchestration/context.py`(실
`ArtifactRef → Pydantic` 검증 셸)도 아직 없어 수집 파이프라인의 `fetch`~`embed` 실 어댑터 배선 대신
`index` 스텁 1단만 `LocalRunner`로 실행한다. 두 갭 모두 §9 DEFERRED와 open_issues에 기록한다.

## 1. 목표

1. `POST /v1/ingest` — `Idempotency-Key` 필수, 202 `{job_id, request_id, document_id, status_url,
   events_url}`, `SecurityContext` 서버 주입, `orchestration.local.runner.LocalRunner`로 백그라운드
   실행해 잡을 `queued → running → succeeded|partial|failed`로 갱신한다(바이블 §14, §11.1).
2. `GET /v1/jobs/{job_id}` — 인메모리 원장에서 `JobStatus` 계약 그대로 반환, 테넌트 스코프.
3. `POST /v1/query` — `QueryRequest` 계약 검증(서버 발급·보안 필드 거부, 컬렉션 인가) 후
   `{context_pack, rendered?}` 반환.
4. `POST /v1/render` — `{pack_id | context_pack, renderer, options}` → `RenderedContext`.
5. 모든 오류를 RFC 9457 `ProblemDetails`(`application/problem+json`)로 통일한다.

## 2. 파일

- `src/rag_platform/api/app.py`
- `src/rag_platform/api/ingest.py`
- `src/rag_platform/api/jobs.py`
- `src/rag_platform/api/query.py`
- `src/rag_platform/api/problems.py`
- `src/rag_platform/security/security_context.py`
- `tests/api/test_api.py`

## 3. 시그니처

```python
# security/security_context.py
@dataclass(frozen=True)
class ApiKeyRecord:
    tenant_id: str; subject: str; roles: tuple[str, ...] = ()
    allowed_collection_ids: tuple[str, ...] | None = None

class ApiKeyRegistry:
    def register(self, api_key: str, *, tenant_id: str, subject: str,
                 roles: Sequence[str] = (), allowed_collection_ids: Sequence[str] | None = None) -> None: ...
    def resolve(self, api_key: str) -> ApiKeyRecord | None: ...

def authenticate(registry: ApiKeyRegistry, authorization_header: str | None) -> ApiKeyRecord: ...
def derive_security_context(record: ApiKeyRecord, *, requested_collection_ids: Sequence[str],
                             now: datetime, policy_version: str = "static-api-key-v1") -> SecurityContext: ...
def root_value(value: object) -> str: ...  # RootModel[str] 계약 스칼라 → 평문 문자열
def format_datetime(value: datetime) -> str: ...  # 바이블 §6.3 DateTime 정본 표기

# api/problems.py
class ApiError(Exception):
    def __init__(self, code: str, *, status: int, detail: str | None = None, instance: str | None = None,
                 retryable: bool = False, retry_after: int | None = None) -> None: ...
def register_exception_handlers(app: FastAPI) -> None: ...

# api/jobs.py
class JobStore:
    def put(self, job: JobStatus) -> None: ...
    def get(self, tenant_id: str, job_id: str) -> JobStatus | None: ...
router: APIRouter  # GET /v1/jobs/{job_id}

# api/ingest.py
class IdempotencyStore: ...  # (tenant_id, key) -> fingerprint + 202 응답 재생
router: APIRouter  # POST /v1/ingest

# api/query.py
router: APIRouter  # POST /v1/query, POST /v1/render

# api/app.py
def create_app() -> FastAPI: ...
```

## 4. 입출력 계약 발췌(정본 철자)

- `JobStatus`(`contracts/job_status.py`): `job_id`/`tenant_id`/`collection_id`/`kind`/`state`/
  `stage`(nullable)/`progress{done,total,unit}`/`attempts`/`workflow_run_id`(null)/`workflow_id`
  (null)/`idempotency_key`/`request_id`/`document_id`/`index_commit_id`/`last_error`/`degraded`/
  `cost{llm_tokens_in,llm_tokens_out,cost_usd,gpu_seconds}`/`priority`/`status_url`/`events_url`/
  `created_at`/`started_at`/`updated_at`/`finished_at`/`deadline_at`. `state ∈ {queued, running,
  succeeded, partial, failed, cancelling, cancelled}`(`common_types.JobState`).
- `common_types.SecurityContext`: `tenant_id, principals, collection_ids, as_of,
  classification_max, policy_version, auth_method, visible_set` — 서버 주입, 요청 본문 무시
  (ADR-0027).
- `common_types.ProblemDetails`: `type=urn:rag:error:{code}, title, status, detail?, instance?,
  code, retryable, trace_id(hex32), errors?, retry_after?, request_id?`. `code`는
  `common_types.ErrorCodeCatalog` 철자(예 `contract.violation`, `auth.unauthenticated`,
  `auth.forbidden`, `api.not_found`, `api.idempotency_payload_mismatch`,
  `plan.collection_forbidden`).
- `query_request.QueryRequest`: `schema_version, query_id(서버 발급, readOnly), query,
  collection_ids, conversation?, filters?, top_k?, mode?, retrieval_variant?, strategy_hint?,
  target_model?, max_context_tokens?, renderer?, ordering_strategy?, include_parents?,
  response_format?, session_id?, exclude_ids?, cursor?, budget?, explain?, requested_at`. 본문에
  `tenant_id`·`as_of`·`security_context`·`principals`·`visible_set`·`classification_max`가 있으면
  거부(05-api/03 §3.1).
- `contracts/context_pack.py`의 `ContextPack`·`contracts/rendered_context.py`의 `RenderedContext`
  전체 트리(중첩 `Budget`/`Ordering`/`Sufficiency`/`RedactionSummary`/`RenderHints`/`Diagnostics`
  등)는 이 WP 읽기 예산 밖이라 문서에 옮기지 않는다 — `_build_empty_context_pack`/`_build_rendered`
  (`api/query.py`)가 `model_validate` 호출 전 파이썬 런타임으로 `model_fields`를 조회해 정확한
  이름·이넘 값을 확인했다(계약 손편집 없음, 코드만 작성).

## 5. 불변식·금지

- `pipelines`·`retrieval`·`render`·`adapters`·`sdk`·`contracts`는 `fastapi`/`rag_platform.
  orchestration`을 임포트하지 않는다(import-linter `pipelines-orchestrator-neutral`) — 이 WP는
  위반하지 않는다(`api`만 `orchestration.local.runner`를 임포트).
- `rag_platform.api`는 `rag_platform.testing`을 임포트하지 않는다(import-linter
  `testing-not-in-production`) — `testing.doubles.InMemoryLedger` 대신 `api.jobs.JobStore`(자체
  인메모리 대역)를 새로 만든 이유가 이것이다(open_issues).
- 계약 인스턴스는 `model_validate(dict)`로만 만든다 — `model_copy(update=...)`로 `RootModel` 필드
  (`Ulid`/`DateTime`/...)에 평문 `str`을 직접 넣지 않는다(`_update_job`이 `dump_contract()` +
  `model_validate` 왕복으로 이를 보장).
- `str(root_model_instance)`는 `"root='...'"` 디버그 표현을 반환하므로 절대 쓰지 않는다 —
  `security_context.root_value()`만 쓴다.
- SecurityContext는 서버가 주입한다 — `POST /v1/ingest`의 `collection_id`, `POST /v1/query`의
  `collection_ids`는 `derive_security_context`의 교집합 결과로만 인가 판정한다.
- 이모지·커밋 금지. 지정 파일만 쓴다.

## 6. 단계

1. `security/security_context.py`: `ApiKeyRecord`/`ApiKeyRegistry`/`authenticate`/
   `derive_security_context`/`root_value`/`format_datetime`/`AuthenticationError`/
   `AuthorizationError`.
2. `api/problems.py`: `ApiError` + `register_exception_handlers`(5개 처리기).
3. `api/jobs.py`: `JobStore` + `GET /v1/jobs/{job_id}`.
4. `api/ingest.py`: `IdempotencyStore` + `_StubIndexStage`/`_InMemoryStageStore` + `POST /v1/ingest`
   (`LocalRunner` 백그라운드 실행).
5. `api/query.py`: `POST /v1/query`/`POST /v1/render`(빈 `ContextPack` + 자리표시자 렌더).
6. `api/app.py`: `create_app()` 조립 + 상태 배선.
7. `tests/api/test_api.py`: 25개 케이스(§7).

## 7. 테스트

- `tests/api/test_api.py`
  - `TestIngestAccepted` — 202 접수 → `LocalRunner` 성공 경로(`succeeded`), `stub-fail://` 트리거로
    실패 경로(`failed` + `last_error.code`).
  - `TestIngestIdempotency` — 헤더 부재(400), 재전송 동일 본문(200 동일 `job_id`), 동일 키·다른
    본문(422 `api.idempotency_payload_mismatch`).
  - `TestIngestValidation` — 서버 발급 `tenant_id`(422)/`request_id`(400) 거부, `collection_id`
    누락(400), `priority` 범위 밖(400).
  - `TestIngestAuthAndTenancy` — 인증 헤더 부재(401), 미등록 키(401), 허용 밖 컬렉션(403
    `auth.forbidden`).
  - `TestJobsLookup` — 알 수 없는 `job_id`(404), 다른 테넌트 격리(404).
  - `TestQuery` — 성공 경로(`context_pack`+`rendered`), `pack_only`(`rendered` 생략), 서버 발급
    `query_id` 거부(400), 필수 필드 누락(400), 컬렉션 인가 실패(403
    `plan.collection_forbidden`), 인증 부재(401).
  - `TestRender` — `pack_id` 경로, 인라인 `context_pack` 경로, 알 수 없는 `pack_id`(404), 상호배타
    위반(400), 잘못된 `renderer`(400).

## 8. 완료 기준

`uv run pytest -q tests/api/test_api.py` 25개 전부 통과(1회차 통과, 재시도 불필요).
`uv run ruff check` 대상 7개 파일 통과. `uv run lint-imports`(6개 계약) 통과 확인.

## 9. 검증 계층·DEFERRED

1층(여기서 검증) — 위 테스트 파일, `TestClient` in-process, Docker·모델·GPU·외부 네트워크 없음.

`# DEFERRED: 실 F4 검색 파이프라인(retrieval.planner/channels/fusion/hydrate/postprocess.*/
pack.packer + render.markdown/anthropic_search_result)을 pipelines.query.QueryPipelineDeps에
묶어 POST /v1/query·POST /v1/render가 실제 결과를 돌려주게 한다 — 이 WP는 항상 items=[]인
route=no_retrieval 모양만 반환한다(F5 후속 또는 F4 배치 검증자).`

`# DEFERRED: orchestration/context.py(ArtifactRef -> Pydantic 검증 셸)와 profile -> StagePolicy
해석기가 갖춰지면 POST /v1/ingest의 index 스텁 1단을 fetch~publish 실 어댑터 체인으로 교체한다
(adapters.fetch/parse/normalize/chunk/enrich/embed/index는 이미 존재 — 배선만 남음).`

`# DEFERRED: GET /v1/jobs(목록)·GET /v1/jobs/{job_id}/events(SSE)·POST /v1/ingest/batch·ETag/
If-None-Match 304·레이트리밋(E3)·Cedar 실 인가(E2)·OIDC JWT(E1)는 이 WP 범위 밖 — API 키 헤더 →
정적 레지스트리 조회로 근사했다.`

결과: 통과 25 / xfail 0 / DEFERRED 3(F4 검색 파이프라인 배선, 수집 실 어댑터 배선, 잡 목록·SSE·배치·
레이트리밋·실 Cedar·OIDC)
