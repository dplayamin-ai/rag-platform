"""MCP 도구 3종의 핸들러 구현 — `search`/`get_document`/`list_collections`(05-api/05 §4~§9).

역할: MCP 도구 호출 인자(dict)를 검증해 주입된 서비스 계층(`QueryRunner`/`DocumentReader`/
`CollectionLister`)을 호출하고, 그 결과를 05-api/05 §4.2~4.4의 슬림 `outputSchema` + `xml_documents`
텍스트 + §9.3 정본 안내 문구로 렌더한다. SDK(`mcp` 패키지)에 의존하지 않는 순수 함수라
`server.py`를 거치지 않고 직접 호출·단위 테스트할 수 있다("도구 함수 단위 테스트").
설계 근거: `docs/05-api/05-mcp-server.md` §4(도구 정의)·§5(결과 렌더·20k 토큰 상한)·§6(커서)·
§7(반복 검색)·§8(오류 표현)·§9.3(안내 문구 정본), ADR-0025, 바이블 §5.7(`FilterableField`·
`ErrorCodeCatalog` 철자), §12(`mcp/` — 코어 로직 재구현 금지).
구성: `QueryRunner`/`DocumentReader`/`CollectionLister`(Protocol, 실 배선은 다른 WP) — `mcp/`가
`retrieval.*`·`api.*` 서비스 계층을 몰라도 되게 하는 경계; `ToolDeps`/`ToolResult`; `DocBlockView`/
`DocChunkView`/`DocumentContent`(§4.3 outputSchema 투영); `search`/`get_document`/
`list_collections`(공개 핸들러 3개) — 각각 인자 검증(로컬 pydantic 모델, MCP `inputSchema`의
런타임 등가물) → 커서 해석(있으면) → 서비스 호출 → 슬림 결과·텍스트·안내 문구 조립 → 20k 토큰
절단 → (필요 시) 커서 발급의 순서.
불변식·주의: 이 모듈은 `rag_platform.testing`을 임포트하지 않는다(운영 진입점,
import-linter `testing-not-in-production`) — 단위 테스트가 `ToolDeps`에 페이크/더블을 주입한다.
슬림 결과·오류 결과 어디에도 `tenant_id`·주체 문자열·`acl_*`·`record_id`·원시 점수를 넣지 않는다
(05 §5 공통 규칙 1). `render.mcp_tool_result`/`render.xml_documents` 전용 렌더러 모듈이 아직 없어
그 역할(슬림 팩 조립·XML 텍스트 렌더)을 이 모듈이 대신한다 — 승격은 DEFERRED(open_issues).
`ContextPack.items`는 `position`(렌더 위치, 예 `litm_alternating`) 오름차순이고 `rank`(관련도
순위, `cite_id = d{rank}`)와 다를 수 있다 — 페이지 선택(`top_k`)·예산 절단은 항상 `rank`
기준으로 하고(`_select_page_by_rank`, 05 §4.2·§5.1), 슬림화·직렬화만 방출 직전에 `position`
기준으로 다시 정렬해 순서 전략을 보존한다. `cite_id`는 재계산하지 않는다(05 §5 규칙 3).
검증 계층: 1층(여기서 검증) — `tests/mcp/test_mcp_tools.py`(페이크 `ToolDeps`, SDK 서버 미기동).
`# DEFERRED: 실 QueryRunner/DocumentReader/CollectionLister 배선과 그 위의 e2e는 이후 WP 몫`.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any, Literal, Protocol, runtime_checkable
from xml.sax.saxutils import escape as xml_escape

from pydantic import AnyUrl, BaseModel, ConfigDict, Field, ValidationError
from ulid import ULID

from rag_platform.contracts.common_types import (
    ErrorCodeCatalog,
    ErrorTypeUrn,
    FilterableField,
    FilterNode,
    Hex64,
    ProblemDetails,
    ResponseFormat,
)
from rag_platform.contracts.query_request import QueryRequest
from rag_platform.mcp.cursor_store import CursorRecord, CursorStore, security_context_hash
from rag_platform.sdk.hashing import hash_of

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence

    from rag_platform.contracts.collection_spec import CollectionSpec as CollectionSpecType
    from rag_platform.contracts.common_types import ContextItem, SecurityContext
    from rag_platform.contracts.context_pack import ContextPack as ContextPackType

__all__ = [
    "MAX_RESULT_TOKENS",
    "CollectionLister",
    "DocBlockView",
    "DocChunkView",
    "DocumentContent",
    "DocumentReader",
    "QueryRunner",
    "ToolDeps",
    "ToolResult",
    "get_document",
    "list_collections",
    "search",
]

#: 05 §5.1 결과 토큰 상한(초안 목표). `tokens(content[0].text) + tokens(canonical_json(structuredContent))`.
MAX_RESULT_TOKENS = 20_000
_MAX_SEEN_CHUNK_IDS = 1000
_ULID_RE = re.compile(r"^[0-9A-HJKMNP-TV-Z]{26}$")
_CUSTOM_FIELD_RE = re.compile(r"^custom\.[a-z0-9_]+$")
_FIXED_FILTERABLE_FIELDS = {member.value for member in FilterableField}


def _now_iso() -> str:
    """`DateTime` 계약 패턴(RFC 3339 UTC, `Z` 접미)에 맞는 현재 시각 문자열(mcp는 shell/api 층)."""
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _new_trace_id() -> str:
    """W3C trace-id 형식(소문자 hex 32)의 자리표시 값 — 실 분산 추적 연동은 telemetry 몫."""
    return hash_of("mcp-trace", str(ULID()))[:32]


def _approx_tokens(text: str) -> int:
    """근사 토큰 카운트(`CountMethod.approximate`): 코드포인트 4개당 1토큰 올림."""
    return math.ceil(len(text) / 4) if text else 0


def _approx_json_tokens(data: Any) -> int:
    return _approx_tokens(json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")))


# ---------------------------------------------------------------------------------------------
# 서비스 경계 Protocol — 실 배선은 이후 WP(api/mcp 공유 서비스 계층 조립) 몫(open_issues)
# ---------------------------------------------------------------------------------------------


@runtime_checkable
class QueryRunner(Protocol):
    """`search`가 위임하는 질의 실행: `QueryRequest` + `SecurityContext` → `ContextPack`."""

    async def __call__(self, request: QueryRequest, security: SecurityContext) -> ContextPackType:
        """Run the underlying query pipeline and return the resulting `ContextPack`."""
        ...


@dataclass(frozen=True)
class DocBlockView:
    """`get_document` outputSchema `DocBlock`의 런타임 투영(05 §4.3)."""

    block_id: str
    type: str
    level: int | None
    numbering_label: str | None
    heading_path: tuple[str, ...]
    text: str
    text_source: str
    page: int | None
    element_path: str


@dataclass(frozen=True)
class DocChunkView:
    """`get_document` outputSchema `DocChunk`의 런타임 투영(05 §4.3)."""

    chunk_id: str
    item_kind: str
    level: int
    parent_chunk_id: str | None
    ordinal: int
    heading_path: tuple[str, ...]
    text: str
    text_source: str


@dataclass(frozen=True)
class DocumentContent:
    """`DocumentReader`가 돌려주는 문서 전체(투영 완료, 미절단) — 절단·커서는 이 모듈이 담당."""

    document_id: str
    collection_id: str
    doc_version: str
    title: str
    source_uri: str
    language: str
    doc_date: str | None
    quality: Literal["full", "degraded"]
    blocks: tuple[DocBlockView, ...] = ()
    chunks: tuple[DocChunkView, ...] = ()


@runtime_checkable
class DocumentReader(Protocol):
    """`get_document`가 위임하는 문서 조회. 접근 불가·미존재는 `None`(존재 비노출, 05 §4.3)."""

    async def __call__(self, document_id: str, view: str, security: SecurityContext) -> DocumentContent | None:
        """Return the full (unpaginated) document content, or `None` if not found/forbidden."""
        ...


@runtime_checkable
class CollectionLister(Protocol):
    """`list_collections`가 위임하는 조회: Cedar `allowed_collections`만(E14)."""

    async def __call__(self, security: SecurityContext) -> list[CollectionSpecType]:
        """Return the collections the current principal may search."""
        ...


@dataclass(frozen=True)
class ToolDeps:
    """세 핸들러가 공유하는 주입 묶음."""

    query_runner: QueryRunner
    document_reader: DocumentReader
    collection_lister: CollectionLister
    cursor_store: CursorStore
    max_result_tokens: int = MAX_RESULT_TOKENS


@dataclass(frozen=True)
class ToolResult:
    """`CallToolResult`의 SDK 미의존 등가물 — `server.py`가 그대로 감싼다."""

    is_error: bool
    structured_content: dict[str, Any]
    text: str


# ---------------------------------------------------------------------------------------------
# 오류 빌더(05 §8) — 텍스트 형식 "{code} ({pointer}): {detail}. {hint}", en / ko 병기
# ---------------------------------------------------------------------------------------------

_ERROR_TITLES: dict[ErrorCodeCatalog, str] = {
    ErrorCodeCatalog.contract_violation: "Contract violation",
    ErrorCodeCatalog.plan_collection_forbidden: "Collection access forbidden",
    ErrorCodeCatalog.plan_filter_field_forbidden: "Filter field forbidden",
    ErrorCodeCatalog.auth_forbidden: "Forbidden",
}
_ERROR_STATUS: dict[ErrorCodeCatalog, int] = {
    ErrorCodeCatalog.contract_violation: 400,
    ErrorCodeCatalog.plan_collection_forbidden: 403,
    ErrorCodeCatalog.plan_filter_field_forbidden: 422,
    ErrorCodeCatalog.auth_forbidden: 403,
}


class ToolError(Exception):
    """핸들러 내부에서 던지고 각 공개 함수의 최상위 `try`가 `ToolResult`로 변환하는 오류."""

    def __init__(  # noqa: PLR0917 - each bilingual detail/hint needs its own name (05 §8 text format)
        self,
        code: ErrorCodeCatalog,
        pointer: str,
        detail_en: str,
        hint_en: str,
        detail_ko: str,
        hint_ko: str,
        *,
        retryable: bool = False,
    ) -> None:
        """Carry every part `_error_result` needs to build both the text line and `ProblemDetails`."""
        super().__init__(detail_en)
        self.code = code
        self.pointer = pointer
        self.detail_en = detail_en
        self.hint_en = hint_en
        self.detail_ko = detail_ko
        self.hint_ko = hint_ko
        self.retryable = retryable


def _error_result(error: ToolError) -> ToolResult:
    """05 §8: `content[0]` 텍스트 한 줄 + `structuredContent = ProblemDetails`."""
    text = (
        f"{error.code.value} ({error.pointer}): {error.detail_en}. {error.hint_en} / {error.detail_ko}. {error.hint_ko}"
    )
    problem = ProblemDetails(
        type=ErrorTypeUrn(AnyUrl(f"urn:rag:error:{error.code.value}")),
        title=_ERROR_TITLES.get(error.code, "Tool execution error"),
        status=_ERROR_STATUS.get(error.code, 400),
        detail=f"{error.pointer}: {error.detail_en}",
        instance="/mcp",
        code=error.code,
        retryable=error.retryable,
        trace_id=_new_trace_id(),
    )
    return ToolResult(is_error=True, structured_content=problem.model_dump(mode="json"), text=text)


def _validation_error(pointer: str, exc: ValidationError) -> ToolError:
    first = exc.errors()[0]
    msg = str(first.get("msg", "invalid value"))
    return ToolError(
        ErrorCodeCatalog.contract_violation,
        pointer,
        f"{pointer}: {msg}",
        "Fix the argument per the tool's inputSchema and retry.",
        f"{pointer}: {msg}",
        "도구 inputSchema에 맞게 인자를 수정한 뒤 다시 호출하십시오.",
    )


def _cursor_error(pointer: str) -> ToolError:
    """05 §6.4: 만료·변조·다른 테넌트·다른 도구·주체 불일치는 모두 이 오류(존재 비노출)."""
    return ToolError(
        ErrorCodeCatalog.contract_violation,
        pointer,
        "cursor expired or not issued to this principal",
        "Re-run search without cursor.",
        "커서가 만료되었거나 이 사용자에게 발급된 것이 아닙니다",
        "cursor 없이 다시 검색하십시오.",
    )


def _collection_forbidden_error() -> ToolError:
    return ToolError(
        ErrorCodeCatalog.plan_collection_forbidden,
        "/collection_ids",
        "no accessible collection matches the requested collection_ids",
        "Call list_collections to see which collections you may access.",
        "요청한 collection_ids 중 접근 가능한 컬렉션이 없습니다",
        "list_collections로 접근 가능한 컬렉션을 확인하십시오.",
    )


def _too_many_collections_error() -> ToolError:
    return ToolError(
        ErrorCodeCatalog.contract_violation,
        "/collection_ids",
        "more than 20 collections are accessible; specify collection_ids",
        "See list_collections.",
        "접근 가능한 컬렉션이 20개를 넘습니다; collection_ids를 지정하십시오",
        "list_collections를 참고하십시오.",
    )


def _filter_field_forbidden_error(field_name: str) -> ToolError:
    allowed = ", ".join(sorted(_FIXED_FILTERABLE_FIELDS))
    return ToolError(
        ErrorCodeCatalog.plan_filter_field_forbidden,
        "/filters",
        f"filter field '{field_name}' is not allowed",
        f"Allowed fields: {allowed}, custom.*.",
        f"필터 필드 '{field_name}'은(는) 허용되지 않습니다",
        f"허용 필드: {allowed}, custom.*",
    )


def _document_not_found_error() -> ToolError:
    return ToolError(
        ErrorCodeCatalog.contract_violation,
        "/document_id",
        "document not found",
        "Verify the document_id from a search result.",
        "문서를 찾을 수 없습니다",
        "search 결과의 document_id를 확인하십시오.",
    )


# ---------------------------------------------------------------------------------------------
# 인자 검증(로컬 pydantic 모델 — MCP `inputSchema`의 런타임 등가물)
# ---------------------------------------------------------------------------------------------


class SearchArgs(BaseModel):
    """05 §4.2 `inputSchema`의 런타임 등가물."""

    model_config = ConfigDict(extra="forbid")

    query: str = Field(..., min_length=1, max_length=4000)
    collection_ids: list[str] | None = Field(None, min_length=1, max_length=20)
    top_k: int = Field(10, ge=1, le=50)
    filters: dict[str, Any] | None = None
    response_format: Literal["concise", "detailed"] = "concise"
    cursor: str | None = Field(None, min_length=1, max_length=512)


class GetDocumentArgs(BaseModel):
    """05 §4.3 `inputSchema`의 런타임 등가물."""

    model_config = ConfigDict(extra="forbid")

    document_id: str = Field(..., pattern=_ULID_RE.pattern)
    view: Literal["parsed", "normalized", "chunks"] = "normalized"
    cursor: str | None = Field(None, min_length=1, max_length=512)


class ListCollectionsArgs(BaseModel):
    """05 §4.4 `inputSchema`의 런타임 등가물 — 인자 없음."""

    model_config = ConfigDict(extra="forbid")


def _walk_filter_fields(node: Any) -> Iterator[str]:
    """`FilterNode` DSL 트리에서 리프의 `field` 값을 모두 순회(화이트리스트 검사용)."""
    if not isinstance(node, dict):
        return
    if "field" in node:
        yield str(node["field"])
        return
    for connective in ("and", "or"):
        for child in node.get(connective) or []:
            yield from _walk_filter_fields(child)
    if "not" in node:
        yield from _walk_filter_fields(node["not"])


def _check_filters(filters: dict[str, Any] | None) -> None:
    """05 §14 표: 화이트리스트 밖 필드는 `plan.filter_field_forbidden`, 그 외 구조 오류는 검증 오류."""
    if filters is None:
        return
    for field_name in _walk_filter_fields(filters):
        if field_name not in _FIXED_FILTERABLE_FIELDS and not _CUSTOM_FIELD_RE.match(field_name):
            raise _filter_field_forbidden_error(field_name)
    try:
        FilterNode.model_validate(filters)
    except ValidationError as exc:
        pointer = "/filters"
        raise _validation_error(pointer, exc) from exc


# ---------------------------------------------------------------------------------------------
# 안내 문구(05 §9.3 정본, 한/영 병기)
# ---------------------------------------------------------------------------------------------


def _guidance_search_page(count: int, *, truncated: bool, next_cursor: str | None) -> str:
    if truncated and next_cursor:
        return (
            f'결과 {count}건 표시(더 있음). 이어서 보려면 같은 query에 cursor="{next_cursor}"를 넣어 '
            "search를 호출하십시오(10분 유효). 범위를 좁히려면 filters(doc_date, doc_type, department, "
            "tags, lang)나 top_k를 조정하십시오. cite_id는 이 응답 안에서만 유효합니다. / "
            f"Showing {count} results (more available). To continue, call search with the same query "
            f'and cursor="{next_cursor}" (valid 10 minutes). To narrow, adjust filters (doc_date, '
            "doc_type, department, tags, lang) or top_k. cite_id values are valid within this response only."
        )
    return f"결과 {count}건 표시(전체). / Showing {count} results (all)."


def _guidance_insufficiency(status: str, missing_aspects: Sequence[str]) -> str:
    missing = ", ".join(missing_aspects) if missing_aspects else "-"
    return (
        f"근거가 충분하지 않습니다(sufficiency={status}). 빠진 관점: {missing}. 질의를 바꾸거나 "
        "filters를 완화해 다시 검색하십시오. / "
        f"Evidence is insufficient (sufficiency={status}). Missing: {missing}. Rephrase or relax "
        "filters and search again."
    )


_GUIDANCE_CURSOR_ISSUE_FAILED = (
    "추가 결과가 있으나 지금은 이어받기 핸들을 발급할 수 없습니다. top_k를 늘리거나 filters로 범위를 "
    "좁혀 다시 검색하십시오. / More results exist but a continuation handle cannot be issued right now. "
    "Increase top_k or narrow with filters and search again."
)
_GUIDANCE_EXCLUSION_LIMIT = (
    "누적 제외 상한(1,000)에 도달했습니다. filters로 범위를 좁혀 새로 검색하십시오. / "
    "Reached the exclusion limit (1,000). Narrow with filters and start a new search."
)
_GUIDANCE_INDEX_REFRESHED = (
    "문서 색인이 갱신되어 이전 페이지와 일부 겹치거나 빠질 수 있습니다. / "
    "The index was updated; this page may overlap with or miss items from the previous one."
)


def _guidance_get_document_page(first: int, last: int, *, truncated: bool, next_cursor: str | None) -> str:
    if truncated and next_cursor:
        return (
            f"문서의 {first}~{last} 블록 표시(더 있음). 이어 읽으려면 같은 document_id에 "
            f'cursor="{next_cursor}"를 넣으십시오. / Showing blocks {first}-{last} (more). Continue with '
            f'the same document_id and cursor="{next_cursor}".'
        )
    return f"문서의 {first}~{last} 블록 표시(전체). / Showing blocks {first}-{last} (all)."


# ---------------------------------------------------------------------------------------------
# `search`
# ---------------------------------------------------------------------------------------------


def _slim_item(item: ContextItem, response_format: str) -> dict[str, Any]:
    """05 §4.2 `SlimItem` — `Header`·`Provenance`는 계약 필드 집합과 1:1이라 그대로 투영한다."""
    slim: dict[str, Any] = {
        "cite_id": item.cite_id.root,
        "chunk_id": item.chunk_id.root,
        "collection_id": item.collection_id.root,
        "document_id": item.document_id.root,
        "header": item.header.model_dump(mode="json"),
        "confidence_tier": item.confidence_tier.value,
        "text_source": item.text_source.value,
        "provenance": [p.model_dump(mode="json") for p in item.provenance],
    }
    if response_format == "detailed":
        slim["text"] = item.text
    else:
        slim["text_preview"] = item.text[:200]
    return slim


def _xml_documents(slim_items: Sequence[dict[str, Any]]) -> str:
    """`xml_documents` 텍스트(05 §5 표) — 전용 렌더러가 없어 이 모듈이 임시로 담당(open_issues)."""
    parts = ["<documents>"]
    for slim in slim_items:
        header = slim["header"]
        section = " > ".join(header.get("section_path") or [])
        content = slim.get("text", slim.get("text_preview", ""))
        parts.append(
            f'<document index="{xml_escape(slim["cite_id"])}">\n'
            f"<source>{xml_escape(header.get('source_uri', ''))}</source>\n"
            f"<title>{xml_escape(header.get('title', ''))}</title>\n"
            f"<section>{xml_escape(section)}</section>\n"
            f"<date>{xml_escape(header.get('doc_date') or '')}</date>\n"
            f"<confidence>{xml_escape(slim['confidence_tier'])}</confidence>\n"
            f"<document_content>{xml_escape(content)}</document_content>\n"
            "</document>"
        )
    parts.append("</documents>")
    return "\n".join(parts)


def _build_structured(
    pack: ContextPackType, slim_items: list[dict[str, Any]], *, truncated: bool, next_cursor: str | None
) -> dict[str, Any]:
    return {
        "schema_version": pack.schema_version.root,
        "pack_id": pack.pack_id.root,
        "items": slim_items,
        "sufficiency": pack.sufficiency.model_dump(mode="json"),
        "truncated": truncated,
        "next_cursor": next_cursor,
    }


def _select_page_by_rank(items: Sequence[ContextItem], top_k: int) -> list[ContextItem]:
    """05 §4.2 `top_k`는 관련도 순위(`rank`) 기준 페이지 크기다 — `position`(렌더 위치)이 아니다.

    `ContextPack.items`는 `position`(렌더 순서, 예: `litm_alternating`이면 `rank`와 다르다) 오름차순
    이므로 `pack.items[:top_k]`로 자르면 관련도 상위권이 페이지 밖으로 빠질 수 있다(예 K=3 litm
    render order `[r2, r3, r1]`에서 `items[:2]`는 `d1`을 빠뜨린다). `rank` 오름차순으로 상위
    `min(top_k, K)`개, 즉 `d1..d{min(top_k,K)}`를 고른다.
    """
    by_rank = sorted(items, key=lambda it: it.rank)
    return by_rank[: min(top_k, len(by_rank))]


def _fit_search_page_to_budget(
    pack: ContextPackType,
    items: list[ContextItem],
    response_format: str,
    max_tokens: int,
) -> tuple[list[dict[str, Any]], str, bool]:
    """05 §5.1 절단 방법 (2)~(3): 하위 순위부터 제거, 0건이면 `concise`로 강등해 1건 재시도.

    `items`는 `_select_page_by_rank`가 고른 페이지로 `rank` 오름차순이어야 한다. 제거는 이 순서의
    끝(선택된 페이지 안에서 가장 낮은 관련도)에서만 일어나므로 남는 `cite_id`가 항상 `d1..dM`
    연속이다(05 §5.1 "하위 순위부터 제거"). 슬림화·직렬화는 방출 직전에 원래 `position`(렌더
    순서, 순서 전략 보존) 오름차순으로 다시 정렬한 뒤에만 하므로 `cite_id`는 관련도순 그대로,
    화면에 나가는 순서만 전략을 따른다.
    """
    working = list(items)  # rank 오름차순 유지
    dropped = False
    while working:
        by_position = sorted(working, key=lambda it: it.position)
        slim = [_slim_item(it, response_format) for it in by_position]
        structured = _build_structured(pack, slim, truncated=False, next_cursor=None)
        text = _xml_documents(slim)
        total = _approx_tokens(text) + _approx_json_tokens(structured)
        if total <= max_tokens:
            return slim, text, dropped
        working = working[:-1]  # 가장 낮은 관련도(가장 큰 rank) 제거
        dropped = True
    if items:
        fallback = min(items, key=lambda it: it.rank)  # d1 — pack.items[0]이 아니라 관련도 1위
        slim = [_slim_item(fallback, "concise")]
        return slim, _xml_documents(slim), True
    return [], _xml_documents([]), dropped


async def search(  # noqa: PLR0912, PLR0915 - cursor vs. fresh-query branching and budget bookkeeping (05 §4.2)
    args: dict[str, Any], security: SecurityContext, deps: ToolDeps
) -> ToolResult:
    """05 §4.2 `search` 핸들러. `args`는 JSON-RPC `tools/call` 인자(dict)."""
    try:
        parsed = SearchArgs.model_validate(args)
    except ValidationError as exc:
        return _error_result(_validation_error("/", exc))

    try:
        if parsed.filters is not None:
            _check_filters(parsed.filters)

        stored_record: CursorRecord | None = None
        if parsed.cursor is not None:
            stored_record = await deps.cursor_store.redeem(
                tenant_id=security.tenant_id.root,
                cursor_id=parsed.cursor,
                tool="search",
                principals=[p.root for p in security.principals],
                collection_ids=[c.root for c in security.collection_ids],
                classification_max=security.classification_max.value,
                visible_set=[v.value for v in security.visible_set],
            )
            if stored_record is None:
                return _error_result(_cursor_error("/cursor"))

        if stored_record is not None:
            stored_request = stored_record.query_request or {}
            query_text = str(stored_request["query"])
            collection_ids = list(stored_request["collection_ids"])
            top_k = int(stored_request["top_k"])
            filters = stored_request.get("filters")
            response_format = str(stored_request["response_format"])
            exclude_ids = list(stored_record.seen_chunk_ids)
            prior_offset = stored_record.offset
        else:
            query_text = parsed.query
            if parsed.collection_ids is not None:
                collection_ids = sorted(set(parsed.collection_ids) & {c.root for c in security.collection_ids})
                if not collection_ids:
                    return _error_result(_collection_forbidden_error())
            else:
                allowed = [c.root for c in security.collection_ids]
                if len(allowed) > 20:  # noqa: PLR2004 - 05 §4.2 표의 고정 상한(계약 collection_ids maxItems)
                    return _error_result(_too_many_collections_error())
                collection_ids = allowed
            top_k = parsed.top_k
            filters = parsed.filters
            response_format = parsed.response_format
            exclude_ids = []
            prior_offset = 0

        request = QueryRequest(
            schema_version="1.0.0",
            query_id=str(ULID()),
            query=query_text,
            collection_ids=collection_ids,
            filters=filters,
            top_k=top_k,
            response_format=ResponseFormat(response_format),
            exclude_ids=[Hex64(cid) for cid in exclude_ids] or None,
            requested_at=_now_iso(),
        )
        pack = await deps.query_runner(request, security)

        page_items = _select_page_by_rank(pack.items, top_k)
        page_count = len(page_items)
        slim_items, text, dropped_for_budget = _fit_search_page_to_budget(
            pack, page_items, response_format, deps.max_result_tokens
        )
        returned_chunk_ids = [item["chunk_id"] for item in slim_items]
        seen = (exclude_ids + returned_chunk_ids)[-_MAX_SEEN_CHUNK_IDS:]

        needs_more = page_count < len(pack.items) or dropped_for_budget
        truncated = False
        next_cursor: str | None = None
        exclusion_limit_hit = len(seen) >= _MAX_SEEN_CHUNK_IDS and needs_more

        if needs_more and not exclusion_limit_hit:
            issue_hash = security_context_hash(
                tenant_id=security.tenant_id.root,
                principals=[p.root for p in security.principals],
                collection_ids=collection_ids,
                as_of=security.as_of.root,
                classification_max=security.classification_max.value,
                visible_set=[v.value for v in security.visible_set],
            )
            issued_at = _now_iso()
            expires_at = (
                (datetime.now(UTC) + timedelta(seconds=deps.cursor_store.ttl_s)).isoformat().replace("+00:00", "Z")
            )
            record = CursorRecord(
                tenant_id=security.tenant_id.root,
                tool="search",
                offset=prior_offset + 1,
                security_context_hash=issue_hash,
                as_of=security.as_of.root,
                issued_at=issued_at,
                expires_at=expires_at,
                query_id=request.query_id.root,
                query_request={
                    "query": query_text,
                    "collection_ids": collection_ids,
                    "top_k": top_k,
                    "filters": filters,
                    "response_format": response_format,
                },
                seen_chunk_ids=tuple(seen),
                index_generations_seen=tuple(g.root for g in pack.diagnostics.index_generations_seen),
            )
            next_cursor = await deps.cursor_store.issue(record)
            truncated = next_cursor is not None

        structured = _build_structured(pack, slim_items, truncated=truncated, next_cursor=next_cursor)
        guidance = (
            _GUIDANCE_CURSOR_ISSUE_FAILED
            if needs_more and next_cursor is None and not exclusion_limit_hit
            else (
                _GUIDANCE_EXCLUSION_LIMIT
                if exclusion_limit_hit
                else _guidance_search_page(len(slim_items), truncated=truncated, next_cursor=next_cursor)
            )
        )
        sufficiency_status = pack.sufficiency.status.value
        if sufficiency_status in ("insufficient", "unknown"):
            missing = [m.root for m in pack.sufficiency.missing_aspects]
            guidance = f"{guidance}\n{_guidance_insufficiency(sufficiency_status, missing)}"
        new_generations = tuple(g.root for g in pack.diagnostics.index_generations_seen)
        if (
            stored_record is not None
            and stored_record.index_generations_seen
            and (set(stored_record.index_generations_seen) != set(new_generations))
        ):
            guidance = f"{guidance}\n{_GUIDANCE_INDEX_REFRESHED}"
        full_text = f"{text}\n\n{guidance}"
        return ToolResult(is_error=False, structured_content=structured, text=full_text)
    except ToolError as exc:
        return _error_result(exc)


# ---------------------------------------------------------------------------------------------
# `get_document`
# ---------------------------------------------------------------------------------------------


def _render_block(block: DocBlockView) -> str:
    prefix = ""
    if block.text_source == "ocr":
        prefix = "[ocr] "
    elif block.text_source == "vlm":
        prefix = "[vlm] "
    elif block.text_source == "converted":
        prefix = "[converted] "
    if block.type == "heading":
        level = block.level or 1
        label = f"{block.numbering_label} " if block.numbering_label else ""
        return f"{'#' * min(level, 6)} {label}{prefix}{block.text}"
    if block.type == "figure":
        return f"[figure: {block.text}]"
    if block.type == "footnote":
        return f"[^{block.text}]" if not prefix else f"{prefix}[^{block.text}]"
    if block.type == "code":
        return f"```\n{block.text}\n```"
    if block.type == "page_break":
        comment = f" <!-- page {block.page} -->" if block.page is not None else ""
        return f"---{comment}"
    return f"{prefix}{block.text}"


def _render_chunk(chunk: DocChunkView) -> str:
    prefix = "[ocr] " if chunk.text_source == "ocr" else "[vlm] " if chunk.text_source == "vlm" else ""
    return f"{prefix}{chunk.text}"


async def get_document(args: dict[str, Any], security: SecurityContext, deps: ToolDeps) -> ToolResult:
    """05 §4.3 `get_document` 핸들러."""
    try:
        parsed = GetDocumentArgs.model_validate(args)
    except ValidationError as exc:
        return _error_result(_validation_error("/", exc))

    try:
        block_offset = 0
        document_id = parsed.document_id
        view = parsed.view
        prior_offset = 0
        if parsed.cursor is not None:
            record = await deps.cursor_store.redeem(
                tenant_id=security.tenant_id.root,
                cursor_id=parsed.cursor,
                tool="get_document",
                principals=[p.root for p in security.principals],
                collection_ids=[c.root for c in security.collection_ids],
                classification_max=security.classification_max.value,
                visible_set=[v.value for v in security.visible_set],
            )
            if record is None or record.document_id is None or record.view is None:
                return _error_result(_cursor_error("/cursor"))
            document_id = record.document_id
            view = record.view  # type: ignore[assignment]
            block_offset = record.block_offset or 0
            prior_offset = record.offset

        content = await deps.document_reader(document_id, view, security)
        if content is None:
            return _error_result(_document_not_found_error())

        items: Sequence[DocBlockView] | Sequence[DocChunkView]
        render_one = _render_block if view != "chunks" else _render_chunk
        items = content.chunks if view == "chunks" else content.blocks

        source_line = f"출처: {content.source_uri} · 버전: {content.doc_version[:12]} · 언어: {content.language}"
        header_line = f"# {content.title}\n{source_line}"
        rendered: list[str] = []
        included = 0
        for candidate in items[block_offset:]:
            fragment = render_one(candidate)  # type: ignore[arg-type]
            trial = "\n\n".join([header_line, *rendered, fragment])
            if rendered and _approx_tokens(trial) > deps.max_result_tokens:
                break
            rendered.append(fragment)
            included += 1
        last_index = block_offset + included
        truncated = last_index < len(items)

        next_cursor: str | None = None
        if truncated:
            issue_hash = security_context_hash(
                tenant_id=security.tenant_id.root,
                principals=[p.root for p in security.principals],
                collection_ids=[c.root for c in security.collection_ids],
                as_of=security.as_of.root,
                classification_max=security.classification_max.value,
                visible_set=[v.value for v in security.visible_set],
            )
            expires_at = (
                (datetime.now(UTC) + timedelta(seconds=deps.cursor_store.ttl_s)).isoformat().replace("+00:00", "Z")
            )
            record = CursorRecord(
                tenant_id=security.tenant_id.root,
                tool="get_document",
                offset=prior_offset + 1,
                security_context_hash=issue_hash,
                as_of=security.as_of.root,
                issued_at=_now_iso(),
                expires_at=expires_at,
                document_id=document_id,
                view=view,
                block_offset=last_index,
            )
            next_cursor = await deps.cursor_store.issue(record)
            truncated = next_cursor is not None

        structured: dict[str, Any] = {
            "document_id": content.document_id,
            "collection_id": content.collection_id,
            "doc_version": content.doc_version,
            "view": view,
            "title": content.title,
            "source_uri": content.source_uri,
            "language": content.language,
            "doc_date": content.doc_date,
            "quality": content.quality,
            "truncated": truncated,
            "next_cursor": next_cursor,
        }
        if view == "chunks":
            structured["chunks"] = [
                {
                    "chunk_id": c.chunk_id,
                    "item_kind": c.item_kind,
                    "level": c.level,
                    "parent_chunk_id": c.parent_chunk_id,
                    "ordinal": c.ordinal,
                    "heading_path": list(c.heading_path),
                    "text": c.text,
                    "text_source": c.text_source,
                }
                for c in content.chunks[block_offset:last_index]
            ]
        else:
            structured["blocks"] = [
                {
                    "block_id": b.block_id,
                    "type": b.type,
                    "level": b.level,
                    "numbering_label": b.numbering_label,
                    "heading_path": list(b.heading_path),
                    "text": b.text,
                    "text_source": b.text_source,
                    "page": b.page,
                    "element_path": b.element_path,
                }
                for b in content.blocks[block_offset:last_index]
            ]

        text = "\n\n".join([header_line, *rendered])
        guidance = _guidance_get_document_page(
            block_offset + 1, last_index, truncated=truncated, next_cursor=next_cursor
        )
        return ToolResult(is_error=False, structured_content=structured, text=f"{text}\n\n{guidance}")
    except ToolError as exc:
        return _error_result(exc)


# ---------------------------------------------------------------------------------------------
# `list_collections`
# ---------------------------------------------------------------------------------------------


async def list_collections(args: dict[str, Any], security: SecurityContext, deps: ToolDeps) -> ToolResult:
    """05 §4.4 `list_collections` 핸들러."""
    try:
        ListCollectionsArgs.model_validate(args)
    except ValidationError as exc:
        return _error_result(_validation_error("/", exc))

    specs = await deps.collection_lister(security)
    specs = sorted(specs, key=lambda s: s.name)[:1000]
    collections: list[dict[str, Any]] = [
        {
            "collection_id": spec.collection_id.root,
            "name": spec.name,
            "profile_id": spec.profile_id.root,
            "document_count": spec.stats.document_count,
            "filterable_fields": [f.root for f in spec.filterable_fields],
            "updated_at": spec.updated_at.root,
        }
        for spec in specs
    ]
    if not collections:
        text = "접근 가능한 컬렉션이 없습니다. / No accessible collections."
    else:
        lines = [
            "- {name} ({collection_id}) — 문서 {count}건, 프로파일 {profile}, 필터: {fields}".format(
                name=c["name"],
                collection_id=c["collection_id"],
                count=c["document_count"],
                profile=c["profile_id"],
                fields=", ".join(c["filterable_fields"]) or "없음",
            )
            for c in collections
        ]
        text = "\n".join(lines)
    return ToolResult(is_error=False, structured_content={"collections": collections}, text=text)
