"""Small role-port protocols referenced by `StageContext` and the conformance kit fakes.

Canon: design bible §4.1 (`ctx.token_counter`, `ctx.analyzer`), §12 (`sdk/` owns `TokenCounter`);
02-architecture/02-component-architecture.md §2.3 (`RuntimeServices`, `ArtifactStore` neighbours).
`Embedder` and `IndexBackend` are not part of the bible §4.1 `StageContext` surface — they are the
role ports that `plugins.registry.build_port` returns for the `embedder` and `index_backend`
extension points (ADR-0032). They are declared here, not in `storage/`, because `storage/` may not
import adapter-shaped ports and both `plugins` and `testing` need a shared, dependency-free home for
them (bible §12 dependency direction: `sdk` sits below `plugins`, `storage`, and `testing`).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class TokenCounter(Protocol):
    """Bible §4.1 `ctx.token_counter`: a single tokenizer-bound counting interface (O-09)."""

    tokenizer_id: str

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
