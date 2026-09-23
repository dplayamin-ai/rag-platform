"""`adapters.embed` 3종 어댑터 단위 테스트 — respx 모의 HTTP로 파싱·정규화·오류 분류·계약 정합을 검증한다.

무엇을 검증하는지: `tei_dense.TeiDenseEmbedder`(배치·질의/문서 비대칭·L2 재정규화·재시도·오류 분류),
`vllm_pooling_bge_m3.VllmPoolingBgeM3Embedder`(dense+sparse 단일 응답 분리, §12.1 특수 토큰 제거·
max 집계·양수 필터·정렬), `inprocess_fake.InprocessFakeEmbedder`(`FakeEmbedder` 위임·`PluginMeta`
등록). 실 서버 대상 검증은 `needs_docker`/`needs_model`로 유보한다(모듈 헤더 DEFERRED 참조).
픽스처 출처: 04-pipelines/12 §4.1(엔드포인트 모양)·§12.1(sparse 집계 규칙, 고정 예시 없음 — 이
파일이 표 규칙 1~4를 최소 벡터로 구성), 03-contracts/07(`embedding_space_ids`/`sparse_learned`).
설계 근거: 04-pipelines/12 §2.1·§4.1·§4.2·§5·§8.1·§12.1, ADR-0009. `respx`로 실제 TCP 연결 없이
`httpx.Client` 트래픽을 가로챈다.
불변식: 재시도 테스트는 `sleep=` 주입으로 실제 대기를 만들지 않는다.
검증 계층: 1층. tests/adapters/ 하위이므로 conftest.py가 `component` 마커를 붙인다.
"""

from __future__ import annotations

from typing import Any, ClassVar

import httpx
import pytest
import respx

from rag_platform.adapters.embed.inprocess_fake import PLUGIN_META, InprocessFakeEmbedder, build
from rag_platform.adapters.embed.tei_dense import TeiDenseEmbedder
from rag_platform.adapters.embed.vllm_pooling_bge_m3 import SparseBundle, VllmPoolingBgeM3Embedder
from rag_platform.contracts.common_types import EmbeddingSpaceIds, Hex64, SparseLearned
from rag_platform.plugins.registry import PluginRegistry, validate_plugin_meta
from rag_platform.sdk.ports import Embedder
from rag_platform.sdk.stage import StageError
from rag_platform.testing.conformance.kits import EmbedderConformance

_BASE_URL = "http://tei.test"
_VLLM_BASE_URL = "http://vllm.test"


def _tei(**overrides: object) -> TeiDenseEmbedder:
    kwargs: dict[str, object] = {
        "base_url": _BASE_URL,
        "model_id": "nlpai-lab/KURE-v1",
        "revision": "abc123",
        "dim": 4,
    }
    kwargs.update(overrides)
    return TeiDenseEmbedder(**kwargs)  # type: ignore[arg-type]


def _vllm(**overrides: object) -> VllmPoolingBgeM3Embedder:
    kwargs: dict[str, object] = {
        "base_url": _VLLM_BASE_URL,
        "revision": "def456",
        "dim": 4,
    }
    kwargs.update(overrides)
    return VllmPoolingBgeM3Embedder(**kwargs)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------------------------
# tei_dense
# ---------------------------------------------------------------------------------------------


def test_tei_dense_satisfies_embedder_protocol() -> None:
    assert isinstance(_tei(), Embedder)


@respx.mock
def test_tei_dense_embed_documents_renormalizes_and_batches() -> None:
    route = respx.post(f"{_BASE_URL}/embed").mock(
        side_effect=[
            httpx.Response(200, json=[[3.0, 0.0, 0.0, 0.0]]),
            httpx.Response(200, json=[[0.0, 4.0, 0.0, 0.0]]),
        ]
    )
    embedder = _tei(max_batch_items=1)  # forces two /embed requests for two texts, one item each
    vectors = embedder.embed_documents(["a", "b"])
    assert route.call_count == 2  # batch size 1 over 2 inputs
    assert vectors == [[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0]]
    for vector in vectors:
        norm = sum(v * v for v in vector) ** 0.5
        assert abs(norm - 1.0) < 1e-4


