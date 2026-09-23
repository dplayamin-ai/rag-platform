"""Unit tests for `rag_platform.sdk.stage` (bible §4.1, §5.7, §11.3; ADR-0032)."""

from __future__ import annotations

import pytest

from rag_platform.sdk.stage import (
    RetryClass,
    Stage,
    StageError,
    classify_error,
    is_valid_code,
)


def test_is_valid_code_accepts_catalog_spelling() -> None:
    assert is_valid_code("fetch.access_denied")
    assert is_valid_code("contract.violation")


def test_is_valid_code_rejects_bad_spelling() -> None:
    assert not is_valid_code("FetchAccessDenied")
    assert not is_valid_code("fetch")  # missing ".reason"
    assert not is_valid_code("notastage.reason")  # unknown stage prefix


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        ("fetch.access_denied", RetryClass.NON_RETRYABLE),
        ("fetch.timeout", RetryClass.RETRYABLE),
        ("enrich.budget_exceeded", RetryClass.PARTIAL),
        ("parse.sidecar_unavailable", RetryClass.FALLBACK),
        ("some.unknown_code", RetryClass.NON_RETRYABLE),  # safe default
    ],
)
def test_classify_error_matches_bible_table(code: str, expected: RetryClass) -> None:
    assert classify_error(code) is expected


def test_stage_error_rejects_bad_code() -> None:
    with pytest.raises(ValueError, match=r"stage.*reason"):
        StageError("bad_code", stage="fetch")


def test_stage_error_default_retryable_follows_classification() -> None:
    retryable = StageError("fetch.timeout", stage="fetch")
    assert retryable.retryable is True
    assert retryable.classification is RetryClass.RETRYABLE

    non_retryable = StageError("fetch.access_denied", stage="fetch")
    assert non_retryable.retryable is False


def test_stage_error_to_payload_matches_contract_shape() -> None:
    error = StageError(
        "parse.corrupt_container",
        stage="parse",
        plugin_id="parser.pdf_docling_standard",
        detail="zip central directory truncated",
    )
    payload = error.to_payload()
    assert payload == {
        "code": "parse.corrupt_container",
        "type": "urn:rag:error:parse.corrupt_container",
        "retryable": False,
        "stage": "parse",
        "plugin_id": "parser.pdf_docling_standard",
        "detail": "zip central directory truncated",
    }


def test_stage_error_nested_cause_round_trips() -> None:
    cause = StageError("parse.sidecar_unavailable", stage="parse")
    error = StageError("parse.conversion_failed", stage="parse", cause=cause)
    assert error.to_payload()["cause"]["code"] == "parse.sidecar_unavailable"


class _DummyStage:
    """Minimal 5-member `Stage[bytes, bytes]` implementation for structural checks."""

    plugin_id = "chunker.dummy"
    config_schema = object  # placeholder; real stages use a pydantic.BaseModel subclass
    requires_lineage: tuple[str, ...] = ()

    def capabilities(self) -> object:
        return object()

    def fingerprint(self) -> str:
        return "fp-dummy"

    async def run(self, inp: bytes, ctx: object) -> bytes:
        return inp


def test_stage_protocol_is_structurally_satisfied() -> None:
    assert isinstance(_DummyStage(), Stage)


def test_stage_protocol_rejects_missing_members() -> None:
    class _Incomplete:
        plugin_id = "chunker.incomplete"

    assert not isinstance(_Incomplete(), Stage)
