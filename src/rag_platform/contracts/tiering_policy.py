"""GENERATED — do not edit; run `uv run python tools/contracts_gen.py` to regenerate.

Source of truth: schemas/*.schema.json (bible §5.1, §6.4, §12)."""

from __future__ import annotations

from pydantic import Field, RootModel

from . import common_types


class TieringPolicy(RootModel[common_types.TieringPolicy]):
    root: common_types.TieringPolicy = Field(
        ...,
        description="테넌트 격리 등급 승격 정책(바이블 §5.3, §10.3 E15, ADR-0028). 프로파일 security.tiering이 생산하고 tier_promotion 잡·컬렉션 검증이 소비한다. 정의는 urn:rag:schema:common-types:1#/$defs/TieringPolicy(03-contracts/00 소유)이며 이 파일은 인벤토리 게시용 $ref 래퍼다. 필드 해설·예시·불변식은 03-contracts/15-collection-profile-and-policy-contracts.",
        title="TieringPolicy",
    )