@respx.mock
def test_tei_dense_embed_query_applies_asymmetric_prompt() -> None:
    captured: dict[str, object] = {}

    def _responder(request: httpx.Request) -> httpx.Response:
        captured["inputs"] = request.content
        return httpx.Response(200, json=[[1.0, 0.0, 0.0, 0.0]])

    respx.post(f"{_BASE_URL}/embed").mock(side_effect=_responder)
    embedder = _tei(query_prompt="Instruct: search\nQuery: {text}", document_prompt=None)
    embedder.embed_query("한국 정보공개")
    assert b"Instruct: search" in captured["inputs"]  # type: ignore[operator]
    assert b"\\ud55c" not in captured["inputs"]  # type: ignore[operator] - sanity: not double-escaped


@respx.mock
def test_tei_dense_retries_retryable_status_then_succeeds() -> None:
    route = respx.post(f"{_BASE_URL}/embed").mock(
        side_effect=[httpx.Response(503), httpx.Response(200, json=[[1.0, 0.0, 0.0, 0.0]])]
    )
    sleeps: list[float] = []
    embedder = _tei(sleep=sleeps.append)
    vectors = embedder.embed_documents(["a"])
    assert route.call_count == 2  # one retry
    assert vectors == [[1.0, 0.0, 0.0, 0.0]]
    assert sleeps == [0.5]  # first backoff step, no jitter injected


@respx.mock
def test_tei_dense_exhausts_retries_and_raises_server_unavailable() -> None:
    respx.post(f"{_BASE_URL}/embed").mock(return_value=httpx.Response(503))
    sleeps: list[float] = []
    embedder = _tei(sleep=sleeps.append)
    with pytest.raises(StageError) as exc_info:
        embedder.embed_documents(["a"])
    assert exc_info.value.code == "embed.server_unavailable"
    assert exc_info.value.retryable is True
    assert sleeps == [0.5, 1.0, 2.0]  # doc 12 sec 5: 3 retries, no jitter injected


@respx.mock
def test_tei_dense_non_retryable_status_fails_immediately() -> None:
    route = respx.post(f"{_BASE_URL}/embed").mock(return_value=httpx.Response(413, text="too large"))
    embedder = _tei()
    with pytest.raises(StageError) as exc_info:
        embedder.embed_documents(["a"])
    assert exc_info.value.code == "contract.violation"
    assert route.call_count == 1  # no retry on 413


@respx.mock
def test_tei_dense_dim_mismatch_is_contract_violation() -> None:
    respx.post(f"{_BASE_URL}/embed").mock(return_value=httpx.Response(200, json=[[1.0, 0.0]]))  # dim=2, configured 4
    embedder = _tei()
    with pytest.raises(StageError) as exc_info:
        embedder.embed_documents(["a"])
    assert exc_info.value.code == "contract.violation"


def test_tei_dense_connect_and_request_timeouts_are_configured() -> None:
    embedder = _tei(connect_timeout_s=2.0, request_timeout_s=120.0)
    timeout = embedder._client.timeout  # white-box config check
    assert timeout.connect == 2.0
    assert timeout.read == 120.0


def test_tei_dense_embedding_space_id_is_hex64() -> None:
    embedder = _tei()
    Hex64(embedder.embedding_space_id)  # must not raise
    assert embedder.normalized is True
    assert embedder.dim == 4


def test_tei_dense_different_prompts_yield_different_spaces() -> None:
    plain = _tei()
    prompted = _tei(query_prompt="Instruct: x\nQuery: {text}")
    assert plain.embedding_space_id != prompted.embedding_space_id  # doc 12 sec 2.5


# ---------------------------------------------------------------------------------------------
# vllm_pooling_bge_m3
# ---------------------------------------------------------------------------------------------


def test_vllm_pooling_satisfies_embedder_protocol() -> None:
    assert isinstance(_vllm(), Embedder)


@respx.mock
def test_vllm_pooling_parses_dense_and_sparse_from_single_response() -> None:
    respx.post(f"{_VLLM_BASE_URL}/pooling").mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "dense": [3.0, 0.0, 0.0, 0.0],
                    # rule 1: token 0 (special) dropped; rule 2: token 5 max-aggregated defensively
                    # (already unique here); rule 3: token 9 (<=0) dropped; rule 4: sorted ascending.
                    "sparse": {"0": 9.9, "9": 0.0, "42": 0.51, "5": 1.2345678},
                }
            ],
        )
    )
    embedder = _vllm()
    dense = embedder.embed_documents(["doc text"])
    assert dense == [[1.0, 0.0, 0.0, 0.0]]
    sparse = embedder.embed_documents_with_sparse(["doc text"])
    assert sparse == [SparseBundle(indices=[5, 42], values=[1.234568, 0.51])]


