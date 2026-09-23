"""Retrieval hot path, in-process and PostgreSQL-independent (layer L2; bible §12, ADR-0034).

Planned modules: ``planner``, ``filters`` (D-09 builders: security, strategy, user), ``channels``,
``fusion``, ``hydrate`` and ``rerank``; subpackages ``postprocess`` and ``pack``.
"""

from __future__ import annotations
