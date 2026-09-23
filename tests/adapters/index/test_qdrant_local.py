"""Qdrant 어댑터 로컬 모드 테스트 — 테넌트 격리·E7 필터 거부·결정적 `point_id`·재upsert 멱등·BM25·테넌트 IDF 검증.

설계 근거: 04-pipelines/13 §3·§4·§6, ADR-0012, ADR-0004(E17), 바이블 §6.1·§10.2·§13.4.
픽스처 출처: `tests/contracts/fixtures/index-record/001.json`(03-contracts/07 예시 2)을 복제해 테넌트·세대·벡터만 바꾼다
(dense 4차원, `sparse_bm25`는 `index_text`의 공백 토큰으로 계산).
구성: 격리(두 테넌트 동일 `chunk_id`), 필터 누락 거부, `point_id` 결정성·변조 탐지, 재upsert 멱등,
보안 필드 누락 배치 거부, 필터 변환 표(§4.3), BM25 포화식·해시·테넌트 코퍼스 IDF 실측,
alias 교체, 컬렉션 대조, Kiwi 토크나이저(설치 시).
불변식: 테넌트 경계를 넘는 검색 결과 유출은 0건이어야 하며(E7), 재upsert는 `point_id`가 같으면 항상
같은 레코드로 수렴해야 한다(E17 멱등성).
검증 계층: 1층(여기서 검증) — `QdrantClient(":memory:")`. 서버 모드 1건은 `needs_docker`.
DEFERRED: `test_server_mode_isolation` — Linux 러너의 `qdrant/qdrant:v1.19.x` 컨테이너(`QDRANT_URL`, 기본
`http://localhost:6333`)에서 `uv run python tools/dev.py test-deferred`로 실행;
payload 인덱스(`is_tenant`, `prefix`) 효과 포함.
"""

from __future__ import annotations

import json
import math
import os
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, uuid5

import pytest
from blake3 import blake3
from qdrant_client import QdrantClient, models

from rag_platform.adapters.index.qdrant.backend import (
    CollectionLayout,
    QdrantIndexBackend,
    alias_name,
    physical_collection_name,
)
from rag_platform.adapters.index.qdrant.bm25_sparse import (
    BM25_B,
    BM25_K1,
    KiwiTokenizer,
    WhitespaceTokenizer,
    bm25_index,
    document_vector,
    query_vector,
    saturate,
    validate_sparse,
)
from rag_platform.adapters.index.qdrant.filters import (
    assert_search_secured,
    build_filter,
    scope_filter,
    to_canonical_json,
)
from rag_platform.adapters.index.qdrant.point_id import point_id_for, verify_record_keys
from rag_platform.contracts.common_types import FilterNode, SecurityFilter, StrategyFilter
from rag_platform.contracts.index_record import IndexRecord
from rag_platform.sdk.hashing import record_id
from rag_platform.sdk.stage import StageError

FIXTURE = Path(__file__).parents[2] / "contracts" / "fixtures" / "index-record" / "001.json"
TENANT_A = "01J9ZQ4K7X2M8N3P5R6S7T8V9W"
TENANT_B = "01J9ZQ4K7X2M8N3P5R6S7T8V9X"
COLLECTION = "01J9ZQ5A1B2C3D4E5F6G7H8J9K"
DOC_A = "01JAB3C4D5E6F7G8H9JKMNPQRS"
DOC_B = "01JAB3C4D5E6F7G8H9JKMNPQRT"
COMMIT = "01JAB3D0E1F2G3H4J5K6M7N8P9"
PROFILE_HASH = "b9ff31b9802e4e0d7c9b40e929f07c0be24668eaff92ab3e14b7e24a9943dccf"
TOKENIZER = WhitespaceTokenizer()


def _unit(vec: list[float]) -> list[float]:
    norm = math.sqrt(sum(x * x for x in vec))
    return [x / norm for x in vec]


