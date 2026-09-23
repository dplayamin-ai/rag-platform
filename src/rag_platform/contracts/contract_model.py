"""GENERATED — 수정 금지. 재생성: `uv run python tools/contracts_gen.py`

역할: 모든 계약 Pydantic v2 모델의 공통 베이스(`rag_platform.contracts.contract_model.ContractModel`) —
`run_datamodel_codegen`이 `--base-class`로 모든 스키마 생성 모델에 이 클래스를 상속시켜, `dump_contract()`
직렬화 하나를 전 계약이 공유하게 한다.
설계 근거: `docs/03-contracts/00-contract-overview.md` §8.1(필수 여부와 nullable은 독립된 두 축 — `Y(nullable)`
필드는 `exclude_none`으로 떨어뜨리면 안 되고 `N`·`N(nullable)` 필드만 `None`을 생략한다), 바이블 §5.1(계약이
정본), §12(모듈 맵 `contracts/`).
구성: `ContractModel` — `model_serializer(mode="wrap")`로 자신의 필드를 직접 다듬는 한 단계만 맡되, 중첩된
`ContractModel` 필드·리스트·매핑은 pydantic-core가 각 항목의 같은 래퍼를 다시 호출하므로 임의 깊이로 재귀
적용된다. `dump_contract()` — `model_dump(mode="json", by_alias=True)`를 감싼 편의 메서드.
불변식·주의: 어떤 필드가 `Y(nullable)`인지는 별도 등록표 없이 `FieldInfo.is_required()`로 판정한다 —
datamodel-code-generator가 스키마의 `required`+`type: [..., "null"]` 조합을 이미 `Field(...)`(기본값 없음) +
`T | None` 타입으로 옮겨 놓았으므로(§8.1 표) 그 둘의 조합이 곧 등록표다. `Y`(nullable 아님) 필드는 타입에
`null`이 없어 값이 `None`일 수 없으므로 이 로직의 영향을 받지 않는다. `RootModel[...]` 래퍼(스칼라 공용
타입)는 이 베이스를 쓰지 않지만 덤프 결과가 `dict`가 아니므로 그대로 통과한다. `tools/contracts_gen.py`만 이
파일을 쓴다 — 손으로 고친 내용은 다음 재생성 때 사라진다.
검증 계층: 1층(여기서 검증) — `tests/contracts/test_contract_roundtrip.py`,
`tests/unit/testing/test_contract_roundtrip.py`.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, SerializationInfo, SerializerFunctionWrapHandler, model_serializer
from pydantic.fields import FieldInfo

__all__ = ["ContractModel"]


def _droppable_none_keys(fields: dict[str, FieldInfo]) -> set[str]:
    """Field name *and* serialization alias, for every field the schema does not mark ``required``

    (``N`` and ``N(nullable)`` in overview §8.1's table) -- the only fields whose dumped ``None``
    this module ever removes. A schema ``Y(nullable)`` field is required, so
    ``FieldInfo.is_required()`` is false for it and it is never added here.
    """
    keys: set[str] = set()
    for name, field in fields.items():
        if field.is_required():
            continue
        keys.add(name)
        if field.alias:
            keys.add(field.alias)
    return keys


class ContractModel(BaseModel):
    """Shared base injected into every generated contract model via
    ``datamodel-code-generator --base-class``; adds the overview §8.1 null-vs-omit dump rule
    without changing validation (parsing an explicit ``null`` for a non-nullable field is already
    rejected by the field's own ``T`` type, independent of this class).
    """

    @model_serializer(mode="wrap")
    def _drop_optional_none(self, handler: SerializerFunctionWrapHandler, _info: SerializationInfo) -> Any:
        data = handler(self)
        if not isinstance(data, dict):
            return data  # a `RootModel` root value already reduced to a bare scalar
        for key in _droppable_none_keys(type(self).model_fields):
            if key in data and data[key] is None:
                del data[key]
        return data

    def dump_contract(self, **kwargs: Any) -> dict[str, Any]:
        """Serialize honoring overview §8.1: keep ``null`` for required-nullable (``Y(nullable)``)
        fields at every nesting depth, drop ``None`` for every ``N``/``N(nullable)`` field.
        Defaults to the wire form (``mode="json", by_alias=True``); override via ``kwargs`` as with
        ``model_dump``.
        """
        kwargs.setdefault("mode", "json")
        kwargs.setdefault("by_alias", True)
        return self.model_dump(**kwargs)
