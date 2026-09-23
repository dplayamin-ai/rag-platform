"""`POST /v1/query`·`POST /v1/render` — `QueryRequest` → `{context_pack, rendered?}`, RFC 9457 오류.

역할: 검색 표면 두 엔드포인트를 구현한다. `POST /v1/query`는 본문을 실 계약 `QueryRequest`로
검증하고 `SecurityContext`를 서버 주입한 뒤 `ContextPack`(+선택 `RenderedContext`)을 돌려준다.
`POST /v1/render`는 `POST /v1/query`가 만든 `pack_id`(인메모리 캐시) 또는 인라인 `context_pack`을
받아 다시 렌더링한다. 실 검색 파이프라인(`plan`~`pack`, F4 `retrieval.*`)이 이 WP 범위에 배선되지
않아(open_issues) 두 엔드포인트 모두 **항상 빈 결과**(`items=[]`, `sufficiency.status=not_needed`)를
반환한다 — `05-api/03-retrieval-api.md` §3.2가 정의한 "`route=no_retrieval`" 모양을 그대로 쓴다.
설계 근거: 바이블 §14(`POST /v1/query` → `{context_pack, rendered?, explain?}`; `POST /v1/render` →
`{pack_id | context_pack, renderer, options} → RenderedContext`)·§10.3 E1·E6(`SecurityContext` 서버
주입, 요청 본문 값은 거부); `05-api/03-retrieval-api.md` §2(주체 도출 규칙)·§3.1(요청 규칙,
서버 발급·보안 필드 거부)·§3.2(`QueryResponse` 봉투)·§3.5(지연 예산 — 이 WP는 예산 계산을 하지 않고
`degraded{hydrate, unavailable}` 한 항목으로 미배선 사실만 남긴다); `pipelines/query.py`의
`resolve_renderer`(§4.3 "renderer 미지정 시 target_model.provider에서 유도" 표)를 그대로 재사용한다.
구성: `_build_empty_context_pack` — 요청·보안 문맥으로 빈 `ContextPack` 조립; `_build_rendered` —
`ContextPack` + `Renderer` → 자리표시자 `RenderedContext`; `_PackCacheEntry` — 팩 캐시 값(`pack` +
`security_context_hash` + `expires_at`, §4.4); `_pack_security_context_hash` — §4.4 결합 해시
(`mcp.cursor_store.security_context_hash`와 같은 공식의 독립 구현, `api`↔`mcp`는 임포트 불가);
`_prune_pack_cache` — 만료·상한 초과 항목 정리; `_lookup_cached_pack` — `pack_id` 조회 시 주체
바인딩 재대조; `router` — `POST /v1/query`·`POST /v1/render`.
불변식·주의: `pipelines.query.run_query`의 6-Protocol(`Planner`~`Packer`) 배선은 하지 않는다 —
그 계약(`QueryPlan`/`CandidateSet`/`RankedSet`)은 이 WP 읽기 예산 밖이고, `pipelines/query.py` 자신의
독스트링도 그 배선을 "F5 또는 F4 배치 검증자의 몫"이라 적어 둔다(open_issues). `explain`은 만들지
않는다(`QueryPlan` 없이는 무의미). 팩 캐시(`pack_id` 조회)는 Valkey가 아니라 `app.state.pack_cache`
프로세스 내 딕셔너리다(Valkey `pack:{tenant}:{pack_id}`로의 이전은 open_issues) — 값은 이제
`{pack, security_context_hash, expires_at}`이고, TTL 10분(§4.4)과 조회 시 재계산 대조(현재
`principals`/`classification_max`/`visible_set`, `allowed ∩ pack.collection_ids`, `as_of`는 팩에
저장된 값으로 고정)를 구현한다 — 불일치·만료는 모두 404 `api.not_found`(존재 비노출). 저장은 매
`POST /v1/query` 호출 전에 만료 항목을 청소하고 상한(`_PACK_CACHE_MAX_ENTRIES`)을 넘으면 가장 오래된
항목부터 지운다(무기한 성장 방지).
검증 계층: 1층(여기서 검증) — `tests/api/test_api.py`.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from ulid import ULID

from rag_platform.api.problems import ApiError
from rag_platform.contracts import common_types as ct
from rag_platform.contracts.context_pack import ContextPack
from rag_platform.contracts.query_request import QueryRequest
from rag_platform.contracts.rendered_context import RenderedContext
from rag_platform.pipelines.query import resolve_renderer
from rag_platform.sdk.hashing import hash_of
from rag_platform.security.security_context import authenticate, derive_security_context, format_datetime, root_value

if TYPE_CHECKING:
    from collections.abc import Sequence

    from rag_platform.contracts.common_types import SecurityContext
    from rag_platform.security.security_context import ApiKeyRecord

__all__ = ["router"]

# 05-api/03 §3.1: these are server-derived; the client body must never carry them.
_SERVER_ASSIGNED_FIELDS: tuple[str, ...] = (
    "query_id",
    "tenant_id",
    "as_of",
    "security_context",
    "principals",
    "visible_set",
    "classification_max",
)
_RENDERER_VALUES = {member.value for member in ct.Renderer}

# Named so `raise ApiError(...)` never passes a bare string literal (ruff EM101).
_CODE_CONTRACT_VIOLATION = "contract.violation"
_CODE_COLLECTION_FORBIDDEN = "plan.collection_forbidden"
_CODE_NOT_FOUND = "api.not_found"

#: 05-api/03 §4.4 `pack_id` 조회 창(초안 10분).
_PACK_CACHE_TTL_S = 600
#: 방어적 메모리 상한 — 만료 청소 후에도 이 개수를 넘으면 가장 오래된 항목부터 지운다.
_PACK_CACHE_MAX_ENTRIES = 10_000


@dataclass(frozen=True)
class _PackCacheEntry:
    """`app.state.pack_cache` 값(05-api/03 §4.4 `{context_pack, security_context_hash}` + TTL)."""

    pack: ContextPack
    security_context_hash: str
    expires_at: datetime


def _new_ulid() -> str:
    """Issue a fresh ULID string (bible §6.1; shell/api is the only layer allowed entropy)."""
    return str(ULID())


def _pack_security_context_hash(
    *,
    tenant_id: str,
    principals: Sequence[str],
    collection_ids: Sequence[str],
    as_of: str,
    classification_max: str,
    visible_set: Sequence[str],
) -> str:
    """05-api/03 §4.4 결합 해시 ``H("sec", tenant_id, sorted(principals), ...)``.

    `mcp.cursor_store.security_context_hash`와 같은 공식이지만 독립 구현이다 — import-linter
    `layers` 계약에서 `rag_platform.api`와 `rag_platform.mcp`는 같은 층(독립)이라 서로 임포트할
    수 없다(바이블 §12; open_issues: 공유 헬퍼는 `security` 패키지 승격이 필요하다).
    """
    return hash_of(
        "sec",
        tenant_id,
        ",".join(sorted(principals)),
        ",".join(sorted(collection_ids)),
        as_of,
        classification_max,
        ",".join(sorted(visible_set)),
    )


def _prune_pack_cache(cache: dict[tuple[str, str], _PackCacheEntry], *, now: datetime) -> None:
    """만료된 항목을 지우고, 그래도 상한을 넘으면 가장 오래된(입력 순) 항목부터 지운다."""
    expired = [key for key, entry in cache.items() if entry.expires_at <= now]
    for key in expired:
        del cache[key]
    while len(cache) > _PACK_CACHE_MAX_ENTRIES:
        oldest_key = next(iter(cache))
        del cache[oldest_key]


def _lookup_cached_pack(request: Request, record: ApiKeyRecord, pack_id: str, *, now: datetime) -> ContextPack:
    """05-api/03 §4.4 조회(주체 바인딩 대조). 엔트리 부재·만료·해시 불일치는 모두 404(존재 비노출).

    현재 자격 증명으로 `SecurityContext`를 다시 도출해 `collection_ids' = allowed ∩
    pack.collection_ids`를 얻고, `as_of`만 팩에 저장된 원 질의 값으로 고정해 해시를 재계산한다
    (원 `as_of`는 팩 자체 — `diagnostics.filters_applied.security.as_of` — 에 있으므로 별도로
    저장하지 않는다).
    """
    cache: dict[tuple[str, str], _PackCacheEntry] = request.app.state.pack_cache
    key = (record.tenant_id, pack_id)
    entry = cache.get(key)
    if entry is None:
        raise ApiError(_CODE_NOT_FOUND, status=404, detail="/pack_id: resource not found")
    if entry.expires_at <= now:
        del cache[key]
        raise ApiError(_CODE_NOT_FOUND, status=404, detail="/pack_id: resource not found")

    pack_collection_ids = [root_value(collection_id) for collection_id in entry.pack.collection_ids]
    current_security = derive_security_context(record, requested_collection_ids=pack_collection_ids, now=now)
    stored_as_of = root_value(entry.pack.diagnostics.filters_applied.security.as_of)
    recomputed_hash = _pack_security_context_hash(
        tenant_id=root_value(current_security.tenant_id),
        principals=[root_value(p) for p in current_security.principals],
        collection_ids=[root_value(c) for c in current_security.collection_ids],
        as_of=stored_as_of,
        classification_max=root_value(current_security.classification_max),
        visible_set=[root_value(v) for v in current_security.visible_set],
    )
    if recomputed_hash != entry.security_context_hash:
        raise ApiError(_CODE_NOT_FOUND, status=404, detail="/pack_id: resource not found")
    return entry.pack


def _reject_server_assigned_fields(body: dict[str, Any]) -> None:
    """05-api/03 §3.1: reject a body that carries any server-derived/security field."""
    for name in _SERVER_ASSIGNED_FIELDS:
        if name in body:
            raise ApiError(_CODE_CONTRACT_VIOLATION, status=400, detail=f"/{name}: server-assigned, must not be sent")


def _build_empty_context_pack(
    query_request: QueryRequest, security: SecurityContext, *, pack_id: str, trace_id: str, now: datetime
) -> ContextPack:
    """Assemble a `route=no_retrieval`-shaped `ContextPack` (05-api/03 §3.2).

    `items=[]` because the real `plan`~`pack` chain is not wired in this WP (open_issues;
    `degraded{hydrate, unavailable}` records the gap on every response instead of hiding it).
    """
    content_hash = hash_of("stub", "context-pack", pack_id)
    renderer = resolve_renderer(query_request)
    collection_ids = [root_value(collection_id) for collection_id in security.collection_ids]
    security_filter = {
        "tenant_id": root_value(security.tenant_id),
        "collection_ids": collection_ids,
        "principals": [root_value(principal) for principal in security.principals],
        "visible_set": [root_value(visibility) for visibility in security.visible_set],
        "as_of": root_value(security.as_of),
        "is_current": True,
        "classification_max": root_value(security.classification_max),
    }
    payload = {
        "schema_version": "1.0.0",
        "schema_type": "ContextPack",
        "tenant_id": root_value(security.tenant_id),
        "collection_ids": collection_ids,
        "producer": {
            "plugin_id": "pack.api_stub_empty",
            "plugin_version": "1.0.0",
            "config_hash": content_hash,
            "image_digest": None,
            "model_ids": None,
        },
        "warnings": [],
        "degraded": [
            {
                "component": "hydrate",
                "reason": "unavailable",
                "detail": "F4 retrieval pipeline wiring deferred (open_issues); no channels queried",
            }
        ],
        "created_at": format_datetime(now),
        "pack_id": pack_id,
        "query_id": root_value(query_request.query_id),
        "plan_id": _new_ulid(),
        "profile_id": "api-stub-v1",
        "profile_hash": content_hash,
        "trace_id": trace_id,
        "budget": {
            "tokenizer": {"provider": "anthropic", "model": "stub", "name": "tiktoken:cl100k_base"},
            "count_method": "approximate",
            "calibration_ratio": None,
            "safety_margin": 0.0,
            "max_context_tokens": query_request.max_context_tokens or 24000,
            "used_tokens": 0,
            "reserved_answer_tokens": 0,
            "k_max": 1,
            "overflow_policy": ["truncate"],
        },
        "ordering": {
            "strategy": root_value(query_request.ordering_strategy)
            if query_request.ordering_strategy
            else "relevance_desc",
            "applied": False,
        },
        "items": [],
        "omitted": [],
        "sufficiency": {
            "status": "not_needed",
            "coverage": 0.0,
            "confidence": "low",
            "missing_aspects": [],
            "method": "rule",
        },
        "stop_signal": None,
        "compression": None,
        "redaction_summary": {"pii_policy": "mask", "entity_counts": {}},
        "classification_max": root_value(security.classification_max),
        "render_hints": {
            "preferred_renderer": root_value(renderer),
            "citation_style": "bracket_id",
            "instructions_template_id": "api-stub-empty@1",
            "stable_prefix_ref": None,
            "table_format_preference": ["markdown"],
            "language": "ko",
            "expose_confidence": False,
            "data_marking": "none",
        },
        "explain": None,
        "diagnostics": {
            "dedup_removed": 0,
            "parent_expansions": 0,
            "mmr_lambda": None,
            "filters_applied": {
                "security": security_filter,
                "strategy": {"level_in": [0], "item_kinds": ["text"]},
                "user": None,
                "self_query": None,
                "effective_hash": content_hash,
            },
            "relaxed_applied_keys": None,
            "latency_ms": {"plan": 0, "retrieve": 0, "fuse": 0, "hydrate": 0, "rerank": 0, "postprocess": 0, "pack": 0},
            "index_generations_seen": [],
            "count_method_fallback": False,
            "pack_steps": [
                {"step": "acl_recheck", "removed": 0, "took_ms": 0},
                {"step": "budget_cut", "removed": 0, "took_ms": 0},
                {"step": "reorder", "removed": 0, "took_ms": 0},
                {"step": "citation_align", "removed": 0, "took_ms": 0},
            ],
            "acl_recheck": {"checked": 0, "denied": 0, "hint_hits": 0},
        },
        "truncated": None,
        "next_cursor": None,
        "content_hash": content_hash,
    }
    return ContextPack.model_validate(payload)


def _build_rendered(
    pack: ContextPack, renderer: ct.Renderer, *, now: datetime, query_text: str | None = None
) -> RenderedContext:
    """Build a placeholder `RenderedContext` for an empty (`items=[]`) `ContextPack`.

    05-api/03 §4.2 `empty_policy=placeholder` default: a single "No results found." block. The
    exact per-renderer `provider_payload` shape (bible §9) is not reproduced here — `provider_payload`
    is a loosely-typed `dict[str, Any]` at the contract level, so this stub fills it with a
    renderer-neutral placeholder instead (open_issues).
    """
    pack_id = root_value(pack.pack_id)
    content_hash = hash_of("stub", "rendered-context", pack_id, root_value(renderer))
    payload = {
        "schema_version": "1.0.0",
        "schema_type": "RenderedContext",
        "pack_id": pack_id,
        "renderer": root_value(renderer),
        "tenant_id": root_value(pack.tenant_id),
        "collection_ids": [root_value(collection_id) for collection_id in pack.collection_ids],
        "provider_payload": {
            "content": [{"type": "text", "text": "No results found."}],
            **({"query_text": query_text} if query_text else {}),
        },
        "stable_prefix": None,
        "volatile_suffix": {},
        "citation_map": [],
        "token_count_rendered": 0,
        "count_method": "approximate",
        "warnings": [],
        "created_at": format_datetime(now),
        "pack_content_hash": root_value(pack.content_hash),
        "options_hash": content_hash,
        "render_key": content_hash,
    }
    return RenderedContext.model_validate(payload)


async def _read_json_object(request: Request) -> dict[str, Any]:
    """Parse the request body as a JSON object, or raise 400 `contract.violation`."""
    try:
        body = await request.json()
    except ValueError as exc:
        raise ApiError(_CODE_CONTRACT_VIOLATION, status=400, detail=f"invalid JSON body: {exc}") from exc
    if not isinstance(body, dict):
        raise ApiError(_CODE_CONTRACT_VIOLATION, status=400, detail="request body must be a JSON object")
    return body


router = APIRouter()


@router.post("/v1/query")
async def post_query(request: Request) -> JSONResponse:
    """`05-api/03-retrieval-api.md` §3: `QueryRequest` → `{context_pack, rendered?}`."""
    record = authenticate(request.app.state.api_keys, request.headers.get("authorization"))
    body = await _read_json_object(request)
    _reject_server_assigned_fields(body)

    candidate = {**body, "query_id": _new_ulid()}
    try:
        query_request = QueryRequest.model_validate(candidate)
    except ValidationError as exc:
        raise ApiError(_CODE_CONTRACT_VIOLATION, status=400, detail=str(exc)) from exc

    now = datetime.now(UTC)
    requested_collection_ids = [root_value(collection_id) for collection_id in query_request.collection_ids]
    security = derive_security_context(record, requested_collection_ids=requested_collection_ids, now=now)
    if not security.collection_ids:
        raise ApiError(_CODE_COLLECTION_FORBIDDEN, status=403, detail="no requested collection is allowed")

    pack_id = _new_ulid()
    trace_id = uuid.uuid4().hex
    pack = _build_empty_context_pack(query_request, security, pack_id=pack_id, trace_id=trace_id, now=now)

    cache: dict[tuple[str, str], _PackCacheEntry] = request.app.state.pack_cache
    _prune_pack_cache(cache, now=now)
    cache_hash = _pack_security_context_hash(
        tenant_id=root_value(security.tenant_id),
        principals=[root_value(p) for p in security.principals],
        collection_ids=[root_value(collection_id) for collection_id in security.collection_ids],
        as_of=root_value(security.as_of),
        classification_max=root_value(security.classification_max),
        visible_set=[root_value(v) for v in security.visible_set],
    )
    cache[(record.tenant_id, pack_id)] = _PackCacheEntry(
        pack=pack, security_context_hash=cache_hash, expires_at=now + timedelta(seconds=_PACK_CACHE_TTL_S)
    )

    response_format = body.get("response_format", "detailed")
    content: dict[str, Any] = {"context_pack": pack.dump_contract()}
    if response_format != "pack_only":
        renderer = resolve_renderer(query_request)
        rendered = _build_rendered(pack, renderer, now=now, query_text=query_request.query)
        content["rendered"] = rendered.dump_contract()
    return JSONResponse(content=content, headers={"Cache-Control": "no-store"})


@router.post("/v1/render")
async def post_render(request: Request) -> JSONResponse:
    """`05-api/03-retrieval-api.md` §4: `{pack_id | context_pack, renderer, options}` → `RenderedContext`."""
    record = authenticate(request.app.state.api_keys, request.headers.get("authorization"))
    body = await _read_json_object(request)

    pack_id = body.get("pack_id")
    inline_pack = body.get("context_pack")
    if (pack_id is None) == (inline_pack is None):
        detail = "exactly one of pack_id or context_pack is required"
        raise ApiError(_CODE_CONTRACT_VIOLATION, status=400, detail=detail)

    renderer_value = body.get("renderer")
    if not isinstance(renderer_value, str) or renderer_value not in _RENDERER_VALUES:
        raise ApiError(_CODE_CONTRACT_VIOLATION, status=400, detail="/renderer: required, one of the 9 catalog values")

    now = datetime.now(UTC)
    if pack_id is not None:
        pack = _lookup_cached_pack(request, record, pack_id, now=now)
    else:
        try:
            pack = ContextPack.model_validate(inline_pack)
        except ValidationError as exc:
            raise ApiError(_CODE_CONTRACT_VIOLATION, status=400, detail=str(exc)) from exc
        if root_value(pack.tenant_id) != record.tenant_id:
            raise ApiError(_CODE_CONTRACT_VIOLATION, status=400, detail="/context_pack/tenant_id: tenant mismatch")

    options_raw = body.get("options")
    options: dict[str, Any] = options_raw if isinstance(options_raw, dict) else {}
    query_text = options.get("query_text") if isinstance(options.get("query_text"), str) else None
    rendered = _build_rendered(pack, ct.Renderer(renderer_value), now=now, query_text=query_text)
    return JSONResponse(content=rendered.dump_contract())
