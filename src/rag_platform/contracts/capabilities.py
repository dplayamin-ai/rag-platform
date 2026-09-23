"""GENERATED — do not edit; run `uv run python tools/contracts_gen.py` to regenerate.

Source of truth: schemas/*.schema.json (bible §5.1, §6.4, §12)."""

from __future__ import annotations

from pydantic import Field, RootModel

from . import common_types


class Capabilities(RootModel[common_types.Capabilities]):
    root: common_types.Capabilities = Field(
        ...,
        description="모든 Stage 공통 capabilities() 선언(바이블 §5.3, ADR-0032). 정의는 urn:rag:schema:common-types:1#/$defs/Capabilities(03-contracts/00 소유)이며 이 파일은 인벤토리 게시용 $ref 래퍼다. 바이블 §5.1이 같은 행에 적은 index_backend 전용 extra 타입 IndexBackendCapabilities는 Capabilities.extra 로 이 정의에 포함되며 독립 정의는 urn:rag:schema:common-types:1#/$defs/IndexBackendCapabilities 다(래퍼에는 $ref 외 키워드를 두지 않는다, 00 §10.3). 필드 해설·예시·불변식은 03-contracts/15-collection-profile-and-policy-contracts.",
        title="Capabilities",
    )
