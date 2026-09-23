"""질의(query) 파이프라인 정의 — plan→retrieve→fuse/hydrate→postprocess→pack→render 인프로세스 체인.

역할: 바이블 §4.3(검색 파이프라인, "오케스트레이터 미경유·인프로세스")의 실행 골격. 각 단계를
`Protocol` 콜러블로 주입받아 `LocalRunner`/오케스트레이터 없이 한 프로세스 안에서 직접 호출한다
(ADR-0034: hot path는 PostgreSQL 비의존).
설계 근거: 바이블 §4.3 검색 파이프라인 표, §12(모듈 맵 — `pipelines`·`retrieval`·`render`는 같은
계층의 독립 형제이며 서로 임포트하지 않는다, `import-linter` 계층 계약으로 확인함), ADR-0003
(오케스트레이터 중립 정의), ADR-0034; `docs/13-implementation/wp/WP-404-render-and-query-pipeline.md`
(F4-04, 이 완성 작업의 WP — §0에 F4-01~03과의 동시 실행 배경 기록).
구성: `Planner`/`ChannelRetriever`/`Fuser`/`Hydrator`/`Postprocessor`/`Packer`/`RendererFn` —
단계별 프로토콜(모두 `contracts.*` 타입만 참조); `QueryPipelineDeps`/`QueryPipelineResult` — 주입
묶음과 결과; `run_query` — 체인 실행; `resolve_renderer` — §4.3 "renderer 미지정 시
target_model.provider에서 유도" 표.
불변식·주의: 이 모듈은 `rag_platform.contracts.*`만 임포트한다(최하단 계층, 바이블 §12) —
`rag_platform.retrieval.*`·`rag_platform.render.*`(형제 계층)·`temporalio`·`fastapi`·`starlette`·
`rag_platform.ledger`·`rag_platform.orchestration`(상위 계층) 임포트는 금지(import-linter
`pipelines-orchestrator-neutral`, D-17, 그리고 §12 형제 계층 규칙). 실제 단계 콜러블 배선(F4-01~03
모듈 + 렌더러 2종을 이 Protocol에 맞춰 묶는 일)은 더 상위 계층(F5 api/mcp/cli)의 몫이다(open_issues).
`retrieve`는 결과를 캐시하지 않는다(ACL 시점성, §4.3). 이 WP 범위에는 `rerank` 어댑터가 없다(모델
다운로드 금지) — `postprocess`는 `hydrate` 직후 `RankedSet`을 그대로 받는다(§4.3이 정의한 rerank
스킵 폴백과 같은 모양).
검증 계층: 1층(여기서 검증) — `tests/retrieval/test_query_e2e.py`(페이크 `QueryPipelineDeps`).
`# DEFERRED: F4 배치 검증자 또는 F5가 실 F4-01~03 모듈 + 렌더러를 이 Protocol에 맞춰 묶어
tests/retrieval의 전체 체인 e2e를 F3 샘플 위에서 실행한다`(모델·Docker·GPU 의존 없음).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from rag_platform.contracts.common_types import Renderer, SecurityContext

if TYPE_CHECKING:
    from rag_platform.contracts.candidate_set import CandidateSet
    from rag_platform.contracts.context_pack import ContextPack
    from rag_platform.contracts.query_plan import QueryPlan
    from rag_platform.contracts.query_request import QueryRequest
    from rag_platform.contracts.ranked_set import RankedSet
    from rag_platform.contracts.rendered_context import RenderedContext

__all__ = [
    "ChannelRetriever",
    "Fuser",
    "Hydrator",
    "Packer",
    "Planner",
    "Postprocessor",
    "QueryPipelineDeps",
    "QueryPipelineResult",
    "RendererFn",
    "resolve_renderer",
    "run_query",
]


@runtime_checkable
class Planner(Protocol):
    """`plan` 스테이지(§4.3): `QueryRequest` + `SecurityContext` → `QueryPlan`."""

    def __call__(self, request: QueryRequest, security: SecurityContext) -> QueryPlan:
        """Run the `plan` stage."""
        ...


@runtime_checkable
class ChannelRetriever(Protocol):
    """`retrieve` 스테이지(§4.3): 채널 x 컬렉션 x 변형 팬아웃을 안에서 실행해 `CandidateSet`을 만든다."""

    async def __call__(self, plan: QueryPlan, security: SecurityContext) -> CandidateSet:
        """Run the `retrieve` stage (fans out internally; results must not be cached)."""
        ...


@runtime_checkable
class Fuser(Protocol):
    """`fuse` 스테이지(§4.3): `CandidateSet` → `RankedSet(stage=fused, hydrated=false)`."""

    def __call__(self, candidates: CandidateSet, plan: QueryPlan) -> RankedSet:
        """Run the `fuse` stage."""
        ...


@runtime_checkable
class Hydrator(Protocol):
    """`hydrate` 서브스텝(§4.3, fuse 내부·경계 타입 추가 없음): 상위 후보 payload를 1회 배치 조회."""

    async def __call__(self, ranked: RankedSet, plan: QueryPlan, security: SecurityContext) -> RankedSet:
        """Run the `hydrate` substep."""
        ...


@runtime_checkable
class Postprocessor(Protocol):
    """`postprocess` 스테이지(§4.3): `RankedSet` → `RankedSet(stage=postprocessed)`."""

    def __call__(self, ranked: RankedSet, plan: QueryPlan) -> RankedSet:
        """Run the `postprocess` stage."""
        ...


@runtime_checkable
class Packer(Protocol):
    """`pack` 스테이지(§4.3): `RankedSet(postprocessed)` + `QueryPlan` → `ContextPack`."""

    def __call__(self, ranked: RankedSet, plan: QueryPlan, security: SecurityContext) -> ContextPack:
        """Run the `pack` stage."""
        ...


@runtime_checkable
class RendererFn(Protocol):
    """`render` 스테이지(§4.3): `ContextPack` → `RenderedContext`."""

    def __call__(self, pack: ContextPack, *, query_text: str) -> RenderedContext:
        """Run the `render` stage."""
        ...


#: 바이블 §4.3: "QueryRequest.renderer가 없으면 target_model.provider에서 유도".
_PROVIDER_TO_RENDERER: dict[str, Renderer] = {
    "anthropic": Renderer.anthropic_search_result,
    "openai": Renderer.openai_messages,
    "google": Renderer.gemini_messages,
    "local": Renderer.xml_documents,
}


def resolve_renderer(request: QueryRequest) -> Renderer:
    """`QueryRequest.renderer`가 있으면 그것을, 없으면 `target_model.provider`에서 유도한다(§4.3)."""
    if request.renderer is not None:
        return request.renderer
    if request.target_model is not None:
        provider = str(request.target_model.provider)
        if provider in _PROVIDER_TO_RENDERER:
            return _PROVIDER_TO_RENDERER[provider]
    return Renderer.markdown


@dataclass(frozen=True)
class QueryPipelineDeps:
    """단계별 콜러블 주입 묶음.

    `renderers`는 호출자(상위 계층)가 채운다 — 비어 있으면 렌더링을 건너뛴다
    (`run_query(..., render=True)`여도 `rendered=None`).
    """

    plan: Planner
    retrieve: ChannelRetriever
    fuse: Fuser
    hydrate: Hydrator
    postprocess: Postprocessor
    pack: Packer
    renderers: dict[Renderer, RendererFn] = field(default_factory=dict)


@dataclass(frozen=True)
class QueryPipelineResult:
    """`run_query`의 반환값 — 단계 산출물과(요청 시) 렌더 결과."""

    plan: QueryPlan
    ranked_set: RankedSet
    context_pack: ContextPack
    rendered: RenderedContext | None


async def run_query(
    request: QueryRequest,
    security: SecurityContext,
    deps: QueryPipelineDeps,
    *,
    render: bool = True,
) -> QueryPipelineResult:
    """plan→retrieve→fuse/hydrate→postprocess→pack→render 체인을 인프로세스로 실행한다(§4.3).

    각 단계는 `deps`의 콜러블을 직접 호출한다 — `PipelineContext`/원장/Temporal은 관여하지 않는다
    (ADR-0034). `rerank`는 이 WP에 어댑터가 없어 건너뛴다: `hydrate`가 만든 `RankedSet`을 그대로
    `postprocess`에 넘긴다(§4.3이 정의한 rerank 실패 폴백 — `rerank.applied=false`,
    `explain += rerank_skipped` — 과 같은 모양이라 새 계약을 만들지 않는다).
    """
    plan = deps.plan(request, security)
    candidates = await deps.retrieve(plan, security)
    fused = deps.fuse(candidates, plan)
    hydrated = await deps.hydrate(fused, plan, security)
    postprocessed = deps.postprocess(hydrated, plan)
    context_pack = deps.pack(postprocessed, plan, security)

    rendered: RenderedContext | None = None
    if render:
        renderer = resolve_renderer(request)
        render_fn = deps.renderers.get(renderer) or deps.renderers.get(Renderer.markdown)
        if render_fn is not None:
            rendered = render_fn(context_pack, query_text=request.query)

    return QueryPipelineResult(plan=plan, ranked_set=postprocessed, context_pack=context_pack, rendered=rendered)


#: F4-01~03 실 모듈(`retrieval.planner`/`channels`/`fusion`/`hydrate`/`postprocess.*`/`pack.packer`)과
#: 렌더러(`render.markdown`/`anthropic_search_result`)를 실제로 이 6-Protocol에 맞춰 묶는 일은 이
#: 파일이 하지 않는다 — `pipelines`는 `retrieval`·`render`(형제 계층)를 임포트할 수 없다(바이블 §12,
#: import-linter). 그 배선은 F5(api/mcp/cli, 상위 계층) 또는 F4 배치 검증자의 몫이다(open_issues).