def make_record(
    tenant_id: str,
    *,
    document_id: str = DOC_A,
    chunk_id: str | None = None,
    index_text: str | None = None,
    dense: list[float] | None = None,
    generation: int = 1,
    **overrides: Any,
) -> IndexRecord:
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    chunk = chunk_id or data["chunk_id"]
    rid = record_id(tenant_id, COLLECTION, document_id, generation, chunk)
    text = index_text if index_text is not None else data["index_text"]
    sparse = document_vector(TOKENIZER.tokenize(text))
    assert sparse is not None
    data.update(
        tenant_id=tenant_id,
        collection_id=COLLECTION,
        document_id=document_id,
        chunk_id=chunk,
        index_generation=generation,
        record_id=rid,
        point_id=point_id_for(rid),
        is_current=False,
        index_text=text,
        vectors={"dense": _unit(dense or [1.0, 0.2, 0.1, 0.0]), "sparse_bm25": sparse.model_dump()},
    )
    data["embedding_space_ids"]["sparse_bm25"] = "a" * 64
    data.update(overrides)
    return IndexRecord.model_validate(data)


def security(tenant_id: str, **overrides: Any) -> SecurityFilter:
    data: dict[str, Any] = {
        "tenant_id": tenant_id,
        "collection_ids": [COLLECTION],
        "principals": ["user:kim.minsu@example.go.kr", "group:mois_records", "tenant:*"],
        "visible_set": ["public", "tenant"],
        "as_of": "2026-09-22T09:00:00.000Z",
        "is_current": True,
        "classification_max": "internal",
    }
    data.update(overrides)
    return SecurityFilter.model_validate(data)


STRATEGY = StrategyFilter.model_validate({"level_in": [0], "item_kinds": ["text", "table"]})


@pytest.fixture
def backend() -> QdrantIndexBackend:
    return QdrantIndexBackend.local()


@pytest.fixture
def collection(backend: QdrantIndexBackend) -> str:
    name = physical_collection_name(PROFILE_HASH)
    assert backend.ensure_collection(name, CollectionLayout(dense_dim=4)) is True
    return name


def _load_and_flip(backend: QdrantIndexBackend, collection: str, records: list[IndexRecord]) -> None:
    backend.upsert(collection, records, commit_id=COMMIT, index_generation=1)
    for rec in records:
        backend.set_current(
            collection,
            tenant_id=rec.tenant_id.root,
            collection_id=rec.collection_id.root,
            document_id=rec.document_id.root,
            index_generation=rec.index_generation,
        )


def _code(exc: pytest.ExceptionInfo[StageError]) -> str:
    return exc.value.code


# --- tenant isolation -----------------------------------------------------------------------


def test_same_chunk_id_two_tenants_are_isolated(backend: QdrantIndexBackend, collection: str) -> None:
    rec_a, rec_b = make_record(TENANT_A), make_record(TENANT_B)
    assert rec_a.chunk_id == rec_b.chunk_id
    assert rec_a.point_id != rec_b.point_id  # E17: scope-composed record_id -> distinct points
    _load_and_flip(backend, collection, [rec_a, rec_b])
    assert backend.count(collection, scope_filter(TENANT_A)) == 1
    assert backend.count(collection, scope_filter(TENANT_B)) == 1

    q_dense = _unit([1.0, 0.2, 0.1, 0.0])
    q_sparse = query_vector(TOKENIZER.tokenize("정보보호 책임자"))
    assert q_sparse is not None
    for tenant, rec in ((TENANT_A, rec_a), (TENANT_B, rec_b)):
        flt = build_filter(security(tenant), STRATEGY)
        dense_hits = backend.search_dense(collection, q_dense, query_filter=flt, top_k=10)
        sparse_hits = backend.search_sparse(collection, q_sparse, query_filter=flt, top_k=10)
        assert [h.record_id for h in dense_hits] == [rec.record_id.root]
        assert [h.record_id for h in sparse_hits] == [rec.record_id.root]
        assert {h.payload["tenant_id"] for h in dense_hits + sparse_hits} == {tenant}


def test_acl_and_generation_prefilters_apply(backend: QdrantIndexBackend, collection: str) -> None:
    visible = make_record(TENANT_A)
    denied = make_record(TENANT_A, document_id=DOC_B, acl_deny=["group:mois_records"])
    _load_and_flip(backend, collection, [visible, denied])
    stale = make_record(TENANT_A, generation=2)  # upserted but never flipped -> is_current=false
    backend.upsert(collection, [stale])
    flt = build_filter(security(TENANT_A), STRATEGY)
    hits = backend.search_dense(collection, _unit([1.0, 0.2, 0.1, 0.0]), query_filter=flt, top_k=10)
    assert [h.record_id for h in hits] == [visible.record_id.root]
    public_only = build_filter(security(TENANT_A, classification_max="public"), STRATEGY)
    assert backend.search_dense(collection, _unit([1.0, 0.2, 0.1, 0.0]), query_filter=public_only) == []


