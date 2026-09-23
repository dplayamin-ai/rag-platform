"""`rag_platform.testing.contract_roundtrip` 단위 테스트 — `dump_contract`/`assert_contract_roundtrip`/
`contract_roundtrip` 픽스처가 계약 개요 §8.1 null·생략 규칙을 지켜 왕복하는지 검증한다.

설계 근거: ADR-0032 적합성 키트 표(`contract_roundtrip`), `docs/03-contracts/00-contract-overview.md`
§8.1(`Y(nullable)` 필드는 보존, `N` 필드는 `None`이면 생략).

구성: 실제 생성 계약 모듈에 대한 의존 없이(다른 작업의 스키마 변경에 흔들리지 않도록) `ContractModel`을
상속한 임시 모델 `_Producer`/`_Widget`과 그 `RootModel` 래퍼 `_WidgetEnvelope`로 왕복·불일치·`RootModel`
언랩·`validate` 훅 전파·픽스처 배선을 각각 검증한다.

불변식: `Y(nullable)` 필드는 `None`이어도 직렬화에서 생략되지 않는다(§8.1).
검증 계층: 1층(여기서 검증).
"""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import Field, RootModel

from rag_platform.contracts.contract_model import ContractModel
from rag_platform.testing.contract_roundtrip import (
    assert_contract_roundtrip,
    contract_roundtrip,  # noqa: F401 - pytest fixture, made available by name via this import
    dump_contract,
)


class _Producer(ContractModel):
    """Mirrors `common_types.Producer`'s shape: `image_digest` is required *and* nullable."""

    plugin_id: str
    image_digest: str | None = Field(...)  # Y(nullable): required, may be explicit null


class _Widget(ContractModel):
    """Mirrors a typical contract record: a nested required-nullable field plus an optional one."""

    widget_id: str
    producer: _Producer
    note: str | None = Field(None)  # N: optional, `None` means "omitted"


class _WidgetEnvelope(RootModel[_Widget]):
    """Mirrors `CloudEventEnvelope`'s shape: a `RootModel` wrapping the real `ContractModel`."""


def test_roundtrip_preserves_required_nullable_none() -> None:
    instance = {"widget_id": "w1", "producer": {"plugin_id": "p.x", "image_digest": None}}
    assert assert_contract_roundtrip(_Widget, instance) == instance


def test_dump_contract_drops_optional_none() -> None:
    model = _Widget.model_validate(
        {"widget_id": "w1", "producer": {"plugin_id": "p.x", "image_digest": None}, "note": None}
    )
    dumped = dump_contract(model)
    assert "note" not in dumped
    assert dumped["producer"]["image_digest"] is None  # nested Y(nullable) still preserved


def test_assert_contract_roundtrip_detects_mismatch() -> None:
    # `note: None` round-trips to omitted (N field), so comparing against the original (which
    # still has the key) must fail loudly rather than silently pass.
    instance = {"widget_id": "w1", "producer": {"plugin_id": "p.x", "image_digest": None}, "note": None}
    with pytest.raises(AssertionError, match="round-trip mismatch"):
        assert_contract_roundtrip(_Widget, instance)


def test_dump_contract_unwraps_root_model() -> None:
    instance = {"widget_id": "w1", "producer": {"plugin_id": "p.x", "image_digest": "sha256:abc"}}
    wrapped = _WidgetEnvelope.model_validate(instance)
    assert dump_contract(wrapped) == instance


def test_assert_contract_roundtrip_propagates_validate_failure() -> None:
    def _always_fails(_instance: Any) -> None:
        msg = "schema says no"
        raise ValueError(msg)

    instance = {"widget_id": "w1", "producer": {"plugin_id": "p.x", "image_digest": None}}
    with pytest.raises(ValueError, match="schema says no"):
        assert_contract_roundtrip(_Widget, instance, validate=_always_fails)


def test_contract_roundtrip_fixture_wraps_assert_function(
    contract_roundtrip: Any,  # noqa: F811 - the pytest fixture, injected by name
) -> None:
    instance = {"widget_id": "w1", "producer": {"plugin_id": "p.x", "image_digest": None}}
    assert contract_roundtrip(_Widget, instance) == instance
