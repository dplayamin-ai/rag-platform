"""플러그인 적합성(conformance) 공용 믹스인 — 5멤버 시그니처·계약 타입·멱등성·`StageError`·`PluginMeta`.

역할: 확장 지점 14종이 공통으로 지켜야 하는 다섯 가지 — `Stage` 5멤버 시그니처, 계약 입출력
타입, 멱등성(순수 변환), `StageError` 분류, `PluginMeta` 필수 필드·`license_grade` — 를 pytest
클래스 상속으로 검증하는 믹스인을 모은다. `kits.py`가 이 믹스인들을 확장 지점별로 조립한다.
설계 근거: `docs/10-development/06-plugin-development-guide.md` §8.1(기반 클래스 상속),
§3.1(5멤버 표), §3.3(오류), §8.2(golden 정규화 — `created_at`/`producer`/`lineage_refs` 제외);
`ADR-0032`(플러그인 SDK `Stage` 프로토콜과 적합성 키트); `sdk.stage.Stage`/`StageError`,
`plugins.registry.validate_plugin_meta`.
구성: `ConformanceKitBase` — 공유 클래스 변수(`extension_point`/`plugin_meta`); `PluginMetaConformance`
— 스키마·`license_grade`; `StageErrorCatalogConformance` — 코드 철자·분류·`to_payload` 왕복;
`StageConformanceMethods` — `build_plugin`/`build_input`/`build_context` 추상 훅;
`StageSignatureConformance`/`ContractRoundtripConformance`/`IdempotencyConformance` — 5멤버·
입출력 타입·순수성; `StageConformanceBase`/`PortConformanceKitBase` — 조립된 완성 클래스;
`default_stage_context()` — 최소 `StageContext`(`sdk.context.LocalContext` 기반).
불변식: 이 패키지는 프로덕션 진입점이 임포트할 수 없다(import-linter `testing-not-in-production`).
추상 훅은 `NotImplementedError`로 두어 서브클래스가 반드시 채우게 한다.
검증 계층: 1층(여기서 검증) — `tests/unit/conformance/test_conformance_base.py`.
"""

from __future__ import annotations

import inspect
import re
from dataclasses import asdict, dataclass, is_dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, ClassVar

import pytest
from pydantic import BaseModel

from rag_platform.plugins.registry import LICENSE_GRADE_ORDER, validate_plugin_meta
from rag_platform.sdk.context import LocalContext
from rag_platform.sdk.stage import CODE_CLASSIFICATION, StageError, classify_error, is_valid_code
from rag_platform.storage.artifact_store import InMemoryArtifactStore

if TYPE_CHECKING:
    from collections.abc import Mapping

__all__ = [
    "ConformanceKitBase",
    "ContractRoundtripConformance",
    "IdempotencyConformance",
    "PluginMetaConformance",
    "PortConformanceKitBase",
    "StageConformanceBase",
    "StageConformanceMethods",
    "StageErrorCatalogConformance",
    "StageSignatureConformance",
    "default_stage_context",
    "normalize_for_comparison",
]

_HEX64_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_PLUGIN_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$")
# Guide sec. 8.2: `expected_golden_hash` normalizes by excluding exactly these three fields before
# hashing/comparing a pure stage's output; the idempotency check reuses the same exclusion set.
_VOLATILE_KEYS = frozenset({"created_at", "producer", "lineage_refs"})
_REQUIRED_PLUGIN_META_FIELDS: tuple[str, ...] = (
    "plugin_id",
    "extension_point",
    "version",
    "license",
    "license_grade",
    "territory",
    "linkage",
    "isolation_supported",
    "contracts_compat",
    "capabilities",
)
# Fixed instant (never `datetime.now()`, banned-api TID251 sec. 4.1 purity rule): every conformance
# context ticks the same clock so idempotency comparisons never fail on a volatile timestamp.
_FIXED_NOW = datetime(2026, 1, 1, tzinfo=UTC)


def normalize_for_comparison(value: Any) -> Any:
    """Recursively drop golden-hash-excluded volatile fields (guide sec. 8.2) before comparing.

    `created_at`/`producer`/`lineage_refs` are excluded exactly as `expected_golden_hash`
    normalization excludes them, so two `run()` calls of a pure stage over identical input compare
    equal even though those three fields may legitimately differ from call to call.
    """
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    elif is_dataclass(value) and not isinstance(value, type):
        value = asdict(value)
    if isinstance(value, dict):
        return {key: normalize_for_comparison(item) for key, item in value.items() if key not in _VOLATILE_KEYS}
    if isinstance(value, (list, tuple)):
        return [normalize_for_comparison(item) for item in value]
    return value


