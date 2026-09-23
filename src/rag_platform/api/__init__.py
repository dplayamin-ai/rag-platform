"""REST API surface ``/v1`` on FastAPI (entry-point layer; bible §14, §12 ``api``; ADR-0018).

Planned routers: ``ingest``, ``query``, ``render``, ``answer``, ``jobs``, ``documents``,
``collections``, ``profiles``, ``tenants``, ``api_keys``, ``plugins``, ``schemas``, ``version``,
``audit_events``, ``eval``, ``feedback``, ``subscriptions`` and ``events`` (SSE); plus ``problems``
(RFC 9457) and ``idempotency``. Single source of API-only view DTOs (bible §5.1).
"""

from __future__ import annotations
