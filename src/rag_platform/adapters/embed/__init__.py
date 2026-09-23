"""Embed 어댑터 공유 헬퍼 — `embedding_space_id` 산출·L2 정규화 재검증·HTTP 재시도 정책을 모은다.

역할: `tei_dense`·`vllm_pooling_bge_m3` 두 HTTP 어댑터가 공통으로 쓰는 순수 함수를 한 곳에 둬,
공간 식별자·재시도 정책을 같은 코드로 계산하게 한다(04-pipelines/12 §2.1).
설계 근거: §2.1(`embedding_space_id = H("space", model_id, revision, str(dim), str(normalized),
prompt_hash, quantization, vocab_id or "")`, 바이블 §6.2), §2.5(`prompt_hash` 산출), §5(재시도:
연결 오류·429·503·5xx 3회 지터 백오프 0.5s→1s→2s, 4xx 즉시 비재시도), §8.1(dense 항상 L2 정규화).
구성: `l2_normalize`/`assert_l2_normalized` — 정규화·§2.2 7단계 재검증; `prompt_hash`/`space_id`
— SDK `hash_of` 재사용 산출 함수; `post_with_retry` — §5 재시도 정책 공용 HTTP POST 헬퍼.
불변식: `random`을 직접 import하지 않는다(§10.2 순수성 — 엔트로피는 호출자가 주입하는 `jitter`
콜백으로만 얻고, 기본값은 지터 없음). `time.sleep`은 엔트로피가 아니라 banned-api 목록에 없다.
검증 계층: 1층(여기서 검증) — tests/adapters/embed/test_embed_adapters.py.
"""

from __future__ import annotations

import json
import math
import time
from typing import TYPE_CHECKING, Any

import httpx

from rag_platform.sdk.hashing import hash_of
from rag_platform.sdk.stage import StageError

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence

__all__ = [
    "CONTRACT_VIOLATION",
    "RETRYABLE_STATUS_CODES",
    "SERVER_UNAVAILABLE",
    "assert_l2_normalized",
    "l2_normalize",
    "post_with_retry",
    "prompt_hash",
    "space_id",
]

# sdk.stage.StageError §5.7 catalog codes this package raises; shared so no call site repeats the
# literal (also sidesteps ruff EM101 "exception must not use a string literal").
CONTRACT_VIOLATION = "contract.violation"
SERVER_UNAVAILABLE = "embed.server_unavailable"

# doc 12 §5 "어댑터 내부 재시도": connection errors, 429, 503, 5xx retry; 4xx(400·413·422)는 즉시
# 비재시도(호출자·어댑터 버그로 간주).
RETRYABLE_STATUS_CODES: frozenset[int] = frozenset({429, 503, *range(500, 600)})
_DEFAULT_BACKOFF_S: tuple[float, ...] = (0.5, 1.0, 2.0)  # doc 12 §5: 지터 포함 합 <= 4s


def l2_normalize(vector: Sequence[float]) -> list[float]:
    """Scale `vector` to unit L2 norm (bible §5.4 dense convention, doc 12 §8.1 "항상 L2 정규화").

    Args:
        vector: Raw dense embedding values from the serving backend.

    Returns:
        A new list with the same direction and unit L2 norm. A zero vector (no direction to
        normalize toward) is returned unchanged rather than raising.
    """
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0.0:
        return list(vector)
    return [value / norm for value in vector]


def assert_l2_normalized(vector: Sequence[float], *, plugin_id: str, tol: float = 1e-4) -> None:
    """Re-verify ``‖vector‖₂ = 1 ± tol`` (doc 12 §2.2 step 7: normalization is re-checked, not trusted).

    Args:
        vector: A dense embedding the adapter already normalized.
        plugin_id: Reporting `PluginMeta.plugin_id`, carried on the raised `StageError`.
        tol: Absolute tolerance around 1.0 (doc 12 §2.2 step 7 default).

    Raises:
        StageError: `contract.violation` if the norm falls outside `1 ± tol` — an adapter bug
            (own normalization failed), never a retryable server condition.
    """
    norm = math.sqrt(sum(value * value for value in vector))
    if abs(norm - 1.0) > tol:
        msg = f"{plugin_id}: dense vector norm {norm!r} outside 1 +/- {tol} (doc 12 sec 2.2 step 7)"
        raise StageError(CONTRACT_VIOLATION, stage="embed", plugin_id=plugin_id, detail=msg)


