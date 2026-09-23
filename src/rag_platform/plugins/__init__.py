"""Plugin discovery (layer L2; bible §12 ``plugins``).

Entry point registry for the groups ``rag_platform.{extension_point}`` (bible §6.7), ``PluginMeta``
validation, ``license_gate`` (D-02, ADR-0001) and ``capabilities_check``. The registry resolves
stage classes dynamically through entry points and never imports adapter modules statically.
"""

from __future__ import annotations
