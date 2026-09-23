"""엔트리 포인트 기반 `PluginRegistry` — 탐색, `PluginMeta` 검증, 라이선스 게이트.

역할: `rag_platform.{extension_point}` 엔트리 포인트로 플러그인을 탐색·등록하고, 로드 전 라이선스
등급과 필요 역량(capabilities)을 검사한다.
설계 근거: 바이블 §5.7(`ExtensionPoint` 14종, `LicenseGrade`, `Linkage`, `IsolationMode`), §6.7(엔트리
포인트 그룹 `rag_platform.{extension_point}`), §7.4 규칙(1)(라이선스 게이트); ADR-0032(플러그인 SDK);
`schemas/plugin-meta.schema.json`.
구성: `entry_point_group` — 확장 지점 → 그룹 이름; `validate_plugin_meta` — jsonschema로 `PluginMeta`
검증; `check_license`/`check_capabilities` — §7.4 규칙(1)/(2); `PluginRegistry` — 수동 등록 + 엔트리
포인트 탐색을 합친 조회·빌드 API(`discover`/`meta`/`build_stage`/`build_port`).
불변식: `PluginMeta`는 아직 생성되지 않은 Pydantic 모델 대신 `jsonschema`(Draft 2020-12)로 검증한다.
`license_grade=X`는 항상 거부(D-02, ADR-0001); `plugin_id` 접두사는 반드시 `extension_point`와
일치해야 한다.
검증 계층: 1층(여기서 검증) — tests/unit/test_plugins_registry.py.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from importlib import metadata as importlib_metadata
from pathlib import Path
from typing import TYPE_CHECKING, Any

import jsonschema
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence

__all__ = [
    "EXTENSION_POINTS",
    "ISOLATION_MODES",
    "LICENSE_GRADE_ORDER",
    "LicenseError",
    "PluginRegistry",
    "check_capabilities",
    "check_license",
    "entry_point_group",
    "validate_plugin_meta",
]

# Bible §5.7 `ExtensionPoint` (D-10, 14 values, ADR-0032). Closed set: growing it needs a D-10
# amendment ADR, not a code change here.
EXTENSION_POINTS: tuple[str, ...] = (
    "fetcher",
    "parser",
    "normalizer",
    "chunker",
    "enricher",
    "embedder",
    "index_backend",
    "query_transformer",
    "retriever",
    "fuser",
    "reranker",
    "postprocessor",
    "packer",
    "evaluator",
)

# Bible §5.7 `IsolationMode`.
ISOLATION_MODES: tuple[str, ...] = ("in_process", "helper_process", "sidecar")

# Bible §5.7 `LicenseGrade`, ordered from most to least permissive (index = rank).
LICENSE_GRADE_ORDER: tuple[str, ...] = ("A", "B", "C", "D", "X")

_SCHEMAS_DIR = Path(__file__).resolve().parents[3] / "schemas"
_PLUGIN_META_SCHEMA_ID = "urn:rag:schema:plugin-meta:1"


class LicenseError(Exception):
    """Raised by :func:`check_license`; carries the bible §5.7 error code as `.code`."""

    def __init__(self, code: str, message: str) -> None:
        """Build a `LicenseError` carrying the catalog `code` and a human-readable `message`."""
        super().__init__(message)
        self.code = code


def entry_point_group(extension_point: str) -> str:
    """Bible §6.7: entry point group name for an extension point."""
    if extension_point not in EXTENSION_POINTS:
        msg = f"unknown extension_point {extension_point!r} (bible §5.7 ExtensionPoint, D-10)"
        raise ValueError(msg)
    return f"rag_platform.{extension_point}"


def _build_registry(schemas_dir: Path = _SCHEMAS_DIR) -> Registry:
    """Load every `schemas/*.schema.json` `$id` into a `referencing.Registry` for `$ref` resolution."""
    resources: list[tuple[str, Resource]] = []
    for path in schemas_dir.glob("*.schema.json"):
        contents = json.loads(path.read_text(encoding="utf-8"))
        schema_id = contents["$id"]
        resources.append((schema_id, Resource.from_contents(contents, default_specification=DRAFT202012)))
    return Registry().with_resources(resources)


def validate_plugin_meta(meta: Mapping[str, Any], *, schemas_dir: Path = _SCHEMAS_DIR) -> None:
    """Validate `meta` against `schemas/plugin-meta.schema.json` (raises `jsonschema.ValidationError`)."""
    registry = _build_registry(schemas_dir)
    schema = registry.contents(_PLUGIN_META_SCHEMA_ID)
    validator = jsonschema.Draft202012Validator(schema, registry=registry)
    validator.validate(dict(meta))


_LICENSE_DENIED = "plugin.license_denied"
_CAPABILITY_UNSUPPORTED = "plugin.capability_unsupported"


def check_license(meta: Mapping[str, Any], policy: Mapping[str, Any]) -> None:
    """Bible §7.4 rule (1): license grade ceiling, territory coverage, B+static_bundled rejection.

    ``policy`` is the `Profile.license_policy` mapping (`{max_grade, territory}`).
    Raises :class:`LicenseError` (code `plugin.license_denied`) on any violation.
    """
    grade = meta["license_grade"]
    max_grade = policy["max_grade"]
    if LICENSE_GRADE_ORDER.index(grade) > LICENSE_GRADE_ORDER.index(max_grade):
        msg = f"{meta['plugin_id']}: license_grade {grade} exceeds policy max_grade {max_grade}"
        raise LicenseError(_LICENSE_DENIED, msg)
    if grade == "X":
        msg = f"{meta['plugin_id']}: license_grade X is never loadable (D-02, ADR-0001)"
        raise LicenseError(_LICENSE_DENIED, msg)
    required_territory = set(policy.get("territory", ()))
    plugin_territory = set(meta.get("territory", ()))
    if required_territory and plugin_territory and not required_territory <= plugin_territory:
        msg = f"{meta['plugin_id']}: territory {plugin_territory} does not cover policy {required_territory}"
        raise LicenseError(_LICENSE_DENIED, msg)
    if grade == "B" and meta.get("linkage") == "static_bundled":
        msg = f"{meta['plugin_id']}: license_grade=B with linkage=static_bundled is rejected (bible §7.4 (1))"
        raise LicenseError(_LICENSE_DENIED, msg)


def check_capabilities(meta: Mapping[str, Any], required: Mapping[str, Any]) -> None:
    """Bible §7.4 rule (2): declared `capabilities()` must cover what the profile requires.

    ``required`` is a flat mapping of capability name -> required value; only keys present in
    `required` are checked (a minimal subset of the full profile validation matrix, §7.4).
    Raises :class:`LicenseError` (reusing it as the capability-mismatch signal, code
    `plugin.capability_unsupported`) on the first unmet requirement.
    """
    declared = meta.get("capabilities", {})
    for key, expected in required.items():
        actual = declared.get(key)
        if isinstance(expected, (list, tuple, set)):
            if not set(expected) <= set(actual or ()):
                msg = f"{meta['plugin_id']}: capability {key} does not cover required {expected}"
                raise LicenseError(_CAPABILITY_UNSUPPORTED, msg)
        elif actual != expected:
            msg = f"{meta['plugin_id']}: capability {key}={actual!r} does not satisfy required {expected!r}"
            raise LicenseError(_CAPABILITY_UNSUPPORTED, msg)


@dataclass
class _Registration:
    meta: Mapping[str, Any]
    factory: Callable[..., Any]


class PluginRegistry:
    """`rag_platform.{extension_point}` entry-point registry + a manual registration API for tests.

    Discovery is lazy and cached per extension point; :meth:`register` (used by the conformance
    kit and unit tests) adds an in-process registration that `discover`/`meta`/`build_stage` see
    exactly like an installed entry point, without requiring a real distribution.
    """

    def __init__(self) -> None:
        """Start with no manual registrations and an empty entry-point cache."""
        self._manual: dict[str, _Registration] = {}
        self._entry_point_cache: dict[str, Sequence[importlib_metadata.EntryPoint]] = {}

    def register(self, meta: Mapping[str, Any], factory: Callable[..., Any]) -> None:
        """Register `meta` (validated against `plugin-meta.schema.json`) with a build `factory`."""
        validate_plugin_meta(meta)
        plugin_id = meta["plugin_id"]
        prefix = plugin_id.split(".", 1)[0]
        if prefix != meta["extension_point"]:
            msg = f"plugin_id {plugin_id!r} prefix does not match extension_point {meta['extension_point']!r}"
            raise ValueError(msg)
        self._manual[plugin_id] = _Registration(meta=dict(meta), factory=factory)  # defensive copy

    def _discover_entry_points(self, extension_point: str) -> Sequence[importlib_metadata.EntryPoint]:
        group = entry_point_group(extension_point)
        if group not in self._entry_point_cache:
            self._entry_point_cache[group] = tuple(importlib_metadata.entry_points(group=group))
        return self._entry_point_cache[group]

    def discover(self, extension_point: str) -> list[Mapping[str, Any]]:
        """List `PluginMeta` mappings for every plugin registered under `extension_point`."""
        metas = [reg.meta for reg in self._manual.values() if reg.meta["extension_point"] == extension_point]
        for entry_point in self._discover_entry_points(extension_point):
            loaded = entry_point.load()
            meta = getattr(loaded, "plugin_meta", None)
            if meta is not None:
                metas.append(meta)
        return metas

    def meta(self, plugin_id: str) -> Mapping[str, Any]:
        """Return the `PluginMeta` mapping for `plugin_id`, or raise `KeyError`."""
        if plugin_id in self._manual:
            return self._manual[plugin_id].meta
        extension_point = plugin_id.split(".", 1)[0]
        for candidate in self.discover(extension_point):
            if candidate["plugin_id"] == plugin_id:
                return candidate
        msg = f"no plugin registered for plugin_id {plugin_id!r}"
        raise KeyError(msg)

    def build_stage(self, plugin_id: str, config: Mapping[str, Any], services: Any = None) -> Any:
        """Build a `Stage[In, Out]` instance (5-member protocol, ADR-0032)."""
        return self._build(plugin_id, config, services)

    def build_port(self, plugin_id: str, config: Mapping[str, Any], services: Any = None) -> Any:
        """Build a role port that is not a `Stage` (e.g. `IndexBackend`, `TokenCounter`)."""
        return self._build(plugin_id, config, services)

    def _build(self, plugin_id: str, config: Mapping[str, Any], services: Any) -> Any:
        if plugin_id in self._manual:
            factory = self._manual[plugin_id].factory
        else:
            extension_point = plugin_id.split(".", 1)[0]
            for entry_point in self._discover_entry_points(extension_point):
                if entry_point.name == plugin_id:
                    factory = entry_point.load()
                    break
            else:
                msg = f"no plugin registered for plugin_id {plugin_id!r}"
                raise KeyError(msg)
        return factory(config, services)

    def check_license(self, meta: Mapping[str, Any], policy: Mapping[str, Any]) -> None:
        """Apply bible §7.4 rule (1) (see the module-level `check_license`)."""
        check_license(meta, policy)

    def check_capabilities(self, meta: Mapping[str, Any], required: Mapping[str, Any]) -> None:
        """Apply bible §7.4 rule (2) (see the module-level `check_capabilities`)."""
        check_capabilities(meta, required)