@respx.mock
def test_vllm_pooling_sparse_bundle_matches_sparse_learned_contract() -> None:
    respx.post(f"{_VLLM_BASE_URL}/pooling").mock(
        return_value=httpx.Response(200, json=[{"dense": [1.0, 0.0, 0.0, 0.0], "sparse": {"7": 0.25}}])
    )
    embedder = _vllm()
    bundle = embedder.embed_documents_with_sparse(["x"])[0]
    validated = SparseLearned.model_validate(bundle.to_contract_dict(embedder.vocab_id))
    assert validated.vocab_id == "xlm-roberta-250k"
    assert [indice.root for indice in validated.indices] == [7]
    assert validated.values == [0.25]


@respx.mock
def test_vllm_pooling_embed_query_uses_same_pooling_endpoint() -> None:
    respx.post(f"{_VLLM_BASE_URL}/pooling").mock(
        return_value=httpx.Response(200, json=[{"dense": [0.0, 5.0, 0.0, 0.0], "sparse": {}}])
    )
    embedder = _vllm()
    assert embedder.embed_query("query text") == [0.0, 1.0, 0.0, 0.0]


@respx.mock
def test_vllm_pooling_wrong_entry_count_is_contract_violation() -> None:
    respx.post(f"{_VLLM_BASE_URL}/pooling").mock(return_value=httpx.Response(200, json=[]))
    embedder = _vllm()
    with pytest.raises(StageError) as exc_info:
        embedder.embed_documents(["a", "b"])
    assert exc_info.value.code == "contract.violation"


def test_vllm_pooling_dense_and_sparse_spaces_are_distinct_hex64() -> None:
    embedder = _vllm()
    Hex64(embedder.embedding_space_id)
    Hex64(embedder.sparse_embedding_space_id)
    assert embedder.embedding_space_id != embedder.sparse_embedding_space_id


def test_vllm_pooling_space_ids_build_a_valid_embedding_space_ids_contract() -> None:
    embedder = _vllm()
    validated = EmbeddingSpaceIds.model_validate(
        {"dense": embedder.embedding_space_id, "sparse_learned": embedder.sparse_embedding_space_id}
    )
    assert validated.root.dense.root == embedder.embedding_space_id
    assert validated.root.sparse_learned.root == embedder.sparse_embedding_space_id


# ---------------------------------------------------------------------------------------------
# inprocess_fake
# ---------------------------------------------------------------------------------------------


def test_inprocess_fake_satisfies_embedder_protocol() -> None:
    assert isinstance(InprocessFakeEmbedder(), Embedder)


def test_inprocess_fake_delegates_deterministically() -> None:
    embedder = InprocessFakeEmbedder(dim=8)
    first = embedder.embed_documents(["같은 텍스트"])
    second = embedder.embed_documents(["같은 텍스트"])
    assert first == second
    assert embedder.embed_query("같은 텍스트") == first[0]


def test_inprocess_fake_plugin_meta_is_schema_valid() -> None:
    validate_plugin_meta(PLUGIN_META)  # must not raise


def test_inprocess_fake_registers_and_builds_through_plugin_registry() -> None:
    registry = PluginRegistry()
    registry.register(PLUGIN_META, build)
    built = registry.build_port("embedder.inprocess_fake", {"dim": 8}, services=None)
    assert isinstance(built, InprocessFakeEmbedder)
    assert built.dim == 8


class TestInprocessFakeEmbedderConformance(EmbedderConformance):
    """`testing.conformance.kits.EmbedderConformance` against the `embedder.inprocess_fake` wrapper.

    Same base class `tests/unit/conformance/test_embedder_conformance.py` runs against the bare
    `FakeEmbedder`; this confirms the `InprocessFakeEmbedder`/`PLUGIN_META` plugin surface built on
    top of it (plugin_id, PluginMeta schema, embed.* StageError catalog) still conforms.
    """

    plugin_meta: ClassVar[dict[str, Any]] = PLUGIN_META

    def build_embedder(self) -> InprocessFakeEmbedder:
        """Return a fresh `InprocessFakeEmbedder` (dim=16, normalized=True defaults)."""
        return InprocessFakeEmbedder()
