"""WP-401 규칙 경로 플래너·필터 단위/통합 테스트.

역할: `adapters/query/korean_normalize.py`(정규화·언어 감지·형태소 키워드), `adapters/query/
rule_router.py`(의도 분류·라우팅·전략 채택), `retrieval/filters.py`(필터 3층 결합·`effective_hash`
`as_of` 불변), `retrieval/planner.py`(`plan()` 통합, 04-pipelines/14 §14 예시 질의 유형에 대응)를
검증한다.
설계 근거: `docs/04-pipelines/14-query-understanding.md` §3.2(규칙 라우터 표)·§14(한국어 예시 질의
5개). 픽스처 출처: 예시 문장은 위 절을 참고해 이 테스트가 직접 지었다(고정 골든 벡터 없음).
구성: 정규화·라우터·필터·`plan()` 각각의 단위 테스트 + 예시 질의 5종 통합 테스트.
불변식: 규칙 경로는 외부 모델을 부르지 않는다 — `kiwipiepy` 미설치가 기본 테스트 경로.
검증 계층: 1층(여기서 검증) — 순수 함수·픽스처만, 외부 자원 없음.
"""

from __future__ import annotations

import pytest
from ulid import ULID

from rag_platform.adapters.query import korean_normalize, rule_router
from rag_platform.contracts import common_types as ct
from rag_platform.contracts.query_request import ConversationTurn, QueryRequest, RequestBudget
from rag_platform.retrieval import filters, planner
from rag_platform.sdk.stage import StageError

pytestmark = pytest.mark.filterwarnings("ignore::DeprecationWarning")

_TENANT_ID = str(ULID())
_COLLECTION_ID = str(ULID())
_AS_OF = "2026-09-23T09:00:00.000Z"


def _security_context(
    *, collection_ids: list[str] | None = None, as_of: str = _AS_OF, tenant_id: str = _TENANT_ID
) -> ct.SecurityContext:
    return ct.SecurityContext(
        tenant_id=tenant_id,
        principals=["user:tester@example.go.kr", "tenant:*"],
        collection_ids=collection_ids or [_COLLECTION_ID],
        as_of=as_of,
        classification_max=ct.Classification.internal,
        policy_version="2026-09-01.1",
        auth_method=ct.AuthMethod.oidc,
        visible_set=[ct.Visibility.public, ct.Visibility.tenant],
    )


def _request(
    query: str,
    *,
    collection_ids: list[str] | None = None,
    conversation: list[dict[str, str]] | None = None,
    filters_node: ct.FilterNode | None = None,
    strategy_hint: ct.Strategy | None = None,
    retrieval_variant: ct.RetrievalVariant | None = None,
    max_latency_ms: int | None = None,
) -> QueryRequest:
    budget = None
    if max_latency_ms is not None:
        budget = RequestBudget(max_latency_ms=max_latency_ms, max_tool_calls=None, max_context_tokens=None)
    conversation_turns = None
    if conversation is not None:
        conversation_turns = [ConversationTurn(role=turn["role"], text=turn["text"]) for turn in conversation]
    return QueryRequest(
        schema_version="1.0.0",
        query_id=str(ULID()),
        query=query,
        collection_ids=collection_ids or [_COLLECTION_ID],
        conversation=conversation_turns,
        filters=filters_node,
        strategy_hint=strategy_hint,
        retrieval_variant=retrieval_variant,
        budget=budget,
        requested_at=_AS_OF,
    )


def _leaf(field: ct.FilterableField, op: ct.FilterOp, value: object) -> ct.FilterNode:
    return ct.FilterNode(ct.FilterNode4(field=ct.FilterableField1(field), op=op, value=value))


def _and(*children: ct.FilterNode) -> ct.FilterNode:
    return ct.FilterNode(ct.FilterNode1(**{"and": list(children)}))


def _not(child: ct.FilterNode) -> ct.FilterNode:
    return ct.FilterNode(ct.FilterNode3(**{"not": child}))


# --------------------------------------------------------------------------------------------
# korean_normalize
# --------------------------------------------------------------------------------------------


def test_normalize_query_splits_display_and_lexical_views() -> None:
    result = korean_normalize.normalize_query("정보공개법\u200b  시행령 제10조", use_kiwi=False)  # noqa: RUF001 - NBSP 원문
    assert result.normalized_query == "정보공개법 시행령 제10조"
    assert "\u200b" not in result.lexical_view
    assert "  " not in result.normalized_query


def test_normalize_query_unifies_symbols_in_lexical_view_only() -> None:
    result = korean_normalize.normalize_query("2024∼2025년 예산", use_kiwi=False)  # noqa: RUF001 - TILDE OPERATOR 원문
    assert "∼" in result.normalized_query  # noqa: RUF001
    assert "~" in result.lexical_view
    assert "∼" not in result.lexical_view  # noqa: RUF001


