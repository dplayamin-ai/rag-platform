"""Regenerate ``src/rag_platform/contracts/`` from ``schemas/*.schema.json``.

GENERATED CONTRACTS BUILD SCRIPT — this script itself is hand-written and owned by the
repository, but everything it writes under ``src/rag_platform/contracts/`` is a build product.
Bible §5.1/§12: ``schemas/*.schema.json`` (JSON Schema 2020-12) is the source of truth for the
contract models; the Pydantic v2 package is generated, never hand-edited.

Pipeline:

1. Copy ``schemas/*.schema.json`` into a temporary directory as a parsed-JSON tree transform
   (not text regex), rewriting every ``$ref`` (``urn:rag:schema:<name>:1#/$defs/X`` and bare
   same-file ``#/$defs/X``) into an explicit relative reference ``<name>.json#/$defs/X`` against
   the temp copy's own filename (``<name>`` is the schema's kebab-case stem with ``-`` replaced by
   ``_``, matching the module name datamodel-code-generator derives from the file it is given).
   Rewriting *all* refs to the explicit form — not just cross-file ones — works around a
   datamodel-code-generator limitation where a bare ``#/$defs/X`` fragment pulled in through a
   cross-file ``$ref`` is resolved against the *importing* file instead of the file that actually
   defines it (reproduced with ``cloud-event-envelope.schema.json`` pulling ``CloudEventEnvelope``
   out of ``common-types.schema.json``). The same pass drops a ``format`` keyword wherever a
   sibling ``pattern`` also constrains the string (``_FORMAT_PATTERN_CLASH``): datamodel-code-
   generator maps ``format: date-time``/``date``/``duration``/``uuid`` to a non-str Python type
   and then, under ``--field-constraints``, tries to attach the sibling ``pattern`` to that same
   type, which raises at validation time (``TypeError: Unable to apply constraint 'pattern' ...
   for schema of type 'datetime'``) — every ``DateTime``/``Date``/``Uuid`` field, so every model
   that carries one. ``pattern`` alone already fully constrains the string.
2. Run datamodel-code-generator (``pydantic_v2.BaseModel``, one module per schema file;
   ``common_types.py`` is the shared module every other module imports from) into
   ``src/rag_platform/contracts/``.
3. Regenerate ``src/rag_platform/contracts/__init__.py`` to re-export, by explicit
   ``import X as X`` (required for mypy ``--no-implicit-reexport`` under ``strict = true``), the
   top-level model named after each schema's ``title`` plus every remaining public class defined
   directly in ``common_types`` (the shared bible §5.3 types and §5.7 enums) that no dedicated
   per-schema module already claims (the wrapper schemas ``stage-error``, ``problem-details``,
   ``capabilities``, ``stage-policy``, ``tiering-policy``, ``egress-policy`` and
   ``cloud-event-envelope`` each ``$ref`` a same-named ``common-types`` ``$def``; the dedicated
   module wins the name).
4. Run ``ruff check --fix`` and ``ruff format`` over the generated package only.

Run: ``uv run python tools/contracts_gen.py`` (add ``--keep-temp`` to inspect the rewritten
schema copies, or ``--no-format`` to skip the ruff pass for faster iteration while debugging
generator flags).
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

GENERATED_NOTE = "GENERATED — do not edit; run `uv run python tools/contracts_gen.py` to regenerate."

# `datamodel-code-generator` writes `--custom-file-header` verbatim at the top of every generated
# file (it does not comment-prefix it), so this must already be valid Python — a triple-quoted
# module docstring rather than `#` comments, so every generated (sub)package still has a non-empty
# `__doc__` (tests/unit/test_scaffold.py walks every package under rag_platform and asserts this;
# `from __future__ import annotations` is allowed to follow a module docstring).
GENERATED_FILE_HEADER = f'"""{GENERATED_NOTE}\n\nSource of truth: schemas/*.schema.json (bible §5.1, §6.4, §12)."""'

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
        '"""Contract models generated from ``schemas/*.schema.json`` (layer L0).',
        "",
        GENERATED_NOTE,
        "",
        "Every module in this package is produced by ``uv run python tools/contracts_gen.py``",
        "and must not be edited by hand (bible §5.1, 10-development/01 §6). This package imports",
        "only pydantic and the standard library.",
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

    if not args.no_format:
        run_ruff()

    print(f"contracts_gen: regenerated {OUTPUT_DIR.relative_to(ROOT)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
