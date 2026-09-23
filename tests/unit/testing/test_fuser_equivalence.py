"""`rag_platform.testing.fuser_equivalence` 단위 테스트 — RRF 정본 동치성 검사기 자체를 검증한다.

설계 근거: 바이블 §8.1 8단계·O-01(RRF `k=60`, 채널 가중 `1:1:1`, 변형 `0.5`, `Σcontribution=fused_score`,
타이브레이크 `record_id` 오름차순). 픽스처: `tests/fixtures/fusion/rrf_3ch_5cand.json`(채널 3개 x
후보 5개, `rec_04`/`rec_05` 동점 포함).

구성: `test_reference_rrf_matches_golden_expected` — `reference_rrf`가 골든 기대값과 일치.
`test_assert_fuser_matches_rrf_golden_accepts_conformant_fuser` — 정본과 동치인 임의 구현을 통과시킴.
`test_assert_fuser_matches_rrf_golden_rejects_wrong_k` — `k`를 어긴 구현을 거부.
`test_assert_score_ledger_invariant_detects_violation` — `Σcontribution != fused_score`를 검출.
`test_assert_tie_break_by_record_id_detects_violation` — 동점 타이브레이크 위반을 검출.
`test_assert_tie_break_by_record_id_detects_non_descending_scores` — 내림차순 위반을 검출.

불변식: 모든 결과의 `Σcontribution`은 `fused_score`와 오차 1e-9 이내로 일치해야 한다.
검증 계층: 1층(여기서 검증).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from rag_platform.testing.fuser_equivalence import (
    ChannelRunVector,
    FusedRecord,
    assert_fuser_matches_rrf_golden,
    assert_score_ledger_invariant,
    assert_tie_break_by_record_id,
    load_golden_case,
    reference_rrf,
)

_FIXTURE = Path(__file__).parents[2] / "fixtures" / "fusion" / "rrf_3ch_5cand.json"


def _golden() -> Any:
    return load_golden_case(_FIXTURE)


def test_reference_rrf_matches_golden_expected() -> None:
    golden = _golden()
    result = reference_rrf(
        golden.channel_runs, k=golden.k, weights=golden.weights, variant_query_weight=golden.variant_query_weight
    )
    assert [record.record_id for record in result] == [record.record_id for record in golden.expected]
    assert [record.fused_rank for record in result] == [record.fused_rank for record in golden.expected]
    for actual, expected in zip(result, golden.expected, strict=True):
        assert actual.fused_score == pytest.approx(expected.fused_score, rel=1e-9)


def test_reference_rrf_tie_break_orders_rec04_before_rec05() -> None:
    golden = _golden()
    result = reference_rrf(
        golden.channel_runs, k=golden.k, weights=golden.weights, variant_query_weight=golden.variant_query_weight
    )
    by_id = {record.record_id: record.fused_rank for record in result}
    assert by_id["rec_04"] < by_id["rec_05"]
    assert result[by_id["rec_04"] - 1].fused_score == pytest.approx(result[by_id["rec_05"] - 1].fused_score, rel=1e-9)


def test_assert_fuser_matches_rrf_golden_accepts_conformant_fuser() -> None:
    golden = _golden()

    def conformant_fuse(
        channel_runs: tuple[ChannelRunVector, ...],
        *,
        k: int,
        weights: dict[str, float],
        variant_query_weight: float,
    ) -> list[FusedRecord]:
        return reference_rrf(channel_runs, k=k, weights=weights, variant_query_weight=variant_query_weight)

    assert_fuser_matches_rrf_golden(conformant_fuse, golden)


def test_assert_fuser_matches_rrf_golden_accepts_mapping_records() -> None:
    """구현이 dataclass 대신 매핑(dict)을 반환해도 구조적으로 받아들여야 한다."""
    golden = _golden()

    def dict_fuse(
        channel_runs: tuple[ChannelRunVector, ...],
        *,
        k: int,
        weights: dict[str, float],
        variant_query_weight: float,
    ) -> list[dict[str, Any]]:
        records = reference_rrf(channel_runs, k=k, weights=weights, variant_query_weight=variant_query_weight)
        return [
            {
                "record_id": r.record_id,
                "fused_score": r.fused_score,
                "fused_rank": r.fused_rank,
                "contributions": dict(r.contributions),
            }
            for r in records
        ]

    assert_fuser_matches_rrf_golden(dict_fuse, golden)


def test_assert_fuser_matches_rrf_golden_rejects_wrong_k() -> None:
    golden = _golden()

    def wrong_k_fuse(
        channel_runs: tuple[ChannelRunVector, ...],
        *,
        k: int,
        weights: dict[str, float],
        variant_query_weight: float,
    ) -> list[FusedRecord]:
        del k
        return reference_rrf(channel_runs, k=1, weights=weights, variant_query_weight=variant_query_weight)

    with pytest.raises(AssertionError, match="fused_score"):
        assert_fuser_matches_rrf_golden(wrong_k_fuse, golden)


def test_assert_score_ledger_invariant_detects_violation() -> None:
    broken = [FusedRecord(record_id="r1", fused_score=1.0, fused_rank=1, contributions={"dense": 0.4})]
    with pytest.raises(AssertionError, match="score ledger invariant"):
        assert_score_ledger_invariant(broken)


def test_assert_tie_break_by_record_id_detects_violation() -> None:
    broken = [
        FusedRecord(record_id="rec_b", fused_score=0.5, fused_rank=1, contributions={"dense": 0.5}),
        FusedRecord(record_id="rec_a", fused_score=0.5, fused_rank=2, contributions={"dense": 0.5}),
    ]
    with pytest.raises(AssertionError, match="tie-break"):
        assert_tie_break_by_record_id(broken)


def test_assert_tie_break_by_record_id_detects_non_descending_scores() -> None:
    broken = [
        FusedRecord(record_id="rec_a", fused_score=0.4, fused_rank=1, contributions={"dense": 0.4}),
        FusedRecord(record_id="rec_b", fused_score=0.5, fused_rank=2, contributions={"dense": 0.5}),
    ]
    with pytest.raises(AssertionError, match="not descending"):
        assert_tie_break_by_record_id(broken)


def test_load_golden_case_reads_fixture_shape() -> None:
    golden = _golden()
    assert golden.k == 60
    assert golden.variant_query_weight == pytest.approx(0.5)
    assert len(golden.channel_runs) == 3
    assert all(len(run.candidates) == 5 for run in golden.channel_runs)
    assert len(golden.expected) == 7
