"""GENERATED — do not edit; run `uv run python tools/contracts_gen.py` to regenerate.

Source of truth: schemas/*.schema.json (bible §5.1, §6.4, §12)."""

from __future__ import annotations

from pydantic import Field, RootModel

from . import common_types


class EgressPolicy(RootModel[common_types.EgressPolicy]):
    root: common_types.EgressPolicy = Field(
        ...,
        description="아웃바운드 egress 정책(바이블 §5.3, §10.3 E16, ADR-0038). 프로파일 runtime.egress와 테넌트 policies.egress_policy가 생산하고 fetch·릴레이·구독 등록이 AND 합성으로 소비한다. 정의는 urn:rag:schema:common-types:1#/$defs/EgressPolicy(03-contracts/00 소유)이며 이 파일은 인벤토리 게시용 $ref 래퍼다. 합성 규칙·호스트 일치·예시·불변식은 03-contracts/15-collection-profile-and-policy-contracts.",
        title="EgressPolicy",
    )
