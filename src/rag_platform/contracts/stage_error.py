"""GENERATED — do not edit; run `uv run python tools/contracts_gen.py` to regenerate.

Source of truth: schemas/*.schema.json (bible §5.1, §6.4, §12)."""

from __future__ import annotations

from pydantic import Field, RootModel

from . import common_types


class StageError(RootModel[common_types.StageError]):
    root: common_types.StageError = Field(
        ...,
        description="스테이지·셸·API가 생성하는 단일 오류 객체(바이블 §4.1·§5.3). 정의는 urn:rag:schema:common-types:1#/$defs/StageError(03-contracts/00 소유)이며 이 파일은 인벤토리 게시용 $ref 래퍼다. 필드 해설·카탈로그·불변식은 03-contracts/13-error-model.",
        title="StageError",
    )
