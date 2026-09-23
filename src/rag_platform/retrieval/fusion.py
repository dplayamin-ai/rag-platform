"""`fuse` 스테이지 — RRF(`k=60`, 채널 가중 1:1:1, 변형 0.5)로 `CandidateSet`을 `RankedSet(fused)`로 바꾼다.

역할: `CandidateSet.channel_runs[]`(`status=ok`만)을 record_id 단위로 누적해 `fused_score = Σ
contribution`을 계산하고((`-fused_score, record_id`) 정렬), 채널당 하나로 합친 `ScoreBreakdown`과
상위 `hydrate.top_n`의 `RankedSet(stage=fused, hydrated=false)`를 만든다. 순수 함수(I/O 없음, in_process).
설계 근거: 바이블 §4.3 `fuse` 행·§8.1 8단계·O-01, docs/04-pipelines/15 §6.1(`Fuser` 프로토콜)·§6.2(RRF
공식·의사코드 `fuse_rrf`/`emit_fused`), 계약 `RankedSet`/`ScoreBreakdown`(`contracts/ranked_set.py`,
`contracts/common_types`), `testing/fuser_equivalence.py`(§8.1의 "단순화된 어댑터 형태").
구성: `fuse_ranks` — §8.1 단순화 어댑터 형태 그대로(`testing.fuser_equivalence.assert_fuser_matches_rrf_golden`에
직접 꽂을 수 있는 순수 RRF 원장 계산); `fuse` — 실제 `CandidateSet` → `RankedSet(fused)` 변환(record_id별
`ScoreBreakdown` 조립 + min-max `final_score`); `RrfFuser` — `Stage[CandidateSet, RankedSet]` 5멤버
래퍼(`plugin_id="fuser.rrf"`).
불변식·주의: 이 WP는 RRF만 구현한다 — `convex_minmax`/`convex_zscore`/`dbsf`/`combmnz`·강등 판정
(`downgraded_from`)·`late_interaction_rerank` 순서 필터는 범위 밖이다(open_issues, §6.3·§6.4·§3.6).
Σ`contribution`(non-null 채널) = `fused_score` 불변식은 합산 방식 자체가 보장한다(가산 누적, 후처리로
재계산하지 않음). 결과 캐시 금지.
검증 계층: 1층(여기서 검증) — `tests/retrieval/test_fusion_channels.py`(`fuse_ranks` ↔
`tests/fixtures/fusion/rrf_3ch_5cand.json` 골든 동치성 포함).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC
from typing import TYPE_CHECKING, Any

from ulid import ULID

from rag_platform.contracts.common_types import (
    Capabilities,
    Channel,
    ChannelRunStatus,
    ChannelScore,
    ContractsCompat,
    ExplainCode,
    FusionMethod,
    IsolationMode,
    Producer,
    RankedStage,
    ScoreBreakdown,
    Ulid,
)
from rag_platform.contracts.ranked_set import FusionReport, FusionWeights, RankedSet, RankedSetStats, Result
from rag_platform.sdk.hashing import hash_of
from rag_platform.sdk.stage import StageError

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from datetime import datetime

    from rag_platform.contracts.candidate_set import Candidate, CandidateSet
    from rag_platform.contracts.query_plan import QueryPlan

__all__ = ["PLUGIN_ID", "PLUGIN_VERSION", "ChannelHit", "FusedCandidate", "RrfFuser", "fuse", "fuse_ranks"]

PLUGIN_ID = "fuser.rrf"
PLUGIN_VERSION = "0.1.0"
_CONTRACT_VIOLATION = "contract.violation"

_SINGLE_HIT_CODE: dict[str, ExplainCode] = {
    "dense": ExplainCode.dense_only_hit,
    "sparse": ExplainCode.sparse_only_hit,
    "lexical": ExplainCode.lexical_only_hit,
}


def _root_str(value: Any) -> str | None:
    """`RootModel`(`.root`)이든 평범한 `str`/`None`이든 같은 방식으로 문자열을 뽑는다(테스트 이중 대비)."""
    if value is None:
        return None
    root = getattr(value, "root", None)
    return root if isinstance(root, str) else str(value)


def _channel_str(value: Any) -> str:
    return str(getattr(value, "value", value))


def _rfc3339_ms(moment: datetime) -> str:
    utc = moment.astimezone(UTC)
    return utc.strftime("%Y-%m-%dT%H:%M:%S.") + f"{utc.microsecond // 1000:03d}Z"


@dataclass(frozen=True, slots=True)
class ChannelHit:
    """채널 하나의 원장 행 — 여러 변형 런이 같은 채널을 적중하면 채널당 하나로 합친 결과(§6.2)."""

    score: float | None
    rank: int | None
    contribution: float
    variant_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class FusedCandidate:
    """`fuse_rrf`(§6.2) 산출 행 하나 — record_id·`fused_score`·`fused_rank`·채널별 원장."""

    record_id: str
    fused_score: float
    fused_rank: int
    channels: Mapping[str, ChannelHit]


@dataclass(frozen=True, slots=True)
class _RunCandidate:
    record_id: str
    rank: int
    score: float | None = None


@dataclass(frozen=True, slots=True)
class _Run:
    channel: str
    candidates: tuple[_RunCandidate, ...]
    is_variant: bool = False
    variant_id: str | None = None


@dataclass
class _MutableChannelHit:
    score: float | None = None
    rank: int | None = None
    contribution: float = 0.0
    variant_ids: set[str] = field(default_factory=set)
    from_original: bool = False


def _fuse_runs(
    runs: Sequence[_Run], *, k: int, weights: Mapping[str, float], variant_query_weight: float
) -> list[FusedCandidate]:
    """§6.2 `fuse_rrf` 그대로: 채널별 `contribution = w_run / (k + rank)`을 record_id x 채널로 누적한다.

    같은 채널을 여러 변형 런이 적중하면 `contribution`은 합산, `score`/`rank`는 원 질의 런 우선(없으면
    최고 순위 런의 값, [10 §4.5]) — 처리 순서(runs의 순서)에 최종 결과가 의존하지 않는다.
    """
    buckets: dict[str, dict[str, _MutableChannelHit]] = {}
    for run in runs:
        channel_weight = float(weights.get(run.channel, 1.0))
        w_run = channel_weight * (variant_query_weight if run.is_variant else 1.0)
        is_original = not run.is_variant
        for candidate in run.candidates:
            contribution = w_run / (k + candidate.rank)
            bucket = buckets.setdefault(candidate.record_id, {})
            hit = bucket.get(run.channel)
            if hit is None:
                hit = _MutableChannelHit()
                bucket[run.channel] = hit
            hit.contribution += contribution
            if run.variant_id is not None:
                hit.variant_ids.add(run.variant_id)
            if is_original or (not hit.from_original and (hit.rank is None or candidate.rank < hit.rank)):
                hit.score, hit.rank = candidate.score, candidate.rank
                hit.from_original = hit.from_original or is_original

    fused_scores = {
        record_id: sum(hit.contribution for hit in bucket.values()) for record_id, bucket in buckets.items()
    }
    ordered = sorted(fused_scores, key=lambda record_id: (-fused_scores[record_id], record_id))
    result: list[FusedCandidate] = []
    for rank, record_id in enumerate(ordered, start=1):
        channels = {
            channel: ChannelHit(
                score=hit.score,
                rank=hit.rank,
                contribution=hit.contribution,
                variant_ids=tuple(sorted(hit.variant_ids)),
            )
            for channel, hit in buckets[record_id].items()
        }
        result.append(
            FusedCandidate(record_id=record_id, fused_score=fused_scores[record_id], fused_rank=rank, channels=channels)
        )
    return result


def fuse_ranks(
    channel_runs: Sequence[Any], *, k: int, weights: Mapping[str, float], variant_query_weight: float
) -> list[dict[str, Any]]:
    """§8.1 "단순화된 어댑터 형태" 구현.

    `channel_runs`(`.channel`, `.candidates[].record_id/.rank`, `.is_variant`)를 받아
    `record_id`/`fused_score`/`fused_rank`/`contributions`만 있는 매핑 목록을 낸다.
    `testing.fuser_equivalence.assert_fuser_matches_rrf_golden(fuse_ranks, golden)`에 그대로 꽂을 수
    있다 — 골든 벡터의 `ChannelRunVector`는 이 함수가 읽는 속성만 가진다.
    """
    runs = [
        _Run(
            channel=_channel_str(run.channel),
            is_variant=bool(getattr(run, "is_variant", False)),
            variant_id=_root_str(getattr(run, "variant_id", None)),
            candidates=tuple(
                _RunCandidate(record_id=_root_str(candidate.record_id) or "", rank=int(candidate.rank))
                for candidate in run.candidates
            ),
        )
        for run in channel_runs
    ]
    fused = _fuse_runs(runs, k=k, weights=dict(weights), variant_query_weight=variant_query_weight)
    return [
        {
            "record_id": item.record_id,
            "fused_score": item.fused_score,
            "fused_rank": item.fused_rank,
            "contributions": {channel: hit.contribution for channel, hit in item.channels.items()},
        }
        for item in fused
    ]


def _runs_from_candidate_set(cs: CandidateSet, *, original_variant_id: str | None) -> list[_Run]:
    runs = []
    for run in cs.channel_runs:
        if run.status != ChannelRunStatus.ok:
            continue
        variant_id = _root_str(run.variant_id)
        runs.append(
            _Run(
                channel=_channel_str(run.channel),
                is_variant=variant_id != original_variant_id,
                variant_id=variant_id,
                candidates=tuple(
                    _RunCandidate(
                        record_id=_root_str(candidate.record_id) or "", rank=candidate.rank, score=candidate.score
                    )
                    for candidate in run.candidates
                ),
            )
        )
    return runs


def _hit_code(channels_hit: Sequence[str]) -> ExplainCode | None:
    if len(channels_hit) > 1:
        return ExplainCode.multi_channel_hit
    if len(channels_hit) == 1:
        return _SINGLE_HIT_CODE.get(channels_hit[0])
    return None


def _score_breakdown(item: FusedCandidate, *, normalization: Any) -> ScoreBreakdown:
    per_channel: dict[str, ChannelScore | None] = dict.fromkeys(
        ("dense", "sparse", "lexical", "graph", "tree", "visual", "late_interaction"), None
    )
    for channel, hit in item.channels.items():
        if hit.score is None or hit.rank is None or channel not in per_channel:
            continue
        per_channel[channel] = ChannelScore(
            score=hit.score,
            rank=hit.rank,
            contribution=hit.contribution,
            variant_ids=[Ulid(v) for v in hit.variant_ids],
        )
    return ScoreBreakdown(
        dense=per_channel["dense"],
        sparse=per_channel["sparse"],
        lexical=per_channel["lexical"],
        graph=per_channel["graph"],
        tree=per_channel["tree"],
        visual=per_channel["visual"],
        late_interaction=per_channel["late_interaction"],
        fused=item.fused_score,
        fused_rank=item.fused_rank,
        rerank_raw=None,
        rerank_normalized=None,
        normalization=normalization,
        boosts=None,
    )


def fuse(cs: CandidateSet, plan: QueryPlan, *, now: datetime) -> RankedSet:
    """§6.2 `fuse_rrf` → `emit_fused` 그대로: `CandidateSet` → `RankedSet(stage=fused, hydrated=false)`.

    `plan.fusion`(`k`, `weights`, `variant_query_weight`)과 `plan.rewritten_queries[].weight`가 아니라
    `is_variant` 플래그(원 질의 여부)만 읽는다 — 변형 가중은 프로파일 고정값 `variant_query_weight`
    하나이며(§5.1 결정), 플래너가 이미 보정하지 않은 값을 그대로 쓴다.
    """
    if plan.fusion.method != FusionMethod.rrf:
        msg = f"fusion method {plan.fusion.method!r} not implemented in this WP (rrf only, WP-402 scope)"
        raise StageError(_CONTRACT_VIOLATION, stage="fuse", detail=msg)

    original_variant_id = _root_str(plan.query_id)
    runs = _runs_from_candidate_set(cs, original_variant_id=original_variant_id)
    weights = {channel: float(weight.root) for channel, weight in plan.fusion.weights.items()}
    fused = _fuse_runs(runs, k=plan.fusion.k, weights=weights, variant_query_weight=plan.fusion.variant_query_weight)

    candidates_by_id: dict[str, Candidate] = {}
    for run in cs.channel_runs:
        if run.status != ChannelRunStatus.ok:
            continue
        for run_candidate in run.candidates:
            candidates_by_id.setdefault(_root_str(run_candidate.record_id) or "", run_candidate)

    head = fused[: plan.hydrate.top_n]
    lo, hi = (head[-1].fused_score, head[0].fused_score) if head else (0.0, 0.0)

    results: list[Result] = []
    for item in head:
        candidate = candidates_by_id.get(item.record_id)
        if candidate is None:
            continue  # defensive: every fused record_id came from an ok channel_run's candidates
        channels_hit = tuple(sorted(item.channels))
        variant_ids = sorted({variant_id for hit in item.channels.values() for variant_id in hit.variant_ids})
        explain: list[ExplainCode] = []
        code = _hit_code(channels_hit)
        if code is not None:
            explain.append(code)
        final_score = 1.0 if len(head) == 1 or hi == lo else (item.fused_score - lo) / (hi - lo)
        results.append(
            Result(
                record_id=candidate.record_id,
                chunk_id=candidate.chunk_id,
                collection_id=candidate.collection_id,
                document_id=candidate.document_id,
                doc_version=candidate.doc_version,
                item_kind=candidate.item_kind,
                level=candidate.level,
                parent_chunk_id=candidate.parent_chunk_id,
                final_rank=len(results) + 1,
                final_score=final_score,
                fused_score=item.fused_score,
                fused_rank=item.fused_rank,
                score_breakdown=_score_breakdown(item, normalization=plan.rerank.normalization),
                channels_hit=[Channel(c) for c in channels_hit],
                variant_ids=[Ulid(v) for v in variant_ids],
                explain=explain,
            )
        )

    fusion_report = FusionReport(
        method=plan.fusion.method,
        k=plan.fusion.k,
        weights=FusionWeights(**weights),
        variant_query_weight=plan.fusion.variant_query_weight,
        candidates_in=cs.total_unique,
        candidates_out=len(results),
        downgraded_from=None,
    )
    config_hash = hash_of("config", json.dumps({"k": plan.fusion.k, "weights": weights}, sort_keys=True))
    return RankedSet(
        schema_version="1.0.0",
        schema_type="RankedSet",
        tenant_id=cs.tenant_id,
        collection_ids=cs.collection_ids,
        producer=Producer(
            plugin_id=PLUGIN_ID,
            plugin_version=PLUGIN_VERSION,
            config_hash=config_hash,
            image_digest=None,
            model_ids=None,
        ),
        warnings=[],
        degraded=list(cs.degraded),
        created_at=_rfc3339_ms(now),
        ranked_set_id=str(ULID()),
        plan_id=cs.plan_id,
        query_id=cs.query_id,
        candidate_set_id=cs.candidate_set_id,
        stage=RankedStage.fused,
        hydrated=False,
        fusion=fusion_report,
        rerank=None,
        late_interaction_rerank=None,
        relevance_gate=None,
        calibration_ref=None,
        postprocess_report=None,
        channel_runs=None,
        results=results,
        omitted=[],
        stats=RankedSetStats(n_in=cs.total_unique, n_out=len(results), hydrated_n=0, gate_passed=None),
        timings_ms=None,
    )


class RrfFuser:
    """`fuser.rrf` — `Stage[CandidateSet, RankedSet]` 5멤버 래퍼(ADR-0032)."""

    plugin_id = PLUGIN_ID
    requires_lineage: tuple[str, ...] = ()

    def config_hash(self) -> str:
        """설정이 없는 순수 함수라 고정 해시(§6.2 근사)."""
        return hash_of("config", "{}")

    def capabilities(self) -> Capabilities:
        """`isolation_modes=[in_process]`, 순수 함수라 재개 불필요, GPU 불필요."""
        return Capabilities(
            isolation_modes=[IsolationMode.in_process],
            supports_resumable=False,
            contracts_compat=ContractsCompat(">=1.0,<2.0"),
            input_formats=None,
            requires_gpu=False,
        )

    def fingerprint(self) -> str:
        """`H("producer", plugin_id, plugin_version, config_hash, "", "")`(모델 없음, 인프로세스)."""
        return hash_of("producer", self.plugin_id, PLUGIN_VERSION, self.config_hash(), "", "")

    async def run(self, inp: CandidateSet, ctx: Any) -> RankedSet:
        """`ctx.plan`(`QueryPlan`)과 `ctx.now()`를 읽어 :func:`fuse`를 호출한다(바이블 §4.1 `ctx.plan`)."""
        return fuse(inp, ctx.plan, now=ctx.now())
