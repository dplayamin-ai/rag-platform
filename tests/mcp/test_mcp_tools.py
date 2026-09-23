"""MCP 도구 3종 핸들러 단위 테스트 — SDK 서버 기동 없이 `tools.py`를 직접 호출한다.

역할: 페이크 `QueryRunner`/`DocumentReader`/`CollectionLister`와 `testing.doubles.InMemoryKV` 위의
`CursorStore`를 `ToolDeps`에 주입해 `search`/`get_document`/`list_collections` 핸들러를 직접
호출·검증한다(05-api/05 §4~§9, ADR-0025). SDK(`mcp` 패키지)·`server.py`는 관여하지 않는다.
설계 근거: `docs/13-implementation/wp/WP-502-mcp-server.md` §7(테스트 목록), `docs/05-api/05-mcp-
server.md` §4(도구 정의)·§5(결과 렌더·20k 토큰 상한)·§6(커서)·§8(오류 표현).
구성: `_make_item`/`_make_pack`/`_make_collection_spec`/`_make_security` — 계약 객체 픽스처
빌더(계약 필드는 `contracts.common_types`·`contracts.context_pack`·`contracts.collection_spec`의
정본 철자 그대로); `_PoolQueryRunner` — `exclude_ids`를 실제로 걸러내는 페이크 질의 실행기(커서
왕복 검증용); 이후 `search`/`get_document`/`list_collections` 각각의 테스트 클래스.
불변식·주의: 이 파일은 `tests/`이므로 `rag_platform.testing.doubles`를 임포트할 수 있다(운영
진입점이 아님 — import-linter `testing-not-in-production`은 `mcp/`·`api/`·`orchestration/`에만
적용). 픽스처의 ULID·Hex64 값은 실제 패턴을 만족해야 하므로 `ulid.ULID()`·`sdk.hashing.hash_of`로
생성한다(하드코딩 금지 — 계약 검증을 우회하지 않는다).
검증 계층: 1층(여기서 검증) — 페이크 의존성만, 외부 자원 없음. `# DEFERRED: 실 QueryRunner/
DocumentReader/CollectionLister 배선 위의 e2e는 이후 WP 몫(WP-502 §9)`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from ulid import ULID

from rag_platform.contracts.collection_spec import (
    CollectionBackend,
    CollectionPolicies,
    CollectionSpec,
    CollectionStats,
    LicensePolicy,
)
from rag_platform.contracts.collection_spec.CollectionSpec import backends as backends_1
from rag_platform.contracts.common_types import (
    Acl2,
    ContextItem,
    Header,
    Producer,
    Provenance,
    SecurityContext,
    SecurityFilter,
    Segment,
    StrategyFilter,
)
from rag_platform.contracts.context_pack import (
    AclRecheckReport,
    Budget,
    ContextPack,
    Diagnostics,
    FiltersApplied,
    LatencyMs,
    Ordering,
    PackStep,
    PackStep2,
    PackStep3,
    PackStep4,
    RedactionSummary,
    RenderHints,
    Sufficiency,
    TokenizerSpec,
)
from rag_platform.mcp.cursor_store import CursorStore
from rag_platform.mcp.tools import (
    DocBlockView,
    DocChunkView,
    DocumentContent,
    ToolDeps,
    get_document,
    list_collections,
    search,
)
from rag_platform.sdk.hashing import hash_of
from rag_platform.testing.doubles.in_memory_kv import InMemoryKV

if TYPE_CHECKING:
    from collections.abc import Sequence

_NOW = "2026-01-01T00:00:00.000Z"


def _ulid() -> str:
    return str(ULID())


def _hex64(*parts: str) -> str:
    return hash_of("test", *parts)


def _make_item(i: int, *, collection_id: str, document_id: str, text: str | None = None, level: int = 0) -> ContextItem:
    """05-api/05 §4.2 슬림 팩이 그대로 투영하는 `ContextItem`(§9.3 헤더 등가) 픽스처 1건."""
    text = text or (f"본문 내용 {i} 정보공개 청구 접수 절차. " * 3)
    return ContextItem(
        cite_id=f"d{i + 1}",
        rank=i + 1,
        position=i,
        record_id=None,
        chunk_id=_hex64("chunk", document_id, str(i)),
        collection_id=collection_id,
        document_id=document_id,
        doc_version=_hex64("docver", document_id),
        parent_chunk_id=None,
        item_kind="text",
        level=level,
        confidence_tier="high",
        header=Header(
            title="정보공개 업무 처리 지침",
            section_path=["제3장 청구 접수", "제12조 접수 절차"],
            numbering_path=["3", "12"],
            source_uri=f"file:///{document_id}.txt",
            lang="ko",
            doc_date="2026-01-01",
        ),
        text=text,
        text_format="plain",
        text_source="text_layer",
        ocr_confidence_min=None,
        segments=[
            Segment(
                index=0,
                text=text,
                char_start=0,
                char_end=len(text),
                block_id=_hex64("block", document_id, str(i))[:32],
            )
        ],
        context_prefix=None,
        tables=None,
        figures=None,
        parent=None,
        duplicates_of=None,
        conflicts_with=None,
        provenance=[Provenance(element_path=f"/p[{i}]", char_start=0, char_end=len(text), page=None, bbox=None)],
        acl=Acl2(classification="internal", checked=True, checked_at=_NOW, source="payload"),
        scores=None,
        token_count=max(len(text) // 4, 1),
    )


def _make_pack(
    items: Sequence[ContextItem],
    *,
    tenant_id: str,
    collection_ids: Sequence[str],
    sufficiency_status: str = "sufficient",
    missing_aspects: Sequence[str] = (),
    index_generations_seen: Sequence[int] = (7,),
    ordering_strategy: str = "relevance_desc",
) -> ContextPack:
    """05-api/05 §4.2 슬림 팩이 투영하는 필드(`schema_version`·`pack_id`·`sufficiency`)를 채운

    최소·유효 `ContextPack` 픽스처. 봉투·렌더 힌트 등 슬림 팩에 나가지 않는 필드도 계약이 요구하는
    만큼만 채운다(전부 필수 — 계약 손편집 없이 그대로 구성).
    """
    return ContextPack(
        schema_version="1.0.0",
        schema_type="ContextPack",
        tenant_id=tenant_id,
        collection_ids=list(collection_ids),
        producer=Producer(
            plugin_id="packer.standard", plugin_version="1.0.0", config_hash=_hex64("cfg"), image_digest=None
        ),
        warnings=[],
        degraded=[],
        created_at=_NOW,
        pack_id=_ulid(),
        query_id=_ulid(),
        plan_id=_ulid(),
        profile_id="standard",
        profile_hash=_hex64("profile"),
        trace_id=_hex64("trace")[:32],
        budget=Budget(
            tokenizer=TokenizerSpec(provider="anthropic", model="claude-test", name="anthropic:claude-test"),
            count_method="approximate",
            calibration_ratio=None,
            safety_margin=0.1,
            max_context_tokens=24000,
            used_tokens=100,
            reserved_answer_tokens=1000,
            k_max=20,
            overflow_policy=["downgrade_tables", "truncate"],
        ),
        ordering=Ordering(strategy=ordering_strategy, applied=True),
        items=list(items),
        omitted=[],
        sufficiency=Sufficiency(
            status=sufficiency_status,
            coverage=0.8,
            confidence="high",
            missing_aspects=list(missing_aspects),
            method="rule",
        ),
        stop_signal=None,
        compression=None,
        redaction_summary=RedactionSummary(pii_policy="keep", entity_counts={}),
        classification_max="internal",
        render_hints=RenderHints(
            preferred_renderer="mcp_tool_result",
            citation_style="bracket_id",
            instructions_template_id="rag-answer-ko@1",
            stable_prefix_ref=None,
            table_format_preference=["markdown"],
            language="ko",
            expose_confidence=False,
            data_marking="none",
        ),
        explain=None,
        diagnostics=Diagnostics(
            dedup_removed=0,
            parent_expansions=0,
            mmr_lambda=None,
            filters_applied=FiltersApplied(
                security=SecurityFilter(
                    tenant_id=tenant_id,
                    collection_ids=list(collection_ids),
                    principals=["user:test"],
                    visible_set=["tenant"],
                    as_of=_NOW,
                    is_current=True,
                    classification_max="internal",
                ),
                strategy=StrategyFilter(level_in=[0], item_kinds=["text"]),
                user=None,
                self_query=None,
                effective_hash=_hex64("filters"),
            ),
            relaxed_applied_keys=None,
            latency_ms=LatencyMs(plan=1, retrieve=1, fuse=1, hydrate=1, rerank=0, postprocess=1, pack=1),
            index_generations_seen=list(index_generations_seen),
            count_method_fallback=False,
            pack_steps=(
                PackStep(step="acl_recheck", removed=0, took_ms=1),
                PackStep2(step="budget_cut", removed=0, took_ms=1),
                PackStep3(step="reorder", removed=0, took_ms=1),
                PackStep4(step="citation_align", removed=0, took_ms=1),
            ),
            acl_recheck=AclRecheckReport(checked=len(items), denied=0, hint_hits=0),
        ),
        truncated=None,
        next_cursor=None,
        content_hash=_hex64("content"),
    )


def _make_collection_spec(name: str, *, collection_id: str | None = None) -> CollectionSpec:
    collection_id = collection_id or _ulid()
    return CollectionSpec(
        schema_version="1.0.0",
        schema_type="CollectionSpec",
        collection_id=collection_id,
        tenant_id=_ulid(),
        name=name,
        profile_id="standard",
        profile_hash=_hex64("profile", name),
        embedding_space_ids={"dense": _hex64("dense"), "sparse_learned": _hex64("sparse")},
        embedding_profile_hash=_hex64("spaces"),
        analyzer_id="mecab-ko:1.3.7:ko-dic-2.1.1",
        dictionary_hash=_hex64("dict"),
        dictionary_ref="file:///dict.tsv",
        tenant_isolation_tier="payload_filter",
        backends=[
            CollectionBackend(
                backend_id="index_backend.qdrant",
                role=backends_1.Role.vector,
                physical_name="rag_vec_abc123",
                alias=f"col_{collection_id}_vec",
            )
        ],
        policies=CollectionPolicies(
            pii_policy="keep",
            pii_tokenize_mode="hash",
            llm_enrichment_allowed=False,
            allow_distribution_documents=False,
            enrichment_budget_tokens=0,
            corpus_multiplier_max=1.0,
        ),
        filterable_fields=["custom.department"],
        license_policy=LicensePolicy(max_grade="A", territory=["KR"]),
        calibration_ref=None,
        stats=CollectionStats(
            document_count=3, leaf_count=10, parent_count=2, bytes_dense=100, bytes_sparse=0, bytes_lexical=0
        ),
        created_at=_NOW,
        updated_at=_NOW,
    )


def _make_security(
    *,
    tenant_id: str,
    collection_ids: Sequence[str],
    principals: Sequence[str] = ("user:test",),
    classification_max: str = "internal",
    visible_set: Sequence[str] = ("tenant",),
    as_of: str = _NOW,
) -> SecurityContext:
    return SecurityContext(
        tenant_id=tenant_id,
        principals=list(principals),
        collection_ids=list(collection_ids),
        as_of=as_of,
        classification_max=classification_max,
        policy_version="1",
        auth_method="oidc",
        visible_set=list(visible_set),
    )


class _PoolQueryRunner:
    """`exclude_ids`를 실제로 제외하는 페이크 `QueryRunner` — 커서 페이지네이션 왕복 검증용.

    반환 시 남은 항목을 `rank`/`position`/`cite_id`가 `d1..dM` 연속이 되도록 재부여한다(05 §6.1
    "cite_id는 페이지마다 새로 부여" 그대로 재현).
    """

    def __init__(self, pool: Sequence[ContextItem], *, tenant_id: str) -> None:
        self.pool = list(pool)
        self.tenant_id = tenant_id
        self.calls: list[Any] = []

    async def __call__(self, request: Any, security: SecurityContext) -> ContextPack:
        self.calls.append(request)
        excluded = {chunk_id.root for chunk_id in (request.exclude_ids or [])}
        remaining = [item for item in self.pool if item.chunk_id.root not in excluded]
        rebuilt = []
        for idx, item in enumerate(remaining):
            data = item.model_dump(mode="json")
            data.update({"cite_id": f"d{idx + 1}", "rank": idx + 1, "position": idx})
            rebuilt.append(ContextItem.model_validate(data))
        return _make_pack(
            rebuilt,
            tenant_id=self.tenant_id,
            collection_ids=[c.root for c in request.collection_ids],
        )


def _deps(
    *,
    pool: Sequence[ContextItem],
    tenant_id: str,
    kv: InMemoryKV | None = None,
    max_result_tokens: int = 20_000,
    document_reader: Any = None,
    collection_lister: Any = None,
) -> tuple[ToolDeps, _PoolQueryRunner]:
    runner = _PoolQueryRunner(pool, tenant_id=tenant_id)

    async def _default_document_reader(document_id: str, view: str, security: SecurityContext) -> None:
        return None

    async def _default_collection_lister(security: SecurityContext) -> list[CollectionSpec]:
        return []

    deps = ToolDeps(
        query_runner=runner,
        document_reader=document_reader or _default_document_reader,
        collection_lister=collection_lister or _default_collection_lister,
        cursor_store=CursorStore(kv or InMemoryKV()),
        max_result_tokens=max_result_tokens,
    )
    return deps, runner


# ---------------------------------------------------------------------------------------------
# `search`
# ---------------------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_search_basic_returns_slim_pack_and_xml_text() -> None:
    tenant = _ulid()
    coll = _ulid()
    doc = _ulid()
    pool = [_make_item(i, collection_id=coll, document_id=doc) for i in range(2)]
    deps, _runner = _deps(pool=pool, tenant_id=tenant)
    security = _make_security(tenant_id=tenant, collection_ids=[coll])

    result = await search({"query": "정보공개 청구 접수 절차"}, security, deps)

    assert result.is_error is False
    assert result.structured_content["truncated"] is False
    assert result.structured_content["next_cursor"] is None
    assert len(result.structured_content["items"]) == 2
    item = result.structured_content["items"][0]
    assert item["cite_id"] == "d1"
    assert "text_preview" in item
    assert "text" not in item
    assert "<documents>" in result.text
    assert "결과 2건 표시(전체)" in result.text
    # 05 §5 공통 규칙 1: 내부 식별자 부재
    assert "tenant_id" not in item
    assert "acl" not in item
    assert "record_id" not in item


@pytest.mark.asyncio
async def test_search_collection_ids_omitted_defaults_to_security_context() -> None:
    tenant = _ulid()
    coll = _ulid()
    doc = _ulid()
    pool = [_make_item(0, collection_id=coll, document_id=doc)]
    deps, runner = _deps(pool=pool, tenant_id=tenant)
    security = _make_security(tenant_id=tenant, collection_ids=[coll])

    result = await search({"query": "q"}, security, deps)

    assert result.is_error is False
    assert [c.root for c in runner.calls[0].collection_ids] == [coll]


@pytest.mark.asyncio
async def test_search_collection_ids_forbidden_intersection_empty() -> None:
    tenant = _ulid()
    allowed_coll = _ulid()
    requested_coll = _ulid()
    doc = _ulid()
    pool = [_make_item(0, collection_id=allowed_coll, document_id=doc)]
    deps, _runner = _deps(pool=pool, tenant_id=tenant)
    security = _make_security(tenant_id=tenant, collection_ids=[allowed_coll])

    result = await search({"query": "q", "collection_ids": [requested_coll]}, security, deps)

    assert result.is_error is True
    assert result.structured_content["code"] == "plan.collection_forbidden"
    assert "list_collections" in result.text


@pytest.mark.asyncio
async def test_search_more_than_20_accessible_without_collection_ids() -> None:
    tenant = _ulid()
    many_collections = [_ulid() for _ in range(21)]
    pool: list[ContextItem] = []
    deps, _runner = _deps(pool=pool, tenant_id=tenant)
    security = _make_security(tenant_id=tenant, collection_ids=many_collections)

    result = await search({"query": "q"}, security, deps)

    assert result.is_error is True
    assert result.structured_content["code"] == "contract.violation"
    assert result.structured_content["detail"].startswith("/collection_ids")


@pytest.mark.asyncio
async def test_search_filter_field_forbidden() -> None:
    tenant = _ulid()
    coll = _ulid()
    doc = _ulid()
    pool = [_make_item(0, collection_id=coll, document_id=doc)]
    deps, _runner = _deps(pool=pool, tenant_id=tenant)
    security = _make_security(tenant_id=tenant, collection_ids=[coll])

    result = await search({"query": "q", "filters": {"field": "tenant_id", "op": "eq", "value": "x"}}, security, deps)

    assert result.is_error is True
    assert result.structured_content["code"] == "plan.filter_field_forbidden"


@pytest.mark.asyncio
async def test_search_top_k_pagination_issues_cursor_and_seen_chunk_ids_accumulate() -> None:
    tenant = _ulid()
    coll = _ulid()
    doc = _ulid()
    pool = [_make_item(i, collection_id=coll, document_id=doc) for i in range(12)]
    deps, _runner = _deps(pool=pool, tenant_id=tenant)
    security = _make_security(tenant_id=tenant, collection_ids=[coll])

    result = await search({"query": "q", "top_k": 5}, security, deps)

    assert len(result.structured_content["items"]) == 5
    assert result.structured_content["truncated"] is True
    assert result.structured_content["next_cursor"] is not None
    assert "더 있음" in result.text


@pytest.mark.asyncio
async def test_search_cursor_redeem_reruns_with_exclude_ids() -> None:
    tenant = _ulid()
    coll = _ulid()
    doc = _ulid()
    pool = [_make_item(i, collection_id=coll, document_id=doc) for i in range(12)]
    deps, runner = _deps(pool=pool, tenant_id=tenant)
    security = _make_security(tenant_id=tenant, collection_ids=[coll])

    page1 = await search({"query": "q", "top_k": 5}, security, deps)
    page1_chunk_ids = {item["chunk_id"] for item in page1.structured_content["items"]}
    cursor = page1.structured_content["next_cursor"]

    page2 = await search({"query": "q", "top_k": 5, "cursor": cursor}, security, deps)
    page2_chunk_ids = {item["chunk_id"] for item in page2.structured_content["items"]}

    assert page2.is_error is False
    assert page1_chunk_ids.isdisjoint(page2_chunk_ids)
    # 두 번째 호출은 저장된 query_request(top_k=5)를 그대로 써서 exclude_ids=5개를 넘긴다
    assert len(runner.calls[1].exclude_ids) == 5
    assert page2.structured_content["items"][0]["cite_id"] == "d1"


@pytest.mark.asyncio
async def test_search_cursor_wrong_tenant_rejected() -> None:
    tenant = _ulid()
    other_tenant = _ulid()
    coll = _ulid()
    doc = _ulid()
    pool = [_make_item(i, collection_id=coll, document_id=doc) for i in range(12)]
    kv = InMemoryKV()
    deps, _runner = _deps(pool=pool, tenant_id=tenant, kv=kv)
    security = _make_security(tenant_id=tenant, collection_ids=[coll])

    page1 = await search({"query": "q", "top_k": 5}, security, deps)
    cursor = page1.structured_content["next_cursor"]

    other_deps, _ = _deps(pool=pool, tenant_id=other_tenant, kv=kv)
    other_security = _make_security(tenant_id=other_tenant, collection_ids=[coll])
    result = await search({"query": "q", "top_k": 5, "cursor": cursor}, other_security, other_deps)

    assert result.is_error is True
    assert result.structured_content["code"] == "contract.violation"
    assert result.structured_content["detail"].startswith("/cursor")


@pytest.mark.asyncio
async def test_search_cursor_wrong_tool_rejected() -> None:
    tenant = _ulid()
    coll = _ulid()
    doc = _ulid()
    content = DocumentContent(
        document_id=doc,
        collection_id=coll,
        doc_version="a" * 64,
        title="문서",
        source_uri="file:///doc.txt",
        language="ko",
        doc_date=None,
        quality="full",
        blocks=_blocks(3, text_len=200),
    )

    async def document_reader(document_id: str, view: str, security: SecurityContext) -> DocumentContent | None:
        return content if document_id == doc else None

    kv = InMemoryKV()
    deps, _runner = _deps(pool=[], tenant_id=tenant, kv=kv, max_result_tokens=60, document_reader=document_reader)
    security = _make_security(tenant_id=tenant, collection_ids=[coll])

    doc_result = await get_document({"document_id": doc}, security, deps)
    doc_cursor = doc_result.structured_content["next_cursor"]
    assert doc_cursor is not None

    result = await search({"query": "q", "cursor": doc_cursor}, security, deps)

    assert result.is_error is True
    assert result.structured_content["code"] == "contract.violation"


@pytest.mark.asyncio
async def test_search_response_format_detailed_uses_full_text() -> None:
    tenant = _ulid()
    coll = _ulid()
    doc = _ulid()
    pool = [_make_item(0, collection_id=coll, document_id=doc, text="상세 원문 전체 텍스트")]
    deps, _runner = _deps(pool=pool, tenant_id=tenant)
    security = _make_security(tenant_id=tenant, collection_ids=[coll])

    result = await search({"query": "q", "response_format": "detailed"}, security, deps)

    item = result.structured_content["items"][0]
    assert item["text"] == "상세 원문 전체 텍스트"
    assert "text_preview" not in item


@pytest.mark.asyncio
async def test_search_result_token_budget_truncates_from_lowest_rank() -> None:
    tenant = _ulid()
    coll = _ulid()
    doc = _ulid()
    pool = [_make_item(i, collection_id=coll, document_id=doc, text="긴 본문 " * 200, level=0) for i in range(5)]
    deps, _runner = _deps(pool=pool, tenant_id=tenant, max_result_tokens=600)
    security = _make_security(tenant_id=tenant, collection_ids=[coll])

    result = await search({"query": "q", "top_k": 5}, security, deps)

    assert 0 < len(result.structured_content["items"]) < 5
    kept_ranks = [item["cite_id"] for item in result.structured_content["items"]]
    assert kept_ranks == [f"d{i + 1}" for i in range(len(kept_ranks))]


def _reposition(item: ContextItem, position: int) -> ContextItem:
    """`item`을 `position`만 바꾼 복제본으로 되돌린다(`rank`·`cite_id`는 그대로, §6.1 불변)."""
    data = item.model_dump(mode="json")
    data["position"] = position
    return ContextItem.model_validate(data)


#: 바이블 §9.2 `litm_alternating` K=5 표: render order(position 0→4) = [r2, r4, r5, r3, r1].
_LITM_POSITION_BY_RANK_K5 = {2: 0, 4: 1, 5: 2, 3: 3, 1: 4}


def _make_litm_pool(*, collection_id: str, document_id: str, text: str | None = None) -> list[ContextItem]:
    """5건을 만들어 바이블 §9.2 K=5 배치로 `position`을 재배열하고, 계약 불변식대로 `ContextPack.
    items`를 `position` 오름차순으로 되돌려준다(렌더 순서 `[r2, r4, r5, r3, r1]`, `rank`와 다르다).
    """
    base = [_make_item(i, collection_id=collection_id, document_id=document_id, text=text) for i in range(5)]
    repositioned = [_reposition(item, _LITM_POSITION_BY_RANK_K5[item.rank]) for item in base]
    return sorted(repositioned, key=lambda it: it.position)


def _fixed_pack_deps(pack: ContextPack, *, max_result_tokens: int = 20_000) -> ToolDeps:
    """`pack`을 그대로 돌려주는 `QueryRunner`(재부여 없이 litm 배치를 보존) 위의 `ToolDeps`."""

    async def _query_runner(request: Any, security: SecurityContext) -> ContextPack:
        return pack

    async def _document_reader(document_id: str, view: str, security: SecurityContext) -> None:
        return None

    async def _collection_lister(security: SecurityContext) -> list[CollectionSpec]:
        return []

    return ToolDeps(
        query_runner=_query_runner,
        document_reader=_document_reader,
        collection_lister=_collection_lister,
        cursor_store=CursorStore(InMemoryKV()),
        max_result_tokens=max_result_tokens,
    )


@pytest.mark.asyncio
async def test_search_top_k_selects_by_rank_not_position() -> None:
    """05 §4.2: `top_k`는 `rank` 기준 페이지 크기다 — `position`으로 자르면 d1이 빠진다(K=5 litm)."""
    tenant = _ulid()
    coll = _ulid()
    doc = _ulid()
    items = _make_litm_pool(collection_id=coll, document_id=doc)
    pack = _make_pack(items, tenant_id=tenant, collection_ids=[coll], ordering_strategy="litm_alternating")
    deps = _fixed_pack_deps(pack)
    security = _make_security(tenant_id=tenant, collection_ids=[coll])

    result = await search({"query": "q", "top_k": 3}, security, deps)

    assert result.is_error is False
    cite_ids = {item["cite_id"] for item in result.structured_content["items"]}
    # position 오름차순 items[:3]로 잘랐다면 {"d2", "d4", "d5"}가 되어 실패했을 버그
    assert cite_ids == {"d1", "d2", "d3"}


@pytest.mark.asyncio
async def test_search_litm_positions_keep_cite_id_contiguous_and_position_order_under_tight_budget() -> None:
    """05 §5.1: 하위 순위부터 제거해 `cite_id` d1..dM 연속 유지, 방출은 `position` 오름차순."""
    tenant = _ulid()
    coll = _ulid()
    doc = _ulid()
    items = _make_litm_pool(collection_id=coll, document_id=doc, text="본문 내용 문장 " * 200)
    pack = _make_pack(items, tenant_id=tenant, collection_ids=[coll], ordering_strategy="litm_alternating")
    deps = _fixed_pack_deps(pack, max_result_tokens=650)
    security = _make_security(tenant_id=tenant, collection_ids=[coll])

    result = await search({"query": "q", "top_k": 5}, security, deps)

    assert result.is_error is False
    returned = result.structured_content["items"]
    assert 0 < len(returned) < 5
    numbers = [int(item["cite_id"][1:]) for item in returned]
    assert sorted(numbers) == list(range(1, len(numbers) + 1))  # d1..dM 연속, 구멍 없음

    position_by_chunk_id = {it.chunk_id.root: it.position for it in items}
    positions = [position_by_chunk_id[item["chunk_id"]] for item in returned]
    assert positions == sorted(positions)  # 방출 순서 = 원래 litm position 오름차순


@pytest.mark.asyncio
async def test_search_valkey_unavailable_falls_back_truncated_false() -> None:
    class _FailingKV(InMemoryKV):
        async def set(self, key: str, value: bytes, *, ttl_s: int) -> None:
            msg = "valkey unavailable"
            raise RuntimeError(msg)

    tenant = _ulid()
    coll = _ulid()
    doc = _ulid()
    pool = [_make_item(i, collection_id=coll, document_id=doc) for i in range(12)]
    deps, _runner = _deps(pool=pool, tenant_id=tenant, kv=_FailingKV())
    security = _make_security(tenant_id=tenant, collection_ids=[coll])

    result = await search({"query": "q", "top_k": 5}, security, deps)

    assert result.structured_content["truncated"] is False
    assert result.structured_content["next_cursor"] is None
    assert "이어받기 핸들을 발급할 수 없습니다" in result.text


# ---------------------------------------------------------------------------------------------
# `get_document`
# ---------------------------------------------------------------------------------------------


def _blocks(count: int, *, text_len: int = 20) -> tuple[DocBlockView, ...]:
    return tuple(
        DocBlockView(
            block_id=f"{i:032d}",
            type="heading" if i == 0 else "paragraph",
            level=1 if i == 0 else None,
            numbering_label=None,
            heading_path=(),
            text=("제목" if i == 0 else f"블록 본문 {'x' * text_len} {i}"),
            text_source="text_layer",
            page=None,
            element_path=f"/p[{i}]",
        )
        for i in range(count)
    )


@pytest.mark.asyncio
async def test_get_document_normalized_view_default() -> None:
    tenant = _ulid()
    coll = _ulid()
    doc = _ulid()
    content = DocumentContent(
        document_id=doc,
        collection_id=coll,
        doc_version="a" * 64,
        title="문서 제목",
        source_uri="file:///doc.txt",
        language="ko",
        doc_date=None,
        quality="full",
        blocks=_blocks(3),
    )

    async def document_reader(document_id: str, view: str, security: SecurityContext) -> DocumentContent | None:
        assert view == "normalized"
        return content if document_id == doc else None

    deps, _runner = _deps(pool=[], tenant_id=tenant, document_reader=document_reader)
    security = _make_security(tenant_id=tenant, collection_ids=[coll])

    result = await get_document({"document_id": doc}, security, deps)

    assert result.is_error is False
    assert result.structured_content["view"] == "normalized"
    assert result.structured_content["truncated"] is False
    assert len(result.structured_content["blocks"]) == 3
    assert result.text.startswith("# 문서 제목")
    assert "문서의 1~3 블록 표시(전체)" in result.text


@pytest.mark.asyncio
async def test_get_document_not_found_is_contract_violation_not_api_not_found() -> None:
    tenant = _ulid()
    coll = _ulid()

    async def document_reader(document_id: str, view: str, security: SecurityContext) -> None:
        return None

    deps, _runner = _deps(pool=[], tenant_id=tenant, document_reader=document_reader)
    security = _make_security(tenant_id=tenant, collection_ids=[coll])

    result = await get_document({"document_id": _ulid()}, security, deps)

    assert result.is_error is True
    assert result.structured_content["code"] == "contract.violation"


@pytest.mark.asyncio
async def test_get_document_chunks_view() -> None:
    tenant = _ulid()
    coll = _ulid()
    doc = _ulid()
    chunks = (
        DocChunkView(
            chunk_id="a" * 64,
            item_kind="text",
            level=0,
            parent_chunk_id=None,
            ordinal=0,
            heading_path=(),
            text="청크 본문",
            text_source="text_layer",
        ),
    )
    content = DocumentContent(
        document_id=doc,
        collection_id=coll,
        doc_version="a" * 64,
        title="문서 제목",
        source_uri="file:///doc.txt",
        language="ko",
        doc_date=None,
        quality="full",
        chunks=chunks,
    )

    async def document_reader(document_id: str, view: str, security: SecurityContext) -> DocumentContent | None:
        return content

    deps, _runner = _deps(pool=[], tenant_id=tenant, document_reader=document_reader)
    security = _make_security(tenant_id=tenant, collection_ids=[coll])

    result = await get_document({"document_id": doc, "view": "chunks"}, security, deps)

    assert result.is_error is False
    assert result.structured_content["view"] == "chunks"
    assert result.structured_content["chunks"][0]["chunk_id"] == "a" * 64
    assert "blocks" not in result.structured_content


@pytest.mark.asyncio
async def test_get_document_cursor_continues_at_block_offset() -> None:
    tenant = _ulid()
    coll = _ulid()
    doc = _ulid()
    content = DocumentContent(
        document_id=doc,
        collection_id=coll,
        doc_version="a" * 64,
        title="긴 문서",
        source_uri="file:///doc.txt",
        language="ko",
        doc_date=None,
        quality="full",
        blocks=_blocks(20, text_len=200),
    )

    async def document_reader(document_id: str, view: str, security: SecurityContext) -> DocumentContent | None:
        return content

    deps, _runner = _deps(pool=[], tenant_id=tenant, document_reader=document_reader, max_result_tokens=300)
    security = _make_security(tenant_id=tenant, collection_ids=[coll])

    page1 = await get_document({"document_id": doc}, security, deps)
    assert page1.structured_content["truncated"] is True
    cursor = page1.structured_content["next_cursor"]
    assert cursor is not None
    page1_ids = [b["block_id"] for b in page1.structured_content["blocks"]]

    page2 = await get_document({"document_id": doc, "cursor": cursor}, security, deps)
    assert page2.is_error is False
    page2_ids = [b["block_id"] for b in page2.structured_content["blocks"]]

    assert set(page1_ids).isdisjoint(page2_ids)


# ---------------------------------------------------------------------------------------------
# `list_collections`
# ---------------------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_collections_projects_allowed_only() -> None:
    tenant = _ulid()
    specs = [_make_collection_spec("나 컬렉션"), _make_collection_spec("가 컬렉션")]

    async def collection_lister(security: SecurityContext) -> list[CollectionSpec]:
        return specs

    deps, _runner = _deps(pool=[], tenant_id=tenant, collection_lister=collection_lister)
    security = _make_security(tenant_id=tenant, collection_ids=[s.collection_id.root for s in specs])

    result = await list_collections({}, security, deps)

    assert result.is_error is False
    names = [c["name"] for c in result.structured_content["collections"]]
    assert names == ["가 컬렉션", "나 컬렉션"]
    assert result.structured_content["collections"][0]["filterable_fields"] == ["custom.department"]
    assert "tenant_id" not in result.structured_content["collections"][0]


@pytest.mark.asyncio
async def test_list_collections_empty() -> None:
    tenant = _ulid()

    async def collection_lister(security: SecurityContext) -> list[CollectionSpec]:
        return []

    deps, _runner = _deps(pool=[], tenant_id=tenant, collection_lister=collection_lister)
    security = _make_security(tenant_id=tenant, collection_ids=[])

    result = await list_collections({}, security, deps)

    assert result.is_error is False
    assert result.structured_content["collections"] == []
    assert "접근 가능한 컬렉션이 없습니다" in result.text
