"""`schemas/*.schema.json`에서 `src/rag_platform/contracts/`를 재생성하는 계약 빌드 스크립트 — 이 스크립트 자체는
손으로 쓰지만 출력 패키지 전체는 빌드 산출물이며 손으로 고치지 않는다.

설계 근거: 바이블 §5.1(`schemas/*.schema.json`이 계약 정본, Pydantic v2 패키지는 생성물), §12(모듈 맵의
`versioning.py`), `docs/03-contracts/14-schema-versioning-and-compatibility.md` §1.2·§4.2·§4.3·§6.2.

구성:
- `prepare_temp_schemas`/`_rewrite_node`/`_property_names_leaf` — `$ref`를 명시적 상대 경로로 재작성하고
  datamodel-code-generator의 두 알려진 결함(`format`+`pattern` 충돌 `_FORMAT_PATTERN_CLASH`,
  `propertyNames.$ref`가 해시 불가능한 클래스를 만드는 문제)을 스키마 복사본에서 우회한다.
- `run_datamodel_codegen` — schema당 Pydantic v2 모듈 생성(`--use-specialized-enum` 등 CLI 플래그).
- `write_init` — 스키마 `title`과 `common_types` 공개 클래스를 재노출하는 `__init__.py` 재생성.
- `write_versioning` — 스키마가 없는 `schema_version` 호환 엔진 `versioning.py`를 고정 템플릿으로 생성.
- `run_ruff` — 생성 패키지에만 `ruff check --fix`·`ruff format` 적용.

불변식: 출력 파일은 이 스크립트만 쓴다 — 손으로 고친 내용은 다음 재생성 때 사라진다.
검증 계층: 1층(여기서 검증) — `tests/contracts`, `tools/validate-contracts.mjs`. 실행: `uv run python
tools/contracts_gen.py`(`--keep-temp`로 재작성된 스키마 사본 확인, `--no-format`으로 ruff 단계 생략).
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS_DIR = ROOT / "schemas"
OUTPUT_DIR = ROOT / "src" / "rag_platform" / "contracts"
COMMON_MODULE = "common_types"

GENERATED_NOTE = "GENERATED — 수정 금지. 재생성: `uv run python tools/contracts_gen.py`"

# `datamodel-code-generator` writes `--custom-file-header` verbatim at the top of every generated
# file (it does not comment-prefix it), so this must already be valid Python — a triple-quoted
# module docstring rather than `#` comments, so every generated (sub)package still has a non-empty
# `__doc__` (tests/unit/test_scaffold.py walks every package under rag_platform and asserts this;
# `from __future__ import annotations` is allowed to follow a module docstring). The body is the
# Korean header required by `tools/phase6/CODE-HEADER-RULE.md`; it is necessarily generic (one
# string applies to every schema-derived module in a single batch run) rather than naming each
# module's own class.
GENERATED_FILE_HEADER = (
    f'"""{GENERATED_NOTE}\n'
    "\n"
    "역할: `schemas/*.schema.json`의 계약 스키마 하나를 그대로 옮긴 Pydantic v2 모델(계층 L0) — 파이프라인 단계 간에 "
    "주고받는 데이터의 타입을 정의한다.\n"
    "설계 근거: 바이블 §5.1(계약이 정본), §6.4(kebab 스키마 이름 ↔ snake_case 모듈명), §12(레이어 지도).\n"
    "구성: 클래스명은 스키마의 `title`(또는 `$defs`의 각 항목)과 동일하며, 필드는 스키마의 `properties`/`required`를 "
    "그대로 반영한다.\n"
    "불변식: `tools/contracts_gen.py`만 이 파일을 쓴다 — 손으로 고친 내용은 다음 재생성 때 사라진다.\n"
    "검증 계층: 1층(여기서 검증) — tests/contracts, tools/validate-contracts.mjs.\n"
    '"""'
)

# Matches a `$ref` string value in either form:
#   "urn:rag:schema:<name>:1"            (whole-document ref, no fragment)
#   "urn:rag:schema:<name>:1#/$defs/X"   (cross-file or self urn ref)
_URN_REF = re.compile(r"^urn:rag:schema:([a-z0-9-]+):1(#(/.*)?)?$")

