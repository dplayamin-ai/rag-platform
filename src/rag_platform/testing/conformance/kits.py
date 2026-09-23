"""확장 지점 14종의 적합성 기반 클래스 — 가이드 §8.1 표(`ParserConformance` 등)를 전체로 일반화한다.

역할: 바이블 §5.7 `ExtensionPoint`(D-10) 14종 각각에 상속용 pytest 기반 클래스를 하나씩 제공하고,
`CONFORMANCE_KIT_BY_EXTENSION_POINT`로 조회할 수 있게 한다.
설계 근거: `docs/10-development/06-plugin-development-guide.md` §8.1(기반 클래스 표, "제안"
일반화), §5.6(index_backend 특유 항목: tenant 보안·E17 upsert 멱등성), `sdk/ports.py`(embedder·
index_backend는 `Stage` 5멤버가 아니라 역할 포트); ADR-0032.
구성: 12종(`fetcher`~`packer`, `evaluator`)은 `base.StageConformanceBase`를 그대로 상속(`Stage`
5멤버 프로토콜); `embedder`/`index_backend`는 `sdk.ports.Embedder`/`IndexBackend` 역할 포트라
전용 클래스(`EmbedderConformance`/`IndexBackendConformance`)로 따로 두고 `base.PortConformanceKitBase`
를 상속한다. `CONFORMANCE_KIT_BY_EXTENSION_POINT`는 14개 값 전부를 담은 조회 표다.
불변식: 각 클래스의 `extension_point` 클래스 변수는 정확히 `plugins.registry.EXTENSION_POINTS`
값 하나와 같다(`tests/unit/conformance/test_kit_catalog.py`가 확인). `evaluator`는 아직 `sdk.stage`
`STAGE_NAMES` 카탈로그에 이름이 없어(05 미해결 이슈 19) `stage_name=None`으로 둔다.
검증 계층: 1층(여기서 검증) — `tests/unit/conformance/`.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any, ClassVar

import pytest

from rag_platform.sdk.ports import Embedder, IndexBackend
from rag_platform.testing.conformance.base import PortConformanceKitBase, StageConformanceBase

if TYPE_CHECKING:
    from collections.abc import Mapping

__all__ = [
    "CONFORMANCE_KIT_BY_EXTENSION_POINT",
    "ChunkerConformance",
    "EmbedderConformance",
    "EnricherConformance",
    "EvaluatorConformance",
    "FetcherConformance",
    "FuserConformance",
    "IndexBackendConformance",
    "NormalizerConformance",
    "PackerConformance",
    "ParserConformance",
    "PostprocessorConformance",
    "QueryTransformerConformance",
    "RerankerConformance",
    "RetrieverConformance",
]


class FetcherConformance(StageConformanceBase):
    """`fetcher` — `fetch` stage. 원본 바이트를 읽어 `SourceDocument`를 만든다(바이블 §4.2)."""

    extension_point: ClassVar[str] = "fetcher"
    stage_name: ClassVar[str | None] = "fetch"


class ParserConformance(StageConformanceBase):
    """`parser` — `parse` stage(§4 튜토리얼 1).

    `supports_resumable=true`면 `resumable_equivalence`(제안, 01 미해결 이슈 10)를 서브클래스가
    별도로 더한다.
    """

    extension_point: ClassVar[str] = "parser"
    stage_name: ClassVar[str | None] = "parse"


class NormalizerConformance(StageConformanceBase):
    """`normalizer` — `normalize` stage(NFC 정규화, PII 정책)."""

    extension_point: ClassVar[str] = "normalizer"
    stage_name: ClassVar[str | None] = "normalize"


class ChunkerConformance(StageConformanceBase):
    """`chunker` — `chunk` stage. 구조 필드용 `requires_lineage = ("ParsedDocument",)`가 흔하다(§3.1)."""

    extension_point: ClassVar[str] = "chunker"
    stage_name: ClassVar[str | None] = "chunk"


class EnricherConformance(StageConformanceBase):
    """`enricher` — `enrich` stage(LLM 서브스텝은 `requires_lineage=("ChunkSet",)`, AM-26)."""

    extension_point: ClassVar[str] = "enricher"
    stage_name: ClassVar[str | None] = "enrich"


class QueryTransformerConformance(StageConformanceBase):
    """`query_transformer` — `plan` stage(질의 확장·재작성)."""

    extension_point: ClassVar[str] = "query_transformer"
    stage_name: ClassVar[str | None] = "plan"


class RetrieverConformance(StageConformanceBase):
    """`retriever` — `retrieve` stage. §8.1 표: `security_invariants`, `contract_roundtrip`."""

    extension_point: ClassVar[str] = "retriever"
    stage_name: ClassVar[str | None] = "retrieve"


class FuserConformance(StageConformanceBase):
    """`fuser` — `fuse` stage. §8.1 표: `litm_order`, `fuser_equivalence`(RRF 등가성)."""

    extension_point: ClassVar[str] = "fuser"
    stage_name: ClassVar[str | None] = "fuse"


class RerankerConformance(StageConformanceBase):
    """`reranker` — `rerank` stage. `mutates_text=true`면 `renderer_citation_roundtrip`을 더한다(§8.1)."""

    extension_point: ClassVar[str] = "reranker"
    stage_name: ClassVar[str | None] = "rerank"


class PostprocessorConformance(StageConformanceBase):
    """`postprocessor` — `postprocess` stage."""

    extension_point: ClassVar[str] = "postprocessor"
    stage_name: ClassVar[str | None] = "postprocess"


class PackerConformance(StageConformanceBase):
    """`packer` — `pack` stage. §8.1 표: `litm_order`, `renderer_citation_roundtrip`."""

    extension_point: ClassVar[str] = "packer"
    stage_name: ClassVar[str | None] = "pack"


class EvaluatorConformance(StageConformanceBase):
    """`evaluator` — 아직 `sdk.stage.STAGE_NAMES` 카탈로그에 이름이 없다(05 미해결 이슈 19).

    `stage_name=None`이라 `StageErrorCatalogConformance`가 그 검사를 자동으로 건너뛴다.
    """

    extension_point: ClassVar[str] = "evaluator"
    stage_name: ClassVar[str | None] = None


class EmbedderConformance(PortConformanceKitBase):
    """`embedder` — `sdk.ports.Embedder` 역할 포트(§4.2 `embed` stage가 내부에서 위임한다).

    `Stage` 5멤버 대신 포트 표면(`embedding_space_id`/`dim`/`normalized`/`embed_documents`/
    `embed_query`)과 그 결정성을 검증한다(`sdk/ports.py`: "정합성 페이크가 필요한 최소 표면").
    """

    extension_point: ClassVar[str] = "embedder"
    stage_name: ClassVar[str | None] = "embed"

    def build_embedder(self) -> Any:
        """Return the `Embedder`-protocol instance under test; concrete tests must override this."""
        msg = f"{type(self).__name__}.build_embedder() must be implemented by the concrete conformance test"
        raise NotImplementedError(msg)

    def sample_texts(self) -> list[str]:
        """Return the deterministic document texts the shape/idempotency checks embed."""
        return ["문서 하나", "문서 둘", "문서 하나"]  # a repeated text checks content-derived determinism

    def test_embedder_implements_the_role_port_protocol(self) -> None:
        """The built object structurally satisfies `sdk.ports.Embedder` (runtime-checkable)."""
        assert isinstance(self.build_embedder(), Embedder)

    def test_embed_documents_is_deterministic_and_matches_declared_dim(self) -> None:
        """Same texts -> same vectors (idempotency), each of length `embedder.dim`."""
        embedder = self.build_embedder()
        vectors_1 = embedder.embed_documents(self.sample_texts())
        vectors_2 = embedder.embed_documents(self.sample_texts())
        assert vectors_1 == vectors_2
        assert vectors_1[0] == vectors_1[2]  # repeated text -> identical vector (content-derived)
        assert all(len(vector) == embedder.dim for vector in vectors_1)

    def test_embed_query_is_consistent_with_embed_documents(self) -> None:
        """`embed_query(t)` equals the single-text `embed_documents([t])` element (contract shape)."""
        embedder = self.build_embedder()
        text = self.sample_texts()[0]
        assert embedder.embed_query(text) == embedder.embed_documents([text])[0]

    def test_normalized_vectors_are_unit_length(self) -> None:
        """When `normalized=True`, every embedded vector has L2 norm 1 (bible sec. 5.6 `EmbeddedChunkSet`)."""
        embedder = self.build_embedder()
        if not embedder.normalized:
            pytest.skip("this embedder declares normalized=False")
        for vector in embedder.embed_documents(self.sample_texts()):
            norm = math.sqrt(sum(component * component for component in vector))
            assert norm == pytest.approx(1.0, abs=1e-9)


class IndexBackendConformance(PortConformanceKitBase):
    """`index_backend` — `sdk.ports.IndexBackend` 역할 포트.

    §8.1 표: `security_invariants`, `idempotency`(E17). `Stage` 5멤버 대신 upsert/search 표면과
    tenant 격리를 검증한다.
    """

    extension_point: ClassVar[str] = "index_backend"
    stage_name: ClassVar[str | None] = "index"

    def build_backend(self) -> Any:
        """Return the `IndexBackend`-protocol instance under test; concrete tests must override this."""
        msg = f"{type(self).__name__}.build_backend() must be implemented by the concrete conformance test"
        raise NotImplementedError(msg)

    def test_index_backend_implements_the_role_port_protocol(self) -> None:
        """The built object structurally satisfies `sdk.ports.IndexBackend` (runtime-checkable)."""
        assert isinstance(self.build_backend(), IndexBackend)

    def test_upsert_is_idempotent_by_record_id(self) -> None:
        """Upserting the same `id` twice overwrites in place; it never duplicates (E17)."""
        backend = self.build_backend()
        record = {"id": "rec-1", "tenant_id": "tenant-a", "vector": [1.0, 0.0], "text": "hello world"}
        backend.upsert([record])
        backend.upsert([record])
        hits = backend.search_dense("tenant-a", [1.0, 0.0], top_k=10)
        assert len(hits) == 1
        assert hits[0][0] == "rec-1"

    def test_search_is_scoped_by_tenant_id(self) -> None:
        """A tenant never sees another tenant's records in dense or lexical search (E7)."""
        backend = self.build_backend()
        backend.upsert(
            [
                {"id": "rec-a", "tenant_id": "tenant-a", "vector": [1.0, 0.0], "text": "seoul weather"},
                {"id": "rec-b", "tenant_id": "tenant-b", "vector": [1.0, 0.0], "text": "seoul weather"},
            ]
        )
        dense_hits = backend.search_dense("tenant-a", [1.0, 0.0], top_k=10)
        lexical_hits = backend.search_lexical("tenant-a", "seoul", top_k=10)
        assert {record_id for record_id, _ in dense_hits} == {"rec-a"}
        assert {record_id for record_id, _ in lexical_hits} == {"rec-a"}


CONFORMANCE_KIT_BY_EXTENSION_POINT: Mapping[str, type] = {
    "fetcher": FetcherConformance,
    "parser": ParserConformance,
    "normalizer": NormalizerConformance,
    "chunker": ChunkerConformance,
    "enricher": EnricherConformance,
    "embedder": EmbedderConformance,
    "index_backend": IndexBackendConformance,
    "query_transformer": QueryTransformerConformance,
    "retriever": RetrieverConformance,
    "fuser": FuserConformance,
    "reranker": RerankerConformance,
    "postprocessor": PostprocessorConformance,
    "packer": PackerConformance,
    "evaluator": EvaluatorConformance,
}
