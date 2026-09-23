"""`pack` 조립기 — `acl_recheck→budget_cut→reorder→citation_align` 고정 순서 + 충분성/해시 확정.

역할: `RankedSet(stage=postprocessed)`를 받아 pack 내부 4단계(문서 04-pipelines/17 §3.2~§3.5)를
순서대로 호출하고, 전용 모듈이 이 배치에 없는 `sufficiency`(§3.6)·`content_hash`(§3.7)를 여기서
인라인으로 계산해 `ContextPack`을 만든다.
설계 근거: 04-pipelines/17 §5(전체 흐름 의사코드 `pack()`), 바이블 §9.1(pack 고정 순서)·§5.5
(`ContextPack` 필드 표). `QueryPlan`/`Profile` 계약은 읽기 예산 밖이므로 `PackConfig`(이 문서
제안, WP-403 §0)가 그 대역이다 — 실 배선은 F4 배치 검증자가 맡는다.
구성: `PackConfig` — pack 실행에 필요한 원시 설정 묶음; `pack(ranked, cfg, now=...)` — 4단계
조립 + `sufficiency`/`redaction_summary`/`classification_max`/`content_hash`/`diagnostics`.
불변식·주의: 4단계는 항상 전부 실행한다(부분열 불가, §9.1). `content_hash`는 `items`에서
`acl.checked_at`만 제거한 뷰로 계산한다(CR-16). `retrieval`은 `storage`/`security`/`ledger`를
import하지 않는다(import-linter `layers`).
검증 계층: 1층(여기서 검증) — tests/retrieval/test_postprocess_pack.py.
"""

from __future__ import annotations

import json
import time
import unicodedata
from dataclasses import dataclass, field
from datetime import UTC
from typing import TYPE_CHECKING, Any

from rag_platform.contracts import common_types
from rag_platform.contracts.context_pack import (
    Budget,
    ContextPack,
    Diagnostics,
    FiltersApplied,
    IndexGenerationsSeenItem,
    LatencyMs,
    MissingAspect,
    Ordering,
    PackOmittedEntry,
    PackStep,
    PackStep2,
    PackStep3,
    PackStep4,
    RedactionSummary,
    StopSignal,
    Sufficiency,
    TokenizerSpec,
)
from rag_platform.retrieval.pack import acl_recheck, budget_cut, citation_align, reorder
from rag_platform.sdk.hashing import hash_of

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence
    from datetime import datetime

    from rag_platform.contracts.common_types import RankedResult, SecurityContext
    from rag_platform.contracts.context_pack import RenderHints
    from rag_platform.contracts.ranked_set import RankedSet
    from rag_platform.retrieval.pack.acl_recheck import RevocationHint
    from rag_platform.sdk.ports import TokenCounter

__all__ = ["PackConfig", "pack"]

_CLASSIFICATION_ORDER: tuple[common_types.Classification, ...] = tuple(common_types.Classification)


def _root(value: Any) -> Any:
    """RootModel 래퍼(`Hex64`·`Ulid` 등)를 순수 값으로 벗긴다. 평범한 값은 그대로."""
    return value.root if hasattr(value, "root") else value


def _canonical_json(data: Any) -> str:
    """정렬 키·구분자 고정 JSON(바이블 §6.2 근사) — `H()` 조합 해시 입력."""
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _rfc3339_ms(moment: datetime) -> str:
    """바이블 §6.3 정본 표기(밀리초 정밀도, `Z` 접미)."""
    utc = moment.astimezone(UTC)
    return utc.strftime("%Y-%m-%dT%H:%M:%S.") + f"{utc.microsecond // 1000:03d}Z"


@dataclass(frozen=True)
class PackConfig:
    """`QueryPlan.pack`/`SecurityContext` 대역(WP-403 §0) — 이 배치는 `QueryPlan`을 읽지 않는다."""

    security: SecurityContext
    token_counter: TokenCounter
    budget_cut: budget_cut.BudgetCutConfig
    ordering_strategy: common_types.OrderingStrategy
    tokenizer: TokenizerSpec
    count_method: common_types.CountMethod
    render_hints: RenderHints
    profile_id: str
    profile_hash: str
    trace_id: str
    producer: common_types.Producer
    pack_id: str
    calibration_ratio: float | None = None
    safety_margin: float = 0.1
    explain: bool = False
    revocation_hints: Mapping[str, RevocationHint] | None = None
    risk_flagged: Callable[[RankedResult], bool] | None = None
    total_variant_ids: Sequence[str] = field(default_factory=tuple)
    lexical_terms: Sequence[str] = field(default_factory=tuple)
    filters_applied: FiltersApplied | None = None
    latency_ms_upstream: Mapping[str, int] | None = None
    index_generations_seen: Sequence[int] = field(default_factory=tuple)
    route_no_retrieval: bool = False
    count_method_fallback: bool = False
    confidence_high: float = 0.7
    confidence_medium: float = 0.4


