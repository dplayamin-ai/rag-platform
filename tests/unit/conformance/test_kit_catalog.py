"""확장 지점 14종 적합성 기반 클래스 카탈로그(`CONFORMANCE_KIT_BY_EXTENSION_POINT`) 자체 검증.

검증 대상: 14개 키가 `plugins.registry.EXTENSION_POINTS`와 정확히 같은 집합인지, 각 클래스의
`extension_point`가 자기 키와 일치하는지, `stage_name`이 `sdk.stage.STAGE_NAMES` 카탈로그
값이거나(`evaluator`만 예외, 05 미해결 이슈 19) `None`인지, `Stage` 5멤버 기반 클래스와 역할
포트 기반 클래스가 올바르게 나뉘어 있는지 확인한다. 구체 플러그인 인스턴스가 필요 없는 클래스
메타데이터 수준 검사다.
설계 근거: `docs/10-development/06-plugin-development-guide.md` §8.1(기반 클래스 표),
`plugins/registry.py`(`EXTENSION_POINTS` D-10 14종), `sdk/stage.py`(`STAGE_NAMES`).
구성: 카탈로그 키 집합 대조, `extension_point` 자기일치 검사, `stage_name` 카탈로그 소속 검사,
기반 클래스 종류(`Stage` 5멤버 대 역할 포트) 분류 검사.
불변식: `CONFORMANCE_KIT_BY_EXTENSION_POINT`의 14개 키는 항상 `EXTENSION_POINTS`와 정확히
일치해야 한다 — 새 확장 지점을 추가하면 카탈로그도 함께 갱신해야 한다.
검증 계층: 1층(여기서 검증).
"""

from __future__ import annotations

from rag_platform.plugins.registry import EXTENSION_POINTS
from rag_platform.sdk.stage import STAGE_NAMES
from rag_platform.testing.conformance.base import PortConformanceKitBase, StageConformanceBase
from rag_platform.testing.conformance.kits import CONFORMANCE_KIT_BY_EXTENSION_POINT

_PORT_BASED_EXTENSION_POINTS = frozenset({"embedder", "index_backend"})


def test_catalog_has_exactly_the_fourteen_extension_points() -> None:
    """`CONFORMANCE_KIT_BY_EXTENSION_POINT` covers the closed D-10 14-value set, no more, no less."""
    assert set(CONFORMANCE_KIT_BY_EXTENSION_POINT) == set(EXTENSION_POINTS)
    assert len(CONFORMANCE_KIT_BY_EXTENSION_POINT) == 14


def test_each_kit_class_declares_its_own_extension_point() -> None:
    """Every kit class's `extension_point` class variable matches the table key it is filed under."""
    for extension_point, kit_class in CONFORMANCE_KIT_BY_EXTENSION_POINT.items():
        assert kit_class.extension_point == extension_point


def test_each_kit_class_declares_a_cataloged_stage_name_or_none() -> None:
    """`stage_name` is a real `sdk.stage.STAGE_NAMES` entry, except `evaluator` (open issue: `None`)."""
    for extension_point, kit_class in CONFORMANCE_KIT_BY_EXTENSION_POINT.items():
        stage_name = kit_class.stage_name
        if stage_name is None:
            assert extension_point == "evaluator"
        else:
            assert stage_name in STAGE_NAMES


def test_port_based_extension_points_use_the_port_kit_base() -> None:
    """`embedder`/`index_backend` skip the `Stage` 5-member checks; every other point keeps them."""
    for extension_point, kit_class in CONFORMANCE_KIT_BY_EXTENSION_POINT.items():
        if extension_point in _PORT_BASED_EXTENSION_POINTS:
            assert issubclass(kit_class, PortConformanceKitBase)
            assert not issubclass(kit_class, StageConformanceBase)
        else:
            assert issubclass(kit_class, StageConformanceBase)
