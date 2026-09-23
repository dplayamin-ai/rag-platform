"""TEI dense 임베더 어댑터 — `POST /embed`로 dense 전용 모델을 서빙(`premium ko-quality` 등).

역할: `sdk.ports.Embedder`를 만족하는 HTTP 어댑터. 배치·질의/문서 비대칭 프롬프트·L2 정규화·
타임아웃·재시도를 어댑터가 소유한다(ADR-0009 DR7 "어댑터 소유권").
설계 근거: 04-pipelines/12 §4.1(`POST /embed`, `--max-client-batch-size`), §4.2(`embedder.tei_dense`
"`normalize: true` 요청 + 재정규화"), §2.4(`truncate: true`), §2.5(프롬프트는 어댑터가 소유),
§5(연결 2s·배치당 120s, 3회 지터 백오프 0.5s→1s→2s, 4xx 비재시도), §8.1(dense 항상 L2 정규화).
구성: `TeiDenseEmbedder` — `embed_documents`/`embed_query`(+ `health`); `embedding_space_id`는
`adapters.embed.space_id`로 산출.
불변식: `embed_query`만 `query_prompt`를 적용한다(비대칭 모델). 프롬프트 없는 모델은
`query_prompt=None`으로 두면 문서 경로와 동일 요청이 나간다. 서버가 정규화해도 어댑터가 재정규화(멱등).
검증 계층: 1층(여기서 검증, respx 모의 HTTP) — tests/adapters/embed/test_embed_adapters.py.
실 TEI 서버 대상은 `needs_docker`로 유보한다.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

import httpx

from rag_platform.adapters.embed import (
    CONTRACT_VIOLATION,
    assert_l2_normalized,
    l2_normalize,
    post_with_retry,
    prompt_hash,
    space_id,
)
from rag_platform.sdk.stage import StageError

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

__all__ = ["TeiDenseEmbedder"]

# TEI `--max-client-batch-size` default (doc 12 §4.1); adapter chunks a larger `texts` list to this.
_DEFAULT_MAX_BATCH_ITEMS = 256


class TeiDenseEmbedder:
    """`embedder.tei_dense` plugin: HF Text Embeddings Inference `POST /embed` client.

    Implements `sdk.ports.Embedder` (`embedding_space_id`, `dim`, `normalized`, `embed_documents`,
    `embed_query`). `query_prompt`/`document_prompt` are optional `str.format(text=...)` templates
    the adapter owns (doc 12 §2.5) — the caller never sees or edits prompt strings.
    """

    def __init__(
        self,
        *,
        base_url: str,
        model_id: str,
        revision: str,
        dim: int,
        query_prompt: str | None = None,
        document_prompt: str | None = None,
        quantization: str = "none",
        connect_timeout_s: float = 2.0,
        request_timeout_s: float = 120.0,
        max_batch_items: int = _DEFAULT_MAX_BATCH_ITEMS,
        max_retries: int = 3,
        client: httpx.Client | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        """Build a TEI dense embedder bound to `base_url` (doc 12 §4.1 config table).

        Args:
            base_url: TEI server base URL, e.g. `"http://embedding-server:8080"`.
            model_id: HF repo id served behind `base_url`, e.g. `"nlpai-lab/KURE-v1"`.
            revision: HF commit SHA or tag (bible §6.1; `"latest"`/`"main"` forbidden, ADR-0009).
            dim: Model output dimension (post any MRL truncation, doc 12 §8.2).
            query_prompt: Optional query-mode instruction template with a `{text}` placeholder
                (doc 12 §2.5); `None` for symmetric models (BGE-M3, KURE-v1).
            document_prompt: Optional document-mode template; almost always `None` in practice.
            quantization: Model-side quantization vocabulary (doc 12 §8.3), part of the space id.
            connect_timeout_s: TCP connect timeout (doc 12 §5 document-path default: 2s).
            request_timeout_s: Per-request read timeout (doc 12 §5 document-path default: 120s).
            max_batch_items: Item cap per HTTP request (doc 12 §4.1 `--max-client-batch-size`).
            max_retries: Retries after the first attempt (doc 12 §5 default: 3).
            client: Injectable `httpx.Client` (tests supply one bound to a mock transport).
            sleep: Injectable retry-backoff delay function (tests pass a recorder, doc 12 §5).
        """
        self.plugin_id = "embedder.tei_dense"
        self._model_id = model_id
        self._revision = revision
        self._query_prompt = query_prompt or None
        self._document_prompt = document_prompt or None
        self._max_batch_items = max_batch_items
        self._max_retries = max_retries
        self._sleep = sleep
        prompt_hash_value = prompt_hash(document=self._document_prompt, query=self._query_prompt)
        self.embedding_space_id = space_id(
            model_id=model_id,
            revision=revision,
            dim=dim,
            normalized=True,
            prompt_hash_value=prompt_hash_value,
            quantization=quantization,
        )
        self.dim = dim
        self.normalized = True
        timeout = httpx.Timeout(
            connect_timeout_s, read=request_timeout_s, write=request_timeout_s, pool=request_timeout_s
        )
        self._client = client or httpx.Client(base_url=base_url, timeout=timeout)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed `texts` in `mode=document` (doc 12 §2.1 port table), batched to `max_batch_items`.

        Args:
            texts: Document/passage texts (already truncated by `EmbedderStageBase`, doc 12 §2.4).

        Returns:
            One L2-normalized dense vector per element of `texts`, in the same order.
        """
        if not texts:
            return []
        prepared = [self._apply_prompt(text, self._document_prompt) for text in texts]
        vectors: list[list[float]] = []
        for start in range(0, len(prepared), self._max_batch_items):
            vectors.extend(self._embed_batch(prepared[start : start + self._max_batch_items]))
        return vectors

    def embed_query(self, text: str) -> list[float]:
        """Embed `text` in `mode=query` (asymmetric instruction prompt attached if configured).

        Args:
            text: The query text (e.g. `QueryPlan.dense_query_text`, doc 12 §10).

        Returns:
            The L2-normalized dense query vector.
        """
        return self._embed_batch([self._apply_prompt(text, self._query_prompt)])[0]

    def health(self) -> bool:
        """Probe `GET /health` (doc 12 §4.1); returns `False` on any transport failure.

        Returns:
            `True` if the server responded with a non-error status, else `False`.
        """
        try:
            response = self._client.get("/health")
        except httpx.TransportError:
            return False
        return response.status_code < httpx.codes.BAD_REQUEST

    def close(self) -> None:
        """Release the underlying `httpx.Client` connection pool."""
        self._client.close()

    def _apply_prompt(self, text: str, template: str | None) -> str:
        """Return `text` with `template` applied, or `text` unchanged if `template` is `None`."""
        return text if template is None else template.format(text=text)

    def _embed_batch(self, batch: Sequence[str]) -> list[list[float]]:
        """POST one `/embed` request for `batch` and return re-normalized dense vectors."""
        response = post_with_retry(
            self._client,
            "/embed",
            json_body={"inputs": list(batch), "normalize": True, "truncate": True},
            plugin_id=self.plugin_id,
            max_retries=self._max_retries,
            sleep=self._sleep,
        )
        payload: Any = response.json()
        if not isinstance(payload, list) or len(payload) != len(batch):
            got = len(payload) if isinstance(payload, list) else type(payload).__name__
            msg = f"{self.plugin_id}: /embed returned {got} vectors for {len(batch)} inputs"
            raise StageError(CONTRACT_VIOLATION, stage="embed", plugin_id=self.plugin_id, detail=msg)
        vectors: list[list[float]] = []
        for raw_vector in payload:
            if not isinstance(raw_vector, list) or len(raw_vector) != self.dim:
                got_dim = len(raw_vector) if isinstance(raw_vector, list) else type(raw_vector).__name__
                msg = f"{self.plugin_id}: /embed vector dim {got_dim} != configured dim {self.dim}"
                raise StageError(CONTRACT_VIOLATION, stage="embed", plugin_id=self.plugin_id, detail=msg)
            normalized = l2_normalize([float(v) for v in raw_vector])
            assert_l2_normalized(normalized, plugin_id=self.plugin_id)
            vectors.append(normalized)
        return vectors
