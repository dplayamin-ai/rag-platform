"""Vendor adapters, one subpackage per extension point (layer L2; bible §12 ``adapters``).

Adapters over Forks: every directory registers at least one entry point. Adapters depend on
``sdk`` and ``contracts`` only; they never import ``storage`` or ``security`` (ArtifactRef loading
is the shell's job) and vendor types never leak out of the adapter module (10-development/03 §2.4).
"""

from __future__ import annotations
