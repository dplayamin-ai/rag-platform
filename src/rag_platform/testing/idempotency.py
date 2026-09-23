"""Stage 순수성·재현성을 검사하는 적합성 키트 모듈.

역할: 같은 입력·설정으로 임의 `sdk.Stage` 구현 하나를 실제로 두 번 실행(모킹 없음)해, 스테이지 순수성(I/O·시간·난수는
`ctx.*`만) 위반이 산출물 차이로 드러나는지 검사한다. `assert_fingerprint_changes`는 그 대칭 축 —
지문 구성요소가 실제로 바뀌면 `fingerprint()`·`stage_key`도 바뀌는지 검사한다.
설계 근거: ADR-0032 적합성 키트 표(`idempotency`: "같은 입력·같은 ctx 고정값으로 2회 실행 → 산출물
`blake3` 동일"; E17 두 테넌트·두 컬렉션 격리), 준수 확인 방법 표 #2(스테이지 순수성)·#7(지문 구성요소 하나가
바뀌면 `fingerprint`·`stage_key`가 바뀜), 바이블 §6.2(`H()`/`stage_key` 공식), §12 `testing/`.
구성: `assert_stage_idempotent(stage, inp, ctx_factory, stage_name=, scope_key=, input_hash=, dump=)` —
`stage.run(inp, ctx)`을 독립적으로 빌드한 두 컨텍스트로 두 번 실행해 `stage_key`(`sdk.hashing.stage_key`)와
산출물 콘텐츠 해시(`sdk.hashing.blake3_hex`)가 일치하는지 검사, `(stage_key, output_hash, out1, out2)`
반환; `assert_fingerprint_changes(baseline, mutated, stage_name=, scope_key=, input_hash=)` — 구성요소가
다른 두 스테이지 인스턴스의 `fingerprint()`·파생 `stage_key`가 실제로 달라지는지 검사.
불변식·주의: 이 모듈은 `stage.run()`을 실제로 두 번 호출한다(모킹·패치 없음) — 결정성 위반은 여기서 드러나야
하는 버그다. `dump` 콜백을 생략하면 산출물이 pydantic `BaseModel`일 때
`rag_platform.testing.contract_roundtrip.dump_contract`로 정규 직렬화한 뒤 키 순서를 고정(`sort_keys=True`)
해 해시한다; 그 외 타입은 호출자가 `dump`를 넘겨야 한다. `ctx_factory`는 매 호출마다 *새* 컨텍스트 객체를
만들어야 한다(같은 고정값이되 동일 객체 재사용이 아님 — 두 번의 독립된 실행이라는 조건을 보존한다).
검증 계층: 1층(여기서 검증) — `tests/unit/testing/test_idempotency.py`.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, TypeVar

from pydantic import BaseModel

from rag_platform.sdk.hashing import blake3_hex, stage_key as compute_stage_key
from rag_platform.testing.contract_roundtrip import dump_contract

if TYPE_CHECKING:
    from collections.abc import Callable

    from rag_platform.sdk.stage import Stage

In = TypeVar("In")
Out = TypeVar("Out")

__all__ = ["assert_fingerprint_changes", "assert_stage_idempotent"]


def _default_dump(value: Any) -> bytes:
    """Canonicalize a stage output for hashing.

    `dump_contract()` for a contract model, else the value itself, both through
    `json.dumps(sort_keys=True)` so key order never causes a spurious mismatch between the two
    runs.
    """
    payload = dump_contract(value) if isinstance(value, BaseModel) else value
    return json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")


async def assert_stage_idempotent(  # noqa: UP047 - `In`/`Out` match `sdk.stage.Stage[In, Out]`'s own TypeVar style
    stage: Stage[In, Out],
    inp: In,
    ctx_factory: Callable[[], Any],
    *,
    stage_name: str,
    scope_key: str,
    input_hash: str,
    dump: Callable[[Out], bytes] | None = None,
) -> tuple[str, str, Out, Out]:
    """Run `stage.run(inp, ctx)` twice and assert `stage_key`/output hash match.

    Two independently-built (same-valued) contexts back the two runs (ADR-0032 `idempotency`,
    compliance #2).

    Args:
        stage: The stage under test.
        inp: The input value passed to both runs, unchanged.
        ctx_factory: Builds a fresh context for each run; both must carry the same fixed values
            (e.g. the same injected clock) so any difference in output traces back to the stage,
            not to the harness.
        stage_name: Passed straight through to `sdk.hashing.stage_key`.
        scope_key: Passed straight through to `sdk.hashing.stage_key`
            (`f"{tenant_id}/{collection_id}/{document_id}"`, ADR-0037).
        input_hash: Passed straight through to `sdk.hashing.stage_key`.
        dump: How to canonicalize an output for hashing; defaults to `_default_dump`.

    Returns:
        `(stage_key, output_hash, out1, out2)` for callers that want to assert more.

    Raises:
        AssertionError: If `stage_key` or the output hash differs between the two runs.
    """
    dump_fn = dump or _default_dump

    out1 = await stage.run(inp, ctx_factory())
    key1 = compute_stage_key(stage_name, scope_key, input_hash, stage.fingerprint())

    out2 = await stage.run(inp, ctx_factory())
    key2 = compute_stage_key(stage_name, scope_key, input_hash, stage.fingerprint())

    if key1 != key2:
        msg = f"idempotency violation: stage_key differs ({key1!r} != {key2!r}) — fingerprint() is not stable"
        raise AssertionError(msg)

    hash1 = blake3_hex(dump_fn(out1))
    hash2 = blake3_hex(dump_fn(out2))
    if hash1 != hash2:
        msg = f"idempotency violation: output hash differs ({hash1!r} != {hash2!r}) for identical input/ctx"
        raise AssertionError(msg)

    return key1, hash1, out1, out2


def assert_fingerprint_changes(
    baseline: Stage[Any, Any],
    mutated: Stage[Any, Any],
    *,
    stage_name: str,
    scope_key: str,
    input_hash: str,
) -> tuple[str, str]:
    """Assert two stage instances with a differing fingerprint component produce different keys.

    A changed `config_hash`/`analyzer_id`/`dictionary_hash`/`embedding_profile_hash`/
    `chunker_config_hash` must invalidate both `fingerprint()` and any cached `stage_key` derived
    from it (ADR-0032 compliance #7).

    Returns:
        `(baseline.fingerprint(), mutated.fingerprint())` for callers that want to assert more.

    Raises:
        AssertionError: If the fingerprints (or their derived `stage_key`s) are equal.
    """
    fp1, fp2 = baseline.fingerprint(), mutated.fingerprint()
    if fp1 == fp2:
        msg = f"fingerprint did not change between baseline and mutated stage: both are {fp1!r}"
        raise AssertionError(msg)

    key1 = compute_stage_key(stage_name, scope_key, input_hash, fp1)
    key2 = compute_stage_key(stage_name, scope_key, input_hash, fp2)
    if key1 == key2:
        msg = f"stage_key did not change even though fingerprint did ({fp1!r} -> {fp2!r})"
        raise AssertionError(msg)

    return fp1, fp2
