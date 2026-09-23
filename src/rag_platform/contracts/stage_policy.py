"""GENERATED — do not edit; run `uv run python tools/contracts_gen.py` to regenerate.

Source of truth: schemas/*.schema.json (bible §5.1, §6.4, §12)."""

from __future__ import annotations

from pydantic import Field, RootModel

from . import common_types


class StagePolicy(RootModel[common_types.StagePolicy]):
    root: common_types.StagePolicy = Field(
        ...,
        description="스테이지 실행 정책(바이블 §4.4 표의 한 행, §5.3). 프로파일이 생산하고 셸(orchestration/context)이 소비한다. 정의는 urn:rag:schema:common-types:1#/$defs/StagePolicy(03-contracts/00 소유)이며 이 파일은 인벤토리 게시용 $ref 래퍼다. 필드 해설·예시·불변식은 03-contracts/15-collection-profile-and-policy-contracts.",
        title="StagePolicy",
    )
