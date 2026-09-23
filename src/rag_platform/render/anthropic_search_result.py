"""`anthropic_search_result` 렌더러(정본) — `ContextPack`을 Anthropic `search_result` 블록 `RenderedContext`로 바꾼다.

역할: 바이블 §9.3(렌더러 정본, `anthropic_search_result` 1차) / §4.4(정본 렌더러 상세)의 구현.
항목 1개 → `search_result` 블록 1개, native 인용(`citations.enabled`), `source`에 `tenant_id`를
넣지 않고 내부 식별자는 `citation_map`에만 둔다.
설계 근거: `docs/04-pipelines/17-post-processing-and-context-packing.md` §4.1(공통 렌더 규칙)·
§4.4(`anthropic_search_result` 상세: 블록 조립, 위치 (a)/(b), 순서, `cache_control`, 모델 미포함,
사전 검증, 응답 인용)·§4.6(상충 안내 위치). 계약 `contracts/context_pack`(`ContextItem`)·
`contracts/rendered_context.py`.
구성: `render(pack, *, query_text=None, system_text=None, tool_result=False, tool_use_id=None,
cache_control=True, empty_policy="text")` — 진입점; `_search_result_block` — 항목 1개 → 블록 1개
(표 항목은 블록 1개, 그 외는 세그먼트 1개=텍스트 블록 1개); `_conflict_notice` — `conflicts_with`
쌍에서 팩 수준 안내 문구(§4.1 "상충 안내") 생성.
불변식·주의: 이 렌더러는 `model` 필드를 만들지 않는다(§4.4 "모델" 행 — 모델 ID 하드코딩 금지;
레퍼런스 `answer`가 감싼다). `citations.enabled`는 all-or-nothing(전 블록 true). `tool_result=True`면
`content`에 `search_result`만 허용되므로 상충 안내·질의 텍스트 블록을 넣지 않는다(§4.4 위치 (b)).
K=0이고 `empty_policy="error"`면 `StageError("render.empty_pack")`.
검증 계층: 1층(여기서 검증) — `tests/retrieval/test_query_e2e.py`.
"""

from __future__ import annotations

import json
import math
from typing import TYPE_CHECKING, Any, Literal

from rag_platform.contracts import common_types
from rag_platform.contracts.rendered_context import CitationMapEntry, RenderedContext
from rag_platform.render import citation_map as citation_map_mod
from rag_platform.render.markdown import header_line
from rag_platform.sdk.stage import StageError

if TYPE_CHECKING:
    from collections.abc import Sequence

    from rag_platform.contracts.context_pack import ContextPack

__all__ = ["render"]

_NO_RESULTS_TEXT = "No results found."


def _table_text(table: common_types.Table) -> str:
    if table.format_used == common_types.TableFormat.html:
        return table.html or ""
    if table.format_used == common_types.TableFormat.markdown:
        return table.markdown or ""
    return json.dumps(table.json_records or [], ensure_ascii=False)


def _version_label(item: common_types.ContextItem) -> str:
    header = item.header
    if header.doc_version_label:
        return header.doc_version_label
    if header.doc_date is not None:
        return citation_map_mod.as_str(header.doc_date)
    return ""


def _conflict_notice(items: Sequence[common_types.ContextItem]) -> str | None:
    """팩 수준 상충 안내(§4.1 "상충 안내", §4.4 위치 (a) 첫 `text` 블록)."""
    if not items:
        return None
    by_cite_id = {citation_map_mod.as_str(item.cite_id): item for item in items}
    pairs: dict[frozenset[str], tuple[common_types.ContextItem, common_types.ContextItem]] = {}
    for item in items:
        for conflict in item.conflicts_with or []:
            other = by_cite_id.get(citation_map_mod.as_str(conflict.cite_id))
            if other is None:
                continue
            key = frozenset({citation_map_mod.as_str(item.cite_id), citation_map_mod.as_str(other.cite_id)})
            pairs.setdefault(key, (item, other))
    if not pairs:
        return None
    clauses = []
    for first_item, second_item in pairs.values():
        first, second = sorted((first_item, second_item), key=lambda candidate: candidate.position)
        clauses.append(
            f"결과 {first.position + 1}({_version_label(first)})와 결과 {second.position + 1}"
            f"({_version_label(second)})은 같은 조문의 서로 다른 판이다."
        )
    return f"검색 결과 {len(items)}건. " + " ".join(clauses)


