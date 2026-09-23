"""Unit tests for `rag_platform.orchestration.local.runner.LocalRunner` (bible §11.1; ADR-0003, ADR-0037).

Covers exactly the three scenarios this work package calls out: a two-dummy-stage chain, a
`stage_key` cache hit (ADR-0037) and failure classification driving abort vs. partial vs. retry
(bible §11.3).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from rag_platform.orchestration.local.runner import LocalRunner, RunResult, StageSpec
from rag_platform.sdk.context import LocalContext
from rag_platform.sdk.policy import StagePolicy
from rag_platform.sdk.stage import StageError
from rag_platform.storage.artifact_store import InMemoryArtifactStore

_POLICY = StagePolicy(
    task_queue="ingest-cpu", start_to_close=timedelta(minutes=5), heartbeat=None, max_attempts=3, resumable=False
)


class _FakeTokenCounter:
    tokenizer_id = "fake"

    def count(self, text: str) -> int:
        return len(text)


class _UpperStage:
    plugin_id = "normalizer.upper"
    config_schema = object
    requires_lineage: tuple[str, ...] = ()

    def capabilities(self) -> object:
        return object()

    def fingerprint(self) -> str:
        return "fp-upper"

    async def run(self, inp: bytes, ctx: object) -> bytes:
        return inp.upper()


class _ReverseStage:
    plugin_id = "chunker.reverse"
    config_schema = object
    requires_lineage: tuple[str, ...] = ()

    def capabilities(self) -> object:
        return object()

    def fingerprint(self) -> str:
        return "fp-reverse"

    async def run(self, inp: bytes, ctx: object) -> bytes:
        return inp[::-1]


class _AlwaysFailsStage:
    """Raises the configured `StageError` code every attempt."""

    plugin_id = "chunker.boom"
    config_schema = object
    requires_lineage: tuple[str, ...] = ()

    def __init__(self, code: str) -> None:
        self._code = code
        self.calls = 0

    def capabilities(self) -> object:
        return object()

    def fingerprint(self) -> str:
        return f"fp-boom-{self._code}"

    async def run(self, inp: bytes, ctx: object) -> bytes:
        self.calls += 1
        raise StageError(self._code, stage=self._code.split(".", 1)[0])


class _FailsTwiceThenSucceeds:
    """A retryable failure that succeeds on the third attempt (max_attempts=3)."""

    plugin_id = "embedder.flaky"
    config_schema = object
    requires_lineage: tuple[str, ...] = ()

    def __init__(self) -> None:
        self.calls = 0

    def capabilities(self) -> object:
        return object()

    def fingerprint(self) -> str:
        return "fp-flaky"

    async def run(self, inp: bytes, ctx: object) -> bytes:
        self.calls += 1
        if self.calls < 3:
            code = "embed.server_unavailable"
            raise StageError(code, stage="embed")
        return inp


def _make_runner() -> tuple[LocalRunner, InMemoryArtifactStore]:
    store = InMemoryArtifactStore()
    context = LocalContext(
        tenant_id="t1",
        collection_id="c1",
        profile_hash="ph",
        trace_id="tr1",
        store=store,
        clock=lambda: datetime.now(UTC),
    )
    runner = LocalRunner(context=context, store=store, token_counter=_FakeTokenCounter())
    return runner, store


async def test_two_stage_chain_runs_serially_and_succeeds() -> None:
    runner, store = _make_runner()
    stages = [
        StageSpec(name="normalize", stage=_UpperStage(), policy=_POLICY, schema_type="NormalizedDocument"),
        StageSpec(name="chunk", stage=_ReverseStage(), policy=_POLICY, schema_type="ChunkSet"),
    ]
    result = await runner.run(stages, b"hello", document_id="doc1")
    assert result.status == "succeeded"
    assert await store.get_bytes(result.ref) == b"OLLEH"
    assert [entry.name for entry in result.log] == ["normalize", "chunk"]


async def test_second_identical_run_is_a_stage_key_cache_hit() -> None:
    runner, _store = _make_runner()
    stages = [
        StageSpec(name="normalize", stage=_UpperStage(), policy=_POLICY, schema_type="NormalizedDocument"),
        StageSpec(name="chunk", stage=_ReverseStage(), policy=_POLICY, schema_type="ChunkSet"),
    ]
    first = await runner.run(stages, b"hello", document_id="doc1")
    second = await runner.run(stages, b"hello", document_id="doc1")
    assert first.status == second.status == "succeeded"
    assert second.cache_hits == ("normalize", "chunk")  # ADR-0037: identical scope+input+fingerprint


async def test_fetch_and_index_are_never_cache_hits() -> None:
    """ADR-0037: `fetch`/`index` are cache-exempt; they always re-run `Stage.run`."""
    runner, _store = _make_runner()
    upper = _UpperStage()
    stages = [StageSpec(name="fetch", stage=upper, policy=_POLICY, schema_type="SourceDocument")]
    await runner.run(stages, b"hello", document_id="doc1")
    second = await runner.run(stages, b"hello", document_id="doc1")
    assert second.cache_hits == ()  # never a cache hit, even though scope+input+fingerprint match


async def test_non_retryable_failure_aborts_the_run() -> None:
    runner, _store = _make_runner()
    boom = _AlwaysFailsStage("chunk.tokenizer_missing")
    stages = [StageSpec(name="chunk", stage=boom, policy=_POLICY, schema_type="ChunkSet")]
    result = await runner.run(stages, b"x", document_id="doc1")
    assert result.status == "failed"
    assert result.errors[0].code == "chunk.tokenizer_missing"
    assert boom.calls == 1  # non-retryable: no retry attempts


async def test_partial_failure_stops_but_reports_partial_status() -> None:
    runner, _store = _make_runner()
    boom = _AlwaysFailsStage("enrich.budget_exceeded")
    stages = [StageSpec(name="enrich", stage=boom, policy=_POLICY, schema_type="EnrichedChunkSet")]
    result = await runner.run(stages, b"x", document_id="doc1")
    assert result.status == "partial"
    assert result.errors[0].code == "enrich.budget_exceeded"


async def test_retryable_failure_retries_up_to_max_attempts_then_succeeds() -> None:
    runner, store = _make_runner()
    flaky = _FailsTwiceThenSucceeds()
    stages = [StageSpec(name="embed", stage=flaky, policy=_POLICY, schema_type="EmbeddedChunkSet")]
    result = await runner.run(stages, b"payload", document_id="doc1")
    assert result.status == "succeeded"
    assert flaky.calls == 3
    assert await store.get_bytes(result.ref) == b"payload"


async def test_retryable_failure_exhausting_max_attempts_fails() -> None:
    runner, _store = _make_runner()
    boom = _AlwaysFailsStage("embed.server_unavailable")
    policy = StagePolicy(
        task_queue="ingest-gpu-embed",
        start_to_close=timedelta(minutes=5),
        heartbeat=None,
        max_attempts=2,
        resumable=True,
    )
    stages = [StageSpec(name="embed", stage=boom, policy=policy, schema_type="EmbeddedChunkSet")]
    result = await runner.run(stages, b"x", document_id="doc1")
    assert result.status == "failed"
    assert boom.calls == 2  # retried once (max_attempts=2), then gave up


def test_run_result_errors_and_cache_hits_helpers_on_empty_log() -> None:
    result = RunResult(status="succeeded", ref=None)
    assert result.errors == []
    assert result.cache_hits == ()


@pytest.mark.parametrize("code", ["parse.sidecar_unavailable", "rerank.timeout"])
async def test_fallback_classification_is_treated_as_abort_in_this_minimal_runner(code: str) -> None:
    """This runner has no adapter-chain concept; FALLBACK degrades to `failed` here (documented)."""
    runner, _store = _make_runner()
    boom = _AlwaysFailsStage(code)
    stages = [StageSpec(name=code.split(".", 1)[0], stage=boom, policy=_POLICY, schema_type="ParsedDocument")]
    result = await runner.run(stages, b"x", document_id="doc1")
    assert result.status == "failed"
