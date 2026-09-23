"""`FakeEmbedder` — `sdk.ports.Embedder` 대역(double). 결정적 해시 벡터를 생성하며 모델 가중치가 없다.

역할: conformance kit과 단위 테스트가 실제 임베딩 모델 없이 `embed_documents`/`embed_query`
호출부를 검증하도록 한다.
설계 근거: 2026-09-23 사용자 결정(VDI에서 모델 가중치 다운로드 금지) — 임베딩은 결정적 대역으로만
검증한다. 벡터 자체는 의미를 담지 않지만 차원(`dim`)과 L2 정규화(`normalized`)는 바이블
§5.6 `EmbeddedChunkSet` 관례를 따른다.

구성: `FakeEmbedder` — 같은 텍스트는 항상 같은 벡터를 내는 `sha256` 기반 결정적 유닛 벡터 생성기
(`embed_documents`, `embed_query`).

불변식·주의: 콘텐츠 주소화 키(`blake3_hex`)가 아니라 `hashlib.sha256`을 의도적으로 사용한다 —
이 대역은 검증용 가짜 임베딩 공간이지 바이블 §6.2 해시 키 체계의 일부가 아니다.
검증 계층: 1층(대역 자체는 여기서 검증) — `tests/unit/test_testing_doubles.py`.
DEFERRED: 실 서빙 BGE-M3(TEI/vLLM pooling) 임베더 대상 검증은 `needs_model`(모델 가중치) +
`needs_network`(서빙 호출) — `docs/12-appendix/09-deferred-verification-ledger.md`에서 추적.
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
