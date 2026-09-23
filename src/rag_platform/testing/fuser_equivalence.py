"""`Fuser` 동치성 검사 — 임의 융합기 구현이 RRF 정본과 같은 점수를 내는지 골든 벡터로 확인한다.

역할: 적합성 키트 구성원. `fuse(...)`를 호출하는 어떤 구현이든 바이블 RRF 공식·타이브레이크와 동치인지 검사.
설계 근거: 바이블 §8.1 8단계·O-01(`contribution = w_run/(k+rank)`, `w_run = channel_weight x
(1.0 원 질의 | 0.5 변형)`, `fused_score = Σ contribution`, 정렬 `(-fused_score, record_id)`),
K3 점수 원장 불변식. 필드명은 `contracts/common_types`(`ChannelScore.contribution`,
`ScoreBreakdown.fused`)의 생성물을 따른다.
구성: `ChannelCandidate`/`ChannelRunVector`/`FusedRecord` — 경량 값 타입; `reference_rrf` — RRF
정본 구현; `load_golden_case` — 골든 벡터 로더; `assert_fuser_matches_rrf_golden` — 골든 자체
정합성 + 대상 `fuse` 결과(불변식·타이브레이크 포함)를 검사.
불변식·주의: `Fuser`는 `fuse(channel_runs, *, k, weights, variant_query_weight)`를 받아야
한다(§8.1의 단순화된 어댑터 형태). 결과 레코드는 속성/매핑 어느 쪽이든 구조적으로 받아들인다.
검증 계층: 1층 — `tests/unit/testing/test_fuser_equivalence.py`, 골든 벡터
`tests/fixtures/fusion/rrf_3ch_5cand.json`.
"""

from __future__ import annotations

import itertools
import json
import math
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

__all__ = [
    "ChannelCandidate",
    "ChannelRunVector",
    "FusedRecord",
    "GoldenFusionCase",
    "assert_fuser_matches_rrf_golden",
    "assert_score_ledger_invariant",
    "assert_tie_break_by_record_id",
    "load_golden_case",
    "reference_rrf",
]

_DEFAULT_REL_TOL = 1e-9
_DEFAULT_ABS_TOL = 1e-12


@dataclass(frozen=True, slots=True)
class ChannelCandidate:
    """단일 채널 런 안의 후보 한 개(`record_id`, 채널 내 1-based `rank`)."""

    record_id: str
    rank: int


@dataclass(frozen=True, slots=True)
class ChannelRunVector:
    """채널 런 하나(§8.1 8단계 "런 = 채널 x 컬렉션 x 변형"의 단순화 — 컬렉션은 생략)."""

    channel: str
    candidates: tuple[ChannelCandidate, ...]
    is_variant: bool = False


@dataclass(frozen=True, slots=True)
class FusedRecord:
    """융합 출력 한 행 — `RankedResult`(`fused_score`, `fused_rank`, `score_breakdown`)의 단순 투영."""

    record_id: str
    fused_score: float
    fused_rank: int
    contributions: Mapping[str, float]


@dataclass(frozen=True, slots=True)
class GoldenFusionCase:
    """`tests/fixtures/fusion/*.json` 골든 벡터 한 건(입력 채널 런 + 기대 융합 결과)."""

    k: int
    weights: Mapping[str, float]
    variant_query_weight: float
    channel_runs: tuple[ChannelRunVector, ...]
    expected: tuple[FusedRecord, ...]


FusedRecordLike = FusedRecord | Mapping[str, Any]
FuserCallable = Callable[..., Sequence[FusedRecordLike]]


def _field(record: FusedRecordLike, name: str) -> Any:
    """`record`가 매핑이든 속성 객체든 같은 방식으로 `name` 필드를 읽는다."""
    if isinstance(record, Mapping):
        return record[name]
    return getattr(record, name)