def test_normalize_query_lexical_terms_tag_subset_and_stopwords() -> None:
    result = korean_normalize.normalize_query("공개 여부와 10일 이내 통지 방법", use_kiwi=False)
    tags = {term.tag for term in result.lexical_terms}
    assert tags <= {"NNG", "NNP", "SL", "SN", "USER_DICT"}
    terms = {term.term for term in result.lexical_terms}
    assert "여부" in terms  # 여부는 §6.3에서 명시적으로 불용어가 아니다
    assert "방법" not in terms  # 방법은 질의 전용 불용어


def test_normalize_query_dictionary_hash_is_deterministic() -> None:
    first = korean_normalize.normalize_query("동일 질의", use_kiwi=False)
    second = korean_normalize.normalize_query("동일 질의", use_kiwi=False)
    assert first.dictionary_hash == second.dictionary_hash
    assert first.analyzer_id == "regex-fallback:1:none"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("정보공개법 시행령 제10조", "ko"),
        ("This is an English query", "en"),
    ],
)
def test_detect_lang(text: str, expected: str) -> None:
    assert korean_normalize.detect_lang(text) == expected


# --------------------------------------------------------------------------------------------
# rule_router
# --------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("query", "expected_intent"),
    [
        ("정보공개법 시행령 제10조", "keyword_lookup"),
        ("며칠 이내에 결정해야 하나요?", "natural_question"),
        ("2024년과 2025년 실적을 비교해줘", "compare_aggregate"),
    ],
)
def test_classify_intent(query: str, expected_intent: str) -> None:
    normalized = korean_normalize.normalize_query(query, use_kiwi=False)
    intent = rule_router.classify_intent(normalized.lexical_terms, query, has_conversation=False)
    assert intent == expected_intent


def test_classify_intent_follow_up_requires_conversation() -> None:
    normalized = korean_normalize.normalize_query("그럼 연장은 며칠까지?", use_kiwi=False)
    intent = rule_router.classify_intent(normalized.lexical_terms, "그럼 연장은 며칠까지?", has_conversation=True)
    assert intent == "follow_up"


def test_route_for_intent_maps_keyword_lookup_to_single() -> None:
    route, complexity = rule_router.route_for_intent("keyword_lookup")
    assert route == ct.Route.single
    assert complexity == ct.Complexity.single_step


def test_route_for_intent_maps_chitchat_to_no_retrieval() -> None:
    route, complexity = rule_router.route_for_intent("chitchat")
    assert route == ct.Route.no_retrieval
    assert complexity == ct.Complexity.no_retrieval


def test_route_for_intent_rejects_unknown_label() -> None:
    with pytest.raises(ValueError, match="unknown intent"):
        rule_router.route_for_intent("not_a_real_intent")


def test_adopt_strategy_keeps_hybrid() -> None:
    strategy, degraded = rule_router.adopt_strategy(ct.Strategy.hybrid)
    assert strategy == ct.Strategy.hybrid
    assert degraded == []


def test_adopt_strategy_falls_back_from_graph_local() -> None:
    strategy, degraded = rule_router.adopt_strategy(ct.Strategy.graph_local)
    assert strategy == ct.Strategy.hybrid
    assert len(degraded) == 1
    assert degraded[0].component == ct.DegradedComponent.channel_graph
    assert degraded[0].reason == ct.DegradedReason.capability_unsupported


# --------------------------------------------------------------------------------------------
# filters
# --------------------------------------------------------------------------------------------


def test_validate_user_filter_accepts_whitelisted_field() -> None:
    node = _leaf(ct.FilterableField.doc_type, ct.FilterOp.eq, "regulation")
    validated, relaxable = filters.validate_and_normalize_user_filter(node)
    assert validated is node
    assert relaxable == []  # 긍정 절은 완화 대상이 아니다(§7.3)


def test_validate_user_filter_rejects_forbidden_field() -> None:
    node = _leaf(ct.FilterableField.doc_type, ct.FilterOp.eq, "regulation")
    node.root.field = ct.FilterableField1(ct.FilterableField3("custom.unknown_key"))
    with pytest.raises(StageError) as exc_info:
        filters.validate_and_normalize_user_filter(node)
    assert exc_info.value.code == "plan.filter_field_forbidden"


def test_validate_user_filter_rejects_disallowed_op() -> None:
    node = _leaf(ct.FilterableField.doc_date, ct.FilterOp.contains_any, ["x"])
    with pytest.raises(StageError) as exc_info:
        filters.validate_and_normalize_user_filter(node)
    assert exc_info.value.code == "plan.filter_field_forbidden"