# `format` values whose datamodel-code-generator Python type (AwareDatetime, date, UUID, ...) does
# not accept a sibling `pattern` constraint. Every use in schemas/ pairs one of these with a
# `pattern` that already fully constrains the string (bible §5.3 common-types `DateTime`, `Date`,
# `Duration`, `Uuid`), so dropping `format` when `pattern` is also present keeps the real
# constraint and avoids `--field-constraints` attaching `pattern` to a non-str type, which raises
# `TypeError: Unable to apply constraint 'pattern' ... for schema of type 'datetime'` at validation
# time (reproduced generating every DateTime-bearing model before this fix).
_FORMAT_PATTERN_CLASH = {"date-time", "date", "duration", "uuid"}


def _module_name(schema_stem: str) -> str:
    """``ingest-request`` -> ``ingest_request`` (matches datamodel-code-generator's own
    kebab-to-snake conversion of the input filename it is given, bible §6.4 kebab schema names).
    """
    return schema_stem.replace("-", "_")


def _rewrite_ref_value(value: str, own_module: str) -> str:
    match = _URN_REF.match(value)
    if match:
        target_module = _module_name(match.group(1))
        fragment = match.group(2) or ""
        return f"{target_module}.json{fragment}"
    if value.startswith("#"):
        return f"{own_module}.json{value}"
    return value


def _resolve_def(ref_value: str, own_kebab: str, all_schemas: dict[str, dict[str, object]]) -> dict[str, object]:
    """Look up the ``$defs`` node a (same-file or ``urn:``) ``$ref`` points at."""
    match = _URN_REF.match(ref_value)
    target_kebab = match.group(1) if match else own_kebab
    fragment = (match.group(2) if match else ref_value) or ""
    def_name = fragment.rsplit("/", 1)[-1]
    defs = all_schemas[target_kebab].get("$defs", {})
    assert isinstance(defs, dict)  # noqa: S101 - schemas/ is trusted repository input, not user data
    target = defs[def_name]
    assert isinstance(target, dict)  # noqa: S101
    return target


def _property_names_leaf(value: object, own_kebab: str, all_schemas: dict[str, dict[str, object]]) -> object:
    """Inline a ``propertyNames: {"$ref": X}`` into ``X``'s own ``type``/``pattern`` (dropping the
    ``$ref``) so the generated dict key stays a plain ``str`` instead of a named model class.

    ``schemas/*.schema.json`` uses ``propertyNames: {"$ref": ...}`` to constrain an open object's
    *keys* to a named scalar type (``TokenizerId``, ``MetricKey``, ``PluginId``, bible §5.3/§6.1).
    datamodel-code-generator instead reads this as "the dict key type is that $def's own
    RootModel class" (``dict[TokenizerId, TokenCounts]``), and Pydantic v2 models are unhashable
    unless frozen, so pydantic-core raises ``TypeError: unhashable type: 'TokenizerId'`` the
    moment such a dict is validated. The referenced type's `pattern` already fully constrains the
    key string; nothing is lost by inlining it and dropping the class indirection.
    """
    if not (isinstance(value, dict) and set(value) == {"$ref"}):
        return value
    ref_value = value["$ref"]
    assert isinstance(ref_value, str)  # noqa: S101 - schemas/ is trusted repository input
    target = _resolve_def(ref_value, own_kebab, all_schemas)
    return {k: v for k, v in target.items() if k in {"type", "pattern", "minLength", "maxLength"}}


