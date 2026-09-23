"""GENERATED — do not edit; run `uv run python tools/contracts_gen.py` to regenerate.

Source of truth: schemas/*.schema.json (bible §5.1, §6.4, §12)."""

from __future__ import annotations

from pydantic import Field, RootModel

from . import common_types


class ProblemDetails(RootModel[common_types.ProblemDetails]):
    root: common_types.ProblemDetails = Field(
        ...,
        description="RFC 9457 Problem Details 응답 본문(application/problem+json). 정의는 urn:rag:schema:common-types:1#/$defs/ProblemDetails(03-contracts/00 소유)이며 이 파일은 인벤토리 게시용 $ref 래퍼다. HTTP 매핑·지역화·불변식은 03-contracts/13-error-model.",
        title="ProblemDetails",
    )
