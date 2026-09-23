"""`rag_platform.testing.conformance.base` 믹스인 자체의 동작을 검증한다(적합성 키트를 테스트하는 테스트).

검증 대상: `StageConformanceBase`(`PluginMetaConformance`/`StageErrorCatalogConformance`/
`StageSignatureConformance`/`ContractRoundtripConformance`/`IdempotencyConformance`)가 통과해야
할 사례(최소 더미 `Stage`, `_EchoStage`)에서 실제로 통과하고, 실패해야 할 사례(잘못된
`license_grade`/`extension_point`)에서 실제로 `AssertionError`를 내는지 확인한다.
설계 근거: ADR-0032, `docs/10-development/06-plugin-development-guide.md` §3.1(5멤버 표)·
§3.3(오류)·§8.2(golden 정규화 제외 필드).
구성: 통과해야 할 더미 `Stage`/`_EchoStage` 픽스처, 실패해야 할 잘못된 `license_grade`/
`extension_point` 픽스처, 각 믹스인별 assert 케이스.
불변식: 적합성 기반 클래스는 올바른 구현에서 거짓 실패(false negative)를, 잘못된 구현에서 거짓
통과(false positive)를 내지 않는다.
검증 계층: 1층(여기서 검증).
"""

from __future__ import annotations

from typing import Any, ClassVar

import pytest
from pydantic import BaseModel, ConfigDict

from rag_platform.contracts import common_types
from rag_platform.sdk.hashing import hash_of
from rag_platform.testing.conformance.base import StageConformanceBase, normalize_for_comparison

_VALID_META: dict[str, Any] = {
    "plugin_id": "chunker.fixed_window",
    "extension_point": "chunker",
    "version": "1.0.0",
    "license": "Apache-2.0",
    "license_grade": "A",
    "territory": ["KR"],
    "linkage": "pure_python",
    "isolation_supported": ["in_process"],
    "contracts_compat": ">=1.0,<2.0",
    "capabilities": {
        "isolation_modes": ["in_process"],
        "supports_resumable": False,
        "contracts_compat": ">=1.0,<2.0",
    },
}


class _EchoConfig(BaseModel):
    """Trivial `config_schema`: no fields, frozen and closed (sec. 3.1 table)."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class _EchoStage:
    """A trivial `Stage[dict, dict]` double: `run()` returns `inp` unchanged (pure, deterministic)."""

    plugin_id = "chunker.fixed_window"
    config_schema = _EchoConfig
    requires_lineage: ClassVar[tuple[str, ...]] = ()

    def capabilities(self) -> common_types.Capabilities:
        """Return the minimal common `Capabilities` fields (sec. 3.1: reflects runtime config)."""
        return common_types.Capabilities(
            isolation_modes=[common_types.IsolationMode.in_process],
            supports_resumable=False,
            contracts_compat=">=1.0,<2.0",
        )

    def fingerprint(self) -> str:
        """Return a fixed `H("producer", ...)` digest — no config, no model ids (bible sec. 6.2)."""
        return hash_of("producer", self.plugin_id, "1.0.0", "config-hash", "", "")

    async def run(self, inp: dict[str, Any], ctx: Any) -> dict[str, Any]:
        """Echo `inp` back unchanged; `ctx` is unused (pure transform, sec. 3.1)."""
        del ctx
        return dict(inp)


class TestEchoStageConformance(StageConformanceBase):
    """`_EchoStage` passes the complete 12-extension-point base class (`StageConformanceBase`)."""

    extension_point: ClassVar[str] = "chunker"
    stage_name: ClassVar[str | None] = "chunk"
    plugin_meta: ClassVar[dict[str, Any]] = _VALID_META
    in_type: ClassVar[type | None] = dict
    out_type: ClassVar[type | None] = dict

    def build_plugin(self) -> _EchoStage:
        """Return a fresh `_EchoStage`."""
        return _EchoStage()

    def build_input(self) -> dict[str, Any]:
        """Return a payload carrying a volatile `created_at` field the idempotency check must ignore."""
        return {"chunks": ["a", "b"], "created_at": "2026-01-01T00:00:00Z"}


def test_plugin_meta_conformance_rejects_license_grade_x() -> None:
    """`test_license_grade_is_a_catalog_value_and_never_x` fails for a shipped `license_grade=X`."""
    kit = TestEchoStageConformance()
    kit.plugin_meta = {**_VALID_META, "license_grade": "X"}
    with pytest.raises(AssertionError):
        kit.test_license_grade_is_a_catalog_value_and_never_x()


def test_plugin_meta_conformance_rejects_mismatched_extension_point() -> None:
    """`test_plugin_meta_extension_point_matches_this_conformance_kit` fails on a mismatch."""
    kit = TestEchoStageConformance()
    kit.plugin_meta = {**_VALID_META, "extension_point": "parser"}
    with pytest.raises(AssertionError):
        kit.test_plugin_meta_extension_point_matches_this_conformance_kit()


def test_plugin_meta_conformance_rejects_a_field_missing_from_the_schema() -> None:
    """`test_plugin_meta_has_every_required_field` fails when a required field is dropped."""
    kit = TestEchoStageConformance()
    kit.plugin_meta = {k: v for k, v in _VALID_META.items() if k != "license_grade"}
    with pytest.raises(AssertionError):
        kit.test_plugin_meta_has_every_required_field()


def test_stage_signature_conformance_rejects_a_plugin_id_prefix_mismatch() -> None:
    """`test_plugin_id_is_extension_point_dot_implementation` fails when the prefix diverges."""

    class _WrongPrefixStage(_EchoStage):
        plugin_id = "parser.fixed_window"

    class _Kit(TestEchoStageConformance):
        def build_plugin(self) -> _WrongPrefixStage:
            return _WrongPrefixStage()

    with pytest.raises(AssertionError):
        _Kit().test_plugin_id_is_extension_point_dot_implementation()


def test_normalize_for_comparison_drops_exactly_the_golden_excluded_fields() -> None:
    """Only `created_at`/`producer`/`lineage_refs` are dropped (guide sec. 8.2); other keys survive."""
    payload = {
        "chunks": ["a"],
        "created_at": "2026-01-01T00:00:00Z",
        "producer": {"plugin_id": "chunker.fixed_window"},
        "lineage_refs": {"source": "ref"},
    }
    assert normalize_for_comparison(payload) == {"chunks": ["a"]}