def _elapsed_ms(t0: float) -> int:
    return max(0, round((time.monotonic() - t0) * 1000))


def _project_omitted(entries: Sequence[Any]) -> list[PackOmittedEntry]:
    return [
        PackOmittedEntry(
            chunk_id=e.chunk_id,
            collection_id=e.collection_id,
            document_id=e.document_id,
            reason=common_types.OmitReason(_root(e.reason)),
        )
        for e in entries
    ]


def _default_filters_applied(ranked: RankedSet, security: SecurityContext) -> FiltersApplied:
    security_filter = common_types.SecurityFilter(
        tenant_id=ranked.tenant_id,
        collection_ids=ranked.collection_ids,
        principals=security.principals,
        visible_set=security.visible_set,
        as_of=security.as_of,
        is_current=True,
        classification_max=security.classification_max,
    )
    strategy_filter = common_types.StrategyFilter(
        level_in=[common_types.ChunkLevel.integer_0], item_kinds=[common_types.ItemKind.text]
    )
    payload = {
        "security": security_filter.model_dump(mode="json"),
        "strategy": strategy_filter.model_dump(mode="json"),
        "user": None,
        "self_query": None,
    }
    effective_hash = hash_of("filters", _canonical_json(payload))
    return FiltersApplied(
        security=security_filter, strategy=strategy_filter, user=None, self_query=None, effective_hash=effective_hash
    )


def _confidence_tier(score: float, *, high: float, medium: float) -> common_types.ConfidenceTier:
    if score >= high:
        return common_types.ConfidenceTier.high
    if score >= medium:
        return common_types.ConfidenceTier.medium
    return common_types.ConfidenceTier.low


def _sufficiency(
    ranked: RankedSet,
    kept: Sequence[budget_cut.PackedItem],
    cfg: PackConfig,
) -> Sufficiency:
    if cfg.route_no_retrieval:
        status = common_types.SufficiencyStatus.not_needed
    elif ranked.relevance_gate is not None and ranked.relevance_gate.passed:
        status = common_types.SufficiencyStatus.sufficient
    elif ranked.relevance_gate is not None and not ranked.relevance_gate.passed:
        status = common_types.SufficiencyStatus.insufficient
    elif ranked.rerank is None or not ranked.rerank.applied:
        status = common_types.SufficiencyStatus.unknown
    else:
        status = common_types.SufficiencyStatus.sufficient if kept else common_types.SufficiencyStatus.insufficient

    hit_variants: set[str] = set()
    hit_terms: set[str] = set()
    total_variants = set(cfg.total_variant_ids)
    for p in kept:
        for v in p.result.variant_ids:
            root_v = _root(v)
            if root_v in total_variants:
                hit_variants.add(root_v)
        norm_text = unicodedata.normalize("NFC", p.result.text or "")
        for term in cfg.lexical_terms:
            if unicodedata.normalize("NFC", term) in norm_text:
                hit_terms.add(term)
    total = len(total_variants) + len(cfg.lexical_terms)
    coverage = (len(hit_variants) + len(hit_terms)) / total if total > 0 else (1.0 if kept else 0.0)
    scores = [p.result.final_score for p in kept]
    confidence = _confidence_tier(max(scores, default=0.0), high=cfg.confidence_high, medium=cfg.confidence_medium)
    missing = [term for term in cfg.lexical_terms if term not in hit_terms]
    missing += [v for v in cfg.total_variant_ids if v not in hit_variants]
    return Sufficiency(
        status=status,
        coverage=coverage,
        confidence=confidence,
        missing_aspects=[MissingAspect(m) for m in missing],
        method=common_types.SufficiencyMethod.rule,
    )


def _stop_signal(suff: Sufficiency) -> StopSignal:
    reason = f"sufficiency.status={suff.status.value}; confidence={suff.confidence.value}"
    sufficient = suff.status == common_types.SufficiencyStatus.sufficient
    return StopSignal(sufficient=sufficient, coverage_estimate=suff.coverage, reason=reason)


def _redaction_summary(kept: Sequence[budget_cut.PackedItem]) -> RedactionSummary:
    policy = next((p.result.pii_policy_applied for p in kept if p.result.pii_policy_applied is not None), None)
    return RedactionSummary(pii_policy=policy or common_types.PiiPolicy.keep, entity_counts={})


def _classification_max(items: Sequence[common_types.ContextItem]) -> common_types.Classification:
    if not items:
        return common_types.Classification.public
    return max((i.acl.classification for i in items), key=_CLASSIFICATION_ORDER.index)


def _content_hash(items: Sequence[common_types.ContextItem]) -> str:
    dumped = []
    for i in items:
        d = i.model_dump(mode="json")
        acl = d.get("acl")
        if isinstance(acl, dict):
            acl.pop("checked_at", None)
        dumped.append(d)
    return hash_of("pack", _canonical_json(dumped))


