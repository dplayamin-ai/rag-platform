"""`LocalRunner` — 비내구(non-durable) 인프로세스 스테이지 실행기.

역할: `Stage.run`을 순차 실행하며 `stage_key` 캐시 히트 스킵과 실패 분류(abort/partial/retry)를
처리하는, 개발·CI·평가 하네스 전용 러너(프로덕션 금지).
설계 근거: 바이블 §11.1(`local` 모드 — "비내구, 개발·CI·평가 하네스, 프로덕션 금지"),
§4.1(`stage_key` 캐시 히트 스킵), §11.3(재시도 분류 -> shell 액션); ADR-0003(오케스트레이터
중립 파이프라인), ADR-0037(캐시 제외 스테이지 `fetch`/`index`는 항상 재실행).

구성:
- `LocalRunner` — 직렬 실행 엔진(`run`), 캐시 조회·기록, 재시도/백오프(`_run_one`)
- `StageSpec` — 스테이지 이름·`Stage`·`StagePolicy`·`schema_type` 묶음
- `StageRunLog`/`RunResult` — 실행 로그와 최종 상태(`succeeded`/`partial`/`failed`)
- `CACHE_EXEMPT` — 캐시 제외 스테이지 집합(`fetch`, `index`)

불변식·주의: 스테이지 경계 페이로드를 검증된 계약 인스턴스가 아닌 불투명한 `bytes`로 취급한다.
`ArtifactRef -> Pydantic` 계약 검증(포인트 2·3)은 생성된 `rag_platform.contracts` 패키지가
필요해 이 작업 범위 밖이며 `orchestration/context.py`의 `run_stage`가 담당한다.
검증 계층: 1층(여기서 검증) — `tests/unit/test_orchestration_local_runner.py`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal, Protocol, runtime_checkable

from rag_platform.sdk.hashing import blake3_hex, stage_key as compute_stage_key
from rag_platform.sdk.policy import compute_backoff_delay, should_retry
from rag_platform.sdk.stage import RetryClass, StageError, classify_error

if TYPE_CHECKING:
    from collections.abc import Sequence

    from rag_platform.sdk.context import LocalContext
    from rag_platform.sdk.policy import StagePolicy
    from rag_platform.sdk.ports import TokenCounter
    from rag_platform.sdk.stage import Stage

__all__ = ["CACHE_EXEMPT", "LocalRunner", "RunResult", "StageRunLog", "StageSpec"]

# ADR-0037: `fetch` has no `stage_key` at all (always re-checked); `index` writes a byte-hash-keyed
# artifact (upsert idempotency is `record_id`'s job, not the stage cache). `publish` is a separate,
# non-cacheable local-ledger-transaction path (bible §4.2) and is out of scope for this runner.
CACHE_EXEMPT: frozenset[str] = frozenset({"fetch", "index"})


@runtime_checkable
class _KeyedStore(Protocol):
    """Structural slice of `storage.artifact_store.ArtifactStore` this runner needs."""

    async def put_artifact(
        self,
        data: bytes,
        *,
        tenant_id: str,
        schema_type: str,
        media_type: str,
        stage_key: str | None = None,
    ) -> Any: ...

    async def get_bytes(self, ref: Any) -> bytes: ...

    async def lookup_stage_key(self, tenant_id: str, schema_type: str, stage_key: str) -> Any | None: ...


@dataclass(frozen=True)
class StageSpec:
    """One stage in the profile's ingest stage order (bible §4.2 `STAGES` sketch).

    ``schema_type`` is the PascalCase output contract type name (bible §5.1), used only to build
    the object key (`storage.keys.artifact_key`); no schema validation happens here (see the
    module docstring).
    """

    name: str
    stage: Stage[bytes, bytes]
    policy: StagePolicy
    schema_type: str


@dataclass
class StageRunLog:
    """One executed (or cache-skipped) stage's outcome, for `RunResult.log`."""

    name: str
    cache_hit: bool
    attempts: int = 1
    classification: RetryClass | None = None
    error: StageError | None = None


@dataclass
class RunResult:
    """Outcome of a full `LocalRunner.run` call over a stage sequence."""

    status: Literal["succeeded", "partial", "failed"]
    ref: Any | None
    log: list[StageRunLog] = field(default_factory=list)

    @property
    def errors(self) -> list[StageError]:
        """Return every `StageError` raised during this run, in stage order."""
        return [entry.error for entry in self.log if entry.error is not None]

    @property
    def cache_hits(self) -> tuple[str, ...]:
        """Return the names of stages skipped by a `stage_key` cache hit (ADR-0037)."""
        return tuple(entry.name for entry in self.log if entry.cache_hit)


