"""표준 필터 DSL → Qdrant `Filter` 순수 변환기 — 보안(a)·전략(b)·사용자·self-query 필터를 사전 필터 하나로 합친다.

설계 근거: 04-pipelines/13 §4.3(변환 표·예시 JSON), 바이블 §10.2(보안 불변식 (a) 제거·완화 불가, E7), §5.7
`FilterableField`(가상 필드 `page`), ADR-0027. 계약 타입: `PlanFilters`·`SecurityFilter`·`StrategyFilter`·`FilterNode`.

구성:
- `build_filter(security, strategy, user, self_query)` — 네 묶음을 `Filter{must, must_not}`로 변환(보안 없으면 예외)
- `from_plan_filters(filters)` — `QueryPlan.filters`(`PlanFilters`) 그대로 변환
- `node_to_condition(node)` — `FilterNode` 트리(and/or/not/리프) 재귀 변환(§4.3 표 1:1)
- `scope_filter(tenant_id, ...)` — 사가·정리 잡의 쓰기 범위 필터(항상 `tenant_id` 포함)
- `assert_search_secured(filter)` / `assert_tenant_scoped(filter)` — 검색·쓰기 직전 E7 구조 검사
- `to_canonical_json(filter)` — 변환 결과의 canonical JSON(`filters_applied.effective_hash` 입력)

불변식: 검색 필터 `must`에는 `tenant_id`·`is_current=true`·ACL `should`, `must_not`에는 `acl_deny`가 반드시 있다 —
없으면 `retrieve.security_context_missing`. `acl_classification ≤ max`는 열거 순서 집합(`MatchAny`)으로 바꾼다.
`prefix`는 Qdrant 1.19 keyword `MatchPrefix`로 변환한다(스파이크 실측: 로컬 모드 동작, 서버는 `prefix: true` 인덱스).
검증 계층: 1층(여기서 검증) — `tests/adapters/index/test_qdrant_local.py`(필터 누락 거부, 테넌트 격리).
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import TYPE_CHECKING, Any

from qdrant_client import models

from rag_platform.contracts.common_types import (
    Classification,
    FilterableField,
    FilterNode,
    FilterNode1,
    FilterNode2,
    FilterNode3,
    FilterNode4,
    FilterOp,
    SecurityFilter,
    StrategyFilter,
)
from rag_platform.sdk.stage import StageError

if TYPE_CHECKING:
    from rag_platform.contracts.query_plan import PlanFilters

__all__ = [
    "assert_search_secured",
    "assert_tenant_scoped",
    "build_filter",
    "from_plan_filters",
    "node_to_condition",
    "scope_filter",
    "to_canonical_json",
]

_CONTRACT_VIOLATION = "contract.violation"
_SECURITY_CONTEXT_MISSING = "retrieve.security_context_missing"
_SECURITY_FIELDS_MISSING = "index.security_fields_missing"

_PLUGIN_ID = "index_backend.qdrant"
#: User-filterable datetime payload fields (`doc_date` is `string(date)` -> `DatetimeRange`).
_DATETIME_FIELDS = frozenset({"doc_date"})
#: Integer payload fields accepting numeric `Range`; `custom.*` numeric keys are also allowed.
_NUMERIC_FIELDS = frozenset({"page_start", "page_end"})
_RANGE_OPS = {FilterOp.gt: "gt", FilterOp.gte: "gte", FilterOp.lt: "lt", FilterOp.lte: "lte"}


def _violation(detail: str) -> StageError:
    return StageError(_CONTRACT_VIOLATION, stage="index", plugin_id=_PLUGIN_ID, detail=detail)


def _field(key: str, value: Any) -> models.FieldCondition:
    return models.FieldCondition(key=key, match=models.MatchValue(value=value))


def _any(key: str, values: list[Any]) -> models.FieldCondition:
    return models.FieldCondition(key=key, match=models.MatchAny(any=values))


def _is_null(key: str) -> models.IsNullCondition:
    return models.IsNullCondition(is_null=models.PayloadField(key=key))


def _is_empty(key: str) -> models.IsEmptyCondition:
    return models.IsEmptyCondition(is_empty=models.PayloadField(key=key))


def _field_name(leaf: FilterNode4) -> str:
    root = leaf.field.root
    return str(root.value) if isinstance(root, FilterableField) else root.root


def _as_list(value: Any, op: FilterOp) -> list[Any]:
    if not isinstance(value, list) or not value:
        msg = f"filter op {op.value!r} needs a non-empty array value"
        raise _violation(msg)
    return value


def _range_condition(key: str, op: FilterOp, value: Any) -> models.FieldCondition:
    bound = _RANGE_OPS[op]
    if key in _DATETIME_FIELDS:
        return models.FieldCondition(key=key, range=models.DatetimeRange(**{bound: value}))
    if key in _NUMERIC_FIELDS or key.startswith("custom."):
        return models.FieldCondition(key=key, range=models.Range(**{bound: value}))
    msg = f"range op {op.value!r} is not defined for keyword field {key!r}"
    raise _violation(msg)


def _one_page(page: Any) -> models.Filter:
    return models.Filter(
        must=[
            models.FieldCondition(key="page_start", range=models.Range(lte=page)),
            models.FieldCondition(key="page_end", range=models.Range(gte=page)),
        ]
    )


def _page_condition(op: FilterOp, value: Any) -> models.Filter:
    """Virtual field `page` (bible §5.7): `page_start <= v <= page_end`; `in` ORs the pages."""
    if op is FilterOp.eq:
        return _one_page(value)
    if op is FilterOp.in_:
        return models.Filter(should=[_one_page(page) for page in _as_list(value, op)])
    msg = f"virtual field 'page' supports only eq/in, got {op.value!r}"
    raise _violation(msg)


def _exists_condition(key: str, value: Any) -> models.Filter:
    if not isinstance(value, bool):
        msg = "filter op 'exists' needs a boolean value"
        raise _violation(msg)
    # User fields may be absent or null: IsNull and IsEmpty together (13 §4.3 `exists` row).
    if value:
        return models.Filter(must_not=[_is_null(key), _is_empty(key)])
    return models.Filter(should=[_is_null(key), _is_empty(key)])


def _prefix_condition(key: str, value: Any) -> models.FieldCondition:
    if not isinstance(value, str) or not value:
        msg = "filter op 'prefix' needs a non-empty string value"
        raise _violation(msg)
    return models.FieldCondition(key=key, match=models.MatchPrefix(prefix=value))


def _leaf_condition(leaf: FilterNode4) -> models.Condition:  # noqa: PLR0911 - one branch per §4.3 row
    key = _field_name(leaf)
    op, value = leaf.op, leaf.value
    if key == "page":
        return _page_condition(op, value)
    if op is FilterOp.eq:
        return _field(key, value)
    if op is FilterOp.ne:
        return models.Filter(must_not=[_field(key, value)])
    if op in (FilterOp.in_, FilterOp.contains_any):
        return _any(key, _as_list(value, op))
    if op is FilterOp.not_in:
        return models.Filter(must_not=[_any(key, _as_list(value, op))])
    if op is FilterOp.contains_all:
        return models.Filter(must=[_field(key, item) for item in _as_list(value, op)])
    if op in _RANGE_OPS:
        return _range_condition(key, op, value)
    if op is FilterOp.exists:
        return _exists_condition(key, value)
    return _prefix_condition(key, value)  # FilterOp.prefix — the only remaining member


def node_to_condition(node: FilterNode) -> models.Condition:
    """Translate one `FilterNode` (and/or/not/leaf) into a Qdrant condition (13 §4.3 table)."""
    root = node.root
    if isinstance(root, FilterNode1):
        return models.Filter(must=[node_to_condition(child) for child in root.and_])
    if isinstance(root, FilterNode2):
        # `or` stays a nested Filter inside `must` so it never mixes with sibling musts (13 §4.3).
        return models.Filter(should=[node_to_condition(child) for child in root.or_])
    if isinstance(root, FilterNode3):
        return models.Filter(must_not=[node_to_condition(root.not_)])
    return _leaf_condition(root)


def _classification_set(maximum: Classification) -> list[str]:
    ordered = list(Classification)  # enum order = rank order (public < internal < confidential < secret)
    return [c.value for c in ordered[: ordered.index(maximum) + 1]]


def _security_parts(security: SecurityFilter) -> tuple[list[models.Condition], list[models.Condition]]:
    principals = [p.root for p in security.principals]
    as_of = datetime.fromisoformat(security.as_of.root)  # RFC 3339 `...Z` (Python >= 3.11)
    must: list[models.Condition] = [
        _field("tenant_id", security.tenant_id.root),
        _any("collection_id", [c.root for c in security.collection_ids]),
        _field("is_current", value=True),
        models.Filter(
            should=[
                _any("acl_visibility", [v.value for v in security.visible_set]),
                _any("acl_allow", principals),
            ]
        ),
        models.Filter(
            should=[
                _is_null("acl_embargo_until"),
                models.FieldCondition(key="acl_embargo_until", range=models.DatetimeRange(lte=as_of)),
            ]
        ),
        models.Filter(
            should=[
                _is_null("acl_expires_at"),
                models.FieldCondition(key="acl_expires_at", range=models.DatetimeRange(gt=as_of)),
            ]
        ),
        _any("acl_classification", _classification_set(security.classification_max)),
    ]
    must_not: list[models.Condition] = [_any("acl_deny", principals)]
    return must, must_not


def build_filter(
    security: SecurityFilter | None,
    strategy: StrategyFilter | None = None,
    user: FilterNode | None = None,
    self_query: FilterNode | None = None,
) -> models.Filter:
    """Combine security AND strategy AND user AND self_query into one pre-filter (bible §10.2).

    Raises `retrieve.security_context_missing` when `security` is absent (E7): no search may
    run without the tenant/ACL invariant.
    """
    if security is None:
        raise StageError(
            _SECURITY_CONTEXT_MISSING,
            stage="retrieve",
            plugin_id=_PLUGIN_ID,
            detail="Qdrant search requires the security filter (tenant_id + ACL) - bible §10.2 (a)",
        )
    must, must_not = _security_parts(security)
    if strategy is not None:
        must.append(_any("level", [int(level) for level in strategy.level_in]))
        must.append(_any("item_kind", [kind.value for kind in strategy.item_kinds]))
    must.extend(node_to_condition(node) for node in (user, self_query) if node is not None)
    return models.Filter(must=must, must_not=must_not)


def from_plan_filters(filters: PlanFilters) -> models.Filter:
    """Translate `QueryPlan.filters` as stored (security + strategy + user + self_query)."""
    return build_filter(filters.security, filters.strategy, filters.user, filters.self_query)


def scope_filter(
    tenant_id: str,
    *,
    collection_id: str | None = None,
    document_id: str | None = None,
    index_generation: int | None = None,
    commit_id: str | None = None,
    is_current: bool | None = None,
) -> models.Filter:
    """Write-side scope filter for sagas/cleanup (flip, delete, count) - always carries `tenant_id`."""
    if not tenant_id:
        raise StageError(
            _SECURITY_FIELDS_MISSING,
            stage="index",
            plugin_id=_PLUGIN_ID,
            detail="write scope filter requires tenant_id",
        )
    must: list[models.Condition] = [_field("tenant_id", tenant_id)]
    optional: dict[str, Any] = {
        "collection_id": collection_id,
        "document_id": document_id,
        "index_generation": index_generation,
        "commit_id": commit_id,
        "is_current": is_current,
    }
    must.extend(_field(key, value) for key, value in optional.items() if value is not None)
    return models.Filter(must=must)


def _conditions(part: list[models.Condition] | models.Condition | None) -> list[models.Condition]:
    if part is None:
        return []
    return part if isinstance(part, list) else [part]


def _has_match(conditions: list[models.Condition], key: str, value: Any = None) -> bool:
    for cond in conditions:
        if not (isinstance(cond, models.FieldCondition) and cond.key == key and cond.match is not None):
            continue
        if value is None or (isinstance(cond.match, models.MatchValue) and cond.match.value == value):
            return True
    return False


def _tenant_of(query_filter: models.Filter | None) -> str | None:
    if query_filter is None:
        return None
    for cond in _conditions(query_filter.must):
        if (
            isinstance(cond, models.FieldCondition)
            and cond.key == "tenant_id"
            and isinstance(cond.match, models.MatchValue)
            and isinstance(cond.match.value, str)
            and cond.match.value
        ):
            return cond.match.value
    return None


def assert_search_secured(query_filter: models.Filter | None) -> str:
    """Check the E7 structure of a search pre-filter and return its `tenant_id`.

    Required: `must` has `tenant_id` (MatchValue), `is_current=true` and a nested `should`
    containing `acl_allow`; `must_not` has `acl_deny`. Otherwise `retrieve.security_context_missing`.
    """
    tenant_id = _tenant_of(query_filter)
    must = _conditions(query_filter.must) if query_filter is not None else []
    must_not = _conditions(query_filter.must_not) if query_filter is not None else []
    acl_should = any(
        isinstance(cond, models.Filter) and _has_match(_conditions(cond.should), "acl_allow") for cond in must
    )
    if (
        tenant_id is None
        or not _has_match(must, "is_current", value=True)
        or not acl_should
        or not _has_match(must_not, "acl_deny")
    ):
        raise StageError(
            _SECURITY_CONTEXT_MISSING,
            stage="retrieve",
            plugin_id=_PLUGIN_ID,
            detail="search filter lacks tenant_id / is_current / acl pre-filter (E7)",
        )
    return tenant_id


def assert_tenant_scoped(query_filter: models.Filter | None) -> str:
    """Check that a write/count filter is tenant-scoped (13 §4.3 last paragraph); return `tenant_id`."""
    tenant_id = _tenant_of(query_filter)
    if tenant_id is None:
        raise StageError(
            _SECURITY_FIELDS_MISSING,
            stage="index",
            plugin_id=_PLUGIN_ID,
            detail="write/count filter lacks tenant_id",
        )
    return tenant_id


def to_canonical_json(query_filter: models.Filter) -> str:
    """Render `query_filter` as canonical JSON (sorted keys, no whitespace, nulls dropped)."""
    data = query_filter.model_dump(mode="json", exclude_none=True)
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