def pack(ranked: RankedSet, cfg: PackConfig, *, now: datetime) -> ContextPack:
    """문서 §5 `pack(ranked, plan, ctx)`의 구현(`plan`/`ctx`는 `cfg`로 대역)."""
    steps: list[Any] = []

    risk_flagged = cfg.risk_flagged or (lambda _r: False)
    candidates: list[RankedResult] = []
    risk_omitted: list[PackOmittedEntry] = []
    for r in ranked.results:
        if risk_flagged(r):
            risk_omitted.append(
                PackOmittedEntry(
                    chunk_id=r.chunk_id,
                    collection_id=r.collection_id,
                    document_id=r.document_id,
                    reason=common_types.OmitReason.risk_flagged,
                )
            )
        else:
            candidates.append(r)
    omitted = _project_omitted(ranked.omitted or []) + risk_omitted

    t0 = time.monotonic()
    passed, denied, acl_report, acl2_by_chunk_id = acl_recheck.apply(
        candidates, cfg.security, revocation_hints=cfg.revocation_hints
    )
    omitted += denied
    steps.append(PackStep(step="acl_recheck", removed=len(denied), took_ms=_elapsed_ms(t0)))

    t0 = time.monotonic()
    packed, cut, warnings = budget_cut.apply(passed, cfg.budget_cut, cfg.token_counter, acl2_by_chunk_id)
    omitted += cut
    steps.append(PackStep2(step="budget_cut", removed=len(cut), took_ms=_elapsed_ms(t0)))

    t0 = time.monotonic()
    reordered, applied_flag = reorder.apply(packed, cfg.ordering_strategy)
    steps.append(PackStep3(step="reorder", removed=0, took_ms=_elapsed_ms(t0)))

    t0 = time.monotonic()
    as_of = _root(cfg.security.as_of)
    items, warnings2 = citation_align.apply(reordered, as_of=as_of, include_scores=cfg.explain)
    steps.append(PackStep4(step="citation_align", removed=0, took_ms=_elapsed_ms(t0)))

    items = sorted(items, key=lambda i: i.position)
    suff = _sufficiency(ranked, packed, cfg)
    filters_applied = cfg.filters_applied or _default_filters_applied(ranked, cfg.security)
    upstream = cfg.latency_ms_upstream or {}
    latency_ms = LatencyMs(
        plan=upstream.get("plan", 0),
        retrieve=upstream.get("retrieve", 0),
        fuse=upstream.get("fuse", 0),
        hydrate=upstream.get("hydrate", 0),
        rerank=upstream.get("rerank", 0),
        postprocess=upstream.get("postprocess", 0),
        pack=sum(s.took_ms for s in steps),
    )
    parent_expansions = 0
    if ranked.postprocess_report is not None:
        parent_expansions = sum(
            s.added for s in ranked.postprocess_report.steps if s.step == common_types.PostprocessStep.parent_expand
        )
    diagnostics = Diagnostics(
        dedup_removed=sum(1 for o in omitted if o.reason == common_types.OmitReason.duplicate),
        parent_expansions=parent_expansions,
        mmr_lambda=None,
        filters_applied=filters_applied,
        latency_ms=latency_ms,
        index_generations_seen=[IndexGenerationsSeenItem(g) for g in cfg.index_generations_seen],
        count_method_fallback=cfg.count_method_fallback,
        pack_steps=tuple(steps),
        acl_recheck=acl_report,
    )
    budget = Budget(
        tokenizer=cfg.tokenizer,
        count_method=cfg.count_method,
        calibration_ratio=cfg.calibration_ratio,
        safety_margin=cfg.safety_margin,
        max_context_tokens=cfg.budget_cut.max_context_tokens,
        used_tokens=sum(i.token_count for i in items),
        reserved_answer_tokens=cfg.budget_cut.reserved_answer_tokens,
        k_max=cfg.budget_cut.k_max,
        overflow_policy=list(cfg.budget_cut.overflow_policy),
    )
    return ContextPack(
        schema_version="1.0.0",
        schema_type="ContextPack",
        tenant_id=ranked.tenant_id,
        collection_ids=ranked.collection_ids,
        producer=cfg.producer,
        warnings=[*warnings, *warnings2],
        degraded=list(ranked.degraded),
        created_at=_rfc3339_ms(now),
        pack_id=cfg.pack_id,
        query_id=ranked.query_id,
        plan_id=ranked.plan_id,
        profile_id=cfg.profile_id,
        profile_hash=cfg.profile_hash,
        trace_id=cfg.trace_id,
        budget=budget,
        ordering=Ordering(strategy=cfg.ordering_strategy, applied=applied_flag),
        items=items,
        omitted=omitted,
        sufficiency=suff,
        stop_signal=_stop_signal(suff),
        compression=None,
        redaction_summary=_redaction_summary(packed),
        classification_max=_classification_max(items),
        render_hints=cfg.render_hints,
        explain=None,
        diagnostics=diagnostics,
        truncated=None,
        next_cursor=None,
        content_hash=_content_hash(items),
    )
