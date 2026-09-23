"""수집(ingest) 파이프라인 정의 골격 — `PipelineContext`에만 의존하는 순수 정의(바이블 §11.1, §12 `pipelines`).

설계 근거: 바이블 §11.1(`pipelines.ingest.run(ctx, req_ref, profile) -> IndexCommit`),
§4.2(`STAGES` 선형 체인); ADR-0003(오케스트레이터 중립 파이프라인 정의);
`docs/04-pipelines/01-pipeline-framework.md` §4.1·§4.4(정의 스케치).

구성:
- `STAGES` — `fetch`부터 `index`까지 선형 체인(`publish`는 루프 이후 별도 실행)
- `STAGE_OUTPUT_SCHEMA_TYPES` — 스테이지별로 산출할 PascalCase 계약 타입명(문서화 목적)
- `PipelineProfile` — 이 정의가 필요로 하는 `Profile`의 부분 프로토콜(`has_stage`, `stage_policy`)
- `run(ctx, req_ref, profile, *, from_stage="fetch")` — 체인을 실행하고 마지막 `ArtifactRef` 반환

불변식·주의: `temporalio`·`fastapi`·`starlette`·`rag_platform.ledger`·`rag_platform.orchestration`
임포트 금지(import-linter `pipelines-orchestrator-neutral`, D-17) — `ctx.run(...)`만 호출하고
구체 shell을 직접 참조하지 않는다. `out_type`은 전 스테이지에서 `object`로 임시 지정했다 — 실제
생성 계약 클래스(`rag_platform.contracts.source_document.SourceDocument` 등)가 아직 없어서이며
(코드젠 이후 스테이지별 한 줄 교체로 대체 예정), `recount`는 프로파일이 활성화한 경우에만 실행한다.
검증 계층: 1층(여기서 검증) — `tests/unit/test_pipelines_ingest.py`.
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
