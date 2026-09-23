"""수집(ingest) 파이프라인 정의 — `PipelineContext`에만 의존하는 순수 정의(바이블 §11.1, §12 `pipelines`).

설계 근거: 바이블 §11.1(`pipelines.ingest.run(ctx, req_ref, profile) -> IndexCommit`),
§4.2(`STAGES` 선형 체인 + 스테이지별 입출력 계약 표); ADR-0003(오케스트레이터 중립 파이프라인 정의);
`docs/04-pipelines/01-pipeline-framework.md` §4.1·§4.4(정의 스케치);
`docs/13-implementation/wp/WP-303-ingest-pipeline-e2e.md`(F3-03, 이 완성 작업의 WP).

구성:
- `STAGES` — `fetch`부터 `index`까지 선형 체인(`publish`는 루프 이후 별도 실행)
- `STAGE_OUTPUT_SCHEMA_TYPES` — 스테이지별로 산출할 PascalCase 계약 타입명(문서화 목적)
- `STAGE_OUTPUT_TYPES` — 위와 같은 매핑을 실제 계약 클래스(런타임 값)로 둔 것; `ctx.run(...)`의
  `out_type` 인자로 그대로 전달한다
- `PipelineProfile` — 이 정의가 필요로 하는 `Profile`의 부분 프로토콜(`has_stage`, `stage_policy`)
- `run(ctx, req_ref, profile, *, from_stage="fetch")` — 체인을 실행하고 마지막 `ArtifactRef` 반환

불변식·주의: `temporalio`·`fastapi`·`starlette`·`rag_platform.ledger`·`rag_platform.orchestration`
임포트 금지(import-linter `pipelines-orchestrator-neutral`, D-17) — `ctx.run(...)`만 호출하고
구체 shell을 직접 참조하지 않는다(계약 클래스 임포트는 최하단 계층이라 허용, 바이블 §12). `out_type`은
`rag_platform.contracts.*`의 생성 Pydantic 모델이다(WP-303이 코드젠 완료 후 이전 `object` 자리표시자를
교체); `publish`만 `CloudEventEnvelope`(단일 원소 타입 — 이 프로토콜은 리스트를 표현하는 별도 문법이
없다). `recount`는 프로파일이 활성화한 경우에만 실행한다.
검증 계층: 1층(여기서 검증) — `tests/unit/test_pipelines_ingest.py`, `tests/e2e/test_ingest_e2e.py`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from rag_platform.contracts.chunk_set import ChunkSet
from rag_platform.contracts.cloud_event_envelope import CloudEventEnvelope
from rag_platform.contracts.embedded_chunk_set import EmbeddedChunkSet
from rag_platform.contracts.enriched_chunk_set import EnrichedChunkSet
from rag_platform.contracts.index_commit import IndexCommit
from rag_platform.contracts.normalized_document import NormalizedDocument
from rag_platform.contracts.parsed_document import ParsedDocument
from rag_platform.contracts.source_document import SourceDocument

if TYPE_CHECKING:
    from rag_platform.sdk.context import PipelineContext
    from rag_platform.sdk.policy import StagePolicy

__all__ = ["STAGES", "STAGE_OUTPUT_SCHEMA_TYPES", "STAGE_OUTPUT_TYPES", "PipelineProfile", "run"]

# Bible §4.2 `STAGES` linear chain; `publish` runs after the loop (bible §4.4 sketch).
STAGES: tuple[str, ...] = ("fetch", "parse", "normalize", "chunk", "recount", "enrich", "embed", "index")

# Bible §5.1 inventory: PascalCase contract type each stage produces (documentation only).
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

# Same mapping as `STAGE_OUTPUT_SCHEMA_TYPES`, but the actual runtime class each `ctx.run(...)` call
# passes as `out_type` (WP-303: contracts codegen has landed, so the `object` placeholder is gone).
STAGE_OUTPUT_TYPES: dict[str, type[Any]] = {
    "fetch": SourceDocument,
    "parse": ParsedDocument,
    "normalize": NormalizedDocument,
    "chunk": ChunkSet,
    "recount": ChunkSet,
    "enrich": EnrichedChunkSet,
    "embed": EmbeddedChunkSet,
    "index": IndexCommit,
    "publish": CloudEventEnvelope,
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
        ref = await ctx.run(stage, ref, STAGE_OUTPUT_TYPES[stage], profile.stage_policy(stage))
    return await ctx.run("publish", ref, STAGE_OUTPUT_TYPES["publish"], profile.stage_policy("publish"))
