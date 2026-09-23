"""`rag_platform.profiles.validate` 단위 테스트 — 프로파일 JSON 스키마 검증과 로딩 시 규칙(§7.4)을 검증한다.

설계 근거: 바이블 §7.4(로딩 시 검증 규칙과 게이트 — 규칙 (3) `fusion.k` 필수, (10) `parse.router` 완전성,
(11) `hydrate.top_n ≥ max(rerank.top_n_in, pack.k_max)`, (12) `deny_cidrs` 축소 불가), §5.3(기본 차단 CIDR 9종).

구성:
- `validate_schema` — 내장 5개 프로파일이 스키마를 통과함, 필수 필드 누락 거부.
- `validate_loading_rules` — 내장 프로파일이 전 규칙을 통과함, 규칙 3/10/11/12 각각의 위반 케이스가
  해당 규칙 번호를 담은 `ProfileInvalidError.issues`를 내는지 확인.
- `SOURCE_FORMATS`/`DEFAULT_DENY_CIDRS` — 바이블 정본 값 개수(13종 원본 포맷, 9개 기본 차단 CIDR) 대조.

검증 계층: 1층(여기서 검증).
"""

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
