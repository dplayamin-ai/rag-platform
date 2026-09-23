"""Unit tests for `rag_platform.storage.keys` (bible §13.3 object key convention)."""

from __future__ import annotations

import pytest

from rag_platform.storage.keys import (
    artifact_key,
    artifact_key_by_hash,
    derived_key,
    kebab_case,
    llm_enrich_key,
    source_key,
)

_HEX64 = "ab" * 32
_HEX2 = "ab"


@pytest.mark.parametrize(
    ("pascal", "expected"),
    [
        ("ParsedDocument", "parsed-document"),
        ("ChunkSet", "chunk-set"),
        ("IndexCommit", "index-commit"),
        ("SourceDocument", "source-document"),
    ],
)
def test_kebab_case(pascal: str, expected: str) -> None:
    assert kebab_case(pascal) == expected


def test_kebab_case_rejects_non_pascal_input() -> None:
    with pytest.raises(ValueError, match="PascalCase"):
        kebab_case("parsed_document")


def test_source_key_layout() -> None:
    assert source_key("t1", _HEX64) == f"tenants/t1/sources/{_HEX2}/{_HEX64}"


def test_artifact_key_layout_uses_stage_key() -> None:
    key = artifact_key("t1", "ParsedDocument", _HEX64)
    assert key == f"tenants/t1/artifacts/parsed-document/{_HEX2}/{_HEX64}.json"


def test_artifact_key_by_hash_layout_for_cache_exempt_stages() -> None:
    key = artifact_key_by_hash("t1", "SourceDocument", _HEX64)
    assert key == f"tenants/t1/artifacts/source-document/{_HEX2}/{_HEX64}.json"


def test_derived_key_layout() -> None:
    key = derived_key("t1", "page_image", _HEX64, "png")
    assert key == f"tenants/t1/derived/page_image/{_HEX2}/{_HEX64}.png"


def test_llm_enrich_key_layout() -> None:
    key = llm_enrich_key("t1", _HEX64)
    assert key == f"tenants/t1/derived/llm_enrich/{_HEX2}/{_HEX64}.json"


def test_hash_validation_rejects_short_or_non_hex_values() -> None:
    with pytest.raises(ValueError, match="hex"):
        source_key("t1", "not-hex!!")
    with pytest.raises(ValueError, match="hex"):
        artifact_key("t1", "ParsedDocument", "a")  # too short
