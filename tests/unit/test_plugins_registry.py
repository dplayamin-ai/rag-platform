"""`rag_platform.plugins.registry` 단위 테스트 — entry point 이름 규약, 라이선스/능력 게이트, 등록 표를 검증한다.

설계 근거: 바이블 §5.7(`ExtensionPoint` 14종 정본, D-10), §6.7(entry point 그룹 `rag_platform.{extension_point}`),
`ADR-0001`(라이선스 등급표 A/B/C/D/X), `ADR-0032`(플러그인 SDK `Stage` 프로토콜·적합성 키트).

구성:
- `entry_point_group` — 확장 지점 이름 → entry point 그룹 문자열 변환과 미지정 값 거부.
- `validate_plugin_meta` — `PluginMeta` 스키마 검증(필수 필드 누락 거부).
- `check_license`/`check_capabilities` — 등급 상한·`static_bundled` 링크 거부·지역 제한·능력 요구 대조.
- `PluginRegistry` — 등록·조회(`discover`/`meta`)·`build_stage`, `plugin_id` 접두어 일치, 방어적 복사.

불변식: `EXTENSION_POINTS`는 정확히 14개 값의 닫힌 집합이며, `plugin_id` 접두어는 `extension_point`와 일치해야 한다.
검증 계층: 1층(여기서 검증).
"""

from __future__ import annotations

import copy

import jsonschema
import pytest

from rag_platform.plugins.registry import (
    EXTENSION_POINTS,
    LicenseError,
    PluginRegistry,
    check_capabilities,
    check_license,
    entry_point_group,
    validate_plugin_meta,
)

_META = {
    "plugin_id": "embedder.fake_hash",
    "extension_point": "embedder",
    "version": "1.0.0",
    "license": "Apache-2.0",
    "license_grade": "A",
    "territory": ["KR"],
    "linkage": "pure_python",
    "isolation_supported": ["in_process"],
    "contracts_compat": ">=1.0,<2.0",
    "capabilities": {
        "isolation_modes": ["in_process"],
        "supports_resumable": False,
        "contracts_compat": ">=1.0,<2.0",
    },
}


def test_entry_point_group_matches_bible_naming() -> None:
    assert entry_point_group("embedder") == "rag_platform.embedder"


def test_entry_point_group_rejects_unknown_extension_point() -> None:
    with pytest.raises(ValueError, match="ExtensionPoint"):
        entry_point_group("not_a_real_extension_point")


def test_extension_points_is_the_closed_14_value_set() -> None:
    assert len(EXTENSION_POINTS) == 14
    assert "index_backend" in EXTENSION_POINTS


def test_validate_plugin_meta_accepts_a_well_formed_meta() -> None:
    validate_plugin_meta(_META)  # must not raise


def test_validate_plugin_meta_rejects_missing_required_field() -> None:
    bad = {k: v for k, v in _META.items() if k != "license_grade"}
    with pytest.raises(jsonschema.ValidationError):
        validate_plugin_meta(bad)


@pytest.mark.parametrize(
    ("grade", "max_grade", "should_raise"),
    [
        ("A", "B", False),
        ("B", "B", False),
        ("C", "B", True),
        ("X", "D", True),  # X is never loadable regardless of policy
    ],
)
def test_check_license_grade_ceiling(grade: str, max_grade: str, should_raise: bool) -> None:
    meta = {**_META, "license_grade": grade}
    policy = {"max_grade": max_grade, "territory": ["KR"]}
    if should_raise:
        with pytest.raises(LicenseError) as exc_info:
            check_license(meta, policy)
        assert exc_info.value.code == "plugin.license_denied"
    else:
        check_license(meta, policy)  # must not raise


def test_check_license_rejects_grade_b_with_static_bundled_linkage() -> None:
    meta = {**_META, "license_grade": "B", "linkage": "static_bundled"}
    with pytest.raises(LicenseError, match="static_bundled"):
        check_license(meta, {"max_grade": "B", "territory": ["KR"]})


def test_check_license_rejects_uncovered_territory() -> None:
    meta = {**_META, "territory": ["US"]}
    with pytest.raises(LicenseError):
        check_license(meta, {"max_grade": "B", "territory": ["KR"]})


def test_check_capabilities_rejects_unmet_requirement() -> None:
    with pytest.raises(LicenseError, match="supports_resumable") as exc_info:
        check_capabilities(_META, {"supports_resumable": True})
    assert exc_info.value.code == "plugin.capability_unsupported"


def test_check_capabilities_accepts_covered_list_requirement() -> None:
    check_capabilities(_META, {"isolation_modes": ["in_process"]})  # subset -> must not raise


def test_plugin_registry_register_discover_build_stage_round_trip() -> None:
    registry = PluginRegistry()
    registry.register(_META, lambda config, services: {"config": config, "services": services})
    assert [m["plugin_id"] for m in registry.discover("embedder")] == ["embedder.fake_hash"]
    assert registry.meta("embedder.fake_hash")["extension_point"] == "embedder"
    built = registry.build_stage("embedder.fake_hash", {"dim": 16}, services=None)
    assert built == {"config": {"dim": 16}, "services": None}


def test_plugin_registry_register_rejects_plugin_id_prefix_mismatch() -> None:
    registry = PluginRegistry()
    mismatched = {**_META, "plugin_id": "chunker.fake_hash"}  # prefix != extension_point
    with pytest.raises(ValueError, match="prefix"):
        registry.register(mismatched, lambda config, services: None)


def test_plugin_registry_meta_raises_key_error_for_unknown_plugin() -> None:
    registry = PluginRegistry()
    with pytest.raises(KeyError):
        registry.meta("embedder.does_not_exist")


def test_plugin_registry_register_copies_caller_meta_defensively() -> None:
    registry = PluginRegistry()
    meta = copy.deepcopy(_META)
    registry.register(meta, lambda config, services: None)
    meta["extension_point"] = "chunker"  # mutate caller's copy after registering
    assert registry.meta("embedder.fake_hash")["extension_point"] == "embedder"  # unaffected: registry copied it
