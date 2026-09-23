"""RAG Platform 코어 패키지(배포명 `rag-platform`, import 이름 `rag_platform`) — 저장소 전체의 최상위 진입점.

설계 근거: 바이블 §6.7(패키지·배포 이름), §12(모듈 맵과 계층 의존 방향).
구성: 패키지 트리는 바이블 §12 모듈 맵을 그대로 따르며, `pyproject.toml`의 `[tool.importlinter]`가
아래에서 위로의 계층 의존 방향을 강제한다::

    contracts
    <- sdk | telemetry | korean
    <- plugins | adapters | pipelines | retrieval | render
    <- orchestration | ledger | storage | security | profiles | settings | eval
    <- api | mcp | cli

불변식: 모듈은 자신보다 아래 계층에서만 import할 수 있고, `|`로 구분된 모듈끼리는 서로 독립이다.
`testing`(적합성 키트)은 이 스택 밖에 있으며 프로덕션 진입점(`api`/`mcp`/`cli`)이 이를 import해서는 안 된다.
검증 계층: 1층(여기서 검증) — `uv run lint-imports`(import-linter 계약).
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

__all__ = ["__version__"]

try:
    __version__: str = version("rag-platform")
except PackageNotFoundError:  # pragma: no cover - source tree without an installed distribution
    __version__ = "0.0.0"
