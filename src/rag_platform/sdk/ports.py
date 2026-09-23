"""`StageContext`와 정합성 키트 페이크가 참조하는 소규모 역할 포트(role port) 프로토콜 모음.

역할: `TokenCounter`/`KoreanAnalyzer`(바이블 §4.1 `ctx` 멤버)와, `embedder`/`index_backend` 확장
지점을 위한 `Embedder`/`IndexBackend`(ADR-0032) 프로토콜을 정의한다.
설계 근거: 바이블 §4.1(`ctx.token_counter`/`ctx.analyzer`), §12(`sdk/`가 `TokenCounter` 소유);
02-architecture/02-component-architecture.md §2.3(`RuntimeServices`/`ArtifactStore` 이웃).
구성: `TokenCounter.count` — 토크나이저 기준 개수; `KoreanAnalyzer.normalize`/`tokenize` — Kiwi/
mecab-ko 정규화·형태소 분석; `Embedder.embed_documents`/`embed_query` — 밀집 벡터만 반환;
`IndexBackend.upsert`/`search_dense`/`search_lexical` — 정합성 페이크가 필요한 최소 표면.
불변식: `Embedder`/`IndexBackend`는 바이블 §4.1 `StageContext` 표면이 아니다 — `storage/`가 어댑터
모양 포트를 import할 수 없으므로 `plugins`와 `testing`이 공유하는 의존성 없는 자리에 둔다(바이블 §12).
검증 계층: 1층(여기서 검증) — tests/unit/test_sdk_ports.py.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class TokenCounter(Protocol):
    """Bible §4.1 `ctx.token_counter`: a single tokenizer-bound counting interface (O-09)."""

    @property
    def tokenizer_id(self) -> str:
        """Identify the tokenizer this counter is bound to (read-only: frozen-dataclass-safe)."""
        ...

    def count(self, text: str) -> int:
        """Return the token count of `text` under this tokenizer."""
        ...


@runtime_checkable
class KoreanAnalyzer(Protocol):
    """Bible §4.1 `ctx.analyzer`: Kiwi or space-only mecab-ko (ADR-0021)."""

    analyzer_id: str

    def normalize(self, text: str) -> str:
        """Return a spacing/typo-corrected form of `text` (engine-dependent)."""
        ...

    def tokenize(self, text: str) -> tuple[str, ...]:
        """Return the morpheme/keyword tokens extracted from `text`."""
        ...


@runtime_checkable
class Embedder(Protocol):
    """`embedder` extension point role port (bible §4.2 `embed` row).

    ``embed_documents``/``embed_query`` return dense vectors only; sparse and late-interaction
    spaces are additional, adapter-specific methods out of scope for the conformance fake.
    """

    embedding_space_id: str
    dim: int
    normalized: bool

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Return one dense vector per element of `texts` (document/passage embedding)."""
        ...

    def embed_query(self, text: str) -> list[float]:
        """Return the dense vector for a query string."""
        ...


@runtime_checkable
class IndexBackend(Protocol):
    """`index_backend` extension point role port (bible §4.2 `index` row, minimal read/write slice).

    Full backends (Qdrant/OpenSearch adapters) implement far more (payload filters, aliasing,
    generation flips, §11.4); the conformance fake only needs enough surface to exercise
    ``retrieve``/``fuse`` unit tests: ``upsert``, ``search_dense``, ``search_lexical``.
    """

    def upsert(self, records: list[dict[str, object]]) -> None:
        """Insert or replace `records` (each a payload mapping keyed at least by `id`)."""
        ...

    def search_dense(self, tenant_id: str, vector: list[float], top_k: int) -> list[tuple[str, float]]:
        """Return up to `top_k` `(record_id, score)` pairs for `tenant_id`, ranked by dense similarity."""
        ...

    def search_lexical(self, tenant_id: str, query: str, top_k: int) -> list[tuple[str, float]]:
        """Return up to `top_k` `(record_id, score)` pairs for `tenant_id`, ranked by lexical match."""
        ...
