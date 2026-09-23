"""Unit tests for `rag_platform.profiles.validate` (bible §7.4 loading rules)."""

from __future__ import annotations

import copy

import jsonschema
import pytest

from rag_platform.profiles.loader import load_profile
from rag_platform.profiles.validate import (
    DEFAULT_DENY_CIDRS,
    SOURCE_FORMATS,
    ProfileInvalidError,
    validate_loading_rules,
    validate_schema,
)

BUILTIN_IDS = ("base", "lite", "standard", "premium", "korean-gov")


@pytest.mark.parametrize("profile_id", BUILTIN_IDS)
def test_every_builtin_profile_passes_schema_validation(profile_id: str) -> None:
    resolved = load_profile(profile_id)
    validate_schema(resolved.data)  # must not raise


@pytest.mark.parametrize("profile_id", BUILTIN_IDS)
def test_every_builtin_profile_passes_loading_rules(profile_id: str) -> None:
    resolved = load_profile(profile_id)
    validate_loading_rules(resolved.data)  # must not raise


def test_validate_schema_rejects_missing_required_field() -> None:
    resolved = load_profile("standard")
    broken = copy.deepcopy(resolved.data)
    del broken["tier"]
    with pytest.raises(jsonschema.ValidationError):
        validate_schema(broken)


def test_source_formats_has_all_13_bible_values() -> None:
    assert len(SOURCE_FORMATS) == 13
    assert "hwpx" in SOURCE_FORMATS
    assert "unknown" in SOURCE_FORMATS


def test_rule_10_rejects_router_missing_a_source_format_key() -> None:
    resolved = load_profile("standard")
    broken = copy.deepcopy(resolved.data)
    del broken["ingest"]["parse"]["router"]["hwp3"]
    with pytest.raises(ProfileInvalidError) as exc_info:
        validate_loading_rules(broken)
    assert any("(10)" in issue for issue in exc_info.value.issues)


def test_rule_3_rejects_missing_fusion_k() -> None:
    resolved = load_profile("standard")
    broken = copy.deepcopy(resolved.data)
    del broken["query"]["fusion"]["k"]
    with pytest.raises(ProfileInvalidError) as exc_info:
        validate_loading_rules(broken)
    assert any("(3)" in issue for issue in exc_info.value.issues)


def test_rule_11_rejects_hydrate_top_n_below_rerank_and_pack() -> None:
    resolved = load_profile("standard")
    broken = copy.deepcopy(resolved.data)
    broken["query"]["hydrate"]["top_n"] = 5  # below rerank.top_n_in=100 and pack.k_max=20
    with pytest.raises(ProfileInvalidError) as exc_info:
        validate_loading_rules(broken)
    assert any("(11)" in issue for issue in exc_info.value.issues)


def test_rule_12_rejects_a_shrunk_deny_cidrs_list() -> None:
    resolved = load_profile("standard")
    broken = copy.deepcopy(resolved.data)
    broken["runtime"]["egress"]["deny_cidrs"] = ["10.0.0.0/8"]  # missing the rest of the default set
    with pytest.raises(ProfileInvalidError) as exc_info:
        validate_loading_rules(broken)
    assert any("(12)" in issue for issue in exc_info.value.issues)


def test_default_deny_cidrs_has_nine_entries_matching_bible_5_3() -> None:
    assert len(DEFAULT_DENY_CIDRS) == 9
    assert "127.0.0.0/8" in DEFAULT_DENY_CIDRS
