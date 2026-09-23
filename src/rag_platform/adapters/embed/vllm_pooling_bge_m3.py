"""vLLM pooling BGE-M3 임베더 어댑터 골격 — `POST /pooling` 단일 응답에서 dense+sparse를 분리한다.

역할: `standard`/`korean-gov` 기본 임베딩(BGE-M3 3-in-1)의 `sdk.ports.Embedder` 어댑터.
`embed_documents`/`embed_query`는 dense만 반환(포트 계약)하고, 같은 응답의 sparse는 포트 밖
확장 메서드 `embed_documents_with_sparse`로 노출한다(04-pipelines/12 §2.1).
설계 근거: §4.1(`POST /pooling`, `--io-processor-plugin bge_m3_sparse_plugin`),
§4.2(`embedder.vllm_pooling_bge_m3`: "재정규화", §12.1 sparse 처리), §12.1(특수 토큰 제거·max
집계·양수 필터·오름차순 유일 `indices`·6자리 반올림), ADR-0009(3-in-1, `image_digest` 필수).
구성: `SparseBundle` — `{indices, values}` + `common_types.SparseLearned` 변환 `to_contract_dict`;
`VllmPoolingBgeM3Embedder` — `embed_documents`/`embed_query`/`embed_documents_with_sparse`.
불변식: 응답 스키마는 **제안**(§4.1 "vLLM 릴리스마다 변동 가능성", 확인 필요 as of 2026-09) — 실
서버 카세트 검증 전까지 골격이다. 특수 토큰 id(`{0,1,2,3}` XLM-R 기본)는 생성자 인자로 재정의 가능.
검증 계층: 1층(여기서 검증, 고정 픽스처) — tests/adapters/embed/test_embed_adapters.py.
# DEFERRED: 실 vLLM 0.29 서버 응답 스키마 검증과 FlagEmbedding `lexical_weights` 골든 대조(§12.1
# 규칙 6)는 `needs_docker`+`needs_gpu` — docs/12-appendix/09-deferred-verification-ledger.md.
"""

from __future__ import annotations

import time
from collections.abc import Mapping
from dataclasses import dataclass
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

__all__ = ["SparseBundle", "VllmPoolingBgeM3Embedder"]

# XLM-R tokenizer special token ids (doc 12 §12.1 rule 1; "확인 필요 as of 2026-09" — not verified
# against a real BAAI/bge-m3 tokenizer.json here, model downloads are forbidden on the VDI).
_DEFAULT_SPECIAL_TOKEN_IDS: frozenset[int] = frozenset({0, 1, 2, 3})
_SPARSE_VALUE_NDIGITS = 6  # doc 12 §12.1 rule 4: "float32 반올림 6자리"


@dataclass(frozen=True)
class SparseBundle:
    """One chunk's `sparse_learned` output: ascending-unique `indices`, positive `values`."""

    indices: list[int]
    values: list[float]

    def to_contract_dict(self, vocab_id: str) -> dict[str, Any]:
        """Render the `common_types.SparseLearned` shape (bible §5.4 `VectorBundle.sparse_learned`).

        Args:
            vocab_id: The sparse vocabulary id (doc 12 §12.2, e.g. `"xlm-roberta-250k"`).

        Returns:
            A mapping constructible as `common_types.SparseLearned(**mapping)`.
        """
        return {"name": "sparse_learned", "vocab_id": vocab_id, "indices": self.indices, "values": self.values}


@dataclass(frozen=True)
class _PoolingResult:
    """One `/pooling` call's parsed output: parallel dense vectors and sparse bundles."""

    dense: list[list[float]]
    sparse: list[SparseBundle]


