"""RAG Platform core package (distribution ``rag-platform``, import ``rag_platform``; bible §6.7).

The package tree follows the bible §12 module map. Layering is enforced by import-linter
(``pyproject.toml`` ``[tool.importlinter]``), from the bottom up::

    contracts
    <- sdk | telemetry | korean
    <- plugins | adapters | pipelines | retrieval | render
    <- orchestration | ledger | storage | security | profiles | settings | eval
    <- api | mcp | cli

A module may import only from layers below it; modules separated by ``|`` are independent.
``testing`` (the conformance kit) sits outside the stack and is never imported by production
entry points.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

__all__ = ["__version__"]

try:
    __version__: str = version("rag-platform")
except PackageNotFoundError:  # pragma: no cover - source tree without an installed distribution
    __version__ = "0.0.0"