# --- E7: missing security filter is rejected ------------------------------------------------


def test_search_without_security_filter_is_rejected(backend: QdrantIndexBackend, collection: str) -> None:
    vec = _unit([1.0, 0.0, 0.0, 0.0])
    with pytest.raises(StageError) as exc:
        build_filter(None)
    assert _code(exc) == "retrieve.security_context_missing"
    tenant_only = scope_filter(TENANT_A, is_current=True)  # no ACL clauses
    no_tenant = build_filter(security(TENANT_A))
    no_tenant.must = [c for c in no_tenant.must if getattr(c, "key", None) != "tenant_id"]  # type: ignore[union-attr]
    for bad in (None, models.Filter(), tenant_only, no_tenant):
        with pytest.raises(StageError) as exc:
            backend.search_dense(collection, vec, query_filter=bad)  # type: ignore[arg-type]
        assert _code(exc) == "retrieve.security_context_missing"
    q = query_vector(["정보보호"])
    assert q is not None
    with pytest.raises(StageError):
        backend.search_sparse(collection, q, query_filter=tenant_only)
    with pytest.raises(StageError) as exc:
        backend.delete(collection, models.Filter(must=[]))
    assert _code(exc) == "index.security_fields_missing"
    with pytest.raises(StageError):
        scope_filter("")


def test_upsert_rejects_batch_missing_security_fields(backend: QdrantIndexBackend, collection: str) -> None:
    good = make_record(TENANT_A)
    bad = make_record(TENANT_A, document_id=DOC_B).model_copy(update={"acl_hash": None})
    with pytest.raises(StageError) as exc:
        backend.upsert(collection, [good, bad])
    assert _code(exc) == "index.security_fields_missing"
    assert backend.count(collection, scope_filter(TENANT_A)) == 0  # nothing of the batch was sent
    with pytest.raises(StageError) as exc:
        backend.upsert(collection, [good.model_copy(update={"is_current": True})])
    assert _code(exc) == "contract.violation"


# --- deterministic point id and idempotent re-upsert ----------------------------------------


def test_point_id_is_deterministic_and_verified() -> None:
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert point_id_for(fixture["record_id"]) == fixture["point_id"]  # 03-contracts/07 example 2
    namespace = uuid5(NAMESPACE_URL, "urn:rag:chunk")
    rid = record_id(TENANT_A, COLLECTION, DOC_A, 1, fixture["chunk_id"])
    assert point_id_for(rid) == str(uuid5(namespace, rid)) == point_id_for(rid)
    assert point_id_for(rid) != point_id_for(record_id(TENANT_A, COLLECTION, DOC_A, 2, fixture["chunk_id"]))
    rec = make_record(TENANT_A)
    assert verify_record_keys(rec) == rec.point_id.root
    tampered = rec.model_copy(update={"point_id": make_record(TENANT_B).point_id})
    with pytest.raises(StageError) as exc:
        verify_record_keys(tampered)
    assert _code(exc) == "contract.violation"
    with pytest.raises(StageError):
        point_id_for("NOT-HEX")


def test_reupsert_is_idempotent(backend: QdrantIndexBackend, collection: str) -> None:
    records = [make_record(TENANT_A), make_record(TENANT_A, document_id=DOC_B)]
    assert backend.upsert(collection, records) == 2
    first = backend.client.retrieve(collection, [r.point_id.root for r in records], with_vectors=True)
    assert backend.upsert(collection, records) == 2
    second = backend.client.retrieve(collection, [r.point_id.root for r in records], with_vectors=True)
    assert backend.count(collection, scope_filter(TENANT_A)) == 2
    assert sorted((str(p.id), json.dumps(p.payload, sort_keys=True)) for p in first) == sorted(
        (str(p.id), json.dumps(p.payload, sort_keys=True)) for p in second
    )
    payload = second[0].payload or {}
    assert "index_text" not in payload
    assert "vectors" not in payload
    assert payload["acl_embargo_until"] is None
    assert payload["acl_deny"] == []


# --- filter DSL translation (13 §4.3) -------------------------------------------------------


