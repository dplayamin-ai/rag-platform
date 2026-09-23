"""`StageContext`와 정합성 키트 페이크가 참조하는 소규모 역할 포트(role port) 프로토콜 모음.

역할: `TokenCounter`/`KoreanAnalyzer`(바이블 §4.1 `ctx` 멤버)와, `embedder`/`index_backend` 확장
지점을 위한 `Embedder`/`IndexBackend`(ADR-0032) 프로토콜을, 그리고 `postprocess.parent_expand`가
쓰는 `ChunkTextStore`(바이블 §13.2)를 정의한다.
설계 근거: 바이블 §4.1(`ctx.token_counter`/`ctx.analyzer`), §12(`sdk/`가 `TokenCounter` 소유), §13.2
(부모 텍스트 번들 캐시 포트); 02-architecture/02-component-architecture.md §2.3(`RuntimeServices`/
`ArtifactStore` 이웃).
구성: `TokenCounter.count` — 토크나이저 기준 개수; `KoreanAnalyzer.normalize`/`tokenize` — Kiwi/
mecab-ko 정규화·형태소 분석; `Embedder.embed_documents`/`embed_query` — 밀집 벡터만 반환;
`IndexBackend.upsert`/`search_dense`/`search_lexical` — 정합성 페이크가 필요한 최소 표면;
`ChunkTextStore.get_many`/`ParentEntry`/`ParentTextMiss` — §13.2 부모 텍스트 번들 조회 포트(F4 배치
검증으로 `retrieval/postprocess/parent_expand.py`의 로컬 Protocol에서 승격 — `retrieval`은 이 포트를
직접 구현하는 Valkey/오브젝트 스토리지 어댑터를 import할 수 없어 여기 둔다, 바이블 §12).
불변식: `Embedder`/`IndexBackend`는 바이블 §4.1 `StageContext` 표면이 아니다 — `storage/`가 어댑터
모양 포트를 import할 수 없으므로 `plugins`와 `testing`이 공유하는 의존성 없는 자리에 둔다(바이블 §12).
실 Valkey/오브젝트 스토리지 구현 배선은 이 승격 범위 밖이다(open_issues — 어댑터·조립 지점 WP 필요).
검증 계층: 1층(여기서 검증) — tests/unit/test_sdk_ports.py, tests/retrieval/test_postprocess_pack.py.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from rag_platform.contracts.common_types import BlockRef, BlockSource, SecurityContext, SentenceSpan2


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


class ParentTextMiss(Exception):  # noqa: N818 - 04-pipelines/17 §2.5가 이 정확한 이름으로 제안한 헬퍼 예외
    """`ChunkTextStore.get_many`가 던지는 조회 실패 — 셸의 `postprocess.parent_text_miss` 폴백."""


@dataclass(frozen=True)
class ParentEntry:
    """바이블 §13.2 부모 텍스트 번들 값 + `n_children`(04-pipelines/17 §2.5 제안 필드, 정본 미등재)."""

    text: str
    heading_path: list[str] | None
    numbering_path: list[str] | None
    token_counts: Mapping[str, int]
    block_refs: list[BlockRef] | None
    sentence_spans: list[SentenceSpan2] | None
    text_source: BlockSource | None
    ocr_confidence_min: float | None
    page_start: int | None
    page_end: int | None
    n_children: int | None = None


@runtime_checkable
class ChunkTextStore(Protocol):
    """바이블 §13.2 부모 텍스트 번들 조회 포트(04-pipelines/17 §2.5 제안).

    실 구현(Valkey `ptxt:{tenant_id}:{chunk_set_blake3}` → 오브젝트 스토리지 순 조회)은 이 승격
    범위 밖이다 — `retrieval.postprocess.parent_expand`는 이 Protocol만 구조적으로 소비한다.
    """

    def get_many(
        self,
        chunk_set_blake3: str,
        parent_chunk_ids: Sequence[str],
        security: SecurityContext,
    ) -> Mapping[str, ParentEntry]:
        """`parent_chunk_ids` 중 조회 가능한 항목만 매핑으로 반환한다. 전체 실패는 `ParentTextMiss`."""
        ...
