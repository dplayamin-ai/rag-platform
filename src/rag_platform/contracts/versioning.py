"""rag_platform.contracts.versioning — schema_version compatibility rules.

GENERATED — do not edit; run `uv run python tools/contracts_gen.py` to regenerate.

Canon: design bible §6.4 ("schema_version semver: addition = minor, removal/semantic change =
major"), §12 module map ("versioning.py(schema_version compatibility rules)"); worked out in full
in docs/03-contracts/14-schema-versioning-and-compatibility.md (§1.2 schema_version rules, §4.1-4.3
producer/consumer judgement matrix and contracts_compat grammar, §6.2 upcaster registry proposal).

Unlike every other module in this package, this file has no schemas/*.schema.json counterpart: it
is the code-level compatibility engine, not a contract data model, so datamodel-code-generator
never runs on it. contracts_gen.py still owns its content (like __init__.py) so a human never
hand-edits it, and the regex constants below are copied verbatim from
schemas/common-types.schema.json at generation time so they can never drift from the
$defs/Semver and $defs/SchemaTypeName patterns every other generated module already relies on.

SchemaDiffReport and its nested types (CompatLevel, SchemaChangeKind, SchemaChange,
GoldenExampleResult, EnumMismatch, EnumCheckResult) are declared in
schemas/schema-diff-report.schema.json and are therefore already generated into
schema_diff_report.py; they are not repeated here.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

__all__ = [
    "RELEASE_SEMVER_RE",
    "SCHEMA_TYPE_RE",
    "SEMVER_RE",
    "CompatDecision",
    "SchemaVersion",
    "Upcaster",
    "UpcasterRegistry",
    "VersionedEnvelope",
    "compat_matcher",
    "judge_compat",
    "prune_unknown",
]

# Copied verbatim from schemas/common-types.schema.json $defs/Semver (regenerate via
# `uv run python tools/contracts_gen.py` if that pattern ever changes; see _common_type_pattern).
SEMVER_RE = "^(0|[1-9]\\d*)\\.(0|[1-9]\\d*)\\.(0|[1-9]\\d*)(?:-((?:0|[1-9]\\d*|\\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\\.(?:0|[1-9]\\d*|\\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\\+([0-9a-zA-Z-]+(?:\\.[0-9a-zA-Z-]+)*))?$"

# 03-contracts/14 §1.2: schema_version (envelope, ArtifactRef.schema_version) forbids the
# pre-release/build metadata that the general-purpose common Semver $def otherwise allows; this
# restriction is enforced as invariant 1 here, in code, not in schemas/ (03-contracts/14 §1.2).
RELEASE_SEMVER_RE = r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$"

# Copied verbatim from schemas/common-types.schema.json $defs/SchemaTypeName (see SEMVER_RE above).
SCHEMA_TYPE_RE = "^[A-Z][A-Za-z0-9]*$"

# Copied verbatim from schemas/common-types.schema.json $defs/ContractsCompat (promoted there in
# bible 1.3.0 AM-35; see SEMVER_RE above). Full syntax check for a contracts_compat range
# (03-contracts/14 §4.3); a caller that already passed Pydantic/JSON Schema validation never hits
# compat_matcher's ValueError. Individual clauses are then re-parsed with _COMPAT_CLAUSE_RE below.
_COMPAT_FULL_RE = "^(>=|<=|==|<|>)(0|[1-9][0-9]*)\\.(0|[1-9][0-9]*)(,(>=|<=|==|<|>)(0|[1-9][0-9]*)\\.(0|[1-9][0-9]*))*$"
_COMPAT_CLAUSE_RE = re.compile(r"(>=|<=|==|<|>)(\d+)\.(\d+)")

CompatDecision = Literal["load", "load_tolerant", "upcast", "reject"]

_COMPARISONS: dict[str, Callable[[tuple[int, int], tuple[int, int]], bool]] = {
    ">=": lambda have, want: have >= want,
    "<=": lambda have, want: have <= want,
    "==": lambda have, want: have == want,
    "<": lambda have, want: have < want,
    ">": lambda have, want: have > want,
}


@dataclass(frozen=True, order=True)
class SchemaVersion:
    """A contract version. Compatibility judgement only looks at major/minor (03-contracts/14 §1.2)."""

    major: int
    minor: int
    patch: int

    @classmethod
    def parse(cls, text: str) -> SchemaVersion:
        """Validate the common Semver format, then enforce invariant 1 (no pre-release/build)."""
        if not re.fullmatch(SEMVER_RE, text):
            msg = f"schema_version format violation (contract.violation: schema_version format): {text!r}"
            raise ValueError(msg)
        if not re.fullmatch(RELEASE_SEMVER_RE, text):
            msg = (
                "schema_version forbids pre-release/build metadata "
                f"(contract.violation, 03-contracts/14 §1.2): {text!r}"
            )
            raise ValueError(msg)
        major, minor, patch = (int(part) for part in text.split("."))
        return cls(major, minor, patch)


def compat_matcher(contracts_compat: str) -> Callable[[SchemaVersion], bool]:
    """Turn a contracts_compat range (e.g. ">=1.0,<2.0") into a predicate (03-contracts/14 §4.3).

    Patch never participates in the comparison.
    """
    if not re.fullmatch(_COMPAT_FULL_RE, contracts_compat):
        msg = f"contracts_compat format violation: {contracts_compat!r}"
        raise ValueError(msg)
    clauses = [(op, (int(major), int(minor))) for op, major, minor in _COMPAT_CLAUSE_RE.findall(contracts_compat)]

    def matches(version: SchemaVersion) -> bool:
        return all(_COMPARISONS[op]((version.major, version.minor), bound) for op, bound in clauses)

    return matches


class VersionedEnvelope(BaseModel):
    """Code-level base for a hand-written envelope contract (bible §5.2); not a schemas/ $def.

    Every generated (schema-derived) contract module already declares its own schema_version/
    schema_type fields directly (03-contracts/00 §3.1: additionalProperties: false and allOf
    merging do not mix), so nothing under rag_platform.contracts currently subclasses this; it
    exists for hand-written envelope-shaped models elsewhere in the codebase that want the same
    schema_version format and schema_type/class-name invariant enforced.
    """

    model_config = ConfigDict(extra="forbid")
    schema_version: str = Field(
        pattern=SEMVER_RE, description="Contract version (common Semver, per-contract). Initial 1.0.0."
    )
    schema_type: str = Field(
        pattern=SCHEMA_TYPE_RE, description="PascalCase type name; must match ArtifactRef.schema_type."
    )

    @model_validator(mode="after")
    def _check_invariants(self) -> VersionedEnvelope:  # noqa: N804 - pydantic v2 "after" validators
        # are instance methods (they run on the constructed model); only "before"/"wrap" mode
        # validators are classmethods, but this repo's pep8-naming config does not distinguish mode.
        SchemaVersion.parse(self.schema_version)  # invariant 1 (03-contracts/14 §1.2)
        if type(self) is not VersionedEnvelope and self.schema_type != type(self).__name__:
            msg = f"schema_type {self.schema_type!r} != {type(self).__name__!r} (contract.violation)"
            raise ValueError(msg)
        return self


Upcaster = Callable[[dict[str, Any]], dict[str, Any]]


class UpcasterRegistry:
    """One pure function per major boundary, ``N.x -> N+1.0.0`` (03-contracts/14 §6.2, proposal).

    Minor versions inside a major are never transformed (additive-only, §2.1): a consumer whose
    minor is >= the payload's needs no upcasting at all (see judge_compat row 6).
    """

    def __init__(self) -> None:
        self._steps: dict[tuple[str, int], Upcaster] = {}

    def register(self, schema_type: str, from_major: int) -> Callable[[Upcaster], Upcaster]:
        """Register the single upcaster for `schema_type` from major `from_major` to `from_major + 1`."""

        def decorator(fn: Upcaster) -> Upcaster:
            key = (schema_type, from_major)
            if key in self._steps:
                msg = f"duplicate upcaster registration: {key!r}"
                raise ValueError(msg)
            self._steps[key] = fn
            return fn

        return decorator

    def has_path(self, schema_type: str, src: SchemaVersion, dst: SchemaVersion) -> bool:
        """True if every major boundary from `src` to `dst` has a registered upcaster."""
        return all((schema_type, major) in self._steps for major in range(src.major, dst.major))

    def upcast(self, payload: dict[str, Any], target: SchemaVersion) -> dict[str, Any]:
        """Apply the registered chain in order; raises `KeyError` if `has_path` was not checked first."""
        current = SchemaVersion.parse(str(payload["schema_version"]))
        for major in range(current.major, target.major):
            payload = self._steps[(str(payload["schema_type"]), major)](dict(payload))
            payload["schema_version"] = f"{major + 1}.0.0"
        return payload


def judge_compat(
    ref_type: str,
    ref_version: str,
    consumer_type: str,
    consumer_version: SchemaVersion,
    *,
    contracts_compat: str,
    registry: UpcasterRegistry,
    tolerant_minor: bool = False,
) -> CompatDecision:
    """Judge a producer artifact against a consumer model (03-contracts/14 §4.2 matrix).

    ``ref_type``/``ref_version`` come from ``ArtifactRef.schema_type``/``.schema_version``;
    ``consumer_type``/``consumer_version`` from the loaded ``rag_platform.contracts`` model's class
    name and its contract version (03-contracts/14 §4.1); ``contracts_compat`` from
    ``Capabilities.contracts_compat`` (plugin) or the built-in stage's own declared range.

    Defaults to the currently decided rows: row 3 (no upcaster) and row 7 (producer minor ahead of
    consumer) both reject. A registered upcaster and ``tolerant_minor=True`` opt into the
    lazy-upcast and tolerant-read proposals respectively (03-contracts/14 open issue 4; not
    adopted). The calling shell raises `contract.violation` with the matching §4.2 detail string on
    every reject.
    """
    if ref_type != consumer_type or not re.fullmatch(RELEASE_SEMVER_RE, ref_version):
        return "reject"  # rows 1, 8
    version = SchemaVersion.parse(ref_version)
    if version.major > consumer_version.major:
        return "reject"  # row 2
    if version.major < consumer_version.major:
        return "upcast" if registry.has_path(consumer_type, version, consumer_version) else "reject"  # rows 3, 4
    if not compat_matcher(contracts_compat)(version):
        return "reject"  # row 5
    if version.minor <= consumer_version.minor:
        return "load"  # row 6
    return "load_tolerant" if tolerant_minor else "reject"  # row 7


def prune_unknown(
    payload: Any,
    schema: dict[str, Any],
    defs: dict[str, dict[str, Any]],
    dropped: list[str],
    path: str = "",
) -> Any:
    """Tolerant-read proposal skeleton (03-contracts/14 §4.2 open issue 4) — not the default
    behaviour (judge_compat only returns `load_tolerant` when the caller opts in explicitly).
    Drops only the optional properties the consumer schema does not know about; required
    properties, enum values and types are left untouched.
    """
    if "$ref" in schema:
        return prune_unknown(payload, defs[schema["$ref"].rsplit("/", 1)[-1]], defs, dropped, path)
    if isinstance(payload, dict) and "properties" in schema:
        pruned: dict[str, Any] = {}
        for key, value in payload.items():
            if key in schema["properties"]:
                pruned[key] = prune_unknown(value, schema["properties"][key], defs, dropped, f"{path}/{key}")
            elif schema.get("additionalProperties", False) is False:
                dropped.append(f"{path}/{key}")
            else:
                pruned[key] = value
        return pruned
    if isinstance(payload, list) and "items" in schema:
        return [
            prune_unknown(item, schema["items"], defs, dropped, f"{path}/{index}") for index, item in enumerate(payload)
        ]
    return payload
