"""Unit tests for `rag_platform.sdk.policy` (bible §4.4, §5.3, §11.3)."""

from __future__ import annotations

from datetime import timedelta

import pytest

from rag_platform.sdk.policy import (
    BackoffPolicy,
    StagePolicy,
    compute_backoff_delay,
    parse_duration,
    should_retry,
)
from rag_platform.sdk.stage import StageError


@pytest.mark.parametrize(
    ("value", "expected_seconds"),
    [
        ("30s", 30),
        ("5m", 300),
        ("1h", 3600),
        ("24h", 86400),
        ("500ms", 0.5),
    ],
)
def test_parse_duration_short_form(value: str, expected_seconds: float) -> None:
    assert parse_duration(value) == timedelta(seconds=expected_seconds)


def test_parse_duration_iso8601() -> None:
    assert parse_duration("PT5M") == timedelta(minutes=5)


def test_parse_duration_rejects_garbage() -> None:
    with pytest.raises(ValueError, match="Duration"):
        parse_duration("five minutes")


def test_backoff_policy_default_matches_bible() -> None:
    backoff = BackoffPolicy()
    assert backoff.initial == timedelta(seconds=1)
    assert backoff.max == timedelta(minutes=5)
    assert backoff.coefficient == 2.0


def test_stage_policy_from_mapping_parses_stage_policy_schema_shape() -> None:
    policy = StagePolicy.from_mapping(
        {
            "task_queue": "ingest-io",
            "start_to_close": "5m",
            "heartbeat": "30s",
            "max_attempts": 5,
            "non_retryable_error_codes": ["fetch.access_denied"],
            "resumable": False,
        }
    )
    assert policy.task_queue == "ingest-io"
    assert policy.start_to_close == timedelta(minutes=5)
    assert policy.heartbeat == timedelta(seconds=30)
    assert policy.max_attempts == 5
    assert policy.non_retryable_error_codes == ("fetch.access_denied",)
    assert policy.backoff == BackoffPolicy()  # not provided -> bible §5.3 default


def test_compute_backoff_delay_is_exponential_and_capped() -> None:
    policy = StagePolicy(
        task_queue="ingest-io",
        start_to_close=timedelta(minutes=5),
        heartbeat=None,
        max_attempts=10,
        resumable=False,
        backoff=BackoffPolicy(initial=timedelta(seconds=1), max=timedelta(seconds=10), coefficient=2.0),
    )
    assert compute_backoff_delay(policy, 1) == timedelta(seconds=1)
    assert compute_backoff_delay(policy, 2) == timedelta(seconds=2)
    assert compute_backoff_delay(policy, 3) == timedelta(seconds=4)
    assert compute_backoff_delay(policy, 10) == timedelta(seconds=10)  # capped at backoff.max


def test_compute_backoff_delay_rejects_attempt_below_one() -> None:
    policy = StagePolicy(
        task_queue="ingest-io", start_to_close=timedelta(minutes=5), heartbeat=None, max_attempts=3, resumable=False
    )
    with pytest.raises(ValueError, match="attempt"):
        compute_backoff_delay(policy, 0)


def test_should_retry_true_for_retryable_within_attempts() -> None:
    policy = StagePolicy(
        task_queue="ingest-io", start_to_close=timedelta(minutes=5), heartbeat=None, max_attempts=3, resumable=False
    )
    error = StageError("fetch.timeout", stage="fetch")
    assert should_retry(policy, 1, error) is True
    assert should_retry(policy, 3, error) is False  # attempt == max_attempts: no more retries


def test_should_retry_false_for_non_retryable_classification() -> None:
    policy = StagePolicy(
        task_queue="ingest-io", start_to_close=timedelta(minutes=5), heartbeat=None, max_attempts=5, resumable=False
    )
    error = StageError("fetch.access_denied", stage="fetch")
    assert should_retry(policy, 1, error) is False


def test_should_retry_false_when_profile_overrides_code_as_non_retryable() -> None:
    policy = StagePolicy(
        task_queue="ingest-io",
        start_to_close=timedelta(minutes=5),
        heartbeat=None,
        max_attempts=5,
        resumable=False,
        non_retryable_error_codes=("fetch.timeout",),
    )
    error = StageError("fetch.timeout", stage="fetch", retryable=True)
    assert should_retry(policy, 1, error) is False