def _rewrite_node(node: object, own_kebab: str, all_schemas: dict[str, dict[str, object]]) -> object:
    own_module = _module_name(own_kebab)
    if isinstance(node, dict):
        has_pattern = "pattern" in node
        out: dict[str, object] = {}
        for key, value in node.items():
            if key == "$ref" and isinstance(value, str):
                out[key] = _rewrite_ref_value(value, own_module)
            elif key == "format" and has_pattern and value in _FORMAT_PATTERN_CLASH:
                continue
            elif key == "uniqueItems":
                # pydantic-core enforces this by hashing every item, which raises `TypeError:
                # unhashable type` for a $ref item type generated as a plain (non-frozen)
                # BaseModel/RootModel. jsonschema (used by tests/contracts against the untouched
                # schemas/ files, not this temp copy) still enforces uniqueness for docs/API
                # validation; only the generated model's own runtime re-check is dropped here.
                continue
            elif key == "propertyNames":
                out[key] = _rewrite_node(_property_names_leaf(value, own_kebab, all_schemas), own_kebab, all_schemas)
            else:
                out[key] = _rewrite_node(value, own_kebab, all_schemas)
        return out
    if isinstance(node, list):
        return [_rewrite_node(item, own_kebab, all_schemas) for item in node]
    return node


def _is_pure_ref_wrapper(schema: dict[str, object]) -> bool:
    """True for a schema whose only substantive keyword is a top-level ``$ref``.

    Six schemas (``stage-error``, ``problem-details``, ``capabilities``, ``stage-policy``,
    ``tiering-policy``, ``egress-policy``) exist only so ``schemas/`` has one file per contract
    name; their own description says so verbatim ("이 파일은 인벤토리 게시용 $ref 래퍼다"). The real
    model lives in the ``common-types`` ``$def`` they point at, so the flat ``common_types`` class
    — not a ``RootModel`` wrapper around it — should win the package-level re-export. Schemas that
    add anything of their own (``cloud-event-envelope`` also has ``$defs``/``oneOf``) keep their
    dedicated module instead.
    """
    return set(schema.keys()) - {"$schema", "$id", "title", "description", "$comment"} == {"$ref"}


def _schema_titles() -> tuple[dict[str, str], set[str]]:
    """Map each schema's module name to its ``title``, plus the set of pure-``$ref``-wrapper modules."""
    titles: dict[str, str] = {}
    thin_modules: set[str] = set()
    for path in sorted(SCHEMAS_DIR.glob("*.schema.json")):
        stem = path.name.removesuffix(".schema.json")
        data = json.loads(path.read_text(encoding="utf-8"))
        title = data.get("title")
        if not title:
            msg = f'{path.name}: missing top-level "title" (needed to name the generated re-export)'
            raise SystemExit(msg)
        module = _module_name(stem)
        titles[module] = title
        if _is_pure_ref_wrapper(data):
            thin_modules.add(module)
    return titles, thin_modules


def _common_type_pattern(def_name: str) -> str:
    """Read the ``pattern`` of ``common-types.schema.json``'s ``$defs/{def_name}`` verbatim.

    Used to embed ``SEMVER_RE``/``SCHEMA_TYPE_RE`` in the generated ``versioning.py`` (see
    ``write_versioning``) so those regexes can never drift from the schema every other generated
    contract module already relies on (bible §6.4, §12).
    """
    common_types_schema = json.loads((SCHEMAS_DIR / "common-types.schema.json").read_text(encoding="utf-8"))
    defs = common_types_schema["$defs"]
    assert isinstance(defs, dict)  # noqa: S101 - schemas/ is trusted repository input, not user data
    pattern = defs[def_name]["pattern"]
    assert isinstance(pattern, str)  # noqa: S101
    return pattern


