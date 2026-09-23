"""프로파일 스키마 검증 + 바이블 §7.4 로딩 시 검증 규칙의 부분 구현.

설계 근거: 바이블 §7.4("로딩 시 검증 규칙과 게이트"), §5.7 `SourceFormat`(13종);
`schemas/profile.schema.json`(jsonschema Draft 2020-12 + `urn:rag:schema:*` 참조 레지스트리 —
`plugins.registry`가 `plugin-meta.schema.json`을 다루는 방식과 동일).

구성:
- `validate_schema(profile, *, schemas_dir=...)` — `profile.schema.json` 대조 검증
- `validate_loading_rules(profile)` — 규칙 (3)/(10)/(11)/(12) 적용, 위반 시 `ProfileInvalidError`
- `ProfileInvalidError` — `profile.invalid`(바이블 §5.7), 위반 규칙 전체를 `.issues`에 담음
- `SOURCE_FORMATS`, `DEFAULT_DENY_CIDRS` — §5.7/§5.3 정본 값

불변식·주의: 해석된 프로파일 문서만으로 판정 가능한 규칙 (3) `fusion.k`, (10) `parse.router`의
`SourceFormat` 커버리지, (11) hydrate/rerank/pack 예산 부등식, (12) `deny_cidrs` 하한만
구현한다. 살아있는 `PluginRegistry`가 필요한 규칙 (1)/(2)/(4)/(5)/(6)/(8)/(9)(라이선스·
`capabilities()` 교차 검증)는 `plugins.registry`의 `check_license`/`check_capabilities`가
담당하며 이 검증기의 범위 밖이다.
검증 계층: 1층(여기서 검증) — `tests/unit/test_profiles_validate.py`.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jsonschema
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

__all__ = [
    "DEFAULT_DENY_CIDRS",
    "SOURCE_FORMATS",
    "ProfileInvalidError",
    "validate_loading_rules",
    "validate_schema",
]

_SCHEMAS_DIR = Path(__file__).resolve().parents[3] / "schemas"
_PROFILE_SCHEMA_ID = "urn:rag:schema:profile:1"

# Bible §5.7 `SourceFormat`, all 13 values; rule (10) requires every one as a `parse.router` key.
SOURCE_FORMATS: tuple[str, ...] = (
    "hwpx",
    "hwp5",
    "hwp3",
    "pdf",
    "docx",
    "doc",
    "rtf",
    "odt",
    "html",
    "txt",
    "md",
    "json",
    "unknown",
)

# Bible §5.3 `EgressPolicy.deny_cidrs` default (private/loopback/link-local/cloud-metadata); rule
# (12) forbids shrinking this set.
DEFAULT_DENY_CIDRS: frozenset[str] = frozenset(
    {
        "10.0.0.0/8",
        "172.16.0.0/12",
        "192.168.0.0/16",
        "127.0.0.0/8",
        "169.254.0.0/16",
        "0.0.0.0/8",
        "::1/128",
        "fc00::/7",
        "fe80::/10",
    }
)


class ProfileInvalidError(Exception):
    """`profile.invalid` (bible §5.7): carries every violated rule in `.issues`."""

    def __init__(self, issues: list[str]) -> None:
        """Build a `ProfileInvalidError` carrying every violated rule message in `issues`."""
        super().__init__("; ".join(issues))
        self.issues = issues


def _build_registry(schemas_dir: Path = _SCHEMAS_DIR) -> Registry:
    resources: list[tuple[str, Resource]] = []
    for path in schemas_dir.glob("*.schema.json"):
        contents = json.loads(path.read_text(encoding="utf-8"))
        resources.append((contents["$id"], Resource.from_contents(contents, default_specification=DRAFT202012)))
    return Registry().with_resources(resources)


def validate_schema(profile: dict[str, Any], *, schemas_dir: Path = _SCHEMAS_DIR) -> None:
    """Validate `profile` against `schemas/profile.schema.json` (raises `jsonschema.ValidationError`)."""
    registry = _build_registry(schemas_dir)
    schema = registry.contents(_PROFILE_SCHEMA_ID)
    jsonschema.Draft202012Validator(schema, registry=registry).validate(profile)


def _rule_fusion_k(profile: dict[str, Any], issues: list[str]) -> None:
    """(3) `fusion.k` is required."""
    fusion = profile.get("query", {}).get("fusion", {})
    if not isinstance(fusion.get("k"), int) or fusion["k"] <= 0:
        issues.append("(3) query.fusion.k must be a positive integer")


def _rule_parse_router_covers_source_format(profile: dict[str, Any], issues: list[str]) -> None:
    """(10) `parse.router` must have every `SourceFormat` value as a key."""
    router = profile.get("ingest", {}).get("parse", {}).get("router", {})
    missing = [fmt for fmt in SOURCE_FORMATS if fmt not in router]
    if missing:
        issues.append(f"(10) ingest.parse.router is missing SourceFormat keys: {missing}")


def _rule_hydrate_top_n(profile: dict[str, Any], issues: list[str]) -> None:
    """(11) `query.hydrate.top_n >= max(rerank.top_n_in, pack.k_max)`."""
    query = profile.get("query", {})
    top_n = query.get("hydrate", {}).get("top_n")
    top_n_in = query.get("rerank", {}).get("top_n_in", 0)
    k_max = query.get("pack", {}).get("k_max", 0)
    if not isinstance(top_n, int) or top_n < max(top_n_in, k_max):
        issues.append(f"(11) query.hydrate.top_n ({top_n}) must be >= max(rerank.top_n_in, pack.k_max)")


def _rule_deny_cidrs_floor(profile: dict[str, Any], issues: list[str]) -> None:
    """(12) `runtime.egress.deny_cidrs` must include the bible §5.3 default set; never shrunk."""
    deny_cidrs = set(profile.get("runtime", {}).get("egress", {}).get("deny_cidrs", ()))
    missing = DEFAULT_DENY_CIDRS - deny_cidrs
    if missing:
        issues.append(f"(12) runtime.egress.deny_cidrs is missing required entries: {sorted(missing)}")


def validate_loading_rules(profile: dict[str, Any]) -> None:
    """Apply the implementable subset of bible §7.4 loading rules; raise `ProfileInvalidError`."""
    issues: list[str] = []
    _rule_fusion_k(profile, issues)
    _rule_parse_router_covers_source_format(profile, issues)
    _rule_hydrate_top_n(profile, issues)
    _rule_deny_cidrs_floor(profile, issues)
    if issues:
        raise ProfileInvalidError(issues)
