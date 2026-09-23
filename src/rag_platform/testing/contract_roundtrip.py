"""계약 왕복(round-trip) 검증을 재사용 가능한 함수·픽스처로 제공하는 적합성 키트 모듈.

역할: 임의 계약 모델(`ContractModel` 서브클래스, 또는 그것을 감싼 `RootModel`) + 예시 JSON 인스턴스
하나를 받아 "스키마 검증(선택) → 파싱 → `dump_contract()` 재직렬화 → 원본과 동치"를 한 번에 검사한다.
`tests/contracts/test_contract_roundtrip.py`가 이 모듈로 왕복 로직을 위임하고, 코어 어댑터·외부 플러그인
CI도 같은 함수를 호출한다(ADR-0032: "적합성 키트는 코어와 외부 플러그인이 같은 것을 실행한다").
설계 근거: ADR-0032 적합성 키트 표(`contract_roundtrip`), `docs/03-contracts/00-contract-overview.md`
§8.1(직렬화기는 `Y(nullable)` 필드를 `exclude_none`으로 떨어뜨리면 안 된다 — `dump_contract()`가 그 규칙을
구현하므로 이 모듈은 그것에 위임할 뿐 재구현하지 않는다), 바이블 §12 `testing/`.
구성: `dump_contract(model)` — `ContractModel.dump_contract()`/`RootModel.root` 언랩을 모두 처리하는 공통
진입점; `assert_contract_roundtrip(model_cls, instance, validate=...)` — 스키마 검증(선택) → 파싱 → 덤프
→ 동치 비교(불일치 시 `AssertionError`); `contract_roundtrip` — 같은 함수를 노출하는 pytest 픽스처.
불변식·주의: 스키마 검증은 호출자가 주입한 `validate` 콜러블(예:
`jsonschema.Draft202012Validator(...).validate`)에 위임한다 — 이 모듈은 `jsonschema`나 스키마 경로 해석을
모르므로 외부 플러그인 저장소에서도 그대로 쓸 수 있다(ADR-0032). 비교는 키 순서를 무시한 `dict` 동치이며,
문서 예시 자체가 스키마와 어긋나는 경우까지 고치지는 않는다 — 그 판단은 호출자(예: 문서별 xfail)의 몫이다.
검증 계층: 1층(여기서 검증) — `tests/unit/testing/test_contract_roundtrip.py`,
`tests/contracts/test_contract_roundtrip.py`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from pydantic import BaseModel, RootModel

from rag_platform.contracts.contract_model import ContractModel

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

__all__ = ["assert_contract_roundtrip", "contract_roundtrip", "dump_contract"]


def dump_contract(model: BaseModel) -> Any:
    """Serialize any contract model instance to its wire form (overview §8.1 null-vs-omit rule).

    A `ContractModel` instance delegates to its own `dump_contract()`. A `RootModel` (e.g. a
    schema's discriminated-union wrapper such as `CloudEventEnvelope`) unwraps to `.root` and
    recurses, since the actual payload -- and the `ContractModel` mixin -- lives one level down.
    Anything else (a plain, non-generated `BaseModel`) falls back to the closest equivalent
    (`exclude_none=True`) so this stays usable outside the generated `contracts/` package too.
    """
    if isinstance(model, ContractModel):
        return model.dump_contract()
    if isinstance(model, RootModel):
        root = model.root
        if isinstance(root, BaseModel):
            return dump_contract(root)
        return model.model_dump(mode="json")
    return model.model_dump(mode="json", by_alias=True, exclude_none=True)


def assert_contract_roundtrip(
    model_cls: type[BaseModel],
    instance: Mapping[str, Any],
    *,
    validate: Callable[[Any], None] | None = None,
) -> dict[str, Any]:
    """Validate (optionally), parse, re-serialize, and assert ``instance`` round-trips unchanged.

    Args:
        model_cls: The generated contract model (or a schema `$defs` model) to parse with.
        instance: A JSON-shaped example instance (already parsed to a mapping, e.g. from a
            fixture file).
        validate: Optional callable raising on an invalid instance (e.g. a bound
            ``jsonschema.Draft202012Validator(...).validate``); this function does not construct
            one itself, so schema/registry resolution stays the caller's responsibility.

    Returns:
        The dumped dict, for callers that want to assert more about the value beyond equality.

    Raises:
        AssertionError: If the re-serialized form differs from ``instance``.
        Exception: Whatever ``validate`` or ``model_cls.model_validate`` raise, unmodified.
    """
    if validate is not None:
        validate(instance)
    parsed = model_cls.model_validate(instance)
    dumped = dump_contract(parsed)
    if dumped != instance:
        msg = f"round-trip mismatch: original={instance!r} dumped={dumped!r}"
        raise AssertionError(msg)
    return dumped  # type: ignore[no-any-return]


@pytest.fixture
def contract_roundtrip() -> Callable[..., dict[str, Any]]:
    """Pytest fixture exposing `assert_contract_roundtrip` for direct use in test bodies."""
    return assert_contract_roundtrip
