"""후처리 `mmr` — Maximal Marginal Relevance로 `results`를 재정렬만 한다(제거 없음).

역할: `argmax_{d∉S} λ·rel_norm(d) - (1-λ)·max_{s∈S} cos(d,s)`(문서 04-pipelines/17 §2.4)로
문서 다양성을 준다. 관련도는 현재 `results`의 `final_score` min-max, 코사인은 `dedup`이 이미
확보한 dense 벡터를 재사용한다(재조회 없음).
설계 근거: 04-pipelines/17 §2.4 의사코드(Carbonell & Goldstein 1998), 바이블 §8.2(후처리
고정 순서 3번째).
구성: `apply` — 문서 의사코드를 그대로 옮긴 것(길이 ≤2 또는 `lam` 미설정/1.0 이상이면 무변경).
불변식·주의: `results`를 제거하지 않고 순서만 바꾼다. 순위가 내려간 항목에만
`explain += mmr_demoted`(중복 추가 금지). 벡터가 없는 항목(`record_id is None`이거나
`vectors`에 없음)은 유사도 0으로 취급해 페널티를 주지 않는다(휴리스틱).
검증 계층: 1층(여기서 검증) — tests/retrieval/test_postprocess_pack.py.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any

from rag_platform.contracts import common_types
from rag_platform.retrieval.postprocess.relevance_gate import StepResult

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from rag_platform.contracts.common_types import RankedResult

__all__ = ["apply"]

_MIN_ITEMS_FOR_DIVERSITY = 2


def _root(value: Any) -> Any:
    """RootModel 래퍼(`Hex64`·`Ulid` 등)를 순수 값으로 벗긴다. 평범한 값은 그대로."""
    return value.root if hasattr(value, "root") else value


def _cosine(a: Sequence[float], b: Sequence[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def apply(
    results: Sequence[RankedResult],
    vectors: Mapping[str, Sequence[float]] | None,
    lam: float | None,
) -> StepResult:
    """문서 §2.4 `mmr(results, vectors, lam)`를 `StepResult`로 감싼 구현."""
    if lam is None or len(results) <= _MIN_ITEMS_FOR_DIVERSITY or lam >= 1.0:
        return StepResult(results=list(results), omitted=[], removed=0, added=0, degraded=[])

    vectors = vectors or {}
    scores = [r.final_score for r in results]
    lo, hi = min(scores), max(scores)

    def rel(r: RankedResult) -> float:
        return 1.0 if hi == lo else (r.final_score - lo) / (hi - lo)

    def vec_of(r: RankedResult) -> Sequence[float] | None:
        if r.record_id is None:
            return None
        return vectors.get(_root(r.record_id))

    remaining = list(results)
    selected: list[RankedResult] = []
    while remaining:

        def sort_key(d: RankedResult) -> tuple[float, int]:
            vd = vec_of(d)
            max_sim = 0.0
            if vd is not None:
                sims = [_cosine(vd, vs) for s in selected if (vs := vec_of(s)) is not None]
                max_sim = max(sims, default=0.0)
            return (lam * rel(d) - (1 - lam) * max_sim, -d.final_rank)

        best = max(remaining, key=sort_key)
        selected.append(best)
        remaining.remove(best)

    for new_rank, r in enumerate(selected, start=1):
        if new_rank > r.final_rank and common_types.ExplainCode.mmr_demoted not in r.explain:
            r.explain.append(common_types.ExplainCode.mmr_demoted)
    return StepResult(results=selected, omitted=[], removed=0, added=0, degraded=[])