_VERSIONING_SOURCE = '''"""{generated_note}

역할: `schema_version` 호환성 엔진 — 스키마에서 생성한 데이터 모델이 아니라 버전 비교·업캐스팅 규칙을 담은
코드 전용 모듈이다(`rag_platform.contracts.versioning`).
설계 근거: 바이블 §6.4(`schema_version` semver 규칙 — 추가는 minor, 제거·의미 변경은 major), §12(모듈 맵의
`versioning.py`), `docs/03-contracts/14-schema-versioning-and-compatibility.md` §1.2·§4.1~4.3·§6.2.
구성: `SchemaVersion`(파싱·비교) · `compat_matcher`(`contracts_compat` 범위 판정) · `VersionedEnvelope`(봉투
불변식을 검증하는 코드 전용 기반 클래스) · `UpcasterRegistry`/`judge_compat`(생산자·소비자 호환 매트릭스) ·
`prune_unknown`(관용적 읽기 시안, 기본 동작 아님).
불변식: `SEMVER_RE`/`SCHEMA_TYPE_RE`는 `schemas/common-types.schema.json`에서 생성 시점에 그대로 복사되므로
스키마와 어긋날 수 없다; `SchemaDiffReport`는 `schema_diff_report.py`가 이미 생성하므로 여기서 반복하지 않는다;
손으로 고친 내용은 다음 재생성 때 사라진다.
검증 계층: 1층(여기서 검증) — `tests/unit/test_contracts_versioning.py`.
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
SEMVER_RE = {semver_re!r}

# 03-contracts/14 §1.2: schema_version (envelope, ArtifactRef.schema_version) forbids the
# pre-release/build metadata that the general-purpose common Semver $def otherwise allows; this
# restriction is enforced as invariant 1 here, in code, not in schemas/ (03-contracts/14 §1.2).
RELEASE_SEMVER_RE = r"^(0|[1-9]\\d*)\\.(0|[1-9]\\d*)\\.(0|[1-9]\\d*)$"

# Copied verbatim from schemas/common-types.schema.json $defs/SchemaTypeName (see SEMVER_RE above).
SCHEMA_TYPE_RE = {schema_type_re!r}

# Copied verbatim from schemas/common-types.schema.json $defs/ContractsCompat (promoted there in
# bible 1.3.0 AM-35; see SEMVER_RE above). Full syntax check for a contracts_compat range
# (03-contracts/14 §4.3); a caller that already passed Pydantic/JSON Schema validation never hits
# compat_matcher's ValueError. Individual clauses are then re-parsed with _COMPAT_CLAUSE_RE below.
_COMPAT_FULL_RE = {compat_re!r}
_COMPAT_CLAUSE_RE = re.compile(r"(>=|<=|==|<|>)(\\d+)\\.(\\d+)")

CompatDecision = Literal["load", "load_tolerant", "upcast", "reject"]

_COMPARISONS: dict[str, Callable[[tuple[int, int], tuple[int, int]], bool]] = {{
    ">=": lambda have, want: have >= want,
    "<=": lambda have, want: have <= want,
    "==": lambda have, want: have == want,
    "<": lambda have, want: have < want,
    ">": lambda have, want: have > want,
}}


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
            msg = f"schema_version format violation (contract.violation: schema_version format): {{text!r}}"
            raise ValueError(msg)
        if not re.fullmatch(RELEASE_SEMVER_RE, text):
            msg = (
                "schema_version forbids pre-release/build metadata "
                f"(contract.violation, 03-contracts/14 §1.2): {{text!r}}"
            )
            raise ValueError(msg)
        major, minor, patch = (int(part) for part in text.split("."))
        return cls(major, minor, patch)


def compat_matcher(contracts_compat: str) -> Callable[[SchemaVersion], bool]:
    """Turn a contracts_compat range (e.g. ">=1.0,<2.0") into a predicate (03-contracts/14 §4.3).

    Patch never participates in the comparison.
    """
    if not re.fullmatch(_COMPAT_FULL_RE, contracts_compat):
        msg = f"contracts_compat format violation: {{contracts_compat!r}}"
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
            msg = f"schema_type {{self.schema_type!r}} != {{type(self).__name__!r}} (contract.violation)"
            raise ValueError(msg)
        return self


Upcaster = Callable[[dict[str, Any]], dict[str, Any]]


class UpcasterRegistry:
    """One pure function per major boundary, ``N.x -> N+1.0.0`` (03-contracts/14 §6.2, proposal).

    Minor versions inside a major are never transformed (additive-only, §2.1): a consumer whose
    minor is >= the payload's needs no upcasting at all (see judge_compat row 6).
    """

    def __init__(self) -> None:
        self._steps: dict[tuple[str, int], Upcaster] = {{}}

    def register(self, schema_type: str, from_major: int) -> Callable[[Upcaster], Upcaster]:
        """Register the single upcaster for `schema_type` from major `from_major` to `from_major + 1`."""

        def decorator(fn: Upcaster) -> Upcaster:
            key = (schema_type, from_major)
            if key in self._steps:
                msg = f"duplicate upcaster registration: {{key!r}}"
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
            payload["schema_version"] = f"{{major + 1}}.0.0"
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
        pruned: dict[str, Any] = {{}}
        for key, value in payload.items():
            if key in schema["properties"]:
                pruned[key] = prune_unknown(value, schema["properties"][key], defs, dropped, f"{{path}}/{{key}}")
            elif schema.get("additionalProperties", False) is False:
                dropped.append(f"{{path}}/{{key}}")
            else:
                pruned[key] = value
        return pruned
    if isinstance(payload, list) and "items" in schema:
        return [
            prune_unknown(item, schema["items"], defs, dropped, f"{{path}}/{{index}}")
            for index, item in enumerate(payload)
        ]
    return payload
'''