@dataclass
class _NullTokenCounter:
    """`sdk.ports.TokenCounter` double: whitespace token count, no real tokenizer (conformance-only)."""

    tokenizer_id: str = "conformance-null-v1"

    def count(self, text: str) -> int:
        """Return the whitespace-split token count of `text`."""
        return len(text.split())


def default_stage_context(
    *,
    tenant_id: str = "tenant-conformance",
    collection_id: str | None = "collection-conformance",
    profile_hash: str = "0" * 64,
    trace_id: str = "trace-conformance",
) -> Any:
    """Build a minimal, non-durable `StageContext` (`sdk.context.LocalContext`) for conformance tests.

    Uses a fixed clock (bible sec. 4.1: stages never call `datetime.now()` themselves) and
    `storage.artifact_store.InMemoryArtifactStore` so `ctx.artifacts.put_source`/`put_derived`
    work without a real object store.
    """
    local = LocalContext(
        tenant_id=tenant_id,
        collection_id=collection_id,
        profile_hash=profile_hash,
        trace_id=trace_id,
        store=InMemoryArtifactStore(),
        clock=lambda: _FIXED_NOW,
    )
    return local.build_stage_context(stage_token_counter=_NullTokenCounter())


class ConformanceKitBase:
    """Shared class-level identity every conformance mixin refers to.

    `extension_point` must equal one of `plugins.registry.EXTENSION_POINTS` (D-10, 14 values);
    `plugin_meta` is the `PluginMeta` mapping the concrete conformance test declares for the
    plugin under test (validated by `PluginMetaConformance`).
    """

    extension_point: ClassVar[str]
    plugin_meta: ClassVar[Mapping[str, Any]]


class PluginMetaConformance(ConformanceKitBase):
    """`PluginMeta` 필수 필드(바이블 §5.6)와 `license_grade` 상한(D-02, ADR-0001)을 검증한다."""

    def test_plugin_meta_has_every_required_field(self) -> None:
        """Every bible sec. 5.6 required `PluginMeta` field is present (schema `required` list)."""
        missing = [field for field in _REQUIRED_PLUGIN_META_FIELDS if field not in self.plugin_meta]
        assert not missing

    def test_plugin_meta_validates_against_the_schema(self) -> None:
        """`schemas/plugin-meta.schema.json` accepts the declared `plugin_meta` mapping."""
        validate_plugin_meta(self.plugin_meta)

    def test_plugin_meta_extension_point_matches_this_conformance_kit(self) -> None:
        """The declared `extension_point` field matches the kit class under test."""
        assert self.plugin_meta["extension_point"] == self.extension_point

    def test_plugin_id_prefix_matches_extension_point(self) -> None:
        """`plugin_id` is `{extension_point}.{implementation}` (bible sec. 6.1)."""
        assert self.plugin_meta["plugin_id"].split(".", 1)[0] == self.extension_point

    def test_license_grade_is_a_catalog_value_and_never_x(self) -> None:
        """`license_grade` is one of A-D; `X` is never loadable (D-02, ADR-0001)."""
        grade = self.plugin_meta["license_grade"]
        assert grade in LICENSE_GRADE_ORDER
        assert grade != "X"


class StageErrorCatalogConformance(ConformanceKitBase):
    """`StageError` 코드가 자신의 stage 접두를 갖고 §5.7 카탈로그로 분류됨을 검증한다(§3.3)."""

    stage_name: ClassVar[str | None] = None
    error_codes: ClassVar[tuple[str, ...] | None] = None

    @classmethod
    def _codes_under_test(cls) -> tuple[str, ...]:
        """Explicit `error_codes` override, else every catalog code prefixed by `stage_name`."""
        if cls.error_codes is not None:
            return cls.error_codes
        if cls.stage_name is None:
            return ()
        return tuple(code for code in CODE_CLASSIFICATION if code.split(".", 1)[0] == cls.stage_name)

    def test_stage_error_codes_are_cataloged_and_classify_consistently(self) -> None:
        """Each declared code round-trips through `StageError`/`classify_error`/`to_payload`."""
        codes = self._codes_under_test()
        if not codes:
            pytest.skip(f"{self.extension_point}: no cataloged StageError codes yet (open issue)")
        for code in codes:
            assert is_valid_code(code)
            stage = code.split(".", 1)[0]
            error = StageError(code, stage=stage, plugin_id=self.plugin_meta["plugin_id"])
            assert error.classification is classify_error(code)
            payload = error.to_payload()
            assert payload["code"] == code
            assert payload["stage"] == stage


