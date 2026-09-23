"""Ingest pipeline definition skeleton: depends only on `PipelineContext` (bible §11.1, §12).

Canon: design bible §11.1 (`pipelines.ingest.run(ctx, req_ref, profile) -> IndexCommit`), §4.2
(`STAGES` linear chain); ADR-0003 (orchestrator-neutral pipeline definitions);
docs/04-pipelines/01-pipeline-framework.md §4.1, §4.4 (definition sketch).

Importing ``temporalio``, ``fastapi``, ``starlette``, ``rag_platform.ledger`` or
``rag_platform.orchestration`` here is forbidden (import-linter `pipelines-orchestrator-neutral`,
D-17): this module calls `ctx.run(...)` only, never a concrete shell. ``out_type`` is passed as
``object`` for every stage below — the real generated contract classes
(``rag_platform.contracts.source_document.SourceDocument``, etc., bible §12) do not exist yet in
this checkout (see `sdk/stage.py`'s module docstring); `STAGE_OUTPUT_SCHEMA_TYPES` records the
PascalCase name each stage will actually produce once codegen lands, so replacing the placeholder
is a one-line change per stage, not a redesign.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from rag_platform.sdk.context import PipelineContext
    from rag_platform.sdk.policy import StagePolicy

__all__ = ["STAGES", "STAGE_OUTPUT_SCHEMA_TYPES", "PipelineProfile", "run"]

# Bible §4.2 `STAGES` linear chain; `publish` runs after the loop (bible §4.4 sketch).
STAGES: tuple[str, ...] = ("fetch", "parse", "normalize", "chunk", "recount", "enrich", "embed", "index")

# Bible §5.1 inventory: PascalCase contract type each stage produces (documentation only; see the
# module docstring for why `out_type` itself is `object` until contracts codegen lands).
STAGE_OUTPUT_SCHEMA_TYPES: dict[str, str] = {
    "fetch": "SourceDocument",
    "parse": "ParsedDocument",
    "normalize": "NormalizedDocument",
    "chunk": "ChunkSet",
    "recount": "ChunkSet",
    "enrich": "EnrichedChunkSet",
    "embed": "EmbeddedChunkSet",
    "index": "IndexCommit",
    "publish": "CloudEventEnvelopeList",
}


@runtime_checkable
class PipelineProfile(Protocol):
    """The slice of a resolved `Profile` the ingest pipeline definition needs (bible §7.3, §11.1)."""

    def has_stage(self, stage: str) -> bool:
        """Return whether the resolved profile enables `stage` (e.g. optional `recount`)."""
        ...

    def stage_policy(self, stage: str) -> StagePolicy:
        """Return the resolved `StagePolicy` for `stage` (bible §4.4)."""
        ...


async def run(
    ctx: PipelineContext,
    req_ref: Any,
    profile: PipelineProfile,
    *,
    from_stage: str = "fetch",
) -> Any:
    """Bible §11.1 / §4.4 sketch: run the ingest chain from `from_stage` through `publish`.

    `recount` is skipped unless the profile enables it (bible §4.2 "선택"). Returns the boundary
    `ArtifactRef` the last stage produced (schema_type `IndexCommit`; the ledger row is the
    canonical record, bible §11.1's `pipelines.query.run` note applies symmetrically here).
    """
    if from_stage not in STAGES:
        msg = f"from_stage must be one of {STAGES}, got {from_stage!r}"
        raise ValueError(msg)
    ref = req_ref
    for stage in STAGES[STAGES.index(from_stage) :]:
        if stage == "recount" and not profile.has_stage("recount"):
            continue
        ref = await ctx.run(stage, ref, object, profile.stage_policy(stage))
    return await ctx.run("publish", ref, object, profile.stage_policy("publish"))
