"""`pipelines.query.run_query` e2e — 한국어 질의 3종으로 전체 인프로세스 체인과 `cite_id` 왕복을 검증한다.

역할: plan~pack 단계를 페이크(`QueryPipelineDeps`)로 대체하고, `pack` 단계만
`tests/contracts/fixtures/context-pack/001.json`(F4-01~03 실 모듈 없이도 스키마 유효한
`ContextPack`)을 돌려주게 해 `run_query`의 체인 순서·렌더러 선택(§4.3)과 실제 렌더러 2종
(`markdown`, `anthropic_search_result`)의 `cite_id` 왕복(`testing.renderer_citation_roundtrip`)을
검증한다.
설계 근거: 바이블 §4.3 검색 파이프라인 표; `docs/13-implementation/wp/WP-404-render-and-query-
pipeline.md` §0·§9. F4-01~03 실 모듈이 붙는 전체 배선(F3 샘플 → 실 검색 → 실 팩)은 `pipelines/
query.py`의 `# DEFERRED` 주석이 표시하듯 api/mcp/cli 계층이 필요한 별도 WP로 남는다(F4 배치 검증
open_issue — 이 계층은 `pipelines`가 `retrieval`·`render`를 import할 수 없어(§12) 여기서 배선할
수 없다).
구성: `_load_pack`/`_assert_roundtrip`/`_request`/`_fake_deps` 픽스처 헬퍼 + 렌더러 2종 왕복 테스트.
불변식: 픽스처 출처는 `tests/contracts/fixtures/context-pack/001.json`(3항목, `conflicts_with`
포함, `render_hints.data_marking=delimit`) — 이미 스키마 유효성이 검증된 고정 픽스처를 재사용한다.
검증 계층: 1층(여기서 검증) — 페이크 의존성만, 외부 자원 없음.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import pytest

from rag_platform.contracts import common_types
from rag_platform.contracts.context_pack import ContextPack
from rag_platform.contracts.query_request import QueryRequest, TargetModel
from rag_platform.pipelines import query
from rag_platform.render import anthropic_search_result, citation_map, markdown
from rag_platform.sdk.stage import StageError
from rag_platform.testing import renderer_citation_roundtrip as roundtrip

_FIXTURE_PATH = Path(__file__).resolve().parents[1] / "contracts" / "fixtures" / "context-pack" / "001.json"

_SECURITY = common_types.SecurityContext(
    tenant_id="01J9ZQ4K7X2M8N3P5R6S7T8V9W",
    principals=["user:kim.minsu@example.go.kr", "group:mois_records", "tenant:*"],
    collection_ids=["01J9ZQ5A1B2C3D4E5F6G7H8J9K"],
    as_of="2026-09-22T09:00:00.000Z",
    classification_max="confidential",
    policy_version="1",
    auth_method="api_key",
    visible_set=["public", "tenant"],
)


def _load_pack(**overrides: Any) -> ContextPack:
    data = json.loads(_FIXTURE_PATH.read_text(encoding="utf-8"))
    data.update(overrides)
    return ContextPack.model_validate(data)


def _assert_roundtrip(pack: ContextPack, rendered: object) -> None:
    """`assert_renderer_citation_roundtrip`은 매핑(JSON) 형태를 받는다.

    `testing.renderer_citation_roundtrip._field()`는 최상위 필드의 `RootModel`(`CiteId`/`Hex64`/
    `Ulid`)은 `.root`로 벗기도록 F4 배치 검증으로 고쳤지만(이전 판은 `str(value)`가 `"root='d2'"`를
    내는 함정이 있었다), `segment_range`처럼 원소가 각각 `RootModel`인 컨테이너 필드까지는 벗기지
    않는다(잔여 갭, open_issues) — 그래서 이 테스트는 여전히 `model_dump(mode="json")`로 덤프해
    순수 값만 넘긴다.
    """
    items = [item.model_dump(mode="json") for item in pack.items]
    citation_entries = [entry.model_dump(mode="json") for entry in rendered.citation_map]  # type: ignore[attr-defined]
    roundtrip.assert_renderer_citation_roundtrip(items, citation_entries)


#: 이 테스트(호출자/상위 계층)가 `pipelines.query`의 6-Protocol에 렌더러 2종을 묶는다 — `pipelines`
#: 자신은 `render`를 임포트할 수 없다(바이블 §12 형제 계층 규칙, query.py 모듈 docstring 참고).
_RENDERERS: dict[common_types.Renderer, query.RendererFn] = {
    common_types.Renderer.markdown: lambda pack, *, query_text: markdown.render(pack, query_text=query_text),
    common_types.Renderer.anthropic_search_result: lambda pack, *, query_text: anthropic_search_result.render(
        pack, query_text=query_text
    ),
}


def _fake_deps(pack: ContextPack) -> query.QueryPipelineDeps:
    """plan~postprocess는 통과만 시키는 페이크, `pack`만 고정 픽스처를 반환한다."""

    def _plan(request: QueryRequest, security: common_types.SecurityContext) -> object:
        return {"request": request, "security": security}

    async def _retrieve(plan: object, security: common_types.SecurityContext) -> object:
        return {"plan": plan}

    def _fuse(candidates: object, plan: object) -> object:
        return {"candidates": candidates, "plan": plan}

    async def _hydrate(ranked: object, plan: object, security: common_types.SecurityContext) -> object:
        return ranked

    def _postprocess(ranked: object, plan: object) -> object:
        return ranked

    def _pack(ranked: object, plan: object, security: common_types.SecurityContext) -> ContextPack:
        return pack

    return query.QueryPipelineDeps(
        plan=_plan,
        retrieve=_retrieve,
        fuse=_fuse,
        hydrate=_hydrate,
        postprocess=_postprocess,
        pack=_pack,
        renderers=_RENDERERS,
    )


def _request(query_text: str, query_id: str, **overrides: Any) -> QueryRequest:
    payload: dict[str, Any] = {
        "schema_version": "1.0.0",
        "query_id": query_id,
        "query": query_text,
        "collection_ids": ["01J9ZQ5A1B2C3D4E5F6G7H8J9K"],
        "requested_at": "2026-09-23T00:00:00.000Z",
    }
    payload.update(overrides)
    return QueryRequest.model_validate(payload)


def test_run_query_markdown_roundtrip() -> None:
    """질의 1: `renderer=markdown` 명시 — 체인 실행 후 `[dN]` 왕복 검증."""
    pack = _load_pack(pack_id="01JAC5F6G7H8J9KMNPQRSTVW01", query_id="01JAC5F6G7H8J9KMNPQRSTVX01")
    request = _request(
        "공공기록물의 보존기간은 어떻게 책정하는가?",
        "01JAC5F6G7H8J9KMNPQRSTVX01",
        renderer="markdown",
    )
    result = asyncio.run(query.run_query(request, _SECURITY, _fake_deps(pack)))

    assert result.rendered is not None
    assert result.rendered.renderer == common_types.Renderer.markdown
    assert isinstance(result.rendered.provider_payload, str)
    assert "[d1]" in result.rendered.provider_payload
    assert "질의: 공공기록물의 보존기간은 어떻게 책정하는가?" in result.rendered.provider_payload
    _assert_roundtrip(result.context_pack, result.rendered)


def test_run_query_anthropic_search_result_roundtrip() -> None:
    """질의 2: `renderer=anthropic_search_result` 명시 — native 인용·모델 미포함·tenant_id 미노출 검증."""
    pack = _load_pack(pack_id="01JAC5F6G7H8J9KMNPQRSTVW02", query_id="01JAC5F6G7H8J9KMNPQRSTVX02")
    request = _request(
        "개인정보 관련 기록물의 보존기간 기준은 무엇인가?",
        "01JAC5F6G7H8J9KMNPQRSTVX02",
        renderer="anthropic_search_result",
    )
    result = asyncio.run(query.run_query(request, _SECURITY, _fake_deps(pack)))

    assert result.rendered is not None
    assert result.rendered.renderer == common_types.Renderer.anthropic_search_result
    payload = result.rendered.provider_payload
    assert isinstance(payload, dict)
    payload_text = json.dumps(payload, ensure_ascii=False)
    assert "tenant_id" not in payload_text
    assert '"model"' not in payload_text
    content = payload["messages"][0]["content"]
    search_results = [block for block in content if block["type"] == "search_result"]
    assert len(search_results) == 3
    assert all(block["citations"] == {"enabled": True} for block in search_results)
    assert all(citation_map.as_str(pack.tenant_id) not in block["source"] for block in search_results)
    _assert_roundtrip(result.context_pack, result.rendered)


def test_run_query_renderer_derived_from_target_model() -> None:
    """질의 3: `renderer` 미지정 + `target_model.provider=anthropic` → `anthropic_search_result` 도출."""
    pack = _load_pack(pack_id="01JAC5F6G7H8J9KMNPQRSTVW03", query_id="01JAC5F6G7H8J9KMNPQRSTVX03")
    request = _request(
        "기록물철 생산 시 보존기간은 어떻게 정해지는가?",
        "01JAC5F6G7H8J9KMNPQRSTVX03",
        target_model=TargetModel(provider="anthropic", model="claude-placeholder"),
    )
    assert query.resolve_renderer(request) == common_types.Renderer.anthropic_search_result

    result = asyncio.run(query.run_query(request, _SECURITY, _fake_deps(pack)))

    assert result.rendered is not None
    assert result.rendered.renderer == common_types.Renderer.anthropic_search_result
    _assert_roundtrip(result.context_pack, result.rendered)


def test_anthropic_search_result_conflict_notice() -> None:
    """픽스처의 `d1`↔`d3` `conflicts_with`가 첫 `text` 블록 안내 문구로 나오는지 검증(§4.1·§4.4)."""
    pack = _load_pack()
    rendered = anthropic_search_result.render(pack, query_text="질의 텍스트")
    content = rendered.provider_payload["messages"][0]["content"]
    assert content[0]["type"] == "text"
    assert "검색 결과 3건" in content[0]["text"]
    assert "결과 2" in content[0]["text"]
    assert "결과 3" in content[0]["text"]
    assert content[-1]["text"] == "질의: 질의 텍스트"


def test_markdown_data_marking_delimit() -> None:
    """픽스처 `render_hints.data_marking=delimit`이면 `<<<DATA dN>>>` 구분자가 본문을 감싼다(§4.7 L3)."""
    pack = _load_pack()
    assert pack.render_hints.data_marking == common_types.DataMarking.delimit
    rendered = markdown.render(pack, query_text="질의 텍스트")
    assert "<<<DATA d1>>>" in rendered.provider_payload
    assert "<<</DATA d1>>>" in rendered.provider_payload


def test_citation_map_back_resolves_and_rejects_hallucination() -> None:
    """`citation_map.map_back`: 정상 위치는 `resolved`, 존재하지 않는 키는 `unresolved(unknown_key)`."""
    pack = _load_pack()
    rendered = anthropic_search_result.render(pack, query_text="질의 텍스트")
    first_item = pack.items[0]  # position=0 -> search_result_index=0 (cite_id d2)

    resolution = citation_map.map_back(
        rendered,
        pack,
        citation_map.SearchResultLocation(
            search_result_index=0,
            start_block_index=0,
            end_block_index=1,
            cited_text=first_item.segments[0].text,
        ),
    )
    assert resolution.status == "resolved"
    assert resolution.cite_id == citation_map.as_str(first_item.cite_id)
    assert resolution.cited_text_match is True

    unresolved = citation_map.map_back(
        rendered,
        pack,
        citation_map.SearchResultLocation(search_result_index=99, start_block_index=0, end_block_index=1),
    )
    assert unresolved.status == "unresolved"
    assert unresolved.reason == "unknown_key"


def test_anthropic_search_result_empty_pack_error_policy() -> None:
    """K=0이고 `empty_policy="error"`면 `StageError("render.empty_pack")`(§4.4 사전 검증)."""
    pack = _load_pack(items=[], omitted=[])
    with pytest.raises(StageError) as excinfo:
        anthropic_search_result.render(pack, query_text="질의", empty_policy="error")
    assert excinfo.value.code == "render.empty_pack"

    rendered = anthropic_search_result.render(pack, query_text="질의", empty_policy="text")
    content = rendered.provider_payload["messages"][0]["content"]
    assert content == [{"type": "text", "text": "No results found."}]