def write_versioning() -> None:
    """Write ``versioning.py`` (see the module docstring's pipeline step 4 and ``_VERSIONING_SOURCE``).

    Not schema-derived (no ``datamodel_code_generator`` involved); the file content is a fixed
    template owned by this script, with only the ``common-types.schema.json``-sourced regex
    patterns substituted in, so it can never hand-drift from the schema (bible §6.4, §12).
    """
    source = _VERSIONING_SOURCE.format(
        generated_note=GENERATED_NOTE,
        semver_re=_common_type_pattern("Semver"),
        schema_type_re=_common_type_pattern("SchemaTypeName"),
        compat_re=_common_type_pattern("ContractsCompat"),
    )
    (OUTPUT_DIR / "versioning.py").write_text(source, encoding="utf-8")


def prepare_temp_schemas(tmp_dir: Path) -> None:
    """Copy every schema into ``tmp_dir``, rewriting ``$ref`` to explicit relative form and
    fixing the two datamodel-code-generator/pydantic-core clashes described on ``_rewrite_node``
    and ``_property_names_leaf`` (format/pattern, propertyNames/$ref).
    """
    all_schemas = {
        path.name.removesuffix(".schema.json"): json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(SCHEMAS_DIR.glob("*.schema.json"))
    }
    for kebab, data in all_schemas.items():
        rewritten = _rewrite_node(data, kebab, all_schemas)
        (tmp_dir / f"{_module_name(kebab)}.json").write_text(json.dumps(rewritten), encoding="utf-8")


def run_datamodel_codegen(tmp_dir: Path) -> None:
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        "-m",
        "datamodel_code_generator",
        "--input",
        str(tmp_dir),
        "--input-file-type",
        "jsonschema",
        "--output",
        str(OUTPUT_DIR),
        "--output-model-type",
        "pydantic_v2.BaseModel",
        "--use-standard-collections",
        "--use-union-operator",
        "--field-constraints",
        "--strict-nullable",
        "--use-schema-description",
        "--target-python-version",
        "3.12",
        # Enums as StrEnum (bible §12 `contracts` single enum source; 10-development/03 §… `StrEnum`).
        "--use-specialized-enum",
        "--enum-field-as-literal",
        "none",
        "--disable-timestamp",
        "--custom-file-header",
        GENERATED_FILE_HEADER,
    ]
    subprocess.run(cmd, cwd=ROOT, check=True)


_CLASS_DEF = re.compile(r"^class ([A-Za-z_][A-Za-z0-9_]*)\(", re.MULTILINE)


def _primary_file(module: str) -> Path:
    as_file = OUTPUT_DIR / f"{module}.py"
    if as_file.exists():
        return as_file
    as_package_init = OUTPUT_DIR / module / "__init__.py"
    if as_package_init.exists():
        return as_package_init
    msg = f"contracts_gen: generated module {module!r} not found as a file or a package"
    raise SystemExit(msg)