@pytest.mark.parametrize(
    ("field", "op", "value"),
    [
        # tags contains_all 'x' — 배열이어야 하는데 문자열.
        (ct.FilterableField.tags, ct.FilterOp.contains_all, "x"),
        # doc_type in [] — 빈 배열.
        (ct.FilterableField.doc_type, ct.FilterOp.in_, []),
        # doc_type exists 'yes' — bool이어야 하는데 문자열.
        (ct.FilterableField.doc_type, ct.FilterOp.exists, "yes"),
        # department prefix '' — 비지 않은 문자열이어야 하는데 빈 문자열.
        (ct.FilterableField.department, ct.FilterOp.prefix, ""),
        # doc_date gt [1] — 스칼라(숫자·날짜)여야 하는데 배열.
        (ct.FilterableField.doc_date, ct.FilterOp.gt, [1]),
    ],
)
def test_validate_user_filter_rejects_malformed_value_before_retrieve(
    field: ct.FilterableField, op: ct.FilterOp, value: object
) -> None:
    """리뷰 지적: 값 모양 오류는 Qdrant 빌더의 늦은 `contract.violation`이 아니라 plan 단계에서 잡혀야
    한다 — 그렇지 않으면 모든 채널 런이 실패해 클라이언트가 `retrieve.unavailable`(재시도 가능)을
    받는데, 실제로는 자신의 입력 오류다.
    """
    node = _leaf(field, op, value)
    with pytest.raises(StageError) as exc_info:
        filters.validate_and_normalize_user_filter(node)
    assert exc_info.value.code == "plan.filter_field_forbidden"


def test_validate_user_filter_collects_negative_clause_as_relaxable() -> None:
    node = _and(
        _leaf(ct.FilterableField.doc_type, ct.FilterOp.eq, "regulation"),
        _not(_leaf(ct.FilterableField.tags, ct.FilterOp.contains_any, ["초안"])),
    )
    _validated, relaxable = filters.validate_and_normalize_user_filter(node)
    assert [filters._field_str(f) for f in relaxable] == ["tags"]


def test_validate_user_filter_rejects_depth_over_three() -> None:
    leaf = _leaf(ct.FilterableField.doc_type, ct.FilterOp.eq, "regulation")
    too_deep = _and(_and(_and(_and(leaf))))
    with pytest.raises(StageError) as exc_info:
        filters.validate_and_normalize_user_filter(too_deep)
    assert exc_info.value.code == "plan.filter_field_forbidden"


def test_effective_hash_is_invariant_to_as_of() -> None:
    security_a = _security_context(as_of="2026-09-23T09:00:00.000Z")
    security_b = _security_context(as_of="2026-09-23T10:30:00.000Z")
    filters_a = filters.build_plan_filters(
        security=security_a, strategy=ct.Strategy.hybrid, user_filter=None, relaxable_keys=[]
    )
    filters_b = filters.build_plan_filters(
        security=security_b, strategy=ct.Strategy.hybrid, user_filter=None, relaxable_keys=[]
    )
    assert filters_a.effective_hash == filters_b.effective_hash


def test_effective_hash_changes_with_user_filter() -> None:
    security = _security_context()
    node = _leaf(ct.FilterableField.doc_type, ct.FilterOp.eq, "regulation")
    without_user = filters.build_plan_filters(
        security=security, strategy=ct.Strategy.hybrid, user_filter=None, relaxable_keys=[]
    )
    with_user = filters.build_plan_filters(
        security=security, strategy=ct.Strategy.hybrid, user_filter=node, relaxable_keys=[]
    )
    assert without_user.effective_hash != with_user.effective_hash


def test_build_security_filter_defaults_to_all_security_collection_ids() -> None:
    """`collection_ids` 생략 시(옛 호출부·테스트 호환) `security.collection_ids` 전체를 그대로 쓴다."""
    other = str(ULID())
    security = _security_context(collection_ids=[_COLLECTION_ID, other])
    security_filter = filters.build_security_filter(security)
    assert {c.root for c in security_filter.collection_ids} == {_COLLECTION_ID, other}


def test_build_security_filter_narrows_to_explicit_collection_ids() -> None:
    """리뷰 지적: 요청 ∩ 보안 교집합만 `:collection_ids`에 넣어야 요청 스코프가 새지 않는다."""
    other = str(ULID())
    security = _security_context(collection_ids=[_COLLECTION_ID, other])
    security_filter = filters.build_security_filter(security, collection_ids=[security.collection_ids[0]])
    assert [c.root for c in security_filter.collection_ids] == [_COLLECTION_ID]


