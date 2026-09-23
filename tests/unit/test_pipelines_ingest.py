"""Unit tests for `rag_platform.pipelines.ingest` (bible §11.1, §4.2 `STAGES`; ADR-0003, D-17)."""

from __future__ import annotations

import datetime
import inspect
from datetime import timedelta
from pathlib import Path

import pytest

from rag_platform.pipelines import ingest
from rag_platform.sdk.policy import StagePolicy

_POLICY = StagePolicy(
    task_queue="ingest-cpu", start_to_close=timedelta(minutes=5), heartbeat=None, max_attempts=3, resumable=False
)


class _RecordingPipelineContext:
    def __init__(self) -> None:
        self.calls: list[str] = []

    async def run(self, stage: str, inp_ref: object, out_type: type[object], policy: StagePolicy) -> str:
        self.calls.append(stage)
        return f"ref-after-{stage}"

    async def emit(self, event: object) -> None:
        return

    def now(self) -> datetime.datetime:
        return datetime.datetime.now(datetime.UTC)

    async def sleep(self, d) -> None:
        return


class _ProfileWithRecount:
    def has_stage(self, stage: str) -> bool:
        return True

    def stage_policy(self, stage: str) -> StagePolicy:
        return _POLICY


class _ProfileWithoutRecount:
    def has_stage(self, stage: str) -> bool:
        return stage != "recount"

    def stage_policy(self, stage: str) -> StagePolicy:
        return _POLICY


async def test_run_calls_every_stage_in_bible_order_including_publish() -> None:
    ctx = _RecordingPipelineContext()
    await ingest.run(ctx, "req-ref", _ProfileWithRecount())
    assert ctx.calls == ["fetch", "parse", "normalize", "chunk", "recount", "enrich", "embed", "index", "publish"]


async def test_run_skips_recount_when_profile_does_not_enable_it() -> None:
    ctx = _RecordingPipelineContext()
    await ingest.run(ctx, "req-ref", _ProfileWithoutRecount())
    assert "recount" not in ctx.calls
    assert ctx.calls[-1] == "publish"


async def test_run_from_stage_restarts_partway_through_the_chain() -> None:
    ctx = _RecordingPipelineContext()
    await ingest.run(ctx, "req-ref", _ProfileWithRecount(), from_stage="enrich")
    assert ctx.calls == ["enrich", "embed", "index", "publish"]


async def test_run_rejects_an_unknown_from_stage() -> None:
    ctx = _RecordingPipelineContext()
    with pytest.raises(ValueError, match="from_stage"):
        await ingest.run(ctx, "req-ref", _ProfileWithRecount(), from_stage="not-a-stage")


async def test_run_returns_the_final_ref() -> None:
    ctx = _RecordingPipelineContext()
    result = await ingest.run(ctx, "req-ref", _ProfileWithRecount())
    assert result == "ref-after-publish"


def test_stages_matches_bible_4_2_linear_chain() -> None:
    assert ingest.STAGES == ("fetch", "parse", "normalize", "chunk", "recount", "enrich", "embed", "index")


def test_module_imports_none_of_the_forbidden_orchestrator_or_web_modules() -> None:
    """Defensive unit-level check of the import-linter `pipelines-orchestrator-neutral` contract."""
    import_lines = [
        line.strip()
        for line in Path(inspect.getfile(ingest)).read_text(encoding="utf-8").splitlines()
        if line.strip().startswith(("import ", "from "))
    ]
    for forbidden in ("temporalio", "fastapi", "starlette", "rag_platform.ledger", "rag_platform.orchestration"):
        assert not any(forbidden in line for line in import_lines), forbidden