class VllmPoolingBgeM3Embedder:
    """`embedder.vllm_pooling_bge_m3` plugin: vLLM `--runner pooling` `POST /pooling` client.

    Implements `sdk.ports.Embedder` for the `dense` channel; `sparse_learned` is an adapter-specific
    extension (`embed_documents_with_sparse`) since the port only covers dense (doc 12 §2.1).
    """

    def __init__(
        self,
        *,
        base_url: str,
        model_id: str = "BAAI/bge-m3",
        revision: str,
        dim: int = 1024,
        vocab_id: str = "xlm-roberta-250k",
        sparse_vocab_size: int = 250_002,
        quantization: str = "none",
        special_token_ids: frozenset[int] = _DEFAULT_SPECIAL_TOKEN_IDS,
        connect_timeout_s: float = 2.0,
        request_timeout_s: float = 120.0,
        max_retries: int = 3,
        client: httpx.Client | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        """Build a vLLM pooling BGE-M3 embedder bound to `base_url` (doc 12 §4.1 config table).

        Args:
            base_url: vLLM server base URL, e.g. `"http://embedding-server:8000"`.
            model_id: HF repo id, default `"BAAI/bge-m3"` (the only model this adapter targets).
            revision: HF commit SHA or tag (bible §6.1; `"latest"`/`"main"` forbidden, ADR-0009).
            dim: Dense output dimension (doc 12 §3: BGE-M3 dense is 1024, no MRL truncation).
            vocab_id: Sparse vocabulary id (doc 12 §12.2, default BGE-M3's `xlm-roberta-250k`).
            sparse_vocab_size: Sparse channel's `dim` input to the space id (doc 12 §12.2 "어휘
                크기"); default is XLM-R's reported `vocab_size` ("확인 필요 as of 2026-09").
            quantization: Model-side quantization vocabulary (doc 12 §8.3), part of both space ids.
            special_token_ids: Token ids stripped from the sparse response (doc 12 §12.1 rule 1).
            connect_timeout_s: TCP connect timeout (doc 12 §5 document-path default: 2s).
            request_timeout_s: Per-request read timeout (doc 12 §5 document-path default: 120s).
            max_retries: Retries after the first attempt (doc 12 §5 default: 3).
            client: Injectable `httpx.Client` (tests supply one bound to a mock transport).
            sleep: Injectable retry-backoff delay function (tests pass a recorder, doc 12 §5).
        """
        self.plugin_id = "embedder.vllm_pooling_bge_m3"
        self.vocab_id = vocab_id
        self._special_token_ids = special_token_ids
        self._max_retries = max_retries
        self._sleep = sleep
        prompt_hash_value = prompt_hash()  # BGE-M3 has no prompts (doc 12 §2.5 "프롬프트 없음")
        self.embedding_space_id = space_id(
            model_id=model_id,
            revision=revision,
            dim=dim,
            normalized=True,
            prompt_hash_value=prompt_hash_value,
            quantization=quantization,
        )
        self.sparse_embedding_space_id = space_id(
            model_id=model_id,
            revision=revision,
            dim=sparse_vocab_size,
            normalized=False,  # doc 12 §8.1 applies to dense only; sparse weights are not unit-norm
            prompt_hash_value=prompt_hash_value,
            quantization=quantization,
            vocab_id=vocab_id,
        )
        self.dim = dim
        self.normalized = True
        timeout = httpx.Timeout(
            connect_timeout_s, read=request_timeout_s, write=request_timeout_s, pool=request_timeout_s
        )
        self._client = client or httpx.Client(base_url=base_url, timeout=timeout)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Return dense vectors only (`sdk.ports.Embedder`); use `embed_documents_with_sparse` for both.

        Args:
            texts: Document/passage texts (already truncated by `EmbedderStageBase`, doc 12 §2.4).

        Returns:
            One L2-normalized dense vector per element of `texts`, in the same order.
        """
        if not texts:
            return []
        return self._pool(texts).dense

    def embed_query(self, text: str) -> list[float]:
        """Return the dense query vector (BGE-M3 shares the document path, doc 12 §2.1 port table).

        Args:
            text: The query text (e.g. `QueryPlan.dense_query_text`, doc 12 §10).

        Returns:
            The L2-normalized dense query vector.
        """
        return self._pool([text]).dense[0]

    def embed_documents_with_sparse(self, texts: list[str]) -> list[SparseBundle]:
        """Return this single `/pooling` pass's `sparse_learned` bundles (doc 12 §12.1).

        Args:
            texts: Document/passage texts, same order as a paired `embed_documents(texts)` call.

        Returns:
            One `SparseBundle` per element of `texts`, in the same order.
        """
        if not texts:
            return []
        return self._pool(texts).sparse

    def close(self) -> None:
        """Release the underlying `httpx.Client` connection pool."""
        self._client.close()

    def _pool(self, texts: Sequence[str]) -> _PoolingResult:
        """POST one `/pooling` request and parse dense+sparse for every input text."""
        response = post_with_retry(
            self._client,
            "/pooling",
            json_body={"input": list(texts)},
            plugin_id=self.plugin_id,
            max_retries=self._max_retries,
            sleep=self._sleep,
        )
        payload: Any = response.json()
        if not isinstance(payload, list) or len(payload) != len(texts):
            got = len(payload) if isinstance(payload, list) else type(payload).__name__
            msg = f"{self.plugin_id}: /pooling returned {got} entries for {len(texts)} inputs"
            raise StageError(CONTRACT_VIOLATION, stage="embed", plugin_id=self.plugin_id, detail=msg)
        dense_vectors: list[list[float]] = []
        sparse_bundles: list[SparseBundle] = []
        for entry in payload:
            dense_vectors.append(self._parse_dense(entry))
            sparse_bundles.append(self._parse_sparse(entry))
        return _PoolingResult(dense=dense_vectors, sparse=sparse_bundles)

    def _parse_dense(self, entry: Mapping[str, Any]) -> list[float]:
        """Extract and re-normalize one `/pooling` entry's `dense` field (doc 12 §4.2 "재정규화")."""
        raw_dense = entry.get("dense")
        if not isinstance(raw_dense, list) or len(raw_dense) != self.dim:
            got_dim = len(raw_dense) if isinstance(raw_dense, list) else type(raw_dense).__name__
            msg = f"{self.plugin_id}: /pooling dense dim {got_dim} != configured dim {self.dim}"
            raise StageError(CONTRACT_VIOLATION, stage="embed", plugin_id=self.plugin_id, detail=msg)
        normalized = l2_normalize([float(v) for v in raw_dense])
        assert_l2_normalized(normalized, plugin_id=self.plugin_id)
        return normalized

    def _parse_sparse(self, entry: Mapping[str, Any]) -> SparseBundle:
        """Extract one `/pooling` entry's `sparse` field into a `SparseBundle` (doc 12 §12.1)."""
        raw_sparse = entry.get("sparse") or {}
        if not isinstance(raw_sparse, Mapping):
            msg = f"{self.plugin_id}: /pooling sparse field must be an object, got {type(raw_sparse).__name__}"
            raise StageError(CONTRACT_VIOLATION, stage="embed", plugin_id=self.plugin_id, detail=msg)
        aggregated: dict[int, float] = {}
        for token_id_raw, weight_raw in raw_sparse.items():
            token_id = int(token_id_raw)
            if token_id in self._special_token_ids:  # rule 1: strip special tokens
                continue
            weight = float(weight_raw)
            if weight <= 0.0:  # rule 3: ReLU output, only exactly-zero (or negative) is dropped
                continue
            previous = aggregated.get(token_id)
            aggregated[token_id] = weight if previous is None else max(previous, weight)  # rule 2: max
        ordered_ids = sorted(aggregated)  # rule 4: ascending, unique (dict keys already unique)
        values = [round(aggregated[token_id], _SPARSE_VALUE_NDIGITS) for token_id in ordered_ids]
        return SparseBundle(indices=ordered_ids, values=values)
