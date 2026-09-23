"""`Stage[In, Out]` 프로토콜, `StageError` 예외, 재시도 분류.

역할: 모든 단계(stage)가 구현해야 하는 5멤버 프로토콜과, 단계·셸이 던지는 예외 `StageError`,
그리고 오류 코드 → 재시도 분류(`RetryClass`) 매핑을 정의한다.
설계 근거: 바이블 §4.1(단계 시그니처), §5.3(`StageError`), §5.7(오류 코드 카탈로그, 철자 정본),
§11.3(재시도 분류); ADR-0032(플러그인 SDK, 5멤버 단계 프로토콜).
구성: `Stage` — `plugin_id`/`config_schema`/`capabilities()`/`fingerprint()`/`async run()`;
`StageError`(+`to_payload`) — 계약 `StageError` 모양을 그대로 미러링하는 SDK측 예외;
`RetryClass`/`CODE_CLASSIFICATION`/`classify_error` — §5.7 표를 코드로 옮긴 4분류; `is_valid_code` —
`{stage}.{reason}` 철자 검사.
불변식: `code`는 반드시 §5.7 카탈로그의 `{stage}.{reason}` 철자여야 한다(아니면 `ValueError`).
미등록 코드는 안전하게 `NON_RETRYABLE`로 분류한다. 계약 `StageError` 모델은 `TYPE_CHECKING` 아래에서만
참조해 런타임 의존성을 만들지 않는다.
검증 계층: 1층(여기서 검증) — tests/unit/test_sdk_stage.py.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Any, Protocol, TypeVar, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Mapping
    from datetime import datetime

    from pydantic import BaseModel

    from rag_platform.contracts.capabilities import Capabilities  # generated (bible §12)

In = TypeVar("In", contravariant=True)  # noqa: PLC0105 - bible §4.1 notation `Stage[In, Out]`
Out = TypeVar("Out", covariant=True)  # noqa: PLC0105 - bible §4.1 notation `Stage[In, Out]`

__all__ = [
    "CODE_CLASSIFICATION",
    "STAGE_NAMES",
    "RetryClass",
    "Stage",
    "StageError",
    "classify_error",
    "is_valid_code",
]

# Bible §5.7 "코드 접두 규약": {stage}.{reason}, snake_case on both sides.
_CODE_PATTERN = re.compile(r"^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$")

# Bible §4.2 pipeline table: pipeline stage names + non-pipeline error-code prefixes (§5.7).
STAGE_NAMES: frozenset[str] = frozenset(
    {
        "fetch",
        "detect",
        "parse",
        "normalize",
        "chunk",
        "recount",
        "enrich",
        "embed",
        "index",
        "publish",
        "plan",
        "retrieve",
        "fuse",
        "hydrate",
        "rerank",
        "postprocess",
        "pack",
        "render",
        "auth",
        "api",
        "profile",
        "plugin",
        "contract",
        "outbox",
    }
)


class RetryClass(StrEnum):
    """Bible §11.3 four-way retry classification; the shell's action per class.

    ``RETRYABLE``: exponential backoff up to ``StagePolicy.max_attempts``.
    ``NON_RETRYABLE``: fail immediately, compensate (saga) if applicable.
    ``PARTIAL``: keep going, mark ``quality=degraded``/``status=partial``.
    ``FALLBACK``: try the next adapter in the chain; degrade if the chain is exhausted.
    """

    RETRYABLE = "retryable"
    NON_RETRYABLE = "non_retryable"
    PARTIAL = "partial"
    FALLBACK = "fallback"


def is_valid_code(code: str) -> bool:
    """Return whether ``code`` matches the bible §5.7 ``{stage}.{reason}`` spelling."""
    if not _CODE_PATTERN.match(code):
        return False
    return code.split(".", 1)[0] in STAGE_NAMES


# Bible §5.7 "오류 코드 접두 규약과 카탈로그" table, transcribed code by code. Codes not listed
# under the "no"/"yes" retry columns are catalog warnings (`—`), not stage failures; they are not
# raised as `StageError` and so are absent from this table (see the docstring of `classify_error`).
CODE_CLASSIFICATION: dict[str, RetryClass] = {
    # fetch
    "fetch.access_denied": RetryClass.NON_RETRYABLE,
    "fetch.not_found": RetryClass.NON_RETRYABLE,
    "fetch.too_large": RetryClass.NON_RETRYABLE,
    "fetch.scheme_unsupported": RetryClass.NON_RETRYABLE,
    "fetch.egress_denied": RetryClass.NON_RETRYABLE,
    "fetch.timeout": RetryClass.RETRYABLE,
    "fetch.upstream_error": RetryClass.RETRYABLE,
    # parse
    "parse.unsupported_format": RetryClass.NON_RETRYABLE,
    "parse.unsupported_variant": RetryClass.NON_RETRYABLE,
    "parse.corrupt_container": RetryClass.NON_RETRYABLE,
    "parse.document_encrypted": RetryClass.NON_RETRYABLE,
    "parse.distribution_document": RetryClass.NON_RETRYABLE,
    "parse.block_limit_exceeded": RetryClass.NON_RETRYABLE,
    "parse.container_limit_exceeded": RetryClass.NON_RETRYABLE,
    "parse.sidecar_unavailable": RetryClass.FALLBACK,
    "parse.conversion_failed": RetryClass.FALLBACK,
    "parse.extractor_fallback": RetryClass.FALLBACK,
    "parse.page_timeout": RetryClass.PARTIAL,
    "parse.page_ocr_failed": RetryClass.PARTIAL,
    "parse.page_skipped": RetryClass.PARTIAL,
    # normalize
    "normalize.nfd_residual": RetryClass.NON_RETRYABLE,
    "normalize.pii_policy_violation": RetryClass.NON_RETRYABLE,
    "normalize.pii_detector_unavailable": RetryClass.RETRYABLE,
    # chunk
    "chunk.tokenizer_missing": RetryClass.NON_RETRYABLE,
    "chunk.count_exceeded": RetryClass.NON_RETRYABLE,
    # enrich
    "enrich.content_policy_violation": RetryClass.NON_RETRYABLE,
    "enrich.llm_policy_denied": RetryClass.NON_RETRYABLE,
    "enrich.budget_exceeded": RetryClass.PARTIAL,
    "enrich.extractor_timeout": RetryClass.PARTIAL,
    "enrich.llm_unavailable": RetryClass.RETRYABLE,
    # embed
    "embed.space_mismatch": RetryClass.NON_RETRYABLE,
    "embed.tokenizer_missing": RetryClass.NON_RETRYABLE,
    "embed.server_unavailable": RetryClass.RETRYABLE,
    "embed.token_overflow": RetryClass.PARTIAL,
    # index
    "index.security_fields_missing": RetryClass.NON_RETRYABLE,
    "index.generation_conflict": RetryClass.NON_RETRYABLE,
    "index.backend_unavailable": RetryClass.RETRYABLE,
    "index.partial_commit": RetryClass.NON_RETRYABLE,  # compensated (saga), then non-retryable
    # plan / retrieve / fuse / hydrate
    "plan.security_context_missing": RetryClass.NON_RETRYABLE,
    "plan.filter_field_forbidden": RetryClass.NON_RETRYABLE,
    "plan.collection_forbidden": RetryClass.NON_RETRYABLE,
    "plan.llm_failed": RetryClass.FALLBACK,
    "retrieve.security_context_missing": RetryClass.NON_RETRYABLE,
    "fuse.k_missing": RetryClass.NON_RETRYABLE,
    "retrieve.channel_timeout": RetryClass.RETRYABLE,
    "retrieve.backend_error": RetryClass.RETRYABLE,
    "retrieve.unavailable": RetryClass.RETRYABLE,
    "hydrate.backend_error": RetryClass.RETRYABLE,
    # rerank / postprocess / pack / render
    "rerank.schema_mismatch": RetryClass.NON_RETRYABLE,
    "rerank.timeout": RetryClass.FALLBACK,
    "postprocess.parent_text_miss": RetryClass.FALLBACK,
    "pack.tokenizer_mismatch": RetryClass.NON_RETRYABLE,
    "pack.count_api_failed": RetryClass.FALLBACK,
    "pack.acl_hint_unavailable": RetryClass.FALLBACK,
    "render.mixed_blocks": RetryClass.NON_RETRYABLE,
    "render.citations_with_structured_output": RetryClass.NON_RETRYABLE,
    "render.empty_pack": RetryClass.NON_RETRYABLE,
    "render.template_unsupported": RetryClass.NON_RETRYABLE,
    # auth / api / contract / profile / plugin / outbox
    "auth.unauthenticated": RetryClass.NON_RETRYABLE,
    "auth.forbidden": RetryClass.NON_RETRYABLE,
    "auth.too_many_principals": RetryClass.NON_RETRYABLE,
    "api.idempotency_conflict": RetryClass.NON_RETRYABLE,
    "api.idempotency_payload_mismatch": RetryClass.NON_RETRYABLE,
    "api.rate_limited": RetryClass.NON_RETRYABLE,
    "api.not_found": RetryClass.NON_RETRYABLE,
    "api.quota_exceeded": RetryClass.NON_RETRYABLE,
    "contract.violation": RetryClass.NON_RETRYABLE,
    "contract.schema_type_mismatch": RetryClass.NON_RETRYABLE,
    "contract.upcast_failed": RetryClass.NON_RETRYABLE,
    "profile.invalid": RetryClass.NON_RETRYABLE,
    "plugin.license_denied": RetryClass.NON_RETRYABLE,
    "plugin.capability_unsupported": RetryClass.NON_RETRYABLE,
    "outbox.egress_denied": RetryClass.NON_RETRYABLE,
    "outbox.relay_failed": RetryClass.RETRYABLE,
}


def classify_error(code: str) -> RetryClass:
    """Classify an error catalog code per bible §11.3.

    Unknown codes (not in :data:`CODE_CLASSIFICATION`, e.g. a future catalog addition this SDK
    has not been updated for) default to :attr:`RetryClass.NON_RETRYABLE` — the safe choice, since
    treating an unrecognized failure as retryable or partial could mask a real defect.
    """
    return CODE_CLASSIFICATION.get(code, RetryClass.NON_RETRYABLE)


@dataclass
class ErrorLocation:
    """Mirrors contract ``ErrorLocation`` (bible §5.3): identifiers only, no ACL/content."""

    pointer: str | None = None
    page: int | None = None
    block_id: str | None = None
    chunk_id: str | None = None
    channel: str | None = None
    collection_id: str | None = None
    document_id: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {k: v for k, v in vars(self).items() if v is not None}


class StageError(Exception):
    """SDK exception wrapping the contract ``StageError`` shape (bible §4.1, §5.3, §5.7).

    ``code`` must be a catalog entry spelled ``{stage}.{reason}`` (§5.7); ``retryable`` defaults to
    the catalog classification unless explicitly overridden by the caller. ``to_payload`` renders
    the contract-shaped mapping (`type = urn:rag:error:{code}`, RFC 9457 1:1).
    """

    def __init__(
        self,
        code: str,
        *,
        stage: str,
        retryable: bool | None = None,
        plugin_id: str | None = None,
        detail: str | None = None,
        message: str | None = None,
        artifact_ref: Mapping[str, Any] | None = None,
        occurred_at: datetime | None = None,
        attempt: int | None = None,
        location: ErrorLocation | None = None,
        cause: StageError | None = None,
    ) -> None:
        """Build a `StageError`; `retryable` defaults to the catalog classification of `code`."""
        if not is_valid_code(code):
            msg = f"StageError.code must be '{{stage}}.{{reason}}' (bible §5.7): {code!r}"
            raise ValueError(msg)
        code_stage = code.split(".", 1)[0]
        if code_stage != stage and stage not in STAGE_NAMES:
            msg = f"unknown stage {stage!r} for code {code!r}"
            raise ValueError(msg)
        classification = classify_error(code)
        super().__init__(detail or message or code)
        self.code = code
        self.type = f"urn:rag:error:{code}"
        self.stage = stage
        self.classification = classification
        self.retryable = classification is RetryClass.RETRYABLE if retryable is None else retryable
        self.plugin_id = plugin_id
        self.detail = detail
        self.message = message
        self.artifact_ref = dict(artifact_ref) if artifact_ref is not None else None
        self.occurred_at = occurred_at
        self.attempt = attempt
        self.location = location
        self.cause = cause

    def to_payload(self) -> dict[str, Any]:
        """Render the contract-shaped ``StageError`` mapping (bible §5.3)."""
        payload: dict[str, Any] = {
            "code": self.code,
            "type": self.type,
            "retryable": self.retryable,
            "stage": self.stage,
        }
        if self.plugin_id is not None:
            payload["plugin_id"] = self.plugin_id
        if self.detail is not None:
            payload["detail"] = self.detail
        if self.artifact_ref is not None:
            payload["artifact_ref"] = self.artifact_ref
        if self.message is not None:
            payload["message"] = self.message
        if self.occurred_at is not None:
            payload["occurred_at"] = self.occurred_at.isoformat()
        if self.attempt is not None:
            payload["attempt"] = self.attempt
        if self.location is not None:
            payload["location"] = self.location.to_payload()
        if self.cause is not None:
            payload["cause"] = self.cause.to_payload()
        return payload

    def __repr__(self) -> str:
        """Return a debug string with `code`, `stage` and `retryable`."""
        return f"StageError(code={self.code!r}, stage={self.stage!r}, retryable={self.retryable!r})"


@runtime_checkable
class Stage(Protocol[In, Out]):
    """Bible §4.1 / ADR-0032: the 5-member stage protocol, verbatim.

    ``plugin_id``, ``config_schema``, ``capabilities()``, ``fingerprint()``, ``async run(inp, ctx)``.
    The optional class attribute ``requires_lineage`` declares upstream ``schema_type`` names the
    shell must load into ``ctx.lineage`` alongside the boundary payload (bible §4.1).
    """

    plugin_id: str
    config_schema: type[BaseModel]
    requires_lineage: tuple[str, ...]

    def capabilities(self) -> Capabilities:
        """Return this stage's declared capabilities (bible §5.3 `Capabilities`)."""
        ...

    def fingerprint(self) -> str:
        """Return `H("producer", plugin_id, plugin_version, config_hash, ...)` (bible §4.1)."""
        ...

    async def run(self, inp: In, ctx: Any) -> Out:
        """Run this stage over `inp` under `ctx`; the only place a stage may have side effects."""
        ...
