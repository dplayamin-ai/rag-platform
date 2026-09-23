"""RFC 9457 오류 응답 — `ApiError`/보안 예외를 `common_types.ProblemDetails`로 변환한다.

역할: API 표면 전체가 공유하는 오류 신호(`ApiError`)와, 그것과 `rag_platform.security.security_context`의
`AuthenticationError`/`AuthorizationError`를 `application/problem+json` 응답으로 바꾸는 예외 처리기를
제공한다. 각 엔드포인트 모듈(`api.ingest`/`api.jobs`/`api.query`)은 `ApiError`를 던지기만 하면 되고
상태 코드·본문 조립은 여기서 한 번만 한다.
설계 근거: 바이블 §14(`RFC 9457`)·§5.7(오류 코드 카탈로그, `code` 철자 정본); `05-api/01-api-design-
guidelines.md`(공통 오류 규약, 이 WP 읽기 예산 밖이라 인용하지 않음 — 계약 필드는 `common_types.
ProblemDetails`가 정본); ADR-0018(REST·SSE·MCP, no gRPC, RFC 9457).
구성: `ApiError` — 엔드포인트가 던지는 범용 오류(코드·상태·detail·instance·retryable·retry_after);
`build_problem_details(error, request_id=None)` — `ProblemDetails` 계약 인스턴스 조립(`trace_id`는
`uuid4` 32자 hex로 발급); `problem_response(error, request_id=None)` — 그 인스턴스를 `JSONResponse`로
직렬화(`Retry-After` 헤더 동봉); `register_exception_handlers(app)` — `ApiError`·
`AuthenticationError`·`AuthorizationError`·`RequestValidationError`·`StarletteHTTPException`·나머지
`Exception` 다섯 처리기를 등록.
불변식·주의: `code`는 반드시 `common_types.ErrorCodeCatalog` 철자여야 한다(그 외 값은 `ValueError`,
호출자 버그). 요청 본문·콘텐츠는 `detail`에 담지 않는다(§13 "콘텐츠 미포함"과 동일 원칙). 구조화된
`errors[].location.pointer` 배열은 이 WP 범위에서 만들지 않는다 — 단일 `detail` 문자열에 포인터를
적어 넣는다(open_issues, 04-management 세분화는 후속 WP).
검증 계층: 1층(여기서 검증) — `tests/api/test_api.py`.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from rag_platform.contracts import common_types as ct
from rag_platform.security.security_context import AuthenticationError, AuthorizationError

if TYPE_CHECKING:
    from fastapi import FastAPI, Request

__all__ = ["ApiError", "build_problem_details", "problem_response", "register_exception_handlers"]

# Curated titles for the codes this WP's endpoints actually raise (05-api tables); anything else
# falls back to a generic title derived from the code spelling.
_TITLES: dict[str, str] = {
    "contract.violation": "Contract violation",
    "auth.unauthenticated": "Unauthenticated",
    "auth.forbidden": "Forbidden",
    "auth.too_many_principals": "Too many principals",
    "api.idempotency_conflict": "Idempotency conflict",
    "api.idempotency_payload_mismatch": "Idempotency payload mismatch",
    "api.rate_limited": "Rate limited",
    "api.not_found": "Not found",
    "plan.collection_forbidden": "Collection forbidden",
    "render.empty_pack": "Empty context pack",
}


class ApiError(Exception):
    """RFC 9457 오류 신호 — 엔드포인트가 던지면 `register_exception_handlers`가 응답으로 바꾼다."""

    def __init__(
        self,
        code: str,
        *,
        status: int,
        detail: str | None = None,
        instance: str | None = None,
        retryable: bool = False,
        retry_after: int | None = None,
    ) -> None:
        """Build the error; `code` must be an `ErrorCodeCatalog` member spelling."""
        if code not in ct.ErrorCodeCatalog.__members__.values():
            msg = f"ApiError.code must be an ErrorCodeCatalog member (bible §5.7): {code!r}"
            raise ValueError(msg)
        super().__init__(detail or code)
        self.code = code
        self.status = status
        self.detail = detail
        self.instance = instance
        self.retryable = retryable
        self.retry_after = retry_after


def _title_for(code: str) -> str:
    """Return the curated title for `code`, or a generic title derived from its spelling."""
    return _TITLES.get(code, code.replace(".", " ").replace("_", " ").title())


def build_problem_details(
    code: str,
    *,
    status: int,
    detail: str | None = None,
    instance: str | None = None,
    retryable: bool = False,
    retry_after: int | None = None,
    request_id: str | None = None,
) -> ct.ProblemDetails:
    """Assemble a `common_types.ProblemDetails` instance for one error occurrence."""
    return ct.ProblemDetails.model_validate(
        {
            "type": f"urn:rag:error:{code}",
            "title": _title_for(code),
            "status": status,
            "detail": detail,
            "instance": instance,
            "code": code,
            "retryable": retryable,
            "trace_id": uuid.uuid4().hex,
            "errors": None,
            "retry_after": retry_after,
            "request_id": request_id,
        }
    )


def problem_response(
    code: str,
    *,
    status: int,
    detail: str | None = None,
    instance: str | None = None,
    retryable: bool = False,
    retry_after: int | None = None,
) -> JSONResponse:
    """Render one error occurrence as an `application/problem+json` `JSONResponse`."""
    problem = build_problem_details(
        code, status=status, detail=detail, instance=instance, retryable=retryable, retry_after=retry_after
    )
    headers: dict[str, str] = {}
    if retry_after is not None:
        headers["Retry-After"] = str(retry_after)
    return JSONResponse(
        status_code=status,
        content=problem.dump_contract(exclude_none=True),
        media_type="application/problem+json",
        headers=headers,
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register the five exception handlers that turn API errors into `ProblemDetails` bodies."""

    async def _handle_api_error(_request: Request, exc: ApiError) -> JSONResponse:
        return problem_response(
            exc.code,
            status=exc.status,
            detail=exc.detail,
            instance=exc.instance,
            retryable=exc.retryable,
            retry_after=exc.retry_after,
        )

    async def _handle_authentication_error(_request: Request, exc: AuthenticationError) -> JSONResponse:
        return problem_response(exc.code, status=exc.status, detail=exc.detail)

    async def _handle_authorization_error(_request: Request, exc: AuthorizationError) -> JSONResponse:
        return problem_response(exc.code, status=exc.status, detail=exc.detail)

    async def _handle_validation_error(_request: Request, exc: RequestValidationError) -> JSONResponse:
        return problem_response("contract.violation", status=400, detail=str(exc))

    async def _handle_http_exception(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = "api.not_found" if exc.status_code == 404 else "contract.violation"  # noqa: PLR2004 - HTTP 404
        return problem_response(code, status=exc.status_code, detail=str(exc.detail))

    async def _handle_unexpected(_request: Request, exc: Exception) -> JSONResponse:
        return problem_response("contract.violation", status=500, detail=f"unexpected error: {exc}")

    handlers: tuple[tuple[type[Exception], Any], ...] = (
        (ApiError, _handle_api_error),
        (AuthenticationError, _handle_authentication_error),
        (AuthorizationError, _handle_authorization_error),
        (RequestValidationError, _handle_validation_error),
        (StarletteHTTPException, _handle_http_exception),
        (Exception, _handle_unexpected),
    )
    for exc_type, handler in handlers:
        app.add_exception_handler(exc_type, handler)
