"""Security services (shell layer; bible §10, §12 ``security``).

Planned modules: ``principal_resolver``, ``authz_cedar``, ``security_context``, ``rate_limit``,
``acl_recheck`` (``aclrev``), ``egress_policy``, ``backend_token`` (per-request tenant JWT),
``key_provider`` and ``audit``. Bible §12 restricts callers to ``api``, ``retrieval`` and
``adapters/index``; lower layers receive these capabilities through ``sdk`` ports.
"""

from __future__ import annotations
