"""저장소 전역 pytest 설정 — 테스트 디렉터리 이름으로부터 계층(layer) 마커를 자동 부착한다.

설계 근거: `10-development/04` §21(계층 마커는 디렉터리와 1:1 대응)·§2(`adapters`/`golden` →
`component`, `replay` → `integration`, `eval` → `quality`). `needs_docker` 등 속성(attribute)
마커는 이 파일이 아니라 각 테스트가 `# DEFERRED:` 주석과 함께 직접 붙인다(phase-6 계획서 §8).

구성:
- `LAYER_BY_DIR` — 최상위 테스트 디렉터리 이름 → pytest 마커 이름 매핑 표.
- `pytest_collection_modifyitems(items)` — 각 테스트 항목의 경로에서 최상위 디렉터리를 찾아
  해당하는 계층 마커를 부여하는 pytest 훅.

불변식: `_TESTS_ROOT` 밖의 항목이나 표에 없는 디렉터리는 조용히 건너뛴다(마커 미부여는 오류가 아님).
검증 계층: 1층(여기서 검증) — 이 파일 자체는 `pytest --collect-only`로 표시되는 마커로 확인한다.
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
