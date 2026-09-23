"""필터 3층 결합 빌더 — `security`(서버 주입·불변) ∧ `strategy`(고정값) ∧ `user`(화이트리스트 검증).

역할: `plan` 스테이지가 `QueryPlan.filters`(`PlanFilters`)를 조립할 때 쓰는 순수 함수 모음(04-pipelines
/14 §8 "필터 결합과 불변식", 바이블 §10.2). `self_query`(정규식/LLM 추출)는 이 WP 범위 밖이라 항상
`None`이다.
설계 근거: 04-pipelines/14 §7.3(신뢰도 임계·적용 정책, 특히 `relaxable_keys` 순서)·§8(F-1~F-7 불변식);
계약 `common_types.{SecurityContext, SecurityFilter, StrategyFilter, FilterNode, FilterableField,
FilterOp}`, `query_plan.PlanFilters`. 필드별 허용 연산자 표는 `03-contracts/09-query-request-and-
query-plan.md §4.3`이 정본이다 — `_ALLOWED_OPS`는 F4 배치 검증으로 그 표와 대조·정정했다(WP-401이
남긴 open issue 해소). `_STRATEGY_FILTERS`의 `hybrid`/`iterative` 값도 같은 문서 §5.2와 대조했다.
구성: `canonical_json` — 해시 입력 정규형; `build_security_filter`/`strategy_filter_for` — 보안·전략
층; `validate_and_normalize_user_filter` — 화이트리스트·깊이·절수 검증 + `relaxable_keys` 수집;
`compute_effective_hash`/`build_plan_filters` — F-5 해시와 `PlanFilters` 조립.
불변식·주의: F-1(security는 복사만, 완화 불가 — `build_security_filter`의 `collection_ids`는 요청 ∩
보안 교집합이어야 하며 `security.collection_ids`(허용된 전체 컬렉션) 그대로 두면 요청 스코프가
샌다, 리뷰 지적) · F-4(`relaxable_keys` ⊆ user 리프, 보안·전략 키 불가) · F-5(`effective_hash`는
`as_of`를 `":as_of"`로 치환한 계획 트리 해시) · F-7(`_validate_leaf`는 필드·연산자 화이트리스트뿐
아니라 값 모양도 검사한다 — `in`/`contains_*`는 비지 않은 배열, `exists`는 bool, `prefix`는 비지
않은 문자열, 범위 연산자는 스칼라; 그래야 Qdrant 빌더의 늦은 `contract.violation`이 아니라 여기서
`plan.filter_field_forbidden`으로 막힌다). 위반은 모두 `StageError("plan.filter_field_forbidden",
stage="plan")`로 올린다. 계약 생성물 손편집 금지.
검증 계층: 1층(여기서 검증) — `tests/retrieval/test_planner.py`.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from rag_platform.contracts import common_types as ct
from rag_platform.contracts.query_plan import PlanFilters
from rag_platform.sdk.hashing import hash_of
from rag_platform.sdk.stage import StageError

if TYPE_CHECKING:
    from collections.abc import Sequence

__all__ = [
    "build_plan_filters",
    "build_security_filter",
    "canonical_json",
    "compute_effective_hash",
    "strategy_filter_for",
    "validate_and_normalize_user_filter",
]

#: 필터 트리 불변식(FilterNode4 독스트링) — 깊이 ≤ 3, 절(리프) ≤ 32.
_MAX_DEPTH = 3
_MAX_CLAUSES = 32
#: 완화(relax) 대상으로 치는 연산자(§7.3 "사용자 필터의 부정 절(`not`·`ne`·`not_in`)").
_NEGATING_OPS = frozenset({ct.FilterOp.ne, ct.FilterOp.not_in})
#: F-7 위반(금지 필드·불허 연산자·깊이·절수 초과)이 공유하는 오류 코드(EM101: 리터럴 대신 변수로 raise).
_FORBIDDEN_CODE = "plan.filter_field_forbidden"

#: 필드별 허용 연산자(F4 배치 검증으로 09 §4.3 정본 표와 대조·정정 — 이전 판은 모든 필드에 보수적으로
#: `eq/ne/in/not_in/exists`를 다는 초안이었다). 값이 없는 필드는 항상 거부. §4.3 자체도 "초안"이라
#: 표기하지만(미해결 이슈 18) 이 저장소 안에서는 유일한 정본이다.
_ALLOWED_OPS: dict[ct.FilterableField, frozenset[ct.FilterOp]] = {
    ct.FilterableField.document_id: frozenset(
        {ct.FilterOp.eq, ct.FilterOp.ne, ct.FilterOp.in_, ct.FilterOp.not_in, ct.FilterOp.exists}
    ),
    ct.FilterableField.doc_version: frozenset({ct.FilterOp.eq, ct.FilterOp.ne, ct.FilterOp.in_, ct.FilterOp.not_in}),
    ct.FilterableField.external_id: frozenset(
        {ct.FilterOp.eq, ct.FilterOp.ne, ct.FilterOp.in_, ct.FilterOp.not_in, ct.FilterOp.exists, ct.FilterOp.prefix}
    ),
    ct.FilterableField.doc_date: frozenset(
        {
            ct.FilterOp.eq,
            ct.FilterOp.ne,
            ct.FilterOp.gt,
            ct.FilterOp.gte,
            ct.FilterOp.lt,
            ct.FilterOp.lte,
            ct.FilterOp.exists,
        }
    ),
    ct.FilterableField.doc_type: frozenset(
        {ct.FilterOp.eq, ct.FilterOp.ne, ct.FilterOp.in_, ct.FilterOp.not_in, ct.FilterOp.exists}
    ),
    ct.FilterableField.department: frozenset(
        {ct.FilterOp.eq, ct.FilterOp.ne, ct.FilterOp.in_, ct.FilterOp.not_in, ct.FilterOp.exists, ct.FilterOp.prefix}
    ),
    ct.FilterableField.tags: frozenset({ct.FilterOp.contains_any, ct.FilterOp.contains_all, ct.FilterOp.exists}),
    ct.FilterableField.lang: frozenset({ct.FilterOp.eq, ct.FilterOp.ne, ct.FilterOp.in_, ct.FilterOp.not_in}),
    ct.FilterableField.genre: frozenset({ct.FilterOp.eq, ct.FilterOp.ne, ct.FilterOp.in_, ct.FilterOp.not_in}),
    #: `item_kind`는 전략 필터(§5.2 `item_kinds`)와 AND — 좁히기만 허용(§4.3 비고).
    ct.FilterableField.item_kind: frozenset({ct.FilterOp.eq, ct.FilterOp.in_}),
    ct.FilterableField.heading_path: frozenset(
        {ct.FilterOp.contains_any, ct.FilterOp.contains_all, ct.FilterOp.prefix}
    ),
    ct.FilterableField.entity_ids: frozenset({ct.FilterOp.contains_any, ct.FilterOp.contains_all, ct.FilterOp.exists}),
    #: `page`는 가상 필드(§4.5) — 리프 검증은 여기서 `eq`/`in`만 통과시키고, `retrieve`의 필터
    #: 빌더가 전송 직전에 `page_start`/`page_end` 조합으로 변환한다(변환 자체는 이 WP 범위 밖).
    ct.FilterableField.page: frozenset({ct.FilterOp.eq, ct.FilterOp.in_}),
    ct.FilterableField.page_start: frozenset(
        {ct.FilterOp.eq, ct.FilterOp.gt, ct.FilterOp.gte, ct.FilterOp.lt, ct.FilterOp.lte, ct.FilterOp.exists}
    ),
    ct.FilterableField.page_end: frozenset(
        {ct.FilterOp.eq, ct.FilterOp.gt, ct.FilterOp.gte, ct.FilterOp.lt, ct.FilterOp.lte, ct.FilterOp.exists}
    ),
}

#: §3.4/§8 F-2: `strategy`별 고정 필터(정본 09 §5.2 표, F4 배치 검증으로 대조). 이 WP의 라우터
#: (`adopt_strategy`)는 `hybrid`·`iterative`만 채택하므로 그 외 전략의 실제 값은 정의하지 않는다.
#: `hybrid`/`iterative` 행은 `level_in=[0]`(리프만) + `item_kinds`에서 `parent`/`summary`/
#: `community_report`/`entity`를 뺀다(§5.2 표 — 이전 판은 `[0,1,2]` 전체 + 모든 `ItemKind`였다).
_STRATEGY_FILTERS: dict[ct.Strategy, ct.StrategyFilter] = {
    ct.Strategy.hybrid: ct.StrategyFilter(
        level_in=[ct.ChunkLevel.integer_0],
        item_kinds=[
            ct.ItemKind.text,
            ct.ItemKind.list_group,
            ct.ItemKind.code,
            ct.ItemKind.table,
            ct.ItemKind.table_part,
            ct.ItemKind.figure,
        ],
    ),
    ct.Strategy.iterative: ct.StrategyFilter(
        level_in=[ct.ChunkLevel.integer_0],
        item_kinds=[
            ct.ItemKind.text,
            ct.ItemKind.list_group,
            ct.ItemKind.code,
            ct.ItemKind.table,
            ct.ItemKind.table_part,
            ct.ItemKind.figure,
        ],
    ),
}


def canonical_json(data: Any) -> str:
    """바이블 §6.2 `canonical_json` — 정렬된 키, 공백 없음, `ensure_ascii=False`."""
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def build_security_filter(
    security: ct.SecurityContext, *, collection_ids: Sequence[ct.Ulid] | None = None
) -> ct.SecurityFilter:
    """`security_context`를 그대로 복사한 `SecurityFilter`를 만든다(F-1, §8).

    Args:
        security: 서버 주입 `SecurityContext`.
        collection_ids: 이 요청이 실제로 조회할 컬렉션(요청 ∩ 보안, `planner._selected_collection_ids`).
            생략하면 `security.collection_ids`(주체가 허용된 전체 컬렉션)를 그대로 쓴다 — 호출측이
            반드시 교집합을 넘겨야 `:collection_ids`가 요청 범위로 좁혀진다(리뷰 지적: 그렇지 않으면
            Qdrant 사전 필터가 요청 밖 컬렉션까지 허용해 요청 스코프가 새고, 두 컬렉션 요청은 채널마다
            서로의 후보를 중복 반환해 §8.1 "컬렉션 차원 무중복 기여"를 어긴다).
    """
    return ct.SecurityFilter(
        tenant_id=security.tenant_id,
        collection_ids=list(collection_ids) if collection_ids is not None else security.collection_ids,
        principals=security.principals,
        visible_set=security.visible_set,
        as_of=security.as_of,
        is_current=True,
        classification_max=security.classification_max,
    )


def strategy_filter_for(strategy: ct.Strategy) -> ct.StrategyFilter:
    """`strategy`의 고정 필터를 돌려준다(F-2, §8).

    Raises:
        ValueError: `strategy`가 이 WP가 정의한 값(`hybrid`, `iterative`) 밖일 때 — 이 규칙 경로
            라우터(`rule_router.adopt_strategy`)는 그 외 값을 만들지 않는다.
    """
    strategy_filter = _STRATEGY_FILTERS.get(strategy)
    if strategy_filter is None:
        msg = (
            f"StrategyFilter for {strategy.value!r} is not defined by the rule-path planner (WP-401); "
            "only 'hybrid'/'iterative' are reachable via rule_router.adopt_strategy()."
        )
        raise ValueError(msg)
    return strategy_filter


def _field_str(field: ct.FilterableField1) -> str:
    """`FilterableField1`(`FilterableField | FilterableField3`)에서 원시 문자열 값을 꺼낸다."""
    inner = field.root
    if isinstance(inner, ct.FilterableField):
        return inner.value
    return inner.root


#: §4.3: `in`/`not_in`/`contains_*`는 비어 있지 않은 배열이 필요하다.
_LIST_VALUE_OPS = frozenset(
    {ct.FilterOp.in_, ct.FilterOp.not_in, ct.FilterOp.contains_any, ct.FilterOp.contains_all}
)
#: §4.3: 범위 연산자는 스칼라(숫자 또는 날짜/일시 문자열, `doc_date` 등)가 필요하다.
_RANGE_VALUE_OPS = frozenset({ct.FilterOp.gt, ct.FilterOp.gte, ct.FilterOp.lt, ct.FilterOp.lte})


def _is_range_scalar(value: Any) -> bool:
    """`value`가 범위 연산자에 쓸 수 있는 숫자 또는 비지 않은 날짜/일시 문자열인지(§4.3)."""
    if isinstance(value, bool):
        return False
    if isinstance(value, int | float):
        return True
    return isinstance(value, str) and bool(value)


def _validate_leaf_value(op: ct.FilterOp, value: Any, field_name: str) -> None:
    """리프 값의 모양을 연산자별로 검사한다(§4.3 표).

    Qdrant 빌더가 뒤늦게 던지는 `contract.violation`을 이 plan 단계로 당겨온다(리뷰 지적: 늦게
    걸리면 모든 채널 런이 실패해 `retrieve.unavailable`(재시도 가능)로 잘못 분류된다 — 사실은 사용자
    입력 오류라 `plan.filter_field_forbidden`(비재시도)이 맞다).
    """
    if op in _LIST_VALUE_OPS and (not isinstance(value, list) or not value):
        detail = f"op {op.value!r} on field {field_name!r} needs a non-empty array value, got {value!r}"
        raise StageError(_FORBIDDEN_CODE, stage="plan", detail=detail)
    if op is ct.FilterOp.exists and not isinstance(value, bool):
        detail = f"op 'exists' on field {field_name!r} needs a boolean value, got {value!r}"
        raise StageError(_FORBIDDEN_CODE, stage="plan", detail=detail)
    if op is ct.FilterOp.prefix and (not isinstance(value, str) or not value):
        detail = f"op 'prefix' on field {field_name!r} needs a non-empty string value, got {value!r}"
        raise StageError(_FORBIDDEN_CODE, stage="plan", detail=detail)
    if op in _RANGE_VALUE_OPS and not _is_range_scalar(value):
        detail = f"op {op.value!r} on field {field_name!r} needs a scalar number or date value, got {value!r}"
        raise StageError(_FORBIDDEN_CODE, stage="plan", detail=detail)


def _validate_leaf(leaf: ct.FilterNode4) -> None:
    """리프의 필드 화이트리스트·연산자 허용 여부·값 모양을 검사한다(F-7, §8; §7.3·§4.3 검사 표)."""
    inner = leaf.field.root
    if not isinstance(inner, ct.FilterableField):
        detail = f"custom.* filterable fields require a declared CollectionSpec catalog: {inner.root!r}"
        raise StageError(_FORBIDDEN_CODE, stage="plan", detail=detail)
    allowed_ops = _ALLOWED_OPS.get(inner)
    if not allowed_ops or leaf.op not in allowed_ops:
        detail = f"op {leaf.op.value!r} is not allowed for field {inner.value!r}"
        raise StageError(_FORBIDDEN_CODE, stage="plan", detail=detail)
    _validate_leaf_value(leaf.op, leaf.value, inner.value)


def _walk(
    node: ct.FilterNode,
    *,
    depth: int,
    negated: bool,
    leaf_count: list[int],
    relaxable: list[ct.FilterableField1],
    seen_relaxable: set[str],
) -> None:
    """필터 트리를 재귀 순회해 리프를 검증하고 완화 대상 필드를 수집한다(§7.3, §8 F-4)."""
    if depth > _MAX_DEPTH:
        detail = f"filter tree depth exceeds {_MAX_DEPTH}"
        raise StageError(_FORBIDDEN_CODE, stage="plan", detail=detail)
    inner = node.root
    if isinstance(inner, ct.FilterNode1):
        for child in inner.and_:
            _walk(
                child,
                depth=depth + 1,
                negated=negated,
                leaf_count=leaf_count,
                relaxable=relaxable,
                seen_relaxable=seen_relaxable,
            )
        return
    if isinstance(inner, ct.FilterNode2):
        for child in inner.or_:
            _walk(
                child,
                depth=depth + 1,
                negated=negated,
                leaf_count=leaf_count,
                relaxable=relaxable,
                seen_relaxable=seen_relaxable,
            )
        return
    if isinstance(inner, ct.FilterNode3):
        _walk(
            inner.not_,
            depth=depth + 1,
            negated=True,
            leaf_count=leaf_count,
            relaxable=relaxable,
            seen_relaxable=seen_relaxable,
        )
        return
    _validate_leaf(inner)
    leaf_count[0] += 1
    if leaf_count[0] > _MAX_CLAUSES:
        detail = f"filter tree clause count exceeds {_MAX_CLAUSES}"
        raise StageError(_FORBIDDEN_CODE, stage="plan", detail=detail)
    if negated or inner.op in _NEGATING_OPS:
        key = _field_str(inner.field)
        if key not in seen_relaxable:
            seen_relaxable.add(key)
            relaxable.append(inner.field)


def validate_and_normalize_user_filter(
    node: ct.FilterNode | None,
) -> tuple[ct.FilterNode | None, list[ct.FilterableField1]]:
    """사용자 필터를 검증하고 완화 대상 필드 목록을 함께 돌려준다(F-4·F-7, §7.3, §8).

    Args:
        node: `QueryRequest.filters`(원형, `page` 변환 전).

    Returns:
        `(node, relaxable_keys)` — `node`가 `None`이면 `relaxable_keys`도 빈 리스트.

    Raises:
        StageError: `plan.filter_field_forbidden` — 금지 필드·불허 연산자·깊이 초과·절수 초과.
    """
    if node is None:
        return None, []
    relaxable: list[ct.FilterableField1] = []
    _walk(node, depth=1, negated=False, leaf_count=[0], relaxable=relaxable, seen_relaxable=set())
    return node, relaxable


def compute_effective_hash(
    security_filter: ct.SecurityFilter,
    strategy_filter: ct.StrategyFilter,
    user_filter: ct.FilterNode | None,
    self_query_filter: ct.FilterNode | None,
) -> str:
    """F-5: `H("filters", canonical_json(계획 트리))` — `as_of`는 `":as_of"` 바인드 이름으로 치환한다.

    `as_of`를 실제 값 대신 바인드 이름으로 치환하는 이유는 시각만 다른 두 요청(같은 질의·필터·주체)이
    같은 `effective_hash`(따라서 같은 `plan:` 캐시 키)를 내게 하기 위함이다(04-pipelines/14 §10).
    """
    security_dict = security_filter.model_dump(mode="json", by_alias=True)
    security_dict["as_of"] = ":as_of"
    tree = {
        "security": security_dict,
        "strategy": strategy_filter.model_dump(mode="json", by_alias=True),
        "user": user_filter.model_dump(mode="json", by_alias=True) if user_filter is not None else None,
        "self_query": self_query_filter.model_dump(mode="json", by_alias=True)
        if self_query_filter is not None
        else None,
    }
    return hash_of("filters", canonical_json(tree))


def build_plan_filters(
    *,
    security: ct.SecurityContext,
    strategy: ct.Strategy,
    user_filter: ct.FilterNode | None,
    relaxable_keys: list[ct.FilterableField1],
    collection_ids: Sequence[ct.Ulid] | None = None,
) -> PlanFilters:
    """3층(`security` ∧ `strategy` ∧ `user`)을 결합해 `PlanFilters`를 조립한다(`self_query=None`).

    Args:
        security: 서버 주입 `SecurityContext`(F-1, 복사만).
        strategy: `rule_router.adopt_strategy()`가 채택한 전략.
        user_filter: `validate_and_normalize_user_filter()`를 통과한 사용자 필터(또는 `None`).
        relaxable_keys: 같은 호출이 돌려준 완화 대상 필드 목록(검증을 두 번 하지 않도록 호출측이
            `validate_and_normalize_user_filter()` 결과를 그대로 넘긴다).
        collection_ids: 요청 ∩ 보안 컬렉션(`planner._selected_collection_ids`). 생략 시
            `security.collection_ids`(허용된 전체 컬렉션) — 옛 호출부·테스트 호환용 기본값이며
            `planner.plan()`은 항상 명시적으로 넘긴다(리뷰 지적, `build_security_filter` 참고).
    """
    security_filter = build_security_filter(security, collection_ids=collection_ids)
    strategy_filter = strategy_filter_for(strategy)
    effective_hash = compute_effective_hash(security_filter, strategy_filter, user_filter, None)
    return PlanFilters(
        security=security_filter,
        strategy=strategy_filter,
        user=user_filter,
        self_query=None,
        relaxable_keys=relaxable_keys,
        effective_hash=effective_hash,
    )