def prompt_hash(*, document: str | None = None, query: str | None = None) -> str:
    """Compute ``prompt_hash = H("config", canonical_json(prompts))`` (doc 12 §2.5).

    Empty-string templates count as absent (doc 12 §2.5 "빈 문자열 키는 제거"). With neither
    template this hashes ``"{}"``, matching 03-contracts/07 §3's "empty object" convention.

    Args:
        document: The document-mode prompt template, or `None`/empty if the model needs none.
        query: The query-mode prompt template, or `None`/empty if the model needs none.

    Returns:
        A 64-character lowercase hex BLAKE3 digest.
    """
    prompts = {k: v for k, v in (("document", document), ("query", query)) if v}
    canonical = json.dumps(prompts, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hash_of("config", canonical)


def space_id(
    *,
    model_id: str,
    revision: str,
    dim: int,
    normalized: bool,
    prompt_hash_value: str,
    quantization: str,
    vocab_id: str | None = None,
) -> str:
    """Compute the bible §6.2 / doc 12 §2.1 embedding space identifier.

    ``H("space", model_id, revision, str(dim), str(normalized), prompt_hash, quantization,
    vocab_id or "")``. `dim`/`vocab_id` already differ between a model's dense and
    `sparse_learned` channels, so the two channels hash to different spaces without `name` (the
    channel discriminant) needing to be part of the tuple.

    Args:
        model_id: HF repo id, e.g. `"BAAI/bge-m3"` (paired with `revision` in `Producer.model_ids`).
        revision: HF commit SHA or tag (bible §6.1); `"latest"`/`"main"` are forbidden (ADR-0009).
        dim: Output dimension (dense) or vocabulary size (sparse).
        normalized: Whether this channel's vectors are L2-normalized (dense is always `True`).
        prompt_hash_value: The `prompt_hash` from :func:`prompt_hash`.
        quantization: Model-side quantization vocabulary (doc 12 §8.3: `none`/`onnx_int8`/
            `output_int8`/`output_binary`).
        vocab_id: Sparse vocabulary id, or `None` for a dense channel.

    Returns:
        A 64-character lowercase hex BLAKE3 digest, matching `common_types.Hex64`.
    """
    return hash_of(
        "space",
        model_id,
        revision,
        str(dim),
        str(normalized),
        prompt_hash_value,
        quantization,
        vocab_id or "",
    )


def post_with_retry(
    client: httpx.Client,
    url: str,
    *,
    json_body: Mapping[str, Any],
    plugin_id: str,
    max_retries: int = 3,
    backoff_schedule: tuple[float, ...] = _DEFAULT_BACKOFF_S,
    sleep: Callable[[float], None] = time.sleep,
    jitter: Callable[[], float] | None = None,
) -> httpx.Response:
    """POST `json_body` to `url`, applying doc 12 §5's short internal retry policy.

    Connection failures and HTTP 429/503/5xx responses retry up to `max_retries` times with the
    jittered `backoff_schedule` (default 0.5s/1s/2s, sum <= 4s); HTTP 400/413/422 fail immediately
    without retrying (adapter/caller bug, e.g. a truncation defect). Once retries are exhausted
    this raises `embed.server_unavailable` (retryable — the caller's orchestrator owns the long
    Temporal backoff, doc 12 §5).

    Args:
        client: An `httpx.Client` bound to the embedding server's base URL and timeouts.
        url: Request path (e.g. `"/embed"`, `"/pooling"`), resolved against `client.base_url`.
        json_body: The JSON request body.
        plugin_id: Reporting `PluginMeta.plugin_id`, carried on any raised `StageError`.
        max_retries: Number of retries after the first attempt (doc 12 §5 default: 3).
        backoff_schedule: Per-attempt base delay in seconds before each retry.
        sleep: Injectable delay function (tests pass a recorder instead of really sleeping).
        jitter: Optional `() -> float` in `[0, 1]` scaling each delay; `None` means no jitter —
            this module never imports `random` itself (bible §10.2 purity), so any randomness is
            the caller's to inject.

    Returns:
        The successful `httpx.Response` (status < 400).

    Raises:
        StageError: `contract.violation` for a 400/413/422 response; `embed.server_unavailable`
            once `max_retries` retryable failures are exhausted.
    """
    last_detail = "no attempt made"
    for attempt in range(max_retries + 1):
        try:
            response = client.post(url, json=json_body)
        except httpx.TransportError as exc:
            last_detail = f"transport error: {exc}"
        else:
            if response.status_code < httpx.codes.BAD_REQUEST:
                return response
            if response.status_code not in RETRYABLE_STATUS_CODES:
                msg = (
                    f"{plugin_id}: {url} returned {response.status_code} (non-retryable, doc 12 "
                    f"sec 5): {response.text[:200]}"
                )
                raise StageError(CONTRACT_VIOLATION, stage="embed", plugin_id=plugin_id, detail=msg)
            last_detail = f"HTTP {response.status_code}: {response.text[:200]}"
        if attempt < max_retries:
            base_delay = backoff_schedule[min(attempt, len(backoff_schedule) - 1)]
            scale = 1.0 if jitter is None else 0.5 + 0.5 * jitter()
            sleep(base_delay * scale)
    msg = f"{plugin_id}: {url} unavailable after {max_retries} retries (doc 12 sec 5): {last_detail}"
    raise StageError(SERVER_UNAVAILABLE, stage="embed", plugin_id=plugin_id, detail=msg)
