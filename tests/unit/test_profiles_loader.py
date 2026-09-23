"""`rag_platform.profiles.loader` 단위 테스트 — 내장 프로파일의 `extends` 상속 병합과 `profile_hash` 계산을 검증한다.

설계 근거: 바이블 §7(프로파일 상속 체인 `base → lite → standard → premium`, `korean-gov extends standard`),
§6.2(`profile_hash` 해시 결합 규칙), `ADR-0031`(프로파일 스키마·`extends`·품질 게이트 — 배열은 교체, 딕셔너리는 병합).

구성:
- `load_profile` — 내장 5종 로딩, 상속 체인이 root→leaf 순서임을 확인, 순환 `extends`·미지정 `profile_id` 거부.
- `deep_merge` — 배열은 통째로 교체하고 딕셔너리는 재귀 병합함을 확인.
- `canonical_json`/`profile_hash` — 키 정렬·공백 없음, `profile_hash` 필드 자체는 해시에서 제외, 내용 변경 시 값 변경.
- `BUILTIN_DIR` — 내장 YAML 파일 경로 상수.

불변식: `profile_hash`는 자기 자신(hash 필드)을 제외한 정규화된 내용에서만 계산되어 순환 의존이 없다.
검증 계층: 1층(여기서 검증).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
import yaml

from rag_platform.profiles.loader import BUILTIN_DIR, canonical_json, deep_merge, load_profile, profile_hash

if TYPE_CHECKING:
    from pathlib import Path

BUILTIN_IDS = ("base", "lite", "standard", "premium", "korean-gov")


@pytest.mark.parametrize("profile_id", BUILTIN_IDS)
def test_every_builtin_profile_loads(profile_id: str) -> None:
    resolved = load_profile(profile_id)
    assert resolved.profile_id == profile_id
    assert resolved.data["profile_hash"] == resolved.profile_hash
    assert resolved.chain[-1] == profile_id


def test_extends_chain_is_root_to_leaf() -> None:
    resolved = load_profile("standard")
    assert resolved.chain == ("base", "lite", "standard")


def test_base_profile_has_no_ancestors() -> None:
    resolved = load_profile("base")
    assert resolved.chain == ("base",)
    assert resolved.data["extends"] is None


def test_load_profile_raises_for_unknown_profile_id(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_profile("does-not-exist", builtin_dir=tmp_path)


def test_load_profile_detects_extends_cycle(tmp_path: Path) -> None:
    (tmp_path / "a.yaml").write_text(yaml.safe_dump({"extends": "b", "profile_id": "a"}), encoding="utf-8")
    (tmp_path / "b.yaml").write_text(yaml.safe_dump({"extends": "a", "profile_id": "b"}), encoding="utf-8")
    with pytest.raises(ValueError, match="cycle"):
        load_profile("a", builtin_dir=tmp_path)


def test_deep_merge_replaces_arrays_wholesale_not_concatenated() -> None:
    base = {"a": [1, 2, 3], "b": {"c": 1}}
    override = {"a": [9], "b": {"c": 2}}
    merged = deep_merge(base, override)
    assert merged == {"a": [9], "b": {"c": 2}}  # ADR-0031: arrays replaced, dicts merged


def test_deep_merge_keeps_untouched_base_keys() -> None:
    base = {"a": 1, "b": 2}
    override = {"b": 3}
    assert deep_merge(base, override) == {"a": 1, "b": 3}


def test_canonical_json_sorts_keys_and_has_no_whitespace() -> None:
    assert canonical_json({"b": 1, "a": 2}) == '{"a":2,"b":1}'


def test_profile_hash_is_deterministic_and_excludes_profile_hash_field() -> None:
    resolved_1 = {"profile_id": "lite", "version": "1.0.0"}
    resolved_2 = {**resolved_1, "profile_hash": "stale-value-must-be-ignored"}
    assert profile_hash(resolved_1) == profile_hash(resolved_2)


def test_profile_hash_changes_when_content_changes() -> None:
    hash_a = profile_hash({"version": "1.0.0"})
    hash_b = profile_hash({"version": "1.0.1"})
    assert hash_a != hash_b


def test_builtin_dir_points_at_the_shipped_yaml_files() -> None:
    assert (BUILTIN_DIR / "standard.yaml").is_file()