def _search_result_block(item: common_types.ContextItem, pack: ContextPack) -> dict[str, Any]:
    """항목 1개 → `search_result` 블록 1개(§4.4). 표 항목은 블록 1개로 강등."""
    source = (
        f"rag://{citation_map_mod.as_str(item.collection_id)}/{citation_map_mod.as_str(item.document_id)}"
        f"/{citation_map_mod.as_str(item.chunk_id)}"
    )
    title = header_line(item, pack)
    if item.tables:
        content: list[dict[str, Any]] = [{"type": "text", "text": "\n".join(_table_text(t) for t in item.tables)}]
    else:
        content = [{"type": "text", "text": segment.text} for segment in item.segments]
    for figure in item.figures or []:
        line = "[그림]" + (f" {figure.caption}" if figure.caption else "")
        if figure.alt_text:
            line += f" ({figure.alt_text})"
        content.append({"type": "text", "text": line})
    return {
        "type": "search_result",
        "source": source,
        "title": title,
        "content": content,
        "citations": {"enabled": True},
    }


def _approximate_token_count(payload: dict[str, Any] | str) -> int:
    """모델 API 없이 쓰는 근사 카운터(직렬화 문자 수 / 4, 최소 1) — `count_method=approximate`."""
    text = payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False)
    return max(1, math.ceil(len(text) / 4))


def render(
    pack: ContextPack,
    *,
    query_text: str | None = None,
    system_text: str | None = None,
    tool_result: bool = False,
    tool_use_id: str | None = None,
    cache_control: bool = True,
    empty_policy: Literal["text", "error"] = "text",
) -> RenderedContext:
    """`ContextPack` → `anthropic_search_result` `RenderedContext`(바이블 §9.3·§4.4).

    위치 (a)(기본): `system`(선택) + `messages[0].content = [안내?, search_result x K, 질의?]`.
    위치 (b)(`tool_result=True`, `tool_use_id` 필수): `content`는 `search_result`만(§4.4) — 안내·
    질의 텍스트 블록은 넣지 않는다. `cache_control=True`면 접두어 끝(`system` 마지막 블록)과 팩 끝
    (마지막 `search_result` 블록)에 `{"type":"ephemeral"}`을 둔다.
    """
    if tool_result and not tool_use_id:
        msg = "tool_use_id is required when tool_result=True (bible §4.4 위치 (b))"
        raise ValueError(msg)

    items = pack.items
    entries: list[CitationMapEntry] = []
    if not items:
        if empty_policy == "error":
            code = "render.empty_pack"
            detail = "ContextPack has no items"
            raise StageError(code, stage="render", detail=detail)
        blocks: list[dict[str, Any]] = [{"type": "text", "text": _NO_RESULTS_TEXT}]
    else:
        blocks = [_search_result_block(item, pack) for item in items]
        entries = [citation_map_mod.build_entry(item, index) for index, item in enumerate(items)]
        if cache_control:
            blocks[-1] = {**blocks[-1], "cache_control": {"type": "ephemeral"}}

    if tool_result:
        provider_payload: dict[str, Any] = {"type": "tool_result", "tool_use_id": tool_use_id, "content": blocks}
        stable_prefix: dict[str, Any] | None = None
        volatile_suffix: dict[str, Any] = provider_payload
    else:
        content = list(blocks)
        if items:
            # K=0(§4.4)은 "No results found." 단일 블록만 낸다 — 안내·질의 블록을 덧붙이지 않는다.
            notice = _conflict_notice(items)
            if notice:
                content = [{"type": "text", "text": notice}, *content]
            if query_text:
                content = [*content, {"type": "text", "text": f"질의: {query_text}"}]
        system_blocks: list[dict[str, Any]] | None = None
        if system_text:
            system_block: dict[str, Any] = {"type": "text", "text": system_text}
            if cache_control:
                system_block["cache_control"] = {"type": "ephemeral"}
            system_blocks = [system_block]
        stable_prefix = {"system": system_blocks} if system_blocks else None
        volatile_suffix = {"messages": [{"role": "user", "content": content}]}
        provider_payload = {**(stable_prefix or {}), **volatile_suffix}

    return RenderedContext(
        schema_version=pack.schema_version,
        schema_type="RenderedContext",
        pack_id=pack.pack_id,
        renderer=common_types.Renderer.anthropic_search_result,
        tenant_id=pack.tenant_id,
        collection_ids=pack.collection_ids,
        provider_payload=provider_payload,
        stable_prefix=stable_prefix,
        volatile_suffix=volatile_suffix,
        citation_map=entries,
        token_count_rendered=_approximate_token_count(provider_payload),
        count_method=common_types.CountMethod.approximate,
        warnings=[],
        pack_content_hash=pack.content_hash,
    )
