"""`GET /v1/jobs/{job_id}` — 잡 원장(인메모리 대역) 조회, `JobStatus` 계약 그대로 반환.

역할: 접수(`api.ingest`)가 쓰고 갱신하는 `JobStatus` 인스턴스를 `(tenant_id, job_id)` 스코프로
보관하는 `JobStore`와, 그 저장소를 읽어 `05-api/02-ingestion-api.md` §6.2 그대로의 응답을 돌려주는
라우터를 제공한다.
설계 근거: 바이블 §14(`GET /v1/jobs/{job_id}` → `JobStatus`)·§5.6(`JobStatus` 계약, `contracts/
job_status.py`가 정본)·§10.3 E1(API 인증); `05-api/02-ingestion-api.md` §6.2(200 `JobStatus`, `failed`·
`partial`도 200); §2.2 RBAC(다른 테넌트의 `job_id`는 거부).
구성: `JobStore` — `dict[(tenant_id, job_id), JobStatus]` 인메모리 원장 대역(`put`/`get`); `router` —
`GET /v1/jobs/{job_id}` 하나짜리 `APIRouter`.
불변식·주의: `rag_platform.testing.doubles.InMemoryLedger`를 쓰지 않는다 — import-linter 계약
`testing-not-in-production`(`rag_platform.api`는 `rag_platform.testing`을 임포트할 수 없다)과
충돌하기 때문이다(open_issues: 실 배포에서는 `rag_platform.ledger.Ledger`의 PostgreSQL 구현이
이 저장소를 대신해야 한다 — 그 프로토콜의 `JobRecord`는 이 응답이 필요로 하는 `progress`/`cost`/
시각 필드가 없어 그대로 쓸 수 없다). `ETag`/`If-None-Match` 304 캐싱은 이 WP 범위 밖(open_issues).
검증 계층: 1층(여기서 검증) — `tests/api/test_api.py`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from rag_platform.api.problems import ApiError
from rag_platform.security.security_context import authenticate, root_value

if TYPE_CHECKING:
    from rag_platform.contracts.job_status import JobStatus

__all__ = ["JobStore", "router"]

# Named so `raise ApiError(...)` never passes a bare string literal (ruff EM101).
_CODE_NOT_FOUND = "api.not_found"


@dataclass
class JobStore:
    """`(tenant_id, job_id)`-scoped in-memory `JobStatus` table (bible §13.1 RLS intent, approximated)."""

    _jobs: dict[tuple[str, str], JobStatus] = field(default_factory=dict)

    def put(self, job: JobStatus) -> None:
        """Insert or replace the row for `(job.tenant_id, job.job_id)`."""
        self._jobs[(root_value(job.tenant_id), root_value(job.job_id))] = job

    def get(self, tenant_id: str, job_id: str) -> JobStatus | None:
        """Return the row for `(tenant_id, job_id)`, or `None` if absent for this tenant."""
        return self._jobs.get((tenant_id, job_id))


router = APIRouter()


@router.get("/v1/jobs/{job_id}")
async def get_job(job_id: str, request: Request) -> JSONResponse:
    """`05-api/02-ingestion-api.md` §6.2: 200 `JobStatus`(`failed`·`partial`도 200), 없으면 404."""
    record = authenticate(request.app.state.api_keys, request.headers.get("authorization"))
    job = request.app.state.jobs.get(record.tenant_id, job_id)
    if job is None:
        raise ApiError(_CODE_NOT_FOUND, status=404, detail=f"/v1/jobs/{job_id}: resource not found")
    return JSONResponse(content=job.dump_contract())
