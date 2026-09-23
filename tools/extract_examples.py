"""Extract golden ```json examples from ``docs/03-contracts/*.md`` into fixture files.

Each ``docs/03-contracts/NN-*.md`` contract document ends with a ``## 예시`` section holding one
or more ``### 예시 N ...`` headings, each followed by one or more fenced ```json blocks that are,
per that document's own words, schema-validated golden instances (``00 §10.3``). This script finds
those blocks, works out which ``schemas/*.schema.json`` (and, for common types, which ``$defs``
entry within it) each one is an instance of, and writes them to
``tests/contracts/fixtures/<schema>/<NN>.json`` plus a ``manifest.json`` that
``tests/contracts/test_contract_roundtrip.py`` reads.

Resolution heuristic per heading (documented here because there is no single markup convention
across the 17 documents):

1. Every backtick-quoted token on the heading line is a candidate; a token is a match if its
   leading ``PascalCase`` prefix is a known schema title or ``$defs`` name (built once from every
   ``schemas/*.schema.json``, common-types included). The first match wins.
2. Failing that, a token matching the CloudEvents ``domain.entity.action`` shape (bible §6.5)
   resolves to ``cloud-event-envelope`` (whose root schema is the discriminated union over every
   event; jsonschema picks the right ``oneOf`` branch from the instance's own ``type``).
3. Failing that, a 3-digit HTTP status in the heading resolves to ``ProblemDetails`` (every
   status-coded example in these docs is a problem-details response body).
4. Failing that, the document's own ``## 예시`` intro paragraph is searched for a
   ``schemas/<name>.schema.json`` mention, which becomes the section-wide default.

A heading that still resolves to nothing is skipped and printed, per the task brief ("판정 불가는
건너뛰고 목록 출력") — a human decides whether it needs a manual fixture or a heuristic fix here.
When a resolved name exists as both a common-types ``$def`` and a dedicated wrapper schema (the six
pure-``$ref`` wrappers ``tools/contracts_gen.py`` already special-cases), the common-types location
is used so the round-trip test parses the flat model, not the wrapper ``RootModel``.

Run: ``uv run python tools/extract_examples.py`` (writes fixtures + manifest; use ``--check`` in CI
to fail if the output would change without writing).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS_DIR = ROOT / "schemas"
DOCS_DIR = ROOT / "docs" / "03-contracts"
FIXTURES_DIR = ROOT / "tests" / "contracts" / "fixtures"
MANIFEST_PATH = FIXTURES_DIR / "manifest.json"

_HEADING_RE = re.compile(r"^### (예시.*)$")
_SECTION_RE = re.compile(r"^## 예시\s*$")
_ANY_HEADING_RE = re.compile(r"^#{1,6} ")
_FENCE_START = "```json"
_FENCE_END = "```"
_BACKTICK_RE = re.compile(r"`([^`]+)`")
_PASCAL_PREFIX_RE = re.compile(r"^([A-Z][A-Za-z0-9]*)")
_EVENT_NAME_RE = re.compile(r"^[a-z][a-z_]*(?:\.[a-z][a-z_]*){2}$")
_HTTP_STATUS_RE = re.compile(r"(?<!\d)[1-5]\d{2}(?!\d)")
_SCHEMA_FILE_MENTION_RE = re.compile(r"schemas/([a-z0-9-]+)\.schema\.json")


def _module_name(kebab: str) -> str:
    return kebab.replace("-", "_")


def _is_pure_ref_wrapper(schema: dict[str, Any]) -> bool:
    """See ``tools/contracts_gen.py::_is_pure_ref_wrapper`` (kept in sync, not imported, so this
    script has no import-time dependency on the generator or the generated package).
    """
    return set(schema.keys()) - {"$schema", "$id", "title", "description", "$comment"} == {"$ref"}


class SchemaIndex:
    """``name -> (schema kebab-name, $defs name or None for the schema root)`` with the
    common-types-over-thin-wrapper preference ``contracts_gen.py`` also applies.
    """

    def __init__(self) -> None:
        self.locations: dict[str, list[tuple[str, str | None]]] = {}
        self.schema_docs: dict[str, dict[str, Any]] = {}
        thin: set[str] = set()
        for path in sorted(SCHEMAS_DIR.glob("*.schema.json")):
            kebab = path.name.removesuffix(".schema.json")
            data = json.loads(path.read_text(encoding="utf-8"))
            self.schema_docs[kebab] = data
            if _is_pure_ref_wrapper(data):
                thin.add(kebab)
            title = data.get("title")
            if title:
                self.locations.setdefault(title, []).append((kebab, None))
            for def_name in data.get("$defs", {}):
                self.locations.setdefault(def_name, []).append((kebab, def_name))
        # common-types (never thin itself) sorts ahead of any thin wrapper for the same name.
        for name, locs in self.locations.items():
            locs.sort(key=lambda loc: 0 if loc[0] not in thin else 1)
            del name  # loop variable only used for clarity above

    def resolve_token(self, token: str) -> tuple[str, str | None] | None:
        match = _PASCAL_PREFIX_RE.match(token)
        if not match:
            return None
        locations = self.locations.get(match.group(1))
        return locations[0] if locations else None


_DOC_SLUG_RE = re.compile(r"^\d+-(.+)$")


def _doc_slug_default(doc_path: Path, known_kebabs: set[str]) -> str | None:
    """``02-source-document.md`` -> ``source-document`` when that is a real schema (file section
    per the task brief); combined docs like ``09-query-request-and-query-plan`` do not match a
    single schema and fall through (their examples all name their type explicitly anyway).
    """
    match = _DOC_SLUG_RE.match(doc_path.stem)
    slug = match.group(1) if match else doc_path.stem
    return slug if slug in known_kebabs else None


def _find_intro_default(doc_text: str) -> str | None:
    lines = doc_text.splitlines()
    in_section = False
    for line in lines:
        if _SECTION_RE.match(line):
            in_section = True
            continue
        if not in_section:
            continue
        if line.startswith("### "):
            break
        found = _SCHEMA_FILE_MENTION_RE.search(line)
        if found:
            return found.group(1)
    return None


def _candidates_from_schema_type(parsed: Any, index: SchemaIndex) -> list[tuple[str, str | None]]:
    """``schema_type`` (or the first array element's) is an explicit self-declaration some
    contracts carry (e.g. ``SourceDocument.schema_type``) — the task brief names it directly as a
    resolution signal alongside heading context and the owning doc.
    """
    node = parsed[0] if isinstance(parsed, list) and parsed else parsed
    if not isinstance(node, dict):
        return []
    schema_type = node.get("schema_type")
    if not isinstance(schema_type, str):
        return []
    locations = index.locations.get(schema_type)
    return [locations[0]] if locations else []


def _iter_example_blocks(doc_text: str) -> list[tuple[str, list[str]]]:
    """Return ``(heading_text, [json_block_text, ...])`` for every heading in ``## 예시``."""
    lines = doc_text.splitlines()
    blocks: list[tuple[str, list[str]]] = []
    in_section = False
    current_heading: str | None = None
    current_jsons: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if _SECTION_RE.match(line):
            in_section = True
            i += 1
            continue
        if not in_section:
            i += 1
            continue
        if _ANY_HEADING_RE.match(line) and not _HEADING_RE.match(line):
            # A non-"### 예시" heading ends the examples section (next "##" or unrelated "###").
            break
        heading_match = _HEADING_RE.match(line)
        if heading_match:
            if current_heading is not None:
                blocks.append((current_heading, current_jsons))
            current_heading = heading_match.group(1)
            current_jsons = []
            i += 1
            continue
        if line.strip() == _FENCE_START:
            i += 1
            fence_lines: list[str] = []
            while i < len(lines) and lines[i].strip() != _FENCE_END:
                fence_lines.append(lines[i])
                i += 1
            i += 1  # skip closing fence
            if current_heading is not None:
                current_jsons.append("\n".join(fence_lines))
            continue
        i += 1
    if current_heading is not None:
        blocks.append((current_heading, current_jsons))
    return blocks


def _candidates_for_heading(heading: str, index: SchemaIndex) -> list[tuple[str, str | None]]:
    tokens = _BACKTICK_RE.findall(heading)
    resolved = [loc for tok in tokens if (loc := index.resolve_token(tok)) is not None]
    if resolved:
        return resolved
    for tok in tokens:
        if _EVENT_NAME_RE.match(tok) and "cloud-event-envelope" in index.schema_docs:
            return [("cloud-event-envelope", None)]
    if _HTTP_STATUS_RE.search(heading) and "ProblemDetails" in index.locations:
        return [index.locations["ProblemDetails"][0]]
    return []


def _schema_type_at(index: SchemaIndex, kebab: str, def_name: str | None) -> str | None:
    schema = index.schema_docs[kebab]
    node = schema if def_name is None else schema.get("$defs", {}).get(def_name, {})
    value = node.get("type") if isinstance(node, dict) else None
    return value if isinstance(value, str) else None


def _clear_fixtures() -> None:
    if not FIXTURES_DIR.exists():
        return
    for child in FIXTURES_DIR.iterdir():
        if child.is_dir():
            for fixture_file in child.glob("*.json"):
                fixture_file.unlink()


def _write_fixture(dir_name: str, seq: int, instance: object, *, write: bool) -> str:
    fixture_rel = f"{dir_name}/{seq:03d}.json"
    if write:
        fixture_path = FIXTURES_DIR / fixture_rel
        fixture_path.parent.mkdir(parents=True, exist_ok=True)
        fixture_path.write_text(json.dumps(instance, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return fixture_rel


def _extract_block(
    *,
    block_index: int,
    block_text: str,
    heading_candidates: list[tuple[str, str | None]],
    doc_default: str | None,
    index: SchemaIndex,
    per_dir_counter: dict[str, int],
    write: bool,
) -> tuple[list[dict[str, Any]], str | None]:
    """Resolve and write the fixture(s) for one ```json block; return (manifest rows, problem)."""
    try:
        parsed = json.loads(block_text)
    except json.JSONDecodeError as exc:
        return [], f"(block {block_index}): invalid JSON ({exc})"

    candidates = heading_candidates or _candidates_from_schema_type(parsed, index)
    if not candidates and doc_default:
        candidates = [(doc_default, None)]
    if not candidates:
        return [], f"(block {block_index})"

    kebab, def_name = candidates[block_index] if block_index < len(candidates) else candidates[0]
    schema_type = _schema_type_at(index, kebab, def_name)
    instances = parsed if isinstance(parsed, list) and schema_type != "array" else [parsed]
    dir_name = kebab if def_name is None else f"{kebab}__{def_name}"

    rows = []
    for instance in instances:
        per_dir_counter[dir_name] = per_dir_counter.get(dir_name, 0) + 1
        fixture_rel = _write_fixture(dir_name, per_dir_counter[dir_name], instance, write=write)
        rows.append({"fixture": fixture_rel, "schema": kebab, "def_name": def_name})
    return rows, None


def extract(*, write: bool) -> tuple[list[dict[str, Any]], list[str]]:
    index = SchemaIndex()
    manifest: list[dict[str, Any]] = []
    unresolved: list[str] = []
    per_dir_counter: dict[str, int] = {}

    if write:
        _clear_fixtures()

    known_kebabs = set(index.schema_docs)
    for doc_path in sorted(DOCS_DIR.glob("*.md")):
        doc_text = doc_path.read_text(encoding="utf-8")
        if "## 예시" not in doc_text:
            continue
        doc_default = _doc_slug_default(doc_path, known_kebabs) or _find_intro_default(doc_text)
        rel_doc = doc_path.relative_to(ROOT).as_posix()
        for heading, json_blocks in _iter_example_blocks(doc_text):
            if not json_blocks:
                continue
            heading_candidates = _candidates_for_heading(heading, index)
            for block_index, block_text in enumerate(json_blocks):
                rows, problem = _extract_block(
                    block_index=block_index,
                    block_text=block_text,
                    heading_candidates=heading_candidates,
                    doc_default=doc_default,
                    index=index,
                    per_dir_counter=per_dir_counter,
                    write=write,
                )
                if problem is not None:
                    unresolved.append(f"{rel_doc} — {heading} {problem}")
                    continue
                manifest.extend({**row, "source_doc": rel_doc, "source_heading": heading} for row in rows)

    manifest.sort(key=lambda entry: entry["fixture"])
    if write:
        FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
        MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest, unresolved


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="do not write; exit 1 if output would differ")
    args = parser.parse_args()

    if args.check:
        before = MANIFEST_PATH.read_text(encoding="utf-8") if MANIFEST_PATH.exists() else None
        manifest, unresolved = extract(write=False)
        after = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
        if before != after:
            sys.stderr.write("extract_examples: fixtures/manifest.json is stale; run without --check\n")
            return 1
    else:
        manifest, unresolved = extract(write=True)

    print(f"extract_examples: {len(manifest)} fixtures extracted", file=sys.stderr)
    if unresolved:
        print(f"extract_examples: {len(unresolved)} example(s) could not be resolved:", file=sys.stderr)
        for item in unresolved:
            print(f"  - {item}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