def reference_rrf(
    channel_runs: Sequence[ChannelRunVector],
    *,
    k: int = 60,
    weights: Mapping[str, float] | None = None,
    variant_query_weight: float = 0.5,
) -> list[FusedRecord]:
    """바이블 §8.1 8단계·O-01 공식대로 RRF를 계산한다: `Σ contribution` 내림차순, 동점은 `record_id` 오름차순."""
    resolved_weights: dict[str, float] = dict(weights) if weights else {}
    contributions: dict[str, dict[str, float]] = {}
    for run in channel_runs:
        channel_weight = resolved_weights.get(run.channel, 1.0)
        w_run = channel_weight * (variant_query_weight if run.is_variant else 1.0)
        for candidate in run.candidates:
            per_channel = contributions.setdefault(candidate.record_id, {})
            per_channel[run.channel] = per_channel.get(run.channel, 0.0) + w_run / (k + candidate.rank)
    fused_scores = {record_id: sum(per_channel.values()) for record_id, per_channel in contributions.items()}
    ordered = sorted(fused_scores, key=lambda record_id: (-fused_scores[record_id], record_id))
    return [
        FusedRecord(
            record_id=record_id,
            fused_score=fused_scores[record_id],
            fused_rank=rank,
            contributions=contributions[record_id],
        )
        for rank, record_id in enumerate(ordered, start=1)
    ]