def test_filter_translation_matches_section_4_3() -> None:
    user = FilterNode.model_validate(
        {
            "and": [
                {"field": "doc_type", "op": "in", "value": ["notice", "regulation"]},
                {"field": "page", "op": "eq", "value": 3},
            ]
        }
    )
    self_query = FilterNode.model_validate({"field": "external_id", "op": "prefix", "value": "MOIS-"})
    flt = build_filter(security(TENANT_A), STRATEGY, user, self_query)
    assert assert_search_secured(flt) == TENANT_A
    text = to_canonical_json(flt)
    assert '"key":"acl_classification","match":{"any":["public","internal"]}' in text
    assert '{"key":"page_start","range":{"lte":3.0}}' in text or '{"key":"page_start","range":{"lte":3}}' in text
    assert '"match":{"prefix":"MOIS-"}' in text
    assert '"must_not":[{"key":"acl_deny"' in text
    with pytest.raises(StageError) as exc:
        build_filter(security(TENANT_A), user=FilterNode.model_validate({"field": "doc_type", "op": "gt", "value": 1}))
    assert _code(exc) == "contract.violation"


def test_filter_ops_evaluate_in_local_mode(backend: QdrantIndexBackend, collection: str) -> None:
    rec = make_record(TENANT_A, page_start=2, page_end=4)
    _load_and_flip(backend, collection, [rec])
    vec = _unit([1.0, 0.2, 0.1, 0.0])
    cases = {
        '{"field": "page", "op": "eq", "value": 3}': 1,
        '{"field": "page", "op": "in", "value": [5, 6]}': 0,
        '{"field": "external_id", "op": "prefix", "value": "MOIS-NOTICE"}': 1,
        '{"field": "doc_date", "op": "gte", "value": "2026-03-02"}': 1,
        '{"field": "doc_date", "op": "lt", "value": "2026-03-02"}': 0,
        '{"field": "tags", "op": "contains_all", "value": ["고시", "공공기관"]}': 1,
        '{"field": "genre", "op": "ne", "value": "law_article"}': 0,
        '{"field": "custom.notice_no", "op": "exists", "value": true}': 1,
        '{"not": {"field": "doc_type", "op": "in", "value": ["notice"]}}': 0,
    }
    for node, expected in cases.items():
        flt = build_filter(security(TENANT_A), STRATEGY, FilterNode.model_validate(json.loads(node)))
        assert len(backend.search_dense(collection, vec, query_filter=flt)) == expected, node


# --- BM25 sparse (ADR-0012) -----------------------------------------------------------------


def test_bm25_saturation_and_indices() -> None:
    tokens = ["정보보호", "책임자", "정보보호", "지정"]
    vec = document_vector(tokens, avgdl=400.0)
    assert vec is not None
    indices = [i.root for i in vec.indices]
    values = [v.root for v in vec.values]
    assert indices == sorted(set(indices))
    validate_sparse(indices, values)
    dl = len(tokens)
    expected = {bm25_index("정보보호"): 2, bm25_index("책임자"): 1, bm25_index("지정"): 1}
    for idx, value in zip(indices, values, strict=True):
        tf = expected[idx]
        reference = tf * (BM25_K1 + 1) / (tf + BM25_K1 * (1 - BM25_B + BM25_B * dl / 400.0))
        assert abs(value - reference) < 1e-9
        assert value != tf  # never raw tf (TF x IDF degeneration, risk #5)
    assert bm25_index("정보보호") == int.from_bytes(blake3("정보보호".encode()).digest()[:4], "little")
    assert saturate(1, 400, 400) == pytest.approx(1.0)
    with pytest.raises(StageError):
        validate_sparse([3, 3], [1.0, 1.0])
    assert document_vector([]) is None


