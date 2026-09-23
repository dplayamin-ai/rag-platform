"""후처리 `dedup` — 부모-흡수 자식·완전 중복·근중복을 순서대로 제거한다(1차·2차 호출 공용).

역할: 04-pipelines/17 §2.3(1차: 완전 중복 → 근중복 → MinHash 폴백)·§2.6(2차: 부모 확장이
흡수한 자식 제거 + 부모 간 근중복)을 하나의 함수로 구현한다. `parent_expand`가 자식을 부모로
바꾼 뒤에는 `expanded_from`을 보고 나머지 형제를 자동으로 지우므로, 같은 `apply`가 두 번
호출되어도(고정 순서 `dedup → mmr → parent_expand → dedup`) 각 호출에서 올바른 부분만 동작한다.
설계 근거: 04-pipelines/17 §2.3·§2.6, 바이블 §8.2. `content_hash`가 `RankedResult`에 없어
(계약 갭) `chunk_id`(콘텐츠 파생 키)를 완전 중복 판정에 대신 쓴다.
구성: `apply` — 부모-흡수 제거(`_split_parent_merged`) 후 근중복 그리디 제거(`_dedup_near`);
`_minhash_signature`/`_minhash_jaccard` — `num_perm`/`seed` 고정 근사 Jaccard(datasketch
미의존, 계수는 `blake3_hex` 결정적 파생 — `random` 미사용, 스테이지 결정성 유지).
불변식·주의: 반환 `results`는 입력 리스트의 원래 순서를 보존한다(대표 선택은 `final_rank`
오름차순 그리디, 재정렬 아님).
검증 계층: 1층(여기서 검증) — tests/retrieval/test_postprocess_pack.py.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any

from rag_platform.contracts import common_types
from rag_platform.contracts.ranked_set import RankedOmittedEntry, Reason
from rag_platform.retrieval.postprocess.relevance_gate import StepResult
from rag_platform.sdk.hashing import blake3_hex

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from rag_platform.contracts.common_types import RankedResult
    from rag_platform.sdk.ports import KoreanAnalyzer

__all__ = ["apply"]

_DEFAULT_NUM_PERM = 128
_DEFAULT_SEED = 42
_MERSENNE_PRIME = (1 << 61) - 1


def _root(value: Any) -> Any:
    """RootModel 래퍼(`Hex64`·`Ulid` 등)를 순수 값으로 벗긴다. 평범한 값은 그대로."""
    return value.root if hasattr(value, "root") else value


def _cosine(a: Sequence[float], b: Sequence[float]) -> float:
    """코사인 유사도. 둘 중 하나라도 영벡터면 0.0(무관계로 취급)."""
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def _shingles(text: str, analyzer: KoreanAnalyzer | None) -> set[str]:
    """형태소 분석기가 있으면 그 토큰을, 없으면 공백 분리 토큰을 shingle 집합으로 쓴다."""
    if analyzer is not None:
        return set(analyzer.tokenize(text))
    return set(text.split())


def _affine_coeffs(num_perm: int, seed: int) -> list[tuple[int, int]]:
    """`blake3_hex`로 결정적 아핀 계수 `(a, b)`를 파생한다(`random` 미사용, 셸 밖에서 비결정 금지)."""
    coeffs = []
    for i in range(num_perm):
        a = int(blake3_hex(f"minhash-a:{seed}:{i}"), 16) % (_MERSENNE_PRIME - 1) + 1
        b = int(blake3_hex(f"minhash-b:{seed}:{i}"), 16) % _MERSENNE_PRIME
        coeffs.append((a, b))
    return coeffs


def _minhash_signature(shingles: set[str], *, num_perm: int, seed: int) -> tuple[int, ...]:
    """`num_perm`개 아핀 해시의 최솟값 서명(`datasketch` affine 스킴의 단순 재현, 휴리스틱)."""
    if not shingles:
        return tuple(_MERSENNE_PRIME for _ in range(num_perm))
    hashed = [int(blake3_hex(s), 16) % _MERSENNE_PRIME for s in shingles]
    return tuple(min((a * h + b) % _MERSENNE_PRIME for h in hashed) for a, b in _affine_coeffs(num_perm, seed))


def _minhash_jaccard(sig_a: tuple[int, ...], sig_b: tuple[int, ...]) -> float:
    """두 MinHash 서명이 일치하는 슬롯 비율(근사 Jaccard)."""
    matches = sum(1 for x, y in zip(sig_a, sig_b, strict=True) if x == y)
    return matches / len(sig_a)


def _omit(
    r: RankedResult, reason: Reason, *, related_chunk_id: str | None, explain: list[common_types.ExplainCode] | None
) -> RankedOmittedEntry:
    return RankedOmittedEntry(
        chunk_id=r.chunk_id,
        collection_id=r.collection_id,
        document_id=r.document_id,
        reason=reason,
        step=common_types.PostprocessStep.dedup,
        related_chunk_id=common_types.Hex64(related_chunk_id) if related_chunk_id is not None else None,
        explain=explain,
    )


def _split_parent_merged(results: Sequence[RankedResult]) -> tuple[list[RankedResult], list[RankedOmittedEntry]]:
    """다른 항목의 `expanded_from`에 자기 `chunk_id`가 있는 항목(흡수된 자식)을 골라낸다(§2.6)."""
    absorbed_by: dict[str, str] = {}
    for r in results:
        if r.item_kind == common_types.ItemKind.parent and r.expanded_from:
            parent_chunk_id = _root(r.chunk_id)
            for child_id in r.expanded_from:
                absorbed_by[_root(child_id)] = parent_chunk_id

    survivors: list[RankedResult] = []
    omitted: list[RankedOmittedEntry] = []
    for r in results:
        parent_chunk_id = absorbed_by.get(_root(r.chunk_id))
        if parent_chunk_id is not None:
            omitted.append(_omit(r, Reason.parent_merged, related_chunk_id=parent_chunk_id, explain=None))
        else:
            survivors.append(r)
    return survivors, omitted


class _NearDupIndex:
    """완전 중복(`chunk_id`)·근중복(코사인/MinHash) 판정을 위한 그리디 대표 집합(§2.3)."""

    def __init__(
        self,
        stage1: Sequence[RankedResult],
        *,
        vectors: Mapping[str, Sequence[float]],
        cosine_threshold: float,
        minhash_threshold: float,
        num_perm: int,
        seed: int,
        analyzer: KoreanAnalyzer | None,
    ) -> None:
        self._stage1 = stage1
        self._vectors = vectors
        self._cosine_threshold = cosine_threshold
        self._minhash_threshold = minhash_threshold
        self._num_perm = num_perm
        self._seed = seed
        self._analyzer = analyzer
        self._minhash_cache: dict[int, tuple[int, ...]] = {}
        self.seen_chunk_id: dict[str, int] = {}
        self.kept_idx: list[int] = []
        self.dropped: set[int] = set()
        self.representative_of: dict[int, str] = {}

    def _minhash_of(self, idx: int) -> tuple[int, ...]:
        if idx not in self._minhash_cache:
            text = self._stage1[idx].text or ""
            shingles = _shingles(text, self._analyzer)
            self._minhash_cache[idx] = _minhash_signature(shingles, num_perm=self._num_perm, seed=self._seed)
        return self._minhash_cache[idx]

    def _is_near_dup(self, idx: int, other_idx: int) -> bool:
        r, other = self._stage1[idx], self._stage1[other_idx]
        record_a = _root(r.record_id) if r.record_id is not None else None
        record_b = _root(other.record_id) if other.record_id is not None else None
        if record_a is not None and record_b is not None and record_a in self._vectors and record_b in self._vectors:
            return _cosine(self._vectors[record_a], self._vectors[record_b]) >= self._cosine_threshold
        return self._minhash_jaccard_of(idx, other_idx) >= self._minhash_threshold

    def _minhash_jaccard_of(self, idx: int, other_idx: int) -> float:
        return _minhash_jaccard(self._minhash_of(idx), self._minhash_of(other_idx))

    def _drop(self, idx: int, representative_idx: int) -> None:
        self.dropped.add(idx)
        self.representative_of[idx] = _root(self._stage1[representative_idx].chunk_id)

    def process(self, idx: int) -> None:
        """`final_rank` 오름차순으로 호출한다. 대표(생존)면 등록, 중복이면 대표를 기록한다."""
        chunk_key = _root(self._stage1[idx].chunk_id)
        rep_idx = self.seen_chunk_id.get(chunk_key)
        if rep_idx is not None:
            self._drop(idx, rep_idx)
            return
        matched_rep = next((kidx for kidx in self.kept_idx if self._is_near_dup(idx, kidx)), None)
        if matched_rep is not None:
            self._drop(idx, matched_rep)
            return
        self.seen_chunk_id[chunk_key] = idx
        self.kept_idx.append(idx)


def _dedup_near(
    stage1: Sequence[RankedResult],
    *,
    vectors: Mapping[str, Sequence[float]],
    cosine_threshold: float,
    minhash_threshold: float,
    num_perm: int,
    seed: int,
    analyzer: KoreanAnalyzer | None,
) -> tuple[list[RankedResult], list[RankedOmittedEntry]]:
    """완전 중복(`chunk_id`) + 근중복(코사인/MinHash)을 상위 `final_rank`부터 그리디로 제거."""
    index = _NearDupIndex(
        stage1,
        vectors=vectors,
        cosine_threshold=cosine_threshold,
        minhash_threshold=minhash_threshold,
        num_perm=num_perm,
        seed=seed,
        analyzer=analyzer,
    )
    order = sorted(range(len(stage1)), key=lambda i: stage1[i].final_rank)
    for idx in order:
        index.process(idx)

    omitted = [
        _omit(
            stage1[idx],
            Reason.duplicate,
            related_chunk_id=index.representative_of[idx],
            explain=[common_types.ExplainCode.deduped],
        )
        for idx in order
        if idx in index.dropped
    ]
    kept_set = set(index.kept_idx)
    survivors = [stage1[i] for i in range(len(stage1)) if i in kept_set]
    return survivors, omitted


def apply(
    results: Sequence[RankedResult],
    *,
    vectors: Mapping[str, Sequence[float]] | None = None,
    cosine_threshold: float = 0.95,
    minhash_threshold: float = 0.8,
    num_perm: int = _DEFAULT_NUM_PERM,
    seed: int = _DEFAULT_SEED,
    analyzer: KoreanAnalyzer | None = None,
) -> StepResult:
    """부모-흡수 자식 → 완전 중복(`chunk_id`) → 근중복(코사인 있으면, 없으면 MinHash) 제거."""
    stage1, parent_merged_omitted = _split_parent_merged(results)
    survivors, dup_omitted = _dedup_near(
        stage1,
        vectors=vectors or {},
        cosine_threshold=cosine_threshold,
        minhash_threshold=minhash_threshold,
        num_perm=num_perm,
        seed=seed,
        analyzer=analyzer,
    )
    omitted = parent_merged_omitted + dup_omitted
    return StepResult(results=survivors, omitted=omitted, removed=len(omitted), added=0, degraded=[])
