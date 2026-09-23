"""`rag_platform.testing.idempotency` 단위 테스트 — `assert_stage_idempotent`/`assert_fingerprint_changes`가
스테이지 순수성(같은 입력·같은 `ctx` 고정값 → 동일 `stage_key`·산출물 해시)과 지문 변화(구성요소가 바뀌면
`fingerprint`·`stage_key`도 바뀜)를 실제로 검출하는지 검증한다.

설계 근거: ADR-0032 적합성 키트 표(`idempotency`), 준수 확인 방법 표 #2(스테이지 순수성)·#7(지문 구성요소).

구성: `_FixedClockCtx`(고정 시각만 제공하는 최소 `ctx`) + `_PureEchoStage`(입력·`ctx.now()`에만 의존하는
순수 스테이지)·`_ImpureStage`(`ctx`를 거치지 않고 `random`을 직접 읽어 순수성을 위반)·
`_FlakyFingerprintStage`(`fingerprint()` 자체가 비결정적)로 통과·산출물 해시 위반·`stage_key` 불안정 세
경로를 각각 검증하고, `assert_fingerprint_changes`의 통과·실패 경로를 별도로 검증한다.

불변식: 순수 스테이지는 같은 입력·같은 `ctx` 고정값에서 항상 같은 `stage_key`·산출물 해시를 낸다.
검증 계층: 1층(여기서 검증).
"""

from __future__ import annotations

import random
from datetime import UTC, datetime
from typing import Any

import pytest

from rag_platform.sdk.hashing import hash_of, stage_key as compute_stage_key
from rag_platform.testing.idempotency import assert_fingerprint_changes, assert_stage_idempotent

FIXED_NOW = datetime(2026, 1, 1, tzinfo=UTC)
STAGE_NAME = "enrich"
SCOPE_KEY = "01J.../01J.../01J..."
INPUT_HASH = "deadbeef" * 8


class _FixedClockCtx:
    """Minimal `StageContext` stand-in: only `now()` is exercised by the stages below."""

    def __init__(self, when: datetime) -> None:
        self._when = when

    def now(self) -> datetime:
        return self._when


class _PureEchoStage:
    """A stage whose output depends only on `inp` and `ctx.now()` (both fixed across two runs)."""

    plugin_id = "test.echo"

    def __init__(self, config_hash: str = "cfg-a") -> None:
        self._config_hash = config_hash

    def fingerprint(self) -> str:
        return hash_of("producer", self.plugin_id, "1.0.0", self._config_hash, "", "")

    async def run(self, inp: dict[str, Any], ctx: _FixedClockCtx) -> dict[str, Any]:
        return {"doubled": inp["x"] * 2, "seen_at": ctx.now().isoformat()}


class _ImpureStage(_PureEchoStage):
    """Violates stage purity (bible sec.4.1): reads entropy directly instead of through `ctx`."""

    async def run(self, inp: dict[str, Any], ctx: _FixedClockCtx) -> dict[str, Any]:
        return {"doubled": inp["x"] * 2, "noise": random.random()}  # noqa: S311 - deliberately impure fixture


class _FlakyFingerprintStage(_PureEchoStage):
    """Violates `stage_key` stability: `fingerprint()` itself is not deterministic."""

    def __init__(self) -> None:
        super().__init__()
        self._calls = 0

    def fingerprint(self) -> str:
        self._calls += 1
        return hash_of("producer", self.plugin_id, "1.0.0", f"cfg-{self._calls}", "", "")


async def test_assert_stage_idempotent_passes_for_a_pure_stage() -> None:
    stage = _PureEchoStage()
    key, _out_hash, out1, out2 = await assert_stage_idempotent(
        stage,
        {"x": 21},
        lambda: _FixedClockCtx(FIXED_NOW),
        stage_name=STAGE_NAME,
        scope_key=SCOPE_KEY,
        input_hash=INPUT_HASH,
    )
    assert out1 == out2
    assert key == compute_stage_key(STAGE_NAME, SCOPE_KEY, INPUT_HASH, stage.fingerprint())


async def test_assert_stage_idempotent_detects_impure_output() -> None:
    with pytest.raises(AssertionError, match="output hash differs"):
        await assert_stage_idempotent(
            _ImpureStage(),
            {"x": 1},
            lambda: _FixedClockCtx(FIXED_NOW),
            stage_name=STAGE_NAME,
            scope_key=SCOPE_KEY,
            input_hash=INPUT_HASH,
        )


async def test_assert_stage_idempotent_detects_unstable_stage_key() -> None:
    with pytest.raises(AssertionError, match="stage_key differs"):
        await assert_stage_idempotent(
            _FlakyFingerprintStage(),
            {"x": 1},
            lambda: _FixedClockCtx(FIXED_NOW),
            stage_name=STAGE_NAME,
            scope_key=SCOPE_KEY,
            input_hash=INPUT_HASH,
        )


def test_assert_fingerprint_changes_detects_a_changed_component() -> None:
    fp1, fp2 = assert_fingerprint_changes(
        _PureEchoStage(config_hash="cfg-a"),
        _PureEchoStage(config_hash="cfg-b"),
        stage_name=STAGE_NAME,
        scope_key=SCOPE_KEY,
        input_hash=INPUT_HASH,
    )
    assert fp1 != fp2


def test_assert_fingerprint_changes_rejects_identical_fingerprints() -> None:
    with pytest.raises(AssertionError, match="fingerprint did not change"):
        assert_fingerprint_changes(
            _PureEchoStage(config_hash="cfg-a"),
            _PureEchoStage(config_hash="cfg-a"),
            stage_name=STAGE_NAME,
            scope_key=SCOPE_KEY,
            input_hash=INPUT_HASH,
        )
