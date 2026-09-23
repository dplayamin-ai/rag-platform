"""계약 왕복(round-trip) 테스트 — `docs/03-contracts/*.md` 골든 예시가 스키마·생성 Pydantic 모델을 오가며
정보 손실 없이 일치하는지 검증한다.

설계 근거: `docs/03-contracts/00-contract-overview.md` §10.3(골든 예시 회귀·Pydantic 동치 게이트 — 골든
인스턴스의 정본은 문서 자체). 픽스처는 `tests/contracts/fixtures/`에 `tools/extract_examples.py`가 생성하며
이 테스트는 `docs/`를 직접 읽지 않는다.

구성:
- `_retrieve`/`_REGISTRY` — `urn:rag:schema:<name>:1` → `schemas/<name>.schema.json` 지연 로딩 레지스트리.
- `_validator_for`/`_model_class` — 스키마(또는 `$defs` 항목) 검증기와 대응 `rag_platform.contracts` 모델 클래스 조회.
- `_roundtrip(entry, instance)` — `rag_platform.testing.contract_roundtrip.assert_contract_roundtrip`에
  위임(스키마 검증 → Pydantic 파싱 → `dump_contract()` 재직렬화 → 원본과 비교, 계약 개요 §8.1의 null·생략 규칙).
- `test_fixtures_extracted`/`test_contract_roundtrip` — 매니페스트 존재 확인, 픽스처별 파라미터화 검증.

불변식·주의: 문서가 스키마와 어긋나 있을 수 있으므로(문서를 고치는 스위트가 아님) 각 단계 실패는 예외를 올리지
않고 런타임에 `pytest.xfail()`을 호출한다(정적 `xfail` 마커 미사용이라 `xfail_strict`에 영향받지 않는다).
검증 계층: 1층(여기서 검증) — `@pytest.mark.contract`.
"""

from __future__ import annotations

import importlib
import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

from rag_platform.testing.contract_roundtrip import assert_contract_roundtrip

if TYPE_CHECKING:
    from pydantic import BaseModel

ROOT = Path(__file__).resolve().parents[2]
SCHEMAS_DIR = ROOT / "schemas"
FIXTURES_DIR = Path(__file__).parent / "fixtures"
MANIFEST_PATH = FIXTURES_DIR / "manifest.json"

_URN_PREFIX = "urn:rag:schema:"


def _retrieve(uri: str) -> Resource:
    """Resolve ``urn:rag:schema:<name>:1`` to ``schemas/<name>.schema.json`` on demand."""
    if not uri.startswith(_URN_PREFIX):
        raise LookupError(uri)
    name = uri[len(_URN_PREFIX) :].rsplit(":", 1)[0]
    path = SCHEMAS_DIR / f"{name}.schema.json"
    contents = json.loads(path.read_text(encoding="utf-8"))
    return Resource.from_contents(contents, default_specification=DRAFT202012)


_REGISTRY = Registry(retrieve=_retrieve)  # type: ignore[call-arg]


def _load_manifest() -> list[dict[str, Any]]:
    if not MANIFEST_PATH.exists():
        return []
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))  # type: ignore[no-any-return]


MANIFEST = _load_manifest()


def _validator_for(schema_kebab: str, def_name: str | None) -> Draft202012Validator:
    base = f"{_URN_PREFIX}{schema_kebab}:1"
    ref = base if def_name is None else f"{base}#/$defs/{def_name}"
    return Draft202012Validator({"$ref": ref}, registry=_REGISTRY)


def _pascal_case(kebab: str) -> str:
    return "".join(word.capitalize() for word in kebab.split("-"))


def _model_class(schema_kebab: str, def_name: str | None) -> type[BaseModel]:
    module = importlib.import_module(f"rag_platform.contracts.{schema_kebab.replace('-', '_')}")
    name = def_name or _pascal_case(schema_kebab)
    cls = getattr(module, name, None)
    if cls is None:
        msg = f"{module.__name__} has no class {name!r}"
        raise AttributeError(msg)
    return cls  # type: ignore[no-any-return]


def _roundtrip(entry: dict[str, Any], instance: Any) -> None:
    validator = _validator_for(entry["schema"], entry["def_name"])
    model_cls = _model_class(entry["schema"], entry["def_name"])
    assert_contract_roundtrip(model_cls, instance, validate=validator.validate)


def test_fixtures_extracted() -> None:
    """Guard: fixtures are a build product, not checked-in-then-forgotten by hand."""
    assert MANIFEST, "run `uv run python tools/extract_examples.py` to (re)build fixtures first"


@pytest.mark.contract
@pytest.mark.parametrize("entry", MANIFEST, ids=[e["fixture"] for e in MANIFEST])
def test_contract_roundtrip(entry: dict[str, Any]) -> None:
    instance = json.loads((FIXTURES_DIR / entry["fixture"]).read_text(encoding="utf-8"))
    try:
        _roundtrip(entry, instance)
    except Exception as exc:  # noqa: BLE001 - any failure here may be a doc/schema drift, not a bug
        pytest.xfail(f"{entry['source_doc']} {entry['source_heading']!r}: {type(exc).__name__}: {exc}")