def test_plan_scopes_security_filter_to_requested_collection_ids() -> None:
    """`SecurityContext`가 컬렉션 A·B 모두 허용해도 요청이 A만 물으면 `filters.security.collection_ids`
    는 A만이어야 한다(리뷰 지적) — 아니면 Qdrant 사전 필터가 B까지 허용해 요청 스코프가 샌다."""
    other = str(ULID())
    security = _security_context(collection_ids=[_COLLECTION_ID, other])
    request = _request("정보공개법 시행령 제10조", collection_ids=[_COLLECTION_ID])
    result = planner.plan(request, security)
    assert [c.root for c in result.filters.security.collection_ids] == [_COLLECTION_ID]
    assert [c.root for c in result.collection_ids] == [_COLLECTION_ID]


# --------------------------------------------------------------------------------------------
# retrieval.planner plan entry point
# --------------------------------------------------------------------------------------------


def test_plan_builds_two_channels_with_rrf_fusion() -> None:
    security = _security_context()
    request = _request("정보공개법 시행령 제10조")
    result = planner.plan(request, security)
    assert result.route == ct.Route.single
    assert result.fusion.method == ct.FusionMethod.rrf
    assert result.fusion.k == 60
    assert {c.channel for c in result.channels} == {ct.Channel.dense, ct.Channel.lexical}
    assert all(c.enabled for c in result.channels)
    assert result.filters.self_query is None
    assert result.budget.llm_calls_allowed is False
    assert result.created_at == security.as_of
    assert result.security_context == security


def test_plan_raises_when_security_missing() -> None:
    request = _request("정보공개법 시행령 제10조")
    with pytest.raises(StageError) as exc_info:
        planner.plan(request, None)
    assert exc_info.value.code == "plan.security_context_missing"


def test_plan_raises_when_collections_disjoint() -> None:
    security = _security_context(collection_ids=[str(ULID())])
    request = _request("정보공개법 시행령 제10조", collection_ids=[str(ULID())])
    with pytest.raises(StageError) as exc_info:
        planner.plan(request, security)
    assert exc_info.value.code == "plan.collection_forbidden"


def test_plan_fast_variant_disables_rerank_and_doubles_hydrate() -> None:
    security = _security_context()
    request = _request("정보공개법 시행령 제10조", retrieval_variant=ct.RetrievalVariant.fast)
    result = planner.plan(request, security)
    assert result.rerank.enabled is False
    assert result.hydrate.top_n == result.pack.k_max * 2


def test_plan_clamps_latency_budget_to_request_max() -> None:
    security = _security_context()
    request = _request("정보공개법 시행령 제10조", max_latency_ms=300)
    result = planner.plan(request, security)
    assert result.latency_budget_ms.total == 300


def test_plan_no_retrieval_route_disables_all_channels() -> None:
    security = _security_context()
    request = _request("안녕하세요")
    result = planner.plan(request, security)
    assert result.route == ct.Route.no_retrieval
    assert all(not c.enabled for c in result.channels)
    assert result.fusion.weights == {}
    assert result.rewritten_queries[0].channels == []
    # 09 §7.5: channels[].enabled·fusion.weights만 강제로 끈다 — rerank/hydrate/pack/postprocess는
    # "정상 계산"이라 route=no_retrieval에 좌우되지 않는다(fast 변형만 리랭크를 끈다, §9.2).
    assert result.rerank.enabled is True


def test_plan_strategy_hint_graph_local_falls_back_and_records_degraded() -> None:
    security = _security_context()
    request = _request("정보공개법 시행령 제10조", strategy_hint=ct.Strategy.graph_local)
    result = planner.plan(request, security)
    assert result.strategy == ct.Strategy.hybrid
    assert any(entry.component == ct.DegradedComponent.channel_graph for entry in result.degraded)


def test_plan_rejects_forbidden_user_filter_field() -> None:
    security = _security_context()
    forbidden = _leaf(ct.FilterableField.doc_date, ct.FilterOp.contains_any, ["x"])
    request = _request("정보공개법 시행령 제10조", filters_node=forbidden)
    with pytest.raises(StageError) as exc_info:
        planner.plan(request, security)
    assert exc_info.value.code == "plan.filter_field_forbidden"


def test_plan_is_deterministic_given_explicit_plan_id() -> None:
    security = _security_context()
    request = _request("정보공개법 시행령 제10조")
    plan_id = str(ULID())
    first = planner.plan(request, security, plan_id=plan_id)
    second = planner.plan(request, security, plan_id=plan_id)
    assert first.plan_id.root == second.plan_id.root == plan_id
    assert first.planner_fingerprint == second.planner_fingerprint
    assert first.filters.effective_hash == second.filters.effective_hash
