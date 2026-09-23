"""PostgreSQL job and index ledger (shell layer; bible §13.1, §12 ``ledger``).

Planned modules: ``models``, ``repo``, ``migrations/``, ``reconcile``, ``consistency_check`` and
``usage``. Every table carries ``tenant_id`` with row level security ``FORCE``.
"""

from __future__ import annotations
