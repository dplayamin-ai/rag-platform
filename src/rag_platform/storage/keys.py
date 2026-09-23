"""Object key conventions (bible §13.3): pure functions, no I/O.

Canon: design bible §13.3 (object key table), §6.2 (hash combination rules), §6.4 (`schema_type`
is PascalCase; the object key uses its kebab-case form, "`schema_type_kebab`"); ADR-0037
(`stage_key` scope and cache classes).
"""

from __future__ import annotations

import re

__all__ = [
    "artifact_key",
    "artifact_key_by_hash",
    "derived_key",
    "kebab_case",
    "llm_enrich_key",
    "source_key",
]

_PASCAL_BOUNDARY = re.compile(r"(?<!^)(?=[A-Z])")


def kebab_case(schema_type: str) -> str:
    """PascalCase `schema_type` -> kebab-case (`ParsedDocument` -> `parsed-document`, bible §13.3)."""
    if not schema_type or not schema_type[0].isupper():
        msg = f"schema_type must be PascalCase (bible §6.4): {schema_type!r}"
        raise ValueError(msg)
    return _PASCAL_BOUNDARY.sub("-", schema_type).lower()


_MIN_HEX_PREFIX_LENGTH = 2  # every key shards on the first two hex characters (bible §13.3 `{blake3[:2]}`)


def _require_hex(value: str, name: str) -> None:
    if len(value) < _MIN_HEX_PREFIX_LENGTH or not all(c in "0123456789abcdef" for c in value):
        msg = f"{name} must be lowercase hex (bible §6.1): {value!r}"
        raise ValueError(msg)


def source_key(tenant_id: str, blake3_hex: str) -> str:
    """Original bytes: `tenants/{tenant_id}/sources/{blake3[:2]}/{blake3}` (bible §13.3)."""
    _require_hex(blake3_hex, "blake3_hex")
    return f"tenants/{tenant_id}/sources/{blake3_hex[:2]}/{blake3_hex}"


def artifact_key(tenant_id: str, schema_type: str, stage_key: str) -> str:
    """Cacheable stage output (envelope carried): keyed by `stage_key` (ADR-0037, bible §13.3)."""
    _require_hex(stage_key, "stage_key")
    return f"tenants/{tenant_id}/artifacts/{kebab_case(schema_type)}/{stage_key[:2]}/{stage_key}.json"


def artifact_key_by_hash(tenant_id: str, schema_type: str, blake3_hex: str) -> str:
    """Cache-exempt stage output (`fetch`, `index`): keyed by the byte hash (bible §13.3, 1.3.0)."""
    _require_hex(blake3_hex, "blake3_hex")
    return f"tenants/{tenant_id}/artifacts/{kebab_case(schema_type)}/{blake3_hex[:2]}/{blake3_hex}.json"


def derived_key(tenant_id: str, kind: str, blake3_hex: str, ext: str) -> str:
    """Envelope-free derived byte object, shared within a tenant (bible §13.3, ADR-0037)."""
    _require_hex(blake3_hex, "blake3_hex")
    return f"tenants/{tenant_id}/derived/{kind}/{blake3_hex[:2]}/{blake3_hex}.{ext}"


def llm_enrich_key(tenant_id: str, cache_key_hex: str) -> str:
    """LLM enrichment cache: `key = H("llm-enrich", ...)` (bible §6.2, §13.3)."""
    _require_hex(cache_key_hex, "cache_key_hex")
    return f"tenants/{tenant_id}/derived/llm_enrich/{cache_key_hex[:2]}/{cache_key_hex}.json"
