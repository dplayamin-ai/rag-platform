"""후처리 1단계 `relevance_gate` — 관련도가 낮은 결과를 잘라내고 `RelevanceGateReport`를 만든다.

역할: `RankedSet(reranked)`의 `results[]` 중 `final_score < tau`인 항목만 제거한다(문서
04-pipelines/17 §2.2). 통과 여부(`passed = max(final_score) >= tau`)는 이후 `sufficiency`
판정(§3.6)의 근거가 된다.
설계 근거: 04-pipelines/17 §2.2·§2.1(`StepResult` 제안), 바이블 §8.2(후처리 고정 순서 1번째),
계약 `contracts/ranked_set.RelevanceGateReport`/`RankedOmittedEntry`.
구성: `StepResult` — 이 배치의 후처리 4개 모듈이 공유하는 반환 타입(문서 제안 `StepResult`의
구현, `dedup`/`mmr`/`parent_expand`가 이 모듈에서 import); `apply` — 게이트 실행.
불변식·주의: `results`의 리스트 순서는 정본이므로 필터링만 하고 재정렬하지 않는다.
`final_rank`/`fused_rank`/`score_breakdown`은 건드리지 않는다(K3, ADR-0030). `tau` 캘리브레이션
(컬렉션 `calibration_ref`)은 호출자가 이미 반영한 값을 넘긴다고 가정한다.
검증 계층: 1층(여기서 검증) — tests/retrieval/test_postprocess_pack.py.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from rag_platform.contracts import common_types
from rag_platform.contracts.ranked_set import RankedOmittedEntry, Reason, RelevanceGateReport

if TYPE_CHECKING:
    from collections.abc import Sequence

    from rag_platform.contracts.common_types import DegradedEntry, RankedResult

__all__ = ["StepResult", "apply"]


@dataclass(frozen=True)
class StepResult:
    """04-pipelines/17 §2.1 `StepResult` 제안의 구현 — 후처리 단계 4개가 공유하는 반환 모양.

    `results`는 갱신된(정본) 순서, `omitted`는 이 단계가 뺀 항목, `gate`는 `relevance_gate`만
    채운다(다른 단계는 `None`).
    """

    results: list[RankedResult]
    omitted: list[RankedOmittedEntry]
    removed: int
    added: int
    degraded: list[DegradedEntry]
    gate: RelevanceGateReport | None = None


def apply(results: Sequence[RankedResult], *, tau: float, retries: int = 0) -> StepResult:
    """`final_score < tau`인 항목을 제거하고 `RelevanceGateReport`를 계산한다(문서 §2.2).

    입력이 비어 있으면 `max_score = 0`(문서 §2.2), 따라서 `tau > 0`이면 `passed=False`.
    """
    max_score = max((r.final_score for r in results), default=0.0)
    passed = max_score >= tau
    kept: list[RankedResult] = []
    omitted: list[RankedOmittedEntry] = []
    for r in results:
        if r.final_score >= tau:
            kept.append(r)
            continue
        explain = list(dict.fromkeys([*r.explain, common_types.ExplainCode.below_gate]))
        omitted.append(
            RankedOmittedEntry(
                chunk_id=r.chunk_id,
                collection_id=r.collection_id,
                document_id=r.document_id,
                reason=Reason.below_threshold,
                step=common_types.PostprocessStep.relevance_gate,
                related_chunk_id=None,
                explain=explain,
            )
        )
    gate = RelevanceGateReport(tau=tau, max_score=max_score, passed=passed, retries=retries)
    return StepResult(results=kept, omitted=omitted, removed=len(omitted), added=0, degraded=[], gate=gate)
