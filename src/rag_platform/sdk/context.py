"""`PipelineContext`/`StageContext` 프로토콜과 로컬 실행기용 `LocalContext` 런타임 헬퍼.

역할: 파이프라인·단계(stage) 실행이 보는 컨텍스트 타입을 정의하고, 비영속(non-durable) 로컬 실행에
필요한 구체 구현(`LocalContext`, `_LocalStageContext`, `TenantBoundArtifacts`)을 제공한다.
설계 근거: 바이블 §11.1("두 실행기, 하나의 정의"), §4.1(`StageContext` 멤버); ADR-0003(오케스트레이터
중립 파이프라인, 비영속 `LocalRunner`); docs/04-pipelines/01-pipeline-framework.md §3.1/§4.1.
구성: `DerivedArtifacts`/`TenantBoundArtifacts` — 테넌트 바운드 쓰기 전용 아티팩트 포트; `SecretsRef`
— 참조만 들고 다니는 비밀값 핸들; `PipelineContext`/`StageContext` — 프로토콜; `LocalContext` —
`StageContext`를 만들어 주는 비영속 런타임 홀더.
불변식: `sdk`는 레이어 스택 최하단(바이블 §12)이라 `storage`/`ledger`/`profiles`/`orchestration`을
import하지 않는다(구조적 프로토콜로 대체). `datetime.now(UTC)` 직접 호출은 셸/api 밖에서 금지 —
호출자가 실제 `clock`을 명시적으로 주입한다.
검증 계층: 1층(여기서 검증) — tests/unit/test_sdk_context.py.
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

    `plan`/`token_counter`/`analyzer` are declared for stage-facing type compatibility;
    `LocalContext` fills the ingest-only subset it needs and leaves the query-only member (`plan`)
    `None` (bible §4.1: "수집 측은 None"). `security`(query측 `SecurityContext`)는 이 Protocol의
    멤버가 아니다 — `retrieval.planner.plan(request, security, ...)`처럼 스테이지 함수의 명시적
    인자로 받는다(F4 배치 검증: 문서-코드 불일치 정정, 이전 판의 이 독스트링이 틀렸다).

    F3 배치 검증 open_issue 통합: `own_input_ref`/`commit_id`/`index_generation`/`profile_id`/
    `dense_vectors`는 WP-106(`normalize`의 `ctx.parsed_ref`)이 처음 임시로 쓰고 이후 WP들(`chunk`의
    `ctx.normalized_ref`, `embed`의 `ctx.enriched_ref`, `index`의 `ctx.embedded_ref`/`ctx.commit_id`/
    `ctx.profile_id`/`ctx.dense_vectors`)이 같은 임시 관례를 반복한 것을 여기서 공식 필드로 승격한
    것이다. `own_input_ref`는 스테이지가 자기 입력(`run(inp, ctx)`의 `inp`)이 저장된 원본
    `ArtifactRef`를 알아야 할 때(출력 계약의 `lineage_refs.<자기 이름>`에 되짚어 넣을 때) 쓰는
    범용 슬롯이다. 모두 선택 필드(`None` 허용)라 이 필드를 아직 채우지 않는 기존 호출부(`ctx: Any` +
    `getattr(ctx, "parsed_ref", None)` 등)는 그대로 동작한다 — 이 변경은 그 관례를 깨지 않고
    문서화·타입화만 한다.
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
    own_input_ref: ArtifactRef | None
    commit_id: str | None
    index_generation: int | None
    profile_id: str | None
    dense_vectors: Mapping[str, Any] | None

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
    own_input_ref: ArtifactRef | None = None
    commit_id: str | None = None
    index_generation: int | None = None
    profile_id: str | None = None
    dense_vectors: Mapping[str, Any] | None = None
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
        own_input_ref: ArtifactRef | None = None,
        commit_id: str | None = None,
        index_generation: int | None = None,
        profile_id: str | None = None,
        dense_vectors: Mapping[str, Any] | None = None,
    ) -> _LocalStageContext:
        """Build the `StageContext` a single `Stage.run` call sees.

        `own_input_ref`/`commit_id`/`index_generation`/`profile_id`/`dense_vectors` are the
        official slots for the per-stage conventions several WPs bolted on via `getattr(ctx, ...)`
        (WP-106 `parsed_ref` precedent; see the `StageContext` docstring). Callers that do not need
        them may omit them; existing `getattr(ctx, "parsed_ref", None)`-style call sites keep working
        unchanged.
        """
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
            own_input_ref=own_input_ref,
            commit_id=commit_id,
            index_generation=index_generation,
            profile_id=profile_id,
            dense_vectors=dense_vectors,
            _clock=self.clock,
            _budget_ms=self.budget_ms,
        )
