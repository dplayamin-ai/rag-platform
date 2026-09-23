"""오브젝트 키 규약(바이블 §13.3): 순수 함수, I/O 없음.

역할: 테넌트별 소스·파생·아티팩트·LLM 보강 캐시 오브젝트의 저장 경로 문자열을 계산한다.
설계 근거: 바이블 §13.3(오브젝트 키 표), §6.2(해시 조합 규칙), §6.4(`schema_type`은 PascalCase,
오브젝트 키는 그 kebab-case 형인 `schema_type_kebab`); ADR-0037(`stage_key` 스코프와 캐시 클래스).
구성: `kebab_case` — PascalCase → kebab-case; `source_key`/`derived_key` — 콘텐츠 해시 기반 키;
`artifact_key`(`stage_key` 기반, 캐시 가능) / `artifact_key_by_hash`(바이트 해시 기반, 캐시 예외
`fetch`/`index`); `llm_enrich_key` — LLM 보강 캐시 키.
불변식: 모든 해시 인자는 소문자 hex여야 한다(`_require_hex`가 강제); 키는 첫 두 hex 문자로
샤딩한다(`{hash[:2]}`).
검증 계층: 1층(여기서 검증) — tests/unit/test_storage_keys.py.
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
