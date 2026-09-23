"""프로파일 YAML 로더 — `extends` 단일 상속 해석, 딥 머지(deep merge), `profile_hash` 계산.

설계 근거: 바이블 §7.3(`schemas/profile.schema.json` 개요, `extends` 단일 상속),
§6.2(`profile_hash = H("profile", canonical_json(resolved))`, `H` = `sdk.hashing.hash_of`);
ADR-0031(`extends` 단일 상속, 딥 머지, 배열은 이어붙이지 않고 통째로 교체).

구성:
- `load_profile(profile_id, *, builtin_dir=BUILTIN_DIR)` — `extends` 조상 체인을 읽어 병합하고
  `profile_hash`를 채운 `ResolvedProfile` 반환
- `deep_merge(base, override)` — 딕셔너리는 키 단위 병합, 그 외 타입(배열 포함)은 통째로 교체
- `canonical_json(data)` — 바이블 §6.2 정본 직렬화(정렬된 키, 공백 없음, `ensure_ascii=false`)
- `profile_hash(resolved_without_hash)` — 이미 해석된 문서에 대해 해시만 재계산
- `ResolvedProfile` — 해석 결과(`profile_id`, `chain`, `data`, `profile_hash`)

불변식·주의: `canonical_json`은 RFC 8785(JCS)의 실용적 근사치일 뿐 완전한 구현이 아니다(Python
기본 `float`/`int` `repr` 사용, ECMAScript `Number::toString` 미구현) — YAML 스칼라만 다루는 이
로더에는 충분하다. `extends` 순환은 `ValueError`로 거부한다.
검증 계층: 1층(여기서 검증) — `tests/unit/test_profiles_loader.py`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from rag_platform.sdk.hashing import hash_of

__all__ = ["BUILTIN_DIR", "ResolvedProfile", "canonical_json", "deep_merge", "load_profile", "profile_hash"]

BUILTIN_DIR = Path(__file__).resolve().parent / "builtin"


@dataclass(frozen=True)
class ResolvedProfile:
    """A profile after `extends` resolution, with its computed `profile_hash`."""

    profile_id: str
    chain: tuple[str, ...]  # root-to-leaf ancestry, e.g. ("base", "lite", "standard")
    data: dict[str, Any]  # resolved document, `profile_hash` field filled in
    profile_hash: str


def canonical_json(data: Any) -> str:
    """Bible §6.2 `canonical_json`: sorted keys, no whitespace, `ensure_ascii=false`.

    This is a pragmatic approximation of RFC 8785 (JCS) number formatting — it relies on Python's
    default `float`/`int` `repr` rather than implementing JCS's ECMAScript `Number::toString`
    algorithm — sufficient for the profile documents this loader handles (plain YAML scalars), but
    not a full JCS implementation.
    """
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def deep_merge(base: Any, override: Any) -> Any:
    """ADR-0031 deep merge: dicts merge key by key; every other type (including arrays) is replaced."""
    if isinstance(base, dict) and isinstance(override, dict):
        merged = dict(base)
        for key, value in override.items():
            merged[key] = deep_merge(base[key], value) if key in base else value
        return merged
    return override  # arrays and scalars: child value replaces the parent's wholesale (ADR-0031)


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        loaded = yaml.safe_load(fh)
    if not isinstance(loaded, dict):
        msg = f"profile document must be a mapping: {path}"
        raise TypeError(msg)
    return loaded


def _read_chain(profile_id: str, builtin_dir: Path, seen: list[str]) -> list[dict[str, Any]]:
    """Read `profile_id` and every ancestor, in root-to-leaf order; raise on `extends` cycles."""
    if profile_id in seen:
        cycle = " -> ".join((*seen, profile_id))
        msg = f"extends cycle detected (ADR-0031 forbids cycles): {cycle}"
        raise ValueError(msg)
    path = builtin_dir / f"{profile_id}.yaml"
    if not path.is_file():
        msg = f"unknown profile_id {profile_id!r}: no such file {path}"
        raise FileNotFoundError(msg)
    doc = _load_yaml(path)
    extends = doc.get("extends")
    ancestors: list[dict[str, Any]] = []
    if extends is not None:
        ancestors = _read_chain(extends, builtin_dir, [*seen, profile_id])
    return [*ancestors, doc]


def load_profile(profile_id: str, *, builtin_dir: Path = BUILTIN_DIR) -> ResolvedProfile:
    """Load `profile_id`, resolve its `extends` ancestry (ADR-0031) and compute `profile_hash`."""
    chain_docs = _read_chain(profile_id, builtin_dir, [])
    resolved: dict[str, Any] = {}
    for doc in chain_docs:
        resolved = deep_merge(resolved, doc)
    resolved.pop("profile_hash", None)  # readOnly, derived value (bible §7.3): never hashed in
    digest = hash_of("profile", canonical_json(resolved))
    resolved["profile_hash"] = digest
    chain_ids = tuple(doc["profile_id"] for doc in chain_docs)
    return ResolvedProfile(profile_id=profile_id, chain=chain_ids, data=resolved, profile_hash=digest)


def profile_hash(resolved_without_hash: dict[str, Any]) -> str:
    """Compute `profile_hash` for an already-resolved document (bible §6.2)."""
    payload = {k: v for k, v in resolved_without_hash.items() if k != "profile_hash"}
    return hash_of("profile", canonical_json(payload))
