"""멀티테넌시·ACL 사전 필터 불변식을 검사하는 적합성 키트 모듈.

역할: `QueryPlan`/`IndexRecord`류 객체에 `tenant_id`·ACL 사전 필터 필드가 존재하고 비어있지 않은지
확인해, 바이블 §10.2 필터 불변식(모든 채널·모든 백엔드, 사전 필터 — 사후 필터 금지)을 값이 실제로 채워져
있는지 검사하는 형태로 재현한다. JSON Schema 검증만으로는 잡히지 않는다 — 예컨대
`IndexRecord.acl_allow`는 스키마상 `max_length=1024`만 있고 `min_length`가 없어(§10.2 (a) 보안 불변식은
문서 수준 서술일 뿐 스키마 제약이 아니다) 빈 배열도 유효한 `IndexRecord` 인스턴스가 된다 — 그 틈을 이
모듈이 메운다.
설계 근거: ADR-0032 적합성 키트 표(`security_invariants`), 준수 확인 방법 표 #9(`index_backend`·
`retriever`: `tenant_id` 필터 존재, 보안 필드 누락 배치 거부), 바이블 §10.2(필터 불변식 (a)(b)(c))·§10.3
(강제 지점 E1·E5·E17).
구성: `assert_tenant_prefilter(obj)` — `tenant_id`(최상위 또는 `QueryPlan`의 `filters.security` 경로)가
존재·비어있지 않은지 검사, 값을 반환; `assert_acl_prefilter(obj)` — ACL 사전 필터 필드(`IndexRecord.acl_allow`
또는 `QueryPlan.filters.security.principals` — 계약 생성물의 실제 필드명, 이 모듈이 새로 짓지 않는다)가
존재·비어있지 않은지 검사, `(field_name, value)` 반환; `assert_security_prefilters(obj)` — 위 둘을 한 번에.
불변식·주의: 필드명은 `src/rag_platform/contracts/`의 실제 생성 모델(§12 계약 정본)을 읽어 하드코딩했다 —
스키마가 바뀌어 철자가 달라지면 이 표(``_TENANT_FIELD_CANDIDATES``/``_ACL_PREFILTER_FIELD_CANDIDATES``)도
같이 갱신해야 한다(바이블 §1.2 minor 절차). 값이 `None`이거나 빈 문자열·빈 배열이면 실패로 간주한다(빈
배열은 §8.1에 따라 "없음"을 뜻하는 값이지 생략이 아니므로, 여기서는 그것이 곧 위반이다).
검증 계층: 1층(여기서 검증) — `tests/unit/testing/test_security_invariants.py`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pydantic import BaseModel

__all__ = ["assert_acl_prefilter", "assert_security_prefilters", "assert_tenant_prefilter"]

# Bible sec.10.2 invariant (a): mandatory tenant_id pre-filter. Checked at the object itself
# (`IndexRecord.tenant_id`) or, for `QueryPlan`, one level down at the server-composed security
# filter (`common_types.SecurityFilter.tenant_id` via `QueryPlan.filters.security`).
_TENANT_FIELD_CANDIDATES: tuple[str, ...] = ("tenant_id",)

# Bible sec.10.2 invariant (a): the ACL pre-filter. `IndexRecord.acl_allow` (index_record.py, the
# flattened `Acl.allow_principals`) and `common_types.SecurityFilter.principals` (the server-copied
# `SecurityContext.principals` a `QueryPlan.filters.security` carries) are the two concrete
# spellings contracts_gen currently produces for this — not a name this module invents.
_ACL_PREFILTER_FIELD_CANDIDATES: tuple[str, ...] = ("acl_allow", "principals")

# Where to look for the two field groups above: the object itself, or (QueryPlan's shape) nested
# one level under `.filters.security`.
_SECURITY_PATHS: tuple[tuple[str, ...], ...] = ((), ("filters", "security"))


def _resolve(obj: Any, path: tuple[str, ...]) -> Any:
    """Walk ``path`` via ``getattr``, stopping (returning ``None``) at the first missing hop."""
    for part in path:
        obj = getattr(obj, part, None)
        if obj is None:
            return None
    return obj


def _first_present(obj: Any, candidates: tuple[str, ...]) -> tuple[str, Any] | None:
    for name in candidates:
        if hasattr(obj, name):
            return name, getattr(obj, name)
    return None


def _scalar(value: Any) -> Any:
    """Unwrap a `RootModel` scalar wrapper (e.g. `common_types.Ulid`) to its plain value.

    Generated common-type scalars (`Ulid`, `PrincipalString`, ...) are `RootModel[str]` wrappers,
    so a bare `str(value)` would render pydantic's `repr` (``"root='...'"``) instead of the ULID
    text itself; unwrapping first keeps the returned/compared value the actual field content.
    """
    root = getattr(value, "root", None)
    return value if root is None else root


def assert_tenant_prefilter(obj: BaseModel) -> str:
    """Assert a non-empty ``tenant_id`` pre-filter field exists on ``obj``, return its value.

    Checks ``obj`` itself first (``IndexRecord.tenant_id``), then ``obj.filters.security``
    (``QueryPlan``'s shape) — the first hop where a ``tenant_id`` attribute is actually present
    wins, so passing either kind of object works without the caller naming which one it is.

    Raises:
        AssertionError: If no candidate field is present anywhere checked, or the value found is
            empty (``None``/``""``).
    """
    for path in _SECURITY_PATHS:
        target = _resolve(obj, path)
        if target is None:
            continue
        found = _first_present(target, _TENANT_FIELD_CANDIDATES)
        if found is None:
            continue
        name, value = found
        text = "" if value is None else str(_scalar(value))
        if not text:
            where = ".".join((*path, name))
            msg = f"{type(obj).__name__}.{where} is empty (bible sec.10.2 tenant pre-filter invariant)"
            raise AssertionError(msg)
        return text
    msg = f"{type(obj).__name__} has no tenant_id pre-filter field (checked {_SECURITY_PATHS!r})"
    raise AssertionError(msg)


def assert_acl_prefilter(obj: BaseModel) -> tuple[str, Any]:
    """Assert a non-empty ACL pre-filter field exists on ``obj``, return ``(field_name, value)``.

    Checks ``obj`` itself first (``IndexRecord.acl_allow``), then ``obj.filters.security``
    (``QueryPlan.filters.security.principals``).

    Raises:
        AssertionError: If no candidate field is present anywhere checked, or the value found is
            empty (``None``/``[]``/``""``).
    """
    for path in _SECURITY_PATHS:
        target = _resolve(obj, path)
        if target is None:
            continue
        found = _first_present(target, _ACL_PREFILTER_FIELD_CANDIDATES)
        if found is None:
            continue
        name, value = found
        if not value:
            where = ".".join((*path, name))
            msg = f"{type(obj).__name__}.{where} is empty (bible sec.10.2 ACL pre-filter invariant)"
            raise AssertionError(msg)
        return name, value
    msg = (
        f"{type(obj).__name__} has no ACL pre-filter field "
        f"(checked {_ACL_PREFILTER_FIELD_CANDIDATES!r} under {_SECURITY_PATHS!r})"
    )
    raise AssertionError(msg)


def assert_security_prefilters(obj: BaseModel) -> dict[str, Any]:
    """Run both `assert_tenant_prefilter` and `assert_acl_prefilter`; return a summary mapping."""
    tenant_id = assert_tenant_prefilter(obj)
    acl_field, acl_value = assert_acl_prefilter(obj)
    return {"tenant_id": tenant_id, "acl_field": acl_field, "acl_value": acl_value}
