"""Conformance kit shipped with the distribution (outside the layer stack; bible §12 ``testing``).

Planned modules: ``contract_roundtrip``, ``idempotency``, ``security_invariants``,
``renderer_citation_roundtrip``, ``litm_order`` and ``fuser_equivalence``, plus fake
``StageContext`` and ``RuntimeServices``. Production entry points (``api``, ``orchestration``) must
not import this package (10-development/01 §4.2).
"""

from __future__ import annotations