def load_golden_case(path: Path) -> GoldenFusionCase:
    """`tests/fixtures/fusion/*.json` 골든 벡터 파일을 `GoldenFusionCase`로 읽어들인다."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    channel_runs = tuple(
        ChannelRunVector(
            channel=run["channel"],
            is_variant=bool(run.get("is_variant", False)),
            candidates=tuple(
                ChannelCandidate(record_id=candidate["record_id"], rank=candidate["rank"])
                for candidate in run["candidates"]
            ),
        )
        for run in payload["channel_runs"]
    )
    expected = tuple(
        FusedRecord(
            record_id=item["record_id"],
            fused_score=item["fused_score"],
            fused_rank=item["fused_rank"],
            contributions=dict(item["contributions"]),
        )
        for item in payload["expected"]
    )
    return GoldenFusionCase(
        k=payload["k"],
        weights=dict(payload["weights"]),
        variant_query_weight=payload["variant_query_weight"],
        channel_runs=channel_runs,
        expected=expected,
    )


def assert_score_ledger_invariant(
    records: Sequence[FusedRecordLike],
    *,
    rel_tol: float = _DEFAULT_REL_TOL,
    abs_tol: float = _DEFAULT_ABS_TOL,
) -> None:
    """K3 점수 원장 불변식 `Σ contribution = fused_score`가 각 레코드에서 성립하는지 검사한다."""
    for record in records:
        record_id = _field(record, "record_id")
        fused_score = float(_field(record, "fused_score"))
        contributions = _field(record, "contributions")
        total = sum(float(value) for value in contributions.values())
        if not math.isclose(total, fused_score, rel_tol=rel_tol, abs_tol=abs_tol):
            msg = f"score ledger invariant violated for {record_id!r}: sum={total!r} != fused_score={fused_score!r}"
            raise AssertionError(msg)


def assert_tie_break_by_record_id(
    records: Sequence[FusedRecordLike],
    *,
    rel_tol: float = _DEFAULT_REL_TOL,
    abs_tol: float = _DEFAULT_ABS_TOL,
) -> None:
    """정렬 규칙 `(-fused_score, record_id)`(§8.1 8단계)를 검사한다 — 동점은 `record_id` 오름차순."""
    for previous, current in itertools.pairwise(records):
        previous_score = float(_field(previous, "fused_score"))
        current_score = float(_field(current, "fused_score"))
        previous_id = str(_field(previous, "record_id"))
        current_id = str(_field(current, "record_id"))
        tied = math.isclose(previous_score, current_score, rel_tol=rel_tol, abs_tol=abs_tol)
        if tied:
            if previous_id >= current_id:
                msg = f"tie-break failed: {previous_id!r} must sort before {current_id!r} (equal fused_score)"
                raise AssertionError(msg)
        elif previous_score < current_score:
            msg = f"fused_score not descending: {previous_id!r}={previous_score!r} < {current_id!r}={current_score!r}"
            raise AssertionError(msg)


def _assert_records_equal(
    actual: Sequence[FusedRecordLike],
    expected: Sequence[FusedRecordLike],
    *,
    rel_tol: float,
    abs_tol: float,
) -> None:
    """`actual`(순서 포함)이 `expected`와 `record_id`·`fused_rank`·`fused_score`·기여분에서 일치하는지 검사한다."""
    if len(actual) != len(expected):
        msg = f"result length {len(actual)} != expected {len(expected)}"
        raise AssertionError(msg)
    for actual_record, expected_record in zip(actual, expected, strict=True):
        actual_id = str(_field(actual_record, "record_id"))
        expected_id = str(_field(expected_record, "record_id"))
        if actual_id != expected_id:
            msg = f"record_id order mismatch: got {actual_id!r}, expected {expected_id!r}"
            raise AssertionError(msg)
        actual_rank = int(_field(actual_record, "fused_rank"))
        expected_rank = int(_field(expected_record, "fused_rank"))
        if actual_rank != expected_rank:
            msg = f"{actual_id!r}: fused_rank {actual_rank} != expected {expected_rank}"
            raise AssertionError(msg)
        actual_score = float(_field(actual_record, "fused_score"))
        expected_score = float(_field(expected_record, "fused_score"))
        if not math.isclose(actual_score, expected_score, rel_tol=rel_tol, abs_tol=abs_tol):
            msg = f"{actual_id!r}: fused_score {actual_score!r} != expected {expected_score!r}"
            raise AssertionError(msg)
        actual_contributions = _field(actual_record, "contributions")
        expected_contributions = _field(expected_record, "contributions")
        if set(actual_contributions) != set(expected_contributions):
            msg = f"{actual_id!r}: channels {set(actual_contributions)} != expected {set(expected_contributions)}"
            raise AssertionError(msg)
        for channel, expected_value in expected_contributions.items():
            actual_value = float(actual_contributions[channel])
            if not math.isclose(actual_value, float(expected_value), rel_tol=rel_tol, abs_tol=abs_tol):
                msg = f"{actual_id!r}.{channel}: contribution {actual_value!r} != expected {expected_value!r}"
                raise AssertionError(msg)


def assert_fuser_matches_rrf_golden(
    fuse: FuserCallable,
    golden: GoldenFusionCase,
    *,
    rel_tol: float = _DEFAULT_REL_TOL,
    abs_tol: float = _DEFAULT_ABS_TOL,
) -> None:
    """`fuse(golden.channel_runs, k=..., weights=..., variant_query_weight=...)`가 골든 벡터와 동치인지 검사한다.

    먼저 `reference_rrf`로 골든 벡터 자체의 정합성을 확인한 뒤(픽스처 회귀 방지), 대상 `fuse`의 결과를
    골든 기대값과 대조하고 점수 원장 불변식·타이브레이크까지 검사한다.
    """
    reference = reference_rrf(
        golden.channel_runs, k=golden.k, weights=golden.weights, variant_query_weight=golden.variant_query_weight
    )
    _assert_records_equal(reference, golden.expected, rel_tol=rel_tol, abs_tol=abs_tol)

    actual = fuse(
        golden.channel_runs, k=golden.k, weights=golden.weights, variant_query_weight=golden.variant_query_weight
    )
    _assert_records_equal(actual, golden.expected, rel_tol=rel_tol, abs_tol=abs_tol)
    assert_score_ledger_invariant(actual, rel_tol=rel_tol, abs_tol=abs_tol)
    assert_tie_break_by_record_id(actual, rel_tol=rel_tol, abs_tol=abs_tol)
