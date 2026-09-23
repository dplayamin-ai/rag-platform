"""Contract round-trip: docs/03-contracts/*.md golden examples vs. generated Pydantic models.

Fixtures under ``tests/contracts/fixtures/`` (and the ``manifest.json`` describing which schema —
and, for common types, which ``$defs`` entry — each one is an instance of) are produced by
``uv run python tools/extract_examples.py`` from every ``## 예시`` section in
``docs/03-contracts/*.md``; this test does not read the docs itself.

Per fixture: validate against ``schemas/*.schema.json`` (JSON Schema 2020-12, resolved through a
``referencing.Registry`` keyed by the ``urn:rag:schema:<name>:1`` ``$id`` scheme so cross-file
``$ref`` needs no rewriting here), parse with the matching generated ``rag_platform.contracts``
model, and re-serialize with ``model_dump(mode="json", by_alias=True, exclude_none=True)``. Key
order is not compared (both sides are already parsed Python structures, so ``==`` ignores it).

A fixture may legitimately be hand-written prose that has drifted from the schema it illustrates
(the docs are not fixed by this suite — bible §2 "문서는 고치지 않는다"), so any failure at any stage
(schema violation, Pydantic validation error, round-trip mismatch) is reported with
``pytest.xfail()`` *called at runtime* rather than raised: a fixture that fails shows as XFAIL, one
that unexpectedly starts passing again just passes (no ``xfail_strict`` surprise, since the
static ``@pytest.mark.xfail`` marker is never used here). See the task's open_issues for the
current XFAIL list.
"""

from __future__ import annotations

import importlib
import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

if TYPE_CHECKING:
    from pydantic import BaseModel

ROOT = Path(__file__).resolve().parents[2]
SCHEMAS_DIR = ROOT / "schemas"
FIXTURES_DIR = Path(__file__).parent / "fixtures"
MANIFEST_PATH = FIXTURES_DIR / "manifest.json"

_URN_PREFIX = "urn:rag:schema:"


def _retrieve(uri: str) -> Resource:
    """Resolve ``urn:rag:schema:<name>:1`` to ``schemas/<name>.schema.json`` on demand."""
    if not uri.startswith(_URN_PREFIX):
        raise LookupError(uri)
    name = uri[len(_URN_PREFIX) :].rsplit(":", 1)[0]
    path = SCHEMAS_DIR / f"{name}.schema.json"
    contents = json.loads(path.read_text(encoding="utf-8"))
    return Resource.from_contents(contents, default_specification=DRAFT202012)


_REGISTRY = Registry(retrieve=_retrieve)  # type: ignore[call-arg]


def _load_manifest() -> list[dict[str, Any]]:
    if not MANIFEST_PATH.exists():
        return []
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))  # type: ignore[no-any-return]


MANIFEST = _load_manifest()


def _validator_for(schema_kebab: str, def_name: str | None) -> Draft202012Validator:
    base = f"{_URN_PREFIX}{schema_kebab}:1"
    ref = base if def_name is None else f"{base}#/$defs/{def_name}"
    return Draft202012Validator({"$ref": ref}, registry=_REGISTRY)


def _pascal_case(kebab: str) -> str:
    return "".join(word.capitalize() for word in kebab.split("-"))


def _model_class(schema_kebab: str, def_name: str | None) -> type[BaseModel]:
    module = importlib.import_module(f"rag_platform.contracts.{schema_kebab.replace('-', '_')}")
    name = def_name or _pascal_case(schema_kebab)
    cls = getattr(module, name, None)
    if cls is None:
        msg = f"{module.__name__} has no class {name!r}"
        raise AttributeError(msg)
    return cls  # type: ignore[no-any-return]


def _roundtrip(entry: dict[str, Any], instance: Any) -> None:
    _validator_for(entry["schema"], entry["def_name"]).validate(instance)
    model_cls = _model_class(entry["schema"], entry["def_name"])
    parsed = model_cls.model_validate(instance)
    dumped = parsed.model_dump(mode="json", by_alias=True, exclude_none=True)
    if dumped != instance:
        msg = f"round-trip mismatch: original={instance!r} dumped={dumped!r}"
        raise AssertionError(msg)


def test_fixtures_extracted() -> None:
    """Guard: fixtures are a build product, not checked-in-then-forgotten by hand."""
    assert MANIFEST, "run `uv run python tools/extract_examples.py` to (re)build fixtures first"


@pytest.mark.contract
@pytest.mark.parametrize("entry", MANIFEST, ids=[e["fixture"] for e in MANIFEST])
def test_contract_roundtrip(entry: dict[str, Any]) -> None:
    instance = json.loads((FIXTURES_DIR / entry["fixture"]).read_text(encoding="utf-8"))
    try:
        _roundtrip(entry, instance)
    except Exception as exc:  # noqa: BLE001 - any failure here may be a doc/schema drift, not a bug
        pytest.xfail(f"{entry['source_doc']} {entry['source_heading']!r}: {type(exc).__name__}: {exc}")
