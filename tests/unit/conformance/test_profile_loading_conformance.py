"""프로파일 4종(`lite`/`standard`/`premium`/`korean-gov`) 로딩과 `profile_hash` 안정성 — 적합성 키트 관점.

검증 대상: `profiles.loader.load_profile`이 내장 tier 4종을 모두 성공적으로 로딩하는지, 반복
로딩에서 `profile_hash`가 안정적인지(동일 내용 -> 동일 해시, 매 호출 새로 계산해도 변하지
않음), 4종의 해시가 서로 다른지(내용이 다르면 구분됨), 그리고 이 값이 적합성 키트의
`default_stage_context()`가 만드는 `ctx.profile_hash`로 그대로 전달될 수 있는지 확인한다.
`tests/unit/test_profiles_loader.py`(6A)가 이미 `extends` 병합·순환·`canonical_json` 자체를
자세히 검증하므로, 여기서는 적합성 키트가 실제로 기대는 지점(tier 4종 전부·해시 안정성·
`StageContext` 연동)만 보충한다.
설계 근거: 바이블 §7(프로파일 상속 체인 `base -> lite -> standard -> premium`, `korean-gov
extends standard`), §6.2(`profile_hash` 결합 규칙), §4.1(`ctx.profile_hash`), ADR-0031.
구성: 4종 프로파일 로딩 성공 검사, 반복 로딩 해시 안정성 검사, 4종 상호 해시 구분 검사,
`default_stage_context()` 연동 검사.
불변식: `profile_hash`는 같은 내용에 대해 항상 같고, 다른 내용에 대해서는 항상 다르다.
검증 계층: 1층(여기서 검증).
"""

from __future__ import annotations

from rag_platform.profiles.loader import load_profile
from rag_platform.testing.conformance.base import default_stage_context

_FOUR_TIER_PROFILE_IDS = ("lite", "standard", "premium", "korean-gov")


def test_all_four_tier_profiles_load_and_descend_from_base() -> None:
    """Each of the 4 shipped tiers loads and its `extends` chain roots at `base` (bible sec. 7)."""
    for profile_id in _FOUR_TIER_PROFILE_IDS:
        resolved = load_profile(profile_id)
        assert resolved.profile_id == profile_id
        assert resolved.chain[0] == "base"
        assert resolved.chain[-1] == profile_id
        assert resolved.data["license_policy"]


def test_profile_hash_is_stable_across_repeated_independent_loads() -> None:
    """Loading the same tier twice (two fresh disk reads) yields the identical `profile_hash`."""
    for profile_id in _FOUR_TIER_PROFILE_IDS:
        first_load = load_profile(profile_id)
        second_load = load_profile(profile_id)
        assert first_load.profile_hash == second_load.profile_hash


def test_profile_hash_is_distinct_across_the_four_tiers() -> None:
    """Four different resolved documents must not collide onto the same `profile_hash`."""
    hashes = {profile_id: load_profile(profile_id).profile_hash for profile_id in _FOUR_TIER_PROFILE_IDS}
    assert len(set(hashes.values())) == len(_FOUR_TIER_PROFILE_IDS)


def test_a_resolved_profile_hash_can_seed_a_stage_context() -> None:
    """`default_stage_context(profile_hash=...)` carries a real `load_profile` hash unchanged."""
    resolved = load_profile("standard")
    ctx = default_stage_context(profile_hash=resolved.profile_hash)
    assert ctx.profile_hash == resolved.profile_hash