class LocalRunner:
    """Serial, non-durable executor: cache-hit skip (ADR-0037), classify-and-abort/partial on failure.

    Not a `PipelineContext` implementation itself (bible §11.1's `LocalContext` is); this class is
    the loop `pipelines.ingest.run` would drive through a `PipelineContext.run` call per stage —
    kept as a separate, directly unit-testable engine per this work package's scope.
    """

    def __init__(
        self,
        *,
        context: LocalContext,
        store: _KeyedStore,
        token_counter: TokenCounter,
        media_type: str = "application/octet-stream",
    ) -> None:
        """Build a runner over `context` (clock/scope) and `store` (artifact persistence)."""
        self._context = context
        self._store = store
        self._token_counter = token_counter
        self._media_type = media_type

    async def run(
        self,
        stages: Sequence[StageSpec],
        initial: bytes,
        *,
        document_id: str | None = None,
        job_id: str | None = None,
    ) -> RunResult:
        """Run `stages` in order over `initial` bytes; bible §4.1 `stage_key` composition per stage."""
        scope_key = f"{self._context.tenant_id}/{self._context.collection_id}/{document_id}"
        current_bytes = initial
        current_ref: Any | None = None
        log: list[StageRunLog] = []

        for spec in stages:
            cacheable = spec.name not in CACHE_EXEMPT
            stage_key: str | None = None
            if cacheable:
                stage_key = compute_stage_key(spec.name, scope_key, blake3_hex(current_bytes), spec.stage.fingerprint())
                cached = await self._store.lookup_stage_key(self._context.tenant_id, spec.schema_type, stage_key)
                if cached is not None:
                    log.append(StageRunLog(name=spec.name, cache_hit=True))
                    current_ref = cached
                    current_bytes = await self._store.get_bytes(cached)
                    continue

            outcome = await self._run_one(spec, current_bytes, stage_key, document_id=document_id, job_id=job_id)
            log.append(outcome.entry)
            if outcome.error is not None:
                if outcome.entry.classification is RetryClass.PARTIAL:
                    # Bible §11.3 `partial`: stop advancing the chain but keep the last good ref —
                    # a simplification of "commit the non-degraded portion" (bible §4.2 `enrich`
                    # row), which needs a real partial-output contract this runner does not model.
                    return RunResult(status="partial", ref=current_ref, log=log)
                return RunResult(status="failed", ref=current_ref, log=log)
            current_ref = outcome.ref
            current_bytes = outcome.output_bytes  # type: ignore[assignment]

        return RunResult(status="succeeded", ref=current_ref, log=log)

    async def _run_one(
        self,
        spec: StageSpec,
        input_bytes: bytes,
        stage_key: str | None,
        *,
        document_id: str | None,
        job_id: str | None,
    ) -> _StageOutcome:
        attempt = 0
        while True:
            attempt += 1
            ctx = self._context.build_stage_context(
                stage_token_counter=self._token_counter, document_id=document_id, job_id=job_id
            )
            try:
                output_bytes = await spec.stage.run(input_bytes, ctx)
            except StageError as error:
                classification = classify_error(error.code)
                if classification is RetryClass.RETRYABLE and should_retry(spec.policy, attempt, error):
                    await self._context.sleep(compute_backoff_delay(spec.policy, attempt))
                    continue
                entry = StageRunLog(
                    name=spec.name, cache_hit=False, attempts=attempt, classification=classification, error=error
                )
                return _StageOutcome(entry=entry, ref=None, output_bytes=None, error=error)
            else:
                ref = await self._store.put_artifact(
                    output_bytes,
                    tenant_id=self._context.tenant_id,
                    schema_type=spec.schema_type,
                    media_type=self._media_type,
                    stage_key=stage_key,
                )
                entry = StageRunLog(name=spec.name, cache_hit=False, attempts=attempt)
                return _StageOutcome(entry=entry, ref=ref, output_bytes=output_bytes, error=None)


@dataclass
class _StageOutcome:
    entry: StageRunLog
    ref: Any | None
    output_bytes: bytes | None
    error: StageError | None
