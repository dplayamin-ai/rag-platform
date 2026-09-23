"""`FakeEmbedder`: `sdk.ports.Embedder` double, deterministic hash vectors, no model weights.

Canon: 2026-09-23 user decision (no model downloads on the VDI) — embedding is verified with a
deterministic fake; dimension and L2-normalization follow bible §5.6 `EmbeddedChunkSet` convention
(`dim`, `normalized`) even though the vector itself carries no semantic content.

# DEFERRED: verify against a real served BGE-M3 (TEI/vLLM pooling) embedder — `needs_model`
# (model weights) and `needs_network` (serving call). Track in
# `docs/12-appendix/09-deferred-verification-ledger.md`.
"""

from __future__ import annotations

import hashlib
import math

__all__ = ["FakeEmbedder"]


class FakeEmbedder:
    """Deterministic, content-derived unit vectors: same text -> same vector, always.

    Not `hashlib`-`blake3`: this is a conformance double, not a content-addressing key, so the
    stdlib `hashlib.sha256` is deliberate (bible §6.2's `H`/`blake3_hex` are for content-addressed
    keys, not for a fake embedding space).
    """

    def __init__(self, *, embedding_space_id: str = "fake:sha256-hash", dim: int = 16, normalized: bool = True) -> None:
        """Build a fake embedder producing `dim`-dimensional vectors, unit-normalized by default."""
        if dim < 1:
            msg = f"dim must be >= 1, got {dim}"
            raise ValueError(msg)
        self.embedding_space_id = embedding_space_id
        self.dim = dim
        self.normalized = normalized

    def _vector(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        raw = [(digest[i % len(digest)] / 255.0) * 2.0 - 1.0 for i in range(self.dim)]
        if not self.normalized:
            return raw
        norm = math.sqrt(sum(v * v for v in raw)) or 1.0
        return [v / norm for v in raw]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Return one deterministic vector per element of `texts`."""
        return [self._vector(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        """Return the deterministic vector for a query string."""
        return self._vector(text)
