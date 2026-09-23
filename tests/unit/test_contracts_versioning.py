"""`rag_platform.contracts.versioning` 단위 테스트 — `schema_version` 파싱·호환성 판정·업캐스터 레지스트리를 검증한다.

설계 근거: `docs/03-contracts/14-schema-versioning-and-compatibility.md` §1.2(`schema_version` 형식·
pre-release/build metadata 금지)·§4.2(생산자·소비자 호환 매트릭스 8행), 바이블 §6.4(콘텐츠 파생 키 규약).

구성:
- `SchemaVersion` 파싱·정렬, `compat_matcher` 범위 매칭 — 정상/기형 입력 각각 검증.
- `TestJudgeCompat` — §4.2 매트릭스의 행(row)마다 하나씩(`reject`/`load`/`upcast`/`load_tolerant`).
- `TestUpcasterRegistry` — 등록·`has_path`·중복 등록 거부.
- `TestVersionedEnvelope` — `schema_type`/`schema_version` 불일치·pre-release·미지정 필드 거부.
- `test_prune_unknown_*` — `additionalProperties` 여부에 따른 미지정 필드 정리(tolerant read) 동작.

검증 계층: 1층(여기서 검증).
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from rag_platform.contracts.versioning import (
    SchemaVersion,
    UpcasterRegistry,
    VersionedEnvelope,
    compat_matcher,
    judge_compat,
    prune_unknown,
)


def test_schema_version_parse_accepts_release_only() -> None:
    assert SchemaVersion.parse("1.2.3") == SchemaVersion(1, 2, 3)


def test_schema_version_parse_rejects_malformed_string() -> None:
    with pytest.raises(ValueError, match="schema_version format violation"):
        SchemaVersion.parse("not-a-version")


def test_schema_version_parse_rejects_pre_release_and_build_metadata() -> None:
    # Common Semver $def allows these; schema_version (03-contracts/14 §1.2, invariant 1) does not.
    with pytest.raises(ValueError, match="pre-release/build metadata"):
        SchemaVersion.parse("1.0.0-rc1")
    with pytest.raises(ValueError, match="pre-release/build metadata"):
        SchemaVersion.parse("1.0.0+build5")


def test_schema_version_ordering_is_major_minor_patch() -> None:
    assert SchemaVersion(1, 2, 0) < SchemaVersion(1, 10, 0)
    assert SchemaVersion(1, 0, 0) < SchemaVersion(2, 0, 0)


def test_compat_matcher_matches_versions_inside_the_range() -> None:
    matches = compat_matcher(">=1.0,<2.0")
    assert matches(SchemaVersion(1, 0, 0))
    assert matches(SchemaVersion(1, 9, 3))  # patch does not participate
    assert not matches(SchemaVersion(2, 0, 0))
    assert not matches(SchemaVersion(0, 9, 0))


def test_compat_matcher_rejects_malformed_range() -> None:
    with pytest.raises(ValueError, match="contracts_compat format violation"):
        compat_matcher(">=1,x<2.0")


class TestJudgeCompat:
    """03-contracts/14 §4.2 producer/consumer judgement matrix, one test per row."""

    consumer_version = SchemaVersion(1, 2, 0)
    contracts_compat = ">=1.0,<2.0"

    def _judge(
        self,
        ref_version: str,
        *,
        ref_type: str = "ParsedDocument",
        registry: UpcasterRegistry | None = None,
        tolerant_minor: bool = False,
    ) -> str:
        return judge_compat(
            ref_type,
            ref_version,
            "ParsedDocument",
            self.consumer_version,
            contracts_compat=self.contracts_compat,
            registry=registry or UpcasterRegistry(),
            tolerant_minor=tolerant_minor,
        )

    def test_row1_schema_type_mismatch_rejects(self) -> None:
        assert self._judge("1.0.0", ref_type="NormalizedDocument") == "reject"

    def test_row2_producer_major_ahead_rejects(self) -> None:
        assert self._judge("2.0.0") == "reject"

    def test_row3_producer_major_behind_upcasts_when_registered(self) -> None:
        registry = UpcasterRegistry()
        registry.register("ParsedDocument", 0)(lambda payload: payload)
        assert self._judge("0.5.0", registry=registry) == "upcast"

    def test_row4_producer_major_behind_rejects_without_upcaster(self) -> None:
        assert self._judge("0.5.0") == "reject"

    def test_row5_producer_outside_contracts_compat_rejects(self) -> None:
        # Same major as the consumer (1), but contracts_compat ">=1.3,<2.0" excludes minor 1 —
        # this must fail on the compat range itself, before any producer/consumer minor comparison.
        judged = judge_compat(
            "ParsedDocument",
            "1.1.0",
            "ParsedDocument",
            self.consumer_version,
            contracts_compat=">=1.3,<2.0",
            registry=UpcasterRegistry(),
        )
        assert judged == "reject"

    def test_row6_producer_minor_at_or_below_consumer_loads(self) -> None:
        assert self._judge("1.0.0") == "load"
        assert self._judge("1.2.0") == "load"

    def test_row7_producer_minor_ahead_rejects_by_default(self) -> None:
        assert self._judge("1.9.0") == "reject"

    def test_row7_producer_minor_ahead_loads_tolerant_when_opted_in(self) -> None:
        assert self._judge("1.9.0", tolerant_minor=True) == "load_tolerant"

    def test_row8_malformed_producer_version_rejects(self) -> None:
        assert self._judge("1.0.0-rc1") == "reject"


class TestUpcasterRegistry:
    def test_has_path_false_without_registration(self) -> None:
        registry = UpcasterRegistry()
        assert not registry.has_path("ParsedDocument", SchemaVersion(0, 5, 0), SchemaVersion(1, 0, 0))

    def test_register_and_upcast_bumps_schema_version(self) -> None:
        registry = UpcasterRegistry()

        @registry.register("ParsedDocument", 0)
        def upcast_0_to_1(payload: dict[str, object]) -> dict[str, object]:
            return {**payload, "new_field": "default"}

        assert registry.has_path("ParsedDocument", SchemaVersion(0, 5, 0), SchemaVersion(1, 0, 0))
        result = registry.upcast({"schema_type": "ParsedDocument", "schema_version": "0.5.0"}, SchemaVersion(1, 0, 0))
        assert result["schema_version"] == "1.0.0"
        assert result["new_field"] == "default"

    def test_duplicate_registration_raises(self) -> None:
        registry = UpcasterRegistry()
        registry.register("ParsedDocument", 0)(lambda payload: payload)
        with pytest.raises(ValueError, match="duplicate upcaster registration"):
            registry.register("ParsedDocument", 0)(lambda payload: payload)


class TestVersionedEnvelope:
    def test_accepts_matching_schema_type_and_version(self) -> None:
        class ParsedDocument(VersionedEnvelope):
            pass

        instance = ParsedDocument(schema_version="1.0.0", schema_type="ParsedDocument")
        assert instance.schema_version == "1.0.0"

    def test_rejects_schema_type_mismatch(self) -> None:
        class ParsedDocument(VersionedEnvelope):
            pass

        with pytest.raises(ValidationError, match=r"contract\.violation"):
            ParsedDocument(schema_version="1.0.0", schema_type="NotParsedDocument")

    def test_rejects_pre_release_schema_version(self) -> None:
        with pytest.raises(ValidationError):
            VersionedEnvelope(schema_version="1.0.0-rc1", schema_type="VersionedEnvelope")

    def test_rejects_unknown_fields(self) -> None:
        with pytest.raises(ValidationError):
            VersionedEnvelope(schema_version="1.0.0", schema_type="VersionedEnvelope", extra_field=1)


def test_prune_unknown_drops_only_unknown_optional_properties() -> None:
    schema = {
        "properties": {"kept": {"type": "string"}},
        "additionalProperties": False,
    }
    dropped: list[str] = []
    result = prune_unknown({"kept": "a", "unknown": "b"}, schema, {}, dropped)
    assert result == {"kept": "a"}
    assert dropped == ["/unknown"]


def test_prune_unknown_keeps_fields_when_additional_properties_allowed() -> None:
    schema = {"properties": {}, "additionalProperties": True}
    dropped: list[str] = []
    result = prune_unknown({"anything": 1}, schema, {}, dropped)
    assert result == {"anything": 1}
    assert dropped == []