def write_init(titles: dict[str, str], thin_modules: set[str]) -> None:
    """Regenerate ``__init__.py`` re-exporting the primary model of every schema plus the
    remaining shared ``common_types`` classes (bible §12: `common_types` is the single source for
    the §5.3 common types and §5.7 enums that other contract modules import).
    """
    modules = sorted(p.stem for p in OUTPUT_DIR.glob("*.py") if p.stem != "__init__")
    modules += sorted(p.name for p in OUTPUT_DIR.iterdir() if p.is_dir() and (p / "__init__.py").exists())
    modules = sorted(set(modules))

    exports: dict[str, str] = {}  # class name -> module name, first writer wins

    # 1. Every public class defined directly in common_types (bible §5.3 common types, §5.7 enum
    #    single source). A pure-$ref wrapper schema (step 2) never overrides these: its class is
    #    just a `RootModel[common_types.X]` around the same $def (see `_is_pure_ref_wrapper`).
    common_text = _primary_file(COMMON_MODULE).read_text(encoding="utf-8")
    for match in _CLASS_DEF.finditer(common_text):
        exports[match.group(1)] = COMMON_MODULE

    # 2. Each non-wrapper schema's own title (cloud-event-envelope's fuller discriminated union,
    #    and every schema that is not just a same-named common_types $def in a trench coat).
    for module, title in titles.items():
        if module not in modules:
            msg = f"contracts_gen: expected generated module {module!r} for schema title {title!r}"
            raise SystemExit(msg)
        class_re = re.compile(rf"^class {re.escape(title)}\(", re.MULTILINE)
        if not class_re.search(_primary_file(module).read_text(encoding="utf-8")):
            msg = f"contracts_gen: {module!r} does not define expected top-level class {title!r}"
            raise SystemExit(msg)
        if module in thin_modules and title in exports:
            continue
        exports[title] = module

    by_module: dict[str, list[str]] = {}
    for name, module in exports.items():
        by_module.setdefault(module, []).append(name)

    lines = [
        f'"""{GENERATED_NOTE}',
        "",
        "역할: `schemas/*.schema.json`에서 생성한 계약 모델 패키지(계층 L0)의 공개 진입점 — 스키마별 대표 모델과",
        "`common_types`의 공유 타입·열거값을 재노출(re-export)한다.",
        "설계 근거: 바이블 §5.1(계약이 정본), §5.7(열거값은 `common_types`가 단일 출처), §12(레이어 지도),",
        "10-development/01 §6(생성 파일은 손으로 고치지 않는다).",
        "구성: 스키마별 대표 클래스(스키마 `title`) + `common_types`에 직접 정의된 공개 클래스를 재노출한다.",
        "불변식: 이 패키지는 pydantic과 표준 라이브러리만 import한다; 손으로 고친 내용은 다음 재생성 때 사라진다.",
        "검증 계층: 1층(여기서 검증) — tests/contracts, tools/validate-contracts.mjs.",
        '"""',
        "",
        "from __future__ import annotations",
        "",
    ]
    for module in sorted(by_module):
        names = sorted(by_module[module])
        imported = ", ".join(f"{name} as {name}" for name in names)
        lines.append(f"from .{module} import {imported}")
    lines.append("")
    lines.append("__all__ = [")
    lines.extend(f'    "{name}",' for name in sorted(exports))
    lines.append("]")
    lines.append("")

    (OUTPUT_DIR / "__init__.py").write_text("\n".join(lines), encoding="utf-8")


def run_ruff() -> None:
    rel = OUTPUT_DIR.relative_to(ROOT)
    subprocess.run([sys.executable, "-m", "ruff", "check", "--fix", str(rel)], cwd=ROOT, check=True)
    subprocess.run([sys.executable, "-m", "ruff", "format", str(rel)], cwd=ROOT, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--keep-temp", action="store_true", help="print the temp dir path instead of deleting it")
    parser.add_argument("--no-format", action="store_true", help="skip the ruff check --fix / format pass")
    args = parser.parse_args()

    titles, thin_modules = _schema_titles()

    tmp_dir = Path(tempfile.mkdtemp(prefix="rag-contracts-gen-"))
    try:
        prepare_temp_schemas(tmp_dir)
        run_datamodel_codegen(tmp_dir)
    finally:
        if args.keep_temp:
            print(f"contracts_gen: kept temp schema copies at {tmp_dir}", file=sys.stderr)
        else:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    write_init(titles, thin_modules)
    write_versioning()

    if not args.no_format:
        run_ruff()

    print(f"contracts_gen: regenerated {OUTPUT_DIR.relative_to(ROOT)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
