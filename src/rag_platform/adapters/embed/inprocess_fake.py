"""인프로세스 페이크 임베더 어댑터 — `testing.doubles.FakeEmbedder`를 `embedder.inprocess_fake` 플러그인으로 감싼다.

역할: 모델 가중치 없이 결정적 해시 벡터를 내는 개발·CI 전용 임베더 플러그인. 실제 서빙 스택
(vLLM·TEI) 없이도 `Embedder` 포트·`PluginRegistry` 등록 경로를 exercise할 수 있게 한다.
설계 근거: 사용자 결정(2026-09-23, VDI 모델 가중치 다운로드 금지 — `testing/doubles/fake_embedder.py`
헤더), 04-pipelines/12 §2.1(`Embedder` 포트 표면), 바이블 §5.6(`PluginMeta` 필드), §6.1(`plugin_id`
= `{extension_point}.{implementation}`); `plugins/registry.py`(`PluginRegistry.register`가 기대하는
`(meta: Mapping, factory)` 모양).
구성: `InprocessFakeEmbedder` — `FakeEmbedder`를 감싸 `plugin_id`를 부여하는 얇은 래퍼; `PLUGIN_META`
— `PluginRegistry.register`/entry-point 탐색이 읽는 매핑; `build(config, services)` — 레지스트리
팩토리 시그니처(바이블 §5.6).
불변식: `in_process`만 지원하고 `model_ids=None`(가중치 없음)이다. 프로덕션 프로파일(`standard`/
`premium`/`korean-gov`)에는 바인딩하지 않는다 — 테스트·`lite` 개발 하네스 전용(FakeEmbedder 자체가
"검증용 가짜 임베딩 공간"이며 §6.2 해시 키 체계의 일부가 아니다).
검증 계층: 1층(여기서 검증) — tests/adapters/embed/test_embed_adapters.py.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from rag_platform.testing.doubles.fake_embedder import FakeEmbedder

if TYPE_CHECKING:
    from collections.abc import Mapping

__all__ = ["PLUGIN_META", "InprocessFakeEmbedder", "build"]


class InprocessFakeEmbedder:
    """`embedder.inprocess_fake` plugin surface over `testing.doubles.FakeEmbedder`.

    Adds only the `plugin_id` attribute the `Embedder` port's neighbors (`PluginMeta.plugin_id`,
    `Producer.plugin_id`) expect; `embedding_space_id`/`dim`/`normalized`/`embed_documents`/
    `embed_query` are the underlying `FakeEmbedder`'s, unchanged.
    """

    plugin_id = "embedder.inprocess_fake"

    def __init__(
        self,
        *,
        embedding_space_id: str = "fake:sha256-hash",
        dim: int = 16,
        normalized: bool = True,
    ) -> None:
        """Build the fake embedder (see `FakeEmbedder` for the deterministic hash-vector rule).

        Args:
            embedding_space_id: The fake space label reported by `embedding_space_id`.
            dim: Output vector dimension.
            normalized: Whether returned vectors are L2-normalized.
        """
        self._fake = FakeEmbedder(embedding_space_id=embedding_space_id, dim=dim, normalized=normalized)
        self.embedding_space_id = self._fake.embedding_space_id
        self.dim = self._fake.dim
        self.normalized = self._fake.normalized

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Delegate to `FakeEmbedder.embed_documents` (deterministic per-text hash vectors)."""
        return self._fake.embed_documents(texts)

    def embed_query(self, text: str) -> list[float]:
        """Delegate to `FakeEmbedder.embed_query` (deterministic hash vector)."""
        return self._fake.embed_query(text)


# Bible §5.6 `PluginMeta` field set, mirroring the `plugins/registry.py` manual-registration shape
# (`tests/unit/test_plugins_registry.py` `_META`). `capabilities.extra` follows doc 12 §2.3's
# proposed `EmbedderCapabilities` subset.
PLUGIN_META: dict[str, Any] = {
    "plugin_id": "embedder.inprocess_fake",
    "extension_point": "embedder",
    "role": None,
    "version": "0.1.0",
    "license": "Apache-2.0",
    "license_grade": "A",
    "territory": [],
    "linkage": "pure_python",
    "isolation_supported": ["in_process"],
    "model_license_ack_required": False,
    "sidecar_image": None,
    "contracts_compat": ">=1.0,<2.0",
    "capabilities": {
        "isolation_modes": ["in_process"],
        "supports_resumable": False,
        "contracts_compat": ">=1.0,<2.0",
        "input_formats": [],
        "requires_gpu": False,
        "extra": {
            "vector_names": ["dense"],
            "max_input_tokens": 8192,
            "tokenizer_id": "hf:BAAI/bge-m3",
            "dense_dim": 16,
            "mrl_dims": [],
            "sparse_vocab_id": None,
            "pooling": "cls",
            "requires_instruction": False,
            "supports_query_mode_split": False,
            "quantization": "none",
            "determinism": "model_pinned",
        },
    },
}


def build(config: Mapping[str, Any], services: Any = None) -> InprocessFakeEmbedder:  # noqa: ARG001 - PluginRegistry factory signature; `services` unused by an in-process fake
    """`PluginRegistry` factory: build an `InprocessFakeEmbedder` from `config` (bible §5.6).

    Args:
        config: Plugin configuration mapping; recognizes `embedding_space_id`, `dim`, `normalized`.
        services: Unused — an in-process fake needs no `RuntimeServices` (registry call shape).

    Returns:
        A configured `InprocessFakeEmbedder`.
    """
    return InprocessFakeEmbedder(
        embedding_space_id=config.get("embedding_space_id", "fake:sha256-hash"),
        dim=config.get("dim", 16),
        normalized=config.get("normalized", True),
    )