class StageConformanceMethods(ConformanceKitBase):
    """`Stage` 5멤버 확장 지점 전용 추상 훅 — `build_plugin`/`build_input`/`build_context`."""

    in_type: ClassVar[type | None] = None
    out_type: ClassVar[type | None] = None

    def build_plugin(self) -> Any:
        """Return the `Stage[In, Out]` instance under test; concrete tests must override this."""
        msg = f"{type(self).__name__}.build_plugin() must be implemented by the concrete conformance test"
        raise NotImplementedError(msg)

    def build_input(self) -> Any:
        """Return one `in_type` instance to feed `Stage.run`; concrete tests must override this."""
        msg = f"{type(self).__name__}.build_input() must be implemented by the concrete conformance test"
        raise NotImplementedError(msg)

    def build_context(self) -> Any:
        """Return the `StageContext` to run under; defaults to `default_stage_context()`."""
        return default_stage_context()


class StageSignatureConformance(StageConformanceMethods):
    """`Stage` 5멤버(§3.1 표) 구조를 검증한다: `plugin_id`/`config_schema`/`capabilities()`/`fingerprint()`/`run()`."""

    def test_plugin_id_is_extension_point_dot_implementation(self) -> None:
        """`plugin_id` is `{extension_point}.{implementation}`, both snake_case (bible sec. 6.1)."""
        plugin = self.build_plugin()
        assert isinstance(plugin.plugin_id, str)
        assert _PLUGIN_ID_PATTERN.match(plugin.plugin_id)
        assert plugin.plugin_id.split(".", 1)[0] == self.extension_point

    def test_config_schema_is_a_frozen_forbid_extra_pydantic_model(self) -> None:
        """`config_schema` forbids unknown fields and is immutable (sec. 3.1 table)."""
        plugin = self.build_plugin()
        schema = plugin.config_schema
        assert isinstance(schema, type)
        assert issubclass(schema, BaseModel)
        assert schema.model_config.get("extra") == "forbid"
        assert schema.model_config.get("frozen") is True

    def test_capabilities_declares_the_common_capability_fields(self) -> None:
        """`capabilities()` exposes `isolation_modes`/`supports_resumable`/`contracts_compat`.

        `contracts_compat` may be a plain `str` or a `ContractsCompat` root-model wrapping one
        (bible sec. 5.1); either way it must stringify to a non-empty value.
        """
        plugin = self.build_plugin()
        caps = plugin.capabilities()
        assert getattr(caps, "isolation_modes", None)
        assert isinstance(getattr(caps, "supports_resumable", None), bool)
        contracts_compat = getattr(caps, "contracts_compat", None)
        assert contracts_compat is not None
        assert str(contracts_compat)

    def test_fingerprint_is_a_stable_hex64_digest(self) -> None:
        """`fingerprint()` is a deterministic BLAKE3 hex digest (bible sec. 4.1/6.2)."""
        plugin = self.build_plugin()
        first = plugin.fingerprint()
        second = plugin.fingerprint()
        assert first == second
        assert _HEX64_PATTERN.match(first)

    def test_run_is_an_async_callable(self) -> None:
        """`run` is `async def run(self, inp, ctx)` (sec. 3.1: the only side-effecting member)."""
        plugin = self.build_plugin()
        assert inspect.iscoroutinefunction(plugin.run)


class ContractRoundtripConformance(StageConformanceMethods):
    """계약 입출력 타입 — `run()`이 선언된 `in_type`/`out_type` 인스턴스를 주고받는지 확인한다."""

    async def test_run_accepts_and_returns_the_declared_contract_types(self) -> None:
        """`build_input()` is an `in_type`; `run()`'s result is an `out_type` (when declared)."""
        plugin = self.build_plugin()
        payload = self.build_input()
        if self.in_type is not None:
            assert isinstance(payload, self.in_type)
        output = await plugin.run(payload, self.build_context())
        if self.out_type is not None:
            assert isinstance(output, self.out_type)


class IdempotencyConformance(StageConformanceMethods):
    """멱등성(순수 변환, §3.1 `run()` 규약) — 동일 입력을 두 번 실행해도 같은 결과가 나옴을 확인한다."""

    async def test_run_is_idempotent_for_identical_input(self) -> None:
        """Two `run()` calls over identical input agree once volatile fields are dropped (sec. 8.2)."""
        plugin = self.build_plugin()
        first = await plugin.run(self.build_input(), self.build_context())
        second = await plugin.run(self.build_input(), self.build_context())
        assert normalize_for_comparison(first) == normalize_for_comparison(second)


class StageConformanceBase(
    PluginMetaConformance,
    StageErrorCatalogConformance,
    StageSignatureConformance,
    ContractRoundtripConformance,
    IdempotencyConformance,
):
    """Stage 5-member 확장 지점(12종: `fetcher`~`packer`, `evaluator`)의 완전한 적합성 기반 클래스."""


class PortConformanceKitBase(PluginMetaConformance, StageErrorCatalogConformance):
    """역할 포트 확장 지점(`embedder`/`index_backend`)의 공통 기반 — `PluginMeta`·`StageError`만 공유한다."""
