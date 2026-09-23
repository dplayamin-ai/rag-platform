"""F4-02 단위·통합 테스트 — `channels.retrieve_once`·`fusion.fuse`(+골든 동치성)·`hydrate.hydrate`·두 어댑터.

설계 근거: `docs/13-implementation/wp/WP-402-channels-fusion-hydrate.md`. 픽스처 출처:
`tests/contracts/fixtures/query-plan/001.json`(유효한 `QueryPlan`을 채널·`fusion`·`hydrate`만
바꿔 재사용)·`tests/contracts/fixtures/index-record/001.json`(`qdrant_dense`/`qdrant_sparse_bm25`
어댑터 통합 테스트의 `IndexRecord` 베이스)·`tests/fixtures/fusion/rrf_3ch_5cand.json`(RRF 골든 벡터).
구성: 픽스처 팩토리(`_load_plan`, `_two_channel_plan`, `_candidate`, `_channel_run`,
`_candidate_set`) + 페이크(`_FakeRetriever`, `_ConcurrencyProbeRetriever`, `_FakeHydrateBackend`) +
네 그룹의 테스트(`fusion.fuse_ranks` 골든 동치성·`fusion.fuse`·`channels.retrieve_once`·
`hydrate.hydrate`·두 Qdrant 리트리버 어댑터).
불변식: 모든 테스트는 결정적 픽스처만 쓴다(고정 `now()`, 고정 해시 라벨) — 외부 자원·네트워크 없음.
검증 계층: 1층 — `QdrantClient(":memory:")` 로컬 모드 + 순수 함수 + 페이크. 외부 자원 없음.
"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from ulid import ULID

from rag_platform.adapters.index.qdrant.backend import CollectionLayout, QdrantIndexBackend, alias_name
from rag_platform.adapters.index.qdrant.bm25_sparse import WhitespaceTokenizer, document_vector
from rag_platform.adapters.retrieve.qdrant_dense import QdrantDenseRetriever
from rag_platform.adapters.retrieve.qdrant_sparse_bm25 import QdrantSparseBm25Retriever
from rag_platform.contracts import common_types as ct
from rag_platform.contracts.candidate_set import Candidate, CandidateSet, ChannelRun, FiltersApplied, PayloadSlim
from rag_platform.contracts.common_types import Producer
from rag_platform.contracts.index_record import IndexRecord
from rag_platform.contracts.query_plan import ChannelPlan, FusionPlan, HydratePlan, QueryPlan
from rag_platform.retrieval import channels, fusion, hydrate
from rag_platform.retrieval.channels import ChannelRunInput, QueryVectors
from rag_platform.sdk.hashing import hash_of, point_id_for_record, record_id as record_id_of
from rag_platform.sdk.stage import StageError
from rag_platform.testing.fuser_equivalence import assert_fuser_matches_rrf_golden, load_golden_case

_FIXTURES_DIR = Path(__file__).parents[1] / "fixtures"
_CONTRACT_FIXTURES = Path(__file__).parents[1] / "contracts" / "fixtures"
_QUERY_PLAN_FIXTURE = _CONTRACT_FIXTURES / "query-plan" / "001.json"
_INDEX_RECORD_FIXTURE = _CONTRACT_FIXTURES / "index-record" / "001.json"
_GOLDEN_FUSION_FIXTURE = _FIXTURES_DIR / "fusion" / "rrf_3ch_5cand.json"

TENANT = "01J9ZQ4K7X2M8N3P5R6S7T8V9W"
COLLECTION = "01J9ZQ5A1B2C3D4E5F6G7H8J9K"
DOCUMENT = "01JAB3C4D5E6F7G8H9JKMNPQRS"


def _now() -> datetime:
    return datetime(2026, 9, 23, 9, 0, 0, tzinfo=UTC)


class _FakeCtx:
    """`StageContext`의 `now()`만 필요로 하는 리트리버/`fuse`/`hydrate` 테스트용 최소 더블."""

    def now(self) -> datetime:
        return _now()


# ---------------------------------------------------------------------------
# QueryPlan 픽스처 팩토리
# ---------------------------------------------------------------------------


def _load_plan() -> QueryPlan:
    """001 fixture를 읽고 이 WP 테스트가 다루지 않는 `user`/`self_query`/기존 `degraded`를 비운다."""
    data = json.loads(_QUERY_PLAN_FIXTURE.read_text(encoding="utf-8"))
    plan = QueryPlan.model_validate(data)
    filters = plan.filters.model_copy(update={"user": None, "self_query": None, "relaxable_keys": []})
    return plan.model_copy(update={"filters": filters, "degraded": []})


def _channel_plan(channel: str, retriever_id: str, *, embedding_profile_hash: str, top_k: int = 10) -> ChannelPlan:
    return ChannelPlan(
        channel=channel,
        collection_id=COLLECTION,
        retriever_id=retriever_id,
        backend_id="index_backend.qdrant",
        collection_alias=alias_name(COLLECTION),
        embedding_profile_hash=embedding_profile_hash,
        index_generation_min=1,
        top_k=top_k,
        timeout_ms=250,
        weight=1.0,
        enabled=True,
    )


def _two_channel_plan(*, top_n: int = 10, keep_variant: bool = False, timeout_ms: int | None = None) -> QueryPlan:
    """`dense` + `lexical` 두 채널의 소형 `QueryPlan`(001 fixture 기반, `original` 변형만이 기본)."""
    plan = _load_plan()
    profile_hash = plan.channels[0].embedding_profile_hash
    dense = _channel_plan("dense", "retriever.qdrant_dense", embedding_profile_hash=profile_hash)
    lexical = _channel_plan("lexical", "retriever.qdrant_sparse_bm25", embedding_profile_hash=profile_hash)
    if timeout_ms is not None:
        dense = dense.model_copy(update={"timeout_ms": timeout_ms})
    original = plan.rewritten_queries[0].model_copy(update={"channels": ["dense", "lexical"]})
    if keep_variant:
        rewritten = [original, plan.rewritten_queries[1].model_copy(update={"channels": ["lexical"]})]
    else:
        rewritten = [original]
    return plan.model_copy(
        update={
            "channels": [dense, lexical],
            "rewritten_queries": rewritten,
            "fusion": FusionPlan(method="rrf", k=60, weights={"dense": 1.0, "lexical": 1.0}, variant_query_weight=0.5),
            "hydrate": HydratePlan(top_n=top_n, backend_id="index_backend.qdrant", with_vectors=False),
        }
    )


# ---------------------------------------------------------------------------
# CandidateSet 픽스처 팩토리 (fusion·hydrate 테스트 공용)
# ---------------------------------------------------------------------------


def _payload_slim(label: str) -> PayloadSlim:
    return PayloadSlim(
        heading_path=["Title"],
        page_start=1,
        page_end=1,
        doc_date=None,
        acl_classification="internal",
        acl_hash=hash_of("aclhash", label),
        token_count_primary=42,
        text_preview=f"preview-{label}",
        content_hash=hash_of("content", label),
        text_source="text_layer",
    )


def _candidate(label: str, *, rank: int, score: float) -> Candidate:
    return Candidate(
        record_id=hash_of("rec", label),
        chunk_id=hash_of("chunk", label),
        collection_id=COLLECTION,
        document_id=DOCUMENT,
        doc_version=hash_of("docver", label),
        item_kind="text",
        level=0,
        parent_chunk_id=None,
        score=score,
        rank=rank,
        payload_slim=_payload_slim(label),
        graph_path=None,
    )


def _channel_run(
    channel: str, variant_id: str, retriever_id: str, candidates: list[Candidate], *, status: str = "ok"
) -> ChannelRun:
    return ChannelRun(
        channel_run_id=f"{channel}:{COLLECTION}:{variant_id}",
        channel=channel,
        collection_id=COLLECTION,
        variant_id=variant_id,
        retriever_id=retriever_id,
        backend_id="index_backend.qdrant",
        collection_alias=alias_name(COLLECTION),
        embedding_profile_hash=hash_of("space", "test"),
        index_generation_seen=[1],
        status=status,
        took_ms=5,
        returned=len(candidates),
        total_hits=None,
        truncated=False,
        error=None,
        candidates=candidates,
    )


def _candidate_set(plan: QueryPlan, channel_runs: list[ChannelRun]) -> CandidateSet:
    total_unique = len({c.record_id.root for run in channel_runs for c in run.candidates})
    return CandidateSet(
        schema_version="1.0.0",
        schema_type="CandidateSet",
        tenant_id=plan.tenant_id,
        collection_ids=plan.collection_ids,
        producer=Producer(
            plugin_id="retriever.pipeline",
            plugin_version="0.1.0",
            config_hash=hash_of("config", "{}"),
            image_digest=None,
            model_ids=None,
        ),
        warnings=[],
        degraded=[],
        created_at="2026-09-23T09:00:00.000Z",
        candidate_set_id=str(ULID()),
        plan_id=plan.plan_id,
        query_id=plan.query_id,
        channel_runs=channel_runs,
        filters_applied=FiltersApplied(
            security=plan.filters.security,
            strategy=plan.filters.strategy,
            user=plan.filters.user,
            self_query=plan.filters.self_query,
            effective_hash=plan.filters.effective_hash,
        ),
        security_context_hash=hash_of("sec", "test"),
        total_unique=total_unique,
        total_latency_ms=10,
    )


# ===========================================================================
# fusion.fuse_ranks — RRF 골든 동치성 (testing/fuser_equivalence)
# ===========================================================================


def test_fuse_ranks_matches_rrf_golden() -> None:
    golden = load_golden_case(_GOLDEN_FUSION_FIXTURE)
    assert_fuser_matches_rrf_golden(fusion.fuse_ranks, golden)


# ===========================================================================
# fusion.fuse — CandidateSet -> RankedSet(fused)
# ===========================================================================


def _p1p2p3_candidate_set(plan: QueryPlan) -> CandidateSet:
    original_variant = str(plan.rewritten_queries[0].variant_id.root)
    dense_run = _channel_run(
        "dense",
        original_variant,
        "retriever.qdrant_dense",
        [_candidate("P1", rank=1, score=0.9), _candidate("P2", rank=2, score=0.8)],
    )
    lexical_run = _channel_run(
        "lexical",
        original_variant,
        "retriever.qdrant_sparse_bm25",
        [_candidate("P1", rank=1, score=12.0), _candidate("P3", rank=3, score=9.0)],
    )
    return _candidate_set(plan, [dense_run, lexical_run])


def test_fuse_score_ledger_and_ordering() -> None:
    plan = _two_channel_plan(top_n=10)
    cs = _p1p2p3_candidate_set(plan)
    rs = fusion.fuse(cs, plan, now=_now())

    assert rs.schema_type == "RankedSet"
    assert rs.stage == "fused"
    assert rs.hydrated is False
    assert [r.record_id.root for r in rs.results] == [hash_of("rec", label) for label in ("P1", "P2", "P3")]

    p1, p2, p3 = rs.results
    for result in rs.results:
        contributions = [
            ch.contribution
            for ch in (
                result.score_breakdown.dense,
                result.score_breakdown.sparse,
                result.score_breakdown.lexical,
            )
            if ch is not None
        ]
        assert sum(contributions) == pytest.approx(result.fused_score, rel=1e-9)

    assert p1.channels_hit == ["dense", "lexical"]
    assert "multi_channel_hit" in p1.explain
    assert p2.channels_hit == ["dense"]
    assert "dense_only_hit" in p2.explain
    assert p3.channels_hit == ["lexical"]
    assert "lexical_only_hit" in p3.explain

    assert p1.final_rank == 1
    assert p1.final_score == pytest.approx(1.0)
    assert p3.final_score == pytest.approx(0.0)
    assert 0.0 < p2.final_score < 1.0
    assert [r.final_rank for r in rs.results] == [1, 2, 3]
    assert rs.fusion.candidates_in == cs.total_unique
    assert rs.fusion.candidates_out == len(rs.results)


def test_fuse_variant_query_weight_is_half() -> None:
    plan = _two_channel_plan(top_n=10, keep_variant=True)
    original_variant = str(plan.rewritten_queries[0].variant_id.root)
    variant_id = str(plan.rewritten_queries[1].variant_id.root)
    lexical_run_original = _channel_run("lexical", original_variant, "retriever.qdrant_sparse_bm25", [])
    lexical_run_variant = _channel_run(
        "lexical", variant_id, "retriever.qdrant_sparse_bm25", [_candidate("P4", rank=1, score=5.0)]
    )
    cs = _candidate_set(plan, [lexical_run_original, lexical_run_variant])

    rs = fusion.fuse(cs, plan, now=_now())

    assert len(rs.results) == 1
    result = rs.results[0]
    expected_contribution = 1.0 * 0.5 / (60 + 1)
    assert result.fused_score == pytest.approx(expected_contribution, rel=1e-9)
    assert result.score_breakdown.lexical.contribution == pytest.approx(expected_contribution, rel=1e-9)
    assert [v.root for v in result.variant_ids] == [variant_id]
    assert result.channels_hit == ["lexical"]


def test_fuse_rejects_non_rrf_method() -> None:
    plan = _two_channel_plan(top_n=10)
    plan = plan.model_copy(update={"fusion": plan.fusion.model_copy(update={"method": "convex_minmax"})})
    cs = _p1p2p3_candidate_set(plan)
    with pytest.raises(StageError) as exc_info:
        fusion.fuse(cs, plan, now=_now())
    assert exc_info.value.code == "contract.violation"


# ===========================================================================
# channels.retrieve_once — asyncio 병렬 실행 + degraded/unavailable
# ===========================================================================


@dataclass
class _FakeRetriever:
    """`channels.Retriever` 더블 — 고정 후보 목록을 돌려주거나 지연·오류를 시뮬레이션한다."""

    channel: str
    plugin_id: str
    hits: list[tuple[str, float]] = field(default_factory=list)
    delay_s: float = 0.0
    error: BaseException | None = None

    def capabilities(self) -> None:
        return None

    async def run(self, inp: ChannelRunInput, ctx: Any) -> ChannelRun:
        if self.delay_s:
            await asyncio.sleep(self.delay_s)
        if self.error is not None:
            raise self.error
        variant_id = str(inp.variant.variant_id.root)
        candidates = [
            _candidate(label, rank=rank, score=score) for rank, (label, score) in enumerate(self.hits, start=1)
        ]
        return _channel_run(str(inp.channel.channel.value), variant_id, self.plugin_id, candidates)


def test_retrieve_once_runs_channels_in_parallel() -> None:
    plan = _two_channel_plan(top_n=10)
    retrievers = {
        "retriever.qdrant_dense": _FakeRetriever("dense", "retriever.qdrant_dense", hits=[("P1", 0.9), ("P2", 0.8)]),
        "retriever.qdrant_sparse_bm25": _FakeRetriever("lexical", "retriever.qdrant_sparse_bm25", hits=[("P1", 12.0)]),
    }

    cs = asyncio.run(channels.retrieve_once(plan, {}, _FakeCtx(), retrievers=retrievers))

    assert cs.schema_type == "CandidateSet"
    statuses = {str(run.channel.value): run.status for run in cs.channel_runs}
    assert statuses == {"dense": "ok", "lexical": "ok"}
    assert cs.total_unique == 2  # P1, P2 (record_id 기준 중복 제거)
    assert cs.degraded == []


def test_retrieve_once_marks_timeout_channel_degraded() -> None:
    plan = _two_channel_plan(top_n=10, timeout_ms=20)
    retrievers = {
        "retriever.qdrant_dense": _FakeRetriever("dense", "retriever.qdrant_dense", delay_s=0.2),
        "retriever.qdrant_sparse_bm25": _FakeRetriever("lexical", "retriever.qdrant_sparse_bm25", hits=[("P1", 12.0)]),
    }

    cs = asyncio.run(channels.retrieve_once(plan, {}, _FakeCtx(), retrievers=retrievers))

    by_channel = {str(run.channel.value): run for run in cs.channel_runs}
    assert by_channel["dense"].status == "timeout"
    assert by_channel["dense"].error.code == "retrieve.channel_timeout"
    assert by_channel["lexical"].status == "ok"
    assert any(d.component == "channel.dense" and d.reason == "timeout" for d in cs.degraded)


def test_retrieve_once_raises_unavailable_when_all_channels_fail() -> None:
    plan = _two_channel_plan(top_n=10, timeout_ms=20)
    retrievers = {
        "retriever.qdrant_dense": _FakeRetriever("dense", "retriever.qdrant_dense", delay_s=0.2),
        "retriever.qdrant_sparse_bm25": _FakeRetriever(
            "lexical", "retriever.qdrant_sparse_bm25", error=StageError("retrieve.backend_error", stage="retrieve")
        ),
    }

    with pytest.raises(StageError) as exc_info:
        asyncio.run(channels.retrieve_once(plan, {}, _FakeCtx(), retrievers=retrievers))
    assert exc_info.value.code == "retrieve.unavailable"


def test_retrieve_once_propagates_security_context_missing() -> None:
    plan = _two_channel_plan(top_n=10)
    retrievers = {
        "retriever.qdrant_dense": _FakeRetriever("dense", "retriever.qdrant_dense", hits=[("P1", 0.9)]),
        "retriever.qdrant_sparse_bm25": _FakeRetriever(
            "lexical",
            "retriever.qdrant_sparse_bm25",
            error=StageError("retrieve.security_context_missing", stage="retrieve"),
        ),
    }

    with pytest.raises(StageError) as exc_info:
        asyncio.run(channels.retrieve_once(plan, {}, _FakeCtx(), retrievers=retrievers))
    assert exc_info.value.code == "retrieve.security_context_missing"


def test_retrieve_once_reraises_contract_violation_instead_of_masking_it() -> None:
    """리뷰 지적: `contract.violation`(예: 사용자 필터 값 오류)은 부분 실패로 감싸 503으로 뭉개면
    안 된다 — 클라이언트 자신의 입력 오류를 재시도 가능한 서버 오류로 잘못 알리게 된다."""
    plan = _two_channel_plan(top_n=10)
    retrievers = {
        "retriever.qdrant_dense": _FakeRetriever("dense", "retriever.qdrant_dense", hits=[("P1", 0.9)]),
        "retriever.qdrant_sparse_bm25": _FakeRetriever(
            "lexical",
            "retriever.qdrant_sparse_bm25",
            error=StageError("contract.violation", stage="index", detail="op 'exists' needs a boolean value"),
        ),
    }

    with pytest.raises(StageError) as exc_info:
        asyncio.run(channels.retrieve_once(plan, {}, _FakeCtx(), retrievers=retrievers))
    assert exc_info.value.code == "contract.violation"


def test_retrieve_once_returns_empty_candidate_set_when_no_runs_are_enabled() -> None:
    """리뷰 지적: `route=no_retrieval`(모든 채널 disabled + 변형 `channels=[]`)이면 시도할 런이 아예
    없다 — "성공 런이 하나도 없다"(`retrieve.unavailable`, 503)와 달리 실패가 아니라 빈 결과다."""
    plan = _two_channel_plan(top_n=10)
    all_disabled = [c.model_copy(update={"enabled": False}) for c in plan.channels]
    no_channel_variant = plan.rewritten_queries[0].model_copy(update={"channels": []})
    plan = plan.model_copy(update={"channels": all_disabled, "rewritten_queries": [no_channel_variant]})

    cs = asyncio.run(channels.retrieve_once(plan, {}, _FakeCtx(), retrievers={}))

    assert cs.schema_type == "CandidateSet"
    assert cs.total_unique == 0
    assert cs.degraded == []
    assert len(cs.channel_runs) == 2
    assert all(run.status == "disabled" for run in cs.channel_runs)


def test_retrieve_once_keeps_disabled_channel_as_disabled() -> None:
    plan = _two_channel_plan(top_n=10)
    disabled = _channel_plan(
        "sparse", "retriever.qdrant_sparse", embedding_profile_hash=plan.channels[0].embedding_profile_hash
    ).model_copy(update={"enabled": False})
    plan = plan.model_copy(update={"channels": [*plan.channels, disabled]})
    retrievers = {
        "retriever.qdrant_dense": _FakeRetriever("dense", "retriever.qdrant_dense", hits=[("P1", 0.9)]),
        "retriever.qdrant_sparse_bm25": _FakeRetriever("lexical", "retriever.qdrant_sparse_bm25", hits=[("P1", 12.0)]),
    }

    cs = asyncio.run(channels.retrieve_once(plan, {}, _FakeCtx(), retrievers=retrievers))

    disabled_runs = [run for run in cs.channel_runs if str(run.channel.value) == "sparse"]
    assert len(disabled_runs) == 1
    assert disabled_runs[0].status == "disabled"
    assert disabled_runs[0].candidates == []


@dataclass
class _ConcurrencyProbeRetriever:
    """세마포어 동시성 상한을 넘지 않는지 관찰하는 더블(동시 실행 계수기)."""

    channel: str = "dense"
    plugin_id: str = "retriever.concurrency_probe"
    active: int = 0
    peak: int = 0

    def capabilities(self) -> None:
        return None

    async def run(self, inp: ChannelRunInput, ctx: Any) -> ChannelRun:
        self.active += 1
        self.peak = max(self.peak, self.active)
        await asyncio.sleep(0.03)
        self.active -= 1
        variant_id = str(inp.variant.variant_id.root)
        return _channel_run("dense", variant_id, self.plugin_id, [])


def test_retrieve_once_respects_concurrency_limit() -> None:
    plan = _two_channel_plan(top_n=10)
    probe = _ConcurrencyProbeRetriever()
    extra_channels = [
        _channel_plan(
            "dense", "retriever.concurrency_probe", embedding_profile_hash=plan.channels[0].embedding_profile_hash
        ).model_copy(update={"collection_id": str(ULID())})
        for _ in range(4)
    ]
    plan = plan.model_copy(update={"channels": [*plan.channels, *extra_channels]})
    retrievers = {
        "retriever.qdrant_dense": _FakeRetriever("dense", "retriever.qdrant_dense", hits=[("P1", 0.9)]),
        "retriever.qdrant_sparse_bm25": _FakeRetriever("lexical", "retriever.qdrant_sparse_bm25", hits=[("P1", 12.0)]),
        "retriever.concurrency_probe": probe,
    }

    asyncio.run(channels.retrieve_once(plan, {}, _FakeCtx(), retrievers=retrievers, concurrency=2))

    assert probe.peak <= 2


# ===========================================================================
# hydrate.hydrate — 배치 조회 + partial_result
# ===========================================================================


def _hydrate_payload(record_id: str, *, text: str = "hello world") -> dict[str, Any]:
    return {
        "record_id": record_id,
        "text": text,
        "context_prefix": "ctx",
        "heading_path": ["Title"],
        "numbering_path": [],
        "page_start": 1,
        "page_end": 1,
        "block_refs": [],
        "sentence_spans": [],
        "table_ref": None,
        "html_ref": None,
        "acl_allow": ["tenant:*"],
        "acl_deny": [],
        "acl_visibility": "tenant",
        "acl_classification": "internal",
        "acl_embargo_until": None,
        "acl_expires_at": None,
        "acl_hash": hash_of("aclhash", record_id),
        "title": "Doc Title",
        "source_uri": "https://example.org/doc",
        "external_id": None,
        "doc_date": None,
        "doc_type": None,
        "lang": "ko",
        "text_source": "text_layer",
        "ocr_confidence_min": None,
        "chunk_set_blake3": hash_of("chunkset", record_id),
        "token_count_primary": 10,
        "ordinal": 0,
        "text_truncated": False,
        "pii_policy_applied": "keep",
    }


@dataclass
class _FakeHydrateBackend:
    payloads_by_record_id: dict[str, dict[str, Any]]
    calls: list[tuple[str, tuple[str, ...]]] = field(default_factory=list)

    async def retrieve_by_ids(
        self, alias: str, record_ids: list[str], *, security: Any, with_payload: Any
    ) -> list[dict[str, Any]]:
        self.calls.append((alias, tuple(record_ids)))
        return [self.payloads_by_record_id[rid] for rid in record_ids if rid in self.payloads_by_record_id]


def test_hydrate_fills_all_results() -> None:
    plan = _two_channel_plan(top_n=10)
    cs = _p1p2p3_candidate_set(plan)
    rs = fusion.fuse(cs, plan, now=_now())
    backend = _FakeHydrateBackend(
        {
            hash_of("rec", label): _hydrate_payload(hash_of("rec", label), text=f"text-{label}")
            for label in ("P1", "P2", "P3")
        }
    )

    hydrated = asyncio.run(hydrate.hydrate(rs, plan, backend, now=_now()))

    assert hydrated.hydrated is True
    assert [r.final_rank for r in hydrated.results] == [1, 2, 3]
    assert hydrated.results[0].text == "text-P1"
    assert hydrated.results[0].acl.visibility == "tenant"
    assert hydrated.stats.hydrated_n == 3
    assert hydrated.omitted == []
    assert len(backend.calls) == 1  # 단일 컬렉션 -> alias 1개 -> 1회 배치 호출


def test_hydrate_marks_missing_record_as_partial_result() -> None:
    plan = _two_channel_plan(top_n=10)
    cs = _p1p2p3_candidate_set(plan)
    rs = fusion.fuse(cs, plan, now=_now())
    # P2(fused_rank 2)의 payload만 없다 — 세대 플립 경합 시뮬레이션.
    backend = _FakeHydrateBackend(
        {hash_of("rec", label): _hydrate_payload(hash_of("rec", label), text=f"text-{label}") for label in ("P1", "P3")}
    )

    hydrated = asyncio.run(hydrate.hydrate(rs, plan, backend, now=_now()))

    assert hydrated.hydrated is True
    assert [r.chunk_id.root for r in hydrated.results] == [hash_of("chunk", "P1"), hash_of("chunk", "P3")]
    assert [r.final_rank for r in hydrated.results] == [1, 2]
    assert hydrated.results[1].fused_rank == 3  # fused_rank는 그대로 유지
    assert len(hydrated.omitted) == 1
    assert hydrated.omitted[0].reason == "hydrate_missing"
    assert any(d.component == "hydrate" and d.reason == "partial_result" for d in hydrated.degraded)
    assert hydrated.stats.hydrated_n == 2


def test_hydrate_is_idempotent_when_already_hydrated() -> None:
    plan = _two_channel_plan(top_n=10)
    cs = _p1p2p3_candidate_set(plan)
    rs = fusion.fuse(cs, plan, now=_now())
    already = rs.model_copy(update={"hydrated": True})
    backend = _FakeHydrateBackend({})

    result = asyncio.run(hydrate.hydrate(already, plan, backend, now=_now()))

    assert result is already
    assert backend.calls == []


# ===========================================================================
# adapters/retrieve/qdrant_dense.py, qdrant_sparse_bm25.py — 실 Qdrant 로컬 모드
# ===========================================================================

_LAYOUT = CollectionLayout(dense_dim=1024, sparse_bm25=True, sparse_learned=False)


def _make_index_record(
    *, chunk_id: str, index_text: str, dense: list[float], collection_id: str = COLLECTION
) -> IndexRecord:
    data = json.loads(_INDEX_RECORD_FIXTURE.read_text(encoding="utf-8"))
    rid = record_id_of(TENANT, collection_id, DOCUMENT, 1, chunk_id)
    sparse = document_vector(WhitespaceTokenizer().tokenize(index_text))
    data.update(
        tenant_id=TENANT,
        collection_id=collection_id,
        document_id=DOCUMENT,
        chunk_id=chunk_id,
        index_generation=1,
        record_id=rid,
        point_id=str(point_id_for_record(rid)),
        is_current=False,
        index_text=index_text,
        text=index_text,
        text_preview=index_text[:80],
        context_prefix=index_text[:40],
        vectors={"dense": dense, "sparse_bm25": sparse.model_dump()},
    )
    data["embedding_space_ids"]["sparse_bm25"] = "a" * 64
    return IndexRecord.model_validate(data)


def _local_backend_with_record(record: IndexRecord) -> QdrantIndexBackend:
    backend = QdrantIndexBackend.local()
    alias = alias_name(COLLECTION)
    backend.ensure_collection(alias, _LAYOUT)
    backend.upsert(alias, [record])
    backend.set_current(alias, tenant_id=TENANT, collection_id=COLLECTION, document_id=DOCUMENT, index_generation=1)
    return backend


def _adapter_channel_run_input(
    plan: QueryPlan, channel: str, retriever_id: str, *, query_vectors: QueryVectors, query_text: str
) -> ChannelRunInput:
    channel_plan = _channel_plan(channel, retriever_id, embedding_profile_hash=plan.channels[0].embedding_profile_hash)
    variant = plan.rewritten_queries[0]
    return ChannelRunInput(
        channel=channel_plan,
        variant=variant,
        query_vectors=query_vectors,
        query_text=query_text,
        filters=plan.filters,
        exclude_ids=(),
        security=plan.security_context,
        lexical_terms=(),
    )


def _shared_alias_backend_with_two_collections(
    *, collection_a: str, collection_b: str, index_text: str, dense: list[float]
) -> QdrantIndexBackend:
    """§13.4 재현: 두 컬렉션의 레코드가 같은 물리 컬렉션(별칭 하나)을 공유한다."""
    alias = alias_name(collection_a)
    record_a = _make_index_record(
        chunk_id=hash_of("chunk", "shared-a"), index_text=index_text, dense=dense, collection_id=collection_a
    )
    record_b = _make_index_record(
        chunk_id=hash_of("chunk", "shared-b"), index_text=index_text, dense=dense, collection_id=collection_b
    )
    backend = QdrantIndexBackend.local()
    backend.ensure_collection(alias, _LAYOUT)
    backend.upsert(alias, [record_a, record_b])
    for collection_id in (collection_a, collection_b):
        backend.set_current(
            alias, tenant_id=TENANT, collection_id=collection_id, document_id=DOCUMENT, index_generation=1
        )
    return backend


def _adapter_channel_run_input_pinned_to(
    plan: QueryPlan,
    channel: str,
    retriever_id: str,
    *,
    query_vectors: QueryVectors,
    query_text: str,
    channel_collection_id: str,
    security_collection_ids: list[str],
    collection_alias: str,
) -> ChannelRunInput:
    """`_adapter_channel_run_input`과 같으나, 보안 필터가 여러 컬렉션을 허용해도(§10.2 (a)) 이 런은
    `channel_collection_id` 하나만 담당하는 상황(공유 물리 컬렉션, §13.4)을 만든다."""
    channel_plan = _channel_plan(
        channel, retriever_id, embedding_profile_hash=plan.channels[0].embedding_profile_hash
    ).model_copy(update={"collection_id": ct.Ulid(channel_collection_id), "collection_alias": collection_alias})
    security_filter = plan.filters.security.model_copy(
        update={"collection_ids": [ct.Ulid(cid) for cid in security_collection_ids]}
    )
    filters_ = plan.filters.model_copy(update={"security": security_filter})
    return ChannelRunInput(
        channel=channel_plan,
        variant=plan.rewritten_queries[0],
        query_vectors=query_vectors,
        query_text=query_text,
        filters=filters_,
        exclude_ids=(),
        security=plan.security_context,
        lexical_terms=(),
    )


def test_qdrant_dense_retriever_hits_upserted_record() -> None:
    dense_vector = [0.0] * 1023 + [1.0]
    record = _make_index_record(
        chunk_id=hash_of("chunk", "dense-hit"), index_text="apple banana cherry", dense=dense_vector
    )
    backend = _local_backend_with_record(record)
    plan = _load_plan()
    retriever = QdrantDenseRetriever(backend=backend)
    inp = _adapter_channel_run_input(
        plan, "dense", retriever.plugin_id, query_vectors=QueryVectors(dense=tuple(dense_vector)), query_text="apple"
    )

    run = asyncio.run(retriever.run(inp, _FakeCtx()))

    assert run.status == "ok"
    assert run.returned == 1
    assert run.candidates[0].rank == 1
    assert run.candidates[0].score == pytest.approx(1.0, abs=1e-6)
    assert run.candidates[0].payload_slim.text_preview.startswith("apple")


def test_qdrant_dense_retriever_missing_vector_raises_embed_unavailable() -> None:
    backend = QdrantIndexBackend.local()
    plan = _load_plan()
    retriever = QdrantDenseRetriever(backend=backend)
    inp = _adapter_channel_run_input(plan, "dense", retriever.plugin_id, query_vectors=QueryVectors(), query_text="x")

    with pytest.raises(StageError) as exc_info:
        asyncio.run(retriever.run(inp, _FakeCtx()))
    assert exc_info.value.code == "embed.server_unavailable"


def test_qdrant_dense_retriever_pins_to_channel_collection_id() -> None:
    """리뷰 지적(§13.4·§8.1): `col_{cid}_vec` 별칭이 여러 컬렉션의 공유 물리 컬렉션을 가리킬 수 있고
    `SecurityFilter.collection_ids`도 다중 컬렉션 요청에서는 둘 다 담을 수 있다 — 그래도 이 런은
    `channel.collection_id` 하나만 반환해야 한다(그렇지 않으면 다른 컬렉션 채널 런과 후보가 겹쳐
    fusion 기여가 중복된다)."""
    collection_a, collection_b = COLLECTION, str(ULID())
    dense_vector = [0.0] * 1023 + [1.0]
    backend = _shared_alias_backend_with_two_collections(
        collection_a=collection_a, collection_b=collection_b, index_text="apple banana", dense=dense_vector
    )
    plan = _load_plan()
    retriever = QdrantDenseRetriever(backend=backend)
    inp = _adapter_channel_run_input_pinned_to(
        plan,
        "dense",
        retriever.plugin_id,
        query_vectors=QueryVectors(dense=tuple(dense_vector)),
        query_text="apple",
        channel_collection_id=collection_a,
        security_collection_ids=[collection_a, collection_b],
        collection_alias=alias_name(collection_a),
    )

    run = asyncio.run(retriever.run(inp, _FakeCtx()))

    assert run.status == "ok"
    assert run.returned == 1  # 회귀 시 두 컬렉션 레코드가 모두 반환되어 2가 된다
    assert {c.collection_id.root for c in run.candidates} == {collection_a}


def test_qdrant_dense_retriever_does_not_block_event_loop() -> None:
    """리뷰 지적(§8.1 7단계): 동기 `QdrantClient` 호출을 `await` 없이 부르면 이벤트 루프가 막혀
    채널 타임아웃(`asyncio.wait_for`)도 강제되지 않는다 — `asyncio.to_thread`로 떼면 다른 태스크가
    그 사이 계속 진행된다."""
    dense_vector = [0.0] * 1023 + [1.0]
    record = _make_index_record(chunk_id=hash_of("chunk", "slow"), index_text="apple", dense=dense_vector)
    backend = _local_backend_with_record(record)
    sleep_s = 0.1

    class _SleepingBackend:
        """`search_dense`가 동기적으로(진짜 `time.sleep`) 오래 걸리는 백엔드 더블."""

        def search_dense(self, *args: Any, **kwargs: Any) -> list[Any]:
            time.sleep(sleep_s)
            return backend.search_dense(*args, **kwargs)

    plan = _load_plan()
    retriever = QdrantDenseRetriever(backend=_SleepingBackend())  # type: ignore[arg-type]
    inp = _adapter_channel_run_input(
        plan, "dense", retriever.plugin_id, query_vectors=QueryVectors(dense=tuple(dense_vector)), query_text="apple"
    )

    # 같은 "느린" 런 두 개를 동시에 실행한다. 동기 호출이 이벤트 루프를 막는다면(수정 전) 실질적으로
    # 순차 실행되어 총 시간이 `2 * sleep_s`에 가깝다; `asyncio.to_thread`로 뗐다면(수정 후) 각자
    # 스레드에서 겹쳐 돌아 총 시간이 `sleep_s` 하나에 가깝다(리뷰 지적, §8.1 7단계).
    async def _run_two_concurrently() -> None:
        await asyncio.gather(retriever.run(inp, _FakeCtx()), retriever.run(inp, _FakeCtx()))

    started = time.perf_counter()
    asyncio.run(_run_two_concurrently())
    elapsed = time.perf_counter() - started
    assert elapsed < sleep_s * 1.6


def test_qdrant_sparse_bm25_retriever_hits_matching_record() -> None:
    dense_vector = [0.0] * 1023 + [1.0]
    record = _make_index_record(
        chunk_id=hash_of("chunk", "lex-hit"), index_text="apple banana cherry", dense=dense_vector
    )
    backend = _local_backend_with_record(record)
    plan = _load_plan()
    retriever = QdrantSparseBm25Retriever(backend=backend, tokenizer=WhitespaceTokenizer())
    inp = _adapter_channel_run_input(
        plan, "lexical", retriever.plugin_id, query_vectors=QueryVectors(), query_text="apple banana"
    )

    run = asyncio.run(retriever.run(inp, _FakeCtx()))

    assert run.status == "ok"
    assert run.returned == 1
    assert run.candidates[0].rank == 1


def test_qdrant_sparse_bm25_retriever_empty_query_is_empty_run_not_error() -> None:
    backend = QdrantIndexBackend.local()
    plan = _load_plan()
    retriever = QdrantSparseBm25Retriever(backend=backend, tokenizer=WhitespaceTokenizer())
    inp = _adapter_channel_run_input(plan, "lexical", retriever.plugin_id, query_vectors=QueryVectors(), query_text="")

    run = asyncio.run(retriever.run(inp, _FakeCtx()))

    assert run.status == "ok"
    assert run.returned == 0
    assert run.error is None


def test_qdrant_sparse_bm25_retriever_pins_to_channel_collection_id() -> None:
    """`qdrant_dense`와 같은 리뷰 지적(§13.4·§8.1) — lexical 런도 공유 물리 컬렉션에서 자기
    `channel.collection_id`만 반환해야 한다."""
    collection_a, collection_b = COLLECTION, str(ULID())
    dense_vector = [0.0] * 1023 + [1.0]
    backend = _shared_alias_backend_with_two_collections(
        collection_a=collection_a, collection_b=collection_b, index_text="apple banana cherry", dense=dense_vector
    )
    plan = _load_plan()
    retriever = QdrantSparseBm25Retriever(backend=backend, tokenizer=WhitespaceTokenizer())
    inp = _adapter_channel_run_input_pinned_to(
        plan,
        "lexical",
        retriever.plugin_id,
        query_vectors=QueryVectors(),
        query_text="apple banana",
        channel_collection_id=collection_a,
        security_collection_ids=[collection_a, collection_b],
        collection_alias=alias_name(collection_a),
    )

    run = asyncio.run(retriever.run(inp, _FakeCtx()))

    assert run.status == "ok"
    assert run.returned == 1  # 회귀 시 두 컬렉션 레코드가 모두 반환되어 2가 된다
    assert {c.collection_id.root for c in run.candidates} == {collection_a}


def test_qdrant_sparse_bm25_retriever_does_not_block_event_loop() -> None:
    """`qdrant_dense`와 같은 리뷰 지적(§8.1 7단계) — 동기 백엔드 호출이 이벤트 루프를 막지 않는다."""
    dense_vector = [0.0] * 1023 + [1.0]
    record = _make_index_record(chunk_id=hash_of("chunk", "slow-lex"), index_text="apple banana", dense=dense_vector)
    backend = _local_backend_with_record(record)
    sleep_s = 0.1

    class _SleepingBackend:
        """`search_sparse`가 동기적으로 오래 걸리는 백엔드 더블."""

        def search_sparse(self, *args: Any, **kwargs: Any) -> list[Any]:
            time.sleep(sleep_s)
            return backend.search_sparse(*args, **kwargs)

    plan = _load_plan()
    retriever = QdrantSparseBm25Retriever(backend=_SleepingBackend(), tokenizer=WhitespaceTokenizer())  # type: ignore[arg-type]
    inp = _adapter_channel_run_input(
        plan, "lexical", retriever.plugin_id, query_vectors=QueryVectors(), query_text="apple banana"
    )

    # `test_qdrant_dense_retriever_does_not_block_event_loop`과 같은 방식: 두 개를 동시에 돌려 총
    # 시간이 순차 실행(`2 * sleep_s`)이 아니라 병렬 실행(`sleep_s` 근처)인지로 판정한다.
    async def _run_two_concurrently() -> None:
        await asyncio.gather(retriever.run(inp, _FakeCtx()), retriever.run(inp, _FakeCtx()))

    started = time.perf_counter()
    asyncio.run(_run_two_concurrently())
    elapsed = time.perf_counter() - started
    assert elapsed < sleep_s * 1.6
