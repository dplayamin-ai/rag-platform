"""`PipelineContext` / `StageContext` protocols and the `LocalContext` runtime helper.

Canon: design bible §11.1 ("two runners, one definition"), §4.1 (`StageContext` members);
ADR-0003 (orchestrator-neutral pipeline, non-durable `LocalRunner`);
docs/04-pipelines/01-pipeline-framework.md §3.1 (`StageContext` member table), §4.1
(`PipelineContext`/`QueryContext`).

`sdk` sits at the bottom of the layer stack (bible §12: `contracts ← sdk ← plugins|adapters|...`)
and must not import `storage`, `ledger`, `profiles` or `orchestration`. Where this module needs an
artifact-store-shaped collaborator (`LocalContext.store`, `DerivedArtifacts`'s backing object) it
declares a small structural protocol locally instead of importing `rag_platform.storage`; any
object with matching methods (for example `storage.artifact_store.FileArtifactStore`) satisfies it
by structural typing, no inheritance required.

`LocalContext.clock` has no default: `datetime.now(UTC)` is banned everywhere except the
shell/api layer (ruff banned-api, 10-development/03 §10.1); the caller assembling `LocalContext`
(the shell, e.g. `orchestration.local.runner`, or a test) supplies the real clock explicitly.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping
    from datetime import datetime, timedelta

    from rag_platform.contracts.common import ArtifactRef, CloudEventEnvelope  # type: ignore[import-not-found]
    from rag_platform.sdk.policy import StagePolicy
    from rag_platform.sdk.ports import KoreanAnalyzer, TokenCounter

__all__ = [
    "DerivedArtifacts",
    "LocalContext",
    "PipelineContext",
    "SecretsRef",
    "StageContext",
    "TenantBoundArtifacts",
]


@runtime_checkable
class DerivedArtifacts(Protocol):
    """Bible §4.1 (1.3.0, AM-27) `ctx.artifacts`: a tenant-bound, write-only derived-artifact port.

    No `get`/`exists`/arbitrary `tenant_id` argument: a stage can neither read a contract artifact
    back nor address another tenant's key space (E5, E17). Reads happen only through `ctx.lineage`.
    """

    async def put_source(self, data: bytes, *, media_type: str) -> ArtifactRef:
        """Store envelope-free original bytes for the bound tenant."""
        ...

    async def put_derived(self, data: bytes, *, kind: str, ext: str, media_type: str) -> ArtifactRef:
        """Store an envelope-free derived byte object for the bound tenant."""
        ...


@runtime_checkable
class _BackingStore(Protocol):
    """Structural shape `TenantBoundArtifacts` needs from a full `ArtifactStore` (storage layer)."""

    async def put_source(self, data: bytes, *, tenant_id: str, media_type: str) -> ArtifactRef:
        """Store envelope-free original bytes for `tenant_id`."""
        ...

    async def put_derived(self, data: bytes, *, tenant_id: str, kind: str, ext: str, media_type: str) -> ArtifactRef:
        """Store an envelope-free derived byte object for `tenant_id`."""
        ...


@dataclass(frozen=True)
class TenantBoundArtifacts:
    """Concrete `DerivedArtifacts`: binds `tenant_id` over a full `ArtifactStore`-shaped backend."""

    store: _BackingStore
    tenant_id: str

    async def put_source(self, data: bytes, *, media_type: str) -> ArtifactRef:
        """Store envelope-free original bytes under the bound `tenant_id`."""
        return await self.store.put_source(data, tenant_id=self.tenant_id, media_type=media_type)

    async def put_derived(self, data: bytes, *, kind: str, ext: str, media_type: str) -> ArtifactRef:
        """Store an envelope-free derived byte object under the bound `tenant_id`."""
        return await self.store.put_derived(data, tenant_id=self.tenant_id, kind=kind, ext=ext, media_type=media_type)


@dataclass(frozen=True)
class SecretsRef:
    """References only, never raw secret values (bible §6.6; pipeline-framework §3.2 `secrets` row).

    Stages never see this; the shell/adapters resolve a `credentials_ref` string to an opaque
    handle through :meth:`resolve`. The default implementation is a closure over a mapping supplied
    by the caller (e.g. tests inject a fake), never environment variables or files read here.
    """

    resolver: Callable[[str], str] = field(default=lambda ref: ref)

    def resolve(self, credentials_ref: str) -> str:
        """Resolve an opaque reference; never returns a value the caller did not already hold."""
        return self.resolver(credentials_ref)


@runtime_checkable
class PipelineContext(Protocol):
    """Bible §11.1 / ADR-0003, 4 members. Pipeline definitions depend on this only."""

    async def run(self, stage: str, inp_ref: ArtifactRef, out_type: type[Any], policy: StagePolicy) -> ArtifactRef:
        """Run one named stage over `inp_ref` under `policy`; return the output `ArtifactRef`."""
        ...

    async def emit(self, event: CloudEventEnvelope) -> None:
        """Publish a domain event (outbox in Temporal mode, a direct log call in local mode)."""
        ...

    def now(self) -> datetime:
        """Return the current time (Temporal: activity-start time; local: wall clock UTC)."""
        ...

    async def sleep(self, d: timedelta) -> None:
        """Suspend for `d` (Temporal: durable timer; local: `asyncio.sleep`)."""
        ...


@runtime_checkable
class StageContext(Protocol):
    """pipeline-framework.md §3.1 member table (subset realized by `LocalContext`, ingest side).

    `security`/`plan`/`token_counters`/`analyzer`/`substages` are declared for stage-facing type
    compatibility; `LocalContext` fills the ingest-only subset it needs and leaves the query-only
    members (`security`, `plan`) `None` (bible §4.1: "수집 측은 None").
    """

    tenant_id: str
    collection_id: str | None
    document_id: str | None
    job_id: str | None
    trace_id: str
    profile_hash: str
    plan: Any | None  # QueryPlan | None (query side only)
    token_counter: TokenCounter
    analyzer: KoreanAnalyzer | None
    lineage: Mapping[str, Any]
    artifacts: DerivedArtifacts
    resume_details: Mapping[str, Any] | None
    cancelled: bool

    def now(self) -> datetime:
        """Return the current time (bible §4.1: shared with `PipelineContext.now`)."""
        ...

    def heartbeat(self, details: Mapping[str, Any]) -> None:
        """Record a `ResumeCursor` for a `Resumable` stage (no-op unless the shell supports it)."""
        ...

    def remaining_ms(self) -> int | None:
        """Return the remaining time budget in milliseconds, or `None` if unbounded."""
        ...


@dataclass
class _LocalStageContext:
    """Concrete `StageContext` built by :meth:`LocalContext.build_stage_context`."""

    tenant_id: str
    collection_id: str | None
    document_id: str | None
    job_id: str | None
    trace_id: str
    profile_hash: str
    token_counter: TokenCounter
    artifacts: DerivedArtifacts
    analyzer: KoreanAnalyzer | None = None
    lineage: Mapping[str, Any] = field(default_factory=dict)
    plan: Any | None = None
    resume_details: Mapping[str, Any] | None = None
    cancelled: bool = False
    _clock: Callable[[], datetime] = field(kw_only=True)
    _budget_ms: int | None = field(default=None, kw_only=True)

    def now(self) -> datetime:
        """Return the current time from the injected clock."""
        return self._clock()

    def heartbeat(self, _details: Mapping[str, Any]) -> None:
        """No-op: `LocalRunner` is non-durable and does not track `ResumeCursor` (bible §11.1)."""
        return

    def remaining_ms(self) -> int | None:
        """Total configured budget (bible §4.1 `remaining_ms`).

        `LocalContext` does not track wall-clock elapsed time per stage call, so this returns the
        whole configured budget rather than a true remainder; `Stage.run` implementations must
        still treat it as an upper bound, not a guarantee of freshness.
        """
        return self._budget_ms


@dataclass
class LocalContext:
    """Non-durable, in-process runtime holder (ADR-0003 `LocalContext`: "asyncio + retries").

    Holds the shell-side state a `StageContext` is built from for every stage call: tenant/
    collection/profile/trace scope, a clock, a budget, a logger, an artifact store and
    reference-only secrets (bible §4.1, §6.6). It intentionally does *not* implement the stage
    execution loop itself (cache lookup, retry/backoff, failure classification) — that is
    `orchestration.local.runner.LocalRunner`'s job (bible §12); `LocalContext` is the collaborator
    `LocalRunner` uses to build each `StageContext` and to answer `PipelineContext.now`/`sleep`.
    """

    tenant_id: str
    collection_id: str | None
    profile_hash: str
    trace_id: str
    store: _BackingStore
    clock: Callable[[], datetime]
    budget_ms: int | None = None
    logger: Any = None
    secrets: SecretsRef = field(default_factory=SecretsRef)

    def now(self) -> datetime:
        """Return the current time from the injected clock."""
        return self.clock()

    async def sleep(self, d: timedelta) -> None:
        """Suspend for `d` using `asyncio.sleep` (local mode has no durable timer)."""
        await asyncio.sleep(d.total_seconds())

    async def emit(self, event: CloudEventEnvelope) -> None:
        """Local mode has no outbox relay; logging the event is the whole of `emit` (bible §11.1)."""
        if self.logger is not None:
            self.logger.info("event.emitted", event=event)

    def build_stage_context(
        self,
        *,
        stage_token_counter: TokenCounter,
        document_id: str | None = None,
        job_id: str | None = None,
        lineage: Mapping[str, Any] | None = None,
        plan: Any | None = None,
        analyzer: KoreanAnalyzer | None = None,
    ) -> _LocalStageContext:
        """Build the `StageContext` a single `Stage.run` call sees."""
        artifacts = TenantBoundArtifacts(store=self.store, tenant_id=self.tenant_id)
        return _LocalStageContext(
            tenant_id=self.tenant_id,
            collection_id=self.collection_id,
            document_id=document_id,
            job_id=job_id,
            trace_id=self.trace_id,
            profile_hash=self.profile_hash,
            token_counter=stage_token_counter,
            artifacts=artifacts,
            analyzer=analyzer,
            lineage=dict(lineage or {}),
            plan=plan,
            _clock=self.clock,
            _budget_ms=self.budget_ms,
        )
