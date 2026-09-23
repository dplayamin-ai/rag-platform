"""`create_app()` — FastAPI 앱 조립: 라우터·오류 처리기·요청 스코프 상태(state) 배선.

역할: `api.ingest`/`api.jobs`/`api.query`의 `APIRouter`를 하나의 `FastAPI` 인스턴스에 묶고,
`api.problems.register_exception_handlers`로 RFC 9457 오류 처리기를 걸고, 각 라우터가 `request.app.
state`로 읽는 인메모리 대역(`ApiKeyRegistry`/`JobStore`/`IdempotencyStore`/팩 캐시)을 초기화한다.
설계 근거: 바이블 §14(API 표면 정본)·§12(레이어 지도 — `api`는 최상위 계층, `orchestration`·
`security`·`profiles`·`pipelines`·`sdk`·`contracts`를 자유롭게 임포트); ADR-0018(REST·SSE·MCP,
no gRPC, RFC 9457); `docs/13-implementation/wp/WP-501-api-ingest-jobs-query.md`(이 WP).
구성: `create_app()` — 새 `FastAPI` 인스턴스를 만들고 위 배선을 마친 뒤 반환(테스트마다 격리된
상태를 원하면 이 함수를 다시 호출한다); `app` — `uvicorn rag_platform.api.app:app` 같은 프로세스
진입점용 모듈 수준 인스턴스(테스트는 `create_app()`을 직접 써서 상태를 공유하지 않는다).
불변식·주의: 이 모듈과 하위 라우터 모두 `rag_platform.testing`을 임포트하지 않는다(import-linter
`testing-not-in-production`). `POST /v1/ingest/batch`·`GET /v1/jobs`·`GET /v1/jobs/{job_id}/events`
(SSE)·`/healthz`·`/readyz`·`/metrics`는 이 WP 대상이 아니다(open_issues) — 바이블 §14 전체 표면 중
지시된 4개 엔드포인트만 배선한다.
검증 계층: 1층(여기서 검증) — `tests/api/test_api.py`(`TestClient(create_app())`).
"""

from __future__ import annotations

from fastapi import FastAPI

from rag_platform.api import ingest, jobs, query
from rag_platform.api.problems import register_exception_handlers
from rag_platform.security.security_context import ApiKeyRegistry

__all__ = ["app", "create_app"]


def create_app() -> FastAPI:
    """Build a fresh, self-contained `FastAPI` app (own registries/stores — no shared state)."""
    fastapi_app = FastAPI(title="RAG Platform API", version="1.0.0")
    fastapi_app.state.api_keys = ApiKeyRegistry()
    fastapi_app.state.jobs = jobs.JobStore()
    fastapi_app.state.idempotency = ingest.IdempotencyStore()
    fastapi_app.state.pack_cache = {}

    fastapi_app.include_router(ingest.router)
    fastapi_app.include_router(jobs.router)
    fastapi_app.include_router(query.router)
    register_exception_handlers(fastapi_app)
    return fastapi_app


app = create_app()
