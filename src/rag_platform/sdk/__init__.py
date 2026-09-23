"""Plugin and stage kernel SDK (layer L1; bible §12 ``sdk``).

Owns the stable surface that core adapters and external ``rag-plugin-*`` distributions build on:
``Stage``, ``StageContext`` (lineage, plan, artifacts), ``PipelineContext``, ``StagePolicy``
application hooks, capability models, ``SidecarStage``, ``TokenCounter``, the ``DerivedArtifacts``
write port and ``hash_of`` (the ``H()`` content key of bible §6.2). Depends only on ``contracts``.
Not to be confused with the client SDKs under the repository root ``sdk/`` (10-development/01 §2.5).
"""

from __future__ import annotations
