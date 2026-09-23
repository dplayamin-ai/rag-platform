"""Runtime settings built on pydantic-settings (shell layer; bible §6.6, §12 ``settings``).

Environment variables use the ``RAG_`` prefix with ``__`` as the nesting delimiter
(``RAG_PG__DSN``). Same layer as ``security`` and ``profiles``.
"""

from __future__ import annotations
