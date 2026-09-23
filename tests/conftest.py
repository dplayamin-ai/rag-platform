"""Repository-wide pytest configuration.

Layer markers are attached from the top-level test directory (10-development/04 §21: layer markers
map 1:1 to directories; §2 maps ``adapters``/``golden`` to ``component``, ``replay`` to
``integration`` and ``eval`` to ``quality``). Attribute markers such as ``needs_docker`` are set by
the tests themselves together with a ``# DEFERRED:`` comment (phase-6 plan §8).
"""

from __future__ import annotations

from pathlib import Path

import pytest

_TESTS_ROOT = Path(__file__).parent
LAYER_BY_DIR: dict[str, str] = {
    # bible §12 directories
    "contracts": "contract",
    "adapters": "component",
    "security": "security",
    "replay": "integration",
    "eval": "quality",
    # 10-development/01 §7 directories adopted by 04
    "golden": "component",
    "unit": "unit",
    "integration": "integration",
    "e2e": "e2e",
}


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        try:
            relative = item.path.relative_to(_TESTS_ROOT)
        except ValueError:
            continue
        layer = LAYER_BY_DIR.get(relative.parts[0]) if len(relative.parts) > 1 else None
        if layer is not None:
            item.add_marker(getattr(pytest.mark, layer))
