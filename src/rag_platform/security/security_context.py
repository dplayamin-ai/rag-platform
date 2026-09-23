"""API 키 헤더 → `SecurityContext` 서버 주입 — 테넌트·주체를 자격 증명에서만 도출한다.

역할: `Authorization: Bearer <api_key>` 헤더를 파싱해 등록된 API 키 레코드를 찾고, 요청이 제시한
`collection_id`(들)과 그 레코드의 허용 목록을 교집합해 계약 `SecurityContext`(읽기 전용)를 만든다.
요청 본문의 `tenant_id`·`security_context` 같은 값은 여기서 만들어지는 값으로 완전히 대체된다
(ADR-0027) — 호출자(`api.ingest`/`api.query`)는 이 모듈이 돌려준 값만 쓰고 본문 값은 버린다.
설계 근거: 바이블 §10.3 E1(API 인증)·E2(API 인가 — 이 WP는 Cedar 정책 엔진 대신 고정 API 키
레지스트리로 근사, open_issues)·E6(플래너 `SecurityContext` 주입); `05-api/02-ingestion-api.md`
§2.1(헤더)·`05-api/03-retrieval-api.md` §2(주체 도출 규칙); 계약 `common_types.SecurityContext`.
구성: `ApiKeyRecord` — 키 1건의 테넌트·주체·역할·허용 컬렉션; `ApiKeyRegistry` — 인메모리 키
저장소(`register`/`resolve`); `AuthenticationError`/`AuthorizationError` — 401/403 신호;
`TooManyPrincipalsError` — 422 `auth.too_many_principals`(RFC 9457 매핑은 `api.problems`의 몫);
`parse_bearer_token` — `Authorization` 헤더 파싱; `authenticate` — 레지스트리 조회까지 묶은 진입점;
`derive_security_context` — `ApiKeyRecord` + 요청 `collection_ids` → `SecurityContext`;
`format_datetime` — 바이블 §6.3 `DateTime` 정본 표기.
불변식·주의: 실 Cedar 인가·OIDC JWT 검증·그룹 전이 폐쇄 확장을 구현하지 않는다(open_issues) — 키마다
고정된 `allowed_collection_ids`만으로 근사하고 `policy_version`은 상수다. API 키는 항상 서비스
주체다(ADR-0027 SecurityContext 불릿, `05-api/03-retrieval-api.md` §2 주체 문자열 행): 이 모듈이
만드는 `principals`는 `["service:{subject}"]`뿐이고 `user:`/`group:`/`tenant:*`를 절대 섞지 않는다
— `tenant:*`가 있으면 `visible_set`에 `tenant`를 넣어야 하는데(§10.1·§10.2) 서비스 주체는
`visible_set=["public"]`이 고정이라 `acl_visibility=tenant` 문서는 `acl_allow`에 그 서비스 주체가
있을 때만 보인다. 정렬·중복 제거 후 1,024개 초과면 `TooManyPrincipalsError`(이 레지스트리는 키당
주체 1개뿐이라 실제로는 발생하지 않지만 계약 상한을 여기서도 지킨다). `fastapi`/`starlette`를
임포트하지 않는다 — `mcp`·`cli`도 재사용할 수 있는 프레임워크 중립 계층이다(바이블 §12 레이어 지도).
검증 계층: 1층(여기서 검증) — `tests/api/test_api.py`, `tests/security/test_security_context.py`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from rag_platform.contracts import common_types as ct

if TYPE_CHECKING:
    from collections.abc import Sequence

__all__ = [
    "ApiKeyRecord",
    "ApiKeyRegistry",
    "AuthenticationError",
    "AuthorizationError",
    "TooManyPrincipalsError",
    "authenticate",
    "derive_security_context",
    "format_datetime",
    "parse_bearer_token",
    "root_value",
]

# `Authorization: Bearer <token>` (05-api/02 §2.1 표; 전용 헤더·쿼리 토큰 없음).
_BEARER_RE = re.compile(r"^Bearer\s+(\S+)$")

#: ADR-0027 SecurityContext 불릿 / 05-api/03 §2 표: 주체 상한(초과 시 422 `auth.too_many_principals`).
_MAX_PRINCIPALS = 1024


class AuthenticationError(Exception):
    """401 `auth.unauthenticated` 신호 — 자격 증명 부재·미인식 API 키(바이블 §10.3 E1)."""

    code = "auth.unauthenticated"
    status = 401

    def __init__(self, detail: str) -> None:
        """Build the error with a machine-oriented `detail` string (no request content)."""
        super().__init__(detail)
        self.detail = detail


class AuthorizationError(Exception):
    """403 `auth.forbidden` 신호 — 인가된 컬렉션 밖 접근(바이블 §10.3 E2, 존재 비노출)."""

    code = "auth.forbidden"
    status = 403

    def __init__(self, detail: str) -> None:
        """Build the error with a machine-oriented `detail` string (no request content)."""
        super().__init__(detail)
        self.detail = detail


class TooManyPrincipalsError(Exception):
    """422 `auth.too_many_principals` 신호 — 정렬·중복 제거한 주체 수 > 1,024(ADR-0027)."""

    code = "auth.too_many_principals"
    status = 422

    def __init__(self, detail: str) -> None:
        """Build the error with a machine-oriented `detail` string (no request content)."""
        super().__init__(detail)
        self.detail = detail


@dataclass(frozen=True)
class ApiKeyRecord:
    """API 키 1건 — 테넌트·주체·역할·허용 컬렉션(`None` = 테넌트 전체 컬렉션 허용)."""

    tenant_id: str
    subject: str
    roles: tuple[str, ...] = ()
    allowed_collection_ids: tuple[str, ...] | None = None


@dataclass
class ApiKeyRegistry:
    """API 키 → `ApiKeyRecord` 인메모리 레지스트리(Cedar·OIDC 대역; open_issues 참조)."""

    _records: dict[str, ApiKeyRecord] = field(default_factory=dict)

    def register(
        self,
        api_key: str,
        *,
        tenant_id: str,
        subject: str,
        roles: Sequence[str] = (),
        allowed_collection_ids: Sequence[str] | None = None,
    ) -> None:
        """Register `api_key` so `resolve`/`authenticate` can derive a context for it."""
        self._records[api_key] = ApiKeyRecord(
            tenant_id=tenant_id,
            subject=subject,
            roles=tuple(roles),
            allowed_collection_ids=None if allowed_collection_ids is None else tuple(allowed_collection_ids),
        )

    def resolve(self, api_key: str) -> ApiKeyRecord | None:
        """Return the registered record for `api_key`, or `None` if unknown."""
        return self._records.get(api_key)


def parse_bearer_token(header_value: str | None) -> str | None:
    """Extract the token from an `Authorization: Bearer <token>` header value, or `None`."""
    if header_value is None:
        return None
    match = _BEARER_RE.match(header_value.strip())
    return match.group(1) if match else None


def authenticate(registry: ApiKeyRegistry, authorization_header: str | None) -> ApiKeyRecord:
    """Resolve `authorization_header` to an `ApiKeyRecord` via `registry` (bible §10.3 E1).

    Raises:
        AuthenticationError: the header is absent/malformed, or the token is not registered.
    """
    token = parse_bearer_token(authorization_header)
    if token is None:
        msg = "missing or malformed Authorization header (expected 'Bearer <api_key>')"
        raise AuthenticationError(msg)
    record = registry.resolve(token)
    if record is None:
        msg = "unrecognized API key"
        raise AuthenticationError(msg)
    return record


def format_datetime(value: datetime) -> str:
    """Render `value` as the bible §6.3 `DateTime` wire form (UTC, millisecond precision, `Z`)."""
    return value.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def root_value(value: object) -> str:
    r"""Return the plain string behind a `RootModel[str]` contract wrapper (`Ulid`, `DateTime`, ...).

    Contract scalars generated by `tools/contracts_gen.py` wrap their value in a Pydantic
    `RootModel` — `str(instance)` returns the model's debug repr (`"root='...'"`), not the wrapped
    value, so every call site that needs the wire string must unwrap `.root` explicitly. `StrEnum`
    members (`Classification`, `AuthMethod`, `Renderer`, ...) have no `.root` and already stringify
    to their wire value, so this also passes those (and plain `str`) through unchanged.
    """
    root = getattr(value, "root", None)
    return root if isinstance(root, str) else str(value)


def derive_security_context(
    record: ApiKeyRecord,
    *,
    requested_collection_ids: Sequence[str],
    now: datetime,
    policy_version: str = "static-api-key-v1",
) -> ct.SecurityContext:
    """Build the server-injected `SecurityContext` for `record` (ADR-0027).

    `collection_ids` is `requested_collection_ids` intersected with `record.allowed_collection_ids`
    (order preserved, duplicates dropped) — `None` means the record's tenant may reach every
    requested collection (this stub registry has no collection catalog of its own to enumerate
    against). Callers decide what an empty result means (403 `auth.forbidden` for `POST /v1/ingest`,
    403 `plan.collection_forbidden` for `POST /v1/query`; bible §10.3 E2, 05-api/03 §2).

    `record` always authenticates via an API key, so `principals` is always the **service**
    principal form `["service:{subject}"]` — never `user:`/`group:`/`tenant:*` (those are for OIDC
    user principals, not derived by this module; ADR-0027 SecurityContext bullet, 05-api/03 §2
    "주체 문자열" row). Because there is no `tenant:*` in the set, `visible_set` is fixed to
    `["public"]`: an `acl_visibility=tenant` document is only visible when this record's service
    principal is itself in the document's `acl_allow` (bible §10.1/§10.2).

    Raises:
        TooManyPrincipalsError: the deduplicated principal list exceeds 1,024 entries (422
            `auth.too_many_principals`; ADR-0027, 05-api/03 §2). Unreachable with today's
            one-subject-per-key registry, but kept so the contract's cap is enforced here too.
    """
    requested = list(dict.fromkeys(requested_collection_ids))
    if record.allowed_collection_ids is None:
        collection_ids = requested
    else:
        allowed = set(record.allowed_collection_ids)
        collection_ids = [collection_id for collection_id in requested if collection_id in allowed]
    principals = sorted(dict.fromkeys([f"service:{record.subject}"]))
    if len(principals) > _MAX_PRINCIPALS:
        msg = f"resolved {len(principals)} principals for service:{record.subject}, exceeds cap {_MAX_PRINCIPALS}"
        raise TooManyPrincipalsError(msg)
    return ct.SecurityContext.model_validate(
        {
            "tenant_id": record.tenant_id,
            "principals": principals,
            "collection_ids": collection_ids,
            "as_of": format_datetime(now),
            "classification_max": "internal",
            "policy_version": policy_version,
            "auth_method": "api_key",
            "visible_set": ["public"],
        }
    )
