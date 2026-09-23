"""`POST /v1/ingest` — 202 접수, `Idempotency-Key` 필수, `LocalRunner` 백그라운드 실행.

역할: 수집 요청 본문(최소 부분집합 — 계약 `IngestRequest` 전체는 이 WP 읽기 예산 밖, open_issues)을
받아 `JobStatus`를 `queued`로 접수하고, 응답을 보낸 뒤 `orchestration.local.runner.LocalRunner`로
스테이지 1개짜리(`index`) 체인을 백그라운드 실행해 `running → succeeded|partial|failed`로 갱신한다.
설계 근거: 바이블 §14(`POST /v1/ingest` → `202 {job_id, status_url, events_url}`, `Idempotency-Key`
필수)·§11.1(`LocalRunner`, 비내구)·§10.3 E1·E2(SecurityContext 서버 주입); `05-api/02-ingestion-
api.md` §4(요청·응답·상태 코드)·§4.4(멱등성 의미론, draft-ietf-httpapi-idempotency-key-header-07).
구성: `IdempotencyStore` — `(tenant_id, key)` → 지문·이전 응답 인메모리 대역; `_StubIndexStage` —
`sdk.stage.Stage` 최소 구현(fetch~embed 생략, `index` 1단만; open_issues); `_InMemoryStageStore` —
`LocalRunner`가 요구하는 `_KeyedStore` 구조의 인메모리 아티팩트 저장소; `router` — `POST /v1/ingest`.
불변식·주의: `IngestRequest` 계약 전체 검증(ACL·`profile_overrides`·콜백 등)은 하지 않는다 —
`collection_id`/`source_uri`만 필수로 받는 축소 본문이다(open_issues). `document_id`/`dedup_policy`
기반 재잡 대기열(`waiting_for`)도 구현하지 않는다 — 매 요청이 새 `document_id`를 받는다
(open_issues). `fetch`~`embed` 실 어댑터 배선은 `orchestration/context.py`(아직 없음, 06 §12
`ArtifactRef → Pydantic` 검증 지점)가 갖춰진 뒤의 몫이라 `index` 스텁 1단만 실행한다(open_issues).
검증 계층: 1층(여기서 검증) — `tests/api/test_api.py`. `needs_docker`/`needs_model` 해당 없음(임베딩
없음, 인메모리 저장소만).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, BackgroundTasks, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from ulid import ULID

from rag_platform.api.problems import ApiError
from rag_platform.contracts.capabilities import Capabilities
from rag_platform.contracts.job_status import JobStatus
from rag_platform.orchestration.local.runner import LocalRunner, StageSpec
from rag_platform.profiles.loader import canonical_json
from rag_platform.sdk.context import LocalContext
from rag_platform.sdk.hashing import hash_of
from rag_platform.sdk.policy import StagePolicy
from rag_platform.sdk.stage import StageError
from rag_platform.security.security_context import (
    AuthorizationError,
    authenticate,
    derive_security_context,
    format_datetime,
    root_value,
)

if TYPE_CHECKING:
    from rag_platform.api.jobs import JobStore

__all__ = ["IdempotencyStore", "router"]

# 05-api/02 §4.4: visible ASCII, 1..255 (draft-ietf-httpapi-idempotency-key-header-07).
_IDEMPOTENCY_KEY_RE = re.compile(r"^[!-~]{1,255}$")
_TOTAL_STAGES = 1  # `index` 스텁 1단만(open_issues); 실 체인은 fetch~publish 8~9단(바이블 §4.2).

# `ErrorCodeCatalog` spellings this module raises (named, not inline, so `raise ApiError(...)` never
# passes a bare string literal — ruff EM101 flags that as if it were a free-text exception message).
_CODE_CONTRACT_VIOLATION = "contract.violation"
_CODE_IDEMPOTENCY_MISMATCH = "api.idempotency_payload_mismatch"
_CODE_STUB_INDEX_FAILURE = "index.security_fields_missing"


@dataclass(frozen=True)
class _IdempotencyRecord:
    """One `(tenant_id, key)` row: the request fingerprint and the replayed 202 body."""

    fingerprint: str
    response_body: dict[str, Any]
    status_url: str


@dataclass
class IdempotencyStore:
    """`(tenant_id, key)`-scoped in-memory idempotency table (05-api/02 §4.4; PostgreSQL in production)."""

    _records: dict[tuple[str, str], _IdempotencyRecord] = field(default_factory=dict)

    def get(self, tenant_id: str, key: str) -> _IdempotencyRecord | None:
        """Return the stored record for `(tenant_id, key)`, or `None` if this key is new."""
        return self._records.get((tenant_id, key))

    def put(self, tenant_id: str, key: str, record: _IdempotencyRecord) -> None:
        """Store the accepted record for `(tenant_id, key)`."""
        self._records[(tenant_id, key)] = record


class _StubStageConfig(BaseModel):
    """Empty `config_schema` for `_StubIndexStage` (bible §4.1 `Stage` protocol member)."""


@dataclass
class _ArtifactRefStub:
    """Opaque in-memory object-store key; `LocalRunner` never inspects its shape (bible §11.1)."""

    key: str


@dataclass
class _InMemoryStageStore:
    """Minimal `_KeyedStore` (`orchestration.local.runner`) backing `LocalRunner` for this stub chain."""

    _objects: dict[str, tuple[bytes, str]] = field(default_factory=dict)
    _stage_cache: dict[tuple[str, str, str], str] = field(default_factory=dict)
    _counter: int = 0

    async def put_artifact(
        self, data: bytes, *, tenant_id: str, schema_type: str, media_type: str, stage_key: str | None = None
    ) -> _ArtifactRefStub:
        """Store `data` (and its `media_type`) under a fresh in-process key; return the opaque ref."""
        self._counter += 1
        key = f"{tenant_id}/{schema_type}/{self._counter}"
        self._objects[key] = (data, media_type)
        if stage_key is not None:
            self._stage_cache[(tenant_id, schema_type, stage_key)] = key
        return _ArtifactRefStub(key=key)

    async def get_bytes(self, ref: _ArtifactRefStub) -> bytes:
        """Return the bytes previously stored under `ref`."""
        return self._objects[ref.key][0]

    async def lookup_stage_key(self, tenant_id: str, schema_type: str, stage_key: str) -> _ArtifactRefStub | None:
        """Return the cached ref for `stage_key`, or `None` on a cache miss."""
        key = self._stage_cache.get((tenant_id, schema_type, stage_key))
        return None if key is None else _ArtifactRefStub(key=key)


class _WhitespaceTokenCounter:
    """Deterministic `sdk.ports.TokenCounter` stub — no model weights, whitespace split only."""

    tokenizer_id = "stub:whitespace"

    def count(self, text: str) -> int:
        """Return the whitespace-token count of `text`."""
        return len(text.split())


class _StubIndexStage:
    """`Stage[bytes, bytes]` placeholder for the whole `fetch..embed` chain (open_issues).

    Real adapter wiring needs `orchestration/context.py`'s `ArtifactRef -> Pydantic` boundary
    (not yet built, per `orchestration.local.runner`'s own module docstring) plus a profile ->
    `StagePolicy` resolver this WP's target-file list does not include. This stage instead proves
    the `LocalRunner` integration point end to end: it echoes a deterministic "committed" summary,
    or raises a non-retryable `StageError` when the caller opts into the `stub-fail://` sentinel
    (used by `tests/api/test_api.py` to exercise the `failed` job path without a real backend).
    """

    plugin_id = "index.api_stub"
    config_schema: type[BaseModel] = _StubStageConfig
    requires_lineage: tuple[str, ...] = ()

    def capabilities(self) -> Capabilities:
        """Return this stub's declared capabilities (bible §5.3 `Capabilities`)."""
        return Capabilities.model_validate(
            {"isolation_modes": ["in_process"], "supports_resumable": False, "contracts_compat": ">=1.0,<2.0"}
        )

    def fingerprint(self) -> str:
        """Return a fixed producer fingerprint (no config, no plugin chain)."""
        return hash_of("producer", self.plugin_id, "1.0.0")

    async def run(self, inp: bytes, ctx: Any) -> bytes:
        """Echo a deterministic commit summary, or raise on the `stub-fail://` test sentinel."""
        body = json.loads(inp.decode("utf-8"))
        if str(body.get("source_uri", "")).startswith("stub-fail://"):
            msg = "stub-fail:// sentinel: simulated index failure (test-only trigger)"
            raise StageError(_CODE_STUB_INDEX_FAILURE, stage="index", detail=msg)
        summary = {"committed_at": ctx.now().isoformat(), "status": "committed"}
        return json.dumps(summary).encode("utf-8")


router = APIRouter()


def _new_ulid() -> str:
    """Issue a fresh ULID string (bible §6.1; shell/api is the only layer allowed entropy)."""
    return str(ULID())


def _build_job(
    *,
    job_id: str,
    tenant_id: str,
    collection_id: str,
    document_id: str,
    request_id: str,
    idempotency_key: str,
    priority: int,
    now: datetime,
    status_url: str,
    events_url: str,
) -> JobStatus:
    """Build the initial `queued` `JobStatus` a freshly accepted ingest job starts as."""
    return JobStatus.model_validate(
        {
            "schema_version": "1.0.0",
            "schema_type": "JobStatus",
            "job_id": job_id,
            "tenant_id": tenant_id,
            "collection_id": collection_id,
            "kind": "ingest_document",
            "state": "queued",
            "stage": None,
            "progress": {"done": 0, "total": _TOTAL_STAGES, "unit": "stage"},
            "attempts": 0,
            "workflow_run_id": None,
            "workflow_id": None,
            "idempotency_key": idempotency_key,
            "request_id": request_id,
            "document_id": document_id,
            "index_commit_id": None,
            "from_stage": None,
            "last_error": None,
            "degraded": [],
            "cost": {"llm_tokens_in": 0, "llm_tokens_out": 0, "cost_usd": 0.0, "gpu_seconds": 0.0},
            "priority": priority,
            "status_url": status_url,
            "events_url": events_url,
            "created_at": format_datetime(now),
            "started_at": None,
            "updated_at": format_datetime(now),
            "finished_at": None,
            "deadline_at": None,
        }
    )


def _update_job(job: JobStatus, **updates: Any) -> JobStatus:
    """Return `job` with `updates` merged in, revalidated.

    Safer than `model_copy`: every contract field wraps a `RootModel` (e.g. `Ulid`/`DateTime`) that
    `model_copy(update=...)` would silently leave holding a bare `str` instead of coercing, breaking
    `dump_contract()` later; round-tripping through `dump_contract()` + `model_validate` re-coerces
    everything.
    """
    data = job.dump_contract()
    data.update(updates)
    return JobStatus.model_validate(data)


async def _run_ingest_job(job_store: JobStore, tenant_id: str, job_id: str, body: dict[str, Any]) -> None:
    """Run the `_StubIndexStage` chain through `LocalRunner` and update the job's terminal state."""
    job = job_store.get(tenant_id, job_id)
    if job is None:  # pragma: no cover - defensive, job is always written before scheduling
        return
    now = datetime.now(UTC)
    job = _update_job(
        job,
        state="running",
        stage="index",
        attempts=1,
        started_at=format_datetime(now),
        updated_at=format_datetime(now),
    )
    job_store.put(job)

    store = _InMemoryStageStore()
    local_ctx = LocalContext(
        tenant_id=tenant_id,
        collection_id=root_value(job.collection_id),
        profile_hash="api-stub-v1",
        trace_id=_new_ulid(),
        # `_InMemoryStageStore` only backs the `_KeyedStore` surface (`put_artifact`) `LocalRunner`
        # needs for this index-only stub chain; `LocalContext.store`'s `_BackingStore` surface
        # (`put_source`/`put_derived`) is never exercised because `_StubIndexStage.run` does not
        # touch `ctx.artifacts` (open_issues: real `fetch`~`embed` wiring needs `orchestration/
        # context.py`, not yet built).
        store=store,  # type: ignore[arg-type]
        clock=lambda: datetime.now(UTC),
    )
    policy = StagePolicy(
        task_queue="ingest-index-stub",
        start_to_close=timedelta(seconds=30),
        heartbeat=None,
        max_attempts=1,
        resumable=False,
    )
    runner = LocalRunner(context=local_ctx, store=store, token_counter=_WhitespaceTokenCounter())
    spec = StageSpec(name="index", stage=_StubIndexStage(), policy=policy, schema_type="IndexCommit")
    result = await runner.run(
        [spec], json.dumps(body).encode("utf-8"), document_id=root_value(job.document_id), job_id=job_id
    )

    now = datetime.now(UTC)
    if result.status == "succeeded":
        job = _update_job(
            job,
            state="succeeded",
            progress={"done": _TOTAL_STAGES, "total": _TOTAL_STAGES, "unit": "stage"},
            index_commit_id=_new_ulid(),
            finished_at=format_datetime(now),
            updated_at=format_datetime(now),
        )
    else:
        last_error = result.errors[-1] if result.errors else None
        state = "partial" if result.status == "partial" else "failed"
        job = _update_job(
            job,
            state=state,
            last_error=None if last_error is None else last_error.to_payload(),
            finished_at=format_datetime(now),
            updated_at=format_datetime(now),
        )
    job_store.put(job)


def _reject_server_assigned_fields(body: dict[str, Any]) -> None:
    """05-api/02 §4.1: `tenant_id` (422) and `request_id` (400) are server-assigned, never client input."""
    if "tenant_id" in body:
        raise ApiError(_CODE_CONTRACT_VIOLATION, status=422, detail="/tenant_id: server-assigned, must not be sent")
    if "request_id" in body:
        raise ApiError(_CODE_CONTRACT_VIOLATION, status=400, detail="/request_id: server-assigned, must not be sent")


def _require_string_field(body: dict[str, Any], name: str) -> str:
    """Return `body[name]` as a non-empty string, or raise 400 `contract.violation`."""
    value = body.get(name)
    if not isinstance(value, str) or not value:
        raise ApiError(_CODE_CONTRACT_VIOLATION, status=400, detail=f"/{name}: required non-empty string")
    return value


@router.post("/v1/ingest")
async def post_ingest(request: Request, background_tasks: BackgroundTasks) -> JSONResponse:
    """`05-api/02-ingestion-api.md` §4: 202 접수, `Idempotency-Key` 필수, `LocalRunner` 백그라운드 실행."""
    idempotency_key = request.headers.get("idempotency-key")
    if idempotency_key is None:
        raise ApiError(_CODE_CONTRACT_VIOLATION, status=400, detail="Idempotency-Key header is required")
    if not _IDEMPOTENCY_KEY_RE.match(idempotency_key):
        detail = "Idempotency-Key must be visible ASCII, 1..255 chars"
        raise ApiError(_CODE_CONTRACT_VIOLATION, status=400, detail=detail)

    record = authenticate(request.app.state.api_keys, request.headers.get("authorization"))

    try:
        body = await request.json()
    except ValueError as exc:
        raise ApiError(_CODE_CONTRACT_VIOLATION, status=400, detail=f"invalid JSON body: {exc}") from exc
    if not isinstance(body, dict):
        raise ApiError(_CODE_CONTRACT_VIOLATION, status=400, detail="request body must be a JSON object")

    _reject_server_assigned_fields(body)
    collection_id = _require_string_field(body, "collection_id")
    _require_string_field(body, "source_uri")
    priority = body.get("priority", 5)
    if not isinstance(priority, int) or not 0 <= priority <= 9:  # noqa: PLR2004 - bible §4.2 `priority` 0..9
        raise ApiError(_CODE_CONTRACT_VIOLATION, status=400, detail="/priority: integer 0..9")

    security = derive_security_context(record, requested_collection_ids=[collection_id], now=datetime.now(UTC))
    if collection_id not in [root_value(cid) for cid in security.collection_ids]:
        msg = "collection is outside the allowed set for this API key"
        raise AuthorizationError(msg)

    idempotency_store: IdempotencyStore = request.app.state.idempotency
    fingerprint = hash_of("idem", "/v1/ingest", canonical_json(body))
    existing = idempotency_store.get(record.tenant_id, idempotency_key)
    if existing is not None:
        if existing.fingerprint != fingerprint:
            raise ApiError(
                _CODE_IDEMPOTENCY_MISMATCH, status=422, detail="Idempotency-Key reused with a different body"
            )
        return JSONResponse(status_code=200, content=existing.response_body, headers={"Location": existing.status_url})

    job_id = _new_ulid()
    request_id = _new_ulid()
    document_id = _new_ulid()
    now = datetime.now(UTC)
    status_url = str(request.url_for("get_job", job_id=job_id))
    events_url = f"{status_url}/events"
    job = _build_job(
        job_id=job_id,
        tenant_id=record.tenant_id,
        collection_id=collection_id,
        document_id=document_id,
        request_id=request_id,
        idempotency_key=idempotency_key,
        priority=priority,
        now=now,
        status_url=status_url,
        events_url=events_url,
    )
    job_store: JobStore = request.app.state.jobs
    job_store.put(job)

    accepted_body = {
        "job_id": job_id,
        "request_id": request_id,
        "document_id": document_id,
        "status_url": status_url,
        "events_url": events_url,
    }
    idempotency_store.put(
        record.tenant_id,
        idempotency_key,
        _IdempotencyRecord(fingerprint=fingerprint, response_body=accepted_body, status_url=status_url),
    )

    background_tasks.add_task(_run_ingest_job, job_store, record.tenant_id, job_id, body)
    return JSONResponse(status_code=202, content=accepted_body, headers={"Location": status_url})