def test_sparse_bm25_idf_is_tenant_scoped(backend: QdrantIndexBackend, collection: str) -> None:
    """Spike measurement: Qdrant IDF = ln(1 + (N - n + 0.5) / (n + 0.5)) over the corpus filter."""
    a_docs = ["alpha beta", "alpha gamma", "alpha"]
    b_docs = ["alpha delta", "delta epsilon", "epsilon"]
    ids = ["1", "2", "3"]
    records = [
        make_record(TENANT_A, document_id=DOC_A, chunk_id=bm * 64, index_text=text)
        for bm, text in zip(ids, a_docs, strict=True)
    ] + [
        make_record(TENANT_B, document_id=DOC_A, chunk_id=bm * 64, index_text=text)
        for bm, text in zip(ids, b_docs, strict=True)
    ]
    backend.upsert(collection, records)
    backend.set_current(collection, tenant_id=TENANT_A, collection_id=COLLECTION, document_id=DOC_A, index_generation=1)
    backend.set_current(collection, tenant_id=TENANT_B, collection_id=COLLECTION, document_id=DOC_A, index_generation=1)
    q = query_vector(["alpha"])
    assert q is not None
    flt = build_filter(security(TENANT_B), STRATEGY)
    tenant_hits = backend.search_sparse(collection, q, query_filter=flt)
    global_hits = backend.search_sparse(collection, q, query_filter=flt, tenant_idf=False)
    doc_value = document_vector(["alpha", "delta"])
    assert doc_value is not None
    assert len(tenant_hits) == len(global_hits) == 1
    tf_sat = next(
        v.root for i, v in zip(doc_value.indices, doc_value.values, strict=True) if i.root == bm25_index("alpha")
    )
    idf_tenant = math.log(1 + (3 - 1 + 0.5) / (1 + 0.5))
    idf_global = math.log(1 + (6 - 4 + 0.5) / (4 + 0.5))
    assert tenant_hits[0].score == pytest.approx(idf_tenant * tf_sat, rel=1e-5)
    assert global_hits[0].score == pytest.approx(idf_global * tf_sat, rel=1e-5)


def test_kiwi_tokenizer_when_installed() -> None:
    pytest.importorskip("kiwipiepy")
    tok = KiwiTokenizer()
    tokens = tok.tokenize("행정안전부는 기록물 관리 규정을 개정했다.")
    assert tok.analyzer_id.startswith("kiwi:")
    assert "기록물" in tokens
    assert "는" not in tokens
    assert "." not in tokens


# --- collection lifecycle and alias swap ----------------------------------------------------


def test_alias_swap_and_layout_check(backend: QdrantIndexBackend, collection: str) -> None:
    alias = alias_name(COLLECTION)
    assert backend.swap_alias(alias, collection) is None
    green = physical_collection_name("c" * 64)
    backend.ensure_collection(green, CollectionLayout(dense_dim=4))
    assert backend.swap_alias(alias, green) == collection
    assert backend.resolve_alias(alias) == green
    backend.upsert(alias, [make_record(TENANT_A)])  # writes through the alias land in green
    assert backend.count(green, scope_filter(TENANT_A)) == 1
    assert backend.count(collection, scope_filter(TENANT_A)) == 0
    assert backend.ensure_collection(collection, CollectionLayout(dense_dim=4)) is False
    with pytest.raises(StageError) as exc:
        backend.ensure_collection(collection, CollectionLayout(dense_dim=8))
    assert _code(exc) == "profile.invalid"
    with pytest.raises(StageError):
        backend.ensure_collection(collection, CollectionLayout(dense_dim=4, sparse_learned=True))
    assert physical_collection_name(PROFILE_HASH, TENANT_A) == f"rag_vec_b9ff31b9802e_t_{TENANT_A}"


# --- tier 2: server mode --------------------------------------------------------------------


@pytest.mark.needs_docker
def test_server_mode_isolation() -> None:
    # DEFERRED: run against `qdrant/qdrant:v1.19.x` (Docker, Linux runner) via
    # `uv run python tools/dev.py test-deferred`; also exercises real payload indexes (is_tenant, prefix).
    client = QdrantClient(url=os.environ.get("QDRANT_URL", "http://localhost:6333"))
    server = QdrantIndexBackend(client)
    name = physical_collection_name("d" * 64)
    if client.collection_exists(name):
        client.delete_collection(name)
    server.ensure_collection(name, CollectionLayout(dense_dim=4))
    rec_a, rec_b = make_record(TENANT_A), make_record(TENANT_B)
    _load_and_flip(server, name, [rec_a, rec_b])
    hits = server.search_dense(
        name, _unit([1.0, 0.2, 0.1, 0.0]), query_filter=build_filter(security(TENANT_A), STRATEGY)
    )
    assert [h.record_id for h in hits] == [rec_a.record_id.root]
    client.delete_collection(name)
